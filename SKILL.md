---
name: self-growing-memory-skill
description: A coding assistant with structured memory that extracts preferences, rules, and learning needs from conversation, applies them proactively across contexts, and auto-decays guidance as the user grows.
---

# Self-Growing Memory Skill

## Contract

Accept user messages as normal conversation. On every interaction:

1. Inject relevant active memories into the system prompt
2. After responding, classify the user's message as feedback or temporary task
3. If feedback: extract structured memories (preference / rule / method)
4. Run scope-graded conflict arbitration on new memories
5. Scan auto-decay memories: reinforce matching topics, decay unmatched ones

Keep memory management transparent. Expose `reset`, `view`, `edit`, `delete` as first-class operations.

## Memory Model

Every memory has:

| Field | Values | Description |
|-------|--------|-------------|
| type | preference / rule / method / temporary | Memory category |
| scope | global / project / file / temporary | Applicability range |
| priority | 1-10 | Resolution weight for conflicts |
| status | active / deprecated / archived | Lifecycle state |
| auto_decay | bool | Whether decay tracking is enabled |
| decay_score | 0-100 | 100=just reinforced, 0=auto-deprecated |
| decay_topic | string | Topic key for per-topic independent decay |

## Conflict Resolution

Scope-graded: global > project > file > temporary.

- New memory with narrower scope → keep both (exception doesn't kill preference)
- New memory with equal/wider scope + higher priority → replace old
- Temporary memory with `expires_at` → auto-archived after expiry

## Decay Mechanism

Triggered only for memories with `auto_decay=true` (typically method-type memories about user learning needs).

- Per-topic matching: only reinforce the specific topic the user is asking about
- Reinforcement: `decay_score = 100` when user asks "why" / "explain" on matching topic
- Decay: `decay_score -= 20` per session where topic is not triggered
- Auto-deprecation: when `decay_score` reaches 0

This means: if a user keeps asking about React but stops asking about TypeScript, only the TypeScript memory decays. Non-decay memories (preference/rule) are never affected.

## Non-Goals

- Does not replace general conversation memory or chat history
- Does not persist memories across different users (single-user model)
- Does not handle multi-modal input

## See Also

- [Architecture docs](./docs/architecture.md)
- [Setup guide](./SETUP.md)
- [Test harness](./tests/test_harness.py)
