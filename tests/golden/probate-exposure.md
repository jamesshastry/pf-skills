# Probate exposure

**A pour-over will does not avoid probate.** It directs whatever is left into the trust on death — it fixes the *destination*, not the *route*. Anything still titled in an individual name goes through court first and lands in the trust afterwards, having paid for the trip. Households with a drafted trust routinely assume they are covered here and are not.

Jurisdiction: **TX**

## Every account, and where it goes

| Account | Titling | Primary designation | Value | Verdict |
|---|---|---|---|---|
| cash | `joint` | *not applicable* | $40,000 | ✅ avoids |
| brokerage | `individual` | `a2` | $45,000 | ✅ avoids |
| retirement_401k | `individual` | **checked — none named** | $310,000 | 🚫 **probate** |
| college_529 | *not recorded* | `c1` | $28,000 | ✅ avoids |

- **retirement_401k** — Individually titled, and the designation was checked with nobody named. Nothing carries it out of the estate, so it passes under the will.

## What is exposed

**$310,000 across 1 account(s)** will pass under the will and through probate on the recorded facts.

## What that costs

Fees here are whatever is reasonable, usually billed hourly and approved by the court, so no schedule can be applied. That is generally cheaper than a percentage state in the ordinary case and much harder to predict. The number to ask an attorney for is a range, not a rate.

## The spousal shortcut

Whether this state offers an abbreviated procedure for property passing to a surviving spouse has **not been checked**. That is not the same as it having none — ask.

## The cheapest fix, per account

**Not a blanket recommendation.** The right instrument depends on the tax wrapper, and the two rules point in opposite directions: a taxable account belongs in the trust, while a **retirement** account names the spouse directly, because a trust as primary generally forfeits the spousal rollover and forces a roughly ten-year payout. Optimising only for probate would recommend the trust for both and cost a surviving spouse decades of deferral.

**retirement_401k** — Name the spouse (`a2`) as primary, directly

> Retirement accounts are the exception. Naming the trust as primary generally forfeits the spousal rollover and forces a roughly ten-year payout, which costs far more than the probate it avoids. Spouse as primary, and a trust for minor children as contingent if that is the intent.

## What this does not do

- **A trust exists and is recorded as unfunded.** Every account above that is not titled to it is the funding that was never done. See `estate-document-review`.
- It does not check whether a designation is *coherent* — missing contingents, shares that do not total 100%, a minor named directly. That is `beneficiary-audit`, and it is the other half of this.
- It does not decide whether joint titling is appropriate. Adding a joint owner is a completed gift in many cases, exposes the asset to that person's creditors and divorce, and can forfeit a step-up in basis. It avoids probate; that is not the same as being a good idea.
- Probate cost here is ordinary fees only. Extraordinary fees, filing costs, appraisal, bond and the value of the delay are all real and none are in the figure.

**Weakest input:** the `titled_to` field. It is the one thing that decides every verdict above, it is not on any statement, and 0 of 4 account(s) do not have it recorded. A deed or registration says what it says regardless of what anyone remembers signing.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/probate.py` with their reasons; every figure above is derived, not restated.*
