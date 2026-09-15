---
name: cfc-gilti-screen
description: Establish whether a foreign company is a controlled foreign corporation, name the information returns that follow — Form 5471 by category, Form 8992, Form 8865, Form 8858 — and price the penalties for not filing them. A screen that stops before computing GILTI, deliberately. Use when holding shares in a non-US company, consulting through a foreign entity, sharing a family business abroad, or wondering whether a dormant overseas company needs a US filing. Reads figures from a local facts file.
requires:
  - expat.foreign_entities
---

# CFC and GILTI screen

## A screen, not a calculator

This establishes three things and then stops:

1. **Does a controlled foreign corporation exist?**
2. **Which information returns follow from it?**
3. **What does not filing them cost?**

All three are knowable. The GILTI inclusion is not knowable from here, and
this skill does not pretend otherwise.

## The two thresholds, and both are required

- **US shareholder:** a US person owning **10% or more of vote *or* value**.
  Value catches people who assumed non-voting shares kept them out.
- **CFC:** US shareholders *together* owning **more than 50%** of vote or
  value, on any day of the year.

*More than* 50%, not 50%. An even split between a US person and a foreign
partner is the case everyone assumes is caught, and it is not.

Being under the control threshold is not the same as having no filing. Form
5471 has five categories, and an acquisition that merely crosses 10% is one of
them.

## The part with no tax attached, which is the expensive part

Form 5471 carries **$10,000 per form, per year**, plus the same again per 30
days after IRS notice up to a cap, plus a 10% reduction in foreign tax
credits. **None of it requires any tax to be due.** A dormant company that
earned nothing, held for three years, with three unfiled forms, is a
six-figure exposure entirely on its own.

And the consequence that outlasts the penalty: **an unfiled Form 5471 keeps
the statute of limitations open on the entire return**, not just the part
about the entity. Years that felt closed are not closed. This is usually the
larger problem and it is the one nobody has heard of.

## Screening only for "foreign corporation" is how these get missed

A foreign partnership is Form 8865. A foreign disregarded entity or branch —
including a single-member foreign LLC, and an unincorporated consulting
business run from abroad — is **Form 8858**, which is the one people have
never heard of. A foreign trust is Forms 3520 and 3520-A. None of them are
CFCs and all of them are filings.

## Direct ownership understates the position

Attribution rules treat shares held by a spouse, children, parents,
partnerships and trusts as yours. A family company in which no individual
holds a majority can still be a CFC. Two related minority holders is the
ordinary case, not an edge case — so read every percentage in the report as a
floor.

## What it refuses, and why that is the point

**No GILTI computation. No §962 election modelling.**

The election interacts with the §250 deduction, indirect foreign tax credits,
the later distribution being taxed a second time, state treatment that
frequently does not follow the federal result, and QBI. A figure produced
without all of that would look exactly as authoritative as one produced with
it. False precision is most expensive precisely where the stakes are highest,
and this is the highest-stakes corner of the cluster.

Unrecorded ownership is reported as **cannot be determined** — never as below
the threshold. Nobody having looked is the most common state and is a finding.

## Closing

1. **Any CFC verdict is a stop sign**, not a to-do item.
2. **Count the unfiled years, not just this one.** The penalty is per form per
   year.
3. **Do not simply start filing** if years are missed. The remediation path
   differs sharply depending on whether the failure was non-wilful, and that
   is the first conversation to have — before anything is filed.
4. **Then a cross-border CPA or EA.** Every path out of this screen ends
   there.

---

*Not financial, tax, or legal advice. This is a screen; the computation it stops short of needs
a professional.*
