#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""One travel ledger, read by the 330-day test, bona fide residence, and the destination."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, presence as P  # noqa: E402

REQUIRED = ["household.members", "presence.days"]
MARK = {"ok": "✅", "fail": "🚫", "unknown": "· unknown"}


def build(data: dict, w: cli.Writer) -> None:
    spec = F._dig(data, "presence") or {}
    led = P.build_ledger(spec.get("days"))
    as_of = F.as_of(data)
    tax_year = spec.get("tax_year") or (as_of.year if as_of else None)

    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})

    w(f"Ledger: **{len(led.stays)} stay(s)**"
      + (f", {led.first.isoformat()} to {led.last.isoformat()} "
         f"({led.span_days} days)" if led.first else "")
      + f". Tax year taken as **{tax_year or 'not recorded'}**.")
    w()
    w(f"- Physical Presence Test counts {P.FULL_DAY_BASIS}.")
    w(f"- The destination and state counts below use the other basis: "
      f"{P.PART_DAY_BASIS}. **The same trip therefore produces different "
      "numbers in different rows, and both are correct.**")
    w()
    for f in led.findings:
        w(f"- ⚠️ {f}")
        w()

    # ── the 330-day test ────────────────────────────────────────────────
    r = P.physical_presence(led, tax_year=tax_year)
    w("## Physical Presence Test — 330 full days in any 12 months")
    w()
    if not r.determinable:
        for f in r.findings:
            w(f"🚫 {f}")
            w()
    else:
        head = ("✅ **Met**" if r.passes else
                f"🚫 **Not met — short by {r.shortfall} day(s)**")
        w(f"{head}, on the best 12-month window available.")
        w()
        w.table(["Window", "Full foreign days", "Against 330"], [
            [f"{r.window_start.isoformat()} → {r.window_end.isoformat()} "
             "(best rolling)",
             str(r.best_days),
             "pass" if r.passes else f"short {r.shortfall}"],
            [f"Calendar {tax_year}" if tax_year else "Calendar year",
             "—" if r.calendar_days is None else str(r.calendar_days),
             "—" if r.calendar_days is None else
             ("pass" if r.calendar_passes else "fail")],
        ])
        w()
        for f in r.findings:
            w(f"- {f}")
            w()
        w("**The window is the optimisation.** The test is any period of "
          "twelve consecutive months, chosen by you, and the exclusion is "
          "then prorated by the qualifying days that fall inside the tax "
          "year — so where the window sits changes both whether the "
          "exclusion is available and how much of it is.")
        w()
        w("A day at the edge of the ledger does not count, because a day "
          "with an unknown neighbour cannot be shown to have been complete. "
          "Extend the ledger a few days either side of every trip and those "
          "days come back.")
        w()

    # ── bona fide residence ─────────────────────────────────────────────
    b = P.bona_fide(spec.get("bona_fide"),
                    us_status=primary.get("us_status"),
                    citizenship=primary.get("citizenship"),
                    tax_year=tax_year)
    w("## Bona fide residence — the other route, and not a day count")
    w()
    w("This test is not arithmetic and no verdict is offered on it. What is "
      "checkable is checked; sufficiency is an IRS determination on facts and "
      "circumstances.")
    w()
    w.table(["Condition", "", "Why it decides claims"],
            [[c.label, MARK[c.state], c.detail] for c in b.checks])
    w()
    for f in b.findings:
        w(f"- {f}")
        w()
    w("**The abode question is not confined to this test.** §911 requires a "
      "tax home in a foreign country under *either* route, and an abode "
      "retained in the US defeats it — so a household that meets the 330-day "
      "count and keeps a home available in the US may still have no "
      "exclusion. The day count is necessary, not sufficient.")
    w()

    # ── the destination's own rule ──────────────────────────────────────
    t = P.destination_test(led, spec.get("destination"))
    w("## The destination's own residency threshold")
    w()
    if t.days is not None and t.threshold is not None:
        w.table(["Country", "Days present", "Recorded threshold", "Crossed"],
                [[t.country, str(t.days), str(t.threshold),
                  "yes" if t.crosses else "no"]])
        w()
    for f in t.findings:
        w(f"- {f}")
        w()
    w("**No country's residency rule is encoded in this repository.** The "
      "threshold above is whatever you recorded. Check how that country "
      "actually counts before relying on it — rolling windows, weighted "
      "prior years and split-year rules all exist, and a bare number does "
      "not capture them.")

    # ── the framing ─────────────────────────────────────────────────────
    w()
    w("## The perpetual traveler myth")
    w()
    w(P.PERPETUAL_TRAVELER_NOTE)
    w()
    w("**Weakest input:** the ledger itself. Every number above is a count of "
      "rows somebody typed. Reconstruct it from passport stamps, boarding "
      "passes and card transactions rather than memory, and keep it as you go "
      "— under examination the ledger is the evidence, and a calendar built "
      "afterwards is worth much less than one kept at the time.")
    cli.disclaimer(w, "lib/pf/presence.py",
                   "Qualifying for §911 also requires a tax home in a foreign "
                   "country, which days alone do not establish — see "
                   "`feie-vs-ftc`.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Foreign presence tests",
                             required=REQUIRED, build=build))
