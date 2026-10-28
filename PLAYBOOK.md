# Governing Agents: A Playbook for Identity Teams

This playbook is non-normative. It turns the governed agent profiles
into the work an enterprise identity team does: choosing a pilot,
assigning owners, configuring and validating an integration, requiring
evidence from vendors, stopping and restoring an agent, and showing an
auditor what happened. The drafts define every
requirement and govern wherever this playbook differs. The
[architecture overview](ARCHITECTURE.md) explains the model, and the
[implementer's guide](IMPLEMENTERS-GUIDE.md) explains what each role
builds.

* [The decisions an identity team owns](#the-decisions-an-identity-team-owns)
* [Operating steps](#operating-steps)
* [Recipes](#recipes)
* [Vendor requirements](#vendor-requirements)
* [Runbooks: stop and restore](#runbooks-stop-and-restore)
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

## Operating steps

Five steps take a deployment from a pilot to operation. Delegated and
self-acting access are independent: a pilot can start with either, and
adding the other later repeats steps 2 and 3 for it. Grant protection is
chosen in step 1 and configured in step 3, with the rest of the
integration.

### 1. Choose a pilot and its operating model

Pick one agent, one OAuth client, one resource domain and tenant, and,
for delegated access, a small set of users. Then record the choices
that the later steps test:

| Choice | Options | What it determines |
|---|---|---|
| Acting relationship | Delegated (ID-JAG), self-acting (WAG), or both | Which authorization the IdP checks, and whether the RAS and API apply the actor gate. With both, also how the API tells the two token populations apart: separate client registrations, audiences, or issuers, or authenticated introspection context. The absence of `act` never does, since a malformed delegated token would then pass as self-acting |
| Resolution input | A dedicated client authenticating with `private_key_jwt`, or a shared client presenting its existing platform JWT | Whether the client's own authentication identifies the agent, or a platform JWT does |
| Grant protection | Bound governed agent access, with DPoP at grant issuance and redemption; or governed agent access, with unbound grants only where policy explicitly permits them | Whether a stolen grant can be redeemed |
| Access-token protection, per resource | DPoP, mutual TLS, or bearer where the resource explicitly permits it | What a stolen access token allows |
| Token validation at the API | Introspection on each request, cached introspection, or offline JWT validation | How soon a revocation at the RAS reaches the API: at the next check, when the cache entry ends, or at token expiry ("Resource Enforcement and Delay" in the [lifecycle profile][lifecycle]) |
| Creating agent records at the RAS | Provisioned in advance, or created just in time from a validated grant where resource policy enables it | Whether the first redemption needs provisioning to have run; without a record, the RAS denies it |
| Keeping agent records current | Lifecycle provisioning and reconciliation, another supported signal, or local administration only | How the RAS learns that the agent was disabled. A grant does not carry the IdP's administrative status, so without lifecycle integration, any record learns of it only through local action or another signal |
| Federation | Federated, or registration only, for a platform-hosted agent that uses only its platform's own resources | Registration-only agents follow the [registration-only branch](#registration-only-branch) |

The two record choices are independent. Under the lifecycle profile, a
record created just in time is exposed to provisioning and follows the
same reconciliation and disablement rules as one provisioned in
advance.

The [recipes](#recipes) fill in these choices for a complete pilot.
Acceptance in steps 2 and 3 covers the pilot population; coverage of
every production agent is a rollout measure in step 5.

### 2. Assign owners and record the decisions

Assign each decision in [the table above](#the-decisions-an-identity-team-owns)
to a team:

| Team | Owns |
|---|---|
| Identity (IAM) | Agent Principals and owners; Identity Bindings; Client Associations; Delegation and Agent Authorizations; Continuation Associations; IdP issuance policy; the authority of SCIM connectors |
| Resource and application owners | Local agent principals and their eligibility; actor-gate policy; access-token protection per client and resource; Local Suspension; per-action policy |
| Platform engineering | Agent OAuth clients and their keys; workload credentials; the SCIM connector |
| Security operations | Signals into the IdP and policy decision points; running the containment runbooks; incident records |

Then create an Agent Principal for each pilot agent, with an
accountable owner, an Identity Binding for each execution identity that
runs it, and the OAuth client registrations it uses. Platforms can do
this through the [SCIM management profile][management], whose Service
Provider keeps registering an agent, binding it, and authorizing a
client as separate permissions.

*Exit checks, for the pilot population:*
* Each pilot agent has an Agent Principal with a recorded owner; in SCIM
  management, the Agent resource's `owners` attribute.
* Permission to register agents does not let a connector bind them or
  authorize clients.
* An execution identifier, such as a session or replica ID, never
  selects an Agent Principal; bindings name exact identities.

### 3. Configure and validate the first integration

Configure the choices from step 1 together, including grant and
access-token protection:

* **At the IdP:** the Client Association for the acting relationship;
  the Delegation Authorization (agent, user, client, tenant, target, and
  authority) or the Agent Authorization; the target RAS and tenant; and
  the client registration association that supplies the grant's
  `client_id` at the RAS. Self-acting Client Associations are
  configured at the IdP directly; the SCIM management profile
  administers associations for delegated issuance only.
* **At the RAS:** the agent's local record, keyed by the exact (IdP
  issuer, agent identifier) pair; user links and the actor-gate policy
  for delegated access; DPoP at the token endpoint for bound grants; and
  the access-token protection for each resource.
* **At the API:** tenant checks, and either the user's authority and the
  actor gate for delegated tokens, or the agent's own authority for
  self-acting tokens. Where both populations reach one API, it
  distinguishes them as chosen in step 1.
* **At the client:** its registrations and keys at the IdP and the RAS,
  and a DPoP key for bound grants.

The implementer's guide lists each item under [Federation
configuration](IMPLEMENTERS-GUIDE.md#federation-configuration).

*Exit checks:* run the matching recipe's transaction and rejection
tests, and these common checks:
* Resource-domain records show the user, the issuer-qualified Agent
  Principal, and the client separately.
* With the Identity Binding disabled, issuance fails with
  `invalid_grant`.
* Where the bound profile is required, a grant without `cnf` is rejected
  with `invalid_grant`, with no fallback.
* A bound grant redeemed without its proof is rejected with
  `invalid_grant`.
* An access token presented in another tenant, even with a valid proof,
  is rejected with HTTP 401 `invalid_token`.

### 4. Add capabilities when needed

Each capability is independent of the others. Add one when the
deployment needs what it addresses, and run its checks.

#### Lifecycle propagation

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

#### Continuation through gateways

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

#### An external policy decision point

Resource authorization already applies at every RAS and API from step
3. A resource domain that needs decisions finer than a grant's resource
and scope can evaluate that policy locally or delegate it. This
capability covers delegation: an external policy decision point, for
example through AuthZEN ([guide][guide-authzen]), fed with risk signals
([guide][guide-risk]). The enforcement point supplies the user, agent,
client, tenant, and token constraints itself, from the validated token.

*Exit checks:*
* A tool's declared mapping cannot change the agent identity the policy
  decision point sees.
* A permit never widens the token's scope or tenant.

### 5. Operate, review, and retire

* **Roll out.** Extend from the pilot until every production agent has
  an Agent Principal with an owner, and an exact Identity Binding for
  each execution identity that runs it.
* **Review.** Certify on the same cadence as human access:
  * Delegation Authorizations, by user and by agent.
  * Agent Authorizations, by agent, since they govern self-acting
    access.
  * Client Associations and dedicated-client bindings, by client.
  * Continuation Associations, by gateway.
  * Agent Principals without an owner, or with no grant issued for a
    defined period.
* **Respond.** Stop and restore access with the
  [runbooks](#runbooks-stop-and-restore).
* **Retire.** Follow [Retire an agent](#retire-an-agent): disable it
  everywhere first, so resource domains revoke its sessions, and then
  delete it and its relationships.

### Registration-only branch

A platform-hosted agent that uses only its platform's own tools and
resources needs no federation. Steps 1, 2, and 5 apply to it, and
registration replaces step 3:

* The platform's connector registers the agent at the IdP through the
  SCIM management profile, with no Identity Binding or Client
  Association, so no client can obtain an IdP grant naming it.
* The platform is the resource domain and the lifecycle Receiver for
  the agent. It correlates its agent with the qualified Agent Principal
  identifier the registration returned; just-in-time correlation does
  not apply.
* The platform obtains the agent's `active` value from IdP provisioning,
  or by retrieving the registered Agent when a change notice or periodic
  reconciliation indicates a change.

*Exit checks:*
* With the agent set to `active: false` at the IdP, the platform denies
  new authorization for it and revokes its existing authorization in its
  own system. An agent the IdP registered inactive pending approval is
  denied the same way.
* Re-enabling the agent permits new decisions but restores no revoked
  authorization.
* The connector's authority to register and describe agents does not
  let it set `active: true` on an agent the IdP disabled, and the
  platform's own suspension is a Local Suspension that IdP activation
  does not clear.
* An unreachable IdP neither disables nor re-enables the agent. Where
  the deployment bounds how long the platform relies on unrefreshed
  state, new authorization is denied when that bound expires.
* The platform's audit records carry the qualified Agent Principal
  identifier next to its own identifier for the agent.

To federate later, add an Identity Binding and a Client Association
for the selected acting relationship to the same Agent, and continue
with step 3. The Agent Principal identifier and its governance history carry
over. The implementer's guide [follows one platform-hosted
agent](IMPLEMENTERS-GUIDE.md#platform-hosted-agents) from registration
to retirement.

## Recipes

| Pattern | What it needs | Recipe |
|---|---|---|
| A SaaS agent works for employees across SaaS apps | Core delegated access (ID-JAG) at each target app; lifecycle where apps are provisioned | [Delegated access to a SaaS application](#recipe-delegated-access-to-a-saas-application) |
| An internal agent acts for itself | Core self-acting access (WAG); an Agent Authorization per target | [Self-acting access](#recipe-self-acting-access) |
| An agent reaches tools through an MCP gateway | Continuation, with the gateway as continuing client; per-tool policy optional | [Through a gateway](#through-a-gateway) |
| Scheduled work runs after the user signs out | Continuation from a chain anchored to a refresh-token grant, where the IdP claims grant-anchored continuation | [Scheduled work](#scheduled-work) |
| A platform runs many agents behind one client | The existing platform JWT input | [A shared platform client](#a-shared-platform-client) |
| A platform hosts agents that use only its own resources | Registration through SCIM management, with no binding or association; the platform applies the IdP's decisions under lifecycle | [Registration-only branch](#registration-only-branch) |

Both recipes use the architecture's example and the identifiers of the
core's [walkthrough][core-walkthrough], so each test can be compared
with the messages there. The [architecture](ARCHITECTURE.md#access-flows-and-deployment-variants)
explains why each check holds.

### Recipe: delegated access to a SaaS application

**Outcome.** `agent-42` reads files for Alice in the data application
`https://api.example/`, a SaaS application in which the enterprise's
tenant is `acme-data`. The application sees Alice as the user and
`agent-42` as the actor, separately from the client, and the enterprise
IdP can stop the agent without affecting Alice or other agents.

**Parties and owners.**

| Party | In the example | Owner |
|---|---|---|
| Agent platform and client | `analysis-client`, a dedicated client that runs `agent-42` | Platform engineering |
| Governing IdP | `https://idp.example/` | Identity (IAM) |
| Resource domain | RAS `https://ras.example/`, API `https://api.example/`, tenant `acme-data` | The application owner |
| User | Alice: `alice-ras` in the grant, `user-108` at the API | Not applicable; her delegations are certified by user in step 5 |
| Agent | (`https://idp.example/`, `agent-42`) | Its accountable owner, from step 2 |

**Operating model.** Delegated; a dedicated client with
`private_key_jwt`; bound governed agent access; DPoP access tokens;
introspection at the API; and the agent provisioned at the RAS through
the lifecycle profile, which also propagates its disablement
([step 4](#lifecycle-propagation)).

**Configuration.**

* At the IdP: an Identity Binding that maps (`analysis-client`,
  `analysis-client`) to `agent-42`; a Client Association that permits
  `analysis-client` to use it for delegated issuance; Alice's Delegation
  Authorization for `agent-42`, with `files.read` at
  `https://api.example/tenants/acme-data/`; and the client registration
  association from `analysis-client` to `analysis-api` at
  `https://ras.example/`.
* At the RAS: the local agent principal for (`https://idp.example/`,
  `agent-42`), Alice's link to `user-108`, an actor-gate policy that
  permits `agent-42` to act for Alice in `acme-data`, the client
  registration `analysis-api`, and DPoP at the token endpoint.
* At the API: DPoP access tokens, tenant checks, Alice's permissions,
  and the actor gate.

**One successful transaction.**

1. Alice signs in to the client through the IdP. The client holds her
   ID Token, whose audience is `analysis-client`.
2. The client exchanges the ID Token at the IdP, authenticating as
   `analysis-client` and proving its DPoP key, for audience
   `https://ras.example/`, resource
   `https://api.example/tenants/acme-data/`, and scope `files.read`.
3. The IdP resolves `agent-42`, checks the Client Association and
   Alice's Delegation Authorization, and issues ID-JAG `grant-1`, valid
   for 300 seconds.
4. The client redeems `grant-1` at the RAS as `analysis-api`, with a
   fresh proof of the same key. The RAS correlates `agent-42`, resolves
   Alice to `user-108`, applies the actor gate, and issues the DPoP
   access token `access-1`, valid for 600 seconds, with no refresh
   token.
5. The client reads `/tenants/acme-data/files/report-7` with `access-1`
   and a new proof. The API checks the proof, the tenant, Alice's
   permissions, and the actor gate.
6. When `access-1` expires, the client obtains a new ID-JAG.

**Rejection tests.**

| Change | Expected result |
|---|---|
| The Client Association for `analysis-client` is disabled; the binding still resolves `agent-42` | The IdP returns HTTP 400 `actor_unauthorized` and issues no ID-JAG. Resolution succeeded; authorization to use it did not |
| Alice's Delegation Authorization for `agent-42` is withdrawn | The IdP returns HTTP 400 `actor_unauthorized` for Alice; the agent's grants for other users it may act for are unaffected |
| A delegated access token without `act` is presented to the API | HTTP 401 `invalid_token`; a missing `act` does not make the token self-acting |

**Containment and restoration.** Restore by undoing the action taken;
no other action clears it.

| Containment | Effect | Restore by |
|---|---|---|
| [Disable the agent everywhere](#disable-an-agent-everywhere) at the IdP | A fresh exchange for Alice fails with `invalid_grant`. Once lifecycle propagation reaches the RAS, redemption is denied and introspection reports `access-1` inactive | Setting the agent `active: true` at the IdP, and confirming the change has propagated to the RAS |
| [Local Suspension](#cut-one-agent-off-from-one-application) at the RAS | The RAS issues no new access token or refresh for `agent-42`. Activation at the IdP and new grants do not clear it | The resource owner lifting the suspension at the RAS |
| [Revoke `grant-1`](#revoke-one-suspicious-grant), where the RAS supports grant-derived revocation | Later redemption of `grant-1` is rejected and access derived from it is revoked; the agent stays enabled | The client obtaining a new grant; `grant-1` stays unusable |

Restoration is complete when a new grant is redeemed and the client
reads `report-7` again, not when the IdP accepts an exchange. Sessions
revoked in the meantime stay revoked. An API that validated `access-1`
offline, instead of introspecting it, would accept it until its 600
seconds end, whichever action was taken.

**Evidence to retain.** The drafts define no log format; as a
deployment convention, retain:

* the IdP's issuance record for `grant-1`: time, `alice-ras`,
  `agent-42`, `analysis-client` and its `client_id` `analysis-api`,
  resource, scope, and the Delegation Authorization it relied on;
* the RAS's record linking `grant-1` to `access-1`, `user-108`, and
  `agent-42`; and
* the API's record of the operation on `report-7`, with `access-1`.

The grant's `jti` joins the IdP's record to the RAS's, and the access
token's `jti` joins the RAS's to the API's.

**Limitations.**

* Tokens that an API validates offline or caches stay usable until they
  expire or the cache entry ends. Document the expected and maximum
  disablement delay.
* Current administrative state cannot reveal a missed
  disable-and-re-enable cycle.
* Each SaaS application is its own resource domain. Repeat the RAS and
  API configuration, the client registration association, and these
  tests for each one.

### Recipe: self-acting access

**Outcome.** `agent-42` runs a nightly data-quality job in `acme-data`
on its own authority, with no user. The recipe uses the same agent,
client, and resource domain as the delegated recipe, so the two differ
only in the acting relationship. An internal API changes who owns the
resource domain, not any step.

**Parties and owners.** As in the delegated recipe, without a user. The
identity team records the Agent Authorization; the application owner
decides what the local principal `service-principal-42` may do.

**Operating model.** Self-acting, alongside the delegated recipe, with
the same dedicated client, client registration, resource, and
protection choices. Because both token populations share a client
registration and an audience, the RAS and API need the additional
bilateral contract the core's implementation considerations describe
for that case. Here, the RAS records which acting relationship
authorized each access token and returns it in its authenticated
introspection response, under a member the two agree on; the drafts
define none. A deployment that wants no such contract, or whose API
validates access tokens offline, gives self-acting tokens a separate
client registration or audience instead, and configures the API with
that mapping.

**Configuration.**

* At the IdP: the same Identity Binding; a Client Association that
  permits `analysis-client` to use it for self-acting issuance,
  configured at the IdP directly; an Agent Authorization for `agent-42`
  with `files.read` at `https://api.example/tenants/acme-data/`; and
  the same client registration association.
* At the RAS: the local principal `service-principal-42`, correlated
  with (`https://idp.example/`, `agent-42`), and its permissions in
  `acme-data`; and the acting relationship recorded with each access
  token and returned on introspection.
* At the API: the acting relationship taken from the introspection
  response, then the agent's own permissions and tenant checks; no
  actor gate.

**One successful transaction.**

1. The client authenticates to the IdP with a fresh assertion, repeats
   it as the subject token, and requests a WAG for the same audience,
   resource, and scope, with a DPoP proof. It sends no user token and
   no actor token.
2. The IdP resolves `agent-42`, checks the self-acting Client
   Association and the Agent Authorization, and issues WAG `wag-1`.
3. The client redeems `wag-1` at the RAS. The RAS checks the grant's
   type, correlates `agent-42` to `service-principal-42`, and issues an
   access token with `sub` `service-principal-42`, no `act`, and no
   refresh token.
4. The API enforces `service-principal-42`'s permissions in `acme-data`.
5. When the access token expires, the client obtains a new WAG.

**Rejection tests.**

| Change | Expected result |
|---|---|
| The self-acting Client Association is disabled; the delegated one remains | The IdP returns HTTP 400 `unauthorized_client`, not `actor_unauthorized`, since no actor is asserted |
| The client requests a resource the Agent Authorization does not cover | The IdP returns HTTP 400 `invalid_target` |
| The RAS has no authorized correlation for `agent-42` in `acme-data` | The RAS rejects `wag-1` with HTTP 400 `invalid_grant` |
| With self-acting access enabled, the API receives a token from the delegated population that lacks `act` | HTTP 401 `invalid_token`, as before self-acting access was enabled; the token is not accepted as self-acting |

**Containment and restoration.**

* **Disablement and Local Suspension:** as in the delegated recipe,
  each restored only by undoing it. Disabling the agent stops its
  self-acting and delegated access together.
* **Stop only its own access:** withdraw or narrow the Agent
  Authorization. New WAGs for that target are refused, and tokens
  already issued run until they expire; Alice's delegation is
  unaffected. Restore the authorization to restore access.
* **Stop one grant:** revoking a single WAG is deployment-specific;
  grant-derived revocation covers ID-JAGs only.
* **Verify:** restoration is complete when a new WAG is redeemed and
  the job's API call succeeds.

**Evidence to retain.** As a deployment convention: the IdP's issuance
record for `wag-1` and the Agent Authorization it relied on; the RAS's
record linking `wag-1` to the access token and to
`service-principal-42`; and the API's records for
`service-principal-42`. The RAS's correlation joins the local principal
to (`https://idp.example/`, `agent-42`).

**Limitations.**

* A WAG yields no refresh token. Once the access token expires, the
  agent needs a WAG the RAS still accepts, under its validity, replay,
  and proof rules, or a new one from the IdP.
* The resource domain sees only the agent: no user is attributed, so
  review the Agent Authorization by agent.

### Variations

Each variation changes one of the recipes as stated; the rest holds.

#### Through a gateway

`agent-42` reaches a tool in another domain through an MCP gateway. Add
[continuation](#continuation-through-gateways): the gateway's
authorization server attests the agent's grant, and the IdP issues an
onward grant naming the same agent and user, with the gateway as
client. The tool sees the same agent; its API also sees the gateway in
`continuation_via` where the tool's RAS supports path disclosure.

Run the continuation checks in [step 4](#continuation-through-gateways),
which include containment: disabling the agent ends its chains, and
re-enabling it does not revive them. One limitation remains: once the
gateway's source hop passes its continuation window, continuation fails
with `invalid_grant`, even while the agent's access token at the
gateway is still accepted.

#### Scheduled work

`agent-42` prepares a daily report for Alice after she signs out. While
Alice is signed in, the client uses her refresh token once to establish
a chain anchored to that refresh token's grant; each run continues from
server-held task state with no retained user credential. This needs an
IdP that claims grant-anchored continuation, and a continuation-aware
authorization server at the agent's operator that holds the task
record. The continuation profile's [scheduled
variant][continuation-scheduled] shows the messages.

* **Extra test:** when Alice withdraws her Delegation Authorization for
  `agent-42`, the next run fails with `invalid_continuation`, and her
  delegations to other agents continue.
* **Containment:** revoking the refresh-token grant that anchors the
  chain also ends it.

#### A shared platform client

A platform runs many agents behind one OAuth client and presents its
existing platform JWT, which names the agent's workload. The IdP
resolves the agent from the JWT through an exact Identity Binding, and
a Client Association permits the shared client to use that binding. The
core's [AWS example][core-aws-example] shows the input.

* **Extra tests:** a platform JWT that fails validation is rejected
  with `invalid_grant`, with no retry from the client's authentication
  or another credential class; and a token the client holds for
  `agent-42` is not reused for another agent with the same scope.

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
| The gateway's source authorization server: the RAS that redeems the agent's grant and issues the access token the gateway receives | Continuation as continuation-aware RAS; and, for it or a separate issuer trusted for it, Continuation Assertion Issuer with assertion issuance at the token endpoint. Often the gateway operator's own, but possibly a separate one |

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
Every runbook uses the same fields:

| Field | Records |
|---|---|
| Trigger | What starts the runbook |
| Scope | Which agents, relationships, and resource domains it covers |
| Prerequisites | Authority, configuration, and information needed before acting |
| Owner | The team that acts, from [step 2](#2-assign-owners-and-record-the-decisions) |
| Action | The steps |
| Verification | How each step is shown to have taken effect |
| Residual access | What still works afterward, and until when |
| Recovery | How to restore what the action stopped |
| Completion evidence | What to keep as proof that the runbook finished |

Three rules apply to every runbook. A successful administrative write
or event acknowledgment is one checkpoint, not completion; completion
is verified where the access is enforced. Tokens that an API accepts
offline or from a cache stay usable until they expire or the cache
entry ends. Recovery undoes only the action taken: revoked sessions
stay revoked, and ended continuation chains stay ended.

### Disable an agent everywhere

* **Trigger:** the agent is compromised or misbehaving, and must stop
  everywhere at once.
* **Scope:** every binding, client, and resource domain of the agent;
  delegated and self-acting access; its continuation chains.
* **Prerequisites:** authority to change the Agent's `active` at the
  IdP; the resource domains provisioned with the agent, and each one's
  documented maximum disablement delay.
* **Owner:** identity team; each resource owner for their domain.
* **Action:**
  1. Set the Agent to `active: false` at the IdP. No new grant issues
     for it through any binding or client, and its continuation chains
     end.
  2. Confirm propagation to each resource domain, through lifecycle
     provisioning or a change notice that triggers reconciliation. Each
     resource domain's authorization server denies redemption and
     refresh and revokes the agent's sessions. A platform that hosts the
     agent denies new authorization and revokes its existing
     authorization.
  3. Where a domain has not applied the change within its agreed delay,
     apply a Local Suspension there as containment.
* **Verification:**

  | Checkpoint | Evidence |
  |---|---|
  | The IdP applied the disablement | A fresh exchange for the agent fails with `invalid_grant` |
  | Each participating RAS applied it | Redemption and refresh for the agent fail there |
  | API enforcement caught up | A previously accepted token is rejected within the agreed delay |
  | A domain has not applied it | Recorded as pending, with its owner and the containment applied |
  | Restoration is complete | Fresh authorization succeeds; revoked sessions and ended chains remain unusable |

* **Residual access:** grants already issued, at a domain that has not
  yet applied the change; tokens accepted offline or from a cache.
* **Recovery:** set `active: true` and confirm propagation. Clients
  obtain new grants.
* **Completion evidence:** the IdP's change record; each domain's
  applied status and time; the failed test exchange and redemption; any
  pending domain, with its containment.

### Cut one agent off from one application

* **Trigger:** the agent must stop in one resource domain, or for one
  target, and keep its other access.
* **Scope:** one resource domain through a Local Suspension, or one
  target through the agent's authorization at the IdP.
* **Prerequisites:** the resource owner's authority to suspend, or the
  identity team's authority to change the authorization.
* **Owner:** the resource owner for a Local Suspension; the identity
  team for the authorization.
* **Action:** either apply a Local Suspension at the RAS, or narrow the
  agent's Delegation or Agent Authorization so that it no longer covers
  that target. Withdraw the authorization as a whole only when the
  agent should lose all of it: withdrawal ends every chain rooted under
  it, for all targets.
* **Verification:** with a Local Suspension, the RAS issues no new
  access token or refresh for the agent, and activation at the IdP does
  not clear it. With narrowing, a new grant for that target is refused,
  continuation to it fails with `invalid_target`, and access to other
  targets still works.
* **Residual access:** tokens already issued for that application,
  until revocation or expiry.
* **Recovery:** the resource owner lifts the Local Suspension, or the
  identity team restores the authorization.
* **Completion evidence:** the suspension or authorization change; the
  refused request; a successful request to another target.

### Revoke one suspicious grant

* **Trigger:** one ID-JAG is suspected stolen or misused, and the agent
  should stay enabled.
* **Scope:** all authorization derived from that grant in one Target
  Tenant.
* **Prerequisites:** the RAS supports the lifecycle profile's optional
  grant-derived revocation, and the stream authorizes the IdP's issuer
  for it; the grant's issuer and `jti`.
* **Owner:** security operations, through the IdP's event transmitter.
* **Action:** send a CAEP `session-revoked` event naming the ID-JAG by
  issuer and `jti`.
* **Verification:** redemption of the grant is rejected, and sessions
  derived from it are invalidated. An event that arrives before
  redemption still makes later redemption fail. The agent stays
  enabled.
* **Residual access:** tokens accepted offline or from a cache. For
  access derived from a WAG, revoking one grant is deployment-specific.
* **Recovery:** none for that grant; the client obtains a new one.
* **Completion evidence:** the event and its delivery acknowledgment,
  and the RAS's record of the revoked grant by issuer, `jti`, and
  tenant.

### Respond to a compromised credential or key

* **Trigger:** a dedicated client's key, or a platform's signing key or
  credential authority, is exposed.
* **Scope:** resolution through that credential, for every agent bound
  to it; continuation chains rooted through it.
* **Prerequisites:** a replacement key; the bindings and clients that
  depend on the compromised one.
* **Owner:** platform engineering for the key; identity team for the
  IdP configuration.
* **Action:**
  * **A dedicated client's key:**
    1. Disable the OAuthClient. This blocks resolution through it and
       its use of every association.
    2. Retire the compromised key: remove it from the client's
       registration, so it cannot authenticate once the client is
       enabled again.
    3. Register a new key and re-enable the OAuthClient. Re-enabling
       does not re-enable an association or binding that was disabled
       separately; restore those explicitly.
  * **A platform's signing key or credential authority:**
    1. Retire the compromised key: remove it from the IdP's trust
       configuration for that issuer, or disable the Identity Bindings
       that rely on it.
    2. Configure the replacement key, and restore any bindings disabled
       in step 1.
* **Verification:** authentication with the retired client key fails
  with `invalid_client`, and a platform JWT signed with the retired key
  fails with `invalid_grant`; the new key resolves the agent again.
  Revoking the credential does not retire the Agent Principal, and an
  agent with other valid bindings keeps them.
* **Residual access:** grants already issued, until their short
  lifetimes end, and resource-domain tokens, until revoked or expired.
  If the exposure is broad, disable the affected agents or associations
  as well.
* **Recovery:** the replacement key is the recovery. Chains rooted
  through the revoked credential stay ended; clients obtain new grants
  with the new key.
* **Completion evidence:** the key retirement and replacement records;
  the failed attempt with the old key and the successful one with the
  new key.

### Offboard a user

* **Trigger:** a user leaves.
* **Scope:** that user's delegations; agents' self-acting authority is
  unaffected.
* **Prerequisites:** the IdP's own user lifecycle.
* **Owner:** identity team.
* **Action:** disable the user through the IdP's user lifecycle.
* **Verification:** a new delegated exchange for that user fails with
  `invalid_grant`, and the user's delegated chains end; agents still
  obtain grants for their own access.
* **Residual access:** delegated tokens already issued for the user,
  until revoked or expired. Where a resource domain is configured for
  CAEP user-and-tenant revocation, an event can revoke those sessions.
* **Recovery:** re-enabling the user permits new delegations; ended
  chains stay ended.
* **Completion evidence:** the user's disablement record and the
  refused exchange.

### Handle an ownerless agent

* **Trigger:** an agent's owner leaves, or a review finds an Agent
  Principal with no owner.
* **Scope:** accountability for one agent. Owners are accountable for
  an agent but are not its delegators, so no authorization changes.
* **Prerequisites:** a policy stating whether an agent may operate
  without an owner, and for how long.
* **Owner:** identity team, with the agent's platform team.
* **Action:** assign a new owner; in SCIM management, the Agent's
  `owners` attribute. If no owner is assigned within the policy's
  period, [disable the agent everywhere](#disable-an-agent-everywhere).
* **Verification:** the new owner is recorded, and the agent's bindings,
  associations, and authorizations are unchanged.
* **Residual access:** none from this runbook; ownership confers no
  authority.
* **Recovery:** reassign the owner, and re-enable the agent if policy
  disabled it.
* **Completion evidence:** the management audit record of the change:
  the administrative actor, Provisioning Domain, affected resource, and
  changed attribute.

### Recover from lost event delivery

* **Trigger:** a lifecycle event stream reports delivery failures,
  falls behind, or is reconfigured, or periodic reconciliation finds
  state that differs from the source.
* **Scope:** the resource domains on that stream, the applied state of
  their agents, and any grant revocations sent while delivery failed.
* **Prerequisites:** the source SCIM service and retrieval authority
  configured for reconciliation; the deployment's documented reliance
  on local state during a source outage.
* **Owner:** each resource domain's operator for reconciliation; the
  identity team for the transmitter.
* **Action:**
  1. Reconcile every managed agent by retrieving its current state from
     the source. A change notice triggers retrieval, never activation.
     A failed or partial retrieval leaves reconciliation incomplete; it
     is never a deletion.
  2. Keep each failed reconciliation pending and retry it; an
     acknowledgment does not discard pending work. An authenticated
     deactivation or deletion event may have caused a provisional Local
     Suspension, which successful reconciliation can clear under local
     policy. It never clears an independent Local Suspension.
  3. Resend any grant revocation whose delivery is unconfirmed, under
     the transport's acknowledgment rules. Revocations are not SCIM
     state, so reconciliation cannot recover them. If the grant's
     derived authorization must stop before delivery is confirmed,
     disable the agent or apply a Local Suspension instead.
  4. Where a disable-and-re-enable cycle may have been missed, current
     state cannot show it. If sessions from before the gap must not
     survive, disable and re-enable the agent so that each domain
     revokes them.
* **Verification:** each agent's applied state matches the source; no
  reconciliation remains pending; each resent revocation is recorded by
  the receiver.
* **Residual access:** during the gap, a disablement not yet applied in
  a domain did not stop redemption, refresh, or sessions there.
* **Recovery:** this runbook is the recovery. Review access during the
  gap with the [audit trace](#audit-evidence).
* **Completion evidence:** the reconciliation report (agents checked,
  changes applied, items still pending), the resend records, and the
  start and end of the gap.

### Retire an agent

* **Trigger:** the agent is no longer needed.
* **Scope:** the Agent Principal everywhere: its bindings, associations,
  authorizations, OAuth clients used only by it, and local records.
* **Prerequisites:** the owner's approval; the resource domains and
  platforms that hold the agent.
* **Owner:** identity team, with the agent's owner.
* **Action:**
  1. [Disable the agent everywhere](#disable-an-agent-everywhere), and
     confirm that each domain applied it. Deletion prevents new grants
     but revokes nothing, so disablement comes first.
  2. Delete the Agent at the IdP. In SCIM management, its bindings and
     associations then become unusable; delete them as well, or let an
     authorized cascade remove them, along with any OAuth client that
     only this agent used.
  3. Remove its local records in each resource domain.
* **Verification:** no grant issues for the agent. A later registration
  with the same platform identifier is a new creation, with a new SCIM
  `id` and a new Agent Principal; the IdP never reuses either.
* **Residual access:** tokens accepted offline or from a cache.
* **Recovery:** none. A replacement agent is a new principal, with new
  relationships and authorizations.
* **Completion evidence:** each domain's applied disablement, the
  deletion records, and the agent's absence from the next
  certification. Deleting a local record alone does not show that the
  IdP retired the agent.

### Roll back an onboarding

* **Trigger:** onboarding fails partway, or acceptance tests fail and
  the integration must be undone.
* **Scope:** what was created for the agent: the Agent, its bindings and
  associations, client registrations, authorizations, local records,
  and any tokens issued.
* **Prerequisites:** the onboarding record of what was created, with
  each resource's SCIM `id` or `externalId`.
* **Owner:** platform engineering for the connector's writes; identity
  team for authorizations.
* **Action:**
  1. If the agent was enabled and any grant was issued, [disable it
     everywhere](#disable-an-agent-everywhere) first. An onboarding
     staged inactive, as the SCIM management profile allows, needs only
     deletion.
  2. If a creation response was lost, find the resource by its
     `externalId` before retrying or deleting. A repeated create is not
     idempotent, and a `409` `uniqueness` conflict is not success until
     the existing resource is retrieved and compared.
  3. Delete what was created. Dependents remain as unusable references
     unless their deletion is authorized; remove them too.
  4. Withdraw the authorizations, and remove client registrations and
     local records created only for this agent.
* **Verification:** queries by `externalId`, and filtered reads for
  references, find nothing left; no grant issues for the agent.
* **Residual access:** tokens issued during the attempt, until
  disablement is applied or they expire.
* **Recovery:** onboarding again is a new creation, with new SCIM `id`s
  and a new Agent Principal.
* **Completion evidence:** the deletion records and the empty query
  results.

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
[core-walkthrough]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#walkthrough
[core-aws-example]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#aws-example
[continuation]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html
[continuation-scheduled]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-scheduled
[lifecycle]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html
[management]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-agent-federation.html
[guide-authzen]: IMPLEMENTERS-GUIDE.md#authorization-decisions-with-authzen
[guide-risk]: IMPLEMENTERS-GUIDE.md#risk-signals
