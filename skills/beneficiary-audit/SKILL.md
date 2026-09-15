---
name: beneficiary-audit
description: Audit beneficiary designations across accounts and insurance policies — missing primaries and contingents, shares that don't total 100%, minors named directly, the estate named as beneficiary, and trusts named but unfunded. Use when asked about estate planning, what happens to accounts on death, whether a will covers everything, or after any birth, death, marriage, or divorce. Reads figures from a local facts file.
requires:
  - household.members
  - household.balance_sheet
---

# Beneficiary audit

## Why this is the highest-value hour in personal finance

**Beneficiary designations override the will.**

Not "interact with", not "are read alongside" — override. Retirement accounts,
life insurance, and transfer-on-death registrations pass by designation,
outside the will entirely, and for most households that is the majority of the
money. A carefully drafted estate plan is routinely defeated by one form
somebody filled in years ago and never revisited.

The work is an hour of phone calls. The failure mode is total.

## This is an audit, not a model

Almost no arithmetic. It checks completeness and internal consistency, and it
cannot tell you whether the designations are *right* — only whether they are
coherent and present. Say so. A checklist that presents itself as analysis
invites the reader to calibrate on the wrong thing.

## The three states, and why the distinction matters

| State | Meaning |
|---|---|
| Field omitted | **Unknown — nobody has looked** |
| `beneficiaries: []` | Checked, and none named |
| `beneficiary_applicable: false` | Not that kind of asset |

**Most audits fail at "unknown," not at a wrong designation.** That is the
finding: not that something is broken, but that nobody has checked, and the
form says whatever it said the day it was signed. Resist the urge to treat
unknown as probably-fine — it is the state most likely to be hiding the
problem, precisely because nobody has looked.

## What it checks

**No contingent beneficiary** is the most common real defect. People name a
spouse and stop. If the primary dies first — or in the same accident — the
asset lands in the estate, which is the exact outcome the designation existed
to avoid.

**A minor named directly** is the most expensive. A minor cannot receive
proceeds, so a court appoints a guardian of the estate: slow, supervised,
expensive, and it hands over the entire balance outright the day they reach
majority. Name a trust for their benefit instead — that is usually why the
trust exists.

**The estate named as beneficiary** forces probate and, on a retirement
account, usually shortens the payout period available to heirs.

**Shares not totalling 100%** leave a remainder allocated by the custodian's
default rules rather than by anyone's intent.

**Per stirpes versus per capita**, where children are named, decides whether a
predeceased child's share passes to their own children or is split among the
survivors. Two very different outcomes, and it is usually left at whatever the
form defaulted to.

## Closing

1. **Lead with the count of unknowns**, not just the defects. "Seven of ten
   designations have never been checked" is the actionable finding.
2. **Say where the fix happens: with each custodian.** Not with a lawyer, not
   in the will. Each institution has its own form and the change is not
   effective until they confirm it — get the confirmation in writing and
   record the date.
3. **Name the re-run triggers**: birth, death, marriage, divorce, new account.

## Out of scope

Whether the trust language is correct, tax consequences of a given
designation, and anything requiring legal judgment. This finds the forms that
need attention; an attorney decides what they should say.

---

*Not financial, tax, or legal advice.*
