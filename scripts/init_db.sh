#!/usr/bin/env bash
# init_db.sh — apply db/ to the target database with psql.
# See init_db.ps1 for the Windows equivalent.
#
#   AGENTBUILDER_DSN=postgresql://... ./scripts/init_db.sh [--drop] [--role NAME]

set -euo pipefail

DSN="${AGENTBUILDER_DSN:-}"
ROLE=""
DROP=0
PREFLIGHT=0

while [ $# -gt 0 ]; do
    case "$1" in
        --drop) DROP=1; shift ;;
        --preflight) PREFLIGHT=1; shift ;;
        --role) ROLE="$2"; shift 2 ;;
        --dsn)  DSN="$2"; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

if [ -z "$DSN" ]; then
    echo "Set AGENTBUILDER_DSN or pass --dsn" >&2
    exit 1
fi

cd "$(dirname "$0")/../db"

if [ "$PREFLIGHT" = "1" ]; then
    # Read-only. Run this before anything else against a database with data.
    psql "$DSN" -v ON_ERROR_STOP=1 -f 000_preflight.sql
    exit $?
fi

if [ "$DROP" = "1" ]; then
    echo "Dropping existing objects..."
    psql "$DSN" -v ON_ERROR_STOP=1 -f 999_drop_all.sql
fi

echo "Applying schema..."
psql "$DSN" -v ON_ERROR_STOP=1 -f run_all.sql

if [ -n "$ROLE" ]; then
    echo "Applying grants for role '$ROLE'..."
    psql "$DSN" -v ON_ERROR_STOP=1 -c "SET agentbuilder.role = '$ROLE'" -f 011_grants.sql
fi

echo "Done."
