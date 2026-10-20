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
  RFC6749:
  RFC6750:
  RFC7523:
  RFC8693:
  RFC8707:
  RFC9449:
  RFC9110:
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
  AWS-CALLEDVIA:
    title: "AWS global condition context keys"
    target: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html
    author:
      - org: Amazon Web Services
    date: false
  KERBEROS-PAC:
    title: "Privilege Attribute Certificate Data Structure"
    target: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-pac/
    author:
      - org: Microsoft
    date: false
  RFC6755:
  RFC7519:
  RFC7662:
  WAG: I-D.carleton-workload-authz-grant
  WS-TRUST:
    title: "WS-Trust 1.4"
    target: http://docs.oasis-open.org/ws-sx/ws-trust/v1.4/os/ws-trust-1.4-spec-os.html
    author:
      - org: OASIS
    date: false

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
the same user, as the agent's grant to the gateway; the gateway is its
client, not an additional actor, and the grant lists the gateways on its
path in a separate claim. The document extends the Identity
Continuation Assertion to self-acting chains rooted in a WAG, and
defines the permission a gateway needs to continue an agent's chain and
the governance events that end it.

--- middle

# Introduction

An agent reaches a tool gateway, such as a Model Context Protocol (MCP)
gateway reached through {{EMA}}, with an access token obtained under
{{FEDERATION}}. The gateway selects a tool at request time and calls it
in another resource domain, whose authorization server does not accept
the gateway's token. The gateway holds neither the user's identity
assertion nor the agent's credential, and calling the tool as itself
would show the tool one client for every agent behind it: the
shared-client problem that {{FEDERATION}} addresses.

{{ICA}} lets a workload continue a request derived from an ID-JAG,
through OAuth 2.0 Token Exchange {{RFC8693}}, to another resource
authorization server (RAS) that trusts the same identity provider
(IdP). Applied to governed agents, a gateway exchanges evidence of an
accepted request for a new grant, and the IdP preserves the agent and
user, checks that the gateway may continue for that agent, and
authorizes access to the next resource. The agent's own client can
continue a chain in the same way, as for scheduled work after the user
signs out ({{walkthrough-scheduled}}).

The onward grant names the Agent Principal and acting relationship of
the chain's root grant, and for delegated access the same user. The
continuing client, typically a gateway, is its client, not an added
actor, and a separate claim, `continuation_via`, discloses the gateways
on the path ({{identity-preservation}}, {{continuation-via}}). A
downstream RAS and API that implement {{FEDERATION}}, with DPoP at the
RAS token endpoint, therefore accept it unchanged
({{target-processing}}). This document also adds the
Continuation Association, the IdP's permission for a client to continue
an agent's chains; extends {{ICA}} to self-acting chains, anchored to an
agent session; and ends chains on governance events.
{{relationship-to-ica}} lists each change to {{ICA}} and
{{FEDERATION}}.

## Protocol Overview {#overview}

An agent calls a tool gateway, and the gateway calls a tool in another
resource domain for the same agent. Inbound, the gateway is the API for
the agent's access token; outbound, it is the continuing client at the
Continuation Assertion Issuer (CAI), the IdP, and the tool's RAS. Here
the gateway's RAS also performs the CAI role.

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

1. The agent's client obtains a governed grant for the gateway's RAS,
   which roots a chain where policy permits ({{chain-establishment}}).
2. The client redeems it, and the RAS binds the handle
   ({{root-redemption}}).
3. The agent calls the gateway, which applies the API processing of
   {{FEDERATION}}.
4. The gateway exchanges the access token at the CAI for an assertion
   ({{assertion-issuance}}).
5. The gateway presents the assertion to the IdP, which checks the
   chain, the gateway's Continuation Association, and the agent's
   authorization for the tool, and issues an onward grant naming the
   same agent, with the gateway as client ({{continuation-exchange}}).
6. The tool's RAS processes the onward grant as any governed grant
   ({{target-processing}}).

Three lifetimes are independent, as in {{Section 6 of ICA}}: a grant's
short redemption window, the access token each RAS issues under its own
policy, and the chain that the IdP holds. Ending a chain stops new
continuations only. Grants and access tokens already issued, and any
refresh token a target issues, keep their own lifetimes
({{chain-ending}}). {{walkthrough}} shows the messages.

## Scope {#scope-boundaries}

This document applies under these conditions:

* **One IdP:** Every RAS in a chain trusts the IdP that issued the
  root grant. Continuity across a chain of IdPs is out of scope.
* **One agent:** Continuation never changes the Agent Principal. A
  continuing client is governed as a client, through its Continuation
  Associations, its attribution as `client_id`, and its registrations.
  One that exercises its own authority and needs authorization,
  attribution, or disablement as a principal is an Agent Principal of
  its own ("Governance Boundary and Execution Independence" in
  {{FEDERATION}}), and its acting for another agent is multi-agent
  delegation, which {{FEDERATION}} excludes.
* **An accepted grant:** The gateway's access token comes from a RAS
  that redeemed a governed grant. Where the IdP itself issues the
  gateway's access tokens, there is no hop to continue.

Whether a call still serves approved work is outside this document, as
in {{FEDERATION}}. This document defines one claim, `continuation_via`
({{continuation-via}}), and no new token format, error code, or
request parameter.

# Conventions and Terminology {#terms}

{::boilerplate bcp14-tagged-bcp14}

Agent Principal, Identity Binding, Client Association, acting
relationship, Delegation Authorization, Agent Authorization, Governance
Tenant, Target Tenant, and grant proof key follow {{FEDERATION}}.
Continuation Assertion Issuer (CAI), Identity Continuation Assertion,
continuation handle, chain, hop, chain authorization, lifecycle anchor,
canonical actor identity, and continuation-aware RAS follow {{ICA}}.
ID-JAG and WAG refer to the grants as {{FEDERATION}} profiles them.

In brief, for readers new to {{ICA}}: a chain is the IdP's record of
grants continued from one root grant; each grant in it is a hop, named
by an opaque continuation handle that the grant carries; the RAS that
accepts a grant binds its handle to the authorization it creates, and a
carrier conveys the handle within that RAS's domain
({{Section 5.3 of ICA}}). The actor gate is the check, under
{{FEDERATION}}, that an agent may act for a user at a resource.

{{ICA}} and {{FEDERATION}} use some of the same words differently:

| ICA term | Meaning in ICA | Term in this document |
|---|---|---|
| Workload | A service that received a request and may continue it | Continuing client |
| Current actor | The workload presenting the assertion | Continuing client, named by the assertion's `act` but not the onward grant's |
| Root actor | The client of the root exchange | Root client; the governed actor is the Agent Principal |
| Actor lineage | The actors disclosed in the onward `act` | Continuing clients disclosed in `continuation_via`; the full lineage is in the IdP's hop records |
| Tenant | The boundary for a chain and CAI trust | Governance Tenant |
{: title="ICA terms in this document"}

Unqualified, "actor" means the Agent Principal in an ID-JAG's `act`,
and "workload" keeps its meaning in {{FEDERATION}}. A continuing client
has a canonical actor identity under {{ICA}} only so that the IdP can
match the assertion's `act` to the authenticated client.

This document defines these terms:

Gateway:
: A resource server that receives requests from agents and calls other
  resources for them, choosing the target at request time.

Continuing client:
: The OAuth client, identified at each server by its registration
  there, that obtains an Identity Continuation Assertion, presents it to
  the IdP, and redeems the onward grant. It is a client in the sense of
  {{FEDERATION}}; the chain, not its identity, identifies the agent.

Source hop:
: The hop whose authorization a continuing client's incoming request
  carries. A continuing client that cannot see the handle identifies
  the source hop by the incoming access token or carrier.

Governed chain:
: A chain rooted in a governed ID-JAG (a delegated chain) or WAG (a
  self-acting chain) ({{governed-chain-authorization}}).

Continuation Association:
: An approved permission for an authenticated OAuth client to continue
  an Agent Principal's governed chains in one acting relationship
  ({{continuation-association}}).

Agent session:
: IdP state recording that an Agent Principal has recently
  authenticated through one Identity Binding; the lifecycle anchor of
  a self-acting chain ({{self-acting-root}}).

Onward grant:
: A governed ID-JAG or WAG issued on a continuation exchange.

# Establishing a Governed Chain {#chain-establishment}

The root exchange is grant issuance under {{FEDERATION}}. For a
governed root, tenant policy permits continuation
({{Section 5.1.2 of ICA}}) only when both:

* it permits continuation for the Agent Principal and acting
  relationship; and
* the Delegation Authorization or Agent Authorization under which the
  root grant is issued permits the agent's access to continue through
  other clients.

When it does, and the root resolves to a lifecycle anchor (one of
{{Section 6.1 of ICA}} for a delegated chain, or the anchor of
{{self-acting-root}}), the IdP MUST establish a chain under
{{Section 5.1.2 of ICA}}. Otherwise the IdP issues the governed grant
without a handle, as {{FEDERATION}} specifies. As in {{ICA}}, no
request parameter requests establishment, and advertised support does
not authorize it. The root grant's only addition to {{FEDERATION}} is
the `identity_continuation_handle` claim ({{Section 4 of ICA}}).

## Governed Chain Authorization {#governed-chain-authorization}

For a governed chain, the IdP records these facts in the chain
authorization ({{Section 5.1.4 of ICA}}), in addition to those ICA
requires, and treats them as follows at each continuation:

| Recorded fact | At each continuation |
|---|---|
| Acting relationship, Agent Principal, Governance Tenant, and root client | Fixed; never resolved again |
| For a delegated chain, the user and authentication context; for a self-acting chain, the agent session | Fixed; the user or session remains active ({{chain-ending}}) |
| Identity Binding, Client Association, and credential through which the root resolved the agent | Each remains enabled, unrevoked, and able to permit the root grant's issuance ({{chain-ending}}) |
| Delegation Authorization or Agent Authorization under which the root grant was issued | Not withdrawn as a whole; current authorization governs each target and authority ({{continuation-validation}}) |
{: title="Recorded facts of a governed chain"}

The Continuation Association, the Target Tenant, the user's subject at
the target, and the continuing client's registration there are
evaluated for each onward grant. Current policy can narrow the chain
authorization but cannot exceed it ({{Section 5.1.4 of ICA}}). The
limits of {{Section 6.3 of ICA}}, including the actor-lineage depth
bound, apply to the IdP's hop records, whose lineage entries are the
root client and the continuing clients.

The IdP SHOULD also enforce a configured continuation window: it refuses
continuation from a hop more than that window after it issued the hop,
with `invalid_grant` as for those limits. The window bounds how long a
CAI, including one that a compromised gateway operator controls, can
obtain continuations from a hop it accepted. A deployment whose gateway
continues from durable task state sets the window to the task's needs.

## Delegated Root {#delegated-root}

The root ID-JAG follows "Delegated Issuance: ID-JAG" in {{FEDERATION}},
and its anchors are those of {{Section 6.1 of ICA}}. For an ID Token
subject, the anchor is the user's IdP session that the ID Token's `sid`
identifies; `sid` is optional, so an IdP that establishes
session-anchored chains includes it in the ID Tokens it issues to
agents' clients. The root exchange can use either resolution mode of
{{FEDERATION}}, including presented-evidence mode, in which the request
carries the agent's workload credential as `actor_token`; {{FEDERATION}}
processes it ("Agent Resolution Input Validation"), and
{{Section 5.1.1 of ICA}} leaves that processing out of scope.

## Self-Acting Root and Agent Session {#self-acting-root}

This section extends {{ICA}} to chains with no user. The root WAG
follows "Self-Acting Issuance: WAG" in {{FEDERATION}} and carries the
root handle, which the IdP generates under rules 1 and 2 of
{{Section 4 of ICA}}. A self-acting chain has no authentication
context, so its onward WAGs carry no `auth_time`, `acr`, or `amr`.

The lifecycle anchor of a self-acting chain is an agent session, which
replaces the user-rooted anchors of {{Section 6.1 of ICA}}; the
prohibition there on rooting a chain from an access token still
applies. An agent session is evidence that the Agent Principal recently
authenticated through one Identity Binding. It does not show that any
particular work continues, and the Agent Authorization, not the
session, governs what the chain may do.

* **Creation:** When a self-acting issuance establishes a chain, the IdP
  anchors it to the active agent session for the resolved Agent
  Principal and the Identity Binding it resolved through, creating one
  if none is active. An ended session is never revived.
* **Refresh:** Completing steps 1 to 3 of "Self-Acting Issuance: WAG" in
  {{FEDERATION}} through that binding refreshes the session: client
  authentication, agent resolution through the binding, and the
  self-acting Client Association check, whether or not issuance is then
  authorized. The IdP MUST NOT refresh it on any other request,
  including a continuation exchange or delegated issuance.
* **Idle timeout:** The IdP MUST end an agent session that has not been
  refreshed within its configured idle timeout.
* **Absolute expiration:** The IdP MUST set a finite absolute
  expiration when it creates an agent session, no later than a
  configured maximum, and MUST NOT extend it.
* **Governance events:** An event of {{chain-ending}} that applies to the
  session's Agent Principal or Identity Binding also ends the session.

A self-acting chain ends with its agent session ({{Section 6.2 of ICA}}),
which neither the gateway nor the CAI can keep active. Work that a
gateway performs after the agent stops authenticating, such as queued
work, therefore loses continuation at the idle timeout; work that must
outlive the agent's authentication needs a durable anchor
({{open-items}}). A working agent obtains a new WAG at least as often
as its gateway access token expires, since WAG redemption yields no
refresh token, so a deployment sets the idle timeout longer than that
token's lifetime. If the token outlives the session, continuation fails
and the gateway's response leads the agent's client to a new root grant
({{gateway-reuse}}). IdP instances evaluate the idle timeout and the
absolute expiration against shared session state. An instance that
cannot confirm the session's state MUST reject the request rather than
issue, as {{Section 5.5.7 of ICA}} requires for replay reservations,
with the temporary refusal of {{continuation-errors}}, and MUST NOT
treat the session as ended on that basis; the chain stays continuable.

# Root Redemption at the Gateway's RAS {#root-redemption}

The gateway's RAS redeems the root grant under "Grant Redemption at the
RAS" in {{FEDERATION}}. When continuation-aware, it also binds the
handle as {{Section 5.2 of ICA}} specifies, for a WAG as for an ID-JAG,
and exposes it to the CAI through a carrier of {{Section 5.3 of ICA}}.

A continuation-aware RAS selects access-token protection under
"Access-Token Protection" in {{FEDERATION}}, including for a
continuation-capable grant that carries `cnf`. For such a grant, this
replaces step 3 of {{Section 5.2 of ICA}}, which permits only a
DPoP-bound access token.

Whatever the grant's binding, the RAS MUST NOT record an authorization
as eligible for continuation when it issued a bearer access token for
that authorization, unless resource policy explicitly permits
continuation from bearer access tokens for that client and resource.
The usual case is an unbound root grant redeemed without a DPoP proof,
as governed agent access permits. A hop therefore remains
sender-constrained from the RAS to the continuing client unless policy
accepts the exposure that {{Section 9.1 of ICA}} describes.

The CAI's attestation establishes that the RAS accepted the hop, not
that the gateway authorized the request, which the gateway does as the
API under "Access at the Resource Server" in {{FEDERATION}}.

# Assertion Issuance {#assertion-issuance}

{{Section 5.4 of ICA}} applies unchanged to both chain types. The CAI
attests acceptance, activity, and the continuing client's association
with the authorization, by the RAS's own authorization semantics; it
evaluates no governance relationship, and the assertion carries no
Agent Principal, user, or acting relationship. The CAI and the IdP are
configured with the same canonical actor identity for the continuing
client, which the CAI places in the assertion's `act` and the IdP
compares ({{Section 5.5.2 of ICA}}).

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

The continuing client selects `requested_token_type` by the acting
relationship it determined for the received access token as the API
("Profile Applicability" under "Access at the Resource Server" in
{{FEDERATION}}). `authorization_details` is processed as in
{{FEDERATION}}.

## Continuation Association {#continuation-association}

A Continuation Association permits an authenticated client to continue
an Agent Principal's governed chains in one acting relationship. It
belongs to the Governance Tenant of those chains and does not apply to
chains in another. It can restrict targets and authority, and it
narrows, without replacing, the
restrictions on who may continue that the chain authorization records
({{Section 5.1.4 of ICA}}). It has these limits:

* A Client Association does not imply a Continuation Association, nor
  the reverse.
* Permission to continue delegated chains does not imply permission to
  continue self-acting chains, nor the reverse.
* A Continuation Association is not an Identity Binding. A continuation
  exchange performs no agent resolution: the onward grant's agent comes
  only from the chain record, even when the continuing client is also
  bound to an agent of its own.

Policy representation and administration are outside this document.

## Validation {#continuation-validation}

For a first presentation of an assertion for a hop of a governed chain,
the IdP MUST perform the following steps in order and MUST reject the
request at the first step that fails, with the error of
{{continuation-errors}}. The checks of {{Section 5.5.3 of ICA}} apply
within the steps that cite them, changed only as stated.

1. **Client and proof:** Authenticate the client, map it to its
   canonical actor identity ({{Section 5.5.2 of ICA}}), and validate
   the DPoP proof.
2. **Request parameters (ICA rule 1):** The parameters of
   {{continuation-request}} replace that rule's requested token type,
   `resource`, and `scope` requirements.
3. **Assertion (ICA rules 2 and 3):** The assertion is well formed and
   validly signed by an issuer trusted as CAI for the hop's RAS.
4. **Current actor (ICA rule 5):** The assertion's `act` names the
   authenticated client's canonical actor identity, and the DPoP proof
   matches its `cnf`. As {{Section 5.5.6 of ICA}} requires, these
   checks precede every chain-state error.
5. **Chain state (ICA rule 4):** The hop is an accepted hop of an active
   chain, and neither it nor an ancestor is revoked. The chain has not
   ended under {{chain-ending}}, `requested_token_type` is the chain's
   grant type, and the chain and hop are within ICA's limits and the
   continuation window ({{governed-chain-authorization}}). An ended
   chain takes precedence over a wrong type, which takes precedence over
   a limit.
6. **Continuer:** A current Continuation Association in the chain's
   Governance Tenant permits the client for the chain's Agent Principal
   and acting relationship, and so do the chain authorization's
   restrictions on who may continue ({{Section 5.1.4 of ICA}}).
7. **Target context (ICA rule 5, replacing its subject resolution):**
   The Target Tenant for the requested resource, the continuing
   client's registration at the target RAS ("Issuance Prerequisites" in
   {{FEDERATION}}), and, for a delegated chain, the user's subject at
   the target ("Subject Resolution" in {{FEDERATION}}) each resolve
   unambiguously. A self-acting chain's subject is its Agent
   Principal, which is not resolved per target. Where policy requires
   path disclosure, the target RAS supports it ({{continuation-via}}).
8. **Freshness and replay (ICA rule 6).**
9. **Authorization (ICA rule 7):** The IdP authorizes the onward grant
   under "Issuance Authorization" in {{FEDERATION}} for the chain's
   Agent Principal and, for a delegated chain, its user, in the root
   client's context, for the requested target and authority. A current
   Delegation Authorization or Agent Authorization that permits
   continuation covers them; it need not name the continuing client.
   The Continuation Association's restrictions and the chain
   authorization also bound the target and authority. Withdrawal of the
   root authorization as a whole is chain state (step 5), not a failure
   of this step.

Because step 6 precedes step 7, a client without a Continuation
Association learns nothing about where the chain's user resolves. The
rules of {{FEDERATION}} for agent resolution and subject tokens do not
apply to the assertion. The IdP reserves the assertion's (`iss`, `jti`)
only after every step succeeds, as {{Section 5.5.7 of ICA}} requires,
so a rejected request consumes nothing.

An IdP that offers idempotent retry ({{Section 5.5.7.1 of ICA}}) MUST
include `requested_token_type` in the request fingerprint.

A presentation that matches an issued reservation is recovery, not a
first presentation. Recovery follows {{Section 5.5.7.1 of ICA}}: after
client authentication, the key proof, and the fingerprint, the IdP
returns the grant it issued if that grant is unexpired, neither the hop
nor an ancestor is revoked, and the chain has not ended, including
under {{chain-ending}}. No other step of this section applies, so
recovery consumes no limit, and a client whose response was lost
recovers even the last continuation that a hop-count limit permits.

## Onward Grants {#onward-grants}

The response follows {{Section 5.5.4 of ICA}}, with `issued_token_type`
equal to the requested grant type and no refresh token. Every onward
grant carries the common claims of "Common Grant Claims, Lifetime, and
Response" in {{FEDERATION}}, a fresh child handle under
{{Section 4 of ICA}}, and `cnf.jkt` for the key proven in the request
({{Section 5.5.2 of ICA}}). The configured grant lifetime limit of
"Common Grant Claims, Lifetime, and Response" in {{FEDERATION}}
applies. The lifetime bounds that {{FEDERATION}} derives from a subject
credential and an agent-resolution input do not apply to continuation,
and the assertion's expiration does not cap the onward grant. An onward
WAG MUST NOT outlive the absolute expiration of its chain's agent
session.

### Identity Preservation {#identity-preservation}

The IdP MUST construct every onward grant of a governed chain so that:

* it is the chain's grant type: an ID-JAG for a delegated chain and a
  WAG for a self-acting chain;
* it names the chain's Agent Principal: in an ID-JAG as the single
  `act` object, with the IdP issuer as `iss` and the Agent Principal
  identifier as `sub`, and in a WAG as `iss` and `sub`, with no `act`;
* for a delegated chain, it names the chain's user, resolved for the
  target RAS;
* its `client_id` identifies the continuing client's registration at the
  target RAS ("Issuance Prerequisites" in {{FEDERATION}}); and
* it lists the chain's continuing clients in `continuation_via`
  ({{continuation-via}}).

The continuing client MUST NOT appear in the onward grant's `act`; it
appears as the grant's client and in `continuation_via`, which disclose
it without making it an actor. The IdP takes the Agent Principal, the
user, and the acting relationship
from its chain record, never from the assertion or the request, so the
assertion's `act` never becomes the governed actor.

Continuation never converts the acting relationship. The IdP MUST NOT
issue a WAG from a delegated chain or an ID-JAG from a self-acting
chain. For a chain established without this document, it MUST NOT issue
a governed onward grant, and for a governed chain it MUST NOT issue an
onward ID-JAG whose `act` is constructed under {{Section 5.5.5 of ICA}}.
{{rationale-client}} explains the choice.

### Path Disclosure {#continuation-via}

Every onward grant of a governed chain discloses the continuing clients
it passed through, as intermediaries rather than actors, in this claim:

`continuation_via`:
: A JSON array of the canonical actor identities
  ({{Section 5.5.2 of ICA}}) of the continuing clients that created the
  hops after the root, on the branch from the root to the hop being
  issued, oldest first, so that the last entry is the current
  continuing client. Each entry is a JSON object with `iss` and `sub`
  string members; a recipient ignores other members. The root hop
  contributes no entry, so the root client appears only if it later
  continues the chain.

The IdP MUST include `continuation_via` in every onward grant of a
governed chain and MUST derive it from its hop records, never from the
assertion or the request, following the lineage rules of
{{Section 5.5.5 of ICA}}: parent references are immutable, and sibling
branches are excluded. It takes one entry from each hop after the root,
then merges consecutive identical entries. For example, with root
client A, continuing clients B and then A give `[B, A]`; A continuing
twice gives `[A]`; and A and then B give `[A, B]`. The
list is complete. Policy that narrows the disclosed depth of `act`
under {{ICA}} does not narrow it, because a forwarding intermediary is
disclosed, never hidden. The last entry and `client_id` identify the
same continuing client, the entry by its canonical actor identity and
`client_id` by its registration at the target.

A recipient MUST NOT treat an entry as an actor: entries are not
subject to the actor gate and authorize nothing. A target RAS MAY use
the list in its own policy, for example to admit agents only through
approved gateways.

A target RAS supports path disclosure when trusted configuration
between it and the IdP establishes that it does; this document defines
no metadata for it. A target RAS that supports path disclosure MUST
convey `continuation_via` unchanged in every access token or
introspection response it issues from the onward grant, including
access tokens it issues on refresh ("Optional RAS Refresh Tokens" in
{{FEDERATION}}), so that the API receives it. A target RAS that does
not support it still accepts onward grants under {{FEDERATION}} and
ignores the claim.

Where the chain authorization, the continuing client's Continuation
Association, or policy for the target requires path disclosure, the IdP
MUST NOT issue an onward grant for a target RAS not established to
support it ({{continuation-errors}}); issuing it would present a path
that the target discards as if it were complete. A RAS or API MUST NOT
read the absence of `continuation_via` as evidence that no continuing
client was involved, unless trusted configuration establishes that the
RAS that issued its token supports path disclosure.

This document defines `continuation_via` for governed chains. It is
proposed for {{ICA}} as the disclosure of forwarding intermediaries in
general ({{dependencies}}).

### Delegated: ID-JAG {#onward-id-jag}

The onward ID-JAG uses the format and claims of
{{Section 3.1 of ID-JAG}} and the following:

| Claim | Value |
|---|---|
| `sub` | The chain's user, in the IdP's subject namespace for the target RAS |
| `act` | The object of "Actor Resolution and Construction" in {{FEDERATION}}, with the chain's Agent Principal as `sub` and the IdP issuer as `iss`; any `sub_profile` reflects the IdP's current classification |
| `client_id` | The continuing client's registration at the target RAS |
| `auth_time`, `acr`, `amr` | Copied unchanged from the root, as {{Section 5.5.5 of ICA}} requires |
| `continuation_via` | The chain's continuing clients ({{continuation-via}}) |
{: title="Onward ID-JAG subject, actor, client, and path claims"}

{{Section 5.5.5 of ICA}} applies to the onward ID-JAG and to the IdP's
hop records, including immutable parent references, ancestry that
excludes sibling branches, and the merging of consecutive identical
actors that the actor-lineage depth bound counts. Two of its rules are
replaced: {{identity-preservation}} replaces the `act` it emits, and
{{target-processing}} its redemption grant type. The continuing clients
that its lineage would place in `act` appear in `continuation_via`
instead.

### Self-Acting: WAG {#onward-wag}

The onward WAG uses the JWT type and claims of "Grant Claims" in
{{FEDERATION}}, including its prohibition of `act`, with these values:

| Claim | Value |
|---|---|
| `iss` | The IdP issuer identifier |
| `sub` | The chain's Agent Principal identifier |
| `aud` | The target RAS issuer identifier |
| `client_id` | The continuing client's registration at the target RAS |
| `continuation_via` | The chain's continuing clients ({{continuation-via}}) |
{: title="Onward WAG issuer, subject, audience, client, and path claims"}

{{continuation-validation}} replaces the issuance steps of "Self-Acting
Issuance: WAG" in {{FEDERATION}}: no agent resolution or Client
Association check takes place.

## Errors {#continuation-errors}

Failures of the {{ICA}} checks within each step use the codes of
{{Section 5.5.6 of ICA}}, and client authentication failures use the
authentication method's error. The governed checks use these codes, for
both chain types:

| Failure | Step | Error |
|---|---|---|
| Missing `resource` | 2 | `invalid_request` |
| Missing `scope` | 2 | `invalid_scope`, as {{Section 3.3 of RFC6749}} and {{Section 5.5.6 of ICA}} provide |
| Multiple `resource` parameters | 2 | `invalid_target`, as in "Token Exchange Request" in {{FEDERATION}} |
| The chain has ended ({{chain-ending}}) | 5 | `invalid_continuation` |
| `requested_token_type` is not the chain's grant type | 5 | `invalid_request` |
| The hop's continuation window has passed | 5 | `invalid_grant` |
| No Continuation Association, or the chain authorization's restriction on who may continue, permits the continuing client | 6 | `unauthorized_client` |
| The Target Tenant, the user's subject, or the continuing client's registration cannot be resolved at the target | 7 | `invalid_target` |
| Policy requires path disclosure, and the target RAS is not established to support it | 7 | `invalid_target` |
| The chain authorization, the Continuation Association, or the agent's current authorization does not permit the target | 9 | `invalid_target` |
| The same sources permit the target but not the requested authority | 9 | `invalid_scope` or `invalid_authorization_details` |
{: title="Errors for governed continuation"}

The client is not the actor, and the subject token is the assertion,
so failures that {{FEDERATION}} reports at issuance as
`actor_unauthorized` or `invalid_grant` concern only the requested
target here. A continuing client recovers as follows:
`invalid_continuation` means the chain has ended; a limit failure
(`invalid_grant`) other than a rate limit means that the source hop can
no longer be continued ({{Section 5.5.6 of ICA}}); and any other code
affects only the request. After either of the first two, only a new
root grant, which the agent's client obtains, starts a new chain
({{gateway-reuse}}).

When the IdP cannot confirm shared state that a continuation depends
on, such as an agent session ({{self-acting-root}}) or a replay
reservation ({{Section 5.5.7 of ICA}}), it MUST respond with HTTP status
code 503 (Service Unavailable) ({{Section 15.6.4 of RFC9110}}) and
SHOULD include a `Retry-After` header field
({{Section 10.2.3 of RFC9110}}). This temporary refusal is not an OAuth
error response: the chain has not ended, and the request was not judged
invalid. Because the IdP reserves an assertion only after every step
succeeds, the continuing client MAY retry the same request with the
same assertion while it is unexpired, after any `Retry-After` interval,
with a fresh client assertion and DPoP proof as the retry rule of
"Dedicated Client Identity" in {{FEDERATION}} requires; otherwise it
obtains a fresh assertion. It MUST NOT treat a temporary refusal as the
end of the chain.

# Onward Redemption and Access {#target-processing}

The continuing client redeems the onward grant under "Redemption
Request" in {{FEDERATION}}: the `urn:ietf:params:oauth:grant-type:jwt-bearer`
grant type, client authentication as the client the grant names, and a
DPoP proof of the grant's `cnf` key. For governed chains, this replaces
the `jwt-dpop` redemption of {{Section 5.5.5 of ICA}};
{{Section 4.4 of ID-JAG}} requires `jwt-bearer`, and {{FEDERATION}}
applies the grant confirmation checks of ID-JAG to it. Every onward
grant carries `cnf`, so the target RAS needs DPoP support at its token
endpoint ("Grant Protection" in {{FEDERATION}}), which the continuing
client verifies under "Capability Discovery" in {{FEDERATION}}.

The target RAS and API process the onward grant and the resulting
access token as for any governed grant ("Grant Redemption at the RAS"
and "Access at the Resource Server" in {{FEDERATION}}). They see the
same Agent Principal, and for delegated access the same user and actor
gate, as for the agent's own client; only `client_id` and
`continuation_via` name continuing clients, and resource policy can
permit or deny an agent's access through a particular client or path.
A RAS that does not implement
{{ICA}} ignores the handle. One that does binds it and applies
{{root-redemption}}, so that a gateway in its domain can continue the
chain as a further hop that again names the same agent.

# Gateway Requirements {#gateway-deployment}

This section collects what a gateway does as a continuing client; the
rules of the IdP and the RASes it relies on are in the sections cited.

## Roles and Configuration {#gateway-roles}

A gateway combines roles, as {{FEDERATION}} permits ({{overview}}); its
operator's RAS is typically the continuation-aware RAS and CAI. A
deployment adds this configuration to that of {{FEDERATION}}:

| Party | Configuration |
|---|---|
| IdP | Tenant policy permitting continuation; Continuation Associations for the gateway; the gateway's client registration and canonical actor identity; trust in the gateway's CAI ({{Section 7.3 of ICA}}); the gateway's registration at each target RAS, for each acting relationship the target serves separately |
| Gateway's RAS | Continuation-aware processing and advertisement; assertion issuance; the gateway's registration as the client that operates the gateway resource; the gateway's canonical actor identity, as the IdP holds it |
| Gateway | A client credential for each server and a DPoP key |
| Target RAS | A client registration for the gateway, one for each population where delegated and self-acting access are distinguished by registration; DPoP support |
{: title="Configuration added by a gateway deployment"}

Where a target RAS distinguishes delegated and self-acting tokens by
client registration ("Profile Applicability" under "Access at the
Resource Server" in {{FEDERATION}}), the IdP selects the gateway's
registration there by the chain's acting relationship. A gateway that
serves several Governance Tenants is configured in each, because
{{ICA}} scopes actor identities and CAI trust to one tenant; how it
selects among those registrations is an open item ({{open-items}}).

## Topologies {#gateway-topologies}

| Topology | CAI | Use |
|---|---|---|
| Gateway authorization server | The gateway's own RAS ({{Section 8.1 of ICA}}) | The gateway operator runs an authorization server for the gateway resource; the baseline |
| Shared authorization server | A separate CAI trusted for that RAS ({{Section 5.4.6 of ICA}}) | The gateway is a resource server behind an API-management or enterprise authorization server |
| Gateway behind a gateway | Each gateway's RAS | Each hop is a governed continuation; every onward grant names the same agent, and `continuation_via` lists each gateway on the path |
| IdP-issued gateway tokens | None | Not applicable ({{scope-boundaries}}) |
{: title="Gateway topologies"}

## Continuing a Request {#gateway-reuse}

To continue a request, a gateway:

1. processes the incoming access token as the API ("Access at the
   Resource Server" in {{FEDERATION}}), including the actor gate;
2. obtains an assertion from the CAI with that request's own token, as
   below ({{walkthrough-assertion}} shows the request);
3. verifies the target's capabilities and requests the chain's grant
   type from the IdP ({{continuation-request}},
   {{walkthrough-continuation}});
4. redeems the onward grant with `jwt-bearer` and a proof of its key
   ({{target-processing}});
5. reuses downstream tokens only within the same context and source
   hop; and
6. handles errors without falling back, as below.

The CAI binds the assertion to the handle of the token the gateway
presents ({{Section 5.4.3 of ICA}}), but a gateway that holds several
agents' tokens chooses which to present. The gateway MUST therefore
request an assertion only with the access token, or a carrier derived
from it, of the request it is continuing.

"Client Token Reuse" in {{FEDERATION}} applies to every onward grant and
downstream access token the gateway holds: it reuses one only for a
request in the same agent, user, tenant, target, authority, and proof
context. The gateway MUST also reuse one only for a request that
arrived on the same source hop. Two chains can share all of that
context yet differ in root binding, credential, anchor, and
revocation, so serving one chain's request with a token obtained on
another would let it continue after its own chain had ended
({{Section 8 of ICA}}). Each source hop therefore needs its own
continuation, once for each target.

When continuation from a request's source hop fails with
`invalid_continuation`, or with a limit failure other than a rate limit,
the gateway SHOULD reject the agent's request with HTTP 401 and the
`invalid_token` error code of the access token's scheme ({{RFC6750}},
{{RFC9449}}), so that the agent's client obtains a new access token and,
with it, a new root grant. A temporary refusal is not such a failure:
the gateway retries as {{continuation-errors}} describes.

After the IdP rejects a governed continuation for a request, the
continuing client MUST NOT serve that request with its own authority or
through a chain established without this document. This extends the
no-fallback rule of "Profile Applicability and Downgrade Prevention" in
{{FEDERATION}}, which covers retrying as ordinary access or without
proof. Gateway-side tool filtering narrows what the gateway attempts
but does not authorize.

# Chain Ending and Governance Events {#chain-ending}

In addition to the conditions of {{Section 6.2 of ICA}}, a governed
chain ends when the IdP applies a change that the following table lists
as ending it. Each such change withdraws the chain's permission to
continue under that section: continuation fails with
`invalid_continuation`, and the chain stays ended if the relationship
is later restored.

| Change applied | Effect on governed chains |
|---|---|
| Disable the Agent Principal | Every chain for the agent ends |
| Disable the user | The user's delegated chains end |
| Disable the root Identity Binding or remove the root Client Association, or change either so that it no longer permits the root grant's issuance, such as its acting relationship or credential class | Chains rooted through it end, even when the agent has other enabled bindings |
| Revoke the credential or trust material through which the root resolved the agent, including through the workload-credential revocation events (WISE) of "Time, Replay, and Key Validation" in {{FEDERATION}}; routine rotation is not revocation | Chains rooted through it end |
| Withdraw or let expire, as a whole, the Delegation Authorization or Agent Authorization under which the root grant was issued, or withdraw its permission to continue | Chains rooted under it end |
| End the user's IdP session or the agent session | Chains anchored to it end |
| Remove a Continuation Association | Only that client stops continuing the agent's chains |
| Remove some targets or authority from current policy or an authorization | Continuation to them fails ({{continuation-errors}}); the chain continues elsewhere |
| Disable the local agent or user at a target RAS | No new access at that RAS ({{FEDERATION}}); the chain continues elsewhere |
{: title="Effects of administrative changes on governed chains"}

The IdP MUST treat a chain as ended once it has applied, since the
chain's establishment, any change that the table lists as ending it,
even if the relationship has since been restored. It applies such
changes within the freshness limit of "Issuance Authorization" in
{{FEDERATION}}, and it can determine the outcome when it applies the
change or at the next continuation, for example by comparing a revision
of each relationship, recorded at establishment and changed by every
disablement or withdrawal. Grants and access tokens already issued
follow "Authorization Changes and Revocation" in {{FEDERATION}}, which
the grant-derived revocation of {{AGENT-LIFECYCLE}} can propagate.

# Conformance and Capability Advertisement {#conformance}

## Conformance Claims {#conformance-claims}

The roles are the IdP, the continuation-aware RAS and its CAI, the
continuing client, and the target RAS. An implementation claims
delegated continuation, self-acting continuation, or both, for each
role it implements. Each claim requires the same realization under
{{FEDERATION}} and the applicable requirements of {{ICA}} as this
document changes them. A target RAS that does not continue the chain
implements {{FEDERATION}} with DPoP support at its token endpoint, and
nothing from this document unless it supports path disclosure
({{continuation-via}}).

Each claim has this mandatory interoperability path:

* **Client authentication:** The continuing client, CAI, IdP, and
  target RAS MUST implement {{RFC7523}} `private_key_jwt` client
  authentication, under "Dedicated Client Identity" in {{FEDERATION}}
  for its audience, replay, and retry rules.
* **Proof:** They MUST implement DPoP {{RFC9449}} with the algorithms
  of "Client Authentication and Algorithms" in {{FEDERATION}}.
* **Assertion issuance:** Every CAI that serves a continuing client MUST
  support assertion issuance at its token endpoint with an access-token
  `subject_token` ({{Section 5.4.1 of ICA}}), resolving the token as
  {{Section 5.4.6 of ICA}} describes when the CAI is not the accepting
  RAS. The continuing client MUST implement that request.

## Metadata {#metadata}

A continuation-aware RAS that binds handles of governed grants lists
`urn:ietf:params:oauth:grant-profile:governed-agent-continuation` in
`authorization_grant_profiles_supported` ({{Section 7.2 of ID-JAG}}),
together with the governed profile URIs that identify the grants it
accepts. The value indicates handle binding under
{{Section 5.2 of ICA}} with the access-token protection and eligibility
of {{root-redemption}}, and redemption of onward grants with
`jwt-bearer` ({{target-processing}}); it does not indicate `jwt-dpop`
support. A RAS lists ICA's
`urn:ietf:params:oauth:grant-profile:id-jag-continuation`, with the
requirements of {{Section 7.2 of ICA}}, only if it also binds handles of
chains established without this document. As for the self-acting
profile URIs of {{FEDERATION}}, use of this parameter for WAGs awaits
coordination ({{dependencies}}).

An IdP that supports delegated continuation advertises
`identity_continuation_supported` ({{Section 7.1 of ICA}}), which
indicates continuation-capable ID-JAG issuance; an IdP that supports
only self-acting continuation does not. Support for self-acting
continuation is established through trusted configuration ("Capability
Discovery" in {{FEDERATION}}); no IdP metadata advertises it.
Advertisement indicates capability and does not authorize continuation.

# Security Considerations {#security}

The security considerations of {{ICA}} and {{FEDERATION}} apply.

## Gateway Compromise {#security-gateway}

A compromised gateway that can still authenticate and prove its key can
continue each chain whose access token it has received, to any target
that the chain authorization, the agent's current authorization, and
its Continuation Associations permit, and can use the downstream tokens
it holds until they expire. Where its operator does not control the
CAI, it cannot continue a chain whose token it has not received,
because the CAI attests only hops bound to tokens presented to it
({{Section 5.4.3 of ICA}}). In the baseline topology the operator runs
the CAI, which can attest any hop its RAS accepted, as
{{Section 9.5 of ICA}} notes for a compromised RAS, until the chain
ends or the hop's continuation window passes. In either case it cannot
change the agent or user, convert the acting relationship, or exceed
the agent's own authorization. Narrow Continuation Associations, chain
authorizations that restrict targets, a short continuation window,
short downstream token lifetimes, and sender-constrained ingress reduce
the exposure; the last also keeps a stolen bearer token at the gateway
from inducing an honest continuation ({{Section 9.1 of ICA}},
{{root-redemption}}).

## Attribution Through an Intermediary {#security-attribution}

Downstream records attribute an action to the Agent Principal and, for
delegated access, the user, with the continuing client as `client_id`
and every continuing client on the path in `continuation_via`. A target
RAS can therefore audit and authorize the path without consulting the
IdP, and so can an API whose RAS supports path disclosure; the IdP's
hop records remain authoritative. A handle does not distinguish a
root grant from an onward grant; a resource that must tell a gateway
from the agent's own client uses the authenticated `client_id` or the
presence of `continuation_via`, which only onward grants carry.

## Self-Acting Chains {#security-self-acting}

When an agent stops authenticating through a binding, its self-acting
chains through that binding end within the idle timeout without
administrative action. A party holding the agent's credential can keep
its session active, as a stolen user credential can keep a user session
active, until the absolute expiration or the credential's revocation
({{chain-ending}}).

## Disablement Windows {#security-disablement}

Issued onward grants and downstream access tokens, including those a
gateway has cached, remain usable after a chain ends until they expire
or their revocation is applied. A refresh token that a target RAS
issues under "Optional RAS Refresh Tokens" in {{FEDERATION}} extends
access further; a deployment that relies on chain ending configures its
targets not to issue refresh tokens to continuing clients, so that
renewal is another continuation.

# Privacy Considerations {#privacy}

The privacy considerations of {{ICA}} and {{FEDERATION}} apply.
Continuation discloses the Agent Principal identifier to each target
the gateway reaches, extending the cross-resource correlation that a
stable agent identifier allows, and the gateway learns which agents and
users call which tools. An onward grant discloses every continuing
client on the path, as {{Section 5.5.5 of ICA}} would, but as
intermediaries rather than actors, and it does not disclose the root
client. The IdP's hop records hold the complete path and are sensitive
audit data.

# IANA Considerations {#iana}

This document requests registration of the following value in the
"OAuth URI" registry established by {{RFC6755}}:

* URN: `urn:ietf:params:oauth:grant-profile:governed-agent-continuation`
* Common Name: Grant profile identifier for a Resource Authorization
  Server that binds the `identity_continuation_handle` claim of
  governed ID-JAGs and WAGs to authorization state under the Identity
  Continuation Profile for Governed Agent Federation
* Change Controller: IETF
* Specification Document: {{metadata}} of this document.

This document also requests registration of the following claim in the
"JSON Web Token Claims" registry established by {{RFC7519}}:

* Claim Name: `continuation_via`
* Claim Description: Continuing clients that a continued grant passed
  through, as intermediaries rather than actors
* Change Controller: IETF
* Specification Document(s): {{continuation-via}} of this document.

and of the following member in the "OAuth Token Introspection Response"
registry established by {{RFC7662}}:

* Name: `continuation_via`
* Description: Continuing clients that the grant from which the
  introspected token was issued passed through
* Change Controller: IETF
* Specification Document(s): {{continuation-via}} of this document.

If {{ICA}} adopts `continuation_via`, these registrations move to it.
The `identity_continuation_handle` JWT claim and the
`urn:ietf:params:oauth:grant-profile:id-jag-continuation` value are
registered by {{ICA}}, and this document uses the handle claim in
WAGs. Errors are those of {{RFC6749}}, {{ICA}}, and {{FEDERATION}}.

--- back

# Gateway Walkthrough {#walkthrough}

This non-normative walkthrough adds a gateway to the dedicated-client
walkthrough of {{FEDERATION}} and reuses its identities: the client
`analysis-client`, the Agent Principal `agent-42`, the user Alice, and
the resource `https://api.example/tenants/acme-data/` at
`https://ras.example/`, where Alice is `alice-ras` to the IdP and
`user-108` locally. Keys, thumbprints, and compact JWTs are labeled
placeholders; JWTs are decoded payloads; HTTP bodies are line-wrapped.

The gateway is an MCP gateway at `https://gateway.example/mcp`, whose
operator runs `https://ras.gateway.example/` as its RAS and CAI.

* **IdP:** Alice's Delegation Authorization, `agent-42`'s Agent
  Authorization, and tenant policy permit continuation. The gateway is
  the client `tool-gateway` (`private_key_jwt`), with canonical actor
  identity (`https://gateway.example/`, `tool-gateway`). Two
  Continuation Associations permit it to continue `agent-42`'s
  delegated chains and its self-acting chains, each to resources in
  `acme-data`. The IdP trusts GatewayRAS as CAI for its own hops, paired
  with `https://gateway.example/` as the gateway's identity authority
  ({{Section 7.3 of ICA}}), and maps `tool-gateway` to
  `gateway-files` (delegated) and `gateway-files-svc` (self-acting) at
  `https://ras.example/`.
* **GatewayRAS:** The agent's client is `analysis-gw` for delegated
  access and `analysis-gw-svc` for self-acting access, which is how the
  gateway tells them apart. The gateway is `tool-gateway`, the client
  that operates `https://gateway.example/mcp`, with the same canonical
  actor identity. Alice is `alice-gw` to the IdP and `gw-user-7`
  locally.
* **Keys:** K is the agent client's grant proof key; G is the gateway's
  DPoP key.

## Root Grant and Gateway Access Token {#walkthrough-root}

The agent's client exchanges Alice's ID Token, whose `sid` resolves to
her IdP session, as in {{FEDERATION}}, but for `audience`
`https://ras.gateway.example/`, `resource`
`https://gateway.example/mcp`, and `scope` `tools.invoke`. The root
ID-JAG:

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

The client redeems it with a proof of K. GatewayRAS binds the handle,
H0, and issues `GW_ACCESS_TOKEN`, DPoP-bound and carrying H0:

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

The agent calls a tool with this token and a proof of K. The gateway
validates both, enforces the actor gate for `agent-42` acting for
Alice, and routes the call to the file service in `acme-data`.

## Assertion {#walkthrough-assertion}

`GW_CAI_PROOF` proves G, and `GW_ASSERTION_1` is a `private_key_jwt`
assertion for `tool-gateway` addressed to GatewayRAS:

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
for the resource `tool-gateway` operates, reads H0, rechecks that the
authorization is active and eligible, and names `https://idp.example/`
in `identity_continuation_authorization_server`. The assertion,
`ICA_ASSERTION`:

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

Every step of {{continuation-validation}} passes: H0 belongs to an
active delegated chain, a Continuation Association permits
`tool-gateway`, Alice is `alice-ras` at `https://ras.example/` and
`tool-gateway` is `gateway-files` there, and Alice's Delegation
Authorization permits `agent-42`, in `analysis-client`'s context, to
act for her with `files.read`. The onward ID-JAG:

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
  "continuation_via": [
    {"iss": "https://gateway.example/", "sub": "tool-gateway"}
  ],
  "cnf": {"jkt": "JKT_G"},
  "identity_continuation_handle": "Zp3kRt8VbN2wLq6YsD4mXe"
}
~~~

Its `sub` and `act` are those of the grant in the walkthrough of
{{FEDERATION}}; its client, key, handle, identifiers, and times differ.
It carries the root's `auth_time`, and its `continuation_via` lists
`tool-gateway`, whose registration at the target `client_id` names.

## Redemption at the Target {#walkthrough-target}

The gateway redeems the onward ID-JAG at `https://ras.example/` with the
`jwt-bearer` grant type, a `private_key_jwt` assertion for
`gateway-files`, and a fresh proof of G. The RAS validates the grant
and its confirmation, resolves Alice to `user-108`, correlates
`agent-42`, applies the actor gate, and ignores the handle and
`continuation_via`, since it implements only {{FEDERATION}}. The access
token:

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
the token for Alice, `agent-42`, Target Tenant `acme-data`,
`https://ras.example/`, the resource, `files.read`, key G, and H0
({{gateway-reuse}}).

## Self-Acting Variant {#walkthrough-self-acting}

The agent's client instead obtains a WAG for GatewayRAS as
`analysis-gw-svc`. The IdP creates an agent session for `agent-42`
through the binding of `analysis-client`, with a 30-minute idle timeout
and an absolute expiration eight hours later, and anchors a self-acting
chain to it:

~~~ json
{
  "iss": "https://idp.example/",
  "sub": "agent-42",
  "aud": "https://ras.gateway.example/",
  "iat": 1789646580,
  "exp": 1789646880,
  "jti": "gw-wag-1",
  "client_id": "analysis-gw-svc",
  "resource": "https://gateway.example/mcp",
  "scope": "tools.invoke",
  "cnf": {"jkt": "JKT_K"},
  "identity_continuation_handle": "Lb5wNq2XzR8tKc4VmP7sYd"
}
~~~

GatewayRAS issues an access token for its local principal
`gw-agent-42`, with no `act` and `client_id` `analysis-gw-svc`, by which
the gateway treats it as self-acting. With an assertion for this
chain's handle, issued at 1789646585, the gateway requests a WAG. The
self-acting Continuation Association, the Agent Authorization of
`agent-42` for `files.read`, and the agent session all hold, and the
IdP issues this onward WAG with `typ` `wag+jwt`:

~~~ json
{
  "iss": "https://idp.example/",
  "sub": "agent-42",
  "aud": "https://ras.example/",
  "iat": 1789646590,
  "exp": 1789646890,
  "jti": "gw-wag-2",
  "client_id": "gateway-files-svc",
  "resource": "https://api.example/tenants/acme-data/",
  "scope": "files.read",
  "continuation_via": [
    {"iss": "https://gateway.example/", "sub": "tool-gateway"}
  ],
  "cnf": {"jkt": "JKT_G"},
  "identity_continuation_handle": "Tf8hMv3QwJ6nZr1KxB4cGe"
}
~~~

The target RAS correlates `agent-42` to `service-principal-42`, as in
{{FEDERATION}}, and issues an access token for it with no `act` and no
refresh token. The agent's client obtains a new WAG each time its
ten-minute gateway access token expires, which refreshes the agent
session; the gateway's continuations do not.

## Two-Gateway Variant {#walkthrough-two-gateways}

Here `tool-gateway` reaches the file service through a second gateway,
`data-gateway` at `https://data-gateway.example/`, whose RAS is
continuation-aware and performs the CAI role. The IdP configures
`data-gateway` as it does `tool-gateway`, with canonical actor identity
(`https://data-gateway.example/`, `data-gateway`), a Continuation
Association for `agent-42`'s delegated chains, and the registration
`data-files` at `https://ras.example/`; D is its DPoP key.

`tool-gateway` continues H0 to the data gateway's RAS, which binds the
child hop H1. `data-gateway` then obtains an assertion for H1 and
continues to `https://ras.example/`. The onward ID-JAG (excerpt):

~~~ json
{
  "sub": "alice-ras",
  "aud": "https://ras.example/",
  "client_id": "data-files",
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "continuation_via": [
    {"iss": "https://gateway.example/", "sub": "tool-gateway"},
    {"iss": "https://data-gateway.example/", "sub": "data-gateway"}
  ],
  "cnf": {"jkt": "JKT_D"}
}
~~~

In this variant, `https://ras.example/` supports path disclosure
({{continuation-via}}), so the access token it issues carries the same
list to the API (excerpt):

~~~ json
{
  "sub": "user-108",
  "client_id": "data-files",
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "continuation_via": [
    {"iss": "https://gateway.example/", "sub": "tool-gateway"},
    {"iss": "https://data-gateway.example/", "sub": "data-gateway"}
  ],
  "cnf": {"jkt": "JKT_D"}
}
~~~

The API applies the actor gate to `agent-42` alone. A policy that admits
`agent-42` only through `tool-gateway` matches the first entry, and the
last entry identifies the client that presented the grant.

## Scheduled Variant {#walkthrough-scheduled}

Here `agent-42` prepares a daily report for Alice after she has signed
out, without a gateway. The agent's operator runs
`https://ras.agents.example/` as a continuation-aware RAS and CAI for
its task service `https://agents.example/tasks`, where the agent's
client is `analysis-tasks` and Alice is `alice-tasks` to the IdP. The
IdP accepts refresh-token subjects from `analysis-client` ("Subject
Token Validation" in {{FEDERATION}}), trusts AgentRAS as CAI for its
own hops, and has a Continuation Association that permits
`analysis-client` to continue `agent-42`'s delegated chains to
resources in `acme-data`. `analysis-client` has the default canonical
actor identity of {{Section 5.5.2 of ICA}}, (`https://idp.example/`,
`analysis-client`), so the IdP pairs AgentRAS with itself as the
client's identity authority.

While Alice is signed in, she asks for the report. The client holds a
refresh token that the IdP issued to `analysis-client` for Alice, whose
grant has her Delegation Authorization for `agent-42` explicitly
associated. It presents that refresh token as the `subject_token`, with
`subject_token_type`
`urn:ietf:params:oauth:token-type:refresh_token`, for `audience`
`https://ras.agents.example/`, `resource`
`https://agents.example/tasks`, and `scope` `tasks.run`. The IdP
anchors the chain to the refresh token's grant, not to Alice's session
({{Section 6.1 of ICA}}). The root ID-JAG (excerpt):

~~~ json
{
  "sub": "alice-tasks",
  "aud": "https://ras.agents.example/",
  "client_id": "analysis-tasks",
  "resource": "https://agents.example/tasks",
  "scope": "tasks.run",
  "auth_time": 1789646400,
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "cnf": {"jkt": "JKT_K"},
  "identity_continuation_handle": "Wd4nKs8QpZ2vXe6TbR1mLy"
}
~~~

AgentRAS redeems it with a proof of K and binds the handle, H0, to a
task record that holds no bearer credential and designates
`analysis-client` to run the task (illustrative):

~~~
task_id:   task-7
user:      alice-tasks
agent:     agent-42
runner:    analysis-client
handle:    Wd4nKs8QpZ2vXe6TbR1mLy   # H0
schedule:  daily at 06:00 UTC
status:    active
~~~

The client does not need the refresh token for this task again. Every
run continues from H0, so the deployment sets the continuation window
({{governed-chain-authorization}}) to the task's duration.

At 06:00 UTC the next day, with Alice signed out, the platform's
scheduler starts a run that names only `task-7`. The run has no
incoming request: it continues from the task's hop under the
scheduled-run carrier of {{Section 5.3 of ICA}}. The client,
authenticating to AgentRAS, names `task-7`; AgentRAS derives H0 from
the active task record for which `analysis-client` is designated into
a Transaction Token for the run, as in {{Appendix B.3 of ICA}}, and
the client exchanges it at AgentRAS's token endpoint for an assertion
bound to K. The client then requests an
ID-JAG from the IdP for `https://ras.example/`, `resource`
`https://api.example/tenants/acme-data/`, and `scope` `files.read`.

The continuation exchange performs no agent resolution: the agent comes
from the chain record, not from `analysis-client`'s Identity Binding
({{continuation-association}}). The grant is unexpired and unrevoked,
the Continuation Association permits `analysis-client`, and Alice's
Delegation Authorization permits `agent-42` to act for her with
`files.read`. The onward ID-JAG (excerpt):

~~~ json
{
  "sub": "alice-ras",
  "aud": "https://ras.example/",
  "iat": 1789711205,
  "exp": 1789711505,
  "client_id": "analysis-api",
  "resource": "https://api.example/tenants/acme-data/",
  "scope": "files.read",
  "auth_time": 1789646400,
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "continuation_via": [
    {"iss": "https://idp.example/", "sub": "analysis-client"}
  ],
  "cnf": {"jkt": "JKT_K"},
  "identity_continuation_handle": "Hc7rVm3NxT9kQw5ZpB2sJf"
}
~~~

Its `sub`, `act`, and `client_id` are those of the grant in the
walkthrough of {{FEDERATION}}, so `https://ras.example/` processes it as
before, and the API sees `agent-42` acting for Alice. Its `auth_time`
is still Alice's sign-in of the previous day, carried unchanged from the
root ({{Section 5.5.5 of ICA}}). `continuation_via` names
`analysis-client` because the root client continued the chain; the root
hop itself contributes no entry ({{continuation-via}}).

Runs need no credential that carries Alice's authority: each creates a
new child of H0 with a short-lived assertion and grant bound to K. If
Alice withdraws her Delegation Authorization for `agent-42`, the chain
ends and the next run fails ({{negative-tests}}), while her
delegations to other agents continue.

## Negative Tests {#negative-tests}

Each case changes the stated conditions; all other checks succeed.

| Changed condition | Checked by | Required result |
|---|---|---|
| No Continuation Association permits `tool-gateway` for `agent-42`'s delegated chains | IdP | HTTP 400, `unauthorized_client`, before target resolution; the gateway does not call the tool with its own authority |
| Delegated chain; the gateway requests a WAG | IdP | HTTP 400, `invalid_request`; no conversion of the acting relationship |
| `agent-42` disabled at the IdP after the root grant, then reactivated before the next continuation | IdP | HTTP 400, `invalid_continuation`; the chain stays ended, and a new root grant is needed |
| Root binding of `analysis-client` disabled while another binding of `agent-42` remains enabled | IdP | HTTP 400, `invalid_continuation` |
| Alice's Delegation Authorization does not cover the requested resource | IdP | HTTP 400, `invalid_target`; the chain stays continuable to other targets |
| GatewayRAS keeps the self-acting hop's authorization active as durable task state, `agent-42`'s client stops obtaining WAGs, and the agent session passes its idle timeout | IdP | HTTP 400, `invalid_continuation`; the gateway's continuations do not keep the session active |
| Two `resource` parameters in the continuation request | IdP | HTTP 400, `invalid_target` |
| The Continuation Association for `tool-gateway` requires path disclosure, and `https://ras.example/` is not established to support it | IdP | HTTP 400, `invalid_target`; the IdP does not issue a grant whose path the target would discard |
| The continuation used the chain's last permitted hop, its response was lost, and the gateway repeats the request with the same assertion | IdP | Where the IdP offers idempotent retry, HTTP 200 with the same onward grant; limits do not apply to recovery |
| Governed agent access: the root ID-JAG has no `cnf`, the agent's client redeems it without a DPoP proof, GatewayRAS issues a bearer access token, and no policy permits continuation from it | CAI | HTTP 400, `invalid_request`; the authorization is not eligible for continuation |
| The gateway redeems the onward ID-JAG without a proof of G | Target RAS | HTTP 400, `invalid_grant` |
| In the scheduled variant, Alice withdraws her Delegation Authorization for `agent-42` before the next run | IdP | HTTP 400, `invalid_continuation`; the chain stays ended, and Alice's delegations to other agents are unaffected |
| The gateway holds the target token for `agent-42` and receives a request for another agent with the same scope | Gateway | Continues that agent's own chain; a matching scope does not permit reuse |
| The gateway holds the target token obtained under H0 and receives a request from `agent-42` for Alice with the same scope on another chain | Gateway | Continues that chain from its own access token; the token obtained under H0 is not reused, so the other chain's ending applies to its requests |
{: title="Negative test cases"}

# Relationship to Other Specifications {#relationship-to-ica}

This informative appendix lists what this document changes in {{ICA}}
and {{FEDERATION}} and needs from the specifications it profiles,
assessed against
ICA-02, ID-JAG-04, WAG-01, and the 2026-10-09 revision of
{{FEDERATION}}.

## Changes to ICA {#ica-changes}

Where this document is silent, {{ICA}} applies unchanged.

| Area | ICA | This document |
|---|---|---|
| Root exchange | Base ID-JAG exchange; `actor_token` out of scope ({{Section 5.1.1 of ICA}}) | Governed issuance in either resolution mode ({{delegated-root}}) |
| Root grant | ID-JAG | Governed ID-JAG or WAG |
| Establishment | Tenant policy permits continuation ({{Section 5.1.2 of ICA}}) | The root's Delegation or Agent Authorization must also permit it ({{chain-establishment}}) |
| Anchors | User session or refresh-token grant; no non-user roots ({{Section 6.1 of ICA}}) | Unchanged for delegated chains; an agent session for self-acting chains ({{self-acting-root}}) |
| Chain authorization | User, root actor, authentication context, anchor, restrictions | Adds the facts of {{governed-chain-authorization}} |
| Who may continue | Chain authorization and current policy | Also a Continuation Association ({{continuation-association}}) |
| Continuation request | Zero or more `resource`; optional `scope`; ID-JAG ({{Section 5.5.1 of ICA}}) | One `resource`; required `scope`; the chain's grant type ({{continuation-request}}) |
| Retry fingerprint | No requested token type ({{Section 5.5.7.1 of ICA}}) | Includes `requested_token_type` ({{continuation-validation}}) |
| Assertion issuance at the token endpoint | Optional; recommended for a RAS acting as CAI ({{Section 5.4.1 of ICA}}) | Required of every CAI that serves a continuing client ({{conformance-claims}}) |
| Onward `act` | Continuing actor atop IdP-derived lineage ({{Section 5.5.5 of ICA}}) | The Agent Principal alone in an ID-JAG, none in a WAG; hop records unchanged ({{identity-preservation}}) |
| Path disclosure | Continuing clients as nested actors in `act` ({{Section 5.5.5 of ICA}}) | Continuing clients as intermediaries in `continuation_via`, preserved to the API by targets that support path disclosure ({{continuation-via}}) |
| Onward redemption | `jwt-dpop` ({{Section 5.5.5 of ICA}}) | `jwt-bearer` with grant confirmation ({{target-processing}}) |
| Access token for a grant with `cnf` | DPoP-bound, never bearer ({{Section 5.2 of ICA}}) | Protection under {{FEDERATION}}; bearer access tokens, whatever the grant's binding, make a hop ineligible without explicit policy ({{root-redemption}}) |
| Advertisement | RAS `id-jag-continuation` with `jwt-dpop`; IdP `identity_continuation_supported` ({{Section 7 of ICA}}) | `governed-agent-continuation` for governed grants, without `jwt-dpop`; the IdP flag only for delegated continuation ({{metadata}}) |
| Chain ending | Anchor end, revocation, withdrawn permission ({{Section 6.2 of ICA}}) | Also governance events ({{chain-ending}}) |
| Continuation window | None | A recommended per-hop window ({{governed-chain-authorization}}) |
{: title="Changes to ICA for governed chains"}

## Changes to FEDERATION {#federation-changes}

Where this document is silent, {{FEDERATION}} applies unchanged.

| Area | FEDERATION | This document |
|---|---|---|
| Issuance authorization | For the authenticated client ("Issuance Authorization") | For an onward grant, in the root client's context; the continuing client is authorized by its Continuation Association ({{continuation-validation}}) |
| Agent resolution and Client Association | Required for each grant | None on a continuation exchange; the agent comes from the chain record ({{continuation-association}}) |
| Grant lifetime | Bounded also by the subject credential and the agent-resolution input | The configured limit and, for a WAG, the agent session ({{onward-grants}}) |
| Downstream client registration | One association per authenticated client ("Issuance Prerequisites") | Also selected by acting relationship where a target distinguishes the two ({{gateway-roles}}) |
| Errors | `actor_unauthorized` for a denied delegation and `invalid_grant` for an unresolvable user ("Issuance Errors") | The codes of {{ICA}} ({{continuation-errors}}) |
| Bearer access tokens | Permitted under explicit configuration ("Access-Token Protection") | Also make a hop ineligible for continuation without explicit policy ({{root-redemption}}) |
| Fallback | No retry as ordinary access or without proof ("Profile Applicability and Downgrade Prevention") | Also no service of the request with the continuing client's own authority ({{gateway-reuse}}) |
{: title="Changes to FEDERATION for continuation"}

## Dependencies {#dependencies}

| Specification | What this document needs | Consequence until resolved |
|---|---|---|
| ICA | The changes of {{ica-changes}}, and a forwarding disclosure mode with `continuation_via` for chains in general | This document applies them to governed chains and defines `continuation_via` itself |
| ID-JAG | {{Section 4.4 of ID-JAG}} requires `jwt-bearer`, while its key-bound example uses `jwt-dpop`, which {{Section 5.5.5 of ICA}} follows | Onward grants are redeemed with `jwt-bearer` under {{FEDERATION}} |
| WAG | Registration of the provisional token type and JWT type; a WAG carrying a continuation handle; a WAG issued by an IdP on a continuation exchange | Provisional values; `governed-agent-continuation` is advertised for WAGs in the ID-JAG metadata parameter pending coordination |
| {{AGENT-MANAGEMENT}} | Administration of Continuation Associations and of an authorization's permission to continue | Configured by each deployment |
{: title="Dependencies"}

## Open Items {#open-items}

\[\[ To be removed before publication as an RFC ]]

1. **Home of `continuation_via`:** Should {{ICA}} define it, with an
   acting or forwarding mode for each hop, so that this document uses
   ICA's claim instead of its own? Should policy ever be able to narrow
   it, as it can narrow the depth of `act` ({{continuation-via}})?
2. **Self-acting discovery:** Should the IdP advertise support for
   self-acting continuation in metadata?
3. **Agent session limits:** Should this document recommend default
   idle and absolute limits for agent sessions, and convey a session's
   expiration to the gateway so that long-running work can obtain a new
   root before it?
4. **Continuation Association management:** Should
   {{AGENT-MANAGEMENT}} model Continuation Associations beside Client
   Associations?
5. **Durable self-acting anchors:** Should a self-acting chain be able
   to anchor to a work authorization with its own lifecycle, as a
   delegated chain can anchor to a refresh-token grant
   ({{rationale-anchor}})?
6. **Tenant selection at a gateway:** How does a gateway that serves
   several Governance Tenants select its registration and credential at
   the IdP, when neither its incoming token nor the assertion response
   names the Governance Tenant?
7. **Temporary refusals:** Should {{ICA}} adopt the same HTTP 503
   response for state it cannot confirm, and define an OAuth error code
   for policy that blocks a chain only temporarily
   ({{continuation-errors}})?
8. **Grant anchors:** Unattended work, as in {{walkthrough-scheduled}},
   needs a chain anchored to a refresh-token grant, which
   {{Section 6.1 of ICA}} makes optional. Should a delegated
   continuation claim require IdP support for grant anchors?

# Design Rationale {#rationale}

This non-normative appendix records the principal design choices.

## The Gateway Is a Client, Not an Actor {#rationale-client}

In {{FEDERATION}}, the Agent Principal is the authorization identity,
and client and workload identities do not replace it downstream. A
gateway that continues an agent's request selects the target but
exercises the agent's authority, within the agent's authorization and
under the Continuation Association, a permission of the same kind as a
Client Association. A gateway governed as a client has its own
permission, attribution as `client_id`, and registrations that can be
disabled, without becoming a principal. A gateway that exercises its
own authority and needs authorization, attribution, or disablement as a
principal is an Agent Principal, and its acting for another agent is
delegation between agents, outside {{FEDERATION}}.

Placing the gateway in `act`, as {{Section 5.5.5 of ICA}} does for the
current actor, would give every agent behind a gateway the same
outermost actor, recreating at the actor level the shared-client
problem. A governed RAS and API would have to process nested `act`,
which {{FEDERATION}} rejects, and a WAG, which carries no `act`, could
not represent the gateway at all.

In the terms of {{WS-TRUST}}, the gateway requests access on behalf of
the agent rather than acting as it: the agent acts for the user, and the
gateway forwards. A forwarding intermediary is still disclosed, in
`continuation_via`. Related precedents record forwarding services apart
from the principal: the Kerberos privilege attribute certificate lists
the services that a delegated ticket passed through ({{KERBEROS-PAC}}),
and AWS lists the services that made a request on a principal's behalf
({{AWS-CALLEDVIA}}). Attribution and path-based policy therefore need no
lineage in `act`.

The user's approval reaches the
gateway through the Delegation Authorization, which must permit
continuation for a delegated chain to exist. Continuation never turns a
delegated chain into a WAG, which would let an agent act on its own
authority because a user's request reached it.

## Governance Events End the Chain {#rationale-ending}

The root's Identity Binding, Client Association, and credential are the
chain's only link between the agent and an authenticated client. When
any is withdrawn, the chain has no current basis, even if another
binding resolves the same agent for new issuance. An ended chain stays
ended, as in {{Section 6.2 of ICA}}, and reactivation permits new
decisions only, as in {{FEDERATION}}.

## Self-Acting Chains Anchor to an Agent Session {#rationale-anchor}

{{ICA}} anchors a chain to state showing that its principal is still
present and records what the chain may do separately. An Agent
Authorization is often indefinite, so as an anchor it cannot tell a
working agent from one that has stopped; a dedicated-client assertion
lasts one request, and routine credential rotation would end chains.
Only the agent's own authentication refreshes an agent session, so a
gateway cannot extend a chain it continues, and keeping it per Identity
Binding stops activity on one platform from sustaining chains rooted
through another. The absolute expiration bounds a session the agent
keeps active, as the absolute authorization expiration of "Optional RAS
Refresh Tokens" in {{FEDERATION}} bounds refresh; without it, a chain
would substitute for the refresh token that {{WAG}} prohibits.

# Document History
{:numbered="false"}

\[\[ To be removed before publication as an RFC ]]

-00

* Initial version.
