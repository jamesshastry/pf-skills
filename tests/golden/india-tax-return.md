# India Tax Return Workpaper

**FY 2025-26** — Income-tax Act, 1961 (AY 2026-27). All amounts in INR on the Indian basis unless marked USD. A workpaper for review; it does not e-file.

## The decision

- **Residential status: Non-resident (NR).** 40 days in India (< 60).
- Only India-source income is taxed; NRE/FCNR interest is exempt; no s.87A rebate; the basic exemption cannot absorb special-rate capital gains.
- The s.10(10D) aggregate-premium tests count every policy you hold, not only those maturing this year; the aggregate here uses only the policies listed.
- **Old regime is lower by ₹4,760** (₹307,450 vs ₹312,210). Without business income the choice is made each year in the return; the old regime is available only in a return filed by the due date (<DATE>) — a belated return is taxed under the new regime (s.115BAC).
- Losses are set off in the order that minimises tax, within what ss.70, 71 and 74 permit (s.70 intra-head first, then s.71 across heads, then brought-forward losses). The taxpayer's freedom to choose that order rests on tribunal rulings (e.g. ITAT, Montgomery Emerging Markets Fund), not on express statutory text.
- **Refund due: ₹291,800.**
- Filing is **mandatory**: income before Chapter VI-A and s.54/54EC exemptions (₹4,781,600) exceeds the basic exemption (₹250,000) — s.139(1); TDS of ₹599,251 is ₹25,000 or more — seventh proviso to s.139(1) (Rule 12AB).
- Rent from a non-resident's let-out property carried no TDS. Tenants paying a non-resident must deduct under s.195; the tax falls due as advance/self-assessment tax instead.

## Income by head

| Head | Item | Income | Taxed as | TDS | Treatment |
|---|---|---|---|---|---|
| interest | NRO savings | ₹18,000 | slab rate | ₹5,616 | taxable at slab |
| interest | NRO fixed deposit | ₹150,000 | slab rate | ₹46,800 | taxable at slab |
| interest | NRE fixed deposit | ₹220,000 | exempt | ₹0 | exempt — s.10(4)(ii), person resident outside India (FEMA) |
| interest | FCNR deposit | ₹60,000 | exempt | ₹0 | exempt — s.10(15)(iv)(fa), non-resident/RNOR |
| capital gains | listed shares | ₹400,000 | LTCG 12.5% above ₹1.25 lakh (s.112A) | ₹34,375 |  |
| capital gains | debt fund | ₹80,000 | STCG at slab | ₹24,960 | s.50AA — deemed short term, slab |
| capital gains | equity fund | −₹60,000 | STCG 20% (s.111A) | ₹0 | short-term loss — set off against any gain |
| capital gains | Nagpur plot | ₹1,900,000 | LTCG 12.5% (s.112) | ₹487,500 | 12.5% without indexation — the 20%-with-indexation option is for residents only; ₹2,000,000 exempt s.54/54EC |
| insurance | growth ULIP | ₹250,000 | LTCG 12.5% above ₹1.25 lakh (s.112A) | ₹0 | not exempt (ULIP issued on/after 1 Feb 2021, aggregate premium ₹300,000 > ₹2.5 lakh) — capital gain s.45(1B) |
| insurance | endowment plan | ₹300,000 | exempt | ₹0 | exempt s.10(10D) |
| house property | Pune flat (let out) | ₹243,600 | slab rate | ₹0 | NAV ₹348,000 less 30% and interest ₹0 |
| house property | family flat (self occupied) | ₹0 | slab rate | ₹0 | nil annual value; interest per regime |

## Regime comparison

|  | New regime | Old regime |
|---|---|---|
| House property (net) | ₹243,600 | ₹43,600 |
| Gross total income | ₹2,981,600 | ₹2,781,600 |
| Chapter VI-A deductions | ₹0 | ₹185,000 |
| **Total income** | **₹2,981,600** | **₹2,596,600** |
| — taxed at slab | ₹491,600 | ₹106,600 |
| Slab tax | ₹4,580 | ₹0 |
| Special-rate tax | ₹295,625 | ₹295,625 |
| Rebate s.87A | ₹0 | ₹0 |
| Surcharge (after marginal relief) | ₹0 | ₹0 |
| Health & education cess 4% | ₹12,008 | ₹11,825 |
| **Tax liability** | **₹312,210** | **₹307,450** |

- *new:* New regime: no deduction for interest on a self-occupied home (₹240,000 disallowed).
- *old:* Self-occupied interest capped at ₹200,000 (₹240,000 paid).
- *old:* Non-resident: the unused basic exemption cannot reduce special-rate gains (provisos to ss.111A/112/112A).

## Credits and result — old regime

|  | Amount |
|---|---|
| Tax liability | ₹307,450 |
| Interest s.234A (late filing) | ₹0 |
| Interest s.234B (advance-tax shortfall) | ₹0 |
| Interest s.234C (deferment, approximate) | ₹0 |
| Late fee s.234F | ₹0 |
| Less TDS (Form 26AS/AIS) | ₹599,251 |
| Less advance tax | ₹0 |
| Less self-assessment tax | ₹0 |
| **Balance (negative = refund)** | **−₹291,800** |


## Filing

- Mandatory: **yes**.
- Due date s.139(1): <DATE>. Belated s.139(4): by <DATE> (late fee; new regime only). Revised s.139(5): by <DATE> — confirm on the e-filing portal.
- A refund of ₹291,800 can only be claimed by filing (optional, but the money is otherwise lost).
- Other seventh-proviso triggers (large deposits, foreign travel, electricity, turnover) are not checked here.
- s.115G relief from filing (NRI with only investment income/LTCG on foreign-exchange assets, fully taxed at source) is not evaluated.

## U.S. hand-off (Form 1116)

Rate: **86.5 INR per USD** — synthetic yearly average for the example.

For `tax_return.foreign` (`country: IN`):

| Category | Indian taxable income (INR) | USD | Indian tax (INR) | USD |
|---|---|---|---|---|
| passive | ₹2,781,600 | $32,157 | ₹307,450 | $3,554 |
| general | ₹0 | $0 | ₹0 | $0 |

By type, losses netted within each type but not across types (the federal return's `foreign.interest`, `foreign.dividends`, `foreign.capital_transactions`, `foreign.rent`):

| Type | INR | USD |
|---|---|---|
| interest | ₹168,000 | $1,942 |
| dividends | ₹0 | $0 |
| capital transactions | ₹2,570,000 | $29,711 |
| rent | ₹43,600 | $504 |
| other | ₹0 | $0 |

**For `federal-tax-return`** — paste into `tax_return.foreign` after re-splitting to the U.S. calendar year (USD, U.S. rules; `null` = unknown, which the federal return treats as a stop or a bound):

```yaml
foreign:
  country: IN
  accounts: true
  interest: 5179
  dividends: 0
  qualified_dividends: 0
  capital_transactions:
  - description: listed shares (India, listed_equity, sold <DATE>)
    proceeds: 13873
    basis: null
    term: long
    wash_sale_disallowed: 0
    basis_reported: false
  - description: Nagpur plot (India, property, sold <DATE>); add ₹100,000 transfer
      expenses to U.S. basis
    proceeds: 104046
    basis: null
    term: long
    wash_sale_disallowed: 0
    basis_reported: false
  rent: 0
  foreign_tax_paid:
    passive: 3554
    general: 0
  reported_on_1099: false
  category: passive
```

- Left out — debt fund: Indian fund units are a PFIC — see `pfic-divest-or-comply`, not capital_transactions.
- Left out — equity fund: Indian fund units are a PFIC — see `pfic-divest-or-comply`, not capital_transactions.
- Left out — growth ULIP: insurance maturity, out of scope for the federal skill (IRC §7702 / PFIC questions).
- Left out — endowment plan: insurance maturity, out of scope for the federal skill (IRC §7702 / PFIC questions).
- Left out — rent of ₹360,000 gross ($4,162): U.S.-taxable, but the federal skill refuses non-zero rent (Schedule E, depreciation, §469) — see `passive-loss-eligibility`; `rent: 0` in the block means not carried here, not none received.

Exempt in India but U.S.-taxable, no Indian tax to credit: ₹2,580,000 ($29,827) — NRE/FCNR interest ₹280,000, s.10(10D) maturity gains ₹300,000, s.54/54EC-sheltered gains ₹2,000,000.

- All income here is passive category (interest, rent, gains, insurance, dividends); general would hold Indian salary or business income, which is out of scope. Passive income taxed in India above the top U.S. rate may be re-categorised as general under the high-taxed income rule — the U.S. return decides.
- The INR tables are on the Indian basis (30% standard deduction on rent, Indian cost). The `tax_return.foreign` block is converted at one supplied rate and covers the Indian financial year (April-March); the U.S. return is calendar-year, so interest and tax must be re-split across two U.S. years, and each sale belongs to the U.S. year of its date. U.S. basis uses the purchase-date rate: it is left null unless `us_basis_usd` is recorded.
- Creditable tax is the Indian liability finally borne (TDS + advance + self-assessment − refund), never the TDS alone; s.234 interest and fees are not tax. India-U.S. DTAA relief-from-double-taxation article (Article 25 in the treaty text — verify) and its resourcing rule decide the credit; not encoded here.
- Income exempt in India — NRE/FCNR interest, s.10(10D) maturity gains (an Indian policy often fails IRC §7702, so the inside build-up is taxable), and gains sheltered by s.54/54EC — is still U.S.-taxable with no Indian tax to credit.
- Indian mutual funds (and ULIPs that hold them) are PFICs for a U.S. person — see `pfic-divest-or-comply`. FBAR and Form 8938 are separate — see `foreign-reporting-audit`.

## Documents to gather

- [ ] Form 26AS, Annual Information Statement (AIS) and Taxpayer Information Summary (TIS) for the year — reconcile every TDS figure below against them
- [ ] Passport entry/exit stamps or travel log for the day counts behind residential status
- [ ] Bank interest certificates for each NRO/NRE/FCNR account, and Form 16A for TDS on NRO interest
- [ ] Rent agreement and rent receipts; municipal-tax receipts showing payment during the year; Form 16A if the tenant deducted TDS (tenants of a non-resident must deduct under s.195)
- [ ] Home-loan interest certificate from the lender (interest and principal split; pre-construction interest if any)
- [ ] Capital-gains statements from the broker and RTA (CAMS/KFintech) with acquisition dates and cost; contract notes showing STT
- [ ] Purchase and sale deeds, stamp-duty valuation, transfer-expense invoices; Form 16A for s.195 TDS by the buyer; s.54 new-house deed or s.54EC bond certificates if claimed
- [ ] Insurer's maturity statement and full premium history (needed for the s.10(10D) premium tests)
- [ ] Tax Residency Certificate and Form 10F if any treaty rate is claimed (treaty claims themselves are not computed here)

**Weakest input:** the day counts behind residential status — a few days in India moves the whole return between NR, RNOR and ROR, and they come from a travel log, not a statement.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/india_return.py` with their reasons; every figure above is derived, not restated. Rates and limits are from the FY 2025-26 table (Finance Act 2025, First Schedule; incometax.gov.in 'Tax rates' help page for AY 2026-27 (slabs, surcharge, 87A, cess); capital gains per CBDT FAQs on the Finance (No.2) Bill 2024 (20% s.111A, 12.5% s.112/112A, ₹1.25 lakh s.112A exemption, 12/24-month holding, ₹50 lakh s.54EC — via taxscan.in, as incometaxindia.gov.in returned 403); resident-only indexation proviso to s.112(1)(a) and Finance Act 2023 ₹10 crore s.54 cap per taxguru.in commentary; due dates per Finance Act 2026 commentary (revised return to 31 Mar 2027 — confirm on the e-filing portal)); marked unverified until checked against the primary text.*
