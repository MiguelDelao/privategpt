#!/bin/bash
set -euo pipefail

echo "Setting up Keycloak realm and users..."

# Wait for Keycloak to be ready
echo "Waiting for Keycloak to be available..."
until curl -s http://keycloak:8080/health/ready | grep -q "UP"; do
  echo "Keycloak not ready, waiting..."
  sleep 5
done

echo "Keycloak is ready, proceeding with setup..."

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

# Create privategpt realm
echo "Creating privategpt realm..."
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
  }' || echo "Realm might already exist"

# Create client
echo "Creating privategpt-ui client..."
curl -s -X POST "http://keycloak:8080/admin/realms/privategpt/clients" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "privategpt-ui",
    "name": "PrivateGPT UI",
    "enabled": true,
    "publicClient": false,
    "directAccessGrantsEnabled": true,
    "serviceAccountsEnabled": true,
    "standardFlowEnabled": true,
    "implicitFlowEnabled": false,
    "secret": "privategpt-ui-secret-key",
    "redirectUris": ["http://localhost:8501/*", "http://localhost/*"],
    "webOrigins": ["http://localhost:8501", "http://localhost"]
  }' || echo "Client might already exist"

# Get client UUID for mapper configuration
echo "Getting client UUID..."
CLIENT_UUID=$(curl -s -X GET "http://keycloak:8080/admin/realms/privategpt/clients?clientId=privategpt-ui" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].id')

if [ "$CLIENT_UUID" != "null" ] && [ -n "$CLIENT_UUID" ]; then
  echo "Adding audience mapper to client..."
  curl -s -X POST "http://keycloak:8080/admin/realms/privategpt/clients/$CLIENT_UUID/protocol-mappers/models" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "audience-mapper",
      "protocol": "openid-connect",
      "protocolMapper": "oidc-audience-mapper",
      "consentRequired": false,
      "config": {
        "included.client.audience": "privategpt-ui",
        "access.token.claim": "true"
      }
    }' || echo "Audience mapper might already exist"
  echo "Audience mapper added successfully"
else
  echo "Could not find client UUID for privategpt-ui"
fi

# Create roles
echo "Creating roles..."
curl -s -X POST "http://keycloak:8080/admin/realms/privategpt/roles" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "admin",
    "description": "Administrator role"
  }' || echo "Admin role might already exist"

curl -s -X POST "http://keycloak:8080/admin/realms/privategpt/roles" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "user",
    "description": "Regular user role"
  }' || echo "User role might already exist"

# Create admin user
echo "Creating admin user..."
USER_RESPONSE=$(curl -s -X POST "http://keycloak:8080/admin/realms/privategpt/users" \
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
  }' -w "%{http_code}")

# Get user ID for role assignment
USER_ID=$(curl -s -X GET "http://keycloak:8080/admin/realms/privategpt/users?username=admin@admin.com" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].id')

if [ "$USER_ID" != "null" ] && [ -n "$USER_ID" ]; then
  echo "Assigning admin role to user..."
  # Get admin role representation
  ADMIN_ROLE=$(curl -s -X GET "http://keycloak:8080/admin/realms/privategpt/roles/admin" \
    -H "Authorization: Bearer $ADMIN_TOKEN")
  
  # Assign admin role to user
  curl -s -X POST "http://keycloak:8080/admin/realms/privategpt/users/$USER_ID/role-mappings/realm" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "[$ADMIN_ROLE]"
  
  echo "Admin role assigned successfully"
else
  echo "Could not find user ID for admin@admin.com"
fi

echo "Keycloak setup completed successfully!"
echo "Default credentials: admin@admin.com / admin"

# Ensure script exits cleanly
exit 0