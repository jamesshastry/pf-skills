"""Unit tests for the California disclosure checklist.

The arithmetic is trivial; the refusals are the point. An unrecorded build year
must not drop a disclosure, an unrecorded association field must not read as
clean, and no state but California may produce a checklist at all.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from pf import disclosure as D  # noqa: E402


def keys(ds):
    return {d.key for d in ds}


# ── which disclosures apply ─────────────────────────────────────────────────

def test_a_pre_1978_home_attracts_the_lead_paint_disclosure():
    assert "lead_paint" in keys(D.required_disclosures(
        property_type=D.SINGLE_FAMILY, year_built=1974))


def test_a_post_1978_home_does_not():
    assert "lead_paint" not in keys(D.required_disclosures(
        property_type=D.SINGLE_FAMILY, year_built=1985))


def test_the_year_boundary_is_the_year_itself():
    """Built *in* 1978 is not built *before* 1978."""
    assert "lead_paint" not in keys(D.required_disclosures(
        property_type=D.SINGLE_FAMILY, year_built=D.LEAD_PAINT_YEAR))
    assert "lead_paint" in keys(D.required_disclosures(
        property_type=D.SINGLE_FAMILY, year_built=D.LEAD_PAINT_YEAR - 1))


def test_an_unknown_year_keeps_the_year_gated_disclosures():
    """The refusal that matters most here. Dropping lead paint because nobody
    recorded the build year turns an open question into a silent answer."""
    ds = keys(D.required_disclosures(property_type=D.SINGLE_FAMILY,
                                     year_built=None))
    assert "lead_paint" in ds
    assert "earthquake_guide" in ds


def test_the_unknown_year_items_are_reported_as_such():
    flagged = {d.key for d in D.year_gated_but_unknown(year_built=None)}
    assert "lead_paint" in flagged
    assert D.year_gated_but_unknown(year_built=1974) == []


def test_a_detached_home_attracts_no_association_disclosures():
    ds = keys(D.required_disclosures(property_type=D.SINGLE_FAMILY,
                                     year_built=2001))
    assert not ({"hoa_packet", "reserve_study", "sb326"} & ds)


def test_a_condo_attracts_them():
    ds = keys(D.required_disclosures(property_type=D.CONDO, year_built=2001))
    assert {"hoa_packet", "reserve_study", "sb326"} <= ds


def test_a_townhome_is_treated_as_a_common_interest_development():
    assert D.is_cid(D.TOWNHOME)
    assert not D.is_cid(D.SINGLE_FAMILY)


def test_every_disclosure_names_an_authority_and_a_reason():
    for d in D.DISCLOSURES:
        assert d.authority.strip(), d.key
        assert len(d.why) > 40, d.key


# ── completeness ────────────────────────────────────────────────────────────

def test_missing_reports_are_named():
    missing = dict(D.missing_reports(["tds", "general_inspection"],
                                     property_type=D.SINGLE_FAMILY))
    assert "sewer" in missing and "roof" in missing
    assert "general_inspection" not in missing


def test_nothing_provided_means_everything_is_missing():
    assert len(D.missing_reports([], property_type=D.SINGLE_FAMILY)) == \
        len(D.STANDARD_REPORTS[D.SINGLE_FAMILY])
    assert len(D.missing_reports(None, property_type=D.SINGLE_FAMILY)) == \
        len(D.STANDARD_REPORTS[D.SINGLE_FAMILY])


def test_the_packet_list_is_the_statutory_one():
    missing = dict(D.missing_packet_items(["governing_documents", "budget"]))
    assert "reserve_study" in missing
    assert "minutes" in missing
    assert "governing_documents" not in missing


def test_a_complete_packet_reports_nothing_missing():
    assert D.missing_packet_items([k for k, _ in D.HOA_PACKET_ITEMS]) == []


# ── SB 326 ──────────────────────────────────────────────────────────────────

def sb(**kw):
    base = {"property_type": D.CONDO, "unit_count": 36,
            "elevated_elements": True, "report": None}
    return D.sb326(**{**base, **kw})


def test_sb326_does_not_reach_a_detached_home():
    assert sb(property_type=D.SINGLE_FAMILY).applies is False


def test_sb326_needs_three_units():
    assert sb(unit_count=D.SB326_MIN_UNITS).applies is True
    assert sb(unit_count=D.SB326_MIN_UNITS - 1).applies is False


def test_sb326_needs_wood_supported_elevated_elements():
    assert sb(elevated_elements=False).applies is False


def test_sb326_cannot_be_determined_without_the_facts():
    """Not 'does not apply'. The duty may well exist; nobody has checked."""
    assert sb(unit_count=None).applies is None
    assert sb(elevated_elements=None).applies is None
    assert "Cannot be determined" in sb(unit_count=None).detail


def test_no_inspection_is_a_finding_not_a_gap():
    out = sb(report="none")
    assert out.applies is True
    assert "obligation exists" in out.detail


def test_findings_push_toward_the_funding_question():
    assert "funded" in sb(report="findings").detail


def test_an_unrecorded_report_is_not_read_as_done():
    out = sb(report=None)
    assert out.status == "unrecorded"
    assert "not evidence that the inspection was done" in out.detail


# ── association thresholds ──────────────────────────────────────────────────

def test_the_reserve_bands():
    assert D.reserve_band(0.85) == "strong"
    assert D.reserve_band(D.RESERVE_STRONG) == "strong"
    assert D.reserve_band(0.50) == "fair"
    assert D.reserve_band(D.RESERVE_WEAK) == "fair"
    assert D.reserve_band(D.RESERVE_WEAK - 0.01) == "weak"
    assert D.reserve_band(None) is None


def test_an_empty_association_is_a_high_flag_not_a_clean_one():
    r = D.review_hoa({})
    assert not r.determinable
    assert r.high


def test_weak_reserves_are_high_severity():
    r = D.review_hoa({"reserve_percent_funded": 0.20})
    assert any(f.topic == "Reserves" and f.severity == "high" for f in r.flags)


def test_strong_reserves_still_point_at_the_component_list():
    r = D.review_hoa({"reserve_percent_funded": 0.90})
    note = next(f for f in r.flags if f.topic == "Reserves")
    assert note.severity == "note"
    assert "component list" in note.detail


def test_delinquency_above_the_threshold_is_framed_as_a_resale_problem():
    r = D.review_hoa({"delinquency_rate": D.DELINQUENCY_FINANCING_RISK + 0.01})
    f = next(f for f in r.flags if f.topic == "Delinquencies")
    assert f.severity == "high"
    assert "resale" in f.detail


def test_delinquency_at_the_threshold_does_not_fire():
    r = D.review_hoa({"delinquency_rate": D.DELINQUENCY_FINANCING_RISK})
    assert not [f for f in r.flags
                if f.topic == "Delinquencies" and f.severity == "high"]


def test_an_unrecorded_field_is_a_note_never_a_pass():
    """The whole discipline in one assertion: silence is not good news."""
    r = D.review_hoa({"reserve_percent_funded": 0.80})
    assert not r.determinable
    topics = {f.topic for f in r.flags}
    assert "Delinquencies" in topics and "Litigation" in topics


def test_construction_defect_litigation_is_high_and_mentions_warrantability():
    r = D.review_hoa({"litigation": "construction_defect"})
    f = next(f for f in r.flags if f.topic == "Litigation")
    assert f.severity == "high"
    assert "non-warrantable" in f.detail


def test_litigation_recorded_as_none_does_not_flag():
    r = D.review_hoa({"litigation": "none"})
    assert not [f for f in r.flags if f.topic == "Litigation"]


def test_a_pending_special_assessment_is_high():
    r = D.review_hoa({"special_assessment_pending": True})
    assert any(f.topic == "Special assessment" and f.severity == "high"
               for f in r.flags)


def test_a_non_renewed_master_policy_is_high():
    r = D.review_hoa({"master_policy_non_renewed": True})
    assert any(f.topic == "Insurance" and f.severity == "high"
               for f in r.flags)


def test_low_reserve_contribution_is_high():
    r = D.review_hoa({"reserve_contribution_share":
                      D.RESERVE_CONTRIBUTION_MIN - 0.01})
    assert any(f.topic == "Reserve contribution" and f.severity == "high"
               for f in r.flags)


# ── rental restrictions ─────────────────────────────────────────────────────

def test_a_cap_below_the_statutory_floor_is_flagged_as_contestable():
    note = D.rental_restriction_note(0.15)
    assert "§4741" in note
    assert "counsel" in note


def test_a_cap_at_or_above_the_floor_is_reported_plainly():
    note = D.rental_restriction_note(D.RENTAL_CAP_FLOOR)
    assert "counsel" not in note
    assert "current count" in note


def test_no_recorded_cap_produces_no_claim():
    assert D.rental_restriction_note(None) is None
