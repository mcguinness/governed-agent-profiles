# Plan: make the federation core approachable, then split specialized inputs and guidance

Status: revised plan, October 9, 2026. The measurements below describe
scratch builds against `main` at `6a318b2`; they have not been repeated
for this revised structure. This update changes the plan only.

## Goal

Readers should understand the core contract in the first few pages and
find their role's processing rules without reading every capability.
Preserve every requirement, definition, exception, and security boundary
needed for independent implementations to interoperate.

The current federation draft is 97 pages. Its size and the amount of
material before issuance can obscure a straightforward transaction:
the IdP resolves and authorizes a governed agent, a grant carries its
identity, and the resource domain correlates and authorizes that agent.
Delegated access also carries and checks a user's identity and authority.
The complete specification must cover more cases than this explanation.
Its structure should make that distinction apparent.

The work has three parts, in this order:

1. Explain the contract early.
2. Move specialized credential inputs and deployment guidance into
   separate documents while preserving complete core transactions.
3. Organize the remaining core's processing predictably.

Retain the earlier 20–30% reduction objective as a secondary target.
Comprehension and interoperability determine acceptance. A repository
primer supplements the explanation inside the specification.

## Opening and reader experience

### Explain the transaction before the detailed vocabulary

Aim for a complete conceptual explanation within the first three to
five pages of body text, excluding front matter and the contents list.
Use the shared-client problem to explain why the profile exists:

> A platform runs several agents behind one OAuth client. Client
> authentication identifies the platform, but the resource needs to know
> which agent is acting. The IdP maps an authenticated client or workload
> identity to a stable Agent Principal and checks whether the client may
> use that identity. It issues a grant identifying the agent. The resource
> domain correlates that identity with its local principal and applies
> its authorization policy. Delegated access identifies both the user and
> the agent; self-acting access identifies the agent as the subject.

Add one compact flow diagram:

Client → IdP resolves and authorizes → grant → RAS validates and
correlates → access token → API enforces.

Explain each relationship through the question it answers:

* **Identity Binding:** Which governed agent does this credential identify?
* **Client Association:** May this OAuth client use that agent identity?
* **Agent or Delegation Authorization:** What authority may the agent
  request, on its own or for a user?
* **Local correlation and resource policy:** What access will the
  resource domain permit?

Show one identity transformation: a qualified platform identity for
`workload-7` maps to (`https://idp.example/`, `agent-42`). A delegated
grant carries a user in `sub` and the agent in `act`; a self-acting
grant carries the agent in `sub`. Show the issuer qualification and
label abbreviated claims as excerpts. The resource domain applies its
own authorization to the correlated agent.

State the limits briefly: identity mapping does not grant permission,
agent ownership does not establish user delegation, and disablement
propagation depends on the lifecycle mechanism. Link to the authoritative
rules. Keep the overview informative and check it against those rules.

### Make the structure carry the explanation

* Introduce terms as the model uses them; defer specialized credential
  vocabulary to the applicable input profile.
* Use the same order within each processing chapter: inputs, common
  checks, delegated/self-acting differences, and output. Keep client
  requirements beside the corresponding requests and responses.
* Give optional capabilities explicit headings and opening applicability
  conditions, such as "Optional: RAS refresh tokens" or "When using
  instance context". Put grant-protection conditions beside their rules.
* Use the shared-client case for motivation and the dedicated-client
  exchange for the mandatory interoperability baseline. Show platform
  JWT as a compact shared-client variation.
* Preserve the stage structure and both peer grant realizations. No
  reading-guide table is needed; headings should reveal the organization.

## Target core structure

1. **Introduction and protocol overview:** the problem, transaction,
   identity transformation, and a short statement of the baseline.
2. **Identity and authorization model:** essential terminology,
   relationships, tenant boundaries, and the two grant realizations. The
   relationships include Agent and Delegation Authorization and the
   definition of the actor gate, which both the RAS (at redemption) and
   the API (for each operation) enforce. Keep the "Delegated and
   self-acting access compared" table here.
3. **Profiles and common rules:** everything the processing chapters rely
   on:
   * adoption profiles and grant protection;
   * client authentication and algorithms;
   * time, replay, and key validation;
   * token-endpoint error conventions;
   * profile applicability and downgrade prevention.

   Keep the "Additions and narrowings" table here.
4. **Grant issuance at the IdP:** common input interface, dedicated-client
   and platform JWT profiles, common validation and authorization, then
   ID-JAG and WAG issuance and errors.
5. **Grant redemption at the RAS:** common checks and correlation,
   grant-specific checks (applying the actor gate defined in chapter 2 for
   delegated grants), access-token issuance and protection, and errors.
6. **Access at the resource server:** applicability, common validation,
   delegated enforcement applying the chapter 2 actor gate, and
   self-acting authorization.
7. **Continuing access and authorization changes:** reuse, optional
   refresh, applied disablement, and revocation.
8. **Conformance and capability advertisement:** detailed conformance
   claims, metadata, and discovery.
9. **Security and privacy considerations.**
10. **IANA considerations.**

Appendices: A. worked exchanges and acceptance cases; B. compact
dependencies and excluded compositions.

Chapter 3 keeps the placement that #10 chose for these prerequisites,
which answered the review that conformance came after the flows. Only
the detailed conformance claims and capability advertisement move after
processing. This changes a structure the author recorded after #10, so it
is an author decision. Keep precise errors near their processing stage,
with one authoritative home for shared rules.

## Measurements and their limits

These existing scratch builds removed the listed material. Page counts
come from rendered text; they do not establish a minimum possible length.

| Version | Pages |
|---|---:|
| Baseline at `6a318b2` | 97 |
| Optional inputs, guidance, coordination notes, and all examples moved out | 71 |
| As above, keeping the core walkthrough and negative tests | 78 |
| As above, also keeping a compact dependencies appendix | 81 |
| Core with a compact dependencies appendix and no examples | 73 |
| As in the 71-page build, also moving the platform JWT input | 68 |
| As in the 71-page build, also moving optional features inside stage chapters | 66 |
| Dedicated client, ID Token subject, both grants, no examples | 64 |

The stage features in that experiment were RAS refresh, SAML and IdP
refresh-token subjects, mutual TLS access tokens, instance context, and
WISE. The proposed split keeps them in the core.

The 81-page result reduces length by 16.5%; the 73-page result by 24.7%.
Keep useful examples provisionally and remeasure after restructuring.
With these boundaries, the 20% target (77 pages or fewer) needs about 4
pages beyond extraction, while the new overview adds text. The overview
therefore has a word budget: it replaces at least its own length from the
overlapping Introduction, Terms, and Federation Model text, and step 1
records the words before and after. Compression in step 5 supplies the
rest, or the target is reported as missed.
The 64-page experiment is an extraction result, not a lower bound.
Definitions and prose without BCP 14 keywords can be essential while
still allowing clearer wording, placement, or consolidation.

Earlier body-word comparisons, excluding front matter and references:

| Specification | Body words |
|---|---:|
| This draft, sections 1–11 | 15,217 |
| This draft, appendices | 5,431 |
| ID-JAG-04 | 11,237 |
| ATTEST-11 | 10,842 |
| RFC 9449 | 10,523 |
| RFC 9700 | 14,624 |

These comparisons provide context, not an acceptance threshold. Record
core and whole-family word/page counts separately so extraction is not
reported as an equivalent reduction in total material. Preserve the
commands and source revision used for the next measurements.

## Document boundaries

| Document | Status | Responsibility |
|---|---|---|
| Core profile | Standards Track | Complete dedicated-client and platform JWT transactions; both grants; IdP, RAS, client, and API rules; continuing access; conformance; security; core examples and acceptance cases |
| Agent Resolution Input Profiles | Standards Track; applies to implementations claiming its inputs | SPIFFE JWT-SVID, WIT-SVID, and X.509-SVID; Client Attestation, endorsement, and managed-installation resolution; input-specific proof and lifetime rules; examples and acceptance cases |
| Implementer's guide | Repository Markdown initially | Supplemental primer, Federation Configuration, distributed deployment guidance, adoption tradeoffs, and deployment examples |
| `COORDINATION.md` | Repository notes | Detailed upstream discussions and deferred work |

Working companion name:
`draft-mcguinness-oauth-governed-agent-inputs`.

Keep managed-installation resolution with Client Attestation: its
attester, matching, continuity, receiver-scope, and proof rules form one
composition. Keep downstream RAS/API instance-context processing in the
core. A client using attestation at the RAS need not have used it to
resolve the agent at the IdP.

The guide has no unique implementation prerequisite. Federation
Configuration remains together there; its underlying protocol
requirements retain authoritative homes in the core or companion.

## Move map

### Specialized input material

| Existing unit or anchor | Destination and treatment |
|---|---|
| `optional-input-profiles`, `jwt-svid-input`, `agent-evidence`, `spiffe-input` | Companion, including managed-installation resolution and attester endorsement |
| `resolution-key-lifecycle` | Companion; retain the core's general proof-key and no-rebinding rules |
| JWT-SVID row in `algorithms` | Companion, preserving its conditional algorithm requirements |
| Optional-input rows in `grant-common` lifetime table | Companion; core retains the generic lifetime rule and dedicated-client exception; each moved input states its exact bound |
| `optional-inputs` and conditional conformance requirements | Core identifies the extension and where its conformance requirements live; companion defines claims for its inputs |
| Input-specific security and privacy material | Inventory individually; specialized rules move with their inputs, while general security boundaries stay in core |
| `shared-client-example`, `svid-context-example` | Companion |
| `input-variants` table and shared explanatory text | Partition by input: platform JWT stays in core; native-input details accompany their companion examples |
| Negative tests referencing optional native inputs | Move input-specific cases to companion; retain generic shared-client token-reuse coverage in core using the platform JWT case. The token-reuse case now cites `shared-client-example` (SPIFFE); rewrite it against the platform JWT variant, which uses the same shared `platform-sso` client |

### Core material and examples

| Existing unit or anchor | Treatment |
|---|---|
| `evidence`, `actor-inputs`, `credential-requirements` | Keep input interface, mode selection, credential-class exclusion, no-fallback rules, and bearer-evidence limits in core |
| `client-assertion-input`, `imported-jwt-input` | Keep in core near issuance; platform JWT supports the generic shared-client claim |
| `identity-binding` | Keep generic matching and authorization boundaries; audit the managed-installation exception's reference and applicability |
| `wag-request` | Keep byte-identical subject-token rule and the explicit lack of an X.509-SVID self-acting path; companion states supported realizations consistently |
| `access-token-response`, `api-validation` instance-context paragraphs | Keep in core, including the prohibition on copying grant-carried context and on substituting instance context for authorization |
| `ras-refresh`, subject-token variants, access-token protection, WISE processing | Keep in core with explicit applicability; governed agent access and bound governed agent access both remain |
| `walkthrough`, `wag-example`, core negative tests | Keep in core; retain issuer/tenant, user-delegation, proof, replay, and failure checks |
| `aws-example` | Keep with platform JWT as a compact input variation; retain its evidence and conformance limits |

### Guidance and coordination

| Existing unit or anchor | Destination and treatment |
|---|---|
| `implementation`, `configuration`, `distributed-key-use` | Guide; audit every incoming citation for a protocol dependency |
| `baseline-costs` | Deployment tradeoffs move to guide; preserve essential threat explanations in core Security Considerations |
| `identity-example`, Intermediate Adoption Variant | Guide; the core's new conceptual example remains independent of specialized inputs |
| Appendix C Upstream Dependencies table, WAG open items, Excluded Compositions table | Compact core appendix; update internal references |
| `bound-grant-coordination`, `dedicated-client-coordination`, remaining Deferred Compositions and Operational Dependencies notes | Reconcile into existing `COORDINATION.md`; retain operative restrictions in core and avoid duplicating existing notes |

Before extraction, expand this map into a complete requirements and
reference inventory. Every affected paragraph, table row, exception,
and example receives a destination. Do not treat absence of BCP 14
keywords as evidence that material is disposable.

## References and conformance

The companion normatively references the core. Classify each reference
from the core by its actual dependency. Optional support alone does not
make a reference informative. Note 1 of the
[IESG Statement on Normative and Informative References](https://www.ietf.org/about/groups/iesg/statements/normative-informative-references/)
says: "Even references that are relevant only for optional features must
be classified as normative if they meet the above conditions for
normative references." For the general definition, see
[RFC 3967, Section 1.1](https://www.rfc-editor.org/rfc/rfc3967.html#section-1.1).
An informative pointer is appropriate when the core remains complete
without the target; a rule importing required behavior or an exception
needs a normative dependency or an explicitly defined extension boundary.

Design the boundary so the core does not depend on the companion. At
`6a318b2`, 23 body paragraphs or table rows in the core name
companion-bound inputs; 10 carry BCP 14 keywords. They are spread across
17 sections, including `actor-inputs`, `identity-binding`,
`credential-requirements`, `algorithms`, `grant-common`, `wag-request`,
and `access-token-response`. Each one either moves to the companion or
is restated against the input contract, naming a property rather than an
input. For example:

* "Native SPIFFE and Client Attestation inputs use authentication context
  and MUST NOT be accepted through presented-evidence mode" becomes a
  rule about inputs that resolve from authentication context.
* The managed-installation exception in `identity-binding` becomes a
  generic condition: an input profile MAY define installation-level
  resolution only with an exact binding, a configured resolution level,
  no fallback between levels, and no inferred continuity. The
  companion's Client Attestation profile then defines it.

Each companion input states which contract properties it has. The core's
reference to the companion can then be informative, and the core can
advance without it. If a rule cannot be restated this way, the two
drafts become a publication cluster; record that outcome explicitly.

* Audit the managed-installation exception in `identity-binding`,
  conditional conformance, lifetime rules, and all guide citations.
* Preserve conformance meaning: profile URI, realization, role,
  supported inputs, and the generic shared-client claim. Optional-input
  claims identify the applicable companion requirements.
* Repoint SCIM agent management's native credential validation references
  to the companion. Check its selectors and key semantics against the
  moved rules.
* Review lifecycle references and examples for meaning even where no
  section number or anchor changes.
* Keep the four profile URIs in the core. No new registration is planned.
* Add the companion to the build and README, with direct links to the
  overview, examples, and guide. Check rendered links across all drafts.

## Preservation and acceptance criteria

Protocol behavior remains unchanged. WAG stays a peer realization,
just-in-time correlation stays in the core, and Federation Configuration
stays together in the guide. Editorial changes to requirements must
preserve their role, conditions, exceptions, and force. Any proposed
behavior change is separate work.

### Semantic preservation

For each affected rule record:

Existing location → destination → implementing role → applicability →
exceptions → expected acceptance or rejection behavior.

Include definitions, tables, security limits, and exclusions. Specifically
track grant lifetime bounds, credential-class isolation, installation
continuity, proof-key relationships across receiver scopes, replay, WAG
subject presentation, and unsupported input/grant combinations.

Paragraph comparisons and BCP 14 counts are supporting checks. Account
for every difference, including reference rewrites and new framing. The
same words or keyword count do not prove the same meaning.

### Comprehension

Give the revised opening to at least one person unfamiliar with the
draft, who is neither an author nor a previous reviewer. A cold-reader
agent can supplement that reader but not replace them. After five
minutes, ask them to explain:

* the problem the profile solves;
* the differences among client, workload identity, and Agent Principal;
* the IdP's decisions and the resource domain's decisions;
* delegated versus self-acting access; and
* where they would begin implementing their role.

The opening passes when the reader answers all five correctly from the
draft alone, without the guide. Record where they hesitate or follow the
wrong section, revise those areas, and record the result in the PR.
This reader exercise is a validation step, not a new table in the draft.

### Implementation and build checks

* Trace dedicated-client and platform JWT shared-client transactions for
  both grants and both protection profiles using the core and its base
  specifications, without unique requirements from the guide or input
  companion. Include client, IdP, RAS, and API behavior and failure cases.
* Trace each companion input through its supported realizations using
  core plus companion. Check key mismatches, expired credentials,
  forbidden fallback, and unsupported X.509-SVID self-acting issuance.
* Build all affected drafts, parse changed JSON examples, resolve local
  and cross-document links, and inspect rendered tables and headings.
* Repeat the size measurements and report comprehension findings beside
  them. An 81-page result can be an intermediate outcome; further editing
  must preserve the contract.

## Execution

Use separate PRs so explanatory changes, relocation, and compression
can each be reviewed against the preceding version. Extraction comes
before reorganization, so the reorganization works on the smaller core
and reconciles fewer anchors.

1. **Opening and protocol overview.** Write the conceptual transaction,
   identity example, and short baseline statement inside the core. Its
   net word change against the current Introduction, Terms, and
   Federation Model is zero or negative; record it in the PR. Run the
   comprehension exercise before extracting material.
2. **Specialized inputs.** Build the requirements and reference inventory
   for the affected material, including the 23 core paragraphs that name
   companion-bound inputs. Restate core rules against the input contract
   where they stay, create the companion, move the assigned material, and
   update the core, SCIM management, build, and README references.
   Preserve input-specific security and privacy considerations and run
   the semantic checks.
3. **Core organization.** Apply the target contents, the predictable
   stage structure, and the optional-feature headings to the remaining
   core. Keep chapter 3's common rules before processing and the actor-gate
   definition in the model. Check semantic preservation before merging.
4. **Guide and coordination.** Create `docs/implementers-guide.md`, move
   the assigned guidance, and reconcile Appendix C with `COORDINATION.md`.
   Add a supplemental primer explaining both flows and role
   responsibilities.
5. **Compression and final review.** Consolidate repetition and simplify
   wording where the requirements map demonstrates equivalence. Run the
   implementation traces, comprehension exercise, builds, and
   measurements.

## Risks and remaining review points

* **A clear overview can omit a decisive condition.** Check examples
  against the full rules, particularly delegation, tenant qualification,
  correlation, and proof. Label excerpts and informative explanations.
* **Moving text can change applicability.** Review requirement scope and
  references, including conditional rules that remain in the core.
* **The family grows from four drafts to five plus a guide.** Assign one
  authoritative home to each rule and report total material separately
  from core length.
* **Specialized inputs require two documents.** Keep all rules specific
  to an input together and verify a complete transaction across that
  boundary.
* **The core may remain long.** Judge whether readers understand the
  contract early and can locate their processing rules. Continue measured
  editing without assuming that every remaining paragraph is irreducible.

The recommended boundaries are platform JWT and downstream instance
context in core, managed-installation resolution with Client Attestation,
and an initially Markdown guide. Review the resulting contents and
reader evidence before treating the extraction size as final. Completing
the split before the first submission may reduce early reference churn;
the approachability and dependency benefits are the primary rationale.
