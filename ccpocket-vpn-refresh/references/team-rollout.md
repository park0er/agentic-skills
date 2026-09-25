# Team rollout guide

How to distribute this skill to teammates who want the same CC Pocket + corporate VPN setup.

## Package once, ship to everyone

From the skill directory on your machine:

```bash
cd ~/ccpocket-vpn-refresh
zip -r ccpocket-vpn-refresh.zip . \
  -x '*.DS_Store' '*/node_modules/*' '*/__pycache__/*' \
     '*/\.git/*' '*-workspace/*' 'evals/runs/*'
```

This produces a `ccpocket-vpn-refresh.zip` suitable for Airdrop / 飞书云盘 / Slack / email.

## Each teammate's install (3 steps)

1. **Unzip** to a stable location. For Claude Code users, `~/.claude/skills/` is ideal because Claude Code auto-discovers skills there:

   ```bash
   mkdir -p ~/.claude/skills
   unzip -o ccpocket-vpn-refresh.zip -d ~/.claude/skills/ccpocket-vpn-refresh
   ```

   For non–Claude Code users (e.g. Codex CLI only), any stable path works — common choice:

   ```bash
   unzip -o ccpocket-vpn-refresh.zip -d ~/tools/ccpocket-vpn-refresh
   ```

2. **Make sure 小米 VPN is connected.** The installer auto-detects the VPN interface, but the VPN must be up or detection fails with a clear error.

3. **Trigger the first run.** Either ask Claude "check ccpocket bridge" (Claude Code users), or run the script directly:

   ```bash
   bash ~/.claude/skills/ccpocket-vpn-refresh/scripts/refresh.sh
   # or
   bash ~/tools/ccpocket-vpn-refresh/scripts/refresh.sh
   ```

   On first invocation, `install.sh` runs automatically, sets up `~/.ccpocket-helper/`, generates a random `BRIDGE_API_KEY` for that user, and launches the bridge. Each user gets their own isolated state dir — no cross-contamination.

## What doesn't transfer across machines

The `~/.ccpocket-helper/` directory is **machine-local and never ships with the zip**. This is by design:

- `config.json` contains the user's VPN interface name (may differ per machine)
- `config.json` contains that user's random BRIDGE_API_KEY
- `bridge.log` and `bridge.pid` are runtime artifacts
- `state.json` tracks the last VPN IP which changes per reconnect

So the zip contains only the *logic* (scripts + SKILL.md + references). The *state* is generated freshly per user.

## Updating

When you improve the skill and want to push a new version:

1. Re-zip on your machine
2. Teammates unzip over their existing directory:
   ```bash
   unzip -o ccpocket-vpn-refresh.zip -d ~/.claude/skills/ccpocket-vpn-refresh
   ```
3. No need to re-run install — their `~/.ccpocket-helper/` is preserved. Next refresh will use the new script logic.

The one exception: if `defaults/config.json.template` gets new required fields, add a migration path inside `install.sh` before pushing.

## Codex CLI users

Codex doesn't have a "skills" concept. Teammates who primarily use Codex should:

1. Unzip somewhere permanent (e.g. `~/tools/ccpocket-vpn-refresh/`)
2. Add an alias to their shell rc:
   ```bash
   echo 'alias ccp-refresh="~/tools/ccpocket-vpn-refresh/scripts/refresh.sh"' >> ~/.zshrc
   ```
3. After each 小米 VPN reconnect, run `ccp-refresh` in their terminal.

Optionally, they can add the core logic to their `~/.codex/AGENTS.md` so Codex auto-invokes the script:

```markdown
## ccpocket bridge management

Whenever the user mentions CC Pocket connection problems, VPN reconnects, or
"刷新 bridge", run `~/tools/ccpocket-vpn-refresh/scripts/refresh.sh` and report
the output to the user.
```

## Minimum system requirements

- macOS (tested on Apple Silicon; Intel should work but is not regularly tested)
- Node.js 18+ (ideally 20+ LTS)
- Bash 3.2+ (macOS default — no modern bash needed)
- ~2 MB disk for the skill itself, ~50 MB for the `@ccpocket/bridge` npx cache
