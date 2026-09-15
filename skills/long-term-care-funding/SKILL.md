---
name: long-term-care-funding
description: Size a multi-year long-term care episode against investable assets, test whether the surviving spouse's retirement still works afterwards, and decide between self-insuring, a traditional long-term care policy, and a hybrid life-LTC contract. Applies the same insure-what-you-cannot-absorb rule as the property and income-protection skills, and states plainly that traditional policy premiums are not guaranteed. Use when asked about long-term care insurance, nursing home costs, aging parents, assisted living, or what happens if one spouse needs care. Reads figures from a local facts file.
requires:
  - household.members
  - household.balance_sheet
---

# Long-term care funding

## The idea

This is the **largest uninsured tail risk most households carry**, and the
shipped insurance cluster does not touch it. Auto, property, umbrella,
life and disability are all covered. A multi-year care episode — which is more
likely than a house fire and an order of magnitude more expensive — is not.

## The rule is the repository's rule

**Insure what you cannot absorb.** The absorb bands are `auto.py`'s and are
imported rather than restated: under 5% of assets, self-insure; over 25%,
transfer; between, partial.

Two things change for long-term care and both are stated in the report.

The **denominator is investable assets, not liquid**. An auto total loss settles
in weeks. A care episode drains the same portfolio that funds the rest of
retirement, over years. Illiquid holdings are excluded — a 529 is on the balance
sheet and is not what pays a care bill, and counting it would flatter the test
in the direction of doing nothing.

The **share of assets is only a screen**. The test that decides it is below.

## The test that actually decides it

Not "can the household afford the bill". **Can the spouse who did not need care
still retire afterwards.**

The report takes the tail-length episode out of the portfolio, applies the
library's withdrawal rate to what remains, and compares the result to the
survivor's spending. A shortfall there is the finding — and a household can pass
the percentage screen comfortably and still fail this one, because the surviving
spouse needs the portfolio for another twenty or thirty years.

The risk being insured is not the care bill. It is impoverishing the spouse who
stayed well.

## Traditional LTC has a poor history and it is not a footnote

Carriers priced early blocks assuming policyholders would lapse at normal rates
and that interest rates would stay high. Neither happened. In-force blocks have
since carried repeated rate increases, approved by regulators, in some cases
cumulatively large enough to force holders to cut benefits or drop cover — after
decades of premiums, at the age when the policy was about to matter.

**The premium on a traditional policy is not guaranteed**, and the increase
arrives at the worst possible moment. Anyone buying one should price a scenario
where it rises substantially and ask whether they would still pay it. If the
answer is no, the policy is not affordable today.

That is a real argument against the product, and this skill states it rather
than burying it under a comparison table.

## Hybrids answer that objection and introduce others

Premium usually guaranteed, and an unused benefit pays as a death benefit — so
the money is not lost, which is the actual reason people buy them. Against that:
much less care benefit per dollar, a large sum tied up in a low-return contract,
and a surrender value that makes the illustration look better than the internal
return is.

**Do not compare them on premium.** Compare maximum benefit per dollar committed
and price the opportunity cost of the capital — the same arithmetic
`life-insurance-review` applies to cash-value life policies.

## Two things people believe that are not true

**Medicare does not pay for long-term care.** It covers limited skilled nursing
after a qualifying hospital stay, not custodial care, which is what a multi-year
episode consists of. This misconception is the reason households arrive at 80
with no plan.

**Medicaid is means-tested and requires a spend-down**, with a transfer lookback
and state-specific community-spouse protections and estate recovery. It is the
real backstop for most households, and it is not a plan.

## What it will not do

- Model Medicaid eligibility, the transfer lookback, or whether a gift is safe.
  Those are state law and need an elder-law attorney in your own state.
- Quote a care cost. Costs are regional, move faster than general inflation, and
  come from `healthcare.ltc.annual_cost_today`. A national average applied to a
  high-cost metro understates the exposure badly, and the error runs toward
  inaction.
- Project care-cost inflation. The report is in today's money against today's
  assets and says that it therefore understates an episode thirty years out.
- Recommend a specific policy or carrier.

## Closing

1. **The verdict**, and the band it came from.
2. **The survivor test** — the number that decides it.
3. **The three options** compared on benefit per dollar, not on premium.
4. **The rate-increase history question**, asked of the carrier, not the
   illustration.
5. **Underwriting is a deadline.** Like disability cover, this is available
   until abruptly it is not.

---

*Not financial, tax, or legal advice. Medicaid rules are state law and are not
modelled here.*
