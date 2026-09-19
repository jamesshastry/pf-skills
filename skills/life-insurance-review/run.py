#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Life insurance: gap against need, and the shape of what is in force."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, life as L, skill_metrics as SM, survivor as S  # noqa: E402

REQUIRED = ["household.members", "household.annual_spending",
            "household.balance_sheet", "insurance.life"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    w.add_metrics(SM.emit("life-insurance-review", data))
    members = F._dig(data, "household.members") or []
    policies = F._dig(data, "insurance.life") or []
    today = F.as_of(data)
    available = (F.tier_total(data, F.LIQUID) + F.tier_total(data, F.AGE_RESTRICTED)
                 + F.tier_total(data, F.ILLIQUID))
    spending = float(F._dig(data, "household.annual_spending"))
    dependents = F.dependents(data)

    insured_ids = sorted({p.get("insured") for p in policies if p.get("insured")})
    for iid in insured_ids:
        need = S.compute(insured_id=iid, members=members, annual_spending=spending,
                         assets_available=available,
                         education_obligation=F._dig(data, "household.education_obligation"),
                         non_citizen_survivor=any(
                             x.get("role") == "spouse" and x.get("us_status")
                             and x.get("us_status") != "citizen" for x in members),
                         social_security=F._dig(data, "social_security"))
        a = L.assess(policies, need=need.net_need, insured_id=iid,
                     dependents=dependents, today=today)

        w(f"## Insured: {iid}")
        w()
        verdict = ("✅ **Covered.**" if a.covered
                   else f"⚠️ **Short by {m(a.gap)}.**")
        w(f"{verdict} Need {m(a.need)} · portable cover in force "
          f"{m(a.in_force_portable)} · premiums {m(a.annual_premium)}/yr.")
        w()
        w.table(["Policy", "Type", "Benefit", "Premium", "Per $1k/yr", "Portable"],
                [[p.label, p.kind, m(p.death_benefit), m(p.premium_annual),
                  f"${p.cost_per_1k:,.2f}" if p.cost_per_1k else "—",
                  "yes" if p.portable else "**no**"] for p in a.policies])
        for n in a.notes:
            w()
            w(f"> {n}")
        w()
        for p in a.policies:
            if not p.findings:
                continue
            w(f"### {p.label}")
            w()
            for f in p.findings:
                w(f"- {f}")
            w()

    cli.disclaimer(w, "lib/pf/life.py",
                   "Cash-value returns are computed generously; the real "
                   "figure is usually worse.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Life insurance review", required=REQUIRED,
                             build=build, skill_id="life-insurance-review"))
