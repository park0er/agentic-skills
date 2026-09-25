---
name: rollica-local-dev
description: Local Rollica/Multica QA, dev testing, and isolated Staging Desktop packaging on macOS or Windows. Use when the user says 本地测试 / QA app / 起本地栈 / 刷新 QA daemon / 测我改的 daemon 或 Desktop / Staging App / 隔离 Staging 包 / Windows Staging 包 / rollica-local-dev / multica-local-dev. Machine-specific paths, ports, test account, and DB live in ~/.rollica/local-dev.yaml — never hardcode them. Default testing mode is persistent QA (keep DB + Desktop login). Never touch production Rollica. Skip cloud/production management and use the current authenticated Rollica CLI tooling instead.
---

# Rollica local dev

本机测 Rollica / Multica 改动。机器相关信息**不写在本 skill 里**，只从本地配置读。

## 第一步：读本机记忆

```bash
python3 "<skill-dir>/scripts/load_config.py" doctor
```

配置文件只认这一处（按顺序）：

1. `$MULTICA_CONFIG_HOME/local-dev.yaml`
2. `~/.rollica/local-dev.yaml`

QA 或 ephemeral 栈没有这份文件就停。把 `templates/local-dev.yaml` 拷到上面的路径并填好，再继续。不要把某台电脑的绝对路径写回 skill。

例外：用户只要隔离 Staging 包、且本机没有这份配置时不要停。Staging 包不读 QA 账户、端口或数据库。仍然不要动本机已安装的正式 Rollica。

`env_file` 里才有 `DATABASE_URL`、验证码等秘密。需要登录码时从该文件读 `account.verification_code_env` 指出的键，不要抄进回复。

`<skill-dir>` = 本 `SKILL.md` 所在目录。

## 两种栈

| kind | 含义 | 默认动作 |
|---|---|---|
| `persistent-qa` | 长期 QA：保留数据库、Desktop userData、测试账户 | 尊重现有 setup，只换需要测的二进制 |
| `ephemeral` | 一次性 `make dev` | 可按旧流程起栈 / teardown |

`local-dev.yaml` 的 `kind` 决定走哪条。本机日常 QA 是 `persistent-qa`。细则见 [references/persistent-qa.md](references/persistent-qa.md)。

## persistent-qa：硬规则

读完配置后必须遵守：

1. **不要动 production。** `production.app` 和 `production.profile`、以及 `daemon.do_not_touch_profiles` 里的 daemon，一律不杀、不重启、不换二进制。
2. **不要另起一套 Desktop。** 用配置里的 `desktop.app_suffix` / `user_data` / `renderer_port` / `env_local`。缺 `apps/desktop/.env.local`（`VITE_API_URL` = `server.url`）时 Desktop 会落到 `:8080`，看起来像“没登录”。
3. **不要清测试账户。** 登录用 `account.email` + `account.workspace_slug`。验证码来自 `env_file`，不要新建用户。
4. **不要继承当前 Work/Agent 会话的 `MULTICA_*`。** 操作 QA daemon / Desktop 时清掉 `MULTICA_SERVER_URL`、`MULTICA_TOKEN`、`MULTICA_TASK_ID`、`MULTICA_DAEMON_PORT`、`MULTICA_WORKSPACE_ID`。否则 QA daemon 会去连正式环境。
5. **Daemon 要用这台电脑真实的 login-shell PATH。** 这样才会扫到本机全部 provider（Grok / Claude / Codex / Pi / …）。不要用精简 PATH 起 daemon。启动后检查 daemon **进程实际继承的 PATH**，并用该 PATH 对预期 provider 逐个 `command -v`；`daemon status` 的 `Agents` 可能包含已登记或缓存项，不能单独证明当前可执行。
6. **换 daemon 二进制时：** 在 QA checkout 里 `bundle-cli`，只重启 `daemon.profile`，然后用**同一套** suffix + `.env.local` 重启 Desktop。Desktop 还活着时换二进制会因版本缓存反复自杀重启。
7. **禁止**对 persistent-qa 跑 `scripts/teardown.sh`，除非用户明确说要拆掉整套 QA。

## Mini 壳本地验收（macOS dev 模式）

Mini 没有 Desktop 那样的 Electron dev app，但也不需要打正式包（打包脚本要求 tag+签名，是发布流程）。自 commit `77f1aed6` 起 Mini 支持 `ROLLICA_MINI_API_URL` / `ROLLICA_MINI_APP_URL` 环境变量覆盖，可指向本地 QA 栈：

1. checkout 同步到含该 commit 的分支；`cd apps/mini-macos && swift build -c debug`
2. **裸可执行文件会崩**（NSStatusItem/UNUserNotificationCenter 需要 bundle 身份）。组一个最小 dev bundle：
   - `Contents/MacOS/` 放编译产物，然后 `install_name_tool -add_rpath @executable_path/../Frameworks <binary>` + ad-hoc 重签（否则 Sparkle dyld 加载失败）
   - `Contents/Frameworks/` 放 `.build/arm64-apple-macosx/debug/Sparkle.framework`
   - `Contents/Resources/bin/multica` 放**与运行中 daemon 版本一致**的 CLI（bundle 内资源优先于 PATH 解析；版本不一致会让 reconcile 把 daemon 换成错的二进制）
   - `Info.plist` 的 bundle id **不能是** `ai.rollica.desktop`（避免共存检测误判自己）
3. 启动前清掉继承的 `MULTICA_*`（同 persistent-qa 规则 4），再设 `ROLLICA_MINI_API_URL=<server.url>` 和 `ROLLICA_MINI_APP_URL=<web_url>`（API/web 分端口部署时登录页在 web 端口，不设 app_url 会 404）
4. 已知坑：
   - QA Desktop 的 Electron dev 进程不带 `ai.rollica.desktop` bundle id，Mini 的共存检测**看不见它**——两个壳会同时管理同一个派生 profile 的 daemon。验 Mini 时先退出 QA Desktop
   - profile 若已有 token，启动直接 reconcile + 开网页（不会走登录）；验 OAuth callback 登录先手动退出登录
5. Windows 壳在 macOS 上无法编译验收（无 dotnet SDK），只能代码级审查

刷新一条 daemon 改动的最短路径：

1. 把 commit 接到 `checkouts.qa`（不要重搭栈）
2. 在该 checkout 跑 `node apps/desktop/scripts/bundle-cli.mjs`
3. 用干净环境 + 完整 PATH 重启 `daemon.profile`
4. 确认 `multica daemon status --profile <daemon.profile>` 的 version 已变；检查 daemon 进程的实际 PATH 能逐个解析预期 provider
5. 重启 Desktop：`DESKTOP_APP_SUFFIX` + `DESKTOP_RENDERER_PORT` + 已有 `.env.local`
6. 用 `runtime list` 核对当前 workspace 中**当前设备 / daemon**的目标 Runtime 为 `online`，并在 Desktop 验证对应按钮可用；不要把同名旧设备的离线记录误判为当前 daemon
7. 日志里 `target API URL` 必须等于 `server.url`；应用应仍登录在 `account.workspace_slug`

## ephemeral：一次性栈

仅当 `kind: ephemeral` 或用户明确说“起一套全新 make dev”时：

- 中国网络先跑 `scripts/pgvector-mirror-pull.sh`
- `make dev` 起 server + web；daemon 必须用这个 checkout 编出来的 `server/bin/multica`
- 登录：`scripts/local-daemon-login.sh`
- 拆：`scripts/teardown.sh`（只杀 ephemeral profile，不碰正式 App）

更多坑见 [references/troubleshooting.md](references/troubleshooting.md)。

## 隔离 Staging 桌面端包

用户要求“基于最新 develop 打一个 Staging App / Staging 包”时，这不是 QA App，也不是正式发布。先读 [references/staging-app-package.md](references/staging-app-package.md)，在最新 `origin/develop` 的独立干净 worktree 中构建，不改当前功能分支，不复用 QA 或正式桌面端状态，只输出用户要求的架构。

在 Windows 上打包时，读该文档的 **Windows** 专区，不要改写 macOS 合同。Windows overlay 必须把 `package.json` 的 `name` 改成 `@multica/desktop-staging`。只改 `productName` 和 `appId` 时，NSIS 仍会装进正式版目录。另外：拉完代码先 `pnpm install --frozen-lockfile` 再打包；命令必须带 `--publish never`；只构建用户要的架构；启动前确认没有别的 checkout 留下的 Rollica 进程把单实例锁占住。内置浏览器 vendor 的校验和按 git 对象原文计算，不要把那些文件当文本做换行转换。

## 方案型 Issue 进展同步

当工作已绑定 Rollica Issue 并更新进展时，若本次内容涉及架构、设计、实施、测试、发布或迁移方案，尽量把该次方案的完整、已定稿材料全部作为同一条评论的附件上传：至少包含 Markdown 真相源和配套 HTML 阅读版，以及直接支撑方案的图表或其他文件。同时在评论正文写出结论、取舍和验证摘要，不要让读者只能靠下载附件才知道进展。

“方案型”不包括纯状态通知、单个 commit 或例行测试结果。上传前排除密钥、本机配置、个人信息、临时草稿和无关日志。若 Issue 通道不支持附件、文件超限或材料不宜上传，在评论里说明原因并提供同等可访问的持久链接。写入后重读 Issue，确认每个附件或链接都对其他成员可见。

## 个人经验

可复用的非机器信息写 `~/.rollie/learnings/rollica-local-dev/learnings.md`。  
路径、端口、账户、库名只写 `local-dev.yaml`，两处不要重复。
