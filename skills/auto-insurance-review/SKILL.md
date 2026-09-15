---
name: auto-insurance-review
description: Review an auto insurance policy against the household's actual balance sheet — liability adequacy first, then a premium-to-value drop test on comprehensive and collision. Use when asked to review, optimise, right-size, or cut the cost of car insurance, or when deciding whether to keep collision on an older car. Reads figures from a local facts file; contains none of its own.
requires:
  - meta.jurisdiction.state
  - household.balance_sheet
  - auto.vehicles[].value
  - auto.vehicles[].value_basis
  - auto.coverage
---

# Auto insurance review

## The idea

Most households have this backwards. They carry generous coverage on a
depreciating $9,000 car and statutory-minimum coverage on a liability exposure
that reaches every dollar they own plus years of future wages. The premium
saved on the first funds a large multiple of the second.

So the order is fixed: **liability first, physical damage second.** A review
that opens with "you can save $1,000 by dropping collision" and never checks
the liability limits has optimised the wrong side of the policy.

## The rule that decides

Insurance is never expected-value positive — the carrier's margin guarantees
it. The question is never *"is this priced fairly"* but **"would this loss be
survivable."** Those give opposite answers on cheap assets, which is exactly
where the money is.

Two tests, and it matters which one is primary:

| Test | Question | Role |
|---|---|---|
| Premium ÷ ACV vs. 10% | Is this priced badly? | **Screen** |
| Loss ÷ liquid assets | Could you eat this? | **Decides** |

Absorbability wins ties and overrides the screen at both extremes. A household
with a three-week emergency fund keeps collision on a badly-priced policy,
because it has nothing to self-insure from. A household with $600K liquid
drops it on a $9,000 car even at a fair price, because the coverage is a
prepayment, not a risk transfer.

**Absorbability is measured against `liquid` assets, never net worth.** A
household with $2M in a 401(k) and $3,000 in cash cannot absorb an $8,000 loss.

## Run it

```bash
uv run skills/auto-insurance-review/run.py --facts inputs/facts.yml
```

Or, if PyYAML is already installed: `python3 skills/auto-insurance-review/run.py --facts inputs/facts.yml`

Write the output to `outputs/` (gitignored) if you want to keep it.

**Do not recompute any of the figures in prose.** Every number in the report
comes from `lib/pf/auto.py`, which has tests. A figure restated in a sentence
is a figure that will eventually disagree with its source — that failure mode
has already happened once in this project's history and produced two defects
that survived several revisions.

If the household disputes a threshold, change the constant in `lib/pf/auto.py`
and re-run. Do not argue with the output in prose.

## What the script will not do

It **stops** rather than guessing:

- A required field is missing → it lists the paths and exits. Fill them in.
- The state isn't in `lib/pf/jurisdiction.py` → it says so and marks every
  jurisdictional claim unverified. Do not supply the rule from memory; state
  insurance codes differ in ways that reverse conclusions.
- `value_basis` isn't `acv` → the ratio becomes a band, and if that band
  straddles 10% the screen is reported inconclusive rather than resolved in
  either direction.

## Reading the output

### Section 1 — liability

Exposure is reachable assets plus a garnishment proxy on future wages.
Retirement accounts are excluded (ERISA protection is broad; IRA protection is
state-set) — say so, because it is an assumption, not a fact.

The gaps to expect, in rough order of how often they're wrong:

- **UM/UIM** is almost always the worst-funded coverage on the policy and the
  one people misunderstand. It is the only thing that pays *your own family*
  for lost earning capacity, permanent impairment, and death when the at-fault
  driver has nothing. Health insurance pays medical bills and stops. A
  household paying hundreds a month for life and disability cover on the
  earner frequently has $30K standing behind a spouse or child as the injured
  party.
- **Property damage** at $50K is one late-model SUV and a guardrail.
- **Bodily injury** below $250K/$500K also blocks an umbrella, which is the
  cheapest liability dollars available anywhere.

Sequencing is a hard constraint, not a preference: most states cap UM/UIM at
the policy's BI limits, and no umbrella carrier binds until the underlying
limits qualify. **Raise BI → raise UM/UIM → then quote the umbrella.** Getting
this order wrong wastes a call to the carrier.

### Section 2 — physical damage, per vehicle

Decisions the script can return:

| Decision | Meaning |
|---|---|
| `blocked` | Lienholder. Not a financial decision until the loan is paid. |
| `keep` | Either the loss is severe against liquid assets, or the buffer is too thin to self-insure, or the price is fair on a material loss. |
| `drop_collision` | The loss is survivable. Collision is the expensive half; comprehensive is judged separately on its own ratio. |
| `drop_both` | The loss is trivial against liquid assets. The whole line is a prepayment. |

Comprehensive is a **separate decision** and usually the keeper. It runs
roughly a quarter to a third of the pair and covers theft, fire, hail, and
glass — non-fault events that careful driving does not prevent. If the carrier
quotes the pair combined, the report says the comprehensive question is
unresolved. Get the split before cancelling anything; do not estimate it.

Expected annual recovery and the implied load are **sanity checks on the
price, not the decision.** They use industry-average claim frequency and
severity, not this driver's record, and carry a wide band. Present them as
estimates or leave them out.

### Section 3 — what changes when collision comes off

**UM Property Damage.** While collision is in force UMPD is redundant, and in
several states — California among them — you may not carry both. It becomes
purchasable only once collision is dropped, so it belongs to this decision
rather than to the liability section. Where it exists it is often capped
(California: $3,500) and it typically requires the at-fault driver to be
identified, so a hit-and-run with no contact may not qualify. It is a partial
backstop, not a replacement for collision. Say so.

**Medical Payments.** Usually duplicative where health coverage is strong: the
plan covers your family, BI liability covers passengers you injure, UM/UIM
covers uninsured drivers. The trigger that flips it is a **teenager carrying
passengers** — MedPay pays their bills immediately, without waiting for a
fault determination. The report raises this automatically once a dependent
reaches driving age.

## Closing the review

Do three things and stop:

1. **Show the reallocation, not the saving.** The point of a dropped collision
   premium is not that it is saved; it is that the same dollars buy UM/UIM and
   an umbrella covering an exposure two orders of magnitude larger. Frame it
   that way or the household just pockets the money.
2. **List what to confirm before calling the carrier** — lienholder status,
   the carrier's valuation basis, and the comp/collision split. The report
   flags these; carry them forward.
3. **Name the trigger that reopens each decision.** A dependent reaching
   driving age, a lien being paid off, a valuation going stale, a move to
   another state. A decision without a revisit trigger silently expires.

## Deliberately out of scope

Umbrella *sizing* (`umbrella-liability` owns it — this skill only checks
whether the underlying limits qualify for attachment), renters and homeowners
liability (`renters-homeowners-review`), and shopping the policy to other
carriers. Rate comparison is a different exercise and this review's
conclusions hold regardless of who writes the policy.

---

*Not financial, tax, or legal advice. Rules vary by state and change. Verify
against your actual policy and declarations page.*
