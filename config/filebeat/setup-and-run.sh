#!/bin/bash
set -e

# Using the data volume for the flag, as it's persistent
SETUP_DONE_FILE="/usr/share/filebeat/data/.setup_done"

if [ ! -f "$SETUP_DONE_FILE" ]; then
  echo "Filebeat: Performing initial setup to load dashboards, ILM, etc..."
  # Allow setup to talk to Elasticsearch and Kibana directly
  # This might take a moment if Elasticsearch/Kibana are still starting
  filebeat setup -e --dashboards \
    -E setup.kibana.host=kibana:5601 \
    -E output.elasticsearch.hosts='["elasticsearch:9200"]'
  
  if [ $? -eq 0 ]; then
    touch "$SETUP_DONE_FILE"
    echo "Filebeat: Initial setup complete."
  else
    echo "Filebeat: Initial setup failed. Will retry on next start."
    exit 1 # Exit to allow Docker to restart and retry
  fi
else
  echo "Filebeat: Setup already done, skipping."
fi

echo "Filebeat: Starting Filebeat normally..."
exec filebeat -e -c /usr/share/filebeat/filebeat.yml 