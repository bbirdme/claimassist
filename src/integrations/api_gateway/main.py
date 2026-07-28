"""
API gateway in front of the agent - the inbound boundary, separate from the
outbound enterprise-API integration. Whoever wants to invoke ClaimAssist
(e.g. a case-worker portal) goes through here first: API-key auth, then
rate limiting, before the request ever reaches the multi-agent pipeline.

Run with: uvicorn src.integrations.api_gateway.main:app --port 8010
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Header, HTTPException

from src.agents.multi_agent import run_multi_agent
from src.integrations.api_gateway.auth import authenticate_api_key
from src.integrations.api_gateway.rate_limit import check_rate_limit

app = FastAPI(title="ClaimAssist API Gateway")


@app.post("/v1/claims/{claim_id}/investigate")
def investigate_claim(claim_id: str, x_api_key: str = Header(...)):
    client_name = authenticate_api_key(x_api_key)
    if client_name is None:
        raise HTTPException(status_code=401, detail="invalid API key")

    if not check_rate_limit(x_api_key):
        raise HTTPException(status_code=429, detail="rate limit exceeded, try again shortly")

    result = run_multi_agent(claim_id)
    return {
        "claim_id": result["claim_id"],
        "policy_number": result["policy"].get("policy_number"),
        "discrepancies": result["discrepancies"],
        "summary": result["summary"],
    }
