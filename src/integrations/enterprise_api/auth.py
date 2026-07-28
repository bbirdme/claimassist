"""
OAuth2 client-credentials flow for the mock enterprise API - the
machine-to-machine grant type, since ClaimAssist's agent is a service
authenticating to another service, not a human logging in.
"""

import os
import time

import jwt

JWT_ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 300  # short-lived on purpose, like a real access token

VALID_CLIENTS = {
    os.environ["ENTERPRISE_CLIENT_ID"]: os.environ["ENTERPRISE_CLIENT_SECRET"],
}


def authenticate_client(client_id: str, client_secret: str) -> bool:
    return VALID_CLIENTS.get(client_id) == client_secret


def issue_token(client_id: str) -> dict:
    now = int(time.time())
    payload = {
        "sub": client_id,
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
        "scope": "claims:read policies:read medical_notes:read",
    }
    token = jwt.encode(payload, os.environ["ENTERPRISE_JWT_SECRET"], algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "expires_in": TOKEN_TTL_SECONDS}


def verify_token(token: str) -> dict:
    """Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure -
    callers decide how to turn that into an HTTP response."""
    return jwt.decode(token, os.environ["ENTERPRISE_JWT_SECRET"], algorithms=[JWT_ALGORITHM])
