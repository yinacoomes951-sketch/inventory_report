from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .schemas import ExceptionRow, HealthResponse, InventoryRun, ReportDetail, ReportRow, RunOnceResponse, RunSummary
from .service import InventoryReportService


def get_service() -> InventoryReportService:
    return InventoryReportService()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Inventory Diagnosis API",
        version="0.1.0",
        description="MVP1 backend for AI inventory report execution monitoring.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
        return HealthResponse(mockData=settings.use_mock_data)

    @app.post("/api/inventory-runs/run-once", response_model=RunOnceResponse)
    def run_once(service: InventoryReportService = Depends(get_service)) -> RunOnceResponse:
        return service.run_once()

    @app.get("/api/inventory-runs/latest/summary", response_model=RunSummary)
    def latest_summary(service: InventoryReportService = Depends(get_service)) -> RunSummary:
        return service.get_summary()

    @app.get("/api/inventory-runs", response_model=list[InventoryRun])
    def list_runs(service: InventoryReportService = Depends(get_service)) -> list[InventoryRun]:
        return service.list_runs()

    @app.get("/api/inventory-runs/{run_id}/reports", response_model=list[ReportRow])
    def list_reports(run_id: str, service: InventoryReportService = Depends(get_service)) -> list[ReportRow]:
        return service.list_reports(run_id)

    @app.get("/api/inventory-reports/{report_id}", response_model=ReportDetail)
    def get_report(report_id: str, service: InventoryReportService = Depends(get_service)) -> ReportDetail:
        return service.get_report(report_id)

    @app.get("/api/inventory-reports/{report_id}/diagnosis")
    def get_report_diagnosis(report_id: str, service: InventoryReportService = Depends(get_service)) -> dict[str, object]:
        return service.get_diagnosis(report_id)

    @app.get("/api/inventory-runs/{run_id}/exceptions", response_model=list[ExceptionRow])
    def list_exceptions(run_id: str, service: InventoryReportService = Depends(get_service)) -> list[ExceptionRow]:
        return service.list_exceptions(run_id)

    @app.get("/api/inventory-source/contract")
    def source_contract(service: InventoryReportService = Depends(get_service)) -> dict[str, object]:
        return service.source_contract()

    @app.get("/api/inventory-llm/status")
    def llm_status(service: InventoryReportService = Depends(get_service)) -> dict[str, object]:
        return service.llm_status()

    return app


app = create_app()
