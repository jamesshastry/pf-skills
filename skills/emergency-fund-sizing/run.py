#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Emergency fund sizing — the buffer everything else assumes."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cash as K, cli, facts as F, skill_metrics as SM  # noqa: E402

REQUIRED = ["household.members", "household.balance_sheet", "household.annual_spending"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    w.add_metrics(SM.emit("emergency-fund-sizing", data))
    members = F._dig(data, "household.members") or []
    earners = [x for x in members if (x.get("income_annual") or 0) > 0]
    var = next((x.get("income_variable_share") for x in earners
                if x.get("income_variable_share") is not None), None)

    reserve = F.reserve_assets(data)
    b = K.size_buffer(
        liquid=reserve.included,
        annual_spending=float(F._dig(data, "household.annual_spending")),
        earners=len(earners),
        has_dependents=bool(F.dependents(data)),
        variable_comp_share=var,
    )

    if b.shortfall:
        w(f"⚠️ **{m(b.shortfall)} short of target.**")
    elif b.excess:
        w(f"✅ **Adequate**, with {m(b.excess)} of excess cash to redeploy.")
    else:
        w("✅ **Adequate.**")
    w()
    w.table(["", ""], [
        ["Cash and cash equivalents", m(b.liquid)],
        ["Monthly spending", m(b.monthly_spending)],
        ["Months held", f"**{b.months_held:.1f}**"],
        ["Target months", f"**{b.target_months:.0f}**"],
        ["Target", f"**{m(b.target)}**"],
    ])
    w()
    w("### How the target was built")
    w()
    for d in b.drivers:
        w(f"- {d}")
    w()
    w("Measured against **cash and cash equivalents** — not total `liquid` "
      "assets, net worth, or retirement accounts. Marketable securities are "
      "spendable within days but are not a cash reserve at par.")
    if reserve.rows:
        w(f"{m(sum(value for _, value in reserve.rows))} of marketable "
          "securities is excluded from the cash reserve until sold and "
          "haircut for market and tax effects.")
    if reserve.unknown:
        w("Unclassified assets are excluded: " + ", ".join(reserve.unknown) + ".")
    w()
    for f in b.findings:
        w(f"- {f}")
        w()

    w("## Why this gates everything else")
    w()
    w(f"The property and casualty skills refuse to recommend dropping any "
      f"coverage from a household below **{K.MIN_BUFFER_MONTHS:.0f} months**, "
      "whatever the price arithmetic says. Self-insuring a risk means paying "
      "for it out of the buffer; without one, the household meets an ordinary "
      "setback with credit-card debt at 20%+ and the saving is erased several "
      "times over.")
    w()
    w(f"That floor is a single constant shared by both skills "
      f"(`cash.MIN_BUFFER_MONTHS`), so the two cannot disagree about it.")
    cli.disclaimer(w, "lib/pf/cash.py")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Emergency fund sizing", required=REQUIRED,
                             build=build, skill_id="emergency-fund-sizing"))
