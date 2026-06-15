---
name: self-growing-memory-v2
description: A coding assistant that learns your preferences from both what you say and what you edit — then silently applies them, reducing repetition over time.
---

# Self-Growing Memory Skill v2

## Contract

Operate in the background during Claude Code sessions. Do not interrupt the user unless you have a confirmation question.

### On Every User Interaction

1. **Capture signals** from user messages and code edits (regex-based, zero cost)
2. **Normalize & group** similar corrections (deterministic, no LLM needed)
3. **Red-line intercept**: strong negation ("絕對不要", "never") → classify immediately
4. **Implicit confirmation**: user doesn't re-correct next turn → accelerate confidence
5. **Classify** signals reaching threshold (trigger_count >= 3 or red_line):
   - Review the signal content and context
   - Extract structured memory: rule_content, type, scope, scope_value, condition, principle
   - Save to the memory store
   - **You (Claude Code) perform this classification using your own intelligence — no external API.**
6. **Confirm** once when a memory reaches mature tier (confidence 40-79): ask "PS: ..."
7. **Apply** silently when confidence >= 80 via JIT context injection (top 5)
8. **Decay** unused memories; **deprecate** overridden ones
9. **Pulse** — periodic status (session start, rule upgrade, milestone)

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

- Does not enforce security rules (that is a separate concern)
- Does not inject more than 5 memories at once
- Does not modify CLAUDE.md without user confirmation
