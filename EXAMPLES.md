# One Agent, End to End

This document is non-normative. It follows one agent, `agent-42`,
through the whole architecture with the messages on the wire:
registration at the IdP, provisioning into a resource domain, delegated
and self-acting access, approval before granting write access, a
gateway that continues the agent's request, a gateway write held for
approval, a scheduled run after the user signs out, and an incident that
revokes a grant and disables the agent. The drafts define every
requirement and govern wherever this document differs. The
[architecture overview](ARCHITECTURE.md) explains why each step holds,
and the [playbook](PLAYBOOK.md) turns the same example into operating
steps and tests.

* [Reading the examples](#reading-the-examples)
* [1. Setup](#1-setup)
* [2. First delegated read](#2-first-delegated-read)
* [3. Self-acting run](#3-self-acting-run)
* [4. Approval before granting write access](#4-approval-before-granting-write-access)
* [5. Through an MCP gateway](#5-through-an-mcp-gateway)
* [6. A gateway write held for approval](#6-a-gateway-write-held-for-approval)
* [7. A scheduled run](#7-a-scheduled-run)
* [8. Incident](#8-incident)
* [9. Variants not traced here](#9-variants-not-traced-here)

## Reading the examples

* **Copied and new messages.** Most messages are copied unchanged from a
  draft's example appendix, and the sentence before each names the
  draft and section. Messages that no draft shows are marked *(new)*.
  They follow the drafts' rules but appear in no draft.
  `tools/check_examples.py` fails when a copied message no longer
  matches its draft.
* **Placeholders.** As in the drafts, compact JWTs, keys, thumbprints,
  proofs, and token hashes are labelled placeholders, such as
  `CLIENT_ASSERTION` and `JKT_K`, not test vectors. JWTs are shown as
  decoded payloads. HTTP bodies are line-wrapped for display, and
  framing headers are omitted.
* **The clock.** Setup happens on September 16, 2026. The first access
  starts at 12:01:03 UTC on September 17. Each later scene starts from
  the state at the end of that access and keeps the clock of the draft
  it comes from, so the scenes overlap in time: scene 5's root grant,
  for example, issues in the same second as scene 2's. Read each scene
  as one thing that can happen next, not as a sequence. Scene 6
  continues scene 5, and scene 7 runs into the next morning.

### The cast

| Party | Identifiers | Notes |
|---|---|---|
| Governing IdP | `https://idp.example/`, Governance Tenant `acme` | SCIM management at `/scim/acme/` |
| Agent Principal | (`https://idp.example/`, `agent-42`) | SCIM `id` `a17` at the IdP |
| Agent's client | `analysis-client` at the IdP; `analysis-api` at `https://ras.example/` | A dedicated client using `private_key_jwt`; DPoP key K |
| User | Alice: `alice-ras` in grants for `https://ras.example/`; `user-108` at the API | Signs in to the client through the IdP |
| Resource domain | RAS `https://ras.example/`; API `https://api.example/tenants/acme-data/`; Target Tenant `acme-data` | The agent is local principal `service-principal-42`, SCIM `id` `local-108` |
| MCP gateway | `https://gateway.example/mcp`; its RAS and Continuation Assertion Issuer (CAI) `https://ras.gateway.example/` | The gateway is the client `tool-gateway`, DPoP key G. At the gateway, Alice is `gw-user-7` and the agent's client is `analysis-gw` |
| Task service | `https://agents.example/tasks`; its RAS and CAI `https://ras.agents.example/` | The agent's client is `analysis-tasks` |

### Scenes

| Scene | Clock (UTC) | What happens | Drafts |
|---|---|---|---|
| [1. Setup](#1-setup) | September 16 | Register the client and the agent at the IdP; provision the agent into the resource domain | SCIM client management, SCIM management, lifecycle |
| [2. First delegated read](#2-first-delegated-read) | 12:01:00 to 12:01:08 | Activate the agent at the RAS, exchange, redeem, read | Lifecycle, core |
| [3. Self-acting run](#3-self-acting-run) | 12:03:00 | Obtain and redeem a WAG | Core |
| [4. Approval before granting write access](#4-approval-before-granting-write-access) | 12:05:00 to 12:07:45 | Refused write, deferred exchange, Alice's approval, grant | Oversight |
| [5. Through an MCP gateway](#5-through-an-mcp-gateway) | 12:01:03 to 12:01:12 | Gateway token, tool call, assertion, continuation, target access | Continuation |
| [6. A gateway write held for approval](#6-a-gateway-write-held-for-approval) | 12:05:30 to 12:06:57 | Tool call answered with a task, deferred continuation, approval | Oversight, continuation |
| [7. A scheduled run](#7-a-scheduled-run) | September 17; 06:00 on September 18 | Chain anchored to a refresh token, task record, run | Continuation |
| [8. Incident](#8-incident) | 12:02 to 12:03 | Revoke one grant; disable and re-enable the agent | Lifecycle, SCIM management |
| [9. Variants not traced here](#9-variants-not-traced-here) | | Where the drafts show other inputs, clients, and topologies | |

## 1. Setup

The agent's platform runs a SCIM connector that administers its
registrations at the IdP. Administrative policy has authorized the
connector for Governance Tenant `acme`, to register clients and agents,
to bind the dedicated client, and to authorize its use. The connector's
token is a placeholder.

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

### Configure what SCIM does not carry

These relationships are configured at the IdP directly; no draft
defines a message for them:

* Alice's Delegation Authorization for `agent-42`, through
  `analysis-client`, at `https://api.example/tenants/acme-data/`:
  `files.read` without approval, and `files.write` only with Alice's
  approval under the [oversight profile][oversight]. The SCIM
  management profile has no attribute for the oversight mode.
* The Agent Authorization of `agent-42` for `files.read` at the same
  resource, and a Client Association that permits `analysis-client` to
  use its binding for self-acting issuance. SCIM management administers
  associations for delegated issuance only.
* The client registration association from `analysis-client` to
  `analysis-api` at `https://ras.example/`, which supplies each grant's
  `client_id`.
* For scenes 5 to 7: tenant policy and Alice's Delegation
  Authorization that permit continuation; the gateway's client
  registration, Continuation Associations, and registration as
  `gateway-files` at `https://ras.example/`; and trust in the gateway's
  and the task service's RASes as CAIs ([continuation, Gateway
  Walkthrough][cont-walkthrough]).

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

## 2. First delegated read

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

The RAS returns a new ETag.

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

The API checks the proof against `cnf.jkt`, the tenant, Alice's
permissions, and the actor gate for `agent-42` acting for Alice, and
returns the file (new):

```http
HTTP/1.1 200 OK
Content-Type: text/csv

region,revenue
north,1200
south,950
```

The redemption returned no refresh token. When `access-1` expires, the
client obtains a new ID-JAG.

## 3. Self-acting run

At 12:03, the agent runs a data-quality job on its own authority. The
client authenticates with a fresh assertion and repeats it as the
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

The client redeems it as in scene 2, with a fresh client assertion,
a fresh proof of K, and the WAG as the `assertion`. The RAS correlates
`agent-42` to `service-principal-42` and issues an access token for
that principal, with no `act` and no refresh token (new):

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
actor gate. Because this token shares scene 2's client registration and
audience, the RAS and API need an additional bilateral contract to tell
the two token populations apart; the absence of `act` alone does not.
A separate client registration or audience for self-acting tokens
avoids that contract.

## 4. Approval before granting write access

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

The challenge only tells the client what authority to ask for. Policy
at the IdP requires Alice's approval before `agent-42` writes her
files, so the client asks for `files.write` and opts in to waiting,
with a fresh client assertion and a proof of K (new; the [oversight
walkthrough][over-request] describes this request without showing it):

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

### Alice approves

The IdP reaches Alice through CIBA on her authenticator, with this
binding message ([oversight, Approval][over-approval]):

<!-- verbatim: draft-mcguinness-oauth-governed-agent-oversight.md -->
```text
agent-42 (client analysis-client) asks to write files in acme-data
```

She authenticates and approves at 12:07:40. The CIBA messages
themselves are outside these profiles. The approval covers this one
request; it is not standing authority.

### The client polls and receives the grant

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

Polls before Alice's decision returned `authorization_pending`. At
this poll, 12:07:45, the IdP checks again that `agent-42` is active,
that its binding still permits the request, that Alice's Delegation
Authorization still permits `files.write`, and that Alice is active.
It issues the grant the request would have produced (new):

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store
Pragma: no-cache

{
  "access_token": "ID_JAG_2",
  "issued_token_type": "urn:ietf:params:oauth:token-type:id-jag",
  "token_type": "N_A",
  "expires_in": 300,
  "scope": "files.write"
}
```

The decoded grant starts its lifetime at resolution (new):

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
correlation identifier. The client redeems `grant-2` as in scene 2 and
retries the write with the new access token.

A denial would have resolved to `access_denied` at the next poll, and
the client would not retry the request as self-acting access or under
another client. Disabling `agent-42` while the request waited would have
prevented issuance if the agent were still disabled at this poll. The
profile does not require disablement to cancel a pending request, so
the request may survive it; if it remains pending and every check
passes after the agent is re-enabled, it can still issue a grant. The
client can cancel its own request by revoking the deferral code.

## 5. Through an MCP gateway

The agent reaches the file service through an MCP gateway. The gateway
is the API for the agent's access token, and the client of every
server after it. MCP messages below follow MCP revision 2026-07-28;
like MCP's own examples, they omit the required `_meta` members, such
as the protocol version and client information.

### Get a gateway access token

The client exchanges Alice's ID Token as in scene 2, but for audience
`https://ras.gateway.example/`, resource `https://gateway.example/mcp`,
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

### Call a tool

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

The gateway validates the token and proof and applies the actor gate
for `agent-42` acting for Alice. Where it delegates the decision to an
AuthZEN policy decision point, it builds the subject and context from
the validated token, never from `client_id` alone (new; the [guide's
illustrative requests][guide-authzen] explain the member names, which
are illustrations, not a convention):

```json
{
  "subject": {"type": "user", "id": "gw-user-7"},
  "action": {"name": "read_file"},
  "resource": {"type": "file", "id": "report-7"},
  "context": {
    "agent": {"iss": "https://idp.example/", "sub": "agent-42"},
    "client": "analysis-gw",
    "scope": "tools.invoke"
  }
}
```

The decision point permits the call.

### Obtain a Continuation Assertion

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

### Continue to the file service

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

### Read the file and answer the agent

The gateway calls the API with a proof of G (new):

```http
GET /tenants/acme-data/files/report-7 HTTP/1.1
Host: api.example
Authorization: DPoP TARGET_ACCESS_TOKEN
DPoP: GW_API_PROOF
```

The API applies the same checks as in scene 2, including the actor gate
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

## 6. A gateway write held for approval

This scene continues scene 5. At 12:05:30, the agent asks the gateway
to write `report-7`. The gateway's token at the file service carries
only `files.read`, and the IdP requires Alice's approval before an
onward grant with `files.write` issues. The [guide][guide-gateway]
describes this flow; the messages below are new.

### The agent calls the tool and accepts a task

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

### The gateway asks for write authority and waits

The gateway obtains a new assertion for H0, `ICA_ASSERTION_2`, as in
scene 5, and sends the continuation exchange for `files.write`, opting
in to waiting:

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

The IdP performs every continuation check, reserves the assertion
against replay, records the pending request, and defers:

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
counts them again when the grant issues.

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
HTTP, the task identifier also goes in `Mcp-Name`, so that intermediaries
route the poll to the server instance that holds the task:

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

While Alice has not decided, the task stays `working` (excerpt):

```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "result": {
    "resultType": "complete",
    "taskId": "task-w1",
    "status": "working",
    "statusMessage": "Waiting for the user's approval."
  }
}
```

### Alice approves, and the gateway polls

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
scene 4. The decoded onward grant:

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

### The write completes

The gateway redeems `gw-grant-3` as in scene 5, writes the file, and
completes the task. The agent's next `tasks/get`, sent the same way
with a fresh proof, returns the tool's result (excerpt; the [MCP tasks extension][mcp-tasks] defines the full
shape):

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

The approval in this scene is the IdP's, on the continuation. A gateway
whose own policy requires a decision on each call holds the call the
same way under per-action oversight, but that decision is the
gateway's and does not satisfy the IdP's: each decision point applies
its own mode. A deployment that wants Alice asked once chooses where to
ask, for example IdP policy that selects human out of the loop for
`tool-gateway`'s continuations while the gateway decides on each call.

## 7. A scheduled run

Alice asks for a daily report that runs after she signs out. The agent's
operator runs a task service whose RAS is continuation-aware and acts
as CAI, and the IdP claims grant-anchored continuation.

### Anchor the chain while Alice is signed in

On September 17, the client presents Alice's refresh token, whose grant
has her Delegation Authorization for `agent-42` explicitly associated,
as the subject token (new; the [continuation's scheduled
variant][cont-scheduled-setup] describes this request without showing
it):

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

### Each run

At 06:00 UTC on September 18, with Alice signed out, the platform's
scheduler starts a run that names only `task-7`. The client
authenticates to the task service's RAS, which derives the hop from the
task record into a Transaction Token for the run; the client exchanges
it there for an assertion bound to K, and then continues at the IdP to
the file service. Those requests have the shape of scene 5's assertion
and continuation requests, with `analysis-client` as the client. The
onward ID-JAG (excerpt, [continuation, Each Scheduled
Run][cont-scheduled-run]):

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

Its `sub`, `act`, and `client_id` are those of scene 2's grant, so the
file service processes it as before. Its `auth_time` is still Alice's
sign-in of the previous day. No user credential was retained.

If Alice withdraws her Delegation Authorization for `agent-42`, the next
run fails with `invalid_continuation`, and her delegations to other
agents continue. Revoking the refresh-token grant that anchors the chain
also ends it.

## 8. Incident

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
gateway's next continuation fails with `invalid_continuation`.

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
blocks new redemption and refresh for the agent and revokes its
sessions, so introspection of `access-1` returns `"active": false` as
above.

### Re-enable

At 12:03, security operations re-enables the Agent with the same PATCH
and `"value": true` at the IdP, using ETag `W/"a3"`, and the connector
does the same at the RAS. New exchanges and redemptions succeed again.
Nothing revoked at 12:02 returns: `access-1` stays inactive, the ended
chains stay ended, and the client needs a new grant. A pending root
request, such as scene 4's, may survive the disablement. If it remains
pending and all checks pass after re-enabling, it can still issue a
grant, so deny or cancel requests that must not proceed.

## 9. Variants not traced here

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
* the approval channel: CIBA messages, and any approval page;
* AuthZEN decision responses;
* the scheduled run's Transaction Token and assertion requests; and
* per-action approval at an API, for which the oversight profile
  defines no wire format.

[oversight]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html
[over-request]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#walkthrough-request
[over-approval]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#walkthrough-approval
[over-resolution]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-oversight.html#walkthrough-resolution
[core-walkthrough]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#walkthrough
[core-client-assertion]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#client-assertion-example
[core-redemption]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html#redemption-example
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
[cont-scheduled-setup]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-scheduled-setup
[cont-scheduled-run]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-continuation.html#walkthrough-scheduled-run
[life-example]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#example
[life-signals]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#signal-examples
[life-platform]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-lifecycle.html#platform-example
[scim-onboarding]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-agent-federation.html#example
[scim-dedicated]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-agent-federation.html#dedicated-example
[oc-cimd]: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-scim-oauth-client-management.html#example-admit-a-cimd-client
[guide-authzen]: IMPLEMENTERS-GUIDE.md#illustrative-requests
[guide-gateway]: IMPLEMENTERS-GUIDE.md#approval-at-an-mcp-gateway
[mcp-tasks]: https://tasks.extensions.modelcontextprotocol.io/specification/2026-07-28/tasks
