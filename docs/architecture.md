# Architecture: Self-Growing Memory Agent

## 1. Design Goals

Build a coding assistant whose memory grows and shrinks with the user — not a static preference store.

Key principles:

1. **Extract, don't just store** — raw conversation is not memory. The system must classify feedback into structured memories.
2. **Decay, don't just accumulate** — memories that no longer serve the user should fade, not pile up.
3. **Transparency always** — every memory is inspectable, explainable, and user-controllable.

## 2. Component Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      User Interface                       │
│              (CLI / MCP Client / Web Chat)                │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│                   MemoryAgent (agent.py)                  │
│                                                           │
│  chat(user_msg) → inject → LLM → extract → arbitrate     │
│                            │                              │
│                     ┌──────▼──────┐                       │
│                     │  Decay      │                       │
│                     │  Scanner    │                       │
│                     └─────────────┘                       │
└──────────────────────┬───────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐
│  Extractor   │ │ Arbitrator│ │ Injector  │
│  (LLM)       │ │           │ │           │
│              │ │ scope-    │ │ semantic  │
│  classifies  │ │ graded    │ │ search +  │
│  feedback    │ │ conflict  │ │ prompt    │
│  → Memory    │ │ resolve   │ │ injection │
└──────┬───────┘ └─────┬─────┘ └─────┬─────┘
       │               │             │
┌──────▼───────────────▼─────────────▼─────┐
│              MemoryStore (store.py)       │
│                                            │
│  In-memory list ←→ Mem0 (vector storage)  │
│  + Qdrant (local) + Ollama (embeddings)   │
└────────────────────────────────────────────┘
```

## 3. Data Flow

### 3.1 Main Chat Flow

```
User message
    │
    ▼
[Injector] Search Mem0 for relevant memories
    │
    ▼
[Agent] Build system prompt with memory block
    │
    ▼
[LLM] Generate response (with memory guidance)
    │
    ▼
[Extractor] Analyze user message — is this feedback?
    │
    ├── NO (temporary task) → skip extraction
    │
    └── YES → extract structured memories as JSON
            │
            ▼
        [Arbitrator] Check conflicts with existing memories
            │
            ├── conflict detected → resolve by scope/priority
            │
            └── no conflict → add to memory list
                    │
                    ▼
                [Mem0] Store in vector DB
```

### 3.2 Decay Flow

```
After every chat turn:
    │
    ▼
[Decay Scanner] For each auto_decay=true memory:
    │
    ├── user asked "why" on matching topic → reinforce (score=100)
    │
    ├── user didn't mention this topic → decay (score -= 20)
    │
    └── score reached 0 → auto-deprecated
```

## 4. Key Design Decisions

### 4.1 Mem0 as storage only, not extraction

Mem0's native `add()` does opaque LLM extraction. We bypass it entirely. We use Mem0 only for vector storage and semantic search. All extraction and classification is done by our own LLM prompt with a structured JSON output contract.

### 4.2 Scope-graded conflict resolution

Simple "new overwrites old" breaks when users make narrow exceptions. Example:
- User says "no `any` type" (global preference)
- User says "this function can use `any`" (file-level exception)

Our arbitrator keeps both: the global preference stays active, and the file exception coexists as a narrower-scope rule.

### 4.3 Topic-keyed decay

Early versions reinforced ALL decay memories when ANY "why" was asked. This was wrong — asking about React shouldn't prevent TypeScript guidance from decaying.

Current version: each decay memory has a `decay_topic`. Only memories whose topic matches the user's current question are reinforced. Unrelated topics continue decaying independently.

### 4.4 One store, two memory behaviors

We deliberately keep permanent (preference/rule) and decaying (method) memories in the same store rather than splitting into two databases. This makes the system simpler to inspect, test, and explain to judges.

## 5. Evaluation

The 8-step test protocol maps directly to WASC's 6 scoring dimensions:

| Step | Action | Dimension Tested |
|------|--------|-----------------|
| 1 | Reset all memories | Reproducibility |
| 2 | First coding task | Baseline |
| 3 | User gives preferences | Memory extraction |
| 4 | View memories | Transparency |
| 5 | Cross-scenario task | Memory application |
| 6 | Preference change | Update & eviction |
| 7 | Third task (verify new rule) | Update + Quality |
| 8 | Delete + re-test | Reproducibility |

The test harness produces a predicted score with judge commentary for each step, making it possible to iterate quickly without manual testing.

## 6. Limitations

- Single-user memory model (no shared/team memory)
- Mem0 internal LLM calls may fail with region-restricted API keys (non-blocking: our extractor handles all classification)
- Embeddings require local Ollama (could be replaced with API-based embeddings for easier setup)
