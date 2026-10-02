# Phased Task Checklist — IAM & RBAC Application

## Phase 0: Documentation & Design
- [x] Create `docs/prd.md` with product requirements and goals.
- [x] Create `docs/architecture.md` with system diagrams and OIDC flows.
- [x] Create `docs/rules.md` with security and testing guidelines.
- [x] Create `docs/design.md` with Keycloak and API specifications.
- [x] Create `docs/task.md` with task checklist.
- [x] Create `docs/memory.md` with project decisions and interview notes.

## Phase 1: Keycloak Configuration
- [x] Create `keycloak/realm-company.json` with `company` realm.
- [x] Define roles `admin`, `manager`, `employee`.
- [x] Create `company-app` public client with direct access grants & PKCE S256 enabled.
- [x] Add `oidc-audience-mapper` protocol mapper for `"company-app"`.
- [x] Configure demo users (`alice`, `bob`, `charlie`) with verified emails and active passwords.

## Phase 2: Core Flask REST API
- [x] Create `requirements.txt` and `requirements-dev.txt`.
- [x] Implement `app/config.py` for environment variables.
- [x] Implement `app/auth.py` with `@require_roles` decorator, PyJWT verification, and error handling.
- [x] Implement `app/main.py` with endpoints (`/`, `/static/<filename>`, `/config.json`, `/health`, `/api/public`, `/api/profile`, `/api/reports`, `/api/admin/users`) and JSON error handlers.

## Phase 3: Docker & Environment
- [x] Create `.env.example` and `.gitignore`.
- [x] Create non-root `Dockerfile` with static asset copy and Gunicorn WSGI runner.
- [x] Create `docker-compose.yml` with `keycloak` and `api` services.

## Phase 4: Verification & Testing
- [x] Write offline unit test suite in `tests/test_unit.py` (24/24 passed 100% offline).
- [x] Write integration test suite in `tests/test_integration.py`.
- [x] Create automated demo script `scripts/demo.py` (11 scenarios).
- [x] Create token retrieval script `scripts/get_token.sh`.
- [x] Execute pytest suite and verify 100% pass rate.

## Phase 5: Primary Project Documentation
- [x] Create root `README.md` with badges, diagrams, quickstart, access matrix, and curl examples.

## Phase 6: Browser Demo Page & UI Security Tests
- [x] Update `keycloak/realm-company.json` for PKCE S256 (`pkce.code.challenge.method: S256`, `post.logout.redirect.uris: http://localhost:5000/*`).
- [x] Create `static/index.html` with modern UI layout, login button, demo users table, user card, countdown timer, endpoint tests, and security attack panel.
- [x] Create `static/style.css` with CSS custom properties, responsive design, dark mode, and accessibility.
- [x] Create `static/app.js` with Vanilla JS PKCE S256 OIDC client, Web Crypto API digest, state/nonce validation, strict `textContent` DOM safety, and security attack tests.
- [x] Update `app/main.py` to serve `/`, `/static/<filename>`, `/config.json`, and set CSP & `X-Content-Type-Options: nosniff` security headers.
- [x] Update `Dockerfile` to copy `static` directory.
- [x] Write `tests/test_ui.py` for static routes, CSP headers, config endpoint, and 404 handler.
- [x] Run full pytest suite (`pytest tests/test_unit.py tests/test_ui.py -v`) and verify 29/29 tests pass.
- [x] Update documentation suite (`README.md`, `docs/prd.md`, `docs/architecture.md`, `docs/design.md`, `docs/rules.md`, `docs/task.md`, `docs/memory.md`).
