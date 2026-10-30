---
title: "Human Oversight Profile for Governed Agent Federation"
abbrev: "Governed Agent Oversight"
category: std
docname: draft-mcguinness-oauth-governed-agent-oversight-latest
submissiontype: IETF
stand_alone: yes
ipr: trust200902
area: "Security"
workgroup: "Web Authorization Protocol"
keyword:
 - OAuth
 - agent federation
 - human oversight
 - deferred token response
 - approval
venue:
  group: "Web Authorization Protocol"
  type: "Working Group"
  mail: "oauth@ietf.org"
  arch: "https://mailarchive.ietf.org/arch/browse/oauth/"
  github: "mcguinness/governed-agent-profiles"
  latest: "https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html"
author:
 - fullname: Karl McGuinness
   organization: Independent
   email: public@karlmcguinness.com
normative:
  FEDERATION:
    title: "OAuth 2.0 Profile for Governed Agent Federation"
    author:
      - name: Karl McGuinness
    date: false
    seriesinfo:
      Internet-Draft: draft-mcguinness-oauth-governed-agent-federation
    target: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html
  DTR: I-D.ietf-oauth-deferred-token-response
  RFC6749:
  RFC8693:
  RFC9449:
informative:
  AGENT-LIFECYCLE:
    title: "Governed Agent Lifecycle Profile for SCIM and OAuth"
    author:
      - name: Karl McGuinness
    date: false
    seriesinfo:
      Internet-Draft: draft-mcguinness-oauth-governed-agent-lifecycle
    target: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html
  AIMS: I-D.ietf-wimse-aims
  ARAP:
    title: "AuthZEN Access Request and Approval Profile - Draft 1"
    author:
      - org: OpenID AuthZEN Working Group
    date: false
    target: https://openid.github.io/authzen/authzen-access-request-approval-profile-1_0.html
  AROP:
    title: "AuthZEN Access Request OAuth Profile - Draft 1"
    author:
      - name: Karl McGuinness
    date: false
    target: https://github.com/openid/authzen/blob/main/profiles/authzen-access-request-oauth/authzen-access-request-oauth-profile-1_0.md
  CIBA:
    title: "OpenID Connect Client-Initiated Backchannel Authentication Flow - Core 1.0"
    author:
      - org: OpenID Foundation
    date: 2021-09-01
    target: https://openid.net/specs/openid-client-initiated-backchannel-authentication-core-1_0.html
  CONTINUATION:
    title: "Identity Continuation Profile for Governed Agent Federation"
    author:
      - name: Karl McGuinness
    date: false
    seriesinfo:
      Internet-Draft: draft-mcguinness-oauth-governed-agent-continuation
    target: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html
  ICA: I-D.mcguinness-oauth-id-continuation-assertion
  MCP:
    title: "Model Context Protocol Specification, Revision 2026-07-28"
    author:
      - org: Model Context Protocol
    date: 2026-07-28
    target: https://modelcontextprotocol.io/specification/2026-07-28
  MCP-SEP-2643:
    title: "SEP-2643: Structured Authorization Denials"
    author:
      - org: Model Context Protocol
    date: false
    target: https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2643
  MCP-SEP-2848:
    title: "SEP-2848: Asynchronous Approval for Tool Calls"
    author:
      - name: Karl McGuinness
    date: false
    target: https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2848
  MCP-TASKS:
    title: "Tasks Extension, Revision 2026-07-28"
    author:
      - org: Model Context Protocol
    date: 2026-07-28
    target: https://tasks.extensions.modelcontextprotocol.io/specification/2026-07-28/tasks
  MISSION-APPROVAL:
    title: "Mission Deferred Approval for OAuth 2.0"
    author:
      - name: Karl McGuinness
    date: false
    target: https://mcguinness.github.io/mission-bound-authorization/draft-mcguinness-oauth-mission-approval.html
  OVERSIGHT-ACTS: I-D.ehstand-oversight-acts
  RFC7009:
  RFC8417:
  WAG: I-D.carleton-workload-authz-grant

--- abstract

The OAuth 2.0 Profile for Governed Agent Federation decides which
governed agent acts, for whom, and under what authorization, and an
identity provider issues the resulting grant without a person present.
It bounds what an external approval can do but leaves asynchronous
approval undefined.

This document defines three oversight modes for governed agent access.
With a human in the loop, an authenticated person decides on the exact
governed request before a grant issues or an action executes. With a
human on the loop, grants issue at once, but each can be observed and
ended with a defined effect within a documented bound. With the human
out of the loop, standing authorization applies with no per-request
decision. The document profiles OAuth Deferred Token Response so that
an identity provider can hold a governed grant until a person decides,
binds that decision to the resolved agent, user, client, target,
authority, and proof key, and requires the grant that follows to be the
one the request would have produced. A resource authorization server
can likewise hold the redemption of a governed grant, binding the
approval to that one redemption and bounding what it issues by the
approval's expiry. The document also describes how Model Context
Protocol servers hold tool calls under these modes.

--- middle

# Introduction

Under {{FEDERATION}}, an identity provider (IdP) issues a governed grant
when a Delegation Authorization or an Agent Authorization permits the
request. The basis of those authorizations is a deployment choice:
administrator assignment, organizational policy, task authorization, or
user consent ("Authorization Relationships" in {{FEDERATION}}). Each is
decided before the request arrives. Many deployments also need a person
to decide at the moment an agent asks for something sensitive, or at
least to see each grant as it issues and be able to stop it.

The pieces for that exist separately. OAuth Deferred Token Response
{{DTR}} lets a token endpoint answer later. OpenID Client-Initiated
Backchannel Authentication {{CIBA}} reaches a person out of band.
AuthZEN's access request profiles route an approval and complete it as
a token ({{ARAP}}, {{AROP}}). Model Context Protocol {{MCP}} servers can
hold a tool call while they wait. None of them says which agent, user,
and authority an approval covers when the requester is a governed
agent, or what grant follows it. {{DTR}} does not say that the token it
eventually returns keeps the original subject, actor, or client.

{{FEDERATION}} answers who acts, for whom, and under what authorization.
{{DTR}} answers how a token endpoint waits. This document answers when
a person must decide, what the decision binds to, and what grant follows
it. It defines:

* three oversight modes, and how policy selects them
  ({{modes}});
* deferred governed issuance: the pending request, who may approve it,
  what an approval can change, and the checks and grant at resolution
  ({{deferred-issuance}});
* deferred redemption: holding the redemption of a governed grant at
  the RAS until an approver decides, the approval's binding to that
  redemption, recovery, and the tokens that follow
  ({{deferred-redemption}});
* supervised issuance: what an IdP and a deployment must provide before
  claiming that a person can observe and end each grant
  ({{supervised}});
* per-action oversight at a resource, within the authority of the
  access token ({{per-action}}).

{{mcp}} describes how Model Context Protocol servers realize these
modes; that section is informative.

## Protocol Overview {#overview}

An agent acting for Alice asks for authority that policy says Alice must
approve. The client opts in to deferral, and the IdP holds the request
until Alice decides.

~~~
Client          IdP              Alice            RAS
  |              |                 |                |
  | (1) exchange, completion_mode=deferred, DPoP K  |
  |------------->|                 |                |
  | (2) authorization_pending, deferral_code        |
  |<-------------|                 |                |
  |              | (3) approval request (agent, user,
  |              |     client, target, authority)   |
  |              |---------------->|                |
  |              |<----------------|                |
  | (4) poll with deferral_code, DPoP K             |
  |------------->|                 |                |
  | (5) ID-JAG for the approved authority, cnf K    |
  |<-------------|                 |                |
  | (6) redeem as any governed grant                |
  |-------------------------------------------------->|
~~~
{: #overview-figure title="Deferred governed issuance"}

1. The client sends a governed token exchange request with
   `completion_mode=deferred` and a DPoP proof ({{opt-in}}).
2. The IdP completes every issuance check except Alice's decision,
   records the pending request, and returns a deferred response
   ({{deferring}}).
3. Alice authenticates and approves the request, or a narrower one,
   through a channel this document does not define ({{approval}}).
4. The client polls with the deferral code, proving the same key.
5. The IdP re-checks the request and issues the governed grant the
   request would have produced, for the approved authority and bound to
   the same key ({{resolution}}).
6. The RAS processes the grant as any governed grant under
   {{FEDERATION}}.

## Scope {#scope}

This document covers governed grant issuance at the IdP, including
continuation ({{CONTINUATION}}), governed grant redemption at the RAS,
and oversight of individual actions at an API. It does not cover:

* approval of a task, which Mission-Bound Authorization addresses
  ({{MISSION-APPROVAL}});
* multi-party approval or the provenance of an approver's authority;
* the approval channel or its user interface;
* the format or transport of notices to overseers;
* completion of an approved access request as a token under {{AROP}}
  at the IdP, or continuation from an authorization whose redemption
  was deferred ({{open-items}}).

This document defines no new token format, claim, error code, grant
type, or request parameter.

# Conventions and Terminology {#terms}

{::boilerplate bcp14-tagged}

Agent Principal, Identity Binding, Client Association, acting
relationship, Delegation Authorization, Agent Authorization, Governance
Tenant, Target Tenant, actor gate, and resource authorization server
(RAS) follow {{FEDERATION}}. ID-JAG and WAG {{WAG}} refer to the grants
as {{FEDERATION}} profiles them. Deferral code, deferred response,
completion mode, and originating grant follow {{DTR}}. Local Suspension
and grant-derived revocation follow {{AGENT-LIFECYCLE}}.

This document defines these terms:

Oversight mode:
: The policy that determines whether a person decides on a governed
  request before a grant issues or an action executes (human in the
  loop), may observe and end what was issued (human on the loop), or is
  not involved per request (human out of the loop) ({{modes}}).

Approver:
: A person who decides on a pending governed request, a pending
  governed redemption, or a held action,
  acting within authority over it that the person held before the
  request. An agent, a client, a policy engine, or another automated
  system is not an approver.

Overseer:
: A person who can observe grants issued under supervised issuance and
  can intervene ({{supervised}}).

Governed request context:
: For a governed token exchange request, the resolved Agent Principal;
  for delegated access, the resolved user; the authenticated client and
  its registration at the target RAS; the acting relationship; the
  Governance and Target Tenants; the RAS, resource, and requested
  authority (scope and any authorization details); for a continuation,
  the continuing client; and the request's proof key.

Pending governed request:
: IdP state for a governed token exchange request that passed every
  check of {{FEDERATION}} except an approver's decision. It holds the
  request's governed request context and is not a credential.

Pending governed redemption:
: RAS state for the redemption of a governed grant that passed every
  check of {{FEDERATION}} except an approver's decision. It holds the
  values those checks established ({{redemption-deferring}}) and is not
  a credential.

Intervention:
: An action that ends or narrows authority already issued: grant-derived
  revocation, withdrawing or narrowing a Delegation or Agent
  Authorization, a Local Suspension, or disabling the agent.

Intervention bound:
: The documented maximum time from an intervention until the affected
  target stops accepting the authority it ends, including propagation,
  caching, and the lifetime of tokens accepted without a check.

# Oversight Modes {#modes}

| Mode | Who decides, and when | Issuance or execution waits for | Defined in |
|---|---|---|---|
| Human in the loop | An approver, before the grant issues or the action executes, on its governed request context or the action | The approver's decision | {{deferred-issuance}}, {{deferred-redemption}}, {{per-action}} |
| Human on the loop | No one before issuance; an overseer can observe each grant and intervene | Nothing | {{supervised}} |
| Human out of the loop | No one per request; standing authorization applies | Nothing | {{FEDERATION}} |
{: #modes-table title="Oversight modes"}

These rules apply to every mode:

* **Policy selects the mode.** The IdP determines the mode for a
  governed request from trusted policy for the resolved agent, acting
  relationship, user, client, target, and requested authority, usually
  as a condition of the Delegation or Agent Authorization; the RAS
  determines it for a redemption from its own policy. A request
  parameter or the client's opt-in to deferral MUST NOT select a mode or
  lower one that policy requires.
* **Each decision point applies its own mode.** IdP issuance, IdP
  continuation, RAS redemption, and the API's decision on an action
  each apply the mode their policy requires. Oversight at one point does not satisfy
  another: a resource domain that requires a person to decide on an
  action applies its own human-in-the-loop decision at the action
  ({{per-action}}), as the RAS decides anew under {{FEDERATION}}.
* **Only a person approves.** A decision by a supervising agent, a
  policy engine, or a risk service can be a condition of issuance, but
  a request decided that way is not human in the loop.
* **An approval is not standing authority.** An approval covers the one
  request or action it was made on. Making it standing authority is a
  change to the Delegation or Agent Authorization, made by a principal
  authorized to make that change; requests within the changed
  authorization are then human out of the loop.

Human out of the loop is the behavior of {{FEDERATION}}; this document
adds no requirement for it.

In the terms of {{OVERSIGHT-ACTS}}, a human-in-the-loop approval is a
release: the approver permits a specified request within authority held
beforehand, and the release establishes that the request was permitted,
not that it was correct. A notice under supervised issuance supports an
observation, and an intervention is a decision. This document does not
define how such acts are recorded.

# Deferred Governed Issuance {#deferred-issuance}

This section profiles {{DTR}} for governed token exchange requests at
the IdP: ID-JAG and WAG requests under {{FEDERATION}}, and continuation
requests under {{CONTINUATION}}. A pending governed request moves
through these steps, which the subsections define:

| Event | IdP action | Result |
|---|---|---|
| Request with the opt-in | Completes every check except the approver's decision; for a continuation, reserves the assertion ({{deferring}}, {{deferred-continuation}}) | Pending; deferred response |
| Poll before a decision | Verifies the client and its key | `authorization_pending` or `slow_down` |
| Approver decides | Records the decision for this request only ({{approval}}) | Pending until the next poll |
| Poll after approval | Re-checks the request; for a continuation, counts the grant against the limits as it issues ({{resolution}}) | Grant; reservation ISSUED |
| Poll after denial, or a re-check fails | Issues nothing | `access_denied`; reservation FAILED |
| Client revokes the deferral code ({{Section 7 of DTR}}) | Ends the request | `access_denied`; reservation FAILED |
| `expires_in` elapses | Issues nothing | `expired_token`; reservation FAILED |
{: title="Steps of a pending governed request"}

Reservation states apply to a deferred continuation at an IdP that
offers idempotent retry ({{deferred-continuation}}). A pending request
holds no limit capacity and no grant, so its end releases nothing else.

## Client Opt-In {#opt-in}

A client that can wait for an approver includes `deferred` in the
`completion_mode` parameter of its token exchange request
({{Section 4.1 of DTR}}). It MUST present a DPoP proof {{RFC9449}} on
that request, whatever its client authentication method. This narrows
{{Section 10.1 of DTR}}, which lets a confidential client using
`private_key_jwt` omit DPoP: under this document the deferral code and
the grant it yields are bound to one key.

When policy requires human in the loop and the request does not include
`deferred`, the IdP MUST NOT return a deferred response
({{Section 4.1 of DTR}}) and MUST NOT issue the grant. It rejects the
request ({{Section 5.2 of RFC6749}}) with `actor_unauthorized` for
delegated issuance or `invalid_target` for self-acting issuance. These
are the errors {{FEDERATION}} assigns when approval requires a condition
the selected composition cannot enforce ("Issuance Authorization" in
{{FEDERATION}}); this document reuses them for an approval that the
request did not let the IdP obtain. This document defines no discovery
of a target's oversight mode; a client learns to opt in from
configuration or from a pre-token hint ({{Section 4.2 of DTR}}). A
client that can wait for an approver and handle a deferred response can
include `deferred` on every request that policy might hold, since the
IdP answers synchronously when it does not defer. A refusal of such a
request is not a missing opt-in, and the client does not retry it
unchanged.

## Deferring {#deferring}

Before returning a deferred response, the IdP MUST complete every check
that {{FEDERATION}} requires for the request except the approver's
decision: client authentication, agent resolution, the Client
Association, subject validation and resolution, the Delegation or Agent
Authorization, target and tenant resolution, and the client
registration association. A request that fails a check is rejected as
{{FEDERATION}} specifies and is not deferred. An approver therefore
never decides on a request the IdP would refuse.

The IdP then records a pending governed request holding the request's
governed request context, and returns the deferred response of
{{Section 5.4 of DTR}}. The deferral code represents that pending
governed request and nothing else. The IdP MUST bind it to the
authenticated client and to the key of the request's DPoP proof, and
MUST reject a poll or cancellation that does not prove that key
({{Section 10.1 of DTR}}). The IdP MUST set `expires_in` no greater than
a configured maximum pending lifetime for the applicable policy.

The client does not present the subject token or the agent-resolution
input again; the IdP validates them when it receives the request. The
lifetime limits of {{FEDERATION}} still bound the grant issued at
resolution: an ID-JAG does not outlive its subject credential ("Grant
Issuance" in {{FEDERATION}}), and no grant outlives an agent-resolution
input that bounds it, such as a platform JWT ("Common Grant Claims,
Lifetime, and Response" in {{FEDERATION}}). For root issuance, the IdP
MUST set `expires_in` so that the pending governed request ends no
later than the earliest of those expirations. An approval late in the
window therefore yields a shorter grant. A deployment that needs a
longer window uses a subject credential that expires later, such as a
refresh token.

## Approval {#approval}

The IdP MUST present a pending governed request only to approvers that
policy designates for it, and MUST authenticate an approver at the
strength that policy requires. For delegated access, an approver is the
user or a person whom policy authorizes to decide for that user and
target. For self-acting access, an approver is a person policy
designates, such as the agent's accountable owner. The IdP MUST NOT
accept a decision from the requesting client, the agent, or another
agent.

The IdP MUST show the approver the governed request context: the agent,
the user for delegated access, the client, the target RAS and resource,
the requested authority, and, for a continuation, the continuing client.
For a continuation, it MUST also show any restrictions of the chain
authorization and the Continuation Association that apply to the
requested target ("Restrictions" in {{CONTINUATION}}); an approval
does not change them.
Text that the client or agent supplies, such as a stated reason, MUST
be shown as supplied by the requester and MUST NOT replace or restate
the governed request context.

An approver can approve the request as shown, approve a narrower
authority, or deny it. An approval MUST NOT widen the governed request
context: a different agent, user, client, target, resource, or acting
relationship, or broader authority, needs a new request. An approval of
narrower authority yields a grant with that authority, as {{RFC8693}}
and "Issuance Authorization" in {{FEDERATION}} permit, and the token
response's `scope` reports it.

An approval covers only the pending governed request it was made on.
The IdP MUST NOT apply it to another request, including a later request
with the same governed request context.

An approver can condition an approval on time. The IdP enforces such a
condition only on the grant it issues. It MUST NOT treat a condition on
downstream access as enforced, since {{FEDERATION}} defines no portable
deadline on authorization a RAS issues and rejects issuance whose
approval requires a downstream condition the composition cannot
enforce.

This document does not define the approval channel. {{CIBA}}, with a
`binding_message` that describes the request, is one way to reach the
user; an access request service under {{ARAP}} is another.

## Resolution {#resolution}

Before issuing a grant in response to a poll, the IdP MUST re-evaluate
the request under {{Section 10.7 of DTR}} and, in addition, MUST confirm
that:

* the Agent Principal is active;
* for root issuance, the Identity Binding and Client Association used
  still permit the request;
* the Delegation or Agent Authorization still permits the target and
  the approved authority;
* for delegated access, the user is active and resolves as before;
* for a continuation, neither the presented hop nor an ancestor is
  revoked, the chain has not ended, a Continuation Association still
  permits the continuing client, the target, and the approved
  authority, and the continuation is within the limits of
  {{Section 6.3 of ICA}} ({{deferred-continuation}}); and
* no change applied within the IdP's freshness limit ("Issuance
  Authorization" in {{FEDERATION}}) withdraws any of these.

If any check fails, the IdP returns `access_denied` and issues no grant,
as {{Section 10.7 of DTR}} requires. A denial resolves to
`access_denied`, and a pending request that outlives `expires_in`
resolves to `expired_token` ({{Section 5.6 of DTR}}). A client cancels
a pending request by revoking its deferral code ({{Section 7 of DTR}},
{{RFC7009}}).

On success, the IdP MUST issue the governed grant that the request
would have produced without deferral, with the approved authority:

* the same Agent Principal, acting relationship, and, for delegated
  access, user;
* the same client registration at the RAS as `client_id`, target, and
  resource;
* `cnf.jkt` equal to the thumbprint of the request's proof key; and
* `iat` and `exp` set when the grant issues, so that the grant's
  redemption window begins at resolution, within the lifetime limits of
  {{FEDERATION}} ({{deferring}}).

The successful polling response carries the `issued_token_type` of the
originating request ({{Section 5.5.2 of DTR}}). No claim in the grant
indicates that an approval occurred. The IdP MAY include the `txn`
claim {{RFC8417}} with an identifier of the approval, for audit
correlation; a RAS or API MUST NOT treat `txn` as evidence of approval
or as authority.

A client whose pending request is denied or expires MUST NOT retry it
as self-acting access, under another client, or under a lower adoption
profile. A later request for the same authority is a new request, and
a new approval if policy requires one.

## Continuation {#deferred-continuation}

A continuation exchange ({{CONTINUATION}}) can be deferred under this
section, with the continuing client as the client. Before deferring, the
IdP performs every validation step of the continuation exchange,
including the Continuation Association and the limits of {{ICA}}, and
reserves the assertion as {{Section 5.5.7 of ICA}} requires. The
pending governed request holds that reservation:

* **Retention.** The IdP MUST retain the reservation until the later of
  the request's end and the time {{Section 5.5.7 of ICA}} requires.
* **States.** Where the IdP offers idempotent retry, this document
  replaces one transition of {{Section 5.5.7.1 of ICA}} for a deferred
  continuation: the reservation stays RESERVED while the request is
  pending, rather than becoming FAILED at the assertion's `exp` plus
  the permitted clock skew. It becomes ISSUED when the onward grant
  issues and FAILED when the request ends otherwise, on denial,
  cancellation, expiry, or a failed re-check.
* **Retries.** The IdP MUST reject a second presentation of the
  assertion, both while the request is pending and after it ends.
  Recovery ({{Section 5.5.7.1 of ICA}}) does not apply to an onward
  grant issued at resolution, which only the polling response delivers
  ({{Section 5.5.2 of DTR}}).

A continuation exchange performs no agent resolution, so at resolution
the IdP re-checks the chain and the continuing client's Continuation
Association rather than an Identity Binding ({{resolution}}). The
continuation window is evaluated when the request is received: it
bounds when a continuation can be requested, and the maximum pending
lifetime bounds how long after that the onward grant can issue. A chain
that ended while the request was pending resolves to `access_denied`;
the continuing client learns of the ending from its next continuation,
which fails with `invalid_continuation`. While the request is pending,
the continuing client reports the wait to its own caller through its
own interface, such as an MCP task ({{mcp}}).

The limits of {{Section 6.3 of ICA}} count continuations that have
issued, not requests, so passing them at deferral reserves no capacity.
At resolution, the IdP MUST evaluate them again against the
continuations issued by then, and MUST count the onward grant against
them atomically with issuing it, so that continuations pending together
cannot exceed a limit. A request that would exceed a limit resolves to
`access_denied`.

# Deferred Redemption {#deferred-redemption}

This section profiles {{DTR}} for the redemption of a governed grant at
the RAS: an ID-JAG or a WAG under "Grant Redemption at the RAS" in
{{FEDERATION}}, whether a root grant or an onward grant under
{{CONTINUATION}}. The RAS holds the redemption until an approver
decides, then issues what the redemption would have produced. This
section covers deferral for an approver's decision only; deferral for
another reason, such as a fraud review, is outside this document.

The approval is the RAS's own. It bounds only what the RAS issues, an
approval at the IdP does not satisfy it ({{modes}}), and it authorizes
nothing at another server ({{redemption-refresh}}). A pending governed
redemption moves through these steps, which the subsections define:

| Event | RAS action | Result |
|---|---|---|
| Redemption with the opt-in | Completes every check except the approver's decision, accepts the grant, and opens one approval request ({{redemption-deferring}}) | Pending; deferred response |
| The same redemption again | Matches the accepted grant ({{redemption-recovery}}) | The same deferral code |
| Poll before a decision | Verifies the client and its key | `authorization_pending` or `slow_down` |
| Approver decides | Records the decision for this pending redemption only ({{redemption-approval}}) | Pending until the next poll |
| Poll after approval | Re-checks the redemption with the approval ({{redemption-resolution}}) | Access token, and any refresh token |
| Poll after denial, or a re-check fails | Issues nothing | `access_denied` |
| Client revokes the deferral code ({{Section 7 of DTR}}) | Ends the pending redemption | `access_denied` |
| `expires_in` elapses | Issues nothing | `expired_token` |
{: title="Steps of a pending governed redemption"}

## Redemption Opt-In {#redemption-opt-in}

A client that can wait for an approver includes `deferred` in the
`completion_mode` parameter of its redemption request
({{Section 4.1 of DTR}}). It MUST present a DPoP proof {{RFC9449}} on
that request, whatever its client authentication method, as for
deferred issuance ({{opt-in}}). For a grant that contains `cnf.jkt`,
that proof is the grant proof.

The RAS MUST NOT return a deferred response to a redemption request
that does not include `deferred` or does not present a DPoP proof. It
MUST NOT defer a redemption for a resource whose configuration selects
mutual-TLS access tokens ("Access-Token Protection" in
{{FEDERATION}}): {{Section 10.1 of DTR}} requires the token issued
after a request with a DPoP proof to be bound to that proof's key, and
that configuration applies mutual TLS regardless of any DPoP proof.

When RAS policy requires approval and the RAS does not defer, it MUST
NOT issue a token. It rejects the redemption with the error it returns
when its own policy refuses a redemption ("Redemption Errors" in
{{FEDERATION}}): `actor_unauthorized` for an ID-JAG and
`invalid_target` for a WAG. The response therefore does not reveal
that an approval could be obtained. A client that can wait and handle a
deferred response can include `deferred` on every redemption that RAS
policy might hold, as at the IdP ({{opt-in}}). A RAS that defers redemptions
advertises `deferred_token_response_supported` in its own metadata
({{Section 4.1 of DTR}}); the IdP's metadata says nothing about the
RAS.

## Deferring a Redemption {#redemption-deferring}

Before returning a deferred response, the RAS MUST complete every check
that {{FEDERATION}} requires for the redemption except the approver's
decision:

* **Both grants:** the proof and client, replay, and authority checks
  of "Common Grant Validation" in {{FEDERATION}}, and the effective
  eligibility of the agent and, for an ID-JAG, the user, including any
  Local Suspension ({{AGENT-LIFECYCLE}}).
* **ID-JAG:** ID-JAG validation, including the grant's time claims; the
  actor; user resolution; correlation of the `act` agent; and the actor
  gate ("Grant Validation" in {{FEDERATION}}).
* **WAG:** validation of the grant, including its time claims and
  `typ`; correlation of (`iss`, `sub`) to one local agent principal; and
  RAS policy for the agent ("Self-Acting Redemption: WAG" in
  {{FEDERATION}}).

A redemption that fails a check is rejected as {{FEDERATION}} specifies
and is not deferred. The client does not present the grant again, so
its time claims are checked when the request is received; the grant's
`exp` limits redemption, not later access ("Authorization Lifetime" in
{{FEDERATION}}). This document thus reads the originating-grant
preconditions that {{Section 10.7 of DTR}} re-evaluates as excluding
the grant's own expiration ({{open-items}}).

The RAS then accepts the grant. It MUST record the grant's (`iss`,
`jti`) as accepted, whether or not the grant is bound, and MUST NOT
accept the grant again for another redemption. This narrows the
re-acceptance of a bound grant that "Common Grant Validation" in
{{FEDERATION}} permits and the parallel request of
{{Section 8.2 of DTR}}: one grant yields one outcome, and a denial
cannot be bypassed by presenting the grant again. The RAS retains the
record until the later of the pending redemption's end and the
retention of "Time, Replay, and Key Validation" in {{FEDERATION}}.

On acceptance, the RAS MUST set the absolute authorization expiration
of "Optional RAS Refresh Tokens" in {{FEDERATION}}, whether or not it
later issues a refresh token, and MUST NOT issue a token for the
redemption that outlives it. That section sets the expiration at
issuance. Without deferral the two coincide; with deferral, a later
start would extend reliance on one IdP decision by the pending time.
Where the RAS already set an absolute authorization expiration for the
grant, that expiration applies, and deferral does not extend it. If it
has passed, the RAS does not defer: access beyond it requires a new
grant, and the RAS rejects the redemption with `invalid_grant`.

The RAS records a pending governed redemption bound to the values that
the checks established:

* the authenticated client, the Target Tenant, the resource, and the
  requested authority, including any `authorization_details` as
  processed;
* the proof key and the absolute authorization expiration;
* for an ID-JAG, the resolved local user, the local agent principal for
  `act`, the validated `act` object, and, where the RAS participates in
  grant-derived revocation ({{AGENT-LIFECYCLE}}), the revocation key;
* for a WAG, the local agent principal correlated from (`iss`, `sub`);
  and
* the grant as received, or a digest of it ({{redemption-recovery}}).

The RAS MUST construct any authorization evaluation for the pending
governed redemption only from these values, keeping the user, the
agent, and the client distinct, as "Optional Policy Services" in
{{FEDERATION}} requires of an API. For an ID-JAG, the agent is the
issuer-qualified `act`; for a WAG, the agent is the subject. The client
identifier never identifies the agent.

The RAS returns the deferred response of {{Section 5.4 of DTR}}. It
MUST bind the deferral code to the authenticated client and the key of
the request's DPoP proof, and MUST reject a poll or cancellation that
does not prove that key ({{Section 10.1 of DTR}}). It MUST set
`expires_in` no greater than a configured maximum pending lifetime and
so that the pending governed redemption ends no later than the absolute
authorization expiration. An approval after that expiration therefore
finds an expired request.

## Approval Binding {#redemption-approval}

The rules of {{approval}} apply with the RAS in place of the IdP and
the values of {{redemption-deferring}} as the governed request context:
approvers designated by RAS policy and authenticated at the strength it
requires, never the client or an agent; the resolved values shown, with
requester text shown as the requester's; approval of the request as
shown or of narrower authority, never of a wider one; and time
conditions enforced only on what the RAS issues.

The RAS MUST bind each approval to one pending governed redemption:

* **One approval request.** The RAS opens one approval request for each
  pending governed redemption. It MUST NOT use one approval request for
  two pending governed redemptions, including by treating a redemption
  with the same client and requested authority as a duplicate of
  another.
* **Only its own approval.** The RAS MUST accept an approval only for
  the approval request it opened for that pending governed redemption,
  received over an authenticated channel or verified for integrity,
  issuer, intended recipient, expiry, and binding. An approval for
  another approval request completes nothing: the pending governed
  redemption remains pending until its own approval, denial, or expiry.
* **Kept unchanged.** The RAS MUST keep the approval as received,
  including its identifier, its time values, and any state that the
  approval channel attaches, or a reference that retrieves it exactly.
  It MUST use that approval unchanged in every later evaluation. A
  shorter deadline that a later evaluation returns is kept separately,
  as an enforcement deadline, and does not modify the approval.

The approval expiry is the latest time at which the approval channel
states the approval remains valid.

{{ARAP}} and {{AROP}} realize these rules. The approval request is an
ARAP access request, the approval is ARAP's `approval` object, which
ARAP carries unchanged into re-evaluation, the approval expiry is its
`approved_until`, and completion is AROP's token issuance completion.
AROP's idempotent submission compares the client and the requested
authority but not the agent or the user; {{redemption-recovery}}
replaces it.

## Recovery {#redemption-recovery}

A pending governed redemption is recoverable until a successful token
response redeems its deferral code ({{Section 5.5.2 of DTR}}), or until
it is denied, cancelled, or expires. The RAS cannot know whether a
token response reached the client; a later poll for a redeemed code
fails ({{Section 5.5.1 of DTR}}).

While a pending governed redemption is recoverable, the RAS MUST return
its deferral code, with the remaining `expires_in`, to a redemption
request that presents:

* the accepted grant, byte for byte, matched against the stored grant
  or its digest;
* authentication of the same client and a DPoP proof of the same key,
  each fresh under its own replay rules;
* `deferred` in `completion_mode`; and
* the same `resource`, `scope`, and `authorization_details`.

Recovery matches the stored grant and does not validate it again, so it
succeeds after the grant's `exp`. It is not an acceptance, opens no
approval request, and changes neither the maximum pending lifetime, the
absolute authorization expiration, nor the approval expiry. The RAS
MUST record an acceptance and its pending governed redemption
atomically, so that identical requests received together create one
pending governed redemption and one approval request. Recovery issues
no token, so it cannot yield a second token while a poll succeeds.

The RAS rejects any other presentation of an accepted grant under the
replay rule of {{redemption-deferring}}, with `invalid_grant`. This
includes a presentation without `deferred` and any presentation after
the pending governed redemption ends.

## Redemption Resolution {#redemption-resolution}

Only an approval accepted under {{redemption-approval}} starts
resolution; an approval for another approval request leaves the pending
governed redemption pending. Before issuing a token in response to a
poll, the RAS MUST re-evaluate the redemption under
{{Section 10.7 of DTR}}, with the approval kept under
{{redemption-approval}}, and MUST confirm that:

* neither the approval's expiry nor any enforcement deadline has
  passed;
* no applied disablement, correlation removal, local restriction, or
  Local Suspension affects the agent or, for an ID-JAG, the user
  ("Applied Disablement and Revocation" in {{FEDERATION}},
  {{AGENT-LIFECYCLE}});
* for an ID-JAG, the user is active and resolves to the same local
  user, the `act` agent correlates to the same local agent principal,
  and the actor gate permits the relationship. An account-link change
  does not substitute another user ("User Resolution and Linking" in
  {{FEDERATION}}), and a changed agent link does not transfer the
  delegation ("Agent Principal Correlation" in {{FEDERATION}});
* for a WAG, (`iss`, `sub`) correlates to the same local agent
  principal; and
* current RAS policy permits the approved authority for the client,
  Target Tenant, and resource.

If any check fails, the RAS returns `access_denied` and issues no
token, as {{Section 10.7 of DTR}} requires. A denial resolves to
`access_denied`, and a pending governed redemption that outlives
`expires_in` resolves to `expired_token` ({{Section 5.6 of DTR}}).
Grant-derived revocation of the grant reaches "all redemptions" of it
({{AGENT-LIFECYCLE}}), so a participating RAS ends the pending governed
redemption when the event arrives, and the next poll gets
`access_denied`. Other changes made at the IdP after receipt reach the
RAS only through such signals or provisioning. The maximum pending
lifetime bounds the rest, and an intervention bound ({{supervised}})
counts it.

On success, the RAS MUST issue what the redemption would have produced
without deferral, for the approved authority:

* the identities bound at receipt: for an ID-JAG, the local user as
  subject and `act` unchanged ("Actor Preservation" in
  {{FEDERATION}}); for a WAG, the local agent principal as subject and
  no `act`;
* an access token bound to the proof key ({{Section 10.1 of DTR}}),
  with `iat` set at resolution and an expiration no later than the
  approval expiry, any enforcement deadline, and the absolute
  authorization expiration; and
* the approved authority, which a narrower approval reduces; the
  response's `scope` reports it.

The successful polling response is the token response that the
redemption would have returned ({{Section 5.5.2 of DTR}}); the JWT
bearer grant defines no `issued_token_type`. The access token MAY carry
`txn` for audit
correlation, as a grant may ({{resolution}}); an API MUST NOT treat it
as evidence of approval or as authority.

## Refresh and Continuation {#redemption-refresh}

A WAG redemption yields no refresh token ("Self-Acting Redemption: WAG"
in {{FEDERATION}}), and an approval of a single use SHOULD NOT yield
one. Otherwise, a refresh token for a deferred redemption follows
"Optional RAS Refresh Tokens" in {{FEDERATION}}, with the absolute
authorization expiration set on acceptance ({{redemption-deferring}}).
The RAS MUST keep the approval with the refresh authorization. On every
refresh, in addition to that section's processing, the RAS MUST
evaluate the request again with the kept approval. It MUST reject the
refresh with `invalid_grant` if the approval has expired or was
revoked, cancelled, or superseded, if an enforcement deadline has
passed, or if the evaluation denies. A shorter deadline that an
evaluation returns becomes the enforcement deadline for every later
token and for the refresh authorization. An access token issued on
refresh expires no later than the approval expiry, any enforcement
deadline, and the absolute authorization expiration. When the RAS
rejects a refresh after authenticating the client and its proof, under
this paragraph or under "Optional RAS Refresh Tokens" in
{{FEDERATION}}, it MUST end the refresh authorization, so that a later
change in policy or approval does not revive it. A request that fails
client authentication or proof does not end it. Access after an ended
refresh authorization needs a new grant, since this one is consumed.

The RAS MUST NOT record an authorization from a deferred redemption as
eligible for continuation ("Root Redemption at the Gateway's RAS" in
{{CONTINUATION}}). This covers every access token issued for that
authorization, including on refresh, and the deferred redemption of an
onward grant as well as of a root grant. A CAI therefore refuses to
attest such a token, as for any ineligible hop. Under {{AROP}}, the
approval expiry also bounds tokens obtained by exchange. Continuation
exchanges the access token at the CAI and the resulting assertion at
the IdP, which issues an onward grant this document cannot bound
({{open-items}}).

# Supervised Issuance {#supervised}

Under supervised issuance, the IdP issues governed grants without
waiting, and a person can observe and end each one. An IdP claims
supervised issuance for a target only where both hold:

* **Each grant is visible.** For each grant it issues under a
  supervised policy, the IdP makes the grant's `iss` and `jti`, its
  governed request context, and its issuance time available to the
  overseers that policy designates, no later than it returns the grant.
  This document does not define the channel or its format.
* **Each grant can be ended.** At least one intervention with a defined
  effect reaches the target, with a documented intervention bound:
  * grant-derived revocation of an ID-JAG where the target participates
    ({{AGENT-LIFECYCLE}});
  * withdrawing or narrowing the Delegation or Agent Authorization,
    which stops new grants and ends or narrows continuation
    ({{CONTINUATION}});
  * a Local Suspension at the target; or
  * disabling the agent, once the target applies it.

Revoking one WAG is deployment-specific ({{AGENT-LIFECYCLE}}), so
supervised self-acting issuance rests on the other interventions.

The intervention bound includes tokens already accepted. An API that
validates access tokens without a check accepts them until they expire,
and no intervention reverses an operation already performed. A
deployment that cannot document an intervention bound for a target
does not claim supervised issuance for it.

# Per-Action Oversight {#per-action}

Resource policy can require a person to decide on an action, such as a
tool call, before it executes. The API holds the action, or refuses it
in a way that lets the agent request it, until an approver decides; the
API then executes it only after a new decision on the same action. This
oversight applies within the access token's authority:

* **The approval binds to the action.** It covers the operation, its
  target object, and its arguments, and the access token's subject,
  agent, client, and tenant. The agent is the validated `act` for a
  delegated token, and the subject for a token that trusted context
  establishes as self-acting ("Profile Applicability" in
  {{FEDERATION}}). A changed action needs a new decision.
* **Policy selects the mode.** A tool's declared hint, such as an MCP
  tool annotation, MUST NOT select or lower the mode that resource
  policy requires for an action ({{mcp}}).
* **The approver is a person.** Resource policy designates approvers as
  in {{approval}}, and the API MUST NOT accept a decision from the
  client, the agent, or another agent as an approval.
* **The approval does not add authority.** It satisfies an additional
  condition within the token's authority and cannot expand it
  ("External Approval" in {{FEDERATION}}). An action outside that
  authority needs a new governed grant, which the client requests by
  token exchange and the IdP can defer under {{deferred-issuance}}.
* **A confirmation is not an approval unless it is bound.** A
  confirmation the client shows in its own interface is not an approval
  under this document. It becomes one only where the API authenticates
  the person, binds the decision as above, and makes the decision
  itself, consistent with {{Section 10.7 of AIMS}}.

# Model Context Protocol {#mcp}

This section is informative. An MCP server is the enforcement point for
each tool call it serves. It realizes the modes as follows.

* **Holding a call.** A server that requires a person to decide on a
  call holds it as a task under the MCP tasks extension
  {{MCP-TASKS}}, which the client declares on the request, reporting
  `working` or `input_required` until the approver decides.
  {{MCP-SEP-2848}} proposes a
  standard extension in which a requestable denial returns a task that
  stays `working` while the approval resolves out of band, with an
  access request service under {{ARAP}} behind it.
* **Reaching the user.** URL-mode elicitation can take the user to an
  approval page while the user is present. {{MCP}} requires the server
  to bind the elicitation to the user identified by its authorization
  and states that the elicitation response does not authorize. Under
  this document, the decision is made on the approval page by an
  authenticated approver and feeds the server's decision
  ({{per-action}}). A self-acting token has no user to elicit from.
* **Asking for more authority.** A call outside the token's authority
  can be refused with an `insufficient_scope` challenge. The client then
  requests a new governed grant by token exchange, which the IdP can
  defer ({{deferred-issuance}}). {{MCP-SEP-2643}} proposes structured
  denials that can describe this remediation.
* **Tool annotations.** {{MCP}} defines tool annotations, such as
  `destructiveHint`, as hints that clients treat as untrusted unless the
  server is trusted. They do not select or lower a mode
  ({{modes}}); a deployment can use its own classification of tools to
  require a stricter one.
* **Client confirmations.** {{MCP}} recommends that a person be able to
  deny tool calls and sampling requests in the client. Such a
  confirmation is client behavior, not an approval under this document
  ({{per-action}}).

# Conformance {#conformance}

Each claim below is optional and names the role that makes it:

| Role | Claim | Requirements |
|---|---|---|
| IdP | Deferred governed issuance | {{deferred-issuance}}, except {{deferred-continuation}} |
| IdP | Deferred continuation | {{deferred-continuation}}, with an IdP continuation claim under {{CONTINUATION}} |
| IdP | Supervised issuance, per target | {{supervised}} |
| RAS | Deferred redemption | {{deferred-redemption}} |
| Client | Deferred governed issuance | {{opt-in}}; polling with the same key under {{DTR}}; the no-retry rule of {{resolution}} |
| Client | Deferred redemption | {{redemption-opt-in}}; polling with the same key under {{DTR}}; recovery only as {{redemption-recovery}} defines |
| API | Per-action oversight | {{per-action}} |
{: title="Conformance claims"}

A claim of deferred governed issuance or deferred redemption requires
the polling mode of
{{DTR}}; callback notification ({{Section 6 of DTR}}) is optional. Each
claim requires the realization of {{FEDERATION}} it applies to.

# Security Considerations {#security}

## Approval Fatigue {#security-fatigue}

An approver asked too often approves without reading. Policy that
places routine requests under human in the loop trains approvers to
approve. Deployments can reserve approval for requests whose authority
warrants it, grant routine authority as standing authorization that a
person reviews periodically, and limit how many pending requests one
agent can hold. Converting an approval into standing authority is an
authorization change ({{modes}}), not a side effect of approving.

## Misleading Requests {#security-misleading}

An agent can phrase a request to mislead an approver. The governed
request context comes from the IdP's resolution, not from the request,
and the requester's own text is shown as the requester's
({{approval}}). An approver can still be misled about why the authority
is needed; this document makes the request accurate, not the reason.

## Self-Approval {#security-self}

An agent that could approve its own requests would remove the person the
mode requires. An approver is a person designated by policy, and neither
the requesting agent, its client, nor another agent can approve
({{approval}}, {{per-action}}). How an IdP or API tells a person's
decision from an automated one depends on the approval channel, which
this document does not define; the channel's authentication of the
approver is what makes the rule enforceable. A deployment that routes
decisions to an automated approver is human out of the loop and records
it as such ({{modes}}).

## Stale Approvals {#security-stale}

A decision can come long after the request. The IdP re-checks the agent,
its bindings and associations, its authorization, the user, and the
chain at resolution ({{resolution}}), and the grant's lifetime starts
then. The maximum pending lifetime, and for root issuance the
expiration of the credentials the request presented ({{deferring}}),
bound how old a request can be when it is approved. At the RAS, the
re-checks of {{redemption-resolution}} and an absolute authorization
expiration set when the grant is accepted ({{redemption-deferring}})
do the same.

## Deferral Codes {#security-codes}

A stolen deferral code could otherwise yield the grant after approval.
The code is bound to the client and to a DPoP key ({{deferring}},
{{redemption-deferring}}), as
{{Section 10.1 of DTR}} requires for clients whose profile mandates
DPoP, and the grant carries the same key.

## Approval Binding at the RAS {#security-binding}

An approval matched to a request by its attributes can complete another
agent's request. {{ARAP}}'s comparison excludes the actor, and
{{AROP}}'s idempotent submission compares only the client and the
requested authority. The RAS opens one approval request for each pending
governed redemption and accepts only that request's approval
({{redemption-approval}}), so no comparison decides which redemption an
approval completes.

## Recovery {#security-recovery}

Recovery returns a deferral code only to the client that authenticates
afresh and proves the deferral's key, for the grant it presented
({{redemption-recovery}}). A party that holds the grant but not the key
gets `invalid_grant`, as for any consumed grant. Recovery cannot
extend a pending governed redemption or the authority that follows it.

## Downgrade {#security-downgrade}

A client that omits the opt-in, or retries a denied request another way,
must not obtain the grant without the approval policy requires. Policy
selects the mode, a request without the opt-in is refused rather than
issued ({{opt-in}}, {{redemption-opt-in}}), and a denied or expired
request is not retried as
self-acting access, under another client, or under a lower profile
({{resolution}}).

## Supervised Exposure {#security-exposure}

Under supervised issuance, an agent acts before anyone reviews the
grant. What it does before an overseer intervenes, and before the
intervention takes effect, cannot be undone. The intervention bound
({{supervised}}) states that window; it does not shorten it.

# Privacy Considerations {#privacy}

An approver sees the agent, the user, the client, the target, and the
requested authority, and an overseer sees the same for each grant. The
approval channel and overseer notices therefore carry personal data and
reveal patterns of an agent's work for a user. Deployments limit what
approvers and overseers can see to the requests they are designated
for, and follow {{Section 8.3 of DTR}}: progress information in a
polling response carries no personal data.

# IANA Considerations {#iana}

This document has no IANA actions.

--- back

# Walkthrough: Approval Before Issuance {#walkthrough}

This non-normative walkthrough extends the dedicated-client walkthrough
of {{FEDERATION}}. Policy lets `agent-42` read files in `acme-data` for
Alice without approval, and requires Alice's approval before it writes
them. The client asks for `files.write`.

## Deferred Request {#walkthrough-request}

The client sends the token exchange request of the {{FEDERATION}}
walkthrough with `scope=files.write`, `completion_mode=deferred`, and a
DPoP proof of key K. The IdP authenticates `analysis-client`, resolves
`agent-42`, checks the Client Association and Alice's Delegation
Authorization, and finds that policy requires Alice's approval for
`files.write`. Alice's ID Token expires in 65 minutes, so a one-hour
pending lifetime leaves a grant issued at any point in it its full
300-second lifetime. The IdP records the pending governed request and
responds:

~~~ http-message
HTTP/1.1 400 Bad Request
Content-Type: application/json
Cache-Control: no-store

{
  "error": "authorization_pending",
  "deferral_code": "DEFERRAL_CODE",
  "expires_in": 3600,
  "interval": 5
}
~~~

## Approval {#walkthrough-approval}

Alice receives an approval request on her authenticator, sent by CIBA
with this binding message:

~~~
agent-42 (client analysis-client) asks to write files in acme-data
~~~

She authenticates and approves.

## Resolution {#walkthrough-resolution}

The client polls, authenticating as in the {{FEDERATION}} walkthrough
and proving K:

~~~ http-message
POST /token HTTP/1.1
Host: idp.example
Content-Type: application/x-www-form-urlencoded
DPoP: IDP_DPOP_PROOF

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adeferred
&deferral_code=DEFERRAL_CODE
&client_id=analysis-client
&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth
%3Aclient-assertion-type%3Ajwt-bearer
&client_assertion=CLIENT_ASSERTION_2
~~~

The IdP re-checks that `agent-42` is active, its binding and
association still permit the request, Alice's Delegation Authorization
still permits `files.write`, and Alice is active. It issues the ID-JAG
the request would have produced, with `scope` `files.write`, `sub`
`alice-ras`, `act` naming `agent-42`, `client_id` `analysis-api`,
`cnf.jkt` for K, and `iat` at resolution. The response carries
`issued_token_type` `urn:ietf:params:oauth:token-type:id-jag`. The
client redeems it at the RAS as in the {{FEDERATION}} walkthrough.

## Negative Tests {#negative-tests}

Each case changes the walkthrough as stated; all other checks succeed.

| Changed condition | Checked by | Required result |
|---|---|---|
| The request omits `completion_mode=deferred` | IdP | HTTP 400, `actor_unauthorized`; no grant and no deferred response |
| The poll proves a key other than K | IdP | HTTP 400, `invalid_dpop_proof` |
| `agent-42` is disabled while the request is pending, and Alice then approves | IdP | HTTP 400, `access_denied` at the next poll; no grant |
| The request asks for `files.read files.write`, and Alice approves only `files.read` | IdP | A grant with `scope` `files.read` |
| Alice denies | IdP | HTTP 400, `access_denied` at the next poll; no grant |
| The client polls again after receiving the grant | IdP | HTTP 400, `invalid_grant` |
| A continuation ({{CONTINUATION}}) is deferred for Alice's approval; the request is received before the source hop's continuation deadline, and Alice approves after it | IdP | The onward grant issues at the next poll; the deadline applies when the request is received ({{deferred-continuation}}) |
| A continuation requests a target or authority outside the restrictions of its chain authorization | IdP | HTTP 400, `invalid_target`, `invalid_scope`, or `invalid_authorization_details` as {{CONTINUATION}} specifies, when the request is received; no deferral and no approval |
| A continuation is within every restriction when received and is deferred; while it is pending, Alice's Delegation Authorization or the Continuation Association is narrowed to exclude its target | IdP | HTTP 400, `access_denied` at the next poll; no grant. The narrowing comes from current authorization, since the chain authorization's restrictions are fixed |
{: title="Negative test cases"}

## Deferred Redemption {#walkthrough-redemption}

In this variant, the IdP issues the ID-JAG of the {{FEDERATION}}
walkthrough without approval, and RAS policy for `acme-data` requires
the tenant's data steward to approve each agent redemption for
`files.read`. The client redeems the grant as in the {{FEDERATION}}
walkthrough, adds `completion_mode=deferred`, and proves the key in the
grant's `cnf.jkt`.

The RAS completes the checks of "Grant Validation" in {{FEDERATION}}:
it resolves `alice-ras` to `user-108`, correlates `agent-42`, and finds
that the actor gate permits it. It accepts the grant, sets the absolute
authorization expiration eight hours ahead, records the pending
governed redemption, opens one approval request, and returns the
deferred response with `expires_in` 3600. The steward approves through
the RAS's access request service, with an approval expiry two hours
ahead.

The client polls the RAS as it polled the IdP
({{walkthrough-resolution}}), proving the same key. The RAS re-checks
`agent-42`, `user-108`, the actor gate, and the approval, and issues
the access token of the {{FEDERATION}} walkthrough: `sub` `user-108`,
`act` naming `agent-42`, `cnf.jkt` for the key, and an expiration
within the approval expiry. The RAS does not record the authorization
as eligible for continuation.

Each case changes this variant as stated; all other checks succeed.

| Changed condition | Checked by | Required result |
|---|---|---|
| The redemption omits `completion_mode=deferred` | RAS | HTTP 400, `actor_unauthorized`; no token and no deferred response |
| The resource is configured for mutual-TLS access tokens | RAS | HTTP 400, `actor_unauthorized`; no deferral |
| A poll proves another key | RAS | HTTP 400, `invalid_dpop_proof` |
| The grant's `exp` passes while the redemption is pending, and the steward then approves | RAS | The access token issues at the next poll |
| The maximum pending lifetime is 24 hours, and the steward approves nine hours after receipt | RAS | `expires_in` was at most eight hours; HTTP 400, `expired_token`; no token |
| Local Suspension of `agent-42` while the redemption is pending, and the steward then approves | RAS | HTTP 400, `access_denied` at the next poll; no token |
| While the redemption is pending, `agent-42`'s correlation changes to another local agent principal, and the steward then approves | RAS | HTTP 400, `access_denied` at the next poll; no token |
| Grant-derived revocation of the ID-JAG arrives while the redemption is pending, at a participating RAS | RAS | HTTP 400, `access_denied` at the next poll |
| The steward denies, and the client presents the grant again | RAS | HTTP 400, `access_denied`; then `invalid_grant` |
| While the redemption is pending, the client presents the grant without `completion_mode` | RAS | HTTP 400, `invalid_grant` |
| After the grant's `exp`, the client repeats the redemption with the same grant, key, opt-in, and parameters | RAS | The same deferral code, with the remaining `expires_in` |
| The repeated redemption reuses the DPoP proof of the first | RAS | HTTP 400, `invalid_dpop_proof` |
| After a successful token response, the client repeats the redemption | RAS | HTTP 400, `invalid_grant` |
| Two identical redemptions arrive together | RAS | One pending governed redemption and one approval request; both responses carry its deferral code |
| While the redemption is pending, `agent-43` redeems its own ID-JAG through the same client, for the same user, resource, and scope | RAS | A separate pending governed redemption and approval request; approving the first issues nothing for it |
| The access request service returns the first redemption's approval for the second's approval request | RAS | The second stays pending (`authorization_pending`); no token |
| The approval expires in one hour, a refresh token issues, and the client refreshes after the approval expiry | RAS | The access token expires within the approval expiry; HTTP 400, `invalid_grant` on refresh |
| The approval is revoked ten minutes into its hour, and the client then refreshes | RAS | HTTP 400, `invalid_grant` |
| The grant had no `cnf` and the client's minimum was governed agent access; after a refresh token issues, the minimum becomes bound governed agent access, and the client refreshes | RAS | HTTP 400, `invalid_grant` ("Optional RAS Refresh Tokens" in {{FEDERATION}}) |
| A refresh is rejected because the actor gate no longer permits `agent-42`; the gate is restored, and the client refreshes again with the same refresh token | RAS | HTTP 400, `invalid_grant`; the rejection ended the refresh authorization |
| A deferred WAG redemption is approved | RAS | An access token with the local agent principal as `sub`, no `act`, and no refresh token |
| The gateway exchanges at the CAI an access token from a deferred redemption, or one refreshed from it | CAI | HTTP 400, `invalid_request`; the authorization is not eligible for continuation |
{: title="Deferred redemption negative test cases"}

# Relationship to Other Specifications {#relationships}

| Specification | Relationship |
|---|---|
| {{DTR}} | Profiled for governed token exchange and governed grant redemption. Narrowed: DPoP on every deferred request; all governed checks before deferring and again at resolution; the token keeps the request's agent, user, client, and key. At the RAS: a deferred grant is accepted once, the absolute authorization expiration starts on acceptance, and no deferral where mutual-TLS access tokens are configured |
| {{AROP}} | Token issuance completion profiled at the RAS ({{deferred-redemption}}): the approval expiry bounds what the RAS issues, every refresh is evaluated again with the approval, recovery replaces idempotent submission, and the authorization is not eligible for continuation. Not profiled at the IdP, where `approved_until` would bound tokens the RAS issues ({{open-items}}) |
| {{ARAP}} | One way to route an approval; at the RAS, its `approval` object is the approval kept unchanged ({{redemption-approval}}) |
| {{ICA}} | A deferred continuation holds the assertion's replay reservation while pending, replacing one transition of {{Section 5.5.7.1 of ICA}}, and counts the limits of {{Section 6.3 of ICA}} when the onward grant issues ({{deferred-continuation}}) |
| {{CIBA}} | One way to reach a user for a decision; not profiled |
| {{MCP}} | Informative realization of per-action oversight ({{mcp}}) |
| {{MISSION-APPROVAL}} | Approves a task, where this document approves a governed request. A Mission approval can be the basis of standing authorization under which requests are human out of the loop |
| {{AIMS}} | Nearest counterpart for confirmation bound to an authorization grant ({{Section 10.7 of AIMS}}); here the IdP issues the grant after the decision |
| {{OVERSIGHT-ACTS}} | Vocabulary for the kinds of human act ({{modes}}) |
{: title="Relationship to other specifications"}

# Open Items {#open-items}

1. **AROP at the IdP, and continuation from a deferred redemption.**
   At the IdP, {{AROP}}'s `approved_until` would bound tokens the RAS
   issues, a downstream condition the composition cannot enforce
   ("Issuance Authorization" in {{FEDERATION}}). From a deferred
   redemption, continuation exchanges the access token at the CAI and
   the resulting assertion at the IdP, and {{AROP}} does not say
   whether an onward grant that the IdP authorizes on its own derives
   from the approval. Both need {{AROP}} to state that the approval
   expiry bounds what the deferring server issues. Continuation also
   needs a rule for how that expiry meets the continuation window.
2. **Administering the mode.** No attribute records the oversight mode
   on a Delegation or Agent Authorization in the SCIM management
   profile.
3. **Overseer notices.** Whether a Shared Signals event should carry
   supervised-issuance notices.
4. **Duplicate pending requests at the IdP.** Whether the IdP should
   return the existing pending request when the same governed request
   context is requested again while one is pending. At the RAS,
   recovery settles this ({{redemption-recovery}}).
5. **Originating-grant preconditions.** Whether the preconditions of
   the originating grant that {{Section 10.7 of DTR}} re-evaluates
   include the grant's own expiration when the client does not present
   the grant again. {{redemption-deferring}} reads them as checked on
   receipt.

# Document History
{:numbered="false"}

RFC Editor: Remove this section before publication.

* Initial version.

# Acknowledgments
{:numbered="false"}

TBD.
