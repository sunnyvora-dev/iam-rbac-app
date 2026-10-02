# Project Memory & Snapshot — IAM & RBAC Application

## 1. Project Snapshot
- **Project Name**: IAM & RBAC Application
- **Stack**: Keycloak 26, Python 3.12, Flask, PyJWT, Vanilla HTML5/CSS/JS, Gunicorn, Docker Compose, Pytest
- **Current Status**: All code, configuration, Docker specs, Vanilla JS browser demo (`http://localhost:5000`), 29 unit & UI tests (100% pass), scripts, and 6 documentation files are complete!

## 2. Key Decisions Table

| Decision | Choice Made | Rationale |
| :--- | :--- | :--- |
| **Signature Algorithm** | `RS256` Only | Asymmetric cryptography allows Flask API to verify tokens using Keycloak's public key without sharing a secret. |
| **Browser Authentication** | OIDC Code + PKCE (S256) | Security standard for public client SPA applications. Eliminates embedded client secrets using Web Crypto API SHA-256 code challenge. |
| **Audience Mapping** | Dedicated Protocol Mapper | Keycloak access tokens default to `aud: ["account"]`. Adding `oidc-audience-mapper` ensures `aud: "company-app"` matches API expectation. |
| **JWKS Key Caching** | `PyJWKClient` | Caches public RSA keys locally to avoid blocking API requests with Keycloak HTTP lookups on every request. |
| **DOM Security** | Strict `textContent` | Prevents XSS attacks by avoiding `innerHTML` and raw string HTML injection. |
| **Unit Test Strategy** | Local RSA Key Pair & Fixtures | Tests generate a throwaway RSA key pair to sign tokens 100% offline, mocking `auth.get_signing_key` and UI static endpoints. |
| **Container User** | Non-root `appuser` (UID 10001) | Security best practice; prevents privilege escalation if API container is compromised. |

## 3. Critical Gotchas & Troubleshooting

1. **Incomplete User Profile Block (Keycloak 24+)**:
   - *Symptom*: User authentication returns `400 Bad Request` with `error_description: "Account is not fully set up"`.
   - *Fix*: Ensure realm JSON sets `emailVerified: true`, `firstName`, `lastName`, and credentials `temporary: false`.

2. **Missing Audience Claim Reject**:
   - *Symptom*: API returns `401 invalid_token` with log message `Audience mismatch`.
   - *Fix*: Verify Keycloak client has `oidc-audience-mapper` adding `company-app` to the access token.

3. **Issuer Host Name Mismatch (`KEYCLOAK_PUBLIC_URL` vs `KEYCLOAK_INTERNAL_URL`)**:
   - *Symptom*: JWT verification fails because token `iss` (`http://localhost:8080/realms/company`) does not match internal container URL (`http://keycloak:8080/realms/company`).
   - *Fix*: Use `KEYCLOAK_PUBLIC_URL` for token `iss` validation and `KEYCLOAK_INTERNAL_URL` for container-to-container JWKS HTTP requests.

4. **Realm JSON Auto-Import Behavior**:
   - *Symptom*: Edits to `realm-company.json` do not take effect when restarting containers.
   - *Fix*: Keycloak only imports realm JSON on fresh database initialization. Run `docker compose down -v` to reset data volume.

5. **PKCE State & Nonce Validation**:
   - *Symptom*: CSRF or replay attack risk during browser redirect.
   - *Fix*: Store random `oauth_state` and `oauth_nonce` in `sessionStorage`. Verify state on callback return and validate `id_token` nonce payload before accepting tokens.

## 4. Useful Commands Reference

```bash
# Start live Docker stack
docker compose up -d --build

# View container logs
docker compose logs -f api

# Run offline unit and UI tests (29 tests total)
pytest tests/test_unit.py tests/test_ui.py -v

# Run integration tests
pytest tests/test_integration.py -v

# Run 11-scenario automated verification script
python scripts/demo.py

# Fetch raw access token CLI
bash scripts/get_token.sh alice Alice@123

# Check JS syntax
node --check static/app.js

# Tear down stack and purge volumes
docker compose down -v
```

## 5. Interview Talking Points

- *"Why did you use RS256 instead of HS256?"* ➔ RS256 uses asymmetric cryptography. The Identity Provider (Keycloak) signs tokens with a private key, while microservices verify signatures using the public key fetched from the JWKS endpoint. This prevents microservices from needing access to sensitive signing secrets.
- *"Why PKCE S256 for the browser client?"* ➔ Browser SPAs are public clients that cannot securely store client secrets. PKCE S256 dynamically generates a one-time cryptographic code verifier and SHA-256 challenge for every authorization code request, mitigating authorization code interception attacks.
- *"How do you protect against XSS and token leaks in the frontend?"* ➔ We use Vanilla JS without external dependencies, enforce strict `textContent` DOM injection (0 `innerHTML`), prohibit logging tokens to browser console, and enforce Security Headers (`Content-Security-Policy` and `X-Content-Type-Options: nosniff`).
- *"How do you handle JWKS network latency?"* ➔ We use `PyJWKClient` which caches the public keys retrieved from `/protocol/openid-connect/certs`. Key refresh occurs automatically only if a key ID (`kid`) is rotated.

## 6. Deliverables Verification
- [x] Read all 6 documentation files in `docs/`.
- [x] Implemented `keycloak/realm-company.json` with PKCE S256 settings.
- [x] Implemented `static/index.html`, `static/style.css`, `static/app.js`.
- [x] Implemented `app/config.py`, `app/auth.py`, `app/main.py`.
- [x] Implemented `Dockerfile`, `docker-compose.yml`, `.env.example`, `.gitignore`.
- [x] Built and verified 29/29 offline unit & UI tests (`pytest tests/test_unit.py tests/test_ui.py`).
- [x] Implemented `scripts/demo.py` and `scripts/get_token.sh`.
- [x] Created `README.md` with flow diagrams, badges, access matrix, browser demo overview, and curl examples.
