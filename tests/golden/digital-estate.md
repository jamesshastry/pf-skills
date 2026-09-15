# Digital estate

Every other estate document assumes someone can **reach** the accounts. Good security practice and good estate practice pull in opposite directions here: two-factor authentication and a strong password manager lock out heirs exactly as effectively as they lock out attackers.

**1 blocker(s)** · 0 not recorded.

|  | Check | Finding |
|---|---|---|
| 🚫 **BLOCKER** | → combination | **A password manager with no emergency access is a single point of failure, not a plan.** Every credential is in one place and nobody else can reach it. This is worse than no manager, because it creates the belief that the problem is solved. |
| ⚠️ Gap | Emergency access configured | **Missing.** Emergency or legacy access configured in that manager. Having the vault and no way in is the same as not having it. |
| ⚠️ Gap | Written account inventory | **Missing.** A written inventory of accounts and institutions. A survivor cannot close or claim what they do not know exists. |
| ⚠️ Gap | 2FA recovery codes recorded | **Missing.** Two-factor recovery codes recorded somewhere reachable. 2FA locks out heirs exactly as well as it locks out attackers. |
| ✅ OK | Password manager | A password manager, so credentials exist in one recoverable place. |

## The test that matters

Not *does a plan exist* but: **could the person you have in mind actually log in tomorrow, without you, using only what they can find?**

Most households fail this while believing they pass, because the vault exists and the recovery path does not. Walk it once, end to end, rather than assuming.

## Worth knowing

- **Legacy or emergency access built into the password manager is the single highest-value setting here.** It is usually a few minutes and it converts the vault from a lockbox into a plan.
- Major platforms have their own inheritance mechanisms — legacy contacts, inactive-account handlers. They are per-platform, off by default, and independent of anything in your will.
- Terms of service frequently make an account **non-transferable**. An executor may have the legal right to the *value* of an asset and no right to the account holding it.
- A printed copy in the same place as the will beats anything clever. The recovery path must not itself require the credentials being recovered.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/estate.py` with their reasons; every figure above is derived, not restated. A completeness audit. Access rules vary by platform and by jurisdiction.*
