---
name: financial-history-review
description: Compare immutable local financial snapshots and structured skill results without mixing observations, historical analyses, or projections. Use when a household wants to understand what changed across review dates, whether findings opened or closed, and whether the cause was household facts or model methodology; reads snapshot paths from a local facts file.
requires:
  - history.snapshot_files
---

# Financial history review

## The decision

Decide which changes need an explanation or follow-up. An opened or worsened
finding ranks ahead of a large balance movement; a correction or model-version
change is methodology, not household progress.

## Protocol

Load immutable snapshot documents through `lib/pf/timeseries.py`. Compare only
points whose stable metric ID, clock, scenario, unit, currency, basis and entity
dimensions agree. Keep observed facts, analysis results and forward projections
in separate tables. Preserve gaps and restatements; never forward-fill or turn
unknown into zero.

Use stable IDs for joins. A changed display label is not a new account, policy,
person, property, goal or finding. If an old report exists only as Markdown,
offer a clearly labeled manual/lossy migration rather than scraping it.

## Attribution

Use recorded flows or source metadata when available. Otherwise show the
unexplained residual. A changed result on identical inputs but a different model
version is a methodology change. Do not invent contributions, market movement,
debt paydown or FX effects from two endpoints.

## What it will not do

It does not create snapshots during a normal report, fetch market data, mutate
history, annualize short periods by default, or fit a trend line to a short
series. Use `scripts/history.py` explicitly to capture, calculate, compare,
restate, or rerun a historical snapshot.

*Not financial, tax, or legal advice.*
