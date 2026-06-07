from __future__ import annotations

from sqlalchemy.orm import Session

from app.skills.knowledge_search import KnowledgeSearchSkill
from app.skills.document_summarize import DocumentSummarizeSkill
from app.skills.knowledge_extract import KnowledgeExtractSkill
from app.skills.knowledge_compare import KnowledgeCompareSkill


class SkillRegistry:
    def __init__(self, db: Session) -> None:
        self.db = db

    def knowledge_search(self) -> KnowledgeSearchSkill:
        return KnowledgeSearchSkill(self.db)

    def document_summarize(self) -> DocumentSummarizeSkill:
        return DocumentSummarizeSkill()

    def knowledge_extract(self) -> KnowledgeExtractSkill:
        return KnowledgeExtractSkill()

    def knowledge_compare(self) -> KnowledgeCompareSkill:
        return KnowledgeCompareSkill()
