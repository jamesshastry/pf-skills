---
name: state-domicile-exit
description: Check whether a state has actually released domicile after a move away — the severance steps that carry weight, the separate statutory-residence hook, source income that stays taxable regardless, and whether the state conforms to the federal foreign earned income exclusion. Use after moving between states or abroad, when a former state is still sending notices, or before assuming that leaving the country ended a state tax obligation. Reads figures from a local facts file.
requires:
  - state_exit.from_state
---

# State domicile exit

## The rule people get backwards

**You do not lose a domicile by leaving. You lose it by acquiring another
one.**

Domicile is singular and sticky: the old one persists until a new one is
established with the intent to remain indefinitely. A household that leaves
for a posting abroad, keeps a home, and intends to come back has not changed
domicile, however many days it is away. Moving somewhere you are yourself
uncertain about is precisely the case where the former state's claim survives
— and it is the common case for a first year abroad.

This is why a checklist of severance steps is the evidence and a calendar is
only one item on it.

## Two hooks, not one

**Domicile** is one way a state taxes you. **Statutory residence** is another,
and it is independent: many states tax someone as a resident on a day count
plus a permanent place of abode, whether or not they are domiciled there.
Winning the domicile argument and still being a statutory resident is a
common, expensive outcome.

And **source income is taxed either way**. Wages for work physically performed
in the state, rent from property there, and income from a business operating
there remain taxable to a non-resident. Leaving changes the residency
question, not the sourcing one.

## The sticky states, and what this skill will actually assert

California, New York, Virginia and South Carolina have reputations for
pursuing departed residents. **That is a practice observation, not a rule, and
this skill asserts no rule about any of them beyond what is in the cited
table.**

The table holds **California and Texas** — checked, with a source and a
verification date, following the `jurisdiction.py` pattern. Every other state
returns nothing and the report says so. It does not reason by analogy from the
two it knows, because state residency rules diverge more than they converge
and the ones that hurt are the ones that differ from the one you have read
about. If your state is not in the table, read that state's own published
residency guidance.

What the two entries say:

- **California** has no day-count bright line at all. Residency turns on
  closest connections, weighed on the facts. There is a narrow statutory safe
  harbour for a long uninterrupted employment-related absence, and it is lost
  by spending too much time back in the state.
- **Texas** levies no personal income tax, so there is no residency
  determination to win or lose — but domicile still governs community property
  and probate, and moving between a community-property state and a common-law
  one changes the character of assets acquired on each side of the move.

## The interaction with the federal election

**Whether a state conforms to the federal §911 exclusion is not recorded here
and must not be assumed.** State conformity to federal exclusions is
piecemeal. If a state still treats you as a resident, foreign earned income
excluded on your federal return may be fully taxable at state level — which
can make the state question worth more than the federal one in `feie-vs-ftc`.

## One ledger

Days in the state are counted from the same `presence.days` ledger that
`foreign-presence-tests` reads, on the part-day basis, because two
implementations of "a day" eventually disagree. If the ledger has no `state:`
detail on US stays, the count is reported as **unknown** rather than zero. An
uncounted day is not a day you were absent.

## Closing

1. **Has a new domicile actually been established?** If not, the rest is
   detail.
2. **Work the outstanding list in order.** The first four items carry most of
   the weight.
3. **Unrecorded is not done.** Each item is a question an examiner asks by
   name.
4. **File the part-year or non-resident return** rather than simply stopping.

---

*Not financial, tax, or legal advice. State residency is decided on the full facts by that
state's revenue authority.*
