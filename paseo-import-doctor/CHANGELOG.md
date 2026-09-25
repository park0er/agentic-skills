# paseo-import-doctor CHANGELOG

## 2026-06-05 — add-restart-and-diag

- Added `restart` command: kills Paseo daemon + app, reopens to reload cleaned import records from disk
- Added `diag` command: cross-references Codex `state_5.sqlite` DB vs Paseo agent records
- `diag` checks Paseo daemon running status, relay connection health, per-workspace breakdown
- `diag --show-all` lists all importable sessions (default: counts only)
- Added mobile/relay troubleshooting section to SKILL.md
- Reads relay status from `~/.paseo/daemon.log` (last 50 entries)

## 2026-06-05 — initial-release

- Initial release of paseo-import-doctor skill
- Core script `paseo_agents.py` with list/show/clean/reset commands
- Supports workspace and status filtering, dry-run mode
- Documents Paseo daemon's import tracking mechanism under `~/.paseo/agents/`
