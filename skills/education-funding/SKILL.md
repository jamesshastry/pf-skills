---
name: education-funding
description: Size the gap between projected education costs and dedicated savings per child, apply the retirement-before-education ordering rule, and cover 529 mechanics including state tax treatment, financial-aid assessment and the capped 529-to-Roth rollover. Use when asked about college savings, 529 plans, whether to fund education or retirement first, or how much university will cost. Reads figures from a local facts file.
requires:
  - household.members
  - education.children
---

# Education funding

## Lead with the ordering rule, before any number

**Retirement funding comes before education funding.** Not as a preference — as
an asymmetry:

> **You can borrow for education. You cannot borrow for retirement.**

A household that underfunds retirement to fully fund college converts a
solvable problem into an unsolvable one, and the children inherit the
consequence anyway, in the form of parents who cannot support themselves.

The report puts this first and, where the facts allow, **applies** it rather
than merely stating it: it runs the readiness check and says whether education
funding is currently competing with retirement. If retirement is not on track,
every gap below should be closed by borrowing, working, a cheaper institution
or a partial contribution — not by diverting retirement savings.

This is the one place in the whole repository where a skill reaches into
another's logic, and it earns the coupling: the ordering rule is worthless as
an abstract principle and useful as an applied one.

## A 529 has exactly one beneficiary

Households think of "the college fund". The form names one child.

An account with no recorded beneficiary is reported as **unallocated**, not
split between children — splitting would invent an allocation nobody made. The
report also says the headline gap is overstated by that amount until it's
resolved, so nobody acts on an inflated shortfall.

Changing the beneficiary to another qualifying family member is permitted, and
is a decision rather than an assumption. Record who is actually named.

## Two arithmetic points that are easy to get wrong

**Inflate each year of study separately.** Year four carries three more years
of inflation than year one; inflating the whole bill to the start date
understates it.

**Education savings grow at a lower assumed return than retirement savings.**
Money needed on a fixed near date cannot be invested like money needed in
thirty years. Related: inside about three years of the first bill, an
equity-heavy glide path is taking a risk the timetable cannot absorb — the bill
arrives whatever the market did. The report flags this per child.

## Mechanics worth raising unprompted

**State tax treatment is jurisdiction-specific and often absent.** Some states
deduct contributions; some have no income tax so the question cannot arise;
some tax income and offer nothing — California among the largest. **Where there
is no deduction, the in-state plan has no tax advantage and should be chosen on
fees alone.** The state table follows the cited-table pattern: a state is in it
only if checked.

**Financial aid treats a parent-owned 529 lightly** — around 5.64% of value,
against 20% for assets in the student's own name. Moving money into a child's
name to save tax can cost more in lost aid than it saves.

**Leftover balances are no longer trapped, but the escape is capped.** A 529 can
be rolled to the beneficiary's Roth IRA, subject to a lifetime cap, a minimum
account age, a look-back excluding recent contributions, the beneficiary's
annual Roth limit, and their earned income. Useful, slow, and **not a reason to
overfund.** The other routes — change the beneficiary, hold it for a future
generation, or withdraw and pay tax plus penalty on the *earnings only* — are
worth stating too, because the fear of being trapped drives real underfunding.

## Closing the gap, in order

1. **A cheaper institution.** The largest lever, considered last. The spread
   between in-state public and private usually exceeds everything else
   combined.
2. **Current cash flow during the study years.** For a high earner this is
   often the plan, not a failure of one.
3. **The student's contribution** — work, scholarships, a reasonable loan in
   their name.
4. **Federal loans in the student's name** before anything in the parents'.
   Parent loans carry no forgiveness or income-driven repayment worth the name.
5. **Not** reducing retirement contributions.

## Out of scope

Choosing a specific 529 plan or investment option, scholarship strategy, aid
appeals, and the tax treatment of scholarships. Cost figures come from the
facts file — this skill does not know what any institution charges.

---

*Not financial or tax advice. Aid formulas, 529 rules and state treatment
change; the state table records itself as unverified.*
