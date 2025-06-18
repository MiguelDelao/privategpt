#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
# docs/ lives one level above v2/
FILE="$ROOT_DIR/../docs/observability/kibana_dashboard.ndjson"
DASH_ID="privategpt-dashboard-logs"

bash scripts/wait_for_kibana.sh

printf "Importing dashboard …\n"
resp=$(curl -s -H "kbn-xsrf: true" \
            -F "file=@${FILE};type=application/ndjson" \
            "http://localhost:5601/api/saved_objects/_import?overwrite=true")

if echo "$resp" | grep -q '"success":true'; then
  echo "Import API reported success"
else
  echo "Import failed:"; echo "$resp"; exit 1
fi

# verify dashboard exists
status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5601/api/saved_objects/dashboard/${DASH_ID}") || true
if [[ "$status" == "200" ]]; then
  echo "✅ Dashboard ${DASH_ID} present"
else
  echo "❌ Dashboard not found (HTTP $status)"; exit 1
fi 