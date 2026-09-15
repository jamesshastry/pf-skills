# Tests

Two layers, and they catch different things.

## `lib/` unit tests — is the arithmetic right?

`test_auto.py`, `test_property.py`, `test_umbrella.py`, `test_income_protection.py`,
`test_estate.py`, `test_contributions.py`, `test_cash_debt.py`, `test_concentration.py`,
`test_retirement.py`, `test_housing.py`, `test_facts.py`, `test_provenance.py`

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
```

The skill tests spawn a subprocess per skill, so they are slower than the unit tests. Nothing is
marked slow — it is still around twenty seconds for the lot.

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

## Adding a skill

The suite will tell you what is missing, in roughly this order:

1. `SKILL.md` and `run.py` exist; frontmatter `name` matches the directory
2. Description is long enough and says *when* to use it
3. `requires` matches the runner's `REQUIRED`
4. The runner uses `cli.run()` so the stop-behaviour matches every other skill
5. Every required path resolves in `inputs/facts.example.yml`
6. The skill is listed in `README.md` and `ROADMAP.md`
7. A golden fixture exists

None of that needs to be remembered — the failures name the fix.
