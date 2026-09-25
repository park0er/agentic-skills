<!-- feishu: https://feishu.cn/wiki/I8GHwek6MiJWglkv1MicVhU7nxc -->

<title>Codex-Mify Skill — 让 OpenAI Codex 跑公司大模型网关</title>

<callout emoji="🚀" background-color="light-blue">

**Codex-Mify Skill** — 把 OpenAI Codex（Desktop app / CLI / VS Code 扩展）从官方登录切换到走公司 Mify 网关跑 Azure GPT-5 系列的 AI 助手。

> 1. 一键完成 Codex 首次配置（config.toml + LaunchAgent + zsh 切换函数）
> 2. 日常切 model 一条命令（带自动备份 + smoke test + 失败自动回滚）
> 3. 诊断并修复 Codex 升级带来的 `wire_api = "chat" is no longer supported` 红框崩溃
> 4. 解决 macOS GUI 下 Codex Desktop 读不到 `MIFY_API_KEY` 的老大难

**⚠️ 前置依赖：本 skill 依赖 `mify-model-gateway` skill 管理 API token。请先安装 mify-model-gateway，再装本 skill。**

</callout>

---

## 为什么做这个 Skill

Codex Desktop / CLI 出厂默认走 OpenAI 官方登录（需要个人 ChatGPT Plus 订阅），但在小米内部有三个痛点：

- **OpenAI 官方订阅**对个人账号绑定，公司报销不便，还要买外汇；
- **Mify 网关上的 Azure GPT-5 系列** 是公司统一出口，内部走量有配额、成本低、合规稳，但配置路径完全没文档；
- 自己摸索配置要踩若干坑：`wire_api = "chat"` 被 OpenAI 在 PR #10157（2026-02）永久删除、Mify `/v1/responses` 端点只给 `azure_openai/*` 开了白名单、Codex Desktop 的 model picker 对 custom provider 直接失效、macOS GUI app 读不到 shell env 里的 `MIFY_API_KEY` 要配 LaunchAgent 等等。

这些坑单个看都不复杂，但**叠起来自己踩一圈平均要半天到一天**，而且每踩一次都会被 LLM 的幻觉（Gemini 经常推荐已废弃的 `wire_api = "chat"` 或 不存在的 `"chat_completions"`）带到沟里。

<callout emoji="💡" background-color="light-blue">

**这个 Skill 的目标**：一句话在 Claude Code 里说明意图，skill 自动完成配置、验证、切换、回滚的完整闭环。把"Codex 装到能跑公司 GPT"的门槛从半天压到 5 分钟。

</callout>

---

## ⚠️ 前置依赖：必须先装 `mify-model-gateway` skill

<callout emoji="warning" background-color="light-yellow">

**这个 skill 不管 API token**。Codex-Mify Skill **反向依赖** `mify-model-gateway` 主 skill 的 `install_token.py` 来管理 Mify 的 `sk-` API key，**不重复实现 token 管理逻辑**。

</callout>

### 为什么拆成两个 skill

- `mify-model-gateway`：管 **Mify 网关本身**（API token、模型列表、调用验证、业界榜单推荐、Claude Code / Claude Desktop 挂载）。通用、底层。
- `codex-mify`（本 skill）：管 **把 Mify 挂到 OpenAI Codex 这一个特定客户端**。窄、专。

这样拆的好处：主 skill 不会因为 Codex 特有的坑（`wire_api` / `azure_openai` 白名单 / LaunchAgent 等）变得臃肿；本 skill 也不会和主 skill 在 token 安装这种基础能力上打架。

### 正确的安装顺序

```markdown
第一步：安装 mify-model-gateway skill（主 skill）
  └── 提供 API token、模型查询、基础网关能力

第二步：安装 codex-mify skill（本 skill）
  └── 调用主 skill 的 install_token.py 完成 token 设置
  └── 在主 skill 基础上加 Codex 特有配置
```

### 先去装 mify-model-gateway

<callout emoji="rocket" background-color="light-green">

**👉 点这个飞书文档看 mify-model-gateway 的完整使用说明和安装方式：**

[**Mify Model Gateway Skill — 公司大模型网关的 AI 助手**](https://mi.feishu.cn/wiki/XmfxwkD8tifAHkkRazVcDQd9nmg)

装完那个 skill 之后，再回这里继续装 codex-mify。

</callout>

如果你还没有 Mify API key，主 skill 的文档会告诉你在 `https://llm.mioffice.cn/apikey` 申请，粘贴到 Claude Code 对话里即可一键安装。

---

## 设计理念

<grid cols="2">
<column>

### 数据驱动，不拍脑袋

- 切模型前自动查 Mify 的 `/v1/models` 确认目标存在
- smoke test 实测一次 `/v1/responses` 验证新模型真能调通
- 模型推荐沿用主 skill 的 Artificial Analysis Intelligence Index × Mify 可用性交叉判断

### 继承主 skill 的安全原则

- **永远先 dry-run**：改 config 前先展示 diff
- 写操作自动 backup + 一键 revert
- 不把 key 写进 skill 目录或代码仓库
- 不覆盖用户已有的 config.toml 字段（只改必要部分）

</column>
<column>

### Codex 特有的硬约束内化

- `wire_api` 只认 `"responses"`（PR #10157 删了 `"chat"`）
- Mify `/v1/responses` 只代理 `azure_openai/*` 通道
- Codex Desktop picker 对 custom provider 是死的 —— 切 model 走 config 文件 + Cmd+Q 重启
- macOS GUI env 独立于 shell env，必须走 LaunchAgent 注入

skill 会**主动**把这些告诉你，不让你反复踩同一个坑。

### 双向指针

本 skill 和主 skill SKILL.md 里互相有 pointer。遇到 token 问题会把你导到主 skill，遇到 MiMo/Kimi 用例会告诉你去 Claude Code 用主 skill。路由不丢失。

</column>
</grid>

---

## 支持的功能（5 大场景）

### 场景 1：一键首次配置

一条命令完成 config.toml 写入 + LaunchAgent 安装 + zshrc 函数注入。

```bash
python3 ~/.claude/skills/codex-mify/scripts/install.py --dry-run    # 先看计划
python3 ~/.claude/skills/codex-mify/scripts/install.py --apply      # 执行
python3 ~/.claude/skills/codex-mify/scripts/install.py --revert     # 全部回滚
```

script 里做的事：

1. Pre-check：macOS + Codex 已装 + Mify credentials 已装
2. 写 `~/.codex/config.toml` 的 Mify provider 块（保留其他 sections）
3. 生成 LaunchAgent plist，引导 Finder 拖拽绕过 macOS TCC 限制
4. 追加 `codex-model()` 函数到 `~/.zshrc`（用 marker comment 做幂等检测）
5. 打印验证命令 + Desktop 首启假登录说明

### 场景 2：日常切换模型

两种等效路径，交互场景用 zsh function、脚本化场景用 Python script。

**zsh function**（安装后任何终端都能用）：
```bash
codex-model                              # 查当前 model + 候选提示
codex-model azure_openai/gpt-5.5         # 切到 5.5
codex-model azure_openai/gpt-5.3-codex   # 切到 codex 变种
```

**Python script**（自带 smoke test + 失败自动 revert，适合 CI / 脚本编排）：
```bash
python3 scripts/set_codex_model.py --model azure_openai/gpt-5.5 --apply
python3 scripts/set_codex_model.py --revert    # 回最近一次备份
```

切换后自动同步 `[model_providers.mify].name` 字段，Desktop UI 标签跟着当前 model 走。

### 场景 3：诊断并修复 Codex 升级崩溃

<callout emoji="fire" background-color="light-orange">

**典型症状**：升级完 Codex Desktop 启动报红框 `Invalid configuration: wire_api = "chat" is no longer supported`。

</callout>

这是 OpenAI 在 Codex PR #10157（2026-02）永久删除了 `wire_api = "chat"` 的后果。Skill 会：

1. 识别问题根因（源码级删除，不是文档过期，不是 Mify 侧问题）
2. 引用二进制证据（`strings /Applications/Codex.app/Contents/Resources/codex | grep wire_api`）
3. 直接改成 `wire_api = "responses"`，且引导 Cmd+Q 重启 Desktop

**反幻觉保护**：LLM 可能推荐 `"chat_completions"` / 降级 Codex / 装 LiteLLM proxy，本 skill 明确拒绝这些建议 —— 对 `azure_openai/*` 模型这些都是过度工程。

### 场景 4：GUI env 持久化（LaunchAgent）

macOS 上 Codex Desktop 从 Dock 启动时不走 shell，读不到 `~/.zshrc` 里的 `MIFY_API_KEY`。Skill 的 `install.py` 自动处理：

- 生成 LaunchAgent plist 指向 `~/.config/mify/credentials`
- 因为 macOS TCC 阻止 Terminal 进程写 `~/Library/LaunchAgents/`，**引导 Finder 拖拽绕过**（Finder 自带权限，弹一次授权对话框即可）
- 装完 `launchctl bootstrap` + `kickstart` 激活，立即可用
- key rotate 时只改 `~/.config/mify/credentials` 一处，下次登录自动刷新

### 场景 5：安全回滚

任何一步出问题都有 escape hatch：

- config 切换失败：`set_codex_model.py --revert` 恢复最近一次自动备份
- 首次安装后悔：`install.py --revert` 卸载所有 skill 写入的组件
- 全部推倒重来：`cp ~/.codex/config.toml.bak.YYYYMMDD-HHMMSS ~/.codex/config.toml`

---

## 用户提问示例合集

### 一键配置

| 问题示例 | 对应场景 |
|---|---|
| "帮我把 Codex 挂到公司网关" | 场景 1 |
| "给我的新机器装 Codex + Mify" | 场景 1 |
| "我刚装完 Codex Desktop，不想登 OpenAI 官方账号" | 场景 1 |

### 切换 / 升级模型

| 问题示例 | 对应场景 |
|---|---|
| "把 Codex 切到 gpt-5.5" | 场景 2 |
| "换 Codex 试试 codex 变种" | 场景 2 |
| "Codex 还在用旧 model，给我升到最新的" | 场景 2 |

### 报错排查

| 问题示例 | 对应场景 |
|---|---|
| "Codex 启动报 `wire_api = "chat" is no longer supported`" | 场景 3 |
| "Codex 说 `Not supported model: ...`" | 场景 3 |
| "Codex Desktop 的 model picker 点不开" | 场景 3 |

### 环境问题

| 问题示例 | 对应场景 |
|---|---|
| "Codex Desktop 启动后报 401，明明 CLI 里是好的" | 场景 4 |
| "Mac 重启后 Codex 又不能用了" | 场景 4 |
| "MIFY_API_KEY 在 Terminal 里有，GUI app 读不到" | 场景 4 |

### 撤回

| 问题示例 | 对应场景 |
|---|---|
| "把 Codex 配置回退到上次好的状态" | 场景 5 |
| "完全卸载 codex-mify 的配置" | 场景 5 |

---

## 技术架构

### 文件结构

```
~/.claude/skills/codex-mify/
├── SKILL.md                              # skill 入口
├── scripts/
│   ├── install.py                        # 首次配置，一键完成 4 件事
│   └── set_codex_model.py                # 日常切模型，含 smoke test 和 revert
└── references/
    └── codex_setup_guide.md              # 长篇配置指南（本文档的详细版）
```

### 三个硬约束

Skill 把这些约束写进 SKILL.md 前排，LLM 读到就不会再去犯这些错：

<lark-table column-widths="230,500">
<lark-tr>
<lark-td>

**约束**

</lark-td>
<lark-td>

**原因 + 结果**

</lark-td>
</lark-tr>
<lark-tr>
<lark-td>

`wire_api = "responses"` 唯一合法

</lark-td>
<lark-td>

Codex PR #10157（2026-02）源码级删除了 `"chat"`。二进制 `strings` 里能 grep 到错误模板硬编码。没有 fallback flag，没有 `"chat_completions"`（那是 LLM 幻觉）。

</lark-td>
</lark-tr>
<lark-tr>
<lark-td>

只 `azure_openai/*` 能跑

</lark-td>
<lark-td>

Mify `/v1/responses` 端点做了前置白名单。其他 owner（`xiaomi/*`、`tongyi/*`、`ppio/*`）一律 400 `only supports provider 'azure_openai'`。MiMo/Kimi/Qwen 要用请走 Claude Code（用主 skill 的 `set_cc_model.py`）。

</lark-td>
</lark-tr>
<lark-tr>
<lark-td>

切 model 必走 config + Cmd+Q

</lark-td>
<lark-td>

Codex Desktop model picker 对 custom provider 是死的（issue #10867）。Skill 维护 `[model_providers.mify].name` 字段让 UI 标签随 model 变，但切换入口只有 `codex-model` 函数和 `set_codex_model.py`。

</lark-td>
</lark-tr>
</lark-table>

---

## 评测结果

3 个真实用户场景 × 2 个 configuration（with-skill vs baseline，baseline 有 mify 主 skill 但没 codex-mify）：

| Eval | with-skill | baseline | Delta |
|---|---|---|---|
| 全新机器一键配置 | 8/8 | 7/8 | +1（baseline 漏 TCC 限制） |
| 修 wire_api 红框崩溃 | 6/6 | 5/6 | +1（baseline 把降级 Codex 列为选项，反模式） |
| 切换 GPT-5.4 → 5.5 | 5/6 | 6/6 | -1（baseline 恰好提了 Azure Responses-only 彩蛋） |
| **汇总** | **19/20** | **18/20** | **+1** |

<callout emoji="memo" background-color="pale-gray">

Delta 窄，但方向对 —— skill 救回 2 个真实 footgun（TCC 限制 / 反幻觉降级建议），丢失 1 个 cosmetic bonus。baseline 高分是因为它访问了主 skill 的 mify-model-gateway，已经覆盖了基础知识；skill 的增量价值集中在 Codex 特有的冷知识上。

</callout>

---

## 快速上手

### Step 1：先装 mify-model-gateway skill

按 [**Mify Model Gateway Skill 飞书文档**](https://mi.feishu.cn/wiki/XmfxwkD8tifAHkkRazVcDQd9nmg) 的「快速上手」走一遍：

1. 申请 Mify API key（https://llm.mioffice.cn/apikey）
2. 安装主 skill（micode 或手动下载）
3. 在 Claude Code 对话里贴上 key，skill 自动帮你装到 `~/.config/mify/credentials`

完成后 `ls ~/.config/mify/credentials` 应该能看到文件存在。

### Step 2：安装 codex-mify skill

（待主 skill ready 后，把本 skill 文件夹放在 `~/.claude/skills/codex-mify/` 目录下，Claude Code 会自动识别。具体 micode 仓库地址 / brew tap 后续补。）

### Step 3：装好 Codex Desktop 或 CLI

- Desktop：从 https://openai.com/codex 下载 DMG
- CLI：`npm i -g @openai/codex` 或 Desktop app 自带

### Step 4：让 Claude Code 帮你跑一键配置

在 Claude Code 对话里说一句：

> "帮我把 Codex 挂到公司 Mify 网关"

Skill 会自动：

1. 检测 `mify-model-gateway` 已装 + Mify credentials 已装
2. 跑 `install.py --dry-run`，展示所有将要改动
3. 等你确认后 `--apply`
4. 引导你 Finder 拖拽 plist（绕 TCC）+ Cmd+Q 重启 Desktop + 首启假登录

---

## 常见问题

<callout emoji="bulb" background-color="light-blue">

**Q：我能不能只装 codex-mify 不装 mify-model-gateway？**
A：**不能**。codex-mify 的 `install.py` 第一步就会检查 `~/.config/mify/credentials` 存在，不存在会退出并指路到主 skill 的 `install_token.py`。这个设计是故意的 —— token 管理集中在一个地方，rotate key 只改一处，不用担心两个 skill 里的 token 值不同步。

</callout>

<callout emoji="bulb" background-color="light-blue">

**Q：Codex 支持 MiMo / Kimi / Qwen 吗？**
A：**不支持**。Mify 的 `/v1/responses` 端点只代理 `azure_openai/*` 通道，xiaomi/tongyi/ppio 等一律 400 拒绝。Codex 又只认 `wire_api = "responses"` 所以也走不了 chat completions 端点。想在 Claude Code 里用这些国产模型，请用主 skill 的 `set_cc_model.py`（走 Anthropic 协议，支持所有 owner 通道）。

</callout>

<callout emoji="bulb" background-color="light-blue">

**Q：codex-mify 会不会覆盖我 `~/.codex/config.toml` 里别的设置？**
A：不会。`install.py` 只在文件顶部插入 Mify provider 块，所有 `[projects.*]`、`[marketplaces.*]`、`[features]`、`[plugins.*]`、`[shell_environment_policy]` 等段落一字不改。写之前还会 backup 到 `.bak.YYYYMMDD-HHMMSS`。

</callout>

<callout emoji="bulb" background-color="light-blue">

**Q：Gemini 建议我用 `wire_api = "chat"`，是不是 Claude 这个 skill 错了？**
A：**Gemini 错了**。Codex PR #10157（2026-02 合并）源码级删除了 `"chat"`。这个事实的铁证是 Codex 二进制里硬编码的错误模板：`strings /Applications/Codex.app/Contents/Resources/codex | grep wire_api` 能看到 `` `wire_api = "chat"` is no longer supported `` 这条字符串。以后 LLM 给配置值拿不准时，`strings + grep` 是成本最低的验证法。

</callout>

<callout emoji="bulb" background-color="light-blue">

**Q：我升级了 Codex，之前 skill 装的配置还能用吗？**
A：绝大概率能用 —— skill 写的是 `wire_api = "responses"` 和标准的 `[model_providers.*]` 结构，这是 Codex 当前代码路径核心。如果未来 Codex 再做 breaking change（比如把 `responses` 也重命名），skill 会更新，届时重新跑 `install.py --apply`（幂等，不会重复写）即可。

</callout>

<callout emoji="bulb" background-color="light-blue">

**Q：`codex-model` 函数能切到任何 model 吗？**
A：**函数本身无白名单**，你传什么 slug 它就老实写什么。但 Mify + Codex 两侧会在调用时判断 —— 合法的只有 `azure_openai/*` 下实际存在的 model。函数里的 usage 列出的是"已实测可用"的候选，不是硬约束。想试新 GPT 版本直接 `codex-model azure_openai/gpt-5.x` 即可；失败的话 `--revert` 回退。

</callout>

<callout emoji="bulb" background-color="light-blue">

**Q：Codex Desktop 里显示的"Mify (Xiaomi)"是什么意思？**
A：旧版 skill 把 provider `name` 设成了 "Mify (Xiaomi)"（display-only）。现在 skill 会把 `name` 字段和当前 `model` 同步 —— 切到 gpt-5.5 就显示 "gpt-5.5"。UI 标签跟着实际 model 走，对用户友好。

</callout>

---

## 参考资料

- [Codex Desktop / CLI 走 Mify 网关完整配置指南](https://feishu.cn/wiki/HZILwO53HiRMxZk2wSTcULSPnDh) — 长篇 setup guide，含架构图、每个坑的深度讲解、完整的 troubleshooting 矩阵
- [Mify Model Gateway Skill 飞书文档](https://mi.feishu.cn/wiki/XmfxwkD8tifAHkkRazVcDQd9nmg) — 主 skill 说明（前置依赖）
- [openai/codex Issue #10867](https://github.com/openai/codex/issues/10867) — Desktop picker 对 custom provider 失效的 workaround
- [openai/codex Discussion #7782](https://github.com/openai/codex/discussions/7782) — wire_api chat 废弃说明
