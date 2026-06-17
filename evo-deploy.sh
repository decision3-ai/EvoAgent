#!/usr/bin/env bash
#
# evo-deploy.sh — build, push, and stage a new EvoAgent release for Akash.
#
# Usage:
#   ./evo-deploy.sh v4
#
# Steps:
#   1. Build victordflos/evoagent-api:{tag}     (apps/api  + Dockerfile.api)
#   2. Build victordflos/evoagent-workers:{tag} (apps/workers + Dockerfile.workers)
#   3. Push both images to Docker Hub
#   4. Rewrite image tags in infrastructure/akash/deploy.filled.yaml
#   5. Print the manual Akash Console "Update" instructions
#
set -euo pipefail

# --- locate project root (this script lives in the root) ---
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# --- args ---
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <version-tag>   e.g. $0 v4" >&2
  exit 1
fi
TAG="$1"

API_IMAGE="victordflos/evoagent-api:${TAG}"
WORKERS_IMAGE="victordflos/evoagent-workers:${TAG}"
SDL="infrastructure/akash/deploy.filled.yaml"

if [[ ! -f "$SDL" ]]; then
  echo "ERROR: SDL not found at $SDL" >&2
  exit 1
fi

echo "==> Building API image: $API_IMAGE"
docker build -t "$API_IMAGE" -f infrastructure/docker/Dockerfile.api apps/api

echo "==> Building Workers image: $WORKERS_IMAGE"
docker build -t "$WORKERS_IMAGE" -f infrastructure/docker/Dockerfile.workers apps/workers

echo "==> Pushing $API_IMAGE"
docker push "$API_IMAGE"

echo "==> Pushing $WORKERS_IMAGE"
docker push "$WORKERS_IMAGE"

echo "==> Updating image tags in $SDL"
# api  -> used once; workers image -> used by both 'workers' and 'celery-beat'
sed -i -E \
  -e "s#(image:[[:space:]]*victordflos/evoagent-api:).*#\1${TAG}#" \
  -e "s#(image:[[:space:]]*victordflos/evoagent-workers:).*#\1${TAG}#" \
  "$SDL"

echo "    New image lines:"
grep -nE 'image:[[:space:]]*victordflos/evoagent-(api|workers):' "$SDL" | sed 's/^/      /'

cat <<EOF

==> Done building & pushing.

NEXT — manual Akash Console step (cannot be automated):
  1. Open https://console.akash.network and select the EvoAgent deployment.
  2. Click "Update".
  3. Paste the contents of:
        $ROOT/$SDL
  4. Review the diff (api -> :${TAG}, workers/celery-beat -> :${TAG}).
  5. Submit the update transaction and approve in your wallet.
  6. Wait for the new lease/pods to come up, then verify the API health endpoint.

EOF
