"""Cluster 13 — §179, bonus, mileage, and the year-one lock. Synthetic only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import depreciation as D  # noqa: E402

# Invented figures shaped like the real ones. Nothing here is a statutory
# assertion — the module reads every year-specific figure from the facts file,
# which is the whole design.
FIG = D.YearFigures(
    year=2026,
    section_179_limit=1_000_000,
    section_179_phaseout=2_500_000,
    suv_179_cap=30_000,
    bonus_pct=1.0,
    luxury_auto_year1_cap=20_000,
    luxury_auto_year1_cap_no_bonus=12_000,
    standard_mileage_rate=0.70,
)
EMPTY = D.YearFigures(year=2031)


def opt(e, method):
    return next(o for o in e.options if o.method == method)


# ── refusal paths ───────────────────────────────────────────────────────────


def test_no_year_figures_means_no_numbers_at_all():
    a = D.Asset("van", 60_000, business_use=0.8, gvwr_lbs=7_000,
                annual_business_miles=15_000)
    e = D.evaluate(a, EMPTY, taxable_business_income=100_000)
    for o in e.options:
        assert o.year_one_deduction is None
        assert o.unavailable is not None
    assert e.largest is None


def test_each_missing_field_is_named_by_its_facts_path():
    a = D.Asset("laptop", 3_000, business_use=1.0)
    e = D.evaluate(a, EMPTY, taxable_business_income=50_000)
    assert "assumptions.section_179_limit" in opt(e, D.SECTION_179).unavailable
    assert "assumptions.bonus_depreciation_pct" in opt(e, D.BONUS).unavailable


def test_unknown_business_use_is_not_treated_as_full_use():
    e = D.evaluate(D.Asset("rig", 40_000), FIG, taxable_business_income=90_000)
    assert e.options == []
    assert any("not 100%" in f for f in e.findings)


def test_mileage_without_miles_refuses_rather_than_estimating():
    a = D.Asset("car", 30_000, business_use=0.9, gvwr_lbs=4_000)
    e = D.evaluate(a, FIG, taxable_business_income=80_000)
    assert opt(e, D.STANDARD_MILEAGE).year_one_deduction is None
    assert "annual_business_miles" in opt(e, D.STANDARD_MILEAGE).unavailable


# ── the §179 income limit, which bonus does not have ────────────────────────


def test_section_179_cannot_create_a_loss_and_carries_forward():
    a = D.Asset("press", 100_000, business_use=1.0)
    e = D.evaluate(a, FIG, taxable_business_income=30_000)
    s = opt(e, D.SECTION_179)
    assert s.year_one_deduction == 30_000
    assert s.carryforward == 70_000
    assert s.capped_by == "taxable business income"


def test_bonus_is_not_limited_by_business_income_and_can_create_a_loss():
    a = D.Asset("press", 100_000, business_use=1.0)
    e = D.evaluate(a, FIG, taxable_business_income=30_000)
    b = opt(e, D.BONUS)
    assert b.year_one_deduction == 100_000
    assert b.carryforward == 0.0
    assert any("net operating loss" in f for f in b.findings)


def test_unknown_business_income_leaves_the_limit_unapplied_and_says_so():
    a = D.Asset("press", 100_000, business_use=1.0)
    e = D.evaluate(a, FIG, taxable_business_income=None)
    s = opt(e, D.SECTION_179)
    assert s.year_one_deduction == 100_000
    assert any("income limitation" in f for f in s.findings)


def test_the_179_limit_phases_out_on_heavy_purchasing():
    assert D.section_179_limit(FIG, total_placed_in_service=2_000_000) == 1_000_000
    assert D.section_179_limit(FIG, total_placed_in_service=2_900_000) == 600_000
    assert D.section_179_limit(FIG, total_placed_in_service=9_000_000) == 0.0


def test_the_limit_is_unknown_when_the_figure_is():
    assert D.section_179_limit(EMPTY, total_placed_in_service=10_000) is None


# ── business use ────────────────────────────────────────────────────────────


def test_deductions_scale_with_business_use():
    a = D.Asset("lathe", 50_000, business_use=0.6)
    e = D.evaluate(a, FIG, taxable_business_income=500_000)
    assert opt(e, D.BONUS).year_one_deduction == 30_000


def test_below_fifty_percent_use_blocks_179_and_bonus_entirely():
    a = D.Asset("suv", 80_000, business_use=0.4, gvwr_lbs=7_000,
                annual_business_miles=8_000)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    methods = {o.method for o in e.options}
    assert D.SECTION_179 not in methods
    assert D.BONUS not in methods
    assert D.ACTUAL_STRAIGHT_LINE in methods
    assert any("below the 50% floor" in f for f in e.findings)


def test_mileage_survives_when_accelerated_methods_do_not():
    a = D.Asset("suv", 80_000, business_use=0.4, gvwr_lbs=7_000,
                annual_business_miles=8_000)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    assert opt(e, D.STANDARD_MILEAGE).year_one_deduction == 8_000 * 0.70


def test_a_thin_margin_over_the_test_raises_recapture_unprompted():
    a = D.Asset("suv", 80_000, business_use=0.55, gvwr_lbs=7_000)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    assert any("barely over the line" in f for f in e.findings)


def test_a_comfortable_margin_does_not():
    a = D.Asset("suv", 80_000, business_use=0.85, gvwr_lbs=7_000)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    assert not any("barely over the line" in f for f in e.findings)


def test_recapture_is_the_excess_over_straight_line():
    got = D.recapture_exposure(deduction_taken=30_000, cost_basis=50_000)
    assert got == 30_000 - 10_000


def test_recapture_is_zero_when_nothing_was_accelerated():
    assert D.recapture_exposure(deduction_taken=10_000, cost_basis=50_000) == 0.0


# ── vehicles: the caps ──────────────────────────────────────────────────────


def test_a_passenger_auto_is_capped_by_280f_under_bonus():
    a = D.Asset("sedan", 60_000, business_use=1.0, gvwr_lbs=4_000,
                annual_business_miles=10_000)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    b = opt(e, D.BONUS)
    assert b.year_one_deduction == 20_000
    assert b.capped_by == "§280F luxury auto first-year cap"


def test_a_passenger_auto_uses_the_lower_no_bonus_cap_for_179():
    a = D.Asset("sedan", 60_000, business_use=1.0, gvwr_lbs=4_000,
                annual_business_miles=10_000)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    assert opt(e, D.SECTION_179).year_one_deduction == 12_000


def test_only_the_bonus_cap_recorded_is_flagged_as_overstating_179():
    figures = D.YearFigures(
        year=2026, section_179_limit=1_000_000, bonus_pct=1.0,
        luxury_auto_year1_cap=20_000, standard_mileage_rate=0.70)
    a = D.Asset("sedan", 60_000, business_use=1.0, gvwr_lbs=4_000)
    e = D.evaluate(a, figures, taxable_business_income=300_000)
    assert any("overstates" in f for f in opt(e, D.SECTION_179).findings)


def test_no_auto_cap_at_all_is_reported_as_wrong_not_silently_uncapped():
    figures = D.YearFigures(year=2026, section_179_limit=1_000_000,
                            bonus_pct=1.0, standard_mileage_rate=0.70)
    a = D.Asset("sedan", 60_000, business_use=1.0, gvwr_lbs=4_000)
    e = D.evaluate(a, figures, taxable_business_income=300_000)
    assert any("uncapped and therefore wrong" in f
               for f in opt(e, D.SECTION_179).findings)
    assert any("uncapped and therefore wrong" in f for f in e.findings)


def test_the_heavy_vehicle_escapes_the_passenger_auto_cap():
    a = D.Asset("pickup", 85_000, business_use=0.8, gvwr_lbs=7_500)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    assert opt(e, D.BONUS).year_one_deduction == 68_000
    assert opt(e, D.BONUS).capped_by is None


def test_a_heavy_suv_is_still_held_to_the_suv_179_cap():
    a = D.Asset("suv", 85_000, business_use=0.8, gvwr_lbs=7_500)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    s = opt(e, D.SECTION_179)
    assert s.year_one_deduction == 30_000
    assert "SUV" in s.capped_by


def test_above_14000_lb_the_suv_cap_does_not_apply():
    a = D.Asset("box truck", 85_000, business_use=0.8, gvwr_lbs=16_000)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    assert opt(e, D.SECTION_179).year_one_deduction == 68_000


def test_the_heavy_vehicle_marketing_is_answered_with_its_conditions():
    a = D.Asset("suv", 85_000, business_use=0.8, gvwr_lbs=7_500)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    text = " ".join(e.findings)
    assert "aggressively marketed" in text
    assert "contemporaneous mileage log" in text


# ── the year-one lock ───────────────────────────────────────────────────────


def test_accelerated_methods_close_off_mileage_and_mileage_does_not():
    a = D.Asset("van", 50_000, business_use=0.9, gvwr_lbs=7_000,
                annual_business_miles=20_000)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    assert opt(e, D.SECTION_179).locks_out_mileage
    assert opt(e, D.BONUS).locks_out_mileage
    assert not opt(e, D.STANDARD_MILEAGE).locks_out_mileage


def test_the_lock_is_stated_for_every_vehicle():
    a = D.Asset("van", 50_000, business_use=0.9, gvwr_lbs=7_000,
                annual_business_miles=20_000)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    assert any("in one direction only" in f for f in e.findings)


def test_non_vehicles_get_no_mileage_option_and_no_lock_talk():
    e = D.evaluate(D.Asset("server", 20_000, business_use=1.0), FIG,
                   taxable_business_income=300_000)
    assert {o.method for o in e.options} == {D.SECTION_179, D.BONUS}
    assert not any("mileage" in f for f in e.findings)


def test_mileage_in_year_one_keeps_both_methods_open():
    text = " ".join(D.method_lock(D.STANDARD_MILEAGE))
    assert "both methods remain" in text
    assert "straight line" in text


def test_actual_expenses_in_year_one_is_permanent():
    text = " ".join(D.method_lock(D.SECTION_179))
    assert "permanently unavailable" in text


def test_an_unrecorded_first_year_method_is_reported_not_assumed():
    text = " ".join(D.method_lock(None))
    assert "cannot be determined" in text


def test_mileage_rate_already_includes_depreciation():
    a = D.Asset("van", 50_000, business_use=0.9, gvwr_lbs=7_000,
                annual_business_miles=20_000)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    assert any("already includes depreciation" in f
               for f in opt(e, D.STANDARD_MILEAGE).findings)


def test_largest_option_ignores_the_ones_with_no_figure():
    a = D.Asset("van", 50_000, business_use=0.9, gvwr_lbs=7_000)
    e = D.evaluate(a, FIG, taxable_business_income=300_000)
    assert e.largest.method == D.BONUS
    assert all(o.year_one_deduction is not None for o in e.usable)
