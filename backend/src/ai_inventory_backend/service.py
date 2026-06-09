from datetime import datetime

from .repository import InventoryRepository
from .schemas import ExceptionRow, InventoryRun, ReportDetail, ReportRow, RunOnceResponse, RunSummary


class InventoryReportService:
    def __init__(self, repository: InventoryRepository | None = None):
        self.repository = repository or InventoryRepository()

    def run_once(self) -> RunOnceResponse:
        run_id = f"manual-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        return RunOnceResponse(
            runId=run_id,
            status="completed",
            message="MVP1已触发一次模拟报告任务；真实库存读取与AI诊断将在数据库和prompt就绪后接入。",
        )

    def get_summary(self) -> RunSummary:
        return self.repository.get_summary()

    def list_runs(self) -> list[InventoryRun]:
        return self.repository.list_runs()

    def list_reports(self, run_id: str) -> list[ReportRow]:
        return self.repository.list_reports(run_id)

    def get_report(self, report_id: str) -> ReportDetail:
        return self.repository.get_report(report_id)

    def get_diagnosis(self, report_id: str) -> dict[str, object]:
        return self.repository.get_diagnosis(report_id)

    def list_exceptions(self, run_id: str) -> list[ExceptionRow]:
        return self.repository.list_exceptions(run_id)

    def source_contract(self) -> dict[str, object]:
        return self.repository.source_contract()

    def llm_status(self) -> dict[str, object]:
        return self.repository.llm_status()
