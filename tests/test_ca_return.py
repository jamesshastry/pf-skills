"""California Form 540 workpaper arithmetic. All figures are synthetic."""
import copy
import datetime as dt
from types import SimpleNamespace

import pytest

from pf import ca_return as C

T = C.CA_TABLES[2025]


def tr(**kw):
    """A complete, quiet single-filer return: no HSA, no itemizing."""
    base = {
        "tax_year": 2025,
        "filing_status": "single",
        "state": "CA",
        "taxpayers": [{"member": "a1", "age": 40, "blind": False}],
        "dependents": [],
        "w2": [{"employer": "Acme", "wages": 100_000, "state": "CA",
                "state_withheld": 5_000, "sdi_withheld": 1_200, "box12": {}}],
        "interest": [],
        "estimated_payments": {"federal": [0, 0, 0, 0], "state": [0, 0, 0, 0]},
        "prior_year": {"agi": 90_000, "federal_total_tax": 9_000,
                       "state_total_tax": 4_000},
        "ca": {"use_tax": 0, "full_year_health_coverage": True, "renter": False},
    }
    ca = kw.pop("ca", None)
    base.update(kw)
    if ca is not None:
        base["ca"] = {**base["ca"], **ca}
    return base


def fed(agi=100_000, status="single", year=2025, **kw):
    base = dict(tax_year=year, filing_status=status, agi=agi,
                us_treasury_interest=0.0, tax_exempt_interest=0.0,
                net_capital_gain_or_loss=0.0)
    base.update(kw)
    return C.FederalInputs(**base)


def adj(r, line):
    return [a for a in r.adjustments if a.line == line]


# ── Rate schedule and Behavioral Health Services Tax ────────────────────

def test_rate_schedule_by_hand_for_each_status():
    from pf.cashflow import progressive_tax
    assert progressive_tax(125_000, T.brackets["mfj"]) == pytest.approx(4_768.10, abs=0.01)
    assert progressive_tax(371_479, T.brackets["single"]) == pytest.approx(30_986.19, abs=0.01)
    assert progressive_tax(1_010_417, T.brackets["hoh"]) == pytest.approx(97_472.91, abs=0.02)
    assert progressive_tax(742_953, T.brackets["mfs"]) == pytest.approx(72_219.84, abs=0.05)  # FTB rounds each band base to cents
    assert T.brackets["qss"] == T.brackets["mfj"]


def test_single_return_end_to_end_by_hand():
    r = C.compute(tr(), fed())
    assert r.ca_agi == 100_000
    assert r.deduction_kind == "standard" and r.deduction == 5_706
    assert r.taxable_income == 94_294
    # 3,201.97 + 9.3% x (94,294 - 72,724)
    assert r.tax == round(3_201.97 + 0.093 * 21_570)
    assert r.exemption_credits == 153
    assert r.total_tax == r.tax - 153
    assert r.withholding == 5_000
    assert r.balance_due == r.total_tax - 5_000
    assert r.refund == 0
    assert r.missing == []


def test_bhst_is_one_percent_over_a_million_and_does_not_double_for_mfj():
    r = C.compute(tr(filing_status="mfj",
                     taxpayers=[{"age": 50}, {"age": 50}]),
                  fed(agi=1_511_412, status="mfj"))
    assert r.taxable_income == 1_500_000
    assert r.bhst == 5_000
    assert r.total_tax == r.tax_after_credits + 5_000


def test_no_bhst_at_or_below_the_threshold():
    r = C.compute(tr(), fed(agi=1_005_706))
    assert r.taxable_income == 1_000_000
    assert r.bhst == 0


# ── Schedule CA Part I ─────────────────────────────────────────────────

def test_treasury_interest_is_subtracted():
    r = C.compute(tr(), fed(us_treasury_interest=2_500))
    assert adj(r, "2")[0].subtraction == 2_500
    assert r.ca_agi == 97_500


def test_unknown_treasury_interest_is_missing_not_zero():
    r = C.compute(tr(), fed(us_treasury_interest=None))
    assert any("us_treasury_interest" in m for m in r.missing)


def test_hsa_payroll_contribution_and_deduction_are_added_back():
    t = tr(hsa={"contributions_personal": 1_000, "distributions": 0,
                "qualified_expenses": 0},
           ca={"hsa_earnings": 150})
    t["w2"][0]["box12"] = {"W": 3_300}
    r = C.compute(t, fed(hsa_deduction=1_000))
    assert adj(r, "1h")[0].addition == 3_300
    assert adj(r, "13")[0].addition == 1_000
    assert adj(r, "2/3/7")[0].addition == 150
    assert r.ca_agi == 100_000 + 3_300 + 1_000 + 150
    assert r.missing == []


def test_hsa_earnings_unknown_goes_to_missing():
    t = tr(hsa={"distributions": 0})
    t["w2"][0]["box12"] = {"W": 2_000}
    r = C.compute(t, fed())
    assert any("hsa_earnings" in m for m in r.missing)


def test_nonqualified_hsa_distribution_is_subtracted_and_qualified_adds_to_medical():
    t = tr(hsa={"distributions": 5_000, "qualified_expenses": 3_000},
           ca={"hsa_earnings": 0},
           itemized={"medical": 10_000, "property_tax": 0,
                     "other_state_local_taxes": 0, "mortgage_interest": 0,
                     "charitable_cash": 0, "charitable_noncash": 0})
    r = C.compute(t, fed(agi=100_000))
    assert adj(r, "8f")[0].subtraction == 2_000
    # CA medical = 10,000 + 3,000 HSA-paid - 7.5% x 100,000 federal AGI
    assert r.itemized_deduction == 13_000 - 7_500


def test_state_refund_and_social_security_are_subtracted():
    r = C.compute(tr(), fed(state_refund_taxable=800, taxable_social_security=12_000))
    assert adj(r, "B1")[0].subtraction == 800
    assert adj(r, "6")[0].subtraction == 12_000
    assert r.ca_agi == 100_000 - 12_800


def test_non_california_muni_interest_is_added_and_unknown_flagged():
    # tax_exempt is the box 8 dollar amount; box 1 `amount` is already in AGI.
    t = tr(interest=[
        {"payer": "NY bond fund", "amount": 1_000, "tax_exempt": 500, "ca_exempt": False},
        {"payer": "CA bond", "amount": 0, "tax_exempt": 400, "ca_exempt": True},
        {"payer": "mystery", "amount": 0, "tax_exempt": 100},
        {"payer": "bank", "amount": 300, "tax_exempt": 0},       # no flag needed
    ])
    r = C.compute(t, fed())
    assert adj(r, "2")[0].addition == 500
    assert r.ca_agi == 100_500
    assert [m for m in r.missing if "ca_exempt" in m] == [
        m for m in r.missing if "interest[2].ca_exempt" in m] != []


def test_boolean_tax_exempt_is_refused():
    t = tr(interest=[{"payer": "x", "amount": 400, "tax_exempt": True}])
    with pytest.raises(C.CAReturnError, match="dollar amount"):
        C.compute(t, fed())


def test_depreciation_unknown_is_missing_and_override_applies():
    sc = [{"owner": "a1", "business": "consult", "gross_receipts": 50_000,
           "expenses": {"depreciation": 8_000}}]
    r = C.compute(tr(schedule_c=sc), fed())
    assert any("depreciation_adjustment" in m for m in r.missing)
    r2 = C.compute(tr(schedule_c=sc, ca={"depreciation_adjustment": 6_000}), fed())
    assert adj(r2, "3")[0].addition == 6_000
    assert r2.ca_agi == 106_000


def test_ca_capital_loss_carryover_differs_from_federal():
    # Federal: 1,000 gain less a 4,000 federal carryover -> -3,000 allowed.
    # CA carryover is only 2,500 -> CA net is -1,500.
    t = tr(capital_transactions=[{"description": "x", "proceeds": 11_000,
                                  "basis": 10_000, "term": "long"}],
           capital_loss_carryover={"short": 0, "long": 4_000},
           ca={"ca_capital_loss_carryover": {"short": 0, "long": 2_500}})
    r = C.compute(t, fed(net_capital_gain_or_loss=-3_000))
    assert adj(r, "7")[0].addition == 1_500


def test_capital_carryover_not_recorded_is_assumed_equal_and_said():
    t = tr(capital_loss_carryover={"short": 0, "long": 4_000})
    r = C.compute(t, fed(net_capital_gain_or_loss=-3_000))
    assert not adj(r, "7")
    assert any("carryover not recorded" in f for f in r.findings)


# ── Deduction ──────────────────────────────────────────────────────────

ITEMS = {"medical": 0, "property_tax": 0, "other_state_local_taxes": 0,
         "mortgage_interest": 0, "charitable_cash": 0, "charitable_noncash": 0}


def test_standard_beats_small_itemized():
    r = C.compute(tr(itemized={**ITEMS, "charitable_cash": 3_000}), fed())
    assert r.itemized_deduction == 3_000
    assert r.deduction_kind == "standard"


def test_no_salt_cap_and_one_million_mortgage_limit():
    items = {**ITEMS, "property_tax": 50_000, "mortgage_interest": 60_000,
             "mortgage_balance": 1_500_000}
    r = C.compute(tr(itemized=items), fed(agi=200_000))
    # 50,000 property tax uncapped + 60,000 x 1.0M / 1.5M
    assert r.itemized_deduction == 50_000 + 40_000
    assert r.deduction_kind == "itemized"


def test_mfs_mortgage_limit_is_half():
    items = {**ITEMS, "mortgage_interest": 30_000, "mortgage_balance": 750_000}
    r = C.compute(tr(filing_status="mfs", itemized=items,
                     ca={"spouse_itemizes": True}),
                  fed(agi=150_000, status="mfs"))
    assert r.itemized_deduction == 20_000


def test_itemized_phaseout_six_percent_capped_at_eighty_percent():
    items = {**ITEMS, "property_tax": 30_000, "mortgage_interest": 40_000,
             "mortgage_balance": 800_000, "charitable_cash": 10_000}
    t = tr(filing_status="mfj", taxpayers=[{"age": 50}, {"age": 50}], itemized=items)
    r = C.compute(t, fed(agi=504_411 + 200_000, status="mfj"))
    assert r.itemized_before_limit == 80_000
    assert r.itemized_deduction == 80_000 - 12_000          # 6% x 200,000
    big = C.compute(t, fed(agi=504_411 + 2_000_000, status="mfj"))
    assert big.itemized_deduction == 80_000 - 64_000        # 80% cap binds


def test_charitable_limited_to_half_of_agi():
    r = C.compute(tr(itemized={**ITEMS, "charitable_cash": 70_000}), fed(agi=100_000))
    assert r.itemized_deduction == 50_000
    assert any("50%-of-AGI" in f for f in r.findings)


def test_null_itemized_item_is_missing_and_standard_used_as_upper_bound():
    r = C.compute(tr(itemized={**ITEMS, "property_tax": None}), fed())
    assert "tax_return.itemized.property_tax" in r.missing
    assert r.deduction_kind == "standard"
    assert any("upper bound" in f for f in r.findings)


def test_mortgage_interest_without_balance_is_missing():
    r = C.compute(tr(itemized={**ITEMS, "mortgage_interest": 20_000}), fed())
    assert any("mortgage_balance" in m for m in r.missing)


# ── Exemption credits ───────────────────────────────────────────────────

def test_exemption_counts_senior_blind_dependents():
    t = tr(filing_status="mfj",
           taxpayers=[{"age": 66, "blind": True}, {"age": 60, "blind": False}],
           dependents=[{"member": "c1"}, {"member": "c2"}])
    r = C.compute(t, fed(agi=150_000, status="mfj"))
    assert r.exemption_counts == {"personal": 2, "blind": 1, "senior": 1, "dependent": 2}
    assert r.exemption_credits == 4 * 153 + 2 * 475


def test_qss_gets_two_personal_exemptions():
    r = C.compute(tr(filing_status="qss"), fed(status="qss"))
    assert r.exemption_counts["personal"] == 2


def test_exemption_phaseout_by_hand_mfj():
    # excess 95,589 -> ceil(/2,500) = 39 steps -> $234 per exemption.
    t = tr(filing_status="mfj", taxpayers=[{"age": 50}, {"age": 50}],
           dependents=[{"member": "c1"}, {"member": "c2"}])
    r = C.compute(t, fed(agi=600_000, status="mfj"))
    assert r.exemption_credits == max(0, 306 - 468) + (950 - 468)


def test_exemption_phaseout_mfs_uses_1250_steps():
    # excess 7,797 -> ceil(/1,250) = 7 steps -> $42.
    r = C.compute(tr(filing_status="mfs", ca={"spouse_itemizes": False}),
                  fed(agi=260_000, status="mfs"))
    assert r.exemption_credits == 153 - 42


def test_unknown_age_is_missing():
    r = C.compute(tr(taxpayers=[{"member": "a1", "age": None}]), fed())
    assert any("age" in m for m in r.missing)


# ── Credits ────────────────────────────────────────────────────────────

def test_renters_credit_inside_limit():
    t = tr(filing_status="mfj", taxpayers=[{"age": 40}, {"age": 40}],
           ca={"renter": True})
    r = C.compute(t, fed(agi=100_000, status="mfj"))
    assert ("Nonrefundable renter's credit", 120) in r.credits


def test_renters_credit_over_limit_or_not_renter():
    r = C.compute(tr(ca={"renter": True}), fed(agi=60_000))
    assert r.credits == []
    assert any("Renter's credit not available" in f for f in r.findings)
    r2 = C.compute(tr(ca={"renter": False}), fed(agi=40_000))
    assert r2.credits == []


def test_renter_status_unknown_is_said():
    t = tr()
    del t["ca"]["renter"]
    r = C.compute(t, fed(agi=40_000))
    assert any("renter status is not recorded" in f for f in r.findings)


def test_renters_credit_comes_before_carryover_credits():
    # R&TC §17039: a no-carryover credit is used before a carryover credit.
    t = tr(filing_status="mfj", taxpayers=[{"age": 40}, {"age": 40}],
           ca={"renter": True,
               "nonrefundable_credits": [{"name": "R&D carryover", "amount": 100_000}]})
    r = C.compute(t, fed(agi=100_000, status="mfj"))
    assert r.credits[0] == ("Nonrefundable renter's credit", 120)
    assert r.credits[1] == ("R&D carryover", r.tax_after_exemptions - 120)
    assert r.tax_after_credits == 0
    assert any("carries forward" in f for f in r.findings)


def test_no_carryover_input_credit_is_ordered_first_and_said_lost():
    t = tr(ca={"renter": True, "nonrefundable_credits": [
        {"name": "carry", "amount": 50}, {"name": "child care", "amount": 5_000,
                                          "carryover": False}]})
    r = C.compute(t, fed(agi=20_000))
    assert r.credits[0] == ("child care", r.tax_after_exemptions)
    assert r.tax_after_credits == 0
    assert any("child care" in f and "lost" in f for f in r.findings)


# ── Payments ───────────────────────────────────────────────────────────

def test_sdi_is_not_a_payment_and_other_state_w2_without_withholding_ignored():
    t = tr()
    t["w2"].append({"employer": "B", "state": "CA", "state_withheld": 1_000,
                    "sdi_withheld": 900})
    r = C.compute(t, fed())
    assert r.withholding == 6_000
    assert any("recovered from the employer" in f for f in r.findings)


def test_estimated_payments_and_refund():
    t = tr(estimated_payments={"state": [1_000, 1_000, 0, 1_000]},
           ca={"prior_year_overpayment_applied": 500})
    r = C.compute(t, fed(agi=60_000))
    assert r.estimated_payments == 3_500
    assert r.refund == r.total_payments - r.total_tax
    assert r.balance_due == 0


def test_null_estimate_quarter_is_missing():
    r = C.compute(tr(estimated_payments={"state": [1_000, None, 0, 0]}), fed())
    assert any("estimated_payments.state" in m for m in r.missing)


def test_use_tax_and_coverage_unknown_go_to_missing():
    t = tr()
    del t["ca"]["use_tax"]
    del t["ca"]["full_year_health_coverage"]
    r = C.compute(t, fed())
    assert any("use_tax" in m for m in r.missing)
    assert any("full_year_health_coverage" in m for m in r.missing)


# ── Estimated tax ──────────────────────────────────────────────────────

def _underpaid():
    t = tr(prior_year={"agi": 180_000, "state_total_tax": 10_000},
           ca={"prior_year_ca_agi": 180_000})
    t["w2"][0]["state_withheld"] = 4_000
    return C.compute(t, fed(agi=200_000))


def test_underpayment_uses_110_percent_of_prior_and_30_40_0_30():
    r = _underpaid()
    assert r.tax_after_credits == 14_508 - 153
    assert r.underpayment_required_annual == 11_000         # min(90% x 14,355, 110% x 10,000)
    assert r.underpayment_shortfalls == [2_300, 5_700, 4_700, 7_000]
    assert any("FTB 5805" in f for f in r.findings)


def test_prior_year_100_percent_when_prior_agi_low():
    t = tr(prior_year={"state_total_tax": 10_000}, ca={"prior_year_ca_agi": 140_000})
    t["w2"][0]["state_withheld"] = 4_000
    r = C.compute(t, fed(agi=200_000))
    assert r.underpayment_required_annual == 10_000


def test_no_penalty_when_balance_under_500():
    r = C.compute(tr(), fed(agi=60_000))
    assert r.underpayment_required_annual is None


def test_million_dollar_agi_must_use_current_year():
    t = tr(prior_year={"state_total_tax": 50_000}, ca={"prior_year_ca_agi": 900_000})
    r = C.compute(t, fed(agi=1_200_000))
    assert r.underpayment_required_annual == round(0.9 * (r.tax_after_credits + r.bhst))
    # Next year's bar depends on NEXT year's AGI: printed, but conditional.
    assert r.next_year_installments
    assert any("only if 2026 California AGI stays under" in f for f in r.findings)


def test_next_year_agi_estimate_decides_the_million_dollar_rule():
    over = C.compute(tr(ca={"next_year_agi_estimate": 1_300_000}), fed(agi=200_000))
    assert over.next_year_required_annual is None and over.next_year_installments == []
    under = C.compute(tr(ca={"next_year_agi_estimate": 900_000}), fed(agi=1_200_000))
    assert under.next_year_installments
    assert not any("only if" in f for f in under.findings)


def test_next_year_installments_dates_and_shares():
    r = _underpaid()
    assert r.next_year_required_annual == 15_791            # 110% x 14,355
    got = [(i.due, i.amount) for i in r.next_year_installments]
    assert got == [(dt.date(2026, 4, 15), 3_537), (dt.date(2026, 6, 15), 4_716),
                   (dt.date(2026, 9, 15), 0), (dt.date(2027, 1, 15), 3_537)]


# ── LLC ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("income,fee", [
    (249_999, 0), (250_000, 900), (499_999, 900), (500_000, 2_500),
    (999_999, 2_500), (1_000_000, 6_000), (4_999_999, 6_000), (5_000_000, 11_790)])
def test_llc_fee_tiers(income, fee):
    assert C.llc_fee(income) == fee


def test_existing_llc_owes_800_and_fee():
    r = C.compute(tr(ca={"llc": [{"name": "Side LLC", "formed_year": 2019,
                                  "gross_receipts_total_income": 300_000}]}), fed())
    o = r.llcs[0]
    assert (o.annual_tax, o.fee, o.annual_tax_due) == (800, 900, dt.date(2025, 4, 15))
    assert o.return_due == dt.date(2026, 4, 15)


def test_first_year_exemption_only_for_2021_to_2023_formations():
    r = C.compute(tr(tax_year=2025, ca={"llc": [
        {"name": "New", "formed_year": 2025, "formed_on": "2025-02-10",
         "gross_receipts_total_income": 10_000}]}), fed())
    assert r.llcs[0].annual_tax == 800
    assert r.llcs[0].annual_tax_due == dt.date(2025, 5, 15)  # 15th day of 4th month
    t = tr(tax_year=2023, ca={"llc": [{"name": "Old", "formed_year": 2023,
                                       "gross_receipts_total_income": 0}]})
    with pytest.raises(C.CAReturnError):          # no 2023 tables: refused
        C.compute(t, fed(year=2023))
    one = C._llcs([{"name": "Old", "formed_year": 2023,
                    "gross_receipts_total_income": 0}], 2023, [], [])
    assert one[0].annual_tax == 0


def test_llc_unknowns_are_missing():
    r = C.compute(tr(ca={"llc": [{"name": "X", "formed_year": 2025,
                                  "gross_receipts_total_income": None}]}), fed())
    assert any("formed_on" in m for m in r.missing)
    assert any("gross_receipts_total_income" in m for m in r.missing)
    assert r.llcs[0].fee is None


# ── Tables, projection, adapter ─────────────────────────────────────────

def test_unpublished_year_uses_latest_table_and_flags_projection():
    r = C.compute(tr(tax_year=2026), fed(year=2026))
    assert r.projection and r.table_year == 2025
    assert any("projection" in f for f in r.findings)


def test_from_federal_reads_by_name():
    fr = SimpleNamespace(tax_year=2025, filing_status="mfj", agi=250_000,
                         us_treasury_interest=100, tax_exempt_interest=0,
                         net_capital_gain_or_loss=-3_000,
                         adjustments={"hsa_deduction": 4_000, "half_se_tax": 700})
    f = C.from_federal(fr)
    assert (f.agi, f.hsa_deduction, f.half_se_tax, f.federal_amt) == (250_000, 4_000, 700, None)


# ── Refusals ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("mutate,match", [
    (lambda t: t["ca"].update(residency="part_year"), "540NR"),
    (lambda t: t.update(state="NV"), "California resident"),
    (lambda t: t["w2"].append({"state": "NY", "state_withheld": 500}), "Schedule S"),
    (lambda t: t["ca"].update(ftb3803=True), "kiddie"),
    (lambda t: t.update(rental=[{"property": "x"}]), "rental"),
    (lambda t: t["taxpayers"][0].update(can_be_claimed_as_dependent=True), "dependent"),
    (lambda t: t["ca"].update(rdp=True), "domestic partners"),
])
def test_out_of_scope_is_refused(mutate, match):
    t = copy.deepcopy(tr())
    mutate(t)
    with pytest.raises(C.CAReturnError, match=match):
        C.compute(t, fed())


def test_mismatched_federal_and_unknown_agi_are_refused():
    with pytest.raises(C.CAReturnError, match="federal return is for"):
        C.compute(tr(), fed(year=2024))
    with pytest.raises(C.CAReturnError, match="filing status"):
        C.compute(tr(), fed(status="mfj"))
    with pytest.raises(C.CAReturnError, match="federal AGI"):
        C.compute(tr(), fed(agi=None))


def test_amt_is_flagged_not_computed():
    r = C.compute(tr(), fed(federal_amt=2_000))
    assert any("Schedule P" in f for f in r.findings)


# ── Review fixes ───────────────────────────────────────────────────────

def test_hsa_employer_contributions_used_when_box_12w_absent():
    t = tr(hsa={"employer_contributions": 1_500, "distributions": 0},
           ca={"hsa_earnings": 0})
    r = C.compute(t, fed())
    assert adj(r, "1h")[0].addition == 1_500
    assert r.missing == []


def test_hsa_employer_unknown_is_missing_and_disagreement_flagged():
    r = C.compute(tr(hsa={"distributions": 0}, ca={"hsa_earnings": 0}), fed())
    assert any("employer_contributions" in m for m in r.missing)
    t = tr(hsa={"employer_contributions": 900, "distributions": 0},
           ca={"hsa_earnings": 0})
    t["w2"][0]["box12"] = {"W": 1_500}
    r2 = C.compute(t, fed())
    assert adj(r2, "1h")[0].addition == 1_500
    assert any("disagree" in f for f in r2.findings)


def test_prior_year_overpayment_counts_on_the_first_installment():
    t = tr(prior_year={"state_total_tax": 20_000}, ca={
        "prior_year_ca_agi": 200_000, "prior_year_overpayment_applied": 20_000})
    t["w2"][0]["state_withheld"] = 0
    r = C.compute(t, fed(agi=400_000))
    assert r.underpayment_required_annual == 22_000          # 110% x 20,000
    assert r.underpayment_shortfalls == [0, 0, 0, 2_000]


def test_lowercase_state_is_california():
    t = tr()
    t["w2"][0]["state"] = "ca"
    r = C.compute(t, fed())
    assert r.withholding == 5_000


def test_mfs_with_itemizing_spouse_must_itemize_even_without_items():
    r = C.compute(tr(filing_status="mfs", ca={"spouse_itemizes": True}),
                  fed(status="mfs"))
    assert r.deduction_kind == "itemized" and r.deduction == 0


def test_bad_shapes_stop_cleanly():
    with pytest.raises(C.CAReturnError, match="list of up to four"):
        C.compute(tr(estimated_payments={"state": 4_000}), fed())
    with pytest.raises(C.CAReturnError, match="ISO date"):
        C.compute(tr(ca={"llc": [{"name": "X", "formed_year": 2025,
                                  "formed_on": "March 2025",
                                  "gross_receipts_total_income": 0}]}), fed())


def test_negative_itemized_input_is_not_blamed_on_the_mortgage():
    r = C.compute(tr(itemized={**ITEMS, "property_tax": -5}), fed())
    assert any(m.startswith("tax_return.itemized —") for m in r.missing)


def test_mfs_minimum_balance_wording():
    r = C.compute(tr(filing_status="mfs", ca={"spouse_itemizes": False}),
                  fed(agi=40_000, status="mfs"))
    assert any("within $250" in f for f in r.findings)


def test_us_obligation_dividends_and_ca_only_itemized_items():
    r = C.compute(tr(ca={"us_obligation_dividends": 700}), fed())
    assert adj(r, "3")[0].subtraction == 700
    r2 = C.compute(tr(itemized={**ITEMS, "charitable_cash": 4_000},
                      ca={"home_equity_interest": 3_000,
                          "foreign_real_property_tax": 1_000}), fed())
    assert r2.itemized_deduction == 8_000


def test_first_year_llc_fee_estimate_is_dated_from_formation():
    r = C.compute(tr(ca={"llc": [{"name": "New", "formed_year": 2025,
                                  "formed_on": "2025-08-20",
                                  "gross_receipts_total_income": 300_000}]}), fed())
    assert r.llcs[0].fee_estimate_due == dt.date(2026, 1, 15)   # 6th month
    assert r.llcs[0].annual_tax_due == dt.date(2025, 11, 15)


# ── Integration: the real federal return feeds this one ────────────────

def test_example_household_as_californians_through_the_real_federal_return():
    yaml = pytest.importorskip("yaml")
    from pathlib import Path
    from pf import federal_return as FR
    example = yaml.safe_load((Path(__file__).resolve().parents[1]
                              / "inputs" / "facts.example.yml").read_text())
    t = copy.deepcopy(example["tax_return"])
    t["state"] = "CA"
    for w in t["w2"]:
        w.update(state="CA", state_wages=w["wages"], state_withheld=9_000)
    t["interest"].append({"payer": "NY muni fund", "amount": 0, "us_treasury": 0,
                          "tax_exempt": 500, "ca_exempt": False})
    t["prior_year"]["state_total_tax"] = 14_000
    t["ca"] = {"hsa_earnings": 60, "use_tax": 0, "full_year_health_coverage": True,
               "renter": True, "prior_year_ca_agi": 171_000}
    fr = FR.compute(t)
    f = C.from_federal(fr)
    r = C.compute(t, f)

    assert f.agi == fr.agi and f.us_treasury_interest == 800
    box_w = sum((w.get("box12") or {}).get("W") or 0 for w in t["w2"])
    assert adj(r, "2")[0].subtraction == 800                  # Treasury
    assert [a.addition for a in adj(r, "2") if a.addition] == [500]   # NY muni
    assert adj(r, "1h")[0].addition == box_w
    hsa_lines = adj(r, "13")
    assert (hsa_lines[0].addition if hsa_lines else 0) == f.hsa_deduction
    assert r.ca_agi == (r.federal_agi - 800 + 500 + box_w + f.hsa_deduction + 60)
    assert r.withholding == 9_000 * len(t["w2"])
    assert r.total_tax == r.tax_after_credits + r.bhst
    assert r.refund - r.balance_due == r.total_payments - r.total_tax
    assert r.missing == []


# ── Federal foreign routing and shared spouse_itemizes ─────────────────

def test_ca_capital_recompute_includes_foreign_sales():
    # Domestic +1,000, foreign -2,000; CA carryover 500 -> CA net -1,500.
    t = tr(capital_transactions=[{"proceeds": 2_000, "basis": 1_000}],
           foreign={"capital_transactions": [{"proceeds": 1_000, "basis": 3_000}]},
           ca={"ca_capital_loss_carryover": 500})
    r = C.compute(t, fed(net_capital_gain_or_loss=-3_000))
    assert adj(r, "7")[0].addition == 1_500


def test_foreign_rent_is_refused():
    with pytest.raises(C.CAReturnError, match="foreign.rent"):
        C.compute(tr(foreign={"rent": 6_000}), fed())


def test_shared_spouse_itemizes_is_honoured_and_ca_overrides():
    r = C.compute(tr(filing_status="mfs", spouse_itemizes=True), fed(status="mfs"))
    assert r.deduction_kind == "itemized" and r.deduction == 0
    r2 = C.compute(tr(filing_status="mfs", spouse_itemizes=True,
                      ca={"spouse_itemizes": False}), fed(status="mfs"))
    assert r2.deduction_kind == "standard"
