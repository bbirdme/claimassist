# Phase 3: SSO Design (Not Implemented)

Per the phase plan, this is a design document, not a build — no code
accompanies this doc. Companion to
[phase-3-integration-build.md](./phase-3-integration-build.md), which built
the two boundaries this design would plug into.

## The problem

Case workers currently have no login of their own in this project at all —
the gateway built in this phase authenticates *applications* (via an API
key), not *people*. A real deployment needs case workers to log in as
themselves, and enterprises essentially always require this to happen via
**SSO**: one login (managed by the insurer's own identity provider) grants
access to every internal tool, ClaimAssist included, rather than yet another
ClaimAssist-specific username and password.

## Recommended approach: OIDC, with SAML as a fallback

**OpenID Connect (OIDC)**, built on top of OAuth2, is the recommended
primary protocol — the same underlying token mechanism already used for the
enterprise API's client-credentials flow (Phase 3's build), just for a
human logging in rather than a service authenticating itself. Reasons to
prefer it over the older alternative:

- Better tooling and library support across every modern framework.
- Simpler to reason about (JSON-based tokens, not XML).
- The Bearer-token mental model this project already has (from the
  enterprise API's JWTs) extends directly to OIDC's ID tokens.

**SAML** should still be supported as a fallback, not dismissed: it remains
the entrenched standard at many large, longer-established enterprises, and
an insurer's IT department may not have a choice about which their identity
provider (Okta, Azure AD/Entra ID, PingIdentity, etc.) actually supports for
a given integration. A real proposal to a client would ask which their IdP
supports before assuming OIDC is available.

## How this plugs into what's already built

The gateway (`src/integrations/api_gateway/`) built in this phase is the
right place for this, but it needs two genuinely different auth paths for
two genuinely different caller types — not a replacement of the existing
mechanism:

- **Human case workers, via a browser** → SSO/OIDC. The gateway (or a
  frontend sitting in front of it) redirects an unauthenticated browser to
  the insurer's identity provider; the IdP authenticates the person using
  credentials they already have; ClaimAssist receives a signed ID token
  back and verifies it against a pre-established trust relationship
  (the IdP's public signing key), never seeing or handling a password
  itself.
- **Service-to-service callers** (a scheduled batch job, another internal
  system calling ClaimAssist programmatically, not a person at a
  keyboard) → the API-key mechanism already built stays exactly as it is.
  These aren't competing designs; they're for different kinds of callers.

## What the identity token needs to carry

Beyond "who is this person," the ID token/claims need to carry enough for
authorization decisions downstream, particularly:

- A stable user identifier and email.
- **Tenant/organization affiliation** — which insurance company this case
  worker belongs to. This is the single most important claim for
  [multi-tenant isolation](./phase-3-multitenant-design.md): every
  downstream data access this session makes must be scoped to this tenant,
  and the identity token is where that scoping decision starts.
- **Role** (case worker, supervisor, admin) — for authorization decisions
  this project hasn't built yet (e.g. who can override a discrepancy
  finding versus who can only view it), but which a real deployment would
  need from day one.

## Why SSO matters beyond convenience

The real value isn't "one less password to remember" — it's centralized
control. When the insurer disables someone's account (they leave the
company, change roles, get flagged for a security incident), that one
action should immediately cut off their ClaimAssist access too, without
anyone on the ClaimAssist side having to be told to do anything. A
ClaimAssist-specific login would mean a second place credentials can go
stale, and a second thing IT has to remember to revoke — exactly the kind
of gap that shows up in security audits and incident postmortems.

## What real production scale would require that this doc doesn't cover

- **Session lifecycle** — token refresh, session timeout policy, and
  what happens to an in-progress discrepancy review (see
  [phase-2-human-in-the-loop.md](./phase-2-human-in-the-loop.md)) if a
  session expires mid-review.
- **Which specific IdP(s)** to actually integrate first — this doc is
  protocol-level, not vendor-specific, since that decision depends on
  whichever real client this system is built for.
- **Authorization**, not just authentication — this doc covers proving who
  someone is; deciding what they're allowed to do once authenticated
  (role-based access control) is a related but separate design question,
  not addressed here.
