"""Cluster 10 — cross-border retirement. Synthetic fixtures only."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import crossborder as X  # noqa: E402
from pf import healthcare as H  # noqa: E402
from pf import retirement as R  # noqa: E402

LEGS_SPLIT = [
    {"name": "Austin", "country": "US", "months_per_year": 7,
     "monthly_spending": 7000, "home_currency": True},
    {"name": "Bengaluru", "country": "IN", "months_per_year": 5,
     "monthly_spending": 2600, "home_currency": False},
]


# ── the shared Medicare penalty rates ───────────────────────────────────────


def test_the_medicare_penalty_rates_are_healthcares_and_not_a_second_copy():
    """Identity, not equality. Both modules once carried their own literal —
    under two different names for the Part B one — and a literal would pass
    this test while the two silently diverged."""
    assert X.PART_B_PENALTY_PER_12M is H.PART_B_PENALTY_PER_12M
    assert X.PART_D_PENALTY_PER_MONTH is H.PART_D_PENALTY_PER_MONTH


def test_the_old_part_b_penalty_alias_is_gone():
    """The duplicate lived under `PART_B_PENALTY_PER_YEAR`. Two names for one
    statutory rate is how the second copy stayed invisible."""
    assert not hasattr(X, "PART_B_PENALTY_PER_YEAR")


# ── the country table ───────────────────────────────────────────────────────


def test_only_the_checked_countries_are_in_the_table():
    assert X.countries_available() == ["IN", "US"]


def test_an_unchecked_country_is_unknown_not_approximated():
    c = X.country_for("PT")
    assert not c.known
    assert c.roth_status == X.UNKNOWN_STATUS
    assert c.roth_recognised is None
    assert c.residency_tests == ()


def test_no_country_means_unknown():
    assert X.country_for(None) is X.UNKNOWN
    assert not X.country_for("").known


def test_every_known_country_carries_provenance():
    for code in X.countries_available():
        c = X.country_for(code)
        assert c.source and c.verified_on


def test_every_known_country_names_something_to_verify_with_a_professional():
    """The honest state of this data. An entry claiming nothing needs checking
    would be the one to distrust."""
    for code in X.countries_available():
        assert X.country_for(code).needs_professional_verification


def test_the_us_recognises_the_wrapper_and_does_not_invert_advice():
    us = X.country_for("us")
    assert us.roth_status == X.RECOGNISED
    assert us.roth_recognised is True
    assert not us.inverts_conversion_advice


def test_india_is_contested_rather_than_resolved_either_way():
    c = X.country_for("IN")
    assert c.roth_status == X.CONTESTED
    assert c.roth_recognised is None, "contested must not read as recognised"
    assert c.inverts_conversion_advice, "an irreversible act needs a settled reading"


def test_the_india_entry_encodes_no_treaty_article_number():
    """Refusing to fabricate a citation is the point, so it is tested."""
    c = X.country_for("IN")
    text = " ".join((c.roth_note, c.transitional_note, c.source) + c.notes)
    assert "Article" not in text
    assert "article" not in text


def test_the_india_entry_asserts_no_foreign_tax_rate():
    c = X.country_for("IN")
    text = " ".join((c.roth_note, c.transitional_note) + c.notes)
    assert "%" not in text


def test_india_carries_the_rnor_transitional_status():
    c = X.country_for("IN")
    assert c.transitional_status == "RNOR"
    assert c.transitional_max_years == 3
    assert "foreign-source income" in c.transitional_note


def test_india_encodes_both_day_tests_including_the_sixty_day_one():
    days = {t.days for t in X.country_for("IN").residency_tests}
    assert days == {182, 60}


def test_asserted_values_are_generated_from_the_entry():
    v = X.country_for("IN").asserted_values()
    assert v["roth_status"] == X.CONTESTED
    assert v["transitional_status"] == "RNOR"
    assert ("resident — 182 days", 182, 1, True) in v["residency_tests"]


def test_the_thirty_one_day_precondition_is_not_a_standalone_test():
    """Flagging a precondition as though it established residence is noise,
    and noise trains the reader to skip warnings."""
    t = next(t for t in X.country_for("US").residency_tests if t.days == 31)
    assert not t.standalone


# ── portability: the inversion ──────────────────────────────────────────────


def test_a_non_recognising_destination_inverts_the_conversion_advice():
    p = X.portability([{"country": "IN"}], roth_balance=42_000,
                      planned_conversion=40_000, conversion_tax_rate=0.24)
    assert p.any_inverts
    joined = " ".join(p.findings)
    assert "conversion advice inverts" in joined
    assert "conditional on not moving" in joined


def test_the_recognising_destination_does_not_invert():
    p = X.portability([{"country": "US"}], roth_balance=42_000)
    assert not p.any_inverts
    assert not any("inverts" in f for f in p.findings)


def test_the_timing_mechanism_is_explained_not_just_asserted():
    p = X.portability([{"country": "IN"}], roth_balance=10_000)
    joined = " ".join(p.findings)
    assert "same" in joined and "foreign tax credit" in joined


def test_the_conversion_tax_is_priced_when_a_rate_is_supplied():
    p = X.portability([{"country": "IN"}], roth_balance=0,
                      planned_conversion=40_000, conversion_tax_rate=0.24)
    assert p.conversion_tax_now == pytest.approx(9_600)
    assert any("$9,600" in f for f in p.findings)


def test_a_conversion_with_no_rate_cannot_be_priced():
    p = X.portability([{"country": "IN"}], roth_balance=0,
                      planned_conversion=40_000, conversion_tax_rate=None)
    assert p.conversion_tax_now is None
    assert any("cannot be determined" in f for f in p.findings)


def test_the_irreversibility_is_stated_because_it_is_the_whole_argument():
    p = X.portability([{"country": "IN"}], roth_balance=1,
                      planned_conversion=1_000, conversion_tax_rate=0.24)
    assert any("cannot be undone" in f for f in p.findings)


# ── portability: quantifying, and refusing to ───────────────────────────────


def test_exposed_balance_is_the_roth_plus_one_conversion():
    p = X.portability([{"country": "IN"}], roth_balance=42_000,
                      planned_conversion=40_000, conversion_tax_rate=0.24)
    assert p.destinations[0].exposed_balance == 82_000


def test_a_missing_roth_balance_is_undeterminable_not_zero():
    p = X.portability([{"country": "IN"}], roth_balance=None)
    d = p.destinations[0]
    assert d.exposed_balance is None
    assert d.double_tax_estimate is None
    assert any("cannot be determined" in f for f in d.findings)


def test_no_destination_rate_means_no_number_rather_than_a_guess():
    p = X.portability([{"country": "IN"}], roth_balance=50_000)
    d = p.destinations[0]
    assert d.double_tax_estimate is None
    assert any("will not guess a foreign tax rate" in f for f in d.findings)


def test_a_supplied_destination_rate_is_used_and_labelled_as_rough():
    p = X.portability([{"country": "IN", "ordinary_income_rate": 0.30}],
                      roth_balance=100_000)
    d = p.destinations[0]
    assert d.double_tax_estimate == pytest.approx(30_000)
    assert any("order of magnitude" in f for f in d.findings)


def test_an_unknown_destination_refuses_to_reason_by_analogy():
    p = X.portability([{"country": "PT"}], roth_balance=100_000)
    d = p.destinations[0]
    assert not d.country.known
    assert p.any_unknown
    assert any("not in the table" in f for f in d.findings)
    assert any("will not reason by analogy" in f for f in d.findings)


def test_both_branches_can_be_reported_side_by_side():
    p = X.portability(
        [{"country": "IN", "label": "Bengaluru"},
         {"country": "US", "label": "stay in Austin"},
         {"country": "PT", "label": "Lisbon"}],
        roth_balance=42_000)
    assert [d.inverts for d in p.destinations] == [True, False, False]
    assert p.any_inverts and p.any_unknown


# ── portability: the surrounding findings ───────────────────────────────────


def test_a_distant_move_is_flagged_against_the_treaty_horizon():
    p = X.portability([{"country": "IN", "years_until_move": 12}],
                      roth_balance=1)
    assert any("years out" in f for f in p.destinations[0].findings)


def test_a_near_move_is_not_flagged_against_the_treaty_horizon():
    p = X.portability([{"country": "IN", "years_until_move": 3}],
                      roth_balance=1)
    assert not any("years out" in f for f in p.destinations[0].findings)


def test_the_transitional_window_is_surfaced_where_one_exists():
    p = X.portability([{"country": "IN"}], roth_balance=1)
    assert any("RNOR" in f for f in p.destinations[0].findings)


def test_totalization_is_imported_from_status_not_restated():
    """`status.py` owns this table. Two copies eventually disagree."""
    p = X.portability([{"country": "IN"}], roth_balance=1)
    assert any("no US–India totalization agreement" in f
               for f in p.destinations[0].findings)


def test_professional_verification_items_reach_the_output():
    p = X.portability([{"country": "IN"}], roth_balance=1)
    flagged = [f for f in p.destinations[0].findings if "Verify with a professional" in f]
    assert len(flagged) == len(X.country_for("IN").needs_professional_verification)


def test_the_report_always_closes_on_taking_it_to_a_professional():
    for code in ("US", "IN", "PT"):
        p = X.portability([{"country": code}], roth_balance=1)
        assert "cross-border tax professional" in p.findings[-1]


def test_no_destinations_still_produces_the_professional_close():
    p = X.portability([])
    assert p.destinations == []
    assert "cross-border tax professional" in p.findings[-1]


# ── geo arbitrage: the arithmetic ───────────────────────────────────────────


def test_the_blend_is_months_times_monthly_plus_fixed():
    legs = X._legs_from(LEGS_SPLIT)
    assert X.blend(legs, 18_000) == pytest.approx(7 * 7000 + 5 * 2600 + 18_000)


def test_the_stress_hits_only_the_foreign_currency_legs():
    legs = X._legs_from(LEGS_SPLIT)
    base = X.blend(legs, 18_000)
    stressed = X.stressed(legs, 18_000, 0.20)
    assert stressed - base == pytest.approx(5 * 2600 * 0.20)


def test_fixed_costs_are_not_stressed():
    legs = X._legs_from([{"name": "a", "country": "IN", "months_per_year": 12,
                          "monthly_spending": 1000}])
    assert X.stressed(legs, 5_000, 0.20) == pytest.approx(12_000 * 1.2 + 5_000)


def test_the_baseline_is_a_full_year_at_the_dearest_leg():
    p = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000,
                fixed_annual=18_000)
    assert p.baseline_annual == pytest.approx(7000 * 12 + 18_000)
    assert p.blended_annual < p.baseline_annual


def test_the_target_uses_the_retirement_module_rather_than_its_own_formula():
    p = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000)
    assert p.target == pytest.approx(
        R.target_for(p.blended_annual, R.DEFAULT_WITHDRAWAL_RATE))
    assert p.baseline_target == pytest.approx(
        R.target_for(p.baseline_annual, R.DEFAULT_WITHDRAWAL_RATE))


def test_years_to_target_uses_the_retirement_projection():
    p = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000)
    assert p.years_to_target == R.years_to(
        p.target, 500_000, 40_000, R.DEFAULT_REAL_RETURN)


def test_geo_projection_accepts_a_time_varying_savings_path():
    flat = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000)
    rising = X.model(
        LEGS_SPLIT, assets=500_000, annual_savings=40_000,
        savings_by_year=[40_000] * 3 + [60_000] * 57)
    assert rising.years_to_target <= flat.years_to_target


def test_a_cheaper_blend_reaches_the_target_sooner():
    p = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000)
    assert p.years_to_target < p.years_to_baseline
    assert p.years_saved > 0


def test_the_target_reduction_is_the_burn_saving_times_the_multiple():
    p = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000)
    assert p.target_reduction == pytest.approx(
        p.annual_saving / R.DEFAULT_WITHDRAWAL_RATE)


def test_the_stressed_target_is_higher_than_the_headline_one():
    p = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000)
    assert p.stressed_target > p.target
    assert any("weakest input" in f for f in p.findings)


def test_all_home_currency_legs_get_a_prompt_rather_than_silence():
    legs = [dict(l, home_currency=True) for l in LEGS_SPLIT]
    p = X.model(legs, assets=500_000, annual_savings=40_000)
    assert p.stressed_annual == pytest.approx(p.blended_annual)
    assert any("no FX stress has been applied" in f for f in p.findings)


# ── geo arbitrage: the refusals ─────────────────────────────────────────────


def test_months_short_of_twelve_are_reported_as_a_range_not_spread():
    legs = [dict(LEGS_SPLIT[0], months_per_year=7),
            dict(LEGS_SPLIT[1], months_per_year=4)]
    p = X.model(legs, assets=500_000, annual_savings=40_000)
    assert p.months_accounted == 11
    f = next(f for f in p.findings if "not twelve" in f)
    assert "$2,600" in f and "$7,000" in f
    assert "will not spread the gap" in f


def test_months_over_twelve_are_flagged_as_overstating():
    legs = [dict(LEGS_SPLIT[0], months_per_year=8),
            dict(LEGS_SPLIT[1], months_per_year=6)]
    p = X.model(legs, assets=500_000, annual_savings=40_000)
    assert any("more than a year" in f for f in p.findings)


def test_a_clean_twelve_month_split_raises_no_month_finding():
    p = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000)
    assert not any("not twelve" in f for f in p.findings)


def test_unrecorded_duplicate_housing_is_undeterminable_not_absent():
    p = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000,
                duplicate_housing=None)
    assert any("cannot be determined" in f and "housing" in f
               for f in p.findings)


def test_recorded_duplicate_housing_asks_whether_the_figures_include_it():
    p = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000,
                duplicate_housing=True)
    assert any("paid in both locations year-round" in f for f in p.findings)


def test_no_locations_refuses_rather_than_returning_zero():
    p = X.model([], assets=500_000, annual_savings=40_000)
    assert p.legs == []
    assert any("No locations recorded" in f for f in p.findings)


def test_healthcare_is_named_as_absent_from_the_number():
    p = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000)
    assert any("cross-border-healthcare" in f for f in p.findings)


# ── geo arbitrage: the residency side-effect ────────────────────────────────


def test_five_months_in_india_is_flagged_against_the_sixty_day_test():
    p = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000)
    hit = [f for f in p.findings if "60 days" in f and "Bengaluru" in f]
    assert hit, "a seasonal arrangement is exactly what the 60-day test catches"
    assert "travel log" in hit[0]


def test_a_leg_just_under_a_threshold_is_flagged_as_at_risk():
    """182 days is 5.98 months. Five and a half months is inside the margin."""
    legs = [dict(LEGS_SPLIT[0], months_per_year=6.5),
            dict(LEGS_SPLIT[1], months_per_year=5.5)]
    p = X.model(legs, assets=500_000, annual_savings=40_000)
    assert any("within 21 days" in f and "182" in f for f in p.findings)


def test_a_precondition_is_never_flagged_as_a_crossed_test():
    """Seven months in the US would trip the 31-day precondition if the model
    treated it as a test. It is not one."""
    p = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000)
    assert not any("minimum current-year presence" in f for f in p.findings)


def test_a_multi_year_test_is_not_flagged_from_one_years_split():
    p = X.model(LEGS_SPLIT, assets=500_000, annual_savings=40_000)
    assert not any("substantial presence" in f for f in p.findings)


def test_a_short_leg_crosses_nothing():
    legs = [dict(LEGS_SPLIT[0], months_per_year=11),
            dict(LEGS_SPLIT[1], months_per_year=1)]
    p = X.model(legs, assets=500_000, annual_savings=40_000)
    assert not any("Bengaluru" in f and "test" in f for f in p.findings)


def test_an_unknown_country_leg_says_find_the_threshold():
    legs = [{"name": "Lisbon", "country": "PT", "months_per_year": 12,
             "monthly_spending": 3000}]
    p = X.model(legs, assets=500_000, annual_savings=40_000)
    assert any("not in the country table" in f for f in p.findings)


def test_estimated_days_are_labelled_as_an_estimate():
    leg = X._legs_from(LEGS_SPLIT)[1]
    assert leg.estimated_days == pytest.approx(5 * X.DAYS_PER_MONTH)


# ── Medicare: the penalty arithmetic ────────────────────────────────────────


def test_the_penalty_counts_full_years_only():
    assert X.part_b_penalty_rate(11) == 0
    assert X.part_b_penalty_rate(12) == pytest.approx(0.10)
    assert X.part_b_penalty_rate(23) == pytest.approx(0.10)
    assert X.part_b_penalty_rate(60) == pytest.approx(0.50)


def test_a_sub_year_absence_says_no_penalty_applies():
    d = X.part_b_decision(months_abroad=11, standard_premium_monthly=185,
                          will_return=True, years_after_return=20)
    assert d.penalty_rate == 0
    assert any("no full 12-month period" in f for f in d.findings)


def test_a_long_absence_and_a_long_life_favours_keeping():
    d = X.part_b_decision(months_abroad=60, standard_premium_monthly=185,
                          will_return=True, years_after_return=20)
    assert d.penalty_rate == pytest.approx(0.50)
    assert d.keep_cost == pytest.approx(60 * 185)
    assert d.penalty_lifetime == pytest.approx(185 * 0.50 * 12 * 20)
    assert d.recommendation == "keep"


def test_a_short_life_after_returning_flips_the_recommendation():
    """The boundary is real: the penalty is time abroad × years afterwards."""
    d = X.part_b_decision(months_abroad=60, standard_premium_monthly=185,
                          will_return=True, years_after_return=4)
    assert d.recommendation == "drop"


def test_never_returning_makes_dropping_right_but_names_the_weak_input():
    d = X.part_b_decision(months_abroad=60, standard_premium_monthly=185,
                          will_return=False)
    assert d.recommendation == "drop"
    assert any("weakest input" in f for f in d.findings)


def test_an_unrecorded_intention_prices_both_arms_rather_than_assuming():
    d = X.part_b_decision(months_abroad=60, standard_premium_monthly=185,
                          will_return=None, years_after_return=20)
    assert d.recommendation == "cannot_determine"
    assert any("not recorded, and it decides this" in f for f in d.findings)
    assert any("If you do return" in f and "keeping is cheaper" in f
               for f in d.findings)


def test_missing_years_after_return_cannot_be_totalled():
    d = X.part_b_decision(months_abroad=60, standard_premium_monthly=185,
                          will_return=True, years_after_return=None)
    assert d.penalty_lifetime is None
    assert d.recommendation == "cannot_determine"


# ── Medicare: the findings that outrank the arithmetic ──────────────────────


def test_every_report_leads_on_medicare_not_covering_care_abroad():
    assert X.MEDICARE_COVERS_ABROAD is False
    d = X.part_b_decision(months_abroad=24, standard_premium_monthly=185,
                          will_return=True, years_after_return=20)
    assert "does not pay for care outside the United States" in d.findings[0]


def test_the_re_enrolment_window_is_stated():
    d = X.part_b_decision(months_abroad=24, standard_premium_monthly=185,
                          will_return=True, years_after_return=20)
    joined = " ".join(d.findings)
    assert X.GENERAL_ENROLMENT_WINDOW in joined
    assert "creditable coverage" in joined
    assert "special enrolment period" in joined


def test_the_medigap_underwriting_trap_is_reported_as_worse_than_the_penalty():
    d = X.part_b_decision(months_abroad=24, standard_premium_monthly=185,
                          will_return=True, years_after_return=20)
    assert any("worse than the penalty" in f for f in d.findings)


def test_the_irmaa_link_to_conversions_is_made():
    d = X.part_b_decision(months_abroad=24, standard_premium_monthly=185,
                          will_return=True, years_after_return=20)
    assert any("roth-portability-check" in f for f in d.findings)


def test_the_basis_of_the_premium_figures_is_stated():
    d = X.part_b_decision(months_abroad=24, standard_premium_monthly=185,
                          will_return=True, years_after_return=20)
    assert any("nominal current-year figures you supplied" in f
               for f in d.findings)


# ── Medigap and expat cover ─────────────────────────────────────────────────


def test_the_medigap_benefit_is_described_by_all_four_of_its_limits():
    joined = " ".join(X.medigap_notes(has_medigap=True))
    assert "80%" in joined and "$250" in joined
    assert "60 days" in joined and "$50,000" in joined
    assert "lifetime" in joined


def test_no_medigap_means_nothing_is_paid_abroad():
    assert any("no foreign travel emergency benefit at all" in n
               for n in X.medigap_notes(has_medigap=False))


def test_unrecorded_medigap_is_a_question_rather_than_a_no():
    assert any("not recorded" in n for n in X.medigap_notes(has_medigap=None))


def test_an_unpriced_expat_policy_refuses_a_placeholder():
    notes = X.expat_cover_notes(premium_annual=None)
    assert any("placeholder is badly misleading" in n for n in notes)


def test_a_priced_expat_policy_is_not_treated_as_a_substitute():
    notes = X.expat_cover_notes(premium_annual=9_600)
    assert any("$9,600" in n for n in notes)
    assert any("not treat them as the same product" in n for n in notes)


def test_expat_cover_always_lists_the_four_checks():
    for premium in (None, 9_600):
        notes = X.expat_cover_notes(premium_annual=premium)
        joined = " ".join(notes)
        assert "guaranteed renewable" in joined
        assert "age cap" in joined
        assert "pre-existing" in joined
        assert "repatriation" in joined


def test_the_destination_public_system_is_explicitly_refused():
    joined = " ".join(X.expat_cover_notes(premium_annual=None))
    assert "not in this repository's tables" in joined
