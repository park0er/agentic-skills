# 隔离 Staging 桌面端打包

用于从最新远端 `develop` 生成可与正式 Rollica、QA App 共存的内部 Staging 桌面端包。它连接共享 Staging 服务，但不改 Server、数据库或部署。

## 合同

- **代码源**：先 `git fetch origin --prune`，记录 `origin/develop` 完整 SHA；用独立 detached worktree 构建。不得把当前功能分支、未提交文件或其他远端分支混入。
- **服务地址**：内置 `http://staging-rollica.ad.xiaomi.srv`，WebSocket 为 `ws://staging-rollica.ad.xiaomi.srv/ws`。通过 `extraResources/runtime-config.json` 提供，不依赖构建机的 `.env.local`。
- **产品身份**：`productName = Rollica Staging`、`appId = ai.rollica.desktop.staging`。仓库的 branded-edition 机制应据此派生 `~/Library/Application Support/Rollica Staging` 与 `~/.rollica-staging`；不得读取或写入正式 `Rollica` / `~/.rollica`，也不得复用 QA userData/profile。
- **深链边界**：当前登录合同仍使用 `rollica://`，安装/启动 Staging 可能把系统默认 Rollica 深链处理器切到 Staging。不得把“状态目录隔离”表述成“所有系统集成都隔离”；改独立 scheme 前必须先确认 Staging 登录回调端到端支持，不能只改 `electron-builder.yml`。
- **更新通道**：Staging 包不得启用正式 Rollica 自动更新源，否则可能被正式包覆盖。打包 overlay 必须关闭 updater，且 `--publish never`。
- **架构**：按用户要求构建；用户只要 Apple Silicon 时仅传 `--mac --arm64`，不要顺手生成 Intel/universal。
- **源码纪律**：Staging 身份、运行配置和 updater 开关只作为打包 worktree 的 overlay，不 commit、不 push；业务代码必须保持 `origin/develop` 原样。最终说明基线 SHA 与 overlay 内容。

## 最短流程

1. 运行本 skill 的 `load_config.py doctor`，确认正式 App/profile 的不可触碰边界。
2. fetch 后创建唯一临时目录：`git worktree add --detach <temp-worktree> origin/develop`；确认 `HEAD` 等于刚记录的远端 SHA。
3. 在临时 worktree 做最小 overlay：
   - `apps/desktop/package.json`：只把 `productName` 改为 `Rollica Staging`。
   - `apps/desktop/electron-builder.yml`：把 `appId` / `productName` / artifactName 改为 Staging；加入 `runtime-config.json` 的 `extraResources`；关闭 notarize，但用 `identity: "-"` 给内部包做完整 ad-hoc 签名。
   - `apps/desktop/runtime-config.json`：写入上述 Staging API、WS、App URL 和 `schemaVersion: 1`。
   - `apps/desktop/src/main/index.ts`：仅 `app.getName() === "Rollica"` 时注册正式 updater。
4. `pnpm install --frozen-lockfile`，再跑桌面端 typecheck 和 `desktop-state-migration`、`runtime-config-loader` 定向测试。
5. 构建 Apple Silicon 内部包：

   ```bash
   CSC_IDENTITY_AUTO_DISCOVERY=false \
     pnpm --filter @multica/desktop package -- --mac --arm64 --publish never
   ```

6. 把 DMG、ZIP 和 SHA-256 复制到稳定输出目录；不要把构建产物提交进仓库。

## 验包门槛

逐项实际检查后才能交付：

- `Info.plist`：`CFBundleIdentifier=ai.rollica.desktop.staging`，名称为 `Rollica Staging`。
- 主可执行文件：`file` 显示 `arm64`（若用户要求 Apple Silicon）。
- `codesign --verify --deep --strict <app>` 通过；不能把“跳过签名”误写成普通的“未公证”。
- `Contents/Resources/runtime-config.json`：三个 URL 都指向 Staging。
- ASAR/源码验证：正式 updater 对 Staging 未启用。
- 隔离逻辑定向测试通过；说明状态目录是 `Rollica Staging` 与 `.rollica-staging`。
- 产物版本和内置 CLI 的 commit 对应记录的 `origin/develop` SHA；若打包 overlay 使 `git describe` 带 `-dirty`，明确这是身份/config overlay，不是混入业务改动。
- 内置 Runtime（包括 Pi）严格采用该 develop 基线的 manifest；若它不是其他分支的更新版本，明确告知用户，不私自跨分支拼装。

内部包只有完整 ad-hoc 签名、没有 Developer ID 公证，在另一台 Mac 首次打开仍可能触发 Gatekeeper；这是一次性交付成本。正式分发仍走仓库 release 文档要求的签名、公证和发布流程，不能拿本流程替代。

## Windows

只在用户要 Windows 包时走这里。不要顺手再打 macOS / Intel。macOS 合同保持原样。

### 构建

在独立 detached worktree 里，overlay 比 macOS 多改一项：`apps/desktop/package.json` 的 `name` 必须是 `@multica/desktop-staging`。其余仍是 `productName`、`appId`、`runtime-config.json`，以及仅 `app.getName() === "Rollica"` 时注册 updater。不要为了 Windows 去改 macOS 的 `notarize` / `identity`，也不要把这个 `name` 写回 macOS 流程。

Windows 安装目录不看 `productName`，也不看 `appId`。NSIS 单用户安装的目录名来自包名：保留 `@`，去掉 `/`。因此：

- `@multica/desktop` → `%LocalAppData%\Programs\@multicadesktop`，这是正式版目录
- `@multica/desktop-staging` → `%LocalAppData%\Programs\@multicadesktop-staging`

如果算出的目录不是后者，停止，不要安装。

注册表比这个推导更优先。NSIS 会先读 `HKCU\Software\<APP_GUID>\InstallLocation`；只要非空，就装回那个旧目录。`APP_GUID` 由 `appId` 决定，所以改了包名也挡不住已经被写错的键。安装前如果这个键指向正式版目录 `@multicadesktop`（没有 `-staging`），删掉 **staging 这个 GUID 键**。不要删正式版自己的注册表键，不要动正式版安装目录和它的 `desktop.json`。PowerShell 5.1 用 .NET 的 `RegistryKey.DeleteSubKeyTree`，不要用 `Remove-Item`。

同名安装器不要覆盖旧文件。`git describe` 带 `-dirty` 时，两次构建的文件名可以完全一样，旧的那个会把正式版盖掉。输出目录带上这次构建时间；交付时写明时间，避免拿错。

拉到新的 `origin/develop` 之后，即使目录里已有 `node_modules`，也先：

```bash
pnpm install --frozen-lockfile
pnpm --filter @multica/desktop package -- --windows --x64 --publish never
```

`--publish never` 不能省。检测到 CI 时，electron-builder 会去发 GitHub Release；没有 token 时任务末尾失败，但安装包本身可能已经打好。缺 `pnpm install` 时，新增依赖（例如 `ws`）会静默缺进包里，安装后启动即崩。

PowerShell 5.1 会撕开 `node -e`、`curl` 里的双引号。复杂命令写成临时脚本再执行。路径白名单拦住 `Remove-Item` / `Copy-Item` 时，用 .NET API，并且只动本次 worktree 和输出目录。

### 内置浏览器 vendor

`server/internal/egobrowser/vendor` 被 `go:embed` 打进 daemon，`manifest.json` 的 sha256 对的是 **git 对象里的字节**。仓库 `.gitattributes` 在 `* text=auto` 之后把该目录标成 `-text -eol`，就是为了不让 Windows 的 `core.autocrlf` 在 checkout 时把 LF 改成 CRLF。

这不是 Staging 专属问题。正式 Desktop 脚本 `apps/desktop/scripts/package-rollica-release.sh` 和 Mini 的 `package-rollica-mini-release.sh` 也是对这份工作区做 `go build`。它们的“工作区干净”只看 `git status`，查不出这种 CRLF。所以打包前的字节门禁放在共用的 `verify-egobrowser-vendor.mjs`：对不上 manifest 就失败，Staging 和正式包都走这里。

优先用含 `-text -eol` 规则的提交新建干净 worktree。不要只跑 `git checkout -- server/internal/egobrowser/vendor`。Git 可能仍认为那些 CRLF 文件没变，这条命令不会重写它们。

必须留在旧目录时，先删掉再检出：

```bash
rm -rf server/internal/egobrowser/vendor
git checkout HEAD -- server/internal/egobrowser/vendor
```

PowerShell：

```powershell
Remove-Item -Recurse -Force server\internal\egobrowser\vendor
git checkout HEAD -- server/internal/egobrowser/vendor
```

PNG 是二进制。禁止用 UTF-8 读写去“统一换行”。门禁不过就不要打包。

### 验包

用这些检查代替 macOS 的 `Info.plist` / `codesign`：

- 安装前确认包名是 `@multica/desktop-staging`，推导出的安装目录是 `%LocalAppData%\Programs\@multicadesktop-staging`。不是这个目录就不要装。
- 应用可执行文件名是 `Rollica Staging.exe`。看的是安装后的程序，不是只看 NSIS 安装器文件名。
- 装完后确认它不在正式版的 `@multicadesktop` 目录里。如果已经盖住正式版，停下来告诉用户；不要删正式版的用户数据，也不要擅自静默重装正式版。
- asar 里 `productName` 是 `Rollica Staging`。
- `resources/runtime-config.json` 的三个 URL 都指向 Staging。
- 主进程 bundle 里，`setupAutoUpdater` 只在 `app.getName() === "Rollica"` 时调用。
- `resources/app-update.yml` 仍可能被生成。它是惰性文件；真正挡住正式更新源的是上面的代码门控。
- 内置 CLI 的 commit 对得上记录的 `origin/develop` SHA。`-dirty` 只来自身份/config overlay。
- 本机已有代码签名证书时，electron-builder 会走 signtool。没有证书就如实说未签名，不要写成已签名。

### 启动

新包点开没有窗口、也没有报错时，先查是不是另一个 checkout 的 `Rollica.exe` 占着单实例锁。只结束那个残留进程。不要结束正式安装目录里的 Rollica，也不要动正式 profile。

`desktop-state-migration` 里依赖 symlink 或旧 Multica 导入的用例，在 Windows 上可以失败，而且与本次 overlay 无关。记录失败项。`runtime-config-loader` 仍然必须通过。不要为了让这几个 Windows 用例变绿去改 macOS 行为。
