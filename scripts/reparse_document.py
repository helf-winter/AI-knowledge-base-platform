from __future__ import annotations

import argparse
from pathlib import Path
import sys

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.models.core import TaskRecord
from app.models.document import Document, DocumentChunk
from app.models.vector import ChunkEmbedding
from app.services.knowledge_service import KnowledgeService


def main() -> None:
    parser = argparse.ArgumentParser(description="Reparse one document and rebuild its chunks/embeddings.")
    parser.add_argument("document_id")
    parser.add_argument("--file", dest="file_path", default=None)
    parser.add_argument("--name", dest="file_name", default=None)
    args = parser.parse_args()

    with SessionLocal() as db:
        document = db.get(Document, args.document_id)
        if document is None:
            raise SystemExit(f"document not found: {args.document_id}")

        file_path = Path(args.file_path or document.storage_path)
        if not file_path.is_absolute():
            file_path = ROOT / file_path
        if not file_path.exists():
            raise SystemExit(f"file not found: {file_path}")

        if args.file_name:
            document.file_name = args.file_name
        document.storage_path = str(file_path.resolve())
        document.parse_status = "processing"
        db.commit()

        for embedding in (
            db.execute(
                select(ChunkEmbedding)
                .join(DocumentChunk)
                .where(DocumentChunk.document_id == document.document_id)
            )
            .scalars()
            .all()
        ):
            db.delete(embedding)
        for chunk in db.execute(select(DocumentChunk).where(DocumentChunk.document_id == document.document_id)).scalars().all():
            db.delete(chunk)
        db.commit()

        try:
            KnowledgeService(db)._process_document(document, file_path.read_bytes())
        except Exception as exc:
            for task in db.execute(select(TaskRecord).where(TaskRecord.related_document_id == document.document_id)).scalars().all():
                task.status = "failed"
                task.error_message = str(exc)
            db.commit()
            raise

        for task in db.execute(select(TaskRecord).where(TaskRecord.related_document_id == document.document_id)).scalars().all():
            task.status = "succeeded"
            task.error_message = None
        db.commit()
        db.refresh(document)

        chunk_count = db.execute(select(DocumentChunk).where(DocumentChunk.document_id == document.document_id)).scalars().all()
        print(f"reparsed {document.document_id} status={document.parse_status} chunks={len(chunk_count)}")


if __name__ == "__main__":
    main()
