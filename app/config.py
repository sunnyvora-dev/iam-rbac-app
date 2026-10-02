"""Application configuration settings derived from environment variables."""

import os

class Config:
    """Central configuration parameters for Keycloak OIDC integration and API runtime."""
    
    # Public Keycloak URL used for JWT issuer validation (e.g. http://localhost:8080)
    KEYCLOAK_PUBLIC_URL: str = os.getenv("KEYCLOAK_PUBLIC_URL", "http://localhost:8080").rstrip("/")
    
    # Internal Keycloak URL used by backend containers to fetch JWKS keys (e.g. http://localhost:8080)
    KEYCLOAK_INTERNAL_URL: str = os.getenv("KEYCLOAK_INTERNAL_URL", "http://localhost:8080").rstrip("/")
    
    # Target Realm name
    REALM: str = os.getenv("REALM", "company")
    
    # Target Client ID / Audience name
    CLIENT_ID: str = os.getenv("CLIENT_ID", "company-app")

    @property
    def ISSUER_URL(self) -> str:
        """Expected issuer claim (iss) in incoming JWT tokens."""
        return f"{self.KEYCLOAK_PUBLIC_URL}/realms/{self.REALM}"

    @property
    def JWKS_URL(self) -> str:
        """Internal Keycloak JWKS endpoint URL for fetching RS256 public signing keys."""
        return f"{self.KEYCLOAK_INTERNAL_URL}/realms/{self.REALM}/protocol/openid-connect/certs"

config = Config()
