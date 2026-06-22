#!/usr/bin/env python3
"""Extract and apply CodeRabbit suggested diffs from review threads."""
import json
import os
import re
import sys


def extract_diff_blocks(body: str) -> list[str]:
    """Extract ```diff ... ``` blocks from comment body."""
    return re.findall(r"```diff\n(.*?)```", body, re.DOTALL)


def parse_diff_lines(diff_text: str):
    """Return (old_lines, new_lines) from a diff block."""
    old_lines = []
    new_lines = []
    for line in diff_text.split("\n"):
        if line.startswith("-") and not line.startswith("---"):
            old_lines.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            new_lines.append(line[1:])
    return old_lines, new_lines


def find_file(path: str) -> str | None:
    """Resolve file path, trying common prefixes."""
    if os.path.exists(path):
        return path
    for prefix in ["", "dashboard/", "src/"]:
        candidate = prefix + path
        if os.path.exists(candidate):
            return candidate
    return None


def apply_edit(content: str, old_text: str, new_text: str) -> str | None:
    """Try to replace old_text with new_text in content."""
    if old_text in content:
        return content.replace(old_text, new_text, 1)
    # Fallback: normalize whitespace, match line by line
    old_stripped = old_text.strip()
    content_lines = content.split("\n")
    for i, line in enumerate(content_lines):
        if line.strip() == old_stripped:
            content_lines[i] = new_text
            return "\n".join(content_lines)
    return None


def main():
    try:
        threads = json.load(sys.stdin)
    except json.JSONDecodeError:
        threads = []

    changed_files: set[str] = set()

    for t in threads:
        body = t.get("body", "")
        path = t.get("path", "")
        tid = t.get("id", "")

        if "🏁 Script executed" in body or "Analysis chain" in body:
            continue
        if "```diff" not in body:
            continue

        diffs = extract_diff_blocks(body)
        if not diffs:
            continue

        resolved_path = find_file(path)
        if not resolved_path:
            print(f"SKIP|{tid}|File not found: {path}")
            continue

        with open(resolved_path, "r") as f:
            content = f.read()
        original = content

        for diff_text in diffs:
            old_lines, new_lines = parse_diff_lines(diff_text)
            if not old_lines or not new_lines:
                continue

            old_text = "\n".join(old_lines)
            new_text = "\n".join(new_lines)
            result = apply_edit(content, old_text, new_text)

            if result is not None:
                content = result
            else:
                # Try one line at a time (simple find-and-replace per line pair)
                for ol, nl in zip(old_lines, new_lines):
                    r = apply_edit(content, ol, nl)
                    if r is not None:
                        content = r

        if content != original:
            with open(resolved_path, "w") as f:
                f.write(content)
            changed_files.add(resolved_path)
            print(f"APPLIED|{tid}|{resolved_path}")
        else:
            print(f"SKIP|{tid}|No changes needed in {resolved_path}")

    if changed_files:
        print(f"CHANGED|{'|'.join(sorted(changed_files))}")


if __name__ == "__main__":
    main()
