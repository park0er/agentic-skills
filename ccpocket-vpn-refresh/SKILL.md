---
name: ccpocket-vpn-refresh
description: Keep the @ccpocket/bridge daemon healthy across 小米 VPN (or any utun-based corporate VPN) reconnects. Detect VPN IP drift, restart the bridge with the current `BRIDGE_PUBLIC_WS_URL`, and handle first-time setup. Also detect a "foreign bridge" on port 8765 with an unknown key and guide adoption / sync / replace flows. Use when the user mentions CC Pocket, ccpocket, @ccpocket/bridge, mobile bridge, bridge in Codex / Claude mobile context, CC pocket 连不上, 刷新 bridge, 重启 bridge, VPN 重连, VPN 断了 bridge, ccpocket 掉线, iPhone 连不上 Mac session, refresh ccpocket, ccpocket reconnecting, invalid token, or 手机配对不上.
---

# CC Pocket VPN Refresh

Manages the lifecycle of the `@ccpocket/bridge` Node daemon on a Mac connected to a corporate VPN (tested against 小米 VPN / utun interfaces). The core problems it solves:

1. **VPN IP drift**: every VPN reconnect may reassign the Mac's internal IP; the bridge's `BRIDGE_PUBLIC_WS_URL` goes stale and the iPhone app can no longer reach the Mac.
2. **API key mismatch / "reconnecting" loop**: if some other launcher started a bridge on port 8765 with a random API key (common: eval harnesses, manual test runs, scripts that call `npx @ccpocket/bridge@latest`), the iPhone's stored token won't match the live bridge's `BRIDGE_API_KEY`, and it stays stuck in "reconnecting" forever. The skill detects this *before* touching anything and offers adoption/sync/replace choices.

## Core workflow

When invoked, follow this decision tree **in order**:

### Step 1 — Check if this is a first-run

```bash
test -f "$HOME/.ccpocket-helper/config.json"
```

If the file does **not** exist, run the install wizard:

```bash
bash "<skill-dir>/scripts/install.sh"
```

`install.sh` now does port discovery **before** generating any key. If port 8765 is already held by a running ccpocket-bridge, it enters the adoption flow (see Step 1.5). After a successful install, jump to Step 2.

### Step 1.5 — Adoption flow (when install finds an existing bridge)

The installer accepts `--adopt-mode sync|keep|replace`. Default is `sync`.

- **sync** (recommended, default): inherit the live bridge's `BRIDGE_API_KEY` into our `config.json`. Phone pairing is preserved across any future helper-managed restart. Non-destructive.
- **keep**: only track the foreign PID; leave our config's own random key alone. ⚠ A future `bridge-ctl.sh restart` will start a bridge with a different key and break phone pairing. Avoid unless you specifically want this.
- **replace**: kill the foreign bridge, start a fresh helper-managed one. Requires `--force-kill` to confirm. User **will** need to unpair and re-scan from the iPhone.

Tell the user what was detected and which mode was applied. If `sync` failed because env vars couldn't be read (sandbox), the installer falls back to `keep` and prints a warning — surface that to the user.

### Step 2 — Run the refresh logic

```bash
bash "<skill-dir>/scripts/refresh.sh"
```

`refresh.sh` now classifies what's on port 8765 before deciding:

| `CLASSIFY_KIND` | `ip_state` | Action | User next step |
|-----------------|------------|--------|----------------|
| managed         | same       | no-op  | keep using CC Pocket |
| managed         | changed    | restart bridge (same key → **pairing preserved**) | nothing; phone reconnects with new URL |
| managed         | first_run  | record last_vpn_ip in state | nothing |
| idle            | same       | start bridge | iPhone may auto-reconnect |
| idle            | changed    | start bridge; print fresh QR | re-scan QR |
| idle            | first_run  | start bridge; print initial QR | scan QR once |
| **foreign**     | any        | **REFUSE to restart**; exit 7 | run `bridge-ctl.sh doctor` |
| stranger        | any        | error out (non-bridge process holding port) | free the port |

### Step 3 — When the phone still shows "reconnecting"

This means TCP + WebSocket upgrade work but auth fails. Run:

```bash
bash "<skill-dir>/scripts/bridge-ctl.sh doctor
```

`doctor` actively audits:
- `[W1]` API key drift between config and the running process
- `[W2]` Bridge started by a foreign launcher (different `$HOME`)
- `[W3]` `BRIDGE_PUBLIC_WS_URL` disagrees with current VPN IP
- `[E3]` `Client rejected: invalid token` flood in bridge.log — the precise signal for "phone's stored token ≠ live bridge's key"

Each finding comes with a specific suggested remedy (`sync-from-live`, `refresh`, or `reset-pair`). Relay the summary to the user and help them pick.

### Step 4 — Report the outcome

Pass through the log blocks from the scripts. If a QR was re-rendered, it's already visible in the terminal — don't regenerate. If doctor flagged `[E3]`, tell the user they'll need to choose between `sync-from-live` (preserve phone's current pairing by inheriting the live bridge's key into our config — only works if `ps eww` can read the env) and `reset-pair` (clean restart; user unpairs in CC Pocket app and re-scans the new QR).

## Script reference

All scripts live under `<skill-dir>/scripts/`:

| Script | Purpose |
|--------|---------|
| `install.sh` | First-run wizard. Does port discovery before generating keys. Supports `--adopt-mode` for the foreign-bridge case. |
| `uninstall.sh` | Removes `~/.ccpocket-helper/`, kills running bridge. |
| `refresh.sh` | Main VPN-drift entry. Classifies port status, refuses to restart on `foreign`. |
| `bridge-ctl.sh` | Lifecycle: `start \| stop \| restart \| status \| logs \| qr \| qr-image \| doctor \| sync-from-live \| reset-pair` |
| `lib/detect-vpn.sh` | Lists utun interfaces carrying private IPv4 (excluding Tailscale's 100.64/10). |
| `lib/discover.sh` | Port discovery + classify idle/managed/foreign/stranger. |
| `lib/state.sh` | Atomic read/write of `config.json` and `state.json`, plus adoption metadata helpers. |
| `lib/log.sh` | Colored, timestamped log helpers. |

## Subcommand cheat-sheet

```bash
bridge-ctl.sh status          # human-readable state (uses port discovery)
bridge-ctl.sh doctor          # active audit — RUN THIS WHEN PHONE SHOWS "reconnecting"
bridge-ctl.sh sync-from-live  # inherit live bridge's key into config (non-destructive)
bridge-ctl.sh reset-pair      # destructive: restart with config's key + print new QR
bridge-ctl.sh restart         # stop + start (uses config's current key)
bridge-ctl.sh qr              # reprint last ASCII QR from the log
bridge-ctl.sh qr-image        # render QR as PNG (~/.ccpocket-helper/qr.png) and open it
bridge-ctl.sh logs            # tail -f bridge.log
```

## CLI usage (works without Claude)

```bash
~/ccpocket-vpn-refresh/scripts/refresh.sh           # everyday VPN refresh
~/ccpocket-vpn-refresh/scripts/bridge-ctl.sh doctor # when the phone is stuck
~/ccpocket-vpn-refresh/scripts/bridge-ctl.sh status # quick check
```

Suggest adding an alias when they use it often:

```bash
alias ccp='~/ccpocket-vpn-refresh/scripts/bridge-ctl.sh'
```

## Dependencies

- **Node.js 18+** (bridge runs on Node; `install.sh` refuses to continue without it)
- Bridge package fetched by `npx @ccpocket/bridge@latest` — first run downloads, cached afterwards
- QR is re-read from the bridge's own log output

No Homebrew dependencies.

## State files

```
~/.ccpocket-helper/
├── config.json          # vpn_interface, bridge_port, bridge_api_key, paths
├── state.json           # last_vpn_ip, last_bridge_pid, last_started_at,
│                        # plus adoption metadata when applicable:
│                        #   adoption_kind, adoption_key_synced,
│                        #   adoption_launcher_home, adopted_at
├── bridge.log           # Rolling log from nohup'd bridge process
└── bridge.pid           # PID file for cross-invocation state
```

`config.json` is machine-specific and generated by `install.sh` — **do not ship it with the skill**.

## Team distribution

See `references/team-rollout.md`. Package as `.zip`; teammates unzip into `~/.claude/skills/` (Claude Code) or any path (CLI-only). The first invocation auto-runs `install.sh`.

## When NOT to trigger

- ChatGPT / Codex subscription questions (not about the bridge) → ignore.
- Tailscale-specific questions — different flow.
- General "Mac doesn't have internet" → out of scope.
- For quick "is my bridge alive?" probes before install, raw tools are lighter: `pgrep -lf ccpocket-bridge`, `lsof -iTCP:8765`, `curl -s http://127.0.0.1:8765/version`. Use `bridge-ctl.sh status` once configured.

## What this skill is actually optimized for

1. 小米 VPN with drifting internal IPs (observed: 10.225.x.y).
2. `@ccpocket/bridge` connecting CC Pocket iPhone ↔ Claude Code / Codex on Mac.
3. Keeping the iPhone paired across: VPN reconnects, helper restarts, and foreign bridges that clobber port 8765 with random keys.

The most important thing the new version does that the old one didn't: **it never generates a random `BRIDGE_API_KEY` if there's already a live bridge on port 8765.** That was the root cause of the "everything was fine, now the phone is stuck reconnecting" class of bug.
