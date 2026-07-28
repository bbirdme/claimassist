# Phase 3: Mock Enterprise API + API Gateway

Mid-phase working document — not the final
`docs/phase-3-integration-architecture.md` decision doc, which comes once
the SSO and multi-tenant isolation design docs are also written.

## What was built

Two genuinely separate integration boundaries, easy to conflate but not the
same thing:

**Outbound — agent → mock enterprise API** (`src/integrations/enterprise_api/`):
a FastAPI service standing in for the insurer's real backend system, which
ClaimAssist would never have direct database access to in production.
Backed by the same ground-truth data as the rest of this project
(`src/corpus_gen/facts.py`), exposed over HTTP instead of a direct Python
import. Protected by a real OAuth2 **client-credentials** flow: `POST
/oauth/token` exchanges a `client_id`/`client_secret` for a short-lived
(5-minute) signed JWT, and `/claims/{id}`, `/policies/{number}`,
`/claims/{id}/medical-notes` all require a valid Bearer token.
`src/integrations/enterprise_client.py` handles token acquisition and
caching on the agent's side; `src/agents/tools.py` was rewired to call this
client instead of importing `facts.py` directly, with no changes needed to
`single_agent.py`, `multi_agent.py`, or `deterministic_check.py` — they all
still call `lookup_claim`/`lookup_policy`/`lookup_medical_notes`, just with
a different implementation underneath.

**Inbound — API gateway in front of the agent** (`src/integrations/api_gateway/`):
a separate FastAPI service that whoever wants to invoke ClaimAssist (e.g. a
case-worker portal) would go through first. Uses a different auth
mechanism on purpose — a simple API key (`X-API-Key` header) rather than
OAuth2 — since this is a genuinely different kind of boundary: authenticating
*inbound* client applications calling ClaimAssist, not ClaimAssist calling
*out* to another system. Also applies a per-key rate limit (5 requests/minute,
matching the tighter free-tier limits observed with Groq/Gemini in Phases
0-1 — no point accepting more gateway traffic than the backend agent can
actually serve) before forwarding to the multi-agent pipeline.

## Verified end to end

- Token request with valid `client_id`/`client_secret` → returns a Bearer
  token; with wrong credentials → `401`.
- Protected enterprise endpoint with a valid token → returns real data; with
  no token, or a tampered token → `401`; unknown claim ID → `404`.
- Gateway with no API key → `422` (FastAPI's own missing-header validation);
  wrong key → `401`; valid key → `200`, and the response is the actual
  multi-agent pipeline's output (claim ID, policy number, discrepancies,
  summary) — the full chain (gateway → agent → OAuth2-protected enterprise
  API) works end to end.
- Rate limiting confirmed working *across separate calls*, not just within
  one burst: an earlier test call from the auth check was still inside the
  same 60-second window, so the 5th call in a fresh loop of 6 got rate-limited
  instead of the 6th — the sliding window correctly persisted state between
  independent invocations, which is the actual thing worth verifying (a
  limiter that only works within a single burst isn't a real limiter).

## Two small, real bugs along the way

Both were the same root cause, hit twice: `load_dotenv()` was only ever
called inside each script's own `if __name__ == "__main__":` block in
earlier phases. The enterprise API and the deterministic checker's CLI entry
point both failed on startup with `KeyError` on an env var, because nothing
had loaded `.env` before the module-level code that reads `os.environ` ran.
Fixed by calling `load_dotenv()` at true import time in both places, not
deferred to a `__main__` guard — worth remembering for anything imported by
a process this codebase doesn't control the entry point of (like `uvicorn`
importing a FastAPI app).

## A real methodological consequence of this phase, not just a build detail

Several Phase 2 synthetic test scripts
(`broken_claim_cases.py`, `hitl_demo.py`, `multi_agent_broken_case_eval.py`,
`agent_broken_case_eval.py`) worked by appending fake claims directly to the
in-memory `facts.CLAIMS` list from within the same Python process running
the test. **That no longer reaches the agent's data source.** The mock
enterprise API is now a separate process with its own independent import of
`facts.py` — appending to one process's list has no effect on the other's.
This isn't a bug to silently patch around; it's a genuine, common
consequence of separating services that this project hadn't hit before
Phase 3: once an integration boundary is real (a network call to another
process), in-process test-data injection stops working, and a real test
strategy needs either a shared test-data seeding mechanism on the mock
service itself, or accepting that synthetic edge cases can only be tested
against whatever the service's actual data already contains. Not fixed in
this phase — noted as a real gap for whichever phase next needs to test
against harder synthetic cases through this same integration boundary.

## What's not yet tested

- **Token expiry and refresh** — the 5-minute TTL and the client's caching
  logic weren't tested against an actual expiry boundary (e.g. holding a
  token past 5 minutes and confirming the client re-requests one).
- **The human-in-the-loop flow through the gateway** — the gateway currently
  calls `run_multi_agent` directly (no pause/resume), not the
  `human_in_the_loop.py` interrupt-based version from Phase 2. Exposing
  that properly through HTTP would need a two-step API (start review, then
  a separate endpoint to submit the human's decision), not the single
  request/response shape built here.
