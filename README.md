# IAM & RBAC Application — Keycloak OIDC & Flask REST API

A portfolio-grade **Identity and Access Management (IAM)** and **Role-Based Access Control (RBAC)** architecture demonstrating enterprise security best practices. The system decouples identity management to a Keycloak 26 OpenID Connect (OIDC) server and enforces asymmetric RS256 JWT signature verification and role-based authorization inside a Python 3.12 Flask REST API.

![Keycloak 26](https://img.shields.io/badge/Keycloak-26.0.0-blue?logo=keycloak)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?logo=flask)
![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v3.8-2496ED?logo=docker)
![Pytest](https://img.shields.io/badge/Pytest-100%25%20Pass-0A9EDC?logo=pytest)
![RS256 JWT](https://img.shields.io/badge/JWT-RS256%20Asymmetric-000000?logo=jsonwebtokens)

---

## 📐 Architecture & Authentication Flow

```
+---------------+                    +------------------+                   +--------------------+
| Client / User |                    | Keycloak IdP 26  |                   |  Flask REST API    |
+-------+-------+                    +--------+---------+                   +---------+----------+
        |                                     |                                       |
        | 1. POST /token (User/Pass)          |                                       |
        +------------------------------------>|                                       |
        | 2. Returns RS256 Signed Access Token|                                       |
        |<------------------------------------+                                       |
        |                                                                             |
        | 3. GET /api/reports (Header: Bearer <JWT>)                                  |
        +---------------------------------------------------------------------------->|
        |                                                                             |
        |                               4. GET /certs (Fetch JWKS Public Key)         |
        |                               +-------------------------------------------->|
        |                               |<--------------------------------------------+
        |                                                                             |
        |                               5. Verify RS256 Signature & Claims (iss, aud) |
        |                               6. Check RBAC Role in realm_access.roles       |
        | 7. Returns JSON Data (200 OK / 403 Forbidden)                               |
        |<----------------------------------------------------------------------------+
```

---

## 📊 Role-Based Access Control (RBAC) Matrix

| Endpoint | Path | Allowed Roles | Employee | Manager | Admin | Anonymous |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Health Check** | `GET /health` | Public | 200 OK | 200 OK | 200 OK | 200 OK |
| **Public Info** | `GET /api/public` | Public | 200 OK | 200 OK | 200 OK | 200 OK |
| **User Profile** | `GET /api/profile` | `admin`, `manager`, `employee` | 200 OK | 200 OK | 200 OK | 401 Unauthorized |
| **Management Reports** | `GET /api/reports` | `admin`, `manager` | **403 Forbidden** | 200 OK | 200 OK | 401 Unauthorized |
| **Admin User Directory**| `GET /api/admin/users` | `admin` | **403 Forbidden** | **403 Forbidden** | 200 OK | 401 Unauthorized |

---

## 🚀 Quick Start (3 Commands)

```bash
# 1. Start the Keycloak and Flask API containers
docker compose up -d --build

# 2. Wait 20 seconds for Keycloak to initialize, then run the 11-scenario automated verification suite
python scripts/demo.py

# 3. Run the 100% offline Pytest unit test suite
pytest tests/test_unit.py -v
```

---

## 👥 Pre-Configured Demo Users

The Keycloak realm (`realm-company.json`) comes auto-imported with 3 pre-configured users (`emailVerified: true`, active non-temporary credentials):

| Username | Password | Assigned Realm Roles | Accessible Endpoints |
| :--- | :--- | :--- | :--- |
| **`alice`** | `Alice@123` | `admin`, `employee` | `/api/profile`, `/api/reports`, `/api/admin/users` |
| **`bob`** | `Bob@123` | `manager`, `employee` | `/api/profile`, `/api/reports` |
| **`charlie`** | `Charlie@123` | `employee` | `/api/profile` |

---

## 💻 Manual `curl` Usage Examples

### 1. Obtain Access Token via Keycloak OIDC Password Grant
```bash
# Get access token for Alice (Admin)
TOKEN=$(curl -s -X POST "http://localhost:8080/realms/company/protocol/openid-connect/token" \
  -d "client_id=company-app" \
  -d "grant_type=password" \
  -d "username=alice" \
  -d "password=Alice@123" | jq -r '.access_token')

echo $TOKEN
```

### 2. Access Admin Endpoints as Alice (Admin) ➔ 200 OK
```bash
curl -i -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/admin/users
```

### 3. Attempt Admin Access as Charlie (Employee) ➔ 403 Forbidden
```bash
# Get token for Charlie
CHARLIE_TOKEN=$(curl -s -X POST "http://localhost:8080/realms/company/protocol/openid-connect/token" \
  -d "client_id=company-app" \
  -d "grant_type=password" \
  -d "username=charlie" \
  -d "password=Charlie@123" | jq -r '.access_token')

# Attempt admin access
curl -i -H "Authorization: Bearer $CHARLIE_TOKEN" http://localhost:5000/api/admin/users
```

---

## 🛡️ Security Audit Checklist & Controls

- [x] **Asymmetric Signature Verification (RS256 Only)**: Unsecure algorithms (`HS256`, `none`) are rejected.
- [x] **Dynamic Public Key Retrieval**: Public keys fetched from Keycloak JWKS (`/protocol/openid-connect/certs`) via cached `PyJWKClient`.
- [x] **Strict Claim Validation**: Mandatory validation of `exp` (expiration), `iat` (issued at), `iss` (issuer), and `aud` (`company-app`).
- [x] **Decoupled Auth & Role Check**: Decorator `@require_roles(*roles)` parses `realm_access.roles` claim.
- [x] **Non-Root Container Hardening**: Docker container runs as unprivileged `appuser` (UID 10001).
- [x] **Zero Token Leak Logging**: Application logs user identities and role lists, never raw JWT tokens or secrets.
- [x] **Standard Error Payloads**: Structured JSON error formatting (`{"error": "...", "message": "..."}`).

---

## 🧪 Testing Suite & Manual Token Expiration Verification

### 1. Offline Unit Tests
Run 100% offline unit tests (generates throwaway local RSA key pairs, no Keycloak server needed):
```bash
pytest tests/test_unit.py -v
```

### 2. Live Integration Tests
Run integration tests against running Keycloak & API stack:
```bash
pytest tests/test_integration.py -v
```

### 3. Manual Expired-Token Verification Test
To manually test expired token rejection (`401 token_expired`):
1. In `keycloak/realm-company.json`, temporarily edit `"accessTokenLifespan": 5`.
2. Re-import realm: `docker compose down -v && docker compose up -d --build`.
3. Fetch a token for `alice`: `TOKEN=$(bash scripts/get_token.sh alice Alice@123)`.
4. Wait 10 seconds.
5. Execute request: `curl -i -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/profile`.
6. **Expected Output**: HTTP 401 Unauthorized `{"error": "token_expired", "message": "Token has expired"}`.

---

## 📁 Project Structure

```
iam-rbac-app/
├── app/
│   ├── __init__.py
│   ├── config.py         # Keycloak URLs, Realm, Client ID config
│   ├── auth.py           # RS256 JWT verification decorator & JWKS client
│   └── main.py           # Flask REST API routes & JSON error handlers
├── keycloak/
│   └── realm-company.json # Keycloak 26 auto-import realm config
├── tests/
│   ├── test_unit.py       # 100% offline Pytest unit test suite
│   └── test_integration.py# Live integration test suite
├── scripts/
│   ├── demo.py           # 11-scenario automated verification script
│   └── get_token.sh      # CLI token retrieval script
├── docs/                 # Documentation suite
│   ├── prd.md            # Product Requirements Document
│   ├── architecture.md   # Architecture, OIDC flows, claims spec
│   ├── rules.md          # Security, coding, and testing rules
│   ├── design.md         # Technical design & API endpoint spec
│   ├── task.md           # Phased task checklist
│   └── memory.md         # Project memory & interview notes
├── Dockerfile            # Non-root multi-stage Python 3.12 Dockerfile
├── docker-compose.yml    # Docker Compose orchestration
├── requirements.txt      # Production runtime dependencies
├── requirements-dev.txt  # Test dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
└── README.md             # Primary project documentation
```

---

## ⚠️ Security Notice: Password Grant vs. Production Auth Code + PKCE

> [!NOTE]
> Resource Owner Password Credentials Grant (`grant_type=password`) used in `scripts/demo.py` and `scripts/get_token.sh` is enabled for **local automated testing and CLI demonstration purposes only**. Production frontend and mobile applications MUST use OpenID Connect **Authorization Code Flow with PKCE (Proof Key for Code Exchange)** where users authenticate directly on Keycloak's hosted login page without exposing credentials to application code.

---

## What I learned

<!-- Keep this section empty for personalized portfolio notes -->
