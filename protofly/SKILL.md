---
name: protofly
description: 把本地 HTML 文件发布到小米内网 proto-fly (https://protofly.v.mitvos.com)，拿到一个内网可访问的 https 链接发给同事。触发条件包括：用户产出 HTML 后说"发给同事看 / 给 XXX review / 内部分享 / 内网分享 / 内部 demo / 公司内部链接 / 把这个 HTML 发出去 / 给老板看一眼"，或直接说"用 proto-fly / protofly / 上传到 protofly / 发到内网 / 挂到 mitvos"，或贴出 protofly.v.mitvos.com / protofly-mcp.v.mitvos.com 链接，或问"这个 HTML 怎么分享给小米同事"。也覆盖 tariq-html / kami / deckify / frontend-design / huashu-design / guizang-ppt-skill 等输出 HTML 后立刻要分享的场景。Skip when 用户要发到公网（用其他托管）、要分享非 HTML 文件、或只是本地预览不准备发出去。
---

# proto-fly：把 HTML 挂到小米内网拿分享链接

## 这个 skill 解决什么

很多技能（tariq-html、kami、deckify、frontend-design、huashu-design、guizang-ppt-skill 等）都会输出**单文件 HTML** 给用户做内部 demo / review / 演讲 / 周报展示。问题是：

- AirDrop 给同事看不方便
- 飞书附件每次都要重传
- 公司内网外部分享需要 VPN，外站不可用
- 飞书云文档不能跑动画 / WebGL / Canvas

**proto-fly**（小米内部产品）就是来解决这一段的：你把 `.html` 上传到 `https://protofly.v.mitvos.com`，它给你一个内网链接 `https://protofly.v.mitvos.com/view/<resource_id>`，飞书账号已授权的同事直接打开就能看，不用 VPN（小米内网内）、不用走相册、版本可回溯。

本 skill 通过 **mcporter** 直接调用 proto-fly 的 5 个 MCP 工具，不需要写新的 HTTP client。`mcporter call protofly.<tool>` 就是 CLI。

## 何时触发（强烈触发优先于克制）

凡是有 HTML 文件 + 想发给小米同事看，就该触发。具体信号：

1. **HTML 刚生成**：刚跑完任意能产出单文件 HTML 的 skill（tariq-html、kami、deckify、interviewer、frontend-design、huashu-design、guizang-ppt-skill），用户说"发给 X 看 / 给老板看 / 同事 review / 内部分享 / 跟 PM 对一下 / 周一会上要展示"。
2. **关键词触发**：用户原话出现 `proto-fly`/`protofly`/`mitvos`/`内网链接`/`内网分享`/`内部 demo`/`挂到内网`/`托管 HTML`。
3. **链接触发**：聊天里出现 `protofly.v.mitvos.com` 或 `protofly-mcp.v.mitvos.com`，无论是用户贴的还是历史返回的。
4. **明确请求**：用户问"我这个 HTML 怎么分享给小米同事"、"内网怎么发 HTML"、"做完了怎么给别人看"。
5. **版本迭代**：用户说"再发一版 / 我改了，再传一次 / 这个 HTML 再上一版"，且历史里能看到是 protofly 的资源（`PF` 前缀的 resource_id）— 用 `--resource-id` 追加版本。
6. **可见性切换**：默认就是 public（任何拿到链接的小米内网同事都能看）。**只在用户主动说**"敏感 / 私密 / 加授权 / 改回私有 / 不要让所有人都能看"才走 `--private` 或 `set_visibility private`；反过来用户说"放开 / 改回公开"则用 `set_visibility public`。

**不触发**：发公网（用 r2 / vercel / GitHub Pages 等其他渠道）；分享 .pdf / .docx / 图片（proto-fly 只收 HTML）；用户只想本地 `open file://` 预览不准备分享。

## 前置：装 token

`mcporter` 通过 `~/.mcporter/mcporter.json` 里挂的 `Authorization: Bearer <jwt>` 访问 protofly。token 来自 `https://protofly.v.mitvos.com` 的"控制台 → 设置 → MCP Token"（飞书登录后可生成）。

### 一键安装协议

如果用户贴出疑似 token（一段 `eyJ...` 开头、形如 `xxx.yyy.zzz` 三段 JWT），或说"这是我的 protofly token"，按下面流程走，不要额外反问：

```bash
printf %s '<TOKEN>' | python3 ${SKILL_DIR}/scripts/install_token.py
```

- **必须用 `printf %s`，不要用 `echo`**：避免 shell 对反斜杠转义破坏 token。
- **必须用单引号包 token**：避免 `$`、`!`、反引号被 shell 解释。
- 脚本会校验 JWT 格式 → 检查 exp（过期/快过期会警告/报错）→ `mcporter config remove protofly`（如已存在）→ `mcporter config add protofly` → 用 `list_resources` 实测一次。

### 安全规则（你和用户都遵守）

- ✓ token 只放进用户自己的 `~/.mcporter/mcporter.json`（mcporter 的标准位置）。
- ✗ **禁止**把 token 写进 skill 目录（SKILL.md / scripts / references）、项目源码、commit/PR/issue、workspace 输出，或任何会被 rsync / iCloud 同步分享的位置。
- ✗ 用户在对话里贴了 token，**不要** echo 到 log，不要写入除 `~/.mcporter/mcporter.json` 外的任何文件。
- ✗ 检查 `~/.mcporter/mcporter.json` 的内容时，**不要把 Authorization 头打印出来**，只验证存在性。

### token 失效或过期

`scripts/status.py` 会报告 `state: token_expired` / `token_expiring_soon`。处理：

1. 让用户去 `https://protofly.v.mitvos.com` 控制台重新生成一个 token；
2. 复制后照"一键安装协议"重新跑 `install_token.py`，旧 entry 会被自动 remove。

## 标准工作流

### Step 1：检查健康

每次开始 protofly 操作前，先跑：

```bash
python3 ${SKILL_DIR}/scripts/status.py
```

可能的输出：

| state | 含义 | 处理 |
|---|---|---|
| `token_ok` + `reachable: true` | 一切正常 | 继续 |
| `not_configured` | 没装过 token | 走"一键安装协议" |
| `token_expired` | JWT 过期 | 让用户拿新 token，重装 |
| `token_expiring_soon` | <7 天到期 | 提醒用户更新，仍可继续用 |
| `reachable: false` | 配置在但访问不通 | 多半没连小米 VPN / 内网；让用户连上再试 |

### Step 2：上传 HTML（默认 = 发布 + 公开）

```bash
python3 ${SKILL_DIR}/scripts/upload.py /path/to/file.html --description "Q2 规划草案 v3"
```

输出（人类可读）：

```
resource_id : PF26051800580010BD05
version     : 1
size        : 384.2 KB
published   : v1
view url    : https://protofly.v.mitvos.com/view/PF26051800580010BD05
visibility  : public  (anyone in Xiaomi network with the link can view)
```

- **默认就把这一版 publish 出去 + `set_visibility public`**：拿到 `view url` 直接发同事，不用对方加授权、不用走选人组件，最贴合"发给同事看一眼"的主用例。
- 直接把 `view url` 复给用户。给用户回报时**不要**再附 preview 链接（preview 是 owner-only，发给别人就 403，徒增混乱）。
- `--description` 只在新建时生效，已有资源加版本不会改 description。

### Step 3：可见性变体（私有 / 草稿）

`upload.py` 的可见性是三选一互斥开关，**不传任何 visibility flag = 默认 public**：

| 场景 | 命令 | 结果 |
|---|---|---|
| 默认（推荐）：公开发出去 | `upload.py file.html` | publish + set_visibility public，`view url` 任意网内同事可访问 |
| 敏感内容 / 想要授权清单 | `upload.py file.html --private` | publish + set_visibility private，`view url` 只有 protofly 控制台授权过的同事能看 |
| 还没写完，先草稿 | `upload.py file.html --draft` | 不 publish，仅 owner 通过 `preview url` 可见；后续 `--publish` 时再决定可见性 |

`--public` / `--publish` 仍然接受（作为默认行为的别名），不会报错，但写不写都一样。

### Step 4：随时切换可见性

资源已存在但要换模式：

```bash
# 改公开（默认就是这个，只在之前选了 --private 后才需要）
mcporter call protofly.set_visibility resource_id:<rid> visibility:public

# 改私有（用户说"收回 / 改回私有 / 加上授权"）
mcporter call protofly.set_visibility resource_id:<rid> visibility:private
```

### Step 5：列举 / 查看历史

```bash
# 列我的资源（默认每页 20）
mcporter call protofly.list_resources page:1 page_size:20

# 单个资源详情，含全部历史版本
mcporter call protofly.get_resource resource_id:PF26051800580010BD05
```

### Step 6：迭代（同一资源新版本）

用户说"再发一版"或要求 v2、v3：用 `--resource-id` 追加，**不要**重新创建。

```bash
python3 ${SKILL_DIR}/scripts/upload.py file.html --resource-id PF26051800580010BD05
```

新版本默认照样 publish + 保持 public。`preview` 永远指向最新草稿，`view` 永远指向最新已发布版本，URL 不变 → 之前发出去的链接对同事自动看到新版本。如果只想悄悄留个草稿不更新 view，加 `--draft`。

## CLI 命令对照表（mcporter 直调）

5 个 MCP 工具一对一映射到 `mcporter call protofly.<tool>`。除 `create_resource` 因 base64 较长需走 `--args <json>`（用 `upload.py` 包好），其余用 `key:value` 即可。

| MCP 工具 | CLI 调用 | 必填参数 | 可选参数 |
|---|---|---|---|
| `create_resource` | **走 `upload.py`**（避免 shell 截断长 base64） | `filename`, `file_content`(b64) | `description`, `resource_id` |
| `list_resources` | `mcporter call protofly.list_resources [page:N] [page_size:N]` | — | `page`, `page_size` |
| `get_resource` | `mcporter call protofly.get_resource resource_id:<id>` | `resource_id` | — |
| `publish_resource` | `mcporter call protofly.publish_resource resource_id:<id> [version:N]` | `resource_id` | `version`（默认最新草稿） |
| `set_visibility` | `mcporter call protofly.set_visibility resource_id:<id> visibility:public\|private` | `resource_id`, `visibility` | — |

完整字段 schema 和返回示例见 `references/api.md`。

## 常见坑

1. **直调 `mcporter call protofly.create_resource file_content:<huge-b64>` 报 `file_content is required`**：base64 字符串里的 `+`/`=` 在 zsh/bash 下被当成字段分隔符或参数 expansion，长字符串经常被截断。**永远走 `upload.py`**，它内部用 `--args <json>` 一次性灌进去。
2. **`preview` 链接转给别人 403**：`preview` 是 owner-only 的草稿链接，发给别人就是 403。先 `--publish` 再发 `view` 链接。
3. **`view` 链接同事打不开**：默认 `upload.py` 已经把可见性置为 public，理论上拿到链接 + 在小米内网就能看。常见排查：（a）对方不在小米网内 / 没连 VPN，protofly 是内网域名；（b）你跑的是 `--private` 或资源在控制台被改回私有了，跑 `mcporter call protofly.get_resource resource_id:<rid>` 看 `visibility` 字段（`20` = public, `10` = private）；（c）用户**主动**要私有，那就维持 private + 让用户在控制台加授权清单。
4. **不在小米内网/VPN**：`status.py` 会报 `reachable: false`。protofly.v.mitvos.com 是内网域名，VPN 断了就访问不到。
5. **"我都改了 N 版了，越发越多资源"**：用户多半希望新版本累积在同一个 `resource_id` 下，不是每次新建。问一下"这是新东西还是上次那份的迭代？"，然后用 `--resource-id` 追加。
6. **API 返回 visibility 字段不一致**：`set_visibility` 响应里 `visibility` 是字符串 `"public"`/`"private"`；`get_resource` 响应里 `visibility` 是整数 10（private）/ 20（public）。语义一致，类型不同；`status.py` / `upload.py` 不解析这个字段，直接显示 raw 值。
7. **token 有效期**：JWT 通常 30 天。`status.py --json` 里看 `token_expires_at`。提前一周提醒用户。

## 输出契约

每次操作完，给用户回报时**必须包含**：

- 资源 `resource_id`（用户拿来追踪 / 后续迭代）
- 链接（默认 `view url` 直发；`--draft` 模式下才用 `preview` 并加"仅你自己可见，要分享请先 publish"提示）
- 当前可见性（默认 public 时也写一行"public — 同事拿到链接即可看，无需授权"，避免用户误以为还要在控制台加权）

不要回报：完整 token、Authorization header、用户的 open_id。

## 文件清单

- `scripts/install_token.py` — 一键装 token（走 stdin，校验，注册到 mcporter）
- `scripts/upload.py` — 上传 HTML（处理 base64 + 可选 publish/public）
- `scripts/status.py` — 健康检查（配置、token 过期、可达性）
- `references/api.md` — 5 个 MCP 工具的完整 schema + 返回示例（按需读取）
- `CHANGELOG.md` — release 历史
