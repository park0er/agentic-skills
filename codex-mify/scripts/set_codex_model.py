#!/usr/bin/env python3
"""Switch the Codex model in ~/.codex/config.toml.

Mirrors the pattern of mify-model-gateway's set_cc_model.py:
  * --dry-run shows what would change
  * --apply writes (and runs a smoke test; auto-reverts on failure)
  * --revert restores from the most recent timestamped backup

Updates top-level `model = "..."`, `[model_providers.mify].name = "..."`,
and the Codex 1M context-window catalog fields so Desktop UI label tracks
the current model without falling back to Codex's 272k unknown-model metadata.

Usage:
  python3 set_codex_model.py --model azure_openai/gpt-5.5 --dry-run
  python3 set_codex_model.py --model azure_openai/gpt-5.5 --apply
  python3 set_codex_model.py --model azure_openai/gpt-5.5 --apply --no-smoke-test
  python3 set_codex_model.py --revert
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CODEX_DIR = Path.home() / ".codex"
CONFIG = CODEX_DIR / "config.toml"
MODEL_CATALOG = CODEX_DIR / "model_catalog.local.json"
MODELS_CACHE = CODEX_DIR / "models_cache.json"
CREDS = Path.home() / ".config" / "mify" / "credentials"
MIFY_RESPONSES_URL = "https://api.llm.mioffice.cn/v1/responses"
CONTEXT_WINDOW = 1_000_000
EFFECTIVE_CONTEXT_WINDOW_PERCENT = 95
AUTO_COMPACT_TOKEN_LIMIT = 850_000
CONTEXT_MODEL_SLUGS = (
    "ppio/pa/gpt-5.5",
    "xiaomi/mimo-v2.5-pro",
    "azure_openai/gpt-5.5",
    "xiaomi/mimo-v2.5",
    "deepseek/deepseek-v4-pro",
    "minimax/MiniMax-M3",
    "zhipuai/glm-5.2",
    "gemini-3.1-pro",
    "gemini-3.5-flash",
)
MODEL_CONTEXT_OVERRIDES = {
    # PPIO's gateway currently rejects larger prompts even though GPT-5.5 is 1M-capable.
    "ppio/pa/gpt-5.5": 272_000,
}



def _base_model_catalog() -> dict:
    if MODELS_CACHE.is_file():
        try:
            return json.loads(MODELS_CACHE.read_text())
        except json.JSONDecodeError:
            pass
    return {"models": []}


def _template_model(models: list[dict]) -> dict:
    for model in models:
        if model.get("slug") == "gpt-5.5":
            return model
    if models:
        return models[0]
    return {
        "slug": "gpt-5.5",
        "display_name": "GPT-5.5",
        "description": None,
        "supported_in_api": True,
        "priority": 99,
        "context_window": CONTEXT_WINDOW,
        "max_context_window": CONTEXT_WINDOW,
        "effective_context_window_percent": EFFECTIVE_CONTEXT_WINDOW_PERCENT,
        "experimental_supported_tools": [],
        "input_modalities": ["text"],
    }


def build_model_catalog(extra_slug: str | None = None) -> dict:
    catalog = _base_model_catalog()
    models = list(catalog.get("models") or [])
    template = _template_model(models)
    by_slug = {model.get("slug"): model for model in models}
    slugs = list(CONTEXT_MODEL_SLUGS)
    if extra_slug and extra_slug not in slugs:
        slugs.append(extra_slug)
    overrides = []
    for slug in slugs:
        model = dict(template)
        model.update(by_slug.get(slug, {}))
        model["slug"] = slug
        model["display_name"] = slug
        context_window = MODEL_CONTEXT_OVERRIDES.get(slug, CONTEXT_WINDOW)
        model["context_window"] = context_window
        model["max_context_window"] = context_window
        model["effective_context_window_percent"] = EFFECTIVE_CONTEXT_WINDOW_PERCENT
        model["supported_in_api"] = True
        overrides.append(model)
    seen = set()
    merged = []
    for model in overrides + models:
        slug = model.get("slug")
        if slug in seen:
            continue
        seen.add(slug)
        merged.append(model)
    catalog["models"] = merged
    return catalog


def write_model_catalog(extra_slug: str | None = None) -> None:
    MODEL_CATALOG.parent.mkdir(parents=True, exist_ok=True)
    catalog = build_model_catalog(extra_slug)
    MODEL_CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")


def ensure_root_key(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf'^(\s*{re.escape(key)}\s*=).*$' , re.MULTILINE)
    replacement = f'{key} = {value}'
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    first_section = re.search(r'^\s*\[', text, re.MULTILINE)
    index = first_section.start() if first_section else len(text)
    prefix = text[:index].rstrip()
    suffix = text[index:]
    return prefix + "\n" + replacement + "\n" + suffix.lstrip("\n")

def backup(cfg: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = cfg.with_suffix(cfg.suffix + f".bak.{stamp}")
    shutil.copy2(cfg, bak)
    return bak


def latest_backup(cfg: Path) -> Path | None:
    candidates = sorted(cfg.parent.glob(cfg.name + ".bak.*"))
    return candidates[-1] if candidates else None


def read_fields(text: str) -> dict:
    """Extract current top-level model and [model_providers.mify].name for display."""
    top_model = re.search(r'^model\s*=\s*"([^"]+)"', text, re.MULTILINE)

    mify_name: str | None = None
    section_match = re.search(
        r'\[model_providers\.mify\][^\[]*', text, re.DOTALL
    )
    if section_match:
        name_in_section = re.search(
            r'^name\s*=\s*"([^"]+)"',
            section_match.group(0),
            re.MULTILINE,
        )
        if name_in_section:
            mify_name = name_in_section.group(1)

    return {
        "model": top_model.group(1) if top_model else None,
        "name": mify_name,
    }


def patch_text(text: str, new_model: str) -> str:
    """Return new config text with top-level model + mify.name both updated."""
    # 1. Top-level model = "..."
    new_text = re.sub(
        r'^(model\s*=\s*)"[^"]+"',
        lambda m: f'{m.group(1)}"{new_model}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )

    # 2. [model_providers.mify].name = "..."  — rewrite ONLY within that section
    short_id = new_model.split("/", 1)[-1] if "/" in new_model else new_model

    def rewrite_section(match: re.Match) -> str:
        section_body = match.group(0)
        return re.sub(
            r'^(name\s*=\s*)"[^"]*"',
            lambda mm: f'{mm.group(1)}"{short_id}"',
            section_body,
            count=1,
            flags=re.MULTILINE,
        )

    new_text = re.sub(
        r'\[model_providers\.mify\][^\[]*',
        rewrite_section,
        new_text,
        count=1,
        flags=re.DOTALL,
    )
    new_text = ensure_root_key(new_text, "model_catalog_json", f'"{MODEL_CATALOG}"')
    new_text = ensure_root_key(new_text, "model_context_window", str(CONTEXT_WINDOW))
    new_text = ensure_root_key(new_text, "model_auto_compact_token_limit", str(AUTO_COMPACT_TOKEN_LIMIT))
    return new_text


def _load_mify_key() -> str | None:
    key = os.environ.get("MIFY_API_KEY")
    if key:
        return key
    if CREDS.is_file():
        for line in CREDS.read_text().splitlines():
            m = re.match(
                r'\s*export\s+MIFY_API_KEY\s*=\s*(?:"([^"]+)"|\'([^\']+)\'|(\S+))',
                line,
            )
            if m:
                return m.group(1) or m.group(2) or m.group(3)
    return None


def smoke_test(model: str, timeout: int = 30) -> tuple[int, str]:
    """POST to /v1/responses with the new model. Returns (http_code, body_snippet)."""
    key = _load_mify_key()
    if not key:
        return (0, "MIFY_API_KEY not available (checked $MIFY_API_KEY and ~/.config/mify/credentials)")

    payload = json.dumps({"model": model, "input": "hi"})
    try:
        proc = subprocess.run(
            [
                "curl", "-sS", "-X", "POST", MIFY_RESPONSES_URL,
                "-H", f"Authorization: Bearer {key}",
                "-H", "Content-Type: application/json",
                "-d", payload,
                "-w", "\nHTTP_STATUS:%{http_code}\n",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return (0, f"timeout after {timeout}s")

    output = proc.stdout
    m = re.search(r'HTTP_STATUS:(\d+)\s*$', output)
    code = int(m.group(1)) if m else 0
    body = output[: m.start()].rstrip() if m else output
    return (code, body)


def cmd_revert() -> int:
    bak = latest_backup(CONFIG)
    if not bak:
        print(f"No backups found matching {CONFIG.name}.bak.*", file=sys.stderr)
        return 1
    shutil.copy2(bak, CONFIG)
    print(f"✓ Restored {CONFIG} from {bak.name}")
    print("→ Cmd+Q Codex Desktop and reopen to apply.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--model", help='New model slug, e.g. azure_openai/gpt-5.5')
    ap.add_argument("--dry-run", action="store_true", help="Show planned diff, don't write")
    ap.add_argument("--apply", action="store_true", help="Write changes (and run smoke test)")
    ap.add_argument("--revert", action="store_true", help="Restore most recent .bak and exit")
    ap.add_argument(
        "--no-smoke-test", action="store_true",
        help="Skip the /v1/responses smoke test after writing",
    )
    args = ap.parse_args()

    if args.revert:
        return cmd_revert()

    if not args.model:
        ap.error("--model is required (unless --revert)")

    if not (args.dry_run or args.apply):
        ap.error("pass --dry-run or --apply")

    if not CONFIG.is_file():
        print(f"{CONFIG} does not exist. Run install.py first.", file=sys.stderr)
        return 1

    old_text = CONFIG.read_text()
    current = read_fields(old_text)
    new_text = patch_text(old_text, args.model)
    short_id = args.model.split("/", 1)[-1] if "/" in args.model else args.model

    print(f"  current model:         {current['model']}")
    print(f"  current provider name: {current['name']}")
    print(f"  → new model:           {args.model}")
    print(f"  → new provider name:   {short_id}")

    if new_text == old_text:
        print("\nNo changes needed — config already has this value.")
        return 0

    if args.dry_run:
        print(f"  → model catalog:       {MODEL_CATALOG}")
        print(f"  → context window:      {CONTEXT_WINDOW} ({CONTEXT_WINDOW * EFFECTIVE_CONTEXT_WINDOW_PERCENT // 100} effective)")
        print("\n(dry-run complete; rerun with --apply to write)")
        return 0

    # Apply path
    bak = backup(CONFIG)
    print(f"\n  backup: {bak.name}")
    CONFIG.write_text(new_text)
    write_model_catalog(args.model)
    print(f"  ✓ {CONFIG.name} written")
    print(f"  ✓ {MODEL_CATALOG.name} written ({CONTEXT_WINDOW} context / {CONTEXT_WINDOW * EFFECTIVE_CONTEXT_WINDOW_PERCENT // 100} effective)")

    if args.no_smoke_test:
        print("\n✓ Model switched (smoke test skipped)")
        print("→ Cmd+Q Codex Desktop and reopen to apply.")
        return 0

    print("  smoke test via /v1/responses ...")
    code, body = smoke_test(args.model)
    if code == 200:
        print(f"  ✓ HTTP 200 (Mify accepted the new model)")
        print("\n✓ Model switched + smoke-tested")
        print("→ Cmd+Q Codex Desktop and reopen to apply.")
        return 0

    # Smoke test failed — auto-revert
    print(f"  ✗ HTTP {code}")
    snippet = body[:300] if body else "(empty body)"
    print(f"    response: {snippet}")
    shutil.copy2(bak, CONFIG)
    print(f"\n✗ Smoke test failed — auto-reverted from {bak.name}")
    print(f"  Your config is back to model = \"{current['model']}\".")
    print("  Common causes:")
    print("    · 400 'Not supported model': gateway/provider does not currently accept that slug")
    print("    · 401: Mify key invalid or expired")
    print("    · 429: rate limit on that owner channel")
    return 2


if __name__ == "__main__":
    sys.exit(main())
