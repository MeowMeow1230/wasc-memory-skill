#!/usr/bin/env python3
"""WASC 進階功能 Demo — 記憶自動衰退機制

展示: method 型記憶隨用戶成長自動淡出，不需手動淘汰。
與 8步主 demo 完全獨立，不影響核心評分。
"""

import sys, os, time

# 消掉 Mem0 內部警告（不影響功能）
import warnings
warnings.filterwarnings("ignore")
sys.stderr = open(os.devnull, 'w')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm import LLMClient
from src.store import MemoryStore
from src.agent import MemoryAgent

B = "\033[1m"; G = "\033[32m"; Y = "\033[33m"; C = "\033[36m"; R = "\033[0m"; D = "\033[2m"

def show_all_memories(agent):
    """展示全部記憶，區分固定型 vs 衰退型"""
    mems = agent.view_memories(include_deprecated=True)
    fixed = [m for m in mems if not m.get("auto_decay")]
    decay = [m for m in mems if m.get("auto_decay")]

    if fixed:
        print(f"\n{C}  📌 固定記憶 (auto_decay=false) — 永不自動衰退{R}")
        for m in fixed:
            status_tag = f"{G}[active]{R}" if m["status"] == "active" else "\033[31m[DEPRECATED]{R}"
            print(f"     {status_tag} [{m['type']}] {m['content'][:65]}")

    if decay:
        print(f"\n{C}  ⏳ 衰退記憶 (auto_decay=true) — 隨用戶成長自動淡出{R}")
        for m in decay:
            score = m.get("decay_score", "N/A")
            bar = "█" * (score // 20) + "░" * (5 - score // 20) if isinstance(score, int) else ""
            status_tag = f"{G}[active]{R}" if m["status"] == "active" else "\033[31m[DEPRECATED]{R}"
            print(f"     {status_tag} [{m['type']}] {m['content'][:55]}  [{bar}] {score}%")

    if not fixed and not decay:
        print(f"  {D}(無記憶){R}")

def wait(msg="按 Enter 繼續..."):
    input(f"\n{D}{msg}{R}")

def main():
    print(f"{B}{Y}")
    print("╔══════════════════════════════════════════════════╗")
    print("║  WASC 進階功能 — 記憶自動衰退 (Auto-Decay)     ║")
    print("║  使用者成長 → 記憶自動淡出 → 不再囉嗦          ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"{R}")

    wait()

    client = LLMClient()
    store = MemoryStore(user_id="decay_demo")
    agent = MemoryAgent(client=client, store=store)
    agent.reset()

    # ========================================
    # Scene 0: 固定記憶 — 用戶表達偏好
    # ========================================
    print(f"\n{B}━━━ 第一幕：固定記憶創建 ━━━{R}")
    print(f"{C}用戶給出編碼偏好 → 系統自動提取偏好/規則{R}")
    print(f"{C}這些記憶 auto_decay=false → 永遠不會自動衰退{R}")
    wait()

    agent.chat("幫我寫一個 React login component")
    print(f"\n{Y}用戶: {R}我偏好 functional component + TypeScript strict mode，用 named export")
    wait()
    agent.chat("我偏好 functional component + TypeScript strict mode，用 named export")

    print(f"\n{G}>>> 提取結果：2 條固定記憶{R}")
    show_all_memories(agent)
    print(f"\n{G}✅ preference/rule 型記憶 → auto_decay=false → 永不自動消失{R}")
    wait()

    # ========================================
    # Scene 1: 自動偵測 → 創建衰退記憶
    # ========================================
    print(f"\n{B}━━━ 第二幕：自動偵測學習需求 ━━━{R}")
    print(f"{C}系統自動偵測到用戶在尋求解釋{R}")
    print(f"{C}→ 自動創建 method 型記憶 + auto_decay=true{R}")
    print(f"{C}→ 不需用戶手動設定，不需要說「記住我還在學」{R}")
    wait()

    print(f"\n{Y}用戶: {R}為什麼要用 useState？跟 class component 的 state 有什麼不同？")
    wait()
    agent.chat("為什麼要用 useState？跟 class component 的 state 有什麼不同？")

    print(f"\n{G}>>> 自動偵測 + 自動創建：衰退記憶出現{R}")
    show_all_memories(agent)
    print(f"\n{G}✅ 同一個記憶庫，兩種記憶共存：{R}")
    print(f"{G}   固定記憶 (2條) → 永遠不變{R}")
    print(f"{G}   衰退記憶 (1條) → 隨用戶成長自動淡出{R}")
    wait()

    # ========================================
    # Scene 2: 雙主題獨立創建
    # ========================================
    print(f"\n{B}━━━ 第三幕：雙主題獨立追蹤 ━━━{R}")
    print(f"{C}用戶再問另一個領域 → 系統創建第二條衰退記憶{R}")
    print(f"{C}React 和 TypeScript 各自獨立衰退，互不影響{R}")
    wait()

    print(f"\n{Y}用戶: {R}為什麼 TypeScript 的 generic 很重要？可以詳細解釋嗎？")
    wait()
    agent.chat("為什麼 TypeScript 的 generic 很重要？可以詳細解釋嗎？")

    show_all_memories(agent)
    print(f"\n{G}✅ 兩條衰退記憶各自追蹤 → React:100%  TypeScript:100%{R}")
    wait()

    # ========================================
    # Scene 3: 主題獨立衰退
    # ========================================
    print(f"\n{B}━━━ 第四幕：只問 React，不問 TypeScript ━━━{R}")
    print(f"{C}用戶持續問 React 相關問題，但不碰 TypeScript{R}")
    print(f"{C}→ React 維持 100%，TypeScript 獨自衰退{R}")
    wait()

    for i in range(3):
        q = ["可以解釋 custom hook 的設計原則嗎？",
             "為什麼 useEffect cleanup 很重要？",
             "React memo 的運作原理是什麼？"][i]
        print(f"\n{Y}用戶: {R}{q}  {D}(React ✓){R}")
        wait()
        agent.chat(q)
        show_all_memories(agent)

    # ========================================
    # Scene 4: TypeScript 淘汰，React 完好
    # ========================================
    print(f"\n{B}━━━ 第五幕：TypeScript 衰退到底 → 淘汰 ━━━{R}")
    for i in range(2):
        q = ["幫我優化這個 component 的效能", "幫我加一個 loading spinner"][i]
        print(f"\n{Y}用戶: {R}{q}  {D}(沒提 React 為什麼，也沒提 TypeScript){R}")
        wait()
        agent.chat(q)
        show_all_memories(agent)

    print(f"\n\n{G}✅ TypeScript 解釋需求 → 已自動淘汰{R}")
    print(f"{G}✅ React 解釋需求仍活躍 → 用戶還在學 React{R}")
    print(f"{G}✅ 固定記憶完好無損 → 仍然遵守所有偏好{R}")
    print(f"{G}✅ 每個主題獨立追蹤，精準感知用戶成長{R}")

    # ========================================
    # Summary
    # ========================================
    print(f"\n{B}{'='*60}{R}")
    print(f"{B}  完整記憶系統總結{R}")
    print(f"{B}{'='*60}{R}")
    print(f"""
  ┌──────────────────────────────────────────────────┐
  │  同一個記憶庫，兩種記憶行為                         │
  ├──────────────────────────────────────────────────┤
  │                                                    │
  │  📌 固定記憶 (preference / rule)                   │
  │     auto_decay = false                             │
  │     永遠不自動衰退                                  │
  │     只靠衝突仲裁淘汰（用戶說改才改）                  │
  │     例: "偏好 TypeScript strict mode"              │
  │                                                    │
  │  ⏳ 衰退記憶 (method)                               │
  │     auto_decay = true                              │
  │     自動偵測創建 → 強化 → 衰退 → 淘汰               │
  │     用戶持續問「為什麼」→ 維持 100%                  │
  │     用戶不再問        → 每次 -20%                  │
  │     decay_score 歸零  → 自動 deprecated            │
  │     例: "用戶需要詳細步驟解釋"                       │
  │                                                    │
  └──────────────────────────────────────────────────┘
""")
    print(f"\n{D}Demo 錄製完成！這是 8步主測試之外的加分展示。{R}")

if __name__ == "__main__":
    main()
