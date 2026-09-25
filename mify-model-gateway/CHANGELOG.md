# Mify Model Gateway Skill — Changelog

## 2026-08-23 — retire-parko-kiro

- **退役 parko/kiro 通道**：trae-api-proxy 与 kiro-gateway-proxy 两个 skill 已从本机退役（服务停止、plist 移除、三处安装副本删除，Skill Factory archive 保留可回滚）。proxy 默认 `DEFAULT_PUBLIC_MODELS` / `DEFAULT_MODEL_MAP` 中移除 `parko/*` 与 `kiro/*` 条目。
- 保留 `_resolve_model` 的前缀识别与 `build_config` 的参数解析作为兼容层（避免旧 LaunchAgent/state 传入 `--trae-upstream`/`--kiro-upstream` 时崩溃）；通道默认关闭，不影响现有 Mify / openrouter 路由。

## 2026-08-23 — add-openrouter-channel

- Claude Desktop 本地 proxy 新增可选 `openrouter/*` 通道：前台暴露 `openrouter/stealth/ox-alpha`，后台转发到 OpenRouter `https://openrouter.ai/api/v1`（Anthropic 协议原生兼容，实测 `stealth/ox-alpha` HTTP 200）。
- `claude_desktop_proxy.py`：新增 `DEFAULT_OPENROUTER_UPSTREAM`、`OPENROUTER_PREFIX`、`openrouter_upstream` 配置与 `--openrouter-upstream` / `--openrouter-api-key` 参数；`_resolve_model` 识别 `openrouter/` 前缀并剥前缀后作为 OpenRouter 模型 id 转发；OpenRouter key 优先取参数，缺省从 `~/.config/mify/openrouter-credentials`（或 `OPENROUTER_API_KEY`）读取，不落 plist。
- **转发路径修复**：OpenRouter base URL 自带 `/api/v1`，而 inbound 路径已含 `/v1` 前缀，直接拼接会得到 `/api/v1/v1/messages` 404；build_config 对 openrouter 把 prefix 去掉末尾 `/v1`，实际转发 `/api/v1/messages`。
- `manage_claude_desktop_proxy.py`：新增 `--enable-openrouter` / `--disable-openrouter` opt-in 开关；`state.json` 记录 `enable_openrouter`，`status` / `configure-desktop` 保留状态；安装时校验 key 文件存在。
- 已知约束：Claude Desktop 1.6259+ 会跳过非 Claude 模型名（`openrouter/stealth/ox-alpha` 不会出现在 Desktop picker），但 Claude Code 走本地 proxy 不受影响，可通过 `ANTHROPIC_DEFAULT_OPUS_MODEL=openrouter/stealth/ox-alpha[1M]` 或 `/model` 使用。

## 2026-06-26 — preserve-proxy-channel-flags

- `manage_claude_desktop_proxy.py install` 改为默认保留已有 `parko/*` 与 `kiro/*` channel 状态；单独传 `--enable-kiro` 不再隐式关闭已启用的 `parko/*`。
- 新增 `--disable-parko` / `--disable-kiro`，需要关闭某个 opt-in 通道时显式声明，避免后续维护时误删另一个通道。
- 本机当前 Claude Desktop proxy 已同时启用 `parko/*` 与 `kiro/*`，Trae 8000 与 Kiro 8001 均通过健康检查。

## 2026-06-26 — kiro-proxy-opt-in-channel

- Claude Desktop 本地 proxy 新增可选 `kiro/*` 通道：前台暴露 `kiro/claude-opus-4-8`、`kiro/claude-sonnet-4-6`、`kiro/claude-haiku-4-5`，后台转发到本机 `kiro-gateway-proxy` 的 Anthropic `/v1/messages`。
- `manage_claude_desktop_proxy.py` 新增 `--enable-kiro` opt-in 开关；安装时会探测 8001，没跑但本机装了 `kiro-gateway-proxy` skill 时自动调用其 `setup` 完整生命周期安装。
- `state.json` 记录 `enable_kiro`，`status` / `configure-desktop` 会保留 Kiro 通道状态；proxy 路由层从二分 `Mify/Trae` 扩展为 `mify/trae/kiro` 上游选择。
- 已知约束：`kiro/*` 依赖用户本机 Kiro 登录态与 `~/.aws/sso/cache/kiro-auth-token.json`，Kiro token 过期时需要打开 Kiro 刷新后重启服务。

## 2026-06-26 — paseo-haiku-passthrough

- `claude_desktop_proxy.py` 的 `DEFAULT_MODEL_MAP` 新增 `claude-haiku-4-5` → `xiaomi/mimo-v2.5-pro` 映射，修复 Paseo 等第三方工具硬编码 `claude-haiku-4-5` 裸 slug 时被 Mify 拒绝（400 Not supported model）导致 structured generation 失败、workspace 创建阻塞的问题。
- `set_cc_model.py` 新增 `LOCAL_PROXY_HOSTS` / `MIFY_RECOGNIZED_HOSTS` 常量，`ANTHROPIC_BASE_URL` 指向本地 proxy（127.0.0.1:41414-41514）时不再被误判为非 Mify 端点而拒绝更新模型，无需 `--force-url`。
- proxy 的 passthrough 行为（不在映射表中的模型名原样转发到 Mify Anthropic endpoint）使得 Claude Code CLI 可以直接将 `ANTHROPIC_BASE_URL` 指向本地 proxy，同时使用 Mify 模型名（如 `xiaomi/mimo-v2.5[1M]`）和裸 Claude 模型名（如 `claude-haiku-4-5`）。
- 已知影响：`~/.claude/settings.json` 的 `ANTHROPIC_BASE_URL` 从 `model.mify.ai.srv/anthropic` 改为 `http://127.0.0.1:41414`，所有 Claude Code / Paseo 的 claude provider 请求改为经过本地 proxy。proxy 不可用时 claude provider 全挂；proxy 有 KeepAlive=true 自动恢复。

## 2026-06-21 — fix-ppio-opus-4-8-consistency

- 统一 `claude_desktop_proxy.py` 与 `manage_claude_desktop_proxy.py` 的 PPIO Claude Opus 默认模型版本：proxy 脚本的 `DEFAULT_PUBLIC_MODELS` 从 `ppio/pa/claude-opus-4-7` 改为 `ppio/pa/claude-opus-4-8`，与 manage 脚本及实际 install 生效的 lineup 一致，避免直接运行 proxy 脚本时暴露过时模型。

## 2026-06-21 — model-lineup-adjust

- 调整 proxy 默认模型 lineup：移除 `xisheng/claude-opus-4-7` 档位；`xisheng/claude-sonnet-4-6` 改映射到 `xiaomi/mimo-v2.5-pro`（MiMo Pro），`xisheng/claude-haiku-4-5` 改映射到 `xiaomi/mimo-v2.5`（MiMo V2.5）；`xisheng/claude-opus-4-8` 维持 `deepseek/deepseek-v4-pro`。基础模型数 8 → 7。
- parko 通道同步调整：`minimax-m3` 从 `parko/claude-opus-4-7` 改挂到 `parko/claude-sonnet-4-6`；`parko/claude-opus-4-8` 维持 `glm-5.2`。parko 档位由 opus-4-8 + sonnet-4-6 组成。
- `claude_desktop_proxy.py` 的 `DEFAULT_PUBLIC_MODELS` / `DEFAULT_MODEL_MAP` 与 `manage_claude_desktop_proxy.py` 的 `PUBLIC_MODELS` / `PARKO_MODELS` 同步更新；SKILL.md 映射表与验证 curl 示例同步刷新。

## 2026-06-21 — parko-trae-opt-in-channel

- 新增可选能力 `parko/*` 模型通道（Trae 反扒）：proxy 把 `parko/` 开头的模型名改写为真实 Trae 模型名（`parko/claude-opus-4-8`→`glm-5.2`、`parko/claude-opus-4-7`→`minimax-m3`），转发到本机 `127.0.0.1:8000` 的 Trae API 代理；其余模型仍走 Mify。
- `manage_claude_desktop_proxy.py` 新增 `--enable-parko` opt-in 开关：默认不暴露 parko 模型（安全基线 8 个模型）；开启时自动做 Trae 代理就绪检查——探测 8000 端口，没跑但本机装了 `trae-api-proxy` skill 就直接调用其 `extract_credentials.py` + `manage_service.py install` 拉起服务；skill 不存在则引导用户找 zhaoxisheng 获取（该 skill 不公开分发），且不把 parko 模型写进 Desktop 配置避免选了用不了。
- `state.json` 记录 `enable_parko` 状态，`status` 显示 `parko: enabled/disabled` + trae 代理运行情况，`configure-desktop` 能正确还原。
- `claude_desktop_proxy.py` 新增 `UpstreamTarget` 数据类与 `trae_upstream` 配置项，`_resolve_model` 返回 `(mapped_model, use_trae)`，`_proxy_to_upstream` 按 `parko/` 前缀选 upstream；parko 模型同样带 `[1m]` 后缀，转发前剥离。
- 已知限制：Trae `llm_raw_chat v2` 不支持原生 tool use（`tools` 字段被服务端忽略），parko 模型仅适合纯对话/补全，agentic tool calling 不可用。

## 2026-06-21 — desktop-model-name-context-tag

- 修复 Claude Desktop 新会话不再显示 1M 标记的问题：配置脚本现在会把支持 1M 的 Desktop 模型名写成 `...[1m]`，匹配老会话实际保存并显示 1M 的模型名格式。
- `install_cowork_config.py` 在校验和写入时会先剥离已有 `[1m]` / `[1M]` 后缀，避免重复标记或误判非 Claude route。
- `manage_claude_desktop_proxy.py` 与 `claude_desktop_proxy.py` 的默认公开模型同步带 `[1m]` 后缀；proxy 转发前继续剥离标签，不影响真实上游模型调用。
- `manage_claude_desktop_proxy.py` 生成 LaunchAgent 时优先使用 Python.org 3.14 + `SSL_CERT_FILE=/private/etc/ssl/cert.pem`，避免 Mify HTTPS 证书校验失败，同时避开 Xcode `/usr/bin/python3` 在 launchd 下读取用户目录脚本的 TCC 限制。
- LaunchAgent 的 proxy 脚本路径优先指向本地 `~/.agents/skills/mify-model-gateway/scripts`，避免读取 iCloud File Provider 下的 AgentSync 安装副本。
- 已知风险：这依赖 Claude Desktop 当前 UI 对 literal `[1m]` 模型名后缀的兼容行为；若未来改成其它标记，需要再次适配。

## 2026-06-01 — global-token-update-protocol

- 新增「一键全局安装与更新协议」：当更换或新设 Mify Key 时，自动同步覆盖至环境凭证、launchd 环境变量、Claude Code 配置 (`settings.json`)、旧版 Claude Desktop 配置 (`claude_desktop_config.json`) 及 Codex 终端注入配置 (`config.toml`)，并自动重启本地代理服务，彻底杜绝多组件间的密钥漂移与失效。
- 同步更新 references 中的 `setup_token.md` 说明文档。


## 2026-05-30 — upgrade-opus-4-8-and-proxy-models

- Desktop proxy 默认模型升级：PPIO Claude Opus `4-7` → `4-8`。
- 新增 `xisheng/claude-opus-4-8` 路由，背后映射到 `deepseek/deepseek-v4-pro`（原厂通道优先）。
- 修复 `tag_context.py` 调用 `load_or_fetch` 缺少 `source` 参数导致 `TypeError` 的 bug；同步给 `fetch_aa_rankings.py` 的 `load_or_fetch` 加 `source="auto"` 默认值，避免下游调用方再踩同样的坑。


## 2026-05-21 — default-desktop-proxy-http-loopback

- Claude Desktop 本地 proxy 默认改为 `http://localhost:<port>` loopback，避免 Electron provider health check 对自签 localhost CA 报 `ERR_CERT_AUTHORITY_INVALID`。
- `manage_claude_desktop_proxy.py` 新增/固化 `--scheme http|https`，state 记录 scheme，并能从 LaunchAgent 参数识别当前协议，避免旧 state 残留 `https` 时误报。
- 更新 Desktop proxy 文档与验证命令：HTTP 为默认推荐，HTTPS 仅在用户明确需要时使用 `--scheme https`。

## 2026-05-21 — fix-desktop-proxy-localhost-tls

- 修复 Claude Desktop 本地 proxy TLS 证书生成：改用明确的 OpenSSL config 生成 CA/server 证书，避免重复/异常扩展导致系统 TLS 校验报 `ERR_CERT_AUTHORITY_INVALID`。
- `manage_claude_desktop_proxy.py install --apply` 会校验现有 CA/server 证书；若发现不可验证，会自动重签 localhost 证书再安装。
- 已知现象：模型对话可能仍能成功，但 Claude Desktop 顶部 provider health check 会因为 Chromium/System TLS 不信任 localhost 证书而提示 `Can't reach localhost:41414`。

## 2026-05-20 — generalize-desktop-proxy-routing-and-port

- 放宽 Claude Desktop 本地 proxy 的模型改写触发条件：任何 `/v1/*` JSON POST 只要 top-level `model` 命中映射表或带 `[1M]` / `[1m]` 标签，就先 normalize/改写再转发，不再把改写绑死到 `/v1/messages`。
- 保留 route path 分流只用于特殊 endpoint：`/v1/models` 本地返回模型列表，`*/count_tokens` 本地返回估算 token，其他 `/v1/*` 透明转发。
- `manage_claude_desktop_proxy.py install --apply` 默认优先 41414；若端口占用，自动选择 41415-41514 的空闲端口，也支持 `--port` 显式指定，避免对外分享时固定端口冲突。
- 更新 SKILL / reference / eval，明确 `xisheng` provider 名保留，排障时不要把 provider 名误判为根因。

## 2026-05-20 — fix-desktop-proxy-beta-routing

- 修复 Claude Desktop 本地 proxy 的核心路由逻辑：按 query 前的 route path 识别 `/v1/messages?beta=true`，避免 `xisheng/claude-*` 原样打到 Mify 后触发 `Not supported model`。
- 新增 `/v1/messages/count_tokens?beta=true` 本地 token 估算响应、`[1M]` / `[1m]` 模型标签剥离、`claude-haiku-4-5-20251001` fallback 映射。
- 更新 Desktop proxy 文档与验证命令，明确 PPIO 直通、xisheng→MiMo 映射、Claude Code 配置三者边界。
- 默认 7 个 Desktop picker 模型全部标记 `supports1m: true`；healthz 改成 loopback liveness 检查，避免旧本地 CA 被 Python 证书策略误报。

## 2026-05-19 — claude-desktop-local-proxy

- 新增 Claude Desktop 非 Claude 模型本地 proxy 工作流：先明确官方 Desktop 只支持 Claude/Anthropic routes，再询问用户是否接受本机 proxy 绕过模型名校验。
- 新增 `scripts/claude_desktop_proxy.py` 与 `scripts/manage_claude_desktop_proxy.py`，支持 `install/status/start/restart/stop/uninstall`，默认提供 PPIO Claude 直通 + `xisheng/claude-*` 映射到 MiMo 的矩阵。
- 明确 Claude Desktop proxy 与 Claude Code 配置完全分离：Claude Code 继续用 `set_cc_model.py` 直接配置真实 Mify 模型，不需要伪装。
- 已知风险：本地 proxy 是工程绕法，不是 Anthropic 官方承诺；未来 Claude Desktop 若加强校验，可能需要更新 proxy。

## 2026-05-16 — fix-description-length

修 Codex 启动时报错 `invalid description: exceeds maximum length of 1024 characters`（实测 1126 字符）。

- 重写 description 1126 → ~501 字符
- 按 superpowers:writing-skills CSO 原则改为 `Use when ...` 触发式
- 剥离原描述里 7 条编号工作流（"(1) 查 Mify... (7) 把 Mify 挂到 Claude Desktop..."），这类细节本来就该在 SKILL.md 正文，不该塞进 frontmatter，否则 Claude/Codex 会把 description 当工作流引导而跳过读全文
- frontmatter 总字节 1898 → 582
- 同期 agent-sync-doctor / icloud-materialization-doctor 也做了类似修复

## 2026-05-11

### Pricing portal investigation note

新增 `references/pricing_portal_research.md`，记录 `gatewayPrice` 调研结论：

- `api.llm.mioffice.cn/v1/models` 仍只返回可用性 catalog，`?include=pricing` 不增加价格字段。
- `api.llm.mioffice.cn` 下常见 pricing 路径仍为 400/404。
- `llm.mioffice.cn/gatewayPrice` 和候选 `/api/*` 路径未登录均被 CAS 302 拦截。
- Chrome 已登录页面可打开到“大模型 API 开放平台”，但本次 Codex Chrome plugin native bridge 不可用，Computer Use 读取 Chrome 超时；AppleScript 可读 URL/title，但页面 JS 需要用户启用 `View > Developer > Allow JavaScript from Apple Events` 才能继续捕获 XHR。
- 推荐后续优先走“捕获已登录页面 XHR 响应并缓存”，避免直接读取/保存 CAS cookie；Chrome extension 技术上可读 HttpOnly cookie，但无法由 skill 静默安装，只能 Web Store / 企业策略 / 用户开发者模式安装。

## 2026-05-08

### Claude Desktop 1.6259.x 适配

Claude Desktop Cowork 3P 本地用户配置主路径更新为：

```text
~/Library/Application Support/Claude-3p/configLibrary/_meta.json
~/Library/Application Support/Claude-3p/configLibrary/<active-id>.json
```

`_meta.json.appliedId` 指向 active config。clean profile / 新机器没有 active id 时，skill 会自动生成 UUID 并创建对应 JSON。

### 模型列表限制更新

生产默认 `inferenceModels` 收敛到 4 个已验证 Claude routes：

- `ppio/pa/claude-opus-4-7`
- `ppio/pa/claude-opus-4-6`
- `ppio/pa/claude-sonnet-4-6`
- `ppio/pa/claude-haiku-4-5`

MiMo / Kimi / Qwen / DeepSeek / GPT 等非 Claude Mify 模型继续支持 Claude Code，但不要写入 Claude Desktop 生产 `inferenceModels`。

### 新增操作模式

| 命令 | 用途 |
|---|---|
| `install_cowork_config.py` | first-time / clean profile dry-run |
| `install_cowork_config.py --apply` | 写入完整 3P configLibrary 配置 |
| `install_cowork_config.py --fix-models` | 已有 profile 只预览模型列表修复 |
| `install_cowork_config.py --fix-models --apply` | 已有 profile 只替换 `inferenceModels` |
| `install_cowork_config.py --include-mimo-test` | 显式追加 MiMo 做 test-only 失败验证 |
| `install_cowork_config.py --live-models` | 探索 Mify 实时 Claude routes，opt-in，不作为默认生产路径 |

### 证据与评测

证据整理：`https://feishu.cn/wiki/NXNNwA1mfiT1zNkfP79crnqdnzf`

新增 4 条 Claude Desktop 1.6259.x 兼容性 eval：

- 已有 profile 只修模型，不能覆盖用户其他配置
- clean profile active id 自举
- MiMo 显式 test-only 失败验证
- live catalog opt-in

## 2026-04-28

历史记录：以下是 4/28 当时的修复背景。Claude Desktop 1.6259.x 之后，请以 2026-05-08 的 `configLibrary` 主路径为准。

### 对话历史安全继承

从 GUI 配置迁移到 skill 自动配置时，已有的 Claude Desktop 对话记录自动继承，不丢失、不需要手动操作。后续修改模型列表也不影响历史对话。

> 历史技术要点：4/28 当时采用 `enterpriseConfig` 驱动模型列表和网关配置，并把 `configLibrary` draft UUID 作为身份锚。5/8 之后，skill 直接写 `configLibrary` active config，不再把它只当身份锚。

### Cowork 联网能力放开

默认写入 `coworkEgressAllowedHosts: ["*"]`，Cowork 沙箱内 Web Fetch（访问外部 URL 获取内容）开箱即用，不再被沙箱拦截。

> 注：Web Search 需要 Anthropic 官方订阅，3P 模式下暂不可用。

### 配置安全性增强

- **不覆盖用户设置**：配置落盘采用 read-modify-write 模式，不会重置你在 Claude Desktop 里手动调过的 UI 偏好（sidebar 模式、快捷键等）
- **回滚更安全**：`--revert` 只清空 enterpriseConfig 字段，保留 preferences 等其他内容，不删整个文件
- **去除多余字段**：不再写入 `deploymentOrganizationUuid`，由 app 自行管理身份，减少配置冲突风险

### 白屏修复（重大）

4/28 当时的白屏修复是从 `defaults write` plist 迁移到 `~/Library/Application Support/Claude-3p/claude_desktop_config.json`。5/8 之后，Claude Desktop 1.6259.x 的当前主路径已更新为 `~/Library/Application Support/Claude-3p/configLibrary/`。旧 plist 路径继续废弃，`claude_desktop_config.json` 只作为旧兼容/偏好载体。

---

### 改动文件清单

| 文件 | 改动 |
|---|---|
| `scripts/install_cowork_config.py` | 4/28 版本：write_json_config() read-modify-write；cmd_revert() 清空而非删文件；build_target() 去掉 deploymentOrganizationUuid、加 coworkEgressAllowedHosts；ENTERPRISE_KEYS 同步 |
| `references/cowork_provisioning.md` | 4/28 版本记录了 configLibrary 身份锚结论；5/8 版本已更新为 configLibrary active config 主路径 |
| `SKILL.md` | 4/28 版本记录了 read-modify-write + 不碰 configLibrary；5/8 版本已更新为写 configLibrary active config |
