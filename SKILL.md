---
name: self-growing-memory-v2
description: A coding assistant that learns your preferences from both what you say and what you edit — then silently applies them, reducing repetition over time.
---

# Self-Growing Memory Skill v2

## Contract

You (Claude Code) are the intelligence. Python is your notebook and regex engine.

### 1. Dual-Track Signal Capture

Every user message is captured through TWO paths:

**Track A — Regex (automatic, Python):**
Python's `signal_capture.py` scans every user message for broad correction patterns:
- Negations: "不要X", "别X", "絕對不要X", "never X", "stop doing X"
- Pre-instructions: "先討論", "先找論文", "直接做", "不急"
- Strong negation (red line): "绝对不要", "永远不要", "不准", "严禁"

When matched → signal enters the pool automatically. Zero cost.

**Track B — Your Own Observation (manual, you):**
As you read each user message, YOU decide if it contains useful signal that regex missed:
- "這個寫法不太好，換成 Y 試試" (implied correction, no explicit "不要")
- "可以，但感覺不對" (weak feedback, regex won't catch)
- "你有沒有想過用 X 來做？" (suggestion/preference)

When you spot these → call `agent.add_signal(text, dialog_type, context)` to add the signal.
This bypasses regex and directly adds to the pool.

**Either track → signal enters pool. Both can fire for the same message (dedup in Python).**

### 2. Signal Classification

Before each response, check `agent.should_classify_now()`. When it returns True (pool >= 3 signals, or 5+ messages accumulated):

1. Call `agent.get_pending_signals()` to read unclassified signals
2. For each signal, classify its **dialog_type**:
   - `correction`: User is correcting something you did (style, approach, output)
   - `pre_instruction`: User is giving direction before you act
   - `feedback`: User is confirming or rejecting
3. **Semantically group** signals that are about the same underlying preference — even if they use different words:
   - "不要硬編碼" + "不要只修一個" + "不要治標不治本" → same group: "fix systemically"
   - "不要用 camelCase" + "用 snake_case，不要 camelCase" → same group: "use snake_case"
4. For each group, extract a structured Memory:
   ```json
   {
     "rule_content": "Clear, actionable rule",
     "type": "preference | rule | workflow | method",
     "scope": "global | workspace | repo | directory",
     "scope_value": "path or project name (empty for global)",
     "condition": "IF [context] THEN [action]",
     "principle": "What does this reveal about the user?",
     "confidence": 40,
     "related_signal_ids": ["sig-1", "sig-2"]
   }
   ```
5. Call `agent.classify_and_save(signal_id, classification)` for each group
6. Remove classified signals from the pool

### 3. Semantic Judgment (You, Claude Code)

**Regex is a thin first pass.** It catches obvious patterns ("不要X") but misses most real language. YOU are the primary intelligence. Use full conversation context to judge what the user actually means.

**Intent vs. Words:**

| User says | Context | Actual meaning | Action |
|-----------|---------|---------------|--------|
| "先這樣做" | After 3 rounds of corrections, user sounds tired | Compromise. Not a real preference. | Do NOT learn. |
| "先這樣做" | Quick affirmative after you proposed a solution | Positive confirmation | Reinforce +10 |
| "先這樣做" | Tentative, with "之後再看看" | Conditional accept | Learn but confidence +5 only |
| "OK" | After you nailed the output | Genuine positive feedback | Reinforce |
| "OK" | Flat tone, after mediocre output | Polite dismissal | Do NOT learn |
| "都可以" | User doesn't care | Not a preference | Do NOT learn |
| "你決定" | User trusts your judgment | Workflow preference: delegate to AI | Learn as workflow |

**Key principles:**
- **Tone > Text.** If the user sounds tired, frustrated, or dismissive, that overrides the literal words.
- **Consistency > Single occurrence.** One "OK" is noise. Three "OK"s in similar contexts is a pattern.
- **When uncertain, ask.** A 5-word clarification is cheaper than learning a wrong preference.
- **Context is everything.** The same sentence in different conversations can mean opposite things.
- **Compromise is NOT preference.** If the user settled, don't learn it.

### 4. Confidence & Confirmation

- **Confidence 40-79 (mature):** Ask a lightweight PS question before your next response.
  > "PS: 我注意到[observation]，以後[action]好嗎？"
  - User says yes → upgrade to 80 (rule), silent from now on
  - User says no → downgrade to 10 (raw)
  - User qualifies ("只在這個專案") → update scope, upgrade to 80
  - User ignores → keep at current level, ask once more next time

- **Confidence 80+ (rule):** Silently apply. Never ask again.

- **Red-line signals** (user said "绝对不要"): start at confidence 60. No PS question needed — user was emphatic enough.

### 5. Application (JIT Injection)

Before each task, Python calls `agent.get_jit_memories(project, directory, file_extension)`.
This returns the **top 5** most relevant rule-level (confidence >= 80) memories matched by scope.
Inject them into your system prompt silently. Do not mention them to the user.

### 6. Memory Lifecycle

- **Decay**: If a mature memory isn't triggered for 3 consecutive related tasks → degrade. If a rule memory isn't triggered for 5 → degrade to mature.
- **Conflict**: When a new memory contradicts an old one, you decide: is it a real conflict (deprecate old) or scope difference (keep both)?
- **User control**: User can always call `python scripts/view_memory.py` to see what's stored, and `edit|delete` to modify.

### 7. Learning Pulse

Python provides periodic status so the user knows the skill is alive:
- Session start: "歡迎回來。上次學到 N 條偏好，M 條已自動套用。"
- Rule upgrade: "PS: 新規則已成熟：[rule]。"
- Milestone: "目前共 N 條偏好。你最近很少有重複糾正了。"

### 8. Non-Goals

- Does NOT enforce security rules
- Does NOT inject more than 5 memories at once
- Does NOT modify CLAUDE.md without user confirmation
- Does NOT call any external API — you (Claude Code) are the only intelligence
