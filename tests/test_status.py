"""Citizenship, immigration status and domicile — review finding A1."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import status as S  # noqa: E402

CITIZEN_PAIR = [
    {"id": "a1", "role": "primary", "us_status": S.CITIZEN, "citizenship": ["US"]},
    {"id": "a2", "role": "spouse", "us_status": S.CITIZEN, "citizenship": ["US"]},
]
MIXED = [
    {"id": "a1", "role": "primary", "us_status": S.CITIZEN, "citizenship": ["US"]},
    {"id": "a2", "role": "spouse", "us_status": S.PERMANENT_RESIDENT,
     "citizenship": ["CA"]},
]
VISA_PAIR = [
    {"id": "a1", "role": "primary", "us_status": S.NONIMMIGRANT, "citizenship": ["IN"]},
    {"id": "a2", "role": "spouse", "us_status": S.NONIMMIGRANT, "citizenship": ["IN"]},
]
US_DOM = {"country": "US", "state": "CA", "determined": True}


def areas(a, area):
    return [f for f in a.findings if f.area == area]


def joined(a):
    return " ".join(f.detail for f in a.findings)


# ── the three statuses are distinct ─────────────────────────────────────────


def test_a_nonimmigrant_visa_holder_is_still_a_us_tax_resident():
    """The visa category changes immigration rights, not income-tax reach."""
    a = S.audit(VISA_PAIR, domicile=US_DOM)
    assert a.us_person is True
    assert any("worldwide income" in f.detail for f in areas(a, "income tax"))


def test_status_not_recorded_blocks_everything():
    a = S.audit([{"id": "a1", "role": "primary"}], domicile=US_DOM)
    assert a.us_person is None
    assert a.blockers
    assert "all" in a.affected_skills


# ── the marital deduction turns on the SPOUSE's citizenship ─────────────────


def test_a_non_citizen_spouse_loses_the_unlimited_marital_deduction():
    for members in (MIXED, VISA_PAIR):
        a = S.audit(members, domicile=US_DOM)
        estate = areas(a, "estate")
        assert any(f.severity == "blocker" and "QDOT" in f.detail for f in estate)


def test_two_citizens_have_no_marital_deduction_problem():
    a = S.audit(CITIZEN_PAIR, domicile=US_DOM)
    assert not any("QDOT" in f.detail for f in a.findings)


def test_the_marital_finding_names_the_skills_it_invalidates():
    a = S.audit(MIXED, domicile=US_DOM)
    f = next(x for x in a.findings if "QDOT" in x.detail)
    assert "survivor-needs" in f.affects
    assert "life-insurance-review" in f.affects


def test_a_permanent_resident_spouse_is_still_a_non_citizen():
    """Green card is not citizenship, and the marital deduction turns on
    citizenship — a distinction that costs real money."""
    a = S.audit(MIXED, domicile=US_DOM)
    assert any("QDOT" in f.detail for f in a.findings)


# ── domicile is a different test from residence ─────────────────────────────


def test_missing_domicile_is_a_blocker():
    a = S.audit(CITIZEN_PAIR, domicile=None)
    assert any(f.severity == "blocker" and "Domicile is not recorded" in f.detail
               for f in a.findings)


def test_assumed_us_domicile_is_flagged_as_assumed():
    a = S.audit(CITIZEN_PAIR, domicile={"country": "US", "determined": False})
    f = next(x for x in a.findings if "assumed rather than determined" in x.detail)
    assert f.severity == "gap"
    assert "$60,000" in f.detail


def test_determined_us_domicile_raises_nothing():
    a = S.audit(CITIZEN_PAIR, domicile=US_DOM)
    assert not any("domicile" in f.detail.lower() and f.severity != "ok"
                   for f in a.findings)


def test_foreign_domicile_limits_the_estate_to_us_situs_assets():
    a = S.audit(CITIZEN_PAIR, domicile={"country": "IN", "determined": True})
    f = next(x for x in a.findings if "US-situs" in x.detail)
    assert f.severity == "blocker"
    assert "$60,000" in f.detail


# ── expatriation reaches only two of the four statuses ──────────────────────


def test_no_expatriation_exposure_without_citizenship_or_a_green_card():
    a = S.audit(VISA_PAIR, domicile=US_DOM)
    f = next(x for x in a.findings if x.area == "expatriation")
    assert f.severity == "ok"
    assert "before accepting a green card" in f.detail


def test_citizens_and_permanent_residents_are_exposed():
    for members in (CITIZEN_PAIR, MIXED):
        a = S.audit(members, domicile=US_DOM)
        f = next(x for x in a.findings if x.area == "expatriation")
        assert f.severity == "note"
        assert "877A" in f.detail


def test_the_long_term_resident_window_is_stated():
    a = S.audit(CITIZEN_PAIR, domicile=US_DOM)
    f = next(x for x in a.findings if x.area == "expatriation")
    assert "8 of the last 15" in f.detail


# ── totalization ────────────────────────────────────────────────────────────


def test_no_us_india_totalization_agreement():
    t = S.totalization("IN")
    assert t.known and t.agreement is False
    assert "no coordination" in t.note


def test_an_agreement_country_reads_differently():
    assert S.totalization("GB").agreement is True


def test_an_unknown_country_refuses_to_guess():
    t = S.totalization("ZZ")
    assert not t.known and t.agreement is None
    notes = S.social_security_notes(statuses={"a1": S.CITIZEN}, home_country="ZZ")
    assert any("not in the table" in n for n in notes)


def test_every_known_country_carries_provenance():
    for c in S.countries_available():
        t = S.totalization(c)
        assert t.source and t.verified_on


def test_non_citizens_get_the_payability_caveat():
    notes = S.social_security_notes(statuses={"a1": S.NONIMMIGRANT},
                                    home_country="IN")
    joined_notes = " ".join(notes)
    assert "Entitlement and payability are different" in joined_notes


def test_citizens_do_not():
    notes = S.social_security_notes(statuses={"a1": S.CITIZEN}, home_country="IN")
    assert not any("payability" in n for n in notes)


# ── the audit points at what it invalidates ─────────────────────────────────


def test_the_audit_lists_affected_shipped_skills():
    a = S.audit(VISA_PAIR, domicile={"country": "US", "determined": False})
    assert "estate-document-review" in a.affected_skills
    assert "foreign-reporting-audit" in a.affected_skills
