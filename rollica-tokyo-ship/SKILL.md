---
name: rollica-tokyo-ship
description: 公司 Rollica 仓库 main 打上版本 tag 之后，一键把这一版铺到东京私服：A1 上重建前后端、把 CLI/Daemon 五平台二进制发到 park0er/rollica-cli、把 Apple Silicon 东京 Desktop 发到独立 tag tokyo-desktop。触发词：发版了部署东京、往东京私服部署、打包二进制和桌面端、一键私服发版、tokyo ship、vX.Y.Z 铺到私服。只做这三件事。不要用来改公司 FDS 正式包、不要动 VPN 的 443、不要改 Clash。
---

# 东京私服整包发版

公司仓库 `main` 已经打好 tag（例如 `v1.0.8`）之后，按下面顺序做完三件事。打包脚本已经存在，不要重写。

1. 东京 A1 前后端：rsync 源码 + `docker compose` 本地镜像，保留 `.env` 和 Postgres。
2. CLI / Daemon：`rollica-cli-release` 的 `package-cli.sh <version> --upload`。GitHub Latest 必须是这个 CLI tag。
3. 东京 Desktop（仅 darwin/arm64）：`deploy/tokyo-private/package.sh --upload`。制品进 tag `tokyo-desktop`，**不能**变成 GitHub Latest。版本号用这次 tag 的 `X.Y.Z`，不要另起一个号。上传前包里必须有可执行的 `app.asar.unpacked/resources/bin/multica`；没有就停，这包装上也不能跑本机 daemon。

细节命令、排除项和验收见 [references/runbook.md](references/runbook.md)。开始前先读它。给人装客户端时只复制 runbook 里「给人装到东京」那一节，不要另写一套，也不要写版本号。

不要在东京那台 Linux 服务器上再装一份客户端二进制。A1 上的 daemon 不在这套安装命令里。

## 版本从哪来

- 用户给出 tag 就用那个 tag。
- 否则 `git fetch origin --tags` 后 `git describe --tags --exact-match origin/main`。main 不是恰好一个 tag 就停，不要拿分支尖端冒充已发布版本。
- CLI tag 带 `v`（`v1.0.8`）。Desktop 的 `ROLLICA_TOKYO_DESKTOP_VERSION` 不带 `v`（`1.0.8`）。
- 源码必须是该 tag 的 detached checkout 或单独 worktree。不要在脏的功能分支上打包。

## 不要动

- `/etc/caddy/Caddyfile` 里已有的 `/health* /healthz /readyz` 转发。部署后若 `http://141.147.189.28/health` 不是 `200 {"status":"ok"}`，按 runbook 补回去。Caddy 只听 80。
- 443 上的 xray（VPN）。不要给 Rollica 开 HTTPS，除非用户本轮明确要求。
- `.env`、Postgres volume、公司 `/Applications/Rollica.app`、Clash。
- 不要把 `tokyo-desktop` 标成 Latest。上传后用 `gh api repos/park0er/rollica-cli/releases/latest` 核对 tag 仍是 CLI 的 `vX.Y.Z`。若被抢走：`gh release edit vX.Y.Z --repo park0er/rollica-cli --latest`，再 `gh release edit tokyo-desktop --repo park0er/rollica-cli --latest=false`。

## 做完必须回报

- A1：commit、`/health`、`/login`、backend 容器里的版本变量。
- CLI：release URL。Mac 和个人 Linux 用 runbook 里那条 `releases/latest/download/install.sh`，不要把版本号写进命令。
- Desktop：`latest-mac.yml` 的 version，以及 runbook 里的东京 Desktop 安装命令。说明这行只装 `/Applications/Rollica Tokyo.app`。
- Windows 用 runbook 里的 PowerShell，不要发 bash。
- 若当前在 Rollica issue 会话里，把结果写回该 issue，署名模型名。无代码改动就不要开 PR。
