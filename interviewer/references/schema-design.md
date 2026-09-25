# Schema Design Reference

How to take a topic the user wants to be interviewed about, and turn it into a `topics + questions` schema that produces a useful interview.

## Why atomic questions

The single most important design choice in this skill is **atomic questions** — each question asks ONE thing.

### Compound (bad)

> 你做规则式 + 程序查数那一段，是哪一周 / 哪个具体的掉量事件让你意识到'规则覆盖不下去了，需要换一种范式'？当时是你自己发现的，还是运营 / 业务找过来发现的？最好讲一个具体的画面 — 比如那一天你在做什么、为什么突然意识到这条路不行。

This question asks 5 things at once: when, what event, who discovered, what scene, why-realized. The user faced with this on a UI card will:

1. Stare at the wall of text
2. Pick whichever sub-question is easiest and answer that
3. Forget the other 4 sub-questions
4. Move on, leaving 80% of the prompt unanswered

The skill becomes a low-resolution data extractor.

### Atomic (good)

The same intent, decomposed into 5 questions over the same topic:

- **`时间`** — 规则式查数大概是哪段时间开始的？比如几月份？
- **`什么`** — 那段时间你做的最重要的几个查询场景是什么？
- **`人物`** — 那段时间最常找你做诊断 / 最常 @ 你的业务用户是谁？
- **`为什么`** — 第一次让你意识到"规则覆盖不下去了"的，是什么类型的 case？
- **`怎么发生`** — 那次具体怎么发生的？是别人来找你 → 跑了规则跑不出？还是你自己跑出来发现不对？

Each prompt asks ONE thing. The user's cognitive load per card is low. The `kind` chip cues which mental drawer to open. Answers come out clean and aligned.

## The 5W1H taxonomy

Default `kind` labels — use these for ~90% of interviews:

| 中文 | English | 用来问什么 |
|---|---|---|
| `时间` | when | 哪一天 / 哪一周 / 持续多久 / 时间顺序 |
| `在哪` | where | 哪个场所 / 哪个群 / 哪条链路 / 物理或数字位置 |
| `人物` | who | 谁参与 / 谁推动 / 谁阻挡 / 谁第一个用 |
| `什么` | what | 是什么事 / 是什么 case / 是什么数据 / 具体内容 |
| `为什么` | why | 为什么这样选 / 为什么是关键 / 因果链 |
| `怎么发生` | how | 流程 / 机制 / 现场画面 / 步骤 |

You can split / merge:
- `什么 - 压缩前` vs `什么 - 压缩后` for "before / after" comparison questions
- `时间+人物` for "哪天 / 跟谁" combined when they're tightly coupled
- Domain-specific: `结果` (result) for retros, `决策` (decision) for option-picking, `情绪` (feeling) for personal reflection

Don't invent more than 8-10 distinct `kind` labels — the chip becomes meaningless if every question has its own kind.

## How many questions per topic

**Sweet spot: 4-6 atomic questions per topic.**

- **< 3** — the topic could be merged with an adjacent topic. Or the topic was too narrow.
- **4-6** — covers the 5W1H without redundancy, finishes in 5-15 minutes per topic, keeps momentum.
- **> 7** — splits into two topics. Sign that the "topic" is actually two related events.

## How many topics total

**Sweet spot: 5-12 topics, ~25-50 total questions.**

- **< 5 topics** — probably too narrow a scope; the interview feels under-substantial.
- **5-12** — fits a single working session (45-90 min) at one user's pace; produces enough material for downstream synthesis.
- **> 15** — interview fatigue sets in. Either split into multiple interviews (e.g., "项目复盘 part 1: 立项-MVP", "part 2: 推广-生态") or compress.

## Categories: when to use, when to skip

Categories visually group topics with different color accents. Use only when:

1. The user has 2+ visually distinct phases / blocks already in their head
2. The grouping is a real semantic distinction, not just "first half / second half"

Examples where categories help:
- Storyline projects with **红 / 绿 / 蓝** color blocks (奠基 / 挑战 / 生态)
- Decision interviews with **选项 A / B / C** parallel branches
- Project retros with **立项 / 执行 / 复盘** phases

Examples where categories don't help and should be skipped:
- A linear story (just use topic order)
- A one-off curiosity ("帮我把脑子里这个想法理清楚")
- < 5 topics (categories add noise without earning their visual weight)

When skipping categories: leave `categories: []`, don't set `category` on topics. The template renders a single neutral accent.

## Worked example 1: Storyline V6 (5W1H, with categories)

Topic: 红块 · 章节 2 (架构演进 · 起点) — 规则式工具搞不定的那个 case

```json
{
  "id": "r1",
  "category": "red",
  "ch": "红块 · 章节 2 (架构演进 · 起点)",
  "title": "规则式工具搞不定的那个 case",
  "intro": "架构演进的起点：你做规则式 + 程序查数那一段。把'时间-人物-事'堆上来。"
}
```

Decomposed into 5 questions:

```json
[
  { "id": "r1-q1", "topic_id": "r1", "kind": "时间",     "prompt": "规则式查数大概是哪段时间开始的？", "hint": "比如几月份？记不清的话，标个大概范围（'去年某 Q'/'冬天'）就行。" },
  { "id": "r1-q2", "topic_id": "r1", "kind": "什么",     "prompt": "那段时间你做的最重要的几个查询场景是什么？", "hint": "掉量？增量？异常？还是别的？列 1-3 个就行。" },
  { "id": "r1-q3", "topic_id": "r1", "kind": "人物",     "prompt": "那段时间最常找你做诊断 / 最常 @ 你的业务用户是谁？", "hint": "可以是具体人，也可以是角色（运营 / 数据分析 / 业务负责人）。" },
  { "id": "r1-q4", "topic_id": "r1", "kind": "为什么",   "prompt": "第一次让你意识到'规则覆盖不下去了'的，是什么类型的 case？", "hint": "想到一个就行。" },
  { "id": "r1-q5", "topic_id": "r1", "kind": "怎么发生", "prompt": "那次具体怎么发生的？是别人来找你 → 跑了规则跑不出？还是你自己跑出来发现不对？", "hint": "用一两句话描绘画面。" }
]
```

## Worked example 2: Project retro (no categories, flat topics)

Topic: 这个项目的转折点

```json
{
  "id": "t-pivot",
  "title": "这个项目的转折点",
  "intro": "项目过程中，你判断'方向变了'的那一刻。"
}
```

Questions (note: hint can be omitted for self-explanatory prompts):

```json
[
  { "id": "t-pivot-q1", "topic_id": "t-pivot", "kind": "时间",     "prompt": "转折是项目第几周 / 哪个时间节点发生的？" },
  { "id": "t-pivot-q2", "topic_id": "t-pivot", "kind": "什么",     "prompt": "转折前在做什么？" },
  { "id": "t-pivot-q3", "topic_id": "t-pivot", "kind": "为什么",   "prompt": "为什么意识到要转？" },
  { "id": "t-pivot-q4", "topic_id": "t-pivot", "kind": "人物",     "prompt": "是谁推动 / 同意了这次转向？" },
  { "id": "t-pivot-q5", "topic_id": "t-pivot", "kind": "怎么发生", "prompt": "宣布转向那一刻是怎么发生的？谁说的？" },
  { "id": "t-pivot-q6", "topic_id": "t-pivot", "kind": "结果",     "prompt": "转向之后头两周，最直观的变化是什么？" }
]
```

## Hint design

A good hint:
- **Lowers the bar** for what counts as an answer ("记不清也没事，标个大概就行")
- **Gives examples** of acceptable answer formats ("比如几月份 / 几周 / 季度")
- **Doesn't lead** the answer (don't tell them what to say)

Bad hint: "你应该回答 3 月初的时候" — this is leading.

Good hint: "比如几月份？记不清的话，标个大概范围（'去年某 Q'/'冬天'）就行。" — opens up the answer space, signals "approximate is OK".

## Topic intro design

The `intro` field appears only on the first question of each topic. It's the user's "okay, what are we talking about now" moment. Keep it to 1-2 sentences and frame the topic without giving away the answer.

Good intros:
- "架构演进的起点：你做规则式 + 程序查数那一段。把'时间-人物-事'堆上来。"
- "项目过程中，你判断'方向变了'的那一刻。"
- "你第一次让团队之外的人看到 demo 的画面。"

Bad intros (too leading / too narrative):
- "我们要重点讨论你那次失败的决策..." (judgmental)
- "回想一下 3 月那次转折，当时你在办公室..." (puts words in user's mouth)

## Confirming the schema before generating HTML

Before you write the HTML in Phase 3, **show the user the schema as a draft**. Format:

```
我打算这样拆问题：

【红块 · 5 个 topic, 25 个原子问题】
  r1 · 规则式工具搞不定的那个 case      (5 题: 时间/什么/人物/为什么/怎么发生)
  r2 · 从自建 Agent Loop 到决定抽 Skill  (5 题: 时间/什么/为什么/时间+人物/怎么发生)
  ...

【绿块 · 3 个 topic, 13 个原子问题】
  ...

合计 8 个 topic, 39 题。预计 60-90 分钟。

要调整 / 增减 / 重排吗？
```

Let the user reorganize. Don't fight them on it — the schema is theirs. Then generate.
