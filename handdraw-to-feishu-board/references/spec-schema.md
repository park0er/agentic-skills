# Editable Feishu Board Spec Schema

Use this reference when building a JSON spec for `scripts/create_editable_board.py`.

## Top-level fields

```json
{
  "title": "手绘图可编辑白板",
  "description": "optional note shown in the Feishu document",
  "elements": []
}
```

## Element types

### Box

Creates a Feishu `composite_shape` with editable text.

```json
{
  "type": "box",
  "id": "runtime-left",
  "x": 80,
  "y": 300,
  "width": 500,
  "height": 160,
  "text": "Agent Runtime\n本地",
  "border": "#334155",
  "fill": "#ffffff",
  "font_size": 22,
  "border_style": "solid"
}
```

`border_style` supports `solid`, `dash`, `dot`, and `none`. Do not use `dashed`.

### Text

Creates a standalone Feishu `text_shape`.

```json
{
  "type": "text",
  "id": "layer-label",
  "x": 40,
  "y": 160,
  "width": 180,
  "height": 50,
  "text": "应用层",
  "font_size": 26,
  "color": "#111827",
  "align": "left"
}
```

### Connector

Creates a Feishu `connector` between existing element IDs.

```json
{
  "type": "connector",
  "from": "zde",
  "to": "runtime-left",
  "color": "#16a34a",
  "shape": "curve"
}
```

Supported `shape`: `straight` or `curve`. The script attaches from bottom-center to top-center by default.

## Recommended colors

- Green done: border `#16a34a`, fill `#dcfce7`
- Red missing: border `#dc2626`, fill `#fee2e2`
- Orange WIP: border `#ea580c`, fill `#fff7ed`, border_style `dash`
- Blue tool/platform: border `#1e3a8a`, fill `#eff6ff`
- Neutral: border `#334155`, fill `#ffffff`
