---
name: emergency-fund-sizing
description: Size an emergency fund against the household's actual spending and risk factors — single earner, dependents, variable compensation — and flag both shortfall and excess cash. Use when asked how much cash to hold, whether savings are adequate, or before any recommendation that involves self-insuring a risk. Reads figures from a local facts file.
requires:
  - household.members
  - household.balance_sheet
  - household.annual_spending
---

# Emergency fund sizing

## Why this gates the rest

Every skill that says "you can absorb this loss" is making a claim about the
buffer. The property and casualty skills already refuse to recommend dropping
coverage from a household below the floor, whatever the price arithmetic says —
this is that rule promoted to a skill.

`cash.MIN_BUFFER_MONTHS` is a **single constant shared by both**, imported
rather than copied, so the two cannot disagree about it. If you change it, both
change.

The reasoning: self-insuring a risk means paying for it out of the buffer.
Without one, an ordinary setback is met with credit-card debt at 20%+, and the
premium saved is erased several times over.

## "Three to six months" is not an answer

The generic advice ignores the two things that actually drive the number.

| Factor | Why |
|---|---|
| **Single earner** | No second income, and no partial-loss case — it's all or nothing |
| **Dependents** | Longer job search, far less room to cut living costs |
| **Variable compensation** | Pay can fall sharply *with no job loss at all* |

The report shows the target built up from a base, one line per driver, so the
household can disagree with a specific adjustment rather than with the total.

## Measured against cash equivalents only

Not net worth, not retirement accounts. A household with a large 401(k) and no
cash cannot pay a deductible. The legacy `liquid` tier also contains marketable
stock because it can settle within days; an emergency reserve cannot silently
count that volatile, taxable position at par. The report therefore uses the
additive `liquidity_class: cash_equivalent` boundary and names marketable or
unclassified assets it excludes.

## Excess is a finding too

An emergency fund is insurance. Past the point where it covers the emergency,
more of it buys nothing while inflation erodes it.

The report flags cash beyond 1.5× target and hands off in order: first
`cash-yield-review` (is it even earning anything?), then the question of
whether some should be invested. **Yield first** — it's free and requires no
change in risk, whereas investing does.

## The essential-spending runway

The target uses **full** spending, deliberately. The report also shows the
longer runway available if spending is trimmed to essentials, as context.

Don't size the target on trimmed spending. A crisis is a bad time to be
discovering which costs are actually fixed, and the difference between "we'll
cut back" and having cut back is most of the failure.

## Closing

1. **Months held versus months targeted** — the one comparison.
2. **If short: say plainly that other recommendations are blocked** until it's
   filled. Don't bury it.
3. **If excess: hand off**, don't leave the money sitting.
4. **Name the triggers**: a change in earners, a new dependent, a shift toward
   variable pay, or a materially different spending level.

## Time-series output

Emit stable observations for months held, target dollars, and shortfall through
the shared structured-results channel. Compare only the same reserve definition;
a classification change is methodology, not new cash.

---

*Not financial advice.*
