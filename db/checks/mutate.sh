#!/usr/bin/env bash
# Prove a story check can fail: apply a mutation, run the check, always roll back.
# Uses the same PSQL as run.sh.
#
#   PSQL="docker compose exec -T db psql -U genbi_owner -d genbi" \
#     db/checks/mutate.sh "UPDATE cafes SET favorite_count = favorite_count + 1 WHERE id = 1" 08_views_favorites.sql
#
# Prints "caught: <first ERROR line>" and exits 0 when the check fails, "NOT caught" and exits 1
# when it still passes, and exits 2 on a usage error or when psql fails without a check error.
set -uo pipefail

usage() {
  echo "usage: $0 \"<mutation SQL>\" <check file or name under db/checks>" >&2
  exit 2
}

[ $# -eq 2 ] || usage
mutation=$1
check=$2
dir="$(cd "$(dirname "$0")" && pwd)"
[ -f "$check" ] || check="$dir/$check"
[ -f "$check" ] || usage

PSQL=${PSQL:-psql}
# One session: the ROLLBACK undoes the mutation; if ON_ERROR_STOP ends the session early,
# closing it rolls back the open transaction too.
out=$({ echo "BEGIN;"; echo "$mutation;"; cat "$check"; echo "ROLLBACK;"; } \
      | $PSQL -X -q -v ON_ERROR_STOP=1 2>&1)
status=$?

error=$(grep -m1 'ERROR:' <<<"$out")
if [ -n "$error" ]; then
  echo "caught: $error"
  exit 0
fi
if [ $status -ne 0 ]; then
  echo "psql failed without a check error: $out" >&2
  exit 2
fi
echo "NOT caught"
exit 1
