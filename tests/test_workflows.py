"""Declared cross-skill workflows stay valid and ordered."""

from pathlib import Path

from pf import workflows as W


ROOT = Path(__file__).resolve().parents[1]


def skill_ids() -> set[str]:
    return {
        path.name for path in (ROOT / "skills").iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    }


def test_every_workflow_step_names_an_existing_skill_once():
    assert W.validate(skill_ids()) == []


def test_property_evaluation_orders_evidence_before_the_offer_and_checks_after():
    workflow = W.PROPERTY_EVALUATION
    positions = {skill: index for index, step in enumerate(workflow.steps)
                 for skill in step.skills}
    assert positions["housing-affordability"] < positions["home-offer-strategy"]
    assert positions["rent-vs-buy"] < positions["home-offer-strategy"]
    assert positions["ca-sfh-disclosure-review"] < positions["home-offer-strategy"]
    assert positions["ca-condo-hoa-disclosure-review"] < positions["home-offer-strategy"]
    assert positions["home-offer-strategy"] < positions["conflict-check"]
    assert positions["home-offer-strategy"] < positions["financial-scenario-planner"]


def test_reverse_lookup_finds_the_property_workflow():
    workflows = W.containing("home-offer-strategy")
    assert [workflow.id for workflow in workflows] == ["property-evaluation"]
