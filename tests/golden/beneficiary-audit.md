# Beneficiary audit

**A beneficiary designation overrides the will.** Whatever the estate documents say, these forms decide where these assets go — which is why an otherwise complete estate plan is routinely defeated by one form nobody revisited.

6 designation(s) examined · **3 blocker(s)** · 0 not recorded.

|  | Asset or policy | Finding |
|---|---|---|
| 🚫 **BLOCKER** | retirement_401k | **No beneficiary named.** The asset falls into the estate and goes through probate — slower, public, and governed by the will rather than by choice. On a retirement account it can also collapse the distribution period for the heirs. |
| 🚫 **BLOCKER** | college_529 | **Minor named directly: Mateo Rivera, Lucia Rivera.** A minor cannot receive the proceeds, so a court appoints a guardian of the estate — expensive, slow, supervised, and it hands the money over outright at majority. Name a trust for their benefit instead, which is usually why the trust exists. |
| 🚫 **BLOCKER** | Employer group life | **No beneficiary named.** The asset falls into the estate and goes through probate — slower, public, and governed by the will rather than by choice. On a retirement account it can also collapse the distribution period for the heirs. |
| ⚠️ Gap | brokerage | Names a trust, and the trust is recorded as **unfunded**. Naming a trust as beneficiary does work even when it holds nothing during life — but confirm the trust language actually contemplates receiving it. |
| ⚠️ Gap | college_529 | **No contingent beneficiary.** If the primary dies first, or with you, the asset lands in the estate — the exact outcome the designation exists to avoid. This is the most common real defect, because people name a spouse and stop. |
| ⚠️ Gap | Level Term 20 | Names a trust, and the trust is recorded as **unfunded**. Naming a trust as beneficiary does work even when it holds nothing during life — but confirm the trust language actually contemplates receiving it. |
| ⚠️ Gap | Variable Universal Life | **No contingent beneficiary.** If the primary dies first, or with you, the asset lands in the estate — the exact outcome the designation exists to avoid. This is the most common real defect, because people name a spouse and stop. |
| · Note | college_529 | Multiple beneficiaries including children, and `per_stirpes` is not set either way. It decides whether a predeceased child's share passes to their children or is split among the survivors. Choose it deliberately. |

## How to fix

Beneficiary changes are made **with each custodian**, not by a lawyer and not in the will. Each institution has its own form, and the change is not effective until they confirm it — get the confirmation in writing and record the date.

Re-run after any birth, death, marriage, divorce, or new account.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/estate.py` with their reasons; every figure above is derived, not restated. This is a completeness audit, not a legal review. Naming a trust correctly is a question for the attorney who drew it.*
