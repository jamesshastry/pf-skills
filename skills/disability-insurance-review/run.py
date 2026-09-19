#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Disability insurance: after-tax cover against need, and the expiring riders."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, disability as D, facts as F, skill_metrics as SM, ssa as SS  # noqa: E402

REQUIRED = ["household.members", "household.annual_spending",
            "household.balance_sheet", "insurance.disability"]
m = cli.money
URGENCY = {"passed": "❌ passed", "urgent": "🔴 urgent",
           "approaching": "🟠 approaching", "distant": "· distant",
           "unknown": "⚠️ no date recorded"}


def build(data: dict, w: cli.Writer) -> None:
    w.add_metrics(SM.emit("disability-insurance-review", data))
    members = F._dig(data, "household.members") or []
    policies = F._dig(data, "insurance.disability") or []
    spending = float(F._dig(data, "household.annual_spending"))
    liquid = F.liquid(data)
    today = F.as_of(data)

    insured_ids = sorted({p.get("insured") for p in policies if p.get("insured")})
    for iid in insured_ids:
        member = next((x for x in members if x.get("id") == iid), {})
        a = D.assess(policies, insured_id=iid, insured_age=member.get("age"),
                     annual_spending=spending,
                     gross_income=float(member.get("income_annual") or 0),
                     liquid_assets=liquid, reference_date=today)

        w(f"## Insured: {iid}")
        w()
        verdict = ("✅ **Covered.**" if a.covered
                   else f"⚠️ **Short by {m(a.monthly_gap)}/mo.**")
        w(f"{verdict} Spending {m(a.monthly_need)}/mo · after-tax cover "
          f"{m(a.monthly_covered_after_tax)}/mo · insurable ceiling about "
          f"{m(a.max_insurable_monthly)}/mo.")
        w()
        w.table(["Policy", "Stated", "After tax", "Elim.", "Period", "Definition"],
                [[p.label, f"{m(p.monthly_benefit)}/mo",
                  f"{m(p.monthly_benefit_after_tax)}/mo",
                  f"{p.elimination_days}d" if p.elimination_days else "—",
                  p.benefit_period_years or "—", p.definition or "**unknown**"]
                 for p in a.policies])
        w()
        w("Cover is compared **after tax**, because a stated benefit is not "
          "comparable across policies until it is. Who paid the premium "
          "decides whether the benefit is taxed.")
        for n in SS.disability_overlay_notes(
                ssdi_monthly=F._dig(data, "social_security.disability_monthly"),
                has_group_cover=any(p.get("employer_provided") for p in policies
                                    if p.get("insured") == iid)):
            w()
            w(f"> {n}")
        for n in a.notes:
            w()
            w(f"> {n}")

        if a.deadlines:
            w()
            w("### Deadlines")
            w()
            w.table(["", "What", "Date", "Days left"],
                    [[URGENCY[d.urgency], d.label,
                      d.on.isoformat() if d.on else "—",
                      d.days_remaining if d.days_remaining is not None else "—"]
                     for d in a.deadlines])
            w()
            w("A finding with a date on it stops being actionable. Re-run "
              "before acting on anything marked urgent.")

        for p in a.policies:
            w()
            w(f"### {p.label}")
            w()
            for f in p.findings:
                w(f"- {f}")
        w()

    cli.disclaimer(w, "lib/pf/disability.py",
                   f"Taxable benefits are converted at an assumed "
                   f"{D.ASSUMED_MARGINAL_RATE:.0%} marginal rate — an estimate.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Disability insurance review",
                             required=REQUIRED, build=build,
                             skill_id="disability-insurance-review"))
