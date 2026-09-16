# PFIC: divest or comply

**The decision here is divest or comply, not which election.** QEF needs a PFIC Annual Information Statement most non-US retail funds do not issue, and mark-to-market needs marketable stock on a qualified exchange. Both are usually unavailable, which leaves §1291 by default — and §1291 by default is the case for selling.

| Holding | Value | Basis | Unrealised gain | Acquired | Regime available |
|---|---|---|---|---|---|
| icici_india_equity | $61,000 | $22,000 | $39,000 | <DATE> | §1291 default |
| overseas_balanced_fund | $12,000 | $12,500 | ($500) | <DATE> | §1291 default |

**2 Form 8621(s) a year** — the form is per fund, per year, and it does not stop while the fund is held.

## The §1291 exit charge

**$20,795 on $38,500 of gain** — an effective **54.0%**. Tax $14,397, interest $6,398.

Allocated pro-rata across 11 tax year(s), 10.2 years held.

| Year | Days | Slice | Top rate that year | Tax | Interest |
|---|---|---|---|---|---|
| 2016 | 200 | $2,065 | 40% | $818 | $819 |
| 2017 | 365 | $3,768 | 40% | $1,492 | $1,294 |
| 2018 | 365 | $3,768 | 37% | $1,394 | $1,035 |
| 2019 | 365 | $3,768 | 37% | $1,394 | $872 |
| 2020 | 366 | $3,779 | 37% | $1,398 | $722 |
| 2021 | 365 | $3,768 | 37% | $1,394 | $578 |
| 2022 | 365 | $3,768 | 37% | $1,394 | $446 |
| 2023 | 365 | $3,768 | 37% | $1,394 | $323 |
| 2024 | 366 | $3,779 | 37% | $1,398 | $208 |
| 2025 | 365 | $3,768 | 37% | $1,394 | $100 |
| 2026 | 242 | $2,499 | 37% | $924 | current year — no interest |

- **$20,795 on $38,500** — an effective 54.0%, of which $14,397 is tax and $6,398 is interest. The gain was allocated across 11 tax year(s) and each prior year's slice taxed at **that year's highest marginal rate**, not the holder's bracket, then compounded forward at the underpayment rate.

- Held 10 years. Past roughly 10 the interest component usually overtakes the tax; it has not here, which is worth confirming against the underpayment series you supplied before relying on it.

- Interest is compounded quarterly from the quarterly rates supplied. §6622 compounds daily, so this runs slightly low. It is an estimate of the size of a problem, not a figure to enter on a Form 8621.

## Regime availability, holding by holding

**icici_india_equity** — §1291 default

- **No PFIC Annual Information Statement, so QEF is unavailable.** This is the common case and it is the fund's decision, not the holder's — there is nothing to elect.
- **Not marketable stock on a qualified exchange, so §1296 is unavailable.**

**overseas_balanced_fund** — §1291 default

- **QEF availability unknown.** A QEF election needs a PFIC Annual Information Statement from the fund; most non-US retail funds do not issue one, because their US investors are a rounding error. Ask the administrator in writing — the answer is usually no, and a documented no is what supports the decision to sell.
- **Mark-to-market availability unknown.** §1296 needs *marketable stock* — regularly traded on a qualified exchange. An open-ended fund that transacts at NAV is generally not that, whatever its liquidity feels like.

## The comparison

- **$800/yr to stay compliant** — 2 Form 8621(s) at $400 each. Form 8621 is per fund, per year, and it does not stop while the fund is held.

- **Breakeven: 26.0 years.** Exiting today costs $20,795; staying costs $800/yr. Holding longer than 26.0 years costs more than leaving now — and this understates the case for leaving, because **the exit charge itself grows every year you wait.** The allocation lengthens and each new slice compounds. There is no year in which selling gets cheaper.

- **The rate differential is the whole penalty.** The same gain in a US-domiciled fund would have been long-term capital gain: $5,775 at 15%, against $20,795 under §1291 — $15,020 more for holding the same exposure through the wrong wrapper.

- **No election is available on any holding, so §1291 applies by default** — and §1291 by default is the case for selling. There is no version of holding these that gets cheaper with time. A US-domiciled fund usually gives the same exposure without the wrapper that causes this.

- **Regime availability is unknown on at least one holding.** `null` is not `false`. Ask the fund administrator whether a PFIC Annual Information Statement is issued — one email, and the answer decides which half of this report applies.

- This is a decision, not a filing position. Everything above ends at a cross-border CPA or EA — including, especially, the exit itself: selling a PFIC is the event that triggers the charge, and the order of operations within a tax year is theirs to set.

## Before acting

- **Email the fund administrator** and ask, in writing, whether a PFIC Annual Information Statement is issued. One email decides which half of this report applies, and a documented *no* is what supports the sale.
- **Get the acquisition dates from the original contract notes**, not from memory. The holding period drives the interest and the interest is most of the charge on a long hold.
- **Do not sell first and ask afterwards.** The sale is the event that triggers the charge; the tax year it lands in is a choice, and it stops being one once the order is placed.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/pfic.py` with their reasons; every figure above is derived, not restated. The rate series comes from your facts file, not from a table in this repository — verify it against the IRS schedules before relying on any figure above.*
