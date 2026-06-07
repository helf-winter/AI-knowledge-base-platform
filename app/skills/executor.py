from __future__ import annotations

import time
from app.skills.errors import SkillNotFoundError, SkillValidationError, SkillExecutionError
from app.skills.registry import registry
from app.skills.types import SkillRequest, SkillResponse


class SkillExecutor:
    def run(self, skill_id: str, request: SkillRequest) -> SkillResponse:
        skill_cls = registry.get(skill_id)
        skill = skill_cls()
        start = time.perf_counter()

        try:
            skill.validate(request)
        except Exception as exc:
            raise SkillValidationError(str(exc)) from exc

        try:
            response = skill.execute(request)
            if response.trace_id is None:
                response.trace_id = request.trace_id
            return response
        except Exception as exc:
            raise SkillExecutionError(f"Skill execution failed: {skill_id}") from exc
        finally:
            _ = time.perf_counter() - start


skill_executor = SkillExecutor()
