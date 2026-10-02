"""Flask REST API entry point exposing public, profile, management, administrative, and static demo endpoints."""

import os
import logging
from flask import Flask, jsonify, g, send_from_directory, make_response
from app.auth import require_roles, ADMIN, MANAGER, EMPLOYEE
from app.config import config

# Configure structured application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("iam-rbac-api")

def create_app() -> Flask:
    """Application factory for constructing and configuring the Flask API instance."""
    app = Flask(__name__, static_folder="../static")

    # --- BROWSER DEMO & STATIC ENDPOINTS ---

    @app.route("/", methods=["GET"])
    def serve_index():
        """Serves static/index.html browser demo page with security headers."""
        response = make_response(send_from_directory(os.path.join(app.root_path, "../static"), "index.html"))
        
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        csp = (
            f"default-src 'self'; "
            f"script-src 'self'; "
            f"style-src 'self'; "
            f"img-src 'self' data:; "
            f"connect-src 'self' {config.KEYCLOAK_PUBLIC_URL}; "
            f"frame-ancestors 'none'"
        )
        response.headers["Content-Security-Policy"] = csp
        return response

    @app.route("/static/<path:filename>", methods=["GET"])
    def serve_static(filename):
        """Serves static assets (CSS, JS)."""
        return send_from_directory(os.path.join(app.root_path, "../static"), filename)

    @app.route("/config.json", methods=["GET"])
    def get_frontend_config():
        """Returns non-sensitive Keycloak public configuration parameters for frontend PKCE initialization."""
        return jsonify({
            "keycloakUrl": config.KEYCLOAK_PUBLIC_URL,
            "realm": config.REALM,
            "clientId": config.CLIENT_ID
        }), 200

    # --- PUBLIC API ENDPOINTS ---

    @app.route("/health", methods=["GET"])
    def health():
        """Public health check endpoint for container probes."""
        return jsonify({
            "status": "healthy",
            "service": "iam-rbac-api",
            "version": "1.0.0"
        }), 200

    @app.route("/api/public", methods=["GET"])
    def public_info():
        """Public information endpoint requiring no authentication."""
        return jsonify({
            "message": "Welcome to the IAM & RBAC Public API",
            "auth_required": False
        }), 200

    # --- PROTECTED RBAC ENDPOINTS ---

    @app.route("/api/profile", methods=["GET"])
    @require_roles(ADMIN, MANAGER, EMPLOYEE)
    def get_profile():
        """Profile endpoint accessible to all authenticated roles (admin, manager, employee)."""
        return jsonify({
            "username": g.user["username"],
            "email": g.user["email"],
            "name": g.user["name"],
            "roles": g.user["roles"]
        }), 200

    @app.route("/api/reports", methods=["GET"])
    @require_roles(ADMIN, MANAGER)
    def get_reports():
        """Management reports endpoint accessible only to admin and manager roles."""
        return jsonify({
            "reports": [
                {"id": "REP-101", "title": "Q3 Access Audit Report", "classification": "CONFIDENTIAL"},
                {"id": "REP-102", "title": "Role Usage Analytics", "classification": "INTERNAL"}
            ],
            "accessed_by": g.user["username"],
            "user_roles": g.user["roles"]
        }), 200

    @app.route("/api/admin/users", methods=["GET"])
    @require_roles(ADMIN)
    def get_admin_users():
        """Administrative user directory endpoint accessible exclusively to admin role."""
        return jsonify({
            "users": [
                {"username": "alice", "email": "alice@company.com", "role": "admin"},
                {"username": "bob", "email": "bob@company.com", "role": "manager"},
                {"username": "charlie", "email": "charlie@company.com", "role": "employee"}
            ],
            "total": 3,
            "accessed_by": g.user["username"]
        }), 200

    # --- JSON ERROR HANDLERS ---

    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({
            "error": "not_found",
            "message": "The requested resource was not found"
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return jsonify({
            "error": "method_not_allowed",
            "message": "The HTTP method is not allowed for this resource"
        }), 405

    @app.errorhandler(500)
    def handle_internal_error(e):
        logger.error(f"Internal server error: {str(e)}")
        return jsonify({
            "error": "internal_error",
            "message": "An internal server error occurred"
        }), 500

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
