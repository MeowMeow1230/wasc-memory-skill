# Setup Guide

## Requirements

- Python 3.12+
- Claude Code (no external API keys needed)
- Zero pip dependencies beyond Python stdlib

## Install

```bash
cd wasc-memory-skill
pip install -e .
```

## Verify

```bash
python3 scripts/demo.py          # 8-step WASC demo
python3 tests/test_harness.py    # Rubric scoring (100/100)
```

## CLI Tools

```bash
python3 scripts/reset_memory.py     # Clear all memories
python3 scripts/view_memory.py      # List all memories
python3 scripts/edit_memory.py <id> '<json>'  # Edit a memory
python3 scripts/delete_memory.py <id>         # Delete a memory
```
