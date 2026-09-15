---
name: windfall-management
description: What to do — and mostly not do — after an inheritance, an IPO or liquidity event, a legal settlement, or any other large one-off receipt. Sizes the estimated-tax gap, states the tax character and basis treatment of each kind of windfall, flags the Form 3520 obligation on a gift or bequest from a foreign person, and names the beneficiary and IRMAA consequences. Use when asked about receiving an inheritance, a vesting or IPO liquidity event, a settlement, or a sudden large sum of money. Reads figures from a local facts file.
requires:
  - transitions.windfall
---

# Windfall management

## Do nothing for ninety days

Park it somewhere safe and liquid, make no irreversible commitments, and let
the urgency pass.

That is the recommendation. Everything else on this page is secondary to it,
and the report prints it first for that reason.

The case for it is not a market view. It is that **the decisions people regret
are made in the first month** — the house bought before the tax was set aside,
the loan to a relative that ends the relationship, the business someone else
was already looking for capital for, the annuity sold by a person who read the
probate filing, the resignation. None of those get worse by waiting. The
pressure to act immediately is real and it is coming from outside the
household, which is exactly why ninety days of nothing is worth more than any
allocation decision available in that window.

Three things are worth doing inside the pause, and all three are reversible:
**park it** in something insured or Treasury-backed, **cover the tax**, and
**name a beneficiary** on whatever account it landed in.

The report measures the window from the recorded `received` date. With no
date, it says it cannot tell rather than assuming the pause has elapsed — the
assumption that costs something is the optimistic one.

## The tax character is the whole analysis

Not the amount. Four households receiving $400,000 owe amounts that differ by
six figures depending on how it arrived:

| Kind | Income on receipt? | Basis |
|---|---|---|
| Inheritance | No | **Stepped up** to date-of-death value |
| Gift | No | **Carries over** from the donor |
| Inherited retirement account | No | **No step-up** — ordinary income as drawn |
| RSUs vesting at IPO | Yes, as wages | Equal to the amount included |
| Sale of shares already held | Yes, as gain | Unchanged |
| Settlement | **Depends on what it compensates** | Varies |
| Life insurance death benefit | No | n/a |

Two of these are worth dwelling on.

**An inherited *taxable* account and an inherited *retirement* account are
opposites.** The first arrives with the decedent's gain erased, which means
selling a concentrated inherited position is usually close to free — so
holding it for sentimental reasons is a concentration decision being made by
default. The second arrives with the decedent's full tax liability intact,
distributions are ordinary income, and most non-spouse beneficiaries must
empty it within ten years. Spreading that across ten tax years is normally the
largest single decision in an inheritance.

**A settlement cannot be characterised from an amount.** Physical injury is
excluded; emotional distress not arising from physical injury is not; lost
wages are ordinary income; punitive damages are taxable in essentially every
case; interest on the award is interest. The allocation in the agreement
largely controls, and it is far harder to argue about afterwards. The report
therefore excludes settlements from the tax estimate rather than guessing, and
says it has.

A `kind` not in the table returns **unknown** and the report refuses. Reasoning
by analogy from a kind that *is* there is precisely the failure the table
exists to prevent.

## The gap that catches people is withholding, not tax

Two mechanisms, both invisible until April.

**Supplemental withholding is 22%** on an RSU vest or a bonus below the annual
threshold — and 22% is a *withholding* rate, not a tax rate. A household at a
35% marginal rate is under-withheld by thirteen cents on every dollar, and
nothing on the pay stub says so. On $500,000 of vesting equity that is $65,000
before state tax.

**A windfall with no withholding at all** — an inherited IRA distribution, a
taxable settlement, a sale — creates an estimated-tax obligation that is
quarterly and penalised per quarter. A single catch-up payment in January does
not cure an underpaid Q3.

The defence is the **prior-year safe harbour**: pay 100% of last year's total
tax through withholding and estimates across the year — 110% if prior-year AGI
was over $150,000 — and the §6654 penalty does not apply however large the
final bill turns out to be. That matters because in a windfall year the
current-year figure is exactly the number nobody can compute yet. It is one
line on last year's return and it is the cheapest insurance in this skill.

## Beneficiary designations on every new account

A designation **overrides the will**. An account opened last month to hold the
money is, right now, outside the estate plan entirely — and a holding account
is the one nobody thinks of as part of one.

This skill only raises the flag. `beneficiary-audit` does the account-by-account
check, and running it is the point of the flag.

## The foreign-source case, which is not rare

**A gift or inheritance above $100,000 from a foreign person requires Form
3520.** No tax is due — it is reporting only — and the penalty for missing it
is a percentage of the amount received, which makes it one of the most
expensive forms to overlook.

Three details that catch people: the threshold is **aggregate across the year**
and across related donors, so a second gift later in the year can cross it
retroactively; the test is whether the **donor** was a nonresident alien or a
foreign estate, not where the money was wired from; and the obligation exists
whether or not the money was ever brought into a US account.

The threshold is imported from `lib/pf/reporting.py`, which owns it. See
`foreign-reporting-audit` for the FBAR and FATCA consequences of the account
the money landed in — receiving a foreign inheritance frequently creates a
foreign account at the same time.

## The two-year echo, and the one that hits this year

**IRMAA looks back two years.** Medicare premiums are set from the modified AGI
on the return filed two years earlier, so a large income year raises premiums
long after the money is spent, and it feels unrelated by the time it arrives.
It is a cliff rather than a taper — a dollar over a bracket costs the whole
step — and it applies for one year, then falls away. **A windfall is not a
life-changing event for SSA-44 purposes.** That form's list is specific: work
stoppage, divorce, death of a spouse, loss of income-producing property.
Receiving money is not on it. Budget for the surcharge; do not plan to appeal
it.

**ACA is the opposite timing.** If the household is on marketplace coverage,
the premium tax credit is advanced on estimated income and reconciled on this
year's return. Income over the eligibility ceiling means repaying the advance,
uncapped. Update the marketplace estimate mid-year — reconciliation is the
expensive way to find out.

## What it will not do

- **Tell you what to buy.** That conversation belongs after the ninety days,
  and it is an allocation question, not a transition one.
- **Compute state tax, NIIT, or the bracket the windfall pushes you into.**
  Every figure is federal and nominal, and is therefore a floor.
- **Characterise a settlement**, value an inherited business, or model the
  ten-year drawdown of an inherited IRA. The first needs the agreement, the
  second needs an appraiser, the third needs a multi-year projection this
  skill does not attempt.
- **Assume the pause has elapsed** when no date was recorded.

## Closing

1. **The pause**, and how many days of it are left.
2. **The tax character of each event** — and which of them could not be
   characterised.
3. **The safe-harbour number**, which is the action item with a deadline.
4. **Form 3520** if any of it came from a foreign person.
5. **Beneficiaries** on every account the money touched.

---

*Not financial, tax, or legal advice. The tax-character table is transcribed
statute and marked unverified — check it before relying on it.*
