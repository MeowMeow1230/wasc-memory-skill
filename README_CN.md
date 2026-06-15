# Self-Growing Memory Skill v2 — 自成長記憶技能

## 概述

一個從你的對話糾正和程式碼修改行為中學習偏好，然後在日常使用中**沉默應用**的 AI 編碼助手技能。

**核心理念**：越用越安靜，越用越準。

## 跟 v1 的區別

| | v1 | v2 |
|------|----|----|
| 信號來源 | 僅對話文字 | 對話 + Diff 行為 |
| 學習方式 | 被動計數 | 紅線攔截 + 常規累積 |
| 應用方式 | 全量注入 | JIT 情境注入 (Top 5) |
| 用戶互動 | 6 個 MCP 工具 | CLI 腳本 + PS 輕量確認 |
| 透明度 | 黑箱 | source_signals 完整追溯 |
| 信任感 | 無（完全沉默） | 🫀 學習脈搏定期報狀態 |

## 快速開始

```bash
pip install -r requirements.txt
python3 scripts/demo.py
```

## 測試

```bash
python3 -m pytest tests/ -v
python3 tests/test_harness.py
```
