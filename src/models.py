"""記憶資料模型 — 完全自控結構，不依賴 Mem0 的黑盒提取"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class MemoryType(str, Enum):
    PREFERENCE = "preference"   # 長期偏好：coding style, 語言偏好
    RULE = "rule"               # 場景規則：命名規範, 檔案結構
    METHOD = "method"           # 工作方法：測試先行, 重構步驟
    TEMPORARY = "temporary"     # 暫時例外：某個檔案暫時放寬規則


class MemoryScope(str, Enum):
    GLOBAL = "global"           # 全局生效，最高優先級
    PROJECT = "project"         # 專案級
    FILE = "file"               # 檔案級例外
    TEMPORARY = "temporary"     # 暫時例外，有過期時間


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ConflictRecord(BaseModel):
    """衝突記錄"""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    old_memory_id: str
    old_content: str
    resolution: str  # "narrower_scope_kept_both" | "new_replaced_old" | "merged"


class Memory(BaseModel):
    """單條記憶"""
    id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:8]}")
    type: MemoryType
    content: str
    scope: MemoryScope = MemoryScope.GLOBAL
    priority: int = Field(default=5, ge=1, le=10)
    status: MemoryStatus = MemoryStatus.ACTIVE
    source: str = ""            # 來源：哪次對話/反饋
    conflict_history: list[ConflictRecord] = Field(default_factory=list)
    expires_at: Optional[str] = None  # temporary 記憶的過期時間
    # 自動衰退：用戶不再表現出某種需求時，記憶自動降權
    auto_decay: bool = False     # 是否啟用自動衰退（僅 method 型記憶建議設 true）
    decay_score: int = Field(default=100, ge=0, le=100)  # 100=剛強化, 0=自動淘汰
    decay_topic: str = ""        # 衰退主題關鍵詞（如 "React", "TypeScript"），用於精準匹配
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def reinforce(self):
        """觸發條件滿足時重設分數"""
        self.decay_score = 100
        self.updated_at = datetime.now().isoformat()

    def decay(self, amount: int = 20):
        """一次對話未觸發，扣分；扣到 0 以下自動 deprecated"""
        if not self.auto_decay:
            return
        self.decay_score = max(0, self.decay_score - amount)
        if self.decay_score <= 0:
            self.status = MemoryStatus.DEPRECATED
        self.updated_at = datetime.now().isoformat()

    def to_view(self) -> dict:
        """展示給用戶的格式"""
        base = {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "scope": self.scope.value,
            "priority": self.priority,
            "status": self.status.value,
            "source": self.source,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
        }
        if self.auto_decay:
            base["auto_decay"] = True
            base["decay_score"] = self.decay_score
        return base
