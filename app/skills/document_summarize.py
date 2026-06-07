from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SkillResult:
    skill_id: str
    name: str
    version: str
    output: dict[str, Any]


class DocumentSummarizeSkill:
    skill_id = "document_summarize"
    name = "DocumentSummarizeSkill"
    version = "v1"
    description = "Summarize plain text into concise bullet points."

    def execute(self, text: str) -> SkillResult:
        cleaned = " ".join(text.split())
        if not cleaned:
            summary = ""
            bullets: list[str] = []
        else:
            normalized = (
                cleaned.replace("。", "。\n")
                .replace("！", "！\n")
                .replace("？", "？\n")
            )
            segments = normalized.splitlines()
            candidates = [segment.strip() for segment in segments if segment.strip()]
            if not candidates:
                candidates = [cleaned]
            bullets = candidates[:5]
            summary = "；".join(bullets[:3])

        return SkillResult(
            skill_id=self.skill_id,
            name=self.name,
            version=self.version,
            output={
                "summary": summary,
                "bullets": bullets,
                "length": len(text),
            },
        )
