#!/bin/bash
set -e

# Using the data volume for the flag, as it's persistent
SETUP_DONE_FILE="/usr/share/metricbeat/data/.setup_done"

if [ ! -f "$SETUP_DONE_FILE" ]; then
  echo "Metricbeat: Performing initial setup to load dashboards, ILM, etc..."
  # Allow setup to talk to Elasticsearch and Kibana directly
  metricbeat setup -e --dashboards \
    -E setup.kibana.host=kibana:5601 \
    -E output.elasticsearch.hosts='["elasticsearch:9200"]'

  if [ $? -eq 0 ]; then
    touch "$SETUP_DONE_FILE"
    echo "Metricbeat: Initial setup complete."
  else
    echo "Metricbeat: Initial setup failed. Will retry on next start."
    exit 1 # Exit to allow Docker to restart and retry
  fi
else
  echo "Metricbeat: Setup already done, skipping."
fi

echo "Metricbeat: Starting Metricbeat normally..."
exec metricbeat -e -c /usr/share/metricbeat/metricbeat.yml 