# Roth portability check

🚫 **At least one destination does not honour the Roth wrapper, so the conversion advice inverts.** Converting now buys a US tax bill today in exchange for an exemption that destination may not grant.

| Destination | Roth wrapper | Exposed balance | Local rate | Local tax if taxed |
|---|---|---|---|---|
| Bengaluru | 🚫 **contested** | $82,000 | 30% | $24,600 |
| stay in Austin | ✅ recognised | $82,000 | not recorded | — |
| Lisbon | ❔ not in the table | $82,000 | not recorded | — |

Exposed balance is the Roth balance plus one planned conversion. *Cannot be determined* means the balance is not recorded — it does not mean zero.

## The accounts at stake

|  |  |
|---|---|
| Roth balance | $42,000 |
| Traditional balance | $310,000 |
| Planned conversion (annual) | $40,000 |
| US tax on that conversion | $9,600 |

## The headline

- **The conversion advice inverts.** `roth-conversion-window` is right for a household that stays: pay tax now at a low rate to buy tax-free growth. For a household moving to a destination that does not honour the wrapper, the same conversion pays a real, irreversible US tax bill to buy an exemption the destination will not grant. Read that skill's output as conditional on not moving.

- **The mechanism is the timing, and it is what makes this worse than ordinary double taxation.** A traditional account is taxed by both countries in the *same* year the distribution is taken, so a foreign tax credit or treaty relief has something to offset. A conversion moves the US tax event years earlier, into a year with no foreign tax to credit against — and the destination's tax then lands in a year with no US tax to credit against. Neither relief mechanism can reach across the gap.

- **$9,600 of US tax per year** at 24% on a $40,000 conversion. That payment cannot be undone — recharacterising a conversion was repealed — so it is the clearest thing in this report: a certain cost today against a benefit that depends on a contested foreign reading.

- **At least one destination is not in the table.** Absence here means nobody checked, not that the treatment is benign. The countries that are encoded: IN, US.

- **Take this to a cross-border tax professional.** That is a weaker output than the rest of this repository produces, and saying so is part of the deliverable: foreign treatment of US retirement accounts is contested, treaty-dependent, and changes. What this skill is for is making sure you arrive at that conversation knowing which question to ask — and knowing not to convert in the meantime.

## By destination

### Bengaluru — India

Source: India Income-tax Act residency tests; Section 89A (Finance Act 2021) foreign retirement account relief. Roth character deliberately recorded as contested rather than resolved.

Verified: *unverified — check against incometaxindia.gov.in and a cross-border tax professional*

- 🚫 **The Roth trap — contested, which means plan as if not recognised.** Contested is the finding, not a placeholder for one. India's Section 89A relief (Finance Act 2021) addresses the *timing* mismatch on foreign retirement accounts — income accruing in the account before withdrawal — for residents of notified countries. It is relief on when income is taxed, not a statement that a Roth distribution is tax-free in India. Practitioners do not agree that the US tax-free character survives the border, and this table will not pretend they do. Plan as though distributions are taxable locally as ordinary income until a professional says otherwise in writing.

- At 30%, roughly **$24,600** of local tax would fall on $82,000 of Roth balance that US tax has already been paid on. A rough figure on a supplied rate, not a computation of a foreign tax liability — it is here to establish the order of magnitude, which is the part that changes decisions.

- **A transitional window may help — RNOR, up to about 3 years.** **Resident but Not Ordinarily Resident** is a transitional status for someone returning to India after a long absence. Broadly, foreign-source income is outside the Indian net while it lasts, which makes the RNOR years the natural window for realising US gains or taking US distributions. The qualifying conditions turn on non-residence in nine of the ten preceding years, or on days present across the seven preceding years — counted precisely, from a travel log nobody keeps retrospectively.

- The move is **12 years out**, past the 10-year mark where today's treatment should not drive an irreversible act. Treaties are renegotiated and domestic law changes. What survives that horizon is the *shape* of the risk — that the wrapper may not travel — not this year's reading of it.

- **Social security, IN:** There is no US–India totalization agreement. An Indian national working in the US pays US Social Security and Medicare with no coordination and no certificate of coverage, and Indian provident-fund periods cannot be combined with US credits. This is a straightforward cost with no offset, and it is frequently assumed away by analyses written for European destinations.

- ⚠️ **Verify with a professional:** Whether a Roth distribution is taxable in India, and on what basis — the single most consequential open question in this report.

- ⚠️ **Verify with a professional:** Whether Section 89A relief is available on these specific accounts, what election it requires, and by when.

- ⚠️ **Verify with a professional:** The exact RNOR qualifying conditions and how many years they would last for this household, computed from an actual travel log.

- ⚠️ **Verify with a professional:** Whether the 60-day test is shortened for a person of Indian origin with Indian-source income above a threshold — a variant exists and this table does not encode its terms.

- ⚠️ **Verify with a professional:** Treaty treatment of pensions and retirement distributions. No article number is encoded here on purpose.

Residency day tests recorded for this country:

| Test | Days | Measured over |
|---|---|---|
| resident — 182 days | 182 | the tax year |
| resident — 60 days plus 365 over four years | 60 | the tax year |

### stay in Austin — United States

Source: IRC §408A (Roth); IRC §7701(b)(3) (substantial presence test)

Verified: *unverified — check against irs.gov*

- **Roth recognised.** Qualified Roth distributions are tax-free under IRC §408A. This is the treatment every Roth conversion argument assumes, and it is the only jurisdiction guaranteed to apply it.

- ⚠️ **Verify with a professional:** Whether a closer-connection exception or a treaty tie-breaker applies in a year when two countries both claim residence.

Residency day tests recorded for this country:

| Test | Days | Measured over |
|---|---|---|
| substantial presence | 183 | 3 years |
| minimum current-year presence | 31 | the tax year |

### Lisbon

- **PT is not in the table, so nothing can be said about it.** This module will not reason by analogy from a country it does know — that is precisely the error it exists to prevent, because destinations differ on exactly the point that matters. Establish, in writing and from a professional in that jurisdiction: whether a Roth distribution is taxed locally, whether a treaty addresses it, and how the local residency day test is counted.

## What this will not do

- **It will not tell you whether your Roth is taxable where you are going.** It tells you whether anyone has checked, and what follows if the answer is yes.
- **It encodes no treaty article numbers and no foreign tax rates.** A plausible-looking citation is worse than an admitted gap, because it stops the reader looking.
- **It does not reason by analogy between countries.** Destinations differ on exactly the point that matters, so an absent country is absent rather than approximated.

**The weakest input is the destination's treatment of the wrapper** — not a number in this report, but the single assumption everything here hangs from. Nothing else in the report is close.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/crossborder.py` with their reasons; every figure above is derived, not restated. Cross-border retirement taxation is contested and treaty-dependent. This establishes the question to take to a cross-border tax professional; it does not answer it.*
