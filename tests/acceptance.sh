#!/bin/bash
# The repository's acceptance test, and it is the README's promise measured:
# from a clean machine, one command brings each profile up, `doctor` is green,
# and a message reaches the deployment recorded the way that profile says.
#
# It needs a reachable Diffuse deployment and a way to read its audit trail.
# `DIFFUSE_AUDIT_CMD` says how; the default is the containerised deployment the
# product repository's own harness stands up.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
HERE=$(pwd)
FAIL=0

step()   { echo; echo "######## $*"; }
expect() { if [ "$2" = "$3" ]; then printf '  ok    %-48s %s\n' "$1" "$3"
           else printf '  FAIL  %-48s wanted %s, got %s\n' "$1" "$2" "$3"; FAIL=1; fi; }
plain()  { sed 's/\x1b\[[0-9;]*m//g'; }

step "a clean machine"
./diffuse-chat down --volumes >/dev/null 2>&1
docker volume ls -q --filter name=diffuse-chat | xargs -r docker volume rm >/dev/null 2>&1
echo "  containers: $(docker ps -a --filter name=diffuse-chat -q | wc -l)" \
     "  volumes: $(docker volume ls -q --filter name=diffuse-chat | wc -l)"

for profile in dev ent; do
  if [ "$profile" = dev ]; then flag=""; label="developer"; else flag="--enterprise"; label="enterprise"; fi

  step "$label profile — ./diffuse-chat up $flag"
  [ "$profile" = ent ] && python3 tests/chat_once.py import
  ./diffuse-chat up $flag 2>&1 | grep -E "created|already there|open http|registration" | head -4
  # The deployment used by this test lives on the compose network; on a
  # customer's machine it is a host and this line is not needed.
  docker network connect diffuse-chat_default diffuse-api >/dev/null 2>&1

  step "$label profile — ./diffuse-chat doctor"
  ./diffuse-chat doctor 2>&1 | plain | grep -E "ok|FAIL|Everything|failed"
  ./diffuse-chat doctor >/dev/null 2>&1
  expect "doctor exits green" 0 "$?"

  step "$label profile — a message, end to end"
  python3 tests/chat_once.py "$profile"
  expect "it reached the deployment, shaped as promised" 0 "$?"
done

step "the trail, which is the whole point"
eval "${DIFFUSE_AUDIT_CMD:-docker exec diffuse-api diffuse-coordinator audit --action inference --limit 4 --config /home/lot3/coordinator.toml}" 2>/dev/null | tail -3

echo
if [ $FAIL -eq 0 ]; then
  echo "  ACCEPTANCE: both profiles, from clean, one command each."
else
  echo "  ACCEPTANCE FAILED."
fi
exit $FAIL
