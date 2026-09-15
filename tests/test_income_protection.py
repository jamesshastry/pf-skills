"""Cluster 2 — survivor needs, life, disability. Synthetic fixtures only."""

import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import disability as D, facts as F, life as L, survivor as S  # noqa: E402

MEMBERS = [
    {"id": "a1", "role": "primary", "age": 41, "income_annual": 180_000},
    {"id": "a2", "role": "spouse", "age": 39, "income_annual": 0},
    {"id": "c1", "role": "dependent", "age": 8},
    {"id": "c2", "role": "dependent", "age": 5},
]
TODAY = dt.date(2026, 8, 30)


# ── present value ───────────────────────────────────────────────────────────


def test_pv_annuity_matches_the_closed_form():
    assert S.pv_annuity(1000, 10, 0.03) == pytest.approx(8530.20, abs=0.5)


def test_pv_annuity_handles_zero_rate():
    assert S.pv_annuity(1000, 10, 0.0) == 10_000


def test_pv_annuity_zero_years_is_zero():
    assert S.pv_annuity(1000, 0, 0.03) == 0


def test_longer_horizon_needs_more_capital():
    assert S.pv_annuity(1000, 40, 0.03) > S.pv_annuity(1000, 20, 0.03)


def test_higher_discount_rate_needs_less_capital():
    assert S.pv_annuity(1000, 30, 0.05) < S.pv_annuity(1000, 30, 0.02)


# ── survivor need ───────────────────────────────────────────────────────────


def test_horizon_runs_from_the_survivor_not_the_insured():
    n = S.compute(insured_id="a1", members=MEMBERS, annual_spending=96_000,
                  assets_available=0)
    assert n.survivor_age == 39
    assert n.horizon_years == S.LIFE_EXPECTANCY_AGE - 39


def test_surviving_income_reduces_the_shortfall():
    earning_spouse = [dict(m, income_annual=60_000) if m["id"] == "a2" else m
                      for m in MEMBERS]
    poor = S.compute(insured_id="a1", members=MEMBERS,
                     annual_spending=96_000, assets_available=0)
    rich = S.compute(insured_id="a1", members=earning_spouse,
                     annual_spending=96_000, assets_available=0)
    assert rich.annual_shortfall == poor.annual_shortfall - 60_000
    assert rich.net_need < poor.net_need


def test_assets_offset_the_need_and_never_go_negative():
    n = S.compute(insured_id="a1", members=MEMBERS, annual_spending=96_000,
                  assets_available=99_000_000)
    assert n.net_need == 0


def test_single_income_household_is_called_out():
    n = S.compute(insured_id="a1", members=MEMBERS, annual_spending=96_000,
                  assets_available=0)
    assert any("single-income" in x for x in n.notes)


def test_missing_education_obligation_is_flagged_not_assumed_zero_silently():
    n = S.compute(insured_id="a1", members=MEMBERS, annual_spending=96_000,
                  assets_available=0)
    assert n.education_obligation == 0
    assert any("education obligation" in x for x in n.notes)


def test_gap_decade_is_named_when_it_exists():
    n = S.compute(insured_id="a1", members=MEMBERS, annual_spending=96_000,
                  assets_available=0)
    assert any("gap decade" in x for x in n.notes)


def test_no_gap_decade_when_survivor_is_already_near_retirement():
    older = [{"id": "a1", "role": "primary", "age": 66, "income_annual": 180_000},
             {"id": "a2", "role": "spouse", "age": 64, "income_annual": 0},
             {"id": "c1", "role": "dependent", "age": 30}]
    n = S.compute(insured_id="a1", members=older, annual_spending=96_000,
                  assets_available=0)
    assert not any("gap decade" in x for x in n.notes)


# ── life ────────────────────────────────────────────────────────────────────

TERM = {"id": "l1", "label": "Term", "type": "term", "insured": "a1",
        "death_benefit": 500_000, "premium_annual": 420,
        "issued": "2021-06-06", "term_expires": "2041-06-06",
        "employer_provided": False}
VUL = {"id": "l2", "label": "VUL", "type": "variable_universal", "insured": "a1",
       "death_benefit": 150_000, "premium_annual": 2_400, "issued": "2016-03-01",
       "term_expires": None, "employer_provided": False,
       "cash_value": 18_500, "premiums_paid_to_date": 25_200}
GROUP = {"id": "l3", "label": "Group", "type": "group", "insured": "a1",
         "death_benefit": 360_000, "premium_annual": 0, "issued": "2020-01-01",
         "employer_provided": True}


def test_group_cover_is_excluded_from_the_gap():
    a = L.assess([TERM, GROUP], need=1_000_000, insured_id="a1", today=TODAY)
    assert a.in_force_portable == 500_000
    assert a.in_force_group == 360_000
    assert a.gap == 500_000  # not 140_000


def test_group_exclusion_is_explained_not_silent():
    a = L.assess([TERM, GROUP], need=1_000_000, insured_id="a1", today=TODAY)
    assert any("job survives" in n for n in a.notes)


def test_gap_never_goes_negative():
    a = L.assess([TERM], need=100_000, insured_id="a1", today=TODAY)
    assert a.gap == 0 and a.covered


def test_cash_value_below_premiums_is_reported_as_a_loss():
    a = L.assess([VUL], need=0, insured_id="a1", today=TODAY)
    p = a.policies[0]
    assert any("below premiums paid" in f for f in p.findings)
    assert p.nominal_return is not None and p.nominal_return < 0


def test_annualised_return_is_computed_generously():
    """Midpoint lump-sum understates the loss. If the generous reading still
    fails, the real one certainly does."""
    generous = L.annualised_return(18_500, 25_200, 10)
    strict = L.annualised_return(18_500, 25_200, 5)  # shorter compounding
    assert generous > strict


def test_annualised_return_guards_bad_inputs():
    assert L.annualised_return(1000, 0, 5) is None
    assert L.annualised_return(1000, 1000, 0) is None


def test_missing_premiums_paid_blocks_the_return_and_says_so():
    p = dict(VUL)
    del p["premiums_paid_to_date"]
    a = L.assess([p], need=0, insured_id="a1", today=TODAY)
    assert a.policies[0].nominal_return is None
    assert any("cannot be computed" in f for f in a.policies[0].findings)


def test_permanent_policy_always_warns_about_1035_and_sequencing():
    a = L.assess([VUL], need=0, insured_id="a1", today=TODAY)
    f = " ".join(a.policies[0].findings)
    assert "1035" in f
    assert "before cancelling" in f


def test_term_expiring_before_dependents_grow_up_is_flagged():
    a = L.assess([TERM], need=0, insured_id="a1",
                 dependents=[{"age": 5}], today=TODAY)
    assert any("expires before the dependents" in n for n in a.notes)


def test_term_outlasting_dependency_is_not_flagged():
    a = L.assess([TERM], need=0, insured_id="a1",
                 dependents=[{"age": 18}], today=TODAY)
    assert not any("expires before the dependents" in n for n in a.notes)


def test_cost_per_thousand_spread_is_surfaced():
    a = L.assess([TERM, VUL], need=0, insured_id="a1", today=TODAY)
    assert any("per dollar of death benefit" in n for n in a.notes)


def test_no_spread_note_when_policies_are_similarly_priced():
    twin = dict(TERM, id="l9", label="Term 2")
    a = L.assess([TERM, twin], need=0, insured_id="a1", today=TODAY)
    assert not any("per dollar of death benefit" in n for n in a.notes)


def test_policies_are_filtered_by_insured():
    other = dict(TERM, id="lx", insured="a2", death_benefit=999_000)
    a = L.assess([TERM, other], need=0, insured_id="a1", today=TODAY)
    assert a.in_force_portable == 500_000


# ── disability ──────────────────────────────────────────────────────────────

INDIV = {"id": "d1", "label": "Individual DI", "insured": "a1",
         "monthly_benefit": 6_500, "premium_annual": 1_150,
         "elimination_days": 90, "benefit_period_years": 10,
         "definition": "modified_own_occupation",
         "riders": ["future_increase", "cola", "partial"],
         "future_increase_deadline": "2029-04-01",
         "employer_provided": False, "premium_paid_with": "after_tax"}
GROUP_LTD = {"id": "d2", "label": "Group LTD", "insured": "a1",
             "monthly_benefit": 6_500, "premium_annual": 0,
             "elimination_days": 180, "benefit_period_years": 10,
             "definition": "any_occupation", "riders": [],
             "employer_provided": True}

DKW = dict(insured_id="a1", insured_age=41, annual_spending=96_000,
           gross_income=180_000, liquid_assets=85_000, reference_date=TODAY)


def test_after_tax_conversion():
    assert D.after_tax_benefit(1000, taxable=False) == 1000
    assert D.after_tax_benefit(1000, taxable=True, rate=0.3) == 700


def test_identical_benefits_are_not_worth_the_same():
    """The whole reason the comparison is done after tax."""
    a = D.assess([INDIV, GROUP_LTD], **DKW)
    indiv, grp = a.policies
    assert indiv.monthly_benefit == grp.monthly_benefit
    assert indiv.monthly_benefit_after_tax > grp.monthly_benefit_after_tax


def test_employer_paid_benefit_is_taxable():
    a = D.assess([GROUP_LTD], **DKW)
    assert a.policies[0].taxable


def test_pre_tax_premium_makes_an_individual_policy_taxable_too():
    p = dict(INDIV, premium_paid_with="pre_tax")
    a = D.assess([p], **DKW)
    assert a.policies[0].taxable


def test_benefit_period_ending_before_retirement_is_flagged():
    a = D.assess([INDIV], **DKW)
    assert any("unfunded" in f for f in a.policies[0].findings)


def test_benefit_period_covering_working_life_is_not_flagged():
    p = dict(INDIV, benefit_period_years=30)
    a = D.assess([p], **DKW)
    assert any("covering working life" in f for f in a.policies[0].findings)


def test_elimination_period_beyond_the_buffer_is_flagged():
    a = D.assess([INDIV], **{**DKW, "liquid_assets": 5_000})
    assert any("arrives too late" in f for f in a.policies[0].findings)


def test_affordable_elimination_period_suggests_lengthening_it():
    a = D.assess([INDIV], **DKW)
    assert any("cheapest way to cut this premium" in f for f in a.policies[0].findings)


def test_future_increase_deadline_becomes_a_dated_finding():
    a = D.assess([INDIV], **DKW)
    d = a.deadlines[0]
    assert d.on == dt.date(2029, 4, 1)
    assert d.days_remaining == (dt.date(2029, 4, 1) - TODAY).days
    assert d.urgency == "distant"


def test_imminent_deadline_is_urgent():
    p = dict(INDIV, future_increase_deadline="2026-10-01")
    a = D.assess([p], **DKW)
    assert a.deadlines[0].urgency == "urgent"


def test_passed_deadline_says_underwriting_is_required_now():
    p = dict(INDIV, future_increase_deadline="2020-01-01")
    a = D.assess([p], **DKW)
    assert a.deadlines[0].passed
    assert any("closed on" in f for f in a.policies[0].findings)


def test_rider_without_a_recorded_deadline_says_go_and_find_it():
    p = dict(INDIV)
    del p["future_increase_deadline"]
    a = D.assess([p], **DKW)
    assert any("no deadline is recorded" in f for f in a.policies[0].findings)


def test_missing_cola_rider_is_flagged():
    p = dict(INDIV, riders=["future_increase"])
    a = D.assess([p], **DKW)
    assert any("cost-of-living" in f for f in a.policies[0].findings)


def test_missing_definition_is_called_the_most_important_term():
    p = dict(INDIV)
    del p["definition"]
    a = D.assess([p], **DKW)
    assert any("most important term" in f for f in a.policies[0].findings)


def test_gap_above_the_insurable_ceiling_says_it_may_not_be_purchasable():
    a = D.assess([INDIV], **{**DKW, "annual_spending": 200_000,
                             "gross_income": 100_000})
    assert any("may not be purchasable" in n for n in a.notes)


# ── deadline primitive ──────────────────────────────────────────────────────


def test_deadline_urgency_bands():
    assert F.deadline("x", "2026-09-01", TODAY).urgency == "urgent"
    assert F.deadline("x", "2027-06-01", TODAY).urgency == "approaching"
    assert F.deadline("x", "2032-01-01", TODAY).urgency == "distant"
    assert F.deadline("x", "2020-01-01", TODAY).urgency == "passed"
    assert F.deadline("x", None, TODAY).urgency == "unknown"
