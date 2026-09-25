---
name: handdraw-to-feishu-board
description: Convert hand-drawn architecture photos, whiteboard screenshots, Excalidraw/SVG/HTML diagrams, or rough product sketches into a Feishu document containing an editable Feishu whiteboard. Use when the user asks to “转飞书白板”, “建一个能编辑元素的白板”, “不要整张图片”, “图片里的框/文字/箭头可编辑”, or similar. Prefer creating native Board nodes (text_shape, composite_shape, connector) instead of embedding a bitmap or one large SVG.
---

# Handdraw To Feishu Board

## Goal

Rebuild a visual sketch as a Feishu document with an embedded whiteboard whose text, boxes, and arrows are separately editable. Do not satisfy the task by uploading the source image as the main whiteboard content unless the user explicitly asks for a non-editable reference image.

## Required Workflow

1. Inspect the source image/HTML/SVG and extract a logical diagram: layers, labels, boxes, status marks, and connection directions.
2. Create a compact reconstruction spec in JSON using `box`, `text`, and `connector` elements.
3. Run `scripts/create_editable_board.py` to create the Feishu doc, obtain the whiteboard token, and write native Board nodes.
4. Fetch or list the whiteboard to verify node counts include editable types, especially `text_shape`, `composite_shape`, and `connector`.
5. If the workspace has local document traceability rules, write the Feishu URL back to the local source/provenance Markdown header.

## Feishu Rules

- Use the `feishu` CLI, not browser automation, for creation and verification.
- Create an initial doc with a trivial Mermaid code block only to force Feishu to allocate a whiteboard token.
- After fetching the document, extract `<whiteboard token="...">` and call `feishu board create-notes <token> -f nodes.json`.
- Use `composite_shape` for boxes/containers, `text_shape` for standalone labels, and `connector` for arrows.
- Avoid `sticky_note`; the Feishu API returns it from reads but does not allow creating it.
- If Feishu rate-limits writes, wait 60–120 seconds and retry the failed step rather than recreating many duplicate docs.

## Reconstruction Heuristics

- Preserve meaning over pixel-perfect handwriting. Keep the original layer names, major components, ✅/❌ status marks, and directional arrows.
- Use large containers for layers and smaller boxes for components. Use dashed orange/red borders for uncertain or WIP areas.
- Use `✅` in green boxes for completed capabilities and `❌` in red boxes for missing platform capabilities.
- Keep labels short enough for direct editing. When handwriting is ambiguous, use best-effort text and mention uncertainty in the final response.
- Prefer a 16:9-ish coordinate canvas such as `0..1900` by `0..1200`; exact size is not required because Feishu whiteboard is spatial.

## Script Usage

Create a spec file, then run:

```bash
python3 /path/to/skill/scripts/create_editable_board.py \
  --spec /tmp/diagram-spec.json \
  --out-dir /tmp/diagram-board
```

Useful variants:

```bash
# Only generate Feishu node JSON for inspection; do not call Feishu.
python3 scripts/create_editable_board.py --spec spec.json --out-dir /tmp/board --dry-run

# Write into an existing whiteboard token instead of creating a new doc.
python3 scripts/create_editable_board.py --spec spec.json --whiteboard-token <token> --out-dir /tmp/board
```

Read `references/spec-schema.md` when writing or debugging a spec.

## Verification Checklist

- `feishu fetch <doc-url>` returns a `media` item with `type: whiteboard`.
- `feishu board nodes <whiteboard-token>` returns native editable nodes, not only `image` or one `svg` node.
- Expected minimum for a useful reconstruction: several `composite_shape` nodes, several `text_shape` nodes, and connector nodes for key arrows.
- Download a preview with `feishu board image <token> preview.png` only for visual QA; the preview image is not the deliverable.

## Final Response

Return the Feishu doc URL, the whiteboard token, a short editability proof such as node counts by type, and any local provenance file path if created.
