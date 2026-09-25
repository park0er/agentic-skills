---
name: mify-model-gateway
description: Use when working with 小米 Mify Gateway (`api.llm.mioffice.cn`) — installing API keys, listing/testing models, diagnosing 400 "Not supported model", recommending Mify LLMs, checking 1M context, wiring Mify into Claude Code, or configuring Claude Desktop Cowork 3P including the local proxy option for non-Claude models. Also fires on 公司大模型网关 / 挂到桌面版 Claude. Skip for direct OpenAI / Anthropic / Google calls.
---

# Mify 大模型网关查询

## 背景

Mify (`api.llm.mioffice.cn`) 是小米公司的大模型统一网关，**OpenAI 兼容接口**，聚合了 13 条上游通道（`tongyi` / `azure_openai` / `siliconflow` / `volcengine_maas` / `ppio` / `xiaomi` / `zhipuai` / `baidu_qianfan` / `wenxin` / `hunyuan` / `minimax` / `vertex_ai` / `cloudml`）。完整说明见 `references/owner_guide.md`。

**同一个模型 id 可能出现多次，`owned_by` 不同**，背后是不同供应商的推理服务，计费/SLA/稳定性都不同。推荐优先级见 owner_guide.md。

### 调用格式（最重要的 Mify 约定）

**`/v1/chat/completions` 的 `model` 参数必须是 `{owned_by}/{id}` 形式，裸 id 一律 HTTP 400。**

因为同一个 id 在不同 owner 下都存在（如 `kimi-k2.5` 同时在 `xiaomi` 和 `tongyi` 下），网关用裸 id 无法路由。必须显式带 owner 前缀：

| ✗ 错误（会 400） | ✓ 正确 |
|---|---|
| `kimi-k2.5` | `xiaomi/kimi-k2.5` 或 `tongyi/kimi-k2.5` |
| `DeepSeek-R1-0528` | `xiaomi/DeepSeek-R1-0528` |
| `gpt-5` | `azure_openai/gpt-5` |
| `moonshotai/Kimi-K2-Thinking` | `siliconflow/moonshotai/Kimi-K2-Thinking` |

注意最后一行：即使原 id 本身已经带 `moonshotai/` 前缀，Mify 调用时还是要在最外层再加 owner，变成 `siliconflow/moonshotai/...`。不要自己省略。

`list_models.py` 的输出里有一列叫 **CALL AS**，列出的字符串是**可以直接复制到 `model` 参数里的**，永远照抄那一列。

### list endpoint vs chat endpoint 的语义差异

- `/v1/models` 返回网关**配置里挂了**的所有模型（约 450 条），反映「公司网关是否集成了 X」。
- `/v1/chat/completions` 是实际调用路径，**model 必须带 owner 前缀**（见上）。

绝大多数 key 对所有通道都开放，`test_model.py` 对列表里任意 `owner/id` 基本都会返回 200。如果 400 且是 "Not supported model"，99% 的情况是**你忘了 owner 前缀**，少数情况是 owner 名拼错或该通道对这个 key 不开放。

## 何时触发

主要场景：

1. **可用性查询**：「公司网关支不支持 X 模型？」「Mify 上有没有 kimi-k2.6？」「DeepSeek-V3.2 在不在？」
2. **清单筛选**：「公司的 embedding 模型有哪些？」「我要找 TTS 模型」「列出 xiaomi 自建的所有 LLM」
3. **调用验证**：「帮我测一下 X 模型能不能调通」「我写的代码一直 404，是不是模型 id 写错了？」
4. **版本比较**：「Mify 上 Qwen 最新版本是多少？」「Kimi 各版本有哪些？」
5. **通用推荐**：「推荐个性能强的模型」「哪个模型又快又强」「适合 RAG 的 LLM 选哪个」「国产里最好的大模型」—— 这种开放问题也触发本 skill，因为需要**业界榜单 × 公司可用性**的交叉判断，不能拍脑袋。
6. **落盘 Claude Code 配置**：「把 `xiaomi/kimi-k2.5` 设成我的 Claude Code 模型」「用 Mify 的 Kimi 跑 Claude Code」「切 Claude Code 到 ppio 那个 claude-opus-4-7」。调 `set_cc_model.py` 改 `~/.claude/settings.json` 的 Haiku/Sonnet/Opus 三档 env 变量之一。**每次推荐完模型后都应主动 offer 一句**「要不要直接在 Claude Code 配置里切过去试试？」

如果用户贴出了一段 `curl api.llm.mioffice.cn` 的命令 —— 无论是问 models 列表、调 chat completion，还是 embedding —— 都应直接用本 skill 的脚本替代裸 curl，**不要重新抄一遍 curl 命令**。

## 前置条件

脚本从环境变量 `$MIFY_API_KEY` 读取 token。如果未配置，`list_models.py` / `test_model.py` 会报错并退出 1：

```
Missing $MIFY_API_KEY. Run:
  export MIFY_API_KEY=sk-...
and re-run this command.
```

### 用户还没配 token 时该怎么引导

如果遇到这个错误，**不要直接帮用户 `export` 完事** —— 那只在当前 session 生效，换个 shell 就没了。也**不要**让用户自己 mkdir / chmod / 改 zshrc —— 那是繁琐体力活。

正确流程：**让用户把 key 贴进对话，你调 `install_token.py` 一键安装**。

#### 一键全局安装与更新协议（当用户贴出新 key、要求更换 key 或初次安装时触发）

判断：用户发送了一个以 `sk-` 开头、长度在 20-200 之间的字符串，且没有明显非 key 语义，或明确要求更换/更新网关 key 时，**必须执行一键全局安装，将该 Key 覆盖同步至所有活动组件**，防止各组件之间出现密钥漂移与失效。

##### 执行步骤：

1. **第一步：环境凭据落盘与校验**
   使用 `printf %s` 将 Key 传递给一键安装脚本（**必须用单引号包裹 Key**，防止 shell 特殊字符被解析）：
   ```bash
   printf %s '<KEY>' | python3 ${SKILL_DIR}/scripts/install_token.py
   ```
   *该脚本会自动验证 Key 有效性并将其写入 `~/.config/mify/credentials`（chmod 600）。*

2. **第二步：更新 Launchd 系统级活动环境变量**
   为了使桌面端/GUI 应用程序（例如 Claude Desktop）在不重启电脑的情况下能立即获取新 Key，向 launchd 写入活动环境变量：
   ```bash
   launchctl setenv MIFY_API_KEY '<KEY>'
   ```

3. **第三步：同步更新 Claude Code 配置文件**
   检查并修改 `~/.claude/settings.json`，将其中的 `"env"` 对象下的 `"ANTHROPIC_AUTH_TOKEN"` 字段更新为新的 `<KEY>`。

4. **第四步：清理并同步 Claude Desktop 历史配置**
   若文件 `~/Library/Application Support/Claude-3p/claude_desktop_config.json` 存在，检查并将其中的 `"enterpriseConfig"` -> `"inferenceGatewayApiKey"` 更新为新的 `<KEY>`。

5. **第五步：同步更新 Codex 配置文件**
   若文件 `~/.codex/config.toml` 存在，将其中的 `[shell_environment_policy.set]` 下的 `"ANTHROPIC_AUTH_TOKEN"` 更新为新的 `<KEY>`。
   *提示：在此步中，建议顺手检查并更新其 `ANTHROPIC_DEFAULT_OPUS_MODEL` 和 `CLAUDE_CODE_SUBAGENT_MODEL` 的版本（如升级到最新推荐的 `ppio/pa/claude-opus-4-8[1m]` 等），确保模型与代理版本高度一致。*

6. **第六步：重启本地 Proxy 代理服务**
   重启本地桌面代理服务，使其运行在完全清爽的新 Key 环境中：
   ```bash
   python3 ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py restart
   ```
   *重启后访问 `http://localhost:41414/healthz` 接口，以确保代理服务完全健康。*

7. **第七步：反馈与最终清理**
   - 检查并反馈是否有任何未尽位置依然残留旧 Key（可通过 `grep -rn "sk-OLD..."` 进行定向局部排查）。
   - 指引用户：如果在当前终端继续操作，请执行 `source ~/.config/mify/credentials` 刷新当前 Shell 缓存；若使用 Claude Desktop App，请完全退出 (Cmd+Q) 并重新打开以激活新配置。

##### 异常处理（脚本返回非 0）：
- `HTTP 401/403`：Key 无效 or 已吊销，让用户重新拿一个。
- `Cannot reach ...`：用户没在小米内网/VPN 上，让他先连通再重试。
- `Key does not look right`：用户可能贴进了乱码或半截 Key，让其重新复制。
- 失败时**不要**把坏 Key 写进任何文件。

#### 传统手动方式（只在一键失败或用户明确要求手动时）

让他读 `references/setup_token.md` 的「方式 2 独立 secrets 文件 + zshrc source」。文档覆盖了 fish 等非 zsh/bash shell 的情况。

**关键安全规则**（对你和用户都适用）：

- ✓ Token 可以放在用户本人的 `~/.config/mify/credentials`（chmod 600）或类似的本地 secrets 文件 —— 这是持久化的正确姿势。
- ✗ 禁止把 token 写进 **skill 目录**（SKILL.md、scripts/、references/ 等）、**项目源码**、**workspace 输出**、**commit/PR/issue**、或任何可能被打包/同步/分享的地方。
- ✗ 若用户在对话里直接贴了 token，**不要** echo 到 log、不要写进文件落盘（除了用户自己的 `~/.config/mify/credentials`）。指引他走方式 2。

Token 长啥样：约 50 字符，前缀 `sk-`。

## 标准工作流

### Step 1: 拿到最新列表或按需过滤

先尝试用关键字筛选而不是拉全量。450 多个模型，全量 response ≈38KB，直接塞进对话会浪费上下文。

```bash
# 按关键字（大小写不敏感，子串匹配）
python ${SKILL_DIR}/scripts/list_models.py --grep kimi

# 按模型类型（注意 embedding 类型名是 text-embedding，带连字符）
python ${SKILL_DIR}/scripts/list_models.py --type text-embedding

# 按 owner
python ${SKILL_DIR}/scripts/list_models.py --owner xiaomi --type llm

# 组合过滤
python ${SKILL_DIR}/scripts/list_models.py --grep qwen --type llm --owner xiaomi

# 需要结构化时用 JSON 输出
python ${SKILL_DIR}/scripts/list_models.py --grep kimi --json
```

如果用户确实需要总览（很少见），再用 `--all`：

```bash
python ${SKILL_DIR}/scripts/list_models.py --all --summary
```

`--summary` 会打印「总数 + 按 type 分布 + 按 owner 分布」三行聚合结果，不会 dump 450 条 id。

### Step 2: 解读结果

对命中结果做三件事：

1. **去重同 id**：同一个模型 id 可能出现多次 owner，脚本默认会按 id 聚合并把所有 owner 列在一起。
2. **给出明确结论**：回答用户的原始问题时，**第一句就是结论**（「支持」/「不支持」/「部分支持」/「只有旧版本」）。
3. **推荐首选 owner**：当同一个 id 有多个 owner 时，按下面优先级推荐：

   ```
   xiaomi > tongyi > volcengine_maas > ppio ≈ siliconflow > 其他
   ```

   理由：xiaomi 自建成本最优、稳定性最好、合规最稳；tongyi / volcengine_maas 是国内大厂 maas，SLA 有保障；siliconflow / ppio 是第三方聚合，作为兜底。

### Step 3 (可选): 调用验证

当用户明确想「验证能不能调通」或怀疑网关问题时，对 LLM 类型的模型发一个最小 chat completion。**传进去的 `--model` 必须是 `{owner}/{id}` 格式**（从 list_models 的 CALL AS 列复制）：

```bash
python ${SKILL_DIR}/scripts/test_model.py --model xiaomi/kimi-k2.5

# 换条通道验证
python ${SKILL_DIR}/scripts/test_model.py --model tongyi/kimi-k2.5

# 自定义 prompt
python ${SKILL_DIR}/scripts/test_model.py --model xiaomi/DeepSeek-R1-0528 --prompt "用一句话介绍你自己"
```

脚本会打印 HTTP 状态码、响应时延、token 用量、首段回复。常见错误码含义：

- `400 "Not supported model"`: 99% 是忘了 owner 前缀（`kimi-k2.5` → `xiaomi/kimi-k2.5`）；其次是 owner 名拼错。脚本的 hint 会根据 `--model` 是否含 `/` 给出对应提示。
- `401`: `$MIFY_API_KEY` 过期或失效
- `429`: 速率限制（该 owner 通道配额打满），换 owner 试试
- `503`: 上游挂了，换个 owner

**⚠️ 只对 `model_type=llm` 的模型调用 `test_model.py`**。Embedding / rerank / TTS / ASR 走的是不同 endpoint，脚本不支持，请在回答里明确提示用户这类模型需要手测。

### Step 4 (可选): 通用推荐 — AA 榜单 × Mify 可用性

当用户问「推荐个模型」「哪个又快又强」「最适合 X 的模型」时，不要拍脑袋 —— 参考 [Artificial Analysis Intelligence Index](https://artificialanalysis.ai/#intelligence) 的今日榜单（业界独立基准，每天更新），再交叉 Mify 可用性给推荐。

#### 拉榜单

AA 官方 API 现在需要 API key（`x-api-key` header）。`fetch_aa_rankings.py` 默认是 `--source auto`：

- 如果环境里有 `AA_API_KEY` 或 `ARTIFICIAL_ANALYSIS_API_KEY`，优先走官方 `https://artificialanalysis.ai/api/v2/llms/models`。
- 如果没有 key，或 API 临时失败，则回退到公开 leaderboard 页面的 Next.js payload 抓取（无需 key）。
- 想强制不用 key 路径：加 `--source page`；想强制验证官方 API：加 `--source api`。
- 不要把 AA key 写进 skill 目录、项目源码或仓库；只放环境变量或本地 secrets 文件。

```bash
# 今日 top 15（reasoning + non-reasoning 都在；按 intelligence 降序）
python ${SKILL_DIR}/scripts/fetch_aa_rankings.py --top 15

# 看上下文窗口（加 Ctx 列，用于评估模型的 context 能力）
python ${SKILL_DIR}/scripts/fetch_aa_rankings.py --top 10 --context

# 只要启动快（非 reasoning，TTFT 低）的 top 10
python ${SKILL_DIR}/scripts/fetch_aa_rankings.py --no-reasoning --top 10

# 合规/数据出境敏感：只看中国模型
python ${SKILL_DIR}/scripts/fetch_aa_rankings.py --country cn --top 10

# 强制刷新今日缓存（默认每天自动 refresh 一次）
python ${SKILL_DIR}/scripts/fetch_aa_rankings.py --refresh --top 15

# 强制走公开页抓取（无 AA API key 时的稳妥定时任务配置）
python ${SKILL_DIR}/scripts/fetch_aa_rankings.py --source page --refresh --top 15

# 强制走官方 API（需要 AA_API_KEY 或 ARTIFICIAL_ANALYSIS_API_KEY）
python ${SKILL_DIR}/scripts/fetch_aa_rankings.py --source api --refresh --top 15
```

表格里列：rank / IQ（intelligence index，`~` 前缀代表 estimated 分数）/ R 列（Y = reasoning 模型，thinks before replying，**TTFT 慢**）/ Cty（US/CN/...）/ Vendor / 模型名 / 发布日期。

#### 推荐三步走

1. **拿业界榜**：`fetch_aa_rankings.py --top 15`（或加 `--no-reasoning` / `--country cn` 根据用户需求过滤）
2. **查网关可用**：对榜单上每个候选 id（label 或 slug）跑 `list_models.py --grep <name>` —— AA 叫 "Kimi K2.6"，网关里可能是 `kimi-k2.6` 或 `tongyi/kimi-k2.6` 这种路径形式；用模糊匹配。
3. **给结论**：
   - 指出 top 业界榜的前 N 名
   - 逐条标注「Mify 已接入 ✓」/「Mify 未接入 ✗ → 业界最新 X 版本 Mify 还没跟上」
   - 针对用户的偏好（性能 / 启动速度 / 成本 / 合规）从可用交集里挑首选

#### 如何回应「性能强 + 启动快」

用户说「启动快」通常指**首 token 延迟（TTFT）低**。reasoning 模型要先内部 think 一段，TTFT 明显比非 reasoning 慢。策略：

- 用 `--no-reasoning --top 10` 先过滤出「非 reasoning 但 IQ 仍高」的候选
- 但**别假装 reasoning 模型不能用**：它们 IQ 普遍高出 5-15 分，如果用户实际需求是单轮问答且延迟敏感，非 reasoning 是对的；但如果是复杂推理，reasoning 的精度提升往往值得那几秒等待 —— 把权衡讲给用户。

#### 如何回应「国产最好」「不出境」

直接 `--country cn --top 15`。当前榜单前列的国产（不完整）：
- Moonshot Kimi K2.6（小米网关里可能还是 K2.5）
- Alibaba Qwen3.6 Max / Plus
- Z AI GLM-5.1 / GLM-5
- MiniMax M2.7
- **Xiaomi MiMo-V2-Pro**（自家模型，可以特别提一下，但 IQ 低于前几个）
- DeepSeek V3.2

#### 如何回应「AA 榜上没有的模型」

AA 只跑它收录的那批（~200 条主流模型）。MiMo / MiLM 的某些变体、一些小众聚合版本可能不在。如果 `list_models.py` 返回某模型但 `fetch_aa_rankings.py` 里找不到，**明确说「AA 未收录该模型，无法给出业界分数定位」**，而不是瞎推测。

#### 榜单 vs 实际体验

AA 的 Intelligence Index 是多个 benchmark 的加权平均（HLE, GPQA, tau2, omniscience 等）。它对**同质化任务（学术问答、代码生成、推理）**的评估比较准；对**工程落地（tool call、长上下文 retrieval、RAG 稳定性）**的体现有限。推荐时要加这句 caveat，别把 IQ 数字当成绝对真理。

### Step 5 (可选): 把选中的模型写入 Claude Code 配置

用户说「把 X 设成我的 Claude Code 模型」或你刚做完推荐、要顺势 offer「直接落盘」时，走这里。脚本写的是 user-level 的 `~/.claude/settings.json`，影响的是 Claude Code 在本机的默认模型。

#### 关键事实（不然会踩坑）

- Mify 网关的 `https://api.llm.mioffice.cn/anthropic` 路径**原生支持 Anthropic 协议**，Claude Code 不需要 claude-code-router 之类的中间层。
- Claude Code 按「三档」查模型：`ANTHROPIC_DEFAULT_HAIKU_MODEL`（小/便宜）/ `ANTHROPIC_DEFAULT_SONNET_MODEL`（默认）/ `ANTHROPIC_DEFAULT_OPUS_MODEL`（大/贵）。**每档独立**，切一档不影响另外两档。
- 模型 id 依然要写 `{owner}/{id}`（如 `xiaomi/kimi-k2.5`），裸 id 会 400。

#### 一键落盘流程（**禁止绕过 dry-run**）

```bash
# 先 dry-run 看 diff（永远先来这步）
python ${SKILL_DIR}/scripts/set_cc_model.py --model xiaomi/kimi-k2.5 --tier sonnet --dry-run

# 用户看完 diff 点头后，去掉 --dry-run 真写
python ${SKILL_DIR}/scripts/set_cc_model.py --model xiaomi/kimi-k2.5 --tier sonnet

# 一次切多档
python ${SKILL_DIR}/scripts/set_cc_model.py --model xiaomi/kimi-k2.5 --tier haiku,sonnet

# 三档全改
python ${SKILL_DIR}/scripts/set_cc_model.py --model xiaomi/kimi-k2.5 --tier all

# 翻车或改了后悔，立即还原
python ${SKILL_DIR}/scripts/set_cc_model.py --revert
```

脚本每次真写都会：拉 Mify 现货列表预检 → 备份原 settings.json 到 `settings.json.bak.YYYYMMDD-HHMMSS` → 写新文件 → 向 `/anthropic/v1/messages` 发一条最小消息做 smoke test → 失败自动 revert。所以最差结果就是「切换失败、原配置保留」，永远不会把用户的 settings.json 搞坏。

#### 决定用户想切哪一档

用户如果没明确说，先问一句：

- **Haiku**（便宜快）→ 后台/自动化/subagent 用。
- **Sonnet**（默认）→ 日常对话大部分场景走这档。
- **Opus**（大而慢）→ 复杂推理 / 长文理解 / agent 编排。
- **all**（三档一起）→ 想完全切到一个模型、不在乎档位分工。

例：用户说「用 Kimi 跑 Claude Code」但没指定档位 → 问「想把 Kimi 挂在哪个档？Sonnet（默认对话）还是 Opus（大任务）？都挂就选 all。」

#### 兼容性与非 Mify 配置

脚本**只在必要时**才修 `ANTHROPIC_BASE_URL` 和 token：
- URL 没设 → 自动填成 Mify 的 `https://api.llm.mioffice.cn/anthropic`。
- URL 已经指向 Mify → 一个字都不动。
- URL 指向别的服务（如 Anthropic 直连）→ **拒绝覆盖**，要用户明确加 `--force-url` 才会改。
- `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY` 只要有其一就不动；都没有才从 `$MIFY_API_KEY`（或 `~/.config/mify/credentials`）补上。

也就是说，**你只改模型字段，不会动用户任何其他 Claude Code 配置**。

#### Smoke test 常见信号

- `HTTP 200 (empty reply — OK, pipeline works)`：通道通了，reasoning 模型在 `max_tokens=32` 下很可能没有 user-facing 输出，这是正常的，算通过。
- `HTTP 200, reply: 'hi!'`：最理想情况，模型能立即产出内容。
- `HTTP 4xx/5xx`：脚本已经自动 revert，把 stderr 里那行 HTTP 错误截屏或复述给用户作为诊断依据（403/404 基本是 token 对该 owner 通道没开放；400 基本是 id/owner 拼错）。

#### 写完之后必须提醒的两件事

1. **重启 Claude Code**：当前正在运行的 Claude Code 进程读的是启动时的 settings.json，改完后要**关掉重开一个新终端**才生效。
2. **想回到原样**：一行 `set_cc_model.py --revert` 即可。

#### 跟推荐场景联动（主动 offer 模式）

当你刚在 Step 4 给出了一个推荐（哪怕只是回答「Kimi K2.5 又快又便宜」），**主动**加一句：

> 要不要我帮你在 Claude Code 配置里把 Sonnet 档切过去试试？一条命令就能切，也能一键还原。

**不要**自己默默写入。一定要走 `--dry-run` 给用户看 diff，得到确认之后再真写。

#### 配置完成后：主动 offer 上下文窗口标记

**当 `set_cc_model.py` 成功写入模型后，紧接着主动问一句**：

> 要不要顺便查一下这个模型的上下文窗口大小？如果支持 1M tokens，我会加上 `[1M]` 标记，
> 这样 Claude Code 能感知到模型的完整上下文能力，不会过早压缩对话。

等用户确认后，再跑 `tag_context.py`。这个 offer 的价值：用户可能不知道 Claude Code 会因为不知道模型上下文窗口大小而过早压缩对话，加了标记后对话体验更完整。

**注意**：`[1M]` 是 Claude Code 专属标记，Claude Code 发请求前会自动剥离。这个功能仅适用于 Claude Code 配置，不适用于 OpenCode 等其他客户端。

### Step 5.5 (可选): 上下文窗口标记

`tag_context.py` 读取 settings.json 中的三档模型，查 AA 上下文窗口数据，对支持 >= 1M tokens 的模型自动加 `[1M]` 标记。

#### 为什么需要这个标记

Claude Code 根据模型名中的 `[N]` 后缀感知上下文窗口大小。没有标记时，Claude Code 可能使用默认的较小窗口阈值，在对话还没到模型实际容量时就开始压缩——白白浪费了大上下文的能力。

目前只确认 `[1M]` 格式被 Claude Code 正确识别。其他大小（如 `[256K]`）未经验证，暂不支持。

#### 用法

```bash
# 查看哪些模型需要加标记（默认就是 dry-run，不会写文件）
python ${SKILL_DIR}/scripts/tag_context.py

# 确认无误后，加 --apply 真正写入
python ${SKILL_DIR}/scripts/tag_context.py --apply

# 强制重新拉 AA 数据（默认用当天缓存）
python ${SKILL_DIR}/scripts/tag_context.py --refresh

# 去掉所有 [1M] 标记（还原）
python ${SKILL_DIR}/scripts/tag_context.py --remove
```

#### 工作流

默认模式就是 dry-run，输出类似：

```
Context window analysis:
  · HAIKU:  xiaomi/mimo-v2.5-pro[1m]       (already tagged, context: 1,000,000 tokens)
  + SONNET: ppio/pa/claude-sonnet-4-6 -> ppio/pa/claude-sonnet-4-6[1M]  (context: 1,000,000 tokens >= 1M)
  + OPUS:   ppio/pa/claude-opus-4-7 -> ppio/pa/claude-opus-4-7[1M]      (context: 1,000,000 tokens >= 1M)
```

把结果展示给用户，确认后再加 `--apply`。脚本会自动备份 settings.json。

#### 匹配逻辑

脚本用三级匹配把 Mify 模型 id（如 `ppio/pa/claude-opus-4-7`）关联到 AA 数据：
1. **精确 slug 匹配**：`mimo-v2.5-pro` → AA slug `mimo-v2-5-pro`
2. **子串匹配**：normalized id 包含 AA slug 或反之
3. **模糊匹配**：AA shortName（如 "Claude Opus 4.7"）与 normalized id 对比

如果匹配不到，脚本会标记 `?` 并跳过，不会乱打标。

### Step 6 (可选): 把 Mify 挂到 Claude 桌面客户端（Cowork 3P 模式）

当用户想让 **Claude.app**（桌面客户端）走公司 Mify 网关时走这里。这和 Step 5 的 Claude Code CLI 是两个独立目标 —— 桌面 app 走 Cowork 3P 模式，有自己的 `Claude-3p/configLibrary` 配置链路。

#### 核心事实（不然会踩坑）

- **2026-05-07 之后的 Claude Desktop 1.6259.x 逻辑已经变了**：本地用户配置的官方路径是 `~/Library/Application Support/Claude-3p/configLibrary/`，由 `_meta.json` 的 `appliedId` 指向当前 active 的 `<uuid>.json`。旧版 skill 写 `~/Library/Preferences/com.anthropic.claudefordesktop.plist` 的方式不再作为主路径使用。
- Claude Desktop 的 gateway `inferenceModels` 现在会校验为 **Anthropic/Claude 模型路由**。Mify 里的 Kimi / Qwen / GPT / MiMo / DeepSeek 等非 Claude 模型仍然可以给 Claude Code 用，但不能直接塞进 Claude Desktop Cowork 3P 的模型列表；否则 app 会进入 degraded 状态并报 `configured model "... " is not an Anthropic model`。
- **如果用户想在 Claude Desktop 里用非 Claude 模型，必须先明说边界并征得同意**：官方路径只支持 Claude/Anthropic 路由；可选绕法是在本机启动 loopback proxy，让 Desktop 看到 `xisheng/claude-*` 这类 Claude 风格模型名，proxy 再把请求改写到真实 Mify 模型（如 `xiaomi/mimo-v2.5-pro`）。本地 proxy 默认使用 `http://localhost:<port>`，避免 Electron 对自签 localhost 证书报 `ERR_CERT_AUTHORITY_INVALID`；如用户明确需要，也可用 `--scheme https`。这是工程绕法，不是官方承诺，未来 Desktop 可能继续加强校验。
- **Claude Desktop proxy 与 Claude Code 配置完全分开**：Claude Code 可直连 Mify Anthropic endpoint，也可将 `ANTHROPIC_BASE_URL` 指向本地 proxy（127.0.0.1:41414）获得裸 Claude 模型名自动改写能力（Paseo 等工具需要）。`set_cc_model.py` 认得 proxy URL，切模型时不会误拒。
- 配置写入后 **Claude.app 启动时只读一次**；已经在运行的 app 要完全退出再打开才生效。
- `configLibrary/<uuid>.json` 是原生 JSON：布尔用 `true`，数组用 JSON array，`inferenceModels` 用 `[{ "name": "...", "supports1m": true }]` 这种对象列表。只有 MDM / plist 路径才需要把数组序列化成 JSON 字符串。
- Mify 当前 `https://api.llm.mioffice.cn/anthropic/v1/messages` 可用，但 `https://api.llm.mioffice.cn/anthropic/v1/models` 返回 400；所以短期内仍要显式写入 `inferenceModels`，不能完全依赖 Claude 的 gateway model discovery。
- Claude Desktop 实际会调用带 query 的路径，例如 `/v1/messages?beta=true` 和 `/v1/messages/count_tokens?beta=true`。本地 proxy 只用 route path 决定哪些 endpoint 要特殊处理（`/v1/models` 本地 model discovery、`*/count_tokens` 本地 token 估算），**模型改写不要绑死到某一个 endpoint**：任何 `/v1/*` JSON POST 只要 top-level `model` 命中映射表或带 `[1M]` 标签，都先 normalize/改写再转发。

#### 三阶段工作流

**Phase A — Pre-check：Claude Desktop 是否装了**

先跑 `check_claude_desktop.py`。脚本用 Spotlight 的 bundle-identifier 查询 + 几个 fallback 路径，找到就返回 path + version；没找到就 exit 1 + 提示可选安装方式。

```bash
python ${SKILL_DIR}/scripts/check_claude_desktop.py          # 只 detect
python ${SKILL_DIR}/scripts/check_claude_desktop.py --json   # 机器可读
```

**Phase B — 如果未装：引导安装（三选一，让用户拍板）**

不要默默帮用户装 app（即使 Homebrew 可行也别默认）—— 问用户偏好哪条路：

| 路径 | 命令 | 适用 |
|---|---|---|
| Homebrew（0-click） | `python ${SKILL_DIR}/scripts/check_claude_desktop.py --install-brew` | 用户有 brew，想一键装好（cask 可能比官网慢几个版本） |
| 打开官方下载页 | `python ${SKILL_DIR}/scripts/check_claude_desktop.py --open-download` | 用户没 brew，或想要最新版；**需要用户手动拖到 Applications** |
| 跳过 | — | 用户说"我先不装，以后再配" |

**关键交互**：如果走"打开下载页"路径，用户 DMG 下完 + 拖到 Applications 是个异步动作，AI **无法轮询**。你要告诉用户：

> 装好后在对话里说一句「装好了」/「installed」/「done」，我再帮你走下一步。

用户说"装好了"后，**一定要先重跑 `check_claude_desktop.py` 确认真的装上了**（防止用户误以为装好了但 DMG 其实没拖成功）；确认 ✓ 后再进入 Phase C。

**Phase C — 先让用户选择 Desktop 模式**

进入写配置前，必须先告诉用户：

> Claude Desktop 3P 官方/稳定路径只支持 Claude/Anthropic 系列模型路由。  
> 如果你只想用 Mify 上的 Claude 路由，我会直接写 4 个 PPIO Claude routes。  
> 如果你想在 Desktop 里用 MiMo / Kimi / Qwen / DeepSeek 等非 Claude 模型，需要本机起一个 loopback proxy：前台给 Desktop 看 Claude 风格名字，后台转发到真实 Mify 模型。这个方案默认走 `http://localhost:<port>`，只绑定 `127.0.0.1`，可避开 Electron 自签证书信任问题；它可用，但属于工程绕法，未来 Desktop 可能加强校验。

然后问用户一句：

> 你要走「官方 Claude routes 直连」还是「本地 proxy + 非 Claude 模型映射」？

如果用户没明确同意 proxy，不要安装 proxy；只走官方 Claude routes。

**Phase C1 — 官方 Claude routes 直连（默认稳妥路径）**

```bash
# 先 dry-run 看 diff（永远先来这步，跟 Step 5 的 set_cc_model.py 一个套路）
python ${SKILL_DIR}/scripts/install_cowork_config.py

# 用户看完 diff 点头后，加 --apply 真写
python ${SKILL_DIR}/scripts/install_cowork_config.py --apply

# 查当前 configLibrary 状态
python ${SKILL_DIR}/scripts/install_cowork_config.py --verify

# 清掉 skill 写入的 gateway key（并清理旧 plist 残留）
python ${SKILL_DIR}/scripts/install_cowork_config.py --revert

# 只修复当前 profile 的模型列表，保留其他配置/历史数据/偏好
python ${SKILL_DIR}/scripts/install_cowork_config.py --fix-models
python ${SKILL_DIR}/scripts/install_cowork_config.py --fix-models --apply

# 显式测试新版 Claude Desktop 是否仍拒绝非 Claude 模型（不要用于默认生产配置）
python ${SKILL_DIR}/scripts/install_cowork_config.py --include-mimo-test
python ${SKILL_DIR}/scripts/install_cowork_config.py --include-mimo-test --apply

# 高级：使用 Mify 当前实时 Claude routes，而不是已验证的 4 个 baseline
python ${SKILL_DIR}/scripts/install_cowork_config.py --live-models
```

脚本会：
- 从 `$MIFY_API_KEY`（或 `~/.config/mify/credentials`）读 token；缺就报错让用户先跑 `install_token.py`
- 生成（或从 `~/.config/mify/cowork-deployment-uuid` 读）一个稳定的 `deploymentOrganizationUuid`，跨安装复用 —— telemetry 标签不跳变
- `inferenceModels` 默认使用已在本机验证 healthy 的 4 个 Claude routes：`ppio/pa/claude-opus-4-7` / `ppio/pa/claude-opus-4-6` / `ppio/pa/claude-sonnet-4-6` / `ppio/pa/claude-haiku-4-5`。这比实时 catalog 更保守，避免把未验证的新 route 写进生产 profile
- 如需探索 Mify 实时可用 Claude routes，可显式加 `--live-models`；这会从今日 Mify LLM catalog 里筛 `claude-*` 路由，按今日 AA `context_window` 数据动态刷新 `supports1m` 标记
- 如只需要修复已有用户 profile，优先用 `--fix-models`：它只替换 active JSON 和旧兼容 `claude_desktop_config.json` 里的 `inferenceModels`，保留其他配置、历史数据、偏好
- 如需验证社区说法，可显式加 `--include-mimo-test`，临时把 `xiaomi/mimo-v2.5-pro` 追加进 `inferenceModels`。这可能触发新版 Claude Desktop 的 `is not an Anthropic model` 错误，必须先看 dry-run，测试后回滚
- `coworkEgressAllowedHosts` 默认写 `["*"]`（全开放），Claude.app 内发起的网络请求不会被白名单卡。**不要默默改回保守值** —— 用户明确要求放开，保守默认曾经导致 Claude Desktop 内嵌搜索 / MCP HTTP / 预览等功能失败。只有用户显式要求锁域名时才用 `--egress-host api.llm.mioffice.cn`（可重复）覆盖
- 写入 `~/Library/Application Support/Claude-3p/configLibrary/<active-id>.json`，并维护 `_meta.json` 的 `appliedId`；如果发现旧 plist key，`--verify` 会提示，`--revert` 会清理
- 写完检测 Claude.app 是否在跑，在跑就提示完全退出再打开

**Phase C2 — 本地 proxy + 非 Claude 模型映射（用户明确同意后）**

默认 proxy 暴露 9 个 Desktop picker 模型：

| Claude Desktop 看到 | Mify 实际收到 | 行为 |
|---|---|---|
| `ppio/pa/claude-opus-4-8` | `ppio/pa/claude-opus-4-8` | 直通 |
| `ppio/pa/claude-opus-4-6` | `ppio/pa/claude-opus-4-6` | 直通 |
| `ppio/pa/claude-sonnet-4-6` | `ppio/pa/claude-sonnet-4-6` | 直通 |
| `ppio/pa/claude-haiku-4-5` | `ppio/pa/claude-haiku-4-5` | 直通 |
| `xisheng/claude-opus-4-8` | `minimax/MiniMax-M3` | MiniMax M3 (mify 直连) |
| `xisheng/claude-opus-4-7` | `deepseek/deepseek-v4-pro` | DeepSeek V4 Pro |
| `xisheng/claude-sonnet-4-6` | `xiaomi/mimo-v2.5-pro` | MiMo Pro |
| `xisheng/claude-haiku-4-5` | `xiaomi/mimo-v2.5` | MiMo V2.5 |
| `xisheng/claude-fable-5` | `zhipuai/glm-5.2` | GLM-5.2 (智谱直连) |

所有默认模型都标记 `supports1m: true`。Claude Desktop/UI 可能在模型名末尾附带 `[1M]` / `[1m]` 这类上下文标签；proxy 转发前必须先剥掉标签，再查映射表或直通 Mify。

安装流程：

```bash
# 先 dry-run：展示将写入的 Desktop config，不改系统
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py install

# 用户确认后，安装 loopback LaunchAgent、写 Claude Desktop config
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py install --apply

# 如 41414 被占用，脚本会自动选择 41415-41514 的空闲端口；也可显式指定
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py install --apply --port 41415

# 可选：如必须使用 HTTPS localhost，再显式打开；默认不推荐
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py install --apply --scheme https

# 查看 proxy / launchd / healthz 状态
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py status
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py status --port 41415

# 手动启动或重启
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py start
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py restart

# 停止或卸载 proxy
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py stop
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py uninstall
```

如果 `status` 显示该 skill 的 LaunchAgent `not loaded`，但 `healthz: ok`，说明这个端口上可能跑着用户已有的另一个本地 proxy；不要误判为本 skill 已经安装成功。此时应看 `base_url` 和 label，再决定是否沿用现有服务或用 `install --apply --port <free-port>` 新装一套。

自定义映射时，先让用户确认“前台给 Desktop 看的 Claude 风格名字”和“后台真实 Mify model id”，再追加 `--model-map external=upstream`：

```bash
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py install --apply \
  --model-map xisheng/claude-sonnet-4-6=xiaomi/mimo-v2.5-pro
```

约束：
- `external` 必须看起来像 Claude/Anthropic route（含 `claude` / `opus` / `sonnet` / `haiku` 等关键词），否则 Desktop 可能拒绝。`xisheng/claude-fable-5` 这种带 `claude` 关键词但非标准型号的名字也被接受（fable-5 仅作为 Claude 家族的家族 tier 兜底；不保证 Desktop 把它渲染成 Claude Opus）。
- `upstream` 必须是 Mify 真正可调用的 `{owned_by}/{id}`，例如 `xiaomi/mimo-v2.5-pro`；先用 `list_models.py --grep ...` 查可用性。
- `manage_claude_desktop_proxy.py install --apply` 会把 Desktop base URL 改成实际选中的 `http://localhost:<port>`，默认优先 `41414`；如果端口已被占用，会自动挑 `41415-41514` 的空闲端口，也可以由用户显式 `--port` 指定。不要在对外文档里假设所有用户都能用固定 `41414`。如用户明确要 HTTPS，可加 `--scheme https`，但 Electron health check 可能因为自签 CA 报 `ERR_CERT_AUTHORITY_INVALID`。
- Desktop config 的 `inferenceGatewayApiKey` 写成本地占位值；真实 Mify token 只由本机 proxy 从 `~/.config/mify/credentials` 读取。
- `/v1/messages/count_tokens?beta=true` 由本地 proxy 返回估算 token 数，不转发给 Mify；当前 Mify Anthropic route 不支持这个 token counting endpoint，直接转发会刷 400。
- 如果 Claude Desktop 内部偷偷请求 `claude-haiku-4-5-20251001`，proxy 默认把它映射回 `ppio/pa/claude-haiku-4-5`，避免 Desktop 背景探测造成无关 API error。
- 如果 PPIO 模型能用但 `xisheng/*` 报 API error，先看 `~/Library/Logs/mify-claude-desktop-proxy/proxy.err.log`：若出现 `Not supported model xisheng/...`，说明模型改写没有发生，通常是 JSON `model` 字段没有被解析/normalize；`xisheng` provider 名本身不是根因。

验证 proxy 真实路由：

```bash
# xisheng Opus 4.8 应返回 model=minimax-m3(mify 直连)
curl -s 'http://localhost:41414/v1/messages?beta=true' \
  -H 'content-type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  --data '{"model":"xisheng/claude-opus-4-8","max_tokens":16,"messages":[{"role":"user","content":"只回复 OK"}]}'

# xisheng Fable 5 应返回 model=glm-5.2(zhipuai 直连)
curl -s 'http://localhost:41414/v1/messages?beta=true' \
  -H 'content-type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  --data '{"model":"xisheng/claude-fable-5","max_tokens":16,"messages":[{"role":"user","content":"只回复 OK"}]}'

# token counting 应本地返回 input_tokens
curl -s 'http://localhost:41414/v1/messages/count_tokens?beta=true' \
  -H 'content-type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  --data '{"model":"xisheng/claude-opus-4-8","messages":[{"role":"user","content":"只回复 OK"}]}'

# PPIO 的 1M 标签应被剥离后直通
curl -s 'http://localhost:41414/v1/messages?beta=true' \
  -H 'content-type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  --data '{"model":"ppio/pa/claude-opus-4-8[1M]","max_tokens":16,"messages":[{"role":"user","content":"只回复 OK"}]}'
```

#### 可选能力：parko/* 模型（Trae 反扒通道，opt-in）

默认 proxy 只暴露 PPIO Claude 直通 + `xisheng/*` 映射的 9 个模型。如果你还想在 Claude Desktop 里用到 **Trae SOLO CN IDE 内置的免费模型**（GLM-5.2、MiniMax-M3 等），可以 opt-in 打开 `parko/*` 通道：proxy 把 `parko/` 开头的模型名改写成真实 Trae 模型名，再转发到本机 `http://127.0.0.1:8000` 的 Trae API 代理。

| Claude Desktop 看到 | Trae 实际收到 | 说明 |
|---|---|---|
| `parko/claude-opus-4-8` | `glm-5.2` | 智谱 GLM-5.2 |
| `parko/claude-sonnet-4-6` | `minimax-m3` | MiniMax M3 |

**前置依赖**：`parko/*` 依赖本机的 `trae-api-proxy` skill（监听 8000 端口）。这个 skill **不在公开渠道分发**（涉及 Trae 登录凭证反扒），需要找 **zhaoxisheng** 私下获取。

**开启流程**（用户明确想用 Trae 免费模型时走这里）：

1. 先确认用户意图：「你想在 Desktop 里加上 Trae 的 GLM-5.2 / MiniMax-M3 吗？这需要本机装 trae-api-proxy skill，没有的话得找 zhaoxisheng 要（这个 skill 不公开分发）。」用户点头才继续。
2. 安装时加 `--enable-parko`：
   ```bash
   python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py install --apply --enable-parko
   ```
   `install` 默认保留已有 opt-in 通道状态；如果 `kiro/*` 已启用，单独加 `--enable-parko` 不会关闭 Kiro。需要关闭 parko 时显式用 `--disable-parko`。
3. 脚本会自动处理 Trae 代理的就绪检查：
   - 先探测 8000 端口是否已有 Trae 代理在跑；在跑就直接加 parko 模型。
   - 若没跑但本机装了 `trae-api-proxy` skill → **直接调用该 skill** 的 `extract_credentials.py`（一键提取 Trae 登录凭证）+ `manage_service.py install`（装开机自启 LaunchAgent）把 Trae 代理拉起来，再继续。
   - 若本机**没装** `trae-api-proxy` skill → 打印引导「这个 skill 不公开分发，找 zhaoxisheng 要，装好后再重跑 `install --apply --enable-parko`」，并**不**把 parko 模型写进 Desktop 配置（避免用户选了用不了），只装基础 10 个模型。
4. Trae 代理就绪后 parko 模型才会写进 Desktop `inferenceModels`；`state.json` 会记录 `enable_parko` 状态，`status` / `configure-desktop` 后续都能正确还原。

**查看状态**：
```bash
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py status
# 会显示 parko: enabled/disabled + trae proxy (:8000): running/NOT running
```

**验证 parko 路由**（trae 代理在跑时）：
```bash
curl -s 'http://localhost:41414/v1/messages?beta=true' \
  -H 'content-type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  --data '{"model":"parko/claude-opus-4-8[1m]","max_tokens":16,"messages":[{"role":"user","content":"只回复 OK"}]}'
# 应转发到 127.0.0.1:8000，模型改写为 glm-5.2
```

**已知限制（必须告诉用户）**：
- Trae 的 `llm_raw_chat v2` 端点**不支持原生 tool use**（`tools` 字段被服务端忽略）。parko 模型做纯对话/补全没问题，但 **agentic tool calling 不可用**——需要工具调用的任务请用 PPIO Claude 直通或 `xisheng/*` 通道。
- Trae IDE token 约 14 天过期，过期后 parko 模型会 401；重开一次 Trae IDE 再跑 `~/.agents/skills/trae-api-proxy/scripts/trae-api-proxy/extract_credentials.py` + 重启 trae 代理即可。
- parko 模型同样带 `[1m]` 后缀，proxy 转发前会剥离；1M 上下文标记对 Trae 上游是否生效取决于 Trae 侧，不保证。

#### 可选能力：kiro/* 模型（Kiro Gateway 通道，opt-in）

如果你还想在 Claude Desktop / Claude Code 本地 proxy 里直接用本机 Kiro 登录态，可以 opt-in 打开 `kiro/*` 通道：proxy 把 `kiro/` 开头的 Claude 风格模型名改写成 Kiro Gateway 真实模型名，再转发到本机 `http://127.0.0.1:8001` 的 Anthropic `/v1/messages`。

| Claude Desktop 看到 | Kiro 实际收到 | 说明 |
|---|---|---|
| `kiro/claude-opus-4-8` | `claude-opus-4.8` | Kiro Opus 4.8 |
| `kiro/claude-sonnet-4-6` | `claude-sonnet-4.6` | Kiro Sonnet 4.6 |
| `kiro/claude-haiku-4-5` | `claude-haiku-4.5` | Kiro Haiku 4.5 |

**前置依赖**：`kiro/*` 依赖本机的 `kiro-gateway-proxy` skill（监听 8001 端口），该 skill 自带 patched `jwadow/kiro-gateway` 源码、LaunchAgent lifecycle 和 Anthropic `/v1/messages` 健康验证。

**开启流程**（用户明确想用 Kiro 通道时走这里）：

1. 先确认用户意图：「你想在这套 Mify 本地 proxy 里加上 Kiro 的 Opus/Sonnet/Haiku 吗？这会复用本机 Kiro 登录态，依赖 kiro-gateway-proxy skill 和 8001 端口。」用户点头才继续。
2. 安装时加 `--enable-kiro`：
   ```bash
   python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py install --apply --enable-kiro
   ```
   `install` 默认保留已有 opt-in 通道状态；如果 `parko/*` 已启用，单独加 `--enable-kiro` 不会关闭 Parko。需要关闭 Kiro 时显式用 `--disable-kiro`。
3. 脚本会自动处理 Kiro 代理就绪检查：
   - 先探测 8001 端口 `/health`；在跑就直接加 `kiro/*` 模型。
   - 若没跑但本机装了 `kiro-gateway-proxy` skill → 直接调用该 skill 的 `manage_service.py setup`，完成 bundled gateway 部署、依赖安装、LaunchAgent 开机自启和 Anthropic smoke test。
   - 若本机没装 `kiro-gateway-proxy` skill → 打印引导先安装/发布该 skill，并不把 `kiro/*` 模型写进 Desktop 配置。
4. Kiro 代理就绪后 `kiro/*` 模型才会写进 Desktop `inferenceModels`；`state.json` 会记录 `enable_kiro` 状态，`status` / `configure-desktop` 后续都能正确还原。

**查看状态**：
```bash
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py status
# 会显示 kiro: enabled/disabled + kiro gateway (:8001): running/NOT running
```

**验证 kiro 路由**（Kiro Gateway 在跑时）：
```bash
curl -s 'http://localhost:41414/v1/messages?beta=true' \
  -H 'content-type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  --data '{"model":"kiro/claude-opus-4-8[1m]","max_tokens":16,"messages":[{"role":"user","content":"只回复 OK"}]}'
# 应转发到 127.0.0.1:8001，模型改写为 claude-opus-4.8
```

**已知限制（必须告诉用户）**：
- Kiro token 来自本机 Kiro 登录态；过期时打开 Kiro 刷新 `~/.aws/sso/cache/kiro-auth-token.json`，再重启 `kiro-gateway-proxy` 或重跑 `install --apply --enable-kiro`。
- `kiro/*` 同样带 `[1m]` 后缀，proxy 转发前会剥离；1M 标记只是给 Claude Desktop/Claude Code 的选择器与上下文提示，不保证 Kiro 上游实际承诺 1M。
- Kiro 通道适合复用个人 Kiro 可用模型；公司 Mify Key 仍由 Mify 本地 proxy 读取，Kiro API key 只用于本机 8001 loopback。

#### 可选能力：openrouter/* 模型（OpenRouter 通道，opt-in）

本地 proxy 可以把 `openrouter/` 前缀的模型名路由到 OpenRouter（`https://openrouter.ai/api/v1`），并在转发时把 `openrouter/` 前缀剥掉，换成 OpenRouter 真实模型 id。OpenRouter 原生支持 Anthropic 协议 `/v1/messages`（实测 `stealth/ox-alpha` HTTP 200），所以 proxy 不需要做协议转换。

| Claude Code / Desktop 看到 | OpenRouter 实际收到 | 说明 |
|---|---|---|
| `openrouter/stealth/ox-alpha[1m]` | `stealth/ox-alpha` | 剥前缀 + 剥 `[1m]` 后直通 |

**前置依赖**：OpenRouter API key 写入 `~/.config/mify/openrouter-credentials`（chmod 600），或设 `OPENROUTER_API_KEY`。key **不写入** plist / settings.json / skill 源码。

**启用流程**（用户明确想用 OpenRouter 模型时走这里）：

1. 先确认用户意图：「要在这个本地 proxy 里加 OpenRouter 通道吗？比如用 `stealth/ox-alpha`。需要你的 OpenRouter API key（落盘 `~/.config/mify/openrouter-credentials`）。」用户点头才继续。
2. 写入 key：
   ```bash
   printf %s '<KEY>' | install_key # 或手动写文件
   ```
   直接手动：`printf %s '<KEY>' > ~/.config/mify/openrouter-credentials && chmod 600 ~/.config/mify/openrouter-credentials`
3. 启用通道：
   ```bash
   python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py install --apply --enable-openrouter
   ```
   `install` 默认保留已有 opt-in 通道状态；要关闭时显式用 `--disable-openrouter`。

**查看状态**：
```bash
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py status
# 会显示 openrouter: enabled/disabled + key file present/MISSING
```

**验证 openrouter 路由**：
```bash
curl -s 'http://localhost:41414/v1/messages?beta=true' \
  -H 'content-type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  --data '{"model":"openrouter/stealth/ox-alpha","max_tokens":16,"messages":[{"role":"user","content":"只回复 OK"}]}'
# 应转发到 openrouter.ai/api/v1，模型改写为 stealth/ox-alpha，返回 OpenRouter 响应
```

**Claude Code 使用**：把 `ANTHROPIC_DEFAULT_OPUS_MODEL`（或其他档位）设为 `openrouter/stealth/ox-alpha[1M]`，Claude Code 走本地 proxy 即自动路由到 OpenRouter。

**已知限制（必须告诉用户）**：
- Claude Desktop 1.6259+ 的 Cowork 3P 会拒绝非 Claude 模型名，`openrouter/stealth/ox-alpha` **不会**出现在 Desktop picker（`install_cowork_config.py` 会跳过它）；但 Claude Code 走本地 proxy 不受影响，可用 `/model` 或档位 env 使用。
- OpenRouter key 来自用户自己申请；计费走用户 OpenRouter 账号，proxy 只负责转发。
- `[1m]` 标记只是给客户端的选择器/上下文提示，proxy 转发前会剥离；OpenRouter 是否实际承诺 1M 上下文取决于上游模型。

#### 写完之后必须提醒用户两件事

1. **完全退出 Claude.app**（不是最小化，是 `Cmd+Q`）再重新打开 —— Cowork 3P 配置只在 app 启动时读一次
2. **如果是官方直连路径要回退**：一行 `install_cowork_config.py --revert` 即可；脚本会备份 active JSON，并清掉旧 plist 残留 key
3. **如果是 proxy 路径要停用**：先 `manage_claude_desktop_proxy.py uninstall` 停掉本地服务，再用 `install_cowork_config.py --apply` 写回官方 Claude routes，最后重启 Claude.app

#### 主动 offer 模式

当你刚做完 Step 4 的模型推荐，或 Step 5 的 Claude Code 配置落盘，且**用户明显是重度桌面 Claude 用户**（对话里提到过"用 Claude desktop"/"桌面版"等线索）时，主动补一句：

> 要不要顺便把 Claude 桌面客户端也切到 Mify？和 Claude Code 共用同一个 key，本地一键装好，不用登录 Anthropic。

如果用户点头，走 Phase A → B → C。进入 Phase C 时必须再区分“官方 Claude routes 直连”还是“本地 proxy + 非 Claude 模型映射”。如果用户说"先不用"，尊重，别再追问。

## 回答格式建议

给用户的回答结构推荐：

```
[一句话结论]

### 命中的候选
| model id | owned_by | model_type | 备注 |
|---|---|---|---|
| ... | ... | ... | ... |

### 推荐使用
`<推荐 id>`（owner=`xiaomi`），理由：<为什么>

### 补充（可选）
- 如果用户问的是某个不存在的版本，查一下有没有"上一个版本"或"相近版本"，主动给出备选。
- 如果模型列表里没有用户要的精确版本，坦白说"没接入"，不要含糊其辞。
```

## 常见坑

### 坑 1: 拉全量 dump 回对话
**不要**。过滤后的结果通常 <20 条，几百字；全量 450 条 / 38KB 会白白占用上下文。如果用户坚持要全量，写到文件里再给路径。

### 坑 2: 只看 `id` 不看 `owner`
回答「支持 kimi-k2.5」却没告诉用户走哪个 owner —— 用户用默认路由可能撞到慢通道或不稳定通道。**始终把 owner 信息一起返回**。

### 坑 3: 用裸 id 调 chat endpoint
用户反馈「明明列表里有 kimi-k2.5 但调不了，返回 400 Not supported model」时，**99% 是忘了加 owner 前缀**。正确姿势是 `xiaomi/kimi-k2.5` 或 `tongyi/kimi-k2.5`。查过 `list_models.py` 后直接把 CALL AS 列里的字符串当 model 参数传即可。如果已经带了前缀还 400，才去怀疑 owner 拼错或通道未开放。

### 坑 4: 模型版本号的约定
观察到网关里版本号有几种写法：

- `X.Y`（语义版本，如 `kimi-k2.5`、`MiniMax-M2.5`）
- `X-Instruct-0905`（日期后缀，月日）
- `X-250711`（6 位年月日）
- `X-thinking` / `X-turbo`（能力后缀）

用户问「最新版」时，需要把这些都列出来让他确认；**不要自己脑补「k2.6 就是最新」**。官方未发布的版本网关里一定没有。

## 文件地图

- `scripts/list_models.py` — 查询 & 过滤 Mify 网关
- `scripts/test_model.py` — LLM 调用验证（用 `{owner}/{id}` 格式）
- `scripts/install_token.py` — **一键 token 安装**（stdin 读 key，校验 → 落盘 → 改 rc），用户贴 key 时调它
- `scripts/fetch_aa_rankings.py` — 拉 Artificial Analysis Intelligence Index 今日榜单（日级缓存），用于通用推荐场景
- `scripts/set_cc_model.py` — 把选中的 Mify 模型落盘到 `~/.claude/settings.json` 的 Haiku/Sonnet/Opus 档位，自带 dry-run / smoke test / 一键 revert；认得本地 proxy URL（127.0.0.1:41414-41514）为 Mify 兼容端点
- `scripts/tag_context.py` — 查 AA 上下文窗口，对 settings.json 中 >= 1M 的模型加 `[1M]` 标记（Claude Code 专属，让 CC 感知大上下文窗口避免过早压缩）
- `scripts/check_claude_desktop.py` — 桌面客户端 provisioning 的 pre-check：Spotlight 查 bundle id / fallback 扫 Applications 目录，确认 Claude.app 装没装；`--install-brew` 走 Homebrew cask、`--open-download` 开浏览器跳到官方下载页
- `scripts/install_cowork_config.py` — 把 Mify 配置写入 Claude.app 当前官方本地配置 `~/Library/Application Support/Claude-3p/configLibrary/<uuid>.json` 零接触激活 3P 模式（0-sudo），`--apply` / `--verify` / `--revert` / `--fix-models` / `--include-mimo-test` / `--live-models` / `--models-file` / `--base-url`；默认使用已验证 4 个 Claude routes，显式 `--live-models` 才按 Mify 实时 Claude routes 刷新
- `scripts/claude_desktop_proxy.py` — 本地 loopback proxy（默认 127.0.0.1:41414）：Claude 风格模型名（含裸 `claude-haiku-4-5` 等 Paseo 硬编码 slug）按映射表改写到真实 Mify 模型；Mify 模型名（如 `xiaomi/mimo-v2.5`）直接透传；`parko/*` 改写后转发 Trae 代理（opt-in）；`kiro/*` 改写后转发 Kiro Gateway 代理（opt-in）。可作为 Claude Code 的 `ANTHROPIC_BASE_URL` 使用，让 Paseo 等工具的 structured generation 正常工作
- `scripts/manage_claude_desktop_proxy.py` — proxy 一键管理：`install --apply` 生成 TLS、安装 LaunchAgent、写 Desktop config；`status/start/restart/stop/uninstall` 做运行维护；支持 `--model-map external=upstream` 自定义映射；`--enable-parko` opt-in 打开 Trae 反扒通道并自动就绪检查 `trae-api-proxy` skill；`--enable-kiro` opt-in 打开 Kiro 通道并自动就绪检查 `kiro-gateway-proxy` skill；默认保留已有 opt-in channel，显式 `--disable-parko` / `--disable-kiro` 才关闭
- `references/owner_guide.md` — owner 速查 & 选择策略（详版）
- `references/setup_token.md` — token 配置教程（含一键、secrets 文件、纯手动，以及安全底线）
- `references/cowork_provisioning.md` — Cowork 3P provisioning 完整研究报告：三层配置源优先级、T1/T2/super-clean 实测方法、keychain Safe Storage 误判释疑、Anthropic 官方文档原文存档、skill 设计规范
- `references/pricing_portal_research.md` — Mify 价格门户调研记录：CAS gate、无公开 pricing API、Chrome 登录态/XHR 捕获方案、Chrome extension 可行性与分发限制
