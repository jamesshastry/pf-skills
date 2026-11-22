"""Indian return workpaper arithmetic. All figures are synthetic and checked by hand."""
import copy

import pytest

from pf import india_return as I

T = I.INDIA_TABLES["2025-26"]
MEMBERS = [{"id": "p1", "role": "primary", "citizenship": ["US"], "birth_year": 1980}]


def itr(**kw):
    """A non-resident with nothing but what the test adds."""
    base = {
        "financial_year": "2025-26",
        "taxpayer": {"member": "p1", "person_of_indian_origin": True,
                     "days_in_india_this_fy": 20, "days_in_india_prior_4_fy": 100,
                     "days_in_india_prior_7_fy": 200, "nri_years_in_prior_10": 10,
                     "liable_to_tax_elsewhere": True},
        "regime": None,
        "usd_inr_rate": 80.0,
        "expected_filing_date": "2026-07-15",
        "advance_tax_paid_inr": 0,
        "self_assessment_tax_paid_inr": 0,
    }
    tp = kw.pop("taxpayer", None)
    base.update(kw)
    if tp:
        base["taxpayer"] = {**base["taxpayer"], **tp}
    return base


def nro(amount, tds=0, kind="nro_fd"):
    return {"account": f"acct-{kind}-{amount}", "kind": kind, "amount_inr": amount,
            "tds_inr": tds}


def run(x, members=MEMBERS):
    return I.compute(x, members=members)


# ── helpers ────────────────────────────────────────────────────────────────

def test_round_to_nearest_ten():
    assert I.round10(316_893) == 316_890
    assert I.round10(316_895) == 316_900
    assert I.round10(-284_001) == -284_000


def test_slab_tax_by_hand():
    assert I.slab_tax(1_000_000, T.new_slabs) == pytest.approx(20_000 + 20_000)
    assert I.slab_tax(1_000_000, T.old_slabs["below_60"]) == pytest.approx(112_500)
    assert I.slab_tax(2_500_000, T.new_slabs) == pytest.approx(300_000 + 30_000)
    assert I.slab_tax(400_000, T.new_slabs) == 0


def test_holding_period_boundary():
    import datetime as dt
    a = dt.date(2024, 5, 10)
    assert not I._long_term(a, dt.date(2025, 5, 10), 12)    # exactly 12 months
    assert I._long_term(a, dt.date(2025, 5, 11), 12)        # more than 12
    assert not I._long_term(a, dt.date(2026, 5, 10), 24)
    assert I._long_term(a, dt.date(2026, 5, 11), 24)


def test_financial_year_format_is_checked():
    with pytest.raises(I.IndiaReturnError):
        I.fy_start("2025-27")
    assert I.fy_start("2025-26") == 2025


# ── residential status ─────────────────────────────────────────────────────

def res(tp, citizen=False, income=0):
    return I.residence(tp, indian_citizen=citizen, indian_income=income)


def test_182_days_resident_then_rnor_by_history():
    r = res({"days_in_india_this_fy": 190, "nri_years_in_prior_10": 9,
             "days_in_india_prior_7_fy": 2000})
    assert r.status == I.RNOR
    r = res({"days_in_india_this_fy": 190, "nri_years_in_prior_10": 2,
             "days_in_india_prior_7_fy": 729})
    assert r.status == I.RNOR
    r = res({"days_in_india_this_fy": 190, "nri_years_in_prior_10": 2,
             "days_in_india_prior_7_fy": 730})
    assert r.status == I.ROR


def test_resident_without_history_stops():
    with pytest.raises(I.IndiaReturnError, match="ordinarily resident"):
        res({"days_in_india_this_fy": 200, "nri_years_in_prior_10": 1})


def test_pio_visitor_gets_182_days_below_15_lakh():
    r = res({"days_in_india_this_fy": 150, "days_in_india_prior_4_fy": 400,
             "person_of_indian_origin": True}, income=1_000_000)
    assert r.status == I.NR


def test_pio_visitor_above_15_lakh_uses_120_days_and_is_rnor():
    tp = {"days_in_india_this_fy": 130, "days_in_india_prior_4_fy": 400,
          "person_of_indian_origin": True, "nri_years_in_prior_10": 0,
          "days_in_india_prior_7_fy": 2000}
    assert res(tp, income=1_600_000).status == I.RNOR
    assert res({**tp, "days_in_india_this_fy": 119}, income=1_600_000).status == I.NR


def test_foreigner_without_indian_origin_uses_60_days():
    tp = {"days_in_india_this_fy": 70, "days_in_india_prior_4_fy": 365,
          "person_of_indian_origin": False, "nri_years_in_prior_10": 0,
          "days_in_india_prior_7_fy": 1500}
    assert res(tp).status == I.ROR
    assert res({**tp, "days_in_india_prior_4_fy": 364}).status == I.NR


def test_citizen_leaving_for_employment_uses_182():
    tp = {"days_in_india_this_fy": 150, "days_in_india_prior_4_fy": 800,
          "left_india_for_employment_this_fy": True}
    assert res(tp, citizen=True).status == I.NR


def test_60_day_band_without_prior_years_stops():
    with pytest.raises(I.IndiaReturnError, match="prior_4"):
        res({"days_in_india_this_fy": 90})


def test_origin_unknown_stops_when_it_decides():
    with pytest.raises(I.IndiaReturnError, match="origin"):
        res({"days_in_india_this_fy": 90, "days_in_india_prior_4_fy": 400},
            citizen=None)


def test_deemed_resident_citizen_not_taxed_elsewhere():
    tp = {"days_in_india_this_fy": 10}
    assert res({**tp, "liable_to_tax_elsewhere": False}, citizen=True,
               income=1_600_000).status == I.RNOR
    assert res({**tp, "liable_to_tax_elsewhere": True}, citizen=True,
               income=1_600_000).status == I.NR
    assert res(tp, citizen=True, income=1_400_000).status == I.NR
    with pytest.raises(I.IndiaReturnError, match="liable_to_tax_elsewhere"):
        res(tp, citizen=True, income=1_600_000)


def test_days_unknown_stops():
    with pytest.raises(I.IndiaReturnError, match="days_in_india_this_fy"):
        res({})


def test_citizenship_comes_from_the_member():
    assert I._indian_citizen({"taxpayer": {"member": "p1"}}, MEMBERS) is False
    assert I._indian_citizen({"taxpayer": {"member": "p1"}},
                             [{"id": "p1", "citizenship": ["IN"]}]) is True
    assert I._indian_citizen({"taxpayer": {"member": "zz"}}, MEMBERS) is None


# ── interest ───────────────────────────────────────────────────────────────

def test_nre_fcnr_exempt_for_nr_nro_taxable():
    r = run(itr(interest=[nro(100_000), nro(50_000, kind="nre_fd"),
                          nro(30_000, kind="fcnr")]))
    n = r.regimes["new"]
    assert n.gross_total_income == 100_000
    assert r.us.india_exempt_inr == 80_000


def test_nre_exemption_follows_fema_status_not_tax_residence():
    ror = {"days_in_india_this_fy": 200, "nri_years_in_prior_10": 0,
           "days_in_india_prior_7_fy": 2000}
    x = itr(interest=[nro(50_000, kind="nre_savings")],
            taxpayer={**ror, "fema_resident_outside_india": False})
    r = run(x)
    assert r.residence.status == I.ROR
    assert r.regimes["new"].gross_total_income == 50_000
    assert "LOWER BOUND" in " ".join(r.findings)
    # FEMA status unrecorded for a resident: stop rather than guess.
    with pytest.raises(I.IndiaReturnError, match="FEMA"):
        run(itr(interest=[nro(50_000, kind="nre_fd")], taxpayer=ror))
    rnor = {"days_in_india_this_fy": 200, "nri_years_in_prior_10": 9}
    with pytest.raises(I.IndiaReturnError, match="FEMA"):
        run(itr(interest=[nro(50_000, kind="nre_fd")], taxpayer=rnor))
    ok = run(itr(interest=[nro(50_000, kind="nre_fd")],
                 taxpayer={**rnor, "fema_resident_outside_india": True}))
    assert ok.regimes["new"].gross_total_income == 0
    # Non-resident whose FEMA status is resident in India: taxable.
    nr = run(itr(interest=[nro(50_000, kind="nre_fd")],
                 taxpayer={"fema_resident_outside_india": False}))
    assert nr.regimes["new"].gross_total_income == 50_000
    # FCNR follows income-tax status: exempt for RNOR whatever FEMA says.
    f = run(itr(interest=[nro(50_000, kind="fcnr")], taxpayer=rnor))
    assert f.regimes["new"].gross_total_income == 0


def test_80tta_old_regime_only_and_capped():
    r = run(itr(interest=[nro(18_000, kind="nro_savings"), nro(500_000)]))
    assert r.regimes["old"].deductions["80TTA"] == 10_000
    assert r.regimes["new"].deductions == {}
    r = run(itr(interest=[nro(6_000, kind="nro_savings")]))
    assert r.regimes["old"].deductions["80TTA"] == 6_000


def test_80ttb_for_resident_senior_not_80tta():
    x = itr(interest=[nro(60_000, kind="nro_savings"), nro(40_000)],
            taxpayer={"days_in_india_this_fy": 200, "nri_years_in_prior_10": 9,
                      "birth_date": "1960-01-01"})
    r = run(x)
    d = r.regimes["old"].deductions
    assert "80TTA" not in d and d["80TTB"] == 50_000


# ── house property ─────────────────────────────────────────────────────────

def lo(rent, mtax=0, interest=0, **kw):
    return {"name": kw.pop("name", f"flat-{rent}"), "status": "let_out",
            "gross_rent_inr": rent, "municipal_tax_paid_inr": mtax,
            "home_loan_interest_inr": interest, "tds_inr": 0, **kw}


def so(interest, name="home"):
    return {"name": name, "status": "self_occupied", "home_loan_interest_inr": interest,
            "tds_inr": 0}


def test_let_out_nav_standard_deduction_interest():
    r = run(itr(house_property=[lo(360_000, 12_000, 50_000)]))
    assert r.regimes["new"].hp_income == pytest.approx(348_000 * 0.7 - 50_000)


def test_co_owner_share_scales_everything():
    r = run(itr(house_property=[lo(400_000, 20_000, 0, co_owner_share=0.5)]))
    assert r.regimes["new"].hp_income == pytest.approx(190_000 * 0.7)


def test_self_occupied_interest_capped_old_disallowed_new():
    r = run(itr(interest=[nro(1_000_000)], house_property=[so(300_000)]))
    assert r.regimes["old"].hp_income == -200_000
    assert r.regimes["new"].hp_income == 0
    assert r.regimes["old"].gross_total_income == 800_000


def test_hp_loss_setoff_capped_and_carried_old_regime():
    r = run(itr(interest=[nro(1_000_000)],
                house_property=[lo(100_000, 0, 400_000)]))
    old, new = r.regimes["old"], r.regimes["new"]
    loss = 400_000 - 70_000
    assert old.gross_total_income == 1_000_000 - 200_000
    assert old.carry_forward["house_property"] == pytest.approx(loss - 200_000)
    # New regime: no set-off against other heads at all.
    assert new.gross_total_income == 1_000_000
    assert new.carry_forward["house_property"] == pytest.approx(loss)


def test_brought_forward_hp_loss_only_against_hp():
    r = run(itr(interest=[nro(500_000)], house_property=[lo(200_000)],
                brought_forward_losses={"house_property_inr": 300_000}))
    old = r.regimes["old"]
    assert old.gross_total_income == 500_000
    assert old.carry_forward["house_property"] == pytest.approx(300_000 - 140_000)


def test_deemed_let_out_uses_expected_rent():
    p = {"name": "third", "status": "deemed_let_out", "expected_rent_inr": 120_000,
         "municipal_tax_paid_inr": 0, "home_loan_interest_inr": 0, "tds_inr": 0}
    r = run(itr(house_property=[p]))
    assert r.regimes["new"].hp_income == pytest.approx(84_000)


def test_more_than_two_self_occupied_stops():
    with pytest.raises(I.IndiaReturnError, match="self_occupied"):
        run(itr(house_property=[so(0, "a"), so(0, "b"), so(0, "c")]))


# ── capital gains ──────────────────────────────────────────────────────────

def cg(asset, acquired, sold, sale, cost, **kw):
    return {"name": kw.pop("name", f"{asset}-{sale}"), "asset": asset,
            "acquired": acquired, "sold": sold, "sale_inr": sale, "cost_inr": cost,
            "stt_paid": kw.pop("stt_paid", True), "tds_inr": kw.pop("tds_inr", 0), **kw}


def test_112a_exemption_and_rate_nr_no_basic_exemption():
    r = run(itr(capital_gains=[cg("listed_equity", "2020-01-01", "2025-06-01",
                                  1_000_000, 500_000)]))
    n = r.regimes["new"]
    assert n.special_tax["ltcg_112a"] == pytest.approx((500_000 - 125_000) * 0.125)
    assert n.tax == I.round10((375_000 * 0.125) * 1.04)


def test_resident_uses_basic_exemption_against_special_gains():
    x = itr(capital_gains=[cg("listed_equity", "2025-01-01", "2025-06-01",
                              600_000, 300_000)],
            taxpayer={"days_in_india_this_fy": 200, "nri_years_in_prior_10": 9})
    r = run(x)
    n = r.regimes["new"]
    # STCG 3,00,000 fully inside the ₹4 lakh basic exemption.
    assert n.exemption_used_against_special == 300_000
    assert n.special_tax["stcg_111a"] == 0
    nr = run(itr(capital_gains=x["capital_gains"]))
    assert nr.regimes["new"].special_tax["stcg_111a"] == pytest.approx(60_000)


def test_no_stt_moves_listed_equity_to_slab_or_112():
    r = run(itr(capital_gains=[
        cg("listed_equity", "2025-01-01", "2025-06-01", 200_000, 100_000, stt_paid=False),
        cg("listed_equity", "2020-01-01", "2025-06-01", 300_000, 100_000, stt_paid=False)]))
    n = r.regimes["new"]
    assert n.pools["stcg_slab"] == 100_000
    assert n.special_tax["ltcg_112"] == pytest.approx(200_000 * 0.125)


def test_debt_fund_after_april_2023_is_slab_whatever_the_holding():
    r = run(itr(capital_gains=[
        cg("debt_mf", "2023-04-01", "2026-01-01", 200_000, 100_000, stt_paid=False),
        cg("debt_mf", "2022-01-01", "2025-06-01", 200_000, 100_000, stt_paid=False)]))
    n = r.regimes["new"]
    assert n.pools["stcg_slab"] == 100_000
    assert n.pools["ltcg_112"] == 100_000


def test_property_24_months_and_nr_no_indexation():
    r = run(itr(capital_gains=[
        cg("property", "2015-01-01", "2025-06-01", 5_000_000, 3_000_000, stt_paid=False,
           transfer_expenses_inr=100_000)]))
    ln = r.lines[0]
    assert ln.pool == "ltcg_112" and ln.amount == 1_900_000
    assert "residents only" in ln.note
    r = run(itr(capital_gains=[
        cg("property", "2024-01-01", "2025-06-01", 5_000_000, 3_000_000, stt_paid=False)]))
    assert r.lines[0].pool == "stcg_slab"


def test_resident_property_flags_the_indexation_option():
    x = itr(capital_gains=[cg("property", "2015-01-01", "2025-06-01", 5_000_000,
                              3_000_000, stt_paid=False)],
            taxpayer={"days_in_india_this_fy": 200, "nri_years_in_prior_10": 9})
    assert any("indexation" in f for f in run(x).findings)


def test_54_needs_residential_and_54ec_cap():
    sale = cg("property", "2015-01-01", "2025-06-01", 20_000_000, 10_000_000,
              stt_paid=False, exemption_54ec_inr=6_000_000)
    r = run(itr(capital_gains=[sale]))
    assert r.lines[0].amount == 10_000_000 - 5_000_000
    assert r.lines[0].exempt_54 == 5_000_000
    with pytest.raises(I.IndiaReturnError, match="residential"):
        run(itr(capital_gains=[{**sale, "exemption_54_inr": 1_000_000}]))
    r = run(itr(capital_gains=[{**sale, "exemption_54_inr": 3_000_000,
                                "residential": True}]))
    assert r.lines[0].amount == 10_000_000 - 3_000_000 - 5_000_000


def test_54_ignored_on_short_term_or_non_property():
    r = run(itr(capital_gains=[cg("listed_equity", "2020-01-01", "2025-06-01",
                                  300_000, 100_000, exemption_54ec_inr=100_000)]))
    assert r.lines[0].amount == 200_000
    assert any("land or buildings" in f for f in r.findings)


def test_losses_go_where_they_save_most_ltcl_only_against_ltcg():
    r = run(itr(capital_gains=[
        cg("debt_mf", "2024-01-01", "2025-06-01", 200_000, 100_000, stt_paid=False),
        cg("listed_equity", "2025-01-01", "2025-06-01", 100_000, 250_000),   # STCL 150k
        cg("listed_equity", "2020-01-01", "2025-06-01", 400_000, 100_000),   # LTCG 300k
        cg("gold", "2020-01-01", "2025-06-01", 100_000, 180_000, stt_paid=False)]))  # LTCL 80k
    n = r.regimes["new"]
    # LTCL 80k -> s.112A (300k -> 220k). STCL: the slab gain is inside the ₹4
    # lakh exemption (0%), so 95k brings s.112A down to its ₹1.25 lakh
    # exemption first; the last 55k saves nothing anywhere and goes to the
    # slab gain by default order.
    assert n.pools["ltcg_112a"] == pytest.approx(125_000)
    assert n.pools["stcg_slab"] == pytest.approx(45_000)
    assert n.tax == 0
    assert n.carry_forward["short_term_capital_loss"] == 0
    assert n.carry_forward["long_term_capital_loss"] == 0
    assert any("tribunal" in f for f in r.findings)


def test_stcl_prefers_111a_over_exempt_slab_income():
    r = run(itr(capital_gains=[
        cg("debt_mf", "2024-01-01", "2025-06-01", 200_000, 100_000, stt_paid=False),
        cg("listed_equity", "2025-01-01", "2025-06-01", 200_000, 100_000),
        cg("listed_equity", "2025-02-01", "2025-07-01", 100_000, 200_000)]))
    assert r.regimes["new"].tax == 0


def test_hp_loss_goes_to_the_12_5_percent_gain_not_exempt_interest():
    r = run(itr(regime="old", interest=[nro(200_000)],
                house_property=[lo(0, 0, 200_000)],
                capital_gains=[cg("property", "2015-01-01", "2025-06-01",
                                  2_000_000, 1_000_000, stt_paid=False)]))
    old = r.regimes["old"]
    assert old.pools["ltcg_112"] == pytest.approx(800_000)
    assert old.tax == I.round10(100_000 * 1.04)


def test_ltcl_cannot_touch_short_term_gain_and_carries():
    r = run(itr(capital_gains=[
        cg("debt_mf", "2024-01-01", "2025-06-01", 200_000, 100_000, stt_paid=False),
        cg("gold", "2020-01-01", "2025-06-01", 100_000, 180_000, stt_paid=False)]))
    n = r.regimes["new"]
    assert n.pools["stcg_slab"] == 100_000
    assert n.carry_forward["long_term_capital_loss"] == 80_000


def test_brought_forward_capital_losses():
    r = run(itr(capital_gains=[cg("listed_equity", "2020-01-01", "2025-06-01",
                                  400_000, 100_000)],
                brought_forward_losses={"stcl_inr": 50_000, "ltcl_inr": 400_000}))
    n = r.regimes["new"]
    # Long-term loss (fewer places to go) first: it absorbs the whole gain.
    assert n.pools["ltcg_112a"] == 0
    assert n.carry_forward["long_term_capital_loss"] == 100_000
    assert n.carry_forward["short_term_capital_loss"] == 50_000


def test_54f_refused():
    with pytest.raises(I.IndiaReturnError, match="54F"):
        run(itr(capital_gains=[cg("unlisted", "2020-01-01", "2025-06-01", 2, 1,
                                  exemption_54f_inr=1)]))


# ── insurance ──────────────────────────────────────────────────────────────

def pol(kind, issued, annual, sa, maturity, premiums, **kw):
    return {"policy": kw.pop("policy", f"{kind}-{issued}"), "kind": kind,
            "issued": issued, "annual_premium_inr": annual, "sum_assured_inr": sa,
            "maturity_inr": maturity, "total_premiums_inr": premiums, "tds_inr": 0, **kw}


def test_ulip_after_feb_2021_above_2_5_lakh_is_capital_gain():
    p = pol("ulip", "2021-03-01", 300_000, 3_000_000, 1_750_000, 1_500_000,
            matured="2026-03-01", equity_oriented=True)
    r = run(itr(insurance_maturities=[p]))
    assert r.lines[0].pool == "ltcg_112a" and r.lines[0].amount == 250_000


def test_ulip_at_or_below_limit_or_before_cutoff_exempt():
    at = pol("ulip", "2021-03-01", 250_000, 3_000_000, 1_500_000, 1_250_000,
             matured="2026-03-01", equity_oriented=True)
    assert run(itr(insurance_maturities=[at])).lines[0].pool == "exempt"
    early = pol("ulip", "2021-01-31", 300_000, 3_000_000, 1_750_000, 1_500_000)
    assert run(itr(insurance_maturities=[early])).lines[0].pool == "exempt"


def test_ulip_needs_maturity_date_and_orientation():
    p = pol("ulip", "2021-03-01", 300_000, 3_000_000, 1_750_000, 1_500_000)
    with pytest.raises(I.IndiaReturnError, match="matured"):
        run(itr(insurance_maturities=[p]))


def test_non_ulip_after_april_2023_above_5_lakh_is_other_income():
    p = pol("endowment", "2023-04-01", 600_000, 10_000_000, 4_000_000, 3_000_000)
    r = run(itr(insurance_maturities=[p]))
    assert r.lines[0].pool == "slab" and r.lines[0].amount == 1_000_000
    small = pol("endowment", "2023-04-01", 500_000, 10_000_000, 4_000_000, 3_000_000)
    assert run(itr(insurance_maturities=[small])).lines[0].pool == "exempt"


def test_premium_ratio_tests():
    post = pol("money_back", "2013-01-01", 110_000, 1_000_000, 1_500_000, 1_000_000)
    assert run(itr(insurance_maturities=[post])).lines[0].pool == "slab"
    pre = pol("endowment", "2005-01-01", 190_000, 1_000_000, 1_500_000, 1_000_000)
    assert run(itr(insurance_maturities=[pre])).lines[0].pool == "exempt"
    pre_bad = pol("endowment", "2005-01-01", 210_000, 1_000_000, 1_500_000, 1_000_000)
    assert run(itr(insurance_maturities=[pre_bad])).lines[0].pool == "slab"
    old = pol("endowment", "2002-01-01", 900_000, 1_000_000, 1_500_000, 1_000_000)
    assert run(itr(insurance_maturities=[old])).lines[0].pool == "exempt"


def test_death_benefit_always_exempt():
    p = pol("ulip", "2022-01-01", 900_000, 1_000_000, 5_000_000, 900_000, on_death=True)
    assert run(itr(insurance_maturities=[p])).lines[0].pool == "exempt"


# ── regimes, rebate, surcharge ─────────────────────────────────────────────

def test_nr_gets_no_87a_rebate():
    r = run(itr(interest=[nro(1_000_000)]))
    assert r.regimes["new"].rebate == 0
    assert r.regimes["new"].tax == I.round10(40_000 * 1.04)


def test_resident_rebate_new_regime_and_marginal_relief():
    tp = {"days_in_india_this_fy": 200, "nri_years_in_prior_10": 9}
    r = run(itr(interest=[nro(1_200_000)], taxpayer=tp))
    assert r.regimes["new"].tax == 0
    r = run(itr(interest=[nro(1_210_000)], taxpayer=tp))
    # Tax 61,500 limited to the ₹10,000 above ₹12 lakh, plus cess.
    assert r.regimes["new"].tax == I.round10(10_000 * 1.04)


def test_resident_rebate_old_regime_up_to_5_lakh():
    tp = {"days_in_india_this_fy": 200, "nri_years_in_prior_10": 9}
    r = run(itr(interest=[nro(500_000)], taxpayer=tp))
    assert r.regimes["old"].tax == 0
    assert run(itr(interest=[nro(500_000)])).regimes["old"].tax == I.round10(12_500 * 1.04)


def test_senior_old_slabs_for_residents_only():
    tp = {"birth_date": "1960-01-01"}
    nr = run(itr(interest=[nro(600_000)], taxpayer=tp))
    assert nr.regimes["old"].slab_tax == pytest.approx(12_500 + 20_000)
    r = run(itr(interest=[nro(600_000)],
                taxpayer={**tp, "days_in_india_this_fy": 200, "nri_years_in_prior_10": 9}))
    # Resident senior: ₹50,000 s.80TTB on deposit interest too.
    assert r.regimes["old"].deductions["80TTB"] == 50_000
    assert r.regimes["old"].slab_tax == pytest.approx(10_000 + 10_000)


def test_recommends_lower_regime_and_flags_forced_choice():
    x = itr(interest=[nro(1_500_000)],
            deductions_old_regime={"80c_inr": 200_000, "80d_inr": 50_000})
    r = run(x)
    assert r.recommended == "new"
    assert r.regimes["old"].deductions["80C"] == 150_000
    forced = run({**x, "regime": "old"})
    assert forced.chosen == "old"
    assert any("forced" in f for f in forced.findings)


def test_surcharge_10_percent_and_marginal_relief_at_50_lakh():
    r = run(itr(interest=[nro(6_000_000)]))
    n = r.regimes["new"]
    assert n.surcharge == pytest.approx(0.10 * (300_000 + 0.30 * 3_600_000))
    assert n.marginal_relief == 0
    r = run(itr(interest=[nro(5_100_000)]))
    n = r.regimes["new"]
    tax = 300_000 + 0.30 * 2_700_000
    at_50 = 300_000 + 0.30 * 2_600_000
    assert n.marginal_relief == pytest.approx(tax * 1.10 - at_50 - 100_000)


def test_special_gains_surcharge_capped_at_15_percent():
    r = run(itr(capital_gains=[cg("listed_equity", "2020-01-01", "2025-06-01",
                                  40_000_000, 10_000_000)]))
    n = r.regimes["new"]
    special = (30_000_000 - 125_000) * 0.125
    assert n.surcharge == pytest.approx(special * 0.15)


def test_new_regime_surcharge_max_25_old_37():
    r = run(itr(interest=[nro(60_000_000)]))
    new, old = r.regimes["new"], r.regimes["old"]
    assert new.surcharge == pytest.approx(new.slab_tax * 0.25)
    assert old.surcharge == pytest.approx(old.slab_tax * 0.37)


# ── credits, interest, filing ──────────────────────────────────────────────

def test_refund_when_tds_exceeds_tax():
    r = run(itr(interest=[nro(1_000_000, tds=312_000)]))
    assert r.credits.balance == I.round10(41_600 - 312_000)
    assert r.filing.mandatory
    assert not any("refund" in x for x in r.filing.reasons)
    assert any("refund" in x for x in r.filing.notes)


def test_unknown_tds_leaves_balance_undetermined():
    r = run(itr(interest=[nro(1_000_000, tds=None)]))
    assert r.credits.balance is None
    assert any("cannot be determined" in f for f in r.findings)


def test_234b_and_234c_without_advance_tax():
    r = run(itr(interest=[nro(1_000_000)], expected_filing_date="2026-07-15"))
    assessed = I.round10(41_600)
    assert r.credits.interest_234b == round(assessed * 0.01 * 4)
    assert r.credits.interest_234c == round(assessed * (0.15 * 3 + 0.45 * 3
                                                        + 0.75 * 3 + 1.0) * 0.01)


def test_no_advance_tax_interest_below_10000():
    r = run(itr(interest=[nro(500_000)]))
    assert r.credits.interest_234b == 0 and r.credits.interest_234c == 0


def test_234c_needs_instalments_when_advance_tax_paid():
    r = run(itr(interest=[nro(1_000_000)], advance_tax_paid_inr=20_000))
    assert r.credits.interest_234c is None


def test_late_filing_234a_and_fee():
    r = run(itr(interest=[nro(1_000_000)], expected_filing_date="2026-09-10"))
    assert r.credits.interest_234a == round(I.round10(41_600) * 0.01 * 2)
    assert r.credits.late_fee == 5_000
    r = run(itr(interest=[nro(450_000)], expected_filing_date="2026-09-10"))
    assert r.credits.late_fee == 1_000


def test_filing_not_mandatory_below_exemption():
    r = run(itr(interest=[nro(200_000, tds=0)]))
    assert not r.filing.mandatory


def test_filing_threshold_ignores_54ec_exemption():
    r = run(itr(regime="new", capital_gains=[
        cg("property", "2015-01-01", "2025-06-01", 1_500_000, 1_000_000,
           stt_paid=False, exemption_54ec_inr=500_000)]))
    assert r.regimes["new"].gross_total_income == 0
    assert r.filing.mandatory


# ── U.S. hand-off ──────────────────────────────────────────────────────────

def test_us_handoff_converts_at_supplied_rate():
    r = run(itr(interest=[nro(800_000, tds=100_000), nro(80_000, kind="nre_fd")]))
    assert r.us.income_usd["passive"] == pytest.approx(800_000 / 80)
    assert r.us.tax_usd == pytest.approx(r.regimes[r.chosen].tax / 80)
    assert r.us.india_exempt_usd == pytest.approx(1_000)
    assert any("pfic-divest-or-comply" in n for n in r.us.notes)
    assert any("foreign-reporting-audit" in n for n in r.us.notes)


def test_bad_rate_stops():
    with pytest.raises(I.IndiaReturnError, match="usd_inr_rate"):
        run(itr(usd_inr_rate=0))


# ── refusals, missing data, tables ─────────────────────────────────────────

@pytest.mark.parametrize("key", ["business_income", "vda", "crypto", "clubbing",
                                 "foreign_income", "salary"])
def test_out_of_scope_refused(key):
    with pytest.raises(I.IndiaReturnError, match=key):
        run(itr(**{key: 1}))


def test_missing_amount_is_not_zero():
    with pytest.raises(I.IndiaReturnError, match="amount_inr"):
        run(itr(interest=[nro(None)]))
    with pytest.raises(I.IndiaReturnError, match="cost_inr"):
        run(itr(capital_gains=[cg("gold", "2020-01-01", "2025-06-01", 1, None)]))


def test_bad_regime_and_kind_stop():
    with pytest.raises(I.IndiaReturnError, match="regime"):
        run(itr(regime="flat"))
    with pytest.raises(I.IndiaReturnError, match="kind"):
        run(itr(interest=[nro(1, kind="ppf")]))


def test_unpublished_year_is_a_projection():
    r = run(itr(financial_year="2028-29", interest=[nro(100_000)]))
    assert r.projected_table and r.table.financial_year == "2026-27"
    assert any("projection" in f for f in r.findings)


def test_2026_27_cites_the_new_act():
    r = run(itr(financial_year="2026-27", interest=[nro(100_000)]))
    assert "2025" in r.table.act
    assert r.table.sections["new_regime"] == "s.202"
    assert r.table.sections["nre_interest"].endswith("(1961 numbering)")
    assert any("Income-tax Act, 2025" in f for f in r.findings)


def test_every_table_is_cited_and_marked_unverified():
    for t in I.INDIA_TABLES.values():
        assert t.source and t.verified_on == "unverified"


def test_example_snippet_runs():
    from pathlib import Path
    yaml = pytest.importorskip("yaml")
    root = Path(__file__).resolve().parents[1]
    facts = yaml.safe_load((root / "inputs/facts.example.yml")
                           .read_text(encoding="utf-8"))
    snip = facts["india_tax_return"]
    members = facts["household"]["members"]
    r = I.compute(copy.deepcopy(snip), members=members)
    assert r.residence.status == I.NR
    # STCL ₹60k goes against the 12.5% plot gain, not the 0-5% debt-fund
    # gain. New: slab ₹4,91,600 -> ₹4,580; special ₹18,40,000 x 12.5% +
    # ₹5,25,000 x 12.5% = ₹2,95,625; x1.04 = ₹3,12,213 -> ₹3,12,210.
    # Old: slab ₹2,91,600 - ₹1,85,000 VI-A -> ₹1,06,600, nil; ₹2,95,625 x1.04.
    assert r.regimes["new"].tax == 312_210 and r.regimes["old"].tax == 307_450
    assert r.recommended == "old"
    assert r.credits.balance == -291_800


# ── adversarial-review regressions ─────────────────────────────────────────

RES = {"days_in_india_this_fy": 200, "nri_years_in_prior_10": 9}


def test_h1_87a_marginal_relief_runs_to_about_12_70_588():
    assert run(itr(interest=[nro(1_260_000)], taxpayer=RES)).regimes["new"].tax == 62_400
    assert run(itr(interest=[nro(1_265_000)], taxpayer=RES)).regimes["new"].tax == 67_600
    # Above the break-even the full tax applies: 60,000 + 15% x 80,000.
    assert run(itr(interest=[nro(1_280_000)], taxpayer=RES)).regimes["new"].tax == \
        I.round10(72_000 * 1.04)


def test_h2_no_old_regime_after_the_due_date():
    # Old: 10L - 2L self-occupied interest - 1.75L VI-A = 6.25L -> 37,500;
    # new: 10L -> 40,000. On time the old regime wins; late it is barred.
    x = itr(interest=[nro(1_000_000)], house_property=[so(200_000)],
            expected_filing_date="2026-09-10",
            deductions_old_regime={"80c_inr": 150_000, "80d_inr": 25_000})
    assert run({**x, "expected_filing_date": "2026-07-01"}).chosen == "old"
    r = run(x)
    assert r.regimes["old"].tax < r.regimes["new"].tax
    assert r.recommended == "new" and r.chosen == "new"
    assert any("only the new regime" in f for f in r.findings)
    forced = run({**x, "regime": "old"})
    assert forced.chosen == "new"
    assert any("requested and is not applied" in f for f in forced.findings)


def test_h4_dividend_surcharge_capped_at_15_percent():
    r = run(itr(dividends=[{"payer": "co", "amount_inr": 60_000_000, "tds_inr": 0}]))
    assert r.regimes["old"].surcharge == pytest.approx(0.15 * 0.20 * 60_000_000)
    res = run(itr(dividends=[{"payer": "co", "amount_inr": 60_000_000, "tds_inr": 0}],
                  taxpayer=RES))
    old = res.regimes["old"]
    assert old.surcharge == pytest.approx(0.15 * old.slab_tax)


def test_m1_ulip_failing_ratio_test_is_other_income():
    p = pol("ulip", "2015-01-01", 200_000, 1_000_000, 1_500_000, 1_000_000)
    ln = run(itr(insurance_maturities=[p])).lines[0]
    assert ln.pool == "slab" and ln.amount == 500_000


def test_m2_54ec_limit_is_per_year_across_sales():
    sales = [cg("property", "2015-01-01", "2025-06-01", 20_000_000, 10_000_000,
                stt_paid=False, exemption_54ec_inr=5_000_000, name=n) for n in "ab"]
    r = run(itr(capital_gains=sales))
    assert sum(ln.exempt_54 for ln in r.lines) == 5_000_000


def test_m3_negative_other_income_is_nil_not_a_capital_loss():
    p = pol("endowment", "2013-01-01", 200_000, 1_000_000, 800_000, 1_000_000)
    r = run(itr(insurance_maturities=[p], capital_gains=[
        cg("gold", "2020-01-01", "2025-06-01", 400_000, 100_000, stt_paid=False)]))
    assert r.lines[1].amount == 0
    assert r.regimes["new"].pools["ltcg_112"] == 300_000


def test_m4_unknown_citizenship_stops_when_it_decides():
    no_cit = [{"id": "p1", "role": "primary"}]
    with pytest.raises(I.IndiaReturnError, match="citizenship"):
        run(itr(interest=[nro(2_000_000)], taxpayer={"days_in_india_this_fy": 10}),
            members=no_cit)
    with pytest.raises(I.IndiaReturnError, match="citizenship"):
        res({"days_in_india_this_fy": 150, "days_in_india_prior_4_fy": 800,
             "left_india_for_employment_this_fy": True,
             "person_of_indian_origin": True}, citizen=None)
    # Below ₹15 lakh, citizenship decides nothing: no stop.
    assert run(itr(interest=[nro(100_000)]), members=no_cit).residence.status == I.NR


def test_m5_unknown_payments_and_stt_are_not_zero_or_favourable():
    x = itr(interest=[nro(1_000_000, tds=0)])
    del x["advance_tax_paid_inr"]
    r = run(x)
    assert r.credits.balance is None and r.credits.interest_234b is None
    assert any("advance_tax_paid_inr" in f for f in r.findings)
    y = itr(interest=[nro(1_000_000, tds=0)], self_assessment_tax_paid_inr=None)
    assert run(y).credits.balance is None
    row = cg("listed_equity", "2020-01-01", "2025-06-01", 300_000, 100_000)
    del row["stt_paid"]
    with pytest.raises(I.IndiaReturnError, match="stt_paid"):
        run(itr(capital_gains=[row]))


def test_m5_unrecorded_brought_forward_losses_bound_the_result():
    r = run(itr(interest=[nro(100_000)]))
    assert any("upper bound" in f for f in r.findings)
    r = run(itr(interest=[nro(100_000)], brought_forward_losses={
        "house_property_inr": 0, "stcl_inr": 0, "ltcl_inr": 0}))
    assert not any("upper bound" in f for f in r.findings)


def test_m6_dates_outside_the_year_stop():
    with pytest.raises(I.IndiaReturnError, match="outside the financial year"):
        run(itr(capital_gains=[cg("listed_equity", "2020-01-01", "2024-06-01",
                                  300_000, 100_000)]))
    p = pol("ulip", "2021-03-01", 300_000, 3_000_000, 1_750_000, 1_500_000,
            matured="2026-04-01", equity_oriented=True)
    with pytest.raises(I.IndiaReturnError, match="outside the financial year"):
        run(itr(insurance_maturities=[p]))


def test_m7_80ttb_without_savings_interest():
    r = run(itr(interest=[nro(200_000)],
                taxpayer={**RES, "birth_date": "1960-01-01"}))
    assert r.regimes["old"].deductions["80TTB"] == 50_000


@pytest.mark.parametrize("bad", [[{"number": "first", "amount_inr": 1}],
                                 [{"number": 5, "amount_inr": 1}],
                                 [{"number": 1}], "x"])
def test_m10_bad_instalments_raise_the_module_error(bad):
    with pytest.raises(I.IndiaReturnError, match="instalment"):
        run(itr(interest=[nro(1_000_000)], advance_tax_paid_inr=10_000,
                advance_tax_instalments=bad))


def test_instalments_reduce_234c():
    none = run(itr(interest=[nro(1_000_000)]))
    paid = run(itr(interest=[nro(1_000_000)], advance_tax_paid_inr=41_600,
                   advance_tax_instalments=[{"number": n, "amount_inr": a} for n, a in
                                            ((1, 6_240), (2, 12_480), (3, 12_480),
                                             (4, 10_400))]))
    assert paid.credits.interest_234c == 0 < none.credits.interest_234c
    assert paid.credits.interest_234b == 0


def test_l1_80d_capped_and_flagged():
    r = run(itr(interest=[nro(2_000_000)], deductions_old_regime={"80d_inr": 900_000}))
    old = r.regimes["old"]
    assert old.deductions["80D"] == 100_000
    assert any("80D" in n for n in old.notes)


def test_l2_tds_trigger_and_refund_is_not_a_mandate():
    big = run(itr(interest=[nro(100_000, tds=40_000)]))
    assert big.filing.mandatory and any("Rule 12AB" in x for x in big.filing.reasons)
    small = run(itr(interest=[nro(100_000, tds=20_000)]))
    assert not small.filing.mandatory
    assert any("refund" in x for x in small.filing.notes)


def test_l3_s195_rent_finding_only_for_non_residents():
    ror = {"days_in_india_this_fy": 200, "nri_years_in_prior_10": 0,
           "days_in_india_prior_7_fy": 2000}
    r = run(itr(house_property=[lo(300_000)], taxpayer=ror))
    assert not any("s.195" in f for f in r.findings)
    assert any("s.195" in f for f in run(itr(house_property=[lo(300_000)])).findings)


def test_l4_no_30_percent_deduction_on_negative_nav():
    r = run(itr(house_property=[lo(100_000, 200_000)]))
    assert r.regimes["new"].hp_income == -100_000


def test_l5_late_return_loses_this_years_capital_loss_carry_forward():
    x = itr(capital_gains=[cg("gold", "2020-01-01", "2025-06-01", 100, 50_000,
                              stt_paid=False)])
    assert run(x).regimes["new"].carry_forward["long_term_capital_loss"] > 0
    late = run({**x, "expected_filing_date": "2026-10-01"})
    assert late.regimes["new"].carry_forward["long_term_capital_loss"] == 0


def test_l6_us_exempt_detail_includes_insurance_and_54ec():
    r = run(itr(insurance_maturities=[pol("endowment", "2010-06-01", 40_000, 500_000,
                                          900_000, 600_000)],
                capital_gains=[cg("property", "2015-01-01", "2025-06-01", 3_000_000,
                                  1_000_000, stt_paid=False,
                                  exemption_54ec_inr=1_000_000)]))
    d = r.us.india_exempt_detail
    assert d["s.10(10D) maturity gains"] == 300_000
    assert d["s.54/54EC-sheltered gains"] == 1_000_000
    assert r.us.india_exempt_inr == 1_300_000


def test_l7_earlier_year_refused():
    with pytest.raises(I.IndiaReturnError, match="predates"):
        run(itr(financial_year="2024-25"))


def test_l8_day_counts_range_checked():
    with pytest.raises(I.IndiaReturnError, match="outside"):
        run(itr(taxpayer={"days_in_india_this_fy": 400}))
    with pytest.raises(I.IndiaReturnError, match="outside"):
        run(itr(taxpayer={"days_in_india_this_fy": -1}))


def test_us_by_type_reconciles_to_passive_total():
    r = run(itr(interest=[nro(300_000)], house_property=[lo(200_000)],
                dividends=[{"payer": "co", "amount_inr": 50_000, "tds_inr": 0}],
                capital_gains=[cg("gold", "2020-01-01", "2025-06-01", 400_000, 100_000,
                                  stt_paid=False)]))
    t = r.us.by_type_inr
    assert t["interest"] == 300_000 and t["dividends"] == 50_000
    assert t["capital_transactions"] == 300_000 and t["rent"] == pytest.approx(140_000)
    assert sum(t.values()) == pytest.approx(r.us.income_inr["passive"])
    assert r.us.by_type_usd["interest"] == pytest.approx(300_000 / 80)


def test_federal_foreign_block_matches_the_federal_contract():
    r = run(itr(interest=[nro(800_000, tds=100_000), nro(80_000, kind="nre_fd")],
                dividends=[{"payer": "co", "amount_inr": 40_000, "tds_inr": 0}],
                house_property=[lo(160_000)],
                capital_gains=[
                    cg("listed_equity", "2024-05-01", "2025-06-01", 400_000, 100_000,
                       us_basis_usd=1_300),
                    cg("gold", "2025-01-01", "2025-06-01", 160_000, 100_000,
                       stt_paid=False, transfer_expenses_inr=8_000),
                    cg("equity_mf", "2020-01-01", "2025-06-01", 200_000, 100_000)]))
    f = r.us.federal_foreign
    assert set(f) == {"country", "accounts", "interest", "dividends",
                      "qualified_dividends", "capital_transactions", "rent",
                      "foreign_tax_paid", "reported_on_1099", "category"}
    assert f["country"] == "IN" and f["accounts"] is True
    assert f["interest"] == round(880_000 / 80)          # NRE included
    assert f["dividends"] == 500 and f["qualified_dividends"] is None
    assert f["rent"] == 0
    assert any("₹160,000 gross" in x for x in r.us.federal_excluded)
    assert f["foreign_tax_paid"] == {"passive": round(r.regimes[r.chosen].tax / 80),
                                     "general": 0}
    shares, gold = f["capital_transactions"]               # fund is a PFIC: left out
    assert shares == {"description": shares["description"], "proceeds": 5_000,
                      "basis": 1_300, "term": "long", "wash_sale_disallowed": 0,
                      "basis_reported": False}
    assert gold["basis"] is None and gold["term"] == "short"
    assert gold["proceeds"] == round(160_000 / 80) and "collectible" in gold["description"]
    assert "₹8,000 transfer expenses" in gold["description"]
    assert any("PFIC" in x for x in r.us.federal_excluded)
    assert any("passive-loss-eligibility" in x for x in r.us.federal_excluded)


def test_federal_block_has_no_unknown_zeroes_without_dividends():
    f = run(itr(interest=[nro(100_000)])).us.federal_foreign
    assert f["qualified_dividends"] == 0 and f["capital_transactions"] == []
    assert f["rent"] == 0
