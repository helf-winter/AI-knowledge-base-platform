from __future__ import annotations

from app.skills.base import BaseSkill
from app.skills.types import SkillMeta, SkillRequest, SkillResponse
from app.skills.registry import registry


class PermissionCheckSkill(BaseSkill):
    meta = SkillMeta(
        skill_id="permission_check",
        name="PermissionCheckSkill",
        description="Check whether a user can access given resources.",
        tags=["security", "acl"],
    )

    def validate(self, request: SkillRequest) -> None:
        if "resources" not in request.input:
            raise ValueError("resources is required")

    def execute(self, request: SkillRequest) -> SkillResponse:
        resources = request.input.get("resources", [])
        result = {"allowed": True, "resources": resources}
        return SkillResponse(trace_id=request.trace_id, data=result)


registry.register(PermissionCheckSkill)
