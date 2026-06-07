from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.flywheel import KnowledgeGap
from app.services.flywheel import KnowledgeFlywheelService
from app.core.skills import SkillRegistry


@dataclass
class LearningInsight:
    topic: str
    count: int
    sample_questions: list[str]
    suggested_title: str
    suggested_content: str
    diff_summary: str


class LearningAgent:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.flywheel = KnowledgeFlywheelService(db)
        self.skills = SkillRegistry(db)

    def analyze_gaps(self, status: str = "pending") -> dict[str, Any]:
        gaps = self.flywheel.list_gaps(status=status)
        if not gaps:
            return {
                "insights": [],
                "total_gaps": 0,
                "status": status,
            }

        grouped: dict[str, list[KnowledgeGap]] = {}
        for gap in gaps:
            key = gap.issue_type or "missing_knowledge"
            grouped.setdefault(key, []).append(gap)

        insights: list[LearningInsight] = []
        for issue_type, items in grouped.items():
            questions = [item.query_text for item in items[:5]]
            source_text = "\n".join(questions)
            extracted = self.skills.knowledge_extract().execute(source_text, source=issue_type).output
            bullets = extracted.get("items", [])
            suggested_title = f"{issue_type} 知识补充"
            suggested_content = "\n".join(
                [bullet.get("content", "") for bullet in bullets[:3] if bullet.get("content")]
            ) or "\n".join(questions[:3])

            compare = self.skills.knowledge_compare().execute(
                left_text="\n".join(questions[:2]),
                right_text=suggested_content,
            ).output

            insights.append(
                LearningInsight(
                    topic=issue_type,
                    count=len(items),
                    sample_questions=questions,
                    suggested_title=suggested_title,
                    suggested_content=suggested_content,
                    diff_summary=compare.get("summary", ""),
                )
            )

        return {
            "insights": [
                {
                    "topic": item.topic,
                    "count": item.count,
                    "sample_questions": item.sample_questions,
                    "suggested_title": item.suggested_title,
                    "suggested_content": item.suggested_content,
                    "diff_summary": item.diff_summary,
                }
                for item in insights
            ],
            "total_gaps": len(gaps),
            "status": status,
        }
