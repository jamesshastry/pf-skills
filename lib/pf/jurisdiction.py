"""State-specific auto insurance rules.

Deliberately small. A state is in here only if the rule has been checked
against the state's insurance code or department guidance; everything else
returns `UNKNOWN` and the skill says so out loud rather than applying the
rule it happens to know.

Adding a state means adding the rule *and* a citation comment. An unsourced
entry is worse than an absent one, because absence is visible.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StateRules:
    state: str
    known: bool
    #: Statutory minimum liability, as (BI/person, BI/accident, PD).
    min_liability: tuple[int, int, int] | None = None
    #: True where UM/UIM bodily injury may not exceed the policy's BI limits.
    um_uim_capped_at_bi: bool | None = None
    #: Is Uninsured Motorist *Property Damage* sold in this state?
    umpd_available: bool | None = None
    #: Statutory cap on UMPD, if any.
    umpd_max: int | None = None
    #: True where UMPD may not be carried alongside collision on the same car.
    umpd_excluded_by_collision: bool | None = None
    umpd_deductible: int | None = None
    notes: tuple[str, ...] = ()
    #: Provenance. Surfaced by `provenance.py` so a stale rule is visible
    #: rather than merely wrong.
    source: str = ""
    verified_on: str = ""


UNKNOWN = StateRules(state="??", known=False)

# ── California ──────────────────────────────────────────────────────────────
# Ins. Code §11580.2: UM/UIM offered up to but not exceeding BI limits.
# UMPD capped at $3,500 and unavailable where collision is carried on the
# vehicle; $250 deductible. Minimums raised to 30/60/15 by SB 1107 (eff.
# 2025-01-01).
CA = StateRules(
    state="CA",
    known=True,
    min_liability=(30_000, 60_000, 15_000),
    um_uim_capped_at_bi=True,
    umpd_available=True,
    umpd_max=3_500,
    umpd_excluded_by_collision=True,
    umpd_deductible=250,
    notes=(
        "UMPD is capped at $3,500 — it is a partial backstop for a dropped "
        "collision, not a replacement.",
        "UMPD requires the at-fault uninsured vehicle to be identified; a "
        "hit-and-run with no contact generally does not qualify.",
    ),
    source="CA Ins. Code §11580.2; SB 1107 minimums eff. 2025-01-01",
    verified_on="unverified — check against the CA Dept. of Insurance",
)

# ── Texas ───────────────────────────────────────────────────────────────────
# Ins. Code §1952.101 et seq.: UM/UIM offered up to BI limits; UMPD written up
# to the policy's PD limit with a $250 deductible. Minimums 30/60/25.
TX = StateRules(
    state="TX",
    known=True,
    min_liability=(30_000, 60_000, 25_000),
    um_uim_capped_at_bi=True,
    umpd_available=True,
    umpd_max=None,
    umpd_excluded_by_collision=False,
    umpd_deductible=250,
    notes=(
        "UMPD carries a $250 deductible and pays only when the at-fault "
        "driver is identified.",
    ),
    source="TX Ins. Code §1952.101 et seq.",
    verified_on="unverified — check against the TX Dept. of Insurance",
)

_TABLE: dict[str, StateRules] = {"CA": CA, "TX": TX}


def states_available() -> list[str]:
    return sorted(_TABLE)


def rules_for(state: str | None) -> StateRules:
    if not state:
        return UNKNOWN
    return _TABLE.get(state.strip().upper(), StateRules(state=state.upper(), known=False))
