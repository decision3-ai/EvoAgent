#!/usr/bin/env bash
#
# evo-save.sh — back up the live Akash Postgres, then remind to close the deployment.
#
# Runs pg_dump *inside* the running Akash postgres container via `provider-services
# lease-shell` and streams a custom-format (-Fc) dump to a local file.
#
# Usage:
#   ./evo-save.sh
#
# Required env (Akash lease coordinates — find them in the Akash Console):
#   AKASH_DSEQ        deployment sequence
#   AKASH_PROVIDER    provider address (akash1...)
#   AKASH_KEY_NAME    local key name used to sign (--from)
# Optional env:
#   AKASH_GSEQ        group sequence   (default: 1)
#   AKASH_OSEQ        order sequence   (default: 1)
#   PG_USER           postgres user    (default: agentevo)
#   PG_DB             postgres db      (default: agentevo_db)
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$HOME/Documents/AgentEvo/backups"

: "${AKASH_DSEQ:?Set AKASH_DSEQ (deployment sequence)}"
: "${AKASH_PROVIDER:?Set AKASH_PROVIDER (provider address)}"
: "${AKASH_KEY_NAME:?Set AKASH_KEY_NAME (signing key --from)}"
AKASH_GSEQ="${AKASH_GSEQ:-1}"
AKASH_OSEQ="${AKASH_OSEQ:-1}"
PG_USER="${PG_USER:-agentevo}"
PG_DB="${PG_DB:-agentevo_db}"

mkdir -p "$BACKUP_DIR"
DATE="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/evo-backup-${DATE}.dump"

echo "==> Dumping Postgres '$PG_DB' (user $PG_USER) from Akash lease dseq=$AKASH_DSEQ"
echo "    -> $OUT"

# lease-shell runs the command in the 'postgres' service container; its stdout
# (the custom-format dump) is captured into the local backup file.
provider-services lease-shell \
  --dseq "$AKASH_DSEQ" \
  --gseq "$AKASH_GSEQ" \
  --oseq "$AKASH_OSEQ" \
  --provider "$AKASH_PROVIDER" \
  --from "$AKASH_KEY_NAME" \
  postgres \
  pg_dump -U "$PG_USER" -d "$PG_DB" -Fc --no-owner --no-privileges \
  > "$OUT"

if [[ ! -s "$OUT" ]]; then
  echo "ERROR: backup file is empty — check lease coordinates / credentials." >&2
  rm -f "$OUT"
  exit 1
fi

echo "==> Backup saved: $OUT ($(du -h "$OUT" | cut -f1))"

cat <<EOF

REMINDER:
  The backup is now safe locally. You can close the Akash deployment to stop billing:
    1. Open https://console.akash.network
    2. Select the EvoAgent deployment.
    3. Click "Close" and approve the close transaction in your wallet.

  Restore later with:  ./evo-start.sh

EOF
