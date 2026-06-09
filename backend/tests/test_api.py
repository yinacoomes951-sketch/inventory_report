from fastapi.testclient import TestClient

from ai_inventory_backend import create_app


client = TestClient(create_app())


def test_health_returns_mock_flag():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ai-inventory-backend"
    assert data["mockData"] is True


def test_latest_summary_contains_required_monitor_metrics():
    response = client.get("/api/inventory-runs/latest/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["latestBatch"] == "2026-W23"
    assert "pushSuccessRate" in data
    assert "clickRate" in data
    assert "exceptionCount" in data


def test_runs_reports_exceptions_and_detail_contracts():
    runs = client.get("/api/inventory-runs")
    assert runs.status_code == 200
    run_id = runs.json()[0]["id"]

    reports = client.get(f"/api/inventory-runs/{run_id}/reports")
    assert reports.status_code == 200
    first_report = reports.json()[0]
    assert first_report["objectName"] == "张三"
    assert first_report["pushStatus"] == "success"

    detail = client.get(f"/api/inventory-reports/{first_report['id']}")
    assert detail.status_code == 200
    assert "SKU-A001" in detail.json()["htmlContent"]

    exceptions = client.get(f"/api/inventory-runs/{run_id}/exceptions")
    assert exceptions.status_code == 200
    assert exceptions.json()[0]["reason"]


def test_run_once_returns_completed_mock_task():
    response = client.post("/api/inventory-runs/run-once")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["runId"].startswith("manual-")


def test_source_contract_exposes_ads_table_and_required_fields():
    response = client.get("/api/inventory-source/contract")
    assert response.status_code == 200
    data = response.json()
    assert data["table"] == "lx_ads.ads_lx_kd_inventory_sku_calc"
    assert "sku" in data["requiredFields"]
    assert "归属" in data["requiredFields"]
    assert "insert_time" in data["requiredFields"]


def test_report_diagnosis_contract():
    response = client.get("/api/inventory-reports/report-owner-zhangsan/diagnosis")
    assert response.status_code == 200
    data = response.json()
    assert data["scope"]["level"]
    assert data["summary"]["risk_level"] in {"high", "medium", "low"}
    assert "problems" in data
    assert "top_skus" in data
    assert "action_list" in data


def test_llm_status_is_safe_and_does_not_expose_key():
    response = client.get("/api/inventory-llm/status")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "enabled" in data
    assert "apiKey" not in data
