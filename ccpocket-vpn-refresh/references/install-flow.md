# install.sh output reference

A quick cheat sheet for reading `install.sh` output, to help Claude surface the right next-step to the user.

## Exit codes

| Code | Meaning | What to tell the user |
|------|---------|-----------------------|
| 0    | Install succeeded | "All set — bridge smoke-tested OK. Run refresh to start it." |
| 2    | Multiple VPN interfaces detected, couldn't auto-pick | Show the printed candidates and ask user which one to use; re-run with `--interface utunX` |
| 3    | Node.js not installed / version too old | User must install Node.js 18+ — installer cannot proceed |
| 4    | No VPN interface found (or override interface has no IP) | User needs to connect 小米 VPN first |
| Other| Unexpected | Show full stderr to user, check `references/troubleshooting.md` |

## Typical success output

```
[HH:MM:SS] INFO  ccpocket-vpn-refresh installer
────────────────────────────────────────────────────
[HH:MM:SS] OK    Node.js v20.X.X detected.
[HH:MM:SS] OK    npx detected.
[HH:MM:SS] OK    State dir: /Users/.../.ccpocket-helper
[HH:MM:SS] INFO  Auto-detecting VPN interfaces…
[HH:MM:SS] OK    Picked single candidate: utun4 (10.X.X.X)
[HH:MM:SS] OK    Generated BRIDGE_API_KEY: abc123…4def
[HH:MM:SS] OK    Wrote config: /Users/.../.ccpocket-helper/config.json
[HH:MM:SS] INFO  Running smoke test: start bridge → probe /version → stop.
[HH:MM:SS] OK    Smoke test passed.
────────────────────────────────────────────────────
[HH:MM:SS] OK    Install complete.
```

## Ambiguous VPN case (exit 2)

```
[HH:MM:SS] WARN  Multiple VPN interfaces found — cannot auto-pick.
  - utun4 (10.225.X.X)
  - utun7 (100.X.X.X)   ← would have been filtered if Tailscale; double-check
[HH:MM:SS] ERROR Re-run with --interface <name>, e.g. --interface utun4
```

Claude should parse the bullet list, show it to the user, and ask which to pick.

## After install completes

Point the user to their next action:

```
bash <skill-dir>/scripts/refresh.sh
```

Or in Claude: "刷新 bridge" / "check ccpocket".
