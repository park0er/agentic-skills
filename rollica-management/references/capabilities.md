# Rollica 正式环境管理能力

本文是 `rollica-management` 的按需命令路由。所有示例中的 `run` 都指：

```bash
python3 "<skill-dir>/scripts/rollica_management.py" [--env production|tokyo] run \
  --workspace "<名称、关键词、slug、ID 前缀或 Issue 前缀>" -- \
  <multica 参数>
```

请求含唯一 Issue 前缀时可省略 `--workspace`。`PKO-*` 会把环境推断为 tokyo；`MIA-*` 走正式。环境发现见 [environments.md](environments.md)。CLI 会更新，执行写操作前以 `run ... -- <domain> <command> --help` 的实际输出为准。

## 1. Workspace 与成员

读取：

```bash
python3 "<skill-dir>/scripts/rollica_management.py" workspaces --output json
run workspace get <workspace-id> --output json
run workspace member list --output json
```

管理：

- `workspace update`：Workspace 元数据，通常要求 admin/owner。
- `workspace member ...`：邀请、更新或移除成员；先读 `workspace member --help`。
- `workspace create` / `switch` 属于 profile 或 Workspace 生命周期操作。只有用户明确要求时执行；`switch` 会改变正式 profile 的默认 Workspace，但不改变包装器的显式解析规则。

不要把 Workspace 名称、关键词或 UUID 当作授权。最终权限由正式服务端按 `mul_` PAT 判定。

## 2. Project 与持久资源

读取：

```bash
run project list --output json
run project get <project-id> --output json
run project resource list <project-id> --output json
```

管理：

```bash
run project create --title "<title>" --output json
run project update <project-id> --title "<title>" --output json
run project status <project-id> in_progress --output json
run project resource add <project-id> --type github_repo --url <url> --output json
run project resource add <project-id> --type github_repo --url <url> --ref <branch-or-sha> --output json
run project resource update <project-id> <resource-id> --ref <branch-or-sha> --output json
run project resource remove <project-id> <resource-id> --output json
```

Project description 是未来 Project-bound Work 的共享规则/背景。Project resource 是持久上下文，不是一次性 checkout：

- `github_repo` 可设置未来任务默认 checkout ref。
- `local_directory` 绑定具体 daemon、本机绝对路径和机器生命周期；只有用户明确指定该路径时添加。
- `repo checkout` 是当前 Agent Task 的 daemon-local 行为，不属于本 Skill。

## 3. Issue、评论、PR、元数据与 Label

读取：

```bash
run issue list --output json
run issue search "<keyword>" --output json
run issue get MIA-220 --output json
run issue children MIA-220 --output json
run issue comment list MIA-220 --recent 20 --output json
run issue runs MIA-220 --output json
run issue run-messages <run-id> --output json
run issue usage MIA-220 --output json
run issue pull-requests MIA-220 --output json
run label list --output json
```

管理面包括：

- Issue create/update/status/assign/reorder、sub-issue stage、subscriber、label。
- 评论新增/编辑/删除，任务 rerun/cancel-task。
- Issue metadata set/delete。
- Label create/update/delete。

同步 Issue 进展时不能只列 commit、测试和 Agent 动作；先归纳触发本轮工作的核心用户反馈与 Why，再写决策、结果和下一步。会改变长期产品合同或验收标准的反馈同时沉淀进正文，详细规则见 [issue-architecture-maintenance.md](issue-architecture-maintenance.md)。

给里程碑评论附关键材料：

```bash
run issue comment add MIA-220 \
  --content-file /absolute/path/progress.md \
  --attachment /absolute/path/proposal.md \
  --attachment /absolute/path/prototype.html \
  --allow-external-file --output json
```

这是普通 Issue 评论附件，可以使用用户 PAT；不要改用依赖当前 Task 身份的 `attachment upload`。

### 执行触发边界

- Agent/Squad-assigned Issue 在 `backlog` 时停放；创建为非 backlog，或从 backlog 移出，可能立即创建任务。
- 评论可能唤醒当前 assignee。`cancelled` 会停止未完成工作；`rerun` 明确创建新执行；`cancel-task` 会中断运行中任务。
- Serial sub-issues：后续步骤用 `backlog` 停放，满足依赖后再改为 `todo`。`--stage N` 可建立阶段屏障。

### PR 与元数据

用 Rollica 的关联表判断真实 PR 状态：

```bash
run issue pull-requests MIA-220 --output json
```

`state` 是 `merged|closed|draft|open`；CI 看 `checks_conclusion`。不要用可能过期的 `pr_url` metadata 推断 PR 是否已合并。

PR 标题或 branch 中的 Issue key 会建立可见链接；只有 title/body 里的 `Closes|Fixes|Resolves MIA-220` 这类相邻 closing keyword 才表达 merge 后关闭意图。

稳定 metadata key 优先使用：`pr_url`、`pr_number`、`pipeline_status`、`deploy_url`、`external_issue_url`、`waiting_on`、`blocked_reason`、`decision`。日志和调查过程放评论，不放 metadata。

### Mention

评论里的有效 mention 不是裸 `@name`，而是：

```md
[@Label](mention://member/<user-id>)
[@Agent](mention://agent/<agent-id>)
[@Squad](mention://squad/<squad-id>)
[@Issue](mention://issue/<issue-id>)
[@all](mention://all/all)
```

ID 来源：

- 人：`workspace member list` 的 `user_id`
- Agent：`agent list` 的 `id`
- Squad：`squad list` 的 `id`
- Issue：`issue get` 的 `id`

`agent` 会触发该 Agent；`squad` 会触发 leader；`member` 和 `issue` 只是链接，不创建 Agent run；`@all` 是广播，不触发特定 Agent，并可能抑制 assignee 的自动评论触发。名称匹配不唯一时不要猜 ID。

## 4. Agent

读取：

```bash
run agent list --output json
run agent get <agent-id> --output json
run agent tasks <agent-id> --output json
run agent skills list <agent-id> --output json
```

管理面包括 create/update/archive/restore/avatar、技能绑定和 env：

```bash
run agent create --name <name> --runtime-id <runtime-id> \
  --description "<catalog summary>" \
  --instructions "<runtime behavior contract>" --output json
run agent skills add <agent-id> --skill-ids <skill-id> --output json
run agent skills list <agent-id> --output json
```

关键合同：

- `description` 是面向人的目录摘要；`instructions` 才是运行时行为约束。
- 创建 Agent 不会自动绑定 Workspace Skill。
- `skills add` 增量添加；`skills set` replace-all。
- `custom_env` 和 `mcp_config` 可能包含秘密。读取 env 是敏感读取；`env set` 覆盖完整 env map。写入优先用 stdin 或权限为 `0600` 的文件。
- 创建前先 `runtime list`，不要猜 `runtime-id`、model 或 thinking level。

## 5. Skill

读取与发现：

```bash
run skill list --output json
run skill get <skill-id> --output json
run skill search "<capability>" --output json
run skill files --help
```

Workspace Skill 的正式安装必须进入 Rollica Workspace 数据库：

```bash
run skill import --url <clawhub|skills.sh|github-url> --output json
run skill import --file </absolute/path/to/skill-or-zip> --output json
```

- 默认 `--on-conflict fail` 最安全。
- `overwrite` 原地替换同名 Skill，保留 ID/绑定，但通常只有原创建者可执行。
- `rename` 创建带后缀的新 Skill；`skip` 保留现状。
- 导入后如需给 Agent 使用，再执行 `agent skills add` 并用 `agent skills list` 验证。
- `npx skills add` 只会安装到外部本地环境，不能替代 Rollica Workspace import。

Skill create/update/delete/files 都是持久写操作。涉及本地 archive 时使用绝对路径和 CLI 要求的 external-file 显式许可。

## 6. Squad

读取：

```bash
run squad list --output json
run squad get <squad-id> --output json
run squad member list <squad-id> --output json
```

管理面包括 squad create/update/delete、member add/remove/set-role 和 leader activity：

```bash
run squad create --name <name> --leader <agent-name-or-id> --output json
run squad update <squad-id> --instructions "<leader policy>" --output json
run squad member add <squad-id> --member-id <id> --type agent --role <role> --output json
```

Squad 是路由/协作对象，不是会自行运行的 Agent：

- Issue assignment、mention 和 Autopilot 都路由给 `leader_id`。
- 不会自动 fan-out 给所有成员。
- `instructions` 进入 leader briefing；member `role` 是 roster 上下文，不自动授予权限或调度行为。
- 评论 squad-assigned Issue 可能唤醒 leader。
- `squad activity` 会写入 leader 对某个 Issue trigger 的评估结论，不是只读诊断命令。

## 7. Autopilot

读取：

```bash
run autopilot list --output json
run autopilot get <autopilot-id> --output json
run autopilot runs <autopilot-id> --output json
```

管理面包括 create/update/delete、trigger add/update/delete/rotate-url 和 manual trigger。先看正式 CLI help：

```bash
run autopilot create --help
run autopilot trigger-add --help
```

核心区别：

- `create_issue` 创建 Rollica Issue，再由 Agent 或 Squad leader 执行。
- `run_only` 直接创建 Agent Task，不产生 Issue。
- schedule、webhook、manual 都是真实 trigger。
- `trigger` 会立即启动一次真实执行。
- webhook URL/token 属于秘密；轮换后旧 URL 失效，不得把新值复制到评论、Issue、文档或回复。

诊断未执行：依次看 autopilot get、runs、目标 Agent/Squad、Runtime。不要通过手动 trigger 来“测试”。

## 8. Runtime 诊断

读取：

```bash
run runtime list --output json
run runtime usage <runtime-id> --output json
run runtime activity <runtime-id> --output json
run runtime profile --help
```

Agent 不执行时按链路诊断：Issue/Autopilot 是否创建任务 → assignee 是 Agent 还是 Squad → Agent 是否 archived/绑定正确 Runtime → Runtime 是否 online、`last_seen_at` 是否新鲜 → tasks/runs/run-messages 是否显示排队或失败。

`runtime rename`、`profile` 写操作、`update` 和 `delete` 会修改正式执行基础设施。`delete --cascade` 还可能归档 Agent 并取消任务；绝不能当成诊断步骤。

## 9. 明确排除的 Task/Work 能力

包装器主动清除 Agent Task 环境变量。以下能力即使 CLI 存在，也不属于“任意 Codex 会话用用户 PAT 管理正式资源”：

- `work memory update`：必须由服务端从可信 `MULTICA_TASK_ID` 推导当前 Project/Work Session，不能传任意目标 ID。
- `chat`：指当前 Rollica chat/Work 上下文，不是任意外部 Codex 会话。
- `repo checkout`：依赖 `MULTICA_DAEMON_PORT` 和当前 Task workdir，创建 task-local worktree。
- `attachment upload`：上传到当前 native Work reply，依赖当前 Work/Task。
- daemon start/stop/setup/update：控制本机执行基础设施，不是 Workspace 资源管理。

`attachment download` 若用户给出明确 attachment ID，可先看 `attachment download --help`；它是唯一可在不伪造 Task 上下文的附件候选读取能力。
