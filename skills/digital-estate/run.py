#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Digital estate — can anyone actually get in?"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, estate as E, facts as F  # noqa: E402

REQUIRED = ["household.members"]
SEV = {"blocker": "🚫 **BLOCKER**", "gap": "⚠️ Gap", "note": "· Note", "ok": "✅ OK"}
LABEL = {"password_manager": "Password manager",
         "emergency_access_configured": "Emergency access configured",
         "account_inventory": "Written account inventory",
         "two_factor_recovery_documented": "2FA recovery codes recorded",
         "combination": "→ combination"}


def build(data: dict, w: cli.Writer) -> None:
    digital = F._dig(data, "estate.digital")
    a = E.audit_digital(digital)

    w("Every other estate document assumes someone can **reach** the accounts. "
      "Good security practice and good estate practice pull in opposite "
      "directions here: two-factor authentication and a strong password "
      "manager lock out heirs exactly as effectively as they lock out "
      "attackers.")
    w()
    if digital is None:
        w("> `estate.digital` is absent, so everything is **not recorded**.")
        w()
    w(f"**{len(a.blockers)} blocker(s)** · {a.unknown} not recorded.")
    w()
    w.table(["", "Check", "Finding"],
            [[SEV[f.severity], LABEL.get(f.subject, f.subject), f.detail]
             for f in a.sorted])

    w()
    w("## The test that matters")
    w()
    w("Not *does a plan exist* but: **could the person you have in mind "
      "actually log in tomorrow, without you, using only what they can find?**")
    w()
    w("Most households fail this while believing they pass, because the vault "
      "exists and the recovery path does not. Walk it once, end to end, rather "
      "than assuming.")
    w()
    w("## Worth knowing")
    w()
    w("- **Legacy or emergency access built into the password manager is the "
      "single highest-value setting here.** It is usually a few minutes and it "
      "converts the vault from a lockbox into a plan.")
    w("- Major platforms have their own inheritance mechanisms — legacy "
      "contacts, inactive-account handlers. They are per-platform, off by "
      "default, and independent of anything in your will.")
    w("- Terms of service frequently make an account **non-transferable**. An "
      "executor may have the legal right to the *value* of an asset and no "
      "right to the account holding it.")
    w("- A printed copy in the same place as the will beats anything clever. "
      "The recovery path must not itself require the credentials being "
      "recovered.")

    cli.disclaimer(w, "lib/pf/estate.py",
                   "A completeness audit. Access rules vary by platform and "
                   "by jurisdiction.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Digital estate", required=REQUIRED, build=build))
