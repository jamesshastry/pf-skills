"""Does the schema, the example, and what the skills actually read agree?

Three artefacts have to stay in step and nothing previously kept them there:

* `SCHEMA.md` — what a user is told to provide
* `inputs/facts.example.yml` — what they are given to copy
* the `requires` on each skill — what is actually enforced

Drift between them is silent and user-facing. A documented field absent from
the example means a new user copies a file that fails; an example field absent
from the schema means nobody knows what it does.
"""

from __future__ import annotations

import pytest

yaml = pytest.importorskip("yaml")

from skill_harness import EXAMPLE_FACTS, discover  # noqa: E402

ROOT = EXAMPLE_FACTS.parents[1]
SCHEMA = (ROOT / "SCHEMA.md").read_text(encoding="utf-8")
EXAMPLE = yaml.safe_load(EXAMPLE_FACTS.read_text(encoding="utf-8"))
SKILLS = discover()
IDS = [s.name for s in SKILLS]


def resolve(data, dotted: str):
    """Resolve a dotted path, treating `x[]` as 'the list x'."""
    cur = data
    for part in dotted.split("."):
        if part.endswith("[]"):
            part = part[:-2]
            if not isinstance(cur, dict) or part not in cur:
                return None
            return cur[part]
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_every_required_path_resolves_in_the_example(skill):
    """The example must satisfy every skill's declared inputs.

    This is the test that would have caught `birth_year` being added to the
    schema and to one member but not the other.
    """
    declared = skill.frontmatter().get("requires", [])
    if isinstance(declared, str) or not declared:
        return
    unresolved = [d for d in declared if resolve(EXAMPLE, d) is None]
    assert not unresolved, (
        f"{skill.name}: {unresolved} declared but absent from "
        "inputs/facts.example.yml"
    )


@pytest.mark.parametrize("skill", SKILLS, ids=IDS)
def test_every_required_top_level_section_is_documented(skill):
    declared = skill.frontmatter().get("requires", [])
    if isinstance(declared, str) or not declared:
        return
    sections = {d.split(".")[0] for d in declared}
    undocumented = [s for s in sections if f"`{s}`" not in SCHEMA]
    assert not undocumented, (
        f"{skill.name} requires {undocumented}, which SCHEMA.md never "
        "documents. A user has no way to know what to provide."
    )


def test_every_example_section_is_documented():
    undocumented = [k for k in EXAMPLE if f"`{k}`" not in SCHEMA]
    assert not undocumented, (
        f"the example ships {undocumented} but SCHEMA.md never documents it"
    )


def test_every_documented_section_appears_in_the_example():
    """A documented section nobody can see an example of is a section nobody
    fills in correctly."""
    import re
    documented = set(re.findall(r"^## `([a-z_]+)`", SCHEMA, re.M))
    missing = sorted(documented - set(EXAMPLE))
    assert not missing, (
        f"SCHEMA.md documents {missing} but the example has no instance"
    )


def test_the_example_declares_the_schema_version_the_library_speaks():
    from pf import facts as F
    assert EXAMPLE["meta"]["schema_version"] == F.SCHEMA_VERSION


def test_the_example_has_a_jurisdiction():
    """Required with no default, per SCHEMA.md."""
    assert EXAMPLE["meta"]["jurisdiction"]["state"]


def test_every_balance_sheet_row_has_a_tier():
    """The single most load-bearing field in the schema."""
    for row in EXAMPLE["household"]["balance_sheet"]:
        assert row.get("tier") in ("liquid", "age_restricted", "illiquid"), row


def test_every_vehicle_declares_its_value_basis():
    for v in EXAMPLE["auto"]["vehicles"]:
        assert v.get("value_basis"), v.get("label")


def test_members_that_need_a_birth_year_have_one():
    """Statutory ages are birth-year banded; deriving them from `age` is off
    by one before a birthday, which is enough to cross an RMD band."""
    for m in EXAMPLE["household"]["members"]:
        if m.get("role") in ("primary", "spouse"):
            assert m.get("birth_year"), f"{m['id']} has no birth_year"
