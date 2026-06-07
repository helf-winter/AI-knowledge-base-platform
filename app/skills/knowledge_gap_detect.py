from __future__ import annotations

from app.skills.base import BaseSkill
from app.skills.registry import registry
from app.skills.types import SkillMeta, SkillRequest, SkillResponse


class KnowledgeGapDetectSkill(BaseSkill):
    meta = SkillMeta(
        skill_id="knowledge_gap_detect",
        name="KnowledgeGapDetectSkill",
        description="Detect missing knowledge topics from feedback and logs.",
        tags=["learning", "analytics"],
    )

    def validate(self, request: SkillRequest) -> None:
        if "records" not in request.input:
            raise ValueError("records is required")

    def execute(self, request: SkillRequest) -> SkillResponse:
        records = request.input.get("records", [])
        data = {"missing_topics": ["待补充知识主题"], "record_count": len(records)}
        return SkillResponse(trace_id=request.trace_id, data=data)


registry.register(KnowledgeGapDetectSkill)
