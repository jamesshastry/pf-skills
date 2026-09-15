#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Citizenship, immigration status and domicile — and what they change."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, status as S  # noqa: E402

REQUIRED = ["household.members"]
SEV = {"blocker": "🚫 **BLOCKER**", "gap": "⚠️ Gap", "note": "· Note", "ok": "✅ OK"}
ORDER = {"blocker": 0, "gap": 1, "note": 2, "ok": 3}


def build(data: dict, w: cli.Writer) -> None:
    members = F._dig(data, "household.members") or []
    a = S.audit(members, domicile=F._dig(data, "household.domicile"))

    w("Three different statuses govern three different taxes, and they do not "
      "move together:")
    w()
    w.table(["Question", "Governed by"], [
        ["Is worldwide income taxed by the US?",
         "**Residence** — citizen, permanent resident, or substantial presence"],
        ["Is the estate taxed, and on what?",
         "**Domicile** — residence *plus* intent to remain"],
        ["Does a transfer to a spouse get the marital deduction?",
         "**The spouse's citizenship**"],
    ])
    w()
    w("A household can be fully US tax resident on income, fully US domiciled "
      "for estate purposes, and still lose the unlimited marital deduction "
      "because the surviving spouse holds a foreign passport.")

    w()
    w("## Recorded status")
    w()
    adults = [m for m in members if m.get("role") in ("primary", "spouse")]
    w.table(["Member", "Role", "Citizenship", "US status"],
            [[m.get("id"), m.get("role"),
              ", ".join(m.get("citizenship") or []) or "**not recorded**",
              m.get("us_status") or "**not recorded**"] for m in adults])
    w()
    dom = F._dig(data, "household.domicile") or {}
    w(f"Domicile: **{dom.get('country') or 'not recorded'}"
      + (f" / {dom['state']}" if dom.get("state") else "") + "** · "
      + ("determined deliberately" if dom.get("determined")
         else "**assumed, not determined**"))

    w()
    w("## Findings")
    w()
    for f in sorted(a.findings, key=lambda x: ORDER[x.severity]):
        w(f"- {SEV[f.severity]} **{f.area}** — {f.detail}")
        if f.affects:
            w(f"  *Affects: {', '.join('`' + s + '`' for s in f.affects)}*")
        w()

    if a.affected_skills:
        w("## Shipped conclusions to re-check")
        w()
        w("These skills were written before status was in the schema, so any "
          "conclusion they have already produced was reached without it:")
        w()
        for s in a.affected_skills:
            w(f"- `{s}`")
        w()
        w("Re-run them once status is recorded. Where a finding above is a "
          "blocker, treat the earlier conclusion as unverified rather than "
          "wrong — it may well survive, but nothing checked.")

    w()
    w("## What this skill will not tell you")
    w()
    w("Whether you *are* US domiciled, whether a QDOT is needed in your case, "
      "whether benefits will be payable where you intend to live, and "
      "anything turning on a treaty. Those are determinations, not lookups. "
      "This skill establishes **which questions apply to you** and which "
      "shipped conclusions were reached without asking them.")
    cli.disclaimer(w, "lib/pf/status.py",
                   "Immigration and estate-domicile questions need a lawyer, "
                   "not a skill.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Citizenship, status and domicile",
                             required=REQUIRED, build=build))
