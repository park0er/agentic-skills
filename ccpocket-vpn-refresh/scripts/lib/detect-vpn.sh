#!/usr/bin/env bash
# Detect VPN interfaces on macOS.
#
# Prints candidate interfaces one per line in the form: "<iface>\t<ip>"
# - Only considers interfaces matching utun* (the pattern macOS uses for virtual tunnels)
# - Skips interfaces with no IPv4 address
# - Skips 100.64.0.0/10 (Tailscale CGNAT range) — those are not corporate VPN
# - Skips 169.254.0.0/16 (link-local)
#
# If called with argument "--one", prints just the single best candidate
# (or nothing + exit 1 if there are zero or more than one).

set -euo pipefail

list_candidates() {
  for iface in $(ifconfig -l 2>/dev/null); do
    case "$iface" in
      utun*) ;;
      *) continue ;;
    esac
    ip=$(ifconfig "$iface" 2>/dev/null | awk '/inet / && $2 !~ /^127\./ && $2 !~ /^169\.254\./ { print $2; exit }')
    [ -z "${ip:-}" ] && continue
    case "$ip" in
      100.*) continue ;; # Tailscale CGNAT
    esac
    printf "%s\t%s\n" "$iface" "$ip"
  done
}

case "${1:-}" in
  --one)
    candidates=$(list_candidates)
    count=$(printf "%s" "$candidates" | grep -c . || true)
    if [ "$count" -eq 1 ]; then
      printf "%s\n" "$candidates"
      exit 0
    fi
    exit 1
    ;;
  --count)
    list_candidates | grep -c . || true
    ;;
  *)
    list_candidates
    ;;
esac
