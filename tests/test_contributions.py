"""Cluster 4 — statutory limits and contribution space. Synthetic only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import contributions as C, limits as L  # noqa: E402

L26 = L.for_year(2026)
MEMBERS = [{"id": "a1", "role": "primary", "age": 41},
           {"id": "a2", "role": "spouse", "age": 39}]

PCT_PLAN = {
    "compensation": 180_000, "pay_periods": 24, "deferral_rate_pct": 40,
    "employee_pre_tax": 24_500, "employer_match": 3_600, "true_up": None,
    "match_formula": {"type": C.PERCENT_OF_PAY, "rate": 0.5, "cap_pct": 0.06},
}
DFD_PLAN = {
    "compensation": 256_760, "pay_periods": 24, "deferral_rate_pct": 60,
    "employee_pre_tax": 32_500, "employer_match": 12_250, "true_up": None,
    "match_formula": {"type": C.DOLLAR_FOR_DOLLAR, "rate": 1.0,
                      "cap_annual": 12_250},
}


# ── limits table ────────────────────────────────────────────────────────────


def test_unknown_year_returns_unknown_not_last_years_numbers():
    lim = L.for_year(1999)
    assert not lim.known
    assert lim.elective_deferral is None


def test_none_year_is_unknown():
    assert not L.for_year(None).known


def test_known_years_are_fully_populated():
    """A partially filled year is worse than a missing one."""
    for y in L.years_available():
        lim = L.for_year(y)
        for f in ("elective_deferral", "catch_up_50", "total_additions",
                  "ira_contribution", "hsa_self_only", "hsa_family"):
            assert getattr(lim, f) is not None, f"{y}.{f}"
        assert lim.source


def test_every_known_year_carries_a_verification_note():
    for y in L.years_available():
        assert L.for_year(y).verified_on


def test_catch_up_is_zero_below_fifty():
    assert L.catch_up_for_age(41, L26) == 0
    assert L.catch_up_for_age(49, L26) == 0


def test_catch_up_applies_from_fifty():
    assert L.catch_up_for_age(50, L26) == L26.catch_up_50


def test_enhanced_catch_up_replaces_rather_than_stacks():
    """SECURE 2.0 ages 60-63 substitute for the age-50 amount."""
    at_55 = L.catch_up_for_age(55, L26)
    at_61 = L.catch_up_for_age(61, L26)
    assert at_61 == L26.catch_up_60_63
    assert at_61 != at_55 + L26.catch_up_50


def test_enhanced_catch_up_ends_after_63():
    assert L.catch_up_for_age(64, L26) == L26.catch_up_50


def test_catch_up_unknown_year_is_zero_not_a_guess():
    assert L.catch_up_for_age(55, L.for_year(1999)) == 0


def test_employer_plan_space_adds_catch_up_outside_415c():
    assert L.employer_plan_space(52, L26) == L26.total_additions + L26.catch_up_50
    assert L.employer_plan_space(41, L26) == L26.total_additions


def test_employer_plan_space_unknown_year_is_none():
    assert L.employer_plan_space(52, L.for_year(1999)) is None


def test_ira_space_with_and_without_catch_up():
    assert L.ira_space(41, L26) == L26.ira_contribution
    assert L.ira_space(52, L26) == L26.ira_contribution + L26.ira_catch_up


def test_hsa_space_by_coverage_and_age():
    assert L.hsa_space("self_only", 41, L26) == L26.hsa_self_only
    assert L.hsa_space("family", 41, L26) == L26.hsa_family
    assert L.hsa_space("family", 60, L26) == L26.hsa_family + L26.hsa_catch_up_55


def test_hsa_space_none_coverage_is_none():
    assert L.hsa_space(None, 41, L26) is None
    assert L.hsa_space("none", 41, L26) is None


# ── the match, and why the formula shape decides it ─────────────────────────


def test_percent_of_pay_forfeits_when_frontloaded():
    a = C.analyse_match(PCT_PLAN, age=41, lim=L26)
    assert a.at_risk
    assert a.periods_contributing == 9
    assert a.forfeited == 3_375.0


def test_dollar_for_dollar_forfeits_nothing_when_frontloaded():
    """Same front-loading, opposite answer. This is the whole module."""
    a = C.analyse_match(DFD_PLAN, age=52, lim=L26)
    assert not a.at_risk
    assert a.match_earned == 12_250
    assert any("costs nothing here" in f for f in a.findings)


def test_dollar_for_dollar_still_recommends_confirming_the_cap_basis():
    a = C.analyse_match(DFD_PLAN, age=52, lim=L26)
    assert any("really is annual" in f for f in a.findings)


def test_missing_formula_type_refuses_to_answer():
    plan = dict(PCT_PLAN, match_formula={"rate": 0.5, "cap_pct": 0.06})
    a = C.analyse_match(plan, age=41, lim=L26)
    assert a.forfeited is None
    assert any("not recorded, so this cannot be answered" in f for f in a.findings)
    assert any("ask HR" in f for f in a.findings)


def test_true_up_neutralises_the_forfeiture():
    a = C.analyse_match(dict(PCT_PLAN, true_up=True), age=41, lim=L26)
    assert not a.at_risk
    assert a.forfeited == 0
    assert any("plan trues up" in f for f in a.findings)


def test_true_up_false_is_stated_more_strongly_than_unknown():
    known_bad = C.analyse_match(dict(PCT_PLAN, true_up=False), age=41, lim=L26)
    unknown = C.analyse_match(PCT_PLAN, age=41, lim=L26)
    assert known_bad.at_risk and unknown.at_risk
    assert any("does not true up" in f for f in known_bad.findings)
    assert any("unknown" in f for f in unknown.findings)


def test_spread_deferrals_forfeit_nothing():
    a = C.analyse_match(dict(PCT_PLAN, deferral_rate_pct=10), age=41, lim=L26)
    assert not a.at_risk
    assert a.periods_contributing == a.pay_periods


def test_catch_up_extends_the_ceiling_and_the_contributing_periods():
    young = C.analyse_match(PCT_PLAN, age=41, lim=L26)
    older = C.analyse_match(PCT_PLAN, age=52, lim=L26)
    assert older.periods_contributing > young.periods_contributing
    assert older.forfeited < young.forfeited


def test_unknown_year_cannot_model_timing():
    a = C.analyse_match(PCT_PLAN, age=41, lim=L.for_year(1999))
    assert a.forfeited is None


def test_zero_deferral_rate_is_reported():
    a = C.analyse_match(dict(PCT_PLAN, deferral_rate_pct=0), age=41, lim=L26)
    assert any("no match is being earned" in f for f in a.findings)


def test_percent_formula_without_cap_pct_cannot_size_it():
    plan = dict(PCT_PLAN, match_formula={"type": C.PERCENT_OF_PAY, "rate": 0.5})
    a = C.analyse_match(plan, age=41, lim=L26)
    assert a.forfeited is None
    assert any("cap_pct" in f for f in a.findings)


# ── space audit ─────────────────────────────────────────────────────────────


def line(a, prefix):
    return next(l for l in a.lines if l.name.startswith(prefix))


def test_unknown_year_produces_no_lines_and_says_why():
    a = C.audit_space({"employer_plan": PCT_PLAN}, members=MEMBERS, year=1999)
    assert a.lines == []
    assert any("not in the table" in f for f in a.findings)


def test_known_year_always_carries_the_verify_warning():
    a = C.audit_space({"employer_plan": PCT_PLAN}, members=MEMBERS, year=2026)
    assert any("verify against irs.gov" in f for f in a.findings)


def test_unused_after_tax_headroom_is_surfaced_with_both_preconditions():
    a = C.audit_space({"employer_plan": PCT_PLAN}, members=MEMBERS, year=2026)
    f = " ".join(a.findings)
    assert "unused" in f
    assert "in-plan Roth conversion" in f
    assert "Both" in f  # after-tax alone is a trap


def test_fully_used_plan_space_says_so():
    plan = dict(DFD_PLAN, employee_pre_tax=32_500, employee_after_tax=31_250,
                employer_match=12_250, employer_other=4_000)
    a = C.audit_space({"employer_plan": plan},
                      members=[{"id": "a1", "role": "primary", "age": 52}],
                      year=2026)
    assert line(a, "Employer plan").unused == 0
    assert any("fully used" in f for f in a.findings)


def test_compensation_above_the_401a17_cap_is_flagged():
    plan = dict(DFD_PLAN, compensation=394_400)
    a = C.audit_space({"employer_plan": plan},
                      members=[{"id": "a1", "role": "primary", "age": 52}],
                      year=2026)
    assert any("401(a)(17)" in f for f in a.findings)


def test_after_tax_without_recorded_conversion_route_is_flagged():
    plan = dict(DFD_PLAN, employee_after_tax=30_000)
    plan.pop("in_plan_roth_conversion", None)
    a = C.audit_space({"employer_plan": plan},
                      members=[{"id": "a1", "role": "primary", "age": 52}],
                      year=2026)
    assert any("conversion route" in f for f in a.findings)


def test_ira_space_uses_the_named_members_own_age():
    a = C.audit_space(
        {"ira": [{"member": "a1", "amount": 7_500},
                 {"member": "a2", "amount": 7_500}]},
        members=[{"id": "a1", "role": "primary", "age": 52},
                 {"id": "a2", "role": "spouse", "age": 39}],
        year=2026)
    assert line(a, "IRA — a1").available == L26.ira_contribution + L26.ira_catch_up
    assert line(a, "IRA — a2").available == L26.ira_contribution


def test_backdoor_roth_always_warns_about_pro_rata():
    a = C.audit_space({"ira": [{"member": "a1", "type": "roth_backdoor",
                                "amount": 7_500}]},
                      members=MEMBERS, year=2026)
    assert any("pro-rata rule" in f for f in a.findings)


def test_plain_ira_does_not_warn_about_pro_rata():
    a = C.audit_space({"ira": [{"member": "a1", "type": "roth", "amount": 7_500}]},
                      members=MEMBERS, year=2026)
    assert not any("pro-rata" in f for f in a.findings)


def test_ineligible_hsa_produces_a_note_not_a_line():
    a = C.audit_space({"hsa": {"coverage": "family", "eligible": False}},
                      members=MEMBERS, year=2026)
    assert not any(l.name.startswith("HSA") for l in a.lines)
    assert any("high-deductible" in f for f in a.findings)


def test_eligible_hsa_counts_unused_space():
    a = C.audit_space({"hsa": {"coverage": "family", "eligible": True,
                               "contribution": 0}},
                      members=MEMBERS, year=2026)
    assert line(a, "HSA").unused == L26.hsa_family


def test_total_unused_sums_the_lines():
    a = C.audit_space({"hsa": {"coverage": "family", "eligible": True,
                               "contribution": 0},
                       "ira": [{"member": "a1", "amount": 0}]},
                      members=MEMBERS, year=2026)
    assert a.total_unused == L26.hsa_family + L26.ira_contribution
