---
name: india-tax-return
description: Prepare an Indian income-tax return workpaper (ITR-2 shape) for one financial year for an individual with Indian-source income, usually a non-resident Indian living abroad. Determines residential status from day counts, computes NRO/NRE interest, house property, capital gains and insurance maturities, compares the new and old regimes, applies surcharge, cess and TDS credits, says whether filing is mandatory and gives the U.S. foreign-tax-credit hand-off in USD. Use when asked to prepare or check an Indian tax return, decide new versus old regime, work out an India refund, or find the Indian tax and income figures for Form 1116. Reads figures from a local facts file; it does not e-file.
requires:
  - household.members
  - india_tax_return.financial_year
  - india_tax_return.taxpayer.member
  - india_tax_return.taxpayer.days_in_india_this_fy
  - india_tax_return.usd_inr_rate
---

# India Tax Return Workpaper

## The idea

**Residential status decides what India may tax; the regime decides how much.**
A non-resident is taxed only on India-source income, keeps NRE/FCNR interest
exempt, gets no s.87A rebate, and cannot set the unused basic exemption against
special-rate capital gains. Status comes from day counts, so it is determined
first and every other figure follows from it.

## The decision rules

| Question | Rule applied |
|---|---|
| Resident? | 182+ days; or 60+ days and 365+ in the four prior years. For an Indian citizen or person of Indian origin on a visit the 60 becomes 182, or 120 if Indian income exceeds ₹15 lakh. A citizen with Indian income above ₹15 lakh who is not liable to tax elsewhere is deemed resident. |
| Ordinarily resident? | Not if non-resident in 9 of the prior 10 years, or 729 days or fewer in the prior 7; the 120-day and deemed-resident routes are always RNOR. |
| Which regime? | Both are computed; the lower is recommended. Without business income the choice is per year, but the old regime needs a return filed by the due date — after it, only the new regime is applied, even if the old is requested. |
| Refund or payable? | Tax plus s.234A/B/C interest and s.234F fee, less TDS, advance and self-assessment tax. Any unrecorded TDS, advance or self-assessment tax leaves the balance "cannot be determined". |
| Must file? | Income before Chapter VI-A and s.54/54EC exemptions above the basic exemption, or TDS of ₹25,000 or more (₹50,000 for a resident senior). A refund is noted as a reason to file, not a mandate. This year's capital losses carry forward only on a timely return. |

## Rules the report applies

- **Interest:** NRO taxable at slab. NRE exempt by FEMA status
  (`fema_resident_outside_india`; assumed for a non-resident and flagged, required
  for a resident); FCNR exempt unless ordinarily resident. s.80TTA (₹10,000, old
  regime) for savings interest; s.80TTB (₹50,000) for resident seniors on all
  deposit interest.
- **House property:** let-out or deemed let-out at rent less municipal tax, less
  30%, less interest. Up to two self-occupied homes at nil; their interest is
  capped at ₹2 lakh in the old regime and disallowed in the new. A
  house-property loss offsets other heads only in the old regime, up to ₹2 lakh;
  the rest carries forward. Three or more self-occupied homes stop the report.
- **Capital gains (transfers after 23 July 2024):** listed equity and equity
  funds with STT — 20% short term, 12.5% above ₹1.25 lakh long term (12
  months). Debt funds bought on or after 1 April 2023 — slab, always. Property,
  unlisted shares, gold — 12.5% long term after 24 months, no indexation for a
  non-resident (a resident's indexation option is flagged, not computed).
  s.54 and s.54EC (₹50 lakh per year across all sales) reduce long-term property
  gains. Missing `stt_paid` on listed equity stops the report.
- **Loss set-off:** short-term losses offset any gain, long-term losses only
  long-term gains (s.70), then house-property loss across heads (s.71, old
  regime, ₹2 lakh), then brought-forward losses. Within those rules the order is
  the one that minimises tax; the report says that freedom rests on tribunal
  rulings rather than statutory text.
- **Insurance:** s.10(10D) — ULIPs issued from 1 Feb 2021 with aggregate premium
  above ₹2.5 lakh are capital gains (s.45(1B)); other policies issued from 1 Apr
  2023 with aggregate premium above ₹5 lakh are other income; a premium above
  10% (20% before April 2012) of sum assured breaks the exemption and makes any
  policy, ULIP included, other income, floored at nil; death benefits are always
  exempt.
- **Tax:** slab tax, special-rate tax, rebate (residents only, with marginal
  relief above ₹12 lakh in the new regime), surcharge (special-rate gains and
  dividends capped at 15%; new regime capped at 25%) with marginal relief, then
  4% cess. Rounded to ₹10.
- **Dates and years:** sales and maturities must fall inside the financial year;
  a year before the earliest shipped table is refused, a later one is projected.
- **U.S. hand-off:** Indian taxable income and Indian tax finally borne,
  converted at the supplied `usd_inr_rate` with its stated basis. Everything is
  passive category here. Indian funds are PFICs (`pfic-divest-or-comply`); FBAR
  and Form 8938 are separate (`foreign-reporting-audit`).

## What it will not do

Refuses business or professional income (ITR-3), Indian salary, virtual digital
assets, clubbing, a resident's foreign income and s.54F/54B claims. Flags
without computing agricultural-income partial integration, Schedule FA, the
resident indexation option, Rule 115A currency computation for unlisted shares,
and DTAA treaty-rate claims (Form 10F / TRC). It does not fetch exchange rates
and it does not file.

## Weakest input

**The day counts.** A few days in India moves the return between NR, RNOR and
ROR, and those counts come from a travel log rather than a statement. The second
weakest is TDS, which must be reconciled to Form 26AS and AIS before filing.

## Closing

FY 2025-26 is under the Income-tax Act 1961; FY 2026-27 is a "tax year" under
the Income-tax Act 2025 with renumbered sections. Rate tables are marked
unverified until a human checks them against the primary text.

*Not financial, tax, or legal advice.*
