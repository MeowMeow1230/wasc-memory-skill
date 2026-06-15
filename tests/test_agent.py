"""Tests for agent.py"""
from unittest.mock import patch
from src.agent import Agent
from src.models import Memory


def test_agent_init():
    agent = Agent(api_key="test", base_url="https://test.com", model="test")
    assert agent.store is not None
    assert agent.capture is not None
    assert agent.classifier is not None


def test_process_dialog_raw_signal():
    agent = Agent(api_key="test", base_url="https://test.com", model="test")
    agent.store.clear()
    result = agent.process_dialog("不要寫註解", {"project": "test", "directory": "src"})
    assert result["phase"] == "observed"
    assert len(result["signal_ids"]) >= 1
    assert len(agent.store.list_memories()) == 0


def test_process_dialog_multiple_triggers():
    agent = Agent(api_key="test", base_url="https://test.com", model="test")
    ctx = {"project": "test", "directory": "src"}
    # Patch classify to avoid real API call on the 3rd trigger (trigger_count hits 3)
    with patch.object(agent.classifier, "classify", return_value=None):
        for _ in range(3):
            agent.process_dialog("不要寫註解，程式碼應該自解釋", ctx)
    signals = agent._get_signals_by_content("不要寫註解")
    assert sum(s.trigger_count for s in signals) >= 3


def test_confirmation_accepted():
    agent = Agent(api_key="test", base_url="https://test.com", model="test")
    mem = Memory(rule_content="test", confidence=40, state="active")
    agent.store.save_memory(mem)
    result = agent.handle_confirmation_response(mem.id, "好")
    updated = agent.store.get_memory(mem.id)
    assert updated.confidence == 80
    assert result["action"] == "upgraded_to_rule"


def test_confirmation_rejected():
    agent = Agent(api_key="test", base_url="https://test.com", model="test")
    mem = Memory(rule_content="test", confidence=40, state="active")
    agent.store.save_memory(mem)
    result = agent.handle_confirmation_response(mem.id, "不要")
    updated = agent.store.get_memory(mem.id)
    assert updated.confidence <= 30
    assert result["action"] == "downgraded"


def test_jit_injection():
    agent = Agent(api_key="test", base_url="https://test.com", model="test")
    agent.store.save_memory(Memory(
        rule_content="use snake_case", scope="global", scope_value="",
        confidence=85, state="active",
    ))
    agent.store.save_memory(Memory(
        rule_content="commit before edit", scope="repo",
        scope_value="/Users/kun/test-project", confidence=80, state="active",
    ))
    injected = agent.get_jit_memories(project="/Users/kun/test-project", directory="src")
    assert len(injected) >= 1


def test_conflict_resolution():
    agent = Agent(api_key="test", base_url="https://test.com", model="test")
    old = agent.store.save_memory(Memory(
        rule_content="always add comments", confidence=80, state="active",
    ))
    new = agent.store.save_memory(Memory(
        rule_content="never add comments to internal code", confidence=80,
        state="active", scope="directory", scope_value="src/internal",
    ))
    conflicts = agent.detect_conflicts(new, [old])
    assert len(conflicts) == 0  # Different scope = not a conflict


def test_get_pulse_session_start():
    agent = Agent(api_key="test", base_url="https://test.com", model="test")
    agent.store.save_memory(Memory(
        rule_content="use snake_case", scope="global", confidence=85, state="active",
    ))
    pulse = agent.get_pulse()
    assert pulse is not None
    assert pulse["type"] == "session_start"
    assert "snake_case" in pulse["message"] or "偏好" in pulse["message"]


def test_get_pulse_milestone():
    agent = Agent(api_key="test", base_url="https://test.com", model="test")
    agent.store.clear()
    for i in range(6):
        agent.store.save_memory(Memory(
            rule_content=f"rule {i}", scope="global", confidence=85, state="active",
        ))
    # Session start already fired once, but milestone should fire for 5+ memories
    pulse = agent.get_pulse()
    # The first call gets session_start, second call should be milestone
    # Simulate calling get_pulse multiple times
    agent._pulse_session_start_sent = True  # skip session start
    agent._pulse_last_upgrade_count = 99  # skip rule upgrade, force milestone
    pulse2 = agent.get_pulse()
    assert pulse2 is not None
    assert pulse2["type"] == "milestone"
