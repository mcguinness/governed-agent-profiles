# Coordination Notes for OAuth 2.0 Profile for Governed Agent Federation

This file keeps the full coordination notes that the draft's
"Dependencies and Deferred Work" appendix summarizes. They list what the
profile needs from the specifications it depends on, and the compositions
it defers, in more detail than the draft carries before working-group
adoption. Backquoted names refer to anchors and references in
`draft-mcguinness-oauth-governed-agent-federation.md`.

## Dependencies and Deferred Work

This informative appendix records dependencies and deferred work.
Assessed revisions: WAG-00, ID-JAG-04, ICA-02, Actor
Profile-00, SPIFFE OAuth-02, ATTEST-11, WIT-02, CIMD-02, and the
current drafts of Client Instance Identification and Client Attester
Endorsement.

### Upstream Dependencies

| Specification | What this profile needs | Consequence until resolved |
|---|---|---|
| WAG | Registration of the WAG token type and JWT type, and alignment on protection, linking, and subject presentation (`wag-gaps`) | The WAG token type and JWT type remain provisional values |
| ID-JAG | Bound-grant example aligned with the normative `jwt-bearer` grant type, and grant-confirmation errors separated from RFC 9449 proof errors (`bound-grant-coordination`) | Confirmation checks are applied to `jwt-bearer` here |
| Actor Profile | A reusable principal-resolution extension point separating credential validation, identity mapping, and actor construction | The mapping is defined locally in `actor-construction` |

#### WAG

Section 5 of WAG anticipates IdP issuance through Token Exchange
without specifying it and lists issuer placement among its open
questions. `wag-flow` defines that composition. Coordination is
needed on:

* **Identifiers:** The token type `urn:ietf:params:oauth:token-type:wag`
  and the JWT type `wag+jwt` are WAG's to register; this document uses
  them as provisional values. Advertising them and the self-acting
  profile URIs in ID-JAG's metadata parameters (`server-metadata`)
  also needs agreement.
* **Protection:** WAG-00 is a bearer grant with proof of possession
  open. This document proposes DPoP binding at issuance and redemption
  under `grant-protection`.
* **Linking:** Section 7 of WAG requires acceptance of previously
  unseen agent identifiers under trusted issuers. Governed agents
  instead require an authorized local correlation, established in
  advance or, where resource policy permits, just in time
  (`wag-redemption`).
* **Renewal:** This document adopts WAG's prohibition on refresh tokens;
  continuing self-acting access re-issues the grant.
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
| Instance-based resolution or propagated instance context under `INSTANCE` | Workload evidence resolves the agent; no per-instance enrollment or continuity protocol is required. Shared workload identity does not distinguish replicas `SPIFFE-CONCEPTS` |
| Client attester endorsement under `ATTESTER-ENDORSEMENT` | Attester trust is configured under `agent-evidence` |
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
