#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""India tax return workpaper — status, income by head, regime choice, credits, U.S. hand-off."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, india_return as I  # noqa: E402

REQUIRED = [
    "household.members",
    "india_tax_return.financial_year",
    "india_tax_return.taxpayer.member",
    "india_tax_return.taxpayer.days_in_india_this_fy",
    "india_tax_return.usd_inr_rate",
]


def r(x) -> str:
    """Rupees, Indian digit grouping is not attempted; plain thousands."""
    if x is None:
        return "cannot be determined"
    return f"₹{x:,.0f}" if x >= 0 else f"−₹{-x:,.0f}"


def usd(x) -> str:
    return "cannot be determined" if x is None else cli.money(x)


POOL_LABEL = {
    "slab": "slab rate", "div_slab": "slab rate (dividend)", "stcg_slab": "STCG at slab", "stcg_111a": "STCG 20% (s.111A)",
    "ltcg_112": "LTCG 12.5% (s.112)", "ltcg_112a": "LTCG 12.5% above ₹1.25 lakh (s.112A)",
    "div_115a": "dividend 20% (s.115A)", "exempt": "exempt",
}


def build(data: dict, w: cli.Writer) -> None:
    itr = F._dig(data, "india_tax_return")
    try:
        ret = I.compute(itr, members=F._dig(data, "household.members") or [])
    except I.IndiaReturnError as e:
        w("## Stopped — the inputs cannot support an Indian return")
        w()
        w(f"- {e}")
        w()
        w("See SCHEMA.md `india_tax_return`. Fill this in rather than letting the "
          "skill guess.")
        return
    t, s = ret.table, ret.table.sections
    w(f"**FY {ret.financial_year}** — {t.act}. All amounts in INR on the Indian basis "
      "unless marked USD. A workpaper for review; it does not e-file.")
    w()
    w("## The decision")
    w()
    for line in ret.findings:
        w(f"- {line}")
    w()

    w("## Income by head")
    w()
    rows = []
    for ln in ret.lines:
        rows.append([ln.head.replace("_", " "), ln.name, r(ln.amount),
                     POOL_LABEL[ln.pool], r(ln.tds), ln.note])
    for p in ret.properties:
        if p.status == "self_occupied":
            treat = "nil annual value; interest per regime"
            amt = 0.0
        else:
            nav = p.annual_value - p.municipal_tax
            amt = nav * (1 - t.hp_standard_deduction) - p.interest
            treat = (f"NAV {r(nav)} less {t.hp_standard_deduction:.0%} and interest "
                     f"{r(p.interest)}")
        rows.append(["house property", f"{p.name} ({p.status.replace('_', ' ')})",
                     r(amt), "slab rate", r(p.tds), treat])
    w.table(["Head", "Item", "Income", "Taxed as", "TDS", "Treatment"], rows)
    w()

    w("## Regime comparison")
    w()
    n, o = ret.regimes["new"], ret.regimes["old"]
    def row(label, f):
        return [label, f(n), f(o)]
    w.table(["", "New regime", "Old regime"], [
        row("House property (net)", lambda x: r(x.hp_income)),
        row("Gross total income", lambda x: r(x.gross_total_income)),
        row("Chapter VI-A deductions", lambda x: r(sum(x.deductions.values()))),
        row("**Total income**", lambda x: f"**{r(x.total_income)}**"),
        row("— taxed at slab", lambda x: r(x.slab_income)),
        row("Slab tax", lambda x: r(x.slab_tax)),
        row("Special-rate tax", lambda x: r(sum(x.special_tax.values()))),
        row(f"Rebate {s['rebate']}", lambda x: r(x.rebate)),
        row("Surcharge (after marginal relief)", lambda x: r(x.surcharge)),
        row(f"Health & education cess {t.cess:.0%}", lambda x: r(x.cess)),
        row("**Tax liability**", lambda x: f"**{r(x.tax)}**"),
    ])
    w()
    for reg in ("new", "old"):
        for note in ret.regimes[reg].notes:
            w(f"- *{reg}:* {note}")
    carry = ret.regimes[ret.chosen].carry_forward
    if any(v > 0 for v in carry.values()):
        w()
        w("Carried forward (8 years, chosen regime): " + ", ".join(
            f"{k.replace('_', ' ')} {r(v)}" for k, v in carry.items() if v > 0) + ".")
    w()

    c = ret.credits
    w(f"## Credits and result — {ret.chosen} regime")
    w()
    w.table(["", "Amount"], [
        ["Tax liability", r(ret.regimes[ret.chosen].tax)],
        [f"Interest {s['int_late']} (late filing)", r(c.interest_234a)],
        [f"Interest {s['int_advance']} (advance-tax shortfall)", r(c.interest_234b)],
        [f"Interest {s['int_deferral']} (deferment, approximate)", r(c.interest_234c)],
        [f"Late fee {s['late_fee']}", r(c.late_fee)],
        ["Less TDS (Form 26AS/AIS)", r(c.tds)],
        ["Less advance tax", r(c.advance_tax)],
        ["Less self-assessment tax", r(c.self_assessment_tax)],
        ["**Balance (negative = refund)**", f"**{r(c.balance)}**"],
    ])
    w()
    for note in c.notes:
        w(f"- {note}")
    w()

    f = ret.filing
    w("## Filing")
    w()
    w(f"- Mandatory: **{'yes' if f.mandatory else 'not on the income test'}**.")
    w(f"- Due date {s['return']}: {f.due_date}. Belated {s['belated']}: by "
      f"{f.belated_deadline} (late fee; new regime only). Revised {s['revised']}: by "
      f"{f.revised_deadline} — confirm on the e-filing portal.")
    for note in f.notes:
        w(f"- {note}")
    w()

    u = ret.us
    w("## U.S. hand-off (Form 1116)")
    w()
    w(f"Rate: **{u.rate} INR per USD** — {u.rate_basis}.")
    w()
    w("For `tax_return.foreign` (`country: IN`):")
    w()
    w.table(["Category", "Indian taxable income (INR)", "USD", "Indian tax (INR)", "USD"], [
        ["passive", r(u.income_inr["passive"]),
         usd(u.income_usd["passive"] if u.income_usd else None),
         r(u.tax_inr), usd(u.tax_usd)],
        ["general", r(u.income_inr["general"]),
         usd(u.income_usd["general"] if u.income_usd else None), r(0), usd(0.0)],
    ])
    w()
    w("By type, losses netted within each type but not across types (the federal "
      "return's `foreign.interest`, `foreign.dividends`, "
      "`foreign.capital_transactions`, `foreign.rent`):")
    w()
    w.table(["Type", "INR", "USD"], [
        [k.replace("_", " "), r(v), usd(u.by_type_usd[k] if u.by_type_usd else None)]
        for k, v in u.by_type_inr.items()])
    w()
    if u.federal_foreign is not None:
        import yaml  # noqa: PLC0415 — already a runner dependency
        w("**For `federal-tax-return`** — paste into `tax_return.foreign` after "
          "re-splitting to the U.S. calendar year (USD, U.S. rules; `null` = unknown, "
          "which the federal return treats as a stop or a bound):")
        w()
        w("```yaml")
        w(yaml.safe_dump({"foreign": u.federal_foreign}, sort_keys=False,
                         allow_unicode=True, default_flow_style=False).rstrip())
        w("```")
        w()
        for item in u.federal_excluded:
            w(f"- {item}.")
        w()
    if u.india_exempt_detail:
        w(f"Exempt in India but U.S.-taxable, no Indian tax to credit: "
          f"{r(u.india_exempt_inr)} ({usd(u.india_exempt_usd)}) — "
          + ", ".join(f"{k} {r(v)}" for k, v in u.india_exempt_detail.items()) + ".")
    w()
    for note in u.notes:
        w(f"- {note}")
    w()

    w("## Documents to gather")
    w()
    for item in ret.checklist:
        w(f"- [ ] {item}")
    w()
    w(f"**Weakest input:** {ret.weakest_input}.")
    cli.disclaimer(w, "lib/pf/india_return.py",
                   f"Rates and limits are from the FY {t.financial_year} table "
                   f"({t.source}); marked unverified until checked against the "
                   "primary text.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="India Tax Return Workpaper", required=REQUIRED,
                             build=build))
