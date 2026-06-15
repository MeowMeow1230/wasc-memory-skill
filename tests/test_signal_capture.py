"""Tests for signal_capture.py"""
from src.signal_capture import SignalCapture
from src.models import Signal


def test_detect_correction():
    cap = SignalCapture()
    sig = cap.capture_dialog("不要用 camelCase，用 snake_case", context={"project": "test"})
    assert sig is not None
    assert sig.source == "dialog"
    assert sig.dialog_type == "correction"
    assert "snake_case" in sig.content


def test_detect_pre_instruction():
    cap = SignalCapture()
    sig = cap.capture_dialog("先找論文再開始做", context={"project": "test"})
    assert sig is not None
    assert sig.dialog_type == "pre_instruction"


def test_detect_red_line_absolute_negation():
    cap = SignalCapture()
    sig = cap.capture_dialog("絕對不要用 class component，永遠用 hooks", context={"project": "test"})
    assert sig is not None
    assert sig.red_line is True


def test_detect_red_line_never():
    cap = SignalCapture()
    sig = cap.capture_dialog("never use var, always use const", context={"project": "test"})
    assert sig is not None
    assert sig.red_line is True


def test_no_signal_for_ordinary_text():
    cap = SignalCapture()
    sig = cap.capture_dialog("這個函數的複雜度有點高", context={"project": "test"})
    assert sig is None


def test_classify_style_edit():
    cap = SignalCapture()
    diff_content = "-  let userName = 'john'\n+  let user_name = 'john'"
    result = cap.classify_diff(diff_content, "test.py")
    assert result["diff_type"] == "style_edit"


def test_classify_structure_rewrite():
    cap = SignalCapture()
    diff_content = "-  def fetch():\n-      return requests.get(url)\n+  async def fetch():\n+      return await aiohttp.get(url)"
    result = cap.classify_diff(diff_content, "api.py")
    assert result["diff_type"] == "structure_rewrite"


def test_classify_full_delete():
    cap = SignalCapture()
    result = cap.classify_diff("", "handler.py", ai_wrote_lines=20, user_kept_lines=0)
    assert result["diff_type"] == "full_delete"


def test_compromise_detection():
    cap = SignalCapture()
    sig = cap.capture_dialog("OK 可以", context={"project": "test", "file": "api.py"})
    cap.record_file_accept("api.py", "a" * 200)
    result = cap.check_compromise("api.py", "b" * 50, within_minutes=10)
    assert result is True
