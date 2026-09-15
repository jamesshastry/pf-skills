# Employer match audit

⚠️ **Up to $3,375 of employer match is at risk this year.**

|  |  |
|---|---|
| Match formula | `percent_of_pay_per_period` |
| Pay periods | 24 |
| Periods with a deferral | **9** |
| §402(g) ceiling incl. catch-up | $24,500 |
| Match earned | $2,025 |
| Match available | $5,400 |
| **Forfeited** | **$3,375** |
| Plan trues up | **unknown** |

- ⚠️ **Up to $3,375 of match at risk this year.** A 40% deferral rate on $180,000 reaches the §402(g) ceiling of $24,500 in about 9 of 24 pay periods. The match is calculated per period, so the remaining 15 periods earn nothing — **and whether the plan trues up is unknown**.

- Two fixes, and the first is usually better: **lower the deferral rate so contributions spread across the whole year**, or get confirmation in writing that the plan trues up. This is invisible on every statement — the balance looks fine because the deferrals arrived; only the match is missing.

## Why the formula shape decides this

| Formula | Front-loading |
|---|---|
| `percent_of_pay_per_period` | **Costly.** Match accrues only in periods you contribute. Stop in month three and the rest of the year earns nothing. |
| `dollar_for_dollar_annual_cap` | **Free.** The cap is annual, so reaching it sooner changes nothing. |

Advice that skips this distinction is wrong about half the time, in the same confident tone either way. If the formula is not recorded, the question to ask is: *"is the match calculated per pay period or on annual compensation, and does the plan true up after year end?"*

**This error is invisible on every statement.** The balance looks correct because the deferrals arrived on schedule; only the match is missing, and nothing flags it.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/contributions.py` with their reasons; every figure above is derived, not restated. Statutory limits change annually — verify against irs.gov.*
