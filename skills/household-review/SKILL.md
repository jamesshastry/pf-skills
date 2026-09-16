---
name: household-review
description: Run every skill in the library against one facts file and rank what to fix first — expiring findings before uncovered losses before priced drags before optimizations. Use when asked for the whole picture, what to do first, or whether anything urgent is hiding across reports. Reads figures from a local facts file.
requires:
  - household.members
---

# Household review

Fifty-plus skills each end with good advice, and no household does fifty
things at once. Each report is also blind past its own edge: it cannot say
whether its finding matters more than another skill's. This skill owns
**order**.

## The idea

Every household skill's check is re-run in-process against the same facts
file, and each verdict becomes zero or more actions in one worklist. A skill
whose inputs are missing is listed as blocked — naming what it waits on —
never approximated.

## The decision rule

Four tiers, in this order, for reasons stated once rather than argued per
skill:

1. **Things that expire.** A dated finding inside six months or already
   passed — a rider window, a filing deadline, an identification clock. What
   closes cannot be repriced later at any price, so it outranks everything
   priced.
2. **Losses you cannot buy back afterwards.** Protection gaps: cover short of
   the need, uninsured exposure, an irreversible filing. Distinct from drags
   you can stop any month.
3. **Priced drags, biggest first.** Ongoing dollars per year the modules
   actually price — foregone yield, interest accrual, credit left on the
   table.
4. **Everything else real.** Neither expiring nor priced: checklists to run,
   policies to adopt, figures to record.

Within a tier the sooner expiry ranks first, then the larger priced impact,
then the skill name — the order is total, so the report is deterministic.

## What it will not do

It does not re-render any skill's tables, resolve any skill's trade-off, or
run a skill whose inputs are absent. `conflict-check` already names the
contradictions; live ones appear here as actions but are not re-decided.
Where the ranking compares a priced drag against an unpriced gap, that
comparison is judgment — the report names the ranking itself as its weakest
input, and each headline points at the skill report that actually prices it.

## Closing

1. **Do first**, in tier order — the top of section one is the most
   time-sensitive finding in the whole library for this household.
2. **Blocked inputs**, ordered by how many skills each one unblocks — that is
   what the next hour of paperwork buys.
3. **The skill reports**, one by one, for anything ranked above. This report
   says what to read next, not what to conclude.

---

*Not financial, tax, or legal advice.*
