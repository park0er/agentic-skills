---
name: gogdoc-exporter
description: Export Gemini Deep Research Google Docs into Obsidian-ready Markdown and reader-friendly HTML via gog + tariq-html (no browser automation). Use when the user says 导出/导出报告 and wants default Markdown+HTML export, latest-doc auto-selection, optional title-based selection, and explicit Markdown-only/PDF-only modes.
---

# GogdocExporter

Handle the "Gemini Deep Research -> Google Docs -> 入库与分享" pipeline.

## Default Behavior (must follow)

1. **If user says only "导出" (no doc specified):**
   - pick the **most recently modified Google Doc**
   - export **Markdown + HTML**
   - HTML is generated from the Markdown via the `tariq-html` skill
2. **If user specifies `only Markdown` / `仅Markdown` / `只要md`:**
   - export **Markdown only**
   - do **not** generate HTML
3. **If user specifies `only PDF` / `只要pdf`:**
   - export **PDF only**
   - do **not** generate Markdown or HTML unless needed internally and explicitly approved
4. **If user gives a doc name keyword:**
   - search docs by name contains keyword
   - choose the newest matched doc
5. **Output location:**
   - put generated `.md`, `.html`, and/or `.pdf` into the same folder
   - default folder comes from `references/config.json`
6. **HTML default:**
   - default export always invokes `tariq-html` after Markdown export
   - skip HTML only when the user explicitly requests a single format such as `markdown only` or `pdf only`
7. **PDF sharing default:**
   - `references/config.json` has `default_send_pdf_in_chat: true`
   - send PDF back only when PDF was explicitly requested/generated
   - plain `导出` no longer generates or sends PDF by default

## Command Parsing (chat-side shorthand)

Interpret short user commands like this:

- `导出` -> latest doc, Markdown + HTML (default)
- `导出 only markdown` -> latest doc, Markdown only, no HTML
- `导出 only pdf` -> latest doc, PDF only, no Markdown/HTML
- `导出 <关键词>` -> match by title, Markdown + HTML (default)
- `导出 <关键词> only markdown` -> match by title, md only
- `导出 <关键词> only pdf` -> match by title, PDF only, no Markdown/HTML
- `导出 不发文件` -> latest doc, Markdown + HTML, no chat attachment
- `导出 tariq-html` / `导出 并用 tariq-html 做网页` -> same as default; explicit wording reinforces HTML generation

## Execute Export

Run script:

```bash
python3 skills/gogdoc-exporter/scripts/export_gdoc_to_md.py --json
```

Optional parameters:

- `--doc-id <id>`: exact target doc
- `--query <keyword>`: title contains keyword
- `--only-markdown`
- `--only-pdf`
- `--formats md,pdf`
- `--out-dir <path>`
- `--base-name <name>`
- `--account <email>`

## Default Tariq HTML generation

By default, this skill must hand off the exported Markdown to the `tariq-html` skill after the `gog` export succeeds. This is not optional for plain `导出`; it is skipped only for explicit single-format requests such as `markdown only` or `pdf only`.

Workflow:

1. Run the export script and parse the JSON result.
2. Read `outputs.md` from the JSON. If it is missing and the user did not ask for `pdf only`, generate Markdown first by rerunning with `--only-markdown` or an appropriate format set.
3. Invoke/read the `tariq-html` skill instructions and select the branch based on the document shape:
   - comparison / 方案对比 -> `comparison`
   - concept or research explainer -> `research-explainer`
   - implementation plan / roadmap -> `decision-plan`
   - status / progress report -> `status-report`
4. Create a single self-contained `.html` next to the Markdown file, using the same base name.
5. Validate the HTML with `tariq-html/scripts/validate.mjs` when available.
6. In the final plain-text conclusion, include doc title, exported formats, Markdown path, and HTML path. Mention PDF path/attachment only if PDF was explicitly requested/generated.

Important constraints inherited from `tariq-html`:

- Output exactly one static `.html` file; do not create a multi-file web project.
- No arbitrary external CDNs or local image references. Google Fonts typography mode is acceptable if `tariq-html` allows it.
- Preserve the Markdown as the source of truth; HTML is the reader-friendly rendering.
- If the user says `markdown only`, `仅Markdown`, or `只要md`, the `only` modifier wins: generate Markdown only and skip HTML.
- If the user says `pdf only`, `仅PDF`, or `只要pdf`, generate PDF only and skip HTML.

## Send PDF back to chat

Default is controlled by `default_send_pdf_in_chat` in config (currently `true`).

1. Read JSON output from script and get `outputs.pdf`
2. **Always send a plain-text conclusion first** (doc title + exported formats + where files were saved)
3. If PDF was requested/generated, default is true, and user did not say "不发文件", then send PDF via `message` tool as a second message
4. If user explicitly asks only files in disk, skip chat attachment but keep the plain-text conclusion
5. If `message` tool is used to send user-visible content (text/file), finish with `NO_REPLY` to avoid duplicate replies

### Messaging order (bugfix)
- Correct order: **结论文字 -> 文件附件**
- Do not rely on PDF caption as the only conclusion channel.
- Even when PDF发送成功, missing text conclusion counts as incomplete delivery.

## Dependencies

Install once if missing:

```bash
python3 -m pip install --user mammoth markdownify pyyaml
```

## Files

- Script: `scripts/export_gdoc_to_md.py`
- Config: `references/config.json`
