#!/usr/bin/env python3
"""Replay real Claude Code session through agent — measure signal capture rate."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.agent import Agent

BASE = os.path.expanduser("~/.claude/projects/-Users-kun/")


def replay_session(session_file: str, batch_classify_every: int = 20) -> dict:
    """Replay all user messages through the agent.

    After every N messages, call classify_all_pending_local() to simulate
    Claude Code periodically classifying signals (in production, Claude Code
    does this with full semantic understanding).
    """
    agent = Agent()
    agent.store.clear()

    stats = {
        "total_user_messages": 0,
        "corrections_captured": 0,
        "batch_classifications": 0,
        "memories_created": 0,
        "pulse_events": [],
    }

    msg_count = 0
    with open(session_file) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: d = json.loads(line)
            except: continue
            if d.get("type") != "user": continue

            msg = d.get("message", {})
            content = msg.get("content", "")
            if isinstance(content, list):
                text = " ".join(b.get("text","") for b in content if isinstance(b, dict) and b.get("type")=="text")
            else:
                text = str(content)

            stats["total_user_messages"] += 1
            msg_count += 1

            if len(text) < 2000:
                r = agent.process_dialog(text, {"project": "replay", "directory": "src"})
                if r.get("phase") == "observed":
                    stats["corrections_captured"] += 1

            # Periodic batch classification (simulates Claude Code reading SKILL.md)
            if msg_count % batch_classify_every == 0:
                before = len(agent.store.list_memories())
                agent.classify_all_pending_local()
                after = len(agent.store.list_memories())
                if after > before:
                    stats["batch_classifications"] += 1

    # Final classification pass
    agent.classify_all_pending_local()

    stats["memories_created"] = len(agent.store.list_memories())
    rules = [m for m in agent.store.list_memories() if m.confidence >= 80]
    stats["rules"] = len(rules)
    stats["active"] = len([m for m in agent.store.list_memories() if m.state == "active"])

    # Pulse
    pulse = agent.get_pulse()
    if pulse:
        stats["pulse_events"].append(pulse)

    return stats


def main():
    # Find large sessions
    candidates = []
    for fname in os.listdir(BASE):
        if fname.endswith('.jsonl'):
            fpath = os.path.join(BASE, fname)
            size_mb = os.path.getsize(fpath) / (1024*1024)
            if size_mb > 5:
                candidates.append((size_mb, fpath))
    candidates.sort(reverse=True)

    # Walk-forward: first 3 calibrate, last 2 blind
    test_sessions = candidates[:5]

    print("=" * 65)
    print("  WALK-FORWARD CROSS-VALIDATION")
    print("  Calibration: 3 sessions | Blind: 2 sessions")
    print("=" * 65)

    print(f"\n{'Session':<12} {'Size':>6} {'Msgs':>6} {'Corr':>6} {'Mems':>6} {'Rules':>6}")
    print("-" * 55)

    calib_rules = []
    for size_mb, fpath in test_sessions[:3]:
        stats = replay_session(fpath)
        calib_rules.append(stats["rules"])
        print(f"{os.path.basename(fpath)[:8]:<12} {size_mb:>5.0f}M {stats['total_user_messages']:>6} {stats['corrections_captured']:>6} {stats['memories_created']:>6} {stats['rules']:>6}")

    print("  --- blind ---")
    blind_rules = []
    for size_mb, fpath in test_sessions[3:5]:
        stats = replay_session(fpath)
        blind_rules.append(stats["rules"])
        print(f"{os.path.basename(fpath)[:8]:<12} {size_mb:>5.0f}M {stats['total_user_messages']:>6} {stats['corrections_captured']:>6} {stats['memories_created']:>6} {stats['rules']:>6}")

    calib_avg = sum(calib_rules) / max(1, len(calib_rules))
    blind_avg = sum(blind_rules) / max(1, len(blind_rules))
    print(f"\n  Calibration avg rules: {calib_avg:.1f}")
    print(f"  Blind test avg rules: {blind_avg:.1f}")
    if calib_avg and blind_avg:
        ratio = min(calib_avg, blind_avg) / max(calib_avg, blind_avg)
        print(f"  Consistency: {ratio:.0%} {'✓' if ratio > 0.3 else '✗ overfit'}")

    for event in stats.get("pulse_events", []):
        print(f"  🫀 {event['message']}")


if __name__ == "__main__":
    main()
