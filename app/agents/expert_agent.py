from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.core.skills import SkillRegistry
from app.services.expert_agent_runtime import ExpertAgentContext
from app.services.deepseek import DeepSeekClient


@dataclass
class AgentTrace:
    agent_name: str
    action: str
    payload: dict[str, Any]


class ExpertAgent:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.skills = SkillRegistry(db)
        self.llm = DeepSeekClient()

    def answer(
        self,
        question: str,
        top_k: int = 5,
        user_id: str | None = None,
        casual: bool = False,
        agent_context: ExpertAgentContext | None = None,
        conversation_context: list[dict[str, str]] | None = None,
    ) -> tuple[str, list[str], list[AgentTrace]]:
        search_result = self.skills.knowledge_search().execute(query=question, top_k=top_k, user_id=user_id, scope=agent_context.search_scope() if agent_context else None)
        chunks = search_result.output.get("results", [])
        context_chunks = [item.get("content", "") for item in chunks]
        refs = [f"{item.get('source_file_name', 'unknown')}#chunk-{item.get('chunk_index', 0)}" for item in chunks]
        traces = self._search_traces(question, top_k, len(chunks))

        if self.llm.is_configured():
            answer_parts = list(
                self.llm.stream_chat(
                    question,
                    context_chunks,
                    casual=casual,
                    expert_context=agent_context.prompt_context() if agent_context else None,
                    conversation_context=conversation_context,
                )
            )
            answer_text = "".join(answer_parts).strip()
            traces.append(
                AgentTrace(
                    agent_name="ExpertAgent",
                    action="deepseek_chat",
                    payload={"model": self.llm.model, "stream": True, "context_count": len(context_chunks), "agent_id": agent_context.agent_id if agent_context else None},
                )
            )
            if answer_text:
                return answer_text, refs, traces

        traces.append(
            AgentTrace(
                agent_name="ExpertAgent",
                action="fallback_summary",
                payload={"reason": "deepseek_empty_or_not_configured", "context_count": len(context_chunks)},
            )
        )
        return self._fallback_answer(question, chunks), refs, traces

    def stream_answer(
        self,
        question: str,
        top_k: int = 5,
        user_id: str | None = None,
        casual: bool = False,
        agent_context: ExpertAgentContext | None = None,
        conversation_context: list[dict[str, str]] | None = None,
    ) -> tuple[Iterable[str], list[str], list[AgentTrace]]:
        search_result = self.skills.knowledge_search().execute(query=question, top_k=top_k, user_id=user_id, scope=agent_context.search_scope() if agent_context else None)
        chunks = search_result.output.get("results", [])
        context_chunks = [item.get("content", "") for item in chunks]
        refs = [f"{item.get('source_file_name', 'unknown')}#chunk-{item.get('chunk_index', 0)}" for item in chunks]
        traces = self._search_traces(question, top_k, len(chunks))

        if self.llm.is_configured():
            streamed = self.llm.stream_chat(
                question,
                context_chunks,
                casual=casual,
                expert_context=agent_context.prompt_context() if agent_context else None,
                conversation_context=conversation_context,
            )
            traces.append(
                AgentTrace(
                    agent_name="ExpertAgent",
                    action="deepseek_chat",
                    payload={"model": self.llm.model, "stream": True, "context_count": len(context_chunks), "agent_id": agent_context.agent_id if agent_context else None},
                )
            )
            return streamed, refs, traces

        traces.append(
            AgentTrace(
                agent_name="ExpertAgent",
                action="fallback_summary",
                payload={"reason": "deepseek_not_configured", "context_count": len(context_chunks)},
            )
        )
        return iter([self._fallback_answer(question, chunks)]), refs, traces

    def _search_traces(self, question: str, top_k: int, result_count: int) -> list[AgentTrace]:
        return [
            AgentTrace(
                agent_name="RetrievalAgent",
                action="knowledge_search",
                payload={"query": question, "top_k": top_k, "result_count": result_count},
            )
        ]

    def _fallback_answer(self, question: str, chunks: list[dict[str, Any]]) -> str:
        if not chunks:
            return f"当前没有检索到能回答“{question}”的知识内容。建议先补充相关文档，或换一个更具体的问题。"

        lines = ["根据知识库命中的内容，可以先参考下面信息："]
        for idx, item in enumerate(chunks[:3], start=1):
            source = item.get("source_file_name", "unknown")
            chunk_index = item.get("chunk_index", 0)
            content = str(item.get("content", "")).strip()[:220]
            lines.append(f"{idx}. {content}（来源：{source}#chunk-{chunk_index}）")
        lines.append("以上回答基于当前知识库检索结果生成。")
        return "\n".join(lines)
