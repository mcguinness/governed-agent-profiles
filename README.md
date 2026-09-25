<!-- regenerate: off (set to off if you edit this file) -->

# OAuth 2.0 Profile for Governed Agent Federation

This is the working area for "OAuth 2.0 Profile for Governed Agent Federation"
and its SCIM client management, agent management, and lifecycle companions.

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

## What the profile defines

The draft defines how an IdP resolves dedicated OAuth client identities or
independently validated workload identities to stable Agent Principals.
Identity Binding, Client Association, user delegation, and resource-local
authorization remain separate decisions.

The mandatory delegated path uses an ID Token issued for the dedicated
client, `private_key_jwt` client authentication, a governed ID-JAG, and RFC
7523 `jwt-bearer` redemption. Dedicated-client resolution uses the authenticated
client context without duplicating its assertion in `actor_token`.
SPIFFE JWT-SVID, WIT-SVID, X.509-SVID, existing platform JWT, and
Client Attestation inputs are optional. Shared platforms agree on a workload
input that distinguishes agents behind their SSO client. No new credential
format or per-replica registration is required.

Two governed profiles support incremental adoption. Bound governed agent
access requires DPoP at issuance and redemption; governed agent access permits
unbound grants only under explicit policy. Access-token protection is a
separate choice: DPoP, mutual TLS, or explicitly permitted bearer use. The
API enforces user authority and the actor gate in every governed mode.

The complete dedicated-client walkthrough includes a shared-client SPIFFE
variant. Continuing access uses eligible subject credentials for new ID-JAGs
or policy-permitted RAS refresh within retained authorization and lifetime
limits. Existing SSO refresh tokens do not automatically authorize downstream
resources.

The self-acting WAG realization issues an IdP-signed WAG naming the Agent
Principal as subject, redeemed with the JWT bearer grant and correlated to
the same local principal. Its token-type, JWT-type, and profile
identifiers are provisional pending coordination with WAG.
Instance identification, attester endorsement, key transition, and Identity
Continuation Assertion compositions remain deferred.

* [Editor's Copy](https://mcguinness.github.io/governed-agent-profiles/#go.draft-mcguinness-oauth-governed-agent-federation.html)
* [Datatracker Page](https://datatracker.ietf.org/doc/draft-mcguinness-oauth-governed-agent-federation)
* [Individual Draft](https://datatracker.ietf.org/doc/html/draft-mcguinness-oauth-governed-agent-federation)
* [Compare Editor's Copy to Individual Draft](https://mcguinness.github.io/governed-agent-profiles/#go.draft-mcguinness-oauth-governed-agent-federation.diff)

## SCIM OAuth Client Management

The generic OAuthClient profile develops the SCIM registration approach first
proposed by Phil Hunt, Morteza Ansari, and Anthony Nadalin. It maps current
OAuth registration metadata into SCIM 2.0 and defines management of the same
registration through SCIM and RFC 7591/7592 interfaces. CIMD clients retain
their URL identifiers and document-owned metadata; SCIM manages local
admission and references used by agent associations. Client registration,
agent identity, and permission to use that identity remain separate.

* [OAuthClient profile source](draft-mcguinness-scim-oauth-client-management.md)
* [OAuthClient editor's copy](https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-oauth-client-management.html)

## Platform-to-IdP SCIM Management

The SCIM management profile provisions Agent Principals and administers
Identity Bindings and Client Associations at the IdP. It reuses SCIM
operations, adds a small Agent identity extension and two relationship
resources, and references OAuthClient registrations from the generic profile.
Dedicated-client bindings reference OAuthClient and administer identity
and client-use permission together. Shared-client deployments retain
external workload bindings and separate Client Associations. Both support CIMD clients without copying their metadata.
Credential-authority trust, client registration permission, user delegation,
and downstream revocation remain separate.

* [SCIM management profile source](draft-mcguinness-scim-agent-federation.md)
* [SCIM management editor's copy](https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-agent-federation.html)

## Provisioning and Lifecycle Companion

The lifecycle profile uses SCIM Agent administrative state and issuer-qualified
correlation to apply disablement at the RAS. Re-enablement permits new
authorization decisions without restoring revoked sessions. API enforcement
still depends on introspection, caching, and token expiry.

The lifecycle draft also profiles existing SCIM Events and optional CAEP
revocation. Provisioning and feed events trigger authoritative reconciliation;
CAEP can revoke all authorization derived from an issuer-qualified ID-JAG
`jti`. No new event type, eligibility lease, or authorization cutoff is
defined. Current state cannot recover a missed disable-and-reenable cycle.

* [Lifecycle profile source](draft-mcguinness-oauth-governed-agent-lifecycle.md)
* [Lifecycle profile editor's copy](https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html)

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
