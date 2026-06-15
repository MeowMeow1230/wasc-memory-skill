---
name: self-growing-memory-v2
description: A coding assistant that learns your preferences from both what you say and what you edit — then silently applies them, reducing repetition over time.
---

# Self-Growing Memory Skill v2

## Contract

Operate in the background during Claude Code sessions. Do not interrupt the user unless you have a confirmation question.

### On Every User Interaction

1. **Capture signals** from user messages (corrections, pre-instructions, feedback) and code edits (style changes, structure rewrites, full deletes)
2. **Red-line intercept**: if the user uses strong negation ("絕對不要", "never", "stop doing") or deletes entire AI outputs twice consecutively — classify immediately
3. **Classify** when trigger_count >= 3 or red_line is true — extract structured memory with type, scope, scope_value, condition, and abstract principle
4. **Confirm** once when a memory reaches mature tier (confidence 40-79): ask a lightweight PS question
5. **Apply** silently when confidence >= 80 via JIT context injection (top 5 most relevant memories)
6. **Decay** unused memories over time; **deprecate** overridden memories
7. **Pulse** — periodic lightweight status (session start, rule upgrade, milestone) so you know the skill is alive

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
