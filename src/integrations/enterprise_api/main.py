"""
Mock "enterprise" claims/ERP system - stands in for the insurer's real
backend, which ClaimAssist would never have direct database access to in
production. Backed by the same ground-truth data as the rest of this
project (src/corpus_gen/facts.py), just exposed over HTTP with real OAuth2
protection instead of a direct in-process import.

Run with: uvicorn src.integrations.enterprise_api.main:app --port 8001
"""

from dotenv import load_dotenv
load_dotenv()

import jwt
from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi.security import OAuth2PasswordBearer

from src.corpus_gen.facts import CLAIMS, POLICIES, MEDICAL_NOTES
from src.integrations.enterprise_api.auth import authenticate_client, issue_token, verify_token

app = FastAPI(title="Mock Enterprise Claims API")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="oauth/token")


@app.post("/oauth/token")
def token_endpoint(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
):
    if grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")
    if not authenticate_client(client_id, client_secret):
        raise HTTPException(status_code=401, detail="invalid_client")
    return issue_token(client_id)


def require_token(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        return verify_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid token")


@app.get("/claims/{claim_id}")
def get_claim(claim_id: str, _claims: dict = Depends(require_token)):
    claim = next((c for c in CLAIMS if c["claim_id"] == claim_id), None)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"claim {claim_id} not found")
    return claim


@app.get("/policies/{policy_number}")
def get_policy(policy_number: str, _claims: dict = Depends(require_token)):
    policy = next((p for p in POLICIES if p["policy_number"] == policy_number), None)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"policy {policy_number} not found")
    return policy


@app.get("/claims/{claim_id}/medical-notes")
def get_medical_notes(claim_id: str, _claims: dict = Depends(require_token)):
    return [n for n in MEDICAL_NOTES if n["claim_id"] == claim_id]
