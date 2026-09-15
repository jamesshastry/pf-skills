"""Renters / homeowners arithmetic: contents, loss of use, liability, limits.

Same rule as `auto`: every threshold is a named constant with a stated reason,
and nothing here is restated in prose.

The hard part of this line is that the household's **contents replacement
cost is not a fact anyone has**. Auto has a value per vehicle; renters has a
number nobody has ever counted. Everything downstream of that — the personal
property limit, and Loss of Use where a carrier sets it as a percentage —
inherits the uncertainty. So contents is produced as an explicitly labelled
benchmark band, and the skill tells the household to replace it with an
inventory. It is the weakest input in the whole repo; treat it accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── contents ────────────────────────────────────────────────────────────────

#: Replacement cost of household contents, per person, for a furnished
#: household in a developed-economy metro. A benchmark, not a measurement.
#: The low end assumes modest furnishing; the high end assumes several
#: personal computers, phones, tablets, and televisions.
CONTENTS_PER_PERSON = (18_000, 31_000)

#: Standard HO-4 / HO-3 special sub-limits. These apply *inside* the personal
#: property limit — raising the limit does not raise them. Only scheduling
#: does.
SPECIAL_SUBLIMITS = {
    "jewelry, watches, furs (theft)": 1_500,
    "firearms (theft)": 2_500,
    "silverware, goldware (theft)": 2_500,
    "business property on premises": 2_500,
    "cash, bullion, coins": 200,
    "securities, manuscripts, passports": 1_500,
}

# ── loss of use ─────────────────────────────────────────────────────────────

#: Short-term / month-to-month housing costs this multiple of a standing
#: lease rate. Furnished, no lease, sourced under time pressure.
TEMP_HOUSING_MULTIPLE = (1.8, 2.4)

#: Additional food and laundry per person per month while displaced — no
#: kitchen, or a worse one.
DISPLACED_UPLIFT_PER_PERSON = 150

#: Displacement after a serious fire. The low end is a clean rebuild of one
#: unit; the high end is permitting, contractor scheduling, and a total loss.
DISPLACEMENT_MONTHS = (3, 12)

#: Months of additional living expense the Loss of Use limit should carry.
#: Mid-range of DISPLACEMENT_MONTHS: covering the 12-month tail is expensive,
#: covering only 3 months is a coin flip.
LOSS_OF_USE_TARGET_MONTHS = 6

# ── liability ───────────────────────────────────────────────────────────────

#: Umbrella carriers require this much underlying personal liability on the
#: renters/homeowners policy. Note it differs from the auto attachment point.
UMBRELLA_ATTACHMENT_LIABILITY = 300_000

#: Recommended personal liability once an umbrella is contemplated. The step
#: from $300K to $500K is usually $20–40/yr and removes the attachment
#: question entirely.
LIABILITY_TARGET = 500_000

#: Medical Payments to Others. Unlike auto MedPay this is worth carrying: it
#: settles a guest's minor injury without a liability claim, and it is cheap.
MEDPAY_TARGET = 5_000

#: A deductible above this share of liquid assets is not a deductible, it is
#: an uninsured loss.
DEDUCTIBLE_MAX_PCT_LIQUID = 0.02

#: Fields schema v1 does not carry, needed for a real homeowners review.
HOMEOWNERS_SCHEMA_GAPS = (
    "property.dwelling.coverage_a — dwelling replacement cost (NOT market "
    "value, and NOT the purchase price; it is the cost to rebuild)",
    "property.dwelling.other_structures — fences, sheds, detached garage",
    "property.dwelling.ordinance_or_law — pays to rebuild to current code; "
    "the usual 10% default is thin on an older house",
    "property.dwelling.extended_replacement_cost — the percentage cushion "
    "over Coverage A",
    "property.perils.excluded — flood and earthquake are excluded by "
    "default everywhere and are separate policies",
)


@dataclass
class Finding:
    key: str
    severity: str  # blocker | gap | note | ok
    current: str
    target: str
    detail: str


@dataclass
class PropertyAssessment:
    form: str
    people: int
    contents_benchmark: tuple[float, float]
    ale_monthly: tuple[float, float]
    loss_of_use_target: tuple[float, float]
    findings: list[Finding] = field(default_factory=list)
    schema_gaps: list[str] = field(default_factory=list)

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "blocker"]


def contents_benchmark(people: int) -> tuple[float, float]:
    return (CONTENTS_PER_PERSON[0] * people, CONTENTS_PER_PERSON[1] * people)


def ale_monthly(monthly_rent: float, people: int) -> tuple[float, float]:
    """Additional living expense per month while displaced.

    'Additional' is the whole point: the policy pays the *increase* over what
    you already spend on housing, not the temporary rent itself. Households
    consistently over-read this coverage by budgeting the gross figure and
    under-buy it by assuming a displacement of weeks.
    """
    uplift = DISPLACED_UPLIFT_PER_PERSON * people
    return (
        monthly_rent * (TEMP_HOUSING_MULTIPLE[0] - 1) + uplift,
        monthly_rent * (TEMP_HOUSING_MULTIPLE[1] - 1) + uplift,
    )


def assess(
    prop: dict,
    *,
    people: int,
    liquid_assets: float,
    attachable_assets: float,
    umbrella_in_force,
) -> PropertyAssessment:
    form = prop.get("form") or "renters"
    cov = prop.get("coverage") or {}

    contents = contents_benchmark(people)
    monthly_rent = float(prop.get("monthly_rent") or 0)
    ale = ale_monthly(monthly_rent, people) if monthly_rent else (0.0, 0.0)
    lou_target = (
        ale[0] * LOSS_OF_USE_TARGET_MONTHS,
        ale[1] * LOSS_OF_USE_TARGET_MONTHS,
    )

    a = PropertyAssessment(
        form=form,
        people=people,
        contents_benchmark=contents,
        ale_monthly=ale,
        loss_of_use_target=lou_target,
    )

    # ── personal liability — the item that gates the umbrella ───────────
    pl = cov.get("personal_liability") or 0
    if pl < UMBRELLA_ATTACHMENT_LIABILITY:
        a.findings.append(
            Finding(
                "personal_liability",
                "blocker",
                _money(pl),
                _money(LIABILITY_TARGET),
                f"Below the {_money(UMBRELLA_ATTACHMENT_LIABILITY)} umbrella "
                f"carriers require underneath. **No umbrella can be bound "
                f"until this is raised** — so it blocks the single largest "
                f"coverage gain available, against an attachable "
                f"{_money(attachable_assets)}. Usually $20–40/yr.",
            )
        )
    elif pl < LIABILITY_TARGET:
        a.findings.append(
            Finding(
                "personal_liability",
                "gap",
                _money(pl),
                _money(LIABILITY_TARGET),
                "Meets the umbrella attachment point. The step to "
                f"{_money(LIABILITY_TARGET)} is usually $20–40/yr and removes "
                "the question permanently.",
            )
        )
    else:
        a.findings.append(
            Finding("personal_liability", "ok", _money(pl), _money(LIABILITY_TARGET),
                    "Qualifies for umbrella attachment.")
        )

    # ── personal property ───────────────────────────────────────────────
    pp = cov.get("personal_property") or 0
    if pp < contents[0]:
        pct = pp / contents[0] if contents[0] else 0
        a.findings.append(
            Finding(
                "personal_property",
                "gap",
                _money(pp),
                f"{_money(contents[0])}–{_money(contents[1])}",
                f"Covers roughly {pct:.0%} of a benchmark replacement cost "
                f"for {people} people. **This benchmark is the weakest input "
                "in the review** — replace it with a room-by-room inventory "
                "and photographs, which you need for a claim anyway.",
            )
        )
    else:
        a.findings.append(
            Finding("personal_property", "ok", _money(pp),
                    f"{_money(contents[0])}–{_money(contents[1])}",
                    "At or above the benchmark band. Confirm with an inventory.")
        )

    # ── settlement basis ────────────────────────────────────────────────
    basis = prop.get("settlement_basis")
    if basis == "actual_cash_value":
        a.findings.append(
            Finding(
                "settlement_basis",
                "blocker",
                "actual_cash_value",
                "replacement_cost",
                "ACV settles a ten-year-old sofa at ten-year-old-sofa prices, "
                "which will not furnish a room. Replacement cost typically "
                "adds 10–15% to the premium and is the single highest-value "
                "change on this policy after liability.",
            )
        )
    elif basis == "replacement_cost":
        a.findings.append(
            Finding("settlement_basis", "ok", "replacement_cost",
                    "replacement_cost", "Correct form.")
        )
    else:
        a.findings.append(
            Finding("settlement_basis", "gap", str(basis), "replacement_cost",
                    "Not stated. Check the declarations page — this changes "
                    "what a claim pays more than the limit does.")
        )

    # ── loss of use ─────────────────────────────────────────────────────
    lou = cov.get("loss_of_use") or 0
    if monthly_rent and lou < lou_target[0]:
        months_low = lou / ale[1] if ale[1] else 0
        months_high = lou / ale[0] if ale[0] else 0
        a.findings.append(
            Finding(
                "loss_of_use",
                "gap",
                _money(lou),
                f"{_money(lou_target[0])}–{_money(lou_target[1])}",
                f"Additional living expense runs {_money(ale[0])}–"
                f"{_money(ale[1])}/month — the *difference* between temporary "
                f"housing and the {_money(monthly_rent)} rent already being "
                f"paid, plus food and laundry. The current limit funds "
                f"**{months_low:.1f}–{months_high:.1f} months**. Displacement "
                f"after a serious fire runs {DISPLACEMENT_MONTHS[0]}–"
                f"{DISPLACEMENT_MONTHS[1]} months.",
            )
        )
    elif monthly_rent:
        a.findings.append(
            Finding("loss_of_use", "ok", _money(lou),
                    f"{_money(lou_target[0])}–{_money(lou_target[1])}",
                    f"Funds at least {LOSS_OF_USE_TARGET_MONTHS} months.")
        )

    # ── medical payments to others ──────────────────────────────────────
    mp = cov.get("medical_payments_to_others") or 0
    if mp < MEDPAY_TARGET:
        a.findings.append(
            Finding(
                "medical_payments_to_others", "note", _money(mp),
                _money(MEDPAY_TARGET),
                "Unlike auto MedPay this is worth carrying: it settles a "
                "guest's minor injury without opening a liability claim "
                "against you. Usually $5–10/yr.",
            )
        )

    # ── deductible ──────────────────────────────────────────────────────
    ded = cov.get("deductible")
    if ded is not None and liquid_assets:
        share = ded / liquid_assets
        if share > DEDUCTIBLE_MAX_PCT_LIQUID:
            a.findings.append(
                Finding("deductible", "gap", _money(ded),
                        _money(liquid_assets * DEDUCTIBLE_MAX_PCT_LIQUID),
                        f"{share:.1%} of liquid assets. A deductible you "
                        "cannot comfortably pay is an uninsured loss.")
            )
        else:
            a.findings.append(
                Finding("deductible", "ok", _money(ded), "—",
                        f"{share:.2%} of liquid assets. Comfortably payable — "
                        "consider raising it to cut premium, since the "
                        "small-claim risk is one you can absorb.")
            )

    # ── scheduled items vs. sub-limits ──────────────────────────────────
    scheduled = prop.get("scheduled_items")
    if not scheduled:
        worst = min(SPECIAL_SUBLIMITS.items(), key=lambda kv: kv[1])
        a.findings.append(
            Finding(
                "scheduled_items", "note", "none scheduled", "schedule or confirm none needed",
                "Special sub-limits apply **inside** the personal property "
                "limit — raising the limit does not raise them, only "
                "scheduling does. Jewellery and watches cap at "
                f"{_money(SPECIAL_SUBLIMITS['jewelry, watches, furs (theft)'])} "
                f"against theft; {worst[0]} at {_money(worst[1])}. If nothing "
                "in the household exceeds these, record that as a decision "
                "rather than leaving it unexamined.",
            )
        )

    # ── endorsed exclusions ─────────────────────────────────────────────
    for exc in prop.get("exclusions") or []:
        a.findings.append(
            Finding(
                f"exclusion:{exc}", "note", exc, "—",
                "An umbrella generally will not cover what the underlying "
                "policy excludes by endorsement. If this exclusion is moot "
                "(the dog, pool, or trampoline no longer exists) ask to have "
                "it removed — a stale endorsement narrows the umbrella above "
                "it for no benefit.",
            )
        )

    if form in ("homeowners", "condo"):
        a.schema_gaps.extend(HOMEOWNERS_SCHEMA_GAPS)

    return a


def sequencing(assessment: PropertyAssessment, umbrella_in_force) -> list[str]:
    """Order of operations. Renters liability is usually the binding item."""
    out: list[str] = []
    if assessment.blockers:
        out.append(
            "**Fix the blockers before quoting an umbrella.** No carrier "
            "binds excess coverage over underlying limits that do not "
            "qualify, so calling for a quote first wastes the call."
        )
    if umbrella_in_force:
        out.append(
            "An umbrella is already in force. Confirm with that carrier that "
            "the underlying limits below still satisfy their attachment "
            "requirement — falling under it can leave the excess layer "
            "unresponsive exactly when it is needed."
        )
    return out


def _money(x) -> str:
    if x is None:
        return "none"
    if isinstance(x, str):
        return x
    return f"${x:,.0f}"
