# performance-writing CHANGELOG

## 2026-06-20 — force-feishu-sheet-attempt

- 将材料收集阶段的飞书表格创建从“可用时创建”升级为必须主动尝试创建。
- 要求飞书表格与本地 `materials_to_collect.md` 行列一致，并尽量为优先级列配置 `P0/P1/P2` 单选或下拉。
- 若飞书创建失败，必须记录具体阻塞原因并明确告知用户，而不能静默退回只生成 Markdown。

## 2026-06-20 — targeted-revision-loop

- 完成本地 Claude fallback 的 REJECT loop：Reviewer REJECT 后自动调用 Leader，解析结构化返工计划，并进入下一轮定向修订。
- 新增 `--resume-from-reviewer` 能力，可从已有 REJECT gate record 继续跑 Leader plan 与后续 revision。
- 验证强制 REJECT 场景：Leader 指派 Writer B 修订，脚本自动跑 Writer B revision、Cross A/B、Reviewer round 02，并最终 PASS。

## 2026-06-19 — claude-fallback-loop-v2

- 升级本地 fallback：从通用 prompt 生成改为基于 confirmed outline + Multica instruction 的角色专属 prompt。
- 新增 Claude Code runner 初版，按 Writer A/B、Cross A/B、Reviewer 顺序执行，并在 REJECT 时回到 Leader 生成返工计划。
- 新增输出校验器，检查全文结构、P0 阅读清单、Reviewer frontmatter 和“预计/计划不得写成已完成”的状态边界。

## 2026-06-18 — initial-performance-loop

- 新增绩效写作 skill，沉淀材料收集、规划者、Multica 多写作者、互学、审阅和最终落盘流程。
- 将本次实际经验固化为主路径：Multica 小队执行写作者、互学、审阅循环，Leader 负责门控和返工组织。
- 标注本地 Claude/SDK 自动化循环为待试跑候选路径，不把未验证流程写成既成事实。
