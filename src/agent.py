"""Agent orchestrator. Signal capture is deterministic (regex).
Semantic grouping and classification is done by Claude Code via SKILL.md contract."""
import re
from typing import Optional
from src.models import (
    Signal, Memory, MemoryState,
    RULE_MIN, MATURE_THRESHOLD, RAW_MAX, JIT_TOP_K,
)
from src.memory_store import MemoryStore
from src.signal_capture import SignalCapture
from src.classifier import Classifier


class Agent:
    def __init__(self):
        self.store = MemoryStore()
        self.capture = SignalCapture()
        self.classifier = Classifier()
        self._signal_pool: list[Signal] = []
        self._pulse_session_start_sent: bool = False
        self._pulse_last_upgrade_count: int = 0
        self._pulse_last_milestone: int = 0

    # ── Public API ──────────────────────────────────────────────

    def process_dialog(self, text: str, context: dict) -> dict:
        """Capture signals from user dialog (Track A: regex). Classification is done by Claude Code."""
        sig = self.capture.capture_dialog(text, context)

        if sig is None:
            return {"phase": "no_signal"}

        return self._add_to_pool(sig)

    def add_signal(self, text: str, dialog_type: str, context: dict, red_line: bool = False) -> dict:
        """Track B: Claude Code manually adds a signal that regex missed.

        Use this when you observe an implied correction, weak feedback,
        or any useful signal that regex didn't catch.
        """
        from src.models import Signal
        sig = Signal(
            source="dialog",
            dialog_type=dialog_type,
            content=text,
            context=context,
            red_line=red_line,
        )
        return self._add_to_pool(sig)

    def _add_to_pool(self, sig) -> dict:
        """Internal: add signal to pool with exact-match dedup."""
        existing = self._find_exact_match(sig)
        if existing:
            existing.trigger_count += 1
            sig = existing
        else:
            self._signal_pool.append(sig)

        return {
            "phase": "observed",
            "signal_ids": [sig.id],
            "trigger_count": sig.trigger_count,
            "red_line": sig.red_line,
        }

    def get_pending_signals(self, min_count: int = 1) -> list[dict]:
        """Return signals needing classification. Called by Claude Code.

        Claude Code reads these, semantically groups related ones,
        and classifies them into structured memories.
        """
        pending = []
        for sig in self._signal_pool:
            if sig.trigger_count >= min_count:
                pending.append({
                    "id": sig.id,
                    "source": sig.source,
                    "dialog_type": sig.dialog_type,
                    "diff_type": sig.diff_type,
                    "content": sig.content,
                    "context": sig.context,
                    "trigger_count": sig.trigger_count,
                    "red_line": sig.red_line,
                })
        return pending

    def classify_and_save(self, signal_id: str, classification: dict) -> Optional[Memory]:
        """Save a Claude-classified memory. Called after Claude processes pending signals."""
        # ── Validation ──
        rule_content = (classification.get("rule_content", "") or "").strip()
        if not rule_content:
            return None  # Empty rule — reject

        valid_types = {"preference", "rule", "workflow", "method"}
        mem_type = classification.get("type", "preference")
        if mem_type not in valid_types:
            mem_type = "preference"  # Fallback

        confidence = classification.get("confidence", MATURE_THRESHOLD)
        confidence = max(0, min(100, confidence))  # Clamp 0-100

        # ── Build memory ──
        source_ids = [signal_id]
        if "related_signal_ids" in classification:
            source_ids.extend(classification["related_signal_ids"])

        memory = Memory(
            rule_content=rule_content,
            type=mem_type,
            scope=classification.get("scope", "global"),
            scope_value=classification.get("scope_value", ""),
            condition=classification.get("condition", ""),
            principle=classification.get("principle", ""),
            confidence=confidence,
            state="active",
            source_signals=source_ids,
        )
        self.store.save_memory(memory)

        # Remove classified signals from pool
        for sid in source_ids:
            self._signal_pool = [s for s in self._signal_pool if s.id != sid]

        return memory

    def handle_confirmation_response(self, memory_id: str, response: str) -> dict:
        memory = self.store.get_memory(memory_id)
        if not memory:
            return {"error": "memory not found"}

        r = response.strip().lower()
        if any(w in r for w in ["好", "可以", "嗯", "對", "对", "yes", "ok", "y"]):
            memory.confidence = RULE_MIN
            self.store.save_memory(memory)
            return {"action": "upgraded_to_rule", "memory_id": memory_id, "confidence": memory.confidence}

        if any(w in r for w in ["不要", "不行", "不對", "不对", "no", "n"]):
            memory.confidence = 10
            self.store.save_memory(memory)
            return {"action": "downgraded", "memory_id": memory_id, "confidence": memory.confidence}

        return {"action": "unclear", "memory_id": memory_id}

    def get_jit_memories(self, project: str = "", directory: str = "", file_extension: str = "") -> list[Memory]:
        return self.store.search_by_context(
            project=project, directory=directory, file_extension=file_extension,
            min_confidence=RULE_MIN,
        )

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

    # ── Internal ────────────────────────────────────────────────

    def _find_exact_match(self, sig: Signal) -> Optional[Signal]:
        """Basic exact-match dedup. Claude handles semantic grouping later."""
        for s in self._signal_pool:
            if s.content.strip().lower() == sig.content.strip().lower() and s.source == sig.source:
                return s
        return None

    # ── For test/replay: batch classify locally without requiring Claude ──

    def classify_all_pending_local(self):
        """Local fallback: classify ALL pending signals without Claude.
        In production, Claude Code handles this with semantic grouping.
        Here we just convert every signal into a basic memory.
        """
        for sig in list(self._signal_pool):
            memory = self.classifier.classify_local(sig, [])
            if memory:
                memory.confidence = 60 if sig.red_line else 40
                self.store.save_memory(memory)
                self._signal_pool.remove(sig)
