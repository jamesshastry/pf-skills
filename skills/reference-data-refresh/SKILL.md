---
name: reference-data-refresh
description: Audit and refresh versioned statutory tables and the provenance metadata for year-sensitive assumptions in a private facts file. Use before a new tax year, after a law or published limit changes, when a skill reports UNKNOWN, or when the scheduled reference-data check fails. Researches authoritative public sources and prepares reviewed changes without uploading household data.
requires: []
---

# Reference data refresh

## What this is for

Most skills here encode **reasoning**, which does not expire. The provenance
registry currently covers statutory and jurisdictional tables across 21 areas;
those outside-world facts do expire. A second class of annual values remains in
the private facts file because it is tax-year, jurisdiction, or household
specific.

| Class | Examples | Changes |
|---|---|---|
| Versioned repository table | contribution limits, statutory ages, reporting and insurance rules | Annually or legislatively |
| Private annual assumption | tax brackets, deductions, QBI and depreciation limits, FPL and IRMAA | Annually |
| Private periodic series | IRS underpayment rates | Quarterly |
| Household estimate | marginal/state rates, deductions, ACA benchmark premium | Annually or when facts change |

A stale entry here is worse than a missing one, because it will be quoted
confidently and believed. This skill is the maintenance procedure that keeps
them honest.

## Audit modes

```bash
uv run skills/reference-data-refresh/run.py              # what is stale or unverified
uv run skills/reference-data-refresh/run.py --checklist  # every value, to go and check
uv run skills/reference-data-refresh/run.py --annual-only --scheduled --strict
uv run skills/reference-data-refresh/run.py --annual-only --target-year 2027
uv run skills/reference-data-refresh/run.py --annual-only --target-year 2027 --strict
uv run skills/reference-data-refresh/run.py --facts inputs/facts.yml --annual-only --strict
```

The first two take no `--facts` — they inspect the repository, not a household.
`--target-year` can test next-year readiness before January. `--annual-only`
keeps that check focused on year-keyed repository data. `--strict` makes stale
or unverified entries fail, not just missing-year blockers.

With `--facts`, the report also checks
`assumptions.annual_parameter_metadata` and reports **schema drift**. It prints
group status and source counts, never private parameter values. Schema drift is
advisory; incomplete annual metadata fails only with `--strict`.

Read [references/annual-tax-parameters.md](references/annual-tax-parameters.md)
when refreshing tax-year data. It defines which values belong in versioned
code versus private facts, the required source hierarchy, and the old/new
review table.

**The checklist is generated from the tables**, not hand-written, so it cannot
omit a value that was added later. That matters: a verification checklist which
silently misses the field somebody added last month is worse than none, because
it certifies a table it never examined.

## The forcing function

`tests/test_provenance.py::test_the_current_year_is_present_in_the_limits_table`
**is designed to fail eventually.** When the calendar rolls into a year the
table doesn't cover, the build goes red.

That is the mechanism, and it's deliberately a hard failure rather than a
warning — a warning in a test suite is a warning nobody reads. The skills
themselves degrade safely, returning `UNKNOWN` and refusing to answer, so a red
build here is a maintenance signal rather than a functional break.

The scheduled GitHub workflow runs the same strict annual check. It checks the
current year through October and the next year during November and December,
publishes the audit in the job summary, and has read-only permissions. It does
not invoke an agent, scrape authorities, edit files, open a pull request, or
receive household facts. A failure is the trigger to run this skill.

## Procedure

**1. Select the target year and ownership boundary.** Run the audit first.
Repository tables and private assumptions have different owners; do not move a
household-specific rate into a global default for convenience.

**2. Find the authoritative source.** For limits, use the IRS annual
cost-of-living adjustment notice—not a summary article, financial-media table,
or recollection. For state rules, use the state insurance code or department's
own guidance. For the full annual tax process, follow the linked reference.

**3. Transcribe every field for the year.** All of them:

```
elective_deferral · catch_up_50 · catch_up_60_63 · total_additions
compensation_limit · ira_contribution · ira_catch_up
hsa_self_only · hsa_family · hsa_catch_up_55
```

**A partially filled year is worse than a missing one.** A missing year makes
every skill refuse to answer; a half-filled year makes them answer wrongly.
`test_known_years_are_fully_populated` enforces this — don't work around it.

**4. Set `source` and `verified_on`.** `verified_on` is an ISO date and means
*a human compared this against the authority on that date*. It is not the date
you edited the file. If you transcribed without checking, leave it as
`unverified` — that is an honest state and the report handles it.

**5. Do not delete old years.** They're needed to re-run a prior year's review
and to reconcile a historical decision.

**6. Show the old/new/source/affected-skills table, then run focused tests.** A
change is ready only after each consuming skill is identified and re-run. Use
the full suite before merging a broad statutory change.

## Rules for this table specifically

**Never carry a value forward.** If you can't find this year's figure for one
field, the year is not ready. Do not copy last year's and intend to fix it —
that is precisely the failure mode being defended against, and it leaves no
trace.

**Never infer from a percentage change.** Several of these are rounded to
different increments and don't move together.

**Watch for structural changes, not just amounts.** The SECURE 2.0 enhanced
catch-up for ages 60–63 *replaces* the age-50 amount rather than stacking on
it. New provisions phase in on their own schedules, and a purely numeric
refresh will miss a change in how a limit works. If the shape changed, the
dataclass may need a field, not just a value.

## When a state rule changes

Same discipline, one addition: **check whether the change is retroactive or
prospective, and whether existing policies are grandfathered.** An insurance
minimum that rose last year may not apply to a policy written before it.

Only add a state you have actually checked. `UNKNOWN` is a good answer — the
skills handle it by saying so, which is far better than a plausible wrong rule.

## Closing

1. **What changed, field by field**, with the old and new values.
2. **Whether any shipped conclusion moves.** A changed limit can alter an
   earlier recommendation; re-run the affected skills rather than assuming.
3. **The `verified_on` dates you set**, and honestly whether you checked or
   transcribed.

---

*Not financial or tax advice. This skill maintains the tables; it does not
vouch for them.*
