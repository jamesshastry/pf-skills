---
name: reference-data-refresh
description: Refresh the repository's own reference tables when the rules change — statutory contribution limits that change annually, and state insurance rules that change on legislative timescales. Use at the start of a calendar year, when a limit or law is known to have changed, when a skill reports UNKNOWN for the current year, or when the provenance test fails. With --facts it also reports schema drift: recorded fields no skill consumes. Operates on the repo, not on any household's facts.
requires: []
---

# Reference data refresh

## What this is for

Every other skill here encodes **reasoning**, which doesn't expire. Two modules
encode **facts about the outside world**, which do:

| Table | Holds | Changes |
|---|---|---|
| `lib/pf/limits.py` | §402(g), §415(c), catch-up, IRA, HSA limits | **Annually** |
| `lib/pf/jurisdiction.py` | UM/UIM caps, UMPD rules, statutory minimums | Legislatively |

A stale entry here is worse than a missing one, because it will be quoted
confidently and believed. This skill is the maintenance procedure that keeps
them honest.

## Three modes

```bash
uv run skills/reference-data-refresh/run.py              # what is stale or unverified
uv run skills/reference-data-refresh/run.py --checklist  # every value, to go and check
uv run skills/reference-data-refresh/run.py --facts inputs/facts.yml  # plus schema drift
```

The first two take no `--facts` — they inspect the repository, not a household.
The third additionally reports **schema drift**: recorded fields in a household
file that no skill consumes. That is either private analysis running ahead of
the public schema (the case the check exists for), a misspelled field, or a
skill not yet built — advisory in all three cases, never a blocker, because a
household legitimately records figures before any skill reads them.

The report exits non-zero if there's a blocker.

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

If you're seeing that failure, you're in the right place.

## Procedure

**1. Find the authoritative source.** For limits, the IRS annual cost-of-living
adjustment notice — not a summary article, not a financial-media table, and not
your own recollection. For state rules, the state insurance code or the
department's own guidance.

**2. Transcribe every field for the year.** All of them:

```
elective_deferral · catch_up_50 · catch_up_60_63 · total_additions
compensation_limit · ira_contribution · ira_catch_up
hsa_self_only · hsa_family · hsa_catch_up_55
```

**A partially filled year is worse than a missing one.** A missing year makes
every skill refuse to answer; a half-filled year makes them answer wrongly.
`test_known_years_are_fully_populated` enforces this — don't work around it.

**3. Set `source` and `verified_on`.** `verified_on` is an ISO date and means
*a human compared this against the authority on that date*. It is not the date
you edited the file. If you transcribed without checking, leave it as
`unverified` — that is an honest state and the report handles it.

**4. Do not delete old years.** They're needed to re-run a prior year's review
and to reconcile a historical decision.

**5. Run the tests.** `uv run --with pytest --with pyyaml pytest tests/ -q`

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
