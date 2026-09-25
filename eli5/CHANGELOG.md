# eli5 CHANGELOG

## 2026-08-22 — initial-port-from-claude-plugins-community

- 首次从 anthropics/claude-plugins-community (eli5) 移植到本地 Skill Factory。
- 单文件 SKILL.md，description 触发 `/eli5 <topic>` 或"像给五岁小孩解释"类请求。
- 行为：生成"大字 + 大图 + 少字"的 HTML 图解，面向零基础读者。
- 已知限制：原仓库仅此一个 SKILL.md，无额外脚本/资源；本机安装即此文件。
