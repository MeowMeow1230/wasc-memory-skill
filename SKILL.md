---
name: self-growing-memory-v2
description: A coding assistant that learns your preferences from both what you say and what you edit — then silently applies them, reducing repetition over time.
---

# Self-Growing Memory Skill v2

## Contract

Operate in the background during Claude Code sessions. You (Claude Code) are the intelligence — the Python engine only does deterministic signal capture.

### On Every User Interaction

1. **Capture signals** — Python engine detects corrections, pre-instructions, and code edits via regex. No LLM needed here.

2. **Periodically classify** — Every 5-10 turns, or when signal pool exceeds 5 items:
   - Call `agent.get_pending_signals()` to get unclassified signals
   - **Read the signals. Use YOUR intelligence to understand what the user meant.**
   - Group signals that are semantically about the same topic — even if they use different words
   - For each group: extract a structured memory and call `agent.classify_and_save(signal_id, classification)`

3. **Classification output** — For each group of related signals, produce:
   - `rule_content`: Clear, actionable rule
   - `type`: "preference" (style) | "rule" (situational) | "workflow" (rhythm) | "method" (approach)
   - `scope`: "global" | "workspace" | "repo" | "directory"
   - `scope_value`: Concrete path/project. Empty for global.
   - `condition`: IF [context] THEN [action]
   - `principle`: What does this reveal about the user? Abstract from concrete cases.
   - `confidence`: Start at 40. Use 60 for red-line signals. Use 80 if highly confident.
   - `related_signal_ids`: Other signal IDs that belong to this same group

4. **Confirm** — When saving a memory with confidence 40-79, ask a lightweight PS question before next response.

5. **Apply** silently when confidence >= 80 via JIT context injection (top 5 most relevant memories).

6. **Decay** unused memories; **deprecate** overridden ones.

7. **Pulse** — Periodic status so user knows the skill is alive.

### Semantic Grouping Examples

These should ALL be grouped together by YOU (Claude Code):
- "不要用 camelCase" / "用 snake_case，不要 camelCase" / "我說過不要 camelCase"
- "不要硬編碼" / "不要只修一個" / "不要只做一半" / "不要治標不治本" → all mean "fix systemically"
- "先討論一下" / "我們要不要討論" / "不急做，先討論" → all mean "discuss before acting"

### Memory Model

| Field | Description |
|-------|-------------|
| `rule_content` | The actionable rule in plain language |
| `type` | preference / rule / workflow / method |
| `scope` | global / workspace / repo / directory |
| `scope_value` | Concrete path or project name |
| `condition` | IF [context] THEN [action] |
| `principle` | Abstract principle behind the rule |
| `confidence` | 0-100 (raw 0-39, mature 40-79, rule 80-100) |
| `source_signals` | Signal IDs tracing why this was learned |

### Non-Goals

- Does not enforce security rules
- Does not inject more than 5 memories at once
- Does not modify CLAUDE.md without user confirmation
