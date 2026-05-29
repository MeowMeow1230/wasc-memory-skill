"""LLM 客戶端 — 使用 Anthropic SDK 連接 DeepSeek"""

import os
from dotenv import load_dotenv
load_dotenv()

from anthropic import Anthropic
from anthropic.types import TextBlock


class LLMClient:
    """統一的 LLM 調用接口，支援 Anthropic SDK（含 DeepSeek Anthropic 兼容端點）"""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY", "")
        base_url = os.getenv("ANTHROPIC_BASE_URL", "")
        self.model = os.getenv("ANTHROPIC_MODEL", "deepseek-v4-pro[1m]")

        if base_url:
            self.client = Anthropic(api_key=api_key, base_url=base_url)
        else:
            self.client = Anthropic(api_key=api_key)

    def _get_text(self, content: list) -> str:
        """從 Anthropic response content 中提取文字，過濾 ThinkingBlock"""
        for block in content:
            if isinstance(block, TextBlock):
                return block.text
        # fallback: 嘗試第一個 block
        return str(content[0]) if content else ""

    def chat(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 4096,
    ) -> str:
        """調用 LLM，返回文字回應"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return self._get_text(response.content)

    def extract_json(self, prompt: str, max_tokens: int = 1024) -> str:
        """用於記憶提取等結構化輸出場景，低溫度保證一致性"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._get_text(response.content)
