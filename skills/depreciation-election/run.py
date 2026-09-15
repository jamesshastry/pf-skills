#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""§179, bonus or standard mileage — and what year one locks in."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, depreciation as D, facts as F  # noqa: E402

REQUIRED = ["business.assets"]
m = cli.money


def _figures(data: dict) -> D.YearFigures:
    as_of = F.as_of(data)
    g = lambda k: F._dig(data, "assumptions." + k)  # noqa: E731
    return D.YearFigures(
        year=as_of.year if as_of else None,
        section_179_limit=g("section_179_limit"),
        section_179_phaseout=g("section_179_phaseout"),
        suv_179_cap=g("suv_179_cap"),
        bonus_pct=g("bonus_depreciation_pct"),
        luxury_auto_year1_cap=g("luxury_auto_year1_cap"),
        luxury_auto_year1_cap_no_bonus=g("luxury_auto_year1_cap_no_bonus"),
        standard_mileage_rate=g("standard_mileage_rate"),
    )


def build(data: dict, w: cli.Writer) -> None:
    rows = F._dig(data, "business.assets") or []
    figures = _figures(data)
    income = F._dig(data, "business.taxable_income")
    total_placed = sum(float(r.get("cost") or 0) for r in rows)

    w(f"{len(rows)} asset(s) placed in service, {m(total_placed)} total cost"
      + (f" · taxable business income {m(income)}" if income is not None
         else " · **taxable business income not recorded**"))
    w()
    w("**A deduction and a deduction are not the same deduction.** §179 cannot "
      "create or increase a loss and carries the excess forward; bonus "
      "depreciation can. On a vehicle, the year-one method choice also decides "
      "what is available for every year after it.")
    w()

    for row in rows:
        a = D.Asset(
            description=row.get("description") or row.get("name") or "asset",
            cost=float(row.get("cost") or 0),
            business_use=row.get("business_use"),
            gvwr_lbs=row.get("gvwr_lbs"),
            annual_business_miles=row.get("annual_business_miles"),
            actual_operating_cost=row.get("actual_operating_cost"),
            placed_in_service=row.get("placed_in_service"),
        )
        e = D.evaluate(a, figures, taxable_business_income=income,
                       total_placed_in_service=total_placed)

        w(f"## {a.description}")
        w()
        w(f"{m(a.cost)} cost"
          + (f" · {a.business_use:.0%} business use" if a.business_use is not None
             else " · **business use not recorded**")
          + (f" · {a.gvwr_lbs:,} lb GVWR" if a.gvwr_lbs else "")
          + (f" · {a.annual_business_miles:,.0f} business miles"
             if a.annual_business_miles else "")
          + (f" · placed in service {a.placed_in_service}"
             if a.placed_in_service else ""))
        w()

        if e.options:
            w.table(["Election", "Year-one deduction", "Carried forward",
                     "Limited by", "Closes off mileage"],
                    [[o.label,
                      f"**{m(o.year_one_deduction)}**"
                      if o.year_one_deduction is not None else "no figure",
                      m(o.carryforward) if o.carryforward else "—",
                      o.capped_by or "—",
                      "yes" if o.locks_out_mileage else "no"]
                     for o in e.options])
            w()

        for o in e.options:
            if o.unavailable:
                w(f"⚠️ **{o.label} — no figure.** {o.unavailable}")
                w()
        for o in e.options:
            for f in o.findings:
                w(f"- {f}")
                w()
        for f in e.findings:
            w(f"- {f}")
            w()

        lock = row.get("first_year_method")
        if a.is_vehicle:
            for f in D.method_lock(lock):
                w(f"- {f}")
                w()

    w("## Before electing anything")
    w()
    w("- **The bigger deduction is not automatically the better one.** A "
      "deduction is worth your marginal rate this year; deferring it to a year "
      "with a higher rate, or to a year where it is not wasted against a loss, "
      "can be worth more. Front-loading everything into a low-income year is "
      "the common mistake, and §179's income limit is the tax code making the "
      "same point.")
    w("- **A purchase is not a saving.** Buying an asset to reduce tax costs "
      "the full price to save the marginal rate on it. It is only worth doing "
      "if the business needed the asset anyway.")
    w("- **The records are the deduction.** A contemporaneous mileage log is "
      "what substantiates business use; a reconstruction after a notice "
      "arrives is not the same thing and is treated as such.")
    w("- **States frequently decouple** from bonus depreciation and sometimes "
      "from §179. A state deduction cannot be inferred from the federal one, "
      "and is not computed here.")
    w()
    w("## The weakest input")
    w()
    w("**Business-use percentage.** It scales every figure above, decides "
      "whether §179 and bonus are available at all, and is the first thing an "
      "examiner asks about. It is also the one input a household estimates "
      "rather than measures. Unknown is not 100%, and a percentage that is "
      "barely over 50% is a reason to take the smaller deduction — the "
      "recapture on a later drop below the line arrives in a year the cash is "
      "already spent.")
    cli.disclaimer(w, "lib/pf/depreciation.py",
                   "Every year-specific figure here comes from your facts "
                   "file, not from a table in this repository — the §179 "
                   "limit, the bonus percentage, the auto caps and the mileage "
                   "rate all change. Confirm them against irs.gov for the year "
                   "the asset was placed in service.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Depreciation election",
                             required=REQUIRED, build=build))
