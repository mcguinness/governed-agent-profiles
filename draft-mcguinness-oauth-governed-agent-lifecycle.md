---
title: "Governed Agent Lifecycle Profile for SCIM and OAuth"
abbrev: "Governed Agent Lifecycle"
category: std
docname: draft-mcguinness-oauth-governed-agent-lifecycle-latest
submissiontype: IETF
stand_alone: yes
ipr: trust200902
area: "Security"
workgroup: "System for Cross-domain Identity Management"
keyword:
 - OAuth
 - agent provisioning
 - SCIM
 - lifecycle
 - shared signals
venue:
  group: "System for Cross-domain Identity Management"
  type: "Working Group"
  mail: "scim@ietf.org"
  arch: "https://mailarchive.ietf.org/arch/browse/scim/"
  github: "mcguinness/governed-agent-profiles"
  latest: "https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html"
author:
 - fullname: Karl McGuinness
   organization: Independent
   email: public@karlmcguinness.com
normative:
  CAEP:
    title: "OpenID Continuous Access Evaluation Profile 1.0"
    target: https://openid.net/specs/openid-caep-1_0-final.html
    author:
      - org: OpenID Foundation
    date: 2025-08-29
  SSF:
    title: "OpenID Shared Signals Framework Specification 1.0"
    target: https://openid.net/specs/openid-sharedsignals-framework-1_0-final.html
    author:
      - org: OpenID Foundation
    date: 2025-08-29
  RFC8417:
  RFC9493:
  RFC9967:
  RFC8935:
  RFC8936:
  ID-JAG: I-D.ietf-oauth-identity-assertion-authz-grant
  FEDERATION:
    title: "OAuth 2.0 Profile for Governed Agent Federation"
    author:
      - name: Karl McGuinness
    date: 2026-09-18
    seriesinfo:
      Internet-Draft: draft-mcguinness-oauth-governed-agent-federation
  SCIM-AGENT: I-D.wzdk-scim-agent-resource
  OAUTH-CLIENT:
    title: "SCIM Profile for OAuth 2.0 Client Management"
    author:
      - name: Karl McGuinness
    date: 2026-09-18
    seriesinfo:
      Internet-Draft: draft-mcguinness-scim-oauth-client-management
    target: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-oauth-client-management.html
  RFC7643:
  RFC7644:
  RFC7662:
informative:
  AGENT-MANAGEMENT:
    title: "SCIM Profile for Agent Federation Management"
    author:
      - name: Karl McGuinness
    date: 2026-09-18
    seriesinfo:
      Internet-Draft: draft-mcguinness-scim-agent-federation
    target: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-agent-federation.html
  RFC7009:
  WISE:
    title: "Workload Identity Security Events (WISE) Profile"
    target: https://github.com/identitymonk/openid-wise/blob/main/openid-wise-profile-1_0.md
    author:
      - org: WISE Contributors
  WAG: I-D.carleton-workload-authz-grant
--- abstract

This document profiles SCIM for provisioning issuer-qualified Agent
Principals into a resource domain and applying administrative disablement
to OAuth authorization. Existing SCIM Events can accelerate reconciliation;
existing session-revocation events can invalidate identified authorization
sessions independently of principal state.

The profile defines identity correlation, receiver actions, and the
limits of propagation and resource enforcement. It defines no new SCIM
schema, event type, eligibility lease, or authorization timestamp.
Current administrative state does not establish a history of revocation.

--- middle

# Introduction

Governed Agent Federation {{FEDERATION}} separates agent identity,
client authority, user delegation, and resource authorization. It
identifies an Agent Principal by the pair (IdP issuer, agent
identifier), independently of the client or workload credential used to
resolve it.

For delegated access, the Identity Assertion JWT Authorization Grant
(ID-JAG) {{ID-JAG}} carries that principal as the actor. The resource
domain correlates the actor with its local agent record.

This companion defines how a resource domain provisions that principal
and applies changes to its administrative status. The responsibilities
are:

| Mechanism | Responsibility |
|---|---|
| SCIM Agent {{SCIM-AGENT}} | Provision and update the local representation, including `active` |
| SCIM Events {{RFC9967}} | Notify the receiver that authoritative provisioning state changed |
| Session revocation | Invalidate identified authorization sessions without changing the principal's administrative status |
| OAuth enforcement | Apply local eligibility and revocation at issuance, refresh, introspection, and API access |

~~~
 Enterprise IdP / connector                  Resource domain
 +------------------------+                 +----------------------+
 | Agent Principal        | ---- SCIM ---->  | Local agent principal|
 | Administrative state   |                  | Correlation + active |
 +------------------------+                 +-----------+----------+
       |                                                |
       +---- change notice --> reconciliation           v
                                             RAS issuance / refresh
       +---- session revocation ------------> session invalidation
                                                        |
                                                        v
                                            API token enforcement
~~~
{: #lifecycle-model title="Administrative state and authorization revocation"}

SCIM is the provisioning baseline. Shared Signals is an optional
addition, profiled in {{signals}} using existing event types. A
deployment can use direct SCIM updates, event-driven reconciliation, or
both, provided that they apply the same authoritative administrative
decisions. Events trigger retrieval of current state rather than
carrying it: a late notice resolves to the current decision, whereas a
late activation applied as an instruction would revive a principal that
was since disabled. That asymmetry is the design's safety property.

Disabling a principal and revoking a session are separate actions. Once
applied, disablement prevents new authorization and invalidates existing
RAS authorization for that principal. Re-enablement permits new
decisions; it does not restore revoked sessions. Neither an event
acknowledgment nor a SCIM response proves that every API has stopped
accepting issued tokens.

## Scope

This profile covers IdP-to-resource-domain provisioning for delegated
Federation. It does not define:

* Platform enrollment or administration of Identity Bindings and Client
  Associations; {{AGENT-MANAGEMENT}} defines that separate interface.
* A new lifecycle state machine, signed eligibility lease, authorization
  cutoff, or distributed ordering protocol.
* Automatic translation of binding or delegation withdrawal into all
  affected grants, or a WAG wire profile. A known ID-JAG can be revoked
  selectively under {{grant-revocation}}.
* A guarantee that an unobserved disable-and-reenable cycle invalidates
  all previously issued grants or sessions.

{{recovery}} and {{enforcement}} state the recovery and enforcement
limits. Deployments requiring stronger revocation-history guarantees need
an additional composition; timestamps in ordinary resource metadata do
not provide those guarantees.

# Conventions and Terminology

{::boilerplate bcp14-tagged-bcp14}

Agent Principal, Governance Tenant, Target Tenant, and resource
authorization server (RAS) follow {{FEDERATION}}. SCIM terms follow
{{RFC7643}} and {{RFC7644}}.

Governing IdP:
: The IdP governing the Agent Principal. An authorized connector can
  provision its decisions into the resource domain.

Receiver:
: The resource-domain SCIM service provider and the components applying
  accepted changes at the RAS. They form one administrative deployment;
  they need not run in one process. It is the resource-domain
  counterpart of the IdP Service Provider in {{AGENT-MANAGEMENT}}.

Provisioning Domain:
: Trusted configuration identifying one governing IdP issuer and one
  receiving Target Tenant, together with the connectors authorized to
  manage their correlation and administrative state. This is the
  resource-domain counterpart of the IdP-side Provisioning Domain.

Authorization Session:
: RAS state retaining the identity and authority derived from a grant,
  including any associated refresh authorization and access tokens. This
  is a processing concept, not a new token or wire identifier.

Local Suspension:
: A resource-domain restriction independent of the Governing IdP's
  administrative state. Upstream activation cannot clear it.

# Conformance and Configuration {#conformance}

Conformance requires the SCIM provisioning and OAuth receiver behavior in
this document. Events are optional; a deployment using them MUST apply
{{signals}}. Support for events alone is not conformance to this
lifecycle profile.

Before provisioning, the parties MUST establish:

* The Provisioning Domain and authenticated connectors authorized for it.
* The SCIM base URI and access controls that select that context.
* The RAS and API token populations to which lifecycle enforcement applies.
* Reconciliation responsibilities, stale-state policy, and resource
  enforcement settings under {{recovery}} and {{enforcement}}.

A connector authorized for one context MUST NOT modify another context's
principal or correlation. Multiple writers MAY represent the same
Governing IdP, but MUST reconcile against its current decisions rather
than replay queued activation writes after newer disablement. SCIM
conditional updates protect receiver resource versions; they do not
order independent source decisions.

The IdP continues to enforce current eligibility when issuing grants under
{{FEDERATION}}. This profile adds resource-domain application of that
state; it does not make SCIM availability or event delivery part of client
authentication.

The Governing IdP, directly or through its connector, MUST apply each
change to a provisioned Agent Principal's administrative status to every
resource domain it has provisioned for that principal, by a SCIM write
or by a subscribed event that triggers reconciliation, and SHOULD do so
promptly after the decision. Where grant-derived revocation under
{{grant-revocation}} is enabled, the IdP MUST retain the identifiers of
the ID-JAGs it issued under each delegation, Identity Binding, and Client
Association, so that withdrawing any of them can be propagated to the
authorization derived from those grants.

# Identity and Local Correlation {#identity}

The federation identity remains the exact pair (IdP issuer, Agent
Principal identifier). A Target Tenant scopes local policy and
correlation; it is not an additional component of that identity.

For this provisioning interface:

* The governing issuer MUST come from the authenticated Provisioning
  Domain, not from a caller-selected attribute.
* The connector MUST set the Agent's `externalId` to the exact Agent
  Principal identifier in that issuer's namespace.
* The Receiver MUST enforce uniqueness of `externalId` within that
  context, including concurrent creates. This is an explicit narrowing
  of SCIM's client-scoped `externalId` behavior.
* Once established, the pair MUST NOT change through a resource update.
  Attempts to change `externalId` use SCIM's `mutability` error.

Thus, `externalId` alone is not a globally qualified identity. A
deployment with multiple IdPs MUST retain the context with each
resource; it cannot merge records on equal `externalId` values across
issuers. This use of `externalId` is specific to the IdP-to-resource
interface. A platform's `externalId` at the IdP remains its own
provisioning correlation value.
The mutability differs for the same reason: at the platform-to-IdP
interface of {{AGENT-MANAGEMENT}} it is the connector's record key and
stays readWrite; here it carries the principal identifier and is
immutable once established.

When the source uses {{AGENT-MANAGEMENT}}, the connector maps the
interfaces as follows; it does not copy the source Agent unchanged:

| IdP-side source | Resource-domain use |
|---|---|
| Configured governing issuer | Issuer established by the authenticated Provisioning Domain |
| `AgentFederation.subject` | Exact value of the destination Agent's `externalId` |
| Agent `active` | Upstream administrative state; local restrictions remain independent |
| Agent `id` | Source-resource correlation, not the destination SCIM `id` |
| Platform-assigned `externalId` | Platform correlation only; not the federated principal identifier |

This mapping applies equally to direct provisioning and event-driven
reconciliation. It introduces no additional destination attributes.

For delegated access, the RAS MUST resolve the validated ID-JAG's
`act.iss` and `act.sub` to this pair within the authorized Target
Tenant. It MUST NOT use the user subject, OAuth client, display name, or
token issuer as a substitute. Comparisons are exact, without case
folding or URI rewriting.

The Receiver MUST correlate the pair with at most one local agent
principal in the Target Tenant. An existing service principal MAY supply
that local representation, but attaching it requires explicit local
authorization. The SCIM Agent is then a management view of that same
principal, not a second authorization identity.

This profile raises Federation's provisioning recommendation to a
requirement: the RAS MUST have the authorized local correlation before
accepting a grant involving the agent. A missing or ambiguous
correlation fails under Federation's identity-resolution error rules.
{{jit}} defines the one optional way to establish that correlation
without a prior SCIM write.

## Just-in-Time Correlation {#jit}

A Receiver MAY be configured to establish the local correlation from a
validated ID-JAG instead of a prior SCIM write. This option is disabled
by default and enabled per governing issuer and Target Tenant.

When enabled, on a validated grant whose `act.iss` is that issuer and
whose `act.sub` has no correlation in that tenant, the RAS MAY create
the local agent principal and its correlation keyed by the pair, with an
initial local `active` state set by local policy. The RAS MUST NOT
attach the pair to an existing principal by name or other descriptive
match, MUST apply Local Suspension, retained revocation state, and local
policy before issuance, and MUST subject the created principal to the
same provisioning, reconciliation, and disablement rules as a
provisioned one. A grant does not carry the IdP's administrative
status; just-in-time correlation therefore does not replace SCIM
provisioning for disablement, and a later SCIM write for the same pair
updates the created record rather than creating a second principal.

# SCIM Provisioning {#scim}

The interface uses `/Agents` and the attributes of {{SCIM-AGENT}},
including required `agentUserName`, plus the common attributes of
{{RFC7643}}. It defines no extension schema. Receivers MUST support
creation, retrieval, filtering by `externalId`, PUT, PATCH, and deletion using
{{RFC7644}}. The Receiver MUST advertise filtering, PATCH, and ETag
support in `/ServiceProviderConfig`. Connectors for `/Agents` are
purpose-built for this resource; User/Group support alone is insufficient.

## Creation and Updates

Creation and PUT requests MUST contain `externalId` and an explicit
boolean `active`; PATCH removal of either is invalid. Only `active:
true` permits authorization evaluation. Missing required values use
`invalidValue`; conflicting correlation values use `uniqueness`,
following SCIM's error model.

Within the authenticated Provisioning Domain, a connector can reconcile
using:

~~~ http
GET /scim/v2/Agents?filter=externalId%20eq%20%22agent-42%22
~~~

The Receiver MUST restrict the result to that context. Names, owners,
groups, and other descriptive attributes do not select the governed
identity or grant delegation.

Versions, ETags, `If-Match`, the conditional requirement for activating
an inactive resource, and incremental reads on `meta.lastModified`
follow the common provisioning conventions of {{OAUTH-CLIENT}}. In this
interface, `meta.version` is not a lifecycle counter and
`meta.lastModified` is not a source decision time or a grant-revocation
boundary; a descriptive edit can change both without affecting
authorization.

## Applying Administrative State {#application}

The Receiver MUST authorize changes to `active` separately from
permission to edit descriptive attributes. It MUST preserve Local
Suspension and resource permissions independently of upstream
administrative updates.

| Applied action | New RAS authorization | Existing RAS authorization |
|---|---|---|
| Create or set `active: true` | Evaluate correlation, local status, and all Federation checks | Does not restore previously revoked sessions |
| Set `active: false` | Deny grant redemption and refresh involving this principal | Revoke associated authorization sessions |
| Delete the local Agent | Deny because the authorized correlation is absent | Revoke associated authorization sessions |
| Change display name, owner, or other descriptive data | No implicit change to eligibility or delegation | No implicit revocation or grant of authority |

The durable restriction rule of {{OAUTH-CLIENT}} applies to disablement
and deletion with the RAS decision point as the decision point; an
inactive record or a separate deny marker can provide that state. If
session invalidation is asynchronous, a local restriction MUST deny use
of the affected sessions until invalidation completes. API observation
of revocation follows {{enforcement}}.

Reactivation MUST NOT cancel pending invalidation or restore revoked
sessions. Recreating a deleted representation likewise does not restore
revoked authorization. Receivers MUST retain revocation state for as
long as affected tokens or refresh authorizations could otherwise be
accepted. This does not require retaining the deleted SCIM resource.

Deleting a local representation does not prove that the IdP retired the
Agent Principal globally. Permanent retirement and non-reassignment
remain authority responsibilities under {{FEDERATION}}.

## Effective Eligibility

The SCIM `active` value reports administrative state received through
this interface. Effective eligibility also requires an authorized
correlation, no Local Suspension, and applicable resource policy. Local
Suspension need not be exposed through this SCIM interface.

Owners provide accountability; they are not automatically user
delegators. Group membership has only the meaning assigned by local
policy. Neither provisioning nor a successful administrative write opens
the actor gate.

# Signals and Reconciliation {#recovery}

SCIM events trigger authoritative reconciliation; CAEP events revoke
identified authorization. {{signals}} defines their optional
composition. Neither event delivery nor current SCIM state supplies a
complete history.

For event-driven reconciliation, the parties MUST configure the source
SCIM service, retrieval authorization, and mapping from its resource
identifier to the qualified agent and Target Tenant. The source and
receiver SCIM `id` values need not match. A GET of the receiver's own
replica does not establish the governing IdP's current state.

Direct SCIM connectors and event-driven workers MUST coordinate local
writes through the same correlation and conditional-update rules. A
reconciliation worker reads the receiver's ETag before retrieving source
state, then uses that ETag for its conditional write. After a conflict,
it retrieves both again. This prevents an in-flight fetch from
overwriting a later local restriction; it does not create a cross-domain
transaction or establish that a remote source replica is current.

Deployments SHOULD periodically reconcile managed principals even when
an event stream appears operational. They MUST document how source
outages and incomplete reconciliation affect continued reliance on local
state. A deployment claiming a maximum stale-state interval needs an
authoritative revalidation mechanism and a policy that denies new
authorization and refresh when that interval expires. Receiving traffic
or reading the Receiver's replica alone does not satisfy such a
revalidation policy.

Transport failure, access denial, and partial list results MUST NOT be
interpreted as authoritative deletion. They leave reconciliation
incomplete. An authoritative absence for a previously mapped resource
requires disablement or deletion of its local representation; the
Receiver MUST distinguish that absence from a visibility or
authorization failure.

A stream verification event proves neither an individual agent's status
nor completion of resource enforcement. A delivery acknowledgment
confirms acceptance under the transport, not API denial.

## Missed Transitions and Reactivation {#missed-transitions}

Current state does not establish transition history. If disablement and
reactivation both occur between successful observations, a later active
resource does not reveal the missed revocation. A different ETag can
also result from an ordinary descriptive edit; it does not identify that
history.

Consequently, this profile does not guarantee rejection after
reactivation of an old unredeemed ID-JAG or an authorization session
whose revocation was never observed. Grant validation, replay
prevention, and expiration still apply. Sessions actually revoked by the
RAS remain revoked.

Deployments requiring revocation to survive every missed transition need
retained revocation history, an authoritative authorization check, or a
separately specified authorization-generation mechanism. That mechanism
is a deferred composition rather than a prohibition: it would carry an
authenticated authorization generation in the grant, agreed with ID-JAG,
and define the comparison the RAS applies. SCIM modification times, SET
issuance times, and event timestamps MUST NOT be treated as
interchangeable grant-issuance cutoffs under this profile.

# OAuth Enforcement {#enforcement}

The RAS requirements that apply administrative state to authorization
are specified in {{FEDERATION}}: checking current locally applied
eligibility at redemption and refresh, retaining the association needed
to invalidate authorization by qualified agent and Target Tenant, not
letting refresh bypass a restriction or restore revoked authorization,
and reporting revoked or disabled authorization as inactive under
{{RFC7662}}. This document supplies the provisioning and signals that
feed those decisions and adds no grant issuance-time claim or timestamp
comparison. The optional capability in {{grant-revocation}} additionally
retains the ID-JAG issuer and `jti`. Once reactivated, the principal may
establish new authorization under ordinary Federation processing,
subject to {{missed-transitions}}. Existing tokens whose agent
correlation cannot be established MUST NOT be represented as covered by
this profile.

## Resource Enforcement and Delay {#api-enforcement}

The API applies Federation's token validation, actor gate, tenant, and
sender-constraint rules. The following are deployment choices, not new
conformance levels:

| Resource processing | When an applied RAS revocation becomes visible |
|---|---|
| Introspection on each request | On the next successful authorization check; a failed or timed-out check cannot authorize the request |
| Cached introspection | After any permitted active-response cache entry expires or is invalidated |
| Offline JWT validation | At token expiration, unless an independent local restriction takes effect earlier |

Caching follows Federation and {{Section 4 of RFC7662}}. In particular,
cached active responses cannot outlive token expiration or the
configured freshness limit. Offline validation does not consult
principal lifecycle state by itself. The RAS and API MUST configure
token lifetimes, expiry leeway, and caching consistently with their
accepted revocation delay.

Deployments SHOULD document their expected and maximum disablement
delays, including propagation, reconciliation, local application, token
lifetime, and caching. A SCIM acknowledgment is not the starting point
of an end-to-end guarantee from the governing IdP's original decision.
Without a bound on propagation and enforcement, this profile claims no
finite end-to-end denial bound. A local stale-state restriction can
limit new issuance; it does not by itself revoke already-issued tokens.

# Relationship Boundaries {#relationship-changes}

| Change | Boundary |
|---|---|
| Disable an Identity Binding | Stop new grants through that binding; other bindings remain independent |
| Withdraw a Client Association | Stop that client use; do not infer agent-wide disablement |
| Revoke a user's delegation | Affect that delegation, not unrelated users or self-acting authority |
| Revoke a workload credential | Apply credential validation and IdP policy; do not automatically retire the Agent Principal |
| Revoke a known ID-JAG | Invalidate its derived sessions; do not change principal eligibility |

{{FEDERATION}} defines the first three authorization relationships.
Grant-derived revocation under {{grant-revocation}} can target known
ID-JAGs. Determining all grants affected by withdrawal of a binding or
delegation remains an IdP responsibility; the agent identity alone
cannot identify that set. OAuth token revocation {{RFC7009}} can revoke a known token at its
issuing server but is not a principal-provisioning or cross-domain
notification protocol.

{{WISE}} can inform the IdP about workloads and credentials. The IdP evaluates those changes against its Identity Bindings before deciding on
agent-wide action. Sharing a credential source does not merge principals;
losing one credential does not necessarily disable a principal with other
valid bindings.

## Self-Acting Access

The self-acting WAG realization in {{FEDERATION}} correlates the same
Agent Principal with the same local principal. Delegated access preserves the qualified
actor in `act`; self-acting access represents the correlated agent as a
local subject. Their authority remains distinct. This document defines
no {{WAG}} wire composition or additional WAG claim.

# Security Considerations

Provisioning writers can enable principals and change eligibility. Their
authority MUST remain scoped to the configured issuer and Target Tenant.
An event signature, matching display name, or equal `externalId` outside
that context does not establish permission to correlate a principal.

Conditional writes prevent stale updates to a known receiver version;
they do not prove that a connector consulted current source state.
Compromised or stale connectors can re-enable principals if their write
permission remains valid. Administrative authorization, reconciliation,
and local suspension therefore remain separate controls.

Event trust, provisioning permission, and session-revocation authority
remain separate. Receivers MUST constrain source retrieval and
credential forwarding to authorized endpoints. A signed subject does not
authorize arbitrary URL retrieval or cross-tenant revocation.

Event loss and reordering can delay enforcement. Receivers SHOULD retry
reconciliation, monitor failures, and retain revoked-session state across
restarts. Recovery from lost revocation state MUST NOT silently restore
sessions represented as revoked. The explicit limit in
{{missed-transitions}} is particularly relevant to unattended refresh.

A disabled principal may still have tokens accepted by an offline API.
Token expiry and cached responses MUST be included in operational
claims; stopping issuance alone does not terminate ongoing work or
retract operations already performed.

# Privacy Considerations

The qualified identity permits correlation across users and resources.
Provisioning and event access SHOULD be limited to the receiving domains
that need it. Logs SHOULD retain administrative actions and affected
identities without copying reusable grants, access tokens, or
credentials.

# IANA Considerations

This document requests no IANA actions.

--- back

# Optional Shared Signals Profile {#signals}

This appendix profiles existing SCIM Events {{RFC9967}} and CAEP
session-revocation events {{CAEP}} over Shared Signals {{SSF}}. It is
normative for deployments that enable either capability and defines no
new event type or subject format. SCIM event reconciliation
and CAEP revocation are independently optional capabilities. A deployment
MAY use either or both; it MUST apply the requirements for each enabled
capability. Direct SCIM provisioning with CAEP revocation does not
require SCIM event subscription or source-resource retrieval.

## Trust and Delivery {#signal-trust}

Trusted stream configuration MUST establish:

* The Transmitter, receiving Target Tenant, and audience.
* For SCIM event reconciliation, the source SCIM service, retrieval
  authority, and source-resource correlation under {{recovery}}.
* For grant-derived revocation, the governing ID-JAG issuer whose grants
  the Transmitter may revoke, and agreement to apply {{grant-revocation}}.
* For coarse user-and-tenant revocation, the authorized user namespace
  and revocation scope defined in {{grant-revocation}}.

The SET issuer can differ from the IdP issuer. Their trust relationship
comes from configuration; a subject identifier or matching host name
cannot establish it.

The authenticated delivery context selects the stream. SET issuer and
audience validation, including audience arrays, follows {{SSF}} and
{{RFC8417}}. SSF uses `secevent+jwt` and does not use SET `exp`.
Push delivery follows {{RFC8935}}; poll delivery follows {{RFC8936}}.
The selected transport defines acknowledgment, duplicate handling, and
errors. Neither transport is mandatory here. Acceptance acknowledges
delivery, not completed reconciliation or API enforcement.

## SCIM Reconciliation Triggers {#scim-events}

Receivers MUST accept every provisioning and feed event defined in
Sections 2.3 and 2.4 of {{RFC9967}} as a reconciliation trigger when
subscribed to that event type. SCIM event capability is exposed through
`securityEvents.eventUris` in `/ServiceProviderConfig` under
{{Section 4 of RFC9967}}. SSF stream configuration uses
`events_supported`, `events_requested`, and `events_delivered` to
establish event delivery. These lists do not authorize a provisioning action
or establishes the grant-revocation composition. This profile adds no
discovery field. The table uses suffixes under
`urn:ietf:params:scim:event:`.

| Event suffix | Reconciliation behavior |
|---|---|
| `prov:create:notice`, `prov:patch:notice`, `prov:put:notice` | Retrieve current authoritative state |
| `prov:create:full`, `prov:patch:full`, `prov:put:full` | Retrieve current state; the included snapshot does not override it |
| `prov:activate`, `prov:deactivate`, `prov:delete` | Reconcile current state or authoritative absence |
| `feed:add`, `feed:remove` | Reconcile the resource and feed coverage; removal from a feed does not establish deletion or disablement |

Transmitters MUST report administrative changes for resources covered by
an agreed stream using an appropriate subscribed event. Event payloads
retain their base meanings. The top-level `sub_id` uses the RFC 9967
`scim` format and resource `uri`. When present, `version` is the source
ETag, not an ordered counter or the Receiver's ETag.

After validating the event and authority for its subject, the Receiver
MUST:

1. Resolve the source service and resource URI to an authorized correlation
   or provisioning workflow in the configured Target Tenant.
2. Retrieve current source state and reconcile under {{recovery}}. Source
   URI resolution MUST remain within the configured service; it cannot
   redirect retrieval credentials to a caller-selected endpoint.
3. Retain failed reconciliation as pending and retry or resolve it
   administratively. Acknowledgment MUST NOT discard pending work.

An authenticated `prov:deactivate` or `prov:delete` MAY cause a
provisional Local Suspension pending reconciliation. An activation event
MUST NOT activate the principal directly. This asymmetry is deliberate:
provisional denial can contain risk; granting access requires current
authoritative state and local authorization. Successful reconciliation
can clear that provisional restriction under local policy, but not an
independent Local Suspension. Feed removal and inaccessible sources
follow the incomplete reconciliation rules; they are not deletion
instructions.

## Grant-Derived Session Revocation {#grant-revocation}

The optional capability uses CAEP's existing event type
`https://schemas.openid.net/secevent/caep/event-type/session-revoked`.
CAEP permits session properties to identify affected sessions; here the
property is the ID-JAG that established their authorization. This
composition additionally requires denial before redemption and rejection
of later redemption. Ordinary CAEP support or advertisement of the
event URI alone does not establish these receiver semantics.

* The Transmitter MUST use the `jwt_id` subject format from
  Section 3.5.1 of {{SSF}}, with `iss` and `jti` equal to the issued
  ID-JAG's corresponding claims. It MUST name a grant it is authorized
  to revoke. The SET's own `jti` identifies the event, not the grant.
* The Receiver MUST verify that the subject's `iss` matches the
  governing ID-JAG issuer authorized in the stream configuration. That
  configuration supplies the Target Tenant. The revocation key is
  (ID-JAG issuer, ID-JAG `jti`, Target Tenant); it MUST NOT be matched as
  a bare RAS session identifier or used outside that tenant.
* On redemption, a participating RAS MUST retain that key with every
  derived authorization session, access token, and refresh authorization.
  The Receiver MUST invalidate all authorization derived from that grant
  in the tenant, including all redemptions, and reject later redemption
  of the revoked grant.
* A valid event received before redemption MUST retain a denial for that
  grant. The Receiver retains it until neither the grant nor derived
  authorization can be accepted. For an unknown grant, this requires a
  configured maximum grant acceptance window, including clock leeway;
  receipt before redemption MUST NOT be treated as a no-op.

This identifies the same grant at both parties without registration of a
RAS-generated session ID. Parties MUST NOT enable this composition
unless the RAS retains the required correlation and enforces the grant
denial. Existing sessions need trustworthy backfilled correlation or
remain outside its coverage.

A deployment MAY additionally configure CAEP's complex subject with
`user` in `iss_sub` format and `tenant` in `opaque` format under
{{RFC9493}} to revoke existing sessions for that user and tenant. The
parties MUST agree on
the user namespace and map it authoritatively to the RAS user, and the
tenant MUST match the stream's Target Tenant. All supplied subject
conditions MUST match; an unmappable component MUST NOT broaden the
revocation. This coarse mode is distinct from grant-derived revocation
and does not revoke future grants or unrelated users' sessions.

Neither mode changes Agent `active`. Revoked authorization remains
revoked after activation. CAEP `event_timestamp`, `initiating_entity`,
and localized reasons retain their meanings; event time is not a cutoff
against grant `iat`. No new claims are introduced.

## Unit of Revocation

| Action | Affected authorization | Principal state |
|---|---|---|
| Apply Agent disablement or deletion | Every RAS session for the qualified agent in the Target Tenant | Inactive or absent |
| Revoke an ID-JAG by issuer-qualified `jti` | All authorization derived from that grant, plus later redemption of it | Unchanged |
| Configured CAEP user-and-tenant revocation | Existing sessions matching that user and tenant | Unchanged |

None establishes a shorter API enforcement delay than
{{api-enforcement}}.

# Shared Delegated Federation Walkthrough {#example}

This non-normative walkthrough uses the dedicated-client exchange in
{{FEDERATION}}. It is a specification walkthrough, not an executed
implementation test.

## Correlate and Provision

The authenticated provisioning context binds `https://idp.example/` to
Target Tenant `acme-data`. The RAS resource is
`https://api.example/tenants/acme-data/`. The connector creates this
Agent:

~~~ json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Agent"],
  "externalId": "agent-42",
  "agentUserName": "analysis-agent",
  "displayName": "Data analysis agent",
  "active": false
}
~~~

The RAS assigns SCIM `id` `local-108` to the management representation
of local principal `service-principal-42` and correlates the context's
`(https://idp.example/, agent-42)` with that principal. The SCIM `id`
is not the principal identifier.
Alice is separately represented as `user-108`; the client is
`analysis-api`. Neither is the agent's correlation identifier.

## Activate and Exchange

The connector reads the resource and receives ETag `W/"a1"`. At 12:01
UTC on September 17, 2026, it applies:

~~~ http
PATCH /scim/v2/Agents/local-108 HTTP/1.1
Host: ras.example
Authorization: Bearer CONNECTOR_ACCESS_TOKEN
Content-Type: application/scim+json
If-Match: W/"a1"

{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [{"op": "replace", "path": "active", "value": true}]
}
~~~

The placeholder connector token is not a test credential. The Receiver
returns a new ETag. At 12:01:03, the IdP issues ID-JAG `grant-7` for
Alice with `act.iss` `https://idp.example/` and `act.sub` `agent-42`. No
lifecycle timestamp is added to the grant or compared with its `iat`.

At redemption, the RAS correlates that pair in `acme-data`, checks local
eligibility and Federation policy, and issues an access token. This
example uses introspection. A policy-permitted refresh retains the same
user, agent, client, tenant, resource, and authority constraints.

## Disable and Re-enable

At 12:02, an authorized connector sets `active: false` using the current
ETag. Before returning success, the Receiver blocks new RAS
authorization and makes existing sessions unusable at the RAS.
Subsequent introspection reports those tokens inactive. An API using a
previously cached response can continue to accept it only within its
configured cache policy.

Alternatively, a SCIM change notice can trigger an authoritative GET and
the same local update. {{signal-examples}} shows that notice and a CAEP
revocation targeting one ID-JAG; revocation need not disable the
principal.

At 12:03, reactivation permits new authorization decisions. It does not
restore the sessions revoked at 12:02. If the Receiver missed the entire
disable-and-reenable cycle, a later active GET alone cannot establish
that those sessions were revoked. An old unredeemed grant is likewise
subject to normal grant validation, not a new lifecycle cutoff.

## Acceptance Checklist {#acceptance-checklist}

| Case | Expected result |
|---|---|
| Equal `externalId` under a different IdP context | Distinct qualified identity; no automatic correlation |
| Stale `If-Match` | HTTP 412; retrieve and reconcile before retrying |
| Descriptive edit | Resource ETag may change; no implicit authorization change |
| Applied disablement | New redemption and refresh denied; existing RAS sessions revoked |
| Reactivation after applied disablement | New decisions allowed; revoked sessions stay revoked |
| Delayed activation notice | Retrieve current source state; do not apply the notice as an activation command |
| Entire disable-and-reenable cycle missed | Current active state cannot recover revocation history |
| Grant revocation arrives before redemption | Retain the denial; reject later redemption |
| Grant subject issuer differs from the stream's authorized issuer | Reject; no cross-issuer revocation |
| Direct SCIM provisioning with CAEP revocation only | No SCIM event subscription or source GET required |
| Reactivation without a version ETag, including `If-Match: *` | HTTP 409; retrieve and use the current ETag |
| Feed removal event | Reconcile coverage; do not infer deletion |
| Source unavailable | No activation inferred; local stale-state policy applies |
| SCIM success or SET acknowledgment | Does not establish immediate API denial |
| Offline JWT | May remain usable until expiration unless separately restricted |

# Signal Examples {#signal-examples}

These decoded SETs omit signatures. Their protected type is
`secevent+jwt`. Trusted configuration binds the stream to governing
issuer `https://idp.example/` and Target Tenant `acme-data`; the
Transmitter issuer is separately authorized for that namespace.

## Provisioning Change Notice

The trusted source SCIM service has resource `/Agents/source-42`. Its
configured correlation is `(https://idp.example/, agent-42)`,
represented at the RAS by `/Agents/local-108`. At 12:02 UTC on September
17, 2026, the source changes the principal's `active` value to false:

~~~ json
{
  "iss": "https://signals.idp.example",
  "aud": ["https://ras.example/signals/acme-data"],
  "iat": 1789646520,
  "jti": "change-42",
  "sub_id": {
    "format": "scim",
    "uri": "/Agents/source-42"
  },
  "events": {
    "urn:ietf:params:scim:event:prov:patch:notice": {
      "version": "W/\"source-b7\"",
      "attributes": ["active"]
    }
  }
}
~~~

The Receiver retrieves the source Agent, observes `active: false`, and
applies disablement under {{application}}. The notice itself contains no
boolean state, authorization cutoff, or lease. If delivered after a
later change, retrieval obtains current state instead.

## Revoke Authorization Derived from an ID-JAG

Separately, an authorized Transmitter can report revocation of the
ID-JAG `grant-7` issued in {{example}} while the principal remains
active:

~~~ json
{
 "iss": "https://signals.idp.example",
 "aud": [
  "https://ras.example/signals/acme-data"
 ],
 "iat": 1789646520,
 "jti": "revoke-grant-7",
 "sub_id": {
  "format": "jwt_id",
  "iss": "https://idp.example/",
  "jti": "grant-7"
 },
 "events": {
"https://schemas.openid.net/secevent/caep/event-type/session-revoked"
  : {
   "event_timestamp": 1789646520,
   "initiating_entity": "admin",
   "reason_admin": {
    "en": "Grant authorization revoked."
   }
  }
 }
}
~~~

No principal-state update is implied. Revocation covers every session
derived from `grant-7`, not another grant's sessions or every session
involving the same agent.

# Document History

RFC Editor: Remove this section before publication.

* Initial version.

# Acknowledgments
{:numbered="false"}

TBD.
