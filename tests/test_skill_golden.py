"""Golden-output tests: every skill's full report, pinned.

The unit tests check that the arithmetic is right. These check that the
**report does not change without someone deciding it should**. A reworded
finding, a reordered table, a threshold nudged in `lib/` — all of them show up
here as a diff in review, which is exactly where a change to what a household
reads should be noticed.

They are cheap to update and that is deliberate:

    PF_UPDATE_GOLDEN=1 pytest tests/test_skill_golden.py

Regenerate, then **read the diff**. A golden test whose fixtures are refreshed
without reading the diff is worse than no golden test, because it converts a
review signal into a rubber stamp.

`reference-data-refresh` is excluded — it reports on the repository as of
today, so its output legitimately changes with the calendar.
"""

from __future__ import annotations

import os

import pytest

from skill_harness import GOLDEN_DIR, discover, normalise, run_skill

UPDATE = os.environ.get("PF_UPDATE_GOLDEN") == "1"

# Repo-scoped skills report on today's state; pinning them would pin the date.
SKILLS = [s for s in discover() if not s.facts_free]
IDS = [s.name for s in SKILLS]


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_report_matches_the_golden_fixture(skill):
    r = run_skill(skill)
    assert r.ok, f"{skill.name} did not run\n{r.stderr}"

    actual = normalise(r.stdout)
    path = GOLDEN_DIR / f"{skill.name}.md"

    if UPDATE:
        GOLDEN_DIR.mkdir(exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        pytest.skip(f"golden updated: {path.name}")

    assert path.is_file(), (
        f"no golden fixture for {skill.name}. Generate with:\n"
        f"  PF_UPDATE_GOLDEN=1 pytest tests/test_skill_golden.py"
    )
    expected = path.read_text(encoding="utf-8")
    assert actual == expected, (
        f"{skill.name}: report changed.\n"
        "If the change is intended, regenerate with "
        "PF_UPDATE_GOLDEN=1 and read the diff before committing."
    )


def test_every_household_skill_has_a_golden_fixture():
    if UPDATE:
        pytest.skip("regenerating")
    missing = [s.name for s in SKILLS
               if not (GOLDEN_DIR / f"{s.name}.md").is_file()]
    assert not missing, f"missing golden fixtures: {missing}"


def test_no_orphan_golden_fixtures():
    """A fixture left behind after a skill is renamed or removed silently
    stops testing anything."""
    if not GOLDEN_DIR.is_dir():
        pytest.skip("no fixtures yet")
    known = {s.name for s in SKILLS}
    orphans = [p.name for p in GOLDEN_DIR.glob("*.md")
               if p.stem not in known]
    assert not orphans, f"golden fixtures with no skill: {orphans}"


def test_golden_fixtures_contain_no_dates():
    """`normalise` replaces ISO dates before comparison. If a raw date reaches
    a fixture, the normalisation regressed and the suite will start failing on
    an arbitrary day."""
    if not GOLDEN_DIR.is_dir():
        pytest.skip("no fixtures yet")
    import re
    for p in GOLDEN_DIR.glob("*.md"):
        assert not re.search(r"\d{4}-\d{2}-\d{2}", p.read_text(encoding="utf-8")), (
            f"{p.name} contains a raw date — normalisation is not being applied"
        )
