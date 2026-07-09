#!/usr/bin/env python3
"""fetch.py — 复制 journal 日志到 lab/inputs/

用法: python3 fetch.py [日期]
  不传日期: 复制所有 inputs/ 中没有的日志
  传日期:   仅复制指定日期 (YYYY-MM-DD)
"""

import shutil
import sys
from pathlib import Path

# 脚本位于 examples/default/lab/scripts/fetch.py
# 项目根需上溯 4 层: scripts/ → lab/ → default/ → examples/ → quanttide-media/
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent.parent.parent
LAB = ROOT / "examples" / "default" / "lab"
INPUTS = LAB / "inputs"
JOURNAL = ROOT / "data" / "journal" / "default"


def main():
    INPUTS.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) >= 2:
        date = sys.argv[1]
        src = JOURNAL / f"{date}.md"
        if src.exists():
            shutil.copy2(src, INPUTS / src.name)
            print(f"copied: {src.name}")
        else:
            print(f"not found: {src.name}", file=sys.stderr)
            sys.exit(1)
    else:
        count = 0
        for f in sorted(JOURNAL.glob("*.md")):
            dst = INPUTS / f.name
            if not dst.exists():
                shutil.copy2(f, dst)
                print(f"copied: {f.name}")
                count += 1
        print(f"done: {count} file(s) copied")


if __name__ == "__main__":
    main()
