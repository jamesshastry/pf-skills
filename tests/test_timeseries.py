"""The history protocol refuses misleading joins and preserves corrections."""
from __future__ import annotations

import copy
import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from pf import timeseries as T  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "tests/fixtures/history/2025-12-31.yml",
    ROOT / "tests/fixtures/history/2025-12-31-analysis.yml",
    ROOT / "tests/fixtures/history/2025-12-31-restatement.yml",
    ROOT / "tests/fixtures/history/2026-03-31.yml",
    ROOT / "tests/fixtures/history/2026-03-31-analysis.yml",
    ROOT / "tests/fixtures/history/2026-06-30.yml",
    ROOT / "tests/fixtures/history/2026-06-30-analysis.yml",
    ROOT / "tests/fixtures/history/2026-09-30.yml",
    ROOT / "tests/fixtures/history/2026-09-30-analysis.yml",
]


def observed(**changes) -> T.MetricObservation:
    values = dict(
        metric_id="household.net_worth", effective_date=dt.date(2026, 1, 1),
        value=100.0, unit="currency", currency="USD", basis="nominal",
        scenario="observed", source="balance_sheet", clock="observed",
        status="measured", observed_at=dt.date(2026, 1, 2),
    )
    values.update(changes)
    return T.MetricObservation(**values)


def analysis(**changes) -> T.MetricObservation:
    values = dict(
        metric_id="retirement.target", effective_date=dt.date(2026, 1, 1),
        value=100.0, unit="currency", currency="USD", basis="real",
        scenario="current", source="retirement-readiness", clock="analysis",
        status="derived", calculated_at=dt.date(2026, 1, 3),
        model_version="v1", inputs_fingerprint="same",
    )
    values.update(changes)
    return T.MetricObservation(**values)


def test_three_clocks_cannot_be_mixed_accidentally():
    projected = analysis(clock="projection", status="projected",
                         scenario="stress")
    with pytest.raises(T.HistoryError, match="clock"):
        T.compare_points(analysis(), projected)
    with pytest.raises(T.HistoryError, match="scenario=observed"):
        observed(scenario="current")


def test_stable_entity_id_survives_an_account_rename():
    first = observed(metric_id="household.asset_balance",
                     entity_id="acct-1", display_label="Old label")
    second = observed(metric_id="household.asset_balance",
                      entity_id="acct-1", display_label="New institution",
                      effective_date=dt.date(2026, 2, 1), value=125)
    series = T.MetricSeries(first.series_key, (first, second))
    assert len(series.observations) == 2
    assert T.compare_points(first, second).absolute_change == 25


def test_unknown_is_not_zero_or_silently_carried_forward():
    missing = observed(value=None, status="unknown", data_quality="unknown",
                       unknown_reason="statement missing")
    with pytest.raises(T.HistoryError, match="unknown observations"):
        T.compare_points(missing, observed(effective_date=dt.date(2026, 2, 1)))


def test_restatement_retains_the_original_and_changes_the_effective_point():
    history = T.load_history([FILES[0], FILES[2]])
    current = history.series("household.net_worth", clock="observed",
                             scenario="observed").observations
    assert current[0].value == 305_000
    all_rows = history.metrics(include_original_restatements=True)
    assert any(row.value == 300_000 for row in all_rows)


def test_nominal_and_real_or_different_currency_are_rejected():
    with pytest.raises(T.HistoryError, match="basis"):
        T.compare_points(analysis(basis="real"),
                         analysis(basis="nominal",
                                  calculated_at=dt.date(2026, 2, 1)))
    with pytest.raises(T.HistoryError, match="currency"):
        T.compare_points(observed(currency="USD"),
                         observed(currency="CAD",
                                  effective_date=dt.date(2026, 2, 1)))


def test_scenarios_at_the_same_date_are_distinct_series():
    current = analysis(scenario="current")
    conservative = analysis(scenario="conservative")
    with pytest.raises(T.HistoryError, match="scenario"):
        T.compare_points(current, conservative)


def test_model_only_change_is_methodology_not_household_progress():
    first = analysis(model_version="v1", value=100,
                     calculated_at=dt.date(2026, 1, 3))
    second = analysis(model_version="v2", value=120,
                      calculated_at=dt.date(2026, 2, 3))
    change = T.compare_points(first, second)
    assert change.change_driver == "model"
    assert "same inputs" in change.warnings[0]


def test_partial_snapshot_cannot_create_a_confident_total():
    snapshot = T.load_snapshot(FILES[3])
    total = next(x for x in snapshot.observations
                 if x.metric_id == "household.net_worth")
    assert total.value is None
    assert total.data_quality == "unknown"


def test_fixture_has_four_dates_rename_addition_fx_guard_and_finding_close():
    history = T.load_history(FILES)
    assert len({s.effective_date for s in history.snapshots}) == 4
    brokerage = history.series("household.asset_balance", clock="observed",
                               scenario="observed", entity_id="acct-brokerage")
    assert [x.display_label for x in brokerage.observations][:2] == [
        "Alder Brokerage", "Meridian Investments"]
    bond = history.series("household.asset_balance", clock="observed",
                          scenario="observed", entity_id="acct-bond")
    assert bond.observations[0].effective_date == dt.date(2026, 6, 30)
    with pytest.raises(T.HistoryError, match="incompatible"):
        history.series("household.asset_balance", clock="observed",
                       scenario="observed", entity_id="acct-fx")
    transitions = T.finding_transitions(history.findings())
    assert any(old and old.state == "worsened" and new.state == "closed"
               for old, new in transitions)


def test_capture_is_pure_and_refuses_overwrite(tmp_path):
    facts = {
        "meta": {"schema_version": 1, "as_of": "2026-01-01",
                 "currency": "USD"},
        "household": {"members": [], "balance_sheet": [
            {"id": "cash-1", "name": "Cash", "value": 100,
             "tier": "liquid", "liquidity_class": "cash_equivalent"}],
            "annual_spending": 120},
        "debts": [],
        "retirement": {"annual_savings": 10},
    }
    original = copy.deepcopy(facts)
    snapshot = T.capture_snapshot(
        facts, snapshot_id="capture-1", effective_date=dt.date(2026, 1, 1),
        observed_at=dt.date(2026, 1, 2))
    assert facts == original
    target = tmp_path / "snapshot.json"
    T.save_snapshot(snapshot, target)
    with pytest.raises(T.HistoryError, match="refusing to overwrite"):
        T.save_snapshot(snapshot, target)


def test_capture_does_not_turn_an_unknown_balance_into_zero():
    facts = {
        "meta": {"schema_version": 1, "as_of": "2026-01-01",
                 "currency": "USD"},
        "household": {"members": [], "balance_sheet": [
            {"id": "cash-1", "name": "Cash", "value": None,
             "tier": "liquid", "liquidity_class": "cash_equivalent"}],
            "annual_spending": 120},
        "debts": [],
        "retirement": {"annual_savings": 10},
    }
    snapshot = T.capture_snapshot(
        facts, snapshot_id="capture-unknown",
        effective_date=dt.date(2026, 1, 1),
        observed_at=dt.date(2026, 1, 2))
    by_id = {row.metric_id: row for row in snapshot.observations}
    assert by_id["household.net_worth"].value is None
    assert by_id["household.cash_reserve"].value is None


def test_summary_and_report_source_share_the_same_series_values():
    summary = T.summarize_history(T.load_history(FILES),
                                  metric_ids={"household.net_worth"})
    change = summary.changes[0]
    assert change.start.value == 305_000
    assert change.end.value == 370_000
    assert change.absolute_change == 65_000
