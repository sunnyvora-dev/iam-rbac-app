# Product Requirements Document (PRD) — IAM & RBAC Application

## 1. Overview
The IAM & RBAC Application is a enterprise-grade Identity & Access Management and Role-Based Access Control service. It decouples authentication and identity management to Keycloak (OIDC / OAuth 2.0) while enforcing fine-grained RS256 JWT validation and role-based endpoint authorization inside a lightweight Python 3.12 Flask REST API.

## 2. Problem Statement
Monolithic applications often embed user registration, password hashing, session tracking, and role checks directly into application code. This leads to security vulnerabilities, weak token handling, lack of central auditability, and poor scalability. Organizations require a centralized OpenID Connect (OIDC) Identity Provider (IdP) with standardized RS256 JWT validation and strict, role-scoped API access control.

## 3. Goals
- Centralize authentication via Keycloak 26 using OpenID Connect (OIDC).
- Enforce stateless RS256 JWT signature verification using public keys fetched dynamically from Keycloak's JWKS endpoint.
- Provide Role-Based Access Control (RBAC) with three distinct roles: `admin`, `manager`, and `employee`.
- Provide a non-root containerized deployment via Docker Compose with auto-imported realm configurations.
- Achieve 100% test coverage for JWT validation edge cases (expired tokens, forged signatures, wrong issuer/audience, algorithm tampering).

## 4. Non-Goals
- Building a custom user registration UI or password reset flow in the Flask API (Keycloak handles all user account management).
- Supporting legacy symmetric (HS256) JWT signatures in production APIs.
- Storing passwords or user credentials in the Flask application database.

## 5. User Roles & Access Hierarchy
- **Admin (`admin`)**: Superuser with full system access. Can view profile, reports, and administrative user lists.
- **Manager (`manager`)**: Middle management role. Can view profile and management reports. Forbidden from admin user management.
- **Employee (`employee`)**: Standard user role. Can only view personal profile. Forbidden from reports and admin management.

## 6. Functional Requirements
- **FR1 (Public Health Check)**: `GET /health` returns JSON `{"status": "healthy"}` without authentication.
- **FR2 (Public Info Endpoint)**: `GET /api/public` returns general system information without authentication.
- **FR3 (Profile Endpoint)**: `GET /api/profile` requires valid JWT token containing `admin`, `manager`, or `employee` role. Returns user details extracted from claims.
- **FR4 (Reports Endpoint)**: `GET /api/reports` requires valid JWT containing `admin` or `manager` role. Returns 403 Forbidden for `employee`.
- **FR5 (Admin Users Endpoint)**: `GET /api/admin/users` requires valid JWT containing `admin` role. Returns 403 Forbidden for `manager` and `employee`.
- **FR6 (Standard Error Payload)**: All authentication and authorization failures return structured JSON `{"error": "<code>", "message": "<text>"}` with HTTP status 401, 403, 404, 405, or 503.

## 7. Non-Functional Requirements
- **NFR1 (Security)**: Cryptographic signature verification using RS256 only (`alg=none` and HS256 explicitly rejected). Mandatory validation of `exp`, `iat`, `iss`, and `aud` claims.
- **NFR2 (Performance)**: JWKS key caching using PyJWT `PyJWKClient` to eliminate redundant HTTP requests to Keycloak per API call.
- **NFR3 (Containerization)**: API runs as non-root user (`appuser`) under Gunicorn WSGI in Docker.
- **NFR4 (Reliability)**: 503 `idp_unavailable` status returned gracefully if Keycloak JWKS endpoint is unreachable.

## 8. Success Metrics
- 100% pass rate on unit test suite covering 15+ JWT validation scenarios.
- 11/11 PASS score on live automated `demo.py` verification script.
- Zero credentials or tokens exposed in application log files.

## 9. Acceptance Criteria
- `docker compose up --build` starts Keycloak 26 and Flask API cleanly with imported realm data.
- Unauthenticated requests to protected endpoints return `401 missing_token`.
- Tokens with expired timestamps return `401 token_expired`.
- Tokens signed by unauthorized keys return `401 invalid_token`.
- Users accessing endpoints beyond their assigned role return `403 forbidden`.

## 10. Risk Assessment
- **Keycloak Startup Latency**: Keycloak 26 takes 15-30s to initialize and import realm. *Mitigation*: Configure healthchecks and `depends_on` in Docker Compose.
- **JWKS Network Isolation**: Container-to-container communication requires resolving internal Docker DNS (`http://keycloak:8080`) while matching token issuer host (`http://localhost:8080`). *Mitigation*: Dual URL configuration (`KEYCLOAK_PUBLIC_URL` vs `KEYCLOAK_INTERNAL_URL`).
