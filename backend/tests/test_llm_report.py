import json
import urllib.error
import urllib.request
from types import SimpleNamespace

from ai_inventory_backend.llm_report import InventoryLlmReportEnhancer


FALLBACK_HTML = '<section class="report-html real-inventory-report"><h2>fallback</h2></section>'
LLM_HTML = '<section class="report-html real-inventory-report llm-enhanced"><h2>fallback</h2></section>'


def test_enhance_html_marks_rule_and_logs_when_disabled(caplog):
    enhancer = InventoryLlmReportEnhancer(_settings(llm_enabled=False, api_key=""))

    with caplog.at_level("INFO"):
        result = enhancer.enhance_html(_diagnosis(), FALLBACK_HTML)

    assert result.startswith("<!-- inventory-report-source: rule -->")
    assert FALLBACK_HTML in result
    assert "LLM enhance_html skipped: disabled_or_missing_key" in caplog.text


def test_enhance_html_marks_llm_and_logs_success(monkeypatch, caplog):
    enhancer = InventoryLlmReportEnhancer(_settings(llm_enabled=True, api_key="key"))
    payload = {"choices": [{"message": {"content": LLM_HTML}}]}
    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: _Response(payload))

    with caplog.at_level("INFO"):
        result = enhancer.enhance_html(_diagnosis(), FALLBACK_HTML)

    assert result.startswith("<!-- inventory-report-source: llm -->")
    assert LLM_HTML in result
    assert "LLM enhance_html request started" in caplog.text
    assert "LLM enhance_html succeeded" in caplog.text


def test_enhance_html_marks_rule_and_logs_request_failure(monkeypatch, caplog):
    enhancer = InventoryLlmReportEnhancer(_settings(llm_enabled=True, api_key="key"))

    def raise_error(request, timeout):
        raise urllib.error.URLError("network failed")

    monkeypatch.setattr(urllib.request, "urlopen", raise_error)

    with caplog.at_level("INFO"):
        result = enhancer.enhance_html(_diagnosis(), FALLBACK_HTML)

    assert result.startswith("<!-- inventory-report-source: rule -->")
    assert FALLBACK_HTML in result
    assert "LLM enhance_html request started" in caplog.text
    assert "LLM enhance_html fallback: request_failed" in caplog.text


def test_enhance_html_marks_rule_and_logs_invalid_html(monkeypatch, caplog):
    enhancer = InventoryLlmReportEnhancer(_settings(llm_enabled=True, api_key="key"))
    payload = {"choices": [{"message": {"content": "not html"}}]}
    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: _Response(payload))

    with caplog.at_level("INFO"):
        result = enhancer.enhance_html(_diagnosis(), FALLBACK_HTML)

    assert result.startswith("<!-- inventory-report-source: rule -->")
    assert FALLBACK_HTML in result
    assert "LLM enhance_html request started" in caplog.text
    assert "LLM enhance_html fallback: invalid_html" in caplog.text


def test_enhance_html_logs_open_section_without_close_section(monkeypatch, caplog):
    enhancer = InventoryLlmReportEnhancer(_settings(llm_enabled=True, api_key="key"))
    content = (
        '<section class="report-html real-inventory-report llm-enhanced">'
        "<h2>fallback</h2>"
        f"<p>{'x' * 400}</p>"
    )
    payload = {"choices": [{"message": {"content": content}}]}
    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: _Response(payload))

    with caplog.at_level("INFO"):
        result = enhancer.enhance_html(_diagnosis(), FALLBACK_HTML)

    assert result.startswith("<!-- inventory-report-source: rule -->")
    assert FALLBACK_HTML in result
    assert "LLM enhance_html fallback: invalid_html" in caplog.text


class _Response:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


def _settings(llm_enabled: bool, api_key: str) -> SimpleNamespace:
    return SimpleNamespace(
        llm_enabled=llm_enabled,
        llm_api_key=api_key,
        llm_base_url="https://example.test",
        llm_model="test-model",
        llm_timeout_seconds=1,
    )


def _diagnosis() -> dict[str, object]:
    return {
        "top_skus": [],
        "warning_distribution": [],
        "problems": [],
    }
