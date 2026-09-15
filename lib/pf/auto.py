"""Auto insurance arithmetic: physical-damage drop test and liability sizing.

Every threshold in this file is a named constant with a stated reason. If you
disagree with one, change the constant — do not argue with the output.

Nothing here decides anything on its own; it returns structured assessments
that the skill renders. Keeping the numbers here and the prose in SKILL.md is
what stops a restated figure from drifting away from its source.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The emergency-buffer floor is defined in `cash`, not here. It has two
#: consumers — this module's drop test and `emergency-fund-sizing` — and two
#: copies of a shared threshold drift.
from .cash import MIN_BUFFER_MONTHS  # noqa: F401

# ── thresholds ──────────────────────────────────────────────────────────────

#: Premium-to-value ratio above which physical-damage coverage is priced badly
#: enough to be a drop candidate. The common industry rule of thumb.
RATIO_DROP_THRESHOLD = 0.10

#: A loss under this share of liquid assets is one the household can write a
#: cheque for without changing any plan. Self-insure it.
ABSORB_TRIVIAL = 0.05

#: A loss over this share of liquid assets forces liquidation or borrowing.
#: Transfer it regardless of how well the ratio test scores.
ABSORB_SEVERE = 0.25

#: Typical insurance load (premium ÷ expected payout) on a competitively
#: priced line. Used only to characterise how far off a given premium is.
TYPICAL_LOAD_RANGE = (1.4, 1.7)

# ── claim frequency / severity ──────────────────────────────────────────────
# Industry averages (ISO/III fast-track, private passenger auto, mid-2020s).
# These are population averages, not this driver. Expected-recovery output is
# therefore reported with EXPECTED_RECOVERY_BAND applied and labelled an
# estimate. It is a sanity check on the premium, never the decision.

COLLISION_CLAIM_FREQUENCY = 0.056  # claims per insured vehicle-year
COLLISION_CLAIM_SEVERITY = 5_700.0  # gross, before deductible
COMPREHENSIVE_CLAIM_FREQUENCY = 0.029
COMPREHENSIVE_CLAIM_SEVERITY = 2_400.0
EXPECTED_RECOVERY_BAND = 0.40  # ±40% around the point estimate

# ── valuation basis ─────────────────────────────────────────────────────────
# How far each basis sits below Actual Cash Value, as (min, max) discount.
# A carrier settles a total loss at ACV, so every ratio must be computed
# against ACV — not against whatever number the household happened to have.

BASIS_DISCOUNT_TO_ACV: dict[str, tuple[float, float]] = {
    "acv": (0.00, 0.00),
    "instant_offer": (0.15, 0.25),  # Carvana/CarMax buy-now, per SCHEMA.md
    "private_party": (0.00, 0.10),
    # An unqualified estimate can sit either side of ACV, so this band is
    # two-sided. The others are one-sided because the basis is known to run
    # below settlement value.
    "estimate": (-0.15, 0.20),
}

LIABILITY_BRACKETS = (100_000, 250_000, 300_000, 500_000)

#: Auto BI is not the instrument for the top of a large exposure. Past roughly
#: $300K/$500K, carriers often stop writing higher and an umbrella buys the
#: next million for a fraction of the marginal auto premium. Target up to the
#: ceiling, then hand the remainder to the umbrella.
AUTO_BI_CEILING = (300_000, 500_000)

#: Umbrella carriers will not attach below these underlying auto limits.
UMBRELLA_ATTACHMENT = {"bi_per_person": 250_000, "bi_per_accident": 500_000, "pd": 100_000}

#: Years of household gross income used as a proxy for the wage-garnishment
#: portion of a judgment. A judgment reaches assets *and* future earnings.
GARNISHMENT_YEARS = 2


# ── value bands ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Band:
    low: float
    high: float

    @property
    def is_point(self) -> bool:
        return abs(self.high - self.low) < 1e-9

    @property
    def mid(self) -> float:
        return (self.low + self.high) / 2.0

    def straddles(self, threshold: float) -> bool:
        return self.low < threshold < self.high


def acv_band(value: float, basis: str) -> Band:
    """Convert a stated value on some basis into a band of plausible ACV."""
    try:
        dmin, dmax = BASIS_DISCOUNT_TO_ACV[basis]
    except KeyError:
        raise ValueError(
            f"unknown value_basis {basis!r}; expected one of "
            f"{sorted(BASIS_DISCOUNT_TO_ACV)}"
        ) from None
    return Band(low=value / (1 - dmin), high=value / (1 - dmax))


def ratio_band(annual_premium: float, value: float, basis: str) -> Band:
    """Premium as a share of ACV. A higher ACV gives a lower ratio."""
    acv = acv_band(value, basis)
    return Band(low=annual_premium / acv.high, high=annual_premium / acv.low)


def expected_annual_recovery(
    acv: float,
    *,
    collision: bool = True,
    comprehensive: bool = True,
    deductible_collision: float = 0.0,
    deductible_comprehensive: float = 0.0,
) -> Band:
    """Expected payout per year, capped by the car's own value.

    A claim cannot pay more than ACV less the deductible, which is exactly why
    coverage on a cheap car is poor value: the premium scales with claim
    frequency while the payout is capped by the asset.
    """
    total = 0.0
    if collision:
        payout = max(0.0, min(COLLISION_CLAIM_SEVERITY, acv) - deductible_collision)
        total += payout * COLLISION_CLAIM_FREQUENCY
    if comprehensive:
        payout = max(
            0.0, min(COMPREHENSIVE_CLAIM_SEVERITY, acv) - deductible_comprehensive
        )
        total += payout * COMPREHENSIVE_CLAIM_FREQUENCY
    return Band(low=total * (1 - EXPECTED_RECOVERY_BAND), high=total * (1 + EXPECTED_RECOVERY_BAND))


# ── per-vehicle assessment ──────────────────────────────────────────────────


@dataclass
class VehicleAssessment:
    label: str
    decision: str  # keep | drop_collision | drop_both | blocked | insufficient_data
    acv: Band
    basis: str
    basis_is_certain: bool
    premium_pd_annual: float
    premium_collision_annual: float | None
    premium_comprehensive_annual: float | None
    ratio: Band
    ratio_verdict: str  # drop_candidate | keep | inconclusive
    uninsured_loss: Band
    loss_pct_liquid: Band
    absorb_verdict: str  # trivial | material | severe
    expected_recovery: Band | None
    load: Band | None
    reasons: list[str] = field(default_factory=list)
    comprehensive_note: str | None = None


def assess_vehicle(
    vehicle: dict,
    *,
    liquid_assets: float,
    buffer_months: float | None,
) -> VehicleAssessment:
    label = vehicle.get("label") or vehicle.get("id") or "vehicle"
    value = vehicle.get("value")
    basis = vehicle.get("value_basis")

    coll = vehicle.get("collision_premium_annual")
    comp = vehicle.get("comprehensive_premium_annual")
    combined = vehicle.get("comp_collision_premium_annual")

    ded_coll = float(vehicle.get("deductible_collision") or 0)
    ded_comp = float(vehicle.get("deductible_comprehensive") or 0)

    premium = None
    if coll is not None or comp is not None:
        premium = float(coll or 0) + float(comp or 0)
    elif combined is not None:
        premium = float(combined)

    if value is None or basis is None or premium is None:
        return VehicleAssessment(
            label=label,
            decision="insufficient_data",
            acv=Band(0, 0),
            basis=basis or "unknown",
            basis_is_certain=False,
            premium_pd_annual=premium or 0.0,
            premium_collision_annual=coll,
            premium_comprehensive_annual=comp,
            ratio=Band(0, 0),
            ratio_verdict="inconclusive",
            uninsured_loss=Band(0, 0),
            loss_pct_liquid=Band(0, 0),
            absorb_verdict="unknown",
            expected_recovery=None,
            load=None,
            reasons=["Missing value, value_basis, or a premium figure."],
        )

    value = float(value)
    acv = acv_band(value, basis)
    ratio = ratio_band(premium, value, basis)

    # What you would actually be out if you dropped and then totalled the car:
    # what the carrier would have paid, i.e. ACV less the deductible.
    loss = Band(
        low=max(0.0, acv.low - max(ded_coll, ded_comp)),
        high=max(0.0, acv.high - max(ded_coll, ded_comp)),
    )
    pct = Band(
        low=loss.low / liquid_assets if liquid_assets else float("inf"),
        high=loss.high / liquid_assets if liquid_assets else float("inf"),
    )

    exp = expected_annual_recovery(
        acv.mid,
        collision=coll is not None or combined is not None,
        comprehensive=comp is not None or combined is not None,
        deductible_collision=ded_coll,
        deductible_comprehensive=ded_comp,
    )
    load = Band(low=premium / exp.high, high=premium / exp.low) if exp.high > 0 else None

    # ── ratio screen ────────────────────────────────────────────────────
    if ratio.straddles(RATIO_DROP_THRESHOLD):
        ratio_verdict = "inconclusive"
    elif ratio.low >= RATIO_DROP_THRESHOLD:
        ratio_verdict = "drop_candidate"
    else:
        ratio_verdict = "keep"

    # ── absorbability, judged on the worse (larger) end of the loss band ──
    if pct.high <= ABSORB_TRIVIAL:
        absorb = "trivial"
    elif pct.high >= ABSORB_SEVERE:
        absorb = "severe"
    else:
        absorb = "material"

    a = VehicleAssessment(
        label=label,
        decision="keep",
        acv=acv,
        basis=basis,
        basis_is_certain=(basis == "acv"),
        premium_pd_annual=premium,
        premium_collision_annual=coll,
        premium_comprehensive_annual=comp,
        ratio=ratio,
        ratio_verdict=ratio_verdict,
        uninsured_loss=loss,
        loss_pct_liquid=pct,
        absorb_verdict=absorb,
        expected_recovery=exp,
        load=load,
    )

    # ── decision ────────────────────────────────────────────────────────
    if vehicle.get("lienholder"):
        a.decision = "blocked"
        a.reasons.append(
            "A lienholder requires physical damage coverage. Not a financial "
            "decision until the loan is paid off."
        )
        return a

    if buffer_months is not None and buffer_months < MIN_BUFFER_MONTHS:
        a.decision = "keep"
        a.reasons.append(
            f"Liquid assets cover only {buffer_months:.1f} months of spending "
            f"(floor is {MIN_BUFFER_MONTHS:.0f}). Self-insuring requires a "
            "buffer to self-insure from. Rebuild the buffer first."
        )
        return a

    if absorb == "severe":
        a.decision = "keep"
        a.reasons.append(
            f"Losing this car uninsured costs up to {pct.high:.1%} of liquid "
            f"assets — at or above the {ABSORB_SEVERE:.0%} line where a loss "
            "forces liquidation or borrowing. Keep it regardless of price."
        )
        return a

    if absorb == "trivial":
        a.decision = "drop_both"
        a.reasons.append(
            f"Losing this car uninsured costs at most {pct.high:.1%} of liquid "
            f"assets — under the {ABSORB_TRIVIAL:.0%} line. This is a "
            "prepayment, not a risk transfer."
        )
        if ratio_verdict == "keep":
            a.reasons.append(
                f"Note the reversal: at {ratio.high:.1%} of ACV this coverage "
                "is priced *well*. It is still a transfer of a loss you do not "
                "need to transfer. Keeping it is a preference, not risk "
                "management — decide it on that basis."
            )
        a.comprehensive_note = (
            "Comprehensive can go too at this size: the loss it prevents is "
            "one you can absorb."
        )
        return a

    # material: a real but survivable loss. Price decides.
    if ratio_verdict == "keep":
        a.decision = "keep"
        a.reasons.append(
            f"Premium is {ratio.high:.1%} of ACV, under the "
            f"{RATIO_DROP_THRESHOLD:.0%} threshold, and the loss "
            f"({pct.high:.1%} of liquid) is material. Fairly priced protection "
            "against a loss worth transferring."
        )
        return a

    a.decision = "drop_collision"
    if ratio_verdict == "inconclusive":
        a.reasons.append(
            f"Premium is {ratio.low:.1%}–{ratio.high:.1%} of ACV, straddling "
            f"the {RATIO_DROP_THRESHOLD:.0%} threshold — the ratio test is "
            "inconclusive because the value basis is uncertain. Absorbability "
            "decides."
        )
    else:
        a.reasons.append(
            f"Premium is {ratio.low:.1%}–{ratio.high:.1%} of ACV, above the "
            f"{RATIO_DROP_THRESHOLD:.0%} threshold."
        )
    a.reasons.append(
        f"The loss is survivable at {pct.low:.1%}–{pct.high:.1%} of liquid "
        "assets. Drop the expensive half."
    )
    note = (
        "Comprehensive is a separate decision and usually the keeper: it "
        "covers theft, fire, hail, and glass — none of them your fault, none "
        "avoidable by driving well."
    )
    if comp is None:
        note += (
            " **The carrier quoted the pair combined, so this question is "
            "unresolved.** Ask for the split before cancelling anything; "
            "comprehensive typically runs 25–35% of the pair."
        )
    else:
        comp_ratio = Band(comp / acv.high, comp / acv.low)
        note += (
            f" Standalone it is {_money(comp)}/yr — {comp_ratio.low:.1%}–"
            f"{comp_ratio.high:.1%} of ACV, "
            + (
                "still under the threshold, so keep it."
                if comp_ratio.high < RATIO_DROP_THRESHOLD
                else "itself above the threshold; drop it too."
            )
        )
    a.comprehensive_note = note
    return a


# ── liability ───────────────────────────────────────────────────────────────


@dataclass
class LiabilityAssessment:
    exposure: float
    target_bi: tuple[int, int]
    target_pd: int
    target_um_uim: tuple[int, int] | None
    umbrella_first_cut: int
    gaps: list[str] = field(default_factory=list)
    qualifies_for_umbrella: bool = False
    jurisdiction_notes: list[str] = field(default_factory=list)


def _bracket_at_least(amount: float) -> int:
    for b in LIABILITY_BRACKETS:
        if b >= amount:
            return b
    return LIABILITY_BRACKETS[-1]


def liability_exposure(attachable_assets: float, household_income: float) -> float:
    """Assets a judgment reaches, plus a garnishment proxy on future wages."""
    return attachable_assets + GARNISHMENT_YEARS * household_income


def assess_liability(
    coverage: dict,
    *,
    attachable_assets: float,
    household_income: float,
    rules,
) -> LiabilityAssessment:
    exposure = liability_exposure(attachable_assets, household_income)

    per_person = _bracket_at_least(min(attachable_assets, LIABILITY_BRACKETS[-1]))
    per_person = max(per_person, UMBRELLA_ATTACHMENT["bi_per_person"])
    per_person = min(per_person, AUTO_BI_CEILING[0])
    per_accident = max(
        _bracket_at_least(per_person * 2), UMBRELLA_ATTACHMENT["bi_per_accident"]
    )
    per_accident = min(per_accident, AUTO_BI_CEILING[1])
    target_pd = max(UMBRELLA_ATTACHMENT["pd"], _bracket_at_least(0))

    a = LiabilityAssessment(
        exposure=exposure,
        target_bi=(per_person, per_accident),
        target_pd=target_pd,
        target_um_uim=(per_person, per_accident),
        umbrella_first_cut=max(1_000_000, _round_up_million(exposure)),
    )

    bi = coverage.get("bodily_injury") or {}
    pd = coverage.get("property_damage") or {}
    um = coverage.get("um_uim_bodily_injury") or {}

    have_bi = (bi.get("per_person") or 0, bi.get("per_accident") or 0)
    have_pd = pd.get("per_accident") or 0
    have_um = (um.get("per_person") or 0, um.get("per_accident") or 0)

    if have_bi[0] < per_person or have_bi[1] < per_accident:
        a.gaps.append(
            f"Bodily injury {_money(have_bi[0])}/{_money(have_bi[1])} → "
            f"{_money(per_person)}/{_money(per_accident)}."
        )
    if have_pd < target_pd:
        a.gaps.append(
            f"Property damage {_money(have_pd)} → {_money(target_pd)}. "
            "One late-model SUV plus a guardrail clears $100K."
        )

    if rules.known and rules.um_uim_capped_at_bi:
        a.jurisdiction_notes.append(
            f"{rules.state}: UM/UIM may not exceed the policy's BI limits — "
            "raise BI first, then UM/UIM to match."
        )
    elif not rules.known:
        a.jurisdiction_notes.append(
            "Jurisdiction not in the rules table. UM/UIM caps, UMPD "
            "availability, and statutory minimums are unverified for this "
            "state — confirm with the carrier before acting."
        )

    if have_um[0] < per_person or have_um[1] < per_accident:
        a.gaps.append(
            f"UM/UIM bodily injury {_money(have_um[0])}/{_money(have_um[1])} → "
            f"{_money(per_person)}/{_money(per_accident)}. This is the only "
            "coverage that pays your own family for lost earning capacity and "
            "permanent impairment when the at-fault driver has nothing. "
            "Health insurance pays medical bills and nothing else."
        )

    a.qualifies_for_umbrella = (
        have_bi[0] >= UMBRELLA_ATTACHMENT["bi_per_person"]
        and have_bi[1] >= UMBRELLA_ATTACHMENT["bi_per_accident"]
        and have_pd >= UMBRELLA_ATTACHMENT["pd"]
    )
    return a


def umpd_guidance(rules, *, collision_being_dropped: bool) -> list[str]:
    """UM Property Damage only becomes an interesting question once collision
    comes off — while collision is in force it is redundant, and in some
    states not even purchasable."""
    out: list[str] = []
    if not rules.known:
        return [
            "UM Property Damage rules are unverified for this state. Ask the "
            "carrier whether it is available and at what limit."
        ]
    if not rules.umpd_available:
        return [f"{rules.state} does not offer UM Property Damage."]
    if not collision_being_dropped and rules.umpd_excluded_by_collision:
        out.append(
            f"{rules.state} does not allow UMPD alongside collision. It "
            "becomes purchasable only if collision comes off."
        )
        return out
    cap = f"capped at {_money(rules.umpd_max)}" if rules.umpd_max else "up to the PD limit"
    ded = f", {_money(rules.umpd_deductible)} deductible" if rules.umpd_deductible else ""
    out.append(f"Add UM Property Damage — {cap}{ded}.")
    out.extend(rules.notes)
    return out


#: Age at which a dependent driving friends around changes the MedPay answer.
MEDPAY_TRIGGER_AGE = 15


def medpay_guidance(medical_payments, dependents: list[dict]) -> list[str]:
    """MedPay is usually duplicative — until a teenager starts carrying
    passengers, at which point it pays their bills without waiting for a fault
    determination."""
    out: list[str] = []
    # Youngest first: the one just starting to drive is the live trigger, not
    # the one who has been driving for years.
    near = sorted(
        (d for d in dependents if (d.get("age") or 0) >= MEDPAY_TRIGGER_AGE),
        key=lambda d: (d.get("age") or 0),
    )
    if medical_payments:
        out.append(
            f"Medical Payments {_money(medical_payments)} is in force. With "
            "strong health coverage it largely duplicates the PPO, at-fault "
            "passenger injuries fall to BI liability, and uninsured scenarios "
            "to UM/UIM. Worth pricing the drop."
        )
    else:
        out.append(
            "Medical Payments declined. Defensible where health coverage is "
            "strong: the PPO covers your family, BI liability covers "
            "passengers you injure, UM/UIM covers uninsured drivers."
        )
    if near:
        oldest = near[0].get("age")
        out.append(
            f"Revisit: a dependent aged {oldest} is at or near driving age. "
            "MedPay pays a passenger's bills immediately, without a fault "
            "determination — that is worth having before a teenager starts "
            "driving friends."
        )
    return out


def _round_up_million(x: float) -> int:
    import math

    return int(math.ceil(x / 1_000_000.0)) * 1_000_000


def _money(x: float | int | None) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
