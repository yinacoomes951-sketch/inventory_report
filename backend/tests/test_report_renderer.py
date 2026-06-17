from ai_inventory_backend.report_renderer import InventoryReportRenderer


def test_core_spu_sections_render_problem_specific_metric_columns():
    renderer = InventoryReportRenderer()
    rows = [
        _spu("RESTOCK-SHORT", stocking_days=80, overseas_days=80),
        _spu("RESTOCK-EXCESS", stocking_days=160, overseas_days=80),
        _spu("SHIPMENT-SHORT", stocking_days=120, overseas_days=50),
        _spu("SHIPMENT-EXCESS", stocking_days=120, overseas_days=110),
        _spu(
            "STAGNANT",
            stocking_days=None,
            overseas_days=None,
            no_sales_count=1,
            aged_12m_qty=123,
        ),
    ]

    sections = {
        title: renderer._render_spu_problem_section(
            title,
            group_rows,
            action,
            metric_title,
            metric_key,
            secondary_metric_title,
            secondary_metric_key,
            sort_note,
        )
        for (
            title,
            group_rows,
            action,
            metric_title,
            metric_key,
            secondary_metric_title,
            secondary_metric_key,
            sort_note,
        ) in renderer._group_spus_by_problem(rows)
    }

    for title in ("备货不足SPU", "发货不足SPU"):
        assert "<th>预测日销</th>" in sections[title]
        assert "<td>12.5</td>" in sections[title]
        assert "<th>90天+库龄</th>" not in sections[title]
        assert "<th>12个月+库龄</th>" not in sections[title]

    for title in ("备货过量SPU", "发货过量SPU"):
        assert "<th>90天+库龄</th>" in sections[title]
        assert "<td>345.0</td>" in sections[title]
        assert "<th>预测日销</th>" not in sections[title]
        assert "<th>12个月+库龄</th>" not in sections[title]

    stagnant_section = sections["无动销/呆滞SPU"]
    assert "<th>90天+库龄</th>" in stagnant_section
    assert "<td>345.0</td>" in stagnant_section
    assert "<th>12个月+库龄</th>" in stagnant_section
    assert "<td>123.0</td>" in stagnant_section
    assert "<th>预测日销</th>" not in stagnant_section
    assert stagnant_section.index("<th>12个月+库龄</th>") < stagnant_section.index(
        "<th>90天+库龄</th>"
    )

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


def test_core_spu_sections_render_problem_specific_sort_notes():
    renderer = InventoryReportRenderer()
    rows = [
        _spu("RESTOCK-SHORT", stocking_days=80, overseas_days=80),
        _spu("RESTOCK-EXCESS", stocking_days=160, overseas_days=80),
        _spu("SHIPMENT-SHORT", stocking_days=120, overseas_days=50),
        _spu("SHIPMENT-EXCESS", stocking_days=120, overseas_days=110),
        _spu(
            "STAGNANT",
            stocking_days=None,
            overseas_days=None,
            no_sales_count=1,
            aged_12m_qty=123,
        ),
    ]
    expected_notes = {
        "备货不足SPU": "整体可售天数升序；相同时按预测日销、综合影响分降序。",
        "备货过量SPU": "整体可售天数、90天+库龄、综合影响分依次降序。",
        "发货不足SPU": "在途+可售天数升序；相同时按预测日销、综合影响分降序。",
        "发货过量SPU": "在途+可售天数、90天+库龄、综合影响分依次降序。",
        "无动销/呆滞SPU": "12个月+库龄、90天+库龄、总库存、综合影响分依次降序。",
    }

    sections = {
        title: renderer._render_spu_problem_section(
            title,
            group_rows,
            action,
            metric_title,
            metric_key,
            secondary_metric_title,
            secondary_metric_key,
            sort_note,
        )
        for (
            title,
            group_rows,
            action,
            metric_title,
            metric_key,
            secondary_metric_title,
            secondary_metric_key,
            sort_note,
        ) in renderer._group_spus_by_problem(rows)
    }

    for title, expected_note in expected_notes.items():
        assert f'<p class="sort-note">排序规则：{expected_note}</p>' in sections[title]


def test_core_spu_sections_prefer_problem_specific_rows():
    renderer = InventoryReportRenderer()
    global_rows = [_spu("GLOBAL-TOP", stocking_days=80, overseas_days=80)]
    problem_rows = {
        "restock_shortage": [_spu("CATEGORY-TOP", stocking_days=20, overseas_days=80)],
    }

    groups = renderer._group_spus_by_problem(global_rows, problem_rows)
    restock_shortage_rows = groups[0][1]

    assert [row["spu"] for row in restock_shortage_rows] == ["CATEGORY-TOP"]


def test_aged_risk_table_renders_dedicated_layout_class():
    renderer = InventoryReportRenderer()
    source = renderer.render_html(
        {
            "summary": {
                "health_status": "local_warning",
                "headline": "test",
                "totals": {},
                "key_counts": {
                    "spu_count": 1,
                    "restock_shortage_spu_count": 0,
                    "restock_excess_spu_count": 0,
                    "shipment_shortage_spu_count": 0,
                    "shipment_excess_spu_count": 0,
                    "no_movement_spu_count": 0,
                },
            },
            "problems": [],
            "spu_health": {"top_spus": []},
            "action_list": {"today": [], "this_week": [], "human_check": []},
        }
    )

    assert '<div class="aged-risk-table">' in source
    assert '<tbody><tr><td colspan="7">' in source


def _spu(
    spu: str,
    *,
    stocking_days: float | None,
    overseas_days: float | None,
    no_sales_count: int = 0,
    aged_12m_qty: float = 0,
) -> dict[str, object]:
    return {
        "spu": spu,
        "product_name": f"{spu}产品",
        "health_status": "local_warning",
        "stocking_coverage_days": stocking_days,
        "overseas_coverage_days": overseas_days,
        "demand_daily": 12.5,
        "aged_90_qty": 345,
        "aged_12m_qty": aged_12m_qty,
        "no_sales_count": no_sales_count,
        "impact_score": 88,
    }
