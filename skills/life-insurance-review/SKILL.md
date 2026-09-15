---
name: life-insurance-review
description: Review life insurance in force against a computed capital need — coverage gap, term expiry against the dependency horizon, the cost spread between term and permanent policies, and the actual internal return on any cash-value policy. Use when asked whether there is enough life insurance, whether to keep or surrender a whole/universal/variable policy, or what a policy illustration is really showing. Reads figures from a local facts file.
requires:
  - household.members
  - household.annual_spending
  - household.balance_sheet
  - insurance.life
---

# Life insurance review

Two questions, in order.

1. **Is there enough?** Against the capital need from `survivor-needs`.
2. **Is what exists the right shape?** Which is where cash-value policies sold
   as investments come apart.

## Employer cover counts as zero

Not as a rhetorical flourish — as an arithmetic choice the report makes and
explains.

Group life is real while employed. But the job ending and the household needing
the cover are **correlated events**: a layoff removes the income and the policy
in the same week, and the replacement policy is priced at that day's age and
health. Counting it toward the gap assumes the job survives whatever created
the claim.

Check whether it's portable or convertible and at what rate, then plan without
it.

## The cash-value question

A permanent policy sold as an investment has to be judged as one. That means
computing its **actual internal return**, not reading the balance.

The report needs `premiums_paid_to_date` to do this. Without it, it will say so
and stop — a cash value on its own cannot answer whether the policy has been a
good investment, which is the only question worth asking about it.

Two properties of the calculation worth knowing:

- It treats total premiums as a lump sum at the midpoint of the holding period,
  which **understates** the loss on a policy funded evenly. That's deliberate:
  it's the generous reading, and these policies typically fail it anyway. When
  the generous number is already negative, there's no argument left to have.
- The bar isn't zero. It's a real return, since the alternative is term
  insurance plus the difference in an index fund.

**The cost-per-thousand spread is the stronger argument.** It requires no
opinion about future returns at all. When one policy costs fifteen or twenty
times another per dollar of death benefit, that ratio is the finding — lead
with it.

## Two traps when surrendering

Both are in the report because both are common and both are expensive.

**Never 1035 exchange into another permanent policy.** It feels like a fix and
is usually presented as one. It restarts the surrender-charge clock on the same
cost architecture.

**Replace the death benefit before cancelling, never after.** The new policy
must be *in force* — not applied for, not approved, in force — before the old
one is surrendered. Insurability is not guaranteed, and the gap between the two
is the household's most exposed moment.

## Term expiring before the need does

A twenty-year term bought when a child was born expires while that child is at
university. The report compares each policy's remaining term against the
dependency horizon and flags any that fall short.

The point isn't that the policy is bad. It's that renewal happens at that age,
in that health, at that price — and that's a decision to make now, while it's
cheap, not then.

## Closing

1. **One gap number**, then the derivation.
2. **The cost spread** if there is one — it's the most persuasive line in the
   report and it's pure arithmetic.
3. **Sequence any replacement explicitly**: new policy in force, then cancel.
4. **Name the dates** — term expiries and conversion deadlines.

## Out of scope

Product selection and carrier shopping, medical underwriting outcomes, and
estate-tax planning for large estates. Beneficiary designations are audited by
`beneficiary-audit`, which matters more than most of this — a perfect policy
paid to the wrong person is a total loss.

---

*Not financial, tax, or legal advice. Verify against your actual policy and
illustration.*
