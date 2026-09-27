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
that client indistinguishable at the resource server: individual actions
cannot be attributed, and authorization cannot be withdrawn from one
agent without withdrawing it from all of them.

What an enterprise needs instead is a principal it can authorize once,
audit across resources, and disable everywhere, whose identity does not
change when the agent moves between platforms or rotates credentials.

Enterprise identity already solves a version of this problem for people.
A person has one account, several credentials linked to it, and separate
rules about which applications may use that account. This document
applies that shape to agents. The Agent Principal is the account, an
Identity Binding maps a validated, qualified client or workload identity
to it, and a Client Association states which OAuth client may exercise
that binding. The account's identifier can be the same as the execution
identity's; the binding decides which identity is authoritative for
governance.

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
   how an actor authenticated through a client or workload credential is
   named in it, or how a resource domain correlates that name with local
   state.

AIMS {{AIMS}} describes a broader framework for agent identity
management. This document is an OAuth deployment profile within that
space that fills those gaps. It is not a governance framework: it
defines how the identities in one transaction relate across
authorization domains. An identity provider (IdP) resolves an
authenticated client or workload identity to an Agent Principal, and
OAuth grants carry that principal into the resource domain. A service
provider can then authorize, audit, and disable a stable,
enterprise-governed agent without understanding the runtime or
credential that currently executes it.

The federation model ({{model}}) is independent of the grant that
carries it. Two peer realizations carry it, each with its own mandatory
path, and an implementation claims one or both ({{scope}}):

* **Delegated access ({{delegated-flow}}):** ID-JAG, with the user as
  subject and the Agent Principal as actor.
* **Self-acting access ({{wag-flow}}):** the Workload Authorization
  Grant (WAG), with the Agent Principal as subject.

Other grant realizations require their own composition rules; the
federation model alone does not define their wire behavior. RFC 7523
client assertions, SPIFFE JWT Verifiable Identity Documents (JWT-SVIDs),
and the other supported credentials supply inputs to the same identity
model ({{evidence}}, {{optional-input-profiles}}).

This document federates an agent governed by the IdP that issues the
grant into a resource domain. It does not define identity continuity
across a chain of IdPs or brokers; forwarding an actor from another
IdP's namespace is out of scope. Also out of scope are task or mission
authorization, asynchronous approval, continuation composition,
provisioning protocols and account administration, multi-agent
delegation chains, instance identification and propagation, client
attester endorsement, and enrollment or key-replacement protocols
({{upstream-gaps}}).

{{scope}} states what each role implements. Implementers of the client,
IdP, resource authorization server (RAS), and API (resource server) can
read in this order:

| Role | Start with | Then read |
|---|---|---|
| All roles | {{model}}, {{scope}} | {{metadata}}, {{security}} |
| Client | {{evidence}}, {{root-request}}, {{wag-request}} | {{grant-protection}}, {{redemption-request}}, {{access-token-response}}, {{client-token-reuse}}, {{wag-redemption}}, {{discovery}}, {{errors}} |
| IdP | {{identity}}, {{authorization}} | {{exchange-request}}, {{wag-issuance}}, {{errors}} |
| RAS | {{sp-contract}}, {{redemption}} | {{agent-correlation}}, {{actor-authorization}}, {{wag-redemption}}, {{ras-refresh}}, {{errors}} |
| API | {{api-processing}} | {{actor-authorization}}, {{access-token-protection}}, {{wag-api}} |
{: title="Reading guide"}

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

Two companion profiles complete the family: {{AGENT-MANAGEMENT}}
establishes the relationships at the IdP, this document exercises them
to obtain authorization, and {{AGENT-LIFECYCLE}} carries the principal's
administrative state into the resource domain and revokes what depends
on it. They add two administrative roles. The Provisioning Client is a
platform connector that manages Agent Principals and their relationships
at the IdP, whose System for Cross-domain Identity Management (SCIM)
service is the IdP Service Provider. The Receiver is the resource-domain
SCIM service together with the RAS components that accept IdP
provisioning. In the companion SCIM profiles, "Service Provider" alone
denotes the IdP-side SCIM service; the Service Provider Contract
({{sp-contract}}) concerns the resource domain.

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
  Agent Principal, which can have the same identifier as that identity.
  It is administered in a Governance Tenant and establishes identity
  resolution, not permission to exercise the agent.

Client Association:
: An approved permission for an authenticated OAuth client to use an
  Agent Principal through the selected Identity Binding, acting
  relationship, and credential class ({{identity-binding}}).

Credential class:
: A configured category of agent-resolution input with mutually
  exclusive validation rules, such as an RFC 7523 client assertion, a
  SPIFFE Verifiable Identity Document (SVID), Client Attestation, or a
  platform issuer's workload JWT profile. JWT encoding alone does not
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
another. A local principal link identifies the agent; resource policy
still determines whether to accept its delegated access.

## Service Provider Contract {#sp-contract}

The mapping from execution identity to Agent Principal is local to the
IdP; the security contract across the boundary between the IdP and the
resource domain is interoperable. The RAS does not resolve the agent
from the execution credential; the grant carries the resolved Agent
Principal instead. The RAS performs no platform-specific credential validation or
workload resolution, and it need not know which input the agent
authenticated with. From a validated grant it receives:

* the Agent Principal, qualified by its governing issuer: `act.iss` and
  `act.sub` in an ID-JAG ({{actor-construction}}), or `iss` and `sub` in
  a WAG;
* the acting relationship: delegated, with the user as subject, or
  self-acting;
* the client's registration at the RAS, in `client_id`; and
* the authority the IdP approved, as a ceiling for the RAS decision.

The RAS correlates the Agent Principal with a local principal, which can
be an existing service principal, without replacing the IdP-qualified
identity ({{agent-correlation}}); for delegated access, it translates
the user into its local namespace and preserves the agent
({{subject-resolution}}, {{agent-correlation}}). Correlation does not
grant authority: the RAS
decides within the grant's ceiling ({{actor-authorization}},
{{wag-redemption}}).

## Authentication, Resolution, and Proof {#inputs}

The IdP MUST validate a credential according to its configured type
before using it for identity resolution; a generic JWT token-type URI,
an unverified header, or a caller-supplied claim MUST NOT select a
weaker validation path or establish an Identity Binding. Unrecognized
request parameters and JWT claims follow {{Section 3.2 of RFC6749}} and
{{Section 4 of RFC7519}}.

The IdP MUST NOT substitute one of three distinct functions for another:

* **Client authentication:** evidence authenticating the OAuth client.
* **Agent resolution:** resolution of the authenticated dedicated-client
  identity or independently validated workload identity through an
  Identity Binding to exactly one Agent Principal.
* **Key possession:** proof that the presenter controls a key, with the
  binding semantics of the proof mechanism.

Up to three identities meet in one request: the workload identity
asserted by accepted evidence ({{evidence}}), the authenticated OAuth
client, and the Agent Principal ({{identity-binding}}). None of them is
inferred from another; with a dedicated client, the authenticated client
identity is itself the resolution input and no separate workload
identity exists. The distinction between an issuer-bound presenter key
and a request proof key ({{terms}}) determines what a proof establishes.

The same credential can serve client authentication and agent resolution
without making the client and agent the same principal. Successful
client authentication MUST NOT imply successful agent resolution, and
successful agent resolution MUST NOT imply permission for the
authenticated client to exercise that agent.

## Canonical Identity and Tenant Boundaries {#canonical-identity}

The Agent Principal identifier MUST be unique and non-reassignable
within the IdP issuer's namespace, across all Governance Tenants sharing
that issuer identifier. Because the Governance Tenant is not an
additional component of the downstream agent identity, a tenant-local
identifier needs qualification to meet this issuer-wide uniqueness
requirement before use as an Agent Principal identifier.

The identifier need not equal an external subject, OAuth client
identifier, SPIFFE ID, display name, or instance identifier. This
profile provides identity continuity for the agent across changes of
execution environment, through Identity Binding, and across the boundary
between the IdP and the resource domain. Identity continuity is an
explicit decision by the governing authority to preserve the same
principal; it does not imply that the principal's permissions remain
unchanged. It is not work continuity: whether an approved task, with its
purpose, approval, and lifecycle, still justifies an action is outside
this profile.

After a transfer to a different Governance Tenant under a different
administrative authority, the IdP MUST assert the agent under a new
Agent Principal identifier. Delegations held for the previous identifier
do not carry forward automatically ({{delegation-authorization}}). RAS
principal links held for the previous identifier MUST NOT be re-keyed to
the new identifier ({{agent-correlation}}). This document defines no
cross-tenant identity migration protocol. For example, moving an agent
to another customer's governance domain creates a new identity, while
renaming a tenant or changing its owner or administrator within the same
governance domain does not by itself change the principal.

The IdP MUST establish an unambiguous Governance Tenant and, before
issuance, the Target Tenant for the requested RAS and resource. The RAS
MUST interpret an agent identifier in its asserted issuer context and
MUST NOT key agent authorization on a bare `sub`. Tenant resolution
failures use the errors in {{errors}}.

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
transfer, or increase Agent Principal authority. This profile defines no
aggregate budget, quota, or concurrency semantics.

## Grant Paths {#paths}

An Agent Principal is not intrinsically self-acting or delegated. The
authorization transaction determines whether it is represented as the
subject, in a WAG ({{wag-flow}}), or as the actor for a user, in an
ID-JAG ({{delegated-flow}}). Authorization for one relationship does not
imply authorization for the other.

## Adoption Profiles {#adoption-profiles}

The adoption path preserves existing Enterprise-Managed Authorization
{{EMA}} deployments, which need no changes to continue, and adds agent
governance before requiring grant binding. The names identify deployment
profiles, not assurance ratings.

| Adoption profile | Required addition | Grant protection |
|---|---|---|
| Enterprise access | Existing EMA and base ID-JAG; no separate Agent Principal required | Existing deployment policy |
| Governed agent access | Agent resolution, Identity Binding, Client Association, the governed actor (delegated) or subject (self-acting), tenant enforcement, and the downstream actor gate for delegated access | Grants without sender constraint permitted only by explicit policy; any binding present is enforced |
| Bound governed agent access | All governed agent requirements plus DPoP at grant issuance and redemption | `cnf.jkt` and same-key continuity required |
{: title="Adoption profiles"}

Enterprise access is a migration baseline, not conformance to this
document's governed profiles. Adding `act` alone does not establish
governed agent conformance: identity resolution and actor authorization
are also required. The adoption profiles apply to both realizations,
each under its own URIs ({{metadata}}).

"Bound" refers to sender constraint on the grant, ID-JAG or WAG, between
issuance and redemption; it does not imply sender constraint on the
agent-resolution credential or the resulting access token. Grant
protection, workload-evidence protection,
and access-token protection are separate choices: even bound governed
agent access can use bearer workload evidence and, under explicit
resource policy, bearer access tokens. Credential-class validation
follows {{actor-inputs}}, grant protection and downgrade prevention
follow {{grant-protection}} and {{discovery}}, and protection on the API
hop follows {{access-token-protection}}.

## Federation Configuration {#configuration}

The relationships in {{model}} require trusted configuration, not a
particular storage representation or administrative interface. Existing
workload-federation configuration can supply credential trust and exact
identity selectors; the Agent Principal mapping and separate Client
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
  registration at the RAS ({{Section 5 of ID-JAG}}), from which the IdP
  derives the grant's `client_id` ({{flow-configuration}}). No companion
  profile provisions it. Using one identifier at both servers, which a
  Client ID Metadata Document (CIMD) {{CIMD}} Client Identifier URL
  provides by construction, makes that mapping the identity mapping.

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

* **Target Tenant binding:** one Target Tenant, configured once and
  carried consistently by the tenant-specific resource URI
  ({{root-request}}), the resource domain's provisioning context, and any
  Shared Signals stream ({{AGENT-LIFECYCLE}}). This profile assumes
  deployments configure these carriers to agree.
* **Applicable profile** (client, IdP, RAS, and resource policy):
  profile and minimum requirements per client, trust relationship, and
  resource, which each role enforces as applicable to it
  ({{discovery}}).

Validation occurs while a request is processed, not when an Agent
Principal, Identity Binding, or Client Association is created. Keys and
metadata may already be held; their retrieval and refresh follow the
rules of the source that supplies them ({{evidence}},
{{redemption-validation}}, {{metadata}}).

Discovery exposes capabilities, not these authorization decisions
({{discovery}}). Credential metadata follows its credential
specification; discovery MUST NOT establish trust. Bindings,
associations, delegation, and local links have no discovery mechanism
here.

Request hints, discovered client metadata, and unverified JWT claims
MUST NOT by themselves establish credential-authority trust or change an
approved Identity Binding or Client Association. Creating and changing
bindings and associations, including imports from platform registries,
is an administrative act outside this profile
({{operational-guidance}}); {{AGENT-MANAGEMENT}} defines a proposed
platform-to-IdP management interface for it. {{identity-example}}
illustrates the shared-client case; {{aws-example}} applies the model to
an AWS Security Token Service (STS) workload credential.

## Identity Mapping Example {#identity-example}

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

The RAS translates the user and preserves the agent: `alice-ras` is
Alice's identifier in the target SSO namespace, `platform-api` is the
registration corresponding to `platform-sso` at the RAS, and the local
agent record `service-principal-42` supports authorization but does not
replace `act.sub`. {{identity-binding}} shows one agent resolving
through several bindings. {{shared-client-example}} supplies the
credential and request details for this scenario, using the complete
message sequence in {{walkthrough}}.

# Agent Principal Resolution {#identity}

Resolution turns validated inputs into principals: an approved Identity
Binding resolves a qualified client or workload identity to one Agent
Principal, subject resolution identifies the user for delegated access,
and the RAS correlates both with its local principals.

## Agent Resolution Inputs {#evidence}

Every agent-resolution input satisfies this contract, which summarizes
requirements stated in {{inputs}}, {{identity-binding}},
{{credential-requirements}}, and the input's own section:

* **Independent validation:** The credential is validated under its
  configured credential profile before it is used for resolution
  ({{inputs}}).
* **Qualified identity:** The input yields an authenticated identity and
  identifies the credential authority or client-registration context
  that qualifies it. That qualified identity keys the Identity Binding
  ({{identity-binding}}).
* **Credential authority:** For workload evidence, the IdP relies on the
  credential mechanism having authorized issuance for the asserted
  workload identity; a caller-supplied subject or agent identifier alone
  MUST NOT establish that identity. For dedicated clients, the IdP
  relies on the configured client-authentication method and approved
  binding.
* **Proof semantics:** The input states whether it is bearer evidence or
  binds a key, and what that proof establishes
  ({{credential-requirements}}).

Credential acquisition is outside this profile. Audience validation
follows each input's credential specification and section; there is no
universal IdP audience.

| Input | Qualified identity | Mode ({{actor-inputs}}) | Reference |
|---|---|---|---|
| Dedicated client | Trusted assertion issuer and exact client `sub`, qualified by the IdP client-registration context | Authentication context | {{client-assertion-input}} |
| Existing platform JWT | Approved issuer and exact `sub`, with configured additional selectors | Presented evidence | {{imported-jwt-input}} |
| SPIFFE JWT-SVID | Approved trust domain and exact SPIFFE ID in `sub` | Authentication context | {{jwt-svid-input}} |
| SPIFFE WIT-SVID | Approved trust domain and exact SPIFFE ID in the validated `sub` | Authentication context | {{spiffe-input}} |
| SPIFFE X.509-SVID | Approved trust domain and exact SPIFFE ID in the certificate's URI Subject Alternative Name | Authentication context | {{spiffe-input}} |
| Client Attestation | Trusted attester and validated `sub`, which identifies the OAuth client; the client-to-agent mapping is explicit | Authentication context | {{agent-evidence}} |
{: title="Agent-resolution inputs and qualified identities"}

Input support follows {{scope}} and {{optional-inputs}}; resolution mode
selection and rejection follow {{actor-inputs}}.

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
to that workload. An attacker who holds acceptable bearer workload
evidence and passes client authentication, Client Association, and
either the user-credential and delegation checks or the
agent-authorization check can obtain a grant, bound to a grant proof key
of its choice, while impersonating the workload. In the JWT-SVID path,
the same bearer credential also satisfies client authentication; that
check is not an independent possession factor.

Short evidence lifetimes limit this exposure; sender-constraining the
output does not prevent it ({{baseline-costs}}).

## Identity Binding {#identity-binding}

**Resolution:** After validating the configured resolution input, the
IdP MUST:

* Resolve the exact qualified client or workload identity ({{evidence}})
  to one active Agent Principal through an enabled Identity Binding;
  reject missing, ambiguous, or disabled mappings.
* Apply exact resolution even when client authentication permits a
  prefix match. A client identifier, including a {{CIMD}} URL,
  identifies the client, not the agent.

Similar names, unqualified identifiers, or a shared signing key MUST
NOT establish identity equivalence.

**Disabling:** An Identity Binding can be disabled independently of the
Agent Principal and its other bindings. A disabled binding MUST NOT
authorize new grant issuance. Disabling a binding does not itself revoke
outstanding tokens; their treatment follows {{status-changes}}.

**Client Association:** Before issuing a governed grant, the IdP MUST
verify that a Client Association permits the authenticated client to use
the selected Identity Binding, with the selected credential class, for
the requested acting relationship ({{configuration}}). Permission for
delegated issuance does not imply self-acting issuance, nor the reverse.
The IdP MUST NOT substitute the client's identity for the resolved
actor.

A Client Association can authorize several Identity Bindings.
Authorization of one binding, a credential authority, a credential
class, or the Agent Principal itself MUST NOT imply authorization of
another binding unless the association's policy explicitly includes it.
No association overrides a disabled binding. Policy representation and
evaluation mechanisms are outside this profile.

For a dedicated client, deployments can administer the Identity Binding
and the Client Association in one registration or policy object; they
remain separate checks.

For example, one Agent Principal can carry a binding for each platform
it runs on, each keyed by its own issuer and selectors:

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

B1 and B2 both resolve to agent-42, which the issued grant names
({{aws-example}} shows B2). Disabling B3 stops new issuance through B3
only; an association naming B1 and B2 still authorizes them, subject to
the remaining checks.

## Subject Resolution and Linking {#subject-resolution}

For ID-JAG, subject resolution identifies the user and linking
associates that user with a local account; self-acting access resolves
the agent as subject ({{wag-flow}}). Subject identifiers, tenant
relationships, `aud_sub`, `aud_tenant`, and `sub_id` follow Sections
3.1, 5, and 6 of {{ID-JAG}}, with these additions.

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

A changed Identity Binding or local agent link MUST NOT transfer an
existing delegation to a different agent.

**Actor preservation:** The RAS MUST preserve the complete validated
`act` object in the access token or its introspection context, including
`iss`, `sub`, and any `sub_profile`, under
{{Section 3.6.3.2 of ACTOR-PROFILE}}. It MUST NOT add, remove, or
rewrite actor members. Preservation applies to JSON members and values,
not to serialization, whitespace, or member order. In particular, the
RAS MUST NOT translate `act.sub` to its local agent-principal identifier
or replace `act.iss` with its own issuer. That rule concerns the actor
of a delegated token; for self-acting access the access token's subject
is the local principal and the qualified identity is retained under
{{wag-redemption}}.

The IdP or an authorized directory connector can provision local agent
principals, keyed by the same pair; no provisioning protocol is required
({{operational-guidance}}). Once deactivation is applied, the RAS
enforces {{applied-changes}}.

### Just-in-Time Correlation {#jit-correlation}

Where the RAS requires a local agent record and none exists for the
qualified pair in the authorized Target Tenant, resource policy MAY
permit the RAS to create one from a validated grant: from (`act.iss`,
`act.sub`) of an ID-JAG, or from (`iss`, `sub`) of a WAG under
{{wag-redemption}}. The policy is disabled by default and enabled per
governing issuer and Target Tenant. When it applies, the RAS:

* MUST key the created record by that exact pair and MUST NOT attach
  the pair to an existing record by name or other descriptive match;
* MUST apply local restrictions, retained revocation state under
  {{applied-changes}}, and local policy before issuance; and
* sets the record's initial eligibility by local policy; a record
  created ineligible denies the triggering request.

Creating the record is correlation, not authorization: the actor gate
({{actor-authorization}}) and resource policy still apply. A grant does
not carry the IdP's administrative status, so creation does not
substitute for propagating disablement: without provisioning, the RAS
learns of disablement only through local action or another signal
({{status-changes}}). {{AGENT-LIFECYCLE}} defines provisioning and
reconciliation of a created record for Receivers that conform to it;
this document does not.

# Authorization Relationship {#authorization}

Validated identity does not grant authority. After resolution under
{{inputs}} and {{identity}}, the IdP MUST
authorize issuance under current assignments and policy for the resolved
agent, authenticated client, acting relationship, Governance and Target
Tenants, RAS, resource, and requested authority. The authority asserted
in a delegated grant MUST be bounded by both:

* The authority the IdP is authorized to assert for the user.
* The authority permitted by the agent's delegation authorization
  ({{delegation-authorization}}).

For a self-acting grant, the asserted authority MUST be bounded by the
Agent Authorization ({{agent-authorization}}).

The basis for Agent or Delegation Authorization is a deployment choice;
administrator assignment, organizational policy, task authorization,
and, for Delegation Authorization, user consent are all acceptable.
Assignment and approval records and their storage are outside this
profile.

The RAS and API determine effective resource and operation
authorization, including the actor gate ({{actor-authorization}}). The
IdP need not interpret every tool argument or business object. An
issuance decision that depends on those semantics requires authoritative
resource-domain evaluation, locally or through a trusted policy service.

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

## Delegation Authorization {#delegation-authorization}

Before constructing `act`, the IdP MUST authorize the resolved Agent
Principal to act for the user in the requested client, tenant, RAS,
resource, and authority context. The IdP MUST reject missing, revoked,
expired, or insufficient delegation authorization. Valid credentials,
user sign-in, or a shared client MUST NOT imply that authorization or
permit one agent to use another agent's. Pre-existing actor chains are
rejected under {{actor-inputs}}.

## Authorization Lifetime {#authorization-lifetime}

Credential or ID-JAG expiration does not by itself terminate an access
token or RAS refresh authorization already issued; the ID-JAG's `exp`
limits redemption, not subsequent access.

The RAS MUST limit access-token and refresh-authorization lifetimes
under its local policy ({{ras-refresh}}). This profile defines no
portable IdP-imposed deadline on downstream authorization
({{deadline-gap}}) and requires no shared approval record or correlated
lifetime lookup.

If IdP approval requires a downstream lifetime condition that the
selected composition cannot enforce, the IdP MUST reject issuance
with `actor_unauthorized` for delegated issuance or `invalid_target`
for self-acting issuance. It MUST NOT discard that condition or treat
a shorter ID-JAG lifetime as enforcing it. Revocation follows
{{status-changes}}.

## Delegated Actor Authorization {#actor-authorization}

For delegated access, the RAS and API MUST enforce both:

* **User authority:** the requested operation is within the user's
  permissions and the grant or token's authorized scope and constraints.
* **Actor gate:** the issuer-qualified agent is permitted to act for
  that user in the selected tenant and resource, within the authorized
  delegation. A valid signature or an `act` claim alone does not open
  the gate; failure to establish it MUST result in denial.

The actor gate is an authorization condition, not a protocol object. It
can be implemented through an agent registration, tenant assignment,
consent policy, or another explicit rule. Requiring the agent to also
hold independent permissions on each object is local policy, not a
baseline requirement.

Every operation the API permits MUST be covered by an applicable
actor-gate authorization. The API MAY evaluate the gate directly or rely
on a validated RAS authorization whose scope and freshness satisfy
resource policy; a fresh policy-service evaluation is not required for
every request.

An ID-JAG issued under this profile asserts that the IdP authorized the
specified delegation within the grant's constraints; it does not assert
that the RAS's policy has been satisfied or convey the IdP's underlying
approval records. The RAS MUST independently decide whether to accept
that delegation under its local user, actor, client, tenant, and
resource policy.

The client identifier MUST NOT stand in for the actor in authorization.
Audit records that identify both the user and the issuer-qualified actor,
rather than the client identifier alone, preserve attribution.

# Delegated Access with ID-JAG {#delegated-flow}

This section profiles ID-JAG issuance and redemption through the actor
extension point in {{Section 9.7 of ID-JAG}}; where it is silent,
ID-JAG applies unchanged. {{profile-additions}} lists each change, and
the sections after it state the rules.

## Relationship to Base Specifications {#profile-additions}

This table is non-normative; the referenced sections define each
requirement.

| Area | Profile requirement | Defined in |
|---|---|---|
| Actor extension | Identity Binding resolves the agent; a separate Client Association authorizes client use | {{identity-binding}} |
| Dedicated-client input | Resolved from authenticated client context; issuer identifier as sole assertion audience; single-use `jti` | {{client-assertion-input}}, {{Section 4 of RFC7523bis}} |
| Other authentication-context inputs | Resolved from the identity validated by SPIFFE or Client Attestation authentication | {{optional-input-profiles}}, {{actor-inputs}} |
| Actor representation | One actor: Agent Principal as `act.sub`, IdP as `act.iss`; replaces Actor Profile's credential-to-actor copying | {{actor-construction}} |
| Request narrowing | Configured resolution mode; one resource; non-empty scope; actor-token parameters required in presented-evidence mode and rejected otherwise; no incoming actor chain | {{root-request}}, {{actor-inputs}} |
| Identity and client binding | Users and agents resolved separately; downstream `client_id` from an authoritative client-registration association | {{subject-resolution}}, {{agent-correlation}}, {{flow-configuration}} |
| Grant narrowing | One resource URI (a string; singleton arrays accepted), scope constraints, input-specific expiration limits; DPoP and `cnf.jkt` in the bound profile | {{grant-issuance}}, {{redemption-validation}}, {{grant-protection}} |
| Resource processing | Actor and tenant context preserved; user authority and actor gate enforced with the selected token protection | {{access-token-response}}, {{api-processing}} |
| Refresh narrowing | Explicit policy, client binding, preserved proof binding and profile, finite absolute authorization expiration | {{ras-refresh}} |
| Error processing | `invalid_grant`, not RFC 8693's default `invalid_request`, for actor credential or resolution failures; `actor_unauthorized` for a denied resolved actor | {{errors}} |
| Profile discovery | Governed profiles in existing ID-JAG metadata; trusted policy sets the minimum | {{metadata}} |
{: title="Additions and narrowings to the base specifications"}

## Prerequisites and Common Capabilities {#flow-configuration}

**Applicability:** This section and {{grant-protection}} apply to both
the ID-JAG and the WAG.

**Relationships:** The IdP MUST issue a grant only under the applicable
identity, client, delegation, and target relationships in
{{configuration}}.

**Downstream client:** The IdP MUST derive the grant's `client_id` from
an authoritative association between the authenticated IdP client and
that client's registration at the target RAS. A client-supplied
downstream client identifier MUST NOT select or override that
association, which is the client registration association of
{{configuration}}, not a Client Association.

**Client authentication:** RFC 7523 client authentication at either
server follows {{client-assertion-input}}, and JWT-SVID authentication
follows {{jwt-svid-input}}; other configured methods MAY be used, and
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

## Grant Protection {#grant-protection}

These rules apply to both grants, the ID-JAG and the WAG. Client
authentication and all governance requirements remain mandatory in
either profile.

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

## Token Exchange {#exchange-request}

### Request {#root-request}

The client sends the token exchange request of {{Section 4.3 of ID-JAG}}
to the IdP token endpoint, authenticates as the configured client, and
supplies any proof required by {{grant-protection}}. The following
parameters are REQUIRED except where the resolution mode specifies
otherwise:

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

**Resource:** The request MUST contain exactly one `resource` parameter.
A client requiring access to multiple resources MUST obtain a separate
grant for each resource. The IdP MUST reject multiple `resource`
parameters with `invalid_target`. The `resource` URI conveys the Target
Tenant through the configured resource-to-tenant association, not the
IdP's Governance Tenant.

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
  establish that permission. That authorization can include an
  explicitly associated cross-domain delegation authorization,
  represented and provisioned locally by the IdP; OpenID Connect scope
  names do not themselves map to resource-specific permissions. Any
  binding retained with the refresh token MUST be enforced rather than
  bypassed by selecting another agent-resolution input, with conflicts
  rejected as `invalid_grant`.

**Also required:** Every subject input requires a current validated
agent-resolution input and delegation authorization under
{{delegation-authorization}}. User access tokens are not subject inputs
({{access-token-subject-gap}}); JWT encoding alone does not make an
access token an ID Token.

### Agent Resolution Input Validation {#actor-inputs}

**Mode selection:** After client authentication, the IdP MUST determine
the resolution mode from trusted configuration for the authenticated
client, applicable profile, and target. If that configuration does not
establish an unambiguous mode, it MUST reject the request with
`invalid_request`. The presence or absence of actor-token parameters
MUST NOT select or change that mode.

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
  issuance, the evidence is the subject token ({{wag-request}}).
  Validate the separate platform JWT under {{imported-jwt-input}}.
  Missing or rejected evidence MUST NOT trigger resolution from
  authentication context.

**Credential class:** The IdP MUST select exactly one configured
platform credential class for actor evidence, or reject with
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

**Delegated result:** In delegated issuance both modes proceed through
{{actor-construction}}, and a governed request MUST result in the
required governed `act` or fail; omitting actor-token parameters in
authentication-context mode does not request ordinary EMA or
subject-only impersonation.

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

**Claims:** The ID-JAG MUST use the format and claims of
{{Section 3.1 of ID-JAG}} and additionally satisfy:

| Claim | Required result |
|---|---|
| `sub` | Same user as the validated subject credential, expressed in the IdP's subject namespace for the RAS |
| `act` | Agent Principal actor constructed under {{actor-construction}} |
| `cnf.jkt` | Thumbprint of the grant proof key when DPoP is used at issuance; REQUIRED for bound governed agent access ({{grant-protection}}) |
| `resource` | The authorized resource URI, issued as a JSON string; receivers also accept a single-element array under {{redemption-validation}} |
| `scope` | Non-empty authorized scope string, no broader than the approved request |
| `client_id` | The client's registration identifier at the RAS, derived under {{flow-configuration}} |
{: title="ID-JAG claims profiled by this document"}

**Unambiguous context:** The IdP MUST NOT issue a grant if it cannot
determine an unambiguous user, actor, downstream client, or tenant
relationship.

**Lifetime:** The grant has three limits:

* **Configured limit:** The grant lifetime SHOULD be at most five
  minutes and MUST NOT exceed the configured lifetime limit.
* **Subject credential:** The grant's expiration MUST NOT exceed the
  subject credential's expiration, determined below.
* **Agent-resolution input:** The grant MUST NOT outlive the validated
  resolution credential, using the bound in the following table. The
  dedicated-client assertion is the exception: it MUST be valid when the
  request is authenticated, but it authenticates one transaction and
  does not cap the grant.

| Input | Lifetime bound on the grant |
|---|---|
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
  configured and agent-resolution input limits apply; absence of a
  recorded expiry does not authorize an unlimited grant lifetime.

### Successful Response {#exchange-response}

The response follows {{Section 4.3.4 of ID-JAG}}. For a bound grant,
the client MUST retain the DPoP key for redemption and SHOULD inspect
the grant to confirm that `cnf.jkt` identifies that key, as specified in
{{Section 9.8.1.1 of ID-JAG}}.

## Redemption {#redemption}

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
3. **Authority:**
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
  under {{agent-correlation}}.
* **Authority:** Redeemed resource as audience and non-empty authorized
  `scope` (otherwise `invalid_scope`), without broadening authority.
* **Protection:** The binding selected under {{access-token-protection}}.
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

**Response:** The response follows {{Section 4.4.2 of ID-JAG}}; the
client MUST reject an output that does not satisfy its configured
protection requirement.

### Access-Token Protection {#access-token-protection}

**Selection:** The RAS MUST issue a sender-constrained access token
unless the resource is explicitly configured to permit bearer tokens.
The permitted protection is selected through trusted client and
resource configuration before issuance, not by a request flag, and a
validation failure MUST NOT trigger a weaker mode.

| Selected protection | Access token |
|---|---|
| DPoP | `cnf.jkt` identifies the validated redemption proof key, which also matches the grant binding when present |
| Mutual TLS | `cnf.x5t#S256` identifies the client certificate validated at redemption; the response uses `token_type=Bearer` |
| Bearer | No `cnf` |
{: title="Access-token protection modes"}

For mutual TLS with a bound grant, the client MUST also prove possession
of the grant's DPoP key in the same redemption request; certificate
possession alone does not redeem the grant. The access token then
carries `cnf.x5t#S256` but not `cnf.jkt`, as {{Section 5 of RFC9449}}
allows for access tokens that are not DPoP-bound; receipt of the grant
proof does not override the configured access-token protection. A native
mutual-TLS-bound grant is future work ({{excluded-compositions}}).

**Enforcement:** The RAS MUST NOT copy the grant's `cnf` into an access
token whose binding will not be enforced, and clients and APIs MUST NOT
treat a constrained token as an unconstrained bearer token or bypass an
unrecognized confirmation method.

### Distributed Platforms and Key Use {#distributed-key-use}

A sender-constrained credential requires proofs from its bound key,
through local custody or an authorized signing arrangement. This
document defines no transition to another key ({{key-transition-gap}}),
so bound-grant issuance and redemption require the same key holder.

A DPoP access token is usable only by a broker holding that key,
including one proxying an authorized worker request, or by a worker
that holds the same key or obtains request-specific proofs from its
authorized key holder. Remote signing interfaces are outside this
profile; remote signing or shared key custody does not establish an
independent worker binding and expands the trusted computing base.

A control plane and worker that cannot share the grant proof key use
governed agent access instead: the control plane obtains an unbound
grant, and the worker redeems it with its own DPoP proof, binding the
access token to the worker's key ({{grant-protection}}).

### Opaque Access Tokens and Introspection {#introspection}

The RAS MAY issue an opaque access token instead of a JWT when the API
obtains equivalent context through token introspection {{RFC7662}}.
For an active token:

* **Identity and authority:** The response MUST carry `sub`, `aud`,
  `scope`, `client_id`, and the validated `act` object unchanged, as the
  `act` introspection member registered by {{Section 7.5 of RFC8693}}.
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
  than reuse an active response. This narrows {{Section 4 of RFC7662}}
  so cached authorization cannot outlive an expiration unknown to the
  API.

### RAS Refresh Tokens {#ras-refresh}

**Issuance:** The RAS SHOULD NOT issue refresh tokens, retaining
{{Section 4.4.3 of ID-JAG}}, but MAY do so for authorized long-running
work under explicit policy. A WAG redemption never yields a refresh
token ({{wag-redemption}}).

**Binding:** The RAS MUST bind each refresh token to the authenticated
client and apply the first applicable additional sender-binding rule
below. Bindings required by the client-authentication method, such as
{{Section 10.3 of ATTEST}}, apply in every row; refresh-token rotation
does not replace them.

| Redemption context | Refresh-token requirement |
|---|---|
| Grant contains `cnf.jkt` | Retain the grant's DPoP key binding, regardless of access-token protection |
| Unbound grant; DPoP proof used at redemption | Bind to the validated redemption proof key |
| No DPoP proof; certificate-bound access token | Bind to the validated mutual-TLS certificate |
| Neither DPoP nor certificate binding | Retain any authentication-method binding; if none applies, require explicit policy permitting client-bound refresh without sender constraint and use rotation under {{Section 4.14 of RFC9700}} |
{: title="Refresh-token sender binding"}

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
   profile under which the grant was accepted; reject with
   `invalid_grant` if it no longer qualifies. Adding a proof does not
   upgrade that authorization.
4. **Lifetime:** Enforce a finite absolute authorization expiration set
   at issuance under local policy and an inactivity limit under
   {{RFC9700}}. Rotation, refresh, or repeated redemption of the same
   ID-JAG MUST NOT reset the absolute expiration. Access beyond it
   requires a new ID-JAG and therefore a fresh IdP decision; that
   ID-JAG starts a new authorization period and leaves the previous
   expiration unchanged.
5. **Output:** Issue access tokens under {{access-token-response}} and
   {{access-token-protection}}, expiring no later than the absolute
   authorization expiration.

### Applied Disablement and Revocation {#applied-changes}

**Applicability:** Authorization derived from either grant.

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

## Token Endpoint Error Responses {#errors}

Token endpoint errors follow {{Section 5.2 of RFC6749}} and the
applicable extension, authentication, and proof specifications.
Servers MUST validate client authentication, credentials, and proofs
before authorization. Proof, grant-binding, grant-claim, and
authorization-detail failures use the errors specified in
{{grant-protection}}, {{spiffe-input}}, {{redemption-validation}}, and
{{root-request}}.

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

Agent-resolution credential failures use `invalid_grant` instead of
the default `invalid_request` of {{Section 2.2.2 of RFC8693}}. Client
authentication failures use the authentication method's error,
including when the same credential supplies an agent-resolution input.

Error descriptions SHOULD NOT reveal identity, binding, or policy
details beyond those disclosed by the error category. Distinguishing
`invalid_grant` from `actor_unauthorized` reveals that an actor was
resolved but denied, even to a holder of stolen bearer evidence who
passes the request's other authentication, but not which
binding-resolution check failed.

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

The client associates each cached grant, access token, and refresh
token with its authorized context: user and Agent Principal, Governance
and Target Tenants, OAuth client registrations, target RAS, resource,
authority, applicable profile, and proof binding. The client MUST reuse
a token or grant only when that context authorizes the operation. A
shared client identifier or matching scope alone MUST NOT permit reuse
across agents, users, or tenants.

The association can use trusted request and configuration context;
clients need not parse opaque tokens. If the client cannot establish
that association, it MUST obtain a token or grant for the current
context. A credential change alone need not invalidate cached tokens
when the governed principal and authorization context remain the same.

## Resource Server Processing {#api-processing}

**Applicability:** The RAS and API MUST establish profile applicability
through trusted issuer, client, and resource configuration or
authoritative token-issuance context. The RAS MUST NOT issue governed
and ordinary tokens for the same client and resource unless the API can
distinguish them through validated claims or authenticated introspection
context. This profile defines no in-band discriminator: the RAS MUST
issue tokens such that the API can determine, from trusted token
context, which adoption profile and acting relationship authorized them
({{wag-api}}).

The API MUST reject ambiguous applicability and reject missing or
malformed `act` for a configured governed delegated population;
self-acting tokens carry no `act` ({{wag-api}}). An ordinary `act`
claim alone does not establish governed issuance.

**Validation:** For tokens subject to this profile, the API MUST
validate access tokens under {{RFC9068}}, or obtain the same context
under {{introspection}}, and MUST enforce the following requirements:

* **Identity:** For delegated tokens, require one `act` object with
  non-empty `iss` and `sub` and no nested `act`. Trust configuration
  MUST authorize the RAS to assert that IdP-qualified agent identity;
  `act.iss` need not equal the access-token issuer.
* **Protection:** Enforce the configured resource mode
  ({{access-token-protection}}) and all token confirmation claims.
  Validate DPoP under {{RFC9449}}, certificate binding under
  {{RFC8705}}, or permitted bearer use under {{RFC6750}}.
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
is bounded under {{status-changes}}.

**Policy services:** If the API delegates authorization evaluation to
a policy decision service, it MUST preserve the distinction between the
user, the issuer-qualified Agent Principal, and the OAuth client, and
supply the tenant and token constraints needed to evaluate the requested
operation. For a self-acting token, the local principal stands for the
Agent Principal. {{AUTHZEN}} is one optional evaluation interface; this
profile defines no mapping to it. A policy permit does not override the
token's constraints.

### Error Responses {#resource-errors}

Challenges and scope errors use the selected scheme: `DPoP` under
{{Section 7.1 of RFC9449}}, or `Bearer` under {{RFC6750}} for bearer
and mutual-TLS tokens.

| Failure | Response |
|---|---|
| Missing or invalid required actor claims; unauthorized namespace assertion; missing, ambiguous, or conflicting token tenant context, or a token tenant different from the requested operation's tenant | HTTP 401, `invalid_token` |
| Denial for a valid actor identity | HTTP 403, `actor_unauthorized` under {{Section 8.2 of ACTOR-PROFILE}} |
{: title="Resource server error responses"}

Actor denial MUST NOT use `insufficient_scope`. The API MUST NOT expose
actor-specific rejection details outside the trust domain.

# Self-Acting Access with WAG {#wag-flow}

This section defines self-acting access, the peer of
{{delegated-flow}}: the Agent Principal is the subject of a Workload
Authorization Grant (WAG) {{WAG}} issued by the IdP and redeemed at the
RAS. Each subsection names the delegated rules it reuses and states its
exceptions. The WAG token and JWT types are provisional; their final
spelling does not affect processing ({{wag-gaps}}).
## Differences from Delegated Access {#wag-differences}

| Area | Delegated ID-JAG | Self-acting WAG |
|---|---|---|
| Subject | User, from the subject credential | Agent Principal, from the agent-resolution input |
| Agent representation | Agent Principal in `act`, which the RAS keeps beside the local user as subject | Grant subject, with no `act` ({{wag-claims}}); the RAS correlates it to a local agent principal ({{agent-correlation}}) |
| Authorization | Delegation Authorization; Client Association for delegated issuance | Agent Authorization ({{agent-authorization}}); a separate Client Association for self-acting issuance |
| API enforcement | User authority and the actor gate | The agent's own authority; no actor gate |
| Refresh | RAS refresh under explicit policy | None; WAG prohibits refresh tokens |
{: title="Self-acting differences from delegated access"}

## Self-Acting Issuance {#wag-issuance}

Self-acting issuance is one token exchange with two resolution modes.
The relationship, downstream client, client authentication, and
algorithm rules of {{flow-configuration}} apply. The IdP MUST:

1. Authenticate the client and validate the resolution input under
   {{evidence}} and {{actor-inputs}}, as presented under
   {{wag-request}}.
2. Resolve the Agent Principal through an active Identity Binding
   ({{identity-binding}}) from the configured input: the workload
   credential presented as the subject token, or the authenticated
   client identity.
3. Verify the Client Association for self-acting issuance
   ({{identity-binding}}).
4. Apply Agent Authorization ({{agent-authorization}}) for the requested
   RAS, resource, and authority. No user is involved.
5. Apply {{grant-protection}} and issue the WAG under {{wag-claims}}.

**Failures:** {{wag-errors}}.

The client redeems the WAG under {{wag-redemption}}; {{wag-example}}
shows the messages.

## Issuance Request {#wag-request}

Token exchange is used because only its `issued_token_type`
({{RFC8693}}) labels the output as an assertion for another token
endpoint. The request follows {{root-request}}, including its resource,
scope, and authorization-details rules, with the differences below. The
subject token carries the agent-resolution input and is not processed
under {{subject-token-validation}}.

| Parameter | Value |
|---|---|
| `requested_token_type` | `urn:ietf:params:oauth:token-type:wag` (provisional) |
| `subject_token`, `subject_token_type` | Per resolution mode, below |
| `actor_token`, `actor_token_type` | MUST be absent |
| `audience`, `resource`, `scope` | As in {{root-request}} |
{: title="Self-acting issuance request"}

**Mode selection:** Configured under {{actor-inputs}}.

**Presented-evidence resolution:** The workload credential is the
subject token, with `subject_token_type`
`urn:ietf:params:oauth:token-type:jwt`, and the client authenticates
separately; the existing platform JWT ({{imported-jwt-input}}) is
presented this way. The presented-evidence, classification, and
mutual-exclusion rules of {{actor-inputs}}, including no fallback to
authentication context, apply to that subject token; its
actor-construction and `act` requirements do not.

**Authentication-context resolution:** The authentication-context rules
of {{actor-inputs}} apply. Because {{RFC8693}} cannot name the
authenticated client as the subject without a subject token, a client
authenticated with a JWT MUST repeat that JWT, byte for byte, as
`subject_token` with type `urn:ietf:params:oauth:token-type:jwt`: the
RFC 7523 assertion, the JWT-SVID, the WIT-SVID, or the Client
Attestation JWT itself, not an accompanying proof-of-possession JWT.
The IdP MUST reject a subject token that is not byte-identical to the
credential presented for authentication, which prevents a client from
substituting another party's assertion as the subject. Carrying one
assertion in both parameters does not violate the single-use `jti` rule
of {{client-assertion-input}}, and the Identity Binding, not the
credential, determines the Agent Principal, as in delegated
dedicated-client resolution. A client authenticated by X.509-SVID over
mutual TLS presents no JWT and has no self-acting issuance under this
profile ({{wag-gaps}}).

## Grant Claims {#wag-claims}

The WAG subject identifies the governed Agent Principal, not the
credential subject from which it was resolved, and stays the same across
the executions behind its Identity Binding ({{governance-boundary}}).
The grant is a JWT with `typ` `wag+jwt` (provisional) and the following
claims, aligned with the claim set of {{Section 5.1 of WAG}}:

| Claim | Value |
|---|---|
| `iss` | The IdP issuer identifier |
| `sub` | The Agent Principal identifier from the Identity Binding |
| `aud` | The target RAS issuer identifier |
| `client_id`, `resource`, `scope`, `cnf.jkt` | As for the ID-JAG in {{grant-issuance}} |
| `exp`, `iat`, `jti` | As for the ID-JAG, within the lifetime below |
{: title="IdP-issued WAG claims"}

The WAG MUST NOT contain `act`.

**Unambiguous context:** The IdP MUST NOT issue a WAG unless the Agent
Principal, downstream client, and tenant are unambiguous, as
{{grant-issuance}} requires for the ID-JAG.

**Lifetime:** Of the limits in {{grant-issuance}}, the configured limit
and the agent-resolution input limit apply, including the
dedicated-client exception.

**Response:** As in {{exchange-response}}, with `issued_token_type` set
to the WAG token type.

## Redemption and Access Tokens {#wag-redemption}

**Request:** The client redeems the WAG at the RAS token endpoint with
`urn:ietf:params:oauth:grant-type:jwt-bearer`, as in WAG, and the
request of {{redemption-request}}.

**Processing:** The RAS MUST:

1. **Grant:** Validate the grant under {{RFC7523}}, consistent with
   {{Section 5 of WAG}}; require `iss` to be a configured governing IdP
   for the asserted agent namespace; and reject a WAG that contains
   `act` with `invalid_grant`.
2. **Proof and client:** Apply {{grant-protection}} and client
   authentication as in {{redemption-validation}}.
3. **Correlation:** Resolve the pair (`iss`, `sub`) under
   {{agent-correlation}} to one local agent principal in the authorized
   Target Tenant. The RAS MUST have that authorized correlation before
   issuance; for governed agents this replaces the required acceptance
   of previously unseen identifiers in {{Section 7 of WAG}}.
   {{jit-correlation}} covers just-in-time correlation where resource
   policy permits it.
4. **Authority:** Validate resource, scope, and authorization details as
   in {{redemption-validation}}, and apply current RAS policy for the
   agent, client, tenant, and resource. A valid grant sets an authority
   ceiling; it does not require issuance.
5. **Output:** Issue an access token under {{access-token-response}} and
   {{access-token-protection}}, with the local agent principal as `sub`
   and no `act`. The RAS MUST NOT issue a refresh token for a WAG
   redemption; continued access obtains a new WAG under current IdP and
   RAS policy.

**Retention:** The RAS retains the correlation between the WAG's
(`iss`, `sub`) and the local principal for the life of the derived
authorization, for revocation by qualified agent ({{applied-changes}})
and audit. The token and its introspection response need not carry it;
this document defines no claim or member for it.

**Shared rules:** With the WAG as the grant, these also apply:

* {{flow-configuration}}, for client authentication and algorithms.
* {{distributed-key-use}} and {{applied-changes}}.
* {{introspection}}, without an `act` member.
* {{client-token-reuse}}, without a user in the cached context.
* {{continuing-access}} does not apply; continued access obtains a new
  WAG (step 5).

## Resource Processing {#wag-api}

The API applies {{api-processing}}, its {{resource-errors}}, and the API
rules of {{access-token-protection}} and {{introspection}} without the
actor gate: it enforces the agent's own permissions, the token's
authority constraints, the Target Tenant, and the selected protection.
A governed self-acting token has no `act`.

Separate client registrations, audiences, or issuers for the two
populations satisfy the applicability rule of {{api-processing}}. The
absence of `act` alone does not: a delegated token lacking `act` would
otherwise be accepted as self-acting.

## Errors {#wag-errors}

Token endpoint errors follow {{errors}} with these additions:

| Failure | Error |
|---|---|
| Actor-token parameters present in a self-acting exchange | `invalid_request` |
| Subject token is not byte-identical to the authentication credential in authentication-context resolution | `invalid_grant` |
| Resolved Agent Principal, but no Client Association permits self-acting issuance for the binding | `unauthorized_client`, not `actor_unauthorized`, since no actor is asserted |
| Agent not authorized for the requested RAS or resource | `invalid_target` |
| Agent not authorized for the requested authority | `invalid_scope` |
| WAG whose `sub` has no authorized correlation at the RAS | `invalid_grant` |
| Invalid WAG at redemption, including one that contains `act` | `invalid_grant` |
{: title="Self-acting error additions"}

## Profile Identifiers {#wag-profiles}

The self-acting realization uses the adoption profiles of
{{adoption-profiles}} under its own identifiers,
`urn:ietf:params:oauth:grant-profile:wag-governed-agent` and
`urn:ietf:params:oauth:grant-profile:wag-agent-federation`. Grant
protection, downgrade prevention, and discovery follow
{{grant-protection}}, {{discovery}}, and {{metadata}}. Provisioning,
disablement, and revocation apply to the same Agent Principal and local
principal as delegated access ({{status-changes}}).

# Conformance and Metadata {#conformance-metadata}

## Conformance {#scope}

This profile does not establish trust in previously unknown agent
issuers or automatically create Identity Bindings from presented
credentials.

Unless explicitly limited to bound grants or a named profile, the
requirements of this document apply to both governed adoption profiles.
Conformance claims MUST identify the supported profile by its URI
({{metadata}}), the realization, the implemented role, and supported
inputs. An implementation supports delegated access, self-acting
access, or both.

The IdP, RAS, and client MUST implement their respective requirements
in {{model}}, {{identity}}, {{authorization}}, {{metadata}},
{{security}}, and {{mandatory-input-profiles}}; in {{delegated-flow}} or
{{wag-flow}} for each supported realization; and in
{{optional-input-profiles}} for each supported optional input. Each
realization has this mandatory interoperability path:

* **Issuance:** The client and IdP MUST implement dedicated-client
  resolution using RFC 7523 `private_key_jwt` authentication
  ({{client-assertion-input}}), and for delegated access also ID Token
  subjects.
* **Redemption:** The client and RAS MUST implement `private_key_jwt` for
  redemption. DPoP support and use are REQUIRED for bound governed agent
  access; governed agent access follows {{grant-protection}}.
* **API:** The API MUST implement {{api-processing}}, with {{wag-api}}
  for self-acting access.

The inputs of {{optional-input-profiles}}, existing platform JWTs, SAML
subjects, and IdP refresh-token subjects are OPTIONAL capabilities, with
one exception: an IdP that accepts any agent-resolution input other than
dedicated-client identity MUST also support the existing platform JWT
input ({{imported-jwt-input}}), and a client that relies on a shared
client identity MUST be able to present it. Input selection follows
{{discovery}}.

ID-JAG requires support for Identity Assertions
({{Section 4.3 of ID-JAG}}); requiring ID Token subjects specifically
gives independent implementations a common subject-token format. This is
an implementation baseline, not a requirement to deploy one client per
agent: deployments MAY use mutually supported optional inputs.

Because an ID Token's audience identifies the authenticated IdP client
({{subject-token-validation}}), a dedicated deployment needs a user
authorization flow for each agent's client registration, though an
existing IdP session may avoid another login prompt. A platform
retaining its shared single sign-on (SSO) client instead uses the
existing platform JWT ({{imported-jwt-input}}) or an optional input.

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

These URIs identify RAS and client processing. IdP issuance and optional
inputs follow {{discovery}}. No URI claims a credential class,
continuation support, a particular workload-evidence protection, or
access-token protection; these are capabilities and configured minimums.

### Authorization Server Metadata {#server-metadata}

Servers MUST publish {{RFC8414}} metadata as follows:

* **RAS:** Include each supported governed profile URI, and for
  delegated access the base `urn:ietf:params:oauth:grant-profile:id-jag`,
  in `authorization_grant_profiles_supported`. The self-acting URIs use
  the same parameter, pending coordination ({{wag-gaps}}).
  * Include `urn:ietf:params:oauth:grant-type:jwt-bearer` in
    `grant_types_supported` for this profile.
* **IdP:** Advertise Token Exchange in `grant_types_supported`. For
  delegated access, advertise ID-JAG in
  `identity_chaining_requested_token_types_supported` under
  {{Section 7.1 of ID-JAG}}; for self-acting access, advertise the WAG
  token type in the same parameter, pending coordination ({{wag-gaps}}).
  * Include `private_key_jwt` in `token_endpoint_auth_methods_supported`.
  * When SPIFFE authentication is supported, include `spiffe_jwt`,
    `spiffe_wit`, or `spiffe_x509` under {{Section 4 of SPIFFE-OAUTH}}.
    Authentication metadata alone does not advertise agent-resolution
    support ({{actor-inputs}}, {{discovery}}).
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
an attacker able to authenticate as their designated client,
particularly a shared client. Binding only the resulting access token
does not prevent that redemption. Explicit acceptance policy, short
grant lifetimes, credential confidentiality, and the no-fallback rules
in {{discovery}} limit this exposure; they do not provide proof of
possession of an issuer-authorized grant key.

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
  mechanism independently. Where a mechanism retains replay state, that
  state MUST remain in effect for as long as the credential, proof, or
  grant would otherwise be accepted, including the maximum allowed skew.

A fresh proof does not renew an expired credential; an unchanged
identifier does not authorize a new proof key.

## Dedicated-Client Key Compromise

In dedicated-client resolution, compromise of the client's authentication
key permits an attacker to authenticate as the resolution source for its
bound Agent Principal. No independent workload credential is required.

For delegated access, the attacker still needs an acceptable user
subject credential and has to satisfy Client Association and delegation
authorization. For self-acting access, the key alone suffices wherever
a Client Association and Agent Authorization already permit the client.

Grant binding does not prevent this impersonation at issuance: unless
policy independently constrains the grant proof key, the attacker can
obtain a grant bound to an attacker-controlled DPoP key. The proof
protects that grant against theft; it does not establish legitimate
runtime provenance.

Runtime or workload provenance requires an agent-resolution input whose
verified claims and trusted issuance policy establish it;
dedicated-client resolution alone does not. A normalized Agent Principal
identity does not imply uniform runtime assurance. Authentication-key
revocation and binding disablement affect subsequent issuance under
{{status-changes}}.

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
({{lifecycle-gap}}). Without a signal or online check, issued tokens
remain usable until expiration; without a bound on propagation, the
remaining lifetime of existing grants, refresh authorizations, and
access tokens determines the possible continuation window. The
five-minute ID-JAG recommendation is not a global stopping guarantee.
Even after disablement is applied, cached introspection results or
offline JWTs can remain usable until their acceptance limits, and
current active state alone cannot recover a missed disable-and-reenable
transition or invalidate every old grant. Deployments benefit from
documenting their maximum disablement delay, including propagation and
cache freshness.

Administrative actions have different effects, and none is evidence
that another has occurred. The following table summarizes each effect
after the change is applied at the enforcing server; it defines no new
propagation mechanism:

| Administrative action | Effect on new authorization | Previously issued authority |
|---|---|---|
| Terminate an execution | Stops that execution; does not disable the agent or its approved relationships | Credentials and tokens remain subject to their validation and revocation rules |
| Disable one Identity Binding at the IdP | No new grant through that binding; other enabled bindings remain usable with their own Client Associations | Existing grants and RAS tokens need separate revocation or expiry |
| Remove a Client Association at the IdP | No new grant through that permission; the Identity Binding can remain valid | Existing grants and RAS tokens need separate revocation or expiry |
| Disable the Agent Principal at the IdP | No new grant for that agent, regardless of binding or client | RAS issuance and refresh stop when the change reaches and is applied by the RAS |
| Withdraw the user's delegation at the IdP | No new delegated grant for that delegation | Existing RAS authorization can continue until revocation is applied or its absolute expiration |
| Disable the local agent or user at the RAS | No new access tokens or refresh for that principal | API access stops when its actor/user policy observes the change, introspection reports inactivity, or the token expires |
{: title="Effects of administrative changes"}

The RAS requirements for applied changes are in {{applied-changes}};
the provisioning that feeds them is a deployment choice. Withdrawing a
delegation, Identity Binding, or Client Association can be propagated
to derived authorization, through grant-derived revocation in
{{AGENT-LIFECYCLE}} or an equivalent signal, only when the IdP has
retained the identifiers of the ID-JAGs it issued under that
relationship; the agent identity alone cannot identify that set.

Account-linking errors can grant access to another user's account;
{{subject-resolution}} states the checks required before authorization.
Proof of key possession does not establish account ownership, and link
removal does not revoke outstanding tokens.

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
delegated users supports audit but lets a resource domain link the
activity of one Agent Principal for different users.

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

This normative appendix defines the two inputs that {{scope}}
requires: dedicated-client identity, mandatory to implement, and the
existing platform JWT, required for shared-client support. Each
satisfies the interface contract of {{evidence}}.

## Dedicated Client Identity {#client-assertion-input}

In this explicitly configured mode, the IdP resolves the client identity
validated during client authentication to its explicitly bound Agent
Principal, without requiring a separate platform-issued credential. The
assertion authenticates the client and is not independent workload
evidence ({{dedicated-client-coordination}}). This mode does not
distinguish agents behind one shared client identity; such a client MUST
use a supported workload-identity input that distinguishes its agents
({{imported-jwt-input}}). {{client-assertion-example}} illustrates this
input.

* **Presentation:** An asymmetrically signed `client_assertion` under
  {{RFC7523}}. For `private_key_jwt`, the common method, the assertion
  issuer and subject are the client's registered identifier
  (Section 9 of {{OPENID}}); other configured asymmetric RFC 7523
  methods MAY be supported.
* **Validation:** The IdP authenticates the client under
  {{Section 3 of RFC7523}} and its configured authentication method,
  and MUST use verification keys authorized for that client and
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
  IdP MUST reject reuse in another request while the assertion remains
  acceptable; a reused assertion fails client authentication. Replay
  identifiers MUST be qualified by the validated issuer and client.
* **Retry:** For any retry of a dedicated-client exchange, including
  after a `use_dpop_nonce` challenge under {{Section 8 of RFC9449}}, the
  client MUST generate a new `client_assertion` with a fresh `jti`; for
  a nonce retry, it MUST also generate a fresh DPoP proof containing the
  supplied nonce while retaining the grant proof key. A new DPoP proof
  alone is not enough, because the IdP may already have consumed the
  previous assertion during authentication.

## Existing Platform JWT {#imported-jwt-input}

This common shared-client input accepts existing signed platform JWTs as
issued, with no new media type or reissuance; {{scope}} states when it
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
* **Validation:** The IdP MUST validate the JWT
  under {{RFC7519}}, {{RFC8725}}, and the configured credential profile.
  Keys or URLs in the JWT MUST NOT override the approved key source.
  The IdP MUST determine the effective evidence deadline from `exp`, a
  configured maximum age measured from an authenticated issuance time
  (such as `iat`), or both; when both apply, the earlier deadline
  governs. Receipt time MUST NOT substitute for issuance time. The
  deadline bounds grant expiration ({{grant-issuance}}).
* **Resolution:** The Identity Binding MUST specify an exact issuer and
  `sub` and MAY require additional string values from the JWT Claims
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
  IdP as workload evidence (**Configuration**).
* **Proof:** This profile defines no new proof mechanism. If `cnf` is
  present, the IdP MUST enforce its proof mechanism and MUST NOT give
  the credential bearer treatment when the binding is unsupported. A
  deployment accepting key-bound JWTs MUST configure their proof
  validation and any required relationship to the grant proof key.
  Bearer platform JWTs fall under {{credential-requirements}}.
* **Failure:** The IdP MUST reject evidence with `invalid_grant` if a
  required time limit cannot be evaluated or no effective evidence
  deadline can be determined.

# Optional Agent Resolution Inputs {#optional-input-profiles}

This normative appendix defines the optional inputs listed in
{{optional-inputs}}. Each satisfies the interface contract of
{{evidence}}, resolves from authentication context with actor-token
parameters omitted ({{actor-inputs}}), and requires trusted
configuration under {{configuration}}.

## SPIFFE JWT-SVID {#jwt-svid-input}

This OPTIONAL input identifies workloads independently of the OAuth
client identifier, including multiple agents behind a shared client.

* **Presentation:** Client authentication by `client_assertion` with
  `client_assertion_type`
  `urn:ietf:params:oauth:client-assertion-type:jwt-spiffe`.
* **Validation:** The IdP MUST apply {{Section 3.1 of SPIFFE-OAUTH}},
  including the assertion type, and {{Section 5 of SPIFFE-OAUTH}} and
  {{Section 6 of SPIFFE-OAUTH}} for trust establishment and key
  distribution, before resolving the agent, and verify the signature
  with keys authorized for the SPIFFE ID's trust domain. An optional
  `iss` MUST NOT select another trust domain or key authority.
* **Resolution:** The IdP MUST resolve the exact SPIFFE ID in the
  validated `sub` under {{identity-binding}}. The SPIFFE ID's
  association with the authenticated client is an authentication check,
  not an Identity Binding or Client Association.
* **Proof:** A JWT-SVID is bearer evidence: DPoP, when used, binds the
  issued grant to the grant proof key, not the JWT-SVID to its
  presenter. A policy requiring issuer-bound presenter proof MUST reject
  this input rather than treat DPoP as that proof
  ({{credential-requirements}}).

## Client Attestation {#agent-evidence}

This OPTIONAL input maps the attested OAuth client identity explicitly
to one Agent Principal. It relies on a trusted attester's endorsement of
the client identity and confirmation key, not a registered client key,
and establishes runtime or workload provenance only as far as verified
attestation claims and the attester's trusted issuance policy support.
It does not distinguish agents behind a shared client; those agents need
distinct workload evidence, such as a JWT-SVID or platform JWT.
Instance-based resolution and attester endorsement are deferred
({{excluded-compositions}}).

* **Presentation:** Client authentication with the configured {{ATTEST}}
  method.
* **Validation:** The IdP MUST validate the attestation and proof under
  {{ATTEST}} before resolving the agent, and MUST identify the attester
  unambiguously from the trusted verification key and configured
  attester-to-client associations. An `iss`, when present, MUST match
  that attester.
* **Resolution:** The IdP MUST resolve the trusted attester and the
  validated `sub` through an approved Identity Binding
  ({{identity-binding}}).
* **Proof:** With `attest_jwt_client_auth`, any grant proof key MUST
  match the attestation's confirmation key, narrowing the allowance in
  {{Section 5.2 of ATTEST}} for a separate DPoP key. With
  `attest_jwt_client_auth_dpop`, one DPoP proof serves both roles. Key
  retention follows {{resolution-key-lifecycle}}.

## SPIFFE WIT-SVID and X.509-SVID Resolution {#spiffe-input}

These OPTIONAL inputs resolve the SPIFFE ID validated during OAuth
client authentication for this token request, in the SVID class that the
client and IdP configure. General non-SPIFFE Workload Identity Token
(WIT) and Workload Identity Certificate (WIC) inputs of {{WIT}} are
excluded ({{excluded-compositions}}). One shared SPIFFE ID cannot
distinguish independently governed agents. Either input proves control
of a credential-bound key; assurance about a particular runtime or
execution depends on the credential authority's issuance rules and
identity granularity. {{svid-context-example}} illustrates both inputs.

### WIT-SVID

* **Presentation:** The WIT-SVID in `OAuth-Client-Attestation`, with its
  proof in `OAuth-Client-Attestation-PoP`.
* **Validation:** The IdP MUST apply {{Section 3.3 of SPIFFE-OAUTH}} and
  {{WIT}}, including their client-identifier association, trust,
  validity, and proof requirements; require `typ=wit+jwt`; and validate
  possession of the key in `cnf.jwk` through the Client Attestation PoP
  JWT. A WIT-SVID MUST NOT be accepted as bearer evidence, and its
  optional `iss` MUST NOT select a different trust domain or key
  authority.
* **Resolution:** The IdP MUST resolve the approved trust domain and
  exact SPIFFE ID in the validated `sub` through {{identity-binding}}.
* **Proof:** When DPoP is used at issuance, its key MUST match the
  WIT-SVID's `cnf.jwk`; the IdP MUST compare their JWK thumbprints as
  used in {{RFC9449}} and MUST reject a mismatch with `invalid_grant`.
  This carries the WIT-endorsed key into the grant binding; the Client
  Attestation PoP JWT remains required. Key retention follows
  {{resolution-key-lifecycle}}.

### X.509-SVID

* **Presentation:** The client certificate on the mutual-TLS connection
  carrying the token request.
* **Validation:** The IdP MUST apply {{Section 3.2 of SPIFFE-OAUTH}} and
  {{RFC8705}}, including their client-identifier association, trust,
  validity, and proof requirements, to the certificate and proof
  established by mutual TLS for this request. A certificate supplied
  only in a request parameter or an untrusted forwarding header MUST NOT
  establish the workload identity, and the request then fails client
  authentication. TLS termination follows
  {{Section 6.5 of RFC8705}}.
* **Resolution:** The IdP MUST resolve the approved trust domain and
  exact SPIFFE ID in the certificate's URI Subject Alternative Name
  through {{identity-binding}}.
* **Proof:** A DPoP grant proof key, when required, is proven on the
  same token request and MAY differ from the certificate key, because
  mutual TLS can terminate separately from the component generating DPoP
  proofs. The certificate does not endorse the DPoP key; the
  authenticated request associates it with this issuance, and the grant
  uses `cnf.jkt`, not certificate confirmation.

## Resolution-Key Lifecycle {#resolution-key-lifecycle}

When the resolution key is also the grant proof key, as for WIT-SVID or
Client Attestation when DPoP is used, replacing it does not rebind an
outstanding grant, access token, or refresh token. Continued use
requires retaining the corresponding proof key; otherwise, the client
obtains a new grant with the replacement key and new RAS authorization.
Any subject-credential binding still applies and may require a new
subject credential. Key migration is deferred ({{key-transition-gap}}).

# Dependencies and Deferred Work {#upstream-gaps}

This informative appendix records dependencies and deferred work,
assessed against WAG-00, ID-JAG-04, ICA-02, Actor Profile-00, SPIFFE
OAuth-02, ATTEST-11, WIT-02, CIMD-02, and the current drafts of Client
Instance Identification and Client Attester Endorsement.

## Upstream Dependencies

| Specification | What this profile needs | Consequence until resolved |
|---|---|---|
| WAG | Type registration; alignment on protection, linking, and subject presentation ({{wag-gaps}}) | Provisional type values |
| ID-JAG | `jwt-bearer` in the bound-grant example; confirmation errors distinct from RFC 9449 proof errors ({{bound-grant-coordination}}) | Confirmation checks apply to `jwt-bearer` here |
| Actor Profile | A reusable principal-resolution extension point ({{dedicated-client-coordination}}) | Local mapping ({{actor-construction}}) |
{: title="Upstream dependencies"}

### WAG {#wag-gaps}

{{wag-flow}} defines the IdP issuance that {{Section 5 of WAG}}
anticipates. Open items are registration of the WAG token type and
`wag+jwt` and their advertisement with the self-acting profile URIs
({{server-metadata}}), DPoP binding ({{grant-protection}}), authorized
correlation in place of the acceptance of unseen identifiers required by
{{Section 7 of WAG}}, a token exchange in which the authenticated client
is the subject without a subject token ({{wag-request}}), which would
also give X.509-SVID authentication a self-acting path, and
self-acting Client Associations ({{AGENT-MANAGEMENT}}).

### ID-JAG Bound Grants {#bound-grant-coordination}

{{Section 4.4 of ID-JAG}} requires `jwt-bearer`, but its bound-grant
example uses `jwt-dpop`. This profile applies explicit confirmation
processing to `jwt-bearer` ({{redemption}}) and takes no dependency on
JWT DPoP Grant.

### Resolution from Authentication Context {#dedicated-client-coordination}

Delegated issuance here resolves the actor from authentication context
without `actor_token` ({{actor-inputs}}). ID-JAG leaves actor processing
to extensions ({{Section 9.7 of ID-JAG}}), Appendix A.1 of {{RFC8693}}
reads a subject-only request as impersonation, and
{{Section 6.3.1 of ACTOR-PROFILE}} permits authentication-context reuse
only with the same assertion as `actor_token`. Generic Token Exchange or
Actor Profile support therefore
does not advertise it.

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
| Asynchronous approval with {{AROP}} | External approval follows {{external-approval}} and {{authorization-lifetime}} |
| Continuation with {{ICA}} | Renewal follows {{continuing-access}} |
| General WIMSE WIT/WIC inputs | Only the SPIFFE forms in {{spiffe-input}} are defined |
| Instance-based resolution or instance context under {{INSTANCE}} | Workload evidence resolves the agent without a per-instance protocol; shared workload identity does not distinguish replicas {{SPIFFE-CONCEPTS}} |
| Attester endorsement under {{ATTESTER-ENDORSEMENT}} | Attester trust is configured ({{agent-evidence}}) |
| Mutual-TLS-bound ID-JAG | Bound grants use DPoP; mutual TLS can protect access tokens ({{access-token-protection}}) |
| Authorization details without scope | Scope is required; the scope-free mode of {{RFC9396}} is not defined |
{: title="Excluded compositions"}

## Operational Dependencies {#operational-guidance}

Provisioning, account linking, and lifecycle propagation are deployment
choices. Useful controls include authenticated link changes,
just-in-time accounts and correlations authorized by issuer and tenant
({{jit-correlation}}), no silent merges or reactivation of disabled
accounts, and issuer and tenant context in SCIM `externalId`
{{RFC7643}}. SCIM {{RFC7644}} and {{SCIM-AGENT}} are building blocks,
not a lifecycle propagation contract.

### Provisioning and Disablement {#lifecycle-gap}

{{AGENT-LIFECYCLE}} profiles SCIM, optional Shared Signals, and applied
changes, including missed-event limits. It is not required for
conformance; {{agent-correlation}} and {{status-changes}} state this
document's guarantees.

# Walkthrough: Dedicated Client {#walkthrough}

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
introspection, disablement, and reactivation; this document alone does
not imply those checks.

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

`CLIENT_ASSERTION` denotes the signed compact JWT, presented only in
`client_assertion` under {{client-assertion-input}}. The Identity
Binding resolves the authenticated client to `agent-42`; no actor-token
parameters are sent, and the assertion supplies no independent workload
identity. The assertion expires after 60 seconds but does not cap the
grant's 300-second lifetime; Alice's ID Token remains valid for at least
that period.

## Exchange Request and Response

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

## Redemption Request and Response {#redemption-example}

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
unbound grant can instead obtain a DPoP-bound access token by presenting
a valid proof at redemption ({{grant-protection}}).

## Renewal and Rejection Examples

The redemption response contains no refresh token; after the access
token expires, the client obtains a new ID-JAG ({{continuing-access}}).

Each rejection below changes one condition in the walkthrough; all
other credentials, proofs, and policy checks succeed. Token endpoint
errors follow {{errors}}; API errors follow {{resource-errors}}.

| Changed condition | Rejecting party | Result |
|---|---|---|
| After a nonce challenge, the retry uses a fresh DPoP proof but reuses the consumed `analysis-auth-1` assertion | IdP | HTTP 400, `invalid_client`; regenerate `client_assertion` |
| Client assertion remains valid, but its Identity Binding is disabled | IdP | HTTP 400, `invalid_grant`; successful authentication does not resolve the agent |
| Client assertion and Identity Binding remain valid, but the Client Association for `analysis-client` is disabled | IdP | HTTP 400, `actor_unauthorized`; no ID-JAG |
| Bound governed agent access is required, but the grant has no `cnf` | RAS | HTTP 400, `invalid_grant`; no fallback to governed agent access |
| The grant has `cnf.jkt` and redemption omits the proof, although the resource accepts bearer access tokens or policy permits unbound grants | RAS | HTTP 400, `invalid_grant`; the grant binding is enforced regardless of access-token protection |
| The client presents the access token for an operation in another tenant where Alice and the agent also have permissions, with a fresh valid proof for that request URI | API | HTTP 401, `invalid_token`; no operation performed |
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
  "iat": 1789646580,
  "exp": 1789646880,
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
{{walkthrough}}; the message sequence is unchanged. The resulting actor
is always the IdP issuer and `agent-42`. Only the platform JWT variant
sends actor-token parameters.

| Variant | Authentication and presentation | Identity resolved |
|---|---|---|
| Shared client with JWT-SVID | IdP `client_id` `platform-sso`; the JWT-SVID is the `client_assertion`, with `client_assertion_type` `jwt-spiffe` | Approved trust domain and exact SPIFFE ID in `sub` ({{jwt-svid-input}}) |
| WIT-SVID | `spiffe_wit`: WIT-SVID in `OAuth-Client-Attestation` with a fresh PoP header signed by its key; `client_id` is the SPIFFE ID | Exact SPIFFE ID in the validated `sub` ({{spiffe-input}}) |
| X.509-SVID | `spiffe_x509`: mutual-TLS authentication with the X.509-SVID; `client_id` is the SPIFFE ID | Exact URI Subject Alternative Name ({{spiffe-input}}) |
| Platform JWT (AWS STS) | IdP `client_id` `platform-sso` with a separately configured authentication method; the STS JWT is the `actor_token` with type `jwt` | Exact issuer, `sub`, and selector ({{imported-jwt-input}}) |
{: title="Input variants relative to the dedicated-client walkthrough"}

In the bound profile, K signs the issuance DPoP proof, except that the
WIT-SVID variant uses the WIT-SVID key; the X.509-SVID variant's DPoP
key may differ from its TLS key. The input bounds the grant lifetime
under {{grant-issuance}}. Each variant needs a Client Association for
its authenticated client, which is `platform-sso` for the JWT-SVID and
platform JWT variants ({{identity-binding}}). The dedicated-client
rejection examples apply to each binding, except that replay rules
follow the input specification.

## Shared Platform Client with SPIFFE {#shared-client-example}

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

## WIT-SVID and X.509-SVID {#svid-context-example}

Both variants resolve the workload authenticated on the exchange request
through an exact Identity Binding from
`spiffe://platform.example/agents/analysis` to `agent-42`. The user ID
Token is issued to that authenticated client, not reused from
`analysis-client`. The WIT-SVID carries the SPIFFE ID in `sub` and the
workload public key in `cnf.jwk`; for X.509-SVID, mutual-TLS
authentication replaces the two attestation headers. An authoritative
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
IAM principal, not an individual agent. Distinct Agent Principals then
need distinct credential identities or additional trusted selectors; a
caller-supplied agent name does not provide that distinction. This
variant covers evidence resolution, not a product's end-to-end
conformance. User-access-token OBO composition remains outside the scope
of this document ({{access-token-subject-gap}}).

# Document History

RFC Editor: Remove this section before publication.

* Initial version.

# Acknowledgments
{:numbered="false"}

The author thanks Jeff Malnick for review and discussion of this
profile.
