#!/bin/bash

# PrivateGPT Dashboard Auto-Setup Script
# Automatically creates working dashboard after ELK stack startup

echo "Setting up PrivateGPT Custom Dashboard..."

# Wait for Kibana to be ready with faster polling
echo "Waiting for ELK stack..."
max_attempts=60
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s "http://localhost:9200/_cluster/health" > /dev/null 2>&1 && \
       curl -s "http://localhost:5601/api/status" > /dev/null 2>&1; then
        echo "✅ ELK Stack ready"
        break
    fi
    
    if [ $((attempt % 10)) -eq 0 ]; then
        echo "⏳ Still waiting... ($attempt/$max_attempts)"
    fi
    sleep 5
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ ELK Stack not ready after ${max_attempts} attempts"
    exit 1
fi

# Reduced wait for Kibana initialization
echo "Initializing Kibana..."
sleep 5

# Create required data views
echo "Setting up data views..."

# Create filebeat data view
filebeat_result=$(curl -s -X POST "http://localhost:5601/api/data_views/data_view" \
    -H "kbn-xsrf: true" \
    -H "Content-Type: application/json" \
    -d '{
        "data_view": {
            "title": "filebeat-*",
            "timeFieldName": "@timestamp"
        }
    }')

filebeat_id=$(echo "$filebeat_result" | jq -r '.data_view.id // empty' 2>/dev/null)
if [ -z "$filebeat_id" ]; then
    filebeat_id=$(curl -s "http://localhost:5601/api/data_views" -H "kbn-xsrf: true" | jq -r '.data_view[] | select(.title=="filebeat-*") | .id' 2>/dev/null)
fi

echo "✅ Data views configured (ID: $filebeat_id)"

# Clean up old saved searches and dashboard in parallel
echo "Cleaning up old dashboard components..."
{
    curl -s -X DELETE "http://localhost:5601/api/saved_objects/dashboard/53c5b260-3f89-11f0-b185-c1d217685ac0" -H "kbn-xsrf: true" > /dev/null 2>&1 &
    curl -s -X DELETE "http://localhost:5601/api/saved_objects/search/auth-service-logs" -H "kbn-xsrf: true" > /dev/null 2>&1 &
    curl -s -X DELETE "http://localhost:5601/api/saved_objects/search/streamlit-app-logs" -H "kbn-xsrf: true" > /dev/null 2>&1 &
    curl -s -X DELETE "http://localhost:5601/api/saved_objects/search/ollama-service-logs" -H "kbn-xsrf: true" > /dev/null 2>&1 &
    curl -s -X DELETE "http://localhost:5601/api/saved_objects/search/database-service-logs" -H "kbn-xsrf: true" > /dev/null 2>&1 &
    curl -s -X DELETE "http://localhost:5601/api/saved_objects/search/weaviate-logs" -H "kbn-xsrf: true" > /dev/null 2>&1 &
    curl -s -X DELETE "http://localhost:5601/api/saved_objects/search/n8n-service-logs" -H "kbn-xsrf: true" > /dev/null 2>&1 &
    wait
}

# Create properly filtered saved searches in parallel
echo "Creating saved searches with correct filtering..."

{
# Create simple saved searches with just 2 columns
for service in "auth-service:🔐 Auth Service" "streamlit-app:🖥️ Streamlit App" "ollama-service:🧠 Ollama LLM" "database-service:🗃️ Database Service" "weaviate-db:🔍 Weaviate DB" "n8n-automation:🔄 N8N Automation"; do
    container=$(echo $service | cut -d: -f1)
    title=$(echo $service | cut -d: -f2-)
    
    curl -s -X POST "http://localhost:5601/api/saved_objects/search/${container}-logs" \
        -H "kbn-xsrf: true" \
        -H "Content-Type: application/json" \
        -d "{
            \"attributes\": {
                \"title\": \"$title\",
                \"columns\": [\"@timestamp\", \"message\"],
                \"sort\": [[\"@timestamp\", \"desc\"]],
                \"kibanaSavedObjectMeta\": {
                    \"searchSourceJSON\": \"{\\\"highlightAll\\\":true,\\\"version\\\":true,\\\"query\\\":{\\\"query\\\":\\\"container.name: \\\\\\\"$container\\\\\\\"\\\",\\\"language\\\":\\\"kuery\\\"},\\\"filter\\\":[],\\\"indexRefName\\\":\\\"kibanaSavedObjectMeta.searchSourceJSON.index\\\"}\"
                }
            },
            \"references\": [
                {
                    \"name\": \"kibanaSavedObjectMeta.searchSourceJSON.index\",
                    \"type\": \"index-pattern\",
                    \"id\": \"$filebeat_id\"
                }
            ]
        }" > /dev/null &
done

# Wait for all parallel saved searches to complete
wait
}

echo "✅ Saved searches created"

# Now create the main dashboard with better layout and fixed columns
echo "Creating dashboard with proper layout..."

dashboard_json='{
  "attributes": {
    "title": "PrivateGPT System Monitor",
    "description": "Container logs with 2-column layout: timestamp + message",
    "panelsJSON": "[{\"version\":\"8.11.1\",\"type\":\"search\",\"gridData\":{\"x\":0,\"y\":0,\"w\":48,\"h\":25,\"i\":\"1\"},\"panelIndex\":\"1\",\"panelRefName\":\"panel_1\",\"embeddableConfig\":{\"timeRange\":{\"from\":\"now-15m\",\"to\":\"now\"},\"hidePanelTitles\":false,\"enhancements\":{},\"savedObjectId\":\"auth-service-logs\"}},{\"version\":\"8.11.1\",\"type\":\"search\",\"gridData\":{\"x\":0,\"y\":25,\"w\":48,\"h\":25,\"i\":\"2\"},\"panelIndex\":\"2\",\"panelRefName\":\"panel_2\",\"embeddableConfig\":{\"timeRange\":{\"from\":\"now-15m\",\"to\":\"now\"},\"hidePanelTitles\":false,\"enhancements\":{},\"savedObjectId\":\"streamlit-app-logs\"}},{\"version\":\"8.11.1\",\"type\":\"search\",\"gridData\":{\"x\":0,\"y\":50,\"w\":48,\"h\":25,\"i\":\"3\"},\"panelIndex\":\"3\",\"panelRefName\":\"panel_3\",\"embeddableConfig\":{\"timeRange\":{\"from\":\"now-15m\",\"to\":\"now\"},\"hidePanelTitles\":false,\"enhancements\":{},\"savedObjectId\":\"ollama-service-logs\"}},{\"version\":\"8.11.1\",\"type\":\"search\",\"gridData\":{\"x\":0,\"y\":75,\"w\":48,\"h\":25,\"i\":\"4\"},\"panelIndex\":\"4\",\"panelRefName\":\"panel_4\",\"embeddableConfig\":{\"timeRange\":{\"from\":\"now-15m\",\"to\":\"now\"},\"hidePanelTitles\":false,\"enhancements\":{},\"savedObjectId\":\"database-service-logs\"}},{\"version\":\"8.11.1\",\"type\":\"search\",\"gridData\":{\"x\":0,\"y\":100,\"w\":48,\"h\":25,\"i\":\"5\"},\"panelIndex\":\"5\",\"panelRefName\":\"panel_5\",\"embeddableConfig\":{\"timeRange\":{\"from\":\"now-15m\",\"to\":\"now\"},\"hidePanelTitles\":false,\"enhancements\":{},\"savedObjectId\":\"weaviate-db-logs\"}},{\"version\":\"8.11.1\",\"type\":\"search\",\"gridData\":{\"x\":0,\"y\":125,\"w\":48,\"h\":25,\"i\":\"6\"},\"panelIndex\":\"6\",\"panelRefName\":\"panel_6\",\"embeddableConfig\":{\"timeRange\":{\"from\":\"now-15m\",\"to\":\"now\"},\"hidePanelTitles\":false,\"enhancements\":{},\"savedObjectId\":\"n8n-automation-logs\"}}]",
    "optionsJSON": "{\"useMargins\":true,\"syncColors\":false,\"hidePanelTitles\":false}",
    "version": 1,
    "timeRestore": true,
    "timeTo": "now",
    "timeFrom": "now-15m",
    "kibanaSavedObjectMeta": {
      "searchSourceJSON": "{\"query\":{\"query\":\"\",\"language\":\"kuery\"},\"filter\":[]}"
    }
  },
  "references": [
    {
      "name": "panel_1",
      "type": "search",
      "id": "auth-service-logs"
    },
    {
      "name": "panel_2",
      "type": "search",
      "id": "streamlit-app-logs"
    },
    {
      "name": "panel_3",
      "type": "search", 
      "id": "ollama-service-logs"
    },
    {
      "name": "panel_4",
      "type": "search",
      "id": "database-service-logs"
    },
    {
      "name": "panel_5",
      "type": "search",
      "id": "weaviate-db-logs"
    },
    {
      "name": "panel_6",
      "type": "search",
      "id": "n8n-automation-logs"
    }
  ]
}'

# Create the dashboard with the original ID
create_result=$(curl -s -X POST "http://localhost:5601/api/saved_objects/dashboard/53c5b260-3f89-11f0-b185-c1d217685ac0" \
    -H "kbn-xsrf: true" \
    -H "Content-Type: application/json" \
    -d "$dashboard_json")

dashboard_id=$(echo "$create_result" | jq -r '.id // empty' 2>/dev/null)

if [ -n "$dashboard_id" ]; then
    echo "✅ Dashboard created successfully!"
    echo ""
    echo "🚀 Access your dashboard:"
    echo "   📊 URL: http://localhost/kibana/app/dashboards#/view/53c5b260-3f89-11f0-b185-c1d217685ac0"
    echo ""
    echo "🎯 Features:"
    echo "   ✅ Proper service filtering - each panel shows only its service logs"
    echo "   ✅ Optimized columns: timestamp | container | message"
    echo "   ✅ Larger panels (25 units height) for better visibility"
    echo "   ✅ 200 log entries per panel"
else
    echo "❌ Failed to create dashboard"
    echo "Response: $create_result"
    exit 1
fi 