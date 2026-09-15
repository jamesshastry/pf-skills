# documents/

**Put your statements here.** Anything, any format, any filename.

Nothing in this directory is committed. Nothing leaves your machine.

```
documents/
  geico-auto-2026.pdf
  401k-statement-2026-q2.pdf
  1040-2025.pdf
  term-life-policy.pdf
```

Then:

```bash
uv run skills/document-intake/run.py
```

That reports which schema fields are still unset, which of them block the most
skills, and which document probably answers each.

---

## What is worth having

| Area | Documents |
|---|---|
| **Insurance** | Declarations pages — auto, renters/homeowners, umbrella, life, disability. The *declarations* page, not the policy booklet: it carries the limits, deductibles and premium on one sheet |
| **Accounts** | Most recent statement for each account. One per account, not twelve months — except for foreign accounts, below |
| **Tax** | Last filed return, with schedules. Prior years too if foreign accounts are in play |
| **Equity comp** | Grant agreements or the broker's vesting schedule |
| **Debt** | Current statement for each loan, showing rate and balance |
| **Property** | Closing statement, and the depreciation schedule for anything rented out |

## Foreign accounts need a full year, not a statement

FBAR turns on the **peak aggregate balance at any point in the calendar year**,
not the year-end figure. An account that touched $12,000 in March and ended the
year at $400 crosses the threshold; a December statement shows $400 and tells
you nothing.

For each foreign account, for each year in question, you need the highest
balance it reached. That usually means twelve statements or a full-year
transaction export.

## Filenames are visible even when files are not

This directory is gitignored, so nothing here reaches git. Gitignore does not
protect a screen share, a terminal recording, a directory listing pasted into a
chat, or a support ticket.

A statement saved as `Jane-Q-Smith-acct-44172-Nov.pdf` puts a name and a partial
account number into all of those. `document-intake` flags filenames that look
like they carry personal data. Renaming costs one `mv`.

## Nothing here is parsed

No skill in this repository reads these files. `document-intake` lists them and
matches **filenames** against the schema areas they might answer — that is a
hint for whoever does the reading, never a value.

The reading is done by you, or by an agent you hand the files to. The values go
into `inputs/facts.yml` after **you** confirm them, because every skill
downstream treats a recorded figure as established fact.
