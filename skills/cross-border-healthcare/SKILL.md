---
name: cross-border-healthcare
description: Price the Medicare Part B keep-or-drop decision for time spent living abroad — premiums for cover that cannot be used, against a permanent late-enrolment penalty on the way back in — plus the limits of the Medigap foreign travel benefit and what private expatriate cover must be checked for. Use when retirement abroad or a long stay outside the US is contemplated by anyone near or past Medicare age. Reads figures from a local facts file.
requires:
  - crossborder.medicare.months_abroad_planned
  - crossborder.medicare.standard_premium_monthly
---

# Cross-border healthcare

## The idea

**Medicare does not pay for care received outside the United States.** The
exceptions are narrow and situational — a foreign hospital nearer than a US one
in an emergency, transit between Alaska and the lower 48 — and they are not a
travel benefit. Everything in this skill follows from that one fact.

Which puts a household living abroad in an odd position: Part B premiums buy
nothing usable while away. The obvious response is to drop it. The obvious
response is the trap.

## The decision rule

Keeping Part B while abroad does not buy healthcare. It buys **the right to
come back without a permanent penalty**, which is a different product, and this
skill prices it as one.

| | Cost |
|---|---|
| Keep | premium × months abroad — paid for cover you cannot use |
| Drop | 10% of the standard premium for each full 12 months uncovered, **permanently**, for as long as you hold Part B thereafter |

The comparison has a real boundary. The keep cost is **linear in time abroad**;
the penalty cost is time abroad **multiplied by years lived after returning**.
Long absences followed by long lives favour keeping. Short absences, or a
genuine intention never to return, favour dropping.

The penalty counts **full years only** — eleven months uncovered is free and
thirteen is not.

## The two consequences that are worse than the penalty

**Re-enrolment is not on demand.** Someone who dropped Part B gets back in
during the General Enrolment Period, 1 January to 31 March. A return in April
can mean months uninsured. Living abroad is generally **not** creditable
coverage and does not create a special enrolment period — the SEP exists for
coverage from *current employment*, which a foreign retirement is not.

**Medigap guaranteed issue does not wait for you.** It runs for six months from
Part B starting. Come back years later in poorer health and a carrier can
medically underwrite or decline. The penalty is a known surcharge you can put a
number on; being uninsurable for the supplement is not priceable at all, and it
gets a fraction of the attention.

## The Medigap foreign travel benefit is a holiday benefit

Where a Medigap plan includes it — not every plan letter does — it pays 80% of
emergency care after a $250 deductible, during the **first 60 days of a trip**,
up to **$50,000 lifetime**. Not annual. Lifetime.

Read those four limits together and the shape is clear: one serious admission
abroad exhausts the cap, and month five of a five-month stay is outside the
trip window entirely. It is cover for a holiday that goes wrong, and it should
never be planned around as expatriate cover.

## Private expatriate cover, and the four questions

The genuine alternative, and the report asks for a real quote at your actual
age rather than accepting a placeholder — expat premiums rise steeply with age
rather than smoothly, so a rounded guess is badly misleading here.

Check, before relying on one: whether it is **guaranteed renewable** or can be
declined at the next anniversary; whether it **terminates or reprices at an age
cap**; how **pre-existing conditions** are treated, which is where most claims
fail; and whether it covers **repatriation**, the expensive event nobody
budgets for.

Note that expat cover and Part B are not substitutes. One covers you where you
live; the other preserves your route back.

## The IRMAA link

Premiums are income-related, and the penalty is a percentage of them. A Roth
conversion raises modified AGI, raises the Part B premium two years later, and
raises the surcharge with it. See `roth-conversion-window` and
`roth-portability-check` — in a cross-border plan these three interact and
conversions are frequently recommended in isolation.

## What it will not do

It will not say whether a destination's public system will admit you, or on
what terms — residency status, contribution history and age limits all bear on
it and none is in this repository's tables. It does not project premiums; every
figure is a nominal current-year amount you supplied. It does not cover
Medicare Advantage, whose network rules abroad differ and have to be read on
the plan.

**The weakest input is whether you will return to the US.** It is an intention
rather than a fact, it decides the whole comparison, and it is the one people
revise. An unrecorded intention produces both arms priced, never an assumption.

## Closing

1. **The keep-or-drop number**, and which way it falls.
2. **The two non-price consequences** — the enrolment window and Medigap
   underwriting — which routinely outweigh the arithmetic.
3. **The Medigap lifetime cap**, if a foreign travel benefit is being counted
   on.
4. **A real expat quote at your real age**, before the decision is made.

---

*Not financial, tax, or legal advice. Enrolment rules and penalty mechanics should be
confirmed against medicare.gov before acting; the figures here are yours, not fetched.*
