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

    def build_messages(self, question: str, context_chunks: list[str], casual: bool = False) -> list[dict[str, str]]:
        context_text = "\n\n".join(f"[{idx + 1}] {chunk}" for idx, chunk in enumerate(context_chunks))
        if casual:
            system_prompt = (
                "你是一个轻松自然、像平常聊天一样的企业 AI 助手。"
                "请用口语化、友好、简洁的方式回答，像在和同事聊天。"
                "如果不知道，可以直接说明，并给出下一步建议。"
            )
            user_prompt = f"用户：{question}"
        else:
            system_prompt = (
                "你是企业知识库助手。请严格基于给定上下文回答，优先使用上下文中的信息。"
                "如果上下文不足以支持结论，请明确说明不确定，并建议补充知识。"
                "回答要求简洁、准确、可执行。"
            )
            user_prompt = f"问题：{question}\n\n检索到的上下文：\n{context_text or '无'}"
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def stream_chat(self, question: str, context_chunks: list[str], casual: bool = False) -> Iterable[str]:
        if not self.is_configured():
            yield "DeepSeek 未配置，已回退到检索拼接答案。"
            return

        payload = {
            "model": self.model,
            "messages": self.build_messages(question, context_chunks, casual=casual),
            "stream": True,
            "thinking": {"type": "enabled"} if settings.deepseek_thinking_enabled else {"type": "disabled"},
            "reasoning_effort": "high",
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120.0,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield content
