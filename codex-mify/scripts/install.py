#!/usr/bin/env python3
"""First-time setup for Codex ↔ Mify integration. Idempotent — safe to rerun.

Does six things:
  1. Pre-flight checks — OS, Codex install (pops download page if missing),
     Mify creds
  2. Moves aside stale ~/.codex/auth.json from prior ChatGPT/OpenAI login
     (these make Codex Desktop's auth::manager hit a 403 refresh loop from
     CN IPs and render the UI unusable — see references/codex_setup_guide.md)
  3. Writes ~/.codex/model_catalog.local.json so custom Mify slugs get a
     1M context window instead of Codex fallback metadata (272k × 95%).
  4. Patches ~/.codex/config.toml via surgical strip + prepend (removes
     conflicting root-level `model`/`model_provider`/`model_reasoning_effort`
     and any existing `[model_providers.mify]` table, preserving every other
     section untouched). TOML-valid, truly idempotent.
  5. Stages LaunchAgent plist at ~/.config/mify/com.xiaomi.mify.env.plist and
     guides user through Finder-drag install (macOS TCC blocks direct writes
     to ~/Library/LaunchAgents/)
  6. Appends codex-model() zsh function to ~/.zshrc (idempotent via marker)

Usage:
  python3 install.py --dry-run                                  # preview
  python3 install.py --apply                                    # execute
  python3 install.py --apply --default-model azure_openai/gpt-5.4
  python3 install.py --revert                                   # undo
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()
CODEX_DIR = HOME / ".codex"
CONFIG = CODEX_DIR / "config.toml"
MODEL_CATALOG = CODEX_DIR / "model_catalog.local.json"
MODELS_CACHE = CODEX_DIR / "models_cache.json"
AUTH_JSON = CODEX_DIR / "auth.json"
CREDS = HOME / ".config" / "mify" / "credentials"
PLIST_STAGING = HOME / ".config" / "mify" / "com.xiaomi.mify.env.plist"
LAUNCHAGENT_TARGET = HOME / "Library" / "LaunchAgents" / PLIST_STAGING.name
ZSHRC = HOME / ".zshrc"

ZSH_MARKER_START = "# >>> codex-mify (managed by codex-mify skill; do not edit manually)"
ZSH_MARKER_END = "# <<< codex-mify"

DEFAULT_MODEL = "ppio/pa/gpt-5.5"
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

LAUNCHD_LABEL = "com.xiaomi.mify.env"

CODEX_DOWNLOAD_URL = "https://openai.com/codex"

TOTAL_STEPS = 6


def uid() -> int:
    return os.getuid()


def gui_domain() -> str:
    return f"gui/{uid()}"


# ─── Config.toml snippet ─────────────────────────────────────────────────

CONFIG_SNIPPET_TEMPLATE = """\
# === Mify gateway config (managed by codex-mify skill) ===
# Setup guide: ~/.claude/skills/codex-mify/references/codex_setup_guide.md
# Daily model switch: `codex-model <slug>` (zsh fn) or scripts/set_codex_model.py

model                  = "{model}"
model_provider         = "mify"
model_reasoning_effort = "{reasoning_effort}"
model_catalog_json = "{model_catalog}"
model_context_window = {context_window}
model_auto_compact_token_limit = {auto_compact_token_limit}

[model_providers.mify]
# `name` is display-only; synced with `model` by codex-model / set_codex_model.py
name     = "{short_name}"
base_url = "https://api.llm.mioffice.cn/v1"
env_key  = "MIFY_API_KEY"
wire_api = "responses"           # Codex PR #10157 removed `chat` — only responses works
requires_openai_auth = true      # Desktop UI workaround for issue #10867
"""

DEFAULT_REASONING_EFFORT = "low"
_REASONING_EFFORT_RE = re.compile(
    r'^\s*model_reasoning_effort\s*=\s*"([^"]+)"',
    re.MULTILINE,
)


def _existing_reasoning_effort(text: str) -> str | None:
    """Read the existing root-level model_reasoning_effort value so rerun
    doesn't silently clobber a user's "high" / "medium" preference. Only
    looks before the first [section] header (root scope)."""
    first_section = re.search(r"^\s*\[", text, re.MULTILINE)
    scope = text[: first_section.start()] if first_section else text
    m = _REASONING_EFFORT_RE.search(scope)
    return m.group(1) if m else None


# ─── Model catalog for 1M context windows ────────────────────────────────


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


def build_model_catalog() -> dict:
    catalog = _base_model_catalog()
    models = list(catalog.get("models") or [])
    template = _template_model(models)
    by_slug = {model.get("slug"): model for model in models}
    overrides = []
    for slug in CONTEXT_MODEL_SLUGS:
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


def ensure_model_catalog(apply_mode: bool) -> bool:
    step("Model catalog (1M context for Mify slugs)")
    catalog = build_model_catalog()
    rendered = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    if MODEL_CATALOG.is_file() and MODEL_CATALOG.read_text() == rendered:
        log(f"{MODEL_CATALOG} already up to date", ok=True)
        return True
    if not apply_mode:
        log(f"would write {MODEL_CATALOG}")
        for slug in CONTEXT_MODEL_SLUGS:
            context_window = MODEL_CONTEXT_OVERRIDES.get(slug, CONTEXT_WINDOW)
        log(f"{slug} → context_window={context_window}, effective={context_window * EFFECTIVE_CONTEXT_WINDOW_PERCENT // 100}")
        return True
    MODEL_CATALOG.parent.mkdir(parents=True, exist_ok=True)
    MODEL_CATALOG.write_text(rendered)
    log(f"wrote {MODEL_CATALOG}", ok=True)
    for slug in CONTEXT_MODEL_SLUGS:
        context_window = MODEL_CONTEXT_OVERRIDES.get(slug, CONTEXT_WINDOW)
        log(f"{slug} → context_window={context_window}, effective={context_window * EFFECTIVE_CONTEXT_WINDOW_PERCENT // 100}")
    return True

# ─── LaunchAgent plist ───────────────────────────────────────────────────

PLIST_CONTENT = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.xiaomi.mify.env</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/zsh</string>
        <string>-c</string>
        <string>source "$HOME/.config/mify/credentials" &amp;&amp; launchctl setenv MIFY_API_KEY "$MIFY_API_KEY"</string>
    </array>
    <key>RunAtLoad</key><true/>
</dict>
</plist>
"""

# ─── codex-model zsh function ────────────────────────────────────────────

# Curly braces that should appear literally in the final output are doubled
# (`{{` → `{`) because this string is formatted with .format(). The raw
# string content is the zsh function exactly as it should appear in ~/.zshrc.

ZSH_FUNCTION_TEMPLATE = """
{marker_start}
codex-model() {{
  local cfg="$HOME/.codex/config.toml"
  local m="$1"
  if [ -z "$m" ]; then
    local current=$(awk -F'"' '/^model[[:space:]]*=[[:space:]]*"/ {{print $2; exit}}' "$cfg")
    cat <<USAGE
Current Codex model: ${{current:-<not set>}}

Usage: codex-model <model_slug>

Suggested candidates (kept in ~/.codex/model_catalog.local.json with 1M context):
  codex-model ppio/pa/gpt-5.5
  codex-model xiaomi/mimo-v2.5-pro
  codex-model azure_openai/gpt-5.5
  codex-model xiaomi/mimo-v2.5
  codex-model deepseek/deepseek-v4-pro
  codex-model minimax/MiniMax-M3
  codex-model zhipuai/glm-5.2
  codex-model gemini-3.1-pro
  codex-model gemini-3.5-flash

If a slug returns Mify 400 Not supported model, the local context metadata is
still installed; the gateway/provider must support that slug before calls work.

After switching: Cmd+Q Codex Desktop and reopen.
USAGE
    return
  fi
  if ! grep -qE '^model[[:space:]]*=[[:space:]]*"[^"]+"' "$cfg"; then
    echo "codex-model: cannot find top-level 'model = \\"...\\"' in $cfg" >&2
    return 1
  fi
  sed -i '' -E "s|^model[[:space:]]*=[[:space:]]*\\"[^\\"]+\\"|model                  = \\"$m\\"|" "$cfg"
  local short="${{m#*/}}"
  sed -i '' -E "s|^name[[:space:]]*=[[:space:]]*\\"[^\\"]*\\"|name     = \\"$short\\"|" "$cfg"
  echo "✓ Codex model → $m"
  echo "  display name → $short"
  echo "→ Cmd+Q Codex Desktop and reopen to apply."
}}
{marker_end}
"""

ZSH_FUNCTION = ZSH_FUNCTION_TEMPLATE.format(
    marker_start=ZSH_MARKER_START,
    marker_end=ZSH_MARKER_END,
)


# ─── Helpers ─────────────────────────────────────────────────────────────


def step(title: str) -> None:
    print(f"\n[{step.counter}/{TOTAL_STEPS}] {title}")
    step.counter += 1


step.counter = 1  # type: ignore[attr-defined]


def log(msg: str, ok: bool | None = None) -> None:
    prefix = "  · " if ok is None else ("  ✓ " if ok else "  ✗ ")
    print(f"{prefix}{msg}")


def backup(cfg: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = cfg.with_suffix(cfg.suffix + f".bak.{stamp}")
    shutil.copy2(cfg, bak)
    return bak


# ─── Phase 1: preconditions ──────────────────────────────────────────────


def _codex_location() -> str | None:
    if Path("/Applications/Codex.app").exists():
        return "/Applications/Codex.app"
    cli = shutil.which("codex")
    if cli:
        return cli
    return None


def _ensure_codex_installed(apply_mode: bool) -> bool:
    loc = _codex_location()
    if loc:
        log(f"Codex at: {loc}", ok=True)
        return True

    log("Codex not found on this Mac", ok=False)

    # Dry-run: just describe the action.
    if not apply_mode:
        log(f"would open {CODEX_DOWNLOAD_URL} and wait for user to install")
        return False

    # Non-interactive (piped stdin / Claude Code / CI): we can't block on
    # input, so print instructions and bail. User reruns after installing.
    if not sys.stdin.isatty():
        print()
        print(f"  Install Codex from: {CODEX_DOWNLOAD_URL}")
        print("  After installing, rerun this script.")
        return False

    # Interactive terminal: pop the download page and wait.
    print()
    print(f"  Opening the Codex download page: {CODEX_DOWNLOAD_URL}")
    print("  Install Codex (drag Codex.app into /Applications), then come")
    print("  back here and press Enter to continue.")
    subprocess.run(["open", CODEX_DOWNLOAD_URL])
    try:
        input("  (Ctrl-C to abort): ")
    except (EOFError, KeyboardInterrupt):
        print("\n  Aborted — Codex still not installed.")
        return False

    loc = _codex_location()
    if not loc:
        log("Still don't see Codex — did the install finish?", ok=False)
        log(f"Install it from {CODEX_DOWNLOAD_URL} then rerun this script.")
        return False
    log(f"Codex now at: {loc}", ok=True)
    return True


def check_preconditions(apply_mode: bool) -> bool:
    step("Pre-flight checks")

    if platform.system() != "Darwin":
        log("This skill is macOS-only.", ok=False)
        return False
    log("macOS detected", ok=True)

    if not _ensure_codex_installed(apply_mode):
        return False

    if not CREDS.is_file():
        log("Mify credentials missing.", ok=False)
        print()
        print("  Hand off to the mify-model-gateway skill to install the token first:")
        print("    1. Ask user for their sk- key from the Mify dashboard")
        print("    2. Run: printf %s '<KEY>' | \\")
        print("           python3 ~/.claude/skills/mify-model-gateway/scripts/install_token.py")
        print("  Then come back and rerun this install.")
        return False
    log(f"Mify credentials at {CREDS}", ok=True)

    return True


# ─── Phase 2: stale OpenAI auth ──────────────────────────────────────────


def _looks_like_chatgpt_login(auth: dict) -> bool:
    """A fresh-install auth.json from official ChatGPT login has auth_mode
    set to 'ChatGPT' and a non-empty refresh_token. On CN IPs, Codex's
    auth::manager loops forever trying to refresh that token against
    auth.openai.com, which returns 403 and crashes app-server. Detecting
    this specific signature avoids clobbering API-key-mode auth.json files
    that a user might legitimately have."""
    if auth.get("auth_mode") == "ChatGPT":
        return True
    tokens = auth.get("tokens") or {}
    if tokens.get("refresh_token"):
        return True
    return False


def handle_stale_auth(apply_mode: bool) -> bool:
    step("Stale OpenAI auth check (avoids Desktop 403 crash loop)")

    if not AUTH_JSON.is_file():
        log("no ~/.codex/auth.json — clean slate", ok=True)
        return True

    try:
        auth = json.loads(AUTH_JSON.read_text())
    except json.JSONDecodeError as e:
        log(f"~/.codex/auth.json present but not valid JSON ({e.msg})", ok=False)
        log("Leaving untouched; if Desktop won't launch, manually:")
        log(f"  mv {AUTH_JSON} {AUTH_JSON}.openai-bak-$(date +%Y%m%d-%H%M%S)")
        return True  # Non-fatal — maybe it's a newer format

    if not _looks_like_chatgpt_login(auth):
        log(
            f"auth.json exists but no stale OpenAI login detected "
            f"(auth_mode={auth.get('auth_mode', '<missing>')!r}) — leaving alone",
            ok=True,
        )
        return True

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = AUTH_JSON.with_name(f"auth.json.openai-bak-{stamp}")

    if not apply_mode:
        log(f"would mv {AUTH_JSON.name} → {target.name} (stale ChatGPT login detected)")
        return True

    AUTH_JSON.rename(target)
    log(f"mv {AUTH_JSON.name} → {target.name}", ok=True)
    log("Codex's auth::manager will now skip the 403-prone refresh.")
    log(f"(to restore: mv {target} {AUTH_JSON})")
    return True


# ─── Phase 3: config.toml patch (surgical TOML merge) ────────────────────


# Root-level keys that our Mify snippet owns. Any occurrence of these at
# the root of an existing config.toml (i.e. before the first [section]
# header) would collide with our snippet's definitions and cause a Rust
# `toml` strict-parse error. Strip them out surgically.
_CONFLICTING_ROOT_KEYS = (
    "model",
    "model_provider",
    "model_reasoning_effort",
    "model_catalog_json",
    "model_context_window",
    "model_auto_compact_token_limit",
)
_ROOT_KEY_RE = re.compile(
    r"^\s*(" + "|".join(_CONFLICTING_ROOT_KEYS) + r")\s*="
)
_SECTION_HEADER_RE = re.compile(r"^\s*\[([^\]]+)\]")
_MANAGED_COMMENT_RE = re.compile(
    r"^\s*#\s*(===\s*Mify gateway config|Setup guide:|Daily model switch:)"
)


def strip_conflicting_toml(text: str) -> str:
    """Remove root-level keys owned by the Mify snippet (`model`,
    `model_provider`, `model_reasoning_effort`, context-window catalog keys),
    any existing `[model_providers.mify]` (and
    subtables thereof), and our own managed-comment header lines.
    Preserves every other section, comment, and key untouched.

    This is the core of the idempotency guarantee: after this runs on any
    config.toml state — fresh, half-patched, double-patched, or already
    correct — the result can be cleanly prepended with our snippet and the
    file becomes strict-TOML-valid."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    in_root = True  # True until the first [section] header
    in_mify_table = False  # True while inside [model_providers.mify] or subtable

    for line in lines:
        header = _SECTION_HEADER_RE.match(line)
        if header:
            in_root = False
            section = header.group(1).strip()
            if section == "model_providers.mify" or section.startswith(
                "model_providers.mify."
            ):
                in_mify_table = True
                continue  # drop the header itself
            in_mify_table = False
            out.append(line)
            continue

        if in_mify_table:
            continue  # drop every line inside the Mify table

        if in_root:
            if _ROOT_KEY_RE.match(line):
                continue  # drop conflicting root key
            if _MANAGED_COMMENT_RE.match(line):
                continue  # drop our own managed comment headers (avoid orphans)

        out.append(line)

    result = "".join(out)
    # Collapse 3+ consecutive blank lines → 1, and lstrip leading blanks.
    result = re.sub(r"\n{3,}", "\n\n", result).lstrip("\n")
    return result


def patch_config(apply_mode: bool, default_model: str) -> bool:
    step("Patch ~/.codex/config.toml")

    short = default_model.split("/", 1)[-1] if "/" in default_model else default_model

    if not CONFIG.is_file():
        log(f"{CONFIG} does not exist; will create with Mify config only")
        snippet = CONFIG_SNIPPET_TEMPLATE.format(
            model=default_model,
            short_name=short,
            reasoning_effort=DEFAULT_REASONING_EFFORT,
            model_catalog=MODEL_CATALOG,
            context_window=CONTEXT_WINDOW,
            auto_compact_token_limit=AUTO_COMPACT_TOKEN_LIMIT,
        )
        if apply_mode:
            CONFIG.parent.mkdir(parents=True, exist_ok=True)
            CONFIG.write_text(snippet)
            log(f"wrote {CONFIG}", ok=True)
        return True

    original = CONFIG.read_text()
    # Preserve user's existing reasoning-effort choice across reruns rather
    # than silently resetting to "low". This is a user preference, not a
    # Mify-required field.
    effort = _existing_reasoning_effort(original) or DEFAULT_REASONING_EFFORT
    snippet = CONFIG_SNIPPET_TEMPLATE.format(
        model=default_model,
        short_name=short,
        reasoning_effort=effort,
        model_catalog=MODEL_CATALOG,
        context_window=CONTEXT_WINDOW,
        auto_compact_token_limit=AUTO_COMPACT_TOKEN_LIMIT,
    )
    stripped = strip_conflicting_toml(original)
    new_text = snippet + ("\n" + stripped if stripped else "")

    if new_text == original:
        log(f"{CONFIG} already in target state — no changes needed", ok=True)
        return True

    # Count what was removed, for a useful dry-run log message.
    removed_lines = len(original.splitlines()) - len(stripped.splitlines())

    if not apply_mode:
        if removed_lines > 0:
            log(
                f"would strip {removed_lines} conflicting line(s) "
                "(old model/provider/mify-block) and prepend Mify snippet"
            )
        else:
            log(f"would prepend Mify snippet to {CONFIG}")
        return True

    bak = backup(CONFIG)
    log(f"backup → {bak.name}")
    CONFIG.write_text(new_text)
    if removed_lines > 0:
        log(
            f"patched {CONFIG} (stripped {removed_lines} conflicting line(s) first)",
            ok=True,
        )
    else:
        log(f"patched {CONFIG}", ok=True)
    return True


# ─── Phase 4: LaunchAgent ────────────────────────────────────────────────


def launchagent_is_loaded() -> bool:
    r = subprocess.run(
        ["launchctl", "print", f"{gui_domain()}/{LAUNCHD_LABEL}"],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def stage_launchagent(apply_mode: bool) -> bool:
    step("LaunchAgent (GUI env persistence for MIFY_API_KEY)")

    if launchagent_is_loaded() and LAUNCHAGENT_TARGET.is_file():
        log("LaunchAgent already loaded and plist in place — skipping", ok=True)
        return True

    if not apply_mode:
        log(f"would stage plist at {PLIST_STAGING}")
        log(f"would guide user to drag into {LAUNCHAGENT_TARGET.parent}")
        log("would bootstrap + kickstart and verify env injection")
        return True

    PLIST_STAGING.parent.mkdir(parents=True, exist_ok=True)
    PLIST_STAGING.write_text(PLIST_CONTENT)
    r = subprocess.run(
        ["plutil", "-lint", str(PLIST_STAGING)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        log(f"plist lint failed: {r.stderr.strip()}", ok=False)
        return False
    log(f"staged plist at {PLIST_STAGING}", ok=True)

    if LAUNCHAGENT_TARGET.is_file():
        log(f"{LAUNCHAGENT_TARGET.name} already in LaunchAgents — bootstrapping")
    else:
        print()
        print("  ┌─ macOS TCC blocks direct writes to ~/Library/LaunchAgents/ ─────────────")
        print("  │  Opening two Finder windows for you. Drag the plist:")
        print(f"  │    FROM: {PLIST_STAGING.parent}")
        print(f"  │    TO:   {LAUNCHAGENT_TARGET.parent}")
        print("  │  Finder may ask permission — click Allow.")
        print("  └─")
        print()
        subprocess.run(["open", str(PLIST_STAGING.parent)])
        subprocess.run(["open", str(LAUNCHAGENT_TARGET.parent)])

        try:
            input("  Press Enter AFTER you've dragged the plist (Ctrl-C to abort): ")
        except (EOFError, KeyboardInterrupt):
            print("\n  (aborted; plist staged but not activated)")
            return False

        if not LAUNCHAGENT_TARGET.is_file():
            log(f"{LAUNCHAGENT_TARGET.name} not in LaunchAgents — drag didn't happen?", ok=False)
            return False
        log("plist in place", ok=True)

    # Load + kick to activate now
    r = subprocess.run(
        ["launchctl", "bootstrap", gui_domain(), str(LAUNCHAGENT_TARGET)],
        capture_output=True,
        text=True,
    )
    # bootstrap fails with code 37 if already loaded — that's fine
    if r.returncode not in (0, 37):
        log(f"launchctl bootstrap returned {r.returncode}: {r.stderr.strip()}")
        # keep going — kickstart still works
    subprocess.run(
        ["launchctl", "kickstart", "-k", f"{gui_domain()}/{LAUNCHD_LABEL}"],
        capture_output=True,
    )

    # Verify
    r = subprocess.run(
        ["launchctl", "getenv", "MIFY_API_KEY"],
        capture_output=True,
        text=True,
    )
    val = r.stdout.strip()
    if val.startswith("sk-"):
        log(f"MIFY_API_KEY injected into GUI env: {val[:8]}...", ok=True)
        return True
    log(f"MIFY_API_KEY not in GUI env after kickstart (got: {val!r})", ok=False)
    log("Check ~/.config/mify/credentials has `export MIFY_API_KEY=sk-...`")
    return False


# ─── Phase 5: zshrc function ─────────────────────────────────────────────


def install_zsh_function(apply_mode: bool) -> bool:
    step("zshrc codex-model function")

    existing = ZSHRC.read_text() if ZSHRC.is_file() else ""
    if ZSH_MARKER_START in existing:
        log(f"{ZSHRC.name} already has codex-model (marker found) — skipping", ok=True)
        return True
    # Detect hand-installed codex-model() without our marker (e.g. from the
    # original setup session). Don't append a duplicate.
    if re.search(r'^\s*codex-model\s*\(\s*\)\s*\{', existing, re.MULTILINE):
        log(f"{ZSHRC.name} has codex-model() without skill marker (likely hand-installed)", ok=True)
        log("leaving as-is to avoid duplicate definition")
        return True

    if not apply_mode:
        log(f"would append codex-model() function to {ZSHRC}")
        return True

    new = existing.rstrip() + "\n" + ZSH_FUNCTION
    ZSHRC.write_text(new)
    log(f"appended codex-model() to {ZSHRC}", ok=True)
    log("run `source ~/.zshrc` or open a new terminal to load it")
    return True


# ─── Revert ──────────────────────────────────────────────────────────────


def cmd_revert() -> int:
    print("Reverting codex-mify install:")

    # 1. Unload LaunchAgent (if loaded)
    if launchagent_is_loaded():
        subprocess.run(
            ["launchctl", "bootout", f"{gui_domain()}/{LAUNCHD_LABEL}"],
            capture_output=True,
        )
        print("  ✓ LaunchAgent unloaded")
    else:
        print("  · LaunchAgent not loaded (nothing to unload)")

    # 2. plist file in ~/Library/LaunchAgents/ — tell user to remove manually
    if LAUNCHAGENT_TARGET.is_file():
        print(f"  ⚠ {LAUNCHAGENT_TARGET} still present (TCC may block auto-delete)")
        print(f"    Remove manually: rm {LAUNCHAGENT_TARGET}")
    else:
        print("  · No plist in LaunchAgents")

    # 3. Remove zsh function (between markers)
    if ZSHRC.is_file():
        text = ZSHRC.read_text()
        if ZSH_MARKER_START in text:
            pattern = re.compile(
                re.escape(ZSH_MARKER_START) + r".*?" + re.escape(ZSH_MARKER_END) + r"\n?",
                re.DOTALL,
            )
            new = pattern.sub("", text).rstrip() + "\n"
            ZSHRC.write_text(new)
            print(f"  ✓ Removed codex-model() from {ZSHRC}")
        else:
            print("  · No codex-mify marker in zshrc")

    # 4. Restore most recent config.toml backup
    baks = sorted(CONFIG.parent.glob(CONFIG.name + ".bak.*"))
    if baks:
        shutil.copy2(baks[-1], CONFIG)
        print(f"  ✓ Restored {CONFIG} from {baks[-1].name}")
    else:
        print("  · No config.toml backup found to restore")

    # 5. Note any moved-aside auth.json files (don't touch them — user may
    # want them back, but also may not. Their call.)
    auth_baks = sorted(CODEX_DIR.glob("auth.json.openai-bak-*"))
    if auth_baks:
        print()
        print("  Moved-aside auth.json files (preserved, not touched by revert):")
        for b in auth_baks:
            print(f"    {b}")
        print("  To restore a prior ChatGPT login state: mv <one of the above> ~/.codex/auth.json")

    print("\n→ Cmd+Q Codex Desktop and reopen if it's running.")
    return 0


# ─── Entry ───────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--apply", action="store_true", help="Execute all steps")
    ap.add_argument("--dry-run", action="store_true", help="Show planned changes only")
    ap.add_argument("--revert", action="store_true", help="Undo the install")
    ap.add_argument(
        "--default-model",
        default=DEFAULT_MODEL,
        help=f"Top-level model slug to seed in config (default: {DEFAULT_MODEL})",
    )
    args = ap.parse_args()

    if args.revert:
        return cmd_revert()

    if not (args.apply or args.dry_run):
        ap.error("pass --dry-run, --apply, or --revert")

    print(f"codex-mify install {'(DRY RUN)' if args.dry_run else ''}")
    print("=" * 60)

    if not check_preconditions(args.apply):
        return 1

    if not handle_stale_auth(args.apply):
        return 1

    if not ensure_model_catalog(args.apply):
        return 1

    if not patch_config(args.apply, args.default_model):
        return 1

    if not stage_launchagent(args.apply):
        return 1

    if not install_zsh_function(args.apply):
        return 1

    print()
    print("─" * 60)
    if args.apply:
        print("✓ codex-mify install complete\n")
        print("Next steps:")
        print("  1. Open a new terminal (or `source ~/.zshrc`) to load codex-model")
        print("  2. Smoke-test CLI:")
        print("       codex exec --skip-git-repo-check --sandbox read-only 'Reply: working'")
        print("  3. Open Codex Desktop — first launch: choose 'Sign in with API key',")
        print("     type any 3+ chars, press Enter (UI-only bypass; real auth uses MIFY_API_KEY)")
    else:
        print("(DRY RUN complete — rerun with --apply to execute)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
