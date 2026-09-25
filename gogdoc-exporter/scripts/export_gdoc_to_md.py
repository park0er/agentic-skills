#!/usr/bin/env python3
"""
GogdocExporter

Export Google Docs into Markdown/PDF using gog CLI (no browser automation).

Features:
- Resolve target doc by docId, title query, or latest doc in Drive
- Export Markdown with formatting preserved (DOCX -> HTML -> Markdown)
- Export PDF using Google native export
- Write both outputs into one target folder (default Obsidian folder)
- Emit JSON summary for automation
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    import mammoth  # type: ignore
    from markdownify import markdownify as md  # type: ignore
except Exception:
    print("[ERROR] Missing dependencies: mammoth, markdownify", file=sys.stderr)
    print("Install with: python3 -m pip install --user mammoth markdownify", file=sys.stderr)
    raise


DOC_MIME = "application/vnd.google-apps.document"

DEFAULT_CONFIG: Dict[str, Any] = {
    "vault_root": "/Users/park0er/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1",
    "target_subdir": "Rollie/Rollie的报告厅",
    "filename_format": "YYYY-MM-DD_{slug}",
    "tags": ["📥/Rollie", "#report/google-docs"],
    "default_formats": ["md", "pdf"],
    "default_send_pdf_in_chat": True,
}


@dataclass
class DocMeta:
    doc_id: str
    title: str
    web_view_link: str
    modified_time: str | None = None


def run(cmd: List[str]) -> str:
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return proc.stdout.strip()


def run_json(cmd: List[str]) -> Dict[str, Any]:
    raw = run(cmd)
    if not raw:
        return {}
    return json.loads(raw)


def load_config(path: Path) -> Dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if path.exists():
        user_cfg = json.loads(path.read_text(encoding="utf-8"))
        cfg.update(user_cfg)
    return cfg


def add_account(cmd: List[str], account: str | None) -> List[str]:
    if account:
        return cmd + ["--account", account]
    return cmd


def safe_slug(text: str) -> str:
    text = text.strip()
    text = text.replace("/", "-").replace("\\", "-").replace(":", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^\w\-\u4e00-\u9fff]", "", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-.")
    return text or "untitled"


def query_escape(value: str) -> str:
    # Drive query string literal uses single quotes
    return value.replace("\\", "\\\\").replace("'", "\\'")


def list_docs(account: str | None, name_contains: str | None = None) -> List[Dict[str, Any]]:
    drive_query = f"mimeType='{DOC_MIME}' and trashed=false"
    if name_contains:
        drive_query += f" and name contains '{query_escape(name_contains)}'"

    files: List[Dict[str, Any]] = []
    page: str | None = None
    while True:
        cmd = [
            "gog",
            "drive",
            "ls",
            "--query",
            drive_query,
            "--max",
            "200",
            "--json",
        ]
        if page:
            cmd += ["--page", page]
        cmd = add_account(cmd, account)
        data = run_json(cmd)
        files.extend(data.get("files", []))
        page = data.get("nextPageToken")
        if not page:
            break

    return files


def newest_doc(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not files:
        raise RuntimeError("No Google Docs found matching criteria.")
    return max(files, key=lambda x: x.get("modifiedTime") or "")


def get_doc_meta(doc_id: str, account: str | None) -> DocMeta:
    info_cmd = add_account(["gog", "docs", "info", doc_id, "--json"], account)
    info = run_json(info_cmd)

    title = info.get("document", {}).get("title") or info.get("file", {}).get("name") or doc_id
    link = info.get("file", {}).get("webViewLink") or f"https://docs.google.com/document/d/{doc_id}/edit"

    # Try drive get for modifiedTime (optional)
    modified = None
    try:
        get_cmd = add_account(["gog", "drive", "get", doc_id, "--json"], account)
        g = run_json(get_cmd)
        modified = g.get("file", {}).get("modifiedTime")
    except Exception:
        modified = None

    return DocMeta(doc_id=doc_id, title=title, web_view_link=link, modified_time=modified)


def resolve_doc(doc_id: str | None, query: str | None, account: str | None) -> DocMeta:
    if doc_id:
        return get_doc_meta(doc_id, account)

    docs = list_docs(account=account, name_contains=query)
    selected = newest_doc(docs)
    selected_id = selected["id"]
    meta = get_doc_meta(selected_id, account)
    if not meta.modified_time:
        meta.modified_time = selected.get("modifiedTime")
    return meta


def download_google_file(doc_id: str, fmt: str, out_path: Path, account: str | None) -> None:
    cmd = [
        "gog",
        "drive",
        "download",
        doc_id,
        "--format",
        fmt,
        "--out",
        str(out_path),
        "--json",
    ]
    cmd = add_account(cmd, account)
    run_json(cmd)


def convert_docx_to_markdown(docx_path: Path) -> str:
    with docx_path.open("rb") as f:
        html = mammoth.convert_to_html(f).value
    markdown = md(html, heading_style="ATX", bullets="-", strip=["span"])
    markdown = markdown.replace("\ufeff", "")
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip() + "\n"
    return markdown


def render_frontmatter(tags: List[str], created_iso: str) -> str:
    rows = ["---", "tags:"]
    for tag in tags:
        rows.append(f"  - {tag}")
    rows.extend([f"created: {created_iso}", "source: OpenClaw", "---", ""])
    return "\n".join(rows)


def render_markdown_doc(meta: DocMeta, body: str, cfg: Dict[str, Any], include_frontmatter: bool) -> str:
    parts: List[str] = []
    if include_frontmatter:
        tags = cfg.get("tags", DEFAULT_CONFIG["tags"])
        parts.append(render_frontmatter(tags, datetime.now().astimezone().isoformat(timespec="seconds")))

    parts.append(f"**原始文档链接**：{meta.web_view_link}  ")
    parts.append("**转换链路**：GOG 导出 DOCX → 本地转换 Markdown（保留标题/列表/表格）")
    parts.append("\n---\n")
    parts.append(body)
    return "\n".join(parts)


def build_base_name(title: str, cfg: Dict[str, Any], override: str | None) -> str:
    if override:
        return override
    fmt = cfg.get("filename_format", "YYYY-MM-DD_{slug}")
    today = datetime.now().strftime("%Y-%m-%d")
    return fmt.replace("YYYY-MM-DD", today).replace("{slug}", safe_slug(title))


def parse_formats(args: argparse.Namespace, cfg: Dict[str, Any]) -> List[str]:
    if args.only_markdown and args.only_pdf:
        raise ValueError("--only-markdown and --only-pdf cannot be used together")

    if args.only_markdown:
        return ["md"]
    if args.only_pdf:
        return ["pdf"]

    if args.formats:
        formats = [x.strip().lower() for x in args.formats.split(",") if x.strip()]
    else:
        formats = [str(x).lower() for x in cfg.get("default_formats", ["md", "pdf"])]

    valid = {"md", "pdf"}
    bad = [f for f in formats if f not in valid]
    if bad:
        raise ValueError(f"Unsupported formats: {bad}. Valid: md,pdf")

    dedup = []
    for f in formats:
        if f not in dedup:
            dedup.append(f)
    return dedup


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Google Docs to Markdown/PDF")
    parser.add_argument("--doc-id", help="Google Doc ID")
    parser.add_argument("--query", help="Name contains query; picks most recently modified match")
    parser.add_argument("--formats", help="Comma-separated output formats: md,pdf")
    parser.add_argument("--only-markdown", action="store_true", help="Export only markdown")
    parser.add_argument("--only-pdf", action="store_true", help="Export only pdf")
    parser.add_argument("--out-dir", help="Target output directory")
    parser.add_argument("--base-name", help="Output base name without extension")
    parser.add_argument("--config", help="Path to config.json")
    parser.add_argument("--account", help="Explicit gog account email")
    parser.add_argument("--no-frontmatter", action="store_true", help="Skip YAML frontmatter in markdown")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON result")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    cfg_path = Path(args.config) if args.config else skill_root / "references" / "config.json"
    cfg = load_config(cfg_path)

    formats = parse_formats(args, cfg)
    meta = resolve_doc(args.doc_id, args.query, args.account)

    out_dir = Path(args.out_dir) if args.out_dir else Path(cfg["vault_root"]) / cfg["target_subdir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    base_name = build_base_name(meta.title, cfg, args.base_name)

    outputs: Dict[str, str] = {}

    if "pdf" in formats:
        pdf_path = out_dir / f"{base_name}.pdf"
        download_google_file(meta.doc_id, "pdf", pdf_path, args.account)
        outputs["pdf"] = str(pdf_path)

    if "md" in formats:
        with tempfile.TemporaryDirectory(prefix="gogdoc-export-") as td:
            docx_path = Path(td) / f"{meta.doc_id}.docx"
            download_google_file(meta.doc_id, "docx", docx_path, args.account)
            body = convert_docx_to_markdown(docx_path)
            md_text = render_markdown_doc(meta, body, cfg, include_frontmatter=(not args.no_frontmatter))
            md_path = out_dir / f"{base_name}.md"
            md_path.write_text(md_text, encoding="utf-8")
            outputs["md"] = str(md_path)

    result = {
        "doc": {
            "id": meta.doc_id,
            "title": meta.title,
            "webViewLink": meta.web_view_link,
            "modifiedTime": meta.modified_time,
        },
        "outputs": outputs,
        "formats": formats,
        "outDir": str(out_dir),
        "baseName": base_name,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[OK] Doc: {meta.title} ({meta.doc_id})")
        for fmt, path in outputs.items():
            print(f"[OK] {fmt.upper()}: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
