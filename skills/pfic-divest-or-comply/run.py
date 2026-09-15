#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""PFIC holdings — keep and pay the compliance cost, or get out."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, pfic as P  # noqa: E402

REQUIRED = ["household.members"]
m = cli.money


def _cell(x) -> str:
    """`null` here means nobody looked it up, and the table should say so. A
    negative gain is a position below basis — the cheapest PFIC to leave."""
    if x is None:
        return "**not recorded**"
    if isinstance(x, (int, float)) and x < 0:
        return f"({m(-x)})"
    return m(x)


def build(data: dict, w: cli.Writer) -> None:
    as_of = F.as_of(data)
    if as_of is None:
        w("## Stopped — `meta.as_of` is missing or unparseable")
        w()
        w("Every date in this report is measured from it, and the holding "
          "period is most of the charge. The clock is never read.")
        return

    holdings = F._dig(data, "pfic_holdings")
    if holdings is None:
        holdings = [a for a in (F._dig(data, "foreign_accounts") or [])
                    if a.get("kind") in ("foreign_mutual_fund", "foreign_etf",
                                         "unit_trust", "investment_linked_policy")]

    d = P.divest_or_comply(
        holdings,
        rates=P.RateSeries.from_facts(F._dig(data, "assumptions.pfic_rates")),
        as_of=as_of,
        annual_cost_per_form=F._dig(data, "assumptions.pfic_form_cost_annual"),
        ltcg_rate=F._dig(data, "assumptions.ltcg_rate"),
    )

    w("**The decision here is divest or comply, not which election.** QEF "
      "needs a PFIC Annual Information Statement most non-US retail funds do "
      "not issue, and mark-to-market needs marketable stock on a qualified "
      "exchange. Both are usually unavailable, which leaves §1291 by default — "
      "and §1291 by default is the case for selling.")
    w()

    if not d.funds:
        for f in d.findings:
            w(f"⚠️ {f}")
            w()
        cli.disclaimer(w, "lib/pf/pfic.py")
        return

    w.table(["Holding", "Value", "Basis", "Unrealised gain", "Acquired",
             "Regime available"],
            [[f.name, _cell(f.value), _cell(f.basis), _cell(f.gain),
              f.acquired.isoformat() if f.acquired else "**not recorded**",
              f.availability.regime] for f in d.funds])
    w()
    w(f"**{d.forms_per_year} Form 8621(s) a year** — the form is per fund, per "
      f"year, and it does not stop while the fund is held.")
    w()

    c = d.charge
    if c is not None:
        w("## The §1291 exit charge")
        w()
        if c.computable:
            w(f"**{m(c.total)} on {m(c.amount)} of gain** — an effective "
              f"**{c.effective_rate:.1%}**. Tax {m(c.tax)}, interest "
              f"{m(c.interest)}.")
        else:
            w(f"**Not computed.** {len(c.missing_rates)} rate(s) missing. The "
              f"allocation below is the shape of the exposure; the dollar "
              f"figure is withheld rather than partially computed.")
        w()
        w(f"Allocated pro-rata across {len(c.slices)} tax year(s), "
          f"{c.holding_years:.1f} years held.")
        w()
        w.table(["Year", "Days", "Slice", "Top rate that year", "Tax",
                 "Interest"],
                [[s.year, s.days, m(s.amount),
                  f"{s.top_rate:.0%}" if s.top_rate is not None else "**missing**",
                  m(s.tax) if s.tax is not None else "—",
                  ("current year — no interest" if s.current_year
                   else (m(s.interest) if s.interest is not None else "—"))]
                 for s in c.slices])
        w()
        if c.missing_rates:
            w("Missing from `assumptions.pfic_rates`:")
            w()
            for k in c.missing_rates[:24]:
                w(f"- `{k}`")
            if len(c.missing_rates) > 24:
                w(f"- …and {len(c.missing_rates) - 24} more")
            w()
        for f in c.findings:
            w(f"- {f}")
            w()

    w("## Regime availability, holding by holding")
    w()
    for f in d.funds:
        w(f"**{f.name}** — {f.availability.regime}")
        w()
        for r in f.availability.reasons:
            w(f"- {r}")
        w()

    w("## The comparison")
    w()
    for f in d.findings:
        w(f"- {f}")
        w()

    w("## Before acting")
    w()
    w("- **Email the fund administrator** and ask, in writing, whether a PFIC "
      "Annual Information Statement is issued. One email decides which half of "
      "this report applies, and a documented *no* is what supports the sale.")
    w("- **Get the acquisition dates from the original contract notes**, not "
      "from memory. The holding period drives the interest and the interest is "
      "most of the charge on a long hold.")
    w("- **Do not sell first and ask afterwards.** The sale is the event that "
      "triggers the charge; the tax year it lands in is a choice, and it stops "
      "being one once the order is placed.")
    cli.disclaimer(w, "lib/pf/pfic.py",
                   "The rate series comes from your facts file, not from a "
                   "table in this repository — verify it against the IRS "
                   "schedules before relying on any figure above.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="PFIC: divest or comply",
                             required=REQUIRED, build=build))
