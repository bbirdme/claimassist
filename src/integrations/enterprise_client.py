"""
HTTP client for the mock enterprise API (src/integrations/enterprise_api/),
used by the agent's tools instead of importing src/corpus_gen/facts.py
directly. This is the actual integration boundary Phase 3 is about: the
agent no longer has direct access to claim/policy data - it authenticates
over the network like any other external client would have to.
"""

import os
import time

import requests

_cached_token: str | None = None
_cached_token_expiry: float = 0


def _api_base() -> str:
    return os.environ.get("ENTERPRISE_API_BASE", "http://127.0.0.1:8001")


def _get_token() -> str:
    global _cached_token, _cached_token_expiry

    if _cached_token and time.time() < _cached_token_expiry - 10:
        return _cached_token

    resp = requests.post(
        f"{_api_base()}/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["ENTERPRISE_CLIENT_ID"],
            "client_secret": os.environ["ENTERPRISE_CLIENT_SECRET"],
        },
    )
    resp.raise_for_status()
    body = resp.json()
    _cached_token = body["access_token"]
    _cached_token_expiry = time.time() + body["expires_in"]
    return _cached_token


def _authed_get(path: str):
    token = _get_token()
    resp = requests.get(f"{_api_base()}{path}", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 404:
        return {"error": resp.json().get("detail", "not found")}
    resp.raise_for_status()
    return resp.json()


def get_claim(claim_id: str) -> dict:
    return _authed_get(f"/claims/{claim_id}")


def get_policy(policy_number: str) -> dict:
    return _authed_get(f"/policies/{policy_number}")


def get_medical_notes(claim_id: str) -> list[dict]:
    return _authed_get(f"/claims/{claim_id}/medical-notes")
