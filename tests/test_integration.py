"""
Live integration test suite testing Flask API against live Keycloak 26 stack.
Automatically skipped if live API (http://localhost:5000/health) or Keycloak is unreachable.
"""

import pytest
import requests

API_BASE = "http://localhost:5000"
KEYCLOAK_TOKEN_URL = "http://localhost:8080/realms/company/protocol/openid-connect/token"

def is_live_stack_available() -> bool:
    """Helper checking if Flask API and Keycloak endpoints are responding."""
    try:
        res = requests.get(f"{API_BASE}/health", timeout=2)
        return res.status_code == 200
    except requests.RequestException:
        return False

pytestmark = pytest.mark.skipif(
    not is_live_stack_available(),
    reason="Live stack unreachable (http://localhost:5000/health offline). Skipping integration tests."
)

def get_real_token(username: str, password: str) -> str:
    """Fetches real Keycloak access token via OIDC Resource Owner Password Flow."""
    payload = {
        "client_id": "company-app",
        "grant_type": "password",
        "username": username,
        "password": password
    }
    res = requests.post(KEYCLOAK_TOKEN_URL, data=payload, timeout=5)
    res.raise_for_status()
    return res.json()["access_token"]


def test_integration_public_endpoints():
    """Verify live public endpoints."""
    res = requests.get(f"{API_BASE}/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    res = requests.get(f"{API_BASE}/api/public")
    assert res.status_code == 200


def test_integration_alice_admin_access():
    """Verify Alice (Admin) access across all live endpoints."""
    token = get_real_token("alice", "Alice@123")
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(f"{API_BASE}/api/profile", headers=headers)
    assert res.status_code == 200
    assert res.json()["username"] == "alice"

    res = requests.get(f"{API_BASE}/api/reports", headers=headers)
    assert res.status_code == 200

    res = requests.get(f"{API_BASE}/api/admin/users", headers=headers)
    assert res.status_code == 200


def test_integration_bob_manager_access():
    """Verify Bob (Manager) access matrix on live stack."""
    token = get_real_token("bob", "Bob@123")
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(f"{API_BASE}/api/profile", headers=headers)
    assert res.status_code == 200

    res = requests.get(f"{API_BASE}/api/reports", headers=headers)
    assert res.status_code == 200

    res = requests.get(f"{API_BASE}/api/admin/users", headers=headers)
    assert res.status_code == 403


def test_integration_charlie_employee_access():
    """Verify Charlie (Employee) access matrix on live stack."""
    token = get_real_token("charlie", "Charlie@123")
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(f"{API_BASE}/api/profile", headers=headers)
    assert res.status_code == 200

    res = requests.get(f"{API_BASE}/api/reports", headers=headers)
    assert res.status_code == 403

    res = requests.get(f"{API_BASE}/api/admin/users", headers=headers)
    assert res.status_code == 403
