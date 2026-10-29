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

Each participating product is configured with scene 1 of
[EXAMPLES.md](../../EXAMPLES.md), then runs scene 2's first access, so
that one grant and one access token exist. The authority records for
`agent-42` are:

| Record kind | Scene 1 value |
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

## The tasks

Each task is run against each product, and each answer is recorded
whether or not the product can give it.

1. **Export.** Export every authority record for `agent-42`, in the
   product's own form: an API response, a report, or a screen.
2. **Provenance.** For each record, say what created it and when: an
   administrator's assignment, a user's consent, a policy, or an import
   from a platform. Name the person or system that approved it, if the
   product knows.
3. **Withdraw.** At 12:02 on September 17, withdraw Alice's Delegation
   Authorization for `agent-42`, then export again.
4. **Explain.** State what remains usable after the withdrawal, and until
   when.

Each answer has four parts, which products tend to hold to very
different degrees:

| Part | What it covers | Example in scene 1 |
|---|---|---|
| Desired state | The record as configured: who, what, where, and whether it is active | Alice's delegation, `files.read` and `files.write`, active |
| Approval provenance | What created the record, who approved it, and when | Assigned by an administrator, or consented to by Alice, on September 16 |
| Expiration policy | When the record ends without anyone acting | No expiry, or an end date set at assignment |
| Observed usage | When the record was last relied on, and what was issued under it | `grant-1` issued at 12:01:03 under Alice's delegation |

Most products are likely to hold desired state, and few to hold observed
usage. Finding out which is the point of the exercise.

## Answer key for task 4

Task 4 has a checkable answer, from the core's "Effects of administrative
changes" table and the scene 2 clock: `grant-1` was issued at 12:01:03
with a 300 s lifetime, and was redeemed at 12:01:04 for `access-1`, a
JWT access token valid until 12:11:04, with no refresh token.

| After the 12:02 withdrawal | Usable? | Until | Source |
|---|---|---|---|
| A new delegated grant for Alice and `agent-42` | No; the IdP returns `actor_unauthorized` | — | Core: Effects of administrative changes; PLAYBOOK: delegated recipe, rejection tests |
| `grant-1` | Already redeemed. A RAS that accepts a bound grant only once rejects it; one that accepts it again under explicit policy can redeem it until it expires | 12:06:03, at most | Core: Common Grant Validation (Grant replay) |
| `access-1`, validated offline at the API | Yes, unless revocation reaches the API another way | 12:11:04 | Core: Effects of administrative changes ("RAS authorization can continue until revocation is applied or its absolute expiration") |
| `access-1`, introspected by the API | Until the RAS applies a revocation, then no | When revocation is applied, or 12:11:04 | Core: Authorization Changes and Revocation |
| Continuation chains rooted under Alice's delegation | No further continuation (`invalid_continuation`); tokens already issued downstream remain until they expire | — | Continuation profile: Chain Ending and Governance Events |
| `agent-42`'s delegations for other users, and its Agent Authorization | Unaffected | — | PLAYBOOK: delegated recipe, rejection tests; The decisions an identity team owns ("None of these implies another") |

Withdrawal reaches `access-1` only if the IdP kept `grant-1`'s identifier
under Alice's delegation and a signal carries it to the RAS ("Authorization
Changes and Revocation" in the core). Whether a product can name
`grant-1` in its task 4 answer is part of what the exercise records.

## Recording the results

Fill in one table per product. Each cell is **exported** (the product
gives it directly), **derivable** (it can be reconstructed from logs or
another system), or **not held**, followed by the product's own name for
the field:

| Record kind | Desired state | Approval provenance | Expiration policy | Observed usage |
|---|---|---|---|---|
| Identity Binding | | | | |
| Client Association | | | | |
| Delegation Authorization | | | | |
| Oversight mode | | | | |
| Agent Authorization | | | | |
| Continuation Association | | | | |

Then record, for the pair of products:

* whether their task 1 exports describe the same effective
  authorization, and where they differ;
* whether each product's task 4 answer matches the answer key, and
  which rows it could not answer; and
* how each withdrawal was performed: through an API, an
  administrative screen, or not at all.

## What the results decide

Three outcomes are named in advance, so the results cannot be read to
fit a preferred answer:

| Outcome | The results point to it when |
|---|---|
| Extend the SCIM management profile with resources for these records | Products hold desired state, provenance, and expiry for most record kinds, and withdraw them through an administrative API, but the exports do not line up |
| Define a read-only export of effective authorization | Products can report the records but manage them in incompatible ways, or the needs are certification and audit rather than shared administration |
| Rely on the existing SCIM resources and lifecycle signals | Delegations come from policy or consent systems rather than stored records, and the task 4 answers depend on revocation signals rather than on the records themselves |

Observed usage that no product holds points to events or logs, not to
records, whichever outcome the other columns support.

## Running it

The exercise needs at least two independent products: two IdPs, or an
IdP and an identity-governance tool that reads it. It also needs people
who can configure scene 1 on each. This repository has neither.

Until then, the table can be tried against the
[reference implementation](../../conformance/README.md) as a dry run.
The reference holds desired state only, in memory, with no provenance,
expiry, or usage, so the dry run exercises the table, not the question.
Its test control can withdraw the delegation, and conformance case N09
shows that the next exchange fails with `actor_unauthorized`.
