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

The drafts define every requirement. The suite tests a subset of them,
and passing it is evidence for that subset only, not a conformance claim.

* [Run](#run)
* [Cases](#cases)
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
| N16 | RAS | An agent the RAS's policy does not let act for the user gets no access token | core: Delegated Actor Authorization | Close the actor gate at the RAS |
| N17 | API | An access token used in another tenant, with a fresh proof, fails with 401 `invalid_token` | core: negative-test row | None; needs a second tenant |
| N18 | API | A delegated-population token without `act` fails with 401 `invalid_token` | core: negative-test row; Profile Applicability | Mint an access token |
| N19 | API | A request proven with another key fails with 401 `invalid_token` | core: Token Validation; RFC 9449 Section 7.1 | None |
| N20 | API | A closed actor gate fails with 403 `actor_unauthorized`, not `insufficient_scope` | core: Error Responses | Close the actor gate at the API |
| N21 | IdP | An ID Token whose `iat` is an hour ahead fails with `invalid_grant` | core: Time, Replay, and Key Validation | ID Token with chosen claims |
| N22 | IdP | A client assertion whose `nbf` is an hour ahead fails with `invalid_client` | RFC 7523 Section 3; core: Time, Replay, and Key Validation | None |
| N23 | RAS | A grant whose `nbf` is an hour ahead fails with `invalid_grant` | RFC 7523 Section 3; core: Time, Replay, and Key Validation | Mint a grant |
| N24 | API | An access token whose `iat` is an hour ahead fails with 401 `invalid_token` | core: Time, Replay, and Key Validation; RFC 9068 Section 4 | Mint an access token |

The "negative-test row" sources are the rows of the core's "Renewal and
Negative Tests" table. N15 and N16 assert only that no token issues,
because the drafts fix no error code for those cases; the runner prints
the code it observed. The time cases use an hour, well beyond the few
minutes of skew the core contemplates, so they do not depend on one
implementation's tolerance.

The suite fails a case only for a departure from a requirement. A
departure from a recommendation, such as a grant longer than five
minutes or a resource challenge without an `error` parameter, is
printed as a note.

Every negative case and P2 name the reference check they exercise
(`CHECKS` in [reference.py](reference.py)). With `--vacuity`, all 25
fail with their check switched off. Twenty-three negative cases fail
because the server then accepts the request. P2 fails because the access
token then carries a rewritten `act`. N11 fails because the RAS returns
`invalid_request` instead of `invalid_grant`: its access-token
protection check also rejects a redemption without a proof, so the case
depends on the code that Grant Protection requires.

## What the suite does not cover

The suite tests nothing outside the path above, including:

* governed agent access with unbound grants, except as the setup for N10;
* existing platform JWTs and the inputs of the inputs draft;
* self-acting access with WAG;
* introspection, opaque access tokens, and RAS refresh tokens;
* DPoP server nonces, mutual TLS, and bearer access tokens;
* continuation, oversight, lifecycle propagation, and SCIM management.

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
   rights.
2. Implement `suite.Adapter` for the deployment. Every case needs
   `id_token`; the "Test control" column lists the other capabilities.
   A case whose capability the deployment cannot provide can be skipped
   and reported as not run.
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
| Access tokens | JWT access tokens validated at the API, 600 s, no introspection, no refresh token | core: Token Validation; Optional RAS Refresh Tokens |
| Client assertion `aud` | The issuer identifier as a string or a one-element array | core: Dedicated Client Identity (Audience) |
| ID Token audience | Accepted when the `aud` string or array contains the authenticated client, without checking `azp` | ID-JAG Section 4.3.3 |
| Clock skew and DPoP proof age | 60 s each; no server nonces | core: Time, Replay, and Key Validation; RFC 9449 |
| Time claims | `exp` enforced on every JWT; `iat` required on ID Tokens, grants and access tokens; `iat` and `nbf`, where present, rejected beyond the skew | core: Time, Replay, and Key Validation; RFC 7519; RFC 7523 Section 3 |
| Explicit types | `typ` accepted with or without the `application/` prefix | RFC 7515 Section 4.1.9; RFC 9068 Section 4 |
| Lifetimes | ID Token 65 min (as the oversight walkthrough uses), grant 300 s, access token 600 s | core: Common Grant Claims |

## Draft questions found while implementing

These are places where the core leaves behavior that two implementations
could build differently. No draft is changed here.

1. **The RAS's error for its own actor-gate denial.** The core assigns
   `actor_unauthorized` at the IdP and at the API, but names no error for
   a redemption the RAS refuses under its actor gate. The reference
   returns `actor_unauthorized`; N16 asserts only that no token issues.
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
