from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.api.routes import _publish_request_response
from app.agents.review_agent import ReviewAgent
from app.schemas.review import ReviewRequest, ReviewResult
from app.services.knowledge_publish import KnowledgePublishService


ROOT = Path(__file__).resolve().parents[1]
ADMIN_PAGE = ROOT / "frontend" / "src" / "app" / "admin" / "page.tsx"
ROUTES_FILE = ROOT / "app" / "api" / "routes.py"


def publish_request() -> SimpleNamespace:
    return SimpleNamespace(
        request_id="publish-1",
        document_id="doc-1",
        requester_id="user-1",
        target_category="VPN相关",
        allowed_job_categories="全公司",
        publish_reason="供团队复用经过整理的申请流程。",
        business_purpose="减少重复咨询并统一办理方式。",
        status="pending",
        ai_suggestion=None,
        ai_risk_level=None,
        ai_reason=None,
        reviewed_by=None,
        review_comment=None,
        reviewed_at=None,
        created_at=None,
    )


def test_build_publish_ai_review_persists_result_without_approving():
    db = MagicMock()
    item = publish_request()
    document = SimpleNamespace(
        file_name="VPN申请经验.md",
        content_text="VPN 申请需要填写用途并由直属负责人确认。",
        knowledge_space="personal",
        security_level="internal",
    )
    requester = SimpleNamespace(
        employee_no="E1001",
        permission_level=1,
        position="研发工程师",
        department="研发部",
    )
    db.get.side_effect = lambda model, key: document if key == "doc-1" else requester
    service = KnowledgePublishService(db)
    service.get_request = MagicMock(return_value=item)

    with patch("app.services.knowledge_publish.ReviewAgent") as agent_cls:
        agent_cls.return_value.review.return_value = ReviewResult(
            review_type="knowledge_publish",
            suggestion="approve",
            risk_level="low",
            reason="申请信息完整，内容未发现明显敏感风险。",
        )
        result = service.build_ai_review("publish-1")

    assert result == {
        "suggestion": "approve",
        "risk_level": "low",
        "reason": "申请信息完整，内容未发现明显敏感风险。",
    }
    assert item.status == "pending"
    assert item.ai_suggestion == "approve"
    assert item.ai_risk_level == "low"
    assert item.ai_reason == "申请信息完整，内容未发现明显敏感风险。"
    db.commit.assert_called_once()


def test_publish_response_contains_ai_review_fields():
    item = publish_request()
    item.ai_suggestion = "review"
    item.ai_risk_level = "medium"
    item.ai_reason = "需要管理员核对适用范围。"

    response = _publish_request_response(item)

    assert response.ai_suggestion == "review"
    assert response.ai_risk_level == "medium"
    assert response.ai_reason == "需要管理员核对适用范围。"


def test_publish_review_route_and_page_expose_ai_review_action():
    routes = ROUTES_FILE.read_text(encoding="utf-8")
    page = ADMIN_PAGE.read_text(encoding="utf-8")

    assert '/admin/publish-requests/{request_id}/ai-review' in routes
    assert '/api/v1/admin/publish-requests/${requestId}/ai-review' in page
    assert "生成 AI 审核建议" in page
    assert "AI 仅提供建议，最终由管理员决定" in page


def test_publish_review_rule_fallback_remains_available_without_deepseek():
    result = ReviewAgent(MagicMock())._fallback_review(
        ReviewRequest(
            review_type="knowledge_publish",
            subject={
                "target_category": "VPN相关",
                "allowed_job_categories": "全公司",
                "business_purpose": "统一 VPN 申请流程",
            },
            context={},
        )
    )

    assert result.suggestion == "review"
    assert result.risk_level == "medium"
    assert result.reason
