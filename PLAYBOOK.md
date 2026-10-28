# Governing Agents: A Playbook for Identity Teams

This playbook is non-normative. It turns the governed agent profiles
into the work an enterprise identity team does: what to stand up, in
what order, what to require from vendors, how to stop and restore an
agent, and what to show an auditor. The drafts define every
requirement and govern wherever this playbook differs. The
[architecture overview](ARCHITECTURE.md) explains the model, and the
[implementer's guide](IMPLEMENTERS-GUIDE.md) explains what each role
builds.

* [The decisions an identity team owns](#the-decisions-an-identity-team-owns)
* [Adoption stages](#adoption-stages)
* [Enterprise patterns](#enterprise-patterns)
* [Vendor requirements](#vendor-requirements)
* [Runbooks: stop and restore](#runbooks-stop-and-restore)
* [Ownership and reviews](#ownership-and-reviews)
* [Audit evidence](#audit-evidence)
* [Where security tooling plugs in](#where-security-tooling-plugs-in)

## The decisions an identity team owns

Each decision is recorded in one relationship, so it can be granted,
reviewed, and withdrawn on its own:

| Decision | Recorded as | Where |
|---|---|---|
| Which agent is this? | Agent Principal, with an accountable owner | The IdP |
| Which execution identity is that agent? | Identity Binding: an exact client or workload identity mapped to the Agent Principal | The IdP |
| Which OAuth clients may act as that agent? | Client Association, or a dedicated-client binding that records both | The IdP |
| What may the agent do for a user? | Delegation Authorization: agent, user, client, tenant, target, and authority | The IdP |
| What may the agent do on its own? | Agent Authorization | The IdP |
| Which gateways may carry its requests further? | Continuation Association | The IdP |
| Is the agent known and allowed here? | The local agent principal, its eligibility, and any Local Suspension | Each resource domain |

None of these implies another. A valid credential does not authorize
use of the agent, owning an agent does not make the owner its
delegator, and a user's sign-in does not authorize an agent to act for
that user.

## Adoption stages

The stages build on each other, but delegated and self-acting access
can be adopted in either order. Each stage ends with checks that can be
run, most of them from the drafts' negative tests.

### 1. Register

Create an Agent Principal for each agent, with an owner, and an Identity
Binding for each execution identity that runs it. Register the OAuth
clients agents use. Platforms can do this through the [SCIM management
profile][management], whose Service Provider keeps registering an agent,
binding it, and authorizing a client as separate permissions.

*Exit checks:*
* Every production agent has an Agent Principal, with its owner recorded
  in the Agent resource's `owners` attribute.
* Permission to register agents does not let a connector bind them or
  authorize clients.
* An execution identifier, such as a session or replica ID, never
  selects an Agent Principal; bindings name exact identities.

### 2. Federate

Configure Client Associations and Delegation or Agent Authorizations,
and have resource domains accept governed grants: an ID-JAG for
delegated access and a WAG for self-acting access ([core][core]). Start
with dedicated-client resolution, one OAuth client per agent
authenticating with `private_key_jwt`, which every conforming
implementation supports. Shared platforms add the existing platform JWT
input. Self-acting Client Associations are configured at the IdP
directly; the SCIM management profile administers associations for
delegated issuance only.

*Exit checks:*
* Resource-domain records show the user, the issuer-qualified Agent
  Principal, and the client separately.
* With the Identity Binding disabled, issuance fails with
  `invalid_grant`.
* With the Client Association disabled, issuance fails with
  `actor_unauthorized`.
* A delegated access token without `act`, presented to an API configured
  for delegated tokens, is rejected with HTTP 401 `invalid_token`.
* An access token presented in another tenant, even with a valid proof,
  is rejected with HTTP 401 `invalid_token`.

### 3. Bind

Move to bound governed agent access: DPoP at grant issuance and
redemption, so a stolen grant cannot be redeemed. Choose access-token
protection separately, per client and resource: DPoP, mutual TLS, or
bearer where explicitly permitted.

*Exit checks:*
* Where the bound profile is required, a grant without `cnf` is rejected
  with `invalid_grant`, with no fallback.
* A bound grant redeemed without its proof is rejected with
  `invalid_grant`.

### 4. Propagate

Provision Agent Principals into resource domains and apply disablement
there ([lifecycle][lifecycle]). The resource domain's authorization
server then denies redemption and refresh for a disabled agent and
revokes its sessions. Optionally, enable grant-derived revocation so
one ID-JAG's authority can be revoked without disabling the agent.

*Exit checks:*
* Disabling an agent at the IdP stops redemption and refresh at the
  resource domain, and revokes its sessions there.
* Re-enabling it permits new decisions but restores no revoked session.
* A delayed activation notice triggers retrieval of current state; it is
  never applied as an activation.
* The deployment documents its expected and maximum disablement delay,
  including propagation, token lifetime, and caching, as the lifecycle
  profile recommends ("Resource Enforcement and Delay").

### 5. Continue

Where agents reach tools through gateways, deploy continuation
([continuation][continuation]): the gateway's authorization server
attests the agent's grant, and the IdP issues an onward grant naming the
same agent, with the gateway as client. Give each gateway a Continuation
Association, and make sure target authorization servers support DPoP at
their token endpoints.

*Exit checks:*
* The onward grant names the same Agent Principal and user, and lists
  the gateway in `continuation_via`.
* A gateway without a Continuation Association is refused with
  `unauthorized_client`, and it does not call the tool with its own
  authority.
* An agent disabled and re-enabled between continuations has its chain
  ended (`invalid_continuation`); a new root grant is needed.

### 6. Decide per action

Where a resource domain needs decisions finer than a grant's resource
and scope, add a policy decision point, for example through AuthZEN
([guide][guide-authzen]), and feed it risk signals
([guide][guide-risk]). The enforcement point supplies the user, agent,
client, tenant, and token constraints itself, from the validated token.

*Exit checks:*
* A tool's declared mapping cannot change the agent identity the policy
  decision point sees.
* A permit never widens the token's scope or tenant.

## Enterprise patterns

| Pattern | What it needs | Notes |
|---|---|---|
| A SaaS agent works for employees across SaaS apps | Core delegated access (ID-JAG) at each target app; lifecycle where apps are provisioned | Each app sees the employee and the agent, not the vendor's shared client |
| An internal agent acts for itself | Core self-acting access (WAG); an Agent Authorization per target | A WAG redemption yields no refresh token; the agent obtains a new WAG |
| An agent reaches tools through an MCP gateway | Continuation, with the gateway as continuing client; per-tool policy optional | The tool sees the same agent, with the gateway as client and in `continuation_via` |
| Scheduled work runs after the user signs out | Continuation from a chain anchored to a refresh-token grant, where the IdP claims grant-anchored continuation | Runs need no retained user credential; withdrawing the delegation ends the chain |
| A platform hosts agents that use only its own resources | Registration through SCIM management, with no binding or association; the platform applies the IdP's decisions under lifecycle | The IdP is not on the platform's runtime path; federating later keeps the same Agent Principal |

## Vendor requirements

Ask vendors for conformance claims, which name the profile, the role,
the realization, and the inputs. Requirements to include:

| Role | Require |
|---|---|
| Identity provider | Delegated and, where needed, self-acting realization of the core, with dedicated-client resolution through `private_key_jwt` and ID Token subjects; bound governed agent access; generic shared-client interoperability through the existing platform JWT input, where platforms share a client; the SCIM management Service Provider role; continuation as IdP, and grant-anchored continuation for scheduled work |
| Resource authorization server (the app's or API's) | The RAS role for each realization it serves; DPoP at its token endpoint; the lifecycle Receiver role, with grant-derived revocation where needed; correlation of agents by the exact (issuer, agent identifier) pair |
| API | The core's resource processing: tenant checks, the user's authority and the actor gate for delegated tokens, and the agent's own authority for self-acting tokens |
| Agent platform | A client per agent with `private_key_jwt`, or the existing platform JWT input for a shared client; DPoP; reuse of tokens only within the same agent, user, tenant, and authority; the SCIM management Provisioning Client role |
| Gateway | Continuation as continuing client; no fallback to the gateway's own authority after a refused continuation |
| Authorization server that accepts the gateway's tokens | Continuation as continuation-aware RAS, and as Continuation Assertion Issuer with assertion issuance at its token endpoint; often the gateway operator's own, but possibly a separate one |

The profile identifiers to name are
`urn:ietf:params:oauth:grant-profile:id-jag-agent-federation` (bound,
delegated), `urn:ietf:params:oauth:grant-profile:wag-agent-federation`
(bound, self-acting), and
`urn:ietf:params:oauth:grant-profile:governed-agent-continuation`
(continuation). During evaluation, run the exit checks above and the
negative tests in the core ("Renewal and Negative Tests"), the
continuation profile ("Negative Tests"), and the lifecycle profile
("Acceptance Checklist").

## Runbooks: stop and restore

Each change stops a defined set of authority. What it does not stop
continues until its own revocation, validation, or expiry rule ends it.

### Disable an agent everywhere

1. Set the Agent to `active: false` at the IdP. No new grant issues for
   it through any binding or client, and its governed continuation
   chains end.
2. Propagate to resource domains through lifecycle provisioning, or let a
   change notice trigger reconciliation. Each resource domain's
   authorization server denies redemption and refresh and revokes the
   agent's sessions. A platform that hosts the agent denies new
   authorization and revokes the agent's existing authorization.
3. **Still running:** access tokens an API accepts offline or from a
   cache, until they expire or the cache entry ends.

*Restore:* set `active: true`. New decisions are permitted, but revoked
sessions stay revoked and ended chains stay ended; the agent's clients
obtain new grants.

### Cut one agent off from one application

* **In that resource domain:** apply a Local Suspension. No new access
  token or refresh issues there, and upstream activation cannot clear
  it. Other domains are unaffected.
* **At the IdP:** when the agent's Delegation or Agent Authorization no
  longer covers that target, however the IdP records the change, new
  grants for that target are refused, and continuation to it fails with
  `invalid_target`, while the agent's chains continue to other targets.
* **Still running:** tokens already issued for that application, until
  revocation or expiry.

*Restore:* lift the Local Suspension or restore the authorization.
Sessions revoked in the meantime stay revoked.

### Revoke one suspicious grant

Where the resource domain supports the lifecycle profile's optional
grant-derived revocation, send a CAEP `session-revoked` event naming the
ID-JAG by issuer and `jti`. Every authorization derived from that grant
in the tenant is revoked, later redemption is rejected, and the agent
stays enabled. For access derived from a WAG, revocation of one grant is
deployment-specific.

### Respond to a compromised credential or key

* **A dedicated client's key:** disable the OAuthClient, which blocks
  resolution through it and every association that uses it, then
  register a new key. Revoking that credential ends the continuation
  chains rooted through it.
* **A platform's signing key or credential authority:** remove it from
  trust configuration, or disable the Identity Bindings that rely on it.
  Revoking a credential does not retire the Agent Principal; an agent
  with other valid bindings keeps them.
* **Still running:** grants already issued, until their short lifetimes
  end, and resource-domain tokens until revoked or expired. Disable
  affected agents or associations if the exposure is broad.

### Offboard a user or an agent owner

* **A user leaves:** disable the user through the IdP's own user
  lifecycle. What follows from it here: no new delegated grant issues
  for that user, and the user's delegated chains end. Agents'
  self-acting authority is unaffected.
* **An agent's owner leaves:** reassign the owner. Owners are
  accountable for an agent but are not its delegators, so the change
  alters no authorization. Disable the agent if policy requires an
  owner and none is assigned.

## Ownership and reviews

| Team | Owns |
|---|---|
| Identity (IAM) | Agent Principals and owners; Identity Bindings; Client Associations; Delegation and Agent Authorizations; Continuation Associations; IdP issuance policy; the authority of SCIM connectors |
| Resource and application owners | Local agent principals and their eligibility; actor-gate policy; access-token protection per client and resource; Local Suspension; per-action policy |
| Platform engineering | Agent OAuth clients and their keys; workload credentials; the SCIM connector |
| Security operations | Signals into the IdP and policy decision points; running the containment runbooks; incident records |

Certify on the same cadence as human access:

* Delegation Authorizations, by user and by agent.
* Client Associations and dedicated-client bindings, by client.
* Continuation Associations, by gateway.
* Agent Principals without an owner, or with no grant issued for a
  defined period.

## Audit evidence

Each action an API performs for an agent can be traced to:

* **The user,** as the access token's subject, for delegated access.
* **The agent,** as the issuer-qualified Agent Principal in `act`, or as
  the correlated subject for self-acting access.
* **The client,** as `client_id`, which never stands in for the agent.
* **The path,** as `continuation_via`, where a gateway continued the
  request and the resource domain supports path disclosure; the IdP's
  hop records hold the complete path.
* **The authorization,** as the IdP's issuance decision under the
  Delegation or Agent Authorization, and the resource domain's own
  decision.

The drafts define no log format. Record these identifiers together in
the IdP's issuance records and in each resource domain's access
records, and use the Agent Principal as the key that joins them with
security telemetry.

## Where security tooling plugs in

Discovery, posture management, runtime monitoring, data loss
prevention, sandboxing, and endpoint controls belong to other teams and
tools. The identity team supplies what they need from identity: the
Agent Principal as the key that correlates their findings, and
relationships that can be withdrawn precisely when they detect a
problem. Their signals reach identity decisions through the lifecycle
profile's events and through risk inputs to policy decision points
([guide][guide-risk]). In return, a disablement or revocation here has a
defined effect that response tooling can rely on.

[core]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html
[continuation]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html
[lifecycle]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html
[management]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-agent-federation.html
[guide-authzen]: IMPLEMENTERS-GUIDE.md#authorization-decisions-with-authzen
[guide-risk]: IMPLEMENTERS-GUIDE.md#risk-signals
