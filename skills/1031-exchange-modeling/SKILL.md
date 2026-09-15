---
name: 1031-exchange-modeling
description: Defer or pay? Computes the taxable gain on an investment property sale including depreciation recapture, tests cash boot and mortgage boot against the equal-or-greater-value rule, and dates the 45-day identification and 180-day closing clocks. Use when asked about a 1031 like-kind exchange, selling a rental property, deferring capital gains on real estate, depreciation recapture, a qualified intermediary, boot, or DST replacement property. Reads figures from a local facts file.
requires:
  - real_estate.exchange
---

# 1031 exchange modeling

## The question is defer or pay, and both sides need the same gain

An exchange is not free. It costs intermediary fees, it compresses a property
search into 45 days, and it carries a live risk of paying too much for the
replacement because the clock was running — which is the commonest way an
exchange loses money while succeeding on paper.

So the comparison has to be honest about the tax it avoids. That starts with
computing the gain properly.

## Depreciation recapture is the part people forget

Gain is measured against **adjusted basis**: purchase price plus improvements,
**minus all depreciation taken**. Years of depreciation have been reducing that
basis, so the gain is larger than "sale price minus what I paid" — often much
larger — and the first slice of it is not capital gain at all.

Unrecaptured §1250 gain, equal to the depreciation claimed, is taxed at a
**higher rate than long-term capital gain**. A household that estimates its
exposure at the capital gain rate underestimates it, decides the exchange is
not worth the hassle, and is wrong.

Worse: depreciation is recaptured to the extent **allowed or allowable**.
Skipping the deduction does not avoid the recapture. The basis reduces anyway.

The rates come from the facts file — `assumptions.depreciation_recapture_rate`,
`assumptions.ltcg_rate`, `assumptions.niit_rate`, `assumptions.state_tax_rate`.
Absent them the report shows the **gain composition** and refuses the tax
figure. The composition is the part that changes the decision.

## The clocks are the part that actually fails

**45 calendar days** from closing on the relinquished property to identify
replacement property **in writing to the Qualified Intermediary**. **180
calendar days** to close — or the due date of the return for the year of sale
if that comes first, which it does for a Q4 sale unless the return is extended.

Neither is extendable, neither stops for a holiday or a failed inspection, and
both run from the relinquished closing rather than from when you started
looking. The report dates both from the sale and counts the days remaining
against the facts file's `as_of`.

## Boot: the cash one is obvious, the debt one is not

**Cash boot** is net equity you did not reinvest. Taxable, gain first, and not
offset by taking on more debt.

**Mortgage boot** is the subtle one and it catches careful people. Replacement
debt lower than relinquished debt is **debt relief, and debt relief is income**
— even with no cash changing hands and even if the replacement property costs
more. Injecting outside cash into the exchange offsets it dollar for dollar;
taking on more replacement debt also works. Doing neither produces a tax bill
with no cash arriving to pay it, which is a liquidity event as well as a tax
one.

**The rule of thumb for full deferral: buy equal or greater value, and
reinvest all net equity.** Both halves. The report tests both and says which
one fails.

## Constructive receipt voids the whole thing

The QI must hold the proceeds **continuously**. If the seller ever has the
right to receive, pledge, borrow against or otherwise benefit from the funds —
including money routed briefly through their own account at closing —
constructive receipt invalidates the exchange retroactively.

Engage the QI **before** the relinquished closing. There is no repair after the
fact, and this is a paperwork failure rather than a judgement failure, which is
why it happens to people who understood everything else.

## Identify a backup

A DST interest can be named as a second or third identified property and closed
quickly with no financing contingency. That turns a failed search at day 44
into a partial deferral instead of a full tax bill. It is illiquid, fee-heavy
and passive — a fallback, not a plan.

## What deferral is worth, and how it ends

The report present-values the deferred tax over the holding period you supply,
rather than quoting the gross deferral as a benefit. A dollar of tax postponed
twelve years is worth well under a dollar.

Deferral also has two endings and you should pick one on purpose: a future
taxable sale, where the whole compounded gain lands at once — or a step-up in
basis at death, which eliminates it. An exchange chain is an estate plan
wearing a tax strategy's clothes, and the strategy only completes if the plan
does.

## What it will not do

It does not find replacement property, vet a QI, or handle reverse and
improvement exchanges, related-party rules (§1031(f)), partnership
drop-and-swap structures, or the personal-residence interaction under §121. It
does not compute state clawback where a state taxes deferred gain on a
subsequent out-of-state exchange. It does not file anything — Form 8824 is a
preparer's job.

## Closing

1. **The gain, split into recapture and capital gain.** Lead with the split.
2. **Boot, both kinds**, and which half of the deferral rule fails.
3. **The two dates**, with days remaining.
4. **The QI, engaged before closing.** Then the backup identification.

---

*Not financial, tax, or legal advice. An exchange is unforgiving of paperwork
errors and cannot be repaired afterwards. Use a qualified intermediary and a
preparer.*
