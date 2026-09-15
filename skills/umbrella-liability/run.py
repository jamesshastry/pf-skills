#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Render the umbrella liability review for a facts file.

    uv run skills/umbrella-liability/run.py --facts inputs/facts.yml
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))

from pf import cli, facts as F, umbrella as U  # noqa: E402

REQUIRED = [
    "meta.jurisdiction.state",
    "household.balance_sheet",
    "household.members",
    "auto.coverage",
    "property.coverage",
]


money = cli.money


def build(data: dict, w: cli.Writer) -> None:

    prop = F._dig(data, "property") or {}
    a = U.assess(
        attachable_assets=F.attachable(data),
        household_income=F.household_income(data),
        auto_coverage=F._dig(data, "auto.coverage") or {},
        property_coverage=prop.get("coverage") or {},
        property_exclusions=prop.get("exclusions"),
        dependents=F.dependents(data),
        balance_sheet=F._dig(data, "household.balance_sheet") or [],
        in_force=F._dig(data, "umbrella.coverage"),
    )

    # ── headline ────────────────────────────────────────────────────────
    if a.in_force:
        head = f"**{money(a.in_force)} in force.**"
        if a.shortfall:
            head += f" Recommended **{money(a.recommended)}** — short by {money(a.shortfall)}."
        else:
            head += " At or above the recommended limit."
    else:
        head = f"**No umbrella in force.** Recommended **{money(a.recommended)}**."
    w(head)
    w("")
    w(
        f"Estimated **{money(a.cost_estimate[0])}–{money(a.cost_estimate[1])}/yr** "
        f"— {money(a.cost_per_million[0])}–{money(a.cost_per_million[1])} per "
        "million of cover."
    )

    # ── gate ────────────────────────────────────────────────────────────
    w("")
    w("## 1 · Attachment gate")
    w("")
    w("| | Policy | Coverage | Current | Required |")
    w("|---|---|---|---|---|")
    for g in sorted(a.gate, key=lambda g: g.ok):
        mark = "✅" if g.ok else "🚫"
        w(f"| {mark} | {g.policy} | {g.coverage} | {money(g.current)} | {money(g.required)} |")
    w("")
    if a.can_bind:
        w("**Underlying limits qualify.** An umbrella can be bound today.")
    else:
        w(
            f"**Cannot bind.** {len(a.failures)} underlying limit(s) fall "
            "below what carriers require. These are cheap to fix and must be "
            "fixed first — see `auto-insurance-review` and "
            "`renters-homeowners-review`."
        )

    # ── sizing ──────────────────────────────────────────────────────────
    w("")
    w("## 2 · Sizing")
    w("")
    w("| | |")
    w("|---|---|")
    w(f"| Attachable assets | {money(a.attachable)} |")
    w(f"| + {U._auto.GARNISHMENT_YEARS} years' gross income (garnishment proxy) | {money(U._auto.GARNISHMENT_YEARS * a.income)} |")
    w(f"| **Exposure** | **{money(a.exposure)}** |")
    w(f"| Rounded up to the nearest million | **{money(a.recommended)}** |")
    w("")
    w(
        "Sized against **attachable assets plus future earnings**, not net "
        "worth: retirement accounts are largely out of a creditor's reach and "
        "wages very much are not. Liability judgments also scale with the "
        "defendant's ability to pay — the same collision settles differently "
        "against someone with $50,000 and someone with $2M. Net worth is "
        "itself a risk factor."
    )
    w("")
    lo1, hi1 = U.cost(U.MIN_UMBRELLA)
    w(
        f"**Buying more than the minimum is the cheap part.** The first "
        f"million runs {money(lo1)}–{money(hi1)}; each million after it "
        f"{money(U.ADDITIONAL_MILLION_COST[0])}–"
        f"{money(U.ADDITIONAL_MILLION_COST[1])}. The underwriting is in the "
        "first layer, so if the limit is a close call, round up."
    )

    # ── what it does not cover ──────────────────────────────────────────
    w("")
    w("## 3 · What it does not cover")
    w("")
    for n in a.notes:
        w(f"- {n}")
    if a.exclusions_passed_through:
        w("")
        w(
            "**Exclusions pass through from the underlying policy.** An "
            "umbrella generally will not cover what the policy beneath it "
            "excludes by endorsement:"
        )
        for e in a.exclusions_passed_through:
            w(f"  - `{e}` — if this is moot, have the endorsement removed; a "
              "stale exclusion narrows the excess layer for no benefit.")

    w("")
    w("## 4 · Disclose before binding")
    w("")
    for r in a.riders:
        w(f"- {r}")

    w("")
    w("## 5 · Where to buy")
    w("")
    for line in U.where_to_buy(not a.can_bind):
        w(f"- {line}")

    w("")
    w("---")
    w("")
    w(
        "*Not financial, tax, or legal advice. Cost estimates are market "
        "ranges, not quotes. Thresholds are in `lib/pf/umbrella.py`; "
        "attachment points are imported from the underlying-policy modules so "
        "they cannot drift apart.*"
    )


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Umbrella liability review",
                             required=REQUIRED, build=build,
                             missing_hint="An umbrella review needs both underlying policies. Sizing without the attachment check produces a number you cannot buy."))
