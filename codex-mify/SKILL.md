---
name: codex-mify
description: Configure OpenAI Codex Desktop/CLI to use Xiaomi Mify gateway. Use for ~/.codex/config.toml Mify setup, 1M context window/model_catalog_json for custom Mify slugs, wire_api/chat errors, Not supported model, Desktop picker issues, GUI MIFY_API_KEY launchd env, codex-model switching among ppio/xiaomi/azure_openai/deepseek/minimax/zhipuai/gemini, or recovering broken Codex Mify config. Skip generic Mify API questions without Codex context and official OpenAI login issues.
---

# Codex ↔ Mify Gateway

Configure OpenAI Codex (Desktop app, CLI binary, VS Code `openai.chatgpt` extension — they all share `~/.codex/config.toml`) to route through Xiaomi's Mify gateway (`api.llm.mioffice.cn`) instead of OpenAI's official login.

**This skill reverse-references `mify-model-gateway` for all token management.** This skill does NOT install Mify API keys — if the user doesn't have one, stop and point them at `mify-model-gateway`'s `install_token.py`. See [Pre-check handoff](#pre-check-handoff) below.

## Hard constraints (load-bearing — don't drift)

These are not opinions, they are observable behaviors of the Codex binary and Mify gateway today. Every one of them has an error message that will hit you if you get it wrong. Internalize before touching config.

1. **`wire_api` MUST be `"responses"`.** Codex PR #10157 (Feb 2026) removed `wire_api = "chat"` from the codebase. The binary error template hardcodes only `"responses"` as legal. You can verify with `strings /Applications/Codex.app/Contents/Resources/codex | grep wire_api` — you will see `` `wire_api = "chat"` is no longer supported `` as a literal error template. There is no `chat_completions` value either (LLMs sometimes hallucinate that; it doesn't exist in source).

2. **Custom Mify slugs need local model metadata.** Codex only knows official model slugs from its remote catalog. Mify slugs such as `ppio/pa/gpt-5.5`, `xiaomi/mimo-v2.5-pro`, `xiaomi/mimo-v2.5`, `deepseek/deepseek-v4-pro`, `minimax/MiniMax-M3`, `zhipuai/glm-5.2`, `gemini-3.1-pro`, and `gemini-3.5-flash` otherwise fall back to Codex's unknown-model metadata (`context_window = 272000`, `max_context_window = 272000`, effective `258400`). Maintain `~/.codex/model_catalog.local.json` and set `model_catalog_json`, `model_context_window = 1000000`, and `model_auto_compact_token_limit = 850000`. Keep `ppio/pa/gpt-5.5` at `272000`/`258400` because the PPIO relay currently rejects larger prompts; other configured slugs keep 950k effective windows. If the gateway returns `Not supported model`, metadata is still correct; the provider simply does not currently accept that slug.

3. **Codex Desktop model picker is inert for custom providers.** The provider name shows in the picker dropdown but model selection is disabled. **The only way to switch model is editing `~/.codex/config.toml`'s top-level `model = "..."` then Cmd+Q restart.** Don't look for a UI path; `[model_providers.mify].name` is display-only and is kept in sync with the current `model` by `set_codex_model.py` / the `codex-model` zsh function so the user at least sees what's actually running.

4. **macOS GUI apps don't inherit zshrc env.** Codex Desktop launched from Dock/Finder reads `launchd` env, not a login shell. `MIFY_API_KEY` must therefore be injected into launchd's user GUI domain. One-shot: `launchctl setenv MIFY_API_KEY $MIFY_API_KEY`. Persistent across reboot: a LaunchAgent that does it on login (this skill installs that). CLI users don't have this problem — CLI inherits Terminal env.

5. **`requires_openai_auth = true` is required in the Mify provider block.** Without it, Codex Desktop hides the model selector entirely (issue #10867). First Desktop launch prompts "Sign in with OpenAI / Sign in with API key" — user picks API key, types any ≥3 chars, presses Enter. That's a UI-only bypass; real auth uses `env_key = "MIFY_API_KEY"`.

6. **Stale `~/.codex/auth.json` from a prior ChatGPT login will crash Codex Desktop's app-server on CN IPs.** Codex's `codex_login::auth::manager` unconditionally refreshes the cached OpenAI `refresh_token` on every launch — independently of `[model_providers.mify]`. From China, OpenAI's refresh endpoint returns `403 unsupported_country_region_territory`; the app-server dies, reconnects, dies again, and the Desktop UI never becomes interactive (no visible error; it just looks frozen). `install.py`'s pre-flight detects this (auth_mode == "ChatGPT" or presence of `tokens.refresh_token`) and moves the file to `~/.codex/auth.json.openai-bak-<timestamp>`. Evidence trail: logs under `~/Library/Logs/com.openai.codex/**/*.log` contain `target: codex_login::auth::manager` + `Failed to refresh token: 403`.

## Pre-check handoff

**Always run first.** If any of these fail, stop and route the user to the right place:

```bash
# 1. macOS?
[ "$(uname)" = "Darwin" ] || { echo "This skill is macOS-only"; exit 1; }

# 2. Mify credentials installed?
if [ ! -r ~/.config/mify/credentials ]; then
  echo "No Mify token installed."
  echo "Hand off to the mify-model-gateway skill:"
  echo "  1. Ask the user for their sk- key (from their Mify dashboard)"
  echo "  2. Run: printf %s '<KEY>' | python3 ~/.Codex/skills/mify-model-gateway/scripts/install_token.py"
  echo "Then come back to this skill."
  exit 1
fi

# 3. Codex installed?
ls /Applications/Codex.app >/dev/null 2>&1 || which codex >/dev/null 2>&1 || {
  echo "Codex not found. Download: https://openai.com/codex"
  exit 1
}
```

## Workflows

### First-time setup

`scripts/install.py` runs **five phases**, all idempotent — safe to rerun:

1. **Pre-flight** — OS check; if Codex isn't installed, the script opens `https://openai.com/codex` in the user's browser and blocks on `input()` until they come back and confirm the install finished (in non-interactive contexts like Codex / CI it prints instructions and exits instead of hanging); Mify credentials check (hands off to `mify-model-gateway` if missing).
2. **Stale OpenAI auth** — detects `~/.codex/auth.json` from a prior ChatGPT login (see hard constraint #6) and moves it to `auth.json.openai-bak-<timestamp>` so Codex's auth::manager doesn't loop on the CN-blocked refresh endpoint.
3. **Model catalog** — writes `~/.codex/model_catalog.local.json` with a PPIO exception (`ppio/pa/gpt-5.5` = 272k, effective 258400) and 1M metadata for `xiaomi/mimo-v2.5-pro`, `azure_openai/gpt-5.5`, `xiaomi/mimo-v2.5`, `deepseek/deepseek-v4-pro`, `minimax/MiniMax-M3`, `zhipuai/glm-5.2`, `gemini-3.1-pro`, and `gemini-3.5-flash` (effective 950k).
4. **Patch config.toml** — **surgical strip + prepend**, not blind prepend. Reads existing config, removes any conflicting root-level `model`/`model_provider`/`model_reasoning_effort`/context-window keys and any existing `[model_providers.mify]` table (including subtables), then prepends the new Mify snippet including `model_catalog_json`, `model_context_window = 1000000`, and `model_auto_compact_token_limit = 850000`. Every other section (`[marketplaces.*]`, `[plugins.*]`, user tables) is preserved byte-for-byte. The strip logic is in `strip_conflicting_toml()` — see the docstring there for the idempotency proof.
5. **LaunchAgent** — stage plist at `~/.config/mify/` → user Finder-drags to `~/Library/LaunchAgents/` (TCC blocks direct writes) → bootstrap + kickstart + verify `MIFY_API_KEY` injected into `gui/$(id -u)` launchd domain.
6. **zshrc codex-model function** — append between `# >>> codex-mify` / `# <<< codex-mify` markers for clean revert.

```bash
# See what would change, no writes
python3 scripts/install.py --dry-run

# Execute
python3 scripts/install.py --apply

# Pick a different default model
python3 scripts/install.py --apply --default-model xiaomi/mimo-v2.5-pro
```

Two phases **block on `input()`** waiting for user action:

- **Phase 1 (Codex missing):** opens download page, waits for user to return after install. Interactive terminals only — non-TTY stdin (piped, Codex's Bash tool) triggers the fail-fast path with instructions.
- **Phase 4 (LaunchAgent drag):** opens source + destination Finder windows, waits for user to drag the plist. macOS TCC blocks direct writes to `~/Library/LaunchAgents/` from Terminal/Codex without Full Disk Access; Finder's built-in authorization flow is the lower-permission path. If the user says "Full Disk Access is fine with me, just write it directly", grant Terminal.app FDA in System Settings → Privacy & Security → Full Disk Access, then retry.

**Codex note:** `launchctl bootstrap` / `bootout` IPC to launchd's user domain may return `I/O error 5` inside Codex's sandbox. If you hit this, re-run the relevant shell command with `dangerouslyDisableSandbox: true`. Users running `install.py` from Terminal.app directly don't encounter this.


### Context-window catalog maintenance

Codex clamps `model_context_window` to the selected model metadata's `max_context_window`. Unknown custom slugs use fallback metadata (`272000` max, `95%` effective), so simply adding `model_context_window = 1000000` is not enough. Always pair Mify custom slugs with a local catalog:

```toml
model_catalog_json = "/Users/<user>/.codex/model_catalog.local.json"
model_context_window = 1000000
model_auto_compact_token_limit = 850000
```

`scripts/install.py --apply` creates the catalog automatically. `scripts/set_codex_model.py --apply` refreshes it and adds the requested model slug if it is not already in the default list. New Codex processes should report `model_context_window = 258400` for `ppio/pa/gpt-5.5` and `950000` for the other configured slugs; existing Desktop threads may need Cmd+Q/reopen because `model_catalog_json` is startup-only.

### Daily model switch

Two equivalent ways. Prefer the zsh function for interactive users; use the Python script when doing model switches programmatically (e.g., another skill or CI invoking it).

**zsh function** (installed by `install.py`; works in any terminal after `source ~/.zshrc`):

```bash
codex-model                              # no args: show current + candidates
codex-model ppio/pa/gpt-5.5            # GPT-5.5 through PPIO
codex-model xiaomi/mimo-v2.5-pro      # MiMo pro
codex-model xiaomi/mimo-v2.5          # MiMo standard
codex-model deepseek/deepseek-v4-pro  # DeepSeek
codex-model minimax/MiniMax-M3        # MiniMax
codex-model zhipuai/glm-5.2          # GLM
codex-model gemini-3.1-pro    # Gemini Pro
codex-model gemini-3.5-flash  # Gemini Flash
```

The function is a thin sed wrapper — no validation, any `owner/id` slug is accepted. Mify/Codex will reject illegal slugs at call time. This is by design (keeps the function simple and offline-friendly).

**Python script** — same effect, but with `--dry-run`/`--apply`/`--revert` semantics and automatic smoke test:

```bash
python3 scripts/set_codex_model.py --model ppio/pa/gpt-5.5 --dry-run
python3 scripts/set_codex_model.py --model ppio/pa/gpt-5.5 --apply
python3 scripts/set_codex_model.py --revert
```

The script backs up `config.toml` before write, updates top-level `model = "..."`, `[model_providers.mify].name = "..."`, ensures the 1M `model_catalog.local.json`, and preserves the context-window keys, then does a `curl /v1/responses` smoke test. If smoke test fails (non-200), it automatically reverts from the just-created backup. Safer than the zsh function when you can't easily retry.

### Recovery (broken config)

```bash
# Roll back to the most recent auto-backup (created by this skill's scripts)
python3 scripts/set_codex_model.py --revert

# Or roll back to a specific known-good timestamp
ls ~/.codex/config.toml.bak.*
cp ~/.codex/config.toml.bak.YYYYMMDD-HHMMSS ~/.codex/config.toml

# Complete nuclear uninstall
python3 scripts/install.py --revert
```

## Verification

Run after `install.py --apply` to confirm everything is wired up:

```bash
# 1. CLI path — should self-report provider: mify and the configured model
[ -r ~/.config/mify/credentials ] && source ~/.config/mify/credentials
codex exec --skip-git-repo-check --sandbox read-only \
  "Reply with exactly one word: working"

# 2. GUI env — should show sk-xxxxx (this is what Desktop reads at launch)
launchctl getenv MIFY_API_KEY | cut -c1-8

# 3. LaunchAgent loaded?
launchctl list | grep -i mify
```

For Desktop: **Cmd+Q to fully quit, then reopen.** Closing the window is not enough — Desktop reads `config.toml` on launch only.

## Troubleshooting matrix

| Symptom | Root cause | Fix |
|---|---|---|
| `wire_api = "chat" is no longer supported` | Config has wrong value (LLMs often recommend this) | Set `wire_api = "responses"` |
| `Not supported model: gpt-5.x` (Mify 400) | Top-level `model` is bare id — no owner prefix | Use an owner-qualified slug such as `ppio/pa/gpt-5.5` or a supported `azure_openai/*` slug |
| `Not supported model: <slug>` after catalog setup | Local Codex metadata is configured, but the Mify gateway/provider does not currently accept that slug | Try another configured slug; do not remove `model_catalog_json` just because gateway support is missing |
| Desktop: `Couldn't update model settings` | Usually wire_api value illegal, or malformed TOML | Check `plutil -lint` equivalent (Codex does its own TOML validation on startup and prints errors to `~/Library/Logs/`) |
| Desktop model picker completely hidden | `requires_openai_auth` missing or false | Set `requires_openai_auth = true` under `[model_providers.mify]` |
| Desktop: 401 after Mac restart | GUI env lost `MIFY_API_KEY` | `launchctl getenv MIFY_API_KEY` — if empty, LaunchAgent didn't fire; `launchctl kickstart -k "gui/$(id -u)/com.xiaomi.mify.env"` |
| Desktop opens but UI never becomes interactive (frozen / blank main area after dismissing the login screen) | Stale `~/.codex/auth.json` from prior ChatGPT login; auth::manager loops on 403 from OpenAI refresh endpoint (CN geoblock). Confirm with `grep "Failed to refresh token.*403" ~/Library/Logs/com.openai.codex/**/*.log` | `mv ~/.codex/auth.json ~/.codex/auth.json.openai-bak-$(date +%Y%m%d-%H%M%S)` then Cmd+Q and reopen. `install.py --apply` does this automatically in its phase 2. |
| `launchctl bootstrap` returns `I/O error 5` when running `install.py` from Codex | Codex sandbox blocks launchd IPC | Retry the bootstrap command with `dangerouslyDisableSandbox: true`, or run `install.py` from Terminal.app directly. |
| Config edits appear but Codex keeps parsing the old one (duplicate `model` key) | Prior skill version did a blind prepend and produced duplicate root keys. Fixed in current `install.py`'s surgical-strip logic. | Re-run `install.py --apply` — it will strip conflicts on any existing config and rewrite cleanly. |
| Config edit had no effect | Desktop still running old in-memory config | Cmd+Q (not close window) then reopen |
| `codex-model: cannot find top-level 'model = "..."'` | Config missing top-level model | Run `install.py --apply` to seed it |

## References

- `references/codex_setup_guide.md` — long-form setup guide (mirror of the team Feishu doc at `https://feishu.cn/wiki/HZILwO53HiRMxZk2wSTcULSPnDh`). Has architecture diagram, every pitfall encountered during the original configuration session (including the auth.json 403 loop from constraint #6), and rationale for each design decision. Load when you need deeper context on WHY a particular constraint exists.
- Team pitch / skill intro doc (what it does, why, evaluation results): `https://mi.feishu.cn/wiki/I8GHwek6MiJWglkv1MicVhU7nxc` — updated separately; keep in sync with SKILL.md's top-level capabilities list when the feature set changes.
- `scripts/install.py` — first-time setup orchestrator
- `scripts/set_codex_model.py` — daily model switch with smoke-test + auto-revert
- External: [openai/codex Issue #10867](https://github.com/openai/codex/issues/10867) (Desktop picker workaround)
- External: [openai/codex Discussion #7782](https://github.com/openai/codex/discussions/7782) (wire_api chat deprecation)
