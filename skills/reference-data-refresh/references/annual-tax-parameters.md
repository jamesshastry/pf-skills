# Annual tax-parameter refresh

Use this procedure for a new tax year or when an authority revises a published
figure. The deterministic audit detects missing provenance; the agent performs
the public-source research and prepares the change for review.

## Keep the ownership boundary

| Parameter class | Examples | Owner | Refresh rule |
|---|---|---|---|
| Repository annual table | 401(k), IRA, and HSA limits | Versioned code | Add a complete year; never replace or forward-fill an old year |
| Annual official assumption | Brackets, standard deduction, FEIE and QCD limits, Social Security wage base, QBI and depreciation limits, FPL, ACA schedule, IRMAA tiers | Gitignored household facts plus provenance metadata | Replace for the selected tax year from the authority; do not create a global default |
| Periodic official series | IRS §6621 underpayment rates | Gitignored household facts keyed by quarter | Fill every required quarter from the applicable revenue ruling; never interpolate |
| Household or jurisdiction estimate | Marginal and state rates, deductions, ACA benchmark premium | Gitignored household facts | Refresh from the return, tax software, marketplace, or professional; do not publish it as a universal rate |
| Planning assumption | Returns, inflation, appreciation | Scenario facts | Change only as an explicit planning choice; it is not part of the statutory refresh |
| Legislative constant | NIIT/FICA rates, RMD ages, eligibility tests | Versioned code with provenance | Change only when enacted rules change, preserving effective dates when old analyses need them |

Values intentionally kept in private facts are grouped under
`assumptions.annual_parameter_metadata`. A group records `tax_year`,
`verified_on`, and `sources`; it does not duplicate the values. Official groups
must use exact URLs. A verification date attests that a human compared every
active value in the group with those sources.

## Research

Use primary sources: IRS revenue procedures, notices, publications and form
instructions; SSA releases; HHS poverty guidelines; CMS tables; and state tax
authorities. Search results and secondary summaries are leads only. Open the
authority's document and record its title, URL, publication date, applicable
tax year, and any effective-date or transition language.

Do not assume all figures in one announcement share an effective date. HSA
limits can be published earlier than retirement-plan limits, §6621 changes by
quarter, and a statute may alter a rule after an inflation notice was issued.

## Review table

Before editing, present this table for every proposed change:

| Group and field | Prior value | Proposed value | Applies to | Primary source | Verified on | Consuming skills | Disposition |
|---|---:|---:|---|---|---|---|---|

Use `unchanged—verified` when a value was checked and did not move. Use
`unresolved` when sources conflict or the authority has not published the
figure. Never turn an unresolved field into zero and never copy the prior year
merely to make a check pass.

## Apply and validate

For repository tables, append the new year, retain every old year, and update
the entry's exact source and `verified_on`. A structural rule change may require
a model change rather than another numeric field.

For private facts, propose a patch to the ignored facts file or a separate
ignored working copy. Do not print its values in the provenance report, commit
it, or upload it to an external service. Update the corresponding metadata
group only after all active values in that group were checked.

Run the affected domain tests, the provenance tests, the skill contract tests,
and the strict target-year audit. Re-run affected reports and call out any
recommendation that changed; a passing parser does not establish numerical
equivalence or tax correctness.

## Automation boundary

The scheduled GitHub workflow is a smoke alarm, not an updater. It has
read-only repository permissions, receives no household facts, and performs no
network research beyond downloading build dependencies. It selects the current
year through October and the next year in November and December. A failed run
is the trigger for a person or agent to execute this procedure and submit a
reviewed change.
