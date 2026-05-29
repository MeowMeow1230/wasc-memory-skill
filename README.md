# Self-Growing Memory Agent Skill

A coding assistant that learns your preferences, rules, and learning needs through continuous use — and automatically adapts as you grow.

**WASC May Challenge: Self-Growing · The More You Use It, The Better It Knows You**

## Why This Project

Most AI coding assistants treat every conversation like the first one. You repeat the same preferences endlessly.

This Skill solves that: it extracts structured memories from every interaction, applies them proactively, and — uniquely — detects when you've outgrown certain needs and lets those memories fade automatically.

## Highlights

- **Structured memory extraction** — classifies into preference / rule / method, discards temporary task noise
- **Scope-graded conflict arbitration** — narrow-scope exceptions never kill global preferences
- **Auto-decay memory** — detects user growth and silently retires obsolete guidance
- **Full transparency** — every memory is viewable, explainable, editable, and deletable
- **Cross-scenario verification** — memory application proven on tasks unrelated to the original context
- **Reproducible testing** — built-in 8-step test harness aligned with WASC 100-point rubric

## How It Works

```
User conversation
       │
       ▼
┌─────────────┐    ┌──────────────────┐
│  Extractor   │───▶│ Structured Memory │
│  (LLM)       │    │ preference/rule/  │
└─────────────┘    │ method/temporary  │
                   └────────┬─────────┘
                            │
                   ┌────────▼─────────┐
                   │  Arbitrator       │
                   │  scope-graded     │
                   │  conflict resolve │
                   └────────┬─────────┘
                            │
                   ┌────────▼─────────┐
                   │  Injector         │───▶ Next chat prompt
                   │  relevant memory  │     auto-enriched
                   │  + decay hints    │
                   └──────────────────┘
                            │
                   ┌────────▼─────────┐
                   │  Decay Scanner    │
                   │  reinforce/decay  │
                   │  by topic         │
                   └──────────────────┘
```

Two memory types coexist in one store:

| Type | auto_decay | Behavior |
|------|-----------|----------|
| preference / rule | false | Permanent. Only changes when user explicitly overrides. |
| method | true | Auto-detected. Strengthens when user keeps asking "why". Decays (-20/session) when they stop. Auto-deprecated at 0. |

## Project Structure

```
├── SKILL.md              # Installable skill contract
├── README.md             # This file
├── SETUP.md              # Installation & run guide
├── docs/
│   └── architecture.md   # Architecture & design decisions
├── src/
│   ├── models.py         # Memory data model
│   ├── store.py          # Mem0 vector store wrapper
│   ├── extractor.py      # LLM-driven memory classifier
│   ├── arbitrator.py     # Scope-graded conflict resolver
│   ├── injector.py       # Memory injection into prompts
│   ├── agent.py          # Main agent logic + decay scanner
│   ├── llm.py            # LLM client (DeepSeek/Anthropic)
│   └── memory_server.py  # MCP Server (6 tools)
├── tests/
│   └── test_harness.py   # 8-step automated test with judge commentary
├── scripts/
│   ├── demo.py           # Main 8-step demo
│   └── decay_demo.py     # Auto-decay feature demo
├── skill/
│   └── SKILL.md          # WASC submission skill description
├── evals/
│   └── test_report.json  # Latest test run results
└── pyproject.toml
```

## Requirements

- Python 3.12+
- DeepSeek API key (or any Anthropic-compatible endpoint)
- Zero external services — no GPU, no Docker, no Ollama

## Quick Start

```bash
# 1. Install
git clone <repo-url>
cd wasc-memory-skill
pip install -e .

# 2. Configure
cp .env.example .env
# Edit .env: add your ANTHROPIC_AUTH_TOKEN

# 3. Run
python3 scripts/demo.py          # 8-step memory test
python3 scripts/decay_demo.py    # Auto-decay feature
python3 -m tests.test_harness    # Automated scoring (97/100)
```

## Evaluation Results

Latest 8-step automated test run:

| Dimension | Score | Max |
|-----------|-------|-----|
| Reproducibility | 10 | 10 |
| Memory Extraction | 20 | 20 |
| Memory Application | 22 | 25 |
| Memory Update & Eviction | 20 | 20 |
| User Control & Transparency | 10 | 10 |
| Result Quality | 15 | 15 |
| **Total** | **97** | **100** |

Cross-scenario verified: memory correctly applied to a TypeScript utility function (non-React context), proving application is not coincidental.

## License

MIT-0 — Free to use, modify, and redistribute without attribution.
