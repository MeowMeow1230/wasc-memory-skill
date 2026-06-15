"""Data models for Self-Growing Memory Skill v2."""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class SignalSource(str, Enum):
    DIALOG = "dialog"
    DIFF = "diff"


class DialogType(str, Enum):
    CORRECTION = "correction"
    PRE_INSTRUCTION = "pre_instruction"
    FEEDBACK = "feedback"


class DiffType(str, Enum):
    STYLE_EDIT = "style_edit"
    STRUCTURE_REWRITE = "structure_rewrite"
    FULL_DELETE = "full_delete"
    COMPROMISE = "compromise"


class MemoryType(str, Enum):
    PREFERENCE = "preference"
    RULE = "rule"
    WORKFLOW = "workflow"
    METHOD = "method"


class MemoryScope(str, Enum):
    GLOBAL = "global"
    WORKSPACE = "workspace"
    REPO = "repo"
    DIRECTORY = "directory"


class MemoryState(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class Signal:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""          # "dialog" | "diff"
    dialog_type: Optional[str] = None
    diff_type: Optional[str] = None
    content: str = ""
    context: dict = field(default_factory=dict)
    trigger_count: int = 1
    red_line: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Signal":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Memory:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rule_content: str = ""
    type: str = ""            # "preference" | "rule" | "workflow" | "method"
    scope: str = ""           # "global" | "workspace" | "repo" | "directory"
    scope_value: str = ""     # e.g. "/Users/kun/Manbang v101", "src/components"
    condition: str = ""       # IF [context] THEN [action]
    principle: str = ""       # Abstracted principle from concrete cases
    confidence: int = 0       # 0-100
    state: str = "active"     # "active" | "deprecated" | "archived"
    source_signals: list[str] = field(default_factory=list)
    last_triggered: str = field(default_factory=lambda: datetime.now().isoformat())
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Memory":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# Confidence tiers
RAW_MAX = 39
MATURE_MAX = 79
RULE_MIN = 80
RULE_MAX = 100

RED_LINE_START = 60
MATURE_THRESHOLD = 40

# Decay config
MATURE_DECAY_MISSES = 3
RULE_DECAY_MISSES = 5
DEPRECATED_ARCHIVE_DAYS = 30

# Injection config
JIT_TOP_K = 5
