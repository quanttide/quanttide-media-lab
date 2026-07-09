#!/usr/bin/env python3
"""从日志中提取候选条目 — LLM 驱动版

用法: python3 extract.py
  从 lab/inputs/ 读取 .md 文件，输出到 lab/outputs/<timestamp>/
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from quanttide_agent import LLM, Message

# ── 路径 ───────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent.parent.parent
LAB = ROOT / "examples" / "default" / "lab"
INPUTS = LAB / "inputs"
OUTPUTS = LAB / "outputs"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d-%H%M")
RUN_DIR = OUTPUTS / TIMESTAMP


# ── 业务域定义 ────────────────────────────────────────
# 与 data/profile/topics/articles/README.md 保持一致
DOMAINS = {
    "default": "未分类，暂不属于任何业务域",
    "qtdata": "量潮数据 — 数据处理、数据清洗、大数据分析、数据脱敏、数据工程",
    "qtclass": "量潮课堂 — 教育培训、课程、训练营、人才培养、教学案例",
    "qtcloud": "量潮云 — 云平台、工具建设、第二大脑、AI客户端、效率工具",
    "qtconsult": "量潮咨询 — 创业咨询、创新咨询、企业治理、管理方法、服务模式",
}
DOMAIN_DOC = "".join(f"  - **{k}**：{v}\n" for k, v in DOMAINS.items())


# ── Prompt ─────────────────────────────────────────────
SYSTEM_PROMPT = f"""你是一个新媒体运营分析助手。分析运营日志，提取可用于内容创作的素材。

## 提取类别

- **topic**（选题）：可直接写作的文章选题
- **insight**（洞察）：有价值的观点、发现、观察
- **methodology**（方法论）：可复用的方法、原则、步骤、流程
- **case**（案例）：可引用的具体案例或例子

## 业务域

每个条目需归入以下业务域之一：
{DOMAIN_DOC}

## 输出格式

每行一个 JSON 对象（JSONL）：
{{"type": "<类别>", "domain": "<业务域>", "title": "简短标题", "summary": "一句话摘要，保留原始细节和上下文"}}

只输出 JSONL，不要有其他文字。如果日志中没有可提取的内容，输出空行。"""


# ── 分类器（纯逻辑 fallback）──────────────────────────
# 当 LLM 未输出 domain 字段时，用关键词猜测
KEYWORD_DOMAIN_MAP = [
    (["数据", "脱敏", "清洗", "TB", "音视频", "音量", "大数据"], "qtdata"),
    (["课堂", "教学", "培训", "课程", "训练营", "培养", "学生", "教"], "qtclass"),
    (["云", "第二大脑", "AI", "客户端", "工具", "git", "平台"], "qtcloud"),
    (["咨询", "创业", "创新", "治理", "管理", "服务", "客户", "商务"], "qtconsult"),
]


def extract_items(filepath: Path, llm: LLM) -> list[dict]:
    """用 LLM 从一篇日志中提取条目"""
    text = filepath.read_text(encoding="utf-8").strip()
    if not text:
        return []

    resp = llm.complete(
        [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=f"请分析这篇日志：\n\n{text}"),
        ],
        model=None,  # 使用 LLM 初始化时指定的模型
        temperature=0.1,
        max_tokens=2048,
    )

    items = []
    for line in resp.content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
            if "type" in item and "title" in item:
                # fallback: LLM 没给 domain 时用关键词猜
                if "domain" not in item or item["domain"] not in DOMAINS:
                    item["domain"] = _classify(
                        item["title"] + " " + item.get("summary", "")
                    )
                items.append(item)
        except json.JSONDecodeError:
            continue
    return items


def _classify(text: str) -> str:
    """关键词 fallback 分类器"""
    for keywords, domain in KEYWORD_DOMAIN_MAP:
        for kw in keywords:
            if kw in text:
                return domain
    return "default"


def main():
    # ── 初始化 LLM ──────────────────────────────────
    llm = LLM()

    # 也可从环境变量覆盖
    if os.environ.get("QT_LLM_MODEL"):
        llm = LLM(model=os.environ["QT_LLM_MODEL"])

    # ── 遍历 inputs/ ────────────────────────────────
    md_files = sorted(INPUTS.glob("*.md"))
    if not md_files:
        print("no input files found", file=sys.stderr)
        sys.exit(1)

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RUN_DIR / "topics" / "raw.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    all_items: list[dict] = []
    for f in md_files:
        print(f"  processing: {f.name}")
        items = extract_items(f, llm)
        for item in items:
            item["source"] = f.name
            all_items.append(item)

    # ── 写入 raw.jsonl ───────────────────────────────
    with open(raw_path, "w", encoding="utf-8") as f:
        for item in all_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"  extracted: {len(all_items)} item(s)")

    # ── 生成 grouped.md ─────────────────────────────
    grouped = raw_path.with_name("grouped.md")
    type_order = ["topic", "insight", "methodology", "case", "task"]
    domain_order = ["default", "qtdata", "qtclass", "qtcloud", "qtconsult"]
    domain_label = {k: v.split(" — ")[0] for k, v in DOMAINS.items()}

    with open(grouped, "w", encoding="utf-8") as f:
        f.write(f"# 提取报告 — {TIMESTAMP}\n\n")
        f.write(f"来源: {' '.join(f.name for f in md_files)}\n\n---\n")

        for t in type_order:
            items = [i for i in all_items if i["type"] == t]
            if not items:
                continue
            f.write(f"\n## {t} ({len(items)})\n\n")

            # 按业务域分组
            for d in domain_order:
                dom_items = [i for i in items if i.get("domain", "default") == d]
                if not dom_items:
                    continue
                label = domain_label.get(d, d)
                f.write(f"### {label}\n\n")
                for item in dom_items:
                    f.write(
                        f"- **{item['title']}** — {item['summary']}（{item['source']}）\n"
                    )
                f.write("\n")

        f.write("---\n")
        f.write(f"_共 {len(all_items)} 条候选，人工筛选后复制到 profile/topics/_")

    print(f"  report: {grouped}")
    print(f"done: {RUN_DIR}")


if __name__ == "__main__":
    main()
