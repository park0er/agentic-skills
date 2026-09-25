---
name: precise-doc-download
description: Manual-only helper for precision document download with a preconfigured local pipeline. Do not invoke implicitly and do not use for general Feishu tasks. Use only when the user explicitly calls /precise-doc-download or $precise-doc-download and asks for faithful local Markdown/media export.
---

# Precise Doc Download

## Default Rule

For project materials from Feishu, prefer the local `feishu2md` pipeline at `/Users/park0er/coding/PerKnowledgeBase/feishu2md` instead of generic document fetches. It preserves nested table text structure and downloads images as local files with Markdown references.

Use native Feishu tooling only for assets the pipeline handles poorly, especially whiteboards/canvases.

## Workflow

1. Identify the source type: single doc URL/token, Drive folder token, or Wiki space ID.
2. Run `scripts/export_materials.py` with the matching mode and an explicit `--out-dir` under the current project workspace.
3. Inspect the exported Markdown and generated asset folders before summarizing or writing derived performance material.
4. Whiteboards are handled **automatically for every mode** (single / folder / wiki): feishu2md's own board export fails with a `99991672` scope error and silently drops boards, so the pipeline exports with `--keep-whiteboard-empty` (placeholders embed the board token as `【白板 序号N】<!--wb:TOKEN-->`) and then `scripts/fuse_whiteboards.py` renders each board to PNG via the native `feishu` CLI and patches every exported `.md` — mapped by token, not by order. Because the token lives in each `.md`, folder/wiki batches need no extra arguments.
5. Optionally run `scripts/find_whiteboard_gaps.py <out-dir>` to spot-check for any remaining whiteboard/canvas gaps.
6. If local Feishu traceability rules apply, keep or add source comments in generated local documents.

## Script Usage

Export one document:

```bash
python3 /path/to/skill/scripts/export_materials.py single "https://mi.feishu.cn/docx/xxx" --out-dir ./Performance_Workspace/01_Human_Preparation/02_Input_Materials/source-name
```

Export a Drive folder:

```bash
python3 /path/to/skill/scripts/export_materials.py folder <folder_token> --out-dir ./Performance_Workspace/01_Human_Preparation/02_Input_Materials/source-folder
```

Export a Wiki space:

```bash
python3 /path/to/skill/scripts/export_materials.py wiki <space_id> --out-dir ./Performance_Workspace/01_Human_Preparation/02_Input_Materials/source-wiki --exclude 草稿 废弃
```

Useful flags:

- `--tool-root <path>`: override the default `/Users/park0er/coding/PerKnowledgeBase/feishu2md`.
- `--skip-fix-links`: skip link rewriting after export.
- `--skip-audit`: skip audit report generation.
- `--keep-whiteboard-empty`: preserve numbered whiteboard placeholders (auto-enabled in single mode when fusion runs).
- `--skip-whiteboard-fusion`: skip the automatic whiteboard rendering step (single mode).
- `--feishu-bin <path>`: feishu CLI used to render whiteboards (default: `feishu` on PATH; must be installed and logged in).
- `--only-docs`: skip sheets/files for folder/wiki exports when speed matters.
- `--dry-run`: print the commands without running them.

## Whiteboard / Canvas Handling (automated)

feishu2md is preferred for text, nested tables, and images, but its built-in
board export fails (`99991672` scope error) and drops whiteboards. So whiteboards
are routed through the native `feishu` CLI and fused back in:

1. The exporter runs feishu2md with `--keep-whiteboard-empty`. The patched
   `feishu-docx` emits placeholders that carry the board token:
   `【白板 序号N】<!--wb:TOKEN-->`.
2. `scripts/fuse_whiteboards.py` finds each marker, renders that token via
   `feishu fetch <TOKEN> --type whiteboard --output <assets>/<TOKEN>.png`, and
   replaces the marker with `![whiteboard](<assets>/<TOKEN>.png)`.
3. Mapping is **by token**, so it is robust to ordering and grid-embedded boards.

All modes run this automatically across every exported `.md` (disable with
`--skip-whiteboard-fusion`). You can also run it standalone on any feishu2md
export:

```bash
python3 /path/to/skill/scripts/fuse_whiteboards.py --md <exported.md>
```

Requires the `feishu` CLI installed and logged in (`feishu auth status`). The
feishu2md side requires the patched `feishu-docx` and its Python deps — see
`references/toolchain.md`.

## Output Expectations

- Preserve local image paths rather than converting them to remote URLs.
- Do not copy credentials, token files, or app secrets into project materials or skill directories.
- Keep source exports separate from derived drafts/reviews so reviewers can trace evidence.
- For performance projects, place raw exports under `Performance_Workspace/01_Human_Preparation/02_Input_Materials/` unless the user specifies another target.
