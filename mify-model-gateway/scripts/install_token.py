#!/usr/bin/env python3
"""Install a Mify API key as a persistent env var.

Reads the token from STDIN (never argv — stays out of `ps` and shell history).
Validates it hits /v1/models, then writes:

  ~/.config/mify/credentials   (chmod 600, contents: export MIFY_API_KEY=...)

and ensures ~/.zshrc (and ~/.bashrc if present) sources that file.

Idempotent: overwriting an existing credentials file is OK; the zshrc/bashrc
source line is only appended when missing.
"""

from __future__ import annotations

import json
import os
import stat
import sys
import urllib.error
import urllib.request
from pathlib import Path

GATEWAY_URL = "https://api.llm.mioffice.cn/v1/models"
SOURCE_MARK = "# mify-model-gateway skill credentials"
SOURCE_LINE = '[ -r "$HOME/.config/mify/credentials" ] && source "$HOME/.config/mify/credentials"'


def die(msg: str, code: int = 1) -> "None":
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(code)


def read_key_from_stdin() -> str:
    if sys.stdin.isatty():
        die(
            "Refusing to prompt for the key interactively.\n"
            "Pipe it in instead:  echo \"$YOUR_KEY\" | python3 install_token.py"
        )
    key = sys.stdin.read().strip()
    if not key:
        die("Empty input — no key provided on stdin.")
    return key


def sanity_check_format(key: str) -> None:
    if not key.startswith("sk-"):
        die(f"Key does not look right: expected to start with 'sk-', got prefix {key[:3]!r}.")
    if not (20 <= len(key) <= 200):
        die(f"Key length {len(key)} is outside the plausible range (20-200).")
    # no whitespace / newlines inside
    if any(c.isspace() for c in key):
        die("Key contains whitespace. Paste the key as a single token.")


def verify_against_gateway(key: str) -> int:
    """Hit /v1/models with the key. Return number of models on success."""
    req = urllib.request.Request(GATEWAY_URL, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        die(
            f"Gateway rejected the key: HTTP {e.code} {e.reason}.\n"
            "Double-check the key you pasted, or confirm it hasn't been revoked."
        )
    except urllib.error.URLError as e:
        die(
            f"Cannot reach {GATEWAY_URL}: {e.reason}.\n"
            "Are you on Xiaomi intranet / VPN?"
        )
    models = payload.get("data", [])
    if not models:
        die("Gateway responded but returned 0 models. Unusual — aborting.")
    return len(models)


def write_credentials(key: str) -> Path:
    config_dir = Path.home() / ".config" / "mify"
    config_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(config_dir, stat.S_IRWXU)  # 700

    cred_file = config_dir / "credentials"
    content = (
        "# Mify 大模型网关 API Key\n"
        "# Managed by mify-model-gateway skill — overwrite at will.\n"
        f"export MIFY_API_KEY={key}\n"
    )
    # Touch first with 600, then write — avoids an O_RDWR race where the new
    # file lands world-readable for a split second.
    cred_file.touch(mode=0o600, exist_ok=True)
    os.chmod(cred_file, stat.S_IRUSR | stat.S_IWUSR)  # 600
    cred_file.write_text(content, encoding="utf-8")
    return cred_file


def ensure_source_in_rc(rc_path: Path) -> str:
    """Append the source line to rc_path if missing. Return status string."""
    if not rc_path.exists():
        return f"(skipped — {rc_path} does not exist)"

    existing = rc_path.read_text(encoding="utf-8")

    # Consider it already installed if either the mark or the raw source line is present.
    if SOURCE_MARK in existing or SOURCE_LINE in existing:
        return f"already sources credentials (no change)"

    to_append = f"\n\n{SOURCE_MARK}\n{SOURCE_LINE}\n"
    with rc_path.open("a", encoding="utf-8") as f:
        f.write(to_append)
    return "added source line"


def detect_unusual_shell() -> str | None:
    shell = os.environ.get("SHELL", "")
    base = Path(shell).name if shell else ""
    if base in {"zsh", "bash", ""}:
        return None
    return shell  # fish / nu / csh / etc.


def main() -> None:
    key = read_key_from_stdin()
    sanity_check_format(key)
    model_count = verify_against_gateway(key)

    cred_file = write_credentials(key)

    home = Path.home()
    zsh_status = ensure_source_in_rc(home / ".zshrc")
    bash_status = ensure_source_in_rc(home / ".bashrc")

    # Report without echoing the key itself.
    print(f"✓ Key validated against {GATEWAY_URL} ({model_count} models visible)")
    print(f"✓ Saved to {cred_file} (chmod 600, length={len(key)})")
    print(f"  ~/.zshrc: {zsh_status}")
    print(f"  ~/.bashrc: {bash_status}")

    unusual = detect_unusual_shell()
    if unusual:
        print(
            f"\n⚠ Your $SHELL is {unusual}, not zsh/bash. "
            f"Add this line to that shell's rc file manually:\n  {SOURCE_LINE}"
        )

    print(
        "\nNext step: open a new terminal, OR run in this one:\n"
        "  source ~/.config/mify/credentials\n"
        "Then try:\n"
        "  python3 ~/.claude/skills/mify-model-gateway/scripts/list_models.py --grep kimi"
    )


if __name__ == "__main__":
    main()
