from __future__ import annotations

import json
from typing import Iterable

import httpx

from app.core.config import get_settings

settings = get_settings()


class DeepSeekClient:
    def __init__(self) -> None:
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url.rstrip("/")
        self.model = settings.deepseek_model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def complete_json(
        self,
        system_prompt: str,
        payload: dict[str, object],
        *,
        temperature: float = 0.1,
        timeout: float = 60.0,
    ) -> dict[str, object] | None:
        """Request one structured JSON object, returning None for a safe fallback."""
        if not self.is_configured():
            return None
        request_payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "stream": False,
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=request_payload,
                timeout=timeout,
            )
            response.raise_for_status()
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            return self._parse_json_object(str(content))
        except Exception:
            return None

    def _parse_json_object(self, content: str) -> dict[str, object] | None:
        text = content.strip()
        if not text:
            return None
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            parsed = json.loads(text)
        except (TypeError, json.JSONDecodeError):
            return None
        return parsed if isinstance(parsed, dict) else None

    def build_messages(
        self,
        question: str,
        context_chunks: list[str],
        casual: bool = False,
        expert_context: dict[str, str] | None = None,
        conversation_context: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        context_text = "\n\n".join(f"[{idx + 1}] {chunk}" for idx, chunk in enumerate(context_chunks))
        conversation_text = self._format_conversation_context(conversation_context or [])
        expert_prompt = ""
        if expert_context:
            expert_prompt = (
                f"你当前扮演专家 Agent：{expert_context.get('agent_name', '')}。"
                f"知识领域：{expert_context.get('domain_name', '')}。"
                f"职责说明：{expert_context.get('description', '')}。"
                f"知识范围：{expert_context.get('knowledge_scope', '')}。"
                f"可用能力：{expert_context.get('skills', '')}。"
                "回答时要体现该专家身份，并优先使用其知识范围内的内容。"
            )
        if casual:
            system_prompt = (
                "你是一个通用 AI 助手，回答方式接近正常聊天版 DeepSeek。"
                "请优先直接、开放地回答用户问题，可以结合通用知识、常见企业实践和合理建议。"
                "系统可能会提供一些企业知识库片段，它们只是可选参考，不是回答边界。"
                "不要因为参考片段没有覆盖完整流程就拒绝回答；如果涉及公司内部审批、权限或制度，"
                "请给出通用流程，并提醒用户最终以公司 IT/行政/制度文档为准。"
                "不要在回答末尾强制写“依据来自知识片段”。"
            )
            user_prompt = f"问题：{question}\n\n可选参考资料（不要求完全依据）：\n{context_text or '无'}"
        else:
            system_prompt = (
                f"你是企业知识库专家助手。{expert_prompt}必须优先基于给定的知识库上下文回答，"
                "不要把通用常识放在知识库证据之前。"
                "如果上下文足以回答，请直接给出步骤或结论；如果上下文不足，请明确说明不足并建议补充知识。"
                "回答末尾用一句话说明依据来自哪些知识片段编号。"
                "语气专业、简洁、可执行。"
            )
            user_prompt = f"问题：{question}\n\n知识库上下文：\n{context_text or '无'}"
        if conversation_text:
            user_prompt = f"{conversation_text}当前问题：{question}\n\n{user_prompt}"
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def stream_chat(
        self,
        question: str,
        context_chunks: list[str],
        casual: bool = False,
        expert_context: dict[str, str] | None = None,
        conversation_context: list[dict[str, str]] | None = None,
    ) -> Iterable[str]:
        if not self.is_configured():
            yield self._build_fallback_answer(question, context_chunks, casual=casual)
            return

        payload = {
            "model": self.model,
            "messages": self.build_messages(question, context_chunks, casual=casual, expert_context=expert_context, conversation_context=conversation_context),
            "stream": True,
            "thinking": {"type": "enabled"} if settings.deepseek_thinking_enabled else {"type": "disabled"},
            "reasoning_effort": "high",
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        collected = ""
        with httpx.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120.0,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        break
                    chunk = self._extract_content_from_stream_chunk(data)
                    if chunk:
                        collected += chunk
                        yield chunk
        if not collected.strip():
            fallback = self._build_fallback_answer(question, context_chunks, casual=casual)
            if fallback:
                yield fallback

    def _extract_content_from_stream_chunk(self, data: str) -> str:
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            return ""
        choices = obj.get("choices") or []
        if not choices:
            return ""
        choice = choices[0] or {}
        delta = choice.get("delta") or {}
        content = delta.get("content")
        if content:
            return str(content)
        message = choice.get("message") or {}
        content = message.get("content")
        if content:
            return str(content)
        text = obj.get("text")
        if text:
            return str(text)
        return ""

    def _format_conversation_context(self, conversation_context: list[dict[str, str]]) -> str:
        if not conversation_context:
            return ""
        lines = ["最近对话上下文："]
        for idx, item in enumerate(conversation_context[-6:], start=1):
            query = str(item.get("query") or "").strip()
            answer = str(item.get("answer") or "").strip()
            if len(answer) > 500:
                answer = f"{answer[:500]}..."
            if query or answer:
                lines.append(f"{idx}. 用户：{query}\n   助手：{answer}")
        if len(lines) == 1:
            return ""
        lines.append("请结合上述上下文理解代词、省略表达和追问，但不要编造知识库中没有的公司制度。")
        return "\n".join(lines) + "\n\n"

    def _build_fallback_answer(self, question: str, context_chunks: list[str], casual: bool = False) -> str:
        if casual:
            normalized = question.lower()
            reference_note = ""
            if context_chunks:
                reference_note = "\n\n我也会参考当前知识库里已有的相关信息，但不会只受这些片段限制。"
            if "vpn" in normalized and any(word in question for word in ("申请", "开通", "权限", "账号")):
                return (
                    "一般可以按下面流程申请 VPN：\n\n"
                    "1. 先确认公司是否有 IT 服务台、OA、工单系统或内部帮助中心入口。\n"
                    "2. 在入口中选择 VPN、远程办公或内网访问权限相关申请。\n"
                    "3. 填写申请原因、使用期限、访问系统范围、设备信息等内容。\n"
                    "4. 提交给直属主管或部门负责人审批。\n"
                    "5. 审批通过后，由 IT 开通账号或权限，并发送客户端、配置方式和登录说明。\n"
                    "6. 首次使用时通常还需要绑定 MFA、安装安全组件或遵守远程访问规范。\n\n"
                    "不同公司的入口和审批字段会不一样，正式操作仍以公司 IT 部门或内部制度文档为准。"
                    f"{reference_note}"
                )
            return (
                f"可以，我先按通用经验回答“{question}”。"
                "当前模型接口未配置或没有返回内容，所以这里只能给出通用处理思路："
                "先明确目标、约束条件和负责部门，再按常见企业流程确认入口、提交材料、等待审批并保存结果记录。"
                "如果这是公司内部事项，最终仍建议以正式制度或负责人答复为准。"
                f"{reference_note}"
            )
        if context_chunks:
            bullets = "\n".join(f"{idx + 1}. {chunk[:220]}" for idx, chunk in enumerate(context_chunks[:3]))
            return (
                "根据知识库检索结果，可以先按下面信息处理：\n"
                f"{bullets}\n\n"
                "以上回答来自当前命中的知识片段；如果需要更精确的结论，建议补充对应制度或操作文档。"
            )
        return f"当前知识库没有检索到足够回答“{question}”的内容，建议换个更具体的问题，或先上传/补充相关文档。"
