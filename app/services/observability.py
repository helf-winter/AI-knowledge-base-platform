from __future__ import annotations

import uuid
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.observability import AlertEvent, AlertRule, MetricSnapshot
from app.models.document import Document
from app.models.core import TaskRecord, AuditLog, Answer
from app.schemas.observability import AlertRuleCreate, MetricSnapshotCreate


class ObservabilityService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def dashboard(self) -> dict[str, object]:
        total_docs = self.db.execute(select(func.count()).select_from(Document)).scalar_one()
        total_tasks = self.db.execute(select(func.count()).select_from(TaskRecord)).scalar_one()
        failed_tasks = self.db.execute(select(func.count()).select_from(TaskRecord).where(TaskRecord.status == "failed")).scalar_one()
        total_answers = self.db.execute(select(func.count()).select_from(Answer)).scalar_one()
        total_audits = self.db.execute(select(func.count()).select_from(AuditLog)).scalar_one()
        recent_metrics = self.db.execute(select(MetricSnapshot).order_by(MetricSnapshot.created_at.desc()).limit(5)).scalars().all()
        return {
            "summary": {
                "documents": int(total_docs or 0),
                "tasks": int(total_tasks or 0),
                "failed_tasks": int(failed_tasks or 0),
                "answers": int(total_answers or 0),
                "audit_logs": int(total_audits or 0),
            },
            "recent_metrics": [
                {
                    "metric_name": item.metric_name,
                    "metric_value": item.metric_value,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                }
                for item in recent_metrics
            ],
        }

    def create_metric_snapshot(self, payload: MetricSnapshotCreate) -> MetricSnapshot:
        item = MetricSnapshot(
            snapshot_id=str(uuid.uuid4()),
            metric_name=payload.metric_name,
            metric_value=payload.metric_value,
            labels_json=payload.labels_json,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        self._evaluate_rules(item.metric_name, item.metric_value)
        return item

    def create_rule(self, payload: AlertRuleCreate) -> AlertRule:
        item = AlertRule(
            rule_id=str(uuid.uuid4()),
            rule_name=payload.rule_name,
            metric_name=payload.metric_name,
            operator=payload.operator,
            threshold=payload.threshold,
            severity=payload.severity,
            is_enabled=1 if payload.is_enabled else 0,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_rules(self) -> list[AlertRule]:
        return list(self.db.execute(select(AlertRule).order_by(AlertRule.created_at.desc())).scalars().all())

    def list_events(self) -> list[AlertEvent]:
        return list(self.db.execute(select(AlertEvent).order_by(AlertEvent.created_at.desc())).scalars().all())

    def _evaluate_rules(self, metric_name: str, actual_value: float) -> None:
        rules = self.db.execute(select(AlertRule).where(AlertRule.metric_name == metric_name)).scalars().all()
        for rule in rules:
            if not bool(rule.is_enabled):
                continue
            triggered = False
            if rule.operator == ">":
                triggered = actual_value > rule.threshold
            elif rule.operator == ">=":
                triggered = actual_value >= rule.threshold
            elif rule.operator == "<":
                triggered = actual_value < rule.threshold
            elif rule.operator == "<=":
                triggered = actual_value <= rule.threshold
            elif rule.operator == "==":
                triggered = actual_value == rule.threshold
            elif rule.operator == "!=":
                triggered = actual_value != rule.threshold
            if triggered:
                self.db.add(
                    AlertEvent(
                        event_id=str(uuid.uuid4()),
                        rule_id=rule.rule_id,
                        metric_name=metric_name,
                        actual_value=actual_value,
                        threshold=rule.threshold,
                        severity=rule.severity,
                        message=f"Metric {metric_name} triggered rule {rule.rule_name}",
                        status="open",
                    )
                )
        self.db.commit()
