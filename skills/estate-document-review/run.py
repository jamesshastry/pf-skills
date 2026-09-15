#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Estate documents — existence, staleness, and whether the trust is funded."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, estate as E, facts as F  # noqa: E402

REQUIRED = ["household.members"]
SEV = {"blocker": "🚫 **BLOCKER**", "gap": "⚠️ Gap", "note": "· Note", "ok": "✅ OK"}
LABEL = {"qdot": "QDOT (non-citizen spouse)", "domicile": "Domicile basis",
         "will": "Will", "financial_poa": "Financial power of attorney",
         "healthcare_poa": "Healthcare power of attorney",
         "advance_directive": "Advance directive",
         "revocable_trust": "Revocable trust",
         "revocable_trust_funding": "→ trust funding"}


def build(data: dict, w: cli.Writer) -> None:
    docs = F._dig(data, "estate.documents")
    members = F._dig(data, "household.members") or []
    non_citizen_spouse = any(
        m.get("role") == "spouse" and m.get("us_status")
        and m.get("us_status") != "citizen" for m in members)
    dom = F._dig(data, "household.domicile") or {}
    a = E.audit_documents(
        docs or [], today=F.as_of(data),
        non_citizen_spouse=non_citizen_spouse,
        domicile_determined=dom.get("determined") if dom else None)

    if docs is None:
        w("> `estate.documents` is absent entirely, so **everything below is "
          "reported as not recorded**. That is the correct reading: nobody has "
          "written down what exists. It is not the same as nothing existing.")
        w()

    w(f"**{len(a.blockers)} blocker(s)** · {a.unknown} not recorded.")
    w()
    w.table(["", "Document", "Finding"],
            [[SEV[f.severity], LABEL.get(f.subject, f.subject), f.detail]
             for f in a.sorted])

    w()
    w("## What each one actually does")
    w()
    w("The distinction people miss: **a will only operates on death.** If you "
      "are alive and incapacitated it does nothing at all — that is what the "
      "powers of attorney are for, and their absence bites far sooner than a "
      "missing will does.")
    w()
    w("| Document | Operates | On what |")
    w("|---|---|---|")
    w("| Financial POA | While alive, incapacitated | Money, bills, accounts |")
    w("| Healthcare POA | While alive, incapacitated | Medical decisions |")
    w("| Advance directive | While alive, incapacitated | Your stated wishes |")
    w("| Will | On death | Anything not passing by designation or title |")
    w("| Trust | Both | Only what is actually titled into it |")
    w()
    w("Note the last column on the will. Beneficiary designations and joint "
      "title pass **outside** it, which for most households is the majority "
      "of the money — see `beneficiary-audit`, which is where the real "
      "exposure usually sits.")

    w()
    w("## Review triggers")
    w()
    for t in ["A birth, adoption, death, marriage, or divorce in the family",
              "A move to another state — estate, property, and marital-property "
              "rules differ, sometimes materially",
              "A named executor, trustee, guardian, or agent becoming unable "
              "or unsuitable",
              "A significant change in assets, especially a new property or "
              "business interest",
              f"Nothing at all having happened for {E.DOCUMENT_REVIEW_YEARS} years"]:
        w(f"- {t}")

    cli.disclaimer(w, "lib/pf/estate.py",
                   "This is a completeness audit, not a legal review. It "
                   "checks whether documents exist and are current, not "
                   "whether they say the right things.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Estate document review",
                             required=REQUIRED, build=build))
