from __future__ import annotations

from pydantic import BaseModel, Field


class MetricSnapshotCreate(BaseModel):
    metric_name: str = Field(min_length=1, max_length=128)
    metric_value: float
    labels_json: str | None = None


class AlertRuleCreate(BaseModel):
    rule_name: str = Field(min_length=1, max_length=128)
    metric_name: str = Field(min_length=1, max_length=128)
    operator: str = Field(default=">", max_length=8)
    threshold: float
    severity: str = Field(default="warning", max_length=32)
    is_enabled: bool = True


class AlertRuleRead(BaseModel):
    rule_id: str
    rule_name: str
    metric_name: str
    operator: str
    threshold: float
    severity: str
    is_enabled: bool


class AlertEventRead(BaseModel):
    event_id: str
    rule_id: str
    metric_name: str
    actual_value: float
    threshold: float
    severity: str
    message: str
    status: str
