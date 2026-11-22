"""Federal return arithmetic. All figures are synthetic and checkable by hand
against the 2026 tables in lib/pf/federal_return.py."""
import copy

import pytest

from pf import federal_return as R

T26 = R.FEDERAL_TABLES[2026]
T25 = R.FEDERAL_TABLES[2025]


def w2(wages, withheld=0.0, owner="a1", employer="E", **kw):
    row = dict(employer=employer, owner=owner, wages=wages, federal_withheld=withheld,
               ss_wages=min(wages, 184_500), ss_withheld=min(wages, 184_500) * 0.062,
               medicare_wages=wages, medicare_withheld=wages * 0.0145)
    row.update(kw)
    return row


def tr(**kw):
    base = dict(tax_year=2026, filing_status="single",
                taxpayers=[{"member": "a1", "age": 40}],
                w2=[w2(100_000, 15_000)],
                prior_year={"agi": 90_000, "federal_total_tax": 12_000})
    base.update(kw)
    return base


def mfj(**kw):
    kw.setdefault("taxpayers", [{"member": "a1", "age": 40}, {"member": "a2", "age": 40}])
    return tr(filing_status="mfj", **kw)


def has(r, text):
    return any(text in f for f in r.findings)


# ── tables and brackets ──────────────────────────────────────────────────


def test_brackets_reproduce_the_rev_proc_base_amounts():
    # Rev. Proc. 2025-32 Table 1: $35,932 at $211,400; $206,583.50 at $768,700.
    assert R.regular_tax(211_400, 0, "mfj", T26) == pytest.approx(35_932)
    assert R.regular_tax(768_700, 0, "mfj", T26) == pytest.approx(206_583.50)
    assert R.regular_tax(640_600, 0, "single", T26) == pytest.approx(192_979.25)
    assert R.regular_tax(384_350, 0, "mfs", T26) == pytest.approx(103_291.75)
    assert R.regular_tax(201_750, 0, "hoh", T26) == pytest.approx(39_207)
    # Qualifying surviving spouse uses the joint table.
    assert R.regular_tax(211_400, 0, "qss", T26) == pytest.approx(35_932)


def test_2025_table_reproduces_its_rev_proc_base_amounts():
    assert R.regular_tax(751_600, 0, "mfj", T25) == pytest.approx(202_154.50)
    assert R.regular_tax(626_350, 0, "single", T25) == pytest.approx(188_769.75)


def test_unknown_year_uses_nearest_table_and_is_flagged():
    assert R.table_for(2027) == (T26, True)
    assert R.table_for(2026) == (T26, False)
    r = R.compute(tr(tax_year=2027))
    assert r.projection and has(r, "projection")


def test_bad_year_status_and_taxpayer_count_refuse():
    with pytest.raises(R.FederalReturnError):
        R.compute(tr(tax_year=None))
    with pytest.raises(R.FederalReturnError, match="filing_status"):
        R.compute(tr(filing_status="joint"))
    with pytest.raises(R.FederalReturnError, match="takes 2"):
        R.compute(tr(filing_status="mfj"))


# ── 1. wages and supplemental withholding ────────────────────────────────


def test_rsu_supplemental_withholding_shortfall_produces_balance_due():
    r = R.compute(tr(w2=[w2(200_000, 30_000, supplemental_wages=50_000)]))
    # TI 200,000 - 16,100 = 183,900; tax 17,966 + 24% x 78,200 = 36,734.
    assert r.taxable_income == pytest.approx(183_900)
    assert r.regular_tax == pytest.approx(36_734)
    assert r.refund_or_due == pytest.approx(30_000 - 36_734)
    assert r.marginal_rate == 0.24
    assert has(r, "about $1,000 of the balance due")      # 50,000 x (24% - 22%)
    assert r.additional_medicare_tax == 0                 # 200,000 is not over 200,000


def test_no_supplemental_finding_when_refund():
    r = R.compute(tr(w2=[w2(100_000, 40_000, supplemental_wages=20_000)]))
    assert r.refund_or_due > 0 and not has(r, "supplemental")


def test_unknown_wages_stop_and_list_what_is_missing():
    bad = tr(w2=[{"employer": "E", "wages": None, "federal_withheld": 1_000}])
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(bad)
    assert "w2[0].wages" in e.value.missing


def test_unknown_withholding_leaves_refund_undetermined():
    r = R.compute(tr(w2=[w2(100_000, None)]))
    assert r.refund_or_due is None and "w2[0].federal_withheld" in r.missing


def test_excess_social_security_from_two_employers_is_refundable():
    r = R.compute(tr(w2=[w2(130_000, 20_000, employer="A", ss_withheld=8_060),
                         w2(130_000, 20_000, employer="B", ss_withheld=8_060)]))
    cap = 184_500 * 0.062
    assert r.credits["excess_social_security"] == pytest.approx(16_120 - cap)


def test_elective_deferrals_over_the_limit_are_flagged():
    r = R.compute(tr(w2=[w2(100_000, 15_000, box12={"D": 26_000})]))
    assert has(r, "exceed the $24,500 limit")
    r = R.compute(tr(w2=[w2(100_000, 15_000, box12={"D": 24_500})]))
    assert not has(r, "elective deferrals")


# ── 2. interest and dividends ────────────────────────────────────────────


def test_treasury_interest_is_taxable_and_carried_for_the_state():
    r = R.compute(tr(interest=[{"payer": "T", "amount": 500, "us_treasury": 1_200,
                                "tax_exempt": 300}]))
    assert r.taxable_interest == 1_700 and r.us_treasury_interest == 1_200
    assert r.tax_exempt_interest == 300 and has(r, "exempt from state")
    assert "Schedule B" in r.forms


def test_schedule_b_not_triggered_at_or_below_1500():
    r = R.compute(tr(interest=[{"payer": "T", "amount": 1_500}]))
    assert "Schedule B" not in r.forms


def test_qualified_dividends_and_distributions_at_zero_percent():
    r = R.compute(tr(w2=[w2(40_000, 3_000)],
                     dividends=[{"payer": "F", "ordinary": 10_000, "qualified": 10_000,
                                 "capital_gain_distributions": 2_000}]))
    # TI 52,000 - 16,100 = 35,900; 12,000 preferential, 23,900 ordinary.
    assert r.taxable_income == pytest.approx(35_900)
    assert r.preferential_income == pytest.approx(12_000)
    assert r.regular_tax == pytest.approx(1_240 + 0.12 * 11_500)


def test_qualified_dividend_worksheet_15_and_20_percent_bands():
    # Single, TI 600,000 of which 100,000 preferential: 45,500 at 15%
    # (to 545,500), 54,500 at 20%.
    ordinary_tax = 58_448 + 0.35 * (500_000 - 256_225)
    assert R.regular_tax(600_000, 100_000, "single", T26) == pytest.approx(
        ordinary_tax + 0.15 * 45_500 + 0.20 * 54_500)


def test_qualified_above_ordinary_refuses():
    with pytest.raises(R.FederalReturnError, match="qualified"):
        R.compute(tr(dividends=[{"payer": "F", "ordinary": 100, "qualified": 200}]))


# ── 3. capital gains and losses ──────────────────────────────────────────


def test_netting_wash_sale_limit_and_carryover_split():
    r = R.compute(tr(capital_transactions=[
        {"description": "A", "proceeds": 6_000, "basis": 9_000, "term": "long"},
        {"description": "B", "proceeds": 4_200, "basis": 5_600, "term": "short",
         "wash_sale_disallowed": 400}],
        capital_loss_carryover={"short": 1_500, "long": 0},
        dividends=[{"payer": "F", "ordinary": 300, "qualified": 0,
                    "capital_gain_distributions": 300}]))
    # ST: -1,400 + 400 - 1,500 = -2,500. LT: -3,000 + 300 = -2,700.
    assert r.short_term_net == pytest.approx(-2_500)
    assert r.long_term_net == pytest.approx(-2_700)
    assert r.net_capital_gain_or_loss == -3_000
    # Short-term loss absorbs the $3,000 first: ST carry 0; LT carry
    # 2,700 - (3,000 - 2,500) = 2,200.
    assert r.capital_loss_carryover_to_next_year == {"short": 0.0, "long": 2_200.0}
    assert has(r, "wash sale")
    assert {"Schedule D", "Form 8949"} <= set(r.forms)


def test_carryover_worksheet_short_gain_long_loss():
    # ST +1,000, LT -6,000: deduct 3,000; LT carry 6,000 - (1,000 + 3,000).
    assert R._carryover(1_000, -6_000, 3_000, 50_000) == {"short": 0.0, "long": 2_000.0}


def test_carryover_worksheet_when_taxable_income_is_negative():
    # Taxable income -2,000 with a 3,000 loss: only 1,000 of the loss was used.
    assert R._carryover(-5_000, 0, 3_000, -2_000) == {"short": 4_000.0, "long": 0.0}


def test_mfs_loss_limit_is_1500():
    r = R.compute(tr(filing_status="mfs", capital_transactions=[
        {"description": "A", "proceeds": 0, "basis": 5_000, "term": "short"}]))
    assert r.net_capital_gain_or_loss == -1_500
    assert r.capital_loss_carryover_to_next_year["short"] == 3_500


def test_net_gain_has_no_limit_and_long_gain_is_preferential():
    r = R.compute(tr(capital_transactions=[
        {"description": "A", "proceeds": 20_000, "basis": 5_000, "term": "long"},
        {"description": "B", "proceeds": 1_000, "basis": 3_000, "term": "short"}]))
    assert r.net_capital_gain_or_loss == 13_000
    assert r.preferential_income == 13_000          # LT 15,000 less ST loss 2,000


def test_unknown_basis_stops_and_unreported_basis_is_flagged():
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(tr(capital_transactions=[
            {"description": "A", "proceeds": 1_000, "basis": None, "term": "long"}]))
    assert "capital_transactions[0].basis" in e.value.missing
    r = R.compute(tr(capital_transactions=[
        {"description": "A", "proceeds": 1_000, "basis": 500, "term": "long",
         "basis_reported": False}]))
    assert has(r, "basis was not reported")


def test_collectibles_refuse():
    with pytest.raises(R.FederalReturnError, match="collectible"):
        R.compute(tr(capital_transactions=[
            {"description": "coin", "proceeds": 1, "basis": 0, "term": "long",
             "collectible": True}]))


# ── 4. Schedule C, SE tax, QBI ───────────────────────────────────────────


def sc(net_gross, expenses=0, **kw):
    row = {"owner": "a1", "business": "Biz", "gross_receipts": net_gross,
           "expenses": {"other": expenses}, "sstb": False, "w2_wages": 0, "ubia": 0}
    row.update(kw)
    return row


def test_se_tax_threshold_400():
    r = R.compute(tr(schedule_c=[sc(433)]))      # 433 x 0.9235 = 399.9
    assert r.self_employment_tax == 0
    r = R.compute(tr(schedule_c=[sc(434)]))      # 400.8 -> taxed
    assert r.self_employment_tax == pytest.approx(434 * 0.9235 * 0.153)


def test_se_oasdi_base_reduced_by_w2_social_security_wages():
    r = R.compute(tr(w2=[w2(150_000, 25_000)], schedule_c=[sc(100_000)]))
    earnings = 92_350
    expected = (184_500 - 150_000) * 0.124 + earnings * 0.029
    assert r.self_employment_tax == pytest.approx(expected)
    assert r.adjustments["half_se_tax"] == pytest.approx(expected / 2)
    assert has(r, "count first against")


def test_w2_without_owner_on_joint_return_makes_se_tax_an_upper_bound():
    r = R.compute(mfj(w2=[w2(150_000, 25_000, owner=None)], schedule_c=[sc(100_000)]))
    assert r.self_employment_tax == pytest.approx(92_350 * 0.153)
    assert any("upper bound" in b for b in r.bounds) and "w2[0].owner" in r.missing


def test_home_office_cannot_create_a_loss_and_carries_forward():
    r = R.compute(tr(schedule_c=[sc(10_000, 9_000, home_office=3_000)]))
    assert r.schedule_c_net == 0
    assert r.carryforwards["home_office"] == {"Biz": 2_000}
    assert has(r, "carries forward")
    r = R.compute(tr(schedule_c=[sc(10_000, 9_000, home_office=3_000,
                                    home_office_method="simplified")]))
    assert r.carryforwards["home_office"] == {} and has(r, "is lost")


def test_schedule_c_loss_offsets_wages_and_gives_no_qbi():
    r = R.compute(tr(schedule_c=[sc(5_000, 8_000)]))
    assert r.schedule_c_net == -3_000 and r.self_employment_tax == 0
    assert r.qbi_deduction == 0 and r.carryforwards["qbi_loss"] == 3_000
    assert r.agi == pytest.approx(97_000)


def test_qbi_below_threshold_is_limited_by_taxable_income():
    r = R.compute(tr(w2=[], schedule_c=[sc(50_000)]))
    se = 46_175 * 0.153
    agi = 50_000 - se / 2
    ti_before = agi - 16_100
    assert r.qbi_deduction == pytest.approx(0.20 * ti_before)   # < 20% x QBI
    assert r.qbi_deduction < 0.20 * (50_000 - se / 2)
    assert "Form 8995" in r.forms


def test_qbi_above_range_non_sstb_uses_wage_limit():
    r = R.compute(tr(w2=[w2(400_000, 120_000)],
                     schedule_c=[sc(100_000, sstb=False, w2_wages=10_000, ubia=100_000)]))
    # max(50% x 10,000, 25% x 10,000 + 2.5% x 100,000) = 5,000.
    assert r.qbi_deduction == pytest.approx(5_000)
    assert "Form 8995-A" in r.forms


def test_qbi_above_range_sstb_is_zero_and_missing_fields_refuse():
    r = R.compute(tr(w2=[w2(400_000, 120_000)],
                     schedule_c=[sc(100_000, sstb=True, w2_wages=0, ubia=0)]))
    assert r.qbi_deduction == 0 and has(r, "specified service")
    with pytest.raises(R.FederalReturnError, match="sstb, w2_wages and ubia"):
        R.compute(tr(w2=[w2(400_000, 120_000)], schedule_c=[sc(100_000, sstb=None)]))


def _qbi(biz, ti, status="single"):
    return R._qbi(R._Ctx(), [biz], {}, ti, 0.0, status, T26, 0.0)


def test_qbi_phase_in_halfway_non_sstb_and_sstb():
    ti = 201_750 + 37_500                       # halfway through the $75,000 range
    biz = {"business": "X", "owner": "a1", "net": 100_000, "sstb": False,
           "w2_wages": 20_000, "ubia": 0}
    # tentative 20,000, wage limit 10,000, reduction 10,000 x 50%.
    assert _qbi(biz, ti) == (pytest.approx(15_000), 0.0)
    # SSTB: applicable 50% -> QBI 50,000, wages 10,000 -> 10,000 - 5,000 x 50%.
    assert _qbi({**biz, "sstb": True}, ti) == (pytest.approx(7_500), 0.0)


def test_qbi_minimum_deduction_2026():
    biz = {"business": "X", "owner": "a1", "net": 1_500, "sstb": False,
           "w2_wages": 0, "ubia": 0}
    assert _qbi(biz, 1_000_000)[0] == 400           # wage limit 0 -> minimum
    assert R._qbi(R._Ctx(), [biz], {}, 1_000_000, 0.0, "single", T25, 0.0)[0] == 0


def test_excess_business_loss_refuses():
    with pytest.raises(R.FederalReturnError, match="excess business loss"):
        R.compute(tr(schedule_c=[sc(0, 300_000)]))


# ── 5. HSA ───────────────────────────────────────────────────────────────


def test_hsa_deduction_net_of_employer_and_excess_flagged():
    r = R.compute(tr(hsa={"contributions_personal": 6_000, "employer_contributions": 3_000,
                          "coverage": "family"}))
    assert r.adjustments["hsa_deduction"] == 5_750        # 8,750 - 3,000
    assert has(r, "by $250")


def test_hsa_self_limit_with_catch_up_and_box12_fallback():
    r = R.compute(tr(taxpayers=[{"member": "a1", "age": 56}],
                     w2=[w2(100_000, 15_000, box12={"W": 1_000})],
                     hsa={"contributions_personal": 4_400, "coverage": "self"}))
    assert r.adjustments["hsa_deduction"] == 4_400        # 4,400 + 1,000 - 1,000
    assert not has(r, "exceed the")


def test_hsa_unknown_coverage_is_a_bound_and_nonqualified_distribution_taxed():
    r = R.compute(tr(hsa={"contributions_personal": 3_000, "coverage": None}))
    assert r.adjustments["hsa_deduction"] == 0 and "hsa.coverage" in r.missing
    r = R.compute(tr(hsa={"contributions_personal": 0, "coverage": "self",
                          "distributions": 2_000, "qualified_expenses": 500}))
    assert r.hsa_taxable_distributions == 1_500
    assert r.other_taxes["hsa_additional_tax"] == pytest.approx(300)


# ── 6. backdoor Roth / Form 8606 ─────────────────────────────────────────


def ira(**kw):
    row = dict(owner="a1", traditional_contributions=7_000, deductible=False,
               nondeductible_basis_prior=0, conversions_to_roth=7_000,
               year_end_traditional_balance=0)
    row.update(kw)
    return row


def test_clean_backdoor_is_not_taxable():
    r = R.compute(tr(ira=[ira()]))
    assert r.ira_taxable == 0 and "Form 8606" in r.forms
    assert not has(r, "pro-rata")


def test_pro_rata_uses_year_end_balance():
    r = R.compute(tr(ira=[ira(year_end_traditional_balance=63_000)]))
    # basis 7,000 / (63,000 + 7,000) = 10% nontaxable.
    assert r.ira_taxable == pytest.approx(6_300)
    assert r.carryforwards["ira_basis"] == {"a1": pytest.approx(6_300)}
    assert has(r, "pro-rata")


def test_unknown_year_end_balance_stops():
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(tr(ira=[ira(year_end_traditional_balance=None)]))
    assert "ira[0].year_end_traditional_balance" in e.value.missing


def test_ira_over_the_contribution_limit_is_flagged():
    r = R.compute(tr(ira=[ira(traditional_contributions=8_000, conversions_to_roth=8_000)]))
    assert has(r, "exceed the $7,500 limit")


# ── 7. itemized vs standard ──────────────────────────────────────────────


def test_itemized_components_reuse_cashflow_rules():
    r = R.compute(mfj(w2=[w2(300_000, 60_000)], state_income_tax_paid=25_000,
                      itemized={"property_tax": 20_000, "mortgage_interest": 30_000,
                                "mortgage_balance": 900_000, "charitable_cash": 10_000}))
    assert r.itemized["salt_allowed"] == 40_400
    assert r.itemized["mortgage_interest"] == pytest.approx(25_000)   # x 750/900
    assert r.itemized["charitable"] == pytest.approx(10_000 - 0.005 * 300_000)
    assert r.itemizes and r.itemized_total == pytest.approx(40_400 + 25_000 + 8_500)
    assert "Schedule A" in r.forms


def test_salt_cap_phases_down_to_the_floor():
    rules = R.itemized_rules("mfj", T26)
    assert rules.effective_salt_cap(605_000) == pytest.approx(10_400)
    assert rules.effective_salt_cap(700_000) == 10_000
    assert R.itemized_rules("mfs", T26).effective_salt_cap(100_000) == 20_200


def test_two_thirty_sevenths_limitation():
    r = R.compute(mfj(w2=[w2(900_000, 250_000)], state_income_tax_paid=50_000,
                      itemized={"mortgage_interest": 20_000, "mortgage_balance": 500_000,
                                "charitable_cash": 50_000}))
    gross = 10_000 + 20_000 + (50_000 - 4_500)
    reduction = 2 / 37 * min(gross, 900_000 - 768_700)
    assert r.itemized_total == pytest.approx(gross - reduction)
    assert has(r, "2/37")


def test_additional_standard_deduction_and_senior_deduction():
    old = [{"member": "a1", "age": 66}, {"member": "a2", "age": 66}]
    r = R.compute(mfj(taxpayers=old, w2=[w2(160_000, 20_000)]))
    assert r.standard_deduction == 32_200 + 2 * 1_650
    assert r.senior_deduction == pytest.approx(2 * (6_000 - 0.06 * 10_000))
    r = R.compute(tr(taxpayers=[{"member": "a1", "age": 65, "blind": True}]))
    assert r.standard_deduction == 16_100 + 2 * 2_050
    r = R.compute(tr(filing_status="mfs", taxpayers=[{"member": "a1", "age": 70}]))
    assert r.senior_deduction == 0 and has(r, "not available")


def test_nonitemizer_charitable_deduction_2026_only():
    r = R.compute(tr(itemized={"charitable_cash": 3_000}))
    assert not r.itemizes and r.nonitemizer_charitable == 1_000
    assert r.deduction_used == 17_100
    r = R.compute(tr(tax_year=2025, itemized={"charitable_cash": 3_000}))
    assert r.nonitemizer_charitable == 0 and r.standard_deduction == 15_750


def test_state_tax_defaults_to_withholding_plus_state_estimates():
    r = R.compute(tr(w2=[w2(100_000, 15_000, state_withheld=4_000, sdi_withheld=900)],
                     estimated_payments={"federal": [0, 0, 0, 0],
                                         "state": [500, 500, 0, 0]}))
    assert r.itemized["state_income_tax"] == 4_000 + 1_000 + 900


def test_mortgage_interest_without_balance_refuses():
    with pytest.raises(R.FederalReturnError, match="mortgage_balance"):
        R.compute(tr(itemized={"mortgage_interest": 10_000}))


def test_unknown_itemized_amount_is_a_bound_not_zero():
    r = R.compute(tr(itemized={"property_tax": None, "charitable_cash": 500}))
    assert "itemized.property_tax" in r.missing
    assert any("lower bound" in b for b in r.bounds)


# ── 8. credits ───────────────────────────────────────────────────────────


KIDS = [{"member": "c1", "age": 8, "months_lived": 12},
        {"member": "c2", "age": 5, "months_lived": 12}]


def test_ctc_phase_out_rounds_up_per_thousand():
    r = R.compute(mfj(w2=[w2(410_500, 100_000)], dependents=KIDS))
    # 10,500 over -> 11 steps x $50 = 550.
    assert r.credits["child_and_other_dependent_credit"] == pytest.approx(4_400 - 550)
    assert has(r, "reduced by $550")


def test_other_dependents_and_months_lived():
    deps = [{"member": "c1", "age": 17, "months_lived": 12, "student": True},
            {"member": "c2", "age": 10, "months_lived": 5}]
    r = R.compute(tr(filing_status="hoh", dependents=deps))
    assert r.credits["child_and_other_dependent_credit"] == 1_000
    assert has(r, "residency test")


def test_refundable_actc_capped_per_child():
    r = R.compute(mfj(w2=[w2(30_000, 0)], dependents=KIDS))
    assert r.regular_tax == 0
    # min(unused 4,400, 2 x 1,700, 15% x 27,500 = 4,125) = 3,400.
    assert r.credits["additional_child_tax_credit"] == pytest.approx(3_400)
    assert r.refund_or_due == pytest.approx(3_400)


def test_simplified_foreign_tax_credit():
    r = R.compute(tr(dividends=[{"payer": "F", "ordinary": 2_000, "qualified": 2_000,
                                 "foreign_tax_paid": 250}]))
    assert r.credits["foreign_tax_credit"] == 250 and "Form 1116" not in r.forms


def test_form_1116_limitation_and_carryover():
    r = R.compute(tr(foreign={"interest": 20_000, "foreign_tax_paid": {"passive": 5_000},
                              "country": "IN", "category": "passive"}))
    ti = 120_000 - 16_100
    reg = 5_800 + 0.22 * (ti - 50_400)
    foreign_taxable = 20_000 - 16_100 * 20_000 / 120_000
    limit = reg * foreign_taxable / ti
    assert r.credits["foreign_tax_credit"] == pytest.approx(limit)
    assert r.carryforwards["foreign_tax_credit"] == pytest.approx(5_000 - limit)
    assert "Form 1116" in r.forms and has(r, "FBAR")


def test_foreign_general_category_refuses():
    with pytest.raises(R.FederalReturnError, match="feie-vs-ftc"):
        R.compute(tr(foreign={"interest": 1_000, "foreign_tax_paid": 0,
                              "category": "general"}))


# ── 9-10. NIIT and Additional Medicare ───────────────────────────────────


def test_niit_on_lesser_of_nii_and_magi_excess():
    r = R.compute(tr(w2=[w2(190_000, 40_000)],
                     interest=[{"payer": "B", "amount": 30_000}]))
    assert r.niit == pytest.approx(0.038 * 20_000)
    r = R.compute(tr(w2=[w2(150_000, 40_000)],
                     interest=[{"payer": "B", "amount": 30_000}]))
    assert r.niit == 0


def test_additional_medicare_two_earners_under_withheld():
    r = R.compute(mfj(w2=[w2(150_000, 25_000, owner="a1"),
                          w2(150_000, 25_000, owner="a2")]))
    assert r.additional_medicare_tax == pytest.approx(0.009 * 50_000)
    assert r.withholding["additional_medicare_withheld"] == 0
    assert has(r, "under-withheld")


def test_additional_medicare_one_earner_over_withheld_is_credited():
    wages = 300_000
    row = w2(wages, 60_000, medicare_withheld=wages * 0.0145 + 100_000 * 0.009)
    r = R.compute(mfj(w2=[row]))
    assert r.additional_medicare_tax == pytest.approx(450)
    assert r.withholding["additional_medicare_withheld"] == pytest.approx(900)
    assert has(r, "over-withheld")


def test_additional_medicare_on_se_income_uses_reduced_threshold():
    r = R.compute(tr(w2=[w2(150_000, 30_000)], schedule_c=[sc(100_000)]))
    assert r.additional_medicare_tax == pytest.approx(0.009 * (92_350 - 50_000))


# ── 11. AMT ──────────────────────────────────────────────────────────────


def test_amt_exemption_phase_out_and_rates():
    a = R.amt(600_000, 0, 0, 100_000, "single", T26)
    assert a["exemption"] == pytest.approx(90_100 - 0.5 * 100_000)
    assert a["tentative_minimum_tax"] == pytest.approx(
        0.26 * 244_500 + 0.28 * (559_900 - 244_500))
    assert a["amt"] == pytest.approx(a["tentative_minimum_tax"] - 100_000)


def test_amt_preferential_income_keeps_capital_gain_rates():
    # 200,000 AMT base, all LTCG, regular ordinary income 0: the 0% band
    # (49,450) and 15% on the rest, below the flat 26%.
    a = R.amt(290_100, 200_000, 0, 0, "single", T26)
    assert a["tentative_minimum_tax"] == pytest.approx(0.15 * (200_000 - 49_450))


def test_typical_wage_return_has_no_amt_and_iso_refuses():
    r = R.compute(mfj(w2=[w2(400_000, 90_000)], state_income_tax_paid=60_000))
    assert r.amt == 0 and r.itemized["salt_allowed"] == 40_400
    with pytest.raises(R.FederalReturnError, match="ISO"):
        R.compute(tr(iso_exercises=[{"spread": 50_000}]))


# ── 12. payments and penalty ─────────────────────────────────────────────


def test_safe_harbor_missed_with_prior_year_100_percent():
    r = R.compute(tr(w2=[w2(100_000, 5_000)],
                     prior_year={"agi": 100_000, "federal_total_tax": 10_000},
                     estimated_payments={"federal": [0, 0, 0, 0]}))
    h = r.penalty_safe_harbor
    assert h["prior_year_pct"] == 1.0 and h["required_annual"] == 10_000
    assert h["met"] is False and "Form 2210" in r.forms
    assert h["quarters"][0]["shortfall"] == pytest.approx(2_500 - 1_250)


def test_safe_harbor_uses_110_percent_above_150k_prior_agi():
    r = R.compute(tr(prior_year={"agi": 200_000, "federal_total_tax": 10_000}))
    assert r.penalty_safe_harbor["prior_year_required"] == pytest.approx(11_000)


def test_under_1000_owed_is_no_penalty():
    r = R.compute(tr(w2=[w2(100_000, 13_000)],
                     prior_year={"agi": 100_000, "federal_total_tax": 50_000}))
    assert r.total_tax - 13_000 < 1_000
    assert r.penalty_safe_harbor["met"] is True


def test_prior_year_unknown_uses_only_90_percent_and_is_listed():
    r = R.compute(tr(w2=[w2(100_000, 0)], prior_year={}))
    assert "prior_year.federal_total_tax" in r.missing
    assert r.penalty_safe_harbor["required_annual"] == pytest.approx(0.9 * r.total_tax)


def test_estimates_by_quarter_and_next_year_suggestion():
    r = R.compute(tr(w2=[w2(200_000, 20_000)],
                     estimated_payments={"federal": [4_000, 4_000, 4_000, 4_000]},
                     prior_year={"agi": 160_000, "federal_total_tax": 30_000}))
    assert r.estimated_payments == 16_000
    assert r.total_payments == pytest.approx(36_000)
    ny = r.next_year_estimates
    assert ny["basis_pct"] == 1.10
    assert ny["quarterly"] == pytest.approx((1.10 * r.total_tax - 20_000) / 4)


def test_unknown_estimate_quarter_leaves_refund_undetermined():
    r = R.compute(tr(estimated_payments={"federal": [1_000, None, 0, 0]}))
    assert r.refund_or_due is None and r.penalty_safe_harbor["met"] is None


# ── out of scope ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("key,pointer", [
    ("schedule_k1", "passive-loss-eligibility"),
    ("rental_properties", "passive-loss-eligibility"),
    ("pfic", "pfic-divest-or-comply"),
    ("depreciation", "depreciation-election"),
])
def test_out_of_scope_items_refuse_with_a_pointer(key, pointer):
    with pytest.raises(R.FederalReturnError, match=pointer):
        R.compute(tr(**{key: [{"x": 1}]}))


def test_nonresident_refuses_and_kiddie_tax_is_flagged():
    with pytest.raises(R.FederalReturnError, match="nonresident"):
        R.compute(tr(residency="nonresident"))
    r = R.compute(tr(filing_status="hoh",
                     dependents=[{"member": "c1", "age": 12, "months_lived": 12,
                                  "unearned_income": 4_000}]))
    assert has(r, "Form 8615")


def test_null_section_is_unknown_not_empty():
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(tr(interest=None))
    assert any(m.startswith("interest") for m in e.value.missing)


def test_compute_does_not_mutate_its_input():
    t = tr(ira=[ira()], schedule_c=[sc(10_000)])
    before = copy.deepcopy(t)
    R.compute(t)
    assert t == before


def test_total_tax_identity():
    r = R.compute(mfj(w2=[w2(250_000, 40_000)], dependents=KIDS,
                      interest=[{"payer": "B", "amount": 5_000}],
                      schedule_c=[sc(40_000)]))
    nonref = (r.credits.get("foreign_tax_credit", 0)
              + r.credits.get("child_and_other_dependent_credit", 0))
    assert r.total_tax == pytest.approx(
        r.regular_tax + r.amt - nonref + sum(r.other_taxes.values()))
    assert r.agi == pytest.approx(r.total_income - sum(r.adjustments.values()))


# ── Social Security benefits (line 6b) ───────────────────────────────────


def ssa(net, withheld=0):
    return [{"recipient": "a1", "net_benefits": net, "federal_withheld": withheld}]


def test_social_security_worksheet_both_tiers_single():
    # Provisional 15,000 + 20,000 = 35,000; 10,000 over 25,000; 1,000 over
    # 34,000. Taxable = min(15,000, 4,500) + 85% x 1,000 = 5,350.
    r = R.compute(tr(w2=[], interest=[{"payer": "B", "amount": 20_000}],
                     social_security_benefits=ssa(30_000)))
    assert r.taxable_social_security == pytest.approx(5_350)
    assert r.total_income == pytest.approx(25_350)
    assert "Form SSA-1099 — a1" in r.documents


def test_social_security_below_base_is_untaxed():
    r = R.compute(tr(w2=[], interest=[{"payer": "B", "amount": 10_000}],
                     social_security_benefits=ssa(20_000)))
    assert r.taxable_social_security == 0


def test_social_security_capped_at_85_percent_and_withholding_counts():
    r = R.compute(mfj(w2=[w2(200_000, 30_000)],
                      social_security_benefits=ssa(40_000, withheld=4_000)))
    assert r.taxable_social_security == pytest.approx(34_000)
    assert r.withholding["ssa_1099_federal"] == 4_000
    assert r.withholding["total"] == pytest.approx(34_000)


def test_social_security_mfs_living_together_has_zero_base():
    t = tr(filing_status="mfs", w2=[], interest=[{"payer": "B", "amount": 1_000}],
           social_security_benefits=ssa(10_000))
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(t)
    assert "mfs_lived_apart_all_year" in e.value.missing
    r = R.compute({**t, "mfs_lived_apart_all_year": False})
    assert r.taxable_social_security == pytest.approx(0.85 * 6_000)
    r = R.compute({**t, "mfs_lived_apart_all_year": True})
    assert r.taxable_social_security == 0


def test_social_security_unknown_or_with_deductible_ira_refuses():
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(tr(social_security_benefits=ssa(None)))
    assert "social_security_benefits[0].net_benefits" in e.value.missing
    with pytest.raises(R.FederalReturnError, match="590-A"):
        R.compute(tr(social_security_benefits=ssa(20_000),
                     ira=[ira(deductible=True, conversions_to_roth=0)]))


def test_social_security_worksheet_function_adjustments_wipe_out_provisional():
    assert R.taxable_social_security(10_000, 1_000, 0, 7_000, "other") == 0


# ── state/local refund (tax-benefit rule) ────────────────────────────────


def test_state_refund_after_standard_deduction_is_not_taxable():
    r = R.compute(tr(prior_year={"agi": 90_000, "federal_total_tax": 12_000,
                                 "state_refund_received": 2_000, "itemized_prior": False}))
    assert r.state_refund_taxable == 0 and has(r, "none of it is")


def test_state_refund_limited_by_itemized_excess():
    py = {"agi": 90_000, "federal_total_tax": 12_000, "state_refund_received": 2_000,
          "itemized_prior": True, "itemized_deduction_prior": 30_000,
          "standard_deduction_prior": 29_200, "salt_paid_prior": 8_000,
          "salt_deducted_prior": 8_000}
    r = R.compute(tr(prior_year=py))
    assert r.state_refund_taxable == 800
    assert r.agi == pytest.approx(100_800) and "Schedule 1" in r.forms


def test_state_refund_limited_by_the_salt_cap():
    # Paid 15,000, deducted 10,000 (capped): a 3,000 refund still leaves
    # 12,000 paid, above the cap — none of it is taxable.
    kw = dict(itemized_prior=True, itemized_deduction_prior=40_000,
              standard_deduction_prior=29_200, salt_deducted_prior=10_000)
    assert R.state_refund_taxable(3_000, salt_paid_prior=15_000, **kw) == 0
    # Paid 11,000: net 8,000 is 2,000 below the 10,000 deducted.
    assert R.state_refund_taxable(3_000, salt_paid_prior=11_000, **kw) == 2_000


def test_state_refund_unknowns_stop_and_absent_is_zero():
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(tr(prior_year={"state_refund_received": None}))
    assert "prior_year.state_refund_received" in e.value.missing
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(tr(prior_year={"state_refund_received": 1_000}))
    assert "prior_year.itemized_prior" in e.value.missing
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(tr(prior_year={"state_refund_received": 1_000, "itemized_prior": True}))
    assert "prior_year.salt_paid_prior" in e.value.missing
    assert R.compute(tr()).state_refund_taxable == 0


# ── K-1s (Schedule E part II) ────────────────────────────────────────────


def k1(**kw):
    row = dict(entity="Partners LLC", form="1065", ordinary_business_income=60_000,
               guaranteed_payments=20_000, se_earnings=80_000, interest=1_000,
               dividends=500, distributions=30_000, qbi_income=60_000,
               qbi_w2_wages=0, qbi_ubia=0, sstb=False, material_participation=True)
    row.update(kw)
    return row


def test_partnership_k1_flows_to_income_se_and_qbi():
    r = R.compute(tr(k1=[k1()]))
    assert r.k1_income == 80_000
    assert r.taxable_interest == 1_000 and r.ordinary_dividends == 500
    assert r.total_income == pytest.approx(100_000 + 1_000 + 500 + 80_000)
    earnings = 80_000 * 0.9235                     # W-2 SS wages 100,000 leave
    assert r.self_employment_tax == pytest.approx(earnings * 0.153)   # 84,500 of base
    # QBI 60,000 less the half SE tax its 60,000 of the 80,000 SE income produced.
    half = earnings * 0.153 / 2
    assert r.qbi_deduction == pytest.approx(0.20 * (60_000 - half * 0.75))
    assert {"Schedule E", "Schedule SE", "Schedule 1"} <= set(r.forms)
    assert has(r, "informational") and has(r, "taxed as ordinary")
    assert "Schedule K-1 (1065) — Partners LLC" in r.documents


def test_partnership_se_coordinates_with_w2_wage_base():
    r = R.compute(tr(w2=[w2(150_000, 25_000)],
                     k1=[k1(ordinary_business_income=100_000, guaranteed_payments=0,
                            se_earnings=100_000, qbi_income=100_000,
                            interest=0, dividends=0, distributions=0)]))
    assert r.self_employment_tax == pytest.approx(
        (184_500 - 150_000) * 0.124 + 92_350 * 0.029)


def test_s_corp_k1_has_no_se_tax_and_no_guaranteed_payments():
    r = R.compute(tr(k1=[k1(form="1120S", guaranteed_payments=0, se_earnings=50_000)]))
    assert r.self_employment_tax == 0 and has(r, "not self-employment income")
    assert r.k1_income == 60_000
    with pytest.raises(R.FederalReturnError, match="guaranteed payments"):
        R.compute(tr(k1=[k1(form="1120S")]))


def test_k1_qbi_wage_limit_above_threshold_and_refusal_without_it():
    s_corp = k1(form="1120S", guaranteed_payments=0, se_earnings=0,
                ordinary_business_income=100_000, qbi_income=100_000,
                qbi_w2_wages=30_000, qbi_ubia=0, interest=0, dividends=0)
    r = R.compute(tr(w2=[w2(400_000, 120_000)], k1=[s_corp]))
    assert r.qbi_deduction == pytest.approx(15_000)     # 50% x 30,000 < 20,000
    with pytest.raises(R.FederalReturnError, match="qbi_w2_wages"):
        R.compute(tr(w2=[w2(400_000, 120_000)], k1=[{**s_corp, "qbi_w2_wages": None}]))


def test_passive_and_unknown_participation():
    with pytest.raises(R.FederalReturnError, match="passive-loss-eligibility"):
        R.compute(tr(k1=[k1(material_participation=False)]))
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(tr(k1=[k1(material_participation=None)]))
    assert "k1[0].material_participation" in e.value.missing


@pytest.mark.parametrize("extra", [{"rental_real_estate": 5_000},
                                   {"section_179": 1_000},
                                   {"other_codes": {"L": 200}}])
def test_k1_rental_179_and_other_codes_refuse(extra):
    with pytest.raises(R.FederalReturnError, match="not modelled"):
        R.compute(tr(k1=[k1(**extra)]))


def test_k1_trust_form_refuses_and_null_figure_stops():
    with pytest.raises(R.FederalReturnError, match="1065 and 1120S"):
        R.compute(tr(k1=[k1(form="1041")]))
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(tr(k1=[k1(ordinary_business_income=None)]))
    assert "k1[0].ordinary_business_income" in e.value.missing


def test_k1_without_owner_on_joint_return_bounds_se_tax():
    r = R.compute(mfj(w2=[w2(150_000, 25_000, owner="a1")], k1=[k1()]))
    assert "k1[0].owner" in r.missing
    assert any("upper bound" in b for b in r.bounds)
    assert r.self_employment_tax == pytest.approx(80_000 * 0.9235 * 0.153)


def test_k1_loss_offsets_income_with_basis_caveat_and_counts_toward_ebl():
    r = R.compute(tr(k1=[k1(ordinary_business_income=-20_000, guaranteed_payments=0,
                            se_earnings=-20_000, qbi_income=-20_000,
                            interest=0, dividends=0, distributions=0)]))
    assert r.k1_income == -20_000 and r.self_employment_tax == 0
    assert r.carryforwards["qbi_loss"] == 20_000 and has(r, "basis and at-risk")
    with pytest.raises(R.FederalReturnError, match="excess business loss"):
        R.compute(tr(k1=[k1(ordinary_business_income=-300_000, se_earnings=0,
                            qbi_income=-300_000)]))


# ── adversarial-review fixes ─────────────────────────────────────────────


def test_h1_form_8606_aggregates_entries_per_owner():
    # Two accounts, one owner: basis 12,500 / (92,500 + 7,500) = 12.5%.
    r = R.compute(tr(ira=[ira(traditional_contributions=7_500, conversions_to_roth=7_500),
                          ira(traditional_contributions=0, nondeductible_basis_prior=5_000,
                              conversions_to_roth=0, year_end_traditional_balance=92_500)]))
    assert r.ira_taxable == pytest.approx(6_562.50)
    assert r.carryforwards["ira_basis"] == {"a1": pytest.approx(11_562.50)}


def test_h1_basis_on_two_entries_is_ambiguous_and_balance_required_on_each():
    with pytest.raises(R.FederalReturnError, match="more than one"):
        R.compute(tr(ira=[ira(nondeductible_basis_prior=1_000),
                          ira(nondeductible_basis_prior=1_000, conversions_to_roth=0)]))
    second = ira(traditional_contributions=0, conversions_to_roth=0)
    del second["year_end_traditional_balance"]
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(tr(ira=[ira(), second]))
    assert "ira[1].year_end_traditional_balance" in e.value.missing


def test_h2_de_minimis_ignores_estimated_payments():
    r = R.compute(tr(w2=[w2(200_000, 20_000)],
                     prior_year={"agi": 100_000, "federal_total_tax": 40_000},
                     estimated_payments={"federal": [0, 0, 0, 16_234]}))
    h = r.penalty_safe_harbor
    assert h["owed_after_withholding"] >= 1_000
    assert h["met"] is False and "Apr 15" in h["reason"]


def test_h3_foreign_interest_and_dividends_route_to_their_lines():
    r = R.compute(tr(foreign={"country": "IN", "interest": 700, "dividends": 400,
                              "qualified_dividends": 300, "foreign_tax_paid": {"passive": 0}}))
    assert r.taxable_interest == 700 and r.ordinary_dividends == 400
    assert r.qualified_dividends == 300 and r.foreign_income == 1_100
    assert "Schedule B" in r.forms and has(r, "Part III")    # below $1,500, still B


def test_h3_schedule_b_part_iii_for_accounts_alone():
    r = R.compute(tr(foreign={"country": "IN", "accounts": True}))
    assert "Schedule B" in r.forms


def test_h3_foreign_gain_is_taxed_at_capital_gain_rates():
    sale = {"description": "foreign lot", "proceeds": 30_000, "basis": 10_000,
            "term": "long"}
    foreign = R.compute(tr(foreign={"country": "IN", "capital_transactions": [sale]}))
    domestic = R.compute(tr(capital_transactions=[sale]))
    assert foreign.regular_tax == pytest.approx(domestic.regular_tax)
    assert foreign.preferential_income == 20_000 and "Form 8949" in foreign.forms


def test_h3_form_1116_capital_gain_rate_adjustment():
    sale = {"description": "foreign lot", "proceeds": 30_000, "basis": 10_000,
            "term": "long"}
    r = R.compute(tr(foreign={"country": "IN", "capital_transactions": [sale],
                              "foreign_tax_paid": {"passive": 3_000}}))
    f = 0.15 / 0.37
    ti = 120_000 - 16_100
    reg = 5_800 + 0.22 * (ti - 20_000 - 50_400) + 0.15 * 20_000
    num = 20_000 * f - 16_100 * 20_000 / 120_000
    den = ti - 20_000 * (1 - f)
    assert r.regular_tax == pytest.approx(reg)
    assert r.credits["foreign_tax_credit"] == pytest.approx(reg * num / den)
    assert has(r, "rate adjustment")


@pytest.mark.parametrize("bad,match", [
    ({"income": 1_000}, "Split it"),
    ({"rent": 5_000}, "passive-loss-eligibility"),
    ({"insurance_maturity": 9_000}, "only foreign interest"),
    ({"foreign_tax_paid": {"passive": 0, "general": 100}}, "feie-vs-ftc"),
    ({"capital_transactions": [{"description": "MF", "proceeds": 1, "basis": 0,
                                "term": "long", "pfic": True}]}, "pfic"),
])
def test_h3_unrouteable_foreign_items_refuse(bad, match):
    with pytest.raises(R.FederalReturnError, match=match):
        R.compute(tr(foreign={"country": "IN", **bad}))


@pytest.mark.parametrize("section", ["capital_loss_carryover", "hsa", "foreign"])
def test_m1_null_section_that_determines_tax_stops(section):
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(tr(**{section: None}))
    assert any(m.startswith(section) for m in e.value.missing)


def test_m1_null_payment_and_deduction_sections_are_bounds():
    r = R.compute(tr(estimated_payments=None))
    assert r.refund_or_due is None and any("estimated_payments" in m for m in r.missing)
    r = R.compute(tr(itemized=None))
    assert any("itemized" in m for m in r.missing) and any("lower bound" in b for b in r.bounds)
    r = R.compute(tr(filing_status="hoh", dependents=None))
    assert any("dependents" in m for m in r.missing) and "child_and_other_dependent_credit" not in r.credits


def test_m2_null_qbi_loss_carryforward_stops():
    with pytest.raises(R.FederalReturnError) as e:
        R.compute(tr(schedule_c=[sc(50_000)], qbi_loss_carryforward=None))
    assert "qbi_loss_carryforward" in e.value.missing


def test_m3_child_born_in_year_qualifies():
    baby = [{"member": "c1", "age": 0, "months_lived": 2, "born_or_died_in_year": True,
             "months_alive": 2}]
    r = R.compute(mfj(w2=[w2(120_000, 15_000)], dependents=baby))
    assert r.credits["child_and_other_dependent_credit"] == 2_200
    unknown = [{**baby[0], "months_alive": None}]
    r = R.compute(mfj(w2=[w2(120_000, 15_000)], dependents=unknown))
    assert "dependents[0].months_alive" in r.missing


def test_m4_itemizing_must_beat_standard_plus_170p():
    r = R.compute(mfj(w2=[w2(150_000, 20_000)], state_income_tax_paid=0,
                      itemized={"property_tax": 20_000, "mortgage_interest": 10_000,
                                "mortgage_balance": 300_000, "charitable_cash": 4_000}))
    # itemized 20,000 + 10,000 + (4,000 - 750) = 33,250 < 32,200 + 2,000.
    assert not r.itemizes and r.deduction_used == 34_200


def test_m5_charitable_agi_limits_and_carryforward():
    r = R.compute(tr(itemized={"charitable_cash": 90_000}))
    agi = 100_000
    assert r.itemized["charitable"] == pytest.approx(0.60 * agi - 0.005 * agi)
    assert r.carryforwards["charitable"] == pytest.approx(30_000)
    r = R.compute(tr(itemized={"charitable_noncash": 50_000}))
    assert r.itemized["charitable"] == pytest.approx(0.30 * agi - 0.005 * agi)


def test_m6_hsa_catch_up_self_coverage_belongs_to_owner_only():
    both55 = [{"member": "a1", "age": 56}, {"member": "a2", "age": 57}]
    r = R.compute(mfj(taxpayers=both55,
                      hsa={"owner": "a1", "coverage": "self", "contributions_personal": 6_400}))
    assert r.adjustments["hsa_deduction"] == 5_400
    r = R.compute(mfj(taxpayers=both55,
                      hsa={"owner": "a1", "coverage": "family", "contributions_personal": 10_750}))
    assert r.adjustments["hsa_deduction"] == 10_750      # 8,750 + 2 x 1,000


def test_m6_hsa_additional_tax_follows_account_owner_and_months_prorate():
    tps = [{"member": "a1", "age": 67}, {"member": "a2", "age": 50}]
    r = R.compute(mfj(taxpayers=tps, hsa={"owner": "a1", "coverage": "self",
                                         "distributions": 10_000, "qualified_expenses": 0}))
    assert r.other_taxes["hsa_additional_tax"] == 0
    r = R.compute(tr(hsa={"coverage": "self", "contributions_personal": 4_400,
                          "eligible_months": 6}))
    assert r.adjustments["hsa_deduction"] == pytest.approx(2_200)


def test_m7_senior_deduction_added_back_for_amt(monkeypatch):
    seen = {}
    real = R.amt

    def spy(amti, *a, **k):
        seen["amti"] = amti
        return real(amti, *a, **k)
    monkeypatch.setattr(R, "amt", spy)
    r = R.compute(mfj(taxpayers=[{"member": "a1", "age": 66}, {"member": "a2", "age": 66}],
                      w2=[w2(100_000, 10_000)]))
    assert r.senior_deduction == 12_000
    assert seen["amti"] == pytest.approx(r.taxable_income + r.standard_deduction + 12_000)


def test_m8_ira_deduction_phases_out_for_covered_worker():
    covered = [{"member": "a1", "age": 40, "covered_by_workplace_plan": True}]
    r = R.compute(tr(taxpayers=covered, w2=[w2(400_000, 100_000)],
                     ira=[ira(deductible=True, conversions_to_roth=0)]))
    assert r.adjustments["ira_deduction"] == 0
    assert r.carryforwards["ira_basis"] == {"a1": 7_000}
    # MAGI 86,000 in the 81,000-91,000 range: 7,500 x 5,000/10,000 = 3,750.
    r = R.compute(tr(taxpayers=covered, w2=[w2(86_000, 10_000)],
                     ira=[ira(deductible=True, traditional_contributions=7_500,
                              conversions_to_roth=0)]))
    assert r.adjustments["ira_deduction"] == 3_750
    # Not covered, single: full deduction.
    r = R.compute(tr(taxpayers=[{"member": "a1", "age": 40, "covered_by_workplace_plan": False}],
                     w2=[w2(400_000, 100_000)], ira=[ira(deductible=True, conversions_to_roth=0)]))
    assert r.adjustments["ira_deduction"] == 7_000


def test_m8_unknown_coverage_is_missing_and_box12_d_proves_coverage():
    r = R.compute(tr(ira=[ira(deductible=True, conversions_to_roth=0)]))
    assert r.adjustments["ira_deduction"] == 0
    assert any("covered_by_workplace_plan" in m for m in r.missing)
    r = R.compute(tr(w2=[w2(100_000, 15_000, box12={"D": 5_000})],
                     ira=[ira(deductible=True, conversions_to_roth=0)]))
    assert r.adjustments["ira_deduction"] == 0           # covered, above 91,000
    assert not any("covered_by_workplace_plan" in m for m in r.missing)


def test_m8_spouse_covered_range():
    tps = [{"member": "a1", "age": 40, "covered_by_workplace_plan": False},
           {"member": "a2", "age": 40, "covered_by_workplace_plan": True}]
    r = R.compute(mfj(taxpayers=tps, w2=[w2(247_000, 40_000, owner="a2")],
                      ira=[ira(owner="a1", deductible=True, traditional_contributions=7_500,
                               conversions_to_roth=0)]))
    assert r.adjustments["ira_deduction"] == 3_750       # halfway 242k-252k


def test_low_malformed_input_is_a_clean_error_and_estimates_capped():
    with pytest.raises(R.FederalReturnError):
        R.compute(tr(estimated_payments={"federal": 4_000}))
    with pytest.raises(R.FederalReturnError, match="at most 4"):
        R.compute(tr(estimated_payments={"federal": [1, 1, 1, 1, 1]}))
    with pytest.raises(R.FederalReturnError):
        R.compute(tr(capital_loss_carryover=3_000))
    with pytest.raises(R.FederalReturnError):
        R.compute(tr(prior_year={"agi": "lots", "federal_total_tax": 1}))
    with pytest.raises(R.FederalReturnError):
        R.compute(tr(taxpayers=["a1"]))


def test_low_excess_ss_needs_different_employers():
    r = R.compute(tr(w2=[w2(130_000, 20_000, employer="A", ss_withheld=8_060),
                         w2(130_000, 20_000, employer="A", ss_withheld=8_060)]))
    assert "excess_social_security" not in r.credits and has(r, "employer must refund")


def test_low_unsupported_1099_div_boxes_and_ira_distributions_refuse():
    with pytest.raises(R.FederalReturnError, match="REIT"):
        R.compute(tr(dividends=[{"payer": "R", "ordinary": 100,
                                 "section_199a_dividends": 100}]))
    with pytest.raises(R.FederalReturnError, match="1099-R"):
        R.compute(tr(ira=[ira(distributions=5_000)]))


def test_low_mfs_spouse_itemizes_forces_itemizing():
    r = R.compute(tr(filing_status="mfs", spouse_itemizes=True))
    assert r.itemizes and r.standard_deduction == 0
    r = R.compute(tr(filing_status="mfs"))
    assert "spouse_itemizes" in r.missing


def test_low_single_without_member_id_still_resolves_owner():
    biz = sc(10_000)
    del biz["owner"]
    r = R.compute(tr(taxpayers=[{"age": 40}], schedule_c=[biz]))
    assert r.schedule_c_net == 10_000


def test_unknown_foreign_qualified_dividends_is_a_bound():
    r = R.compute(tr(foreign={"country": "IN", "dividends": 1_000,
                              "qualified_dividends": None}))
    assert r.ordinary_dividends == 1_000 and r.qualified_dividends == 0
    assert "foreign.qualified_dividends" in r.missing
    assert any("upper bound" in b for b in r.bounds)
