# Architecture Documentation — IAM & RBAC Application

## 1. System Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                                 CLIENT / BROWSER DEMO                             |
|              (Vanilla HTML5/JS Frontend at http://localhost:5000)                |
|                    OIDC Authorization Code + PKCE (S256)                          |
+-------------------+------------------------------------+--------------------------+
                    |                                    |
  1. Redirect /auth | 2. POST /token (code+verifier)     | HTTP GET /api/*
     (PKCE S256)    |    Returns JWT Tokens              | Bearer JWT Token
                    v                                    v
+-------------------+--------------------+   +-----------+--------------------------+
|   KEYCLOAK 26 IDENTITY PROVIDER        |   |     FLASK REST API (Gunicorn)            |
|             Port 8080                  |   |             Port 5000                    |
|                                        |   |                                          |
| - Realm: "company"                     |   | +--------------------------------------+ |
| - Client: "company-app" (PKCE S256)    |   | |     request_validation_pipeline      | |
| - Roles: admin, manager, employee      |   | | 1. Extract Bearer JWT                | |
| - RS256 Private Key (Signs Tokens)     |   | | 2. Fetch JWKS Public Key             | |
| - JWKS Certs Endpoint                  |   | | 3. Verify RS256 Signature            | |
+-------------------+--------------------+   | | 4. Validate Claims (iss, aud, exp)    | |
                    ^                        | | 5. Check RBAC Roles (realm_access)   | |
                    | Fetch JWKS Public Key  | | 6. Return JSON (200 / 401 / 403)     | |
                    +------------------------+ +--------------------------------------+ |
                                             +------------------------------------------+
```

## 2. Component Descriptions

| Component | Technology | Responsibilities |
| :--- | :--- | :--- |
| **Browser Demo UI** | HTML5 / Vanilla CSS / JS | Front-end application serving interactive HR demo at `http://localhost:5000`. Executes OIDC PKCE flow using Web Crypto API. |
| **Keycloak 26** | Java / Quarkus | OpenID Connect Identity Provider. Manages user directory, authentication, role assignments, and RS256 keypair. Exports JWKS public keys. |
| **Flask REST API** | Python 3.12 / Gunicorn | Resource Server. Serves static UI assets and endpoints. Validates incoming JWT bearer tokens against Keycloak JWKS, enforcing RBAC rules. |
| **PyJWKClient** | PyJWT Library | Fetches and caches Keycloak RS256 public keys from the JWKS certs endpoint to verify JWT signatures efficiently. |
| **Docker Compose** | Container Runtime | Orchestrates Keycloak and API containers, network bridges, environment variables, and data volume persistence. |

## 3. OpenID Connect (OIDC) Authentication Flow (PKCE S256)

1. **PKCE Challenge Generation**: Browser app generates a random 64-character `code_verifier` and computes `code_challenge = base64url(SHA-256(code_verifier))` using `window.crypto.subtle.digest()`.
2. **Authorization Request**: Browser redirects to Keycloak auth endpoint (`/realms/company/protocol/openid-connect/auth`) with `response_type=code`, `client_id=company-app`, `code_challenge`, `code_challenge_method=S256`, `state`, and `nonce`.
3. **User Authentication**: User logs in directly on Keycloak's hosted interface. Keycloak authenticates user, generates authorization code, and redirects back to `http://localhost:5000/?code=...&state=...`.
4. **Token Exchange**: Browser verifies state parameter matches `sessionStorage`, then sends `POST` request to Keycloak token endpoint with `code` and `code_verifier`.
5. **Token Verification**: Keycloak verifies `SHA-256(code_verifier) == code_challenge`, issues signed `access_token` and `id_token`.
6. **ID Token Nonce Validation**: Browser decodes `id_token` payload and validates that `payload.nonce` matches stored nonce before saving tokens to `sessionStorage`.
7. **API Invocation**: Browser app calls Flask API endpoints (`/api/profile`, etc.) with header `Authorization: Bearer <access_token>`.
8. **JWKS Signature & Claims Verification**: Flask API verifies token signature against Keycloak JWKS public key, checking `exp`, `iat`, `iss`, and `aud`.
9. **RBAC Authorization**: Decorator `@require_roles(*allowed_roles)` checks if `realm_access.roles` contains permitted role for target endpoint.

## 4. JWT Claims Specification

```json
{
  "exp": 1770000300,
  "iat": 1770000000,
  "jti": "b1a2c3d4-e5f6-7890-abcd-ef1234567890",
  "iss": "http://localhost:8080/realms/company",
  "aud": "company-app",
  "sub": "u1v2w3x4-y5z6-7890-abcd-ef1234567890",
  "typ": "Bearer",
  "azp": "company-app",
  "session_state": "s1t2u3v4-w5x6-7890-abcd-ef1234567890",
  "preferred_username": "alice",
  "email": "alice@company.com",
  "given_name": "Alice",
  "family_name": "Admin",
  "email_verified": true,
  "realm_access": {
    "roles": [
      "default-roles-company",
      "offline_access",
      "uma_authorization",
      "admin"
    ]
  }
}
```

## 5. Request Validation Pipeline

```
[Incoming HTTP Request]
          |
          v
Has 'Authorization: Bearer <token>' header?
   ├── NO  --> 401 missing_token ("Missing or malformed Authorization header")
   └── YES
        |
        v
Fetch RS256 Public Key via PyJWKClient.get_signing_key_from_jwt(token)?
   ├── NO / Connection Error --> 503 idp_unavailable ("Unable to reach Keycloak JWKS")
   └── YES
        |
        v
Verify Signature (RS256) & Claims (iss, aud, exp, iat)?
   ├── Expired  --> 401 token_expired ("Token has expired")
   ├── Invalid  --> 401 invalid_token ("Invalid token signature or claims")
   └── Valid
        |
        v
User has required role in 'realm_access.roles'?
   ├── NO  --> 403 forbidden ("User does not possess required role permission")
   └── YES --> 200 OK (Execute Route Logic & Return JSON)
```

## 6. Access Control Matrix

| Endpoint | Path | Allowed Roles | Employee | Manager | Admin | Anonymous |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `GET /` | `/` | Public | 200 OK | 200 OK | 200 OK | 200 OK |
| `GET /health` | `/health` | Public | 200 OK | 200 OK | 200 OK | 200 OK |
| `GET /api/public` | `/api/public` | Public | 200 OK | 200 OK | 200 OK | 200 OK |
| `GET /api/profile` | `/api/profile` | `admin`, `manager`, `employee` | 200 OK | 200 OK | 200 OK | 401 Unauthorized |
| `GET /api/reports` | `/api/reports` | `admin`, `manager` | **403 Forbidden** | 200 OK | 200 OK | 401 Unauthorized |
| `GET /api/admin/users` | `/api/admin/users` | `admin` | **403 Forbidden** | **403 Forbidden** | 200 OK | 401 Unauthorized |

## 7. Security Decisions & Controls

- **PKCE S256 Public Client Flow**: Standard OAuth 2.0 PKCE flow used for browser client authentication without embedding client secrets in static JS.
- **Strict DOM Security**: All user identity fields and server responses rendered via `textContent` to prevent DOM XSS.
- **Zero Console Token Leakage**: JWT tokens stored strictly in memory/sessionStorage without console logging.
- **Security Headers**: Served with `X-Content-Type-Options: nosniff` and strict `Content-Security-Policy`.

## 8. Local vs. Future AWS Production Deployment Path

```
LOCAL DEV (Docker Compose)                   PRODUCTION (AWS Cloud Architecture)

+--------------------------+                 +------------------------------------------------+
| Host Machine             |                 | AWS Cloud (VPC)                                |
|  - localhost:8080 (Keycl) |                 |                                                |
|  - localhost:5000 (API)  |                 |  AWS ALB (HTTPS / SSL Termination)             |
+------------+-------------+                 |    ├── auth.company.com  --> Keycloak ECS Fargate|
             |                               |    └── api.company.com   --> Flask API ECS Fargate|
             v                               |                                                |
Docker Network bridge                        |  Amazon Aurora PostgreSQL (Multi-AZ DB)        |
  - http://keycloak:8080                     |  AWS Secrets Manager & IAM Roles               |
                                             +------------------------------------------------+
```
