#!/usr/bin/env bash
# Helper script fetching a Keycloak OIDC Access Token via Resource Owner Password Flow.
# Usage: ./scripts/get_token.sh [username] [password]
# Default: alice Alice@123

USERNAME="${1:-alice}"
PASSWORD="${2:-Alice@123}"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-company}"
CLIENT_ID="${CLIENT_ID:-company-app}"

TOKEN_ENDPOINT="${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token"

RESPONSE=$(curl -s -X POST "${TOKEN_ENDPOINT}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${CLIENT_ID}" \
  -d "grant_type=password" \
  -d "username=${USERNAME}" \
  -d "password=${PASSWORD}")

ACCESS_TOKEN=$(echo "${RESPONSE}" | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$')

if [ -z "${ACCESS_TOKEN}" ]; then
  echo "Error fetching access token for user '${USERNAME}'. Response:" >&2
  echo "${RESPONSE}" >&2
  exit 1
fi

echo "${ACCESS_TOKEN}"
