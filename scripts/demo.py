#!/usr/bin/env python3
"""
Automated 11-scenario verification script for IAM & RBAC Application.
Obtains real OIDC password grant tokens from Keycloak for alice, bob, charlie,
tests every access matrix combination, prints an ANSI-colored summary table,
and exits non-zero if any scenario fails.
"""

import sys
import time
import requests

API_BASE = "http://localhost:5000"
KEYCLOAK_TOKEN_URL = "http://localhost:8080/realms/company/protocol/openid-connect/token"

# ANSI Color Codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def fetch_token(username: str, password: str) -> str:
    """Fetches real Keycloak access token for demo user."""
    payload = {
        "client_id": "company-app",
        "grant_type": "password",
        "username": username,
        "password": password
    }
    try:
        res = requests.post(KEYCLOAK_TOKEN_URL, data=payload, timeout=5)
        if res.status_code == 200:
            return res.json().get("access_token", "")
        print(f"{RED}Failed to fetch token for '{username}': HTTP {res.status_code} - {res.text}{RESET}")
        return ""
    except Exception as e:
        print(f"{RED}Error connecting to Keycloak token endpoint: {e}{RESET}")
        return ""

def main():
    print(f"\n{BOLD}{CYAN}========================================================================={RESET}")
    print(f"{BOLD}{CYAN}      IAM & RBAC APPLICATION — 11-SCENARIO VERIFICATION SUITE           {RESET}")
    print(f"{BOLD}{CYAN}========================================================================={RESET}\n")

    # 1. Fetch Tokens for Demo Users
    print(f"{BOLD}1. Authenticating demo users with Keycloak OIDC Provider...{RESET}")
    tokens = {
        "alice": fetch_token("alice", "Alice@123"),      # admin, employee
        "bob": fetch_token("bob", "Bob@123"),          # manager, employee
        "charlie": fetch_token("charlie", "Charlie@123")  # employee
    }

    for user, token in tokens.items():
        if token:
            print(f"  [{GREEN}✓{RESET}] User {BOLD}{user.capitalize()}{RESET}: Token acquired ({token[:25]}...)")
        else:
            print(f"  [{RED}✗{RESET}] User {BOLD}{user.capitalize()}{RESET}: Failed to acquire token.")
            sys.exit(1)

    # 2. Define 11 Test Scenarios
    scenarios = [
        # Public Endpoints
        {"id": 1, "name": "Public Health Check", "endpoint": "/health", "user": None, "token": None, "expected": 200},
        {"id": 2, "name": "Public System Info", "endpoint": "/api/public", "user": None, "token": None, "expected": 200},

        # Profile Endpoint (/api/profile -> admin, manager, employee allowed)
        {"id": 3, "name": "Alice (Admin) -> /api/profile", "endpoint": "/api/profile", "user": "alice", "token": tokens["alice"], "expected": 200},
        {"id": 4, "name": "Bob (Manager) -> /api/profile", "endpoint": "/api/profile", "user": "bob", "token": tokens["bob"], "expected": 200},
        {"id": 5, "name": "Charlie (Employee) -> /api/profile", "endpoint": "/api/profile", "user": "charlie", "token": tokens["charlie"], "expected": 200},

        # Reports Endpoint (/api/reports -> admin, manager allowed; employee 403)
        {"id": 6, "name": "Alice (Admin) -> /api/reports", "endpoint": "/api/reports", "user": "alice", "token": tokens["alice"], "expected": 200},
        {"id": 7, "name": "Bob (Manager) -> /api/reports", "endpoint": "/api/reports", "user": "bob", "token": tokens["bob"], "expected": 200},
        {"id": 8, "name": "Charlie (Employee) -> /api/reports", "endpoint": "/api/reports", "user": "charlie", "token": tokens["charlie"], "expected": 403},

        # Admin Users Endpoint (/api/admin/users -> admin allowed; manager/employee 403)
        {"id": 9, "name": "Alice (Admin) -> /api/admin/users", "endpoint": "/api/admin/users", "user": "alice", "token": tokens["alice"], "expected": 200},
        {"id": 10, "name": "Bob (Manager) -> /api/admin/users", "endpoint": "/api/admin/users", "user": "bob", "token": tokens["bob"], "expected": 403},
        {"id": 11, "name": "Charlie (Employee) -> /api/admin/users", "endpoint": "/api/admin/users", "user": "charlie", "token": tokens["charlie"], "expected": 403},
    ]

    print(f"\n{BOLD}2. Executing Access Control Scenarios against Flask API...{RESET}\n")
    print(f"{'#':<3} {'Scenario Description':<40} {'Expected':<10} {'Actual':<10} {'Result':<10}")
    print("-" * 75)

    passed_count = 0
    failed_count = 0

    for sc in scenarios:
        headers = {}
        if sc["token"]:
            headers["Authorization"] = f"Bearer {sc['token']}"

        try:
            res = requests.get(f"{API_BASE}{sc['endpoint']}", headers=headers, timeout=5)
            actual_status = res.status_code
        except Exception as e:
            actual_status = 0

        passed = (actual_status == sc["expected"])
        if passed:
            passed_count += 1
            status_str = f"{GREEN}PASS{RESET}"
        else:
            failed_count += 1
            status_str = f"{RED}FAIL{RESET}"

        print(f"{sc['id']:<3} {sc['name']:<40} {sc['expected']:<10} {actual_status:<10} {status_str:<10}")

    print("-" * 75)
    print(f"\n{BOLD}SUMMARY:{RESET} Total Scenarios: 11 | {GREEN}Passed: {passed_count}{RESET} | {RED}Failed: {failed_count}{RESET}\n")

    if failed_count > 0:
        print(f"{RED}{BOLD}VERIFICATION FAILED: {failed_count} scenario(s) did not match expected access control policy.{RESET}\n")
        sys.exit(1)
    else:
        print(f"{GREEN}{BOLD}VERIFICATION SUCCESSFUL: 11/11 Scenarios Passed! Access control matrix fully verified.{RESET}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
