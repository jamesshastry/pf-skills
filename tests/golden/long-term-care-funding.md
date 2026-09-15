# Long-term care funding

**Transfer the tail.**

|  |  |
|---|---|
| Annual care cost (today's money) | $110,000 |
| 3-year episode | $330,000 |
| **5-year episode** | **$550,000** |
| Investable assets (liquid + age-restricted) | $395,000 |
| Tail as a share of investable | 139% |
| Portfolio after the tail case | **exhausted** |
| Supports at 4.0% | $0 |
| **Survivor shortfall** | **$72,000/yr** |

- At $110,000/yr, a 3-year episode costs **$330,000** and a 5-year episode **$550,000**, in today's money. The decision is about the tail, not the central case: most episodes are shorter than the mean and the mean is dragged up by the long ones. Insurance is for the long ones.

- The 5-year figure is **139% of $395,000 investable assets** (the 3-year figure is 84%). The absorb bands are the same ones `auto-insurance-review` uses — under 5% self-insure, over 25% transfer — but measured against investable rather than liquid assets, because a care episode draws on the retirement portfolio over years rather than settling in weeks.

- ⚠️ **The 5-year case costs more than the entire investable portfolio** ($550,000 against $395,000). There is no residual to run a survivor test against — the portfolio is gone before the episode ends, and what follows is a Medicaid spend-down rather than a funding plan. At this ratio the question is not whether to insure but whether cover can be obtained and afforded.

- ⚠️ **This is the test that decides it, and it fails.** After a 5-year episode the portfolio is $0, supporting $0/yr at 4.0% — against a survivor needing $72,000. A **$72,000/yr shortfall for the rest of the survivor's life.** The risk being insured is not the care bill. It is impoverishing the spouse who did not need care.

- **Verdict: transfer at least the tail.** The exposure is past the line this repository uses for every other insurance decision. Note what transferring means here: cover the *duration* tail, not the first dollar. A policy with a long elimination period and a long benefit period insures the part that cannot be absorbed and is far cheaper than one that pays from day one — which is the opposite of how these are usually sold.

- A policy of type `hybrid` is in force. Check three things on it: whether the benefit is **inflation-adjusted** (a fixed daily benefit written years ago buys a fraction of what it did), the **elimination period** against liquid assets, and the **benefit period** — the tail is what is being insured, so a three-year benefit period leaves the exact scenario that motivated the purchase uncovered.

- **Traditional long-term care insurance has a bad history and it is not a footnote.** Carriers priced early blocks assuming policyholders would lapse at normal rates and interest rates would stay high. Neither happened. In-force blocks have since carried repeated rate increases, approved by regulators, in some cases cumulatively large enough to force holders to reduce benefits or drop cover — after paying premiums for decades, at the age when the policy was about to matter. **The premium on a traditional policy is not guaranteed, and the increase arrives when it is hardest to absorb.** Anyone buying one should price a scenario in which it goes up substantially and ask whether they would still pay it.

- **Hybrid life-LTC policies answer that specific objection and introduce different ones.** The premium is usually guaranteed and an unused benefit pays as a death benefit, so the money is not lost — which is the real reason people buy them. Against that: far less care benefit per premium dollar, a large sum tied up in a low-return contract, and a surrender value that makes the illustration look better than the internal return actually is. **Do not compare them on premium.** Compare maximum benefit per dollar and ask what the committed capital would otherwise have earned — the same arithmetic `life-insurance-review` applies to cash-value policies.

- **Self-insuring is a real answer, not a failure to decide** — but only if it is funded and named. An unlabelled 'the portfolio will cover it' is how the survivor ends up short. If the verdict above is self-insure, the follow-through is an earmarked share of the portfolio and a written statement of who arranges care.

- **Medicaid is the actual backstop for most households, and it is means-tested.** It pays for custodial care only after a spend-down, with a lookback on transfers and state-specific community-spouse protections and estate recovery. Those rules are state law and are **not** modelled here — this skill will not tell you whether a transfer is safe, and anyone considering one needs an elder-law attorney in their own state.

- **Medicare does not pay for long-term care.** It covers limited skilled nursing after a qualifying hospital stay, not custodial care, which is what the multi-year episode above consists of. This is the most widespread single misconception in the subject and it is the reason households arrive at 80 with no plan.

- Cost basis dated <DATE>. **Care cost inflation has run above general inflation**, so a figure in today's money understates an episode thirty years out — this report is real, today-money throughout, and does not project that excess.

## The three options, compared on the right axis

|  | Self-insure | Traditional LTC | Hybrid life-LTC |
|---|---|---|---|
| Premium certainty | n/a | **not guaranteed — the known defect** | usually guaranteed |
| Care benefit per dollar | 1:1 with assets | highest of the three | lowest of the three |
| If care is never needed | assets retained | premiums gone | death benefit paid |
| Capital committed | none upfront | annual premium | large single or limited premium |
| Fails when | the tail runs long | a rate increase arrives at 80 | the opportunity cost compounds |

**Do not compare a hybrid to a traditional policy on premium.** Compare maximum care benefit per dollar committed, and price what the committed capital would otherwise have earned — the same arithmetic `life-insurance-review` applies to cash-value policies.

## Before acting

- **Ask for the carrier's rate-increase history on in-force business**, not the illustration. A carrier that has never raised rates on an old block is telling you something; one that has raised them repeatedly is telling you more.
- **Price the increase scenario.** If the premium rose substantially at the age where dropping the policy wastes everything paid in, would you still pay it? If not, the policy is not affordable now.
- **Check inflation protection.** A fixed daily benefit written today buys a fraction of a care day in thirty years, which is when it is needed.
- **Match the benefit period to the tail.** A three-year benefit period leaves uncovered exactly the scenario that justified buying.
- **Underwriting is the real gate.** This decision has a health deadline as well as a cost, the same way `disability-insurance-review` does — it is cheap and available until abruptly it is neither.

## Weakest input

`healthcare.ltc.annual_cost_today` — regional, self-reported, and the figure every dollar above is a multiple of. A national average in a high-cost metro understates it badly, and the error runs in the direction of doing nothing.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/healthcare.py` with their reasons; every figure above is derived, not restated. Medicaid spend-down, transfer lookback, community-spouse protection and estate recovery are state law and are not modelled — this report will not tell you whether a transfer is safe.*
