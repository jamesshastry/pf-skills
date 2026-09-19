# Contributing a skill

The house style, written down because it was previously only in the existing skills. Read this
plus one exemplar — `skills/cash-yield-review/` is the best — before writing anything.

---

## What earns a place

A skill exists when **there is a decision, and a defensible rule for it.** The filter from
`ROADMAP.md`:

| Test | Why |
|---|---|
| There is a **decision**, and a rule for it | Otherwise it is a report, not a skill |
| The rule can be **wrong in a specific way** | "Review your insurance" is not a rule |
| The arithmetic fits in **tested code** | Prose restatement is how figures drift |
| The **schema slice is small** | A skill needing twenty new fields is three skills |

A skill that produces a number without a decision attached is out of scope.

---

## The four files

```
lib/pf/<module>.py          tested arithmetic + named thresholds
skills/<name>/SKILL.md      frontmatter + how to interpret the report
skills/<name>/run.py        thin renderer, uses cli.run()
tests/test_<module>.py      unit tests on the module
```

### `lib/pf/<module>.py`

- **Every threshold is a module-level constant with a `#:` comment giving its reason.** If
  someone disagrees, they change the constant — they do not argue with the output.
- Functions return **structured results** (dataclasses with a `findings: list[str]`), never
  formatted strings for the whole report.
- Module docstring states **the one idea** the module exists to encode, and what it refuses.
- **Never** read the clock. Dates come from `meta.as_of` via the caller.
- Import shared thresholds rather than redefining them. `auto.py` imports `MIN_BUFFER_MONTHS`
  from `cash.py`; two copies drift.

### `skills/<name>/run.py`

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""One line on what this renders."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, <module> as M  # noqa: E402

REQUIRED = ["household.members", "..."]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    ...
    cli.disclaimer(w, "lib/pf/<module>.py")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Title Case", required=REQUIRED, build=build))
```

`w()` appends a line, `w.table(header, rows)` writes a markdown table. Nothing else.

### Adding a comparable history metric

Do not add storage or history parsing to the skill. Add a small adapter to
`lib/pf/skill_metrics.py` that calls the same domain function as the runner,
returns `timeseries.MetricObservation` values with stable IDs and explicit
clock/scenario/unit/currency/basis, and register it in `skill_metrics.ADAPTERS`.
Then attach it without changing Markdown:

```python
w.add_metrics(SM.emit("skill-name", data))
cli.run(..., skill_id="skill-name")
```

This enables the explicit `--structured-output` channel. Snapshot storage,
restatements and comparisons remain owned by `lib/pf/timeseries.py` and
`scripts/history.py`; a domain skill must not create history as a side effect.

The Markdown and structured paths must call the same calculation. Add focused
coverage in `tests/test_time_scenario_reports.py`, and prove the ordinary report
did not move with `tests/test_skill_golden.py`. Structured-output and snapshot
files refuse overwrite; do not weaken that property in a convenience wrapper.

### Adding a scenario event or focused scenario skill

Extend the typed event vocabulary in `lib/pf/scenario.py`; do not accept an
executable expression or an unvalidated generic map. Assign the event to one
documented same-month phase, define its cash, asset, debt, retirement and net
worth effects, and add an ambiguity check anywhere two individually valid
events could double count the same economic action.

A focused skill such as `job-loss-stress-test` must remain a thin view over the
shared engine. It may impose stricter required facts or surface domain-specific
unknowns, but it must not fork the cash-flow calculation. Never infer taxes,
liquidation, spending cuts, refinancing, market returns, or probabilities.
Scenarios are projections: they do not mutate facts or become observed history.

Pin engine behavior in `tests/test_scenario.py` and report behavior in
`tests/test_time_scenario_reports.py`. Include a reconciliation invariant and
an intra-period failure case; a recovered ending balance must not hide an
earlier cash breach.

### `skills/<name>/SKILL.md`

```markdown
---
name: <must match the directory>
description: <120-1024 chars, and must contain "Use when ..." — this is what an agent routes on>
requires:
  - dotted.paths          # must match run.py's REQUIRED
---

# Title

## The idea
## <the decision rule>
## What it will not do
## Closing

*Not financial, tax, or legal advice.*
```

---

## Non-negotiables, each learned from a defect

**Refuse rather than guess.** A missing field produces a clean stop listing what is missing,
never a default. A guessed number in a recommendation is worse than a gap.

**Unknown is not zero.** `null` means nobody looked. Treating it as zero produces a confident
answer that is wrong in the direction of inaction. Say "cannot be determined".

**State the basis.** Real or nominal, gross or after-tax, ACV or instant offer. Mixing bases has
caused four separate defects here. If a module is real throughout, say so in the docstring; if
nominal, say that and say why.

**Import, never restate.** A figure computed in two places eventually disagrees with itself.

**Jurisdiction and statutory data go in a cited table.** A country or state is in the table only
if checked, with `source` and `verified_on`. Everything else returns `UNKNOWN` and the skill says
so — **never reason by analogy from a jurisdiction you do know.** Register the table with
`provenance.py`, exposing every asserted value so it appears on the verification checklist.

**Name the weakest input.** Every skill has one. Say which it is in the report.

**Findings that expire carry a date.** Use `facts.deadline()`.

---

## Fixtures must exercise both branches

`inputs/facts.example.yml` is the Rivera household — fictional, Austin TX. A fixture that only
exercises one outcome hides the boundary: the auto fixture has a keep case *and* a drop case,
and the drop case only appeared after the first version produced identical answers either way.

Add a comment above each case saying which branch it exercises.

---

## Tests

Two layers, both required.

**Unit tests** on the module — pure functions, synthetic data, no subprocesses. Cover each
branch, each threshold boundary, and each refusal path.

**Contract and behaviour tests run automatically** over every skill and will tell you what is
missing:

- frontmatter `name` matches the directory
- description is 120–1024 chars and says *when* to use it
- `requires` matches `run.py`'s `REQUIRED`
- the runner uses `cli.run()`
- every required path resolves in the example fixture
- the skill is listed in `README.md` and `ROADMAP.md`
- a golden fixture exists
- output is deterministic and contains no unrendered placeholders

```bash
uv run --with pytest --with pyyaml pytest tests/ -q
PF_UPDATE_GOLDEN=1 uv run --with pytest --with pyyaml pytest tests/test_skill_golden.py
```

**Read the golden diff.** Refreshing fixtures without reading the diff turns a review signal into
a rubber stamp.

---

## Tone

Analytical, specific, and willing to say what is uncertain. Show the derivation, not just the
conclusion. Name what would change the answer. No hedging where the arithmetic is clear, no false
precision where it is not.

The reader is technically able and wants reasoning rather than reassurance.
