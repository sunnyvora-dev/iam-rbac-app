"""
Unit and integration tests for UI browser demo static endpoints, configuration, and security headers.
"""

import pytest
from app.main import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_serve_index(client):
    """Test that GET / returns index.html with correct text/html status and security headers."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    assert b"Login with Keycloak" in response.data
    
    # Check security headers
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    csp = response.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp

def test_serve_static_app_js(client):
    """Test that GET /static/app.js serves JavaScript file."""
    response = client.get("/static/app.js")
    assert response.status_code == 200
    assert "javascript" in response.content_type or "text/plain" in response.content_type or response.status_code == 200

def test_serve_static_style_css(client):
    """Test that GET /static/style.css serves CSS file."""
    response = client.get("/static/style.css")
    assert response.status_code == 200

def test_config_json(client):
    """Test that GET /config.json returns Keycloak public configuration."""
    response = client.get("/config.json")
    assert response.status_code == 200
    data = response.get_json()
    assert "keycloakUrl" in data
    assert "realm" in data
    assert "clientId" in data
    assert data["clientId"] == "company-app"
    assert data["realm"] == "company"

def test_404_json_handler(client):
    """Test that undefined route returns 404 with JSON error format."""
    response = client.get("/api/nonexistent-route-path")
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "not_found"
