#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Has the state actually let go — severance, statutory residence, and sourcing."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, expat as X, facts as F, presence as P  # noqa: E402

REQUIRED = ["state_exit.from_state"]


def build(data: dict, w: cli.Writer) -> None:
    spec = F._dig(data, "state_exit") or {}
    as_of = F.as_of(data)
    year = spec.get("count_year") or (as_of.year if as_of else None)

    days = None
    led = P.build_ledger(F._dig(data, "presence.days"))
    if year and led.stays:
        import datetime as dt
        days = P.count_present_days(
            led, start=dt.date(year, 1, 1), end=dt.date(year, 12, 31),
            state=spec.get("from_state"))

    x = X.domicile_exit(
        spec, days_in_state=days,
        new_domicile_established=spec.get("new_domicile_established"))

    w(f"Leaving **{x.from_state}** for "
      f"**{x.to_state or 'somewhere not recorded'}**"
      + (f", from {spec['move_date']}" if spec.get("move_date") else "")
      + f". Severance steps complete: **{x.score}**."
      + (f" Days in {x.from_state} during {year}: **{days}**"
         f" — counted on the basis that {P.PART_DAY_BASIS}." if days is not None
         else ""))
    w()

    # ── the cited table ─────────────────────────────────────────────────
    w("## What is actually known about these states")
    w()
    w.table(["State", "In the cited table", "Income tax", "Day-count bright line"],
            [[r.state or "—",
              "yes" if r.known else "**no — nothing asserted**",
              "—" if r.has_income_tax is None else
              ("yes" if r.has_income_tax else "none"),
              "—" if r.no_bright_line is None else
              ("**none — facts and circumstances**" if r.no_bright_line
               else "yes")]
             for r in (x.rules, x.destination_rules) if r.state != "??"])
    w()
    w(f"Only {', '.join(X.domicile_states_available())} have been checked, "
      "each with a source and a verification date. Every other state returns "
      "nothing, and this skill does not reason by analogy from the two it "
      "knows — state residency rules diverge more than they converge, and the "
      "ones that hurt are the ones that differ from the one you have read "
      "about.")
    w()
    for r in (x.rules, x.destination_rules):
        if r.known and r.notes:
            w(f"**{r.state}** — {r.source}")
            w()
            for n in r.notes:
                w(f"- {n}")
            w()

    # ── findings ────────────────────────────────────────────────────────
    w("## Findings")
    w()
    for f in x.findings:
        w(f"- {f}")
        w()

    # ── the checklist ───────────────────────────────────────────────────
    w("## Severance")
    w()
    w("Ordered by the weight these carry. Where you sleep, where your family "
      "is and where your business is beat where your mail goes — a household "
      "that changes the mailing address and keeps the house has done the easy "
      "half.")
    w()
    if x.completed:
        w("**Done:** " + ", ".join(f"`{k}`" for k in x.completed) + ".")
        w()
    if x.outstanding:
        w("**Outstanding — recorded as not done:**")
        w()
        for k, detail in x.outstanding:
            w(f"- 🚫 `{k}` — {detail}")
        w()
    if x.unrecorded:
        w("**Not recorded — nobody has checked:**")
        w()
        for k, detail in x.unrecorded:
            w(f"- · `{k}` — {detail}")
        w()
        w("Unrecorded is not done. Each of these is a question an examiner "
          "asks by name.")
        w()

    w("## Before relying on any of this")
    w()
    w("- **Keep contemporaneous evidence.** A day count reconstructed two "
      "years later, in response to a notice, is worth a fraction of one kept "
      "as you went. The same is true of every item above.")
    w("- **File a part-year or non-resident return** where one is due rather "
      "than simply stopping. A taxpayer who files nothing looks the same to a "
      "state as one who forgot, and in several states not filing leaves the "
      "assessment period open indefinitely.")
    w("- **Re-execute the estate documents.** It is the step households skip "
      "and the one that reads most clearly as a statement of where you "
      "consider yourself domiciled.")
    w()
    w("**Weakest input:** the severance flags. They are self-reported, and "
      "the whole test is a judgement about the picture they add up to rather "
      "than a count of ticks. A checklist at "
      f"{x.score} is not a defence; it is a description.")
    cli.disclaimer(w, "lib/pf/expat.py",
                   "State residency is decided on the full facts by that "
                   "state's revenue authority. Two states are in the table "
                   "here; nothing is asserted about any other.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="State domicile exit",
                             required=REQUIRED, build=build))
