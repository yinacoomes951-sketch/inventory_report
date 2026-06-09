from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RoleScope:
    id: str
    level: str
    object_name: str
    where_sql: str
    params: dict[str, Any]


class InventoryDiagnosisEngine:
    def build(
        self,
        *,
        scope: RoleScope,
        batch_key: str,
        metrics: dict[str, Any],
        warnings: list[dict[str, Any]],
        spu_health: dict[str, Any],
        top_skus: list[dict[str, Any]],
    ) -> dict[str, Any]:
        problems = self._build_problems(metrics, top_skus, spu_health)
        risk_level = self._risk_level(metrics)
        health_status = self._health_status(metrics, spu_health)
        return {
            "scope": {
                "level": scope.level,
                "object_name": scope.object_name,
                "batch_key": batch_key,
            },
            "summary": {
                "risk_level": risk_level,
                "health_status": health_status,
                "headline": self._headline(scope, metrics, health_status),
                "key_counts": {
                    "spu_count": int(metrics.get("spu_count") or 0),
                    "restock_shortage_spu_count": int(
                        spu_health.get("problem_distribution", {}).get("restock_shortage_spu") or 0
                    ),
                    "restock_excess_spu_count": int(
                        spu_health.get("problem_distribution", {}).get("restock_excess_spu") or 0
                    ),
                    "shipment_shortage_spu_count": int(
                        spu_health.get("problem_distribution", {}).get("shipment_shortage_spu") or 0
                    ),
                    "shipment_excess_spu_count": int(
                        spu_health.get("problem_distribution", {}).get("shipment_excess_spu") or 0
                    ),
                    "no_movement_spu_count": int(
                        spu_health.get("problem_distribution", {}).get("no_movement_spu") or 0
                    ),
                },
                "totals": {
                    "total_inventory": _to_number(metrics.get("total_inventory")),
                    "suggested_restock_qty": _to_number(metrics.get("suggested_restock_qty")),
                    "avg_sellable_days": _to_number(metrics.get("avg_sellable_days")),
                    "sales_30d": _to_number(metrics.get("sales_30d")),
                    "fba_available": _to_number(metrics.get("fba_available")),
                    "awd_available": _to_number(metrics.get("awd_available")),
                    "overseas_ready_qty": _to_number(metrics.get("overseas_ready_qty")),
                    "overseas_coverage_days": _to_number(metrics.get("overseas_coverage_days")),
                    "stocking_inventory_qty": _to_number(metrics.get("stocking_inventory_qty")),
                    "stocking_coverage_days": _to_number(metrics.get("stocking_coverage_days")),
                    "purchase_in_transit_qty": _to_number(metrics.get("purchase_in_transit_qty")),
                    "purchase_plan_qty": _to_number(metrics.get("purchase_plan_qty")),
                    "domestic_total_qty": _to_number(metrics.get("domestic_total_qty")),
                    "domestic_coverage_days": _to_number(metrics.get("domestic_coverage_days")),
                    "domestic_aged_90_qty": _to_number(metrics.get("domestic_aged_90_qty")),
                    "overseas_aged_90_qty": _to_number(metrics.get("overseas_aged_90_qty")),
                    "aged_90_qty": _to_number(metrics.get("aged_90_qty")),
                    "domestic_aged_qty": _to_number(metrics.get("domestic_aged_qty")),
                    "overseas_aged_qty": _to_number(metrics.get("overseas_aged_qty")),
                    "aged_12m_qty": _to_number(metrics.get("aged_12m_qty")),
                },
            },
            "problems": problems,
            "warning_distribution": warnings,
            "spu_health": spu_health,
            "charts": self._charts(metrics, warnings, spu_health),
            "top_skus": [self._sku_diagnosis(row) for row in top_skus],
            "action_list": self._action_list(problems),
        }

    def _build_problems(
        self,
        metrics: dict[str, Any],
        top_skus: list[dict[str, Any]],
        spu_health: dict[str, Any],
    ) -> list[dict[str, Any]]:
        problems = []
        shortage_skus = [row for row in top_skus if row.get("restock_warning") == "缺货预警"]
        limited_skus = [row for row in top_skus if row.get("restock_warning") == "限制备货"]
        no_sales_skus = [row for row in top_skus if row.get("restock_warning") == "无销量"]
        top_spus = spu_health.get("top_spus", [])
        problem_distribution = spu_health.get("problem_distribution", {})

        shortage_count = int(metrics.get("shortage_count") or 0)
        restock_shortage_spu = int(problem_distribution.get("restock_shortage_spu") or 0)
        if restock_shortage_spu:
            problems.append(
                {
                    "problem_type": "stockout",
                    "priority": "P0",
                    "title": "备货不足SPU需要优先补齐总库存水位",
                    "question_to_investigate": "哪些SPU的整体可售天数低于90天，需要补采购或补计划？",
                    "facts": [
                        f"备货不足SPU={restock_shortage_spu}",
                        f"整体可售天数={_fmt_num(metrics.get('stocking_coverage_days'))}天（目标90-150天）",
                        f"整体库存口径包含海外在途+可售、国内库存、采购在途、采购计划",
                    ],
                    "inference": "所有库存折算后低于备货安全下限，才进入补备货判断。",
                    "action": "按备货不足SPU优先级复核预测日销、采购在途和采购计划，确认是否补采购。",
                    "confidence": "high",
                    "needs_human_check": False,
                    "evidence_skus": [str(row.get("sku")) for row in shortage_skus[:8]],
                }
            )

        restock_excess_spu = int(problem_distribution.get("restock_excess_spu") or 0)
        if restock_excess_spu:
            problems.append(
                {
                    "problem_type": "restrict_restock",
                    "priority": "P1",
                    "title": "备货过量SPU需要暂停新增备货",
                    "question_to_investigate": "哪些SPU的整体可售天数高于150天，需要消化或暂停采购？",
                    "facts": [
                        f"备货过量SPU={restock_excess_spu}",
                        f"整体可售天数={_fmt_num(metrics.get('stocking_coverage_days'))}天（目标90-150天）",
                        f"90天以上库龄库存={_fmt_num(metrics.get('aged_90_qty'))}",
                    ],
                    "inference": "所有库存折算后高于备货上限，继续采购会加大库存占用。",
                    "action": "暂停新增备货，复核预测日销、季节性和库龄，优先消化库存。",
                    "confidence": "high",
                    "needs_human_check": False,
                    "evidence_skus": [str(row.get("sku")) for row in limited_skus[:8]],
                }
            )

        shipment_shortage_spu = int(problem_distribution.get("shipment_shortage_spu") or 0)
        shipment_excess_spu = int(problem_distribution.get("shipment_excess_spu") or 0)
        if shipment_shortage_spu or shipment_excess_spu:
            problems.append(
                {
                    "problem_type": "shipment",
                    "priority": "P1",
                    "title": "发货水位需要按海外在途+可售单独判断",
                    "question_to_investigate": "哪些SPU海外在途+可售低于60天或高于100天，需要调整发货节奏？",
                    "facts": [
                        f"发货不足SPU={shipment_shortage_spu}",
                        f"发货过量SPU={shipment_excess_spu}",
                        f"在途+可售天数={_fmt_num(metrics.get('overseas_coverage_days'))}天（目标60-100天）",
                    ],
                    "inference": "发货看海外在途和可售，不看采购在途/采购计划；低于下限优先发货，高于上限优先控发。",
                    "action": "按发货不足/发货过量SPU分别调整发货、调拨和控发节奏。",
                    "confidence": "high",
                    "needs_human_check": False,
                    "evidence_skus": [],
                }
            )

        no_movement_spu = int(problem_distribution.get("no_movement_spu") or 0)
        if no_movement_spu:
            problems.append(
                {
                    "problem_type": "no_sales",
                    "priority": "P1",
                    "title": "无动销SPU不能直接按普通补货处理",
                    "question_to_investigate": "这些SPU是停售、断货、链接异常、新品冷启动，还是数据口径问题？",
                    "facts": [
                        f"无动销SPU={no_movement_spu}",
                        f"国内库存={_fmt_num(metrics.get('domestic_total_qty'))}",
                        f"FBA可售={_fmt_num(metrics.get('fba_available'))}",
                        f"12个月以上库龄库存={_fmt_num(metrics.get('aged_12m_qty'))}",
                    ],
                    "inference": "无动销可能是运营状态问题，也可能是库存位置或数据状态问题，原因不能只靠库存表证明。",
                    "action": "先排查链接状态、开售状态、停售状态和库存可售位置，再决定是否备货或清理。",
                    "confidence": "medium",
                    "needs_human_check": True,
                    "evidence_skus": [str(row.get("sku")) for row in no_sales_skus[:8]],
                }
            )

        aged_qty = (metrics.get("domestic_aged_qty") or 0) + (metrics.get("overseas_aged_qty") or 0)
        stagnant_spus = [row for row in top_spus if row.get("health_status") == "stagnant"]
        if aged_qty > 0 or stagnant_spus:
            problems.append(
                {
                    "problem_type": "aged_inventory",
                    "priority": "P1",
                    "title": "库龄和呆滞库存需要单独清仓视角",
                    "question_to_investigate": "哪些SPU已经不动销且库龄偏长，需要清仓、停售复核或坏账关注？",
                    "facts": [
                        f"国内90天以上库龄={_fmt_num(metrics.get('domestic_aged_90_qty'))}",
                        f"海外90天以上库龄={_fmt_num(metrics.get('overseas_aged_90_qty'))}",
                        f"12个月以上库龄={_fmt_num(metrics.get('aged_12m_qty'))}",
                    ],
                    "inference": "底层水位规则只能说明库存位置是否偏离目标，库龄说明库存是否正在变成资金占用和坏账风险；两者必须分开看。",
                    "action": "对呆滞SPU优先做清仓/促销/移除/停售判断；清不了的库存单独进入坏账风险清单。",
                    "confidence": "high",
                    "needs_human_check": True,
                    "evidence_skus": [str(row.get("spu")) for row in stagnant_spus[:8]],
                }
            )

        unhealthy_spus = [row for row in top_spus if row.get("health_status") == "unhealthy"]
        if unhealthy_spus:
            problems.append(
                {
                    "problem_type": "spu_health",
                    "priority": "P1",
                    "title": "核心影响SPU需要从SPU下钻到SKU",
                    "question_to_investigate": "哪些SPU下面既有缺货SKU，又有国内或海外库存位置不合理的SKU？",
                    "facts": [
                        f"TOP不健康SPU={len(unhealthy_spus)}",
                        f"最高影响SPU={unhealthy_spus[0].get('spu') or '-'}",
                    ],
                    "inference": "运营实际处理通常先按SPU定位业务责任，再下钻SKU决定发货、备货或清理。",
                    "action": "先处理核心影响SPU，再进入突出SKU证据表确认具体SKU动作。",
                    "confidence": "high",
                    "needs_human_check": False,
                    "evidence_skus": [str(row.get("spu")) for row in unhealthy_spus[:8]],
                }
            )

        if not problems:
            problems.append(
                {
                    "problem_type": "shipment_allocation",
                    "priority": "P2",
                    "title": "当前未发现高优先级库存问题",
                    "question_to_investigate": "是否存在正常标签下的局部SKU发货或备货机会？",
                    "facts": [f"SKU数={int(metrics.get('sku_count') or 0)}"],
                    "inference": "整体风险较低，可按周度节奏复核重点SKU。",
                    "action": "保持常规监控，重点查看建议备货量为正且近30天销量较高的SKU。",
                    "confidence": "medium",
                    "needs_human_check": False,
                    "evidence_skus": [],
                }
            )
        return problems

    def _sku_diagnosis(self, row: dict[str, Any]) -> dict[str, Any]:
        demand_daily = row.get("forecast_daily_sales")
        return {
            "sku": row.get("sku"),
            "spu": row.get("spu"),
            "product_name": row.get("product_name"),
            "owner": row.get("owner"),
            "department_name": row.get("department_name"),
            "region": row.get("region"),
            "warning": _diagnosis_label(row.get("restock_warning")),
            "facts": {
                "sellable_days": _to_number(row.get("sellable_days")),
                "suggested_sellable_days": _to_number(row.get("suggested_sellable_days")),
                "suggested_restock_qty": _to_number(row.get("suggested_restock_qty")),
                "recent_30d_sales": _to_number(row.get("sales_30d")),
                "fba_available": _to_number(row.get("fba_available")),
                "awd_available": _to_number(row.get("awd_available")),
                "overseas_ready_qty": _to_number(row.get("overseas_ready_qty")),
                "overseas_coverage_days": _safe_days(row.get("overseas_ready_qty"), demand_daily),
                "domestic_total_qty": _to_number(row.get("domestic_total_qty")),
                "domestic_coverage_days": _safe_days(row.get("domestic_total_qty"), demand_daily),
                "domestic_aged_qty": _to_number(row.get("domestic_aged_qty")),
                "overseas_aged_qty": _to_number(row.get("overseas_aged_qty")),
                "aged_12m_qty": _to_number(row.get("aged_12m_qty")),
            },
            "action": self._sku_action(row),
        }

    def _action_list(self, problems: list[dict[str, Any]]) -> dict[str, list[str]]:
        today = [p["action"] for p in problems if p["priority"] == "P0"]
        this_week = [p["action"] for p in problems if p["priority"] in {"P1", "P2"}]
        human_check = [
            p["question_to_investigate"]
            for p in problems
            if p.get("needs_human_check")
        ]
        return {
            "today": today or ["优先查看核心影响SPU，必要时再下钻突出SKU证据。"],
            "this_week": this_week or ["保持周度复核。"],
            "human_check": human_check or ["暂无必须人工确认项。"],
        }

    def _headline(self, scope: RoleScope, metrics: dict[str, Any], health_status: str) -> str:
        health_text = {
            "healthy": "整体健康",
            "local_warning": "局部预警",
            "unhealthy": "不健康",
            "stagnant": "呆滞风险突出",
        }.get(health_status, "需要复核")
        return (
            f"{scope.object_name}当前库存健康判断为「{health_text}」；"
            f"有 {int(metrics.get('spu_count') or 0)} 个SPU纳入诊断；"
            f"备货按90-150天、发货按60-100天判断，"
            "并单独关注90天以上长库龄和无动销库存。"
        )

    def _health_status(self, metrics: dict[str, Any], spu_health: dict[str, Any]) -> str:
        distribution = spu_health.get("distribution", {})
        if int(distribution.get("stagnant") or 0) >= 3:
            return "stagnant"
        if int(distribution.get("unhealthy") or 0) > 0:
            return "unhealthy"
        if int(distribution.get("local_warning") or 0) > 0:
            return "local_warning"
        return "healthy"

    def _risk_level(self, metrics: dict[str, Any]) -> str:
        sku_count = metrics.get("sku_count") or 0
        shortage = metrics.get("shortage_count") or 0
        limited = metrics.get("limited_count") or 0
        if shortage >= 10 or (sku_count and shortage / sku_count >= 0.08):
            return "high"
        if shortage > 0 or limited >= 10:
            return "medium"
        return "low"

    def _sku_action(self, row: dict[str, Any]) -> str:
        warning = row.get("restock_warning")
        if warning == "缺货预警":
            return "优先补FBA/AWD可售；若国内库存充足则安排发货，否则补采购。"
        if warning == "限制备货":
            return "暂停新增备货，优先消化现有库存并复核销量趋势。"
        if warning == "无销量":
            return "先排查链接、停售、新品和断货原因，再决定是否备货。"
        if (row.get("suggested_restock_qty") or 0) > 0:
            return "按建议备货量补足到建议可售天数。"
        return "维持观察。"

    def _charts(
        self,
        metrics: dict[str, Any],
        warnings: list[dict[str, Any]],
        spu_health: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "spu_health_distribution": [
                {"label": "健康", "value": int(spu_health.get("distribution", {}).get("healthy") or 0)},
                {"label": "局部预警", "value": int(spu_health.get("distribution", {}).get("local_warning") or 0)},
                {"label": "不健康", "value": int(spu_health.get("distribution", {}).get("unhealthy") or 0)},
                {"label": "呆滞", "value": int(spu_health.get("distribution", {}).get("stagnant") or 0)},
            ],
            "warning_distribution": [
                {"label": "备货不足SPU", "value": int(spu_health.get("problem_distribution", {}).get("restock_shortage_spu") or 0)},
                {"label": "备货过量SPU", "value": int(spu_health.get("problem_distribution", {}).get("restock_excess_spu") or 0)},
                {"label": "发货不足SPU", "value": int(spu_health.get("problem_distribution", {}).get("shipment_shortage_spu") or 0)},
                {"label": "发货过量SPU", "value": int(spu_health.get("problem_distribution", {}).get("shipment_excess_spu") or 0)},
                {
                    "label": "无动销SPU",
                    "value": int(spu_health.get("problem_distribution", {}).get("no_movement_spu") or 0),
                },
                {
                    "label": "健康SPU",
                    "value": int(spu_health.get("problem_distribution", {}).get("healthy_spu") or 0),
                },
            ],
            "coverage": [
                {"label": "整体可售天数", "value": _to_number(metrics.get("stocking_coverage_days")), "min": 90, "max": 150},
                {"label": "在途+可售天数", "value": _to_number(metrics.get("overseas_coverage_days")), "min": 60, "max": 100},
            ],
            "aging": [
                {"label": "国内90天+", "value": _to_number(metrics.get("domestic_aged_90_qty")) or 0},
                {"label": "海外90天+", "value": _to_number(metrics.get("overseas_aged_90_qty")) or 0},
                {"label": "12个月+", "value": _to_number(metrics.get("aged_12m_qty")) or 0},
            ],
        }


def _to_number(value: Any) -> float | int | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else round(number, 2)


def _fmt_num(value: Any) -> str:
    number = _to_number(value)
    if number is None:
        return "-"
    return f"{number:,.1f}" if isinstance(number, float) else f"{number:,}"


def _diagnosis_label(value: Any) -> str:
    return {
        "缺货预警": "保供风险",
        "限制备货": "库存过量",
        "无销量": "无动销",
        "正常": "健康",
    }.get(str(value or ""), str(value or "未标记"))


def _safe_days(qty: Any, demand_daily: Any) -> float | int | None:
    try:
        demand = float(demand_daily or 0)
        if demand <= 0:
            return None
        number = round(float(qty or 0) / demand, 2)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number
