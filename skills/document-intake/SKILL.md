---
name: document-intake
description: Turns a pile of statements, policies and tax returns into a prioritised worklist for filling in a facts file. Reports which schema fields are still unset, which of them block the most skills, and which document probably answers each. Use when starting from nothing, after adding documents, or when you want to know what the next hour of transcription would unlock. Does not parse documents or guess values — it decides what is worth reading for.
---

# Document intake

## The idea

Sixty-five skills read a facts file. **Nothing writes one.** That gap is where
a new household actually stalls — not on understanding the schema, but on the
hour of transcription between a folder of PDFs and the first useful report.

This skill does not close the gap by parsing documents. It closes it by making
the transcription **ordered and finite**: here is what is still missing, here
is what each missing field costs you, here is the document that probably
answers it.

## Completeness is measured in skills, not fields

The schema has several hundred fields. Nobody fills all of them, and a
"percent complete" figure against the whole schema is discouraging, largely
meaningless, and never reaches 100.

So the measure is **how many skills can actually run**. That has three
properties the other measure lacks: it is honest, it is monotonic, and it
ranks the work for you. Ten fields that unlock four skills beat forty that
unlock none, and you find that out from the report rather than from an opinion
about what matters.

`household.members` is usually the first row, because it blocks around thirty
skills on its own. Four lines of YAML.

## What the report contains

| Section | What it answers |
|---|---|
| **Documents** | What is in categorized `inputs/<category>/` directories and the legacy `documents/` directory, and which schema area each path suggests |
| **What runs today** | How many skills are unblocked right now |
| **Next hour** | Skills blocked on one or two fields — shortest distance first |
| **Fields by blast radius** | One field, and everything it is holding up |
| **Not on any statement** | The fields no document announces, where intakes stall at ninety percent |

## Working with an agent

Put documents in the closest `inputs/<category>/` directory. Run this. Hand an
agent both the report and the files. The legacy flat `documents/` directory is
still scanned.

When `--facts` points to `<project>/inputs/facts.yml`, the runner scans that
project's input directories rather than pf-skills' own scaffold. Use
`--source-root` only when the facts file lives somewhere else.

The report says which fields are open and which document probably answers
each; the agent reads and **proposes** values; you confirm them into
`inputs/facts.yml`.

**Keep the confirmation step.** Every skill downstream treats a recorded figure
as established fact and builds a confident recommendation on it. A misread
statement therefore does not stay a misread statement — it becomes a
conclusion, several reports away from the page it came from, with nothing
marking it as uncertain.

## What it will not do

**It does not read your documents.** Filenames are matched against schema
areas, and that match is a hint for whoever does the reading. Nothing is
parsed, nothing is extracted, and a file called `geico-auto-2026.pdf` is
evidence of nothing except its own name.

**It does not guess a value from a filename**, infer one field from another,
or fill a default. A field is set or it is not.

**It does not rank by importance.** It ranks by how many skills a field
unblocks, which is a fact about the dependency graph rather than a judgement
about your finances. The field blocking the most skills is not necessarily the
one that matters most to you.

**`null` stays a valid answer.** A skill missing a field stops and says what is
missing. That is the designed behaviour, not a failure to work around, and it
is always better than a plausible number nobody checked.

## Closing

The output is a list of questions. Answer them in the order given and the
number of runnable skills goes up; answer them out of order and it still goes
up, just more slowly.

*Not financial, tax, or legal advice.*
