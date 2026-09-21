"""Comparable-sale evidence and a bounded home-offer strategy.

This module answers one decision: what opening price and walk-away ceiling are
defensible when verified closed sales are reconciled with the household's
existing stress-tested affordability limit?  It does not fetch market data,
invent adjustment rates, estimate an appraisal, or recommend waiving buyer
protections.  All amounts are nominal dollars as of the recorded analysis date.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime

from . import facts as F
from . import housing_affordability as A

#: A core adjusted-value range wider than this share of its midpoint is weak
#: evidence for a precise bid.  It is a diagnostic, not a valuation haircut.
WIDE_CORE_RANGE_RATE = 0.10

#: A listing at least this many times the local median days on market is
#: treated as having negotiation leverage when no competing offer is recorded.
STALE_LISTING_MULTIPLIER = 1.5

COMPETITION_STATES = {"none", "possible", "multiple", "unknown"}
FINANCING_KINDS = {"mortgage", "cash"}


class OfferError(ValueError):
    """Recorded offer facts are contradictory or unusable."""


@dataclass(frozen=True)
class ComparableResult:
    label: str
    source: str
    sale_price: float
    sale_date: date
    age_days: int
    distance_miles: float
    square_feet: float
    net_sale_price: float
    adjustment_total: float
    gross_adjustment_rate: float
    adjusted_price: float
    adjusted_price_per_sqft: float
    included: bool
    reasons: tuple[str, ...]


@dataclass
class OfferAnalysis:
    subject_label: str
    list_price: float
    affordability_ceiling: float
    comparables: tuple[ComparableResult, ...]
    minimum_comparables: int
    competition: str
    posture: str
    core_low: float | None = None
    central_value: float | None = None
    core_high: float | None = None
    observed_low: float | None = None
    observed_high: float | None = None
    value_ceiling: float | None = None
    appraisal_ceiling: float | None = None
    opening_offer: float | None = None
    walk_away_price: float | None = None
    appraisal_gap_at_cap: float | None = None
    binding_constraints: tuple[str, ...] = ()
    blockers: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    @property
    def usable_comparables(self) -> tuple[ComparableResult, ...]:
        return tuple(comp for comp in self.comparables if comp.included)


def _number(mapping: dict, key: str, scope: str) -> float:
    value = mapping.get(key)
    if value is None or isinstance(value, bool):
        raise OfferError(f"{scope}.{key} must be recorded; unknown is not zero")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise OfferError(f"{scope}.{key} must be numeric") from exc
    if not math.isfinite(number):
        raise OfferError(f"{scope}.{key} must be finite")
    return number


def _text(mapping: dict, key: str, scope: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise OfferError(f"{scope}.{key} must be recorded")
    return value.strip()


def _date(value: object, scope: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise OfferError(f"{scope} must be an ISO date") from exc
    raise OfferError(f"{scope} must be an ISO date")


def _quantile(values: list[float], q: float) -> float:
    """Linearly interpolated quantile over an already validated sample."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _round_down(value: float, increment: float) -> float:
    return math.floor((value + 1e-9) / increment) * increment


def _review_comparable(
    raw: dict,
    *,
    subject_type: str,
    subject_square_feet: float,
    as_of: date,
    maximum_age_days: int,
    maximum_distance_miles: float,
    maximum_gross_adjustment_rate: float,
) -> ComparableResult:
    label = _text(raw, "id", "comparable")
    scope = f"comparable {label}"
    source = _text(raw, "source", scope)
    sale_price = _number(raw, "sale_price", scope)
    concessions = _number(raw, "seller_concessions", scope)
    distance = _number(raw, "distance_miles", scope)
    square_feet = _number(raw, "square_feet", scope)
    property_type = _text(raw, "property_type", scope).lower()
    sold = _date(raw.get("sale_date"), f"{scope}.sale_date")

    if sale_price <= 0:
        raise OfferError(f"{scope}.sale_price must be positive")
    if concessions < 0 or concessions >= sale_price:
        raise OfferError(
            f"{scope}.seller_concessions must be nonnegative and below sale price")
    if distance < 0:
        raise OfferError(f"{scope}.distance_miles cannot be negative")
    if square_feet <= 0:
        raise OfferError(f"{scope}.square_feet must be positive")

    raw_adjustments = raw.get("adjustments")
    if not isinstance(raw_adjustments, dict):
        raise OfferError(
            f"{scope}.adjustments must be a mapping; use an empty mapping "
            "only after confirming that no adjustment is needed")
    adjustments: dict[str, float] = {}
    for name, value in raw_adjustments.items():
        if not isinstance(name, str) or not name.strip():
            raise OfferError(f"{scope}.adjustments contains an unnamed item")
        if value is None or isinstance(value, bool):
            raise OfferError(f"{scope}.adjustments.{name} must be numeric")
        try:
            amount = float(value)
        except (TypeError, ValueError) as exc:
            raise OfferError(
                f"{scope}.adjustments.{name} must be numeric") from exc
        if not math.isfinite(amount):
            raise OfferError(f"{scope}.adjustments.{name} must be finite")
        adjustments[name] = amount

    net_price = sale_price - concessions
    adjustment_total = sum(adjustments.values())
    adjusted_price = net_price + adjustment_total
    if adjusted_price <= 0:
        raise OfferError(f"{scope} adjustments produce a nonpositive value")
    gross_rate = sum(abs(value) for value in adjustments.values()) / net_price
    age_days = (as_of - sold).days

    reasons: list[str] = []
    if raw.get("verified") is not True:
        reasons.append("source not verified")
    if raw.get("arms_length") is not True:
        reasons.append("not confirmed arm's-length")
    if raw.get("adjustments_supported") is not True:
        reasons.append("adjustment basis not verified")
    if age_days < 0:
        reasons.append("sale date is after the analysis date")
    elif age_days > maximum_age_days:
        reasons.append(
            f"sale is {age_days} days old; limit is {maximum_age_days}")
    if distance > maximum_distance_miles:
        reasons.append(
            f"distance {distance:g} mi exceeds {maximum_distance_miles:g} mi")
    if property_type != subject_type and "property_type" not in adjustments:
        reasons.append("property type differs without an explicit adjustment")
    if square_feet != subject_square_feet and "living_area" not in adjustments:
        reasons.append("living area differs without an explicit adjustment")
    if gross_rate > maximum_gross_adjustment_rate:
        reasons.append(
            f"gross adjustments {gross_rate:.1%} exceed "
            f"{maximum_gross_adjustment_rate:.1%}")

    return ComparableResult(
        label=label,
        source=source,
        sale_price=sale_price,
        sale_date=sold,
        age_days=age_days,
        distance_miles=distance,
        square_feet=square_feet,
        net_sale_price=net_price,
        adjustment_total=adjustment_total,
        gross_adjustment_rate=gross_rate,
        adjusted_price=adjusted_price,
        adjusted_price_per_sqft=adjusted_price / subject_square_feet,
        included=not reasons,
        reasons=tuple(reasons),
    )


def assess(
    offer: dict,
    *,
    as_of: date,
    affordability_ceiling: float,
    affordability_blockers: tuple[str, ...] = (),
) -> OfferAnalysis:
    """Evaluate supplied closed sales and construct a bounded offer ladder."""
    as_of = _date(as_of, "as_of")
    if not isinstance(offer, dict):
        raise OfferError("housing.offer must be a mapping")
    subject = offer.get("subject")
    selection = offer.get("selection")
    strategy = offer.get("strategy")
    market = offer.get("market")
    comparables = offer.get("comparables")
    for value, name in (
        (subject, "subject"), (selection, "selection"),
        (strategy, "strategy"), (market, "market"),
    ):
        if not isinstance(value, dict):
            raise OfferError(f"housing.offer.{name} must be a mapping")
    if not isinstance(comparables, list):
        raise OfferError("housing.offer.comparables must be a list")
    if any(not isinstance(row, dict) for row in comparables):
        raise OfferError("every housing.offer.comparables item must be a mapping")

    subject_label = _text(subject, "label", "housing.offer.subject")
    subject_type = _text(
        subject, "property_type", "housing.offer.subject").lower()
    subject_square_feet = _number(
        subject, "square_feet", "housing.offer.subject")
    list_price = _number(offer, "list_price", "housing.offer")
    if list_price <= 0 or subject_square_feet <= 0:
        raise OfferError("list price and subject square feet must be positive")

    minimum_raw = _number(
        selection, "minimum_comparables", "housing.offer.selection")
    if not minimum_raw.is_integer() or minimum_raw < 2:
        raise OfferError("minimum_comparables must be an integer of at least 2")
    minimum = int(minimum_raw)
    maximum_age_raw = _number(
        selection, "maximum_age_days", "housing.offer.selection")
    if not maximum_age_raw.is_integer() or maximum_age_raw < 1:
        raise OfferError("maximum_age_days must be a positive integer")
    maximum_age = int(maximum_age_raw)
    maximum_distance = _number(
        selection, "maximum_distance_miles", "housing.offer.selection")
    maximum_adjustment = _number(
        selection, "maximum_gross_adjustment_rate", "housing.offer.selection")
    if maximum_distance <= 0:
        raise OfferError("maximum_distance_miles must be positive")
    if not 0 <= maximum_adjustment < 1:
        raise OfferError("maximum_gross_adjustment_rate must be from 0 to below 1")

    reviewed = tuple(
        _review_comparable(
            row,
            subject_type=subject_type,
            subject_square_feet=subject_square_feet,
            as_of=as_of,
            maximum_age_days=maximum_age,
            maximum_distance_miles=maximum_distance,
            maximum_gross_adjustment_rate=maximum_adjustment,
        )
        for row in comparables
    )
    labels = [comp.label for comp in reviewed]
    if len(labels) != len(set(labels)):
        raise OfferError("comparable IDs must be unique")

    competition = _text(
        market, "competing_offers", "housing.offer.market").lower()
    if competition not in COMPETITION_STATES:
        raise OfferError(
            "competing_offers must be none, possible, multiple, or unknown")
    days_on_market = _number(
        market, "subject_days_on_market", "housing.offer.market")
    reductions_raw = _number(
        market, "price_reductions", "housing.offer.market")
    if days_on_market < 0:
        raise OfferError("subject_days_on_market cannot be negative")
    if not reductions_raw.is_integer() or reductions_raw < 0:
        raise OfferError("price_reductions must be a nonnegative integer")
    reductions = int(reductions_raw)
    median_days_raw = market.get("market_median_days_on_market")
    median_days = None
    if median_days_raw is not None:
        median_days = _number(
            market, "market_median_days_on_market", "housing.offer.market")
        if median_days <= 0:
            raise OfferError("market_median_days_on_market must be positive")
    stale = (
        median_days is not None
        and days_on_market >= median_days * STALE_LISTING_MULTIPLIER
    )
    if competition == "multiple":
        posture = "competitive"
    elif competition == "none" and (stale or reductions > 0):
        posture = "leverage"
    elif competition == "none":
        posture = "uncontested"
    else:
        posture = "balanced"

    try:
        affordability_ceiling = float(affordability_ceiling)
    except (TypeError, ValueError) as exc:
        raise OfferError(
            "stress-tested affordability ceiling must be numeric") from exc
    if not math.isfinite(affordability_ceiling) or affordability_ceiling <= 0:
        raise OfferError("stress-tested affordability ceiling must be positive")

    result = OfferAnalysis(
        subject_label=subject_label,
        list_price=list_price,
        affordability_ceiling=float(affordability_ceiling),
        comparables=reviewed,
        minimum_comparables=minimum,
        competition=competition,
        posture=posture,
        blockers=list(affordability_blockers),
    )
    usable = result.usable_comparables
    if len(usable) < minimum:
        result.blockers.append(
            f"Only {len(usable)} verified comparable(s) pass the recorded "
            f"selection rules; {minimum} are required.")
        return result

    values = [comp.adjusted_price for comp in usable]
    result.observed_low = min(values)
    result.core_low = _quantile(values, 0.25)
    result.central_value = _quantile(values, 0.50)
    result.core_high = _quantile(values, 0.75)
    result.observed_high = max(values)

    if result.blockers:
        return result

    maximum_premium = _number(
        strategy, "maximum_premium_rate", "housing.offer.strategy")
    increment = _number(
        strategy, "offer_increment", "housing.offer.strategy")
    financing = _text(
        strategy, "financing", "housing.offer.strategy").lower()
    if not 0 <= maximum_premium < 1:
        raise OfferError("maximum_premium_rate must be from 0 to below 1")
    if increment <= 0:
        raise OfferError("offer_increment must be positive")
    if financing not in FINANCING_KINDS:
        raise OfferError("financing must be mortgage or cash")

    result.value_ceiling = result.core_high * (1.0 + maximum_premium)
    limits = {
        "comparable evidence": result.value_ceiling,
        "stress-tested affordability": result.affordability_ceiling,
    }
    if financing == "mortgage":
        appraisal_gap = _number(
            strategy, "appraisal_gap_cash_limit", "housing.offer.strategy")
        if appraisal_gap < 0:
            raise OfferError("appraisal_gap_cash_limit cannot be negative")
        result.appraisal_ceiling = result.central_value + appraisal_gap
        limits["appraisal-gap cash"] = result.appraisal_ceiling

    raw_cap = min(limits.values())
    if increment > raw_cap:
        raise OfferError("offer_increment cannot exceed the binding ceiling")
    result.walk_away_price = _round_down(raw_cap, increment)
    result.binding_constraints = tuple(
        label for label, value in limits.items()
        if math.isclose(value, raw_cap, rel_tol=0.0, abs_tol=0.01)
    )

    if posture == "competitive":
        anchor = max(list_price, result.central_value)
    elif posture == "leverage":
        anchor = min(list_price, result.core_low)
    else:
        anchor = min(list_price, result.central_value)
    result.opening_offer = _round_down(
        min(anchor, result.walk_away_price), increment)
    result.appraisal_gap_at_cap = max(
        0.0, result.walk_away_price - result.central_value)

    if result.core_high - result.core_low > (
            result.central_value * WIDE_CORE_RANGE_RATE):
        result.findings.append(
            "The middle half of adjusted comparable values spans more than "
            f"{WIDE_CORE_RANGE_RATE:.0%}; the evidence is too dispersed for "
            "a precise bid.")
    if competition == "unknown":
        result.findings.append(
            "Competing-offer status is unknown; the opening posture is "
            "balanced rather than presented as a prediction of seller response.")
    if list_price > result.core_high:
        result.findings.append(
            "The list price is above the core adjusted-comparable range; "
            "asking price is not evidence of market value.")
    elif list_price < result.core_low:
        result.findings.append(
            "The list price is below the core adjusted-comparable range; "
            "competition may close that gap, but the listing itself does not "
            "justify bidding through the cap.")
    if result.walk_away_price < result.core_low:
        result.findings.append(
            "The buyer's bounded ceiling is below the core evidence range. "
            "Treat any offer as low-probability and accept losing the property; "
            "do not stretch the affordability or appraisal-gap limit.")
    if list_price > result.walk_away_price:
        result.findings.append(
            "The list price exceeds the walk-away ceiling. A below-list offer "
            "or no offer is the only strategy consistent with the recorded limits.")
    excluded = len(reviewed) - len(usable)
    if excluded:
        result.findings.append(
            f"{excluded} supplied comparable(s) were excluded by the recorded "
            "verification and selection rules.")
    return result


def assess_from_facts(data: dict) -> OfferAnalysis:
    """Use the same affordability and transition calculations as their skill."""
    offer = F._dig(data, "housing.offer") or {}
    if not isinstance(offer, dict):
        raise OfferError("housing.offer must be a mapping")
    subject = offer.get("subject") or {}
    if not isinstance(subject, dict):
        raise OfferError("housing.offer.subject must be a mapping")
    purchase = F._dig(data, "housing.purchase") or {}
    disclosure = F._dig(data, "property_review") or {}
    if not isinstance(purchase, dict):
        raise OfferError("housing.purchase must be a mapping")
    if not isinstance(disclosure, dict):
        raise OfferError("property_review must be a mapping")
    subject_label = subject.get("label")
    if purchase.get("label") and subject_label != purchase.get("label"):
        raise OfferError(
            "housing.offer.subject.label must match housing.purchase.label")
    subject_type = str(subject.get("property_type") or "").lower()
    purchase_type = str(purchase.get("property_type") or "").lower()
    disclosure_type = str(disclosure.get("property_type") or "").lower()
    if purchase_type and subject_type != purchase_type:
        raise OfferError(
            "housing.offer subject type must match housing.purchase.property_type")
    if disclosure_type and subject_type != disclosure_type:
        raise OfferError(
            "housing.offer subject type must match property_review.property_type")
    affordability = A.assess_from_facts(data)
    transition = A.transition_from_facts(data)
    blockers = list(transition.blockers)
    failures = [
        check for check in A.phase_cash_checks(affordability.scenarios, transition)
        if not check.passes
    ]
    if failures:
        blockers.append(
            f"The housing transition misses its savings floor in "
            f"{len(failures)} phase/scenario row(s).")
    analysis_date = F.as_of(data)
    if analysis_date is None:
        raise OfferError("meta.as_of must be a valid ISO date")
    return assess(
        offer,
        as_of=analysis_date,
        affordability_ceiling=affordability.stress_tested_ceiling,
        affordability_blockers=tuple(blockers),
    )
