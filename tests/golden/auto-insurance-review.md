# Auto insurance review

Facts as of **<DATE>** · jurisdiction **TX**

## Capacity

| | |
|---|---|
| Liquid assets | $85,000 |
| Attachable by a judgment (liquid + illiquid) | $113,000 |
| Household gross income | $180,000 |
| Liquid buffer | 10.6 months of spending |

Retirement accounts are excluded from the attachable figure — ERISA plans are broadly creditor-protected and IRA protection is set by state. Absorbability below is measured against **liquid** assets only, never net worth.

## 1 · Liability — do this first

Exposure: **$473,000** — $113,000 of reachable assets plus 2 years of gross income as a garnishment proxy. A judgment does not stop at your balance sheet.

- ⚠️ Bodily injury $100,000/$300,000 → $250,000/$500,000.
- ⚠️ Property damage $50,000 → $100,000. One late-model SUV plus a guardrail clears $100K.
- ⚠️ UM/UIM bodily injury $30,000/$60,000 → $250,000/$500,000. This is the only coverage that pays your own family for lost earning capacity and permanent impairment when the at-fault driver has nothing. Health insurance pays medical bills and nothing else.
- TX: UM/UIM may not exceed the policy's BI limits — raise BI first, then UM/UIM to match.

Umbrella attachment: underlying limits of $250,000/$500,000 BI and $100,000 PD are what carriers require. Currently **does not qualify**. First-cut size: **$1,000,000** — the `umbrella-liability` skill owns that decision.

## 2 · Physical damage — the drop test

### 2019 Subaru Outback

**Keep** comprehensive and collision

| | |
|---|---|
| Stated value | $14,500 (`acv`) |
| Comp + collision premium | $1,100/yr |
| Premium ÷ ACV | **7.6%** (threshold 10%) |
| Uninsured loss if totalled | $14,000 |
| …as a share of liquid assets | **16.5%** |
| Expected annual recovery | $208–$485 *(estimate)* |
| Implied load | 2.3×–5.3× (typical 1.4–1.7×) |

- Premium is 7.6% of ACV, under the 10% threshold, and the loss (16.5% of liquid) is material. Fairly priced protection against a loss worth transferring.

### 2012 Toyota Corolla

**Drop collision.** Comprehensive decided separately

| | |
|---|---|
| Stated value | $4,200 (`instant_offer`) |
| Implied ACV | $4,941–$5,600 |
| Comp + collision premium | $640/yr |
| Premium ÷ ACV | **11.4%–13.0%** (threshold 10%) |
| Uninsured loss if totalled | $4,441–$5,100 |
| …as a share of liquid assets | **5.2%–6.0%** |
| Expected annual recovery | $193–$451 *(estimate)* |
| Implied load | 1.4×–3.3× (typical 1.4–1.7×) |

> **`instant_offer` is not ACV.** A carrier settles a total loss at Actual Cash Value, so the ratio is a band, not a number — and the basis uncertainty does not change the answer.

- Premium is 11.4%–13.0% of ACV, above the 10% threshold.
- The loss is survivable at 5.2%–6.0% of liquid assets. Drop the expensive half.
- Comprehensive is a separate decision and usually the keeper: it covers theft, fire, hail, and glass — none of them your fault, none avoidable by driving well. Standalone it is $190/yr — 3.4%–3.8% of ACV, still under the threshold, so keep it.

## 3 · Coverages that change when collision comes off

- Add UM Property Damage — up to the PD limit, $250 deductible.
- UMPD carries a $250 deductible and pays only when the at-fault driver is identified.

- Medical Payments declined. Defensible where health coverage is strong: the PPO covers your family, BI liability covers passengers you injure, UM/UIM covers uninsured drivers.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/auto.py` with their reasons; every figure above is derived, not restated. Verify against your actual policy.*
