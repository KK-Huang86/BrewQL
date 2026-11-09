#!/usr/bin/env bash
# Prove a story check can fail: apply a mutation, run the check, always roll back.
# Uses the same PSQL as run.sh.
#
#   PSQL="docker compose exec -T db psql -U genbi_owner -d genbi" \
#     db/checks/mutate.sh "UPDATE cafes SET favorite_count = favorite_count + 1 WHERE id = 1" 08_views_favorites.sql
#
# Prints "caught: <first ERROR line>" and exits 0 when the check fails, "NOT caught" and exits 1
# when it still passes. Exits 2 on a usage error, when the mutation itself fails (so a typo is
# never read as caught), or when psql fails without a check error.
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
# The marker separates the mutation's output from the check's: only an ERROR after it counts.
marker="mutate.sh: mutation applied"
# The newline before ROLLBACK keeps it off a last line that is a comment without a newline.
out=$({ printf 'BEGIN;\n%s;\n\\echo %s\n' "$mutation" "$marker"; cat "$check"; printf '\nROLLBACK;\n'; } \
      | $PSQL -X -q -v ON_ERROR_STOP=1 2>&1)
status=$?

if ! grep -qxF "$marker" <<<"$out"; then
  echo "mutation or psql failed before the check ran: $(grep -m1 'ERROR:' <<<"$out" || echo "$out")" >&2
  exit 2
fi
error=$(sed -n "/^${marker}\$/,\$p" <<<"$out" | grep -m1 'ERROR:')
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
