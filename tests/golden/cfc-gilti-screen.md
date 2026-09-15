# CFC and GILTI screen

**This is a screen, not a calculator.** It establishes whether a controlled foreign corporation exists, names the filings that follow, and prices the penalty for missing them. It does **not** compute a GILTI inclusion and it does **not** model a §962 election — the findings below say why that refusal is the point rather than a gap.

| Test | Threshold |
|---|---|
| US shareholder | a US person owning **10% or more** of vote **or** value |
| Controlled foreign corporation | US shareholders together owning **more than 50%** of vote or value, on any day of the year (or for 30 uninterrupted days) |

Both are required. *More than* 50%, not 50% — an even split is the case people assume is caught, and it is not.

## Entities

| Entity | Country | Kind | Your % | US shareholders % | Verdict |
|---|---|---|---|---|---|
| Rivera Consultoria Lda | PT | foreign corporation | 60% | 60% | 🚫 **CFC** |
| Iberia Tech Holdings | PT | foreign corporation | 4% | 4% | ✅ not a CFC |
| side consulting | PT | disregarded entity | 100% | 100% | — outside the CFC rules |

**Rivera Consultoria Lda**

- **A CFC.** US shareholders hold 60% — over the 50% control threshold — and this holding of 60% is at or above the 10% US shareholder threshold. Both conditions are required and both are met.
- Consequences that follow automatically, with no distribution and no cash received: a **GILTI inclusion** in current income, **Subpart F** income picked up currently, and the information returns above. Being taxed on profits you have not been paid is the part that surprises people.
- Filings that follow: **Form 5471 (category 5 — US shareholder of a CFC)**, **Form 5471 (category 4 — control)**, **Form 8992 (GILTI inclusion)**.

**Iberia Tech Holdings**

- A 4% holding is below the 10% US shareholder threshold, so no CFC inclusion arises from it on the figures recorded.

**side consulting**

- Recorded as **disregarded entity**, which is outside the CFC rules but not outside the filing rules: Form 8858 applies to a foreign disregarded entity or foreign branch — including a single-member foreign LLC and an unincorporated consulting business run abroad. Screening only for foreign *corporations* is how these get missed.
- Filings that follow: **Form 8858**.

## Findings

- **The penalties are the quantifiable part, and they do not depend on any tax being due.** Form 5471 carries $10,000 **per form, per year**, with a continuation penalty of the same again per 30 days after IRS notice, capped at $50,000 — plus a 10% reduction in foreign tax credits. Three entities and three unfiled years is a six-figure exposure on a company that made nothing.

- **A missing Form 5471 keeps the statute of limitations open on the entire return**, not just the part about the entity (§6501(c)(8)). Years that felt closed are not closed. This is usually the larger consequence and is the one nobody has heard of.

- **Direct ownership understates the position.** Attribution rules treat shares held by a spouse, children, parents, partnerships and trusts as yours, so a family company where no individual holds a majority can still be a CFC. Two minority holders who are related is the ordinary case, not an edge case.

- **This screen stops here, deliberately.** It does not compute a GILTI inclusion and it does not model a §962 election. That election interacts with the §250 deduction, indirect foreign tax credits, the later distribution being taxed a second time, state treatment that often does not follow the federal result, and QBI — and a number produced without those would look exactly as confident as one produced with them. What this establishes is that you are in a regime where the question arises, and what it costs to ignore the forms while deciding. Take it to a cross-border CPA or EA.

## The forms, and what they cost to miss

| Form | Who files | Penalty for not filing |
|---|---|---|
| **5471** | US shareholders and officers/directors of a foreign corporation — categories 1 through 5 | $10,000 per form per year, plus the same again per 30 days after notice up to $50,000, plus a 10% cut in foreign tax credits |
| **8992** | US shareholders of a CFC, computing the GILTI inclusion | flows through the return; the inclusion itself is the exposure |
| **8865** | US persons with a controlling or 10%-plus interest in a foreign partnership | $10,000-scale, on the same pattern |
| **8858** | owners of a foreign disregarded entity or branch — including a single-member foreign LLC and an unincorporated business run abroad | $10,000-scale, and the one people have never heard of |

If years are already missed, **do not simply start filing.** The remediation path differs sharply depending on whether the failure was non-wilful, and choosing it is the first conversation to have with a cross-border CPA or EA — before anything is filed, not after.

## Weakest input

**Weakest input:** the ownership percentages. They are direct holdings as recorded, and attribution rules treat shares held by a spouse, children, parents, partnerships and trusts as yours — so the real figure is at least as high as the one above and frequently higher. A family company where no individual holds a majority is the ordinary case, not an edge case.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/expat.py` with their reasons; every figure above is derived, not restated. This is a screen. Every path out of it ends at a cross-border CPA or EA.*
