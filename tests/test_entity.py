"""Cluster 13 — entity choice, the salary optimum, owner-only plans. Synthetic only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import entity as E, limits as L  # noqa: E402

# Invented figures. They are shaped like the real ones so the regimes behave,
# but nothing here is a statutory assertion — the module reads those from the
# facts file, which is the point.
P = E.TaxParams(
    marginal_rate=0.24, state_rate=0.0, ss_wage_base=180_000,
    qbi_threshold=390_000, qbi_phase_in=100_000,
    qualified_dividend_rate=0.15, filing_status="married_joint",
)
HIGH = E.TaxParams(
    marginal_rate=0.35, state_rate=0.0, ss_wage_base=180_000,
    qbi_threshold=390_000, qbi_phase_in=100_000,
    qualified_dividend_rate=0.15, filing_status="married_joint",
)


def biz(revenue=250_000, expenses=50_000, **kw):
    return E.Business(gross_revenue=revenue, expenses=expenses, **kw)


# ── refusal paths ───────────────────────────────────────────────────────────


def test_missing_indexed_figures_refuses_to_compare():
    c = E.compare(biz(), E.TaxParams(marginal_rate=0.24))
    assert not c.params_known
    assert c.outcomes == []
    assert "assumptions.ss_wage_base" in c.missing
    assert "assumptions.qbi_threshold" in c.missing


def test_marginal_rate_alone_is_not_enough():
    p = E.TaxParams(ss_wage_base=180_000, qbi_threshold=1, qbi_phase_in=1)
    assert not p.known
    assert "assumptions.marginal_tax_rate" in p.missing


def test_c_corp_refuses_without_a_dividend_rate():
    p = E.TaxParams(marginal_rate=0.24, ss_wage_base=180_000,
                    qbi_threshold=390_000, qbi_phase_in=100_000)
    o = E.c_corp(biz(), p, 80_000)
    assert o.unavailable is not None
    assert "qualified_dividend_rate" in o.unavailable


def test_no_reasonable_salary_floor_is_reported_not_invented():
    c = E.compare(biz(), P)
    joined = " ".join(c.curve.findings)
    assert "reasonable_salary_floor" in joined
    assert "will not invent" in joined


def test_missing_s_corp_cost_downgrades_verdict_to_a_number():
    c = E.compare(biz(reasonable_salary_floor=70_000), P)
    assert any("s_corp_annual_cost" in f for f in c.findings)


# ── self-employment and FICA ────────────────────────────────────────────────


def test_se_tax_uses_the_9235_base():
    pt = E.se_tax(100_000, P)
    base = 100_000 * E.SE_BASE_FACTOR
    assert pt.social_security == base * E.SS_RATE
    assert pt.medicare == base * E.MEDICARE_RATE


def test_se_tax_caps_social_security_at_the_wage_base():
    pt = E.se_tax(400_000, P)
    assert pt.social_security == 180_000 * E.SS_RATE
    # Medicare is uncapped.
    assert pt.medicare == 400_000 * E.SE_BASE_FACTOR * E.MEDICARE_RATE


def test_outside_wages_consume_the_wage_base_first():
    p = E.TaxParams(marginal_rate=0.24, ss_wage_base=180_000,
                    qbi_threshold=390_000, qbi_phase_in=100_000,
                    other_wages=180_000)
    pt = E.se_tax(100_000, p)
    assert pt.social_security == 0.0
    assert pt.medicare > 0


def test_additional_medicare_starts_at_the_filing_status_threshold():
    p = E.TaxParams(marginal_rate=0.35, ss_wage_base=180_000,
                    qbi_threshold=390_000, qbi_phase_in=100_000,
                    filing_status="single")
    assert E.se_tax(150_000, p).additional_medicare == 0.0
    assert E.se_tax(400_000, p).additional_medicare > 0.0


def test_employer_share_is_half_of_ss_plus_medicare_not_of_the_surtax():
    f = E.fica_on_wages(120_000, P)
    assert f.employer_share == (f.social_security + f.medicare) / 2


# ── §199A ───────────────────────────────────────────────────────────────────


def test_below_threshold_there_is_no_wage_limit():
    q = E.qbi_deduction(qbi=100_000, w2_wages=0, ubia=0,
                        taxable_income_before_qbi=200_000, sstb=False, p=P)
    assert q.regime == "below_threshold"
    assert q.deduction == 20_000


def test_above_threshold_a_schedule_c_with_no_wages_gets_nothing():
    """The finding most comparisons miss entirely."""
    q = E.qbi_deduction(qbi=500_000, w2_wages=0, ubia=0,
                        taxable_income_before_qbi=600_000, sstb=False, p=P)
    assert q.deduction == 0.0
    assert q.regime == "wage_limited"


def test_wage_limit_is_fifty_percent_of_wages():
    q = E.qbi_deduction(qbi=400_000, w2_wages=100_000, ubia=0,
                        taxable_income_before_qbi=600_000, sstb=False, p=P)
    assert q.tentative == 80_000
    assert q.deduction == 50_000
    assert q.limited


def test_ubia_alternative_can_beat_the_wage_only_limit():
    q = E.qbi_deduction(qbi=400_000, w2_wages=100_000, ubia=2_000_000,
                        taxable_income_before_qbi=600_000, sstb=False, p=P)
    # 25% of wages + 2.5% of UBIA = 75,000 > 50% of wages.
    assert q.wage_limit == 75_000
    assert q.deduction == 75_000


def test_missing_ubia_is_flagged_only_when_the_limit_is_in_play():
    over = E.qbi_deduction(qbi=400_000, w2_wages=100_000, ubia=None,
                           taxable_income_before_qbi=600_000, sstb=False, p=P)
    under = E.qbi_deduction(qbi=100_000, w2_wages=0, ubia=None,
                            taxable_income_before_qbi=200_000, sstb=False, p=P)
    assert any("ubia" in f for f in over.findings)
    assert not any("ubia" in f for f in under.findings)


def test_sstb_phases_out_linearly_and_reaches_zero():
    mid = E.qbi_deduction(qbi=200_000, w2_wages=100_000, ubia=0,
                          taxable_income_before_qbi=440_000, sstb=True, p=P)
    assert 0 < mid.applicable_pct < 1
    top = E.qbi_deduction(qbi=200_000, w2_wages=100_000, ubia=0,
                          taxable_income_before_qbi=500_000, sstb=True, p=P)
    assert top.deduction == 0.0
    assert top.regime == "sstb_phased_out"


def test_sstb_below_the_threshold_is_unaffected():
    q = E.qbi_deduction(qbi=100_000, w2_wages=0, ubia=0,
                        taxable_income_before_qbi=200_000, sstb=True, p=P)
    assert q.deduction == 20_000


def test_qbi_is_zero_when_there_is_no_business_income():
    q = E.qbi_deduction(qbi=-5_000, w2_wages=0, ubia=0,
                        taxable_income_before_qbi=50_000, sstb=False, p=P)
    assert q.deduction == 0.0


# ── the structures ──────────────────────────────────────────────────────────


def test_s_corp_distribution_is_net_of_employer_fica():
    o = E.s_corp(biz(), P, 80_000)
    f = E.fica_on_wages(80_000, P)
    assert o.lines[3] == ("Distribution", 200_000 - 80_000 - f.employer_share)


def test_s_corp_take_home_does_not_double_count_the_employer_half():
    o = E.s_corp(biz(), P, 80_000)
    f = E.fica_on_wages(80_000, P)
    distribution = 200_000 - 80_000 - f.employer_share
    employee = f.total - f.employer_share
    expected = (80_000 + distribution - employee
                - o.federal_income_tax - o.state_tax)
    assert abs(o.take_home - expected) < 0.01


def test_salary_above_profit_is_trimmed_rather_than_going_negative():
    o = E.s_corp(biz(revenue=100_000, expenses=90_000), P, 500_000)
    assert o.salary <= 10_000
    assert o.take_home > 0


def test_c_corp_is_taxed_twice():
    o = E.c_corp(biz(), P, 80_000)
    assert o.entity_tax > 0
    assert o.qbi.deduction == 0.0
    assert o.take_home < E.s_corp(biz(), P, 80_000).take_home


def test_c_corp_figure_is_declared_optimistic():
    o = E.c_corp(biz(), P, 80_000)
    assert any("optimistic" in f for f in o.findings)


# ── the salary optimum: the reason this skill exists ────────────────────────


def test_below_the_threshold_salary_should_be_minimised():
    c = E.compare(biz(reasonable_salary_floor=70_000, s_corp_annual_cost=2_400), P)
    assert c.curve.shape == "minimise"
    assert c.curve.at_floor


def test_above_the_threshold_there_is_a_genuine_interior_optimum():
    """0.5W = 0.2(P - W - employer FICA) puts the optimum near 28% of profit."""
    b = biz(revenue=900_000, expenses=200_000,
            reasonable_salary_floor=120_000, s_corp_annual_cost=3_000)
    c = E.compare(b, HIGH)
    assert c.curve.shape == "interior"
    ratio = c.curve.best.salary / b.net_profit
    assert 0.25 < ratio < 0.31
    assert not c.curve.at_floor


def test_the_optimum_beats_the_floor_by_a_reported_amount():
    b = biz(revenue=900_000, expenses=200_000,
            reasonable_salary_floor=120_000, s_corp_annual_cost=3_000)
    c = E.compare(b, HIGH)
    at_floor = E.s_corp(b, HIGH, 120_000)
    assert c.curve.best.take_home > at_floor.take_home


def test_an_sstb_above_the_phase_out_reverses_to_minimise():
    """QBI is gone, so salary stops buying anything and is a cost again."""
    b = biz(revenue=800_000, expenses=150_000, sstb=True,
            reasonable_salary_floor=150_000, s_corp_annual_cost=3_000)
    c = E.compare(b, HIGH)
    assert c.curve.shape == "minimise"
    assert c.by_structure(E.S_CORP).qbi.regime == "sstb_phased_out"


def test_raising_salary_below_the_threshold_costs_qbi_and_fica_both():
    low = E.s_corp(biz(reasonable_salary_floor=60_000), P, 60_000)
    high = E.s_corp(biz(reasonable_salary_floor=60_000), P, 140_000)
    assert high.qbi.deduction < low.qbi.deduction
    assert high.payroll_tax > low.payroll_tax
    assert high.take_home < low.take_home


def test_schedule_c_over_the_threshold_is_told_why_it_loses_qbi():
    b = biz(revenue=900_000, expenses=200_000)
    o = E.schedule_c(b, HIGH)
    assert o.qbi.deduction == 0.0
    assert any("no W-2 wages" in f for f in o.findings)


# ── the ROI threshold ───────────────────────────────────────────────────────


def test_s_corp_loses_at_low_profit_once_its_cost_is_counted():
    c = E.compare(biz(revenue=75_000, expenses=15_000,
                      reasonable_salary_floor=45_000,
                      s_corp_annual_cost=2_400), P)
    assert c.by_structure(E.S_CORP).take_home < c.by_structure(E.SCHEDULE_C).take_home
    assert any("loses" in f for f in c.findings)


def test_s_corp_wins_at_higher_profit():
    c = E.compare(biz(reasonable_salary_floor=70_000, s_corp_annual_cost=2_400), P)
    assert c.by_structure(E.S_CORP).take_home > c.by_structure(E.SCHEDULE_C).take_home
    assert any("nets" in f for f in c.findings)


def test_a_marginal_saving_is_called_marginal():
    """Between break-even and 2x the running cost, the verdict is hedged."""
    b = biz(revenue=150_000, expenses=20_000, reasonable_salary_floor=70_000,
            s_corp_annual_cost=2_400)
    c = E.compare(b, P)
    gap = c.by_structure(E.S_CORP).take_home - c.by_structure(E.SCHEDULE_C).take_home
    assert 0 < gap < 2_400 * (E.ROI_MULTIPLE - 1)
    assert any("Marginal" in f for f in c.findings)


def test_a_high_salary_relative_to_profit_can_make_the_election_lose():
    """The QBI side of the interaction, isolated.

    At $100k profit with a $70k defensible salary there is little distribution
    left to shelter, and the QBI given up by moving profit into wages exceeds
    the payroll tax saved. A payroll-only model recommends electing here.
    """
    b = biz(revenue=120_000, expenses=20_000, reasonable_salary_floor=70_000,
            s_corp_annual_cost=0)
    c = E.compare(b, P)
    s, sc = c.by_structure(E.S_CORP), c.by_structure(E.SCHEDULE_C)
    assert s.payroll_tax < sc.payroll_tax          # payroll tax is saved
    assert s.qbi.deduction < sc.qbi.deduction      # QBI is given up
    assert s.take_home < sc.take_home              # and the QBI side wins


def test_outside_wages_are_reported_as_eroding_the_saving():
    p = E.TaxParams(marginal_rate=0.24, ss_wage_base=180_000,
                    qbi_threshold=390_000, qbi_phase_in=100_000,
                    other_wages=200_000, other_taxable_income=200_000,
                    qualified_dividend_rate=0.15)
    c = E.compare(biz(reasonable_salary_floor=70_000, s_corp_annual_cost=2_400), p)
    assert any("wage base" in f for f in c.findings)


def test_missing_deductions_total_warns_about_the_threshold_test():
    c = E.compare(biz(reasonable_salary_floor=70_000, s_corp_annual_cost=2_400), P)
    assert any("deductions_total" in f for f in c.findings)


# ── cross-border ────────────────────────────────────────────────────────────


def test_no_cross_border_noise_for_a_domestic_household():
    assert E.cross_border_flags(tax_home_abroad=False) == []


def test_feie_does_not_exclude_self_employment_tax():
    flags = " ".join(E.cross_border_flags(tax_home_abroad=True))
    assert "does not exclude" in flags
    assert "15.3%" in flags
    assert "totalization" in flags.lower()
    assert "feie-vs-ftc" in flags


# ── owner-only retirement plans ─────────────────────────────────────────────


L26 = L.for_year(2026)


def test_unknown_year_produces_no_contribution_figure():
    choice = E.solo_plan_options(net_profit=200_000, w2_salary=None, age=45,
                                 year=1999, p=P)
    assert not choice.limits_known
    assert choice.options == []


def test_solo_401k_beats_a_sep_by_the_elective_deferral():
    choice = E.solo_plan_options(net_profit=200_000, w2_salary=None, age=41,
                                 year=2026, p=P)
    solo = choice.options[0]
    sep = choice.options[1]
    assert solo.name.startswith("Solo")
    assert solo.total - sep.total == L26.elective_deferral


def test_catch_up_sits_outside_the_415c_ceiling():
    younger = E.solo_plan_options(net_profit=600_000, w2_salary=None, age=41,
                                  year=2026, p=P)
    older = E.solo_plan_options(net_profit=600_000, w2_salary=None, age=52,
                                year=2026, p=P)
    assert older.options[0].total - younger.options[0].total == L26.catch_up_50


def test_neither_plan_exceeds_415c_before_catch_up():
    choice = E.solo_plan_options(net_profit=2_000_000, w2_salary=None, age=41,
                                 year=2026, p=P)
    for o in choice.options[:2]:
        assert o.total <= L26.total_additions


def test_employer_base_is_w2_salary_for_an_s_corp_not_the_profit():
    base, label = E.employer_contribution_base(
        net_profit=None, w2_salary=80_000, p=P)
    assert base == 80_000 * E.EMPLOYER_RATE_W2
    assert "W-2" in label


def test_employer_base_for_a_schedule_c_is_net_of_half_the_se_tax():
    base, label = E.employer_contribution_base(
        net_profit=200_000, w2_salary=None, p=P)
    pt = E.se_tax(200_000, P)
    expected = (200_000 - (pt.social_security + pt.medicare) / 2) \
        * E.EMPLOYER_RATE_SELF_EMPLOYED
    assert abs(base - expected) < 0.01
    assert "self-employment" in label


def test_minimising_s_corp_salary_also_caps_the_plan():
    """The interaction the two skills must be read together for."""
    small = E.solo_plan_options(net_profit=None, w2_salary=50_000, age=41,
                                year=2026, p=P)
    large = E.solo_plan_options(net_profit=None, w2_salary=150_000, age=41,
                                year=2026, p=P)
    assert large.options[0].total > small.options[0].total
    assert any("no plan space" in f for f in large.findings)


def test_sep_carries_the_employee_warning_before_the_business_hires():
    choice = E.solo_plan_options(net_profit=200_000, w2_salary=None, age=41,
                                 year=2026, p=P)
    sep = choice.options[1]
    assert any("eligible employee" in f for f in sep.findings)


def test_defined_benefit_refuses_a_number_and_says_why():
    choice = E.solo_plan_options(net_profit=800_000, w2_salary=None, age=55,
                                 year=2026, p=P)
    db = choice.options[2]
    assert db.total is None
    assert any("actuary" in f for f in db.findings)
    assert any("funding commitment" in f for f in db.findings)


def test_plan_choice_points_at_the_existing_space_audit():
    choice = E.solo_plan_options(net_profit=200_000, w2_salary=None, age=52,
                                 year=2026, p=P)
    text = " ".join(f for o in choice.options for f in o.findings)
    assert "contribution-space-audit" in text
