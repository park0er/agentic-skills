# 本地 Worker Loop 候选设计（未实跑验证）

当没有 Multica 时，可以考虑用本地脚本生成角色 prompts，再通过 Claude Code CLI、Anthropic SDK 或其它 agent CLI 执行。

## 推荐角色模型

| 角色 | 模型建议 | 原因 |
|---|---|---|
| Leader | 好模型 | 负责结构、事实边界、返工组织 |
| Writer A | 好模型 | 产出高质量主版本 |
| Writer B | 中模型或好模型 | 增加表达差异和第二视角 |
| Reviewer | 好模型 | 需要强逻辑审查和防编造 |

## 待验证执行方式

1. Claude Code CLI：优点是复用本地配置、工具和仓库上下文；风险是 CLI 自动化接口需要实测。
2. Anthropic SDK：优点是可控编排；风险是需要自行实现文件读写、工具调用和上下文管理。
3. Codex / other agent CLI：优点是贴近现有工作区；风险是并行与权限行为需实测。

在试跑成功前，任何 skill 输出都只能称为“本地候选方案”，不能称为已跑通流程。
