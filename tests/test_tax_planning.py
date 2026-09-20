"""Tax planning from filed-return history and current household facts."""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from pf import skill_metrics as M, tax_planning as T  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def facts() -> dict:
    return {
        "meta": {
            "schema_version": 1,
            "as_of": "2026-09-19",
            "currency": "USD",
            "jurisdiction": {"country": "US", "state": "CA"},
        },
        "household": {
            "members": [
                {"id": "a1", "role": "primary", "age": 45},
            ],
            "balance_sheet": [
                {
                    "id": "brokerage",
                    "account_type": "taxable",
                    "wash_sale_policy_applied": True,
                    "tax_lots": [
                        {
                            "ticker": "LOSS",
                            "value": 12_000,
                            "cost_basis": 15_000,
                            "holding_period": "long_term",
                        },
                        {
                            "ticker": "GAIN",
                            "value": 20_000,
                            "cost_basis": 8_000,
                            "holding_period": "long_term",
                        },
                    ],
                },
            ],
        },
        "contributions": {
            "year": 2026,
            "employer_plan": {
                "employee_pre_tax": 10_000,
                "employee_roth": 5_000,
            },
            "hsa": {
                "coverage": "family",
                "eligible": True,
                "contribution": 2_000,
            },
        },
        "assumptions": {
            "marginal_tax_rate": 0.30,
            "state_tax_rate": 0.05,
            "ltcg_rate": 0.15,
            "niit_rate": 0.038,
            "standard_deduction": 30_000,
            "other_itemized_deductions": 10_000,
        },
        "charity": {
            "annual_gift": 9_000,
            "candidate_holdings": [
                {
                    "name": "Appreciated fund",
                    "value": 20_000,
                    "basis": 5_000,
                    "held_days": 900,
                },
            ],
        },
        "retirement": {"planned_retirement_age": 60},
        "tax_planning": {
            "returns": [
                {
                    "tax_year": 2023,
                    "filing_status": "married_joint",
                    "state": "CA",
                    "adjusted_gross_income": 150_000,
                    "taxable_income": 120_000,
                    "federal_total_tax": 24_000,
                    "state_income_tax": 6_000,
                    "payments": 31_000,
                },
                {
                    "tax_year": 2024,
                    "filing_status": "married_joint",
                    "state": "CA",
                    "adjusted_gross_income": 180_000,
                    "taxable_income": 150_000,
                    "federal_total_tax": 32_000,
                    "state_income_tax": 8_000,
                    "payments": 38_000,
                },
                {
                    "tax_year": 2025,
                    "filing_status": "married_joint",
                    "state": "CA",
                    "adjusted_gross_income": 200_000,
                    "taxable_income": 170_000,
                    "federal_total_tax": 40_000,
                    "state_income_tax": 10_000,
                    "payments": 45_000,
                },
            ],
            "current_year": {
                "tax_year": 2026,
                "filing_status": "married_joint",
                "state": "CA",
                "projected_adjusted_gross_income": 160_000,
                "projected_taxable_income": 130_000,
                "projected_federal_total_tax": 30_000,
                "projected_state_income_tax": 7_000,
                "projected_payments": 33_000,
                "retirement_contribution_state_deductible": True,
                "remaining_roth_deferrals": 5_000,
                "hsa_state_deductible": True,
                "loss_harvest_usable_amount": 2_500,
                "loss_harvest_marginal_rate": 0.20,
                "target_ordinary_bracket_top": 160_000,
                "expected_future_combined_marginal_rate": 0.40,
                "roth_conversion_state_taxable": True,
            },
        },
    }


def opportunities(plan: T.TaxPlan) -> dict[str, T.TaxOpportunity]:
    return {item.key: item for item in plan.opportunities}


def test_history_is_sorted_and_rates_are_derived_from_tax_not_payments():
    data = facts()
    data["tax_planning"]["returns"].reverse()
    plan = T.plan_from_facts(data)

    assert [row.tax_year for row in plan.history.years] == [2023, 2024, 2025]
    assert plan.history.years[0].effective_rate == pytest.approx(0.20)
    assert plan.history.years[0].payment_gap == -1_000
    assert plan.history.years[-1].payment_gap == 5_000


def test_payment_timing_does_not_change_tax_reduction_candidates():
    low_payments = facts()
    high_payments = deepcopy(low_payments)
    low_payments["tax_planning"]["current_year"]["projected_payments"] = 0
    high_payments["tax_planning"]["current_year"]["projected_payments"] = 100_000

    low = T.plan_from_facts(low_payments)
    high = T.plan_from_facts(high_payments)

    assert low.current.payment_gap != high.current.payment_gap
    assert low.opportunities == high.opportunities


def test_filing_status_or_state_changes_are_disclosed():
    data = facts()
    data["tax_planning"]["returns"][0]["filing_status"] = "single"
    data["tax_planning"]["current_year"]["state"] = "OR"
    findings = T.plan_from_facts(data).findings

    assert any("within the return history" in item for item in findings)
    assert any("differs from the latest" in item for item in findings)


def test_us_strategies_are_not_applied_to_another_country():
    data = facts()
    data["meta"]["jurisdiction"]["country"] = "CA"
    plan = T.plan_from_facts(data)

    assert plan.opportunities == []
    assert any("U.S.-specific" in item for item in plan.findings)


def test_current_fact_opportunities_are_quantified_independently():
    found = opportunities(T.plan_from_facts(facts()))

    assert found["pre-tax-deferral"].amount == 9_500
    assert found["pre-tax-deferral"].current_tax_savings == 3_325
    assert found["roth-to-pretax"].current_tax_savings == 1_750
    assert found["hsa-contribution"].amount == 6_750
    assert found["hsa-contribution"].current_tax_savings == pytest.approx(2_362.5)
    assert found["tax-loss-harvest"].amount == 3_000
    assert found["tax-loss-harvest"].current_tax_savings == 500
    assert found["appreciated-charity"].amount == 9_000
    assert found["appreciated-charity"].current_tax_savings == pytest.approx(
        1_269)
    assert found["charitable-bunching"].current_tax_savings is None
    assert found["charitable-bunching"].future_tax_savings == 7_500


def test_opportunities_are_ranked_without_adding_overlapping_savings():
    plan = T.plan_from_facts(facts())
    assert plan.opportunities[0].key == "pre-tax-deferral"
    assert not hasattr(plan, "total_tax_savings")


def test_roth_conversion_is_a_current_cost_and_separate_future_estimate():
    data = facts()
    data["household"]["members"][0]["age"] = 61
    current = data["tax_planning"]["current_year"]
    current["projected_adjusted_gross_income"] = 140_000
    current["projected_taxable_income"] = 130_000
    current["target_ordinary_bracket_top"] = 160_000

    conversion = opportunities(T.plan_from_facts(data))["roth-conversion-window"]

    assert conversion.amount == 30_000
    assert conversion.current_tax_savings == -10_500
    assert conversion.future_tax_savings == pytest.approx(1_500)
    assert any("ACA" in item and "IRMAA" in item
               for item in conversion.tradeoffs)


def test_roth_conversion_is_not_suggested_while_still_working():
    assert "roth-conversion-window" not in opportunities(
        T.plan_from_facts(facts()))


def test_past_roth_deferrals_are_not_claimed_as_available_tax_savings():
    data = facts()
    del data["tax_planning"]["current_year"]["remaining_roth_deferrals"]
    choice = opportunities(T.plan_from_facts(data))["roth-to-pretax"]

    assert choice.amount is None
    assert choice.current_tax_savings is None
    assert any("retroactively" in item for item in choice.tradeoffs)


def test_loss_harvesting_is_unpriced_without_return_level_netting_inputs():
    data = facts()
    current = data["tax_planning"]["current_year"]
    del current["loss_harvest_usable_amount"]
    del current["loss_harvest_marginal_rate"]
    data["household"]["balance_sheet"][0]["wash_sale_policy_applied"] = None

    loss = opportunities(T.plan_from_facts(data))["tax-loss-harvest"]

    assert loss.amount == 3_000
    assert loss.current_tax_savings is None
    assert loss.confidence == "conditional"


def test_tax_lot_without_basis_is_excluded_and_named():
    data = facts()
    data["household"]["balance_sheet"][0]["tax_lots"][0]["cost_basis"] = None
    plan = T.plan_from_facts(data)

    assert "tax-loss-harvest" not in opportunities(plan)
    assert any("LOSS lacks value or basis" in item for item in plan.findings)


def test_duplicate_and_overlapping_tax_years_are_refused():
    duplicate = facts()
    duplicate["tax_planning"]["returns"][1]["tax_year"] = 2023
    with pytest.raises(T.TaxPlanningError, match="duplicate"):
        T.plan_from_facts(duplicate)

    overlap = facts()
    overlap["tax_planning"]["current_year"]["tax_year"] = 2025
    with pytest.raises(T.TaxPlanningError, match="must follow"):
        T.plan_from_facts(overlap)


def test_invalid_and_contradictory_tax_figures_are_refused():
    non_finite = facts()
    non_finite["tax_planning"]["returns"][0][
        "adjusted_gross_income"] = float("nan")
    with pytest.raises(T.TaxPlanningError, match="finite"):
        T.plan_from_facts(non_finite)

    negative = facts()
    negative["tax_planning"]["returns"][0]["federal_total_tax"] = -1
    with pytest.raises(T.TaxPlanningError, match="negative"):
        T.plan_from_facts(negative)

    taxable_over_agi = facts()
    taxable_over_agi["tax_planning"]["returns"][0]["taxable_income"] = 160_000
    with pytest.raises(T.TaxPlanningError, match="exceeds AGI"):
        T.plan_from_facts(taxable_over_agi)


def test_invalid_optional_rates_cannot_create_impossible_savings():
    non_finite = facts()
    non_finite["assumptions"]["ltcg_rate"] = float("nan")
    with pytest.raises(T.TaxPlanningError, match="finite"):
        T.plan_from_facts(non_finite)

    stacked = facts()
    stacked["assumptions"]["marginal_tax_rate"] = 0.90
    stacked["assumptions"]["state_tax_rate"] = 0.20
    with pytest.raises(T.TaxPlanningError, match="cannot exceed one"):
        T.plan_from_facts(stacked)


def test_filing_dimensions_must_be_text():
    data = facts()
    data["tax_planning"]["returns"][0]["state"] = ["CA"]
    with pytest.raises(T.TaxPlanningError, match="historical return state"):
        T.plan_from_facts(data)


def test_current_and_contribution_years_must_match():
    data = facts()
    data["contributions"]["year"] = 2025
    with pytest.raises(T.TaxPlanningError, match="contribution year"):
        T.plan_from_facts(data)


def test_one_year_and_history_gaps_are_disclosed_not_interpolated():
    one = facts()
    one["tax_planning"]["returns"] = one["tax_planning"]["returns"][:1]
    assert any("Only one" in item for item in T.plan_from_facts(one).findings)

    gap = facts()
    del gap["tax_planning"]["returns"][1]
    assert any("year gaps" in item for item in T.plan_from_facts(gap).findings)


def test_planning_does_not_mutate_the_facts_mapping():
    data = facts()
    original = deepcopy(data)
    T.plan_from_facts(data)
    assert data == original


def test_tax_planning_emits_comparable_structured_metrics():
    metrics = M.emit("tax-planning", facts())
    by_id = {metric.metric_id: metric for metric in metrics}

    assert by_id["tax.projected_combined_tax"].value == 37_000
    assert by_id["tax.projected_effective_rate"].value == pytest.approx(
        37_000 / 160_000)
    assert by_id["tax.projected_payment_gap"].value == 4_000
    assert by_id["tax.historical_weighted_effective_rate"].scenario == (
        "historical_baseline")


def test_runner_shows_history_tax_moves_and_tradeoffs():
    process = subprocess.run(
        [
            sys.executable,
            str(ROOT / "skills/tax-planning/run.py"),
            "--facts",
            str(ROOT / "inputs/facts.example.yml"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert process.returncode == 0, process.stderr
    assert "Filed-return history" in process.stdout
    assert "Tax-reduction candidates" in process.stdout
    assert "Tradeoffs:" in process.stdout
    assert "Do not add the opportunity figures together" in process.stdout


def test_runner_can_write_tax_metrics_explicitly(tmp_path):
    target = tmp_path / "tax-planning.json"
    process = subprocess.run(
        [
            sys.executable,
            str(ROOT / "skills/tax-planning/run.py"),
            "--facts",
            str(ROOT / "inputs/facts.example.yml"),
            "--structured-output",
            str(target),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert process.returncode == 0, process.stderr
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["skill_id"] == "tax-planning"
    assert {row["metric_id"] for row in payload["metrics"]} == {
        "tax.historical_weighted_effective_rate",
        "tax.projected_combined_tax",
        "tax.projected_effective_rate",
        "tax.projected_payment_gap",
    }


def test_runner_stops_cleanly_when_a_return_field_is_missing(tmp_path):
    data = facts()
    del data["tax_planning"]["returns"][0]["federal_total_tax"]
    source = tmp_path / "incomplete.json"
    source.write_text(json.dumps(data), encoding="utf-8")

    process = subprocess.run(
        [
            sys.executable,
            str(ROOT / "skills/tax-planning/run.py"),
            "--facts",
            str(source),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert process.returncode == 1
    assert "federal_total_tax" in process.stdout
    assert "Traceback" not in process.stderr
