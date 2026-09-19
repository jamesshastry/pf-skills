"""The new cross-cutting runners render their shared structured results."""
from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "inputs/facts.example.yml"


def run(name: str) -> str:
    process = subprocess.run(
        [sys.executable, str(ROOT / "skills" / name / "run.py"),
         "--facts", str(FACTS)],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert process.returncode == 0, process.stderr
    return process.stdout


def test_history_report_separates_clocks_and_retains_gaps():
    report = run("financial-history-review")
    assert "three separate clocks" in report
    assert "partial snapshot cannot support a household total" in report
    assert "methodology" in report
    assert "Alder Brokerage" not in report  # labels never become join keys


def test_scenario_report_shows_intraperiod_failure_and_bridge():
    before = FACTS.read_bytes()
    report = run("financial-scenario-planner")
    assert FACTS.read_bytes() == before
    assert "Min cash" in report
    assert "Event bridge" in report
    assert "Composition residual" in report
    assert "No ranking" in report


def test_job_loss_report_keeps_two_runways_and_correlated_bundle():
    report = run("job-loss-stress-test")
    assert "Current spending" in report
    assert "Essential spending" in report
    assert "Correlated event bundle" in report
    assert "fails before terminal recovery" in report


def test_windfall_report_blocks_or_labels_the_live_pause():
    report = run("windfall-deployment-planner")
    assert "Decision pause" in report
    assert "preliminary" in report
    assert "not cash" in report


def test_adapted_skill_can_write_structured_metrics_explicitly(tmp_path):
    target = tmp_path / "emergency.json"
    process = subprocess.run(
        [sys.executable,
         str(ROOT / "skills/emergency-fund-sizing/run.py"),
         "--facts", str(FACTS), "--structured-output", str(target)],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert process.returncode == 0, process.stderr
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["skill_id"] == "emergency-fund-sizing"
    assert {row["metric_id"] for row in payload["metrics"]} >= {
        "emergency_fund.months_held", "emergency_fund.target"}


def test_structured_output_refuses_overwrite(tmp_path):
    target = tmp_path / "exists.json"
    target.write_text("keep", encoding="utf-8")
    process = subprocess.run(
        [sys.executable,
         str(ROOT / "skills/emergency-fund-sizing/run.py"),
         "--facts", str(FACTS), "--structured-output", str(target)],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert process.returncode == 2
    assert target.read_text(encoding="utf-8") == "keep"


def test_history_capture_and_current_model_rerun_are_explicit(tmp_path):
    captured = tmp_path / "captured.yml"
    analyzed = tmp_path / "analysis.yml"
    capture = subprocess.run(
        [sys.executable, str(ROOT / "scripts/history.py"), "capture",
         "--facts", str(FACTS), "--output", str(captured),
         "--snapshot-id", "captured-example",
         "--effective-date", "2026-08-30",
         "--observed-at", "2026-09-02"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert capture.returncode == 0, capture.stderr
    rerun = subprocess.run(
        [sys.executable, str(ROOT / "scripts/history.py"), "rerun",
         "--snapshot", str(captured), "--output", str(analyzed),
         "--snapshot-id", "analysis-example",
         "--calculated-at", "2026-09-03"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert rerun.returncode == 0, rerun.stderr
    assert "kind: analysis" in analyzed.read_text(encoding="utf-8")
