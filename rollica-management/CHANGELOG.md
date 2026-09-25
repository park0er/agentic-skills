# rollica-management CHANGELOG

## 2026-09-10 — add-tokyo-private-env

- 包装器增加 `--env production|tokyo`（可用 `ROLLICA_ENV`）。默认仍是公司正式环境。
- 东京支持两种本机安装：Rollica Tokyo.app 内置 CLI，或只有 `~/.rollica-cli/bin/multica`；禁止用公司 Rollica.app 打东京。
- 东京 profile 从 `~/.rollica-tokyo` 或 `~/.multica/profiles`（常见 `a1`）按 `server_url` 发现；`PKO-*` / `pko` / 「东京」会推断 tokyo。
- `Parko`（正式）与 `Pko`（东京）明确拆开。详情见 `references/environments.md`。

## 2026-08-31 — persist-bound-issue-artifact-sync

- Issue 绑定与主动里程碑同步要求在整个当前会话持续有效，不要求用户在后续消息重复编号或再次提醒。
- OpenSpec、方案 Markdown、交互 HTML、关键图片和 QA/Review 报告发生实质更新时，随同一条里程碑评论作为附件回写。
- 补充用户 PAT 可用的 `issue comment add --attachment` 与 Task-only `attachment upload` 的边界，并保留 assignee 唤醒检查、隐私过滤和写后复读。

## 2026-08-30 — move-bound-issue-sync-policy

- 将用户全局规则中的 Rollica Issue 主动进展同步迁入本 Skill，避免全局文件重复维护业务流程。
- 明确绑定 `MIA-xxx` 后可主动维护里程碑评论和状态，但不授权唤醒 Agent/Squad、触发执行或修改无关资源。
- 保留开始前读取、里程碑去重、状态生命周期、写后复读和最终回报要求。

## 2026-08-18 — capture-user-feedback-why-in-issues

- Issue 进展同步必须先记录触发工作的核心用户反馈与 Why，再记录 Agent 的决策、动作、验证和下一步。
- 区分用户明确反馈与 Agent 推断；长期合同变更进入正文，迭代反馈进入里程碑评论，并避免重复倾倒聊天记录。
- 增加需求替代关系、隐私最小化、评论唤醒边界和写后复读要求；无既有 Issue 数据迁移。

## 2026-08-18 — model-production-dba-gates

- 发布 Checklist 必须区分 staging 自动 migration 与 production 人工 DBA SQL 工单，不能把两者写成同一条自动部署流程。
- production 主流程按时间线维护 additive DDL、migration check、停写/排空、repair、cutover/activation 和应用发布顺序。
- 持续维护发布前 SQL、manifest、迁移说明、OpenSpec 与专项方案入口，避免正文改写时无声丢失。

## 2026-08-18 — backup-and-detail-release-checklists

- 大幅改写 Issue 正文前必须保存服务端旧正文，并在写回后做全文一致性核验。
- 发布 Checklist 顶部必须维护分层总表，所有 Issue 引用都写“编号 + 可读标题”。
- 数据库 Gate 必须逐个说明 migration、repair/cutover、执行顺序、停止条件和恢复边界，禁止用一句“执行 migration”代替。

## 2026-08-18 — maintain-issue-architecture-impact

- 新增开发类 Issue 正文顶部的分端架构影响维护合同，要求设计、实现、Review、QA 变化后原位更新。
- 新增发布 Checklist 联动规则：只同步尚未闭环的发布动作，并保持面向聪明非技术读者的简洁表达。
- 将已安装副本中验证可用的正式 profile `desktop-rollica.ad.miui.com` 回收至 Factory 真源，避免 release 回滚连接配置。

## 2026-07-30 — correct-capability-audit-count

- 更正上一条记录中的来源计数：本次实际盘点了九个 `rollica-*` 内置 Skills。
- 能力路由、命令示例、权限和副作用边界均无行为变化。

## 2026-07-30 — expand-production-management-capabilities

- 从正式 Agent Work 中的九个 `rollica-*` 内置 Skills 盘点并吸收通用正式资源管理能力。
- 新增 Workspace/成员、Agent、Skill、Squad、Autopilot、Runtime、Label、Project resource、Issue PR/metadata/stage/mention 等能力路由与正式 CLI 示例。
- 明确评论、分配、状态、trigger、replace-all、secret、Runtime 和 durable resource 的副作用，并排除必须依赖可信 Task/Work/daemon 上下文的 Work Memory、Chat、repo checkout 与附件上传。

## 2026-07-30 — rename-from-rollica-prod

- 将 Skill 从 `rollica-prod` 重命名为更贴近职责的 `rollica-management`。
- 同步更新 Factory 目录、frontmatter、执行脚本名和所有调用示例，资源管理行为不变。
- 新版本发布验证后停用三个安装位置的旧 `rollica-prod` 副本，旧 Factory archive 保留用于追溯。

## 2026-07-30 — initial-production-resource-wrapper

- 首次发布面向正式 Rollica Workspace、Project、Issue、评论和进展的用户身份 CLI Skill。
- 支持 Workspace 名称、slug、UUID/短前缀、关键词与 Issue 前缀解析，并在歧义时失败关闭。
- 动态读取正式 Desktop profile 的 `mul_` PAT，不输出凭证；不绑定或伪装 Agent/Work/Provider 会话。
