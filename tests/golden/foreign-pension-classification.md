# Foreign pension classification

**This classifies; it does not conclude.** The output is a bucket and the filing obligation that follows from it. Which form is filed, on what basis, and whether a treaty claim applies to these specific facts is a cross-border preparer's call — but whether one is needed is a decision that can be made today.

| Scheme | Country | Bucket | Forms in scope |
|---|---|---|---|
| uk_employer_scheme | GB | ✅ treaty-protected | FinCEN 114 (FBAR), Form 8938 (FATCA) |
| epf_india | IN | 🚫 foreign grantor trust | Form 3520, Form 3520-A, FinCEN 114 (FBAR), Form 8938 (FATCA) |
| epf_india_dormant | IN | ⚠️ contested — both readings live | Form 3520, Form 3520-A, FinCEN 114 (FBAR), Form 8938 (FATCA) |
| kiwisaver | — | ❓ unknown — not in the table | unknown — a preparer has to place this before anything else |

- **2 of 4 scheme(s) sit outside treaty protection.** That is the finding to act on: a preparer who handles the specific jurisdiction, before the next filing deadline rather than after it.

- **1 scheme(s) are recorded as contested rather than classified.** That is the finding, not a gap in it: practitioners disagree and the facts recorded here do not separate the readings. Recording the employee/employer contribution split is what narrows them, and until it is recorded the conservative footing is the one to plan on.

- **1 scheme(s) are not in the table.** Absence is reported rather than guessed, because a wrong analogy between jurisdictions is indistinguishable from an answer.

## uk_employer_scheme

**✅ treaty-protected** — UK workplace pension (occupational / auto-enrolment)

Source: US–UK income tax treaty Arts. 17–18; Rev. Proc. 2020-17 · verified: unverified — check against irs.gov and the treaty text

- Treaty: US–UK Art. 17 (pensions) and Art. 18 (pension schemes). Relief from Forms 3520/3520-A is available under the revenue procedures cited in the table.

- **Treaty-protected — the comfortable bucket, and not a no-filing bucket.** The treaty and the revenue procedures address the foreign-trust forms and the timing of tax on inside build-up. They do nothing about FBAR or Form 8938, which apply to the balance on their own terms.

- **Treaty relief is claimed, not automatic** — except where a revenue procedure makes it so, which the table records scheme by scheme. A position that is available and not claimed is the same as no position.

- **FBAR and Form 8938 apply regardless of the bucket.** A pension balance is a foreign financial asset whatever its trust characterisation, and the aggregate FBAR test is easy to cross once a pension is counted. Run `foreign-reporting-audit` with the balance included — thresholds live there, not here.

- **This is a bucket, not a position.** Which form is filed, on what basis, and whether a treaty claim or a revenue procedure applies to these specific facts is a cross-border preparer's call. The purpose here is to establish whether one is needed, which is a decision the household can make today.

Table notes:

- Treaty relief is claimed, not automatic. The deferral of inside build-up depends on the scheme qualifying under the treaty's pension definition and on the claim being made.
- FBAR and Form 8938 are unaffected. A treaty-protected pension is still a foreign financial asset and frequently still reportable.
- The 25% UK tax-free lump sum is not tax-free in the US. The treaty does not make it so, and this is the single most common surprise.

## epf_india

**🚫 foreign grantor trust** — Indian Employees' Provident Fund (EPF)

Source: US–India income tax treaty (no article number encoded — see the notes); IRC §402(b); §§671–679; §6048 · verified: unverified — check against irs.gov and the treaty text

- No US treaty pension article reaches this scheme.
- Grantor-trust signals: employee contributions ($26,000) exceed employer contributions ($18,000).

- **Reads as a foreign grantor trust.** Under §§671–679 a US person who funds a foreign trust is treated as its owner, which brings **Form 3520 and Form 3520-A** into scope. Non-filing penalties **start at $10,000** and scale with the amounts involved — and 3520-A is the trust's own return, which a US owner is responsible for procuring from an administrator who has never heard of it.

- **Tax-favoured locally and taxable in the US is the recurring shape**, and it is worse than it sounds: where the home country does not tax the growth, there is no foreign tax credit to offset the US liability. The two systems do not cancel out.

- **FBAR and Form 8938 apply regardless of the bucket.** A pension balance is a foreign financial asset whatever its trust characterisation, and the aggregate FBAR test is easy to cross once a pension is counted. Run `foreign-reporting-audit` with the balance included — thresholds live there, not here.

- **This is a bucket, not a position.** Which form is filed, on what basis, and whether a treaty claim or a revenue procedure applies to these specific facts is a cross-border preparer's call. The purpose here is to establish whether one is needed, which is a decision the household can make today.

Table notes:

- **Whether the treaty defers US tax on interest credited each year is the open question, and no article number is encoded here to answer it.** The common practitioner reading is that it does not, in which case EPF interest is currently taxable in the US while being exempt in India — and because India does not tax it, there is no foreign tax credit to offset the US liability.
- The employer's statutory matching contribution supports the §402(b) reading. Voluntary Provident Fund contributions are employee money and push toward the grantor-trust reading. With the split unrecorded both readings stay live, which is why the default is contested rather than the more favourable of the two.
- A **PPF is a different instrument** and is a separate row in this table — do not record one as `in_epf`.
- The EPF balance is a foreign financial account for FBAR and a foreign asset for Form 8938 regardless of which bucket it lands in.

## epf_india_dormant

**⚠️ contested — both readings live** — Indian Employees' Provident Fund (EPF)

Source: US–India income tax treaty (no article number encoded — see the notes); IRC §402(b); §§671–679; §6048 · verified: unverified — check against irs.gov and the treaty text

- No US treaty pension article reaches this scheme.

- **The contribution split is not recorded, so the bucket cannot be narrowed.** Whether employee contributions exceed employer contributions is one of the three facts the classification turns on, and it is on the annual statement. Absent it the table's recorded default stands unnarrowed — treat this as the weakest input in the report.

- **Contested — the §402(b) and grantor-trust readings are both live, and this table will not pick between them.** Practitioners disagree, the household's own facts have not separated the two, and reporting the more comfortable reading would turn a refusal into a conclusion. Plan on the **conservative** footing: Form 3520 and Form 3520-A are in scope until a preparer rules them out, and their non-filing penalties **start at $10,000**. Recording the contribution split is what narrows this.

- **Tax-favoured locally and taxable in the US is the recurring shape**, and it is worse than it sounds: where the home country does not tax the growth, there is no foreign tax credit to offset the US liability. The two systems do not cancel out.

- **FBAR and Form 8938 apply regardless of the bucket.** A pension balance is a foreign financial asset whatever its trust characterisation, and the aggregate FBAR test is easy to cross once a pension is counted. Run `foreign-reporting-audit` with the balance included — thresholds live there, not here.

- **This is a bucket, not a position.** Which form is filed, on what basis, and whether a treaty claim or a revenue procedure applies to these specific facts is a cross-border preparer's call. The purpose here is to establish whether one is needed, which is a decision the household can make today.

Table notes:

- **Whether the treaty defers US tax on interest credited each year is the open question, and no article number is encoded here to answer it.** The common practitioner reading is that it does not, in which case EPF interest is currently taxable in the US while being exempt in India — and because India does not tax it, there is no foreign tax credit to offset the US liability.
- The employer's statutory matching contribution supports the §402(b) reading. Voluntary Provident Fund contributions are employee money and push toward the grantor-trust reading. With the split unrecorded both readings stay live, which is why the default is contested rather than the more favourable of the two.
- A **PPF is a different instrument** and is a separate row in this table — do not record one as `in_epf`.
- The EPF balance is a foreign financial account for FBAR and a foreign asset for Form 8938 regardless of which bucket it lands in.

## kiwisaver

**❓ unknown — not in the table** — unrecognised scheme

- **`nz_kiwisaver` is not in the table, so the bucket is unknown — which is the answer, not a gap to fill by analogy.** UK workplace pensions and Australian Superannuation are both employer-established workplace schemes with opposite US treatment; reasoning from one to the other would be confidently wrong. Schemes checked so far: au_superannuation, ca_rrsp, in_epf, in_ppf, sg_cpf, uk_sipp, uk_workplace_pension. Adding one means adding the treaty position *and* the citation.

- **FBAR and Form 8938 apply regardless of the bucket.** A pension balance is a foreign financial asset whatever its trust characterisation, and the aggregate FBAR test is easy to cross once a pension is counted. Run `foreign-reporting-audit` with the balance included — thresholds live there, not here.

## What would change the answer

- **The contribution split.** Employee against employer contributions to date is the weakest input in this report: absent it, a contested scheme stays contested and the trust forms stay in scope. It is on the annual statement.
- **Who directs the investments.** Holder-directed investment tips a non-treaty scheme toward the grantor-trust reading on its own.
- **A scheme not in the table.** Schemes checked: au_superannuation, ca_rrsp, in_epf, in_ppf, sg_cpf, uk_sipp, uk_workplace_pension. Anything else returns unknown rather than the nearest match — the UK and Australia both have employer workplace pensions and opposite US treatment.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/pension.py` with their reasons; every figure above is derived, not restated. Form 3520 and 3520-A penalties start at $10,000; the scheme table is recorded as unverified and every entry should be checked against the treaty text before it is relied on.*
