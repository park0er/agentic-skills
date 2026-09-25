# Multica 小队 Instruction 模板

将 `<...>` 替换为项目事实后交给 Multica。不要保留占位符。

## 背景

本轮任务是为 `<绩效周期>` 产出绩效文档。前置工作已经完成：

1. 已收集材料并按 P0/P1/P2 标注优先级。
2. 已完成深度阅读要求：每个成员必须输出逐文档阅读清单和阅读感想。
3. 已确认规划大纲：`<confirmed_outline_path_or_summary>`。
4. 现在需要组织 Writer A、Writer B、互相学习、Reviewer 审阅，最后由 Leader 组织返工或汇总。

## 材料优先级

### P0 必读强参考

- `<P0 material 1>` — `<用途：事实/数据/结构/风格>`
- `<P0 material 2>` — `<用途>`

### P1 重要参考

- `<P1 material>` — `<用途>`

### P2 辅助参考

- `<P2 material>` — `<用途>`

历史绩效样例只能参考格式、表达密度、结构和系统填写方式，不得迁移业务事实。

## 通用硬规则

1. 不编造已完成、已上线、已采纳、进度、规模、数据；证据不足就写待确认。
2. 所有成员先输出“文档阅读清单 + 逐文档阅读感想”，未读全则退回重做。
3. 写作要先总后分、言简意赅、高信息密度；复杂层级优先编号。
4. 每层通常 3 点，最多 4 点；避免散点罗列。
5. 标题必须是完整总结句，尽量体现“通过 X 解决 Y 实现 Z”。
6. 用户是大团队负责人时，团队成果可以写作其负责范围内产出，但要讲清主导/共同设计/推动协调/参与支持。

## 角色与流程

### Leader / Coordinator（好模型）

职责：

1. 维护材料清单、优先级和 confirmed outline。
2. 分配 Writer A / Writer B 的独立写作任务。
3. 检查每个成员是否读全材料；不合格直接打回。
4. 组织 Cross Learning：A 学 B、B 学 A，各自产出 after-learning 版本。
5. 收到 Reviewer Reject 后，由 Leader 组织新一轮循环，不直接让 Reviewer 指挥单个 Writer。

### Writer A（好模型或中模型）

输出：`Writer_A_draft.md`。

要求：完整阅读材料并写阅读清单；基于 confirmed outline 独立完成一版，不要参考 Writer B 初稿。

### Writer B（好模型或中模型）

输出：`Writer_B_draft.md`。

要求：完整阅读材料并写阅读清单；基于 confirmed outline 独立完成另一版，表达策略要和 Writer A 有差异。

### Cross Learning

不是第三个融合执行者。仍由两个写作者执行：

1. Writer A 阅读 Writer B 初稿，产出 `Writer_A_after_learning.md`。
2. Writer B 阅读 Writer A 初稿，产出 `Writer_B_after_learning.md`。
3. 两份 after-learning 文档都要说明吸收了对方哪些优点、拒绝了哪些写法及原因。

### Reviewer（好模型）

输出：`review_gate_record.md`，结论为 PASS 或 REJECT。

审阅标准：

1. 对照写作 best practices 和历史成品样例审阅结构、标题、信息密度、语言风格。
2. 假装自己不是本部门成员、但懂行业，检查业务逻辑是否说得通。
3. 检查是否有夸大、编造、状态不明、证据缺口。
4. 检查每条战功/内功是否能看出用户贡献和团队责任边界。
5. REJECT 时列清楚问题和建议，但返工入口回到 Leader。
