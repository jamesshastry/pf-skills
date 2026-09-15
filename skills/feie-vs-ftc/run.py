#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Form 2555 or Form 1116 — priced both ways, and then the parts a price misses."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, expat as X, facts as F, presence as P  # noqa: E402

REQUIRED = [
    "household.members",
    "expat.foreign_earned_income",
    "expat.foreign_tax_on_earned_income",
]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    e = F._dig(data, "expat") or {}
    members = F._dig(data, "household.members") or []
    status = e.get("filing_status") or (
        "married_joint" if any(x.get("role") == "spouse" for x in members)
        else "single")
    kids = [x for x in members
            if x.get("role") == "dependent"
            and (x.get("age") is not None and x["age"] < X.CTC_QUALIFYING_AGE)]

    assumptions = F._dig(data, "assumptions") or {}
    try:
        brackets = X.parse_brackets(assumptions, status)
        bracket_error = ""
    except X.BracketError as exc:
        brackets, bracket_error = None, str(exc)

    c = X.compare(
        e,
        brackets=brackets,
        exclusion_cap=assumptions.get("feie_exclusion_cap"),
        children_under_17=len(kids),
        refundable_ctc_per_child=assumptions.get("additional_ctc_per_child"),
    )

    w(f"Filing status taken as **{status}**"
      + ("" if e.get("filing_status") else " (derived from the household, not "
         "recorded — set `expat.filing_status` if that is wrong)") + ". "
      + f"{len(kids)} child(ren) under {X.CTC_QUALIFYING_AGE}.")
    w()
    if bracket_error:
        w(f"🚫 **The bracket table supplied was rejected:** {bracket_error}.")
        w()

    if not c.determinable:
        for f in c.findings:
            w(f"⚠️ {f}")
            w()
        _structure(w)
        cli.disclaimer(w, "lib/pf/expat.py",
                       "Brackets, the standard deduction and the exclusion "
                       "cap are inputs here, never repository data — see "
                       "REVIEW.md A3 for why.")
        return

    # ── the two liabilities ─────────────────────────────────────────────
    verdict = {
        "ftc": "**The credit (Form 1116) is the better answer.**",
        "feie": "**The exclusion (Form 2555) is the better answer.**",
        "too_close": "**No recommendation is made.**",
    }[c.recommendation]
    w(verdict)
    w()

    w.table(
        ["", "Form 2555 — exclusion", "Form 1116 — credit"],
        [
            ["Excluded from income", m(c.feie.excluded), m(c.ftc.excluded)],
            ["Taxable income", m(c.feie.taxable_income), m(c.ftc.taxable_income)],
            ["US tax before credit", m(c.feie.precredit_tax),
             m(c.ftc.precredit_tax)],
            ["Foreign tax creditable", m(c.feie.creditable_foreign_tax),
             m(c.ftc.creditable_foreign_tax)],
            ["§904 limitation", m(c.feie.credit_limitation),
             m(c.ftc.credit_limitation)],
            ["Credit used", m(c.feie.credit_used), m(c.ftc.credit_used)],
            ["**US tax owed**", f"**{m(c.feie.net_tax)}**",
             f"**{m(c.ftc.net_tax)}**"],
            [f"Carryforward ({X.FTC_CARRYFORWARD_YEARS} yr)",
             m(c.feie.carryforward), m(c.ftc.carryforward)],
            ["Income supporting an IRA", m(c.feie.ira_compensation),
             m(c.ftc.ira_compensation)],
        ])
    w()
    if abs(c.current_year_delta) < 1:
        w("**This year's tax bill is the same either way.** That is common in "
          "a high-tax country, and it is exactly the case where deciding on "
          "the tax bill decides nothing — everything below is the whole "
          "decision.")
    else:
        cheaper = "credit" if c.current_year_delta > 0 else "exclusion"
        w(f"On this year's tax alone the **{cheaper}** is "
          f"{m(abs(c.current_year_delta))} cheaper.")
    w()
    for n in c.feie.notes + c.ftc.notes:
        w(f"- {n}")
    w()

    # ── what the two numbers leave out ──────────────────────────────────
    w("## What the two numbers leave out")
    w()
    w("This is the section the rule of thumb — *credit in a high-tax country, "
      "exclusion in a low-tax one* — does not have. It is directionally "
      "right and it answers a smaller question than the one asked.")
    w()
    if c.adjustments:
        w.table(["Consequence", "Favours", "Valued at"],
                [[a.label,
                  "Form 1116" if a.favours == "ftc" else "Form 2555",
                  m(a.value) if a.value is not None else "**not valued**"]
                 for a in c.adjustments])
        w()
        for a in c.adjustments:
            w(f"- {a.detail}")
            w()
    else:
        w("None of the tracked consequences applies: no IRA contribution "
          "planned, no children under "
          f"{X.CTC_QUALIFYING_AGE}, no unused credit, and no prior election "
          "recorded. Check each of those is genuinely absent rather than "
          "simply unrecorded.")
        w()

    for f in c.findings:
        w(f"- {f}")
        w()

    # ── boundary ────────────────────────────────────────────────────────
    w("## What this does not model")
    w()
    w("- **Self-employment tax.** §911 excludes income from *income* tax, not "
      "from SE tax. A self-employed expat owes roughly 15.3% on the excluded "
      "income anyway unless a totalization agreement covers them — and for "
      "some countries there is no agreement at all.")
    w("- **The foreign housing exclusion or deduction**, which rides on the "
      "same Form 2555 and can be worth more than people expect in an "
      "expensive city.")
    w("- **NIIT, AMT, itemised deductions, and the passive basket.** Foreign "
      "tax on investment income sits in a different credit basket and cannot "
      "be netted against the general one; nothing above attempts to.")
    w("- **State tax.** If a state still treats the household as resident, it "
      "may not conform to §911 at all. Run `state-domicile-exit`.")
    w("- **Any filing position.** This ends at a cross-border CPA or EA, and "
      "so does every other skill in this cluster.")
    w()
    w(f"**Weakest input:** {c.weakest_input}.")
    w()
    w(P.PERPETUAL_TRAVELER_NOTE)
    cli.disclaimer(w, "lib/pf/expat.py",
                   "Brackets, the standard deduction, the exclusion cap and "
                   "the refundable child-credit amount come from your facts "
                   "file, not from a tax table held here — keep them current "
                   "and year-matched.")


def _structure(w: cli.Writer) -> None:
    """Refusing the figure is not refusing the answer."""
    w("## The structure of the decision, which holds without the figures")
    w()
    w.table(["Moves the answer toward", "Because"], [
        ["Form 1116 — credit",
         "the local rate is high enough that the credit wipes out the US tax "
         "anyway, and the excess carries forward"],
        ["Form 1116 — credit",
         "excluded income cannot support an IRA contribution; the credit "
         "leaves the compensation intact"],
        ["Form 1116 — credit",
         "filing Form 2555 disqualifies the household from the **refundable** "
         "child tax credit entirely"],
        ["Form 1116 — credit",
         "earnings above the exclusion cap are taxed at the rates that would "
         "have applied without it (§911 stacking), so the exclusion is worth "
         "less at high income than it looks"],
        ["Form 2555 — exclusion",
         "the local rate is low or nil, so there is little foreign tax to "
         "credit and the exclusion is the only relief available"],
        ["Form 2555 — exclusion",
         "it is already elected, and revoking it locks the household out for "
         f"{X.FEIE_REVOCATION_LOCK_YEARS} years without IRS consent"],
    ])


if __name__ == "__main__":
    raise SystemExit(cli.run(title="FEIE vs FTC — Form 2555 or Form 1116",
                             required=REQUIRED, build=build))
