#!/bin/bash
# ssh-panel.sh — Open SSH tunnel to 3x-ui panel
# Usage: bash ssh-panel.sh
# Then open: http://localhost:2053/parko-3xui-dashboard/

SSH_KEY="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1/KEY/OracleCloud/ssh-key-2026-07-04-private.key"
SERVER="ubuntu@141.147.189.28"
LOCAL_PORT=2053

echo "Opening SSH tunnel to 3x-ui panel..."
echo "Panel URL: http://localhost:${LOCAL_PORT}/parko-3xui-dashboard/"
echo "Username: park0er"
echo "Press Ctrl+C to close the tunnel."
echo ""

ssh -L ${LOCAL_PORT}:localhost:${LOCAL_PORT} -N -i "$SSH_KEY" "$SERVER"
