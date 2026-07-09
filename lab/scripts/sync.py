#!/usr/bin/env python3
"""sync.py — 展示待同步到 profile 的变更

用法: python3 sync.py
  展示最新提取结果和目标目录，提供同步指引。
"""

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent.parent.parent
LAB = ROOT / "examples" / "default" / "lab"
OUTPUTS = LAB / "outputs"
PROFILE_TOPICS = ROOT / "data" / "profile" / "topics"


def main():
    # 找最新一次运行
    runs = sorted(OUTPUTS.iterdir()) if OUTPUTS.exists() else []
    if not runs:
        print("no outputs found — run extract.py first", file=sys.stderr)
        return

    latest = runs[-1]
    print(f"=== 最新实验运行: {latest.name} ===")
    print()

    grouped = latest / "topics" / "grouped.md"
    if grouped.exists():
        print("--- 提取结果 ---")
        print(grouped.read_text(encoding="utf-8"))
        print()

    print("--- 目标目录: profile/topics/ ---")
    print("已有选题文件:")
    for d in ["articles", "notes"]:
        for f in sorted((PROFILE_TOPICS / d).glob("*.md")):
            print(f"  {d}/{f.name}")

    print()
    print("--- 同步指引 ---")
    print(f"1. 审阅 {grouped}")
    print("2. 将确认的条目手动复制到 data/profile/topics/ 下")
    print("3. 在分组文件中添加来源引用")
    print()
    print("也可直接运行:")
    print(f"  cp {grouped} {PROFILE_TOPICS}/articles/  # 或 notes/")
    print("  然后编辑调整")


if __name__ == "__main__":
    main()
