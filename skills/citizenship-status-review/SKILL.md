---
name: citizenship-status-review
description: Audit the household's citizenship, US immigration status and domicile, and identify which conclusions elsewhere depend on them — the marital deduction for a non-citizen spouse, estate domicile, expatriation exposure, and social-security totalization. Use when anyone in the household is not a US citizen, when a move abroad is contemplated, or before relying on estate or survivor analysis. Reads figures from a local facts file.
requires:
  - household.members
---

# Citizenship, status and domicile

## Three statuses, three taxes, and they do not move together

| Question | Governed by |
|---|---|
| Is worldwide income taxed by the US? | **Residence** — citizen, permanent resident, or substantial presence |
| Is the estate taxed, and on what? | **Domicile** — residence *plus* intent to remain |
| Does a transfer to a spouse get the marital deduction? | **The spouse's citizenship** |

A household can be fully US tax resident on income, fully US domiciled for
estate purposes, and **still lose the unlimited marital deduction** because the
surviving spouse holds a foreign passport. That combination is common, and it
is why these are three fields rather than one.

## Why this skill exists at all

It was added twenty-sixth, after the first twenty-five were already shipped —
because not one of them mentioned citizenship, visa status or domicile. Every
conclusion they produced carried a silent assumption that the household was a
US citizen or permanent resident.

The schema **refused to run** without knowing which US *state* a household
lived in, and never asked whether they were a US *citizen*. See `REVIEW.md` A1.

That history matters when reading the output: this skill's job is partly to
say **which earlier conclusions were reached without asking.**

## The findings that change other skills' answers

**A non-citizen spouse loses the unlimited marital deduction.** Property
passing to them at death does not qualify unless it goes through a
**qualifying domestic trust (QDOT)** — which has to exist and be drafted for
the purpose before it is needed. A standard revocable trust generally is not
one. The deduction can also be preserved if the spouse naturalises before the
estate-tax return is filed, which is a reason to know where that timeline sits.

**Permanent residence is not citizenship**, and the marital deduction turns on
citizenship. This distinction costs real money and is easy to elide.

**Estate tax turns on domicile, not residence.** A US domiciliary gets the full
exemption; a non-domiciliary gets **$60,000** against US-situs assets, taxed up
to 40% above it. Two orders of magnitude on the same balance sheet. Domicile is
decided on facts and circumstances — long residence, family, a home and a
pending petition all point one way, but it is a *determination*, and
`domicile.determined` records whether anyone has actually made it.

**A nonimmigrant visa holder meeting the substantial presence test is a US tax
resident on worldwide income**, exactly as a citizen would be — including the
obligation to report foreign accounts. The visa category changes immigration
rights, not tax reach. People are routinely surprised by this in the direction
that creates a filing failure.

**Expatriation exposure reaches only two of the four statuses.** §877A applies
to citizens who relinquish and to long-term permanent residents who cease to be
one. Somebody on a nonimmigrant visa has none — **which is worth costing before
accepting a green card**, because taking one starts the eight-year clock.

## Closing

1. **The blockers first**, and which shipped skill each one invalidates.
2. **Whether domicile was determined or assumed.** Usually assumed; usually
   fine; worth knowing which.
3. **Re-run the affected skills** once status is recorded. Treat their earlier
   conclusions as unverified rather than wrong — most will survive, but nothing
   checked.

## What this will not tell you

Whether you *are* US domiciled, whether a QDOT is needed in your case, whether
benefits will be payable where you intend to live, or anything turning on a
treaty. Those are determinations, not lookups. This establishes **which
questions apply to you**.

---

*Not financial, tax, or legal advice. Immigration and estate-domicile questions need a
lawyer, not a skill.*
