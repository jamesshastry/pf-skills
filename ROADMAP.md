# Roadmap

What is built, what is next, and — as importantly — what this project will not do.

This file exists because the skill list previously lived only in conversation. That is the
same failure mode as a figure restated in prose: it drifts, and nobody can check it.

---

## What pf-skills is

**Skills that help a household make a decision it could get wrong.** Each one encodes a
procedure and a set of thresholds; the figures live in the user's own `facts.yml`.

That framing is doing real work as a filter. A skill earns a place here when:

| Test | Why |
|---|---|
| There is a **decision**, and a defensible rule for it | Otherwise it is a report, not a skill |
| The rule can be **wrong in a specific way** | "Review your insurance" is not a rule |
| The arithmetic fits in **tested code** | Prose restatement is how figures drift |
| The **schema slice is small** | A skill that needs twenty new fields is three skills |
| A **validation case exists** | Something to run it against that has a known answer |

The last one matters more than it looks. Every skill so far was written against a synthetic
fixture and then validated against real data held privately. That second step found defects
in both directions — in the skills *and* in the hand analysis they were checked against.

---

## What pf-skills is not

**Not a portfolio tool.** Anything needing lot-level positions, market data, or order
execution is out of scope. Tax-loss harvesting, wash-sale calendars, factor exposure, and
tax-lot accounting all belong to a portfolio system, and implementing them here would mean
two codebases with two sets of thresholds for the same rule. That is precisely the drift this
project is organised to prevent.

The seam: **pf-skills answers "should I, and how much." A portfolio tool answers "which lots,
and when."**

**Not budgeting or expense tracking.** Commodity, well served, and not a decision.

**Not rate shopping.** Whether a policy is well-priced against the market is a different
exercise from whether the coverage is right, and the conclusions here hold regardless of who
writes the policy.

**Not advice.** Analysis tooling that shows its derivations and names what would change the
answer.

---

## Status

| Cluster | Skills | State |
|---|---|---|
| 1 · Property & casualty | `auto-insurance-review` · `renters-homeowners-review` · `umbrella-liability` | ✅ shipped |
| 2 · Income protection | `survivor-needs` · `life-insurance-review` · `disability-insurance-review` | ✅ shipped |
| 3 · Beneficiaries & estate | `beneficiary-audit` · `estate-document-review` · `digital-estate` · `probate-exposure` | ✅ shipped |
| 4 · Tax-advantaged space | `contribution-space-audit` · `employer-match-audit` · `hsa-review` | ✅ shipped |
| 5 · Cash & debt | `emergency-fund-sizing` · `cash-yield-review` · `debt-payoff-priority` | ✅ shipped |
| 5a · Maintenance | `reference-data-refresh` | ✅ shipped |
| 5b · Maintenance *(cross-cutting)* | `conflict-check` | ✅ shipped |
| 5c · Onboarding *(cross-cutting)* | `document-intake` | ✅ shipped |
| 5d · Review *(cross-cutting)* | `household-review` | ✅ shipped |
| 0 · Status *(cross-cutting)* | `citizenship-status-review` | ✅ shipped — closes `REVIEW.md` A1 |
| 6 · Concentration | `employer-concentration-risk` · `equity-comp-review` | ✅ shipped |
| 7 · Retirement adequacy | `retirement-readiness` · `withdrawal-sequencing` · `roth-conversion-window` · `social-security-timing` | ✅ shipped |
| 8 · Housing | `rent-vs-buy` · `mortgage-review` · `ca-sfh-disclosure-review` · `ca-condo-hoa-disclosure-review` | ✅ shipped |
| 9 · Education | `education-funding` | ✅ shipped |
| 10 · Cross-border planning | ~~`roth-portability-check`~~ ✅ · ~~`geo-arbitrage-model`~~ ✅ · ~~`cross-border-healthcare`~~ ✅ | ✅ shipped |
| 11 · Expat tax filing | ~~`feie-vs-ftc`~~ ✅ · ~~`foreign-presence-tests`~~ ✅ · ~~`state-domicile-exit`~~ ✅ · ~~`cfc-gilti-screen`~~ ✅ | ✅ shipped |
| 12 · Offshore assets & pensions | ~~`foreign-reporting-audit`~~ ✅ · ~~`pfic-divest-or-comply`~~ ✅ · ~~`foreign-pension-classification`~~ ✅ | ✅ shipped |
| 13 · Owner-operator business | ~~`entity-structure-comparison`~~ ✅ · ~~`solo-retirement-plan-choice`~~ ✅ · ~~`depreciation-election`~~ ✅ | ✅ shipped |
| 14 · Portfolio policy | ~~`asset-allocation-review`~~ ✅ · ~~`rebalancing-rules`~~ ✅ · ~~`wash-sale-policy`~~ ✅ | ✅ shipped |
| 15 · Charitable giving | ~~`charitable-giving-strategy`~~ ✅ | ✅ shipped |
| 16 · Healthcare & aging | ~~`aca-subsidy-optimization`~~ ✅ · ~~`medicare-enrollment-timing`~~ ✅ · ~~`long-term-care-funding`~~ ✅ | ✅ shipped |
| 17 · Life transitions | ~~`windfall-management`~~ ✅ · ~~`marriage-finance-merger`~~ ✅ · ~~`divorce-asset-split`~~ ✅ | ✅ shipped |
| 18 · Real estate investing | ~~`passive-loss-eligibility`~~ ✅ · ~~`rental-deal-underwriting`~~ ✅ · ~~`1031-exchange-modeling`~~ ✅ · ~~`cost-segregation-screen`~~ ✅ | ✅ shipped — the gate runs first |
| — · Multinational corporate tax | transfer pricing · DEMPE · IP boxes · Pillar Two | **recommended against — see below** |

Clusters ship whole. A cluster is done when every skill in it runs, its schema extension is
documented, its tests pass, and it has been validated against real data at least once.

**All eighteen clusters are shipped, plus the cross-cutting skills** (`conflict-check`,
`document-intake`, `household-review`, `citizenship-status-review`) **and maintenance.**
What follows is maintenance and whatever the next
real gap turns out to be — see the open questions at the bottom. Resist adding clusters for
symmetry; the filter at the top of this file still applies.

---

## Shipped since

### Cluster 2 — Income protection

The same shape as property & casualty, which is why it comes first: a risk-transfer decision
with a survivability test underneath it. Much of `lib/pf` carries over.

**`survivor-needs`** is the engine the other two consume, and it is deliberately separate.
Both life and disability cover reduce to the same question — *what does this household need if
an income stops* — and computing it twice guarantees two answers.

**`life-insurance-review`** covers the need-versus-in-force gap and the cash-value trap. The
recurring defect in the wild is a permanent policy sold as an investment: a negative real
return, a large front load, and a cost-of-insurance curve that crosses the premium at an age
nobody mentions. The skill has to compute the actual IRR on cash value and find the crossover
rather than accept the illustration. It must also handle the 1035 exchange, which restarts a
surrender clock while feeling like a fix.

**`disability-insurance-review`** is the more neglected of the two and carries a hard deadline
the others don't: **Future Increase Option windows close with age.** Own-occupation versus
any-occupation, elimination period against the liquid buffer, benefit period, whether benefits
are taxable (which depends on who paid the premium with what money), and group versus
individual portability.

*Schema:* `insurance.life[]`, `insurance.disability[]`, and a discount-rate assumption.
*Time-sensitivity:* highest on the board. Insurability degrades with age and health, so a
finding here can expire.

### Cluster 3 — Beneficiaries & estate

Cheap to run, catastrophic when wrong, and almost never checked.

**`beneficiary-audit`** is the highest consequence-to-effort ratio in personal finance.
Beneficiary designations **override the will**, so an unrevised designation defeats an
otherwise perfect estate plan. Checks: every account has a primary *and* a contingent; no
stale designations; minors not named directly (which forces a court-supervised guardianship
rather than the trust that exists for the purpose); per stirpes versus per capita chosen
deliberately; and a trust named as beneficiary only where it is actually funded.

**`estate-document-review`** — will, financial power of attorney, healthcare power of attorney,
advance directive, and trust funding. An unfunded trust is an empty box; that check alone
justifies the skill.

**`digital-estate`** — account inventory, password manager access, and 2FA recovery. Modern,
routinely forgotten, and the reason an otherwise well-prepared survivor gets locked out.

*Shape note:* these are **audit** skills, not calculation skills. Nearly no arithmetic, mostly
completeness and consistency checks. Worth saying so in each `SKILL.md` — a checklist that
pretends to be a model is worse than one that admits what it is.

*Schema:* `accounts[].beneficiaries`, `estate.documents[]` with `last_reviewed`.

---

## Shipped since

### Cluster 4 — Tax-advantaged space

**`employer-match-audit`** is the sleeper. Front-loading deferrals hits the annual limit early
in the year, and if the plan has no true-up, every subsequent pay period earns no match. It is
a recurring five-figure error in a high-income household, it is invisible on every statement,
and essentially nobody checks it.

**`contribution-space-audit`** — employee, employer, and after-tax contributions against the
overall additions limit; catch-up eligibility; the after-tax-plus-in-plan-conversion route;
backdoor and its pro-rata trap.

*Built.* `lib/pf/limits.py` holds the table; see open question 2, now closed.

### Cluster 5a — `reference-data-refresh` *(shipped)*

**The repository has no mechanism for its own facts going stale**, and two of them already have:
`lib/pf/limits.py` carries statutory contribution limits that change every year, and
`lib/pf/jurisdiction.py` carries state insurance rules that change on legislative timescales.
Both currently read `verified_on: unverified`. D16 — IRA contributions left at the prior year's
limit — is exactly this failure occurring in the private data; nothing stops it occurring in the
public tables too.

A skill, not a script, because the update needs judgement: find the authoritative source,
transcribe every field for the year, and refuse a partial update. But it needs mechanical
support alongside it:

- **A staleness report** over every cited table — what it is, when it was last verified, and by
  whom.
- **A test that fails when the current year is missing from `limits.py`.** This is the important
  one. It converts a silent staleness problem into a red build every January, which is the only
  mechanism that reliably works.
- **A refusal to accept a partially filled year**, already enforced by
  `test_known_years_are_fully_populated`.

Scheduled ahead of clusters 6–8 because every skill already shipped depends on these tables
being right, and the cost of them being wrong is confident, believable, incorrect output.

### Cluster 5 — Cash & debt *(shipped)*

**`emergency-fund-sizing`** was already half-built: the P&C skills refuse to recommend dropping
coverage from a household without a buffer. This promotes that rule to a skill and makes the
dependency explicit rather than incidental.

**`cash-yield-review`** — idle cash against short-duration Treasuries or a money market. Simple
arithmetic, high hit rate, and one of the few places where the answer is unambiguous.

**`debt-payoff-priority`** — the honest version, which is that the mathematical answer
(avalanche) and the behavioural answer (snowball) differ, and the skill should show both rather
than pretend the trade-off doesn't exist.

### Cluster 6 — Concentration *(shipped)*

**`employer-concentration-risk`** sits carefully on the right side of the boundary. It does not
compute factor exposures. It states the household-level fact that salary, bonus, unvested
equity, and held employer stock are **one bet**, and that a layoff and a share-price decline
are not independent events — so stress-testing them separately understates the risk. The output
is a policy (for example, sell-at-vest as a standing rule), not a trade.

**`equity-comp-review`** — vest schedule, refresh-grant dependence, and the cliff that appears
when a multi-year grant completes. Income planned against a run-rate that includes an expiring
grant is planned against a number that will not recur.

---

## Later

### Cluster 7 — Retirement adequacy *(shipped)*

Deferred deliberately, for two reasons.

**Assumption sensitivity.** Returns, inflation, and longevity dominate the output. A skill that
projects forty years and reports a single number is a confidence trick; this cluster needs the
real-versus-nominal machinery and scenario handling in place first.

**Prior art.** Mature open-source tools already do Roth conversion sequencing, RMD optimisation,
withdrawal ordering, and Monte Carlo. The open question is whether pf-skills should **wrap one
rather than reimplement it** — reimplementation is a lot of surface area for a well-solved
problem. Resolve that before writing a line.

`social-security-timing` may be separable and earlier: claiming age, spousal benefits, and
especially **survivor benefits**, which are the dominant consideration for a single-income
household and are routinely missed.

### Cluster 9 — Education *(shipped)*

Not in the original eight. Added because writing the private-side documents reached a question
the skills could not answer, which is the right reason to add one.

The decision content is almost entirely the **ordering rule** — retirement before education,
because you can borrow for one and not the other — and this is the only skill that reaches into
another's logic to apply it rather than merely state it. That coupling is earned: the rule is
worthless abstract and useful applied.

Everything else is mechanics people get wrong: a 529 names exactly one beneficiary, each year of
study inflates separately, state deductions frequently do not exist, and the 529-to-Roth rollover
is capped enough that it is not a reason to overfund.

### Cluster 8 — Housing *(shipped)*

Depends on cluster 7's assumptions. The one durable rule worth encoding now: **test
affordability against the conservative income case, not the current one.** Variable
compensation is the first thing to fall and the last thing people model.

---

## Cross-cutting infrastructure

Not skills. Built when a skill needs them, extracted at rule-of-three.

| Piece | Why |
|---|---|
| `lib/pf/limits.py` | Statutory limits by year. Cited table, `UNKNOWN` outside it. Blocks cluster 4. |
| `lib/pf/money.py` | Real versus nominal, and present value. Mixing the two is a documented defect class; make it structural rather than a convention. |
| Absorbability / exposure helpers | `auto` and `property` already share the shape. Third consumer triggers extraction. |
| Band propagation | `Band` currently lives in `auto`. Any second consumer moves it. |
| Conclusion-consistency check | A validator that compares **peer items resolved by different rules** — the failure where every figure is right and the reasoning is inconsistent. Figure-level validation cannot see it. |

---

## Cluster 10 — cross-border retirement *(shipped)*

Requested 2026-09-14. All three skills below are built; the decomposition and the country-table
constraint stood as written. The "open before building" answers are recorded at the bottom —
both were settled by building.

### Domain 1 of the request is already built

The brief's "US tax & savings mechanics" — maxing accounts, catch-ups, SECURE 2.0 super
catch-up, withdrawal sequencing, IRMAA, Social Security taxation — is covered by
`contribution-space-audit`, `withdrawal-sequencing`, `roth-conversion-window`, `hsa-review` and
`social-security-timing`. Cluster 10 should extend those, not restate them.

### One decision per skill, not one strategist

The brief describes a single expert persona. A single skill of that scope fails the filter at
the top of this file — it has no one decision and no defensible rule, so nothing can be tested
and nothing can be wrong in a specific way. Decomposed:

| Skill | The decision it answers |
|---|---|
| `roth-portability-check` | Does the destination recognise the Roth wrapper? If not, **conversion advice inverts** |
| `geo-arbitrage-model` | Blended burn rate across locations, and the portfolio target that follows |
| `cross-border-healthcare` | Medicare does not travel; the enrolment-penalty trap on leaving and returning |

*(`residency-day-tracker` and `expat-tax-exposure` were in the first draft of this cluster and
have moved to cluster 11, where they merge into `foreign-presence-tests` and
`foreign-reporting-audit`. Two clusters each checking PFIC, or each counting days, is exactly the
duplication this file exists to prevent.)*

### The design constraint that matters most

**This is the area where the repository is least able to be authoritative.** Foreign tax
treatment of US retirement accounts is contested, treaty-dependent, changes, and is expensive to
get wrong. India's Section 89A and RNOR status, Roth recognition by treaty, Portugal's regime —
these are not facts to encode from memory.

So the country table follows the `jurisdiction.py` pattern, at nation scale and with the dial
turned further toward refusal:

- A country is in the table **only if checked**, with `source` and `verified_on`.
- Everything else returns `UNKNOWN` and the skill says so rather than reasoning by analogy from
  a country it does know.
- Registered with `provenance.py` alongside the other reference tables.
- The skills frame findings as **"here is the trap, take it to a cross-border tax professional"**
  rather than producing confident conclusions. That is a weaker output than the rest of the
  repository produces, and saying so is part of the deliverable.

The arithmetic — day counting, blended burn rates, location-adjusted portfolio targets — can be
fully rigorous, and should carry the weight the tax content cannot.

### Prior art

PFIC treatment of foreign mutual funds for US persons is well covered elsewhere — compliance
cost, NRE vs NRO accounts, and the liquidate-versus-comply decision. `expat-tax-exposure` should
compute the comparison rather than restate the background.

### Open before building

- ~~Which countries to encode first.~~ **Answered 2026-09-14: the United States and India.**
  The case that drove it is a US tax resident by substantial presence who is **neither a citizen
  nor a lawful permanent resident** — a combination that changes more than it looks, and one the
  schema could not previously express at all. See `REVIEW.md` A1.
- ~~Whether immigration status is its own skill or a section of `foreign-reporting-audit`.~~
  **Its own skill: `citizenship-status-review`** (closes `REVIEW.md` A1). The legal-question
  argument lost to a wider finding — the premise affected every shipped skill, so it needed a
  skill-shaped audit, not a section.
- ~~Whether `geo-arbitrage-model` extends `retirement-readiness` or stands alone.~~ **Standalone
  skill that imports retirement's machinery** (`geo-arbitrage-model` calls into `lib/pf/retirement.py`
  rather than restating projections).

---

## Cluster 11 — expat tax filing *(shipped, with the caveats below standing)*

Requested 2026-09-14, as a second brief. All five skills are built with one owner per topic
as resolved here.

### It is a different activity from cluster 10, and the split matters

Cluster 10 is forward-looking **planning**: where to live, whether to convert, how much is
needed. Cluster 11 is annual **filing**: which election, which credit, which forms. The two
briefs overlap in three places — FBAR, FATCA and PFIC — and building both as written would
produce two skills that each check PFIC and two that each count days.

Resolved by giving each topic exactly one owner. *(A third brief later moved PFIC and
`foreign-reporting-audit` out to cluster 12 — see below.)*

| Skill | The decision it answers | Absorbs |
|---|---|---|
| `feie-vs-ftc` | Form 2555 or Form 1116? Computable, and the answer flips on local tax rate | — |
| `foreign-presence-tests` | Do I meet the 330-day Physical Presence Test, or Bona Fide Residence? | the old `residency-day-tracker` |
| `foreign-reporting-audit` | Which reporting thresholds have I crossed? FBAR · FATCA · 5471 | the old `expat-tax-exposure` |
| `state-domicile-exit` | Has the sticky state actually let go? | — |
| `cfc-gilti-screen` | Do I own something that triggers GILTI, and is §962 worth investigating? | — |

**One day ledger, two tests.** The 330-day Physical Presence Test and a destination's
residency threshold are different rules over the same travel log, so one skill owns the ledger
and evaluates both. Splitting them guarantees two implementations that eventually disagree about
what a day is.

### `feie-vs-ftc` is the strongest candidate in either brief

It is the only one here that is genuinely a **computation with a decision attached**: run the US
liability both ways and compare. The rule of thumb in the brief — FTC in high-tax countries,
FEIE in low-tax ones — is directionally right and insufficient, because the choice also moves:

- **IRA eligibility.** Income excluded under FEIE cannot support an IRA contribution. A household
  that takes the exclusion and then funds a Roth has made an excess contribution.
- **Refundable Child Tax Credit**, which FEIE can eliminate.
- **Carryforward credits**, which FTC generates and FEIE does not — worth real money later.
- **Revocation.** Electing out of FEIE locks you out for five years without IRS consent.

A comparison that reports only the current-year tax bill gets this wrong for exactly the
households where it matters. That is the skill's reason to exist.

### What this needs that does not exist yet

**Federal bracket tables did not go into `limits.py`.** The comparison instead takes
brackets, the standard deduction and the FEIE cap as facts-file assumptions — still
placeholders in the example — rather than expanding the highest-risk table in the
repository. Cheaper, and it keeps unverified rates out of versioned code.

**Cluster 11 shipped without a validation case.** Every other cluster was checked against
real figures at least once — the rule at the top of this file. This one could not be: the
validation set has no foreign earned income and no foreign entity. Stated here rather than
discovered later; it stands until a household with foreign income validates it.

### What to refuse

**GILTI and §962 get a screen, not a calculator.** The election interacts with the §250
deduction, indirect foreign tax credits, later distributions being taxed again, state treatment
and QBI. Producing a number there would be false precision of the most expensive kind.
`cfc-gilti-screen` should establish whether a CFC exists, name the filing obligations and their
penalties, and stop.

**PFIC gets a screen and a pointer**, not an election recommendation. QEF versus mark-to-market
turns on whether the fund issues a PFIC Annual Information Statement, which is a fact about that
specific fund and not something a skill can know.

**No skill in this cluster produces a filing position.** Every report ends at a cross-border CPA
or EA. That is a weaker output than the rest of the repository and it is the correct one.

### Sequencing

Cluster 10 before cluster 11. Cluster 10 is live for this household now — the India question is
real and the retirement-date interaction is unpriced. Cluster 11 only becomes relevant if they
actually move and have foreign income or accounts — and it shipped without a validation case,
as flagged above, until a household with foreign income validates it.

---

## Cluster 12 — offshore assets & pensions *(shipped)*

Requested 2026-09-14, as a third brief. PFIC and reporting split out of cluster 11 as
resolved here, because the third brief makes PFIC too large to be one check inside a
threshold audit.

| Skill | The decision it answers |
|---|---|
| `pfic-divest-or-comply` | Keep the foreign fund and pay the compliance cost, or sell it? |
| `foreign-reporting-audit` | Which thresholds have I crossed — FBAR · FATCA · 5471 · Form 8621 de minimis |
| `foreign-pension-classification` | Is this scheme treaty-protected, a §402(b) employees' trust, or a foreign grantor trust? |

### The decision is divest-or-comply, not which election

The brief frames PFIC around §1291 versus QEF versus MTM. That is the right *analysis* and the
wrong *decision*, because for a retail holder the answer is usually neither: **QEF requires a
PFIC Annual Information Statement that most non-US retail funds do not issue**, and MTM requires
marketable stock on a qualified exchange. Both are frequently unavailable, which leaves §1291 by
default — and §1291 by default is the case for selling.

The skill's job is to **quantify** a comparison that is usually made qualitatively — ongoing
annual compliance cost and the punitive rate differential, against the one-off cost of divesting.

The regime comparison becomes an *input* to that decision, not the output.

### The §1291 interest charge is the best arithmetic in any of the three briefs

It is also the part nobody intuits. An excess distribution or gain is allocated pro-rata across
the entire holding period; each prior year's slice is taxed at **that year's highest marginal
rate**, then carries a compound interest charge at the IRS underpayment rate, year by year. On a
long hold the interest can exceed the tax.

Genuinely computable, and worth computing precisely because the intuition is so wrong.

### …and it needs data this repository must not invent

The calculation requires **the top marginal rate for every year of the holding period and the
IRS underpayment rate for every quarter of it.** A fund bought in 2005 needs eighty-odd quarterly
rates. Encoding that series from memory would mean a long list of numbers where each wrong entry
silently corrupts the result, and the result is a dollar figure someone might act on.

So: **the rate series is supplied in the facts file, never encoded in the repo.** Same principle
as `assumptions.cash_benchmark_apr` — asked for, never fetched. The arithmetic is the skill's
contribution; the rates are data the user or their CPA takes from the IRS tables. That also
forces contact with the authoritative source, which is where someone should be anyway before
acting on a §1291 number.

If the series is absent the skill reports the *shape* of the exposure — holding period, regime,
what drives the charge — and refuses the figure.

### Foreign pensions: classify, do not conclude

Classification drives Forms 3520 and 3520-A, whose non-filing penalties start at $10,000. The
classification itself turns on treaty status, whether employee contributions exceed employer
contributions, and who controls the investment choices.

A scheme table follows the same cited pattern as the country table: treaty-protected schemes
(UK workplace pensions and SIPPs, Canadian RRSPs) in one state, known-problematic ones
(Australian Superannuation, Singapore CPF, **Indian EPF**) in another, everything else `UNKNOWN`.
The skill establishes which bucket and what filing obligation follows. It does not produce a
position.

Indian EPF is the validation-relevant entry, and the only part of these three briefs with a
plausible connection to this household.

### What all three briefs have in common, stated plainly

Together they describe something close to a cross-border CPA practice. This repository's premise
is decisions a household can make; a §1291 allocation is tax preparation.

The line taken across clusters 10–12: **build the decision, refuse the filing.** Divest or
comply, is this scheme a problem, which election is even available, have I crossed a threshold —
all decisions. Producing a filing position, a completed form, or a number to enter on one — none
of them. Every report in these clusters ends at a cross-border CPA or EA, and that is a weaker
output than the rest of the repository by design.

---

## The fourth brief added one skill, not a cluster

The digital-nomad brief (2026-09-14) overlaps almost entirely with clusters 10–12. Presence
testing, sticky-state domicile, FBAR/FATCA, PFIC, CFC screening and the FEIE-versus-FTC choice
are all already assigned owners. Two things in it are genuinely new:

**The self-employment tax trap** — **the Foreign Earned Income Exclusion excludes income tax
only.** A Schedule C filer pays the full 15.3% self-employment tax however long they live abroad,
which surprises almost everyone who has just learned about the FEIE.

This was briefly its own cluster 11 skill. A later brief made entity choice a domestic question
first, so it now lives in **cluster 13's `entity-structure-comparison`**, which owns the
Schedule C / S-Corp / C-Corp arithmetic and flags the cross-border extensions — foreign
corporation, permanent-establishment risk, totalization — pointing back here for the residency
effects. Two skills each modelling an S-Corp election would be the same duplication this file
keeps catching.

**Country attributes, not a skill.** Territorial versus worldwide taxation, digital-nomad visa
terms, and totalization agreements are *columns on the cluster 10 country table*, consumed by
several skills. Making them a skill of their own would produce a report nobody has a decision
to make about. As built: worldwide-versus-territorial is a column, totalization is answered
through `status.py` and consumed by the cross-border skills, and visa terms stayed prose —
no skill prices a visa outcome, so there is nothing for a column to decide.

The brief's "perpetual traveler myth" section is framing rather than a decision — it belongs in
the `foreign-presence-tests` SKILL.md as the thing to say, not as its own skill. For a US
citizen the myth is dispatched in one line: citizenship-based taxation does not care where you
sleep.

---

## Cluster 13 — owner-operator business *(shipped)*

Requested 2026-09-14, as a sixth brief, and **domestic** rather than cross-border.

### Scope: owner-operators, not businesses with staff

A sole proprietor or single-member LLC deciding whether to elect S-Corp status is making a
personal financial decision about their own money — the same shape as rent-versus-buy. A company
optimising payroll across employees is business administration, and out of scope.

The line: **one or two owner-operators, no third-party employees.** That keeps it household-shaped
and also happens to be where the Solo 401(k) rules apply.

| Skill | The decision it answers |
|---|---|
| `entity-structure-comparison` | Schedule C, S-Corp or C-Corp? Including the cross-border extension |
| `solo-retirement-plan-choice` | Solo 401(k), SEP IRA, or a defined benefit plan? |
| `depreciation-election` | §179, bonus, or standard mileage — and the year-one lock-in |

### `entity-structure-comparison` is the strongest candidate in all six briefs

Genuinely computable, genuinely decided wrong in practice, and the reason is a **non-obvious
interaction the brief itself names**:

> W-2 salary reduces self-employment tax **and** reduces qualified business income.

So the reasonable-salary figure has an optimum rather than a floor. Set it too low and the IRS
disallows it; set it high to be safe and the 20% QBI deduction shrinks by twenty cents on every
dollar moved. A comparison that models SE tax savings without the QBI offset recommends the wrong
salary, confidently.

**QBI is folded into this skill rather than standing alone.** Separating them invites exactly the
error of optimising one and ignoring the other — which is the mistake the skill exists to prevent.

### `solo-retirement-plan-choice` must share limits with what is already shipped

A Solo 401(k) is an employer plan, so §415(c) and the catch-up rules already in `limits.py`
govern it. This skill reads the same table and points at `contribution-space-audit` rather than
recomputing space. Its own contribution is the comparison: the elective deferral a Solo 401(k)
allows **on top of** the 25% employer piece is usually decisive against a SEP for an owner-only
business, and that is the finding.

### ⚠️ The BOI claim in the brief is unverified and will not be encoded

The brief states that an **August 2026 FinCEN final rule exempts US domestic companies from
Beneficial Ownership Information reporting**, leaving only foreign-formed entities in scope.

I cannot confirm that. It postdates what I can reliably attest to, the Corporate Transparency
Act's scope has moved more than once, and the penalty for getting it wrong falls on the filer.

Treated as **unverified user-supplied data, not as fact.** If a skill mentions BOI at all it
states the position as reported, marks it unverified, and sends the user to FinCEN — the same
treatment `limits.py` gives a statutory limit. Encoding a "you are exempt" conclusion from a
brief would be the worst failure mode available here: confident, believed, and wrong in the
direction of not filing.

---

## Recommended against — multinational corporate tax structuring

The fifth brief (2026-09-14) asks for holding-company architecture, transfer pricing under the
arm's length principle, DEMPE allocation, IP box regimes, Pillar Two, CbCR and Forms
5471/5472/8858/8992.

**I do not think this belongs in this repository**, and the reasons are structural rather than
about effort:

**It is not personal finance.** The README's first line scopes this to a household's insurance,
liability and risk. A transfer pricing benchmarking study is a different discipline with a
different audience.

**It fails the filter at the top of this file.** "Skills that help a household make a decision it
could get wrong." A household does not allocate DEMPE functions or choose between TNMM and a
profit split.

**Pillar Two applies above €750M consolidated group revenue.** Encoding it here would be scope
theatre — a rule that cannot apply to any user of a personal-finance skill library.

**It requires inputs a skill cannot supply.** Arm's length pricing needs comparables from
licensed commercial databases. Substance requirements need local counsel. Intercompany
agreements need lawyers. A skill that produced a transfer pricing position without a
benchmarking study would be generating exactly the artefact that gets penalised.

**The harm profile differs from everything else here.** Getting an insurance threshold slightly
wrong costs a household money. A plausible-looking TP position used as a substitute for a real
study invites penalties and interest, and the plausibility is what makes it dangerous.

**No validation case exists or could.** Every shipped cluster was checked against a real
household. This one has no household-shaped input at all.

### If it is wanted anyway

It is a **separate product** — different audience, different name, different disclaimer regime,
and a licensed professional in the loop by design rather than as a footer. It should not be
`npx skills add pf-skills`. Say so and I will build it there; I will not fold it into a
household finance library.

---

## Clusters 14 to 18 *(all shipped)*

Five clusters proposed 2026-09-14 in one message, all since built. The assessments below are
kept as written — including the reservations, which explain the order they shipped in and
the shape they took.

### 14 · Portfolio policy — *with one item moved*

| Skill | Verdict |
|---|---|
| `asset-allocation-review` | **In.** Target allocation and glide path are household policy decisions |
| `rebalancing-rules` | **In.** Band-versus-calendar is a rule, decided once |
| ~~`tax-loss-harvesting`~~ → `wash-sale-policy` | **Reshaped — see below** |

Tax-loss harvesting was explicitly assigned to the portfolio tool earlier in this file, with the
reason recorded: it needs lot-level positions and market data, and two codebases holding two
copies of the same threshold is the drift this project exists to prevent. That boundary should
not be quietly reversed.

What *is* a household decision is the **policy**: which securities are permanently excluded from
purchase, across which accounts, and for how long. Any household using a direct-index provider
that harvests losses continuously already needs a rule of exactly this shape — an exclusion list
that must apply to **every** account including the Roth IRA under Rev. Rul.
2008-5. Getting that wrong disallows the loss permanently with no basis adjustment, because the
IRA is not a taxpayer that can inherit it.

So: `wash-sale-policy` sets the rule; the portfolio tool executes it. The seam holds.

### 15 · Charitable giving — *one new skill, not three*

`backdoor-roth-mechanics` and `mega-backdoor-audit` **already exist** inside
`contribution-space-audit`, which raises the pro-rata trap on every backdoor contribution and
checks the after-tax plus in-plan-conversion route. Duplicating them would be the same mistake
this file caught between briefs 1 and 2. If they need more depth, extend that skill.

`charitable-giving-strategy` is genuinely new and unusually well matched to the validating
household: **donating appreciated employer stock avoids the capital gain and reduces the
concentration in one transaction**, which is the rare move that improves two problems at once.
Bunching into a donor-advised fund to clear the standard deduction is arithmetic. Qualified
charitable distributions from an IRA become relevant later.

### 16 · Healthcare & aging — *the strongest of the five*

All three in, and `aca-subsidy-optimization` is the highest-value skill in this entire batch.

A household reaching its retirement target before **65** faces Medicare only at 65. Every year
in between is a **gap funded on the individual market** — and the
premium subsidy depends on modified AGI, which is exactly what `roth-conversion-window` proposes
to deliberately increase. **Two shipped and proposed skills are pulling in opposite directions
and nothing currently notices.**

`medicare-enrollment-timing` carries the same conflict one layer on: IRMAA surcharges look back
two years, so conversions at 63 raise premiums at 65. Late-enrolment penalties are permanent.

`long-term-care-funding` is a real gap in the shipped set — the largest uninsured tail risk most
households carry, and the one the insurance cluster does not touch.

### 17 · Life transitions *(shipped — all three)*

`windfall-management` was worth building: the decision is mostly *do nothing for ninety days*, and
the arithmetic is the tax and beneficiary restructuring that follows. One cross-border note
belongs in it — **a gift or inheritance above $100,000 from a foreign person triggers Form 3520**,
which is a reporting obligation with real penalties and no tax attached, and which an
India-connected household is meaningfully likely to encounter.

`marriage-finance-merger` and `divorce-asset-split` shipped after it. The divorce caveat stands:
it is substantially legal rather than arithmetic, and a skill that reads as guidance during a
divorce carries a different risk profile from one that reads as guidance about car insurance.

### 18 · Real estate investing — *strong content, wrong household*

A detailed brief followed on 2026-09-14. It is the most **computable** of the six: NOI, cap rate,
cash-on-cash, DSCR, IRR and equity multiple are unambiguous formulas with agreed definitions, and
the tax layer on top of them is mechanical.

| Skill | The decision it answers |
|---|---|
| `rental-deal-underwriting` | Does this deal clear the metrics? NOI · cap rate · CoC · DSCR · IRR |
| `1031-exchange-modeling` | Defer or pay? Gain including depreciation recapture, against the 45/180 clocks and boot |
| `passive-loss-eligibility` | Can these losses reach W-2 income at all — §469, the $25k allowance, REPS, or the short-stay exception? |
| `cost-segregation-screen` | Is a study worth commissioning, and does the acceleration actually help? |

**`passive-loss-eligibility` is the one that matters**, and it is a gate rather than a
calculator. Rental losses are passive under §469 and cannot offset W-2 income unless one of three
doors opens: the $25,000 allowance, which phases out well below this household's income; **REPS**,
whose 50% test is close to unattainable for a full-time W-2 employee and is heavily audited; or
the **short-stay exception**, where an average guest stay of seven days or less makes the activity
non-rental, so material participation alone can unlock the loss.

Modelling a deal's after-tax return without first passing that gate produces a number that is
simply wrong for most W-2 investors — which is why the gate is its own skill and runs first.

**`cost-segregation-screen` is a screen, not a study.** A real study is an engineering exercise
producing an audit-defensible allocation. The skill establishes whether the economics plausibly
justify commissioning one — property basis, holding period, marginal rate, and whether the
resulting losses can be used at all, which loops back to the gate.

**Shipped last, as predicted.** All four are genuinely good skills and none applies to a household that rents its
home and owns no investment property. This serves a different investor persona from every other
cluster — kept here as the reason it shipped last, not as an argument against what is built.

---

## Deliberately not planned

Budgeting and expense tracking · rate shopping and carrier comparison · investment selection ·
credit-score optimisation · crypto · anything requiring live market data · anything requiring
lot-level positions · business and commercial insurance · anything that produces a number
without a decision attached to it.

---

## Found in use

Things the shipped skills got wrong or could not express, discovered by running them rather
than by reviewing them. This section is the useful one.

**`cash-yield-review` compared gross yields** *(fixed 2026-09-11)*. A household did the analysis
by hand and the skill could not express it: Treasury interest is exempt from state income tax
and bank interest is not, so two vehicles with the same gross yield are not the same holding —
and in a high-tax state the exemption can be worth more than the headline yield difference it
hides behind. Comparing gross can therefore rank the wrong vehicle first.

The fix separates the **durable** part of a spread from the **floating** part. A gross yield
edge floats with short rates; the exemption is worth the state rate on whatever the yield is, so
it survives convergence. Reporting one combined number invites action on a figure that is mostly
temporary. Same run also surfaced that `tier: liquid` is true of a stock position — the skill was
demanding a cash yield for an equity holding, now handled by `asset_class`.

**`employer-concentration-risk` scored assets only** *(fixed 2026-09-12)*. A household with a
diversified portfolio and 100% of its income from one employer reported as "within guideline" —
for what its own risk register called its largest structural gap. The single-bet finding was also
gated on asset share, suppressing it for exactly the household that needed it. Severity is now
the worse of an asset score and an income score.

**`rent-vs-buy` summed cash flows undiscounted** *(fixed 2026-09-12)*. Over decades that treats a
dollar in year 30 as a dollar today, and since owning front-loads cost and back-loads benefit it
flattered buying — enough to reverse the conclusion against a careful hand analysis. Both sides
are now carried forward to the horizon at the investment return. A calibration test pins the
crossover near a price-to-rent ratio of 15.

*Both were invisible to the synthetic fixture, which did not have the shapes that trigger them.
That is the argument for the real-data validation step, not just for having tests.*

**The lesson worth generalising:** the drift ran private → public, which the design was supposed
to make impossible. The private repo's analysis outran the public skill and nothing detected it.
Nothing still does — see open question 6.

---

## Standing adversarial review

[`REVIEW.md`](REVIEW.md) is the honest inventory of what is wrong with this plan. It is not a
one-off — it should be updated as findings land or are closed.

Two of its findings concern **already-shipped work** and outrank everything proposed here:

- ~~**A1**~~ — **closed** by `citizenship-status-review`. Originally: no skill or document mentioned citizenship, visa status or domicile, so all 25 shipped
  skills carry a silent assumption of US citizenship that a non-citizen household does not
  satisfy. The schema is more careful about which US state someone lives in than about whether
  they are a US citizen.
- ~~**A2**~~ — **closed.** The claim that the household had no cross-border exposure was an
  assumption presented as a fact. It was false: foreign accounts are confirmed.
  `foreign-reporting-audit` was built ahead of the rest of the roadmap and reports FBAR as
  unresolved pending peak balances.

And one that argues directly against the size of this roadmap:

- **A3** — the reference tables assert **some two hundred values that nobody has verified**
  (201 across 21 tables at last count — the figure moves, which is the thing to watch).
  `reference-data-refresh --checklist` generates the list to check them against; until someone
  does, every figure derived from them is provisional. This is the only finding here that code
  cannot close.
- **A6** — `roth-conversion-window` and `aca-subsidy-optimization` give
  the same household opposite instructions for the same five years. `conflict-check` now
  registers that contradiction as data and `household-review` surfaces it live — the edge is
  tracked. Each new skill still adds edges, not just nodes, so registering its conflicts is
  part of shipping it.

---

## Open questions

1. ~~**Wrap or reimplement** the retirement engine?~~ **Reimplemented, deliberately simply.**
   Three reasons: a heavy modelling dependency undoes the small-auditable-library premise that
   makes these skills reviewable; a single number from a black box is worse than a transparent
   range, since a forty-year projection reported to the dollar invites confidence nobody should
   have; and the decision content — drawdown order, the conversion window, survivor benefits —
   needs no simulation at all. `retirement-readiness` therefore reports a 3×3 sensitivity grid
   and points at a dedicated Monte Carlo tool for distributions.
2. ~~**How should statutory limits be versioned?**~~ **Answered by cluster 4.** One table keyed
   by year in `lib/pf/limits.py`, every year fully populated or absent — a partially filled year
   is worse than a missing one — and `UNKNOWN` outside it. Each entry carries `source` and
   `verified_on`, and every skill that reads them prints "verify against irs.gov" regardless.
3. ~~**Do audit-shaped skills need a different `SKILL.md` structure?**~~ **Answered by cluster
   3.** Same structure, different content: no derivation section, and an explicit "this is an
   audit, not a model" line so the reader calibrates correctly. What they *did* need was a
   three-state input convention — omitted / empty / not-applicable — because "nobody looked" is
   a distinct and more common finding than "it is wrong".
6. **Nothing detects a private facts file drifting ahead of the public schema.** The
   `cash-yield-review` gap above sat unnoticed for a week. A check that reads a facts file and
   reports fields no skill consumes would have caught it in one run — and would be a reasonable
   addition to `reference-data-refresh`, which already reports on repository health.

4. ~~**Where does a skill record that a finding expires?**~~ **Answered by cluster 2.**
   `facts.Deadline` carries a date, days remaining, and an urgency band; skills render dated
   findings in their own table and tell the user to re-run before acting. Rider-exercise windows
   were the forcing case.

---

*Ordering here is by leverage and time-sensitivity, not by ease. It will change as clusters
land and as validation finds things. Amend this file rather than remembering.*
