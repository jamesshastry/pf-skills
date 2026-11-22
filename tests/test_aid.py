"""Student Aid Index arithmetic. All figures are synthetic."""
import pytest

from pf import aid as A

T = A.AID_TABLES["2026-27"]


def parent(**kw):
    base = dict(total_income=100_000, federal_income_tax=8_000,
                earned_income=100_000, family_size=4, older_parent_age=50,
                two_parents=True, assets=0, income_year=2024)
    base.update(kw)
    return A.ParentInputs(**base)


def test_assessment_schedule_band_edges_by_hand():
    assert A.assess(-9_000, T) == -1870                     # below the floor
    assert A.assess(-8_500, T) == pytest.approx(-1870)      # 22% x -8,500
    assert A.assess(21_800, T) == pytest.approx(4796)
    assert A.assess(27_300, T) == pytest.approx(4796 + 0.25 * 5_500)
    assert A.assess(43_900, T) == pytest.approx(9670 + 0.40 * 5_500)
    assert A.assess(100_000, T) == pytest.approx(11870 + 0.47 * 56_100)


def test_income_protection_extends_past_the_table():
    assert A.parent_ipa(T, 4) == 44880
    assert A.parent_ipa(T, 8) == 61930 + 2 * 6990
    with pytest.raises(ValueError):
        A.parent_ipa(T, 1)


def test_payroll_allowance_doubles_the_wage_base_on_a_joint_return():
    # §1087oo(c)(2): "twice such contribution and benefit base, in the case of
    # a joint return" — for the parents together, whoever earns it.
    joint = A.payroll_allowance(300_000, 100_000, joint=True)
    single = A.payroll_allowance(300_000, 100_000, joint=False)
    assert joint == pytest.approx(300_000 * 0.0145 + 50_000 * 0.009
                                  + 200_000 * 0.062)
    assert single == pytest.approx(300_000 * 0.0145 + 100_000 * 0.009
                                   + 100_000 * 0.062)


def test_payroll_allowance_below_the_additional_medicare_threshold():
    assert A.payroll_allowance(150_000, 100_000, joint=True) == pytest.approx(
        150_000 * 0.0145 + 150_000 * 0.062)


def test_parent_contribution_by_hand():
    r = A.parent_contribution(parent(assets=50_000), "2026-27")
    allow = 8_000 + (100_000 * 0.0145 + 100_000 * 0.062) + 44_880 + 5_000
    available = 100_000 - allow
    assert r.available_income == pytest.approx(available)
    assert r.asset_contribution_income == pytest.approx(6_000)
    assert r.parent_contribution == pytest.approx(A.assess(available + 6_000, T))
    assert r.parent_contribution_income_only == pytest.approx(A.assess(available, T))
    assert not r.projected_table and not r.projected_wage_base


def test_employment_expense_allowance_is_capped():
    low = A.parent_contribution(parent(earned_income=10_000), "2026-27")
    assert low.allowances["employment expense allowance"] == pytest.approx(3_500)
    high = A.parent_contribution(parent(earned_income=500_000), "2026-27")
    assert high.allowances["employment expense allowance"] == 5_000


def test_student_income_is_floored_at_zero_and_assets_at_20_percent():
    sc = A.student_contribution(income=5_000, federal_income_tax=0,
                                earned_income=5_000, assets=10_000,
                                income_year=2024, award_year="2026-27")
    assert sc == pytest.approx(2_000)
    working = A.student_contribution(income=30_000, federal_income_tax=1_000,
                                     earned_income=30_000, assets=0,
                                     income_year=2024, award_year="2026-27")
    adj = 1_000 + 30_000 * (0.0145 + 0.062) + 11_770
    assert working == pytest.approx((30_000 - adj) * 0.5)


def test_sai_floor():
    r = A.parent_contribution(parent(total_income=10_000, federal_income_tax=0,
                                     earned_income=10_000), "2026-27")
    assert A.sai(r, 0) == -1500


def test_unpublished_years_are_projected_and_say_so():
    r = A.parent_contribution(parent(income_year=2097), "2099-00")
    assert r.projected_table and r.projected_wage_base
    text = " ".join(A.assessment_findings(r, {"x": 50_000}))
    assert "not yet published" in text


def test_need_is_cost_less_nonnegative_sai():
    assert A.need(40_000, 25_000) == 15_000
    assert A.need(40_000, 60_000) == 0
    assert A.need(40_000, -1_500) == 40_000


def test_classification_excludes_retirement_insurance_home_pending_and_foreign_on_request():
    rows = [
        {"name": "cash", "value": 10, "tier": "liquid"},
        {"name": "k401", "value": 20, "tier": "age_restricted"},
        {"name": "policy", "value": 30, "tier": "liquid", "vehicle": "ulip_fund"},
        {"name": "home", "value": 40, "tier": "illiquid", "primary_residence": True},
        {"name": "order", "value": 50, "tier": "liquid", "pending": True},
        {"name": "abroad", "value": 60, "tier": "illiquid", "country": "IN"},
        {"name": "fund", "value": 70, "tier": "illiquid"},
    ]
    worldwide = {x.name: x.counted for x in A.classify_assets(rows, include_foreign=True)}
    assert worldwide == {"cash": True, "k401": False, "policy": False, "home": False,
                         "order": False, "abroad": True, "fund": True}
    us_only = {x.name: x.counted for x in A.classify_assets(rows, include_foreign=False)}
    assert us_only["abroad"] is False and us_only["fund"] is True


# BRANCH: income alone exceeds the highest cost — assets cannot create need.
def test_findings_income_alone_above_cost():
    r = A.parent_contribution(parent(total_income=400_000, federal_income_tax=70_000,
                                     earned_income=400_000), "2026-27")
    text = A.assessment_findings(r, {"public": 45_000, "private": 90_000})[0]
    assert "No asset decision can create need-based aid" in text


# BRANCH: assets, not income, push SAI above cost.
def test_findings_assets_push_above_cost():
    r = A.parent_contribution(parent(total_income=150_000, federal_income_tax=14_000,
                                     earned_income=150_000, assets=600_000), "2026-27")
    assert r.parent_contribution_income_only < 45_000 <= r.parent_contribution
    text = A.assessment_findings(r, {"public": 45_000})[0]
    assert "reportable assets push the SAI above cost" in text


# BRANCH: need is plausible.
def test_findings_need_plausible():
    r = A.parent_contribution(parent(), "2026-27")
    text = A.assessment_findings(r, {"public": 45_000})[0]
    assert "Need-based aid is plausible" in text


def test_no_costs_cannot_be_determined():
    r = A.parent_contribution(parent(), "2026-27")
    assert "cannot be determined" in A.assessment_findings(r, {})[0]


def test_income_year_must_be_prior_prior_year():
    with pytest.raises(A.AidError, match="2024"):
        A.parent_contribution(parent(income_year=2026), "2026-27")


def test_negative_tax_or_earnings_are_refused():
    with pytest.raises(A.AidError):
        A.parent_contribution(parent(earned_income=-1), "2026-27")


def test_years_before_the_shipped_tables_are_not_called_unpublished():
    r = A.parent_contribution(parent(income_year=1997), "1999-00")
    text = " ".join(A.assessment_findings(r, {"x": 50_000}))
    assert r.projected_table and "not in this module" in text
    assert "not yet published" not in text


def test_projected_income_verdict_is_not_bold_and_shows_its_margin():
    r = A.parent_contribution(parent(total_income=400_000, federal_income_tax=70_000,
                                     earned_income=400_000, income_year=2097),
                              "2099-00")
    text = A.assessment_findings(r, {"public": 45_000})[0]
    assert not text.startswith("**") and "recheck" in text and "margin" in text


def test_parents_negative_aai_shelters_student_income():
    # Parents' AAI -5,000 adds 5,000 to the student's allowances.
    base = dict(income=20_000, federal_income_tax=0, earned_income=20_000,
                assets=0, income_year=2024, award_year="2026-27")
    plain = A.student_contribution(**base)
    sheltered = A.student_contribution(**base, parents_aai=-5_000)
    assert plain - sheltered == pytest.approx(2_500)
    assert A.student_contribution(**base, parents_aai=5_000) == pytest.approx(plain)


def test_classification_handles_unknown_liabilities_vehicles_margin_and_business():
    rows = [
        {"name": "unknown", "value": None, "tier": "liquid"},
        {"name": "heloc", "value": -60_000, "tier": "liquid"},
        {"name": "minivan", "value": 20_000, "tier": "illiquid", "vehicle": "car"},
        {"name": "broker", "value": 50_000, "tier": "liquid", "margin_debt": 8_000},
        {"name": "shop", "value": 90_000, "tier": "illiquid", "vehicle": "business_equity"},
    ]
    got = {x.name: (x.counted, x.value) for x in A.classify_assets(rows, include_foreign=True)}
    assert got["unknown"] == (False, 0.0)
    assert got["heloc"][0] is False and got["minivan"][0] is False
    assert got["broker"] == (True, 42_000)
    assert got["shop"] == (True, 90_000)


MEMBERS = [{"id": "p1", "role": "primary"}, {"id": "p2", "role": "spouse"},
           {"id": "k1", "role": "dependent", "fafsa_eligible": True}]
FA = dict(award_year="2026-27", income_year=2024, parent_total_income=60_000,
          parent_federal_income_tax=2_000, parent_earned_income=60_000,
          family_size=3, older_parent_age=45, two_parents=True,
          cost_of_attendance={"public": 30_000},
          students={"k1": {"income": 0, "federal_income_tax": 0, "earned_income": 0}})


def _hh(accounts, sheet=None, fa=None):
    return A.household(fa or FA, balance_sheet=sheet or [], members=MEMBERS,
                       accounts=accounts)


def test_student_owned_529_is_a_parent_asset_and_utma_a_student_asset():
    h = _hh([{"name": "k1_529", "value": 50_000, "owner": "k1", "beneficiary": "k1",
              "vehicle": "529"},
             {"name": "k1_utma", "value": 10_000, "owner": "k1", "beneficiary": "k1",
              "vehicle": "utma_custodial"}])
    assert h.parent.reportable_assets == 50_000
    assert h.students[0].student_assets == 10_000


def test_student_owned_account_without_vehicle_is_refused():
    with pytest.raises(A.AidError, match="vehicle"):
        _hh([{"name": "k1_acct", "value": 1, "owner": "k1"}])


def test_accounts_linked_to_an_aggregate_row_are_not_counted_twice():
    sheet = [{"id": "edu", "name": "college", "value": 100_000, "tier": "illiquid",
              "earmark": "education"}]
    accts = [{"name": "a", "value": 60_000, "owner": "p1", "balance_sheet_row": "edu"},
             {"name": "b", "value": 40_000, "owner": "p1", "balance_sheet_row": "edu"}]
    assert _hh(accts, sheet).parent.reportable_assets == 100_000


def test_unlinked_account_beside_an_earmarked_row_is_ambiguous():
    sheet = [{"name": "college", "value": 100_000, "tier": "illiquid",
              "earmark": "education"}]
    with pytest.raises(A.AidError, match="balance_sheet_row"):
        _hh([{"name": "a", "value": 60_000, "owner": "p1"}], sheet)


def test_parent_account_off_the_sheet_is_added_once():
    sheet = [{"name": "cash", "value": 10_000, "tier": "liquid"}]
    h = _hh([{"name": "a", "value": 100_000, "owner": "p1"}], sheet)
    assert h.parent.reportable_assets == 110_000


def test_missing_student_income_and_costs_are_flagged_not_zeroed():
    fa = dict(FA, students={}, cost_of_attendance={"public": 30_000, "private": None})
    h = _hh([], fa=fa)
    assert not h.students[0].income_recorded
    text = " ".join(h.findings)
    assert "private" in text and "lower bounds" in text
