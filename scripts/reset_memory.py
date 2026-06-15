#!/usr/bin/env python3
"""CLI: Clear all memories."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.memory_store import MemoryStore

def main():
    store = MemoryStore()
    before = len(store.list_memories())
    store.clear()
    print(f"Memories cleared: {before} → 0")
    print("Reset complete. Memory store is now empty.")

if __name__ == "__main__":
    main()
