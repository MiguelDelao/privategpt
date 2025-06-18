#!/usr/bin/env bash
set -e

HOST=${KIBANA_HOST:-localhost:5601}
TIMEOUT_SEC=${KIBANA_WAIT_TIMEOUT:-180}

printf "Waiting for Kibana at %s " "$HOST"
start=$(date +%s)
while true; do
  if curl -s "http://$HOST/api/status" | grep -q '"level":"available"' ; then
    echo "✅"
    exit 0
  fi
  printf "."
  sleep 3
  now=$(date +%s)
  if (( now - start > TIMEOUT_SEC )); then
    echo "\n❌ Timed out after ${TIMEOUT_SEC}s waiting for Kibana"
    exit 1
  fi
done 