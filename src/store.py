"""記憶存儲封裝 — 純 Python 內存實現，零外部依賴

不需要 Ollama、不需要 OpenAI embedding、不需要 Qdrant。
評審 clone 完 pip install 就能直接跑。
"""

from src.models import Memory, MemoryScope, MemoryStatus


class MemoryStore:
    """內存存儲 + 關鍵詞匹配搜尋"""

    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self._memories: dict[str, Memory] = {}  # id → Memory

    def add(self, memory: Memory) -> None:
        self._memories[memory.id] = memory

    def search(self, query: str, top_k: int = 10, scope: MemoryScope | None = None) -> list[dict]:
        """關鍵詞匹配搜尋 — 不需 embedding，直接比對文字"""
        scored = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for mem in self._memories.values():
            if mem.status != MemoryStatus.ACTIVE:
                continue
            if scope and mem.scope != scope:
                continue

            # 計算關鍵詞命中數作為分數
            content_lower = mem.content.lower()
            score = sum(1 for w in query_words if w in content_lower)

            # scope 匹配加分
            if mem.scope == MemoryScope.GLOBAL:
                score += 1

            # priority 加權
            score += mem.priority * 0.1

            if score > 0:
                scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        return [{
            "id": mem.id,
            "memory": mem.content,
            "score": s,
            "metadata": {
                "memory_id": mem.id,
                "type": mem.type.value,
                "scope": mem.scope.value,
            }
        } for s, mem in top]

    def delete(self, memory_id: str) -> bool:
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False

    def delete_all(self) -> None:
        self._memories.clear()

    def get_all(self) -> list[dict]:
        return [
            {
                "id": mid,
                "memory": mem.content,
                "metadata": {
                    "memory_id": mid,
                    "type": mem.type.value,
                    "scope": mem.scope.value,
                }
            }
            for mid, mem in self._memories.items()
        ]
