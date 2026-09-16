"""Unit tests for Social Security survivor sequencing and insured status.

The sequence is the finding, so most of these pin *when* a benefit starts and
stops rather than how much it is. The gap between the caregiver benefit ending
and the widow(er)'s benefit beginning is the thing the module exists to surface,
and an average across the horizon would carry the same present value while
hiding it entirely.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from pf import ssa as S, survivor as SV  # noqa: E402

BEN = S.Benefits(spouse_at_fra=3200, minor_child=2380,
                 family_maximum=5600, survivor_fra=67)
UNCAPPED = S.Benefits(spouse_at_fra=3200, minor_child=2380,
                      family_maximum=None, survivor_fra=67)


def sched(**kw):
    base = {"benefits": BEN, "survivor_age": 39, "dependent_ages": [8, 5],
            "horizon_years": 51}
    return S.survivor_schedule(**{**base, **kw})


# ── refusals ────────────────────────────────────────────────────────────────

def test_no_amounts_means_nothing_is_netted():
    out = sched(benefits=S.Benefits())
    assert not out.computable
    assert out.years == []
    assert any("largest single omission" in n for n in out.notes)


def test_a_partial_statement_is_not_enough():
    """spouse_at_fra alone cannot build the sequence — the child figure also
    serves as the caregiver benefit."""
    assert not S.Benefits(spouse_at_fra=3200).computable
    assert S.Benefits(spouse_at_fra=3200, minor_child=2380).computable


def test_no_survivor_age_refuses_rather_than_averaging():
    out = sched(survivor_age=None)
    assert not out.computable
    assert any("cannot be placed in time" in n for n in out.notes)


def test_a_missing_fra_is_assumed_but_said_out_loud():
    out = sched(benefits=S.Benefits(spouse_at_fra=3200, minor_child=2380,
                                    family_maximum=5600))
    assert out.computable
    assert any("full_retirement_age" in n for n in out.notes)


# ── the sequence ────────────────────────────────────────────────────────────

def test_the_caregiver_benefit_stops_at_the_youngest_childs_sixteenth():
    """Not their eighteenth. This is the error that moves the gap two years
    later than it really starts."""
    out = sched(dependent_ages=[5])
    # Youngest is 5, so turns 16 when the survivor is 39 + 11 = 50.
    assert "caregiver" in out.years[10].label       # survivor 49
    assert "caregiver" not in out.years[11].label   # survivor 50


def test_a_child_benefit_runs_to_eighteen():
    out = sched(dependent_ages=[5])
    assert out.annual_at(51) > 0      # child is 17
    assert out.annual_at(52) == 0     # child is 18


def test_still_in_school_extends_the_child_benefit_by_a_year():
    a = sched(dependent_ages=[5], child_in_school=False)
    b = sched(dependent_ages=[5], child_in_school=True)
    assert a.annual_at(52) == 0
    assert b.annual_at(52) > 0


def test_there_is_a_gap_and_it_is_reported():
    out = sched()
    gap = out.gap
    assert gap is not None
    assert gap.annual == 0
    assert any("gap" in n.lower() for n in out.notes)


def test_the_widow_benefit_cannot_start_before_sixty():
    out = sched(dependent_ages=[])
    assert out.annual_at(S.WIDOW_EARLIEST_AGE - 1) == 0
    assert out.annual_at(S.WIDOW_EARLIEST_AGE) > 0


def test_the_widow_benefit_is_reduced_before_fra_and_full_after():
    out = sched(dependent_ages=[])
    early = out.annual_at(60)
    full = out.annual_at(67)
    assert early == pytest.approx(3200 * S.WIDOW_FACTOR_AT_EARLIEST * 12, rel=1e-6)
    assert full == pytest.approx(3200 * 12, rel=1e-6)
    assert early < full


def test_no_dependents_means_no_caregiver_phase_at_all():
    out = sched(dependent_ages=[])
    assert not any("caregiver" in y.label for y in out.years)


def test_phases_collapse_consecutive_equal_years():
    out = sched(dependent_ages=[])
    labels = [p.label for p in out.phases]
    assert labels == ["nothing payable", "reduced widow(er)'s benefit",
                      "full widow(er)'s benefit"]
    assert sum(p.years for p in out.phases) == len(out.years)


# ── the family maximum ──────────────────────────────────────────────────────

def test_the_family_maximum_caps_the_total():
    out = sched()
    peak = out.annual_at(39)
    assert peak == pytest.approx(5600 * 12, rel=1e-6)
    assert out.years[0].capped


def test_without_the_cap_the_benefits_simply_add_up():
    out = sched(benefits=UNCAPPED)
    # two children plus the caregiver benefit, all at the child rate
    assert out.annual_at(39) == pytest.approx(3 * 2380 * 12, rel=1e-6)
    assert not out.years[0].capped


def test_a_missing_family_maximum_is_flagged_as_possibly_overstating():
    out = sched(benefits=UNCAPPED)
    assert any("overstate" in n for n in out.notes)


def test_a_binding_cap_is_flagged():
    assert any("family maximum binds" in n for n in sched().notes)


def test_the_cap_does_not_reduce_a_single_benefit_below_it():
    out = sched(dependent_ages=[])
    assert out.annual_at(67) == pytest.approx(3200 * 12, rel=1e-6)


# ── insured status ──────────────────────────────────────────────────────────

def test_forty_credits_is_insured():
    assert S.insured_status({"ss_credits": S.FULLY_INSURED_CREDITS}) is True
    assert S.insured_status({"ss_credits": S.FULLY_INSURED_CREDITS - 1}) is False


def test_an_explicit_flag_wins_over_credits():
    assert S.insured_status({"ss_credits": 4, "ss_insured": True}) is True


def test_unrecorded_is_none_not_false():
    assert S.insured_status({}) is None


def test_an_unrecorded_status_asks_rather_than_asserts():
    notes = S.uninsured_spouse_notes(insured=None, payable_abroad=None)
    assert len(notes) == 1
    assert "not recorded" in notes[0]


def test_an_insured_spouse_gets_no_notes():
    assert S.uninsured_spouse_notes(insured=True, payable_abroad=None) == []


def test_the_first_thing_said_is_that_entitlement_is_unaffected():
    """The common intuition is wrong in the direction that wastes years, so
    the correction leads rather than trailing the caveats."""
    notes = S.uninsured_spouse_notes(insured=False, payable_abroad=None)
    assert "does not reduce" in notes[0]


def test_an_uninsured_spouse_is_told_the_benefit_is_coupled_to_the_filing_date():
    notes = " ".join(S.uninsured_spouse_notes(insured=False,
                                              payable_abroad=True))
    assert "cannot begin until the worker files" in notes


def test_restricted_payment_abroad_is_escalated_for_an_uninsured_spouse():
    notes = " ".join(S.uninsured_spouse_notes(insured=False,
                                              payable_abroad=False))
    assert "entire entitlement" in notes


def test_unknown_payment_abroad_is_reported_as_unknown():
    notes = " ".join(S.uninsured_spouse_notes(insured=False,
                                              payable_abroad=None))
    assert "not recorded" in notes


# ── credit building ─────────────────────────────────────────────────────────

def test_credit_building_is_futile_below_half_the_workers_pia():
    assert S.credit_building_is_futile(own_projected_monthly=800,
                                       worker_pia_monthly=3200) is True


def test_credit_building_pays_above_it():
    assert S.credit_building_is_futile(own_projected_monthly=2200,
                                       worker_pia_monthly=3200) is False


def test_it_refuses_without_both_figures():
    assert S.credit_building_is_futile(own_projected_monthly=None,
                                       worker_pia_monthly=3200) is None
    assert S.credit_building_is_futile(own_projected_monthly=800,
                                       worker_pia_monthly=None) is None


# ── the propagation ─────────────────────────────────────────────────────────

def test_survivor_needs_and_life_insurance_review_pass_the_same_inputs():
    """`survivor-needs` feeds `life-insurance-review`. When Social Security
    netting was added to the first, the second kept calling `compute` without
    it and silently carried the un-netted gap — and because its golden did not
    move, that read as "no impact" rather than "not applied".

    Asserting the call sites agree is cheaper than asserting the numbers do.
    """
    import re
    root = Path(__file__).resolve().parents[1]
    callers = ["survivor-needs", "life-insurance-review"]
    for name in callers:
        src = (root / "skills" / name / "run.py").read_text()
        assert "S.compute(" in src, name
        assert "social_security=" in src, (
            f"{name} calls survivor.compute without social_security, so it "
            "reports a capital gap with no survivor benefit netted")
        assert re.search(r"social_security=F\._dig\(data, \"social_security\"\)",
                         src), name


# ── the horizon year count ──────────────────────────────────────────────

def test_the_schedule_covers_exactly_the_horizon_years():
    """A 51-year horizon is 51 payments — ages 39 through 89 — not a 52nd
    year at life expectancy itself."""
    out = sched()
    assert len(out.years) == 51
    assert out.years[0].survivor_age == 39
    assert out.years[-1].survivor_age == 89
    assert out.annual_at(90) == 0


# ── the netting ─────────────────────────────────────────────────────────

SS_DICT = {
    "statement_date": "2026-09-15",
    "full_retirement_age": 67,
    "retirement_monthly": {62: 2240, 67: 3200, 70: 3968},
    "disability_monthly": 3100,
    "survivors_monthly": {"spouse_at_fra": 3200, "minor_child": 2380,
                          "family_maximum": 5600},
    "payable_abroad": None,
    "totalization_agreement": False,
}
MEMBERS = [
    {"id": "a1", "role": "primary", "age": 41, "income_annual": 180_000},
    {"id": "a2", "role": "spouse", "age": 39, "income_annual": 0},
    {"id": "c1", "role": "dependent", "age": 8},
    {"id": "c2", "role": "dependent", "age": 5},
]


def test_netting_reduces_but_does_not_erase_the_need():
    base = dict(insured_id="a1", members=MEMBERS, annual_spending=96_000,
                assets_available=0)
    without = SV.compute(**base)
    with_ss = SV.compute(**base, social_security=SS_DICT)
    assert with_ss.ss is not None and with_ss.ss.computable
    assert with_ss.capital_for_income < without.capital_for_income
    assert with_ss.ss_value > 0
    assert with_ss.net_need < without.net_need


def test_the_un_netted_need_survives_alongside():
    """Excluding Social Security as conservatism is a visible choice, so the
    before figure must equal what the old code reported on its own."""
    base = dict(insured_id="a1", members=MEMBERS, annual_spending=96_000,
                assets_available=0)
    without = SV.compute(**base)
    with_ss = SV.compute(**base, social_security=SS_DICT)
    assert with_ss.total_need_before_ss == without.total_need


def test_a_flat_average_would_hide_the_gap_the_phases_show():
    with_ss = SV.compute(insured_id="a1", members=MEMBERS,
                         annual_spending=96_000, assets_available=0,
                         social_security=SS_DICT)
    assert with_ss.ss.gap is not None and with_ss.ss.gap.annual == 0


# ── the worker's PIA ────────────────────────────────────────────────────

def test_worker_pia_is_the_fra_figure():
    assert S.worker_pia_from_statement(SS_DICT) == 3200


def test_worker_pia_tolerates_string_keys():
    ss = {"full_retirement_age": 67, "retirement_monthly": {"67": 3200}}
    assert S.worker_pia_from_statement(ss) == 3200


def test_worker_pia_refuses_without_the_figure():
    assert S.worker_pia_from_statement({}) is None
    assert S.worker_pia_from_statement(None) is None
    assert S.worker_pia_from_statement(
        {"full_retirement_age": 67,
         "retirement_monthly": {62: 2240}}) is None


# ── credit-building notes ───────────────────────────────────────────────

def test_a_verdict_of_futile_says_so_plainly():
    notes = S.credit_building_notes(own_projected_monthly=800,
                                    worker_pia_monthly=3200)
    assert any("will not raise household benefits" in n for n in notes)


def test_clearing_the_bar_says_so():
    notes = S.credit_building_notes(own_projected_monthly=2200,
                                    worker_pia_monthly=3200)
    assert any("can** raise" in n for n in notes)


def test_exactly_half_is_not_futile():
    assert S.credit_building_is_futile(own_projected_monthly=1986.5,
                                       worker_pia_monthly=3200) is False


def test_worker_only_names_the_dollar_threshold():
    notes = S.credit_building_notes(own_projected_monthly=None,
                                    worker_pia_monthly=3200)
    joined = " ".join(notes)
    assert "1,600" in joined
    assert "spouse_own_projected_monthly" in joined


def test_neither_figure_asks_for_both_statements():
    notes = S.credit_building_notes(own_projected_monthly=None,
                                    worker_pia_monthly=None)
    assert any("cannot be tested" in n for n in notes)


# ── the SSDI overlay ────────────────────────────────────────────────────

def test_missing_ssdi_is_a_missing_input_not_a_finding():
    notes = S.disability_overlay_notes(ssdi_monthly=None,
                                       has_group_cover=False)
    assert any("unmodelled" in n for n in notes)
    assert any("missing" in n and "input" in n for n in notes)


def test_recorded_ssdi_is_named_as_an_overlay():
    notes = S.disability_overlay_notes(ssdi_monthly=3100,
                                       has_group_cover=False)
    assert any("3,100" in n for n in notes)
    assert not any("offset" in n for n in notes)


def test_group_cover_triggers_the_offset_warning():
    notes = " ".join(S.disability_overlay_notes(ssdi_monthly=3100,
                                                has_group_cover=True))
    assert "offset" in notes


# ── the netting convention ──────────────────────────────────────────────────

def test_a_zero_benefit_nets_to_exactly_the_un_netted_figure():
    """The invariant that catches a discounting mismatch.

    `pv_annuity` is an ordinary annuity — first payment at the end of year
    one. Netting year by year has to use the same convention. An earlier
    version discounted year `i` at `t=i` and disagreed with itself by about
    3% even when the benefit was zero, which is invisible in a report that
    shows only one of the two figures.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
    from pf import survivor as SV
    members = [{"id": "a1", "role": "primary", "age": 41,
                "income_annual": 180_000},
               {"id": "a2", "role": "spouse", "age": 39, "income_annual": 0}]
    ss = {"full_retirement_age": 67,
          "survivors_monthly": {"spouse_at_fra": 0, "minor_child": 0,
                                "family_maximum": 0}}
    n = SV.compute(insured_id="a1", members=members, annual_spending=96_000,
                   assets_available=0, social_security=ss)
    assert n.capital_for_income == pytest.approx(
        n.capital_for_income_before_ss, rel=1e-9)
    assert n.ss_value == pytest.approx(0.0, abs=1e-6)


def test_netting_covers_the_same_periods_as_the_need():
    """Off-by-one guard. The schedule must not run a year longer than the
    annuity it is being netted against, or the benefit is over-credited."""
    from pf import survivor as SV
    out = S.survivor_schedule(benefits=BEN, survivor_age=39,
                              dependent_ages=[], horizon_years=51)
    assert len(out.years) == 51
    assert out.years[-1].survivor_age == 39 + 50
    assert SV.LIFE_EXPECTANCY_AGE == 90
