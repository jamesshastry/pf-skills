#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Social Security timing — longevity insurance, and a survivor decision."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, limits as L, retirement as R, status as S  # noqa: E402

REQUIRED = ["household.members"]


def build(data: dict, w: cli.Writer) -> None:
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    ages = L.retirement_ages(primary.get("birth_year"))
    earners = [x for x in members if (x.get("income_annual") or 0) > 0]
    adults = [x for x in members if x.get("role") in ("primary", "spouse")]
    single_earner = len(earners) <= 1 and len(adults) > 1

    table = R.claiming_table(ages)
    if table:
        w(f"Full retirement age **{ages.ss_full}**. Benefit relative to the "
          f"full-retirement amount:")
        w()
        w.table(["Claim at", "Benefit"],
                [[r["age"], f"{r['multiplier']:.0%}"
                  + (" ← full" if r["age"] == ages.ss_full else "")]
                 for r in table])
        w()
        w("Percentages are the statutory adjustment, applied to your own "
          "benefit amount — which comes from your Social Security statement, "
          "not from this skill.")
    w()
    statuses = {m.get("id"): m.get("us_status") for m in members
                if m.get("role") in ("primary", "spouse")}
    home = next((c for m in members for c in (m.get("citizenship") or [])
                 if c != "US"), None)
    for f in S.social_security_notes(statuses=statuses, home_country=home):
        w(f"- {f}")
        w()

    for f in R.claiming_guidance(ages=ages, single_earner_household=single_earner):
        w(f"- {f}")
        w()
    w("## How to think about it")
    w()
    w("**Not as a break-even calculation.** The usual framing — *at what age "
      "does waiting pay off?* — quietly assumes you know when you will die, "
      "and answers the wrong question. The benefit is inflation-adjusted and "
      "lasts as long as you do, which makes delaying a purchase of longevity "
      "insurance. The risk being insured is living a long time.")
    w()
    w("Reasons to claim early that are actually good ones: poor health with a "
      "genuinely shortened life expectancy; needing the income now and having "
      "no alternative; or a portfolio so large the benefit is irrelevant "
      "either way.")
    w()
    w("Reasons that are not: *getting back what I paid in*, and *the "
      "programme might change*. Neither survives contact with the arithmetic, "
      "and the second argues for delaying if anything.")
    cli.disclaimer(w, "lib/pf/retirement.py",
                   "Statutory adjustment rates only. Your actual benefit, "
                   "spousal eligibility and earnings-test thresholds come "
                   "from ssa.gov.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Social Security timing", required=REQUIRED, build=build))
