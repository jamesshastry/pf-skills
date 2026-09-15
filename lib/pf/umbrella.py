"""Umbrella (excess liability): attachment gate, sizing, and the gaps.

Attachment thresholds are **imported**, not restated. They are the same
numbers `auto` and `property` test against, and a threshold duplicated across
modules is a threshold that will eventually disagree with itself — here that
would mean telling a household it qualifies to bind when it does not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import auto as _auto
from . import property as _property

# ── sizing ──────────────────────────────────────────────────────────────────

MIN_UMBRELLA = 1_000_000

#: Umbrella limits are sold in millions. Anything else is a rounding error.
GRANULARITY = 1_000_000

#: Typical annual cost of the first million, and of each million after it.
#: The gap between these two is the entire argument for buying more than the
#: minimum: the first million carries the underwriting, the rest is nearly
#: linear and much cheaper per dollar.
FIRST_MILLION_COST = (150, 300)
ADDITIONAL_MILLION_COST = (75, 150)

#: Above this, carriers typically re-underwrite and pricing stops being
#: linear. Not a cap — a point at which to expect a different conversation.
LINEAR_PRICING_CEILING = 5_000_000

#: Self-insured retention that applies where the umbrella covers a loss the
#: underlying policies do not (so there is no underlying limit to sit above).
TYPICAL_SIR = (250, 1_000)


@dataclass
class GateItem:
    policy: str
    coverage: str
    current: int
    required: int

    @property
    def ok(self) -> bool:
        return self.current >= self.required


@dataclass
class UmbrellaAssessment:
    exposure: float
    attachable: float
    income: float
    recommended: int
    in_force: int | None
    gate: list[GateItem] = field(default_factory=list)
    cost_estimate: tuple[float, float] = (0.0, 0.0)
    cost_per_million: tuple[float, float] = (0.0, 0.0)
    riders: list[str] = field(default_factory=list)
    exclusions_passed_through: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def failures(self) -> list[GateItem]:
        return [g for g in self.gate if not g.ok]

    @property
    def can_bind(self) -> bool:
        return not self.failures

    @property
    def shortfall(self) -> int:
        return max(0, self.recommended - (self.in_force or 0))


def size(attachable_assets: float, household_income: float) -> int:
    """Assets a judgment reaches, plus a garnishment proxy, rounded up.

    Deliberately not "net worth": retirement accounts are largely out of
    reach, and future earnings very much are not. A judgment does not stop at
    the balance sheet.
    """
    exposure = _auto.liability_exposure(attachable_assets, household_income)
    rounded = int(math.ceil(exposure / GRANULARITY)) * GRANULARITY
    return max(MIN_UMBRELLA, rounded)


def cost(limit: int) -> tuple[float, float]:
    millions = max(1, limit // GRANULARITY)
    extra = millions - 1
    return (
        FIRST_MILLION_COST[0] + extra * ADDITIONAL_MILLION_COST[0],
        FIRST_MILLION_COST[1] + extra * ADDITIONAL_MILLION_COST[1],
    )


def check_gate(auto_coverage: dict, property_coverage: dict) -> list[GateItem]:
    """Every underlying limit a carrier checks before it will attach."""
    bi = auto_coverage.get("bodily_injury") or {}
    pd = auto_coverage.get("property_damage") or {}
    att = _auto.UMBRELLA_ATTACHMENT
    return [
        GateItem("auto", "bodily injury per person",
                 bi.get("per_person") or 0, att["bi_per_person"]),
        GateItem("auto", "bodily injury per accident",
                 bi.get("per_accident") or 0, att["bi_per_accident"]),
        GateItem("auto", "property damage",
                 pd.get("per_accident") or 0, att["pd"]),
        GateItem("property", "personal liability",
                 property_coverage.get("personal_liability") or 0,
                 _property.UMBRELLA_ATTACHMENT_LIABILITY),
    ]


def assess(
    *,
    attachable_assets: float,
    household_income: float,
    auto_coverage: dict,
    property_coverage: dict,
    property_exclusions: list[str] | None,
    dependents: list[dict],
    balance_sheet: list[dict],
    in_force: int | None,
) -> UmbrellaAssessment:
    recommended = size(attachable_assets, household_income)
    a = UmbrellaAssessment(
        exposure=_auto.liability_exposure(attachable_assets, household_income),
        attachable=attachable_assets,
        income=household_income,
        recommended=recommended,
        in_force=in_force,
        gate=check_gate(auto_coverage, property_coverage),
        cost_estimate=cost(recommended),
    )
    lo, hi = a.cost_estimate
    millions = recommended / GRANULARITY
    a.cost_per_million = (lo / millions, hi / millions)

    # ── the gap people think the umbrella closes and it does not ────────
    um = (auto_coverage.get("um_uim_bodily_injury") or {}).get("per_person") or 0
    a.notes.append(
        "**An umbrella does not extend UM/UIM by default.** It covers "
        "liability *you* owe others. The coverage that pays your own family "
        "when an uninsured driver injures them stops at the auto policy's "
        f"UM/UIM limit — currently {_money(um)} per person — no matter how "
        "large the umbrella above it. **Excess UM/UIM is a separate election**, "
        "not offered by every carrier, and often only available where the "
        "umbrella carrier also writes the auto. Ask for it by name."
    )

    if recommended > LINEAR_PRICING_CEILING:
        a.notes.append(
            f"Above {_money(LINEAR_PRICING_CEILING)} carriers re-underwrite "
            "and pricing stops being roughly linear. Expect a different "
            "conversation and possibly a different market."
        )

    a.notes.append(
        f"Where the umbrella covers a loss the underlying policies do not, a "
        f"self-insured retention applies — typically "
        f"{_money(TYPICAL_SIR[0])}–{_money(TYPICAL_SIR[1])}. Ask what it is; "
        "it is the deductible nobody mentions."
    )

    # ── exclusions pass through from the underlying policy ──────────────
    for exc in property_exclusions or []:
        a.exclusions_passed_through.append(exc)

    # ── things that need to be disclosed or ridered ─────────────────────
    drivers = [d for d in dependents
               if (d.get("age") or 0) >= _auto.MEDPAY_TRIGGER_AGE]
    if drivers:
        ages = ", ".join(str(d.get("age")) for d in sorted(
            drivers, key=lambda d: d.get("age") or 0))
        a.riders.append(
            f"Dependents of driving age ({ages}) must be listed as household "
            "residents. An undisclosed resident driver is the most common "
            "reason an excess claim is denied — and a young driver is exactly "
            "when the umbrella earns its premium."
        )
    for row in balance_sheet or []:
        name = (row.get("name") or "").lower()
        if any(k in name for k in ("rental", "rental_property", "landlord")):
            a.riders.append(
                f"`{row.get('name')}` looks like rental property. Landlord "
                "liability is not covered by a personal umbrella unless the "
                "property is scheduled on it."
            )
        if "business" in name:
            a.riders.append(
                f"`{row.get('name')}` looks like a business interest. Personal "
                "umbrellas exclude business activities — that exposure needs "
                "commercial liability, not this."
            )

    a.riders.append(
        "Board service for a nonprofit or an HOA is excluded by most personal "
        "umbrellas and needs either a rider or the organisation's own D&O "
        "cover. Confirm before assuming you are covered."
    )
    a.riders.append(
        "Rideshare and delivery driving voids personal auto cover and the "
        "umbrella above it. Disclose it if anyone in the household does it."
    )
    return a


def where_to_buy(gate_fails: bool) -> list[str]:
    out = []
    if gate_fails:
        out.append(
            "**Do not call for a quote yet.** No carrier binds excess "
            "coverage over underlying limits that do not qualify. Raise the "
            "underlying limits in the same call, then quote."
        )
    out.extend([
        "**Your existing auto carrier first.** Bundling is nearly always "
        "cheapest, and it keeps the attachment question trivial.",
        "**A standalone excess carrier** writes over *other* carriers' auto "
        "and renters. Worth it when the home or renters policy is somewhere "
        "cheap you would rather keep. Usually via an independent agent.",
        "**An independent agent** quotes several carriers at once, which is "
        "the whole value on a commoditised product.",
        "**Not through a life or disability adviser.** They do not underwrite "
        "property and casualty, so it becomes a referral to a partner — a "
        "middleman on a commodity, and it opens a broader planning "
        "conversation you did not ask for.",
    ])
    return out


def _money(x) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
