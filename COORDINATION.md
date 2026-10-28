# Coordination Notes for OAuth 2.0 Profile for Governed Agent Federation

This file keeps the full coordination notes that the draft's
"Differences, Dependencies, and Excluded Compositions" appendix
summarizes. They list what the profile needs from the specifications it
depends on, and the compositions it defers, in more detail than the
draft carries before working-group adoption. Backquoted names refer to
anchors and references
in `draft-mcguinness-oauth-governed-agent-federation.md`, except where a
note names the input profiles companion
(`draft-mcguinness-oauth-governed-agent-inputs.md`, `INPUTS`) or the
implementer's guide (`IMPLEMENTERS-GUIDE.md`).

## Dependencies and Deferred Work

These notes record dependencies and deferred work.
Assessed revisions: WAG-01, ID-JAG-04, ICA-02, Actor
Profile-01, SPIFFE OAuth-02, ATTEST-11, WIT-02, CIMD-02, Client Instance
Identification-00, Client Attester Endorsement-00, and WISE draft 03.

### Upstream Dependencies

| Specification | What this profile needs | Consequence until resolved |
|---|---|---|
| WAG | Registration of the WAG token type and JWT type, and alignment on protection, linking, and subject presentation (`wag-gaps`) | The WAG token type and JWT type remain provisional values |
| ID-JAG | Bound-grant example aligned with the normative `jwt-bearer` grant type, and grant-confirmation errors separated from RFC 9449 proof errors (below) | Confirmation checks are applied to `jwt-bearer` here |
| Actor Profile | A reusable principal-resolution extension point separating credential validation, identity mapping, and actor construction | The mapping is defined locally in `actor-construction` |
| COAZ-MCP | A trusted agent identity: from `act` for delegated tokens and the subject for self-acting tokens, supplied or verified by the enforcement point, never from a declared mapping or `client_id` (below) | Governed deployments configure their enforcement points themselves; this profile defines no AuthZEN mapping |

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

Resolved in Actor Profile-01
(https://github.com/mcguinness/draft-mcguinness-oauth-actor-profile/issues/5):
Section 4.2 of ACTOR-PROFILE now makes a grant without an enforced
grant-level sender constraint single-use, and a proof used only for
client authentication or to bind the issued token is not such a
constraint. The two rules agree.

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

#### Shared Signals: WISE and CAEP

The family uses WISE (OpenID Shared Signals WG, draft 03) for workload
facts and CAEP for sessions and IdP risk:

* **Platform to IdP:** WISE credential and posture events about
  platform-hosted agents, with an RFC 9493 `aliases` subject carrying
  both the WISE `uri` workload identifier and `iss_sub` for the governed
  Agent Principal (`platform-signals`). WISE names only the `uri`
  format; coordination is needed so that an `aliases` subject including
  `iss_sub` is a recognized WISE subject for governed agents.
* **Credential authority to IdP:** WISE credential and trust events stop
  resolution through the affected credentials and trust material
  (`time-validation`).
* **Lifecycle state:** WISE `workload-enabled` carries state. This
  family keeps the notice-then-retrieve asymmetry, so enabled events
  only trigger retrieval (`scim-events`).
* **Agent principal:** CAEP `risk-level-change` requires a `principal`,
  and neither CAEP nor SSF defines one for an agent; stream
  configuration fixes it today. A registered agent principal value in
  CAEP or SSF would remove that configuration.
* **Reference:** draft 03 is cited at its working-group editor's copy;
  move the reference to openid.net once a revision is published there.

#### Resolution from Authentication Context

This document explicitly defines delegated issuance from validated
authentication context and an approved Identity Binding, without
`actor_token`: dedicated-client identity under `client-assertion-input`
or the SPIFFE and Client Attestation identities defined in
`INPUTS`.
ID-JAG makes that parameter optional and leaves actor processing to
extensions (Section 9.7 of ID-JAG); its omission alone does not establish
this composition.

Appendix A.1 of `RFC8693` describes a subject-only request as
impersonation. Section 6.4.1.2 of ACTOR-PROFILE permits authentication-context
reuse only when the same client assertion is also present as
`actor_token`, and requires the client subject as `act.sub`.
Neither defines these mapped authentication-context inputs.

Coordination with Actor Profile and ID-JAG is needed on this explicit
extension: trusted configuration selects the resolution input,
separate mapping and authorization checks establish the governed actor,
and the issued ID-JAG contains `act`. Generic Token Exchange or Actor
Profile support does not advertise support for this composition.

#### AuthZEN and COAZ-MCP

`policy-services` lets an API delegate evaluation to a policy decision
service, names AuthZEN as one optional interface, and defines no
mapping. The service must keep the user, the issuer-qualified Agent
Principal, and the OAuth client distinct, and the client identifier
must not stand in for the actor (`actor-authorization`).

AuthZEN Authorization API 1.0 defines a subject with `type`, `id`, and
`properties`, and no member for an actor acting on behalf of a subject.
COAZ-MCP Draft 1 (February 2026) takes the subject from the token's
`sub` (Section 3.1) and, in its default `tools/call` mapping (Section
7.1), puts the agent in `context.agent`, "typically `$token.?client_id`".
It does not read `act` or mention token exchange. For a governed
delegated token, that default names the platform's shared client, or
in a further domain the continuing gateway, as the agent for every agent
behind it.

Changing the mapping's source to `act` is not enough on its own.
COAZ-MCP treats every attribute a server-declared mapping produces,
other than the verified `subject.id`, as untrusted input (Section 11.4),
and it verifies only `subject.id` against the token (Section 8). A
declared mapping could therefore supply another agent's identity in
`context.agent` and obtain an actor-gate decision for that agent.

Suggested change for the OpenID AuthZEN working group:

* The enforcement point supplies or verifies the agent identity, like
  `subject.id`, from the validated access token: from `act` (`iss` and
  `sub`) for delegated tokens, and as the subject for tokens with no
  user, such as those derived from a WAG. The case follows the token
  population configured for the resource, not the presence of `act`.
* `client_id` stays a separate attribute and never stands in for the
  agent.
* A declared mapping does not supply or override these attributes.

A reusable vocabulary for these context members belongs in COAZ-MCP,
not in these profiles, whose examples are illustrations only. Not yet
filed. The implementer's guide ("Authorization decisions with AuthZEN")
shows the enforcement point's inputs and the default mapping as a
counter-example.

### Deferred Compositions

#### Grant Key Transition

A control plane obtaining a bound grant for redemption by a different
worker needs an authorized proof-key transition. This document defines
no such transition: the holder of the issuance key also redeems the
grant (the implementer's guide, "Distributed platforms and key use"). A future composition would need to bind
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
| Continuation with `ICA` | Defined for governed grants in the continuation companion (`CONTINUATION`, below); renewal without continuation follows `continuing-access` |
| General WIMSE WIT/WIC inputs | WIT-SVID and X.509-SVID resolution is defined in `spiffe-input` of `INPUTS`; non-SPIFFE credentials need an explicit OAuth presentation and proof composition |
| Instance context carried in an ID-JAG or WAG, or preserved across domains, under `INSTANCE` | The RAS conveys only an instance it validated (`access-token-response`); instances resolve the agent only through a managed-installation binding (`agent-evidence` of `INPUTS`). Preservation would need this profile to define provenance and association under Section 7.4 of `INSTANCE` |
| Mutual-TLS-bound ID-JAG | Bound grants use DPoP. Mutual TLS remains available for access-token protection under `access-token-protection` |
| Rich Authorization Requests without scope | This profile requires meaningful scope alongside any authorization details; it does not define the scope-free mode permitted by `RFC9396` |

### Operational Dependencies

Provisioning, account linking, and lifecycle propagation are deployment
choices. The implementer's guide ("Provisioning and linking") lists
useful controls. SCIM `RFC7644` and Agent resources `SCIM-AGENT` provide
building blocks, not a lifecycle propagation contract.

#### Provisioning and Disablement

Consistent correlation and disablement across IdP and RAS need an agreed
provisioning and enforcement contract. `AGENT-LIFECYCLE` profiles SCIM,
optional Shared Signals, and the effects of applied changes on authorization.
It distinguishes current administrative state from revocation history and
states the limits of missed-event recovery and token enforcement. Stronger
guarantees across unobserved transitions require an additional composition.
One is deferred rather than prohibited: it would carry an authenticated
authorization generation in the grant, agreed with ID-JAG, and define the
comparison the RAS applies.
The companion is not required for conformance to this federation profile;
`agent-correlation` and `status-changes` state this document's guarantees.

### Related Work

#### Credential Broker for Agents (CB4A)

`draft-hartman-credential-broker-4-agents-00` (Informational, March 2026,
now expired) describes a credential broker that keeps long-lived
credentials away from agents. No draft in this family cites it; the
implementer's guide ("Credential brokers") maps it onto these profiles.
Points for its author, not yet raised:

* Section 4.11 describes, as future work, a native token naming the
  agent as `sub`, with `aud`, `scope`, `exp`, `jti`, and `cnf`. A
  governed WAG defines that token now, issued by the IdP the target
  already trusts, with the governed Agent Principal as `sub`.
* The SPIFFE ID of Section 4.1 combines agent, user, and session. A
  stable agent identifier, with the user and session conveyed
  separately, would let a CB4A broker federate through these profiles:
  `identity-binding` requires an exact identity and forbids an
  execution identifier from selecting the Agent Principal.
* Its approval tiers would compose with governed issuance through ARAP
  and AROP, an excluded composition (`excluded-compositions`).
* Its `envelope_hash` provenance claim has no counterpart here. Within
  one trust domain, Transaction Tokens
  (draft-ietf-oauth-transaction-tokens-11, Section 9.2.3) carry
  transaction context.

## Identity Continuation Companion

`draft-mcguinness-oauth-governed-agent-continuation.md` (`CONTINUATION`)
profiles ICA-02 for governed chains, with gateways as the primary
deployment. Its "Relationship to Other Specifications" appendix lists
the changes these notes discuss. Backquoted anchors in this section
refer to that draft.

### ICA

The companion replaces or extends these ICA-02 rules for governed chains
(`relationship-to-ica`). Each is either a candidate change to ICA or a
rule that stays local to the profile:

* **Onward actor:** Section 5.5.5 of ICA places the current actor atop
  IdP-derived lineage in the onward `act`. Governed chains keep the
  Agent Principal as the only actor (ID-JAG) or as the subject (WAG),
  and the continuing client is `client_id` (`identity-preservation`).
  The core requires one `act` with no nesting at the RAS and API, and a
  WAG carries no `act`, so the ICA form cannot reach a governed target.
  The companion now defines `continuation_via`, which discloses
  continuing clients as intermediaries rather than actors, and proposes
  it for ICA with an acting or forwarding mode per hop (ICA issue #138).
  If ICA adopts it, the companion uses ICA's claim instead. Precedents
  record forwarding services apart from the principal: in the terms of
  [WS-Trust 1.4](http://docs.oasis-open.org/ws-sx/ws-trust/v1.4/os/ws-trust-1.4-spec-os.html),
  the gateway requests access on behalf of the agent rather than acting
  as it; the Kerberos privilege attribute certificate lists the services
  that a delegated ticket passed through
  ([MS-PAC](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-pac/));
  and AWS lists the services that made a request on a principal's
  behalf ([AWS global condition context keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)).
* **Non-user anchors:** Section 6.1 of ICA puts non-user-rooted
  authority out of scope. Self-acting chains anchor to an agent
  session: IdP state refreshed only by the agent's own authentication
  through one Identity Binding, ended by an idle timeout or an
  absolute expiration (`self-acting-root`). ICA could generalize
  anchors to any principal's session, or leave non-user roots to
  profiles. A durable anchor for scheduled self-acting work, like the
  refresh-token grant for users, is open (open item 5 of the
  companion).
* **WAG chains:** ICA issues only ID-JAGs. The companion issues onward
  WAGs and registers `governed-agent-continuation`, one grant-profile
  value for handle binding of governed ID-JAGs and WAGs, because its
  access-token protection and redemption differ from what
  `id-jag-continuation` advertises.
* **Redemption grant type:** Section 5.5.5 of ICA redeems onward
  ID-JAGs with `jwt-dpop`, citing Section 9.8.1.2.1 of ID-JAG. Section
  4.4 of ID-JAG-04 requires `jwt-bearer`, and `jwt-dpop` appears only in
  the key-bound example; JWT DPoP Grant -01 expired in August 2026. The
  companion redeems with `jwt-bearer` and the core's confirmation
  checks, and drops the requirement of Section 7.2 of ICA to advertise
  `jwt-dpop`.
* **Access-token protection and bearer ingress:** Step 3 of Section 5.2
  of ICA requires a DPoP-bound access token for a continuation-capable
  grant carrying `cnf`; ICA tracks bearer ingress as issue #110. The
  companion keeps the core's protection selection (DPoP, mutual TLS, or
  configured bearer) and instead records no continuation eligibility
  for a bearer access token without explicit policy
  (`root-redemption`). Bearer-only MCP clients therefore need that
  policy to start a chain.
* **Retry fingerprint:** Section 5.5.7.1 of ICA fingerprints a retry
  without the requested token type, because ICA issues only ID-JAGs.
  With two grant types the companion adds `requested_token_type`.
* **Errors:** The companion uses the codes of Section 5.5.6 of ICA for
  both chain types, placing each governed check in one of ICA's
  validation rules (`continuation-errors`). It does not use the core's
  `actor_unauthorized` or `invalid_grant` for continuation failures.
* **Root `actor_token`:** Section 5.1.1 of ICA leaves `actor_token`
  processing on the root exchange out of scope. The governed root uses
  the core's presented-evidence mode (`delegated-root`).
* **Request narrowing:** Exactly one `resource` and a required `scope`,
  from the core. Local to the profile; no ICA change needed.
* **Continuation window:** ICA bounds no hop by how long after issuance
  a CAI can obtain continuations from it, and a compromised RAS acting
  as CAI can attest any hop it accepted (Section 9.5 of ICA). The
  companion adds a per-hop window as a SHOULD
  (`governed-chain-authorization`), which ICA could adopt for all
  chains.

### WAG

* A WAG that carries `identity_continuation_handle`, and a WAG issued by
  an IdP on a continuation exchange rather than from the Platform's own
  assertion (Section 2 of WAG).
* Advertising `governed-agent-continuation` for WAGs in ID-JAG's
  `authorization_grant_profiles_supported`, as for the core's
  self-acting profile URIs (`wag-gaps` in the core).

### Management

`AGENT-MANAGEMENT` administers Client Associations only. Continuation
Associations (`continuation-association`) need a resource or an
association dimension there before SCIM can administer them, and a
Delegation or Agent Authorization needs a way to record its permission
to continue (`chain-establishment`).

### References

The companion references the core and ICA normatively. The core
references the companion informatively, from its "Continuation with
ICA" row of Excluded Compositions, because the core does not depend on
it. No publication cluster forms.

## Family Structure

### Publication Cluster with the Input Profiles Companion

The core references the input profiles companion (`INPUTS`) normatively.
Its client-authentication rule (`algorithms`) requires an implementation
that uses JWT-SVID client authentication to claim the companion's
JWT-SVID input and follow its rules. Those rules supply validation and
algorithm requirements that the core does not contain, and Note 1 of the
IESG statement on normative and informative references classifies such
a dependency as normative even for an optional feature. The companion
references the core normatively, so the two drafts form a publication
cluster: neither can be published as an RFC without the other.

The cluster can be broken with a small behavior change:

* The core keeps only "JWT-SVID client authentication is not a
  dedicated-client method." Agent resolution from a JWT-SVID remains the
  companion's input, through the core's input-profile extension point.
* JWT-SVID client authentication at the RAS follows `SPIFFE-OAUTH`
  without this profile's narrowing: the rule that an optional `iss` does
  not select another trust domain, and `ES256` as mandatory to
  implement.
* `INPUTS` becomes an informative reference.

Breaking the cluster alone does not let the core advance ahead of early
dependencies. The core also references Client Instance Identification
(`INSTANCE`) normatively, for the client instance rule in
`identity-binding` and the instance context of `access-token-response`
and `api-validation`.

Decide this at working-group adoption, if the core should be adopted or
published separately from the SPIFFE and Client Attestation inputs.
Do not revisit the family structure before the human comprehension
check of the core's opening.
