"""Extract Bioicons SVGs from the local clone into data/icons/ organized by category."""

import subprocess
import sys
from pathlib import Path

BIOICONS_DIR = Path("/tmp/bioicons")
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "icons"


def main():
    if not BIOICONS_DIR.exists():
        print("Bioicons clone not found at /tmp/bioicons. Clone it first:")
        print("  git clone --depth 1 --filter=blob:none --sparse https://github.com/duerrsimon/bioicons.git /tmp/bioicons")
        sys.exit(1)

    result = subprocess.run(
        ["git", "ls-tree", "-r", "HEAD", "--name-only", "--", "static/icons/"],
        capture_output=True, text=True, cwd=BIOICONS_DIR,
    )
    svgs = [l for l in result.stdout.strip().split("\n") if l.endswith(".svg")]
    print(f"Found {len(svgs)} SVGs in bioicons repo")

    extracted = 0
    for svg_path in svgs:
        parts = svg_path.split("/")
        category = parts[3]
        filename = parts[-1]

        cat_dir = OUTPUT_DIR / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        target = cat_dir / filename
        if target.exists():
            continue

        content = subprocess.run(
            ["git", "show", f"HEAD:{svg_path}"],
            capture_output=True, text=True, cwd=BIOICONS_DIR,
        )
        if content.returncode == 0 and content.stdout.strip():
            target.write_text(content.stdout)
            extracted += 1

    print(f"Extracted {extracted} new SVGs to {OUTPUT_DIR}")
    total = sum(1 for _ in OUTPUT_DIR.rglob("*.svg"))
    print(f"Total SVGs in {OUTPUT_DIR}: {total}")


if __name__ == "__main__":
    main()
