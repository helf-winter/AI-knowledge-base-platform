import unittest

from app.services.deepseek import DeepSeekClient


class ConversationContextTest(unittest.TestCase):
    def test_deepseek_prompt_includes_recent_conversation_context(self):
        client = DeepSeekClient()

        messages = client.build_messages(
            question="那第二步呢？",
            context_chunks=["VPN 使用步骤：1. 打开客户端。2. 输入账号密码。"],
            conversation_context=[
                {"query": "VPN 使用步骤是什么？", "answer": "第一步打开 VPN 客户端，第二步输入账号密码。"}
            ],
        )

        prompt = messages[-1]["content"]

        self.assertIn("最近对话上下文", prompt)
        self.assertIn("VPN 使用步骤是什么？", prompt)
        self.assertIn("第一步打开 VPN 客户端", prompt)
        self.assertIn("当前问题：那第二步呢？", prompt)


if __name__ == "__main__":
    unittest.main()
