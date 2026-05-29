"""記憶分類器 — LLM 驅動的結構化記憶提取，支援 DeepSeek"""

import json
from src.llm import LLMClient
from src.models import Memory, MemoryType, MemoryScope, MemoryStatus


EXTRACTION_PROMPT = """你是一個記憶提取器。分析用戶的反饋，從中提取結構化記憶。

## 四種記憶類型

1. **preference** (長期偏好): 用戶的編碼風格、語言偏好、工具偏好
   例: "偏好 TypeScript strict mode"、"喜歡 functional style 不喜歡 class"

2. **rule** (場景規則): 特定場景下的規則或約定
   例: "React component 用 named export"、"檔案命名用 kebab-case"

3. **method** (工作方法): 工作流程或方法論
   例: "重構前先跑測試"、"commit message 用 conventional commits"

4. **temporary** (暫時例外): 明確是暫時的例外情況
   例: "這個函數暫時用 any"、"先跳過測試這部分"

## Scope 分類

- **global**: 全局生效，適用所有場景
- **project**: 專案級，僅在當前專案生效
- **file**: 檔案級例外，僅對特定檔案
- **temporary**: 暫時例外，有過期時間

## 規則

- 捨棄臨時任務資訊（如 "把按鈕改紅色"、"修這個 bug"）
- 每條記憶必須有明確的 type 和 scope
- 如果用戶反饋中沒有值得長期記住的資訊，返回空列表
- 不要重複提取已經存在的相同記憶
- preference 的 priority 設 7-9，method 設 5-7，rule 設 6-8，temporary 設 3-5

## 用戶反饋

{user_message}

## 上下文（之前的記憶，僅供參考避免重複）

{existing_memories}

## 輸出格式

返回 JSON 陣列，每條記憶包含: type, content, scope, priority, source
如果沒有值得提取的記憶，返回空陣列 []。

只輸出 JSON，不要其他文字。"""


class MemoryExtractor:
    """從用戶反饋中提取結構化記憶"""

    def __init__(self, client: LLMClient):
        self.client = client

    def extract(self, user_message: str, existing_memories: list[Memory]) -> list[Memory]:
        """分析用戶反饋，返回新提取的記憶列表"""
        existing_summary = "\n".join(
            f"- [{m.type.value}] {m.content} (scope: {m.scope.value})"
            for m in existing_memories
        ) or "(無現有記憶)"

        prompt = EXTRACTION_PROMPT.format(
            user_message=user_message,
            existing_memories=existing_summary,
        )

        raw = self.client.extract_json(prompt)
        items = self._parse_json(raw)

        if not items:
            # fallback: 直接問 LLM 有沒有偏好，用更簡單的格式
            items = self._fallback_extract(user_message)

        if not isinstance(items, list):
            items = []

        memories = []
        for item in items:
            try:
                if not isinstance(item, dict) or "content" not in item:
                    continue
                mem = Memory(
                    type=MemoryType(item.get("type", "preference")),
                    content=item["content"],
                    scope=MemoryScope(item.get("scope", "global")),
                    priority=item.get("priority", 5),
                    source=item.get("source", user_message[:80]),
                )
                memories.append(mem)
            except (KeyError, ValueError):
                continue

        return memories

    def _parse_json(self, raw: str) -> list:
        """多層 JSON 解析：直接 / markdown code block / 文字中找數組 / 逐行"""
        # 1. 直接解析
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 2. 找 markdown code block
        import re
        m = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 3. 找文字中的 JSON 數組
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass

        return []

    def _fallback_extract(self, user_message: str) -> list:
        """備用方案：用更簡單的 prompt 直接問"""
        prompt = f"""分析這段用戶反饋。如果用戶表達了編碼偏好、規則或工作方法，用 JSON 陣列列出。
如果沒有值得記住的偏好，返回 []。

用戶反饋: {user_message}

格式: [{{"type": "preference", "content": "...", "scope": "global", "priority": 7, "source": "用戶反饋"}}]

只輸出 JSON 陣列。type 只能是 preference/rule/method。沒有偏好就輸出 []。"""

        raw = self.client.extract_json(prompt)
        items = self._parse_json(raw)
        return items if isinstance(items, list) else []

    def classify_feedback(self, response_text: str, original_request: str) -> str:
        """判斷用戶回覆是本質反饋還是臨時任務"""
        temp_patterns = [
            "幫我", "改一下", "修這個", "加一個", "刪掉", "換成",
            "把這個", "這裡", "現在就", "快",
        ]
        pref_patterns = [
            "我偏好", "我習慣", "我喜歡", "我不喜歡", "以後都",
            "每次都", "記住", "永遠", "不要用", "要用", "盡量",
            "我的風格", "我的規則", "按照我的",
        ]

        msg = original_request.lower()
        pref_score = sum(1 for p in pref_patterns if p in msg)
        temp_score = sum(1 for p in temp_patterns if p in msg)

        if pref_score > temp_score:
            return "feedback"
        elif temp_score > pref_score:
            return "temporary"
        else:
            return "feedback"
