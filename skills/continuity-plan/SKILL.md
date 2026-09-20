---
name: continuity-plan
description: Build a printable, privacy-conscious death and incapacity runbook from a local facts file, showing immediate actions, safe contact and record references, continuity resources, recorded transfer facts, and operational gaps. Use when a spouse, partner, fiduciary, or trusted helper needs to act without the plan author.
requires:
  - meta.as_of
  - meta.currency
  - household.members
---

# Continuity plan

## The decision

Decide whether the intended reader could execute the first steps after death or
incapacity without the plan author. Lead with operational readiness, then give
the two event paths. A sparse plan is still useful when it clearly says
`NEEDS COMPLETION`; it must never fill a gap with a generic legal checklist.

## What belongs in the plan

Use `lib/pf/continuity.py` to order safety and dependent care first, essential
cash flow and coverage second, legal and benefit notifications third, and
reversible optimization last. Keep death and incapacity separate: a will does
not establish authority while someone is alive.

Reuse the shared estate-document, beneficiary, digital-access, liquidity,
life-insurance, and debt functions. The continuity report is a runbook over
those facts, not a second implementation of their analysis.

## Privacy boundary

Print display-safe labels and pointers to a sealed contact or recovery package.
Never render passwords, passcodes, recovery codes, private keys, Social
Security numbers, full account or policy numbers, or document contents. Do not
put those values in `contact_via`, instructions, or location descriptions.
Extra credential fields are ignored, and obvious secrets or long numeric
identifiers in printable fields are suppressed.

The structured-output channel contains only critical-gap count and review age.
It never contains contacts, locations, account identifiers, or free-form plan
text.

## Readiness

- `ready`: the operational path works and no completion item remains.
- `incomplete`: immediate execution works, but noncritical inventory, review,
  transfer, or maintenance facts remain open.
- `blocked`: the reader cannot locate the plan or documents, reach a confirmed
  helper, maintain essential obligations, use the recovery process, cover an
  immediate dependent/business duty, or identify required institutions.

These labels assess execution, not whether an estate plan is legally or
financially optimal. Recorded title and beneficiary facts remain facts; the
report does not turn them into transfer conclusions.

## Boundaries

Do not promise benefits, tax treatment, transfer route, processing time, or
legal authority. Do not encode universal certificate counts, waiting periods,
or jurisdiction-specific steps without maintained reference data. Route estate
language, retirement elections, taxes, and fiduciary authority to the relevant
professional and specialist report before an irreversible action.

*Not financial, tax, or legal advice.*
