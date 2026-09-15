"""Foreign reporting thresholds — review finding A2."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import reporting as R  # noqa: E402


def bank(name, mx, country="IN"):
    return {"name": name, "kind": "bank", "country": country,
            "max_value_during_year": mx}


def forms(a):
    return {f.form: f for f in a.findings}


# ── FBAR is aggregate, and it is the maximum ────────────────────────────────


def test_fbar_aggregates_across_accounts():
    """Five accounts of $3,000 cross a $10,000 threshold. Per-account
    thinking is the standard error."""
    a = R.audit([bank(f"a{i}", 3_000) for i in range(5)])
    assert a.known_max == 15_000
    assert forms(a)["FinCEN 114 (FBAR)"].severity == "blocker"


def test_a_single_small_account_is_below_threshold():
    a = R.audit([bank("a", 4_000)])
    assert forms(a)["FinCEN 114 (FBAR)"].severity == "ok"


def test_being_below_still_warns_that_the_test_is_the_peak():
    a = R.audit([bank("a", 4_000)])
    assert "peak" in forms(a)["FinCEN 114 (FBAR)"].detail


def test_an_unknown_maximum_makes_the_answer_undeterminable_not_zero():
    """null means nobody looked. Treating it as zero would produce a
    confident 'below threshold' that is very likely wrong."""
    a = R.audit([bank("a", None)])
    f = forms(a)["FinCEN 114 (FBAR)"]
    assert f.severity == "blocker"
    assert "cannot be determined" in f.detail
    assert not a.determinable


def test_a_partially_known_set_is_still_undeterminable():
    a = R.audit([bank("known", 4_000), bank("unknown", None)])
    assert a.unknown_accounts == 1
    assert forms(a)["FinCEN 114 (FBAR)"].severity == "blocker"


def test_crossing_the_threshold_raises_prior_years():
    a = R.audit([bank("a", 50_000)])
    assert "prior years it was required then too" in forms(a)["FinCEN 114 (FBAR)"].detail


# ── FATCA is a different filing with different thresholds ───────────────────


def test_fatca_thresholds_are_higher_than_fbar():
    a = R.audit([bank("a", 60_000)], filing_status="married_joint")
    assert forms(a)["FinCEN 114 (FBAR)"].severity == "blocker"
    assert forms(a)["Form 8938 (FATCA)"].severity == "ok"


def test_fatca_triggers_above_the_any_time_threshold():
    a = R.audit([bank("a", 200_000)], filing_status="married_joint")
    assert forms(a)["Form 8938 (FATCA)"].severity == "blocker"


def test_single_filers_have_lower_thresholds():
    a = R.audit([bank("a", 90_000)], filing_status="single")
    assert forms(a)["Form 8938 (FATCA)"].severity == "blocker"


def test_living_abroad_raises_the_thresholds_substantially():
    here = R.audit([bank("a", 200_000)], tax_home_abroad=False)
    there = R.audit([bank("a", 200_000)], tax_home_abroad=True)
    assert forms(here)["Form 8938 (FATCA)"].severity == "blocker"
    assert forms(there)["Form 8938 (FATCA)"].severity == "ok"


def test_the_two_filings_are_described_as_separate():
    a = R.audit([bank("a", 60_000)])
    assert "separately from the tax return" in forms(a)["FinCEN 114 (FBAR)"].detail


# ── PFIC ────────────────────────────────────────────────────────────────────


def test_a_foreign_mutual_fund_is_a_pfic_by_default():
    a = R.audit([{"name": "fund", "kind": "foreign_mutual_fund",
                  "max_value_during_year": 5_000}])
    f = forms(a)["Form 8621 (PFIC)"]
    assert f.severity == "blocker"
    assert "per fund" in f.detail


def test_every_pfic_kind_is_caught():
    for kind in R.PFIC_KINDS:
        a = R.audit([{"name": "x", "kind": kind, "max_value_during_year": 1_000}])
        assert "Form 8621 (PFIC)" in forms(a), kind


def test_a_plain_bank_account_is_not_a_pfic():
    a = R.audit([bank("a", 50_000)])
    assert "Form 8621 (PFIC)" not in forms(a)


def test_the_de_minimis_waiver_is_described_with_both_conditions():
    a = R.audit([{"name": "f", "kind": "foreign_etf",
                  "max_value_during_year": 1_000}])
    d = forms(a)["Form 8621 (PFIC)"].detail
    assert "excess distribution" in d and "no election is in effect" in d


def test_pfic_points_at_the_divest_decision():
    a = R.audit([{"name": "f", "kind": "unit_trust",
                  "max_value_during_year": 1_000}])
    assert "pfic-divest-or-comply" in forms(a)["Form 8621 (PFIC)"].detail


# ── foreign gifts ───────────────────────────────────────────────────────────


def test_a_large_foreign_gift_triggers_3520():
    a = R.audit([bank("a", 1_000)], foreign_gifts_received=250_000)
    f = forms(a)["Form 3520"]
    assert f.severity == "blocker"
    assert "No tax is due" in f.detail


def test_a_small_foreign_gift_does_not():
    a = R.audit([bank("a", 1_000)], foreign_gifts_received=5_000)
    assert "Form 3520" not in forms(a)


def test_unrecorded_gifts_are_raised_as_a_note():
    a = R.audit([bank("a", 1_000)])
    assert forms(a)["Form 3520"].severity == "note"


# ── the always-on caveats ───────────────────────────────────────────────────


def test_signature_authority_is_always_raised():
    a = R.audit([bank("a", 1_000)])
    assert any("Signature authority counts" in f.detail for f in a.findings)


def test_no_accounts_recorded_asks_for_an_explicit_empty_list():
    a = R.audit([])
    assert any("record `foreign_accounts: []`" in f.detail for f in a.findings)
    assert any("signature authority" in f.detail.lower() for f in a.findings)


def test_an_explicit_empty_list_is_still_reported_as_unchecked():
    """Empty and absent look the same to the audit, deliberately: both mean
    nobody has demonstrated the answer."""
    assert R.audit([]).account_count == 0
