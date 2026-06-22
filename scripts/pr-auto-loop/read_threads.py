#!/usr/bin/env python3
import json
import sys

try:
    threads = json.load(sys.stdin)
except json.JSONDecodeError:
    threads = []

has_auto = False
by_option = False

for t in threads:
    body = t.get("body", "")
    path = t.get("path", "?")
    tid = t.get("id", "")
    has_diff = "```diff" in body

    if "🏁 Script executed" in body or "Analysis chain" in body:
        print(f"  \U0001f4cb {path}  (analysis chain)")
        continue

    sev = "\U0001f534" if "Critical" in body else "\U0001f7e0" if "Major" in body else "\U0001f7e1"
    summary = body[:100].replace("\n", " ").replace("```", "")
    label = " [auto-fixable]" if has_diff else ""
    print(f"  {sev} {path}{label}  |  {summary}")
    if has_diff:
        has_auto = True

print()
if has_auto:
    print("  \u26a1 Some threads have suggested diffs. Run: pr-review-loop auto")
