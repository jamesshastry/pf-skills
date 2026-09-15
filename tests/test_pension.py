"""Foreign pension classification — the bucket, and the refusal to guess it."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import pension as N  # noqa: E402


def held(scheme, **kw):
    base = {"scheme": scheme}
    base.update(kw)
    return base


# ── the table is cited, and silence is the answer ───────────────────────────


def test_every_entry_carries_a_source_and_a_verified_date():
    for key in N.schemes_available():
        s = N.scheme_for(key)
        assert s.source, key
        assert s.verified_on, key


def test_an_unlisted_scheme_returns_unknown_rather_than_the_nearest_match():
    c = N.classify(held("de_riester"))
    assert c.bucket == N.UNKNOWN_BUCKET
    assert not c.determinable


def test_the_unknown_path_refuses_reasoning_by_analogy_explicitly():
    c = N.classify(held("nz_kiwisaver"))
    assert any("confidently wrong" in f for f in c.findings)
    assert any("not in the table" in f for f in c.findings)


def test_the_unknown_path_lists_what_has_been_checked():
    c = N.classify(held("nz_kiwisaver"))
    assert any("in_epf" in f for f in c.findings)


def test_no_scheme_recorded_is_also_unknown():
    assert N.classify({}).bucket == N.UNKNOWN_BUCKET
    assert N.scheme_for(None) is N.UNKNOWN


def test_scheme_lookup_is_case_insensitive():
    assert N.scheme_for("IN_EPF").key == "in_epf"


# ── treaty-protected ────────────────────────────────────────────────────────


def test_a_uk_workplace_pension_is_treaty_protected():
    c = N.classify(held("uk_workplace_pension"))
    assert c.bucket == N.TREATY_PROTECTED
    assert not c.problematic


def test_an_rrsp_is_treaty_protected_and_automatic():
    c = N.classify(held("ca_rrsp"))
    assert c.bucket == N.TREATY_PROTECTED
    assert "Rev. Proc. 2014-55" in " ".join(N.CA_RRSP.notes)


def test_treaty_protection_does_not_remove_the_trust_forms_by_itself():
    """It is the revenue procedure, not the treaty, that reaches 3520."""
    c = N.classify(held("uk_workplace_pension"))
    assert "Form 3520" not in c.forms
    assert any("not a no-filing bucket" in f for f in c.findings)


def test_a_self_directed_sipp_stays_treaty_protected():
    """Holder direction tips other schemes toward grantor trust. Here the
    table's cited treaty position governs, which is why it is a table."""
    c = N.classify(held("uk_sipp", holder_directs_investments=True,
                        employee_contributions_to_date=90_000,
                        employer_contributions_to_date=0))
    assert c.bucket == N.TREATY_PROTECTED


def test_treaty_relief_is_described_as_claimed_not_automatic():
    c = N.classify(held("uk_sipp"))
    assert any("claimed, not automatic" in f for f in c.findings)


# ── the problem cases ───────────────────────────────────────────────────────


def test_superannuation_is_not_treaty_protected():
    c = N.classify(held("au_superannuation"))
    assert c.bucket != N.TREATY_PROTECTED
    assert c.problematic


# ── contested is a finding, not a placeholder for one ───────────────────────


def test_superannuation_defaults_to_contested_rather_than_the_favourable_side():
    """Its own table note calls it the best-known problem case. A machine-
    readable §402(b) default contradicted the prose that hedged around it."""
    c = N.classify(held("au_superannuation"))
    assert c.bucket == N.CONTESTED
    assert c.contested


def test_a_contested_scheme_is_still_problematic_and_still_points_at_3520():
    c = N.classify(held("au_superannuation"))
    assert c.problematic
    assert "Form 3520" in c.forms and "Form 3520-A" in c.forms
    assert any("conservative" in f for f in c.findings)


def test_contested_says_it_will_not_pick_between_the_readings():
    c = N.classify(held("au_superannuation"))
    assert any("will not pick between them" in f for f in c.findings)


def test_a_recorded_employer_weighted_split_narrows_contested_to_402b():
    """The contested default is narrowed only by a fact the household gave."""
    c = N.classify(held("au_superannuation",
                        employee_contributions_to_date=10_000,
                        employer_contributions_to_date=90_000))
    assert c.bucket == N.EMPLOYEES_TRUST_402B
    assert not c.contested


def test_a_scheme_with_a_settled_unfavourable_default_is_not_narrowed_upward():
    """CPF has no treaty at all. An employer-weighted split does not buy it
    the employees'-trust reading — only a contested default is narrowable."""
    c = N.classify(held("sg_cpf", employee_contributions_to_date=10_000,
                        employer_contributions_to_date=90_000))
    assert c.bucket == N.FOREIGN_GRANTOR_TRUST


def test_the_audit_names_contested_schemes_separately():
    a = N.audit([held("au_superannuation"), held("uk_sipp")])
    assert len(a.contested) == 1
    assert any("contested rather than classified" in f for f in a.findings)


# ── EPF and PPF are two instruments ─────────────────────────────────────────


def test_epf_and_ppf_are_separate_rows():
    assert "in_epf" in N.schemes_available()
    assert "in_ppf" in N.schemes_available()
    assert N.IN_EPF is not N.IN_PPF


def test_epf_no_longer_claims_to_cover_ppf():
    assert "PPF" not in N.IN_EPF.name


def test_a_ppf_does_not_get_the_employees_trust_reading_by_default():
    """A PPF has no employer, so §402(b) has nothing to attach to. Under the
    single combined row it got the favourable reading of a structurally
    impossible characterisation."""
    c = N.classify(held("in_ppf"))
    assert c.bucket == N.FOREIGN_GRANTOR_TRUST
    assert any("entirely self-funded" in n for n in N.IN_PPF.notes)


def test_a_ppf_is_holder_directed_by_design():
    assert N.IN_PPF.holder_directed_by_design is True


def test_cpf_defaults_to_grantor_trust_because_there_is_no_treaty_at_all():
    c = N.classify(held("sg_cpf"))
    assert c.bucket == N.FOREIGN_GRANTOR_TRUST
    assert "no US–Singapore income tax treaty" in " ".join(N.SG_CPF.notes)


def test_indian_epf_is_in_the_table_and_problematic():
    c = N.classify(held("in_epf"))
    assert c.scheme.known
    assert c.problematic
    assert c.bucket == N.CONTESTED


def test_no_treaty_article_number_is_encoded_for_india():
    """`crossborder.py` refuses to encode one for the same country and says so
    on purpose. Two modules asserting different confidence about one treaty is
    a policy split, not a nuance."""
    for s in (N.IN_EPF, N.IN_PPF):
        assert s.treaty_article is None, s.key
        assert "no article number encoded" in s.source


def test_indian_epf_raises_the_accrual_question_without_answering_it():
    notes = " ".join(N.IN_EPF.notes)
    assert "the open question" in notes
    assert "no article number is encoded here" in notes
    c = N.classify(held("in_epf"))
    assert any("no foreign tax credit" in f for f in c.findings)


def test_employee_contributions_exceeding_employer_tips_to_grantor_trust():
    c = N.classify(held("in_epf", employee_contributions_to_date=80_000,
                        employer_contributions_to_date=20_000))
    assert c.bucket == N.FOREIGN_GRANTOR_TRUST
    assert any("employee contributions" in d for d in c.drivers)


def test_employer_contributions_exceeding_employee_stays_402b():
    c = N.classify(held("in_epf", employee_contributions_to_date=20_000,
                        employer_contributions_to_date=80_000))
    assert c.bucket == N.EMPLOYEES_TRUST_402B
    assert any("supports the employees'-trust reading" in d for d in c.drivers)


def test_holder_directed_investment_tips_to_grantor_trust_on_its_own():
    c = N.classify(held("au_superannuation", holder_directs_investments=True,
                        employee_contributions_to_date=10_000,
                        employer_contributions_to_date=90_000))
    assert c.bucket == N.FOREIGN_GRANTOR_TRUST
    assert any("directs the investments" in d for d in c.drivers)


def test_an_absent_contribution_split_is_named_as_the_weakest_input():
    c = N.classify(held("au_superannuation"))
    assert any("weakest input" in f for f in c.findings)
    assert any("cannot be narrowed" in f for f in c.findings)


def test_the_non_treaty_buckets_both_point_at_3520_and_3520a():
    for scheme in ("au_superannuation", "sg_cpf", "in_epf"):
        c = N.classify(held(scheme))
        assert "Form 3520" in c.forms and "Form 3520-A" in c.forms, scheme


def test_the_ten_thousand_dollar_penalty_floor_is_stated():
    c = N.classify(held("sg_cpf"))
    assert N.PENALTY_FLOOR == 10_000
    assert any("$10,000" in f for f in c.findings)


# ── what it refuses to do ───────────────────────────────────────────────────


def test_fbar_and_8938_are_raised_for_every_bucket():
    for scheme in ("uk_sipp", "in_epf", "sg_cpf", "not_a_scheme"):
        c = N.classify(held(scheme))
        assert any("FBAR and Form 8938" in f for f in c.findings), scheme


def test_thresholds_are_delegated_to_the_reporting_skill():
    c = N.classify(held("in_epf"))
    assert any("foreign-reporting-audit" in f for f in c.findings)


def test_it_produces_a_bucket_and_says_it_is_not_a_position():
    c = N.classify(held("in_epf"))
    assert any("a bucket, not a position" in f for f in c.findings)


# ── the audit across a household ────────────────────────────────────────────


def test_no_pensions_recorded_asks_for_an_explicit_empty_list():
    a = N.audit([])
    assert any("foreign_pensions: []" in f for f in a.findings)


def test_a_dormant_scheme_still_counts():
    a = N.audit(None)
    assert any("dormant" in f for f in a.findings)


def test_the_audit_separates_problematic_from_unknown():
    a = N.audit([held("uk_sipp"), held("in_epf"), held("de_riester")])
    assert len(a.problematic) == 1
    assert len(a.unknown) == 1
    assert any("outside treaty protection" in f for f in a.findings)
    assert any("not in the table" in f for f in a.findings)


def test_an_all_treaty_household_is_told_so_without_being_told_it_is_done():
    a = N.audit([held("uk_workplace_pension"), held("ca_rrsp")])
    assert not a.problematic and not a.unknown
    assert any("still has to be claimed" in f for f in a.findings)
