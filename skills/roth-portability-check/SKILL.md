---
name: roth-portability-check
description: Check whether a destination country recognises the US Roth wrapper as tax-free, and show why conversion advice inverts where it does not — a conversion pays an irreversible US tax bill today to buy an exemption the destination may tax anyway. Use when a move abroad, retirement abroad, or a return to a home country is contemplated, and before acting on any Roth conversion recommendation. Reads figures from a local facts file.
requires:
  - crossborder.destinations
---

# Roth portability check

## The idea

A US retirement account is a creature of US law. **The destination decides for
itself what the wrapper is**, and nothing obliges a foreign revenue authority
to agree that a Roth is tax-free. Where it does not, the account is an ordinary
pot of money taxed on the way out — after US tax was already paid on the way in.

The Roth is unusual in being the account most exposed to this. A traditional
balance was always going to be taxed on distribution; the only question is by
whom. A Roth's entire value *is* the exemption, so a destination that does not
grant it does not reduce the benefit — it removes it, having already charged
for it.

## The decision rule

**If the destination does not recognise the wrapper, the conversion advice
inverts.**

`roth-conversion-window` is right for a household that stays: pay tax now at a
low rate to buy tax-free growth. For a household that leaves, the same
conversion pays a real, irreversible US tax bill to buy an exemption the
destination will not grant. Read that skill's output as **conditional on not
moving**, and this one decides whether the condition holds.

`contested` is treated as `not recognised`. That is deliberate and it is the
only judgement call in the module: the act being decided cannot be undone —
recharacterising a conversion was repealed — so a contested reading is not a
sound basis for taking it.

## Why the timing is worse than ordinary double taxation

This is the part that surprises people who assume a foreign tax credit will
sort it out.

A **traditional** distribution is taxed by both countries in the *same* year,
so a credit or treaty relief has something to offset against. A **conversion**
moves the US tax event years earlier — into a year with no foreign tax to
credit against — and the destination's tax then lands in a year with no US tax
to credit against. Neither relief mechanism can reach across the gap. The two
taxes do not net; they stack.

## What is in the table, and what is refused

The country table follows the same discipline as `jurisdiction.py`, with the
dial turned further toward refusal:

- **United States** and **India** only. Everything else returns unknown and the
  report says so rather than reasoning by analogy.
- **No treaty article numbers. No foreign tax rates.** Where the answer turns
  on one, the skill names the question and stops. A plausible-looking citation
  is worse than an admitted gap, because it stops the reader looking.
- Every entry carries a list of items to **verify with a professional**, and
  those appear in the output rather than being quietly resolved.

India is recorded as **contested**, not as resolved in either direction.
Section 89A relief addresses the *timing* of tax on foreign retirement
accounts, not the character of a Roth distribution, and practitioners do not
agree on what crosses the border. The report says that in those words.

The US is in the table as the baseline: "stay put" is a row rather than an
unstated assumption, and it is the only jurisdiction guaranteed to honour the
wrapper.

## What it will not do

It will not tell you whether your Roth is taxable where you are going. It tells
you **whether anyone has checked**, what follows if the answer is yes, and what
order of magnitude is at stake on a rate you supply.

It does not compute a foreign tax liability, does not read a treaty, and does
not price the alternative of not moving. It refuses to quantify anything on a
guessed rate — an unrecorded destination rate produces "cannot be determined",
never a placeholder.

**This is a weaker output than the rest of this repository produces, and saying
so is part of the deliverable.** The right outcome here is that you arrive at a
cross-border tax professional knowing which question to ask — and knowing not
to convert in the meantime.

## Closing

1. **Whether the advice inverts**, and for which destination.
2. **The cost of the conversion you are about to make anyway** — certain,
   immediate, and irreversible — against a benefit that depends on a contested
   foreign reading.
3. **Any transitional window**, such as India's RNOR years, where the ordinary
   answer does not apply.
4. **The professional-verification list**, taken to someone qualified in both
   jurisdictions rather than either one.

---

*Not financial, tax, or legal advice. Cross-border retirement taxation is contested and
treaty-dependent; this establishes the question, it does not answer it.*
