#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""ACA premium subsidy in the pre-Medicare gap — and the MAGI conflict it creates."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, healthcare as H, limits as L, retirement as R  # noqa: E402

REQUIRED = ["household.members", "retirement.planned_retirement_age"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    ages = L.retirement_ages(primary.get("birth_year"))
    retire_at = F._dig(data, "retirement.planned_retirement_age")

    window = R.conversion_window(
        retirement_age=retire_at, ages=ages,
        claim_age=F._dig(data, "retirement.ss_claim_age"))

    params = H.params_from_assumptions(F._dig(data, "assumptions"))

    a = H.assess_aca(
        retirement_age=retire_at,
        household_size=len(members),
        magi=F._dig(data, "assumptions.expected_magi_in_gap_years"),
        params=params,
        window=window,
    )

    # ── the gap ─────────────────────────────────────────────────────────────
    if a.gap.exists:
        w(f"**{a.gap.years} years of health cover to buy privately** — ages "
          f"{a.gap.retirement_age} to {a.gap.medicare_age}.")
    else:
        w("**No pre-Medicare gap at these ages.**")
    w()

    if a.point and a.point.subsidy is not None:
        w.table(["", ""], [
            ["Expected gap-year MAGI", m(a.magi)],
            [f"Poverty level, household of {a.household_size}", m(a.point.fpl)],
            ["**% of FPL**",
             f"**{a.point.pct_of_fpl:.0%}**" if a.point.pct_of_fpl else "—"],
            ["Benchmark silver premium", m(a.point.benchmark)],
            ["Expected contribution", m(a.point.expected_contribution)],
            ["**Estimated credit**", f"**{m(a.point.subsidy)}/yr**"],
        ])
        w()

    for f in a.findings:
        w(f"- {f}")
        w()

    # ── A6 ──────────────────────────────────────────────────────────────────
    live = [c for c in a.conflicts if c.live]
    if live:
        w("## ⚠️ Conflict with another skill in this repository")
        w()
        w("Two skills here give **opposite instructions about the same "
          "number in the same years**. This is not a caveat; it is a "
          "contradiction, and it is reported rather than resolved silently.")
        w()
        for c in live:
            w(f"### {c.name}")
            w()
            w(f"*{' · '.join(f'`{s}`' for s in c.skills)} — "
              f"{c.overlap_years} overlapping year(s), ages "
              f"{c.overlap_ages[0]}–{c.overlap_ages[1]}.*")
            w()
            w(c.detail)
            w()
            for q in c.quantified:
                w(f"- {q}")
                w()
    else:
        w("## No conflict detected")
        w()
        w("The conversion window and the pre-Medicare gap do not overlap at "
          "these ages, so `roth-conversion-window` and this skill are not "
          "pulling against each other. That is unusual — check the retirement "
          "age and birth year are right before relying on it.")
        w()

    # ── the partition ───────────────────────────────────────────────────────
    if a.segments:
        w("## Which years cost what")
        w()
        w("The conflict resolves into a **sequence**, not a choice. The "
          "conversion window splits into segments with different binding "
          "constraints, and they are not equally expensive to convert in.")
        w()
        w.table(["Ages", "Years", "What binds"],
                [[f"{s.start_age}–{s.end_age}", s.years,
                  " + ".join(s.constraints) if s.constraints else "**nothing**"]
                 for s in a.segments])
        w()
        for n in H.resolution_notes(a.segments):
            w(f"- {n}")
            w()

    w("## Weakest input")
    w()
    w(a.weakest_input)
    cli.disclaimer(w, "lib/pf/healthcare.py",
                   "Poverty levels, the applicable-percentage schedule, the "
                   "benchmark premium and whether the 400% cliff is in force "
                   "all come from your facts file, not from a table in this "
                   "repository — they change every year and a stale one is "
                   "worse than none.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="ACA subsidy optimization",
                             required=REQUIRED, build=build))
