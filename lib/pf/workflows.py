"""Declarative cross-skill workflows.

Conflict edges live in ``pf.conflicts``.  This module owns the different
question of order: which specialist reports form one decision workflow, why
each stage exists, and which alternatives are conditional.  It executes no
skill and makes no financial conclusion.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowStep:
    stage: str
    skills: tuple[str, ...]
    purpose: str
    condition: str = "always"


@dataclass(frozen=True)
class Workflow:
    id: str
    title: str
    steps: tuple[WorkflowStep, ...]

    @property
    def skill_ids(self) -> tuple[str, ...]:
        return tuple(skill for step in self.steps for skill in step.skills)


PROPERTY_EVALUATION = Workflow(
    id="property-evaluation",
    title="Property evaluation and offer",
    steps=(
        WorkflowStep(
            stage="Feasibility",
            skills=("housing-affordability", "rent-vs-buy"),
            purpose="Set the financial ceiling and compare ownership cost.",
        ),
        WorkflowStep(
            stage="Property diligence",
            skills=("ca-sfh-disclosure-review", "ca-condo-hoa-disclosure-review"),
            purpose="Review condition, title, insurability, and association evidence.",
            condition="Run the one applicable California review; use local professional review elsewhere.",
        ),
        WorkflowStep(
            stage="Comparable research, price, and bid",
            skills=("home-offer-strategy",),
            purpose="Research and normalize closed sales, then set opening and walk-away prices.",
        ),
        WorkflowStep(
            stage="Whole-plan check",
            skills=("conflict-check", "financial-scenario-planner"),
            purpose="Resolve competing uses of cash and test the balance-sheet path.",
            condition="Run before committing material cash or debt.",
        ),
    ),
)

WORKFLOWS = {PROPERTY_EVALUATION.id: PROPERTY_EVALUATION}


def containing(skill_id: str) -> tuple[Workflow, ...]:
    """Return each declared workflow containing ``skill_id``."""
    return tuple(
        workflow for workflow in WORKFLOWS.values()
        if skill_id in workflow.skill_ids
    )


def validate(known_skill_ids: set[str]) -> list[str]:
    """Return registry defects without reading or executing any skill."""
    defects: list[str] = []
    for workflow in WORKFLOWS.values():
        if not workflow.steps:
            defects.append(f"{workflow.id}: has no steps")
            continue
        seen: set[str] = set()
        for step in workflow.steps:
            if not step.skills:
                defects.append(f"{workflow.id}/{step.stage}: has no skills")
            for skill in step.skills:
                if skill not in known_skill_ids:
                    defects.append(f"{workflow.id}: unknown skill {skill}")
                if skill in seen:
                    defects.append(f"{workflow.id}: duplicate skill {skill}")
                seen.add(skill)
    return defects
