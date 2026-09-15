"""Life transitions — windfall, marriage, divorce.

Three things are being defended here:

* the ninety-day pause is stated as a **blocker**, not as a pleasantry;
* an unknown tax character or an unknown basis is a refusal, never a zero;
* the after-tax gap on a nominally equal divorce split is computed, because
  that gap is the entire reason the third skill exists.
"""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import cash as K  # noqa: E402
from pf import healthcare as H  # noqa: E402
from pf import reporting as R  # noqa: E402
from pf import transitions as T  # noqa: E402


def test_the_irmaa_lookback_is_healthcares_and_not_a_second_copy():
    """Identity, not equality. `healthcare.py` owns the Medicare structure and
    its skills are the load-bearing consumers; this module only reports the
    consequence. A literal here would pass on equality and drift later."""
    assert T.IRMAA_LOOKBACK_YEARS is H.IRMAA_LOOKBACK_YEARS

AS_OF = dt.date(2026, 8, 30)
RECENT = "2026-07-15"          # 46 days before AS_OF — inside the pause
OLD = "2025-01-10"             # well outside it

MIXED_MEMBERS = [
    {"id": "a1", "role": "primary", "us_status": "citizen", "age": 41},
    {"id": "a2", "role": "spouse", "us_status": "permanent_resident", "age": 39},
]
CITIZEN_MEMBERS = [
    {"id": "a1", "role": "primary", "us_status": "citizen", "age": 41},
    {"id": "a2", "role": "spouse", "us_status": "citizen", "age": 39},
]
US_DOM = {"country": "US", "state": "TX", "determined": True}


def joined(findings):
    return " ".join(f.detail for f in findings)


def area(obj, name):
    return [f for f in obj.findings if f.area == name]


# ══ windfall ════════════════════════════════════════════════════════════════
# ── the pause is the answer ─────────────────────────────────────────────────


def test_a_recent_windfall_produces_a_do_nothing_blocker():
    p = T.assess_windfall(
        [{"label": "inheritance", "kind": "inheritance", "amount": 400_000,
          "received": RECENT, "source_foreign": False}],
        as_of=AS_OF, marginal_rate=0.24)
    pause = area(p, "pause")
    assert pause and pause[0].severity == "blocker"
    assert "irreversible" in pause[0].detail
    assert p.any_pause_live


def test_the_pause_expires_and_then_says_so():
    p = T.assess_windfall(
        [{"kind": "inheritance", "amount": 400_000, "received": OLD,
          "source_foreign": False}],
        as_of=AS_OF, marginal_rate=0.24)
    assert area(p, "pause")[0].severity == "ok"
    assert not p.any_pause_live


def test_the_pause_window_is_measured_from_receipt_not_from_today():
    p = T.assess_windfall(
        [{"kind": "inheritance", "amount": 1, "received": RECENT}],
        as_of=AS_OF)
    e = p.events[0]
    assert e.pause_until == dt.date(2026, 7, 15) + dt.timedelta(
        days=T.DECISION_PAUSE_DAYS)
    assert e.days_held == 46


def test_no_receipt_date_is_a_gap_not_an_elapsed_pause():
    p = T.assess_windfall([{"kind": "inheritance", "amount": 400_000}],
                          as_of=AS_OF)
    pause = area(p, "pause")[0]
    assert pause.severity == "gap"
    assert p.events[0].pause_elapsed is None


# ── tax character ───────────────────────────────────────────────────────────


def test_an_inheritance_steps_up_and_an_ipo_vest_does_not():
    assert T.tax_character("inheritance").basis_rule == "stepped_up"
    assert T.tax_character("inheritance").income_on_receipt is False
    assert T.tax_character("equity_vest").basis_rule == "unchanged"
    assert T.tax_character("equity_vest").income_on_receipt is True


def test_an_inherited_retirement_account_is_the_opposite_of_an_inheritance():
    """The trap: the word is the same, the treatment is inverted."""
    c = T.tax_character("retirement_account_inherited")
    assert c.basis_rule == "unchanged"
    assert "No step-up" in c.note


def test_a_gift_carries_over_basis_where_an_inheritance_does_not():
    assert T.tax_character("gift").basis_rule == "carryover"


def test_an_unknown_kind_refuses_rather_than_guessing():
    c = T.tax_character("crypto_airdrop_from_a_friend")
    assert c.known is False
    p = T.assess_windfall(
        [{"kind": "crypto_airdrop_from_a_friend", "amount": 50_000,
          "received": OLD}],
        as_of=AS_OF, marginal_rate=0.24)
    blockers = [f for f in p.blockers if f.area == "character"]
    assert blockers
    assert "not in the table" in blockers[0].detail


def test_a_settlement_is_excluded_from_the_estimate_rather_than_characterised():
    p = T.assess_windfall(
        [{"kind": "settlement", "amount": 300_000, "received": OLD}],
        as_of=AS_OF, marginal_rate=0.32)
    assert p.taxable_amount == 0
    assert any("allocation" in f.detail for f in p.blockers)
    assert any(f.area == "estimated tax" and f.severity == "gap"
               for f in p.findings)


# ── the withholding gap ─────────────────────────────────────────────────────


def test_supplemental_withholding_is_flagged_as_a_rate_not_a_tax():
    p = T.assess_windfall(
        [{"kind": "equity_vest", "amount": 500_000, "received": OLD}],
        as_of=AS_OF, marginal_rate=0.35, withheld=110_000)
    w = area(p, "withholding")[0]
    assert w.severity == "blocker"
    # 500k * (0.35 - 0.22) = 65,000
    assert "$65,000" in w.detail


def test_above_the_threshold_the_higher_mandatory_rate_applies():
    p = T.assess_windfall(
        [{"kind": "equity_vest", "amount": 1_500_000, "received": OLD}],
        as_of=AS_OF, marginal_rate=0.37)
    assert "37%" in area(p, "withholding")[0].detail


def test_the_shortfall_nets_what_was_actually_withheld():
    p = T.assess_windfall(
        [{"kind": "equity_vest", "amount": 100_000, "received": OLD}],
        as_of=AS_OF, marginal_rate=0.35, withheld=22_000)
    assert p.estimated_tax == 35_000
    assert p.shortfall == 13_000


def test_no_marginal_rate_blocks_the_estimate_rather_than_assuming_one():
    p = T.assess_windfall(
        [{"kind": "lottery", "amount": 1_000_000, "received": OLD}],
        as_of=AS_OF)
    assert p.estimated_tax is None
    assert any("marginal rate" in f.detail for f in p.blockers)


# ── safe harbour ────────────────────────────────────────────────────────────


def test_the_safe_harbour_steps_up_above_the_high_agi_line():
    low = T.safe_harbor_payment(40_000, T.SAFE_HARBOR_HIGH_AGI)
    high = T.safe_harbor_payment(40_000, T.SAFE_HARBOR_HIGH_AGI + 1)
    assert low == 40_000
    assert high == 44_000


def test_an_unknown_prior_year_returns_none_not_zero():
    assert T.safe_harbor_payment(None, 500_000) is None
    p = T.assess_windfall(
        [{"kind": "inheritance", "amount": 10_000, "received": OLD}],
        as_of=AS_OF, marginal_rate=0.24)
    assert p.safe_harbor is None
    assert any(f.area == "estimated tax" and "safe harbour" in f.detail
               for f in p.findings)


# ── Form 3520, imported ─────────────────────────────────────────────────────


def test_the_foreign_threshold_is_imported_not_restated():
    """If reporting.py moves the threshold, this module must move with it."""
    assert T._rep.FOREIGN_GIFT_THRESHOLD is R.FOREIGN_GIFT_THRESHOLD


def test_a_foreign_inheritance_over_the_threshold_triggers_form_3520():
    p = T.assess_windfall(
        [{"kind": "inheritance", "amount": R.FOREIGN_GIFT_THRESHOLD + 1,
          "received": OLD, "source_foreign": True}],
        as_of=AS_OF, marginal_rate=0.24)
    f = area(p, "reporting")[0]
    assert f.severity == "blocker"
    assert "3520" in f.detail
    assert "No tax is due" in f.detail


def test_a_foreign_gift_under_the_threshold_is_ok_but_says_it_aggregates():
    p = T.assess_windfall(
        [{"kind": "gift", "amount": R.FOREIGN_GIFT_THRESHOLD - 1,
          "received": OLD, "source_foreign": True}],
        as_of=AS_OF, marginal_rate=0.24)
    f = area(p, "reporting")[0]
    assert f.severity == "ok"
    assert "aggregate" in f.detail


def test_an_unstated_source_is_a_gap_not_an_assumption_of_domestic():
    p = T.assess_windfall(
        [{"kind": "inheritance", "amount": 500_000, "received": OLD}],
        as_of=AS_OF, marginal_rate=0.24)
    assert area(p, "reporting")[0].severity == "gap"


# ── the rest of the windfall surface ────────────────────────────────────────


def test_over_the_fdic_limit_the_parking_advice_appears():
    p = T.assess_windfall(
        [{"kind": "inheritance", "amount": T.FDIC_LIMIT_PER_DEPOSITOR + 1,
          "received": OLD, "source_foreign": False}],
        as_of=AS_OF, marginal_rate=0.24)
    assert any("FDIC" in f.detail for f in area(p, "parking"))


def test_under_the_fdic_limit_it_stays_quiet():
    p = T.assess_windfall(
        [{"kind": "inheritance", "amount": 100_000, "received": OLD,
          "source_foreign": False}],
        as_of=AS_OF, marginal_rate=0.24)
    assert not area(p, "parking")


def test_new_accounts_without_beneficiaries_are_a_blocker():
    p = T.assess_windfall(
        [{"kind": "inheritance", "amount": 100_000, "received": OLD,
          "source_foreign": False}],
        as_of=AS_OF, marginal_rate=0.24,
        new_accounts_without_beneficiaries=["windfall holding account"])
    b = [f for f in p.blockers if f.area == "beneficiaries"]
    assert b and "windfall holding account" in b[0].detail


def test_irmaa_is_described_as_a_two_year_echo_and_not_appealable():
    p = T.assess_windfall(
        [{"kind": "inheritance", "amount": 100_000, "received": OLD,
          "source_foreign": False}],
        as_of=AS_OF, marginal_rate=0.24, medicare_within_lookback=True)
    d = area(p, "irmaa")[0].detail
    assert "SSA-44" in d
    assert str(T.IRMAA_LOOKBACK_YEARS) in d


def test_aca_coverage_is_a_this_year_problem():
    p = T.assess_windfall(
        [{"kind": "equity_vest", "amount": 200_000, "received": OLD,
          "source_foreign": False}],
        as_of=AS_OF, marginal_rate=0.24, aca_marketplace_coverage=True)
    assert area(p, "aca")[0].severity == "blocker"


def test_no_events_is_a_clean_gap():
    p = T.assess_windfall([], as_of=AS_OF)
    assert p.findings and p.findings[0].severity == "gap"
    assert p.total == 0


# ══ marriage ════════════════════════════════════════════════════════════════
# ── filing status: both branches ────────────────────────────────────────────


def test_joint_wins_when_there_is_no_loan_to_offset_the_extra_tax():
    c = T.compare_filing_status(joint_tax=41_200,
                                separate_tax_combined=46_800)
    assert c.tax_delta == 5_600
    assert c.recommendation == "joint"


def test_separate_wins_when_the_idr_saving_exceeds_the_tax_cost():
    c = T.compare_filing_status(
        joint_tax=41_200, separate_tax_combined=46_800,
        idr_payment_joint=14_400, idr_payment_separate=3_120)
    assert c.idr_delta == 11_280
    assert c.net_advantage == 11_280 - 5_600
    assert c.recommendation == "separate"


def test_choosing_separate_also_prints_what_separate_costs():
    c = T.compare_filing_status(
        joint_tax=41_200, separate_tax_combined=46_800,
        idr_payment_joint=14_400, idr_payment_separate=3_120)
    gaps = [f for f in c.findings if f.severity == "gap"]
    assert gaps and "Roth IRA phase-out" in gaps[0].detail
    assert f"${T.MFS_ROTH_PHASEOUT_CEILING:,.0f}" in gaps[0].detail


def test_the_community_property_caveat_rides_with_the_idr_recommendation():
    c = T.compare_filing_status(
        joint_tax=10_000, separate_tax_combined=11_000,
        idr_payment_joint=9_000, idr_payment_separate=1_000)
    assert "community property" in joined(c.findings)


def test_missing_either_total_refuses_to_recommend():
    c = T.compare_filing_status(joint_tax=41_200, separate_tax_combined=None)
    assert c.recommendation == "cannot be determined"
    assert c.findings[0].severity == "blocker"


def test_joint_liability_is_stated_whichever_way_it_goes():
    for kwargs in ({"joint_tax": 1, "separate_tax_combined": 2},
                   {"joint_tax": 2, "separate_tax_combined": 1}):
        c = T.compare_filing_status(**kwargs)
        assert "joint and several" in joined(c.findings)


# ── the medical branch ──────────────────────────────────────────────────────


def test_medical_expenses_against_a_lower_agi_clear_a_lower_floor():
    p = T.assess_marriage(
        members=CITIZEN_MEMBERS, domicile=US_DOM,
        joint_tax=40_000, separate_tax_combined=42_000,
        medical_expenses=30_000, lower_earner_agi=60_000,
        household_agi=300_000)
    # joint floor 22,500 → 7,500 deductible; separate floor 4,500 → 25,500
    assert "argues for separate" in joined(p.findings)


def test_medical_expenses_with_no_agi_cannot_be_tested():
    p = T.assess_marriage(
        members=CITIZEN_MEMBERS, domicile=US_DOM,
        joint_tax=40_000, separate_tax_combined=42_000,
        medical_expenses=30_000)
    assert any(f.severity == "gap" and "AGI figures" in f.detail
               for f in p.findings)


def test_the_medical_floor_is_the_statutory_one():
    assert T.MEDICAL_DEDUCTION_AGI_FLOOR == 0.075


# ── beneficiaries and estate ────────────────────────────────────────────────


def test_erisa_spousal_consent_and_the_ira_gap_are_both_stated():
    p = T.assess_marriage(members=CITIZEN_MEMBERS, domicile=US_DOM,
                          joint_tax=1, separate_tax_combined=2)
    d = joined(area(p, "beneficiaries"))
    assert "notarised written consent" in d
    assert "IRA has no such protection" in d


def test_stale_pre_marriage_designations_escalate_to_a_blocker():
    p = T.assess_marriage(members=CITIZEN_MEMBERS, domicile=US_DOM,
                          joint_tax=1, separate_tax_combined=2,
                          accounts_with_stale_beneficiaries=["rollover IRA"])
    assert any(f.area == "beneficiaries" and f.severity == "blocker"
               for f in p.findings)


def test_a_non_citizen_spouse_loses_the_marital_deduction_via_status_py():
    """Imported from status.py, not restated — QDOT wording is the tell."""
    p = T.assess_marriage(members=MIXED_MEMBERS, domicile=US_DOM,
                          joint_tax=1, separate_tax_combined=2)
    estate = area(p, "estate")
    assert any(f.severity == "blocker" and "QDOT" in f.detail for f in estate)
    assert any("citizenship-status-review" in f.detail for f in estate)


def test_a_citizen_pair_gets_no_qdot_blocker():
    p = T.assess_marriage(members=CITIZEN_MEMBERS, domicile=US_DOM,
                          joint_tax=1, separate_tax_combined=2)
    assert not any("QDOT" in f.detail for f in area(p, "estate"))


def test_portability_requires_a_return_nobody_would_otherwise_file():
    p = T.assess_marriage(members=CITIZEN_MEMBERS, domicile=US_DOM,
                          joint_tax=1, separate_tax_combined=2)
    d = joined(area(p, "estate"))
    assert "Form 706" in d and "no estate tax is owed" in d


# ── accounts as a policy ────────────────────────────────────────────────────


def test_the_independent_access_floor_is_imported_from_cash_py():
    p = T.assess_marriage(members=CITIZEN_MEMBERS, domicile=US_DOM,
                          joint_tax=1, separate_tax_combined=2,
                          monthly_spending=8_000)
    expected = 8_000 * K.MIN_BUFFER_MONTHS
    assert f"${expected:,.0f}" in joined(area(p, "accounts"))


def test_a_spouse_with_no_individual_account_is_named():
    p = T.assess_marriage(members=CITIZEN_MEMBERS, domicile=US_DOM,
                          joint_tax=1, separate_tax_combined=2,
                          independent_access={"a1": True, "a2": False})
    assert any(f.severity == "gap" and "a2" in f.detail
               for f in area(p, "accounts"))


# ══ divorce ═════════════════════════════════════════════════════════════════
# ── a dollar is not a dollar ────────────────────────────────────────────────

EQUAL_ON_PAPER = [
    # Roth: fully spendable.
    {"name": "roth", "kind": "roth_ira", "value": 200_000, "to": "a"},
    # Pre-tax: worth 76% of the statement at a 24% ordinary rate.
    {"name": "401k", "kind": "traditional_401k", "value": 200_000, "to": "b"},
]


def test_a_nominally_equal_split_is_unequal_after_tax():
    s = T.split_assets(EQUAL_ON_PAPER, ordinary_rate=0.24,
                       capital_gains_rate=0.15)
    assert s.nominal_gap == 0
    assert s.after_tax_by_party["a"] == 200_000
    assert s.after_tax_by_party["b"] == 152_000
    assert s.after_tax_gap == 48_000
    blocker = [f for f in s.findings
               if f.area == "split" and f.severity == "blocker"]
    assert blocker and "three different amounts of spendable money" in \
        blocker[0].detail


def test_the_equalising_transfer_is_half_the_after_tax_gap():
    s = T.split_assets(EQUAL_ON_PAPER, ordinary_rate=0.24,
                       capital_gains_rate=0.15)
    assert "$24,000" in joined([f for f in s.findings if f.area == "split"])


def test_embedded_gain_on_taxable_stock_reduces_its_value():
    at, gain, _ = T.after_tax_value(
        {"kind": "taxable", "value": 100_000, "basis": 20_000},
        ordinary_rate=0.24, capital_gains_rate=0.15)
    assert gain == 80_000
    assert at == 100_000 - 12_000


def test_a_split_that_is_genuinely_even_after_tax_says_so():
    s = T.split_assets(
        [{"name": "roth", "kind": "roth_ira", "value": 100_000, "to": "a"},
         {"name": "hsa", "kind": "hsa", "value": 100_000, "to": "b"}],
        ordinary_rate=0.24, capital_gains_rate=0.15)
    assert s.after_tax_gap == 0
    assert any(f.area == "split" and f.severity == "ok" for f in s.findings)


# ── unknown is not zero ─────────────────────────────────────────────────────


def test_a_taxable_account_with_no_basis_cannot_be_valued():
    at, gain, note = T.after_tax_value(
        {"kind": "taxable", "value": 100_000},
        ordinary_rate=0.24, capital_gains_rate=0.15)
    assert at is None and gain is None
    assert "cannot be determined" in note


def test_missing_basis_makes_the_whole_comparison_incomplete():
    s = T.split_assets(
        EQUAL_ON_PAPER + [{"name": "brokerage", "kind": "taxable",
                           "value": 90_000, "to": "a"}],
        ordinary_rate=0.24, capital_gains_rate=0.15)
    assert s.undetermined == 90_000
    assert not s.complete
    assert any("could not be valued after tax" in f.detail for f in s.findings)
    # and it must not silently print an after-tax verdict anyway
    assert not any(f.area == "split" and f.severity == "ok" for f in s.findings)


def test_missing_rates_refuse_the_whole_split():
    s = T.split_assets(EQUAL_ON_PAPER, ordinary_rate=None,
                       capital_gains_rate=0.15)
    assert not s.lines
    assert s.findings[0].severity == "blocker"
    assert "post-divorce" in s.findings[0].detail


def test_an_unknown_account_kind_is_refused_not_guessed():
    s = T.split_assets(
        [{"name": "crypto", "kind": "self_custodied_wallet", "value": 50_000,
          "to": "a"}],
        ordinary_rate=0.24, capital_gains_rate=0.15)
    assert s.lines[0].after_tax is None
    assert any(f.area == "mechanism" and f.severity == "blocker"
               for f in s.findings)


def test_an_unassigned_asset_is_reported_rather_than_split():
    s = T.split_assets(
        [{"name": "roth", "kind": "roth_ira", "value": 100_000}],
        ordinary_rate=0.24, capital_gains_rate=0.15)
    assert s.nominal_total == 0
    assert any("not assigned to a party" in f.detail for f in s.findings)


# ── mechanisms ──────────────────────────────────────────────────────────────


def test_qualified_plans_need_a_qdro_and_iras_do_not():
    assert T.transfer_mechanism("traditional_401k").instrument == "QDRO"
    assert T.transfer_mechanism("pension").instrument == "QDRO"
    assert T.transfer_mechanism("traditional_ira").instrument == \
        "transfer incident to divorce"
    assert "not** a qualified plan" in \
        T.transfer_mechanism("traditional_ira").detail


def test_a_decree_is_not_a_qdro():
    assert "is not a QDRO" in T.transfer_mechanism("traditional_401k").detail


def test_basis_carries_over_on_a_1041_transfer():
    m = T.transfer_mechanism("taxable")
    assert m.instrument == "§1041 transfer"
    assert "basis carries over unchanged" in m.detail


def test_the_qdro_penalty_exception_is_flagged_as_sequence_sensitive():
    s = T.split_assets(EQUAL_ON_PAPER, ordinary_rate=0.24,
                       capital_gains_rate=0.15)
    d = joined([f for f in s.findings if f.area == "mechanism"])
    assert "rolled into an IRA" in d
    assert f"{T.EARLY_DISTRIBUTION_PENALTY:.0%}" in d


def test_an_unknown_mechanism_kind_refuses():
    assert T.transfer_mechanism("timeshare").known is False
    assert T.transfer_mechanism(None).known is False


# ── beneficiaries survive the decree ────────────────────────────────────────


def test_beneficiary_designations_survive_divorce_and_erisa_preempts():
    s = T.split_assets(EQUAL_ON_PAPER, ordinary_rate=0.24,
                       capital_gains_rate=0.15)
    b = [f for f in s.findings if f.area == "beneficiaries"]
    assert b and b[0].severity == "blocker"
    assert "preempted" in b[0].detail
    assert "still the named beneficiary" in b[0].detail


# ── the refusals ────────────────────────────────────────────────────────────


def test_support_and_children_are_explicitly_out_of_scope():
    s = T.split_assets(EQUAL_ON_PAPER, ordinary_rate=0.24,
                       capital_gains_rate=0.15)
    scope = [f for f in s.findings if f.area == "scope"]
    assert scope and "outside this module entirely" in scope[0].detail


def test_real_estate_is_described_but_never_valued():
    m = T.transfer_mechanism("real_estate")
    assert m.known
    assert "does not value property" in m.detail


def test_no_assets_is_a_clean_gap():
    s = T.split_assets([], ordinary_rate=0.24, capital_gains_rate=0.15)
    assert s.findings[0].severity == "gap"
    assert not s.lines


# ── reference data discipline ───────────────────────────────────────────────


def test_every_table_entry_carries_a_source_and_a_verification_marker():
    for kind in T.windfall_kinds_available():
        c = T.tax_character(kind)
        assert c.source, kind
        assert c.verified_on, kind


def test_the_module_never_reads_the_clock():
    src = (Path(__file__).resolve().parents[1]
           / "lib" / "pf" / "transitions.py").read_text(encoding="utf-8")
    assert "date.today" not in src
    assert "datetime.now" not in src
