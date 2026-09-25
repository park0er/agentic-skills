# Interview Method Reference

Why "ask one thing at a time" beats "ask everything"; how to write prompts and hints that elicit detail without leading the answer; when to follow up vs. when to move on.

## The Socratic principle

The skill's name is `interviewer`, not `extractor`. The difference matters:

- **Extractor**: maximize answers per minute. Throw a wide net per question. Output: bullet-point summaries.
- **Interviewer**: help the user *think*. Each question is a small mirror they hold up to a corner of their memory. The user often discovers their own answer in the act of typing it. Output: real understanding, sometimes more valuable than the surface answer.

This skill is the latter. Optimize for the user's thinking quality, not the data density per minute.

## One question, one cognitive load

A typical user, faced with a question, does this:

1. Read the prompt
2. Pick the **easiest** part of it to answer
3. Type that
4. Move on

If the prompt asks 5 things, you get answers to ~1.5 of them. The other 3.5 are dropped silently.

Atomic questions (one thing per prompt) avoid this loss. The user can't dodge — there's nothing to dodge to.

This is also why the UI shows ONE question at a time, not a long form. A long form with 50 questions visible at once produces "scan-and-skip" behavior. A single card focuses attention.

## The `kind` chip is a memory drawer cue

Each question card shows a small chip: `时间 / 在哪 / 人物 / 什么 / 为什么 / 怎么发生`. This isn't just decoration — it's a **memory retrieval cue**.

Cognitive psych: human memory is structured by these dimensions. When you ask "what happened?", the brain searches a wide event space. When you ask "what time of day?", the brain searches a narrow temporal space. The chip pre-narrows the search.

So even when the prompt itself is clear, the chip helps the user click into the right mental drawer immediately.

This is why you should:
- **Match the chip to the prompt's actual question type** (a `时间` chip on a "what" question is misleading)
- **Pick the chip granularly** (`什么 - 压缩前` is more useful than just `什么` if the topic has before/after)
- **Don't invent more than ~10 distinct chips** across the whole interview — too many chips means the chip has no signal

## Hint design: open the door, don't push them through

A hint sits below the prompt and gives the user permission to answer imprecisely.

### Bad hints (leading)

> 比如，应该是 3 月 12 号，那天你在办公室和 X 一起讨论...

This puts words in the user's mouth. They'll either:
- Just say "yes that's right" (no real information added)
- Feel cornered if reality differed from your guess (defensive answer)

### Good hints (lowering the bar)

> 比如几月份？记不清的话，标个大概范围（'去年某 Q'/'冬天'）就行。

This:
- Gives example formats ("几月份")
- Explicitly accepts approximation ("标个大概范围")
- Lists actual answer-shapes ("'去年某 Q'/'冬天'") so the user knows what counts

### Pattern

> [Concrete examples of acceptable answer formats]?[ Permission to be imprecise].

Examples:
- "宁宁是产品 / 运营 / 数据分析 / 其他。" — list the categories so user can pick one
- "记不清就标个大概阶段。" — explicit permission for fuzziness
- "原话最好，没有就大致意思。'转发了'/'问了一句'/'打字一段'。" — multiple grain levels with examples

## When to skip vs. answer

The "跳过" button is the user's escape hatch. They can come back later. **Encourage skipping** rather than letting them stare at a question they can't answer.

Why this matters: a user stuck on question 3 of 30 will close the tab and never come back. A user who skips through questions 3, 7, 12, then circles back for the easy ones, finishes the interview.

The UI design supports this:
- Skip button is prominent (not hidden in a menu)
- The overview at the bottom shows skipped questions visibly
- "Previous" works freely — you can revisit any answer any time
- The progress bar counts answered, not "completed" — there's no "submit" gate

## When the user gives a one-liner: don't push for more

Sometimes the answer is genuinely short. "宁宁是数据分析" — that's the answer. Don't add follow-up questions in the hint trying to extract more. Trust the user's calibration of "what's worth saying".

When you (the agent generating the schema) are tempted to write "请详细描述...", reframe to a more atomic question instead, or split into two prompts.

## The drop-empty-answer rule

The template's input handler:

```js
if (text.trim() === '') {
  delete state.answers[q.id];   // un-answered
} else {
  state.answers[q.id] = { text, saved_at };   // answered
}
```

**Empty text deletes the answer entry.** Why this matters:

- User types "..." then deletes it → the question reverts to "not answered" (✗ in overview)
- A user who typed once and deleted hasn't actually answered
- Progress count stays honest: 5/30 answered means 5 questions have non-empty content

This protects the user from a false sense of progress and also from accidentally "answering" a question by tabbing through it.

## Order of questions inside a topic

Within a topic, order the questions by **cognitive ease, easy to hard**:

1. `时间` first (when did this happen?) — usually easy, anchors memory
2. `什么` (what was going on?) — sets the scene
3. `人物` / `在哪` — adds dimensions
4. `怎么发生` (how exactly did X happen?) — needs reconstruction
5. `为什么` last — usually requires reflection, may take time

This isn't strict — sometimes the topic has a natural narrative order — but if you're in doubt, easy-to-hard reduces drop-off.

## Order of topics in the interview

Topics within a category, or in a flat schema, should follow:

1. **Setup topics** first — easy stuff that lets the user warm up
2. **Substantive / important topics** in the middle when the user is in flow
3. **Reflective / synthesis topics** at the end (e.g., "最大的收获")

Don't put the hardest emotional question first. The user closes the tab.

## Rate of progress

The app auto-toasts a backup reminder every 5 answers ("已答 N 题。建议导出一次 JSON。"). Don't tune this lower (annoying) or higher (data-loss risk). 5 is the sweet spot validated on the V6 故事采访 case.

The user typically completes 1-2 questions per minute when in flow. 30 questions = 20-40 minutes. Plan topic count to fit available session length.

## Asking domain-specific kinds

The default 5W1H suffices for ~90% of interviews. Add domain-specific kinds when:

- The domain has structured frameworks already in the user's head (STAR for behavior interviews, OKR-style for goal-setting, decision-matrix for pickings)
- Adding the kind genuinely cues a different memory dimension than 5W1H covers

Examples:

| Kind | Domain | Cues |
|---|---|---|
| `情境` (S) | STAR behavior | Situation backdrop |
| `任务` (T) | STAR behavior | What was being attempted |
| `行动` (A) | STAR behavior | Specific actions taken |
| `结果` (R) | STAR behavior, retros | Outcome |
| `决策` | Decision interviews | Choice made |
| `权衡` | Decision interviews | Trade-off considered |
| `情绪` | Reflection / personal | Emotional dimension |
| `证据` | Critical thinking | What supports the claim |

Don't go overboard. If you're inventing the 12th kind, you've probably overengineered the schema.

## When NOT to use this skill

Cases where chat-only interviewing in the current conversation is better than generating an HTML app:

- The user wants quick clarification ("just answer 3 questions about X")
- The user is in a focused conversation flow already; switching to a separate UI breaks state
- The user explicitly wants to talk it through (interview ≠ form)
- The interview is one-shot and the answers feed directly into your next response

Cases where this skill IS the right tool:

- The interview is multi-session ("I'll do this over a few days")
- The user wants to see all questions at once, jump around
- The user wants persistent storage they can come back to
- The user wants to share / continue on another device (export JSON)
- The user explicitly mentions wanting an "app" / "interactive thing" / "采访器"
