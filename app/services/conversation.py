from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import ConversationTurn
from app.schemas.conversation import ConversationTurnCreate


class ConversationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_turn(self, payload: ConversationTurnCreate) -> ConversationTurn:
        item = ConversationTurn(
            turn_id=str(uuid.uuid4()),
            session_id=payload.session_id,
            user_id=payload.user_id,
            trace_id=payload.trace_id,
            query_text=payload.query_text,
            answer_text=payload.answer_text,
            confidence=payload.confidence,
            source_refs_json=payload.source_refs_json,
            model_name=payload.model_name,
            prompt_version=payload.prompt_version,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_turns(self, session_id: str | None = None) -> list[ConversationTurn]:
        stmt = select(ConversationTurn)
        if session_id:
            stmt = stmt.where(ConversationTurn.session_id == session_id)
        return list(self.db.execute(stmt).scalars().all())
