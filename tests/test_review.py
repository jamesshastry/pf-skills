"""Whole-household review: the ranking rule, the gating, and the coverage.

The ranking tests pin the decision this skill owns — order — with synthetic
actions. The coverage test pins the promise: every household skill has an
adapter, so the review cannot silently stop covering the library as it grows.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from pf import intake as I, review as R  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SELF = "household-review"


def action(skill="s", tier=R.TIER_OPTIMISE, impact=None, expiry=None,
           headline="h"):
    return R.Action(skill=skill, headline=headline, tier=tier,
                    impact_annual=impact, days_to_expiry=expiry)


# ── the ranking ───────────────────────────────────────────────────────────


def test_closing_outranks_uncovered_outranks_drags_outranks_optimise():
    ranked = R.prioritize([
        action("d", R.TIER_OPTIMISE),
        action("c", R.TIER_DRAG, impact=10_000),
        action("b", R.TIER_UNCOVERED),
        action("a", R.TIER_CLOSING, expiry=30),
    ])
    assert [a.skill for a in ranked] == ["a", "b", "c", "d"]


def test_sooner_expiry_ranks_first_undated_last():
    ranked = R.prioritize([
        action("late", R.TIER_CLOSING, expiry=170),
        action("undated", R.TIER_CLOSING),
        action("passed", R.TIER_CLOSING, expiry=-12),
        action("soon", R.TIER_CLOSING, expiry=4),
    ])
    assert [a.skill for a in ranked] == ["passed", "soon", "late", "undated"]


def test_bigger_priced_drag_ranks_first():
    ranked = R.prioritize([
        action("small", R.TIER_DRAG, impact=200),
        action("big", R.TIER_DRAG, impact=9_000),
        action("unpriced", R.TIER_DRAG),
    ])
    assert [a.skill for a in ranked] == ["big", "small", "unpriced"]


def test_ties_break_by_skill_then_headline_deterministically():
    first = R.prioritize([action("b", headline="y"), action("a", headline="z"),
                          action("a", headline="a")])
    second = R.prioritize([action("a", headline="a"), action("b", headline="y"),
                           action("a", headline="z")])
    assert [(a.skill, a.headline) for a in first] == [
        ("a", "a"), ("a", "z"), ("b", "y")]
    assert first == second


def test_unknown_tier_is_rejected_not_ranked():
    with pytest.raises(AssertionError):
        R.act("s", "h", "eventually")


# ── the gating ────────────────────────────────────────────────────────────


def example_facts() -> dict:
    return yaml.safe_load(
        (ROOT / "inputs" / "facts.example.yml").read_text(encoding="utf-8"))


def test_blocked_skills_name_what_is_missing():
    facts = {"meta": {"schema_version": 1},
             "household": {"members": [{"id": "a1", "role": "primary"}]}}
    rep = R.collect(facts, ROOT / "skills")
    assert rep.blocked, "a nearly empty file should block almost everything"
    assert all(b.missing for b in rep.blocked)


def test_collect_is_deterministic():
    once = R.collect(example_facts(), ROOT / "skills")
    twice = R.collect(example_facts(), ROOT / "skills")
    assert [(a.skill, a.headline) for a in once.ranked] == [
        (a.skill, a.headline) for a in twice.ranked]
    assert once.blocked == twice.blocked


def test_an_adapter_error_is_recorded_not_fatal():
    R.ADAPTERS["__probe__"] = lambda data: 1 / 0
    try:
        reqs = I.skill_requirements(ROOT / "skills")
        assert "__probe__" not in reqs  # self-made adapters never run
    finally:
        del R.ADAPTERS["__probe__"]
    R.ADAPTERS.setdefault("cash-yield-review", None)
    facts = example_facts()
    rep = R.collect(facts, ROOT / "skills")
    assert isinstance(rep, R.HouseholdReview)


# ── the promise ───────────────────────────────────────────────────────────


def test_every_household_skill_has_an_adapter():
    """The mechanism that keeps this list whole-library.

    Adding a skill without an adapter must fail here rather than silently
    narrow the review. The adapter mirrors the skill runner's core call —
    see the contract in `lib/pf/review.py`.
    """
    reqs = I.skill_requirements(ROOT / "skills",
                                skip=I.FACTS_FREE | {SELF})
    missing = sorted(s for s in reqs if s not in R.ADAPTERS)
    assert not missing, (
        f"skills with no review adapter: {missing}. Add one function plus "
        "one ADAPTERS entry in lib/pf/review.py."
    )


def test_no_adapter_points_at_a_removed_skill():
    reqs = I.skill_requirements(ROOT / "skills",
                                skip=I.FACTS_FREE | {SELF})
    orphans = sorted(s for s in R.ADAPTERS if s not in reqs)
    assert not orphans, f"adapters with no skill: {orphans}"


def test_collect_runs_the_whole_library_without_error_on_the_example():
    """The example fixture runs every household skill, so collection over it
    executes every adapter. An error here is a broken adapter, recorded —
    and this test refuses to let that be silent."""
    rep = R.collect(example_facts(), ROOT / "skills")
    assert not rep.errors, (
        f"adapters that raised: {[(e.skill, e.message) for e in rep.errors]}")
    assert not rep.unwired
    assert rep.ranked, "the example is built to have findings"
    assert rep.checked, "the example is built to clear some skills too"


def test_representative_skills_emit_structured_metrics_without_scraping_reports():
    facts = example_facts()
    rep = R.collect(facts, ROOT / "skills")
    by_skill = {outcome.skill: outcome for outcome in rep.structured}
    expected = {
        "emergency-fund-sizing", "employer-concentration-risk",
        "retirement-readiness", "housing-affordability", "education-funding",
        "survivor-needs", "life-insurance-review",
        "disability-insurance-review",
    }
    assert expected <= {skill for skill, outcome in by_skill.items()
                        if outcome.metrics}
    results = R.structured_results(rep, facts)
    assert any(result.metrics for result in results)
    assert all(result.findings for result in results)
