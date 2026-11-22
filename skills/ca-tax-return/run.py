#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""California Form 540 workpaper — federal AGI to refund or balance due, next year's estimates, LLC tax."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import ca_return as CA, cli, facts as F  # noqa: E402

REQUIRED = [
    "meta.jurisdiction",
    "tax_return.tax_year",
    "tax_return.filing_status",
    "tax_return.state",
    "tax_return.taxpayers",
]
m = cli.money


def _stop(w: cli.Writer, reason: str) -> None:
    w("## Stopped — the inputs cannot support a California return")
    w()
    w(f"- {reason}")
    w()
    w("See SCHEMA.md `tax_return`. Fill this in rather than letting the skill guess.")
    cli.disclaimer(w, "lib/pf/ca_return.py",
                   "A workpaper for review, not a filed return.")


def _not_resident(w: cli.Writer, state: object, tax_year: object) -> None:
    w("## No California resident return")
    w()
    w(f"`tax_return.state` is **{state}** for {tax_year}, so this household does "
      "not file a California resident return (Form 540) for that year, and "
      "nothing is computed.")
    w()
    w("What would change that:")
    w()
    w("- **Moving to California, or out of it, during the year.** That is a "
      "part-year return (Form 540NR). It is not modelled here; take it to a "
      "preparer.")
    w("- **California-source income while living elsewhere** — a California "
      "rental, a California business, or wages for work done in California — "
      "can require a nonresident return (Form 540NR). Also not modelled.")
    w("- **An LLC organized, registered or doing business in California** owes "
      "the $800 annual tax and files Form 568 "
      "regardless of where its owner lives.")
    w()
    w("If the household has left California, the residency facts are reviewed "
      "by `state-domicile-exit`.")
    cli.disclaimer(w, "lib/pf/ca_return.py",
                   "A workpaper for review, not a filed return.")


def build(data: dict, w: cli.Writer) -> None:
    tr = F._dig(data, "tax_return")
    if str(tr.get("state") or "").upper() != "CA":
        _not_resident(w, tr.get("state"), tr.get("tax_year"))
        return
    try:
        from pf import federal_return as FR  # noqa: PLC0415
    except ImportError:
        _stop(w, "the federal return module (lib/pf/federal_return.py) is not "
                 "installed; California starts from federal AGI")
        return
    fed_error = getattr(FR, "FederalReturnError", ValueError)
    try:
        fr = FR.compute(tr)
        r = CA.compute(tr, CA.from_federal(fr))
    except (CA.CAReturnError, fed_error, ValueError) as e:
        _stop(w, str(e))
        return
    ref = F.as_of(data)

    basis = (f"**{r.tax_year} Form 540**, filing status `{r.filing_status}`. "
             "Nominal dollars, whole dollars as on the form.")
    if r.projection:
        basis += (f" **Projection:** {r.tax_year} indexed amounts are not in the "
                  f"module, so {r.table_year} tables are used.")
    w(basis)
    w()
    fed_missing = list(getattr(fr, "missing", []) or [])
    fed_bounds = list(getattr(fr, "bounds", []) or [])
    if fed_missing or fed_bounds or r.missing:
        w("> **Incomplete.** Figures below are bounded, not final — see "
          "*Missing documents*.")
        w()

    w("## Result")
    w()
    if r.balance_due:
        w(f"**Balance due: {m(r.balance_due)}** (line 100).")
    else:
        w(f"**Refund: {m(r.refund)}** (line 97).")
    w()

    w("## Schedule CA — federal AGI to California AGI")
    w()
    rows = [["13", "Federal AGI", "", "", m(r.federal_agi)]]
    rows += [[a.line, a.description, m(a.subtraction) if a.subtraction else "",
              m(a.addition) if a.addition else "", ""] for a in r.adjustments]
    rows += [["14 / 16", "Total subtractions / additions", m(r.subtractions),
              m(r.additions), ""],
             ["17", "**California AGI**", "", "", f"**{m(r.ca_agi)}**"]]
    w.table(["Line", "Item", "Subtract (B)", "Add (C)", "Amount"], rows)
    w()

    w("## Form 540")
    w()
    item = "not computed" if r.itemized_deduction is None else m(r.itemized_deduction)
    rows = [
        ["18", f"Deduction ({r.deduction_kind}; standard {m(r.standard_deduction)}, "
               f"itemized {item})", m(r.deduction)],
        ["19", "Taxable income", m(r.taxable_income)],
        ["31", "Tax (rate schedule)", m(r.tax)],
        ["32", "Exemption credits ("
               + ", ".join(f"{k} {v}" for k, v in r.exemption_counts.items() if v)
               + f"; before limit {m(r.exemption_before_limit)})",
         f"−{m(r.exemption_credits)}"],
        ["35", "Tax after exemption credits", m(r.tax_after_exemptions)],
    ]
    rows += [["40–46", name, f"−{m(amt)}"] for name, amt in r.credits]
    rows += [
        ["48", "Tax after credits", m(r.tax_after_credits)],
        ["61", "Alternative minimum tax", "not computed"],
        ["62", "Behavioral Health Services Tax", m(r.bhst)],
        ["63", "Other taxes", m(r.other_taxes)],
        ["64", "**Total tax**", f"**{m(r.total_tax)}**"],
        ["71", "CA income tax withheld (W-2 box 17, 1099s)", m(r.withholding)],
        ["72", "Estimated and extension payments", m(r.estimated_payments)],
        ["73", "Form 592-B / 593 withholding", m(r.other_withholding)],
        ["78", "**Total payments**", f"**{m(r.total_payments)}**"],
        ["91", "Use tax", "unknown" if r.use_tax is None else m(r.use_tax)],
    ]
    w.table(["Line", "Item", "Amount"], rows)
    w()

    w("## Estimated tax")
    w()
    if r.underpayment_required_annual is not None:
        w(f"**{r.tax_year} required annual payment:** "
          f"{m(r.underpayment_required_annual)}. Cumulative shortfall by "
          "installment (30/40/0/30, withholding spread evenly): "
          + ", ".join(m(x) for x in r.underpayment_shortfalls) + ".")
        w()
    if r.next_year_installments:
        w(f"**{r.tax_year + 1} payments** on the prior-year safe harbor "
          f"({m(r.next_year_required_annual)} required):")
        w()
        rows = []
        for i in r.next_year_installments:
            d = F.deadline(f"Q{i.number}", i.due, reference=ref)
            rows.append([str(i.number), i.due.isoformat(), f"{i.share:.0%}",
                         m(i.amount), d.urgency])
        w.table(["#", "Due", "Share", "Amount", "Status"], rows)
        w()

    if r.llcs:
        w("## LLC obligations (not on Form 540)")
        w()
        rows = []
        for o in r.llcs:
            due = o.annual_tax_due.isoformat() if o.annual_tax_due else "unknown"
            rows.append([o.name, m(o.total_income), m(o.annual_tax), due,
                         m(o.fee), o.return_due.isoformat(), o.note])
        w.table(["LLC", "Total CA income", "Annual tax", "Tax due", "Fee",
                 "Form 568 due", "Note"], rows)
        w()

    w("## Findings")
    w()
    for f in r.findings:
        w(f"- {f}")
    w()

    w("## Missing documents")
    w()
    if not (r.missing or fed_missing or fed_bounds):
        w("None recorded. Check the source documents before filing anyway.")
    for x in fed_missing:
        w(f"- (federal) {x}")
    for x in fed_bounds:
        w(f"- (federal bound) {x}")
    for x in r.missing:
        w(f"- {x}")
    w()
    w("**Weakest input:** the federal return. Every California line starts from "
      "federal AGI; an error there moves this return at the marginal CA rate.")
    cli.disclaimer(w, "lib/pf/ca_return.py",
                   "A workpaper for review, not a filed return. Part-year, "
                   "nonresident, other-state credit, kiddie tax, rental/passive "
                   "income and CA AMT are not computed.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="California Tax Return", required=REQUIRED, build=build))
