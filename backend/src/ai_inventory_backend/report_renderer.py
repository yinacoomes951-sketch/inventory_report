from __future__ import annotations

import html
from typing import Any


class InventoryReportRenderer:
    def render_html(self, diagnosis: dict[str, Any]) -> str:
        summary = diagnosis["summary"]
        totals = summary["totals"]
        charts = diagnosis.get("charts", {})
        spu_health = diagnosis.get("spu_health", {})
        actions = diagnosis["action_list"]

        pain_cards = "".join(self._render_pain_card(problem) for problem in diagnosis["problems"][:4])
        paths = "".join(self._render_path(problem) for problem in diagnosis["problems"][:3])
        grouped_spus = self._group_spus_by_problem(
            spu_health.get("top_spus", []),
            spu_health.get("problem_top_spus"),
        )
        spu_sections = "".join(
            self._render_spu_problem_section(
                title,
                rows,
                action,
                metric_title,
                metric_key,
                secondary_metric_title,
                secondary_metric_key,
                sort_note,
            )
            for (
                title,
                rows,
                action,
                metric_title,
                metric_key,
                secondary_metric_title,
                secondary_metric_key,
                sort_note,
            ) in grouped_spus
            if rows
        )
        aged_rows = "".join(
            self._render_aged_row(row)
            for row in sorted(
                spu_health.get("top_spus", []),
                key=lambda item: (item.get("aged_90_qty") or 0, item.get("aged_12m_qty") or 0),
                reverse=True,
            )[:8]
            if (row.get("aged_90_qty") or 0) > 0
        )

        return f"""
<section class="report-html real-inventory-report">
  <h2>核心结论</h2>
  <div class="hero-diagnosis">
    <div>
      <span class="status-pill status-{html.escape(str(summary.get('health_status') or 'local_warning'))}">{_health_label(summary.get('health_status'))}</span>
      <p>{html.escape(summary['headline'])}</p>
    </div>
    <div class="hero-facts">
      <span>整体可售天数 <strong>{_fmt_num(totals.get('stocking_coverage_days'))}</strong> 天</span>
      <span>在途+可售天数 <strong>{_fmt_num(totals.get('overseas_coverage_days'))}</strong> 天</span>
      <span>12个月+库龄 <strong>{_fmt_num(totals.get('aged_12m_qty'))}</strong></span>
    </div>
  </div>

  <h2>库存健康总览</h2>
  <div class="summary-grid">
    <div><strong>{summary['key_counts']['spu_count']}</strong><span>SPU数</span></div>
    <div><strong>{summary['key_counts']['restock_shortage_spu_count']}</strong><span>备货不足SPU</span></div>
    <div><strong>{summary['key_counts']['restock_excess_spu_count']}</strong><span>备货过量SPU</span></div>
    <div><strong>{summary['key_counts']['shipment_shortage_spu_count']}</strong><span>发货不足SPU</span></div>
    <div><strong>{summary['key_counts']['shipment_excess_spu_count']}</strong><span>发货过量SPU</span></div>
    <div><strong>{summary['key_counts']['no_movement_spu_count']}</strong><span>无动销SPU</span></div>
    <div><strong>{_fmt_num(totals.get('stocking_inventory_qty'))}</strong><span>整体库存口径</span></div>
    <div><strong>{_fmt_num(totals.get('overseas_ready_qty'))}</strong><span>海外在途+可售</span></div>
    <div><strong>{_fmt_num(totals.get('aged_90_qty'))}</strong><span>90天+库龄</span></div>
  </div>

  <div class="concept-grid">
    <article>
      <h3>健康</h3>
      <p>整体可售天数在90-150天、在途+可售天数在60-100天，且动销和库龄未触发明显风险。</p>
    </article>
    <article>
      <h3>局部预警</h3>
      <p>备货或发货有一项高于上限，或出现90天以上库龄，需要运营复核。</p>
    </article>
    <article>
      <h3>不健康</h3>
      <p>整体可售天数低于90天或在途+可售天数低于60天，可能影响后续供给。</p>
    </article>
    <article>
      <h3>呆滞风险</h3>
      <p>SPU整体预测日销为0或动销弱，同时仍有库存或长库龄，重点关注清仓和坏账风险。</p>
    </article>
  </div>

  <h2>图表概览</h2>
  <div class="chart-grid">
    {self._render_bar_chart('SPU健康分布', charts.get('spu_health_distribution', []))}
    {self._render_bar_chart('库存问题分布', charts.get('warning_distribution', []))}
    {self._render_target_chart('可售天数区间', charts.get('coverage', []))}
    {self._render_bar_chart('库龄风险', charts.get('aging', []))}
  </div>

  <h2>TOP问题</h2>
  <div class="pain-grid">{pain_cards}</div>

  <h2>核心影响SPU</h2>
  <p>按问题拆开看，方便分别安排备货、发货、控货和清仓动作；同一个SPU可能出现在多个问题组里。</p>
  <div class="spu-section-list">{spu_sections}</div>

  <h2>排查路径</h2>
  <div class="path-list">{paths}</div>

  <h2>呆滞与清仓风险</h2>
  <p>重点看无动销、90天以上库龄、12个月以上库龄。这里只摘出长库龄最突出的少量SPU，便于优先清仓排查。</p>
  <table>
    <thead>
      <tr><th>SPU</th><th>产品</th><th>健康状态</th><th>90天+库龄</th><th>12个月+</th><th>近30天销量</th><th>建议</th></tr>
    </thead>
    <tbody>{aged_rows or '<tr><td colspan="7">本轮TOP影响SPU中暂无突出的90天以上长库龄对象。</td></tr>'}</tbody>
  </table>

  <h2>BI排查建议</h2>
  <div class="bi-handoff">
    <p>本报告不直接展开SKU明细，避免一进入报告就被过细颗粒度淹没。需要处理某个SPU时，再跳转BI按SPU下钻到SKU。</p>
    <ul>
      <li>优先筛选“核心影响SPU”表中的TOP SPU。</li>
      <li>备货问题：查看整体库存口径、预测日销、采购在途、采购计划，确认整体可售天数90-150天区间。</li>
      <li>发货问题：查看海外在途+可售和预测日销，确认在途+可售天数60-100天区间。</li>
      <li>呆滞清仓问题：查看无动销、国内90天以上库龄、海外90天以上库龄、12个月以上库龄。</li>
    </ul>
    <a class="bi-link" href="#" aria-disabled="true">跳转BI查看SKU明细（待接入BI深链）</a>
  </div>

  <h2>行动清单</h2>
  <h3>今天处理</h3>
  <ul>{''.join(f'<li>{html.escape(item)}</li>' for item in actions['today'])}</ul>
  <h3>本周跟进</h3>
  <ul>{''.join(f'<li>{html.escape(item)}</li>' for item in actions['this_week'])}</ul>
  <h3>需要人工确认</h3>
  <ul>{''.join(f'<li>{html.escape(item)}</li>' for item in actions['human_check'])}</ul>

  <p class="muted">说明：本报告由真实库存数据、库存诊断分析Skill和库存报告表达Skill生成；底层水位规则只参与判断，不作为面向运营的最终诊断表达。SKU明细建议通过BI按SPU下钻查看。</p>
</section>
""".strip()

    def _render_pain_card(self, problem: dict[str, Any]) -> str:
        facts = "".join(f"<li>{html.escape(fact)}</li>" for fact in problem["facts"])
        return f"""
<article class="pain-card">
  <span>{html.escape(problem.get('priority', '-'))}</span>
  <h3>{html.escape(problem['title'])}</h3>
  <p><strong>为什么痛：</strong>{html.escape(problem['inference'])}</p>
  <ul>{facts}</ul>
  <p><strong>先查什么：</strong>{html.escape(problem['question_to_investigate'])}</p>
  <p><strong>建议动作：</strong>{html.escape(problem['action'])}</p>
</article>
"""

    def _render_path(self, problem: dict[str, Any]) -> str:
        return f"""
<article class="path-card">
  <h3>{html.escape(problem['question_to_investigate'])}</h3>
  <p>先看核心影响SPU，再下钻突出SKU；备货按整体可售天数90-150天判断，发货按在途+可售天数60-100天判断。</p>
  <p>超过上限的对象不要直接补货或发货，先复核预测日销、季节性、链接状态和库龄。</p>
  <p>若出现12个月以上库龄，单独进入清仓、移除或坏账风险判断。</p>
</article>
"""

    def _render_bar_chart(self, title: str, rows: list[dict[str, Any]]) -> str:
        max_value = max([float(row.get("value") or 0) for row in rows] or [1])
        bars = "".join(
            f"""
            <div class="bar-row">
              <span>{html.escape(str(row.get('label') or '-'))}</span>
              <div class="bar-track"><i style="width:{_pct(row.get('value'), max_value)}%"></i></div>
              <strong>{_fmt_num(row.get('value'))}</strong>
            </div>
            """
            for row in rows
        )
        return f'<article class="chart-card"><h3>{html.escape(title)}</h3>{bars}</article>'

    def _render_target_chart(self, title: str, rows: list[dict[str, Any]]) -> str:
        bars = "".join(
            f"""
            <div class="target-row">
              <div><span>{html.escape(str(row.get('label') or '-'))}</span><small>合理 {_fmt_num(row.get('min'))}-{_fmt_num(row.get('max'))} 天</small></div>
              <div class="bar-track"><i class="{_target_class(row)}" style="width:{min(_pct(row.get('value'), row.get('max') or 1), 100)}%"></i></div>
              <strong>{_fmt_num(row.get('value'))}天</strong>
            </div>
            """
            for row in rows
        )
        return f'<article class="chart-card"><h3>{html.escape(title)}</h3>{bars}</article>'

    def _render_spu_row(
        self,
        row: dict[str, Any],
        metric_key: str,
        secondary_metric_key: str | None = None,
    ) -> str:
        focus_text = html.escape(str(row.get("_focus_text") or _spu_problem_text(row)))
        metric_text = _fmt_num(row.get(metric_key))
        secondary_metric_cell = (
            f"<td>{_fmt_num(row.get(secondary_metric_key))}</td>"
            if secondary_metric_key
            else ""
        )
        return (
            "<tr>"
            f"<td>{html.escape(str(row.get('spu') or '-'))}</td>"
            f"<td>{html.escape(str(row.get('product_name') or '-'))}</td>"
            f"<td>{_health_label(row.get('health_status'))}</td>"
            f"<td>{focus_text}</td>"
            f"<td>{_fmt_num(row.get('stocking_coverage_days'))}天</td>"
            f"<td>{_fmt_num(row.get('overseas_coverage_days'))}天</td>"
            f"<td>{metric_text}</td>"
            f"{secondary_metric_cell}"
            f"<td>{_fmt_num(row.get('impact_score'))}</td>"
            "</tr>"
        )

    def _group_spus_by_problem(
        self,
        rows: list[dict[str, Any]],
        problem_top_spus: dict[str, list[dict[str, Any]]] | None = None,
    ) -> list[
        tuple[str, list[dict[str, Any]], str, str, str, str | None, str | None, str]
    ]:
        problem_top_spus = problem_top_spus or {}
        restock_shortage = [
            {**row, "_focus_text": _restock_shortage_focus(row)}
            for row in problem_top_spus.get(
                "restock_shortage",
                [row for row in rows if _is_below(row.get("stocking_coverage_days"), 90)][:8],
            )
        ][:8]
        restock_excess = [
            {**row, "_focus_text": _restock_excess_focus(row)}
            for row in problem_top_spus.get(
                "restock_excess",
                [row for row in rows if _is_above(row.get("stocking_coverage_days"), 150)][:8],
            )
        ][:8]
        shipment_shortage = [
            {**row, "_focus_text": _shipment_shortage_focus(row)}
            for row in problem_top_spus.get(
                "shipment_shortage",
                [row for row in rows if _is_below(row.get("overseas_coverage_days"), 60)][:8],
            )
        ][:8]
        shipment_excess = [
            {**row, "_focus_text": _shipment_excess_focus(row)}
            for row in problem_top_spus.get(
                "shipment_excess",
                [row for row in rows if _is_above(row.get("overseas_coverage_days"), 100)][:8],
            )
        ][:8]
        stagnant = [
            {**row, "_focus_text": _stagnant_focus(row)}
            for row in problem_top_spus.get(
                "stagnant",
                [
                    row
                    for row in rows
                    if (row.get("no_sales_count") or 0) > 0
                    or row.get("health_status") == "stagnant"
                    or (row.get("aged_12m_qty") or 0) > 0
                ][:8],
            )
        ][:8]
        return [
            (
                "备货不足SPU",
                restock_shortage,
                "整体库存口径=海外在途+可售+国内库存+采购在途+采购计划；整体可售天数低于90天才进入补备货判断。",
                "预测日销",
                "demand_daily",
                None,
                None,
                "整体可售天数升序；相同时按预测日销、综合影响分降序。",
            ),
            (
                "备货过量SPU",
                restock_excess,
                "整体可售天数高于150天，优先暂停新增备货并消化库存。",
                "90天+库龄",
                "aged_90_qty",
                None,
                None,
                "整体可售天数、90天+库龄、综合影响分依次降序。",
            ),
            (
                "发货不足SPU",
                shipment_shortage,
                "发货只看海外在途+可售；低于60天优先安排发货或调拨。",
                "预测日销",
                "demand_daily",
                None,
                None,
                "在途+可售天数升序；相同时按预测日销、综合影响分降序。",
            ),
            (
                "发货过量SPU",
                shipment_excess,
                "在途+可售天数高于100天，优先控发并消化海外库存。",
                "90天+库龄",
                "aged_90_qty",
                None,
                None,
                "在途+可售天数、90天+库龄、综合影响分依次降序。",
            ),
            (
                "无动销/呆滞SPU",
                stagnant,
                "先查链接、停售、新品冷启动和库龄；清不了的库存进入清仓、移除或坏账关注。",
                "12个月+库龄",
                "aged_12m_qty",
                "90天+库龄",
                "aged_90_qty",
                "12个月+库龄、90天+库龄、总库存、综合影响分依次降序。",
            ),
        ]

    def _render_spu_problem_section(
        self,
        title: str,
        rows: list[dict[str, Any]],
        action: str,
        metric_title: str,
        metric_key: str,
        secondary_metric_title: str | None = None,
        secondary_metric_key: str | None = None,
        sort_note: str = "",
    ) -> str:
        row_html = "".join(
            self._render_spu_row(row, metric_key, secondary_metric_key) for row in rows
        )
        secondary_metric_header = (
            f"<th>{html.escape(secondary_metric_title)}</th>"
            if secondary_metric_title
            else ""
        )
        return f"""
<article class="spu-problem-section">
  <h3>{html.escape(title)}</h3>
  <p>{html.escape(action)}</p>
  <p class="sort-note">排序规则：{html.escape(sort_note)}</p>
  <table>
    <thead>
      <tr>
        <th>SPU</th><th>产品</th><th>健康状态</th><th>本组关注点</th>
        <th>整体可售天数</th><th>在途+可售天数</th><th>{html.escape(metric_title)}</th>{secondary_metric_header}<th>综合影响分</th>
      </tr>
    </thead>
    <tbody>{row_html}</tbody>
  </table>
</article>
"""

    def _render_aged_row(self, row: dict[str, Any]) -> str:
        suggestion = "优先清仓/移除/坏账关注" if (row.get("aged_12m_qty") or 0) > 0 else "复核动销并安排消化"
        return (
            "<tr>"
            f"<td>{html.escape(str(row.get('spu') or '-'))}</td>"
            f"<td>{html.escape(str(row.get('product_name') or '-'))}</td>"
            f"<td>{_health_label(row.get('health_status'))}</td>"
            f"<td>{_fmt_num(row.get('aged_90_qty'))}</td>"
            f"<td>{_fmt_num(row.get('aged_12m_qty'))}</td>"
            f"<td>{_fmt_num(row.get('sales_30d'))}</td>"
            f"<td>{suggestion}</td>"
            "</tr>"
        )

def _health_label(value: Any) -> str:
    return {
        "healthy": "健康",
        "local_warning": "局部预警",
        "unhealthy": "不健康",
        "stagnant": "呆滞风险",
    }.get(str(value or ""), "待复核")


def _target_class(row: dict[str, Any]) -> str:
    value = float(row.get("value") or 0)
    min_value = float(row.get("min") or 0)
    max_value = float(row.get("max") or 0)
    return "ok" if min_value <= value <= max_value else "risk"


def _spu_problem_text(row: dict[str, Any]) -> str:
    labels = []
    if _is_below(row.get("stocking_coverage_days"), 90):
        labels.append("备货不足")
    if _is_above(row.get("stocking_coverage_days"), 150):
        labels.append("备货过量")
    if _is_below(row.get("overseas_coverage_days"), 60):
        labels.append("发货不足")
    if _is_above(row.get("overseas_coverage_days"), 100):
        labels.append("发货过量")
    if (row.get("no_sales_count") or 0) > 0:
        labels.append("无动销")
    return " / ".join(labels) or "观察"


def _restock_shortage_focus(row: dict[str, Any]) -> str:
    return f"整体可售{_fmt_num(row.get('stocking_coverage_days'))}天，低于90天"


def _restock_excess_focus(row: dict[str, Any]) -> str:
    if (row.get("aged_90_qty") or 0) > 0:
        return f"整体可售{_fmt_num(row.get('stocking_coverage_days'))}天且90天+库龄"
    return f"整体可售{_fmt_num(row.get('stocking_coverage_days'))}天，高于150天"


def _shipment_shortage_focus(row: dict[str, Any]) -> str:
    return f"在途+可售{_fmt_num(row.get('overseas_coverage_days'))}天，低于60天"


def _shipment_excess_focus(row: dict[str, Any]) -> str:
    return f"在途+可售{_fmt_num(row.get('overseas_coverage_days'))}天，高于100天"


def _overstock_focus(row: dict[str, Any]) -> str:
    aged_qty = (row.get("domestic_aged_qty") or 0) + (row.get("overseas_aged_qty") or 0)
    if aged_qty > 0:
        return "库存偏高且已有库龄压力"
    return "可售天数偏高，暂停新增备货"


def _stagnant_focus(row: dict[str, Any]) -> str:
    if (row.get("aged_12m_qty") or 0) > 0:
        return "12个月+库龄，优先清仓/坏账关注"
    if (row.get("sales_30d") or 0) <= 0:
        return "近30天无动销，先查链接/停售"
    return "动销弱且库龄偏长，复核清仓策略"


def _is_below(value: Any, threshold: float) -> bool:
    try:
        return value is not None and float(value) < threshold
    except (TypeError, ValueError):
        return False


def _is_above(value: Any, threshold: float) -> bool:
    try:
        return value is not None and float(value) > threshold
    except (TypeError, ValueError):
        return False


def _pct(value: Any, max_value: Any) -> float:
    try:
        denominator = float(max_value or 1)
        if denominator <= 0:
            return 0
        return round(float(value or 0) / denominator * 100, 1)
    except (TypeError, ValueError):
        return 0


def _fmt_num(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):,.1f}"
    except (TypeError, ValueError):
        return str(value)
