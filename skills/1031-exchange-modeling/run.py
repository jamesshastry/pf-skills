#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Defer or pay — gain including recapture, boot, and the 45/180 clocks."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, realestate as R  # noqa: E402

REQUIRED = ["real_estate.exchange"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    r = R.model_exchange(
        F._dig(data, "real_estate.exchange") or {},
        as_of=F.as_of(data),
        recapture_rate=F._dig(data, "assumptions.depreciation_recapture_rate"),
        ltcg_rate=F._dig(data, "assumptions.ltcg_rate"),
        niit_rate=F._dig(data, "assumptions.niit_rate"),
        state_rate=F._dig(data, "assumptions.state_tax_rate"),
        discount_rate=F._dig(data, "assumptions.expected_return_apr"),
    )

    if r.fully_deferred:
        w(f"**Full deferral: the rule of thumb is satisfied.** "
          f"{m(r.total_gain)} of gain — including {m(r.unrecaptured_1250)} of "
          "depreciation recapture — defers into the replacement property.")
    elif r.recognized_gain > 0:
        w(f"**{m(r.recognized_gain)} of gain is recognised now** on "
          f"{m(r.cash_boot + r.debt_boot)} of boot. "
          f"{m(r.deferred_gain)} defers.")
    else:
        w("No gain is recognised, but the deferral rule is not cleanly "
          "satisfied — see below.")
    w()

    w("## The gain")
    w()
    w.table(["Line", "Amount"], [
        ["Sale price less selling costs", m(r.amount_realized)],
        ["Adjusted basis (cost + improvements − depreciation)",
         m(r.adjusted_basis)],
        ["**Total gain**", f"**{m(r.total_gain)}**"],
        ["— unrecaptured §1250 (taxed *above* the capital gain rate)",
         m(r.unrecaptured_1250)],
        ["— long-term capital gain", m(r.capital_gain)],
    ])
    w()
    if r.tax_if_sold is not None:
        w.table(["Scenario", "Tax"], [
            ["Sell outright", m(r.tax_if_sold)],
            ["Exchange as structured", m(r.tax_if_exchanged)],
            ["**Deferred**", f"**{m(r.tax_deferred)}**"],
        ])
        w()

    w("## Boot and the deferral rule")
    w()
    w.table(["Test", "Figure"], [
        ["Net equity from the sale", m(r.net_equity)],
        ["Equity going into the replacement", m(r.equity_into_replacement)],
        ["Cash boot", m(r.cash_boot)],
        ["Mortgage (debt) boot", m(r.debt_boot)],
        ["Gain recognised now", m(r.recognized_gain)],
    ])
    w()

    if r.identify_by and r.close_by:
        w("## The clocks")
        w()
        w.table(["Deadline", "Date", "Days remaining"], [
            [f"Identify in writing to the QI ({R.EXCHANGE_IDENTIFY_DAYS} days)",
             r.identify_by.isoformat(),
             "—" if r.days_to_identify is None else str(r.days_to_identify)],
            [f"Close ({R.EXCHANGE_CLOSE_DAYS} days, or the return due date)",
             r.close_by.isoformat(),
             "—" if r.days_to_close is None else str(r.days_to_close)],
        ])
        w()

    for f in r.findings:
        w(f"- {f}")
        w()

    w("## Before acting")
    w()
    w("- **Engage the qualified intermediary before the relinquished "
      "closing.** After closing there is nothing to fix; constructive receipt "
      "voids the exchange retroactively.")
    w("- **Identify in writing, unambiguously** — street address or legal "
      "description, signed and delivered inside 45 days. A conversation is "
      "not an identification.")
    w("- **Extend the return** if the sale falls late in the year, or the "
      "180 days silently shortens to the filing date.")
    w("- **Decide the ending now**: taxable sale, or step-up at death. An "
      "exchange chain only pays off if one of the two is actually planned.")
    cli.disclaimer(
        w, "lib/pf/realestate.py",
        "Tax rates come from your facts file, not from a table in this "
        "library. Reverse and improvement exchanges, §1031(f) related-party "
        "rules and state clawback are out of scope.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="1031 exchange modeling",
                             required=REQUIRED, build=build))
