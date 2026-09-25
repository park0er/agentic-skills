# xiaomi-postgres-workorder CHANGELOG

## 2026-09-09 — concrete-offline-rewrite-rules

- 将泛化操作流程替换为主文中的 6 组具体兼容规则与改写前后 SQL。
- 已知规则直接离线使用，不依赖浏览器、生产查询或重复语法实验；未覆盖部分单独标注，不阻塞其他改写。
- 保留必要的条件式等价说明：规范邮箱约束、NOT VALID 历史验证、平台超时未知及事务片段不能盲拆。
- 原始审核矩阵作为可选证据存档，移除要求未来使用者重做探针的表达。

## 2026-09-09 — initial-audit-compatibility

- Initial release：沉淀 DevX PostgreSQL 14.8 工单审核实测矩阵。
- 区分引擎支持、审核通过和执行成功；禁止移除事务/断言或扩大授权以过审。
- 明确规范格式 CHECK + 唯一索引的等价条件，以及在线写入、CTE 快照和恢复约束。
- 当前矩阵仅有审核证据，没有将生产执行或未测语法标为成功。
