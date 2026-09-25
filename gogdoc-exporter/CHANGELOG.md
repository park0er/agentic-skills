# gogdoc-exporter CHANGELOG

## 2026-06-15 — default-markdown-html

- 将默认导出行为从 Markdown+PDF 调整为 Markdown+HTML
- 明确只有 `markdown only` / `pdf only` 这类单格式请求才跳过 HTML
- PDF 不再由 plain `导出` 默认生成或发送，仅在用户明确请求 PDF 时处理

## 2026-06-15 — tariq-html-handoff

- 增加用户点名 `tariq-html` 时的后处理流程
- 规定先导出 Markdown，再调用 `tariq-html` 生成同目录同名 HTML，并尽量运行校验脚本
- 明确 `markdown only + tariq-html` 表示不生成 PDF，但仍生成 Markdown + HTML

## 2026-06-15 — initial-import-from-openclaw

- 从 OpenClaw 工作区导入并进行首次初始化发布
- 支持将 Gemini Deep Research 导出的 Google Docs 转换为 Markdown 和 PDF 双格式
- 实现自动选择最新文档或关键字匹配功能
