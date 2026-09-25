# notebooklm-zh CHANGELOG

## 2026-06-12 — upgrade-to-notebooklm-py

- **底层 CLI 从 `notebooklm-cli`（命令 `nlm`）升级为 `notebooklm-py`（命令 `notebooklm`，16k+ Stars）。**
- 新增产物下载能力：report → Markdown, audio → MP3, slides → PDF/PPTX, video → MP4, infographic → PNG, quiz/flashcard → JSON/Markdown/HTML, mindmap → JSON, data-table → CSV。
- 新增本地文件上传（`--file`），支持 PDF/MD/DOCX/EPUB/音视频等。
- 新增批量下载（`--all`）、分享管理（`share public/private/invite`）、批量查询（`batch query`）、多步骤管道（`pipeline run`）。
- 新增 Deep Research 专项指导（`research start --mode deep`）。
- 旧 `nlm` 命令（notebooklm-cli）仍可并存，skill 以 `notebooklm` 为主。
- 更新前置条件安装命令和认证检查命令。

## 2026-06-02 — align-with-nlm-cli

- Ported the installed-only skill into Skill Factory as the source of truth.
- Switched command guidance from nonexistent `notebooklm` syntax to installed `nlm` / `notebooklm-cli` 0.1.12 syntax.
- Removed or caveated unsupported commands such as direct local-file upload, `use/ask/history/language/share`, and generic `download`.
- Documented the Codex Desktop DevTools 9229 collision that can break `nlm login`.
