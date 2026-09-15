#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Render the auto-insurance review for a facts file.

    uv run skills/auto-insurance-review/run.py --facts inputs/facts.yml
    python3 skills/auto-insurance-review/run.py --facts inputs/facts.yml

Writes markdown to stdout. Redirect it into outputs/ (gitignored) if you want
to keep it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))

from pf import cli, auto, facts as F, jurisdiction  # noqa: E402

REQUIRED = [
    "meta.jurisdiction.state",
    "household.balance_sheet",
    "auto.vehicles",
    "auto.coverage",
    "auto.vehicles[].value",
    "auto.vehicles[].value_basis",
]


money = cli.money


def pct_band(b: auto.Band) -> str:
    if b.is_point:
        return f"{b.low:.1%}"
    return f"{b.low:.1%}–{b.high:.1%}"


def money_band(b: auto.Band) -> str:
    if b.is_point:
        return money(b.low)
    return f"{money(b.low)}–{money(b.high)}"


DECISION_LABEL = {
    "keep": "**Keep** comprehensive and collision",
    "drop_collision": "**Drop collision.** Comprehensive decided separately",
    "drop_both": "**Drop both** comprehensive and collision",
    "blocked": "**Cannot drop** — lienholder",
    "insufficient_data": "**Insufficient data**",
}


def build(data: dict, w: cli.Writer) -> None:
    state = F._dig(data, "meta.jurisdiction.state")
    rules = jurisdiction.rules_for(state)
    w(f"Facts as of **{F._dig(data, 'meta.as_of')}** · jurisdiction **{state}**")
    if not rules.known:
        w("")
        w(
            f"> ⚠️ **{state} is not in the rules table.** UM/UIM caps, UMPD "
            "availability, and statutory minimums below are unverified for "
            "this state. Confirm anything jurisdictional with the carrier."
        )

    liquid = F.liquid(data)
    attachable = F.attachable(data)
    income = F.household_income(data)
    buffer_months = F.months_of_spending(data)

    w("")
    w("## Capacity")
    w("")
    w("| | |")
    w("|---|---|")
    w(f"| Liquid assets | {money(liquid)} |")
    w(f"| Attachable by a judgment (liquid + illiquid) | {money(attachable)} |")
    w(f"| Household gross income | {money(income)} |")
    if buffer_months is not None:
        w(f"| Liquid buffer | {buffer_months:.1f} months of spending |")
    w("")
    w(
        "Retirement accounts are excluded from the attachable figure — ERISA "
        "plans are broadly creditor-protected and IRA protection is set by "
        "state. Absorbability below is measured against **liquid** assets "
        "only, never net worth."
    )

    # ── liability ───────────────────────────────────────────────────────
    cov = F._dig(data, "auto.coverage") or {}
    lia = auto.assess_liability(
        cov, attachable_assets=attachable, household_income=income, rules=rules
    )

    w("")
    w("## 1 · Liability — do this first")
    w("")
    w(
        f"Exposure: **{money(lia.exposure)}** — {money(attachable)} of "
        f"reachable assets plus {auto.GARNISHMENT_YEARS} years of gross income "
        "as a garnishment proxy. A judgment does not stop at your balance "
        "sheet."
    )
    w("")
    if lia.gaps:
        for g in lia.gaps:
            w(f"- ⚠️ {g}")
    else:
        w("- ✅ Liability limits meet the targets for this exposure.")
    for n in lia.jurisdiction_notes:
        w(f"- {n}")
    w("")
    w(
        f"Umbrella attachment: underlying limits of "
        f"{money(auto.UMBRELLA_ATTACHMENT['bi_per_person'])}/"
        f"{money(auto.UMBRELLA_ATTACHMENT['bi_per_accident'])} BI and "
        f"{money(auto.UMBRELLA_ATTACHMENT['pd'])} PD are what carriers "
        f"require. Currently **{'qualifies' if lia.qualifies_for_umbrella else 'does not qualify'}**. "
        f"First-cut size: **{money(lia.umbrella_first_cut)}** — the "
        "`umbrella-liability` skill owns that decision."
    )

    # ── physical damage ─────────────────────────────────────────────────
    w("")
    w("## 2 · Physical damage — the drop test")
    w("")
    vehicles = F._dig(data, "auto.vehicles") or []
    ref = F.as_of(data)
    any_drop = False

    for v in vehicles:
        a = auto.assess_vehicle(v, liquid_assets=liquid, buffer_months=buffer_months)
        if a.decision in ("drop_collision", "drop_both"):
            any_drop = True

        w(f"### {a.label}")
        w("")
        w(f"{DECISION_LABEL[a.decision]}")
        w("")
        if a.decision == "insufficient_data":
            for r in a.reasons:
                w(f"- {r}")
            w("")
            continue

        w("| | |")
        w("|---|---|")
        w(f"| Stated value | {money(v.get('value'))} (`{a.basis}`) |")
        if not a.basis_is_certain:
            w(f"| Implied ACV | {money_band(a.acv)} |")
        w(f"| Comp + collision premium | {money(a.premium_pd_annual)}/yr |")
        w(f"| Premium ÷ ACV | **{pct_band(a.ratio)}** (threshold {auto.RATIO_DROP_THRESHOLD:.0%}) |")
        w(f"| Uninsured loss if totalled | {money_band(a.uninsured_loss)} |")
        w(f"| …as a share of liquid assets | **{pct_band(a.loss_pct_liquid)}** |")
        if a.expected_recovery:
            w(f"| Expected annual recovery | {money_band(a.expected_recovery)} *(estimate)* |")
        if a.load:
            w(
                f"| Implied load | {a.load.low:.1f}×–{a.load.high:.1f}× "
                f"(typical {auto.TYPICAL_LOAD_RANGE[0]}–{auto.TYPICAL_LOAD_RANGE[1]}×) |"
            )
        w("")

        if not a.basis_is_certain:
            verdict = (
                "the ratio test is inconclusive on its own"
                if a.ratio_verdict == "inconclusive"
                else "the basis uncertainty does not change the answer"
            )
            w(
                f"> **`{a.basis}` is not ACV.** A carrier settles a total loss "
                f"at Actual Cash Value, so the ratio is a band, not a number — "
                f"and {verdict}."
            )
            w("")

        for r in a.reasons:
            w(f"- {r}")
        if a.comprehensive_note:
            w(f"- {a.comprehensive_note}")

        st = F.staleness(a.label, v.get("value_as_of"), ref)
        if st.is_stale:
            age = "undated" if st.days is None else f"{st.days} days old"
            w(f"- ⚠️ Valuation is {age}. Re-check before cancelling anything.")
        if v.get("lienholder") is None:
            w("- ⚠️ `lienholder` not stated. Confirm before calling the carrier.")
        w("")

    # ── UMPD + MedPay ───────────────────────────────────────────────────
    w("## 3 · Coverages that change when collision comes off")
    w("")
    for line in auto.umpd_guidance(rules, collision_being_dropped=any_drop):
        w(f"- {line}")
    w("")
    for line in auto.medpay_guidance(cov.get("medical_payments"), F.dependents(data)):
        w(f"- {line}")

    w("")
    w("---")
    w("")
    w(
        "*Not financial, tax, or legal advice. Thresholds are in "
        "`lib/pf/auto.py` with their reasons; every figure above is derived, "
        "not restated. Verify against your actual policy.*"
    )


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Auto insurance review",
                             required=REQUIRED, build=build))
