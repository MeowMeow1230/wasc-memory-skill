"""衝突仲裁器 — Scope 分級制，窄範圍例外不殺全局偏好"""

from src.models import Memory, MemoryType, MemoryScope, MemoryStatus, ConflictRecord


class ConflictArbitrator:
    """處理新舊記憶衝突，採用 scope 分級策略"""

    def __init__(self, similarity_threshold: float = 0.7):
        self.threshold = similarity_threshold

    def resolve(
        self,
        new_memory: Memory,
        existing_memories: list[Memory],
    ) -> tuple[list[Memory], list[Memory]]:
        """
        檢查新記憶是否與現有記憶衝突。
        返回: (要保留的記憶列表, 要標記為 deprecated 的記憶列表)
        """
        to_deprecate = []
        to_keep = [new_memory]

        # 只檢查 active 記憶
        active = [m for m in existing_memories if m.status == MemoryStatus.ACTIVE]

        for existing in active:
            if self._is_conflict(new_memory, existing):
                resolution = self._decide(new_memory, existing)
                if resolution == "replace":
                    existing.status = MemoryStatus.DEPRECATED
                    existing.conflict_history.append(ConflictRecord(
                        old_memory_id=existing.id,
                        old_content=existing.content,
                        resolution="new_replaced_old",
                    ))
                    to_deprecate.append(existing)
                elif resolution == "keep_both_narrower":
                    # 新記憶 scope 較窄，兩者都保留
                    # 不淘汰舊偏好，標註例外關係
                    new_memory.conflict_history.append(ConflictRecord(
                        old_memory_id=existing.id,
                        old_content=existing.content,
                        resolution="narrower_scope_kept_both",
                    ))
                elif resolution == "keep_old":
                    # 舊記憶優先級更高，不新增
                    to_keep.remove(new_memory)

        return to_keep, to_deprecate

    def _is_conflict(self, a: Memory, b: Memory) -> bool:
        """判斷兩條記憶是否存在潛在衝突（同領域但內容矛盾）"""
        # 不同 type 的不衝突
        if a.type != b.type:
            return False

        # 同一 type 且 scope 重疊才可能衝突
        if not self._scope_overlaps(a.scope, b.scope):
            return False

        # 檢查內容是否有矛盾關鍵詞
        return self._content_contradicts(a.content, b.content)

    def _scope_overlaps(self, a: MemoryScope, b: MemoryScope) -> bool:
        """判斷兩個 scope 是否有重疊"""
        if a == MemoryScope.GLOBAL or b == MemoryScope.GLOBAL:
            return True  # global 跟任何 scope 都有重疊
        if a == b:
            return True
        if a == MemoryScope.PROJECT and b == MemoryScope.FILE:
            return True
        if b == MemoryScope.PROJECT and a == MemoryScope.FILE:
            return True
        return False

    def _content_contradicts(self, content_a: str, content_b: str) -> bool:
        """簡單的關鍵詞矛盾檢測"""
        contradiction_pairs = [
            (["不要", "別", "禁止", "避免", "不用"], ["要用", "必須", "總是", "保持"]),
            (["functional", "function"], ["class", "OOP"]),
            (["named export"], ["default export"]),
            (["strict"], ["loose", "any"]),
            (["kebab-case"], ["camelCase", "PascalCase"]),
        ]

        for negative_words, positive_words in contradiction_pairs:
            a_neg = any(w in content_a for w in negative_words)
            a_pos = any(w in content_a for w in positive_words)
            b_neg = any(w in content_b for w in negative_words)
            b_pos = any(w in content_b for w in positive_words)

            if (a_neg and b_pos) or (a_pos and b_neg):
                return True

        return False

    def _decide(self, new_mem: Memory, existing: Memory) -> str:
        """決定衝突處理策略"""
        # Scope 優先級: global > project > file > temporary
        scope_rank = {
            MemoryScope.GLOBAL: 4,
            MemoryScope.PROJECT: 3,
            MemoryScope.FILE: 2,
            MemoryScope.TEMPORARY: 1,
        }

        new_rank = scope_rank[new_mem.scope]
        old_rank = scope_rank[existing.scope]

        # 新記憶 scope 更窄 → 保留兩者（例外不殺偏好）
        if new_rank < old_rank:
            return "keep_both_narrower"

        # 同等 scope → 看 priority
        if new_rank == old_rank:
            if new_mem.priority > existing.priority:
                return "replace"
            elif new_mem.priority < existing.priority:
                return "keep_old"
            else:
                # Priority 相同 → 新的取代舊的
                return "replace"

        # 新記憶 scope 更寬 → 取代
        if new_mem.type == MemoryType.TEMPORARY:
            return "keep_both_narrower"

        return "replace"
