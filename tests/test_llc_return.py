"""LLC entity-return workpaper arithmetic. All figures are synthetic and
worked by hand in the comments."""
import copy
import datetime as dt

import pytest

from pf import federal_return as FED
from pf import llc_return as L


def base(**kw):
    """A quiet single-member LLC in Texas: no home office, no contractors."""
    d = {
        "name": "Test Co LLC", "state": "TX", "classification": "disregarded",
        "formed_on": "2020-01-01",
        "owners": [{"member": "a1", "share": 1.0, "active": True}],
        "accounting_method": "cash",
        "gross_receipts": 100_000, "returns_and_allowances": 0,
        "cost_of_goods_sold": 0, "other_income": 0,
        "expenses": {"supplies": 10_000}, "meals": 0, "depreciation": 0,
        "sstb": False, "ubia": 0, "estimated_payments": [0, 0, 0, 0],
    }
    d.update(kw)
    return d


def partnership(**kw):
    d = base(classification="partnership", owners=[
        {"member": "a1", "share": 0.5, "active": True},
        {"member": "b1", "share": 0.5, "active": False}],
        guaranteed_payments=[{"member": "a1", "amount": 30_000}])
    d.update(kw)
    return d


def s_corp(**kw):
    d = base(classification="s_corp", s_election_effective="2021-01-01",
             officer_wages=[{"member": "a1", "amount": 50_000,
                             "federal_withheld": 6_000, "ss_withheld": 3_100,
                             "medicare_withheld": 725}],
             payroll_taxes_employer=3_825 + 42,
             distributions=[{"member": "a1", "amount": 30_000}])
    d.update(kw)
    return d


def run(d, year=2026, **kw):
    return L.compute(d, tax_year=year, **kw)


def has(findings, text):
    return any(text in f for f in findings)


# ── disregarded: ledger → Schedule C ────────────────────────────────────


def test_disregarded_net_profit_and_meals_at_half():
    # 100,000 − 10,000 supplies − 50% of 2,000 meals = 89,000
    r = run(base(meals=2_000))
    assert r.form.startswith("Schedule C")
    assert r.net == pytest.approx(89_000)
    assert ("24b", "Meals (50% of $2,000)", -1_000) in r.lines


def test_returns_cogs_and_other_income_build_gross_income():
    # 100,000 − 5,000 − 20,000 + 1,000 = 76,000 gross income (Schedule C line 7)
    r = run(base(returns_and_allowances=5_000, cost_of_goods_sold=20_000,
                 other_income=1_000))
    assert r.gross_income == 76_000
    assert r.net == 66_000


def test_schedule_c_handoff_has_exactly_the_federal_fields_and_reproduces_net():
    r = run(base(meals=2_000, home_office={"method": "actual", "amount": 3_000},
                 vehicle={"method": "actual", "amount": 4_000}))
    [sc] = r.schedule_c
    assert set(sc) == {"owner", "business", "gross_receipts", "expenses", "vehicle",
                       "home_office", "home_office_method", "sstb", "w2_wages",
                       "ubia"}
    # Federal applies the same home-office limit, so the nets agree.
    tr = {"tax_year": 2026, "filing_status": "single",
          "taxpayers": [{"member": "a1", "age": 45}], "w2": [],
          "schedule_c": [sc],
          "estimated_payments": {"federal": [0, 0, 0, 0]},
          "prior_year": {"agi": 50_000, "federal_total_tax": 5_000}}
    fr = FED.compute(tr)
    assert fr.schedule_c_net == pytest.approx(r.net)
    assert r.net == pytest.approx(100_000 - 10_000 - 1_000 - 4_000 - 3_000)


def test_se_note_at_and_below_the_400_floor():
    at = run(base(gross_receipts=10_000 + 400 / L.SE_EARNINGS_FACTOR))
    assert "SE tax applies" in at.se_note[0]
    below = run(base(gross_receipts=10_000 + 399 / L.SE_EARNINGS_FACTOR))
    assert "no SE tax" in below.se_note[0]


def test_unmapped_categories_go_to_other_expenses_and_lines_sort():
    r = run(base(expenses={"software": 1_000, "advertising": 500, "other": 200}))
    assert has(r.findings, "software")
    assert not has(r.findings, "Categories other")
    lines = [ln for ln, _, _ in r.lines]
    assert lines.index("8") < lines.index("27b")


# ── home office ─────────────────────────────────────────────────────────


def test_simplified_home_office_is_capped_at_300_sq_ft():
    r = run(base(home_office={"method": "simplified", "sq_ft": 400}))
    assert r.home_office["amount"] == 1_500


def test_home_office_cannot_create_a_loss_actual_carries_forward():
    # tentative profit 100,000 − 99,000 = 1,000; 3,000 claimed
    r = run(base(expenses={"supplies": 99_000},
                 home_office={"method": "actual", "amount": 3_000}))
    assert r.home_office["allowed"] == 1_000
    assert r.home_office["carryforward"] == 2_000
    assert r.net == 0


def test_simplified_excess_is_lost():
    r = run(base(expenses={"supplies": 99_500},
                 home_office={"method": "simplified", "sq_ft": 200}))
    assert r.home_office["allowed"] == 500
    assert r.home_office["lost"] == 500 and r.home_office["carryforward"] == 0


def test_home_office_not_deducted_by_a_partnership():
    r = run(partnership(home_office={"method": "actual", "amount": 3_000}))
    assert r.home_office["allowed"] == 0
    assert has(r.findings, "unreimbursed partnership expenses")


def test_home_office_amount_null_bounds():
    r = run(base(home_office={"method": "actual", "amount": None}))
    assert r.home_office is None
    assert has(r.bounds, "upper bound")


# ── vehicle ─────────────────────────────────────────────────────────────


def test_standard_mileage_2025_single_rate():
    r = run(base(vehicle={"method": "standard", "business_miles": 1_000}), year=2025)
    assert r.net == pytest.approx(90_000 - 700)


def test_standard_mileage_2026_split_rates():
    # 1,000 × 0.725 + 2,000 × 0.76 = 725 + 1,520 = 2,245
    r = run(base(vehicle={"method": "standard", "business_miles": [1_000, 2_000]}))
    assert r.net == pytest.approx(90_000 - 2_245)


def test_standard_mileage_2026_single_total_uses_lower_rate_and_bounds():
    r = run(base(vehicle={"method": "standard", "business_miles": 3_000}))
    assert r.net == pytest.approx(90_000 - 3_000 * 0.725)
    assert has(r.bounds, "lower bound")


def test_mileage_period_count_must_match():
    with pytest.raises(L.LLCReturnError, match="periods"):
        run(base(vehicle={"method": "standard", "business_miles": [1, 2]}), year=2025)


# ── start-up and organizational costs ───────────────────────────────────


def test_startup_phaseout_and_amortization_in_first_year():
    # 54,000: immediate 5,000 − 4,000 = 1,000; 53,000 / 180 = 294.44/mo × 10 (Mar–Dec)
    a = L.amortize(54_000, dt.date(2026, 3, 1), 2026)
    assert a["immediate"] == 1_000
    assert a["amortization"] == pytest.approx(53_000 / 180 * 10)


def test_startup_fully_phased_out_above_55000():
    a = L.amortize(60_000, dt.date(2026, 1, 1), 2026)
    assert a["immediate"] == 0
    assert a["amortization"] == pytest.approx(60_000 / 180 * 12)


def test_small_startup_fully_expensed():
    a = L.amortize(3_000, dt.date(2026, 6, 1), 2026)
    assert a["immediate"] == 3_000 and a["amortization"] == 0


def test_startup_in_a_later_year_takes_twelve_months_only():
    # began Jul 2024: 18 months used by end-2025; 12 more in 2026
    a = L.amortize(20_000, dt.date(2024, 7, 1), 2026)
    assert a["immediate"] == 0
    assert a["amortization"] == pytest.approx(15_000 / 180 * 12)
    assert a["remaining"] == pytest.approx(15_000 - 15_000 / 180 * 30)


def test_startup_ends_after_180_months():
    a = L.amortize(20_000, dt.date(2010, 1, 1), 2026)
    assert a["amortization"] == 0


def test_startup_before_business_begins_is_not_deductible():
    r = run(base(startup_costs={"incurred": 10_000, "business_began": "2027-02-01"}))
    assert r.startup["deduction"] == 0
    assert has(r.findings, "nothing is deductible")


def test_disregarded_formation_costs_join_startup():
    # 3,000 + 4,000 = 7,000 → one 5,000 allowance; 2,000/180 × 12
    r = run(base(startup_costs={"incurred": 3_000, "business_began": "2026-01-01"},
                 organizational_costs=4_000))
    assert len(r.startup["parts"]) == 1
    assert r.startup["deduction"] == pytest.approx(5_000 + 2_000 / 180 * 12)
    assert has(r.findings, "§195 start-up costs")


def test_partnership_gets_separate_section_709_allowance():
    r = run(partnership(startup_costs={"incurred": 3_000, "business_began": "2026-01-01"},
                        organizational_costs=4_000))
    assert [p[0] for p in r.startup["parts"]] == ["§195 start-up", "§709 organizational"]
    assert r.startup["deduction"] == 7_000


def test_startup_without_began_date_stops():
    with pytest.raises(L.LLCReturnError) as e:
        run(base(startup_costs={"incurred": 3_000}))
    assert "startup_costs.business_began" in e.value.missing


# ── partnership ─────────────────────────────────────────────────────────


def test_partnership_guaranteed_payments_and_k1_boxes():
    # OBI = 100,000 − 10,000 − 30,000 GP = 60,000; 30,000 each
    r = run(partnership(distributions=[{"member": "a1", "amount": 5_000}]))
    assert r.net == 60_000
    a, b = r.k1
    assert a["form"] == "1065"
    assert a["ordinary_business_income"] == 30_000 and a["guaranteed_payments"] == 30_000
    assert a["se_earnings"] == 60_000          # active: share + GP
    assert b["se_earnings"] == 0               # inactive: GP only
    assert a["qbi_income"] == 30_000           # GP excluded from QBI
    assert a["distributions"] == 5_000 and b["distributions"] == 0
    boxes = dict((x[0], x[2]) for x in r.k1_boxes["a1"])
    assert "19F" in boxes and "19A" in dict((x[0], x[2]) for x in r.k1_boxes["b1"])
    assert set(a) == {"owner", "entity", "form", "ordinary_business_income",
                      "guaranteed_payments", "se_earnings", "interest", "dividends",
                      "distributions", "qbi_income", "qbi_w2_wages", "qbi_ubia",
                      "sstb", "material_participation"}


def test_partnership_active_unknown_leaves_se_unknown():
    d = partnership()
    d["owners"][1]["active"] = None
    r = run(d)
    assert r.k1[1]["se_earnings"] is None
    assert any("owners[].active" in x for x in r.missing)


def test_partnership_interest_is_separately_stated_and_wages_shared():
    r = run(partnership(interest_income=1_000, expenses={"supplies": 10_000,
                                                         "wages": 20_000}))
    assert r.net == 40_000                     # interest not in OBI
    assert r.k1[0]["interest"] == 500
    assert r.k1[0]["qbi_w2_wages"] == 10_000


def test_partnership_needs_two_owners():
    with pytest.raises(L.LLCReturnError, match="single-member"):
        run(base(classification="partnership"))


def test_partnership_gp_amount_null_stops():
    with pytest.raises(L.LLCReturnError) as e:
        run(partnership(guaranteed_payments=[{"member": "a1", "amount": None}]))
    assert "guaranteed_payments[0].amount" in e.value.missing


def test_guaranteed_payment_to_non_owner_is_an_error():
    with pytest.raises(L.LLCReturnError, match="not an owner"):
        run(partnership(guaranteed_payments=[{"member": "zz", "amount": 1}]))


def test_late_penalty_per_partner_per_month():
    r = run(partnership())
    assert r.late_penalty["per_month"] == 2 * 260
    assert r.late_penalty["maximum"] == 2 * 260 * 12
    assert r.late_penalty["small_partnership"] is True
    assert run(partnership(), year=2025).late_penalty["per_owner_month"] == 255


def test_entity_return_due_15th_of_third_month_rolled_off_weekend():
    r = run(partnership(), year=2025)
    assert (dt.date(2026, 3, 16), r.deadlines[0][1]) in r.deadlines  # Mar 15 2026 is Sunday


# ── basis ───────────────────────────────────────────────────────────────


def test_loss_beyond_basis_is_suspended():
    # OBI = 100,000 − 10,000 − 130,000 = −40,000; −20,000 each; a1 basis 5,000
    d = partnership(guaranteed_payments=[{"member": "a1", "amount": 130_000}],
                    owner_basis_start=[{"member": "a1", "amount": 5_000},
                                       {"member": "b1", "amount": 50_000}])
    r = run(d)
    a = next(b for b in r.basis if b["member"] == "a1")
    assert a["allowed_loss"] == 5_000 and a["suspended"] == 15_000
    b = next(b for b in r.basis if b["member"] == "b1")
    assert b["suspended"] == 0 and b["end"] == 30_000


def test_distribution_in_excess_of_basis_is_gain():
    d = partnership(distributions=[{"member": "b1", "amount": 50_000}],
                    owner_basis_start=[{"member": "b1", "amount": 10_000}])
    r = run(d)
    b = next(x for x in r.basis if x["member"] == "b1")
    # 10,000 + 30,000 income − 50,000 → 10,000 gain
    assert b["excess_distribution"] == 10_000
    assert has(r.findings, "§731(a)")


def test_unknown_basis_bounds_the_loss():
    d = partnership(guaranteed_payments=[{"member": "a1", "amount": 130_000}])
    r = run(d)
    assert all(b["suspended"] is None for b in r.basis)
    assert has(r.bounds, "between 0 and")


# ── classification checks ───────────────────────────────────────────────


def test_disregarded_with_two_owners_is_an_error():
    with pytest.raises(L.LLCReturnError, match="Rev. Proc. 2002-69"):
        run(partnership(classification="disregarded", guaranteed_payments=[]))


def test_spouses_in_community_property_state_may_be_disregarded():
    d = partnership(classification="disregarded", guaranteed_payments=[])
    r = run(d, spouses=("a1", "b1"), household_state="CA")
    assert has(r.findings, "Rev. Proc. 2002-69")
    # §1402(a)(5)(A): split by share when no se_share is recorded
    assert [x["owner"] for x in r.schedule_c] == ["a1", "b1"]
    assert r.schedule_c[0]["gross_receipts"] == 50_000
    assert has(r.findings, "§1402(a)(5)(A)")


def test_spouse_se_share_puts_all_on_the_working_spouse():
    d = partnership(classification="disregarded", guaranteed_payments=[])
    d["owners"][0]["se_share"] = 1.0
    d["owners"][1]["se_share"] = 0.0
    r = run(d, spouses=("a1", "b1"), household_state="CA")
    assert [x["owner"] for x in r.schedule_c] == ["a1"]
    assert r.schedule_c[0]["gross_receipts"] == 100_000


def test_spouse_partnership_gets_the_alternative_noted():
    r = run(partnership(), spouses=("a1", "b1"), household_state="TX")
    assert has(r.findings, "§761(f)")


def test_spouses_outside_community_property_state_get_no_note():
    r = run(partnership(), spouses=("a1", "b1"), household_state="NY")
    assert not has(r.findings, "2002-69")


def test_shares_must_sum_to_one():
    d = partnership()
    d["owners"][0]["share"] = 0.6
    with pytest.raises(L.LLCReturnError, match="sum"):
        run(d)


def test_unknown_classification_and_missing_classification():
    with pytest.raises(L.LLCReturnError, match="must be one of"):
        run(base(classification="llp"))
    with pytest.raises(L.LLCReturnError) as e:
        run(base(classification=None))
    assert e.value.missing == ["classification"]


def test_formed_after_year_is_an_error():
    with pytest.raises(L.LLCReturnError, match="after tax year"):
        run(base(formed_on="2027-01-05"))


# ── S corporation ───────────────────────────────────────────────────────


def test_s_corp_officer_wages_and_payroll_tax_deducted_no_se():
    # 100,000 − 10,000 − 50,000 − 3,867 = 36,133
    r = run(s_corp())
    assert r.net == pytest.approx(36_133)
    assert r.k1[0]["form"] == "1120S" and r.k1[0]["se_earnings"] == 0
    assert r.k1[0]["qbi_w2_wages"] == 50_000
    assert r.w2[0]["wages"] == 50_000
    assert ("7", "Compensation of officers", -50_000) in r.lines
    assert has(r.se_note, "no self-employment tax")


def test_s_corp_taxes_and_payroll_tax_share_line_12():
    r = run(s_corp(expenses={"supplies": 10_000, "taxes_and_licenses": 1_000}))
    line12 = [x for x in r.lines if x[0] == "12"]
    assert line12 == [("12", "Taxes and licenses (incl. employer payroll tax)", -4_867)]


def test_s_corp_requires_election_date():
    with pytest.raises(L.LLCReturnError) as e:
        run(s_corp(s_election_effective=None))
    assert e.value.missing == ["s_election_effective"]


def test_mid_year_election_is_refused():
    with pytest.raises(L.LLCReturnError, match="partway"):
        run(s_corp(s_election_effective="2026-04-01"))


def test_election_in_formation_year_from_formation_is_fine():
    r = run(s_corp(formed_on="2026-03-01", s_election_effective="2026-03-01"))
    assert r.classification == "s_corp"


def test_election_after_year_is_an_error():
    with pytest.raises(L.LLCReturnError, match="not an S corporation"):
        run(s_corp(s_election_effective="2027-01-01"))


def test_reasonable_comp_flag_at_zero_wages():
    r = run(s_corp(officer_wages=[], payroll_taxes_employer=0))
    assert r.reasonable_comp["status"] == "flag"
    assert has(r.findings, "Rev. Rul. 74-44")


def test_reasonable_comp_review_when_wages_below_distributions():
    r = run(s_corp(distributions=[{"member": "a1", "amount": 80_000}]))
    assert r.reasonable_comp["status"] == "review"
    assert any("reasonable_salary_floor" in x for x in r.missing)


def test_reasonable_comp_flag_below_asserted_floor():
    r = run(s_corp(reasonable_salary_floor=60_000))
    assert r.reasonable_comp["status"] == "flag"


def test_reasonable_comp_no_flag():
    r = run(s_corp())
    assert r.reasonable_comp["status"] == "no flag"


def test_payroll_tax_below_employer_fica_is_flagged():
    r = run(s_corp(payroll_taxes_employer=1_000))
    assert has(r.findings, "below the employer FICA")


def test_disproportionate_s_corp_distributions_flag_second_class_of_stock():
    d = s_corp(owners=[{"member": "a1", "share": 0.5, "active": True},
                       {"member": "b1", "share": 0.5, "active": False}],
               distributions=[{"member": "a1", "amount": 30_000},
                              {"member": "b1", "amount": 10_000}])
    r = run(d)
    assert has(r.findings, "second class of stock")


def test_officer_wages_only_in_s_corp_and_gp_only_in_partnership():
    with pytest.raises(L.LLCReturnError, match="officer wages exist only"):
        run(partnership(officer_wages=[{"member": "a1", "amount": 1}]))
    with pytest.raises(L.LLCReturnError, match="guaranteed payments exist only"):
        run(s_corp(guaranteed_payments=[{"member": "a1", "amount": 1}]))


def test_officer_wage_or_payroll_tax_null_stops():
    with pytest.raises(L.LLCReturnError) as e:
        run(s_corp(officer_wages=[{"member": "a1", "amount": None}]))
    assert "officer_wages[0].amount" in e.value.missing
    with pytest.raises(L.LLCReturnError) as e:
        run(s_corp(payroll_taxes_employer=None))
    assert "payroll_taxes_employer" in e.value.missing


# ── California ──────────────────────────────────────────────────────────


def test_ca_partnership_568_fee_penalty_and_first_year_tax():
    # total income 300,000 → fee 900; estimate 0 → penalty 90; formed Feb 10 2026,
    # so FTB 3536 is due the 15th of the 6th month counting February: July 15.
    d = partnership(state="CA", gross_receipts=300_000, formed_on="2026-02-10",
                    estimated_payments=[800, 0, 0, 0])
    r = run(d)
    ca = r.ca
    assert ca["form"] == "568" and ca["fee"] == 900 and ca["fee_penalty"] == 90
    assert ca["fee_due"] == dt.date(2026, 7, 15)
    assert ca["late_per_month"] == 2 * 18
    assert ca["annual_tax"] == 800 and ca["annual_due"] == dt.date(2026, 5, 15)
    assert ca["return_due"] == dt.date(2027, 3, 15)
    assert ca["balance"] == 900
    assert r.ca_llc is None


def test_ca_fee_base_adds_back_cogs():
    # 260,000 receipts − 20,000 COGS: fee base is still 260,000 (≥ 250,000)
    r = run(base(state="CA", gross_receipts=260_000, cost_of_goods_sold=20_000))
    assert r.ca["total_income"] == 260_000 and r.ca["fee"] == 900


def test_ca_disregarded_due_april_and_hands_off_to_ca_return():
    r = run(base(state="CA"))
    assert r.ca["return_due"] == dt.date(2027, 4, 15) and r.ca["fee"] == 0
    assert r.ca_llc == {"name": "Test Co LLC", "gross_receipts_total_income": 100_000,
                        "formed_year": 2020, "formed_on": "2020-01-01"}


def test_ca_first_year_exemption_window_reused_from_ca_return():
    r = run(base(state="CA", formed_on="2022-06-01"), year=2022)
    assert r.ca["annual_tax"] == 0


def test_ca_s_corp_franchise_tax_and_no_llc_fee():
    # OBI 36,133 × 1.5% = 542 < 800 → 800
    r = run(s_corp(state="CA", estimated_payments=[800, 0, 0, 0]))
    assert r.ca["form"] == "100S" and r.ca["tax"] == 800
    assert r.ca["fee"] is None and r.ca["annual_tax"] is None
    big = run(s_corp(state="CA", gross_receipts=300_000,
                     estimated_payments=[800, 0, 0, 0]))
    assert big.ca["tax"] == pytest.approx((300_000 - 63_867) * 0.015)
    assert has(big.findings, "100-ES installments fell short")
    # $800 minimum, all paid with installment 1: no shortfall
    assert not has(r.findings, "fell short")


def test_corp_es_installments_cumulative_schedule():
    assert L.corp_es_installments(800) == [800, 0, 0, 0]
    # 1,574: targets 800 (30% = 472, floored), 1,102 (70%), 1,102, 1,574
    assert L.corp_es_installments(1_574) == pytest.approx([800, 301.8, 0, 472.2])
    # 10,000: 3,000 / 4,000 / 0 / 3,000
    assert L.corp_es_installments(10_000) == pytest.approx([3_000, 4_000, 0, 3_000])


def test_fee_estimate_not_due_when_first_year_ends_before_sixth_month():
    d = base(state="CA", gross_receipts=600_000, formed_on="2026-08-01",
             estimated_payments=[800, 0, 0, 0])
    r = run(d)
    assert r.ca["fee_due"] is None and r.ca["fee_penalty"] == 0
    assert r.ca["fee"] == 2_500


def test_fee_penalty_prior_year_safe_harbor():
    d = base(state="CA", gross_receipts=600_000, estimated_payments=[800, 900, 0, 0])
    unknown = run(d)
    assert unknown.ca["fee_penalty"] == 160         # 10% × (2,500 − 900)
    assert has(unknown.findings, "upper bound")
    assert any("prior_year_fee" in x for x in unknown.missing)
    safe = run(dict(d, prior_year_fee=900))
    assert safe.ca["fee_penalty"] == 0
    short = run(dict(d, prior_year_fee=2_500))
    assert short.ca["fee_penalty"] == 160


def test_fifteen_day_rule():
    late = base(state="CA", formed_on="2026-12-20")
    r = run(late)                                    # 12 days, business unknown
    assert r.ca["annual_tax"] == 800 and r.ca["short_year"] == 12
    assert has(r.bounds, "§17946")
    r = run(dict(late, did_business_in_short_year=False))
    assert r.ca["annual_tax"] == 0 and r.ca["return_due"] is None
    r = run(dict(late, did_business_in_short_year=True))
    assert r.ca["annual_tax"] == 800
    assert run(base(state="CA", formed_on="2026-12-16")).ca["short_year"] is None


def test_ca_s_corp_first_year_minimum_is_flagged_not_waived():
    r = run(s_corp(state="CA", formed_on="2026-01-01",
                   s_election_effective="2026-01-01"))
    assert r.ca["tax"] == 800
    assert has(r.findings, "§23153(f)")


def test_ca_payments_null_leave_balance_undetermined():
    r = run(base(state="CA", estimated_payments=None))
    assert r.ca["balance"] is None and r.ca["fee_penalty"] is None


def test_other_state_is_named_not_modelled_and_missing_state_listed():
    assert has(run(base(state="NY")).findings, "not modelled")
    assert any("state" in x for x in run(base(state=None)).missing)


# ── 1099-NEC ────────────────────────────────────────────────────────────


def contractors(*rows):
    return base(contractors=list(rows), expenses={"contract_labor": 10_000})


def test_nec_threshold_by_year():
    d = contractors({"name": "P", "amount": 1_000, "w9_on_file": True,
                     "entity_type": "individual"})
    assert run(d, year=2025).nec["payees"][0]["required"] is True
    assert run(d, year=2026).nec["payees"][0]["required"] is False


def test_nec_corporation_exempt_unless_attorney():
    d = contractors({"name": "C", "amount": 5_000, "w9_on_file": True,
                     "entity_type": "corporation"},
                    {"name": "Law", "amount": 5_000, "w9_on_file": True,
                     "entity_type": "corporation", "attorney": True})
    p = run(d).nec["payees"]
    assert p[0]["required"] is False and p[1]["required"] is True


def test_nec_missing_w9_flags_backup_withholding():
    r = run(contractors({"name": "X", "amount": 10_000, "w9_on_file": False,
                         "entity_type": "individual"}))
    assert r.nec["backup_withholding"] == 2_400
    assert has(r.findings, "backup withholding")


def test_nec_unknown_entity_type_is_undetermined():
    r = run(contractors({"name": "U", "amount": 10_000, "w9_on_file": True}))
    assert r.nec["payees"][0]["required"] is None
    assert any("entity_type" in x for x in r.missing)


def test_nec_null_list_is_undetermined_and_absent_list_with_labour_is_flagged():
    assert run(base(contractors=None)).nec["undetermined"] is True
    assert has(run(base(expenses={"contract_labor": 5_000})).findings,
               "no contractors listed")


def test_nec_due_jan_31_rolled_and_de542_in_ca():
    d = contractors({"name": "X", "amount": 1_000, "w9_on_file": True,
                     "entity_type": "individual"})
    d["state"] = "CA"
    r = run(d)
    assert r.nec["due"] == dt.date(2027, 2, 1)        # Jan 31 2027 is Sunday
    assert r.nec["de542"] == ["X"]


# ── unknown is not zero, refusals, projection ───────────────────────────


@pytest.mark.parametrize("key", ["gross_receipts", "cost_of_goods_sold", "meals"])
def test_null_income_figures_stop(key):
    with pytest.raises(L.LLCReturnError) as e:
        run(base(**{key: None}))
    assert key in e.value.missing


def test_null_expense_stops():
    with pytest.raises(L.LLCReturnError) as e:
        run(base(expenses={"supplies": None}))
    assert "expenses.supplies" in e.value.missing


def test_null_depreciation_bounds():
    r = run(base(depreciation=None))
    assert has(r.bounds, "depreciation is not recorded")
    assert "depreciation" in r.missing


@pytest.mark.parametrize("extra, pointer", [
    ({"rental_properties": [{"x": 1}]}, "passive-loss-eligibility"),
    ({"activity": "rental"}, "passive-loss-eligibility"),
    ({"depreciation": [{"asset": "van"}]}, "depreciation-election"),
    ({"inventory": {"method": "fifo"}}, "cost_of_goods_sold"),
    ({"apportionment": True}, "apportionment"),
    ({"section_754": True}, "§754"),
    ({"special_allocations": True}, "special allocations"),
    ({"payroll_filings": True}, "941"),
    ({"classification": "c_corp"}, "Form 1120"),
])
def test_refusals_point_elsewhere(extra, pointer):
    with pytest.raises(L.LLCReturnError, match="out of scope") as e:
        run(base(**extra))
    assert pointer.lower() in str(e.value).lower()


def test_foreign_owner_refused():
    d = base()
    d["owners"][0]["foreign"] = True
    with pytest.raises(L.LLCReturnError, match="§1446"):
        run(d)


def test_unpublished_year_uses_nearest_and_says_projection():
    r = run(base(), year=2030)
    assert r.projection is True
    assert has(r.findings, "projection")
    t, proj = L.table_for(2024)
    assert proj and t is L.LLC_TABLES[2025]


# ── hobby loss ──────────────────────────────────────────────────────────


def test_hobby_presumption_not_met_with_two_profits_in_five():
    hist = [{"year": 2022, "net": 1_000}, {"year": 2023, "net": -500},
            {"year": 2024, "net": 2_000}, {"year": 2025, "net": -800}]
    r = run(base(expenses={"supplies": 110_000}, prior_year_results=hist))
    assert has(r.findings, "Hobby-loss risk")


def test_hobby_loss_without_history_asks_for_it():
    r = run(base(expenses={"supplies": 110_000}))
    assert has(r.findings, "prior_year_results")


def test_profit_raises_no_hobby_note():
    assert not has(run(base()).findings, "§183")


def test_inputs_are_not_mutated():
    d = partnership(state="CA")
    before = copy.deepcopy(d)
    run(d)
    assert d == before


# ── review fixes ────────────────────────────────────────────────────────


def test_w9_unknown_is_bounded_not_backup_withholding():
    r = run(contractors({"name": "N", "amount": 10_000, "entity_type": "llc"}))
    assert r.nec["backup_withholding"] == 0
    assert any("w9_on_file" in x for x in r.missing)
    assert has(r.bounds, "cannot be ruled out")


def test_card_payments_are_1099k_not_nec():
    r = run(contractors({"name": "K", "amount": 10_000, "entity_type": "individual",
                         "paid_via": "card"}))
    assert r.nec["payees"][0]["required"] is False
    assert has(r.findings, "1099-K")


def test_de542_lists_unknown_type_as_undetermined():
    d = contractors({"name": "U", "amount": 700, "w9_on_file": True})
    d["state"] = "CA"
    assert run(d).nec["de542"] == ["U (if an individual — type unknown)"]


def test_nondeductible_meals_reduce_basis_before_losses():
    # S corp: 2,000 receipts − 20,000 supplies − 500 meals deductible − 50,000 wages …
    d = s_corp(gross_receipts=0, expenses={"supplies": 20_000}, meals=1_000,
               officer_wages=[], payroll_taxes_employer=0,
               distributions=[{"member": "a1", "amount": 3_000}],
               owner_basis_start=[{"member": "a1", "amount": 5_000}])
    r = run(d)
    b = r.basis[0]
    # loss 20,500; basis 5,000 − 3,000 distributions − 500 nondeductible = 1,500
    assert b["nondeductible"] == 500 and b["allowed_loss"] == 1_500
    assert ("16C", "Nondeductible expenses", 500) in r.k1_boxes["a1"]


def test_contributions_increase_basis():
    d = partnership(guaranteed_payments=[{"member": "a1", "amount": 130_000}],
                    contributions=[{"member": "a1", "amount": 10_000}],
                    owner_basis_start=[{"member": "a1", "amount": 5_000},
                                       {"member": "b1", "amount": 50_000}])
    a = next(b for b in run(d).basis if b["member"] == "a1")
    assert a["allowed_loss"] == 15_000 and a["suspended"] == 5_000


def test_basis_row_for_non_owner_is_an_error():
    with pytest.raises(L.LLCReturnError, match="not an owner"):
        run(partnership(owner_basis_start=[{"member": "zz", "amount": 1}]))


def test_schedule_c_handoff_never_negative_and_federal_agrees():
    r = run(base(gross_receipts=1_000, cost_of_goods_sold=5_000, expenses={},
                 other_income=-200))
    [sc] = r.schedule_c
    assert sc["gross_receipts"] == 1_000
    assert sc["expenses"]["cost_of_goods_sold"] == 5_000
    tr = {"tax_year": 2026, "filing_status": "single",
          "taxpayers": [{"member": "a1", "age": 45}], "w2": [], "schedule_c": [sc],
          "estimated_payments": {"federal": [0, 0, 0, 0]},
          "prior_year": {"agi": 50_000, "federal_total_tax": 5_000}}
    assert FED.compute(tr).schedule_c_net == pytest.approx(r.net) == -4_200


def test_returns_above_receipts_is_an_error():
    with pytest.raises(L.LLCReturnError, match="exceed"):
        run(base(returns_and_allowances=200_000))


@pytest.mark.parametrize("cls_fn, text", [
    (base, "Schedule 1"), (partnership, "box 13"), (s_corp, "2008-1")])
def test_owner_retirement_and_health_lines_are_flagged(cls_fn, text):
    r = run(cls_fn(expenses={"supplies": 10_000, "retirement_plans": 5_000}))
    assert has(r.findings, text)


def test_officer_w2_uses_federal_field_names():
    w = run(s_corp()).w2[0]
    assert {"ss_wages", "ss_withheld", "medicare_wages", "medicare_withheld"} <= set(w)
    assert w["ss_wages"] == 50_000 and w["medicare_withheld"] == 725


def test_officer_w2_withholding_absent_is_unknown_not_zero():
    r = run(s_corp(officer_wages=[{"member": "a1", "amount": 50_000}]))
    assert r.w2[0]["ss_withheld"] is None
    assert any("ss_withheld" in x for x in r.missing)


def test_material_participation_is_separate_from_active():
    d = partnership()
    d["owners"][1]["material_participation"] = True
    r = run(d)
    assert r.k1[1]["material_participation"] is True and r.k1[1]["se_earnings"] == 0
    assert r.k1[0]["material_participation"] is None
    assert any("material_participation" in x for x in r.missing)


def test_box_4c_and_18c_on_partnership_k1():
    r = run(partnership(meals=2_000))
    boxes = {b[0]: b[2] for b in r.k1_boxes["a1"]}
    assert boxes["4c"] == 30_000 and boxes["18C"] == 500


def test_depreciation_on_1065_is_line_16c():
    r = run(partnership(depreciation=1_000))
    assert any(ln == "16c" for ln, _, _ in r.lines)
