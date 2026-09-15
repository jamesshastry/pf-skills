#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Contribution space audit — is all tax-advantaged room being used?"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, contributions as C, facts as F  # noqa: E402

REQUIRED = ["household.members", "contributions.year"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    year = F._dig(data, "contributions.year")
    a = C.audit_space(F._dig(data, "contributions") or {},
                      members=F._dig(data, "household.members") or [],
                      year=year)

    if not a.limits_known:
        for f in a.findings:
            w(f"⚠️ {f}")
        return

    if a.total_unused > 0:
        w(f"**{m(a.total_unused)} of tax-advantaged space is unused this year.**")
    else:
        w("✅ **All recorded tax-advantaged space is used.**")
    w()

    w.table(["Space", "Used", "Ceiling", "Unused"],
            [[l.name, m(l.used), m(l.available) if l.available else "**unknown**",
              f"**{m(l.unused)}**" if l.unused else "—"] for l in a.lines])
    w()
    for l in a.lines:
        if l.note:
            w(f"- *{l.name}* — {l.note}")
    w()

    for f in a.findings:
        w(f"- {f}")
        w()

    w("## Order of operations")
    w()
    w("Space is not fungible, and filling it in the wrong order leaves value "
      "behind:")
    w()
    for i, s in enumerate([
        "**Employer match** — an immediate return nothing else matches. "
        "Never leave it on the table; see `employer-match-audit`.",
        "**HSA**, if eligible. The only triple-tax-advantaged account: "
        "deductible in, untaxed growth, untaxed out for medical.",
        "**Elective deferral to the §402(g) limit**, plus catch-up if age "
        "permits.",
        "**IRA space**, backdoor if income precludes a direct Roth.",
        "**After-tax plan contributions with in-plan conversion**, if and "
        "only if the plan offers both.",
        "**Taxable brokerage** — unlimited, and the right home for anything "
        "left over.",
    ], 1):
        w(f"{i}. {s}")
    w()
    w("> **After-tax contributions without a conversion route are a trap.** "
      "The earnings grow taxable-on-withdrawal, which is worse than a plain "
      "brokerage account for most people. Both features have to be present.")

    cli.disclaimer(w, "lib/pf/limits.py",
                   "Statutory limits change annually — verify against irs.gov "
                   "before acting.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Contribution space audit",
                             required=REQUIRED, build=build))
