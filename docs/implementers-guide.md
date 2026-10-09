# Implementer's Guide for Governed Agent Federation

This guide is non-normative. It accompanies [OAuth 2.0 Profile for
Governed Agent Federation][core] (the core profile) and [Agent Resolution
Input Profiles for Governed Agent Federation][INPUTS]. Those documents
define every requirement, and they govern wherever this guide differs
from them. Nothing here is needed to implement them; the guide explains
the flows, collects the configuration a deployment needs, and records
deployment tradeoffs. Section names link to the editor's copy of the
core profile.

* [Primer: two grants, one identity model](#primer-two-grants-one-identity-model)
* [What each role builds](#what-each-role-builds)
* [Federation configuration](#federation-configuration)
* [Distributed platforms and key use](#distributed-platforms-and-key-use)
* [Adoption tradeoffs](#adoption-tradeoffs)
* [Intermediate adoption](#intermediate-adoption)
* [Provisioning and linking](#provisioning-and-linking)

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
the mandatory path for each grant.

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

Discovery exposes capabilities, not these authorization decisions
([Authorization Server and Client Metadata][metadata]). Bindings,
associations, delegation, and local links have no discovery mechanism
in the core profile.

Creating and changing bindings and associations, including imports from
platform registries, is an administrative act outside the core profile
([Provisioning and linking](#provisioning-and-linking)).
[AGENT-MANAGEMENT] defines a proposed platform-to-IdP management
interface for it.

[AWS Workload Identity Binding][aws-example] applies the model to an AWS
Security Token Service (STS) workload credential, and [INPUTS]
illustrates a shared client with SPIFFE.

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

## Provisioning and linking

Provisioning, account linking, and lifecycle propagation are deployment
choices. Useful controls include:

* authenticated link changes, or verified control of both accounts in a
  user-linking flow;
* just-in-time accounts and correlations authorized by issuer and tenant
  ([Optional Just-in-Time Correlation][jit-correlation]);
* no silent merges or reactivation of disabled accounts;
* ownership, groups, and entitlements retained with their principal, and
  audited link and binding changes; and
* issuer and tenant context in the SCIM `externalId` attribute
  [RFC7643].

SCIM [RFC7644] and Agent resources [SCIM-AGENT] are building blocks,
not a lifecycle propagation contract. [AGENT-LIFECYCLE] profiles SCIM,
optional Shared Signals, and applied changes, including missed-event
limits. It is not required for conformance to the core profile; [Agent
Principal Correlation][agent-correlation] and [Authorization Changes and
Revocation][status-changes] state the core profile's guarantees.

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
[security]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#security
[status-changes]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#status-changes
[walkthrough]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#walkthrough
[aws-example]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#aws-example
[excluded-compositions]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#excluded-compositions
