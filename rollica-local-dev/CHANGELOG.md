# rollica-local-dev CHANGELOG

## 2026-09-22 — isolate-windows-staging-install-dir

- Windows Staging overlay 必须把 `package.json` 的 `name` 改成 `@multica/desktop-staging`。只改 productName/appId 会装进正式版目录。
- 安装前检查 NSIS 记住的 `InstallLocation`；指向正式版目录时只删 staging 的注册表键。
- 同名 `-dirty` 安装器不得覆盖旧文件。已经盖住正式版时停止，不擅自重装。

## 2026-09-22 — fix-windows-vendor-recovery

- 删掉无效的 `git checkout -- vendor` 恢复步骤。旧 checkout 要先删目录再检出，或直接新建 worktree。
- 写明正式 Windows 打包和 Staging 共用同一条 `go:embed` 字节门禁，`git status` 干净不能代替校验。

## 2026-09-22 — add-windows-staging-package

- 隔离 Staging 包在缺少本机 QA 配置时可以继续，不再被 doctor 挡住。
- 增加 Windows 打包专区：先安装依赖、必须 `--publish never`、只打要求的架构、验包看 exe/asar 而不是 Info.plist。
- 写明 egobrowser vendor 按 git 对象字节校验；Windows 上 CRLF checkout 要重检出，不能用文本方式改 PNG。

## 2026-09-21 — add-rollica-repository-target

- 纳入 Rollica 仓库 `.agents/skills/rollica-local-dev/` 共享发布目标。
- 移除对个人 `rollica-management` Skill 的硬依赖，改为使用当前已认证的 Rollica CLI 工具。
- 修正模板行尾注释被轻量 YAML 解析器读入 `kind` 值的问题。

## 2026-09-04 — add-isolated-staging-package-workflow

- 新增基于最新 `origin/develop` 的隔离 Staging 桌面端打包流程，明确它不同于 QA App 和正式发布。
- 固化 Staging 服务地址、独立产品身份/userData/config home、正式 updater 隔离及 Apple Silicon 单架构构建要求。
- 增加来源 SHA、内置 Runtime、产物身份、架构、运行配置、完整 ad-hoc 签名与校验和验收门槛，并记录 `rollica://` 深链尚未隔离的边界。

## 2026-09-02 — verify-runtime-path-and-device-readiness

- 要求在 QA daemon 重启后检查进程实际 PATH，并逐个解析预期 provider；不再把 `daemon status` 的 Agent 名单当作可用性证明。
- 增加当前 workspace、当前设备 Runtime 的 `online` 与 Desktop 按钮验收，避免被同名旧设备的离线记录误导。
- 记录 Desktop 重开但旧 daemon 仍可能携带旧 PATH 存活的故障模式。

## 2026-08-18 — attach-solution-materials-to-issue-updates

- 新增方案型 Issue 进展同步要求：尽量在同一条评论附上完整定稿的 Markdown、HTML 及直接支撑材料。
- 明确方案型进展的边界，并要求评论正文仍包含自洽摘要。
- 增加敏感信息排除、附件受限时的持久链接降级，以及写入后可见性复核。

## 2026-08-15 — rename-and-persistent-qa-memory

- 从 `multica-local-dev` 更名为 `rollica-local-dev`。
- 本机路径、端口、测试账户、库名不再写进 skill，只读 `$MULTICA_CONFIG_HOME/local-dev.yaml` 或 `~/.rollica/local-dev.yaml`；秘密留在 `env_file`。
- 默认按 persistent-qa 尊重现有 QA Desktop / daemon / 数据库；禁止误 teardown、误连正式环境、误开新 userData。
- 固化本轮教训：Desktop 缺 `.env.local` 会掉到 :8080 像没登录；换 daemon 二进制必须先停 Desktop；daemon 要用完整 login-shell PATH 才能看到本机全部 provider。

## 2026-06-30 — initial-release

- 作为 `multica-local-dev` 首次发布的内容仍适用于 `kind: ephemeral`。
