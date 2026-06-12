from __future__ import annotations

import hashlib
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import Settings
from .diagnosis import InventoryDiagnosisEngine, RoleScope
from .llm_report import InventoryLlmReportEnhancer
from .mock_data import EXCEPTIONS, REPORT_DETAIL, REPORTS, RUNS, SUMMARY
from .report_renderer import InventoryReportRenderer
from .schemas import ExceptionRow, InventoryRun, ReportDetail, ReportRow, RunSummary
from .source_fields import REQUIRED_SOURCE_FIELDS, SOURCE_TABLE


def _load_project_env() -> None:
    project_root = Path(__file__).resolve().parents[3]
    for env_path in (project_root / ".env", project_root / "backend" / ".env"):
        if not env_path.exists():
            continue
        with env_path.open(encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


class InventoryRepository:
    def __init__(self, settings: Settings | None = None, engine: Engine | None = None):
        _load_project_env()
        self.settings = settings or Settings()
        self.database_url = (
            self.settings.database_url
            or os.getenv("AI_INVENTORY_DATABASE_URL", "")
            or os.getenv("DATABASE_URL", "")
        )
        self.use_mock_data = self.settings.use_mock_data or not self.database_url
        self.engine = engine or (
            create_engine(self.database_url, pool_pre_ping=True) if not self.use_mock_data else None
        )
        self.diagnosis_engine = InventoryDiagnosisEngine()
        self.report_renderer = InventoryReportRenderer()
        self.llm_enhancer = InventoryLlmReportEnhancer(self.settings)

    def get_summary(self) -> RunSummary:
        if self.use_mock_data:
            return SUMMARY
        batch = self._latest_batch()
        scopes = self._build_scopes(batch)
        exception_count = self._exception_count(batch)
        return RunSummary(
            latestBatch=batch["batch_key"],
            reportCount=len(scopes),
            pushSuccessRate=0.0,
            clickRate=0.0,
            exceptionCount=exception_count,
        )

    def list_runs(self) -> list[InventoryRun]:
        if self.use_mock_data:
            return RUNS
        batch = self._latest_batch()
        scopes = self._build_scopes(batch)
        return [
            InventoryRun(
                id=batch["run_id"],
                batchKey=batch["batch_key"],
                startedAt=batch["started_at"],
                finishedAt=batch["finished_at"],
                status="completed",
                reportCount=len(scopes),
                pushSuccessRate=0.0,
                clickRate=0.0,
                exceptionCount=self._exception_count(batch),
            )
        ]

    def list_reports(self, run_id: str) -> list[ReportRow]:
        if self.use_mock_data:
            return REPORTS
        batch = self._latest_batch()
        scopes = self._build_scopes(batch)
        return [
            ReportRow(
                id=scope.id,
                objectName=scope.object_name,
                level=scope.level,
                reportStatus="generated",
                pushStatus="not_integrated",
                clickStatus="not_tracked",
                clickCount=0,
                lastClickedAt=None,
            )
            for scope in scopes
        ]

    def list_exceptions(self, run_id: str) -> list[ExceptionRow]:
        if self.use_mock_data:
            return EXCEPTIONS
        batch = self._latest_batch()
        issues = []
        if self._exception_count(batch) > 0:
            issues.append(
                ExceptionRow(
                    id="real-warning-rows",
                    createdAt=batch["finished_at"],
                    objectName="真实库存批次",
                    type="库存预警",
                    reason="最新批次存在缺货预警或限制备货SKU，需要在报告中优先处理。",
                    suggestion="按角色报告查看风险SKU证据，先处理缺货预警，再处理限制备货和无销量。",
                )
            )
        return issues

    def get_report(self, report_id: str) -> ReportDetail:
        if self.use_mock_data:
            return REPORT_DETAIL.model_copy(update={"id": report_id})
        batch = self._latest_batch()
        scopes = {scope.id: scope for scope in self._build_scopes(batch)}
        scope = scopes.get(report_id)
        if scope is None:
            scope = self._build_scopes(batch)[-1]
        report = self._build_report_detail(batch, scope)
        return report

    def get_diagnosis(self, report_id: str) -> dict[str, Any]:
        if self.use_mock_data:
            return {
                "scope": {
                    "level": REPORT_DETAIL.level,
                    "object_name": REPORT_DETAIL.objectName,
                    "batch_key": REPORT_DETAIL.batchKey,
                },
                "summary": {
                    "risk_level": REPORT_DETAIL.riskLevel,
                    "headline": "MVP mock diagnosis",
                    "key_counts": {"sku_count": 2, "shortage_count": 1, "limited_restock_count": 1, "no_sales_count": 0},
                    "totals": {},
                },
                "problems": [],
                "warning_distribution": [],
                "top_skus": [],
                "action_list": {"today": [], "this_week": [], "human_check": []},
            }
        batch = self._latest_batch()
        scopes = {scope.id: scope for scope in self._build_scopes(batch)}
        scope = scopes.get(report_id) or self._build_scopes(batch)[-1]
        return self._build_diagnosis(batch, scope)

    def source_contract(self) -> dict[str, object]:
        return {
            "table": SOURCE_TABLE,
            "requiredFields": list(REQUIRED_SOURCE_FIELDS),
            "mode": "mock_contract" if self.use_mock_data else "real_readonly",
        }

    def llm_status(self) -> dict[str, Any]:
        return self.llm_enhancer.status()

    def _connect(self):
        if self.engine is None:
            raise RuntimeError("Inventory database engine is not configured.")
        return self.engine.connect()

    def _latest_batch(self) -> dict[str, str]:
        with self._connect() as conn:
            row = conn.execute(
                text(
                    """
                    select max(insert_time) as insert_time
                    from lx_ads.ads_lx_kd_inventory_sku_calc
                    """
                )
            ).mappings().one()
        insert_time = row["insert_time"]
        if insert_time is None:
            raise RuntimeError("库存源表没有 insert_time 批次数据。")
        finished_at = _fmt_dt(insert_time)
        batch_key = f"inventory-{insert_time:%Y%m%d-%H%M%S}"
        return {
            "insert_time": insert_time,
            "batch_key": batch_key,
            "run_id": f"run-{batch_key}",
            "started_at": finished_at,
            "finished_at": finished_at,
        }

    def _build_scopes(self, batch: dict[str, Any]) -> list[RoleScope]:
        owner = self._top_dimension(batch, "归属")
        department = self._top_dimension(batch, "部门名称")
        scopes = [
            RoleScope(
                id=f"real-owner-{_slug(owner)}",
                level="运营个人",
                object_name=owner,
                where_sql='and "归属" = :owner',
                params={"owner": owner},
            ),
            RoleScope(
                id=f"real-department-{_slug(department)}",
                level="战队/部门",
                object_name=department,
                where_sql='and "部门名称" = :department',
                params={"department": department},
            ),
            RoleScope(
                id="real-director-all",
                level="运营总监",
                object_name="运营总监视角（全量）",
                where_sql="",
                params={},
            ),
        ]
        return scopes

    def _top_dimension(self, batch: dict[str, Any], column: str) -> str:
        with self._connect() as conn:
            row = conn.execute(
                text(
                    f"""
                    select coalesce("{column}", '未归属') as name,
                           sum(case
                               when "备货预警" = '缺货预警' then 100
                               when "备货预警" = '限制备货' then 60
                               when "备货预警" = '无销量' then 30
                               else 1
                           end) as risk_score,
                           count(*) as sku_count
                    from lx_ads.ads_lx_kd_inventory_sku_calc
                    where insert_time = :insert_time
                    group by 1
                    order by risk_score desc, sku_count desc
                    limit 1
                    """
                ),
                {"insert_time": batch["insert_time"]},
            ).mappings().one()
        return str(row["name"] or "未归属")

    def _exception_count(self, batch: dict[str, Any]) -> int:
        with self._connect() as conn:
            count = conn.execute(
                text(
                    """
                    select count(*)
                    from lx_ads.ads_lx_kd_inventory_sku_calc
                    where insert_time = :insert_time
                      and "备货预警" in ('缺货预警', '限制备货')
                    """
                ),
                {"insert_time": batch["insert_time"]},
            ).scalar_one()
        return int(count or 0)

    def _build_report_detail(self, batch: dict[str, Any], scope: RoleScope) -> ReportDetail:
        diagnosis = self._build_diagnosis(batch, scope)
        fallback_html = self.report_renderer.render_html(diagnosis)
        html_content = self.llm_enhancer.enhance_html(diagnosis, fallback_html)
        return ReportDetail(
            id=scope.id,
            title=f"{scope.object_name} / {scope.level} / 真实库存诊断报告",
            objectName=scope.object_name,
            level=scope.level,
            batchKey=batch["batch_key"],
            riskLevel=diagnosis["summary"]["risk_level"],
            htmlContent=html_content,
        )

    def _build_diagnosis(self, batch: dict[str, Any], scope: RoleScope) -> dict[str, Any]:
        metrics = self._scope_metrics(batch, scope)
        warnings = self._warning_distribution(batch, scope)
        spu_health = self._spu_health(batch, scope)
        top_skus = self._top_risk_skus(batch, scope)
        return self.diagnosis_engine.build(
            scope=scope,
            batch_key=batch["batch_key"],
            metrics=metrics,
            warnings=warnings,
            spu_health=spu_health,
            top_skus=top_skus,
        )

    def _scope_metrics(self, batch: dict[str, Any], scope: RoleScope) -> dict[str, Any]:
        sql = f"""
            select count(*) as sku_count,
                   count(distinct spu) as spu_count,
                   count(distinct "归属") as owner_count,
                   count(distinct "部门名称") as department_count,
                   sum(coalesce("总库存", 0)) as total_inventory,
                   sum(coalesce("建议备货量", 0)) as suggested_restock_qty,
                   avg(nullif("可售天数", 0)) as avg_sellable_days,
                   avg(nullif("建议可售天数", 0)) as avg_suggested_sellable_days,
                   sum(coalesce("最近30天总销量", 0)) as sales_30d,
                   sum(coalesce("预测日销", 0)) as demand_daily,
                   sum(coalesce("fba可售", 0)) as fba_available,
                   sum(coalesce("awd可用", 0)) as awd_available,
                   sum(coalesce("国外合计", 0)) as overseas_ready_qty,
                   sum(coalesce("国内总数量", 0)) as domestic_total_qty,
                   sum(coalesce("采购在途", 0)) as purchase_in_transit_qty,
                   sum(coalesce("采购计划", 0)) as purchase_plan_qty,
                   sum(coalesce("国内库龄_90_180", 0) + coalesce("国内库龄_180_270", 0) +
                       coalesce("国内库龄_270_330", 0) + coalesce("国内库龄_330_365", 0) +
                       coalesce("国内库龄_365以上", 0)) as domestic_aged_90_qty,
                   sum(coalesce("国内库龄_180_270", 0) + coalesce("国内库龄_270_330", 0) +
                       coalesce("国内库龄_330_365", 0) + coalesce("国内库龄_365以上", 0)) as domestic_aged_qty,
                   sum(coalesce("3_6个月库龄", 0) + coalesce("6_9个月库龄", 0) +
                       coalesce("9_11个月库龄", 0) + coalesce("11_12个月库龄", 0) +
                       coalesce("12个月以上库龄", 0)) as overseas_aged_90_qty,
                   sum(coalesce("6_9个月库龄", 0) + coalesce("9_11个月库龄", 0) +
                       coalesce("11_12个月库龄", 0) + coalesce("12个月以上库龄", 0)) as overseas_aged_qty,
                   sum(coalesce("国内库龄_365以上", 0) + coalesce("12个月以上库龄", 0)) as aged_12m_qty,
                   sum(case when "备货预警" = '缺货预警' then 1 else 0 end) as shortage_count,
                   sum(case when "备货预警" = '限制备货' then 1 else 0 end) as limited_count,
                   sum(case when "备货预警" = '无销量' then 1 else 0 end) as no_sales_count,
                   sum(case when "备货预警" = '正常' then 1 else 0 end) as normal_count
            from lx_ads.ads_lx_kd_inventory_sku_calc
            where insert_time = :insert_time
            {scope.where_sql}
        """
        params = {"insert_time": batch["insert_time"], **scope.params}
        with self._connect() as conn:
            row = conn.execute(text(sql), params).mappings().one()
        metrics = {key: _to_float(value) for key, value in dict(row).items()}
        metrics["stocking_inventory_qty"] = metrics.get("total_inventory") or 0
        metrics["stocking_coverage_days"] = _safe_days(metrics.get("stocking_inventory_qty"), metrics.get("demand_daily"))
        metrics["overseas_coverage_days"] = _safe_days(metrics.get("overseas_ready_qty"), metrics.get("demand_daily"))
        metrics["domestic_coverage_days"] = _safe_days(metrics.get("domestic_total_qty"), metrics.get("demand_daily"))
        metrics["aged_inventory_qty"] = (metrics.get("domestic_aged_qty") or 0) + (metrics.get("overseas_aged_qty") or 0)
        metrics["aged_90_qty"] = (metrics.get("domestic_aged_90_qty") or 0) + (metrics.get("overseas_aged_90_qty") or 0)
        return metrics

    def _spu_health(self, batch: dict[str, Any], scope: RoleScope) -> dict[str, Any]:
        sql = f"""
            select *,
                   case
                     when demand_daily <= 0 and total_inventory > 0 then 'stagnant'
                     when stocking_coverage_days is not null and stocking_coverage_days < 90 then 'unhealthy'
                     when overseas_coverage_days is not null and overseas_coverage_days < 60 then 'unhealthy'
                     when stocking_coverage_days is not null and stocking_coverage_days > 150 then 'local_warning'
                     when overseas_coverage_days is not null and overseas_coverage_days > 100 then 'local_warning'
                     when aged_90_qty > 0 then 'local_warning'
                     else 'healthy'
                   end as health_status,
                   (
                     case
                       when stocking_coverage_days is null then 0
                       when stocking_coverage_days < 90 then (90 - stocking_coverage_days) * 8
                       when stocking_coverage_days > 150 then (stocking_coverage_days - 150) * 3
                       else 0
                     end
                     + case
                       when overseas_coverage_days is null then 0
                       when overseas_coverage_days < 60 then (60 - overseas_coverage_days) * 7
                       when overseas_coverage_days > 100 then (overseas_coverage_days - 100) * 3
                       else 0
                     end
                     + case when demand_daily <= 0 and total_inventory > 0 then 160 else 0 end
                     + least(aged_90_qty / 100.0, 80)
                   ) as impact_score
            from (
                select spu,
                       min("产品名称") as product_name,
                       count(*) as sku_count,
                       sum(coalesce("总库存", 0)) as total_inventory,
                       sum(coalesce("最近30天总销量", 0)) as sales_30d,
                       sum(coalesce("建议备货量", 0)) as suggested_restock_qty,
                       sum(coalesce("预测日销", 0)) as demand_daily,
                       sum(coalesce("国外合计", 0)) as overseas_ready_qty,
                       sum(coalesce("国内总数量", 0)) as domestic_total_qty,
                       sum(coalesce("采购在途", 0)) as purchase_in_transit_qty,
                       sum(coalesce("采购计划", 0)) as purchase_plan_qty,
                       sum(coalesce("国内库龄_90_180", 0) + coalesce("国内库龄_180_270", 0) +
                           coalesce("国内库龄_270_330", 0) + coalesce("国内库龄_330_365", 0) +
                           coalesce("国内库龄_365以上", 0)) as domestic_aged_90_qty,
                       sum(coalesce("国内库龄_180_270", 0) + coalesce("国内库龄_270_330", 0) +
                           coalesce("国内库龄_330_365", 0) + coalesce("国内库龄_365以上", 0)) as domestic_aged_qty,
                       sum(coalesce("3_6个月库龄", 0) + coalesce("6_9个月库龄", 0) +
                           coalesce("9_11个月库龄", 0) + coalesce("11_12个月库龄", 0) +
                           coalesce("12个月以上库龄", 0)) as overseas_aged_90_qty,
                       sum(coalesce("6_9个月库龄", 0) + coalesce("9_11个月库龄", 0) +
                           coalesce("11_12个月库龄", 0) + coalesce("12个月以上库龄", 0)) as overseas_aged_qty,
                       sum(coalesce("国内库龄_90_180", 0) + coalesce("国内库龄_180_270", 0) +
                           coalesce("国内库龄_270_330", 0) + coalesce("国内库龄_330_365", 0) +
                           coalesce("国内库龄_365以上", 0) + coalesce("3_6个月库龄", 0) +
                           coalesce("6_9个月库龄", 0) + coalesce("9_11个月库龄", 0) +
                           coalesce("11_12个月库龄", 0) + coalesce("12个月以上库龄", 0)) as aged_90_qty,
                       sum(coalesce("国内库龄_365以上", 0) + coalesce("12个月以上库龄", 0)) as aged_12m_qty,
                       sum(case when "备货预警" = '缺货预警' then 1 else 0 end) as shortage_count,
                       sum(case when "备货预警" = '限制备货' then 1 else 0 end) as limited_count,
                       sum(case when "备货预警" = '无销量' then 1 else 0 end) as no_sales_count,
                       sum(case when "备货预警" = '正常' then 1 else 0 end) as normal_count,
                       round((sum(coalesce("国外合计", 0)) / nullif(sum(coalesce("预测日销", 0)), 0))::numeric, 2) as overseas_coverage_days,
                       round((sum(coalesce("国内总数量", 0)) / nullif(sum(coalesce("预测日销", 0)), 0))::numeric, 2) as domestic_coverage_days,
                       round((sum(coalesce("总库存", 0)) /
                           nullif(sum(coalesce("预测日销", 0)), 0))::numeric, 2) as stocking_coverage_days
                from lx_ads.ads_lx_kd_inventory_sku_calc
                where insert_time = :insert_time
                {scope.where_sql}
                group by spu
            ) s
            order by impact_score desc, sales_30d desc
        """
        params = {"insert_time": batch["insert_time"], **scope.params}
        with self._connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        all_spus = [{key: _to_float(value) for key, value in dict(row).items()} for row in rows]
        distribution = {"healthy": 0, "local_warning": 0, "unhealthy": 0, "stagnant": 0}
        problem_distribution = {
            "restock_shortage_spu": 0,
            "restock_excess_spu": 0,
            "shipment_shortage_spu": 0,
            "shipment_excess_spu": 0,
            "no_movement_spu": 0,
            "healthy_spu": 0,
        }
        for row in all_spus:
            distribution[str(row.get("health_status") or "local_warning")] = (
                distribution.get(str(row.get("health_status") or "local_warning"), 0) + 1
            )
            has_problem = False
            if _is_below(row.get("stocking_coverage_days"), 90):
                problem_distribution["restock_shortage_spu"] += 1
                has_problem = True
            if _is_above(row.get("stocking_coverage_days"), 150):
                problem_distribution["restock_excess_spu"] += 1
                has_problem = True
            if _is_below(row.get("overseas_coverage_days"), 60):
                problem_distribution["shipment_shortage_spu"] += 1
                has_problem = True
            if _is_above(row.get("overseas_coverage_days"), 100):
                problem_distribution["shipment_excess_spu"] += 1
                has_problem = True
            if _is_no_movement_spu(row):
                problem_distribution["no_movement_spu"] += 1
                has_problem = True
            if not has_problem:
                problem_distribution["healthy_spu"] += 1
        return {"distribution": distribution, "problem_distribution": problem_distribution, "top_spus": all_spus[:30]}

    def _warning_distribution(self, batch: dict[str, Any], scope: RoleScope) -> list[dict[str, Any]]:
        sql = f"""
            select coalesce("备货预警", '未标记') as warning,
                   count(*) as count,
                   sum(coalesce("建议备货量", 0)) as suggested_restock_qty
            from lx_ads.ads_lx_kd_inventory_sku_calc
            where insert_time = :insert_time
            {scope.where_sql}
            group by 1
            order by count desc
        """
        params = {"insert_time": batch["insert_time"], **scope.params}
        with self._connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [{key: _to_float(value) for key, value in dict(row).items()} for row in rows]

    def _top_risk_skus(self, batch: dict[str, Any], scope: RoleScope) -> list[dict[str, Any]]:
        sql = f"""
            select sku,
                   spu,
                   "产品名称" as product_name,
                   "归属" as owner,
                   "部门名称" as department_name,
                   "区域" as region,
                   "备货预警" as restock_warning,
                   "可售天数" as sellable_days,
                   "建议可售天数" as suggested_sellable_days,
                   "近期日销" as recent_daily_sales,
                   "预测日销" as forecast_daily_sales,
                   "总库存" as total_inventory,
                   "建议备货量" as suggested_restock_qty,
                   "最近30天总销量" as sales_30d,
                   "fba可售" as fba_available,
                   "awd可用" as awd_available,
                   "国内总数量" as domestic_total_qty,
                   coalesce("国外合计", 0) as overseas_ready_qty,
                   (coalesce("国内库龄_180_270", 0) + coalesce("国内库龄_270_330", 0) +
                    coalesce("国内库龄_330_365", 0) + coalesce("国内库龄_365以上", 0)) as domestic_aged_qty,
                   (coalesce("6_9个月库龄", 0) + coalesce("9_11个月库龄", 0) +
                    coalesce("11_12个月库龄", 0) + coalesce("12个月以上库龄", 0)) as overseas_aged_qty,
                   (coalesce("国内库龄_365以上", 0) + coalesce("12个月以上库龄", 0)) as aged_12m_qty
            from lx_ads.ads_lx_kd_inventory_sku_calc
            where insert_time = :insert_time
            {scope.where_sql}
            order by case
                       when "备货预警" = '缺货预警' then 1
                       when "备货预警" = '限制备货' then 2
                       when "备货预警" = '无销量' then 3
                       else 4
                     end,
                     coalesce("建议备货量", 0) desc,
                     coalesce("最近30天总销量", 0) desc
            limit 20
        """
        params = {"insert_time": batch["insert_time"], **scope.params}
        with self._connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [{key: _to_float(value) for key, value in dict(row).items()} for row in rows]


def _to_float(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _fmt_dt(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _slug(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def _safe_days(qty: Any, demand_daily: Any) -> float | None:
    try:
        demand = float(demand_daily or 0)
        if demand <= 0:
            return None
        return round(float(qty or 0) / demand, 2)
    except (TypeError, ValueError):
        return None


def _is_no_movement_spu(row: dict[str, Any]) -> bool:
    total_inventory = float(row.get("total_inventory") or 0)
    if total_inventory <= 0:
        return False
    sales_30d = float(row.get("sales_30d") or 0)
    demand_daily = float(row.get("demand_daily") or 0)
    if sales_30d <= 0 and demand_daily <= 0:
        return True
    return str(row.get("health_status") or "") == "stagnant"


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
