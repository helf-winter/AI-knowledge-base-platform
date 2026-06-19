from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.core import ExpertAgentProfile
from app.services.agent_recommender import AgentRecommender


@dataclass
class ExpertAgentContext:
    agent_id: str
    agent_name: str
    domain_name: str
    description: str | None = None
    knowledge_scope: dict[str, Any] = field(default_factory=dict)
    skills: list[str] = field(default_factory=lambda: ["knowledge_search"])
    selection_reason: str = "系统自动选择通用专家"

    @property
    def document_ids(self) -> set[str]:
        values: set[str] = set()
        for key in ("document_id", "document_ids"):
            raw = self.knowledge_scope.get(key)
            if isinstance(raw, str) and raw.strip():
                values.add(raw.strip())
            elif isinstance(raw, list):
                values.update(str(item).strip() for item in raw if str(item).strip())
        documents = self.knowledge_scope.get("documents")
        if isinstance(documents, list):
            for item in documents:
                if isinstance(item, dict):
                    raw_id = item.get("document_id") or item.get("id")
                    if raw_id:
                        values.add(str(raw_id).strip())
                elif str(item).strip():
                    values.add(str(item).strip())
        return values

    @property
    def knowledge_categories(self) -> set[str]:
        raw = self.knowledge_scope.get("knowledge_category") or self.knowledge_scope.get("knowledge_categories")
        if isinstance(raw, str) and raw.strip():
            return {raw.strip()}
        if isinstance(raw, list):
            return {str(item).strip() for item in raw if str(item).strip()}
        return set()

    @property
    def keywords(self) -> list[str]:
        raw = self.knowledge_scope.get("keywords")
        if isinstance(raw, str) and raw.strip():
            return [raw.strip()]
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        return []

    def search_scope(self) -> dict[str, Any]:
        return {
            "document_ids": sorted(self.document_ids),
            "knowledge_categories": sorted(self.knowledge_categories),
            "keywords": self.keywords,
        }

    def prompt_context(self) -> dict[str, str]:
        return {
            "agent_name": self.agent_name,
            "domain_name": self.domain_name,
            "description": self.description or "",
            "knowledge_scope": json.dumps(self.knowledge_scope, ensure_ascii=False) if self.knowledge_scope else "未限制",
            "skills": "、".join(self.skills),
        }


class ExpertAgentRuntime:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.recommender = AgentRecommender(db)

    def resolve(self, question: str, agent_id: str | None = None) -> ExpertAgentContext | None:
        if agent_id:
            profile = self.db.get(ExpertAgentProfile, agent_id)
            if profile is None or profile.status != "active":
                return None
            return self._context_from_profile(profile, f"用户主动选择 {profile.agent_name}")

        recommendation = self.recommender.recommend(question)
        if recommendation is None:
            return None
        profile = self.db.get(ExpertAgentProfile, recommendation.agent_id)
        if profile is None or profile.status != "active":
            return None
        return self._context_from_profile(profile, recommendation.reason)

    def _context_from_profile(self, profile: ExpertAgentProfile, reason: str) -> ExpertAgentContext:
        return ExpertAgentContext(
            agent_id=profile.agent_id,
            agent_name=profile.agent_name,
            domain_name=profile.domain_name,
            description=profile.description,
            knowledge_scope=self._parse_json_object(profile.knowledge_scope_json),
            skills=self._parse_skills(getattr(profile, "skills_json", None)),
            selection_reason=reason,
        )

    def _parse_json_object(self, raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except Exception:
            return {"keywords": [raw]}
        return parsed if isinstance(parsed, dict) else {}

    def _parse_skills(self, raw: str | None) -> list[str]:
        if not raw:
            return ["knowledge_search"]
        try:
            parsed = json.loads(raw)
        except Exception:
            return ["knowledge_search"]
        if not isinstance(parsed, list):
            return ["knowledge_search"]
        skills = [str(item).strip() for item in parsed if str(item).strip()]
        return skills or ["knowledge_search"]

