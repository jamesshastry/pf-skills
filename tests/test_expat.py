"""Expat filing: the §911 election, the day ledger, domicile, the CFC screen.

Two things are being defended here. The arithmetic — bracket stacking, the
§904 limitation, the rolling window — and, at least as importantly, **the
refusals**: that a missing bracket table produces no figure, that an unknown
state produces no rule, that an unrecorded ownership percentage is not read as
zero, and that the CFC screen stops before GILTI.
"""

import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import expat as X, presence as P  # noqa: E402

D = dt.date

# A deliberately round table, so every expected figure below can be checked by
# hand. Not anyone's real brackets.
BRACKETS = X.Brackets(
    status="married_joint",
    rows=((0.10, 20_000.0), (0.20, 100_000.0), (0.30, 200_000.0),
          (0.40, None)),
    standard_deduction=30_000.0,
)


def stays(*rows):
    return P.build_ledger([dict(r) for r in rows])


# ── brackets ────────────────────────────────────────────────────────────────


def test_tax_is_marginal_not_flat():
    # 20,000 @ 10% = 2,000; 30,000 @ 20% = 6,000.
    assert X.tax_on(50_000, BRACKETS) == pytest.approx(8_000)


def test_tax_reaches_the_open_ended_top_band():
    # 2,000 + 16,000 + 30,000 + 40% of 50,000.
    assert X.tax_on(250_000, BRACKETS) == pytest.approx(68_000)


def test_zero_and_negative_taxable_income_produce_no_tax():
    assert X.tax_on(0, BRACKETS) == 0
    assert X.tax_on(-5_000, BRACKETS) == 0


def test_brackets_are_absent_rather_than_guessed():
    assert X.parse_brackets({}, "married_joint") is None
    assert X.parse_brackets({"federal_brackets": {"single": []}},
                            "married_joint") is None


def test_a_bracket_table_with_no_open_top_band_is_rejected():
    """Silently capping the top band would under-tax high incomes."""
    with pytest.raises(X.BracketError):
        X.parse_brackets({
            "federal_brackets": {"single": [{"rate": 0.1, "up_to": 10_000}]},
            "standard_deduction": {"single": 15_000},
        }, "single")


def test_rates_that_do_not_ascend_are_rejected():
    with pytest.raises(X.BracketError):
        X.parse_brackets({
            "federal_brackets": {"single": [
                {"rate": 0.3, "up_to": 10_000},
                {"rate": 0.1, "up_to": None}]},
            "standard_deduction": {"single": 15_000},
        }, "single")


def test_a_valid_table_round_trips():
    b = X.parse_brackets({
        "federal_brackets": {"single": [
            {"rate": 0.10, "up_to": 20_000},
            {"rate": 0.40, "up_to": None}]},
        "standard_deduction": {"single": 15_000},
        "federal_brackets_as_of": "2026-01-01",
    }, "single")
    assert b.rows == ((0.10, 20_000.0), (0.40, None))
    assert b.standard_deduction == 15_000
    assert b.as_of == "2026-01-01"


# ── FEIE vs FTC: the arithmetic ─────────────────────────────────────────────


# HIGH-TAX CASE. Earnings well above the cap and a local rate above the US
# one, with US-source income alongside so the §904 fraction actually bites.
HIGH_TAX = {
    "foreign_earned_income": 300_000,
    "foreign_tax_on_earned_income": 100_000,
    "us_source_income": 100_000,
    "planned_ira_contribution": 7_000,
    "feie_elected_prior_year": False,
}
# ABOVE THE CAP. Exercises the partial exclusion and the pro-rata disallowance.
ABOVE_CAP = {
    "foreign_earned_income": 200_000,
    "foreign_tax_on_earned_income": 70_000,
    "planned_ira_contribution": 7_000,
    "feie_elected_prior_year": False,
}
LOW_TAX = {
    "foreign_earned_income": 120_000,
    "foreign_tax_on_earned_income": 3_000,
    "feie_elected_prior_year": False,
}


def run(e, **kw):
    kw.setdefault("brackets", BRACKETS)
    kw.setdefault("exclusion_cap", 130_000)
    return X.compare(e, **kw)


def test_the_exclusion_is_capped_not_unlimited():
    c = run(ABOVE_CAP)
    assert c.feie.excluded == 130_000


def test_remaining_income_is_stacked_at_the_rates_without_the_exclusion():
    """The finding people get backwards: the leftover is not taxed from the
    bottom bracket up."""
    c = run(ABOVE_CAP)
    # Taxable after exclusion and standard deduction: 200k - 130k - 30k = 40k.
    assert c.feie.taxable_income == pytest.approx(40_000)
    # Stacked: tax(170k) - tax(130k), not tax(40k).
    stacked = X.tax_on(170_000, BRACKETS) - X.tax_on(130_000, BRACKETS)
    assert c.feie.precredit_tax == pytest.approx(stacked)
    assert c.feie.precredit_tax > X.tax_on(40_000, BRACKETS)


def test_foreign_tax_on_excluded_income_is_not_creditable():
    """§911(d)(6). Exclude everything and the credit disappears with it."""
    c = run(LOW_TAX)
    assert c.feie.excluded == 120_000
    assert c.feie.creditable_foreign_tax == pytest.approx(0)
    assert any("none of the foreign tax" in n for n in c.feie.notes)


def test_partial_exclusion_leaves_a_pro_rata_credit():
    c = run(ABOVE_CAP)
    # 70k of 200k is unexcluded, so 35% of the foreign tax survives.
    assert c.feie.creditable_foreign_tax == pytest.approx(70_000 * 0.35)


def test_the_credit_is_capped_by_the_section_904_limitation():
    """Paying more foreign tax than the US would charge does not refund it."""
    c = run(HIGH_TAX)
    assert c.ftc.credit_used == pytest.approx(c.ftc.credit_limitation)
    assert c.ftc.credit_used < c.ftc.creditable_foreign_tax
    assert c.ftc.carryforward > 0
    # The excess is not refunded: US tax on the US-source income survives.
    assert c.ftc.net_tax > 0


def test_high_tax_country_favours_the_credit():
    c = run(HIGH_TAX)
    assert c.ftc.net_tax < c.feie.net_tax
    assert c.current_year_delta > 0
    assert c.recommendation == "ftc"


def test_low_tax_country_favours_the_exclusion():
    c = run(LOW_TAX)
    assert c.feie.net_tax < c.ftc.net_tax
    assert c.current_year_delta < 0
    assert c.recommendation == "feie"


# ── FEIE vs FTC: the things the two numbers leave out ───────────────────────


def test_excluded_income_cannot_support_an_ira_contribution():
    # The exclusion swallows all of the earned income, leaving nothing behind
    # it to support a contribution.
    c = run({**LOW_TAX, "planned_ira_contribution": 7_000})
    ira = [a for a in c.adjustments if a.label == "IRA contribution room"][0]
    assert ira.favours == "ftc"
    assert ira.value == pytest.approx(7_000 * X.IRA_EXCESS_EXCISE_RATE)
    assert "every year it stays" in ira.detail


def test_an_ira_contribution_covered_by_unexcluded_income_is_not_flagged():
    c = run(ABOVE_CAP)  # 70k of earned income survives the exclusion
    ira = [a for a in c.adjustments if a.label == "IRA contribution room"][0]
    assert ira.value == 0


def test_the_refundable_child_credit_is_named_even_when_it_cannot_be_valued():
    c = run(LOW_TAX, children_under_17=2)
    ctc = [a for a in c.adjustments
           if a.label == "Refundable child tax credit"][0]
    assert ctc.value is None
    assert ctc.favours == "ftc"
    assert ctc in c.unvalued


def test_the_refundable_child_credit_is_valued_when_the_amount_is_supplied():
    c = run(LOW_TAX, children_under_17=2, refundable_ctc_per_child=1_700)
    ctc = [a for a in c.adjustments
           if a.label == "Refundable child tax credit"][0]
    assert ctc.value == pytest.approx(3_400)


def test_an_unvalued_adjustment_pointing_the_other_way_withholds_the_answer():
    """The flagship behaviour: the arithmetic alone is not enough."""
    c = run(LOW_TAX, children_under_17=3)
    assert c.current_year_delta < 0          # exclusion is cheaper this year
    assert c.recommendation == "too_close"   # and the answer is withheld
    assert any("points the other way" in f for f in c.findings)


def test_a_prior_election_makes_switching_a_five_year_decision():
    c = run({**HIGH_TAX, "feie_elected_prior_year": True})
    lock = [a for a in c.adjustments
            if a.label == "Five-year revocation lock"][0]
    assert lock.favours == "feie"
    assert lock.value is None
    assert str(X.FEIE_REVOCATION_LOCK_YEARS) in lock.detail
    assert c.recommendation == "too_close"


def test_an_unrecorded_prior_election_is_reported_not_assumed():
    c = run({k: v for k, v in HIGH_TAX.items()
             if k != "feie_elected_prior_year"})
    assert any("feie_elected_prior_year" in f for f in c.findings)


def test_a_carryforward_is_named_but_never_valued():
    c = run(ABOVE_CAP)
    cf = [a for a in c.adjustments
          if a.label == "Foreign tax credit carryforward"][0]
    assert cf.value is None
    assert "option, not a receivable" in cf.detail


# ── FEIE vs FTC: the refusal ────────────────────────────────────────────────


def test_no_bracket_table_means_no_figure():
    c = X.compare(HIGH_TAX, brackets=None, exclusion_cap=130_000)
    assert not c.determinable
    assert c.feie is None and c.ftc is None
    assert c.recommendation == "undetermined"
    assert any("federal_brackets" in f for f in c.findings)


def test_no_exclusion_cap_means_no_figure():
    c = X.compare(HIGH_TAX, brackets=BRACKETS, exclusion_cap=None)
    assert not c.determinable
    assert any("feie_exclusion_cap" in f for f in c.findings)


def test_missing_income_is_a_refusal_not_a_zero():
    c = X.compare({}, brackets=BRACKETS, exclusion_cap=130_000)
    assert not c.determinable
    assert any("foreign_earned_income" in f for f in c.findings)


def test_the_weakest_input_is_named():
    assert "bracket table" in run(HIGH_TAX).weakest_input


# ── the day ledger ──────────────────────────────────────────────────────────


def test_a_full_foreign_day_excludes_the_edges_of_what_is_known():
    led = stays({"country": "PT", "start": "2026-01-01", "end": "2026-01-05"})
    days = P.full_foreign_days(led)
    assert min(days) == D(2026, 1, 2) and max(days) == D(2026, 1, 4)


def test_a_day_touching_the_us_is_not_a_full_foreign_day():
    led = stays(
        {"country": "PT", "start": "2026-01-01", "end": "2026-01-10"},
        {"country": "US", "start": "2026-01-10", "end": "2026-01-20"},
    )
    assert D(2026, 1, 10) not in P.full_foreign_days(led)
    assert D(2026, 1, 9) in P.full_foreign_days(led)


def test_a_transit_day_between_two_foreign_countries_still_does_not_count():
    led = stays(
        {"country": "PT", "start": "2026-01-01", "end": "2026-01-10"},
        {"country": "XX", "start": "2026-01-11", "end": "2026-01-11",
         "transit": True},
        {"country": "IN", "start": "2026-01-12", "end": "2026-01-20"},
    )
    days = P.full_foreign_days(led)
    assert D(2026, 1, 11) not in days
    assert D(2026, 1, 12) in days


def test_a_gap_is_reported_and_counts_against_the_taxpayer():
    led = stays(
        {"country": "PT", "start": "2026-01-01", "end": "2026-01-10"},
        {"country": "PT", "start": "2026-01-15", "end": "2026-01-31"},
    )
    assert led.gaps == [(D(2026, 1, 11), D(2026, 1, 14))]
    assert any("unaccounted" in f for f in led.findings)
    assert D(2026, 1, 12) not in P.full_foreign_days(led)


def test_an_unreadable_stay_is_dropped_loudly():
    led = P.build_ledger([{"country": "PT", "start": "nonsense",
                           "end": "2026-01-10", "label": "oops"}])
    assert led.stays == []
    assert any("oops" in f for f in led.findings)


def test_a_stay_ending_before_it_starts_is_rejected():
    led = P.build_ledger([{"country": "PT", "start": "2026-02-01",
                           "end": "2026-01-01", "label": "reversed"}])
    assert led.stays == []
    assert any("reversed" in f for f in led.findings)


def test_overlapping_stays_are_flagged_as_possible_duplicates():
    led = stays(
        {"country": "PT", "start": "2026-01-01", "end": "2026-01-10"},
        {"country": "ES", "start": "2026-01-08", "end": "2026-01-20"},
    )
    assert led.overlaps
    assert any("more than one stay" in f for f in led.findings)


# ── the Physical Presence Test ──────────────────────────────────────────────


def test_the_rolling_window_can_pass_where_the_calendar_year_fails():
    """The optimisation that justifies searching rather than counting."""
    led = stays(
        {"country": "US", "start": "2026-01-01", "end": "2026-02-20"},
        {"country": "PT", "start": "2026-02-21", "end": "2027-06-30"},
    )
    r = P.physical_presence(led, tax_year=2026)
    assert r.determinable
    assert not r.calendar_passes
    assert r.passes
    assert r.window_placement_matters
    assert r.window_start > D(2026, 1, 1)
    assert any("calendar year fails" in f for f in r.findings)


def test_a_failing_ledger_reports_the_shortfall_rather_than_a_verdict_alone():
    led = stays(
        {"country": "PT", "start": "2026-01-01", "end": "2026-09-30"},
        {"country": "US", "start": "2026-10-01", "end": "2027-03-31"},
    )
    r = P.physical_presence(led, tax_year=2026)
    assert not r.passes
    assert r.shortfall > 0
    assert r.best_days == P.FULL_DAYS_REQUIRED - r.shortfall


def test_a_ledger_shorter_than_a_year_cannot_be_evaluated():
    led = stays({"country": "PT", "start": "2026-01-01", "end": "2026-06-30"})
    r = P.physical_presence(led, tax_year=2026)
    assert not r.determinable
    assert not r.passes
    assert any("spans" in f for f in r.findings)


def test_an_empty_ledger_refuses_rather_than_returning_zero_days():
    r = P.physical_presence(P.build_ledger([]), tax_year=2026)
    assert not r.determinable
    assert any("No travel ledger" in f for f in r.findings)


def abroad_for(end):
    """US either side of one foreign stay, contiguous and with no gaps, so
    every foreign day has a known neighbour and the span exceeds a year."""
    back = (dt.date.fromisoformat(end) + dt.timedelta(days=1)).isoformat()
    return stays(
        {"country": "US", "start": "2025-12-01", "end": "2025-12-31"},
        {"country": "PT", "start": "2026-01-01", "end": end},
        {"country": "US", "start": back, "end": "2026-12-31"},
    )


def test_exactly_330_full_days_passes():
    r = P.physical_presence(abroad_for("2026-11-26"), tax_year=2026)
    assert r.best_days == P.FULL_DAYS_REQUIRED
    assert r.passes and r.shortfall == 0


def test_one_day_short_fails():
    """The boundary from the other side — the case a rounded-off day count
    turns into a wrong answer."""
    r = P.physical_presence(abroad_for("2026-11-25"), tax_year=2026)
    assert r.best_days == P.FULL_DAYS_REQUIRED - 1
    assert not r.passes and r.shortfall == 1


# ── bona fide residence ─────────────────────────────────────────────────────


def test_bona_fide_is_gated_on_status_for_a_non_citizen():
    b = P.bona_fide({}, us_status="permanent_resident", citizenship=["IN"],
                    tax_year=2026)
    assert b.eligible is None
    assert any("may not be available at all" in f for f in b.findings)


def test_a_citizen_is_eligible_for_the_test_itself():
    b = P.bona_fide({}, us_status="citizen", citizenship=["US"], tax_year=2026)
    assert b.eligible is True


def test_a_retained_us_abode_is_a_failure_not_a_gap():
    b = P.bona_fide({"us_abode_retained": True}, us_status="citizen",
                    citizenship=["US"], tax_year=2026)
    abode = [c for c in b.checks if "abode" in c.label][0]
    assert abode.state == "fail"
    assert b.any_fail


def test_unanswered_bona_fide_questions_are_unknown_not_satisfied():
    b = P.bona_fide({}, us_status="citizen", citizenship=["US"], tax_year=2026)
    assert all(c.state == "unknown" for c in b.checks)
    assert b.any_unknown
    assert any("not the same as satisfied" in f for f in b.findings)


# ── a destination's threshold ───────────────────────────────────────────────


def test_days_in_the_destination_use_the_part_day_basis():
    led = stays({"country": "PT", "start": "2026-03-01", "end": "2026-03-10"})
    t = P.destination_test(led, {"country": "PT", "threshold_days": 5,
                                 "tax_year_start": "2026-01-01",
                                 "tax_year_end": "2026-12-31"})
    assert t.days == 10          # both edge days count here, unlike the PPT
    assert t.crosses is True


def test_no_threshold_means_a_count_and_no_conclusion():
    led = stays({"country": "PT", "start": "2026-03-01", "end": "2026-03-10"})
    t = P.destination_test(led, {"country": "PT",
                                 "tax_year_start": "2026-01-01",
                                 "tax_year_end": "2026-12-31"})
    assert t.days == 10
    assert t.crosses is None
    assert any("does not hold any country's residency rule" in f
               for f in t.findings)


def test_a_missing_destination_tax_year_is_not_assumed_to_be_the_calendar():
    t = P.destination_test(stays({"country": "PT", "start": "2026-03-01",
                                  "end": "2026-03-10"}),
                           {"country": "PT", "threshold_days": 183})
    assert t.days is None
    assert any("tax year is not recorded" in f for f in t.findings)


def test_not_crossing_the_day_count_is_not_a_clean_bill():
    led = stays({"country": "PT", "start": "2026-03-01", "end": "2026-03-10"})
    t = P.destination_test(led, {"country": "PT", "threshold_days": 183,
                                 "tax_year_start": "2026-01-01",
                                 "tax_year_end": "2026-12-31"})
    assert t.crosses is False
    assert any("backstop test" in f for f in t.findings)


# ── state days come off the same ledger ─────────────────────────────────────


def test_state_days_are_counted_from_the_same_ledger():
    led = stays(
        {"country": "US", "state": "CA", "start": "2026-01-01",
         "end": "2026-01-31"},
        {"country": "US", "state": "TX", "start": "2026-02-01",
         "end": "2026-03-31"},
    )
    assert P.count_present_days(led, start=D(2026, 1, 1), end=D(2026, 12, 31),
                                state="CA") == 31


def test_a_ledger_with_no_state_detail_returns_unknown_not_zero():
    led = stays({"country": "US", "start": "2026-01-01", "end": "2026-01-31"})
    assert P.count_present_days(led, start=D(2026, 1, 1), end=D(2026, 12, 31),
                                state="CA") is None


# ── state domicile ──────────────────────────────────────────────────────────


def test_only_checked_states_are_in_the_table():
    assert X.domicile_states_available() == ["CA", "TX"]
    assert X.domicile_rules("NY").known is False
    assert X.domicile_rules(None).known is False


def test_an_unchecked_sticky_state_gets_a_caution_and_no_rule():
    x = X.domicile_exit({"from_state": "NY", "to_state": "TX"})
    text = " ".join(x.findings)
    assert "not in the cited table" in text
    assert "reputation for pursuing" in text
    # and nothing is asserted about how New York actually tests residency
    assert "183" not in text


def test_california_has_no_bright_line_and_a_named_safe_harbour():
    x = X.domicile_exit({"from_state": "CA", "to_state": "TX"})
    text = " ".join(x.findings)
    assert "no day-count bright line" in text
    assert str(X.CA.safe_harbor_days) in text


def test_state_conformity_to_the_exclusion_is_never_assumed():
    x = X.domicile_exit({"from_state": "CA", "to_state": "TX"})
    assert X.CA.conforms_to_feie is None
    assert any("must not be assumed" in f for f in x.findings)


def test_a_state_with_no_income_tax_has_no_exit_problem_to_solve():
    x = X.domicile_exit({"from_state": "TX", "to_state": "PT"})
    assert any("no personal income tax" in f for f in x.findings)


def test_domicile_persists_until_a_new_one_is_established():
    x = X.domicile_exit({"from_state": "CA"}, new_domicile_established=False)
    text = " ".join(x.findings)
    assert "You lose it by acquiring another one" in text
    assert "close to fatal" in text


def test_severance_steps_split_into_done_outstanding_and_unrecorded():
    x = X.domicile_exit({"from_state": "CA", "to_state": "TX",
                         "severance": {"home": True, "voter_registration": False}})
    assert x.completed == ["home"]
    assert [k for k, _ in x.outstanding] == ["voter_registration"]
    assert len(x.unrecorded) == len(X.SEVERANCE_STEPS) - 2
    assert x.score == f"1/{len(X.SEVERANCE_STEPS)}"


def test_uncounted_state_days_are_reported_as_uncounted():
    x = X.domicile_exit({"from_state": "CA"}, days_in_state=None)
    assert any("not a day you were absent" in f for f in x.findings)


def test_statutory_residence_is_named_as_a_separate_hook():
    x = X.domicile_exit({"from_state": "CA"})
    assert any("Statutory residence is a second" in f for f in x.findings)


# ── the CFC screen ──────────────────────────────────────────────────────────


CONTROLLED = {"name": "Acme Ltd", "country": "PT",
              "kind": "foreign_corporation", "ownership_pct": 60}
MINORITY = {"name": "Side Co", "country": "IN",
            "kind": "foreign_corporation", "ownership_pct": 8,
            "us_shareholder_pct": 8}


def test_a_majority_holding_is_a_cfc_and_names_its_forms():
    s = X.cfc_screen([CONTROLLED])
    e = s.entities[0]
    assert e.is_cfc is True
    assert any("category 5" in f for f in e.forms)
    assert any("category 4" in f for f in e.forms)
    assert "Form 8992 (GILTI inclusion)" in e.forms


def test_a_small_holding_is_neither_a_us_shareholder_nor_a_cfc():
    s = X.cfc_screen([MINORITY])
    e = s.entities[0]
    assert e.is_us_shareholder is False
    assert e.is_cfc is False
    assert not s.any_cfc


def test_a_ten_percent_holder_without_control_still_may_have_a_filing():
    s = X.cfc_screen([{"name": "Joint Co", "kind": "foreign_corporation",
                       "ownership_pct": 25, "us_shareholder_pct": 40}])
    e = s.entities[0]
    assert e.is_us_shareholder is True
    assert e.is_cfc is False
    assert any("category 3" in f for f in e.findings)


def test_exactly_fifty_percent_is_not_control():
    """§957 says *more than* 50%. An even split is the case people assume is
    caught, and it is not."""
    s = X.cfc_screen([{"name": "Even Co", "kind": "foreign_corporation",
                       "ownership_pct": 50, "us_shareholder_pct": 50}])
    assert s.entities[0].is_cfc is False


def test_unrecorded_ownership_is_undetermined_not_below_the_threshold():
    s = X.cfc_screen([{"name": "Mystery", "kind": "foreign_corporation"}])
    e = s.entities[0]
    assert e.is_cfc is None
    assert s.any_undetermined
    assert any("not the same as below the threshold" in f for f in e.findings)


def test_non_corporate_entities_are_routed_to_their_own_forms():
    s = X.cfc_screen([
        {"name": "LLP", "kind": "foreign_partnership", "ownership_pct": 30},
        {"name": "Consulting", "kind": "disregarded_entity",
         "ownership_pct": 100},
    ])
    assert s.entities[0].forms == ["Form 8865"]
    assert s.entities[1].forms == ["Form 8858"]
    assert all(e.is_cfc is None for e in s.entities)


def test_no_entities_recorded_asks_for_an_explicit_empty_list():
    s = X.cfc_screen([])
    assert any("record `expat.foreign_entities: []`" in f for f in s.findings)


def test_the_penalty_and_the_open_statute_are_both_reported():
    s = X.cfc_screen([CONTROLLED])
    text = " ".join(s.findings)
    assert "$10,000" in text
    assert "statute of limitations open" in text


def test_attribution_is_flagged_on_every_run():
    assert any("Attribution rules" in f for f in X.cfc_screen([MINORITY]).findings)


def test_the_screen_refuses_to_compute_gilti_or_model_962():
    s = X.cfc_screen([CONTROLLED])
    text = " ".join(s.findings)
    assert "does not compute a GILTI inclusion" in text
    assert "§962" in text
    # no dollar figure of an inclusion anywhere in the entity output
    for e in s.entities:
        assert "inclusion of $" not in " ".join(e.findings)


# ── the framing that has to survive refactoring ─────────────────────────────


def test_the_perpetual_traveler_myth_is_stated_not_implied():
    note = P.PERPETUAL_TRAVELER_NOTE
    assert "citizenship, not sleep" in note
    assert "worse" in note
