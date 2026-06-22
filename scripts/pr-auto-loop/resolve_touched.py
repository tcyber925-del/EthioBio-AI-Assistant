#!/usr/bin/env python3
"""Filter unresolved threads to those touching changed files."""
import json
import sys


def main():
    all_changed = sys.argv[1].split("\n") if len(sys.argv) > 1 else []
    changed_set = set(f.strip() for f in all_changed if f.strip())

    try:
        threads = json.load(sys.stdin)
    except json.JSONDecodeError:
        threads = []

    for t in threads:
        path = t.get("path", "")
        tid = t.get("id", "")
        body = t.get("body", "")
        if "🏁 Script executed" in body or "Analysis chain" in body:
            continue
        if path in changed_set:
            print(f"RESOLVE|{tid}|{path}")


if __name__ == "__main__":
    main()
