# Engineering Rules & Guidelines — IAM & RBAC Application

## 1. Security Rules (Non-Negotiable)
1. **Never Decode Without Verification**: Never decode a JWT using `options={"verify_signature": False}` in production code. Signature verification using RS256 is mandatory.
2. **Explicit Algorithm Constraint**: Always specify `algorithms=["RS256"]` explicitly during `jwt.decode()`. Unsecure algorithms (`HS256`, `none`) MUST be rejected.
3. **Mandatory Claim Validation**: Always enforce validation of `exp` (expiration), `iat` (issued at), `iss` (issuer), and `aud` (audience).
4. **Distinguish Authentication vs. Authorization Errors**:
   - `401 Unauthorized`: Returned when authentication fails (missing token, invalid signature, expired token, malformed header).
   - `403 Forbidden`: Returned when user is authenticated successfully, but lacks required roles for the requested resource.
5. **Zero Token Leaks in Logs**: Never log full JWT tokens, authorization headers, private keys, or raw user passwords. Log only usernames, user IDs, and assigned role lists.
6. **Least Privilege Non-Root Container**: The API container must run under a unprivileged system user (`appuser` with UID 10001), never `root`.

## 2. Code Rules
1. **Clean Code & Type Hints**: All Python modules must use Python 3.12 syntax, type hints, docstrings, and clean error handling.
2. **Explicit Error Formats**: All error responses from the API must conform to the standard JSON schema: `{"error": "<code>", "message": "<text>"}`.
3. **Role Constants**: Role strings (`ADMIN = "admin"`, `MANAGER = "manager"`, `EMPLOYEE = "employee"`) must be defined as central constants in `app/auth.py`.
4. **Decoupled Key Retrieval**: Key retrieval must be encapsulated in a dedicated function `get_signing_key(token)` so that unit test suites can easily monkeypatch local RSA test keys without touching application logic.

## 3. Testing Rules
1. **100% Offline Unit Tests**: Unit tests (`tests/test_unit.py`) must run 100% offline without requiring a live Keycloak server. Tests generate a local RSA key pair to sign test tokens and mock `auth.get_signing_key`.
2. **Matrix Coverage**: Every endpoint x role combination must be explicitly tested in both positive and negative authorization test cases.
3. **Attack Surface Coverage**: Unit tests must explicitly cover forged signatures, tampered payloads, `alg=none`, expired tokens, wrong issuers, wrong audiences, and missing required claims.
4. **Clean Integration Skipping**: Integration tests (`tests/test_integration.py`) must gracefully auto-skip if the live stack (`http://localhost:5000/health` or Keycloak) is unreachable.

## 4. Documentation & Git Rules
1. **Write Docs Before Code**: All documentation files (`docs/prd.md`, `docs/architecture.md`, `docs/rules.md`, `docs/design.md`, `docs/task.md`, `docs/memory.md`) must be written prior to implementation.
2. **Conventional Commits**: Commit messages must follow conventional commit guidelines (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).
3. **Definition of Done**: A feature or phase is considered DONE only when:
   - Code is written and clean.
   - All unit tests pass (`pytest tests/test_unit.py`).
   - Integration & demo script (`python scripts/demo.py`) pass 11/11.
   - `task.md` and `memory.md` are updated to reflect the new state.
