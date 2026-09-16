#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Whole-household review: every skill's check, one ranked worklist."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, review as R  # noqa: E402

REQUIRED = ["household.members"]
m = cli.money

SKILLS_DIR = Path(__file__).resolve().parents[1]

TIER_HEADING = {
    R.TIER_CLOSING: "Things that expire",
    R.TIER_UNCOVERED: "Losses you cannot buy back afterwards",
    R.TIER_DRAG: "Priced drags, biggest first",
    R.TIER_OPTIMISE: "Real, but neither expiring nor priced",
}


def size_of(a: R.Action) -> str:
    bits = []
    if a.impact_annual:
        bits.append(f"{m(a.impact_annual)}/yr")
    if a.days_to_expiry is not None:
        bits.append(f"{a.days_to_expiry} days left" if a.days_to_expiry >= 0
                    else f"passed {abs(a.days_to_expiry)} days ago")
    return "; ".join(bits) or "—"


def build(data: dict, w: cli.Writer) -> None:
    rep = R.collect(data, SKILLS_DIR)
    ran = len(rep.checked) + len({a.skill for a in rep.ranked})
    w(f"**{len(rep.ranked)} action(s)** from {ran} skill(s) that run · "
      f"{len(rep.checked)} clean · {len(rep.blocked)} blocked on missing "
      f"inputs.")
    w()

    n = 0
    for tier in R.TIERS:
        acts = [a for a in rep.ranked if a.tier == tier]
        if not acts:
            continue
        n += 1
        w(f"## {n}. {TIER_HEADING[tier]}")
        w()
        for a in acts:
            w(f"- `{a.skill}` — {a.headline} *({size_of(a)})*")
            if a.detail and a.detail not in a.headline:
                w(f"  - {a.detail}")
        w()

    if rep.checked:
        w(f"## Checked, nothing to do")
        w()
        for o in rep.checked:
            w(f"- `{o.skill}` — {o.headline}")
        w()

    if rep.blocked:
        w(f"## Blocked on missing inputs")
        w()
        for b in rep.blocked:
            w(f"- `{b.skill}` — needs {', '.join(b.missing)}")
        w()
        w("What the next hour of paperwork buys, by blast radius:")
        w()
        for path, skills in rep.blocking[:8]:
            w(f"- `{path}` unblocks {len(skills)}: {', '.join(skills)}")
        w()

    for e in rep.errors:
        w(f"- ⚠️ `{e.skill}` did not conclude: {e.message}")
    if rep.errors:
        w()
    for s in rep.unwired:
        w(f"- ⚠️ `{s}` has no review adapter yet")
    if rep.unwired:
        w()

    w("**Weakest input:** the ranking itself. Tiers compare priced drags "
      "against unpriced gaps by judgment — the order says what to do first, "
      "not what matters most in any absolute sense. Each headline links to "
      "the skill report that actually prices it; read that before acting.")
    cli.disclaimer(w, "lib/pf/review.py",
                   "Each adapter re-reads its skill's own verdict — this "
                   "report ranks findings, it does not remake them.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Household review", required=REQUIRED,
                             build=build))
