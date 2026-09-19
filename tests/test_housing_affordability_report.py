"""Report contract for housing affordability. Synthetic fixture only."""

import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import cli, facts as F  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "skills" / "housing-affordability" / "run.py"
SPEC = importlib.util.spec_from_file_location("housing_affordability_run", RUN)
run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run)


def fixture():
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load((ROOT / "inputs/facts.example.yml").read_text())


def render(data):
    writer = cli.Writer()
    run.build(data, writer)
    return writer.render()


def test_report_labels_every_distinct_limit_and_the_binding_constraint():
    text = render(fixture())
    for label in ("Target", "Current-income capacity", "Stress-tested ceiling",
                  "Lender maximum", "Liquidity/down-payment limit",
                  "Binding constraint"):
        assert label.lower() in text.lower()


def test_report_keeps_affordability_and_economic_cost_separate():
    text = render(fixture())
    assert "Affordability includes mortgage principal" in text
    assert "rent-vs-buy" in text
    assert "economic cost" in text


def test_report_shows_sources_uses_and_two_transition_phases():
    text = render(fixture())
    assert "Gross sale proceeds" in text
    assert "Post-close financial assets and cash" in text
    assert "Tenant phase" in text
    assert "Owner-occupancy phase" in text
    assert "current rental tax benefit is zero" in text


def test_reconciliation_error_is_a_top_level_blocker():
    data = fixture()
    data["cash_flow"]["scenarios"][0]["gross_income_annual"] += 25_000
    text = render(data)
    assert "## BLOCKED" in text
    assert "No affordability conclusion" in text


def test_rent_vs_buy_report_disclaims_affordability():
    text = (ROOT / "skills" / "rent-vs-buy" / "run.py").read_text()
    assert "determine affordability" in text


def test_example_fixture_is_strong_and_fully_synthetic():
    data = fixture()
    scenarios = data["cash_flow"]["scenarios"]
    assert {s["kind"] for s in scenarios} == {"current", "conservative"}
    assert data["housing"]["transition"]["tenant_months"] > 12
    brokerage = next(
        row for row in data["household"]["balance_sheet"]
        if row["name"] == "brokerage")
    assert any(lot["value"] > lot["cost_basis"] for lot in brokerage["tax_lots"])
    assert any(lot["value"] < lot["cost_basis"] for lot in brokerage["tax_lots"])
    assert brokerage["margin_debt"] > 0
    assert F.reserve_assets(data).included < F.liquid(data)
