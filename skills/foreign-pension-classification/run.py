#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Foreign pensions — which bucket, and which forms follow from it."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, pension as N  # noqa: E402

REQUIRED = ["household.members"]
BUCKET = {
    N.TREATY_PROTECTED: "✅ treaty-protected",
    N.EMPLOYEES_TRUST_402B: "⚠️ §402(b) employees' trust",
    N.CONTESTED: "⚠️ contested — both readings live",
    N.FOREIGN_GRANTOR_TRUST: "🚫 foreign grantor trust",
    N.UNKNOWN_BUCKET: "❓ unknown — not in the table",
}
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    a = N.audit(F._dig(data, "foreign_pensions"))

    w("**This classifies; it does not conclude.** The output is a bucket and "
      "the filing obligation that follows from it. Which form is filed, on "
      "what basis, and whether a treaty claim applies to these specific facts "
      "is a cross-border preparer's call — but whether one is needed is a "
      "decision that can be made today.")
    w()

    if not a.classifications:
        for f in a.findings:
            w(f"⚠️ {f}")
            w()
        cli.disclaimer(w, "lib/pf/pension.py")
        return

    w.table(["Scheme", "Country", "Bucket", "Forms in scope"],
            [[c.label, c.scheme.country if c.scheme.known else "—",
              BUCKET[c.bucket], ", ".join(c.forms)]
             for c in a.classifications])
    w()
    for f in a.findings:
        w(f"- {f}")
        w()

    for c in a.classifications:
        w(f"## {c.label}")
        w()
        w(f"**{BUCKET[c.bucket]}** — {c.scheme.name if c.scheme.known else 'unrecognised scheme'}")
        w()
        if c.scheme.known:
            w(f"Source: {c.scheme.source} · verified: {c.scheme.verified_on}")
            w()
        for d in c.drivers:
            w(f"- {d}")
        if c.drivers:
            w()
        for f in c.findings:
            w(f"- {f}")
            w()
        if c.scheme.notes:
            w("Table notes:")
            w()
            for n in c.scheme.notes:
                w(f"- {n}")
            w()

    w("## What would change the answer")
    w()
    w(f"- **The contribution split.** Employee against employer contributions "
      f"to date is the weakest input in this report: absent it, a contested "
      f"scheme stays contested and the trust forms stay in scope. It is on "
      f"the annual statement.")
    w("- **Who directs the investments.** Holder-directed investment tips a "
      "non-treaty scheme toward the grantor-trust reading on its own.")
    w(f"- **A scheme not in the table.** Schemes checked: "
      f"{', '.join(N.schemes_available())}. Anything else returns unknown "
      f"rather than the nearest match — the UK and Australia both have "
      f"employer workplace pensions and opposite US treatment.")
    cli.disclaimer(w, "lib/pf/pension.py",
                   f"Form 3520 and 3520-A penalties start at "
                   f"{m(N.PENALTY_FLOOR)}; the scheme table is recorded as "
                   f"unverified and every entry should be checked against the "
                   f"treaty text before it is relied on.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Foreign pension classification",
                             required=REQUIRED, build=build))
