---
name: rollica-dev-squad
description: 为赵锡盛组建临时的 Rollica 开发小队（squad）：现查并复用/新建私有 agent（协调者队长统一 CCGlm5.3Flash 不写码，执行者 + 必有 reviewer 当成员，复杂需求可加 planner），创建小队并注入协调者契约（队长在 issue 里 @成员派活并转述规则、执行者开发合并、review 门禁、方案停下等人工审），再把目标 issue 指派给小队开工。Use when 用户说 组个小队/建个小队/组个开发小队/临时小队/组个 squad/建 squad，或要求由"执行者+reviewer"的小队推进某个 issue。Not for：单独建一个 agent（用 rollica-creating-agents）、给已有 agent 直接派 issue、查已有小队状态、成员增删以外的 squad 运维。
---

# rollica-dev-squad — 组建临时 Rollica 开发小队

## 核心契约（先读，防误设）

- squad 不是 agent：issue 指派、@小队、autopilot 全部只路由到 leader（队长），成员不会被自动 fan-out。
- squad 的 `instructions` 只进 leader 的 briefing，**成员收不到**。规则传导 = 队长委派时转述。
- **队长 = 协调者，纯动嘴、零代码操作**：不写代码、不拉仓库、不做任何 git/工具类落盘操作（每次 checkout 都会新克隆仓库、堆冗余 workdir）；只读 issue、@成员、转述规则、跟进进度。一切代码操作（开发、提交、合并推送）都在执行者侧。daemon 对队长任务不复用 PriorWorkDir（平台把队长当轻协调者），CLI 类 agent 会话按 cwd 存，工作目录一换会话必丢；执行者、reviewer 一律当**成员**（成员任务正常复用工作目录，会话连续）。**执行者绝不能当队长**——这是 2026-09-03 排查 MIA-429、MIA-406 会话丢失后的结构性结论。
- 队长必须是 workspace agent；队长被归档后所有路由 fail closed。
- agent `description` 只是目录摘要，不进 prompt；`instructions` 才进 prompt。
- **reviewer 必须是独立 agent（独立会话）**：执行者与 reviewer 不得是同一个 agent——哪怕 harness+模型+thinking 完全相同，也要新建第二实例（名字加 `-2`，即"杠二"，如 pkoCodexGPT5.6SolHigh-2）。同一 agent 复用同一会话，review 的上下文就不独立了。

## 建队流程

### 1. 输入确认（信息不全时先问，不要猜）

**引导流程**：用户只说"建个小队"而没给全时，把缺的项**一次性问齐**，不许猜、不许拿默认值顶替：

1. 执行者（成员，负责开发）：harness + 模型
2. reviewer（必有）：harness + 模型
3. 是否需要 planner（可选）：复杂需求才设

只有以下项可以默认，无需问：

- 协调者队长 = **CCGlm5.3Flash（RollieCC）**，所有小队统一；现查时目标 workspace 里没有该 agent（如 Parko）→ 一次性问用户协调者用谁，不许猜
- 机器 = 用户当前对话所在的机器（用户明确说别台才用别台）
- planner = 用户没提就不设
- 小队名 = 默认规则生成（见下），用户给了名字就用用户的

**小队名默认规则**：**整体无空格、驼峰紧凑**：`{执行者模型名}（执行者）{reviewer模型名}（Reviewer）`，涉及 planner 再追加 `{planner模型名}（Planner）`；Codex/GPT 系模型名带 thinking level（如 GPT5.6SolHigh），执行者与 reviewer 同模型时 reviewer 标 `-2`。协调者不进小队名。例：`Gemini3.8Flash（执行者）GPT5.6SolHigh（Reviewer）`。用户给了名字就用用户的。

**小队保持通用**：不把目标 issue 绑进小队定义——那会让小队失去通用性。派活是独立的后续动作（见"派活"）。

### 2. 现查名单，判定复用（禁止维护本地持久名单）

共享 workspace，别的会话/别人也会建 agent 和小队，本地名单会过时导致误判——每次现查：

```bash
multica agent list --output json
multica squad list --output json
```

- agent 去重键 = **harness + 模型 + 机器**（同模型不同机器 = 不同 agent，否则活会跑到别的电脑上）。机器看 agent 绑定 runtime 的 hostname。
- squad 去重键 = **协调者 + 执行者 + reviewer (+planner) 的 agent 组合完全一致**。一致 → 复用（必要时 update instructions）；不一致 → 新建。
- 把现查对比结果报给用户：哪些复用、哪些新建。

### 3. 建缺失的 agent

```bash
multica agent create --name "<pko+Harness名+模型名，驼峰无空格，见下方命名规则>" \
  --runtime-id <该机器上对应 harness 的 runtime id> \
  --model <完整模型 id，见下方 provider 前缀规则> \
  --visibility private \
  --description "<一句话目录摘要>" \
  --output json
```

- **指定模型时 `--model` 必须用带 provider 前缀的完整 id**（前缀由该 harness 实际配置的 provider 决定，**不要写死特定前缀**）：Pi harness 的 model id 形如 `<provider>/…`，完整 id 可从 `~/.pi/agent/models.json` 精确推导：`providers` 对象的每个 key 就是 provider 前缀（当前是 `mify`、`openrouter`），拼上其下 `models[].id` 即完整 id（如 `mify` + `xiaomi/mimo-v2.6-pro` → `mify/xiaomi/mimo-v2.6-pro`）。条目里的裸 id **不能直接当 agent model 用**。pi CLI 无非交互的模型列表子命令，脚本化场景直接读 models.json；拿不准时以现成同 harness agent 为准（`agent get` 一个如 PkoPiGLM5.3Flash 看 model 写法）

- 命名规则：**整体无空格、驼峰紧凑**，结构 = 用户个人前缀 `pko` + harness 名 + 模型名。参考用户现有 agent：`pkoKiroOpus5`、`pkoTraeGLM5.3`、`PkoPiGLM5.3Flash`。例：`pkoAntiGemini3.8Flash`（Antigravity + Gemini 3.8 Flash）、`pkoCodexGPT5.6SolHigh`（Codex + GPT 5.6 Sol，thinking high）、`pkoGrokBuildGrok4.6`（harness 叫 Grok Build 时）
- **Codex/GPT 系模型的 thinking level 必须标在名字里**（High/Medium 能力差距巨大）：如 `pkoCodexGPT5.6SolHigh`，`--thinking-level` 配置与名字一致；同配第二实例用 `-2`（杠二）
- "Build" 只有在 harness 本身就叫 Grok Build 时才出现在名字里；其他 harness（Antigravity / Pi / Trae / Kiro / Codex 等）直接写原名（可缩写如 Anti），不要硬加 Build
- 同名冲突（别的机器已有同名）→ 名字后追加机器短名，仍无空格：`pkoCodexGPT5.6SolImac`
- **instructions 保持空**：不要把开发规则/Work Group 规则写进 agent instructions（规则由小队 instructions 承载，经队长转述传导到成员）
- 其他 harness 的模型 id 格式未知时，同样先看现成同 harness agent 的 model 值再写，不要从模型目录/配置文件里照抄裸 id
- visibility 一律 private

### 4. 建小队

```bash
multica squad create --name <小队名> --leader <协调者 agent 名或 id，默认 CCGlm5.3Flash> --output json
multica squad update <squad-id> --instructions "$(cat squad-instructions.md)" --output json
multica squad member add <squad-id> --member-id <执行者 agent id> --type agent --role executor --output json
multica squad member add <squad-id> --member-id <reviewer agent id> --type agent --role reviewer --output json
multica squad member add <squad-id> --member-id <planner agent id> --type agent --role planner --output json  # 仅设 planner 时
```

- instructions 用下方模板原样注入（可按任务微调任务上下文，结构不动）
- create 时 leader 自动入队（role leader），无需再加
- 建完用 `multica squad list --output json`（或 get）核对花名册：协调者 = leader、执行者 = executor、reviewer = Reviewer、planner = Planner

### 5. 派活（独立动作，不绑定小队定义）

小队是通用资源，建队时不绑 issue。用户要派活时，再把指定 issue 指派给小队：

```bash
multica issue update <issue-id> --assignee "<小队名>" --status todo   # todo 立即触发 leader；backlog 停着不触发
```

或在 issue 评论里 @小队。触发的是 leader（协调者），协调者按契约里的「委派流程」在 issue 里 @执行者开工——开发发生在执行者的成员任务里，工作目录正常复用、会话连续。把触发的 issue 与状态报给用户。

## 方案审阅闭环（设了 planner 才有）

1. planner 产出方案 → 发 issue 评论，关键方案文件作为附件上传
2. 协调者设 metadata `waiting_on`，issue 置 blocked，然后**停**
3. 赵锡盛回复同意后才进入开发

## 小队 instructions 模板（协调者契约）

```markdown
# Rollica 开发小队 — 队长协调契约（协调者队长）

本小队是围绕当前任务的临时开发小队，以下为任务期内的要求。

## 角色分工（以花名册为准）
- 队长 = 协调者（你）：纯动嘴，零代码操作——不写代码、不拉仓库、不做任何 git/工具类落盘操作，否则每次 checkout 都会新克隆仓库、堆冗余 workdir。你只负责读任务、拆解转述、在 issue 里 @成员派活、跟进进度、把关收尾；一切代码操作（开发、提交、合并推送）都在执行者侧进行。
- 执行者（成员）：接收你转述的任务后直接开发；本地已有仓库 checkout，review 通过后由执行者负责最终合并推送到 origin/xisheng。
- reviewer（成员，必有）：独立负责本次相关 issue 的 code review；P1 及以上的问题全部解决前不得通过，循环到通过；review 进展随时同步 issue。
- planner（成员，若花名册有）：只做技术方案，产出后停下等赵锡盛人工审，见「方案先行」。

## 委派流程（你的操作手册）
1. 被指派或被 @ 后：先读 issue 全文和关联评论，把任务拆成"一句话目标 + 验收标准"。
2. 在 issue 评论里 @执行者 agent 派活：任务目标 + 下方「开发规则」原文转述 + 提醒"动手前先在 issue 评论里同步方案"。
3. 执行者在 issue 里报完成后：你 @reviewer，一句话"请进行本次 issue 相关的 code review"。
4. review 提出 P1 及以上问题：你转回执行者修复，修完再 @reviewer，循环到通过。
5. review 通过后：提醒执行者合并推送 origin/xisheng，确认后在 issue 里同步收尾进展。
给成员的话说清楚就好，不要额外堆要求；你是推进进度的管理者，不是提要求的老板。

## 开发规则（@执行者派活时原文转述）
1. git 提交邮箱：zhaoxisheng@xiaomi.com
2. 每个新 issue/功能建独立功能分支；建分支前先基于最新 origin/xisheng rebase
3. code review 由小队 reviewer 独立执行；P1 及以上全部解决才通过，进展同步 issue
4. review 通过后由执行者合并推送到 origin/xisheng
5. 所有回复和 issue 评论署名模型名字/型号
6. 父 issue 为完整时间线：派生子 issue 时，父 issue 必须始终保有按时间顺序的完整进展记录；子 issue 记录只是补充，不能替代

## 方案先行（开发前，硬要求）
- **动手开发前，先在 issue 评论里同步你的方案**：打算怎么修/怎么做，简明扼要。
- **关键方案文件（Markdown/HTML 等）必须作为附件上传到对应 issue**，便于在 issue 里直接查看。
- 真正的大功能走仓库的 OpenSpec 流程；普通改动也必须有上述方案同步，不许闷头就写。
- 设有 planner 时：planner 只做方案，产出后立即停下等赵锡盛人工审阅（方案发到 issue 评论 + metadata waiting_on + 状态置 blocked），未经赵锡盛明确同意不得进入开发。协调者负责盯住这个停下动作。

## 项目共享规则
1. 动手前先读仓库根目录 AGENTS.md（至关重要）
2. 本地 QA 通过后，等 staging 测试的 issue 可先行标「已完成」
3. 最小必要改动、不过度设计，方案简明扼要；快速迭代期，面向内部用户
```

## 注意

- 建 squad、update instructions、member add、指派 issue、@小队 都会触发 leader 任务或改持久状态——只在用户明确要求时执行，不要试跑。
- 现有小队若还挂着旧契约的 instructions（"队长=执行者"版），要在它上面派活前，先和用户确认是否 `squad update` 换成上面的新模板。
- 受管 Work 会话里若不能直连 multica，用该会话可用的正式 CLI 通道（如 rollica-management 包装器）执行同参数命令；文件参数加 `--allow-external-file`。
