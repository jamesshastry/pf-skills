---
name: equity-comp-review
description: Review an equity compensation vesting schedule for the cliff that occurs when a multi-year grant completes, and derive the steady-state income that remains without refresh grants. Use when asked about RSU income, vesting schedules, whether compensation is sustainable, or planning against variable pay. Reads figures from a local facts file.
requires:
  - equity_comp
---

# Equity compensation review

## The cliff an annual figure hides

Overlapping multi-year grants produce a smooth annual vesting number. That
number is not a run rate — it is the sum of several grants at different stages,
and it **steps down** when the oldest completes.

An income figure of "X per year in equity" conceals the moment X becomes
materially less than X. The report separates:

- **Run rate** — what is vesting now, including grants about to finish
- **Steady state** — what remains without a new grant
- **The delta**, and the date it lands

## Plan against the steady state

Sustaining the run rate assumes refresh grants continue at their present size.
That is:

- a **discretionary decision by someone else**,
- made **annually**, and
- **correlated with exactly the conditions in which it is least likely** — a
  weak share price, a cost-reduction cycle, a reorganisation.

So refresh dependence is not a neutral assumption. It is optimistic in exactly
the scenarios where it matters, which is the same correlation
`employer-concentration-risk` is about.

**Anything tested against income should be tested against the steady state.**
Housing affordability, savings rate, insurance need. Variable compensation is
the first thing to fall and the last thing people model.

## Two habits, both of which remove a decision

**Sell at vest as a standing policy.** Covered in
`employer-concentration-risk`; the point here is that it turns a quarterly
judgement into a one-time decision.

**Treat equity as a bonus, not as salary.** Budgeting fixed costs against
variable income converts a variable input into a fixed obligation. That is the
wrong direction, and it is how a pay cut becomes a crisis rather than an
inconvenience.

## What this doesn't cover

Option exercise strategy, ISO versus NSO treatment, AMT, 83(b) elections, and
ESPP mechanics. Those are tax questions with real complexity, and none is
modelled here. If options are in play rather than restricted stock, this skill
sizes the income and nothing else.

## Closing

1. **Run rate, steady state, and the date** — three numbers.
2. **Which downstream conclusions used the wrong one.**
3. **The refresh assumption named as an assumption**, with why it is optimistic
   in the cases that matter.

---

*Not financial or tax advice.*
