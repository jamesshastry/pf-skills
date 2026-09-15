#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Cash yield review — after tax, because gross gets it backwards."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cash as K, cli, facts as F  # noqa: E402

REQUIRED = ["household.balance_sheet"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    tax = K.TaxProfile(
        federal=F._dig(data, "assumptions.marginal_tax_rate"),
        niit=F._dig(data, "assumptions.niit_rate"),
        state=F._dig(data, "assumptions.state_tax_rate"),
        state_code=F._dig(data, "meta.jurisdiction.state"),
    )
    r = K.review_yield(
        F._dig(data, "household.balance_sheet") or [],
        benchmark_apr=F._dig(data, "assumptions.cash_benchmark_apr"),
        benchmark_as_of=F._dig(data, "assumptions.cash_benchmark_as_of"),
        benchmark_label=F._dig(data, "assumptions.cash_benchmark_label"),
        benchmark_state_exempt=bool(
            F._dig(data, "assumptions.cash_benchmark_state_tax_exempt")),
        tax=tax,
    )

    if not r.lines:
        for f in r.findings:
            w(f"⚠️ {f}")
        return

    basis = "after tax" if r.after_tax else "gross"
    if r.total_foregone > 0:
        w(f"**{m(r.total_foregone)}/yr is being left on the table** ({basis}).")
        if r.total_durable > 0:
            w()
            w(f"Of which **{m(r.total_durable)}/yr is durable** — the part that "
              "survives the two yields converging.")
    else:
        w(f"✅ **Liquid holdings are at or above the benchmark** ({basis}).")
    w()

    bench = f"**{r.benchmark:.2%}** gross"
    if r.after_tax:
        net = K.after_tax_yield(r.benchmark, state_exempt=r.benchmark_state_exempt,
                                tax=r.tax)
        bench += f", **{net:.2%}** after tax"
    w(f"Benchmark: {r.benchmark_label or 'unnamed'} — {bench}"
      + (f", as of {r.benchmark_as_of}." if r.benchmark_as_of
         else " — no date recorded; confirm it is current."))
    if r.after_tax:
        w()
        parts = [f"{r.tax.federal:.1%} federal"]
        if r.tax.niit:
            parts.append(f"{r.tax.niit:.1%} NIIT")
        parts.append(f"{r.tax.state:.1%} {r.tax.state_code or 'state'}"
                     " (not on Treasury interest)")
        w("Rates applied: " + " + ".join(parts) + ".")
    w()

    if r.after_tax:
        w.table(["Holding", "Balance", "Gross", "State tax", "After tax", "Foregone/yr"],
                [[l.name, m(l.balance),
                  f"{l.gross:.2%}" if l.gross is not None else "**unknown**",
                  "exempt" if l.state_exempt else "taxable",
                  f"{l.after_tax:.2%}" if l.after_tax is not None else "—",
                  m(l.foregone) if l.foregone else ("—" if l.gross is not None else "?")]
                 for l in r.lines])
    else:
        w.table(["Holding", "Balance", "Gross yield", "Foregone/yr"],
                [[l.name, m(l.balance),
                  f"{l.gross:.2%}" if l.gross is not None else "**unknown**",
                  m(l.foregone) if l.foregone else ("—" if l.gross is not None else "?")]
                 for l in r.lines])
    w()
    for f in r.findings:
        w(f"- {f}")
        w()

    w("## Before acting")
    w()
    w("- **Enter yields net of expenses** — the SEC 7-day yield already is. "
      "Subtracting an expense ratio from a quoted yield double-counts it.")
    w("- **Check redemption fees.** A per-withdrawal charge makes a fund the "
      "wrong home for cash you actually draw on, whatever it yields.")
    w("- **Confirm settlement.** A placed order is not a held position, and a "
      "fund strikes at the next NAV.")
    cli.disclaimer(w, "lib/pf/cash.py",
                   "The benchmark and the tax rates come from your facts "
                   "file, not from a market feed or a tax table — keep them "
                   "current.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Cash yield review", required=REQUIRED, build=build))
