"""Cluster 3 — beneficiary and estate audits. Synthetic fixtures only."""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import estate as E  # noqa: E402

TODAY = dt.date(2026, 8, 30)
MEMBERS = [
    {"id": "a1", "role": "primary", "age": 41},
    {"id": "a2", "role": "spouse", "age": 39},
    {"id": "c1", "role": "dependent", "age": 8},
    {"id": "c2", "role": "dependent", "age": 5},
]
SPOUSE = {"name": "Ana", "member_id": "a2", "relationship": "spouse",
          "share": 100, "type": "primary"}
TRUST = {"name": "Trust", "relationship": "trust", "share": 100,
         "type": "contingent"}


def sev(a, subject):
    return {f.severity for f in a.findings if f.subject == subject}


def details(a, subject):
    return " ".join(f.detail for f in a.findings if f.subject == subject)


# ── the three states ────────────────────────────────────────────────────────


def test_omitted_is_unknown_not_empty():
    a = E.audit_beneficiaries([("acct", {})], members=MEMBERS, trust_funded=None)
    assert a.unknown == 1
    assert sev(a, "acct") == {"gap"}
    assert "Not recorded" in details(a, "acct")


def test_empty_list_is_a_blocker_because_someone_looked():
    a = E.audit_beneficiaries([("acct", {"beneficiaries": []})],
                              members=MEMBERS, trust_funded=None)
    assert a.unknown == 0
    assert "blocker" in sev(a, "acct")
    assert "No beneficiary named" in details(a, "acct")


def test_not_applicable_is_skipped_entirely():
    a = E.audit_beneficiaries([("car", {"beneficiary_applicable": False})],
                              members=MEMBERS, trust_funded=None)
    assert a.findings == []
    assert a.checked == 0


# ── designation defects ─────────────────────────────────────────────────────


def test_clean_designation_passes():
    a = E.audit_beneficiaries([("acct", {"beneficiaries": [SPOUSE, TRUST]})],
                              members=MEMBERS, trust_funded=True)
    assert sev(a, "acct") == {"ok"}
    assert a.blockers == []


def test_missing_contingent_is_the_common_defect():
    a = E.audit_beneficiaries([("acct", {"beneficiaries": [SPOUSE]})],
                              members=MEMBERS, trust_funded=None)
    assert "gap" in sev(a, "acct")
    assert "No contingent beneficiary" in details(a, "acct")


def test_primary_shares_not_totalling_100_is_a_blocker():
    b = [dict(SPOUSE, share=60)]
    a = E.audit_beneficiaries([("acct", {"beneficiaries": b})],
                              members=MEMBERS, trust_funded=None)
    assert "blocker" in sev(a, "acct")
    assert "60%" in details(a, "acct")


def test_contingent_only_has_no_primary():
    a = E.audit_beneficiaries([("acct", {"beneficiaries": [TRUST]})],
                              members=MEMBERS, trust_funded=True)
    assert "none is primary" in details(a, "acct")


def test_minor_named_directly_is_a_blocker():
    kid = {"name": "Mateo", "member_id": "c1", "relationship": "child",
           "share": 100, "type": "primary"}
    a = E.audit_beneficiaries([("529", {"beneficiaries": [kid]})],
                              members=MEMBERS, trust_funded=None)
    assert "blocker" in sev(a, "529")
    assert "Mateo" in details(a, "529")
    assert "guardian of the estate" in details(a, "529")


def test_adult_child_named_directly_is_fine():
    grown = [{"id": "a1", "role": "primary", "age": 60},
             {"id": "c1", "role": "dependent", "age": 25}]
    kid = {"name": "Sam", "member_id": "c1", "relationship": "child",
           "share": 100, "type": "primary"}
    a = E.audit_beneficiaries([("acct", {"beneficiaries": [kid]})],
                              members=grown, trust_funded=None)
    assert not a.blockers


def test_member_without_a_recorded_age_is_not_assumed_to_be_a_minor():
    ageless = [{"id": "c9", "role": "dependent"}]
    b = {"name": "?", "member_id": "c9", "relationship": "child",
         "share": 100, "type": "primary"}
    a = E.audit_beneficiaries([("acct", {"beneficiaries": [b]})],
                              members=ageless, trust_funded=None)
    assert not a.blockers


def test_estate_named_as_beneficiary_is_flagged():
    b = {"name": "my estate", "relationship": "estate", "share": 100,
         "type": "primary"}
    a = E.audit_beneficiaries([("ira", {"beneficiaries": [b]})],
                              members=MEMBERS, trust_funded=None)
    assert "forces probate" in details(a, "ira")


def test_unfunded_trust_named_as_beneficiary_gets_a_caveat():
    a = E.audit_beneficiaries([("acct", {"beneficiaries": [SPOUSE, TRUST]})],
                              members=MEMBERS, trust_funded=False)
    assert "unfunded" in details(a, "acct")


def test_per_stirpes_unset_with_children_is_a_note():
    kids = [{"name": "A", "member_id": "c1", "relationship": "child",
             "share": 50, "type": "primary"},
            {"name": "B", "member_id": "c2", "relationship": "child",
             "share": 50, "type": "primary"}]
    a = E.audit_beneficiaries([("acct", {"beneficiaries": kids})],
                              members=MEMBERS, trust_funded=None)
    assert "per_stirpes" in details(a, "acct")


# ── documents ───────────────────────────────────────────────────────────────


def test_absent_document_list_reports_everything_as_not_recorded():
    a = E.audit_documents([], today=TODAY)
    assert a.unknown == len(E.EXPECTED_DOCUMENTS)
    assert a.blockers == []  # unknown is not a blocker


def test_explicitly_absent_poa_is_a_blocker():
    a = E.audit_documents([{"type": "financial_poa", "exists": False}], today=TODAY)
    assert "blocker" in sev(a, "financial_poa")


def test_absent_trust_is_only_a_note_because_it_is_optional():
    a = E.audit_documents([{"type": "revocable_trust", "exists": False}], today=TODAY)
    assert sev(a, "revocable_trust") == {"note"}


def test_stale_document_is_flagged_with_its_age():
    a = E.audit_documents(
        [{"type": "will", "exists": True, "last_reviewed": "2016-05-14"}], today=TODAY)
    assert "gap" in sev(a, "will")
    assert "10 years ago" in details(a, "will")


def test_recent_document_passes():
    a = E.audit_documents(
        [{"type": "will", "exists": True, "last_reviewed": "2024-01-01"}], today=TODAY)
    assert "ok" in sev(a, "will")


def test_existing_document_with_no_review_date_is_a_gap():
    a = E.audit_documents([{"type": "will", "exists": True}], today=TODAY)
    assert "no review date recorded" in details(a, "will")


def test_unfunded_trust_is_a_blocker_in_its_own_right():
    a = E.audit_documents(
        [{"type": "revocable_trust", "exists": True, "funded": False,
          "last_reviewed": "2025-01-01"}], today=TODAY)
    assert "blocker" in sev(a, "revocable_trust_funding")
    assert "owns nothing does nothing" in details(a, "revocable_trust_funding")


def test_trust_funding_unknown_is_a_gap_not_a_pass():
    a = E.audit_documents(
        [{"type": "revocable_trust", "exists": True, "last_reviewed": "2025-01-01"}],
        today=TODAY)
    assert "gap" in sev(a, "revocable_trust_funding")


def test_funded_trust_passes():
    a = E.audit_documents(
        [{"type": "revocable_trust", "exists": True, "funded": True,
          "last_reviewed": "2025-01-01"}], today=TODAY)
    assert "ok" in sev(a, "revocable_trust_funding")


def test_unparseable_review_date_does_not_crash():
    a = E.audit_documents(
        [{"type": "will", "exists": True, "last_reviewed": "sometime in 2016"}],
        today=TODAY)
    assert "no review date recorded" in details(a, "will")


# ── digital ─────────────────────────────────────────────────────────────────


def test_absent_digital_block_is_all_unknown():
    a = E.audit_digital(None)
    assert a.unknown == len(E.DIGITAL_CHECKS)


def test_vault_without_emergency_access_is_the_blocker():
    a = E.audit_digital({"password_manager": True,
                         "emergency_access_configured": False,
                         "account_inventory": True,
                         "two_factor_recovery_documented": True})
    assert len(a.blockers) == 1
    assert "single point of failure" in a.blockers[0].detail


def test_no_vault_at_all_produces_no_combination_blocker():
    """The combination finding is about a false sense of security, which
    requires the vault to exist."""
    a = E.audit_digital({"password_manager": False,
                         "emergency_access_configured": False,
                         "account_inventory": False,
                         "two_factor_recovery_documented": False})
    assert a.blockers == []


def test_fully_configured_digital_estate_passes():
    a = E.audit_digital({k: True for k in E.DIGITAL_CHECKS})
    assert a.blockers == []
    assert all(f.severity == "ok" for f in a.findings)


# ── ordering ────────────────────────────────────────────────────────────────


def test_findings_sort_blockers_first():
    a = E.audit_documents(
        [{"type": "financial_poa", "exists": False},
         {"type": "will", "exists": True, "last_reviewed": "2025-01-01"}],
        today=TODAY)
    assert a.sorted[0].severity == "blocker"
    assert a.sorted[-1].severity in ("gap", "ok")
