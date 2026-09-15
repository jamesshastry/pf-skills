"""What every skill must actually do when run.

Three promises the project makes, none of which was previously tested:

1. Given complete facts, a skill produces a report and exits 0.
2. Given incomplete facts, it **stops cleanly** — names what is missing, exits
   1, and never crashes or invents a default.
3. Given the same facts twice, it produces the same output.

These run the real runners as subprocesses, so they cover the argument
parsing, the import path surgery, and the rendering — the parts unit tests on
`pf.*` cannot reach.
"""

from __future__ import annotations

import re

import pytest

from skill_harness import (EXAMPLE_FACTS, discover, normalise, run_skill,
                           write_bad_version, write_minimal)

SKILLS = discover()
IDS = [s.name for s in SKILLS]
HOUSEHOLD = [s for s in SKILLS if not s.facts_free]
HOUSEHOLD_IDS = [s.name for s in HOUSEHOLD]


# ── the happy path ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_skill_runs_against_the_example_fixture(skill):
    r = run_skill(skill)
    assert r.ok, f"{skill.name} exited {r.returncode}\n{r.stderr}"


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_output_is_a_markdown_report_with_a_title(skill):
    r = run_skill(skill)
    assert r.stdout.startswith("# "), f"{skill.name}: output has no H1"
    assert len(r.stdout) > 400, f"{skill.name}: output is suspiciously short"


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_output_carries_the_not_advice_disclaimer(skill):
    r = run_skill(skill)
    if skill.facts_free:
        return
    assert "Not financial" in r.stdout, f"{skill.name}: report has no disclaimer"


#: Sentinels that mean a value never got formatted. Matched on word
#: boundaries — an early version checked substrings and flagged every report,
#: because "nan" lives inside "financial".
PLACEHOLDER_PATTERNS = (
    (r"\{[A-Za-z_][A-Za-z0-9_.\[\]]*\}", "an unsubstituted format placeholder"),
    # Only in a value position. Sentence-initial "None of that..." is
    # ordinary English and an earlier version flagged it.
    (r"[|:=($\[]\s*None\b|\bNone\s*[|)\]]", "a None in a value position"),
    (r"\bnan\b", "a NaN reaching the reader"),
    (r"(?<![A-Za-z])inf(?![A-Za-z])", "an infinity reaching the reader"),
    (r"\$0\.00\b", "a zero-valued money field that should have been omitted"),
)


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_output_has_no_unrendered_placeholders(skill):
    """A format string that never got its value, or a sentinel leaking into
    prose. These are the failures a reader would take at face value."""
    r = run_skill(skill)
    for pattern, why in PLACEHOLDER_PATTERNS:
        m = re.search(pattern, r.stdout)
        assert m is None, (
            f"{skill.name}: report contains {m.group(0)!r} — {why}"
        )


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_nothing_is_written_to_stderr_on_success(skill):
    r = run_skill(skill)
    assert r.stderr == "", f"{skill.name}: unexpected stderr\n{r.stderr}"


# ── stopping cleanly ────────────────────────────────────────────────────────


@pytest.mark.parametrize("skill", HOUSEHOLD, ids=HOUSEHOLD_IDS)
def test_missing_facts_stops_cleanly_rather_than_crashing(skill, tmp_path):
    """The core promise: refuse rather than guess.

    A skill that crashes here is a skill that would have crashed on a
    half-filled facts file, which is the state every new user starts in.
    """
    r = run_skill(skill, write_minimal(tmp_path))
    assert r.returncode == 1, (
        f"{skill.name}: expected a clean stop (1), got {r.returncode}.\n"
        f"{r.stderr}"
    )
    assert "Traceback" not in r.stderr


@pytest.mark.parametrize("skill", HOUSEHOLD, ids=HOUSEHOLD_IDS)
def test_the_stop_names_what_is_missing(skill, tmp_path):
    r = run_skill(skill, write_minimal(tmp_path))
    assert "missing required facts" in r.stdout.lower()
    assert "- `" in r.stdout, f"{skill.name}: stop did not list any field"


@pytest.mark.parametrize("skill", HOUSEHOLD, ids=HOUSEHOLD_IDS)
def test_the_stop_lists_each_field_once(skill, tmp_path):
    """Several `things[].field` requirements share one missing head; listing
    it three times reads like three separate problems."""
    r = run_skill(skill, write_minimal(tmp_path))
    listed = [ln for ln in r.stdout.splitlines() if ln.startswith("- `")]
    assert len(listed) == len(set(listed)), f"{skill.name}: duplicate fields"


@pytest.mark.parametrize("skill", HOUSEHOLD, ids=HOUSEHOLD_IDS)
def test_a_wrong_schema_version_is_fatal_and_explained(skill, tmp_path):
    r = run_skill(skill, write_bad_version(tmp_path))
    assert r.returncode == 2
    assert "schema_version" in r.stderr
    assert "Traceback" not in r.stderr


@pytest.mark.parametrize("skill", HOUSEHOLD, ids=HOUSEHOLD_IDS)
def test_a_missing_facts_file_fails_without_a_traceback(skill, tmp_path):
    r = run_skill(skill, tmp_path / "does-not-exist.json")
    assert r.returncode != 0
    # A bare FileNotFoundError traceback is a poor experience but not a
    # correctness bug; what matters is that it does not exit 0.
    assert not r.stdout.startswith("# " + skill.name)


# ── determinism ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("skill", HOUSEHOLD, ids=HOUSEHOLD_IDS)
def test_output_is_deterministic(skill):
    """Household reports must derive dates from `meta.as_of`, never from the
    clock. A report that changes overnight cannot be diffed or reviewed."""
    first = run_skill(skill).stdout
    second = run_skill(skill).stdout
    assert first == second


@pytest.mark.parametrize("skill", HOUSEHOLD, ids=HOUSEHOLD_IDS)
def test_household_reports_do_not_read_the_system_clock(skill):
    """`datetime.today()`/`now()` in a household runner means the report
    changes with the date rather than with the facts."""
    src = skill.runner.read_text(encoding="utf-8")
    for bad in ("date.today()", "datetime.now()", "datetime.today()"):
        assert bad not in src, (
            f"{skill.name}: runner reads the clock ({bad}). Dates must come "
            "from meta.as_of so the report is reproducible."
        )


# ── the example fixture itself ──────────────────────────────────────────────


def test_the_example_fixture_satisfies_every_household_skill():
    """The shipped example must exercise everything, or a new user copying it
    hits a wall of missing fields on their first run."""
    failed = [s.name for s in HOUSEHOLD if not run_skill(s).ok]
    assert not failed, f"example fixture does not satisfy: {failed}"


def test_the_example_fixture_is_the_only_one_committed():
    """inputs/ is gitignored except the example; a stray real facts file here
    would be the whole privacy failure."""
    stray = [p.name for p in (EXAMPLE_FACTS.parent).iterdir()
             if p.is_file() and p.name not in {"facts.example.yml", "README.md"}
             and not p.name.startswith(".")]
    assert not stray, f"unexpected files in inputs/: {stray}"
