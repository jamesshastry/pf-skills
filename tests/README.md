# Tests

Two layers, and they catch different things.

## `lib/` unit tests — is the arithmetic right?

Examples include the insurance, cash, cash-flow, retirement, housing,
cross-border, real-estate, history, and scenario modules. `test_cashflow.py`
pins income, explicit-rule tax estimates, and annual cash reconciliation;
`test_timeseries.py` pins clock and comparability rules; `test_scenario.py` pins
monthly cash reconciliation and typed event semantics;
`test_housing_affordability.py` pins the distinct cash, lender, savings, and
occupancy constraints.

Pure functions, synthetic fixtures, no subprocesses. These are where thresholds and
derivations are pinned.

## Skill tests — is it actually a working skill?

Everything above tests `pf.*`. None of it touches the thing a user runs. These do:

| Module | Asks |
|---|---|
| `test_skill_contract.py` | Is it shaped like a skill? Frontmatter, naming, and **does `SKILL.md` declare what `run.py` enforces?** |
| `test_skill_behaviour.py` | Does it run, stop cleanly on missing facts, and produce the same output twice? |
| `test_skill_golden.py` | Has the report changed without anyone deciding it should? |
| `test_schema_coverage.py` | Do `SCHEMA.md`, the example, and the skills' `requires` agree? |
| `test_time_scenario_reports.py` | Do history/scenario reports preserve gaps, clocks, intra-period failures, and explicit structured-output behavior? |
| `test_tax_planning.py` | Does filed-return history remain distinct from payments, and are tax opportunities quantified without hiding their tradeoffs? |
| `test_housing_affordability_report.py` | Does the report keep affordability, economic cost, sources/uses, and transition phases distinct? |
| `test_privacy_audit.py` | Does the audit include nonignored untracked public files? |

`skill_harness.py` holds the discovery and subprocess plumbing.

### The three that earn their place

**The requires-drift check.** `SKILL.md` frontmatter advertises inputs; `run.py`'s `REQUIRED`
list is what actually stops execution. Nothing else keeps them in step, and a skill advertising a
field it never checks will happily build a report on a silently missing input.

**Stop-cleanly.** Every household skill is run against a nearly empty facts file and must exit 1,
name what is missing, and not produce a traceback. That is the state every new user starts in,
and it was completely untested.

**Determinism.** Household reports must take dates from `meta.as_of`, never the clock. A report
that changes overnight cannot be diffed or reviewed. There is also a source check for
`date.today()` in household runners.

## Running

```bash
uv run --with pytest --with pyyaml pytest tests/ -q      # everything
uv run --with pytest --with pyyaml pytest tests/test_skill_contract.py -q

# Focused history and scenario checks
uv run --with pytest --with pyyaml pytest -q \
  tests/test_timeseries.py tests/test_scenario.py \
  tests/test_time_scenario_reports.py

# Focused housing-affordability checks
uv run --with pytest --with pyyaml pytest -q \
  tests/test_housing_affordability.py \
  tests/test_housing_affordability_report.py

# Focused annual cash-flow checks
uv run --with pytest --with pyyaml pytest tests/test_cashflow.py -q
```

The skill tests spawn a subprocess per skill, so they are slower than the unit
tests. Prefer a focused module while iterating, then run the full suite before
hand-off.

## Golden fixtures

`tests/golden/<skill>.md` holds each household skill's full report against the example fixture,
with dates normalised. To update after an intended change:

```bash
PF_UPDATE_GOLDEN=1 uv run --with pytest --with pyyaml pytest tests/test_skill_golden.py
```

**Then read the diff.** Refreshing goldens without reading the diff converts a review signal into
a rubber stamp, which is worse than not having them.

`reference-data-refresh` has no golden fixture: it reports on the repository as of today, so its
output legitimately changes with the calendar.

Synthetic history documents live in `tests/fixtures/history/`. Observed,
analysis, and restatement documents are separate on purpose; do not collapse
them to make a fixture shorter. The scenario examples remain in
`inputs/facts.example.yml`, and every amount there is fictional.

## Structured metric adapters

Skills that participate in history call the shared domain calculation once,
attach `MetricObservation` values to `cli.Writer`, and expose them only through
`--structured-output`. Add or change an adapter with focused coverage in
`test_time_scenario_reports.py`, then run `test_skill_golden.py` to prove the
ordinary Markdown stayed stable. Both snapshot and structured-output writers
must refuse overwrite.

## Adding a skill

The suite will tell you what is missing, in roughly this order:

1. `SKILL.md` and `run.py` exist; frontmatter `name` matches the directory
2. Description is long enough and says *when* to use it
3. `requires` matches the runner's `REQUIRED`
4. The runner uses `cli.run()` so the stop-behaviour matches every other skill
5. Every required path resolves in `inputs/facts.example.yml`
6. The skill is listed in `README.md` and `ROADMAP.md`
7. A golden fixture exists

If the skill emits comparable history metrics, it also needs a registered
adapter in `lib/pf/skill_metrics.py` and explicit clock, scenario, unit,
currency, basis, stable entity ID, and dimensions. If it adds a scenario event,
extend the typed parser, deterministic phase ordering, ambiguity checks, and
both engine and report tests together.

None of that needs to be remembered — the failures name the fix.
