#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Roth conversion window — the low-tax years between work and RMDs."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, limits as L, retirement as R  # noqa: E402

REQUIRED = ["household.members", "retirement.planned_retirement_age"]


def build(data: dict, w: cli.Writer) -> None:
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    ages = L.retirement_ages(primary.get("birth_year"))
    win = R.conversion_window(
        retirement_age=F._dig(data, "retirement.planned_retirement_age"),
        ages=ages, claim_age=F._dig(data, "retirement.ss_claim_age"))

    if win.exists:
        w(f"**A {win.years}-year window: ages {win.opens_age} to "
          f"{win.closes_age}.**")
    else:
        w("**No conversion window at these ages.**")
    w()
    if ages.known:
        w.table(["", ""], [
            ["Planned retirement", win.opens_age],
            ["RMDs begin", ages.rmd_age],
            ["Social Security latest", ages.ss_latest],
            ["**Window closes**", f"**{win.closes_age}**"],
        ])
    w()
    for f in win.findings:
        w(f"- {f}")
        w()
    if win.exists:
        w("## Why the window is worth planning around")
        w()
        w("Three income sources stop or have not started: employment income "
          "has ended, RMDs have not begun, and benefits can be deferred. "
          "Taxable income in these years is whatever you choose it to be, "
          "which is a position most people occupy exactly once.")
        w()
        w("Converting during it does three things at once: it moves money "
          "into an account that is never taxed again, it **shrinks the future "
          "RMD** that would otherwise be forced out at a higher rate, and it "
          "leaves heirs a far better asset — an inherited Roth is tax-free "
          "while an inherited traditional IRA is ordinary income to them, "
          "usually within ten years and often during their peak earning "
          "period.")
        w()
        w("It is also the main defence against the **widow's tax trap**: on "
          "the first death the survivor files as single, with roughly half "
          "the bracket width, on much the same required income.")
    cli.disclaimer(w, "lib/pf/retirement.py",
                   "Bracket thresholds, IRMAA tiers and subsidy cliffs are "
                   "year-specific and not modelled here.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Roth conversion window", required=REQUIRED, build=build))
