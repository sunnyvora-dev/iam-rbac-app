# Technical Design Specification — IAM & RBAC Application

## 1. Keycloak Realm Configuration Design (`keycloak/realm-company.json`)

### Realm Metadata
- **Realm Name**: `company`
- **Enabled**: `true`
- **Access Token Lifespan**: `300` seconds (5 minutes)
- **SSL Requirement**: `none` (local development mode)

### Roles Definition
- **Realm Roles**:
  - `admin`: High-privilege administrative role.
  - `manager`: Middle-management role.
  - `employee`: Standard baseline employee role.

### Client Configuration (`company-app`)
- **Client ID**: `company-app`
- **Enabled**: `true`
- **Protocol**: `openid-connect`
- **Public Client**: `true`
- **Standard Flow Enabled**: `true`
- **Direct Access Grants Enabled**: `true` (Enables Resource Owner Password Flow for demo & testing scripts)
- **Redirect URIs**: `["http://localhost:5000/*"]`
- **Web Origins**: `["+"]`
- **Protocol Mappers**:
  - **Mapper Name**: `oidc-audience-mapper`
  - **Mapper Type**: `oidc-audience-mapper`
  - **Config**: `included.client.audience: "company-app"`, `included.custom.audience: "company-app"`, `id.token.claim: "false"`, `access.token.claim: "true"` (Ensures access token `aud` contains `"company-app"`).

### Pre-Configured Demo Users
All users have `emailVerified: true` and non-temporary credentials (preventing Keycloak 24+ incomplete profile blocks):

| Username | Password | Email | First Name | Last Name | Realm Roles Assigned |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **alice** | `Alice@123` | `alice@company.com` | Alice | Admin | `admin`, `employee` |
| **bob** | `Bob@123` | `bob@company.com` | Bob | Manager | `manager`, `employee` |
| **charlie** | `Charlie@123` | `charlie@company.com` | Charlie | Employee | `employee` |

---

## 2. API Design & Endpoints

### Endpoint Specification

#### 1. Public Health Check
- **Route**: `GET /health`
- **Auth**: None (Public)
- **Response (200 OK)**:
```json
{
  "status": "healthy",
  "service": "iam-rbac-api",
  "version": "1.0.0"
}
```

#### 2. Public System Info
- **Route**: `GET /api/public`
- **Auth**: None (Public)
- **Response (200 OK)**:
```json
{
  "message": "Welcome to the IAM & RBAC Public API",
  "auth_required": false
}
```

#### 3. User Profile
- **Route**: `GET /api/profile`
- **Auth**: Required (`admin`, `manager`, or `employee`)
- **Response (200 OK)**:
```json
{
  "username": "alice",
  "email": "alice@company.com",
  "name": "Alice Admin",
  "roles": ["admin", "employee"]
}
```

#### 4. Management Reports
- **Route**: `GET /api/reports`
- **Auth**: Required (`admin` or `manager`)
- **Response (200 OK)**:
```json
{
  "reports": [
    {"id": "REP-101", "title": "Q3 Access Audit Report", "classification": "CONFIDENTIAL"},
    {"id": "REP-102", "title": "Role Usage Analytics", "classification": "INTERNAL"}
  ],
  "accessed_by": "bob",
  "role_used": "manager"
}
```

#### 5. Administrative User Directory
- **Route**: `GET /api/admin/users`
- **Auth**: Required (`admin` only)
- **Response (200 OK)**:
```json
{
  "users": [
    {"username": "alice", "email": "alice@company.com", "role": "admin"},
    {"username": "bob", "email": "bob@company.com", "role": "manager"},
    {"username": "charlie", "email": "charlie@company.com", "role": "employee"}
  ],
  "total": 3
}
```

---

## 3. Standard JSON Error Schema

All error responses return `Content-Type: application/json` with the format:
```json
{
  "error": "error_code_identifier",
  "message": "Human-readable explanation of error"
}
```

| HTTP Status | Error Code (`error`) | Cause |
| :--- | :--- | :--- |
| **401 Unauthorized** | `missing_token` | Missing or malformed `Authorization: Bearer <token>` header. |
| **401 Unauthorized** | `token_expired` | JWT token timestamp `exp` is in the past. |
| **401 Unauthorized** | `invalid_token` | Invalid signature, mismatched issuer/audience, or malformed claims. |
| **403 Forbidden** | `forbidden` | User is authenticated but lacks required role in `realm_access.roles`. |
| **404 Not Found** | `not_found` | Requested URI endpoint does not exist. |
| **405 Method Not Allowed**| `method_not_allowed` | Requested HTTP method is not supported for endpoint. |
| **500 Server Error** | `internal_error` | Unexpected application exception. |
| **503 Service Unavailable**| `idp_unavailable` | Failed to reach Keycloak JWKS endpoint (`PyJWKClientConnectionError`). |

---

## 4. Code Layout

```
iam-rbac-app/
├── app/
│   ├── __init__.py
│   ├── main.py        # Flask application factory, routes, and error handlers
│   ├── auth.py        # JWT verification decorator, JWKS key client, role checks
│   └── config.py      # Environment variable configuration loading
├── keycloak/
│   └── realm-company.json # Exported realm configuration JSON
├── tests/
│   ├── test_unit.py        # Offline unit tests using local RSA keys
│   └── test_integration.py # Live integration tests against Keycloak stack
├── scripts/
│   ├── demo.py        # 11-scenario automated verification script
│   └── get_token.sh   # CLI helper script for fetching Keycloak access tokens
├── docs/              # Documentation suite (6 files)
├── Dockerfile         # Non-root multi-stage Python 3.12 container file
├── docker-compose.yml # Orchestrates Keycloak 26 and API services
├── requirements.txt   # Runtime dependencies
├── requirements-dev.txt # Test dependencies
├── .env.example       # Example environment variable file
├── .gitignore         # Git ignore rules
└── README.md          # Primary project overview & documentation
```

---

## 5. Demo Script Design (`scripts/demo.py`)

The automated demo script executes 11 distinct test scenarios using real OIDC password grant tokens against the live stack:

1. `GET /health` (Public -> 200 OK)
2. `GET /api/public` (Public -> 200 OK)
3. `GET /api/profile` as **Alice (Admin)** -> 200 OK
4. `GET /api/profile` as **Bob (Manager)** -> 200 OK
5. `GET /api/profile` as **Charlie (Employee)** -> 200 OK
6. `GET /api/reports` as **Alice (Admin)** -> 200 OK
7. `GET /api/reports` as **Bob (Manager)** -> 200 OK
8. `GET /api/reports` as **Charlie (Employee)** -> **403 Forbidden**
9. `GET /api/admin/users` as **Alice (Admin)** -> 200 OK
10. `GET /api/admin/users` as **Bob (Manager)** -> **403 Forbidden**
11. `GET /api/admin/users` as **Charlie (Employee)** -> **403 Forbidden**

Outputs a clean ANSI-colored table summarizing status codes and PASS/FAIL metrics, exiting with code 0 if 11/11 scenarios pass.
