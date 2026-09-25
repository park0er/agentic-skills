#!/usr/bin/env bash
# Load Claude Code gateway environment for helper-managed @ccpocket/bridge.
#
# The bridge process only sees environment variables from its launcher. Claude
# Code can keep gateway settings in ~/.claude/settings.json, so load the safe
# allowlist here before starting the detached bridge.

load_claude_env() {
  local config_dir settings fallback_settings
  config_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  settings="$config_dir/settings.json"
  fallback_settings="$HOME/.claude/settings.json"

  if [ ! -f "$settings" ] && [ "$settings" != "$fallback_settings" ]; then
    settings="$fallback_settings"
  fi

  [ -f "$settings" ] || return 0
  command -v node >/dev/null 2>&1 || return 0

  local exports_file
  exports_file=$(mktemp "${TMPDIR:-/tmp}/ccpocket-claude-env.XXXXXX") || return 0

  if ! SETTINGS_PATH="$settings" node > "$exports_file" <<'NODE'
const fs = require("fs");

const settingsPath = process.env.SETTINGS_PATH;
let parsed;
try {
  parsed = JSON.parse(fs.readFileSync(settingsPath, "utf8"));
} catch (error) {
  process.exit(0);
}

const env = parsed && typeof parsed === "object" && parsed.env && typeof parsed.env === "object"
  ? parsed.env
  : {};

const exact = new Set([
  "ANTHROPIC_API_KEY",
  "ANTHROPIC_AUTH_TOKEN",
  "ANTHROPIC_BASE_URL",
  "ANTHROPIC_DEFAULT_HAIKU_MODEL",
  "ANTHROPIC_DEFAULT_SONNET_MODEL",
  "ANTHROPIC_DEFAULT_OPUS_MODEL",
]);

function allowedKey(key) {
  return exact.has(key) || key.startsWith("CLAUDE_CODE_");
}

function shellQuote(value) {
  return "'" + String(value).replace(/'/g, "'\\''") + "'";
}

for (const key of Object.keys(env).sort()) {
  if (!allowedKey(key) || !/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) continue;
  const value = env[key];
  if (!["string", "number", "boolean"].includes(typeof value)) continue;
  if (process.env[key] != null && process.env[key] !== "") continue;
  console.log(`export ${key}=${shellQuote(value)}`);
}
NODE
  then
    rm -f "$exports_file"
    return 0
  fi

  if [ -s "$exports_file" ]; then
    eval "$(cat "$exports_file")"
  fi
  rm -f "$exports_file"
}
