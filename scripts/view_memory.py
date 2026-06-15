#!/usr/bin/env python3
"""CLI: View all memories with source traceability."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.memory_store import MemoryStore
from src.models import RAW_MAX, RULE_MIN

def main():
    store = MemoryStore()
    mems = store.list_memories()

    if not mems:
        print("No memories stored.")
        return

    print(f"{'ID':<10} {'Conf':>4} {'Tier':>8} {'State':>10} {'Scope':>10} {'Scope Value':<25} Rule")
    print("-" * 120)
    for m in mems:
        if m.confidence <= RAW_MAX:
            tier = "raw"
        elif m.confidence < RULE_MIN:
            tier = "mature"
        else:
            tier = "RULE"
        short_id = m.id[:8]
        print(f"{short_id:<10} {m.confidence:>4} {tier:>8} {m.state:>10} {m.scope:>10} {m.scope_value:<25} {m.rule_content[:60]}")
        if m.source_signals:
            print(f"  └─ source_signals: {', '.join(m.source_signals)}")
        print()

if __name__ == "__main__":
    main()
