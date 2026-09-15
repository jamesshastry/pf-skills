---
name: renters-homeowners-review
description: Review a renters, condo, or homeowners policy against the household's actual balance sheet — liability adequacy and the umbrella attachment gate first, then contents, loss of use, settlement basis, sub-limits, and endorsed exclusions. Use when asked to review, right-size, or cut the cost of renters or home insurance, or when a policy's limits look like defaults nobody chose. Reads figures from a local facts file; contains none of its own.
requires:
  - meta.jurisdiction.state
  - household.members
  - household.balance_sheet
  - property.form
  - property.coverage
---

# Renters / homeowners review

## The idea

Renters policies are bought once, in about four minutes, at whatever limits
appeared on the quote screen, and then never looked at again. The premium is
small enough that nobody audits it — which is exactly why the limits are
usually defaults nobody chose, and why the errors here are proportionally the
largest in a household's whole insurance programme.

Two of them recur almost universally:

- **Personal liability at $100,000**, which is not merely low, it is
  *disqualifying* — no umbrella carrier will attach above it. A $70/yr policy
  is silently blocking the cheapest catastrophic coverage on the market.
- **Loss of Use at $3,000**, which sounds like a real number and funds about
  one month.

Fix order is therefore: **liability and the attachment gate, then the
settlement basis, then the limits.** Limits are the last thing to argue about,
because a replacement-cost policy at a low limit beats an ACV policy at a high
one.

## Run it

```bash
uv run skills/renters-homeowners-review/run.py --facts inputs/facts.yml
```

**Do not recompute any of the figures in prose.** Everything comes from
`lib/pf/property.py`, which has tests. Disagree with a threshold by changing
the constant and re-running, not by arguing with the output in text.

## The one input the schema cannot give you

There is no `contents_value` field, because **no household has that number.**
Auto has a value per vehicle; contents replacement cost is a thing nobody has
ever counted.

So the script produces a per-person benchmark band and labels it the weakest
input in the review. Treat it that way:

- Never present the benchmark as a finding on its own. It sizes a gap; it does
  not measure one.
- The real deliverable on this line is **"do a room-by-room inventory with
  photographs"** — which the household needs for a claim regardless, and which
  replaces the benchmark with data.
- If the household disputes the band, they are probably right. Ask for the
  inventory instead of defending the constant.

This is the `prefer their data over benchmarks` rule doing real work: a
published per-person figure is a placeholder for a measurement, and should
never survive contact with one.

## Reading the output

### Blockers vs. gaps

A **blocker** stops something else from happening — it is not merely the
biggest gap. Personal liability under the attachment point blocks the umbrella
entirely. An ACV settlement basis blocks the personal property limit from
meaning what it appears to mean. Clear blockers before quoting anything, or
the call to the carrier is wasted.

### Loss of Use is the one people misread

It pays the **difference** between temporary housing and the housing cost
already being paid, not the temporary rent itself. Two errors follow, and they
push in opposite directions:

- Budgeting the *gross* temporary rent overstates the need roughly twofold.
- Assuming a displacement of *weeks* understates it by a factor of three to
  twelve.

The second error dominates. The report shows how many months the current limit
actually funds, which is the number that lands — "$3,000" sounds adequate and
"one month" does not.

### Sub-limits are not limits

Special sub-limits on jewellery, watches, firearms, silverware, business
property, and cash apply **inside** the personal property limit. Raising the
limit does not raise them. Only scheduling does.

If nothing in the household exceeds them, that is a fine answer — but record
it as a decision rather than leaving it unexamined, so the next review doesn't
re-litigate it.

### Endorsed exclusions narrow the umbrella above them

An umbrella generally will not cover what the underlying policy excludes by
endorsement. A dog-liability exclusion attached years ago, on a household with
no dog, is pure downside: it narrows the excess layer and buys nothing. Ask to
have moot endorsements removed.

### Homeowners and condo

The script runs every shared section, then **names what it did not review.**
Schema v1 carries no dwelling fields — Coverage A, other structures, ordinance
or law, extended replacement cost, and the flood and earthquake exclusions are
all absent, and on an owned property that is the larger number by an order of
magnitude.

Do not infer them. Do not review a homeowners policy on the strength of the
shared sections alone and imply it was complete. Propose the schema addition.

## Closing the review

1. **Lead with the blocker and what it costs.** "$20–40/yr unblocks a $2M
   umbrella" is the sentence that gets acted on. A table of eight findings is
   not.
2. **Total the change.** These fixes usually take a renters premium from
   trivial to slightly-less-trivial while multiplying what it does. Show the
   before and after premium together, or the household reads a list of
   upsells.
3. **Hand off to `umbrella-liability`** once the underlying limits qualify.
   This skill checks the gate; it does not size the umbrella.
4. **Name the revisit triggers** — a move, a dog, a renovation, a piece of
   jewellery, a new roommate on the policy, or a switch from renting to
   owning.

## Deliberately out of scope

Umbrella sizing, auto coverage (`auto-insurance-review`), flood and earthquake
(separate policies everywhere, and correctly so), and shopping the policy to
other carriers.

---

*Not financial, tax, or legal advice. Rules and forms vary by state and
carrier. Verify against your actual policy and declarations page.*
