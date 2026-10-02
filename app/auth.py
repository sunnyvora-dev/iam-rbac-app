"""Authentication and authorization middleware module enforcing RS256 JWT validation and RBAC."""

import logging
from functools import wraps
from typing import Callable, Any, List, Optional
from flask import request, jsonify, g
import jwt
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError, PyJWTError, ExpiredSignatureError
from jwt.api_jwk import PyJWKSet
from jwt.jwks_client import PyJWKClient

from app.config import config

logger = logging.getLogger(__name__)

# System Role Constants
ADMIN: str = "admin"
MANAGER: str = "manager"
EMPLOYEE: str = "employee"

# Centralized PyJWKClient instance for JWKS caching
_jwks_client: Optional[PyJWKClient] = None

def get_jwks_client() -> PyJWKClient:
    """Lazily initializes and returns the PyJWKClient instance."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(config.JWKS_URL, cache_keys=True)
    return _jwks_client

def get_signing_key(token: str) -> Any:
    """
    Fetches the matching RS256 public key from Keycloak JWKS endpoint.
    Decoupled function allowing unit test suites to easily monkeypatch local signing keys.
    """
    client = get_jwks_client()
    return client.get_signing_key_from_jwt(token)

def require_roles(*allowed_roles: str) -> Callable:
    """
    Decorator enforcing JWT authentication and role-based authorization.
    
    Validates:
    1. Authorization Bearer header presence.
    2. IdP JWKS reachability.
    3. RS256 JWT signature verification.
    4. Required claims presence (exp, iat, iss, aud).
    5. User role membership in realm_access.roles.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            auth_header = request.headers.get("Authorization", "")
            
            if not auth_header or not auth_header.startswith("Bearer "):
                logger.warning("Authentication failed: Missing or malformed Authorization header")
                return jsonify({
                    "error": "missing_token",
                    "message": "Missing or malformed Authorization header"
                }), 401
            
            token = auth_header.split(" ", 1)[1].strip()
            if not token:
                logger.warning("Authentication failed: Empty token string")
                return jsonify({
                    "error": "missing_token",
                    "message": "Missing or malformed Authorization header"
                }), 401
            
            # 1. Fetch Signing Key
            try:
                signing_key = get_signing_key(token)
                verification_key = signing_key.key
            except (PyJWKClientConnectionError, PyJWKClientError, Exception) as err:
                # Catch IdP connection failures or key lookup errors specifically for JWKS reachability
                err_msg = str(err)
                if "connection" in err_msg.lower() or "unreachable" in err_msg.lower() or isinstance(err, PyJWKClientConnectionError):
                    logger.error(f"IdP JWKS endpoint unavailable: {err_msg}")
                    return jsonify({
                        "error": "idp_unavailable",
                        "message": "Unable to reach Identity Provider JWKS endpoint"
                    }), 503
                logger.warning(f"Key lookup failed: {err_msg}")
                return jsonify({
                    "error": "invalid_token",
                    "message": "Invalid token signature or claims"
                }), 401

            # 2. Decode and Verify JWT Token Signature & Claims
            try:
                payload = jwt.decode(
                    token,
                    verification_key,
                    algorithms=["RS256"],
                    audience=config.CLIENT_ID,
                    issuer=config.ISSUER_URL,
                    options={
                        "require": ["exp", "iat", "iss", "aud"]
                    }
                )
            except ExpiredSignatureError:
                logger.warning("Authentication failed: Token has expired")
                return jsonify({
                    "error": "token_expired",
                    "message": "Token has expired"
                }), 401
            except PyJWTError as err:
                logger.warning(f"Authentication failed: Invalid token ({type(err).__name__}: {str(err)})")
                return jsonify({
                    "error": "invalid_token",
                    "message": "Invalid token signature or claims"
                }), 401

            # 3. Role-Based Access Control (RBAC) Check
            user_roles: List[str] = payload.get("realm_access", {}).get("roles", [])
            username: str = payload.get("preferred_username", "unknown_user")
            
            if allowed_roles:
                has_role = any(role in user_roles for role in allowed_roles)
                if not has_role:
                    logger.warning(
                        f"Authorization failed for user '{username}' with roles {user_roles}. "
                        f"Required one of: {allowed_roles}"
                    )
                    return jsonify({
                        "error": "forbidden",
                        "message": "User does not possess required role permission"
                    }), 403

            # Store sanitized user context in Flask 'g' global context
            given_name = payload.get("given_name", "")
            family_name = payload.get("family_name", "")
            full_name = f"{given_name} {family_name}".strip() or username

            g.user = {
                "username": username,
                "email": payload.get("email", ""),
                "name": full_name,
                "roles": user_roles
            }

            return fn(*args, **kwargs)

        return wrapper
    return decorator
