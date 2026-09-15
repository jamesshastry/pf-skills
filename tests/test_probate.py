"""Unit tests for probate routing, cost and the constrained fix list.

Three things are worth testing here and the arithmetic is the least of them:
that an unrecorded field never resolves to a verdict, that an uncited state
never borrows a cited one's schedule, and that the fix list refuses the
instrument that would be cheapest and wrong.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from pf import probate as P  # noqa: E402

ADULTS = [{"id": "a1", "role": "primary", "age": 50},
          {"id": "a2", "role": "spouse", "age": 48}]
WITH_MINOR = ADULTS + [{"id": "c1", "role": "dependent", "age": 9}]
MINOR_ONLY = [{"id": "a1", "role": "primary", "age": 50},
              {"id": "c1", "role": "dependent", "age": 9}]


# ── the cited table ─────────────────────────────────────────────────────────

def test_an_uncited_state_is_unknown_not_a_default():
    for code in ("OH", "NY", "WY", "zz"):
        assert P.rules_for(code) is P.UNKNOWN, code


def test_a_missing_state_is_unknown():
    assert P.rules_for(None) is P.UNKNOWN
    assert P.rules_for("") is P.UNKNOWN


def test_state_codes_are_matched_case_and_space_insensitively():
    assert P.rules_for(" ca ").state == "CA"


def test_every_cited_state_carries_a_source_and_a_verified_on():
    for code in P.states_available():
        r = P.rules_for(code)
        assert r.source.strip(), code
        assert r.verified_on.strip(), code


def test_no_cost_is_produced_for_an_uncited_state():
    """The whole point of the cited table. If this ever passes a number, a
    'sensible default' has been added and the discipline is gone."""
    c = P.cost(500_000, P.UNKNOWN)
    assert not c.computable
    assert c.total is None


def test_an_uncited_state_still_routes_but_reports_the_pricing_gap():
    e = P.assess([{"name": "x", "value": 100, "titled_to": "individual",
                   "beneficiaries": []}], state="OH")
    assert len(e.exposed) == 1                      # routing still works
    assert any("cannot be estimated" in f for f in e.findings)


# ── the fee schedule ────────────────────────────────────────────────────────

def test_the_first_band_is_priced_at_the_first_rate():
    assert P.statutory_fee(100_000, P.rules_for("CA")) == pytest.approx(4_000)


def test_the_schedule_is_marginal_not_a_flat_rate():
    """Each band applies only to the slice inside it. A flat reading of the
    top rate is the common error and overstates small estates."""
    # 4% of 100k + 3% of the next 100k.
    assert P.statutory_fee(200_000, P.rules_for("CA")) == pytest.approx(7_000)
    # ... + 2% of the next 800k.
    assert P.statutory_fee(1_000_000, P.rules_for("CA")) == pytest.approx(23_000)


def test_each_band_boundary(  ):
    ca = P.rules_for("CA")
    for gross, want in ((100_000, 4_000), (200_000, 7_000),
                        (1_000_000, 23_000), (10_000_000, 113_000),
                        (25_000_000, 188_000)):
        assert P.statutory_fee(gross, ca) == pytest.approx(want), gross


def test_above_the_last_band_there_is_no_formula():
    """The statute stops giving one. Returning a number here would be
    invention, so it returns None and the report says the court decides."""
    assert P.statutory_fee(30_000_000, P.rules_for("CA")) is None


def test_an_hourly_state_has_no_schedule_to_apply():
    assert P.statutory_fee(500_000, P.rules_for("TX")) is None
    c = P.cost(500_000, P.rules_for("TX"))
    assert not c.computable
    assert "reasonable" in c.detail


def test_the_fee_is_doubled_where_both_claimants_may_charge_it():
    """The detail that makes a percentage state expensive, and the one a
    single reading of the statute misses."""
    ca = P.rules_for("CA")
    c = P.cost(1_000_000, ca)
    assert c.doubled
    assert c.single_fee == pytest.approx(23_000)
    assert c.total == pytest.approx(46_000)
    assert "each" in c.detail


# ── small estate ────────────────────────────────────────────────────────────

def test_below_the_small_estate_threshold_the_exposure_is_near_zero():
    c = P.cost(70_000, P.rules_for("TX"))       # threshold 75,000
    assert c.small_estate and c.total == 0
    assert "do not buy paperwork" in c.detail


def test_the_threshold_is_inclusive_at_the_boundary():
    assert P.cost(75_000, P.rules_for("TX")).small_estate
    assert not P.cost(75_001, P.rules_for("TX")).small_estate


def test_just_above_the_threshold_is_priced_normally():
    c = P.cost(200_000, P.rules_for("CA"))      # threshold 184,500
    assert not c.small_estate and c.computable


# ── routing ─────────────────────────────────────────────────────────────────

def r(**kw):
    return P.route({"name": "x", "value": 1000, **kw})


def test_trust_titling_avoids():
    assert r(titled_to="trust").verdict == P.AVOIDS


def test_joint_titling_avoids_but_warns_about_tenants_in_common():
    out = r(titled_to="joint")
    assert out.verdict == P.AVOIDS
    assert "tenants in common" in out.why


def test_a_named_beneficiary_avoids_even_when_individually_titled():
    assert r(titled_to="individual",
             beneficiary_primary="a2").verdict == P.AVOIDS


def test_the_estate_named_as_beneficiary_is_exposed():
    assert r(titled_to="individual",
             beneficiary_primary="estate").verdict == P.PROBATE


def test_individually_titled_with_nobody_named_is_exposed():
    assert r(titled_to="individual", beneficiaries=[]).verdict == P.PROBATE


def test_an_asset_that_takes_no_designation_is_decided_by_titling():
    assert r(titled_to="individual",
             beneficiary_applicable=False).verdict == P.PROBATE
    assert r(titled_to="joint",
             beneficiary_applicable=False).verdict == P.AVOIDS


# ── the refusals ────────────────────────────────────────────────────────────

def test_nothing_recorded_is_undetermined_not_exposed():
    out = r()
    assert out.verdict == P.UNDETERMINED
    assert not out.exposed


def test_unrecorded_designation_on_an_individual_account_is_undetermined():
    assert r(titled_to="individual").verdict == P.UNDETERMINED


def test_nobody_named_but_titling_unrecorded_is_undetermined():
    """Checked-and-empty is a defect, but joint or trust titling would still
    carry it out. Calling it exposed skips a question that has an answer."""
    assert r(beneficiaries=[]).verdict == P.UNDETERMINED


def test_an_undetermined_account_is_counted_in_neither_total():
    e = P.assess([{"name": "u", "value": 50_000},
                  {"name": "e", "value": 10_000, "titled_to": "individual",
                   "beneficiaries": []}], state="TX")
    assert e.exposed_total == 10_000
    assert e.undetermined_total == 50_000
    assert e.upper_total == 60_000
    assert not e.determinable


def test_a_fully_recorded_estate_is_determinable():
    e = P.assess([{"name": "a", "value": 1, "titled_to": "trust"}], state="TX")
    assert e.determinable


# ── designation derived from either shape ───────────────────────────────────

def test_the_primary_is_derived_from_the_beneficiaries_list():
    """`beneficiary-audit` already reads this shape. Requiring a duplicate
    shorthand field would guarantee the two eventually disagree."""
    state, who = P.designation({"beneficiaries": [
        {"member_id": "a2", "type": "primary"},
        {"relationship": "trust", "type": "contingent"}]})
    assert (state, who) == (P.NAMED, "a2")


def test_a_list_of_only_contingents_counts_as_nobody_named():
    state, _ = P.designation({"beneficiaries": [
        {"member_id": "c1", "type": "contingent"}]})
    assert state == P.NONE_NAMED


def test_the_estate_in_the_list_is_recognised():
    state, _ = P.designation({"beneficiaries": [
        {"name": "Estate", "type": "primary"}]})
    assert state == P.PROBATE


def test_an_absent_list_is_unrecorded_and_an_empty_one_is_not():
    assert P.designation({})[0] == P.UNRECORDED
    assert P.designation({"beneficiaries": []})[0] == P.NONE_NAMED


def test_not_applicable_beats_everything():
    assert P.designation({"beneficiary_applicable": False,
                          "beneficiaries": []})[0] == P.NOT_APPLICABLE


# ── the fix list ────────────────────────────────────────────────────────────

def exposed_row(**kw):
    return P.route({"name": "x", "value": 1000, "titled_to": "individual",
                    "beneficiaries": [], **kw})


def test_a_taxable_account_is_sent_to_the_trust():
    f = P.recommend([exposed_row()], members=ADULTS, trust_exists=True)[0]
    assert "trust" in f.instrument.lower()


def test_a_retirement_account_names_the_spouse_not_the_trust():
    """The wrapper rule. Optimising for probate alone would put the trust
    here and cost the survivor the rollover."""
    f = P.recommend([exposed_row(tier="age_restricted")],
                    members=ADULTS, trust_exists=True)[0]
    assert "spouse" in f.instrument.lower()
    assert "trust" not in f.instrument.lower()
    assert "rollover" in f.rationale


def test_the_module_gives_different_answers_for_the_two_wrappers():
    """Directly asserts the refusal to answer for 'accounts' generically."""
    fixes = P.recommend([exposed_row(), exposed_row(tier="age_restricted")],
                        members=ADULTS, trust_exists=True)
    assert fixes[0].instrument != fixes[1].instrument


def test_a_tod_is_withheld_where_the_only_beneficiaries_are_minors():
    """Avoiding probate is not the same as a good outcome: a TOD to a minor
    buys a guardianship of the estate and an outright payout at majority."""
    f = P.recommend([exposed_row()], members=MINOR_ONLY,
                    trust_exists=False)[0]
    assert f.withheld
    assert "guardianship" in f.withheld
    assert str(P.AGE_OF_MAJORITY) in f.withheld


def test_a_tod_is_offered_where_there_is_an_adult_beneficiary():
    f = P.recommend([exposed_row()], members=WITH_MINOR,
                    trust_exists=False)[0]
    assert not f.withheld
    assert "death" in f.instrument.lower()


def test_no_instrument_is_recommended_for_an_unknown_account():
    f = P.recommend([P.route({"name": "x", "value": 1})],
                    members=ADULTS, trust_exists=True)[0]
    assert "Find out first" in f.instrument


def test_accounts_that_already_avoid_get_no_fix():
    assert P.recommend([P.route({"name": "x", "value": 1,
                                 "titled_to": "trust"})],
                       members=ADULTS, trust_exists=True) == []


# ── the spousal shortcut ────────────────────────────────────────────────────

def test_an_unchecked_spousal_rule_says_so_rather_than_saying_no():
    note = P.spousal_note(P.rules_for("TX"), will_pours_to_trust=None)
    assert "not been checked" in note


def test_the_pour_over_interaction_is_flagged_not_decided():
    note = P.spousal_note(P.rules_for("CA"), will_pours_to_trust=True)
    assert "off the table" in note
    assert "counsel" in note


def test_without_a_pour_over_the_shortcut_is_reported_plainly():
    note = P.spousal_note(P.rules_for("CA"), will_pours_to_trust=False)
    assert "off the table" not in note


def test_an_uncited_state_gives_no_spousal_answer():
    assert "not been checked" in P.spousal_note(P.UNKNOWN,
                                                will_pours_to_trust=True)


# ── shared constants are imported, not restated ─────────────────────────────

def test_the_age_of_majority_is_the_estate_modules_constant():
    from pf import estate
    assert P.AGE_OF_MAJORITY is estate.AGE_OF_MAJORITY
