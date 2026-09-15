---
name: retirement-readiness
description: Project when retirement becomes affordable, as a range across withdrawal-rate and real-return assumptions rather than a single date. Uses actual spending, not a benchmark. Use when asked "can I retire", "am I on track", "what's my number", or how much is needed to stop working. Reads figures from a local facts file.
requires:
  - household.members
  - household.annual_spending
  - household.balance_sheet
  - retirement.annual_savings
---

# Retirement readiness

## The answer is a range, and saying so is the skill

The report produces a grid — three withdrawal rates by three real returns —
and the honest output is **the spread**, not the middle cell.

A half-point change in either assumption moves the date by years. Quoting one
number to the dollar implies a precision that a multi-decade projection cannot
support, and the false precision is what makes people either complacent or
needlessly grim.

Lead with the range. Give the central case as one cell within it, clearly
labelled as an assumption rather than a finding.

## Deterministic, and it says so

This is a constant-real-return projection. No real sequence delivers that.

**It says nothing about sequence-of-returns risk**, which is the dominant
danger in the first years of drawdown — a bad first decade can exhaust a
portfolio that the average return says was fine. For distributions rather than
a single path, point at a dedicated Monte Carlo tool. Don't pretend.

The design decision behind that (ROADMAP question 1, now closed): reimplement
simply rather than wrap a modelling library. The value here is the framing and
the sensitivity, not a third significant figure, and a heavy dependency would
cost the auditability that is the point of this project.

## Real, throughout

Today's money, discounted at a real return. A nominal projection produces a
much larger and entirely meaningless number, and mixing a nominal return into
real spending is a defect class this project has already been bitten by.

If you quote a figure, say which it is.

## Use their spending, not a benchmark

The target is derived from **actual annual spending**. Replacement-ratio rules
of thumb — 70% or 80% of final salary — are worse data than a number the
household can look up, and they are systematically wrong for high savers,
whose spending is a much smaller fraction of income than the rule assumes.

## Spending is the strongest lever, and it works twice

A dollar less of annual spending cuts the target by 20–29× *and* raises annual
savings. Nothing available on the return side comes close, and unlike return
assumptions it is under the household's control.

Say this when the date looks too far away. It is more useful than any
adjustment to the projection.

## The withdrawal rate is a rule of thumb

It came from historical sequences over a fixed horizon. Longer retirements,
different asset mixes, and fee levels all move it. That is precisely why the
report runs three rather than one.

## Closing

1. **The range**, with the central case labelled.
2. **What would move it most** — spending first.
3. **The caveats**, particularly sequence risk, without burying them.
4. If already funded, **say the question has changed**: from accumulation to
   sequencing, taxes, and purpose.

---

*Not financial advice. A deterministic projection, not a simulation.*
