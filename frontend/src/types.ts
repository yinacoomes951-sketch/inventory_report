export type RunStatus = 'completed' | 'partial_failed' | 'failed' | 'running';
export type ReportStatus = 'generated' | 'failed' | 'data_insufficient';
export type DeliveryStatus = 'not_integrated' | 'pending' | 'success' | 'failed';
export type ClickStatus = 'not_tracked' | 'not_clicked' | 'clicked';

export interface RunSummary {
  latestBatch: string;
  reportCount: number;
  pushSuccessRate: number;
  clickRate: number;
  exceptionCount: number;
}

export interface InventoryRun {
  id: string;
  batchKey: string;
  startedAt: string;
  finishedAt: string;
  status: RunStatus;
  reportCount: number;
  pushSuccessRate: number;
  clickRate: number;
  exceptionCount: number;
}

export interface ReportRow {
  id: string;
  objectName: string;
  level: string;
  reportStatus: ReportStatus;
  pushStatus: DeliveryStatus;
  clickStatus: ClickStatus;
  clickCount: number;
  lastClickedAt: string | null;
}

export interface ExceptionRow {
  id: string;
  createdAt: string;
  objectName: string;
  type: string;
  reason: string;
  suggestion: string;
}

export interface ReportDetail {
  id: string;
  title: string;
  objectName: string;
  level: string;
  batchKey: string;
  riskLevel: 'high' | 'medium' | 'low';
  htmlContent: string;
}
