---
name: foreign-reporting-audit
description: Establish whether foreign account and asset reporting obligations already exist — FBAR (FinCEN 114), FATCA (Form 8938), PFIC (Form 8621) and foreign gifts (Form 3520) — against their statutory thresholds. Use when anyone in the household holds accounts or investments outside the US, holds foreign citizenship, or has received a gift or inheritance from abroad. Reads figures from a local facts file.
requires:
  - household.members
---

# Foreign reporting audit

## This is a compliance skill, not a planning one

Everything else here helps a household decide something. This one establishes
whether an obligation **already exists** — and if one does, it existed last
year too.

That changes the tone. There is nothing to weigh up: there is a threshold, and
you are either over it or **you do not yet know**. Treat the second as a
finding, not as missing data.

## The three things people get wrong

**FBAR is aggregate, and it is the maximum.** Not per account, and not the
year-end balance. Five accounts of $3,000 cross the threshold. An account that
peaked at $12,000 in March and ended the year at $400 crosses it. Checking
December statements and concluding you are fine is the standard error, and the
schema field is named `max_value_during_year` to make it hard to make.

**FBAR and FATCA are different filings.** One goes to FinCEN separately from
the return; the other attaches to it. Filing one does not satisfy the other,
and the same account is frequently reportable on both. FATCA's thresholds are
higher, so FBAR usually binds first — which is why people who have heard of
FATCA and not FBAR are the ones with a problem.

**Signature authority counts.** An account you can direct but do not own — a
parent's, a relative's, a business's — is reportable. Most commonly missed,
because it does not feel like your money.

## Never assume zero for an unknown balance

A `null` maximum means nobody looked. The skill reports the question as
**unresolved** rather than treating it as zero, because treating it as zero
produces a confident "below threshold" that is very likely wrong — and wrong in
the direction of not filing.

That distinction is the single most important behaviour in this skill.

## Who this applies to that people assume it does not

**A nonimmigrant visa holder who meets the substantial presence test is a US
tax resident on worldwide income**, with the same reporting obligations as a
citizen. The visa category changes immigration rights, not tax reach. Someone
who has held accounts in their country of citizenship since before they
arrived is the most likely person in any household to have an unresolved
obligation, and the least likely to expect one. See
`citizenship-status-review`.

## If a prior year was missed

**Do not quietly file a late form and hope.**

The remediation paths differ sharply depending on whether the failure was
non-wilful, and choosing the wrong one forfeits protections that were
available. Filing a late form outside a formal procedure can foreclose the
procedure.

This is the point to involve a cross-border CPA — **before** filing anything,
not after. Say so plainly rather than leaving it as a footer; it is the most
consequential sentence in the report.

## Closing

1. **What is required, what is unresolved, and what is below threshold** —
   three different states, kept distinct.
2. **For anything unresolved: the specific number to go and find.** The peak
   balance of each account in each year concerned.
3. **The prior-year question**, if any threshold is crossed.
4. **Hand off to `pfic-divest-or-comply`** if any holding is a PFIC — the
   reporting obligation is the symptom; the holding is the problem.

## Out of scope

Preparing or filing anything, choosing a remediation procedure, and the PFIC
election question. Thresholds are statutory and recorded here as unverified.

---

*Not financial, tax, or legal advice. Penalties for these forms are severe and
the remediation path is not a decision to make alone.*
