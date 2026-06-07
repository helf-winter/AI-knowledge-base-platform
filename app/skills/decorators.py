from __future__ import annotations

from functools import wraps
from app.skills.registry import registry


def register_skill(skill_cls):
    registry.register(skill_cls)
    return skill_cls


def skill_entrypoint(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper
