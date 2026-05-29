# Setup Guide

## Requirements

- Python 3.12+
- DeepSeek API key (or any Anthropic-compatible endpoint)
- No GPU, no Docker, no external services needed

## Install

```bash
git clone <repo-url>
cd wasc-memory-skill
pip install -e .
```

## Configure

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your API key:
#   ANTHROPIC_AUTH_TOKEN=your-key
#   ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
#   ANTHROPIC_MODEL=deepseek-chat
```

## Verify

```bash
# Run the automated 8-step test
python3 -m tests.test_harness
```

Expected output: 97/100 with judge commentary for each step.

## Usage

### CLI Demo

```bash
python3 scripts/demo.py       # Main 8-step memory test
python3 scripts/decay_demo.py  # Auto-decay feature demo
```

### MCP Server

The Skill can be run as an MCP server, exposing 6 tools:

| Tool | Description |
|------|-------------|
| `reset_memory` | Clear all memories |
| `view_memories` | List all active memories |
| `edit_memory` | Edit a memory's content/scope/priority |
| `delete_memory` | Delete a memory |
| `chat` | Chat with the memory-aware agent |
| `run_test_harness` | Run the 8-step automated test |

Connect to any MCP-compatible AI tool:

```json
{
  "mcpServers": {
    "wasc-memory": {
      "command": "python3",
      "args": ["-m", "src.memory_server"],
      "cwd": "/path/to/wasc-memory-skill"
    }
  }
}
```
