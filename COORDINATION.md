# Coordination Notes for OAuth 2.0 Profile for Governed Agent Federation

This file keeps the full coordination notes that the draft's
"Dependencies and Deferred Work" appendix summarizes. They list what the
profile needs from the specifications it depends on, and the compositions
it defers, in more detail than the draft carries before working-group
adoption. Backquoted names refer to anchors and references in
`draft-mcguinness-oauth-governed-agent-federation.md`.

## Dependencies and Deferred Work

This informative appendix records dependencies and deferred work.
Assessed revisions: WAG-01, ID-JAG-04, ICA-02, Actor
Profile-00, SPIFFE OAuth-02, ATTEST-11, WIT-02, CIMD-02, Client Instance
Identification-00, and Client Attester Endorsement-00.

### Upstream Dependencies

| Specification | What this profile needs | Consequence until resolved |
|---|---|---|
| WAG | Registration of the WAG token type and JWT type, and alignment on protection, linking, and subject presentation (`wag-gaps`) | The WAG token type and JWT type remain provisional values |
| ID-JAG | Bound-grant example aligned with the normative `jwt-bearer` grant type, and grant-confirmation errors separated from RFC 9449 proof errors (`bound-grant-coordination`) | Confirmation checks are applied to `jwt-bearer` here |
| Actor Profile | A reusable principal-resolution extension point separating credential validation, identity mapping, and actor construction; a grant-level condition for `jti` single use (below) | The mapping is defined locally in `actor-construction`; this profile states its own grant replay rule |

#### WAG

In WAG-01 the Platform signs the grant (Section 2 of WAG).
`wag-issuance` defines issuance by an IdP acting as that Platform.
Coordination is needed on:

* **Identifiers:** WAG-01 defines neither a token type nor an explicit
  JWT type. Section 8 of WAG lists the JWT type as open, and Section 9
  notes the risk of another JWT being taken for the grant. This document
  uses `urn:ietf:params:oauth:token-type:wag` and `wag+jwt` as
  provisional values and requires the RAS to check the JWT type.
  Registering them needs agreement. Advertising them and the self-acting
  profile URIs in ID-JAG's metadata parameters (`server-metadata`)
  also needs agreement.
* **Protection:** WAG-01 is a bearer grant; Section 8 of WAG lists proof
  of possession as open. This document proposes DPoP binding at issuance and redemption
  under `grant-protection`.
* **Linking:** WAG accepts previously unseen agents on their first
  assertion (Section 3 of WAG), and Section 9 lets an authorization
  server cap new agents. Governed agents
  instead require an authorized local correlation, established in
  advance or, where resource policy permits, just in time
  (`wag-redemption`).
* **Renewal:** This document adopts WAG's prohibition on refresh tokens;
  continuing self-acting access re-issues the grant. Section 5 of WAG-01
  adds that access tokens SHOULD NOT outlive the assertion by a
  significant period; this document leaves access-token lifetime to RAS
  policy. Decision pending: adopt the SHOULD, or state the difference.
* **Client registration:** Section 5 of WAG-01 says an authorization
  server MUST NOT require a client registration per Agent. This
  document's mandatory path resolves the agent from a dedicated client,
  one Agent Principal per client identity at the IdP. Decision pending:
  whether that conflicts at the RAS, where the client redeems the WAG.
* **Subject presentation:** A token exchange in which the authenticated
  client is the subject, by permitting omission of `subject_token` in
  that case or by registering a subject token type for authenticated
  client context. That would simplify the presentation this document
  defines, in which JWT-authenticated clients repeat their
  authentication JWT as the subject token (`wag-request`), and would
  give X.509-SVID authentication a self-acting path.
* **Management:** `AGENT-MANAGEMENT` administers Client Associations
  for delegated issuance only; self-acting permission needs a flow
  dimension there.

#### ID-JAG Bound Grants

Section 4.4 of ID-JAG requires `jwt-bearer` while its bound-grant example
uses `jwt-dpop`. This profile follows the normative grant type with
explicit confirmation processing (`redemption`) and takes no
dependency on JWT DPoP Grant.

#### Grant Replay and Re-redemption

Section 4.4.3 of ID-JAG lets a client re-submit an unexpired ID-JAG for
a new access token, and Section 8 of WAG leaves replay open. This
profile decides by the grant's own binding (`redemption-common`): an
unbound grant is single-use, and the RAS may accept a bound grant again
under explicit policy with a fresh proof matching its `cnf.jkt`.

Section 4.2 of ACTOR-PROFILE instead makes single use depend on whether
the token endpoint requires DPoP or mutual TLS. That exempts an unbound
grant redeemed with a DPoP proof that only binds the access token.
Tracked in
https://github.com/mcguinness/draft-mcguinness-oauth-actor-profile/issues/5.

#### Client Instance Identification

This document composes `INSTANCE` as evidence beside the governed agent:
an instance identifier selects the Agent Principal only through an
exact, approved managed-installation binding, and the RAS conveys instance context only for an instance it validated. Two items
for the `INSTANCE` draft:

* **Appendix A.3 example:** it names the issuing authorization server as
  `act.iss`. Under governed actor preservation, the RAS keeps the IdP's
  issuer in `act.iss`, so the example should use an IdP issuer distinct
  from the token issuer.
* **Grant-carried context:** if a deployment needs the instance that
  obtained the grant, not only the one that redeemed it, this document
  would become a consuming profile under Section 7.4 of `INSTANCE` and
  define provenance and association for context in the ID-JAG or WAG.

#### Resolution from Authentication Context

This document explicitly defines delegated issuance from validated
authentication context and an approved Identity Binding, without
`actor_token`: dedicated-client identity under `client-assertion-input`
or the SPIFFE and Client Attestation identities under
`optional-input-profiles`.
ID-JAG makes that parameter optional and leaves actor processing to
extensions (Section 9.7 of ID-JAG); its omission alone does not establish
this composition.

Appendix A.1 of `RFC8693` describes a subject-only request as
impersonation. Section 6.3.1 of ACTOR-PROFILE permits authentication-context
reuse only when the same client assertion is also present as
`actor_token`, and requires the client subject as `act.sub`.
Neither defines these mapped authentication-context inputs.

Coordination with Actor Profile and ID-JAG is needed on this explicit
extension: trusted configuration selects the resolution input,
separate mapping and authorization checks establish the governed actor,
and the issued ID-JAG contains `act`. Generic Token Exchange or Actor
Profile support does not advertise support for this composition.

### Deferred Compositions

#### Grant Key Transition

A control plane obtaining a bound grant for redemption by a different
worker needs an authorized proof-key transition. This document defines
no such transition: the holder of the issuance key also redeems the
grant (`distributed-key-use`). A future composition would need to bind
the new key without weakening the applicable grant protection.

#### Portable Authorization Deadlines

A portable IdP-imposed deadline on downstream access needs an
authenticated claim or reference, its association with the delegation,
and enforcement rules for access tokens and refresh authorization.
That composition is outside the scope of this document. ID-JAG `exp`
remains the redemption limit; it cannot communicate a deadline for
subsequent access (`authorization-lifetime`).

#### User Access Tokens as Subjects

Deployed on-behalf-of (OBO) flows, including `AWS-AGENTCORE-OBO`, use a user
access
token as input. This document accepts ID-JAG's ID Token, SAML, and
refresh-token subjects; it defines no access-token subject composition.
Such a composition needs rules for token eligibility and audience,
user/client/actor resolution, sender constraints, and the authority to
request downstream access. Coordinate those rules with ID-JAG;
changing only `subject_token_type` does not establish them.

#### Excluded Compositions

The following compositions are not defined in this document. Their
exclusion does not prevent the independently supported uses listed here.

| Composition | Boundary in this document |
|---|---|
| Asynchronous approval with `AROP` | No approval transport or completion flow; external approval remains subject to `external-approval` and the lifetime limits in `authorization-lifetime` |
| Continuation with `ICA` | No ICA issuance or continuation chain; supported renewal follows `continuing-access` |
| General WIMSE WIT/WIC inputs | WIT-SVID and X.509-SVID resolution is defined in `spiffe-input`; non-SPIFFE credentials need an explicit OAuth presentation and proof composition |
| Instance context carried in an ID-JAG or WAG, or preserved across domains, under `INSTANCE` | The RAS conveys only an instance it validated (`access-token-response`); instances resolve the agent only through a managed-installation binding (`agent-evidence`). Preservation would need this profile to define provenance and association under Section 7.4 of `INSTANCE` |
| Mutual-TLS-bound ID-JAG | Bound grants use DPoP. Mutual TLS remains available for access-token protection under `access-token-protection` |
| Rich Authorization Requests without scope | This profile requires meaningful scope alongside any authorization details; it does not define the scope-free mode permitted by `RFC9396` |

### Operational Dependencies

Provisioning, account linking, and lifecycle propagation are deployment
choices. Useful controls include:

* Authenticate the authority creating or changing a link, or verify
  control of both accounts in a user-linking flow.
* Authorize just-in-time creation of user accounts and agent
  correlations by issuer and tenant, the latter under
  `jit-correlation`; avoid silent merges and reactivation of disabled
  accounts.
* Retain ownership, groups, and entitlements with their principal;
  audit link and binding changes.
* Preserve issuer and tenant context when using the System for
  Cross-domain Identity Management (SCIM) `externalId` attribute
  `RFC7643`.

SCIM `RFC7644` and Agent resources `SCIM-AGENT` provide building
blocks, not a lifecycle propagation contract.

#### Provisioning and Disablement

Consistent correlation and disablement across IdP and RAS need an agreed
provisioning and enforcement contract. `AGENT-LIFECYCLE` profiles SCIM,
optional Shared Signals, and the effects of applied changes on authorization.
It distinguishes current administrative state from revocation history and
states the limits of missed-event recovery and token enforcement. Stronger
guarantees across unobserved transitions require an additional composition.
The companion is not required for conformance to this federation profile;
`agent-correlation` and `status-changes` state this document's guarantees.
