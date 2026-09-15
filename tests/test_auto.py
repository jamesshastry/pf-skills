"""Tests for the auto drop test.

Fixtures here are synthetic. Two of them are the Rivera household vehicles
from inputs/facts.example.yml; the rest are boundary probes.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import auto, jurisdiction  # noqa: E402

OUTBACK = {
    "id": "v1",
    "label": "2019 Subaru Outback",
    "value": 14500,
    "value_basis": "acv",
    "lienholder": False,
    "comprehensive_premium_annual": 340,
    "collision_premium_annual": 760,
    "deductible_comprehensive": 500,
    "deductible_collision": 500,
}

COROLLA = {
    "id": "v2",
    "label": "2012 Toyota Corolla",
    "value": 4200,
    "value_basis": "instant_offer",
    "lienholder": False,
    "comprehensive_premium_annual": 190,
    "collision_premium_annual": 450,
    "deductible_comprehensive": 500,
    "deductible_collision": 500,
}

RIVERA_LIQUID = 85_000.0
RIVERA_BUFFER = 85_000 / (96_000 / 12)  # 10.6 months


# ── value bands ─────────────────────────────────────────────────────────────


def test_acv_basis_is_a_point_not_a_band():
    b = auto.acv_band(10_000, "acv")
    assert b.is_point and b.low == 10_000


def test_instant_offer_widens_upward():
    b = auto.acv_band(4200, "instant_offer")
    # 15–25% below ACV means ACV is above the offer, never below it.
    assert b.low == pytest.approx(4200 / 0.85)
    assert b.high == pytest.approx(4200 / 0.75)
    assert b.low > 4200


def test_unknown_basis_raises_rather_than_defaulting():
    with pytest.raises(ValueError, match="unknown value_basis"):
        auto.acv_band(1000, "kbb_vibes")


def test_ratio_inverts_with_value():
    r = auto.ratio_band(1000, 10_000, "instant_offer")
    assert r.low < r.high  # higher ACV → lower ratio
    assert r.high == pytest.approx(1000 / (10_000 / 0.85))


def test_straddles():
    assert auto.Band(0.09, 0.11).straddles(0.10)
    assert not auto.Band(0.11, 0.13).straddles(0.10)
    assert not auto.Band(0.07, 0.09).straddles(0.10)


# ── expected recovery ───────────────────────────────────────────────────────


def test_expected_recovery_is_capped_by_the_car():
    """A $2,000 car cannot produce a $5,700 collision payout."""
    cheap = auto.expected_annual_recovery(2_000, deductible_collision=500)
    dear = auto.expected_annual_recovery(30_000, deductible_collision=500)
    assert cheap.high < dear.low


def test_deductible_reduces_expected_recovery():
    low = auto.expected_annual_recovery(10_000, deductible_collision=250)
    high = auto.expected_annual_recovery(10_000, deductible_collision=1_000)
    assert high.low < low.low


# ── the two fixture branches ────────────────────────────────────────────────


def test_outback_is_a_keep():
    a = auto.assess_vehicle(OUTBACK, liquid_assets=RIVERA_LIQUID, buffer_months=RIVERA_BUFFER)
    assert a.decision == "keep"
    assert a.ratio.is_point
    assert a.ratio.low == pytest.approx(1100 / 14500)  # 7.59%
    assert a.ratio_verdict == "keep"
    assert a.absorb_verdict == "material"


def test_corolla_is_a_drop():
    a = auto.assess_vehicle(COROLLA, liquid_assets=RIVERA_LIQUID, buffer_months=RIVERA_BUFFER)
    assert a.decision == "drop_collision"
    # Not "trivial": at the top of the ACV band the loss is ~6% of liquid,
    # above the 5% line. Collision goes on price; comprehensive is judged on
    # its own ratio and survives.
    assert a.absorb_verdict == "material"
    assert "keep it" in a.comprehensive_note


def test_a_genuinely_disposable_car_drops_both():
    v = dict(COROLLA, value=1_200, value_basis="acv",
             collision_premium_annual=300, comprehensive_premium_annual=120)
    a = auto.assess_vehicle(v, liquid_assets=RIVERA_LIQUID, buffer_months=RIVERA_BUFFER)
    assert a.absorb_verdict == "trivial"
    assert a.decision == "drop_both"


def test_known_split_does_not_ask_for_a_split():
    a = auto.assess_vehicle(COROLLA, liquid_assets=RIVERA_LIQUID, buffer_months=RIVERA_BUFFER)
    assert "unresolved" not in a.comprehensive_note


def test_combined_premium_flags_the_split_as_unresolved():
    a = auto.assess_vehicle(STRADDLER, liquid_assets=100_000, buffer_months=8)
    assert "unresolved" in a.comprehensive_note


def test_corolla_ratio_is_above_threshold_on_every_basis():
    """The offer/ACV distinction must not be load-bearing here — the answer is
    the same at both ends of the band. Contrast with the straddle test."""
    a = auto.assess_vehicle(COROLLA, liquid_assets=RIVERA_LIQUID, buffer_months=RIVERA_BUFFER)
    assert a.ratio.low > auto.RATIO_DROP_THRESHOLD
    assert a.ratio_verdict == "drop_candidate"


# ── decision-rule boundaries ────────────────────────────────────────────────


def test_lienholder_blocks_everything():
    v = dict(COROLLA, lienholder=True)
    a = auto.assess_vehicle(v, liquid_assets=RIVERA_LIQUID, buffer_months=RIVERA_BUFFER)
    assert a.decision == "blocked"


def test_no_emergency_buffer_blocks_a_drop():
    """The buffer is what does the self-insuring. Without one, keep."""
    a = auto.assess_vehicle(COROLLA, liquid_assets=RIVERA_LIQUID, buffer_months=1.5)
    assert a.decision == "keep"
    assert "buffer" in a.reasons[0].lower()


def test_severe_loss_keeps_coverage_even_at_a_terrible_ratio():
    """A household with $20K liquid and a $40K car: ratio says drop, and that
    would be catastrophic advice."""
    v = dict(OUTBACK, value=40_000, collision_premium_annual=3_600,
             comprehensive_premium_annual=800)
    a = auto.assess_vehicle(v, liquid_assets=20_000, buffer_months=6)
    assert a.ratio.low > auto.RATIO_DROP_THRESHOLD
    assert a.decision == "keep"
    assert a.absorb_verdict == "severe"


STRADDLER = {
    "label": "straddler",
    "value": 9_000,
    "value_basis": "instant_offer",
    "lienholder": False,
    "comp_collision_premium_annual": 1_125,
    "deductible_collision": 250,
    "deductible_comprehensive": 250,
}


def test_straddling_ratio_falls_through_to_absorbability():
    """A stated value on an uncertain basis whose ratio band crosses 10%, on a
    car that is material but not severe against liquid assets. This is the
    case the whole band-propagation design exists for."""
    a = auto.assess_vehicle(STRADDLER, liquid_assets=100_000, buffer_months=8)
    assert a.ratio.straddles(auto.RATIO_DROP_THRESHOLD)
    assert a.ratio_verdict == "inconclusive"
    assert a.absorb_verdict == "material"
    assert a.decision == "drop_collision"
    assert a.comprehensive_note  # comp left as its own question


def test_missing_premium_is_reported_not_assumed():
    v = {"label": "x", "value": 5000, "value_basis": "acv"}
    a = auto.assess_vehicle(v, liquid_assets=RIVERA_LIQUID, buffer_months=12)
    assert a.decision == "insufficient_data"


# ── liability ───────────────────────────────────────────────────────────────

RIVERA_COVERAGE = {
    "bodily_injury": {"per_person": 100_000, "per_accident": 300_000},
    "property_damage": {"per_accident": 50_000},
    "um_uim_bodily_injury": {"per_person": 30_000, "per_accident": 60_000},
    "um_property_damage": None,
    "medical_payments": None,
}


def test_rivera_liability_gaps():
    a = auto.assess_liability(
        RIVERA_COVERAGE,
        attachable_assets=113_000,
        household_income=180_000,
        rules=jurisdiction.TX,
    )
    assert not a.qualifies_for_umbrella  # BI 100/300 is below 250/500
    assert len(a.gaps) == 3  # BI, PD, UM/UIM
    assert a.target_bi == (250_000, 500_000)
    assert a.target_pd == 100_000


def test_umbrella_first_cut_rounds_up_to_a_million():
    a = auto.assess_liability(
        RIVERA_COVERAGE,
        attachable_assets=113_000,
        household_income=180_000,
        rules=jurisdiction.TX,
    )
    # 113k + 2 × 180k = 473k → $1M floor
    assert a.umbrella_first_cut == 1_000_000


def test_larger_household_gets_a_larger_umbrella():
    a = auto.assess_liability(
        RIVERA_COVERAGE,
        attachable_assets=900_000,
        household_income=394_000,
        rules=jurisdiction.CA,
    )
    assert a.umbrella_first_cut == 2_000_000  # 900k + 788k = 1.69M → $2M


def test_auto_bi_target_is_capped_and_the_rest_goes_to_the_umbrella():
    """A $900K household does not buy $500K/$500K auto BI — carriers often
    won't write it, and an umbrella is cheaper per dollar above the ceiling."""
    a = auto.assess_liability(
        RIVERA_COVERAGE,
        attachable_assets=900_000,
        household_income=394_000,
        rules=jurisdiction.CA,
    )
    assert a.target_bi == auto.AUTO_BI_CEILING == (300_000, 500_000)
    assert a.target_um_uim == (300_000, 500_000)
    assert a.umbrella_first_cut == 2_000_000


def test_estimate_basis_bands_both_ways():
    """An unqualified estimate can be high or low; the others only run low."""
    b = auto.acv_band(6_500, "estimate")
    assert b.low < 6_500 < b.high


def test_adequate_coverage_produces_no_gaps():
    good = {
        "bodily_injury": {"per_person": 300_000, "per_accident": 500_000},
        "property_damage": {"per_accident": 100_000},
        "um_uim_bodily_injury": {"per_person": 300_000, "per_accident": 500_000},
    }
    a = auto.assess_liability(
        good, attachable_assets=113_000, household_income=180_000, rules=jurisdiction.TX
    )
    assert a.gaps == []
    assert a.qualifies_for_umbrella


# ── jurisdiction ────────────────────────────────────────────────────────────


def test_unknown_state_says_so_instead_of_guessing():
    r = jurisdiction.rules_for("ZZ")
    assert not r.known
    lines = auto.umpd_guidance(r, collision_being_dropped=True)
    assert "unverified" in lines[0]


def test_ca_umpd_is_unavailable_while_collision_is_in_force():
    lines = auto.umpd_guidance(jurisdiction.CA, collision_being_dropped=False)
    assert "only if collision comes off" in lines[0]


def test_ca_umpd_becomes_available_and_is_capped():
    lines = auto.umpd_guidance(jurisdiction.CA, collision_being_dropped=True)
    assert "Add UM Property Damage" in lines[0]
    assert "$3,500" in lines[0]
    assert any("partial backstop" in ln for ln in lines)


def test_tx_umpd_is_available_alongside_collision():
    lines = auto.umpd_guidance(jurisdiction.TX, collision_being_dropped=False)
    assert "Add UM Property Damage" in lines[0]


# ── medpay ──────────────────────────────────────────────────────────────────


def test_medpay_declined_with_young_children_needs_no_revisit():
    lines = auto.medpay_guidance(None, [{"age": 8}, {"age": 5}])
    assert len(lines) == 1


def test_medpay_revisit_names_the_youngest_new_driver():
    """The 16-year-old is the live trigger; the 20-year-old already drives."""
    lines = auto.medpay_guidance(None, [{"age": 20}, {"age": 16}])
    assert len(lines) == 2
    assert "16" in lines[1] and "20" not in lines[1]
