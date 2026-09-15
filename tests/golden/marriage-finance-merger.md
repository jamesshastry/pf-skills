# Marriage finance merger

## Filing status

**File separate.**

|  | Joint | Separate (combined) | Separate − joint |
|---|---|---|---|
| Federal tax | $41,200 | $46,800 | $5,600 |
| Income-driven loan payments | $14,400 | $3,120 | −$11,280 |
| **Net advantage of separate** |  |  | **$5,680** |

Both tax totals are figures your software produces by running the return twice. This skill does not contain a bracket table and will not estimate them.

## Why, and what separate also costs

- **What separate filing also costs, none of which is in the figures above:** no student-loan interest deduction, no education credits, a Roth IRA phase-out running from zero to $10,000 of MAGI for spouses who lived together at any point in the year, a halved capital-loss allowance, and a requirement that **both** spouses itemise or **both** take the standard deduction. Net those against the advantage before deciding.

- **Separate wins by $5,680/yr.** It costs $5,600 more in tax but saves $11,280 in income-driven student-loan payments, because most IDR plans measure the payment on the borrower's income alone when the borrower files separately. Two caveats that can reverse this: **in a community property state, income is split between spouses regardless of how you file**, which can erase the saving entirely; and the plan rules here change with litigation and regulation, so confirm the current treatment for the specific plan before filing. Neither is encoded in this module.

## Liability

- **A joint return creates joint and several liability.** Each spouse is liable for the whole tax, including on income they did not earn and understatements they did not know about, and that survives divorce. Innocent-spouse relief exists and is neither quick nor certain. Where one spouse has opaque finances — a business, foreign accounts, unfiled years — separate filing buys liability separation that is worth real money even when it costs tax. That is a legal judgement, not an arithmetic one.

## Beneficiaries — the most-forgotten item

- ⚠️ **1 account(s) still carry a pre-marriage designation:** retirement_401k. Two rules that differ and surprise people: an **ERISA plan — a 401(k), a pension — makes the spouse the beneficiary automatically on marriage, and naming anyone else requires the spouse's notarised written consent**; an **IRA has no such protection**, so a parent or an ex named years ago stays named until someone files a new form. Marrying does not revoke anything on an IRA. `beneficiary-audit` does the account-by-account check.

## Estate

- ⚠️ **The unlimited marital deduction does not apply to a non-US-citizen spouse** (a2). Property passing to them at death does not qualify unless it passes through a **qualifying domestic trust (QDOT)**, which has to exist and be drafted for the purpose before it is needed. The deduction can also be preserved if the spouse naturalises before the estate-tax return is filed — which is a reason to know where the naturalisation timeline sits. *(from `citizenship-status-review`.)*

- Lifetime gifts to a non-citizen spouse are also capped at an annual exclusion rather than being unlimited. Relevant to any plan that equalises assets between spouses. *(from `citizenship-status-review`.)*

- **Marriage changes estate treatment substantially, and mostly favourably.** Transfers between US-citizen spouses are unlimited, in life and at death, and the unused portion of a deceased spouse's federal exemption can pass to the survivor — but **portability is an election that requires a Form 706 to be filed, even when no estate tax is owed and no return would otherwise be required.** Missing that filing forfeits the exemption permanently, and it is missed routinely because the family is told there is no tax to pay. See `estate-document-review`; wills, powers of attorney and titling all need revisiting on the same occasion.

## Combining accounts, as a policy

- **No individually-titled account recorded for a2.** See above: this is about what happens when an account is frozen, not about trust.

- **Decide combining as a policy rather than arriving at one by default.** All three shapes work — fully joint, fully separate with an agreed split of shared costs, or joint for shared spending with personal accounts alongside — and the failure mode is not picking any of them, so accounts merge by accident and nobody can say who owns what. Two constraints worth applying to whichever is chosen: each spouse keeps **independent access to money in their own name**, which is a resilience point rather than a trust one (a frozen joint account after a death, an incapacity, or a bank's fraud hold leaves the other spouse with nothing); and each keeps an **individual credit history**, which an authorised-user card does not reliably build. Sizing the first one: 3 months of household spending is $24,000, and that is the floor `cash.py` refuses to self-insure below — a reasonable minimum for the individually-titled account, not a target for it.

## The weakest input

**`tax_if_separate_combined`.** It is the only figure here nobody has usually computed, because computing it means preparing two returns that will not be filed. Everything in the filing-status section is downstream of it, and a household that estimates it from a rule of thumb has estimated the answer.

## What this will not do

- **Estimate either tax total.** No bracket table lives here, deliberately: a stale one produces confident nonsense.
- **Apply community-property rules.** In a community-property state income is split between spouses regardless of how you file, which can erase the separate-filing advantage entirely. That table is not encoded, so the answer is *check it* rather than a guess.
- **Advise on a prenuptial agreement**, which is legal work.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/transitions.py` with their reasons; every figure above is derived, not restated. The non-citizen-spouse estate rule comes from `lib/pf/status.py`; the buffer floor from `lib/pf/cash.py`.*
