---
name: pfic-divest-or-comply
description: Decide whether to keep a non-US mutual fund, ETF or unit trust and pay the annual PFIC compliance cost, or sell it — by computing the §1291 excess-distribution charge including the compound interest and comparing it against Form 8621 preparation for as long as the fund is held. Use when asked about PFICs, Form 8621, foreign mutual funds, Indian or UK or Australian funds held by a US person, QEF or mark-to-market elections, or whether to sell an offshore fund. Reads figures from a local facts file.
requires:
  - household.members
---

# PFIC: divest or comply

## The decision is divest-or-comply, not which election

The natural framing is §1291 versus QEF versus mark-to-market. That is the right
*analysis* and the wrong *decision*, because for a retail holder the answer is
usually neither:

- **QEF (§1295) requires a PFIC Annual Information Statement** from the fund.
  Most non-US retail funds do not issue one — their US investors are a rounding
  error and the statement exists solely for US tax purposes. This is the fund's
  decision, not the holder's. There is nothing to elect.
- **Mark-to-market (§1296) requires marketable stock** — regularly traded on a
  qualified exchange. An open-ended fund transacting at NAV is not that, however
  liquid it feels.

Both are frequently unavailable, which leaves **§1291 by default** — and §1291
by default is the case for selling. So the regime comparison is an **input**
here. The output is the ongoing annual compliance cost against the one-off cost
of getting out.

## The §1291 charge, and why it is computed rather than warned about

An excess distribution — or the whole gain on disposition — is allocated
**pro-rata across every day of the holding period**. Each prior year's slice is
taxed at **that year's highest marginal rate**, whatever bracket the holder was
actually in, then carries compound interest at the IRS underpayment rate from
that year's return due date to this one's.

On a long hold **the interest can exceed the tax**, and the effective rate can
pass 100% of the gain. Nobody intuits this, which is exactly why it is worth
computing rather than describing. It also inverts the usual instinct: a
long-held PFIC is the expensive case, not the safe one.

## `null` is not `false`

A fund whose PFIC Annual Information Statement nobody has asked about is
recorded as unknown, and the unknown is a finding. Asking the administrator is
one email, the answer is usually no, and **a documented no is what supports the
decision to sell.** Assuming the answer in either direction is the error.

## The rate series comes from the facts file, and the skill refuses without it

`assumptions.pfic_rates.top_marginal_rate` and
`assumptions.pfic_rates.underpayment_rate` are **asked for, never encoded.**

A fund bought in 2005 needs eighty-odd quarterly rates. A list that long
transcribed from memory is a list that long of chances to silently corrupt a
dollar figure someone acts on. Same principle as
`assumptions.cash_benchmark_apr` — and it forces contact with the authoritative
source, which is where anyone should be before acting on a §1291 number.

The refusal is **wholesale**. A charge computed across only the years the
series happens to cover is not a smaller charge, it is the same charge reported
too low, with nothing in the output to say so. When rates are missing the report
gives the **shape**: holding period, the allocation, which regime applies, and
what drives the charge — and names every missing rate exactly.

## The asymmetry that settles it

Every year of waiting makes the exit charge larger. The allocation lengthens
and each new slice compounds. **There is no year in which selling gets
cheaper**, which is why the breakeven figure understates the case for leaving.

The corollary is the good news in the report: a PFIC currently **below basis**
is the cheapest one ever to leave. No gain, no excess distribution, no charge —
and the cost of staying is unchanged. If a position is underwater, that is the
moment.

## What it will not do

- **No filing position.** It sizes a problem. Which form, on what basis, in
  which tax year, and in what order — a cross-border CPA or EA.
- **No exit sequencing.** Selling a PFIC is the event that triggers the charge.
  The order of operations within a tax year is a preparer's call.
- **No thresholds.** FBAR, FATCA and the Form 8621 de minimis waiver live in
  `foreign-reporting-audit`.
- **Federal only, nominal dollars.** No state tax, no NIIT layer, no foreign tax
  credit. Interest is compounded quarterly from the supplied quarterly rates;
  §6622 compounds daily, so the figure runs slightly low.

## The weakest input

The **acquisition date**, and then the **basis**. The holding period drives the
interest, which on a long hold is most of the charge — so a date remembered
rather than looked up moves the answer more than any rate in the series does.
Where several funds are held, the charge is computed off the **earliest**
acquisition rather than an average, because averaging flatters it.

## Closing

1. **The regime first** — is any election actually available, or is this §1291
   by default.
2. **The charge**, with tax and interest shown separately. The split is the
   finding.
3. **The breakeven**, then the asymmetry: waiting makes it worse.
4. **One email to the fund administrator** about the Annual Information
   Statement, if that is still unknown.
5. **A cross-border preparer before any sale.**

---

*Not financial, tax, or legal advice. The rate series is yours to supply and
yours to verify against the IRS tables.*
