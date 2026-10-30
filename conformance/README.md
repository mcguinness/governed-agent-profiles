# Conformance suite: the mandatory delegated path

This directory holds executable positive and negative tests for one
interoperable path through the core profile, and a reference
implementation to run them against. The path is the mandatory
interoperability path for delegated access in the core's [Conformance
Claims][core-scope], under the bound profile, as
[EXAMPLES.md](../EXAMPLES.md) scene 2 traces it:

* a dedicated client authenticating with `private_key_jwt`;
* an ID Token as the subject token;
* bound governed agent access, with DPoP at the IdP and the RAS;
* a DPoP-bound JWT access token, validated at the API.

It also holds tests of the oversight companion's deferred redemption at
the reference RAS ([Deferred redemption at the
RAS](#deferred-redemption-at-the-ras)), and of the core's Optional
Policy Services, error selection order, self-acting access and
introspection at the reference API ([Policy services at the
API](#policy-services-at-the-api)).

The drafts define every requirement. The suite tests a subset of them,
and passing it is evidence for that subset only, not a conformance claim.

* [Run](#run)
* [Cases](#cases)
* [Deferred redemption at the RAS](#deferred-redemption-at-the-ras)
* [Policy services at the API](#policy-services-at-the-api)
* [What the suite does not cover](#what-the-suite-does-not-cover)
* [Running against another implementation](#running-against-another-implementation)
* [Configuration the reference assumes](#configuration-the-reference-assumes)
* [Draft questions found while implementing](#draft-questions-found-while-implementing)

## Run

The suite needs Python 3 and one package, `cryptography`:

```sh
python3 -m venv .venv-conformance
.venv-conformance/bin/pip install -r conformance/requirements.txt
.venv-conformance/bin/python conformance/run.py --vacuity
```

`run.py` starts the reference IdP, RAS and API on localhost ports, plays
the client, and prints one line per case. `--vacuity` then runs every
case that cites reference checks once for each check, with that check
switched off, prints why the case failed, and fails if it still passes. `--list` prints each case's source and
the test-control capabilities it needs. The exit status is non-zero on
any failure.

The reference servers use the example identifiers: `https://idp.example/`,
`https://ras.example/` and `https://api.example` are the issuer and
origin values in tokens, client assertions and DPoP proofs, while the
servers listen on localhost. A reader can lay the output beside
[EXAMPLES.md](../EXAMPLES.md) scene 2.

## Cases

| Case | Role | Checks that | Source | Test control |
|---|---|---|---|---|
| P1 | IdP | The ID-JAG names the user in the RAS namespace, the agent in `act`, the RAS registration as `client_id`, and the grant key in `cnf.jkt`, lives no longer than the configured limit (`max_grant_lifetime`, 300 s by default) or the ID Token, and is noted if it exceeds the recommended 300 s | core: Actor Resolution and Construction; Grant Issuance; Common Grant Claims | None |
| P2 | RAS | The access token is DPoP-bound to the same key, names the local user, and carries `act` unchanged; a refresh token is noted, not failed | core: Actor Preservation; Access Token Issuance and Response | None |
| P3 | API | A read with the access token and a fresh proof succeeds | core: Token Validation; Delegated Access | None |
| P4 | API | An access token typed `application/at+jwt`, with a one-element `aud` array, is accepted | RFC 9068 Sections 2.1 and 4; core: Token Validation | Mint an access token |
| N01 | IdP | A reused client assertion fails with `invalid_client` | core: Dedicated Client Identity (Replay); negative-test row for the nonce retry | None |
| N02 | IdP | A client assertion addressed to the token endpoint URL fails with `invalid_client` | core: Dedicated Client Identity (Audience) | None |
| N03 | IdP | An exchange without a DPoP proof under the bound profile fails with `invalid_request` | core: Grant Protection | None |
| N04 | IdP | Two `resource` parameters fail with `invalid_target` | core: Token Exchange Request | None |
| N05 | IdP | An ID Token issued to another client fails with `invalid_grant` | core: Subject Token Validation | ID Token for another audience |
| N06 | IdP | A disabled Identity Binding fails with `invalid_grant` | core: negative-test row | Disable the binding |
| N07 | IdP | A disabled Agent Principal fails with `invalid_grant` | core: Issuance Errors; PLAYBOOK runbook | Disable the agent |
| N08 | IdP | No Client Association fails with `actor_unauthorized` | core: negative-test row | Remove the association |
| N09 | IdP | A withdrawn Delegation Authorization fails with `actor_unauthorized` | core: Delegation Authorization; Issuance Errors; PLAYBOOK recipe | Withdraw the delegation |
| N10 | RAS | A grant without `cnf` under the bound profile fails with `invalid_grant` | core: negative-test row | Let the IdP issue unbound grants |
| N11 | RAS | A bound grant redeemed without a proof fails with `invalid_grant` | core: negative-test row; Access-Token Protection | None |
| N12 | RAS | A redemption proven with another key fails with `invalid_grant` | core: Grant Protection | None |
| N13 | RAS | A grant redeemed by a client other than its `client_id` fails with `invalid_grant` | core: Redemption Request; ID-JAG Section 4.4.1 | None; needs a second RAS client |
| N14 | RAS | A `resource` parameter other than the grant's fails with `invalid_target` | core: Common Grant Validation | None |
| N15 | RAS | A grant for an agent disabled at the RAS fails with `invalid_grant` | core: Agent Principal Correlation; Applied Disablement and Revocation; Redemption Errors | Disable the agent at the RAS |
| N16 | RAS | An agent the RAS's policy does not let act for the user fails with `actor_unauthorized` | core: Delegated Actor Authorization; Redemption Errors | Close the actor gate at the RAS |
| N17 | API | An access token used in another tenant, with a fresh proof, fails with 401 `invalid_token` | core: negative-test row | None; needs a second tenant |
| N18 | API | A delegated-population token without `act` fails with 401 `invalid_token` | core: negative-test row; Profile Applicability | Mint an access token |
| N19 | API | A request proven with another key fails with 401 `invalid_token` | core: Token Validation; RFC 9449 Section 7.1 | None |
| N20 | API | A closed actor gate fails with 403 `actor_unauthorized`, not `insufficient_scope` | core: Error Responses | Close the actor gate at the API |
| N21 | IdP | An ID Token whose `iat` is an hour ahead fails with `invalid_grant` | core: Time, Replay, and Key Validation | ID Token with chosen claims |
| N22 | IdP | A client assertion whose `nbf` is an hour ahead fails with `invalid_client` | RFC 7523 Section 3; core: Time, Replay, and Key Validation | None |
| N23 | RAS | A grant whose `nbf` is an hour ahead fails with `invalid_grant` | RFC 7523 Section 3; core: Time, Replay, and Key Validation | Mint a grant |
| N24 | API | An access token whose `iat` is an hour ahead fails with 401 `invalid_token` | core: Time, Replay, and Key Validation; RFC 9068 Section 4 | Mint an access token |
| N25 | IdP | A request for `files.write`, when the delegation permits only `files.read`, fails with `invalid_scope` | core: Issuance Authorization; Issuance Errors | Set the delegation's scope |
| N26 | RAS | A grant whose `scope` claim is missing, empty or an array fails with `invalid_grant` | core: Common Grant Validation | Mint a grant |
| N27 | RAS | A grant whose `act` names `agent-99`, which the RAS has no correlation for, fails with `invalid_grant` | core: Agent Principal Correlation; Redemption Errors | Mint a grant |
| N28 | IdP | A request for `files.write`, which the delegation permits but policy categorically prohibits for the agent, fails with `actor_unauthorized` | core: Issuance Authorization; Issuance Errors | Set the delegation's scope; prohibit a scope for the agent |
| D01 | RAS | Without `completion_mode=deferred`, a redemption that needs approval fails with `actor_unauthorized` and carries no deferral code | oversight: Redemption Opt-In; core: Redemption Errors | Require approval |
| D02 | RAS | A deferred redemption stays `authorization_pending` until approved, then issues an access token like P2's, expiring within `approved_until`, that the API accepts; a second poll fails with `invalid_grant` | oversight: Deferring a Redemption; Redemption Resolution | Require approval; approve |
| D03 | RAS | A poll proven with another key fails with `invalid_dpop_proof` | oversight: Deferring a Redemption | Require approval |
| D04 | RAS | With a 24 h maximum pending lifetime and an 8 h absolute expiration, `expires_in` is at most 8 h, and an approval after 9 h finds `expired_token` | oversight: Deferring a Redemption | Require approval; set both lifetimes; approve; advance the clock |
| D05 | RAS | An agent disabled while pending gets `access_denied` at the poll after approval | oversight: Redemption Resolution | Require approval; disable the agent at the RAS; approve |
| D06 | RAS | After a denial, the poll gets `access_denied` and the grant presented again gets `invalid_grant` | oversight: Recovery; Redemption Resolution | Require approval; deny |
| D07 | RAS | While pending, the grant presented without the opt-in fails with `invalid_grant` | oversight: Recovery; Deferring a Redemption | Require approval |
| D08 | RAS | For an unbound grant, a repeated request gets the same deferral code and an `expires_in` no greater than the first; the same request with another key fails with `invalid_grant` | oversight: Recovery | Require approval; let both the IdP and the RAS accept unbound grants |
| D09 | RAS | After approval, a repeated request gets the same deferral code and no token, and the poll then issues | oversight: Recovery | Require approval; approve |
| D10 | RAS | A second agent's grant through the same client, for the same user, resource and scope, gets its own deferral code and access request; approving the first leaves it pending | oversight: Approval Binding | Require approval; mint a grant; approve |
| D11 | RAS | When the Access Request Service answers the second request with the first one's approval, the second stays `authorization_pending` | oversight: Approval Binding | Require approval; mint a grant; approve; substitute |
| D12 | RAS | An approval narrowed from `files.read files.write` to `files.read` yields `scope` `files.read` in the response and the token, in any order | oversight: Redemption Resolution | Require approval; mint a grant; approve |
| D13 | RAS | With an approval expiry 300 s ahead, the access token expires within it, and a refresh after it fails with `invalid_grant` | oversight: Redemption Resolution; Refresh and Continuation | Require approval; permit refresh; approve; advance the clock |
| D14 | RAS | A refresh after the approval is revoked fails with `invalid_grant` | oversight: Refresh and Continuation | Require approval; permit refresh; approve; revoke; advance the clock |
| D15 | RAS | A shorter approval expiry returned at one refresh bounds that token and the next | oversight: Approval Binding; Refresh and Continuation | Require approval; permit refresh; approve; shorten |
| D16 | RAS | Two identical requests sent together get one deferral code, and one access request is opened | oversight: Recovery | Require approval; list tasks |
| D17 | RAS | After the grant's `exp`, a repeated request gets the same deferral code with the remaining `expires_in`, and the approval then issues | oversight: Recovery | Require approval; approve; advance the clock |
| D18 | RAS | A repeated request that reuses the first request's DPoP proof fails with `invalid_dpop_proof` | oversight: Recovery; RFC 9449 Section 11.1 | Require approval |
| D19 | RAS | After a token response redeems the code, a repeated request fails with `invalid_grant` | oversight: Recovery | Require approval; approve |
| D20 | RAS | An agent whose correlation changes to another local principal while pending gets `access_denied` at the poll after approval | oversight: Redemption Resolution; core: Agent Principal Correlation | Require approval; change the agent's local principal at the RAS; approve |
| D21 | RAS | After an unbound grant's deferred redemption, raising the client's minimum to the bound profile makes the next refresh fail with `invalid_grant` | oversight: Refresh and Continuation; core: Optional RAS Refresh Tokens (step 3) | Require approval; permit refresh; set the governed profile; approve |
| D22 | RAS | A refresh with another key is rejected and the next refresh still succeeds; a refresh rejected on re-evaluation ends the authorization, so restoring the actor gate does not revive it | oversight: Refresh and Continuation (ending the refresh authorization) | Require approval; permit refresh; approve; close and reopen the actor gate |
| S01 | API | Through the policy service, the positive path's read succeeds, and the evaluation names the user `user-108` as subject, the agent from `act`, the client `analysis-api`, the tenant `acme-data`, and `files.read` in the token constraints | core: Optional Policy Services; Delegated Access | Turn on the policy service; set its policy; read its evaluations |
| S02 | API | A request attribute naming `agent-77`, which policy permits instead of `agent-42`, fails with 403 `actor_unauthorized`, not `insufficient_scope` | core: Optional Policy Services; negative-test row for a policy service; Error Responses | Turn on the policy service; set its policy |
| S03 | API | When policy permits only `agent-42`, another agent's access token with the same `client_id` fails with 403 `actor_unauthorized`, and `agent-42`'s succeeds | core: Delegated Actor Authorization; negative-test row for the platform JWT variant's policy | Turn on the policy service; set its policy; mint an access token |
| S04 | API | A request attribute naming another user, whom policy permits instead, fails with HTTP 403, a challenge without an `error` attribute, neither `actor_unauthorized` nor `insufficient_scope`, and none of the file's data | core: Optional Policy Services; Error Responses | Turn on the policy service; set its policy |
| S05 | API | A request attribute naming another OAuth client, `other-api`, which policy permits instead, fails as S04 does | core: Optional Policy Services; Error Responses | Turn on the policy service; set its policy |
| S06 | API | With an `acme-data` token on the `acme-data` path, a request attribute naming tenant `beta-data`, which policy permits instead, fails as S04 does | core: Optional Policy Services; Token Validation (Tenant); Error Responses | Turn on the policy service; set its policy |
| S07 | API | With a `files.read` token, a request attribute naming `files.admin`, which policy requires, fails with HTTP 403 `insufficient_scope` and none of the file's data | core: Optional Policy Services; Error Responses | Turn on the policy service; set its policy |
| S08 | API | A self-acting token is served with the API's actor gate closed, and through the policy service, whose evaluation has the local agent principal as subject and names no user | core: Self-Acting Access; Optional Policy Services; Profile Applicability | Mint an access token; close the actor gate at the API; turn on the policy service; set its policy; read its evaluations |
| S09 | API | For a self-acting token, a request attribute naming `service-principal-77`, which policy permits instead, fails as S04 does | core: Optional Policy Services; Self-Acting Access; Error Responses | Mint an access token; turn on the policy service; set its policy |
| S10 | API | An opaque DPoP-bound token is introspected and served, and the evaluation takes the user, the unchanged `act` and the client from the introspection response | core: Optional Opaque Access Tokens and Introspection; Optional Policy Services | Mint an opaque token; turn on the policy service; set its policy; read its evaluations |
| S11 | API | For an opaque token, a request attribute naming `agent-77`, which policy permits instead, fails with 403 `actor_unauthorized` | core: Optional Policy Services; Optional Opaque Access Tokens and Introspection | Mint an opaque token; turn on the policy service; set its policy |
| S12 | API | An introspection response with `active` false fails with 401 `invalid_token` | core: Optional Opaque Access Tokens and Introspection; RFC 7662 Section 2.2 | Mint an opaque token |
| S13 | API | A delegated-population introspection response without `act` fails with 401 `invalid_token` | core: Optional Opaque Access Tokens and Introspection; Profile Applicability | Mint an opaque token; have the RAS leave `act` out of introspection |
| S14 | API | When policy requires `files.admin`, which the token lacks, and categorically prohibits the agent, the request fails with 403 `actor_unauthorized`, not `insufficient_scope` | core: Error Responses; Optional Policy Services | Turn on the policy service; set its policy |
| S15 | API | When the actor gate and the user's permission both deny, the request fails with 403 `actor_unauthorized` | core: Error Responses; Optional Policy Services | Turn on the policy service; set its policy |
| S16 | API | A request proven with another key, which policy would also deny, fails with 401 `invalid_token`, not 403 | core: Error Responses; Token Validation; RFC 9449 Section 7.1 | Turn on the policy service; set its policy |
| S17 | API | When the policy service cannot be reached, the request gets HTTP 503, none of the file's data and no denial code; a missing `Retry-After` is noted | core: Error Responses; Optional Policy Services | Turn on the policy service; set its policy; make it unavailable |
| S18 | API | When the actor gate denies and the evaluation of the user's permissions cannot complete, the request gets HTTP 403 `actor_unauthorized`, since no unfinished check comes earlier | core: Error Responses; Optional Policy Services | Turn on the policy service; set its policy; make the `other` condition unavailable |
| S19 | API | When the actor gate cannot be evaluated and the user's permission denies, the request gets HTTP 503, since the unfinished actor gate could come earlier | core: Error Responses; Optional Policy Services | Turn on the policy service; set its policy; make the `actor` condition unavailable |

The "negative-test row" sources are the rows of the core's "Renewal and
Negative Tests" table. N15 and N27 assert `invalid_grant`, which the
core's Redemption Errors assigns to an ID-JAG whose `act` agent has no
authorized correlation or is disabled. N16 asserts `actor_unauthorized`,
which Redemption Errors assigns when RAS policy refuses a valid
ID-JAG's delegation. N25 and N28 send a single scope, so they do not
depend on whether the IdP narrows a request, which Issuance
Authorization permits but does not require. The time cases use an hour,
well beyond the few minutes of skew the core contemplates, so they do
not depend on one implementation's tolerance.

The suite fails a case only for a departure from a requirement. A
departure from a recommendation, such as a grant longer than five
minutes, a 401 challenge without an `error` parameter, or a 503 without
`Retry-After`, is printed as a note. An HTTP 403 is different: under the
core's Error Responses, a 403 challenge without an `error` attribute is
the response for a denial other than the actor gate or token authority.
A case that expects `actor_unauthorized` or `insufficient_scope` at the
API (N20, S02, S03, S07, S11, S14, S15 and S18) therefore requires the code,
in the challenge's `error` attribute or, where the challenge has none,
in the body.

Every negative case, P2 and D02 name the reference checks they exercise
(`CHECKS` in [reference.py](reference.py)). With `--vacuity`, each of
these 66 cases runs once for each check it names, with that check
switched off; five S cases name two checks, so there are 71 runs, and
every run fails. Twenty-six N cases fail because the server then accepts
the request. P2 fails because the access token then carries a rewritten
`act`. N11 fails because the RAS's access-token protection check then
rejects the redemption with `invalid_request`; Access-Token Protection
states that Grant Protection's checks come first, so `invalid_grant` is
the required code, and the case no longer depends on the reference's
own order. N27 fails because the RAS's actor gate then refuses the
uncorrelated agent with `actor_unauthorized`, the code Redemption Errors
keeps for RAS policy that refuses a valid ID-JAG's delegation.

The D cases fail without their check in these ways:

* the RAS issues a token it must not: D01, D02 (a second token), D05,
  D11, D14, D20, D21 and D22 (after the actor gate reopens);
* it returns or keeps a deferral where an error is required: D03, D06
  (a new deferral after the denial), D08, D18 and D19;
* it returns another error: D07 (`actor_unauthorized`);
* it exceeds a bound: D04 and D17 (`expires_in`), D12 (`scope`), D13
  and D15 (the token's `exp`);
* it opens one access request for two redemptions (D10), or two
  pending redemptions for one grant (D16).

D09 is a positive case and names no check.

Without these checks, the S cases fail because the API then serves the
file (HTTP 200):

* S02, S04 to S07, S09 and S11 (`api.policy_source`): the request
  attribute replaces the token's value in the evaluation, and policy
  permits that value;
* S03 (`api.agent_from_token`): the API takes the agent from the client
  registration, so the other agent's token is evaluated as `agent-42`;
* S12 (`api.introspection_active`): the API reads the members of an
  inactive response;
* S13 (`api.introspection_act`): without `act`, the API applies no
  actor gate, as if the token were self-acting.

Without these, they fail on the response the API selects:

* S04 to S07 and S09 (`api.denial_codes`): the API returns
  `actor_unauthorized` for every denial of a delegated token, and
  `insufficient_scope` for every denial of a self-acting one, so S04 to
  S06 and S09 find an `error` attribute, and S07 finds
  `actor_unauthorized`;
* S14 and S15 (`api.error_order`): the API reports the failing
  conditions in reverse order, so S14 gets `insufficient_scope` and S15
  gets a 403 without a code;
* S16 (`api.key_binding`): the API accepts the proof and reports the
  policy denial, HTTP 403 `actor_unauthorized`;
* S17 (`api.evaluation_unavailable`): the API treats the unreachable
  policy service as a denial, HTTP 403;
* S18 (`api.established_failure`): the API evaluates every condition
  and answers HTTP 503 whenever one cannot complete, even after the
  actor gate has denied;
* S19 (`api.incomplete_outranks`): the API passes over the unfinished
  actor gate and reports the user's denial, HTTP 403 without a code.

S01, S08 and S10 are positive cases and name no check.

## Deferred redemption at the RAS

The D cases test the oversight companion's Deferred Redemption at the
reference RAS. In each of them, RAS policy requires approval for the
requested scope. They follow the companion's "Deferred redemption
negative test cases" table, and add a positive flow (D02) and a
recovery after approval (D09). D17 also covers the table's row in which
the grant's `exp` passes while the redemption is pending and the
approval then issues.

**Test-controlled Access Request Service.** The reference RAS opens one
task for each pending redemption in an Access Request Service of its
own, which test control decides. The suite can list the tasks, approve
one until an `approved_until` (optionally narrowing the scope), deny
one, revoke an approval, have the next re-evaluation of an approval
return a shorter `approved_until`, and have the service answer one
task's status with another task's result. The RAS keeps each approval
as the complete object it received (`id`, `approved_until`,
`approved_at`, and any `state`) and keeps a shorter deadline apart from
it, as its enforcement deadline.

**Clock control.** Test control advances each server's clock. The
suite's client advances its own clock with them, so DPoP proofs and
client assertions stay fresh, and no case sleeps. D04 advances nine
hours; D13, D14 and D17 advance some minutes.

**Reference-implementation tests.** A case that approves, denies,
revokes, shortens or substitutes needs control of the implementation's
Access Request Service, and a clock case needs control of its clock. A
third party cannot exercise those through the token endpoint, so these
are tests of the reference implementation, not black-box conformance
cases. Another implementation can run them only through an adapter that
provides the hooks ([Running against another
implementation](#running-against-another-implementation)). D01, D03,
D07 and D18 need only configuration: a RAS that requires approval for
the scope. D08 also needs an IdP and a RAS that accept unbound grants.

Some cases depend on choices made for the reference:

* D10 and D11 need a second agent, `agent-43`, for the same user. Its
  ID-JAG comes from the IdP's `mint_grant` test control, for the same
  RAS client, resource and scope. This stands for a shared client's
  issuance, which the reference IdP does not implement. D12 mints a
  grant for `files.read files.write` the same way, because the
  reference Delegation Authorization covers `files.read` only.
* D13 uses an approval expiry 300 s ahead, shorter than the 600 s
  access-token lifetime, so that the bound changes the token. The
  companion's row uses one hour, which any 600 s token meets. D15 uses a
  shorter expiry 120 s ahead, returned at one re-evaluation only, so the
  second refresh shows that the RAS kept it.
* D08 uses an unbound grant. For a bound grant, a proof of another key
  already fails Grant Protection, so the recovery match would not be
  what refuses it.
* D11 asserts `authorization_pending`, as Approval Binding says.

## Policy services at the API

The S cases test the core's Optional Policy Services at the reference
API: when the API delegates authorization evaluation to a policy
decision service, it takes the user, the Agent Principal, the OAuth
client, the tenant and the token constraints only from the validated
access token or an authenticated introspection response, and trusted
configuration. Attributes derived from the request never supply or
override them. S02 and S03 are the core's negative-test rows for the
API's policy: the request attribute naming `agent-77`, and the platform
JWT variant's two agents with one `client_id`. S04 to S13 cover each
member, self-acting access, and introspection.

The S cases also test the core's Error Responses. When several checks
fail, the API reports the first in this order: the token and proof
(HTTP 401), the token context (HTTP 401 `invalid_token`), the actor gate
(HTTP 403 `actor_unauthorized`), token authority (HTTP 403
`insufficient_scope`), and any other denial (HTTP 403 with a challenge
that carries no `error` attribute). An evaluation that cannot complete
is not a denial: HTTP 503. S04 to S07 and S09 each fail one condition
after the actor gate; S14 to S16 fail two conditions at once; S17 makes
the policy service unavailable; S18 and S19 make one condition's
evaluation fail beside a denial, so that an established failure is
reported only when no unfinished check comes earlier.

**Test fixtures.** The policy service and the API's introspection
caller are test fixtures under the suite's control. The policy service
runs in the API's process. When test control turns it on, it replaces
the API's own user-permission and actor-gate evaluation; token
validation, DPoP, applicability and the tenant check still run first,
and the API still requires the token's scope for the read, so a permit
never overrides the token's constraints. Test control sets its policy,
makes it unavailable, and reads the evaluation requests it received.
The S cases are reference-implementation tests, not black-box
conformance cases, and passing them claims nothing about a real policy
decision point integration.

**Policy and decisions.** The policy is a document whose members each
list what policy permits: the actor gate's (user, agent, tenant)
entries, categorical prohibitions of an agent for an action, the scope
each action requires, the user's own permissions, a self-acting agent's
own permissions, and the allowed clients and tenants. The service
evaluates three conditions in the order the API asks for and returns
the first that fails as the decision's reason: the actor gate (delegated
access only), then the required scope, then the rest. The API merges
that reason with its own scope check, reports the first in the order,
and maps it to `actor_unauthorized`, to `insufficient_scope` with the
required scope, or to a DPoP challenge without an `error` attribute and
an empty JSON body. A decision it cannot interpret, or an unreachable
service, gets HTTP 503 with `Retry-After`. The API's own evaluation,
without the service, uses the same order.

**Evaluation requests.** The API's request follows the implementer's
guide's [illustrative AuthZEN
requests](../IMPLEMENTERS-GUIDE.md#illustrative-requests): `subject`,
`action` and `resource`, with `agent`, `client`, `tenant` and
`constraints` (`scope` and `aud`) in `context`. For self-acting access
the subject is the local agent principal and there is no `agent`
member. The drafts define no AuthZEN mapping; this shape is the
reference's own.

**Request attributes.** The API accepts the query parameters `agent`,
`user`, `client_id`, `tenant` and `scope` on a file read. They stand in
for a tool call's arguments; the drafts define no such parameters. The
API passes every query parameter to the policy service unchanged, in
`context.request` and nowhere else.

**Self-acting tokens.** The API configures a separate client
registration, `analysis-agent-client`, as the self-acting population for
the `acme-data` resource, as Profile Applicability permits. Its tokens
name the local agent principal `service-principal-42` as `sub` and carry
no `act`. The RAS mints them through test control; the reference has no
WAG issuance or redemption.

**Introspection.** The RAS answers RFC 7662 introspection at
`/introspect` to a caller that authenticates with HTTP Basic, and
rejects any other caller with 401 `invalid_client`. The API holds its
own credential, generated at start, and calls the RAS over HTTP at the
RAS's localhost transport whenever the presented token is not a JWS.
The RAS mints opaque tokens only through test control. The API treats
the response as validated claims: it rejects `active` false, applies
applicability and the `act` requirement, binds the DPoP proof to
`cnf.jkt`, and takes the tenant from `aud`. Nothing caches a response,
and the suite tests no freshness limit.

Some cases depend on choices made for the reference:

* Each S case's policy permits the positive path in both tenants and
  changes one member. S04 lets the actor gate permit both `user-108`
  and `user-109`, so that `user-108`'s denial comes from the user's own
  permission and not from the gate. S06's gate and user permissions
  cover both tenants, so that the request attribute naming `beta-data`
  would succeed if it replaced the token's tenant.
* S14 makes the actor gate fail through a categorical prohibition of
  `agent-42`, and S15 through an actor gate with no entry for it, so the
  two cases cover both forms.
* S03 mints the other agent's token, for `agent-43`, with the same
  `client_id` as `agent-42`'s. It stands for the platform JWT variant's
  shared client.
* S08 first reads with the API's own evaluation and its actor gate for
  `agent-42` closed, to show that no actor gate applies, and then reads
  through the policy service.
* For S12, the RAS returns the token's members with `active` false.
  RFC 7662 Section 2.2 discourages that but permits it, and it gives an
  API that ignores `active` something to accept. For an unknown or
  expired token, the RAS returns only `active`.
* S12 and S13 test introspection processing and leave the policy
  service off.
* `api.introspection_auth` is not a check. An API that stopped
  authenticating would be refused by the RAS on every introspection, so
  no case could observe it accepting an unauthenticated response.

## What the suite does not cover

The suite tests nothing outside the path above, including:

* governed agent access with unbound grants, except as the setup for N10
  and D08;
* existing platform JWTs and the inputs of the inputs draft;
* WAG issuance and redemption, including deferred WAG redemption, the
  removal of a pending WAG redemption's correlation, and the WAG rows of
  Redemption Errors; self-acting access at the API is covered only with
  minted tokens (S08 and S09);
* introspection beyond the API's processing in S10 to S13: the RAS's
  own introspection responses, caching and freshness limits,
  `authorization_details`, certificate-bound tokens, and opaque tokens
  issued by a redemption;
* a real policy decision point, and policy services at the IdP or the
  RAS;
* the error selection order under the API's own evaluation, except the
  actor gate (N20), and a policy decision the API cannot interpret; the
  S cases test the order through the policy service, S17 an
  unreachable one, and S18 and S19 one condition that cannot complete;
* RAS refresh tokens other than those from a deferred redemption;
* DPoP server nonces, mutual TLS (including the refusal to defer for a
  resource configured for mutual-TLS access tokens), and bearer access
  tokens;
* continuation, including the CAI's refusal to attest an access token
  from a deferred redemption or one refreshed from it;
* in deferred redemption: grant-derived revocation while pending,
  cancellation by revoking the deferral code, a change of the user's
  account link while pending, an absolute expiration set before the
  deferral, and `slow_down`;
* other oversight, lifecycle propagation, and SCIM management.

## Running against another implementation

The cases in [suite.py](suite.py) use only HTTP. To run them against
another IdP, RAS or API:

1. Build a `suite.Config` with the deployment's issuers, token
   endpoints, API origin, transport URLs, client identifiers and keys,
   and the identities `expect` names: the agent's issuer and
   identifier, the user's subject in the grant, and the user's subject
   in the access token. Set `max_grant_lifetime` to the IdP's configured
   grant lifetime limit. N13 needs a second client registered at the RAS;
   N17 needs a second tenant in which the user and the agent also have
   rights. N27 needs `uncorrelated_agent`, an agent the RAS has no
   correlation for. D10 and D11 need `second_agent`, another agent the RAS
   correlates and lets act for the user; D12 needs `extra_scope`, a
   scope beyond `scope` the RAS can require approval for, and N25 and N28
   use it as a scope the IdP can exclude from the delegation or prohibit
   for the agent. The S cases
   need `tenant` and `other_tenant`, the Target Tenants of the two
   resources, and `self_acting_client_id` and `self_acting_sub`, a
   registration the API configures as the self-acting population for
   `resource` and the local agent principal its tokens name.
2. Implement `suite.Adapter` for the deployment. Every case needs
   `id_token`; the "Test control" column lists the other capabilities.
   A case whose capability the deployment cannot provide can be skipped
   and reported as not run. N25 and N28 use `set` on the IdP
   (`delegation_scope`, `prohibited_scope`). The D cases use `set` on
   the RAS (`approval_required`, `refresh_permitted`,
   `max_pending_lifetime`, `authorization_lifetime`, `client_profile`),
   the Access Request Service hooks `tasks`, `approve`, `deny`, `revoke`,
   `shorten` and `substitute`, and `advance_clock`, which must advance
   every server's clock. The S cases use `set` on the API
   (`policy_service`, `actor_gate`, `policy_unavailable`) and on the RAS
   (`introspection_omit_act`), the policy service hooks `set_policy` and
   `evaluations`, `mint_access_token`, and `mint_opaque_token`. The
   `Adapter` docstring defines each one, including the policy document
   that `set_policy` takes.
3. Call `suite.run_case` for each case in `suite.CASES`.

`disable_check` exists only for the reference implementation's vacuity
mode.

## Configuration the reference assumes

The drafts leave these choices to deployments. The reference makes one
choice for each, and an implementation that chooses differently
interoperates only where the choice is agreed. The implementer's guide
lists what each pair of implementations exchanges and must agree on
([configuration exchanged between
implementations](../IMPLEMENTERS-GUIDE.md#configuration-exchanged-between-implementations)).

| Choice | The reference's choice | Drafts' text |
|---|---|---|
| How the API tells the governed delegated population apart | Trusted configuration keyed by the access token's `client_id` and audience | core: Profile Applicability ("no in-band discriminator") |
| How the API tells the self-acting population apart | A separate client identifier, `analysis-agent-client`, configured at the API as the self-acting population for the `acme-data` resource; the RAS mints its tokens through test control | core: Profile Applicability (separate client registrations) |
| Where the tenant is carried | The tenant-specific resource URI, as the access token's audience | core: Access Token Issuance and Response (the default) |
| Client registration association | One RAS registration, `analysis-api`, for the dedicated IdP client `analysis-client` | core: Issuance Prerequisites |
| Actor gate | An explicit entry of user, agent issuer, agent and tenant, at both the RAS and the API | core: Delegated Actor Authorization ("not a protocol object") |
| Delegation Authorization | Agent, user, client and resource, with a scope set; a request is narrowed to that set and away from scopes policy categorically prohibits for the agent there; if nothing remains, a requested scope that is prohibited gives `actor_unauthorized`, and otherwise the result is `invalid_scope` | core: Delegation Authorization; Issuance Authorization |
| Re-redeeming a bound grant | Not accepted: each grant is redeemed once | core: Common Grant Validation (MAY accept again under explicit policy) |
| Access tokens | JWT access tokens validated at the API, 600 s, no refresh token except after a deferred redemption; opaque tokens only through test control | core: Token Validation; Optional RAS Refresh Tokens |
| Introspection | RFC 7662 at the RAS, for opaque tokens; the API authenticates with HTTP Basic, calls over HTTP, and caches nothing | core: Optional Opaque Access Tokens and Introspection |
| Policy service | Off unless test control turns it on; in-process, replacing the API's own evaluation; policy set by test control; the decision names the first failing condition | core: Optional Policy Services |
| API denials | HTTP 403 `actor_unauthorized` for the actor gate; HTTP 403 `insufficient_scope`, with the required scope, for token authority; for any other denial, delegated or self-acting, HTTP 403 with `DPoP algs="ES256"` and an empty JSON body; HTTP 503 with `Retry-After: 5` and an empty JSON body when an evaluation cannot complete | core: Error Responses; Self-Acting Access |
| Approval at the RAS | Not required unless test control names the scopes that need it; the Access Request Service is in-process and test-controlled | oversight: Redemption Opt-In; Approval Binding |
| Deferral lifetimes | Maximum pending lifetime 3600 s; absolute authorization expiration 8 h after acceptance; polling interval 5 s | oversight: Deferring a Redemption |
| Refresh after a deferred redemption | Only where test control permits it; bound to the client and the DPoP key, not rotated | core: Optional RAS Refresh Tokens; oversight: Refresh and Continuation |
| Client assertion `aud` | The issuer identifier as a string or a one-element array | core: Dedicated Client Identity (Audience) |
| ID Token audience | Accepted when the `aud` string or array contains the authenticated client, without checking `azp` | ID-JAG Section 4.3.3 |
| Clock skew and DPoP proof age | 60 s each; no server nonces | core: Time, Replay, and Key Validation; RFC 9449 |
| Time claims | `exp` enforced on every JWT; `iat` required on ID Tokens, grants and access tokens; `iat` and `nbf`, where present, rejected beyond the skew | core: Time, Replay, and Key Validation; RFC 7519; RFC 7523 Section 3 |
| Explicit types | `typ` accepted with or without the `application/` prefix | RFC 7515 Section 4.1.9; RFC 9068 Section 4 |
| Lifetimes | ID Token 65 min (as the oversight walkthrough uses), grant 300 s, access token 600 s | core: Common Grant Claims |

## Draft questions found while implementing

These are places where the core leaves behavior that two implementations
could build differently. An entry marked resolved names the draft change
that settled it.

1. **The RAS's error for its own actor-gate denial.** Resolved. The
   core's Redemption Errors now assigns `actor_unauthorized` when RAS
   policy refuses a valid ID-JAG's delegation, including under the
   actor gate, and N16 asserts it.
2. **The RAS's error for a missing or disabled agent record.**
   Resolved. The core's Redemption Errors now assigns `invalid_grant`
   for an ID-JAG whose `act` agent has no authorized correlation or is
   not eligible, and widens the WAG row. N15 asserts it for a disabled
   agent, and N27 for an uncorrelated one.
3. **A delegation that covers none of the requested scope.** Resolved.
   The core's Issuance Errors and Issuance Authorization split
   `actor_unauthorized` (no applicable delegation, or a categorical
   prohibition) from `invalid_scope` (scope ceiling). N09 and N28 assert
   the first, and N25 the second.
4. **A grant with a missing or empty `scope` claim.** Resolved. The
   core's Common Grant Validation assigns `invalid_grant`, and N26
   asserts it.
5. **Check order for a bound redemption without a proof.** Resolved.
   The core's Access-Token Protection states that Grant Protection's
   checks come first, so N11's `invalid_grant` no longer depends on the
   reference's order.
6. **The API's error for a user-authority denial.** Resolved, with
   questions 7 and 8. The core's Error Responses defines the selection
   order, the no-code 403 and the 503. A user-permission denial is HTTP
   403 with a challenge that carries no `error` attribute (S04).
7. **The API's error for a self-acting denial.** Resolved by the same
   change: HTTP 403 with a challenge that carries no `error` attribute
   (S09).
8. **The API's error for a client, tenant or constraint policy
   denial.** Resolved by the same change. A client or tenant policy
   denial is HTTP 403 with a challenge that carries no `error` attribute
   (S05, S06); a scope the operation needs and the token lacks is HTTP
   403 `insufficient_scope` (S07). S14 to S19 test the order and the 503.

[core-scope]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#scope
