from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.vector import ChunkEmbedding
from app.services.embedding import EmbeddingService


@dataclass
class RetrievalCandidate:
    chunk: DocumentChunk
    keyword_score: float
    vector_score: float
    final_score: float = 0.0


class HybridRetriever:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedding = EmbeddingService()

    def search(self, query: str, top_k: int = 5) -> list[RetrievalCandidate]:
        """Perform a lightweight hybrid retrieval.

        Vector recall uses the configured embedding provider. With the default
        local BGE model this is real semantic retrieval; keyword recall remains
        as a safety net for exact matches.
        """
        query = query.strip()
        if not query:
            return []

        qvec = self.embedding.embed_text(query)
        lowered = query.lower()

        # Vector recall.
        vector_rows = self.db.execute(
            select(ChunkEmbedding, ChunkEmbedding.vector.cosine_distance(qvec).label("distance"))
            .join(DocumentChunk)
            .join(Document)
            .where(Document.parse_status == "succeeded")
            .order_by("distance")
            .limit(max(top_k * 5, 20))
        ).all()

        candidates: dict[str, RetrievalCandidate] = {}
        for embedding, distance in vector_rows:
            chunk = self.db.get(DocumentChunk, embedding.chunk_id)
            if chunk is None:
                continue
            candidates[chunk.chunk_id] = RetrievalCandidate(
                chunk=chunk,
                keyword_score=0.0,
                vector_score=max(0.0, 1.0 - float(distance or 0.0)),
            )

        # Keyword recall.
        keyword_rows = self.db.execute(
            select(DocumentChunk)
            .join(Document)
            .where(Document.parse_status == "succeeded")
            .where(func.lower(DocumentChunk.content).like(f"%{lowered}%"))
            .limit(max(top_k * 5, 20))
        ).scalars().all()

        for chunk in keyword_rows:
            if chunk.chunk_id not in candidates:
                candidates[chunk.chunk_id] = RetrievalCandidate(
                    chunk=chunk,
                    keyword_score=1.0,
                    vector_score=0.0,
                )
            else:
                candidates[chunk.chunk_id].keyword_score = 1.0

        if not candidates:
            return []

        for item in candidates.values():
            item.final_score = self._rerank(query, item)

        ranked = sorted(candidates.values(), key=lambda x: x.final_score, reverse=True)
        return ranked[:top_k]

    def _rerank(self, query: str, candidate: RetrievalCandidate) -> float:
        """Lightweight rerank strategy.

        In production this can be replaced by a cross-encoder reranker.
        """
        length_bonus = min(len(candidate.chunk.content) / 1000.0, 0.1)
        query_tokens = [token for token in query.lower().split() if token]
        overlap_bonus = 0.0
        if query_tokens:
            overlap_bonus = 1.0 if query_tokens[0] in candidate.chunk.content.lower() else 0.0
        return 0.3 * candidate.keyword_score + 0.6 * candidate.vector_score + 0.1 * overlap_bonus + length_bonus
