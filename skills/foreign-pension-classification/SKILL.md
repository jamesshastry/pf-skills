---
name: foreign-pension-classification
description: Establish whether a foreign pension is treaty-protected, a §402(b) employees' trust, a foreign grantor trust under §§671-679, or contested between the last two — and which of Forms 3520, 3520-A, FBAR and 8938 follow from that bucket. Use when asked about a UK workplace pension or SIPP, a Canadian RRSP, Australian Superannuation, Singapore CPF, Indian EPF or PPF, Form 3520 penalties, or a retirement account left behind in another country. Reads figures from a local facts file.
requires:
  - household.members
---

# Foreign pension classification

## Classify, do not conclude

This skill establishes **which bucket a scheme falls into** and what filing
obligation follows. It does not produce a filing position, a characterisation
to assert on a return, or a treaty claim.

That line is deliberate. The classification is a decision a household can act
on today — engage a cross-border preparer, or do not. The position itself is
tax preparation.

One of the buckets is **contested**, and it is an answer rather than a gap.
Where practitioners disagree and the recorded facts do not separate the
§402(b) and grantor-trust readings, the report says so and plans on the
conservative footing. Reporting the more comfortable default instead would
convert a refusal into a conclusion.

## Why a bucket is worth establishing at all

Classification drives Forms **3520** and **3520-A**, whose non-filing penalties
**start at $10,000** and scale with the amounts involved. Form 3520-A is the
*trust's* own return, which a US owner is responsible for procuring from an
administrator who has usually never heard of it.

A household holding an Australian Superannuation account it has never mentioned
to anyone is exposed to a five-figure penalty for a filing nobody told them
about. That is a different failure mode from a suboptimal allocation, and it is
why the bucket matters more than the nuance inside it.

## The three facts it turns on

1. **Treaty status.** A US treaty pension article that reaches the scheme can
   defer tax on inside build-up and, separately, keep the scheme out of the
   foreign-trust regime. Those are two questions, and a treaty can answer one
   without answering the other.
2. **Whether employee contributions exceed employer contributions.** A scheme
   funded mostly by the employee looks less like an employees' trust under
   §402(b) and more like a foreign trust the employee funded — and §§671–679
   treat a US person who funds a foreign trust as its owner.
3. **Who controls the investment choices.** Holder-directed investment is the
   fact that most often tips a scheme into grantor-trust territory.

The household's own facts can move a scheme *within* the non-treaty buckets.
They cannot move one *into* the treaty bucket: treaty coverage is a property of
the scheme and the treaty, not of how the holder uses it.

## The table is cited, and silence is the honest answer

A scheme is in the table only if the treaty and revenue-procedure position has
been checked, with a `source` and a `verified_on`. Everything else returns
`UNKNOWN` and the report says so — **never reasoning by analogy from a
jurisdiction it does know.**

The UK and Australia both have employer-established workplace pensions and
opposite US treatment. An analogy between them would be confidently wrong, and
indistinguishable in the output from an answer.

Checked so far: UK workplace pensions and SIPPs, Canadian RRSP/RRIF, Australian
Superannuation, Singapore CPF, Indian EPF/PPF.

## The recurring shape: tax-favoured there, taxable here

Worse than it sounds, and the reason the problem cases are problems. Where the
home country does not tax the growth, **there is no foreign tax credit to
offset the US liability.** The two systems do not cancel out; one of them simply
does not apply.

Indian EPF is the clearest instance. US–India Article 20 covers pensions **in
payment**, not accrual — so interest credited each year is commonly treated as
currently taxable in the US while being exempt in India. Singapore is starker:
there is **no US–Singapore income tax treaty at all**, so there is nothing to
claim.

## Treaty-protected is not a no-filing bucket

FBAR and Form 8938 apply to a pension balance whatever its trust
characterisation, and a pension is large enough to cross the aggregate FBAR
test on its own. Thresholds live in `foreign-reporting-audit`, not here.

Two more things the treaty does not do: the UK's 25% tax-free lump sum **is not
tax-free in the US**, and treaty relief is generally **claimed, not automatic**
— except where a revenue procedure makes it so, which the table records scheme
by scheme.

## What it will not do

- **No filing position.** Which form, on what basis, and whether a treaty claim
  applies to these specific facts is a cross-border preparer's call.
- **No treaty analysis of unlisted schemes.** Absence is reported.
- **No thresholds.** FBAR and FATCA numbers live in `foreign-reporting-audit`.
- **No PFIC analysis of what is inside the wrapper.** A SIPP commonly holds
  non-US funds, which are PFICs in their own right; whether the pension wrapper
  shelters them is an unsettled treaty question. See `pfic-divest-or-comply`.

## The weakest input

The **contribution split**. It is one of the three facts the classification
turns on and it is on the annual statement — but when it is absent the report
falls back to the table's default, which is the **more favourable** of the two
non-treaty readings. An absent split therefore biases the answer toward
comfort, and the report says so wherever it happens.

## Closing

1. **The bucket**, per scheme, with the drivers that put it there.
2. **The forms that follow**, and the $10,000 penalty floor where they are the
   trust forms.
3. **Anything `UNKNOWN`** — that is the item to take to a preparer first,
   because nothing else can be said about it here.
4. **FBAR and 8938 regardless**, via `foreign-reporting-audit`.

---

*Not financial, tax, or legal advice. This establishes a bucket, not a filing
position, and every path out of it ends at a cross-border CPA or EA.*
