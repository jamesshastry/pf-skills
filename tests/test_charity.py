"""Charitable giving — in-kind versus cash, bunching, AGI limits, QCDs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import charity as C  # noqa: E402


def lot(**kw):
    base = {"name": "META", "value": 50_000, "basis": 10_000, "held_days": 900}
    base.update(kw)
    return base


def by_name(r):
    return {l.name: l for l in r.lines}


# ── the lead finding: two problems, one transaction ─────────────────────────


def test_an_appreciated_long_term_lot_is_given_in_kind():
    r = C.review_gifts([lot()], ltcg_rate=0.15)
    line = by_name(r)["META"]
    assert "give in kind" in line.recommendation
    assert line.deductible == 50_000


def test_the_avoided_gain_is_valued_at_the_supplied_rate_plus_niit():
    r = C.review_gifts([lot()], ltcg_rate=0.20, niit_rate=0.038)
    assert round(by_name(r)["META"].gain_tax_avoided, 2) == round(40_000 * 0.238, 2)


def test_the_deduction_is_the_same_either_way_so_the_avoided_gain_is_pure_gain():
    r = C.review_gifts([lot()], ltcg_rate=0.15)
    assert any("pure gain" in f for f in r.findings)


def test_a_concentrated_position_is_named_as_fixing_two_problems():
    r = C.review_gifts([lot(value=400_000)], ltcg_rate=0.15, investable=1_000_000)
    assert any("two things at once" in f for f in r.findings)
    assert any("employer-concentration-risk" in f for f in r.findings)


def test_the_concentration_finding_is_gated_on_the_shared_threshold():
    """Imported from concentration.py, not restated — a small position does
    not trigger it."""
    r = C.review_gifts([lot(value=50_000)], ltcg_rate=0.15, investable=1_000_000)
    assert 50_000 / 1_000_000 < C.MAX_SINGLE_NAME_SHARE
    assert not any("two things at once" in f for f in r.findings)


def test_the_gift_is_sized_by_charitable_intent_not_by_the_concentration():
    r = C.review_gifts([lot(value=400_000)], ltcg_rate=0.15, investable=1_000_000)
    assert any("larger than most households mean to make" in f for f in r.findings)


def test_transferring_the_security_rather_than_selling_it_is_always_said():
    r = C.review_gifts([lot()], ltcg_rate=0.15)
    assert any("do not sell and wire the cash" in f for f in r.findings)


# ── the mirror image: a loss position ───────────────────────────────────────


def test_donating_a_loss_position_is_rejected_outright():
    r = C.review_gifts([lot(value=10_000, basis=25_000)], ltcg_rate=0.15)
    line = by_name(r)["META"]
    assert line.at_a_loss
    assert "sell first, donate cash" in line.recommendation
    assert "forfeits the $15,000 loss permanently" in line.detail


def test_a_loss_position_contributes_no_avoided_gain():
    r = C.review_gifts([lot(value=10_000, basis=25_000)], ltcg_rate=0.15)
    assert r.total_avoided == 0.0


def test_selling_first_leaves_the_charity_no_worse_off():
    r = C.review_gifts([lot(value=10_000, basis=25_000)], ltcg_rate=0.15)
    assert "same amount" in by_name(r)["META"].detail


# ── holding period and missing basis ────────────────────────────────────────


def test_a_short_term_lot_is_deductible_at_basis_not_value():
    r = C.review_gifts([lot(held_days=200)], ltcg_rate=0.15)
    line = by_name(r)["META"]
    assert line.deductible == 10_000
    assert line.gain_tax_avoided is None


def test_the_long_term_boundary_is_a_named_constant():
    short = C.review_gifts([lot(held_days=C.LONG_TERM_DAYS - 1)], ltcg_rate=0.15)
    long = C.review_gifts([lot(held_days=C.LONG_TERM_DAYS)], ltcg_rate=0.15)
    assert by_name(short)["META"].deductible == 10_000
    assert by_name(long)["META"].deductible == 50_000


def test_an_unrecorded_holding_period_is_flagged_rather_than_assumed_long():
    r = C.review_gifts([lot(held_days=None)], ltcg_rate=0.15)
    assert "short-term lot is deductible at basis" in by_name(r)["META"].detail


def test_a_missing_basis_cannot_be_assessed_because_the_answers_are_opposite():
    r = C.review_gifts([lot(basis=None)], ltcg_rate=0.15)
    line = by_name(r)["META"]
    assert line.recommendation == "cannot assess"
    assert "opposite recommendations" in line.detail


def test_no_capital_gains_rate_refuses_to_value_the_benefit():
    r = C.review_gifts([lot()], ltcg_rate=None)
    assert r.gain_rate is None
    assert by_name(r)["META"].gain_tax_avoided is None
    assert any("assumptions.ltcg_rate" in f for f in r.findings)


# ── bunching ────────────────────────────────────────────────────────────────


def test_bunching_helps_a_household_sitting_below_the_standard_deduction():
    p = C.bunch(standard_deduction=30_000, other_itemized=12_000,
                annual_gift=10_000, marginal_rate=0.32, years=2)
    # Annually: max(30k, 22k) = 30k each year = 60k.
    # Bunched:  max(30k, 32k) + 30k = 62k.
    assert p.annual_total == 60_000
    assert p.bunched_total == 62_000
    assert p.benefit == 2_000 * 0.32


def test_bunching_gains_nothing_for_a_household_that_already_itemizes():
    p = C.bunch(standard_deduction=30_000, other_itemized=40_000,
                annual_gift=10_000, marginal_rate=0.32, years=2)
    assert not p.worth_it
    assert p.benefit == 0
    assert any("already clear" in f for f in p.findings)


def test_the_comparison_is_on_total_deductions_not_the_bunch_year_total():
    """A household that already itemizes has a large bunch-year itemized
    figure and no benefit. Reporting the former would imply the latter."""
    p = C.bunch(standard_deduction=30_000, other_itemized=40_000,
                annual_gift=10_000, marginal_rate=0.32, years=3)
    assert p.bunched_total == p.annual_total


def test_a_donor_advised_fund_is_raised_only_when_bunching_helps():
    helps = C.bunch(standard_deduction=30_000, other_itemized=12_000,
                    annual_gift=10_000, marginal_rate=0.32, years=2)
    does_not = C.bunch(standard_deduction=30_000, other_itemized=40_000,
                       annual_gift=10_000, marginal_rate=0.32, years=2)
    assert any("donor-advised fund" in f for f in helps.findings)
    assert not any("donor-advised fund" in f for f in does_not.findings)


def test_the_daf_answers_the_charitys_cash_flow_objection():
    p = C.bunch(standard_deduction=30_000, other_itemized=12_000,
                annual_gift=10_000, marginal_rate=0.32, years=2)
    assert any("cash flow" in f for f in p.findings)


def test_best_bunch_picks_the_window_with_the_largest_benefit():
    p = C.best_bunch(standard_deduction=30_000, other_itemized=12_000,
                     annual_gift=10_000, marginal_rate=0.32)
    assert p.years >= 2
    alternatives = [C.bunch(standard_deduction=30_000, other_itemized=12_000,
                            annual_gift=10_000, marginal_rate=0.32, years=n)
                    for n in range(2, 6)]
    assert p.benefit == max(a.benefit for a in alternatives)


def test_the_bunching_window_never_exceeds_the_carryforward_period():
    p = C.best_bunch(standard_deduction=30_000, other_itemized=0,
                     annual_gift=10_000, marginal_rate=0.32, max_years=99)
    assert p.years <= C.CARRYFORWARD_YEARS


# ── AGI limits ──────────────────────────────────────────────────────────────


def test_the_two_agi_limits_differ_and_the_report_says_so():
    c = C.check_limits(agi=400_000, cash_gift=10_000, appreciated_gift=10_000)
    assert C.CASH_AGI_LIMIT > C.APPRECIATED_AGI_LIMIT
    assert any("The two limits are different" in f for f in c.findings)


def test_an_in_kind_gift_sized_against_the_cash_limit_overshoots():
    c = C.check_limits(agi=200_000, appreciated_gift=120_000)
    assert c.cash_room == 120_000
    assert c.appreciated_excess == 60_000
    assert any("carries forward" in f for f in c.findings)


def test_a_carryforward_is_described_as_worth_less_than_a_deduction_now():
    c = C.check_limits(agi=200_000, appreciated_gift=120_000)
    assert any("worth less than a deduction now" in f for f in c.findings)
    assert C.CARRYFORWARD_YEARS == 5


def test_the_basis_election_is_offered_and_discouraged():
    c = C.check_limits(agi=200_000, appreciated_gift=120_000)
    assert any("almost never worth it" in f for f in c.findings)


def test_a_gift_inside_both_limits_raises_no_excess():
    c = C.check_limits(agi=400_000, cash_gift=20_000, appreciated_gift=20_000)
    assert c.appreciated_excess == 0 and c.cash_excess == 0


def test_a_large_cash_gift_can_exceed_its_own_limit():
    c = C.check_limits(agi=100_000, cash_gift=80_000)
    assert c.cash_excess == 20_000


# ── qualified charitable distributions ──────────────────────────────────────


def test_a_younger_household_is_not_yet_eligible():
    q = C.qcd(age=52)
    assert not q.eligible
    assert any("Not yet eligible" in f for f in q.findings)


def test_eligibility_turns_on_the_statutory_age():
    assert C.qcd(age=C.QCD_AGE).eligible
    assert not C.qcd(age=C.QCD_AGE - 0.5).eligible


def test_the_qcd_age_is_not_the_rmd_age():
    q = C.qcd(age=72)
    assert C.QCD_AGE == 70.5
    assert any("has not moved with the RMD age" in f for f in q.findings)


def test_a_qcd_never_enters_agi_which_is_the_point():
    q = C.qcd(age=72)
    assert any("never enters AGI" in f for f in q.findings)


def test_the_indexed_limit_is_asked_for_not_encoded():
    q = C.qcd(age=72)
    assert q.limit is None
    assert any("assumptions.qcd_annual_limit" in f for f in q.findings)


def test_a_supplied_limit_is_reported_as_per_person():
    q = C.qcd(age=72, annual_limit=108_000)
    assert any("per person" in f for f in q.findings)


def test_the_rmd_ordering_trap_is_raised_when_rmds_apply():
    q = C.qcd(age=75, rmd_applies=True)
    assert any("before" in f and "other distribution" in f for f in q.findings)


def test_no_age_recorded_refuses_rather_than_assuming():
    q = C.qcd(age=None)
    assert not q.eligible
    assert any("cannot be established" in f for f in q.findings)
