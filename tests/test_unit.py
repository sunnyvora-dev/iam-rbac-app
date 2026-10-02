"""
Comprehensive 100% offline unit test suite for IAM & RBAC Flask REST API.
Uses a locally generated RSA key pair to sign JWT test tokens and mocks auth.get_signing_key.
"""

import time
import pytest
import jwt
from unittest.mock import MagicMock
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from jwt.exceptions import PyJWKClientConnectionError

from app.main import create_app
from app.config import config

# --- LOCAL RSA KEY GENERATION FOR OFFLINE UNIT TESTING ---

# Generate primary RSA Private/Public Keypair
_private_key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_private_pem = _private_key_obj.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
_public_pem = _private_key_obj.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

# Generate secondary (untrusted/forged) RSA Private Keypair
_forged_private_key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_forged_private_pem = _forged_private_key_obj.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

def create_test_token(
    username: str = "alice",
    email: str = "alice@company.com",
    roles: list = None,
    issuer: str = config.ISSUER_URL,
    audience: str = config.CLIENT_ID,
    ttl: int = 300,
    alg: str = "RS256",
    signing_pem: bytes = _private_pem,
    omit_claims: list = None
) -> str:
    """Helper utility constructing signed JWT tokens for unit testing."""
    now = int(time.time())
    if roles is None:
        roles = ["admin", "employee"]

    payload = {
        "exp": now + ttl,
        "iat": now,
        "iss": issuer,
        "aud": audience,
        "sub": "test-user-uuid-123",
        "preferred_username": username,
        "email": email,
        "given_name": username.capitalize(),
        "family_name": "Test",
        "realm_access": {
            "roles": roles
        }
    }

    if omit_claims:
        for claim in omit_claims:
            payload.pop(claim, None)

    if alg == "none":
        return jwt.encode(payload, key="", algorithm="none")

    return jwt.encode(payload, signing_pem, algorithm=alg, headers={"kid": "test-key-id"})


@pytest.fixture
def client(monkeypatch):
    """Flask test client fixture with monkeypatched get_signing_key returning local test public key."""
    # Create mock PyJWK wrapping local public key
    mock_pyjwk = MagicMock()
    mock_pyjwk.key = _public_pem

    # Monkeypatch auth.get_signing_key in app.auth module
    monkeypatch.setattr("app.auth.get_signing_key", lambda token: mock_pyjwk)

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# --- PUBLIC ENDPOINT TESTS ---

def test_health_endpoint(client):
    """Verify /health returns 200 OK without authentication."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "iam-rbac-api"


def test_public_api_endpoint(client):
    """Verify /api/public returns 200 OK without authentication."""
    res = client.get("/api/public")
    assert res.status_code == 200
    data = res.get_json()
    assert data["auth_required"] is False


# --- AUTHENTICATION FAILURE EDGE CASES ---

def test_missing_authorization_header(client):
    """Verify missing Authorization header returns 401 missing_token."""
    res = client.get("/api/profile")
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"] == "missing_token"


def test_malformed_authorization_scheme(client):
    """Verify non-Bearer Authorization header returns 401 missing_token."""
    res = client.get("/api/profile", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"] == "missing_token"


def test_garbage_token(client):
    """Verify malformed/garbage JWT string returns 401 invalid_token."""
    res = client.get("/api/profile", headers={"Authorization": "Bearer not.a.valid.jwt.string"})
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"] == "invalid_token"


def test_expired_token(client):
    """Verify expired token (exp in past) returns 401 token_expired."""
    expired_token = create_test_token(ttl=-10)
    res = client.get("/api/profile", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"] == "token_expired"


def test_wrong_audience(client):
    """Verify token with incorrect aud claim returns 401 invalid_token."""
    wrong_aud_token = create_test_token(audience="wrong-app-id")
    res = client.get("/api/profile", headers={"Authorization": f"Bearer {wrong_aud_token}"})
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"] == "invalid_token"


def test_wrong_issuer(client):
    """Verify token with incorrect iss claim returns 401 invalid_token."""
    wrong_iss_token = create_test_token(issuer="http://malicious-idp.com/realms/company")
    res = client.get("/api/profile", headers={"Authorization": f"Bearer {wrong_iss_token}"})
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"] == "invalid_token"


def test_forged_signature(client):
    """Verify token signed by an unauthorized RSA key returns 401 invalid_token."""
    forged_token = create_test_token(signing_pem=_forged_private_pem)
    res = client.get("/api/profile", headers={"Authorization": f"Bearer {forged_token}"})
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"] == "invalid_token"


def test_algorithm_none(client):
    """Verify unsigned token (alg=none) returns 401 invalid_token."""
    unsigned_token = create_test_token(alg="none")
    res = client.get("/api/profile", headers={"Authorization": f"Bearer {unsigned_token}"})
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"] == "invalid_token"


def test_missing_required_claim(client):
    """Verify token missing mandatory exp or iat claim returns 401 invalid_token."""
    missing_claim_token = create_test_token(omit_claims=["exp"])
    res = client.get("/api/profile", headers={"Authorization": f"Bearer {missing_claim_token}"})
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"] == "invalid_token"


def test_token_no_roles_returns_forbidden(client):
    """Verify token containing empty realm_access.roles returns 403 forbidden on protected routes."""
    empty_roles_token = create_test_token(roles=[])
    res = client.get("/api/profile", headers={"Authorization": f"Bearer {empty_roles_token}"})
    assert res.status_code == 403
    data = res.get_json()
    assert data["error"] == "forbidden"


def test_idp_unavailable_returns_503(client, monkeypatch):
    """Verify 503 idp_unavailable returned when Keycloak JWKS endpoint raises PyJWKClientConnectionError."""
    def mock_raise_conn_err(token):
        raise PyJWKClientConnectionError("Connection to JWKS endpoint failed")
    
    monkeypatch.setattr("app.auth.get_signing_key", mock_raise_conn_err)
    valid_token = create_test_token()
    
    res = client.get("/api/profile", headers={"Authorization": f"Bearer {valid_token}"})
    assert res.status_code == 503
    data = res.get_json()
    assert data["error"] == "idp_unavailable"


# --- FULL ACCESS MATRIX ROLE TESTING (EMPLOYEE, MANAGER, ADMIN) ---

@pytest.mark.parametrize("role,endpoint,expected_status", [
    # Employee Matrix
    ("employee", "/api/profile", 200),
    ("employee", "/api/reports", 403),
    ("employee", "/api/admin/users", 403),

    # Manager Matrix
    ("manager", "/api/profile", 200),
    ("manager", "/api/reports", 200),
    ("manager", "/api/admin/users", 403),

    # Admin Matrix
    ("admin", "/api/profile", 200),
    ("admin", "/api/reports", 200),
    ("admin", "/api/admin/users", 200),
])
def test_rbac_access_matrix(client, role, endpoint, expected_status):
    """Tests every role x endpoint combination in the authorization access matrix."""
    token = create_test_token(username=f"user_{role}", roles=[role])
    res = client.get(endpoint, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == expected_status, f"Role {role} on {endpoint} returned {res.status_code}, expected {expected_status}"


# --- STANDARD JSON ERROR HANDLER TESTS ---

def test_404_json_handler(client):
    """Verify 404 returns structured JSON payload."""
    res = client.get("/api/nonexistent-route")
    assert res.status_code == 404
    data = res.get_json()
    assert data["error"] == "not_found"


def test_405_json_handler(client):
    """Verify 405 returns structured JSON payload."""
    res = client.post("/health")
    assert res.status_code == 405
    data = res.get_json()
    assert data["error"] == "method_not_allowed"
