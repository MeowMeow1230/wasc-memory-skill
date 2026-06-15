# Self-Growing Memory Skill v2 — 自成長記憶技能

**WASC 六月挑戰：自成長 · 越用越懂你**

## 概述

一個在背景默默觀察你的糾正和程式碼修改，學習偏好，然後沉默應用的 Claude Code Skill。

**核心理念**：越用越安靜，越用越準。

## 架構

Python 做機械的事（信號捕獲、儲存、JIT 注入）。Claude Code 做智慧的事（語義分組、分類、信心判斷）。零外部 API。

## 跟 v1 的區別

| | v1 | v2 |
|------|----|----|
| 信號來源 | 僅對話文字 | 對話 + Diff 行為 |
| 分類方式 | Python + DeepSeek API | Claude Code 原生 |
| 應用方式 | 全量注入 | JIT 情境注入 (Top 20) |
| 用戶互動 | 6 個 MCP 工具 | CLI 腳本 + PS 輕量確認 |
| 外部依賴 | anthropic SDK | **零** |
| 信號捕獲 | 只看 regex | **雙軌**：regex + Claude 補漏 |

## 快速開始

```bash
pip install -e .
python3 scripts/demo.py           # 8 步 WASC demo
python3 tests/test_harness.py     # Rubric 評分 (100/100)
```

## 測試

```bash
python3 tests/test_harness.py     # 自動化 rubric 評分
python3 scripts/replay_session.py # 真實歷史交叉驗證
python3 scripts/ab_compare.py     # A/B 量化對比
```
