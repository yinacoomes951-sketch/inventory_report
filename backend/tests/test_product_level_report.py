import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from ai_inventory_backend import create_app
from ai_inventory_backend.diagnosis import RoleScope
from ai_inventory_backend.product_level_diagnosis import ProductLevelDiagnosisEngine
from ai_inventory_backend.product_level_report_renderer import ProductLevelReportRenderer
from ai_inventory_backend.repository import InventoryRepository


client = TestClient(create_app())


class _Result:
    def __init__(self, *, rows=None, row=None):
        self.rows = rows or []
        self.row = row or {}

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def one(self):
        return self.row


class _Connection:
    def __init__(self, statements, rows=None, row=None):
        self.statements = statements
        self.rows = rows or []
        self.row = row or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement, params):
        self.statements.append(str(statement))
        return _Result(rows=self.rows, row=self.row)


class _Engine:
    def __init__(self, *, rows=None, row=None):
        self.statements = []
        self.rows = rows or []
        self.row = row or {}

    def connect(self):
        return _Connection(self.statements, rows=self.rows, row=self.row)


def _scope():
    return RoleScope(
        id="real-owner-test",
        level="运营个人",
        object_name="测试对象",
        where_sql='and "归属" = :owner',
        params={"owner": "测试对象"},
    )


def test_product_level_labels_use_same_coverage_ranges_as_spu_dimension():
    diagnosis = ProductLevelDiagnosisEngine().build(
        scope=_scope(),
        batch_key="batch",
        level_rows=[
            _level("大爆款", stocking_days=89, overseas_days=59, aged_365_qty=0),
            _level("公司级产品", stocking_days=90, overseas_days=60, aged_365_qty=0),
            _level("团队级产品", stocking_days=120, overseas_days=80, aged_365_qty=0),
            _level("运营级产品", stocking_days=121, overseas_days=81, aged_365_qty=1),
        ],
        aging_buckets=[],
    )

    levels = {row["product_level"]: row for row in diagnosis["levels"]}
    assert levels["大爆款"]["stocking_label"] == "备货不足"
    assert levels["大爆款"]["shipment_label"] == "发货不足"
    assert levels["大爆款"]["priority"] == "P0"
    assert levels["公司级产品"]["stocking_label"] == "正常"
    assert levels["公司级产品"]["shipment_label"] == "正常"
    assert levels["团队级产品"]["stocking_label"] == "正常"
    assert levels["团队级产品"]["shipment_label"] == "正常"
    assert levels["运营级产品"]["stocking_label"] == "备货过量"
    assert levels["运营级产品"]["shipment_label"] == "发货过量"
    assert levels["运营级产品"]["priority"] == "P1"
    assert levels["运营级产品"]["risk_tags"] == ["备货过量", "发货过量"]
    assert "business_judgement" not in levels["运营级产品"]
    assert "stagnant_risk" not in levels["运营级产品"]


def test_product_level_action_list_is_label_priority_driven():
    diagnosis = ProductLevelDiagnosisEngine().build(
        scope=_scope(),
        batch_key="batch",
        level_rows=[
            _level("大爆款", stocking_days=80, overseas_days=70, aged_365_qty=0),
            _level("运营级产品", stocking_days=121, overseas_days=81, aged_365_qty=1),
            _level("未分级", stocking_days=100, overseas_days=70, aged_365_qty=0),
        ],
        aging_buckets=[],
    )

    assert diagnosis["action_list"]["today"][0].startswith("大爆款")
    assert "运营级产品" in diagnosis["action_list"]["this_week"][0]
    assert "未分级" in diagnosis["action_list"]["monitor"][0]
    assert "呆滞库存风险" not in str(diagnosis)
    for forbidden in ("保供", "观察", "控补", "清理"):
        assert forbidden not in str(diagnosis)


def test_product_level_metrics_group_by_product_level_and_keep_role_scope():
    engine = _Engine(
        rows=[
            {
                "product_level": "未分级",
                "sku_count": 2,
                "spu_count": 1,
                "total_inventory": 180,
                "overseas_ready_qty": 120,
                "domestic_total_qty": 60,
                "purchase_in_transit_qty": 0,
                "purchase_plan_qty": 0,
                "demand_daily": 2,
                "sales_30d": 60,
                "aged_90_qty": 3,
                "aged_365_qty": 1,
            }
        ]
    )
    repository = object.__new__(InventoryRepository)
    repository.engine = engine

    rows = repository._product_level_metrics({"insert_time": "batch"}, _scope())

    assert rows[0]["product_level"] == "未分级"
    assert rows[0]["stocking_coverage_days"] == 90
    assert rows[0]["overseas_coverage_days"] == 60
    assert rows[0]["aged_365_ratio"] == 0.0056
    sql = engine.statements[0]
    assert 'coalesce("产品层级", \'未分级\') as product_level' in sql
    assert 'coalesce("总库存", 0)' in sql
    assert 'coalesce("国外合计", 0)' in sql
    assert 'coalesce("国内总数量", 0)' in sql
    assert 'coalesce("最近30天总销量", 0)' in sql
    assert 'coalesce("国内库龄_365以上", 0)' in sql
    assert 'coalesce("12个月以上库龄", 0)' in sql
    assert "鎬" not in sql
    assert "鍥" not in sql
    assert "搴撻" not in sql
    assert 'and "归属" = :owner' in sql
    assert "group by 1" in sql


def test_product_level_aging_returns_report_buckets():
    engine = _Engine(
        row={
            "aged_90_180_qty": 20,
            "aged_180_270_qty": 30,
            "aged_270_365_qty": 40,
            "aged_365_qty": 10,
            "total_inventory": 150,
        }
    )
    repository = object.__new__(InventoryRepository)
    repository.engine = engine

    rows = repository._product_level_aging({"insert_time": "batch"}, _scope())
    sql = engine.statements[0]

    assert rows == [
        {"label": "0-90天", "value": 50},
        {"label": "90-180天", "value": 20},
        {"label": "180-270天", "value": 30},
        {"label": "270-365天", "value": 40},
        {"label": "365天以上", "value": 10},
    ]
    assert 'coalesce("国内库龄_90_180", 0)' in sql
    assert 'coalesce("3_6个月库龄", 0)' in sql
    assert 'coalesce("总库存", 0)' in sql
    assert "鎬" not in sql
    assert "鍥" not in sql
    assert "搴撻" not in sql


def test_product_level_report_renderer_contains_expected_sections_without_removed_actions():
    source = ProductLevelReportRenderer().render_html(
        ProductLevelDiagnosisEngine().build(
            scope=_scope(),
            batch_key="batch",
            level_rows=[_level("未分级", stocking_days=100, overseas_days=70, aged_365_qty=1)],
            aging_buckets=[{"label": "365天以上", "value": 1}],
        )
    )

    assert "产品层级判断" in source
    assert "display:inline-flex;align-items:center;justify-content:center;min-height:26px" in source
    assert 'class="pl-bar-value"' in source
    assert "100.0%" in source
    assert "库存占比" in source
    assert "库存集中度" in source
    assert "365天以上长库龄集中度" in source
    assert source.index("库存集中度") < source.index("365天以上长库龄集中度")
    assert source.index("未分级库存") < source.index("未分级长库龄")
    assert ".pl-table-wrap{overflow-x:hidden" in source
    assert ".pl-table-wrap table{width:100%;table-layout:fixed" in source
    assert "font-size:12.5px" in source
    assert ".pl-table-wrap th{background:#f9fafb;color:#667085;font-weight:700;white-space:nowrap" in source
    assert ".pl-table-wrap th:nth-child(10),.pl-table-wrap td:nth-child(10){width:15%}" in source
    assert "层级诊断明细" in source
    assert "行动清单" in source
    assert "未分级" in source
    assert "备货标签" in source
    assert "发货标签" in source
    assert "经营判断" not in source
    assert "呆滞库存风险" not in source
    for forbidden in ("保供", "观察", "控补", "清理"):
        assert forbidden not in source


def test_product_level_api_contracts_do_not_replace_spu_report_api():
    reports = client.get("/api/product-level-inventory-runs/latest/reports")
    assert reports.status_code == 200
    first_report = reports.json()[0]
    assert first_report["id"].startswith("product-level-")

    detail = client.get(f"/api/product-level-inventory-reports/{first_report['id']}")
    assert detail.status_code == 200
    assert "产品层级判断" in detail.json()["htmlContent"]
    assert "经营判断" not in detail.json()["htmlContent"]

    diagnosis = client.get(f"/api/product-level-inventory-reports/{first_report['id']}/diagnosis")
    assert diagnosis.status_code == 200
    assert "levels" in diagnosis.json()

    spu_reports = client.get("/api/inventory-runs/latest/reports")
    assert spu_reports.status_code == 200
    assert not spu_reports.json()[0]["id"].startswith("product-level-")


def test_export_product_level_html_page_wraps_report_content():
    export_module = _load_export_module()
    detail = {
        "id": "product-level-report",
        "title": "产品层级库存诊断报告",
        "batchKey": "batch",
        "riskLevel": "medium",
        "htmlContent": '<section class="product-level-report">产品层级判断</section>',
    }

    source = export_module._html_page(detail)

    assert "报告口径：产品层级" in source
    assert '<section class="product-level-report">产品层级判断</section>' in source


def _level(product_level, *, stocking_days, overseas_days, aged_365_qty):
    return {
        "product_level": product_level,
        "sku_count": 1,
        "spu_count": 1,
        "total_inventory": 100,
        "overseas_ready_qty": 70,
        "domestic_total_qty": 30,
        "purchase_in_transit_qty": 0,
        "purchase_plan_qty": 0,
        "demand_daily": 1,
        "sales_30d": 30,
        "stocking_coverage_days": stocking_days,
        "overseas_coverage_days": overseas_days,
        "domestic_coverage_days": 30,
        "aged_90_qty": aged_365_qty,
        "aged_365_qty": aged_365_qty,
        "aged_365_ratio": aged_365_qty / 100,
    }


def _load_export_module():
    export_path = Path(__file__).resolve().parents[1] / "tools" / "export_product_level_reports.py"
    spec = importlib.util.spec_from_file_location("export_product_level_reports", export_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
