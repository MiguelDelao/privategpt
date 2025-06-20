#!/bin/sh
set -e

echo "Setting up Keycloak realm via import..."

# Wait for Keycloak to be ready
echo "Waiting for Keycloak to be available..."
until curl -s http://keycloak:8080/health/ready | grep -q "UP"; do
  echo "Keycloak not ready, waiting..."
  sleep 5
done

echo "Keycloak is ready, proceeding with realm import..."

# Get admin token
echo "Getting admin token..."
ADMIN_TOKEN=$(curl -s -X POST "http://keycloak:8080/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin" \
  -d "password=${KEYCLOAK_ADMIN_PASSWORD:-admin123}" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token')

if [ "$ADMIN_TOKEN" = "null" ] || [ -z "$ADMIN_TOKEN" ]; then
  echo "Failed to get admin token"
  exit 1
fi

echo "Admin token obtained successfully"

# Check if realm already exists
echo "Checking if privategpt realm already exists..."
REALM_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://keycloak:8080/admin/realms/privategpt")

if [ "$REALM_EXISTS" = "200" ]; then
  echo "✅ Realm 'privategpt' already exists, skipping import"
else
  echo "📥 Importing privategpt realm from configuration..."
  
  # Import the realm from the pre-configured JSON file
  IMPORT_RESPONSE=$(curl -s -X POST "http://keycloak:8080/admin/realms" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d @/config/realm-export.json \
    -w "%{http_code}")
  
  if [ "$IMPORT_RESPONSE" = "201" ] || [ "$IMPORT_RESPONSE" = "409" ]; then
    echo "✅ Realm imported successfully"
  else
    echo "❌ Failed to import realm (HTTP $IMPORT_RESPONSE)"
    echo "🔄 Falling back to manual realm creation..."
    
    # Fallback: Create basic realm manually
    curl -s -X POST "http://keycloak:8080/admin/realms" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "realm": "privategpt",
        "displayName": "PrivateGPT",
        "enabled": true,
        "registrationAllowed": true,
        "loginWithEmailAllowed": true,
        "duplicateEmailsAllowed": false,
        "resetPasswordAllowed": false,
        "editUsernameAllowed": false,
        "bruteForceProtected": false,
        "accessTokenLifespan": 3600,
        "ssoSessionMaxLifespan": 36000
      }' || echo "Basic realm creation failed"
  fi
fi

# Verify admin user exists
echo "Verifying admin user exists..."
ADMIN_USER_CHECK=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://keycloak:8080/admin/realms/privategpt/users?username=admin@admin.com" | jq -r 'length')

if [ "$ADMIN_USER_CHECK" = "0" ]; then
  echo "⚠️  Admin user not found, creating manually..."
  
  # Create admin user manually as fallback
  curl -s -X POST "http://keycloak:8080/admin/realms/privategpt/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "username": "admin@admin.com",
      "email": "admin@admin.com",
      "firstName": "Admin",
      "lastName": "User",
      "enabled": true,
      "emailVerified": true,
      "credentials": [{
        "type": "password",
        "value": "admin",
        "temporary": false
      }]
    }'
  
  echo "Manual admin user created"
else
  echo "✅ Admin user exists"
fi

# Get admin credentials from config (with fallbacks)
ADMIN_EMAIL="${DEFAULT_ADMIN_EMAIL:-admin@admin.com}"
ADMIN_USERNAME="${DEFAULT_ADMIN_USERNAME:-admin@admin.com}"
ADMIN_PASSWORD="${DEFAULT_ADMIN_PASSWORD:-admin}"

echo "Keycloak setup completed successfully!"
echo "Default credentials: $ADMIN_EMAIL / $ADMIN_PASSWORD"
echo "📝 You can customize these via environment variables or config.json"

# Ensure script exits cleanly
exit 0