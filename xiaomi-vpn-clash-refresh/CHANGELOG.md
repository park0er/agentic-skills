# xiaomi-vpn-clash-refresh CHANGELOG

## 2026-08-02 — confirm-company-domain-boundary

- Recorded the user-confirmed Xiaomi corporate suffixes and public-domain exclusions.
- Added the requirement that public DNS uses the existing Clash proxy path.

## 2026-08-02 — initial-vpn-tunnel-recovery

- Added a reusable macOS workflow for Xiaomi VPN and Clash Verge tunnel drift.
- Included installer, health check, recovery, and persistent-agent management.
- Keeps user-specific profile backups in a local recovery vault, not in the distributed skill.
- The watcher never connects or disconnects the corporate VPN.
