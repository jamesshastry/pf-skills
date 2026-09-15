#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Charitable giving — in kind, bunched, or straight out of the IRA."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import charity as G, cli, facts as F  # noqa: E402

REQUIRED = ["household.members", "assumptions.marginal_tax_rate"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    members = F._dig(data, "household.members") or []
    adults = [x for x in members if x.get("role") in ("primary", "spouse")]
    ages = [x.get("age") for x in adults if x.get("age") is not None]
    marginal = float(F._dig(data, "assumptions.marginal_tax_rate"))
    investable = (F.tier_total(data, F.LIQUID) + F.tier_total(data, F.AGE_RESTRICTED)
                  + F.tier_total(data, F.ILLIQUID))
    agi = F._dig(data, "household.agi")
    if agi is None:
        agi = F.household_income(data)

    # ── the lead: gifts in kind ─────────────────────────────────────────
    holdings = F._dig(data, "charity.candidate_holdings") or []
    r = G.review_gifts(holdings,
                       ltcg_rate=F._dig(data, "assumptions.ltcg_rate"),
                       niit_rate=F._dig(data, "assumptions.niit_rate"),
                       investable=investable or None)

    w("**Donating an appreciated security in kind does two things at once.** "
      "The full market value is deductible *and* the embedded capital gain is "
      "never realised by anyone — the charity is exempt, so the gain "
      "evaporates rather than transferring. The deduction is identical whether "
      "you give the share or sell it and give the cash, so the avoided gain is "
      "pure gain.")
    w()

    if holdings:
        if r.total_avoided > 0:
            w(f"**{m(r.total_avoided)} of capital gains tax avoided** by giving "
              f"the positions below in kind rather than selling first.")
            w()
        w.table(["Holding", "Value", "Basis", "Gain", "Long-term",
                 "Deductible", "Gain tax avoided", "Do this"],
                [[l.name, m(l.value), _cell(l.basis), _cell(l.gain),
                  {True: "yes", False: "**no**", None: "not recorded"}[l.long_term],
                  _cell(l.deductible), _cell(l.gain_tax_avoided),
                  l.recommendation] for l in r.lines])
        w()
        for l in r.lines:
            w(f"- **{l.name}** — {l.detail}")
            w()
    else:
        w("**No candidate holdings recorded.** Set "
          "`charity.candidate_holdings` to the lots you would consider giving, "
          "each with a `value`, a `basis` and `held_days`. Without a basis an "
          "appreciated gift and a forfeited loss are indistinguishable, and "
          "those are opposite recommendations.")
        w()
    for f in r.findings:
        w(f"- {f}")
        w()

    # ── bunching ────────────────────────────────────────────────────────
    w("## Bunching")
    w()
    standard = F._dig(data, "assumptions.standard_deduction")
    annual_gift = F._dig(data, "charity.annual_gift")
    other = F._dig(data, "assumptions.other_itemized_deductions")
    if standard is None or annual_gift is None or other is None:
        w("**Not computed.** Bunching needs `assumptions.standard_deduction`, "
          "`assumptions.other_itemized_deductions` and `charity.annual_gift`. "
          "The standard deduction is indexed and moves most years, so it is "
          "read from the facts file rather than encoded here — a figure that "
          "goes stale silently would produce a confident answer on the wrong "
          "side of the floor.")
        w()
        for name, value in (("assumptions.standard_deduction", standard),
                            ("assumptions.other_itemized_deductions", other),
                            ("charity.annual_gift", annual_gift)):
            if value is None:
                w(f"- `{name}` missing")
        w()
    else:
        p = G.best_bunch(standard_deduction=float(standard),
                         other_itemized=float(other),
                         annual_gift=float(annual_gift),
                         marginal_rate=marginal)
        w.table(["", ""], [
            ["Standard deduction", m(standard)],
            ["Other itemizable deductions", m(other)],
            ["Giving, per year", m(annual_gift)],
            ["Best window", f"{p.years} years"],
            ["Deductions taken — giving annually", m(p.annual_total)],
            ["Deductions taken — bunched", m(p.bunched_total)],
            ["Benefit at " + f"{marginal:.0%}", m(p.benefit)],
        ])
        w()
        for f in p.findings:
            w(f"- {f}")
            w()

        # ── AGI limits, sized against the plan the bunching implies ─────
        w("## AGI limits")
        w()
        appreciated = min(float(annual_gift) * p.years,
                          sum(l.value for l in r.lines if not l.at_a_loss)) \
            if r.lines else 0.0
        c = G.check_limits(agi=float(agi),
                           cash_gift=max(0.0, float(annual_gift) * p.years - appreciated),
                           appreciated_gift=appreciated)
        for f in c.findings:
            w(f"- {f}")
            w()

    # ── QCD ─────────────────────────────────────────────────────────────
    w("## Qualified charitable distributions")
    w()
    q = G.qcd(age=max(ages) if ages else None,
              annual_limit=F._dig(data, "assumptions.qcd_annual_limit"),
              rmd_applies=F._dig(data, "household.rmd_applies"))
    for f in q.findings:
        w(f"- {f}")
        w()

    w("## Before acting")
    w()
    w("- **Confirm the charity accepts in-kind transfers.** Most donor-advised "
      "funds do; many small charities cannot, which is one of the reasons a "
      "DAF exists.")
    w("- **Initiate the transfer early.** A share transfer settles on its own "
      "schedule, and a gift that lands on 2 January is deductible in the wrong "
      "year.")
    w("- **Give the specific long-term lot**, identified to the broker. A "
      "default lot selection can hand over the short-term one, which is "
      "deductible at basis.")
    cli.disclaimer(w, "lib/pf/charity.py",
                   "The standard deduction, QCD limit and capital gains rate "
                   "come from your facts file — all three are indexed or "
                   "household-specific and none is encoded here.")


def _cell(x) -> str:
    """`null` means nobody looked it up. A negative reads as a loss, not as a
    minus sign attached to a dollar sign."""
    if x is None:
        return "**not recorded**"
    if isinstance(x, (int, float)) and x < 0:
        return f"({m(-x)})"
    return m(x)


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Charitable giving strategy",
                             required=REQUIRED, build=build))
