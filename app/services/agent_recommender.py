from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, text, inspect
from sqlalchemy.orm import Session

from app.models.core import ExpertAgentProfile


@dataclass
class AgentRecommendation:
    agent_id: str
    agent_name: str
    reason: str


class AgentRecommender:
    def __init__(self, db: Session) -> None:
        self.db = db

    def recommend(self, question: str, agent_id: str | None = None) -> AgentRecommendation | None:
        candidates = self._list_agents()
        if agent_id:
            item = next((x for x in candidates if x.agent_id == agent_id), None)
            if item is None:
                return None
            return AgentRecommendation(agent_id=item.agent_id, agent_name=item.agent_name, reason=f"你当前已经选择了 {item.agent_name}，它更适合处理这类问题。")

        q = question.lower()
        if not candidates:
            return None

        keywords = {
            "报销": ["报销", "差旅", "发票", "财务"],
            "入职": ["入职", "新员工", "onboarding", "培训"],
            "合同": ["合同", "签署", "法务", "审批"],
            "IT": ["vpn", "账号", "密码", "系统", "权限", "电脑"],
            "知识库": ["资料", "文档", "知识", "检索", "搜索"],
        }

        best: tuple[int, ExpertAgentProfile] | None = None
        for item in candidates:
            hay = " ".join(filter(None, [item.agent_name, item.domain_name, item.description or "", item.knowledge_scope_json or ""]))
            score = 0
            for label, words in keywords.items():
                if any(word in q for word in words) and any(word in hay for word in words):
                    score += 2
            if item.domain_name and item.domain_name.lower() in q:
                score += 3
            if item.agent_name and item.agent_name.lower() in q:
                score += 3
            if best is None or score > best[0]:
                best = (score, item)

        if best is None or best[0] <= 0:
            return None
        return AgentRecommendation(
            agent_id=best[1].agent_id,
            agent_name=best[1].agent_name,
            reason=f"建议优先使用 {best[1].agent_name}，因为它的知识域是 {best[1].domain_name}。",
        )

    def _list_agents(self) -> list[ExpertAgentProfile]:
        if self._supports_skills_json():
            return list(self.db.execute(select(ExpertAgentProfile)).scalars().all())
        stmt = text("""
            SELECT agent_id, agent_name, domain_name, description, knowledge_scope_json, status, created_at, updated_at
            FROM expert_agent_profiles
            ORDER BY created_at DESC
        """)
        rows = list(self.db.execute(stmt).mappings().all())
        items: list[ExpertAgentProfile] = []
        for row in rows:
            item = ExpertAgentProfile(
                agent_id=row["agent_id"],
                agent_name=row["agent_name"],
                domain_name=row["domain_name"],
                description=row["description"],
                knowledge_scope_json=row["knowledge_scope_json"],
                status=row["status"],
            )
            setattr(item, "created_at", row["created_at"])
            setattr(item, "updated_at", row["updated_at"])
            setattr(item, "skills_json", None)
            items.append(item)
        return items

    def _supports_skills_json(self) -> bool:
        try:
            inspector = inspect(self.db.bind)
            columns = [col.get("name") for col in inspector.get_columns("expert_agent_profiles")]
            return "skills_json" in columns
        except Exception:
            return False
