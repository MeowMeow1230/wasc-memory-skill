# Self-Growing Memory Skill v2

A Claude Code Skill that learns your coding preferences from both dialog corrections and code-diff behavior, then silently applies them — reducing repetition over time.

**WASC June Challenge: 自成長 · 越用越懂你**

## Core Philosophy

> The more you use it, the less you need to repeat yourself.

Python does the mechanical work (signal capture, storage, JIT injection). Claude Code does the intelligent work (semantic grouping, classification, confidence judgment).

## Highlights

- **Dual-track signals**: learns from what you say AND what you edit
- **Claude-powered classification**: no external API — Claude Code IS the intelligence
- **JIT context injection**: top 20 most relevant memories, filtered by project/directory scope
- **Confidence lifecycle**: raw → mature (PS confirmation) → rule (silent application) → decay
- **Learning pulse**: periodic status so you know the skill is alive
- **Real session verified**: tested against 108 real Claude Code history sessions
- **100/100 rubric score**: validated against WASC 6-dimension scoring

## Quick Start

```bash
pip install -e .
python3 scripts/demo.py           # 8-step WASC demo
python3 tests/test_harness.py     # Rubric scoring
python3 scripts/replay_session.py # Real history cross-validation
```

## Project Structure

```
src/           — Core engine (models, store, capture, classifier, agent)
scripts/       — CLI tools + demo + A/B + replay
tests/         — Unit tests + rubric harness
skill/         — Submission skill description
docs/          — Design spec + implementation plan
```

## Requirements

- Python 3.12+
- Claude Code
- Zero pip dependencies
- Zero external API keys

[中文說明](README_CN.md)
