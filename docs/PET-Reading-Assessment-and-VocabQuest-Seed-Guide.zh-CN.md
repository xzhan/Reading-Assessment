# PET Reading 测评与 VocabQuest 种子题库说明

版本日期：2026-05-07

本文档说明当前 Reading MVP 如何使用 VocabQuest 生成的阅读题，如何判断候选题是否可以入库，以及主测评流程如何使用这些题目。

## 1. 目标

Reading MVP 的目标不是生成官方 Lexile 或 Renaissance Star Reading 分数，而是给家长和老师一个可解释的内部阅读水平估计。系统会输出：

- Lexile-like 阅读区间
- ZPD-like 推荐练习区间
- CEFR 估计
- 阅读技能画像
- 家长选书建议
- 测试时长与可信度提示

当前主测评流程为：

- 6 篇阅读
- 每篇 5 道选择题
- 共 30 道题
- 覆盖 5 个阅读技能

## 2. 五个必需技能

每一篇可用于测评的阅读都必须覆盖以下 5 个技能，并且每个技能出现一次：

| 技能字段 | 中文含义 | 题目作用 |
| --- | --- | --- |
| `main_idea` | 主旨大意 | 判断学生是否理解文章整体意思 |
| `detail` | 细节理解 | 判断学生是否能定位和理解明确细节 |
| `inference` | 推断理解 | 判断学生是否能根据文本推出隐含信息 |
| `vocabulary_context` | 语境词义 | 判断学生是否能根据上下文理解词义 |
| `structure_author_purpose` | 结构与作者目的 | 判断学生是否理解作者为什么这样写 |

如果一篇文章缺少这些技能中的任何一个，默认不能直接作为诊断测评题入库。

## 3. Reviewed Candidate 是什么

`reviewed candidate` 是已经从 VocabQuest export 中标准化出来、可以进入人工或程序审核的候选阅读题记录。

主要存储位置：

- `data/reading_review/vocabquest_reviewed_candidates.jsonl`
- `data/reading_review/vocabquest_reviewed_candidates.csv`

每条 candidate 会包含：

- passage id
- title
- body text
- anchor Lexile-like 难度
- CEFR level
- 题目列表
- 每题技能
- A-D 选项
- 正确答案
- rationale
- validation flags
- diagnostic_ready 状态

## 4. 什么样的 Candidate 可以入库

一个 candidate 必须满足：

- passage 正文不少于 80 个英文词
- 正好 5 道题
- 每题都有 A-D 四个选项
- 正确答案能在选项中找到
- 正确答案有 explanation / rationale
- 5 道题刚好覆盖 5 个必需技能
- 没有 validation flags

满足这些条件时：

```text
diagnostic_ready = true
validation_flags = []
```

这样的 candidate 可以被 promote 成 app seed reading。

## 5. Promotion 是什么

Promotion 是把 reviewed candidate 转成 app 可以直接使用的 seed passage。

输入：

```text
data/reading_review/vocabquest_reviewed_candidates.jsonl
```

输出：

```text
backend/pet_reading_api/vocabquest_promoted.py
```

promoted passage 会被 `seed_data.py` 加入 `READING_PASSAGES`，然后在本地数据库初始化时写入 `reading_passages` 和 `reading_items`。

## 6. 当前题库状态

截至本次更新：

- review bank 中共有 39 条 VocabQuest reviewed candidates
- promoted seed 中共有 10 篇 VocabQuest readings
- 29 条 candidate 暂未入库

本次新增或替换：

| Seed ID | 标题 | 状态 |
| --- | --- | --- |
| `rp_vq_253ea7923758` | `Reading Quest [Literature]: PET全_Page_57_03261514` | 替换旧的不合格 Page 57 |
| `rp_vq_3fcd767f3e99` | `Reading Quest [Literature]: PET全_Page_59_03261514` | 新增入库 |

旧的 Page 57 candidate：

```text
vq_4d34d1625dea
```

因为技能覆盖不完整，已经从 reviewed JSONL 中移除，并由新的正确版本替换。

## 7. 如何导入新的 VocabQuest 文件

假设新文件在：

```bash
/Users/xzhan/Downloads/reading_quests.json
```

先导入为 reviewed candidates：

```bash
python3 scripts/import_vocab_quest_reading_bank.py \
  /Users/xzhan/Downloads/reading_quests.json
```

导入后检查输出：

```text
Imported N reviewed Vocab Quest candidates
Diagnostic-ready candidates: M
Validation flags:
...
```

如果 `Diagnostic-ready candidates` 数量不够，说明部分题还需要人工修复。

## 8. 如何生成 app seed

导入或修复 candidate 后，运行：

```bash
python3 scripts/promote_vocab_quest_reading_bank.py
```

输出示例：

```text
Promoted 10 candidates
Skipped 29 candidates
Output: backend/pet_reading_api/vocabquest_promoted.py
```

`Promoted` 表示可以进入 app 的阅读题数量。

`Skipped` 表示暂不适合入库的候选题数量。常见原因包括：

- `item_count_not_5`
- `missing_skill_count_not_1`
- `unsupported_missing_skill_*`

## 9. 最小人工修复原则

如果一篇文章整体质量可以，但只有一个技能不满足，优先使用最小修法：

- 保留合理题目
- 只修改错误的 `skill`
- 或只替换一题为缺失技能
- 不重写整篇文章
- 不随意改变 passage 内容

例如之前的修复方式：

```text
保留 q1/q2/q4/q5，把 q3 从 detail 改成 structure_author_purpose
```

这样可以减少人工成本，也避免引入新的内容错误。

## 10. 主测评流程

用户点击 `Start assessment` 后：

1. 系统创建 reading assessment
2. 根据年级选择初始 anchor Lexile-like 难度
3. 每次返回一篇 passage 和 5 道题
4. 用户提交答案后，系统计算该 passage 正确率
5. adaptive logic 调整下一篇的 anchor
6. 完成 6 篇后，状态变为 `ready_to_complete`
7. 系统生成 reading report

状态规则：

```text
passage 1-5: continue
passage 6: ready_to_complete
```

## 11. 报告中的重要术语

| 术语 | 含义 |
| --- | --- |
| Lexile-like | 内部阅读难度估计，不是官方 Lexile |
| SS-like | 内部 scaled score 展示位，不是官方 Star SS |
| PR | Percentile Rank；当前没有 norm group，所以显示 N/A |
| GE-like | 内部年级等价估计 |
| IRL-like | 从练习区间推算的教学阅读水平 |
| ZPD-like | 推荐练习阅读区间 |
| Benchmark-like | 内部 benchmark 分档 |
| Test Fidelity | 测评可信度提示 |

## 12. 验证命令

每次导入、替换或 promote 后，至少运行：

```bash
python3 -m unittest tests.test_reading_review_bank tests.test_reading_api tests.test_reading_adaptive tests.test_reading_estimator
git diff --check
```

发布或提交前建议运行完整测试：

```bash
python3 -m unittest discover -s tests
```

## 13. 本地运行

启动本地 app：

```bash
python3 backend/app.py --host 127.0.0.1 --port 8123 \
  --db-path /tmp/english_test_reading_manual_test.db
```

打开：

```text
http://127.0.0.1:8123/app/reading
```

如果已经有旧 server 占用端口，需要先停止旧进程，再重启。重启后数据库会重新 seed，才能看到最新 promoted readings。

