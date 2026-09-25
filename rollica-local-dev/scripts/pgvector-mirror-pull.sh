#!/usr/bin/env bash
# Pre-pull the Postgres image `make dev` needs, via a China-reachable mirror,
# and retag it to the canonical name so `docker compose up` finds it locally
# and never reaches Docker Hub (which is throttled/blocked from CN networks).
#
# pgvector/pgvector:pg17 is the ONLY image `make dev` requires; everything else
# is built from source. Run this once before the first `make dev` on a CN network.
#
# Usage: pgvector-mirror-pull.sh [image] [mirror1 mirror2 ...]
set -euo pipefail

IMAGE="${1:-pgvector/pgvector:pg17}"
shift || true
MIRRORS=("$@")
if [ "${#MIRRORS[@]}" -eq 0 ]; then
  MIRRORS=(docker.m.daocloud.io docker.1panel.live docker.1ms.run dockerproxy.net)
fi

if docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "✓ $IMAGE already present locally; nothing to do."
  exit 0
fi

for m in "${MIRRORS[@]}"; do
  echo "==> trying mirror: $m"
  if docker pull "$m/$IMAGE" 2>&1 | tail -3; then
    docker tag "$m/$IMAGE" "$IMAGE"
    echo "✓ pulled via $m and retagged as $IMAGE"
    docker images | grep -i "${IMAGE%%:*}" || true
    exit 0
  fi
  echo "   mirror $m failed, trying next..."
done

echo "✗ all mirrors failed for $IMAGE. Try a VPN, or pass working mirrors as args." >&2
exit 1
