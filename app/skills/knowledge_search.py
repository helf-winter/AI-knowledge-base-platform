from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.services.access_control import DocumentAccessService
from app.services.auth import AuthService
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
        self.db = db
        self.retriever = HybridRetriever(db)

    def execute(self, query: str, top_k: int = 5, user_id: str | None = None, scope: dict[str, Any] | None = None) -> SkillResult:
        hits = self.retriever.search(query=query, top_k=max(top_k * 3, top_k))
        user = AuthService(self.db).get_user_by_id(user_id) if user_id else None
        access = DocumentAccessService(self.db)
        results = []
        for hit in hits:
            if not self._matches_scope(hit.chunk.document, hit.chunk.content, scope):
                continue
            decision = access.can_access_document(hit.chunk.document, user) if user else None
            can_access = decision.can_access if decision else True
            if not can_access:
                continue
            if len(results) >= top_k:
                break
            results.append(
                {
                    "chunk_id": hit.chunk.chunk_id,
                    "document_id": hit.chunk.document_id,
                    "chunk_index": hit.chunk.chunk_index,
                    "content": hit.chunk.content if can_access else "",
                    "page_start": hit.chunk.page_start,
                    "page_end": hit.chunk.page_end,
                    "score": hit.final_score,
                    "source_file_name": hit.chunk.document.file_name,
                    "can_access": can_access,
                    "need_apply": decision.need_apply if decision else False,
                    "access_reason": decision.reason if decision else None,
                }
            )
        output = {
            "query": query,
            "top_k": top_k,
            "results": results,
        }
        return SkillResult(skill_id=self.skill_id, name=self.name, version=self.version, output=output)

    def _matches_scope(self, document: Any, content: str, scope: dict[str, Any] | None) -> bool:
        if not scope:
            return True
        document_ids = {str(item) for item in scope.get("document_ids", []) if str(item).strip()}
        if document_ids and getattr(document, "document_id", None) not in document_ids:
            return False
        categories = {str(item) for item in scope.get("knowledge_categories", []) if str(item).strip()}
        if categories and getattr(document, "knowledge_category", None) not in categories:
            return False
        keywords = [str(item).lower() for item in scope.get("keywords", []) if str(item).strip()]
        if keywords:
            haystack = " ".join(filter(None, [getattr(document, "file_name", ""), content])).lower()
            if not any(keyword in haystack for keyword in keywords):
                return False
        return True
