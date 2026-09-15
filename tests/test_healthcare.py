"""Cluster 16 — ACA subsidy, Medicare timing, long-term care.

The centre of gravity of this file is the **conflict detection** (review
finding A6). Everything else is ordinary threshold and refusal coverage; the
conflict tests are the ones that would catch the defect the cluster was built to
prevent — two skills giving opposite instructions about one number with nothing
noticing.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import healthcare as H, limits as L, retirement as R  # noqa: E402

AGES85 = L.retirement_ages(1985)  # rmd 75, ss_latest 70 — the Rivera primary

#: Plausible-shaped parameters. Deliberately **not** real figures: they are
#: test inputs, and a test that transcribed real poverty levels would become a
#: second unverified copy of the thing A3 is about.
PARAMS = H.SubsidyParams(
    year=2026,
    fpl_base=15_000.0,
    fpl_per_additional=5_000.0,
    benchmark_premium_annual=24_000.0,
    cliff_applies=True,
    applicable_pct_schedule=((1.5, 0.00), (2.0, 0.02), (3.0, 0.06), (4.0, 0.085)),
    medicaid_expansion_state=True,
)


def window_at(retirement_age, ages=AGES85, claim_age=None):
    return R.conversion_window(retirement_age=retirement_age, ages=ages,
                               claim_age=claim_age)


# ── FPL and the applicable percentage ───────────────────────────────────────


def test_fpl_scales_with_household_size():
    assert H.fpl_for(1, PARAMS) == 15_000
    assert H.fpl_for(4, PARAMS) == 30_000


def test_fpl_unknown_without_parameters():
    assert H.fpl_for(4, H.SubsidyParams()) is None


def test_applicable_pct_interpolates_between_anchors():
    """The published schedule is piecewise linear, not a step table."""
    assert H.applicable_pct(2.5, PARAMS.applicable_pct_schedule) == pytest.approx(0.04)


def test_applicable_pct_is_flat_outside_the_table_rather_than_extrapolated():
    sched = PARAMS.applicable_pct_schedule
    assert H.applicable_pct(0.5, sched) == 0.00
    assert H.applicable_pct(9.9, sched) == 0.085


def test_applicable_pct_refuses_without_a_schedule():
    assert H.applicable_pct(2.5, None) is None


# ── the subsidy ─────────────────────────────────────────────────────────────


def test_subsidy_is_benchmark_less_expected_contribution():
    p = H.subsidy_at(90_000, 4, PARAMS)  # 300% of a 30,000 FPL -> 6%
    assert p.pct_of_fpl == pytest.approx(3.0)
    assert p.applicable_pct == pytest.approx(0.06)
    assert p.expected_contribution == pytest.approx(5_400)
    assert p.subsidy == pytest.approx(18_600)
    assert p.eligible is True


def test_subsidy_floors_at_zero_rather_than_going_negative():
    rich = H.SubsidyParams(**{**PARAMS.__dict__, "cliff_applies": False})
    p = H.subsidy_at(500_000, 4, rich)
    assert p.subsidy == 0.0


def test_the_cliff_removes_the_whole_credit_not_a_slice():
    below = H.subsidy_at(120_000, 4, PARAMS)   # exactly 400%
    above = H.subsidy_at(120_100, 4, PARAMS)
    assert below.subsidy > 0
    assert above.subsidy == 0.0
    assert above.eligible is False


def test_cliff_can_be_switched_off_because_it_has_been_suspended_before():
    """Whether the 400% ceiling is in force is a policy fact, not a constant."""
    no_cliff = H.SubsidyParams(**{**PARAMS.__dict__, "cliff_applies": False})
    assert H.subsidy_at(120_100, 4, no_cliff).subsidy > 0


def test_below_the_floor_in_a_non_expansion_state_is_the_coverage_gap():
    p = H.SubsidyParams(**{**PARAMS.__dict__, "medicaid_expansion_state": False})
    pt = H.subsidy_at(20_000, 4, p)  # 67% of FPL
    assert pt.eligible is False
    assert "coverage gap" in pt.reason


def test_below_the_floor_in_an_expansion_state_routes_to_medicaid():
    pt = H.subsidy_at(20_000, 4, PARAMS)
    assert pt.eligible is False
    assert "Medicaid" in pt.reason


def test_expansion_status_unknown_says_so_rather_than_picking_one():
    p = H.SubsidyParams(**{**PARAMS.__dict__, "medicaid_expansion_state": None})
    assert "not recorded" in H.subsidy_at(20_000, 4, p).reason


def test_missing_parameters_refuse_the_figure_and_name_what_is_missing():
    bare = H.SubsidyParams()
    assert not bare.computable
    assert H.subsidy_at(90_000, 4, bare).subsidy is None
    assert "assumptions.fpl_base" in bare.missing()
    assert "assumptions.aca_cliff_applies" in bare.missing()


def test_a_partially_filled_parameter_set_is_still_refused():
    """Half a table is worse than none — it invites a plausible wrong answer."""
    half = H.SubsidyParams(fpl_base=15_000, fpl_per_additional=5_000)
    assert not half.computable
    assert "assumptions.aca_benchmark_premium_annual" in half.missing()


# ── the taper ───────────────────────────────────────────────────────────────


def test_taper_is_a_marginal_rate_on_magi():
    t = H.taper_at(90_000, 4, PARAMS, step=1_000)
    assert t.lost_per_step > 0
    assert 0 < t.marginal_rate < 1


def test_taper_reports_headroom_to_the_cliff():
    t = H.taper_at(100_000, 4, PARAMS)
    assert t.headroom_to_cliff == pytest.approx(20_000)


def test_taper_headroom_goes_negative_once_past_the_cliff():
    t = H.taper_at(130_000, 4, PARAMS)
    assert t.headroom_to_cliff == pytest.approx(-10_000)


def test_taper_flags_the_step_that_crosses_the_cliff():
    t = H.taper_at(119_500, 4, PARAMS, step=1_000)
    assert t.crosses_cliff is True
    assert t.subsidy_after == 0.0


def test_taper_refuses_without_parameters():
    t = H.taper_at(90_000, 4, H.SubsidyParams())
    assert t.marginal_rate is None


# ── gap years ───────────────────────────────────────────────────────────────


def test_gap_is_retirement_to_medicare():
    g = H.gap_years(60)
    assert g.years == 5 and g.exists


def test_no_gap_when_retiring_at_or_after_medicare():
    assert H.gap_years(67).years == 0
    assert not H.gap_years(67).exists


def test_gap_unknown_without_a_retirement_age():
    assert H.gap_years(None).years is None


# ── A6: the conflict ────────────────────────────────────────────────────────


def test_the_conflict_is_detected_for_the_validating_household():
    """Retire at 60, born 1985: window 60-70, Medicare at 65. The subsidy years
    and the conversion years are the same five years. This is the test the
    cluster exists for."""
    w = window_at(60)
    assert (w.opens_age, w.closes_age) == (60, 70)

    cs = H.magi_conflicts(retirement_age=60, window=w)
    subsidy = next(c for c in cs if c.name == H.CONFLICT_SUBSIDY_VS_CONVERSION)
    assert subsidy.live
    assert subsidy.overlap_years == 5
    assert subsidy.overlap_ages == (60, 65)
    assert "roth-conversion-window" in subsidy.skills


def test_the_irmaa_conflict_is_separate_and_also_live():
    w = window_at(60)
    irmaa = next(c for c in H.magi_conflicts(retirement_age=60, window=w)
                 if c.name == H.CONFLICT_IRMAA_VS_CONVERSION)
    assert irmaa.live
    assert irmaa.overlap_ages == (63, 70)
    assert irmaa.overlap_years == 7
    assert "medicare-enrollment-timing" in irmaa.skills


def test_the_conflict_reads_the_shipped_conversion_window_not_a_copy():
    """If `retirement.conversion_window` changes its answer, this must follow.
    Two implementations of one window is the drift the repository is organised
    against."""
    w = window_at(60, claim_age=66)      # closes at 66, not 70
    assert w.closes_age == 66
    irmaa = next(c for c in H.magi_conflicts(retirement_age=60, window=w)
                 if c.name == H.CONFLICT_IRMAA_VS_CONVERSION)
    assert irmaa.overlap_ages == (63, 66)


def test_no_subsidy_conflict_when_retirement_is_after_medicare():
    w = window_at(67)
    cs = H.magi_conflicts(retirement_age=67, window=w)
    subsidy = next(c for c in cs if c.name == H.CONFLICT_SUBSIDY_VS_CONVERSION)
    assert not subsidy.live
    assert subsidy.overlap_years == 0


def test_no_conflicts_at_all_when_there_is_no_conversion_window():
    w = window_at(75)  # retires after RMDs begin
    assert not w.exists
    assert H.magi_conflicts(retirement_age=75, window=w) == []


def test_the_conflict_is_reported_even_when_it_cannot_be_quantified():
    """Its existence does not depend on the subsidy parameters. Reporting it
    only when the figures happen to be present would hide it from exactly the
    households that have not filled the file in."""
    c = next(c for c in H.magi_conflicts(retirement_age=60, window=window_at(60))
             if c.name == H.CONFLICT_SUBSIDY_VS_CONVERSION)
    assert c.live
    assert any("Not quantified" in q for q in c.quantified)


def test_the_conflict_is_quantified_as_a_marginal_rate_when_it_can_be():
    t = H.taper_at(90_000, 4, PARAMS)
    pt = H.subsidy_at(90_000, 4, PARAMS)
    c = next(c for c in H.magi_conflicts(retirement_age=60, window=window_at(60),
                                         taper=t, subsidy=pt)
             if c.name == H.CONFLICT_SUBSIDY_VS_CONVERSION)
    joined = " ".join(c.quantified)
    assert "marginal tax rate" in joined
    assert "hard ceiling" in joined          # the cliff headroom
    assert f"{pt.subsidy * 5:,.0f}" in joined  # five years of credit at stake


def test_past_the_cliff_the_conflict_reverses_rather_than_disappearing():
    t = H.taper_at(130_000, 4, PARAMS)
    pt = H.subsidy_at(130_000, 4, PARAMS)
    c = next(c for c in H.magi_conflicts(retirement_age=60, window=window_at(60),
                                         taper=t, subsidy=pt)
             if c.name == H.CONFLICT_SUBSIDY_VS_CONVERSION)
    assert any("dormant" in q for q in c.quantified)


# ── the partition ───────────────────────────────────────────────────────────


def test_the_window_partitions_into_segments_by_binding_constraint():
    segs = H.segment_conversion_window(window=window_at(60), retirement_age=60)
    assert [(s.start_age, s.end_age, s.constraints) for s in segs] == [
        (60, 63, (H.BINDS_SUBSIDY,)),
        (63, 65, (H.BINDS_SUBSIDY, H.BINDS_IRMAA)),
        (65, 70, (H.BINDS_IRMAA,)),
    ]


def test_segments_tile_the_window_exactly():
    w = window_at(58)
    segs = H.segment_conversion_window(window=w, retirement_age=58)
    assert sum(s.years for s in segs) == w.years
    assert segs[0].start_age == w.opens_age
    assert segs[-1].end_age == w.closes_age


def test_early_retirement_produces_a_genuinely_clean_segment():
    """Retiring at 55 gives years reached by neither constraint — the cheapest
    conversion capacity the household will ever have, and the thing the
    partition exists to find."""
    segs = H.segment_conversion_window(window=window_at(55), retirement_age=55)
    assert segs[0].clean is False  # ACA gap starts at retirement
    # A household already retired before the facts file's retirement age:
    segs2 = H.segment_conversion_window(window=window_at(55), retirement_age=None)
    clean = [s for s in segs2 if s.clean]
    assert clean and clean[0].start_age == 55 and clean[0].end_age == 63


def test_resolution_notes_order_clean_years_before_constrained_ones():
    notes = H.resolution_notes(
        H.segment_conversion_window(window=window_at(60), retirement_age=60))
    text = " ".join(notes)
    assert "IRMAA only" in text
    assert "the subsidy only" in text
    assert "constrained by both" in text
    assert "not a recommendation to convert" in text


def test_every_segment_is_accounted_for_in_the_notes():
    """A segment with no note is a year the report silently says nothing about,
    which is how a sequencing rule loses the years it was meant to order."""
    segs = H.segment_conversion_window(window=window_at(60), retirement_age=60)
    notes = H.resolution_notes(segs)
    for s in segs:
        assert any(f"{s.start_age}–{s.end_age}" in n for n in notes), s


def test_no_segments_without_a_window():
    assert H.segment_conversion_window(window=window_at(75), retirement_age=75) == []


# ── the ACA assessment ──────────────────────────────────────────────────────


def test_assessment_refuses_the_figure_but_still_reports_the_conflict():
    a = H.assess_aca(retirement_age=60, household_size=4, magi=None,
                     params=H.SubsidyParams(), window=window_at(60))
    assert a.point is None
    assert any("refused, not estimated" in f for f in a.findings)
    assert any(c.live for c in a.conflicts)


def test_assessment_says_unknown_magi_is_not_zero():
    a = H.assess_aca(retirement_age=60, household_size=4, magi=None,
                     params=PARAMS, window=window_at(60))
    assert any("Unknown is not zero" in f for f in a.findings)


def test_assessment_warns_when_magi_can_be_too_low():
    a = H.assess_aca(retirement_age=60, household_size=4, magi=30_000,
                     params=PARAMS, window=window_at(60))
    assert any("MAGI can be too low" in f for f in a.findings)


def test_assessment_warns_near_the_cliff():
    a = H.assess_aca(retirement_age=60, household_size=4, magi=115_000,
                     params=PARAMS, window=window_at(60))
    assert any("Within 10% of the cliff" in f for f in a.findings)


def test_assessment_does_not_warn_when_the_cliff_is_far_away():
    a = H.assess_aca(retirement_age=60, household_size=4, magi=60_000,
                     params=PARAMS, window=window_at(60))
    assert not any("of the cliff" in f for f in a.findings)


def test_assessment_names_its_weakest_input():
    a = H.assess_aca(retirement_age=60, household_size=4, magi=90_000,
                     params=PARAMS, window=window_at(60))
    assert "expected_magi_in_gap_years" in a.weakest_input


def test_assessment_handles_no_gap_without_pretending_there_is_one():
    a = H.assess_aca(retirement_age=67, household_size=2, magi=90_000,
                     params=PARAMS, window=window_at(67))
    assert any("No gap." in f for f in a.findings)


def test_assessment_always_raises_the_reconciliation_risk():
    a = H.assess_aca(retirement_age=60, household_size=4, magi=90_000,
                     params=PARAMS, window=window_at(60))
    assert any("reconciled on the tax return" in f for f in a.findings)


# ── Medicare ────────────────────────────────────────────────────────────────


def test_part_b_penalty_is_ten_percent_per_full_year_and_permanent():
    assert H.part_b_penalty_rate(1) == pytest.approx(0.10)
    assert H.part_b_penalty_rate(3) == pytest.approx(0.30)
    assert H.part_b_penalty_rate(0) == 0
    assert H.part_b_penalty_rate(-2) == 0


def test_part_d_penalty_is_one_percent_per_uncovered_month():
    assert H.part_d_penalty_rate(24) == pytest.approx(0.24)


def test_twenty_or_more_employees_means_the_group_plan_is_primary():
    a = H.assess_medicare(current_age=64, working_past_65=True,
                          employer_employees=250,
                          coverage_is_current_employment=True,
                          part_a_quarters=40, magi=None, irmaa_tiers=None,
                          contributing_to_hsa=False)
    assert a.sep_available is True
    assert any("group plan is primary" in f for f in a.findings)


def test_under_twenty_employees_means_medicare_is_primary_and_delay_is_a_trap():
    a = H.assess_medicare(current_age=64, working_past_65=True,
                          employer_employees=12,
                          coverage_is_current_employment=True,
                          part_a_quarters=40, magi=None, irmaa_tiers=None,
                          contributing_to_hsa=False)
    assert a.sep_available is False
    assert any("Medicare is primary" in f for f in a.findings)


def test_unknown_employer_size_refuses_rather_than_assuming_the_safe_case():
    a = H.assess_medicare(current_age=64, working_past_65=True,
                          employer_employees=None,
                          coverage_is_current_employment=True,
                          part_a_quarters=40, magi=None, irmaa_tiers=None,
                          contributing_to_hsa=False)
    assert a.sep_available is None
    assert any("load-bearing" in f for f in a.findings)
    assert "employer_employees" in a.weakest_input


def test_cobra_does_not_create_a_special_enrolment_period():
    a = H.assess_medicare(current_age=64, working_past_65=False,
                          employer_employees=None,
                          coverage_is_current_employment=False,
                          part_a_quarters=40, magi=None, irmaa_tiers=None,
                          contributing_to_hsa=False)
    assert any("COBRA" in f for f in a.findings)


def test_part_a_quarters_decide_whether_it_is_premium_free():
    assert H.assess_medicare(
        current_age=64, working_past_65=False, employer_employees=None,
        coverage_is_current_employment=None, part_a_quarters=40, magi=None,
        irmaa_tiers=None, contributing_to_hsa=False).part_a_premium_free is True
    assert H.assess_medicare(
        current_age=64, working_past_65=False, employer_employees=None,
        coverage_is_current_employment=None, part_a_quarters=31, magi=None,
        irmaa_tiers=None, contributing_to_hsa=False).part_a_premium_free is False
    assert H.assess_medicare(
        current_age=64, working_past_65=False, employer_employees=None,
        coverage_is_current_employment=None, part_a_quarters=None, magi=None,
        irmaa_tiers=None, contributing_to_hsa=False).part_a_premium_free is None


def test_the_irmaa_year_is_two_before_medicare():
    a = H.assess_medicare(current_age=41, working_past_65=None,
                          employer_employees=None,
                          coverage_is_current_employment=None,
                          part_a_quarters=None, magi=None, irmaa_tiers=None,
                          contributing_to_hsa=False)
    assert a.irmaa_magi_year_age == 63
    assert a.years_away == 24


def test_hsa_deadline_is_raised_only_when_contributing():
    on = H.assess_medicare(current_age=64, working_past_65=True,
                           employer_employees=50,
                           coverage_is_current_employment=True,
                           part_a_quarters=40, magi=None, irmaa_tiers=None,
                           contributing_to_hsa=True)
    off = H.assess_medicare(current_age=64, working_past_65=True,
                            employer_employees=50,
                            coverage_is_current_employment=True,
                            part_a_quarters=40, magi=None, irmaa_tiers=None,
                            contributing_to_hsa=False)
    assert any("6 months before Part A" in f for f in on.findings)
    assert not any("6 months before Part A" in f for f in off.findings)


# ── IRMAA tiers ─────────────────────────────────────────────────────────────

TIERS = [
    H.IrmaaTier(110_000, 70.0, 13.0),
    H.IrmaaTier(140_000, 175.0, 33.0),
    H.IrmaaTier(170_000, 280.0, 54.0),
]


def test_irmaa_position_finds_the_tier_and_the_next_step():
    p = H.irmaa_position(120_000, TIERS)
    assert p.tier_index == 0
    assert p.surcharge_monthly_per_person == pytest.approx(83.0)
    assert p.next_threshold == 140_000
    assert p.headroom == pytest.approx(20_000)
    assert p.step_cost_annual_per_person == pytest.approx((208.0 - 83.0) * 12)


def test_below_the_first_tier_there_is_no_surcharge():
    p = H.irmaa_position(90_000, TIERS)
    assert p.tier_index is None
    assert p.surcharge_monthly_per_person == 0.0
    assert p.headroom == pytest.approx(20_000)


def test_above_the_top_tier_there_is_no_next_step():
    p = H.irmaa_position(500_000, TIERS)
    assert p.tier_index == 2
    assert p.next_threshold is None
    assert p.step_cost_annual_per_person is None


def test_irmaa_refuses_without_supplied_tiers():
    """Tier thresholds are annual CMS figures. A3 says the repo does not grow
    another unverified table to hold them."""
    p = H.irmaa_position(120_000, [])
    assert p.tier_index is None and p.surcharge_monthly_per_person is None


# ── long-term care ──────────────────────────────────────────────────────────


def test_ltc_refuses_without_a_cost_and_says_why():
    a = H.assess_ltc(annual_cost=None, cost_as_of=None,
                     investable_assets=2_000_000,
                     survivor_annual_spending=80_000,
                     has_policy=False, policy_type=None)
    assert a.verdict == "unknown"
    assert any("No care cost recorded" in f for f in a.findings)


def test_ltc_sizes_the_planning_case_and_the_tail():
    a = H.assess_ltc(annual_cost=100_000, cost_as_of="2026-01-01",
                     investable_assets=4_000_000,
                     survivor_annual_spending=80_000,
                     has_policy=False, policy_type=None)
    assert a.planning_cost == 300_000
    assert a.tail_cost == 500_000
    assert a.share_tail == pytest.approx(0.125)


def test_a_small_tail_against_a_large_portfolio_is_self_insured():
    a = H.assess_ltc(annual_cost=100_000, cost_as_of=None,
                     investable_assets=20_000_000,
                     survivor_annual_spending=200_000,
                     has_policy=False, policy_type=None)
    assert a.verdict == H.SELF_INSURE


def test_a_tail_past_the_absorb_line_is_transferred():
    a = H.assess_ltc(annual_cost=120_000, cost_as_of=None,
                     investable_assets=1_500_000,
                     survivor_annual_spending=40_000,
                     has_policy=False, policy_type=None)
    assert a.share_tail >= H.ABSORB_SEVERE
    assert a.verdict == H.TRANSFER


def test_the_survivor_test_overrides_a_comfortable_percentage():
    """The case the skill exists for: the share of assets passes, and the
    surviving spouse's retirement still does not."""
    a = H.assess_ltc(annual_cost=100_000, cost_as_of=None,
                     investable_assets=4_000_000,
                     survivor_annual_spending=150_000,
                     has_policy=False, policy_type=None)
    assert a.share_tail < H.ABSORB_SEVERE          # screen says fine
    assert a.survivor_shortfall > 0                # test says not fine
    assert a.verdict == H.TRANSFER
    assert any("impoverishing the spouse" in f for f in a.findings)


def test_the_survivor_test_can_pass_and_says_it_is_the_stronger_argument():
    a = H.assess_ltc(annual_cost=100_000, cost_as_of=None,
                     investable_assets=4_000_000,
                     survivor_annual_spending=100_000,
                     has_policy=False, policy_type=None)
    assert a.survivor_shortfall == 0
    assert any("survivor test passes" in f for f in a.findings)


def test_the_survivor_test_is_skipped_loudly_when_spending_is_unknown():
    a = H.assess_ltc(annual_cost=100_000, cost_as_of=None,
                     investable_assets=4_000_000,
                     survivor_annual_spending=None,
                     has_policy=False, policy_type=None)
    assert a.survivor_shortfall is None
    assert any("not run" in f for f in a.findings)


def test_the_residual_uses_the_shared_withdrawal_rate_not_a_local_copy():
    a = H.assess_ltc(annual_cost=100_000, cost_as_of=None,
                     investable_assets=4_000_000,
                     survivor_annual_spending=None,
                     has_policy=False, policy_type=None)
    assert a.residual_assets == 3_500_000
    assert a.residual_supportable_spending == pytest.approx(
        3_500_000 * R.DEFAULT_WITHDRAWAL_RATE)


def test_the_absorb_bands_are_the_shared_ones_not_redefined():
    from pf import auto as A
    assert H.ABSORB_SEVERE is A.ABSORB_SEVERE
    assert H.ABSORB_TRIVIAL is A.ABSORB_TRIVIAL


def test_the_premium_increase_history_is_stated_every_time():
    """Not a footnote. The strongest argument against traditional LTC has to
    appear whatever the verdict is."""
    for assets in (1_000_000, 20_000_000):
        a = H.assess_ltc(annual_cost=100_000, cost_as_of=None,
                         investable_assets=assets,
                         survivor_annual_spending=40_000,
                         has_policy=False, policy_type=None)
        assert any("premium on a traditional policy is not" in f
                   for f in a.findings)


def test_medicare_and_medicaid_misconceptions_are_always_corrected():
    a = H.assess_ltc(annual_cost=100_000, cost_as_of=None,
                     investable_assets=4_000_000,
                     survivor_annual_spending=80_000,
                     has_policy=False, policy_type=None)
    text = " ".join(a.findings)
    assert "Medicare does not pay for long-term care" in text
    assert "means-tested" in text


def test_an_existing_policy_is_checked_on_the_three_things_that_matter():
    a = H.assess_ltc(annual_cost=100_000, cost_as_of=None,
                     investable_assets=4_000_000,
                     survivor_annual_spending=80_000,
                     has_policy=True, policy_type="hybrid")
    text = " ".join(a.findings)
    assert "inflation-adjusted" in text
    assert "elimination period" in text
    assert "benefit period" in text


# ── the params helper both runners share ────────────────────────────────────


def test_params_are_built_from_assumptions_by_one_shared_helper():
    """`aca-subsidy-optimization` and `medicare-enrollment-timing` both report
    the same conflict. If they built parameters separately one could quantify
    it and the other refuse, and a household would see the tooling disagree
    with itself."""
    p = H.params_from_assumptions({
        "fpl_base": 15_000, "fpl_per_additional_person": 5_000,
        "aca_benchmark_premium_annual": 24_000, "aca_cliff_applies": True,
        "aca_applicable_pct_schedule": [[1.5, 0.0], [4.0, 0.085]],
        "medicaid_expansion_state": True,
    })
    assert p.computable
    assert p.applicable_pct_schedule == ((1.5, 0.0), (4.0, 0.085))


def test_params_helper_is_safe_on_an_absent_assumptions_block():
    p = H.params_from_assumptions(None)
    assert not p.computable
    assert p.applicable_pct_schedule is None


def test_a_tail_larger_than_the_portfolio_is_flagged_exhausted_not_negative():
    """A negative residual is not a portfolio. Rendering one invites reading a
    total loss as merely a large shortfall."""
    a = H.assess_ltc(annual_cost=110_000, cost_as_of=None,
                     investable_assets=395_000,
                     survivor_annual_spending=72_000,
                     has_policy=False, policy_type=None)
    assert a.exhausted is True
    assert a.residual_assets == 0.0
    assert a.residual_supportable_spending == 0.0
    assert a.survivor_shortfall == 72_000
    assert any("costs more than the entire" in f for f in a.findings)


def test_a_tail_inside_the_portfolio_is_not_flagged_exhausted():
    a = H.assess_ltc(annual_cost=100_000, cost_as_of=None,
                     investable_assets=4_000_000,
                     survivor_annual_spending=80_000,
                     has_policy=False, policy_type=None)
    assert a.exhausted is False
