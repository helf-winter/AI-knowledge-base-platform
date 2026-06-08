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
            yield self._build_fallback_answer(question, context_chunks, casual=casual)
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

    def _build_fallback_answer(self, question: str, context_chunks: list[str], casual: bool = False) -> str:
        if context_chunks:
            summary = "\n".join(f"- {chunk[:180]}" for chunk in context_chunks[:3])
            return f"根据知识库检索结果，先给你一个简要回答：\n{summary}"
        if casual:
            return f"我先给你一个简单建议：关于『{question}』，建议你先明确场景、系统名称和具体报错，再继续提问。"
        return f"当前没有检索到足够的知识内容，建议你换个更具体的问法，或者补充相关文档后再试。"
