#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Marriage finance merger — filing status, beneficiaries, estate, accounts."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, transitions as T  # noqa: E402

REQUIRED = ["household.members", "transitions.marriage"]
m = cli.money


def signed(x) -> str:
    """`$-11,280` reads as a typo. A leading minus sign reads as a saving."""
    if x is None:
        return "cannot be determined"
    return f"−{m(abs(x))}" if x < 0 else m(x)


def build(data: dict, w: cli.Writer) -> None:
    mar = F._dig(data, "transitions.marriage") or {}
    spend = F._dig(data, "household.annual_spending")

    plan = T.assess_marriage(
        members=F._dig(data, "household.members") or [],
        domicile=F._dig(data, "household.domicile"),
        joint_tax=mar.get("tax_if_joint"),
        separate_tax_combined=mar.get("tax_if_separate_combined"),
        idr_payment_joint=mar.get("idr_annual_payment_joint"),
        idr_payment_separate=mar.get("idr_annual_payment_separate"),
        medical_expenses=mar.get("medical_expenses"),
        lower_earner_agi=mar.get("lower_earner_agi"),
        household_agi=mar.get("household_agi"),
        accounts_with_stale_beneficiaries=mar.get("stale_beneficiary_accounts"),
        monthly_spending=(float(spend) / 12.0) if spend else None,
        independent_access=mar.get("independent_access"),
    )
    c = plan.filing

    w("## Filing status")
    w()
    if c.tax_delta is None:
        w("**Cannot be determined** — see below.")
    else:
        w(f"**File {c.recommendation}.**")
    w()
    w.table(
        ["", "Joint", "Separate (combined)", "Separate − joint"],
        [["Federal tax", m(c.joint_tax), m(c.separate_tax),
          signed(c.tax_delta)],
         ["Income-driven loan payments",
          m(mar.get("idr_annual_payment_joint")),
          m(mar.get("idr_annual_payment_separate")),
          signed(-c.idr_delta) if c.idr_delta is not None else "not recorded"],
         ["**Net advantage of separate**", "", "",
          f"**{signed(c.net_advantage)}**"]])
    w()
    w("Both tax totals are figures your software produces by running the "
      "return twice. This skill does not contain a bracket table and will not "
      "estimate them.")
    w()

    for heading, areas in (
            ("Why, and what separate also costs", ("filing status",)),
            ("Liability", ("liability",)),
            ("Beneficiaries — the most-forgotten item", ("beneficiaries",)),
            ("Estate", ("estate",)),
            ("Combining accounts, as a policy", ("accounts",))):
        rows = T._sorted([f for f in plan.findings if f.area in areas])
        if not rows:
            continue
        w(f"## {heading}")
        w()
        for f in rows:
            w(f"- {'⚠️ ' if f.severity == 'blocker' else ''}{f.detail}")
            w()

    w("## The weakest input")
    w()
    w("**`tax_if_separate_combined`.** It is the only figure here nobody has "
      "usually computed, because computing it means preparing two returns "
      "that will not be filed. Everything in the filing-status section is "
      "downstream of it, and a household that estimates it from a rule of "
      "thumb has estimated the answer.")
    w()
    w("## What this will not do")
    w()
    w("- **Estimate either tax total.** No bracket table lives here, "
      "deliberately: a stale one produces confident nonsense.")
    w("- **Apply community-property rules.** In a community-property state "
      "income is split between spouses regardless of how you file, which can "
      "erase the separate-filing advantage entirely. That table is not "
      "encoded, so the answer is *check it* rather than a guess.")
    w("- **Advise on a prenuptial agreement**, which is legal work.")
    cli.disclaimer(w, "lib/pf/transitions.py",
                   "The non-citizen-spouse estate rule comes from "
                   "`lib/pf/status.py`; the buffer floor from `lib/pf/cash.py`.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Marriage finance merger", required=REQUIRED,
                             build=build))
