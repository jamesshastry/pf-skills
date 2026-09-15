#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Employer match audit — is front-loading costing you match?"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, contributions as C, facts as F, limits as L  # noqa: E402

REQUIRED = ["household.members", "contributions.year", "contributions.employer_plan"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    year = F._dig(data, "contributions.year")
    plan = F._dig(data, "contributions.employer_plan") or {}
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    lim = L.for_year(year)

    if not lim.known:
        w(f"⚠️ **Statutory limits for {year} are not in the table** "
          f"(available: {L.years_available()}). The §402(g) ceiling is what "
          "determines when deferrals stop, so the timing cannot be modelled. "
          "Add the year to `lib/pf/limits.py` with a citation.")
        return

    a = C.analyse_match(plan, age=primary.get("age"), lim=lim)

    if a.at_risk:
        w(f"⚠️ **Up to {m(a.forfeited)} of employer match is at risk this year.**")
    elif a.match_earned is not None:
        w(f"✅ **No match lost to timing.** {m(a.match_earned)} earned of "
          f"{m(a.match_available)} available.")
    else:
        w("**Cannot answer yet** — see below.")
    w()

    if a.periods_contributing is not None:
        w.table(["", ""], [
            ["Match formula", f"`{a.formula_type}`"],
            ["Pay periods", a.pay_periods],
            ["Periods with a deferral", f"**{a.periods_contributing}**"],
            ["§402(g) ceiling incl. catch-up",
             m((lim.elective_deferral or 0) + L.catch_up_for_age(primary.get('age'), lim))],
            ["Match earned", m(a.match_earned)],
            ["Match available", m(a.match_available)],
            ["**Forfeited**", f"**{m(a.forfeited)}**"],
            ["Plan trues up",
             {True: "yes", False: "**no**", None: "**unknown**"}[a.true_up]],
        ])
        w()

    for f in a.findings:
        w(f"- {f}")
        w()

    w("## Why the formula shape decides this")
    w()
    w("| Formula | Front-loading |")
    w("|---|---|")
    w("| `percent_of_pay_per_period` | **Costly.** Match accrues only in "
      "periods you contribute. Stop in month three and the rest of the year "
      "earns nothing. |")
    w("| `dollar_for_dollar_annual_cap` | **Free.** The cap is annual, so "
      "reaching it sooner changes nothing. |")
    w()
    w("Advice that skips this distinction is wrong about half the time, in "
      "the same confident tone either way. If the formula is not recorded, "
      "the question to ask is: *\"is the match calculated per pay period or "
      "on annual compensation, and does the plan true up after year end?\"*")
    w()
    w("**This error is invisible on every statement.** The balance looks "
      "correct because the deferrals arrived on schedule; only the match is "
      "missing, and nothing flags it.")

    cli.disclaimer(w, "lib/pf/contributions.py",
                   "Statutory limits change annually — verify against irs.gov.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Employer match audit", required=REQUIRED, build=build))
