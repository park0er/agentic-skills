---
name: paseo-import-doctor
description: "Diagnose and fix Paseo desktop app import-history issues. Manage Codex/Claude session import records stored under ~/.paseo/agents/. Use when: (1) user cannot re-import a previously imported Codex/Claude session into Paseo, (2) user wants to list, inspect, or clean up Paseo import records, (3) user mentions 'paseo import', 'can't re-import session', 'paseo import history', 'paseo 已导入', 'paseo 导不进去', 'paseo 重新导入', '清掉 paseo import 记录'."
---

# Paseo Import Doctor

## How Paseo Tracks Imports

Paseo daemon stores each imported session as a JSON file:

```
~/.paseo/agents/<workspace-slug>/<uuid>.json
```

Each JSON contains:
- `persistence.sessionId` — original Codex/Claude session ID
- `lastStatus` — `idle`, `closed`, `error`
- `archivedAt` — ISO timestamp if session was closed in Paseo UI

When `listImportablePersistedAgents` runs, it skips sessions that already have an agent record. This is why "closed" sessions block re-import — the record still exists.

## Quick Diagnosis

Run the management script to see current state:

```bash
python3 scripts/paseo_agents.py list
```

Filter by workspace or status:

```bash
python3 scripts/paseo_agents.py list --workspace MulticaApp
python3 scripts/paseo_agents.py list --status closed
```

## Deep Diagnosis

Cross-reference Codex DB vs Paseo records + check relay connectivity:

```bash
python3 scripts/paseo_agents.py diag
python3 scripts/paseo_agents.py diag --show-all  # also list all 200+ importable sessions
```

Reports:
1. Paseo daemon running status
2. Blocked vs importable session counts (queries `~/.codex/state_5.sqlite`)
3. Relay connection health (from `~/.paseo/daemon.log`)
4. Per-workspace breakdown

Use `diag` when `list` alone doesn't explain why import fails (e.g., relay issues, provider-side filtering).

## Fix: Clean Closed Import Records

To unblock re-import, remove the stale agent records:

```bash
# Preview what will be deleted
python3 scripts/paseo_agents.py clean --dry-run

# Execute cleanup (all closed/archived)
python3 scripts/paseo_agents.py clean

# Clean only a specific workspace
python3 scripts/paseo_agents.py clean --workspace MulticaApp

# Also clean error-status records
python3 scripts/paseo_agents.py clean --status error
```

After cleanup, **restart Paseo** for changes to take effect:

```bash
python3 scripts/paseo_agents.py restart
```

This kills the daemon + app and reopens Paseo, which reloads import records from disk.

## Inspect a Specific Session

```bash
python3 scripts/paseo_agents.py show 019e8d3e
```

Uses session ID prefix matching.

## Nuclear Option: Reset All Imports

```bash
python3 scripts/paseo_agents.py reset --dry-run
python3 scripts/paseo_agents.py reset
```

Requires interactive confirmation. Removes ALL agent import records.

## Mobile / Relay Troubleshooting

When import works from Mac desktop but fails from phone:

1. Run `diag` to check relay status — look for `relay_data_disconnected` entries
2. If relay is unstable: restart Paseo on Mac (`kill -9` the daemon, reopen app)
3. On phone: fully close and reopen Paseo app to force fresh connection
4. Import from Mac desktop as fallback (bypasses relay entirely)

The relay connects phone → `relay.paseo.sh` → Mac daemon. VPN or network instability can break this chain.

## Safety Notes

- Deleting agent JSON files does NOT affect the original Codex/Claude sessions — those remain intact on the Codex side.
- Always `--dry-run` first before any destructive operation.
- Restart Paseo after cleaning records for changes to take effect.
- The script reads from `~/.paseo/agents/` — the daemon must not be actively writing during cleanup (stop Paseo first if concerned).
