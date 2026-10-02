# Architecture Documentation — IAM & RBAC Application

## 1. System Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                                 CLIENT / DEMO SCRIPT                              |
|                      (Obtains JWT tokens via OIDC Password Grant)                 |
+----------------------------------------+------------------------------------------+
                                         |
                       Bearer JWT Token  | HTTP GET /api/*
                                         v
+-----------------------------------------------------------------------------------+
|                               FLASK REST API (Gunicorn)                           |
|                                     Port 5000                                     |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                            request_validation_pipeline                      |  |
|  |                                                                             |  |
|  |  1. Extract Bearer Token  -->  2. Fetch Public Key  -->  3. Verify RS256    |  |
|  |     (Authorization header)        (Keycloak JWKS)          Signature        |  |
|  |                                                                             |  |
|  |  4. Validate Claims       -->  5. Check RBAC Roles   -->  6. Return JSON    |  |
|  |     (iss, aud, exp, iat)          (realm_access.roles)     200 / 401 / 403   |  |
|  +-------------------------------------+---------------------------------------+  |
+----------------------------------------|------------------------------------------+
                                         |
                                         | Fetch JWKS Public Key
                                         | (http://keycloak:8080/realms/company/protocol/openid-connect/certs)
                                         v
+-----------------------------------------------------------------------------------+
|                             KEYCLOAK 26 IDENTITY PROVIDER                         |
|                                     Port 8080                                     |
|                                                                                   |
|   - Realm: "company"                                                              |
|   - Roles: admin, manager, employee                                               |
|   - Client: "company-app" (Audience Mapper configured)                            |
|   - RS256 Private Key (Signs JWT tokens)                                          |
|   - JWKS Endpoint (Publishes RS256 Public Keys)                                   |
+-----------------------------------------------------------------------------------+
```

## 2. Component Descriptions

| Component | Technology | Responsibilities |
| :--- | :--- | :--- |
| **Keycloak 26** | Java / Quarkus | OpenID Connect Identity Provider. Manages user directory, authentication, role assignments, and RS256 keypair. Exports JWKS public keys. |
| **Flask REST API** | Python 3.12 / Gunicorn | Resource Server. Validates incoming JWT bearer tokens against Keycloak JWKS, enforces role-based access control, and serves API endpoints. |
| **PyJWKClient** | PyJWT Library | Fetches and caches Keycloak RS256 public keys from the JWKS certs endpoint to verify JWT signatures efficiently. |
| **Docker Compose** | Container Runtime | Orchestrates Keycloak and API containers, network bridges, environment variables, and data volume persistence. |

## 3. OpenID Connect (OIDC) Authentication Flow

1. **Token Request**: Client sends authentication request to Keycloak token endpoint (`/realms/company/protocol/openid-connect/token`) with username and password.
2. **Token Generation**: Keycloak validates credentials, attaches assigned realm roles (`realm_access.roles`) and target audience (`company-app`), and signs the JWT using its private RSA key.
3. **Token Response**: Keycloak returns JSON payload containing `access_token` (JWT, RS256), `expires_in` (300s), and `token_type` (`Bearer`).
4. **API Request**: Client sends HTTP request to Flask API with header `Authorization: Bearer <access_token>`.
5. **JWKS Key Fetching**: Flask API calls Keycloak JWKS endpoint (`/realms/company/protocol/openid-connect/certs`) to obtain the matching RS256 public key (cached after first retrieval).
6. **Signature Verification & Validation**: PyJWT decodes and verifies the token signature using the public key, validating `exp`, `iat`, `iss`, and `aud` claims.
7. **RBAC Authorization**: Decorator `@require_roles(*allowed_roles)` checks if `realm_access.roles` contains at least one allowed role.
8. **Response**: If authorized, returns JSON response (200 OK); otherwise returns structured JSON error (401 Unauthorized or 403 Forbidden).

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

| Endpoint | Allowed Roles | Employee | Manager | Admin | Anonymous |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `GET /health` | Public | 200 OK | 200 OK | 200 OK | 200 OK |
| `GET /api/public` | Public | 200 OK | 200 OK | 200 OK | 200 OK |
| `GET /api/profile` | `admin`, `manager`, `employee` | 200 OK | 200 OK | 200 OK | 401 Unauthorized |
| `GET /api/reports` | `admin`, `manager` | **403 Forbidden** | 200 OK | 200 OK | 401 Unauthorized |
| `GET /api/admin/users` | `admin` | **403 Forbidden** | **403 Forbidden** | 200 OK | 401 Unauthorized |

## 7. Local vs. Future AWS Production Deployment Path

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
