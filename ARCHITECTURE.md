# Governed Agent Profiles: Architecture Overview

This overview is non-normative. It explains the problem the governed
agent profiles address, the principles behind them, and how the six
drafts fit together. The drafts define every requirement, and they
govern wherever this overview differs from them. For message-level
flows, what each role builds, and deployment configuration, see the
[implementer's guide](IMPLEMENTERS-GUIDE.md).

* [The problem](#the-problem)
* [Principles](#principles)
* [Architecture](#architecture)
* [How the drafts fit](#how-the-drafts-fit)
* [Continuation through gateways](#continuation-through-gateways)
* [Changes and revocation](#changes-and-revocation)
* [Platform-hosted agents](#platform-hosted-agents)
* [Beyond these drafts](#beyond-these-drafts)

## The problem

Enterprises run agents on platforms they do not operate. Each platform
issues its own identity for the workload it runs, and that identity is
not the principal the enterprise governs. The enterprise needs to
recognize, authorize, and audit each agent as one principal across
changes in platforms, workloads, and credentials.

The common workaround is one shared OAuth client per platform
integration. Every agent behind it looks identical to the resource
server, so actions cannot be attributed and revocation becomes all or
nothing.

The pieces needed to fix that exist separately and do not yet compose:

* OAuth 2.0 Token Exchange defines `act` but leaves the actor's meaning
  to profiles.
* The Identity Assertion JWT Authorization Grant (ID-JAG) brokers
  cross-application access through the identity provider (IdP) both
  sides already trust for single sign-on, and leaves actor validation,
  authorization, and representation to extensions.
* Attestation-based and SPIFFE client authentication establish which
  OAuth client is calling, not which agent a shared client is acting
  for.

## Principles

* **Execution identity is evidence; governed identity is the
  principal.** Platforms mint execution identities. The enterprise
  governs an Agent Principal in the IdP's namespace, and an Identity
  Binding connects the two, so an agent keeps its identity when it
  moves between platforms or rotates credentials. The principal's
  identifier may reuse the execution identity's; what matters is which
  identity is authoritative for governance.
* **Resolving an identity does not authorize its use.** An Identity
  Binding says which agent a credential represents. A separate Client
  Association says whether a client may exercise that agent.
* **Attribution is not delegation authority.** An agent named in `act`
  acts for a user only under the IdP's delegation decision and the
  resource domain's actor gate.
* **Every concern has an owner, and none stands in for another.** The
  IdP owns identity, the resource domain owns resource authority, and a
  mission control point owns approved work. Being known is not being
  authorized, and being authorized is not being approved for this work.
* **Owners, not a single control plane.** Each boundary keeps its own
  decision: the resource authorization server (RAS) decides anew within
  the grant, and a Local Suspension in a resource domain cannot be
  cleared from upstream.
* **Facts cross boundaries only by contract.** A contract states what is
  preserved, what is translated, and what is decided anew.

The treatment of each boundary follows
[Continuity Is Not One Thing](https://notes.karlmcguinness.com/notes/continuity-is-not-one-thing/).

## Architecture

### Parties

| Party | Role |
|---|---|
| Agent platform | Runs agents. Implements the OAuth client that obtains access for them, and a SCIM connector that registers them at the IdP |
| Credential authority | Issues the workload evidence the IdP can resolve: SPIFFE, a client attester, or the platform's own JWTs |
| Governing IdP | Holds each Agent Principal and the relationships that govern it, and issues grants naming it |
| Resource domain | Its RAS redeems grants and issues access tokens; its API enforces them. It correlates the agent with a local principal |
| Gateway | An API that continues an agent's request to a resource in another domain |

### How they connect

```mermaid
flowchart LR
  authority["Credential authority<br/>SPIFFE, client attester,<br/>platform JWT issuer"]
  subgraph platform["Agent platform"]
    connector["SCIM connector"]
    client["OAuth client<br/>for one or more agents"]
  end
  subgraph idp["Governing IdP"]
    principal["Agent Principal<br/>Identity Bindings, Client Associations,<br/>authorizations"]
  end
  subgraph domainA["Resource domain"]
    rasA["RAS"]
    gateway["API or gateway"]
  end
  subgraph domainB["Further resource domain"]
    rasB["RAS"]
    apiB["API"]
  end
  connector -->|"register agents and relationships"| principal
  authority -->|"workload evidence"| client
  client -->|"token exchange"| principal
  principal -->|"ID-JAG or WAG"| client
  client -->|"redeem grant"| rasA
  client -->|"call with access token"| gateway
  principal -->|"provision, disable, revoke"| rasA
  gateway -->|"continuation exchange"| principal
  gateway -->|"redeem onward grant"| rasB
  gateway -->|"call"| apiB
```

| Connection | Defined in |
|---|---|
| Register agents and relationships | SCIM Profile for Governed Agent Federation Management, with OAuth clients from the SCIM Profile for OAuth 2.0 Client Management |
| Workload evidence | OAuth 2.0 Profile for Governed Agent Federation (dedicated client, platform JWT); Agent Resolution Input Profiles (SPIFFE, Client Attestation) |
| Token exchange, grant, redemption, call | OAuth 2.0 Profile for Governed Agent Federation |
| Provision, disable, revoke | Governed Agent Lifecycle Profile for SCIM and OAuth |
| Continuation exchange, onward grant | Identity Continuation Profile for Governed Agent Federation |

### One identity, two acting relationships

The IdP resolves the client or workload identity to the Agent Principal
and carries that principal in one of two peer grants. An implementation
claims one or both.

| Acting relationship | Grant | Representation |
|---|---|---|
| The agent acts for a user | ID-JAG | User as subject; agent as actor in `act` |
| The agent acts for itself | Workload Authorization Grant (WAG) | Agent as subject |

```
Platform identity:  https://platform.example/  workload-7
                            |  Identity Binding at the IdP
                            v
Agent Principal:    https://idp.example/       agent-42

Delegated ID-JAG (excerpt):
  "sub": "alice",
  "act": {"iss": "https://idp.example/", "sub": "agent-42"}

Self-acting WAG (excerpt):
  "iss": "https://idp.example/", "sub": "agent-42"
```

### The relationships the IdP holds

Each relationship answers one question, and none implies another:

| Relationship | Question | Defined in |
|---|---|---|
| Identity Binding | Which governed agent does this credential identify? | Federation profile; administered with SCIM management |
| Client Association | May this OAuth client use that agent's identity? | Federation profile; administered with SCIM management |
| Delegation Authorization | May the agent act for this user, with what authority? | Federation profile |
| Agent Authorization | What may the agent access on its own behalf? | Federation profile |
| Continuation Association | May this gateway continue the agent's chains? | Continuation profile |

In the resource domain, the RAS correlates the agent with its local
principal by the exact (IdP issuer, agent identifier) pair. For
delegated access, the RAS and API also enforce the actor gate: may this
agent act for this user here?

## How the drafts fit

| Draft | Working group | What it defines |
|---|---|---|
| [OAuth 2.0 Profile for Governed Agent Federation][core] | OAuth | Resolution of client and workload identities to an Agent Principal, and the two grants that carry it into a resource domain |
| [Agent Resolution Input Profiles][inputs] | OAuth | Optional SPIFFE and Client Attestation inputs, including managed installations behind a shared client |
| [Identity Continuation Profile][continuation] | OAuth | Carrying the same Agent Principal through gateways into further resource domains |
| [SCIM Profile for Governed Agent Federation Management][management] | SCIM | Platform-to-IdP management of Agent Principals, Identity Bindings, and Client Associations |
| [Governed Agent Lifecycle Profile][lifecycle] | SCIM | IdP-to-resource-domain provisioning, administrative disablement, and session revocation |
| [SCIM Profile for OAuth 2.0 Client Management][oauth-client] | SCIM | SCIM management of OAuth client registrations, including Client ID Metadata Document clients |

**Federation (the core).** An OAuth deployment profile that standardizes
the boundary between execution identity and governed identity. Identity
resolution, client authority, user delegation, and resource
authorization remain separate decisions. Every implementation supports
dedicated-client resolution, one OAuth client per agent; shared
platforms use their existing platform JWT to distinguish the agents
behind one client. No new workload credential format is defined. Two
adoption profiles differ in grant protection: bound governed agent
access requires DPoP at issuance and redemption.

**Inputs.** Further agent-resolution inputs that satisfy the core's
input contract, each claimed separately. The core requires an
implementation that uses JWT-SVID client authentication to follow this
companion, so the two drafts reference each other and are published
together.

**Continuation.** Profiles the Identity Continuation Assertion (ICA) for
governed agents, with gateways as the primary deployment. See
[Continuation through gateways](#continuation-through-gateways).

**SCIM management.** Platform-to-IdP administration of the relationships
above. Administering them is authorization management: permission to
create an agent does not imply permission to bind it, and permission to
disable a relationship does not imply permission to enable it.

**Lifecycle.** Provisions issuer-qualified Agent Principals into a
resource domain and applies administrative disablement to OAuth
authorization. Existing SCIM Events trigger reconciliation, and
existing CAEP session-revocation events can revoke what one grant
authorized. It defines no new schema, event type, or authorization
timestamp, and states what current state cannot recover.

**OAuth client management.** A generic SCIM resource for OAuth client
registrations, developing the approach first proposed by Phil Hunt,
Morteza Ansari, and Anthony Nadalin. It can share a registration with
OAuth dynamic registration, and manages local admission of Client ID
Metadata Document clients without copying their metadata.

What each draft needs from the specifications it depends on is in
[COORDINATION.md](COORDINATION.md).

## Continuation through gateways

An agent often reaches tools through a gateway, such as a Model Context
Protocol (MCP) gateway, that selects a tool at request time and calls it
in another resource domain. The gateway holds neither the user's
credential nor the agent's, and calling the tool as itself would make
every agent behind it look the same: the shared-client problem again.

```mermaid
sequenceDiagram
  participant C as Agent client
  participant I as Governing IdP
  participant G as Gateway with its RAS
  participant T as Tool's RAS
  C->>I: Token exchange
  I-->>C: Governed grant, chain root
  C->>G: Redeem the grant, then call the gateway
  G->>G: Its RAS attests that it accepted the grant
  G->>I: Continuation exchange with that attestation
  I-->>G: Onward grant naming the same agent, gateway as client
  G->>T: Redeem the onward grant
  T-->>G: Access token for the tool
```

* The onward grant names the same Agent Principal and, for delegated
  access, the same user. A RAS and API that implement the core accept
  it unchanged.
* The gateway is the grant's client, never an added actor. A separate
  `continuation_via` claim lists the gateways on the path.
* A chain exists only when the user's delegation, or the agent's own
  authorization, permits continuation through other clients, and the
  gateway needs its own Continuation Association.
* Self-acting chains anchor to an agent session that only the agent's
  own authentication keeps active, so a gateway cannot keep a stopped
  agent's chains alive.
* A chain ends when its anchor ends, such as the user's IdP session,
  and on governance events: disabling the agent or user, or withdrawing
  the root binding, association, credential, or authorization.

The same mechanism lets the agent's own client continue a chain for
scheduled work after the user signs out, where the IdP supports chains
anchored to a refresh-token grant.

## Changes and revocation

Identity, authority, and approved work have separate owners, checks,
and lifetimes, so each change ends something different:

| Change | What it stops |
|---|---|
| Disable an Identity Binding | New grants through that binding; the agent's other bindings continue |
| Remove a Client Association | That client's use of the binding; the binding can remain valid |
| Withdraw a user's delegation | New delegated grants for that delegation |
| Disable the Agent Principal | New grants for the agent; once the resource domain applies it, the agent's sessions there are revoked |
| Revoke one grant | All authorization derived from that ID-JAG; the principal is unchanged |
| Apply a Local Suspension | The agent in one resource domain, regardless of upstream state |
| Withdraw what a governed continuation chain rests on | Further continuation of that chain |
| End a Mission | Actions at every boundary that checks work state |

Otherwise, tokens already issued end only by revocation or expiry.
Re-enabling a principal permits new decisions; it does not restore
revoked sessions. Current administrative state cannot reveal a missed
disable-and-reenable cycle, and how quickly an API stops accepting
tokens depends on introspection, caching, and token lifetimes.

## Platform-hosted agents

A platform such as a data or application platform can host agents for a
customer that use only the platform's own tools and resources. The IdP
issues those agents nothing, and the platform must keep running when the
IdP is unavailable. The enterprise still wants them in one inventory,
under one governance decision, and visible in its monitoring. The
drafts support this without putting the IdP in the platform's runtime
path:

* **Register, don't federate.** The platform's connector registers each
  hosted agent at the IdP as an Agent with no Identity Binding or Client
  Association. The agent is visible and governed but cannot obtain an
  IdP grant.
* **Split authority.** The platform owns the agent's existence,
  description, and deletion. The IdP owns the governance decision,
  `active`, and the connector cannot re-enable an agent the IdP
  disabled.
* **Apply governance locally.** When the IdP disables an agent, the
  platform denies new authorization and revokes the agent's existing
  authorization in its own system. Its own suspension is a Local
  Suspension the IdP cannot clear.
* **Signal both ways.** The platform sends WISE credential and posture
  events and CAEP session events about its agents to the IdP, and the
  IdP can send CAEP risk changes back. Events inform policy; they do not
  change administrative state.
* **One correlation key.** The issuer-qualified Agent Principal
  identifier appears in SCIM, in events, and in the platform's audit
  records next to the platform's own identifier.
* **Federate later, same principal.** When the agent needs a resource
  beyond the platform, an administrator adds an Identity Binding and
  Client Association to the same Agent. Its identifier and governance
  history carry over.

The implementer's guide
[follows one agent](IMPLEMENTERS-GUIDE.md#platform-hosted-agents) from
registration through third-party access and retirement, and the
lifecycle draft's [platform-hosted example][lifecycle-example] shows its
risk signals, disablement, and re-enablement.

## Beyond these drafts

These drafts define agent identity and authority up to the allow or deny
decision at an action. Work context and per-action authorization belong
to other specifications:

| Concern | Question | Responsibility | Specifications |
|---|---|---|---|
| Identity | Which governed agent is acting? | The IdP resolves the Agent Principal; the resource domain correlates it locally | These drafts |
| Authority | What may it do, and for whom? | The IdP authorizes the grant; the resource domain decides within its limits | These drafts; AuthZEN and COAZ for per-action decisions; ARAP and AROP for requestable denials |
| Work | Does approved work still justify this action? | Mission-bound authorization supplies and evaluates work context | [Mission-Bound Authorization](https://github.com/mcguinness/mission-bound-authorization) |

Two compositions remain undefined:

* The core lets an API delegate evaluation to a policy decision service,
  which must keep the user, the issuer-qualified Agent Principal, and
  the OAuth client distinct. It names AuthZEN as an optional interface
  but defines no AuthZEN message mapping.
* The core lists asynchronous approval with AROP as an excluded
  composition. Approval that completes as a token is not yet composed
  with governed ID-JAG issuance.

The AuthZEN profiles are developed in the OpenID AuthZEN working group:

* [AuthZEN Authorization API 1.0](https://openid.net/specs/authorization-api-1_0.html):
  a policy enforcement point asks a policy decision point for an access
  decision about a subject, action, resource, and context.
* [COAZ](https://openid.github.io/authzen/authzen-coaz-framework-1_0.html)
  (Compatible with OpenID AuthZEN): a protocol-neutral framework that
  maps an operation's inputs into an AuthZEN request.
  [COAZ-MCP](https://openid.github.io/authzen/authzen-coaz-mcp-binding-1_0.html)
  is its binding for the Model Context Protocol.
* [ARAP](https://openid.github.io/authzen/authzen-access-request-approval-profile-1_0.html)
  (AuthZEN Access Request and Approval Profile): after a requestable
  denial, the enforcement point submits an access request, tracks it as
  an asynchronous task, and re-evaluates after approval.
* [AROP](https://github.com/openid/authzen/blob/main/profiles/authzen-access-request-oauth/authzen-access-request-oauth-profile-1_0.md)
  (AuthZEN Access Request OAuth Profile): binds ARAP to OAuth so that an
  approved request completes as an issued access token.

Also outside these drafts: identity continuity across a chain of IdPs,
multi-agent delegation chains, authorization of individual client
instances, enrollment and key-replacement protocols, request provenance
through intermediaries other than governed continuation, and behavioral
monitoring and anomaly detection.

[core]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html
[inputs]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-inputs.html
[continuation]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html
[management]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-agent-federation.html
[lifecycle]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html
[lifecycle-example]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#platform-example
[oauth-client]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-oauth-client-management.html
