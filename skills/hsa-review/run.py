#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""HSA review — the only triple-tax-advantaged account."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, limits as L  # noqa: E402

REQUIRED = ["household.members", "contributions.year"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    year = F._dig(data, "contributions.year")
    lim = L.for_year(year)
    hsa = F._dig(data, "contributions.hsa")
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    age = primary.get("age")

    if not lim.known:
        w(f"⚠️ **Statutory limits for {year} are not in the table** "
          f"(available: {L.years_available()}). Add the year to "
          "`lib/pf/limits.py` with a citation rather than assuming last "
          "year's figures.")
        return

    w("**The only triple-tax-advantaged account available.** Deductible "
      "going in, untaxed while it grows, untaxed coming out for qualified "
      "medical expenses. Every other account gives up one of the three.")
    w()

    if hsa is None:
        w("> `contributions.hsa` is not recorded. If anyone in the household "
          "is enrolled in a qualifying high-deductible health plan, this is "
          "usually the highest-value unused space available — record it and "
          "re-run.")
    elif hsa.get("eligible") is False or hsa.get("coverage") in (None, "none"):
        w("Not eligible — an HSA requires enrolment in a qualifying "
          "high-deductible health plan.")
        w()
        w("**Worth re-evaluating at open enrolment.** The comparison people "
          "get wrong is premium-only: a HDHP usually has a lower premium *and* "
          "a higher deductible, and the HSA tax benefit is a third term that "
          "belongs in the comparison. Run it as total expected annual cost "
          "including the tax saving, not as a premium difference — and against "
          "a bad health year, not an average one.")
    else:
        coverage = hsa.get("coverage")
        used = float(hsa.get("contribution") or 0)
        space = L.hsa_space(coverage, age, lim)
        w.table(["", ""], [
            ["Coverage", coverage],
            ["Contributed", m(used)],
            ["Ceiling", m(space)],
            [f"Catch-up (age {L.HSA_CATCH_UP_AGE}+)",
             m(lim.hsa_catch_up_55) if (age or 0) >= L.HSA_CATCH_UP_AGE else "not yet"],
            ["**Unused**", f"**{m(max(0, (space or 0) - used))}**"],
        ])
        w()
        if space and used < space:
            w(f"- **{m(space - used)} unused.** This is the most tax-efficient "
              "space on the board; fill it before taxable saving.")

    w()
    w("## The part most people miss")
    w()
    w("**An HSA is a retirement account that happens to pay for healthcare.** "
      "Used as a spending account it is merely a good deal. Used as an "
      "investment account it is the best one available:")
    w()
    w("- **Pay current medical costs out of pocket** if cash flow allows, and "
      "let the HSA balance stay invested.")
    w("- **Keep the receipts.** There is no deadline for reimbursing yourself "
      "for a qualified expense — a receipt from today can be reimbursed "
      "decades from now, tax-free, after the balance has compounded.")
    w("- **Invest the balance** rather than leaving it in the cash sweep. "
      "Most custodians default to cash and require an explicit election.")
    w()
    w("Two things to know about the long game: after age 65 non-medical "
      "withdrawals are taxed as ordinary income without penalty, so the "
      "downside case is simply a traditional IRA. And an HSA inherited by "
      "anyone other than a spouse is fully taxable in one year — which makes "
      "it a poor asset to leave behind, and an argument for spending it "
      "before less-taxed assets late in life.")

    cli.disclaimer(w, "lib/pf/limits.py",
                   "Statutory limits change annually — verify against irs.gov.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="HSA review", required=REQUIRED, build=build))
