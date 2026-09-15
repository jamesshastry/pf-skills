#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Mortgage review — PMI, prepayment, and the refinance break-even."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, housing as H  # noqa: E402

REQUIRED = ["housing.mortgage"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    mo = F._dig(data, "housing.mortgage") or {}
    r = H.review_mortgage(
        balance=float(mo.get("balance") or 0),
        rate=float(mo.get("rate") or 0),
        term_years=int(mo.get("remaining_years") or 30),
        value=mo.get("property_value"),
        pmi_monthly=mo.get("pmi_monthly"),
        extra_monthly=float(mo.get("extra_monthly") or 0),
    )
    w.table(["", ""], [
        ["Balance", m(r.balance)],
        ["Rate", f"{r.rate:.2%}"],
        ["Payment (P&I)", f"{m(r.payment)}/mo"],
        ["Loan-to-value", f"{r.ltv:.0%}" if r.ltv is not None else "**unknown**"],
    ])
    w()
    for f in r.findings:
        w(f"- {f}")
        w()
    cli.disclaimer(w, "lib/pf/housing.py")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Mortgage review", required=REQUIRED, build=build))
