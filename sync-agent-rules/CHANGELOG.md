# sync-agent-rules CHANGELOG

## 2026-06-29 — ai-driven-editing-redesign

- 改为 **AI 自己编辑**：移除程序化插入脚本 `sync_rules.py`（它只会贴一段无标题层级的纯文本块）。
- 新增 `scripts/rule_tool.py`（仅机械护栏：`backup` / `locate` / `verify`），内容的标题层级、放置位置、各文件语气都由 agent 按文件结构现写。
- 保留 `<!-- BEGIN/END agent-rule:<topic> -->` marker，仅作幂等锚点（更新时就地改写、不重复）。
- SKILL.md 重写为 agent 驱动工作流（备份 → locate → 自己编辑 → verify → 汇报）。


## 2026-06-29 — initial-release

- Initial release: idempotent managed-block sync to 3 global agent rule files
- CLI: `--topic`, `--body`/`--body-file`, `--targets-file` for testing
- Backup before first write, per-file OK/CHANGED verification
