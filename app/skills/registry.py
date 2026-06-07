from __future__ import annotations

from app.skills.base import BaseSkill
from app.skills.errors import SkillNotFoundError


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, type[BaseSkill]] = {}

    def register(self, skill_cls: type[BaseSkill]) -> None:
        self._skills[skill_cls.meta.skill_id] = skill_cls

    def get(self, skill_id: str) -> type[BaseSkill]:
        skill_cls = self._skills.get(skill_id)
        if skill_cls is None:
            raise SkillNotFoundError(f"Skill not found: {skill_id}")
        return skill_cls

    def list_ids(self) -> list[str]:
        return sorted(self._skills.keys())


registry = SkillRegistry()
