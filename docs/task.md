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
- [x] Create `company-app` public client with direct access grants enabled.
- [x] Add `oidc-audience-mapper` protocol mapper for `"company-app"`.
- [x] Configure demo users (`alice`, `bob`, `charlie`) with verified emails and active passwords.

## Phase 2: Core Flask REST API
- [x] Create `requirements.txt` and `requirements-dev.txt`.
- [x] Implement `app/config.py` for environment variables.
- [x] Implement `app/auth.py` with `@require_roles` decorator, PyJWT verification, and error handling.
- [x] Implement `app/main.py` with endpoints (`/health`, `/api/public`, `/api/profile`, `/api/reports`, `/api/admin/users`) and JSON error handlers.

## Phase 3: Docker & Environment
- [x] Create `.env.example` and `.gitignore`.
- [x] Create non-root `Dockerfile` with Gunicorn WSGI runner.
- [x] Create `docker-compose.yml` with `keycloak` and `api` services.

## Phase 4: Verification & Testing
- [x] Write offline unit test suite in `tests/test_unit.py` (24/24 passed 100% offline).
- [x] Write integration test suite in `tests/test_integration.py`.
- [x] Create automated demo script `scripts/demo.py` (11 scenarios).
- [x] Create token retrieval script `scripts/get_token.sh`.
- [x] Execute pytest suite and verify 100% pass rate (24/24 passed).
- [~] Run `docker compose up --build` and verify 11/11 PASS on `scripts/demo.py` (Manual container spin-up step by user).

## Phase 5: Primary Project Documentation
- [x] Create root `README.md` with badges, diagrams, quickstart, access matrix, and curl examples.
