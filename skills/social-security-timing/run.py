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
from pf import cli, facts as F, limits as L, retirement as R, ssa as SS, status as S  # noqa: E402

m = cli.money

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

        recorded = F._dig(data, "social_security.retirement_monthly") or {}
        if recorded:
            w()
            w("### Your recorded amounts, beside the percentages")
            w()
            w.table(["Claim at", "Monthly", "Annual"],
                    [[k, m(v), f"{m(v * 12)}/yr"]
                     for k, v in sorted(recorded.items())])
            w()
            stmt = F._dig(data, "social_security.statement_date")
            w(f"Read from `social_security.retirement_monthly`"
              + (f", statement dated **{stmt}**. " if stmt else ". ")
              + "These are transcribed from the statement, not computed here "
                "— a benefit this skill calculated would be a guess wearing a "
                "statement's clothes. Re-pull the statement annually; the "
                "figures move with the earnings record.")
        else:
            w()
            w("> **No amounts are recorded.** Add "
              "`social_security.retirement_monthly` from your statement and "
              "this table gains a dollar column. The percentages above are "
              "correct without it and decide nothing on their own.")
    w()
    statuses = {m.get("id"): m.get("us_status") for m in members
                if m.get("role") in ("primary", "spouse")}
    home = next((c for m in members for c in (m.get("citizenship") or [])
                 if c != "US"), None)
    for f in S.social_security_notes(statuses=statuses, home_country=home):
        w(f"- {f}")
        w()

    spouse = next((x for x in members if x.get("role") == "spouse"), None)
    if spouse is not None:
        notes = SS.uninsured_spouse_notes(
            insured=SS.insured_status(spouse),
            payable_abroad=F._dig(data, "social_security.payable_abroad"))
        notes += SS.credit_building_notes(
            own_projected_monthly=F._dig(
                data, "social_security.spouse_own_projected_monthly"),
            worker_pia_monthly=SS.worker_pia_from_statement(
                F._dig(data, "social_security")))
        if notes:
            w("## The spouse's own record")
            w()
            for n in notes:
                w(f"- {n}")
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
