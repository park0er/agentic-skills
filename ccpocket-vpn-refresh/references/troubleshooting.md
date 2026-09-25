# Troubleshooting

## Install fails with "No utun interface with a private IP found"

Meaning: the installer couldn't detect a VPN interface.

Fixes:
1. Connect to your corporate VPN (小米 VPN) first, then re-run install.
2. Verify the VPN is up: `ifconfig | grep -A 1 "^utun" | grep "inet "` — you should see a 10.x.x.x or 172.16-31.x.x address on one of the utun interfaces.
3. If you're sure a VPN is up but detection fails, pass `--interface` manually to the installer: `bash scripts/install.sh --interface utun5`.

## Install fails with "Multiple VPN interfaces found" (exit 2)

Meaning: you have more than one utun interface carrying private IPv4 — for example both 小米 VPN and a WireGuard profile. The installer refuses to guess.

Fix: look at the printed list, pick the right one, and re-run with `--interface`:

```bash
bash scripts/install.sh --interface utun4
```

## Smoke test warns "bridge did not respond on port 8765"

Meaning: a bridge was supposed to come up on the port but curl couldn't reach it within 6 seconds.

Common causes:
- **Port already in use.** Another copy of the bridge is already running. Run `bash scripts/bridge-ctl.sh status` to check. If there's an orphan, run `bash scripts/uninstall.sh` to forcibly kill it, then re-install.
- **Slow npx cold-start.** If this is the first time `@ccpocket/bridge` is fetched, download can exceed 6 seconds. Pre-warm with `npx @ccpocket/bridge@latest --version` once, then re-run install.
- **Node.js permission issue.** Check `~/.ccpocket-helper/bridge.log` for the actual error.

## Refresh says "Bridge not running" but iPhone app shows it was running

The bridge is running, but was started outside this skill (for example, you ran `npx @ccpocket/bridge` directly in a terminal). This skill only tracks bridges started via its `bridge-ctl.sh start`.

Fix:
```bash
# Stop the externally-started bridge (in its own terminal: Ctrl+C, or):
pkill -f ccpocket-bridge
# Now let the skill manage it:
bash scripts/refresh.sh
```

## iPhone shows "Tailscale" as the connection label even though I don't use Tailscale

That's cosmetic. The bridge (not this skill) labels any `utun*` interface "Tailscale" in its UI. See `internal/auth/codex/` in the bridge source. Nothing is broken — it's just mislabeled.

## VPN IP changes every few hours

Known behavior for 小米 VPN (and most corporate VPNs). That's why this skill exists. Just re-run refresh after each VPN reconnect:

```bash
bash scripts/refresh.sh
```

Or in Claude: "刷新 bridge" / "VPN 重连了".

## How do I know whether I need to re-scan the QR on iPhone?

Refresh tells you. The log lines "Re-scan the QR above from the CC Pocket iPhone app" appear only when the IP changed or a brand-new bridge was started. If refresh says "Bridge healthy and IP unchanged", your iPhone pairing from last time is still valid.

## Bridge won't start: "EADDRINUSE 0.0.0.0:8765"

Another process is already bound to port 8765. Either:
- It's the skill's own previous bridge that didn't shut down cleanly — fix with `bash scripts/bridge-ctl.sh stop` (then `start`).
- It's a bridge you started manually outside the skill — kill it: `pkill -f ccpocket-bridge`.
- It's something unrelated — move the skill's bridge to a new port: edit `~/.ccpocket-helper/config.json`, change `bridge_port`, then `bash scripts/bridge-ctl.sh restart`.

## I want to see the bridge's live logs

```bash
bash scripts/bridge-ctl.sh logs
```

Or directly: `tail -f ~/.ccpocket-helper/bridge.log`.

## I want to completely reset and start over

```bash
bash scripts/uninstall.sh
bash scripts/install.sh
```
