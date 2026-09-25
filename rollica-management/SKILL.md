---
name: rollica-management
description: 通过本机 Rollica CLI 以已登录用户身份管理 Workspace、成员、Project、Issue、Agent、Skill、Squad、Autopilot 与 Runtime。默认公司正式环境（Rollica.app）；用户提到东京服、东京私服、Pko、PKO-xxx 时改走东京（Rollica Tokyo.app 或 ~/.rollica-cli 二进制）。也用于 MiAdsAgent、MIA-xxx、同步进展、配置自动化。Workspace 按名称/slug/UUID/Issue 前缀解析。不要用于 QA/dev、恢复 Provider/Work 会话、任务内 repo checkout/附件上传或 Work Memory。
---

# Rollica management

使用 `scripts/rollica_management.py` 调用 Rollica。脚本按环境选择 CLI 和用户 `mul_` PAT；不要自行拼 token、直接调用 API、使用 `curl`，也不要设置 `MULTICA_TASK_ID` / `MULTICA_AGENT_ID`。不要用公司 `Rollica.app` 的 CLI 打东京服。

## 定义

- **正式 Rollica（production）**：`/Applications/Rollica.app` 与 `desktop-rollica.ad.miui.com` profile。默认环境。不含 localhost、QA、staging、东京私服。
- **东京私服（tokyo）**：`http://141.147.189.28`（可用 `ROLLICA_TOKYO_SERVER` 改主机）。CLI 优先 Tokyo Desktop 内置二进制，否则 `~/.rollica-cli/bin/multica`。登录配置优先 `~/.rollica-tokyo`，否则 `~/.multica/profiles` 里指向东京的 profile（常见名 `a1`）。发现细节见 [references/environments.md](references/environments.md)。
- **Workspace 目标**：底层 workspace-scoped 请求必须有规范 Workspace UUID，但用户无需提供 UUID；脚本从当前用户有权访问的 Workspace 中按名称、slug、UUID/短前缀、关键词或 Issue 前缀解析。公司 `Parko` 与东京 `Pko` 不是同一个工作区。
- **用户操作**：使用所选环境 profile 中的 `mul_` PAT，服务端继续按当前用户的 Workspace 成员关系、角色和资源权限鉴权；Workspace 线索不是凭证。
- **业务对象**：Project、Issue、Agent、Skill、Squad、Autopilot、Runtime 等是每次操作的对象，不是启动 Skill 的必填环境变量。
- **通用管理**：指不依赖某个正在运行的 Rollica Work/Agent Task 的资源操作。它不包含任务身份、Work Session 私有上下文或 daemon-local repo 状态。

## 工作流

0. 先选环境，再解析 Workspace。
   - 默认 `--env production`。
   - 用户说东京/东京服/私服，或 Issue 是 `PKO-xxx`，或 Workspace 线索是 `pko`：加 `--env tokyo`（也可不写，包装器会从这些线索推断）。
   - 公司 `Parko` 用 `--env production --workspace parko`；不要把 `pko` 丢给正式环境（会误伤 `parko` 关键词匹配）。
1. 从用户请求提取 Workspace 线索。
   - 用户给出 Workspace 名称、slug、ID 或关键词时，传给 `--workspace`。
   - 请求含 `MIA-220` 或 `PKO-3` 这类 Issue 标识符时，可以省略 `--workspace`；脚本按 Issue 前缀推断。
   - 没有任何线索且用户可访问多个 Workspace 时，先列出候选并请用户选择；不要默认看起来最像的 Workspace。
2. 先读取，再决定是否写入。
   - 查询、列表、诊断可直接执行。
   - 创建、更新、评论、分配、绑定、导入、触发等写操作只在用户明确要求时执行。
   - 当前工作已由用户明确绑定到某个 Rollica Issue（提供或持续引用 `MIA-xxx`）时，视为已授权维护该 Issue 的里程碑评论和状态；具体边界见 [references/issue-architecture-maintenance.md](references/issue-architecture-maintenance.md)。这不授权唤醒 Agent/Squad、触发执行或修改无关资源。
   - 删除、归档、取消任务、replace-all、密钥轮换等高影响操作遵循当前会话的确认规则。
3. 不确定命令参数时，用包装器执行 `<domain> --help` 或 `<domain> <command> --help`；不要凭记忆猜参数。
4. 使用 `--output json` 读取机器可判定的结果；写后再用相应 `get` / `list` 验证。
5. 解析结果不唯一时，把候选项交给用户选择，不要猜测。
6. 更新 Issue 时同时维护工作的因果链，不能只写 Agent 做了什么。
   - 先归纳触发本轮工作的核心用户反馈，以及它为什么重要；再写采取的决策/动作、验证与下一步。
   - 用户反馈、Agent 推断和最终决策要明确区分，不得把推断冒充用户原意，也不要直接倾倒聊天记录。
   - 改变长期产品合同、验收标准或范围的反馈同步进 Issue 正文；迭代过程中的反馈至少写进对应里程碑评论。具体格式、去重和隐私规则见 [references/issue-architecture-maintenance.md](references/issue-architecture-maintenance.md)。
7. 开发类 Issue 在形成设计、实现、Review 或 QA 结论后，持续维护正文最上方的分端架构影响块；项目发布清单同步吸收仍未闭环的发布动作。具体格式和判断规则见 [references/issue-architecture-maintenance.md](references/issue-architecture-maintenance.md)。
8. **把绑定 Issue 的同步合同保持到本次会话结束。** 一旦本 Skill 在当前 session 中解析出用户正在推进的 `MIA-xxx`（正式）或 `PKO-xxx`（东京），即使后续消息只说“继续”“改一下原型”或不再重复 Issue 编号，也要继续把该 Issue 视为进展记录目标，直到用户明确解绑、切换 Issue 或结束该项工作。不要依赖下一轮再次加载本 Skill 才想起同步。回写正式 Issue 用 `--env production`；回写东京 Issue 用 `--env tokyo`。
   - 形成产品/技术决策、更新 OpenSpec、完成实现/commit、Review/QA、发现或解除 blocker、交付可读原型等关键里程碑时，主动回写；普通探索不刷屏。
   - 方案 Markdown、OpenSpec、可交互 HTML、关键图片、QA/Review 报告等可独立阅读的关键产物发生实质变化时，优先作为该里程碑评论的附件上传，并在正文中说明附件版本/用途。只附不含 secret、个人数据和本机敏感路径的文件。
   - 使用 `issue comment add <issue> --attachment <absolute-path> --allow-external-file`；这是 Issue 评论附件，不是依赖 Task 身份的 `attachment upload`。同一里程碑把说明和附件放在一条评论中，避免碎片化；未变化的旧附件不重复上传。
   - 每次写前仍须重读 Issue 并检查 `assignee_type`，防止意外唤醒 Agent/Squad；写后复读确认评论、附件和状态落地。

完整能力路由、读写边界和常用命令见 [references/capabilities.md](references/capabilities.md)。涉及下列领域时先读取对应章节：

- Workspace/成员、Project/资源、Issue/评论/PR/元数据/mention、Label
- Agent/env/Skill 绑定、Skill 搜索/导入/文件、Squad、Autopilot
- Runtime 诊断，以及明确排除的 Work/Chat/repo checkout/附件上传能力

## 包装器

以下 `<skill-dir>` 指本 `SKILL.md` 所在目录。始终从该目录解析脚本，不依赖当前仓库。

检查 CLI、profile、用户 PAT 与 Workspace 发现：

```bash
python3 "<skill-dir>/scripts/rollica_management.py" doctor
python3 "<skill-dir>/scripts/rollica_management.py" --env tokyo doctor
```

列出当前用户可访问的 Workspace：

```bash
python3 "<skill-dir>/scripts/rollica_management.py" workspaces --output json
python3 "<skill-dir>/scripts/rollica_management.py" --env tokyo workspaces --output json
```

用名称、关键词、slug、ID 前缀或 Issue 前缀解析 Workspace：

```bash
python3 "<skill-dir>/scripts/rollica_management.py" resolve-workspace "miads"
python3 "<skill-dir>/scripts/rollica_management.py" resolve-workspace "MIA-220"
python3 "<skill-dir>/scripts/rollica_management.py" --env tokyo resolve-workspace "pko"
python3 "<skill-dir>/scripts/rollica_management.py" resolve-workspace "PKO-3"
```

调用 CLI（正式默认，东京加 `--env tokyo`）：

```bash
python3 "<skill-dir>/scripts/rollica_management.py" run \
  --workspace "MiAdsAgent" -- \
  project list --output json
python3 "<skill-dir>/scripts/rollica_management.py" --env tokyo run \
  --workspace "pko" -- \
  agent list --output json
```

按 Issue 前缀自动推断 Workspace 和环境：

```bash
python3 "<skill-dir>/scripts/rollica_management.py" run -- \
  issue get MIA-220 --output json
python3 "<skill-dir>/scripts/rollica_management.py" run -- \
  issue get PKO-3 --output json
```

执行前只检查解析结果：

```bash
python3 "<skill-dir>/scripts/rollica_management.py" run \
  --workspace "miads" --dry-run -- \
  agent list --output json
```

查看当前环境 CLI 真正支持的参数：

```bash
python3 "<skill-dir>/scripts/rollica_management.py" run \
  --workspace "miads" -- \
  autopilot trigger-add --help
```

## 关键副作用

- Issue 评论可能唤醒 Issue 当前分配的 Agent 或 Squad leader；带 `mention://agent/...` 或 `mention://squad/...` 会明确触发目标。发布进展前先判断用户是否希望触发执行。
- Agent/Squad-assigned Issue 在 `backlog` 时停放；创建为 `todo` 或从 `backlog` 移出可能立即排队执行。
- `agent skills add` 是增量绑定；`agent skills set` 是 replace-all，可能移除全部既有绑定。
- Autopilot 的 `trigger` 会启动真实执行；trigger 新增、更新、删除和 webhook URL 轮换都会修改持久配置，且 URL/token 不得写入评论、文档或日志。
- Project resource 会影响未来任务上下文；`local_directory` 还绑定具体 daemon 和绝对路径。
- Runtime 更新、删除，以及 Agent/Squad/Project/Skill/Label/Autopilot 删除或归档，都不是诊断步骤。
- Agent `custom_env` 与 `mcp_config` 可能含密钥。只在用户明确要求且权限允许时读取或修改；不要在回复中回显明文。优先使用 stdin 或 `0600` 文件输入，而不是把秘密放进命令行。

## 约束

- 脚本从所选环境的 profile 动态读取 token，但绝不输出 token。生产与东京的 token/CLI/config home 不得混用。
- 脚本会清除 `MULTICA_TASK_ID`、`MULTICA_AGENT_ID` 和 `MULTICA_DAEMON_PORT`，并在中性目录调用 CLI，确保以当前用户而非某个 Agent Task 身份操作。
- 涉及本地文件的正式资源命令使用绝对路径，并按 CLI 要求显式提供 `--allow-external-file`；含秘密的临时文件权限设为 `0600`。
- 不用本 Skill 恢复 Kiro/Codex/Claude Provider session，不绑定或冒充 Rollica Work Session。
- 不用本 Skill 执行 `work memory update`、`chat`、`repo checkout` 或 `attachment upload`；这些依赖可信 Task/Work/daemon 上下文，不能用 Workspace ID 和用户 PAT 伪造。
