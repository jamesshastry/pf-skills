"""Unit tests for the intake worklist.

The thing worth testing here is not the arithmetic — there is barely any — but
the refusals: that a filename never becomes a value, that an empty section is
treated as unanswered, and that the privacy warning does not cry wolf.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from pf import intake as I  # noqa: E402


# ── document classification ─────────────────────────────────────────────────

def test_a_filename_suggests_an_area_but_never_a_value():
    d = I.classify("geico-auto-2026.pdf", 1024)
    assert "auto" in d.suggests
    # The Document carries no field, amount or parsed content of any kind.
    assert not hasattr(d, "value")
    assert set(vars(d)) == {"name", "size_bytes", "suggests"}


def test_an_unrecognised_filename_is_reported_rather_than_dropped():
    d = I.classify("scan001.pdf")
    assert d.unrecognised
    assert d.suggests == ()


def test_matching_is_case_insensitive():
    assert I.classify("VANGUARD-Statement.PDF").suggests


# ── the privacy warning ─────────────────────────────────────────────────────

def test_a_name_in_a_filename_is_flagged():
    assert I.looks_renamed_for_privacy("Jane-Q-Smith-november.pdf")


def test_an_account_number_in_a_filename_is_flagged():
    assert I.looks_renamed_for_privacy("statement-acct-44172.pdf")


def test_a_year_is_not_an_account_number():
    """The warning has to stay quiet on the single most useful thing to put in
    a statement filename, or it trains the reader to ignore it."""
    assert not I.looks_renamed_for_privacy("geico-auto-2026.pdf")


def test_a_tax_form_number_is_not_an_account_number():
    """1040, 1099, 8938 and 5471 are all four digits. Flagging them would
    make the warning fire on most well-named tax documents."""
    for n in ("1040-2025.pdf", "1099-int-2025.pdf", "8938-2024.pdf",
              "5471-2023.pdf"):
        assert not I.looks_renamed_for_privacy(n), n


def test_an_ordinary_filename_is_not_flagged():
    assert not I.looks_renamed_for_privacy("401k-statement-q2.pdf")


# ── presence ────────────────────────────────────────────────────────────────

def test_an_empty_list_counts_as_unanswered():
    """A stubbed-out section is not an answer. `vehicles: []` means someone
    created the key and never filled it."""
    assert not I._present({"auto": {"vehicles": []}}, "auto.vehicles")


def test_a_populated_list_counts_as_present():
    assert I._present({"auto": {"vehicles": [{"id": "v1"}]}}, "auto.vehicles")


def test_null_counts_as_unanswered():
    assert not I._present({"household": {"annual_spending": None}},
                          "household.annual_spending")


def test_zero_counts_as_present():
    """Nought is an answer. Treating it as missing would be the `null`-is-not-
    zero rule run backwards, and just as wrong."""
    assert I._present({"household": {"annual_spending": 0}},
                      "household.annual_spending")


# ── the worklist ────────────────────────────────────────────────────────────

REQS = {
    "alpha": ["household.members"],
    "beta": ["household.members", "auto.vehicles"],
    "gamma": ["household.members", "auto.vehicles", "debts"],
}


def test_a_skill_with_every_field_is_runnable():
    r = I.assess({"household": {"members": [{"id": "a1"}]}}, REQS)
    assert r.runnable == ["alpha"]
    assert {g.skill for g in r.gaps} == {"beta", "gamma"}


def test_blocking_is_ordered_by_how_many_skills_a_field_holds_up():
    r = I.assess({}, REQS)
    assert [p for p, _ in r.blocking][0] == "household.members"
    assert r.blocking[0][1] == ("alpha", "beta", "gamma")


def test_nearly_there_is_the_shortest_distance_first():
    r = I.assess({"household": {"members": [{"id": "a1"}]}}, REQS)
    near = r.nearly_there
    assert [g.skill for g in near] == ["beta", "gamma"]
    assert near[0].distance == 1


def test_a_skill_three_fields_away_is_not_in_the_next_hour():
    r = I.assess({}, REQS)
    assert "gamma" not in [g.skill for g in r.nearly_there]


def test_totals_add_up():
    r = I.assess({}, REQS)
    assert r.total_skills == len(REQS)
    assert len(r.runnable) + len(r.gaps) == r.total_skills


def test_no_requirements_means_runnable():
    assert I.assess({}, {"delta": []}).runnable == ["delta"]


# ── refusals ────────────────────────────────────────────────────────────────

def test_the_module_never_infers_a_value_from_a_document():
    """The whole safety property, asserted directly: a report built from
    documents alone still has every field missing."""
    docs = [I.classify("geico-auto-2026.pdf"), I.classify("401k-2026.pdf")]
    r = I.assess({}, REQS, docs)
    assert r.runnable == []
    assert len(r.documents) == 2


def test_off_paper_fields_name_the_peak_balance_problem():
    """FBAR turns on the year's peak, not the year-end figure. A December
    statement answers the wrong question, so the intake has to ask for it
    explicitly rather than let a statement look sufficient."""
    text = " ".join(why for _, why in I.OFF_PAPER)
    assert "PEAK" in text or "peak" in text
    assert "year-end" in text
