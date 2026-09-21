# pf-skills

Local-first agent skills for evaluating and optimizing personal finance — insurance, liability,
and risk. Deterministic calculations run on your machine against your own data;
the home-offer research workflow can query public property sources when invoked.

> **Status:** eighteen clusters shipped, plus cross-cutting review infrastructure — property & casualty, income protection,
> estate, tax-advantaged space, cash & debt, concentration, retirement, housing, education, cross-border retirement,
> expat tax filing, offshore assets & pensions, owner-operator business, portfolio policy, charitable giving,
> healthcare & aging, life transitions, and real estate investing.
>
> Clusters 10 onward ship **without a real-data validation case** — the validation set does not exercise foreign
> earned income, business ownership or investment property. `ROADMAP.md` predicted this; it is a property of those
> skills, not a discovery to be made later.

| Skill | Covers |
|---|---|
| `auto-insurance-review` | Liability adequacy, UM/UIM, the comp/collision drop test, UMPD and MedPay interactions |
| `renters-homeowners-review` | Personal liability and the umbrella attachment gate, contents, loss of use, settlement basis, sub-limits, endorsed exclusions |
| `umbrella-liability` | Sizing against attachable assets and future earnings, the attachment gate, exclusions and pass-throughs |
| `survivor-needs` | Capital-needs analysis: what the household needs if an income stops |
| `life-insurance-review` | Coverage gap, term expiry, and the real return on a cash-value policy |
| `disability-insurance-review` | After-tax cover against spending, occupation definition, and expiring rider windows |
| `beneficiary-audit` | Designations override the will — missing contingents, minors named directly, shares that don't total 100% |
| `estate-document-review` | Will, powers of attorney, directive, and whether the trust is actually funded |
| `probate-exposure` | Which assets go through court, what it costs in your state, and the cheapest instrument per account — a pour-over will is not one |
| `digital-estate` | Could anyone actually log in tomorrow, without you |
| `continuity-plan` | Printable death/incapacity runbook: immediate actions, safe contact and record references, continuity resources, and operational readiness gaps |
| `contribution-space-audit` | Unused tax-advantaged room, the after-tax route, and the backdoor pro-rata trap |
| `employer-match-audit` | Whether front-loading deferrals is forfeiting match |
| `hsa-review` | Eligibility, space, and treating an HSA as a retirement account |
| `emergency-fund-sizing` | The buffer every absorbability test assumes — shortfall *and* excess |
| `cash-yield-review` | What idle cash costs per year, and the Treasury state-tax exemption |
| `debt-payoff-priority` | Avalanche vs snowball with the difference priced, after tax |
| `employer-concentration-risk` | Income and assets as one correlated bet, and the joint scenario |
| `equity-comp-review` | The vesting cliff an annual equity figure hides |
| `retirement-readiness` | When retirement is affordable, as a range across assumptions |
| `withdrawal-sequencing` | Which account to spend first, and why not strictly |
| `roth-conversion-window` | The low-tax years between work and RMDs |
| `social-security-timing` | Claiming age as longevity insurance, and the survivor decision |
| `ca-sfh-disclosure-review` | California detached home: which disclosures apply, what the package is missing, what to read the TDS and SPQ for |
| `ca-condo-hoa-disclosure-review` | California condo: the §4525 packet, reserves and delinquency against thresholds, SB 326, warrantability |
| `housing-affordability` | Reconciled household cash flow, current and stress-tested price ceilings, closing liquidity, and rent-first occupancy phases |
| `home-offer-strategy` | Public-web research for closed-sale comps, explicit verified adjustments, and an opening offer plus walk-away ceiling bounded by affordability and appraisal-gap cash |
| `rent-vs-buy` | Total cost of occupancy and the break-even holding period |
| `mortgage-review` | Removable PMI, prepayment, and the refinance break-even |
| `education-funding` | The college gap per child, the retirement-first rule, and 529 mechanics |
| `citizenship-status-review` | Citizenship, visa status and domicile — and which other conclusions depend on them |
| `foreign-reporting-audit` | FBAR · FATCA · PFIC · Form 3520 — does an obligation already exist |
| `roth-portability-check` | Does the destination honour the Roth wrapper — and the conversion advice that inverts where it does not |
| `geo-arbitrage-model` | Blended burn across a split year, the target it moves, and the day test it trips |
| `cross-border-healthcare` | Medicare does not travel: the Part B keep-or-drop arithmetic and the permanent enrolment penalty |
| `feie-vs-ftc` | Form 2555 or Form 1116 — priced both ways, plus the IRA, child-credit, carryforward and five-year-lock consequences a tax bill misses |
| `foreign-presence-tests` | One travel ledger: the 330-day test across every rolling window, bona fide residence, and the destination's own threshold |
| `state-domicile-exit` | Has the sticky state actually let go — severance, statutory residence, and source income |
| `cfc-gilti-screen` | Does a controlled foreign corporation exist, which forms follow, and what they cost to miss |
| `pfic-divest-or-comply` | Keep the foreign fund and pay the compliance cost, or sell it? The §1291 charge with its compound interest |
| `foreign-pension-classification` | Treaty-protected, §402(b) employees' trust, or foreign grantor trust — and which of 3520/3520-A follow |
| `entity-structure-comparison` | Schedule C vs S-Corp vs C-Corp, and the salary optimum QBI creates |
| `solo-retirement-plan-choice` | Solo 401(k), SEP or defined benefit for an owner-only business |
| `depreciation-election` | §179 vs bonus vs mileage — the income limit, and what year one locks in |
| `asset-allocation-review` | Target versus actual, a horizon-based glide band, and asset *location* — the free half nobody checks |
| `rebalancing-rules` | Bands versus calendar, decided once, and how much of the correction needs a taxable sale |
| `wash-sale-policy` | Which securities are unbuyable, in which accounts — an IRA purchase deletes the loss outright |
| `charitable-giving-strategy` | Give appreciated stock in kind, bunch into a DAF, or run a QCD — and which AGI limit binds |
| `tax-planning` | Filed-return history plus current facts: prioritize tax-reduction candidates and expose liquidity, timing, eligibility, and future-tax tradeoffs |
| `aca-subsidy-optimization` | The pre-Medicare gap, the premium tax credit against MAGI as a share of FPL, and the taper as a marginal rate |
| `medicare-enrollment-timing` | Which enrolment window applies, what a late Part B costs permanently, and the two-year IRMAA lookback |
| `long-term-care-funding` | A multi-year care episode against investable assets, and whether the surviving spouse's retirement survives it |
| `windfall-management` | Do nothing for ninety days — then tax character, estimated tax, Form 3520 |
| `marriage-finance-merger` | Joint vs separate netted against IDR payments · beneficiaries · marital deduction |
| `divorce-asset-split` | After-tax value of a proposed split · QDRO vs transfer incident to divorce |
| `passive-loss-eligibility` | Can a rental loss reach W-2 income at all — §469's three doors, and which one is open |
| `rental-deal-underwriting` | NOI without the mortgage in it, cap rate, cash-on-cash, DSCR against the lender floor, IRR |
| `1031-exchange-modeling` | Defer or pay — gain *including* depreciation recapture, cash and mortgage boot, the 45/180 clocks |
| `cost-segregation-screen` | Whether a study is worth commissioning, and whether the deduction is usable at all |
| `conflict-check` | Cross-cutting: where two skills' recommendations pull the same dollar in opposite directions |
| `document-intake` | Onboarding: which fields are still unset, what each one unblocks, and which document answers it |
| `reference-data-refresh` | Maintenance: annual statutory readiness plus provenance for private tax-year assumptions |
| `household-review` | Cross-cutting: every skill's verdict re-read in-process, ranked — expiring findings, uncovered losses, priced drags, then optimizations |
| `financial-history-review` | Cross-cutting: immutable observed snapshots, historical skill results, comparable metric changes, finding transitions, and methodology attribution |
| `financial-scenario-planner` | Cross-cutting: deterministic baseline-versus-scenario monthly liquidity, net worth, saving, debt, and recovery conditions |
| `job-loss-stress-test` | Correlated employment loss: income, vesting, match, employer stock, health cost, runway, and intra-period cash failure |
| `windfall-deployment-planner` | After the decision pause: compare cash, investing, debt, home, and split uses of net proceeds without treating stock as cash |

This table is a catalog, not an execution order. Start with the cross-cutting
workflow below, then follow only the domain chain relevant to the decision. For
example, the property-and-casualty chain runs `auto-insurance-review` and
`renters-homeowners-review` before `umbrella-liability`, because the umbrella
depends on adequate underlying limits.

What comes next, and what this project deliberately won't do: [ROADMAP.md](ROADMAP.md).

### A test here is designed to fail eventually

`test_the_current_year_is_present_in_the_limits_table` goes red when the
calendar rolls into a year `lib/pf/limits.py` doesn't cover. That is the
mechanism, not a bug — statutory limits change annually, and a stale one gets
quoted confidently and believed. The skills themselves degrade safely, so it is
a maintenance signal rather than a functional break. Run
`reference-data-refresh`.

The read-only `Reference data readiness` GitHub Actions workflow runs weekly.
It checks the current tax year through October and next-year readiness in
November and December, then writes the audit to the job summary. It never reads
ignored `inputs/`, researches figures, or commits an update; a failed run is the
signal to invoke `reference-data-refresh`, review primary sources, and submit a
normal change. Run a local private-assumption audit with:

```bash
uv run skills/reference-data-refresh/run.py \
  --facts inputs/facts.yml --annual-only --strict
```

Setup, manual-dispatch, failure-resolution, and privacy details are in the
[reference-data automation runbook](docs/reference-data-automation.md).

---

## Your data never leaves your machine

The first question anyone should ask of a personal-finance tool, answered plainly:

- **There is no pf-skills server.** No account, sign-up, or background upload;
  every deterministic runner is offline.
- **Your figures live in `inputs/facts.yml`**, gitignored, on your disk.
- **Historical snapshots live in `history/`**, also gitignored; they are retained
  copies of private facts, so never force-add them.
- **Skills are text and runners are offline.** They tell an AI agent how to
  reason and the Python code transmits nothing. An agent following the explicit
  home-offer research workflow may separately use its web tools as described
  below.
- **Outputs are grouped by purpose** under `outputs/reports/`, `history/`,
  `scenarios/`, and `structured/`. Generated contents are gitignored.
- **Statements go in categorized `inputs/<category>/` directories.** Their
  contents are gitignored and read only by you and whichever agent you hand
  them to. The legacy flat `documents/` directory remains supported.
- **Local task briefs go in `prompts/`.** Everything there except the README is
  gitignored because prompts can quote the same private facts as their inputs.
- **Comparable research is the explicit network exception.** When an agent runs
  `home-offer-strategy`, it may send the minimum necessary address or property
  search terms to public search and listing services. It must not upload local
  documents or financial facts, and it must cite what it finds.

If you install via `npx skills add`, that CLI reports an anonymous install count and nothing
else — it never sees your data, because it isn't involved once the files are on disk.

The one thing to be aware of: **your AI agent is a third party.** If you run these skills in
Claude Code, Cursor, or similar, your facts are sent to that provider like any other file you
open. That's their privacy policy, not ours. For maximum privacy, run against a local model.

---

## How it works

```
1. Check the setup        uv run scripts/doctor.py
2. Start a facts file     uv run scripts/init_facts.py
3. Add your documents     cp ~/Downloads/checking.pdf inputs/banking/
4. Fill the next facts    uv run skills/document-intake/run.py
5. Rank the live issues   uv run skills/household-review/run.py
6. Follow one chain       run the specialist reports named by the review
7. Check interactions     uv run skills/conflict-check/run.py
8. Test material changes  run a scenario before acting, when applicable
9. Preserve observations  capture history explicitly and repeat the review
```

Full walkthrough: **[QUICKSTART.md](QUICKSTART.md)**.

### Skill chains

These are routing paths, not hard software dependencies. Stop when a report is
irrelevant or its required facts are unavailable. `household-review` chooses
the live starting point; the chains show which neighboring reports must be read
together before acting. The property-evaluation path is also declared in
`lib/pf/workflows.py` and rendered by `home-offer-strategy`, so its tested order
cannot drift independently from this documentation.

| Decision | Recommended chain |
|---|---|
| Property and casualty | `auto-insurance-review` + `renters-homeowners-review` → `umbrella-liability` |
| Income protection | `emergency-fund-sizing` → (`survivor-needs` → `life-insurance-review`) + `disability-insurance-review` → `beneficiary-audit` → `continuity-plan` |
| Estate continuity | `beneficiary-audit` + `estate-document-review` + `probate-exposure` + `digital-estate` → `continuity-plan` |
| Retirement transition | `retirement-readiness` → `social-security-timing` + `withdrawal-sequencing` + `roth-conversion-window` → applicable ACA, Medicare, tax, and cross-border reviews → `conflict-check` → scenario |
| Portfolio changes | `asset-allocation-review` → `rebalancing-rules` → `wash-sale-policy` → `tax-planning` → `conflict-check` |
| Home purchase | `housing-affordability` + `rent-vs-buy` → applicable disclosure review → `home-offer-strategy` → `conflict-check` → scenario |
| Owner-operated business | `entity-structure-comparison` → `solo-retirement-plan-choice` + `depreciation-election` → `tax-planning` → `conflict-check` |
| Cross-border move | `citizenship-status-review` → `foreign-presence-tests` + `state-domicile-exit` → applicable tax, reporting, pension, investment, healthcare, and Roth reviews → `conflict-check` |
| Rental property | `rental-deal-underwriting` → `passive-loss-eligibility` → `cost-segregation-screen` → `1031-exchange-modeling` when disposition is considered |
| Windfall | `windfall-management` → decision pause → `windfall-deployment-planner` → affected specialist reports → `conflict-check` |

Run `financial-scenario-planner` before a recommendation that materially
changes cash flow, liquidity, debt, or the balance sheet. Capture a truthful
baseline and later observations explicitly, then use `financial-history-review`
to identify changes and re-run `household-review`. `continuity-plan` is the
operational endpoint of the protection and estate chains, not a substitute for
their legal, coverage, and transfer analysis.

### History and scenarios are explicit

Normal skill runs remain read-only and never create history. Capture and compare
immutable local snapshots deliberately:

```bash
uv run scripts/history.py capture --facts inputs/facts.yml \
  --snapshot-id s2026-08-30 --effective-date 2026-08-30 \
  --observed-at 2026-08-31 --output history/2026-08-30.yml
uv run scripts/history.py calculate --snapshot history/2026-08-30.yml \
  --snapshot-id a2026-08-31 --calculated-at 2026-08-31 \
  --output history/2026-08-30.analysis.yml
uv run scripts/history.py compare history/2026-05-31.yml history/2026-08-30.yml
```

Point `history.snapshot_files` at those documents to run
`financial-history-review`. Existing dated Markdown can be entered manually as
a labeled lossy migration; it is never scraped automatically.

History-enabled skills also accept `--structured-output <path>` for explicit,
machine-readable metrics. That output is not captured implicitly, and both the
structured writer and snapshot writer refuse overwrite.

Record deterministic cases under `scenario_planning.scenarios`, then run:

```bash
uv run skills/financial-scenario-planner/run.py --facts inputs/facts.yml
uv run skills/job-loss-stress-test/run.py --facts inputs/facts.yml
uv run skills/windfall-deployment-planner/run.py --facts inputs/facts.yml
```

Scenarios never become facts, write results back, or execute an action.

**Step 2 writes a skeleton of nulls rather than copying the example
household.** Copying is one command and it is the wrong first move: every field
you never get to still holds an invented figure, and no skill can tell the
difference between a number you entered and one the example came with. A null
stops the skill and names the field; an invented number produces a confident
report.

**Step 4 is the one that saves the hour.** Sixty-five skills read a facts file
and nothing writes one, so the real onboarding cost is transcription.
`document-intake` makes it ordered and finite: it ranks the unset fields by how
many skills each one unblocks, and `household.members` alone is about thirty of
them.

Skills contain **procedures and thresholds**. Your facts file contains **values**. That split is
why the skills can be public while your data stays private — and why a skill is reviewable by
anyone without exposing anyone.

---

## Layout

```
skills/     the skills themselves
lib/        tested arithmetic — ratios, IRR, unit conversion
scripts/    setup, history and safety — doctor, init_facts, history, privacy_audit
inputs/     facts plus private, categorized source-document drop zones
documents/  legacy flat source-document drop zone; still scanned
outputs/    private reports, history views, scenarios, and structured results
history/    immutable local snapshots and analyses; gitignored
prompts/    private local task prompts and briefs; gitignored except its README
tests/      synthetic fixtures only
SCHEMA.md   the facts contract
```

**Arithmetic lives in `lib/`, not in prose.** A derived number restated in a document is a
number that will eventually disagree with its source. Ratios, real-vs-nominal conversion, and
expected-value calculations are code with tests so they cannot drift.

---

## Design principles

**State the jurisdiction.** Insurance and tax rules are state-specific. A skill that needs a
state rule and doesn't recognize yours says so instead of applying the one it knows.

**Label the basis of every figure.** An instant cash offer is not Actual Cash Value. A skill
that runs a premium-to-value test against the wrong basis gives a confidently wrong answer, so
the schema requires you to declare which you have.

**Insure what you cannot absorb.** The recurring question is not "is this coverage worth it on
expected value" — insurance is never EV-positive. It is "would this loss be survivable." Those
give opposite answers on cheap assets and catastrophic liability.

**Show the math.** Tables and derivations, not conclusions. Every figure should be checkable.

**Name the uncertainty.** Estimates are labeled as estimates. Unverified inputs are labeled
unverified. A skill that needs a number you don't have stops and asks.

---

## Not advice

This is analysis tooling, not licensed financial, tax, or legal advice. It shows reasoning so
you can check it and names what would change the answer. Rules vary by state and change over
time. Verify anything that matters against your actual policy documents and a qualified
professional.

---

## License

MIT
