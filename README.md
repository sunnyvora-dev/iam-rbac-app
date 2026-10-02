# IAM & RBAC Application — Keycloak OIDC & Flask REST API

A portfolio-grade **Identity and Access Management (IAM)** and **Role-Based Access Control (RBAC)** architecture demonstrating enterprise security best practices. The system decouples identity management to a Keycloak 26 OpenID Connect (OIDC) server, features a **vanilla JavaScript browser demo page with OIDC PKCE S256 authentication**, and enforces asymmetric RS256 JWT signature verification and role-based authorization inside a Python 3.12 Flask REST API.

![Keycloak 26](https://img.shields.io/badge/Keycloak-26.0.0-blue?logo=keycloak)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?logo=flask)
![OIDC PKCE](https://img.shields.io/badge/OIDC-PKCE%20S256-green?logo=openid)
![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v3.8-2496ED?logo=docker)
![Pytest](https://img.shields.io/badge/Pytest-100%25%20Pass-0A9EDC?logo=pytest)
![RS256 JWT](https://img.shields.io/badge/JWT-RS256%20Asymmetric-000000?logo=jsonwebtokens)

---

## 🌐 Browser Demo Interface (http://localhost:5000)

The application includes an interactive browser demo interface at **`http://localhost:5000`** designed for HR and technical reviewers to test the complete identity lifecycle:

- 🔐 **OIDC Authorization Code Flow + PKCE (S256)**: Secure client-side authentication without client secrets using Web Crypto API.
- ⏱️ **Live Session Countdown Timer**: Visual 1-second countdown showing token expiration with automatic UI state reset on expiration.
- 🎯 **Interactive RBAC Endpoint Testing**: One-click API invocation (`/api/public`, `/api/profile`, `/api/reports`, `/api/admin/users`) with expected status badges.
- 🛡️ **Built-in Security Attack Test Suite**:
  1. **Expired Token Test**: Sends an expired token to demonstrate 401 Unauthorized handling.
  2. **Tampered Signature Test**: Modifies token signature bytes to test RS256 signature verification rejection.
  3. **Privilege Escalation Test**: Strips administrative roles from token payload to verify backend RBAC enforcement.
- 🔒 **Zero Token Console Logging**: Strictly zero token values exposed in browser developer tools or console.
- 🛡️ **Security Headers**: Served with `X-Content-Type-Options: nosniff` and strict `Content-Security-Policy`.

---

## 📐 Architecture & Authentication Flow

```
+------------------+                    +------------------+                   +--------------------+
|  Browser Client  |                    | Keycloak IdP 26  |                   |  Flask REST API    |
| (http://localhost|                    | (http://localhost|                   | (http://localhost  |
|      :5000)      |                    |      :8080)      |                   |      :5000)        |
+--------+---------+                    +--------+---------+                   +---------+----------+
         |                                       |                                       |
         | 1. Redirect to /auth (PKCE S256)      |                                       |
         +-------------------------------------->|                                       |
         | 2. User Authenticates & Consents      |                                       |
         | 3. Redirect back with ?code=          |                                       |
         |<--------------------------------------+                                       |
         |                                       |                                       |
         | 4. POST /token (code + code_verifier) |                                       |
         +-------------------------------------->|                                       |
         | 5. Returns access_token & id_token    |                                       |
         |<--------------------------------------+                                       |
         |                                                                               |
         | 6. GET /api/reports (Header: Bearer <JWT>)                                    |
         +------------------------------------------------------------------------------>|
         |                                                                               |
         |                                 7. GET /certs (Fetch JWKS Public Key)         |
         |                                 +-------------------------------------------->|
         |                                 |<--------------------------------------------+
         |                                                                               |
         |                                 8. Verify RS256 Signature & Claims (iss, aud) |
         |                                 9. Check RBAC Role in realm_access.roles       |
         | 10. Returns JSON Data (200 OK / 403 Forbidden)                                |
         |<------------------------------------------------------------------------------+
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
# 1. Start Keycloak and Flask API containers
docker compose up -d --build

# 2. Run the 100% offline Pytest test suite (unit + UI tests)
pytest tests/test_unit.py tests/test_ui.py -v

# 3. Open http://localhost:5000 in your browser to experience the demo!
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

### 1. Obtain Access Token via Keycloak OIDC Password Grant (Testing CLI)
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

- [x] **OIDC Authorization Code Flow + PKCE (S256)**: Front-end uses SHA-256 code challenge for public client security.
- [x] **Asymmetric Signature Verification (RS256 Only)**: Unsecure algorithms (`HS256`, `none`) strictly rejected.
- [x] **Dynamic Public Key Retrieval**: Public keys fetched from Keycloak JWKS (`/protocol/openid-connect/certs`) via cached `PyJWKClient`.
- [x] **Strict Claim Validation**: Mandatory validation of `exp` (expiration), `iat` (issued at), `iss` (issuer), `aud` (`company-app`), and `nonce`.
- [x] **Decoupled Auth & Role Check**: Decorator `@require_roles(*roles)` parses `realm_access.roles` claim.
- [x] **DOM Security (Strict textContent)**: UI code uses exclusively `textContent` to eliminate XSS vulnerabilities.
- [x] **Non-Root Container Hardening**: Docker container runs as unprivileged `appuser` (UID 10001).
- [x] **Zero Token Leak Logging**: Application logs user identities and role lists, never raw JWT tokens or secrets.
- [x] **Security Headers**: Served with `X-Content-Type-Options: nosniff` and `Content-Security-Policy`.

---

## 🧪 Testing Suite & Verification

### 1. Offline Unit & UI Tests
Run 100% offline unit and UI tests:
```bash
pytest tests/test_unit.py tests/test_ui.py -v
```

### 2. Live Integration Tests
Run integration tests against running Keycloak & API stack:
```bash
pytest tests/test_integration.py -v
```

---

## 📁 Project Structure

```
iam-rbac-app/
├── app/
│   ├── __init__.py
│   ├── config.py         # Keycloak URLs, Realm, Client ID config
│   ├── auth.py           # RS256 JWT verification decorator & JWKS client
│   └── main.py           # Flask REST API routes & JSON error handlers
├── static/
│   ├── index.html        # Vanilla HTML5 Browser Demo Page
│   ├── style.css         # Modern CSS design system & dark theme
│   └── app.js            # PKCE S256 OIDC client & security test panel
├── keycloak/
│   └── realm-company.json # Keycloak 26 auto-import realm config (PKCE enabled)
├── tests/
│   ├── test_unit.py       # 100% offline Pytest unit test suite
│   ├── test_ui.py         # UI static route & CSP security header tests
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

## What I learned

<!-- Keep this section empty for personalized portfolio notes -->
