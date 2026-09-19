# prompts/

**Empty, and deliberately kept as a note rather than deleted.**

Two long-form California property review prompts lived here briefly. They are now
skills:

| Skill | For |
|---|---|
| [`ca-sfh-disclosure-review`](../skills/ca-sfh-disclosure-review/) | Detached single-family |
| [`ca-condo-hoa-disclosure-review`](../skills/ca-condo-hoa-disclosure-review/) | Condo or townhome, where the association is usually the larger risk |

## Why they moved

The original argument for keeping them out of `skills/` was that they fail two of
`CONTRIBUTING.md`'s four tests — the arithmetic does not fit in tested code, and
there is no schema slice. That was half right and it produced the wrong answer.

**What it missed:** a skill's frontmatter description is how an agent finds the
thing without being told. A prompt in a folder has to be located and pasted by a
human, which is the delivery mechanism of this whole repository, given up to
protect a contract that had already bent in the same direction — `document-intake`
is a skill, takes no computation, and organises reading rather than doing it.

**And the premise was wrong.** There *is* testable logic: which disclosures a
property attracts given its type and build year, the Civ. Code §4525 packet as a
named list, SB 326 applicability, reserve and delinquency thresholds. All of it
now lives in `lib/pf/disclosure.py`, cited and registered with `provenance.py`,
where it can be checked and go stale visibly. As prose it was neither.

The schema slice turned out to be small too: `property_review`, six fields and a
nested `hoa` block.

## What is left here

No prompt is committed. Local `*-prompt.md` and `*-brief.md` task artifacts may
exist while work is in progress, but they are gitignored and the commit hook
blocks a forced add because those briefs can quote private household facts.
This file exists so the question does not get re-litigated from scratch, and
because a directory that vanishes without explanation invites someone to
recreate it.

If a future artefact genuinely cannot be a skill — no decision, no rule, nothing
testable — this is where it would go. Check first whether that is true or just
how it was written the first time.
