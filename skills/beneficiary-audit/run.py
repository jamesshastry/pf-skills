#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Beneficiary audit — designations override the will."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, estate as E, facts as F  # noqa: E402

REQUIRED = ["household.members", "household.balance_sheet"]
SEV = {"blocker": "🚫 **BLOCKER**", "gap": "⚠️ Gap", "note": "· Note", "ok": "✅ OK"}


def build(data: dict, w: cli.Writer) -> None:
    members = F._dig(data, "household.members") or []
    items = [(r.get("name") or "account", r)
             for r in (F._dig(data, "household.balance_sheet") or [])]
    items += [(p.get("label") or p.get("id") or "policy", p)
              for p in (F._dig(data, "insurance.life") or [])]

    trust = next((d for d in (F._dig(data, "estate.documents") or [])
                  if d.get("type") == "revocable_trust"), None)
    a = E.audit_beneficiaries(items, members=members,
                              trust_funded=trust.get("funded") if trust else None)

    w("**A beneficiary designation overrides the will.** Whatever the estate "
      "documents say, these forms decide where these assets go — which is why "
      "an otherwise complete estate plan is routinely defeated by one form "
      "nobody revisited.")
    w()
    w(f"{a.checked} designation(s) examined · **{len(a.blockers)} blocker(s)** "
      f"· {a.unknown} not recorded.")
    w()
    w.table(["", "Asset or policy", "Finding"],
            [[SEV[f.severity], f.subject, f.detail] for f in a.sorted])

    if a.unknown:
        w()
        w("> **Not recorded is the most likely state to be hiding a problem.** "
          "It means nobody has looked, not that the designation is fine. Pull "
          "each form from the custodian and record what it actually says.")

    w()
    w("## How to fix")
    w()
    w("Beneficiary changes are made **with each custodian**, not by a lawyer "
      "and not in the will. Each institution has its own form, and the change "
      "is not effective until they confirm it — get the confirmation in "
      "writing and record the date.")
    w()
    w("Re-run after any birth, death, marriage, divorce, or new account.")
    cli.disclaimer(w, "lib/pf/estate.py",
                   "This is a completeness audit, not a legal review. Naming "
                   "a trust correctly is a question for the attorney who drew "
                   "it.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Beneficiary audit", required=REQUIRED, build=build))
