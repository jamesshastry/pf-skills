---
name: estate-document-review
description: Audit whether the core estate documents exist, are current, and — for a trust — are actually funded. Covers will, financial power of attorney, healthcare power of attorney, advance directive, and revocable trust. Use when asked about estate planning, wills, powers of attorney, incapacity planning, or what happens if someone can no longer manage their own affairs. Reads figures from a local facts file.
requires:
  - household.members
---

# Estate document review

## The distinction almost everyone misses

**A will only operates on death.** If you are alive and incapacitated it does
nothing whatsoever.

That gap is what the powers of attorney fill, and their absence bites far
sooner and far more often than a missing will does — dementia, a stroke, and a
serious accident are all more likely than death during working years. Without a
financial power of attorney, managing the affairs of a living incapacitated
person requires a court-appointed conservatorship.

| Document | Operates | On what |
|---|---|---|
| Financial POA | Alive, incapacitated | Money, bills, accounts |
| Healthcare POA | Alive, incapacitated | Medical decisions |
| Advance directive | Alive, incapacitated | Your stated wishes |
| Will | On death | Anything not passing by designation or title |
| Trust | Both | **Only what is titled into it** |

Note the last column on the will. It governs the residue — and for most
households the majority of the money passes outside it by beneficiary
designation or joint title. `beneficiary-audit` covers that, and it is usually
where the real exposure sits.

## The unfunded trust

The single most common estate-planning failure, and the reason `funded` is a
separate field from `exists`.

**A trust that owns nothing does nothing.** Drafting it is the part people pay
for. Retitling assets into it is the part they skip — and skipping it means the
probate the trust was bought to avoid happens anyway, having paid for the trust.

The check is not "does a trust exist" but "what is actually titled in its
name."

## Unknown is not absent

A document type missing from the facts file is reported as **not recorded**, not
as missing. The difference matters: one is fixed by drafting, the other by
looking in a drawer. Never collapse them.

## Staleness

Estate documents do not expire. The life they describe does.

The report flags anything unreviewed for more than five years, and lists the
events that should trigger a review regardless of the clock: a birth, death,
marriage, or divorce; a move to another state, since estate, property, and
marital-property rules differ materially; a named executor, trustee, guardian
or agent becoming unable or unsuitable; or a significant change in assets.

The named-guardian check deserves particular attention for households with
young children — it is chosen once, under emotional conditions, and almost
never revisited even when the choice has clearly stopped making sense.

## An audit, not a legal review

It checks whether documents exist and are current. It cannot check whether they
say the right things, and it should not imply otherwise.

## Closing

1. **Blockers first** — an explicitly absent power of attorney, or an unfunded
   trust.
2. **Then the unknowns**, framed as "go and look," with where to look.
3. **Hand off to `beneficiary-audit`**, which usually governs more money than
   everything here combined.
4. **Set a review date** rather than leaving it to the next crisis.

---

*Not financial, tax, or legal advice. Estate law is state-specific and changes.*
