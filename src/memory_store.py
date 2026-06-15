"""Memory store: local JSON CRUD with confidence tiers and time decay."""
import json
import os
from datetime import datetime, timedelta
from typing import Optional
from src.models import (
    Memory, RAW_MAX, RULE_MIN,
    MATURE_DECAY_MISSES, RULE_DECAY_MISSES,
    DEPRECATED_ARCHIVE_DAYS, JIT_TOP_K,
)


STORE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "memories.json")


class MemoryStore:
    def __init__(self, path: str = STORE_PATH):
        self.path = path
        self._ensure_store()

    def _ensure_store(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                json.dump([], f)

    def _load(self) -> list[dict]:
        with open(self.path, "r") as f:
            return json.load(f)

    def _save(self, data: list[dict]):
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def list_memories(self, state: Optional[str] = None) -> list[Memory]:
        data = self._load()
        mems = [Memory.from_dict(d) for d in data]
        if state:
            mems = [m for m in mems if m.state == state]
        return sorted(mems, key=lambda m: m.confidence, reverse=True)

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        data = self._load()
        for d in data:
            if d["id"] == memory_id:
                return Memory.from_dict(d)
        return None

    def save_memory(self, memory: Memory) -> Memory:
        data = self._load()
        for i, d in enumerate(data):
            if d["id"] == memory.id:
                data[i] = memory.to_dict()
                self._save(data)
                return memory
        data.append(memory.to_dict())
        self._save(data)
        return memory

    def delete_memory(self, memory_id: str) -> bool:
        data = self._load()
        new_data = [d for d in data if d["id"] != memory_id]
        if len(new_data) < len(data):
            self._save(new_data)
            return True
        return False

    def clear(self):
        self._save([])

    def set_confidence(self, memory_id: str, confidence: int):
        mem = self.get_memory(memory_id)
        if mem:
            mem.confidence = max(0, min(100, confidence))
            self.save_memory(mem)

    def apply_decay(self, memory_id: str, miss_count: int, is_mature: bool):
        mem = self.get_memory(memory_id)
        if not mem:
            return
        threshold = MATURE_DECAY_MISSES if is_mature else RULE_DECAY_MISSES
        if miss_count >= threshold:
            new_conf = max(0, mem.confidence - 30) if mem.confidence >= RULE_MIN else max(0, mem.confidence - 25)
            if new_conf <= RAW_MAX:
                if mem.confidence >= RULE_MIN:
                    mem.state = "deprecated"
                mem.confidence = new_conf
            else:
                if mem.confidence >= RULE_MIN:
                    mem.confidence = 50
            self.save_memory(mem)

    def archive_deprecated(self):
        data = self._load()
        cutoff = (datetime.now() - timedelta(days=DEPRECATED_ARCHIVE_DAYS)).isoformat()
        for d in data:
            if d["state"] == "deprecated" and d.get("last_triggered", "") < cutoff:
                d["state"] = "archived"
        self._save(data)

    def search_by_context(
        self, project: str = "", directory: str = "", file_extension: str = "", min_confidence: int = 40
    ) -> list[Memory]:
        all_mems = self.list_memories(state="active")
        scored = []
        for m in all_mems:
            if m.confidence < min_confidence:
                continue
            score = 0
            if m.scope == "directory" and m.scope_value and m.scope_value in directory:
                score += 30
            if m.scope == "repo" and m.scope_value and m.scope_value in project:
                score += 20
            if m.scope == "workspace" and m.scope_value and m.scope_value in project:
                score += 10
            if m.scope == "global":
                score += 5
            if file_extension and file_extension in m.condition:
                score += 5
            if score > 0:
                scored.append((m, score))
        scored.sort(key=lambda x: (x[1], x[0].confidence), reverse=True)
        return [m for m, _ in scored[:JIT_TOP_K]]

    def edit_memory(self, memory_id: str, updates: dict):
        mem = self.get_memory(memory_id)
        if not mem:
            return None
        for key, value in updates.items():
            if hasattr(mem, key):
                setattr(mem, key, value)
        mem.last_triggered = datetime.now().isoformat()
        self.save_memory(mem)
        return mem

    def touch(self, memory_id: str):
        mem = self.get_memory(memory_id)
        if mem:
            mem.last_triggered = datetime.now().isoformat()
            self.save_memory(mem)
