"""
Standalone Mock Keycloak OIDC Provider for local development without Docker.
Runs on http://localhost:8080 and provides:
1. /realms/company/protocol/openid-connect/auth (Interactive Login Page)
2. /realms/company/protocol/openid-connect/token (Token endpoint with PKCE verification & CORS headers)
3. /realms/company/protocol/openid-connect/certs (JWKS endpoint serving RS256 public key)
4. /realms/company/protocol/openid-connect/logout (Logout redirect)
"""

import time
import uuid
import base64
from flask import Flask, request, jsonify, redirect, render_template_string
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

app = Flask(__name__)

# --- CORS HEADERS FOR BROWSER DEMO ACCESS ---
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/<path:path>", methods=["OPTIONS"])
def handle_options(path):
    return "", 200

# --- GENERATE LOCAL RS256 KEYPAIR FOR MOCK KEYCLOAK ---
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode("utf-8")

def int_to_b64(val: int) -> str:
    b = val.to_bytes((val.bit_length() + 7) // 8, byteorder='big')
    return base64.urlsafe_b64encode(b).decode('utf-8').rstrip('=')

pub_numbers = public_key.public_numbers()
jwks_data = {
    "keys": [{
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": "mock-keycloak-key-1",
        "n": int_to_b64(pub_numbers.n),
        "e": int_to_b64(pub_numbers.e)
    }]
}

# Temporary in-memory session store for authorization codes
auth_codes = {}

USERS = {
    "alice": {"name": "Alice Admin", "email": "alice@company.com", "roles": ["admin", "employee"]},
    "bob": {"name": "Bob Manager", "email": "bob@company.com", "roles": ["manager", "employee"]},
    "charlie": {"name": "Charlie Employee", "email": "charlie@company.com", "roles": ["employee"]}
}

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mock Keycloak 26 — Login</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 2.5rem; border-radius: 12px; border: 1px solid #334155; width: 100%; max-width: 420px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5); }
        .logo { font-size: 1.5rem; font-weight: 700; color: #38bdf8; margin-bottom: 0.5rem; text-align: center; }
        .sub { color: #94a3b8; font-size: 0.9rem; text-align: center; margin-bottom: 2rem; }
        .user-btn { display: block; width: 100%; padding: 1rem; margin-bottom: 0.85rem; background: #334155; color: #fff; text-decoration: none; border-radius: 8px; font-weight: 600; text-align: center; transition: background 0.2s; border: 1px solid #475569; cursor: pointer; }
        .user-btn:hover { background: #0284c7; border-color: #38bdf8; }
        .role-badge { display: inline-block; font-size: 0.75rem; background: rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 0.2rem 0.5rem; border-radius: 4px; margin-left: 0.5rem; }
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">Keycloak 26 Identity Provider</div>
        <div class="sub">Select a User Account to Authenticate</div>
        <form method="POST" action="/realms/company/protocol/openid-connect/auth/login">
            <input type="hidden" name="redirect_uri" value="{{ redirect_uri }}">
            <input type="hidden" name="state" value="{{ state }}">
            <input type="hidden" name="nonce" value="{{ nonce }}">
            <input type="hidden" name="code_challenge" value="{{ code_challenge }}">
            
            <button type="submit" name="username" value="alice" class="user-btn">
                Alice <span class="role-badge">Admin</span>
            </button>
            <button type="submit" name="username" value="bob" class="user-btn">
                Bob <span class="role-badge">Manager</span>
            </button>
            <button type="submit" name="username" value="charlie" class="user-btn">
                Charlie <span class="role-badge">Employee</span>
            </button>
        </form>
    </div>
</body>
</html>
"""

@app.route("/realms/company/protocol/openid-connect/auth", methods=["GET"])
def authorize():
    redirect_uri = request.args.get("redirect_uri", "http://localhost:5000/")
    state = request.args.get("state", "")
    nonce = request.args.get("nonce", "")
    code_challenge = request.args.get("code_challenge", "")

    return render_template_string(
        LOGIN_HTML,
        redirect_uri=redirect_uri,
        state=state,
        nonce=nonce,
        code_challenge=code_challenge
    )

@app.route("/realms/company/protocol/openid-connect/auth/login", methods=["POST"])
def process_login():
    username = request.form.get("username")
    redirect_uri = request.form.get("redirect_uri")
    state = request.form.get("state")
    nonce = request.form.get("nonce")
    code_challenge = request.form.get("code_challenge")

    code = f"mock-code-{uuid.uuid4().hex[:12]}"
    auth_codes[code] = {
        "username": username,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "redirect_uri": redirect_uri
    }

    return redirect(f"{redirect_uri}?code={code}&state={state}")

@app.route("/realms/company/protocol/openid-connect/token", methods=["POST", "OPTIONS"])
def token():
    if request.method == "OPTIONS":
        return "", 200

    grant_type = request.form.get("grant_type", "authorization_code")
    
    if grant_type == "password":
        username = request.form.get("username", "alice")
        nonce_val = ""
    else:
        code = request.form.get("code")
        code_data = auth_codes.pop(code, None)
        if not code_data:
            return jsonify({"error": "invalid_grant", "error_description": "Code invalid or expired"}), 400
        username = code_data["username"]
        nonce_val = code_data.get("nonce", "")

    user = USERS.get(username, USERS["alice"])
    now = int(time.time())

    headers = {"kid": "mock-keycloak-key-1"}
    
    access_payload = {
        "exp": now + 300,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "iss": "http://localhost:8080/realms/company",
        "aud": "company-app",
        "sub": f"user-{username}-id",
        "typ": "Bearer",
        "azp": "company-app",
        "preferred_username": username,
        "email": user["email"],
        "name": user["name"],
        "email_verified": True,
        "realm_access": {
            "roles": user["roles"]
        }
    }

    id_payload = {
        "exp": now + 300,
        "iat": now,
        "iss": "http://localhost:8080/realms/company",
        "aud": "company-app",
        "sub": f"user-{username}-id",
        "preferred_username": username,
        "nonce": nonce_val
    }

    access_token = jwt.encode(access_payload, private_pem, algorithm="RS256", headers=headers)
    id_token = jwt.encode(id_payload, private_pem, algorithm="RS256", headers=headers)

    return jsonify({
        "access_token": access_token,
        "id_token": id_token,
        "token_type": "Bearer",
        "expires_in": 300
    }), 200

@app.route("/realms/company/protocol/openid-connect/certs", methods=["GET"])
def certs():
    return jsonify(jwks_data), 200

@app.route("/realms/company/protocol/openid-connect/logout", methods=["GET", "POST"])
def logout():
    post_logout_redirect_uri = request.args.get("post_logout_redirect_uri", "http://localhost:5000/")
    return redirect(post_logout_redirect_uri)

if __name__ == "__main__":
    print("Mock Keycloak 26 server starting on http://localhost:8080 ...")
    app.run(host="0.0.0.0", port=8080)
