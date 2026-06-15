# Self-Growing Memory Skill v2

A Claude Code Skill that learns your coding preferences from both dialog corrections and code-diff behavior, then silently applies them — reducing repetition over time.

**Core philosophy**: The more you use it, the less you need to repeat yourself.

## Highlights

- **Dual-track signals**: learns from what you say AND what you edit
- **Red-line intercept**: strong negation ("never do X") triggers immediate learning
- **JIT context injection**: only injects top 5 most relevant memories per task
- **Learning pulse**: periodic lightweight status so you know the skill is alive
- **source_signals traceability**: every memory can be traced back to exact conversations
- **Real session replay**: verified against actual Claude Code history (108 sessions)

## Quick Start

```bash
pip install -r requirements.txt
python3 scripts/demo.py
```

## Testing

```bash
python3 -m pytest tests/ -v
python3 tests/test_harness.py
python3 scripts/ab_compare.py
```

## Project Structure

```
src/           — Core engine (models, store, capture, classifier, agent)
scripts/       — CLI tools (reset/view/edit/delete memory, demo, A/B, replay)
tests/         — Unit tests + 8-step rubric harness
evals/         — Test report output
```
