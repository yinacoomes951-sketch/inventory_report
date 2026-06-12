from ai_inventory_backend.report_renderer import InventoryReportRenderer


def test_core_spu_sections_render_problem_specific_metric_columns():
    renderer = InventoryReportRenderer()
    rows = [
        _spu("RESTOCK-SHORT", stocking_days=80, overseas_days=80),
        _spu("RESTOCK-EXCESS", stocking_days=160, overseas_days=80),
        _spu("SHIPMENT-SHORT", stocking_days=120, overseas_days=50),
        _spu("SHIPMENT-EXCESS", stocking_days=120, overseas_days=110),
        _spu("STAGNANT", stocking_days=None, overseas_days=None, no_sales_count=1),
    ]

    sections = {
        title: renderer._render_spu_problem_section(
            title, group_rows, action, metric_title, metric_key
        )
        for title, group_rows, action, metric_title, metric_key
        in renderer._group_spus_by_problem(rows)
    }

    for title in ("备货不足SPU", "发货不足SPU"):
        assert "<th>预测日销</th>" in sections[title]
        assert "<td>12.5</td>" in sections[title]
        assert "<th>90天+库龄</th>" not in sections[title]

    for title in ("备货过量SPU", "发货过量SPU", "无动销/呆滞SPU"):
        assert "<th>90天+库龄</th>" in sections[title]
        assert "<td>345.0</td>" in sections[title]
        assert "<th>预测日销</th>" not in sections[title]

    for title, spu in (
        ("备货不足SPU", "RESTOCK-SHORT"),
        ("备货过量SPU", "RESTOCK-EXCESS"),
        ("发货不足SPU", "SHIPMENT-SHORT"),
        ("发货过量SPU", "SHIPMENT-EXCESS"),
        ("无动销/呆滞SPU", "STAGNANT"),
    ):
        assert f"<td>{spu}</td>" in sections[title]
        assert "<th>整体可售天数</th>" in sections[title]
        assert "<th>在途+可售天数</th>" in sections[title]
        assert "<th>综合影响分</th>" in sections[title]


def test_core_spu_sections_prefer_problem_specific_rows():
    renderer = InventoryReportRenderer()
    global_rows = [_spu("GLOBAL-TOP", stocking_days=80, overseas_days=80)]
    problem_rows = {
        "restock_shortage": [_spu("CATEGORY-TOP", stocking_days=20, overseas_days=80)],
    }

    groups = renderer._group_spus_by_problem(global_rows, problem_rows)
    restock_shortage_rows = groups[0][1]

    assert [row["spu"] for row in restock_shortage_rows] == ["CATEGORY-TOP"]


def _spu(
    spu: str,
    *,
    stocking_days: float | None,
    overseas_days: float | None,
    no_sales_count: int = 0,
) -> dict[str, object]:
    return {
        "spu": spu,
        "product_name": f"{spu}产品",
        "health_status": "local_warning",
        "stocking_coverage_days": stocking_days,
        "overseas_coverage_days": overseas_days,
        "demand_daily": 12.5,
        "aged_90_qty": 345,
        "aged_12m_qty": 0,
        "no_sales_count": no_sales_count,
        "impact_score": 88,
    }
