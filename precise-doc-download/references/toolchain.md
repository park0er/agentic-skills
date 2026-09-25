# feishu2md Toolchain Reference

## Default location

`/Users/park0er/coding/PerKnowledgeBase/feishu2md`

Important files:

- `scripts/feishu_exporter.py`: main exporter for `single`, `folder`, and `wiki` modes.
- `scripts/fix_links.py`: rewrites Feishu token links after export.
- `scripts/audit_staging.py`: creates an export audit report.
- `scripts/core/get_user_token.py`: refreshes local user auth when the exporter reports an expired/missing token.
- `feishu-docx/`: patched local library used by the exporter for Markdown, nested tables, media, and whiteboard handling.

## Dependencies

The exporter imports the local `feishu-docx` package, which needs the full
runtime, not just the old `requests/tiktoken/rich` set. Provide a Python 3.11+
env with:

```bash
python3 -m pip install "lark-oapi>=1.4.24" "pydantic>=2" "httpx>=0.27" \
  "mistune>=3" rich tiktoken requests
```

A ready-made venv lives at `<tool-root>/.venv_export`; run the wrapper with
`<tool-root>/.venv_export/bin/python scripts/export_materials.py ...` to avoid
polluting system Python.

Do not vendor `scripts/core/user_token.json`, app secrets, or generated Obsidian vault outputs into a skill.

## Auth

- The exporter reads `scripts/core/user_token.json` and silently refreshes the
  ~2h `access_token` via the **passport** endpoint using a 30-day `refresh_token`.
- If the token is missing/expired with no refresh_token, re-auth with the
  passport OAuth flow: `scripts/core/reauth_passport.py` (browser, redirect
  `http://127.0.0.1:9527/`). This flow returns a refresh_token by default — do
  NOT switch it to the v2 `authen/v2` flow (that needs scopes pre-registered and
  throws 20027/20029 on this test app).

## Operational notes

- Run from any workspace; the wrapper sets `cwd` to the tool root so the exporter finds the local `feishu-docx` library.
- Use explicit project output directories; avoid exporting into the tool repository's bundled `ObsidianVault` during project work.
- `folder` and `wiki` exports create token-map JSON files that `fix_links.py` can consume.
- **Whiteboards**: feishu2md's own board export hits a `99991672` scope error and
  drops boards. `feishu-docx`'s `core/parsers/document.py` is patched so that
  under `--keep-whiteboard-empty` each placeholder embeds the board token
  (`【白板 序号N】<!--wb:TOKEN-->`); `scripts/fuse_whiteboards.py` then renders
  each via the `feishu` CLI. `export_materials.py` runs this automatically in
  single mode.
