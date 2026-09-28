---
title: "OAuth 2.0 Profile for Governed Agent Federation"
abbrev: "Governed Agent Federation"
category: std
docname: draft-mcguinness-oauth-governed-agent-federation-latest
submissiontype: IETF
stand_alone: yes
ipr: trust200902
area: "Security"
workgroup: "Web Authorization Protocol"
keyword:
 - OAuth
 - agent federation
 - workload identity
 - agent registry
 - token exchange
venue:
  group: "Web Authorization Protocol"
  type: "Working Group"
  mail: "oauth@ietf.org"
  arch: "https://mailarchive.ietf.org/arch/browse/oauth/"
  github: "mcguinness/governed-agent-profiles"
  latest: "https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html"
author:
 - fullname: Karl McGuinness
   organization: Independent
   email: public@karlmcguinness.com
normative:
  SPIFFE-OAUTH: I-D.ietf-oauth-spiffe-client-auth
  WIT: I-D.ietf-wimse-workload-creds
  ATTEST: I-D.ietf-oauth-attestation-based-client-auth
  INSTANCE: I-D.mcguinness-oauth-client-instance-id
  ATTESTER-ENDORSEMENT: I-D.mcguinness-oauth-client-attesters
  ACTOR-PROFILE: I-D.mcguinness-oauth-actor-profile
  ID-JAG: I-D.ietf-oauth-identity-assertion-authz-grant
  RFC7523bis: I-D.ietf-oauth-rfc7523bis
  CIMD: I-D.ietf-oauth-client-id-metadata-document
  OPENID:
    title: "OpenID Connect Core 1.0 incorporating errata set 2"
    target: https://openid.net/specs/openid-connect-core-1_0.html
    author:
      - org: OpenID Foundation
    date: 2023-12-15
  RFC6749:
  RFC6750:
  RFC6901:
  RFC7517:
  RFC7519:
  RFC7523:
  RFC7662:
  RFC8414:
  RFC8693:
  RFC8705:
  RFC8707:
  RFC8725:
  RFC9068:
  RFC9396:
  RFC9449:
  RFC9700:
informative:
  AGENT-MANAGEMENT:
    title: "SCIM Profile for Governed Agent Federation Management"
    author:
      - name: Karl McGuinness
    date: 2026-09-18
    seriesinfo:
      Internet-Draft: draft-mcguinness-scim-agent-federation
    target: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-agent-federation.html
  AIMS: I-D.ietf-wimse-aims
  AGENT-LIFECYCLE:
    title: "Governed Agent Lifecycle Profile for SCIM and OAuth"
    target: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html
    author:
      - name: Karl McGuinness
    seriesinfo:
      Internet-Draft: draft-mcguinness-oauth-governed-agent-lifecycle
  EMA:
    title: "Enterprise-Managed Authorization"
    target: https://github.com/modelcontextprotocol/ext-auth/blob/main/specification/stable/enterprise-managed-authorization.mdx
    author:
      - org: Model Context Protocol
  AUTHZEN:
    title: "Authorization API 1.0"
    target: https://openid.net/specs/authorization-api-1_0.html
    author:
      - org: OpenID Foundation
  AROP:
    title: "AuthZEN Access Request OAuth Profile - Draft 1"
    target: https://github.com/openid/authzen/blob/main/profiles/authzen-access-request-oauth/authzen-access-request-oauth-profile-1_0.md
    author:
      - name: Karl McGuinness
  AWS-TOKEN-CLAIMS:
    title: "Understanding token claims"
    target: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_outbound_token_claims.html
    author:
      - org: Amazon Web Services
  AWS-AGENTCORE-OBO:
    title: "On-behalf-of token exchange with AgentCore Identity"
    target: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-behalf-of-token-exchange.html
    author:
      - org: Amazon Web Services
  ICA: I-D.mcguinness-oauth-id-continuation-assertion
  RFC6755:
  WAG: I-D.carleton-workload-authz-grant
  SPIFFE-CONCEPTS:
    title: "SPIFFE Concepts"
    target: https://spiffe.io/docs/latest/spiffe-about/spiffe-concepts/
    author:
      - org: SPIFFE
  ENTITY-PROFILES: I-D.mora-oauth-entity-profiles
  SCIM-AGENT: I-D.wzdk-scim-agent-resource
  RFC7643:
  RFC7644:
--- abstract

Service providers need a stable identity for an enterprise-governed agent
without understanding the runtime, workload credential, or OAuth client
through which it executes. Enterprises govern such agents independently
of those platforms, workloads, and clients.

This document is an OAuth deployment profile that standardizes the
boundary between execution identity and governed identity. An
enterprise identity provider resolves an authenticated OAuth client or
workload identity to a governed Agent Principal, whose identifier can be
the same as the execution identity's or different, and conveys that
principal to a resource domain. Identity resolution, client authority,
user delegation, and resource authorization remain separate decisions.
No new credential format is defined.

Two peer realizations carry the Agent Principal: delegated access
through the Identity Assertion JWT Authorization Grant (ID-JAG), with
the user as subject and the agent as actor, and self-acting access
through the Workload Authorization Grant (WAG), with the agent as
subject.

--- middle

# Introduction

Enterprises run agents on platforms they do not operate. Each platform
issues its own identity for the workload it runs, and that identity is
not the principal the enterprise governs. A platform integration
commonly uses one shared OAuth client, so the resource server cannot
tell the agents behind that client apart. Individual actions cannot be
attributed, and authorization cannot be withdrawn from one agent without
withdrawing it from all of them.

What an enterprise needs instead is a principal it can authorize once,
audit across resources, and disable everywhere. That principal's
identity does not change when the agent moves between platforms or
rotates credentials. This profile establishes the identity and
authorization relationships that disablement acts on; how far and how
fast disablement propagates depends on the lifecycle mechanism a
deployment selects, such as {{AGENT-LIFECYCLE}}.

Enterprise identity already solves a version of this problem for people.
A person has one account, several credentials linked to it, and separate
rules about which applications may use that account. This document
applies that shape to agents:

* The Agent Principal is the account.
* An Identity Binding maps a validated, qualified client or workload
  identity to it.
* A Client Association states which OAuth client may exercise that
  binding.

The account's identifier can be the same as the execution identity's.
The binding decides which identity is authoritative for governance.

Existing OAuth mechanisms authenticate clients and carry actors, but
they leave three relationships open:

1. How different client and workload identities resolve to the same
   governed principal. {{ATTEST}} and {{SPIFFE-OAUTH}} authenticate
   OAuth clients, not the agents a shared client serves.
2. How authority to use that principal is separated from identity
   resolution. The Identity Assertion JWT Authorization Grant (ID-JAG)
   leaves two things to extensions ({{Section 9.7 of ID-JAG}}):
   validating and authorizing an actor, and relating client, subject,
   and actor.
3. How the resulting principal is represented and correlated across
   authorization domains. {{RFC8693}} defines the `act` claim. It does
   not define how that claim names an actor authenticated through a
   client or workload credential, or how a resource domain correlates
   that name with local state.

This document is an OAuth deployment profile that fills those gaps. An
identity provider (IdP) resolves an authenticated client or workload
identity to an Agent Principal, and OAuth grants carry that principal
into the resource domain. A service provider can then authorize, audit,
and disable a stable, enterprise-governed agent without understanding
the runtime or credential that currently executes it.

The profile sits within the broader framework for agent identity
management that AIMS {{AIMS}} describes. It is not a governance
framework: it defines how the identities in one transaction relate
across authorization domains.

The federation model ({{model}}) is independent of the grant that
carries it. Two peer realizations carry it, each with its own mandatory
path, and an implementation claims one or both ({{scope}}):

* **Delegated access ({{delegated-flow}}):** ID-JAG, with the user as
  subject and the Agent Principal as actor.
* **Self-acting access ({{wag-flow}}):** the Workload Authorization
  Grant (WAG), with the Agent Principal as subject.

Other grant realizations require their own composition rules. The
federation model alone does not define their wire behavior. RFC 7523
client assertions, SPIFFE JWT Verifiable Identity Documents (JWT-SVIDs),
and the other supported credentials supply inputs to the same identity
model ({{evidence}}, {{optional-input-profiles}}).

This document federates an agent governed by the IdP that issues the
grant into a resource domain. It does not define identity continuity
across a chain of IdPs or brokers. Forwarding an actor from another
IdP's namespace is out of scope. Also out of scope ({{upstream-gaps}}):

* task or mission authorization;
* asynchronous approval;
* continuation composition;
* provisioning protocols and account administration;
* multi-agent delegation chains;
* instance-level authorization and cross-domain propagation of
  instance context; and
* enrollment or key-replacement protocols.

This document is organized by protocol stage. {{model}} and
{{conformance-metadata}} apply to every role. {{issuance}},
{{redemption}}, and {{api-processing}} give the processing of the IdP,
the resource authorization server (RAS), and the API (resource server),
each covering delegated and self-acting access, and
{{continuing-access}} covers renewal, token reuse, and disablement, and
{{implementation}} collects non-normative configuration and deployment
guidance.
{{scope}} states what each role implements. Client requirements
accompany the requests and responses at each stage.

# Conventions and Terminology

{::boilerplate bcp14-tagged-bcp14}

OAuth and Token Exchange terms follow {{RFC6749}} and {{RFC8693}}.
Client Attestation terminology follows {{ATTEST}}. Actor Profile refers
to {{ACTOR-PROFILE}}.

## Roles

Agent Platform (the platform):
: The environment that runs agents. It supplies verifiable workload
  evidence from its own or an approved external credential authority and
  can implement the OAuth client that obtains access for an agent.

Client:
: Software making OAuth requests for an agent. It authenticates as an
  OAuth client and presents the evidence, target, and proofs for the
  selected grant flow.

Identity Provider (IdP):
: The OAuth authorization server that resolves validated inputs to an
  Agent Principal, checks the permitted client and acting relationship,
  and issues a grant naming that agent as subject or actor.

Resource Authorization Server (RAS):
: The OAuth authorization server that validates the grant, resolves its
  identities, applies local policy, and issues an access token for its
  resources.

API (resource server):
: The OAuth resource server that accepts the access token and enforces
  the acting relationship and proof binding it carries.

One service can implement several roles.

Two companion profiles complete the family:

* {{AGENT-MANAGEMENT}} establishes the relationships at the IdP, and
  this document exercises them to obtain authorization.
* {{AGENT-LIFECYCLE}} carries the principal's administrative state into
  the resource domain and revokes what depends on it.

The companion profiles add two administrative roles:

Provisioning Client:
: A platform connector that manages Agent Principals and their
  relationships at the IdP. The IdP's System for Cross-domain Identity
  Management (SCIM) service is the IdP Service Provider.

Receiver:
: The resource-domain SCIM service together with the RAS components that
  accept IdP provisioning.

In the companion SCIM profiles, "Service Provider" alone denotes the
IdP-side SCIM service. The Service Provider Contract ({{sp-contract}})
concerns the resource domain.

## Terms {#terms}

Agent Principal:
: A stable, non-human authorization principal in the IdP's namespace
  representing an independently governed workload or agent. It is
  independent of the external credentials, execution environments, and
  OAuth clients used to obtain authorization for it
  ({{governance-boundary}}).

Workload:
: An external computational principal identified by accepted workload
  evidence. It can span multiple running instances; its identity does
  not necessarily distinguish executions.

Dedicated client:
: An OAuth client whose authenticated identity maps explicitly to one
  Agent Principal in the IdP's client-registration context. Dedicated
  refers to identity resolution, not to one process, replica, or
  installation.

Shared client:
: An OAuth client serving multiple Agent Principals. Its authenticated
  client identity alone cannot distinguish those agents; resolution
  requires independently validated workload identity.

Identity Binding:
: An approved association from an exact client or workload identity,
  qualified by its registration context or credential authority, to one
  Agent Principal. The Agent Principal can have the same identifier as
  that identity. An Identity Binding is administered in a Governance
  Tenant and establishes identity resolution, not permission to exercise
  the agent.

Client Association:
: An approved permission for an authenticated OAuth client to use an
  Agent Principal through the selected Identity Binding, acting
  relationship, and credential class ({{identity-binding}}).

Credential class:
: A configured category of agent-resolution input with mutually
  exclusive validation rules. Examples are an RFC 7523 client assertion,
  a SPIFFE Verifiable Identity Document (SVID), Client Attestation, and
  a platform issuer's workload JWT profile. JWT encoding alone does not
  identify the class.

Acting relationship:
: Whether the Agent Principal acts as the subject of a grant
  (self-acting) or as the actor for a user (delegated).

Delegation Authorization:
: The IdP's decision that an Agent Principal may act for a user within
  an approved client, tenant, target, and authority context.

Agent Authorization:
: The self-acting counterpart of Delegation Authorization: the IdP's
  decision that an Agent Principal may access a target on its own behalf
  within an approved client, tenant, target, and authority context.

Agent Principal Correlation:
: The RAS's authoritative association of an IdP-qualified Agent
  Principal with a local principal.

Issuer-bound presenter key:
: A key the credential issuer has attested belongs to the workload, such
  as a Client Attestation's confirmation key. It shows that the
  credential authority authorized the key.

Request proof key:
: A key the presenter proves in the request without issuer attestation,
  as with Demonstrating Proof of Possession (DPoP) {{RFC9449}}
  accompanying bearer evidence. It shows possession alone
  ({{credential-requirements}}).

Grant proof key:
: The DPoP key proven when requesting an ID-JAG or WAG and bound into
  that grant for redemption ({{credential-requirements}}).

Governance Tenant:
: The IdP's administrative scope within which an Agent Principal and its
  relationships are managed. It is not part of the Agent Principal's
  identity, which the IdP issuer qualifies ({{canonical-identity}}).

Target Tenant:
: The tenant at the RAS in which the agent or user is authorized, that
  is, where authority is exercised. It can differ from the Governance
  Tenant, as in {{identity-example}}.

Where the meaning is clear, this document uses agent as shorthand for
Agent Principal.

# Federation Model {#model}

The IdP controls Identity Bindings, Client Associations, and Agent and
Delegation Authorization. The RAS controls local principal correlation
and authorization ({{agent-correlation}}).

The relationships compose into one model; the grant that carries the
result depends on the acting relationship:

~~~
 Client authentication or workload evidence
                      |
               Identity Binding .......... which agent?
                      v
       Agent Principal (IdP namespace)
                      |
              Client Association ........ may this client use it?
                      |
          +-----------+------------+
          |                        |
 Delegation Authorization    Agent Authorization
   agent acts for user         agent acts for itself
          |                        |
 ID-JAG: sub = user          WAG: sub = agent
         act = agent               |
          |                        |
          +-----------+------------+
                      |
                      v
 RAS: validate grant; correlate agent with local principal
                      |
                      v
 RAS and API: resource authorization; actor gate if delegated
~~~

One Agent Principal can carry several Identity Bindings and several
Client Associations ({{identity-binding}}).

Establishing one relationship MUST NOT be treated as establishing
another.

## Service Provider Contract {#sp-contract}

The mapping from execution identity to Agent Principal is local to the
IdP. The security contract across the boundary between the IdP and the
resource domain is interoperable. The RAS does not resolve the agent
from the execution credential; the grant carries the resolved Agent
Principal instead. The RAS performs no platform-specific credential
validation or workload resolution and need not know which input the
agent authenticated with. From a validated grant it receives:

* the Agent Principal, qualified by its governing issuer: `act.iss` and
  `act.sub` in an ID-JAG ({{actor-construction}}), or `iss` and `sub` in
  a WAG;
* the acting relationship: delegated, with the user as subject, or
  self-acting;
* the client's registration at the RAS, in `client_id`; and
* the authority the IdP approved, as a ceiling for the RAS decision.

The RAS correlates the Agent Principal with a local principal, which can
be an existing service principal. Correlation does not replace the
IdP-qualified identity ({{agent-correlation}}). For delegated access,
the RAS translates the user into its local namespace and preserves the
agent ({{subject-resolution}}). Correlation does not grant authority:
the RAS decides within the grant's ceiling ({{actor-authorization}},
{{wag-redemption}}).

For example, two agents run behind one platform OAuth client, and one of
them later moves to another runtime with a different workload
credential. The resource domain keeps recognizing that agent through
the same issuer-qualified Agent Principal, without merging it with the
other agent, attributing its actions to the platform client, or
learning the new runtime's credential format. {{identity-example}}
works a shared-client case in full.

## Authentication, Resolution, and Proof {#inputs}

The IdP MUST validate a credential according to its configured type
before using it for identity resolution. A generic JWT token-type URI,
an unverified header, or a caller-supplied claim MUST NOT select a
weaker validation path or establish an Identity Binding.

Credential metadata follows its credential specification; discovery MUST
NOT establish trust. Request hints, discovered client metadata, and
unverified JWT claims MUST NOT by themselves establish
credential-authority trust or change an approved Identity Binding or
Client Association.

The IdP MUST NOT substitute one of three distinct functions for another:

* **Client authentication:** evidence authenticating the OAuth client.
* **Agent resolution:** resolution of the authenticated dedicated-client
  identity or independently validated workload identity through an
  Identity Binding to exactly one Agent Principal.
* **Key possession:** proof that the presenter controls a key, with the
  binding semantics of the proof mechanism.

Up to three identities meet in one request:

* the workload identity asserted by accepted evidence ({{evidence}});
* the authenticated OAuth client; and
* the Agent Principal ({{identity-binding}}).

None of them is inferred from another. With a dedicated client, the
authenticated client identity is itself the resolution input, and no
separate workload identity exists. The distinction between an
issuer-bound presenter key and a request proof key ({{terms}})
determines what a proof establishes.

The same credential can serve client authentication and agent resolution
without making the client and agent the same principal. Successful
client authentication MUST NOT imply successful agent resolution.
Successful agent resolution MUST NOT imply permission for the
authenticated client to exercise that agent.

## Canonical Identity and Tenant Boundaries {#canonical-identity}

The Agent Principal identifier MUST be unique and non-reassignable
within the IdP issuer's namespace, across all Governance Tenants sharing
that issuer identifier. The Governance Tenant is not part of the
downstream agent identity. A tenant-local identifier therefore needs
qualification to meet this issuer-wide uniqueness requirement before use
as an Agent Principal identifier. The Agent Principal identifier need
not equal an external subject, OAuth client identifier, SPIFFE ID,
display name, or instance identifier.

This profile provides identity continuity for the agent across changes
of execution environment, through Identity Binding, and across the
boundary between the IdP and the resource domain. Identity continuity is
an explicit decision by the governing authority to preserve the same
principal. It does not imply that the principal's permissions remain
unchanged. It is also not work continuity: whether an approved task,
with its purpose, approval, and lifecycle, still justifies an action is
outside this profile.

After a transfer to a different Governance Tenant under a different
administrative authority:

* The IdP MUST assert the agent under a new Agent Principal identifier.
* Delegations held for the previous identifier do not carry forward
  automatically ({{delegation-authorization}}).
* RAS principal links held for the previous identifier MUST NOT be
  re-keyed to the new identifier ({{agent-correlation}}).

For example, moving an agent to another customer's governance domain
creates a new identity. Renaming a tenant or changing its owner or
administrator within the same governance domain does not by itself
change the principal. This document defines no cross-tenant identity
migration protocol.

The IdP MUST establish an unambiguous Governance Tenant and, before
issuance, the Target Tenant for the requested RAS and resource. The RAS
MUST interpret an agent identifier in its asserted issuer context and
MUST NOT key agent authorization on a bare `sub`. Tenant resolution
failures use the errors in {{errors}} and {{issuance-errors}}.

## Governance Boundary and Execution Independence {#governance-boundary}

Clients, workloads, or other actors that require independently managed
authorization, delegation, attribution, resource correlation, or
disablement as principals need separate Agent Principal identities. This
holds even when they share a runtime, OAuth client, workload credential,
or deployment. Differences in process, replica, session, worker, or
credential alone do not require distinct identities.

An execution that shares its authorization, delegation, attribution,
resource correlation, and disablement with an Agent Principal can run as
that Agent Principal. A sub-agent working entirely within its parent's
authority and attributed to it is an example. An execution that needs
any of these separately needs its own identity.

Multiple executions can operate as the same Agent Principal. An agent
can move between workloads or execution environments through approved
Identity Bindings. Conversely, one environment can host multiple Agent
Principals. The validated resolution input and its Identity Binding
therefore need to distinguish exactly one Agent Principal for each
authorization transaction. The IdP rejects an ambiguous mapping
({{identity-binding}}), and a shared workload identity alone cannot
select among agents.

Scaling, restarting, rescheduling, migration, credential rotation, or
creation of additional executions, replicas, credentials, Identity
Bindings, or Client Associations does not by itself create, merge,
transfer, or increase Agent Principal authority. This profile defines no
aggregate budget, quota, or concurrency semantics.

## Grant Paths {#paths}

An Agent Principal is not intrinsically self-acting or delegated. The
authorization transaction determines whether it is represented as the
subject, in a WAG ({{wag-flow}}), or as the actor for a user, in an
ID-JAG ({{delegated-flow}}). Authorization for one relationship does not
imply authorization for the other.

### Delegated and Self-Acting Access Compared {#wag-differences}

| Area | Delegated ID-JAG | Self-acting WAG |
|---|---|---|
| Subject | User, from the subject credential | Agent Principal, from the agent-resolution input |
| Agent in the grant | Agent Principal in `act` | Grant subject, with no `act` ({{wag-claims}}) |
| Agent at the RAS | Kept in `act` beside the local user as subject | Correlated to a local agent principal ({{agent-correlation}}) |
| Authorization | Delegation Authorization | Agent Authorization ({{agent-authorization}}) |
| Client Association | For delegated issuance | A separate one for self-acting issuance |
| API enforcement | User authority and the actor gate | The agent's own authority; no actor gate |
| Refresh | RAS refresh under explicit policy | None; WAG prohibits refresh tokens |
{: title="Delegated and self-acting access compared"}

## Authorization Relationships {#authorization}

The basis for Agent or Delegation Authorization is a deployment choice.
Administrator assignment, organizational policy, and task authorization
are all acceptable, as is user consent for Delegation Authorization.
Assignment and approval records and their storage are outside this
profile.

The RAS and API determine effective resource and operation
authorization, including the actor gate ({{actor-authorization}}). The
IdP need not interpret every tool argument or business object. An
issuance decision that depends on those semantics requires authoritative
resource-domain evaluation, locally or through a trusted policy service.

### Agent Authorization {#agent-authorization}

For self-acting access, the IdP MUST authorize the resolved Agent
Principal to access the requested RAS, resource, and authority on its
own behalf in the requested client and tenant context. The IdP MUST do
so before issuing a grant that names the agent as subject. The IdP
MUST reject missing, revoked, expired, or insufficient Agent
Authorization. Valid credentials, an active Identity Binding, or a
Client Association MUST NOT imply it. Agent Authorization MUST NOT be
inferred from a Delegation Authorization involving the same agent.
Denied self-acting access MUST NOT fall back to delegated access or to
a broader authority.

### Delegation Authorization {#delegation-authorization}

Before constructing `act`, the IdP MUST authorize the resolved Agent
Principal to act for the user in the requested client, tenant, RAS,
resource, and authority context. The IdP MUST reject missing, revoked,
expired, or insufficient delegation authorization. Valid credentials,
user sign-in, or a shared client MUST NOT imply that authorization or
permit one agent to use another agent's.

### Authorization Lifetime {#authorization-lifetime}

Credential or grant expiration does not by itself terminate an access
token or RAS refresh authorization already issued; the grant's `exp`
limits redemption, not subsequent access.

The RAS MUST limit access-token and refresh-authorization lifetimes
under its local policy ({{ras-refresh}}). This profile defines no
portable IdP-imposed deadline on downstream authorization
({{deadline-gap}}) and requires no shared approval record or correlated
lifetime lookup.

### Delegated Actor Authorization {#actor-authorization}

For delegated access, the RAS and API MUST enforce both:

* **User authority:** the requested operation is within the user's
  permissions and the grant or token's authorized scope and constraints.
* **Actor gate:** the issuer-qualified agent is permitted to act for
  that user in the selected tenant and resource, within the authorized
  delegation. A valid signature or an `act` claim alone does not open
  the gate. Failure to establish the gate MUST result in denial.

The actor gate is an authorization condition, not a protocol object. It
can be implemented through an agent registration, tenant assignment,
consent policy, or another explicit rule. Requiring the agent to also
hold independent permissions on each object is local policy, not a
baseline requirement.

Every operation the API permits MUST be covered by an applicable
actor-gate authorization. The API MAY evaluate the gate directly or rely
on a validated RAS authorization whose scope and freshness satisfy
resource policy.

An ID-JAG issued under this profile asserts that the IdP authorized the
specified delegation within the grant's constraints. It does not assert
that the RAS's policy has been satisfied, and it does not convey the
IdP's underlying approval records. The RAS MUST independently decide
whether to accept that delegation under its local user, actor, client,
tenant, and resource policy.

The client identifier MUST NOT stand in for the actor in authorization.
Audit records that identify both the user and the issuer-qualified
actor, rather than the client identifier alone, preserve attribution.

# Profiles and Conformance {#conformance-metadata}

## Delegated Access with ID-JAG {#delegated-flow}

This document profiles ID-JAG issuance and redemption through the actor
extension point in {{Section 9.7 of ID-JAG}}. Where it is silent, ID-JAG
applies unchanged.

### Relationship to Base Specifications {#profile-additions}

This table is non-normative; the referenced sections define each
requirement.

| Area | Profile requirement | Defined in |
|---|---|---|
| Actor extension | Identity Binding resolves the agent; a separate Client Association authorizes client use | {{identity-binding}} |
| Dedicated-client input | Resolved from authenticated client context; issuer identifier as sole assertion audience; single-use `jti` | {{client-assertion-input}}, {{Section 4 of RFC7523bis}} |
| Other authentication-context inputs | Resolved from the identity validated by SPIFFE or Client Attestation authentication | {{optional-input-profiles}}, {{actor-inputs}} |
| Actor representation | One actor: Agent Principal as `act.sub`, IdP as `act.iss`; replaces Actor Profile's credential-to-actor copying | {{actor-construction}} |
| Request narrowing | Configured resolution mode; one resource; non-empty scope; actor-token parameters required in presented-evidence mode and rejected otherwise; no incoming actor chain | {{issuance-request}}, {{root-request}}, {{actor-inputs}} |
| Identity and client binding | Users and agents resolved separately; downstream `client_id` from an authoritative client-registration association | {{idp-subject-resolution}}, {{subject-resolution}}, {{agent-correlation}}, {{flow-configuration}} |
| Grant narrowing | One resource URI (a string; singleton arrays accepted), scope constraints, input-specific expiration limits; single use unless bound; DPoP and `cnf.jkt` in the bound profile | {{grant-common}}, {{grant-issuance}}, {{redemption-common}}, {{grant-protection}} |
| Resource processing | Actor and tenant context preserved; user authority and actor gate enforced with the selected token protection | {{access-token-response}}, {{api-processing}} |
| Refresh narrowing | Explicit policy, client binding, preserved proof binding and profile, finite absolute authorization expiration | {{ras-refresh}} |
| Error processing | `invalid_grant`, not RFC 8693's default `invalid_request`, for subject or actor credential and resolution failures; `actor_unauthorized` for a denied resolved actor | {{issuance-errors}} |
| Profile discovery | Governed profiles in existing ID-JAG metadata; trusted policy sets the minimum | {{metadata}} |
{: title="Additions and narrowings to the base specifications"}

## Self-Acting Access with WAG {#wag-flow}

Self-acting access is a peer realization of the federation model: the
Agent Principal is the subject of a Workload Authorization Grant (WAG)
{{WAG}} issued by the IdP ({{wag-issuance}}) and redeemed at the RAS
({{wag-redemption}}). This document specifies a governed composition of
WAG, including the issuance exchange, client binding, principal
correlation, and grant protection. Generic WAG support does not imply
these requirements. This document defines the complete wire contract it
relies on, so {{WAG}} is an informative reference, and the composition
remains subject to alignment with the evolving WAG specification
({{wag-gaps}}). The WAG token and JWT types are provisional.

| Area | WAG-01 | This profile |
|---|---|---|
| Issuer | The Platform that created the agent | The governing IdP, through token exchange ({{wag-issuance}}) |
| Client authentication | Not required; `client_id` carries no meaning | Required at issuance and redemption; `client_id` is the client's registration at the RAS ({{redemption-common}}) |
| Grant binding | Bearer; proof of possession open | DPoP under {{grant-protection}}, required for the bound profile |
| Explicit type | None defined | `typ` `wag+jwt`, checked at redemption ({{wag-redemption}}) |
| Replay | Open | Unbound grants are single-use ({{redemption-common}}) |
| `resource` | Recommended, not required | Exactly one ({{issuance-request}}) |
| Previously unseen agents | Accepted on first assertion | Authorized correlation required ({{agent-correlation}}) |
| Refresh tokens | Prohibited | Prohibited |
{: title="Governed composition of WAG"}

## Adoption Profiles {#adoption-profiles}

The adoption path preserves existing Enterprise-Managed Authorization
{{EMA}} deployments, which need no changes to continue, and adds agent
governance before requiring grant binding. The names identify deployment
profiles, not assurance ratings.

| Adoption profile | Required addition | Grant protection |
|---|---|---|
| Enterprise access | Existing EMA and base ID-JAG; no separate Agent Principal required | Existing deployment policy |
| Governed agent access | Agent resolution, Identity Binding, Client Association, governed actor (delegated) or subject (self-acting), tenant enforcement, downstream actor gate (delegated) | Unbound grants permitted only by explicit policy; any binding present is enforced |
| Bound governed agent access | All governed agent requirements plus DPoP at grant issuance and redemption | `cnf.jkt` and same-key continuity required |
{: title="Adoption profiles"}

Enterprise access is a migration baseline, not conformance to this
document's governed profiles. Adding `act` alone does not establish
governed agent conformance: identity resolution and actor authorization
are also required. The adoption profiles apply to both realizations,
each under its own URIs ({{metadata}}).

"Bound" refers to sender constraint on the grant, ID-JAG or WAG, between
issuance and redemption. It does not imply sender constraint on the
agent-resolution credential or the resulting access token. Grant
protection, workload-evidence protection, and access-token protection
are separate choices. Even bound governed agent access can use bearer
workload evidence and, under explicit resource policy, bearer access
tokens.

## Grant Protection {#grant-protection}

Client authentication and all governance requirements remain mandatory
in either adoption profile.

By profile:

* **Bound governed agent access:** The client MUST supply a DPoP proof
  at issuance. The IdP MUST reject a missing proof with
  `invalid_request`. The RAS MUST require `cnf.jkt` in the grant.
* **Governed agent access:** DPoP support is OPTIONAL. The IdP and RAS
  MAY issue and accept grants without `cnf` only when trusted policy
  explicitly permits them for the client, trust relationship, and
  resource.

In both profiles:

* **Supplied proof:** A supplied DPoP proof MUST be validated under
  {{RFC9449}}. An endpoint that does not support DPoP MUST reject a
  request containing a DPoP proof with `invalid_request`; it MUST NOT
  silently ignore the proof. At issuance, a valid proof MUST result in
  `cnf.jkt` binding of the grant, as in {{Section 9.8.1.1 of ID-JAG}}.
* **Bound grant:** A grant containing `cnf` MUST have a valid, supported
  `jkt` binding. The RAS MUST require a fresh DPoP proof whose public
  key thumbprint matches exactly, as in {{Section 9.8.1.2 of ID-JAG}}.
  Missing proof, missing required binding, unsupported confirmation, or
  key mismatch MUST fail with `invalid_grant`.
* **Unbound grant:** When policy permits a grant without `cnf`, the
  client MAY present a DPoP proof only at redemption to obtain a
  DPoP-bound access token ({{access-token-protection}}). That proof does
  not retroactively bind the grant.
* **Credential proof:** Selecting governed agent access MUST NOT disable
  proof required by the agent-resolution input or client authentication
  method.

## Conformance {#scope}

This profile does not establish trust in previously unknown agent
issuers or automatically create Identity Bindings from presented
credentials.

Unless explicitly limited to bound grants or a named profile, the
requirements of this document apply to both governed adoption profiles.
Conformance claims MUST identify the supported profile by its URI
({{metadata}}), the realization, the implemented role, supported inputs,
and any claim of generic shared-client interoperability. An
implementation supports delegated access, self-acting access, or both.

The IdP, RAS, and client MUST implement their respective
requirements in:

* {{model}}, {{conformance-metadata}}, {{security}}, and
  {{mandatory-input-profiles}};
* the parts of {{issuance}}, {{redemption}}, {{api-processing}}, and
  {{continuing-access}} that apply to each supported realization; and
* {{optional-input-profiles}} for each supported optional input.

Each realization has this mandatory interoperability path:

* **Issuance:** The client and IdP MUST implement dedicated-client
  resolution using RFC 7523 `private_key_jwt` authentication
  ({{client-assertion-input}}). For delegated access, they MUST also
  implement ID Token subjects.
* **Redemption:** The client and RAS MUST implement `private_key_jwt`
  for redemption. DPoP support and use are REQUIRED for bound governed
  agent access; governed agent access follows {{grant-protection}}.
* **API:** The API MUST implement {{api-processing}}, with {{wag-api}}
  for self-acting access.

The inputs of {{optional-input-profiles}}, existing platform JWTs, SAML
subjects, and IdP refresh-token subjects are OPTIONAL capabilities.
Claiming an input requires that input's rules, not support for another
input. An implementation that claims generic shared-client
interoperability MUST support the existing platform JWT input
({{imported-jwt-input}}): an IdP by accepting it, and a client by
presenting it. Implementations that support only different native
inputs do not interoperate on a shared client, and their conformance
claims show this.

ID-JAG requires support for Identity Assertions
({{Section 4.3 of ID-JAG}}). Requiring ID Token subjects specifically
gives independent implementations a common subject-token format. This is
an implementation baseline, not a requirement to deploy one client per
agent: deployments MAY use mutually supported optional inputs.

An ID Token's audience identifies the authenticated IdP client
({{subject-token-validation}}). A dedicated deployment therefore needs a
user authorization flow for each agent's client registration, though an
existing IdP session may avoid another login prompt. A platform that
keeps its shared single sign-on (SSO) client instead uses the existing
platform JWT ({{imported-jwt-input}}) or an optional input.

### Optional Inputs {#optional-inputs}

The following inputs are OPTIONAL: SPIFFE JWT-SVID ({{jwt-svid-input}}),
Client Attestation ({{agent-evidence}}), and SPIFFE WIT-SVID and
X.509-SVID ({{spiffe-input}}).

## Client Authentication and Algorithms {#algorithms}

**Client authentication:** RFC 7523 client authentication at either
server follows {{client-assertion-input}}, and JWT-SVID authentication
follows {{jwt-svid-input}}. Other configured methods MAY be used, and
client identifiers and keys MAY differ between servers.

**Algorithms:** Each implementing role MUST support the capabilities
below for the artifacts it produces or validates:

| Artifact | Mandatory-to-implement (MTI) capability |
|---|---|
| ID-JAG or WAG | IdP signing and RAS validation: `RS256` ({{Section 5 of RFC7523}}) |
| `private_key_jwt` | Client signing and IdP/RAS validation: `RS256` under {{Section 5 of RFC7523}} |
| JWT-SVID, where supported | IdP validation: `RS256` under {{Section 3.1 of SPIFFE-OAUTH}}, plus `ES256` added by this profile |
| DPoP, where supported or required | Client proof generation and server validation: `ES256`, a minimum {{RFC9449}} does not prescribe |
{: title="Mandatory-to-implement algorithms"}

Other algorithms permitted by the selected specification MAY be used
through trusted configuration and metadata.

## Time, Replay, and Key Validation {#time-validation}

Validators MUST enforce:

* **Time claims:** Apply the selected credential's expiration and other
  time rules. Reject `iat` later than the current time plus permitted
  clock skew. Under {{RFC7519}}, `iat` has no not-before semantics.
* **Clock skew:** Use a configured tolerance that MUST NOT extend a
  configured maximum age or lifetime. It SHOULD remain within the few
  minutes contemplated by {{RFC7519}}.
* **Replay protection:** Apply each credential, proof, and grant
  mechanism independently. Where a mechanism retains replay state, that
  state MUST remain in effect for as long as the credential, proof, or
  grant would otherwise be accepted, including the maximum allowed skew.

Key lookup MUST retain the issuer or trust-domain association
({{Section 3.8 of RFC8725}}).

A fresh proof does not renew an expired credential; an unchanged
identifier does not authorize a new proof key.

## Token Endpoint Errors {#errors}

Token endpoint errors follow {{Section 5.2 of RFC6749}} and the
applicable extension, authentication, and proof specifications.
Servers MUST validate client authentication, credentials, and proofs
before authorization. Proof, grant-binding, grant-claim, and
authorization-detail failures use the errors specified in
{{grant-protection}}, {{spiffe-input}}, {{redemption-common}}, and
{{issuance-request}}. {{issuance-errors}} and {{redemption-errors}} list
the failures specific to each server.

| Failure | Error |
|---|---|
| Unacceptable `resource` parameter at exchange, redemption, or refresh, including multiple values or a target outside the grant or retained authorization | `invalid_target` under RFC 8707 |
| Target Tenant cannot be resolved for the requested resource | `invalid_target` |
| No client registration association exists for the requested RAS ({{flow-configuration}}) | `invalid_target` |
| Unacceptable requested scope, invalid scope reduction, or no non-empty scope can be issued | `invalid_scope` |
| User cannot be resolved, user or required link is disabled, or subject identifiers conflict | `invalid_grant`; no token or automatic linking fallback |
{: title="Target, authority, and user-resolution errors"}

Client authentication failures use the authentication method's error,
including when the same credential supplies an agent-resolution input.

Error descriptions SHOULD NOT reveal identity, binding, or policy
details beyond those disclosed by the error category. Distinguishing
`invalid_grant` from `actor_unauthorized` reveals that an actor was
resolved but denied, but not which binding-resolution check failed.
That disclosure reaches even a holder of stolen bearer evidence who
passes the request's other authentication.

## Authorization Server and Client Metadata {#metadata}

The governed profiles have distinct identifiers:

* **Governed agent access:**
  `urn:ietf:params:oauth:grant-profile:id-jag-governed-agent`
* **Bound governed agent access:**
  `urn:ietf:params:oauth:grant-profile:id-jag-agent-federation`
* **Self-acting governed agent access:**
  `urn:ietf:params:oauth:grant-profile:wag-governed-agent`
* **Self-acting bound governed agent access:**
  `urn:ietf:params:oauth:grant-profile:wag-agent-federation`

Enterprise access uses the base
`urn:ietf:params:oauth:grant-profile:id-jag` identifier under ID-JAG;
that identifier alone makes no governed-agent conformance claim.

These URIs identify RAS and client processing. No URI claims a
credential class, continuation support, a particular workload-evidence
protection, or access-token protection; these are capabilities and
configured minimums.

### Authorization Server Metadata {#server-metadata}

Servers MUST publish {{RFC8414}} metadata as follows:

* **RAS:** Include each supported governed profile URI, and for
  delegated access the base
  `urn:ietf:params:oauth:grant-profile:id-jag`, in
  `authorization_grant_profiles_supported`. The self-acting URIs use the
  same parameter, pending coordination ({{wag-gaps}}).
  * Include `urn:ietf:params:oauth:grant-type:jwt-bearer` in
    `grant_types_supported` for this profile.
* **IdP:** Advertise Token Exchange in `grant_types_supported`. For
  delegated access, advertise ID-JAG in
  `identity_chaining_requested_token_types_supported` under
  {{Section 7.1 of ID-JAG}}. For self-acting access, advertise the WAG
  token type in the same parameter, pending coordination ({{wag-gaps}}).
  * Include `private_key_jwt` in
    `token_endpoint_auth_methods_supported`.
* **Both:** Advertise supported client authentication methods and, when
  DPoP is supported, DPoP algorithms, including {{algorithms}}'s common
  capabilities. Where supported, publish the existing Client ID Metadata
  Document (CIMD) and mutual-TLS capability metadata defined by {{CIMD}}
  and {{RFC8705}}.

### Client Metadata {#client-metadata}

A client SHOULD advertise each supported governed profile URI in
`authorization_grant_profiles_supported` in its authoritative client
metadata under {{Section 8 of ID-JAG}}, including when supplied through
CIMD. Its `grant_types` MUST permit:

* `urn:ietf:params:oauth:grant-type:token-exchange` at the IdP.
* `urn:ietf:params:oauth:grant-type:jwt-bearer` at the RAS.

### Discovery and Profile Applicability {#discovery}

Profile applicability follows these rules:

1. **Establish policy:** Before exchange, trusted configuration MUST
   establish the applicable governed profile and minimum requirements
   for the client, issuer trust relationship, and target resource. The
   client, IdP, and RAS MUST use that configuration. This document
   defines no transaction-level profile negotiation.
2. **Enforce the minimum:** Each server MUST enforce its configured
   minimum regardless of absent `actor_token`, `act`, DPoP, or `cnf`.
   Their presence or absence MUST NOT select a different profile.
   Metadata advertises capabilities; it MUST NOT authorize a lower
   profile or override resource policy.
3. **Prevent fallback:** Implementations MUST NOT retry a failed
   governed request as ordinary EMA or drop proof to retry as governed
   agent access. A lower profile requires a separately authorized
   configuration, not an error-driven fallback.
4. **Enforce resource policy:** The RAS and API MUST agree on the
   minimum profile for their resource. The API relies on the RAS to
   enforce grant protection. An access token's `cnf` describes the
   token's own protection. It does not establish which grant profile
   was used. Where multiple paths share a resource, applicability
   follows {{api-processing}}.

An implementation MAY serve existing EMA and either governed profile
concurrently under these rules. Supporting the bound profile does not
require accepting grants without sender constraint or advertising the
intermediate profile.

Migration changes the configured profile after the participating roles
implement its requirements. It does not relabel previously issued
grants or refresh tokens.

Before using either path:

* **Issuance support:** The client and IdP MUST agree through trusted
  configuration on issuance support and any options. Generic JWT or
  authentication-method support is insufficient.
* **RAS capabilities:** The client MUST verify the RAS's profile
  advertisement, JWT bearer grant support, and compatible access-token
  protection. If no supported profile satisfies the configured minimum,
  the client MUST NOT initiate that path.
* **Metadata consistency:** For delegated access, if the
  `actor_profile_token_exchange` parameter of
  {{Section 16.2 of ACTOR-PROFILE}} is published, it MUST describe only
  the paths actually supported and agree with the ID-JAG advertisement.

# Grant Issuance at the IdP {#issuance}

## Issuance Prerequisites {#flow-configuration}

**Relationships:** The IdP MUST issue a grant only under the applicable
identity, client, delegation, and target relationships ({{model}});
{{configuration}} describes their configuration.

**Downstream client:** The IdP MUST derive the grant's `client_id` from
an authoritative association between the authenticated IdP client and
that client's registration at the target RAS. This is the client
registration association of {{configuration}}, not a Client
Association. A client-supplied downstream client identifier MUST NOT
select or override that association.

## Token Exchange Request {#issuance-request}

Both grants are requested with a token exchange request {{RFC8693}} to
the IdP token endpoint. The client authenticates as the configured
client and supplies any proof required by {{grant-protection}}. Both
requests carry these REQUIRED parameters:

| Parameter | Value |
|---|---|
| `grant_type` | `urn:ietf:params:oauth:grant-type:token-exchange` |
| `audience` | One target RAS issuer identifier |
| `resource` | Exactly one resource URI under {{RFC8707}}, served by the RAS named in `audience` |
| `scope` | Non-empty scope string for the requested resource |
{: title="Token exchange parameters common to both grants"}

**Resource:** A client requiring access to multiple resources MUST
obtain a separate grant for each resource. The IdP MUST reject multiple
`resource` parameters with `invalid_target`. The `resource` URI conveys
the Target Tenant through the configured resource-to-tenant association,
not the IdP's Governance Tenant.

**Scope and authorization details:** `authorization_details` MAY
accompany the required non-empty `scope` and is processed under ID-JAG.
The IdP MUST constrain all granted scope and `authorization_details` to
the requested resource. If requested authorization details cannot be
confined to it, the IdP MUST reject the request with
`invalid_authorization_details` under {{Section 6 of RFC9396}} rather
than authorize additional resources.

{{root-request}} and {{wag-request}} add the parameters of each grant.

## Agent Resolution {#identity}

The IdP resolves the Agent Principal from validated inputs through an
approved Identity Binding. For delegated access, it also resolves the
user ({{idp-subject-resolution}}). The RAS then correlates both with its
local principals ({{agent-correlation}}, {{subject-resolution}}).

### Agent Resolution Inputs {#evidence}

Every agent-resolution input satisfies this contract, which summarizes
requirements stated in the cited sections and the input's own section
({{input-profiles}}):

* **Independent validation:** The credential is validated under its
  configured credential profile before it is used for resolution
  ({{inputs}}).
* **Qualified identity:** The input yields an authenticated identity and
  identifies the credential authority or client-registration context
  that qualifies it. That qualified identity keys the Identity Binding
  ({{identity-binding}}).
* **Credential authority:** For workload evidence, the IdP relies on the
  credential mechanism having authorized issuance for the asserted
  workload identity. A caller-supplied subject or agent identifier alone
  MUST NOT establish that identity. For dedicated clients, the IdP
  relies on the configured client-authentication method and approved
  binding.
* **Proof semantics:** The input states whether it is bearer evidence or
  binds a key, and what that proof establishes
  ({{credential-requirements}}).

Credential acquisition is outside this profile. Audience validation
follows each input's credential specification and section; there is no
universal IdP audience.

Input support follows {{scope}} and {{optional-inputs}}; resolution mode
selection and rejection follow {{actor-inputs}}.

### Bearer Evidence Limits {#credential-requirements}

Where issuer endorsement of the proof key is required, the deployment
needs a supported input that cryptographically binds the key, such as
Client Attestation under {{agent-evidence}} or the WIT-SVID input under
{{spiffe-input}}. DPoP co-presented with bearer JWT-SVID or unbound
platform JWT evidence establishes possession only. DPoP MUST NOT
substitute for a credential proof that the selected input requires.

Bearer evidence establishes the credential authority's assertion of the
workload identity. It does not cryptographically bind the current
presenter to that workload. An attacker who holds acceptable bearer
workload evidence can therefore impersonate the workload and obtain a
grant, bound to a grant proof key of its choice, if it also passes:

* client authentication;
* Client Association; and
* either the user-credential and delegation checks or the
  agent-authorization check.

In the JWT-SVID path, the same bearer credential also satisfies client
authentication, so that check is not an independent possession factor.

Short evidence lifetimes limit this exposure; sender-constraining the
output does not prevent it ({{baseline-costs}}).

### Agent Resolution Input Validation {#actor-inputs}

**Mode selection:** After client authentication, the IdP MUST determine
the resolution mode from trusted configuration for the authenticated
client, applicable profile, and target. If that configuration does not
establish an unambiguous mode, it MUST reject the request with
`invalid_request`. The presence or absence of actor-token parameters
MUST NOT select or change that mode.

* **Authentication-context resolution:** The IdP MUST use the identity
  validated during client authentication for this token request under
  the configured input in {{evidence}}. Client-supplied identity hints
  and context from another request or session MUST NOT substitute for
  that identity. The credential class MUST match the authentication
  method. The client MUST omit `actor_token` and `actor_token_type`.
  The IdP MUST reject either parameter with `invalid_request`, including
  a duplicate authentication credential.
* **Presented-evidence input:** In delegated issuance, the IdP MUST
  require both `actor_token` and `actor_token_type`, and the type MUST
  be `urn:ietf:params:oauth:token-type:jwt` ({{issuance-errors}}). In
  self-acting issuance, the evidence is the subject token
  ({{wag-request}}). Validate the separate platform JWT under
  {{imported-jwt-input}}. Missing or rejected evidence MUST NOT trigger
  resolution from authentication context.

**Credential class:** The IdP MUST select exactly one configured
platform credential class for presented evidence, or reject with
`invalid_request`. Native SPIFFE and Client Attestation inputs use
authentication context and MUST NOT be accepted through
presented-evidence mode. Credential classes MUST have mutually exclusive
validation rules under {{Section 3.12 of RFC8725}}. Within one token
request, rejection under the selected class's validation or
authorization rules MUST NOT trigger validation under another class.

**Inbound actor chain:** To preserve the single user-to-agent
relationship, the IdP MUST reject an agent-resolution JWT or ID Token
containing `act`, and a refresh-token subject whose retained
authorization contains an actor chain.

### Identity Binding {#identity-binding}

**Resolution:** After validating the configured resolution input, the
IdP MUST:

* Resolve the exact qualified client or workload identity ({{evidence}})
  to one active Agent Principal through an enabled Identity Binding;
  reject missing, ambiguous, or disabled mappings.
* Apply exact resolution even when client authentication permits a
  prefix match. A client identifier, including a {{CIMD}} URL,
  identifies the client, not the agent.

Similar names, unqualified identifiers, or a shared signing key MUST
NOT establish identity equivalence. An identifier of one execution, such
as a process, replica, or container, MUST NOT select or change the Agent
Principal ({{governance-boundary}}). A client instance identifier
({{INSTANCE}}) MUST NOT select or change the Agent Principal except
through the managed-installation binding of {{agent-evidence}}, and MUST
NOT satisfy a Client Association.

**Disabling:** An Identity Binding can be disabled independently of the
Agent Principal and its other bindings. A disabled binding MUST NOT
authorize new grant issuance. Disabling a binding does not itself revoke
outstanding tokens; their treatment follows {{status-changes}}.

**Client Association:** Before issuing a governed grant, the IdP MUST
verify that a Client Association permits the authenticated client to use
the selected Identity Binding, with the selected credential class, for
the requested acting relationship ({{terms}}). The IdP MUST NOT
substitute the client's identity for the resolved actor.

Association permissions have these limits:

* Permission for delegated issuance does not imply self-acting
  issuance, nor the reverse.
* A Client Association can authorize several Identity Bindings.
  Authorization of one binding, a credential authority, a credential
  class, or the Agent Principal itself MUST NOT imply authorization of
  another binding unless the association's policy explicitly includes
  it.

Policy representation and evaluation mechanisms are outside this
profile.

For a dedicated client, deployments can administer the Identity Binding
and the Client Association in one registration or policy object; they
remain separate checks.

## Issuance Authorization {#issuance-authorization}

Validated identity does not grant authority. After resolution under
{{inputs}}, {{identity}}, and, for delegated access,
{{idp-subject-resolution}}, the IdP MUST authorize issuance under
current assignments and policy for the resolved agent, authenticated
client, acting relationship, Governance and Target Tenants, RAS,
resource, and requested authority. The authority asserted in a delegated
grant MUST be bounded by both:

* The authority the IdP is authorized to assert for the user.
* The authority permitted by the agent's delegation authorization
  ({{delegation-authorization}}).

For a self-acting grant, the asserted authority MUST be bounded by the
Agent Authorization ({{agent-authorization}}).

Issuance and denial follow these rules:

* The IdP MAY narrow scope, reflecting the result in the grant and
  response under {{RFC8693}}. It MUST return `invalid_scope` if no scope
  can be granted.
* The IdP MUST NOT issue by dropping a required actor or binding,
  substituting an external identifier for the Agent Principal, or
  weakening proof requirements.
* Denied delegation MUST NOT fall back to self-acting access.

Before issuance, the IdP MUST apply current binding and authorization
policy and reject an inactive agent or withdrawn binding once the change
has been applied. The IdP MUST apply such a change within a configured
freshness limit on cached policy data.

If IdP approval requires a downstream lifetime condition that the
selected composition cannot enforce, the IdP MUST reject issuance
with `actor_unauthorized` for delegated issuance or `invalid_target`
for self-acting issuance. It MUST NOT discard that condition or treat
a shorter grant lifetime as enforcing it. Revocation follows
{{status-changes}}.

## Common Grant Claims, Lifetime, and Response {#grant-common}

Each grant carries these claims in addition to those of its own section
({{grant-issuance}}, {{wag-claims}}):

| Claim | Required result |
|---|---|
| `client_id` | The client's registration identifier at the RAS, derived under {{flow-configuration}} |
| `resource` | The authorized resource URI, issued as a JSON string |
| `scope` | Non-empty authorized scope string, no broader than the approved request |
| `cnf.jkt` | Thumbprint of the grant proof key when DPoP is used at issuance; REQUIRED for bound governed agent access ({{grant-protection}}) |
| `exp`, `iat`, `jti` | As in {{Section 3.1 of ID-JAG}}, within the lifetime limits below |
{: title="Claims common to both grants"}

**Lifetime:** A grant has these limits:

* **Configured limit:** The grant lifetime SHOULD be at most five
  minutes and MUST NOT exceed the configured lifetime limit.
* **Agent-resolution input:** The grant MUST NOT outlive the validated
  resolution credential, using the bound in the following table. The
  dedicated-client assertion is the exception: it MUST be valid when the
  request is authenticated, but it authenticates one transaction and
  does not cap the grant.

| Input | Lifetime bound on the grant |
|---|---|
| Dedicated client assertion | None (the exception above) |
| Platform JWT | The effective evidence deadline in {{imported-jwt-input}} |
| JWT-SVID | Its `exp` |
| WIT-SVID and Client Attestation | The credential's `exp`; the PoP JWT adds no limit |
| X.509-SVID | The earliest `notAfter` in the validated certificate path, excluding the trust anchor |
{: title="Grant lifetime bound by agent-resolution input"}

The ID-JAG is also limited by its subject credential
({{grant-issuance}}).

**Response:** The response follows {{Section 4.3.4 of ID-JAG}}; for a
WAG, `issued_token_type` is the WAG token type. For a bound grant, the
client MUST retain the DPoP key for redemption and SHOULD inspect
the grant to confirm that `cnf.jkt` identifies that key
({{Section 9.8.1.1 of ID-JAG}}).

## Delegated Issuance: ID-JAG {#exchange-request}

### Request {#root-request}

The client sends the token exchange request of {{Section 4.3 of ID-JAG}}
with the common parameters and rules of {{issuance-request}}. The
following parameters are REQUIRED except where the resolution mode
specifies otherwise:

| Parameter | Value |
|---|---|
| `requested_token_type` | `urn:ietf:params:oauth:token-type:id-jag` |
| `subject_token` | User subject credential issued for the authenticated client ({{subject-token-validation}}) |
| `subject_token_type` | `urn:ietf:params:oauth:token-type:id_token`, `urn:ietf:params:oauth:token-type:saml2`, or `urn:ietf:params:oauth:token-type:refresh_token` |
| `actor_token` | Omitted for authentication-context resolution; REQUIRED for a presented-evidence input under {{actor-inputs}} |
| `actor_token_type` | Omitted when `actor_token` is omitted; REQUIRED, with value `urn:ietf:params:oauth:token-type:jwt`, whenever `actor_token` is present |
{: title="ID-JAG token exchange parameters"}

### Subject Token Validation {#subject-token-validation}

The IdP MUST support ID Token subjects, MAY support SAML 2.0 assertion
subjects, and MAY support its own refresh tokens when agreed in client
configuration, validating each under {{Section 4.3.3 of ID-JAG}}:

* **SAML 2.0 assertion:** The IdP MUST map the assertion's Audience to
  the authenticated client under {{Section 4.5 of ID-JAG}} and resolve
  the subject under {{Section 3.2 of ID-JAG}}.
* **Refresh token:** The IdP MUST establish that the refresh token's
  retained authorization permits the requested target and authority.
  Possession of a refresh token or an `offline_access` grant alone
  MUST NOT establish that permission. That authorization can include
  an explicitly associated cross-domain delegation authorization,
  represented and provisioned locally by the IdP. OpenID Connect scope
  names do not themselves map to resource-specific permissions. Any
  binding retained with the refresh token MUST be enforced rather than
  bypassed by selecting another agent-resolution input, with conflicts
  rejected as `invalid_grant`.

**Also required:** Every subject input requires a current validated
agent-resolution input and delegation authorization under
{{delegation-authorization}}. User access tokens are not subject inputs
({{access-token-subject-gap}}). JWT encoding alone does not make an
access token an ID Token.

### Subject Resolution {#idp-subject-resolution}

Subject identifiers, tenant relationships, `aud_sub`, `aud_tenant`, and
`sub_id` follow Sections 3.1, 5, and 6 of {{ID-JAG}}, with these
additions.

The IdP MUST:

* Resolve exactly one user from the ID Token's issuer-qualified subject
  or the SAML assertion's issuer-qualified NameID and tenant context,
  or from the validated refresh token's authorization context. The actor
  credential and authenticated client MUST NOT substitute for that
  identity.
* Select the subject namespace of the target RAS's SSO relationship. A
  client-specific pairwise subject MUST NOT be copied into another
  relying party's namespace without resolving the same user there.
* Derive `aud_sub`, `aud_tenant`, or `sub_id`, when used, from an
  authoritative association for the target, never from a client-supplied
  account hint.
* Reject issuance for a disabled user or missing, ambiguous, or
  conflicting resolution ({{errors}}).

### Actor Resolution and Construction {#actor-construction}

In delegated issuance, both resolution modes proceed through this
section, and a governed request MUST result in the required governed
`act` or fail. Omitting actor-token parameters in authentication-context
mode does not request ordinary EMA or subject-only impersonation.

After credential validation, the IdP MUST resolve the agent under
{{identity}} and authorize issuance under {{issuance-authorization}} and
{{delegation-authorization}}. The ID-JAG MUST contain one `act` object
with:

* `sub`: the Agent Principal identifier from the Identity Binding.
* `iss`: this IdP's issuer identifier.

These values MUST come from the approved mapping, even when source and
governed identifiers coincide. For presented-evidence inputs this
replaces credential-to-actor copying in
{{Section 6.3 of ACTOR-PROFILE}}.

The object MUST follow {{Section 3.4 of ACTOR-PROFILE}}, including its
`sub_profile` recommendation and unclassified-actor rules. Any
`sub_profile` MUST reflect the IdP's authoritative classification.
Being an Agent Principal does not itself establish the `ai_agent`
classification of {{ENTITY-PROFILES}}.

### Grant Issuance {#grant-issuance}

**Claims:** The ID-JAG MUST use the format and claims of
{{Section 3.1 of ID-JAG}} and the common claims of {{grant-common}}, and
additionally satisfy:

| Claim | Required result |
|---|---|
| `sub` | Same user as the validated subject credential, expressed in the IdP's subject namespace for the RAS |
| `act` | Agent Principal actor constructed under {{actor-construction}} |
{: title="ID-JAG subject and actor claims"}

**Unambiguous context:** The IdP MUST NOT issue a grant if it cannot
determine an unambiguous user, actor, downstream client, or tenant
relationship.

**Lifetime:** The limits of {{grant-common}} apply. The grant's
expiration also MUST NOT exceed the subject credential's expiration,
which is:

* **ID Token:** its `exp` claim.
* **SAML assertion:** the earliest applicable `NotOnOrAfter` in the
  assertion's `Conditions` and the `SubjectConfirmationData` used to
  validate the subject. If neither supplies an expiration bound, the
  IdP MUST reject the subject as `invalid_grant`.
* **Refresh token:** its expiry, if the IdP records one. Otherwise the
  configured and agent-resolution input limits apply; absence of a
  recorded expiry does not authorize an unlimited grant lifetime.

## Self-Acting Issuance: WAG {#wag-issuance}

Self-acting issuance is one token exchange with two resolution modes.
The relationship and downstream client rules of {{flow-configuration}}
and the client authentication and algorithm rules of {{algorithms}}
apply. The IdP MUST:

1. Authenticate the client and validate the resolution input under
   {{evidence}} and {{actor-inputs}}, as presented under
   {{wag-request}}.
2. Resolve the Agent Principal through an active Identity Binding
   ({{identity-binding}}) from the configured input: the workload
   credential presented as the subject token, or the authenticated
   client identity.
3. Verify the Client Association for self-acting issuance
   ({{identity-binding}}).
4. Authorize issuance under {{issuance-authorization}}, applying Agent
   Authorization ({{agent-authorization}}) for the requested RAS,
   resource, and authority. No user is involved.
5. Apply {{grant-protection}} and issue the WAG under {{wag-claims}}.

**Failures:** {{issuance-errors}}.

The client redeems the WAG under {{redemption-request}}, and the RAS
processes it under {{wag-redemption}}; {{wag-example}} shows the
messages.

### Issuance Request {#wag-request}

Token exchange is used because only its `issued_token_type`
({{RFC8693}}) labels the output as an assertion for another token
endpoint. The request carries the common parameters and rules of
{{issuance-request}} and the parameters below, which are REQUIRED except
where the table or the resolution mode specifies otherwise. The subject
token carries the agent-resolution input and is not processed under
{{subject-token-validation}}.

| Parameter | Value |
|---|---|
| `requested_token_type` | `urn:ietf:params:oauth:token-type:wag` (provisional) |
| `subject_token`, `subject_token_type` | Per resolution mode, below |
| `actor_token`, `actor_token_type` | MUST be absent |
{: title="WAG token exchange parameters"}

**Mode selection:** Configured under {{actor-inputs}}.

**Presented-evidence resolution:** The workload credential is the
subject token, with `subject_token_type`
`urn:ietf:params:oauth:token-type:jwt`. The client authenticates
separately. The existing platform JWT ({{imported-jwt-input}}) is
presented this way. The presented-evidence, classification, and
mutual-exclusion rules of {{actor-inputs}} apply to that subject token.

**Authentication-context resolution:** The authentication-context rules
of {{actor-inputs}} apply. In this mode:

* {{RFC8693}} cannot name the authenticated client as the subject
  without a subject token. A client authenticated with a JWT therefore
  MUST repeat that JWT, byte for byte, as `subject_token` with type
  `urn:ietf:params:oauth:token-type:jwt`. That JWT is the credential
  itself: the RFC 7523 assertion, the JWT-SVID, the WIT-SVID, or the
  Client Attestation JWT, not an accompanying proof-of-possession JWT.
* The IdP MUST reject a subject token that is not byte-identical to the
  credential presented for authentication. This prevents a client from
  substituting another party's assertion as the subject.
* Carrying one assertion in both parameters does not violate the
  single-use `jti` rule of {{client-assertion-input}}.
* A client authenticated by X.509-SVID over mutual TLS presents no JWT
  and has no self-acting issuance under this profile ({{wag-gaps}}).

### Grant Claims {#wag-claims}

The WAG subject identifies the governed Agent Principal, not the
credential subject from which it was resolved. The grant is a JWT with
`typ` `wag+jwt` (provisional) whose claims are aligned with the claim
set of {{Section 5.1 of WAG}}: the common claims of {{grant-common}} and
the following:

| Claim | Value |
|---|---|
| `iss` | The IdP issuer identifier |
| `sub` | The Agent Principal identifier from the Identity Binding |
| `aud` | The target RAS issuer identifier |
{: title="WAG issuer, subject, and audience claims"}

The WAG MUST NOT contain `act`.

**Unambiguous context:** The IdP MUST NOT issue a WAG unless the Agent
Principal, downstream client, and tenant are unambiguous.

**Lifetime:** The limits of {{grant-common}} apply.

## Issuance Errors {#issuance-errors}

In addition to {{errors}}, the IdP uses these errors:

| Failure | Error |
|---|---|
| Unsupported or invalid requested authorization details | `invalid_authorization_details` ({{Section 8 of RFC9396}}) |
| Unsupported input combination, ambiguous credential classification, or unsupported `actor_token_type` in presented-evidence mode | `invalid_request` |
| No unambiguous configured resolution mode, or missing actor-token parameters in presented-evidence mode | `invalid_request`; no mode fallback |
| Actor-token parameters in an authentication-context mode, or a method inconsistent with that mode | `invalid_request`; no mode fallback |
{: title="Request errors"}

| Failure | Error |
|---|---|
| Invalid subject or agent-resolution credential, or disallowed inbound actor chain | `invalid_grant` |
| Absent, disabled, or ambiguous Identity Binding, or no active Agent Principal can be resolved | `invalid_grant` |
| Governance Tenant cannot be resolved unambiguously from trusted identity and configuration context | `invalid_grant` |
| Resolved Agent Principal, but no Client Association permits the selected binding for delegated issuance, or delegation is unauthorized | `actor_unauthorized` under Actor Profile, with HTTP 400 |
| Approval requires a downstream lifetime condition that the selected composition cannot enforce, in delegated issuance ({{issuance-authorization}}) | `actor_unauthorized` |
{: title="Identity resolution and delegation errors"}

Subject and agent-resolution credential failures use `invalid_grant`,
as in the example of {{Section 4.3.4.3 of ID-JAG}}, instead of the
default `invalid_request` of {{Section 2.2.2 of RFC8693}}.

Self-acting issuance adds these errors:

| Failure | Error |
|---|---|
| Actor-token parameters present in a self-acting exchange | `invalid_request` |
| Subject token is not byte-identical to the authentication credential in authentication-context resolution | `invalid_grant` |
| Resolved Agent Principal, but no Client Association permits self-acting issuance for the binding | `unauthorized_client`, not `actor_unauthorized`, since no actor is asserted |
| Agent not authorized for the requested RAS or resource | `invalid_target` |
| Agent not authorized for the requested authority | `invalid_scope` |
| Approval requires a downstream lifetime condition that the selected composition cannot enforce ({{issuance-authorization}}) | `invalid_target` |
{: title="Self-acting issuance errors"}

# Grant Redemption at the RAS {#redemption}

## Redemption Request {#redemption-request}

The client redeems either grant at the RAS token endpoint with the JWT
bearer grant type, `urn:ietf:params:oauth:grant-type:jwt-bearer`: an
ID-JAG as in {{Section 4.4 of ID-JAG}}, and a WAG as in {{WAG}}. The
request includes the proof required by {{grant-protection}} and the
applicable access-token protection. These additional parameters are
REQUIRED unless marked OPTIONAL:

| Parameter | Value |
|---|---|
| `resource` | Exactly one parameter whose value equals the grant's resource URI |
| `scope` | OPTIONAL subset of the grant's scope; if omitted, the grant's scope is the upper bound |
{: title="Redemption request parameters"}

The confirmation checks of {{Section 9.8.1.2 of ID-JAG}} apply to this
grant type ({{bound-grant-coordination}}).

## Common Grant Validation {#redemption-common}

Both grants use these checks. {{redemption-validation}} and
{{wag-redemption}} each apply them at the step that names them:

1. **Proof and client:** Enforce {{grant-protection}}, including the
   configured minimum profile even when `cnf` is absent, and
   independently authenticate the client identified by `client_id`.
2. **Authority:**
   * **Resource claim:** Require `resource` to be one URI, encoded as a
     JSON string or a single-element JSON array
     ({{Section 3.1 of ID-JAG}}), and normalize it to that URI. Reject
     a missing or invalid value, an empty array, or a multi-element
     array with `invalid_grant`.
   * **Requested resource:** The RAS MUST reject multiple `resource`
     parameters, or a requested resource different from that URI, with
     `invalid_target` under {{Section 2 of RFC8707}}.
   * **Scope:** Require the grant's `scope` claim to be a non-empty
     string. A supplied request `scope` MUST be a non-empty subset of
     that claim, or the RAS MUST return `invalid_scope`.
   * **Authorization details:** Apply ID-JAG's processing for
     `authorization_details`. Reject the grant with `invalid_grant` if
          its authority extends beyond that resource.

**Grant replay:** For a grant without an enforced grant-level sender
constraint, the RAS MUST reject a grant whose validated (`iss`, `jti`)
it has already accepted while that grant remains acceptable. A proof
used only for client authentication or access-token binding is not such
a constraint. The RAS MAY accept a bound grant again under explicit
policy, each time with a fresh proof that matches its `cnf.jkt`
({{grant-protection}}). This narrows re-submission under
{{Section 4.4.3 of ID-JAG}} for unbound ID-JAGs, and settles for the WAG
the replay question that {{Section 8 of WAG}} leaves open. The retention
rule of {{time-validation}} applies to accepted identifiers.

## Agent Principal Correlation {#agent-correlation}

The Agent Principal identity is the pair of IdP issuer and agent
identifier, carried as (`act.iss`, `act.sub`) in an ID-JAG and as
(`iss`, `sub`) in a WAG. The RAS MUST:

* Resolve that qualified identity independently of any user identity;
  a bare subject, display name, or OAuth client identifier MUST NOT
  replace it.
* Deny authorization that depends on a missing agent record, whether
  that record is provisioned in advance or created just in time under
  {{jit-correlation}}.

A changed Identity Binding or local agent link MUST NOT transfer an
existing delegation to a different agent.

The IdP or an authorized directory connector can provision local agent
principals, keyed by the same pair. No provisioning protocol is required
({{operational-guidance}}). Once deactivation is applied, the RAS
enforces {{applied-changes}}.

### Just-in-Time Correlation {#jit-correlation}

Where the RAS requires a local agent record and none exists for the
qualified pair in the authorized Target Tenant, resource policy MAY
permit the RAS to create one from a validated grant. The policy is
disabled by default and enabled per governing issuer and Target Tenant.
When it applies, the RAS:

* MUST key the created record by that exact pair;
* MUST NOT attach the pair to an existing record by name or other
  descriptive match;
* MUST apply local restrictions, retained revocation state under
  {{applied-changes}}, and local policy before issuance; and
* sets the record's initial eligibility by local policy; a record
  created ineligible denies the triggering request.

Creating the record is correlation, not authorization. Resource policy
still applies, and for delegated access so does the actor gate
({{actor-authorization}}). Creation does not substitute for propagating
disablement, because a grant does not carry the IdP's administrative
status. Without provisioning, the RAS learns of disablement only through
local action or another signal ({{status-changes}}).
{{AGENT-LIFECYCLE}}, not this document, defines provisioning and
reconciliation of a created record for Receivers that conform to it.

## Delegated Redemption: ID-JAG {#idjag-redemption}

### Grant Validation {#redemption-validation}

The RAS MUST perform ID-JAG validation and additionally:

1. **Actor:** Require a single `act` object under Actor Profile's rules,
   with non-empty `iss` and `sub` and no nested `act`. Require `act.iss`
   to equal the ID-JAG issuer and configured trust to authorize
   assertion of that namespace.
2. **Proof and client:** Apply the proof and client checks of
   {{redemption-common}}.
3. **Replay:** Apply the grant replay rule of {{redemption-common}}.
4. **Authority:** Apply the authority checks of {{redemption-common}}.
5. **Local authorization:** Resolve the user under
   {{subject-resolution}} and the Agent Principal actor under
   {{agent-correlation}}, and apply current RAS policy to the
   user/actor relationship under {{actor-authorization}}, client,
   tenant, and resource. A valid grant sets an authority ceiling; it
   does not require issuance.

### User Resolution and Linking {#subject-resolution}

Subject identifiers, tenant relationships, `aud_sub`, `aud_tenant`, and
`sub_id` follow Sections 3.1, 5, and 6 of {{ID-JAG}}, with these
additions. After validating the ID-JAG and its client and proof
bindings, the RAS MUST:

* Resolve exactly one local user in the authorized Target Tenant,
  qualifying `sub` by the validated IdP issuer and tenant relationship;
  IdP and RAS tenant identifiers are not interchangeable.
* Use `aud_sub` only when the IdP is authorized to assert local account
  identifiers for that Target Tenant, and MUST NOT use it to override
  a conflicting approved link.
* Reject conflicting identifiers or multiple local matches without
  retrying a weaker selector or another tenant.
* Resolve `act.iss` and `act.sub` separately under
  {{agent-correlation}}; acting for a user does not link the agent to
  the user's account.

User-account links have these constraints:

* **Authority:** A link between an external user and a local account
  MUST rest on an authoritative association, not on email, username,
  or display-name equality alone.
* **Uniqueness:** Each qualified external identity MUST resolve to at
  most one local account per Target Tenant.
* **Continuity:** A link change MUST NOT transfer an outstanding grant
  or delegation to another user.
* **Failure:** The RAS MUST reject issuance for a disabled user or
  missing, ambiguous, or conflicting resolution ({{errors}}).

### Actor Preservation {#actor-preservation}

The RAS MUST preserve the complete validated
`act` object, including `iss`, `sub`, and any `sub_profile`, in the
access token or its introspection context under
{{Section 3.6.3.2 of ACTOR-PROFILE}}. Preservation applies to JSON
members and values, not to serialization, whitespace, or member order.
The RAS:

* MUST NOT add, remove, or rewrite actor members.
* MUST NOT translate `act.sub` to its local agent-principal identifier
  or replace `act.iss` with its own issuer.

## Self-Acting Redemption: WAG {#wag-redemption}

**Processing:** The RAS MUST:

1. **Grant:** Validate the grant under {{RFC7523}}, consistent with
   {{Section 5 of WAG}}. Require the JWT `typ` header parameter
   `wag+jwt` ({{Section 3.11 of RFC8725}}), so that an ID-JAG or another
   JWT from the same issuer cannot be accepted as a WAG. Require `iss`
   to be a configured governing IdP for the asserted agent namespace.
   Reject a WAG that contains `act` with `invalid_grant`.
2. **Proof and client:** Apply the proof and client checks of
   {{redemption-common}}.
3. **Replay:** Apply the grant replay rule of {{redemption-common}}.
4. **Correlation:** Resolve the pair (`iss`, `sub`) under
   {{agent-correlation}} to one local agent principal in the authorized
   Target Tenant. The RAS MUST have that authorized correlation before
   issuance. For governed agents, this replaces WAG's acceptance of
   previously unseen agents ({{Section 3 of WAG}}). {{jit-correlation}}
   covers just-in-time correlation where resource policy permits it.
5. **Authority:** Apply the authority checks of {{redemption-common}}
   and current RAS policy for the agent, client, tenant, and resource. A
   valid grant sets an authority ceiling; it does not require issuance.
6. **Output:** Issue an access token under {{access-token-response}} and
   {{access-token-protection}}, with the local agent principal as `sub`
   and no `act`. The RAS MUST NOT issue a refresh token for a WAG
   redemption.

## Access Token Issuance and Response {#access-token-response}

After validation and authorization, the RAS MUST issue an access token
with these claims under {{RFC9068}}, or equivalent context through
{{introspection}}:

* **Identity:** For delegated access, the resolved user as subject and
  the validated `act` unchanged under {{actor-preservation}}. For
  self-acting access, the local agent principal as subject and no `act`
  ({{wag-redemption}}).
* **Authority:** Redeemed resource as audience and non-empty authorized
  `scope` (otherwise `invalid_scope`), without broadening authority.
* **Protection:** The binding selected under
  {{access-token-protection}}.
* **Tenant:** By default, the tenant-specific resource URI, which
  becomes the audience under {{Section 3 of RFC8707}}. A deployment MAY
  instead carry the tenant in a configured tenant claim or authoritative
  token context.
* **Authorization details:** Effective `authorization_details`, when
  used, in the JWT claim or introspection member under
  {{Section 9 of RFC9396}}. Narrowing or translating authorization
  MUST NOT discard restrictions in those details or expand the approved
  authority.
* **Expiration:** Within RAS-local lifetime policy under
  {{authorization-lifetime}} and any applicable refresh-authorization
  limit.

**Response:** The response follows {{Section 4.4.2 of ID-JAG}}. The
client MUST reject an output that does not satisfy its configured
protection requirement.

**Instance context:** When the client authenticates at redemption with a
Client Attestation validated under {{INSTANCE}}, the RAS MAY include
instance context for that presenting instance under
{{Section 7 of INSTANCE}}. The RAS MUST NOT copy or remap instance
context from the ID-JAG or WAG. Instance context identifies an execution
of the client; it is not an actor, and it does not replace `act`, `sub`,
or `client_id`.

Whether the response also carries a refresh token, and how that token
is bound and used, follows {{ras-refresh}}.

## Access-Token Protection {#access-token-protection}

**Selection:** The RAS MUST issue a sender-constrained access token
unless the resource is explicitly configured to permit bearer tokens.
The permitted protection is selected through trusted client and
resource configuration before issuance, not by a request flag. A
validation failure MUST NOT trigger a weaker mode.

* **DPoP or bearer:** Where the effective client and resource
  configuration leaves a choice only between DPoP and bearer tokens,
  the RAS MUST bind the access token to the key of a valid DPoP proof
  presented at redemption. Under that configuration, the RAS issues a
  bearer token only when no proof is presented.
* **Mutual TLS:** Where the effective client and resource
  configuration selects mutual TLS, mutual TLS applies regardless of
  any DPoP proof, including the grant proof required below.

A proof never selects a protection that configuration does not permit.

| Selected protection | Access token |
|---|---|
| DPoP | `cnf.jkt` identifies the validated redemption proof key, which also matches the grant binding when present |
| Mutual TLS | `cnf.x5t#S256` identifies the client certificate validated at redemption; the response uses `token_type=Bearer` |
| Bearer | No `cnf` |
{: title="Access-token protection modes"}

For mutual TLS with a bound grant, the client MUST also prove possession
of the grant's DPoP key in the same redemption request. Certificate
possession alone does not redeem the grant. The access token then
carries `cnf.x5t#S256` but not `cnf.jkt`, as {{Section 5 of RFC9449}}
allows for access tokens that are not DPoP-bound. Receipt of the grant
proof does not override the configured access-token protection. A
native mutual-TLS-bound grant is future work
({{excluded-compositions}}).

**Enforcement:** The RAS MUST NOT copy the grant's `cnf` into an access
token whose binding will not be enforced. Clients and APIs MUST NOT
treat a constrained token as an unconstrained bearer token or bypass an
unrecognized confirmation method.

## Opaque Access Tokens and Introspection {#introspection}

The RAS MAY issue an opaque access token instead of a JWT when the API
obtains equivalent context through token introspection {{RFC7662}}.
For an active token:

* **Identity and authority:** The response MUST carry `sub`, `aud`,
  `scope`, `client_id`, and, for delegated access, the validated `act`
  object unchanged, as the `act` introspection member registered by
  {{Section 7.5 of RFC8693}}.
* **Context:** The response MUST preserve the Target Tenant
  representation and any effective `authorization_details` required by
  {{access-token-response}}.
* **Protection:** For a bound token, the response MUST carry `cnf` with
  `jkt` under {{Section 6.2 of RFC9449}} or `x5t#S256` under
  {{Section 3.2 of RFC8705}}.

## Redemption Errors {#redemption-errors}

In addition to {{errors}} and the checks of {{redemption-common}}, the
RAS uses these errors:

| Failure | Error |
|---|---|
| Invalid ID-JAG | `invalid_grant` |
| Unbound grant whose (`iss`, `jti`) the RAS already accepted | `invalid_grant` |
| WAG whose `sub` has no authorized correlation at the RAS | `invalid_grant` |
| Invalid WAG, including one without `typ` `wag+jwt` or one that contains `act` | `invalid_grant` |
{: title="Redemption errors"}

# Access at the Resource Server {#api-processing}

## Profile Applicability {#api-applicability}

This profile defines no in-band discriminator.

* The RAS and API MUST establish profile applicability through trusted
  issuer, client, and resource configuration or authoritative
  token-issuance context.
* The RAS MUST NOT issue governed and ordinary tokens for the same
  client and resource unless the API can distinguish them through
  validated claims or authenticated introspection context.
* The RAS MUST issue tokens such that the API can determine, from
  trusted token context, which adoption profile and acting
  relationship authorized them.

The API MUST reject ambiguous applicability and reject missing or
malformed `act` for a configured governed delegated population.
Self-acting tokens carry no `act` ({{wag-api}}). An ordinary `act`
claim alone does not establish governed issuance.

Separate client registrations, audiences, or issuers for the delegated
and self-acting populations satisfy these rules. The absence of `act`
alone does not: a delegated token lacking `act` would otherwise be
accepted as self-acting.

Conformance does not by itself provide a portable discriminator for
every mixed-token deployment. For example, where one issuer serves
ordinary, delegated, and self-acting access to one API, the RAS can use
a separate client registration or audience for each population, and
the API is configured with that mapping. A deployment that needs one
registration and one audience for several populations needs an
additional bilateral contract.

## Token Validation {#api-validation}

For tokens subject to this profile, the API MUST validate access tokens
under {{RFC9068}}, or obtain the same context under {{introspection}},
and MUST enforce the following requirements:

* **Protection:** Enforce the configured resource mode
  ({{access-token-protection}}) and all token confirmation claims.
  Validate DPoP under {{RFC9449}}, certificate binding under
  {{RFC8705}}, or permitted bearer use under {{RFC6750}}.
* **Authority:** Require non-empty `scope` with its defined type.
  Enforce any effective `authorization_details` under {{RFC9396}}, using
  the API's defined semantics for their combination with scope.
* **Tenant:** Resolve exactly one authorized Target Tenant from token
  context, as represented under {{access-token-response}}. A request
  parameter alone cannot establish it. Verify that it matches the
  tenant of the requested operation. Missing, ambiguous, or conflicting
  tenant context MUST result in denial.

**Introspection caching:** A cached active response MUST NOT be used
beyond `exp` or the freshness limit of the resource's disablement
policy. Without `exp`, the API MUST introspect again for subsequent
requests rather than reuse an active response. This narrows
{{Section 4 of RFC7662}} so cached authorization cannot outlive an
expiration unknown to the API.

**Instance context:** An API that uses instance context applies
{{Section 7.5 of INSTANCE}}. It MUST NOT treat instance context as
satisfying the actor gate or the agent's own permissions. Attributing a
request to an instance requires the sender constraint of
{{Section 7.3 of INSTANCE}}.

## Delegated Access {#api-delegated}

For delegated tokens, the API MUST also:

* **Identity:** Require one `act` object with non-empty `iss` and `sub`
  and no nested `act`. Trust configuration MUST authorize the RAS to
  assert that IdP-qualified agent identity; `act.iss` need not equal the
  access-token issuer.
* **Authority:** Enforce user permissions and the actor gate under
  {{actor-authorization}} and {{Section 8 of ACTOR-PROFILE}}.

## Self-Acting Access {#wag-api}

For self-acting tokens, the API enforces the agent's own permissions
together with the requirements of {{api-validation}}. No actor gate
applies, and a governed self-acting token has no `act`.

## Policy Services {#policy-services}

If the API delegates authorization evaluation to
a policy decision service, it MUST:

* Preserve the distinction between the user, the issuer-qualified
  Agent Principal, and the OAuth client.
* Supply the tenant and token constraints needed to evaluate the
  requested operation.

For a self-acting token, the local principal stands for the Agent
Principal. {{AUTHZEN}} is one optional evaluation interface. This
profile defines no mapping to it. A policy permit does not override the
token's constraints.

## Error Responses {#resource-errors}

Challenges and scope errors use the selected scheme: `DPoP` under
{{Section 7.1 of RFC9449}}, or `Bearer` under {{RFC6750}} for bearer
and mutual-TLS tokens.

| Failure | Response |
|---|---|
| Missing or invalid required actor claims, or unauthorized namespace assertion | HTTP 401, `invalid_token` |
| Missing, ambiguous, or conflicting token tenant context, or a token tenant different from the requested operation's tenant | HTTP 401, `invalid_token` |
| Denial for a valid actor identity | HTTP 403, `actor_unauthorized` under {{Section 8.2 of ACTOR-PROFILE}} |
{: title="Resource server error responses"}

Actor denial MUST NOT use `insufficient_scope`. The API MUST NOT expose
actor-specific rejection details outside the trust domain.

# Continuing Access and Authorization Changes {#continuing-access}

Deployments select a renewal model before scheduling unattended work:

| Mechanism | Conditions |
|---|---|
| Redeem an existing ID-JAG | Grant remains valid, and is bound with RAS policy permitting reuse; an unbound grant is single-use ({{redemption-common}}) |
| Obtain a new ID-JAG | Valid subject credential, current agent-resolution input, and a fresh IdP authorization decision ({{exchange-request}}) |
| RAS refresh (delegated access) | Preserves authorization at the same RAS within its lifetime and policy limits ({{ras-refresh}}) |
| Obtain a new WAG | Current agent-resolution input and a fresh IdP authorization decision ({{wag-issuance}}); a WAG redemption yields no refresh token |
{: title="Renewal mechanisms"}

## Client Token Reuse {#client-token-reuse}

The client associates each cached grant, access token, and refresh
token with its authorized context:

* Agent Principal and, for delegated access, user;
* Governance and Target Tenants;
* OAuth client registrations and target RAS;
* resource, authority, and applicable profile; and
* proof binding.

The client MUST reuse a token or grant only when that context
authorizes the operation. A shared client identifier or matching scope
alone MUST NOT permit reuse across agents, users, or tenants.

The association can use trusted request and configuration context.
Clients need not parse opaque tokens. If the client cannot establish
that association, it MUST obtain a token or grant for the current
context. A credential change alone need not invalidate cached tokens
when the governed principal and authorization context remain the same.

## RAS Refresh Tokens {#ras-refresh}

**Issuance:** The RAS SHOULD NOT issue refresh tokens, retaining
{{Section 4.4.3 of ID-JAG}}, but MAY do so for authorized long-running
work under explicit policy. A WAG redemption never yields a refresh
token ({{wag-redemption}}).

**Binding:** The RAS MUST bind each refresh token to the authenticated
client and apply the first applicable additional sender-binding rule
below. Bindings required by the client-authentication method, such as
{{Section 10.3 of ATTEST}}, apply in every row. Refresh-token rotation
does not replace them.

| Redemption context | Refresh-token requirement |
|---|---|
| Grant contains `cnf.jkt` | Retain the grant's DPoP key binding, regardless of access-token protection |
| Unbound grant; DPoP proof used at redemption | Bind to the validated redemption proof key |
| No DPoP proof; certificate-bound access token | Bind to the validated mutual-TLS certificate |
| Neither DPoP nor certificate binding | Retain any authentication-method binding; if none applies, apply the fallback below |
{: title="Refresh-token sender binding"}

Without DPoP, certificate, or authentication-method binding, the RAS
requires explicit policy permitting client-bound refresh without sender
constraint and uses rotation under {{Section 4.14 of RFC9700}}.

**Resource:** A refresh request MAY include one `resource` parameter
under {{Section 2.2 of RFC8707}} solely to identify the retained
resource. If omitted, the RAS MUST use that resource. If supplied, its
value MUST match the retained resource exactly. The RAS MUST reject
multiple values or a different resource with `invalid_target`.

**Processing:** On every refresh, the RAS MUST:

1. **Client and proof:** Authenticate the bound client and enforce the
   retained authentication-method binding and any additional sender
   binding under RFC 9449 or RFC 8705. Dropping or replacing a
   sender binding requires a new grant.
2. **Authorization context:** Preserve the user, qualified actor, Target
   Tenant, resource, and authorization ceiling, including
   `authorization_details`. Apply current local user and actor policy
   and {{Section 6 of RFC9396}}.
3. **Profile:** Enforce current minimum-profile policy against the
   profile under which the grant was accepted. Reject with
   `invalid_grant` if it no longer qualifies. Adding a proof does not
   upgrade that authorization.
4. **Lifetime:** Enforce a finite absolute authorization expiration set
   at issuance under local policy and an inactivity limit under
   {{RFC9700}}. Rotation, refresh, or repeated redemption of the same
   ID-JAG MUST NOT reset the absolute expiration. Access beyond it
   requires a new ID-JAG and therefore a fresh IdP decision. That new
   ID-JAG starts a new authorization period and leaves the previous
   expiration unchanged.
5. **Output:** Issue access tokens under {{access-token-response}} and
   {{access-token-protection}}, expiring no later than the absolute
   authorization expiration.

## Applied Disablement and Revocation {#applied-changes}

When a principal disablement, correlation removal, or local restriction
is applied at the RAS, the RAS MUST:

* Check current locally applied eligibility at grant redemption and
  refresh, in addition to grant validation and the actor gate.
* Invalidate authorization derived from grants for that qualified agent
  and Target Tenant, including refresh tokens, when the principal is
  disabled or its correlation is removed. The RAS retains enough
  association for this from the time it issues that authorization.
* Not let refresh bypass a principal restriction or restore revoked
  authorization; reactivation permits new decisions only.

# Implementation Considerations {#implementation}

This section is non-normative.

## Federation Configuration {#configuration}

The relationships in {{model}} require trusted configuration, not a
particular storage representation or administrative interface. Existing
workload-federation configuration can supply credential trust and exact
identity selectors. The Agent Principal mapping and separate Client
Association are still required, but no new configuration object types
are prescribed.

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
  mode ({{actor-inputs}}).
* **Target** (IdP administrator): RAS issuer, resources, Target Tenant,
  subject namespace, and authority to assert `aud_sub`.
* **Delegation Authorization** (IdP policy or consent): agent, user,
  client, tenant, RAS, resource, and authority.
* **Agent Authorization** (IdP policy or assignment): the agent's own
  access to the RAS, resource, and authority, for self-acting issuance.
* **Client registration association** (per target RAS): the
  authoritative mapping from the authenticated client to that client's
  registration at the RAS ({{Section 5 of ID-JAG}}). The IdP derives the
  grant's `client_id` from it ({{flow-configuration}}). No companion
  profile provisions it. If the client uses one identifier at both
  servers, that mapping is the identity mapping. A Client ID Metadata
  Document (CIMD) {{CIMD}} Client Identifier URL provides one identifier
  at both servers by construction.

**At the RAS:**

* **Local principals:** local agent principals and user links,
  provisioned or synchronized for RAS and API processing.

**At the client and each authorization server:**

* **Client registration** (the client, at each authorization server):
  registration and authentication keys, or CIMD where supported; each
  server consumes the corresponding metadata.
* **Access-token protection** (RAS and client): protection per resource
  for client, RAS, and API use. `token_type` distinguishes DPoP, but not
  mutual TLS from bearer ({{access-token-protection}}).

**Across the deployment:**

* **Target Tenant binding:** one Target Tenant, configured once. The
  tenant-specific resource URI ({{issuance-request}}), the resource
  domain's provisioning context, and any Shared Signals stream
  ({{AGENT-LIFECYCLE}}) carry it consistently. This profile assumes
  deployments configure these carriers to agree.
* **Applicable profile** (client, IdP, RAS, and resource policy):
  profile and minimum requirements per client, trust relationship, and
  resource, which each role enforces as applicable to it
  ({{discovery}}).

Validation occurs while a request is processed, not when an Agent
Principal, Identity Binding, or Client Association is created. Keys and
metadata may already be held. Their retrieval and refresh follow the
rules of the source that supplies them ({{evidence}},
{{redemption-validation}}, {{metadata}}).

Discovery exposes capabilities, not these authorization decisions
({{discovery}}). Bindings, associations, delegation, and local links
have no discovery mechanism here.

Creating and changing bindings and associations, including imports from
platform registries, is an administrative act outside this profile
({{operational-guidance}}). {{AGENT-MANAGEMENT}} defines a proposed
platform-to-IdP management interface for it.

{{identity-example}} illustrates the shared-client case. {{aws-example}}
applies the model to an AWS Security Token Service (STS) workload
credential.

## Distributed Platforms and Key Use {#distributed-key-use}

A sender-constrained credential requires proofs from its bound key,
through local custody or an authorized signing arrangement. This
document defines no transition to another key ({{key-transition-gap}}),
so bound-grant issuance and redemption require the same key holder.

A DPoP access token is usable only by:

* a broker holding the token's bound key, including one proxying an
  authorized worker request; or
* a worker that holds the same key or obtains request-specific proofs
  from its authorized key holder.

Remote signing interfaces are outside this profile. Remote signing or
shared key custody does not establish an independent worker binding
and expands the trusted computing base.

A control plane and worker that cannot share the grant proof key use
governed agent access instead. The control plane obtains an unbound
grant, and the worker redeems it with its own DPoP proof. That proof
binds the access token to the worker's key ({{grant-protection}}).

# Security Considerations {#security}

The security requirements of the selected credential and grant
specifications, {{RFC9700}}, and {{RFC8725}} apply.

## Adoption Tradeoffs {#baseline-costs}

The profile's security controls carry these deployment costs:

| Requirement | Benefit | Cost |
|---|---|---|
| Dedicated-client resolution as the common mode | Reuses deployed client authentication and registered keys | One Agent Principal per client identity; proves registered-client identity, not independent runtime or workload provenance |
| Optional native JWT-SVID input | Reuses SPIFFE issuance, client authentication, and trust-domain validation | Bearer evidence; issuer-bound presenter proof needs another supported input |
| Bound profile: DPoP at both token endpoints; grant bound to the grant proof key | A stolen ID-JAG cannot be redeemed without the key | Every client holds and proves a key |
| Bound grants: same key for issuance and redemption | No key-transition protocol to secure | A broker that obtains bound grants also redeems them ({{distributed-key-use}}) |
| Access-token context as JWT claims or introspection ({{introspection}}) | The API reads `act`, `scope`, and `cnf` from the token or authenticated introspection | Opaque tokens add an introspection round trip and a freshness policy |
| Actor-aware API processing | The actor gate is enforced where access happens | APIs parse `act` and consult the gate on delegated paths |
| Sender-constrained access tokens by default | Token theft is contained | Resources without DPoP or mutual TLS need explicit configuration for bearer use |
{: title="Adoption tradeoffs"}

Governed agent access without grant binding adds agent authorization
to existing enterprise access. It still leaves a stolen grant
redeemable by an attacker who can authenticate as the grant's
designated client, particularly a shared client. Single use
({{redemption-common}}) limits such a grant to one redemption; it does
not prevent the first. Binding only the
resulting access token
does not prevent that redemption. Explicit acceptance policy, short
grant lifetimes, credential confidentiality, and the no-fallback rules
in {{discovery}} limit this exposure. They do not provide proof of
possession of an issuer-authorized grant key.

## Credential and Token Confusion

Credential classification and mutually exclusive validation follow
{{actor-inputs}} and {{Section 3.12 of RFC8725}}. Signature validity
alone establishes neither a credential's intended use nor permission to
resolve or exercise an agent.

Both grants are JWTs redeemed with the same grant type, so the RAS tells
them apart by explicit type: `oauth-id-jag+jwt` for an ID-JAG
({{Section 3.1 of ID-JAG}}) and `wag+jwt` for a WAG
({{wag-redemption}}).

## Dedicated-Client Key Compromise

In dedicated-client resolution, compromise of the client's
authentication key permits an attacker to authenticate as the resolution
source for its bound Agent Principal. No independent workload credential
is required.

For delegated access, the attacker still needs an acceptable user
subject credential and has to satisfy Client Association and delegation
authorization. For self-acting access, the key alone suffices wherever
a Client Association and Agent Authorization already permit the client.

Grant binding does not prevent this impersonation at issuance. Unless
policy independently constrains the grant proof key, the attacker can
obtain a grant bound to an attacker-controlled DPoP key. The proof
protects that grant against theft; it does not establish legitimate
runtime provenance.

Runtime or workload provenance requires an agent-resolution input whose
verified claims and trusted issuance policy establish it.
Dedicated-client resolution alone does not. A normalized Agent Principal
identity does not imply uniform runtime assurance. Authentication-key
revocation and binding disablement affect subsequent issuance under
{{issuance-authorization}} and {{status-changes}}.

## Credential Authority and Key Isolation

A compromised credential authority can assert identities within its
trusted scope. Exact bindings, tenant boundaries, and issuer-scoped key
lookup ({{time-validation}}) limit that scope. Neither `kid` alone nor a
union of unrelated issuers' keys establishes the assertion's source.

A holder of a shared private key can present any credential issued for
that key. Agent isolation therefore depends on issuance controls and
key custody as well as identity mapping. Sharing the grant proof key
across components widens its exposure ({{distributed-key-use}}).

## Authorization Changes and Revocation {#status-changes}

Cross-system disablement needs a provisioning and signaling contract
({{lifecycle-gap}}). Issued authority can outlast disablement:

* Without a signal or online check, issued tokens remain usable until
  expiration.
* Without a bound on propagation, the remaining lifetime of existing
  grants, refresh authorizations, and access tokens determines the
  possible continuation window. The five-minute ID-JAG recommendation is
  not a global stopping guarantee.
* Even after disablement is applied, cached introspection results or
  offline JWTs can remain usable until their acceptance limits.
* Current active state alone cannot recover a missed
  disable-and-reenable transition or invalidate every old grant.

Deployments benefit from documenting their maximum disablement delay,
including propagation and cache freshness.

Administrative actions have different effects, and none is evidence
that another has occurred. The following table summarizes each effect
after the change is applied at the enforcing server; it defines no new
propagation mechanism:

| Administrative action | Effect on new authorization | Previously issued authority |
|---|---|---|
| Terminate an execution | Stops that execution; does not disable the agent or its approved relationships | Credentials and tokens remain subject to their validation and revocation rules |
| Suspend one client instance ({{INSTANCE}}) | That instance fails authentication where the suspension is enforced; the agent's other bindings and instances continue | Revocation and introspection follow {{Section 6.3 of INSTANCE}} |
| Disable one Identity Binding at the IdP | No new grant through that binding; other enabled bindings remain usable with their own Client Associations | Grants and RAS tokens continue until separately revoked or expired |
| Remove a Client Association at the IdP | No new grant through that permission; the Identity Binding can remain valid | Grants and RAS tokens continue until separately revoked or expired |
| Disable the Agent Principal at the IdP | No new grant for that agent, regardless of binding or client | RAS issuance and refresh stop once the RAS receives and applies the change |
| Withdraw the user's delegation at the IdP | No new delegated grant for that delegation | RAS authorization can continue until revocation is applied or its absolute expiration |
| Disable the local agent or user at the RAS | No new access tokens or refresh for that principal | API access stops when its actor/user policy observes the change, introspection reports inactivity, or the token expires |
{: title="Effects of administrative changes"}

The RAS requirements for applied changes are in {{applied-changes}}.
The provisioning that feeds them is a deployment choice.

The withdrawal of a delegation, Identity Binding, or Client Association
can be propagated to derived authorization only when the IdP has
retained the identifiers of the ID-JAGs it issued under that
relationship. The agent identity alone cannot identify that set.
Propagation can use grant-derived revocation in {{AGENT-LIFECYCLE}} or
an equivalent signal.

Account-linking errors can grant access to another user's account.
{{idp-subject-resolution}} and {{subject-resolution}} state the checks
required before authorization.
Proof of key possession does not establish account ownership, and link
removal does not revoke outstanding tokens.

## External Approval {#external-approval}

External approval MUST NOT replace credential validation, identity
resolution, Client Association, or delegation authorization. A
resource-local approval can satisfy an additional policy condition
within the presented token's authority. It MUST NOT expand that
authority or override token validity or tenant restrictions. Access
beyond that authority requires new authorization through an applicable
protocol. Asynchronous approval composition is deferred under
{{excluded-compositions}}.

# Privacy Considerations {#privacy}

A stable agent identifier can correlate activity across resources,
users, and instances. Preserving the same issuer-qualified actor across
delegated users supports audit but lets a resource domain link the
activity of one Agent Principal for different users.

Issuers SHOULD disclose only the agent attributes needed for the
authorized purpose. User and agent context remain separate when the
agent acts for a user. The mapping in {{actor-construction}} keeps
external workload identifiers out of the ID-JAG. This profile does not
define pairwise actor translation.

Instance context adds correlation of individual executions. Its
identifiers are scoped per receiver and per consumer under
{{Section 10 of INSTANCE}}.

# IANA Considerations {#iana}

## ID-JAG Grant Profile URIs

This document requests registration in the "OAuth URI" registry
established by {{RFC6755}}:

* URN: `urn:ietf:params:oauth:grant-profile:id-jag-agent-federation`
* Common Name: ID-JAG Bound Governed Agent Access grant profile
* Change Controller: IETF
* Specification Document: {{metadata}} of this document.

This document also requests:

* URN: `urn:ietf:params:oauth:grant-profile:id-jag-governed-agent`
* Common Name: ID-JAG Governed Agent Access grant profile
* Change Controller: IETF
* Specification Document: {{metadata}} of this document.

## WAG Grant Profile URIs

This document also requests:

* URN: `urn:ietf:params:oauth:grant-profile:wag-agent-federation`
* Common Name: WAG Bound Governed Agent Access grant profile
* Change Controller: IETF
* Specification Document: {{metadata}} of this document.

* URN: `urn:ietf:params:oauth:grant-profile:wag-governed-agent`
* Common Name: WAG Governed Agent Access grant profile
* Change Controller: IETF
* Specification Document: {{metadata}} of this document.

This document does not request registration of the provisional WAG
token type `urn:ietf:params:oauth:token-type:wag` or JWT type
`wag+jwt`. {{WAG}} does not yet define either; registration awaits
coordination ({{wag-gaps}}).

--- back

# Agent Resolution Input Profiles {#input-profiles}

| Input | Qualified identity | Reference |
|---|---|---|
| Dedicated client | Trusted assertion issuer and exact client `sub` | {{client-assertion-input}} |
| Existing platform JWT | Approved issuer, exact `sub`, and configured additional selectors | {{imported-jwt-input}} |
| SPIFFE JWT-SVID | Approved trust domain and exact SPIFFE ID in `sub` | {{jwt-svid-input}} |
| SPIFFE WIT-SVID | Approved trust domain and exact SPIFFE ID in the validated `sub` | {{spiffe-input}} |
| SPIFFE X.509-SVID | Approved trust domain and exact SPIFFE ID in the certificate's URI Subject Alternative Name | {{spiffe-input}} |
| Client Attestation | Trusted attester and validated `sub`; for a managed installation, also the IdP Receiver Scope and `client_instance_id` | {{agent-evidence}} |
{: title="Agent-resolution inputs and qualified identities"}

The IdP client-registration context qualifies a dedicated client's
identity. For Client Attestation, `sub` identifies the OAuth client, and
the client-to-agent mapping is explicit. The existing platform JWT uses
presented-evidence mode; every other input uses authentication-context
mode.

## Required Input Profiles {#mandatory-input-profiles}

This normative appendix defines the two inputs that {{scope}}
requires: dedicated-client identity, mandatory to implement, and the
existing platform JWT, required for a claim of generic shared-client
interoperability. Each
satisfies the interface contract of {{evidence}}.

### Dedicated Client Identity {#client-assertion-input}

In this explicitly configured mode, the IdP resolves the client identity
validated during client authentication to its explicitly bound Agent
Principal. No separate platform-issued credential is needed. The
assertion authenticates the client and is not independent workload
evidence ({{dedicated-client-coordination}}). This mode does not
distinguish agents behind one shared client identity. Such a client MUST
use a supported workload-identity input that distinguishes its agents
({{imported-jwt-input}}). {{client-assertion-example}} illustrates this
input.

* **Presentation:** An asymmetrically signed `client_assertion` under
  {{RFC7523}}. For `private_key_jwt`, the common method, the assertion
  issuer and subject are the client's registered identifier
  (Section 9 of {{OPENID}}); other configured asymmetric RFC 7523
  methods MAY be supported.
* **Validation:** The IdP authenticates the client under
  {{Section 3 of RFC7523}} and its configured authentication method.
  It MUST use verification keys authorized for that client and
  assertion issuer. Assertion-supplied keys or issuer claims MUST NOT
  establish trust.
* **Resolution:** The IdP MUST resolve the exact validated (`iss`,
  `sub`) in its client-registration context under {{identity-binding}}.
  An additional agent claim in a self-signed client assertion MUST NOT
  select another Agent Principal under this input.
* **Audience:** RFC 7523 client authentication at the IdP and the RAS
  MUST follow {{Section 4 of RFC7523bis}}: `aud` has the authorization
  server's issuer identifier as its sole value, never its token endpoint
  URL, and the server rejects any other audience. This profile adds no
  alternative audience configuration and leaves other credential
  classes' audience rules unchanged.
* **Proof:** Assertion signing neither binds the grant to the signing
  key nor establishes an attested runtime identity. Grant proof
  processing follows {{grant-protection}} independently, and the DPoP
  key MAY differ from the client-authentication key. An assertion
  carrying `cnf` MUST NOT be accepted unless its configured
  authentication method defines and validates the corresponding proof.
* **Replay:** These rules narrow the base specifications and prohibit
  negotiated assertion reuse. The assertion MUST contain a `jti`. The
  IdP and the RAS MUST each reject reuse in another request while the
  assertion remains acceptable; a reused assertion fails client
  authentication. Replay identifiers MUST be qualified by the validated
  issuer and client.
* **Retry:** For any retry of a dedicated-client token request at either
  server, including after a `use_dpop_nonce` challenge under
  {{Section 8 of RFC9449}}, the client MUST generate a new
  `client_assertion` with a fresh `jti`. For a nonce retry, the client
  MUST also generate a fresh DPoP proof containing the supplied nonce
  while retaining the grant proof key. A new DPoP proof alone is not
  enough, because the server may already have consumed the previous
  assertion during authentication.

### Existing Platform JWT {#imported-jwt-input}

This common shared-client input accepts existing signed platform JWTs as
issued, with no new media type or reissuance. {{scope}} states when it
is required, and {{aws-example}} gives an AWS STS example. The IdP MUST
accept a platform JWT only when its issuer, credential class, and the
authenticated client are explicitly configured together. Credential
classification and rejection follow {{actor-inputs}}.

* **Configuration:** Configuration MUST also specify:
  * the credential class: the rule distinguishing workload credentials
    from user, management-API, or other tokens of the same issuer,
    namely an explicit `typ`, a dedicated issuer, or an accepted
    audience combined with exact selectors;
  * approved keys or an approved HTTPS JWK Set URI under {{RFC7517}},
    retrieved with server authentication;
  * the issuer's permitted asymmetric algorithms;
  * the effective evidence deadline, the permitted clock skew for a
    future issuance time, and any maximum age; and
  * the audiences that authorize presentation to this IdP as workload
    evidence.

* **Presentation:** `actor_token` in delegated issuance and
  `subject_token` in self-acting issuance ({{wag-request}}); the client
  authenticates separately with a configured method. An accepted JWT
  MUST NOT be treated as OAuth client authentication unless it
  independently satisfies a configured client authentication method.
* **Validation:** The IdP MUST validate the JWT under {{RFC7519}},
  {{RFC8725}}, and the configured credential profile. Keys or URLs in
  the JWT MUST NOT override the approved key source. The IdP MUST
  determine the effective evidence deadline from `exp`, a configured
  maximum age measured from an authenticated issuance time (such as
  `iat`), or both. When both apply, the earlier deadline governs.
  Receipt time MUST NOT substitute for issuance time. The deadline
  bounds grant expiration ({{grant-common}}).
* **Resolution:** The Identity Binding MUST specify an exact issuer and
  `sub`. It MAY require additional string values from the JWT Claims
  Set, including nested claims. Selectors constrain identity
  resolution, not the administrative configuration format. Additional
  selectors MUST use the JSON Pointer string representation in
  {{Section 5 of RFC6901}}, evaluated from the Claims Set root under
  {{Section 4 of RFC6901}}:
  * Every selector MUST resolve unambiguously to a string equal to its
    configured value, without type conversion, case folding, or Unicode
    normalization. Missing paths, evaluation errors, non-string values,
    or unequal values MUST prevent that binding from matching.
  * Selectors MUST NOT use wildcard, prefix, or pattern matching, and
    MUST NOT replace the exact issuer and `sub` checks.
  * A caller-controlled claim MUST NOT distinguish agents unless trusted
    issuance policy constrains its values to identities the caller is
    authorized to assert. A signature alone does not establish that
    authority for request tags or other caller-supplied attributes.
* **Audience:** The configured audiences authorize presentation to this
  IdP as workload evidence (**Configuration**). The IdP MUST reject a
  platform JWT whose `aud` is absent or contains none of them.
* **Proof:** This profile defines no new proof mechanism. If `cnf` is
  present, the IdP MUST enforce its proof mechanism and MUST NOT give
  the credential bearer treatment when the binding is unsupported. A
  deployment accepting key-bound JWTs MUST configure their proof
  validation and any required relationship to the grant proof key.
  Bearer platform JWTs fall under {{credential-requirements}}.
* **Failure:** The IdP MUST reject evidence with `invalid_grant` if a
  required time limit cannot be evaluated or no effective evidence
  deadline can be determined.

## Optional Input Profiles {#optional-input-profiles}

This normative appendix defines the optional inputs listed in
{{optional-inputs}}. Each satisfies the interface contract of
{{evidence}}, resolves from authentication context with actor-token
parameters omitted ({{actor-inputs}}), and requires trusted
configuration under {{configuration}}.

### SPIFFE JWT-SVID {#jwt-svid-input}

This OPTIONAL input identifies workloads independently of the OAuth
client identifier, including multiple agents behind a shared client.

* **Presentation:** Client authentication by `client_assertion` with
  `client_assertion_type`
  `urn:ietf:params:oauth:client-assertion-type:jwt-spiffe`.
* **Validation:** Before resolving the agent, the IdP MUST apply
  {{Section 3.1 of SPIFFE-OAUTH}}, including the assertion type, and
  {{Section 5 of SPIFFE-OAUTH}} and {{Section 6 of SPIFFE-OAUTH}} for
  trust establishment and key distribution. It MUST also verify the
  signature, before resolving the agent, with keys authorized for the
  SPIFFE ID's trust domain. An
  optional `iss` MUST NOT select another trust domain or key authority.
* **Resolution:** The IdP MUST resolve the exact SPIFFE ID in the
  validated `sub` under {{identity-binding}}. The SPIFFE ID's
  association with the authenticated client is an authentication check,
  not an Identity Binding or Client Association.
* **Proof:** A JWT-SVID is bearer evidence: DPoP, when used, binds the
  issued grant to the grant proof key, not the JWT-SVID to its
  presenter. A policy requiring issuer-bound presenter proof MUST reject
  this input rather than treat DPoP as that proof
  ({{credential-requirements}}).

### Client Attestation {#agent-evidence}

This OPTIONAL input maps the attested OAuth client identity explicitly
to one Agent Principal. It relies on a trusted attester's attestation of
the client identity and confirmation key, not a registered client key.
It establishes runtime or workload provenance only as far as verified
attestation claims and the attester's trusted issuance policy support.
It does not distinguish agents behind a shared client, except through
the managed-installation binding below. Otherwise those agents need
distinct workload evidence, such as a JWT-SVID or platform JWT.

* **Presentation:** Client authentication with the configured {{ATTEST}}
  method.
* **Validation:** The IdP MUST validate the attestation and proof under
  {{ATTEST}} before resolving the agent. It MUST identify the attester
  unambiguously from the trusted verification key and configured
  attester-to-client associations. An `iss`, when present, MUST match
  that attester.
* **Attester endorsement:** The IdP MAY derive the attester-to-client
  association from an endorsement it accepts under
  {{Section 2.1 of ATTESTER-ENDORSEMENT}}. An endorsement MUST NOT
  create or change an Identity Binding or Client Association. Because
  the binding names the attester, a newly endorsed attester resolves no
  Agent Principal until an Identity Binding names it. An endorsement
  accepted under that policy is not client metadata acting by itself
  ({{inputs}}).
* **Resolution:** The IdP MUST resolve the trusted attester and the
  validated `sub` through an approved Identity Binding
  ({{identity-binding}}).
* **Managed installation:** Where agents share one OAuth client, a
  Client Attestation carrying `client_instance_id` under {{INSTANCE}}
  MAY resolve the agent instead. The IdP MUST accept it only from an
  attester configured to assign that identifier at Installation
  granularity ({{Section 1.1 of INSTANCE}}) under the continuity rules
  of {{Section 6 of INSTANCE}}. The Identity Binding names the exact
  attester, client (`sub`), IdP Receiver Scope, and
  `client_instance_id`. Trusted configuration for the client selects
  client-level or installation-level resolution. Attestation claims MUST
  NOT select the level, and a failed match MUST NOT fall back to the
  other level. A new enrollment yields a new identifier that needs its
  own approved Identity Binding. The IdP MUST NOT infer continuity
  across identifiers or attesters.
* **Proof:** With `attest_jwt_client_auth`, any grant proof key MUST
  match the attestation's confirmation key. This narrows the allowance
  in {{Section 5.2 of ATTEST}} for a separate DPoP key. With
  `attest_jwt_client_auth_dpop`, one DPoP proof serves both roles. Key
  retention follows {{resolution-key-lifecycle}}.

With {{INSTANCE}}, instance keys differ per receiver scope
({{Section 4.1 of INSTANCE}}). A bound grant carries the IdP-scoped key.
A client that also authenticates to the RAS with a Client Attestation
therefore uses `attest_jwt_client_auth` there and proves the grant key
with a separate DPoP proof, unless the IdP and RAS share a receiver
scope.

### SPIFFE WIT-SVID and X.509-SVID Resolution {#spiffe-input}

These OPTIONAL inputs resolve the SPIFFE ID validated during OAuth
client authentication for this token request, in the SVID class that the
client and IdP configure. General non-SPIFFE Workload Identity Token
(WIT) and Workload Identity Certificate (WIC) inputs of {{WIT}} are
excluded ({{excluded-compositions}}). One shared SPIFFE ID cannot
distinguish independently governed agents. Either input proves control
of a credential-bound key. Assurance about a particular runtime or
execution depends on the credential authority's issuance rules and
identity granularity. {{svid-context-example}} illustrates both inputs.

#### WIT-SVID

* **Presentation:** The WIT-SVID in `OAuth-Client-Attestation`, with its
  proof in `OAuth-Client-Attestation-PoP`.
* **Validation:** The IdP MUST apply {{Section 3.3 of SPIFFE-OAUTH}} and
  {{WIT}}, including their client-identifier association, trust,
  validity, and proof requirements. It MUST require `typ=wit+jwt`. It
  MUST validate possession of the key in `cnf.jwk` through the Client
  Attestation PoP JWT. A WIT-SVID MUST NOT be accepted as bearer
  evidence. Its optional `iss` MUST NOT select a different trust domain
  or key authority.
* **Resolution:** The IdP MUST resolve the approved trust domain and
  exact SPIFFE ID in the validated `sub` through {{identity-binding}}.
* **Proof:** When DPoP is used at issuance, its key MUST match the
  WIT-SVID's `cnf.jwk`. The IdP MUST compare the JWK thumbprints of the
  DPoP key and `cnf.jwk` as used in {{RFC9449}} and MUST reject a
  mismatch with `invalid_grant`.
  This carries the WIT-endorsed key into the grant binding; the Client
  Attestation PoP JWT remains required. Key retention follows
  {{resolution-key-lifecycle}}.

#### X.509-SVID

* **Presentation:** The client certificate on the mutual-TLS connection
  carrying the token request.
* **Validation:** The IdP MUST apply {{Section 3.2 of SPIFFE-OAUTH}} and
  {{RFC8705}} to the certificate and proof established by mutual TLS
  for this request. This includes their client-identifier association,
  trust, validity, and proof requirements. A certificate supplied only
  in a request parameter or an untrusted forwarding header MUST NOT
  establish the workload identity, and the request then fails client
  authentication. TLS termination follows {{Section 6.5 of RFC8705}}.
* **Resolution:** The IdP MUST resolve the approved trust domain and
  exact SPIFFE ID in the certificate's URI Subject Alternative Name
  through {{identity-binding}}.
* **Proof:** A DPoP grant proof key, when required, is proven on the
  same token request. It MAY differ from the certificate key, because
  mutual TLS can terminate separately from the component generating DPoP
  proofs. The certificate does not endorse the DPoP key; the
  authenticated request associates it with this issuance, and the grant
  uses `cnf.jkt`, not certificate confirmation.

### Resolution-Key Lifecycle {#resolution-key-lifecycle}

When the resolution key is also the grant proof key, replacing it does
not rebind an outstanding grant, access token, or refresh token. This
is the case for WIT-SVID or Client Attestation when DPoP is used.
Continued use requires retaining the corresponding proof key.
Otherwise, the client obtains a new grant with the replacement key and
new RAS authorization. Any subject-credential binding still applies and
may require a new subject credential. Key migration is deferred
({{key-transition-gap}}).

# Worked Exchanges and Input Variants {#examples}

## Walkthrough: Dedicated Client {#walkthrough}

This non-normative walkthrough exercises the common dedicated-client
input, bound governed agent access, and DPoP-protected API access. Key
coordinates, thumbprints, token hashes, and compact JWTs are labeled
placeholders, not cryptographic test vectors.

The dedicated client is `analysis-client` at the IdP and `analysis-api`
at the RAS. In the IdP's client-registration context, an Identity
Binding maps (`analysis-client`, `analysis-client`) to `agent-42`.
A separate Client Association permits use of that binding, and
delegation authorization permits the agent to act for Alice.
Alice's ID Token has audience `analysis-client`; subject resolution
produces `alice-ras` for the RAS and `user-108` at the resource.

The exchange starts at 12:01:03 UTC on September 17, 2026. The shared
walkthrough in {{AGENT-LIFECYCLE}} uses the same identities, Target
Tenant `acme-data`, and grant issuance time to add SCIM provisioning,
introspection, disablement, and reactivation. This document alone does
not imply those checks.

### Dedicated Client Authentication {#client-assertion-example}

The client signs this illustrative assertion payload with its
registered private key, using an `RS256` header and the registered
key identifier:

~~~ json
{
  "iss": "analysis-client",
  "sub": "analysis-client",
  "aud": "https://idp.example/",
  "iat": 1789646463,
  "exp": 1789646523,
  "jti": "analysis-auth-1"
}
~~~

`CLIENT_ASSERTION` denotes the signed compact JWT, presented only in
`client_assertion` under {{client-assertion-input}}. The Identity
Binding resolves the authenticated client to `agent-42`. No actor-token
parameters are sent, and the assertion supplies no independent workload
identity. The assertion expires after 60 seconds but does not cap the
grant's 300-second lifetime. Alice's ID Token remains valid for at least
that period.

### Exchange Request and Response

The HTTP examples show application parameters and relevant headers;
framing headers are omitted. Bodies are line-wrapped for display;
concatenate their lines before sending.

`IDP_DPOP_PROOF` proves a separate grant key K, with `htm=POST`,
`htu=https://idp.example/token`, a current `iat`, a unique `jti`, and a
server nonce if challenged. `JKT_K` denotes K's JWK thumbprint. The same
key is proven at redemption.

~~~ http-message
POST /token HTTP/1.1
Host: idp.example
Content-Type: application/x-www-form-urlencoded
DPoP: IDP_DPOP_PROOF

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Atoken-exchange
&requested_token_type=urn%3Aietf%3Aparams%3Aoauth
%3Atoken-type%3Aid-jag
&client_id=analysis-client
&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth
%3Aclient-assertion-type%3Ajwt-bearer
&client_assertion=CLIENT_ASSERTION
&subject_token=ALICE_ID_TOKEN_FOR_ANALYSIS_CLIENT
&subject_token_type=urn%3Aietf%3Aparams%3Aoauth
%3Atoken-type%3Aid_token
&audience=https%3A%2F%2Fras.example%2F
&resource=https%3A%2F%2Fapi.example%2Ftenants%2Facme-data%2F
&scope=files.read
~~~

~~~ http-message
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store
Pragma: no-cache

{
  "access_token": "ID_JAG",
  "issued_token_type": "urn:ietf:params:oauth:token-type:id-jag",
  "token_type": "N_A",
  "expires_in": 300,
  "scope": "files.read"
}
~~~

The decoded grant header uses `alg=RS256`, `typ=oauth-id-jag+jwt`, and
an IdP signing-key identifier. Its payload includes:

~~~ json
{
  "iss": "https://idp.example/",
  "sub": "alice-ras",
  "aud": "https://ras.example/",
  "iat": 1789646463,
  "exp": 1789646763,
  "jti": "grant-1",
  "client_id": "analysis-api",
  "resource": "https://api.example/tenants/acme-data/",
  "scope": "files.read",
  "act": {"iss":"https://idp.example/", "sub":"agent-42"},
  "cnf": {"jkt":"JKT_K"}
}
~~~

This example uses Actor Profile's unclassified-actor processing and
omits the recommended `sub_profile`. The configured issuer and client
relationships resolve the Governance Tenant; the tenant-specific
resource identifies Target Tenant `acme-data`.

### Redemption Request and Response {#redemption-example}

`RAS_CLIENT_ASSERTION` authenticates the corresponding RAS client with
`iss=sub=analysis-api`, `aud=https://ras.example/`, a short expiration,
its own `jti`, and that registration's signing key. `RAS_DPOP_PROOF` is
a fresh proof using K, with `htm=POST` and
`htu=https://ras.example/token`.

~~~ http-message
POST /token HTTP/1.1
Host: ras.example
Content-Type: application/x-www-form-urlencoded
DPoP: RAS_DPOP_PROOF

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer
&client_id=analysis-api
&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth
%3Aclient-assertion-type%3Ajwt-bearer
&client_assertion=RAS_CLIENT_ASSERTION
&assertion=ID_JAG
&resource=https%3A%2F%2Fapi.example%2Ftenants%2Facme-data%2F
~~~

For the configured DPoP-protected resource, the response is:

~~~ http-message
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store
Pragma: no-cache

{
  "access_token": "API_ACCESS_TOKEN",
  "token_type": "DPoP",
  "expires_in": 600,
  "scope": "files.read"
}
~~~

The access token uses `typ=at+jwt` and the following decoded payload:

~~~ json
{
  "iss": "https://ras.example/",
  "sub": "user-108",
  "aud": "https://api.example/tenants/acme-data/",
  "iat": 1789646464,
  "exp": 1789647064,
  "jti": "access-1",
  "client_id": "analysis-api",
  "scope": "files.read",
  "act": {"iss":"https://idp.example/", "sub":"agent-42"},
  "cnf": {"jkt":"JKT_K"}
}
~~~

The RAS translates Alice's subject and preserves the Agent Principal
actor, which the dedicated client identifier does not replace. The
access token is bound to K, the key used at both token endpoints.

### Protected Resource Request

The client presents the access token and a new proof signed with K:

~~~ http-message
GET /tenants/acme-data/files/report-7 HTTP/1.1
Host: api.example
Authorization: DPoP API_ACCESS_TOKEN
DPoP: API_DPOP_PROOF
~~~

The decoded proof header and payload are:

~~~ json
{
  "typ": "dpop+jwt",
  "alg": "ES256",
  "jwk": {
    "kty": "EC",
    "crv": "P-256",
    "x": "K_X",
    "y": "K_Y"
  }
}
~~~

~~~ json
{
  "jti": "api-proof-1",
  "htm": "GET",
  "htu": "https://api.example/tenants/acme-data/files/report-7",
  "iat": 1789646468,
  "ath": "ATH_ACCESS_TOKEN"
}
~~~

`K_X` and `K_Y` are K's base64url-encoded public coordinates.
`ATH_ACCESS_TOKEN` is the unpadded base64url-encoded SHA-256 hash of the
ASCII access-token value ({{Section 4.2 of RFC9449}}). If the API
requires a nonce, the proof also includes it.

The API validates the token and proof, including `htm`, `htu`, `ath`,
and the match between the proof key and `cnf.jkt`. It then enforces the
user permissions, actor gate, and tenant-specific audience. The client
caches this token for Alice and `agent-42` in `acme-data`
({{client-token-reuse}}).

For explicitly configured bearer access, the response instead uses
`token_type=Bearer`, the access token has no `cnf`, and the API request
uses `Authorization: Bearer API_ACCESS_TOKEN` without a DPoP proof. DPoP
at grant issuance and redemption remains required in this bound profile.

### Intermediate Adoption Variant

To adopt governed agent access, the parties instead configure
`urn:ietf:params:oauth:grant-profile:id-jag-governed-agent` and
explicitly permit grants without sender constraint. With bearer access
also permitted for this resource, the preceding messages change only as
follows:

| Message | Change |
|---|---|
| Exchange request and ID-JAG | Omit the DPoP header; the issued grant has no `cnf` |
| Redemption request | Omit the DPoP header; retain client authentication and all request parameters |
| Access-token response and API request | Use the bearer variant above |
{: title="Message changes for governed agent access"}

The client assertion, Identity Binding, Client Association, user and
actor identities, scope, tenant checks, and actor gate are unchanged. An
unbound grant can instead obtain a DPoP-bound access token by presenting
a valid proof at redemption ({{grant-protection}}).

### Renewal and Negative Tests

The redemption response contains no refresh token; after the access
token expires, the client obtains a new ID-JAG ({{continuing-access}}).

Each case below changes the walkthrough, or the named variant, as
stated; all other credentials, proofs, and policy checks succeed. The
last column is the required result. Token endpoint errors follow
{{errors}}; API errors follow {{resource-errors}}.

| Changed condition | Checked by | Required result |
|---|---|---|
| Nonce retry with a fresh DPoP proof reuses the consumed `analysis-auth-1` assertion | IdP | HTTP 400, `invalid_client`; regenerate `client_assertion` |
| Identity Binding disabled | IdP | HTTP 400, `invalid_grant`; successful authentication does not resolve the agent |
| Client Association for `analysis-client` disabled | IdP | HTTP 400, `actor_unauthorized`; no ID-JAG |
| Bound governed agent access required; grant has no `cnf` | RAS | HTTP 400, `invalid_grant`; no fallback to governed agent access |
| Grant has `cnf.jkt`; redemption omits the proof | RAS | HTTP 400, `invalid_grant`; grant binding enforced |
| Access token used in another tenant where Alice and the agent also have permissions, with a fresh valid proof | API | HTTP 401, `invalid_token`; no operation performed |
| Governed agent access: the grant has no `cnf`, was redeemed once with a DPoP proof, and is presented again with a fresh proof by another key | RAS | HTTP 400, `invalid_grant`; an access-token proof does not make an unbound grant reusable ({{redemption-common}}) |
| Self-acting variant ({{wag-example}}) under governed agent access: the WAG has no `cnf`, was redeemed once, and is presented again | RAS | HTTP 400, `invalid_grant`; an unbound WAG is single-use ({{redemption-common}}) |
| Delegated access token without `act`, presented to an API configured for the governed delegated population | API | HTTP 401, `invalid_token`; a missing `act` does not make the token self-acting ({{api-applicability}}) |
| Shared-client variant ({{shared-client-example}}): the platform client holds a token for `agent-42` and starts an operation for another agent with the same scope | Client | Obtains a grant for that agent; a matching `client_id` and scope do not permit reuse ({{client-token-reuse}}) |
| Platform JWT variant ({{aws-example}}): the platform JWT fails validation | IdP | HTTP 400, `invalid_grant`; no retry from authentication context or under another credential class ({{actor-inputs}}) |
{: title="Negative test cases"}

The grant binding is enforced regardless of access-token protection,
even when the resource accepts bearer access tokens or policy permits
unbound grants.

### Self-Acting Variant {#wag-example}

This non-normative variant issues a WAG to the same dedicated client
under {{wag-issuance}}. The client authenticates with a fresh assertion,
`analysis-auth-3`, and repeats the same compact JWT as the subject token
as {{wag-request}} defines:

~~~ http-message
POST /token HTTP/1.1
Host: idp.example
Content-Type: application/x-www-form-urlencoded
DPoP: IDP_DPOP_PROOF

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Atoken-exchange
&requested_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type%3Awag
&client_id=analysis-client
&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth
%3Aclient-assertion-type%3Ajwt-bearer
&client_assertion=CLIENT_ASSERTION_3
&subject_token=CLIENT_ASSERTION_3
&subject_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type%3Ajwt
&audience=https%3A%2F%2Fras.example%2F
&resource=https%3A%2F%2Fapi.example%2Ftenants%2Facme-data%2F
&scope=files.read
~~~

The IdP resolves `analysis-client` to `agent-42`. It verifies a Client
Association for self-acting issuance and the agent's own authorization
for `files.read` at the resource. It returns `issued_token_type`
`urn:ietf:params:oauth:token-type:wag` with `token_type` `N_A`. The
decoded WAG uses `typ=wag+jwt` and this payload:

~~~ json
{
  "iss": "https://idp.example/",
  "sub": "agent-42",
  "aud": "https://ras.example/",
  "iat": 1789646580,
  "exp": 1789646880,
  "jti": "wag-1",
  "client_id": "analysis-api",
  "resource": "https://api.example/tenants/acme-data/",
  "scope": "files.read",
  "cnf": {"jkt":"JKT_K"}
}
~~~

Redemption follows {{redemption-example}}, with a fresh client assertion
and DPoP proof and the WAG as the `assertion`. The RAS correlates
(`https://idp.example/`, `agent-42`) to `service-principal-42` and
applies its own policy for that principal. It issues an access token
with `sub` `service-principal-42`, no `act`, the same audience, scope,
and `cnf`, and no refresh token. The API enforces the agent's own
permissions and the tenant; it applies no actor gate.

## Input Variants {#input-variants}

These non-normative variants change only the agent-resolution input of
{{walkthrough}}; the message sequence is unchanged. The resulting actor
is always the IdP issuer and `agent-42`. Only the platform JWT variant
sends actor-token parameters.

| Variant | Authentication and presentation | Identity resolved |
|---|---|---|
| Shared client with JWT-SVID | JWT-SVID as `client_assertion`, with `client_assertion_type` `jwt-spiffe` | Approved trust domain and exact SPIFFE ID in `sub` ({{jwt-svid-input}}) |
| WIT-SVID | `spiffe_wit`: WIT-SVID in `OAuth-Client-Attestation`, with a fresh PoP header signed by its key | Exact SPIFFE ID in the validated `sub` ({{spiffe-input}}) |
| X.509-SVID | `spiffe_x509`: mutual-TLS authentication with the X.509-SVID | Exact URI Subject Alternative Name ({{spiffe-input}}) |
| Platform JWT (AWS STS) | STS JWT as `actor_token` with type `jwt`; separately configured client authentication | Exact issuer, `sub`, and selector ({{imported-jwt-input}}) |
{: title="Input variants relative to the dedicated-client walkthrough"}

The JWT-SVID and platform JWT variants use IdP `client_id`
`platform-sso`. The WIT-SVID and X.509-SVID variants use the SPIFFE ID
as `client_id`. Across the variants:

* **Proof key:** In the bound profile, K signs the issuance DPoP proof,
  except that the WIT-SVID variant uses the WIT-SVID key. The
  X.509-SVID variant's DPoP key may differ from its TLS key.
* **Lifetime:** The input bounds the grant lifetime under
  {{grant-common}}.
* **Client Association:** Each variant needs a Client Association for
  its authenticated client ({{identity-binding}}). The JWT-SVID and
  platform JWT variants need a separate one for `platform-sso`. In the
  WIT-SVID and X.509-SVID variants, where the authenticated client is
  the workload itself, the association can be administered together
  with the binding.
* **Negative tests:** The dedicated-client negative tests apply to each
  binding, except that replay rules follow the input specification.

One Agent Principal can carry a binding for each platform it runs on
({{identity-binding}}), each keyed by its own issuer and selectors:

~~~
 Agent Principal: agent-42

 B1  JWT-SVID, orchestrated runtime                     enabled
     trust domain  platform.example
     SPIFFE ID     spiffe://platform.example/accounts/acme/
                     agents/workload-7

 B2  platform JWT, managed container service            enabled
     issuer        https://sts.amazonaws.com/
     sub           arn:aws:iam::123456789012:role/AgentRuntime
     selector      /https:~1~1sts.amazonaws.com~1/aws_account
                     = 123456789012

 B3  dedicated client, private_key_jwt                 disabled
     assertion iss  https://idp.example/clients/c1
     assertion sub  https://idp.example/clients/c1
~~~

B1 and B2 both resolve to agent-42, which the issued grant names
({{aws-example}} shows B2). Disabling B3 stops new issuance through B3
only; an association naming B1 and B2 still authorizes them, subject to
the remaining checks.

### Identity Mapping Example {#identity-example}

Alice asks a data-analysis agent to read a file. The platform uses one
shared OAuth client for many agents, so its client identifier alone
cannot identify which agent is acting. This non-normative example uses
the optional SPIFFE input to make that distinction through four separate
decisions:

1. **Resolve the agent.** The IdP validates the workload's JWT-SVID, and
   an Identity Binding maps its exact SPIFFE ID,
   `spiffe://platform.example/accounts/acme/agents/workload-7`, to
   `agent-42` in the namespace of `https://idp.example/`, in Governance
   Tenant `acme`.
2. **Authorize the client.** The IdP's configured SPIFFE association
   authenticates the caller as `platform-sso`, and a separate Client
   Association permits that client to use this binding for delegated
   ID-JAG issuance.
3. **Authorize delegation.** Alice's ID Token, issued for
   `platform-sso`, identifies her as `alice-app`. The IdP authorizes
   `agent-42` to act for her with `files.read` at the requested resource
   in Target Tenant `acme-data` and issues an ID-JAG.
4. **Apply resource policy.** The RAS resolves Alice to local user
   `user-108` and correlates the agent with local principal
   `service-principal-42`. Alice has the file permission, and resource
   policy permits this agent to act for her; the agent needs no file
   permission of its own.

| Claim | ID-JAG issued by IdP | Access token issued by RAS |
|---|---|---|
| `sub` (Alice) | `alice-ras` | `user-108` |
| `act.iss` (agent namespace) | `https://idp.example/` | `https://idp.example/` |
| `act.sub` (Agent Principal) | `agent-42` | `agent-42` |
| `client_id` (client at RAS) | `platform-api` | `platform-api` |
| `scope` | `files.read` | `files.read` |
{: title="Identity claims across the domain boundary"}

The RAS translates the user and preserves the agent:

* `alice-ras` is Alice's identifier in the target SSO namespace.
* `platform-api` is the registration corresponding to `platform-sso` at
  the RAS.
* The local agent record `service-principal-42` supports authorization
  but does not replace `act.sub`.

### Shared Platform Client with SPIFFE {#shared-client-example}

This variant completes {{identity-example}}. The workload obtains a
JWT-SVID with the IdP issuer as its audience. The existing SPIFFE format
omits `iss` and `iat`, and the expiration is an illustrative NumericDate
value. The IdP selects trusted signing keys from its configured bundle
for the `platform.example` trust domain.

~~~ json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "spiffe-key-1"
}
~~~

~~~ json
{
  "sub": "spiffe://platform.example/accounts/acme/agents/workload-7",
  "aud": ["https://idp.example/"],
  "exp": 1789647063
}
~~~

The JWT-SVID authenticates the client through the configured SPIFFE
association and resolves the agent separately. It is bearer evidence and
does not attest that grant proof key K belongs to the workload.
`platform-api` replaces `analysis-api` in grants, access tokens, and RAS
client authentication.

### WIT-SVID and X.509-SVID {#svid-context-example}

Both variants resolve the workload authenticated on the exchange request
through an exact Identity Binding from
`spiffe://platform.example/agents/analysis` to `agent-42`. The user ID
Token is issued to that authenticated client, not reused from
`analysis-client`. The WIT-SVID carries the SPIFFE ID in `sub` and the
workload public key in `cnf.jwk`. For X.509-SVID, mutual-TLS
authentication replaces the two attestation headers. An authoritative
association supplies the downstream client identifier in both cases.

### AWS Workload Identity Binding {#aws-example}

This variant uses the AWS STS `GetWebIdentityToken` credential
documented in {{AWS-TOKEN-CLAIMS}}. The Identity Binding names:

* the configured STS issuer as credential authority;
* the exact `sub` `arn:aws:iam::123456789012:role/AgentRuntime`;
* the accepted audience `https://idp.example/token`; and
* the selector `/https:~1~1sts.amazonaws.com~1/aws_account` equal to
  `123456789012`.

The selector addresses the string `aws_account` within the
`https://sts.amazonaws.com/` object; `~1` escapes each slash in that
member name.

If several agents share this role, issuer and `sub` identify the shared
IAM principal, not an individual agent. Distinct Agent Principals then
need distinct credential identities or additional trusted selectors. A
caller-supplied agent name does not provide that distinction. This
variant covers evidence resolution, not a product's end-to-end
conformance. User-access-token OBO composition remains outside the scope
of this document ({{access-token-subject-gap}}).

# Dependencies and Deferred Work {#upstream-gaps}

This informative appendix records dependencies and deferred work. They
were assessed against WAG-01, ID-JAG-04, ICA-02, Actor Profile-00,
SPIFFE OAuth-02, ATTEST-11, WIT-02, CIMD-02, Client Instance
Identification-00, and Client Attester Endorsement-00.

## Upstream Dependencies

| Specification | What this profile needs | Consequence until resolved |
|---|---|---|
| WAG | Type registration; alignment on protection, linking, and subject presentation ({{wag-gaps}}) | Provisional type values |
| ID-JAG | `jwt-bearer` in the bound-grant example; confirmation errors distinct from RFC 9449 proof errors ({{bound-grant-coordination}}) | Confirmation checks apply to `jwt-bearer` here |
| Actor Profile | A reusable principal-resolution extension point ({{dedicated-client-coordination}}) | Local mapping ({{actor-construction}}) |
{: title="Upstream dependencies"}

### WAG {#wag-gaps}

In WAG terms, the IdP is the Platform that signs the grant
({{Section 2 of WAG}}), and {{wag-issuance}} defines that issuance. Open
items are:

* a token type and an explicit JWT type for the grant, which
  {{Section 8 of WAG}} lists as open, their registration, and their
  advertisement with the self-acting profile URIs ({{server-metadata}});
* DPoP binding ({{grant-protection}});
* authorized correlation in place of WAG's acceptance of previously
  unseen agents ({{Section 3 of WAG}});
* a token exchange in which the authenticated client is the subject
  without a subject token ({{wag-request}}), which would also give
  X.509-SVID authentication a self-acting path; and
* self-acting Client Associations ({{AGENT-MANAGEMENT}}).

### ID-JAG Bound Grants {#bound-grant-coordination}

{{Section 4.4 of ID-JAG}} requires `jwt-bearer`, but its bound-grant
example uses `jwt-dpop`. This profile applies explicit confirmation
processing to `jwt-bearer` ({{redemption}}) and takes no dependency on
JWT DPoP Grant.

### Resolution from Authentication Context {#dedicated-client-coordination}

Delegated issuance here resolves the actor from authentication context
without `actor_token` ({{actor-inputs}}). ID-JAG leaves actor processing
to extensions ({{Section 9.7 of ID-JAG}}). Appendix A.1 of {{RFC8693}}
reads a subject-only request as impersonation.
{{Section 6.3.1 of ACTOR-PROFILE}} permits authentication-context reuse
only with the same assertion as `actor_token`. Generic Token Exchange or
Actor Profile support therefore does not advertise this resolution.

## Deferred Compositions

### Grant Key Transition {#key-transition-gap}

No proof-key transition is defined ({{distributed-key-use}}); passing a
bound grant to a worker with another key would need one.

### Portable Authorization Deadlines {#deadline-gap}

No portable IdP-imposed deadline on downstream access is defined
({{authorization-lifetime}}).

### User Access Tokens as Subjects {#access-token-subject-gap}

Deployed on-behalf-of (OBO) flows, including {{AWS-AGENTCORE-OBO}}, use
a user access token as the subject. Accepting one needs eligibility,
audience, resolution, sender-constraint, and authority rules coordinated
with ID-JAG, not only a new `subject_token_type`.

### Excluded Compositions {#excluded-compositions}

This document does not define the following compositions:

| Composition | Boundary in this document |
|---|---|
| Asynchronous approval with {{AROP}} | External approval follows {{external-approval}}, {{authorization-lifetime}}, and {{issuance-authorization}} |
| Continuation with {{ICA}} | Renewal follows {{continuing-access}} |
| General WIMSE WIT/WIC inputs | Only the SPIFFE forms in {{spiffe-input}} are defined |
| Instance context in an ID-JAG or WAG, or preserved across domains, under {{INSTANCE}} | The RAS conveys only an instance it validated ({{access-token-response}}); workload evidence resolves the agent, and a shared workload identity does not distinguish replicas {{SPIFFE-CONCEPTS}} |
| Mutual-TLS-bound ID-JAG | Bound grants use DPoP; mutual TLS can protect access tokens ({{access-token-protection}}) |
| Authorization details without scope | Scope is required; the scope-free mode of {{RFC9396}} is not defined |
{: title="Excluded compositions"}

## Operational Dependencies {#operational-guidance}

Provisioning, account linking, and lifecycle propagation are deployment
choices. Useful controls include:

* authenticated link changes;
* just-in-time accounts and correlations authorized by issuer and tenant
  ({{jit-correlation}});
* no silent merges or reactivation of disabled accounts; and
* issuer and tenant context in SCIM `externalId` {{RFC7643}}.

SCIM {{RFC7644}} and {{SCIM-AGENT}} are building blocks, not a lifecycle
propagation contract.

### Provisioning and Disablement {#lifecycle-gap}

{{AGENT-LIFECYCLE}} profiles SCIM, optional Shared Signals, and applied
changes, including missed-event limits. It is not required for
conformance; {{agent-correlation}} and {{status-changes}} state this
document's guarantees.

# Document History

RFC Editor: Remove this section before publication.

* Initial version.

# Acknowledgments
{:numbered="false"}

The author thanks Jeff Malnick for review and discussion of this
profile.
