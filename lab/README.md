# 实验室操作说明

## 快速开始

```sh
python3 lab/scripts/fetch.py     # 拉入今日日志
python3 lab/scripts/extract.py   # LLM 提取候选条目
python3 lab/scripts/sync.py      # 预览待同步内容
```

## 指定日期

```sh
python3 lab/scripts/fetch.py 2026-07-08
python3 lab/scripts/extract.py
```

## 输出解读

每次运行 `extract.py` 会在 `outputs/` 下生成一个带时间戳的目录：

```
outputs/2026-07-09-1830/
├── topics/
│   ├── raw.jsonl           # JSONL，每条含 type / title / summary / source
│   └── grouped.md          # 按类型归并，可直接审阅
```

审阅 `grouped.md`，确认后将内容复制到 `data/profile/topics/` 下的对应文件。

## 设计约束

- 所有处理在 `lab/` 内完成，不修改外部子模块
- 输入从 `data/journal/default/` 复制而来
- 输出人工确认后再同步到 `data/profile/`
