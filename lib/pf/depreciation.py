"""Cost recovery for an owner-operator: §179, bonus, or standard mileage.

## The one idea

**A deduction and a deduction are not the same deduction.** Three things
separate them, and each one is where a household gets caught:

1. **§179 cannot create or increase a loss.** It is limited to taxable income
   from the trade or business; the excess carries forward. Bonus depreciation
   has no such limit — it *can* drive the business to a loss. So in a low-income
   year the two elections that look identical on paper are not: one produces a
   deduction now, the other produces a carryforward.
2. **The vehicle method is chosen once.** Claim actual expenses with
   accelerated depreciation in year one and standard mileage is closed off for
   that vehicle for as long as it is owned. Start with standard mileage and the
   option to switch to actual expenses stays open — though only on straight
   line from then on. The asymmetry is the decision.
3. **Business use must stay above 50%.** Below that, §179 and bonus are
   unavailable, and if use *falls* below 50% in a later year the accelerated
   deduction already taken is recaptured as ordinary income.

## On the heavy-vehicle deduction

The >6,000 lb GVWR exception to the luxury auto limits is real, and it is the
single most aggressively marketed line in small-business tax. This module
computes it and then computes what happens when it goes wrong, because the
marketing does not: the >50% business-use test is where people are caught, the
records that prove it are a contemporaneous mileage log, and the recapture on a
later drop below 50% arrives in a year the cash has already been spent.

## What comes from the facts file

**Every year-specific figure** — the §179 dollar limit and its phase-out
threshold, the bonus percentage, the luxury auto caps, the SUV §179 cap, the
standard mileage rate. None of them are held in this repository. `REVIEW.md` A3
records `limits.py` as an unverified tax-code mirror that must not grow, and
these figures change annually or by legislation. Absent, this module reports
the structure and refuses the figure.

## Basis

Nominal, first-year federal deduction, before any state conformity. Several
states decouple from bonus depreciation and some from §179 — a state deduction
is not computed here and must not be inferred from the federal one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SECTION_179 = "section_179"
BONUS = "bonus"
STANDARD_MILEAGE = "standard_mileage"
ACTUAL_STRAIGHT_LINE = "actual_straight_line"

#: Below this share of business use, §179 and bonus are unavailable and the
#: asset must be depreciated straight line under ADS. Crossing back below it in
#: a later year triggers recapture of what was already taken.
BUSINESS_USE_FLOOR = 0.50

#: Gross vehicle weight rating above which the §280F luxury auto caps do not
#: apply. The line that the heavy-SUV deduction is built on.
HEAVY_GVWR_LBS = 6_000

#: Above this GVWR a vehicle is outside the SUV §179 cap as well — a genuine
#: work truck rather than an SUV. Bed length and seating also matter; this is a
#: screen, not a determination.
WORK_VEHICLE_GVWR_LBS = 14_000

#: Margin below the 50% test at which the recapture exposure is worth raising
#: unprompted. A business at 55% use is one contract change from a problem.
USE_WARNING_MARGIN = 0.10

#: Recovery period used for the straight-line comparison that recapture is
#: measured against. Five years is the MACRS class life for a vehicle.
VEHICLE_RECOVERY_YEARS = 5

DEPRECIATION_SOURCE = (
    "IRC §280F(b) and §280F(d)(4) (the 50% qualified-business-use test and "
    "the recapture that follows falling below it); §179(b)(5) and "
    "§280F(d)(5)(A) (the 6,000 lb GVWR line that takes a vehicle outside the "
    "passenger-automobile caps, and the 14,000 lb line above the SUV §179 "
    "cap); §168(e) and Rev. Proc. 87-56 asset class 00.241 (the five-year "
    "MACRS class life for a vehicle). The year-specific dollar figures — the "
    "§179 limit, its phase-out, the SUV cap, the §280F caps, the bonus "
    "percentage and the standard mileage rate — are **not** here: they come "
    "from the facts file via `YearFigures`, per REVIEW.md A3"
)
DEPRECIATION_VERIFIED = (
    "unverified — check against irs.gov Publications 463 and 946")


@dataclass(frozen=True)
class YearFigures:
    """Year-specific statutory figures, from the facts file. Never guessed."""

    year: int | None = None
    section_179_limit: float | None = None
    #: Dollar-for-dollar phase-out of the §179 limit begins here.
    section_179_phaseout: float | None = None
    #: SUV-specific §179 cap for vehicles between 6,000 and 14,000 lb GVWR.
    suv_179_cap: float | None = None
    #: Bonus depreciation percentage for property placed in service this year.
    bonus_pct: float | None = None
    #: §280F first-year cap for a passenger auto, bonus claimed.
    luxury_auto_year1_cap: float | None = None
    #: §280F first-year cap where bonus is *not* claimed. Materially lower than
    #: the bonus figure, and a separate number — using one for the other
    #: overstates what a §179 election on a passenger auto actually buys.
    luxury_auto_year1_cap_no_bonus: float | None = None
    standard_mileage_rate: float | None = None
    source: str = ""

    def missing_for(self, method: str) -> list[str]:
        need = {
            SECTION_179: {"assumptions.section_179_limit": self.section_179_limit},
            BONUS: {"assumptions.bonus_depreciation_pct": self.bonus_pct},
            STANDARD_MILEAGE: {
                "assumptions.standard_mileage_rate": self.standard_mileage_rate},
        }[method]
        return [k for k, v in need.items() if v is None]


@dataclass(frozen=True)
class Asset:
    description: str
    cost: float
    business_use: float | None = None
    #: Vehicles only. `None` means not a vehicle.
    gvwr_lbs: int | None = None
    annual_business_miles: float | None = None
    #: Actual operating cost for the year — fuel, insurance, repairs,
    #: registration. Needed to compare actual expenses against mileage.
    actual_operating_cost: float | None = None
    placed_in_service: str | None = None

    @property
    def is_vehicle(self) -> bool:
        return self.gvwr_lbs is not None or self.annual_business_miles is not None

    @property
    def heavy(self) -> bool:
        return self.gvwr_lbs is not None and self.gvwr_lbs > HEAVY_GVWR_LBS

    @property
    def business_cost(self) -> float | None:
        if self.business_use is None:
            return None
        return self.cost * self.business_use


@dataclass
class Option:
    method: str
    label: str
    year_one_deduction: float | None
    #: §179 amount disallowed by the taxable-income limit and carried forward.
    carryforward: float = 0.0
    capped_by: str | None = None
    #: True when choosing this in year one forecloses standard mileage for the
    #: life of the vehicle.
    locks_out_mileage: bool = False
    unavailable: str | None = None
    findings: list[str] = field(default_factory=list)


@dataclass
class Election:
    asset: Asset
    options: list[Option]
    taxable_business_income: float | None
    figures: YearFigures
    findings: list[str] = field(default_factory=list)

    @property
    def usable(self) -> list[Option]:
        return [o for o in self.options
                if o.unavailable is None and o.year_one_deduction is not None]

    @property
    def largest(self) -> Option | None:
        return max(self.usable, key=lambda o: o.year_one_deduction or 0.0,
                   default=None)


# ── the pieces ──────────────────────────────────────────────────────────────


def section_179_limit(figures: YearFigures, *, total_placed_in_service: float
                      ) -> float | None:
    """The §179 dollar limit after the phase-out for heavy asset purchases.

    The phase-out reduces the limit dollar for dollar above the threshold, so a
    business that bought a lot of equipment this year may have less §179
    available than the headline figure — which is the figure everybody quotes.
    """
    if figures.section_179_limit is None:
        return None
    if figures.section_179_phaseout is None:
        return figures.section_179_limit
    over = max(0.0, total_placed_in_service - figures.section_179_phaseout)
    return max(0.0, figures.section_179_limit - over)


def recapture_exposure(
    *, deduction_taken: float, cost_basis: float, years_held: int = 1,
    recovery_years: int = VEHICLE_RECOVERY_YEARS,
) -> float:
    """Ordinary income on a later drop below 50% business use.

    The excess of accelerated depreciation already claimed over the
    straight-line amount that would have been allowed. It lands as ordinary
    income in the year use drops — typically a year when the cash is long gone
    and the vehicle is worth less than the tax bill.
    """
    straight_line = cost_basis / recovery_years * max(1, years_held)
    return max(0.0, deduction_taken - straight_line)


def evaluate(
    asset: Asset,
    figures: YearFigures,
    *,
    taxable_business_income: float | None,
    total_placed_in_service: float | None = None,
) -> Election:
    """Compare the year-one elections available for one asset."""
    e = Election(asset, [], taxable_business_income, figures)
    use = asset.business_use
    biz_cost = asset.business_cost

    if use is None:
        e.findings.append(
            "**Business-use percentage is not recorded, so nothing can be "
            "computed.** This is not a detail: it scales every deduction below, "
            "it decides whether §179 and bonus are available at all, and it is "
            "the figure an examiner asks for first. Unknown is not 100%.")
        return e

    if use < BUSINESS_USE_FLOOR:
        e.findings.append(
            f"**Business use is {use:.0%}, below the 50% floor.** Neither §179 "
            "nor bonus depreciation is available. The asset is depreciated "
            "straight line under the alternative depreciation system, and the "
            "personal share is not deductible at all.")
        e.options.append(Option(
            ACTUAL_STRAIGHT_LINE, "Straight line (ADS)",
            (biz_cost or 0.0) / VEHICLE_RECOVERY_YEARS,
            capped_by="business use below 50%"))
        if asset.is_vehicle:
            e.options.append(_mileage_option(asset, figures))
        return e

    # ── §179 ────────────────────────────────────────────────────────────
    miss = figures.missing_for(SECTION_179)
    if miss:
        e.options.append(Option(
            SECTION_179, "§179 expensing", None,
            unavailable="Missing from the facts file: " + ", ".join(
                f"`{k}`" for k in miss) + ". The limit is indexed annually and "
            "is not held in this repository, so no figure is produced."))
    else:
        limit = section_179_limit(
            figures, total_placed_in_service=total_placed_in_service
            or asset.cost) or 0.0
        cap_reason = None
        amount = min(biz_cost or 0.0, limit)
        if amount < (biz_cost or 0.0):
            cap_reason = "§179 dollar limit"
        # Between 6,000 and 14,000 lb GVWR an SUV escapes the passenger-auto
        # caps but not the SUV-specific §179 cap. Above 14,000 lb it escapes
        # both — that is a work vehicle, not an SUV.
        if (asset.heavy and figures.suv_179_cap is not None
                and (asset.gvwr_lbs or 0) < WORK_VEHICLE_GVWR_LBS
                and amount > figures.suv_179_cap):
            amount = figures.suv_179_cap
            cap_reason = "SUV §179 cap (6,000–14,000 lb GVWR)"

        auto_cap = None
        if asset.is_vehicle and not asset.heavy:
            # A passenger auto is subject to §280F whichever election is made,
            # and the no-bonus cap is the lower of the two figures.
            auto_cap = (figures.luxury_auto_year1_cap_no_bonus
                        or figures.luxury_auto_year1_cap)
        if auto_cap is not None and amount > auto_cap:
            amount = auto_cap
            cap_reason = "§280F luxury auto first-year cap"

        carry = 0.0
        if taxable_business_income is not None:
            allowed = max(0.0, min(amount, taxable_business_income))
            carry = amount - allowed
            if carry > 0:
                cap_reason = "taxable business income"
            amount = allowed
        opt = Option(SECTION_179, "§179 expensing", amount, carry, cap_reason,
                     locks_out_mileage=asset.is_vehicle)
        if asset.is_vehicle and not asset.heavy:
            if auto_cap is None:
                opt.findings.append(
                    "This is a passenger auto at or below 6,000 lb GVWR and no "
                    "§280F cap is recorded, so the figure above is **uncapped "
                    "and therefore wrong.** Supply "
                    "`assumptions.luxury_auto_year1_cap_no_bonus`.")
            elif figures.luxury_auto_year1_cap_no_bonus is None:
                opt.findings.append(
                    "The §280F cap applied here is the *with-bonus* figure, "
                    "because `assumptions.luxury_auto_year1_cap_no_bonus` is "
                    "not recorded. The no-bonus cap is lower, so this "
                    "**overstates** what §179 alone buys on a passenger auto.")
        if taxable_business_income is None:
            opt.findings.append(
                "Taxable business income is not recorded, so the income "
                "limitation is **not applied** to the figure above. §179 cannot "
                "create or increase a loss — supply the income and the report "
                "will say how much of this actually lands this year.")
        elif carry > 0:
            opt.findings.append(
                f"**{_money(carry)} of the §179 election does not land this "
                f"year.** §179 is limited to taxable business income "
                f"({_money(taxable_business_income)}) and cannot create or "
                "increase a loss. The excess carries forward indefinitely, "
                "which is not nothing — but it is not this year's deduction, "
                "and a decision made on the headline figure assumed it was.")
        e.options.append(opt)

    # ── bonus ───────────────────────────────────────────────────────────
    miss = figures.missing_for(BONUS)
    if miss:
        e.options.append(Option(
            BONUS, "Bonus depreciation", None,
            unavailable="Missing from the facts file: " + ", ".join(
                f"`{k}`" for k in miss) + ". The percentage has been legislated "
            "up and down more than once; it is not held in this repository."))
    else:
        amount = (biz_cost or 0.0) * (figures.bonus_pct or 0.0)
        cap_reason = None
        if asset.is_vehicle and not asset.heavy:
            if figures.luxury_auto_year1_cap is None:
                e.findings.append(
                    "This is a passenger auto at or below 6,000 lb GVWR, so the "
                    "§280F first-year cap applies — and "
                    "`assumptions.luxury_auto_year1_cap` is not recorded. The "
                    "bonus figure below is **uncapped and therefore wrong**; "
                    "supply the cap.")
            else:
                if amount > figures.luxury_auto_year1_cap:
                    amount = figures.luxury_auto_year1_cap
                    cap_reason = "§280F luxury auto first-year cap"
        opt = Option(BONUS, "Bonus depreciation", amount, 0.0, cap_reason,
                     locks_out_mileage=asset.is_vehicle)
        opt.findings.append(
            "**Bonus depreciation can create or increase a net operating "
            "loss**, which §179 cannot. In a year where business income is thin "
            "that is the whole difference between the two elections, and it "
            "runs the other way from the usual advice: a loss is only worth "
            "creating if it can be used.")
        e.options.append(opt)

    # ── mileage ─────────────────────────────────────────────────────────
    if asset.is_vehicle:
        e.options.append(_mileage_option(asset, figures))
        e.findings.extend(_vehicle_findings(asset, figures, e))

    return e


def _mileage_option(asset: Asset, figures: YearFigures) -> Option:
    miss = figures.missing_for(STANDARD_MILEAGE)
    if miss:
        return Option(
            STANDARD_MILEAGE, "Standard mileage", None,
            unavailable="Missing from the facts file: " + ", ".join(
                f"`{k}`" for k in miss) + ". The rate is set annually.")
    if asset.annual_business_miles is None:
        return Option(
            STANDARD_MILEAGE, "Standard mileage", None,
            unavailable="`annual_business_miles` is not recorded. A mileage "
            "deduction is miles times a rate; without the miles there is "
            "nothing to compute, and estimating them is exactly what the "
            "substantiation rules do not accept.")
    amount = asset.annual_business_miles * (figures.standard_mileage_rate or 0.0)
    opt = Option(STANDARD_MILEAGE, "Standard mileage", amount)
    opt.findings.append(
        "The standard rate **already includes depreciation**, so no separate "
        "depreciation, §179 or bonus may be claimed on the same vehicle in the "
        "same year. It also reduces basis, which matters on sale.")
    return opt


def _vehicle_findings(asset: Asset, figures: YearFigures,
                      e: Election) -> list[str]:
    out: list[str] = []
    use = asset.business_use or 0.0

    out.append(
        "**Year one decides the method for the life of this vehicle — in one "
        "direction only.** Claim actual expenses with depreciation now and "
        "standard mileage is closed off for this vehicle permanently. Start "
        "with standard mileage and you may switch to actual expenses later, "
        "but only on straight line. If the two are close, the reversible "
        "choice is worth something the arithmetic does not show.")

    if asset.heavy:
        out.append(
            f"At {asset.gvwr_lbs:,} lb GVWR this is above the 6,000 lb line, so "
            "the §280F passenger-auto caps do not apply and the first-year "
            "deduction can be large. **This is the most aggressively marketed "
            "deduction in small-business tax, and the marketing omits the "
            "conditions.** The vehicle must be placed in service and actually "
            "used in the business this year, above 50%, and the proof is a "
            "contemporaneous mileage log — not a reconstruction.")

    if BUSINESS_USE_FLOOR <= use < BUSINESS_USE_FLOOR + USE_WARNING_MARGIN:
        biggest = e.largest
        taken = biggest.year_one_deduction if biggest else 0.0
        exposure = recapture_exposure(
            deduction_taken=taken or 0.0,
            cost_basis=asset.business_cost or asset.cost)
        out.append(
            f"**Business use is {use:.0%} — barely over the line.** One changed "
            "contract or one relocation and it drops below 50%, at which point "
            "the accelerated deduction already claimed is recaptured as "
            f"ordinary income: about {_money(exposure)} on the largest election "
            "above. That arrives in a year the cash is spent and the vehicle is "
            "worth less than the tax on it. A thin margin over the test is a "
            "reason to take the smaller deduction, not the larger one.")

    if asset.actual_operating_cost is None and asset.annual_business_miles:
        out.append(
            "`actual_operating_cost` is not recorded, so actual expenses cannot "
            "be compared against the mileage figure on a like-for-like basis. "
            "The comparison above is depreciation only — fuel, insurance, "
            "repairs and registration are deductible under the actual method "
            "and are already inside the standard rate.")
    return out


# ── the standing choice ─────────────────────────────────────────────────────


def method_lock(first_year_method: str | None) -> list[str]:
    """What a year-one method choice does to the years after it."""
    if first_year_method is None:
        return ["No first-year method is recorded for this vehicle, so the "
                "options still open cannot be determined. It is on the return "
                "for the year it was placed in service."]
    if first_year_method == STANDARD_MILEAGE:
        return [
            "Standard mileage was taken in year one, so **both methods remain "
            "available.** Switching to actual expenses is allowed, but "
            "depreciation from then on must be straight line over the "
            "remaining recovery period, on a basis already reduced by the "
            "depreciation component of the mileage rate.",
            "That flexibility has a value the year-one arithmetic never "
            "shows, and it is the reason the smaller deduction is sometimes "
            "the better election.",
        ]
    return [
        "Actual expenses with depreciation were taken in year one, so "
        "**standard mileage is permanently unavailable for this vehicle.** "
        "Every future year must use actual expenses, which means keeping "
        "receipts for the life of the vehicle, not just a mileage log.",
    ]


def _money(x) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
