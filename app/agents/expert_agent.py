from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.core.skills import SkillRegistry
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

    def answer(self, question: str, top_k: int = 5, user_id: str | None = None, casual: bool = False) -> tuple[str, list[str], list[AgentTrace]]:
        search_result = self.skills.knowledge_search().execute(query=question, top_k=top_k, user_id=user_id)
        chunks = search_result.output.get("results", [])
        context_chunks = [item.get("content", "") for item in chunks]
        refs = [f"{item.get('source_file_name', 'unknown')}#chunk-{item.get('chunk_index', 0)}" for item in chunks]

        traces = [
            AgentTrace(
                agent_name="RetrievalAgent",
                action="knowledge_search",
                payload={"query": question, "top_k": top_k, "result_count": len(chunks)},
            )
        ]

        if self.llm.is_configured():
            answer_parts = list(self.llm.stream_chat(question, context_chunks, casual=casual))
            answer_text = "".join(answer_parts).strip()
            traces.append(
                AgentTrace(
                    agent_name="ExpertAgent",
                    action="deepseek_chat",
                    payload={"model": self.llm.model, "stream": True, "context_count": len(context_chunks)},
                )
            )
            if answer_text:
                return answer_text, refs, traces

        fallback = "根据知识库检索结果，相关内容如下：\n" + "\n".join(f"- {item.get('content', '')[:200]}" for item in chunks)
        if not chunks:
            fallback = "当前没有检索到足够的知识内容，但你可以尝试换个问法，或者切换到更合适的助手继续交流。"
        traces.append(
            AgentTrace(
                agent_name="ExpertAgent",
                action="fallback_summary",
                payload={"reason": "deepseek_empty_or_not_configured", "context_count": len(context_chunks)},
            )
        )
        return fallback, refs, traces

    def stream_answer(self, question: str, top_k: int = 5, user_id: str | None = None, casual: bool = False) -> tuple[Iterable[str], list[str], list[AgentTrace]]:
        search_result = self.skills.knowledge_search().execute(query=question, top_k=top_k, user_id=user_id)
        chunks = search_result.output.get("results", [])
        context_chunks = [item.get("content", "") for item in chunks]
        refs = [f"{item.get('source_file_name', 'unknown')}#chunk-{item.get('chunk_index', 0)}" for item in chunks]
        traces = [
            AgentTrace(
                agent_name="RetrievalAgent",
                action="knowledge_search",
                payload={"query": question, "top_k": top_k, "result_count": len(chunks)},
            )
        ]

        if self.llm.is_configured():
            streamed = self.llm.stream_chat(question, context_chunks, casual=casual)
            return streamed, refs, traces

        fallback = "根据知识库检索结果，相关内容如下：\n" + "\n".join(f"- {item.get('content', '')[:200]}" for item in chunks)
        if not chunks:
            fallback = "当前没有检索到足够的知识内容，但你可以尝试换个问法，或者切换到更合适的助手继续交流。"
        traces.append(
            AgentTrace(
                agent_name="ExpertAgent",
                action="fallback_summary",
                payload={"reason": "deepseek_not_configured", "context_count": len(context_chunks)},
            )
        )
        return iter([fallback]), refs, traces
