# Phase 3: Integration Architecture

Full working detail lives in its own doc per piece:
[phase-3-integration-build.md](./phase-3-integration-build.md),
[phase-3-sso-design.md](./phase-3-sso-design.md),
[phase-3-multitenant-design.md](./phase-3-multitenant-design.md). This doc
is the synthesis.

## Decision

- **Outbound integration**: the agent's tools no longer import claim/policy
  data directly. They call a mock enterprise API
  (`src/integrations/enterprise_api/`) over HTTP, authenticated via a real
  OAuth2 **client-credentials** flow — the machine-to-machine grant type,
  since this is one service (the agent) authenticating to another (the
  insurer's system), with no human involved at this step.
- **Inbound integration**: a separate API gateway
  (`src/integrations/api_gateway/`) fronts the multi-agent pipeline,
  authenticating whoever calls ClaimAssist itself via a per-client API key
  — deliberately a *different* mechanism than the outbound OAuth2 flow,
  since it's a different kind of boundary — plus per-key rate limiting.
- **SSO and multi-tenant data isolation**: designed, not built, per the
  phase plan. OIDC recommended as the primary SSO protocol (with SAML
  supported as a fallback for insurers whose identity provider requires
  it); shared-schema-per-tenant as the isolation floor, with PostgreSQL
  Row-Level Security as a mandatory second layer wherever shared tables are
  used at all.

## Alternatives considered

- **Skipping the mock enterprise API and keeping direct data access** —
  rejected as unrealistic. A real ClaimAssist deployment would never have
  direct database access to an insurer's systems of record; testing the
  agent against an actual authenticated network boundary, not an
  in-process import, is the entire point of this phase.
- **Using the same auth mechanism for both boundaries** — considered, but
  the inbound and outbound boundaries authenticate genuinely different
  kinds of callers (client applications calling ClaimAssist, versus
  ClaimAssist calling out to another system), and conflating them would
  obscure that they're separate architectural concerns with separate
  trust relationships.
- **Building SSO and multi-tenant isolation instead of just designing
  them** — explicitly out of scope per the phase plan, and for good
  reason: both decisions depend on facts a toy project doesn't have (which
  identity provider a real client uses, how many tenants, what contractual
  isolation guarantees are required) — writing code against unknown
  requirements would be guessing, not architecture.
- **Shared tables with only application-level `tenant_id` filtering, no
  database-level enforcement** — considered and rejected in the
  multi-tenant design doc specifically because it depends on every query,
  everywhere, forever, remembering to filter correctly — exactly the kind
  of discipline that erodes as a codebase grows, for data sensitive enough
  that a single missed filter is a real breach, not a minor bug.

## Why

- **Realism was the point, not just checking a phase-plan box.** This
  phase exists because a real ClaimAssist deployment integrates with
  systems ClaimAssist doesn't own or control — an insurer's existing claims
  system, an identity provider, potentially other tenants' data on the same
  infrastructure. Building an actual authenticated HTTP boundary (not just
  discussing one) is what let this phase surface a genuine, non-obvious
  finding: that Phase 2's synthetic test-data injection technique silently
  stops working once a boundary becomes a real network call to a separate
  process — a consequence of integration architecture that only shows up
  by actually building the integration, not by designing it on paper.
- **Data sensitivity drove the multi-tenant recommendation specifically.**
  This system handles regulated, claims/health-adjacent data. That's the
  direct reason the multi-tenant design doc recommends against pure
  shared-table isolation as sufficient on its own, even though it's the
  cheapest option to operate — the cost of getting isolation wrong here is
  categorically different from a typical SaaS multi-tenancy decision.
- **Client type shaped both design docs.** An insurance company's IT
  department almost certainly already has centralized identity management
  and would expect ClaimAssist to integrate with it (SSO), not add another
  password. Whether they use OIDC- or SAML-based tooling is a real
  unknown this project can't resolve without an actual client, hence
  recommending one primary approach while keeping the other genuinely
  supported, not dismissed.

## What I'd change at real production scale

- **Actually decide the multi-tenant architecture**, rather than
  presenting three options — this requires real numbers (tenant count,
  data volume, contractual isolation requirements) this project doesn't
  have, and was explicitly left as a decision for whoever has those
  numbers.
- **Build a proper test-data strategy across the integration boundary.**
  Phase 2's synthetic broken/ambiguous test cases can no longer reach the
  agent's data source now that it's a separate process — a real system
  needs either a dedicated test-data seeding endpoint on the mock service,
  or a shared fixture/database the test process and the service both read
  from, rather than in-process list mutation.
- **Test token expiry and refresh under real conditions**, not just the
  happy path — the 5-minute JWT TTL and the client's caching logic were
  never actually exercised against a real expiry boundary in this phase.
- **Expose the human-in-the-loop flow (Phase 2) through the gateway
  properly.** The gateway currently calls the multi-agent pipeline directly
  with no pause step; supporting Phase 2's interrupt/resume review flow
  over HTTP needs a genuinely different API shape (two calls — start a
  review, then submit the human's decision — not one request/response),
  which wasn't built here.
- **Move rate limiting and API-key storage out of in-memory Python
  dictionaries.** Both were built as the simplest thing that correctly
  demonstrates the boundary; neither survives a service restart or scales
  across multiple gateway instances, which any real deployment would run.
- **Implement, not just design, RLS policies and the SSO integration**
  once a real identity provider and real tenant requirements exist to build
  against — this phase intentionally stopped at the design stage for both,
  per the phase plan's own scope.
