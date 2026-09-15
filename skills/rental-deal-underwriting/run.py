#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Rental deal metrics — NOI, cap rate, cash-on-cash, DSCR, IRR."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, realestate as R  # noqa: E402

REQUIRED = ["real_estate.deals"]
m = cli.money


def _pct(x, dp=2):
    return "—" if x is None else f"{x:.{dp}%}"


def build(data: dict, w: cli.Writer) -> None:
    deals = [R.underwrite(d) for d in (F._dig(data, "real_estate.deals") or [])]
    if not deals:
        w("⚠️ No deals recorded under `real_estate.deals`.")
        return

    fails = [u for u in deals if u.financeable is False]
    if fails:
        w(f"**{len(fails)} of {len(deals)} deals fail the "
          f"{R.DSCR_LENDER_FLOOR:.2f} DSCR floor** — "
          + ", ".join(u.label for u in fails)
          + ". At that leverage the property does not service its own debt and "
          "the borrower's salary is the reserve.")
    else:
        w(f"**All {len(deals)} deals clear the {R.DSCR_LENDER_FLOOR:.2f} DSCR "
          "floor.**")
    w()
    w("Every figure below is **pre-investor-tax and nominal**. No after-tax "
      "return is available until `passive-loss-eligibility` says a §469 door "
      "is open.")
    w()

    w.table(
        ["Deal", "Price", "Cash in", "NOI yr1", "Cap rate", "CoC", "DSCR",
         "IRR", "Multiple"],
        [[u.label, m(u.price), m(u.cash_invested), m(u.noi_year1),
          _pct(u.cap_rate), _pct(u.cash_on_cash),
          "—" if u.dscr is None else
          (f"**{u.dscr:.2f}**" if u.financeable is False else f"{u.dscr:.2f}"),
          _pct(u.irr, 1), "—" if u.equity_multiple is None
          else f"{u.equity_multiple:.2f}×"]
         for u in deals])
    w()
    w("NOI excludes debt service **and** capital expenditure — that is what "
      "makes the cap rate comparable across differently financed buyers. The "
      "capital reserve is subtracted below NOI, in cash flow.")
    w()

    for u in deals:
        w(f"## {u.label}")
        w()
        w(f"Loan {m(u.loan)} · annual debt service {m(u.annual_debt_service)} "
          f"· net sale proceeds at exit {m(u.net_sale_proceeds)}")
        w()
        w.table(["Year", "Gross rent", "NOI", "Debt service", "Capex reserve",
                 "Cash flow"],
                [[y.year, m(y.gross_rent), m(y.noi), m(y.debt_service),
                  m(y.capex), m(y.cash_flow)] for y in u.years])
        w()
        for f in u.findings:
            w(f"- {f}")
        w()

    w("## Before acting")
    w()
    w("- **Verify rents against signed leases**, not a broker's pro forma. "
      "Market rent and in-place rent are different numbers and only one of "
      "them is collectable next month.")
    w("- **Get the last two years of operating statements** and the property "
      "tax bill. Taxes usually reassess on sale, and the seller's bill is not "
      "yours.")
    w("- **Insurance is quoted, not estimated.** In several markets it is now "
      "the line that moves a deal from workable to not.")
    w("- **The reserve is not the down payment.** Capital events arrive early "
      "and do not wait for the reserve to accumulate.")
    cli.disclaimer(
        w, "lib/pf/realestate.py",
        "Rent, expenses and appreciation are yours, not fetched. The IRR "
        "depends mostly on the appreciation assumption; the year-one figures "
        "do not.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Rental deal underwriting",
                             required=REQUIRED, build=build))
