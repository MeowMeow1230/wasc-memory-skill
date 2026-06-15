#!/usr/bin/env python3
"""Scan session history for repeated correction patterns — candidate test data for replay."""
import json, os, re
from collections import defaultdict

BASE = os.path.expanduser("~/.claude/projects/-Users-kun/")
CORRECTION_RE = re.compile(r'(不要|别|別|应该|你又忘了|不對|不对|错了|錯了|先不要|不急|別急|等一下|看一下再|討論一下)')


def extract_user_messages(filepath: str) -> list[str]:
    msgs = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("type") != "user":
                continue
            msg = d.get("message")
            if msg is None:
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                text = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
            else:
                text = str(content)
            if len(text) < 200 and CORRECTION_RE.search(text):
                msgs.append(text.strip())
    return msgs


def find_repeated_patterns(messages: list[str]) -> list[tuple[str, int, list[int]]]:
    groups = defaultdict(list)
    for i, msg in enumerate(messages):
        for phrase in re.findall(r'(?:不要|别|先不要|你又忘了|不對|不急|等一下|討論一下)\s*\S+', msg):
            key = phrase.strip()
            groups[key].append(i)
    return [(phrase, len(idxs), idxs) for phrase, idxs in groups.items() if len(idxs) >= 3]


def main():
    print("Scanning session history for repeated corrections...\n")
    results = []
    for fname in sorted(os.listdir(BASE)):
        if not fname.endswith('.jsonl'):
            continue
        fpath = os.path.join(BASE, fname)
        size_mb = os.path.getsize(fpath) / (1024 * 1024)
        if size_mb < 1:
            continue

        msgs = extract_user_messages(fpath)
        patterns = find_repeated_patterns(msgs)
        if patterns:
            results.append((fname, size_mb, len(msgs), patterns))

    results.sort(key=lambda x: sum(p[1] for p in x[3]), reverse=True)
    for fname, size_mb, total, patterns in results[:10]:
        print(f"Session: {fname[:8]}... ({size_mb:.0f}MB, {total} corrections)")
        for phrase, count, idxs in patterns[:5]:
            print(f"  [{count}x] \"{phrase}\" at positions {idxs[:5]}...")
        print()


if __name__ == "__main__":
    main()
