"""Cluster 9 — education funding. Synthetic fixtures only."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import education as E  # noqa: E402

MEMBERS = [{"id": "a1", "role": "primary", "age": 41},
           {"id": "c1", "role": "dependent", "age": 8},
           {"id": "c2", "role": "dependent", "age": 5},
           {"id": "c3", "role": "dependent", "age": 19}]
KIDS = [{"member": "c1", "annual_cost_today": 28_000},
        {"member": "c2", "annual_cost_today": 28_000}]


# ── the ordering rule ───────────────────────────────────────────────────────


def test_the_ordering_rule_leads_with_the_asymmetry():
    out = E.ordering_rule(retirement_on_track=True, retirement_age_at_target=61)
    assert "borrow for education" in out[0]
    assert "cannot borrow for retirement" in out[0]


def test_retirement_off_track_forbids_diverting_savings():
    out = E.ordering_rule(retirement_on_track=False, retirement_age_at_target=None)
    joined = " ".join(out)
    assert "not on track" in joined
    assert "not by diverting retirement savings" in joined


def test_unknown_retirement_status_says_run_that_first():
    out = E.ordering_rule(retirement_on_track=None, retirement_age_at_target=None)
    assert any("retirement-readiness" in x for x in out)


# ── cost projection ─────────────────────────────────────────────────────────


def test_each_year_of_study_is_inflated_separately():
    """Inflating the whole bill to the start date understates it: year four
    carries three more years of inflation than year one."""
    naive = 28_000 * 4 * (1.05 ** 10)
    actual = E.project_cost(28_000, 10, 4, 0.05)
    assert actual > naive


def test_cost_grows_with_the_horizon():
    near = E.project_cost(28_000, 2, 4, 0.05)
    far = E.project_cost(28_000, 15, 4, 0.05)
    assert far > near


def test_zero_inflation_is_a_plain_multiple():
    assert E.project_cost(10_000, 5, 4, 0.0) == 40_000


def test_more_years_of_study_costs_more():
    assert E.project_cost(28_000, 10, 5, 0.05) > E.project_cost(28_000, 10, 4, 0.05)


# ── allocation ──────────────────────────────────────────────────────────────


def test_an_account_with_a_beneficiary_is_allocated_to_that_child():
    p = E.plan_for(KIDS, members=MEMBERS,
                   accounts=[{"value": 30_000, "beneficiary": "c1"}])
    c1 = next(c for c in p.children if c.member_id == "c1")
    c2 = next(c for c in p.children if c.member_id == "c2")
    assert c1.allocated_savings == 30_000
    assert c2.allocated_savings == 0
    assert p.unallocated_savings == 0


def test_a_pooled_account_is_not_split_between_children():
    """Splitting would invent an allocation nobody made. A 529 names exactly
    one beneficiary."""
    p = E.plan_for(KIDS, members=MEMBERS, accounts=[{"value": 28_000}])
    assert p.unallocated_savings == 28_000
    assert all(c.allocated_savings == 0 for c in p.children)
    assert any("exactly one beneficiary" in f for f in p.findings)


def test_the_pooled_note_counts_the_children_with_no_account():
    p = E.plan_for(KIDS, members=MEMBERS,
                   accounts=[{"value": 10_000, "beneficiary": "c1"},
                             {"value": 5_000}])
    assert p.unallocated_savings == 5_000
    assert any("1 child(ren) have no account" in f for f in p.findings)


def test_no_pooled_note_when_everything_is_allocated():
    p = E.plan_for(KIDS, members=MEMBERS,
                   accounts=[{"value": 10_000, "beneficiary": "c1"},
                             {"value": 10_000, "beneficiary": "c2"}])
    assert p.findings == []


# ── timetable ───────────────────────────────────────────────────────────────


def test_a_child_near_enrolment_gets_a_glide_path_warning():
    kids = [{"member": "c3", "annual_cost_today": 28_000, "start_age": 20}]
    p = E.plan_for(kids, members=MEMBERS, accounts=[])
    assert any("glide path" in f for f in p.children[0].findings)


def test_a_child_already_enrolled_is_a_cash_flow_question():
    kids = [{"member": "c3", "annual_cost_today": 28_000, "start_age": 18}]
    p = E.plan_for(kids, members=MEMBERS, accounts=[])
    c = p.children[0]
    assert c.years_until_start == 0
    assert any("cash-flow question now" in f for f in c.findings)


def test_a_distant_child_gets_no_glide_warning():
    p = E.plan_for(KIDS, members=MEMBERS, accounts=[])
    assert not any("glide path" in f for f in p.children[1].findings)


def test_a_child_with_no_age_cannot_be_scheduled():
    members = MEMBERS + [{"id": "c9", "role": "dependent"}]
    p = E.plan_for([{"member": "c9", "annual_cost_today": 28_000}],
                   members=members, accounts=[])
    c = p.children[0]
    assert c.years_until_start is None
    assert any("timetable cannot be computed" in f for f in c.findings)


# ── the gap ─────────────────────────────────────────────────────────────────


def test_savings_grow_to_the_start_date_before_being_netted_off():
    p = E.plan_for([{"member": "c1", "annual_cost_today": 28_000}],
                   members=MEMBERS,
                   accounts=[{"value": 50_000, "beneficiary": "c1"}],
                   real_return=0.03)
    c = p.children[0]
    assert c.projected_savings == pytest.approx(50_000 * 1.03 ** 10)
    assert c.gap == pytest.approx(c.projected_cost - c.projected_savings)


def test_overfunding_shows_a_negative_gap_and_is_excluded_from_the_total():
    p = E.plan_for([{"member": "c1", "annual_cost_today": 1_000}],
                   members=MEMBERS,
                   accounts=[{"value": 500_000, "beneficiary": "c1"}])
    assert p.children[0].gap < 0
    assert p.total_gap == 0


def test_funded_share_is_reported():
    p = E.plan_for([{"member": "c1", "annual_cost_today": 28_000}],
                   members=MEMBERS,
                   accounts=[{"value": 50_000, "beneficiary": "c1"}])
    assert 0 < p.children[0].funded_share < 1


# ── state treatment ─────────────────────────────────────────────────────────


def test_california_taxes_income_and_gives_no_deduction():
    sb = E.state_benefit("CA")
    assert sb.known and sb.has_income_tax and not sb.deduction_available
    assert "no tax advantage" in sb.note


def test_a_no_income_tax_state_cannot_have_a_deduction():
    sb = E.state_benefit("TX")
    assert sb.known and not sb.has_income_tax and not sb.deduction_available


def test_an_unknown_state_says_so_rather_than_assuming():
    sb = E.state_benefit("ZZ")
    assert not sb.known
    notes = E.mechanics_notes(state="ZZ", has_leftover_risk=False)
    assert any("not in the table" in n for n in notes)


def test_every_known_state_carries_provenance():
    for code in E.states_available():
        sb = E.state_benefit(code)
        assert sb.source and sb.verified_on


# ── mechanics ───────────────────────────────────────────────────────────────


def test_aid_treatment_warns_against_moving_money_to_the_student():
    notes = E.mechanics_notes(state="CA", has_leftover_risk=False)
    joined = " ".join(notes)
    assert "5.64%" in joined and "20%" in joined
    assert "lost aid" in joined


def test_the_roth_rollover_is_described_with_all_its_limits():
    notes = E.mechanics_notes(state="CA", has_leftover_risk=True)
    joined = " ".join(notes)
    assert "$35,000" in joined
    assert "15 years" in joined
    assert "not a reason to overfund" in joined


def test_no_leftover_risk_skips_the_rollover_note():
    notes = E.mechanics_notes(state="CA", has_leftover_risk=False)
    assert not any("SECURE 2.0" in n for n in notes)


def test_superfunding_is_always_mentioned():
    notes = E.mechanics_notes(state="CA", has_leftover_risk=False)
    assert any("Superfunding" in n for n in notes)
