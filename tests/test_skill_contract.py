"""Structural contract every skill must satisfy.

None of this exercises arithmetic. It checks that a skill *is* a skill: that it
has the two files, that its frontmatter is usable by an agent deciding whether
to invoke it, and — the one that catches real drift — that what the `SKILL.md`
claims to need matches what the runner actually enforces.
"""

from __future__ import annotations

import re

import pytest

from skill_harness import EXAMPLE_FACTS, discover

SKILLS = discover()
IDS = [s.name for s in SKILLS]

#: Long enough to actually describe when to invoke the skill. Short
#: descriptions are the main cause of a skill never being selected.
MIN_DESCRIPTION = 120
MAX_DESCRIPTION = 1024


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_skill_has_both_required_files(skill):
    assert skill.skill_md.is_file(), f"{skill.name}: no SKILL.md"
    assert skill.runner.is_file(), f"{skill.name}: no run.py"


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_frontmatter_name_matches_the_directory(skill):
    """An agent invokes by name; a mismatch means the skill is unreachable."""
    assert skill.frontmatter().get("name") == skill.name


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_description_is_long_enough_to_route_on(skill):
    d = skill.frontmatter().get("description", "")
    assert isinstance(d, str)
    assert MIN_DESCRIPTION <= len(d) <= MAX_DESCRIPTION, (
        f"{skill.name}: description is {len(d)} chars. It has to tell an "
        "agent *when* to reach for this skill, not just what it is."
    )


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_description_says_when_to_use_it(skill):
    d = skill.frontmatter().get("description", "").lower()
    assert re.search(r"\buse (when|for|at|after|before)\b", d), (
        f"{skill.name}: description never says when to use it."
    )


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_household_skills_say_they_read_a_local_facts_file(skill):
    if skill.facts_free:
        return
    d = skill.frontmatter().get("description", "").lower()
    assert "facts file" in d, (
        f"{skill.name}: description should say it reads a local facts file, "
        "so nobody assumes it fetches anything."
    )


def test_skill_names_are_unique():
    names = [s.name for s in SKILLS]
    assert len(names) == len(set(names))


# ── the drift check ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_declared_requires_matches_what_the_runner_enforces(skill):
    """The one that catches real drift.

    `SKILL.md` frontmatter advertises the inputs. `run.py` has the REQUIRED
    list that actually stops execution. Nothing keeps them in step, and a
    skill that advertises a field it never checks will happily produce a
    report built on a silently missing input.
    """
    declared = skill.frontmatter().get("requires", [])
    if isinstance(declared, str):
        declared = []
    enforced = skill.runner_required()

    if skill.facts_free:
        assert not declared, f"{skill.name} takes no facts; requires should be empty"
        return

    assert enforced is not None, f"{skill.name}: run.py has no REQUIRED list"

    # Declared may be coarser than enforced (`auto.vehicles` vs
    # `auto.vehicles[].value`), but every declared path must be a prefix of
    # something enforced, and every enforced path must be covered by a
    # declared one. Neither list may contain a path the other knows nothing
    # about.
    def covered(path, others):
        return any(o == path or o.startswith(path + ".")
                   or o.startswith(path + "[") or path.startswith(o + ".")
                   or path.startswith(o + "[") for o in others)

    orphan_declared = [d for d in declared if not covered(d, enforced)]
    orphan_enforced = [e for e in enforced if not covered(e, declared)]

    assert not orphan_declared, (
        f"{skill.name}: SKILL.md declares {orphan_declared} but run.py never "
        "checks it. Either enforce it or stop advertising it."
    )
    assert not orphan_enforced, (
        f"{skill.name}: run.py enforces {orphan_enforced} but SKILL.md never "
        "declares it. A caller cannot know it is needed."
    )


# ── runner shape ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_runner_declares_its_dependencies_inline(skill):
    """PEP 723 header, so `uv run` works with nothing preinstalled."""
    assert skill.has_pep723_header(), f"{skill.name}: run.py has no PEP 723 header"


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_household_runners_use_the_shared_cli_harness(skill):
    """One preamble, one stop-behaviour.

    Every runner must parse --facts, load, check required paths and stop
    cleanly. Hand-rolling that per skill is how the stop-behaviour drifts —
    one skill listing missing fields, another crashing with a traceback.
    """
    if skill.facts_free:
        return
    src = skill.runner.read_text(encoding="utf-8")
    assert "cli.run(" in src, (
        f"{skill.name}: run.py does not use cli.run(). Migrate it so the "
        "missing-facts path is identical across skills."
    )


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_facts_argument_has_no_default(skill):
    if skill.facts_free:
        return
    src = skill.runner.read_text(encoding="utf-8")
    assert "add_argument" not in src or "required=True" in src, (
        f"{skill.name}: --facts must be required, never defaulted to a path."
    )


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_runner_points_at_the_module_holding_its_thresholds(skill):
    """Every report has to say where its numbers came from."""
    if skill.facts_free:
        return
    src = skill.runner.read_text(encoding="utf-8")
    assert "lib/pf/" in src, (
        f"{skill.name}: run.py never names the module its thresholds live in."
    )


# ── body ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_skill_body_carries_the_not_advice_line(skill):
    body = skill.body().lower()
    assert "not financial" in body or "not tax advice" in body, (
        f"{skill.name}: SKILL.md is missing the not-advice line."
    )


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_skill_body_has_no_unfilled_placeholders(skill):
    body = skill.body()
    for marker in ("TODO", "FIXME", "XXX", "TBD", "Lorem ipsum"):
        assert marker not in body, f"{skill.name}: SKILL.md contains {marker}"


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_skill_body_contains_no_figures_from_a_real_household(skill):
    """Skills hold procedures and thresholds. A raw dollar figure in prose is
    either a threshold (fine, and it lives in lib) or a leak."""
    body = skill.body()
    # Amounts with thousands separators are the shape a real balance takes.
    suspicious = re.findall(r"\$\d{1,3}(?:,\d{3}){2,}", body)
    assert not suspicious, (
        f"{skill.name}: SKILL.md contains large specific amounts {suspicious}. "
        "Thresholds belong in lib/pf with a name; anything else is a leak."
    )


def test_every_skill_is_listed_in_the_readme():
    readme = (EXAMPLE_FACTS.parents[1] / "README.md").read_text(encoding="utf-8")
    missing = [s.name for s in SKILLS if f"`{s.name}`" not in readme]
    assert not missing, f"README does not list: {missing}"


def test_every_skill_is_listed_in_the_roadmap():
    roadmap = (EXAMPLE_FACTS.parents[1] / "ROADMAP.md").read_text(encoding="utf-8")
    missing = [s.name for s in SKILLS if f"`{s.name}`" not in roadmap]
    assert not missing, f"ROADMAP does not list: {missing}"
