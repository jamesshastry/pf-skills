# pf-skills Product Brief

## Overview

pf-skills is a local-first library of agent skills for personal-finance decisions — insurance
adequacy, tax-advantaged space, retirement drawdown, cross-border filing, estate documents,
real-estate underwriting. Each skill is a procedure plus a set of named thresholds. It reads a
YAML file the user owns, runs tested arithmetic from a small Python library, and prints a
markdown report to stdout.

There is no server, no account, and no network call. The repository is public; the numbers never
are. Fifty-five skill directories sit under `skills/`, backed by thirty-six modules under
`lib/pf/` and 2,591 passing tests. The work was built as eighteen thematic clusters plus several
cross-cutting ones, landed over twenty-four commits — one per cluster or piece of shared
infrastructure.

It has no external users. Every design decision so far has been validated against synthetic
fixtures and one privately held real-data set.

## Problem

Household financial decisions fail in a specific way: the arithmetic is easy and the framing is
hard. Whether an umbrella policy can attach above your auto limits, whether a Roth conversion in
a given year raises the MAGI a premium subsidy tapers against, whether a foreign mutual fund is
a PFIC — none of these need simulation. They need someone to ask the right question, apply a
rule that is written down, and say out loud when the rule does not cover your case.

The existing options each fail a different way. Spreadsheets restate derived figures in prose
until two copies of the same number disagree. Commercial tools want the data uploaded, which is
exactly the data a household is least willing to hand over. General-purpose LLM chat will answer
any of these questions confidently, including the ones where it has no basis — it will apply a
California insurance rule to a Texas household, or quote last year's contribution limit, with
the same tone it uses when it is right.

The failure that matters most is not being wrong. It is being confidently wrong about a number
that then travels: a misread statement becomes a recorded fact, and three reports later it is a
recommendation with nothing marking it as uncertain.

## Solution

Skills hold procedures and thresholds. The user's `inputs/facts.yml` holds values. That single
split is what makes the repository publishable — a skill is reviewable by anyone without
exposing anyone — and it is also what makes the reasoning auditable, because every threshold is
a module-level constant with a comment giving its reason rather than a number buried in prose.

A skill declares the dotted field paths it needs. If one is missing, it stops and names the
field rather than substituting a default. Arithmetic lives in `lib/pf/` with unit tests, never
restated in the markdown. Statutory and jurisdictional data lives in cited tables keyed by year
or state; anything outside the table returns `UNKNOWN` and the report says so.

The whole thing is driven by `uv run`. Every runner carries PEP 723 inline script metadata
declaring its dependencies, so there is no install step, no virtualenv, and no lockfile to keep
current. `scripts/doctor.py` checks the environment, `scripts/init_facts.py` writes a skeleton
of nulls, and `scripts/privacy_audit.py` scans the working tree and full git history for values
that should not have been committed.

## Target Users

**A technically literate household running an AI coding agent locally.** The primary user reads
Python, is comfortable hand-editing YAML, and wants the derivation rather than the conclusion.
They have documents — policies, statements, returns — and no interest in uploading them.

**The agent itself is the second user, and arguably the closer one.** Skill descriptions are
written to be routed on: 120–1024 characters, each containing an explicit "Use when …" clause.
The intended loop is that the agent runs `document-intake`, reads the documents, *proposes*
values, the human confirms them into the facts file, and then the agent runs the relevant skills
and explains the output.

**A contributor adding a skill** is a third audience. `CONTRIBUTING.md` documents the house style
as four files per skill; a contract test suite enforces most of it mechanically.

## Product Decisions

**Refuse rather than guess.** A missing field produces a clean stop listing what is missing. A
guessed number inside a recommendation is worse than a gap, because a gap is visible.

**Null is not zero.** `null` means nobody looked. Treating it as zero yields a confident answer
that is wrong in the direction of inaction — the report says "cannot be determined" instead.
`scripts/init_facts.py` writes a skeleton of nulls rather than copying the example household for
exactly this reason: a field you never reached still holds an invented figure, and nothing
downstream can distinguish it from one you entered.

**State the basis of every figure.** Real or nominal, gross or after-tax, Actual Cash Value or
an instant cash offer. Mixing bases caused four separate defects here, so the schema requires the
basis to be declared and a test enforces that every vehicle carries one.

**Import, never restate.** A figure computed in two places eventually disagrees with itself.
Shared thresholds are imported across modules rather than redefined.

**Cited jurisdiction tables that return UNKNOWN rather than reasoning by analogy.** A state is in
`lib/pf/jurisdiction.py` only if the rule was checked against that state's insurance code, with a
source and a `verified_on` date. An unsourced entry is worse than an absent one, because absence
is visible. The same discipline covers statutory limits by year and country-level treatment of
retirement accounts.

**Measure completeness in runnable skills, not fields filled.** The schema has several hundred
fields and nobody fills all of them; a percentage against the schema is discouraging and
meaningless. `document-intake` instead ranks unset fields by how many skills each one unblocks —
`household.members` alone unblocks roughly thirty — so the ordering falls out of the data.

**A conflict registry that catches contradictions between skills.** Each skill is individually
correct, and some of them give the same household opposite instructions. `conflict-check` reads a
declared registry in `lib/pf/conflicts.py` rather than having skills cross-import each other,
because a full dependency graph between fifty-plus skills is not reasonable to reason about. The
canonical case: filling low tax brackets with Roth conversions raises the MAGI that ACA premium
subsidies taper against, and IRMAA looks back two years on top of that. For a household retiring
before 65, those are the same years, and nothing in either single report would tell you.

**A test designed to go red.** `test_the_current_year_is_present_in_the_limits_table` fails when
the calendar rolls past the last year `lib/pf/limits.py` covers. That is a maintenance signal,
not a bug — a stale statutory limit gets quoted confidently and believed.

## Architecture

Four files per skill:

```
lib/pf/<module>.py        tested arithmetic and named thresholds
skills/<name>/SKILL.md    frontmatter + how to read the report
skills/<name>/run.py      thin renderer over cli.run()
tests/test_<module>.py    unit tests on the module
```

`lib/pf/facts.py` loads and validates the facts file against the schema version and resolves
dotted paths. `lib/pf/cli.py` is the shared runner: parse `--facts`, load, check required paths,
stop cleanly if any are missing, otherwise hand a `Writer` to the skill's `build()`. Modules
return dataclasses with a `findings` list, never formatted report strings. No module reads the
system clock — dates come from `meta.as_of` in the facts file, which is what makes output
deterministic and golden-testable.

Reference data is segregated from reasoning. `limits.py`, `jurisdiction.py` and the country and
statutory tables in `crossborder.py`, `healthcare.py`, `expat.py` and others register themselves
with `lib/pf/provenance.py`, which knows when each was last checked and can emit a verification
checklist generated from the tables rather than hand-written — currently 201 asserted values
across 21 tables.

Testing runs in two layers. Unit tests cover each branch, threshold boundary and refusal path.
Above them, `tests/skill_harness.py` discovers every skill and a generated suite asserts the
contract: frontmatter `name` matches the directory, the description is long enough and says when
to use it, declared `requires` matches the runner's `REQUIRED`, the runner uses `cli.run()` and
declares dependencies inline, every required path resolves in the example fixture, the skill is
listed in `README.md` and `ROADMAP.md`, output is deterministic against a golden fixture, a
missing field stops without a traceback, and nothing goes to stderr on success. Two skills —
`document-intake` and `reference-data-refresh` — take no `--facts` and are excluded from the
household-skill checks by name, with the reason recorded in the harness. The other fifty-three
each have a golden fixture.

Privacy is enforced structurally rather than by care. `.gitignore` excludes everything in
`inputs/`, `documents/` and `outputs/` except the example and the READMEs; a pre-commit hook runs
gitleaks and a local hook that blocks any non-example file staged from `inputs/`, because
`git add -f` exists and a mistyped ignore rule fails silently; a contract test asserts the
example fixture is the only one committed.

## Design System

**There is no GUI.** No web app, no TUI, no charts. The product surface is a command line, a text
file, and markdown on stdout — and the consistency work went there instead.

The *report* is the design system. `cli.Writer` offers exactly two operations: `w("text")`
appends a line and `w.table(header, rows)` writes a markdown table. Nothing else. Every report
opens with a title, shows derivations as tables rather than asserting conclusions, names its
weakest input explicitly, labels estimates as estimates and unverified figures as unverified,
attaches dates to findings that expire, and closes with a disclaimer pointing at the module that
holds its thresholds so a reader can go argue with the constant. Tests enforce the title, the
disclaimer, the absence of unrendered placeholders, and determinism.

The *refusal* is designed as carefully as the report: a missing-field stop names each field
once, exits non-zero, and never produces a traceback. Behaviour tests cover the missing file, the
wrong schema version and the incomplete file separately.

The *agent-facing interface* is the SKILL.md frontmatter: `name`, a routing description
constrained to 120–1024 characters containing "Use when …", and a `requires` list of dotted paths
that must match the runner. `SCHEMA.md` is the human-facing half of the same contract, and a
coverage test asserts that every section in the example is documented and every documented
section appears in the example.

Prose style is specified in `CONTRIBUTING.md`: analytical, specific, willing to state
uncertainty, no hedging where the arithmetic is clear.

## Current Capabilities

Fifty-five skills run today. Fifty-three read a facts file and cover property and casualty,
income protection, beneficiaries and estate, tax-advantaged space, cash and debt, concentration,
retirement adequacy, housing, education, cross-border planning, expat tax filing, offshore assets
and pensions, owner-operator business entities, portfolio policy, charitable giving, healthcare
and aging, life transitions, and real-estate investing — plus a cross-cutting citizenship,
immigration-status and domicile review, and `conflict-check` over the registry of contradictions.
Two run without a facts file: `document-intake`, which builds the onboarding worklist from what
is in `documents/`, and `reference-data-refresh`, which reports on the staleness of the
repository's own tables and generates the verification checklist.

Supporting all of it: the schema contract in `SCHEMA.md`, a fictional example household (the
Riveras, Austin TX) as the committed fixture, three setup and safety scripts, gitleaks plus a
local pre-commit hook, and 2,591 passing tests.

`REVIEW.md` is the standing inventory of what is wrong, and it is worth reading as part of the
capability statement rather than against it. The 201 asserted reference values are generated,
cited and checkable — but not yet verified by a human, so every figure derived from them is
provisional. Clusters 10 and onward shipped without a real-data validation case, because the
validation set does not exercise foreign earned income, business ownership or investment
property; the roadmap predicted that rather than discovering it. And nothing here has been used
by a second household.

## Roadmap

**Verify the reference tables.** Work the generated checklist and set `verified_on`. This is the
one open finding that writing code cannot close, and it gates the credibility of every dollar
figure in the tax-heavy clusters.

**Get it in front of a second household.** The cheapest available information is one other
person running a skill and saying what was confusing. Report length, markdown-to-stdout, and
hand-maintained YAML all currently feel settled and are simply untested.

**Detect a private facts file drifting ahead of the public schema.** Two shipped defects were
found by a household doing the analysis by hand and the skill being unable to express it. A check
that reads a facts file and reports fields no skill consumes would have caught them in one run.

**Decide whether `SCHEMA.md` needs a v2 or a modular split.** It is approaching the point where a
new user cannot read it in one sitting, which defeats its purpose as the contract someone fills
in.

**Re-examine the "not advice" framing at this size.** Fifty-plus skills covering tax elections,
entity structure, Medicare timing and portfolio allocation reads differently from twenty-five
covering insurance, and the disclaimer footer may not be carrying the weight alone.

Explicitly out of scope and staying there: budgeting and expense tracking, rate shopping,
investment selection, crypto, anything needing live market data, and anything needing lot-level
positions. The seam with a portfolio tool is deliberate — pf-skills answers "should I, and how
much"; a portfolio system answers "which lots, and when."

## My Role

Sole author. I designed the product, wrote every skill, module, test and document, and made the
architectural calls: the procedures-versus-values split, the refusal discipline, cited tables
over inferred ones, the conflict registry instead of cross-imports, and the decision to
reimplement retirement projection simply rather than take a heavy modelling dependency — a
transparent 3×3 sensitivity grid rather than a single number from a black box.

The part I would point at is the review discipline rather than the feature count. `REVIEW.md`
records findings against my own shipped work, including two cases where I asserted something
about the validation data without checking it, and names the class of error — reasoning from a
persona rather than from the facts file. `ROADMAP.md` carries a "Found in use" section listing
defects the synthetic fixtures could not have caught, and a "Deliberately not planned" list that
has held up under repeated pressure to widen scope. One boundary did erode and I logged the
erosion, because a boundary that gives way under repeated asking is not a boundary.

## Portfolio Summary

pf-skills is a local-first library of 55 agent skills for household financial decisions, built on
36 tested Python modules with 2,591 passing tests and zero network dependencies. Its organising
idea is that skills hold procedures and thresholds while the user's own gitignored file holds
values — which is what allows the reasoning to be public and reviewable while the data never
leaves the machine. The engineering interest is in what the system refuses to do: it stops and
names a missing field rather than defaulting, returns `UNKNOWN` outside its cited jurisdiction
tables rather than reasoning by analogy, and runs a registry that flags where two individually
correct skills give the same household opposite instructions. It has no external users, and its
standing adversarial review says so in the first paragraph.

---
Created: 2026-09-15
Last updated: 2026-09-15
