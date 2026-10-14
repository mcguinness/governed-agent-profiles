---
title: "Identity Continuation Profile for Governed Agent Federation"
abbrev: "Governed Agent Continuation"
category: std
docname: draft-mcguinness-oauth-governed-agent-continuation-latest
submissiontype: IETF
stand_alone: yes
ipr: trust200902
area: "Security"
workgroup: "Web Authorization Protocol"
keyword:
 - OAuth
 - agent federation
 - identity continuation
 - gateway
 - token exchange
venue:
  group: "Web Authorization Protocol"
  type: "Working Group"
  mail: "oauth@ietf.org"
  arch: "https://mailarchive.ietf.org/arch/browse/oauth/"
  github: "mcguinness/governed-agent-profiles"
  latest: "https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html"
author:
 - fullname: Karl McGuinness
   organization: Independent
   email: public@karlmcguinness.com
normative:
  FEDERATION:
    title: "OAuth 2.0 Profile for Governed Agent Federation"
    author:
      - name: Karl McGuinness
    date: 2026-10-09
    seriesinfo:
      Internet-Draft: draft-mcguinness-oauth-governed-agent-federation
    target: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html
  ICA: I-D.mcguinness-oauth-id-continuation-assertion
  ID-JAG: I-D.ietf-oauth-identity-assertion-authz-grant
  RFC7523:
  RFC8707:
  RFC9449:
informative:
  AGENT-LIFECYCLE:
    title: "Governed Agent Lifecycle Profile for SCIM and OAuth"
    target: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html
    author:
      - name: Karl McGuinness
    seriesinfo:
      Internet-Draft: draft-mcguinness-oauth-governed-agent-lifecycle
  AGENT-MANAGEMENT:
    title: "SCIM Profile for Governed Agent Federation Management"
    author:
      - name: Karl McGuinness
    date: 2026-09-18
    seriesinfo:
      Internet-Draft: draft-mcguinness-scim-agent-federation
    target: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-agent-federation.html
  EMA:
    title: "Enterprise-Managed Authorization"
    target: https://github.com/modelcontextprotocol/ext-auth/blob/main/specification/stable/enterprise-managed-authorization.mdx
    author:
      - org: Model Context Protocol
  RFC6755:
  WAG: I-D.carleton-workload-authz-grant

--- abstract

The OAuth 2.0 Profile for Governed Agent Federation carries a governed
Agent Principal from an identity provider into one resource domain, as
the actor of an Identity Assertion JWT Authorization Grant (ID-JAG) or
the subject of a Workload Authorization Grant (WAG). A gateway that
receives such an agent's request and calls resources in other domains
for it holds neither the user's credential nor the agent's.

This document profiles the Identity Continuation Assertion for governed
agents, with gateways as the primary deployment. The gateway obtains an
attestation that its authorization server accepted the agent's grant
and exchanges it at the identity provider for an onward grant. The
onward grant names the same Agent Principal, and for delegated access
the same user, as the grant the gateway received; the gateway is its
client, not an additional actor. The document extends the Identity
Continuation Assertion to self-acting chains rooted in a WAG, and
defines the permission a gateway needs to continue an agent's chain and
the governance events that end it.

--- middle

# Introduction

An agent reaches a tool gateway, such as a Model Context Protocol (MCP)
gateway reached through {{EMA}}, with an access token obtained under
{{FEDERATION}}. The gateway selects a tool at request time and calls it
in another resource domain. The tool's authorization server does not
accept the gateway's incoming access token, and the gateway holds
neither the user's identity assertion nor the agent's credential.
Deployments then commonly do one of these:

* call the tool with the gateway's own identity, so that the tool sees
  one client for every agent behind the gateway: the shared-client
  problem that {{FEDERATION}} addresses;
* store users' or agents' credentials at the gateway; or
* have each agent obtain access to each tool itself, which removes
  request-time tool selection from the gateway.

{{ICA}} defines how a workload that received a request derived from an
ID-JAG continues it to another resource authorization server (RAS) that
trusts the same identity provider (IdP). A Continuation Assertion
Issuer (CAI) attests that the workload's RAS accepted the earlier grant,
and the IdP issues an onward ID-JAG. {{FEDERATION}} defines how an IdP
resolves a governed Agent Principal and carries it into one resource
domain. This document defines how the governed agent's identity
survives a gateway, for delegated and self-acting access, so that each
downstream resource recognizes, authorizes, and audits the same Agent
Principal that the gateway received.

The contract has one invariant: continuation preserves the governed
identity ({{identity-preservation}}). An onward grant names the Agent
Principal and acting relationship of the chain's root grant, and for
delegated access the same user. The continuing workload, typically a
gateway, is the onward grant's client and is not added as an actor. To
keep that invariant, this document:

* replaces ICA's onward actor construction for governed chains
  ({{relationship-to-ica}});
* adds the Continuation Association, the IdP's permission for a client
  to continue an agent's chains ({{continuation-association}});
* extends ICA to self-acting chains rooted in a WAG, with an anchor that
  needs no user ({{self-acting-root}}); and
* ends a chain when a governance relationship behind it ends
  ({{chain-ending}}).

A downstream RAS and API that implement {{FEDERATION}} accept an onward
grant with no additional processing ({{target-processing}}). The IdP,
the gateway's RAS and CAI, and the gateway implement this document.

## Protocol Overview {#overview}

The following flow shows one continuation. An agent calls a tool
gateway, and the gateway calls a tool in another resource domain for
the same agent. The gateway's RAS also performs the CAI role.

~~~
Agent        IdP       GatewayRAS/CAI     Gateway        ToolRAS
  |           |               |              |               |
  | (1) governed grant with handle H0        |               |
  |---------->|               |              |               |
  |<----------|               |              |               |
  | (2) redeem; RAS binds H0  |              |               |
  |-------------------------->|              |               |
  |<--------------------------|              |               |
  | (3) call with access token               |               |
  |----------------------------------------->|               |
  |           |               | (4) assertion for H0         |
  |           |               |<-------------|               |
  |           |               |------------->|               |
  |           | (5) onward grant: same agent, gateway as client
  |           |<-----------------------------|               |
  |           |----------------------------->|               |
  |           |               |              | (6) redeem    |
  |           |               |              |-------------->|
  |           |               |              |<--------------|
~~~
{: #overview-figure title="One governed continuation through a gateway"}

1. The agent's client obtains a governed ID-JAG or WAG for the
   gateway's RAS under {{FEDERATION}}. New: where policy permits
   continuation, the IdP establishes a governed chain and includes its
   root handle ({{chain-establishment}}).
2. The client redeems the grant at the gateway's RAS under
   {{FEDERATION}}. New: the RAS binds the handle to the authorization it
   creates ({{Section 5.2 of ICA}}).
3. The agent calls the gateway, which processes the access token as the
   API under {{FEDERATION}}, including the actor gate for delegated
   access.
4. The gateway selects a tool and exchanges the access token at the
   CAI for an Identity Continuation Assertion
   ({{Section 5.4 of ICA}}).
5. The gateway presents the assertion to the IdP with its own client
   authentication and DPoP proof. New: the IdP checks the gateway's
   Continuation Association and the agent's current authorization for
   the tool, and issues an onward grant of the chain's type that names
   the same agent, with the gateway as client ({{continuation-exchange}}).
6. The gateway redeems the onward grant at the tool's RAS, which
   processes it as any governed grant ({{target-processing}}).

{{walkthrough}} shows the messages.

## Scope {#scope-boundaries}

This document applies under these conditions:

* **One IdP:** Every RAS in a chain trusts the IdP that issued the
  root grant. Continuity across a chain of IdPs remains out of scope,
  as in {{FEDERATION}}.
* **One agent:** Continuation never changes the Agent Principal. A
  continuing workload that needs its own authorization, attribution,
  or disablement as an agent is a separate Agent Principal
  ("Governance Boundary and Execution Independence" in {{FEDERATION}}),
  and its acting for another agent is the multi-agent delegation chain
  that {{FEDERATION}} excludes.
* **An accepted grant:** The gateway's access token comes from a RAS
  that redeemed a governed grant. Where the IdP itself issues the
  gateway's access tokens, there is no hop to continue; that deployment
  needs the access-token subject composition that {{FEDERATION}}
  excludes.

Whether a call still serves approved work is outside this document, as
in {{FEDERATION}}. This document defines no new token format, claim,
error code, or request parameter.

# Conventions and Terminology {#terms}

{::boilerplate bcp14-tagged-bcp14}

Agent Principal, Identity Binding, Client Association, acting
relationship, Delegation Authorization, Agent Authorization, Governance
Tenant, Target Tenant, and grant proof key follow {{FEDERATION}}.
Continuation Assertion Issuer (CAI), Identity Continuation Assertion,
continuation handle, chain, hop, chain authorization, lifecycle anchor,
and continuation-aware RAS follow {{ICA}}. ID-JAG and WAG refer to the
grants as {{FEDERATION}} profiles them.

{{ICA}} and {{FEDERATION}} use some of the same words differently. This
document uses them as follows:

| ICA term | Meaning in ICA | Term in this document |
|---|---|---|
| Workload | A service that received a request on a user's behalf and may continue it | Continuing client; "workload" keeps its meaning in {{FEDERATION}} |
| Current actor | The workload presenting the assertion, named by its `act` | Continuing client; the assertion's `act` still names it, and the onward grant does not ({{identity-preservation}}) |
| Root actor | The authenticated client of the root exchange | Root client; the chain's governed actor is the Agent Principal |
| Actor lineage | The actors disclosed in the onward `act` | Kept only in the IdP's hop records |
{: title="ICA terms in this document"}

This document defines these terms:

Gateway:
: A resource server that receives requests from agents and calls other
  resources for them, choosing the target at request time. A gateway is
  the primary continuing client.

Continuing client:
: The OAuth client that presents an Identity Continuation Assertion to
  the IdP and redeems the resulting onward grant. It is a client as
  {{FEDERATION}} uses the term: software making OAuth requests for an
  agent.

Governed chain:
: A chain whose root is a governed ID-JAG or WAG and whose chain
  authorization this document extends
  ({{governed-chain-authorization}}). By its root grant it is a
  delegated chain or a self-acting chain.

Continuation Association:
: An approved permission for an authenticated OAuth client to continue
  an Agent Principal's governed chains in one acting relationship
  ({{continuation-association}}).

Onward grant:
: A governed ID-JAG or WAG issued on a continuation exchange.

# Continuation Model {#model}

## Identity Preservation {#identity-preservation}

The IdP MUST construct every onward grant of a governed chain so that:

* it is the chain's grant type: an ID-JAG for a delegated chain and a
  WAG for a self-acting chain;
* it names the chain's Agent Principal: in an ID-JAG as the single
  `act` object, with the IdP issuer as `iss` and the Agent Principal
  identifier as `sub`, and in a WAG as `iss` and `sub`, with no `act`;
* for a delegated chain, it names the chain's user, resolved for the
  target RAS ({{onward-id-jag}}); and
* its `client_id` identifies the continuing client's registration at the
  target RAS ("Issuance Prerequisites" in {{FEDERATION}}).

The continuing client MUST NOT appear in the onward grant's `act`. This
replaces, for governed chains, the onward actor lineage that
{{Section 5.5.5 of ICA}} constructs. The assertion's `act` still names
the continuing client ({{Section 3.2 of ICA}}), and the IdP still
matches it to the authenticated client ({{Section 5.5.2 of ICA}}). That
identity never becomes the governed actor. The IdP takes the Agent
Principal, the user, and the acting relationship from its chain record,
never from the assertion or the request.

Continuation never converts the acting relationship. The IdP MUST NOT
issue a WAG from a delegated chain or an ID-JAG from a self-acting
chain. For a chain established without this document, it MUST NOT issue
a governed onward grant, and for a governed chain it MUST NOT issue an
onward ID-JAG constructed under {{Section 5.5.5 of ICA}}.

The downstream RAS and API therefore see the same issuer-qualified Agent
Principal that the gateway received and apply the same actor gate to it.
The continuing client is accountable as the authenticated `client_id`,
and the complete path across hops remains in the IdP's hop records.
{{rationale-client}} explains the choice.

## Continuation Association {#continuation-association}

Before issuing an onward grant, the IdP MUST verify that a current
Continuation Association permits the authenticated continuing client to
continue the chain's Agent Principal in the chain's acting relationship,
for the requested target. A Continuation Association can restrict
targets and authority. It narrows, and does not replace, the
restrictions on who may continue that the chain authorization records
({{Section 5.1.4 of ICA}}).

Permissions have these limits:

* A Client Association does not imply a Continuation Association, nor
  the reverse.
* Permission to continue delegated chains does not imply permission to
  continue self-acting chains, nor the reverse.
* A Continuation Association is not an Identity Binding. On a
  continuation exchange, the IdP performs no agent resolution: the
  assertion is not an agent-resolution input, and the continuing
  client's credential MUST NOT resolve an Agent Principal for the
  onward grant, even when that client is also bound to an agent.

Policy representation and administration are outside this document.
{{AGENT-MANAGEMENT}} does not yet manage Continuation Associations.

## Governed Chain Authorization {#governed-chain-authorization}

For a governed chain, the IdP records in the chain authorization
({{Section 5.1.4 of ICA}}), in addition to the facts ICA requires:

* the acting relationship and the Agent Principal;
* for a delegated chain, the user and authentication context that ICA
  records; a self-acting chain has neither;
* the root client, and the Identity Binding and Client Association
  through which the root grant was issued;
* the Governance Tenant;
* the Delegation Authorization or Agent Authorization under which the
  root grant was issued; and
* for a self-acting chain, its absolute expiration ({{self-acting-root}}).

Each fact is either fixed at the root or evaluated at every
continuation:

| Fact | Treatment at continuation |
|---|---|
| Agent Principal, acting relationship, user, root client, and Governance Tenant | Fixed at the root; never resolved again |
| Status of the Agent Principal, the user, the root Identity Binding, and the root Client Association | Current state; a disabled one ends the chain ({{chain-ending}}) |
| Delegation or Agent Authorization for the requested target and authority | Current policy, within the chain authorization |
| Continuation Association of the continuing client | Current policy |
| Target Tenant, the user's subject at the target, and the continuing client's registration there | Resolved for each onward grant |
{: title="Fixed and current facts of a governed chain"}

Current policy can narrow the chain authorization but cannot exceed it
({{Section 5.1.4 of ICA}}).

## Relationship to the Identity Continuation Assertion {#relationship-to-ica}

Where this document is silent, {{ICA}} applies unchanged. The following
table is non-normative; the referenced sections define each
requirement.

| Area | ICA | This document |
|---|---|---|
| Root exchange | Base ID-JAG exchange; `actor_token` processing out of scope ({{Section 5.1.1 of ICA}}) | Governed issuance under {{FEDERATION}} in either resolution mode ({{delegated-root}}) |
| Root grant | ID-JAG | Governed ID-JAG or WAG |
| Anchors | User session or refresh-token grant; non-user roots out of scope ({{Section 6.1 of ICA}}) | Unchanged for delegated chains; an Agent Authorization anchor with an absolute expiration for self-acting chains ({{self-acting-root}}) |
| Chain authorization | User, root actor, authentication context, anchor, restrictions | Adds the facts of {{governed-chain-authorization}} |
| Who may continue | Chain authorization and current policy | Also a Continuation Association ({{continuation-association}}) |
| Continuation request | Zero or more `resource`; optional `scope`; ID-JAG requested ({{Section 5.5.1 of ICA}}) | Exactly one `resource`; required `scope`; the chain's grant type ({{continuation-request}}) |
| Onward `act` | Continuing actor atop IdP-derived lineage ({{Section 5.5.5 of ICA}}) | The Agent Principal alone in an ID-JAG; none in a WAG ({{identity-preservation}}) |
| Onward redemption | `jwt-dpop` grant ({{Section 5.5.5 of ICA}}) | `jwt-bearer` grant with grant confirmation ({{target-processing}}) |
| Access token for a grant with `cnf` | DPoP-bound, never bearer ({{Section 5.2 of ICA}}) | DPoP-bound or, where configured, certificate-bound; never bearer ({{root-redemption}}) |
| Continuation eligibility | RAS policy | Not recorded for a bearer access token without explicit policy ({{root-redemption}}) |
| RAS advertisement | `id-jag-continuation`, with `jwt-dpop` ({{Section 7.2 of ICA}}) | Adds `wag-continuation`; `jwt-dpop` not required ({{conformance}}) |
| Chain ending | Anchor end, revocation, withdrawn permission ({{Section 6.2 of ICA}}) | Also governance events ({{chain-ending}}) |
{: title="Changes to ICA for governed chains"}

The limits of {{Section 6.3 of ICA}}, including the actor-lineage depth
bound, apply to the IdP's hop records unchanged. Their lineage entries
are the root client and the continuing clients, although no onward
grant discloses them.

# Establishing a Governed Chain {#chain-establishment}

The root exchange is grant issuance under {{FEDERATION}}. In addition to
the conditions of {{Section 5.1.2 of ICA}}, the IdP MUST establish a
governed chain only when tenant policy permits continuation for the
Agent Principal and acting relationship, and the root resolves to a
lifecycle anchor: one of {{Section 6.1 of ICA}} for a delegated chain,
or the anchor of {{self-acting-root}}. Otherwise the IdP issues the
governed grant without a handle, as {{FEDERATION}} specifies. As in
{{ICA}}, no request parameter requests establishment, and advertised
support does not authorize it.

The root grant conforms to {{FEDERATION}}. Its only addition is the
`identity_continuation_handle` claim ({{Section 4 of ICA}}).

## Delegated Root {#delegated-root}

The root ID-JAG follows "Delegated Issuance: ID-JAG" in {{FEDERATION}}.
Its anchors are those of {{Section 6.1 of ICA}}. With the ID Token
subject that {{FEDERATION}} requires, the anchor is the user's IdP
session that the ID Token's `sid` identifies.

The root exchange MAY use either resolution mode of {{FEDERATION}},
including presented-evidence mode, whose `actor_token` carries the
agent-resolution input ("Agent Resolution Input Validation" in
{{FEDERATION}}). This document thereby defines the root `actor_token`
processing that {{Section 5.1.1 of ICA}} leaves out of scope. The
`actor_token` resolves the governed actor; it does not name an inbound
actor, which {{FEDERATION}} rejects.

## Self-Acting Root {#self-acting-root}

This section extends {{ICA}} to chains with no user. The root WAG
follows "Self-Acting Issuance: WAG" in {{FEDERATION}} and carries the
root handle, which the IdP generates under rules 1 and 2 of
{{Section 4 of ICA}}.

The lifecycle anchor of a self-acting chain is the Agent Authorization
under which the root WAG was issued. For these chains, it replaces the
user-rooted anchors of {{Section 6.1 of ICA}}; the prohibition there on
rooting a chain from an access token still applies.

No session ends a self-acting chain. The IdP MUST therefore set an
absolute expiration for each self-acting chain at establishment, no
later than its configured maximum chain lifetime, and MUST NOT extend
it. A chain past that expiration has ended ({{chain-ending}}). Access
after it requires a new root WAG, and with it a fresh agent resolution
and Agent Authorization decision.

A self-acting chain has no authentication context, so its onward WAGs
carry no `auth_time`, `acr`, or `amr`.

# Root Redemption at the Gateway's RAS {#root-redemption}

The gateway's RAS redeems the root grant under "Grant Redemption at the
RAS" in {{FEDERATION}}. When continuation-aware, it also binds the
handle as {{Section 5.2 of ICA}} specifies, for a WAG as for an ID-JAG,
and exposes the handle to the CAI through a carrier of
{{Section 5.3 of ICA}}.

A continuation-aware RAS selects access-token protection under
"Access-Token Protection" in {{FEDERATION}}, with these rules:

* **Bound grant:** For a grant carrying `cnf`, as every onward grant
  does, the RAS MUST NOT issue a bearer access token. It binds the
  token to the grant's DPoP key or, where configuration selects mutual
  TLS, to the client certificate. This relaxes step 3 of
  {{Section 5.2 of ICA}}, which permits only DPoP, so that the
  protection modes of {{FEDERATION}} remain available.
* **Bearer ingress:** The RAS MUST NOT record an authorization as
  eligible for continuation when it issued a bearer access token for
  that authorization, unless resource policy explicitly permits
  continuation from bearer access tokens for that client and resource.
  {{Section 9.1 of ICA}} describes the exposure.

The gateway is the API for its incoming access token. It applies
"Access at the Resource Server" in {{FEDERATION}}, including the actor
gate for delegated access. The CAI's attestation establishes that the
RAS accepted the hop. It does not establish that the gateway authorized
the request.

# Assertion Issuance {#assertion-issuance}

{{Section 5.4 of ICA}} applies unchanged to delegated and self-acting
chains. The CAI attests acceptance, activity, and the continuing
client's association with the authorization by the RAS's own
authorization semantics. It does not evaluate Identity Bindings,
Client Associations, Continuation Associations, or the agent's
authorization. The assertion carries no Agent Principal, user, or acting
relationship; the IdP takes them from its chain record.

# Continuation Exchange at the IdP {#continuation-exchange}

## Request {#continuation-request}

The continuing client sends the continuation request of
{{Section 5.5.1 of ICA}}, with client authentication under
{{Section 5.5.2 of ICA}} and a DPoP proof of the assertion's `cnf` key.
The common parameters and rules of "Token Exchange Request" in
{{FEDERATION}} apply to it, so these parameters are REQUIRED:

| Parameter | Value |
|---|---|
| `requested_token_type` | `urn:ietf:params:oauth:token-type:id-jag` for a delegated chain; `urn:ietf:params:oauth:token-type:wag` (provisional) for a self-acting chain |
| `audience` | One target RAS issuer identifier |
| `resource` | Exactly one resource URI under {{RFC8707}}, served by the RAS named in `audience` |
| `scope` | Non-empty scope string for the requested resource |
{: title="Continuation request parameters"}

The continuing client selects `requested_token_type` from the acting
relationship of the access token it received, which "Profile
Applicability" in {{FEDERATION}} requires the token context to convey.
`authorization_details` is processed as in {{FEDERATION}}.

## Validation {#continuation-validation}

The IdP MUST apply the request validation of {{Section 5.5.3 of ICA}},
with the requested token type of its rule 1 replaced by the table in
{{continuation-request}}. For a hop of a governed chain, the IdP MUST
also establish the following, within the chain-state and authorization
rules of that section:

1. **Chain type:** `requested_token_type` is the chain's grant type
   ({{identity-preservation}}). A WAG is never issued from a hop that
   is not in a self-acting chain.
2. **Governance state:** The Agent Principal is active; for a delegated
   chain, the user is active; the root Identity Binding and Client
   Association remain enabled; the Delegation Authorization or Agent
   Authorization recorded at the root has not been withdrawn or
   expired; and a self-acting chain is within its absolute expiration
   ({{chain-ending}}).
3. **Continuation Association:** One permits the authenticated client
   ({{continuation-association}}).
4. **Issuance authorization:** "Issuance Authorization" in
   {{FEDERATION}} permits the onward grant for the chain's Agent
   Principal and, for a delegated chain, its user, with the continuing
   client as the authenticated client. That requires a current
   Delegation Authorization for the user, agent, target, and authority,
   or a current Agent Authorization for the agent, target, and
   authority. The chain authorization also bounds the authority.
5. **Target context:** The Target Tenant for the requested resource, the
   continuing client's registration at the target RAS ("Issuance
   Prerequisites" in {{FEDERATION}}), and for a delegated chain the
   user's subject at the target ("Subject Resolution" in
   {{FEDERATION}}) each resolve unambiguously. For a self-acting chain,
   the Agent Principal identifier is not resolved per target; it is the
   chain's.

The rules of {{FEDERATION}} for agent resolution and subject tokens do
not apply to the assertion.

## Onward Grants {#onward-grants}

The response follows {{Section 5.5.4 of ICA}}, with `issued_token_type`
equal to the requested grant type and no refresh token.

Every onward grant carries the common claims of "Common Grant Claims,
Lifetime, and Response" in {{FEDERATION}}, a fresh child handle under
{{Section 4 of ICA}}, and `cnf.jkt` for the key proven in the request
({{Section 5.5.2 of ICA}}). The assertion authenticates one
continuation exchange and does not bound the onward grant's lifetime.
An onward WAG MUST NOT outlive its chain's absolute expiration.

### Delegated: ID-JAG {#onward-id-jag}

The onward ID-JAG follows "Grant Issuance" in {{FEDERATION}} and
{{Section 5.5.5 of ICA}}, except for the actor:

| Claim | Value |
|---|---|
| `sub` | The chain's user, in the IdP's subject namespace for the target RAS |
| `act` | The object of "Actor Resolution and Construction" in {{FEDERATION}}, with the chain's Agent Principal as `sub` and the IdP issuer as `iss`; any `sub_profile` reflects the IdP's current classification |
| `client_id` | The continuing client's registration at the target RAS |
| `auth_time`, `acr`, `amr` | Copied unchanged from the root, as {{Section 5.5.5 of ICA}} requires |
{: title="Onward ID-JAG subject, actor, and client claims"}

### Self-Acting: WAG {#onward-wag}

The onward WAG follows "Self-Acting Issuance: WAG" in {{FEDERATION}},
including its JWT type and its prohibition of `act`:

| Claim | Value |
|---|---|
| `iss` | The IdP issuer identifier |
| `sub` | The chain's Agent Principal identifier |
| `aud` | The target RAS issuer identifier |
| `client_id` | The continuing client's registration at the target RAS |
{: title="Onward WAG issuer, subject, audience, and client claims"}

## Errors {#continuation-errors}

The error codes and precedence of {{Section 5.5.6 of ICA}} apply. The
governed checks of {{continuation-validation}} use these errors:

| Failure | Error |
|---|---|
| `requested_token_type` is not the chain's grant type | `invalid_request` |
| A governance state failure ({{chain-ending}}) | `invalid_continuation`; the chain has ended |
| No Continuation Association permits the continuing client | `unauthorized_client` |
| Delegated chain: the agent is not authorized to act for the user at the requested target or authority | `actor_unauthorized` ("Issuance Errors" in {{FEDERATION}}) |
| Self-acting chain: the agent is not authorized for the requested target, or for the requested authority | `invalid_target`, or `invalid_scope` |
| Target Tenant, user subject, or continuing-client registration cannot be resolved at the target | `invalid_target` |
| Missing, multiple, or unacceptable `resource` or `scope` | As in "Token Endpoint Errors" in {{FEDERATION}} |
{: title="Errors for governed continuation"}

The chain-type check is part of the chain-state rule, so its error is
not returned before issuer trust for the hop's RAS is established
({{Section 5.5.6 of ICA}}). A failure other than `invalid_continuation`
affects only the current request, and the chain stays continuable.

# Onward Redemption and Access {#target-processing}

The continuing client redeems the onward grant under "Redemption
Request" in {{FEDERATION}}: the `urn:ietf:params:oauth:grant-type:jwt-bearer`
grant type, client authentication as the client the grant names, and a
DPoP proof of the grant's `cnf` key. For governed chains, this replaces
the `jwt-dpop` redemption of {{Section 5.5.5 of ICA}}.
{{Section 4.4 of ID-JAG}} requires `jwt-bearer`, and {{FEDERATION}}
applies the grant confirmation checks of ID-JAG to it.

The target RAS processes the onward grant as any governed grant, under
"Delegated Redemption: ID-JAG" or "Self-Acting Redemption: WAG" in
{{FEDERATION}}. It correlates the same Agent Principal, applies the
actor gate to that agent for delegated access, and authenticates the
continuing client as `client_id`. A RAS that does not implement {{ICA}}
ignores the handle ({{Section 5.2 of ICA}}). A RAS that continues the
chain further is a continuation-aware RAS under {{root-redemption}}.

The continuing client is a client of the target RAS like any other.
Resource policy can permit or deny an agent's access through a
particular client registration, for example to admit agents only
through an approved gateway. As {{FEDERATION}} requires for any client,
the client identifier does not stand in for the actor.

The API applies "Access at the Resource Server" in {{FEDERATION}}
unchanged. A delegated access token at the target names the user and
the Agent Principal exactly as it would for the agent's own client; its
`client_id` names the continuing client.

# Gateway Deployment {#gateway-deployment}

## Roles {#gateway-roles}

A gateway combines roles, as {{FEDERATION}} permits. Inbound, it is the
API for the agent's access token, and its operator's RAS is the
continuation-aware RAS and CAI. Outbound, it is the continuing client at
the CAI, the IdP, and each target RAS.

A gateway deployment adds this configuration to that of {{FEDERATION}}:

| Party | Configuration |
|---|---|
| IdP | Tenant policy permitting continuation; Continuation Associations for the gateway; the gateway's client registration and canonical actor identity ({{Section 5.5.2 of ICA}}); trust in the gateway's CAI ({{Section 7.3 of ICA}}); the gateway's registration at each target RAS |
| Gateway's RAS | Continuation-aware processing and advertisement; assertion issuance; the gateway's registration as the client that operates the gateway resource |
| Gateway | A client credential for each server and a DPoP key |
| Target RAS | A client registration for the gateway; otherwise {{FEDERATION}} |
{: title="Configuration added by a gateway deployment"}

## Topologies {#gateway-topologies}

| Topology | CAI | Use |
|---|---|---|
| Gateway authorization server | The gateway's own RAS ({{Section 8.1 of ICA}}) | The gateway operator runs an authorization server for the gateway resource; the baseline |
| Shared authorization server | A separate CAI trusted for that RAS ({{Section 5.4.6 of ICA}}) | The gateway is a resource server behind an API-management or enterprise authorization server |
| Gateway behind a gateway | Each gateway's RAS | Each hop is a governed continuation, and every onward grant names the same agent |
| IdP-issued gateway tokens | None | Not applicable ({{scope-boundaries}}) |
{: title="Gateway topologies"}

## Context Isolation {#gateway-reuse}

One gateway client registration serves many agents, users, and tenants.
"Client Token Reuse" in {{FEDERATION}} applies to every onward grant and
downstream access token the gateway holds: it reuses one only for a
request in the same agent, user, tenant, target, authority, and proof
context. A gateway SHOULD also keep downstream tokens separate for each
source hop, so that continuation and revocation follow the chain on
which each request arrived ({{Section 8 of ICA}}).

Each continuation derives from the authorization context of the request
being served ({{Section 5.3 of ICA}}). The gateway cannot select another
agent's chain, because the CAI uses the handle bound to the presented
token.

A continuing client MUST NOT serve an agent's request with its own
authority, or through a chain established without this document, after
a governed continuation for that request is denied. As in "Profile
Applicability and Downgrade Prevention" in {{FEDERATION}}, a lower path
requires separately authorized configuration, not an error-driven
fallback.

Gateway-side tool filtering narrows what the gateway attempts. It does
not authorize: the IdP decides whether the agent may reach a target,
and the target decides what it permits.

# Chain Ending and Governance Events {#chain-ending}

In addition to the conditions of {{Section 6.2 of ICA}}, a governed
chain ends when the IdP has applied any of the following:

* disablement of the Agent Principal;
* for a delegated chain, disablement of the user;
* disablement of the root Identity Binding or removal of the root
  Client Association;
* withdrawal or expiration of the Delegation Authorization or Agent
  Authorization recorded at the root; or
* for a self-acting chain, its absolute expiration.

Each is a withdrawal of the chain's permission to continue under
{{Section 6.2 of ICA}}. Continuation fails with `invalid_continuation`,
and the chain stays ended if the relationship is restored. The IdP
applies these changes within the freshness limit of "Issuance
Authorization" in {{FEDERATION}}.

Disabling the root Identity Binding ends the chain even when the agent
has other enabled bindings. A continuation performs no agent
resolution, so the chain has no resolution other than its root's.

Ending a chain stops new continuations only. Onward grants and access
tokens already issued follow "Authorization Changes and Revocation" in
{{FEDERATION}}, and propagating revocation to them can use the
grant-derived revocation of {{AGENT-LIFECYCLE}}.

| Administrative action | Effect on governed chains |
|---|---|
| Disable the Agent Principal | Every chain for the agent ends |
| Disable the root Identity Binding or remove the root Client Association | Chains rooted through it end; chains rooted through other bindings continue |
| Withdraw a Delegation Authorization or Agent Authorization | Chains rooted under it end |
| Remove a Continuation Association | That client can no longer continue the agent's chains; other permitted clients can |
| Remove a target or authority from current policy | Continuation to it fails; the chain remains continuable to other targets |
| End the user's IdP session | Delegated chains anchored to it end ({{Section 6.2 of ICA}}) |
| Disable the local agent or user at a target RAS | No new access at that RAS ({{FEDERATION}}); the chain is unaffected elsewhere |
{: title="Effects of administrative changes on governed chains"}

# Conformance and Capability Advertisement {#conformance}

## Conformance Claims {#conformance-claims}

The roles are the IdP, the continuation-aware RAS and its CAI, the
continuing client, and the target RAS. An implementation claims
delegated continuation, self-acting continuation, or both, for each
role it implements. Each claim requires the same realization under
{{FEDERATION}} and the applicable requirements of {{ICA}} as this
document changes them. A target RAS that does not continue the chain
needs only {{FEDERATION}}.

Each claim has this mandatory interoperability path:

* **Client authentication:** The continuing client, CAI, IdP, and
  target RAS MUST implement {{RFC7523}} `private_key_jwt` client
  authentication, under "Dedicated Client Identity" in {{FEDERATION}}
  for its audience, replay, and retry rules.
* **Proof:** They MUST implement DPoP {{RFC9449}} with the algorithms
  of "Client Authentication and Algorithms" in {{FEDERATION}}.
* **Assertion issuance:** A continuation-aware RAS that performs the CAI
  role MUST support assertion issuance at its token endpoint with an
  access-token `subject_token` ({{Section 5.4.1 of ICA}}), and the
  continuing client MUST implement that request.

## Metadata {#metadata}

A continuation-aware RAS lists, in `authorization_grant_profiles_supported`
({{Section 7.2 of ID-JAG}}), together with its governed profile URIs:

* `urn:ietf:params:oauth:grant-profile:id-jag-continuation`
  ({{Section 7.2 of ICA}}) when it binds handles of governed ID-JAGs;
  and
* `urn:ietf:params:oauth:grant-profile:wag-continuation` when it binds
  handles of governed WAGs. As for the self-acting profile URIs of
  {{FEDERATION}}, use of this parameter for WAG awaits coordination
  ({{dependencies}}).

The requirement of {{Section 7.2 of ICA}} to advertise the `jwt-dpop`
grant type does not apply.

The IdP advertises `identity_continuation_supported`
({{Section 7.1 of ICA}}). Support for self-acting continuation is
established through trusted configuration ("Capability Discovery" in
{{FEDERATION}}); no IdP metadata advertises it. Advertisement indicates
capability and does not authorize continuation.

# Security Considerations {#security}

The security considerations of {{ICA}} and {{FEDERATION}} apply.

## Gateway Compromise {#security-gateway}

A gateway concentrates access. A compromised gateway that can still
authenticate and prove its key can continue each chain whose requests
reach it, to any target that the chain authorization, the agent's
current authorization, and its Continuation Associations permit, while
the authorizations behind those requests remain active. It can also use
the downstream tokens it already holds until they expire.

It cannot:

* continue a chain whose request did not reach it, because the CAI
  attests only hops bound to tokens presented to it
  ({{Section 5.4.3 of ICA}});
* change the agent or the user, or convert the acting relationship
  ({{identity-preservation}}); or
* obtain authority beyond the agent's own authorization.

Narrow Continuation Associations, chain authorizations that restrict
targets, sender-constrained ingress ({{root-redemption}}), and short
downstream token lifetimes reduce this exposure.

## Attribution Through an Intermediary {#security-attribution}

Downstream records attribute an action to the Agent Principal and, for
delegated access, the user; the continuing client appears as
`client_id`. The gateway selects the target, but the agent's
authorization governs whether the gateway can reach it. The onward
grant does not disclose earlier continuing clients, so audit across
hops correlates each target's records with the IdP's hop records. A
handle does not distinguish a root grant from an onward grant: a
resource that must tell a gateway from the agent's own client uses the
authenticated `client_id`.

## Bearer Ingress {#security-bearer}

A bearer access token at the gateway lets a party that steals it call
the gateway and induce an honest continuation ({{Section 9.1 of ICA}}).
The bearer-ingress rule of {{root-redemption}} keeps such an
authorization ineligible for continuation unless policy explicitly
accepts that exposure.

## Self-Acting Chains {#security-self-acting}

No user session bounds a self-acting chain. Its absolute expiration,
the governance events of {{chain-ending}}, and the limits of
{{Section 6.3 of ICA}} are its bounds. A configured maximum chain
lifetime close to the expected duration of the agent's work limits how
long a compromised gateway can continue it.

## Disablement Windows {#security-disablement}

Ending a chain stops new continuations. Issued onward grants and
downstream access tokens remain usable until they expire or their
revocation is applied ("Authorization Changes and Revocation" in
{{FEDERATION}}). In a gateway deployment, that window includes every
downstream access token the gateway has cached.

# Privacy Considerations {#privacy}

The privacy considerations of {{ICA}} and {{FEDERATION}} apply.
Continuation discloses the Agent Principal identifier to each target the
gateway reaches, which extends the cross-resource correlation that a
stable agent identifier allows. The gateway learns which agents and
users call which tools. An onward grant discloses only the current
continuing client, not earlier ones, so a target learns less of the
path than under {{Section 5.5.5 of ICA}}. The IdP's hop records hold the
complete path and are sensitive audit data.

# IANA Considerations {#iana}

This document requests registration of the following value in the
"OAuth URI" registry established by {{RFC6755}}:

* URN: `urn:ietf:params:oauth:grant-profile:wag-continuation`
* Common Name: Grant profile identifier for a governed WAG whose
  accepting Resource Authorization Server binds the
  `identity_continuation_handle` claim to authorization state
* Change Controller: IETF
* Specification Document: {{metadata}} of this document.

The `identity_continuation_handle` JWT claim and the
`urn:ietf:params:oauth:grant-profile:id-jag-continuation` value are
registered by {{ICA}}. This document uses the claim in WAGs and
registers nothing further.

--- back

# Gateway Walkthrough {#walkthrough}

This non-normative walkthrough adds a gateway to the dedicated-client
walkthrough of {{FEDERATION}} and reuses its identities: the dedicated
client `analysis-client`, the Agent Principal `agent-42`, the user
Alice, and the resource `https://api.example/tenants/acme-data/` at
`https://ras.example/`, where Alice is `alice-ras` to the IdP and
`user-108` locally. Key coordinates, thumbprints, and compact JWTs are
labeled placeholders. JWTs are shown as decoded payloads, and HTTP
bodies are line-wrapped for display.

The gateway is an MCP gateway at `https://gateway.example/mcp`, whose
operator runs `https://ras.gateway.example/` as its RAS and CAI.

* **IdP:** `analysis-client` is registered as before. The gateway is
  the client `tool-gateway`, authenticating with `private_key_jwt`; its
  registration records the canonical actor identity
  (`https://gateway.example/`, `tool-gateway`). Tenant policy permits
  continuation for `agent-42`. A Continuation Association permits
  `tool-gateway` to continue `agent-42`'s delegated and self-acting
  chains to resources in `acme-data`. The IdP trusts
  `https://ras.gateway.example/` as CAI for its own hops, and associates
  `tool-gateway` with the registration `gateway-files` at
  `https://ras.example/`.
* **GatewayRAS:** The agent's client is registered as `analysis-gw` and
  the gateway as `tool-gateway`, the client that operates
  `https://gateway.example/mcp`. Alice is `alice-gw` to the IdP and
  `gw-user-7` locally. GatewayRAS advertises both continuation
  profiles.
* **Keys:** K is the agent client's grant proof key, as in
  {{FEDERATION}}; G is the gateway's DPoP key.

## Root Grant and Gateway Access Token {#walkthrough-root}

The agent's client exchanges Alice's ID Token at the IdP as in the
walkthrough of {{FEDERATION}}, with `audience` set to
`https://ras.gateway.example/`, `resource` to
`https://gateway.example/mcp`, and `scope` to `tools.invoke`. Alice's
ID Token carries a `sid` that resolves to her IdP session, which
anchors the chain. The decoded root ID-JAG:

~~~ json
{
  "iss": "https://idp.example/",
  "sub": "alice-gw",
  "aud": "https://ras.gateway.example/",
  "iat": 1789646463,
  "exp": 1789646763,
  "jti": "gw-grant-1",
  "client_id": "analysis-gw",
  "resource": "https://gateway.example/mcp",
  "scope": "tools.invoke",
  "auth_time": 1789646400,
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "cnf": {"jkt": "JKT_K"},
  "identity_continuation_handle": "Qm7zXu2VtL9pKe4RaW1nHc"
}
~~~

The client redeems it at GatewayRAS with a proof of K. GatewayRAS binds
the handle, H0, to the authorization it creates and issues a DPoP-bound
access token that carries the handle:

~~~ json
{
  "iss": "https://ras.gateway.example/",
  "sub": "gw-user-7",
  "aud": "https://gateway.example/mcp",
  "iat": 1789646464,
  "exp": 1789647064,
  "jti": "gw-access-1",
  "client_id": "analysis-gw",
  "scope": "tools.invoke",
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "cnf": {"jkt": "JKT_K"},
  "identity_continuation_handle": "Qm7zXu2VtL9pKe4RaW1nHc"
}
~~~

The agent calls a tool through the gateway with this token and a proof
of K. The gateway validates both, enforces the actor gate for
`agent-42` acting for Alice, and routes the call to the file service in
`acme-data`.

## Assertion {#walkthrough-assertion}

`GW_CAI_PROOF` proves G. `GW_ASSERTION_1` is a `private_key_jwt`
assertion with `iss` and `sub` `tool-gateway` and `aud`
`https://ras.gateway.example/`:

~~~ http-message
POST /token HTTP/1.1
Host: ras.gateway.example
Content-Type: application/x-www-form-urlencoded
DPoP: GW_CAI_PROOF

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Atoken-exchange
&requested_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type
%3Aidentity-continuation
&subject_token=GW_ACCESS_TOKEN
&subject_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type
%3Aaccess_token
&client_id=tool-gateway
&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth
%3Aclient-assertion-type%3Ajwt-bearer
&client_assertion=GW_ASSERTION_1
~~~

GatewayRAS confirms that the token is its own, unexpired, and issued
for the resource `tool-gateway` operates, reads H0, and rechecks that
the authorization is active and eligible. Its response names
`https://idp.example/` in `identity_continuation_authorization_server`.
The decoded assertion:

~~~ json
{
  "iss": "https://ras.gateway.example/",
  "aud": "https://idp.example/",
  "identity_continuation_handle": "Qm7zXu2VtL9pKe4RaW1nHc",
  "act": {"iss": "https://gateway.example/", "sub": "tool-gateway"},
  "cnf": {"jkt": "JKT_G"},
  "iat": 1789646470,
  "exp": 1789646590,
  "jti": "n3Vt7Jq2Xd5PbR9wLc1eKs"
}
~~~

## Continuation {#walkthrough-continuation}

`IDP_GW_PROOF` proves G, and `GW_ASSERTION_2` is a fresh
`private_key_jwt` assertion addressed to `https://idp.example/`:

~~~ http-message
POST /token HTTP/1.1
Host: idp.example
Content-Type: application/x-www-form-urlencoded
DPoP: IDP_GW_PROOF

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Atoken-exchange
&requested_token_type=urn%3Aietf%3Aparams%3Aoauth
%3Atoken-type%3Aid-jag
&client_id=tool-gateway
&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth
%3Aclient-assertion-type%3Ajwt-bearer
&client_assertion=GW_ASSERTION_2
&subject_token=ICA_ASSERTION
&subject_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type
%3Aidentity-continuation
&audience=https%3A%2F%2Fras.example%2F
&resource=https%3A%2F%2Fapi.example%2Ftenants%2Facme-data%2F
&scope=files.read
~~~

The IdP applies {{continuation-validation}}:

* **ICA rules:** GatewayRAS is the RAS recorded for H0; H0 is accepted
  and its chain is active; `act` names `tool-gateway`'s canonical actor
  identity; the proof matches `cnf`; the `jti` is fresh.
* **Chain type:** H0 is in a delegated chain, and an ID-JAG is
  requested.
* **Governance state:** `agent-42`, Alice, the root binding of
  `analysis-client`, and its Client Association are active, and the
  root Delegation Authorization stands.
* **Continuation Association:** `tool-gateway` may continue
  `agent-42`'s delegated chains to `acme-data`.
* **Issuance authorization:** `agent-42` may act for Alice with
  `files.read` at the resource, within the chain authorization.
* **Target context:** Alice is `alice-ras` for `https://ras.example/`,
  and `tool-gateway` is `gateway-files` there.

The decoded onward ID-JAG:

~~~ json
{
  "iss": "https://idp.example/",
  "sub": "alice-ras",
  "aud": "https://ras.example/",
  "iat": 1789646471,
  "exp": 1789646771,
  "jti": "gw-grant-2",
  "client_id": "gateway-files",
  "resource": "https://api.example/tenants/acme-data/",
  "scope": "files.read",
  "auth_time": 1789646400,
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "cnf": {"jkt": "JKT_G"},
  "identity_continuation_handle": "Zp3kRt8VbN2wLq6YsD4mXe"
}
~~~

Its `sub` and `act` are those of the grant in the walkthrough of
{{FEDERATION}}. Only the client, the key, and the handle differ.

## Redemption at the Target {#walkthrough-target}

The gateway redeems the onward ID-JAG at `https://ras.example/` with the
`jwt-bearer` grant type, a `private_key_jwt` assertion for
`gateway-files`, and a fresh proof of G. The RAS validates the grant
and its confirmation, resolves Alice to `user-108`, correlates
`agent-42`, applies the actor gate, and authenticates `gateway-files`.
It does not implement {{ICA}}, so it ignores the handle. The decoded
access token:

~~~ json
{
  "iss": "https://ras.example/",
  "sub": "user-108",
  "aud": "https://api.example/tenants/acme-data/",
  "iat": 1789646472,
  "exp": 1789647072,
  "jti": "access-gw-1",
  "client_id": "gateway-files",
  "scope": "files.read",
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "cnf": {"jkt": "JKT_G"}
}
~~~

The API enforces Alice's permissions, the actor gate for `agent-42`, and
the tenant, as it would for the agent's own client. The gateway caches
the token for Alice, `agent-42`, `acme-data`, and H0
({{gateway-reuse}}).

## Self-Acting Variant {#walkthrough-self-acting}

The agent's client instead obtains a WAG for GatewayRAS under
"Self-Acting Issuance: WAG" in {{FEDERATION}}. The IdP establishes a
self-acting chain whose absolute expiration is eight hours after
issuance:

~~~ json
{
  "iss": "https://idp.example/",
  "sub": "agent-42",
  "aud": "https://ras.gateway.example/",
  "iat": 1789646580,
  "exp": 1789646880,
  "jti": "gw-wag-1",
  "client_id": "analysis-gw",
  "resource": "https://gateway.example/mcp",
  "scope": "tools.invoke",
  "cnf": {"jkt": "JKT_K"},
  "identity_continuation_handle": "Lb5wNq2XzR8tKc4VmP7sYd"
}
~~~

GatewayRAS correlates (`https://idp.example/`, `agent-42`) to its local
principal `gw-agent-42`, binds the handle, and issues an access token
with that principal as `sub` and no `act`. The gateway obtains an
assertion exactly as in {{walkthrough-assertion}} and requests
`urn:ietf:params:oauth:token-type:wag`. The IdP checks the self-acting
Continuation Association, the Agent Authorization of `agent-42` for
`files.read` at the resource, and the chain's expiration, and issues
this onward WAG with `typ` `wag+jwt`:

~~~ json
{
  "iss": "https://idp.example/",
  "sub": "agent-42",
  "aud": "https://ras.example/",
  "iat": 1789646590,
  "exp": 1789646890,
  "jti": "gw-wag-2",
  "client_id": "gateway-files",
  "resource": "https://api.example/tenants/acme-data/",
  "scope": "files.read",
  "cnf": {"jkt": "JKT_G"},
  "identity_continuation_handle": "Tf8hMv3QwJ6nZr1KxB4cGe"
}
~~~

The target RAS correlates `agent-42` to `service-principal-42`, as in
the self-acting variant of {{FEDERATION}}, and issues an access token
with that principal as `sub`, no `act`, `client_id` `gateway-files`,
and no refresh token. The API enforces the agent's own permissions.

## Negative Tests {#negative-tests}

Each case changes one condition of this walkthrough; all other checks
succeed.

| Changed condition | Checked by | Required result |
|---|---|---|
| No Continuation Association permits `tool-gateway` for `agent-42`'s delegated chains | IdP | HTTP 400, `unauthorized_client`; the gateway does not call the tool with its own authority |
| Delegated chain; the gateway requests a WAG | IdP | HTTP 400, `invalid_request`; no conversion of the acting relationship |
| `agent-42` disabled at the IdP after the root grant, then reactivated | IdP | HTTP 400, `invalid_continuation`; the chain stays ended, and a new root grant is needed |
| Root binding of `analysis-client` disabled while another binding of `agent-42` remains enabled | IdP | HTTP 400, `invalid_continuation` |
| Delegation Authorization does not permit `agent-42` to act for Alice at the requested resource | IdP | HTTP 400, `actor_unauthorized`; the chain stays continuable to other targets |
| Self-acting chain past its absolute expiration | IdP | HTTP 400, `invalid_continuation` |
| Two `resource` parameters in the continuation request | IdP | HTTP 400, `invalid_target` |
| GatewayRAS issued a bearer access token for the root, and no policy permits continuation from it | CAI | HTTP 400, `invalid_request`; the authorization is not eligible for continuation |
| The gateway redeems the onward ID-JAG without a proof of G | Target RAS | HTTP 400, `invalid_grant` |
| The gateway holds the target token for `agent-42` and receives a request for another agent with the same scope | Gateway | Continues that agent's own chain; a matching scope does not permit reuse |
{: title="Negative test cases"}

# Design Rationale {#rationale}

This non-normative appendix records the principal design choices.

## The Gateway Is a Client, Not an Actor {#rationale-client}

{{FEDERATION}} defines a client as software making OAuth requests for an
agent, and a gateway that continues an agent's request is exactly that.
Representing it as `client_id` keeps the governing principle of
{{FEDERATION}}: the Agent Principal is the authorization identity, and
client and workload identities do not replace it downstream.

Placing the gateway in `act`, as {{Section 5.5.5 of ICA}} does for the
current actor, would have three effects. Every agent behind a gateway
would share the gateway as its outermost actor, which recreates at the
actor level the shared-client problem that {{FEDERATION}} solves. A
governed RAS and API would have to process nested `act`, which
{{FEDERATION}} rejects for delegated grants. And a WAG, which carries no
`act`, could not represent the gateway at all. Identity preservation
needs no change to the target's processing and treats both grants the
same way.

{{ICA}} discloses lineage for audit. Here the authenticated `client_id`
identifies the current continuing client, and the IdP's hop records
hold the rest. Whether onward grants should also disclose earlier
continuing clients, without making them actors, is an open item
({{open-items}}).

A continuing workload that acts with its own authority is an agent in
its own right. Its relationship to the agent it serves is delegation
between agents, which {{FEDERATION}} leaves out of scope.

## No Conversion Between Relationships {#rationale-conversion}

In {{FEDERATION}}, authorization for one acting relationship does not
imply the other, and denied delegation does not fall back to
self-acting access. A gateway that could turn a delegated chain into a
WAG would let an agent act on its own authority because a user's request
reached it.

## Governance Events End the Chain {#rationale-ending}

A continuation does not resolve the agent again; the root's Identity
Binding and Client Association are the chain's only link between the
agent and an authenticated client. When either is withdrawn, the chain
has no current basis, even if another binding resolves the same agent
for new issuance. Ending rather than suspending the chain follows
{{Section 6.2 of ICA}}, where an ended chain stays ended, and
{{FEDERATION}}, where reactivation permits new decisions only.

## Self-Acting Chains Have an Absolute Expiration {#rationale-expiration}

A user session bounds a delegated chain. An Agent Authorization can be
indefinite, and a WAG yields no refresh token, so an unbounded
self-acting chain would become a substitute for the refresh token that
{{WAG}} prohibits. The absolute expiration plays the role of the finite
absolute authorization expiration that "Optional RAS Refresh Tokens" in
{{FEDERATION}} requires of refresh.

# Dependencies and Open Items {#dependencies}

This informative appendix records what this document needs from the
specifications it profiles, assessed against ICA-02, ID-JAG-04, WAG-01,
and the 2026-10-09 revision of {{FEDERATION}}.

| Specification | What this document needs | Consequence until resolved |
|---|---|---|
| ICA | Governed onward grants without continuing clients in `act`; non-user anchors; WAG chains; `jwt-bearer` redemption; certificate-bound access tokens at a continuation-aware RAS | This document replaces or extends those rules for governed chains ({{relationship-to-ica}}) |
| ID-JAG | {{Section 4.4 of ID-JAG}} requires `jwt-bearer`, while its key-bound example uses `jwt-dpop`, which {{Section 5.5.5 of ICA}} follows | Onward grants are redeemed with `jwt-bearer` under {{FEDERATION}} |
| WAG | Registration of the provisional token type and JWT type; a WAG carrying a continuation handle; a WAG issued by an IdP on a continuation exchange | Provisional values; `wag-continuation` is advertised in the ID-JAG metadata parameter pending coordination |
| {{AGENT-MANAGEMENT}} | Administration of Continuation Associations | Configured by each deployment |
{: title="Dependencies"}

## Open Items {#open-items}

\[\[ To be removed before publication as an RFC ]]

1. **Disclosure of continuing clients:** Should an onward grant
   disclose earlier continuing clients for audit, in a claim that does
   not make them actors ({{rationale-client}})?
2. **Self-acting discovery:** Should the IdP advertise support for
   self-acting continuation in metadata?
3. **Chain lifetime:** Should this document recommend a default maximum
   lifetime for self-acting chains?
4. **Continuation Association management:** Should
   {{AGENT-MANAGEMENT}} model Continuation Associations beside Client
   Associations?

# Document History
{:numbered="false"}

\[\[ To be removed before publication as an RFC ]]

-00

* Initial version.
