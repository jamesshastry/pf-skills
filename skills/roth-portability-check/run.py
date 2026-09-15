#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Does the destination recognise the Roth wrapper — and does the advice invert."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, crossborder as X, facts as F  # noqa: E402

REQUIRED = ["crossborder.destinations"]
m = cli.money

STATUS = {
    X.RECOGNISED: "✅ recognised",
    X.CONTESTED: "🚫 **contested**",
    X.NOT_RECOGNISED: "🚫 **not recognised**",
    X.UNKNOWN_STATUS: "❔ not in the table",
}


def build(data: dict, w: cli.Writer) -> None:
    p = X.portability(
        F._dig(data, "crossborder.destinations") or [],
        roth_balance=F._dig(data, "crossborder.roth_balance"),
        traditional_balance=F._dig(data, "crossborder.traditional_balance"),
        planned_conversion=F._dig(data, "crossborder.planned_conversion_annual"),
        conversion_tax_rate=F._dig(data, "assumptions.marginal_tax_rate"),
    )

    if p.any_inverts:
        w("🚫 **At least one destination does not honour the Roth wrapper, so "
          "the conversion advice inverts.** Converting now buys a US tax bill "
          "today in exchange for an exemption that destination may not grant.")
    else:
        w("No destination recorded here is known to tax Roth distributions — "
          "but read what that does and does not mean below.")
    w()

    w.table(["Destination", "Roth wrapper", "Exposed balance", "Local rate",
             "Local tax if taxed"],
            [[d.label, STATUS.get(d.country.roth_status, "❔"),
              m(d.exposed_balance) if d.exposed_balance is not None
              else "**cannot be determined**",
              f"{d.ordinary_rate:.0%}" if d.ordinary_rate is not None
              else "not recorded",
              m(d.double_tax_estimate) if d.double_tax_estimate is not None
              else "—"]
             for d in p.destinations])
    w()
    w("Exposed balance is the Roth balance plus one planned conversion. "
      "*Cannot be determined* means the balance is not recorded — it does not "
      "mean zero.")

    w()
    w("## The accounts at stake")
    w()
    w.table(["", ""], [
        ["Roth balance", m(p.roth_balance) if p.roth_balance is not None
         else "**not recorded**"],
        ["Traditional balance", m(p.traditional_balance)
         if p.traditional_balance is not None else "**not recorded**"],
        ["Planned conversion (annual)", m(p.planned_conversion)
         if p.planned_conversion is not None else "none planned"],
        ["US tax on that conversion", m(p.conversion_tax_now)
         if p.conversion_tax_now is not None else "**cannot be determined**"],
    ])

    w()
    w("## The headline")
    w()
    for f in p.findings:
        w(f"- {f}")
        w()

    w("## By destination")
    w()
    for d in p.destinations:
        w(f"### {d.label}"
          + (f" — {d.country.name}" if d.country.known and d.country.name else ""))
        w()
        if d.country.known:
            w(f"Source: {d.country.source}")
            w()
            w(f"Verified: *{d.country.verified_on}*")
            w()
        for f in d.findings:
            w(f"- {f}")
            w()
        if d.country.known and d.country.residency_tests:
            w("Residency day tests recorded for this country:")
            w()
            w.table(["Test", "Days", "Measured over"],
                    [[t.label, t.days,
                      "the tax year" if t.window_years == 1
                      else f"{t.window_years} years"]
                     for t in d.country.residency_tests])
            w()

    w("## What this will not do")
    w()
    w("- **It will not tell you whether your Roth is taxable where you are "
      "going.** It tells you whether anyone has checked, and what follows if "
      "the answer is yes.")
    w("- **It encodes no treaty article numbers and no foreign tax rates.** "
      "A plausible-looking citation is worse than an admitted gap, because it "
      "stops the reader looking.")
    w("- **It does not reason by analogy between countries.** Destinations "
      "differ on exactly the point that matters, so an absent country is "
      "absent rather than approximated.")
    w()
    w("**The weakest input is the destination's treatment of the wrapper** — "
      "not a number in this report, but the single assumption everything here "
      "hangs from. Nothing else in the report is close.")
    cli.disclaimer(w, "lib/pf/crossborder.py",
                   "Cross-border retirement taxation is contested and "
                   "treaty-dependent. This establishes the question to take to "
                   "a cross-border tax professional; it does not answer it.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Roth portability check",
                             required=REQUIRED, build=build))
