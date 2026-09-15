#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Is a cost segregation study worth commissioning? A screen, not a study."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, realestate as R  # noqa: E402

REQUIRED = ["real_estate.cost_segregation", "assumptions.marginal_tax_rate"]
m = cli.money


def _gates(data: dict) -> tuple[dict[str, bool], str]:
    """Reuse the §469 gate rather than restating its logic here.

    Resolved **per activity**, not per household. A household can have one
    short-stay property whose gate is open and a long-term rental whose gate
    is shut, and accelerating depreciation on the second is still worth
    nothing — so the gate has to be matched to the property being screened.
    """
    acts = F._dig(data, "real_estate.activities")
    p = F._dig(data, "real_estate.participation") or {}
    if not acts or p.get("magi") is None:
        return {}, ("No `real_estate.activities` or "
                    "`real_estate.participation.magi` recorded, so passive-"
                    "loss eligibility is **unresolved** for every property "
                    "below. Run `passive-loss-eligibility` — it decides this "
                    "screen more often than the arithmetic does.")
    g = R.assess_gate(
        acts,
        magi=float(p["magi"]),
        active_participation=p.get("active_participation"),
        hours_real_property=p.get("hours_real_property"),
        hours_all_work=p.get("hours_all_work"),
        grouping_election=bool(p.get("grouping_election")),
        allowance=F._dig(data, "assumptions.passive_loss_allowance"),
        phaseout_start=F._dig(data, "assumptions.passive_loss_phaseout_start"),
        phaseout_end=F._dig(data, "assumptions.passive_loss_phaseout_end"),
    )
    by_label = {a.label: a.open for a in g.activities}
    note = "§469 gate, per activity: " + " · ".join(
        f"**{a.label}** {a.door.replace('_', '-') if a.door else 'shut'}"
        for a in g.activities
    ) + "."
    return by_label, note


def build(data: dict, w: cli.Writer) -> None:
    gates, gate_note = _gates(data)
    rows = F._dig(data, "real_estate.cost_segregation") or []
    if isinstance(rows, dict):
        rows = [rows]

    unmatched = [p.get("label") for p in rows
                 if gates and p.get("label") not in gates]

    screens = [
        R.screen_cost_segregation(
            p,
            gate_open=gates.get(p.get("label")),
            marginal_rate=F._dig(data, "assumptions.marginal_tax_rate"),
            bonus_rate=F._dig(data, "assumptions.bonus_depreciation_rate"),
            discount_rate=F._dig(data, "assumptions.expected_return_apr"),
            state_rate=F._dig(data, "assumptions.state_tax_rate"),
        )
        for p in rows
    ]
    if not screens:
        w("⚠️ Nothing recorded under `real_estate.cost_segregation`.")
        return

    shut = [s for s in screens if s.gate_open is False]
    yes = [s for s in screens if s.worth_commissioning]
    if yes:
        w(f"**{len(yes)} of {len(screens)} properties clear the "
          f"{R.MIN_BENEFIT_TO_COST:.0f}× benefit-to-fee bar** at the "
          "conservative end of the reclassification range — "
          + ", ".join(s.label for s in yes) + ".")
    else:
        w(f"**No property here justifies commissioning a study.** None of "
          f"{len(screens)} clears the {R.MIN_BENEFIT_TO_COST:.0f}× "
          "benefit-to-fee bar at the conservative end of the range.")
    if shut:
        w()
        w(f"**{len(shut)} of them "
          f"{'returns' if len(shut) == 1 else 'return'} zero for a reason "
          "that is not arithmetic**: the §469 gate is shut, so the "
          "accelerated deduction "
          "enlarges a suspended passive loss rather than reducing tax. "
          "Accelerating a loss you cannot deduct is worth nothing — and the "
          "study fee is real money.")
    w()
    w(gate_note)
    if unmatched:
        w()
        w("⚠️ No matching activity for " + ", ".join(f"`{u}`" for u in unmatched)
          + " — the label must match `real_estate.activities[].label` or the "
            "gate cannot be resolved, and the figures below are conditional.")
    w()

    w.table(
        ["Property", "§469 gate", "Depreciable basis", "Reclassified (range)",
         "Year-1 tax saving", "PV of the timing benefit", "Study fee",
         "Ratio"],
        [[s.label,
          "unresolved" if s.gate_open is None
          else ("open" if s.gate_open else "**shut**"),
          m(s.depreciable_basis),
          f"{m(s.reclass_low)}–{m(s.reclass_high)}",
          "—" if s.tax_benefit_low is None
          else f"{m(s.tax_benefit_low)}–{m(s.tax_benefit_high)}",
          "—" if s.pv_benefit_low is None
          else f"{m(s.pv_benefit_low)}–{m(s.pv_benefit_high)}",
          m(s.study_cost),
          "—" if s.benefit_to_cost is None else f"{s.benefit_to_cost:.1f}×"]
         for s in screens])
    w()
    w("The reclassified column is a **screening range**, not an estimate. "
      "Producing the actual figure is what the study is.")
    w()

    for s in screens:
        w(f"## {s.label}")
        w()
        w(f"Straight-line recovery {s.recovery_years:.1f} years.")
        w()
        for f in s.findings:
            w(f"- {f}")
        w()

    w("## Before acting")
    w()
    w("- **Confirm land is excluded** from `depreciable_basis`. If the "
      "purchase price went in, every figure above is overstated and nothing "
      "here can detect it.")
    w("- **Ask for the free feasibility estimate** before paying for a study. "
      "Most providers give one, and it is a better number than this screen.")
    w("- **Decide the exit first.** A sale triggers §1245 recapture at "
      "ordinary rates; an exchange defers it. See `1031-exchange-modeling`.")
    w("- **A study can be applied to a prior year** via a change in accounting "
      "method, without amending. That is a preparer conversation, not a "
      "reason to hurry.")
    cli.disclaimer(
        w, "lib/pf/realestate.py",
        "The bonus depreciation percentage and the tax rates come from your "
        "facts file, not from a table in this library — the bonus figure is "
        "legislated and has changed in most recent years.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Cost segregation screen",
                             required=REQUIRED, build=build))
