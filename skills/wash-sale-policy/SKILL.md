---
name: wash-sale-policy
description: Set the household's standing wash-sale rule — which securities are excluded from purchase, across which accounts, and for how long — and check whether every account including IRAs and a spouse's is actually covered. Use when asked about wash sales, direct indexing exclusion lists, tax-loss harvesting rules, whether a purchase in an IRA affects a taxable loss, or substantially identical securities. Reads accounts from a local facts file.
requires:
  - household.balance_sheet
  - portfolio.wash_sale
---

# Wash sale policy

## The idea

This is **not tax-loss harvesting.** It does not identify a loss, value one,
choose a replacement security, or decide when to sell. Those need lot-level
positions and live prices, and they belong to a portfolio tool.

What this sets is the **standing rule that tool has to obey**: which securities
may not be bought, in which accounts, and until when. The rule is a household
policy because the accounts are — a harvesting engine only sees the accounts it
manages, and the taxpayer owns all of them.

## The window is 61 days, not 30

**30 days before the sale and 30 days after, plus the day of sale.**

The half that gets missed is the one *before*, because a purchase that has
already happened cannot be undone once the loss is taken. Quoting "30 days"
understates the exposure by half.

Inside that window, these all count as purchases:

- an automatic monthly contribution
- a dividend or capital-gain reinvestment
- a rebalancing buy — including one this repository's `rebalancing-rules`
  would suggest
- a purchase by a spouse
- a purchase in *any* account, at *any* broker

## The IRA case is the expensive one

An ordinary wash sale **defers** the loss: it is disallowed now and added to
the basis of the replacement shares, so it comes back later.

A wash sale triggered by a purchase in an **IRA does not work that way.** Under
Rev. Rul. 2008-5 the loss is disallowed and **no basis adjustment is
available** — because the IRA is not a taxpayer that can inherit the basis.
The loss is not deferred. It is deleted.

That single asymmetry is why the policy must span every account rather than the
harvesting one. It is also why the mistake is so common: nobody chooses to buy
the security, an automatic contribution does it on a schedule that was set up
years earlier and never reviewed.

Rev. Rul. 2008-5 names IRAs specifically. A 401(k) is not named in it, and this
policy covers 401(k)s anyway — the reasoning that produces the result applies
identically, and the downside of being conservative is nothing.

## Substantially identical, not identical

The test is *substantially identical*, and a policy written against tickers
covers only the easy half of it.

- The **same fund in a different account** — not arguable.
- The fund's **own ETF share class** — not arguable.
- A **different fund tracking the same index** — this is the case everyone
  argues about, and the conservative reading treats it as identical.
- A **different index in the same asset class** — generally accepted as
  distinct, and this is the seam a harvesting engine actually trades through.

Write the exclusion against the *exposure*, not the symbol.

## Continuous harvesting makes the list standing, not dated

If a direct-indexing provider is harvesting continuously, a name sold at a loss
this month may be sold again next month, restarting the window each time. There
is no date on which the exclusion reliably clears.

So the list is a **standing prohibition** in every other account the household
controls — including retirement accounts and a spouse's accounts — until the
provider removes the name. And it must be re-pulled on a schedule: a list
pulled at the moment of a trade was pulled too late to cover the 30 days
before it.

## Unknown coverage is no coverage

An account with `wash_sale_policy_applied: null` is reported as a gap, not as
probably fine. Unrecorded coverage is the exact state in which the expensive
version of this mistake happens — nobody decided it was uncovered, nobody
looked.

The same applies to a spouse's accounts. If they are at a different broker, the
trade is invisible on both 1099-Bs, which makes it more dangerous rather than
less: neither broker reports it, and the taxpayer still owes it.

## What it will not do

- **No losses, no harvests, no replacements.** No lot-level data is read and
  none is wanted.
- **No 1099-B reconciliation.** Working out what already happened is a
  different job from deciding what may happen.
- **No trades of any kind.** The output is a document you hand to every broker
  and every automatic instruction.

## Closing

1. **Any retirement account outside the list** — this is the finding, and it
   outranks everything else in the report.
2. **The exclusion list itself**, with what is still live.
3. **Automatic reinvestment**, which is how an agreed policy gets broken.
4. **The boundary**: this is the rule; execution is elsewhere.

---

*Not financial, tax, or legal advice. The wash-sale rule is federal law and the
figures above are cited in `lib/pf/portfolio.py`; verify them before relying on
them.*
