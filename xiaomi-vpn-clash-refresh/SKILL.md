---
name: xiaomi-vpn-clash-refresh
description: Repair, install, verify, or remove automatic Clash Verge recovery after Xiaomi corporate VPN reconnects on macOS. Use for internal domains that fail only through Clash after VPN reconnects, utun interface drift, company DNS binding, or requests to make the VPN plus Clash split-routing fix persistent. Do not use for general VPN setup or ordinary Clash rules unrelated to Xiaomi VPN.
---

# Xiaomi VPN + Clash automatic recovery

Use this skill only after confirming the user wants to manage the local Xiaomi
VPN/Clash integration. It never connects or disconnects the corporate VPN.

This is deliberately separate from the general `clash-verge` skill:

- `clash-verge`: subscriptions, broad rules, ordinary DNS policy, and office
  networking.
- this skill: the user's home-network arrangement where Xiaomi VPN and Clash
  must coexist, plus its local recovery and background watcher.

## Model

The changing value is the active `utunN` interface chosen by macOS for the
corporate resolver. Two Clash settings must track it:

1. corporate DNS entries using `resolver#utunN`;
2. the `type: direct` outbound used by intranet rules, with
   `interface-name: utunN`.

The domain rules, Fake-IP exclusions, private-route exclusions, and external
proxy selection are not rewritten by this skill.

## Known domain boundary for this Mac

This is a user-confirmed routing scope, not a guess:

- **Company DNS and company-VPN direct outbound**: `mioffice.cn`,
  `xiaomi.srv`, `xiaomi.com`, `xiaomi.net`, `mi.com`, `olap.srv`,
  `mi-dun.com`, and `mitvos.com`.
- **Public DNS through Clash and normal proxy routing**: `apple-cloudkit.com`,
  `icloud.com`, `icloud-content.com`, `multica.ai`, and
  `typeless-static.com`, plus all other domains.

The public DNS resolver itself must use the existing proxy path. This avoids
company-VPN system DNS returning a wrong public address, which can present as
an unrelated TLS certificate. Verify both a company host and a public host
after changes.

## Safety and workflow

1. Read the active profile script and runtime config. Confirm the intranet
   rules and a company direct outbound already exist; this skill does not
   invent company domain suffixes.
2. With the VPN connected, verify the system route to the company resolver:
   `route -n get <company-dns>`. It must report a `utunN` interface.
3. Verify the same intranet host both direct and through the Clash HTTP proxy.
   Do not install automation until the manual binding works.
4. Explain that installation creates a per-user LaunchAgent which polls only
   the route to the company DNS every five seconds. It edits only the two
   bindings above, reloads Mihomo through its local Unix-socket API, then
   flushes DNS and Fake-IP cache.
5. Back up the profile script before installing. Use `scripts/install.sh` only
   with the exact active profile-script path. It creates the backup and prints
   its location. The mutable backups live only in the local recovery vault,
   never inside the distributed skill package.
6. Test the proxy path after installation. If a profile refresh later replaces
   the runtime config, the watcher reapplies the current interface on its next
   check.

## Commands

Run these bundled scripts with absolute paths:

- `scripts/install.sh --profile-script <active-script.js>` — install the
  watcher after explicit approval.
- `scripts/status.sh` — report the watcher state and current tracked tunnel.
- `scripts/manage.sh start|stop|restart|set-interval <seconds>` — manage the
  LaunchAgent and its polling interval.
- `scripts/restore.sh --list` — list local recovery backups.
- `scripts/restore.sh --latest --yes` — stop the watcher and restore the most
  recent pre-home-VPN profile backup. It saves the pre-restore current script
  into the same local recovery vault before changing anything.
- `scripts/uninstall.sh` — remove the watcher only after explicit approval.

## Repair

If internal domains stop working after reconnect:

1. Run `status.sh`.
2. Compare the tracked interface with `route -n get <company-dns>`.
3. If Mihomo is not running, start Clash Verge; the watcher exits harmlessly
   until its local socket is available.
4. If the interfaces match but proxy traffic fails, diagnose DNS and rules;
   do not blindly reinstall.
5. To undo the integration, run `restore.sh --latest --yes`, then reactivate
   the profile in Clash Verge. This restores the prior office-oriented script;
   it does not erase the home-VPN backups.

## Boundaries

- Do not store VPN credentials, inspect company content, or alter VPN policy.
- Do not use a guessed `utun` number. Always derive it from macOS routing.
- Do not modify remote subscriptions directly. Persistent profile changes stay
  in the local extend script; runtime changes are intentionally regenerated.
