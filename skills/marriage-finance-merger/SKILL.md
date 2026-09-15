---
name: marriage-finance-merger
description: The financial decisions a marriage forces — joint versus separate filing netted against income-driven student-loan payments and AGI-floored medical deductions, beneficiary designations and the ERISA spousal-consent rule, estate consequences including the loss of the unlimited marital deduction for a non-citizen spouse, and combining accounts as a deliberate policy. Use when asked about getting married, merging finances with a spouse, married filing jointly versus separately, or what changes financially after a wedding. Reads figures from a local facts file.
requires:
  - household.members
  - transitions.marriage
---

# Marriage finance merger

## The idea

Marriage is a set of defaults that switch on without anyone choosing them:
a filing status, an estate treatment, a beneficiary rule on some accounts but
not others, and a slow merging of accounts that happens by accident if it does
not happen by decision.

This skill is about picking each of those deliberately. It has nothing to say
about the wedding.

## Joint versus separate, decided on two numbers

Joint filing is right for most couples most of the time, and the exceptions
are specific enough to enumerate. What makes the comparison tractable is that
it needs exactly two inputs — **the total tax if you file jointly, and the sum
of the two returns if you file separately** — and both come from running the
return twice in whatever software prepares it. Ten minutes, and exact.

This skill contains **no bracket table** and will not estimate either figure.
Whether a couple faces a marriage penalty or a marriage bonus depends on how
evenly the two incomes are split, and nothing about that generalises into a
rule of thumb worth printing.

### When separate actually wins

**Income-driven student-loan repayment.** Most IDR plans measure the payment
on the borrower's own income when the borrower files separately. For a
high-earning spouse married to a borrower with a large balance, the annual
payment reduction routinely exceeds the extra tax — and that netting is the
arithmetic this skill does. Two caveats can reverse it: **in a
community-property state income is split between spouses regardless of filing
status**, which can erase the saving entirely, and the plan rules here move
with litigation and regulation. Neither is encoded. Confirm both before
filing.

**Large medical expenses concentrated in one spouse.** The itemised deduction
is only the excess over 7.5% of AGI. Measured against one spouse's AGI rather
than the couple's, that floor can be a fraction of the size — $30,000 of
expenses clears a $4,500 floor on a $60,000 AGI and only a $22,500 floor on a
$300,000 joint AGI, a difference of $18,000 of deduction. The report computes
this where the AGI figures are supplied and says it cannot where they are not.

**Liability separation.** A joint return creates **joint and several
liability**: each spouse is liable for the entire tax, including on income
they did not earn and understatements they did not know about, and it survives
divorce. Innocent-spouse relief exists and is neither quick nor certain. Where
one spouse has opaque finances — a business, foreign accounts, unfiled years —
separate filing buys a real thing, and it can be worth paying tax for. That is
a legal judgement rather than an arithmetic one, and the report says so rather
than scoring it.

### What separate costs, which the two totals already contain but people forget

No student-loan interest deduction, no education credits, a Roth IRA phase-out
running from zero to $10,000 of MAGI for spouses who lived together at any
point in the year — effectively a bar on direct Roth contributions — a halved
capital-loss allowance, and a requirement that **both** spouses itemise or
**both** take the standard deduction. The report lists these whenever it
recommends separate, because the recommendation is only as good as the totals
it netted.

## Beneficiary designations are the single most-forgotten item

They override the will, and marriage does not update them.

The rule differs by account type in a way that surprises almost everyone:

- **ERISA plans — a 401(k), a pension, employer life insurance — make the
  spouse the beneficiary automatically on marriage**, and naming anyone else
  requires the spouse's notarised written consent.
- **An IRA has no such protection.** A parent, a sibling, or a former partner
  named years ago stays named until somebody files a new form. Marrying
  revokes nothing.

So the account most people worry about is the one already protected, and the
one they do not think about is the exposed one. `beneficiary-audit` does the
account-by-account check; this skill only points at it.

## Marriage changes estate treatment substantially

Mostly in your favour. Transfers between US-citizen spouses are unlimited in
life and at death, and the unused portion of a deceased spouse's federal
exemption can pass to the survivor.

**But portability is an election, and the election requires a Form 706 to be
filed — even when no estate tax is owed and no return would otherwise be
required.** Missing that filing forfeits the exemption permanently. It is
missed routinely, because the family has just been told there is no tax to
pay.

**For a non-citizen spouse, the unlimited marital deduction does not apply at
all.** Property passing to them does not qualify unless it passes through a
qualifying domestic trust (QDOT), which must exist and be drafted for the
purpose before it is needed; lifetime gifts to them are capped at an annual
exclusion rather than being unlimited. The deduction can also be preserved if
the spouse naturalises before the estate-tax return is filed, which is a
reason to know where that timeline sits. This rule is encoded in
`lib/pf/status.py` and imported here — see `citizenship-status-review`, which
owns it.

Wills, powers of attorney and how property is titled all need revisiting on
the same occasion. `estate-document-review`.

## Combining accounts is a policy, not a default

All three shapes work: fully joint; fully separate with an agreed split of
shared costs; or joint for shared spending with personal accounts alongside.
The failure mode is not choosing any of them — accounts merge by attrition,
and eventually nobody can say who owns what or who is responsible for which
bill.

Two constraints worth applying to whichever shape is chosen, and both are
resilience points rather than trust ones:

1. **Each spouse keeps independent access to money in their own name.** A
   joint account can be frozen — by a death, an incapacity, a bank's fraud
   hold, an estate administration — and the other spouse then has nothing. The
   report sizes this against the three-month buffer floor in `lib/pf/cash.py`,
   as a minimum rather than a target.
2. **Each spouse keeps an individual credit history.** Authorised-user status
   on a partner's card does not reliably build one, and the spouse without a
   file discovers it at the worst possible moment.

## What it will not do

- **Estimate either tax total.** No bracket table lives here, deliberately.
- **Apply community-property rules.** They materially change the separate
  filing case and the table is not encoded, so the answer is "check this",
  not a guess.
- **Advise on a prenuptial agreement**, which is legal work, or on how to
  split shared costs, which is not a financial question.
- **Audit the beneficiary forms.** `beneficiary-audit` does that.

## Closing

1. **The filing recommendation and the number behind it** — including the
   loan-payment netting, which is where the counter-intuitive answers come
   from.
2. **What separate would also cost**, if separate won.
3. **Beneficiaries**, with the ERISA/IRA distinction stated.
4. **The estate items with deadlines**: the Form 706 portability election, and
   a QDOT where the spouse is not a US citizen.
5. **The account policy**, chosen rather than drifted into.

---

*Not financial, tax, or legal advice.*
