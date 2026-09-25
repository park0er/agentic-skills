# Claude Desktop (Cowork 3P) 零接触 Provisioning

本文档记录 Mify 网关 + Claude Desktop 3P 模式的自动化配置机制。

**2026-05-08 更新**：Claude Desktop `1.6259.x` 已经更新本地配置和模型校验逻辑。本 skill 现在以官方当前的 `~/Library/Application Support/Claude-3p/configLibrary/` 为主路径；旧版 `defaults write com.anthropic.claudefordesktop ...` 只作为历史兼容/清理对象保留。新版还会校验 `inferenceModels` 必须是 Anthropic/Claude gateway route；Kimi / Qwen / GPT / MiMo / DeepSeek 等非 Claude 模型不能再出现在 Claude Desktop Cowork 3P picker 中。

## 背景

Anthropic 的 Claude Desktop app 在有 3P / enterprise 配置时会进入 "3P 模式" —— 不登录 Anthropic 账号，而是通过预配置的第三方 gateway（我们的用例：小米 Mify）转发请求。官方当前文档把本地用户配置位置列为 `Claude-3p/configLibrary/`；本机 Claude `1.6259.1` 也确实读取该目录下 `_meta.json` 指向的 active JSON。

## 当前配置源

Claude Desktop 当前相关配置源：

| # | 路径 | 权限 | 当前状态 |
|---|---|---|---|
| 1 | `/Library/Managed Preferences/<user>/com.anthropic.claudefordesktop.plist` | sudo / MDM | IT / MDM 管理路径；优先级最高 |
| 2 | `~/Library/Application Support/Claude-3p/configLibrary/_meta.json` + `<uuid>.json` | 无需 sudo | **当前本地用户配置主路径**；skill 现在写这里 |
| 3 | `~/Library/Application Support/Claude-3p/claude_desktop_config.json` 的 `enterpriseConfig` 字段 | 无需 sudo | 旧兼容/偏好载体；不要作为新写入主路径 |
| 4 | `~/Library/Preferences/com.anthropic.claudefordesktop.plist` | 无需 sudo | 旧版 skill 曾写入；当前只做检测/清理 |

官方原话（`configuration.md`）：
> "When a managed source is present, it wins and locally written values are ignored."
> "Configuration is read **once at launch**, so fully quit and reopen the app after any change."

## 激活所需的 key

对 gateway provider 最小可行组合：

| key | 值类型 | 说明 |
|---|---|---|
| `inferenceProvider` | `"gateway"` | 固定 |
| `inferenceGatewayBaseUrl` | URL（必须 `https://`） | Mify 推荐 `https://api.llm.mioffice.cn/anthropic`（公网 DigiCert 证书），而非 `model.mify.ai.srv`（小米内网 CA） |
| `inferenceGatewayApiKey` | `sk-...` | Mify API key；gateway 不需要 key 时可以是占位 |
| `disableDeploymentModeChooser` | `true` | 跳过 "Anthropic vs 3P" 选择屏，直接进 3P |
| `deploymentOrganizationUuid` | UUID v4 | telemetry 标签，用户生成并保持稳定；没设会用占位 UUID |
| `coworkEgressAllowedHosts` | JSON array | 允许 Cowork 本地工具访问的 host；本机已有 `"*"` 时保留 |
| `inferenceModels` | JSON array | 当前 Mify 需要显式写；生产默认只写已验证 Claude routes |

## 激活判定规则

官方两处说法（内部不一致）：
1. "3P mode activates only when `inferenceProvider` is set **and** the required credential keys for the selected provider are present and valid; otherwise the app launches in standard mode." (`configuration.md`)
2. "When any managed source is present, it takes effect." (`overview.md`)

**安全姿势**：三件套（`inferenceProvider` + `inferenceGatewayBaseUrl` + `inferenceGatewayApiKey`）齐全必能激活。

## 能跳过的 GUI 步骤

| GUI 步骤 | 对应 key |
|---|---|
| Sign-in 选 "Anthropic vs 3P" | `disableDeploymentModeChooser` |
| Provider 下拉 | `inferenceProvider` |
| BaseUrl / ApiKey 填写 | `inferenceGatewayBaseUrl` / `inferenceGatewayApiKey` |
| 模型清单 | `inferenceModels` |
| Deployment UUID | `deploymentOrganizationUuid` |
| In-app 配置窗口整体 | "the in-app configuration window becomes read-only"（文档原话，只要 managed source 存在） |

## 值类型

`configLibrary/<uuid>.json` 是原生 JSON：

```json
{
  "inferenceProvider": "gateway",
  "inferenceGatewayBaseUrl": "https://api.llm.mioffice.cn/anthropic",
  "inferenceGatewayApiKey": "sk-...",
  "disableDeploymentModeChooser": true,
  "deploymentOrganizationUuid": "<UUID>",
  "coworkEgressAllowedHosts": ["api.llm.mioffice.cn"],
  "inferenceModels": [
    {"name": "ppio/pa/claude-opus-4-7", "supports1m": true},
    {"name": "ppio/pa/claude-sonnet-4-6", "supports1m": true},
    {"name": "ppio/pa/claude-haiku-4-5"}
  ]
}
```

只有 MDM / plist OS preference store 才需要把数组作为 JSON 字符串写入。当前 skill 不再把 plist 作为主写入路径。

## 模型列表限制

Claude Desktop `1.6259.x` 的日志实测错误：

> `Invalid custom3p enterprise config: inferenceModels: configured model "azure_openai/gpt-5.4" is not an Anthropic model. Gateway deployments require an Anthropic model from the provider catalog — expected a gateway model route referencing an Anthropic model (e.g. claude-sonnet-4-5, anthropic/claude-*). Name routes to match the underlying model.`

因此：

- Claude Desktop Cowork 3P：生产默认只写已验证的 4 个 Claude routes：`ppio/pa/claude-opus-4-7`、`ppio/pa/claude-opus-4-6`、`ppio/pa/claude-sonnet-4-6`、`ppio/pa/claude-haiku-4-5`。
- Mify 实时 catalog 里可能有更多 `claude-*` 路由；只在用户明确要求探索时用 `install_cowork_config.py --live-models`。
- Claude Code：仍可写 `xiaomi/kimi-k2.5`、`tongyi/qwen-max`、`azure_openai/gpt-*` 等任意 Mify LLM，这是另一套配置链路。
- Mify 当前 `https://api.llm.mioffice.cn/anthropic/v1/models` 返回 400，而 `https://api.llm.mioffice.cn/v1/models` 正常；由于 Claude Desktop 会对 `baseUrl + /v1/models` 做 discovery，短期仍要显式写入 `inferenceModels`。

## 非 Claude 模型的本地 proxy 方案

如果用户明确要求在 Claude Desktop 里使用 MiMo / Kimi / Qwen / DeepSeek 等非 Claude 模型，不能直接把这些模型写入 `inferenceModels`。可选绕法是：

1. 本机启动 `http://localhost:<port>` 的 Anthropic-compatible loopback proxy，默认只绑定 `127.0.0.1`。
2. Claude Desktop 的 `inferenceGatewayBaseUrl` 写成实际选中的 `http://localhost:<port>`。
3. `inferenceModels` 只放 Claude 风格 route，例如 `xisheng/claude-opus-4-7`。
4. proxy 对任何 `/v1/*` JSON POST 都先看 top-level `model`，命中映射表或带 `[1M]` / `[1m]` 标签就 normalize/改写，再转发到 `https://api.llm.mioffice.cn/anthropic`。不要把模型改写绑死到某一个 endpoint。
5. proxy 只用 route path 做特殊 endpoint 分流：`/v1/models` 本地返回 model discovery，`*/count_tokens` 本地返回 token 估算，因为 Mify Anthropic route 当前不支持 token counting endpoint，直接转发会返回 400。

默认矩阵：

| Claude Desktop 看到 | Mify 实际收到 | 行为 |
|---|---|---|
| `ppio/pa/claude-opus-4-7` | `ppio/pa/claude-opus-4-7` | 直通 |
| `ppio/pa/claude-opus-4-6` | `ppio/pa/claude-opus-4-6` | 直通 |
| `ppio/pa/claude-sonnet-4-6` | `ppio/pa/claude-sonnet-4-6` | 直通 |
| `ppio/pa/claude-haiku-4-5` | `ppio/pa/claude-haiku-4-5` | 直通 |
| `xisheng/claude-opus-4-7` | `xiaomi/mimo-v2.5-pro` | MiMo Pro |
| `xisheng/claude-sonnet-4-6` | `xiaomi/mimo-v2.5` | MiMo V2.5 |
| `xisheng/claude-haiku-4-5` | `xiaomi/mimo-v2-flash` | MiMo Flash |

默认所有模型都写 `supports1m: true`。proxy 转发前会剥离模型名末尾的 `[1M]` / `[1m]` 标签，因此 PPIO 直通和 xisheng 映射都不受 UI 上下文标签影响。

管理脚本：

```bash
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py install        # dry-run
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py install --apply
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py status
python ${SKILL_DIR}/scripts/manage_claude_desktop_proxy.py restart
```

默认优先使用 `http://localhost:41414`。如果本机 41414 已被占用，`install --apply` 会自动选择 `41415-41514` 的空闲端口并把 Claude Desktop config 写成实际端口；也可以显式传 `--port 41415`。对外分享时不要把 41414 写成唯一可用端口。

HTTPS localhost 仍可用 `manage_claude_desktop_proxy.py install --apply --scheme https` 显式打开，但不作为默认路径。实测 Claude Desktop/Electron 的 provider health check 可能对自签 localhost CA 报 `ERR_CERT_AUTHORITY_INVALID`，即使系统 curl 已经信任该 CA；本地 HTTP loopback 可以避开这类误报。

安全边界：

- 这是工程绕法，不是 Anthropic 官方承诺。未来 Desktop 如果加强校验，可能需要更新 proxy。
- 必须先告知用户“官方 Desktop 只支持 Claude/Anthropic routes”，并询问是否接受本地 proxy。
- 不要把真实 Mify token 写入 Claude Desktop config；proxy 用 `~/.config/mify/credentials` 读取 token，Desktop config 只写本地占位 key。
- Claude Code 不需要这种伪装，继续使用 `set_cc_model.py` 直接配置真实 Mify 模型。
- 如果 PPIO 可用但 xisheng 报 API error，优先查 proxy 是否解析到了 JSON `model` 字段并执行 normalize/映射；不要把根因归咎于 `xisheng` provider 名。实测 `xisheng/claude-opus-4-7` 可成功路由到 `xiaomi/mimo-v2.5-pro` 并返回 `model=mimo-v2.5-pro`。

## 操作模式

| 命令 | 用途 | 写入范围 |
|---|---|---|
| `install_cowork_config.py` | 默认 dry-run，展示完整 3P 配置 diff | 不写 |
| `install_cowork_config.py --apply` | first-time / fresh profile provisioning | 写 gateway key、base URL、deployment UUID、egress hosts、`inferenceModels` |
| `install_cowork_config.py --fix-models` | 修复已有 profile 的模型列表 | 只预览 `inferenceModels` |
| `install_cowork_config.py --fix-models --apply` | 修复已有 profile，不动其他配置 | 只替换 active JSON 和旧兼容 `claude_desktop_config.json` 的 `inferenceModels` |
| `install_cowork_config.py --include-mimo-test` | 显式验证新版是否仍拒绝 MiMo | 追加 `xiaomi/mimo-v2.5-pro`，预期可能 invalid_config |
| `install_cowork_config.py --live-models` | 探索 Mify 实时 Claude routes | 使用实时 catalog，不作为默认生产路径 |

`--fix-models` 是已有用户 profile 的首选修复方式，因为它保留除模型列表以外的所有配置、历史数据和偏好。

## 历史实测方法（仅留档，不再作为当前实现）

分三轮实测，每轮都完整备份 + 可还原。

### T1: 预写 `enterpriseConfig in JSON`（Level 3）

```bash
# 1. 关 app + 清目录
osascript -e 'tell application "Claude" to quit'; sleep 2
rm -rf "$HOME/Library/Application Support/Claude-3p"
mkdir -p "$HOME/Library/Application Support/Claude-3p"

# 2. 写 JSON
cat > "$HOME/Library/Application Support/Claude-3p/claude_desktop_config.json" <<EOF
{
  "deploymentMode": "3p",
  "enterpriseConfig": {
    "inferenceProvider": "gateway",
    "inferenceGatewayBaseUrl": "https://api.llm.mioffice.cn/anthropic",
    "inferenceGatewayApiKey": "sk-...",
    "disableDeploymentModeChooser": true,
    "deploymentOrganizationUuid": "<UUID>",
    "inferenceModels": [{"name": "...", "supports1m": true}, "..."]
  }
}
EOF

# 3. 启动 → 直接进 3P 聊天界面
open -a "Claude"
```

**结果**：✅ 激活成功。UI 跳过 chooser，picker 显示预置清单。

### T2: user-level plist（历史路径，当前不再作为主路径）

```bash
osascript -e 'tell application "Claude" to quit'; sleep 2
rm -rf "$HOME/Library/Application Support/Claude-3p"
mkdir -p "$HOME/Library/Application Support/Claude-3p"

MODELS_JSON='[{"name":"ppio/pa/claude-opus-4-7","supports1m":true}, ...]'
defaults write com.anthropic.claudefordesktop inferenceProvider -string "gateway"
defaults write com.anthropic.claudefordesktop inferenceGatewayBaseUrl -string "https://api.llm.mioffice.cn/anthropic"
defaults write com.anthropic.claudefordesktop inferenceGatewayApiKey -string "sk-..."
defaults write com.anthropic.claudefordesktop disableDeploymentModeChooser -string "true"
defaults write com.anthropic.claudefordesktop deploymentOrganizationUuid -string "<UUID>"
defaults write com.anthropic.claudefordesktop inferenceModels -string "$MODELS_JSON"

open -a "Claude"
```

**结果**：✅ 激活成功。

### super-clean T2: 模拟"全新机器"

除了 T2 之外，还删除以下"可能的激活残留"，验证 T2 路径是否依赖这些：

- `~/Library/HTTPStorages/com.anthropic.claudefordesktop/`（Chromium cookies / localStorage）
- `~/Library/Caches/com.anthropic.claudefordesktop/` + `.ShipIt/`
- `~/Library/Application Support/Claude/`（非 -3p 目录，标准版遗留）
- `defaults delete com.anthropic.claudefordesktop`（整域）
- **keychain `Claude Safe Storage` / `Claude Key` 条目**（`security delete-generic-password -s "Claude Safe Storage" -a "Claude Key"`）

然后重做 T2 的 `defaults write` + 启动 app。

**结果**：✅ 激活成功。`ant-did` 被**新生成**（确认真正 first-launch，不是 warm path）。App 自行重建了 keychain 条目（证明 keychain 条目是 runtime 依赖、非"已激活"标记）。

## 四个曾经不确定的点 — 当前回答

| # | 问题 | 回答 |
|---|---|---|
| 1 | `~/Library/Application Support/Claude-3p/configLibrary/<uuid>.json` 的作用 | 当前本地用户 active config。`_meta.json` 的 `appliedId` 指向它，skill 应写这里 |
| 2 | 预写 `claude_desktop_config.json.enterpriseConfig` 能否激活 | 旧版实测能；当前不作为主路径 |
| 3 | `/Library/Managed Preferences/` machine scope 是否真被读 | 官方路径，留给 IT / MDM；skill 不写这条路径 |
| 4 | user-level plist 能否激活 | 旧版实测能；当前不作为主路径，只检测/清理残留 |

## 常见误解 / 坑

### Keychain `Claude Safe Storage` 不是"激活标记"

Electron apps 常用 `safeStorage` API 加密敏感数据。主加密 key 存在 keychain 的 "Claude Safe Storage" / "Claude Key" 条目里。**这个 key 是 app 运行时自举的 secret**，每台机器首次启动都会新建；删除后 app 启动时会**自动重建**新的 key（加密的历史数据会失效，但不影响启动逻辑）。

不要把这个 key 的存在当成"此机器已激活"的信号。本 skill 的 `install_cowork_config.py` **不读不写 keychain**。

### `configLibrary/<uuid>.json` 是当前本地主配置

旧研究曾把这个 UUID JSON 判断为 in-app wizard 草稿。Claude Desktop `1.6259.x` 之后，官方当前文档和本机实测都表明 `_meta.json` 的 `appliedId` 指向 active config，skill 应写这里。旧 plist 路径不再作为主路径。

### `deploymentOrganizationUuid` 要 persist

每次安装新生成一个 UUID 会让 telemetry 标签跳变。本 skill 把它持久化到 `~/.config/mify/cowork-deployment-uuid`，跨安装复用。

### BaseUrl scheme 的实测边界

Cowork 官方文档写 `inferenceGatewayBaseUrl` 必须 `https://`，这个要求对远端网关应继续遵守：直接连 Mify 时一律使用 `https://api.llm.mioffice.cn/anthropic`，不要退回旧的内网 CA URL。

本地 proxy 是例外路径：实测 Claude Desktop 可以使用 `http://localhost:<port>`，且这种 loopback-only HTTP 能避免 Electron 对自签 localhost CA 的 `ERR_CERT_AUTHORITY_INVALID` health check 误报。若用户的安全策略强制 HTTPS localhost，再显式使用 `--scheme https`，但要预期顶部 provider health warning 可能复现。

## 官方文档原文存档

以下片段来自 Anthropic Cowork 3P 文档（`https://claude.com/docs/cowork/3p/*`），保留原文作为 skill 开发依据。

### installation.md
> "Deploying the configuration before the app means end users open Claude for the first time and land directly in Cowork."
> "When the app launches and finds a managed configuration, it enters 3P mode automatically with no user sign-in or setup required."
> "When any managed source is present, it takes effect and the in-app configuration window becomes read-only."
> "Both managed paths are read; per-user wins on conflict."

### configuration.md
> "3P mode activates only when this key is set *and* the required credential keys for the selected provider are present and valid; otherwise the app launches in standard mode."
> "When a managed source is present, it wins and locally written values are ignored."
> "Configuration is read once at launch, so fully quit and reopen the app after any change."
> "All values are stored as strings in the OS preference store, even booleans and arrays."
> "Keys like `inferenceModels`, `disabledBuiltinTools`, and `coworkEgressAllowedHosts` must be JSON strings."
> "Local (user) location: `~/Library/Application Support/Claude-3p/configLibrary/`."

### data-storage.md
> "`claude_desktop_config.json` — Locally authored configuration (from the in-app configuration window). Ignored when a managed profile is present."
> "managed configuration values are read from the OS preference store / registry at launch and held in memory; never written to the application-data directory."
> "When the app first launches in 3P mode, it generates a random UUID" and writes it base64-encoded to `ant-did`.

### gateway.md
> `inferenceGatewayBaseUrl`: "Gateway base URL. Must be `https://`."
> `inferenceGatewayApiKey`: "The field cannot be empty, so if your gateway authenticates by network identity and does not require a key, set a placeholder value."
> Auth schemes: `bearer`（默认）/ `x-api-key` / `sso`
> `GET /v1/models` is optional. If the gateway implements it, Cowork on 3P auto-discovers available models; if not, set `inferenceModels` explicitly.
> Use the model IDs your gateway expects (for example `bedrock/us.anthropic.claude-opus-4-7` for a LiteLLM-style routing prefix).

注意：官网没有明文写“必须是 Anthropic 模型”。这个限制来自本机 Claude Desktop `1.6259.1` 运行时日志里的 `Invalid custom3p enterprise config` 报错，见上文“模型列表限制”。

### 全部已读页面清单
`/cowork/3p/overview` · `/installation` · `/configuration` · `/data-storage` · `/extensions` · `/feature-matrix` · `/legal` · `/local-access` · `/telemetry` · `/code` · `/web-tools` · `/gateway` · `/vertex` · `/vertex-google-sign-in` · `/bedrock` · `/foundry`

## 对本 skill 的约束 / 设计规范

1. **只写当前本地配置主路径**：`~/Library/Application Support/Claude-3p/configLibrary/<active-id>.json`，并维护 `_meta.json`。
2. **不写 MDM 路径**（`/Library/Managed Preferences/...`），不需要 sudo。
3. **永远不碰** keychain。
4. `inferenceModels` 只能包含 Claude/Anthropic gateway route；非 Claude Mify 模型要用于 Claude Code，不要用于 Claude Desktop Cowork 3P。
5. `configLibrary` 是原生 JSON；不要把 `inferenceModels` 字符串化。
6. 默认生产模型列表使用已验证 4 模型 baseline；实时 catalog 只通过 `--live-models` 显式启用。
7. 修复已有 profile 时优先 `--fix-models`，只改模型列表。
8. `deploymentOrganizationUuid` 读写 `~/.config/mify/cowork-deployment-uuid`，跨 install 复用。
9. 配置写入后**必须**重启 Claude.app 才生效 —— 脚本要检测 app 是否在跑并显式提示用户。
