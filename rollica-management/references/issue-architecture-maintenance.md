# Issue 分端架构影响维护

开发类 Issue 指会设计、实现、修复或发布代码、数据库、协议、客户端、daemon/runtime、部署或外部平台行为的 Issue。纯运营、纯调研且未形成交付设计的 Issue 不强行补“最终架构”；若 Issue 尚未实现但已有设计，明确标成 `planned` / `待实现`，不要冒充已落地。

## 先记录用户反馈与 Why

Issue 是工作的因果记录，不只是 Agent 的施工日志。每次同步设计、实现、修复、Review、QA 或发布里程碑时，先回答“为什么会有这一轮工作”，再记录“做了什么”。

- **核心反馈**：用一两句话归纳用户指出的现象、目标、约束或取舍。只保留足以解释工作的内容，不复制整段对话、语气词或无关细节。
- **Why / 影响**：说明该反馈对应的用户问题、风险或验收标准。没有用户明确说明时，写成“Agent 判断 / 推断”，不得伪装成用户理由。
- **决策与进展**：说明因此采用或放弃了什么方案、完成了什么，以及验证证据、限制和下一步。
- **变更关系**：若新反馈替代、收窄或扩大旧要求，明确写出“替代什么、现在以什么为准”，不要让互相冲突的要求并列存在。
- **隐私最小化**：不写验证码、token、内部绝对路径、个人数据或不必要的聊天原文；只保留理解产品决策所需的信息。

推荐的里程碑评论结构：

```md
用户反馈 / Why
- 核心反馈：...
- 为什么要改：...

本轮决策与进展
- ...

验证 / 风险 / 下一步
- ...
```

落点按信息生命周期决定：

1. 仅解释本轮修改原因的迭代反馈，写入对应的里程碑评论；同一反馈后续只引用或补充变化，不重复刷屏。
2. 改变产品范围、交互合同、数据/权限语义、验收标准或发布要求的反馈，同时整理进 Issue 正文的稳定章节，再用评论说明本轮为什么更新正文。
3. 写入前先读正文与近期评论，避免重复；写后重新读取，确认“反馈 → Why → 决策/结果”的链条完整且归因准确。
4. 评论可能唤醒 Agent/Squad 时仍遵守触发边界；不能安全评论时，先把同样结构保存为待回填说明，并告知用户。

## 已绑定 Issue 的主动进展同步

用户提供或持续引用 `MIA-xxx`，并明确当前工作围绕该 Issue 时，把它作为正式进展记录。无需用户反复提醒即可：

1. 开始前读取 Issue，核对标题、状态、assignee、正文和近期评论。
2. 在形成设计结论、完成实现或 commit、发现或解除阻塞、完成 Review/QA、合入或交付等里程碑时更新；普通探索和无变化检查不刷评论。
3. 评论写清本轮结果、commit/range（如有）、验证、风险和下一步；Review 同时记录结论与 findings 的处理情况。
4. 状态按事实维护：已排期未开始用 `todo`；实质推进用 `in_progress`；确有阻止继续或验收的问题才用 `blocked`；阻塞解除后恢复 `in_progress` 或 `in_review`；等待最终验收用 `in_review`；只有用户明确完成或给出最终验收结论时才用 `done`。
5. 写入前确认评论不会意外唤醒 Agent/Squad。进展同步不授权 trigger、rerun 或扩大工作范围；不能安全评论时保存待回填说明。
6. 写后重新读取 Issue，确认评论、正文和状态均已落地；最终回复简要说明同步结果。

上述绑定在当前会话内持续有效：后续用户用省略主语的“继续”“更新方案”“把页面改了”等方式推进同一工作时，不要求用户重复 Issue 编号，也不等待用户再次提醒同步。只有用户明确解绑、切换目标 Issue 或该项工作结束时才停止。

### 关键产物附件

当里程碑形成或实质更新可独立阅读的关键产物时，把它们随同一条进展评论附到 Issue：

- 需求方案、技术方案、OpenSpec proposal/design/spec/tasks；
- 可交互 HTML 原型、产品阅读版、关键流程图或产品提供的 benchmark 图片；
- QA、Review、迁移、发布或回滚报告。

使用 `issue comment add <issue> --attachment <absolute-path> --allow-external-file`，可重复 `--attachment`。这条命令使用用户 PAT 给 Issue 评论添加附件，与只允许当前 Task 的 `attachment upload` 不同。上传前检查无 secret、真实 Key、个人数据、本机内部路径或临时恢复信息；内容未变化时不重复附加，发生实质更新时附新版本并说明它替代哪一版。写后通过 `issue comment list` 确认附件名称、大小和 comment 归属。

## 写入位置与更新方式

1. **大幅重写或替换正文前先备份。** 先 `issue get` 读取服务端当前正文，原样保存到任务所属仓库的 `docs/.../backups/` 或其他明确的持久目录；文件名包含 Issue 编号、日期和“改写前”含义。保存后核对字节数或 hash，再执行写入。小范围 marker 原位更新也必须保证 marker 外正文不丢失。
2. 将维护块放在 Issue 正文第一块，保留用户原始正文在后。
3. 使用稳定 marker，后续原位替换，禁止重复追加：

```md
<!-- architecture-impact:start -->
## 分端架构影响 / Architecture Impact by Layer
...
<!-- architecture-impact:end -->
```

4. 设计定稿、实现 checkpoint、Review finding 闭环、QA、合入、范围延期或取消后，都检查该块是否仍准确。
5. 以当前最终事实为准：先读 Issue 正文、评论、关联 PR/commit/OpenSpec；信息不足时核对实际代码。不要把最初方案当最终实现。
6. 写后重新 `issue get`，确认 marker 位于最上方、只有一份、正文其余内容未丢失；全文替换时将服务端正文与本地事实源做 hash 或逐字比较。

## 必须覆盖的内容

逐项标记 `changed` / `unchanged`；未实现的设计用 `planned changed` / `unresolved`：

- Web
- Desktop
- Mobile Web / PWA（明确 Rollica 没有独立原生/Expo Mobile app）
- Shared frontend
- Server
- Database
- Daemon / CLI / Runtime
- Deployment / external platforms
- Cross-cutting contracts

块内还要包含：

- 当前维护状态与证据（设计中、已实现、Review/QA/合入状态）；
- 一条短的端到端数据/控制流；
- Upstream Sync Impact：冲突面、兼容/迁移、是否需要 daemon/Desktop 重发；
- 用户可见后果和必要的部署/版本要求。

区分 additive adapter 与替换现有系统；未修改的 Desktop 通知、飞书 Bot、daemon 协议等要明确写 unchanged。不要用文件列表代替架构说明。

## 与发布 Checklist 联动

若 Project 有中央发布 Checklist，在维护开发 Issue 时检查是否新增或改变以下事项：历史数据、迁移/repair、权限/隐私、版本错位、daemon/Desktop 分发、签名、Secret、域名/TLS、外部平台 canary、真实环境 UAT、回滚。

- 只把仍需发布团队执行或验收的动作同步到 Checklist；已完成的实现细节留在来源 Issue。
- Checklist 主文先写当前 Go/No-Go、未闭环 blocker、负责人/解除条件，再写 staging、production、回滚。
- Checklist 顶部维护一张**以层级为主干**的总表，至少包含“层级 / 本版整体变化 / 涉及 Issue”。Issue 引用必须写成“`MIA-123 — 能看懂的问题标题`”，不能只列编号；同一规则适用于 blocker、范围、迁移来源和技术证据入口。
- 数据库部分不能压缩成“执行 migration”。逐个列出候选 migration 编号、来源 Issue、schema/trigger/constraint 实际动作、是否自动 backfill、独立 repair/cutover 命令、执行顺序、停止条件、验证证据和回滚/forward-recovery 边界。明确区分：已存在的历史 migration、当前候选已有的 migration、尚未实现但旧清单声称要执行的清理动作。
- 涉及历史数据 repair 或权威来源 cutover 时，写清 read-only preflight、批准条件、apply、二次幂等检查、旧 writer 停止/排空、manifest/hash、污染 reconciliation 和不可做的 destructive down；不要只用技术名词代替动作。
- 先核对每个环境的真实 migration 合同，不能把 staging 的自动流程套到 production。若 staging 会随部署自动跑 SQL，而 production 需要产品/发布负责人提交 SQL 工单、由 DBA 手工执行，就把它写成明确的人工 Gate：冻结 tag/SHA 与 SQL hash、提交工单、DBA 回执、应用只读 migration check；production 应默认禁止应用容器自行补跑 schema。
- 把数据库动作放进 production 正式发布的同一条时间线，不另建一段与上线顺序脱节的“数据库说明”。逐项标明是否停旧服务：additive DDL 通常可在旧服务在线时由 DBA 先执行；只有 final scan、权威来源 cutover、activation 等要求冻结写入的动作，才另开维护窗停止旧 writer、排空 in-flight work。不得把 cutover 隐藏在容器启动或普通自动 migration 后面。
- Checklist 维护“发布前文件与技术证据入口”，恢复并持续更新原正文/评论中给发布人、DBA 或产品负责人的 SQL、manifest、迁移说明、OpenSpec 阅读版和专项方案。说明文件不能替代最终候选 tag/SHA 中的原始 SQL；过时文件要明确标注，不得无声删除。
- 面向聪明的非技术读者：使用用户行为和结果描述，减少表名、函数名、SQL、协议缩写与 commit 流水账；技术证据链接回来源 Issue/OpenSpec。
- 发现旧项已完成、范围已延期、实现已替换或说法失真时，直接更新/删除过时项，不在主清单叠加另一版近义说明。

## 副作用边界

优先编辑 Issue 正文，不为架构块单独发评论，避免无意唤醒 Agent/Squad。若还需要里程碑评论，先按本 Skill 的评论触发规则判断，并让评论包含本轮用户反馈 / Why；正文更新后照常复读验证。
