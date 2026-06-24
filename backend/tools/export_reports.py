from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path


BASE_URL = "http://127.0.0.1:8001"


def fetch_json(path: str) -> dict | list:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "generated_reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    reports = fetch_json("/api/inventory-runs/latest/reports")
    generated = []
    for report in reports:
        detail = fetch_json(f"/api/inventory-reports/{report['id']}")
        path = output_dir / f"{detail['id']}.html"
        path.write_text(_html_page(detail), encoding="utf-8")
        generated.append(
            {
                "id": detail["id"],
                "level": detail["level"],
                "objectName": detail["objectName"],
                "riskLevel": detail["riskLevel"],
                "path": str(path),
            }
        )

    print(json.dumps(generated, ensure_ascii=False, indent=2))
    return 0


def _html_page(detail: dict) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{detail["title"]}</title>
<style>body{{padding:24px;background:#f6f8fb}}.report-page{{max-width:1180px;margin:0 auto}}.html-card{{box-sizing:border-box}}</style>
</head>
<body>
<main class="report-page html-card">
<h1>{detail["title"]}</h1>
<p class="muted">批次：{detail["batchKey"]} | 风险等级：{detail["riskLevel"]} | 推送状态：待集成</p>
{detail["htmlContent"]}
</main>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
