"""LLM classifier with pattern discovery and red-line routing."""
import json
import os
from typing import Optional
from anthropic import Anthropic
from src.models import Signal, Memory, RED_LINE_START, MATURE_THRESHOLD


CLASSIFIER_SYSTEM_PROMPT = """You are a memory classifier for an AI coding assistant. Your job: extract structured, durable memories from raw user signals.

Input: A signal (dialog correction, pre-instruction, or diff behavior) with context.
Output: A structured memory in JSON format.

## Classification Rules

1. **type**: Classify as one of:
   - "preference": Code style, naming, formatting habits (high frequency, low cognitive load)
   - "rule": Situational rules ("in this project, always commit before editing")
   - "workflow": Communication rhythm, tool usage, Git conventions (medium frequency, multi-step)
   - "method": Working methods ("debug by fixing the class, not the instance")

2. **scope**: Determine applicability range:
   - "global": Applies everywhere, all projects
   - "workspace": Applies to a workspace/collection of projects
   - "repo": Specific to one repository
   - "directory": Specific to a directory path

3. **scope_value**: The concrete path or project name. Empty string for global.

4. **condition**: Write as "IF [context] THEN [action]". Must be specific and actionable.

5. **principle**: Abstract the signal to a general principle. What does this reveal about the user?

## Pattern Discovery

Check: are there patterns in the signal history that the user has NEVER explicitly stated, but their behavior consistently shows? If yes, include a `discovered_pattern` field.

## Output Format

```json
{
  "rule_content": "clear actionable rule",
  "type": "preference|rule|workflow|method",
  "scope": "global|workspace|repo|directory",
  "scope_value": "path or empty",
  "condition": "IF ... THEN ...",
  "principle": "abstract principle",
  "discovered_pattern": null
}
```

If the signal is noise or not actionable, return: `{"skip": true, "reason": "..."}`
"""


class Classifier:
    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.api_key = api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
        self.base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro")
        self._client: Optional[Anthropic] = None

    @property
    def client(self) -> Anthropic:
        if self._client is None:
            self._client = Anthropic(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def should_trigger_llm(self, signal: Signal) -> bool:
        if signal.red_line:
            return True
        if signal.trigger_count >= 3:
            return True
        return False

    def get_start_confidence(self, red_line: bool = False) -> int:
        if red_line:
            return RED_LINE_START
        return MATURE_THRESHOLD

    def classify(self, signal: Signal, related_signals: list[Signal], existing_memories: list[Memory]) -> Optional[Memory]:
        context_str = json.dumps(signal.context, ensure_ascii=False) if signal.context else "{}"
        related_str = json.dumps([{"content": s.content, "source": s.source, "dialog_type": s.dialog_type, "diff_type": s.diff_type} for s in related_signals], ensure_ascii=False, indent=2)
        existing_str = json.dumps([{"rule_content": m.rule_content, "scope": m.scope, "scope_value": m.scope_value, "confidence": m.confidence} for m in existing_memories[-5:]], ensure_ascii=False, indent=2)

        user_msg = f"""Signal:
  source: {signal.source}
  dialog_type: {signal.dialog_type}
  diff_type: {signal.diff_type}
  content: {signal.content}
  context: {context_str}
  trigger_count: {signal.trigger_count}
  red_line: {signal.red_line}

Related signals from the same pattern:
{related_str}

Existing active memories:
{existing_str}

Classify this signal. If it reveals a durable preference or pattern, extract it. If it's noise, skip it."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=CLASSIFIER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        result_text = response.content[0].text
        result = self._parse_json(result_text)
        source_ids = [s.id for s in related_signals] + [signal.id]
        return self.parse_result(result, source_ids)

    def parse_result(self, result: dict, source_signal_ids: list[str]) -> Optional[Memory]:
        if result.get("skip"):
            return None
        return Memory(
            rule_content=result.get("rule_content", ""),
            type=result.get("type", "preference"),
            scope=result.get("scope", "global"),
            scope_value=result.get("scope_value", ""),
            condition=result.get("condition", ""),
            principle=result.get("principle", ""),
            confidence=MATURE_THRESHOLD,
            state="active",
            source_signals=source_signal_ids,
        )

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        for delimiter in ["```json\n", "```\n", "```json", "```"]:
            if delimiter in text:
                parts = text.split(delimiter)
                if len(parts) >= 2:
                    text = parts[1]
                break
        text = text.strip().strip("`").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"skip": True, "reason": f"JSON parse error: {text[:100]}"}
