# One Agent, End to End

This document is non-normative. It follows one agent, `agent-42`, with
the messages on the wire: first the core, one delegated transaction and
its self-acting counterpart; then optional variations, each stating
where it starts and what it adds; then an incident, and the SCIM
provisioning that can create some of the records the core assumes. The
drafts define every requirement and govern wherever this document
differs. The [architecture overview](ARCHITECTURE.md) explains why each
step holds, and the [playbook](PLAYBOOK.md) turns the same example into
operating steps and tests.

* [Reading the examples](#reading-the-examples)
* [First delegated transaction](#first-delegated-transaction)
* [Self-acting transaction](#self-acting-transaction)
* [Optional variations](#optional-variations)
* [Incident and recovery](#incident-and-recovery)
* [Provisioning with SCIM](#provisioning-with-scim)
* [Variants not traced here](#variants-not-traced-here)

## Reading the examples

* **Copied and new messages.** Most messages are copied unchanged from a
  draft's example appendix, and the sentence before each names the
  draft and section. Messages that no draft shows are marked *(new)*.
  They follow the drafts' rules but appear in no draft.
  `tools/check_examples.py` fails when a copied message no longer
  matches its draft, or when a new message cites a draft section that
  does not exist.
* **Placeholders.** As in the drafts, compact JWTs, keys, thumbprints,
  proofs, and token hashes are labelled placeholders, such as
  `CLIENT_ASSERTION` and `JKT_K`, not test vectors. JWTs are shown as
  decoded payloads. HTTP bodies are line-wrapped for display, and
  framing headers are omitted.
* **The clock.** Times are UTC. The first delegated transaction starts
  at 12:01:03 on September 17, 2026. Provisioning ran the day before,
  except the agent's activation at the RAS at 12:01. Each later section
  states when it starts and what it starts from, so sections can share a
  clock without following one another.

### The cast

| Party | Identifiers | Notes |
|---|---|---|
| Governing IdP | `https://idp.example/`, Governance Tenant `acme` | Issues the grants |
| Agent Principal | (`https://idp.example/`, `agent-42`) | The identity that grants carry |
| Agent's client | `analysis-client` at the IdP; `analysis-api` at `https://ras.example/` | A dedicated client using `private_key_jwt`; DPoP key K |
| User | Alice: `alice-ras` in grants for `https://ras.example/`; `user-108` at the API | Signs in to the client through the IdP |
| Resource domain | RAS `https://ras.example/`; API `https://api.example/tenants/acme-data/`; Target Tenant `acme-data` | The agent is local principal `service-principal-42` |

## First delegated transaction

At 12:01:03 on September 17, Alice, signed in to the client through the
IdP, asks the agent to read `report-7`. The deployment uses the core's
bound profile rather than its unbound one, so the grant is bound to the
client's DPoP key K, and the API requires DPoP-bound access tokens. The
IdP and the RAS already hold these records; [Provisioning with
SCIM](#provisioning-with-scim) shows how SCIM can create some of them:

* at the IdP, an Identity Binding that resolves `analysis-client` to the
  active Agent Principal `agent-42`, and a Client Association that
  permits `analysis-client` to use that binding for delegated issuance;
* at the IdP, Alice's Delegation Authorization for `agent-42`, through
  `analysis-client`, at `https://api.example/tenants/acme-data/`, for
  `files.read`;
* at the IdP, the client registration association from
  `analysis-client` to its registration `analysis-api` at
  `https://ras.example/`, which supplies each grant's `client_id`;
* at the RAS, the registration `analysis-api`, and an active correlation
  of (`https://idp.example/`, `agent-42`) with the local principal
  `service-principal-42`; and
* at the RAS and the API, actor-gate policy that lets `agent-42` act
  for Alice (`user-108`) in `acme-data`.

### Exchange Alice's ID Token for a grant

Alice has signed in to the client through the IdP, so the client holds
her ID Token, whose audience is `analysis-client`. The client signs a
client assertion with its registered key ([core, Dedicated Client
Authentication][core-client-assertion]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-federation.md -->
```json
{
  "iss": "analysis-client",
  "sub": "analysis-client",
  "aud": "https://idp.example/",
  "iat": 1789646463,
  "exp": 1789646523,
  "jti": "analysis-auth-1"
}
```

It proves a separate grant key K with `IDP_DPOP_PROOF` and sends the
exchange ([core, Exchange Request and Response][core-walkthrough]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-federation.md -->
```http
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
```

The IdP resolves `analysis-client` to `agent-42` through the binding,
checks Alice's Delegation Authorization for `files.read`, and returns
an ID-JAG:

<!-- verbatim: draft-mcguinness-oauth-governed-agent-federation.md -->
```http
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
```

The decoded grant:

<!-- verbatim: draft-mcguinness-oauth-governed-agent-federation.md -->
```json
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
```

### Redeem the grant at the RAS

The client authenticates as `analysis-api` and proves the same key K
([core, Redemption Request and Response][core-redemption]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-federation.md -->
```http
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
```

The RAS validates the ID-JAG and its `act`, authenticates
`analysis-api`, and checks the proof against `cnf.jkt`. It resolves
`alice-ras` to its local user `user-108`, correlates `agent-42` with
`service-principal-42`, and finds that the actor gate permits
`agent-42` to act for Alice ([core, Grant
Validation][core-redemption-validation]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-federation.md -->
```http
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
```

The decoded access token keeps Alice as subject and `agent-42` as
actor; the client identifier does not replace the agent:

<!-- verbatim: draft-mcguinness-oauth-governed-agent-federation.md -->
```json
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
```

### Read a file

The client presents the access token with a new proof of K ([core,
Protected Resource Request][core-walkthrough]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-federation.md -->
```http
GET /tenants/acme-data/files/report-7 HTTP/1.1
Host: api.example
Authorization: DPoP API_ACCESS_TOKEN
DPoP: API_DPOP_PROOF
```

The decoded proof header and payload:

<!-- verbatim: draft-mcguinness-oauth-governed-agent-federation.md -->
```json
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
```

<!-- verbatim: draft-mcguinness-oauth-governed-agent-federation.md -->
```json
{
  "jti": "api-proof-1",
  "htm": "GET",
  "htu": "https://api.example/tenants/acme-data/files/report-7",
  "iat": 1789646468,
  "ath": "ATH_ACCESS_TOKEN"
}
```

The API checks the proof against `cnf.jkt` and the tenant, itself
evaluates the actor gate for `agent-42` acting for Alice, checks Alice's
permissions, and returns the file (new):

```http
HTTP/1.1 200 OK
Content-Type: text/csv

region,revenue
north,1200
south,950
```

The redemption returned no refresh token. When `access-1` expires, the
client obtains a new ID-JAG.

### A write the token does not cover

At 12:05, the agent needs to update `report-7`. Its access token
carries only `files.read`, so the API refuses the write (new):

```http
PUT /tenants/acme-data/files/report-7 HTTP/1.1
Host: api.example
Authorization: DPoP API_ACCESS_TOKEN
DPoP: API_DPOP_PROOF_2
Content-Type: text/csv
```

```http
HTTP/1.1 403 Forbidden
WWW-Authenticate: DPoP error="insufficient_scope", scope="files.write", algs="ES256"
```

The actor gate permits `agent-42`, and the missing scope ranks before
Alice's own permissions in the core's [error selection
order][core-resource-errors], so the API reports `insufficient_scope`.
The challenge says what to ask for: a new ID-JAG for `files.write`,
which the IdP refuses with `invalid_scope` while Alice's Delegation
Authorization covers only `files.read`.

## Self-acting transaction

At 12:03, the agent runs a data-quality job on its own authority. This
adds two records at the IdP: the Agent Authorization of `agent-42` for
`files.read` at the same resource, and a Client Association that
permits `analysis-client` to use its binding for self-acting issuance.
The client authenticates with a fresh assertion and repeats it as the
subject token ([core, Self-Acting Variant][core-wag]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-federation.md -->
```http
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
```

The IdP resolves `agent-42`, checks the self-acting Client Association
and the Agent Authorization for `files.read`, and returns a WAG (new):

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store
Pragma: no-cache

{
  "access_token": "WAG",
  "issued_token_type": "urn:ietf:params:oauth:token-type:wag",
  "token_type": "N_A",
  "expires_in": 300,
  "scope": "files.read"
}
```

The decoded WAG names the agent as subject and has no `act`:

<!-- verbatim: draft-mcguinness-oauth-governed-agent-federation.md -->
```json
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
```

The client redeems it as in the [first
transaction](#redeem-the-grant-at-the-ras), with a fresh client
assertion, a fresh proof of K, and the WAG as the `assertion`. The RAS
correlates `agent-42` to `service-principal-42` and issues an access
token for that principal, with no `act` and no refresh token (new):

```json
{
  "iss": "https://ras.example/",
  "sub": "service-principal-42",
  "aud": "https://api.example/tenants/acme-data/",
  "iat": 1789646581,
  "exp": 1789647181,
  "jti": "access-2",
  "client_id": "analysis-api",
  "scope": "files.read",
  "cnf": {"jkt":"JKT_K"}
}
```

The API enforces the agent's own permissions and the tenant, with no
actor gate. Because this token shares the delegated tokens' client
registration and audience, the RAS and API need an additional
bilateral contract to tell the two token populations apart; the absence
of `act` alone does not. A separate client registration or audience for
self-acting tokens avoids that contract.

That completes the two basic access flows, one for each peer grant; an
implementation supports one or both. The variations below are optional,
and each says what it adds; [Incident and
recovery](#incident-and-recovery) shows how disablement and revocation
stop access.

## Optional variations

Each variation states where it starts, its clock, and what it adds.
They are alternatives, not a sequence:

| Variation | Starts from | Leads to |
|---|---|---|
| [Approval at issuance](#approval-at-issuance) | The refused write, 12:05 | A grant for `files.write`, then the write |
| [Approval at redemption](#approval-at-redemption) | `grant-1` before its redemption, 12:01:04 | Access here, and refresh where permitted; no continuation |
| [Gateway continuation](#gateway-continuation) | Alice signed in; a second root grant, 12:01:03 | An onward grant, and the read at the file service |
| [Approved continuation](#approved-continuation) | The gateway continuation's first hop, 12:05:30 | An onward grant for `files.write`, and the write |
| [Scheduled work](#scheduled-work) | Alice's refresh token, September 17 | A run each morning until its first hop's deadline; then a new chain |

Approval at redemption replaces the first transaction's redemption.
Because its authorization cannot be continued, the gateway variations
start from a root grant redeemed without deferral.

### Approval at issuance

* **Starts from:** the refused write, at 12:05.
* **Adds:** Alice's Delegation Authorization also permits `files.write`,
  only with her approval under the [oversight profile][oversight]; Alice
  approves through CIBA; the maximum pending lifetime is one hour; and
  the client opts in to deferral on every request that policy might
  hold ([oversight, Client Opt-In][over-opt-in]).

The client asks for `files.write` and opts in to waiting, with a fresh
client assertion and a proof of K (new; the [oversight
walkthrough][over-request] describes this request without showing it):

<!-- new: draft-mcguinness-oauth-governed-agent-oversight.md#walkthrough-request -->
```http
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
&client_assertion=CLIENT_ASSERTION_4
&subject_token=ALICE_ID_TOKEN_FOR_ANALYSIS_CLIENT
&subject_token_type=urn%3Aietf%3Aparams%3Aoauth
%3Atoken-type%3Aid_token
&audience=https%3A%2F%2Fras.example%2F
&resource=https%3A%2F%2Fapi.example%2Ftenants%2Facme-data%2F
&scope=files.write
&completion_mode=deferred
```

The IdP completes every check except Alice's decision, records the
pending request, and responds with a deferral code ([oversight,
Deferred Request][over-request]). Alice's ID Token expires at 13:10, 65
minutes after the request, so a one-hour pending lifetime leaves a
grant issued at any point in it its full 300 seconds:

<!-- verbatim: draft-mcguinness-oauth-governed-agent-oversight.md -->
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json
Cache-Control: no-store

{
  "error": "authorization_pending",
  "deferral_code": "DEFERRAL_CODE",
  "expires_in": 3600,
  "interval": 5
}
```

Without `completion_mode=deferred`, the IdP would instead have refused
the request with `actor_unauthorized` and issued nothing.

#### Alice approves

The IdP reaches Alice through CIBA on her authenticator, with this
binding message ([oversight, Approval][over-approval]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-oversight.md -->
```text
agent-42 (client analysis-client) asks to write files in acme-data
```

She authenticates and approves at 12:07:40. The CIBA messages
themselves are outside these profiles. The approval covers this one
request; it is not standing authority.

#### The client polls and receives the grant

The client polls at the returned interval, proving K ([oversight,
Resolution][over-resolution]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-oversight.md -->
```http
POST /token HTTP/1.1
Host: idp.example
Content-Type: application/x-www-form-urlencoded
DPoP: IDP_DPOP_PROOF

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adeferred
&deferral_code=DEFERRAL_CODE
&client_id=analysis-client
&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth
%3Aclient-assertion-type%3Ajwt-bearer
&client_assertion=CLIENT_ASSERTION_2
```

Polls before Alice's decision returned `authorization_pending`. At this
poll, 12:07:45, the IdP checks again that `agent-42` is active, that its
binding still permits the request, that Alice's Delegation Authorization
still permits `files.write`, and that Alice is active. It issues the
grant the request would have produced, `ID_JAG_2`, in a token response
like the first transaction's exchange response, with `issued_token_type`
id-jag and `scope` `files.write`. The decoded grant starts its lifetime
at resolution (new):

```json
{
  "iss": "https://idp.example/",
  "sub": "alice-ras",
  "aud": "https://ras.example/",
  "iat": 1789646865,
  "exp": 1789647165,
  "jti": "grant-2",
  "client_id": "analysis-api",
  "resource": "https://api.example/tenants/acme-data/",
  "scope": "files.write",
  "act": {"iss":"https://idp.example/", "sub":"agent-42"},
  "cnf": {"jkt":"JKT_K"},
  "txn": "approval-17"
}
```

No claim records the approval. The optional `txn` joins the grant to
the IdP's approval record for audit; the RAS and API treat it only as a
correlation identifier. The client redeems `grant-2` as in the first
transaction and
retries the write with the new access token.

A denial would have resolved to `access_denied` at the next poll, and
the client would not retry the request as self-acting access or under
another client. Disabling `agent-42` while the request waited would have
prevented issuance if the agent were still disabled at this poll;
[Re-enable](#re-enable) covers a request that survives the
disablement. The client can cancel its own request by revoking the
deferral code.

### Approval at redemption

* **Starts from:** `grant-1` at 12:01:04, in place of the first
  transaction's redemption.
* **Adds:** RAS policy requires the `acme-data` data steward to approve
  each agent redemption for `files.read`; a one-hour maximum pending
  lifetime and an eight-hour absolute authorization expiration; and a
  client that opts in on every redemption that policy might hold
  ([oversight, Redemption Opt-In][over-redemption-opt-in]).

The client adds `completion_mode=deferred` to its redemption and proves
K (new; the [oversight walkthrough][over-redemption] describes this
request without showing it):

<!-- new: draft-mcguinness-oauth-governed-agent-oversight.md#walkthrough-redemption -->
```http
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
&completion_mode=deferred
```

The RAS completes every check except the steward's decision, including
the actor gate. It accepts `grant-1`, which it will not accept again,
sets the absolute authorization expiration to 20:01:04, opens one
approval request, and defers (new; [oversight, Deferring a
Redemption][over-redemption-deferring]):

<!-- new: draft-mcguinness-oauth-governed-agent-oversight.md#redemption-deferring -->
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json
Cache-Control: no-store

{
  "error": "authorization_pending",
  "deferral_code": "RAS_DEFERRAL_CODE",
  "expires_in": 3600,
  "interval": 5
}
```

Without the opt-in, the RAS would have refused with
`actor_unauthorized`, as for any policy refusal, revealing nothing
about approval. The grant's `exp` at 12:06:03 limits only acceptance:
until the redemption ends, the same grant presented again with fresh
client authentication, a fresh proof of K, the opt-in, and the same
request returns the same deferral code ([oversight,
Recovery][over-recovery]).

The steward approves at 12:20, until 14:20. At the client's next poll,
at 12:20:05, the RAS checks the agent, the user, the actor gate, and the
approval again, and returns the token response that the redemption would
have returned, without `issued_token_type`. The access token,
`access-3`, expires at 12:30:05, within the approval expiry and the
absolute authorization expiration ([oversight, Redemption
Resolution][over-redemption-resolution]). Where RAS policy permits a
refresh token, each refresh is evaluated again with the approval, so a
refresh after 14:20 fails with `invalid_grant`. The authorization is
never eligible for continuation: a CAI refuses to attest its tokens
([oversight, Refresh and Continuation][over-redemption-refresh]).

### Gateway continuation

* **Starts from:** Alice signed in, at 12:01:03. The client obtains a
  second root grant, for the gateway, in the same second as `grant-1`,
  and redeems it without deferral.
* **Adds:** the MCP gateway `https://gateway.example/mcp`, which is the
  client `tool-gateway` with DPoP key G, and whose RAS
  `https://ras.gateway.example/` is also its Continuation Assertion
  Issuer (CAI). At the gateway, Alice is `gw-user-7` and the agent's
  client is `analysis-gw`; at `https://ras.example/`, the gateway is
  `gateway-files`. Alice's Delegation Authorization covers
  `tools.invoke` at the gateway and, with tenant policy, permits
  continuation. Neither the chain authorization nor the Continuation
  Association records restrictions ([continuation,
  Restrictions][cont-restrictions]). The IdP holds a
  Continuation Association for `tool-gateway` and trusts the gateway's
  RAS as a CAI ([continuation, Gateway Walkthrough][cont-walkthrough]),
  with a 15-minute continuation window.

The agent reaches the file service through an MCP gateway. The gateway
is the API for the agent's access token, and the client of every
server after it. MCP messages below follow MCP revision 2026-07-28,
except that the agent's client presents a DPoP-bound token
([below](#call-a-tool)). Like MCP's own examples, they omit the
required `_meta` members, such as the protocol version and client
information.

#### Get a gateway access token

The client exchanges Alice's ID Token as in the first transaction, but
for audience `https://ras.gateway.example/`, resource
`https://gateway.example/mcp`,
and scope `tools.invoke`. Because Alice's Delegation Authorization and
tenant policy permit continuation, the root ID-JAG carries a
continuation handle ([continuation, Root Grant and Gateway Access
Token][cont-root]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-continuation.md -->
```json
{
  "iss": "https://idp.example/",
  "sub": "alice-gw",
  "aud": "https://ras.gateway.example/",
  "iat": 1789646463,
  "exp": 1789646763,
  "jti": "gw-grant-1",
  "client_id": "analysis-gw",
  "resource": "https://gateway.example/mcp",
  "scope": "tools.invoke",
  "auth_time": 1789646400,
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "cnf": {"jkt": "JKT_K"},
  "identity_continuation_handle": "Qm7zXu2VtL9pKe4RaW1nHc"
}
```

The client redeems it at the gateway's RAS with a proof of K, and
receives a DPoP-bound access token carrying the same handle, H0:

<!-- verbatim: draft-mcguinness-oauth-governed-agent-continuation.md -->
```json
{
  "iss": "https://ras.gateway.example/",
  "sub": "gw-user-7",
  "aud": "https://gateway.example/mcp",
  "iat": 1789646464,
  "exp": 1789647064,
  "jti": "gw-access-1",
  "client_id": "analysis-gw",
  "scope": "tools.invoke",
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "cnf": {"jkt": "JKT_K"},
  "identity_continuation_handle": "Qm7zXu2VtL9pKe4RaW1nHc"
}
```

#### Call a tool

The agent calls `read_file` with that token and a proof of K (new):

```http
POST /mcp HTTP/1.1
Host: gateway.example
Authorization: DPoP GW_ACCESS_TOKEN
DPoP: GW_TOOL_PROOF
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: read_file

{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "read_file",
    "arguments": {"path": "report-7"}
  }
}
```

MCP clients send access tokens with the `Bearer` scheme, and MCP
defines no DPoP usage; these examples, like the continuation
walkthrough, assume DPoP for this hop. A bearer-only MCP client sends
the same request with `Authorization: Bearer GW_BEARER_ACCESS_TOKEN` and
no `DPoP` header. Its bearer token is eligible for continuation only
where resource policy explicitly permits continuation from bearer
access tokens for `analysis-gw` and the gateway resource, accepting
that a stolen gateway token could induce an honest continuation.

The gateway validates the token and proof and applies the actor gate
for `agent-42` acting for Alice. Where it delegates that decision to a
policy decision point, the identities and token constraints come from
the validated token, never from the tool call's arguments, and the
agent never from `client_id` ([core, Optional Policy
Services][core-policy-services];
the guide's [illustrative requests][guide-authzen]). The call is
permitted.

#### Obtain a Continuation Assertion

The gateway proves its own key G and authenticates as `tool-gateway`
to its RAS, presenting the agent's access token
([continuation, Assertion][cont-assertion]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-continuation.md -->
```http
POST /token HTTP/1.1
Host: ras.gateway.example
Content-Type: application/x-www-form-urlencoded
DPoP: GW_CAI_PROOF

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Atoken-exchange
&requested_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type
%3Aidentity-continuation
&subject_token=GW_ACCESS_TOKEN
&subject_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type
%3Aaccess_token
&client_id=tool-gateway
&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth
%3Aclient-assertion-type%3Ajwt-bearer
&client_assertion=GW_ASSERTION_1
```

The gateway's RAS, acting as CAI, attests that it accepted the
originating grant, that the authorization is active and eligible for
continuation, and that `tool-gateway` is associated with it.
Accepting the API request alone would not establish those facts. The
assertion:

<!-- verbatim: draft-mcguinness-oauth-governed-agent-continuation.md -->
```json
{
  "iss": "https://ras.gateway.example/",
  "aud": "https://idp.example/",
  "identity_continuation_handle": "Qm7zXu2VtL9pKe4RaW1nHc",
  "act": {"iss": "https://gateway.example/", "sub": "tool-gateway"},
  "cnf": {"jkt": "JKT_G"},
  "iat": 1789646470,
  "exp": 1789646590,
  "jti": "n3Vt7Jq2Xd5PbR9wLc1eKs"
}
```

#### Continue to the file service

The gateway presents the assertion at the IdP for the file service
([continuation, Continuation][cont-continuation]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-continuation.md -->
```http
POST /token HTTP/1.1
Host: idp.example
Content-Type: application/x-www-form-urlencoded
DPoP: IDP_GW_PROOF

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Atoken-exchange
&requested_token_type=urn%3Aietf%3Aparams%3Aoauth
%3Atoken-type%3Aid-jag
&client_id=tool-gateway
&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth
%3Aclient-assertion-type%3Ajwt-bearer
&client_assertion=GW_ASSERTION_2
&subject_token=ICA_ASSERTION
&subject_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type
%3Aidentity-continuation
&audience=https%3A%2F%2Fras.example%2F
&resource=https%3A%2F%2Fapi.example%2Ftenants%2Facme-data%2F
&scope=files.read
```

The IdP checks the chain, the Continuation Association for
`tool-gateway`, the target, and Alice's Delegation Authorization. It
also checks that the request arrives before H0's deadline: the time the
IdP issued H0, 12:01:03, plus its continuation window ([continuation,
Governed Chain Authorization][cont-window]). This deployment chooses a
15-minute window, which covers the root grant's 300-second redemption
window and the gateway's 600-second access token ([continuation,
Identity Provider][cont-impl-idp]), so H0's deadline is 12:16:03. It
performs no agent resolution: the agent comes from the chain. The
onward ID-JAG names the same agent and user, with the gateway as client:

<!-- verbatim: draft-mcguinness-oauth-governed-agent-continuation.md -->
```json
{
  "iss": "https://idp.example/",
  "sub": "alice-ras",
  "aud": "https://ras.example/",
  "iat": 1789646471,
  "exp": 1789646771,
  "jti": "gw-grant-2",
  "client_id": "gateway-files",
  "resource": "https://api.example/tenants/acme-data/",
  "scope": "files.read",
  "auth_time": 1789646400,
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "continuation_via": [
    {"iss": "https://gateway.example/", "sub": "tool-gateway"}
  ],
  "cnf": {"jkt": "JKT_G"},
  "identity_continuation_handle": "Zp3kRt8VbN2wLq6YsD4mXe"
}
```

The gateway redeems it at `https://ras.example/` as `gateway-files`,
with a fresh proof of G. The access token, `TARGET_ACCESS_TOKEN`
([continuation, Redemption at the Target][cont-target]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-continuation.md -->
```json
{
  "iss": "https://ras.example/",
  "sub": "user-108",
  "aud": "https://api.example/tenants/acme-data/",
  "iat": 1789646472,
  "exp": 1789647072,
  "jti": "access-gw-1",
  "client_id": "gateway-files",
  "scope": "files.read",
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "cnf": {"jkt": "JKT_G"}
}
```

#### Read the file and answer the agent

The gateway calls the API with a proof of G (new):

```http
GET /tenants/acme-data/files/report-7 HTTP/1.1
Host: api.example
Authorization: DPoP TARGET_ACCESS_TOKEN
DPoP: GW_API_PROOF
```

The API applies the same checks as in the first transaction, including
the actor gate
for `agent-42`, and returns the file. The gateway answers the agent's
call (new):

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "resultType": "complete",
    "content": [
      {"type": "text", "text": "region,revenue\nnorth,1200\nsouth,950"}
    ],
    "isError": false
  }
}
```

The gateway caches `TARGET_ACCESS_TOKEN` for this agent, user, tenant,
resource, scope, key, and source hop, and never uses it for another
agent or another chain.

### Approved continuation

* **Starts from:** the [gateway continuation](#gateway-continuation)'s
  first hop, H0, at 12:05:30, before its 12:16:03 deadline. The
  gateway's token at the file service carries only `files.read`.
* **Adds:** Alice's Delegation Authorization also permits `files.write`,
  only with her approval, so the IdP requires it before an onward grant
  with `files.write` issues; and the agent's client supports the MCP
  tasks extension. The messages below are new.

At 12:05:30, the agent asks the gateway to write `report-7`.

#### The agent calls the tool and accepts a task

The agent's client declares the MCP tasks extension on the request, so
the gateway may answer with a task:

```http
POST /mcp HTTP/1.1
Host: gateway.example
Authorization: DPoP GW_ACCESS_TOKEN
DPoP: GW_TOOL_PROOF_2
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: write_file

{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "write_file",
    "arguments": {
      "path": "report-7",
      "content": "region,revenue\nnorth,1300\nsouth,950"
    },
    "_meta": {
      "io.modelcontextprotocol/clientCapabilities": {
        "extensions": {"io.modelcontextprotocol/tasks": {}}
      }
    }
  }
}
```

#### The gateway asks for write authority and waits

The gateway obtains a new assertion for H0, `ICA_ASSERTION_2`, as in the
gateway continuation, and sends the continuation exchange for
`files.write`, opting in to waiting:

```http
POST /token HTTP/1.1
Host: idp.example
Content-Type: application/x-www-form-urlencoded
DPoP: IDP_GW_PROOF

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Atoken-exchange
&requested_token_type=urn%3Aietf%3Aparams%3Aoauth
%3Atoken-type%3Aid-jag
&client_id=tool-gateway
&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth
%3Aclient-assertion-type%3Ajwt-bearer
&client_assertion=GW_ASSERTION_3
&subject_token=ICA_ASSERTION_2
&subject_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type
%3Aidentity-continuation
&audience=https%3A%2F%2Fras.example%2F
&resource=https%3A%2F%2Fapi.example%2Ftenants%2Facme-data%2F
&scope=files.write
&completion_mode=deferred
```

The IdP performs every continuation check, including that the request
arrives before H0's 12:16:03 deadline, reserves the assertion against
replay, records the pending request, and defers:

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json
Cache-Control: no-store

{
  "error": "authorization_pending",
  "deferral_code": "GW_DEFERRAL_CODE",
  "expires_in": 900,
  "interval": 5
}
```

The reservation lasts until the request ends, even past the
assertion's two-minute lifetime, so the assertion cannot be presented
again. Passing the chain's limits now reserves no capacity; the IdP
counts them again when the grant issues. The deadline limits only when
a continuation can be requested, so the onward grant can still issue
after 12:16:03 if Alice approves within the request's 15-minute pending
lifetime.

The gateway answers the agent's call with a task:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "resultType": "task",
    "taskId": "task-w1",
    "status": "working",
    "statusMessage": "Waiting for the user's approval.",
    "createdAt": "2026-09-17T12:05:31Z",
    "lastUpdatedAt": "2026-09-17T12:05:31Z",
    "ttlMs": 900000,
    "pollIntervalMs": 5000
  }
}
```

The agent polls the task with `tasks/get` and a fresh proof of K. Over
HTTP, the task identifier also goes in `Mcp-Name`, so that
intermediaries route the poll to the server instance that holds the
task:

```http
POST /mcp HTTP/1.1
Host: gateway.example
Authorization: DPoP GW_ACCESS_TOKEN
DPoP: GW_TOOL_PROOF_3
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tasks/get
Mcp-Name: task-w1

{
  "jsonrpc": "2.0",
  "id": 8,
  "method": "tasks/get",
  "params": {"taskId": "task-w1"}
}
```

While Alice has not decided, the task stays `working`.

#### Alice approves, and the gateway polls

Alice receives a CIBA request with this binding message, and approves at
12:06:50:

```text
agent-42 via tool-gateway asks to write files in acme-data
```

The gateway's next poll, proving G:

```http
POST /token HTTP/1.1
Host: idp.example
Content-Type: application/x-www-form-urlencoded
DPoP: IDP_GW_PROOF

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adeferred
&deferral_code=GW_DEFERRAL_CODE
&client_id=tool-gateway
&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth
%3Aclient-assertion-type%3Ajwt-bearer
&client_assertion=GW_ASSERTION_4
```

At 12:06:55, the IdP checks again that the chain has not ended, that
neither the hop nor an ancestor is revoked, that the Continuation
Association still permits `tool-gateway`, and that Alice's Delegation
Authorization permits `files.write`. It counts the onward grant against
the chain's limits as it issues it, and returns it with
`issued_token_type` `urn:ietf:params:oauth:token-type:id-jag`, as in
approval at issuance. The decoded onward grant:

```json
{
  "iss": "https://idp.example/",
  "sub": "alice-ras",
  "aud": "https://ras.example/",
  "iat": 1789646815,
  "exp": 1789647115,
  "jti": "gw-grant-3",
  "client_id": "gateway-files",
  "resource": "https://api.example/tenants/acme-data/",
  "scope": "files.write",
  "auth_time": 1789646400,
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "continuation_via": [
    {"iss": "https://gateway.example/", "sub": "tool-gateway"}
  ],
  "cnf": {"jkt": "JKT_G"},
  "identity_continuation_handle": "Rk2pWx7NcQ4vZt9LbM3sHe"
}
```

#### The write completes

The gateway redeems `gw-grant-3` as in the gateway continuation, writes
the file, and completes the task. The agent's next `tasks/get`, sent the
same way with a fresh proof, returns the tool's result (excerpt; the
[MCP tasks extension][mcp-tasks] defines the full shape):

```json
{
  "jsonrpc": "2.0",
  "id": 12,
  "result": {
    "resultType": "complete",
    "taskId": "task-w1",
    "status": "completed",
    "lastUpdatedAt": "2026-09-17T12:06:57Z",
    "result": {
      "content": [{"type": "text", "text": "Wrote report-7."}],
      "isError": false
    }
  }
}
```

Had Alice denied, the poll would have returned `access_denied`, and
the gateway would have failed the task without writing the file on its
own authority. Had a limit been reached while the request waited, the
approved continuation would still have been refused; the gateway would
then need a new assertion and a new approval.

The approval in this variation is the IdP's, on the continuation. A
gateway whose own policy requires a decision on each call holds the
call the same way under per-action oversight, but that decision is the
gateway's and does not satisfy the IdP's: each decision point applies
its own mode ([guide][guide-oversight]). A deployment that wants Alice
asked once chooses where to ask, for example IdP policy that selects
human out of the loop for `tool-gateway`'s continuations while the
gateway decides on each call.

### Scheduled work

* **Starts from:** Alice signed in on September 17, with the client
  holding her refresh token.
* **Adds:** the agent operator's task service
  `https://agents.example/tasks`, whose RAS
  `https://ras.agents.example/` is continuation-aware and which the IdP
  trusts as a CAI; there the agent's client is `analysis-tasks`. The
  IdP claims grant-anchored continuation and accepts refresh-token
  subjects from `analysis-client`. Alice's Delegation Authorization,
  with tenant policy, permits continuation, and a Continuation
  Association permits `analysis-client` to continue. The continuation
  window covers the task ([continuation, Scheduled
  Variant][cont-scheduled]).

Alice asks for a daily report that runs after she signs out.

#### Anchor the chain while Alice is signed in

On September 17, the client presents Alice's refresh token, whose grant
has her Delegation Authorization for `agent-42` explicitly associated,
as the subject token (new; the [continuation's scheduled
variant][cont-scheduled-setup] describes this request without showing
it):

<!-- new: draft-mcguinness-oauth-governed-agent-continuation.md#walkthrough-scheduled-setup -->
```http
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
&client_assertion=CLIENT_ASSERTION_5
&subject_token=ALICE_REFRESH_TOKEN
&subject_token_type=urn%3Aietf%3Aparams%3Aoauth
%3Atoken-type%3Arefresh_token
&audience=https%3A%2F%2Fras.agents.example%2F
&resource=https%3A%2F%2Fagents.example%2Ftasks
&scope=tasks.run
```

The IdP anchors the chain to the refresh token's grant, not to Alice's
session. The root ID-JAG (excerpt, [continuation, One-Time
Setup][cont-scheduled-setup]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-continuation.md -->
```json
{
  "sub": "alice-tasks",
  "aud": "https://ras.agents.example/",
  "client_id": "analysis-tasks",
  "resource": "https://agents.example/tasks",
  "scope": "tasks.run",
  "auth_time": 1789646400,
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "cnf": {"jkt": "JKT_K"},
  "identity_continuation_handle": "Wd4nKs8QpZ2vXe6TbR1mLy"
}
```

The client redeems it at the task service's RAS with a proof of K. The
RAS binds the handle to a task record that holds no bearer credential:

<!-- verbatim: draft-mcguinness-oauth-governed-agent-continuation.md -->
```text
task_id:   task-7
user:      alice-tasks
agent:     agent-42
runner:    analysis-client
handle:    Wd4nKs8QpZ2vXe6TbR1mLy   # H0
schedule:  daily at 06:00 UTC
status:    active
```

Every run continues from H0, which is why the window covers the task
([continuation, One-Time Setup][cont-scheduled-setup]); where each
window is configured is the deployment's choice.

#### Each run

At 06:00 UTC on September 18, with Alice signed out, the platform's
scheduler starts a run that names only `task-7`. The client
authenticates to the task service's RAS, which derives the hop from the
task record into a Transaction Token for the run; the client exchanges
it there for an assertion bound to K, and then continues at the IdP to
the file service. Those requests have the shape of the gateway
continuation's assertion and continuation requests, with
`analysis-client` as the client. The onward ID-JAG (excerpt,
[continuation, Each Scheduled Run][cont-scheduled-run]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-continuation.md -->
```json
{
  "sub": "alice-ras",
  "aud": "https://ras.example/",
  "iat": 1789711205,
  "exp": 1789711505,
  "client_id": "analysis-api",
  "resource": "https://api.example/tenants/acme-data/",
  "scope": "files.read",
  "auth_time": 1789646400,
  "act": {"iss": "https://idp.example/", "sub": "agent-42"},
  "continuation_via": [
    {"iss": "https://idp.example/", "sub": "analysis-client"}
  ],
  "cnf": {"jkt": "JKT_K"},
  "identity_continuation_handle": "Hc7rVm3NxT9kQw5ZpB2sJf"
}
```

Its `sub`, `act`, and `client_id` are those of `grant-1`, so the
file service processes it as before. Its `auth_time` is still Alice's
sign-in of the previous day. No user credential was retained.

Once H0's deadline passes, the next run fails with `invalid_grant`, and
the task needs a new chain, anchored as at setup ([continuation,
Identity Provider][cont-impl-idp]). If Alice withdraws her Delegation
Authorization for `agent-42`, the next run fails with
`invalid_continuation`, and her delegations to other agents continue.
Revoking the refresh-token grant that anchors the chain also ends it.

## Incident and recovery

* **Starts from:** the first read, at 12:02:
  `access-1` is live, `grant-1` has not expired, and any chain of
  `agent-42` is live.
* **Uses:** the records of [Provisioning with
  SCIM](#provisioning-with-scim): `a17` at the IdP and `local-108` at
  the RAS, each with ETag `W/"a2"`.

At 12:02, security operations responds to suspicious use of `grant-1`.
The two responses below are alternatives: revoke one grant and keep the
agent, or disable the agent everywhere.

### Revoke one grant

The IdP's Transmitter tells the RAS that authorization derived from
`grant-1` is revoked, while `agent-42` stays enabled ([lifecycle,
Revoke Authorization Derived from an ID-JAG][life-signals]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-lifecycle.md -->
```json
{
 "iss": "https://signals.idp.example",
 "aud": [
  "https://ras.example/signals/acme-data"
 ],
 "iat": 1789646520,
 "jti": "revoke-grant-1",
 "sub_id": {
  "format": "jwt_id",
  "iss": "https://idp.example/",
  "jti": "grant-1"
 },
 "events": {
"https://schemas.openid.net/secevent/caep/event-type/session-revoked"
  : {
   "event_timestamp": 1789646520,
   "initiating_entity": "admin",
   "reason_admin": {
    "en": "Grant authorization revoked."
   }
  }
 }
}
```

The RAS invalidates every session derived from `grant-1`, and no other.
When the API next introspects `access-1` (new):

```http
POST /introspect HTTP/1.1
Host: ras.example
Authorization: Bearer API_INTROSPECTION_TOKEN
Content-Type: application/x-www-form-urlencoded

token=API_ACCESS_TOKEN
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "active": false
}
```

The API refuses the client's next request with `access-1` (new):

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: DPoP error="invalid_token", algs="ES256"
```

Redemption of `grant-1` is refused from now on. Where the RAS's policy
accepts a bound grant more than once, a redemption before the grant's
12:06:03 expiry fails; and an event that arrives before a grant's first
redemption makes that redemption fail too. The core assigns no code
more specific than OAuth's `invalid_grant`, which RFC 6749 defines to
include a revoked grant (new):

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json
Cache-Control: no-store

{
  "error": "invalid_grant"
}
```

The agent is still enabled, so a new exchange yields a new grant;
`grant-1` stays unusable. An API that validated `access-1` offline,
instead of introspecting it, would accept it until it expires.

### Disable the agent everywhere

Security operations disables the Agent at the IdP (new):

```http
PATCH /scim/acme/Agents/a17 HTTP/1.1
Host: idp.example
Authorization: Bearer ADMIN_ACCESS_TOKEN
Content-Type: application/scim+json
If-Match: W/"a2"

{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {"op": "replace", "path": "active", "value": false}
  ]
}
```

The IdP returns `204 No Content` with ETag `W/"a3"`. No grant issues
for `agent-42` through any binding or client: a fresh exchange fails
with the same `invalid_grant` response, because no active Agent
Principal resolves. The agent's continuation chains end, so the
gateway's next continuation fails with `invalid_continuation`. The
gateway then rejects the agent's request with HTTP 401 `invalid_token`,
as the continuation profile recommends, so that the agent's client
obtains a new root grant ([continuation, Gateway
Requirements][cont-gateway]).

The disablement reaches the RAS in one of two ways ([lifecycle, Disable
and Re-enable][life-example]). The provisioning connector can apply it
directly (new):

```http
PATCH /scim/v2/Agents/local-108 HTTP/1.1
Host: ras.example
Authorization: Bearer CONNECTOR_ACCESS_TOKEN
Content-Type: application/scim+json
If-Match: W/"a2"

{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [{"op": "replace", "path": "active", "value": false}]
}
```

Or the IdP's provisioning source, where the agent is
`/Agents/source-42`, sends a change notice that carries no state
([lifecycle, Provisioning Change Notice][life-signals]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-lifecycle.md -->
```json
{
  "iss": "https://signals.idp.example",
  "aud": ["https://ras.example/signals/acme-data"],
  "iat": 1789646520,
  "jti": "change-42",
  "sub_id": {
    "format": "scim",
    "uri": "/Agents/source-42"
  },
  "events": {
    "urn:ietf:params:scim:event:prov:patch:notice": {
      "version": "W/\"source-b7\"",
      "attributes": ["active"]
    }
  }
}
```

The RAS then retrieves the source Agent, observes `active: false`, and
applies the same change. Either way, before reporting success the RAS
blocks new redemption and refresh for the agent, so a grant naming
`agent-42` fails there with `invalid_grant` ([core, Redemption
Errors][core-redemption-errors]), and revokes its sessions, so
introspection of `access-1` returns `"active": false` as
above.

### Re-enable

At 12:03, security operations re-enables the Agent with the same PATCH
and `"value": true` at the IdP, using ETag `W/"a3"`, and the connector
does the same at the RAS. New exchanges and redemptions succeed again.
Nothing revoked at 12:02 returns: `access-1` stays inactive, the ended
chains stay ended, and the client needs a new grant. A pending root
request, such as the one in [Approval at
issuance](#approval-at-issuance), may survive a disablement. If it
remains pending and all checks pass after re-enabling, it can still
issue a grant, so deny or cancel requests that must not proceed.

## Provisioning with SCIM

The [first transaction](#first-delegated-transaction) assumed its
records. On September 16, the agent's platform creates several of them
through a SCIM connector, which administrative policy has authorized
for Governance Tenant `acme` to register clients and agents, to bind
the dedicated client, and to authorize its use. The connector's token
is a placeholder, and SCIM management is at `/scim/acme/` at the IdP.

The IdP configures the rest directly, and no draft defines a message
for them: Delegation and Agent Authorizations, with any oversight mode;
self-acting Client Associations, since SCIM management administers
associations for delegated issuance only; the client registration
association; and continuation configuration.

### Register the client at the IdP

The connector registers the agent's dedicated client under the SCIM
OAuth client management profile (new):

```http
POST /scim/acme/OAuthClients HTTP/1.1
Host: idp.example
Authorization: Bearer CONNECTOR_ACCESS_TOKEN
Content-Type: application/scim+json
Accept: application/scim+json

{
  "schemas": [
    "urn:ietf:params:scim:schemas:core:2.0:OAuthClient",
    "urn:ietf:params:scim:schemas:extension:oauth:2.0:OAuthClient"
  ],
  "externalId": "analysis-registration-1",
  "active": false,
  "urn:ietf:params:scim:schemas:extension:oauth:2.0:OAuthClient": {
    "token_endpoint_auth_method": "private_key_jwt",
    "grant_types": [
      "authorization_code",
      "refresh_token",
      "urn:ietf:params:oauth:grant-type:token-exchange",
      "urn:ietf:params:oauth:grant-type:deferred"
    ],
    "response_types": ["code"],
    "redirect_uris": ["https://analysis.example/callback"],
    "jwks_uri": "https://analysis.example/oauth/jwks.json",
    "client_name": "Data analysis"
  }
}
```

The IdP assigns the OAuth `client_id`, which is read-only in SCIM
(new):

```http
HTTP/1.1 201 Created
Location: https://idp.example/scim/acme/OAuthClients/oc9
ETag: W/"c1"
Content-Type: application/scim+json

{
  "schemas": [
    "urn:ietf:params:scim:schemas:core:2.0:OAuthClient",
    "urn:ietf:params:scim:schemas:extension:oauth:2.0:OAuthClient"
  ],
  "id": "oc9",
  "externalId": "analysis-registration-1",
  "authorizationServer": "https://idp.example/",
  "clientId": "analysis-client",
  "active": false,
  "meta": {
    "resourceType": "OAuthClient",
    "version": "W/\"c1\"",
    "location": "https://idp.example/scim/acme/OAuthClients/oc9",
    "created": "2026-09-16T09:00:00Z",
    "lastModified": "2026-09-16T09:00:00Z"
  },
  "urn:ietf:params:scim:schemas:extension:oauth:2.0:OAuthClient": {
    "token_endpoint_auth_method": "private_key_jwt",
    "grant_types": [
      "authorization_code",
      "refresh_token",
      "urn:ietf:params:oauth:grant-type:token-exchange",
      "urn:ietf:params:oauth:grant-type:deferred"
    ],
    "response_types": ["code"],
    "redirect_uris": ["https://analysis.example/callback"],
    "jwks_uri": "https://analysis.example/oauth/jwks.json",
    "client_name": "Data analysis"
  }
}
```

An authorized PATCH, of the same form as the Agent's below, sets the
client `active`. Registration creates no Agent Principal and no user
delegation. The resource domain registers the same client as
`analysis-api` at `https://ras.example/` under its own policy; these
examples do not show that registration.

### Register the agent at the IdP

The connector creates the Agent inactive, under the SCIM management
profile (new; the [platform onboarding
example][scim-onboarding] shows the same request for a shared client):

```http
POST /scim/acme/Agents HTTP/1.1
Host: idp.example
Authorization: Bearer CONNECTOR_ACCESS_TOKEN
Content-Type: application/scim+json
Accept: application/scim+json

{
  "schemas": [
    "urn:ietf:params:scim:schemas:core:2.0:Agent",
    "urn:ietf:params:scim:schemas:extension:agent-federation:2.0:Agent"
  ],
  "urn:ietf:params:scim:schemas:extension:agent-federation:2.0:Agent":
    {},
  "externalId": "analysis-agent-1",
  "agentUserName": "analysis-agent",
  "displayName": "Data analysis agent",
  "active": false
}
```

The IdP populates the federation extension with the Agent Principal
identifier (new):

```http
HTTP/1.1 201 Created
Location: https://idp.example/scim/acme/Agents/a17
ETag: W/"a1"
Content-Type: application/scim+json

{
  "schemas": [
    "urn:ietf:params:scim:schemas:core:2.0:Agent",
    "urn:ietf:params:scim:schemas:extension:agent-federation:2.0:Agent"
  ],
  "id": "a17",
  "externalId": "analysis-agent-1",
  "agentUserName": "analysis-agent",
  "displayName": "Data analysis agent",
  "active": false,
  "urn:ietf:params:scim:schemas:extension:agent-federation:2.0:Agent":
    {
    "issuer": "https://idp.example/",
    "subject": "agent-42"
  },
  "meta": {
    "resourceType": "Agent",
    "created": "2026-09-16T09:05:00Z",
    "lastModified": "2026-09-16T09:05:00Z",
    "version": "W/\"a1\"",
    "location": "https://idp.example/scim/acme/Agents/a17"
  }
}
```

The platform's `analysis-agent-1`, SCIM's `a17`, and the IdP's
`agent-42` have separate roles. Only (`https://idp.example/`,
`agent-42`) is the Agent Principal identity that grants carry.

### Bind the dedicated client and enable the agent

A dedicated client is its own execution identity, so one binding both
resolves the agent and permits the client to use it for delegated
issuance. The connector sends `POST /scim/acme/AgentIdentityBindings`
with this body ([SCIM management, Example: Dedicated
Client][scim-dedicated]):

<!-- verbatim: draft-mcguinness-scim-agent-federation.md -->
```json
{
  "schemas": [
    "urn:ietf:params:scim:schemas:core:2.0:AgentIdentityBinding"
  ],
  "externalId": "dedicated-binding-7",
  "agent": {"value": "a17"},
  "credentialClass": "dedicated-client",
  "client": {"value": "oc9"},
  "active": true
}
```

The IdP returns `201 Created` with the binding's `id`. The connector
then enables the Agent ([SCIM management, Enable the
Agent][scim-onboarding]):

<!-- verbatim: draft-mcguinness-scim-agent-federation.md -->
```http
PATCH /scim/acme/Agents/a17 HTTP/1.1
Host: idp.example
Content-Type: application/scim+json
If-Match: W/"a1"

{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {"op": "replace", "path": "active", "value": true}
  ]
}
```

The IdP returns `204 No Content` with ETag `W/"a2"`.

### Provision the agent into the resource domain

The IdP's provisioning connector, whose authenticated context binds
`https://idp.example/` to Target Tenant `acme-data`, creates the agent
at the RAS's SCIM service with `POST /scim/v2/Agents` and this body
([lifecycle, Correlate and Provision][life-example]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-lifecycle.md -->
```json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Agent"],
  "externalId": "agent-42",
  "agentUserName": "analysis-agent",
  "displayName": "Data analysis agent",
  "active": false
}
```

The RAS correlates (`https://idp.example/`, `agent-42`) with its local
principal `service-principal-42` and returns the management
representation (new):

```http
HTTP/1.1 201 Created
Location: https://ras.example/scim/v2/Agents/local-108
ETag: W/"a1"
Content-Type: application/scim+json

{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Agent"],
  "id": "local-108",
  "externalId": "agent-42",
  "agentUserName": "analysis-agent",
  "displayName": "Data analysis agent",
  "active": false,
  "meta": {
    "resourceType": "Agent",
    "version": "W/\"a1\"",
    "location": "https://ras.example/scim/v2/Agents/local-108"
  }
}
```

The SCIM `id` `local-108` is not the principal identifier, and the
agent stays inactive at the RAS until the connector activates it.

### Activate the agent at the RAS

At 12:01 UTC on September 17, the connector activates the agent at the
RAS, using the ETag it read ([lifecycle, Activate and
Exchange][life-example]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-lifecycle.md -->
```http
PATCH /scim/v2/Agents/local-108 HTTP/1.1
Host: ras.example
Authorization: Bearer CONNECTOR_ACCESS_TOKEN
Content-Type: application/scim+json
If-Match: W/"a1"

{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [{"op": "replace", "path": "active", "value": true}]
}
```

The RAS returns ETag `W/"a2"`, and the agent is active there for the
first transaction.

## Variants not traced here

| Variant | Where its messages are |
|---|---|
| A shared platform client presenting a platform JWT, such as AWS STS, as the actor token | Core, [Input Variants][core-inputs] |
| SPIFFE JWT-SVID, WIT-SVID, and X.509-SVID inputs, and Client Attestation | [Inputs draft][inputs-examples]: decoded credentials and a comparison table, without requests |
| Onboarding a shared platform client through SCIM, with an Agent Client Association | SCIM management, [Example: Platform Onboarding][scim-onboarding] |
| Admitting a Client ID Metadata Document client | SCIM client management, [Example: Admit a CIMD Client][oc-cimd] |
| A self-acting chain through a gateway | Continuation, [Self-Acting Variant][cont-self-acting] |
| Two gateways in a row, with path disclosure | Continuation, [Two-Gateway Variant][cont-two-gateways] |
| A platform-hosted agent: signals to the IdP, risk, and disablement | Lifecycle, [Platform-Hosted Agent Example][life-platform] |

### Not shown

These steps have no message in any draft, and these examples do not
invent one:

* the RAS's registration of `analysis-api`, and the IdP's
  configuration of Delegation Authorizations, Agent Authorizations,
  self-acting Client Associations, oversight modes, and Continuation
  Associations;
* the approval channels: CIBA messages, the RAS's access request
  service, and any approval page;
* AuthZEN requests and responses, which the guide
  [illustrates][guide-authzen];
* the scheduled run's Transaction Token and assertion requests; and
* per-action approval at an API, for which the oversight profile
  defines no wire format.

[oversight]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html
[over-request]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#walkthrough-request
[over-approval]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#walkthrough-approval
[over-resolution]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#walkthrough-resolution
[over-opt-in]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#opt-in
[over-redemption]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#walkthrough-redemption
[over-redemption-opt-in]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#redemption-opt-in
[over-redemption-deferring]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#redemption-deferring
[over-recovery]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#redemption-recovery
[over-redemption-resolution]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#redemption-resolution
[over-redemption-refresh]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#redemption-refresh
[core-walkthrough]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#walkthrough
[core-client-assertion]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#client-assertion-example
[core-redemption]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#redemption-example
[core-redemption-validation]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#redemption-validation
[core-redemption-errors]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#redemption-errors
[core-resource-errors]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#resource-errors
[core-policy-services]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#policy-services
[core-wag]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#wag-example
[core-inputs]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#input-variants
[inputs-examples]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-inputs.html#input-variants
[cont-walkthrough]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough
[cont-root]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-root
[cont-assertion]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-assertion
[cont-continuation]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-continuation
[cont-target]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-target
[cont-self-acting]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-self-acting
[cont-two-gateways]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-two-gateways
[cont-scheduled]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-scheduled
[cont-scheduled-setup]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-scheduled-setup
[cont-scheduled-run]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-scheduled-run
[cont-gateway]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#gateway-reuse
[cont-window]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#governed-chain-authorization
[cont-restrictions]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#restrictions
[cont-impl-idp]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#implementation-idp
[life-example]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#example
[life-signals]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#signal-examples
[life-platform]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#platform-example
[scim-onboarding]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-agent-federation.html#example
[scim-dedicated]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-agent-federation.html#dedicated-example
[oc-cimd]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-oauth-client-management.html#example-admit-a-cimd-client
[guide-authzen]: IMPLEMENTERS-GUIDE.md#illustrative-requests
[guide-oversight]: IMPLEMENTERS-GUIDE.md#human-oversight
[mcp-tasks]: https://tasks.extensions.modelcontextprotocol.io/specification/2026-07-28/tasks
