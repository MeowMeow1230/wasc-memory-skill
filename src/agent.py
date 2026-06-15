"""Agent orchestrator: five-stage pipeline with implicit confirmation and project-scoped preferences."""
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
        self.classifier = Classifier()
        self._signal_pool: list[Signal] = []
        self._pending_confirmations: dict[str, Memory] = {}
        self._pulse_session_start_sent: bool = False
        self._pulse_last_upgrade_count: int = 0
        self._pulse_last_milestone: int = 0
        # Implicit confirmation: per-project tracking
        self._last_correction: dict[str, str] = {}   # project -> signal_id
        self._last_correction_norm: dict[str, str] = {}  # project -> normalized_topic
        self._pending_classifications: list[Signal] = []  # signals awaiting Claude classification

    # ── Public API ──────────────────────────────────────────────

    def process_dialog(self, text: str, context: dict) -> dict:
        """Process a user dialog message."""
        project = context.get("project", "default")
        sig = self.capture.capture_dialog(text, context)

        result = {
            "phase": "no_signal",
            "signal_ids": [],
            "need_confirmation": False,
            "confirmation_message": None,
            "implicitly_confirmed": False,
            "injected_memories": [],
        }

        # ── Step 0: Implicit confirmation ──
        # User didn't re-correct next turn → AI understood → accelerate learning
        is_correction_now = sig and sig.dialog_type == "correction"
        was_awaiting = project in self._last_correction

        if was_awaiting and not is_correction_now:
            self._apply_implicit_confirmation(project)
            result["implicitly_confirmed"] = True

        if sig is None:
            return result

        # ── Step 1: Dedup ──
        existing = self._find_similar_signal(sig)
        if existing:
            existing.trigger_count += 1
            existing.context = {**existing.context, **context}
            sig = existing
        else:
            self._signal_pool.append(sig)

        result["phase"] = "observed"
        result["signal_ids"] = [sig.id]

        # Track correction for implicit confirmation
        if sig.dialog_type == "correction":
            self._last_correction[project] = sig.id
            self._last_correction_norm[project] = self._normalize_signal(sig.content)

        # ── Step 2: LLM classification ──
        if self.classifier.should_trigger_llm(sig):
            result = self._run_classifier(sig, project, result)

        return result

    def handle_confirmation_response(self, memory_id: str, response: str) -> dict:
        memory = self.store.get_memory(memory_id)
        if not memory:
            return {"error": "memory not found"}

        r = response.strip().lower()

        if any(w in r for w in ["好", "可以", "嗯", "對", "对", "yes", "ok", "y"]):
            if any(w in response for w in ["專案", "项目", "project", "這個", "这个"]):
                memory.scope = "repo"
                memory.scope_value = self._extract_scope_from_response(response)
            memory.confidence = RULE_MIN
            self.store.save_memory(memory)
            self._pending_confirmations.pop(memory_id, None)
            return {"action": "upgraded_to_rule", "memory_id": memory_id, "confidence": memory.confidence}

        if any(w in r for w in ["不要", "不行", "不對", "不对", "no", "n"]):
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

    # ── Implicit Confirmation ───────────────────────────────────

    def _apply_implicit_confirmation(self, project: str):
        """User didn't re-correct → accelerate both signals AND memories."""
        signal_id = self._last_correction.pop(project, None)
        norm_topic = self._last_correction_norm.pop(project, None)
        if not signal_id or not norm_topic:
            return

        # 1. Accelerate matching raw signals → reach LLM threshold faster
        sig_to_classify = None
        for sig in self._signal_pool:
            sig_norm = self._normalize_signal(sig.content)
            if self._word_overlap(sig_norm, norm_topic) >= 0.4:
                sig.trigger_count = max(sig.trigger_count, 3)  # fast-track past threshold
                sig.red_line = True
                sig_to_classify = sig
                break  # classify one at a time

        # 2. Directly classify the confirmed signal (user silence = validation)
        if sig_to_classify:
            self._run_classifier(sig_to_classify, project, {})

        # 3. Boost matching memories
        for mem in self.store.list_memories(state="active"):
            if mem.scope_value and mem.scope_value != project:
                continue
            if mem.confidence >= RULE_MIN:
                continue
            if self._topic_relates(mem.rule_content, norm_topic):
                boost = 15
                mem.confidence = min(RULE_MIN - 1, mem.confidence + boost)
                if mem.confidence >= 50:
                    mem.confidence = max(mem.confidence, 55)
                self.store.save_memory(mem)

    # ── Classification ──────────────────────────────────────────

    def _run_classifier(self, sig: Signal, project: str, result: dict) -> dict:
        """Queue signal for Claude Code classification (via SKILL.md contract).

        In test/replay mode (no Claude), uses classify_local() as fallback.
        """
        related = self._get_related_signals(sig, project)
        active_mems = self.store.list_memories(state="active")

        # Try local classifier first (works without API)
        memory = self.classifier.classify_local(sig, related)
        if memory:
            if not memory.scope_value:
                memory.scope_value = project
                memory.scope = "repo"
            memory.confidence = self.classifier.get_start_confidence(red_line=sig.red_line)
            self.store.save_memory(memory)
            result["phase"] = "classified"
            result["memory_id"] = memory.id
            if MATURE_THRESHOLD <= memory.confidence < RULE_MIN:
                self._pending_confirmations[memory.id] = memory
                result["need_confirmation"] = True
                result["confirmation_message"] = self._build_confirmation_message(memory)
        else:
            # Queue for Claude to process
            self._pending_classifications.append(sig)
            result["phase"] = "pending_classification"

        return result

    def get_pending_classifications(self) -> list[dict]:
        """Get signals awaiting Claude Code classification. Called by SKILL.md contract."""
        pending = []
        for sig in self._pending_classifications:
            related = self._get_related_signals(sig, "")
            active_mems = self.store.list_memories(state="active")
            request = self.classifier.format_request(sig, related, active_mems)
            pending.append({
                "signal_id": sig.id,
                "content": sig.content,
                "trigger_count": sig.trigger_count,
                "request": request,
            })
        self._pending_classifications.clear()
        return pending

    # ── Normalization & Dedup (deterministic, zero LLM) ─────────

    def _normalize_signal(self, text: str) -> str:
        """Extract core instruction from correction for dedup grouping. Regex only."""
        t = text.strip()
        t = re.sub(r'\s+', ' ', t).lower()
        t = re.sub(r'^(我说過|我說過|操[，,]?\s*|你又忘了\s*|講了多少次\s*|說了多少次\s*)', '', t)
        t = re.sub(r'[！!。，,]+$', '', t)
        # Strip truly generic verbs (only 用/使用) between negation and target
        t = re.sub(r'(不要|别|別|不应该|不應該|绝对不要|絕對不要|永遠不要|永远不要|不准|严禁|嚴禁)\s*(?:用|使用)\s*', r'\1', t)
        # Extract negation phrases
        negation_kws = r'(?:不要|别|別|不应该|不應該|绝对不要|絕對不要|永遠不要|永远不要|不准|严禁|嚴禁|不能)'
        negations = re.findall(negation_kws + r'[^！!。，,；;、\n' + "'" + r'"]+', t)
        if negations:
            cleaned = [re.sub(r'\s+', '', n) for n in negations]
            return ' '.join(sorted(set(cleaned)))
        # Fallback
        filler = {'你', '我', '他', '的', '了', '在', '是', '有', '和', '就', '都', '也', '吧', '嗎', '呢', '啊', '哦', '喔', '再', '又', '一直', '每次', '總是', '老是', '不要', '別'}
        tokens = [w for w in t.split() if w not in filler]
        return ' '.join(tokens[:6])

    def _find_similar_signal(self, sig: Signal) -> Optional[Signal]:
        norm = self._normalize_signal(sig.content)
        for s in self._signal_pool:
            if self._normalize_signal(s.content) == norm and s.source == sig.source:
                return s
        return None

    def _get_related_signals(self, sig: Signal, project: str = "") -> list[Signal]:
        norm = self._normalize_signal(sig.content)
        related = []
        for s in self._signal_pool:
            if s.id == sig.id:
                continue
            s_norm = self._normalize_signal(s.content)
            if s_norm == norm:
                related.append(s)
            elif s.context.get("project") == project:
                overlap = self._word_overlap(s_norm, norm)
                if overlap >= 0.5:
                    related.append(s)
        return related

    # ── Helpers ──────────────────────────────────────────────────

    def _get_signals_by_content(self, content: str) -> list[Signal]:
        return [s for s in self._signal_pool if content in s.content]

    def _topic_relates(self, rule_content: str, norm_topic: str) -> bool:
        return self._word_overlap(rule_content.lower(), norm_topic.lower()) >= 0.3

    def _word_overlap(self, a: str, b: str) -> float:
        wa = set(a.split())
        wb = set(b.split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / max(len(wa), len(wb))

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
