import importlib.util
from pathlib import Path


_EXPORT_REPORTS_PATH = Path(__file__).resolve().parents[1] / "tools" / "export_reports.py"
_SPEC = importlib.util.spec_from_file_location("export_reports", _EXPORT_REPORTS_PATH)
assert _SPEC is not None
export_reports = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(export_reports)


def test_export_html_page_uses_embedded_report_styles_without_external_css():
    detail = {
        "id": "report-1",
        "title": "Inventory Report",
        "batchKey": "batch",
        "riskLevel": "medium",
        "htmlContent": (
            "<style data-inventory-report-style>.html-card{background:#fff}</style>"
            '<section class="report-html real-inventory-report"></section>'
        ),
    }

    source = export_reports._html_page(detail)

    assert "../frontend/src/styles.css" not in source
    assert '<link rel="stylesheet"' not in source
    assert "<style data-inventory-report-style>" in source
    assert '<section class="report-html real-inventory-report">' in source
