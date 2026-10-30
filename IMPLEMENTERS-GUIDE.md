# Implementer's Guide for Governed Agent Federation

This guide is non-normative. It accompanies [OAuth 2.0 Profile for
Governed Agent Federation][core] (the core profile), [Agent Resolution
Input Profiles for Governed Agent Federation][INPUTS], [Identity
Continuation Profile for Governed Agent Federation][CONTINUATION],
[Human Oversight Profile for Governed Agent Federation][OVERSIGHT], and
[Governed Agent Lifecycle Profile for SCIM and OAuth][AGENT-LIFECYCLE].
Those documents define every requirement, and they govern wherever this
guide differs
from them. Nothing here is needed to implement them; the guide explains
the flows, collects the configuration a deployment needs, and records
deployment tradeoffs. The [architecture overview](ARCHITECTURE.md) explains
the problem, the principles, and how the drafts fit together. Section
names link to the editor's copy of the profile that defines them.

The core comes first; a builder of one role can stop there. Optional
capabilities follow, each naming the roles that build it.

**The core**

* [Primer: two grants, one identity model](#primer-two-grants-one-identity-model)
* [What each role builds](#what-each-role-builds)
* [Federation configuration](#federation-configuration)
* [Configuration exchanged between implementations](#configuration-exchanged-between-implementations)
* [Distributed platforms and key use](#distributed-platforms-and-key-use)
* [Intermediate adoption](#intermediate-adoption)
* [Errors and recovery](#errors-and-recovery)

**Optional capabilities**

* [Continuation through gateways](#continuation-through-gateways): the
  IdP, a gateway and its RAS, and target RASes
* [Human oversight](#human-oversight): the IdP, the RAS, the client, and
  the API or MCP server
* [Authorization decisions with AuthZEN](#authorization-decisions-with-authzen):
  the API or MCP gateway
* [Transaction Tokens inside a resource domain](#transaction-tokens-inside-a-resource-domain):
  the resource domain
* [Risk signals](#risk-signals): the IdP, platforms, and resource
  domains
* [Platform-hosted agents](#platform-hosted-agents): the platform and
  the IdP

**Deployment patterns**

* [Sub-agents and orchestrators](#sub-agents-and-orchestrators)
* [Credential brokers](#credential-brokers)
* [Adoption tradeoffs](#adoption-tradeoffs)

## Primer: two grants, one identity model

An OAuth client runs one or more agents. The IdP that governs those
agents decides which agent a request identifies and what that agent may
request. The resource domain decides what access it will grant. The core
profile carries the IdP's decision in one of two grants, both requested
from the IdP with OAuth Token Exchange and redeemed at the resource
authorization server (RAS) with the JWT bearer grant type. The [Protocol
Overview][overview] shows the same transaction as a figure.

Both grants begin with agent resolution at the IdP. The client
authenticates, and the IdP takes an agent-resolution input from that
request:

* A **dedicated client**, one OAuth client per agent, authenticates with
  `private_key_jwt`. The authenticated client identity is the input
  (authentication-context resolution), so the request carries no
  separate workload credential. The client and IdP of every
  implementation support this input.
* A **shared client**, such as a platform's single sign-on client,
  authenticates as itself and presents an existing platform JWT that
  names the agent's workload (presented-evidence resolution). An
  implementation that claims generic shared-client interoperability
  supports this input.

The IdP validates the input, maps it to an Agent Principal through an
exact Identity Binding, and checks the Client Association that permits
this client to use that binding, with that credential class, for the
requested acting relationship. The input profiles companion adds SPIFFE
and Client Attestation inputs that resolve the same way.

### Delegated access with ID-JAG

The agent acts for a user.

1. The user signs in to the client through the IdP. The client holds an
   ID Token issued to it.
2. The client sends a token exchange request to the IdP with the ID
   Token as `subject_token`, `requested_token_type`
   `urn:ietf:params:oauth:token-type:id-jag`, the RAS issuer as
   `audience`, exactly one `resource`, and a non-empty `scope`. A shared
   client adds its platform JWT as `actor_token`. In the bound profile,
   the request carries a DPoP proof.
3. The IdP resolves the agent and the user separately, checks the
   Delegation Authorization for that agent, user, client, target, and
   authority, and issues an ID-JAG. Its `sub` identifies the user, its
   `act` names the Agent Principal (`act.iss` is the IdP, `act.sub` the
   agent), and its `client_id` is the client's registration at the RAS.
   A bound grant carries `cnf.jkt`.
4. The client redeems the ID-JAG at the RAS, authenticating with its RAS
   registration and, for a bound grant, proving the grant key.
5. The RAS validates the grant, correlates the Agent Principal with its
   local agent record, resolves the user, and enforces the actor gate:
   may this agent act for this user here? It issues an access token with
   the user as subject and `act` unchanged.
6. The API validates the access token and enforces the user's
   authority and the actor gate, directly or by relying on a validated
   RAS authorization that satisfies resource policy.

### Self-acting access with WAG

The agent acts for itself, with no user.

1. The client sends a token exchange request with
   `requested_token_type` `urn:ietf:params:oauth:token-type:wag`. A
   dedicated client repeats its authentication JWT, byte for byte, as
   `subject_token`; a shared client presents its platform JWT as
   `subject_token`. No `actor_token` is sent.
2. The IdP resolves the agent as before, checks the Agent Authorization
   for the agent's own access, and issues a Workload Authorization Grant
   (WAG) whose `iss` is the IdP and whose `sub` is the agent.
3. The client redeems the WAG at the RAS. The RAS checks its explicit
   type, correlates the agent, and issues an access token whose subject
   is the local agent principal, with no `act` and no refresh token.
4. The API enforces the agent's own authority.

### What stays the same

In both grants, the IdP never lets a request parameter choose the
resolution mode, the grant names exactly one resource, an unbound grant
is single-use, and the RAS correlates agents only by the exact
(issuer, agent) pair. The two adoption profiles differ only in grant
protection: bound governed agent access requires DPoP at both token
endpoints, and governed agent access permits unbound grants only where
trusted policy explicitly permits them for the client, trust
relationship, and resource. Access-token protection (DPoP, mutual TLS,
or bearer use) follows trusted client and resource configuration; the
RAS issues a sender-constrained access token unless the resource
explicitly permits bearer tokens.

## What each role builds

| Role | Builds | Start with |
|---|---|---|
| Client | `private_key_jwt` authentication at the IdP and the RAS; the token exchange request; grant redemption; DPoP where the profile or resource requires it; a separate grant for each agent and resource | [Token Exchange Request][issuance-request], [Redemption Request][redemption-request] |
| IdP | Input validation and Identity Binding; Client Association; Delegation or Agent Authorization; ID-JAG or WAG issuance; the client registration association that supplies the grant's `client_id` | [Grant Issuance at the IdP][issuance] |
| RAS | Grant validation and replay protection; Agent Principal correlation; user resolution and the actor gate for delegated grants; access-token issuance and protection | [Grant Redemption at the RAS][redemption] |
| API | Access-token validation; tenant checks; user authority and the actor gate for delegated tokens; the agent's own authority for self-acting tokens | [Access at the Resource Server][api-processing] |

The [Federation Model][model] and [Profiles and Common
Rules][common-rules] hold the definitions and rules every role shares.
[Conformance Claims][scope] lists the sections each role implements and
the mandatory path for each grant, and [Errors and
recovery](#errors-and-recovery) the codes each role returns. The
[conformance suite](conformance/README.md) checks each role's HTTP
responses; many cases also need control of the implementation, such as
minting a grant, disabling a binding, or changing policy, which its
"Test control" column lists for each case.

## Federation configuration

The relationships in the [Federation Model][model] require trusted
configuration, not a particular storage representation or administrative
interface. Existing workload-federation configuration can supply
credential trust and exact identity selectors. The Agent Principal
mapping and separate Client Association are still required, but no new
configuration object types are prescribed.

**At the IdP:**

* **Credential trust:** issuer or trust domain, approved key source,
  algorithms, credential class, and time limits under the selected
  credential specification.
* **Identity Binding** (IdP administrator or approved platform-registry
  import): qualified client or workload identity, Agent Principal, and
  Governance Tenant.
* **Client Association** (IdP administrator): client, permitted binding
  or binding set, acting relationship, and credential class.
* **Resolution mode and proof** (IdP policy with client configuration):
  authentication-context or presented-evidence resolution, with its
  accepted credential classes and proof requirements, per client,
  applicable profile, and target. Request parameters do not select the
  mode ([Agent Resolution Input Validation][actor-inputs]).
* **Target** (IdP administrator): RAS issuer, resources, Target Tenant,
  subject namespace, and authority to assert `aud_sub`.
* **Delegation Authorization** (IdP policy or consent): agent, user,
  client, tenant, RAS, resource, and authority.
* **Agent Authorization** (IdP policy or assignment): the agent's own
  access to the RAS, resource, and authority, for self-acting issuance.
* **Client registration association** (per target RAS): the
  authoritative mapping from the authenticated client to that client's
  registration at the RAS (Section 5 of [ID-JAG]). The IdP derives the
  grant's `client_id` from it ([Issuance
  Prerequisites][flow-configuration]). No companion profile provisions
  it. If the client uses one identifier at both servers, that mapping is
  the identity mapping. A Client ID Metadata Document (CIMD) [CIMD]
  Client Identifier URL provides one identifier at both servers by
  construction.

**At the RAS:**

* **Local principals:** local agent principals and user links,
  provisioned or synchronized for RAS and API processing.
* **Actor gate** (RAS policy): which agents may act for which users,
  per tenant and resource ([Delegated Actor
  Authorization][actor-authorization]).
* **Just-in-time correlation** (optional RAS policy): whether a
  validated grant from a trusted issuer and tenant can create the local
  agent record ([Optional Just-in-Time Correlation][jit-correlation]).

**At the API:** trust in the RAS's access tokens, through its keys or
its introspection endpoint, and in the IdP namespaces it may assert in
`act`; how delegated and self-acting tokens are told apart and where
the tenant is carried; and how the actor gate is enforced ([RAS and
API](#ras-and-api)).

**At the client and each authorization server:**

* **Client registration** (the client, at each authorization server):
  registration and authentication keys, or CIMD where supported; each
  server consumes the corresponding metadata.
* **Access-token protection** (RAS and client): protection per resource
  for client, RAS, and API use. `token_type` distinguishes DPoP, but not
  mutual TLS from bearer ([Access-Token
  Protection][access-token-protection]).

**Across the deployment:**

* **Target Tenant binding:** one Target Tenant, configured once. The
  tenant-specific resource URI ([Token Exchange
  Request][issuance-request]), the resource domain's provisioning
  context, and any Shared Signals stream ([AGENT-LIFECYCLE]) carry it
  consistently. The core profile assumes deployments configure these
  carriers to agree.
* **Applicable profile** (client, IdP, RAS, and resource policy):
  profile and minimum requirements per client, trust relationship, and
  resource, which each role enforces as applicable to it ([Profile
  Applicability and Downgrade Prevention][discovery]).

Validation occurs while a request is processed, not when an Agent
Principal, Identity Binding, or Client Association is created. Keys and
metadata may already be held. Their retrieval and refresh follow the
rules of the source that supplies them ([Agent Resolution
Inputs][evidence], [Grant Validation][redemption-validation],
[Authorization Server and Client Metadata][metadata]).

Creating and changing bindings and associations, including imports from
platform registries, is an administrative act outside the core profile
([Provisioning and linking](#provisioning-and-linking)).
[AGENT-MANAGEMENT] defines a proposed platform-to-IdP management
interface for it.

[AWS Workload Identity Binding][aws-example] applies the model to an AWS
Security Token Service (STS) workload credential, and [INPUTS]
illustrates a shared client with SPIFFE.

### Provisioning and linking

Provisioning, account linking, and lifecycle propagation are deployment
choices. Useful controls include:

* authenticated link changes, or verified control of both accounts in a
  user-linking flow;
* just-in-time accounts and correlations authorized by issuer and tenant
  ([Optional Just-in-Time Correlation][jit-correlation]);
* no silent merges or reactivation of disabled accounts;
* ownership, groups, and entitlements retained with their principal, and
  audited link and binding changes; and
* issuer and tenant context in the external identifier that a
  provisioning protocol carries, such as SCIM's `externalId` [RFC7643].

SCIM [RFC7644] and Agent resources [SCIM-AGENT] are building blocks,
not a lifecycle propagation contract. [AGENT-LIFECYCLE] profiles SCIM,
optional Shared Signals, and applied changes, including missed-event
limits. It is not required for conformance to the core profile; [Agent
Principal Correlation][agent-correlation] and [Authorization Changes and
Revocation][status-changes] state the core profile's guarantees.

No profile defines a portable way to manage Delegation Authorizations,
Agent Authorizations, Continuation Associations, or oversight modes. The
[authority inventory exercise](exercises/authority-inventory/README.md)
asks what products can already report about them before one is chosen.

## Configuration exchanged between implementations

Independently built implementations work together only after each pair
of them exchanges the values below and agrees on the choices the drafts
leave open. Authorization server metadata carries part of it ([Capability
Discovery][capability-discovery]); the rest is configuration, because
the core profile defines no discovery for bindings, associations,
delegations, or local links. The tables cover the mandatory delegated
path under the bound profile, with the value for each item in
[EXAMPLES.md](EXAMPLES.md)'s [first delegated
transaction](EXAMPLES.md#first-delegated-transaction).

The last column names the related cases in the [conformance
suite](conformance/README.md) and how far they go:

* **Direct:** the case fails when the value or rule is wrong.
* **Positive path:** a passing case uses the value, but no case shows
  what happens when it is wrong.
* **Untested:** no case covers it yet.

### Client and IdP

| Item | From | Example value | In metadata | Related cases |
|---|---|---|---|---|
| IdP issuer identifier, the client assertion's sole `aud`, and token endpoint | IdP | `https://idp.example/`; `https://idp.example/token` | Yes (RFC 8414 metadata) | Direct: N02 |
| Client identifier and keys for `private_key_jwt` with `RS256` | Client, through registration | `analysis-client` and its JWK Set | Client metadata or CIMD | Positive path: P1. Direct for assertion replay and `nbf`: N01, N22 |
| The client registration's `grant_types`, permitting token exchange at the IdP ([Client Metadata][client-metadata]) | Client, through registration | `urn:ietf:params:oauth:grant-type:token-exchange` | Client metadata or CIMD | Untested |
| The client's OpenID Connect registration, so ID Tokens name it as audience | IdP | ID Token `aud` `analysis-client` | No | Direct: N05 |
| Token exchange for ID-JAG, and the resolution mode: the dedicated client's own authentication, with no actor token | Agreed; IdP configures | Authentication-context resolution | Token exchange and ID-JAG support only; the mode is configuration ([Agent Resolution Input Validation][actor-inputs]) | Positive path: P1 |
| The minimum profile for this client and target: bound, with DPoP at issuance | Agreed | `urn:ietf:params:oauth:grant-profile:id-jag-agent-federation`; DPoP `ES256` | DPoP algorithms only; the minimum is configuration ([Profile Applicability and Downgrade Prevention][discovery]) | Direct: N03 |
| The targets the client may request: RAS issuer as `audience`, one resource per grant, and scopes | IdP | `https://ras.example/`; `https://api.example/tenants/acme-data/`; `files.read` | No | Direct for one resource: N04. Direct for scope beyond the delegation: N25 (`invalid_scope`) and N28 (a categorical prohibition, `actor_unauthorized`). Positive path: P1 |

### IdP and RAS

| Item | From | Example value | In metadata | Related cases |
|---|---|---|---|---|
| IdP issuer and grant signing keys | IdP | `https://idp.example/`; its JWK Set | Yes (`jwks_uri`) | Positive path: P2 |
| Authority for the IdP to assert agents in `act` under its issuer ([Grant Validation][redemption-validation]) | RAS trust configuration | Agents of `https://idp.example/` | No | Positive path: P2 |
| The user subject namespace: what the grant's `sub` identifies at this RAS, and whether the IdP may assert `aud_sub` ([Subject Resolution][idp-subject-resolution]) | Agreed, as part of the SSO relationship | `alice-ras` | No | Positive path: P2 |
| RAS issuer, the grant's `aud`, and token endpoint | RAS | `https://ras.example/`; `https://ras.example/token` | Yes | Positive path: P2 |
| Resources the RAS serves, and each one's Target Tenant | RAS, to the IdP | `https://api.example/tenants/acme-data/` in `acme-data` | No | Direct for resource matching: N14. Positive path: P1, P2 |
| Client registration association: each IdP client's registration at the RAS, which becomes the grant's `client_id` ([Issuance Prerequisites][flow-configuration]) | RAS, to the IdP | `analysis-client` to `analysis-api` | No | Direct: N13 |
| The minimum profile per client and resource, enforced at redemption | Agreed | `urn:ietf:params:oauth:grant-profile:id-jag-agent-federation` | No; the minimum is configuration | Direct for grant binding: N10, N11, N12 |
| Agent records: the (IdP issuer, agent identifier) pairs the RAS correlates, provisioned in advance or created just in time ([Agent Principal Correlation][agent-correlation]) | IdP or its connector, to the RAS | (`https://idp.example/`, `agent-42`) to `service-principal-42` | No | Direct: N15 for a disabled agent and N27 for an uncorrelated one, both `invalid_grant` |
| What opens the actor gate at the RAS for an agent and a user ([Delegated Actor Authorization][actor-authorization]) | RAS policy, agreed with the IdP's operator | An entry for `agent-42` and `user-108` in `acme-data` | No | Direct: N16 |

### Client and RAS

| Item | From | Example value | In metadata | Related cases |
|---|---|---|---|---|
| Client registration and keys at the RAS, with the RAS issuer as the assertion's `aud` | Client, through registration | `analysis-api` and its JWK Set | Client metadata or CIMD | Positive path: P2. Direct for the grant's `client_id`: N13 |
| The client registration's `grant_types`, permitting the JWT bearer grant at the RAS ([Client Metadata][client-metadata]) | Client, through registration | `urn:ietf:params:oauth:grant-type:jwt-bearer` | Client metadata or CIMD | Untested |
| Before starting the path, the client verifies that the RAS advertises a profile meeting the configured minimum, supports the JWT bearer grant, and offers compatible access-token protection ([Capability Discovery][capability-discovery]) | RAS advertises; client verifies | `authorization_grant_profiles_supported` includes `urn:ietf:params:oauth:grant-profile:id-jag-agent-federation`; `grant_types_supported` includes `urn:ietf:params:oauth:grant-type:jwt-bearer` | Yes | Untested: the suite does not retrieve metadata |
| DPoP at the token endpoint, proven with the grant's key | RAS | `ES256`; the same key K | DPoP algorithms | Direct: N11, N12 |
| Access-token protection per resource ([Access-Token Protection][access-token-protection]) | Agreed with the resource | DPoP | `token_type` in the response, which does not tell mutual TLS from bearer | Positive path: P2 |

### RAS and API

| Item | From | Example value | In metadata | Related cases |
|---|---|---|---|---|
| RAS issuer and access-token signing keys | RAS | `https://ras.example/`; JWT access tokens validated offline | Yes (`jwks_uri`) | Positive path: P3, P4 |
| Which IdP namespaces the RAS may assert in `act` ([Access at the Resource Server][api-processing]) | API trust configuration | Agents of `https://idp.example/` | No | Positive path: P3 |
| How the API tells the governed delegated population apart ([Profile Applicability][api-applicability]) | Agreed | Client `analysis-api` with the `acme-data` audience | No; the core defines no in-band discriminator | Direct: N18. Positive path for a separate self-acting registration, with minted tokens: S08 |
| Where the tenant is carried | Agreed | The tenant-specific resource URI as `aud` | No | Direct: N17 |
| Access-token protection and scopes per resource | API, to the RAS | DPoP; `files.read` | Protected Resource Metadata, where the API publishes it | Direct for key binding: N19. Scope, against the reference's policy service: S07 (`insufficient_scope`) |
| How the API enforces the actor gate: direct evaluation, or reliance on validated RAS authorization with sufficient scope and freshness. The RAS enforces the gate in either case | Agreed | The API evaluates the gate directly | No | Direct: N20 at the API, N16 at the RAS |
| How fresh authorization must be: introspection caching and the disablement delay | Agreed | Offline JWT validation; 600 s tokens | No | Untested |

### Optional exchanges within the core

These core features are optional. A pair of implementations that uses
one also exchanges or agrees on its item:

| Item | Between | From | Example value | In metadata | Related cases |
|---|---|---|---|---|---|
|  Refresh tokens ([Optional RAS Refresh Tokens][ras-refresh]) | Client and RAS | RAS policy | None | No | Direct after a deferred redemption, against the reference: D13, D14, D15, D21, D22. Otherwise untested: P2 notes a refresh token but does not fail  |
|  Introspection endpoint and the API's credentials for it, where access tokens are opaque ([Optional Opaque Access Tokens and Introspection][introspection]) | RAS and API | RAS | Not used | Introspection endpoint | Direct against the reference, without caching: S12 for an inactive token, S13 for a delegated response without `act`. Positive path: S10, S11  |
|  Whether the API delegates evaluation to a policy service, which then receives the user, agent, client, tenant, and token constraints only from the validated token or introspection response and from trusted configuration ([Optional Policy Services][policy-services]) | RAS and API | API | No policy service | No | Direct against the reference, whose policy service the suite controls: S02 to S07, S09, S11, and for the error selection order, S14 to S19. Positive path: S01, S08, S10  |

### Choices to agree

The drafts let each of these vary. Two implementations that choose
differently fail at the boundary between them, often with an error that
names neither choice:

| Choice | What the drafts allow | The example and the reference |
|---|---|---|
| Telling token populations apart | Separate client registrations, audiences, or issuers, or a bilateral contract such as an introspection member | Separate configuration per client and audience |
| Carrying the tenant | The tenant-specific resource as audience, a configured tenant claim, or authoritative token context | The resource as audience |
| Re-redeeming a bound grant | Once, or again under explicit policy with a fresh proof | Once |
| Clock skew and DPoP proof age | A few minutes; DPoP server nonces optional | 60 s each; no nonces |
| Grant lifetime | The configured limit, recommended at most five minutes | 300 s |

Optional capabilities add their own exchanges, which their chapters
list; lifecycle propagation adds a provisioning connection or a Shared
Signals stream ([AGENT-LIFECYCLE]), and SCIM management the connector's
authority at the IdP ([AGENT-MANAGEMENT]).

## Distributed platforms and key use

A sender-constrained credential requires proofs from its bound key,
through local custody or an authorized signing arrangement. The core
profile defines no transition to another key ([Excluded
Compositions][excluded-compositions]), so bound-grant issuance and
redemption require the same key holder.

A DPoP access token is usable only by:

* a broker holding the token's bound key, including one proxying an
  authorized worker request; or
* a worker that holds the same key or obtains request-specific proofs
  from its authorized key holder.

Remote signing interfaces are outside the core profile. Remote signing
or shared key custody does not establish an independent worker binding
and expands the trusted computing base.

A control plane and worker that cannot share the grant proof key use
governed agent access instead. The control plane obtains an unbound
grant, and the worker redeems it with its own DPoP proof. That proof
binds the access token to the worker's key ([Grant
Protection][grant-protection]).

## Intermediate adoption

To adopt governed agent access, the parties configure
`urn:ietf:params:oauth:grant-profile:id-jag-governed-agent` instead of
the bound profile and explicitly permit grants without sender
constraint. With bearer access also permitted for the resource, the
messages of the core profile's [dedicated-client
walkthrough][walkthrough] change only as follows:

| Message | Change |
|---|---|
| Exchange request and ID-JAG | Omit the DPoP header; the issued grant has no `cnf` |
| Redemption request | Omit the DPoP header; retain client authentication and all request parameters |
| Access-token response and API request | Use the walkthrough's bearer variant |

The client assertion, Identity Binding, Client Association, user and
actor identities, scope, tenant checks, and actor gate are unchanged. An
unbound grant can instead obtain a DPoP-bound access token by presenting
a valid proof at redemption ([Grant Protection][grant-protection]).

## Errors and recovery

The drafts, and the specifications they build on, fix the codes each
role returns; this index points to their tables, which govern.

| Role | Returns | Defined in | Cases |
|---|---|---|---|
| IdP | The client authentication method's error, such as `invalid_client`, for a failed client assertion. `invalid_request`: a malformed request, or a missing DPoP proof under the bound profile. `invalid_grant`: the subject, input, binding, agent, or Governance Tenant cannot be resolved. `actor_unauthorized` (HTTP 400): no Client Association, no applicable Delegation Authorization, or a categorical prohibition. `invalid_scope`: beyond the authorization's scope ceiling. `invalid_target`: the target, its Target Tenant, or the client registration association. Self-acting issuance uses `unauthorized_client` (no Client Association) and `invalid_target` (not authorized for the target) where delegated issuance uses `actor_unauthorized` | core: [Token Endpoint Errors][errors]; [Issuance Errors][issuance-errors] | N01 to N09, N21, N22, N25, N28 |
| RAS | `invalid_grant`: an invalid or replayed grant, a missing proof or one of another key, another client, or an uncorrelated, disabled, or restricted agent. `actor_unauthorized` (HTTP 400): policy, including the actor gate, refuses an ID-JAG's delegation. `invalid_target`: policy refuses a WAG, or the resource is outside the grant | core: [Redemption Errors][redemption-errors] | N10 to N16, N23, N26, N27 |
| API | The first failure in the core's order, whatever order it checks in: token or proof (401); actor claims or tenant (401 `invalid_token`); actor gate (403 `actor_unauthorized`); scope (403 `insufficient_scope`); any other denial (403 with no `error` attribute, and no body that conveys either code). HTTP 503 when a check cannot complete, unless a failure is established and no unfinished check ranks earlier than it | core: [Error Responses][resource-errors] | N17 to N20, N24, S02 to S07, S14 to S19 |
| Continuation (optional), at the IdP | `invalid_continuation`: the chain has ended. `invalid_grant`: past the hop's deadline or a chain limit. `unauthorized_client`: no Continuation Association or restriction permits the client. HTTP 503: shared state cannot be confirmed | continuation: [Errors][cont-errors] | None yet |
| Oversight (optional), at the IdP and the RAS | Without the opt-in, or where the RAS cannot defer, the ordinary refusal (`actor_unauthorized` delegated, `invalid_target` self-acting). Polls: `authorization_pending`, `slow_down`, `access_denied`, `expired_token`, `invalid_dpop_proof`. `invalid_grant`: at the IdP, a poll after delivery; at the RAS, any presentation of an accepted grant other than recovery, and a refresh the kept approval no longer permits. A CAI refuses a deferred redemption's token with `invalid_request` | oversight: [Client Opt-In][ov-opt-in]; [Redemption Opt-In][ov-redemption-opt-in]; [Recovery][ov-recovery]; [Redemption Resolution][ov-redemption-resolution]; [Refresh and Continuation][ov-redemption-refresh] | D01 to D22, at the RAS; IdP deferral and the CAI refusal untested |

An API that relies on a policy service for the actor gate needs the
decision to say whether the gate denied, or it evaluates the gate
itself ([Optional Policy Services][policy-services]). A decision it
cannot obtain or interpret is a check that cannot complete.

A client recovers as the core's [recovery list][implementation-client]
describes: at most one bounded attempt after `invalid_client` or
`invalid_grant`, a corrected request after `invalid_scope`, a token
with more authority after `insufficient_scope`, a retry after a 503,
and otherwise no automatic retry of the unchanged request. After
`invalid_continuation`, a gateway should answer the agent with 401
`invalid_token`; after a continuation `invalid_grant`, it must not, and
fails the request with an error of its own API instead ([Gateway
Requirements][cont-gateway]).

### One request, several outcomes

A `PUT` of `report-7` needs `files.write`. With the examples' [first
transaction](EXAMPLES.md#a-write-the-token-does-not-cover), where the
API evaluates the actor gate itself, except in the fourth row:

| Token scope | Actor gate | Other checks | Response |
|---|---|---|---|
| `files.read` | Permits | Pass, or Alice cannot write | 403 `insufficient_scope`: scope ranks before her permissions |
| `files.read` | Denies | Any | 403 `actor_unauthorized` |
| `files.read` | Permits | Policy service unreachable | 403 `insufficient_scope`: no unfinished check ranks earlier |
| `files.read` | Unreachable policy service owns it | — | 503: the unfinished gate ranks before scope |
| `files.write` | Permits | Alice cannot write, with or without a client-policy check that cannot complete in the same row | 403 with no `error` attribute |

The nearest conformance cases are S07, S14, S18, S19, and S04.

## Continuation through gateways

[CONTINUATION] lets a gateway continue an agent's request to a resource
in another domain, under the same Agent Principal and, for delegated
access, the same user. A gateway combines roles: it is the API for the
agent's access token, and the continuing client at the Continuation
Assertion Issuer (CAI), the IdP, and the tool's RAS. Its operator's RAS
is typically the continuation-aware RAS and CAI.

A gateway deployment adds this configuration to the [federation
configuration](#federation-configuration):

| Party | Configuration |
|---|---|
| IdP | Tenant policy permitting continuation; Continuation Associations for the gateway; the gateway's client registration and canonical actor identity; trust in the gateway's CAI (Section 7.3 of [ICA]); the gateway's registration at each target RAS, for each acting relationship the target serves separately; a finite continuation window ([Governed Chain Authorization][cont-window]), where it is configured, and how finely, being the deployment's choice; the hop-count limit; and any [restrictions][cont-restrictions] recorded in chain authorizations or Continuation Associations |
| Gateway's RAS | Continuation-aware processing and advertisement; assertion issuance; the gateway's registration as the client that operates the gateway resource; the gateway's canonical actor identity, as the IdP holds it |
| Gateway | A client credential for each server and a DPoP key |
| Target RAS | A client registration for the gateway, one for each population where delegated and self-acting access are distinguished by registration; DPoP support |

The CAI's placement gives these topologies:

| Topology | CAI | Use |
|---|---|---|
| Gateway authorization server | The gateway's own RAS (Section 8.1 of [ICA]) | The gateway operator runs an authorization server for the gateway resource; the baseline |
| Shared authorization server | A separate CAI trusted for that RAS (Section 5.4.6 of [ICA]) | The gateway is a resource server behind an API-management or enterprise authorization server |
| Gateway behind a gateway | Each gateway's RAS | Each hop is a governed continuation; every onward grant names the same agent, and `continuation_via` lists each gateway on the path |
| IdP-issued gateway tokens | None | Not applicable: there is no accepted hop to continue ([Scope][cont-scope]) |

[Gateway Requirements][cont-gateway] lists what the gateway does with
each request, and [Implementation Considerations][cont-implementation]
covers continuation-window and agent-session sizing.

## Human oversight

The [oversight profile][OVERSIGHT] adds a person to governed access.
With a human in the loop, an approver decides on the exact request
before a grant issues, before a RAS issues access, or before an action
executes. With a human on the loop,
grants issue at once, and an overseer can see each one and end it.
Without the profile, the core issues grants under standing
authorization alone, which the profile calls human out of the loop.
Policy selects the mode for each agent, acting relationship, user,
client, target, and authority, usually as a condition of the
Delegation or Agent Authorization; a client's opt-in to deferral never
selects or lowers it ([Oversight Modes][ov-modes]).

| Mode | Where | Mechanism | Suits |
|---|---|---|---|
| Human in the loop | IdP issuance, including continuation | [Deferred governed issuance][ov-deferred]: the IdP holds the token exchange under [Deferred Token Response][DTR] until an approver decides, then issues the grant the request would have produced | Authority whose misuse cannot be undone, such as writing, paying, or sharing outside the tenant |
| Human in the loop | RAS redemption | [Deferred redemption][ov-redemption]: the RAS holds the redemption until an approver that RAS policy designates decides, then issues the access token the redemption would have produced; the authorization is not eligible for continuation | A resource domain that approves each agent's access itself, such as a data steward approving an agent's first access to a tenant |
| Human in the loop | Each action at an API or MCP server | [Per-action oversight][ov-per-action]: the server holds the call until an approver decides on that call | A sensitive operation, object, or argument within authority the agent already holds |
| Human on the loop | IdP issuance | [Supervised issuance][ov-supervised]: grants issue at once; overseers see each one and can end it | Work that cannot wait for a person, at a target where an intervention takes effect within a documented bound |
| Human out of the loop | Every decision point | The core's standing authorization | Routine authority, certified periodically |

Each decision point applies its own mode. An approval at the IdP does
not satisfy a RAS that requires its own approval for a redemption, or a
resource domain that requires a person to decide on an action, and no
claim in the grant tells the RAS that anyone approved.

A deployment that uses oversight adds this configuration to the
[federation configuration](#federation-configuration):

| Party | Configuration |
|---|---|
| IdP | The mode in issuance policy, configured at the IdP directly, since the SCIM management profile has no attribute for it; the approvers each policy designates, and the authentication strength each requires; an approval channel, such as [CIBA] with a `binding_message` that describes the request; a maximum pending lifetime for each policy; Deferred Token Response in polling mode, with deferral codes bound to the client and its DPoP key; for supervised issuance, the overseers and the channel that gives them each grant's issuer, `jti`, request context, and issuance time |
| RAS, for deferred redemption | The mode in RAS policy, and the approvers it designates; `deferred_token_response_supported` in its metadata; an approval channel, such as an access request service under [ARAP], with one access request for each pending redemption and the approval kept unchanged; a maximum pending lifetime and an absolute authorization expiration that starts when the grant is accepted; no deferral for a resource configured for mutual-TLS access tokens; the accepted grant, or its digest, kept for recovery; the resulting authorization never eligible for continuation |
| Client | `completion_mode=deferred` and a DPoP proof on each request that can wait, whatever its authentication method; polling with the same key, no faster than the returned `interval` and slower after `slow_down`; stopping on `access_denied` or `expired_token`; cancelling by revoking the deferral code; never retrying a denied or expired request as self-acting access, under another client, or under a lower adoption profile; after losing a deferred redemption's response, repeating the redemption with the same grant, a fresh proof of the same key, and the same parameters ([Recovery][ov-recovery]) |
| Gateway | The client behavior above for its continuation exchanges; reporting the wait to the agent through its own interface, such as an MCP task |
| API or MCP server | Per-action policy and its approvers; holding a call, or refusing it in a way the agent can request; an approval page that authenticates the approver and binds the decision to the call, its arguments, and the token's subject, agent, client, and tenant |
| Overseers | Supervised-issuance notices, and the interventions of the [playbook's runbooks](PLAYBOOK.md#runbooks-stop-and-restore), each with a documented intervention bound |

The conformance suite tests deferred redemption against the reference,
whose Access Request Service it controls: D01 to D22. WAG deferral,
mutual-TLS resources, continuation ineligibility, and grant-derived
revocation while pending are untested.

### How long a request can wait

A pending request is the deferring server's state, not a credential,
and what it yields keeps the core's lifetime limits
([Deferring][ov-deferring]):

* **Root issuance.** A pending request ends no later than the subject
  credential expires, or any agent-resolution input that bounds the
  grant, such as a platform JWT. ID Tokens are often short-lived, so a
  wait of hours needs a subject credential that expires later, such as
  a refresh token. An approval late in the window yields a shorter
  grant.
* **Continuation.** The pending request holds the Continuation
  Assertion's replay reservation until the request ends, even past the
  assertion's own expiry, so the assertion cannot be presented again
  ([Continuation][ov-continuation]). The chain's limits count
  continuations that have issued, so a continuation approved after a
  limit was reached is refused at resolution; the gateway then needs a
  new assertion and, where policy requires it, a new approval. The IdP
  checks the hop's continuation deadline when it receives the request,
  so an approved continuation can issue after that deadline.
* **Redemption at the RAS.** The RAS accepts the grant once and sets
  the absolute authorization expiration then. The pending redemption
  ends by that expiration and the maximum pending lifetime; the grant's
  `exp` limits only acceptance, so [recovery][ov-recovery] works after
  it. Each access token, including one issued on refresh, expires no
  later than the approval expiry, any enforcement deadline, and the
  absolute expiration ([Deferring a
  Redemption][ov-redemption-deferring]; [Redemption
  Resolution][ov-redemption-resolution]; [Refresh and
  Continuation][ov-redemption-refresh]).
* **Re-checks.** At resolution the deferring server checks again that
  the agent is active, the authorization still permits the approved
  authority, and the user resolves as before; for root issuance, the
  binding and association; for a continuation, the chain and the
  Continuation Association; and at the RAS, the actor gate and the
  approval. A change that still holds then ends the request with
  `access_denied` ([Resolution][ov-resolution]; [Redemption
  Resolution][ov-redemption-resolution]). Until then the request stays
  pending: the profile does not require a change to cancel it, except
  that grant-derived revocation of the grant ends a pending redemption
  at a participating RAS.

Approvers asked too often approve without reading ([Approval
Fatigue][ov-fatigue]). Reserve the human in the loop for authority that
warrants it, limit how many pending requests one agent can hold, and
make routine approvals standing authorization through a reviewed change
to the Delegation or Agent Authorization; approving a request never
makes that change.

### Approval at an MCP gateway

When IdP policy requires approval before an onward grant issues, the
gateway sends its continuation exchange with `completion_mode=deferred`
and a DPoP proof, and reports the wait to the agent through its own
interface, such as an MCP task that stays `working`. Alice sees the
agent, the gateway as continuing client, the tool's domain, and the
authority. If she denies, or a check or limit fails at resolution, the
poll returns `access_denied`, and the gateway fails the task without
calling the tool on its own authority. The examples' [Approved
continuation](EXAMPLES.md#approved-continuation) shows every message.

### What oversight does not provide

* **Approval visible downstream.** No claim in the grant records an
  approval. An IdP can include `txn` to correlate the grant with its
  approval record, but a RAS or API never treats it as evidence of
  approval or as authority. A resource domain that needs a person
  applies its own decision ([Resolution][ov-resolution]).
* **Approval in place of governance.** An approval is an additional
  condition; it never replaces identity resolution or delegation
  authorization ([External Approval][external-approval]).
* **Approval from the client.** A confirmation an MCP client shows its
  user is client behavior, not an approval. A tool annotation such as
  `destructiveHint` neither selects nor lowers a mode, though a
  deployment can use its own classification of tools to require a
  stricter one ([Model Context Protocol][ov-mcp]).
* **Approval that completes as a token at the IdP.** At the RAS,
  [deferred redemption][ov-redemption] completes an approval as an
  access token, which AROP can realize. At the IdP, asynchronous
  approval with AROP stays an [excluded
  composition][excluded-compositions] of the core. Continuation from a
  deferred redemption is refused: the RAS does not record that
  authorization as eligible ([Refresh and
  Continuation][ov-redemption-refresh]). Whether a later revision could
  permit it is an [open item][ov-open-items] of the profile.
* **Revoking one WAG.** Revoking a single WAG is deployment-specific, so
  supervised self-acting issuance rests on withdrawing the Agent
  Authorization, a Local Suspension, or disabling the agent.
* **The approval channel.** The profile defines no approval channel,
  overseer notice format, or multi-party approval. The channel's
  authentication of the approver is what keeps an agent from approving
  its own requests.

## Authorization decisions with AuthZEN

An API or MCP gateway that delegates authorization to a policy decision
point (PDP) keeps the user, the issuer-qualified Agent Principal, and
the OAuth client distinct, and supplies the tenant and token constraints
([Optional Policy Services][policy-services]). The profiles define no
AuthZEN mapping. This chapter shows where a PDP fits, the use cases, the
inputs an enforcement point must supply itself, and illustrative
requests in the [AuthZEN Authorization API 1.0][AUTHZEN] format. The
[architecture overview](ARCHITECTURE.md#authorization-decisions-with-authzen)
summarizes the points that need care.

### Integration points

```mermaid
flowchart LR
  client["Agent client"]
  idp["Governing IdP"]
  ras["RAS"]
  api["API or MCP gateway"]
  pdp["Policy decision point<br/>AuthZEN"]
  approval["Access request<br/>ARAP, AROP"]
  client -->|"token exchange"| idp
  client -->|"redeem grant"| ras
  client -->|"call a tool"| api
  api -->|"evaluate each action"| pdp
  ras -.->|"evaluate local policy"| pdp
  idp -.->|"semantics it cannot evaluate"| pdp
  api -.->|"requestable denial"| approval
```

| Point | Enforcement point | What is decided | Hook in the profiles | AuthZEN fit |
|---|---|---|---|---|
| Each action | API or MCP gateway | Whether this user and agent may perform this operation on this object | [Optional Policy Services][policy-services] and [Delegated Actor Authorization][actor-authorization]; the conformance suite's S cases try substituting each identity from request attributes | AuthZEN evaluation; [COAZ-MCP][COAZ-MCP] for MCP tool calls |
| Redemption | RAS | Whether to issue an access token under local user, actor, client, tenant, and resource policy | Grant Redemption at the RAS; the core states its policy-service rules for the API, and [deferred redemption][ov-redemption] builds evaluations only from the redemption's resolved values | AuthZEN evaluation; ARAP and AROP when RAS policy requires approval |
| Issuance | IdP | Decisions that depend on tool arguments or business objects, which the IdP need not interpret | Authorization Relationships: resource-domain evaluation, locally or through a trusted policy service | A resource-domain PDP; the AuthZEN Token Issuance profile is not yet composed with governed issuance ([below](#one-identity-model-across-authzen-profiles)) |
| Requestable denial | API | Whether the agent can ask for more access | External Approval; per-action oversight in the oversight profile. A RAS that refuses a redemption does not reveal whether approval could be obtained ([Redemption Opt-In][ov-redemption-opt-in]) | ARAP for the request |

### Use cases

1. **Per-tool decisions at an MCP gateway.** The gateway is the
   enforcement point for each `tools/call`, and COAZ-MCP maps the call
   to an AuthZEN request. With a delegated token, the user is the
   subject and the agent comes from the validated `act`.
2. **Decisions on tool arguments.** The grant carries one resource and a
   scope, such as `files.read` for one tenant; the IdP need not judge
   which file a call touches. A tool's declared mapping carries
   arguments into the action and resource, so the resource domain
   decides at that level, within the token's authority.
3. **Self-acting agents.** A token derived from a WAG has no user. The
   correlated local agent principal is the subject.
4. **Agents reached through gateways.** In a further resource domain,
   `client_id` names the last gateway's registration, and
   `continuation_via`, where the RAS supports path disclosure, lists the
   gateways on the path. A PDP can admit an agent only through approved
   gateways, while the agent remains the actor in `act`.
5. **Requestable denials.** A PDP can deny an action as requestable, and
   ARAP lets the enforcement point submit an access request and
   re-evaluate after approval. A resource-local approval can satisfy an
   additional condition within the token's authority but cannot expand
   it. A new governed grant after approval comes from deferred issuance
   under the [oversight profile][OVERSIGHT] ([Human
   oversight](#human-oversight)), and at the RAS an approval completes
   as an access token through its [deferred redemption][ov-redemption].

Risk signals and approved work are further inputs; see [Risk
signals](#risk-signals) and [Beyond these
drafts](ARCHITECTURE.md#beyond-these-drafts).

### Inputs the enforcement point supplies

The enforcement point builds the protected part of each request from the
validated access token, or an authenticated introspection response, and
trusted configuration, as [Optional Policy Services][policy-services]
requires:

| Attribute | Delegated access | Self-acting access | Source |
|---|---|---|---|
| Subject | The token's `sub`, the local user | The token's `sub`, the correlated local agent principal | Validated token |
| Agent | The validated `act` (`iss` and `sub`) | The subject | Validated token |
| Client | `client_id` | `client_id` | Validated token |
| Tenant | The resource's Target Tenant | The resource's Target Tenant | Trusted configuration |
| Token constraints | `scope`, and the token's resource | `scope`, and the token's resource | Validated token |
| Path | `continuation_via`, where present | `continuation_via`, where present | Validated token |

The enforcement point selects delegated or self-acting processing by the
token population configured for the resource ([Profile
Applicability][api-applicability]), not by whether `act` is present: a
delegated token that lacks `act` is not self-acting. A tool's declared
mapping (Section 8 of COAZ-MCP) can add action, resource, and context
attributes derived from the call. COAZ-MCP treats every attribute a
declared mapping produces, other than the verified subject identifier,
as untrusted input (Section 11.4 of COAZ-MCP). A declared mapping
therefore must not supply or override the attributes in the table, and
policy must not grant identity or privilege on the strength of
attributes it supplies. What the decision must convey back is in
[Errors and recovery](#errors-and-recovery).

### One identity model across AuthZEN profiles

Several AuthZEN profiles take identity from an OAuth token, and each
places the agent somewhere different. A governed token keeps the
subject, the OAuth client, the actor, and the gateways on the path
apart, and never carries a delegation chain: a delegated token has a
single `act`, and every onward grant names the same Agent Principal
("Identity Preservation" in [CONTINUATION]), so the current actor is
also the agent the IdP authorized. The table compares nearest
counterparts; these profiles define no mapping.

| Source | Subject | Agent (actor) | Client | Chain or path |
|---|---|---|---|---|
| Governed token | The user (delegated); the correlated local agent principal (self-acting) | Delegated: `act` (`iss`, `sub`). Self-acting: the subject | `client_id` | No chain; continuing clients in `continuation_via` |
| [COAZ-MCP][COAZ-MCP] Draft 1 | `$token.sub`, or an agreed on-behalf-of claim | `context.agent`, by default `$token.?client_id` | The same default | Not modeled |
| [ARAP][ARAP] with the [Actor Delegation Profile][AUTHZEN-ACTOR] | The principal on whose behalf the operation is performed | `client.actor`, identified by the (`iss`, `sub`) pair of [Actor Profile][ACTOR-PROFILE] | ARAP's `client.id` | Nested `act`, from the immediate actor outward |
| [AROP][AROP] Draft 1 | The principal the token will act as, per grant | `subject.properties.act` | `context.client_id` | Not modeled |
| [Token Issuance][AUTHZEN-ISSUANCE] Draft 1 | `subject.id`: the subject the authorization server intends to issue | No member; `act` is built by the authorization server | `context.client_id` | Not modeled |
| Mission-Bound Runtime Enforcement, [AuthZEN profile][MISSION-AUTHZEN] | The credential's `sub`; for an agent acting for its own workload principal, that principal | Delegated: the leaf of `context.actor.act`. Self-acting: the workload principal in `subject`; the profile calls the client in `context.actor` the immediate actor | `context.actor.client_id` | `context.actor.act`, root to leaf |

Four differences matter for governed deployments:

* **The agent is not the client.** COAZ-MCP's default names the client,
  the same for every agent behind a shared client or gateway
  ([counter-example](#counter-example-the-client-as-the-agent)).
* **A self-acting agent is the subject**, where trusted context
  establishes governed self-acting access; the absence of `act` alone
  does not. The Mission profile places the workload principal in
  `subject` and calls the client in `context.actor` the immediate
  actor: a difference of terminology, not of model.
* **Gateways are clients, not actors.** Governed continuation keeps one
  actor and lists continuing clients in `continuation_via`, which none
  of these profiles reads yet.
* **Issuance and approval need the resolved agent.** Token Issuance has
  no mandatory input for the actor, and a governed IdP decides on the
  Agent Principal it resolved, which for a dedicated client is not the
  requesting client. ARAP leaves the actor out of its approval
  comparison, and AROP does not say which identities an approved token
  carries. The oversight profile profiles AROP only at the RAS ([What
  oversight does not provide](#what-oversight-does-not-provide)).

An enforcement point can map each profile's request into this model
today; the issuance and approval protocols cannot be composed by
mapping fields. [COORDINATION.md](COORDINATION.md) records what the
governed profiles need from each.

### Illustrative requests

The requests below illustrate those rules. Subject types and context
member names are illustrations, not a convention; the profiles leave a
reusable convention to the OAuth mapping profile the AuthZEN working
group plans ([coordination notes](COORDINATION.md)). In each request,
the enforcement point supplies the subject and every `context` member
from the validated token and trusted configuration, with the token's
`scope` and audience grouped as `constraints`; the tool's declared
mapping supplies only `action` and `resource` from the call. The
`context` members are trustworthy because the enforcement point
supplies them, not because a binding defines them.

#### Delegated access at an MCP gateway

The core profile's walkthrough issues this access token (excerpt):

~~~ json
{
  "iss": "https://ras.example/",
  "sub": "user-108",
  "aud": "https://api.example/tenants/acme-data/",
  "client_id": "analysis-api",
  "scope": "files.read",
  "act": {"iss": "https://idp.example/", "sub": "agent-42"}
}
~~~

The agent calls a `read_file` tool with the argument
`"path": "reports/q3.csv"`. The gateway asks:

~~~ json
{
  "subject": {"type": "user", "id": "user-108"},
  "action": {"name": "read_file"},
  "resource": {"type": "file", "id": "reports/q3.csv"},
  "context": {
    "agent": {"iss": "https://idp.example/", "sub": "agent-42"},
    "client": "analysis-api",
    "tenant": "acme-data",
    "constraints": {
      "scope": "files.read",
      "aud": "https://api.example/tenants/acme-data/"
    }
  }
}
~~~

The policy covers both the user's authority and the actor gate for
`agent-42` acting for this user ([Delegated Actor
Authorization][actor-authorization]). A permit cannot widen
`files.read` or reach another tenant. The decision also has to tell the
gateway whether the actor gate denied, so that it can return
`actor_unauthorized` ([Errors and recovery](#errors-and-recovery)).

#### Self-acting access

A token derived from a WAG names the correlated local agent principal
and carries no `act` (excerpt):

~~~ json
{
  "iss": "https://ras.example/",
  "sub": "service-principal-42",
  "aud": "https://api.example/tenants/acme-data/",
  "client_id": "analysis-api",
  "scope": "files.read"
}
~~~

~~~ json
{
  "subject": {"type": "agent", "id": "service-principal-42"},
  "action": {"name": "read_file"},
  "resource": {"type": "file", "id": "reports/q3.csv"},
  "context": {
    "client": "analysis-api",
    "tenant": "acme-data",
    "constraints": {
      "scope": "files.read",
      "aud": "https://api.example/tenants/acme-data/"
    }
  }
}
~~~

The resource is configured for self-acting access, so the local
principal stands for the Agent Principal and the policy evaluates the
agent's own authority. No actor gate applies.

#### Access through gateways

In the continuation profile's [two-gateway variant][cont-two-gateways],
the API in a further domain receives this token, whose RAS supports
path disclosure (excerpt):

~~~ json
{
  "sub": "user-108",
  "aud": "https://api.example/tenants/acme-data/",
  "client_id": "data-files",
  "scope": "files.read",
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "continuation_via": [
    {"iss": "https://gateway.example/", "sub": "tool-gateway"},
    {"iss": "https://data-gateway.example/", "sub": "data-gateway"}
  ]
}
~~~

~~~ json
{
  "subject": {"type": "user", "id": "user-108"},
  "action": {"name": "read_file"},
  "resource": {"type": "file", "id": "reports/q3.csv"},
  "context": {
    "agent": {"iss": "https://idp.example/", "sub": "agent-42"},
    "client": "data-files",
    "path": [
      {"iss": "https://gateway.example/", "sub": "tool-gateway"},
      {"iss": "https://data-gateway.example/", "sub": "data-gateway"}
    ],
    "tenant": "acme-data",
    "constraints": {
      "scope": "files.read",
      "aud": "https://api.example/tenants/acme-data/"
    }
  }
}
~~~

The client is the last gateway's registration, and the agent is still
`agent-42`. A policy that admits `agent-42` only through `tool-gateway`
matches the first path entry. Admitting the path does not by itself
permit reading the file: the policy still needs the user's authority,
the actor gate for `agent-42`, and `files.read`. Path entries authorize
nothing on their own.

#### Counter-example: the client as the agent

COAZ-MCP's default mapping puts `$token.?client_id` in `context.agent`.
For the delegated token above, it would produce:

~~~ json
{
  "subject": {"type": "identity", "id": "user-108"},
  "action": {"name": "tools/call"},
  "resource": {"type": "tool", "id": "read_file"},
  "context": {"agent": "analysis-api"}
}
~~~

Every agent behind `analysis-api`, or behind `data-files` in the
gateway case, looks the same to the PDP, and the client identifier
stands in for the actor, which the core profile forbids. Configure the
enforcement point to supply the agent itself: the validated `act` for a
delegated token population, or the correlated local subject for a
self-acting one, with `client_id` kept as a separate attribute.

## Transaction Tokens inside a resource domain

A resource domain often calls internal services to serve one request.
Transaction Tokens ([TXN-TOKENS]) carry identity and authorization
context through that internal call chain. They are bound to one trust
domain: a Txn-Token "MUST NOT be accepted outside the Trust Domain
identified by the aud claim" (Section 9.2 of [TXN-TOKENS]). Crossing
into another domain therefore uses a governed grant or
[continuation](#continuation-through-gateways), not a Txn-Token.

After the API validates a governed access token, the domain's
Transaction Token Service (TTS) can mint a Txn-Token for the call
chain. [TXN-TOKENS] defines no `act` claim, and recipients ignore
claims they do not understand, so the governed context belongs in
`tctx`, whose contents the TTS determines. An illustrative mapping:

| Txn-Token claim | Delegated access | Self-acting access |
|---|---|---|
| `sub` | The access token's `sub`, the local user | The access token's `sub`, the correlated local agent principal |
| `tctx` | The agent from the validated `act`, the client, the tenant, `continuation_via` where present, and the authorized operation and object | The client, the tenant, `continuation_via` where present, and the authorized operation and object |
| `scope` | As narrow as the transaction allows, and no broader than the access token's authority | The same |
| `req_wl` | The workload that requested the Txn-Token, such as the API | The same |
| `aud` | The resource domain's trust domain | The same |

For the delegated token in the [AuthZEN
examples](#delegated-access-at-an-mcp-gateway), the TTS might issue:

~~~ json
{
  "iat": 1789646470,
  "exp": 1789646530,
  "aud": "api.example",
  "txn": "97053963-771d-49cc-a4e3-20aad399c312",
  "sub": "user-108",
  "scope": "files.read",
  "req_wl": "files-api",
  "tctx": {
    "agent": {"iss": "https://idp.example/", "sub": "agent-42"},
    "client": "analysis-api",
    "tenant": "acme-data",
    "action": "read_file",
    "resource": {"type": "file", "id": "reports/q3.csv"}
  }
}
~~~

The `tctx` member names are illustrations, as in the AuthZEN examples;
the TTS defines them for its domain and takes them from the validated
access token and the entry point's decision. An internal service
evaluates its requested activity against them (Section 12.2 of
[TXN-TOKENS]). The entry point's decision, including the actor gate,
covers downstream work only within the bounds it authorized: here, one
read of `reports/q3.csv`, not every operation within `files.read`.
Where the entry point narrowed the authority, the Txn-Token carries the
narrower bounds.

The continuation profile uses a Transaction Token differently in its
[scheduled variant][cont-scheduled]: as the carrier that tells its
Continuation Assertion Issuer which hop a scheduled run continues.

## Risk signals

The profiles separate signals that change authority from signals that
inform decisions:

| Signal | Effect | Defined in |
|---|---|---|
| SCIM provisioning and feed events to a resource domain | Trigger retrieval of current state; never activate an agent | [Lifecycle][lc-scim-events] |
| CAEP `session-revoked` naming an ID-JAG | Revokes what that grant authorized at participating receivers | [Lifecycle][lc-grant-revocation], optional |
| WISE credential and posture events from a platform to the IdP | Inform IdP policy and monitoring; change no administrative state | [Lifecycle][lc-platform-signals] |
| CAEP `risk-level-change` from the IdP to a platform | Applied under the platform's own policy; not a disablement | [Lifecycle][lc-platform-signals] |

Risk feeds decisions at three points:

* **At issuance.** The IdP authorizes each grant under current policy
  ([Issuance Authorization][issuance-authorization]), so risk can deny
  a grant or narrow its scope.
* **Per action.** A PDP can take risk as context, for example to permit
  only read operations, as the lifecycle profile's [platform-hosted
  example][lc-platform-example] shows
  ([Authorization decisions with AuthZEN](#authorization-decisions-with-authzen)).
* **For continuing work.** A signal that leads to disabling the agent or
  the user, revoking the root credential, or withdrawing the root
  authorization ends governed continuation chains ([Chain
  Ending][cont-chain-ending]). A risk signal alone does not.

How strongly a receiver responds to a medium-confidence signal remains
local policy. These profiles define no risk event for federated
resource domains: `risk-level-change` is profiled only between an IdP
and a platform that hosts agents.

## Platform-hosted agents

A platform that hosts agents and authorizes them for its own resources
can register them with the IdP for governance ([AGENT-MANAGEMENT]) and
apply the IdP's administrative state in its own authorization ([Platform-Hosted
Agents][lc-platform-hosted]). This walkthrough follows one first-party
agent on a data platform from creation to retirement. The lifecycle
profile's [example][lc-platform-example] shows the signals, risk change,
disablement, and re-enablement in between. Signatures, credentials, and
tokens are omitted or shown as placeholders.

| Party | Identifier |
|---|---|
| Enterprise IdP | `https://idp.example/`, SCIM base `https://idp.example/scim/acme` |
| Data platform | `https://dataplatform.example/` |
| Platform's workload identifier for the agent (`agt-31`) | `wimse://dataplatform.example/agents/agt-31` |
| IdP SCIM resource for the agent | `/Agents/a58` |
| Agent Principal | (`https://idp.example/`, `agent-58`) |
| Agent owner, an IdP User | `u-2819` |

### Configure the relationship

Once, before any agent exists, the IdP administrator:

* authorizes the platform's connector to register and describe Agents
  in Governance Tenant `acme`, without authority to create Identity
  Bindings or Client Associations, or to enable an Agent the IdP
  disabled;
* configures a stream from the IdP to the platform for SCIM change
  notices about the Agents that connector registered, and for CAEP
  `risk-level-change` with `principal` value `AGENT` agreed for
  registered agents; and
* configures a stream from the platform to the IdP for WISE credential
  and posture events and CAEP `session-revoked` about those Agents.

The platform needs nothing else from the IdP to run its agents. This
deployment sets no revalidation bound, so the platform keeps
authorizing on locally applied state while the IdP is unreachable.

### Register the agent

At 14:00 UTC on September 17, 2026, a customer creates a
report-building agent on the platform. The platform names it `agt-31`,
with workload identifier `wimse://dataplatform.example/agents/agt-31`,
and its connector registers the agent:

~~~ http
POST /scim/acme/Agents HTTP/1.1
Host: idp.example
Authorization: Bearer CONNECTOR_ACCESS_TOKEN
Content-Type: application/scim+json

{
  "schemas": [
    "urn:ietf:params:scim:schemas:core:2.0:Agent",
    "urn:ietf:params:scim:schemas:extension:agent-federation:2.0:Agent"
  ],
  "urn:ietf:params:scim:schemas:extension:agent-federation:2.0:Agent": {},
  "externalId": "wimse://dataplatform.example/agents/agt-31",
  "agentUserName": "report-builder",
  "displayName": "Quarterly report builder",
  "description": "Builds finance reports from platform tables",
  "owners": [{"value": "u-2819"}],
  "active": true
}
~~~

IdP policy approves registrations from this connector automatically,
so the Agent is created active. The response carries SCIM `id` `a58`
and `AgentFederation.subject` `agent-58`. The platform stores the
correlation from `agt-31` to (`https://idp.example/`, `agent-58`). The
Agent has no Identity Binding or Client Association, so the IdP issues
it no grant.

Under an approval policy, the IdP would instead create the Agent with
`active: false`, and the platform would deny the agent authorization
until the IdP activated it.

### Operate on the platform

The agent reads finance tables and writes reports through the
platform's own authorization; no request reaches the IdP. The
platform's audit record for one read carries both identifiers, for
example:

~~~ json
{
  "time": "2026-09-17T14:05:00Z",
  "action": "table.read",
  "resource": "finance.q3_ledger",
  "agent": {
    "platform_id": "wimse://dataplatform.example/agents/agt-31",
    "principal": {"iss": "https://idp.example/", "sub": "agent-58"}
  }
}
~~~

This shape is illustrative; the lifecycle profile defines no log
format. The IdP, a SIEM, or a posture tool joins this record with the
Agent's SCIM resource and the platform's events on the qualified
identifier.

### Signals, risk, and disablement

From 14:20 to 15:00, the platform reports a credential rotation and
anomalous behavior, the IdP raises the agent's risk, and an
administrator disables and then re-enables the agent. The lifecycle
profile's [example][lc-platform-example] shows each step.

### Reach a third-party resource

Later, the agent needs a third-party API on behalf of Alice, a finance
analyst who is not its owner. An administrator authorized for bindings
adds an Identity Binding to `/Agents/a58` with credential class
`platform-jwt`, source authority `https://dataplatform.example/`, and
source subject `wimse://dataplatform.example/agents/agt-31`. The
administrator also adds a Client Association permitting the platform's
OAuth client to use that binding ([AGENT-MANAGEMENT]). Separately, the
IdP records Alice's delegation authorization for the agent at that
resource and scope. The Agent's `owners` do not establish that
delegation.

For access on Alice's behalf, the platform authenticates its OAuth
client and presents Alice's ID Token as `subject_token` and its JWT for
`agt-31` as `actor_token`. After validating delegation authorization for
the requested resource and scope, the IdP issues an ID-JAG identifying
Alice in `sub` and (`https://idp.example/`, `agent-58`) in `act` under
the [core profile][core]. The third-party RAS correlates that pair as in
the lifecycle profile's [delegated walkthrough][lc-example].

For the agent's own access, with no user, the IdP would instead need
Agent Authorization and a Client Association for self-acting issuance,
and would issue a WAG with `agent-58` as `sub`.

Either way, the principal identifier, owner, and audit history
registered at 14:00 carry over unchanged.

### Retire the agent

At 16:00, the customer deletes the agent. The connector deletes
`/Agents/a58` at the IdP. The binding and association become unusable,
and `agent-58` is never assigned to another agent. A third-party
resource domain provisioned for `agent-58` applies the deletion under
[Applying Administrative State][lc-application].

## Sub-agents and orchestrators

The core decides a sub-agent's identity by what needs to be governed
separately ([Governance Boundary and Execution
Independence][governance-boundary]). Differences in process, session,
or worker alone do not call for a new identity; a need for separate
authorization, delegation, attribution, resource correlation, or
disablement does.

### A sub-agent within its parent's authority

The sub-agent runs as the parent's Agent Principal: an execution, like
a replica or worker. To obtain grants itself, it presents a resolution
input that an Identity Binding maps to that same principal. To use the
parent's grants and tokens, it stays within the client's reuse context:
the same agent, user, tenant, target, authority, and proof key ([Client
Token Reuse][client-token-reuse]). A DPoP-bound token also needs the
key, or request-specific proofs from its holder ([Distributed platforms
and key use](#distributed-platforms-and-key-use)). Resource domains see
the parent agent, which is accurate: the sub-agent's actions are the
parent's.

### A sub-agent that needs its own governance

The sub-agent gets its own Agent Principal, Identity Binding, and
Client Association, and its own authorizations. For delegated access,
the user's Delegation Authorization names the sub-agent; the
orchestrator's delegation does not extend to it, because a valid
credential, a shared client, or another agent's authorization never
implies one ([Delegation Authorization][delegation-authorization]).
Resource domains see the sub-agent as the actor and can authorize,
audit, and disable it separately.

A separate Agent Principal needs its own authorization. These profiles
define no automatic inheritance or cascading withdrawal between agents.
A deployment can explicitly constrain the sub-agent using the
orchestrator's current authority; otherwise, narrow or withdraw each
authorization separately.

### What to avoid

* **Passing the orchestrator's tokens to a sub-agent with its own
  principal.** A token names the orchestrator, so the resource domain
  would attribute the sub-agent's actions to the wrong agent, and the
  client reuse rules forbid it.
* **Encoding the parent in the sub-agent's identifier.** A change of
  parent or task would rename the sub-agent; record relationships in
  authorizations and in the Agent resource's metadata instead.
* **Treating the orchestrator as the sub-agent's actor.** One agent
  acting for another is multi-agent delegation, which these profiles do
  not define. A gateway that forwards an agent's request is different:
  it is the onward grant's client, not an actor
  ([Continuation through gateways](#continuation-through-gateways)).

## Credential brokers

The Credential Broker for Agents ([CB4A]) draft describes a broker that
keeps long-lived credentials away from agents. The agent submits each
request as a signed Task Request Envelope, and a policy decision point
approves it. A separate credential delivery point then mints a
short-lived, DPoP-bound token from a vaulted credential, proxies the
call with the real credential, or hands out a credential and revokes it
later. CB4A is an individual, Informational -00 draft, now expired.

For a target that accepts governed grants, a broker needs no vaulted
credential: the IdP issues a grant naming the agent, and the target's
RAS issues the access token. A gateway that would otherwise inject a
shared credential continues the agent's grant instead ([Continuation
through gateways](#continuation-through-gateways)). This chapter covers
the identity a broker must present, two deployment patterns, and the
limits. The [coordination notes](COORDINATION.md) compare CB4A element
by element.

### Stable identity

CB4A gives each agent session a SPIFFE ID of the form
`spiffe://trust-domain/agent/{user-id}/{session-id}` (Section 4.1 of
CB4A). That identifier combines what these profiles keep apart:

* **The agent** is a stable, issuer-qualified Agent Principal. An
  Identity Binding names an exact identity, without pattern matching,
  and an identifier of one execution, such as a session, cannot select
  or change the Agent Principal ([Identity Binding][identity-binding]).
* **The user** is the subject of a delegated ID-JAG, taken from the
  user's own sign-in.
* **A session** is a lifecycle anchor of a continuation chain, or the
  agent session of a self-acting chain.

A broker that federates therefore presents a stable per-agent identity,
such as `spiffe://trust-domain/agent/{agent-id}`. The per-session SVID
can still authenticate the agent to the broker.

### Pattern 1: the agent authenticates itself

The agent authenticates to the IdP with a JWT-SVID carrying its stable
per-agent SPIFFE ID ([JWT-SVID input][inputs-jwt-svid]), as a dedicated
client or behind a shared client. The broker no longer mints credentials
for targets that accept governed grants: its policy decision point and
approval service act as the IdP's issuance policy rather than as a
credential gate.

For the grant and the access token to be bound to the agent's own key,
as CB4A's sender-constrained tokens (Section 4.5 of CB4A) intend, the
deployment needs all of:

* client and resource configuration at the RAS that selects DPoP access
  tokens, not mutual TLS or bearer ([Access-Token
  Protection][access-token-protection]);
* DPoP proofs from the same agent-held key at issuance and redemption,
  under bound governed agent access ([Grant
  Protection][grant-protection]); and
* an API that enforces DPoP.

### Pattern 2: the broker as a governed shared client

The broker authenticates to the IdP as its own OAuth client and
presents, as workload evidence, a JWT it issues for the agent with the
stable agent identifier as `sub` ([Existing Platform
JWT][imported-jwt-input]). It cannot relay the agent's SVID instead:
inputs that resolve from authentication context are not accepted as
presented evidence ([Agent Resolution Input
Validation][actor-inputs]). A Client Association permits the broker's
client to use each agent's binding. For delegated access, the broker
also needs the user's ID Token, issued to the broker's client, as the
subject token.

The agent keeps the DPoP key and gives the broker a request-specific
proof for each token request, which the broker sends; the broker never
holds the key ([Distributed platforms and
key use](#distributed-platforms-and-key-use)). Where a token endpoint
requires a DPoP nonce, the broker relays the challenge to the agent for
a new proof. The prerequisites of Pattern 1 apply: configuration that
selects DPoP access tokens, the same agent-held key at both token
endpoints, and DPoP enforcement at the API. If configuration selects
mutual TLS instead, the RAS binds the access token to the broker's
certificate even when the grant's DPoP proof is presented, and the
agent cannot use the token directly.

### Limits

* **Targets that do not accept governed grants.** The broker remains the
  credential holder, as in CB4A's proxy, minting, and wrapping models.
  Where it uses a shared credential that carries no agent identity the
  target recognizes, the target cannot attribute or revoke per agent.
  Dedicated per-agent credentials can preserve those properties, but the
  target still does not see this family's interoperable governed
  identity. Govern and audit the broker's decision by the
  issuer-qualified Agent Principal rather than by the session
  identifier.
* **Approval.** CB4A's human and MFA approval tiers can be an additional
  condition on issuance at the IdP, under the [oversight
  profile][OVERSIGHT] ([What oversight does not
  provide](#what-oversight-does-not-provide)).
* **Revocation.** CB4A revokes individual leases on anomaly signals.
  These profiles provide different scopes:
  * For ID-JAG-derived access, the lifecycle profile's optional
    [grant-derived revocation][lc-grant-revocation] revokes what one
    grant authorized, where both parties support it.
  * For the agent as a whole, applied disablement or a Local Suspension
    in the resource domain stops it there.
  * For an individual WAG-derived access token, revocation or expiry is
    deployment-specific. These profiles define no selective WAG
    revocation.

## Adoption tradeoffs

The profile's security controls carry these deployment costs. The
threats behind them are in the core profile's [Security
Considerations][security].

| Requirement | Benefit | Cost |
|---|---|---|
| Dedicated-client resolution as the common mode | Reuses deployed client authentication and registered keys | One Agent Principal per client identity; proves registered-client identity, not independent runtime or workload provenance |
| Optional native JWT-SVID input ([INPUTS]) | Reuses SPIFFE issuance, client authentication, and trust-domain validation | Bearer evidence; issuer-bound presenter proof needs another supported input |
| Bound profile: DPoP at both token endpoints; grant bound to the grant proof key | A stolen ID-JAG cannot be redeemed without the key | Every client holds and proves a key |
| Bound grants: same key for issuance and redemption | No key-transition protocol to secure | A broker that obtains bound grants also redeems them ([Distributed platforms and key use](#distributed-platforms-and-key-use)) |
| Access-token context as JWT claims or introspection ([Optional Opaque Access Tokens and Introspection][introspection]) | The API reads `act`, `scope`, and `cnf` from the token or authenticated introspection | Opaque tokens add an introspection round trip and a freshness policy |
| Actor-aware API processing | The actor gate is enforced where access happens | APIs parse `act` and consult the gate on delegated paths |
| Sender-constrained access tokens by default | Token theft is contained | Resources without DPoP or mutual TLS need explicit configuration for bearer use |

[core]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html
[INPUTS]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-inputs.html
[AGENT-LIFECYCLE]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html
[AGENT-MANAGEMENT]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-agent-federation.html
[ID-JAG]: https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-assertion-authz-grant/
[CIMD]: https://datatracker.ietf.org/doc/draft-ietf-oauth-client-id-metadata-document/
[SCIM-AGENT]: https://datatracker.ietf.org/doc/draft-wzdk-scim-agent-resource/
[RFC7643]: https://www.rfc-editor.org/rfc/rfc7643
[RFC7644]: https://www.rfc-editor.org/rfc/rfc7644
[overview]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#overview
[model]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#model
[common-rules]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#common-rules
[grant-protection]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#grant-protection
[discovery]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#discovery
[issuance]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#issuance
[flow-configuration]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#flow-configuration
[issuance-request]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#issuance-request
[evidence]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#evidence
[actor-inputs]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#actor-inputs
[redemption]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#redemption
[redemption-request]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#redemption-request
[agent-correlation]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#agent-correlation
[jit-correlation]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#jit-correlation
[redemption-validation]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#redemption-validation
[access-token-protection]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#access-token-protection
[introspection]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#introspection
[api-processing]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#api-processing
[scope]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#scope
[metadata]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#metadata
[capability-discovery]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#capability-discovery
[client-metadata]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#client-metadata
[idp-subject-resolution]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#idp-subject-resolution
[ras-refresh]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#ras-refresh
[security]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#security
[status-changes]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#status-changes
[walkthrough]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#walkthrough
[aws-example]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#aws-example
[excluded-compositions]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#excluded-compositions
[CONTINUATION]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html
[OVERSIGHT]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html
[ov-modes]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#modes
[ov-deferred]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#deferred-issuance
[ov-deferring]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#deferring
[ov-resolution]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#resolution
[ov-continuation]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#deferred-continuation
[ov-supervised]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#supervised
[ov-per-action]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#per-action
[ov-mcp]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#mcp
[ov-fatigue]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#security-fatigue
[ov-open-items]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#open-items
[ov-redemption]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#deferred-redemption
[ov-recovery]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#redemption-recovery
[ov-redemption-opt-in]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#redemption-opt-in
[ov-redemption-resolution]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#redemption-resolution
[ov-opt-in]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#opt-in
[ov-redemption-deferring]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#redemption-deferring
[ov-redemption-refresh]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#redemption-refresh
[DTR]: https://www.ietf.org/archive/id/draft-ietf-oauth-deferred-token-response-00.html
[CIBA]: https://openid.net/specs/openid-client-initiated-backchannel-authentication-core-1_0.html
[ICA]: https://www.ietf.org/archive/id/draft-mcguinness-oauth-id-continuation-assertion-02.html
[cont-scope]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#scope-boundaries
[cont-gateway]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#gateway-reuse
[cont-errors]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#continuation-errors
[cont-window]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#governed-chain-authorization
[cont-restrictions]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#restrictions
[cont-implementation]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#implementation
[cont-two-gateways]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-two-gateways
[policy-services]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#policy-services
[errors]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#errors
[issuance-errors]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#issuance-errors
[redemption-errors]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#redemption-errors
[resource-errors]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#resource-errors
[implementation-client]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#implementation-client
[actor-authorization]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#actor-authorization
[api-applicability]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#api-applicability
[external-approval]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#external-approval
[identity-binding]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#identity-binding
[imported-jwt-input]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#imported-jwt-input
[inputs-jwt-svid]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-inputs.html#jwt-svid-input
[lc-grant-revocation]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#grant-revocation
[CB4A]: https://www.ietf.org/archive/id/draft-hartman-credential-broker-4-agents-00.html
[governance-boundary]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#governance-boundary
[client-token-reuse]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#client-token-reuse
[delegation-authorization]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#delegation-authorization
[TXN-TOKENS]: https://www.ietf.org/archive/id/draft-ietf-oauth-transaction-tokens-11.html
[cont-scheduled]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-scheduled
[cont-chain-ending]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#chain-ending
[lc-scim-events]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#scim-events
[lc-platform-signals]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#platform-signals
[issuance-authorization]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#issuance-authorization
[AUTHZEN]: https://openid.net/specs/authorization-api-1_0.html
[COAZ-MCP]: https://openid.github.io/authzen/authzen-coaz-mcp-binding-1_0.html
[ARAP]: https://openid.github.io/authzen/authzen-access-request-approval-profile-1_0.html
[AROP]: https://github.com/openid/authzen/blob/main/profiles/authzen-access-request-oauth/authzen-access-request-oauth-profile-1_0.md
[AUTHZEN-ACTOR]: https://openid.github.io/authzen/authzen-access-request-actor-profile-1_0.html
[AUTHZEN-ISSUANCE]: https://openid.github.io/authzen/authzen-oauth-token-issuance-1_0.html
[ACTOR-PROFILE]: https://datatracker.ietf.org/doc/draft-mcguinness-oauth-actor-profile/
[MISSION-AUTHZEN]: https://github.com/mcguinness/mission-bound-authorization/blob/main/draft-mcguinness-mission-authzen.md
[lc-platform-hosted]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#platform-hosted
[lc-platform-example]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#platform-example
[lc-example]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#example
[lc-application]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#application
