# 实验：从日志到档案（Journal → Profile）

## 实验假设

日常运营日志（Journal）中蕴含选题、观点、方法论等可复用内容，但目前散落在时间流中，没有被系统性地提取到新媒体档案（Profile）中。

**假设**：通过一个受控的提取-转换流程，可以从日志中持续产出结构化选题和素材，补充到档案中，使内容生产的"原料"供给更加稳定、可追溯。

## 范围限定

| 维度 | 限定 |
|------|------|
| 输入 | `data/journal/default/` — 默认工作流的每日日志 |
| 输出 | `data/profile/topics/` — 选题清单（首批）<br>`data/profile/contents/` — 内容初稿（后续阶段） |
| 处理域 | **仅在 `examples/default/lab/` 内部** |
| 跨域原则 | 需要的数据**复制**进来，产出的结果**复制**出去，不跨子模块直接写 |

## 数据流

```
                        实验室边界
                    ┌──────────────────────┐
 journal/ ──copy──▶ │  lab/inputs/         │
 （子模块，只读）     │  （原始日志副本）      │
                    │                      │
                    │  lab/scripts/        │
                    │  （提取→转换→组装）    │
                    │         │            │
                    │         ▼            │
                    │  lab/outputs/        │
                    │  （结构化工件）        │
                    └────────┬─────────────┘
                             │ review
                             ▼
 profile/ ◀──sync── 人工确认后复制过去
 （子模块）
```

## 工件设计

### 输入（`lab/inputs/`）

从 `data/journal/default/` 复制 `*.md`，保持文件名不变。

### 中间件（`lab/outputs/`）

每次运行产出一个带时间戳的目录：

```
outputs/YYYY-MM-DD-HHMM/
├── provenance.json         # 本次处理了哪些输入文件、处理时间
├── topics/                 # 提取的选题
│   ├── raw.jsonl           # 逐条提取结果：来源文件、行号、类型、摘要
│   └── grouped.md          # 按主题归并后的选题清单（可供人工复用到 profile/topics/）
├── drafts/                 # 内容草稿（后续阶段）
│   └── ...
└── report.md              # 摘要报告：新增/更新了哪些条目
```

### 选题条目格式

每条选题记录以下字段：

```
- 来源: journal/default/2026-07-08.md
- 类型: topic | insight | methodology | case
- 标题: <标题>
- 摘要: <一句话摘要>
- 状态: draft | reviewed | copied
```

## 实验步骤

### 阶段一：手动跑通链路（当前）

1. 手工复制一篇日志到 `lab/inputs/`
2. 手工阅读，提取选题，写入 `lab/outputs/`
3. 手工复制结果到 `data/profile/topics/`
4. 记录耗时和问题

**判断标准**：一个完整闭环跑通，记录下环节问题。

## 阶段二：LLM 驱动提取（当前）

1. `lab/scripts/extract_llm.py` 使用 `quanttide_agent.LLM` 语义理解日志内容
2. 每条输出包含结构化标题和摘要（`title` + `summary`），而非原始文本片段
3. 相比关键词匹配，召回率更高（18 → 25 条/2篇）、噪声更低
4. 自动降级：若 `quanttide_agent` 不可用，回退到关键词匹配

**判断标准**：提取质量明显优于关键词匹配，无需人工二次整理即可直接用于选题规划。

### 阶段三：持续运行

1. 标准流程固化：`fetch → extract → review → sync`
2. 每次写完日志后运行一次
3. 积累运行记录到 `lab/outputs/`

**判断标准**：连续运行 10 次无人工干预故障。

## 文件清单

```
examples/default/lab/
├── inputs/            # 复制的日志（.gitignore 排除）
├── outputs/           # 产物（.gitignore 排除）
├── scripts/
├── fetch.py       # 复制 journal 默认工作流的增量日志
├── extract.py      # LLM 驱动提取（使用 quanttide_agent.LLM）
├── sync.py        # 展示待同步到 profile 的变更
├── .gitignore         # 排除 inputs/ outputs/
└── README.md          # 实验操作说明
```

## 约束

1. 不修改 `data/journal/` 和 `data/profile/` 子模块中的任何文件。
2. 如果需要修改，通过 PR 或手动复制进行，不在实验流程中自动写入。
3. 每次实验运行应可重复、可追溯。
4. 实验产物的格式应能被人工直接审阅（Markdown / JSONL）。

## 已有案例验证

`data/profile/topics/articles/qtdata.md` 是一个已成功的手动闭环：

```
journal/default/2026-07-08.md
  ── 提取 "数据脱敏方法论"、"洗过最脏的数据" 等 5 个选题
  ── 写入 profile/topics/articles/qtdata.md
  ── 标记来源引用
```

证明该链路是有价值的，实验的目标是将它从"偶然手动"变为"可重复流程"。
