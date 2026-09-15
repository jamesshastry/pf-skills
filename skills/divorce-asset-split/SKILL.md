---
name: divorce-asset-split
description: The tax character of assets being divided in a divorce, and nothing else. Computes the after-tax value of a proposed split — because a dollar of Roth, a dollar of pre-tax 401(k) and a dollar of appreciated stock are three different amounts of money — and states which instrument each account type requires to move without tax, QDRO or transfer incident to divorce. Use when asked about dividing retirement accounts or investments in a divorce, QDROs, or whether a proposed split is actually equal. This is not legal advice and does not cover support, custody, or valuation. Reads figures from a local facts file.
requires:
  - transitions.divorce
---

# Divorce asset split

## This needs a family-law attorney

Stated first, and meant.

A divorce is substantially a legal process, not an arithmetic one, and the
parts of it that matter most — what a fair division is, what a court in your
jurisdiction would do, what to concede — are legal judgements made on facts
this skill does not have and would not be competent to weigh.

What *is* arithmetic is the tax character of what is being divided. That is
the whole of this skill, and it is a genuinely useful piece: the most common
and most expensive error in an otherwise amicable division is treating
differently-taxed dollars as interchangeable.

Nothing here is a negotiating position. It is arithmetic both sides' lawyers
can check, and it works the same whichever side runs it.

## A dollar is not a dollar

This is the single most valuable point in the skill and the one most often
missed.

| $200,000 of… | Spendable, at a 24% ordinary rate / 15% capital-gains rate |
|---|---|
| Roth IRA | $200,000 |
| Traditional 401(k) | $152,000 |
| Taxable stock, $40,000 basis | $176,000 |
| HSA, spent on medical care | $200,000 |

Three accounts with identical statement balances; three different amounts of
money. A 50/50 split of the *statement values* therefore produces an unequal
settlement, and the direction of the error is invisible to both parties
because the paperwork says the totals match.

The report computes each side's total twice — nominal and after tax — and
prints the gap between the two gaps. Where that drift is non-zero it says
which party it favours and roughly how much after-tax value would have to move
the other way to equalise properly.

Some caveats on the after-tax column, which the report also states:

- **Roth and HSA are taken at face value**, which assumes the qualification
  conditions hold: the Roth five-year and age tests, a qualified medical
  expense for the HSA. A party who will need the money before those are met
  holds something worth less.
- **The rates that matter are post-divorce rates** — single or head of
  household, on one income — not the joint rates on last year's return. They
  also differ between the two parties, and the report applies one pair to
  both.
- **A missing basis is a refusal, not a zero.** Assuming basis equals value
  assumes the embedded gain away, in exactly the direction that makes an
  unequal split look equal. Those assets are excluded from the after-tax
  totals and the report says the comparison is incomplete.

## The mechanism is not interchangeable, and getting it wrong is irreversible

| Account | Moves by |
|---|---|
| 401(k), 403(b), pension | **QDRO** — a separate court order, accepted by the plan |
| Traditional or Roth IRA | **Transfer incident to divorce** (§408(d)(6)) — no QDRO |
| HSA | Transfer under the decree |
| Taxable accounts, real property | **§1041 transfer** — not taxable, basis carries over |

**A qualified plan can only be divided by a QDRO.** A divorce decree that says
the account is split is not a QDRO, and the plan will not act on it. A
participant who instead withdraws the money and hands it over has taken a
taxable distribution personally, with the early-distribution tax on top of the
income tax — on the full amount, and with no way back.

**An IRA is not a qualified plan and does not use a QDRO.** It moves by direct
trustee-to-trustee transfer authorised by the decree. Taking a distribution
and re-depositing it is a taxable event for the original owner.

**One sequencing point worth real money.** An alternate payee who needs cash
rather than a rolled-over account can take it **directly from the plan under
the QDRO, free of the 10% early-distribution tax** — ordinary income tax still
applies. That exception is lost the moment the money is rolled into an IRA,
where the ordinary early-withdrawal rules resume. It is a single point in time,
and nobody gets a second one.

Draft the order before the decree is final and have the plan administrator
pre-approve it. A rejected QDRO after a finalised divorce means going back to
court.

## Basis carries over

On a transfer incident to divorce, the recipient takes the transferor's basis
along with the asset. The transfer itself is not taxable; the embedded gain is
simply now theirs.

This is why the after-tax column above is not a theoretical adjustment. The
tax genuinely follows whoever receives the shares, and receiving a
low-basis position is receiving a smaller asset than the statement says.

Get lot-level detail rather than an account total. Which lots move changes the
answer.

## Beneficiary designations survive divorce

An ex-spouse named in 2014 is still the named beneficiary the day after the
decree, and until somebody files a new form.

Many states have a statute purporting to revoke a spousal designation
automatically on divorce. **For ERISA plans — 401(k)s, pensions, employer life
insurance — those statutes are preempted and do not apply.** The plan pays
whoever is on the form. This was settled by the Supreme Court and is still
litigated regularly, because families assume the opposite and find out at the
worst possible time.

Change the form on every account the moment the decree permits it, and
re-check the retirement plan after any QDRO has been executed.
`beneficiary-audit` enumerates the accounts.

## One factual note on support

**For agreements executed after 2018, alimony is neither deductible to the
payer nor income to the recipient** — the reverse of the long-standing rule.
Pre-2019 agreements keep the old treatment unless modified to adopt the new
one.

That is a statement about tax character, which is in scope. **How much support
is appropriate is not, and neither is any question involving children.**

## What it will not do

- **Value anything.** Not a business, not a professional practice, not a
  pension's present value, not a house net of selling costs. Those are
  appraisals, and a wrong number here would be worse than no number.
- **Compute support, or anything linked to custody.** Permanently out of
  scope.
- **Say what a fair split would be.** "Equitable" is a legal standard applied
  by a court, and it does not mean equal.
- **Advise on strategy, or produce anything adversarial.** The output is
  symmetric by construction.
- **Replace a QDRO.** The mechanism notes say what instrument is required.
  They are not the instrument.

## Closing

1. **The after-tax gap against the nominal gap** — and which party the
   difference favours.
2. **Anything that could not be valued**, and why the comparison is therefore
   incomplete.
3. **The instrument each account requires**, and the QDRO sequencing point.
4. **Beneficiary forms**, which nobody changes on their own.
5. **Take all of it to a family-law attorney.** This is one input to that
   conversation, not a substitute for it.

---

*Not financial, tax, or legal advice. Several of the steps described here
cannot be undone; confirm each with counsel before acting.*
