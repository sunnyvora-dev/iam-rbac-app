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
- **Standard Flow Enabled**: `true` (Enables OIDC Authorization Code Flow with PKCE)
- **Direct Access Grants Enabled**: `true` (Enables Resource Owner Password Flow for demo & testing scripts)
- **Redirect URIs**: `["http://localhost:5000/*"]`
- **Post Logout Redirect URIs**: `["http://localhost:5000/*"]`
- **Web Origins**: `["http://localhost:5000"]`
- **Attributes**: `pkce.code.challenge.method: "S256"` (Enforces S256 PKCE method)
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

## 2. API & UI Endpoint Specification

### Static & UI Endpoints

#### 1. Browser Demo Page
- **Route**: `GET /`
- **Auth**: None (Public)
- **Headers**: `X-Content-Type-Options: nosniff`, `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self' http://localhost:8080; frame-ancestors 'none'`
- **Response**: Serves `static/index.html` with Vanilla JS OIDC PKCE client logic.

#### 2. Static Assets
- **Route**: `GET /static/<filename>`
- **Auth**: None (Public)
- **Response**: Serves requested CSS/JS static files from `static/` directory.

#### 3. Frontend Keycloak Configuration
- **Route**: `GET /config.json`
- **Auth**: None (Public)
- **Response (200 OK)**:
```json
{
  "keycloakUrl": "http://localhost:8080",
  "realm": "company",
  "clientId": "company-app"
}
```

### Protected & Public API Endpoints

#### 1. Public Health Check
- **Route**: `GET /health`
- **Auth**: None (Public)
- **Response (200 OK)**: `{"status": "healthy", "service": "iam-rbac-api", "version": "1.0.0"}`

#### 2. Public System Info
- **Route**: `GET /api/public`
- **Auth**: None (Public)
- **Response (200 OK)**: `{"message": "Welcome to the IAM & RBAC Public API", "auth_required": false}`

#### 3. User Profile Endpoint
- **Route**: `GET /api/profile`
- **Auth**: Bearer JWT (`admin`, `manager`, `employee`)
- **Response (200 OK)**: User profile JSON extracted from JWT claims.

#### 4. Management Reports Endpoint
- **Route**: `GET /api/reports`
- **Auth**: Bearer JWT (`admin`, `manager`)
- **Response (200 OK / 403 Forbidden)**: Management reports list.

#### 5. Admin Users Directory
- **Route**: `GET /api/admin/users`
- **Auth**: Bearer JWT (`admin`)
- **Response (200 OK / 403 Forbidden)**: System users directory.

---

## 3. UI Browser Demo Architecture (`static/`)

- **`index.html`**: Clean 900px max-width layout with responsive design, dynamic cards, user card, 1-sec token countdown, interactive endpoint test section, and security test panel.
- **`style.css`**: Design system with CSS variables, light/dark mode auto-switching (`prefers-color-scheme`), accessible button focus states, and status badges.
- **`app.js`**: Vanilla JS OIDC client implementing:
  - PKCE code generation via Web Crypto API (`window.crypto.subtle.digest('SHA-256')`).
  - OAuth state verification and ID token nonce validation.
  - Live 1-second countdown timer updating session remaining time.
  - Endpoint testing with `✓ as expected` or `⚠ expected <status>` badges.
  - Security attack simulation panel (expired token, tampered signature, role removal).
  - Strict DOM safety using `textContent` for all dynamic data injection (0 `innerHTML` calls).
  - Token storage trade-off notice in comments regarding `sessionStorage`.

---

## 4. Error Handling & HTTP Status Codes

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

## 5. Code Layout

```
iam-rbac-app/
├── app/
│   ├── __init__.py
│   ├── main.py        # Flask application factory, routes, static file serving, CSP headers
│   ├── auth.py        # JWT verification decorator, JWKS key client, role checks
│   └── config.py      # Environment variable configuration loading
├── static/
│   ├── index.html     # Vanilla HTML5 Browser Demo Page
│   ├── style.css      # Design system CSS with dark mode support
│   └── app.js         # Vanilla JS PKCE OIDC client & security test panel
├── keycloak/
│   └── realm-company.json # Keycloak 26 auto-import realm config with PKCE S256 enabled
├── tests/
│   ├── test_unit.py        # Offline unit tests using local RSA keys
│   ├── test_ui.py          # UI static route & CSP security header tests
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
