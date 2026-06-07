from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluationCaseCreate(BaseModel):
    question: str = Field(min_length=1)
    expected_answer: str = Field(min_length=1)
    source_references: list[str] = Field(default_factory=list)
    category: str = Field(default="general", max_length=64)


class EvaluationRunCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    model_name: str = Field(default="deepseek", max_length=64)
    prompt_version: str = Field(default="v1", max_length=32)
    retriever_version: str = Field(default="v1", max_length=32)


class EvaluationCaseRead(BaseModel):
    case_id: str
    question: str
    expected_answer: str
    source_references_json: str
    category: str


class EvaluationRunRead(BaseModel):
    run_id: str
    name: str
    model_name: str
    prompt_version: str
    retriever_version: str
    avg_score: float
    total_cases: int
    passed_cases: int
    failed_cases: int
    summary_json: str | None = None
    status: str = "pending"
    created_at: str | None = None


class EvaluationResultRead(BaseModel):
    result_id: str
    run_id: str
    case_id: str
    score_recall: float
    score_precision: float
    score_faithfulness: float
    score_groundedness: float
    score_overall: float
    created_at: str | None = None
