# rollica-dev-squad CHANGELOG

## 2026-09-22 — pi-model-id-derivation

- 补充 Pi 完整 model id 的精确推导法：`~/.pi/agent/models.json` 的 `providers` key 就是 provider 前缀，拼上其下 `models[].id` 即完整 id；并注明 pi CLI 无非交互模型列表子命令，脚本化场景直接读 models.json。

## 2026-09-22 — pi-provider-prefix-not-hardcoded

- 修正上一条措辞：规则是"`--model` 必须带 provider 前缀"，前缀由该 harness 实际配置决定，**不写死 `mify/`**；`mify/` 只是当前 Pi 配置的现值。权威来源 = 现成同 harness agent 的 model 值。

## 2026-09-21 — pi-model-provider-prefix

- 建 agent 的 `--model` 必须用带 provider 前缀的完整 id：Pi harness 一律 `mify/` 开头（如 `mify/xiaomi/mimo-v2.6-pro`、`mify/zhipuai/glm-5.3-flash`）；`~/.pi/agent/models.json` 里的裸 id（`xiaomi/mimo-v2.6-pro`）不能直接用。create 命令示例补上 `--model` 参数，新增"拿不准先看现成同 harness agent 的 model 写法"规则。起因：2026-09-21 建 pkoPiMimoV2.6Pro 时用了裸 id，用户手动改回 `mify/` 前缀。

## 2026-09-09 — coordinator-voice-only

- 协调者契约收紧为「纯动嘴、零代码操作」：队长不写代码、不拉仓库、不做任何 git/工具类落盘操作，一切代码操作（开发、提交、合并推送）都在执行者侧。理由：队长任务不复用 workdir，每次 checkout 都会新克隆仓库、堆冗余目录（用户 2026-09-09 明确）。
- 执行者角色行补充：本地已有仓库 checkout，合并推送由执行者负责。member add 执行者示例 role 改为 `executor`，与现有 5 个小队的实际花名册一致。

## 2026-09-09 — coordinator-leader-structure

- 结构性调整：队长 = 协调者，统一 CCGlm5.3Flash（RollieCC），不写代码；执行者 + reviewer 一律当成员（member add --role member / --role reviewer）。执行者绝不能当队长——daemon 对队长任务不复用 PriorWorkDir，CLI 类 agent 会话按 cwd 存，队长当执行者会每轮丢会话（MIA-429/MIA-406 结论）。
- 小队 instructions 模板整体改为「协调者契约」：新增委派流程（@执行者派活并原文转述开发规则 → 执行者报完成 → @reviewer → P1 循环修复 → review 通过后由执行者合并推送 origin/xisheng）。
- squad 去重键更新为 协调者+执行者+reviewer(+planner) 组合一致；输入确认里协调者是默认项（现查不到该 agent 时问用户，不许猜）。
- 小队命名规则不变（执行者+reviewer，不含协调者）；示例更新 Gemini3.7Flash → Gemini3.8Flash。

## 2026-08-31 — plan-first-and-openspec

- 新增「方案先行」硬要求（写入小队 instructions 模板）：动手开发前必须先在 issue 评论里同步方案；关键方案文件（Markdown/HTML 等）必须作为附件上传到对应 issue；真正的大功能走仓库 OpenSpec 流程，普通改动也必须有方案同步，不许闷头就写。
- planner 停下等审规则并入「方案先行」章节，角色分工 planner 行改为引用该章节。
- 修正 agent create 命令示例里残留的旧命名 `{harness} build {model}`，改为与命名规则一致的驼峰无空格格式。
- 已推送更新后的 instructions 到 5 个现存小队。

## 2026-08-30 — independent-reviewer-and-thinking-in-name

- 硬约束：reviewer 必须是独立 agent（独立会话）——执行者与 reviewer 不得是同一 agent，同配也要建第二实例（名字加 -2 杠二），否则 review 上下文不独立。
- Codex/GPT 系 thinking level 必须标在 agent 名字里（如 pkoCodexGPT5.6SolHigh），配置与名字一致；小队名同步带 thinking level。
- 实操记录：pkoCodexGPT5.6Sol 改名 pkoCodexGPT5.6SolHigh；新建 pkoCodexGPT5.6SolHigh-2（独立 reviewer）入第 5 队 role=Reviewer；5 个小队名同步更新。

## 2026-08-30 — compact-naming-no-spaces

- agent 名和小队名一律整体无空格、驼峰紧凑：agent = pko 前缀 + harness 名 + 模型名（例 pkoAntiGemini3.7Flash、pkoCodexGPT5.6Sol、pkoGrokBuildGrok4.6）；同名冲突加机器短名（pkoCodexGPT5.6SolImac）。
- 小队名默认规则同步改紧凑：{执行者模型名}（执行者）{reviewer模型名}（Reviewer），planner 追加（Planner）。

## 2026-08-30 — fix-build-is-grok-only

- 修正 agent 命名规则的错误表述：明确"Build" 只是 Grok harness 的专有名字（Grok Build），不是通用连接词；其他 harness（Antigravity / Pi / Trae / Kiro / Codex 等）直接写原名，不要硬加 Build。

## 2026-08-30 — generic-squad-and-default-name

- 引导流程去掉"目标 issue"：小队是通用资源，不把 issue 绑进小队定义；派活是独立后续动作。
- 新增小队名默认规则：{执行者模型名}（执行者） {reviewer模型名}（reviewer），涉及 planner 再追加 {planner模型名}（planner）；用户给了名字就用用户的。

## 2026-08-30 — fix-naming-and-add-interview-flow

- 修正 agent 命名理解：`{harness} build {model}` 是错的——"Grok Build" 本身就是 harness 的全名，"Build" 不是连接词。命名 = harness 全名 + 模型名（例：Grok Build Grok 4.6）。
- 新增引导流程：用户没给全（执行者/reviewer 的 harness+模型、planner 与否、目标 issue、小队名）时必须一次性问齐，不许猜；仅机器（默认当前对话机器）和 planner（未提不设）可默认。

## 2026-08-30 — initial-release

- 首次发布：为赵锡盛组建临时 Rollica 开发小队的一体化流程 skill。
- 关键行为：agent 去重键 = harness+模型+机器（命名 "{harness} build {model}"，冲突加机器后缀）；agent instructions 一律留空，开发规则由小队 instructions 承载（只进队长 briefing，靠队长委派时转述）；squad 去重键 = 队长+reviewer(+planner) 组合一致；名单每次现查，禁止本地持久名单；planner 方案必须停下等赵锡盛人工审（评论+waiting_on+blocked）。
- 已知风险：squad create / member add / 指派 issue 会触发 leader 任务，仅限用户明确要求时执行。
