---
name: employer-match-audit
description: Check whether front-loading 401(k) deferrals is forfeiting employer match — models the match formula shape, when deferrals hit the §402(g) ceiling, and whether the plan trues up. Use when asked about 401(k) contribution rate, maximising employer match, whether to front-load contributions, or if someone is "leaving money on the table". Reads figures from a local facts file.
requires:
  - household.members
  - contributions.year
  - contributions.employer_plan
---

# Employer match audit

## The error this exists to catch

A high deferral rate hits the §402(g) elective-deferral ceiling early in the
year. Deferrals then stop. If the plan calculates match **per pay period**, the
remaining periods earn no match — and unless the plan trues up after year end,
that money is simply gone.

**It is invisible on every statement.** The balance looks right, because the
deferrals arrived on schedule. Only the match is missing, and nothing flags it.
It recurs annually until someone notices.

## The distinction that decides the answer

**Two common formula shapes give opposite answers**, and the skill refuses to
guess between them.

| Formula | Front-loading |
|---|---|
| `percent_of_pay_per_period` — *50% of the first 6% of each cheque* | **Costly.** Match accrues only in periods you contribute. |
| `dollar_for_dollar_annual_cap` — *100% of contributions up to $X/year* | **Free.** The cap is annual; reaching it sooner changes nothing. |

This matters more than it sounds. Generic advice about front-loading is wrong
roughly half the time, delivered in the same confident tone either way — and
the household has no way to tell which half they're in without reading the
formula.

If `match_formula.type` is absent, the report says the question is
unanswerable and gives the exact question to ask:

> *"Is the match calculated per pay period or on annual compensation, and does
> the plan true up after year end?"*

Resist the temptation to infer the shape from the match's size or from what is
common. Both shapes are common.

## Unknown true-up is treated as at-risk

`true_up: null` means nobody has checked. The report treats that as exposure,
because it is: the money is at risk until someone confirms otherwise, and
"probably fine" is how this survives for years.

When `true_up: true`, the report says the timing would have forfeited money but
the plan recovers it — and still suggests confirming the true-up actually
lands, because it is a plan operation that can fail quietly.

## The fix, in order of preference

1. **Lower the deferral rate so contributions spread across the whole year.**
   Simple, immediate, and it costs nothing — the same total goes in.
2. Get written confirmation that the plan trues up.

Option 1 is usually better because it doesn't depend on the plan behaving.

## Closing

1. **The dollar figure at risk**, or a clear "nothing at risk and here's why."
2. **The formula shape**, named, since it's what drives the answer.
3. If the shape is unknown, **the question to ask HR**, verbatim.
4. Note that this recurs annually — put it in the calendar before open
   enrolment, not after.

## Out of scope

Whether to defer pre-tax or Roth, and total contribution space —
`contribution-space-audit` covers the latter.

---

*Not financial or tax advice. Statutory limits change annually; verify against
irs.gov.*
