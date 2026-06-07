from __future__ import annotations


class SkillError(Exception):
    pass


class SkillNotFoundError(SkillError):
    pass


class SkillValidationError(SkillError):
    pass


class SkillExecutionError(SkillError):
    pass
