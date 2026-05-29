"""記憶注入器 — 每次 Agent 調用前注入相關記憶到 system prompt"""

from src.models import Memory, MemoryScope, MemoryStatus
from src.store import MemoryStore


MEMORY_INJECTION_TEMPLATE = """## 用戶記憶

以下是從過去互動中學習到的用戶偏好和規則。請在回答時自動應用這些記憶，
不需要用戶再次提醒。如果記憶之間有衝突，以 priority 較高者為準。

{memories}

---
"""


class MemoryInjector:
    """管理記憶注入到 Agent prompt 的邏輯"""

    def __init__(self, store: MemoryStore):
        self.store = store

    def inject(
        self,
        user_message: str,
        all_memories: list[Memory],
        current_scope: MemoryScope | None = None,
    ) -> str:
        """
        根據用戶當前訊息，搜索並注入相關記憶。
        返回要添加到 system prompt 的記憶區塊。
        """
        # 只用 active 記憶
        active = [m for m in all_memories if m.status == MemoryStatus.ACTIVE]

        if not active:
            return ""

        # 用 Mem0 做語義搜尋，找最相關的記憶
        search_results = self.store.search(
            query=user_message,
            top_k=10,
            scope=current_scope,
        )

        # 從 Mem0 的 metadata 找回 memory_id，匹配我們的 Memory 物件
        matched_ids = set()
        for r in search_results:
            if "metadata" in r and "memory_id" in r["metadata"]:
                matched_ids.add(r["metadata"]["memory_id"])

        # 匹配到的記憶 + 所有 global 記憶
        relevant = []
        for m in active:
            if m.id in matched_ids or m.scope == MemoryScope.GLOBAL:
                relevant.append(m)

        # 按 priority 排序
        relevant.sort(key=lambda m: m.priority, reverse=True)

        if not relevant:
            return ""

        # 結構化輸出
        lines = []
        for m in relevant:
            scope_tag = f"[{m.scope.value}]" if m.scope != MemoryScope.GLOBAL else ""
            type_tag = self._type_label(m)
            decay_info = ""
            if m.auto_decay and m.status == MemoryStatus.ACTIVE:
                decay_info = f" [decay:{m.decay_score}]"
                if m.decay_score >= 80:
                    decay_info += " ← 用戶仍需要詳細解釋"
                elif m.decay_score >= 40:
                    decay_info += " ← 用戶正在進步，可適度簡化"
                else:
                    decay_info += " ← 即將淡出"
            lines.append(f"- {type_tag}{scope_tag}: {m.content} (priority: {m.priority}){decay_info}")

        return MEMORY_INJECTION_TEMPLATE.format(memories="\n".join(lines))

    def _type_label(self, m: Memory) -> str:
        labels = {
            "preference": "[偏好]",
            "rule": "[規則]",
            "method": "[方法]",
            "temporary": "[暫時]",
        }
        return labels.get(m.type.value if hasattr(m.type, 'value') else m.type, "[?]")
