"""Agent orchestrator: five-stage pipeline with learning/application phases and learning pulse."""
import os
import re
from typing import Optional
from src.models import (
    Signal, Memory, MemoryState, MemoryScope,
    RULE_MIN, MATURE_THRESHOLD, RAW_MAX, JIT_TOP_K,
)
from src.memory_store import MemoryStore
from src.signal_capture import SignalCapture
from src.classifier import Classifier


class Agent:
    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.store = MemoryStore()
        self.capture = SignalCapture()
        self.classifier = Classifier(
            api_key=api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
            base_url=base_url or os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"),
            model=model or os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro"),
        )
        self._signal_pool: list[Signal] = []
        self._pending_confirmations: dict[str, Memory] = {}
        self._pulse_session_start_sent: bool = False
        self._pulse_last_upgrade_count: int = 0
        self._pulse_last_milestone: int = 0

    def process_dialog(self, text: str, context: dict) -> dict:
        sig = self.capture.capture_dialog(text, context)
        if sig is None:
            return {"phase": "no_signal"}

        existing = self._find_similar_signal(sig)
        if existing:
            existing.trigger_count += 1
            sig = existing
        else:
            self._signal_pool.append(sig)

        result = {
            "phase": "observed",
            "signal_ids": [sig.id],
            "need_confirmation": False,
            "confirmation_message": None,
            "injected_memories": [],
        }

        if self.classifier.should_trigger_llm(sig):
            related = self._get_related_signals(sig)
            active_mems = self.store.list_memories(state="active")
            memory = self.classifier.classify(sig, related, active_mems)
            if memory:
                memory.confidence = self.classifier.get_start_confidence(red_line=sig.red_line)
                self.store.save_memory(memory)
                result["phase"] = "classified"
                result["memory_id"] = memory.id
                if memory.confidence >= MATURE_THRESHOLD and memory.confidence < RULE_MIN:
                    self._pending_confirmations[memory.id] = memory
                    result["need_confirmation"] = True
                    result["confirmation_message"] = self._build_confirmation_message(memory)

        return result

    def handle_confirmation_response(self, memory_id: str, response: str) -> dict:
        memory = self.store.get_memory(memory_id)
        if not memory:
            return {"error": "memory not found"}

        response_lower = response.strip().lower()

        if any(word in response_lower for word in ["好", "可以", "嗯", "對", "对", "yes", "ok", "y"]):
            if any(limit_word in response for limit_word in ["專案", "项目", "project", "這個", "这个"]):
                memory.scope = "repo"
                memory.scope_value = self._extract_scope_from_response(response)
            memory.confidence = RULE_MIN
            self.store.save_memory(memory)
            self._pending_confirmations.pop(memory_id, None)
            return {"action": "upgraded_to_rule", "memory_id": memory_id, "confidence": memory.confidence}

        if any(word in response_lower for word in ["不要", "不行", "不對", "不对", "no", "n"]):
            memory.confidence = 10
            self.store.save_memory(memory)
            self._pending_confirmations.pop(memory_id, None)
            return {"action": "downgraded", "memory_id": memory_id, "confidence": memory.confidence}

        return {"action": "unclear", "memory_id": memory_id}

    def get_jit_memories(self, project: str = "", directory: str = "", file_extension: str = "") -> list[Memory]:
        return self.store.search_by_context(
            project=project, directory=directory, file_extension=file_extension,
            min_confidence=RULE_MIN,
        )

    def detect_conflicts(self, new_memory: Memory, existing_memories: list[Memory]) -> list[Memory]:
        conflicts = []
        for old in existing_memories:
            if old.id == new_memory.id:
                continue
            if old.scope != new_memory.scope or old.scope_value != new_memory.scope_value:
                continue
            if self._topic_overlap(new_memory.rule_content, old.rule_content) and new_memory.rule_content != old.rule_content:
                conflicts.append(old)
        return conflicts

    def resolve_conflict(self, new_memory: Memory, old_memory: Memory):
        if new_memory.confidence >= old_memory.confidence:
            old_memory.state = MemoryState.DEPRECATED.value
            self.store.save_memory(old_memory)

    def get_summary(self) -> dict:
        all_mems = self.store.list_memories()
        return {
            "total": len(all_mems),
            "active": sum(1 for m in all_mems if m.state == "active"),
            "deprecated": sum(1 for m in all_mems if m.state == "deprecated"),
            "archived": sum(1 for m in all_mems if m.state == "archived"),
            "by_confidence": {
                "raw": sum(1 for m in all_mems if m.confidence <= RAW_MAX),
                "mature": sum(1 for m in all_mems if RAW_MAX < m.confidence < RULE_MIN),
                "rule": sum(1 for m in all_mems if m.confidence >= RULE_MIN),
            },
        }

    def get_pulse(self) -> Optional[dict]:
        all_mems = self.store.list_memories()
        active = [m for m in all_mems if m.state == "active"]
        rules = [m for m in active if m.confidence >= RULE_MIN]
        matures = [m for m in active if MATURE_THRESHOLD <= m.confidence < RULE_MIN]

        if not self._pulse_session_start_sent:
            self._pulse_session_start_sent = True
            if active:
                return {
                    "type": "session_start",
                    "message": f"歡迎回來。上次學到 {len(active)} 條偏好（{len(rules)} 條已自動套用、{len(matures)} 條學習中）。`view` 查看。"
                }

        if len(rules) > self._pulse_last_upgrade_count:
            newest = rules[-1]
            self._pulse_last_upgrade_count = len(rules)
            return {
                "type": "rule_upgraded",
                "message": f"PS: 新規則已成熟：「{newest.rule_content[:60]}」。`view` 查看全部。",
                "memory_id": newest.id,
            }

        current_milestone = len(active) // 5
        if current_milestone > self._pulse_last_milestone:
            self._pulse_last_milestone = current_milestone
            return {
                "type": "milestone",
                "message": f"目前共 {len(active)} 條偏好，{len(rules)} 條已自動套用。你最近很少有重複糾正了。",
            }

        return None

    def _find_similar_signal(self, sig: Signal) -> Optional[Signal]:
        for s in self._signal_pool:
            if s.content == sig.content and s.source == sig.source:
                return s
        return None

    def _get_related_signals(self, sig: Signal) -> list[Signal]:
        return [s for s in self._signal_pool if s.id != sig.id and s.content == sig.content]

    def _get_signals_by_content(self, content: str) -> list[Signal]:
        return [s for s in self._signal_pool if content in s.content]

    def _build_confirmation_message(self, memory: Memory) -> str:
        return f"PS: 我注意到 {memory.rule_content}，以後 {memory.condition or '這樣做'} 好嗎？"

    def _extract_scope_from_response(self, response: str) -> str:
        m = re.search(r'(?:專案|项目|project|這個|这个)\s*[:：]?\s*(\S+)', response)
        return m.group(1) if m else ""

    def _topic_overlap(self, text_a: str, text_b: str) -> bool:
        a_words = set(text_a.lower().split())
        b_words = set(text_b.lower().split())
        stop = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is", "are", "be", "的", "了", "在", "是", "有", "和", "就", "都", "也"}
        a_clean = a_words - stop
        b_clean = b_words - stop
        return len(a_clean & b_clean) >= 2 if a_clean and b_clean else False
