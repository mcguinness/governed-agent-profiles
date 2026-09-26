<!-- regenerate: off (set to off if you edit this file) -->

# Governed Agent Profiles

This is the working area for four related Internet-Drafts on governing
agents across platform, identity-provider, and resource-domain boundaries:

| Draft | What it covers |
|---|---|
| [OAuth 2.0 Profile for Governed Agent Federation](#oauth-20-profile-for-governed-agent-federation) | Resolves client and workload identities to a stable Agent Principal and carries it into a resource domain |
| [SCIM Profile for Governed Agent Federation Management](#scim-profile-for-governed-agent-federation-management) | Platform-to-IdP management of Agent Principals, Identity Bindings, and Client Associations |
| [Governed Agent Lifecycle Profile for SCIM and OAuth](#governed-agent-lifecycle-profile-for-scim-and-oauth) | IdP-to-resource-domain provisioning, administrative disablement, and session revocation |
| [SCIM Profile for OAuth 2.0 Client Management](#scim-profile-for-oauth-20-client-management) | Generic SCIM management of OAuth client registrations, including CIMD clients |

Together with the OpenID AuthZEN profiles, they form one
[architecture for governed agents](#an-architecture-for-governed-agents).

## Why this matters

Enterprises run agents on platforms they do not operate: a coding agent on
one vendor's runtime, a support agent on another, something else on a
developer's laptop. Each platform issues its own identity for the thing it
runs. None of those identities is what the enterprise needs to govern.

What the enterprise needs is a principal it can authorize once, audit across
systems, and disable everywhere. Platform and client identity do not line up
with that boundary. One runtime can serve several agents that need separate
authorization, and one agent can move between runtimes while its authority
has to stay the same.

The common workaround is a shared OAuth client per platform integration.
Every agent behind it looks identical to the resource server, so attribution
is lost and revocation becomes all or nothing.

## Why now

Agent deployments multiply the number of platforms an enterprise federates
with, and they ask resource servers to authorize callers that have no
registration relationship with them. The pieces needed to answer that exist
separately and do not yet compose:

* OAuth 2.0 Token Exchange defines `act` but leaves the actor's meaning to
  profiles.
* ID-JAG brokers cross-application access through the IdP both sides already
  trust for SSO, and deliberately leaves actor-token validation,
  authorization, and representation to extensions.
* Attestation-based and SPIFFE client authentication establish which OAuth
  client is calling, not which agent a shared client is acting for.

Federation already answers which external identity is calling. What is
missing is which enterprise principal that identity represents, whether this
client may exercise it, and what it may do once it arrives. These drafts
profile that.

## An architecture for governed agents

Governing agents means owned facts, explicit boundaries, composition at the
action, and independent ends.

Three facts matter for every agent action: which governed principal is
acting, what authority it holds, and whether approved work still justifies
the action. Each fact is established by its own owner, carried across
boundaries by an explicit contract, decided at the action, and ended on its
own:

| Fact | Established by | Carried across boundaries by | Decided at the action by | Ended by |
|---|---|---|---|---|
| **Identity**: which governed principal is acting | The IdP: Agent Principal, Identity Bindings, and Client Associations (SCIM Governed Agent Federation Management) | Governed Agent Federation, across execution changes through Identity Binding and across domains with the agent preserved and the user translated | RAS correlation of the issuer-qualified agent, and the actor gate at the API | Principal or binding disablement (Governed Agent Lifecycle); Local Suspension as the resource domain's own denial |
| **Authority**: what it may do, and for whom | The IdP: Delegation Authorization or Agent Authorization for an associated client | The grant, ID-JAG or WAG, as a ceiling | The RAS deciding anew within that ceiling; AuthZEN and COAZ allowing or denying each operation; ARAP and AROP re-establishing authority after a requestable denial | Grant and session revocation at the issuing server (Governed Agent Lifecycle, CAEP) |
| **Work**: whether approved work still justifies the action | Mission approval | Mission projection | Mission runtime enforcement, at the same AuthZEN decision point with work state as an input | Mission termination, which reaches every boundary that checks work state |

These drafts define the Identity and Authority rows.
[Mission-Bound Authorization](https://github.com/mcguinness/mission-bound-authorization)
defines the Work row. The fact-by-fact treatment of boundaries follows
[Continuity Is Not One Thing](https://notes.karlmcguinness.com/notes/continuity-is-not-one-thing/).

### Principles

* **Execution identity is evidence; governed identity is the principal.**
  Platforms mint execution identities. The enterprise governs the principal,
  and an Identity Binding connects the two, so an agent keeps its identity
  when it moves between platforms or rotates credentials.
* **Every fact has an owner, and no fact stands in for another.** The IdP
  owns identity, the resource domain owns resource authority, and the Mission
  control point owns work. Being known is not being authorized, and being
  authorized is not being approved for this work.
* **Owners, not a single control plane.** Each boundary keeps its own
  decision: the RAS decides anew within the grant, and a Local Suspension
  cannot be cleared from upstream.
* **Facts cross boundaries only by contract.** A contract states what is
  preserved, what is translated, and what is decided anew. Traceable
  delegation is attribution, not authority.
* **As many kill switches as owners.** Each fact ends on its own, with its
  own reach and timing.

Request provenance through intermediaries, behavioral monitoring, anomaly
detection, and telemetry are outside this architecture.

### How the drafts fit together

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

Where they meet these drafts today:

* The Federation draft lets an API delegate evaluation to a policy decision
  service, which must keep the user, the issuer-qualified Agent Principal, and
  the OAuth client distinct. It names AuthZEN as an optional interface but
  defines no AuthZEN message mapping.
* The Federation draft lists asynchronous approval with AROP as an excluded
  composition. Approval that completes as a token is not yet composed with
  governed ID-JAG issuance.

## OAuth 2.0 Profile for Governed Agent Federation

The core draft defines how an IdP resolves dedicated OAuth client identities
or independently validated workload identities to stable Agent Principals.
Identity Binding, Client Association, user delegation, and resource-local
authorization remain separate decisions.

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

The mandatory delegated path uses an ID Token issued for the dedicated
client, `private_key_jwt` client authentication, a governed ID-JAG, and RFC
7523 `jwt-bearer` redemption. Dedicated-client resolution uses the
authenticated client context without duplicating its assertion in
`actor_token`. SPIFFE JWT-SVID, WIT-SVID, X.509-SVID, existing platform JWT,
and Client Attestation inputs are optional. Shared platforms agree on a
workload input that distinguishes agents behind their SSO client. No new
credential format or per-replica registration is required.

Two governed profiles support incremental adoption. Bound governed agent
access requires DPoP at issuance and redemption; governed agent access permits
unbound grants only under explicit policy. Access-token protection is a
separate choice: DPoP, mutual TLS, or explicitly permitted bearer use. The
API enforces user authority and the actor gate in every governed mode.

The appendices walk through the dedicated-client flow and a shared-client
SPIFFE variant. Continuing access uses eligible subject credentials for new
ID-JAGs or policy-permitted RAS refresh within retained authorization and
lifetime limits. Existing SSO refresh tokens do not automatically authorize
downstream resources.

The self-acting WAG realization, the peer of the delegated ID-JAG profile,
issues an IdP-signed WAG naming the Agent Principal as subject, redeemed with
the JWT bearer grant and correlated to the same local principal. Each
realization has its own mandatory path, and an implementation claims one or
both. The WAG token type and JWT type are provisional values until WAG
registers them. Instance
identification, attester endorsement, key transition, and Identity
Continuation Assertion compositions remain deferred.

* [Editor's Copy](https://mcguinness.github.io/governed-agent-profiles/#go.draft-mcguinness-oauth-governed-agent-federation.html)
* [Datatracker Page](https://datatracker.ietf.org/doc/draft-mcguinness-oauth-governed-agent-federation)
* [Individual Draft](https://datatracker.ietf.org/doc/html/draft-mcguinness-oauth-governed-agent-federation)
* [Compare Editor's Copy to Individual Draft](https://mcguinness.github.io/governed-agent-profiles/#go.draft-mcguinness-oauth-governed-agent-federation.diff)

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
