"""Agent 主邏輯 — 組合記憶分類器、仲裁器、注入器，處理每次對話"""

from datetime import datetime
from src.llm import LLMClient
from src.models import Memory, MemoryType, MemoryScope, MemoryStatus
from src.store import MemoryStore
from src.extractor import MemoryExtractor
from src.arbitrator import ConflictArbitrator
from src.injector import MemoryInjector


class MemoryAgent:
    """具備自成長記憶能力的程式開發助手 Agent"""

    def __init__(self, client: LLMClient, store: MemoryStore):
        self.client = client
        self.store = store

        # 子組件
        self.extractor = MemoryExtractor(client)
        self.arbitrator = ConflictArbitrator()
        self.injector = MemoryInjector(store)

        # 內存中的記憶列表（與 Mem0 同步）
        self.memories: list[Memory] = []
        self.conversation_history: list[dict] = []

    def reset(self) -> dict:
        """完全重置記憶和對話歷史"""
        self.store.delete_all()
        self.memories = []
        self.conversation_history = []
        return {"status": "reset_complete", "memory_count": 0}

    def view_memories(self, include_deprecated: bool = False) -> list[dict]:
        """查看所有記憶"""
        mems = self.memories
        if not include_deprecated:
            mems = [m for m in mems if m.status == MemoryStatus.ACTIVE]
        return [m.to_view() for m in mems]

    def edit_memory(self, memory_id: str, updates: dict) -> dict:
        """編輯指定記憶的欄位"""
        for m in self.memories:
            if m.id == memory_id:
                for key, value in updates.items():
                    if hasattr(m, key):
                        setattr(m, key, value)
                m.updated_at = datetime.now().isoformat()
                # 更新 Mem0 中的記錄：刪舊存新
                self.store.delete(memory_id)
                self.store.add(m)
                return {"status": "updated", "memory": m.to_view()}
        return {"status": "not_found", "memory_id": memory_id}

    def delete_memory(self, memory_id: str) -> dict:
        """刪除指定記憶"""
        self.store.delete(memory_id)
        self.memories = [m for m in self.memories if m.id != memory_id]
        return {"status": "deleted", "memory_id": memory_id}

    def chat(self, user_message: str) -> str:
        """處理一次對話：注入記憶 → 呼叫 LLM → 提取新記憶 → 仲裁衝突 → 存儲"""

        # 1. 注入相關記憶到 system prompt
        memory_block = self.injector.inject(user_message, self.memories)
        system_prompt = self._build_system_prompt(memory_block)

        # 2. 呼叫 LLM
        reply = self.client.chat(
            messages=self.conversation_history + [
                {"role": "user", "content": user_message}
            ],
            system=system_prompt,
            max_tokens=4096,
        )

        # 3. 記錄對話
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": reply})

        # 4. 判斷用戶訊息是本質反饋還是臨時任務
        msg_type = self.extractor.classify_feedback(user_message, user_message)

        # 5. 如果是反饋，提取新記憶
        if msg_type == "feedback":
            new_memories = self.extractor.extract(user_message, self.memories)

            # 偵測用戶是否在尋求解釋（新手特徵）
            explain_kw = ["為什麼", "怎麼操作", "如何", "解釋", "說明", "不懂",
                         "why", "how to", "explain", "help me understand"]
            user_is_learning = any(kw in user_message.lower() for kw in explain_kw)

            # 6. 對每條新記憶做衝突仲裁
            for new_mem in new_memories:
                # method 型 + 用戶在學 → 啟用自動衰退
                if new_mem.type == MemoryType.METHOD and user_is_learning:
                    new_mem.auto_decay = True
                    new_mem.decay_score = 100

                to_keep, to_deprecate = self.arbitrator.resolve(
                    new_mem, self.memories
                )

                for mem in to_keep:
                    self.memories.append(mem)
                    self.store.add(mem)

                for mem in to_deprecate:
                    mem.status = MemoryStatus.DEPRECATED

        # 7. 自動衰退掃描：檢查哪些 auto_decay 記憶該扣分/強化
        self._process_decay(user_message)

        return reply

    def _is_learning_behavior(self, msg: str) -> bool:
        """偵測用戶是否在尋求解釋、學習"""
        kw = ["為什麼", "怎麼操作", "如何運作", "解釋", "說明一下", "不懂",
              "詳細", "每一步", "why", "how to", "explain", "step by step",
              "help me understand", "what does", "can you explain"]
        return any(k in msg.lower() for k in kw)

    def _process_decay(self, user_message: str):
        """掃描所有 auto_decay 記憶：精準匹配主題 → 強化 or 衰退"""
        user_is_learning = self._is_learning_behavior(user_message)

        # 第一優先：用戶在學習但尚無匹配的 auto_decay 記憶 → 自動創建
        if user_is_learning:
            topic = self._guess_topic(user_message)
            has_matching = any(
                m.auto_decay and m.status == MemoryStatus.ACTIVE and m.decay_topic == topic
                for m in self.memories
            )
            if not has_matching:
                explain_mem = Memory(
                    type=MemoryType.METHOD,
                    content=f"用戶需要關於 {topic} 的詳細解釋",
                    scope=MemoryScope.GLOBAL,
                    priority=7,
                    source=f"自動偵測: {user_message[:60]}",
                    auto_decay=True,
                    decay_score=100,
                    decay_topic=topic,
                )
                self.memories.append(explain_mem)
                try:
                    self.store.add(explain_mem)
                except Exception:
                    pass

        for mem in self.memories:
            if not mem.auto_decay or mem.status != MemoryStatus.ACTIVE:
                continue

            # 精準匹配：只有該主題的衰退記憶才受此訊息影響
            topic_match = (
                not mem.decay_topic or  # 無主題 → 通用，全部影響
                mem.decay_topic.lower() in user_message.lower() or
                any(kw in user_message.lower() for kw in mem.decay_topic.lower().split(","))
            )

            if user_is_learning and topic_match:
                mem.reinforce()
            elif not topic_match:
                # 不相關主題 → 跳過，不扣分也不加分
                continue
            else:
                mem.decay(amount=20)

    def _guess_topic(self, msg: str) -> str:
        """從用戶訊息中猜測學習主題"""
        topics = {
            "React": ["react", "component", "jsx", "hook", "useState", "useEffect", "props", "state"],
            "TypeScript": ["typescript", "type", "interface", "generic", "strict"],
            "Testing": ["test", "vitest", "jest", "mock", "assert"],
            "CSS": ["css", "style", "tailwind", "layout", "flex"],
            "Python": ["python", "django", "flask", "pip"],
        }
        msg_lower = msg.lower()
        for topic, keywords in topics.items():
            if any(kw in msg_lower for kw in keywords):
                return topic
        return "General"

    def _build_system_prompt(self, memory_block: str) -> str:
        base = """你是一個程式開發助手，能夠記住用戶的偏好和規則。

當用戶給你反饋時（例如 "我偏好 TypeScript"、"以後都用 functional component"），
記住這些偏好並在後續對話中自動應用。

如果記憶區塊中有用戶偏好，請在回答時主動應用這些偏好，
不需要等用戶再次提醒。"""
        if memory_block:
            return base + "\n\n" + memory_block
        return base
