"""Comparable-sale normalization and bounded home-offer strategy."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest
from pf import cli
from pf import home_offer as O


AS_OF = date(2026, 8, 30)
RUNNER_PATH = (
    Path(__file__).resolve().parents[1] / "skills" / "home-offer-strategy" / "run.py"
)
SPEC = importlib.util.spec_from_file_location("home_offer_strategy_run", RUNNER_PATH)
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def comp(
    label: str,
    price: float,
    *,
    sqft: float = 1800,
    concessions: float = 0,
    adjustments: dict[str, float] | None = None,
    sale_date: str = "2026-07-01",
    distance: float = 0.5,
    property_type: str = "townhome",
    verified: bool = True,
    arms_length: bool = True,
    adjustments_supported: bool = True,
) -> dict:
    return {
        "id": label,
        "source": f"MLS record {label}",
        "sale_price": price,
        "sale_date": sale_date,
        "distance_miles": distance,
        "square_feet": sqft,
        "property_type": property_type,
        "verified": verified,
        "arms_length": arms_length,
        "adjustments_supported": adjustments_supported,
        "seller_concessions": concessions,
        "adjustments": adjustments or {},
    }


def offer(*, competition: str = "unknown") -> dict:
    return {
        "list_price": 525_000,
        "subject": {
            "label": "Maple Ridge home",
            "property_type": "townhome",
            "square_feet": 1800,
        },
        "selection": {
            "minimum_comparables": 3,
            "maximum_age_days": 180,
            "maximum_distance_miles": 2,
            "maximum_gross_adjustment_rate": 0.25,
        },
        "market": {
            "competing_offers": competition,
            "subject_days_on_market": 12,
            "market_median_days_on_market": 20,
            "price_reductions": 0,
        },
        "strategy": {
            "financing": "mortgage",
            "maximum_premium_rate": 0.02,
            "appraisal_gap_cash_limit": 15_000,
            "offer_increment": 1_000,
        },
        "comparables": [
            comp("c1", 500_000),
            comp("c2", 520_000),
            comp("c3", 540_000),
        ],
    }


def test_concessions_are_netted_before_signed_adjustments():
    data = offer()
    data["comparables"][0] = comp(
        "c1", 520_000, concessions=10_000,
        sqft=1700, adjustments={"living_area": 15_000, "condition": -5_000},
    )
    result = O.assess(data, as_of=AS_OF, affordability_ceiling=700_000)
    reviewed = result.comparables[0]
    assert reviewed.net_sale_price == 510_000
    assert reviewed.adjustment_total == 10_000
    assert reviewed.adjusted_price == 520_000
    assert reviewed.gross_adjustment_rate == pytest.approx(20_000 / 510_000)


def test_median_and_middle_half_are_robust_to_order():
    data = offer()
    data["comparables"] = [
        comp("high", 560_000), comp("low", 480_000),
        comp("middle", 520_000), comp("upper", 540_000),
    ]
    result = O.assess(data, as_of=AS_OF, affordability_ceiling=700_000)
    assert result.observed_low == 480_000
    assert result.core_low == 510_000
    assert result.central_value == 530_000
    assert result.core_high == 545_000
    assert result.observed_high == 560_000


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"verified": False}, "source not verified"),
        ({"arms_length": False}, "not confirmed arm's-length"),
        ({"adjustments_supported": False}, "adjustment basis not verified"),
        ({"sale_date": "2025-01-01"}, "days old"),
        ({"sale_date": "2027-01-01"}, "after the analysis date"),
        ({"distance_miles": 5}, "distance"),
        ({"property_type": "single_family"}, "property type differs"),
        ({"square_feet": 1500}, "living area differs"),
    ],
)
def test_weak_comparables_remain_visible_but_are_excluded(change, reason):
    data = offer()
    data["comparables"][0].update(change)
    result = O.assess(data, as_of=AS_OF, affordability_ceiling=700_000)
    reviewed = result.comparables[0]
    assert not reviewed.included
    assert any(reason in item for item in reviewed.reasons)
    assert result.blockers


def test_explicit_adjustments_can_support_property_and_size_differences():
    data = offer()
    data["comparables"][0] = comp(
        "c1", 500_000, sqft=1600, property_type="condo",
        adjustments={"living_area": 20_000, "property_type": 5_000},
    )
    result = O.assess(data, as_of=AS_OF, affordability_ceiling=700_000)
    assert result.comparables[0].included


def test_excessive_gross_adjustment_excludes_a_comp():
    data = offer()
    data["comparables"][0] = comp(
        "c1", 500_000, sqft=1200, adjustments={"living_area": 130_000})
    result = O.assess(data, as_of=AS_OF, affordability_ceiling=700_000)
    assert not result.comparables[0].included
    assert "gross adjustments" in result.comparables[0].reasons[-1]


def test_walkaway_uses_the_lowest_of_value_affordability_and_appraisal_caps():
    result = O.assess(offer(), as_of=AS_OF, affordability_ceiling=515_500)
    assert result.core_high == 530_000
    assert result.value_ceiling == 540_600
    assert result.appraisal_ceiling == 535_000
    assert result.walk_away_price == 515_000
    assert result.binding_constraints == ("stress-tested affordability",)
    assert result.opening_offer == 515_000


def test_appraisal_gap_caps_a_mortgage_bid_but_not_a_cash_bid():
    mortgage = O.assess(offer(), as_of=AS_OF, affordability_ceiling=700_000)
    assert mortgage.walk_away_price == 535_000
    assert mortgage.binding_constraints == ("appraisal-gap cash",)

    cash_offer = offer()
    cash_offer["strategy"]["financing"] = "cash"
    cash_offer["strategy"].pop("appraisal_gap_cash_limit")
    cash = O.assess(cash_offer, as_of=AS_OF, affordability_ceiling=700_000)
    assert cash.appraisal_ceiling is None
    assert cash.walk_away_price == 540_000


@pytest.mark.parametrize(
    ("competition", "expected"),
    [("multiple", "competitive"), ("possible", "balanced"),
     ("unknown", "balanced"), ("none", "uncontested")],
)
def test_competition_selects_posture_without_moving_the_cap(
    competition, expected,
):
    result = O.assess(
        offer(competition=competition), as_of=AS_OF,
        affordability_ceiling=700_000,
    )
    assert result.posture == expected
    assert result.walk_away_price == 535_000


def test_stale_reduced_uncontested_listing_creates_leverage_posture():
    data = offer(competition="none")
    data["market"]["subject_days_on_market"] = 31
    data["market"]["market_median_days_on_market"] = 20
    data["market"]["price_reductions"] = 1
    result = O.assess(data, as_of=AS_OF, affordability_ceiling=700_000)
    assert result.posture == "leverage"
    assert result.opening_offer == 510_000


def test_affordability_blocker_withholds_offer_but_keeps_comp_evidence():
    result = O.assess(
        offer(), as_of=AS_OF, affordability_ceiling=700_000,
        affordability_blockers=("occupancy assumption is inconsistent",),
    )
    assert result.central_value == 520_000
    assert result.opening_offer is None
    assert result.walk_away_price is None
    assert result.blockers == ["occupancy assumption is inconsistent"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data["comparables"].append(deepcopy(data["comparables"][0])),
        lambda data: data["comparables"].append("not a mapping"),
        lambda data: data["comparables"][0].update(seller_concessions=None),
        lambda data: data["comparables"][0].update(sale_price=float("nan")),
        lambda data: data["strategy"].update(maximum_premium_rate=-0.01),
        lambda data: data["strategy"].update(offer_increment=1_000_000),
        lambda data: data["market"].update(competing_offers="guaranteed"),
    ],
)
def test_contradictory_or_nonfinite_inputs_are_refused(mutate):
    data = offer()
    mutate(data)
    with pytest.raises(O.OfferError):
        O.assess(data, as_of=AS_OF, affordability_ceiling=700_000)


def test_report_renders_the_actionable_offer_ladder(monkeypatch):
    analysis = O.assess(
        offer(competition="multiple"), as_of=AS_OF,
        affordability_ceiling=700_000,
    )
    monkeypatch.setattr(RUNNER.O, "assess_from_facts", lambda _data: analysis)
    writer = cli.Writer()
    RUNNER.build({}, writer)
    report = writer.render()
    assert "Open at $525,000 and do not exceed $535,000" in report
    assert "## Offer ladder" in report
    assert "## Subject-to-comparable data points" in report
    assert "| Property | Basis | Type | Living area | Date | Distance |" in report
    assert "| Maple Ridge home | subject listing | townhome | 1,800 |" in report
    assert "| c1 | closed sale | townhome | 1,800 | 2026-07-01 |" in report
    assert "MLS record c1" in report
    assert "Appraisal-gap cash ceiling" in report
    assert "Weakest input" in report


def test_missing_comparables_route_a_web_capable_agent_to_research(tmp_path):
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps({
        "meta": {
            "schema_version": 1,
            "as_of": "2026-09-20",
            "currency": "USD",
            "jurisdiction": {"country": "US", "state": "CA"},
        },
    }), encoding="utf-8")
    completed = subprocess.run(
        (sys.executable, str(RUNNER_PATH), "--facts", str(facts)),
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 1
    assert "web-capable agent" in completed.stdout
    assert "public closed-sale sources" in completed.stdout
    assert "affordability ceiling" in completed.stdout
