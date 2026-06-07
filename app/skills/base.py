from __future__ import annotations

from abc import ABC, abstractmethod

from app.skills.types import SkillMeta, SkillRequest, SkillResponse


class BaseSkill(ABC):
    meta: SkillMeta

    @abstractmethod
    def validate(self, request: SkillRequest) -> None:
        raise NotImplementedError

    @abstractmethod
    def execute(self, request: SkillRequest) -> SkillResponse:
        raise NotImplementedError
