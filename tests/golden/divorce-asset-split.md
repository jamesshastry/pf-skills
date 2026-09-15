# Divorce asset split

## Scope, before anything else

**This needs a family-law attorney.** A divorce is substantially a legal process, and this skill covers exactly one part of it: **the tax character of what is being divided.** It does not value a business, compute support, touch anything involving children, or take a side. Nothing below is a negotiating position — it is arithmetic that both sides' lawyers can check.

## A dollar is not a dollar

| Asset | To | Kind | Statement value | Embedded gain | After tax | Moves by |
|---|---|---|---|---|---|---|
| roth_ira | a1 | `roth_ira` | $200,000 | — | $200,000 | transfer incident to divorce |
| retirement_401k | a2 | `traditional_401k` | $200,000 | — | $152,000 | QDRO |
| brokerage | a2 | `taxable` | $45,000 | $15,000 | $42,750 | §1041 transfer |
| inherited_stock | a1 | `taxable` | $45,000 | $1,000 | $44,850 | §1041 transfer |

|  | `a1` | `a2` | Gap |
|---|---|---|---|
| Statement value | $245,000 | $245,000 | $0 |
| **After tax** | **$244,850** | **$194,750** | **$50,100** |

## What the split is really worth

- ⚠️ **This split is $0 apart on paper and $50,100 apart after tax** — $50,100 of the difference is embedded tax that the nominal figures hide, and it runs in favour of `a1`. A dollar of Roth, a dollar of pre-tax retirement and a dollar of appreciated stock are three different amounts of spendable money. Equalising the paper totals therefore produces an unequal settlement, and it is the most common and most expensive error in an otherwise amicable division. Equalising after tax instead means moving about $25,050 of after-tax value the other way — in whichever account type makes that arithmetic work.

## How each account may be divided

- ⚠️ **Sequencing note on the QDRO, because it is irreversible.** An alternate payee who wants cash rather than a rolled-over account can take it **directly from the plan under the QDRO free of the 10% early-distribution tax** — ordinary income tax still applies. That exception is lost the moment the money is rolled into an IRA, where the ordinary early-withdrawal rules resume. Anyone who will need part of the money before the §72(t) age in `limits.py` should take it at that single point or not at all. Draft the order before the decree is final and have the plan administrator pre-approve it; a rejected QDRO after a finalised divorce means going back to court.

- **roth_ira → transfer incident to divorce.** A Roth IRA is not a qualified plan either, so no QDRO: a direct trustee-to-trustee transfer authorised by the decree. The five-year clocks follow the account.

- **traditional_401k → QDRO.** A qualified plan can only be divided by a **qualified domestic relations order** — a separate court order, drafted to the plan's specification and accepted by the plan administrator. A divorce decree that says the account is split is not a QDRO and the plan will not act on it. Without one, a participant who withdraws and hands over the money has taken a taxable distribution, personally, with the early-distribution tax on top.

- **taxable → §1041 transfer.** A transfer between spouses, or former spouses incident to divorce, is **not a taxable event** — and **basis carries over unchanged**. The recipient inherits the embedded gain along with the shares, which is the whole reason the after-tax column differs from the statement one.

## Beneficiaries

- ⚠️ **Beneficiary designations survive divorce unless somebody files a new form.** An ex-spouse named in 2014 is still the named beneficiary the day after the decree. Many states have a statute purporting to revoke a spousal designation automatically on divorce, and for **ERISA plans — 401(k)s, pensions, employer life insurance — those statutes are preempted and do not apply**; the plan pays whoever is on the form. Settled by the Supreme Court, and litigated repeatedly because families assume the opposite. Change the form on every account the moment the decree permits it, and re-check the retirement plan after any QDRO is executed. `beneficiary-audit` enumerates the accounts.

## Scope

- **Alimony, for agreements executed after 2018, is neither deductible to the payer nor income to the recipient** — the reverse of the long-standing rule, and pre-2019 agreements keep the old treatment unless modified to adopt the new one. That is a factual statement about tax character. **How much support is appropriate, and every question involving children, is outside this module entirely.**

## The weakest input

**The rates.** The after-tax column uses the rates in your facts file, and the ones that matter are the **post-divorce** rates — single or head of household, on one income — not the joint rates on last year's return. They also differ between the two parties, and this report applies one pair to both. Treat the gap as an order of magnitude that shows the direction, not as a settlement figure.

## What this will not do

- **Value a business, a pension's present value, a professional practice, or a house net of selling costs.** Those are appraisals, and a wrong one here would be worse than none.
- **Compute support, or anything linked to custody.** Out of scope, permanently.
- **Advise on strategy, or on what a fair division would be.** 'Equitable' is a legal standard applied by a court to facts this skill does not have, and it is not the same as equal.
- **Replace a QDRO drafted for the plan.** The mechanism notes above say what instrument is required; they are not the instrument.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/transitions.py` with their reasons; every figure above is derived, not restated. The mechanism table is transcribed statute, marked unverified. Confirm every item with counsel before acting — several of these steps cannot be undone.*
