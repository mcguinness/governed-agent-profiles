# Authority inventory exercise

This exercise finds out what independent products can already report
about the records that decide what an agent may do, before anyone
chooses a protocol for managing those records. It asks one question:

> Can two products export the same effective authorization, identify
> what created it, withdraw it, and explain what remains usable?

The drafts do not answer it. The core profile leaves assignment and
approval records, and their storage, outside the profile ("Authorization
Relationships" in the core), and the SCIM management profile
administers Identity Bindings and Client Associations for delegated
issuance, but not self-acting Client Associations or the other records
below. Only the answers products give will show what an
interoperable contract needs. This kit proposes no format, schema, or
protocol; it defines the tasks, the record to keep, and how the results
decide what comes next.

* [The deployment](#the-deployment)
* [The tasks](#the-tasks)
* [Answer key for task 4](#answer-key-for-task-4)
* [Recording the results](#recording-the-results)
* [What the results decide](#what-the-results-decide)
* [Running it](#running-it)

## The deployment

Each participating product is configured with the records that
[EXAMPLES.md](../../EXAMPLES.md)'s first delegated transaction and its
variations assume, then runs that first transaction, so
that one grant and one access token exist. The authority records for
`agent-42` are:

| Record kind | Example value |
|---|---|
| Identity Binding | (`analysis-client`, `analysis-client`) resolves to `agent-42`; as a dedicated-client binding it also permits the client's delegated use |
| Client Association | `analysis-client` may use that binding for self-acting issuance |
| Delegation Authorization | `agent-42` may act for Alice through `analysis-client` at `https://api.example/tenants/acme-data/`, with `files.read`, and with `files.write` |
| Oversight mode | `files.write` under Alice's Delegation Authorization requires her approval before a grant issues |
| Agent Authorization | `agent-42`, on its own behalf, with `files.read` at the same resource |
| Continuation Association | `tool-gateway` may continue `agent-42`'s delegated and self-acting chains to resources in `acme-data` |

The client registration association from `analysis-client` to
`analysis-api` is configuration rather than authority, and is out of the
exercise.

### Settings to record

What remains usable after a withdrawal depends on settings the drafts
leave to each deployment. Record them for each product, and for the RAS
and API it is tested with, before task 3:

| Setting | Written as | Drafts' text |
|---|---|---|
| The IdP's freshness limit: the longest it may go on issuing under a withdrawn relationship before it applies the change | F | Core: Issuance Authorization |
| Whether the IdP keeps the identifiers of the grants it issued under each relationship, and signals their revocation to the RAS | | Core: Authorization Changes and Revocation; lifecycle: Grant-Derived Session Revocation |
| When the RAS applies a revocation it receives, if one reaches it | R | Core: Applied Disablement and Revocation |
| How the API validates access tokens: offline, introspection on each request, or cached introspection with its cache limit | C | Core: Token Validation (Introspection caching) |

The withdrawal is made at 12:02:00 on September 17. The IdP applies it at
some time A, no later than 12:02:00 plus F; record A.

## The tasks

Each task is run against each product, and each answer is recorded
whether or not the product can give it.

1. **Export.** Export every authority record for `agent-42`, in the
   product's own form: an API response, a report, or a screen.
2. **Provenance.** For each record, say what created it and when: an
   administrator's assignment, a user's consent, a policy, or an import
   from a platform. Name the person or system that approved it, if the
   product knows.
3. **Withdraw.**
   * At 12:02:00, withdraw Alice's Delegation Authorization for
     `agent-42`, record when the IdP applied it, and export again. Task
     4 checks this withdrawal.
   * On a copy of the deployment, try to withdraw each other record kind
     through the product's administrative interface, and record how: an
     API, the administrative console only, or not supported. Mark any
     kind not tried as untested.
4. **Explain.** State what remains usable after Alice's delegation is
   withdrawn, and until when.
5. **Administration.** For each record kind, say who other than the
   product's administrators needs to create or withdraw it: a platform's
   connector, an identity-governance tool, a resource owner, or the user.

Each answer to tasks 1 and 2 has four parts, which products tend to hold
to very different degrees:

| Part | What it covers | Example value |
|---|---|---|
| Desired state | The record as configured: who, what, where, and whether it is active | Alice's delegation, `files.read` and `files.write`, active |
| Approval provenance | What created the record, who approved it, and when | Assigned by an administrator, or consented to by Alice, on September 16 |
| Expiration policy | When the record ends without anyone acting | No expiry, or an end date set at assignment |
| Observed usage | When the record was last relied on, and what was issued under it | `grant-1` issued at 12:01:03 under Alice's delegation |

Most products are likely to hold desired state, and few to hold observed
usage. Finding out which is the point of the exercise.

## Answer key for task 4

Task 4's answer depends on the recorded settings. The first transaction's clock
fixes the rest: `grant-1` was issued at 12:01:03 with a 300 s lifetime,
and was redeemed at 12:01:04 for `access-1`, a JWT access token valid
until 12:11:04, with no refresh token.

| After the 12:02:00 withdrawal | Usable? | Until | Source |
|---|---|---|---|
| A new delegated grant for Alice and `agent-42` | Yes until the IdP applies the withdrawal; then no, with `actor_unauthorized` | A, no later than 12:02:00 plus F | Core: Issuance Authorization; Effects of administrative changes. PLAYBOOK: delegated recipe, rejection tests |
| A new continuation in a chain rooted under Alice's delegation | Yes until the IdP applies the withdrawal; then no, with `invalid_continuation`, and the chain stays ended | A | Continuation profile: Chain Ending and Governance Events |
| `grant-1` | Already redeemed. A RAS that accepts a bound grant only once rejects it; one that accepts it again under explicit policy can redeem it until it expires | 12:06:03, at most | Core: Common Grant Validation (Grant replay) |
| `access-1`, validated offline at the API | Yes, unless a revocation reaches the API by another route it checks | 12:11:04 | Core: Effects of administrative changes; Authorization Changes and Revocation |
| `access-1`, introspected on each request | Yes until the RAS applies a revocation, if one reaches it | R, or 12:11:04 if no revocation reaches the RAS | Core: Authorization Changes and Revocation |
| `access-1`, with cached introspection | An active response cached before R stays usable until its cache limit | The later of R and the last cached response's limit, never after 12:11:04 | Core: Token Validation (Introspection caching) |
| Tokens already issued downstream through continuation | Yes until they expire or their revocation is applied | Their expiry, or when revocation is applied | Continuation profile: Disablement Windows |
| `agent-42`'s delegations for other users, and its Agent Authorization | Unaffected | — | PLAYBOOK: delegated recipe, rejection tests; The decisions an identity team owns ("None of these implies another") |

For example, with cached introspection and a 60 s cache limit, an active
response cached at 12:01:59 lets `access-1` through until 12:02:59, even
if the RAS applies a revocation at 12:02:05.

A revocation reaches the RAS only if the IdP kept `grant-1`'s identifier
under Alice's delegation and a signal carries it there ("Authorization
Changes and Revocation" in the core). Whether a product can name
`grant-1` in its task 4 answer is part of what the exercise records.

## Recording the results

Fill in two tables per product. In the first, each cell is **exported**
(the product gives it directly), **derivable** (it can be reconstructed
from logs or another system), or **not held**, followed by the
product's own name for the field:

| Record kind | Desired state | Approval provenance | Expiration policy | Observed usage |
|---|---|---|---|---|
| Identity Binding | | | | |
| Client Association | | | | |
| Delegation Authorization | | | | |
| Oversight mode | | | | |
| Agent Authorization | | | | |
| Continuation Association | | | | |

The second records how each kind is held and administered:

| Record kind | Stored, or derived from policy or consent at issuance | Create and withdraw: API (named), console only, not supported, or untested | Others who need to create or withdraw it (task 5) |
|---|---|---|---|
| Identity Binding | | | |
| Client Association | | | |
| Delegation Authorization | | | |
| Oversight mode | | | |
| Agent Authorization | | | |
| Continuation Association | | | |

Then record, for the pair of products:

* whether their task 1 exports describe the same effective
  authorization, and where they differ; and
* whether each product's task 4 answer matches the answer key for its
  recorded settings, and which rows it could not answer.

## What the results decide

Decide for each record kind separately; different kinds can reach
different outcomes. Answer these questions in order, using both
products' results:

1. **Is the record stored?** If both products derive it from policy or
   consent when they issue a grant, there is no record to manage: the
   outcome is **keep the existing SCIM resources and lifecycle
   signals**, and withdrawal works through the policy.
2. **Do others need to create or withdraw it?** If task 5 names parties
   other than the product's administrators, and both products create and
   withdraw the record through an API, the outcome is **extend the SCIM
   management profile** with a resource for it. For Identity Bindings and
   Client Associations, the question is instead whether the resources
   the profile already defines suffice.
3. **Do others only need to read it?** If no one else needs to create or
   withdraw it, and both products export its desired state, provenance,
   and expiry, the outcome is **define a read-only export** of effective
   authorization for it.

Anything else is **inconclusive** for that kind: fewer than two products
answered, a deciding cell is not held or untested, or the products
disagree at a step. Mixed and inconclusive results are expected. Each
one leaves a follow-up question for the products concerned:

* Does the product store this record, or derive it at issuance?
* Who other than its administrators needs to create or withdraw it, and
  why?
* Would the product expose creating and withdrawing it through an API?
* Can the product name the grants issued under it?

Observed usage that no product holds points to events or logs, not to
records, whatever the outcome for the kind.

## Running it

The exercise needs at least two independent products: two IdPs, or an
IdP and an identity-governance tool that reads it. It also needs people
who can configure the examples' records on each. This repository has neither.

Until then, the table can be tried against the
[reference implementation](../../conformance/README.md) as a dry run.
The reference holds desired state only, in memory, with no provenance,
expiry, or usage, so the dry run exercises the table, not the question.
Its test control can withdraw the delegation, and conformance case N09
shows that the next exchange fails with `actor_unauthorized`.
