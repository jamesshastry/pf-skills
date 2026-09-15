#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Render the renters / homeowners review for a facts file.

    uv run skills/renters-homeowners-review/run.py --facts inputs/facts.yml
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))

from pf import cli, facts as F, property as P  # noqa: E402

REQUIRED = [
    "meta.jurisdiction.state",
    "household.members",
    "household.balance_sheet",
    "property.form",
    "property.coverage",
]

SEVERITY = {
    "blocker": "🚫 **BLOCKER**",
    "gap": "⚠️ Gap",
    "note": "· Note",
    "ok": "✅ OK",
}
ORDER = {"blocker": 0, "gap": 1, "note": 2, "ok": 3}


def build(data: dict, w: cli.Writer) -> None:

    prop = F._dig(data, "property")
    people = len(F._dig(data, "household.members") or [])
    liquid = F.liquid(data)
    attachable = F.attachable(data)
    umbrella = F._dig(data, "umbrella.coverage")

    a = P.assess(
        prop,
        people=people,
        liquid_assets=liquid,
        attachable_assets=attachable,
        umbrella_in_force=umbrella,
    )

    state = F._dig(data, "meta.jurisdiction.state")
    w(
        f"Facts as of **{F._dig(data, 'meta.as_of')}** · **{a.form}** · "
        f"{people} people · jurisdiction **{state}**"
    )
    w("")
    w(
        f"Premium **{P._money(prop.get('premium_annual'))}/yr**. Liquid assets "
        f"{P._money(liquid)}; attachable by a judgment {P._money(attachable)}."
    )

    for line in P.sequencing(a, umbrella):
        w("")
        w(f"> {line}")

    # ── findings table ──────────────────────────────────────────────────
    w("")
    w("## Findings")
    w("")
    w("| | Coverage | Current | Target |")
    w("|---|---|---|---|")
    findings = sorted(a.findings, key=lambda f: ORDER[f.severity])
    for f in findings:
        w(f"| {SEVERITY[f.severity]} | {f.key} | {f.current} | {f.target} |")

    w("")
    w("## Detail")
    for f in findings:
        if f.severity == "ok":
            continue
        w("")
        w(f"### {SEVERITY[f.severity]} — {f.key}")
        w("")
        w(f"**{f.current} → {f.target}.** {f.detail}")

    # ── the two derivations worth showing ───────────────────────────────
    w("")
    w("## Derivations")
    w("")
    w("**Contents replacement cost** *(benchmark — replace with an inventory)*")
    w("")
    w(
        f"{people} people × {P._money(P.CONTENTS_PER_PERSON[0])}–"
        f"{P._money(P.CONTENTS_PER_PERSON[1])} = "
        f"**{P._money(a.contents_benchmark[0])}–{P._money(a.contents_benchmark[1])}**"
    )
    w("")
    w("**Additional living expense**")
    w("")
    w("| | |")
    w("|---|---|")
    w(f"| Current housing cost | {P._money(prop.get('monthly_rent'))}/mo |")
    w(
        f"| Short-term equivalent | {P.TEMP_HOUSING_MULTIPLE[0]}×–"
        f"{P.TEMP_HOUSING_MULTIPLE[1]}× that |"
    )
    w(
        f"| Food and laundry uplift | {P._money(P.DISPLACED_UPLIFT_PER_PERSON)}"
        f"/person/mo × {people} |"
    )
    w(f"| **ALE** | **{P._money(a.ale_monthly[0])}–{P._money(a.ale_monthly[1])}/mo** |")
    w(
        f"| × {P.LOSS_OF_USE_TARGET_MONTHS} months | "
        f"**{P._money(a.loss_of_use_target[0])}–{P._money(a.loss_of_use_target[1])}** |"
    )

    if a.schema_gaps:
        w("")
        w("## Not reviewed — schema v1 does not carry these")
        w("")
        w(
            f"This is a **{a.form}** policy. The sections above (contents, "
            "loss of use, liability, sub-limits) apply to it unchanged, but "
            "the structure itself was not reviewed, and on an owned property "
            "that is the larger number:"
        )
        w("")
        for g in a.schema_gaps:
            w(f"- `{g}`")
        w("")
        w(
            "Propose these as a schema addition before relying on this review "
            "for a homeowners policy. Do not infer them."
        )

    w("")
    w("---")
    w("")
    w(
        "*Not financial, tax, or legal advice. Thresholds are in "
        "`lib/pf/property.py` with their reasons. The contents benchmark is "
        "the weakest input here — an inventory replaces it.*"
    )


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Renters / homeowners review",
                             required=REQUIRED, build=build))
