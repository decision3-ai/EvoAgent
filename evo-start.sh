#!/usr/bin/env bash
#
# evo-start.sh — deploy a fresh SDL on Akash, then restore the latest local backup.
#
# Custom-format (-Fc) backups produced by evo-save.sh are restored with
# `pg_restore`, running inside the new postgres container via
# `provider-services lease-shell`.
#
# Usage:
#   ./evo-start.sh
#
# Required env (the *new* Akash lease coordinates after you deploy):
#   AKASH_DSEQ        deployment sequence of the NEW deployment
#   AKASH_PROVIDER    provider address (akash1...)
#   AKASH_KEY_NAME    local key name used to sign (--from)
# Optional env:
#   AKASH_GSEQ        group sequence (default: 1)
#   AKASH_OSEQ        order sequence (default: 1)
#   PG_USER           postgres user  (default: agentevo)
#   PG_DB             postgres db    (default: agentevo_db)
#   BACKUP_FILE       explicit backup path (default: newest evo-backup-*.dump)
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$HOME/Documents/AgentEvo/backups"
SDL="$ROOT/infrastructure/akash/deploy.filled.yaml"

cat <<EOF
==> STEP 1 — Deploy the SDL on Akash (manual):
    1. Open https://console.akash.network and click "Create Deployment".
    2. Paste the contents of:
          $SDL
    3. Submit, pick a bid/provider, and create the lease.
    4. Wait for all pods (postgres, redis, ollama, api, workers, celery-beat) to be Running.
    5. Note the NEW dseq / provider and export them:
          export AKASH_DSEQ=...  AKASH_PROVIDER=akash1...  AKASH_KEY_NAME=...

EOF

# --- locate latest backup ---
PG_USER="${PG_USER:-agentevo}"
PG_DB="${PG_DB:-agentevo_db}"

if [[ -n "${BACKUP_FILE:-}" ]]; then
  BACKUP="$BACKUP_FILE"
else
  BACKUP="$(ls -1t "$BACKUP_DIR"/evo-backup-*.dump 2>/dev/null | head -n1 || true)"
fi

if [[ -z "${BACKUP:-}" || ! -f "$BACKUP" ]]; then
  echo "ERROR: no backup found in $BACKUP_DIR (set BACKUP_FILE to override)." >&2
  exit 1
fi

# --- require lease coordinates before restoring ---
: "${AKASH_DSEQ:?Set AKASH_DSEQ for the new deployment, then re-run}"
: "${AKASH_PROVIDER:?Set AKASH_PROVIDER, then re-run}"
: "${AKASH_KEY_NAME:?Set AKASH_KEY_NAME, then re-run}"
AKASH_GSEQ="${AKASH_GSEQ:-1}"
AKASH_OSEQ="${AKASH_OSEQ:-1}"

echo "==> STEP 2 — Restoring $BACKUP into '$PG_DB' (dseq=$AKASH_DSEQ)"

# Pipe the local custom-format dump into pg_restore inside the new postgres container.
provider-services lease-shell \
  --dseq "$AKASH_DSEQ" \
  --gseq "$AKASH_GSEQ" \
  --oseq "$AKASH_OSEQ" \
  --provider "$AKASH_PROVIDER" \
  --from "$AKASH_KEY_NAME" \
  --stdin \
  postgres \
  pg_restore -U "$PG_USER" -d "$PG_DB" --no-owner --no-privileges --clean --if-exists \
  < "$BACKUP"

echo "==> Restore complete."
echo "    Verify the API health endpoint and that data is present, then you're live."
