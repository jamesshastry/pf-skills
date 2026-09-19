"""Structural privacy checks for private input and history paths."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
INPUT_CATEGORIES = (
    "banking", "business", "cross-border", "debts", "education", "estate",
    "healthcare", "income", "insurance", "investments", "life-events",
    "property", "retirement", "tax",
)
OUTPUT_CATEGORIES = ("history", "reports", "scenarios", "structured")


def check_ignored(path: str) -> bool:
    result = subprocess.run(
        ("git", "-C", str(ROOT), "check-ignore", "--no-index", "--quiet", path),
        check=False,
    )
    return result.returncode == 0


@pytest.mark.parametrize("category", INPUT_CATEGORIES)
def test_private_input_contents_are_ignored_but_scaffold_is_committed(category):
    assert (ROOT / "inputs" / category / ".gitignore").exists()
    assert check_ignored(f"inputs/{category}/private-statement.pdf")
    assert not check_ignored(f"inputs/{category}/.gitignore")


@pytest.mark.parametrize("category", OUTPUT_CATEGORIES)
def test_private_output_contents_are_ignored_but_scaffold_is_committed(category):
    assert (ROOT / "outputs" / category / ".gitignore").exists()
    assert check_ignored(f"outputs/{category}/private-report.md")
    assert not check_ignored(f"outputs/{category}/.gitignore")


def test_history_contents_are_ignored_but_scaffold_is_committed():
    assert check_ignored("history/private-snapshot.yml")
    assert not check_ignored("history/.gitkeep")


def test_commit_hook_covers_inputs_outputs_and_history():
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "inputs/|outputs/|history/" in config
    assert "prompt|brief" in config
    assert "inputs/[^/]+/\\.gitignore" in config
    assert "outputs/[^/]+/\\.gitignore" in config
    assert "history/\\.gitkeep" in config


def test_private_task_prompts_are_ignored():
    assert check_ignored("private-household-prompt.md")
    assert check_ignored("prompts/private-household-prompt.md")
