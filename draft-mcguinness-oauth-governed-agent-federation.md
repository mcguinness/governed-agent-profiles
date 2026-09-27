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
  INSTANCE:
    title: "Client Instance Identification for Attestation-Based Client Authentication"
    target: https://mcguinness.github.io/draft-mcguinness-oauth-client-instance-id/draft-mcguinness-oauth-client-instance-id.html
    author:
      - name: Karl McGuinness
    date: 2026-09-15
    seriesinfo:
      Internet-Draft: draft-mcguinness-oauth-client-instance-id
  ATTESTER-ENDORSEMENT:
    title: "OAuth 2.0 Client Attester Endorsement"
    target: https://mcguinness.github.io/draft-mcguinness-oauth-client-attesters/draft-mcguinness-oauth-client-attesters.html
    author:
      - name: Karl McGuinness
    date: 2026-09-15
    seriesinfo:
      Internet-Draft: draft-mcguinness-oauth-client-attesters
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
commonly uses one shared OAuth client, which leaves every agent behind
that client indistinguishable at the resource server: individual
actions cannot be attributed, and authorization cannot be withdrawn
from one agent without withdrawing it from all of them.

What an enterprise needs instead is a principal it can authorize once,
audit across resources, and disable everywhere, whose identity does not
change when the agent moves between platforms or rotates credentials.

Client and workload identities do not necessarily match the
enterprise's governance boundary. One runtime may serve several
independently governed actors, while one actor may operate through
several platform identities.

Enterprise identity already solves a version of this problem for
people. A person has one account, several credentials linked to it,
and separate rules about which applications may use that account.
This document applies that shape to agents. The Agent Principal is
the account, an Identity Binding maps a validated, qualified client or
workload identity to it, and a Client Association states which OAuth
client may exercise that binding. The account's identifier can be the
same as the execution identity's; the binding decides which identity is
authoritative for governance.

Existing OAuth mechanisms authenticate clients and carry actors, but
they leave three relationships open:

1. How different client and workload identities resolve to the same
   governed principal. {{ATTEST}} and {{SPIFFE-OAUTH}} authenticate
   OAuth clients, not the agents a shared client serves.
2. How authority to use that principal is separated from identity
   resolution. The Identity Assertion JWT Authorization Grant (ID-JAG)
   leaves the validation and authorization of an actor, and the
   relationship among client, subject, and actor, to extensions
   ({{Section 9.7 of ID-JAG}}).
3. How the resulting principal is represented and correlated across
   authorization domains. {{RFC8693}} defines the `act` claim but not
   how an actor authenticated through a client or workload credential
   is named in it, or how a resource domain correlates that name with
   local state.

This document is an OAuth deployment profile that fills those gaps. It
standardizes the boundary between execution identity and governed
identity, and it does not require the two to differ. An identity
provider (IdP) resolves an authenticated client or workload identity to
an Agent Principal, whose identifier can equal the execution identity's
or differ from it, and OAuth grants carry that principal into the
resource domain. A service provider can then authorize a stable,
enterprise-governed agent without understanding the runtime or
credential that currently executes it:

~~~
 Customer domain                          Service provider
 ---------------                          ----------------
 Runtime identity: workload-7
        |
        |  customer IdP resolves
        |  workload-7 -> agent-42
        v
 Agent Principal: agent-42  ------------>  authorizes, audits, and
                                           can disable agent-42
~~~

If agent-42 later runs as workload-19, the customer's IdP binds
workload-19 to the same Agent Principal, and the service provider still
sees agent-42.

The governing principle is that the Agent Principal is the
authorization identity: client and workload identities are
authenticated inputs from which the IdP resolves it, and they do not
replace it downstream. Three consequences shape the rest of the
document:

* **Governed identity is independent of execution identity.**
  Platforms, workload credentials, and OAuth clients can change without
  changing the Agent Principal.
* **Resolving an identity does not authorize its use.** Identity
  Binding establishes which agent a credential represents; a separate
  Client Association establishes whether a client may exercise it.
* **Actor attribution is not delegation authority.** An agent named in
  `act` acts for the user only under the IdP's Delegation Authorization
  and the resource's actor gate ({{actor-authorization}}).

A dedicated OAuth client resolves through an explicit client-to-agent
binding. A shared client uses independently validated workload identity
to distinguish the agents it serves. Both deployments retain separate
identity, client-authority, delegation, and resource-policy decisions.

Each question in the model is decided by one owner:

| Question | Decided by | Relationship |
|---|---|---|
| Which governed agent does this client or workload identity represent? | IdP | Identity Binding |
| May this OAuth client exercise that agent? | IdP | Client Association |
| May the agent act for this user, or for itself, toward the requested target and authority? | IdP | Delegation Authorization or Agent Authorization |
| What may that agent do in this resource domain? | Resource domain | Agent Principal Correlation and resource policy |
{: title="Decisions and their owners"}

For delegated access, the resource authorization server (RAS):

* Translates the user identity into its local namespace.
* Preserves the issuer-qualified agent identity.
* Correlates that identity with local authorization state without
  replacing it with the local principal's identifier.

AIMS {{AIMS}} describes a broader framework for agent identity management.
This document is an OAuth deployment profile within that space, not a
governance framework: it defines how the identities in one transaction
relate across authorization domains.

The federation model ({{model}}) is independent of the grant that
carries it. Two peer realizations carry it:

* **Delegated access ({{delegated-flow}}):** ID-JAG, with the user as
  subject and the Agent Principal as actor.
* **Self-acting access ({{wag-flow}}):** the Workload Authorization Grant
  (WAG), with the Agent Principal as subject.

Each realization has its own mandatory path, and an implementation
claims one or both ({{scope}}).

Other grant realizations require their own composition rules; the
federation model alone does not define their wire behavior.

RFC 7523 client assertions, SPIFFE JWT Verifiable Identity Documents
(JWT-SVIDs), and the other supported credentials supply inputs to the
same identity model ({{evidence}},
{{optional-input-profiles}}).

This document federates an agent governed by the IdP that issues the
grant into a resource domain. It does not define identity continuity
across a chain of IdPs or brokers; forwarding an actor from another
IdP's namespace is out of scope. Also out of scope are task or mission
authorization, asynchronous approval, continuation composition,
provisioning protocols and account administration, multi-agent
delegation chains, instance identification and propagation, client
attester endorsement, and enrollment or key-replacement protocols
({{upstream-gaps}}).

# Conventions and Terminology

{::boilerplate bcp14-tagged-bcp14}

OAuth and Token Exchange terms follow {{RFC6749}} and {{RFC8693}}.
Client Attestation terminology follows {{ATTEST}}; Actor Profile refers
to {{ACTOR-PROFILE}}. This document uses "API" for the OAuth resource
server and "AS" for an authorization server when a statement applies
to both the IdP and the RAS.

## Roles

Agent Platform (the platform):
: The environment that runs agents. It supplies verifiable workload
  evidence from its own or an approved external credential authority and
  can implement the OAuth client that obtains access for an agent.

Client:
: Software making OAuth requests for an agent. It authenticates as an
  OAuth client and presents the evidence, target, and proofs for the
  selected grant flow. One client registration can serve several agents.
  Client authentication identifies the client; agent resolution requires
  an explicit Identity Binding.

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

Two companion profiles complete the family: {{AGENT-MANAGEMENT}}
establishes the relationships at the IdP, this document exercises them
to obtain authorization, and {{AGENT-LIFECYCLE}} carries the
principal's administrative state into the resource domain and revokes
what depends on it.

The companion profiles add two administrative roles. The Provisioning
Client is a platform connector that manages Agent Principals and their
relationships at the IdP, whose System for Cross-domain
Identity Management (SCIM) service is the IdP Service Provider
({{AGENT-MANAGEMENT}}). The Receiver is the resource-domain SCIM service
together with the RAS components that accept IdP provisioning
({{AGENT-LIFECYCLE}}). "Service Provider" alone always denotes the
IdP-side SCIM service.

## Terms {#terms}

Agent Principal:
: A stable, non-human authorization principal in the IdP's namespace
  representing an independently governed workload or agent. Its identity
  defines the boundary for independently managed authorization, delegation,
  attribution, correlation, and disablement. It is independent of the
  external credentials, execution environments, and OAuth clients used
  to obtain authorization for it; it does not necessarily identify an
  execution, process, replica, installation, or OAuth client.

Workload:
: An external computational principal identified by accepted workload
  evidence. It can span multiple running instances; its identity does
  not necessarily distinguish executions. An Identity Binding resolves
  that external identity to an Agent Principal.

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
  Agent Principal, which can have the same identifier as that identity.
  It is administered in a Governance Tenant and establishes identity
  resolution, not permission to exercise the agent.

Client Association:
: An approved permission for an authenticated OAuth client to use an
  Agent Principal through the selected Identity Binding, acting relationship, and
  credential class. The permission can cover one binding or an explicitly
  authorized set of bindings under {{identity-binding}}. It is an
  authorization-policy relationship, independent of identity resolution.

Credential class:
: A configured category of agent-resolution input with mutually exclusive
  validation rules, such as an RFC 7523 client assertion, a SPIFFE
  Verifiable Identity Document (SVID), Client Attestation, or a platform
  issuer's workload JWT profile.
  JWT encoding alone does not identify the class.

Acting relationship:
: Whether the Agent Principal acts as the subject of a grant
  (self-acting) or as the actor for a user (delegated). Client
  Association, Agent Authorization, and Delegation Authorization are
  each scoped to an acting relationship.

Delegation Authorization:
: The IdP's decision that an Agent Principal may act for a user within
  an approved client, tenant, target, and authority context.

Agent Authorization:
: The IdP's decision that an Agent Principal may access a target on its
  own behalf within an approved client, tenant, target, and authority
  context. It is the self-acting counterpart of Delegation Authorization.

Agent Principal Correlation:
: The RAS's authoritative association of an IdP-qualified Agent Principal
  with a local principal. Correlation does not grant authority.

Issuer-bound presenter key:
: A key the credential issuer has attested belongs to the workload,
  such as a Client Attestation's confirmation key. It shows that the
  credential authority authorized the key.

Request proof key:
: A key the presenter proves in the request without issuer attestation,
  as with Demonstrating Proof of Possession (DPoP) {{RFC9449}}
  accompanying bearer evidence. It shows possession alone
  ({{credential-requirements}}).

Grant proof key:
: The DPoP key proven when requesting an ID-JAG or WAG and bound into
  that grant for redemption. A bearer JWT-SVID does not endorse this
  key; only an input that binds a key, such as a WIT-SVID or Client
  Attestation, can tie it to the credential issuer
  ({{credential-requirements}}).

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
Delegation Authorization. The RAS controls local principal correlation and
authorization, using trusted provisioning from the IdP or an authorized
directory connector where applicable.

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

One Agent Principal carries a set of Identity Bindings and a set of
Client Associations:

~~~
 Agent Principal: agent-42
 (one stable identity in the IdP issuer's namespace)
   |
   |  Identity Bindings        keyed by qualified input identity
   +-- B1  JWT-SVID          trust domain + SPIFFE ID
   +-- B2  platform JWT      issuer + sub + selector
   +-- B3  dedicated client  assertion iss + sub
   |
   |  Client Associations      permit a client to use bindings
   +-- A1  client C1 -> B1, B2    delegated
   +-- A2  client C2 -> B3        self-acting
~~~

A binding maps one qualified identity to the Agent Principal. An
association permits one client to exercise named bindings for one
acting relationship. Neither implies the other.

Establishing one relationship MUST NOT be treated as establishing
another. A local principal link identifies the agent; resource policy
still determines whether to accept its delegated access.

Up to three identities meet in one request, and each answers a
different question:

| Identity | Question it answers | Established by |
|---|---|---|
| Workload | Which workload identity does the accepted evidence assert? | Credential validation ({{evidence}}) |
| OAuth client | Which software is requesting the grant? | Client authentication |
| Agent Principal | Which independently governed principal does that input resolve to? | Identity Binding ({{identity-binding}}) |
{: title="Distinct identities in a request"}

Dedicated-client resolution establishes no separate workload identity:
the authenticated client identity is itself the resolution input. In
every case, none of these identities is inferred from another.
The relationship between workloads and Agent Principals can be
one-to-one; this profile does not require it ({{governance-boundary}}).
Client Association authorizes client use through the binding, acting
relationship, and credential class under {{identity-binding}}.

The IdP is the authority for the Agent Principal: the ID-JAG's `act.iss`
equals its `iss`, and `act.sub` comes from the IdP's mapping rather than
forwarding the external subject.

Identity resolution establishes which governed principal participates
in a transaction. It does not establish client authority, user delegation,
resource authority, or permission to perform an operation. This profile
provides identity continuity for the agent: across changes of execution
environment through Identity Binding, and across the boundary between
the IdP and the resource domain. It does not provide work continuity.
Whether an approved task, with its purpose, approval, and lifecycle,
still justifies an action is outside this profile.

## Service Provider Contract {#sp-contract}

The mapping from execution identity to Agent Principal is local to the
IdP; the security contract across the boundary between the IdP and the
resource domain is interoperable. A resource domain consumes an
IdP-qualified Agent Principal. Its RAS
performs no platform-specific credential validation or workload
resolution, and it need not know whether the agent authenticated as a
dedicated OAuth client or with a SPIFFE identity, Client Attestation, or
a platform JWT. From a validated grant it receives:

* the Agent Principal, qualified by its governing issuer: `act.iss` and
  `act.sub` in an ID-JAG, or `iss` and `sub` in a WAG;
* the acting relationship: delegated, with the user as subject, or
  self-acting;
* the client's registration at the RAS, in `client_id`; and
* the authority the IdP approved, as a ceiling for the RAS decision.

The RAS correlates the Agent Principal with a local principal for
authorization and lifecycle state; an existing service principal can
serve without replacing the IdP-qualified identity
({{agent-correlation}}). The resource domain keeps its own decision:
correlation does not grant authority, and the RAS decides within the
grant's ceiling ({{actor-authorization}}, {{wag-redemption}}).

## Authentication, Resolution, and Proof {#inputs}

The IdP MUST validate a credential according to its configured type
before using it for identity resolution; a generic JWT token-type URI,
an unverified header, or a caller-supplied claim MUST NOT select a
weaker validation path or establish an Identity Binding. Unrecognized
request parameters and JWT claims follow {{Section 3.2 of RFC6749}} and
{{Section 4 of RFC7519}}.

The IdP MUST NOT substitute one of three distinct functions for
another:

* **Client authentication:** evidence authenticating the OAuth client.
* **Agent resolution:** resolution of the authenticated dedicated-client
  identity or independently validated workload identity through an
  Identity Binding to exactly one Agent Principal.
* **Key possession:** proof that the presenter controls a key, with the
  binding semantics of the proof mechanism.

The distinction between an issuer-bound presenter key and a request
proof key ({{terms}}) determines what a proof establishes.

The same credential can serve client authentication and agent resolution
without making the client and agent the same principal. Successful
client authentication MUST NOT imply successful agent resolution, and
successful agent resolution MUST NOT imply permission for the
authenticated client to exercise that agent.

## Canonical Identity and Tenant Boundaries {#canonical-identity}

The Agent Principal identifier MUST be unique and non-reassignable
within the IdP issuer's namespace, across all Governance Tenants sharing
that issuer identifier. Governance Tenant is not an additional component
of the downstream agent identity. A tenant-local identifier therefore
needs qualification to meet this issuer-wide uniqueness requirement
before use as an Agent Principal identifier.

It need not equal an external subject, OAuth client identifier,
SPIFFE ID, display name, or instance identifier. Identity continuity is
an explicit decision by the governing authority to preserve the same
principal; it does not imply that the principal's permissions remain
unchanged. Agent Principal continuity concerns the authorization
principal, not continuity of a particular execution or runtime instance.

An Agent Principal identity does not itself prove which runtime or
execution currently represents the agent; any such assurance comes from
the validated evidence and proofs required by the resolution-input
profile ({{evidence}}).

After a transfer to a different Governance Tenant under a different
administrative authority, the IdP MUST assert the agent under a new
Agent Principal identifier. Delegations held for the previous identifier
do not carry forward automatically ({{delegation-authorization}}). RAS
principal links held for the previous identifier MUST NOT be re-keyed to
the new identifier ({{agent-correlation}}). This document
defines no cross-tenant identity migration protocol.

For example:

* Moving an agent to another customer's governance domain creates a
  new identity.
* Renaming a tenant or changing its owner or administrator within the
  same governance domain does not by itself change the principal.

Multiple Identity Bindings can resolve distinct client or workload
identities to the same Agent Principal when the IdP approves them as
representing the same governed principal. They share the governed
authorization identity downstream.

The IdP MUST establish an unambiguous Governance Tenant and, before
issuance, the Target Tenant for the requested RAS and resource. The RAS
MUST interpret an agent identifier in its asserted issuer context and
MUST NOT key agent authorization on a bare `sub`. Failure to resolve
the Governance Tenant uses `invalid_grant`; failure to resolve the
Target Tenant for the requested resource uses `invalid_target`.

## Governance Boundary and Execution Independence {#governance-boundary}

Clients, workloads, or other actors requiring independently managed
authorization, delegation, attribution, resource correlation, or
disablement as principals need separate Agent Principal identities,
even when they share a runtime, OAuth client, workload credential, or
deployment. Differences in process, replica, session, worker, or
credential alone do not require distinct identities. An execution that
shares all of these with an Agent Principal, such as a sub-agent
working entirely within its parent's authority and attributed to it,
can run as that Agent Principal; one that needs any of them separately
needs its own identity.

Multiple executions can operate as the same Agent Principal, and an
agent can move between workloads or execution environments through
approved Identity Bindings. Conversely, one environment can host
multiple Agent Principals. The validated resolution input and its
Identity Binding therefore need to distinguish exactly one Agent
Principal for each authorization transaction; the IdP rejects an
ambiguous mapping ({{identity-binding}}), and a shared workload
identity alone cannot select among agents.

Scaling, restarting, rescheduling, migration, credential rotation, or
creation of additional executions, replicas, credentials, Identity
Bindings, or Client Associations does not by itself create, merge,
transfer, or increase Agent Principal authority.
Each transaction remains subject to the applicable Client Association,
delegation authorization, target, and resource policy.
This profile defines no aggregate budget, quota, or concurrency semantics.

## Grant Paths {#paths}

The federation model covers both acting relationships, each with a peer
realization:

| Acting relationship | Grant | Realization |
|---|---|---|
| Agent acts as itself | WAG; Agent Principal is the subject | {{wag-flow}} |
| Agent acts for a user | ID-JAG; user is the subject and Agent Principal is the actor | {{delegated-flow}} |
{: title="Grant paths"}

An Agent Principal is not intrinsically self-acting or delegated. The
authorization transaction determines whether it is represented as the
subject or as the actor for another subject. Authorization for one
relationship does not imply authorization for the other.

The delegated realization transforms validated identities into bounded
authority at two authorization servers, followed by API enforcement:

~~~
 Resolution inputs         Enterprise IdP
 -----------------         --------------
 Dedicated client -------> Authenticate; resolve client binding
           OR
 Workload + client ------> Validate both; resolve workload binding
                                      |
                           Client Association
 User credential --------> Resolve user
                                      |
                           Delegation Authorization
                           (client, tenant, target, authority)
                                      |
                           ID-JAG: sub = user
                                   act = IdP-qualified agent
                                      |
                           Resource Domain
                           ---------------
                           RAS validates grant, client, and proof
                                      |
                           Resolve local user; correlate agent
                                      |
                           RAS authorization within grant ceiling
                                      |
                                 Access token
                                      |
                           API enforces user authority, actor gate,
                           tenant, token limits, and proof binding
~~~

The client presents a supported user credential and agent-resolution input,
and authenticates at each authorization server. The two token requests
are ID-JAG issuance at the IdP and redemption at the RAS. Proof processing
follows the applicable grant and access-token protection; each decision
is constrained by its own policy domain ({{actor-authorization}}).

## Adoption Profiles {#adoption-profiles}

The adoption path preserves existing Enterprise-Managed Authorization
{{EMA}} deployments and adds agent governance before requiring grant
binding. The names identify deployment profiles, not assurance ratings.

| Adoption profile | Required addition | Grant protection |
|---|---|---|
| Enterprise access | Existing EMA and base ID-JAG; no separate Agent Principal required | Existing deployment policy |
| Governed agent access | Agent resolution, Identity Binding, Client Association, the governed actor (delegated) or subject (self-acting), tenant enforcement, and the downstream actor gate for delegated access | Grants without sender constraint permitted only by explicit policy; any binding present is enforced |
| Bound governed agent access | All governed agent requirements plus DPoP at grant issuance and redemption | `cnf.jkt` and same-key continuity required |
{: title="Adoption profiles"}

"Bound" refers to sender constraint on the grant, ID-JAG or WAG, between issuance and
redemption. It does not imply sender constraint on the agent-resolution
credential or the resulting access token.

Enterprise access is a migration baseline, not conformance to this
document's governed profiles. Existing EMA deployments need no changes
to continue on that path. Adding `act` alone does not establish governed
agent conformance: identity resolution and actor authorization are also
required. The adoption profiles apply to both realizations, each under
its own URIs ({{metadata}}).

Grant protection, workload-evidence protection, and access-token
protection are separate choices: even bound governed agent access can
use bearer workload evidence and, under explicit resource policy, bearer
access tokens. Credential-class validation follows {{actor-inputs}},
grant protection and downgrade prevention follow {{grant-protection}}
and {{discovery}}, and protection on the API hop follows
{{access-token-protection}}.

## Federation Configuration {#configuration}

The relationships in {{model}} require trusted configuration, not a
particular storage representation or administrative interface:

**At the IdP:**

* **Credential trust:** The IdP configures the issuer or trust domain,
  approved key source, algorithms, credential class, and time limits
  under the selected credential specification.
* **Identity Binding:** An IdP administrator or approved platform-registry
  import supplies the qualified client or workload identity, Agent
  Principal, and Governance Tenant.
* **Client Association:** The IdP administrator specifies the client,
  permitted binding or binding set, acting relationship, and credential
  class.
* **Resolution mode and proof:** IdP policy and client configuration
  establish authentication-context resolution or a separate presented-evidence
  input under {{actor-inputs}} for the client,
  applicable profile, and target. They establish accepted credential
  classes and proof requirements for that mode.
  Request parameters do not select the resolution mode ({{actor-inputs}}).
* **Target:** The IdP administrator configures the RAS issuer, resources,
  Target Tenant, subject namespace, and authority to assert `aud_sub`.
* **Delegation:** IdP policy or consent authorizes the agent, user,
  client, tenant, RAS, resource, and authority relationship.
* **Agent Authorization:** IdP policy or assignment authorizes the
  agent's own access to the RAS, resource, and authority for self-acting
  issuance.

**Across the client and resource domain:**

* **Client registration:** The client establishes its registration and
  authentication keys at each authorization server, or through Client
  ID Metadata Documents (CIMD) {{CIMD}} where supported. Each server consumes
  the corresponding metadata.
* **Client registration association:** For each target RAS, the IdP
  holds the authoritative mapping from its authenticated client to that
  client's registration at the RAS ({{Section 5 of ID-JAG}}), from which
  it derives the ID-JAG `client_id` ({{flow-configuration}}). Using one
  identifier at both
  servers, which a CIMD Client Identifier URL provides by construction,
  makes that mapping the identity mapping. No companion profile
  provisions this association; it is configured.
* **Target Tenant binding:** The Target Tenant is configured once and
  carried consistently by the tenant-specific resource URI
  ({{root-request}}), by the resource domain's provisioning context, and
  by any Shared Signals stream ({{AGENT-LIFECYCLE}}). This profile
  assumes deployments configure these carriers to agree.
* **Local principals:** The RAS provisions or synchronizes local agent
  principals and user links for RAS and API processing.
* **Applicable profile:** Client, IdP, RAS, and resource policy establish
  the profile and minimum requirements per client, trust relationship,
  and resource; all roles enforce their applicable requirements.
* **Access-token protection:** The RAS and client configure protection
  per resource for client, RAS, and API use ({{access-token-protection}}).
  `token_type` distinguishes DPoP, but not mutual TLS from bearer.

Discovery exposes capabilities, not these authorization decisions:

* Credential metadata follows its credential specification; discovery
  MUST NOT establish trust.
* {{CIMD}} can supply client metadata where supported. RAS metadata
  under {{RFC8414}} confirms grant and profile support.
* Bindings, associations, delegation, and local links have no discovery
  mechanism here. Profile metadata does not establish acceptance policy
  ({{discovery}}).

These validations occur while a request is processed, not when an Agent
Principal, Identity Binding, or Client Association is created. Keys and
metadata may already be held; their retrieval and refresh follow the
rules of the source that supplies them:

* The IdP validates a platform JWT or an SVID under the approved key
  source configured for that input ({{evidence}}).
* The RAS validates an ID-JAG at redemption under the governing IdP's
  keys, with trust configured for the asserted namespace
  ({{redemption-validation}}).
* A client uses server metadata to locate endpoints and to confirm which
  grants and profiles each server accepts ({{metadata}}).

Existing workload-federation configuration can supply credential trust
and exact identity selectors. The Agent Principal mapping and separate
Client Association are still required, but no new configuration object
types are prescribed. {{identity-example}} illustrates the shared-client
case; {{aws-example}} applies the model to an AWS Security Token Service
(STS) workload credential.

Request hints, discovered client metadata, and unverified JWT claims
MUST NOT by themselves establish credential-authority trust or change
an approved Identity Binding or Client Association. Creating and changing
bindings
and associations, including imports from platform registries, is an
administrative act outside this profile ({{operational-guidance}}). The
SCIM companion {{AGENT-MANAGEMENT}} defines a proposed platform-to-IdP
management interface for those relationships.

## Identity Mapping Example {#identity-example}

Alice asks a data-analysis agent to read a file. The platform uses one
shared OAuth client for many agents, so its client identifier alone
cannot identify which agent is acting. This non-normative example uses
the optional SPIFFE input to make that distinction.

The request passes four separate decisions:

1. **Resolve the agent.** The IdP validates the
   workload's JWT-SVID. An Identity Binding maps its exact SPIFFE ID,
   `spiffe://platform.example/accounts/acme/agents/workload-7`, to
   `agent-42` in the namespace of `https://idp.example/`. The agent
   belongs to Governance Tenant `acme`.
2. **Authorize the client.** The IdP's configured SPIFFE
   association authenticates the caller as `platform-sso`. A separate
   Client Association permits that client to use this Identity Binding
   for delegated ID-JAG issuance. Authenticating the client does not
   grant that permission.
3. **Authorize delegation.** Alice's ID Token identifies her as
   `alice-app` and was issued for `platform-sso`. The IdP authorizes
   `agent-42` to act for her with `files.read` at the requested resource
   in Target Tenant `acme-data`, and issues an ID-JAG for the RAS.
4. **Apply resource policy.** The RAS resolves
   Alice to its local user `user-108` and correlates the IdP-qualified
   agent with local principal `service-principal-42`. Alice has the
   file permission, and resource policy permits this agent to act for
   her. In this example, the agent needs no file permission of its own.

The two identities move differently across the three namespaces:

~~~
           Input credential   ID-JAG          Access token
           ----------------   ------          ------------

 user      alice-app    -->   alice-ras  -->  user-108
                              (sub)           (sub)

 agent     workload-7   -->   agent-42   ==>  agent-42
           (SPIFFE ID)        (act.sub)       (act.sub)

 -->  translated into the next namespace
 ==>  preserved unchanged across the boundary
~~~

The resulting tokens show which identities change across the boundary:

| Claim | ID-JAG issued by IdP | Access token issued by RAS |
|---|---|---|
| `sub` (Alice) | `alice-ras` | `user-108` |
| `act.iss` (agent namespace) | `https://idp.example/` | `https://idp.example/` |
| `act.sub` (Agent Principal) | `agent-42` | `agent-42` |
| `client_id` (client at RAS) | `platform-api` | `platform-api` |
| `scope` | `files.read` | `files.read` |
{: title="Identity claims across the domain boundary"}

`alice-ras` is Alice's identifier in the target SSO namespace;
`platform-api` is the registration corresponding to `platform-sso` at
the RAS. The RAS translates the user and preserves the agent. Its local
agent record supports authorization; `service-principal-42` does not
replace `act.sub`.

If the agent later runs under another approved workload identity, a
second Identity Binding can resolve it to the same `agent-42`. A Client
Association also needs to permit that binding. The downstream agent identity
then stays unchanged, and either binding can be disabled independently.

{{shared-client-example}} supplies the credential and request details
for this scenario, using the complete message sequence in {{walkthrough}}.

# Agent Principal Resolution {#identity}

Resolution turns validated inputs into principals: the Identity
Binding resolves a qualified client or workload identity to one Agent Principal,
subject resolution identifies the user for delegated access, and the
RAS correlates both to its local principals.

Resolution maps a qualified execution identity to an Agent Principal.
The Agent Principal can have the same identifier as the execution
identity: resolution establishes which identity is authoritative for
governance, not that the identifiers differ ({{actor-construction}}).
An Identity Binding is the approved record that supports resolution.

## Agent Resolution Inputs {#evidence}

Each input resolves an authenticated dedicated-client identity or
an independently validated workload identity to one Agent Principal.
Every input satisfies the same contract, which summarizes requirements
stated in {{inputs}}, {{identity-binding}}, {{credential-requirements}},
and the input's own section:

* **Independent validation:** The credential is validated under its
  configured credential profile before it is used for resolution.
  Authentication, resolution, and permission remain separate
  ({{inputs}}).
* **Qualified identity:** The input yields an authenticated identity
  together with the credential authority or client-registration context
  that qualifies it. That qualified identity keys the Identity Binding
  ({{identity-binding}}).
* **Credential authority:** The input identifies that authority. For
  workload evidence, the IdP relies on the credential mechanism having
  authorized issuance for the asserted workload identity; a
  caller-supplied subject or agent identifier alone MUST NOT establish
  that identity. For
  dedicated clients, the IdP relies on the configured
  client-authentication method and approved binding.
* **Proof semantics:** The input states whether it is bearer evidence or
  binds a key, and what that proof establishes, so the IdP can apply
  configured policy ({{credential-requirements}}).

Credential acquisition is outside this profile. Audience validation
follows each input's credential specification and section; there is no
universal IdP audience.

| Input | Qualified identity | Reference |
|---|---|---|
| Dedicated client | Trusted assertion issuer and exact client `sub`, qualified by the IdP client-registration context | {{client-assertion-input}} |
| Existing platform JWT | Approved issuer and exact `sub`, with configured additional selectors | {{imported-jwt-input}} |
| SPIFFE JWT-SVID | Approved trust domain and exact SPIFFE ID in `sub` | {{jwt-svid-input}} |
| SPIFFE WIT-SVID | Approved trust domain and exact SPIFFE ID in the validated `sub` | {{spiffe-input}} |
| SPIFFE X.509-SVID | Approved trust domain and exact SPIFFE ID in the certificate's URI Subject Alternative Name | {{spiffe-input}} |
| Client Attestation | Trusted attester and validated `sub`, which identifies the OAuth client; the client-to-agent mapping is explicit | {{agent-evidence}} |
{: title="Agent-resolution inputs and qualified identities"}

Input support follows {{scope}}, which makes dedicated-client identity
mandatory to implement and the existing platform JWT the common
shared-client input; the other inputs are optional
({{optional-inputs}}). Except for the platform JWT, each input resolves
from the authentication context of the token request, with actor-token
parameters omitted; mode selection and rejection follow
{{actor-inputs}}.

### Optional Inputs {#optional-inputs}

The following inputs are OPTIONAL: SPIFFE JWT-SVID ({{jwt-svid-input}}),
Client Attestation ({{agent-evidence}}), and SPIFFE WIT-SVID and
X.509-SVID ({{spiffe-input}}).

### Bearer Evidence Limits {#credential-requirements}

Where issuer endorsement of the proof key is required, the deployment
needs a supported input that cryptographically binds the key, such as
Client Attestation under {{agent-evidence}} or the WIT-SVID input under
{{spiffe-input}}; DPoP co-presented with bearer JWT-SVID or unbound
platform JWT evidence establishes possession only. DPoP MUST NOT
substitute for a credential proof that the selected input requires.

Bearer evidence establishes the credential authority's assertion of the
workload identity, not a cryptographic binding of the current presenter
to that workload. An attacker who obtains acceptable bearer workload
evidence and satisfies the request's client authentication, Client
Association, and user-credential and delegation checks, or its
agent-authorization check, can obtain a grant
while impersonating the workload, with a grant proof key of its choice.
In the JWT-SVID path, the same bearer credential also satisfies client
authentication; that check is not an independent possession factor.

Short evidence lifetimes limit this exposure; sender-constraining the
output does not prevent it ({{baseline-costs}}).

## Identity Binding {#identity-binding}

An Identity Binding is keyed by the qualified identity of its input,
as listed for each input in {{evidence}}.

After validating the configured resolution input, the IdP MUST:

* Resolve the exact qualified client or workload identity to one active
  Agent Principal through an enabled Identity Binding; reject missing,
  ambiguous, or disabled mappings.
* Apply exact resolution even when client authentication permits a
  prefix match. A client identifier, including a {{CIMD}} URL,
  identifies the client, not the agent.

Similar names, unqualified identifiers, or a shared signing key MUST
NOT establish identity equivalence.

Permitting an Identity Binding to be disabled independently of the
Agent Principal and its other bindings lets a deployment withdraw one
resolution path while the others remain usable.
A disabled binding MUST NOT authorize new grant issuance. Disabling
a binding does not itself revoke outstanding tokens; their treatment
follows {{status-changes}}.

Before issuing a governed grant, the IdP MUST verify that a Client
Association permits the authenticated client to use the selected
Identity Binding, with the selected credential class, for the requested
acting relationship ({{configuration}}). Permission for delegated
issuance does not imply self-acting issuance, nor the reverse. The IdP
MUST NOT substitute the client's identity for the resolved actor.

A Client Association can authorize several Identity Bindings.
Authorization of one binding, a credential authority, a credential
class, or the Agent Principal itself MUST NOT imply authorization of
another binding unless the association's policy explicitly includes it.
No association overrides a disabled binding. Policy representation and
evaluation mechanisms are outside this profile.

For a dedicated client, Identity Binding determines which Agent Principal
the client represents. Client Association independently determines
whether that client may exercise the binding for the requested acting
relationship.
Deployments can administer both in one registration or policy object;
their identity and authorization semantics remain distinct.

A binding can remain valid while permission to use it is withdrawn,
preserving identity continuity across policy changes. Credential class
constrains the authorized resolution path even when several classes
can resolve to the same Agent Principal.

For example, one Agent Principal can carry a binding for each platform
the same agent runs on, each keyed by its own issuer and selectors:

~~~
 Agent Principal: agent-42

 B1  JWT-SVID, orchestrated runtime                     enabled
     trust domain  acme.example
     SPIFFE ID     spiffe://acme.example/ns/ml/sa/bot

 B2  platform JWT, managed container service            enabled
     issuer        https://sts.amazonaws.com/
     sub           arn:aws:iam::123456789012:role/agent-42-runtime
     selector      /https:~1~1sts.amazonaws.com~1/aws_account
                     = 123456789012

 B3  dedicated client, private_key_jwt                 disabled
     assertion iss  https://idp.example/clients/c1
     assertion sub  https://idp.example/clients/c1
~~~

The same agent resolves through B1 on the orchestrated runtime and
through B2 on the managed container service ({{aws-example}}). Neither
the SPIFFE ID nor the role identifies the agent downstream; both
resolve to agent-42, and the issued grant names that principal.
Disabling B3 prevents new issuance through that binding. It does not
change what a Client Association permits: an association naming B1 and
B2 continues to authorize them, subject to the remaining checks.

## Subject Resolution and Linking {#subject-resolution}

For ID-JAG, subject resolution identifies the user and linking
associates that identity with a local account. Self-acting access
resolves the agent as subject under {{wag-flow}}.
Subject identifiers, tenant relationships, and `aud_sub`, `aud_tenant`,
and `sub_id` follow Sections 3.1, 5, and 6 of {{ID-JAG}}; this profile adds
the following.

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

After validating the ID-JAG and its client and proof bindings, the RAS
MUST:

* Resolve exactly one local user in the authorized Target Tenant,
  qualifying `sub` by the validated IdP issuer and tenant relationship;
  IdP and RAS tenant identifiers are not interchangeable.
* Use `aud_sub` only when the IdP is authorized to assert local account
  identifiers for that Target Tenant, and MUST NOT use it to override
  a conflicting approved link.
* Reject conflicting identifiers or multiple local matches without
  retrying a weaker selector or another tenant.
* Resolve `act.iss` and `act.sub` separately under {{agent-correlation}};
  acting for a user does not link the agent to the user's account.

User-account links have these constraints:

* **Authority:** A link between an external user and a local account
  MUST rest on an authoritative association, not on email, username,
  or display-name equality alone.
* **Uniqueness:** Each qualified external identity MUST resolve to at
  most one local account per Target Tenant.
* **Continuity:** A link change MUST NOT transfer an outstanding grant
  or delegation to another user.
* **Failure:** The IdP and RAS MUST reject issuance for a disabled user
  or missing, ambiguous, or conflicting resolution ({{errors}}).

Linking mechanisms are deployment choices ({{operational-guidance}}).

## Agent Principal Correlation {#agent-correlation}

The Agent Principal identity is the pair of IdP issuer and agent
identifier, carried in ID-JAG as (`act.iss`, `act.sub`).
The RAS MUST:

* Resolve that qualified identity independently of the user's identity;
  a bare subject, display name, or OAuth client identifier MUST NOT
  replace it.
* Deny authorization that depends on a missing agent record, whether
  that record is provisioned in advance or created just in time under
  {{jit-correlation}}.

User-account and agent-record links are distinct. A changed Identity
Binding or local agent link MUST NOT transfer an existing delegation
to a different agent.

The RAS MUST preserve the complete validated `act` object in the access
token or its introspection context, including `iss`, `sub`, and any
`sub_profile`, under {{Section 3.6.3.2 of ACTOR-PROFILE}}. It MUST NOT add,
remove, or rewrite actor members.

Preservation applies to JSON members and values, not to serialization,
whitespace, or member order.

In particular, the RAS MUST NOT translate `act.sub` to its local
agent-principal identifier or replace `act.iss` with its own issuer.
The local agent record supports authorization and attribution; it does
not replace the federated actor. That rule concerns the actor of a delegated token; for self-acting
access the access token's subject is the local principal and the
qualified identity is retained under {{wag-redemption}}.

Where the RAS requires a local agent principal, deployments normally
have the IdP or its authorized directory connector provision and
synchronize that principal, keyed by the same pair, and propagate
activation and deactivation. Once deactivation is applied, the RAS
enforces {{applied-changes}}. No provisioning protocol is required
({{operational-guidance}}).

### Just-in-Time Correlation {#jit-correlation}

Where the RAS requires a local agent record and none exists for the
qualified pair in the authorized Target Tenant, resource policy MAY
permit the RAS to create one from a validated grant: from (`act.iss`,
`act.sub`) of an ID-JAG, or from (`iss`, `sub`) of a WAG under
{{wag-redemption}}. The policy is disabled by default and enabled per
governing issuer and Target Tenant. It serves resource domains that do
not accept provisioning and deployments in which the first grant can
arrive before provisioning completes. When it applies, the RAS:

* MUST key the created record by that exact pair and MUST NOT attach
  the pair to an existing record by name or other descriptive match;
* MUST apply local restrictions, retained revocation state under
  {{applied-changes}}, and local policy before issuance; and
* sets the record's initial eligibility by local policy; a record
  created ineligible denies the triggering request.

Creating the record is correlation, not authorization: the actor gate
({{actor-authorization}}) and resource policy still apply. A grant does
not carry the IdP's administrative status, so creation does not
substitute for propagating disablement; without provisioning, the RAS
learns of disablement only through local action or another signal
({{status-changes}}). Provisioning and reconciliation of a created
record are outside this document; {{AGENT-LIFECYCLE}} defines them for
Receivers that conform to it.

# Authorization Relationship {#authorization}

Validated identity does not grant authority. After resolution under
{{inputs}} and {{identity}}, the IdP MUST authorize issuance under
current assignments and policy for the resolved agent, authenticated
client, acting relationship, Governance and Target Tenants, RAS, resource,
and requested authority. The authority asserted in a delegated grant MUST be
bounded by both:

* The authority the IdP is authorized to assert for the user.
* The authority permitted by the agent's delegation authorization
  ({{delegation-authorization}}).

For a self-acting grant, the asserted authority MUST be bounded by the
Agent Authorization ({{agent-authorization}}).

The IdP authorizes cross-domain delegation within its configured
authority; the RAS and API determine effective resource and operation
authorization, including the actor gate ({{actor-authorization}}).
The IdP need not interpret every tool argument or business
object. An issuance decision that depends on those semantics requires
authoritative resource-domain evaluation, locally or through a trusted
policy service.

Issuance and denial follow these rules:

* The IdP MAY narrow scope, reflecting the result in the grant and
  response under {{RFC8693}}. It MUST return `invalid_scope` if no scope
  can be granted.
* It MUST NOT issue by dropping a required actor or binding,
  substituting an external identifier for the Agent Principal, or
  weakening proof requirements.
* Denied delegation MUST NOT fall back to self-acting access.

## Agent Authorization {#agent-authorization}

For self-acting access, the IdP MUST authorize the resolved Agent
Principal to access the requested RAS, resource, and authority on its
own behalf in the requested client and tenant context before issuing a
grant that names the agent as subject. The IdP MUST reject missing,
revoked, expired, or insufficient Agent Authorization. Valid
credentials, an active Identity Binding, or a Client Association MUST
NOT imply it, and it MUST NOT be inferred from a Delegation
Authorization involving the same agent. Denied self-acting access MUST
NOT fall back to delegated access or to a broader authority.

The basis for the decision is a deployment choice: administrator
assignment, organizational policy, or task authorization are all
acceptable. Assignment records and their storage are outside this
profile.

## Delegation Authorization {#delegation-authorization}

Before constructing `act`, the IdP MUST authorize the resolved Agent
Principal to act for the user in the requested client, tenant, RAS,
resource, and authority context. The IdP MUST reject missing, revoked,
expired, or insufficient delegation authorization. Valid credentials,
user sign-in, or a shared client MUST NOT imply that authorization or
permit one agent to use another agent's.

The basis for the decision is a deployment choice: user consent,
administrator assignment, organizational policy, or task authorization
are all acceptable. Approval records and their storage are outside this
profile. Pre-existing actor chains are rejected under {{actor-inputs}}.

## Authorization Lifetime {#authorization-lifetime}

Credential validity, the ID-JAG redemption window, and the duration of
downstream authorization are separate limits. Credential or ID-JAG
expiration does not by itself terminate an access token or RAS refresh
authorization already issued.

The RAS MUST limit access-token and refresh-authorization lifetimes
under its local policy ({{ras-refresh}}). The ID-JAG's `exp` limits
redemption, not subsequent access. This profile defines no portable
IdP-imposed deadline on downstream authorization ({{deadline-gap}});
it requires no shared approval record or correlated lifetime lookup.

If IdP approval requires a downstream lifetime condition that the
selected composition cannot enforce, the IdP MUST reject issuance
with `actor_unauthorized` for delegated issuance or `invalid_target`
for self-acting issuance. It MUST NOT discard that condition or treat
a shorter ID-JAG lifetime as enforcing it. Revocation follows
{{status-changes}}.

## Delegated Actor Authorization {#actor-authorization}

The authorization decisions belong to separate policy domains:

| Decision point | Question |
|---|---|
| IdP | May this agent act for this user toward the requested RAS, resource, and authority? |
| RAS | Does this resource domain accept the trusted IdP's delegation for this user, actor, client, and tenant? |
| API | Is this operation permitted by user authority, the actor gate, and the token's resource and authorization constraints? |
{: title="Authorization decision points"}

For delegated access, the RAS and API MUST enforce both:

* **User authority:** the requested operation is within the user's
  permissions and the grant or token's authorized scope and constraints.
* **Actor gate:** the issuer-qualified agent is permitted to act for
  that user in the selected tenant and resource, within the authorized
  delegation. A valid signature or an `act` claim alone does not open
  the gate; failure to establish it MUST result in denial.

The actor gate is an authorization condition, not a protocol object.
It can be implemented through an agent registration, tenant assignment,
consent policy, or another explicit rule. Requiring the agent to also
hold independent permissions on each object is local
policy, not a baseline requirement.

Every operation the API permits
MUST be covered by an applicable actor-gate authorization. The API MAY
evaluate the gate directly or rely on a validated RAS authorization
whose scope and freshness satisfy resource policy; a fresh policy-service
evaluation is not required for every request.

Issuing an ID-JAG under this profile asserts that the IdP authorized
the specified delegation within the grant's constraints. The RAS MUST
independently decide whether to accept that delegation under its local
user, actor, client, tenant, and resource policy. The grant does not
assert that the RAS's policy has been satisfied or convey the IdP's
underlying approval records.

The client identifier MUST NOT stand in for the actor in authorization.
Audit records that identify both the user and the issuer-qualified
actor, rather than the client identifier alone, preserve attribution.

# Delegated Access with ID-JAG {#delegated-flow}

This section realizes the federation model as a normative profile of
ID-JAG issuance and redemption, using the actor extension point in
{{Section 9.7 of ID-JAG}}. Where it is silent, ID-JAG applies
unchanged. {{profile-additions}} lists every change this profile makes
to ID-JAG; the sections after it state the processing rule behind each
row.

## Relationship to Base Specifications {#profile-additions}

This non-normative table lists the profile's additions to and narrowings
of its base specifications; the referenced sections define the
requirements.

| Area | Profile requirement | Defined in |
|---|---|---|
| Actor extension | Resolve the agent through an Identity Binding; authorize client use through a separate Client Association | {{identity-binding}} |
| Dedicated-client input | Resolve from authenticated client context; require the issuer identifier as the sole assertion audience and single-use `jti` | {{client-assertion-input}}, {{Section 4 of RFC7523bis}} |
| Other authentication-context inputs | Resolve the identity validated by SPIFFE or Client Attestation authentication | {{optional-input-profiles}}, {{actor-inputs}} |
| Actor representation | One actor with the Agent Principal as `act.sub` and the IdP as `act.iss`; replaces Actor Profile's credential-to-actor copying | {{actor-construction}} |
| Request narrowing | Configured resolution mode, exactly one resource, and non-empty scope required; actor-token parameters required in presented-evidence mode and rejected otherwise; no incoming actor chain | {{root-request}}, {{actor-inputs}} |
| Identity and client binding | Resolve users and agents separately; derive downstream `client_id` from an authoritative client-registration association | {{subject-resolution}}, {{agent-correlation}}, {{flow-configuration}} |
| Grant narrowing | One resource URI (a string; singleton arrays accepted), scope constraints, and input-specific expiration limits; bound profile requires DPoP and `cnf.jkt` | {{grant-issuance}}, {{redemption-validation}}, {{grant-protection}} |
| Resource processing | Preserve actor and tenant context; enforce the user authority and actor gate with the selected token protection | {{access-token-response}}, {{api-processing}} |
| Refresh narrowing | Explicit policy, client binding, preservation of proof binding and profile, and a finite absolute authorization expiration | {{ras-refresh}} |
| Error processing | Actor credential or resolution failures use `invalid_grant` rather than RFC 8693's default `invalid_request`; denial for a resolved actor uses `actor_unauthorized` | {{errors}} |
| Profile discovery | Identify supported governed profiles in existing ID-JAG metadata; trusted policy sets the minimum | {{metadata}} |
{: title="Additions and narrowings to the base specifications"}

## Prerequisites and Common Capabilities {#flow-configuration}

The IdP MUST issue an ID-JAG only under the applicable identity,
client, delegation, and target relationships in {{configuration}}.

The IdP MUST derive the ID-JAG `client_id` from an authoritative
association between the authenticated IdP client and that client's
registration at the target RAS. A client-supplied downstream client
identifier MUST NOT select or override that association, which is
the client registration association of {{configuration}}, not a Client
Association.

RFC 7523 client authentication at either server follows
{{client-assertion-input}}, and JWT-SVID authentication follows
{{jwt-svid-input}}; other configured methods MAY be used, and client
identifiers and keys MAY differ between servers.

Each implementing role MUST support the capabilities below for the
artifacts it produces or validates:

| Artifact | Mandatory-to-implement (MTI) capability |
|---|---|
| ID-JAG | IdP signing and RAS validation: `RS256` ({{Section 5 of RFC7523}}) |
| `private_key_jwt` | Client signing and IdP/RAS validation: `RS256` under {{Section 5 of RFC7523}} |
| JWT-SVID, where supported | IdP validation: `RS256` under {{Section 3.1 of SPIFFE-OAUTH}}, plus `ES256` added by this profile |
| DPoP, where supported or required | Client proof generation and server validation: `ES256`, a minimum {{RFC9449}} does not prescribe |
{: title="Mandatory-to-implement algorithms"}

Other algorithms permitted by the selected specification MAY be used
through trusted configuration and metadata.

An ID-JAG containing `cnf.jkt` is bound to the DPoP key proven at
issuance and redeemed under {{grant-protection}}; see
{{distributed-key-use}} and {{key-transition-gap}}.

## Grant Protection {#grant-protection}

Client authentication and all governance requirements remain
mandatory in either profile.

| Applicable profile | Grant-protection requirement |
|---|---|
| Bound governed agent access | The client MUST supply a DPoP proof at issuance; the IdP MUST reject its absence with `invalid_request`. The RAS MUST require `cnf.jkt` in the grant. |
| Governed agent access | DPoP support is OPTIONAL. The IdP and RAS MAY issue and accept grants without `cnf` only when trusted policy explicitly permits them for the client, trust relationship, and resource. |
{: title="Grant protection by profile"}

In both profiles:

* **Supplied proof:** A supplied DPoP proof MUST be validated under
  {{RFC9449}}. An endpoint that does not support DPoP MUST reject a
  request containing a DPoP proof with `invalid_request`; it MUST NOT
  silently ignore the proof. At issuance, a valid proof MUST result in
  `cnf.jkt` binding of the grant, as {{Section 9.8.1.1 of ID-JAG}}
  specifies for the ID-JAG.
* **Bound grant:** A grant containing `cnf` MUST have a valid, supported
  `jkt` binding. The RAS MUST require a fresh DPoP proof whose public
  key thumbprint matches exactly, as {{Section 9.8.1.2 of ID-JAG}}
  specifies for the ID-JAG. Missing proof, missing required binding,
  unsupported confirmation, or key mismatch MUST fail with
  `invalid_grant`.
* **Unbound grant:** When policy permits a grant without `cnf`, the
  client MAY present a DPoP proof only at redemption to obtain a
  DPoP-bound access token ({{access-token-protection}}). That proof does
  not retroactively bind the grant.
* **Credential proof:** Selecting governed agent access MUST NOT disable
  proof required by the agent-resolution input or client authentication
  method.

## Token Exchange {#exchange-request}

### Request {#root-request}

The client sends the token exchange request of {{Section 4.3 of ID-JAG}}
to the IdP token endpoint, authenticates as the configured client, and
supplies any proof required by {{grant-protection}}.

The following parameters are REQUIRED except where the resolution mode
specifies otherwise:

| Parameter | Value |
|---|---|
| `grant_type` | `urn:ietf:params:oauth:grant-type:token-exchange` |
| `requested_token_type` | `urn:ietf:params:oauth:token-type:id-jag` |
| `subject_token` | User subject credential issued for the authenticated client ({{subject-token-validation}}) |
| `subject_token_type` | `urn:ietf:params:oauth:token-type:id_token`, `urn:ietf:params:oauth:token-type:saml2`, or `urn:ietf:params:oauth:token-type:refresh_token` |
| `actor_token` | Omitted for authentication-context resolution; REQUIRED for a presented-evidence input under {{actor-inputs}} |
| `actor_token_type` | Omitted when `actor_token` is omitted; REQUIRED, with value `urn:ietf:params:oauth:token-type:jwt`, whenever `actor_token` is present |
| `audience` | One target RAS issuer identifier |
| `resource` | Exactly one resource URI under {{RFC8707}}, served by the RAS named in `audience` |
| `scope` | Non-empty scope string for the requested resource |
{: title="Token exchange request parameters"}

The `resource` URI conveys the Target Tenant through the configured
resource-to-tenant association, not the IdP's Governance Tenant.

**Resource:** The request MUST contain exactly one `resource` parameter.
A client requiring access to multiple resources MUST obtain a separate
ID-JAG for each resource. The IdP MUST reject multiple `resource`
parameters with `invalid_target`.

**Scope and authorization details:** `authorization_details` MAY
accompany the required non-empty `scope` and is processed under ID-JAG.
One resource per grant avoids carrying different scope ceilings for
different resources; the IdP MUST constrain all granted scope and
`authorization_details` to that resource. If requested authorization
details cannot be confined to it, the IdP MUST reject the request with
`invalid_authorization_details` under {{Section 6 of RFC9396}} rather
than authorize additional resources.

### Subject Token Validation {#subject-token-validation}

The IdP MUST support ID Token subjects, MAY support SAML 2.0 assertion
subjects, and MAY support its own refresh tokens when agreed in client
configuration, validating each under {{Section 4.3.3 of ID-JAG}}:

* **ID Token:** the audience MUST identify the authenticated IdP client.
* **SAML 2.0 assertion:** The IdP MUST map the assertion's Audience to
  the authenticated client under {{Section 4.5 of ID-JAG}} and resolve
  the subject under {{Section 3.2 of ID-JAG}}.
* **Refresh token:** The IdP MUST establish that the token's retained
  authorization permits the requested target and authority; possession
  of a refresh token or an `offline_access` grant alone MUST NOT
  establish that permission. The retained authorization can include an
  explicitly associated cross-domain delegation authorization, whose
  representation and provisioning are local to the IdP. OpenID Connect
  scope names do not themselves map to resource-specific permissions. Any binding retained
  with the refresh token MUST be enforced rather than bypassed by
  selecting another agent-resolution input, with conflicts rejected as
  `invalid_grant`.

All subject inputs require a current validated agent-resolution input
and delegation authorization under {{delegation-authorization}}. User
access tokens are not subject inputs ({{access-token-subject-gap}});
JWT encoding alone does not make an access token an ID Token.

### Agent Resolution Input Validation {#actor-inputs}

After client authentication, the IdP MUST determine the resolution mode
from trusted configuration for the authenticated client, applicable
profile, and target. If that configuration does not establish an
unambiguous mode, it MUST reject the request with `invalid_request`.
The presence or absence of actor-token parameters MUST NOT select or
change that mode.

* **Authentication-context resolution:** The IdP MUST use the identity
  validated during client authentication for this token request under
  the configured input in {{evidence}}. The credential class MUST match
  the authentication method. Client-supplied identity hints and context
  from another request or session MUST NOT substitute for that identity.
  The client MUST omit `actor_token` and `actor_token_type`; the IdP MUST
  reject either parameter with `invalid_request`, including a duplicate
  authentication credential.
* **Presented-evidence input:** In delegated issuance, the IdP MUST
  require both `actor_token` and `actor_token_type`, and the type MUST be
  `urn:ietf:params:oauth:token-type:jwt` ({{errors}}); in self-acting
  issuance, the evidence is the subject token ({{wag-request}}). Validate the
  separate platform JWT under {{imported-jwt-input}}. Missing or
  rejected evidence MUST NOT trigger resolution from authentication
  context.

In delegated issuance both modes proceed through {{actor-construction}},
and a governed request MUST result in the required governed `act` or
fail; omitting actor-token parameters in authentication-context mode
does not request ordinary EMA or subject-only impersonation.

The IdP MUST select exactly one configured platform credential class for
actor evidence, or reject with `invalid_request`. Native SPIFFE and
Client Attestation inputs use authentication context and MUST NOT be
accepted through presented-evidence mode.

Credential classes MUST have mutually exclusive validation rules under
{{Section 3.12 of RFC8725}}. Within one token request, rejection under the
selected class's validation or authorization rules MUST NOT trigger
validation under another class.

To preserve the single user-to-agent relationship, the IdP MUST reject
an agent-resolution JWT or ID Token containing `act`, and a refresh-token
subject whose retained authorization contains an actor chain.

### Actor Resolution and Construction {#actor-construction}

After credential validation, the IdP MUST resolve the agent under
{{identity}} and authorize issuance under {{authorization}}. The
ID-JAG MUST contain one `act` object with:

* `sub`: the Agent Principal identifier from the Identity Binding.
* `iss`: this IdP's issuer identifier.

These values MUST come from the approved mapping, even when source and
governed identifiers coincide. For presented-evidence inputs this replaces
credential-to-actor copying in {{Section 6.3 of ACTOR-PROFILE}}.

The object MUST follow {{Section 3.4 of ACTOR-PROFILE}}, including its
`sub_profile` recommendation and unclassified-actor rules. Any
`sub_profile` MUST reflect the IdP's authoritative classification.
Being an Agent Principal does not itself establish the `ai_agent`
classification of {{ENTITY-PROFILES}}.

### Grant Issuance {#grant-issuance}

The ID-JAG MUST use the format and claims of {{Section 3.1 of ID-JAG}}
and additionally satisfy:

| Claim | Required result |
|---|---|
| `sub` | Same user as the validated subject credential, expressed in the IdP's subject namespace for the RAS |
| `act` | Agent Principal actor constructed under {{actor-construction}} |
| `cnf.jkt` | Thumbprint of the grant proof key when DPoP is used at issuance; REQUIRED for bound governed agent access ({{grant-protection}}) |
| `resource` | The authorized resource URI, issued as a JSON string; receivers also accept a single-element array under {{redemption-validation}} |
| `scope` | Non-empty authorized scope string, no broader than the approved request |
| `client_id` | The client's registration identifier at the RAS, derived under {{flow-configuration}} |
{: title="ID-JAG claims profiled by this document"}

The IdP MUST NOT issue a grant if it cannot determine an unambiguous
user, actor, downstream client, or tenant relationship.

Grant lifetime has three limits:

* **Configured limit:** The grant lifetime SHOULD be at most five
  minutes and MUST NOT exceed the configured lifetime limit.
* **Subject credential:** The grant's expiration MUST NOT exceed the subject
  credential's expiration, determined below.
* **Agent-resolution input:** The grant MUST NOT outlive the validated
  resolution credential, using the bound in the following table. The
  dedicated-client assertion is the exception: it MUST be valid when the
  request is authenticated, but it authenticates one transaction and
  does not cap the grant.

| Input | Lifetime bound on the grant |
|---|---|
| Dedicated client assertion | None; the configured and subject-credential limits apply |
| Platform JWT | The effective evidence deadline in {{imported-jwt-input}} |
| JWT-SVID | Its `exp` |
| WIT-SVID and Client Attestation | The credential's `exp`; the PoP JWT adds no limit |
| X.509-SVID | The earliest `notAfter` in the validated certificate path, excluding the trust anchor |
{: title="Grant lifetime bound by agent-resolution input"}

The subject credential's expiration is:

* **ID Token:** its `exp` claim.
* **SAML assertion:** the earliest applicable `NotOnOrAfter` in the
  assertion's `Conditions` and the `SubjectConfirmationData` used to
  validate the subject. If neither supplies an expiration bound, the
  IdP MUST reject the subject as `invalid_grant`.
* **Refresh token:** its expiry, if the IdP records one. Otherwise the
  configured and agent-resolution input limits apply; absence of
  a recorded expiry does not authorize an unlimited grant lifetime.

### Successful Response {#exchange-response}

The response follows {{Section 4.3.4 of ID-JAG}}. For a bound grant,
the client MUST retain the DPoP key for redemption and SHOULD inspect
the grant to confirm that `cnf.jkt` identifies that key, as specified in
{{Section 9.8.1.1 of ID-JAG}}.

## ID-JAG Redemption {#redemption}

### Request {#redemption-request}

The client sends the request of {{Section 4.4 of ID-JAG}} with the
proof required by {{grant-protection}} and the applicable access-token
protection. These additional parameters are REQUIRED unless marked
OPTIONAL:

| Parameter | Value |
|---|---|
| `resource` | Exactly one parameter whose value equals the grant's resource URI |
| `scope` | OPTIONAL subset of the grant's scope; if omitted, the grant's scope is the upper bound |
{: title="Redemption request parameters"}

The confirmation checks of {{Section 9.8.1.2 of ID-JAG}} apply to this
grant type ({{bound-grant-coordination}}).

### Grant Validation {#redemption-validation}

The RAS MUST perform ID-JAG validation and additionally:

1. **Actor:** Require a single `act` object under Actor Profile's rules,
   with non-empty `iss` and `sub` and no nested `act`. Require `act.iss`
   to equal the ID-JAG issuer and configured trust to authorize
   assertion of that namespace.
2. **Proof and client:** Enforce {{grant-protection}}, including the
   configured minimum profile even when `cnf` is absent, and
   independently authenticate the client identified by `client_id`.
3. **Authority:** Validate the resource, scope, and authorization details:
   * **Resource claim:** Require `resource` to be one URI, encoded as a
     JSON string or a single-element JSON array
     ({{Section 3.1 of ID-JAG}}), and normalize it to that URI; reject a
     missing or invalid value, an empty array, or a multi-element array
     with `invalid_grant`.
   * **Requested resource:** The RAS MUST reject multiple `resource`
     parameters or a requested resource different from that URI with
     `invalid_target` under {{Section 2 of RFC8707}}.
   * **Scope:** Require the grant's `scope` claim to be a non-empty
     string. A supplied request `scope` MUST be a non-empty subset of
     that claim or the RAS MUST return `invalid_scope`.
   * **Authorization details:** Apply ID-JAG's processing for
     `authorization_details`; reject the grant with `invalid_grant`
     if its authority extends beyond that resource.
4. **Local authorization:** Resolve the user under
   {{subject-resolution}} and the Agent Principal actor under
   {{agent-correlation}}, and apply current RAS policy to the
   user/actor relationship under {{actor-authorization}}, client,
   tenant, and resource. A valid grant sets an authority ceiling; it
   does not require issuance.

### Access Token Issuance and Response {#access-token-response}

After validation and authorization, the RAS MUST issue an access token
with these claims under {{RFC9068}}, or equivalent context through
{{introspection}}:

* **Identity:** Resolved user as subject and validated `act` unchanged
  under {{agent-correlation}}. Neither the authenticated client nor the
  local agent-principal identifier replaces the actor.
* **Authority:** Redeemed resource as audience and non-empty authorized
  `scope` (otherwise `invalid_scope`), without broadening authority.
* **Protection:** The binding selected under {{access-token-protection}}.
* **Tenant:** By default the tenant is carried by the tenant-specific
  resource URI, which becomes the access-token audience under
  {{Section 3 of RFC8707}}. A deployment MAY instead carry it in a
  configured tenant claim or authoritative token context.
* **Authorization details:** Effective `authorization_details`, when
  used, in the JWT claim or introspection member under {{Section 9 of RFC9396}}.
  Narrowing or translating authorization MUST NOT discard restrictions
  in those details or expand the approved authority.
* **Expiration:** Within RAS-local lifetime policy under
  {{authorization-lifetime}} and any applicable refresh-authorization limit.

The response follows {{Section 4.4.2 of ID-JAG}}; the client MUST reject
an output that does not satisfy its configured protection requirement.

### Access-Token Protection {#access-token-protection}

The RAS MUST issue a sender-constrained access token unless the resource
is explicitly configured to permit bearer tokens. The permitted
protection is selected through trusted client and resource
configuration before issuance, not by a request flag, and a validation
failure MUST NOT trigger a weaker mode.

| Selected protection | Access token |
|---|---|
| DPoP | `cnf.jkt` identifies the validated redemption proof key, which also matches the grant binding when present |
| Mutual TLS | `cnf.x5t#S256` identifies the client certificate validated at redemption; the response uses `token_type=Bearer` |
| Bearer | No `cnf` |
{: title="Access-token protection modes"}

For mutual TLS with a bound grant, the client MUST also prove possession
of the grant's DPoP key in the same redemption request; certificate
possession alone does not redeem the grant. The access token then
carries `cnf.x5t#S256` but not `cnf.jkt`, under the allowance in
{{Section 5 of RFC9449}} for access tokens that are not DPoP-bound;
receipt of the grant proof does not override the configured
access-token protection. A native mutual-TLS-bound grant is future
work ({{excluded-compositions}}).

The RAS MUST NOT copy the grant's `cnf` into an access token whose
binding will not be enforced, and clients and APIs MUST NOT treat a
constrained token as an unconstrained bearer token or bypass an
unrecognized confirmation method.

### Distributed Platforms and Key Use {#distributed-key-use}

A sender-constrained credential requires proofs from its bound key,
through local custody or an authorized signing arrangement; this
document defines no transition to another key ({{key-transition-gap}}).
Bound-grant issuance and redemption therefore require the same key
holder. A DPoP access token is usable only by a broker holding that
key, including when it proxies an authorized worker request, or by a
worker that holds the same key or obtains request-specific proofs from
its authorized key holder; handing only the token to a worker with an
independent key is insufficient. Remote signing interfaces are outside
this profile; remote signing or shared key custody does not establish
an independent worker binding and expands the trusted computing base.

Control-plane and worker splits that cannot share the grant proof key
use governed agent access instead: the control plane obtains an unbound
ID-JAG and the worker redeems it with its own DPoP proof, binding the
access token to the worker's key ({{grant-protection}}).

### Opaque Access Tokens and Introspection {#introspection}

The RAS MAY issue an opaque access token instead of a JWT when the API
obtains equivalent context through token introspection {{RFC7662}}.
For an active token, the response provides the following context:

* **Identity and authority:** The response MUST carry `sub`, `aud`,
  `scope`, `client_id`, and the validated `act` object unchanged, using
  the `act` introspection member registered by {{Section 7.5 of RFC8693}}.
* **Context:** The response MUST preserve the Target Tenant
  representation and any effective `authorization_details` required by
  {{access-token-response}}.
* **Protection:** For a bound token the response MUST carry `cnf` with
  `jkt` under {{Section 6.2 of RFC9449}} or `x5t#S256` under
  {{Section 3.2 of RFC8705}}, and the API MUST enforce it as it would
  the JWT claim.
* **Caching:** A cached active response MUST NOT be used beyond `exp`
  or the freshness limit of the resource's disablement policy. Without
  `exp`, the API MUST introspect again for subsequent requests rather
  than reuse an active response. This restriction narrows
  {{Section 4 of RFC7662}} so cached authorization cannot outlive an
  expiration unknown to the API.

### RAS Refresh Tokens {#ras-refresh}

The RAS SHOULD NOT issue refresh tokens, retaining
{{Section 4.4.3 of ID-JAG}}, but MAY do so for authorized long-running
work under explicit policy. The RAS MUST bind each refresh token to the
authenticated client and apply the first applicable additional
sender-binding rule below. Bindings required by the
client-authentication method, such as {{Section 10.3 of ATTEST}},
remain applicable in every row; refresh-token rotation does not
replace them.

| Redemption context | Refresh-token requirement |
|---|---|
| Grant contains `cnf.jkt` | Retain the grant's DPoP key binding, regardless of access-token protection |
| Unbound grant; DPoP proof used at redemption | Bind to the validated redemption proof key |
| No DPoP proof; certificate-bound access token | Bind to the validated mutual-TLS certificate |
| Neither DPoP nor certificate binding | Retain any authentication-method binding; if none applies, require explicit policy permitting client-bound refresh without sender constraint and use rotation under {{Section 4.14 of RFC9700}} |
{: title="Refresh-token sender binding"}

A refresh request MAY include one `resource` parameter under
{{Section 2.2 of RFC8707}} solely to identify the retained resource.
If omitted, the RAS MUST use that resource. If supplied, its value MUST
match the retained resource exactly. The RAS MUST reject multiple
values or a different resource with `invalid_target`.

On every refresh, the RAS MUST:

* **Client and proof:** Authenticate the bound client, enforce the
  retained authentication-method binding, and enforce any additional
  sender binding under RFC 9449 or RFC 8705. Dropping or replacing a
  sender binding requires a new grant.
* **Authorization context:** Preserve the user, qualified actor, Target
  Tenant, resource, and authorization ceiling, including
  `authorization_details`. Apply current local user and actor policy
  and {{Section 6 of RFC9396}}.
* **Profile:** Enforce current minimum-profile policy against the
  profile under which the grant was accepted; reject with
  `invalid_grant` if it no longer qualifies. Adding a proof does not
  upgrade that authorization.
* **Lifetime:** Enforce a finite absolute authorization expiration set
  at issuance under local policy and an inactivity limit under
  {{RFC9700}}. Rotation, refresh, or repeated redemption of the same
  ID-JAG MUST NOT reset the absolute expiration.
* **Output:** Issue access tokens under {{access-token-response}} and
  {{access-token-protection}}, expiring no later than the absolute
  authorization expiration.

Absolute expiration prevents indefinite renewal from one ID-JAG without
a fresh IdP decision; continued access beyond it requires a new ID-JAG.

### Applied Disablement and Revocation {#applied-changes}

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
* Report revoked or disabled authorization as inactive under
  {{RFC7662}}.

These rules apply to authorization derived from either realization.

## Token Endpoint Error Responses {#errors}

Token endpoint errors follow {{Section 5.2 of RFC6749}} and the
applicable extension, authentication, and proof specifications.
Servers MUST validate client authentication, credentials, and proofs
before authorization. Proof, grant-binding, grant-claim, and
authorization-detail failures use the errors specified in
{{grant-protection}}, {{spiffe-input}}, {{redemption-validation}}, and
{{root-request}}. This profile also specifies the following outcomes:

| Failure | Error |
|---|---|
| Unsupported or invalid requested authorization details | `invalid_authorization_details` ({{Section 8 of RFC9396}}) |
| Unsupported input combination, ambiguous credential classification, or unsupported `actor_token_type` in presented-evidence mode | `invalid_request` |
| No unambiguous configured resolution mode, actor-token parameters in an authentication-context mode, a method inconsistent with that mode, or missing actor-token parameters in presented-evidence mode | `invalid_request`; no mode fallback |
{: title="Request errors"}

| Failure | Error |
|---|---|
| Unacceptable `resource` parameter at exchange, redemption, or refresh, including multiple values or a target outside the grant or retained authorization | `invalid_target` under RFC 8707 |
| Target Tenant cannot be resolved for the requested resource, or no client registration association exists for the requested RAS ({{flow-configuration}}) | `invalid_target` |
| Unacceptable requested scope, invalid scope reduction, or no non-empty scope can be issued | `invalid_scope` |
{: title="Target and authority errors"}

| Failure | Error |
|---|---|
| Invalid subject or agent-resolution credential, disallowed inbound actor chain, or invalid ID-JAG | `invalid_grant` |
| User cannot be resolved, user or required link is disabled, or subject identifiers conflict | `invalid_grant`; no token or automatic linking fallback |
| Absent, disabled, or ambiguous Identity Binding, or no active Agent Principal can be resolved | `invalid_grant` |
| Governance Tenant cannot be resolved unambiguously from trusted identity and configuration context | `invalid_grant` |
| Resolved Agent Principal, but no Client Association permits the selected binding and acting relationship, or delegation is unauthorized | `actor_unauthorized`, as defined by Actor Profile, with HTTP 400 |
{: title="Identity resolution and delegation errors"}

Agent-resolution credential failures intentionally use `invalid_grant`
instead of the default `invalid_request` of
{{Section 2.2.2 of RFC8693}}. Client authentication failures use the
authentication method's error, including when the same credential
supplies an agent-resolution input.

Error descriptions SHOULD NOT reveal identity, binding, or policy
details beyond those disclosed by the error category. Distinguishing
`invalid_grant` from `actor_unauthorized` reveals that an actor was
resolved but denied authorization, including to a holder of stolen
bearer evidence who satisfies the request's other authentication
requirements, but not which binding-resolution check failed.

## Continuing Access {#continuing-access}

Deployments select a renewal model before scheduling unattended work:

| Mechanism | Conditions |
|---|---|
| Redeem an existing ID-JAG | Grant remains valid; any required proof and current RAS policy apply ({{redemption}}) |
| Obtain a new ID-JAG | Valid subject credential, current agent-resolution input, and a fresh IdP authorization decision ({{exchange-request}}) |
| RAS refresh | Preserves authorization at the same RAS within its lifetime and policy limits ({{ras-refresh}}) |
{: title="Renewal mechanisms"}

An IdP refresh token can supply the subject credential for a new
exchange only when eligible under {{subject-token-validation}};
otherwise renewal may require user interaction.

## Client Token Reuse {#client-token-reuse}

To govern reuse, the client associates each cached grant, access
token, and refresh token with its authorized context:

* User and Agent Principal.
* Governance and Target Tenants.
* OAuth client registrations, target RAS, and resource.
* Authority, applicable profile, and proof binding.

It MUST reuse a token or grant only when that context authorizes the
operation. A shared client
identifier or matching scope alone MUST NOT permit reuse across agents,
users, or tenants.

The association can use trusted request and configuration context;
clients need not parse opaque tokens. If the client cannot establish
the required association, it MUST obtain a token or grant for the current
context. A credential change alone need not invalidate cached tokens
when the governed principal and authorization context remain the same.

## Resource Server Processing {#api-processing}

The RAS and API MUST establish profile applicability through trusted
issuer, client, and resource configuration or authoritative token-issuance
context. The RAS MUST NOT issue governed and ordinary tokens for the
same client and resource unless the API can distinguish them through
validated claims or authenticated introspection context. This profile
defines no in-band discriminator: the RAS MUST issue tokens such that
the API can determine, from trusted token context, which adoption
profile and acting relationship authorized them ({{wag-api}}).

The API MUST reject ambiguous applicability and reject missing or
malformed `act` for a configured governed delegated population;
self-acting tokens carry no `act` ({{wag-api}}). An ordinary `act`
claim alone does not establish governed issuance.

For tokens subject to this profile, the API MUST validate access tokens
under {{RFC9068}}, or obtain the same context under {{introspection}},
and MUST enforce the following requirements:

* **Identity:** For delegated tokens, require one `act` object with
  non-empty `iss` and `sub` and no nested `act`. Trust configuration
  MUST authorize the RAS to
  assert that IdP-qualified agent identity; `act.iss` need not equal the
  access-token issuer.
* **Protection:** Enforce the configured resource mode and all token
  confirmation claims. Validate DPoP under {{RFC9449}}, certificate
  binding under {{RFC8705}}, or permitted bearer use under {{RFC6750}}.
* **Authority:** Require non-empty `scope` with its defined type.
  Enforce user permissions and the actor gate under
  {{actor-authorization}} and {{Section 8 of ACTOR-PROFILE}}. Enforce any
  effective `authorization_details` under {{RFC9396}}, using the API's
  defined semantics for their combination with scope.
* **Tenant:** Resolve exactly one authorized Target Tenant from token
  context, as represented under {{access-token-response}}; a request
  parameter alone cannot establish it. Verify that it matches the
  tenant of the requested operation. Missing, ambiguous, or conflicting
  tenant context MUST result in denial.

Revocation visibility for offline validation and cached introspection
is bounded as described in {{status-changes}}.

If the API delegates authorization evaluation to a policy decision
service, it MUST preserve the distinction between the user, the
issuer-qualified Agent Principal, and the OAuth client, and supply the
tenant and token constraints needed to evaluate the requested operation.
For a self-acting token, the local principal stands for the Agent
Principal.
{{AUTHZEN}} is one optional evaluation interface; this profile defines
no mapping to it. A policy permit does not override the token's
constraints.

### Error Responses {#resource-errors}

Challenges and scope errors use the selected scheme: `DPoP` under
{{Section 7.1 of RFC9449}}, or `Bearer` under {{RFC6750}} for bearer
and mutual-TLS tokens.

| Failure | Response |
|---|---|
| Missing or invalid required actor claims; unauthorized namespace assertion; missing, ambiguous, or conflicting token tenant context | HTTP 401, `invalid_token` |
| Denial for a valid actor identity | HTTP 403, `actor_unauthorized` under {{Section 8.2 of ACTOR-PROFILE}} |
{: title="Resource server error responses"}

Actor denial MUST NOT use `insufficient_scope`. The API MUST NOT expose
actor-specific rejection details outside the trust domain.

# Self-Acting Access with WAG {#wag-flow}

This section realizes the federation model for self-acting access: the
Agent Principal is the subject of a Workload Authorization Grant (WAG)
{{WAG}} issued by the IdP and redeemed at the RAS. It is the peer of
{{delegated-flow}}. The same resolution inputs, except X.509-SVID
({{wag-request}}), and the same Identity Binding, client authorization,
grant protection, access-token protection, and resource processing
apply, with the differences stated here; where this section
is silent, {{delegated-flow}} applies with the WAG in place of the
ID-JAG.

WAG-00 defines a platform-issued bearer grant and leaves IdP issuance,
proof of possession, and identifier registrations open
({{Section 5 of WAG}} and its list of open issues); this section defines
that composition. The WAG token type and JWT type are WAG's to register;
this document uses them as provisional values ({{wag-gaps}}), and the
processing rules do not depend on their final spelling.

## Differences from Delegated Access {#wag-differences}

| Area | Delegated ID-JAG | Self-acting WAG |
|---|---|---|
| Subject | User, resolved from the subject credential | Agent Principal, resolved from the agent-resolution input |
| Actor | Agent Principal in `act` | None; `act` MUST be absent |
| IdP authorization | Delegation Authorization for the user and agent | Agent Authorization for the agent alone ({{agent-authorization}}) |
| Client permission | Client Association for delegated issuance | Client Association for self-acting issuance, a separate permission |
| RAS subject | Local user, with the agent preserved in `act` | Local agent principal correlated under {{agent-correlation}}; the issuer-qualified identity is retained for audit |
| API check | User authority and the actor gate | The agent's own authority; no actor gate |
| Refresh | RAS refresh under explicit policy | None; WAG prohibits refresh tokens |
{: title="Self-acting differences from delegated access"}

## Self-Acting Issuance {#wag-issuance}

Self-acting issuance is one operation with two resolution modes. The
IdP MUST:

1. Authenticate the client and validate the resolution input under
   {{evidence}} and {{actor-inputs}}.
2. Resolve the Agent Principal through an active Identity Binding
   ({{identity-binding}}) from the configured resolution input:
   * **Presented-evidence resolution:** an independently validated
     workload credential presented in the request, the presented-evidence
     input of {{actor-inputs}} carried as the subject token here.
   * **Authentication-context resolution:** the authenticated client
     identity, with no separate credential.
3. Verify a Client Association that permits the authenticated client to
   use that binding for self-acting issuance. Permission for delegated
   issuance does not imply this permission.
4. Apply Agent Authorization ({{agent-authorization}}) for the requested
   RAS, resource, and authority. No user is involved.
5. Apply {{grant-protection}} and issue the WAG with the claims in
   {{wag-claims}}; in the bound profile the request carries a DPoP proof
   and the grant carries `cnf.jkt`.

The client then redeems the WAG at the RAS ({{wag-redemption}}), which
correlates the pair to a local principal, applies current resource
authorization, and issues an access token. {{wag-example}} shows the
messages.

Credentials are inputs used to resolve a governed principal; none of
them is the subject of the grant. The WAG names the resolved Agent
Principal.

## Issuance Request {#wag-request}

The request uses token exchange because its output is an assertion for
redemption at another token endpoint, which only {{RFC8693}} can label
as such through `issued_token_type`. Parameters follow {{root-request}}
with these differences:

| Parameter | Value |
|---|---|
| `requested_token_type` | `urn:ietf:params:oauth:token-type:wag` (provisional) |
| `subject_token`, `subject_token_type` | Per resolution mode, below |
| `actor_token`, `actor_token_type` | MUST be absent |
| `audience`, `resource`, `scope` | As in {{root-request}} |
{: title="Self-acting issuance request"}

**Presented-evidence resolution.** The workload credential is the
subject token, with `subject_token_type`
`urn:ietf:params:oauth:token-type:jwt`, and the client authenticates
separately; the existing platform JWT input ({{imported-jwt-input}}) is
presented this way. This is the natural token exchange shape: the token
represents the party on whose behalf the request is made, and the IdP
resolves the governed principal from it, as it resolves the user from an
ID Token in delegated access. The classification and mutual-exclusion rules of
{{actor-inputs}} apply to that subject token; its actor-construction
and `act` requirements do not.

**Authentication-context resolution.** The subject is the authenticated
client itself and no separate token exists. {{RFC8693}} requires a
subject token and offers no way to state that the authenticated client
is the subject. This profile therefore presents the authentication
credential as the subject: a client authenticated with a
JWT MUST repeat that JWT, byte for byte, as `subject_token` with type
`urn:ietf:params:oauth:token-type:jwt`: the RFC 7523 assertion, the
JWT-SVID, the WIT-SVID, or the Client Attestation JWT itself, not an
accompanying proof-of-possession JWT. The IdP MUST reject a subject
token that is not byte-identical to the credential presented for
authentication. This prevents a client from substituting another
party's assertion as the subject, and one request carrying the same
assertion in both parameters does not violate the single-use `jti`
rule of {{client-assertion-input}}. It does not make the credential the
agent: the Identity Binding resolves the authenticated client to the
Agent Principal exactly as in delegated dedicated-client resolution. A
client authenticated by X.509-SVID over mutual TLS presents no JWT and
has no self-acting issuance under this profile. The same reuse of an
authentication assertion appears in {{Section 6.3.1 of ACTOR-PROFILE}},
which presents it as `actor_token`. A token exchange in which the
authenticated client is the subject without a subject token would
simplify this presentation ({{wag-gaps}}).

Mode selection is configured under {{actor-inputs}}. Presence of
actor-token parameters is `invalid_request`.

## Grant Claims {#wag-claims}

The WAG subject identifies the governed Agent Principal, not the
credential subject from which it was resolved. Changing the platform,
credential, replica, or execution environment behind an Identity
Binding does not change the subject. The grant is a JWT with the
following claims, aligned with the claim set of {{Section 5.1 of WAG}}:

| Claim | Value |
|---|---|
| `iss` | The IdP issuer identifier |
| `sub` | The Agent Principal identifier from the Identity Binding |
| `aud` | The target RAS issuer identifier |
| `client_id` | The client's registration identifier at the RAS ({{flow-configuration}}) |
| `resource` | The authorized resource URI as a JSON string |
| `scope` | Non-empty authorized scope, no broader than the request |
| `cnf.jkt` | Grant proof key thumbprint when DPoP is used; REQUIRED in the bound profile |
| `exp`, `iat`, `jti` | As for the ID-JAG, under the limits in {{grant-issuance}} |
{: title="IdP-issued WAG claims"}

The JWT `typ` is `wag+jwt` (provisional). The grant MUST NOT contain
`act`. Its lifetime follows {{grant-issuance}}: the configured limit
applies, and the grant MUST NOT outlive the validated resolution
credential, except that a dedicated-client assertion authenticates one
transaction and does not cap the grant. The response follows
{{exchange-response}} with `issued_token_type` set to the WAG token
type.

## Redemption and Access Tokens {#wag-redemption}

The client redeems the WAG at the RAS token endpoint with
`urn:ietf:params:oauth:grant-type:jwt-bearer`, as WAG already uses, and
the request of {{redemption-request}}. The RAS MUST:

1. Validate the grant under {{RFC7523}}, consistent with
   {{Section 5 of WAG}}; require `iss` to be a configured governing IdP
   for the asserted agent namespace; and apply {{grant-protection}} and
   client authentication as in {{redemption-validation}}.
2. Resolve the pair (`iss`, `sub`) under {{agent-correlation}} to one
   local agent principal in the authorized Target Tenant. The RAS MUST
   have that authorized correlation before issuance; for governed agents
   this replaces the required acceptance of previously unseen
   identifiers in {{Section 7 of WAG}}. Just-in-time correlation, where
   resource policy permits it, is defined in {{jit-correlation}}.
3. Validate resource, scope, and authorization details as in
   {{redemption-validation}}, and apply current RAS policy for the
   agent, client, tenant, and resource. A valid grant sets an authority
   ceiling; it does not require issuance.
4. Issue an access token under {{access-token-response}} and
   {{access-token-protection}}, with the local agent principal as `sub`,
   no `act`, and the tenant, authority, and protection rules unchanged.
   The RAS MUST NOT issue a refresh token for a WAG redemption;
   continued access obtains a new WAG under current IdP and RAS policy.

The access token's `sub` is the local principal. This differs from
delegated access, where the IdP-qualified actor survives in `act`. The
RAS retains the correlation between the WAG's (`iss`, `sub`) and the
local principal for the life of the derived authorization, which
supports revocation by qualified agent ({{applied-changes}}) and audit.
The token and its introspection response need not carry it; this
document defines no claim or member for that purpose.

## Resource Processing {#wag-api}

The API applies {{api-processing}} without the actor gate: it enforces
the agent's own permissions, the token's authority constraints, the
Target Tenant, and the selected protection. A governed self-acting
token has no `act`.

{{api-processing}} requires the RAS to issue access tokens from which
the API can determine the acting relationship. Separate client
registrations, audiences, or issuers for the two populations satisfy
that requirement. The absence of `act` alone does not: a delegated
token lacking `act` would otherwise be accepted as self-acting.

## Errors {#wag-errors}

Token endpoint errors follow {{errors}} with these additions:

| Failure | Error |
|---|---|
| Actor-token parameters present in a self-acting exchange | `invalid_request` |
| Subject token is not byte-identical to the authentication credential in authentication-context resolution | `invalid_grant` |
| Resolved Agent Principal, but no Client Association permits self-acting issuance for the binding | `unauthorized_client`; no actor is asserted, so the delegated path's `actor_unauthorized` does not apply |
| Agent not authorized for the requested RAS or resource | `invalid_target` |
| Agent not authorized for the requested authority | `invalid_scope` |
| WAG whose `sub` has no authorized correlation at the RAS | `invalid_grant` |
{: title="Self-acting error additions"}

## Profile Identifiers {#wag-profiles}

The self-acting realization uses the adoption profiles of {{adoption-profiles}}
under its own identifiers,
`urn:ietf:params:oauth:grant-profile:wag-governed-agent` and
`urn:ietf:params:oauth:grant-profile:wag-agent-federation`. Grant
protection, downgrade prevention, and discovery follow
{{grant-protection}}, {{discovery}}, and {{metadata}}. Provisioning,
disablement, and revocation apply to the same Agent Principal and local
principal as delegated access ({{status-changes}}).

The profile URIs identify acting relationship and grant protection only.
Further dimensions such as credential class, access-token protection,
or continuation are capabilities and configured minimums; they do not
create additional profile URIs.

# Conformance and Metadata {#conformance-metadata}

## Conformance {#scope}

This profile does not establish trust in previously unknown agent issuers
or automatically create Identity Bindings from presented credentials. A
resource domain creates an Agent Principal Correlation from a validated
grant only where its own policy permits just-in-time correlation
({{jit-correlation}}).

Unless explicitly limited to bound grants or a named profile, the
requirements of this document apply to both governed adoption profiles.
Conformance claims MUST identify the supported profile by its URI
({{metadata}}), the realization, the implemented role, and supported
inputs. An implementation supports delegated access, self-acting
access, or both:

* **Roles:** The IdP, RAS, and client MUST implement their respective
  requirements in {{model}}, {{identity}}, {{authorization}},
  {{metadata}}, {{security}}, and {{mandatory-input-profiles}}; in
  {{delegated-flow}} or {{wag-flow}} for each supported realization; and
  in {{optional-input-profiles}} for each supported optional input. The
  API MUST implement {{api-processing}}, with {{wag-api}} for self-acting
  access.
* **Issuance:** The client and IdP MUST implement dedicated-client
  resolution using RFC 7523 `private_key_jwt` authentication
  ({{client-assertion-input}}), and for delegated access also ID Token
  subjects.
* **Redemption:** The client and RAS MUST implement `private_key_jwt` for
  redemption. DPoP support and use are REQUIRED for bound governed agent
  access; governed agent access follows {{grant-protection}}.
* **Access tokens:** Access tokens are JWTs under {{RFC9068}} or opaque
  tokens whose introspection response carries the same context under
  {{introspection}}.
* **Optional inputs and subjects:** The inputs of
  {{optional-input-profiles}} (SPIFFE JWT-SVIDs, Workload Identity Token
  SVIDs (WIT-SVIDs), X.509-SVIDs, and Client Attestation), existing
  platform JWTs, SAML subjects, and IdP refresh-token subjects are
  OPTIONAL capabilities, with one exception: an IdP that accepts any
  agent-resolution input other than dedicated-client identity MUST also
  support the existing platform JWT input ({{imported-jwt-input}}), and
  a client that relies on a shared client identity MUST be able to
  present it. A deployment selects mutually supported inputs
  through trusted configuration; neither role needs SPIFFE for the
  client-assertion path. The platform JWT input is the common
  shared-client input; other shared-client inputs remain bilateral.
* **Self-acting access:** {{wag-flow}} uses the same adoption profiles
  under its own profile URIs ({{wag-profiles}}). The WAG token type and
  JWT type are provisional values until WAG registers them
  ({{wag-gaps}}).

Each realization has a mandatory interoperability path. For delegated
access: an ID Token subject and dedicated-client resolution at the IdP,
governed ID-JAG redemption using `private_key_jwt` at the RAS, and
actor-aware processing at the API. For self-acting access:
dedicated-client resolution at the IdP, WAG redemption using
`private_key_jwt` at the RAS, and processing of the agent's own
authority at the API. Grant protection follows the applicable governed
profile.

ID-JAG requires support for Identity Assertions ({{Section 4.3 of ID-JAG}}).
This profile specifically requires ID Token support to give independent
implementations a common subject-token format. This is an implementation
baseline, not a requirement to deploy one client per agent: deployments
MAY use mutually supported optional inputs. Support alone establishes
neither trust nor authorization configuration.

Under {{subject-token-validation}}, the ID Token's audience identifies
the dedicated client. A token issued only to a shared `platform-sso`
client cannot accompany
authentication as a separate `analysis-client`. Dedicated deployments
therefore need a user authorization flow for each agent's client
registration, though an existing IdP session may avoid another login
prompt. A platform retaining its shared single sign-on (SSO) client instead
uses an agreed independent workload input: the existing platform JWT
({{imported-jwt-input}}) or an optional input ({{optional-input-profiles}}).

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

The two agent-federation URIs carry the mandatory grant-binding
requirements; the ID-JAG one is the original identifier. Enterprise
access uses the base
`urn:ietf:params:oauth:grant-profile:id-jag` identifier under ID-JAG;
that identifier alone makes no governed-agent conformance claim.

These URIs identify RAS and client processing. IdP issuance and optional
inputs follow {{discovery}}. No URI claims continuation support, a
particular workload-evidence protection, or access-token protection.

### Authorization Server Metadata {#server-metadata}

Servers MUST publish {{RFC8414}} metadata as follows:

* **RAS:** Include each supported governed profile URI, and for
  delegated access the base `urn:ietf:params:oauth:grant-profile:id-jag`,
  in `authorization_grant_profiles_supported`. The self-acting URIs use the
  same parameter; that use is proposed for coordination with ID-JAG and
  WAG ({{wag-gaps}}).
  * Include `urn:ietf:params:oauth:grant-type:jwt-bearer` in
    `grant_types_supported` for this profile.
* **IdP:** Advertise Token Exchange in `grant_types_supported`. For
  delegated access, advertise ID-JAG in
  `identity_chaining_requested_token_types_supported` under
  {{Section 7.1 of ID-JAG}}; for self-acting access, advertise the WAG
  token type in the same parameter, a use proposed for coordination
  with ID-JAG and WAG ({{wag-gaps}}).
  * Include `private_key_jwt` in `token_endpoint_auth_methods_supported`.
  * When SPIFFE authentication is supported, include `spiffe_jwt`,
    `spiffe_wit`, or `spiffe_x509` under {{Section 4 of SPIFFE-OAUTH}}.
    Authentication metadata alone does not advertise agent-resolution
    support; the client and IdP configure the input under
    {{actor-inputs}}.
  * The WAG advertisement states a capability for self-acting issuance
    ({{wag-flow}}); trusted configuration establishes permission to use
    it.
* **Both:** Advertise supported client authentication methods and, when
  DPoP is supported, DPoP algorithms, including {{flow-configuration}}'s
  common capabilities.
  Where supported, publish the existing CIMD and mutual-TLS capability
  metadata defined by {{CIMD}} and {{RFC8705}}.

### Client Metadata {#client-metadata}

A client SHOULD advertise each supported governed profile URI in
`authorization_grant_profiles_supported` in its authoritative client
metadata under {{Section 8 of ID-JAG}}, including when supplied through
CIMD. Its `grant_types` MUST permit:

* `urn:ietf:params:oauth:grant-type:token-exchange` at the IdP.
* `urn:ietf:params:oauth:grant-type:jwt-bearer` at the RAS.

### Discovery and Profile Applicability {#discovery}

RAS support is advertised in metadata. IdP issuance requires bilateral
configuration of trust, Identity Bindings, and Client Associations.
Profile applicability follows these rules:

1. **Establish policy:** Before exchange, trusted configuration MUST
   establish the applicable
   governed profile and minimum requirements for the client, issuer
   trust relationship, and target resource. The client, IdP, and RAS
   MUST use that configuration. Client identity, issuer context, and
   target resource identify the applicable policy; this document defines
   no transaction-level profile negotiation.
2. **Enforce the minimum:** Each server MUST enforce its configured minimum
   regardless of absent
   `actor_token`, `act`, DPoP, or `cnf`. Their presence or absence MUST
   NOT select a different profile. Metadata advertises capabilities;
   it MUST NOT authorize a lower profile or override resource policy.
3. **Prevent fallback:** Implementations MUST NOT retry a failed governed
   request as ordinary
   EMA or drop proof to retry as governed agent access. A lower profile
   requires a separately authorized configuration, not an error-driven
   fallback.
4. **Enforce resource policy:** The RAS and API MUST agree on the minimum
   profile for their resource.
   The API relies on the RAS to enforce grant protection; an access
   token's `cnf` describes its own protection and does not establish
   which grant profile was used. Where multiple paths share a resource,
   applicability follows {{api-processing}}.

An implementation MAY serve existing EMA and either governed profile
concurrently under these rules. Supporting the bound profile does not
require accepting grants without sender constraint or advertising the
intermediate profile.

Migration changes the configured profile after
the participating roles implement its requirements; it does not relabel
previously issued grants or refresh tokens.

Before using either path:

* **Issuance support:** The client and IdP MUST agree through trusted
  configuration on issuance support and any options; generic JWT or
  authentication-method support is insufficient.
* **RAS capabilities:** The client MUST verify the RAS's profile
  advertisement, JWT bearer grant support, and compatible access-token
  protection. If no supported profile satisfies the configured minimum,
  the client MUST NOT initiate that path.
* **Metadata consistency:** For delegated access, if the
  `actor_profile_token_exchange` parameter of
  {{Section 16.2 of ACTOR-PROFILE}} is published, it MUST
  describe only the paths actually supported and agree with the
  ID-JAG advertisement.

# Security Considerations {#security}

The security requirements of the selected credential and grant
specifications, {{RFC9700}}, and {{RFC8725}} apply.

## Adoption Tradeoffs {#baseline-costs}

The profile's security controls carry these deployment costs:

| Requirement | Benefit | Cost |
|---|---|---|
| Dedicated-client resolution as the common mode | Reuses deployed client authentication and registered keys | Each client identity resolves to one Agent Principal; proves registered-client identity, not independent runtime or workload provenance |
| Optional native JWT-SVID input | Reuses SPIFFE issuance, client authentication, and trust-domain validation | JWT-SVID is bearer evidence; deployments requiring issuer-bound presenter proof need another supported input |
| Bound profile: DPoP at both token endpoints; grant bound to the grant proof key | A stolen ID-JAG cannot be redeemed without the key | Every client holds and proves a key. Grant binding does not make bearer evidence proof of an issuer-authorized presenter ({{credential-requirements}}) |
| Bound grants: same key for issuance and redemption | No key-transition protocol to secure | A broker that obtains bound grants also redeems them ({{distributed-key-use}}) |
| Access-token context as JWT claims or introspection | The API reads `act`, `scope`, and `cnf` from the token or from an authenticated introspection response ({{introspection}}) | Opaque-token deployments add an introspection round trip and a freshness policy |
| Actor-aware API processing | The actor gate is enforced where access happens | APIs parse `act` and consult the gate on delegated paths |
| Sender-constrained access tokens by default | Token theft is contained | Resources without DPoP or mutual TLS need explicit configuration for bearer use |
{: title="Adoption tradeoffs"}

Governed agent access without grant binding adds agent authorization
to existing enterprise access but leaves stolen grants redeemable by
an attacker able to authenticate as their designated client. This is
particularly relevant to shared clients. Binding only the resulting
access token does not prevent that redemption.

Explicit acceptance
policy, short grant lifetimes, credential confidentiality, and the
no-fallback rules in {{discovery}} limit this exposure; they do not
provide proof of possession of an issuer-authorized grant key.

## Credential and Token Confusion

Credential classification and mutually exclusive validation follow
{{actor-inputs}} and {{Section 3.12 of RFC8725}}. Signature validity alone
establishes neither a credential's intended use nor permission to
resolve or exercise an agent.

## Time, Replay, and Key Changes {#time-validation}

Validators MUST enforce:

* **Time claims:** Apply the selected credential's expiration and other
  time rules; reject `iat` later than the current time plus permitted
  clock skew. Under {{RFC7519}}, `iat` has no not-before semantics.
* **Clock skew:** Use a configured tolerance that MUST NOT extend a
  configured maximum age or lifetime. It SHOULD remain within the few
  minutes contemplated by {{RFC7519}}.
* **Replay protection:** Apply each credential, proof, and grant
  mechanism independently. Replay detection MUST remain in effect for
  as long as the credential, proof, or grant would otherwise be
  accepted, including the maximum allowed skew.

A fresh proof does not renew an expired credential; an unchanged
identifier does not authorize a new proof key.

## Dedicated-Client Key Compromise

In dedicated-client resolution, compromise of the client's authentication
key permits an attacker to authenticate as the resolution source for its
bound Agent Principal. No independent workload credential is required.
A normalized Agent Principal identity does not imply uniform runtime
assurance; assurance depends on the resolution input, verified claims,
and the credential authority's issuance policy.

For delegated access, the attacker still needs an acceptable user
subject credential and has to satisfy Client Association and delegation
authorization. For self-acting access, the key alone suffices wherever
a Client Association and Agent Authorization already permit the client.
Existing permissions may already authorize the compromised client.

Grant binding does not prevent this impersonation at issuance. Unless
policy independently constrains the grant proof key, the attacker can
obtain a grant bound to an attacker-controlled DPoP key. The proof
protects that grant against theft; it does not establish legitimate
runtime provenance.

Deployments requiring runtime or workload provenance need an
agent-resolution input whose verified claims and trusted issuance policy
establish the required properties; dedicated-client resolution alone
does not establish them. Authentication-key revocation and binding
disablement affect subsequent issuance under {{status-changes}}.

## Credential Authority and Key Isolation

A compromised credential authority can assert identities within its
trusted scope. Exact bindings, tenant boundaries, and issuer-scoped
key lookup limit that scope. Key lookup MUST retain the issuer or
trust-domain association ({{Section 3.8 of RFC8725}}); `kid` alone or a
union of unrelated issuers' keys does not establish the assertion's source.

A holder of a shared private key can present any credential issued for
that key. Agent isolation therefore depends on issuance controls and
key custody as well as identity mapping. Sharing the grant proof key
across components widens its exposure ({{distributed-key-use}}).

## Authorization Changes and Revocation {#status-changes}

Before issuance, the IdP MUST apply current binding and authorization
policy and reject an inactive agent or withdrawn binding once the change
has been applied. The IdP MUST apply such a change within a configured
freshness limit on cached policy data.

Cross-system disablement needs a provisioning and signaling contract
({{lifecycle-gap}}); without a signal or online check, issued tokens
remain usable until expiration. {{AGENT-LIFECYCLE}} profiles SCIM
administrative state, optional change notices, and session revocation
for that purpose: applied disablement stops RAS issuance and refresh
and revokes associated sessions, cached introspection results or
offline JWTs can remain usable until their acceptance limits, and
current active state alone cannot recover a missed
disable-and-reenable transition or invalidate every old grant.

Execution termination, Identity Binding disablement, Client Association
removal, delegation revocation, and Agent Principal disablement have
different effects, and none of them is evidence that the others have
occurred. In particular, stopping an execution does not revoke
credentials or authority held elsewhere.

The following table summarizes the effect after a change is applied at
the enforcing server; it defines no new propagation mechanism:

| Administrative action | Effect on new authorization | Previously issued authority |
|---|---|---|
| Terminate an execution | Stops that execution; does not disable the agent or its approved relationships | Credentials and tokens remain subject to their validation and revocation rules |
| Disable one Identity Binding at the IdP | No new grant through that binding; other enabled bindings remain usable with their own Client Associations | Existing grants and RAS tokens need separate revocation or expiry |
| Remove a Client Association at the IdP | No new grant through that permission; the Identity Binding can remain valid | Existing grants and RAS tokens need separate revocation or expiry |
| Disable the Agent Principal at the IdP | No new grant for that agent, regardless of binding or client | RAS issuance and refresh stop when the change reaches and is applied by the RAS |
| Withdraw the user's delegation at the IdP | No new delegated grant for that delegation | Existing RAS authorization can continue until revocation is applied or its absolute expiration |
| Disable the local agent or user at the RAS | No new access tokens or refresh for that principal | API access stops when its actor/user policy observes the change, introspection reports inactivity, or the token expires |
{: title="Effects of administrative changes"}

The RAS requirements for applied disablement and revocation are in
{{applied-changes}}; the provisioning that feeds them is a deployment
choice. Withdrawing a delegation, Identity Binding, or Client
Association can be propagated to derived authorization, through
grant-derived revocation in that companion or an equivalent signal,
only when the IdP has retained the identifiers of the ID-JAGs it issued
under that relationship. The agent identity alone cannot identify that
set.

Deployments benefit from documenting their maximum disablement delay,
including propagation and cache freshness. Without a bound on
propagation, the remaining lifetime of existing grants, refresh
authorizations, and access tokens determines the possible continuation
window; the five-minute ID-JAG recommendation is not a global stopping
guarantee.

Account-linking errors can grant access to another user's account.
{{subject-resolution}} requires issuer, namespace, tenant, and
link-change checks before authorization; proof of key possession does
not establish account ownership, and link removal does not revoke
outstanding tokens.

## External Approval {#external-approval}

External approval MUST NOT replace credential validation, identity
resolution, Client Association, or delegation authorization. A
resource-local approval can satisfy an additional policy condition
within the presented token's authority; it MUST NOT expand that
authority or override token validity or tenant restrictions. Access
beyond that authority requires new authorization through an applicable
protocol. Asynchronous approval composition is deferred under
{{excluded-compositions}}.

# Privacy Considerations {#privacy}

A stable agent identifier can correlate activity across resources,
users, and instances. Preserving the same issuer-qualified actor across
delegated users enables a resource domain to correlate activity performed
by the same Agent Principal for different users, supporting audit while
linking those activities.

Issuers SHOULD disclose only the agent attributes needed for the
authorized purpose. User and agent context remain separate when the
agent acts for a user. The mapping in {{actor-construction}} keeps
external workload identifiers out of the ID-JAG; this profile does not
define pairwise actor translation.

Any future instance context needs purpose limits, retention guidance,
and clear rules about whose activity it describes.

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

The URIs are used with ID-JAG's existing authorization server and client
metadata parameters.

## WAG Grant Profile URIs

This document also requests:

* URN: `urn:ietf:params:oauth:grant-profile:wag-agent-federation`
* Common Name: WAG Bound Governed Agent Access grant profile
* Change Controller: IETF
* Specification Document: {{wag-profiles}} of this document.

* URN: `urn:ietf:params:oauth:grant-profile:wag-governed-agent`
* Common Name: WAG Governed Agent Access grant profile
* Change Controller: IETF
* Specification Document: {{wag-profiles}} of this document.

The WAG token type `urn:ietf:params:oauth:token-type:wag` and JWT type
`wag+jwt` are not requested here; they are proposed for registration by
WAG.

--- back

# Mandatory Agent Resolution Inputs {#mandatory-input-profiles}

This appendix is normative. It defines the two inputs that
{{scope}} requires: dedicated-client identity, which is mandatory to
implement, and the existing platform JWT, which shared-client support
requires. Each satisfies the interface contract of {{evidence}}.

## Dedicated Client Identity {#client-assertion-input}

This mode resolves an authenticated OAuth client identity to its
explicitly bound Agent Principal. Client authentication uses an
asymmetrically signed assertion under {{RFC7523}}; no separate
platform-issued credential is required. The common method is
`private_key_jwt`; other configured asymmetric RFC 7523 methods MAY
be supported.

### Presentation and Resolution

The client presents its assertion as `client_assertion` under
{{RFC7523}}. The assertion authenticates the client and is not
independent workload evidence; in this explicitly configured mode, the
validated client-authentication context is the resolution source. This
composition differs from the dual-presentation input of
{{ACTOR-PROFILE}} ({{dedicated-client-coordination}}).

The IdP authenticates the client under {{Section 3 of RFC7523}} and its
configured authentication method. The IdP MUST also:

* **Key trust:** Use verification keys authorized for that client and
  assertion issuer. Assertion-supplied keys or issuer claims MUST NOT
  establish trust.
* **Resolution:** Resolve the exact validated (`iss`, `sub`) in the
  IdP's client-registration context under {{identity-binding}}.

For `private_key_jwt`, the assertion issuer and subject are the client's
registered identifier (Section 9 of {{OPENID}}).

### Assertion Audience

RFC 7523 client authentication at the IdP and the RAS MUST follow the
audience requirements of {{Section 4 of RFC7523bis}}: the assertion's
`aud` contains the authorization server's issuer identifier as its sole
value, never its token endpoint URL, and the server rejects any other
audience. This profile adds no alternative audience configuration and
does not change other credential classes' audience rules.

### Replay and Retries

For dedicated-client resolution, these requirements narrow the base
specifications and prohibit negotiated assertion reuse:

* The assertion MUST contain a `jti`.
* The IdP MUST reject reuse in another request while the assertion
  remains acceptable.
* Replay identifiers MUST be qualified by the validated issuer and
  client.

For a retry of a dedicated-client exchange, including after a
`use_dpop_nonce` challenge under {{Section 8 of RFC9449}}:

* The client MUST generate a new `client_assertion` with a fresh `jti`.
* For a nonce retry, the client MUST also generate a fresh DPoP proof
  containing the supplied nonce while retaining the grant proof key.

Changing only the DPoP proof does not satisfy the assertion replay rule,
because the IdP may already have consumed the previous assertion during
authentication.

### Identity and Proof Boundaries

This mode does not distinguish agents behind one shared client identity;
such a client MUST use a supported workload-identity input that
distinguishes its agents ({{imported-jwt-input}}). An additional agent claim
in a self-signed client assertion MUST NOT select another Agent
Principal under this input.

Assertion signing authenticates the client; it does not bind the grant
to that signing key or establish an attested runtime identity. Grant
proof processing follows {{grant-protection}} independently, and the
DPoP key MAY differ from the client-authentication key. An assertion
carrying `cnf` MUST NOT be accepted unless its configured authentication
method defines and validates the corresponding proof.

{{client-assertion-example}} illustrates this input.

## Existing Platform JWT {#imported-jwt-input}

This input accepts existing signed platform JWTs without a new media
type or reissuance in a federation-specific format. It is the common
shared-client input; {{scope}} states when it is required. The client
presents the JWT as `actor_token` in delegated issuance and as
`subject_token` in self-acting issuance ({{wag-request}}), and
authenticates separately with a configured method. The IdP MUST accept
a platform JWT only from an explicitly configured issuer, for a
configured credential class and authenticated client. Credential
classification and rejection follow
{{actor-inputs}}.

The Identity Binding MUST specify an exact issuer and `sub` and MAY
require additional string values from the JWT Claims Set, including
nested claims. Additional selectors MUST use the JSON Pointer string
representation in {{Section 5 of RFC6901}}, evaluated from the Claims
Set root under {{Section 4 of RFC6901}}:

* **Exact value:** Every selector MUST resolve unambiguously to a string
  equal to its configured value, without type conversion, case folding,
  or Unicode normalization. Missing paths, evaluation errors, non-string
  values, or unequal values MUST prevent that binding from matching.
* **No patterns:** Selectors MUST NOT use wildcard, prefix, or pattern
  matching, and MUST NOT replace the exact issuer and `sub` checks.
* **Claim authority:** A caller-controlled claim MUST NOT distinguish
  agents unless trusted issuance policy constrains its values to
  identities the caller is authorized to assert. A signature alone does
  not establish that authority for request tags or other caller-supplied
  attributes.

Selectors constrain identity resolution, not the administrative
configuration format. Configuration MUST also specify:

| Item | Requirement |
|---|---|
| Key source and algorithms | Approved keys or an approved HTTPS JWK Set URI under {{RFC7517}}, retrieved with server authentication, and permitted asymmetric algorithms for the issuer |
| Audiences | Values that authorize presentation to this IdP as workload evidence |
| Time limits | Effective evidence deadline as defined below, permitted clock skew for a future issuance time, and any maximum age |
| Credential class | The rule distinguishing workload credentials from user, management-API, or other tokens of the same issuer: an explicit `typ`, a dedicated issuer, or an accepted audience combined with exact selectors |
{: title="Platform JWT configuration"}

The IdP MUST determine an effective evidence deadline from `exp`, a
configured maximum age measured from an authenticated issuance time
(such as `iat`),
or both. When both apply, the earlier deadline governs. The IdP MUST
reject evidence with `invalid_grant` if a required time limit cannot be
evaluated or no deadline can be determined. Receipt time MUST NOT
substitute for issuance time. This deadline bounds grant expiration
under {{grant-issuance}}; it does not require a new claim in existing
credentials.

The IdP MUST validate the JWT under {{RFC7519}} and {{RFC8725}} and the
configured credential profile. Keys or URLs in the JWT MUST NOT
override the approved key source. An accepted JWT MUST NOT be treated
as OAuth client authentication unless it independently satisfies a
configured client authentication method.

This profile defines no new proof mechanism for platform JWTs. If `cnf`
is present, the IdP MUST enforce its proof mechanism and MUST NOT give
the credential bearer treatment when the binding is unsupported. A
deployment accepting key-bound JWTs MUST configure their proof
validation and any required relationship to the grant proof key. If the
JWT is bearer evidence, {{credential-requirements}} applies.

An AWS STS example appears in {{aws-example}}.

# Optional Agent Resolution Inputs {#optional-input-profiles}

This appendix is normative. It defines the optional agent-resolution
inputs listed in {{optional-inputs}}. Each satisfies the interface
contract of {{evidence}}.

## SPIFFE JWT-SVID {#jwt-svid-input}

This OPTIONAL input supports workload identity independently of the
OAuth client identifier, including multiple agents behind a shared
client. It resolves from authentication context, with actor-token
parameters omitted ({{actor-inputs}}), and requires trusted
configuration under {{configuration}}.

The client presents the JWT-SVID in `client_assertion` with
`client_assertion_type`
`urn:ietf:params:oauth:client-assertion-type:jwt-spiffe` and
authenticates under {{Section 3.1 of SPIFFE-OAUTH}}; trust establishment
and key distribution follow {{Section 5 of SPIFFE-OAUTH}} and
{{Section 6 of SPIFFE-OAUTH}}. The IdP MUST apply those validation
rules, including that assertion type, before resolving the agent, and
verify the signature with keys authorized for the trust domain in the
SPIFFE ID. An optional `iss` MUST NOT select another trust domain or key
authority. The SPIFFE ID's association with the authenticated client is
an authentication check; it does not establish an Identity Binding or
Client Association.

The IdP MUST resolve the exact SPIFFE ID in the validated `sub` under
{{identity-binding}}.

A JWT-SVID is bearer evidence. When used, DPoP binds the issued grant to
the grant proof key, not the JWT-SVID to its presenter. A policy
requiring issuer-bound presenter proof MUST reject this bearer input
rather than treat DPoP as that proof ({{credential-requirements}}).

## Client Attestation {#agent-evidence}

Client Attestation is an OPTIONAL agent-resolution input where the
attested OAuth client identity maps explicitly to one Agent Principal.
It resolves from authentication context, with actor-token parameters
omitted ({{actor-inputs}}), and requires trusted configuration under
{{configuration}}. The client authenticates with the configured
{{ATTEST}} method.

The IdP MUST validate the attestation and proof under {{ATTEST}} before
resolving the agent. The IdP MUST identify the attester unambiguously
from the trusted verification key and configured attester-to-client
associations, and resolve the trusted attester and validated Client
Attestation `sub` through an approved Identity Binding
({{identity-binding}}). An `iss`, when present, MUST match that
authority.

With `attest_jwt_client_auth`, any grant proof key MUST match the
attestation's confirmation key, narrowing the allowance in
{{Section 5.2 of ATTEST}} for a separate DPoP key. With
`attest_jwt_client_auth_dpop`, one DPoP proof serves both roles. Key
retention follows {{resolution-key-lifecycle}}.

This input relies on a trusted attester's endorsement of client identity
and its confirmation key, not on a registered client key. It establishes
runtime or workload provenance only to the extent supported by verified
attestation claims and the attester's trusted issuance policy. It does
not distinguish agents behind a shared client; those agents need
distinct workload evidence, such as a JWT-SVID or an accepted platform
JWT. Instance-based resolution and attester endorsement are deferred
({{excluded-compositions}}).

## SPIFFE WIT-SVID and X.509-SVID Resolution {#spiffe-input}

These OPTIONAL inputs resolve the workload identity validated during
OAuth client authentication for this token request. They resolve from
authentication context, with actor-token parameters omitted, and the
client and IdP configure the accepted SVID class under {{actor-inputs}}
and {{configuration}}. WIT-SVID is the SPIFFE form of a Workload
Identity Token (WIT), and X.509-SVID is a certificate input within the
Workload Identity Certificate (WIC) model in {{WIT}}; general non-SPIFFE
WIT and WIC inputs are excluded ({{excluded-compositions}}).
{{svid-context-example}} illustrates both inputs.

### Presentation and Validation

| Input | Presentation | Validation and resolution source |
|---|---|---|
| WIT-SVID | `OAuth-Client-Attestation` carries the WIT-SVID; `OAuth-Client-Attestation-PoP` carries its proof | {{Section 3.3 of SPIFFE-OAUTH}} and {{WIT}}; exact SPIFFE ID in validated `sub` |
| X.509-SVID | Client certificate on the mutual-TLS connection carrying the token request | {{Section 3.2 of SPIFFE-OAUTH}} and {{RFC8705}}; exact SPIFFE ID in the certificate's URI Subject Alternative Name |
{: title="Native WIT-SVID and X.509-SVID inputs"}

The IdP MUST apply the selected authentication profile, including its
client-identifier association, trust, validity, and proof requirements.
In addition:

* **WIT-SVID:** Require `typ=wit+jwt` and validate possession of the key
  in `cnf.jwk` through the Client Attestation PoP JWT. A WIT-SVID MUST
  NOT be accepted as bearer evidence. Its optional `iss` MUST NOT select
  a different trust domain or key authority.
* **X.509-SVID:** Use the certificate and proof established by mutual
  TLS for this request. A certificate supplied only in a request
  parameter or an untrusted forwarding header MUST NOT establish the
  workload identity. TLS termination arrangements follow
  {{Section 6.5 of RFC8705}}.
* **Resolution:** Resolve the approved trust domain and exact SPIFFE ID
  through {{identity-binding}}.

One shared SPIFFE ID cannot distinguish independently governed agents.

### Proof Boundaries

Workload authentication and grant protection remain separate:

* **WIT-SVID:** When DPoP is used at issuance, its key MUST match the
  WIT-SVID's `cnf.jwk`. The IdP MUST compare their JWK thumbprints as
  used in {{RFC9449}} and reject a mismatch with `invalid_grant`. This
  carries the WIT-endorsed key into the grant binding; the Client
  Attestation PoP JWT remains required.
* **X.509-SVID:** The client proves the certificate key on the
  mutual-TLS connection and, when required, a grant proof key in DPoP on
  the same token request. The keys MAY differ, because mutual TLS can
  terminate separately from the component generating DPoP proofs. The
  certificate does not endorse the DPoP key; the authenticated request
  associates it with this issuance. The grant uses `cnf.jkt`, not
  certificate confirmation.

Either input proves control of a credential-bound key. Assurance about a
particular runtime or execution depends on the credential authority's
issuance rules and identity granularity.

## Resolution-Key Lifecycle {#resolution-key-lifecycle}

When the resolution key is also the grant proof key, as for WIT-SVID and
Client Attestation when DPoP is used, replacing it does not change the
binding of an outstanding grant, access token, or refresh token.
Continued use of those requires retaining the corresponding proof key;
otherwise, the client obtains a new grant using the replacement key
and establishes new RAS authorization. Any subject-credential binding
still applies and may require a new subject credential. Key migration
is not defined here ({{key-transition-gap}}).

# Dependencies and Deferred Work {#upstream-gaps}

This informative appendix records dependencies and deferred work.
Assessed revisions: WAG-00, ID-JAG-04, ICA-02, Actor
Profile-00, SPIFFE OAuth-02, ATTEST-11, WIT-02, CIMD-02, and the
current drafts of Client Instance Identification and Client Attester
Endorsement.

## Upstream Dependencies

| Specification | What this profile needs | Consequence until resolved |
|---|---|---|
| WAG | Registration of the WAG token type and JWT type, and alignment on protection, linking, and subject presentation ({{wag-gaps}}) | The WAG token type and JWT type remain provisional values |
| ID-JAG | Bound-grant example aligned with the normative `jwt-bearer` grant type, and grant-confirmation errors separated from RFC 9449 proof errors ({{bound-grant-coordination}}) | Confirmation checks are applied to `jwt-bearer` here |
| Actor Profile | A reusable principal-resolution extension point separating credential validation, identity mapping, and actor construction | The mapping is defined locally in {{actor-construction}} |
{: title="Upstream dependencies"}

### WAG {#wag-gaps}

{{wag-flow}} defines the IdP issuance that {{Section 5 of WAG}}
anticipates without specifying. Coordination is needed on:

* **Identifiers:** registration of `urn:ietf:params:oauth:token-type:wag`
  and `wag+jwt`, and their advertisement with the self-acting profile
  URIs in ID-JAG's metadata parameters ({{server-metadata}}).
* **Protection:** DPoP binding at issuance and redemption
  ({{grant-protection}}); WAG-00 leaves proof of possession open.
* **Linking:** an authorized local correlation, established in advance
  or, where resource policy permits, just in time ({{wag-redemption}}),
  in place of the required acceptance of unseen identifiers in
  {{Section 7 of WAG}}.
* **Renewal:** this document adopts WAG's prohibition on refresh tokens.
* **Subject presentation:** a token exchange whose authenticated client
  is the subject without a subject token, which would replace repeating
  the authentication JWT ({{wag-request}}) and give X.509-SVID
  authentication a self-acting path.
* **Management:** a self-acting dimension for Client Associations in
  {{AGENT-MANAGEMENT}}, which covers delegated issuance only.

### ID-JAG Bound Grants {#bound-grant-coordination}

{{Section 4.4 of ID-JAG}} requires `jwt-bearer` while its bound-grant example
uses `jwt-dpop`. This profile follows the normative grant type with
explicit confirmation processing ({{redemption}}) and takes no
dependency on JWT DPoP Grant.

### Resolution from Authentication Context {#dedicated-client-coordination}

This document defines delegated issuance from validated authentication
context and an approved Identity Binding, without `actor_token`
({{actor-inputs}}). ID-JAG leaves actor processing to extensions
({{Section 9.7 of ID-JAG}}); Appendix A.1 of {{RFC8693}} reads a
subject-only request as impersonation; and
{{Section 6.3.1 of ACTOR-PROFILE}} permits authentication-context reuse
only with the same assertion as `actor_token`. None defines these mapped
inputs, so generic Token Exchange or Actor Profile support does not
advertise this composition, and coordination with both is needed.

## Deferred Compositions

### Grant Key Transition {#key-transition-gap}

A control plane obtaining a bound grant for redemption by a different
worker needs an authorized proof-key transition. This document defines
no such transition: the holder of the issuance key also redeems the
grant ({{distributed-key-use}}). A future composition would need to bind
the new key without weakening the applicable grant protection.

### Portable Authorization Deadlines {#deadline-gap}

A portable IdP-imposed deadline on downstream access would need an
authenticated claim, its association with the delegation, and
enforcement rules for access tokens and refresh. ID-JAG `exp` limits
only redemption ({{authorization-lifetime}}).

### User Access Tokens as Subjects {#access-token-subject-gap}

Deployed on-behalf-of (OBO) flows, including {{AWS-AGENTCORE-OBO}}, use
a user access token as the subject. This document accepts only ID-JAG's
ID Token, SAML, and refresh-token subjects. An access-token subject
composition needs eligibility, audience, resolution, sender-constraint,
and authority rules coordinated with ID-JAG; changing only
`subject_token_type` does not establish them.

### Excluded Compositions {#excluded-compositions}

The following compositions are not defined in this document. Their
exclusion does not prevent the independently supported uses listed here.

| Composition | Boundary in this document |
|---|---|
| Asynchronous approval with {{AROP}} | No approval transport or completion flow; external approval remains subject to {{external-approval}} and the lifetime limits in {{authorization-lifetime}} |
| Continuation with {{ICA}} | No ICA issuance or continuation chain; supported renewal follows {{continuing-access}} |
| General WIMSE WIT/WIC inputs | WIT-SVID and X.509-SVID resolution is defined in {{spiffe-input}}; non-SPIFFE credentials need an explicit OAuth presentation and proof composition |
| Instance-based resolution or propagated instance context under {{INSTANCE}} | Workload evidence resolves the agent; no per-instance enrollment or continuity protocol is required. Shared workload identity does not distinguish replicas {{SPIFFE-CONCEPTS}} |
| Client attester endorsement under {{ATTESTER-ENDORSEMENT}} | Attester trust is configured under {{agent-evidence}} |
| Mutual-TLS-bound ID-JAG | Bound grants use DPoP. Mutual TLS remains available for access-token protection under {{access-token-protection}} |
| Rich Authorization Requests without scope | This profile requires meaningful scope alongside any authorization details; it does not define the scope-free mode permitted by {{RFC9396}} |
{: title="Excluded compositions"}

## Operational Dependencies {#operational-guidance}

Provisioning, account linking, and lifecycle propagation are deployment
choices. Useful controls include:

* Authenticate the authority creating or changing a link, or verify
  control of both accounts in a user-linking flow.
* Authorize just-in-time creation of user accounts and agent
  correlations by issuer and tenant, the latter under
  {{jit-correlation}}; avoid silent merges and reactivation of disabled
  accounts.
* Retain ownership, groups, and entitlements with their principal;
  audit link and binding changes.
* Preserve issuer and tenant context when using the System for
  Cross-domain Identity Management (SCIM) `externalId` attribute
  {{RFC7643}}.

SCIM {{RFC7644}} and Agent resources {{SCIM-AGENT}} provide building
blocks, not a lifecycle propagation contract.

### Provisioning and Disablement {#lifecycle-gap}

{{AGENT-LIFECYCLE}} profiles SCIM, optional Shared Signals, and the
effect of applied changes on authorization, including the limits of
missed-event recovery. It is not required for conformance to this
document; {{agent-correlation}} and {{status-changes}} state this
document's guarantees.

# Walkthrough: Dedicated Client {#walkthrough}

This non-normative walkthrough exercises the common dedicated-client
input, bound governed agent access, and DPoP-protected API access.
Key coordinates, thumbprints, token hashes, and compact JWTs are labeled
placeholders, not cryptographic test vectors. The optional shared-client
SPIFFE variant follows in {{shared-client-example}}.

The dedicated client is `analysis-client` at the IdP and `analysis-api`
at the RAS. In the IdP's client-registration context, an Identity
Binding maps (`analysis-client`, `analysis-client`) to `agent-42`.
A separate Client Association permits use of that binding, and
delegation authorization permits the agent to act for Alice.
Alice's ID Token has audience `analysis-client`; subject resolution
produces `alice-ras` for the RAS and `user-108` at the resource.

The exchange starts at 12:01:03 UTC on September 17, 2026. The lifecycle
companion's shared walkthrough {{AGENT-LIFECYCLE}} uses the same identities,
Target Tenant `acme-data` and grant issuance time. It adds SCIM provisioning,
introspection, disablement, and reactivation, including the limit when an
entire transition is missed. Those checks are not implied by Federation alone.

## Dedicated Client Authentication {#client-assertion-example}

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

`CLIENT_ASSERTION` denotes the signed compact JWT presented only in
`client_assertion` under {{client-assertion-input}}. The configured
Identity Binding resolves the authenticated client to `agent-42`;
no actor-token parameters are sent. The assertion supplies no independent
workload identity. The client assertion expires after 60 seconds;
the resulting grant can remain valid for 300 seconds.

## Exchange Request and Response

The HTTP examples show application parameters and relevant headers;
framing headers are omitted. Bodies are line-wrapped for display;
concatenate their lines before sending.

`IDP_DPOP_PROOF` proves a separate grant key K, with `htm=POST`,
`htu=https://idp.example/token`, a current `iat`, and a unique `jti`.
A server nonce is included if challenged. The same key is proven at
redemption; `JKT_K` denotes its public key thumbprint.

After `use_dpop_nonce`, retry with a new `client_assertion` and a fresh
DPoP proof containing the nonce, still signed by K
({{client-assertion-input}}). For example, replace
assertion `jti=analysis-auth-1` with `analysis-auth-2`; resending
`analysis-auth-1` with only a new proof is a replay.

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

`JKT_K` denotes K's JWK thumbprint. This example uses Actor Profile's
unclassified-actor processing; it omits the recommended `sub_profile`.
The configured issuer and client relationships resolve the Governance
Tenant; the tenant-specific resource identifies Target Tenant
`acme-data`.

The 60-second client assertion authenticates issuance and does not cap
this grant's 300-second lifetime. Alice's ID Token remains valid for
at least that period. Adding another agent's identifier to the client
assertion cannot select that agent.

## Redemption Request and Response {#redemption-example}

`RAS_CLIENT_ASSERTION` authenticates the corresponding RAS client with
`iss=sub=analysis-api`, `aud=https://ras.example/`, a short
expiration, and its own `jti`. It uses that registration's signing key.
`RAS_DPOP_PROOF` is a fresh proof using K, `htm=POST`, and
`htu=https://ras.example/token`.
The RAS validates the grant binding regardless of the API's token mode.
It also accepts `resource` encoded as the single-element array
`["https://api.example/tenants/acme-data/"]`, with the same authorization
result as the string shown above.

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

The RAS translates Alice's subject while preserving the Agent Principal
actor. The dedicated OAuth client identifier does not replace that
actor, and the access token is bound to the same key K used at both
token endpoints.

## Protected Resource Request

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

`K_X` and `K_Y` represent K's base64url-encoded public coordinates.
The public JWK's thumbprint is `JKT_K`. `ATH_ACCESS_TOKEN` represents
the base64url-encoded SHA-256 hash of the ASCII access-token value,
computed without padding under {{Section 4.2 of RFC9449}}. The proof has
a new `jti` and current `iat`; if the API requires a nonce, the client
also includes the API-provided `nonce`.

The API validates the token and proof, including `htm`, `htu`, `ath`,
and the match between the proof key and `cnf.jkt`. It then enforces
the user permissions, actor gate, and tenant constraints.

The API verifies the tenant-specific audience for `acme-data`; a call
for another tenant is rejected even if Alice and the agent also have
permissions there. The client caches this token for Alice and
`agent-42` in `acme-data`; matching client identity or scope alone does
not permit other uses.

For explicitly configured bearer access, the response instead uses
`token_type=Bearer`, the access token has no `cnf`, and the API request
uses `Authorization: Bearer API_ACCESS_TOKEN` without a DPoP proof.
DPoP at grant issuance and redemption remains required in this bound
profile, including when the API accepts bearer tokens.

## Intermediate Adoption Variant

To adopt governed agent access, the parties instead configure
`urn:ietf:params:oauth:grant-profile:id-jag-governed-agent` and explicitly
permit grants without sender constraint. With bearer access also
permitted for this resource, the preceding messages change only as follows:

| Message | Change |
|---|---|
| Exchange request and ID-JAG | Omit the DPoP header; the issued grant has no `cnf` |
| Redemption request | Omit the DPoP header; retain client authentication and all request parameters |
| Access-token response and API request | Use the bearer variant above |
{: title="Message changes for governed agent access"}

The client assertion, Identity Binding, Client Association, user and actor
identities, scope, tenant checks, and actor gate are unchanged. An
unbound grant may instead obtain a DPoP-bound access token by presenting
a valid proof at redemption; this does not establish bound governed
agent access.
Refresh, if enabled, follows the applicable binding rules in {{ras-refresh}}.

## Renewal and Rejection Examples

The response contains no refresh token. After access-token expiration,
the client obtains a new ID-JAG using valid subject and agent-resolution
inputs.

If policy instead permits RAS refresh, the RAS sets an absolute refresh
authorization expiration at initial issuance. For example, with a
four-hour authorization and a thirty-minute inactivity limit:

* Renewal is permitted only while both limits hold.
* Rotation and refresh do not restart the four-hour period.
* Each access token expires no later than that period's end.
* Access beyond the period requires a new ID-JAG and new IdP and RAS
  authorization decisions. These establish a new period under
  {{ras-refresh}}; the previous expiration remains unchanged.

Each rejection below changes one condition in the walkthrough; all
other credentials, proofs, and policy checks succeed. Token endpoint
errors follow {{errors}}; API errors follow {{resource-errors}}.

| Changed condition | Rejecting party | Result |
|---|---|---|
| Dedicated-client exchange includes `actor_token` or `actor_token_type`, even a duplicate client assertion | IdP | HTTP 400, `invalid_request`; no switch to presented-evidence mode |
| Configured presented-evidence exchange omits `actor_token` or its type | IdP | HTTP 400, `invalid_request`; no fallback to authentication-context resolution |
| Configured presented-evidence exchange uses an unsupported `actor_token_type` | IdP | HTTP 400, `invalid_request` |
| JWT-SVID, WIT-SVID, X.509-SVID, or Client Attestation resolution includes either actor-token parameter | IdP | HTTP 400, `invalid_request`; no resolution-mode switch |
| A native credential authenticates successfully but has no enabled exact Identity Binding | IdP | HTTP 400, `invalid_grant`; authentication alone does not resolve the agent |
| Valid WIT-SVID proof accompanies an issuance DPoP proof using a different key | IdP | HTTP 400, `invalid_grant`; no grant issued |
| X.509-SVID is supplied only as request data without the required mutual-TLS client authentication | IdP | Authentication failure under the configured method; no agent resolution |
| Platform JWT has neither `exp` nor an authenticated issuance time with a configured maximum age | IdP | HTTP 400, `invalid_grant`; no effective evidence deadline |
| RAS refresh uses a replacement Client Attestation key without an applicable key-transition profile | RAS | Reject under ATTEST's binding requirements, even if the grant was unbound and the access token was bearer |
| A renewed WIT uses a new key to redeem an outstanding ID-JAG bound to the old key | RAS | HTTP 400, `invalid_grant`; renewal does not transfer the grant binding |
| Bound-profile exchange omits its DPoP proof | IdP | HTTP 400, `invalid_request` |
| Exchange repeats `analysis-auth-1` | IdP | HTTP 400, `invalid_client`; the authentication assertion was already consumed |
| After a nonce challenge, retry uses a fresh proof but reuses the consumed `analysis-auth-1` assertion | IdP | HTTP 400, `invalid_client`; regenerate `client_assertion` |
| Exchange contains a second `resource` parameter | IdP | HTTP 400, `invalid_target`; obtain separate grants for the resources |
| Exchange requests authorization details that cannot be confined to its resource | IdP | HTTP 400, `invalid_authorization_details`; no ID-JAG |
| Redemption requests a resource different from the grant's resource | RAS | HTTP 400, `invalid_target`; no access token |
| ID-JAG `resource` is an empty or multi-element array | RAS | HTTP 400, `invalid_grant`; a grant identifies exactly one resource |
| Client assertion remains valid, but its Identity Binding is disabled | IdP | HTTP 400, `invalid_grant`; no actor can be resolved through this binding |
| Client assertion and Identity Binding remain valid, but the Client Association for `analysis-client` is disabled | IdP | HTTP 400, `actor_unauthorized`; no ID-JAG |
| Redemption carries a valid DPoP proof signed with another key, while the ID-JAG contains `cnf.jkt=JKT_K` | RAS | HTTP 400, `invalid_grant`; no access token |
| Bound governed agent access is required, but the grant has no `cnf` | RAS | HTTP 400, `invalid_grant`; no fallback to governed agent access |
| Governed agent access permits unbound grants, but this grant has `cnf.jkt` and redemption omits the proof | RAS | HTTP 400, `invalid_grant`; the existing binding is enforced |
| The client presents the access token for an operation in another tenant, with a fresh valid proof for that request URI | API | HTTP 401, `invalid_token`; no operation performed |
{: title="Rejection examples"}

## Self-Acting Variant {#wag-example}

This non-normative variant issues a WAG to the same dedicated client
under {{wag-flow}}. The client authenticates with a fresh assertion,
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

The IdP resolves `analysis-client` to `agent-42`, verifies a Client
Association for self-acting issuance and the agent's own authorization
for `files.read` at the resource, and returns `issued_token_type`
`urn:ietf:params:oauth:token-type:wag` with `token_type` `N_A`. The
decoded WAG uses `typ=wag+jwt` and this payload:

~~~ json
{
  "iss": "https://idp.example/",
  "sub": "agent-42",
  "aud": "https://ras.example/",
  "iat": 1789488000,
  "exp": 1789488300,
  "jti": "wag-1",
  "client_id": "analysis-api",
  "resource": "https://api.example/tenants/acme-data/",
  "scope": "files.read",
  "cnf": {"jkt":"JKT_K"}
}
~~~

Redemption reuses the request in {{redemption-example}} with the WAG as the
`assertion`. The RAS correlates (`https://idp.example/`, `agent-42`) to
`service-principal-42`, applies its own policy for that principal, and
issues an access token with `sub` `service-principal-42`, no `act`, the
same audience, scope, and `cnf`, and no refresh token. The API enforces
the agent's own permissions and the tenant; it applies no actor gate.

# Input Variants {#input-variants}

These non-normative variants change only the agent-resolution input of
the dedicated-client walkthrough in {{walkthrough}}. The message
sequence is unchanged, and identifiers and keys differ only as noted
below. The resulting actor is always the IdP issuer and `agent-42`, and
the RAS never receives or validates the original credential.

| Variant | Authentication and presentation | Identity resolved |
|---|---|---|
| Shared client with JWT-SVID | IdP `client_id` `platform-sso`; `client_assertion_type` `jwt-spiffe`; the JWT-SVID is the `client_assertion`; no actor-token parameters | Approved trust domain and exact SPIFFE ID in `sub`, under {{jwt-svid-input}} |
| WIT-SVID | `spiffe_wit`: WIT-SVID in `OAuth-Client-Attestation` with a fresh PoP header signed by its key; `client_id` is the SPIFFE ID; no actor-token parameters | Exact SPIFFE ID in the validated `sub`, under {{spiffe-input}} |
| X.509-SVID | `spiffe_x509`: mutual-TLS authentication with the X.509-SVID; `client_id` is the SPIFFE ID; no actor-token parameters | Exact URI Subject Alternative Name, under {{spiffe-input}} |
| Platform JWT (AWS STS) | IdP `client_id` `platform-sso` with a separately configured authentication method; the STS JWT is the `actor_token` with type `jwt` | Exact issuer, `sub`, and selector, under {{imported-jwt-input}} |
{: title="Input variants relative to the dedicated-client walkthrough"}

In the bound profile the issuance DPoP proof is signed by K, except that
the WIT-SVID variant signs it with the WIT-SVID key; the X.509 variant's
DPoP key may differ from the TLS key. The grant expires no later than
the credential's validity or effective evidence deadline. The
JWT-SVID and platform JWT variants keep a separate Client Association
for `platform-sso`; the WIT-SVID and X.509-SVID bindings carry their
own permission. The dedicated-client rejection cases that do not
depend on client-assertion replay apply to each binding;
credential-specific replay rules follow the input specification.

## Shared Platform Client with SPIFFE {#shared-client-example}

This variant completes {{identity-example}}. The workload obtains a
JWT-SVID with the IdP issuer as its audience; `iss` and `iat` are
omitted in the existing SPIFFE format, and the expiration is an
illustrative NumericDate value. The IdP selects trusted signing keys
from its configured bundle for the `platform.example` trust domain.

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
association and resolves the agent separately. It is bearer evidence; it
does not attest that grant proof key K belongs to the workload.
`platform-api` replaces `analysis-api` in grants, access tokens, and RAS
client authentication.

## WIT-SVID and X.509-SVID {#svid-context-example}

Both variants resolve the workload authenticated on the exchange request
through an exact Identity Binding from
`spiffe://platform.example/agents/analysis` to `agent-42`. The user ID
Token is issued to that authenticated client, not reused from
`analysis-client`. The WIT-SVID carries the SPIFFE ID in `sub` and the
workload public key in `cnf.jwk`. For X.509-SVID, the two attestation
headers are replaced by mutual-TLS authentication. An authoritative
association supplies the downstream client identifier in both cases.

## AWS Workload Identity Binding {#aws-example}

This variant uses the AWS STS `GetWebIdentityToken` credential
documented in {{AWS-TOKEN-CLAIMS}}. The Identity Binding names the
configured STS issuer as credential authority, the exact `sub`
`arn:aws:iam::123456789012:role/AgentRuntime`, the accepted audience
`https://idp.example/token`, and the selector
`/https:~1~1sts.amazonaws.com~1/aws_account` equal to `123456789012`.
The selector addresses the string `aws_account` within the
`https://sts.amazonaws.com/` object; `~1` escapes each slash in that
member name.

If several agents share this role, issuer and `sub` identify the shared
IAM principal, not an individual agent. Mapping those agents to distinct
Agent Principals requires distinct credential identities or additional
trusted selectors; a caller-supplied agent name does not provide that
distinction. This variant covers evidence resolution, not a product's
end-to-end conformance. User-access-token OBO composition remains
outside the scope of this document ({{access-token-subject-gap}}).

# Document History

RFC Editor: Remove this section before publication.

* Initial version.

# Acknowledgments
{:numbered="false"}

The author thanks Jeff Malnick for review and discussion of this
profile.
