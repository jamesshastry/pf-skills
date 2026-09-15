---
name: umbrella-liability
description: Size a personal umbrella (excess liability) policy against the household's attachable assets and future earnings, check whether the underlying auto and renters/homeowners limits qualify for a carrier to attach above them, and name what the umbrella does not cover. Use when asked about umbrella or excess liability insurance, whether existing coverage is enough, or how to protect assets from a lawsuit. Reads figures from a local facts file; contains none of its own.
requires:
  - meta.jurisdiction.state
  - household.balance_sheet
  - household.members
  - auto.coverage
  - property.coverage
---

# Umbrella liability

## The idea

An umbrella is the cheapest liability coverage on the market by a wide margin
— roughly $150–300 for the first million and $75–150 for each one after — and
it is the coverage most households don't have. It sits on top of both the auto
and the renters/homeowners policy and pays judgments above their limits.

It is also the one line where the household's own balance sheet is the thing
being insured, which changes how you size it.

## Sizing: assets plus earnings, not net worth

Two adjustments to the obvious answer, in opposite directions:

**Down.** Retirement accounts are largely out of a judgment creditor's reach —
ERISA protection is broad, IRA protection is state-set. Sizing against total
net worth over-buys.

**Up, and by more.** A judgment does not stop at the balance sheet. Future
wages are garnishable, which for a high earner is often the larger number. The
script uses a two-year gross-income proxy; it is a judgment call, and worth
saying so out loud rather than presenting as derived.

Then round **up** to the nearest million, because that is the only granularity
sold — and because the underwriting cost sits in the first layer, so the
marginal million is roughly half the price of the first. If the limit is a
close call, round up.

> **Net worth is itself a risk factor.** Liability settlements scale with the
> defendant's ability to pay. The same collision produces a modest settlement
> against someone with $50,000 and an aggressive one against someone with $2M
> and a high income. Accumulating assets increases the exposure, which is
> precisely why this coverage becomes more necessary as a plan succeeds.

## Run it

```bash
uv run skills/umbrella-liability/run.py --facts inputs/facts.yml
```

Attachment thresholds are **imported** from `lib/pf/auto.py` and
`lib/pf/property.py`, not restated in `lib/pf/umbrella.py`. Keep it that way.
A duplicated threshold drifts, and a drifted one here tells a household it
qualifies to bind when it does not — which they discover on the phone, or
worse, at claim time.

## The attachment gate comes first

No carrier binds excess coverage over underlying limits that do not qualify.
This is a hard sequencing constraint, not a preference:

1. Raise auto BI and PD to the attachment points
2. Raise renters/homeowners personal liability to its attachment point
3. **Then** quote the umbrella

Get this wrong and the call to the carrier is wasted. If the gate fails, the
skill says *don't call yet* and points at `auto-insurance-review` and
`renters-homeowners-review`, which own those fixes.

Note the two attachment points differ — auto and property are checked against
different numbers. Read them off the table rather than assuming one.

## What it does not cover — the part worth the whole review

**An umbrella does not extend UM/UIM.** This is the single most valuable thing
to say, because it is the gap people believe they have closed.

An umbrella covers liability *you* owe someone else. The coverage that pays
*your own family* when an uninsured driver injures them is UM/UIM on the auto
policy, and it stops at that policy's limit no matter how large the umbrella
above it. A household can buy $2M of excess liability and still have $30,000
standing behind a spouse who is permanently injured by an uninsured driver.

**Excess UM/UIM is a separate election.** Not every carrier offers it, and it
is often available only where the umbrella carrier also writes the auto —
which can be a reason to consolidate. Ask for it by name; it will not be
offered.

Also surfaced, because none of it is obvious:

- **Underlying exclusions pass through.** An umbrella generally won't cover
  what the policy beneath it excludes by endorsement. A dog exclusion attached
  years ago to a household with no dog narrows the excess layer and buys
  nothing — have it removed.
- **A self-insured retention** applies where the umbrella covers something the
  underlying policies don't, so there's no limit for it to sit above.
  Typically $250–1,000. It is the deductible nobody mentions.
- **Business activity, rideshare and delivery driving** are excluded. Rideshare
  voids the personal auto policy and the umbrella above it together.
- **Board service** for a nonprofit or HOA is excluded by most personal
  umbrellas and needs a rider or the organisation's own D&O cover.
- **Every resident of driving age must be listed.** An undisclosed resident
  driver is the most common reason an excess claim is denied — and a household
  with a new teenage driver is exactly when the umbrella earns its premium.

## Where to buy

Bundling with the existing auto carrier is nearly always cheapest and makes
the attachment question trivial. A standalone excess carrier writes over
*other* carriers' policies, which matters when the renters policy is somewhere
cheap worth keeping. An independent agent quotes several at once, which is the
entire value on a commoditised product.

**Not through a life or disability adviser.** They don't underwrite property
and casualty, so it becomes a referral to a partner — a middleman on a
commodity — and it opens a broader planning conversation nobody asked for.

## Closing the review

1. **Lead with the price per million.** "$225–450/yr for $2M" is the sentence
   that gets acted on, and it usually costs less than the physical-damage
   coverage a household is already carrying on an old car.
2. **State the sequence as a call script** — what to raise, in what order, in
   which call. The gate makes this a process problem, not just an analysis.
3. **Ask for excess UM/UIM explicitly**, and record the answer.
4. **Name the revisit triggers** — a material change in assets or income, a
   new resident driver, a rental property, a board seat, a move.

## Deliberately out of scope

The underlying limits themselves (`auto-insurance-review`,
`renters-homeowners-review` own those), professional liability, commercial
general liability, and directors-and-officers cover. Those are different
products, not larger versions of this one.

---

*Not financial, tax, or legal advice. Cost figures are market ranges, not
quotes. Verify against your actual policies and a carrier.*
