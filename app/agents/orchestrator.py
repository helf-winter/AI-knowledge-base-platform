from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.skills import SkillRegistry


@dataclass
class AgentTrace:
    agent_name: str
    action: str
    payload: dict[str, Any]


class AgentOrchestrator:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.skills = SkillRegistry(db)

    def route_intent(self, query: str) -> str:
        lowered = query.lower()
        if any(token in lowered for token in ["总结", "概括", "摘要"]):
            return "summarize"
        if any(token in lowered for token in ["抽取", "提炼", "结构化"]):
            return "extract"
        if any(token in lowered for token in ["检索", "搜索", "查找"]):
            return "search"
        return "qa"

    def run_search(self, query: str, top_k: int = 5, user_id: str | None = None) -> tuple[dict[str, Any], list[AgentTrace]]:
        skill = self.skills.knowledge_search()
        result = skill.execute(query=query, top_k=top_k, user_id=user_id)
        trace = [AgentTrace(agent_name="RetrievalAgent", action="knowledge_search", payload={"query": query, "top_k": top_k})]
        return result.output, trace

    def run_summary(self, text: str) -> tuple[dict[str, Any], list[AgentTrace]]:
        skill = self.skills.document_summarize()
        result = skill.execute(text=text)
        trace = [AgentTrace(agent_name="ExpertAgent", action="document_summarize", payload={"length": len(text)})]
        return result.output, trace

    def run_extract(self, text: str, source: str | None = None) -> tuple[dict[str, Any], list[AgentTrace]]:
        skill = self.skills.knowledge_extract()
        result = skill.execute(text=text, source=source)
        trace = [AgentTrace(agent_name="LearningAgent", action="knowledge_extract", payload={"length": len(text), "source": source})]
        return result.output, trace
