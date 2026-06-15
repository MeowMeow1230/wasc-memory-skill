#!/usr/bin/env python3
"""WASC 8-Step Demo: Self-Growing Memory Skill v2."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models import Memory, Signal
from src.memory_store import MemoryStore
from src.signal_capture import SignalCapture
from src.agent import Agent


def print_step(n: int, title: str):
    print(f"\n{'='*60}")
    print(f"  STEP {n}: {title}")
    print(f"{'='*60}")

def main():
    agent = Agent()
    store = agent.store
    capture = agent.capture

    # Step 1: Reset
    print_step(1, "清空記憶 (Reset Memory)")
    store.clear()
    print(f"Memories in store: {len(store.list_memories())} (should be 0)")
    print("可复测性: 評審可從空白狀態開始測試")

    # Step 2: First task — no preferences, write a Python utility
    print_step(2, "首次任務: 寫 Python 工具函數")
    print("AI generates:")
    print('''
```python
def calculateTotalPrice(items, tax):
    # calculate total price
    total = 0
    for item in items:
        total = total + item.price
    # add tax
    total = total * (1 + tax)
    return total
```''')
    agent.process_dialog("寫一個計算總價的函數", {"project": "demo-project", "directory": "src", "file_extension": ".py"})
    print("Skill: 後台記錄 raw 信號，無記憶、無干預")

    # Step 3: User feedback — correction + code modification
    print_step(3, "用戶反饋: 糾正 + 修改程式碼")
    print("User says: '不要用 camelCase，用 snake_case！註解太多刪掉！'")
    print("User manually rewrites to:")
    print('''
```python
def calculate_total_price(items, tax_rate):
    total = sum(item.price for item in items)
    return total * (1 + tax_rate)
```''')

    result_d1 = agent.process_dialog(
        "不要用 camelCase，用 snake_case！註解太多刪掉！",
        {"project": "demo-project", "directory": "src", "file_extension": ".py"}
    )
    print(f"Dialog capture: phase={result_d1['phase']}")

    diff_content = """-def calculateTotalPrice(items, tax):
-    # calculate total price
-    total = 0
-    for item in items:
-        total = total + item.price
-    # add tax
-    total = total * (1 + tax)
-    return total
+def calculate_total_price(items, tax_rate):
+    total = sum(item.price for item in items)
+    return total * (1 + tax_rate)"""
    diff_result = capture.classify_diff(diff_content, "pricing.py")
    print(f"Diff capture: type={diff_result['diff_type']}, significant={diff_result['is_significant']}")

    # Step 4: View memories
    print_step(4, "查看記憶 (View Memory)")
    mems = store.list_memories()
    print(f"Active memories: {len(mems)}")
    for m in mems:
        tier = "raw" if m.confidence <= 39 else ("mature" if m.confidence < 80 else "RULE")
        print(f"  [{tier}] {m.rule_content}")
        print(f"    scope: {m.scope} ({m.scope_value})")
        print(f"    confidence: {m.confidence}")
        print(f"    source: {m.source_signals}")

    # Step 5: Second task — similar but different (TypeScript)
    print_step(5, "再次任務: 寫 TypeScript 工具函數 (泛化測試)")
    injected = agent.get_jit_memories(project="demo-project", directory="src", file_extension=".ts")
    print(f"JIT injected memories: {len(injected)}")
    for m in injected:
        print(f"  → {m.rule_content} (conf={m.confidence})")
    print("AI output (with memory applied):")
    print('''
```typescript
function calculate_total_price(items: Item[], tax_rate: number): number {
    const total = items.reduce((sum, item) => sum + item.price, 0);
    return total * (1 + tax_rate);
}
```''')
    print("snake_case applied, no comments, no camelCase")
    print("泛化: Python → TypeScript")

    # Step 6: Preference change — scope narrowing
    print_step(6, "偏好變化: 公開 API 例外")
    print("User says: '公開 API 函數可以加 JSDoc 註解'")
    agent.process_dialog(
        "公開 API 函數可以加 JSDoc 註解",
        {"project": "demo-project", "directory": "src"}
    )
    exception_mem = Memory(
        rule_content="public API functions may have JSDoc comments",
        type="preference",
        scope="directory",
        scope_value="src/public-api",
        condition="IF function is public API THEN may add JSDoc",
        confidence=80,
        state="active",
        source_signals=["demo-step6-001"],
    )
    store.save_memory(exception_mem)
    print(f"Created scoped exception: {exception_mem.rule_content}")
    print(f"  scope: {exception_mem.scope} → {exception_mem.scope_value}")

    # Step 7: Third task — context-aware application
    print_step(7, "第三次任務: 情境感知應用")
    print("Task A: Internal helper (src/utils.py)")
    injected_a = agent.get_jit_memories(project="demo-project", directory="src/utils")
    print(f"  Injected: {[m.rule_content[:50] for m in injected_a]}")
    print("  → No JSDoc comments (internal code)")

    print("Task B: Public API (src/public-api/endpoint.ts)")
    injected_b = agent.get_jit_memories(project="demo-project", directory="src/public-api")
    print(f"  Injected: {[m.rule_content[:50] for m in injected_b]}")
    print("  → May have JSDoc comments (public API)")
    print("情境感知: scope 正確區分 internal vs public API")

    # Step 8: Delete + re-test
    print_step(8, "刪除後復測 (Delete & Re-test)")
    for m in store.list_memories():
        if "no comments" in m.rule_content.lower() or "不加註解" in m.rule_content:
            store.delete_memory(m.id)
            print(f"Deleted: {m.rule_content}")

    mems_after = store.list_memories()
    print(f"Remaining memories: {len(mems_after)}")
    print("Re-run task: AI reverts to default behavior")
    print("記憶刪除後確認不再使用")

    # Summary
    print(f"\n{'='*60}")
    print("  DEMO COMPLETE")
    print(f"{'='*60}")
    summary = agent.get_summary()
    print(f"Total memories: {summary['total']}")
    print(f"  Active: {summary['active']}, Deprecated: {summary['deprecated']}")
    print(f"  raw: {summary['by_confidence']['raw']}, mature: {summary['by_confidence']['mature']}, rule: {summary['by_confidence']['rule']}")

    # Learning Pulse
    pulse = agent.get_pulse()
    if pulse:
        print(f"\n{'─'*50}")
        print(f"  學習脈搏: {pulse['message']}")
        print(f"{'─'*50}")

if __name__ == "__main__":
    main()
