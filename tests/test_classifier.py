"""Tests for classifier.py"""
from unittest.mock import patch, MagicMock
from src.models import Signal, Memory
from src.classifier import Classifier


def test_should_trigger_llm_below_3():
    c = Classifier(api_key="test", base_url="https://test.com", model="test-model")
    sig = Signal(content="test", trigger_count=2, red_line=False)
    assert c.should_trigger_llm(sig) is False


def test_should_trigger_llm_at_3():
    c = Classifier(api_key="test", base_url="https://test.com", model="test-model")
    sig = Signal(content="test", trigger_count=3, red_line=False)
    assert c.should_trigger_llm(sig) is True


def test_should_trigger_llm_red_line_immediately():
    c = Classifier(api_key="test", base_url="https://test.com", model="test-model")
    sig = Signal(content="test", trigger_count=1, red_line=True)
    assert c.should_trigger_llm(sig) is True


def test_parse_classification_result():
    c = Classifier(api_key="test", base_url="https://test.com", model="test-model")
    result = {
        "rule_content": "use snake_case",
        "type": "preference",
        "scope": "global",
        "scope_value": "",
        "condition": "IF writing Python THEN use snake_case",
        "principle": "User prefers snake_case naming convention",
    }
    mem = c.parse_result(result, ["sig-1"])
    assert mem.rule_content == "use snake_case"
    assert mem.type == "preference"
    assert mem.scope == "global"
    assert mem.source_signals == ["sig-1"]


def test_red_line_start_confidence():
    c = Classifier(api_key="test", base_url="https://test.com", model="test-model")
    assert c.get_start_confidence(red_line=True) == 60


def test_normal_start_confidence():
    c = Classifier(api_key="test", base_url="https://test.com", model="test-model")
    conf = c.get_start_confidence(red_line=False)
    assert 40 <= conf <= 50
