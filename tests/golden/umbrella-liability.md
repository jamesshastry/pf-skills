# Umbrella liability review

**No umbrella in force.** Recommended **$1,000,000**.

Estimated **$150–$300/yr** — $150–$300 per million of cover.

## 1 · Attachment gate

| | Policy | Coverage | Current | Required |
|---|---|---|---|---|
| 🚫 | auto | bodily injury per person | $100,000 | $250,000 |
| 🚫 | auto | bodily injury per accident | $300,000 | $500,000 |
| 🚫 | auto | property damage | $50,000 | $100,000 |
| 🚫 | property | personal liability | $100,000 | $300,000 |

**Cannot bind.** 4 underlying limit(s) fall below what carriers require. These are cheap to fix and must be fixed first — see `auto-insurance-review` and `renters-homeowners-review`.

## 2 · Sizing

| | |
|---|---|
| Attachable assets | $113,000 |
| + 2 years' gross income (garnishment proxy) | $360,000 |
| **Exposure** | **$473,000** |
| Rounded up to the nearest million | **$1,000,000** |

Sized against **attachable assets plus future earnings**, not net worth: retirement accounts are largely out of a creditor's reach and wages very much are not. Liability judgments also scale with the defendant's ability to pay — the same collision settles differently against someone with $50,000 and someone with $2M. Net worth is itself a risk factor.

**Buying more than the minimum is the cheap part.** The first million runs $150–$300; each million after it $75–$150. The underwriting is in the first layer, so if the limit is a close call, round up.

## 3 · What it does not cover

- **An umbrella does not extend UM/UIM by default.** It covers liability *you* owe others. The coverage that pays your own family when an uninsured driver injures them stops at the auto policy's UM/UIM limit — currently $30,000 per person — no matter how large the umbrella above it. **Excess UM/UIM is a separate election**, not offered by every carrier, and often only available where the umbrella carrier also writes the auto. Ask for it by name.
- Where the umbrella covers a loss the underlying policies do not, a self-insured retention applies — typically $250–$1,000. Ask what it is; it is the deductible nobody mentions.

**Exclusions pass through from the underlying policy.** An umbrella generally will not cover what the policy beneath it excludes by endorsement:
  - `trampoline` — if this is moot, have the endorsement removed; a stale exclusion narrows the excess layer for no benefit.

## 4 · Disclose before binding

- Board service for a nonprofit or an HOA is excluded by most personal umbrellas and needs either a rider or the organisation's own D&O cover. Confirm before assuming you are covered.
- Rideshare and delivery driving voids personal auto cover and the umbrella above it. Disclose it if anyone in the household does it.

## 5 · Where to buy

- **Do not call for a quote yet.** No carrier binds excess coverage over underlying limits that do not qualify. Raise the underlying limits in the same call, then quote.
- **Your existing auto carrier first.** Bundling is nearly always cheapest, and it keeps the attachment question trivial.
- **A standalone excess carrier** writes over *other* carriers' auto and renters. Worth it when the home or renters policy is somewhere cheap you would rather keep. Usually via an independent agent.
- **An independent agent** quotes several carriers at once, which is the whole value on a commoditised product.
- **Not through a life or disability adviser.** They do not underwrite property and casualty, so it becomes a referral to a partner — a middleman on a commodity, and it opens a broader planning conversation you did not ask for.

---

*Not financial, tax, or legal advice. Cost estimates are market ranges, not quotes. Thresholds are in `lib/pf/umbrella.py`; attachment points are imported from the underlying-policy modules so they cannot drift apart.*
