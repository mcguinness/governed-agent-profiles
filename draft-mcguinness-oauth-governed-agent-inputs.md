---
title: "Agent Resolution Input Profiles for Governed Agent Federation"
abbrev: "Governed Agent Inputs"
category: std
docname: draft-mcguinness-oauth-governed-agent-inputs-latest
submissiontype: IETF
stand_alone: yes
ipr: trust200902
area: "Security"
workgroup: "Web Authorization Protocol"
keyword:
 - OAuth
 - agent identity
 - SPIFFE
 - client attestation
 - workload identity
venue:
  group: "Web Authorization Protocol"
  type: "Working Group"
  mail: "oauth@ietf.org"
  arch: "https://mailarchive.ietf.org/arch/browse/oauth/"
  github: "mcguinness/governed-agent-profiles"
  latest: "https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-inputs.html"
author:
 - fullname: Karl McGuinness
   organization: Independent
   email: public@karlmcguinness.com
normative:
  FEDERATION:
    title: "OAuth 2.0 Profile for Governed Agent Federation"
    author:
      - name: Karl McGuinness
    date: 2026-10-09
    seriesinfo:
      Internet-Draft: draft-mcguinness-oauth-governed-agent-federation
    target: https://mcguinness.github.io/governed-agent-profiles/draft-mcguinness-oauth-governed-agent-federation.html
  ATTEST: I-D.ietf-oauth-attestation-based-client-auth
  ATTESTER-ENDORSEMENT: I-D.mcguinness-oauth-client-attesters
  INSTANCE: I-D.mcguinness-oauth-client-instance-id
  RFC8705:
  RFC9449:
  SPIFFE-OAUTH: I-D.ietf-oauth-spiffe-client-auth
  WIT: I-D.ietf-wimse-workload-creds

--- abstract

This document defines optional agent-resolution input profiles for the
OAuth 2.0 Profile for Governed Agent Federation: SPIFFE JWT-SVIDs,
WIT-SVIDs, and X.509-SVIDs, and OAuth Attestation-Based Client
Authentication, including resolution of managed installations by client
instance identifier. Each profile satisfies the federation profile's
agent-resolution input contract and is claimed separately.

--- middle

# Introduction

{{FEDERATION}} resolves an authenticated OAuth client or workload
identity to a governed Agent Principal through an Identity Binding. It
defines the agent-resolution input contract, two inputs
(dedicated-client identity and the existing platform JWT), and the
issuance, redemption, and resource processing that every input shares.

This document defines further inputs: SPIFFE JWT-SVIDs, Client
Attestation, including resolution of a managed installation behind a
shared client, and SPIFFE WIT-SVIDs and X.509-SVIDs. Each satisfies the
input contract of {{FEDERATION}}, resolves from authentication context
with actor-token parameters omitted, and requires trusted configuration.
An implementation that claims none of these inputs does not need this
document.

## Conventions and Terminology

{::boilerplate bcp14-tagged-bcp14}

Agent Principal, Identity Binding, Client Association, credential class,
Governance Tenant, Target Tenant, and grant proof key follow
{{FEDERATION}}. Client Attestation terminology follows {{ATTEST}}.

# Conformance {#conformance}

The following inputs are OPTIONAL: SPIFFE JWT-SVID ({{jwt-svid-input}}),
Client Attestation ({{agent-evidence}}), and SPIFFE WIT-SVID and
X.509-SVID ({{spiffe-input}}).

For each input it claims, the IdP, RAS, and client MUST implement that
input's requirements in this document together with {{FEDERATION}}.
Conformance claims under {{FEDERATION}} name each supported input of
this document.

# Common Rules for These Inputs

## Grant Lifetime {#lifetime}

Under the grant lifetime rule of {{FEDERATION}}, these inputs bound the
grant as follows:

| Input | Lifetime bound on the grant |
|---|---|
| JWT-SVID | Its `exp` |
| WIT-SVID and Client Attestation | The credential's `exp`; the PoP JWT adds no limit |
| X.509-SVID | The earliest `notAfter` in the validated certificate path, excluding the trust anchor |
{: title="Grant lifetime bound by input"}

## Algorithms {#algorithms-inputs}

Implementations that support the JWT-SVID input MUST support this
capability in addition to those of {{FEDERATION}}:

| Artifact | Mandatory-to-implement (MTI) capability |
|---|---|
| JWT-SVID, where supported | IdP validation: `RS256` under {{Section 3.1 of SPIFFE-OAUTH}}, plus `ES256` added by this profile |
{: title="Mandatory-to-implement algorithm for JWT-SVIDs"}

# SPIFFE JWT-SVID {#jwt-svid-input}

This OPTIONAL input identifies workloads independently of the OAuth
client identifier, including multiple agents behind a shared client.
JWT-SVID client authentication at either the IdP or the RAS follows this
section.

* **Presentation:** Client authentication by `client_assertion` with
  `client_assertion_type`
  `urn:ietf:params:oauth:client-assertion-type:jwt-spiffe`.
* **Validation:** Before resolving the agent, the IdP MUST apply
  {{Section 3.1 of SPIFFE-OAUTH}}, including the assertion type, and
  {{Section 5 of SPIFFE-OAUTH}} and {{Section 6 of SPIFFE-OAUTH}} for
  trust establishment and key distribution. It MUST also verify the
  signature, before resolving the agent, with keys authorized for the
  SPIFFE ID's trust domain. An
  optional `iss` MUST NOT select another trust domain or key authority.
* **Resolution:** The IdP MUST resolve the exact SPIFFE ID in the
  validated `sub` through an Identity Binding ({{FEDERATION}}). The
  SPIFFE ID's association with the authenticated client is an
  authentication check, not an Identity Binding or Client Association.
* **Proof:** A JWT-SVID is bearer evidence: DPoP, when used, binds the
  issued grant to the grant proof key, not the JWT-SVID to its
  presenter. A policy requiring issuer-bound presenter proof MUST reject
  this input rather than treat DPoP as that proof
  ("Bearer Evidence Limits" in {{FEDERATION}}).

# Client Attestation {#agent-evidence}

This OPTIONAL input maps the attested OAuth client identity explicitly
to one Agent Principal. It relies on a trusted attester's attestation of
the client identity and confirmation key, not a registered client key.
It establishes runtime or workload provenance only as far as verified
attestation claims and the attester's trusted issuance policy support.
It does not distinguish agents behind a shared client, except through
the managed-installation binding below. Otherwise those agents need
distinct workload evidence, such as a JWT-SVID or platform JWT.

* **Presentation:** Client authentication with the configured {{ATTEST}}
  method.
* **Validation:** The IdP MUST validate the attestation and proof under
  {{ATTEST}} before resolving the agent. It MUST identify the attester
  unambiguously from the trusted verification key and configured
  attester-to-client associations. An `iss`, when present, MUST match
  that attester.
* **Attester endorsement:** The IdP MAY derive the attester-to-client
  association from an endorsement it accepts under
  {{Section 2.1 of ATTESTER-ENDORSEMENT}}. An endorsement MUST NOT
  create or change an Identity Binding or Client Association. Because
  the binding names the attester, a newly endorsed attester resolves no
  Agent Principal until an Identity Binding names it. An endorsement
  accepted under that policy is not client metadata acting by itself
  ("Authentication, Resolution, and Proof" in {{FEDERATION}}).
* **Resolution:** The IdP MUST resolve the trusted attester and the
  validated `sub` through an approved Identity Binding
  ("Identity Binding" in {{FEDERATION}}).
* **Managed installation:** Where agents share one OAuth client, a
  Client Attestation carrying `client_instance_id` under {{INSTANCE}}
  MAY resolve the agent instead. The IdP MUST accept it only from an
  attester configured to assign that identifier at Installation
  granularity ({{Section 1.1 of INSTANCE}}) under the continuity rules
  of {{Section 6 of INSTANCE}}. The Identity Binding names the exact
  attester, client (`sub`), IdP Receiver Scope, and
  `client_instance_id`. Trusted configuration for the client selects
  client-level or installation-level resolution. Attestation claims MUST
  NOT select the level, and a failed match MUST NOT fall back to the
  other level. A new enrollment yields a new identifier that needs its
  own approved Identity Binding. The IdP MUST NOT infer continuity
  across identifiers or attesters.
* **Proof:** With `attest_jwt_client_auth`, any grant proof key MUST
  match the attestation's confirmation key. This narrows the allowance
  in {{Section 5.2 of ATTEST}} for a separate DPoP key. With
  `attest_jwt_client_auth_dpop`, one DPoP proof serves both roles. Key
  retention follows {{resolution-key-lifecycle}}.

With {{INSTANCE}}, instance keys differ per receiver scope
({{Section 4.1 of INSTANCE}}). A bound grant carries the IdP-scoped key.
A client that also authenticates to the RAS with a Client Attestation
therefore uses `attest_jwt_client_auth` there and proves the grant key
with a separate DPoP proof, unless the IdP and RAS share a receiver
scope.

# SPIFFE WIT-SVID and X.509-SVID Resolution {#spiffe-input}

These OPTIONAL inputs resolve the SPIFFE ID validated during OAuth
client authentication for this token request, in the SVID class that the
client and IdP configure. General non-SPIFFE Workload Identity Token
(WIT) and Workload Identity Certificate (WIC) inputs of {{WIT}} are
excluded ("Excluded Compositions" in {{FEDERATION}}). One shared SPIFFE
ID cannot distinguish independently governed agents. Either input proves
control of a credential-bound key. Assurance about a particular runtime
or execution depends on the credential authority's issuance rules and
identity granularity. {{svid-context-example}} illustrates both inputs.

## WIT-SVID

* **Presentation:** The WIT-SVID in `OAuth-Client-Attestation`, with its
  proof in `OAuth-Client-Attestation-PoP`.
* **Validation:** The IdP MUST apply {{Section 3.3 of SPIFFE-OAUTH}} and
  {{WIT}}, including their client-identifier association, trust,
  validity, and proof requirements. It MUST require `typ=wit+jwt`. It
  MUST validate possession of the key in `cnf.jwk` through the Client
  Attestation PoP JWT. A WIT-SVID MUST NOT be accepted as bearer
  evidence. Its optional `iss` MUST NOT select a different trust domain
  or key authority.
* **Resolution:** The IdP MUST resolve the approved trust domain and
  exact SPIFFE ID in the validated `sub` through an Identity Binding
  ({{FEDERATION}}).
* **Proof:** When DPoP is used at issuance, its key MUST match the
  WIT-SVID's `cnf.jwk`. The IdP MUST compare the JWK thumbprints of the
  DPoP key and `cnf.jwk` as used in {{RFC9449}} and MUST reject a
  mismatch with `invalid_grant`.
  This carries the WIT-endorsed key into the grant binding; the Client
  Attestation PoP JWT remains required. Key retention follows
  {{resolution-key-lifecycle}}.

## X.509-SVID

* **Presentation:** The client certificate on the mutual-TLS connection
  carrying the token request.
* **Validation:** The IdP MUST apply {{Section 3.2 of SPIFFE-OAUTH}} and
  {{RFC8705}} to the certificate and proof established by mutual TLS
  for this request. This includes their client-identifier association,
  trust, validity, and proof requirements. A certificate supplied only
  in a request parameter or an untrusted forwarding header MUST NOT
  establish the workload identity, and the request then fails client
  authentication. TLS termination follows {{Section 6.5 of RFC8705}}.
* **Resolution:** The IdP MUST resolve the approved trust domain and
  exact SPIFFE ID in the certificate's URI Subject Alternative Name
  through an Identity Binding ({{FEDERATION}}).
* **Proof:** A DPoP grant proof key, when required, is proven on the
  same token request. It MAY differ from the certificate key, because
  mutual TLS can terminate separately from the component generating DPoP
  proofs. The certificate does not endorse the DPoP key; the
  authenticated request associates it with this issuance, and the grant
  uses `cnf.jkt`, not certificate confirmation.

# Resolution-Key Lifecycle {#resolution-key-lifecycle}

When the resolution key is also the grant proof key, replacing it does
not rebind an outstanding grant, access token, or refresh token. This
is the case for WIT-SVID or Client Attestation when DPoP is used.
Continued use requires retaining the corresponding proof key.
Otherwise, the client obtains a new grant with the replacement key and
new RAS authorization. Any subject-credential binding still applies and
may require a new subject credential. Key migration is deferred
("Excluded Compositions" in {{FEDERATION}}).

# Security Considerations

The security considerations of {{FEDERATION}} apply, including its
bearer evidence limits. In the JWT-SVID path, the same bearer credential
also satisfies client authentication, so that check is not an
independent possession factor.

Managed-installation resolution relies on the attester's continuity
evidence and enrollment controls ({{Section 9 of INSTANCE}}).

# Privacy Considerations

The privacy considerations of {{FEDERATION}} apply. Client instance
identifiers are scoped per receiver under {{Section 10 of INSTANCE}}.

# IANA Considerations

This document has no IANA actions.

--- back

# Input Variants {#input-variants}

These non-normative variants change only the agent-resolution input of
the dedicated-client walkthrough in {{FEDERATION}}; the message sequence
is unchanged. The resulting actor is always the IdP issuer and
`agent-42`.

| Variant | Authentication and presentation | Identity resolved |
|---|---|---|
| Shared client with JWT-SVID | JWT-SVID as `client_assertion`, with `client_assertion_type` `jwt-spiffe` | Approved trust domain and exact SPIFFE ID in `sub` ({{jwt-svid-input}}) |
| WIT-SVID | `spiffe_wit`: WIT-SVID in `OAuth-Client-Attestation`, with a fresh PoP header signed by its key | Exact SPIFFE ID in the validated `sub` ({{spiffe-input}}) |
| X.509-SVID | `spiffe_x509`: mutual-TLS authentication with the X.509-SVID | Exact URI Subject Alternative Name ({{spiffe-input}}) |
{: title="Input variants relative to the dedicated-client walkthrough"}

The JWT-SVID variant uses IdP `client_id` `platform-sso`. The WIT-SVID
and X.509-SVID variants use the SPIFFE ID as `client_id`. Across the
variants:

* **Proof key:** In the bound profile, K signs the issuance DPoP proof,
  except that the WIT-SVID variant uses the WIT-SVID key. The
  X.509-SVID variant's DPoP key may differ from its TLS key.
* **Lifetime:** The input bounds the grant lifetime under {{lifetime}}.
* **Client Association:** Each variant needs a Client Association for
  its authenticated client. The JWT-SVID variant needs a separate one
  for `platform-sso`. In the WIT-SVID and X.509-SVID variants, where the
  authenticated client is the workload itself, the association can be
  administered together with the binding.
* **Negative tests:** The dedicated-client negative tests of
  {{FEDERATION}} apply to each binding, except that replay rules follow
  the input specification.

## Identity Mapping Example {#identity-example}

Alice asks a data-analysis agent to read a file. The platform uses one
shared OAuth client for many agents, so its client identifier alone
cannot identify which agent is acting. This non-normative example uses
the optional SPIFFE input to make that distinction through four separate
decisions:

1. **Resolve the agent.** The IdP validates the workload's JWT-SVID, and
   an Identity Binding maps its exact SPIFFE ID,
   `spiffe://platform.example/accounts/acme/agents/workload-7`, to
   `agent-42` in the namespace of `https://idp.example/`, in Governance
   Tenant `acme`.
2. **Authorize the client.** The IdP's configured SPIFFE association
   authenticates the caller as `platform-sso`, and a separate Client
   Association permits that client to use this binding for delegated
   ID-JAG issuance.
3. **Authorize delegation.** Alice's ID Token, issued for
   `platform-sso`, identifies her as `alice-app`. The IdP authorizes
   `agent-42` to act for her with `files.read` at the requested resource
   in Target Tenant `acme-data` and issues an ID-JAG.
4. **Apply resource policy.** The RAS resolves Alice to local user
   `user-108` and correlates the agent with local principal
   `service-principal-42`. Alice has the file permission, and resource
   policy permits this agent to act for her; the agent needs no file
   permission of its own.

| Claim | ID-JAG issued by IdP | Access token issued by RAS |
|---|---|---|
| `sub` (Alice) | `alice-ras` | `user-108` |
| `act.iss` (agent namespace) | `https://idp.example/` | `https://idp.example/` |
| `act.sub` (Agent Principal) | `agent-42` | `agent-42` |
| `client_id` (client at RAS) | `platform-api` | `platform-api` |
| `scope` | `files.read` | `files.read` |
{: title="Identity claims across the domain boundary"}

The RAS translates the user and preserves the agent:

* `alice-ras` is Alice's identifier in the target SSO namespace.
* `platform-api` is the registration corresponding to `platform-sso` at
  the RAS.
* The local agent record `service-principal-42` supports authorization
  but does not replace `act.sub`.

## Shared Platform Client with SPIFFE {#shared-client-example}

This variant completes {{identity-example}}. The workload obtains a
JWT-SVID with the IdP issuer as its audience. The existing SPIFFE format
omits `iss` and `iat`, and the expiration is an illustrative NumericDate
value. The IdP selects trusted signing keys from its configured bundle
for the `platform.example` trust domain.

~~~ json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "spiffe-key-1"
}
~~~

~~~ json
{
  "sub": "spiffe://platform.example/accounts/acme/agents/workload-7",
  "aud": ["https://idp.example/"],
  "exp": 1789647063
}
~~~

The JWT-SVID authenticates the client through the configured SPIFFE
association and resolves the agent separately. It is bearer evidence and
does not attest that grant proof key K belongs to the workload.
`platform-api` replaces `analysis-api` in grants, access tokens, and RAS
client authentication.

## WIT-SVID and X.509-SVID {#svid-context-example}

Both variants resolve the workload authenticated on the exchange request
through an exact Identity Binding from
`spiffe://platform.example/agents/analysis` to `agent-42`. The user ID
Token is issued to that authenticated client, not reused from
`analysis-client`. The WIT-SVID carries the SPIFFE ID in `sub` and the
workload public key in `cnf.jwk`. For X.509-SVID, mutual-TLS
authentication replaces the two attestation headers. An authoritative
association supplies the downstream client identifier in both cases.

# Document History

RFC Editor: Remove this section before publication.

* Initial version.
