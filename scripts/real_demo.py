#!/usr/bin/env python3
"""WASC 真實使用場景 Demo — 自然對話，無測試框架感"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm import LLMClient
from src.store import MemoryStore
from src.agent import MemoryAgent

B = "\033[1m"; G = "\033[32m"; C = "\033[36m"; Y = "\033[33m"; R = "\033[0m"; D = "\033[2m"

def type_out(text: str, delay: float = 0.02):
    """模擬打字效果"""
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()

def show_memories(agent, title=""):
    mems = agent.view_memories(include_deprecated=True)
    if not mems:
        return
    active = [m for m in mems if m["status"] == "active"]
    decay = [m for m in mems if m.get("auto_decay")]
    fixed = [m for m in active if not m.get("auto_decay")]

    print(f"\n{D}┌─ 記憶快照{' ' * 40}")
    if fixed:
        print(f"│ 固定記憶 ({len(fixed)}):")
        for m in fixed:
            print(f"│   [{m['type']}] {m['content'][:55]}")
    if decay:
        print(f"│ 衰退記憶 ({len(decay)}):")
        for m in decay:
            bar = "█" * (m["decay_score"] // 20) + "░" * (5 - m["decay_score"] // 20)
            print(f"│   [{m['type']}] {m['content'][:45]} [{bar}] {m['decay_score']}%")
    print(f"└{'─' * 50}{R}\n")

def main():
    client = LLMClient()
    store = MemoryStore(user_id="real_demo")
    agent = MemoryAgent(client=client, store=store)
    agent.reset()

    print(f"{B}{C}")
    print("╔══════════════════════════════════════════════╗")
    print("║  自成長記憶 Skill — 真實使用場景             ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"{R}\n")

    # ---- 第一天：新手模式 ----
    print(f"{B}── 第一天：新專案開始 ──{R}\n")
    time.sleep(0.5)

    print(f"{C}👤 開發者：{R}", end=""); type_out("幫我開一個 React 專案，我要做一個 login 頁面")
    time.sleep(0.3)
    print(f"\n{G}🤖 助手：{R}")
    r = agent.chat("幫我開一個 React 專案，我要做一個 login 頁面")
    type_out(r[:350], 0.005)
    print(f"{D}...{R}")

    time.sleep(1)
    print(f"\n{C}👤 開發者：{R}", end=""); type_out("等一下，我不太懂。為什麼用 useState 而不是一般變數？我是 React 新手，可以每個步驟都解釋嗎？")
    time.sleep(0.3)
    print(f"\n{G}🤖 助手：{R}")
    r = agent.chat("等一下，我不太懂。為什麼用 useState 而不是一般變數？我是 React 新手，可以每個步驟都解釋嗎？")
    type_out(r[:350], 0.005)
    print(f"{D}...{R}")

    show_memories(agent)

    time.sleep(1)
    print(f"{C}👤 開發者：{R}", end=""); type_out("還有，我偏好用 TypeScript strict mode，functional component，不要 class")

    print(f"\n{G}🤖 助手：{R}")
    r = agent.chat("還有，我偏好用 TypeScript strict mode，functional component，不要 class")
    type_out(r[:300], 0.005)
    print(f"{D}...{R}")

    show_memories(agent)
    time.sleep(1.5)

    # ---- 一週後：漸漸上手 ----
    print(f"\n{B}── 一週後：漸漸上手 ──{R}\n")
    time.sleep(0.5)

    print(f"{C}👤 開發者：{R}", end=""); type_out("幫我加一個 signup 頁面")
    time.sleep(0.3)
    print(f"\n{G}🤖 助手：{R}")
    r = agent.chat("幫我加一個 signup 頁面")
    type_out(r[:300], 0.005)
    print(f"{D}...{R}")
    time.sleep(1)

    print(f"{C}👤 開發者：{R}", end=""); type_out("再幫我加一個 dashboard，要顯示用戶數據")
    time.sleep(0.3)
    print(f"\n{G}🤖 助手：{R}")
    r = agent.chat("再幫我加一個 dashboard，要顯示用戶數據")
    type_out(r[:300], 0.005)
    print(f"{D}...{R}")

    show_memories(agent)
    time.sleep(1.5)

    # ---- 兩週後：熟手 ----
    print(f"\n{B}── 兩週後：變成熟手了 ──{R}\n")
    time.sleep(0.5)

    print(f"{C}👤 開發者：{R}", end=""); type_out("幫我把 login 改成 default export，其他頁面也改一下")
    time.sleep(0.3)
    print(f"\n{G}🤖 助手：{R}")
    r = agent.chat("幫我把 login 改成 default export，其他頁面也改一下")
    type_out(r[:300], 0.005)
    print(f"{D}...{R}")
    time.sleep(1)

    # 注意：這裡不再問為什麼
    print(f"{C}👤 開發者：{R}", end=""); type_out("幫我優化一下效能，加個 loading spinner")
    time.sleep(0.3)
    print(f"\n{G}🤖 助手：{R}")
    r = agent.chat("幫我優化一下效能，加個 loading spinner")
    type_out(r[:300], 0.005)
    print(f"{D}...{R}")
    time.sleep(1)

    show_memories(agent)

    # ---- 結尾 ----
    print(f"\n{B}{'─'*55}{R}")
    print(f"{G}三週的時間：{R}")
    print(f"{G}  新手 → 習慣偏好被記住 → 不需要的解釋自動淡出{R}")
    print(f"{G}  這就是「自成長 · 越用越懂你」{R}")
    print(f"{B}{'─'*55}{R}")

if __name__ == "__main__":
    main()
