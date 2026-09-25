#!/usr/bin/env bash
# Authenticate the `local` multica profile WITHOUT the browser-OAuth/TTY login
# the CLI normally requires. It mints a Personal Access Token directly in the
# local Postgres and logs in with `multica login --token`.
#
# Why this works: a PAT row stores token_hash = sha256_hex("mul_"+40hex) and
# token_prefix = first 12 chars (see server/internal/auth/jwt.go HashToken /
# GeneratePATToken). We generate a token, insert its hash, then hand the raw
# token to `multica login --token`, which validates it against the local server.
#
# Run from the multica checkout root, AFTER: `make dev` is up, you have signed
# up + created a workspace in the browser, and `make build` has produced
# server/bin/multica.
#
# Usage: local-daemon-login.sh [server_url] [profile]
#   server_url default http://localhost:8080 ; profile default "local"
set -euo pipefail

SERVER_URL="${1:-http://localhost:8080}"
PROFILE="${2:-local}"
MULTICA_BIN="./server/bin/multica"
[ -x "$MULTICA_BIN" ] || { echo "✗ $MULTICA_BIN not found — run 'make build' first." >&2; exit 1; }

psql() { docker compose exec -T postgres psql -U multica -d multica "$@"; }

# Newest signed-up user (table name "user" is a reserved word -> must be quoted).
USER_ID="$(psql -Atc 'select id from "user" order by created_at desc limit 1;' | tr -d '\r')"
[ -n "$USER_ID" ] || { echo "✗ no user found — sign up at the web app first." >&2; exit 1; }
echo "==> user: $USER_ID"

read RAW HASH PREFIX <<<"$(python3 -c "import os,hashlib;raw='mul_'+os.urandom(20).hex();print(raw, hashlib.sha256(raw.encode()).hexdigest(), raw[:12])")"
echo "==> minting PAT (prefix $PREFIX) for the local daemon"
psql -v ON_ERROR_STOP=1 -c \
"INSERT INTO personal_access_token (id,user_id,name,token_hash,token_prefix,expires_at,revoked,created_at) \
 VALUES (gen_random_uuid(),'$USER_ID','multica-local-daemon','$HASH','$PREFIX', now()+interval '365 days', false, now());" >/dev/null

echo "==> logging in profile '$PROFILE' against $SERVER_URL"
"$MULTICA_BIN" login --profile "$PROFILE" --server-url "$SERVER_URL" --token "$RAW"
echo "✓ profile '$PROFILE' authenticated. Next: $MULTICA_BIN daemon start --profile $PROFILE"
