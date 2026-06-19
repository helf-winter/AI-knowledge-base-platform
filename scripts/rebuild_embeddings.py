from __future__ import annotations

import uuid
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.document import DocumentChunk
from app.models.vector import ChunkEmbedding
from app.services.embedding import EmbeddingService


def main() -> None:
    settings = get_settings()
    embedding = EmbeddingService()
    rebuilt = 0

    with SessionLocal() as db:
        db.query(ChunkEmbedding).delete()
        chunks = list(db.execute(select(DocumentChunk).order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)).scalars().all())

        for start in range(0, len(chunks), settings.embedding_batch_size):
            batch = chunks[start : start + settings.embedding_batch_size]
            vectors = embedding.embed_texts([chunk.content for chunk in batch])
            for chunk, vector in zip(batch, vectors):
                db.add(
                    ChunkEmbedding(
                        embedding_id=str(uuid.uuid4()),
                        chunk_id=chunk.chunk_id,
                        embedding_model=embedding.model_name,
                        dimension=len(vector),
                        vector=vector,
                    )
                )
                rebuilt += 1
            db.commit()

    print(f"rebuilt {rebuilt} chunk embeddings with {embedding.model_name}")


if __name__ == "__main__":
    main()
