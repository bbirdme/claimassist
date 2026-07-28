# Phase 3: Multi-Tenant Data Isolation Design (Not Implemented)

Per the phase plan, this is a design document, not a build. Companion to
[phase-3-sso-design.md](./phase-3-sso-design.md) — the identity token
described there is where tenant scoping would actually originate from.

## The problem

Everything built in this project so far is single-tenant: one synthetic
insurance company's worth of policies and claims (`src/corpus_gen/facts.py`),
one Postgres database, one pgvector index. If ClaimAssist became a product
sold to *multiple* insurance companies rather than built for just one, each
becomes a "tenant" sharing the same underlying system — and isolation means
Company A's case workers must never be able to see Company B's data,
**not even via an application bug**. Given this system handles regulated,
sensitive claims/health-adjacent data, a cross-tenant leak isn't a
hypothetical embarrassment; it's a severe compliance and trust failure.

## Three architectures, and the real trade-off between them

| Approach | Isolation strength | Operational cost |
|---|---|---|
| Separate database per tenant | Strongest — a bug in one tenant's code path physically cannot reach another tenant's data, since it's not in the same database at all | Highest — N databases to provision, migrate, back up, and monitor as tenant count grows |
| Shared database, separate schema per tenant | Strong — one database instance, but each tenant's tables are namespaced apart | Moderate — one instance to operate, but schema-per-tenant migrations and connection routing add real complexity |
| Shared database and tables, `tenant_id` column on every row | Weakest by default | Lowest — one schema, no per-tenant provisioning |

The shared-table approach is not automatically unacceptable, but its safety
depends entirely on **never trusting application code alone** to add the
right `WHERE tenant_id = ...` filter every time, everywhere. A single
missed filter anywhere in the codebase is a real, silent data leak — and
"remember to always filter correctly" is exactly the kind of discipline
that erodes as a codebase grows and more people touch it.

## Recommendation for ClaimAssist specifically

Given the sensitivity of this data: **shared database with separate
schemas per tenant as the floor**, with **PostgreSQL Row-Level Security
(RLS) as a mandatory second layer if shared tables are used anywhere**
(e.g. for tables where per-tenant schemas would be impractical). RLS
matters specifically because it moves the isolation guarantee from
"application code remembered to filter" to "the database itself refuses to
return rows outside the current session's tenant, even if the application
query forgot to ask" — a real defense-in-depth layer, not a redundant one.
Pure shared-table-with-no-RLS is not recommended for this system given what
it handles.

## How this maps onto what's already built

- **Postgres (claims/policies) and pgvector (`chunks` table, Phase 1)**
  would both need a `tenant_id` column, with RLS policies enforcing that a
  connection can only see its own tenant's rows regardless of what the
  query asks for.
- **Vector similarity search specifically** has its own version of the same
  trade-off: filtering by `tenant_id` on every similarity query (cheaper,
  same shared-table risk) versus maintaining genuinely separate indexes per
  tenant (stronger isolation, more indexes to manage as tenant count grows)
  — the same strength-versus-operational-cost curve as the SQL-level
  decision above, not a separate problem.
- **The enterprise API's OAuth2 tokens** (Phase 3's build) would need a
  `tenant_id` claim alongside the existing scopes, and every downstream
  call the agent's tools make would need to thread that tenant context
  through, never accepting a claim/policy ID lookup that isn't scoped to
  the caller's own tenant, even if the ID happens to be well-formed.
- **The SSO identity token** (see
  [phase-3-sso-design.md](./phase-3-sso-design.md)) is where this tenant
  context should originate for human users — a case worker's session
  should carry their tenant affiliation from login onward, not have it
  re-derived or re-checked ad hoc at each layer.

## Other isolation concerns beyond query filtering

- **Encryption keys per tenant** — separate encryption-at-rest keys, so a
  key compromise affecting one tenant doesn't expose every other tenant's
  data too.
- **Audit logging tagged per tenant** — every tool call, retrieval, and
  model call (this is also Phase 4's territory) needs to record which
  tenant it was scoped to, both for compliance and for detecting an
  isolation failure after the fact.
- **Per-tenant rate limiting/quotas** — the "noisy neighbor" problem: one
  tenant's heavy usage shouldn't be able to degrade service for another.
  The rate limiter built in this phase
  ([phase-3-integration-build.md](./phase-3-integration-build.md)) is
  already per-API-key, which is a reasonable starting point for this, since
  each tenant would reasonably get its own key(s).

## What real production scale would require that this doc doesn't cover

- **An actual decision**, not just a menu of options — which of the three
  architectures to commit to depends on real constraints this toy project
  doesn't have: how many tenants, how large each one's data is, and what
  specific compliance/contractual isolation guarantees a real client would
  demand in writing.
- **Migration strategy** — how tenants get onboarded/offboarded, and what
  happens to a tenant's data on offboarding (deletion, export, retention
  requirements).
- **Testing isolation, not just designing it** — proving the isolation
  boundary actually holds (e.g. an automated test that attempts a
  cross-tenant read and asserts it's rejected) is a real piece of future
  work, not covered by writing the design down.
