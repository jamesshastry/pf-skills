#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Provenance report — what this repo knows about the world, and when it checked.

Takes no --facts: this is about the repository's own tables, not any household.

    uv run skills/reference-data-refresh/run.py
"""
from __future__ import annotations
import argparse
import datetime as dt
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import provenance as P  # noqa: E402

SEV = {"blocker": "🚫 **BLOCKER**", "stale": "⚠️ Stale", "unverified": "· Unverified"}


def fmt(v) -> str:
    if isinstance(v, bool) or v is None:
        return f"`{v}`"
    if isinstance(v, dict):
        return "  ·  ".join(f"{k}: {fmt(x)}" for k, x in v.items())
    if isinstance(v, (tuple, list)):
        return " / ".join(fmt(x) for x in v)
    if isinstance(v, int) and abs(v) >= 1000:
        return f"**${v:,}**"
    return f"**{v}**"


def checklist() -> int:
    """Every asserted value, generated from the tables themselves.

    Generated rather than hand-written on purpose: a hand-written checklist
    silently omits whatever was added to a table after it.
    """
    today = dt.date.today()
    out: list[str] = []
    w = out.append

    total = sum(len(e.values) for t in P.registry() for e in t.entries)
    w("# Reference data verification checklist")
    w("")
    w(f"Generated {today.isoformat()} from the tables themselves — **"
      f"{total} asserted values** across {len(P.registry())} tables.")
    w("")
    w("Every one of these is currently attested by nobody. Each was "
      "transcribed and marked `unverified`. Tick a value only when you have "
      "seen it on the authority's own page — not in a summary article, not "
      "in a search result.")
    w("")
    w("**When a whole entry checks out**, set `verified_on: <today>` on it in "
      "the module and re-run `reference-data-refresh` to confirm the report "
      "changes. **If any value is wrong**, fix it and note what it was — a "
      "wrong entry that has been quoted in a report is a defect, not a typo.")

    for tb in P.registry():
        w("")
        w(f"## {tb.name}")
        w("")
        w(f"`{tb.module}` · changes **{tb.cadence}**")
        w("")
        for u in (tb.url or tb.authority).split(" · "):
            w(f"- {u}")
        for e in tb.entries:
            w("")
            w(f"### `{e.key}`")
            w("")
            if not e.values:
                w("- [ ] *(no individual values recorded)*")
                continue
            for k, v in e.values.items():
                w(f"- [ ] `{k}` = {fmt(v)}")
            w("")
            w(f"  → then set `verified_on` on `{e.key}` in `{tb.module}`")

    w("")
    w("---")
    w("")
    w("## Why this matters more than it looks")
    w("")
    w("These are the only values in the repository that can be **wrong rather "
      "than merely debatable**. Every threshold elsewhere is a judgement you "
      "can argue with; these are facts, and a wrong one propagates silently "
      "into a confident dollar figure.")
    w("")
    w("The proposed clusters would add federal brackets, the standard "
      "deduction, QBI thresholds, §179 limits, ACA subsidy tables and IRMAA "
      "tiers to the same file. **Verifying what is already here is the "
      "precondition for that, not a follow-up to it** — see `REVIEW.md` A3.")
    print("\n".join(out))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checklist", action="store_true",
                    help="emit a verification checklist of every asserted value")
    if ap.parse_args().checklist:
        return checklist()

    today = dt.date.today()
    out: list[str] = []
    w = out.append

    w("# Reference data provenance")
    w("")
    w(f"As of **{today.isoformat()}**.")
    w("")
    w("Every other module in this repository encodes reasoning, which does "
      "not expire. These tables encode **facts about the outside world**, "
      "which do.")
    w("")

    issues = P.check(today)
    blockers = [i for i in issues if i.severity == "blocker"]
    w(f"**{len(blockers)} blocker(s)** · {len(issues)} issue(s) total.")

    for t in P.registry():
        w("")
        w(f"## {t.name}")
        w("")
        w(f"`{t.module}` · {t.holds}")
        w("")
        w(f"**Authority:** {t.authority} · **changes:** {t.cadence} · "
          f"**tolerance:** {P.MAX_AGE_DAYS[t.cadence] // 365} year(s)")
        w("")
        w("| Entry | Verified | Source |")
        w("|---|---|---|")
        for e in t.entries:
            when = ("**never**" if e.self_declared_unverified
                    else e.verified_on.isoformat() if e.verified_on else "**unknown**")
            w(f"| `{e.key}` | {when} | {e.source or '—'} |")

    if issues:
        w("")
        w("## Issues")
        w("")
        for i in sorted(issues, key=lambda x: x.severity != "blocker"):
            w(f"- {SEV[i.severity]} **{i.table} / {i.key}** — {i.detail}")

    w("")
    w("---")
    w("")
    w("Run the `reference-data-refresh` skill to act on this. Do not edit the "
      "tables from memory.")
    print("\n".join(out))
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
