---
name: mimo
description: "MiMo 评测 — 模型 AB 对比 / Agent CLI 对比"
---

MiMo AB 评测工具。盲测对比两个模型 / 两个 Agent CLI 的体验。

## Arguments

用户输入: $ARGUMENTS

## 参数解析

从 `$ARGUMENTS` 判断命令（按顺序匹配，先匹配到先执行）：

- `submit` 或 `提交` → 执行**提交结果**
- 以 `模型` 或 `model` 开头 → 后面的内容作为 prompt，执行**模型评测**
- 以 `agent web` 或 `agent 网页` 开头 → 执行**Agent Web 评测**
- 以 `agent` 开头 → 后面的内容作为 prompt，执行**Agent 终端评测**（默认）
- 其他任何输入（包括非空内容、为空、含义不明确） → **不要猜测，不要直接启动评测**，展示以下帮助：

```
📋 MiMo 评测命令：

  /mimo agent <任务描述>        Agent 评测（Claude Code vs MiMo Code，终端双栏）
  /mimo agent web <任务描述>    Agent 评测（浏览器双栏）
  /mimo model <任务描述>        模型 AB 评测（浏览器双栏）
  /mimo submit                  提交评测结果（仅终端模式，在评测终端内执行）

示例：
  /mimo agent 给这个项目加上单元测试
  /mimo model 帮我实现一个登录页面
```

> 去掉命令前缀后剩下的就是 prompt：`/mimo agent 写TODO` → prompt 是 `写TODO`；`/mimo 模型 写TODO` → prompt 是 `写TODO`；`/mimo 写TODO`（无前缀）→ prompt 是 `写TODO`。

---

## Git 仓库预检（启动任何评测前必做；submit 跳过）

worktree 隔离要求 `$ORIG_PWD`（用户当前目录）**自身是 git 仓库根**。若它落在某个**祖先** git 工作树里（如祖先目录有 stray `.git`），CLI 的 `git add -A` / `git worktree add` 会作用于整个祖先工作树，拖入大量无关文件。

```bash
cd "$ORIG_PWD" && git rev-parse --show-toplevel 2>/dev/null
```

- 命令失败或输出为空 → **跳过预检**，直接启动（CLI 会自行 `git init`）。
- 输出等于 `$ORIG_PWD`（必要时 `realpath` 规范化后比较）→ **跳过预检**，正常。
- 输出非空且 ≠ `$ORIG_PWD` → **mismatch，必须 AskUserQuestion** 三选一：
  1. **初始化独立 git 仓库（推荐）** — 不影响祖先仓。先 `cd "$ORIG_PWD" && git init && git add -A && git commit -m "mimo eval: initial commit" --allow-empty`，再走对应评测启动命令。
  2. **中止评测** — 不启动；提示用户可清理祖先 `<git_root>/.git`，或 `cd` 到独立 git 仓库下再跑。
  3. **仍然使用祖先仓库（有风险）** — 直接启动，并**显式警告**：后续 `git add -A` / `git worktree add` 会作用于整个祖先工作树 `<git_root>`，可能很慢或污染祖先仓。

> 注：在用户主目录（`$HOME`）下启动评测会被后端直接拒绝（避免在 home 创建 git 仓库 / worktree），需先 `cd` 进具体项目目录。

---

## Agent 终端评测（/mimo agent <prompt>，默认）

**先完成 Git 仓库预检。** 在终端中启动 Claude Code vs MiMo Code 对比：

```bash
ORIG_PWD="$PWD" && cd ~/.claude/skills/mimo/skill && MIMO_USER_CWD="$ORIG_PWD" MIMO_FIRST_MESSAGE="<prompt部分>" npx tsx src/start-cli-eval.ts
```

执行后告诉用户：
- 已打开两个终端（花名 Alpha / Beta），分别是不同的 CLI 工具。
- 一个终端已自动注入首句，另一个需**手动粘贴同样的 prompt**（两侧首句必须一致，否则 AB 无效）。
- 正常开发，**完成后在每个评测终端内分别执行 `/mimo submit`**（Claude 侧、MiMo Code 侧都要，详见「提交结果」）。

**注意：** 此命令会打开两个新的终端窗口，**不要 run_in_background**。

---

## Agent Web 评测（/mimo agent web <prompt>）

**先完成 Git 仓库预检。** 在浏览器中双栏进行 Agent 评测：

```bash
ORIG_PWD="$PWD" && cd ~/.claude/skills/mimo/skill && MIMO_USER_CWD="$ORIG_PWD" MIMO_FIRST_MESSAGE="<prompt部分>" npx tsx src/web-start-agent.ts "$ORIG_PWD"
```

执行后告诉用户：
- 已在浏览器打开 Agent 评测界面 http://localhost:3458 ，左右两栏是 Claude Code 和 MiMo Code（花名隐藏），首句已注入。
- 可连续对话——两侧消息已串行化，快速连发不会丢、也不会因上一轮未结束而报错。
- **完成后在页面上点「结束评测」提交**（Web 模式不走 `/mimo submit`）。

**注意：** 此命令会持续运行（Web 服务器），**使用 run_in_background 运行**。

---

## 模型评测（/mimo model <prompt>；/mimo <prompt> 无前缀同义）

**先完成 Git 仓库预检。** 在浏览器中双栏，两个模型同时回答：

```bash
ORIG_PWD="$PWD" && cd ~/.claude/skills/mimo/skill && MIMO_USER_CWD="$ORIG_PWD" MIMO_FIRST_MESSAGE="<prompt部分>" npx tsx src/web-start.ts "$ORIG_PWD"
```

执行后告诉用户：
- 已在浏览器打开 Web 评测界面 http://localhost:3457 ，左右两栏是两个模型，首句已注入。
- **完成后点页面「提交 A」/「提交 B」分别提交**（Web 模式不走 `/mimo submit`）。

**注意：** 此命令会持续运行（Web 服务器），**使用 run_in_background 运行**。

> **纯 Web 模式**：同上命令，但**去掉 `MIMO_FIRST_MESSAGE`**，进页面后自己输入首句（其余一致）。

---

## 提交结果（/mimo submit 或 /mimo 提交）—— 仅终端模式

> Web 模式（模型 / agent web）的提交是**点页面按钮**，不走 `/mimo submit`。
> 终端模式下，在**评测子终端内**（不是你敲 `/mimo` 的那个主终端）执行 `/mimo submit`。

**先用纯文本对话**（不要用 AskUserQuestion 工具）一次性把问题列给用户，让其一次回复：

```
请回答以下评测问题：

1. 是否采用了这一侧的代码产出？（输入 1/2/3）
   1=采用  2=部分采用  3=未采用

2. 使用体感打分 1-5（交互流畅度、理解力、是否需要反复纠正）

3. 产出效果打分 1-5（代码正确性、完整性、可用性）

4. 补充反馈（可选，无内容直接跳过）
```

解析回复（如 "2 3 4" 或 "2，3，4，没什么问题"）后，按当前终端环境变量 `MIMO_CLI_TYPE` 分流：

- 有 `MIMO_CLI_TYPE`（Agent 评测终端）→ 执行：

```bash
cd ~/.claude/skills/mimo/skill && MIMO_ADOPTION="用户的选择1/2/3" MIMO_RATING="体感评分1-5" MIMO_OUTPUT_RATING="效果评分1-5" MIMO_FEEDBACK="用户的反馈文本" npx tsx src/submit-cli-eval.ts
```

- 否则（模型评测终端）→ 执行：

```bash
cd ~/.claude/skills/mimo/skill && MIMO_ADOPTION="用户的选择1/2/3" MIMO_RATING="体感评分1-5" MIMO_OUTPUT_RATING="效果评分1-5" MIMO_FEEDBACK="用户的反馈文本" npx tsx src/submit.ts
```

执行后告诉用户提交结果（成功或失败）。若报错"当前终端不是评测终端"，说明不在通过 `/mimo` 启动的评测终端里，提醒用户切换到正确的终端。

---

## 注意事项 / 首次使用

- **首次使用**：`cd ~/.claude/skills/mimo/skill && npm install` 安装依赖；首次运行会自动打开浏览器登录，点「授权」即可，后续免登。
- 评测状态保存在 `~/.mimo-eval/current.json`；同一时间只保持一条评测任务。
- 端口：模型 / 纯 Web 模式 = 3457，Agent Web = 3458。
- 终端模式两侧都要分别提交，才算一组完整的 AB 数据。
