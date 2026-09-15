#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Foreign account reporting — an obligation that already exists, or does not."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, reporting as R  # noqa: E402

REQUIRED = ["household.members"]
SEV = {"blocker": "🚫 **REQUIRED / UNRESOLVED**", "gap": "⚠️ Gap",
       "note": "· Note", "ok": "✅ Below threshold"}
ORDER = {"blocker": 0, "gap": 1, "note": 2, "ok": 3}
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    members = F._dig(data, "household.members") or []
    adults = [x for x in members if x.get("role") in ("primary", "spouse")]
    status = "married_joint" if len(adults) > 1 else "single"
    accounts = F._dig(data, "foreign_accounts")

    a = R.audit(accounts, filing_status=status,
                tax_home_abroad=bool(F._dig(data, "household.tax_home_abroad")),
                foreign_gifts_received=F._dig(data, "foreign_gifts_received"))

    w("**This is not a planning skill.** It establishes whether a filing "
      "obligation already exists — and if one does, it existed last year too. "
      "There is nothing here to weigh up: there is a threshold, and you are "
      "either over it or you do not yet know.")
    w()
    if a.blockers:
        w(f"**{len(a.blockers)} item(s) require action or cannot be resolved "
          f"from what is recorded.**")
    else:
        w("**Nothing currently required on what is recorded.**")
    w()
    w.table(["", ""], [
        ["Filing status assumed", status.replace("_", " ")],
        ["Tax home", "abroad" if a.abroad else "United States"],
        ["Foreign accounts recorded", a.account_count],
        ["…with a maximum value recorded", a.account_count - a.unknown_accounts],
        ["Aggregate of known maxima", m(a.known_max)],
    ])

    if accounts:
        w()
        w.table(["Account", "Kind", "Country", "Max during year"],
                [[x.get("name", "?"), (x.get("kind") or "—").replace("_", " "),
                  x.get("country", "—"),
                  m(x["max_value_during_year"])
                  if x.get("max_value_during_year") is not None
                  else "**not recorded**"] for x in accounts])

    w()
    w("## Findings")
    w()
    for f in sorted(a.findings, key=lambda x: ORDER[x.severity]):
        w(f"- {SEV[f.severity]} **{f.form}** — {f.detail}")
        w()

    w("## The three things people get wrong")
    w()
    w("1. **FBAR is aggregate, and it is the maximum.** Not per account, and "
      "not the year-end balance. Five accounts of $3,000 cross the threshold. "
      "An account that peaked at $12,000 in March and ended the year at $400 "
      "crosses it. Checking December statements is the standard error.")
    w("2. **FBAR and FATCA are different filings.** One goes to FinCEN "
      "separately; the other attaches to the return. Filing one does not "
      "satisfy the other, and the same account is often reportable on both.")
    w("3. **Signature authority counts.** An account you can direct but do "
      "not own is reportable. Most commonly missed, because it does not feel "
      "like your money.")

    w()
    w("## If a prior year was missed")
    w()
    w("**Do not quietly file a late form and hope.** The remediation paths "
      "differ sharply depending on whether the failure was non-wilful, and "
      "choosing the wrong one forfeits protections that were available. This "
      "is the point at which to involve a cross-border CPA — before filing "
      "anything, not after.")
    cli.disclaimer(w, "lib/pf/reporting.py",
                   "Thresholds are statutory but recorded as unverified; "
                   "penalties for these forms are severe and the remediation "
                   "path is not a decision to make alone.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Foreign reporting audit",
                             required=REQUIRED, build=build))
