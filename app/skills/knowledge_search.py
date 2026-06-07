from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.services.search import HybridRetriever


@dataclass
class SkillResult:
    skill_id: str
    name: str
    version: str
    output: dict[str, Any]


class KnowledgeSearchSkill:
    skill_id = "knowledge_search"
    name = "KnowledgeSearchSkill"
    version = "v1"
    description = "Search knowledge chunks using hybrid retrieval."

    def __init__(self, db: Session) -> None:
        self.retriever = HybridRetriever(db)

    def execute(self, query: str, top_k: int = 5, user_id: str | None = None) -> SkillResult:
        hits = self.retriever.search(query=query, top_k=top_k)
        output = {
            "query": query,
            "top_k": top_k,
            "results": [
                {
                    "chunk_id": hit.chunk.chunk_id,
                    "document_id": hit.chunk.document_id,
                    "chunk_index": hit.chunk.chunk_index,
                    "content": hit.chunk.content,
                    "page_start": hit.chunk.page_start,
                    "page_end": hit.chunk.page_end,
                    "score": hit.final_score,
                    "source_file_name": hit.chunk.document.file_name,
                }
                for hit in hits
            ],
        }
        return SkillResult(skill_id=self.skill_id, name=self.name, version=self.version, output=output)
