"""Operational continuity planning with synthetic households only."""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from pf import continuity as C, skill_metrics as M  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def complete_facts() -> dict:
    return {
        "meta": {
            "schema_version": 1,
            "as_of": "2026-08-30",
            "currency": "USD",
            "jurisdiction": {"country": "US", "state": "WA"},
        },
        "household": {
            "members": [
                {
                    "id": "adult-1",
                    "role": "primary",
                    "age": 43,
                    "income_annual": 120_000,
                    "employer": "Example Works",
                },
                {
                    "id": "adult-2",
                    "role": "spouse",
                    "age": 42,
                    "income_annual": 40_000,
                    "us_status": "citizen",
                },
                {"id": "child-1", "role": "dependent", "age": 9},
            ],
            "balance_sheet": [
                {
                    "id": "cash-1",
                    "name": "Household cash",
                    "value": 45_000,
                    "tier": "liquid",
                    "liquidity_class": "cash_equivalent",
                    "beneficiary_applicable": False,
                    "titled_to": "joint",
                },
                {
                    "id": "retirement-1",
                    "name": "Workplace retirement plan",
                    "value": 300_000,
                    "tier": "age_restricted",
                    "liquidity_class": "restricted",
                    "beneficiaries": [
                        {
                            "member_id": "adult-2",
                            "relationship": "spouse",
                            "share": 100,
                            "type": "primary",
                        },
                        {
                            "relationship": "trust",
                            "share": 100,
                            "type": "contingent",
                        },
                    ],
                },
            ],
        },
        "insurance": {
            "life": [
                {
                    "id": "term-1",
                    "label": "Term life policy",
                    "insured": "adult-1",
                    "type": "term",
                    "death_benefit": 500_000,
                    "premium_annual": 500,
                    "employer_provided": False,
                    "beneficiaries": [
                        {
                            "member_id": "adult-2",
                            "relationship": "spouse",
                            "share": 100,
                            "type": "primary",
                        },
                        {
                            "relationship": "trust",
                            "share": 100,
                            "type": "contingent",
                        },
                    ],
                },
            ],
        },
        "debts": [],
        "estate": {
            "documents": [
                {"type": "will", "exists": True, "last_reviewed": "2026-08-01"},
                {
                    "type": "financial_poa",
                    "exists": True,
                    "last_reviewed": "2026-08-01",
                },
                {
                    "type": "healthcare_poa",
                    "exists": True,
                    "last_reviewed": "2026-08-01",
                },
                {
                    "type": "advance_directive",
                    "exists": True,
                    "last_reviewed": "2026-08-01",
                },
                {
                    "type": "revocable_trust",
                    "exists": True,
                    "last_reviewed": "2026-08-01",
                    "funded": True,
                },
            ],
            "digital": {
                "password_manager": True,
                "emergency_access_configured": True,
                "account_inventory": True,
                "two_factor_recovery_documented": True,
            },
        },
        "continuity": {
            "intended_reader_id": "adult-2",
            "intended_reader_knows_location": True,
            "authorized_helper_contact_id": "helper",
            "plan_last_reviewed": "2026-08-01",
            "offline_plan_copy_location": "Printed continuity binder",
            "document_package_location": "Sealed document packet",
            "tax_records_location": "Tax index in the document packet",
            "account_inventory_location": "Account index in the packet",
            "recovery_package_location": "Sealed recovery packet",
            "recovery_process_tested": True,
            "essential_obligations_reviewed": True,
            "notification_contacts_reviewed": True,
            "contacts": [
                {
                    "id": "helper",
                    "role": "trusted_helper",
                    "label": "Trusted family helper",
                    "contact_via": "Contact card in the document packet",
                    "confirmed": True,
                    "authority_scope_recorded": True,
                },
                {
                    "id": "benefits",
                    "role": "employer_benefits",
                    "label": "Employer benefits desk",
                    "contact_via": "Employer card in the document packet",
                    "confirmed": True,
                },
                {
                    "id": "healthcare-agent",
                    "role": "healthcare_agent",
                    "label": "Healthcare agent",
                    "contact_via": "Healthcare card in the document packet",
                    "confirmed": True,
                    "authority_scope_recorded": True,
                },
                {
                    "id": "claims",
                    "role": "insurance_claims",
                    "label": "Insurance claims desk",
                    "contact_via": "Insurance card in the document packet",
                    "confirmed": True,
                },
                {
                    "id": "institutions",
                    "role": "financial_institution",
                    "label": "Institution directory",
                    "contact_via": "Account index in the document packet",
                    "confirmed": True,
                },
                {
                    "id": "counsel",
                    "role": "estate_attorney",
                    "label": "Estate counsel",
                    "contact_via": "Professional card in the document packet",
                    "confirmed": True,
                },
                {
                    "id": "tax",
                    "role": "tax_professional",
                    "label": "Tax professional",
                    "contact_via": "Professional card in the document packet",
                    "confirmed": True,
                },
            ],
            "essential_obligations": [
                {
                    "id": "housing",
                    "label": "Housing payment",
                    "category": "housing",
                    "cadence": "monthly",
                    "autopay_status": True,
                    "continuation_instruction": (
                        "Keep active and verify against the bill inventory"
                    ),
                },
            ],
            "immediate_duties": [
                {
                    "id": "dependent-care",
                    "label": "Confirm dependent care",
                    "category": "dependent_care",
                    "applies_to": "both",
                    "instruction": "Use the dependent-care page in the packet",
                    "confirmed": True,
                },
            ],
            "review_triggers": [
                "A household or fiduciary change",
                "A new or closed account, policy, debt, or employer",
                "A failed recovery-path test",
            ],
        },
    }


def run_with_facts(
    data: dict,
    tmp_path: Path,
    *extra: str,
) -> subprocess.CompletedProcess:
    source = tmp_path / "facts.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "skills/continuity-plan/run.py"),
            "--facts",
            str(source),
            *extra,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_complete_plan_is_ready_and_contains_both_event_paths(tmp_path):
    plan = C.build_plan(complete_facts())

    assert plan.readiness == C.READY
    assert plan.findings == []
    assert {item.path for item in plan.actions} == {C.DEATH, C.INCAPACITY}
    assert any(
        item.action == "Contact the recorded healthcare agent"
        for item in plan.actions
        if item.path == C.INCAPACITY
    )

    result = run_with_facts(complete_facts(), tmp_path)
    assert result.returncode == 0, result.stderr
    assert "If the plan author dies" in result.stdout
    assert "If the plan author is incapacitated" in result.stdout
    assert "Operational readiness: ✅ READY" in result.stdout


def test_sparse_plan_lists_critical_missing_facts_without_crashing(tmp_path):
    data = {
        "meta": {
            "schema_version": 1,
            "as_of": "2026-08-30",
            "currency": "USD",
        },
        "household": {
            "members": [
                {"id": "adult-1", "role": "primary", "income_annual": None},
                {"id": "adult-2", "role": "spouse", "income_annual": None},
            ],
        },
    }

    plan = C.build_plan(data)
    assert plan.readiness == C.BLOCKED
    assert plan.critical_gaps

    result = run_with_facts(data, tmp_path)
    assert result.returncode == 0, result.stderr
    assert "NEEDS COMPLETION" in result.stdout
    assert "Traceback" not in result.stderr


def test_noncritical_missing_fact_yields_incomplete_not_blocked():
    data = complete_facts()
    del data["continuity"]["tax_records_location"]

    plan = C.build_plan(data)

    assert plan.readiness == C.INCOMPLETE
    assert not plan.critical_gaps
    assert any(item.key == "tax_records-location" for item in plan.findings)


def test_unknowns_remain_unknown_instead_of_becoming_false_or_clear():
    data = complete_facts()
    data["continuity"]["contacts"][0]["confirmed"] = None
    data["estate"]["digital"]["account_inventory"] = None
    next(row for row in data["estate"]["documents"] if row["type"] == "financial_poa")[
        "exists"
    ] = None
    del data["household"]["balance_sheet"][1]["beneficiaries"]

    plan = C.build_plan(data)

    assert plan.readiness == C.BLOCKED
    keys = {item.key for item in plan.findings}
    assert "authorized-helper-confirmation" in keys
    assert "digital-account-inventory" in keys
    assert "document-financial_poa" in keys
    assert any("not recorded" in item.recorded_route for item in plan.transfers)


def test_printable_output_suppresses_credentials_and_long_identifiers(tmp_path):
    data = complete_facts()
    contact_number = "".join(("1234", "5678", "9012", "3456"))
    account_number = "".join(("9988", "7766", "5544"))
    continuity = data["continuity"]
    continuity["password"] = "EXAMPLE-SECRET"
    continuity["offline_plan_copy_location"] = "password=OPEN-SESAME"
    continuity["contacts"][0]["contact_via"] = contact_number
    continuity["contacts"][0]["recovery_code"] = "RECOVERY-SECRET"
    data["household"]["balance_sheet"][0]["name"] = "Account " + account_number
    data["household"]["balance_sheet"][0]["account_number"] = account_number

    result = run_with_facts(data, tmp_path)

    assert result.returncode == 0, result.stderr
    for secret in (
        "EXAMPLE-SECRET",
        "OPEN-SESAME",
        contact_number,
        "RECOVERY-SECRET",
        account_number,
    ):
        assert secret not in result.stdout
    assert "NEEDS COMPLETION" in result.stdout


def test_action_order_is_safety_then_cash_flow_then_notifications_then_defer():
    plan = C.build_plan(complete_facts())
    death = [item for item in plan.actions if item.path == C.DEATH]
    ordering = [
        (C.PHASE_ORDER[item.phase], C.CATEGORY_ORDER[item.category]) for item in death
    ]

    assert ordering == sorted(ordering)
    assert death[0].category == "life_safety"
    assert death[-1].phase == C.DEFER


def test_transfer_rows_state_recorded_facts_not_legal_outcomes():
    plan = C.build_plan(complete_facts())
    by_name = {item.subject: item for item in plan.transfers}

    retirement = by_name["Workplace retirement plan"]
    assert "title recorded" not in retirement.recorded_route
    assert "primary → member adult-2" in retirement.recorded_route
    assert "No issue found" in retirement.review_status

    cash = by_name["Household cash"]
    assert "title recorded as joint" in cash.recorded_route
    assert "not applicable" in cash.review_status


def test_non_us_household_does_not_inherit_the_us_qdot_check():
    data = complete_facts()
    data["meta"]["jurisdiction"]["country"] = "CA"
    data["household"]["members"][1]["us_status"] = "nonresident"

    plan = C.build_plan(data)

    assert all(item.subject != "qdot" for item in plan.document_audit.findings)


def test_shared_domain_functions_are_reused(monkeypatch):
    called = set()

    def wrap(owner, name):
        original = getattr(owner, name)

        def traced(*args, **kwargs):
            called.add(name)
            return original(*args, **kwargs)

        monkeypatch.setattr(owner, name, traced)

    for owner, name in (
        (C.E, "audit_documents"),
        (C.E, "audit_digital"),
        (C.E, "audit_beneficiaries"),
        (C.F, "reserve_assets"),
        (C.F, "household_income"),
        (C.L, "assess"),
        (C.D, "parse"),
    ):
        wrap(owner, name)

    C.build_plan(complete_facts())

    assert called == {
        "audit_documents",
        "audit_digital",
        "audit_beneficiaries",
        "reserve_assets",
        "household_income",
        "assess",
        "parse",
    }


def test_structured_metrics_contain_only_stable_readiness_state(tmp_path):
    data = complete_facts()
    metrics = M.emit("continuity-plan", data)
    by_id = {metric.metric_id: metric for metric in metrics}

    assert by_id["continuity.critical_gaps"].value == 0
    assert by_id["continuity.last_review_age_days"].value == 29

    target = tmp_path / "continuity.json"
    result = run_with_facts(data, tmp_path, "--structured-output", str(target))
    assert result.returncode == 0, result.stderr
    payload = target.read_text(encoding="utf-8")
    assert "Trusted family helper" not in payload
    assert "Printed continuity binder" not in payload
    assert {row["metric_id"] for row in json.loads(payload)["metrics"]} == {
        "continuity.critical_gaps",
        "continuity.last_review_age_days",
    }


def test_plan_is_deterministic_and_does_not_mutate_facts():
    data = complete_facts()
    original = deepcopy(data)

    first = C.build_plan(data)
    second = C.build_plan(data)

    assert first == second
    assert data == original


def test_future_review_date_and_duplicate_ids_are_rejected():
    future = complete_facts()
    future["continuity"]["plan_last_reviewed"] = "2027-01-01"
    with pytest.raises(C.ContinuityError, match="future"):
        C.build_plan(future)

    duplicate = complete_facts()
    duplicate["continuity"]["contacts"].append(
        deepcopy(duplicate["continuity"]["contacts"][0])
    )
    with pytest.raises(C.ContinuityError, match="duplicate"):
        C.build_plan(duplicate)
