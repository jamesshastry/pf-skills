# Withdrawal sequencing

## The conventional order

| # | Account | Why |
|---|---|---|
| 1 | Taxable brokerage | Gains only are taxed, at long-term rates if held. Spending it first also removes the drag of taxable dividends and lets the sheltered accounts keep compounding untaxed. |
| 2 | Traditional 401(k) / IRA | Fully taxable as ordinary income. Drawing it down before RMDs begin is what keeps the forced distributions from landing in a higher bracket. |
| 3 | Roth | Tax-free and not subject to lifetime RMDs, so it should compound longest. It is also the best asset to leave to heirs. |

- **The default order is a starting point, not the answer.** Strict sequencing leaves low brackets unused in early retirement and then forces high-bracket withdrawals later. The better version blends: spend from taxable while deliberately filling the low brackets with tax-deferred withdrawals or conversions.

- **No Roth balance recorded.** Every dollar of retirement income will be taxable as ordinary income, with no lever to manage the bracket in a given year. That is what makes the conversion window valuable — see `roth-conversion-window`.

- Dates that shape the sequence: penalty-free IRA access at **59.5**, Rule of 55 access to a workplace plan on separation at **55**, Social Security from **62**, RMDs beginning at **75**.

- **Retiring before 59½ needs an access plan, not just a number.** The Rule of 55 (separation in or after the year you turn 55, workplace plan only, not an IRA) and §72(t) substantially equal periodic payments are the usual routes. Rolling a 401(k) to an IRA *forfeits* the Rule of 55 — a common and irreversible mistake.

- **Asset location matters as much as the order.** Bonds and other income-producing assets belong in tax-deferred accounts; the highest expected-return assets belong in the Roth, because that is where growth is never taxed.

## The version that actually works

Strict sequencing is the wrong answer for most households, and it is wrong in a specific way: it leaves the low brackets empty during early retirement, then forces large ordinary-income withdrawals once RMDs begin. The total tax bill is higher even though every individual step looked tax-efficient.

The better rule is **fill brackets, don't drain accounts**:

1. Spend from taxable for cash flow.
2. Each year, compute the headroom to the top of the target bracket.
3. Fill it with tax-deferred withdrawals or Roth conversions.
4. Leave the Roth alone as long as possible.

Unused bracket space does not carry forward. A year spent entirely in the lowest bracket has wasted the headroom above it permanently.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/retirement.py` with their reasons; every figure above is derived, not restated. Bracket management is jurisdiction- and year-specific; this skill gives the structure, not the numbers.*
