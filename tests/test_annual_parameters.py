"""Year-sensitive private assumptions carry auditable, non-value metadata."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

from pf import annual_parameters as A


TODAY = dt.date(2026, 9, 21)
RUNNER = (Path(__file__).resolve().parents[1] / "skills" /
          "reference-data-refresh" / "run.py")
WORKFLOW = (Path(__file__).resolve().parents[1] / ".github" / "workflows" /
            "reference-data-refresh.yml")


def facts(*, metadata: dict | None = None) -> dict:
    assumptions = {
        "federal_brackets": {
            "single": [
                {"rate": 0.10, "up_to": 10_000},
                {"rate": 0.20, "up_to": None},
            ],
        },
    }
    if metadata is not None:
        assumptions["annual_parameter_metadata"] = metadata
    return {
        "meta": {"as_of": "2026-09-21"},
        "contributions": {"year": 2026},
        "tax_planning": {"current_year": {"tax_year": 2027}},
        "assumptions": assumptions,
    }


def federal(audits: tuple[A.GroupAudit, ...]) -> A.GroupAudit:
    return next(audit for audit in audits if audit.group.key == "federal_tax")


def test_tax_year_prefers_explicit_tax_plan_then_contributions_then_as_of():
    data = facts()
    assert A.infer_tax_year(data) == 2027
    del data["tax_planning"]
    assert A.infer_tax_year(data) == 2026
    del data["contributions"]
    assert A.infer_tax_year(data) == 2026


def test_scheduled_check_switches_to_next_year_in_november():
    assert A.scheduled_target_year(dt.date(2026, 10, 31)) == 2026
    assert A.scheduled_target_year(dt.date(2026, 11, 1)) == 2027
    assert A.scheduled_target_year(dt.date(2026, 12, 31)) == 2027
    assert A.scheduled_target_year(dt.date(2027, 1, 1)) == 2027


def test_active_group_without_metadata_is_not_ready():
    audit = federal(A.audit(facts(), target_year=2027, today=TODAY))
    assert audit.active
    assert not audit.ready
    assert audit.issues == ("metadata is missing",)


def test_official_group_requires_year_date_and_exact_source_url():
    data = facts(metadata={
        "federal_tax": {
            "tax_year": 2026,
            "verified_on": "2027-01-01",
            "sources": ["IRS revenue procedure"],
        },
    })
    audit = federal(A.audit(data, target_year=2027, today=TODAY))
    assert "tax_year is 2026; expected 2027" in audit.issues
    assert "verified_on is in the future" in audit.issues
    assert "official sources must be recorded as exact URLs" in audit.issues


def test_complete_metadata_marks_the_active_group_ready():
    data = facts(metadata={
        "federal_tax": {
            "tax_year": 2027,
            "verified_on": "2026-09-20",
            "sources": ["https://www.irs.gov/example-authority"],
        },
    })
    audit = federal(A.audit(data, target_year=2027, today=TODAY))
    assert audit.ready
    assert audit.source_count == 1
    assert audit.issues == ()


def test_inactive_groups_do_not_demand_irrelevant_metadata():
    audits = A.audit(facts(), target_year=2027, today=TODAY)
    healthcare = next(
        audit for audit in audits if audit.group.key == "healthcare")
    assert not healthcare.active
    assert not healthcare.ready
    assert healthcare.issues == ()


def test_cli_can_check_a_future_year_before_january():
    completed = subprocess.run(
        (sys.executable, str(RUNNER), "--annual-only", "--target-year", "2099"),
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 1
    assert "Annual readiness target: **2099**" in completed.stdout
    assert "2099 is missing" in completed.stdout
    assert "statutory retirement ages" not in completed.stdout


def test_private_facts_audit_does_not_print_parameter_values(tmp_path):
    secret_value = 987_654_321
    data = facts(metadata={
        "federal_tax": {
            "tax_year": 2027,
            "verified_on": "2026-09-20",
            "sources": ["https://www.irs.gov/example-authority"],
        },
    })
    data["assumptions"]["federal_brackets"]["single"][0]["up_to"] = secret_value
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    completed = subprocess.run(
        (sys.executable, str(RUNNER), "--annual-only", "--target-year", "2027",
         "--facts", str(path)),
        capture_output=True, text=True, check=False,
    )
    assert "Private annual-parameter metadata" in completed.stdout
    assert str(secret_value) not in completed.stdout


def test_scheduled_workflow_is_read_only_and_never_receives_private_facts():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "contents: read" in workflow
    assert "--annual-only --strict" in workflow
    assert "--scheduled" in workflow
    assert "inputs/facts" not in workflow
    assert "git commit" not in workflow
    assert "git push" not in workflow
