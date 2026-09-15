#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Employer concentration — income and assets are one bet, not two."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, concentration as C, facts as F  # noqa: E402

REQUIRED = ["household.members", "household.balance_sheet",
            "household.annual_spending", "equity_comp"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    eq = F._dig(data, "equity_comp") or {}
    members = F._dig(data, "household.members") or []
    employer = eq.get("employer") or "the employer"
    linked = [x for x in members if x.get("employer")]
    income_linked = sum(float(x.get("income_annual") or 0) for x in linked)

    investable = (F.tier_total(data, F.LIQUID) + F.tier_total(data, F.AGE_RESTRICTED)
                  + F.tier_total(data, F.ILLIQUID))
    e = C.assess_exposure(
        employer=employer,
        income_from_employer=income_linked,
        total_income=F.household_income(data),
        held_value=float(eq.get("held_value") or 0),
        unvested_value=float(eq.get("unvested_value") or 0),
        investable=investable, liquid=F.liquid(data),
        monthly_spending=float(F._dig(data, "household.annual_spending")) / 12.0,
        sell_at_vest=eq.get("sell_at_vest"),
    )
    s = C.joint_scenario(e)

    w(f"**{e.income_share:.0%} of income and {e.asset_share:.0%} of investable "
      f"assets depend on {employer}.** Overall severity: "
      f"**{e.severity.replace('_', ' ')}** "
      f"(income {e.income_severity.replace('_', ' ')}, "
      f"assets {e.asset_severity.replace('_', ' ')}).")
    w()
    w.table(["", ""], [
        ["Employer-linked income", f"{m(e.income_from_employer)}/yr"],
        ["Held shares", m(e.held_value)],
        ["Unvested pipeline", m(e.unvested_value)],
        ["Investable assets", m(e.investable)],
        ["**Total at risk**", f"**{m(e.total_at_risk)}**"],
    ])
    w()
    w("Unvested equity is counted as exposure but is **not** on the balance "
      "sheet — it is contingent on employment, which is the thing at risk.")

    w()
    w("## The joint scenario")
    w()
    w(f"Shares fall **{s.decline:.0%}** and the job ends for **{s.months} "
      f"months** — modelled together, because the event that causes one tends "
      "to cause the other.")
    w()
    w.table(["", ""], [
        ["Value of held shares lost", m(s.stock_loss)],
        [f"Income lost over {s.months} months", m(s.income_loss)],
        ["Unvested pipeline forfeited", m(s.unvested_loss)],
        ["**Combined**", f"**{m(s.total_loss)}**"],
        ["Liquid assets after the decline", m(s.liquid_after)],
        ["**Runway at current spending**", f"**{s.runway_months:.0f} months**"],
    ])
    w()
    w("> **Never stress-test these separately.** Two independent tests, each "
      "survivable, can describe a combined event that is not. A layoff and a "
      "share-price decline are not independent draws.")

    w()
    w("## Findings")
    w()
    for f in e.findings:
        w(f"- {f}")
        w()

    w("## What this skill does not do")
    w()
    w("It produces a **policy**, not a transaction. Factor exposure, tax-lot "
      "selection, wash-sale timing and trade execution need positions and "
      "market data, and belong to a portfolio tool. The output here is a "
      "standing rule the household adopts once — which is the part that "
      "actually changes outcomes, because it removes a recurring decision "
      "made under pressure.")
    cli.disclaimer(w, "lib/pf/concentration.py")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Employer concentration risk",
                             required=REQUIRED, build=build))
