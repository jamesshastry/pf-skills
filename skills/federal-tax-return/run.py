#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Federal return workpaper — Form 1040 line by line, refund or balance due, penalty check."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, federal_return as R  # noqa: E402

REQUIRED = [
    "tax_return.tax_year",
    "tax_return.filing_status",
    "tax_return.taxpayers",
]
m = cli.money

STATUS = {"single": "single", "mfj": "married filing jointly",
          "mfs": "married filing separately", "hoh": "head of household",
          "qss": "qualifying surviving spouse"}


def _neg(x: float) -> str:
    return f"−{m(x)}" if x else m(0)


def s(x: float) -> str:
    """Signed money: a loss reads −$2,500, not $-2,500."""
    return f"−{m(-x)}" if x < 0 else m(x)


def build(data: dict, w: cli.Writer) -> None:
    tr = F._dig(data, "tax_return")
    try:
        r = R.compute(tr)
    except R.FederalReturnError as e:
        w("## Stopped — the inputs cannot support a return")
        w()
        w(f"- {e}")
        for item in e.missing:
            w(f"- missing: `tax_return.{item}`")
        w()
        w("See SCHEMA.md `tax_return`. Fill this in rather than letting the skill guess.")
        return

    w(f"**Tax year {r.tax_year}**, {STATUS[r.filing_status]}. Parameters: "
      f"{r.table_source}.")
    if r.projection:
        w()
        w(f"> **Projection.** No parameter table for {r.tax_year} ships with the "
          "module; the nearest year's figures were used.")
    w()

    w("## The answer")
    w()
    if r.refund_or_due is None:
        w("**Refund or balance due cannot be determined** — a payment figure is unknown.")
    elif r.refund_or_due >= 0:
        w(f"**Refund of {m(r.refund_or_due)}** on total tax of {m(r.total_tax)}.")
    else:
        w(f"**Balance due of {m(-r.refund_or_due)}** on total tax of {m(r.total_tax)}.")
    w()
    for b in r.bounds:
        w(f"> {b}")
        w()
    for line in r.findings:
        w(f"- {line}")
    w()

    w("## Income (Form 1040 lines 1–9)")
    w()
    rows = [["1a", "Wages (W-2 box 1, incl. RSU and bonus)", m(r.wages)],
            ["2a", "Tax-exempt interest (not taxed)", m(r.tax_exempt_interest)],
            ["2b", f"Taxable interest (incl. {m(r.us_treasury_interest)} Treasury)",
             m(r.taxable_interest)],
            ["3a", "Qualified dividends", m(r.qualified_dividends)],
            ["3b", "Ordinary dividends", m(r.ordinary_dividends)],
            ["4b", "Taxable IRA distributions / conversions", m(r.ira_taxable)]]
    if r.taxable_social_security:
        rows.append(["6b", "Taxable Social Security benefits", m(r.taxable_social_security)])
    rows += [
            ["7", f"Capital gain or (loss): short {s(r.short_term_net)}, long "
                  f"{s(r.long_term_net)} incl. {m(r.capital_gain_distributions)} "
                  "distributions", s(r.net_capital_gain_or_loss)],
            ["8", "Schedule 1: taxable state/local tax refund", m(r.state_refund_taxable)],
            ["8", "Schedule 1: business income or (loss)", s(r.schedule_c_net)]]
    if r.k1_detail:
        rows.append(["8", "Schedule 1: K-1 ordinary income and guaranteed payments "
                          "(Schedule E part II)", s(r.k1_income)])
    if r.hsa_taxable_distributions:
        rows.append(["8", "Schedule 1: non-qualified HSA distributions",
                     m(r.hsa_taxable_distributions)])
    rows.append(["9", "**Total income**", f"**{m(r.total_income)}**"])
    w.table(["Line", "Item", "Amount"], rows)
    w()
    if r.foreign_income:
        w(f"Foreign-source income of {m(r.foreign_income)} (interest, dividends and "
          "net gains) is included in the lines above, not added separately.")
        w()
    if r.schedule_c_detail:
        w.table(["Business", "Owner", "Receipts", "Expenses", "Home office", "Net"],
                [[b["business"], b["owner"], m(b["gross_receipts"]), m(b["expenses"]),
                  m(b["home_office_allowed"]), s(b["net"])] for b in r.schedule_c_detail])
        w()

    if r.k1_detail:
        w.table(["K-1", "Form", "Owner", "Ordinary", "Guaranteed payments",
                 "SE earnings", "QBI", "Distributions (informational)"],
                [[k["entity"], k["form"], k["owner"], s(k["ordinary_business_income"]),
                  m(k["guaranteed_payments"]), s(k["se_earnings"]), s(k["net"]),
                  m(k["distributions"]) if k["distributions"] is not None else "unknown"]
                 for k in r.k1_detail])
        w()
        w("K-1 interest and dividends are included in lines 2b and 3b above.")
        w()

    w("## Adjustments and AGI")
    w()
    labels = {"hsa_deduction": "HSA deduction (Form 8889)",
              "half_se_tax": "Deductible half of SE tax",
              "ira_deduction": "Deductible IRA contribution"}
    rows = [[labels[k], _neg(v)] for k, v in r.adjustments.items()]
    rows.append(["**Adjusted gross income (line 11)**", f"**{m(r.agi)}**"])
    w.table(["", "Amount"], rows)
    w()

    w("## Deduction")
    w()
    it = r.itemized
    rows = [["State and local income tax (incl. SDI)", m(it["state_income_tax"])],
            ["Property tax", m(it["property_tax"])],
            ["Other state and local taxes", m(it["other_state_local_taxes"])],
            [f"SALT allowed (cap {m(it['salt_cap'])})", m(it["salt_allowed"])],
            ["Medical above 7.5% of AGI", m(it["medical"])],
            ["Mortgage interest (after debt limit)", m(it["mortgage_interest"])],
            ["Charitable (after any AGI floor)", m(it["charitable"])],
            ["2/37 limitation", _neg(-it["limitation_2_37"])],
            ["**Itemized total**", f"**{m(r.itemized_total)}**"],
            ["**Standard deduction** (incl. 65+/blind)", f"**{m(r.standard_deduction)}**"]]
    w.table(["Schedule A", "Amount"], rows)
    w()
    if r.itemizes:
        w(f"**Deduction used: itemized** — {m(r.deduction_used)}.")
    elif r.nonitemizer_charitable:
        w(f"**Deduction used: standard** — {m(r.standard_deduction)} plus "
          f"{m(r.nonitemizer_charitable)} non-itemizer charitable deduction = "
          f"{m(r.deduction_used)}.")
    else:
        w(f"**Deduction used: standard** — {m(r.deduction_used)}.")
    w()

    w("## Tax and credits")
    w()
    rows = [["12", "Deduction", _neg(r.deduction_used)],
            ["13a", "Qualified business income deduction", _neg(r.qbi_deduction)]]
    if r.senior_deduction:
        rows.append(["13b", "Senior deduction (65+, Schedule 1-A)", _neg(r.senior_deduction)])
    rows += [["15", "**Taxable income**", f"**{m(r.taxable_income)}**"],
             ["16", f"Regular tax ({m(r.preferential_income)} at capital-gain rates; "
                    f"ordinary marginal rate {r.marginal_rate:.0%})", m(r.regular_tax)],
             ["17", "Alternative minimum tax (Form 6251)", m(r.amt)]]
    names = {"foreign_tax_credit": "Foreign tax credit",
             "child_and_other_dependent_credit": "Child tax credit / credit for other dependents",
             "additional_child_tax_credit": "Additional child tax credit (refundable)",
             "excess_social_security": "Excess Social Security withheld (refundable)"}
    for k, v in r.credits.items():
        if k in ("foreign_tax_credit", "child_and_other_dependent_credit"):
            rows.append(["19–20", names[k], _neg(v)])
    w.table(["Line", "Item", "Amount"], rows)
    w()

    w("## Other taxes (Schedule 2)")
    w()
    labels = {"self_employment_tax": "Self-employment tax (Schedule SE)",
              "additional_medicare_tax": "Additional Medicare Tax (Form 8959)",
              "niit": "Net investment income tax (Form 8960)",
              "hsa_additional_tax": "HSA 20% additional tax"}
    rows = [[labels[k], m(v)] for k, v in r.other_taxes.items()]
    rows.append(["**Total tax (line 24)**", f"**{m(r.total_tax)}**"])
    w.table(["", "Amount"], rows)
    w()

    w("## Payments")
    w()
    rows = [["Federal income tax withheld (W-2 box 2)", m(r.withholding["w2_federal"])],
            ["Additional Medicare Tax withheld (Form 8959)",
             m(r.withholding["additional_medicare_withheld"])],
            ["Federal tax withheld on SSA-1099", m(r.withholding["ssa_1099_federal"])],
            ["Estimated payments", m(r.estimated_payments) if r.estimated_payments is not None
             else "unknown"]]
    for k, v in r.credits.items():
        if k in ("additional_child_tax_credit", "excess_social_security"):
            rows.append([names[k], m(v)])
    rows.append(["**Total payments**", f"**{m(r.total_payments)}**"
                 if r.total_payments is not None else "**unknown**"])
    w.table(["", "Amount"], rows)
    w()

    w("## Underpayment penalty (Form 2210 safe harbor)")
    w()
    h = r.penalty_safe_harbor
    prior = (f"{h['prior_year_pct']:.0%} of prior-year tax = {m(h['prior_year_required'])}"
             if h["prior_year_required"] is not None else "prior-year tax not recorded")
    w(f"Required: the lesser of 90% of this year's tax ({m(h['current_year_90'])}) "
      f"and {prior} → **{m(h['required_annual'])}**.")
    w()
    if h["quarters"]:
        w.table(["Installment due", "Required (cumulative)", "Paid (cumulative)", "Short"],
                [[q["due"], m(q["required_cumulative"]), m(q["paid_cumulative"]),
                  m(q["shortfall"])] for q in h["quarters"]])
        w()
        w("Withholding is treated as paid evenly through the year.")
        w()
    verdict = {True: "**Safe harbor met**", False: "**Safe harbor missed**",
               None: "**Cannot be determined**"}[h["met"]]
    w(f"{verdict}" + (f" — {h['reason']}." if h.get("reason") else "."))
    if h["met"] and r.refund_or_due is not None and r.refund_or_due < 0:
        w()
        w(f"No penalty, but the {m(-r.refund_or_due)} balance is still due with the return.")
    w()

    w(f"## Estimated payments for {r.next_year_estimates['tax_year']}")
    w()
    ny = r.next_year_estimates
    w(f"Safe harbor for next year: {ny['basis_pct']:.0%} of this year's tax = "
      f"{m(ny['target'])}. Assuming withholding repeats at "
      f"{m(ny['assumed_withholding'])}, pay **{m(ny['quarterly'])} per quarter** "
      f"({', '.join(ny['due'])}). Paying 90% of next year's actual tax instead is "
      "allowed but needs a projection this report does not make.")
    w()

    cf = r.carryforwards
    rows = []
    if cf["capital_loss"]["short"] or cf["capital_loss"]["long"]:
        rows.append(["Capital loss (short / long)",
                     f"{m(cf['capital_loss']['short'])} / {m(cf['capital_loss']['long'])}"])
    for k, v in cf["home_office"].items():
        rows.append([f"Home office (Form 8829) — {k}", m(v)])
    if cf["qbi_loss"]:
        rows.append(["Qualified business loss", m(cf["qbi_loss"])])
    if cf.get("charitable"):
        rows.append(["Charitable contributions above the AGI limits", m(cf["charitable"])])
    if cf["foreign_tax_credit"]:
        rows.append(["Foreign tax credit", m(cf["foreign_tax_credit"])])
    for k, v in cf["ira_basis"].items():
        rows.append([f"IRA nondeductible basis (Form 8606) — {k}", m(v)])
    if rows:
        w("## Carried to next year")
        w()
        w.table(["Item", "Amount"], rows)
        w()

    w("## Forms and schedules triggered")
    w()
    w(", ".join(r.forms) + ".")
    w()
    w("## Document checklist")
    w()
    for d in r.documents:
        w(f"- [ ] {d}")
    if r.missing:
        w()
        w("**Not recorded** (listed, never read as zero):")
        w()
        for item in r.missing:
            w(f"- `tax_return.{item}`")
    w()
    w("**Weakest input:** cost basis on the 1099-B and the year-end traditional "
      "IRA balance — both come from records outside the year's forms, and each "
      "moves taxable income dollar for dollar.")
    cli.disclaimer(w, "lib/pf/federal_return.py",
                   "This is a workpaper for checking a return, not a filed return; "
                   "it does not e-file.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Federal Tax Return Workpaper", required=REQUIRED,
                             build=build))
