from __future__ import annotations

from typing import Any

from .diagnosis import RoleScope


PRODUCT_LEVEL_ORDER = {
    "大爆款": 1,
    "公司级产品": 2,
    "团队级产品": 3,
    "运营级产品": 4,
    "未分级": 5,
}

NORMAL_LABEL = "正常"


class ProductLevelDiagnosisEngine:
    def build(
        self,
        *,
        scope: RoleScope,
        batch_key: str,
        level_rows: list[dict[str, Any]],
        aging_buckets: list[dict[str, Any]],
    ) -> dict[str, Any]:
        levels = [self._level_diagnosis(row) for row in self._sort_levels(level_rows)]
        totals = self._totals(levels)
        return {
            "scope": {
                "level": scope.level,
                "object_name": scope.object_name,
                "batch_key": batch_key,
            },
            "summary": {
                "risk_level": self._risk_level(levels),
                "headline": self._headline(scope, levels),
                "totals": totals,
                "evidence": self._evidence(levels),
            },
            "levels": levels,
            "aging_buckets": aging_buckets,
            "charts": {
                "inventory_concentration": [
                    {
                        "label": row["product_level"],
                        "inventory": row.get("total_inventory") or 0,
                        "aged_365_qty": row.get("aged_365_qty") or 0,
                    }
                    for row in levels
                ],
                "aging_buckets": aging_buckets,
            },
            "action_list": self._action_list(levels),
        }

    def _sort_levels(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda row: (
                PRODUCT_LEVEL_ORDER.get(str(row.get("product_level") or ""), 99),
                str(row.get("product_level") or ""),
            ),
        )

    def _level_diagnosis(self, row: dict[str, Any]) -> dict[str, Any]:
        product_level = str(row.get("product_level") or "未分级")
        stock_label = _stocking_label(row.get("stocking_coverage_days"))
        shipment_label = _shipment_label(row.get("overseas_coverage_days"))
        normalized = {
            **row,
            "product_level": product_level,
            "sort_order": PRODUCT_LEVEL_ORDER.get(product_level, 99),
            "stocking_label": stock_label,
            "shipment_label": shipment_label,
            "risk_tags": [stock_label, shipment_label],
        }
        normalized["priority"] = _priority(normalized)
        normalized["needs_human_check"] = _needs_human_check(normalized)
        normalized["question_to_investigate"] = _question_to_investigate(normalized)
        normalized["action"] = _suggested_action(normalized)
        normalized["first_check"] = normalized["question_to_investigate"]
        normalized["suggested_action"] = normalized["action"]
        normalized["diagnosis"] = _diagnosis_text(normalized)
        return normalized

    def _totals(self, levels: list[dict[str, Any]]) -> dict[str, Any]:
        total_inventory = sum(float(row.get("total_inventory") or 0) for row in levels)
        overseas_ready_qty = sum(float(row.get("overseas_ready_qty") or 0) for row in levels)
        demand_daily = sum(float(row.get("demand_daily") or 0) for row in levels)
        aged_365_qty = sum(float(row.get("aged_365_qty") or 0) for row in levels)
        return {
            "sku_count": sum(int(row.get("sku_count") or 0) for row in levels),
            "spu_count": sum(int(row.get("spu_count") or 0) for row in levels),
            "total_inventory": _to_number(total_inventory),
            "overseas_ready_qty": _to_number(overseas_ready_qty),
            "stocking_coverage_days": _safe_days(total_inventory, demand_daily),
            "overseas_coverage_days": _safe_days(overseas_ready_qty, demand_daily),
            "aged_365_qty": _to_number(aged_365_qty),
            "aged_365_ratio": _safe_ratio(aged_365_qty, total_inventory),
        }

    def _risk_level(self, levels: list[dict[str, Any]]) -> str:
        if any(
            row.get("stocking_label") != NORMAL_LABEL or row.get("shipment_label") != NORMAL_LABEL
            for row in levels
        ):
            return "medium"
        return "low"

    def _headline(self, scope: RoleScope, levels: list[dict[str, Any]]) -> str:
        if not levels:
            return f"{scope.object_name}当前没有可诊断的产品层级库存数据。"
        shortage_levels = [
            row["product_level"]
            for row in levels
            if row.get("stocking_label") == "备货不足" or row.get("shipment_label") == "发货不足"
        ]
        excess_levels = [
            row["product_level"]
            for row in levels
            if row.get("stocking_label") == "备货过量" or row.get("shipment_label") == "发货过量"
        ]
        if shortage_levels and excess_levels:
            return (
                f"{scope.object_name}产品层级库存同时存在不足和过量标签；"
                f"{'、'.join(shortage_levels[:2])}先查供给缺口，"
                f"{'、'.join(excess_levels[:2])}先查库存消化节奏。"
            )
        if shortage_levels:
            return f"{scope.object_name}产品层级库存主要是{'、'.join(shortage_levels[:3])}出现不足标签，需要优先排查供给缺口。"
        if excess_levels:
            return f"{scope.object_name}产品层级库存主要是{'、'.join(excess_levels[:3])}出现过量标签，需要优先排查库存消化节奏。"
        return f"{scope.object_name}产品层级库存标签整体正常，保持周度监控。"

    def _evidence(self, levels: list[dict[str, Any]]) -> list[dict[str, str]]:
        ranked = sorted(
            levels,
            key=lambda row: (
                row.get("stocking_label") == NORMAL_LABEL and row.get("shipment_label") == NORMAL_LABEL,
                -float(row.get("total_inventory") or 0),
            ),
        )
        evidence = []
        for row in ranked[:3]:
            evidence.append(
                {
                    "title": f"{row['product_level']}：{row['stocking_label']} / {row['shipment_label']}",
                    "text": (
                        f"整体可售{_fmt_days(row.get('stocking_coverage_days'))}，"
                        f"海外在途+可售{_fmt_days(row.get('overseas_coverage_days'))}，"
                        f"365天以上库龄{_fmt_num(row.get('aged_365_qty'))}。"
                    ),
                }
            )
        return evidence

    def _action_list(self, levels: list[dict[str, Any]]) -> dict[str, list[str]]:
        today = [f"{row['product_level']}：{row['action']}" for row in levels if row["priority"] == "P0"]
        this_week = [f"{row['product_level']}：{row['action']}" for row in levels if row["priority"] == "P1"]
        monitor = [f"{row['product_level']}：{row['action']}" for row in levels if row["priority"] == "P2"]
        human_check = [
            f"{row['product_level']}：{row['question_to_investigate']}"
            for row in levels
            if row.get("needs_human_check")
        ]
        return {
            "today": today or ["暂无 P0 产品层级标签，保持例行监控。"],
            "this_week": this_week or ["本周复核各产品层级可售天数是否仍在目标区间。"],
            "monitor": monitor or ["暂无完全正常层级，先处理异常标签后再恢复例行监控。"],
            "human_check": human_check or ["暂无必须人工确认项。"],
        }


def _stocking_label(value: Any) -> str:
    if _is_below(value, 90):
        return "备货不足"
    if _is_above(value, 120):
        return "备货过量"
    return NORMAL_LABEL


def _shipment_label(value: Any) -> str:
    if _is_below(value, 60):
        return "发货不足"
    if _is_above(value, 80):
        return "发货过量"
    return NORMAL_LABEL


def _priority(row: dict[str, Any]) -> str:
    if row.get("stocking_label") == "备货不足" or row.get("shipment_label") == "发货不足":
        return "P0"
    if row.get("stocking_label") == "备货过量" or row.get("shipment_label") == "发货过量":
        return "P1"
    return "P2"


def _needs_human_check(row: dict[str, Any]) -> bool:
    return row.get("stocking_label") != NORMAL_LABEL or row.get("shipment_label") != NORMAL_LABEL


def _question_to_investigate(row: dict[str, Any]) -> str:
    checks = []
    if row.get("stocking_label") == "备货不足":
        checks.append("预测日销、采购在途、采购计划是否足以覆盖90天")
    if row.get("stocking_label") == "备货过量":
        checks.append("预测日销是否偏高、采购计划是否需要控制")
    if row.get("shipment_label") == "发货不足":
        checks.append("海外在途+可售和发货计划是否足以覆盖60天")
    if row.get("shipment_label") == "发货过量":
        checks.append("海外库存消化速度和新增发货节奏是否匹配")
    return "；".join(checks) or "周度复核可售天数和库龄迁移"


def _suggested_action(row: dict[str, Any]) -> str:
    actions = []
    if row.get("stocking_label") == "备货不足":
        actions.append("复核预测日销、采购在途和采购计划，确认是否需要补采购")
    if row.get("stocking_label") == "备货过量":
        actions.append("复核预测日销和库龄，控制新增备货并优先消化库存")
    if row.get("shipment_label") == "发货不足":
        actions.append("复核海外在途+可售和发货计划，确认是否需要补发货")
    if row.get("shipment_label") == "发货过量":
        actions.append("复核海外库存消化速度，控制新增发货")
    return "；".join(actions) or "保持周度监控，关注可售天数和库龄迁移"


def _diagnosis_text(row: dict[str, Any]) -> str:
    return f"标签：{row['stocking_label']} / {row['shipment_label']}；建议：{row['action']}。"


def _safe_days(qty: Any, demand_daily: Any) -> float | int | None:
    try:
        demand = float(demand_daily or 0)
        if demand <= 0:
            return None
        return _to_number(round(float(qty or 0) / demand, 2))
    except (TypeError, ValueError):
        return None


def _safe_ratio(numerator: Any, denominator: Any) -> float:
    try:
        total = float(denominator or 0)
        if total <= 0:
            return 0.0
        return round(float(numerator or 0) / total, 4)
    except (TypeError, ValueError):
        return 0.0


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


def _to_number(value: Any) -> float | int | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else round(number, 2)


def _fmt_days(value: Any) -> str:
    number = _to_number(value)
    return "-" if number is None else f"{number}天"


def _fmt_num(value: Any) -> str:
    number = _to_number(value)
    if number is None:
        return "-"
    return f"{number:,.2f}" if isinstance(number, float) else f"{number:,}"
