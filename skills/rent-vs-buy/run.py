#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Rent vs buy — total cost of occupancy, and the break-even holding period."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, housing as H  # noqa: E402

REQUIRED = ["housing.monthly_rent", "housing.purchase"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    p = F._dig(data, "housing.purchase") or {}
    rent = float(F._dig(data, "housing.monthly_rent"))
    years = int(p.get("expected_years") or 7)
    # Deliberately NOT assumptions.expected_return_apr — that is a nominal
    # figure used against nominal debt rates, and silently reusing it here
    # once produced a real-vs-nominal mix that never broke even.
    ret = F._dig(data, "assumptions.nominal_investment_return") or H.DEFAULT_INVESTMENT_RETURN
    appr = F._dig(data, "assumptions.home_appreciation")
    appr = H.DEFAULT_APPRECIATION if appr is None else appr
    growth = F._dig(data, "assumptions.rent_growth") or H.DEFAULT_RENT_GROWTH

    c = H.compare(p, monthly_rent=rent, years=years,
                  investment_return=float(ret), appreciation=float(appr),
                  rent_growth=float(growth))

    verdict = ("**Buying is cheaper**" if c.owning_cheaper else "**Renting is cheaper**")
    w(f"{verdict} over {years} years, by **{m(abs(c.difference))}**.")
    w()
    w.table(["", ""], [
        ["Price", m(c.price)],
        ["Down payment", m(c.down_payment)],
        ["Loan", m(c.loan)],
        ["Monthly payment (P&I)", m(c.monthly_payment)],
        ["Current rent", f"{m(rent)}/mo"],
    ])

    w()
    w(f"## Wealth given up over {years} years")
    w()
    w("Both sides are carried forward to the horizon at the investment "
      "return, so the comparison is like-for-like on timing. Owning "
      "front-loads cost and back-loads benefit; summing undiscounted cash "
      "flows would flatter it.")
    w()
    w.table(["Line", "Amount"], [
        ["Mortgage interest paid", m(c.interest_paid)],
        ["Property tax", m(c.tax_paid)],
        ["Insurance", m(c.insurance_paid)],
        ["Maintenance", m(c.maintenance_paid)],
        ["HOA", m(c.hoa_paid)],
        [f"Transaction costs ({H.BUY_COSTS:.0%} in, {H.SELL_COSTS:.0%} out)",
         m(c.transaction_costs)],
        ["**All outflows, compounded to the horizon**",
         f"**{m(c.opportunity_cost)}**"],
        ["Less terminal equity (sale − costs − balance)",
         f"−{m(c.appreciation)}"],
        ["**Net cost of owning**", f"**{m(c.total_cost_of_owning)}**"],
        ["**Net cost of renting**", f"**{m(c.total_cost_of_renting)}**"],
    ])
    w()
    w(f"The first six lines are undiscounted totals, shown so the components "
      f"are checkable. The compounded figure is what the comparison uses. "
      f"Principal repaid ({m(c.principal_paid)}) is not a cost — it returns "
      "through terminal equity.")

    w()
    w("## Break-even")
    w()
    if c.breakeven_years:
        w(f"**About {c.breakeven_years} years.** Shorter than that and renting "
          f"wins; longer and buying does.")
    else:
        w("**Buying does not break even within 40 years** at these assumptions.")
    w()
    for f in c.findings:
        w(f"- {f}")
        w()

    w("## What this does not model")
    w()
    w("Mortgage interest and property tax deductibility, which depend on "
      "whether the household itemises; the risk of being unable to move for "
      "work; the value of security of tenure; and any view on house prices. "
      "The appreciation input is a dial, not a forecast — move it and see how "
      "much of the conclusion depends on it.")
    cli.disclaimer(w, "lib/pf/housing.py")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Rent vs buy", required=REQUIRED, build=build))
