"""Tests for memory_store.py"""
import json
import os
import tempfile
from datetime import datetime, timedelta
from src.models import Memory, Signal, MemoryType, MemoryScope, MemoryState
from src.memory_store import MemoryStore


def _new_store():
    """Create a MemoryStore backed by a temp file for test isolation."""
    fd, path = tempfile.mkstemp(suffix=".json", prefix="memtest_")
    os.close(fd)
    os.remove(path)
    return MemoryStore(path=path)


def test_store_save_and_load():
    store = _new_store()
    mem = Memory(
        rule_content="use snake_case for Python variables",
        type="preference",
        scope="global",
        scope_value="",
        confidence=50,
        state="active",
        source_signals=["sig-1", "sig-2"],
    )
    store.save_memory(mem)
    all_mems = store.list_memories()
    assert len(all_mems) == 1
    assert all_mems[0].rule_content == mem.rule_content
    assert all_mems[0].source_signals == ["sig-1", "sig-2"]


def test_store_delete():
    store = _new_store()
    mem = store.save_memory(Memory(rule_content="test delete"))
    assert store.get_memory(mem.id) is not None
    store.delete_memory(mem.id)
    assert store.get_memory(mem.id) is None


def test_store_clear():
    store = _new_store()
    store.save_memory(Memory(rule_content="test 1"))
    store.save_memory(Memory(rule_content="test 2"))
    assert len(store.list_memories()) == 2
    store.clear()
    assert len(store.list_memories()) == 0


def test_confidence_upgrade():
    store = _new_store()
    mem = store.save_memory(Memory(rule_content="test", confidence=30, state="active"))
    store.set_confidence(mem.id, 50)
    updated = store.get_memory(mem.id)
    assert updated.confidence == 50


def test_confidence_decay():
    store = _new_store()
    mem = store.save_memory(Memory(
        rule_content="test", confidence=45, state="active",
        last_triggered=(datetime.now() - timedelta(hours=24)).isoformat(),
    ))
    store.apply_decay(mem.id, miss_count=3, is_mature=True)
    updated = store.get_memory(mem.id)
    assert updated.confidence < 45


def test_get_by_scope():
    store = _new_store()
    store.save_memory(Memory(rule_content="global rule", scope="global", scope_value="", confidence=80))
    store.save_memory(Memory(rule_content="project rule", scope="repo", scope_value="/Users/kun/foo", confidence=80))
    store.save_memory(Memory(rule_content="dir rule", scope="directory", scope_value="src/components", confidence=80))
    results = store.search_by_context(project="/Users/kun/foo", directory="src/components")
    assert len(results) >= 2


def test_edit_memory():
    store = _new_store()
    mem = store.save_memory(Memory(rule_content="original"))
    store.edit_memory(mem.id, {"rule_content": "updated", "confidence": 85})
    updated = store.get_memory(mem.id)
    assert updated.rule_content == "updated"
    assert updated.confidence == 85
