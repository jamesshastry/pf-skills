#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Capital-needs analysis: how much a household needs if an income stops."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, ssa as SS, survivor as S  # noqa: E402

REQUIRED = ["household.members", "household.annual_spending", "household.balance_sheet"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    members = F._dig(data, "household.members") or []
    earners = [x for x in members
               if x.get("role") in ("primary", "spouse") and (x.get("income_annual") or 0) > 0]
    if not earners:
        w("No member has recorded income. Nothing to replace — add "
          "`income_annual` to the earning member(s).")
        return

    # Everything passes to the survivor, including retirement accounts.
    available = (F.tier_total(data, F.LIQUID) + F.tier_total(data, F.AGE_RESTRICTED)
                 + F.tier_total(data, F.ILLIQUID))
    spending = float(F._dig(data, "household.annual_spending"))

    for e in earners:
        need = S.compute(
            insured_id=e["id"],
            members=members,
            annual_spending=spending,
            assets_available=available,
            education_obligation=F._dig(data, "household.education_obligation"),
            non_citizen_survivor=any(
                x.get("role") == "spouse" and x.get("us_status")
                and x.get("us_status") != "citizen" for x in members),
            social_security=F._dig(data, "social_security"),
        )
        label = f"{e.get('role')} ({e['id']})"
        w(f"## If the {label} income stops")
        w()
        w.table(["", ""], [
            ["Household spending today", f"{m(spending)}/yr"],
            [f"× survivor factor {S.SURVIVOR_SPENDING_FACTOR:.0%}",
             f"**{m(need.annual_need)}/yr**"],
            ["Less surviving income", f"−{m(need.surviving_income)}"],
            ["**Annual shortfall**", f"**{m(need.annual_shortfall)}**"],
            [f"Over {need.horizon_years} years at "
             f"{S.REAL_DISCOUNT_RATE:.0%} real, before Social Security",
             m(need.capital_for_income_before_ss)],
            ["Less Social Security survivor benefits",
             f"−{m(need.ss_value)}" if need.ss_value else "—"],
            ["**Capital for income**", f"**{m(need.capital_for_income)}**"],
            ["Final expenses", m(need.final_expenses)],
            ["Education obligation", m(need.education_obligation)],
            ["**Total need**", f"**{m(need.total_need)}**"],
            ["Less assets available to survivors", f"−{m(need.assets_available)}"],
            ["**Capital gap**", f"**{m(need.net_need)}**"],
        ])
        w()
        if need.ss and need.ss.computable:
            w(f"**Before netting Social Security the total need is "
              f"{m(need.total_need_before_ss)}.** Both figures are shown "
              "because excluding Social Security is a defensible choice — "
              "some households treat it as conservatism — and the choice "
              "should be visible rather than buried in an assumption.")
            w()
            w("### The survivor benefit does not arrive as a flat amount")
            w()
            w("Netting an average across the horizon produces the same "
              "present value and erases the only feature worth knowing about: "
              "the caregiver benefit stops at the youngest child's "
              f"**{SS.CAREGIVER_CHILD_AGE_LIMIT}th** "
              "birthday, not their eighteenth, and a widow(er)'s benefit "
              "cannot start before 60.")
            w()
            w.table(["Survivor's age", "Payable", "What it is"],
                    [[f"{ph.start_age}–{ph.end_age}" if ph.years > 1
                      else str(ph.start_age),
                      f"{m(ph.annual)}/yr" + (" *(capped)*" if ph.capped else ""),
                      ph.label] for ph in need.ss.phases])
            w()
        w(f"**{m(need.net_need)}** is the figure life cover has to close. "
          "`life-insurance-review` compares it against what is in force.")
        for n in need.notes:
            w()
            w(f"- {n}")
        w()

    w("---")
    w()
    w("Both figures are **real** — today's money throughout, discounted at a "
      "real rate. Mixing a nominal rate into a real cash flow overstates the "
      "discount and understates the need.")
    w()
    w("Assets available deliberately include retirement accounts: on death "
      "they pass to the survivor. They are *not* included in the "
      "absorbability tests used by the property and casualty skills, where "
      "the household is still alive and cannot reach them.")
    cli.disclaimer(w, "lib/pf/survivor.py",
                   "The survivor spending factor is a benchmark — replace it "
                   "with a real post-loss budget if you have one.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Survivor needs", required=REQUIRED, build=build))
