# Persistent QA stack

本文件是流程，不是本机记忆。真实路径 / 账户 / 库名只来自 `local-dev.yaml` + `env_file`。

## 什么算“原来的 setup”

一套 persistent-qa 是这些东西绑在一起，缺一块就会像“没登录”或“provider 丢了”：

- 已在跑的 server / web（`server.port` / `server.web_port`）
- 已有 Postgres 库（`postgres.database`），不是 `make dev` 默认库
- Desktop userData（`desktop.user_data`）里的登录态
- `apps/desktop/.env.local` 把 Vite 指到 `server.url`
- daemon profile（`daemon.profile`）连同一 server
- 测试账户（`account.email`）是该库里的 owner，不是新注册用户

刷新代码时只替换 QA checkout 里的二进制。不要新建 userData、不要换 profile 名、不要新建数据库。

## Desktop 看起来没登录

先核对，不要急着重做登录：

1. 日志是否 `target API URL set to <server.url>`。若是 `:8080`，就是缺 `.env.local` 或启动时没读到它。
2. userData 是否仍是 `desktop.user_data`。换了 `DESKTOP_APP_SUFFIX` 等于新装一个 App。
3. 当前进程有没有继承 Work 会话的 `MULTICA_SERVER_URL=https://…`。有的话清掉再启。

指回正确 API + 原 userData 后，原 `localStorage` 会话通常会自己回来。仍要手工登录时：

- 邮箱：`account.email`
- 验证码：`env_file` 里 `account.verification_code_env` 的值
- 不要 `SendCode` 去造新用户

## 换 daemon 二进制

Desktop 启动时会缓存 bundled CLI version。进程还在时换 `apps/desktop/resources/bin/multica`，它会每几秒对比版本并重启 daemon，形成死循环。

正确顺序：停 Desktop → bundle-cli → 重启 QA daemon（完整 PATH）→ 再用同一 suffix / `.env.local` 启 Desktop。

启 daemon 时用 `env -i` 清掉当前任务的 `MULTICA_*`，只留 `HOME`、完整 `PATH`、`MULTICA_CONFIG_HOME`、`MULTICA_SERVER_URL=<server.url>`。

重新打开 Desktop 不代表旧 daemon 已经重启；原 profile 的进程可能继续存活并保留旧 PATH。重启后核对 daemon PID 和进程实际 PATH，用该 PATH 对预期 provider 逐个 `command -v`。`daemon status` 的 `Agents` 可能来自已登记或缓存信息，不足以证明当前 provider 可执行。最后用目标 workspace 的 `runtime list` 和 Desktop 按钮状态确认当前设备 Runtime 为 `online`；同名旧设备的离线记录不代表当前 daemon 失败。

## 查库

```bash
docker exec -i <postgres.container> psql -U <postgres.user> -d <postgres.database>
```

表名：`"user"`（必须引号）、`workspace`、`member`（不是 `workspace_member`）、`agent_runtime`、`agent_task_queue`、`comment`。

## 不要做的事

- 杀 `/Applications/Rollica.app` 或 `production.profile`
- 对 persistent-qa 跑 `teardown.sh` / `docker compose down`
- 用精简 PATH 起 daemon（会只剩 Codex 等少数 provider）
- 为了“方便”再 `pnpm dev:desktop` 而不带 suffix 和 `.env.local`
