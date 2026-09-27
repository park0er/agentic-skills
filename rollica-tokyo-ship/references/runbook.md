# 东京私服发版 runbook

## 机器与路径

| 项 | 值 |
|---|---|
| 公司仓库 | `https://git.n.xiaomi.com/biz-ai-lab/rollica.git` |
| A1 | `ubuntu@141.147.189.28` |
| SSH key | `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1/KEY/OracleCloud/ssh-key-2026-07-04-private.key` |
| A1 源码 | `/home/ubuntu/rollica`（无 git。GitLab 从东京拉不到，用 rsync） |
| Compose | `docker-compose.selfhost.yml` + `docker-compose.selfhost.build.yml` |
| 镜像 | `multica-backend:dev`、`multica-web:dev`。不要 `docker compose pull`，不要用 GHCR latest |
| GitHub | `park0er/rollica-cli` |
| CLI 脚本 | `~/.agents/skills/rollica-cli-release/scripts/package-cli.sh` |
| Desktop 脚本 | 仓库内 `deploy/tokyo-private/package.sh` |
| Desktop tag | `tokyo-desktop`（不是 Latest） |
| 签名 | `Apple Development: parker.z@live.cn (HHR7QNK66G)`，Team `373JSZMNM5` |
| 公网 | `http://141.147.189.28`（HTTP。443 是 VPN） |

A1 上 Go 模块走公网代理。Dockerfile 默认是小米内网 GOPROXY，东京访问不到。backend build 必须带：

```bash
--build-arg GOPROXY=https://proxy.golang.org,direct --build-arg GOSUMDB=off
```

## 1. 同步并部署 A1

在 tag checkout 根目录：

```bash
KEY="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1/KEY/OracleCloud/ssh-key-2026-07-04-private.key"
rsync -az --delete \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude 'node_modules/' \
  --exclude '.next/' \
  --exclude 'apps/desktop/dist/' \
  --exclude 'dist/' \
  --exclude '.deploy-commit' \
  --exclude '.deploy-version' \
  -e "ssh -i \"$KEY\" -o BatchMode=yes" \
  ./ ubuntu@141.147.189.28:/home/ubuntu/rollica/
```

`--delete` 不会删被 exclude 的 `.env`。同步后在 A1 上确认 `.env` 仍在，再写 `.deploy-commit` / `.deploy-version`。

构建（`VERSION` 用 `v1.0.8` 这种带 v 的字符串，`COMMIT` 用 tag 的短 SHA）：

```bash
cd /home/ubuntu/rollica
export VERSION=vX.Y.Z COMMIT=<shortsha> DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
export NEXT_PUBLIC_APP_VERSION=$VERSION
docker compose -f docker-compose.selfhost.yml -f docker-compose.selfhost.build.yml build \
  --build-arg GOPROXY=https://proxy.golang.org,direct \
  --build-arg GOSUMDB=off \
  backend
docker compose -f docker-compose.selfhost.yml -f docker-compose.selfhost.build.yml build frontend
docker compose -f docker-compose.selfhost.yml -f docker-compose.selfhost.build.yml up -d \
  --no-build --force-recreate --no-deps backend frontend
```

只 recreate backend 和 frontend。不要 recreate postgres。

验收：

```bash
curl -fsS http://127.0.0.1:8080/health    # {"status":"ok"}
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1/login   # 200
curl -fsS http://141.147.189.28/health    # 公网也必须是 200 JSON，不能是 Next 的 404 HTML
```

公网 `/health` 若是 404 HTML，Caddy 把 `/health` 转到了前端。`/etc/caddy/Caddyfile` 的 `@api` 必须包含 `/health* /healthz /readyz`，然后 `sudo systemctl reload caddy`。不要改 `auto_https off`，不要监听 443。

backend 日志若 migration 失败，停在这里修，不要继续对外说部署成功。

## 2. CLI 发到 GitHub

在同一个 tag checkout：

```bash
~/.agents/skills/rollica-cli-release/scripts/package-cli.sh vX.Y.Z --upload --repo-dir "$PWD"
```

脚本会编 darwin/arm64、darwin/amd64、linux/arm64、linux/amd64、windows/amd64，并上传 `checksums.txt` 和 `install.sh`。新 tag 用 `--latest=true` 创建，这是对的。

验收：

```bash
gh api repos/park0er/rollica-cli/releases/latest --jq .tag_name   # 必须是 vX.Y.Z
```

发布验收只核对 GitHub Latest 是这次 CLI tag。给人安装时用下一节的命令，不要把 `vX.Y.Z` 写进安装地址。

## 3. 东京 Desktop（Apple Silicon）

本机要能看到签名身份 `Apple Development: parker.z@live.cn (HHR7QNK66G)`。没有就停，不要打 ad-hoc 包。

```bash
pnpm install --frozen-lockfile
ROLLICA_MAC_SIGNING_IDENTITY='Apple Development: parker.z@live.cn (HHR7QNK66G)' \
ROLLICA_TOKYO_DESKTOP_VERSION=X.Y.Z \
  ./deploy/tokyo-private/package.sh --upload
```

默认版本号在脚本里仍是 `0.0.6`，不传 `ROLLICA_TOKYO_DESKTOP_VERSION` 会发错版本。Desktop 版本跟这次 tag 相同（`1.0.8` 就还叫 `1.0.8`），不要为了修包私自改成 `1.0.9`。同一版本号覆盖 zip 后，已经装过这一版的机器不会弹出应用内更新，要重跑下面的安装命令。

`package.sh` 传给 electron-builder 的 `-c overlay.yml` 会**替换** `electron-builder.yml`，不是合并。overlay 必须有 `extends: electron-builder.yml`，否则 `asarUnpack: resources/**` 丢失：`multica` 被封进 `app.asar`，没有 `app.asar.unpacked`。Desktop 只从 unpacked 路径启动本机 daemon，这个包装上也不能跑 agent。打包前确认脚本里有 `extends: electron-builder.yml`；没有就先补上再打。

验收（缺一项就不要上传）：

- `Contents/Resources/app.asar.unpacked/resources/bin/multica` 存在且可执行
- zip 清单里有 `app.asar.unpacked/resources/bin/multica`
- `codesign --verify --deep --strict` 通过，TeamIdentifier=`373JSZMNM5`
- 包内 `runtime-config.json` 的服务器是 `http://141.147.189.28`
- GitHub `tokyo-desktop` 上的 `latest-mac.yml` version 等于 `X.Y.Z`
- `releases/latest` 仍是 CLI tag，不是 `tokyo-desktop`

已装过同一张证书的东京 App 可以走应用内更新。无签名旧包不能，必须重跑安装命令。同一版本号覆盖 zip 后，已经装过这一版的机器也不会弹出更新，同样要重跑。

## 给人装到东京

只服务东京私服 `http://141.147.189.28`。三选一，不要混用。不要在 A1 这台 Linux 服务器上再装客户端二进制。

新机器的 CLI profile 名用 `tokyo`。这台 iMac 上已经有的那份 profile 名叫 `a1`，指的是同一台服务器，不要再为它建一个 `tokyo`。

### Mac，以及个人 Linux 电脑

终端，不是 Git Bash on Windows：

```bash
curl -fsSL https://github.com/park0er/rollica-cli/releases/latest/download/install.sh | bash
```

然后：

```bash
multica --profile tokyo setup self-host --server-url http://141.147.189.28 --app-url http://141.147.189.28
multica --profile tokyo login --token
multica --profile tokyo daemon start
multica --profile tokyo daemon status
```

`install.sh` 在 Windows 上会直接退出。Mac 上公司 `Rollica.app` 里的 `multica` 不要用这条去替换。

### Windows（64 位 Intel/AMD）

PowerShell 5.1 或 7。不要用 Git Bash。骁龙 ARM 电脑没有对应包。

```powershell
$ErrorActionPreference = "Stop"
$Repo = "park0er/rollica-cli"
$Headers = @{ "User-Agent" = "rollica-tokyo-install" }
$Release = Invoke-RestMethod -Headers $Headers -Uri "https://api.github.com/repos/$Repo/releases/latest"
$Version = $Release.tag_name.TrimStart("v")
$Dest = Join-Path $env:USERPROFILE ".rollica-cli\bin"
$Config = Join-Path $env:USERPROFILE ".rollica-cli"
New-Item -ItemType Directory -Force -Path $Dest, $Config | Out-Null
$Zip = Join-Path $env:TEMP "multica-cli-$Version-windows-amd64.zip"
$Url = "https://github.com/$Repo/releases/download/v$Version/multica-cli-$Version-windows-amd64.zip"
Invoke-WebRequest -Headers $Headers -Uri $Url -OutFile $Zip -UseBasicParsing
Expand-Archive -Path $Zip -DestinationPath $Dest -Force
Set-Content -Path (Join-Path $Config "update-source") -Value $Repo -NoNewline
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$Dest*") {
  [Environment]::SetEnvironmentVariable("Path", "$Dest;$userPath", "User")
}
$env:Path = "$Dest;$env:Path"
[Environment]::SetEnvironmentVariable("ROLLICA_UPDATE_REPO", $Repo, "User")
[Environment]::SetEnvironmentVariable("MULTICA_RELEASES_API", "https://api.github.com/repos/$Repo/releases/latest", "User")
[Environment]::SetEnvironmentVariable("MULTICA_DAEMON_AUTO_UPDATE", "true", "User")
$env:ROLLICA_UPDATE_REPO = $Repo
$env:MULTICA_RELEASES_API = "https://api.github.com/repos/$Repo/releases/latest"
$env:MULTICA_DAEMON_AUTO_UPDATE = "true"
& "$Dest\multica.exe" --version
```

关掉窗口，新开一个 PowerShell，再：

```powershell
multica --profile tokyo setup self-host --server-url http://141.147.189.28 --app-url http://141.147.189.28
multica --profile tokyo login --token
multica --profile tokyo daemon start
multica --profile tokyo daemon status
```

Windows 没有开机自启。电脑重启后要再执行一次 `multica --profile tokyo daemon start`。

### 东京 Desktop（仅 Apple Silicon Mac）

不要用 CLI 那条，也不要装到公司的 Rollica.app：

```bash
curl -fsSL https://github.com/park0er/rollica-cli/releases/download/tokyo-desktop/install-desktop-tokyo.sh | bash
```

装到 `/Applications/Rollica Tokyo.app`。第一次若被系统拦住：右键 → 打开。

## 顺序

A1 的 docker build 和本机 CLI 交叉编译可以并行。Desktop 的 electron 打包吃内存，不要和 CLI 交叉编译同时跑。先确认 A1 `/health` 再对用户说私服已更新。
