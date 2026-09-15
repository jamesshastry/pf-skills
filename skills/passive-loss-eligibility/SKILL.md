---
name: passive-loss-eligibility
description: Decide whether rental losses can offset W-2 income at all under §469 — the $25,000 allowance and its phase-out, Real Estate Professional Status, and the short-stay exception — before any deal is modelled. Use when asked about rental property tax benefits, depreciation write-offs against salary, whether to claim real estate professional status, short-term rental tax strategy, suspended passive losses, or a grouping election. Reads figures from a local facts file.
requires:
  - real_estate.activities
  - real_estate.participation.magi
---

# Passive loss eligibility

## This is a gate, not a calculator

It runs **first**, before `rental-deal-underwriting` and before
`cost-segregation-screen`, and the other two are meant to be read in light of
its answer.

A rental loss is passive under §469. Passive losses offset passive income. They
do not touch wage income unless a specific door opens, and the sales pitch for
investment property routinely assumes one is open without checking. Quote an
after-tax return, a "depreciation shelter" or a cost-segregation benefit to a
household whose gate is shut and you have quoted a number that is simply wrong
— not conservative, not approximate: wrong in the direction the person wanted.

So the output here is a door, or no door. Everything downstream is conditional
on it.

## The three doors, in the order a W-2 earner can actually use them

**The short-stay exception is first, because it is the one that works.** An
average customer stay of **seven days or less** makes the activity *not a
rental activity* under Reg. §1.469-1T(e)(3)(ii)(A). The per se passive rule in
§469(c)(2) never attaches. It becomes an ordinary trade or business, and
**material participation alone** — more than 100 hours and more than any other
individual, or 500 hours outright — releases the loss against salary. No REPS,
no 750 hours, no majority-of-working-time test.

Two things defeat it in practice. The average is **total rental days divided by
number of bookings**, not the typical stay and not the nightly minimum; one
month-long winter booking can drag the average over seven. And the "more than
anyone else" comparison counts the **cleaner and the property manager**, whose
hours on a short-stay property routinely exceed the owner's. That single fact
is the commonest reason this door looks open and is not.

**REPS is second, and for a full-time employee it is close to unattainable.**
It needs 750+ hours in real property trades **and more than 50% of all personal
services in any trade or business**. The hours are the easy half. The majority
test is the one a 2,000-hour job defeats arithmetically, and it is tested per
spouse, not per household — which is why the standard answer in a two-earner
couple is that one spouse qualifies or nobody does. It is among the most
heavily audited positions in the individual code, and it survives on a
contemporaneous log kept as you go. Reconstructions written after the notice
arrives have been rejected repeatedly.

**The $25,000 allowance is last, because the households that want it cannot
have it.** It requires active participation — a low bar — and then phases out
at 50 cents per dollar of MAGI above the floor, which means a $50,000 band
consumes the whole allowance. Above the ceiling it is zero. It is also a
**household-wide cap across all properties**, not a per-property figure.

## The statutory figures come from the facts file

`assumptions.passive_loss_allowance`, `..._phaseout_start` and
`..._phaseout_end` are asked for, never carried in the library. `REVIEW.md` A3
already records one unverified tax-code mirror here; this skill does not add a
second. Absent them the report describes the door and **refuses to evaluate
it** — reported as unresolved, never as closed.

The structural tests are different and *are* in the module: 750 hours, 50%,
seven days, 100 hours. Those define the shape of a door rather than a figure,
they have not moved since 1986, and a facts file is not the place to edit the
statute.

## A disallowed loss suspends — it does not vanish

This is the part that changes the decision rather than just the number.

Losses the gate blocks carry forward indefinitely. They offset future passive
income, and the **entire accumulated balance is released** on a fully taxable
disposition of the activity to an unrelated party. So a shut gate is a timing
problem, not a loss — which is exactly why the cost-segregation screen treats
acceleration behind a shut gate as worth approximately nothing today rather
than as a write-off.

## The grouping election cuts both ways

Reg. §1.469-9(g) treats all rental interests as a single activity, so material
participation is tested once against combined hours instead of property by
property. Without it, a portfolio that clears the hours in aggregate can fail
on every individual property — a real and common outcome.

The cost is on exit: suspended losses are released only when the **entire
grouped activity** is disposed of, so selling one building out of five releases
nothing. The election is not casually revocable. Make it deliberately.

## What it will not do

It does not decide whether you qualify. It applies the tests to hours and stay
lengths that **you** recorded, and the recording is the weak point: an
undocumented 750 hours is not 750 hours. It does not compute your MAGI, model
at-risk limitations under §465 (a separate limitation that applies before
§469), or handle the self-rental rule. It takes no view on whether the
short-stay structure is worth the operating burden it implies — that is an
operations decision with a tax consequence, not a tax decision.

## Closing

1. **Which door, if any.** If none, say so plainly and stop quoting after-tax
   returns.
2. **The suspended balance**, and the disposition that releases it.
3. **The weakest input** — nearly always the participation log. Start it today;
   it cannot be created retroactively.
4. **Then, and only then**, run `rental-deal-underwriting` and
   `cost-segregation-screen`.

---

*Not financial, tax, or legal advice. §469 positions, and REPS in particular,
are audited. Take a position with a professional who will sign the return.*
