"""Cluster 18 — investment property. Synthetic only.

Three things are worth testing hard here, and they are the three the brief
says people get wrong: NOI excluding debt service and capex, the §469 gate
opening only through a door that actually exists, and depreciation recapture
being counted in the exchange gain.
"""

import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import realestate as R  # noqa: E402

# A W-2 household: too much MAGI for the allowance, a day job that defeats the
# REPS majority test.
PARTICIPATION = dict(
    magi=212_000,
    active_participation=True,
    hours_real_property=260,
    hours_all_work=2_340,
    allowance=25_000,
    phaseout_start=100_000,
    phaseout_end=150_000,
)

LONG_TERM = {
    "label": "Cedar Park duplex",
    "avg_stay_days": 365,
    "material_participation_hours": 120,
    "most_hours_of_anyone": True,
    "expected_loss": 22_000,
    "suspended_losses": 14_000,
}

SHORT_STAY = {
    "label": "Gulf Coast cabin",
    "avg_stay_days": 4,
    "material_participation_hours": 180,
    "most_hours_of_anyone": True,
    "expected_loss": 31_000,
    "suspended_losses": 0,
}

DEAL = {
    "label": "Cedar Park duplex",
    "price": 420_000,
    "closing_costs": 9_000,
    "down_payment": 147_000,
    "loan_rate": 0.0685,
    "loan_term_years": 30,
    "gross_rent_monthly": 4_000,
    "vacancy_rate": 0.06,
    "credit_loss_rate": 0.01,
    "capex_reserve_rate": 0.05,
    "operating_expenses": {
        "property_tax": 7_800,
        "insurance": 2_400,
        "management": 3_100,
        "maintenance": 2_600,
    },
    "hold_years": 7,
    "rent_growth": 0.03,
    "expense_growth": 0.035,
    "appreciation": 0.03,
    "selling_cost_rate": 0.07,
}

EXCHANGE = {
    "sale_price": 640_000,
    "selling_costs": 44_800,
    "purchase_price": 385_000,
    "improvements": 22_000,
    "accumulated_depreciation": 96_000,
    "relinquished_debt": 210_000,
    "replacement_value": 720_000,
    "replacement_debt": 300_000,
    "sale_date": dt.date(2026, 8, 3),
    "deferral_years": 12,
}

RATES = dict(
    recapture_rate=0.25,
    ltcg_rate=0.15,
    niit_rate=0.038,
    state_rate=0.0,
)


# ── the $25,000 allowance ───────────────────────────────────────────────────


def test_allowance_is_whole_below_the_floor():
    assert R.allowance_available(
        90_000, allowance=25_000, phaseout_start=100_000, phaseout_end=150_000
    ) == 25_000


def test_allowance_halves_at_the_midpoint_of_the_band():
    """50 cents per dollar is what makes a $50k band consume a $25k allowance."""
    assert R.allowance_available(
        125_000, allowance=25_000, phaseout_start=100_000, phaseout_end=150_000
    ) == pytest.approx(12_500)


def test_allowance_is_gone_at_the_ceiling():
    assert R.allowance_available(
        150_000, allowance=25_000, phaseout_start=100_000, phaseout_end=150_000
    ) == 0.0


def test_allowance_refuses_rather_than_guessing_the_statutory_figures():
    """REVIEW.md A3 — this library does not carry its own tax-code mirror."""
    assert R.allowance_available(
        90_000, allowance=None, phaseout_start=100_000, phaseout_end=150_000
    ) is None


def test_missing_allowance_figures_are_reported_as_unresolved_not_closed():
    g = R.assess_gate(
        [LONG_TERM],
        magi=212_000,
        active_participation=True,
        hours_real_property=260,
        hours_all_work=2_340,
    )
    assert g.allowance is None
    assert any("cannot be evaluated" in f for f in g.findings)
    assert any("not as closed" in f for f in g.findings)


# ── the gate ────────────────────────────────────────────────────────────────


def test_long_term_rental_for_a_w2_earner_finds_no_open_door():
    g = R.assess_gate([LONG_TERM], **PARTICIPATION)
    a = g.activities[0]
    assert a.door is None
    assert not g.any_open
    assert a.deductible_against_wages == 0.0


def test_the_short_stay_exception_opens_the_gate_without_reps():
    g = R.assess_gate([SHORT_STAY], **PARTICIPATION)
    a = g.activities[0]
    assert a.is_rental_activity is False
    assert a.door == "short_stay"
    assert g.reps is False  # explicitly NOT via REPS
    assert a.deductible_against_wages == 31_000


def test_seven_days_is_inside_the_exception_and_eight_is_not():
    inside = R.assess_gate(
        [dict(SHORT_STAY, avg_stay_days=7.0)], **PARTICIPATION
    ).activities[0]
    outside = R.assess_gate(
        [dict(SHORT_STAY, avg_stay_days=7.1)], **PARTICIPATION
    ).activities[0]
    assert inside.door == "short_stay"
    assert outside.door is None


def test_short_stay_without_material_participation_stays_shut():
    """Non-rental is only half of it — the loss is still passive without
    material participation."""
    a = R.assess_gate(
        [dict(SHORT_STAY, material_participation_hours=60)], **PARTICIPATION
    ).activities[0]
    assert a.is_rental_activity is False
    assert a.door is None


def test_hundred_hours_needs_more_than_anyone_else_and_unknown_is_not_yes():
    a = R.assess_gate(
        [dict(SHORT_STAY, most_hours_of_anyone=None)], **PARTICIPATION
    ).activities[0]
    assert a.materially_participates is None
    assert a.door is None
    assert any("cleaner" in f for f in a.findings)


def test_five_hundred_hours_needs_no_comparison():
    a = R.assess_gate(
        [dict(SHORT_STAY, material_participation_hours=520,
              most_hours_of_anyone=False)],
        **PARTICIPATION,
    ).activities[0]
    assert a.materially_participates is True
    assert a.door == "short_stay"


def test_reps_fails_on_the_majority_test_not_the_hours():
    g = R.assess_gate(
        [LONG_TERM],
        **dict(PARTICIPATION, hours_real_property=900, hours_all_work=2_340),
    )
    assert g.reps_hours_met is True
    assert g.reps_majority_met is False
    assert g.reps is False
    assert any("more than 50%" in f or "not more than 50%" in f for f in g.findings)


def test_reps_opens_a_long_term_rental_when_both_tests_pass():
    g = R.assess_gate(
        [dict(LONG_TERM, material_participation_hours=600)],
        **dict(PARTICIPATION, hours_real_property=1_400, hours_all_work=2_000),
    )
    assert g.reps is True
    assert g.activities[0].door == "reps"


def test_reps_is_unresolved_rather_than_false_when_hours_are_missing():
    g = R.assess_gate(
        [LONG_TERM],
        **dict(PARTICIPATION, hours_real_property=None, hours_all_work=None),
    )
    assert g.reps is None
    assert any("unresolved" in f for f in g.findings)


def test_the_allowance_is_a_household_cap_not_a_per_property_one():
    g = R.assess_gate(
        [dict(LONG_TERM, expected_loss=20_000),
         dict(LONG_TERM, label="second", expected_loss=20_000)],
        **dict(PARTICIPATION, magi=100_000),
    )
    assert sum(a.deductible_against_wages for a in g.activities) == 25_000


def test_the_allowance_does_not_release_the_carryforward():
    g = R.assess_gate([LONG_TERM], **dict(PARTICIPATION, magi=100_000))
    a = g.activities[0]
    assert a.deductible_against_wages == 22_000
    assert a.suspended_carryforward == 14_000  # untouched


def test_a_disallowed_loss_suspends_rather_than_vanishing():
    g = R.assess_gate([LONG_TERM], **PARTICIPATION)
    a = g.activities[0]
    assert a.suspended_this_year == 22_000
    assert g.total_suspended == 36_000
    assert any("disposition" in f for f in a.findings)


def test_multiple_activities_without_grouping_are_flagged():
    g = R.assess_gate([LONG_TERM, SHORT_STAY], **PARTICIPATION)
    assert any("grouping election" in f for f in g.findings)


def test_grouping_election_warns_about_the_disposition_consequence():
    g = R.assess_gate(
        [LONG_TERM, SHORT_STAY], **dict(PARTICIPATION, grouping_election=True)
    )
    assert any("entire grouped activity" in f for f in g.findings)


def test_a_shut_gate_says_the_marginal_benefit_is_zero_this_year():
    g = R.assess_gate([LONG_TERM], **PARTICIPATION)
    assert any("zero this year" in f for f in g.findings)


# ── NOI, and what it excludes ───────────────────────────────────────────────


def test_noi_is_collected_income_less_operating_expenses():
    noi = R.net_operating_income(
        gross_rent=100_000, vacancy_rate=0.05, credit_loss_rate=0.0,
        operating_expenses=30_000,
    )
    assert noi == pytest.approx(65_000)


def test_noi_excludes_debt_service_so_cap_rate_compares_properties():
    """The classic error. Financing must not move NOI."""
    a = R.underwrite(DEAL)
    b = R.underwrite(dict(DEAL, down_payment=420_000, loan_rate=0.0))
    assert a.noi_year1 == pytest.approx(b.noi_year1)
    assert a.cap_rate == pytest.approx(b.cap_rate)
    assert a.annual_debt_service > 0
    assert b.annual_debt_service == 0


def test_noi_excludes_capex_but_cash_flow_includes_it():
    u = R.underwrite(DEAL)
    y1 = u.years[0]
    assert y1.capex == pytest.approx(4_000 * 12 * 0.05)
    assert y1.cash_flow == pytest.approx(y1.noi - y1.debt_service - y1.capex)


def test_a_missing_vacancy_rate_is_assumed_and_said_rather_than_zeroed():
    d = dict(DEAL)
    d.pop("vacancy_rate")
    u = R.underwrite(d)
    assert any("assumed" in f and "vacancy" in f.lower() for f in u.findings)
    assert u.noi_year1 < R.underwrite(dict(DEAL, vacancy_rate=0.0)).noi_year1


def test_no_operating_expenses_recorded_is_a_loud_finding():
    d = dict(DEAL)
    d.pop("operating_expenses")
    u = R.underwrite(d)
    assert any("upper bound" in f for f in u.findings)


# ── DSCR, both sides of the floor ───────────────────────────────────────────


def test_dscr_is_noi_over_debt_service():
    u = R.underwrite(DEAL)
    assert u.dscr == pytest.approx(u.noi_year1 / u.annual_debt_service)


def test_a_thin_deal_fails_the_lender_floor_and_says_so():
    thin = dict(DEAL, down_payment=42_000, gross_rent_monthly=2_600)
    u = R.underwrite(thin)
    assert u.dscr < R.DSCR_LENDER_FLOOR
    assert u.financeable is False
    assert any("below the 1.20 lender floor" in f for f in u.findings)


def test_a_well_capitalised_deal_clears_the_comfort_level():
    strong = dict(DEAL, down_payment=210_000, gross_rent_monthly=4_200)
    u = R.underwrite(strong)
    assert u.dscr >= R.DSCR_COMFORT
    assert u.financeable is True


def test_the_band_between_floor_and_comfort_is_called_out_separately():
    u = R.underwrite(dict(DEAL, down_payment=138_000, gross_rent_monthly=3_850))
    assert R.DSCR_LENDER_FLOOR <= u.dscr < R.DSCR_COMFORT
    assert any("one bad quarter" in f for f in u.findings)


# ── return metrics ──────────────────────────────────────────────────────────


def test_cash_on_cash_uses_cash_invested_including_closing_costs():
    u = R.underwrite(DEAL)
    assert u.cash_invested == 147_000 + 9_000
    assert u.cash_on_cash == pytest.approx(u.years[0].cash_flow / u.cash_invested)


def test_irr_recovers_a_known_rate():
    assert R.irr([-1_000, 0, 0, 1_331]) == pytest.approx(0.10, abs=1e-4)


def test_irr_is_none_when_nothing_ever_comes_back():
    assert R.irr([-1_000, -100, -100]) is None


def test_equity_multiple_and_irr_agree_on_direction():
    u = R.underwrite(DEAL)
    assert (u.equity_multiple > 1.0) == (u.irr > 0)


def test_leverage_lifts_irr_when_the_deal_works():
    levered = R.underwrite(DEAL)
    cash = R.underwrite(dict(DEAL, down_payment=420_000, loan_rate=0.0))
    assert levered.irr > cash.irr


def test_the_appreciation_assumption_is_named_as_the_weakest_input():
    u = R.underwrite(DEAL)
    assert any("Weakest input" in f for f in u.findings)


def test_a_thin_cap_rate_is_relabelled_as_an_appreciation_bet():
    u = R.underwrite(dict(DEAL, gross_rent_monthly=2_300))
    assert u.cap_rate < R.THIN_CAP_RATE
    assert any("coming from appreciation" in f for f in u.findings)


# ── 1031: recapture is the part people forget ───────────────────────────────


def test_gain_is_computed_against_basis_reduced_by_depreciation():
    r = R.model_exchange(EXCHANGE, **RATES)
    assert r.adjusted_basis == 385_000 + 22_000 - 96_000
    assert r.amount_realized == 640_000 - 44_800
    assert r.total_gain == pytest.approx(595_200 - 311_000)


def test_depreciation_recapture_is_split_out_and_taxed_higher():
    r = R.model_exchange(EXCHANGE, **RATES)
    assert r.unrecaptured_1250 == 96_000
    assert r.capital_gain == pytest.approx(r.total_gain - 96_000)
    assert RATES["recapture_rate"] > RATES["ltcg_rate"]


def test_ignoring_recapture_would_understate_the_tax():
    r = R.model_exchange(EXCHANGE, **RATES)
    naive = r.total_gain * (RATES["ltcg_rate"] + RATES["niit_rate"])
    assert r.tax_if_sold > naive


def test_no_tax_figure_is_reported_without_the_rates():
    r = R.model_exchange(EXCHANGE)
    assert r.tax_if_sold is None
    assert r.total_gain > 0  # the structure still stands
    assert any("No tax figure is reported" in f for f in r.findings)


def test_equal_or_greater_value_with_all_equity_reinvested_defers_fully():
    r = R.model_exchange(EXCHANGE, **RATES)
    assert r.cash_boot == 0
    assert r.debt_boot == 0
    assert r.recognized_gain == 0
    assert r.fully_deferred
    assert r.tax_if_exchanged == 0


def test_cash_taken_out_is_cash_boot():
    r = R.model_exchange(
        dict(EXCHANGE, replacement_value=600_000, replacement_debt=300_000),
        **RATES,
    )
    assert r.cash_boot == pytest.approx(385_200 - 300_000)
    assert not r.fully_deferred


def test_mortgage_boot_arises_from_lower_replacement_debt_alone():
    """The subtle one: same value, less debt, no cash out — still taxable."""
    r = R.model_exchange(
        dict(EXCHANGE, replacement_value=640_000, replacement_debt=100_000),
        **RATES,
    )
    assert r.cash_boot == 0
    assert r.debt_boot == 0  # offset by the extra cash going in
    r2 = R.model_exchange(
        dict(EXCHANGE, replacement_value=385_200, replacement_debt=0),
        **RATES,
    )
    assert r2.cash_boot == 0
    assert r2.debt_boot == pytest.approx(210_000)
    assert r2.recognized_gain == pytest.approx(210_000)


def test_recognized_gain_is_capped_at_the_realized_gain():
    r = R.model_exchange(
        dict(EXCHANGE, accumulated_depreciation=0, purchase_price=550_000,
             replacement_value=200_000, replacement_debt=0),
        **RATES,
    )
    assert r.total_gain == pytest.approx(23_200)
    assert r.cash_boot > r.total_gain          # boot exceeds the gain
    assert r.recognized_gain == pytest.approx(r.total_gain)


def test_recognized_gain_is_taxed_as_recapture_first():
    r = R.model_exchange(
        dict(EXCHANGE, replacement_value=385_200, replacement_debt=0), **RATES
    )
    # 210k of boot, all inside the 96k recapture layer plus LTCG above it
    expected = (
        96_000 * 0.25 + (210_000 - 96_000) * 0.15 + 210_000 * 0.038
    )
    assert r.tax_if_exchanged == pytest.approx(expected)


def test_the_clocks_are_dated_from_the_sale_and_counted_from_as_of():
    r = R.model_exchange(EXCHANGE, as_of=dt.date(2026, 8, 30), **RATES)
    assert r.identify_by == dt.date(2026, 9, 17)
    assert r.close_by == dt.date(2027, 1, 30)
    assert r.days_to_identify == 18
    assert r.days_to_close == 153


def test_an_earlier_return_due_date_truncates_the_180_days():
    r = R.model_exchange(
        dict(EXCHANGE, tax_return_due=dt.date(2027, 4, 15)), **RATES
    )
    assert r.close_by == dt.date(2027, 1, 30)
    r2 = R.model_exchange(
        dict(EXCHANGE, sale_date=dt.date(2026, 11, 20),
             tax_return_due=dt.date(2027, 4, 15)),
        **RATES,
    )
    assert r2.close_by == dt.date(2027, 4, 15)  # 180 days would be 19 May


def test_a_passed_identification_window_is_called_a_taxable_sale():
    r = R.model_exchange(EXCHANGE, as_of=dt.date(2026, 10, 1), **RATES)
    assert r.days_to_identify < 0
    assert any("has failed" in f for f in r.findings)


def test_constructive_receipt_and_the_qi_are_always_stated():
    r = R.model_exchange(EXCHANGE, **RATES)
    assert any("constructive receipt" in f.lower() for f in r.findings)
    assert any("DST" in f for f in r.findings)


def test_the_value_of_deferral_is_present_valued_not_quoted_gross():
    r = R.model_exchange(EXCHANGE, discount_rate=0.07, **RATES)
    pv_line = [f for f in r.findings if "present" in f]
    assert pv_line
    assert r.tax_deferred == r.tax_if_sold


# ── cost segregation screen ─────────────────────────────────────────────────


PROPERTY = {
    "label": "Cedar Park duplex",
    "depreciable_basis": 340_000,
    "property_type": "residential",
    "study_cost": 6_500,
    "hold_years": 10,
}


def test_the_screen_reports_a_range_not_a_point_estimate():
    s = R.screen_cost_segregation(
        PROPERTY, gate_open=True, marginal_rate=0.32, bonus_rate=0.40,
        discount_rate=0.07,
    )
    assert s.reclass_low == pytest.approx(340_000 * R.RECLASS_SHARE_LOW)
    assert s.reclass_high == pytest.approx(340_000 * R.RECLASS_SHARE_HIGH)
    assert s.reclass_high > s.reclass_low
    assert any("is** the study" in f or "is the study" in f for f in s.findings)


def test_no_benefit_is_reported_without_the_legislated_bonus_percentage():
    s = R.screen_cost_segregation(
        PROPERTY, gate_open=True, marginal_rate=0.32, bonus_rate=None,
        discount_rate=0.07,
    )
    assert s.tax_benefit_low is None
    assert any("No benefit figure is reported" in f for f in s.findings)


def test_a_shut_gate_makes_the_benefit_zero_and_the_answer_no():
    s = R.screen_cost_segregation(
        PROPERTY, gate_open=False, marginal_rate=0.32, bonus_rate=0.40,
        discount_rate=0.07,
    )
    assert s.pv_benefit_high == 0.0
    assert s.worth_commissioning is False
    assert any("worth nothing" in f for f in s.findings)


def test_acceleration_is_net_of_the_depreciation_that_would_have_happened():
    s = R.screen_cost_segregation(
        PROPERTY, gate_open=True, marginal_rate=0.32, bonus_rate=0.40,
        discount_rate=0.07,
    )
    low = 340_000 * R.RECLASS_SHARE_LOW
    assert s.accelerated_deduction_low == pytest.approx(
        low * 0.40 - low / R.RESIDENTIAL_RECOVERY_YEARS
    )


def test_commercial_property_uses_the_39_year_period():
    s = R.screen_cost_segregation(
        dict(PROPERTY, property_type="commercial"), gate_open=True,
        marginal_rate=0.32, bonus_rate=0.40, discount_rate=0.07,
    )
    assert s.recovery_years == R.COMMERCIAL_RECOVERY_YEARS


def test_the_benefit_is_present_valued_as_timing_not_permanent():
    s = R.screen_cost_segregation(
        PROPERTY, gate_open=True, marginal_rate=0.32, bonus_rate=0.40,
        discount_rate=0.07,
    )
    assert s.pv_benefit_low < s.tax_benefit_low
    assert any("timing" in f for f in s.findings)


def test_a_tiny_basis_does_not_justify_a_study():
    s = R.screen_cost_segregation(
        dict(PROPERTY, depreciable_basis=90_000), gate_open=True,
        marginal_rate=0.32, bonus_rate=0.40, discount_rate=0.07,
    )
    assert s.benefit_to_cost < R.MIN_BENEFIT_TO_COST
    assert s.worth_commissioning is False


def test_a_large_basis_clears_the_bar():
    s = R.screen_cost_segregation(
        dict(PROPERTY, depreciable_basis=1_800_000), gate_open=True,
        marginal_rate=0.37, bonus_rate=0.60, discount_rate=0.07,
    )
    assert s.benefit_to_cost >= R.MIN_BENEFIT_TO_COST
    assert s.worth_commissioning is True


def test_section_1245_recapture_is_always_flagged():
    s = R.screen_cost_segregation(
        PROPERTY, gate_open=True, marginal_rate=0.32, bonus_rate=0.40,
        discount_rate=0.07,
    )
    assert any("§1245" in f for f in s.findings)


def test_an_unresolved_gate_is_conditional_not_assumed_open():
    s = R.screen_cost_segregation(
        PROPERTY, gate_open=None, marginal_rate=0.32, bonus_rate=0.40,
        discount_rate=0.07,
    )
    assert any("unresolved" in f for f in s.findings)
