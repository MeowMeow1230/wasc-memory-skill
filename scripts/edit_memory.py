#!/usr/bin/env python3
"""CLI: Edit a memory by ID."""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.memory_store import MemoryStore

def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/edit_memory.py <memory_id> '<json_updates>'")
        print("Example: python scripts/edit_memory.py abc123 '{\"rule_content\": \"new rule\", \"confidence\": 85}'")
        sys.exit(1)

    memory_id = sys.argv[1]
    updates = json.loads(sys.argv[2])

    store = MemoryStore()
    updated = store.edit_memory(memory_id, updates)
    if updated:
        print(f"Memory {memory_id} updated:")
        print(f"  rule_content: {updated.rule_content}")
        print(f"  confidence: {updated.confidence}")
        print(f"  scope: {updated.scope} ({updated.scope_value})")
    else:
        print(f"Memory {memory_id} not found.")
        sys.exit(1)

if __name__ == "__main__":
    main()
