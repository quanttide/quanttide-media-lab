# 程序逻辑

## 概述

三个脚本构成一个从**日志（Journal）**到**档案（Profile）**的提取管道：

```
fetch.py  →  extract.py  →  sync.py
 复制数据      LLM 提取     预览结果
```

数据仅在 `lab/` 目录内流转，不直接写入外部的子模块。

---

## fetch.py — 数据复制

### 职责

将 `data/journal/default/` 中的 Markdown 日志文件复制到 `lab/inputs/`。

### 逻辑

```
journal/default/        lab/inputs/
  2026-07-08.md  ───▶   2026-07-08.md
  2026-07-09.md  ───▶   2026-07-09.md
```

- **增量模式**（无参数）：遍历日志目录，只复制 `inputs/` 中不存在的文件
- **指定日期**（`python3 fetch.py 2026-07-08`）：复制单篇日志
- 使用 `shutil.copy2` 保留文件元数据
- **不修改日志源文件**

### 路径

```
脚本位置: examples/default/lab/scripts/fetch.py
项目根:   ../../.. (4 层上溯)
```

---

## extract.py — LLM 提取 + 分类

### 依赖

- `quanttide_agent` (v0.4.0)
  - `LLM` — LLM 客户端，自动读取环境/配置中的 `LLM_API_KEY`
  - `Message` — 对话消息结构（role/content）

### 逻辑

```
inputs/*.md  ──▶  LLM  ──▶  outputs/<timestamp>/topics/
                              ├── raw.jsonl     (逐条结构化数据)
                              └── grouped.md    (按类型+业务域归并的报告)
```

### 处理流程

1. **遍历** `inputs/` 下所有 `.md` 文件
2. **构造 Prompt**：
   - `system`：定义角色、提取类别、业务域、输出格式
   - `user`：日志全文
3. **调用 LLM**：`llm.complete(messages=[...], temperature=0.1, max_tokens=2048)`
4. **解析响应**：逐行解析 JSON，验证必要字段
5. **分类 fallback**：LLM 未输出 `domain` 或输出非法值时，用关键词猜测
6. **写入输出**：
   - `raw.jsonl` — 每行一个条目，含 `type` / `domain` / `title` / `summary` / `source`
   - `grouped.md` — 先按 type 分组，每组内按业务域分组

### 业务域分类

与 `data/profile/topics/articles/README.md` 保持一致：

| 域 | 名称 | 覆盖内容 |
|----|------|----------|
| `default` | 未分类 | 暂不属于任何业务域 |
| `qtdata` | 量潮数据 | 数据处理、清洗、大数据、脱敏、数据工程 |
| `qtclass` | 量潮课堂 | 教育培训、课程、训练营、人才培养 |
| `qtcloud` | 量潮云 | 云平台、第二大脑、AI 客户端、效率工具 |
| `qtconsult` | 量潮咨询 | 创业咨询、创新咨询、企业治理、管理方法 |

分类器有两层：

1. **LLM 语义分类**（主）：在 Prompt 中要求 LLM 输出 `domain` 字段，LLM 根据全文语义判断匹配的业务域
2. **关键词 fallback**（备用）：当 LLM 未输出有效 domain 时，用 `_classify()` 函数根据标题+摘要中的关键词猜测

```python
KEYWORD_DOMAIN_MAP = [
    (["数据", "脱敏", "清洗", "TB", "音视频", "大数据"], "qtdata"),
    (["课堂", "教学", "培训", "课程", "训练营", "教"], "qtclass"),
    (["云", "第二大脑", "AI", "客户端", "工具", "平台"], "qtcloud"),
    (["咨询", "创业", "创新", "治理", "管理", "服务", "客户", "商务"], "qtconsult"),
]

def _classify(text: str) -> str:
    for keywords, domain in KEYWORD_DOMAIN_MAP:
        for kw in keywords:
            if kw in text:
                return domain
    return "default"
```

### Prompt 设计

```
"你是一个新媒体运营分析助手。分析运营日志，提取可用于内容创作的素材。

## 提取类别
- topic（选题）：可直接写作的文章选题
- insight（洞察）：有价值的观点、发现
- methodology（方法论）：可复用的方法、原则、步骤
- case（案例）：可引用的具体案例

## 业务域
每个条目需归入以下业务域之一：
  - default：未分类
  - qtdata：量潮数据 — ...
  - qtclass：量潮课堂 — ...
  - qtcloud：量潮云 — ...
  - qtconsult：量潮咨询 — ...

## 输出格式
每行 JSON：{"type": "<类别>", "domain": "<业务域>", "title": "<标题>", "summary": "<摘要>"}"
```

- `temperature=0.1`：低随机性，保证提取的一致性
- `max_tokens=2048`：足以覆盖一篇日志的提取结果

### 输出示例

```jsonl
{"type": "topic", "domain": "qtdata", "title": "洗过最脏的数据", "summary": "分享处理过的极脏数据案例", "source": "2026-07-08.md"}
{"type": "methodology", "domain": "qtconsult", "title": "标准化创业咨询服务模式", "summary": "建立针对特定类型客户的标准化服务模式", "source": "2026-07-09.md"}
```

`grouped.md` 组织方式：

```
## topic (5)

### 量潮数据
- **xxx** — ...

### 量潮课堂
- **xxx** — ...

## methodology (8)

### 量潮数据
- **xxx** — ...
```

### 容错

- 空日志跳过
- 非 JSON 行跳过
- 缺失必要字段跳过
- LLM 未分类 → 关键词 fallback
- 关键词也匹配不到 → `default`

---

## sync.py — 预览同步

### 职责

展示最新一次提取结果，列出 `profile/topics/` 已有文件，提供同步指引。

### 逻辑

```
1. 找 outputs/ 中最新（按文件名排序最后）的运行目录
2. 打印该目录下的 grouped.md
3. 列出 profile/topics/articles/ 和 profile/topics/notes/ 的已有文件
4. 给出 cp 命令建议
```

**不执行任何写入**，仅展示信息供人工确认。

---

## 数据流总图

```
                   实验室边界 (examples/default/lab/)
               ┌──────────────────────────────────────────────┐
data/journal/  │  inputs/          outputs/                    │  data/profile/
  日志文件      │    │                │                         │   选题/内容
  (只读)       │    ▼                │                         │   (只读)
               │  extract.py ──▶  <timestamp>/                 │
               │  (LLM 提取)    ├── raw.jsonl                  │
               │  + 分类        │   (含 type/domain/title/...) │
               │                ├── grouped.md                 │
               │                │   (按 type → domain 分级)     │
               │                      │                        │
               │                      ▼ 人工确认                │
               │              ────────┴───────────────▶ 复制────┤
               └──────────────────────────────────────────────┘
```

## 配置

所有脚本通过 `quanttide_agent` 包读取 LLM 配置：

| 变量 | 默认值 |
|------|--------|
| `LLM_API_KEY` | 从 `quanttide_agent.config` 读取 |
| `LLM_BASE_URL` | `https://api.deepseek.com` |
| `QT_LLM_MODEL` (环境变量) | 覆盖使用的模型名 |
