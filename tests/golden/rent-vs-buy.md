# Rent vs buy

**Renting is cheaper** over 7 years, by **$146,789**.

|  |  |
|---|---|
| Price | $520,000 |
| Down payment | $104,000 |
| Loan | $416,000 |
| Monthly payment (P&I) | $2,616 |
| Current rent | $2,400/mo |

## Wealth given up over 7 years

Both sides are carried forward to the horizon at the investment return, so the comparison is like-for-like on timing. Owning front-loads cost and back-loads benefit; summing undiscounted cash flows would flatter it.

| Line | Amount |
|---|---|
| Mortgage interest paid | $179,539 |
| Property tax | $67,340 |
| Insurance | $12,600 |
| Maintenance | $36,400 |
| HOA | $35,280 |
| Transaction costs (2% in, 6% out) | $48,772 |
| **All outflows, compounded to the horizon** | **$642,787** |
| Less terminal equity (sale − costs − balance) | −$225,345 |
| **Net cost of owning** | **$417,442** |
| **Net cost of renting** | **$270,653** |

The first six lines are undiscounted totals, shown so the components are checkable. The compounded figure is what the comparison uses. Principal repaid ($40,183) is not a cost — it returns through terminal equity.

## Break-even

**Buying does not break even within 40 years** at these assumptions.

- **Do not compare the mortgage payment to the rent.** The payment is not the cost of owning. Property tax, insurance, maintenance and the cost of getting in and out are most of it, and none of them appears on a mortgage statement.

- Principal repayment ($40,183 over 7 years) is **excluded from the cost of owning** — it converts cash into equity rather than spending it. Counting it as a cost is the most common error in the other direction.

- **Both sides are carried forward to the horizon at 7%**, not summed undiscounted. A dollar spent on housing in year 3 is a dollar that could have been invested for the rest of the term. Owning front-loads cost and back-loads benefit, so ignoring timing flatters buying — which is the error most published comparisons make, on top of omitting the down payment's opportunity cost entirely.

- **Buying does not break even within 40 years** at these assumptions. That normally means the price-to-rent ratio is very high, or the assumed appreciation is very low — check both before treating it as settled.

- **Everything here is nominal**, because the mortgage rate is. Appreciation 3.0% against rent growth 3.0% is **+0.0% real** — the deliberate default, so no forecast is baked in.

- Selling costs alone are about 6% of price. That single line is why short holding periods lose, and it does not shrink if the market moves against you.

- **The HOA is not a substitute for maintenance — it is a substitute for mortgage.** $420/month is fixed, unavoidable and perpetual, which makes it debt service in everything but name. At 6.45% over 30 years and the 80% loan-to-value actually being used, $5,040 a year carries **$66,796 of loan**, which at that loan-to-value is **$83,495 of price** — 16% of the asking price. A $520,000 property with these dues costs what a **$603,495** property without them costs. That is the comparison to make against listings that carry no dues, and no amount of reading the outflows table surfaces it.

- **And it is worse debt than a mortgage.** Principal and interest are fixed and gone at the end of the term; dues inflate and never end. At 3% growth, $420/month is about **$759/month in 20 years** — typically arriving around the time earned income stops. The association also sets the number, and a special assessment is not optional.

- Over 7 years the dues total $35,280. Unlike maintenance, none of it is deferrable, and unlike principal, none of it comes back on sale.

## What this does not model

Mortgage interest and property tax deductibility, which depend on whether the household itemises; the risk of being unable to move for work; the value of security of tenure; and any view on house prices. The appreciation input is a dial, not a forecast — move it and see how much of the conclusion depends on it.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/housing.py` with their reasons; every figure above is derived, not restated.*
