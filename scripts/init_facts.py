#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Write a starter `inputs/facts.yml` — a skeleton of nulls, not a copy.

    uv run scripts/init_facts.py

## Why not just copy the example

`cp inputs/facts.example.yml inputs/facts.yml` is one command and it is the
wrong first move. The example is a complete fictional household, so every field
you do not get to still holds an invented figure — and an invented figure that
survives into a report is exactly the defect this repository is organised
against. A skill cannot tell the difference between a number you entered and
one the Riveras came with.

A skeleton of nulls fails loudly instead: the skill stops and names the field.

## Why this file is short

It covers the fields that unblock the most skills, and stops. Roughly thirty of
the sixty-four facts-file skills are waiting on `household.members` alone.

Add sections as you need them — `SCHEMA.md` has all of them, and
`document-intake` tells you which one to add next and what it will unlock.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "inputs" / "facts.yml"

TEMPLATE = """\
# Your facts. Gitignored, never committed, never transmitted.
#
# Every field below is `null` on purpose. A skill that needs a field you have
# not filled in stops and tells you which one -- that is the designed
# behaviour. A guessed number is worse than a gap, because a gap is visible.
#
# Add sections as you need them. SCHEMA.md documents all of them, and
# `uv run skills/document-intake/run.py` says which to add next.

meta:
  schema_version: 1
  as_of: {today}
  currency: USD
  jurisdiction:
    country: US
    state: null          # two-letter code. REQUIRED, no default -- liability
                         # minimums, community property and homestead rules
                         # all turn on it.

household:
  # Unblocks roughly 30 of the 64 facts-file skills on its own. Start here.
  #
  # role:   primary | spouse | dependent | other
  # income_annual: gross, before tax. Omit for dependents.
  members:
    - id: a1
      role: primary
      age: null
      birth_year: null
      income_annual: null
      # Three separate taxes turn on three different answers here: residence
      # decides worldwide income, domicile decides estate, and a spouse's
      # citizenship decides the marital deduction. See lib/pf/status.py.
      citizenship: null      # e.g. US, IN, GB
      us_status: null        # citizen | permanent_resident | nonimmigrant_visa

  # Unblocks ~17 skills.
  #
  # tier is the most load-bearing field in the schema:
  #   liquid          spendable within days, no penalty
  #   age_restricted  retirement accounts; penalty or age gate
  #   illiquid        property, private investments, lockups
  #
  # "Can this household absorb an $8,000 loss?" is answered from `liquid`
  # alone, never from net worth.
  balance_sheet:
    - name: cash
      label: Cash
      value: null
      tier: liquid

  # Twelve months of actual outflow, minus savings. Not a monthly guess x12 --
  # that understates by the amount of everything annual.
  annual_spending: null

# ── Add below as needed. See SCHEMA.md. ────────────────────────────────────
#
#   auto:            auto-insurance-review
#   property:        renters-homeowners-review
#   umbrella:        umbrella-liability
#   insurance:       life-insurance-review, disability-insurance-review
#   debts:           debt-payoff-priority
#   equity_comp:     equity-comp-review, employer-concentration-risk
#   retirement:      retirement-readiness, withdrawal-sequencing
#   foreign_accounts: foreign-reporting-audit
#                    -- record `foreign_accounts: []` if you have none, so the
#                    answer is checked rather than absent. An empty list is an
#                    answer; a missing key is not.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing inputs/facts.yml")
    ap.add_argument("--path", type=Path, default=TARGET)
    a = ap.parse_args()

    if a.path.exists() and not a.force:
        print(f"{a.path.relative_to(ROOT)} already exists. Refusing to "
              f"overwrite it.\n\nThat file is not in git, so this would be "
              f"unrecoverable. Pass --force if you are sure.", file=sys.stderr)
        return 1

    a.path.parent.mkdir(parents=True, exist_ok=True)
    a.path.write_text(TEMPLATE.format(today=dt.date.today().isoformat()))
    rel = a.path.relative_to(ROOT) if a.path.is_relative_to(ROOT) else a.path
    print(f"Wrote {rel}\n\nNext:\n"
          f"  1. Fill in household.members and meta.jurisdiction.state\n"
          f"  2. uv run skills/document-intake/run.py\n"
          f"  3. Work the list it gives you")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
