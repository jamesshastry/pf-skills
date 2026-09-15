# Estate document review

**4 blocker(s)** · 0 not recorded.

|  | Document | Finding |
|---|---|---|
| 🚫 **BLOCKER** | QDOT (non-citizen spouse) | **The surviving spouse is not a US citizen, and no QDOT is recorded.** The unlimited marital deduction does not apply to a non-citizen spouse; property has to pass through a qualifying domestic trust to defer the tax, and that trust has to exist and be drafted for the purpose before it is needed. Ask the attorney who drew the existing trust whether it qualifies — a standard revocable trust generally does not. |
| 🚫 **BLOCKER** | Financial power of attorney | **Does not exist.** Lets someone manage money if you are alive but incapacitated. A will does nothing here — it only operates on death. This is the most commonly missing document and the one whose absence bites soonest. |
| 🚫 **BLOCKER** | Advance directive | **Does not exist.** States your own wishes so the decision is not left to someone else to guess under pressure. |
| 🚫 **BLOCKER** | → trust funding | **The trust is not funded.** A trust that owns nothing does nothing. Creating it is the part people pay for; retitling assets into it is the part they skip, and skipping it means the probate the trust was bought to avoid happens anyway. |
| ⚠️ Gap | Will | Last reviewed <DATE> — **10 years ago**, past the 5-year mark. Re-read it against the household as it is now. |
| ⚠️ Gap | Healthcare power of attorney | Last reviewed <DATE> — **10 years ago**, past the 5-year mark. Re-read it against the household as it is now. |
| ⚠️ Gap | Revocable trust | Last reviewed <DATE> — **10 years ago**, past the 5-year mark. Re-read it against the household as it is now. |

## What each one actually does

The distinction people miss: **a will only operates on death.** If you are alive and incapacitated it does nothing at all — that is what the powers of attorney are for, and their absence bites far sooner than a missing will does.

| Document | Operates | On what |
|---|---|---|
| Financial POA | While alive, incapacitated | Money, bills, accounts |
| Healthcare POA | While alive, incapacitated | Medical decisions |
| Advance directive | While alive, incapacitated | Your stated wishes |
| Will | On death | Anything not passing by designation or title |
| Trust | Both | Only what is actually titled into it |

Note the last column on the will. Beneficiary designations and joint title pass **outside** it, which for most households is the majority of the money — see `beneficiary-audit`, which is where the real exposure usually sits.

## Review triggers

- A birth, adoption, death, marriage, or divorce in the family
- A move to another state — estate, property, and marital-property rules differ, sometimes materially
- A named executor, trustee, guardian, or agent becoming unable or unsuitable
- A significant change in assets, especially a new property or business interest
- Nothing at all having happened for 5 years

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/estate.py` with their reasons; every figure above is derived, not restated. This is a completeness audit, not a legal review. It checks whether documents exist and are current, not whether they say the right things.*
