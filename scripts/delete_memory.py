#!/usr/bin/env python3
"""CLI: Delete a memory by ID."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.memory_store import MemoryStore

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/delete_memory.py <memory_id>")
        sys.exit(1)

    memory_id = sys.argv[1]
    store = MemoryStore()
    mem = store.get_memory(memory_id)
    if not mem:
        print(f"Memory {memory_id} not found.")
        sys.exit(1)

    rule = mem.rule_content
    store.delete_memory(memory_id)

    if store.get_memory(memory_id) is None:
        print(f"Deleted memory {memory_id}: '{rule}'")
        print(f"Verification: memory no longer in store. ✓")
    else:
        print("ERROR: Deletion failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
