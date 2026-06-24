from ai_inventory_backend.diagnosis import RoleScope
from ai_inventory_backend.repository import (
    FORECAST_ZERO_THRESHOLD,
    InventoryRepository,
    _is_no_movement_spu,
    _normalize_forecast,
    _problem_top_spus,
    _report_inventory_cte,
    _safe_days,
)


class _Result:
    def __init__(self, row=None):
        self.row = row or {}

    def mappings(self):
        return self

    def one(self):
        return self.row

    def all(self):
        return []


class _Connection:
    def __init__(self, statements, row):
        self.statements = statements
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement, params):
        self.statements.append(str(statement))
        return _Result(self.row)


class _Engine:
    def __init__(self, row=None):
        self.statements = []
        self.row = row

    def connect(self):
        return _Connection(self.statements, self.row)


def _scope(where_sql="", params=None):
    return RoleScope(
        id="test-scope",
        level="运营个人",
        object_name="测试对象",
        where_sql=where_sql,
        params=params or {},
    )


def test_report_inventory_cte_filters_after_role_scope_and_spu_aggregation():
    sql = _report_inventory_cte(_scope('and "归属" = :owner', {"owner": "张三"}))

    assert 'and "归属" = :owner' in sql
    assert 'sum(coalesce("总库存", 0)) over (partition by spu)' in sql
    assert 'sum(coalesce("预测日销", 0)) over (partition by spu)' in sql
    assert f"report_spu_demand_daily < {FORECAST_ZERO_THRESHOLD}" in sql
    assert "report_spu_total_inventory <> 0 or normalized_spu_demand_daily <> 0" in sql


def test_all_report_queries_use_the_same_reportable_spu_scope():
    engine = _Engine()
    repository = object.__new__(InventoryRepository)
    repository.engine = engine
    batch = {"insert_time": "2026-06-12"}
    scope = _scope('and "部门名称" = :department', {"department": "测试部门"})

    repository._scope_metrics(batch, scope)
    repository._spu_health(batch, scope)
    repository._warning_distribution(batch, scope)
    repository._top_risk_skus(batch, scope)

    assert len(engine.statements) == 4
    for sql in engine.statements:
        assert "report_inventory as" in sql
        assert f"report_spu_demand_daily < {FORECAST_ZERO_THRESHOLD}" in sql
        assert "report_spu_total_inventory <> 0 or normalized_spu_demand_daily <> 0" in sql
        assert 'and "部门名称" = :department' in sql


def test_forecast_below_threshold_is_normalized_to_zero_before_filtering():
    sql = _report_inventory_cte(_scope())

    assert f"when report_spu_demand_daily < {FORECAST_ZERO_THRESHOLD} then 0" in sql
    assert "else coalesce(\"预测日销\", 0)" in sql
    assert "report_spu_total_inventory <> 0 or normalized_spu_demand_daily <> 0" in sql


def test_forecast_threshold_is_strictly_less_than_zero_point_five():
    sql = _report_inventory_cte(_scope())

    assert "report_spu_demand_daily < 0.5" in sql
    assert "report_spu_demand_daily <= 0.5" not in sql


def test_forecast_boundary_values_are_normalized_consistently():
    assert _normalize_forecast(0) == 0
    assert _normalize_forecast(0.49) == 0
    assert _normalize_forecast(0.5) == 0.5
    assert _safe_days(100, 0.49) is None
    assert _safe_days(100, 0.5) == 200


def test_low_forecast_with_inventory_is_treated_as_no_movement():
    row = {
        "total_inventory": 100,
        "sales_30d": 0,
        "demand_daily": 0.49,
        "health_status": "healthy",
    }

    assert _is_no_movement_spu(row) is True


def test_top_dimension_excludes_double_zero_spu_after_dimension_aggregation():
    engine = _Engine({"name": "张三"})
    repository = object.__new__(InventoryRepository)
    repository.engine = engine

    assert repository._top_dimension({"insert_time": "2026-06-12"}, "归属") == "张三"

    sql = engine.statements[0]
    assert 'coalesce("归属", \'未归属\') as name' in sql
    assert "group by 1, spu" in sql
    assert "when sum(coalesce(\"预测日销\", 0)) < 0.5 then 0" in sql
    assert "where total_inventory <> 0 or demand_daily <> 0" in sql


def test_report_metrics_and_spu_coverage_use_normalized_forecast():
    engine = _Engine()
    repository = object.__new__(InventoryRepository)
    repository.engine = engine
    batch = {"insert_time": "2026-06-12"}
    scope = _scope()

    repository._scope_metrics(batch, scope)
    repository._spu_health(batch, scope)

    metrics_sql, spu_sql = engine.statements
    assert "sum(report_forecast_daily_sales) as demand_daily" in metrics_sql
    assert "sum(report_forecast_daily_sales) as demand_daily" in spu_sql
    assert "nullif(sum(report_forecast_daily_sales), 0)" in spu_sql


def test_problem_top_spus_use_problem_specific_sorting_and_limit():
    rows = [
        _spu("HIGH-IMPACT", stocking_days=80, demand_daily=100, impact_score=999),
        _spu("LOWEST-COVERAGE", stocking_days=10, demand_daily=1, impact_score=1),
        _spu("SAME-COVERAGE-HIGH-DEMAND", stocking_days=20, demand_daily=50, impact_score=2),
        _spu("SAME-COVERAGE-LOW-DEMAND", stocking_days=20, demand_daily=10, impact_score=500),
    ]
    rows.extend(
        _spu(f"EXTRA-{index}", stocking_days=30 + index, demand_daily=1, impact_score=1)
        for index in range(10)
    )

    result = _problem_top_spus(rows)

    assert len(result["restock_shortage"]) == 8
    assert [row["spu"] for row in result["restock_shortage"][:4]] == [
        "LOWEST-COVERAGE",
        "SAME-COVERAGE-HIGH-DEMAND",
        "SAME-COVERAGE-LOW-DEMAND",
        "EXTRA-0",
    ]
    assert result["restock_shortage"][0]["impact_score"] < rows[0]["impact_score"]


def test_problem_top_spus_allow_one_spu_in_multiple_groups():
    row = _spu(
        "MULTI-PROBLEM",
        stocking_days=20,
        overseas_days=30,
        demand_daily=10,
        impact_score=100,
    )

    result = _problem_top_spus([row])

    assert result["restock_shortage"][0]["spu"] == "MULTI-PROBLEM"
    assert result["shipment_shortage"][0]["spu"] == "MULTI-PROBLEM"


def test_problem_top_spus_sort_each_remaining_problem_by_its_own_priority():
    rows = [
        _spu("RESTOCK-EXCESS-HIGH", stocking_days=200, demand_daily=1, impact_score=1),
        _spu(
            "RESTOCK-EXCESS-AGED",
            stocking_days=180,
            demand_daily=1,
            impact_score=999,
            aged_90_qty=500,
        ),
        _spu("SHIPMENT-SHORT-LOW", stocking_days=120, overseas_days=10, demand_daily=1, impact_score=1),
        _spu("SHIPMENT-SHORT-HIGH", stocking_days=120, overseas_days=40, demand_daily=100, impact_score=999),
        _spu("SHIPMENT-EXCESS-HIGH", stocking_days=120, overseas_days=160, demand_daily=1, impact_score=1),
        _spu(
            "SHIPMENT-EXCESS-AGED",
            stocking_days=120,
            overseas_days=140,
            demand_daily=1,
            impact_score=999,
            aged_90_qty=500,
        ),
        _spu(
            "STAGNANT-12M",
            stocking_days=None,
            demand_daily=0,
            impact_score=1,
            aged_90_qty=10,
            aged_12m_qty=5,
            health_status="stagnant",
        ),
        _spu(
            "STAGNANT-90D",
            stocking_days=None,
            demand_daily=0,
            impact_score=999,
            aged_90_qty=500,
            aged_12m_qty=0,
            health_status="stagnant",
        ),
    ]

    result = _problem_top_spus(rows)

    assert result["restock_excess"][0]["spu"] == "RESTOCK-EXCESS-HIGH"
    assert result["shipment_shortage"][0]["spu"] == "SHIPMENT-SHORT-LOW"
    assert result["shipment_excess"][0]["spu"] == "SHIPMENT-EXCESS-HIGH"
    assert result["stagnant"][0]["spu"] == "STAGNANT-12M"


def test_problem_top_spus_are_not_limited_to_global_top_30():
    global_top_rows = [
        _spu(f"GLOBAL-{index}", stocking_days=120, demand_daily=1, impact_score=1000 - index)
        for index in range(30)
    ]
    category_only_row = _spu(
        "CATEGORY-OUTSIDE-GLOBAL-TOP",
        stocking_days=10,
        demand_daily=1,
        impact_score=1,
    )

    result = _problem_top_spus([*global_top_rows, category_only_row])

    assert result["restock_shortage"][0]["spu"] == "CATEGORY-OUTSIDE-GLOBAL-TOP"


def test_build_report_detail_uses_rule_html_without_llm_rewrite():
    repository = object.__new__(InventoryRepository)
    repository.report_renderer = _Renderer()
    repository.llm_enhancer = _FailingLlmEnhancer()
    repository._build_diagnosis = lambda batch, scope: {
        "summary": {"risk_level": "medium"},
    }

    detail = repository._build_report_detail(
        {"batch_key": "batch"},
        _scope(),
    )

    assert detail.htmlContent == "<section>rule html</section>"


class _Renderer:
    def render_html(self, diagnosis):
        return "<section>rule html</section>"


class _FailingLlmEnhancer:
    def enhance_html(self, diagnosis, fallback_html):
        raise AssertionError("enhance_html should not be called by _build_report_detail")


def _spu(
    spu,
    *,
    stocking_days,
    overseas_days=80,
    demand_daily,
    impact_score,
    aged_90_qty=0,
    aged_12m_qty=0,
    total_inventory=100,
    sales_30d=30,
    health_status="local_warning",
):
    return {
        "spu": spu,
        "stocking_coverage_days": stocking_days,
        "overseas_coverage_days": overseas_days,
        "demand_daily": demand_daily,
        "impact_score": impact_score,
        "aged_90_qty": aged_90_qty,
        "aged_12m_qty": aged_12m_qty,
        "total_inventory": total_inventory,
        "sales_30d": sales_30d,
        "health_status": health_status,
    }
