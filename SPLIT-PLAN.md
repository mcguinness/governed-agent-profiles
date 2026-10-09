# Plan: split the federation draft into a core profile, an input-profiles companion, and an implementer's guide

Status: proposal for review. Measured against `main` at `6a318b2`
(October 9, 2026). Nothing in the drafts changes until the decisions in
[Decisions requested](#decisions-requested) are made.

## Problem

The core draft, *OAuth 2.0 Profile for Governed Agent Federation*, is 97
pages. Its mandatory path is not complex: a dedicated client
authenticates with `private_key_jwt`, the IdP resolves one Agent
Principal, and the IdP issues an ID-JAG (with the user as `sub` and the
agent as `act`) or a WAG (with the agent as `sub`). The RAS validates and
correlates the agent, and the API enforces the actor gate. The concern
is that readers stop before they reach that path, and that the document
does not make clear which parts are core, which are optional, which are
examples, and which are guidance.

## Measurements

Each row is a scratch build with the listed material removed. Page
counts come from the rendered text.

| Version | Pages |
|---|---:|
| Today | 97 |
| Optional inputs, guidance, coordination notes, and all examples moved out | 71 |
| As above, keeping the core walkthrough and negative tests | 78 |
| As above, also keeping a compact dependencies appendix (two tables) | **81** |
| Core with a compact dependencies appendix and no examples | 73 |
| As in row 2, also moving the platform JWT input | 68 |
| As in row 2, also moving the optional features inside the stage chapters | 66 |
| Mandatory path only: dedicated client, ID Token subject, both grants, no examples | 64 |

The optional features inside the stage chapters are RAS refresh, SAML and
IdP refresh-token subjects, mutual TLS access tokens, instance context,
and WISE.

For comparison, measured as body word counts excluding front matter and
references:

| Specification | Body words |
|---|---:|
| This draft, sections 1–11 | 15,217 |
| This draft, appendices | 5,431 |
| ID-JAG-04 (65 pages) | 11,237 |
| ATTEST-11 | 10,842 |
| RFC 9449 (DPoP) | 10,523 |
| RFC 9700 (OAuth Security BCP) | 14,624 |

Three conclusions:

1. Moving optional inputs, guidance, coordination notes, and peripheral
   examples out of the core takes it from 97 to about 81 pages, or 73
   without examples.
2. The mandatory contract itself is about 64 pages, about the size of
   ID-JAG. That covers two grants, three processing roles, conformance,
   metadata, and security. A split cannot make the core short.
3. Of the main body, 41% is prose without BCP 14 keywords. That is not a
   free cut: the September trim pass removed the restatements, and
   reviewers confirmed that the rest is definitional. This plan does not
   count on cutting it.

So the split fixes classification, and the length perception needs an
on-ramp outside the spec: a short primer.

## Proposal

| Document | Status | Contents | Size |
|---|---|---|---|
| Core profile (this draft) | Standards Track | Model; both grants; dedicated-client and platform JWT inputs; grant protection; IdP, RAS, and API processing; continuing access; errors; metadata; security; IANA; dedicated-client walkthrough, self-acting variant, and negative tests; a compact dependencies appendix | ~81 pp (73 without examples) |
| Agent Resolution Input Profiles (new) | Standards Track, optional | SPIFFE JWT-SVID, WIT-SVID, and X.509-SVID; Client Attestation with the managed-installation binding; endorsement and instance-context composition; resolution-key lifecycle; input-variant examples | ~8–12 pp (rough build: 7) |
| Implementer's guide (new) | Repository Markdown now; an Informational draft later if the working group wants one | Primer (the model, one flow, what each role builds); Federation Configuration (kept whole); distributed platforms; adoption tradeoffs; identity-mapping and intermediate-adoption examples | Not paginated |
| Coordination notes | `COORDINATION.md` (exists) | Appendix C prose notes not kept in the compact appendix | — |

Working file name for the companion:
`draft-mcguinness-oauth-governed-agent-inputs`.

This follows the order a reviewer gave on September 28: "split
peripheral input machinery before splitting the central contract." One
transaction still reads in one document.

## Move map

### To the Input Profiles companion

| Unit today | Anchor | Notes |
|---|---|---|
| Optional Input Profiles (A.2) | `optional-input-profiles` | Section moves whole |
| SPIFFE JWT-SVID | `jwt-svid-input` | |
| Client Attestation, including the managed-installation binding and endorsement | `agent-evidence` | |
| SPIFFE WIT-SVID and X.509-SVID | `spiffe-input` | |
| Resolution-Key Lifecycle | `resolution-key-lifecycle` | |
| Input variants: Shared Platform Client with SPIFFE; WIT-SVID and X.509-SVID | `shared-client-example`, `svid-context-example` | |
| The optional-inputs list in Conformance | `optional-inputs` | Replaced by a pointer to the companion |
| Body sentences specific to these inputs | various | For example, the JWT-SVID row of the mandatory-to-implement table, and the instance-context paragraphs in Access Token Issuance and Token Validation |

### To the implementer's guide

| Unit today | Anchor |
|---|---|
| Implementation Considerations (Federation Configuration, Distributed Platforms and Key Use) | `implementation`, `configuration`, `distributed-key-use` |
| Adoption Tradeoffs | `baseline-costs` |
| Identity Mapping Example | `identity-example` |
| Intermediate Adoption Variant | — |

### Appendix C

The compact appendix keeps the Upstream Dependencies table, the WAG open
items, and the Excluded Compositions table, which the body cites 8
times. These move to `COORDINATION.md`, and the body's 7 citations of
them are reworded or pointed at the kept tables:

* ID-JAG Bound Grants;
* Resolution from Authentication Context;
* the remaining Deferred Compositions notes;
* Operational Dependencies.

### Stays in the core

These hooks stay in the core, so the companion fills an extension point
rather than redefining processing. The list follows the September trim
analysis.

* The input interface contract.
* The authentication-context and presented-evidence modes.
* The credential-class exclusion rules.
* Bearer Evidence Limits.
* The WAG byte-identical subject-token rule.
* The generic grant-lifetime rule.
* The dedicated-client input, which is mandatory to implement.
* The platform JWT input, which carries the generic shared-client claim; see decision 2.

## Cross-references and companion-draft impact

| Item | Change |
|---|---|
| Citations to moved anchors | 37 citations in the body: <br>• 13 to companion sections, which become citations of the companion; <br>• 9 to guide sections, which become informative references to the guide; <br>• 15 to Appendix C notes, of which 8 survive in the compact appendix and 7 are reworded. <br>Citations inside moved sections move with them. |
| SCIM agent management | Its `spiffe-jwt`, `spiffe-wit`, `spiffe-x509`, and `client-attestation` credential classes cite the core for validation; they cite the companion instead. This is about 14 mentions. |
| Lifecycle | No change. It cites `{{FEDERATION}}` without section numbers. |
| Conformance | Core claims stay as they are. A claim of an optional input names the companion. The generic shared-client claim stays in the core with the platform JWT. |
| References | The companion normatively references the core. The core informatively references the companion, which is optional. |
| IANA | No change. The four profile URIs stay in the core, and the companion registers nothing. |
| Repository | Add the companion draft to the i-d-template build and to the README's drafts table. |

## What does not change

* No requirement changes: every BCP 14 sentence lands, unchanged, in
  the core or the companion.
* Author rulings hold:
  * WAG stays a peer realization in the core.
  * The stage structure stays.
  * Just-in-time correlation stays in the core.
  * Federation Configuration stays in one place (the guide).
  * The "Additions and narrowings" and "Delegated and self-acting access
    compared" tables stay.
* No reading-guide table returns to the draft. The primer lives in the
  repository, outside the spec; see decision 4.
* No section numbers are cited across drafts today, so renumbering is
  free.

## Decisions requested

1. **Adopt the three-document split, and do it before -00 is
   submitted.** Recommended. Before submission, splitting is a repository
   change. After submission, it means renamed or replacement drafts and
   reference churn.
2. **Keep the platform JWT input in the core.** Recommended, at about
   +3 pp. The core's motivating case is a shared platform client, so
   the core should be implementable for that case on its own. If the
   input moves instead, the generic shared-client conformance claim moves
   with it, and the core's shared-client story depends on the companion.
3. **Keep the dedicated-client walkthrough, self-acting variant, and
   negative tests in the core**, at about 81 pp. Recommended. They show
   exactly the mandatory path, and a reviewer asked for the negative
   tests so the contract is checkable. The alternative moves all examples
   to the guide, at about 73 pp.
4. **Write the primer.** Recommended. It is the change that addresses
   the length perception. It is close to the earlier ruling against a
   reading-guide table, so it needs explicit confirmation: it lives
   outside the draft and is not navigation inside it.
5. **Leave the optional features inside the stage chapters in the core.**
   Recommended. These are RAS refresh, SAML and refresh-token subjects,
   mutual TLS, instance context, WISE, and the unbound "governed agent
   access" profile. Moving them saves about 5 pp. But their hooks sit
   inside baseline rules, and a reader would cross documents
   mid-transaction. Revisit after the split.

## Execution

Each step is its own PR with the same discipline as the stage
restructure (#10).

1. **Companion, move only.**
   * Create the companion with its front matter, a short introduction,
     terminology, security and privacy considerations for the moved
     inputs, and references.
   * Move the units in the move map.
   * Repoint citations in the core and in SCIM agent management.
   * Verification:
     * the paragraph multiset of core plus companion equals today's
       draft, minus what moves to the guide, plus new framing text that
       is listed;
     * the BCP 14 keyword census across the two drafts is unchanged;
     * every anchor resolves;
     * both drafts build.
2. **Guide and Appendix C.**
   * Create `docs/implementers-guide.md` with the guidance units.
   * Trim Appendix C to the compact form.
   * Move its prose notes to `COORDINATION.md`.
   * Repoint the guide citations as informative references.
3. **Primer**, if decision 4 is yes: a short, non-normative walk through
   the model, one delegated and one self-acting flow, and what each
   role builds, linking into the core.
4. **Independent checks.**
   * A requirements verifier across both drafts.
   * A cold implementer trace that answers: can an IdP, RAS, and API
     interoperate on the mandatory path using only the core?

## Risks

* **The core is still long.** At about 81 pages, it stays ID-JAG-sized.
  The primer is the mitigation; further cuts to the core would change
  what it requires.
* **More documents to maintain.** The family grows from four drafts to
  five, plus the guide.
* **Optional inputs span two documents.** An implementer of an optional
  input reads the core and the companion. That is the usual pattern for
  OAuth extensions, but it adds one hop.
* **Timing.** The case for splitting now rests on the draft not yet
  being submitted.

## Review questions

1. Is the core/companion boundary right? In particular, should the
   managed-installation binding stay with Client Attestation in the
   companion?
2. Should the guide start as repository Markdown, or as an Informational
   draft from the outset?
3. Is about 81 pages acceptable for the core, given that the mandatory
   contract alone is about 64?
