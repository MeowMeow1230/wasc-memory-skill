"""Signal capture: dialog regex + diff classification + red-line intercept."""
import re
import difflib
from datetime import datetime, timedelta
from typing import Optional
from src.models import Signal, SignalSource, DialogType, DiffType


CORRECTION_PATTERNS = [
    (re.compile(r'不要[再]?\s*(\S+)'), DialogType.CORRECTION),
    (re.compile(r'别[再]?\s*(\S+)'), DialogType.CORRECTION),
    (re.compile(r'应该\s*(\S+)'), DialogType.CORRECTION),
    (re.compile(r'你又忘了\s*(.+)'), DialogType.CORRECTION),
    (re.compile(r'不是这样[，\s]*(.+)'), DialogType.CORRECTION),
    (re.compile(r'改成?\s*(.+)'), DialogType.CORRECTION),
    (re.compile(r'不对[，\s]*(.+)'), DialogType.CORRECTION),
    (re.compile(r'错了[，\s]*(.+)'), DialogType.CORRECTION),
    (re.compile(r"don'?t\s+(\S+)", re.IGNORECASE), DialogType.CORRECTION),
]

PRE_INSTRUCTION_PATTERNS = [
    (re.compile(r'先找论文|先找論文|先搜一下|先查'), DialogType.PRE_INSTRUCTION),
    (re.compile(r'先讨论|先討論|不急[着做]|看一下再做'), DialogType.PRE_INSTRUCTION),
    (re.compile(r'直接做|直接改|馬上做'), DialogType.PRE_INSTRUCTION),
]

FEEDBACK_PATTERNS = [
    (re.compile(r'^(好|可以|OK|ok|行|沒問題)$'), DialogType.FEEDBACK),
    (re.compile(r'^(不行|不好|不對|不要|no)$'), DialogType.FEEDBACK),
]

RED_LINE_PATTERNS = [
    re.compile(r'絕對不要|永远不要|永遠不要|不准|严禁|嚴禁'),
    re.compile(r'never\s+(use|do|write|add)', re.IGNORECASE),
    re.compile(r'stop\s+doing', re.IGNORECASE),
    re.compile(r'我说过|我說過|讲了多少次|講了多少次|再三'),
    re.compile(r'最后一次说|最後一次說'),
]

ADDED_LINES_FOR_REWRITE = 3
DELETED_LINES_FOR_FULL_DELETE = 5


class SignalCapture:
    def __init__(self):
        self._file_accepts: dict[str, tuple[str, str]] = {}
        self._file_edits: dict[str, list[tuple[str, str]]] = {}
        self._consecutive_full_deletes: dict[str, int] = {}

    def capture_dialog(self, text: str, context: dict) -> Optional[Signal]:
        if not text or not text.strip():
            return None

        dialog_type = None
        is_red_line = False

        # Check red-line patterns first — independent of dialog type match
        for pattern in RED_LINE_PATTERNS:
            if pattern.search(text):
                is_red_line = True
                break

        for pattern, dtype in CORRECTION_PATTERNS:
            m = pattern.search(text)
            if m:
                dialog_type = dtype.value
                break

        if not dialog_type:
            for pattern, dtype in PRE_INSTRUCTION_PATTERNS:
                m = pattern.search(text)
                if m:
                    dialog_type = dtype.value
                    break

        if not dialog_type:
            for pattern, dtype in FEEDBACK_PATTERNS:
                m = pattern.search(text)
                if m:
                    dialog_type = dtype.value
                    break

        # Return signal if dialog type found OR red line detected
        if not dialog_type and not is_red_line:
            return None

        return Signal(
            source=SignalSource.DIALOG.value,
            dialog_type=dialog_type,
            diff_type=None,
            content=text,
            context=context,
            red_line=is_red_line,
        )

    def classify_diff(
        self, diff_content: str, filepath: str,
        ai_wrote_lines: int = 0, user_kept_lines: int = 0,
    ) -> dict:
        if not diff_content.strip():
            if ai_wrote_lines >= DELETED_LINES_FOR_FULL_DELETE and user_kept_lines == 0:
                return {"diff_type": DiffType.FULL_DELETE.value, "is_significant": True}
            return {"diff_type": DiffType.FULL_DELETE.value, "is_significant": False}

        added_lines = [l for l in diff_content.split('\n') if l.startswith('+') and not l.startswith('+++')]
        removed_lines = [l for l in diff_content.split('\n') if l.startswith('-') and not l.startswith('---')]

        added_count = len(added_lines)
        removed_count = len(removed_lines)

        if added_count <= 3 and removed_count <= 3:
            style_indicators = 0
            for al, rl in zip(added_lines + [''] * max(0, removed_count - added_count),
                              removed_lines + [''] * max(0, added_count - removed_count)):
                if len(al) > 1 and len(rl) > 1 and al[1:].strip() == rl[1:].strip():
                    style_indicators += 1
                elif len(al) > 1 and len(rl) > 1 and _is_rename(al[1:], rl[1:]):
                    style_indicators += 1

            if style_indicators >= max(1, min(added_count, removed_count)):
                return {"diff_type": DiffType.STYLE_EDIT.value, "is_significant": False}

        if (added_count + removed_count) >= ADDED_LINES_FOR_REWRITE:
            return {"diff_type": DiffType.STRUCTURE_REWRITE.value, "is_significant": True}

        return {"diff_type": DiffType.STYLE_EDIT.value, "is_significant": False}

    def record_file_accept(self, filepath: str, content: str):
        self._file_accepts[filepath] = (datetime.now().isoformat(), content)

    def check_compromise(self, filepath: str, new_content: str, within_minutes: int = 10) -> bool:
        if filepath not in self._file_accepts:
            return False
        accept_time_str, old_content = self._file_accepts[filepath]
        accept_time = datetime.fromisoformat(accept_time_str)
        elapsed = datetime.now() - accept_time
        if elapsed > timedelta(minutes=within_minutes):
            return False
        similarity = difflib.SequenceMatcher(None, old_content, new_content).ratio()
        return similarity < 0.5

    def track_consecutive_full_delete(self, filepath: str, task_type: str) -> bool:
        key = f"{filepath}:{task_type}"
        self._consecutive_full_deletes[key] = self._consecutive_full_deletes.get(key, 0) + 1
        return self._consecutive_full_deletes[key] >= 2


def _is_rename(line_a: str, line_b: str) -> bool:
    if line_a == line_b:
        return False
    a_tokens = re.findall(r'[_\w]+', line_a)
    b_tokens = re.findall(r'[_\w]+', line_b)
    if len(a_tokens) != len(b_tokens):
        return False
    a_stripped = re.sub(r'[_\w]+', '', line_a)
    b_stripped = re.sub(r'[_\w]+', '', line_b)
    return a_stripped == b_stripped
