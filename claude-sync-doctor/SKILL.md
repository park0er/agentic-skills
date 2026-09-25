---
name: claude-sync-doctor
description: Diagnose, repair, and hand off iCloud symlink sync for Claude Code and Claude Desktop across multiple Macs. Use when the user asks to check, repair, doctor, audit, automate, switch computers, hand off, sync before leaving a Mac, receive sync on a new Mac, or fix syncing of Claude sessions, ~/.claude, ~/.claude.json, Claude-3p desktop config, plugins, skills, hooks, or iCloud-backed symlinks.
---

# Claude Sync Doctor

Use the bundled script for deterministic checks and repairs:

```bash
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py check
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py handoff
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py icloud-check
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py deep-check
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py desktop-check
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py desktop-repair --dry-run
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py repair --safe --dry-run
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py repair --safe --apply
```

## Rules

- Always run `check` before `repair`.
- Default to `--dry-run`; use `--apply` only after reading the report.
- Do not use `--force` unless the user explicitly accepts repairing while Claude/Claude Desktop are running.
- For file entries, Doctor can repair broken symlinks caused by atomic replace.
- For directory entries, Doctor reports drift and can recreate missing/wrong symlinks, but it does not automatically merge real directories into iCloud unless explicitly extended later.
- `~/.claude.json` is atomic-replaced by Claude Code and must be monitored.
- `claude_desktop_config.json` may contain API keys; reports must not print file contents.
- Claude Desktop filters visible Code sessions by the current `ownerAccountId`; Doctor must repair metadata visibility by copying valid synced `claude-code-sessions/*/*/local_*.json` records into the current owner group when needed.
- Do not sync or repair Chromium runtime stores (`Local Storage`, `Session Storage`, `IndexedDB`) for session visibility. Treat them as local caches.
- Default manifest is the recommended hybrid topology: `~/.claude` as a parent-directory symlink plus external single-file symlinks.
- If using file-level symlinks inside `~/.claude`, pass `--manifest ~/.claude/skills/claude-sync-doctor/references/architecture_a_manifest.json`.

## Handoff Workflow

Use this when the user is leaving one Mac or arriving at another Mac after the first-time migration has already been completed.

1. Run an interactive handoff check:

   ```bash
   python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py handoff
   ```

2. If the user says they are ready to close/hand off the machine and accepts repairing while Claude/Claude Desktop may still be running, run:

   ```bash
   python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py handoff --yes --force
   ```

3. Treat `HANDOFF_READY` plus `desktop orphan count: 0`, `desktop visible missing count: 0`, `iCloud current pending count: 0`, and `iCloud placeholder count: 0` as the machine-level success signal.

4. If the command prints `HANDOFF_NOT_READY`, inspect the remaining entries. Do not switch machines until the remaining entries are understood.

5. The handoff flow checks iCloud upload/apply status for the current `ClaudeSync` root. Pending entries under `/.Trash/ClaudeSync ...` are reported as `iCloud trash pending count` but do not block Claude handoff unless the user explicitly wants whole-drive iCloud idle.

Practical rhythm across two Macs:

- Leaving Mac A: run `handoff --yes --force`; do not leave until it prints `HANDOFF_READY` with `iCloud current pending count: 0` and `iCloud placeholder count: 0`.
- Arriving on Mac B: wait for iCloud to finish downloading `ClaudeSync`, then run `handoff --yes --force` and require the same ready counters.
- Do not use the same Claude session concurrently on both Macs.
- Before Mac B has gone through the first-time migration/symlink setup, use the saved Mac B execution plan and migration scripts; Doctor does not merge large real local directories into iCloud by itself.

## Diagnostic Workflow

1. Inspect:

   ```bash
   python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py check
   ```

2. If issues exist, dry-run safe repair:

   ```bash
   python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py repair --safe --dry-run
   ```

3. Ask the user to quit Claude Desktop / Claude Code if the repair would relink files.

4. Apply:

   ```bash
   python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py repair --safe --apply --update-state
   ```

5. Verify:

   ```bash
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py deep-check
```

If Claude Desktop can resume from CLI data but does not show synced sessions in the sidebar, run:

```bash
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py desktop-check
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py desktop-repair --dry-run
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py desktop-repair --apply
```

The repair only copies Desktop metadata aliases into the current owner group when the referenced `cliSessionId` transcript exists. Missing transcripts remain reported as orphans.

For architecture A:

```bash
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py \
  --manifest ~/.claude/skills/claude-sync-doctor/references/architecture_a_manifest.json check
```

## LaunchAgent

Generate a LaunchAgent plist, but do not load it unless the user asks:

```bash
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py install-launchagent --dry-run
python3 ~/.claude/skills/claude-sync-doctor/scripts/claude_sync_doctor.py install-launchagent --apply
```
