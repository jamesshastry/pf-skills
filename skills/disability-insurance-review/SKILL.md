---
name: disability-insurance-review
description: Review disability insurance against actual spending — converting benefits to a common after-tax basis, checking the occupation definition, the elimination period against the liquid buffer, the benefit period against working life, and flagging rider deadlines that expire. Use when asked whether disability cover is adequate, what a policy actually pays, whether to exercise a Future Increase option, or how group LTD compares to an individual policy. Reads figures from a local facts file.
requires:
  - household.members
  - household.annual_spending
  - household.balance_sheet
  - insurance.disability
---

# Disability insurance review

Disability is more likely than death during working years and is insured far
worse. It is also the harder policy to read: two policies with the same
headline monthly benefit can differ by a factor of two in what they actually
pay.

## Compare after tax or don't compare at all

**Who paid the premium decides whether the benefit is taxed.**

- Individual policy, after-tax premiums → **tax-free** benefit
- Employer-paid group policy, or premiums paid pre-tax → **taxable** benefit

A $6,500/month group benefit and a $6,500/month individual benefit are not the
same coverage. The report converts everything to a spendable figure before
comparing anything, using an assumed marginal rate that is labelled an estimate
wherever it appears.

This single distinction is the most commonly missed thing in the whole line.

## The four terms that matter more than the benefit amount

**Occupation definition.** *Own occupation* pays if you cannot do your own job,
even if you work elsewhere. *Modified own occupation* pays only if you also are
not working elsewhere. *Any occupation* pays only if you cannot do any job you
are suited to — much harder to claim than people assume. If the definition
isn't stated, the report says to go and find it, because it changes the value
of the cover more than the benefit amount does.

**Elimination period**, checked against the liquid buffer that has to bridge
it. A benefit that starts after the money runs out arrives too late. If the
buffer comfortably covers it, the report says so — lengthening the elimination
period is usually the cheapest way to reduce this premium.

**Benefit period**, checked against working life. A ten-year benefit taken at
50 stops at 60, leaving years unfunded with no earnings and no further
retirement contributions. This is a structural gap, not a mispricing, and it
is easy to miss because the policy looks generous.

**Cost-of-living rider.** A level benefit over a twenty-year claim erodes
steadily.

## Findings that expire

This skill is the reason the schema has a deadline concept at all.

**Future Increase / Future Purchase options let you raise cover without further
medical underwriting** — and the window closes, typically somewhere in the
early fifties. What's being bought is insurability, which cannot be purchased
later at any price once health changes.

The report renders these as a dated table with days remaining and an urgency
band. Three cases, three different messages:

| State | What to say |
|---|---|
| Date recorded, in future | Days remaining, and whether income has grown enough to justify exercising |
| Date recorded, passed | Any increase now needs fresh underwriting |
| Rider present, no date | **Go and find the date.** The rider is worthless unexercised and unknown |

Because these expire, tell the user to re-run before acting on anything marked
urgent. A stale recommendation here is worse than none — they believe the
option is still open.

## Group LTD is not a substitute

It ends with the job, it's usually taxable, and it typically caps at a
percentage of **base salary** — excluding bonus and equity, which for variable
compensation can be most of the income. It stacks with an individual policy
subject to combined issue limits, so it's worth knowing about, but it does not
replace one.

## SSDI is an overlay, not cover

Social Security Disability Insurance may pay alongside a private benefit — or a
group policy may subtract it dollar-for-dollar through an offset clause.
Either way it changes what arrives, and the report treats it as an overlay
rather than cover: where the statement figure
(`social_security.disability_monthly`) is on file it is named beside the
policies, with a pointer to check the offset clause in the plan documents;
where it is not, the report says the gap treats SSDI as zero, which is a
missing input rather than a finding. It is never estimated and never netted
out silently.

## The ceiling

Carriers won't insure the whole income. When the gap sits above roughly 70% of
gross, the report says so: that gap may not be purchasable at all, and closing
it means reducing required spending rather than buying more cover.

## Closing

1. **After-tax cover against monthly spending** — one comparison, correctly
   based.
2. **The definition and the benefit period**, which are where the surprises
   live.
3. **Any dated finding, with its date**, and a note to re-run before acting.
4. **Whether employer group LTD exists** — if it isn't in the facts file, ask.

---

*Not financial, tax, or legal advice. Tax treatment depends on how premiums are
paid; verify with your plan documents and a tax professional.*
