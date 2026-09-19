# Adversarial Review

**Opened:** September 14, 2026 · **Updated:** September 19, 2026 · **Current scope:** 64 shipped skills

> A roadmap without a list of its own weaknesses is a wish list. This is the honest inventory.

Written at the point where the plan roughly doubled in one sitting. The question this asks is not
*"are these good skills"* — several are — but *"what is wrong with the thing as a whole, and what
would I regret in six months."*

Findings are ordered by consequence. The first two concern **already-shipped work** and outrank
every proposed cluster.

---

## A1 — Every shipped skill assumes a citizenship nobody ever asked about ⚠️ material · **CLOSED 2026-09-14**

**Not one of the 25 shipped skills, and not one of the nine analysis documents, mentions
citizenship, visa status, or domicile.** A grep for `citizen|green card|visa|domicile|QDOT`
across `lib/`, `skills/` and the private repo returns nothing.

Every conclusion therefore carries a silent assumption: that the household is a US citizen or
lawful permanent resident.

**The household this was validated against is neither** — a US tax resident by substantial
presence, holding non-US citizenship on a nonimmigrant visa. That is not an exotic case. It
describes a large share of US tech households, and the schema had no field for any of it.

### What that plausibly changes in work already shipped

| Area | The issue |
|---|---|
| **Estate** | The **unlimited marital deduction does not apply to a non-US-citizen spouse.** Transfers at death normally require a QDOT to defer tax. `07-ESTATE.md` was written without considering it |
| **Estate, again** | Estate-tax exposure turns on **domicile**, a facts-and-circumstances test distinct from income-tax residency. A US domiciliary gets the full exemption; a non-domiciliary gets **$60,000** against US-situs assets. Long residence in one metro with family and a pending petition points strongly at US domicile — but it is a determination, not an automatic |
| **Social Security** | **Totalization agreements do not cover every country pair** — India is one with no agreement in force. `social-security-timing` assumed a straightforward benefit; the coordination most expat analyses rely on cannot be presumed |
| **Survivor analysis** | `survivor-needs` and `life-insurance-review` size a gap without asking whether the survivor's immigration status survives the earner's death. For a dependent spouse on a derivative status, it may not |
| **Every retirement projection** | Assumes the household can remain in the US. A pending petition is not a guarantee |

**None of these is certainly wrong.** For an estate below the federal exemption, estate tax
probably does not bite *if domiciled*. The point is that **nothing in the system asked**, so
nobody knows which assumptions are load-bearing.

### Why it is a design defect, not a data gap

The schema requires `meta.jurisdiction.state` and refuses to proceed without it, because state
rules change conclusions. **Citizenship and domicile change conclusions at least as much and are
not in the schema at all.** The repository is more careful about which US state someone lives in
than about whether they are a US citizen.

**Fixed 2026-09-14.** `lib/pf/status.py` and `citizenship-status-review` added; `citizenship`,
`us_status` and `domicile` are in the schema. `estate-document-review` now checks for a QDOT and
flags an assumed domicile; `survivor-needs` and `life-insurance-review` state that their figure is
a need rather than a projection of what arrives; `social-security-timing` carries the totalization
table and records that **no US–India agreement exists**.

The facts file now records citizenship and immigration status explicitly, and carries
`domicile.determined: false` rather than an assumed answer.

**Residual:** the affected skills now *flag* the issue; none of them *re-computes* around it. The
survivor gap is still sized without modelling estate tax on a transfer to a non-citizen spouse.
That is the right stopping point for a skill — the QDOT question is for an attorney — but it
should not be mistaken for the arithmetic having been corrected.

---

## A2 — I asserted the household had no cross-border exposure without checking ⚠️ material · **CLOSED 2026-09-14**

Three times in this planning cycle I wrote that clusters 11 and 12 *"have no validation case —
the household is US-resident with no foreign income, no foreign accounts and no foreign
entity."*

**That was an assumption presented as a fact, and it was false.** A long-resident non-citizen
very likely holds accounts in their country of citizenship. If the aggregate exceeds **$10,000
at any point in a calendar year**, FBAR is already required, annually, with penalties that start
meaningful and escalate for wilfulness.

If any non-US pooled funds are held, PFIC treatment is live now — and an adjacent project in
the same workspace documents exactly that exposure. I read it during this cycle and still wrote
that there was none.

**This inverts the priority order I recommended.** `foreign-reporting-audit` may be the most
urgent unbuilt skill in the entire roadmap, not a speculative cluster-12 item. Compliance
obligations that already exist outrank planning for a move that has not happened.

**Class of error worth naming: reasoning from a persona rather than from the facts file.** The
household was mentally filed as "US tech W-2 earner", and every inference followed from the
label rather than from the data. The same error produced D13 in the private repo — a conclusion
reached by the first rule that came to hand.

**Confirmed and closed 2026-09-14.** Foreign accounts were confirmed to exist.
`foreign-reporting-audit` shipped, moved out of cluster 12 and built ahead of everything else on
the roadmap.

The facts file records the accounts with a **null** maximum rather than a guess, so the skill
reports FBAR as *unresolved* rather than as satisfied. That is the honest state: existence
confirmed, balances not pulled.

**Open, and it is the actual work:** pull the **peak** balance of every foreign account for every
year concerned, not the year-end figure. If any year's aggregate exceeded $10,000, that year's
FBAR was required at the time — and the remediation path depends on wilfulness, so that is a
conversation with a cross-border CPA before anything is filed.

---

## A3 — `limits.py` is becoming a tax-code mirror, and it is still unverified

Today it holds contribution limits and statutory ages, all marked `verified_on: unverified`.

The proposed clusters need it to also hold: federal marginal brackets, the standard deduction,
the FEIE cap, QBI thresholds and phase-outs, §179 limits, bonus depreciation rules, standard
mileage rates, ACA subsidy tables, IRMAA tiers, estate exemptions, and gift-tax annual
exclusions.

That is **a substantial fraction of an individual tax code**, hand-maintained by one person, in
one file, currently attested by nobody.

The failure mode compounds: one wrong bracket silently corrupts `feie-vs-ftc`,
`entity-structure-comparison`, `roth-conversion-window` and `aca-subsidy-optimization`
simultaneously, and each of those produces a confident dollar figure.

**The existing safeguards are not enough at this scale.** `reference-data-refresh` reports
staleness; it cannot report *wrongness*. A test asserts the current year is present; it cannot
assert the numbers in it are right.

**Partial progress 2026-09-14.** `reference-data-refresh --checklist` now generates a
verification checklist from the tables themselves — **201 asserted values across 21 tables**, each
with the authority's URL and a tick box. Generated rather than hand-written, so it cannot omit a
value added after it was written.

The count is quoted here as a figure that moves. It was 50 across six tables when the checklist
was built; five modules — `entity`, `healthcare`, `realestate`, `depreciation`, `presence` — were
asserting statutory values outside the generator and have since been registered. If that number
goes up without anyone ticking anything off, the gap is growing, which is the thing to watch.

That converts A3 from research into a few hours of checking. It does **not** close the finding:
nothing is verified until a human has actually done it and set `verified_on`. This is the one
finding in this document that cannot be closed by writing code.

**Options, none of them free:**

1. **Verify what exists before adding more.** Cheapest, already overdue, and the checklist now
   exists to make it mechanical.
2. **Sharply limit what goes in.** Anything not needed by a shipped skill stays out.
3. **Require year-specific rates as facts-file input** rather than repo data, as
   `pfic-divest-or-comply` already proposes for the interest-rate series. Pushes the burden onto
   the user, who is closer to the authoritative source anyway.
4. Accept the risk explicitly and say so in every affected report.

Doing none of these while adding fifteen dependent skills is the worst available choice.

---

## A4 — Cluster 14 reversed a boundary this file had already settled

Tax-loss harvesting was assigned to the portfolio tool early on, with the reason recorded:
lot-level positions and market data are out of scope, and two codebases holding two copies of one
threshold is the drift the whole project is organised around.

It reappeared as a proposed skill here. **Reshaped rather than accepted** — `wash-sale-policy`
sets the rule, the portfolio tool executes it — but the incident is worth logging, because a
boundary that erodes under repeated asking is not a boundary.

Worth noting the pattern: the erosion came from a new brief written without reference to the
existing decision, which is how most architectural boundaries actually fail.

---

## A5 — Two proposed skills already exist

`backdoor-roth-mechanics` and `mega-backdoor-audit` are both inside `contribution-space-audit`,
which raises the pro-rata trap on every backdoor contribution and checks the after-tax plus
in-plan-conversion route.

Minor, caught before building, and included here because it is the third instance this cycle of
a new brief proposing something already shipped. That is a **discoverability** problem: the
briefs are written without reading `README.md`, and at sixty-four skills that is understandable. It
argues for a one-line index of what each skill already covers, kept where a brief-writer would
find it.

---

## A6 — Two shipped skills actively contradict each other

`roth-conversion-window` (shipped) tells a household to deliberately raise taxable income in
early retirement, to fill low brackets before RMDs.

`aca-subsidy-optimization` (shipped) tells the same household to deliberately *suppress*
modified AGI in exactly those years, because premium subsidies taper and there is a cliff.

`medicare-enrollment-timing` (shipped) adds a third pull: IRMAA looks back two years, so
conversions at 63 raise premiums at 65.

For any household that reaches its retirement target before **65**, this is not hypothetical:
Medicare starts at 65, so the conversion window and the subsidy years are *the same years*. The
earlier the target is reached, the wider the overlap.

**The catching mechanism is now built, and this finding tracks whether it is used.** Each skill is individually correct.
`conflict-check` registers the contradiction as data rather than prose, and `household-review`
surfaces live ones in the ranked worklist. What remains is discipline, not design: a new skill
that contradicts a shipped one has to register the conflict, or the edge goes untracked again.
The roadmap's fuller conclusion-consistency idea — a validator comparing peer items
resolved by different rules — was proposed after D13 and never built; the registry is the
cheaper version that shipped.

**This is the strongest argument in this document for building fewer skills.** Each new one adds
edges, not just nodes.

---

## A7 — Nothing here has been used by anyone

Sixty-four skills, 3,118 passing tests, one household, zero external users. Every design decision has been
validated against a single set of facts and a single reader.

Several patterns that feel settled may simply be untested: reports are long, they are markdown to
stdout, the facts file is hand-maintained YAML, and the whole thing assumes an agent in the loop
to interpret. None of that has met a second person.

**Building 26 more before the first 25 meet a second household is speculative.** The
cheapest available information is one other person running `auto-insurance-review` and saying
what was confusing.

---

## A8 — Schema v1 has no size budget and no v2 plan

Every cluster adds sections. Clusters 10–18 would add roughly a dozen more, including a country
table, a pension-scheme table, travel logs, business entities, depreciation schedules and rental
properties.

`SCHEMA.md` is approaching the point where a new user cannot read it in one sitting, which is the
document's whole purpose — it is the contract a person fills in.

Nobody is tracking this. There is no modularisation, no per-cluster split, no v2 trigger. The
version rule says additive changes stay in v1, which is technically true and increasingly beside
the point.

---

## A9 — At sixty-four skills the "not advice" framing deserves a fresh look

Twenty-five skills covering insurance and savings reads as analysis tooling. Sixty covering tax
elections, estate structure, entity choice, charitable strategy, Medicare timing and portfolio
allocation reads like something else, and the distinction between *"showing a household the
arithmetic"* and *"providing financial planning"* is not purely a matter of adding a footer.

Not a legal opinion, and not a reason to stop. It is a reason to look at it deliberately — that
"at some point" is now — and the honest answer may simply be that the disclaimers
and the refusal-to-conclude discipline are already doing the work.

---

## A10 — History contained private facts but had only the ignore-rule guard ⚠️ material · **CLOSED 2026-09-19**

The new `history/` directory retains prior copies of account balances, income,
spending and analysis results. At discovery, `.gitignore` excluded it and
snapshot writes refused overwrite, but the local pre-commit hook that caught a
forced add checked only `inputs/`. `scripts/doctor.py` likewise inspected only
`inputs/` and `documents/`.

That leaves a specific escape hatch: `git add -f history/<snapshot>.yml` can
stage ordinary financial values that gitleaks does not recognize as secrets.
The token privacy pass helps only when its source includes the same old values;
a later facts file may not.

**Fixed 2026-09-19.** The staged-file hook now blocks private files under
`inputs/`, `outputs/`, and `history/`, while allowing their committed
scaffolds. The doctor checks the ignore rules and inspects all private-source
and generated-output locations for tracked files. Contract tests exercise both
the deny rules and the committed exceptions.

---

## A11 — Task prompts could bypass the root-only privacy rule ⚠️ material · **CLOSED 2026-09-19**

Implementation prompts routinely quote the household facts that exposed a
defect. The original ignore rules protected only `/*-prompt.md` and
`/*-brief.md`; placing the same artifact under `prompts/` made it a normal
untracked public file. Pattern scanning does not reliably recognize an exact
benefit, balance, or other identifying profile as private.

**Fixed 2026-09-19.** Prompt and brief artifacts are ignored at both locations,
the forced-add hook blocks them, and the doctor includes them in its tracked
private-file check. Existing local task prompts remain available to their owner
but are excluded from this commit.

---

## What I would actually do next

In order, and it is not the order the clusters are numbered in:

1. ~~**A1 — add citizenship and domicile to the schema, and audit the shipped skills against it.**~~
   **Done** — `citizenship-status-review` closed A1.
2. ~~**A2 — establish whether FBAR and PFIC obligations already exist.**~~ **Done** —
   confirmed, and `foreign-reporting-audit` tracks them.
3. **A3 — verify the existing `limits.py` entries** before anything depends on more of them.
   Still open, and still the only item here that no code can close.
4. ~~**Then cluster 10**, which has a real validation case and a live decision behind it.~~ **Shipped.**
5. ~~**Then cluster 16**, specifically `aca-subsidy-optimization` — and build the conflict
   detection from A6 alongside it rather than afterwards.~~ **Shipped, with `conflict-check`
   as the detection.**
6. Everything else on evidence of use.

---

*This document should be updated, not archived. A review that describes a past state of the
system stops being adversarial and becomes decoration.*
