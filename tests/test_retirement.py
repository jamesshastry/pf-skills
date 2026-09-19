"""Cluster 7 — readiness, drawdown, conversion window, claiming."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import limits as L, retirement as R  # noqa: E402

AGES85 = L.retirement_ages(1985)


# ── statutory ages ──────────────────────────────────────────────────────────


def test_rmd_and_fra_by_birth_year_band():
    assert L.retirement_ages(1985).rmd_age == 75
    assert L.retirement_ages(1985).ss_full == 67
    assert L.retirement_ages(1945).rmd_age == 73
    assert L.retirement_ages(1945).ss_full == 66


def test_the_stepped_fra_band_returns_none_rather_than_a_rounded_guess():
    """1955-1959 steps in months. A plausible rounded number would be
    believed; None forces the user to look it up."""
    r = L.retirement_ages(1957)
    assert r.known and r.rmd_age == 73
    assert r.ss_full is None


def test_unknown_birth_year_is_unknown():
    assert not L.retirement_ages(None).known


def test_retirement_ages_carry_provenance():
    r = L.retirement_ages(1985)
    assert r.source and r.verified_on


# ── projection ──────────────────────────────────────────────────────────────


def test_project_compounds_assets_and_contributions():
    assert R.project(100_000, 0, 0.05, 1) == pytest.approx(105_000)
    assert R.project(0, 10_000, 0.05, 2) == pytest.approx(20_500)


def test_project_handles_zero_return():
    assert R.project(100_000, 10_000, 0.0, 5) == 150_000


def test_project_zero_years_is_the_starting_balance():
    assert R.project(100_000, 10_000, 0.05, 0) == 100_000


def test_expiring_education_obligation_can_change_the_savings_path():
    path = R.savings_path_from_obligations(
        10_000,
        [{"label": "education", "annual_amount": 6_000,
          "start_month": 1, "end_month": 24,
          "basis": "real", "redirect_to_retirement": True}],
        years=4,
    )
    assert path == [10_000, 10_000, 16_000, 16_000]
    variable = R.project(0, 10_000, 0.0, 4, savings_by_year=path)
    flat = R.project(0, 10_000, 0.0, 4)
    assert variable == 52_000
    assert variable > flat


def test_freed_cash_is_not_assumed_saved_without_explicit_redirection():
    path = R.savings_path_from_obligations(
        10_000,
        [{"annual_amount": 6_000, "start_month": 1, "end_month": 12}],
        years=3,
    )
    assert path == [10_000, 10_000, 10_000]


def test_nominal_obligation_is_refused_from_the_real_projection():
    with pytest.raises(ValueError, match="basis: real"):
        R.savings_path_from_obligations(
            10_000,
            [{"annual_amount": 6_000, "start_month": 1, "end_month": 12,
              "basis": "nominal", "redirect_to_retirement": True}],
            years=3,
        )


def test_target_is_spending_over_the_withdrawal_rate():
    assert R.target_for(96_000, 0.04) == 2_400_000
    assert R.target_for(96_000, 0.035) == pytest.approx(2_742_857, abs=1)


def test_lower_withdrawal_rate_means_a_larger_target():
    assert R.target_for(96_000, 0.035) > R.target_for(96_000, 0.045)


def test_years_to_target_is_zero_when_already_there():
    assert R.years_to(100_000, 200_000, 0, 0.05) == 0.0


def test_years_to_target_returns_none_when_unreachable():
    assert R.years_to(10_000_000, 1_000, 0, 0.0) is None


def test_higher_return_reaches_the_target_sooner():
    slow = R.years_to(2_400_000, 423_000, 42_000, 0.03)
    fast = R.years_to(2_400_000, 423_000, 42_000, 0.07)
    assert fast < slow


# ── readiness ───────────────────────────────────────────────────────────────


def test_readiness_reports_an_age_when_one_is_known():
    r = R.assess_readiness(annual_spending=96_000, assets=423_000,
                           annual_savings=42_000, current_age=41)
    assert r.years_to_target == 20
    assert r.age_at_target == 61


def test_already_funded_household_is_told_the_question_changed():
    r = R.assess_readiness(annual_spending=96_000, assets=5_000_000,
                           annual_savings=0, current_age=60)
    assert r.already_there
    assert any("stops being accumulation" in f for f in r.findings)


def test_every_readiness_report_states_it_is_real_and_deterministic():
    r = R.assess_readiness(annual_spending=96_000, assets=423_000,
                           annual_savings=42_000, current_age=41)
    joined = " ".join(r.findings)
    assert "real" in joined
    assert "deterministic projection, not a simulation" in joined
    assert "Monte Carlo" in joined


def test_unreachable_target_says_the_plan_does_not_close():
    r = R.assess_readiness(annual_spending=500_000, assets=1_000,
                           annual_savings=0, current_age=60, real_return=0.0)
    assert r.years_to_target is None
    assert any("does not close" in f for f in r.findings)


# ── sensitivity ─────────────────────────────────────────────────────────────


def test_sensitivity_covers_the_whole_grid():
    grid = R.sensitivity(annual_spending=96_000, assets=423_000,
                         annual_savings=42_000, current_age=41)
    assert len(grid) == len(R.WITHDRAWAL_RATES)
    for row in grid:
        for rr in R.REAL_RETURN_SCENARIOS:
            assert rr in row


def test_the_grid_spans_a_wide_range_of_ages():
    """The spread is the actual answer; if it were narrow the point estimate
    would be defensible, and it is not."""
    grid = R.sensitivity(annual_spending=96_000, assets=423_000,
                         annual_savings=42_000, current_age=41)
    ages = [row[rr]["age"] for row in grid for rr in R.REAL_RETURN_SCENARIOS]
    assert max(ages) - min(ages) >= 10


# ── drawdown ────────────────────────────────────────────────────────────────


def test_default_sequence_is_taxable_deferred_roth():
    d = R.drawdown_guidance(current_age=60, ages=AGES85, has_taxable=True,
                            has_tax_deferred=True, has_roth=True)
    assert [k for k, _, _ in d.sequence] == ["taxable", "tax_deferred", "roth"]


def test_strict_sequencing_is_immediately_qualified():
    d = R.drawdown_guidance(current_age=60, ages=AGES85, has_taxable=True,
                            has_tax_deferred=True, has_roth=True)
    assert any("starting point, not the answer" in f for f in d.findings)


def test_no_roth_balance_points_at_the_conversion_window():
    d = R.drawdown_guidance(current_age=60, ages=AGES85, has_taxable=True,
                            has_tax_deferred=True, has_roth=False)
    assert any("roth-conversion-window" in f for f in d.findings)


def test_early_retirement_triggers_the_access_warning():
    d = R.drawdown_guidance(current_age=52, ages=AGES85, has_taxable=True,
                            has_tax_deferred=True, has_roth=True)
    joined = " ".join(d.findings)
    assert "Rule of 55" in joined
    # Rolling to an IRA loses it — the irreversible part.
    assert "irreversible mistake" in joined
    assert "72(t)" in joined


def test_late_retirement_does_not_warn_about_early_access():
    d = R.drawdown_guidance(current_age=62, ages=AGES85, has_taxable=True,
                            has_tax_deferred=True, has_roth=True)
    assert not any("needs an access plan" in f for f in d.findings)


def test_unknown_birth_year_says_ages_cannot_be_resolved():
    d = R.drawdown_guidance(current_age=60, ages=L.retirement_ages(None),
                            has_taxable=True, has_tax_deferred=True, has_roth=True)
    assert any("cannot be resolved" in f for f in d.findings)


# ── conversion window ───────────────────────────────────────────────────────


def test_window_closes_at_the_earlier_of_rmd_and_claiming():
    w = R.conversion_window(retirement_age=60, ages=AGES85)
    assert w.closes_age == 70   # ss_latest, earlier than RMD at 75
    assert w.years == 10


def test_an_earlier_claim_shortens_the_window():
    w = R.conversion_window(retirement_age=60, ages=AGES85, claim_age=65)
    assert w.closes_age == 65 and w.years == 5


def test_no_window_when_retiring_after_it_would_close():
    w = R.conversion_window(retirement_age=72, ages=AGES85)
    assert not w.exists
    assert any("No window" in f for f in w.findings)


def test_window_always_warns_about_irmaa_and_paying_tax_from_outside():
    w = R.conversion_window(retirement_age=60, ages=AGES85)
    joined = " ".join(w.findings)
    assert "IRMAA" in joined
    assert "never from the converted amount" in joined


def test_window_needs_both_inputs():
    assert not R.conversion_window(retirement_age=None, ages=AGES85).exists


# ── social security ─────────────────────────────────────────────────────────


def test_claiming_multipliers_match_the_statutory_schedule():
    assert R.benefit_multiplier(67, 67) == 1.0
    assert R.benefit_multiplier(62, 67) == pytest.approx(0.70, abs=0.005)
    assert R.benefit_multiplier(70, 67) == pytest.approx(1.24, abs=0.005)


def test_delayed_credits_stop_at_seventy():
    assert R.benefit_multiplier(72, 67) == R.benefit_multiplier(70, 67)


def test_claiming_table_covers_earliest_to_latest():
    t = R.claiming_table(AGES85)
    assert t[0]["age"] == 62 and t[-1]["age"] == 70


def test_claiming_table_is_empty_when_fra_is_unresolved():
    assert R.claiming_table(L.retirement_ages(1957)) == []


def test_single_earner_household_gets_the_survivor_argument():
    g = R.claiming_guidance(ages=AGES85, single_earner_household=True)
    joined = " ".join(g)
    assert "survivor decision" in joined
    assert "of the two benefits, not both" in joined
    assert "no benefit record of their own" in joined


def test_dual_earner_household_does_not_get_it():
    g = R.claiming_guidance(ages=AGES85, single_earner_household=False)
    assert not any("survivor decision" in x for x in g)


def test_guidance_always_reframes_away_from_break_even():
    g = R.claiming_guidance(ages=AGES85, single_earner_household=False)
    assert any("longevity insurance" in x for x in g)


def test_unresolved_fra_refuses_to_approximate():
    g = R.claiming_guidance(ages=L.retirement_ages(1957),
                            single_earner_household=False)
    assert any("deliberately does not approximate" in x for x in g)
