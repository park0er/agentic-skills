#!/usr/bin/env python3
"""Create or populate a Feishu editable whiteboard from a simple JSON spec."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


def run(cmd: list[str], retries: int = 0, wait_seconds: int = 75) -> str:
    for attempt in range(retries + 1):
        proc = subprocess.run(cmd, text=True, capture_output=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        rate_limited = "rate_limited" in output or "frequency limit" in output or "99991400" in output
        if proc.returncode == 0 and not rate_limited:
            return proc.stdout
        if attempt < retries and rate_limited:
            time.sleep(wait_seconds)
            continue
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{output}")
    raise AssertionError("unreachable")


def load_spec(path: Path) -> dict[str, Any]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise ValueError("spec must be a JSON object")
    if not isinstance(spec.get("elements"), list):
        raise ValueError("spec.elements must be a list")
    return spec


def text_payload(text: str, size: int, color: str = "#111827", align: str = "center") -> dict[str, Any]:
    return {
        "text": text,
        "font_size": size,
        "text_color": color,
        "text_color_type": 1,
        "horizontal_align": align,
        "vertical_align": "mid",
    }


def style_payload(element: dict[str, Any]) -> dict[str, Any]:
    border_style = element.get("border_style", "solid")
    if border_style == "dashed":
        border_style = "dash"
    return {
        "border_color": element.get("border", "#334155"),
        "border_color_type": 1,
        "border_opacity": 100,
        "border_style": border_style,
        "border_width": element.get("border_width", "medium"),
        "fill_color": element.get("fill", "#ffffff"),
        "fill_color_type": 1,
        "fill_opacity": element.get("fill_opacity", 70),
    }


def build_nodes(spec: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    shape_nodes: list[dict[str, Any]] = []
    connector_specs: list[dict[str, Any]] = []
    ids: list[str] = []
    for element in spec["elements"]:
        element_type = element.get("type")
        if element_type == "connector":
            connector_specs.append(element)
            continue
        element_id = element.get("id")
        if not element_id:
            raise ValueError(f"non-connector element missing id: {element}")
        ids.append(element_id)
        if element_type == "box":
            shape_nodes.append({
                "type": "composite_shape",
                "x": element["x"],
                "y": element["y"],
                "width": element["width"],
                "height": element["height"],
                "composite_shape": {"type": element.get("shape", "round_rect")},
                "style": style_payload(element),
                "text": text_payload(
                    element.get("text", ""),
                    int(element.get("font_size", 20)),
                    element.get("color", "#111827"),
                    element.get("align", "center"),
                ),
            })
        elif element_type == "text":
            shape_nodes.append({
                "type": "text_shape",
                "x": element["x"],
                "y": element["y"],
                "width": element["width"],
                "height": element["height"],
                "text": text_payload(
                    element.get("text", ""),
                    int(element.get("font_size", 24)),
                    element.get("color", "#111827"),
                    element.get("align", "left"),
                ),
            })
        else:
            raise ValueError(f"unknown element type: {element_type}")
    return shape_nodes, connector_specs, ids


def build_connectors(connector_specs: list[dict[str, Any]], id_map: dict[str, str]) -> list[dict[str, Any]]:
    nodes = []
    for element in connector_specs:
        start = element["from"]
        end = element["to"]
        if start not in id_map or end not in id_map:
            raise ValueError(f"connector references unknown id: {start}->{end}")
        nodes.append({
            "type": "connector",
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 0,
            "connector": {
                "shape": element.get("shape", "straight"),
                "specified_coordinate": True,
                "start": {
                    "arrow_style": element.get("start_arrow", "none"),
                    "attached_object": {
                        "id": id_map[start],
                        "position": element.get("from_position", {"x": 0.5, "y": 1}),
                        "snap_to": element.get("from_snap", "bottom"),
                    },
                },
                "end": {
                    "arrow_style": element.get("end_arrow", "triangle_arrow"),
                    "attached_object": {
                        "id": id_map[end],
                        "position": element.get("to_position", {"x": 0.5, "y": 0}),
                        "snap_to": element.get("to_snap", "top"),
                    },
                },
                "turning_points": element.get("turning_points", []),
            },
            "style": {
                "border_color": element.get("color", "#334155"),
                "border_color_type": 1,
                "border_width": element.get("border_width", "medium"),
                "border_style": element.get("border_style", "solid"),
            },
        })
    return nodes


def create_doc(title: str, description: str | None, out_dir: Path) -> tuple[str, str]:
    markdown = out_dir / "initial-doc.md"
    markdown.write_text(
        f"## 可编辑白板\n\n{description or ''}\n\n```mermaid\ngraph TD\n    Init[初始化画板]\n```\n",
        encoding="utf-8",
    )
    raw = run(["feishu", "docx", "create", title, "-f", str(markdown)], retries=2)
    data = json.loads(raw)
    url = data.get("url")
    if not url:
        raise RuntimeError(f"No doc URL returned: {raw}")
    fetch = run(["feishu", "fetch", url], retries=2)
    match = re.search(r'<whiteboard\s+token="([^"]+)"', fetch)
    if not match:
        raise RuntimeError(f"No whiteboard token found in fetch output: {fetch[:1000]}")
    return url, match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--whiteboard-token")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    spec = load_spec(args.spec)
    shape_nodes, connector_specs, ids = build_nodes(spec)
    (args.out_dir / "shape-nodes.json").write_text(json.dumps(shape_nodes, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.dry_run:
        print(json.dumps({"shape_nodes": len(shape_nodes), "connectors": len(connector_specs), "out_dir": str(args.out_dir)}, ensure_ascii=False, indent=2))
        return 0

    doc_url = None
    whiteboard_token = args.whiteboard_token
    if not whiteboard_token:
        doc_url, whiteboard_token = create_doc(spec.get("title", "手绘图可编辑白板"), spec.get("description"), args.out_dir)

    raw_ids = run(["feishu", "board", "create-notes", whiteboard_token, "-f", str(args.out_dir / "shape-nodes.json")], retries=2)
    node_ids = json.loads(raw_ids).get("node_ids", [])
    id_map = dict(zip(ids, node_ids))
    (args.out_dir / "id-map.json").write_text(json.dumps(id_map, ensure_ascii=False, indent=2), encoding="utf-8")

    connector_nodes = build_connectors(connector_specs, id_map)
    (args.out_dir / "connector-nodes.json").write_text(json.dumps(connector_nodes, ensure_ascii=False, indent=2), encoding="utf-8")
    connector_count = 0
    if connector_nodes:
        raw_connectors = run(["feishu", "board", "create-notes", whiteboard_token, "-f", str(args.out_dir / "connector-nodes.json")], retries=2)
        connector_count = len(json.loads(raw_connectors).get("node_ids", []))

    nodes_raw = run(["feishu", "board", "nodes", whiteboard_token], retries=1)
    nodes_data = json.loads(nodes_raw).get("nodes", [])
    counts = Counter(node.get("type") for node in nodes_data)
    summary = {
        "doc_url": doc_url,
        "whiteboard_token": whiteboard_token,
        "shape_nodes_created": len(node_ids),
        "connector_nodes_created": connector_count,
        "node_counts_by_type": counts,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
