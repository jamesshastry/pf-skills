# Reference-data automation

The `Reference data readiness` GitHub Actions workflow is a scheduled detector,
not an automatic tax-data updater. It runs the deterministic audit with
read-only repository permissions and never receives `inputs/facts.yml`.

## Schedule

The workflow runs every Monday at 15:17 UTC from the default branch:

- January through October: audit the current tax year.
- November and December: audit next-year readiness.

The unusual minute reduces the delay GitHub warns can affect jobs scheduled at
the top of an hour. Scheduled runs can still be delayed during busy periods.
GitHub may disable scheduled workflows in a public repository after prolonged
repository inactivity; the Actions page shows whether the schedule is active.

The strict audit fails when the selected annual entry is missing, stale, or
unverified. The Markdown audit is copied into the workflow run summary before
the job exits.

## Run it manually

In GitHub, open **Actions → Reference data readiness → Run workflow**. Leave
`target_year` blank to use the scheduled selection rule, or enter a four-digit
tax year.

The equivalent GitHub CLI commands are:

```bash
gh workflow run reference-data-refresh.yml
gh workflow run reference-data-refresh.yml -f target_year=2027
gh run list --workflow reference-data-refresh.yml --limit 10
gh run watch --exit-status
```

`gh run watch` without a run ID watches a selected recent run interactively;
pass the run ID shown by `gh run list` when scripting.

## Resolve a failed run

First reproduce the failure locally:

```bash
uv run skills/reference-data-refresh/run.py \
  --annual-only --target-year 2027 --strict
uv run skills/reference-data-refresh/run.py \
  --annual-only --target-year 2027 --checklist
```

Then invoke the `reference-data-refresh` skill. It should:

1. Open the primary authority—not a search-result snippet or secondary table.
2. Present the old/new/source/effective-date/consumer comparison table.
3. Leave an unpublished or conflicting value unresolved instead of carrying
   the prior year forward.
4. Append a complete year to versioned tables and preserve older years.
5. Set `verified_on` only after every active value was checked.
6. Run provenance plus affected-domain tests and submit a normal reviewed
   change.

The workflow does not scrape, edit, commit, open issues, or create pull
requests. Automating those mutations would turn an upstream correction or
parsing error directly into financial guidance without review.

## Audit private annual assumptions

Private tax brackets, household rates, deductions, marketplace premiums, and
other year-sensitive assumptions stay in the ignored facts file. They are
never available to GitHub Actions. Audit them locally:

```bash
uv run skills/reference-data-refresh/run.py \
  --facts inputs/facts.yml --annual-only --strict
```

Record `tax_year`, `verified_on`, and `sources` under
`assumptions.annual_parameter_metadata`. The report prints group status and
source counts, but not the underlying values or source descriptions.

## Security and notifications

The workflow declares `contents: read`, uses no repository secrets, and cannot
push. Keep branch-protection and Actions notifications enabled so a red
scheduled run is visible. Anyone with suitable repository permission can run
the manual workflow; the audit itself still has read-only permissions.
