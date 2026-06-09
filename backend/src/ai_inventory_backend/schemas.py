from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

RunStatus = Literal["pending", "running", "completed", "partial_failed", "failed"]
ReportStatus = Literal["generated", "failed", "data_insufficient"]
DeliveryStatus = Literal["not_integrated", "pending", "success", "failed"]
ClickStatus = Literal["not_tracked", "not_clicked", "clicked"]
RiskLevel = Literal["high", "medium", "low"]


class RunSummary(BaseModel):
    latestBatch: str
    reportCount: int
    pushSuccessRate: float
    clickRate: float
    exceptionCount: int


class InventoryRun(BaseModel):
    id: str
    batchKey: str
    startedAt: str
    finishedAt: str
    status: RunStatus
    reportCount: int
    pushSuccessRate: float
    clickRate: float
    exceptionCount: int


class ReportRow(BaseModel):
    id: str
    objectName: str
    level: str
    reportStatus: ReportStatus
    pushStatus: DeliveryStatus
    clickStatus: ClickStatus
    clickCount: int
    lastClickedAt: str | None


class ExceptionRow(BaseModel):
    id: str
    createdAt: str
    objectName: str
    type: str
    reason: str
    suggestion: str


class ReportDetail(BaseModel):
    id: str
    title: str
    objectName: str
    level: str
    batchKey: str
    riskLevel: RiskLevel
    htmlContent: str


class RunOnceResponse(BaseModel):
    runId: str
    status: RunStatus
    message: str


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "ai-inventory-backend"
    mockData: bool
    checkedAt: datetime = Field(default_factory=datetime.utcnow)
