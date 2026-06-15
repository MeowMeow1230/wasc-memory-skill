"""Classifier prompt provider. Actual classification is done by Claude Code (via SKILL.md contract)."""
import json
from typing import Optional
from src.models import Signal, Memory, MATURE_THRESHOLD


CLASSIFIER_CONTRACT = """## Classification Contract

When signals reach threshold (trigger_count >= 3 or red_line), classify them into structured memories.

### Output a Memory with:

1. **rule_content**: The actionable rule. Clear, specific.

2. **type**: "preference" (style/naming) | "rule" (situational) | "workflow" (rhythm) | "method" (approach)

3. **scope**: "global" | "workspace" | "repo" | "directory"

4. **scope_value**: Concrete path/project name. Empty for global.

5. **condition**: IF [context] THEN [action] format.

6. **principle**: What does this reveal about the user? Abstract from the concrete case.

7. **confidence**: Start at 40 (mature). Red-line signals start at 60.

### Skip if: noise, one-time instruction, already covered by existing memory.
"""


class Classifier:
    """Provides classification prompts. Claude Code does the actual classification."""

    def should_trigger_llm(self, signal: Signal) -> bool:
        if signal.red_line:
            return True
        if signal.trigger_count >= 3:
            return True
        return False

    def get_start_confidence(self, red_line: bool = False) -> int:
        return 60 if red_line else MATURE_THRESHOLD

    def format_request(self, signal: Signal, related_signals: list[Signal], existing_memories: list[Memory]) -> str:
        """Format a classification request for Claude Code to process."""
        context_str = json.dumps(signal.context, ensure_ascii=False) if signal.context else "{}"
        related_str = json.dumps([
            {"content": s.content, "source": s.source, "trigger_count": s.trigger_count}
            for s in related_signals
        ], ensure_ascii=False, indent=2)
        existing_str = json.dumps([
            {"rule_content": m.rule_content, "scope": m.scope, "scope_value": m.scope_value, "confidence": m.confidence}
            for m in existing_memories[-5:]
        ], ensure_ascii=False, indent=2)

        return f"""Signal to classify:
  source: {signal.source}
  dialog_type: {signal.dialog_type}
  diff_type: {signal.diff_type}
  content: {signal.content}
  context: {context_str}
  trigger_count: {signal.trigger_count}
  red_line: {signal.red_line}

Related signals (same pattern):
{related_str}

Existing active memories:
{existing_str}

{CLASSIFIER_CONTRACT}

Classify this signal into a Memory JSON and save to the store."""

    def classify_local(self, signal: Signal, related_signals: list[Signal]) -> Optional[Memory]:
        """Simple rule-based classification for testing when no Claude Code is available.
        Uses the normalized signal content directly as the rule.
        """
        source_ids = [s.id for s in related_signals] + [signal.id]
        content = signal.content.strip()

        # Skip empty or very short
        if len(content) < 3:
            return None

        return Memory(
            rule_content=content[:200],
            type="preference",
            scope="global",
            scope_value="",
            condition=f"IF similar task THEN {content[:80]}",
            principle=content[:200],
            confidence=self.get_start_confidence(red_line=signal.red_line),
            state="active",
            source_signals=source_ids,
        )
