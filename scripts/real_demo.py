#!/usr/bin/env python3
"""WASC 真實使用場景 Demo — 自然對話，無測試框架感"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm import LLMClient
from src.store import MemoryStore
from src.agent import MemoryAgent

B = "\033[1m"; G = "\033[32m"; C = "\033[36m"; Y = "\033[33m"; R = "\033[0m"; D = "\033[2m"

def say(text: str):
    """快速打字（用戶訊息）"""
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(0.002)
    print()

def chat_ai(agent, msg: str, n: int = 400) -> str:
    """呼叫 AI，附思考提示"""
    print(f"{G}🤖 助手：{D}思考中...{R}", end="", flush=True)
    r = agent.chat(msg)
    print(f"\r{G}🤖 助手：{R}")  # 清除思考提示
    print(r[:n])
    print(f"{D}...{R}\n")
    return r

def show_memories(agent, title=""):
    mems = agent.view_memories(include_deprecated=True)
    if not mems:
        return
    active = [m for m in mems if m["status"] == "active"]
    decay = [m for m in mems if m.get("auto_decay")]
    fixed = [m for m in active if not m.get("auto_decay")]

    print(f"\n{D}┌─ 記憶快照")
    if fixed:
        print(f"│ 固定記憶 ({len(fixed)}):")
        for m in fixed:
            print(f"│   [{m['type']}] {m['content'][:55]}")
    if decay:
        print(f"│ 衰退記憶 ({len(decay)}):")
        for m in decay:
            bar = "█" * (m["decay_score"] // 20) + "░" * (5 - m["decay_score"] // 20)
            print(f"│   [{m['type']}] {m['content'][:45]} [{bar}] {m['decay_score']}%")
    print(f"└{'─'*50}{R}\n")

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

    # ---- Day 1 ----
    print(f"{B}── 第一天：新專案開始 ──{R}\n")

    print(f"{C}👤 開發者：{R}", end=""); say("幫我寫一個 React login 頁面")

    r = chat_ai(agent, "幫我寫一個 React login 頁面", 400)

    print(f"{C}👤 開發者：{R}", end="")
    say("等一下，為什麼用 useState？我是 React 新手，可以解釋每一步嗎？")

    r = chat_ai(agent, "等一下，為什麼用 useState？我是 React 新手，可以解釋每一步嗎？", 400)
    show_memories(agent)

    print(f"{C}👤 開發者：{R}", end="")
    say("還有，我偏好 TypeScript strict mode，functional component，不要 class，用 named export")

    r = chat_ai(agent, "還有，我偏好 TypeScript strict mode，functional component，不要 class，用 named export", 300)

    show_memories(agent)

    # ---- 一週後 ----
    print(f"\n{B}── 一週後：漸漸上手 ──{R}\n")

    print(f"{C}👤 開發者：{R}", end=""); say("幫我加一個 signup 頁面")
    r = chat_ai(agent, "幫我加一個 signup 頁面", 400)

    print(f"{C}👤 開發者：{R}", end=""); say("再幫我加個 dashboard")
    r = chat_ai(agent, "再幫我加個 dashboard", 300)

    show_memories(agent)

    # ---- 兩週後：變熟手，不再問為什麼 ----
    print(f"\n{B}── 兩週後：變成熟手了 ──{R}\n")
    print(f"{D}（注意：以下對話不再問「為什麼」，衰退開始）{R}\n")

    # Round 1 — 沒問為什麼 → 衰退 100→80
    print(f"{C}👤 開發者：{R}", end=""); say("改用 default export 吧")
    r = chat_ai(agent, "改用 default export 吧", 300)

    show_memories(agent)

    # Round 2 — 沒問為什麼 → 衰退 80→60
    print(f"{C}👤 開發者：{R}", end=""); say("幫我優化效能")
    r = chat_ai(agent, "幫我優化效能", 250)
    show_memories(agent)

    # Round 3 — 沒問為什麼 → 衰退 60→40
    print(f"{C}👤 開發者：{R}", end=""); say("加個 loading spinner")
    r = chat_ai(agent, "加個 loading spinner", 250)
    show_memories(agent)

    # ---- 三週後：徹底熟手，衰退到底 ----
    print(f"\n{B}── 三週後：完全熟練 ──{R}\n")
    print(f"{D}（不再需要解釋 → 自動淡出）{R}\n")

    print(f"{C}👤 開發者：{R}", end=""); say("重構一下這個模組")
    r = chat_ai(agent, "重構一下這個模組", 250)
    show_memories(agent)

    print(f"{C}👤 開發者：{R}", end=""); say("加個 error boundary")
    r = chat_ai(agent, "加個 error boundary", 250)
    print(f"{D}...{R}")

    show_memories(agent)

    # ---- End ----
    print(f"\n{B}{'─'*55}{R}")
    print(f"{G}三週的變化：{R}")
    print(f"{G}  第一週：AI 偵測到新手 → 自動詳細解釋，分數 100%{R}")
    print(f"{G}  第二週：不再問為什麼 → 衰退開始，100→80→60→40{R}")
    print(f"{G}  第三週：完全熟練 → 衰退歸零，自動淘汰，不再囉嗦{R}")
    print(f"{G}  固定記憶不受影響 → 偏好仍然被遵守{R}")
    print(f"{G}  這就是「自成長 · 越用越懂你」{R}")
    print(f"{B}{'─'*55}{R}")

if __name__ == "__main__":
    main()
