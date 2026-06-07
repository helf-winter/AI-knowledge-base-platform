from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SkillResult:
    skill_id: str
    name: str
    version: str
    output: dict[str, Any]


class KnowledgeExtractSkill:
    skill_id = "knowledge_extract"
    name = "KnowledgeExtractSkill"
    version = "v1"
    description = "Extract structured knowledge items from text."

    def execute(self, text: str, source: str | None = None) -> SkillResult:
        cleaned = " ".join(text.split())
        if not cleaned:
            items: list[dict[str, Any]] = []
        else:
            sentences = [part.strip() for part in cleaned.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").splitlines() if part.strip()]
            if not sentences:
                sentences = [cleaned]
            items = []
            for idx, sentence in enumerate(sentences[:5]):
                items.append(
                    {
                        "title": f"知识条目 {idx + 1}",
                        "content": sentence,
                        "source": source,
                        "confidence": round(max(0.55, 0.95 - idx * 0.08), 2),
                    }
                )

        return SkillResult(
            skill_id=self.skill_id,
            name=self.name,
            version=self.version,
            output={
                "items": items,
                "count": len(items),
                "source": source,
            },
        )
