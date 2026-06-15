---
name: nest
description: Nest — your preferences, grown to fit. A background skill that learns from corrections and code edits, then silently applies them. Claude Code is the intelligence; Python is the notebook.
---

# Nest

## One-Liner

你的偏好，越用越合身。A background skill that observes, learns, and silently applies — so you repeat yourself less with every session.

## How It Works

1. **Dual-track capture**: regex catches obvious corrections ("不要X"). Claude Code catches implicit ones ("這個寫法不太好").
2. **Claude classifies**: semantic grouping + structured memory extraction (type, scope, condition, principle).
3. **JIT injection**: top 20 most relevant memories filtered by project/directory scope, injected before each task.
4. **Self-growing**: confidence grows from raw → mature → rule. PS confirmation at mature. Silent at rule.

## Key Differentiators

- **Behavior > Words**: learns from code diffs, not just dialog
- **Zero API calls**: Claude Code does all semantic work natively
- **Project isolation**: memories scoped to global/repo/directory
- **Learning pulse**: periodic status so you know the skill is alive
- **Full traceability**: every memory linked to source signals

## Requirements

- Python 3.12+
- Claude Code (no external API keys needed)
- Zero dependencies beyond Python stdlib

## Usage

```bash
pip install -e .
python3 scripts/demo.py
python3 tests/test_harness.py
```
