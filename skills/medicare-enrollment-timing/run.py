#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Medicare enrolment windows, permanent late penalties, and the IRMAA lookback."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, healthcare as H, limits as L, retirement as R  # noqa: E402

REQUIRED = ["household.members"]


def _tiers(raw) -> list[H.IrmaaTier]:
    return [H.IrmaaTier(float(t["magi_threshold"]),
                        float(t.get("part_b_monthly", 0) or 0),
                        float(t.get("part_d_monthly", 0) or 0))
            for t in (raw or [])]


def build(data: dict, w: cli.Writer) -> None:
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    ages = L.retirement_ages(primary.get("birth_year"))
    retire_at = F._dig(data, "retirement.planned_retirement_age")
    magi = F._dig(data, "assumptions.expected_magi_in_gap_years")

    a = H.assess_medicare(
        current_age=primary.get("age"),
        working_past_65=F._dig(data, "healthcare.working_past_65"),
        employer_employees=F._dig(data, "healthcare.employer_employees"),
        coverage_is_current_employment=F._dig(
            data, "healthcare.coverage_is_current_employment"),
        part_a_quarters=F._dig(data, "healthcare.part_a_quarters"),
        magi=magi,
        irmaa_tiers=_tiers(F._dig(data, "assumptions.irmaa_tiers")),
        contributing_to_hsa=bool(F._dig(data, "contributions.hsa.eligible")),
    )

    if a.years_away is not None and a.years_away > 0:
        w(f"**Medicare at {a.medicare_age} — {a.years_away} years away.** The "
          f"year that prices the first premium is the one at age "
          f"**{a.irmaa_magi_year_age}**, not {a.medicare_age}.")
    elif a.years_away is not None:
        w(f"**Already at or past {a.medicare_age}.** Check the enrolment "
          f"status of every part before reading anything below as planning.")
    else:
        w("**No age recorded for the primary member**, so the windows below "
          "are structural rather than dated.")
    w()

    w.table(["", ""], [
        ["Initial Enrolment Period",
         f"{H.IEP_MONTHS} months — {H.IEP_MONTHS_BEFORE} before, the birthday "
         f"month, {H.IEP_MONTHS_AFTER} after"],
        ["Special Enrolment Period (Part B)",
         f"{H.SEP_PART_B_MONTHS} months after current-employment coverage ends"],
        ["Part D creditable-coverage gap",
         f"{H.CREDITABLE_COVERAGE_GAP_DAYS} days"],
        ["Part B late penalty",
         f"{H.PART_B_PENALTY_PER_12M:.0%} per full 12 months — **permanent**"],
        ["Part D late penalty",
         f"{H.PART_D_PENALTY_PER_MONTH:.0%} per uncovered month — **permanent**"],
        ["Premium-free Part A",
         f"{H.PART_A_QUARTERS_REQUIRED} quarters of covered employment"],
        ["Employer-size threshold",
         f"{H.SEP_EMPLOYER_MIN_EMPLOYEES} employees — decides who pays primary"],
        ["IRMAA lookback", f"{H.IRMAA_LOOKBACK_YEARS} years"],
    ])
    w()

    for f in a.findings:
        w(f"- {f}")
        w()

    # ── what a late enrolment actually costs ────────────────────────────────
    w("## What lateness costs, as a multiplier")
    w()
    w("The penalty is a percentage of a premium this repository does not hold, "
      "so it is shown as the multiplier it applies for the rest of the "
      "enrollee's life. Multiply it by the standard premium for the year to "
      "get a figure.")
    w()
    w.table(["Years late", "Part B surcharge", "Part D surcharge (same gap)"],
            [[y, f"+{H.part_b_penalty_rate(y):.0%}",
              f"+{H.part_d_penalty_rate(y * 12):.0%}"]
             for y in (1, 2, 3, 5)])
    w()
    w("Both are permanent and both are charged monthly for life. A three-year "
      "delay is not a three-year problem.")
    w()

    # ── the shared conflict ─────────────────────────────────────────────────
    window = R.conversion_window(
        retirement_age=retire_at, ages=ages,
        claim_age=F._dig(data, "retirement.ss_claim_age"))
    # The subsidy parameters are read here too, so that a conflict quantified
    # in `aca-subsidy-optimization` is quantified identically here. Two reports
    # giving different magnitudes for one conflict is the same defect as two
    # skills giving opposite instructions.
    params = H.params_from_assumptions(F._dig(data, "assumptions"))
    size = len(members)
    conflicts = [c for c in H.magi_conflicts(
        retirement_age=retire_at, window=window,
        taper=(H.taper_at(magi, size, params) if magi is not None else None),
        subsidy=(H.subsidy_at(magi, size, params) if magi is not None else None),
    ) if c.live]

    if conflicts:
        w("## ⚠️ The same MAGI conflict, one layer on")
        w()
        w("IRMAA is priced from a return filed two years earlier, which puts "
          "it in direct tension with `roth-conversion-window` — and with "
          "`aca-subsidy-optimization`, which is pulling the same number the "
          "same way. All three are describing one decision about one variable.")
        w()
        for c in conflicts:
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
        w("For the full partition of the conversion window — which years are "
          "free, which are constrained by the subsidy, and which by both — run "
          "`aca-subsidy-optimization`. It holds the sequencing; this skill "
          "holds the enrolment deadlines.")
        w()

    w("## Weakest input")
    w()
    w(a.weakest_input)
    cli.disclaimer(w, "lib/pf/healthcare.py",
                   "Part B and Part D premiums and the IRMAA tier thresholds "
                   "are annual figures published by CMS and are deliberately "
                   "not stored here — supply them in the facts file for dollar "
                   "amounts.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Medicare enrollment timing",
                             required=REQUIRED, build=build))
