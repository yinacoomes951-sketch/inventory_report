from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .config import Settings


class InventoryLlmReportEnhancer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_key = (
            settings.llm_api_key
            or os.getenv("AI_INVENTORY_LLM_API_KEY", "")
            or os.getenv("DEEPSEEK_API_KEY", "")
            or os.getenv("OPENAI_API_KEY", "")
        ).strip()
        self.base_url = (
            os.getenv("AI_INVENTORY_LLM_BASE_URL", "")
            or settings.llm_base_url
            or os.getenv("DEEPSEEK_BASE_URL", "")
        ).strip()
        self.model = (
            os.getenv("AI_INVENTORY_LLM_MODEL", "")
            or settings.llm_model
            or os.getenv("DEEPSEEK_MODEL", "")
            or "deepseek-chat"
        ).strip()

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.settings.llm_enabled,
            "configured": bool(self.api_key),
            "baseUrl": self._masked_base_url(),
            "model": self.model,
            "mode": "llm_enhanced" if self.settings.llm_enabled and self.api_key else "rule_renderer",
        }

    def enhance_html(self, diagnosis: dict[str, Any], fallback_html: str) -> str:
        if not self.settings.llm_enabled or not self.api_key:
            return fallback_html
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": self._user_prompt(diagnosis, fallback_html)},
            ],
        }
        request = urllib.request.Request(
            url=f"{self._normalized_base_url()}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.llm_timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return fallback_html
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        html = self._extract_html(content)
        if not html:
            return fallback_html
        return self._restore_required_sections(html, fallback_html)

    def _system_prompt(self) -> str:
        return (
            "你是Amazon库存诊断报告专家。你只能基于用户提供的结构化诊断JSON和规则报告改写表达，"
            "不得发明新SKU、新字段、新数字或外部原因。输出只能是HTML片段，根节点必须是"
            "<section class=\"report-html real-inventory-report llm-enhanced\">。"
            "必须包含：核心结论、库存健康总览、图表概览、TOP问题、核心影响SPU、排查路径、呆滞与清仓风险、BI排查建议、行动清单。"
        )

    def _user_prompt(self, diagnosis: dict[str, Any], fallback_html: str) -> str:
        analysis_skill, report_skill = self._load_skill_docs()
        compact_diagnosis = self._compact_diagnosis(diagnosis)
        return (
            "请根据两个skill要求，把结构化诊断润色成更适合运营阅读的HTML报告。\n\n"
            "【库存诊断分析思路Skill】\n"
            f"{analysis_skill}\n\n"
            "【库存报告表达Skill】\n"
            f"{report_skill}\n\n"
            "【结构化诊断JSON】\n"
            f"{json.dumps(compact_diagnosis, ensure_ascii=False)}\n\n"
            "【当前规则HTML，可参考但不要照抄】\n"
            f"{fallback_html[:12000]}\n\n"
            "要求：\n"
            "1. 不新增任何JSON里没有的数字或SKU。\n"
            "2. 每个TOP问题都要说明为什么痛、先查什么、建议动作。\n"
            "3. 不在报告正文展开SKU明细，只提供BI下钻排查建议。\n"
            "4. 不输出Markdown，不输出解释，只输出HTML片段。"
        )

    def _load_skill_docs(self) -> tuple[str, str]:
        root = Path(__file__).resolve().parents[3]
        docs = root / "docs"
        return (
            _read_limited(docs / "inventory_analysis_skill.md"),
            _read_limited(docs / "inventory_report_skill.md"),
        )

    def _compact_diagnosis(self, diagnosis: dict[str, Any]) -> dict[str, Any]:
        compact = dict(diagnosis)
        compact["top_skus"] = diagnosis.get("top_skus", [])[:12]
        compact["warning_distribution"] = diagnosis.get("warning_distribution", [])[:8]
        compact["problems"] = diagnosis.get("problems", [])[:5]
        return compact

    def _extract_html(self, content: str) -> str:
        cleaned = content.strip()
        cleaned = re.sub(r"^```(?:html)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        if "<section" not in cleaned or "</section>" not in cleaned:
            return ""
        cleaned = re.sub(r"<script\b[^>]*>.*?</script>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"\son[a-zA-Z]+\s*=\s*(['\"]).*?\1", "", cleaned)
        return cleaned

    def _restore_required_sections(self, llm_html: str, fallback_html: str) -> str:
        required_titles = [
            "核心结论",
            "库存健康总览",
            "图表概览",
            "TOP问题",
            "核心影响SPU",
            "排查路径",
            "呆滞与清仓风险",
            "BI排查建议",
            "行动清单",
        ]
        restored = llm_html
        inserts = []
        for title in required_titles:
            if f"<h2>{title}</h2>" in restored:
                continue
            section = self._find_section(fallback_html, title)
            if section:
                inserts.append(section)
        if inserts and "</section>" in restored:
            restored = restored.replace("</section>", "\n".join(inserts) + "\n</section>", 1)
        return restored

    def _find_section(self, html_text: str, title: str) -> str:
        pattern = rf"<h2>{re.escape(title)}</h2>.*?(?=<h2>|</section>)"
        match = re.search(pattern, html_text, flags=re.DOTALL)
        return match.group(0).strip() if match else ""

    def _normalized_base_url(self) -> str:
        if not self.base_url:
            return "https://api.deepseek.com/v1"
        if self.base_url.rstrip("/").endswith("/v1"):
            return self.base_url.rstrip("/")
        return self.base_url.rstrip("/") + "/v1"

    def _masked_base_url(self) -> str:
        return self.base_url.rstrip("/") if self.base_url else ""


def _read_limited(path: Path, limit: int = 12000) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")[:limit]
