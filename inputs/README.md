# inputs/

**`facts.example.yml`** — a synthetic household. Committed. Every figure is invented.

**`facts.yml`** — yours. Gitignored. Never committed, never transmitted.

```bash
uv run scripts/init_facts.py
```

This writes a short skeleton of nulls. Add only fields you have actually
verified; use `facts.example.yml` to learn the shape, not as a starting set of
values. See [`../SCHEMA.md`](../SCHEMA.md).

Year-sensitive assumptions remain private but should carry non-value
provenance under `assumptions.annual_parameter_metadata`. Audit them locally;
the report shows group status and source counts without printing the values:

```bash
uv run skills/reference-data-refresh/run.py \
  --facts inputs/facts.yml --annual-only --strict
```

This file is never supplied to the scheduled GitHub reference-data check.

---

Two guards keep real data out of git: deny-all ignore rules, and a pre-commit
hook that blocks private files staged from this directory. Both exist because
`git add -f` is one keystroke away and a mistyped ignore rule fails silently.

## Source-document scaffold

Put source files in the closest category. The directories are committed, but
their contents are ignored. `document-intake` scans all of them recursively;
it displays the relative path and uses the category plus filename as hints.

```text
inputs/
├── banking/       checking, savings, money-market statements
├── investments/   brokerage and taxable portfolio statements
├── retirement/    401(k), IRA, HSA, pension, and Social Security records
├── insurance/     auto, home, umbrella, life, and disability policies
├── income/        pay statements and compensation summaries
├── debts/         cards, mortgages, student loans, and other liabilities
├── tax/           returns, W-2s, 1099s, and supporting schedules
├── property/      leases, closing packages, HOA, comps, and rental records
├── estate/        wills, trusts, directives, powers, and designations
├── education/     tuition, aid, and education-account records
├── healthcare/    coverage, Medicare, and long-term-care records
├── business/      entity, payroll, and owner-operator records
├── cross-border/  foreign accounts, pensions, travel, and filings
└── life-events/   marriage, divorce, inheritance, and other transitions
```

Anything, any format, any filename works. Prefer neutral filenames such as
`auto-policy-2026.pdf`; gitignore does not protect filenames shown in a screen
share, terminal recording, or support ticket.

```bash
cp ~/Downloads/checking.pdf inputs/banking/
cp ~/Downloads/brokerage.pdf inputs/investments/
cp ~/Downloads/auto-policy.pdf inputs/insurance/
uv run skills/document-intake/run.py
```

The former flat `documents/` drop zone remains supported for compatibility,
but categorized inputs are the recommended layout.

Put MLS sheets, appraisal extracts, and other comparable-sale evidence under
`inputs/property/evaluations/`. That nested directory does not need its own
ignore rule: the deny-all `inputs/property/.gitignore` already protects every
file and subdirectory beneath it.

When `home-offer-strategy` uses public-web research, only the minimum property
search terms should leave the machine. The agent must not upload files from
this directory or send household financial facts to a listing service.

If you keep several independent household data sets, name them anything except
`*.example.yml`:

```
facts.yml
facts.household-two.yml
```

All are ignored.

What-if cases normally belong inside one facts file under
`scenario_planning.scenarios`, where they can share and reconcile against the
named baselines in `cash_flow.scenarios`. A scenario is not a second set of
facts and no scenario runner writes back to this directory.

## History is private too

Explicit snapshots live under `../history/`, not here. They retain old copies
of the same private facts and are gitignored. Start with the first supportable
observation rather than inventing a back history, never force-add snapshots,
and select the files for review with local paths:

```yaml
history:
  snapshot_files:
    - history/2026-08-30.yml
    - history/2026-11-30.yml
```

See the [history and scenario schema](../SCHEMA.md#history--immutable-local-snapshots)
and the [quickstart](../QUICKSTART.md#9-start-a-history-only-when-you-have-a-truthful-observation-optional).
