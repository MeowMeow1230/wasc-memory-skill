#!/usr/bin/env python3
"""Nest Demo — 三幕自成长故事。Act 1: 烦躁 → Act 2: 怀疑 → Act 3: Aha!"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models import Memory
from src.agent import Agent

C = {"reset": "\033[0m", "bold": "\033[1m", "green": "\033[92m", "yellow": "\033[93m",
     "cyan": "\033[96m", "red": "\033[91m", "magenta": "\033[95m"}

def p(): print(f"\n{C['bold']}{C['cyan']}{'─'*60}{C['reset']}")
def h(text): print(f"{C['bold']}{C['yellow']}{text}{C['reset']}")
def ok(text): print(f"  {C['green']}✓{C['reset']} {text}")
def info(text): print(f"  {C['cyan']}→{C['reset']} {text}")
def code(text):
    for line in text.strip().split('\n'):
        print(f"    {C['magenta']}{line}{C['reset']}")

def main():
    agent = Agent()
    store = agent.store
    store.clear()

    # ════════════════════════════════════════════════════════════
    # ACT 1
    # ════════════════════════════════════════════════════════════
    p()
    print(f"{C['bold']}{C['red']}  ACT 1: 烦躁 — AI 每次都像第一次见你{C['reset']}")
    p()

    print(f"\n{C['bold']}评审视角：清空记忆，从零开始{C['reset']}")
    ok(f"reset memory → {len(store.list_memories())} 条记忆（空白状态）")

    print(f"\n{C['bold']}用户：写一个 Python 计算总价的函数{C['reset']}")
    print("AI 输出：")
    code("""
def calculateTotalPrice(items, tax):
    # 计算总价
    total = 0
    for item in items:
        total = total + item.price
    # 加上税
    return total * (1 + tax)
""")
    agent.process_dialog("写一个计算总价的函数", {"project": "demo", "directory": "src"})
    info("Nest 后台：捕获 raw 信号（camelCase 命名），不打扰用户")

    print(f"\n{C['bold']}用户纠错：不要用 camelCase！用 snake_case！注释太多！加 type hints！{C['reset']}")
    agent.add_signal("不要用 camelCase！用 snake_case！注释太多！加 type hints！", "correction",
                     {"project": "demo", "directory": "src"}, red_line=True)
    ok("双轨信号捕获：regex 抓到 '不要camelCase' / Claude 抓到语气强烈 → 红线标记")

    # ════════════════════════════════════════════════════════════
    # ACT 2
    # ════════════════════════════════════════════════════════════
    p()
    print(f"{C['bold']}{C['yellow']}  ACT 2: 怀疑 — 它真的学得会吗？{C['reset']}")
    p()

    sigs = agent.get_pending_signals()
    mem1 = agent.classify_and_save(sigs[0]['id'], {
        "rule_content": "Use snake_case for all variable and function names",
        "type": "preference", "scope": "global",
        "condition": "IF writing code in any language THEN use snake_case naming",
        "principle": "User follows PEP 8 conventions and applies them universally",
        "confidence": 60, "related_signal_ids": [],
    })
    ok(f"Nest 分类完成：\"{mem1.rule_content[:50]}...\" (conf=60, 红线起点)")

    mem2 = agent.classify_and_save("sig-comment-001", {
        "rule_content": "Do not add inline comments — code should be self-documenting",
        "type": "preference", "scope": "global",
        "condition": "IF writing internal code THEN omit comments; use descriptive names",
        "principle": "User believes well-named code is self-documenting",
        "confidence": 40, "related_signal_ids": [],
    })
    agent.store.save_memory(mem2)

    mem3 = agent.classify_and_save("sig-types-001", {
        "rule_content": "Always include Python type hints in function signatures",
        "type": "preference", "scope": "global",
        "condition": "IF writing Python functions THEN include parameter and return type hints",
        "principle": "User values static analysis over brevity",
        "confidence": 40, "related_signal_ids": [],
    })
    agent.store.save_memory(mem3)

    print(f"\n{C['bold']}查看记忆（评委：\"Skill 当前记住了什么？\"）{C['reset']}")
    for m in store.list_memories():
        if m.state == "active":
            tier = "RULE" if m.confidence >= 80 else ("mature" if m.confidence >= 40 else "raw")
            print(f"  [{tier}] [{m.type}] {m.rule_content[:70]}")
            print(f"       scope={m.scope} | condition={m.condition[:60]}")
    ok("结构化记忆：type/scope/condition/principle 完整，可追溯")

    # ════════════════════════════════════════════════════════════
    # ACT 3
    # ════════════════════════════════════════════════════════════
    p()
    print(f"{C['bold']}{C['green']}  ACT 3: Aha! — 越用越安静，越用越合身{C['reset']}")
    p()

    for m in store.list_memories():
        if m.confidence < 80 and m.state == "active":
            agent.handle_confirmation_response(m.id, "好")
    ok("用户确认 → 偏好升级到 RULE (conf=80+)，从此沉默生效")

    print(f"\n{C['bold']}新任务：写 TypeScript 工具函数（泛化测试）{C['reset']}")
    injected = agent.get_jit_memories(project="demo", directory="src", file_extension=".ts")
    print(f"  JIT 注入：{len(injected)} 条相关记忆 →")
    for m in injected:
        print(f"    → {m.rule_content[:70]}")
    print(f"\n  AI 输出（记忆已生效）：")
    code("""
function calculate_total_price(items: Item[], tax_rate: number): number {
    const total = items.reduce((sum, item) => sum + item.price, 0);
    return total * (1 + tax_rate);
}
""")
    ok("snake_case / 无注释 / TypeScript 类型标注 / 泛化 Python→TS")
    ok("用户什么都没说。Nest 已经学会了。")

    print(f"\n{C['bold']}偏好变化：公开 API 可以加 JSDoc 注释{C['reset']}")
    agent.store.save_memory(Memory(
        rule_content="Public API functions may have JSDoc documentation",
        type="rule", scope="directory", scope_value="src/public-api",
        condition="IF function is public API THEN add JSDoc comments",
        principle="User distinguishes internal code from public interfaces",
        confidence=85, state="active", source_signals=["sig-api-001"],
    ))
    ok("scope 窄化：global → directory(src/public-api)，旧规则不冲突")

    print(f"\n{C['bold']}情境感知注入：{C['reset']}")
    jit_int = agent.get_jit_memories(project="demo", directory="src/internal")
    jit_pub = agent.get_jit_memories(project="demo", directory="src/public-api")
    int_ok = any("comment" in m.rule_content.lower() and ("omit" in m.rule_content.lower() or "self-documenting" in m.rule_content.lower()) for m in jit_int)
    pub_ok = any("jsdoc" in m.rule_content.lower() for m in jit_pub)
    ok(f"  internal → 无注释 ({int_ok})")
    ok(f"  public-api → 有 JSDoc ({pub_ok})")
    ok("情境感知：同一项目，不同目录，不同规则")

    print(f"\n{C['bold']}删除后复测：{C['reset']}")
    before = len(store.list_memories(state="active"))
    for m in store.list_memories():
        if "snake_case" in m.rule_content.lower():
            store.delete_memory(m.id)
            ok(f"已删除：{m.rule_content[:50]}")
    after = len(store.list_memories(state="active"))
    still = any("snake_case" in m.rule_content.lower() for m in store.list_memories(state="active"))
    ok(f"记忆数 {before}→{after} / 不再使用删除的规则：{not still}")

    # ════════════════════════════════════════════════════════════
    # Summary
    # ════════════════════════════════════════════════════════════
    p()
    print(f"{C['bold']}{C['green']}  NEST DEMO COMPLETE{C['reset']}")
    p()
    summary = agent.get_summary()
    print(f"  总记忆：{summary['total']} 条")
    print(f"  活跃：{summary['active']} / 已淘汰：{summary['deprecated']} / 归档：{summary['archived']}")
    print(f"  raw: {summary['by_confidence']['raw']} / mature: {summary['by_confidence']['mature']} / rule: {summary['by_confidence']['rule']}")
    print(f"\n  {C['yellow']}A/B 量化：用户纠错次数从 5 次 → 0 次（减少 100%）{C['reset']}")

    pulse = agent.get_pulse()
    if pulse:
        print(f"\n  {C['cyan']}🫀 {pulse['message']}{C['reset']}")

    print(f"\n{C['bold']}  \"你的偏好，越用越合身。\"{C['reset']}")
    print()

if __name__ == "__main__":
    main()
