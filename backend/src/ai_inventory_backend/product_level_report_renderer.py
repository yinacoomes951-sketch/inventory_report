from __future__ import annotations

import html
from typing import Any


class ProductLevelReportRenderer:
    def render_html(self, diagnosis: dict[str, Any]) -> str:
        summary = diagnosis["summary"]
        totals = summary["totals"]
        levels = diagnosis.get("levels", [])
        total_inventory = float(totals.get("total_inventory") or 0)
        actions = diagnosis.get("action_list", {})
        return f"""
<style data-product-level-report-style>
{_style()}
</style>
<section class="product-level-report">
  <article class="pl-report-shell">
    <header class="pl-header">
      <div>
        <h1>产品层级库存诊断报告</h1>
        <p>从产品层级识别备货与发货标签，定位优先排查方向。产品层级以SPU维度进行分级。</p>
      </div>
      <div class="pl-meta">
        <span>口径：产品层级</span>
        <span>排序：大爆款 → 公司级 → 团队级 → 运营级 → 未分级</span>
      </div>
    </header>

    <div class="pl-content">
      <section class="pl-hero">
        <div class="pl-hero-main">
          <span class="pl-eyebrow">核心结论</span>
          <h2>{html.escape(summary.get("headline") or "产品层级库存诊断")}</h2>
          <div class="pl-evidence-list">
            {''.join(_render_evidence(item, index) for index, item in enumerate(summary.get("evidence", []), start=1))}
          </div>
        </div>
        <aside class="pl-facts">
          <div><span>库存总量</span><strong>{_fmt_num(totals.get("total_inventory"))}</strong></div>
          <div><span>海外在途+可售</span><strong>{_fmt_num(totals.get("overseas_ready_qty"))}</strong></div>
          <div><span>整体可售天数</span><strong>{_fmt_days(totals.get("stocking_coverage_days"))}</strong></div>
          <div><span>365天以上库龄</span><strong>{_fmt_num(totals.get("aged_365_qty"))}</strong></div>
        </aside>
      </section>

      <section class="pl-section">
        <div class="pl-section-head">
          <h2>产品层级判断</h2>
          <p>每个层级只展示备货与发货标签，365天以上库龄作为事实指标展示。</p>
        </div>
        <div class="pl-level-grid">
          {''.join(_render_level_card(row, total_inventory) for row in levels)}
        </div>
      </section>

      <section class="pl-section">
        <div class="pl-section-head">
          <h2>结构化分析</h2>
          <p>左侧看库存和长库龄集中度，右侧看整体库龄结构。</p>
        </div>
        <div class="pl-dashboard-grid">
          {_render_concentration(levels)}
          {_render_aging(diagnosis.get("aging_buckets", []))}
        </div>
      </section>

      <section class="pl-section">
        <div class="pl-section-head">
          <h2>层级诊断明细</h2>
          <p>表格保留能决定排查方向的字段，明细下钻留给 SPU/SKU 报告或 BI。</p>
        </div>
        {_render_detail_table(levels, total_inventory)}
      </section>

      <section class="pl-section">
        <div class="pl-section-head">
          <h2>行动清单</h2>
          <p>行动清单由标签优先级生成：不足为 P0，过量为 P1，正常为 P2。</p>
        </div>
        <div class="pl-action-grid">
          {_render_action_card("今天处理", actions.get("today", []), "risk")}
          {_render_action_card("本周跟进", actions.get("this_week", []), "warn")}
          {_render_action_card("持续监控", actions.get("monitor", []), "")}
        </div>
      </section>

      <p class="pl-note">说明：本报告按源表“产品层级”聚合，备货区间为90-120天，发货区间为60-80天；365天以上库龄仅作为结构性库存事实展示，不在本版作为独立标签。</p>
    </div>
  </article>
</section>
""".strip()


def _render_evidence(item: dict[str, str], index: int) -> str:
    return f"""
<div class="pl-evidence">
  <span>{index}</span>
  <div><strong>{html.escape(str(item.get("title") or "-"))}</strong><p>{html.escape(str(item.get("text") or "-"))}</p></div>
</div>
"""


def _render_level_card(row: dict[str, Any], total_inventory: float) -> str:
    return f"""
<article class="pl-level-card">
  <div class="pl-level-top">
    <div>
      <h3>{html.escape(str(row.get("product_level") or "-"))}</h3>
      <div class="pl-badge-row">
        {_tag_badge("备货", row.get("stocking_label"))}
        {_tag_badge("发货", row.get("shipment_label"))}
      </div>
    </div>
    <strong>{int(row.get("sort_order") or 99):02d}</strong>
  </div>
  <dl>
    <div><dt>库存总量</dt><dd>{_fmt_num(row.get("total_inventory"))}</dd></div>
    <div><dt>库存占比</dt><dd>{_fmt_percent(row.get("total_inventory"), total_inventory)}</dd></div>
    <div><dt>海外在途+可售</dt><dd>{_fmt_num(row.get("overseas_ready_qty"))}</dd></div>
    <div><dt>整体可售天数</dt><dd>{_fmt_days(row.get("stocking_coverage_days"))}</dd></div>
    <div><dt>发货可售天数</dt><dd>{_fmt_days(row.get("overseas_coverage_days"))}</dd></div>
    <div><dt>365天以上库龄</dt><dd>{_fmt_num(row.get("aged_365_qty"))}</dd></div>
  </dl>
  <p>{html.escape(str(row.get("diagnosis") or ""))}</p>
</article>
"""


def _render_concentration(levels: list[dict[str, Any]]) -> str:
    max_inventory = max([float(row.get("total_inventory") or 0) for row in levels] or [1])
    max_aged = max([float(row.get("aged_365_qty") or 0) for row in levels] or [1])
    inventory_rows = []
    aged_rows = []
    for row in levels:
        class_name = _tag_class(row.get("stocking_label"))
        inventory_rows.append(
            _bar_row(f'{row.get("product_level")}库存', row.get("total_inventory"), max_inventory, class_name)
        )
        aged_rows.append(_bar_row(f'{row.get("product_level")}长库龄', row.get("aged_365_qty"), max_aged, "muted"))
    return (
        '<article class="pl-panel"><h3>库存和长库龄集中度</h3>'
        '<h4>库存集中度</h4>'
        f'{"".join(inventory_rows)}'
        '<h4>365天以上长库龄集中度</h4>'
        f'{"".join(aged_rows)}'
        "</article>"
    )


def _render_aging(rows: list[dict[str, Any]]) -> str:
    max_value = max([float(row.get("value") or 0) for row in rows] or [1])
    total_value = sum(float(row.get("value") or 0) for row in rows)
    bars = "".join(
        _bar_row(
            str(row.get("label") or "-"),
            row.get("value"),
            max_value,
            "muted",
            percent_text=_fmt_percent(row.get("value"), total_value),
        )
        for row in rows
    )
    return f'<article class="pl-panel"><h3>整体库龄结构</h3>{bars}</article>'


def _render_detail_table(levels: list[dict[str, Any]], total_inventory: float) -> str:
    rows = "".join(
        f"""
        <tr>
          <td>{html.escape(str(row.get("product_level") or "-"))}</td>
          <td>{_tag_badge("", row.get("stocking_label"))}</td>
          <td>{_tag_badge("", row.get("shipment_label"))}</td>
          <td class="num">{_fmt_num(row.get("total_inventory"))}</td>
          <td class="num">{_fmt_percent(row.get("total_inventory"), total_inventory)}</td>
          <td class="num">{_fmt_num(row.get("overseas_ready_qty"))}</td>
          <td class="num">{_fmt_days(row.get("stocking_coverage_days"))}</td>
          <td class="num">{_fmt_days(row.get("overseas_coverage_days"))}</td>
          <td class="num">{_fmt_num(row.get("aged_365_qty"))}</td>
          <td>{html.escape(str(row.get("question_to_investigate") or "-"))}</td>
          <td>{html.escape(str(row.get("action") or "-"))}</td>
        </tr>
        """
        for row in levels
    )
    return f"""
<div class="pl-table-wrap">
  <table>
    <thead>
      <tr>
        <th>产品层级</th><th>备货标签</th><th>发货标签</th><th>库存总量</th><th>库存占比</th>
        <th>海外在途+可售</th><th>整体可售天数</th><th>发货可售天数</th>
        <th>365天以上库龄</th><th>先查什么</th><th>建议动作</th>
      </tr>
    </thead>
    <tbody>{rows or '<tr><td colspan="11">暂无产品层级数据。</td></tr>'}</tbody>
  </table>
</div>
"""


def _render_action_card(title: str, items: list[str], class_name: str) -> str:
    return f"""
<article class="pl-action-card {html.escape(class_name)}">
  <h3>{html.escape(title)}</h3>
  <ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in items)}</ul>
</article>
"""


def _bar_row(
    label: str,
    value: Any,
    max_value: float,
    class_name: str,
    *,
    percent_text: str | None = None,
) -> str:
    width = 0 if max_value <= 0 else round(float(value or 0) / max_value * 100, 1)
    value_html = (
        f'<div class="pl-bar-value"><strong>{_fmt_num(value)}</strong><small>{html.escape(percent_text)}</small></div>'
        if percent_text is not None
        else f"<strong>{_fmt_num(value)}</strong>"
    )
    return f"""
<div class="pl-bar-row">
  <span>{html.escape(label)}</span>
  <div class="pl-track"><i class="{html.escape(class_name)}" style="width:{width}%"></i></div>
  {value_html}
</div>
"""


def _tag_badge(prefix: str, value: Any) -> str:
    text = str(value or "-")
    label = f"{prefix}：{text}" if prefix else text
    return f'<span class="pl-tag {_tag_class(text)}">{html.escape(label)}</span>'


def _tag_class(value: Any) -> str:
    text = str(value or "")
    if "不足" in text:
        return "short"
    if "过量" in text:
        return "excess"
    if text == "正常":
        return "normal"
    return "muted"


def _fmt_days(value: Any) -> str:
    if value is None:
        return "-"
    return f"{_fmt_num(value)}天"


def _fmt_num(value: Any) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:,.2f}" if not number.is_integer() else f"{int(number):,}"


def _fmt_percent(value: Any, total: float) -> str:
    try:
        if total <= 0:
            return "0.0%"
        return f"{round(float(value or 0) / total * 100, 1)}%"
    except (TypeError, ValueError):
        return "0.0%"


def _style() -> str:
    return """
.product-level-report{font-family:Arial,"Microsoft YaHei",sans-serif;color:#172033;line-height:1.55;background:#f5f7fa;padding:20px}
.product-level-report *{box-sizing:border-box}.pl-report-shell{max-width:1220px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden}
.pl-header{display:grid;grid-template-columns:minmax(0,1fr)auto;gap:18px;padding:22px 24px 18px;border-bottom:1px solid #e5e7eb}.pl-header h1{margin:0;font-size:24px}.pl-header p{margin:6px 0 0;color:#667085}.pl-meta{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}.pl-meta span{display:inline-flex;align-items:center;justify-content:center;min-height:26px;line-height:1;white-space:nowrap;border:1px solid #e5e7eb;border-radius:999px;padding:4px 10px;color:#667085;font-size:13px}
.pl-content{padding:20px 24px 24px}.pl-hero{display:grid;grid-template-columns:minmax(0,1.35fr)360px;gap:16px;margin-bottom:18px}.pl-hero-main{padding:18px;border:1px solid #d7e7f2;border-radius:8px;background:linear-gradient(135deg,#eef6fb 0%,#fff 76%)}.pl-eyebrow{display:inline-block;margin-bottom:10px;padding:4px 10px;border-radius:999px;background:#2f6690;color:#fff;font-size:12px;font-weight:700}.pl-hero h2{margin:0;font-size:22px;line-height:1.35}
.pl-evidence-list{display:grid;gap:10px;margin-top:16px}.pl-evidence{display:grid;grid-template-columns:28px minmax(0,1fr);gap:10px}.pl-evidence>span{display:flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:999px;background:#2f6690;color:#fff;font-size:12px;font-weight:700}.pl-evidence strong{display:block}.pl-evidence p{margin:2px 0 0;color:#667085}
.pl-facts{display:grid;gap:10px}.pl-facts>div{border:1px solid #e5e7eb;border-radius:8px;background:#fff;padding:12px}.pl-facts span{display:block;color:#667085;font-size:13px}.pl-facts strong{display:block;margin-top:2px;font-size:24px;line-height:1.2}
.pl-section{margin-top:18px}.pl-section-head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;margin-bottom:10px}.pl-section h2{margin:0;font-size:18px}.pl-section-head p{margin:0;color:#667085;font-size:13px}
.pl-level-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.pl-dashboard-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.pl-action-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.pl-level-card,.pl-panel,.pl-action-card{border:1px solid #e5e7eb;border-radius:8px;background:#fff;padding:14px}.pl-level-top{display:flex;justify-content:space-between;gap:12px}.pl-level-top h3,.pl-panel h3,.pl-action-card h3{margin:0 0 10px;font-size:15px}.pl-level-top>strong{color:#9ca3af}
.pl-badge-row{display:flex;flex-wrap:wrap;gap:6px}.pl-tag{display:inline-flex;align-items:center;min-height:24px;border-radius:999px;padding:3px 8px;font-size:12px;font-weight:700}.pl-tag.normal{background:#edf6f0;color:#4f7d61}.pl-tag.short{background:#f8ebe9;color:#a84f45}.pl-tag.excess{background:#fbf2df;color:#9a6b20}.pl-tag.muted{background:#f3f4f6;color:#667085}
.pl-level-card dl{display:grid;gap:7px;margin:12px 0}.pl-level-card dl div{display:flex;justify-content:space-between;border-bottom:1px solid #edf0f3}.pl-level-card dt{color:#667085}.pl-level-card dd{margin:0;font-weight:700}.pl-level-card p{margin:10px 0 0;color:#667085}
.pl-bar-row{display:grid;grid-template-columns:120px minmax(0,1fr)90px;gap:10px;align-items:center;margin:9px 0;font-size:13px}.pl-track{height:10px;border-radius:999px;background:#edf1f5;overflow:hidden}.pl-track i{display:block;height:100%;background:#2f6690}.pl-track i.normal{background:#4f7d61}.pl-track i.short{background:#a84f45}.pl-track i.excess{background:#9a6b20}.pl-track i.muted{background:#9ca3af}.pl-bar-value{text-align:right}.pl-bar-value strong{display:block}.pl-bar-value small{display:block;color:#9ca3af;font-size:12px;line-height:1.2}
.pl-table-wrap{overflow-x:hidden;border:1px solid #e5e7eb;border-radius:8px}.pl-table-wrap table{width:100%;table-layout:fixed;border-collapse:collapse;background:#fff;font-size:12.5px}.pl-table-wrap th,.pl-table-wrap td{padding:7px 6px;border-bottom:1px solid #e5e7eb;text-align:left;vertical-align:top;overflow-wrap:anywhere}.pl-table-wrap th{background:#f9fafb;color:#667085;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:clip}.pl-table-wrap th:nth-child(1),.pl-table-wrap td:nth-child(1){width:7.5%}.pl-table-wrap th:nth-child(2),.pl-table-wrap td:nth-child(2),.pl-table-wrap th:nth-child(3),.pl-table-wrap td:nth-child(3){width:7.5%}.pl-table-wrap th:nth-child(4),.pl-table-wrap td:nth-child(4),.pl-table-wrap th:nth-child(5),.pl-table-wrap td:nth-child(5),.pl-table-wrap th:nth-child(6),.pl-table-wrap td:nth-child(6),.pl-table-wrap th:nth-child(7),.pl-table-wrap td:nth-child(7),.pl-table-wrap th:nth-child(8),.pl-table-wrap td:nth-child(8),.pl-table-wrap th:nth-child(9),.pl-table-wrap td:nth-child(9){width:8%}.pl-table-wrap th:nth-child(10),.pl-table-wrap td:nth-child(10){width:15%}.pl-table-wrap th:nth-child(11),.pl-table-wrap td:nth-child(11){width:17.5%}.num{text-align:right;white-space:nowrap}.pl-action-card{border-top:4px solid #2f6690}.pl-action-card.risk{border-top-color:#a84f45}.pl-action-card.warn{border-top-color:#9a6b20}.pl-action-card ul{margin:0;padding-left:18px}.pl-note{margin:18px 0 0;padding:12px;border-radius:8px;background:#f9fafb;color:#667085;font-size:13px}
@media(max-width:980px){.pl-header,.pl-hero,.pl-dashboard-grid,.pl-action-grid{grid-template-columns:1fr}.pl-meta{justify-content:flex-start}.pl-level-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:640px){.product-level-report{padding:12px}.pl-content,.pl-header{padding-left:14px;padding-right:14px}.pl-level-grid{grid-template-columns:1fr}}
""".strip()
