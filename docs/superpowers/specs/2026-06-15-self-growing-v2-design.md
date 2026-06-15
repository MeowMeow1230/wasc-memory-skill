# Self-Growing Memory Skill v2 — Design Spec

> **WASC June Challenge**: 自成長 · 越用越懂你
> **Status**: Final Design · Ready for Implementation
> **Last Updated**: 2026-06-15

---

## 1. Problem Statement

### 1.1 v1 為什麼失敗

v1 在自動化評分中取得 97/100，但用戶從未真正使用。三個結構性根因：

1. **為評分打造，不是為問題打造** — rubric 盡可能拿滿，但沒有解決任何真實的日常痛點
2. **用戶不信任** — 記憶管理需要用戶操作 MCP tools（reset/view/edit/delete），摩擦大、透明度低
3. **只聽對話、不看行為** — 用戶修改程式碼的行為信號完全被忽略。這是最致命的盲點：用戶嘴上說「好」，手上卻把程式碼整段重寫了。v1 學到的是「好」，不是「重寫」

### 1.2 v2 解決的真實問題

用戶在 AI 輔助開發中重複糾正同一個偏好，平均 5-8 次同一事項才會穩定生效。隨著對話增長，CLAUDE.md 規則被推入 context 深處，模型注意力衰減 30%+。用戶說：「我不想管理另一個記憶系統。我只想**越用越不需要重複說話**。」

---

## 2. Core Insight & Design Philosophy

> **從「用戶說了什麼」擴展到「用戶做了什麼」。越用越安靜，越用越準。**

### 設計原則

| 原則 | 含義 |
|------|------|
| **行為 > 話語** | Diff 行為是比對話更誠實的信號。用戶說「OK」但把程式碼全改了 → OK 是假的，改動是真的 |
| **確定性優先** | 能靠 regex + 編輯距離搞定的事，絕不消耗 LLM tokens |
| **學習期問，應用期沉默** | 不確定時主動確認一次。確定了就永遠閉嘴、默默生效 |
| **越用越不需要說話** | 終極成功指標：用戶的重複糾正次數持續下降 |

---

## 3. Architecture

### 3.1 五階段故事線

```
階段 1：觀察 ──── 雙軌信號捕獲（對話 + Diff）+ 紅線攔截
        │
        ▼
階段 2：理解 ──── 正交分類 + 模式發現 + 信號追溯
        │
        ▼
階段 3：確認 ──── 雙軌驗證（學習期問 → 確認升級）
        │
        ▼
階段 4：適應 ──── JIT 情境注入 + 衝突淘汰 + 時間衰減
        │
        ▼
階段 5：進化 ──── Suggest 寫入 + 對話摘要 + A/B 量化證據
```

### 3.2 組件架構圖

```
User: Conversation + Code Edits
        │
        ▼
┌─ signal_capture.py ──────────────────────────────┐
│                                                   │
│  對話信號 (regex, 零 LLM)                          │
│    ├─ 糾正: "不要 X" / "別 X" / "你又忘了"         │
│    ├─ 前置: "先找論文" / "直接做"                   │
│    └─ 紅線: "絕對不要" / "never" / "stop doing"    │
│                                                   │
│  行為信號 (編輯距離, 零 LLM)                        │
│    ├─ style_edit: 只改變數名/格式                   │
│    ├─ structure_rewrite: 刪掉函數、換寫法重寫        │
│    ├─ full_delete: 整段生成結果刪除                  │
│    └─ compromise: Accept 後 10min 內該檔案被大改     │
│                                                   │
│  產出: Signal[] (帶 trigger_count + context)        │
└──────────────────┬────────────────────────────────┘
                   ▼
┌─ classifier.py ──────────────────────────────────┐
│                                                   │
│  觸發閘門:                                         │
│    ├─ 常規路徑: trigger_count >= 3 → 呼叫 LLM     │
│    └─ 紅線路徑: 強否定詞 或 連續 2 次 full_delete   │
│        → 立即呼叫 LLM，跳過累積門檻                  │
│                                                   │
│  LLM 分類輸出:                                     │
│    ├─ type: preference / rule / workflow / method │
│    ├─ scope + scope_value: 綁定作用域               │
│    ├─ condition: IF [context] THEN [action]       │
│    ├─ principle: 抽象泛化原則                       │
│    └─ 模式發現: 用戶從未說但行為上重複出現的模式       │
│                                                   │
│  產出: Memory (帶 confidence + source_signals)     │
└──────────────────┬────────────────────────────────┘
                   ▼
┌─ agent.py ───────────────────────────────────────┐
│                                                   │
│  學習期 (confidence < 80):                         │
│    ├─ 首次進入 mature (40): 觸發雙軌驗證確認問題     │
│    ├─ 用戶確認 → 直接升 rule (80)                   │
│    ├─ 用戶拒絕 → 降回 raw (10)，記錄拒絕原因         │
│    └─ 情境限定: 更新 scope + scope_value，升 rule   │
│                                                   │
│  應用期 (confidence >= 80):                        │
│    ├─ JIT 情境注入: 依當前 context 匹配 Top 3-5     │
│    ├─ 沉默生效: 不問、不提醒、不中斷                  │
│    └─ 衝突即時淘汰 + 時間衰減降級                    │
│                                                   │
│  產出: 用戶重複糾正次數持續下降                      │
└──────────────────┬────────────────────────────────┘
                   ▼
┌─ memory_store.py ────────────────────────────────┐
│                                                   │
│  記憶持久化 (本地 JSON 檔案)                         │
│  信心層級: raw(0-39) / mature(40-79) / rule(80-100)│
│  狀態: active / deprecated / archived              │
│  操作: CRUD + 信心升降 + 時間衰減計時                │
│                                                   │
│  產出: 可查詢、可追溯、可編輯、可刪除的記憶庫          │
└──────────────────────────────────────────────────┘
```

---

## 4. Data Model

### 4.1 Signal（原始信號）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | str | UUID，唯一識別 |
| `source` | `"dialog"` \| `"diff"` | 信號來源 |
| `dialog_type` | `"correction"` \| `"pre_instruction"` \| `"feedback"` \| `null` | 對話信號子類 |
| `diff_type` | `"style_edit"` \| `"structure_rewrite"` \| `"full_delete"` \| `"compromise"` \| `null` | 行為信號子類 |
| `content` | str | 原始對話文本或 Diff patch 內容 |
| `context` | dict | 捕捉時的情境：`{project, branch, directory, file_extension, timestamp}` |
| `trigger_count` | int | 該相似信號累積出現次數（用於判斷是否觸發 LLM 分類） |
| `red_line` | bool | 是否為紅線信號（強否定詞或連續 full_delete），立即觸發 |
| `created_at` | datetime | 首次捕捉時間 |

### 4.2 Memory（結構化記憶實體）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | str | UUID，唯一識別 |
| `rule_content` | str | LLM 提煉後的抽象原則（例："在 React 組件中優先使用 hooks 而非 class"） |
| `type` | enum | `"preference"` \| `"rule"` \| `"workflow"` \| `"method"` |
| `scope` | enum | `"global"` \| `"workspace"` \| `"repo"` \| `"directory"` |
| `scope_value` | str | 具體路徑或專案名（例：`"/Users/kun/Manbang v101"`、`"src/components"`） |
| `condition` | str | 觸發條件 — `IF [context] THEN [action]` |
| `principle` | str | 泛化後的抽象原則 |
| `confidence` | int | 0-100。隨觸發次數增加，隨時間/衝突衰減 |
| `state` | enum | `"active"` \| `"deprecated"` \| `"archived"` |
| `source_signals` | list[str] | 關聯的 Signal IDs，用於追溯「這個記憶從哪裡學來的」 |
| `last_triggered` | datetime | 最後一次被應用或驗證的時間（用於時間衰減計算） |
| `created_at` | datetime | 記憶建立時間 |

---

## 5. Signal Capture（階段 1：觀察）

### 5.1 對話信號偵測（regex，零 LLM tokens）

| 信號類別 | 匹配模式（示例） | dialog_type |
|---------|----------------|------------|
| 糾正 | 「不要 X」「別 X」「應該 Y」「你又忘了 Z」「不是這樣」「改成」 | `correction` |
| 前置指令 | 「先找論文」「先討論」「直接做」「不急」「看一下再做」 | `pre_instruction` |
| 反饋 | 「這個好」「這個不行」「繼續」「可以」 | `feedback` |
| ⚡ 紅線 | **「絕對不要」「永遠不要」「never」「stop doing」「不准」** | `correction` + `red_line: true` |

### 5.2 Diff 行為分類（編輯距離，零 LLM tokens）

| Diff 模式 | diff_type | 信號解讀 | 優先級 |
|-----------|-----------|---------|:---:|
| 改變數名/格式/縮排 | `style_edit` | 程式碼風格偏好 | 正常 |
| 刪掉 AI 寫的函數、換寫法重寫 | `structure_rewrite` | 設計哲學/架構偏好 | 正常 |
| 把 AI 生成的整段刪除 | `full_delete` | 工作流偏好或強烈不認同 | ⚡ 連續 2 次 → 紅線 |
| Accept 後 10min 內該檔案被大幅修改 | `compromise` | 用戶其實不滿意，**不升級** | 降級 |

### 5.3 信號去重與合併

相同 `content` + 相同 `source` + 相同 `context.project` 的信號 → 合併，遞增 `trigger_count`。紅線信號不參與合併——獨立保留。

### 5.4 紅線攔截機制（Red-Line Intercept）

常規路徑需要 `trigger_count >= 3` 才呼叫 LLM。但以下情況**立即觸發 LLM 提取，無視累積次數**：

| 觸發條件 | 動作 |
|---------|------|
| 對話命中強否定詞（「絕對不要」「never」等） | 標記 `red_line: true`，即時送入 LLM 分類，confidence 起點設為 60 |
| Diff `full_delete` 連續出現 2 次（同一檔案/同一類型任務） | 標記 `red_line: true`，即時送入 LLM 分類，confidence 起點設為 60 |

這解決了 v1 最大的信任缺陷：用戶說「**絕對不要**這樣寫」時，Skill 不需要等到第 3 次才開始學。

---

## 6. Classification & Pattern Discovery（階段 2：理解）

### 6.1 LLM 觸發閘門

```
if signal.red_line:
    → 立即觸發 LLM
elif signal.trigger_count >= 3:
    → 常規觸發 LLM
else:
    → 僅記錄，不消耗 LLM tokens
```

### 6.2 LLM 分類合約

**輸入**：Signal 內容 + 情境 context + diff_type/dialog_type + 相關歷史 Memory

**輸出**：

| 輸出欄位 | 說明 |
|---------|------|
| `rule_content` | 提煉後的具體規則 |
| `type` | 偏好類型（preference / rule / workflow / method） |
| `scope` | `global` \| `workspace` \| `repo` \| `directory` |
| `scope_value` | 具體路徑或專案名 |
| `condition` | `IF [context] THEN [action]` 格式的觸發條件 |
| `principle` | 抽象泛化原則（從具體案例推到通用原則） |

### 6.3 模式發現（Pattern Discovery）

在執行常規分類時，LLM **必須**額外檢查：

> Signal 池中是否存在**用戶從未明確說出、但在行為中重複出現**的模式？

- 若有：生成一條待確認記憶，`confidence` 設為 40（mature 最低門檻），`source_signals` 關聯相關信號
- 若無：僅輸出常規分類結果

### 6.4 信號追溯

每條 Memory 的 `source_signals` 欄位記錄所有促成該記憶的 Signal IDs。評審問「為什麼 AI 學到這個？」→ 可精確指向第幾輪對話、哪段 Diff。

---

## 7. Confidence & Validation（階段 3：確認）

### 7.1 信心層級

| 層級 | 分數 | 觸發條件 | 行為 |
|------|:---:|---------|------|
| **raw** | 0-39 | trigger_count 1-2 | 僅記錄，不注入、不問 |
| **mature** | 40-79 | trigger_count 3+ 或紅線觸發 | 首次進入 mature 時觸發確認問題；相關任務注入提醒 |
| **rule** | 80-100 | trigger_count 5+ 或用戶確認 | JIT 情境注入，沉默生效，永遠不再問 |

### 7.2 雙軌驗證（Dual-Track Validation）

記憶首次達到 `confidence: 40`（mature 最低門檻）時，在 AI 回覆末尾**輕量級**附加確認：

> 「PS: 我注意到[觀察]，以後[建議]好嗎？」

用戶回應處理：

| 回應 | 動作 |
|------|------|
| 「好」「嗯」「可以」「對」 | confidence → 80（rule），scope 維持 |
| 「不要」「不行」「不對」 | confidence → 10（raw），記錄拒絕原因 |
| 情境限定（「這個專案可以，其他不行」） | 更新 scope + scope_value，confidence → 80 |
| 忽略不回應 | 維持 mature，下次類似情境再問一次（上限 2 次，超過自動降至 raw 30） |

紅線觸發的記憶：confidence 起點 60，**不觸發確認問題**，直接進入學習期觀察，下次相關任務時驗證。

---

## 8. Application & Decay（階段 4：適應）

### 8.1 JIT 情境注入（Just-in-Time Context Injection）

**嚴禁全量注入。** 每次任務開始時，基於當前情境匹配最相關的記憶：

```
當前任務 Context:
  ├─ project: "Manbang v101"
  ├─ directory: "src/constraint_parser"
  ├─ file_extension: ".py"
  └─ task_type: "bug_fix"

記憶庫查詢:
  1. scope_value 匹配 "Manbang v101" → 精準匹配
  2. scope_value 匹配 "*.py" → 泛化匹配
  3. scope: global → 全局適用

排序: scope_value 精準 > scope_value 泛化 > global
取 Top 3-5，confidence >= 80 的記憶 → 靜默注入當次 system prompt
```

不需要向量資料庫。`scope_value` + `condition` + `file_extension` 的結構化匹配已足夠精準。

### 8.2 衝突淘汰

新 Memory 與舊 Memory 衝突時：

| 情境 | 處理 |
|------|------|
| 新 confidence >= 舊 confidence | 新取代舊，舊 → `deprecated`，`source_signals` 保留 |
| 新 confidence < 舊 confidence | 兩者保留，LLM 判斷是衝突還是 scope 互補 |
| scope 不同（Project A vs Project B） | 不是衝突，各自獨立生效 |

### 8.3 時間衰減

| 當前層級 | 衰減條件 | 降級目標 |
|---------|---------|---------|
| mature | 連續 3 次相關任務未觸發 | → raw (30) |
| rule | 連續 5 次相關任務未觸發 | → mature (50) |
| deprecated | 30 天後 | → archived |

### 8.4 概念漂移防護

用戶偏好會隨技術棧演進。當新信號與舊 rule 衝突：舊 rule **不直接刪除**，而是標記 `deprecated` + 記錄衝突原因。舊記憶的 `source_signals` 完整保留，可供日後回溯。

### 8.5 學習脈搏（Learning Pulse）

v1 最大的失敗原因：完全沉默 = 用戶永遠不知道 skill 是否活著 → **永不信任**。

v2 用「學習脈搏」解決這個信任問題。不是每輪打擾，而是**定期、輕量、一句話**讓用戶感知 skill 的存在與進展：

| 時機 | 內容 | 頻率 |
|------|------|------|
| **新 session 開始** | 「歡迎回來。上次學到 N 條偏好，M 條已自動套用。`view` 查看。」 | 每次新 session 一次 |
| **規則升級時** | 「PS: 學到一條新規則：[rule_content]。`view` 查看全部。」 | 升級時（rule 級不觸發，已沉默） |
| **里程碑** | 「目前共 N 條偏好，M 條成熟。你最近很少重複糾正了。」 | 每 10 條成熟記憶 |

**設計原則**：

- 脈搏不是「功能提醒」，是「存在證明」
- 不問問題、不要求回應、不中斷工作
- 資訊密度高：一行包含進展、狀態、下一步
- 用戶可隨時 `view` 查看更多（但不需要）

---

## 9. Evolution（階段 5：進化）

### 9.1 Suggest 模式

當記憶達到 rule 級（confidence >= 80）時，**不自動寫入 CLAUDE.md**。生成建議，讓用戶確認後才寫入。確保 AI 不擅自修改用戶的專案設定。

### 9.2 對話摘要

每次測試結束或階段性里程碑時，產生摘要：

- 這段互動學到了什麼（新記憶清單）
- 升級了什麼（raw → mature → rule）
- 淘汰了什麼（deprecated / archived）

### 9.3 A/B 量化證據

同一測試場景的 before/after 對比：

- **Baseline（無 Skill）**：用戶重複糾正 N 次
- **Skill（有 Skill）**：用戶重複糾正 M 次

量化指標：**減少比例 = (N - M) / N × 100%**

---

## 10. 8-Step Test Script

使用真實程式開發協作場景。每一步對應 rubric 評分維度。

| Step | 動作 | 預期 Skill 行為 | Rubric 維度 | 階段 |
|:---:|------|----------------|-----------|:---:|
| 1 | `reset` 清空記憶 | 確認所有記憶為空白 | 可复测性 | — |
| 2 | 首次任務：寫一個 Python 工具函數 | 後台記錄對話 + Diff 信號為 raw | 有效记忆提取 | 觀察 |
| 3 | 用戶反饋：改變數名為 snake_case、刪掉過度註解、說「絕對不要用 camelCase」 | diff → style_edit；「絕對不要」→ 紅線即時觸發 LLM 分類 | 有效记忆提取 | 觀察→理解 |
| 4 | `view` 查看記憶 | 展示結構化記憶：rule_content / scope / scope_value / source_signals 追溯 | 用户控制与透明度 | 理解 |
| 5 | 再次任務：寫一個 TypeScript 工具函數 | 自動應用 snake_case（泛化 Python→TS）。無 camelCase。首次確認問題出現 | 记忆应用效果 | 確認 |
| 6 | 偏好變化：用戶說「公開 API 函數可以加 JSDoc 註解」 | scope 從 global 更新為「公開 API 例外」，confidence 更新 | 记忆更新与淘汰 | 適應 |
| 7 | 第三次任務：同時寫內部 helper + 公開 API 函數 | JIT 匹配後：內部函數無註解、公開 API 有 JSDoc — 情境感知應用 | 记忆应用效果 + 结果质量 | 適應 |
| 8 | `delete`「不加註解」規則，再做任務 | 記憶刪除後恢復預設行為，不再強制無註解 | 记忆更新与淘汰 + 可复测性 | 進化 |

---

## 11. Demo Storyline（三幕 Aha Moment）

以下是用戶視角的敘事，協助評審理解產品情感價值：

### Act 1：煩躁（Day 1）

用戶寫 Python。AI 輸出 `camelCase` 的變數名。

用戶糾正：「用 `snake_case`。」修改了變數名，AI 說好。Skill 在後台記錄：`dialog: correction` + `diff: style_edit`。trigger_count = 1，raw 層級。什麼都沒發生。

### Act 2：懷疑（Day 2）

用戶開新檔案。AI 又輸出 `camelCase`。用戶罵了一句「**我說過不要 camelCase！**」，然後手動把整段程式碼重寫。

Skill 偵測到：紅線信號（「不要」）+ `diff: structure_rewrite`。紅線攔截啟動 → 立即呼叫 LLM 提取為 Memory：`rule_content: "使用 snake_case 命名"`，`scope: global`，`confidence: 60`（紅線起點）。

### Act 3：Aha Moment（Day 3）

用戶開全新專案，一句偏好都沒說。AI 輸出第一行程式碼——**完美的 snake_case**，沒有任何註解。

沒有彈窗確認。沒有記憶管理面板。沒有 PS 問題。用戶什麼都沒做。AI 就是懂他了。

**這就是「自成長」的真正定義：用戶不再需要重複說話。**

---

## 12. Project Structure

```
wasc-memory-skill/
├── SKILL.md              ← 合約（AI 讀、評審看）
├── README.md
├── README_CN.md          ← 中文說明
├── SETUP.md
├── LICENSE (MIT-0)
├── skill/
│   └── SKILL.md          ← 提交用 skill 描述
├── src/
│   ├── __init__.py
│   ├── models.py         ← Signal + Memory 資料模型
│   ├── memory_store.py   ← 記憶 CRUD + 信心層級 + 時間衰減
│   ├── signal_capture.py ← 雙軌信號捕獲（對話 regex + Diff 分類 + 紅線攔截）
│   ├── classifier.py     ← LLM 分類器（正交分類 + 模式發現 + 紅線路徑）
│   └── agent.py          ← 主邏輯（學習/應用期切換 + JIT 注入 + 雙軌驗證 + 衝突淘汰）
├── scripts/
│   ├── reset_memory.py   ← CLI: 清空記憶
│   ├── view_memory.py    ← CLI: 查看記憶（含 source_signals 追溯）
│   ├── edit_memory.py    ← CLI: 編輯記憶
│   ├── delete_memory.py  ← CLI: 刪除記憶
│   ├── demo.py           ← 8 步完整 demo（rubric 對標）
│   └── ab_compare.py     ← A/B 對比腳本
├── tests/
│   └── test_harness.py   ← 8 步自動化測試（rubric 6 維度評分）
├── evals/
│   └── test_report.json  ← 測試結果
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-06-15-self-growing-v2-design.md
└── pyproject.toml
```

---

## 13. Rubric Mapping

| 維度 | 權重 | v2 設計對應 |
|------|:---:|---------|
| **可复测性** | 10 | `scripts/reset|view|edit|delete_memory.py` 四個 CLI，評審可從零開始驗證 |
| **有效记忆提取** | 20 | 雙軌信號來源（對話 + Diff）、正交分類（Scope × Type × Condition）、紅線攔截、區分長期偏好/場景規則/工作方法/臨時任務 |
| **记忆应用效果** | 25 | JIT 情境注入（Top 3-5）、泛化（Python → TypeScript）、應用期沉默生效 |
| **记忆更新与淘汰** | 20 | 衝突即時淘汰（新推翻舊）、時間衰減降級、概念漂移 deprecate 不硬刪 |
| **用户控制与透明度** | 10 | `source_signals` 追溯鏈、雙軌驗證透明確認、scope_value 明確綁定 |
| **结果质量与真实可用性** | 15 | 真實開發場景（非寫詩/笑話）、A/B 量化減少比例、三幕 Demo 展示情感價值 |

---

## 14. Key Differentiators

| # | 差異化點 | 為什麼別人沒有 |
|---|---------|-------------|
| 1 | **雙軌信號（對話 + Diff）** | 其他參賽者只看對話文字。我們從程式碼修改行為中提取更誠實的信號 |
| 2 | **紅線攔截** | 用戶說「絕對不要」不需要等 3 次。常規偏好緩學、強否定即學，尊重人類溝通的自然節奏 |
| 3 | **模式發現** | 發現用戶自己都沒察覺的行為規律。不是被動記事本，是主動觀察者 |
| 4 | **JIT 情境注入** | 不做全量注入導致的 token 爆炸。按 scope_value 精準匹配，每次只注入最相關的 Top 3-5 |
| 5 | **學習期問、應用期沉默** | v1 從頭問到尾或用戶手動管理。v2 只在第一次確認，之後永遠沉默 |
| 6 | **source_signals 追溯** | 評審問「為什麼學到這個」→ 精確指向第幾輪對話、哪段 Diff。全透明 |
| 7 | **真實場景 + 量化證據** | Demo 是真實程式開發，有 A/B 數據。不是寫詩/笑話 |
| 8 | **學習脈搏** | 完全沉默 = 用戶不信任。定期一句話讓用戶知道 skill 活著、學了什麼、進展如何 |
