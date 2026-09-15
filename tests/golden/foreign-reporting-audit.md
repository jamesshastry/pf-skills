# Foreign reporting audit

**This is not a planning skill.** It establishes whether a filing obligation already exists — and if one does, it existed last year too. There is nothing here to weigh up: there is a threshold, and you are either over it or you do not yet know.

**2 item(s) require action or cannot be resolved from what is recorded.**

|  |  |
|---|---|
| Filing status assumed | married joint |
| Tax home | United States |
| Foreign accounts recorded | 3 |
| …with a maximum value recorded | 2 |
| Aggregate of known maxima | $24,400 |

| Account | Kind | Country | Max during year |
|---|---|---|---|
| legacy_savings | bank | CA | $6,400 |
| family_account_signature_only | bank | CA | **not recorded** |
| overseas_balanced_fund | foreign mutual fund | CA | $18,000 |

## Findings

- 🚫 **REQUIRED / UNRESOLVED** **FinCEN 114 (FBAR)** — **1 of 3 accounts have no maximum value recorded, so this cannot be determined.** FBAR turns on the **aggregate maximum across all accounts at any point in the calendar year** — not the year-end balance, and not per account. Recorded maxima so far total $24,400 against a $10,000 threshold. Pull the highest balance each account reached in each year concerned.

- 🚫 **REQUIRED / UNRESOLVED** **Form 8621 (PFIC)** — **1 holding(s) are PFICs by default: overseas_balanced_fund.** A non-US pooled fund is the paradigm case. Form 8621 is required **per fund**, and the de minimis waiver — under $50,000 aggregate at year end — applies only if no excess distribution was received and no election is in effect. The default §1291 regime taxes gains at the highest marginal rate for each prior year plus a compound interest charge. See `pfic-divest-or-comply`; the usual answer is to sell.

- ⚠️ Gap **Form 8938 (FATCA)** — Cannot be determined either. Thresholds for married_joint living in the US are $100,000 at year end **or** $150,000 at any time. Higher than FBAR, so FBAR usually binds first — but they are separate filings and both can apply to the same account.

- · Note **Form 3520** — Foreign gifts and inheritances are not recorded. Above $100,000 from a foreign person in a year, Form 3520 is required — no tax, reporting only, and a percentage-of-amount penalty for missing it.

- · Note **—** — **Signature authority counts even without ownership.** An account you can direct but do not own — a parent's, a relative's, a business account — is reportable on FBAR. This is the most commonly missed category, because it does not feel like *your* money.

## The three things people get wrong

1. **FBAR is aggregate, and it is the maximum.** Not per account, and not the year-end balance. Five accounts of $3,000 cross the threshold. An account that peaked at $12,000 in March and ended the year at $400 crosses it. Checking December statements is the standard error.
2. **FBAR and FATCA are different filings.** One goes to FinCEN separately; the other attaches to the return. Filing one does not satisfy the other, and the same account is often reportable on both.
3. **Signature authority counts.** An account you can direct but do not own is reportable. Most commonly missed, because it does not feel like your money.

## If a prior year was missed

**Do not quietly file a late form and hope.** The remediation paths differ sharply depending on whether the failure was non-wilful, and choosing the wrong one forfeits protections that were available. This is the point at which to involve a cross-border CPA — before filing anything, not after.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/reporting.py` with their reasons; every figure above is derived, not restated. Thresholds are statutory but recorded as unverified; penalties for these forms are severe and the remediation path is not a decision to make alone.*
