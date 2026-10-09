<!-- regenerate: off (set to off if you edit this file) -->

# Governed Agent Profiles

This is the working area for four related Internet-Drafts on governing
agents across platform, identity-provider, and resource-domain boundaries.

## The problem

Enterprises run agents on platforms they do not operate, and they need to
recognize and govern each agent across changes in platforms, workloads, and
credentials. These drafts let an identity provider resolve those execution
identities to an Agent Principal that resource domains can recognize,
authorize, and audit. The principal can remain stable while its execution
environment and its permissions change. Its identifier can also be the same
as the execution identity's; what the drafts establish is which identity is
authoritative for governance.

The common workaround is a shared OAuth client per platform integration.
Every agent behind it looks identical to the resource server, so attribution
is lost and revocation becomes all or nothing.

The pieces needed to fix that exist separately and do not yet compose.
OAuth 2.0 Token Exchange defines `act` but leaves the actor's meaning to
profiles. ID-JAG brokers cross-application access through the IdP both sides
already trust for SSO, and leaves actor validation, authorization, and
representation to extensions. Attestation-based and SPIFFE client
authentication establish which OAuth client is calling, not which agent a
shared client is acting for.

## The drafts

| Draft | What it covers |
|---|---|
| [OAuth 2.0 Profile for Governed Agent Federation](#oauth-20-profile-for-governed-agent-federation) | Resolves client and workload identities to a stable Agent Principal and carries it into a resource domain |
| [Agent Resolution Input Profiles for Governed Agent Federation](#agent-resolution-input-profiles-for-governed-agent-federation) | Optional SPIFFE and Client Attestation inputs, including managed-installation resolution |
| [SCIM Profile for Governed Agent Federation Management](#scim-profile-for-governed-agent-federation-management) | Platform-to-IdP management of Agent Principals, Identity Bindings, and Client Associations |
| [Governed Agent Lifecycle Profile for SCIM and OAuth](#governed-agent-lifecycle-profile-for-scim-and-oauth) | IdP-to-resource-domain provisioning, administrative disablement, and session revocation |
| [SCIM Profile for OAuth 2.0 Client Management](#scim-profile-for-oauth-20-client-management) | Generic SCIM management of OAuth client registrations, including CIMD clients |

```
 Agent platform
      |
      |  SCIM Governed Agent Federation Management
      v
 +----------------------------------+
 | Governing IdP                    |
 |   Agent Principal                |
 |   Identity Bindings              |
 |   Client Associations            |
 |   OAuth clients                  |
 |   Administrative state           |
 +----------------------------------+
      |                        |
      | Governed Agent         | Governed Agent Lifecycle
      | Federation (OAuth)     | (SCIM and signals)
      v                        v
 +----------------------------------+
 | Resource domain                  |
 |   Local agent principal          |
 |   Authorization sessions         |
 |   Local Suspension               |
 +----------------------------------+
```

Management establishes the relationships at the IdP, federation exercises
them to obtain authorization, and lifecycle carries the principal's
administrative state into the resource domain and revokes what depends on
it. SCIM OAuth Client Management supplies the OAuth client registrations
that bindings and associations reference.

## OAuth 2.0 Profile for Governed Agent Federation

The core draft defines how an IdP resolves dedicated OAuth client identities
or independently validated workload identities to stable Agent Principals,
and how two peer grants carry that principal to a resource domain:

| Acting relationship | Grant | Principal representation |
|---|---|---|
| Acting for a user | ID-JAG | User as subject; agent as actor |
| Acting for itself | WAG | Agent as subject |

The governing principle is that the Agent Principal is the authorization
identity. Client and workload identities are authenticated inputs that
resolve to it; they do not replace it downstream. Three consequences follow:

* Governed identity is independent of execution identity. Platforms,
  workload credentials, and OAuth clients can change without changing the
  Agent Principal.
* Resolving an identity does not authorize its use. An Identity Binding says
  which agent a credential represents; a separate Client Association says
  whether a client may exercise it.
* Actor attribution is not delegation authority. An agent named in `act`
  acts for a user only under the IdP's delegation decision and the
  resource's actor gate.

The scope is deliberately narrow: an agent governed by the IdP that issues
the grant, federated into a resource domain. Identity continuity across a
chain of IdPs or brokers is out of scope.

Each grant has its own mandatory path, and an implementation claims one or
both. Delegated access uses an ID Token issued for the dedicated client,
`private_key_jwt` client authentication, a governed ID-JAG, and RFC 7523
`jwt-bearer` redemption. Self-acting access uses the same dedicated-client
resolution and redemption with a WAG naming the Agent Principal as subject.
The WAG token type and JWT type are provisional values until WAG registers
them. SPIFFE JWT-SVID, WIT-SVID, X.509-SVID, and Client Attestation inputs
are optional; shared platforms use the existing platform JWT input to
distinguish the agents behind their SSO client. No new credential format or
per-replica registration is required.

Two governed profiles support incremental adoption. Bound governed agent
access requires DPoP at issuance and redemption; governed agent access
permits unbound grants only under explicit policy. Access-token protection
is a separate choice: DPoP, mutual TLS, or explicitly permitted bearer use.
For delegated access, the API enforces user authority and the actor gate.
For self-acting access, it enforces the agent's own authority.

The appendices walk through the dedicated-client flow and a shared-client
SPIFFE variant. Continuing access uses eligible subject credentials for new
grants or policy-permitted RAS refresh within retained authorization and
lifetime limits. Existing SSO refresh tokens do not automatically authorize
downstream resources. Client instances and attester endorsements compose
with the governed agent: an instance resolves an agent only through an
exact, approved installation binding, and an endorsement never creates a
binding. Key transition and Identity Continuation Assertion compositions
remain deferred.

* [Editor's Copy](https://mcguinness.github.io/governed-agent-profiles/#go.draft-mcguinness-oauth-governed-agent-federation.html)
* [Datatracker Page](https://datatracker.ietf.org/doc/draft-mcguinness-oauth-governed-agent-federation)
* [Individual Draft](https://datatracker.ietf.org/doc/html/draft-mcguinness-oauth-governed-agent-federation)
* [Compare Editor's Copy to Individual Draft](https://mcguinness.github.io/governed-agent-profiles/#go.draft-mcguinness-oauth-governed-agent-federation.diff)

## Agent Resolution Input Profiles for Governed Agent Federation

The federation draft defines the agent-resolution input contract and two
inputs: dedicated-client identity, which every implementation supports, and
the existing platform JWT for shared clients. This companion defines further
inputs that satisfy the same contract: SPIFFE JWT-SVIDs, WIT-SVIDs, and
X.509-SVIDs, and Client Attestation, including resolution of a managed
installation behind a shared client by its client instance identifier. An
implementation that claims none of these inputs needs only the federation
draft.

* [Editor's Copy](https://mcguinness.github.io/governed-agent-profiles/#go.draft-mcguinness-oauth-governed-agent-inputs.html)

## SCIM Profile for Governed Agent Federation Management

The SCIM management profile provisions Agent Principals and administers
Identity Bindings and Client Associations at the IdP. Because those
relationships decide which clients and workloads can obtain authorization as
an agent, administering them is authorization management: permission to
create an agent does not imply permission to bind it, and permission to
disable a relationship does not imply permission to enable it.

The profile reuses SCIM operations, adds a small Agent identity extension and
two relationship resources, and references OAuthClient registrations from the
generic profile. Dedicated-client bindings reference OAuthClient and
administer identity and client-use permission together. Shared-client
deployments retain external workload bindings and separate Client
Associations. Both support CIMD clients without copying their metadata.
Credential-authority trust, client registration permission, user delegation,
and downstream revocation remain separate.

* [SCIM management profile source](draft-mcguinness-scim-agent-federation.md)
* [SCIM management editor's copy](https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-agent-federation.html)

## Governed Agent Lifecycle Profile for SCIM and OAuth

The lifecycle profile provisions issuer-qualified Agent Principals into the
resource domain with SCIM and applies administrative disablement at the RAS.
The RAS needs that correlation before it accepts a grant. The core draft lets
resource policy create it just in time from a validated grant, off by default
and enabled per issuer and tenant; that serves resource domains without SCIM
and orchestration in which the first grant arrives before provisioning. The
lifecycle draft adds SCIM exposure and reconciliation of such records, so
later provisioning updates the same principal. Re-enablement permits new
authorization decisions without restoring revoked sessions.

Disablement is one of several revocation boundaries. Disabling the principal
or a binding, withdrawing a client association or a delegation, revoking a
workload credential, and revoking one grant each reach different
authorization. A Local Suspension lets the resource domain deny an agent
regardless of upstream state, and upstream activation cannot clear it.

The lifecycle draft also profiles existing SCIM Events and optional CAEP
revocation. Provisioning and feed events trigger authoritative reconciliation;
CAEP can revoke all authorization derived from an issuer-qualified ID-JAG
`jti`. No new event type, eligibility lease, or authorization cutoff is
defined. Current state cannot recover a missed disable-and-reenable cycle.
API enforcement still depends on introspection, caching, and token expiry.

* [Lifecycle profile source](draft-mcguinness-oauth-governed-agent-lifecycle.md)
* [Lifecycle profile editor's copy](https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html)

## SCIM Profile for OAuth 2.0 Client Management

The generic OAuthClient profile develops the SCIM registration approach first
proposed by Phil Hunt, Morteza Ansari, and Anthony Nadalin. It maps current
OAuth registration metadata into SCIM 2.0 and defines management of the same
registration through SCIM and RFC 7591/7592 interfaces. CIMD clients retain
their URL identifiers and document-owned metadata; SCIM manages local
admission and references used by agent associations. Client registration,
agent identity, and permission to use that identity remain separate.

* [OAuthClient profile source](draft-mcguinness-scim-oauth-client-management.md)
* [OAuthClient editor's copy](https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-oauth-client-management.html)

## Platform-hosted agents

A platform such as a data or application platform can host agents for a
customer that use only the platform's own tools and resources. The IdP issues
those agents nothing, and the platform must keep running when the IdP is
unavailable. The enterprise still wants them in one inventory, under one
governance decision, and visible in its monitoring. The drafts support this
without putting the IdP in the platform's runtime path:

* **Register, don't federate.** The platform's connector registers each hosted
  agent at the IdP as an Agent with no Identity Binding or Client Association.
  The agent is visible and governed but cannot obtain an IdP grant.
* **Split authority.** The platform owns the agent's existence, description,
  and deletion. The IdP owns the governance decision, `active`, and the
  connector cannot re-enable an agent the IdP disabled.
* **Apply governance locally.** The platform is the Receiver for its own
  agents. When the IdP disables one, the platform denies new authorization and
  revokes the agent's existing authorization in its own system. Its own
  suspension is a Local Suspension the IdP cannot clear.
* **Signal both ways.** The platform sends WISE credential and posture events
  and CAEP session events about its agents to the IdP, and the IdP can send
  CAEP risk changes back. Events inform policy; they do not change
  administrative state.
* **One correlation key.** The issuer-qualified Agent Principal identifier
  appears in SCIM, in events, and in the platform's audit records and
  telemetry, next to the platform's own identifier. Logs, observability, and
  posture tools join on it; the drafts define no log format.
* **Federate later, same principal.** When the agent needs a resource beyond
  the platform, an administrator adds an Identity Binding and Client
    Association to the same Agent. Its identifier and governance history carry
  over.

The lifecycle draft's
[platform-hosted walkthrough](https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#platform-example)
follows one agent from registration through risk signals, disablement,
re-enablement, third-party access, and retirement.


## Beyond these drafts

Identity, authority, and approved work have separate owners, checks, and
lifetimes. These drafts define agent federation, management, and lifecycle
controls. This section shows how those controls relate to resource
authorization, approval workflows, and mission-bound authorization. Some of
those protocol compositions remain undefined:

* The Federation draft lets an API delegate evaluation to a policy decision
  service, which must keep the user, the issuer-qualified Agent Principal, and
  the OAuth client distinct. It names AuthZEN as an optional interface but
  defines no AuthZEN message mapping.
* The Federation draft lists asynchronous approval with AROP as an excluded
  composition. Approval that completes as a token is not yet composed with
  governed ID-JAG issuance.

| Concern | Question | Responsibility | Specifications |
|---|---|---|---|
| Identity | Which governed agent is acting? | The IdP resolves the Agent Principal; the resource domain correlates it locally. | These drafts |
| Authority | What may it do, and for whom? | The IdP authorizes the grant; the resource domain decides within its limits. | These drafts; AuthZEN and COAZ for per-action decisions; ARAP and AROP for requestable denials |
| Work | Does approved work still justify this action? | Mission-bound authorization supplies and evaluates work context. | [Mission-Bound Authorization](https://github.com/mcguinness/mission-bound-authorization) |

Each concern ends separately. Disabling an Identity Binding stops new grants
through that binding. Disabling the Agent Principal stops new grants for the
agent and, once the resource domain applies it, revokes the agent's sessions
there. Otherwise, tokens already issued end only by revocation or expiry.
Revoking a grant or session ends the authority derived from it. Ending a
Mission denies actions at every boundary that checks work state. A Local
Suspension denies the agent in one resource domain regardless of upstream
state.

### Principles

* **Execution identity is evidence; governed identity is the principal.**
  Platforms mint execution identities. The enterprise governs the principal,
  and an Identity Binding connects the two, so an agent keeps its identity
  when it moves between platforms or rotates credentials.
* **Every concern has an owner, and none stands in for another.** The IdP
  owns identity, the resource domain owns resource authority, and the Mission
  control point owns work. Being known is not being authorized, and being
  authorized is not being approved for this work.
* **Owners, not a single control plane.** Each boundary keeps its own
  decision: the RAS decides anew within the grant, and a Local Suspension
  cannot be cleared from upstream.
* **Facts cross boundaries only by contract.** A contract states what is
  preserved, what is translated, and what is decided anew. Traceable
  delegation is attribution, not authority.

The treatment of each boundary follows
[Continuity Is Not One Thing](https://notes.karlmcguinness.com/notes/continuity-is-not-one-thing/).
Request provenance through intermediaries, behavioral monitoring, anomaly
detection, and telemetry are outside this architecture.

### The AuthZEN profiles

The AuthZEN profiles are developed in the OpenID AuthZEN working group:

* [AuthZEN Authorization API 1.0](https://openid.net/specs/authorization-api-1_0.html):
  a policy enforcement point asks a policy decision point for an access
  decision about a subject, action, resource, and context.
* [COAZ](https://openid.github.io/authzen/authzen-coaz-framework-1_0.html)
  (Compatible with OpenID AuthZEN): a protocol-neutral framework that maps an
  operation's inputs into an AuthZEN request.
  [COAZ-MCP](https://openid.github.io/authzen/authzen-coaz-mcp-binding-1_0.html)
  is its binding for the Model Context Protocol.
* [ARAP](https://openid.github.io/authzen/authzen-access-request-approval-profile-1_0.html)
  (AuthZEN Access Request and Approval Profile): after a requestable denial,
  the enforcement point submits an access request, tracks it as an
  asynchronous task, and re-evaluates after approval. The denial stands until
  then.
* [AROP](https://github.com/openid/authzen/blob/main/profiles/authzen-access-request-oauth/authzen-access-request-oauth-profile-1_0.md)
  (AuthZEN Access Request OAuth Profile): binds ARAP to OAuth so that an
  approved request completes as an issued access token, using the OAuth
  Deferred Token Response, CIBA, or the Transaction Authorization Challenge.

## Contributing

See the
[guidelines for contributions](https://github.com/mcguinness/governed-agent-profiles/blob/main/CONTRIBUTING.md).

The contributing file also has tips on how to make contributions, if you
don't already know how to do that.

## Command Line Usage

Formatted text and HTML versions of all drafts can be built using `make`.

```sh
$ make
```

Command line usage requires that you have the necessary software installed.  See
[the instructions](https://github.com/martinthomson/i-d-template/blob/main/doc/SETUP.md).
