# Tax planning

Filed returns are the baseline; the current row is a projection. Payments stay separate because a refund or balance due says when tax was paid, not how much tax the household incurred.

## Filed-return history

| Year | Filing / state | AGI | Taxable | Federal | State tax | Combined | Effective | Payment result |
|---|---|---|---|---|---|---|---|---|
| 2023 | married_joint / TX | $145,000 | $115,000 | $19,000 | $0 | $19,000 | 13.1% | $500 refund |
| 2024 | married_joint / TX | $163,000 | $132,000 | $23,800 | $0 | $23,800 | 14.6% | $1,300 due |
| 2025 | married_joint / TX | $172,000 | $141,000 | $26,000 | $0 | $26,000 | 15.1% | $2,000 due |

Across the recorded period, nominal AGI changed by $27,000 and the combined effective rate moved up by 2.0%. The income-weighted historical rate is 14.3%.
That movement is diagnostic, not causal: it does not identify a deduction, law change, or income-mix effect by itself.

## Current projection

| Year | Filing / state | AGI | Taxable | Combined tax | Effective | Payments | Projected result |
|---|---|---|---|---|---|---|---|
| 2026 | married_joint / TX | $155,500 | $125,500 | $24,000 | 15.4% | $22,000 | $2,000 due |

- 2 historical year(s) ended with tax due. Withholding and estimates change payment timing and penalties, not the underlying tax.

- The current projection is short $2,000 against recorded payments; reserve or adjust payments separately from tax-reduction decisions.

## Tax-reduction candidates

| Move | Amount | Current-year tax | Possible later benefit | Confidence | Detail |
|---|---|---|---|---|---|
| Fill available HSA contribution room | $8,750 | **$2,100 lower** | not separately sized | estimated | `hsa-review` |
| Donate intended gifts with appreciated long-term lots | $9,000 | **$1,384 lower** | not separately sized | estimated | `charitable-giving-strategy` |
| Review taxable loss lots before year end | $3,082 | **$564 lower** | not separately sized | estimated | `wash-sale-policy` |
| Bunch 5 years of planned giving | $45,000 | not sized | $6,480 | estimated | `charitable-giving-strategy` |

### Fill available HSA contribution room

8,750 of recorded HSA room remains for 2026.

Tradeoffs:
- Requires current cash and continued HSA eligibility.
- Non-medical withdrawals do not receive the full tax advantage.
- State and payroll-tax effects are not included.

### Donate intended gifts with appreciated long-term lots

Giving the recorded long-term lots in kind avoids their embedded gain without changing the charitable deduction.

Tradeoffs:
- The gift is irrevocable; charitable intent sets its size.
- Confirm holding period, basis, recipient eligibility, and AGI deduction limits before transferring.
- Transfer shares directly; selling first realizes the gain.

### Review taxable loss lots before year end

Recorded taxable lots contain 3,082 of unrealized losses across PFE.

Tradeoffs:
- A harvested loss is tax timing, not an economic profit; future gains and carryforwards determine when it is used.
- Avoid replacement purchases across every household account for the wash-sale window, including retirement and spouse accounts.
- Use the recorded usable amount and marginal rate from tax software; this planner does not perform capital-gain netting.

### Bunch 5 years of planned giving

Bunching creates 27,000 more deductions and an estimated 6,480 federal benefit over the 5-year window.

Tradeoffs:
- Requires prefunding several years of irrevocable gifts.
- A donor-advised fund adds fees and administration.
- AGI limits can defer or expire part of a large deduction.

**Do not add the opportunity figures together.** Contribution choices compete for cash; charitable techniques can overlap; losses depend on return-level netting; and a conversion deliberately moves tax between years. Reproject the return after selecting a combination.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/tax_planning.py` with their reasons; every figure above is derived, not restated. This is a planning screen, not a prepared return. Verify current law, eligibility, and filing treatment before acting.*
