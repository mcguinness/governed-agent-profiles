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
RAS](#deferred-redemption-at-the-ras)).

The drafts define every requirement. The suite tests a subset of them,
and passing it is evidence for that subset only, not a conformance claim.

* [Run](#run)
* [Cases](#cases)
* [Deferred redemption at the RAS](#deferred-redemption-at-the-ras)
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
case that cites a reference check with that check switched off, and
fails if the case still passes. `--list` prints each case's source and
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
| N09 | IdP | A withdrawn Delegation Authorization fails with `actor_unauthorized` | core: Delegation Authorization; PLAYBOOK recipe | Withdraw the delegation |
| N10 | RAS | A grant without `cnf` under the bound profile fails with `invalid_grant` | core: negative-test row | Let the IdP issue unbound grants |
| N11 | RAS | A bound grant redeemed without a proof fails with `invalid_grant` | core: negative-test row | None |
| N12 | RAS | A redemption proven with another key fails with `invalid_grant` | core: Grant Protection | None |
| N13 | RAS | A grant redeemed by a client other than its `client_id` fails with `invalid_grant` | core: Redemption Request; ID-JAG Section 4.4.1 | None; needs a second RAS client |
| N14 | RAS | A `resource` parameter other than the grant's fails with `invalid_target` | core: Common Grant Validation | None |
| N15 | RAS | An agent disabled at the RAS gets no access token | core: Agent Principal Correlation; Applied Disablement and Revocation | Disable the agent at the RAS |
| N16 | RAS | An agent the RAS's policy does not let act for the user fails with `actor_unauthorized` | core: Delegated Actor Authorization; Redemption Errors | Close the actor gate at the RAS |
| N17 | API | An access token used in another tenant, with a fresh proof, fails with 401 `invalid_token` | core: negative-test row | None; needs a second tenant |
| N18 | API | A delegated-population token without `act` fails with 401 `invalid_token` | core: negative-test row; Profile Applicability | Mint an access token |
| N19 | API | A request proven with another key fails with 401 `invalid_token` | core: Token Validation; RFC 9449 Section 7.1 | None |
| N20 | API | A closed actor gate fails with 403 `actor_unauthorized`, not `insufficient_scope` | core: Error Responses | Close the actor gate at the API |
| N21 | IdP | An ID Token whose `iat` is an hour ahead fails with `invalid_grant` | core: Time, Replay, and Key Validation | ID Token with chosen claims |
| N22 | IdP | A client assertion whose `nbf` is an hour ahead fails with `invalid_client` | RFC 7523 Section 3; core: Time, Replay, and Key Validation | None |
| N23 | RAS | A grant whose `nbf` is an hour ahead fails with `invalid_grant` | RFC 7523 Section 3; core: Time, Replay, and Key Validation | Mint a grant |
| N24 | API | An access token whose `iat` is an hour ahead fails with 401 `invalid_token` | core: Time, Replay, and Key Validation; RFC 9068 Section 4 | Mint an access token |
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

The "negative-test row" sources are the rows of the core's "Renewal and
Negative Tests" table. N15 asserts only that no token issues, because
the drafts fix no error code for it; the runner prints the code it
observed. N16 asserts `actor_unauthorized`, which the core's Redemption
Errors assigns when RAS policy refuses a valid ID-JAG's delegation. The time cases use an hour, well beyond the few
minutes of skew the core contemplates, so they do not depend on one
implementation's tolerance.

The suite fails a case only for a departure from a requirement. A
departure from a recommendation, such as a grant longer than five
minutes or a resource challenge without an `error` parameter, is
printed as a note.

Every negative case, P2 and D02 name the reference check they exercise
(`CHECKS` in [reference.py](reference.py)). With `--vacuity`, all 43
fail with their check switched off. Twenty-three N cases fail because
the server then accepts the request. P2 fails because the access token
then carries a rewritten `act`. N11 fails because the RAS returns
`invalid_request` instead of `invalid_grant`: its access-token
protection check also rejects a redemption without a proof, so the case
depends on the code that Grant Protection requires.

The D cases fail without their check in these ways:

* the RAS issues a token it must not: D01, D02 (a second token), D05,
  D11 and D14;
* it returns or keeps a deferral where an error is required: D03, D06
  (a new deferral after the denial), D08, D18 and D19;
* it returns another error: D07 (`actor_unauthorized`);
* it exceeds a bound: D04 and D17 (`expires_in`), D12 (`scope`), D13
  and D15 (the token's `exp`);
* it opens one access request for two redemptions (D10), or two
  pending redemptions for one grant (D16).

D09 is a positive case and names no check.

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
* D11 asserts `authorization_pending`, as Approval Binding says. See
  draft question 6.

## What the suite does not cover

The suite tests nothing outside the path above, including:

* governed agent access with unbound grants, except as the setup for N10
  and D08;
* existing platform JWTs and the inputs of the inputs draft;
* self-acting access with WAG, including deferred WAG redemption and the
  removal of a pending WAG redemption's correlation;
* introspection, opaque access tokens, and RAS refresh tokens other than
  those from a deferred redemption;
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
   rights. D10 and D11 need `second_agent`, another agent the RAS
   correlates and lets act for the user; D12 needs `extra_scope`, a
   scope beyond `scope` the RAS can require approval for.
2. Implement `suite.Adapter` for the deployment. Every case needs
   `id_token`; the "Test control" column lists the other capabilities.
   A case whose capability the deployment cannot provide can be skipped
   and reported as not run. The D cases use `set` on the RAS
   (`approval_required`, `refresh_permitted`, `max_pending_lifetime`,
   `authorization_lifetime`, `client_profile`), the Access Request
   Service hooks `tasks`, `approve`, `deny`, `revoke`, `shorten` and
   `substitute`, and `advance_clock`, which must advance every server's
   clock. The `Adapter` docstring defines each one.
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
| Where the tenant is carried | The tenant-specific resource URI, as the access token's audience | core: Access Token Issuance and Response (the default) |
| Client registration association | One RAS registration, `analysis-api`, for the dedicated IdP client `analysis-client` | core: Issuance Prerequisites |
| Actor gate | An explicit entry of user, agent issuer, agent and tenant, at both the RAS and the API | core: Delegated Actor Authorization ("not a protocol object") |
| Delegation Authorization | Agent, user, client and resource, with a scope set; a request is narrowed to it, and a request with no overlap fails with `invalid_scope` | core: Delegation Authorization; Issuance Authorization |
| Re-redeeming a bound grant | Not accepted: each grant is redeemed once | core: Common Grant Validation (MAY accept again under explicit policy) |
| Access tokens | JWT access tokens validated at the API, 600 s, no introspection, no refresh token except after a deferred redemption | core: Token Validation; Optional RAS Refresh Tokens |
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
2. **The RAS's error for a missing or disabled agent record.** Agent
   Principal Correlation and Applied Disablement require denial. The
   Redemption Errors table fixes `invalid_grant` for a WAG whose `sub`
   has no authorized correlation, but names no error for an ID-JAG whose
   `act` has none, or for a disabled agent. The reference returns
   `invalid_grant`; N15 asserts only that no token issues.
3. **A delegation that covers none of the requested scope.** Issuance
   Authorization returns `invalid_scope` when no scope can be granted;
   the Issuance Errors table returns `actor_unauthorized` for an
   insufficient delegation. The reference returns `invalid_scope`.
4. **A grant with a missing or empty `scope` claim.** Common Grant
   Validation requires a non-empty string but names no error. Two codes
   are candidates: `invalid_grant` for an invalid ID-JAG (Redemption
   Errors), and `invalid_scope` when no non-empty scope can be issued
   (Token Endpoint Errors). The reference returns `invalid_grant`.
5. **Check order for a bound redemption without a proof.** Grant
   Protection requires `invalid_grant`. Access-Token Protection also
   prevents issuing an access token for a resource that requires DPoP
   when no proof is presented. An implementation that applies
   access-token protection first returns a different error. The core
   could say that grant protection is checked first.

[core-scope]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#scope
