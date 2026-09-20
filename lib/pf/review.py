"""Whole-household review: every skill's check, one ranked worklist.

## The one idea

Fifty-plus skills each end with good advice, and no household does fifty
things at once. Each report is also blind past its own edge — it cannot say
whether its finding matters more than another skill's. The decision this
skill owns is **order**: which findings expire, which losses cannot be
bought back after the fact, which drags are priced in dollars per year, and
what everything else waits behind.

## How it stays honest at whole-library scale

An adapter per skill calls **the same module function the skill's own runner
calls, with the same inputs** — the runner stays the implementation and this
module only re-reads its verdict. A skill whose inputs are missing is
reported as blocked, naming what is missing, never approximated: gating uses
`facts.require`, the same check `cli.run` enforces, so the runnable set here
is the runnable set everywhere by construction rather than by parallel
maintenance.

## Tiers, and why they rank this way

`closing` first: a dated finding that expires — a rider window, a filing
deadline — cannot be repriced later at any price, so it outranks everything
priced. `uncovered` second: protection gaps are losses you cannot self-insure
after the fact, which is what distinguishes them from drags you can stop any
month. `drag` third, ranked by annual dollars. `optimise` last: real, but
neither expiring nor priced.

## What it refuses

It does not re-render any skill's tables, resolve any skill's trade-off, or
run a skill whose inputs are absent. `conflict-check` already names the
contradictions; this module surfaces live ones as actions but does not
re-decide them. Findings that expire carry their dates through untouched.

## Adapter contract (for contributors adding a skill)

Every adapter is `def _<name>(data: dict) -> Outcome` in this file,
registered in `ADAPTERS` under the skill's directory name:

- call the same `lib/pf` function the skill's runner calls, with arguments
  read the same way (`F._dig`, same optional-field guards);
- return `ok(skill, headline)` when there is nothing to do, `act(...)` when
  there is — one `Action` per independently doable thing;
- choose the tier by the ranking above, not by the skill's own emphasis;
- put dollars per year in `impact_annual` wherever the module prices one;
- put `days_to_expiry` on anything dated (pass the runner's own deadline
  through; compute against `F.as_of(data)`, never the clock);
- never read the filesystem, never import a runner, never add a schema
  field to satisfy an adapter.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import facts as F
from . import intake as I
from . import timeseries as T

#: Findings dated within this window outrank everything priced. Mirrors the
#: `urgent` band of `facts.Deadline` (there is no named constant to import):
#: inside six months a deadline stops being a plan and starts being a diary
#: entry, and diary entries are what get missed.
CLOSING_WINDOW_DAYS = 180

#: A dated finding that expires. Rider windows, filing deadlines, election
#: cutoffs — anything that cannot be repriced later at any price.
TIER_CLOSING = "closing"
#: A protection gap: a loss the household cannot self-insure after the fact.
TIER_UNCOVERED = "uncovered"
#: An ongoing drag priced in dollars per year. Ranked by size within the tier.
TIER_DRAG = "drag"
#: Real and actionable, but neither expiring nor priced.
TIER_OPTIMISE = "optimise"

TIERS = (TIER_CLOSING, TIER_UNCOVERED, TIER_DRAG, TIER_OPTIMISE)

#: Rank order. Closing beats uncovered beats priced beats the rest, for the
#: reasons in the module docstring — argue with the order here, not per skill.
TIER_ORDER = {TIER_CLOSING: 0, TIER_UNCOVERED: 1, TIER_DRAG: 2,
              TIER_OPTIMISE: 3}


@dataclass
class Action:
    """One independently doable thing, from whichever skill found it."""
    skill: str
    headline: str
    tier: str
    impact_annual: float | None = None
    days_to_expiry: int | None = None
    irreversible: bool = False
    detail: str = ""
    findings: list[str] = field(default_factory=list)


@dataclass
class Outcome:
    """What one skill's check concluded."""
    skill: str
    status: str  # "ok" | "action"
    headline: str
    actions: list[Action] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    metrics: list[T.MetricObservation] = field(default_factory=list)
    structured_findings: list[T.FindingObservation] = field(default_factory=list)


@dataclass
class Blocked:
    """A skill that cannot run yet, and what it is waiting on."""
    skill: str
    missing: tuple[str, ...] = ()


@dataclass
class ReviewError:
    """An adapter that raised rather than concluded. Recorded, never fatal:
    one skill's edge case must not take down the other fifty-five."""
    skill: str
    message: str


@dataclass
class HouseholdReview:
    ranked: list[Action] = field(default_factory=list)
    checked: list[Outcome] = field(default_factory=list)
    structured: list[Outcome] = field(default_factory=list)
    blocked: list[Blocked] = field(default_factory=list)
    unwired: list[str] = field(default_factory=list)
    errors: list[ReviewError] = field(default_factory=list)
    #: Missing field -> skills it blocks, by blast radius. Counted over this
    #: review's own blocked set (compare `intake.assess`, which counts over
    #: its stricter empty-list-means-absent semantics).
    blocking: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)


def _money(x: float | None) -> str:
    if x is None:
        return "unpriced"
    return f"${x:,.0f}"


def ok(skill: str, headline: str) -> Outcome:
    """No action: the check ran and there is nothing to do."""
    return Outcome(skill=skill, status="ok", headline=headline)


def act(skill: str, headline: str, tier: str, *,
        impact_annual: float | None = None,
        days_to_expiry: int | None = None,
        irreversible: bool = False,
        detail: str = "") -> Outcome:
    """One action, already wrapped as its skill's outcome."""
    assert tier in TIER_ORDER, f"unknown tier {tier!r}"
    return Outcome(
        skill=skill, status="action", headline=headline,
        actions=[Action(skill=skill, headline=headline, tier=tier,
                        impact_annual=impact_annual,
                        days_to_expiry=days_to_expiry,
                        irreversible=irreversible, detail=detail)])


def prioritize(actions: list[Action]) -> list[Action]:
    """The decision this skill owns, as a sort key.

    Tier first, for the reasons above. Within a tier: the sooner it expires
    the higher it ranks (undated last); then the larger the priced impact;
    then the skill name, so the order is total and the output deterministic.
    """
    return sorted(
        actions,
        key=lambda a: (
            TIER_ORDER[a.tier],
            a.days_to_expiry if a.days_to_expiry is not None else float("inf"),
            -(a.impact_annual or 0.0),
            a.skill,
            a.headline,
        ),
    )


def collect(facts: dict, skills_dir: str | Path) -> HouseholdReview:
    """Run every wired skill's check and rank what to fix first.

    Gating uses `facts.require` — the check `cli.run` enforces — so a skill
    runs here exactly when it runs on its own. Anything else (blocked,
    unwired, errored) is reported as such rather than approximated.
    """
    reqs = I.skill_requirements(skills_dir, skip=I.FACTS_FREE | {"household-review"})
    out = HouseholdReview()
    for skill in sorted(reqs):
        missing = F.require(facts, reqs[skill]).missing
        if missing:
            out.blocked.append(Blocked(skill=skill, missing=tuple(missing)))
            continue
        fn = ADAPTERS.get(skill)
        if fn is None:
            out.unwired.append(skill)
            continue
        try:
            outcome = fn(facts)
            from . import skill_metrics as _skill_metrics  # noqa: PLC0415
            outcome.metrics.extend(_skill_metrics.emit(skill, facts))
            calculated = F._as_date(F._dig(facts, "meta.analysis_at")) or F.as_of(facts)
            effective = F.as_of(facts)
            if calculated is not None and effective is not None:
                is_open = outcome.status == "action"
                outcome.structured_findings.append(T.FindingObservation(
                    finding_id="skill." + skill.replace("-", ".") + ".verdict",
                    effective_date=effective,
                    source_skill=skill,
                    state="open" if is_open else "closed",
                    severity=(outcome.actions[0].tier if outcome.actions else "ok"),
                    text=outcome.headline,
                    calculated_at=calculated,
                    model_version=T.ANALYSIS_MODEL_VERSION,
                    transition_reason=(None if is_open else
                                       "current model reports no action"),
                    change_driver="unknown",
                    inputs_fingerprint=T.analysis_input_fingerprint(facts),
                ))
        except Exception as exc:  # noqa: BLE001 — recorded, see ReviewError
            out.errors.append(ReviewError(skill=skill, message=str(exc)))
            continue
        if outcome.status == "action":
            out.ranked.extend(outcome.actions)
        else:
            out.checked.append(outcome)
        out.structured.append(outcome)

    out.ranked = prioritize(out.ranked)
    out.checked.sort(key=lambda o: o.skill)
    out.blocked.sort(key=lambda b: b.skill)

    counts: dict[str, list[str]] = {}
    for b in out.blocked:
        for p in b.missing:
            counts.setdefault(p, []).append(b.skill)
    out.blocking = sorted(
        ((p, tuple(sorted(s))) for p, s in counts.items()),
        key=lambda kv: (-len(kv[1]), kv[0]),
    )
    return out


def structured_results(review: HouseholdReview, facts: dict) -> list[T.StructuredResult]:
    """Expose review outcomes without scraping their Markdown renderers."""
    calculated = F._as_date(F._dig(facts, "meta.analysis_at")) or F.as_of(facts)
    if calculated is None:
        raise ValueError("meta.as_of or meta.analysis_at is required")
    by_skill: dict[str, Outcome] = {
        outcome.skill: outcome for outcome in review.structured
    }
    return [T.StructuredResult(
        skill_id=outcome.skill,
        headline=outcome.headline,
        calculated_at=calculated,
        model_version=T.ANALYSIS_MODEL_VERSION,
        metrics=list(outcome.metrics),
        findings=list(outcome.structured_findings),
        dependencies=(),
        assumptions=(),
    ) for outcome in sorted(by_skill.values(), key=lambda o: o.skill)
    if outcome.metrics or outcome.structured_findings]


# ── adapters ──────────────────────────────────────────────────────────────
#
# One per household skill, each mirroring its runner's core call. New skills
# add one function here plus one ADAPTERS entry; `test_review.py` fails
# otherwise, which is the mechanism that keeps this list whole-library.

from . import auto as _auto  # noqa: E402
from . import cash as _cash  # noqa: E402
from . import charity as _charity  # noqa: E402
from . import concentration as _conc  # noqa: E402
from . import conflicts as _conflicts  # noqa: E402
from . import continuity as _continuity  # noqa: E402
from . import contributions as _contrib  # noqa: E402
from . import crossborder as _xb  # noqa: E402
from . import debt as _debt  # noqa: E402
from . import depreciation as _depr  # noqa: E402
from . import disability as _disab  # noqa: E402
from . import disclosure as _disclosure  # noqa: E402
from . import education as _edu  # noqa: E402
from . import entity as _ent  # noqa: E402
from . import estate as _estate  # noqa: E402
from . import expat as _expat  # noqa: E402
from . import healthcare as _health  # noqa: E402
from . import housing as _housing  # noqa: E402
from . import housing_affordability as _afford  # noqa: E402
from . import jurisdiction as _jurisdiction  # noqa: E402
from . import life as _life  # noqa: E402
from . import limits as _lim  # noqa: E402
from . import pension as _pension  # noqa: E402
from . import pfic as _pfic  # noqa: E402
from . import portfolio as _port  # noqa: E402
from . import presence as _presence  # noqa: E402
from . import probate as _probate  # noqa: E402
from . import property as _property  # noqa: E402
from . import realestate as _re  # noqa: E402
from . import reporting as _reporting  # noqa: E402
from . import retirement as _retire  # noqa: E402
from . import ssa as _ssa  # noqa: E402
from . import status as _status  # noqa: E402
from . import survivor as _survivor  # noqa: E402
from . import tax_planning as _taxplan  # noqa: E402
from . import transitions as _trans  # noqa: E402
from . import umbrella as _umbrella  # noqa: E402
import datetime as _dt  # noqa: E402


def _retirement_savings_path(data: dict, annual_savings: float) -> list[float]:
    current = next(
        (s for s in (F._dig(data, "cash_flow.scenarios") or [])
         if s.get("kind") == "current"), {})
    return _retire.savings_path_from_obligations(
        annual_savings, current.get("obligations") or [])


def _cash_yield(data: dict) -> Outcome:
    skill = "cash-yield-review"
    tax = _cash.TaxProfile(
        federal=F._dig(data, "assumptions.marginal_tax_rate"),
        niit=F._dig(data, "assumptions.niit_rate"),
        state=F._dig(data, "assumptions.state_tax_rate"),
        state_code=F._dig(data, "meta.jurisdiction.state"),
    )
    r = _cash.review_yield(
        F._dig(data, "household.balance_sheet") or [],
        benchmark_apr=F._dig(data, "assumptions.cash_benchmark_apr"),
        benchmark_as_of=F._dig(data, "assumptions.cash_benchmark_as_of"),
        benchmark_label=F._dig(data, "assumptions.cash_benchmark_label"),
        benchmark_state_exempt=bool(
            F._dig(data, "assumptions.cash_benchmark_state_tax_exempt")),
        tax=tax,
    )
    if r.total_foregone > 0:
        return act(
            skill,
            f"{_money(r.total_foregone)}/yr left on the table in cash",
            TIER_DRAG, impact_annual=r.total_foregone,
            detail=f"Of which {_money(r.total_durable)}/yr is durable. "
                   f"Benchmark: {r.benchmark_label or 'unnamed'}.")
    if not r.lines:
        return act(skill, "; ".join(r.findings) or "cash review inconclusive",
                   TIER_OPTIMISE)
    return ok(skill, "Liquid holdings are at or above the benchmark")


def _conflict_check(data: dict) -> Outcome:
    skill = "conflict-check"
    r = _conflicts.check(data)
    if not r.live:
        return ok(skill, "No known live conflicts between skills")
    out = Outcome(skill=skill, status="action",
                  headline=f"{len(r.live)} live conflict(s) between skills")
    for c in r.live:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"{' vs '.join(c.skills)}: {c.key}",
            detail=f"{c.tension} Trigger: {c.trigger} "
                   f"Resolution: {c.resolution}",
            irreversible=False))
    return out


def _disability(data: dict) -> Outcome:
    skill = "disability-insurance-review"
    members = F._dig(data, "household.members") or []
    policies = F._dig(data, "insurance.disability") or []
    spending = float(F._dig(data, "household.annual_spending"))
    liquid = F.liquid(data)
    today = F.as_of(data)
    out = Outcome(skill=skill, status="ok", headline="")
    insured_ids = sorted({p.get("insured") for p in policies if p.get("insured")})
    for iid in insured_ids:
        member = next((x for x in members if x.get("id") == iid), {})
        a = _disab.assess(
            policies, insured_id=iid, insured_age=member.get("age"),
            annual_spending=spending,
            gross_income=float(member.get("income_annual") or 0),
            liquid_assets=liquid, reference_date=today)
        if not a.covered:
            out.actions.append(Action(
                skill=skill, tier=TIER_UNCOVERED,
                headline=f"Disability cover short by "
                         f"{_money(a.monthly_gap)}/mo for {iid}",
                impact_annual=a.monthly_gap * 12,
                detail="After-tax cover against spending; see the skill "
                       "report for the definition and benefit-period terms."))
        for d in a.deadlines:
            if d.passed or (d.days_remaining is not None
                            and d.days_remaining <= CLOSING_WINDOW_DAYS):
                out.actions.append(Action(
                    skill=skill, tier=TIER_CLOSING,
                    headline=f"{d.label}: "
                             f"{'closed ' + d.on.isoformat() if d.passed else f'{d.days_remaining} days left'}",
                    days_to_expiry=d.days_remaining,
                    irreversible=True,
                    detail="A Future Increase option buys insurability "
                           "without underwriting; once shut it cannot be "
                           "repriced."))
    # The SSDI overlay is reported by the skill, not ranked here.
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Disability cover meets spending with no closing riders"
    return out



# survivor-needs: mirrors run.py lines 18-42 calling survivor.compute; tier because a capital gap is a loss survivors cannot self-insure after the fact (uncovered), with annual_shortfall as impact_annual per the disability precedent
def _survivor_needs(data: dict) -> "Outcome":
    skill = "survivor-needs"
    members = F._dig(data, "household.members") or []
    earners = [x for x in members
               if x.get("role") in ("primary", "spouse") and (x.get("income_annual") or 0) > 0]
    if not earners:
        return ok(skill, "No member has recorded income — nothing to replace")
    available = (F.tier_total(data, F.LIQUID) + F.tier_total(data, F.AGE_RESTRICTED)
                 + F.tier_total(data, F.ILLIQUID))
    spending = float(F._dig(data, "household.annual_spending"))
    out = Outcome(skill=skill, status="ok", headline="")
    for e in sorted(earners, key=lambda x: x.get("id") or ""):
        need = _survivor.compute(
            insured_id=e["id"],
            members=members,
            annual_spending=spending,
            assets_available=available,
            education_obligation=F._dig(data, "household.education_obligation"),
            non_citizen_survivor=any(
                x.get("role") == "spouse" and x.get("us_status")
                and x.get("us_status") != "citizen" for x in members),
            social_security=F._dig(data, "social_security"),
        )
        if need.net_need > 0:
            out.actions.append(Action(
                skill=skill, tier=TIER_UNCOVERED,
                headline=(f"If the {e.get('role')} ({e['id']}) income stops: "
                          f"capital gap {_money(need.net_need)}"),
                impact_annual=need.annual_shortfall,
                detail=(f"Need {_money(need.total_need)} against "
                        f"{_money(need.assets_available)} available; shortfall "
                        f"{_money(need.annual_shortfall)}/yr over "
                        f"{need.horizon_years} years.")))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Assets cover the survivor need for every earner"
    return out


# life-insurance-review: mirrors run.py lines 18-37 calling survivor.compute + life.assess; tier because a cover shortfall is uncovered, while term cover expiring within the closing window is dated and cannot be repriced later (closing, days from F.as_of)
def _life_insurance_review(data: dict) -> "Outcome":
    skill = "life-insurance-review"
    members = F._dig(data, "household.members") or []
    policies = F._dig(data, "insurance.life") or []
    today = F.as_of(data)
    available = (F.tier_total(data, F.LIQUID) + F.tier_total(data, F.AGE_RESTRICTED)
                 + F.tier_total(data, F.ILLIQUID))
    spending = float(F._dig(data, "household.annual_spending"))
    dependents = F.dependents(data)
    out = Outcome(skill=skill, status="ok", headline="")
    insured_ids = sorted({p.get("insured") for p in policies if p.get("insured")})
    for iid in insured_ids:
        need = _survivor.compute(
            insured_id=iid, members=members, annual_spending=spending,
            assets_available=available,
            education_obligation=F._dig(data, "household.education_obligation"),
            non_citizen_survivor=any(
                x.get("role") == "spouse" and x.get("us_status")
                and x.get("us_status") != "citizen" for x in members),
            social_security=F._dig(data, "social_security"))
        a = _life.assess(policies, need=need.net_need, insured_id=iid,
                         dependents=dependents, today=today)
        if not a.covered:
            out.actions.append(Action(
                skill=skill, tier=TIER_UNCOVERED,
                headline=(f"Life cover short by {_money(a.gap)} for {iid} "
                          f"(need {_money(a.need)}, portable in force "
                          f"{_money(a.in_force_portable)})"),
                detail=(f"Premiums {_money(a.annual_premium)}/yr. " +
                        " ".join(a.notes))))
        if today is not None:
            for p in sorted(a.policies, key=lambda p: p.label):
                if p.expires is None:
                    continue
                days_left = (p.expires - today).days
                if days_left <= CLOSING_WINDOW_DAYS:
                    out.actions.append(Action(
                        skill=skill, tier=TIER_CLOSING,
                        headline=(f"Term cover `{p.label}` "
                                  f"{'expired ' + p.expires.isoformat() if days_left < 0 else f'expires in {days_left} days'}"),
                        days_to_expiry=days_left,
                        irreversible=False,
                        detail="Renewing means renewing at that age, in that health."))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Life cover meets the survivor need with no closing expiries"
    return out


# long-term-care-funding: mirrors run.py lines 24-39 calling healthcare.assess_ltc; tier because a tail the survivor cannot absorb is uncovered (survivor_shortfall $/yr as impact_annual); an in-force policy of unverified adequacy is optimise since a gap cannot honestly be claimed
def _long_term_care_funding(data: dict) -> "Outcome":
    skill = "long-term-care-funding"
    investable = F.tier_total(data, F.LIQUID) + F.tier_total(data, F.AGE_RESTRICTED)
    policies = F._dig(data, "healthcare.ltc.policies") or []
    a = _health.assess_ltc(
        annual_cost=F._dig(data, "healthcare.ltc.annual_cost_today"),
        cost_as_of=F._dig(data, "healthcare.ltc.cost_as_of"),
        investable_assets=investable,
        survivor_annual_spending=F._dig(
            data, "healthcare.ltc.survivor_annual_spending"),
        has_policy=bool(policies),
        policy_type=(policies[0].get("type") if policies else None),
    )
    if a.verdict in (_health.TRANSFER, _health.PARTIAL):
        if policies:
            return act(
                skill,
                (f"In-force LTC policy of type `{policies[0].get('type') or 'unrecorded'}` "
                 f"against a {a.verdict} tail — verify benefit, inflation "
                 f"protection and benefit period"),
                TIER_OPTIMISE,
                detail="; ".join(a.findings))
        label = "Transfer the tail" if a.verdict == _health.TRANSFER else "Partial transfer"
        return act(
            skill,
            (f"{label}: {_money(a.tail_cost)} tail against "
             f"{_money(investable)} investable"),
            TIER_UNCOVERED,
            impact_annual=a.survivor_shortfall,
            detail="; ".join(a.findings))
    if a.verdict == _health.SELF_INSURE:
        return ok(skill, "Tail care cost is absorbable — self-insure and earmark")
    return ok(skill, "; ".join(a.findings) or "LTC need cannot be determined")


# umbrella-liability: mirrors run.py lines 32-44 calling umbrella.assess; tier because a limit shortfall and attachment-gate failures leave exposure uncovered, while disclosure riders are real but neither expiring nor priced (optimise)
def _umbrella_liability(data: dict) -> "Outcome":
    skill = "umbrella-liability"
    prop = F._dig(data, "property") or {}
    a = _umbrella.assess(
        attachable_assets=F.attachable(data),
        household_income=F.household_income(data),
        auto_coverage=F._dig(data, "auto.coverage") or {},
        property_coverage=prop.get("coverage") or {},
        property_exclusions=prop.get("exclusions"),
        dependents=F.dependents(data),
        balance_sheet=F._dig(data, "household.balance_sheet") or [],
        in_force=F._dig(data, "umbrella.coverage"),
    )
    out = Outcome(skill=skill, status="ok", headline="")
    if a.shortfall:
        out.actions.append(Action(
            skill=skill, tier=TIER_UNCOVERED,
            headline=(f"Umbrella short by {_money(a.shortfall)} "
                      f"(recommended {_money(a.recommended)}, in force "
                      f"{_money(a.in_force)})"),
            detail=(f"Exposure {_money(a.exposure)}. Estimated cost "
                    f"{_money(a.cost_estimate[0])}-{_money(a.cost_estimate[1])}/yr. " +
                    " ".join(a.notes))))
    for g in sorted(a.failures, key=lambda g: (g.policy, g.coverage)):
        out.actions.append(Action(
            skill=skill, tier=TIER_UNCOVERED,
            headline=(f"Raise {g.policy} {g.coverage} from {_money(g.current)} "
                      f"to {_money(g.required)} to bind an umbrella"),
            detail="Carriers will not attach excess cover below this."))
    if a.riders:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"Disclose or schedule {len(sorted(set(a.riders)))} item(s) before binding",
            detail="; ".join(sorted(set(a.riders)))))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    elif a.in_force:
        out.headline = "Umbrella in force at or above the recommended limit"
    else:
        out.headline = "No umbrella shortfall and the attachment gate passes"
    return out


# auto-insurance-review: mirrors run.py lines 59-136 calling jurisdiction.rules_for + auto.assess_liability + auto.assess_vehicle per vehicle; tier because liability gaps are uncovered while dropping overpriced physical-damage cover saves premium $/yr (drag); umpd/medpay guidance (lines 195-201) is advisory with no pass/fail and is not ranked
def _auto_insurance_review(data: dict) -> "Outcome":
    skill = "auto-insurance-review"
    state = F._dig(data, "meta.jurisdiction.state")
    rules = _jurisdiction.rules_for(state)
    liquid = F.liquid(data)
    attachable = F.attachable(data)
    income = F.household_income(data)
    buffer_months = F.months_of_spending(data)
    cov = F._dig(data, "auto.coverage") or {}
    lia = _auto.assess_liability(
        cov, attachable_assets=attachable, household_income=income, rules=rules)
    out = Outcome(skill=skill, status="ok", headline="")
    for g in sorted(lia.gaps):
        out.actions.append(Action(
            skill=skill, tier=TIER_UNCOVERED,
            headline=g,
            detail=" ".join(lia.jurisdiction_notes)))
    vehicles = F._dig(data, "auto.vehicles") or []
    for v in sorted(vehicles, key=lambda v: v.get("label") or v.get("id") or ""):
        a = _auto.assess_vehicle(v, liquid_assets=liquid, buffer_months=buffer_months)
        if a.decision in ("drop_collision", "drop_both"):
            if a.decision == "drop_collision" and a.premium_collision_annual is not None:
                saving = a.premium_collision_annual
            else:
                saving = a.premium_pd_annual
            out.actions.append(Action(
                skill=skill, tier=TIER_DRAG,
                headline=(f"{a.label}: drop "
                          f"{'collision' if a.decision == 'drop_collision' else 'comprehensive and collision'} "
                          f"to save {_money(saving)}/yr"),
                impact_annual=saving,
                detail=" ".join(a.reasons) + (
                    f" {a.comprehensive_note}" if a.comprehensive_note else "")))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = ("Auto liability meets targets; no physical-damage "
                        "drop priced")
    return out


# renters-homeowners-review: mirrors run.py lines 37-51 calling property.assess; tier because blocker/gap findings are protection gaps (uncovered) while note findings are real but unpriced and undated (optimise)
def _renters_homeowners_review(data: dict) -> "Outcome":
    skill = "renters-homeowners-review"
    prop = F._dig(data, "property")
    people = len(F._dig(data, "household.members") or [])
    liquid = F.liquid(data)
    attachable = F.attachable(data)
    umbrella = F._dig(data, "umbrella.coverage")
    a = _property.assess(
        prop,
        people=people,
        liquid_assets=liquid,
        attachable_assets=attachable,
        umbrella_in_force=umbrella,
    )
    order = {"blocker": 0, "gap": 1, "note": 2, "ok": 3}
    out = Outcome(skill=skill, status="ok", headline="")
    for f in sorted(a.findings, key=lambda f: (order[f.severity], f.key)):
        if f.severity in ("blocker", "gap"):
            out.actions.append(Action(
                skill=skill, tier=TIER_UNCOVERED,
                headline=f"{f.key}: {f.current} -> {f.target}",
                detail=f.detail))
        elif f.severity == "note":
            out.actions.append(Action(
                skill=skill, tier=TIER_OPTIMISE,
                headline=f"{f.key}: {f.current} -> {f.target}",
                detail=f.detail))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Property cover meets all targets"
    return out


# citizenship-status-review: mirrors run.py lines 18-20 calling status.audit; tier because every finding (even blockers) is a determination to obtain, neither expiring nor priced in $/yr (optimise); note findings ride in outcome findings, ok findings mean ok
def _citizenship_status_review(data: dict) -> "Outcome":
    skill = "citizenship-status-review"
    members = F._dig(data, "household.members") or []
    a = _status.audit(members, domicile=F._dig(data, "household.domicile"))
    order = {"blocker": 0, "gap": 1, "note": 2, "ok": 3}
    out = Outcome(skill=skill, status="ok", headline="")
    for f in sorted(a.findings, key=lambda x: (order[x.severity], x.area)):
        if f.severity in ("blocker", "gap"):
            out.actions.append(Action(
                skill=skill, tier=TIER_OPTIMISE,
                headline=f"{f.area}: {f.detail}",
                detail=("Affects: " + ", ".join(f.affects)) if f.affects else ""))
        elif f.severity == "note":
            out.findings.append(f"{f.area}: {f.detail}")
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Status recorded with no open blockers or gaps"
    return out


# beneficiary-audit: mirrors run.py build lines 17-27 calling estate.audit_beneficiaries; tier because a defective designation routes the asset into probate at death, a loss that cannot be self-insured after the fact (uncovered); pure notes are neither expiring nor priced (optimise).
def _beneficiary_audit(data: dict) -> "Outcome":
    skill = "beneficiary-audit"
    members = F._dig(data, "household.members") or []
    items = [(r.get("name") or "account", r)
             for r in (F._dig(data, "household.balance_sheet") or [])]
    items += [(p.get("label") or p.get("id") or "policy", p)
              for p in (F._dig(data, "insurance.life") or [])]
    trust = next((d for d in (F._dig(data, "estate.documents") or [])
                  if d.get("type") == "revocable_trust"), None)
    a = _estate.audit_beneficiaries(items, members=members,
                                    trust_funded=trust.get("funded") if trust else None)
    out = Outcome(skill=skill, status="ok", headline="")
    for f in sorted(a.findings, key=lambda x: (x.subject, x.severity, x.detail)):
        if f.severity == "ok":
            continue
        tier = TIER_UNCOVERED if f.severity in ("blocker", "gap") else TIER_OPTIMISE
        out.actions.append(Action(skill=skill, headline="%s: %s" % (f.subject, f.detail),
                                  tier=tier, detail=f.detail))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "%d designation(s) examined, none defective" % a.checked
    return out


# estate-document-review: mirrors run.py build lines 23-33 calling estate.audit_documents; tier because a missing or unrecorded will, POA, or unfunded trust bites at death or incapacity and cannot be fixed after the fact (uncovered); the optional-trust note is neither expiring nor priced (optimise).
def _estate_document_review(data: dict) -> "Outcome":
    skill = "estate-document-review"
    docs = F._dig(data, "estate.documents")
    members = F._dig(data, "household.members") or []
    non_citizen_spouse = any(
        m.get("role") == "spouse" and m.get("us_status")
        and m.get("us_status") != "citizen" for m in members)
    dom = F._dig(data, "household.domicile") or {}
    a = _estate.audit_documents(
        docs or [], today=F.as_of(data),
        non_citizen_spouse=non_citizen_spouse,
        domicile_determined=dom.get("determined") if dom else None)
    out = Outcome(skill=skill, status="ok", headline="")
    for f in sorted(a.findings, key=lambda x: (x.subject, x.severity, x.detail)):
        if f.severity == "ok":
            continue
        tier = TIER_UNCOVERED if f.severity in ("blocker", "gap") else TIER_OPTIMISE
        out.actions.append(Action(skill=skill, headline="%s: %s" % (f.subject, f.detail),
                                  tier=tier, detail=f.detail))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Estate documents exist and are current"
    return out


# digital-estate: mirrors run.py build lines 22-24 calling estate.audit_digital; tier because credentials nobody can reach after death or incapacity lock heirs out exactly as well as attackers, an unrecoverable access loss (uncovered).
def _digital_estate(data: dict) -> "Outcome":
    skill = "digital-estate"
    digital = F._dig(data, "estate.digital")
    a = _estate.audit_digital(digital)
    out = Outcome(skill=skill, status="ok", headline="")
    for f in sorted(a.findings, key=lambda x: (x.subject, x.severity, x.detail)):
        if f.severity == "ok":
            continue
        tier = TIER_UNCOVERED if f.severity in ("blocker", "gap") else TIER_OPTIMISE
        out.actions.append(Action(skill=skill, headline="%s: %s" % (f.subject, f.detail),
                                  tier=tier, detail=f.detail))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Digital access is recoverable by the person named"
    return out


# continuity-plan: the domain module owns operational readiness and reuses the
# estate/digital/designation audits. A blocked first-response path is an
# uncovered risk; noncritical completion work is an optimization.
def _continuity_plan(data: dict) -> "Outcome":
    skill = "continuity-plan"
    plan = _continuity.build_plan(data)
    if plan.readiness == _continuity.READY:
        return ok(skill, "Death and incapacity paths are operationally ready")
    count = len(plan.critical_gaps)
    if count:
        return act(
            skill,
            f"Continuity plan blocked by {count} critical operational gap(s)",
            TIER_UNCOVERED,
            detail=plan.critical_gaps[0].detail,
        )
    return act(
        skill,
        f"Continuity plan has {len(plan.noncritical_gaps)} completion item(s)",
        TIER_OPTIMISE,
        detail=plan.noncritical_gaps[0].detail,
    )


# probate-exposure: mirrors run.py build lines 25-34 calling probate.assess plus lines 101/142 calling probate.cost/probate.recommend; tier because an exposed account passes through court on death, a route that cannot be repriced afterwards (uncovered); unknown titling/designation needs phone calls first, neither expiring nor priced (optimise).
def _probate_exposure(data: dict) -> "Outcome":
    skill = "probate-exposure"
    state = F._dig(data, "meta.jurisdiction.state")
    members = F._dig(data, "household.members") or []
    rows = F._dig(data, "household.balance_sheet") or []
    docs = F._dig(data, "estate.documents") or []
    by_type = {d.get("type"): d for d in docs}
    trust = by_type.get("revocable_trust") or {}
    trust_exists = bool(trust.get("exists"))
    trust_funded = trust.get("funded")
    e = _probate.assess(rows, state=state)
    fixes = _probate.recommend(e.routes, members=members, trust_exists=trust_exists)
    lo = _probate.cost(e.exposed_total, e.rules)
    exposed = {r.label for r in e.exposed}
    out = Outcome(skill=skill, status="ok", headline="")
    if trust_exists and trust_funded is False:
        out.actions.append(Action(
            skill=skill, headline="Trust exists but is unfunded: retitle assets into it",
            tier=TIER_OPTIMISE,
            detail="Recorded as unfunded in estate.documents; every "
                   "non-trust-titled account above is the funding never done."))
    for fx in sorted(fixes, key=lambda x: x.label):
        if fx.label in exposed:
            if lo.small_estate:
                continue
            detail = fx.instrument + ". " + fx.rationale
            if lo.computable and lo.total:
                detail += " Ordinary probate cost on the exposed total: $%s." % f"{lo.total:,.0f}"
            elif not lo.computable:
                detail += " Probate cost cannot be estimated: %s." % lo.detail
            if fx.withheld:
                detail += " Withheld on suitability: " + fx.withheld
            out.actions.append(Action(skill=skill, headline="%s: %s" % (fx.label, fx.instrument),
                                      tier=TIER_UNCOVERED, detail=detail))
        else:
            detail = fx.rationale
            if fx.withheld:
                detail += " Withheld on suitability: " + fx.withheld
            out.actions.append(Action(skill=skill, headline="%s: %s" % (fx.label, fx.instrument),
                                      tier=TIER_OPTIMISE, detail=detail))
    out.actions.sort(key=lambda x: (x.headline, x.detail))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "No account is positively exposed to probate"
    return out


# marriage-finance-merger: mirrors run.py build lines 24-41 calling transitions.assess_marriage; tier because a positive net filing advantage is priced dollars per year (drag); stale-beneficiary and other blockers are protection gaps fixed by filing forms (uncovered); gaps such as missing independent access are neither expiring nor priced (optimise).
def _marriage_finance_merger(data: dict) -> "Outcome":
    skill = "marriage-finance-merger"
    mar = F._dig(data, "transitions.marriage") or {}
    spend = F._dig(data, "household.annual_spending")
    plan = _trans.assess_marriage(
        members=F._dig(data, "household.members") or [],
        domicile=F._dig(data, "household.domicile"),
        joint_tax=mar.get("tax_if_joint"),
        separate_tax_combined=mar.get("tax_if_separate_combined"),
        idr_payment_joint=mar.get("idr_annual_payment_joint"),
        idr_payment_separate=mar.get("idr_annual_payment_separate"),
        medical_expenses=mar.get("medical_expenses"),
        lower_earner_agi=mar.get("lower_earner_agi"),
        household_agi=mar.get("household_agi"),
        accounts_with_stale_beneficiaries=mar.get("stale_beneficiary_accounts"),
        monthly_spending=(float(spend) / 12.0) if spend else None,
        independent_access=mar.get("independent_access"),
    )
    c = plan.filing
    out = Outcome(skill=skill, status="ok", headline="")
    if c.tax_delta is None:
        out.actions.append(Action(
            skill=skill, headline="Run the return both ways and record tax_if_joint and tax_if_separate_combined",
            tier=TIER_OPTIMISE,
            detail="Both totals are needed and at least one is missing; no rule of thumb substitutes."))
    elif (c.net_advantage or 0.0) > 0:
        out.actions.append(Action(
            skill=skill, headline="File separate: wins by $%s/yr net" % f"{c.net_advantage:,.0f}",
            tier=TIER_DRAG, impact_annual=c.net_advantage,
            detail="Separate costs more in tax but saves more in income-driven loan payments."))
    for f in sorted(plan.findings, key=lambda x: (x.area, x.severity, x.detail)):
        if f.severity in ("ok", "note"):
            continue
        if f.severity == "blocker" and f.area == "filing status" and c.tax_delta is None:
            continue
        if f.severity == "blocker":
            tier = TIER_UNCOVERED
        elif f.severity == "gap":
            tier = TIER_OPTIMISE
        else:
            continue
        out.actions.append(Action(skill=skill, headline="%s: %s" % (f.area, f.detail),
                                  tier=tier, detail=f.detail))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Joint filing stands; no stale beneficiaries or checklist blockers"
    return out


# divorce-asset-split: mirrors run.py build lines 17-36 calling transitions.split_assets; tier because an unequal after-tax split, a wrong QDRO sequence, or a stale beneficiary becomes permanent at the decree and cannot be self-insured afterwards (uncovered); unassigned assets and missing inputs are neither expiring nor priced (optimise).
def _divorce_asset_split(data: dict) -> "Outcome":
    skill = "divorce-asset-split"
    div = F._dig(data, "transitions.divorce") or {}
    labels = tuple(div.get("parties") or ("a", "b"))
    s = _trans.split_assets(
        div.get("assets") or [],
        ordinary_rate=F._dig(data, "assumptions.marginal_tax_rate"),
        capital_gains_rate=F._dig(data, "assumptions.capital_gains_rate"),
        party_labels=labels,
    )
    if not s.lines:
        detail = "; ".join(f.detail for f in sorted(s.findings, key=lambda x: (x.area, x.detail)))
        return act(skill, detail or "No assets recorded; nothing to compare",
                   TIER_OPTIMISE, detail=detail)
    out = Outcome(skill=skill, status="ok", headline="")
    for f in sorted(s.findings, key=lambda x: (x.area, x.severity, x.detail)):
        if f.severity in ("ok", "note"):
            continue
        if f.severity == "blocker":
            tier = TIER_UNCOVERED
        elif f.severity == "gap":
            tier = TIER_OPTIMISE
        else:
            continue
        out.actions.append(Action(
            skill=skill, headline="%s: %s" % (f.area, f.detail), tier=tier,
            irreversible=("irreversible" in f.detail.lower()), detail=f.detail))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "After-tax values do not distort this split"
    return out


# education-funding: mirrors run.py build lines 34-44 calling education.plan_for plus the helper lines 17-31 calling retirement.assess_readiness and education.ordering_rule; tier because a funding gap is borrowable and unpriced per year, so every finding here is real but neither expiring nor priced (optimise); runner lines 46-52 force the checklist choice, the ordering rule has no pass/fail of its own.
def _education_funding(data: dict) -> "Outcome":
    skill = "education-funding"
    edu = F._dig(data, "education") or {}
    state = F._dig(data, "meta.jurisdiction.state")
    members = F._dig(data, "household.members") or []
    p = _edu.plan_for(
        edu.get("children"),
        members=members,
        accounts=edu.get("accounts") or [],
        cost_inflation=float(edu.get("cost_inflation") or _edu.DEFAULT_COST_INFLATION),
        real_return=float(edu.get("real_return") or _edu.DEFAULT_REAL_RETURN),
        state=state,
    )
    savings = F._dig(data, "retirement.annual_savings")
    spending = F._dig(data, "household.annual_spending")
    on_track = None
    age_at = None
    if savings is not None and spending is not None:
        primary = next((x for x in members if x.get("role") == "primary"), {})
        classified = F.retirement_assets(data)
        if not classified.unknown:
            r = _retire.assess_readiness(
                annual_spending=float(spending), assets=classified.included,
                annual_savings=float(savings),
                current_age=primary.get("age"),
                savings_by_year=_retirement_savings_path(
                    data, float(savings)))
            on_track = r.years_to_target is not None
            age_at = r.age_at_target
    lines = _edu.ordering_rule(retirement_on_track=on_track,
                               retirement_age_at_target=age_at)
    out = Outcome(skill=skill, status="ok", headline="")
    if on_track is False:
        out.actions.append(Action(
            skill=skill, headline="Retirement is off track: close any education gap without diverting retirement savings",
            tier=TIER_OPTIMISE, detail=" ".join(lines)))
    for c in sorted(p.children, key=lambda x: x.member_id or ""):
        if c.gap > 0:
            detail = "$%s gap against $%s projected cost. %s" % (
                f"{c.gap:,.0f}", f"{c.projected_cost:,.0f}",
                " ".join(c.findings))
            out.actions.append(Action(
                skill=skill, headline="%s education gap of $%s" % (c.member_id, f"{c.gap:,.0f}"),
                tier=TIER_OPTIMISE, detail=detail.strip()))
    if p.unallocated_savings > 0:
        out.actions.append(Action(
            skill=skill, headline="Attribute $%s of education savings to a named beneficiary" % f"{p.unallocated_savings:,.0f}",
            tier=TIER_OPTIMISE,
            detail="A 529 has exactly one beneficiary at a time; pooled balances overstate every gap."))
    for f in sorted(p.findings):
        if p.unallocated_savings > 0 and "not attributed" in f:
            continue
        out.actions.append(Action(skill=skill, headline=f, tier=TIER_OPTIMISE, detail=f))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Education fully funded and retirement on track"
    return out



# retirement-readiness: mirrors run.py lines 19-30 calling _retire.assess_readiness/_retire.sensitivity; tier because the projection prices no dollars per year and carries no expiry, so a plan that does not close is real but neither expiring nor priced.
def _retirement_readiness(data: dict) -> "Outcome":
    skill = "retirement-readiness"
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    spending = float(F._dig(data, "household.annual_spending"))
    savings = float(F._dig(data, "retirement.annual_savings"))
    classified = F.retirement_assets(data)
    assets = classified.included
    age = primary.get("age")
    r = _retire.assess_readiness(annual_spending=spending, assets=assets,
                           annual_savings=savings, current_age=age,
                           savings_by_year=_retirement_savings_path(data, savings))
    if classified.unknown:
        return act(
            skill,
            "Retirement asset eligibility is incomplete; unclassified assets "
            "are excluded",
            TIER_OPTIMISE,
            detail="Add retirement_eligible for: "
                   + ", ".join(classified.unknown) + ".")
    if r.already_there:
        return ok(skill, "Assets already exceed the target — the question is sequencing, not accumulation")
    if r.years_to_target is None:
        return act(skill, "Plan does not close at central assumptions — spending, savings, or the target must change",
                   TIER_OPTIMISE, detail="; ".join(r.findings))
    grid = _retire.sensitivity(annual_spending=spending, assets=assets,
                         annual_savings=savings, current_age=age,
                         savings_by_year=_retirement_savings_path(data, savings))
    ages = [row[rr]["age"] for row in grid for rr in _retire.REAL_RETURN_SCENARIOS
            if row[rr]["age"] is not None]
    if ages:
        return act(skill,
                   f"Target in about {r.years_to_target:.0f} years at central assumptions (plausible range age {min(ages):.0f} to {max(ages):.0f})",
                   TIER_OPTIMISE, detail="The spread across the sensitivity grid is the answer, not the middle cell.")
    return act(skill, f"Target in about {r.years_to_target:.0f} years at central assumptions",
               TIER_OPTIMISE, detail="; ".join(r.findings))


# roth-conversion-window: mirrors run.py lines 17-22 calling _lim.retirement_ages/_retire.conversion_window; tier because the window is an opportunity with no priced annual dollars and the runner carries no deadline objects, so it is real but neither expiring nor priced.
def _roth_conversion_window(data: dict) -> "Outcome":
    skill = "roth-conversion-window"
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    ages = _lim.retirement_ages(primary.get("birth_year"))
    win = _retire.conversion_window(
        retirement_age=F._dig(data, "retirement.planned_retirement_age"),
        ages=ages, claim_age=F._dig(data, "retirement.ss_claim_age"))
    if win.exists:
        return act(skill,
                   f"A {win.years}-year window: ages {win.opens_age} to {win.closes_age} — fill brackets, do not convert on schedule",
                   TIER_OPTIMISE, detail="; ".join(win.findings))
    return ok(skill, "No conversion window at these ages")


# withdrawal-sequencing: mirrors run.py lines 17-28 calling _lim.retirement_ages/_retire.drawdown_guidance with the same balance-sheet name scan and tier-total guards; tier because missing-balance findings are structural gaps with no priced annual figure and no deadline objects, so optimise.
def _withdrawal_sequencing(data: dict) -> "Outcome":
    skill = "withdrawal-sequencing"
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    rows = F._dig(data, "household.balance_sheet") or []
    names = " ".join((r.get("name") or "").lower() for r in rows)
    has_taxable = F.tier_total(data, F.LIQUID) > 0
    has_tax_deferred = any(k in names for k in ("401k", "ira", "403b", "457"))
    has_roth = "roth" in names
    ages = _lim.retirement_ages(primary.get("birth_year"))
    current_age = primary.get("age")
    d = _retire.drawdown_guidance(
        current_age=current_age,
        ages=ages,
        has_taxable=has_taxable,
        has_tax_deferred=has_tax_deferred,
        has_roth=has_roth,
    )
    out = Outcome(skill=skill, status="ok", headline="")
    if not has_roth and has_tax_deferred:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="No Roth balance recorded — every retirement dollar will be taxed as ordinary income",
            detail="Without a Roth there is no lever to manage the bracket in a given year; that is what makes the conversion window valuable."))
    if not has_taxable and has_tax_deferred:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="No taxable balance recorded — nothing to spend in early retirement without generating ordinary income",
            detail="Removes most bracket-management flexibility and can complicate pre-59.5 access."))
    if ages.known and current_age is not None and current_age < 59:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="Retiring before 59.5 needs an access plan, not just a number",
            detail="Rule of 55 (separation in or after the year of turning 55, workplace plan only) or section 72(t) payments; rolling a 401(k) to an IRA forfeits the Rule of 55."))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Withdrawal order set with bracket-filling capacity in place"
    return out


# social-security-timing: mirrors run.py lines 18-89 calling _lim.retirement_ages, _retire.claiming_table, _retire.claiming_guidance, _status.social_security_notes, _ssa.insured_status, _ssa.uninsured_spouse_notes, _ssa.worker_pia_from_statement and _ssa.credit_building_notes with the same optional-field reads; tier because every verdict is guidance with no priced annual dollars and no expiry, so optimise.
def _social_security_timing(data: dict) -> "Outcome":
    skill = "social-security-timing"
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    ages = _lim.retirement_ages(primary.get("birth_year"))
    earners = [x for x in members if (x.get("income_annual") or 0) > 0]
    adults = [x for x in members if x.get("role") in ("primary", "spouse")]
    single_earner = len(earners) <= 1 and len(adults) > 1
    out = Outcome(skill=skill, status="ok", headline="")
    table = _retire.claiming_table(ages)
    recorded = F._dig(data, "social_security.retirement_monthly") or {}
    if not table:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="Full retirement age cannot be resolved from the birth year — read it from the Social Security statement",
            detail="It steps in months across the 1955-1959 birth years and is deliberately not approximated."))
    elif not recorded:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="No benefit amounts recorded — transcribe social_security.retirement_monthly from the statement",
            detail="The statutory percentages decide nothing on their own; a benefit computed here would be a guess wearing a statement's clothes."))
    statuses = {m.get("id"): m.get("us_status") for m in members
                if m.get("role") in ("primary", "spouse")}
    home = next((c for m in members for c in (m.get("citizenship") or [])
                 if c != "US"), None)
    status_notes = _status.social_security_notes(statuses=statuses, home_country=home)
    if status_notes:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="Cross-border caveat on Social Security — confirm payability with SSA before the plan depends on it",
            findings=list(status_notes)))
    spouse = next((x for x in members if x.get("role") == "spouse"), None)
    if spouse is not None:
        notes = _ssa.uninsured_spouse_notes(
            insured=_ssa.insured_status(spouse),
            payable_abroad=F._dig(data, "social_security.payable_abroad"))
        notes += _ssa.credit_building_notes(
            own_projected_monthly=F._dig(
                data, "social_security.spouse_own_projected_monthly"),
            worker_pia_monthly=_ssa.worker_pia_from_statement(
                F._dig(data, "social_security")))
        if notes:
            out.actions.append(Action(
                skill=skill, tier=TIER_OPTIMISE,
                headline="The spouse's own record needs a decision before the claiming decision",
                findings=list(notes)))
    guide = _retire.claiming_guidance(ages=ages, single_earner_household=single_earner)
    if single_earner and ages.known:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="Single-income couple: delaying the higher earner's claim raises the survivor's floor for life",
            detail="The household keeps the larger of the two benefits, not both; a non-earning spouse has no record of their own to fall back on.",
            findings=list(guide)))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Claiming ages resolved with recorded dollars beside the percentages"
    return out


# medicare-enrollment-timing: mirrors run.py lines 16-40 (the _tiers helper and _health.assess_medicare with the same optional-field guards) and lines 96-109 (_retire.conversion_window, _health.params_from_assumptions, _health.taper_at/subsidy_at, _health.magi_conflicts); uncovered for the sub-20-employee primary-payer gap and the COBRA-as-bridge error because both leave uninsured exposure that cannot be bought back after the fact, optimise for the rest; no closing because the runner carries no Deadline objects and years_away is whole years, so no days_to_expiry is passed.
def _medicare_enrollment_timing(data: dict) -> "Outcome":
    skill = "medicare-enrollment-timing"
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    ages = _lim.retirement_ages(primary.get("birth_year"))
    retire_at = F._dig(data, "retirement.planned_retirement_age")
    magi = F._dig(data, "assumptions.expected_magi_in_gap_years")
    working_past_65 = F._dig(data, "healthcare.working_past_65")
    employer_employees = F._dig(data, "healthcare.employer_employees")
    coverage_is_current = F._dig(data, "healthcare.coverage_is_current_employment")
    tiers = [_health.IrmaaTier(float(t["magi_threshold"]),
                         float(t.get("part_b_monthly", 0) or 0),
                         float(t.get("part_d_monthly", 0) or 0))
             for t in (F._dig(data, "assumptions.irmaa_tiers") or [])]
    a = _health.assess_medicare(
        current_age=primary.get("age"),
        working_past_65=working_past_65,
        employer_employees=employer_employees,
        coverage_is_current_employment=coverage_is_current,
        part_a_quarters=F._dig(data, "healthcare.part_a_quarters"),
        magi=magi,
        irmaa_tiers=tiers,
        contributing_to_hsa=bool(F._dig(data, "contributions.hsa.eligible")),
    )
    out = Outcome(skill=skill, status="ok", headline="")
    if working_past_65 and employer_employees is None:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="Employer size not recorded — it decides whether Part B can be delayed safely",
            detail="At 20+ employees the group plan pays primary; below that Medicare is primary and not enrolling leaves an uninsured gap."))
    if working_past_65 and employer_employees is not None and employer_employees < _health.SEP_EMPLOYER_MIN_EMPLOYEES:
        out.actions.append(Action(
            skill=skill, tier=TIER_UNCOVERED,
            headline="Below the 20-employee threshold — Medicare is primary, so enrol in Part B at 65 regardless of the group plan",
            detail="The plan may pay only what it would owe as secondary, so the Medicare share is simply unpaid."))
    if coverage_is_current is False:
        out.actions.append(Action(
            skill=skill, tier=TIER_UNCOVERED,
            headline="COBRA, retiree, or marketplace cover is not current-employment cover — it creates no Part B special enrolment period",
            detail="Treating it as a bridge past 65 accrues the permanent late penalty for the whole of it."))
    if a.part_a_premium_free is False:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="Part A is not premium-free on this record — the shortfall is fixable only with covered employment before 65",
            detail="A spouse's record may qualify the household instead."))
    window = _retire.conversion_window(
        retirement_age=retire_at, ages=ages,
        claim_age=F._dig(data, "retirement.ss_claim_age"))
    params = _health.params_from_assumptions(F._dig(data, "assumptions"))
    size = len(members)
    conflicts = [c for c in _health.magi_conflicts(
        retirement_age=retire_at, window=window,
        taper=(_health.taper_at(magi, size, params) if magi is not None else None),
        subsidy=(_health.subsidy_at(magi, size, params) if magi is not None else None),
    ) if c.live and skill in c.skills]
    for c in conflicts:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"{c.name}: {c.overlap_years} overlapping year(s)",
            detail=c.detail, findings=list(c.quantified)))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Medicare windows mapped with no enrolment gaps"
    return out


# aca-subsidy-optimization: mirrors run.py lines 18-35 calling _lim.retirement_ages, _retire.conversion_window, _health.params_from_assumptions and _health.assess_aca; drag with impact_annual set to the priced yearly credit when a live conflict governs it, uncovered when gap-year MAGI falls outside credit eligibility, optimise when the figure is refused for missing annual inputs.
def _aca_subsidy_optimization(data: dict) -> "Outcome":
    skill = "aca-subsidy-optimization"
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    ages = _lim.retirement_ages(primary.get("birth_year"))
    retire_at = F._dig(data, "retirement.planned_retirement_age")
    window = _retire.conversion_window(
        retirement_age=retire_at, ages=ages,
        claim_age=F._dig(data, "retirement.ss_claim_age"))
    params = _health.params_from_assumptions(F._dig(data, "assumptions"))
    a = _health.assess_aca(
        retirement_age=retire_at,
        household_size=len(members),
        magi=F._dig(data, "assumptions.expected_magi_in_gap_years"),
        params=params,
        window=window,
    )
    if retire_at is None:
        return act(skill, "No planned retirement age recorded — the pre-Medicare gap cannot be sized",
                   TIER_OPTIMISE, detail="; ".join(a.findings))
    if not a.gap.exists:
        return ok(skill, "No pre-Medicare gap at these ages")
    if a.point is not None and a.point.eligible is False:
        return act(skill, "Gap-year MAGI falls outside premium credit eligibility",
                   TIER_UNCOVERED, detail=(a.point.reason or "") + "; ".join(a.findings))
    if a.magi is None or not params.computable:
        return act(skill, "Subsidy figure refused, not estimated — supply the missing annual inputs",
                   TIER_OPTIMISE, detail="; ".join(a.findings))
    live = [c for c in a.conflicts if c.live and skill in c.skills]
    if a.point is not None and a.point.subsidy and live:
        c = live[0]
        return act(skill,
                   f"Gap-year credit worth ${a.point.subsidy:,.0f}/yr shares {c.overlap_years} year(s) with the conversion window — convert around it",
                   TIER_DRAG, impact_annual=a.point.subsidy,
                   detail="; ".join(c.quantified))
    if a.point is not None and a.point.subsidy:
        return act(skill,
                   f"Gap-year credit worth ${a.point.subsidy:,.0f}/yr depends on holding MAGI in band",
                   TIER_DRAG, impact_annual=a.point.subsidy,
                   detail="; ".join(a.findings))
    return act(skill, "Gap years priced with no credit due — funding comes entirely from the household",
               TIER_OPTIMISE, detail="; ".join(a.findings))


# employer-match-audit: mirrors run.py lines 18-31 calling _lim.for_year/_contrib.analyse_match with the same plan/age reads; drag with impact_annual set to the forfeited match when timing puts dollars at risk, optimise otherwise; the unknown-formula branch (run.py lines 91-102 in contributions.analyse_match) is a pure checklist with no pass/fail, so act/optimise there with the severity finding as the headline.
def _employer_match_audit(data: dict) -> "Outcome":
    skill = "employer-match-audit"
    year = F._dig(data, "contributions.year")
    plan = F._dig(data, "contributions.employer_plan") or {}
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    lim = _lim.for_year(year)
    if not lim.known:
        return act(skill,
                   f"Statutory limits for {year} are not in the table — the section 402(g) ceiling decides when deferrals stop, so timing cannot be modelled until the year is added with a citation",
                   TIER_OPTIMISE)
    a = _contrib.analyse_match(plan, age=primary.get("age"), lim=lim)
    if a.at_risk:
        return act(skill,
                   f"Up to ${a.forfeited:,.0f} of employer match at risk this year — spread deferrals across every pay period",
                   TIER_DRAG, impact_annual=a.forfeited,
                   detail="; ".join(a.findings))
    if a.match_earned is not None:
        return ok(skill, "No match lost to timing")
    return act(skill, (a.findings[0] if a.findings else "Match timing cannot be answered yet"),
               TIER_OPTIMISE, detail="; ".join(a.findings[1:]))

# from . import cash as _cash
# from . import debt as _debt
# from . import housing as _housing
# from . import disclosure as _disclosure
# from . import transitions as _trans

# emergency-fund-sizing: mirrors run.py lines 18-29 calling cash.size_buffer;
# tier because a shortfall is a protection gap (nothing to self-insure from,
# run.py lines 59-66) and excess cash is real but neither expiring nor priced.
def _emergency_fund_sizing(data: dict) -> "Outcome":
    skill = "emergency-fund-sizing"
    members = F._dig(data, "household.members") or []
    earners = [x for x in members if (x.get("income_annual") or 0) > 0]
    var = next((x.get("income_variable_share") for x in earners
                if x.get("income_variable_share") is not None), None)
    reserve = F.reserve_assets(data)
    b = _cash.size_buffer(
        liquid=reserve.included,
        annual_spending=float(F._dig(data, "household.annual_spending")),
        earners=len(earners),
        has_dependents=bool(F.dependents(data)),
        variable_comp_share=var,
    )
    if b.shortfall:
        return act(
            skill,
            f"{_money(b.shortfall)} short of emergency-fund target "
            f"({b.months_held:.1f} of {b.target_months:.0f} months held)",
            TIER_UNCOVERED,
            detail="; ".join(sorted(b.findings)))
    if b.excess:
        return act(
            skill,
            f"Adequate buffer, with {_money(b.excess)} of excess cash "
            "to redeploy",
            TIER_OPTIMISE,
            detail="; ".join(sorted(b.findings)))
    return ok(skill, "Emergency buffer meets its target")


# debt-payoff-priority: mirrors run.py lines 18-22 calling debt.plan; tier
# because a non-terminating schedule and high-rate balances are ongoing priced
# interest (drag, annualised from balance x apr), while the avalanche/snowball
# ordering gap is a one-off cost that is real but not annual (optimise).
def _debt_payoff_priority(data: dict) -> "Outcome":
    skill = "debt-payoff-priority"
    extra = F._dig(data, "assumptions.monthly_debt_extra") or 0
    rate = F._dig(data, "assumptions.marginal_tax_rate") or 0.0
    p = _debt.plan(
        F._dig(data, "debts") or [],
        monthly_extra=float(extra),
        marginal_rate=float(rate),
        expected_return_apr=F._dig(data, "assumptions.expected_return_apr"))
    if not p.debts:
        return ok(skill, "No debts with a balance recorded")
    if not (p.avalanche and p.snowball and p.avalanche.terminated):
        yearly = sum(d.balance * d.apr for d in p.debts)
        return act(
            skill,
            "Minimum payments do not cover interest; balances grow "
            f"indefinitely (about {_money(yearly)}/yr of interest accrual)",
            TIER_DRAG, impact_annual=yearly,
            detail="; ".join(sorted(p.findings)))
    out = Outcome(skill=skill, status="ok", headline="")
    if p.cost_of_snowball and p.cost_of_snowball > 0:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"Snowball costs {_money(p.cost_of_snowball)} more "
                     "than avalanche",
            detail="That is the entire price of the psychologically easier "
                   "schedule."))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Both orderings cost the same here; no high-rate debt"
    return out


# mortgage-review: mirrors run.py lines 18-26 calling housing.review_mortgage;
# tier because PMI still billed below the removal LTV is an ongoing priced
# annual premium (drag); prepayment/refinance notes are informational.
def _mortgage_review(data: dict) -> "Outcome":
    skill = "mortgage-review"
    mo = F._dig(data, "housing.mortgage") or {}
    r = _housing.review_mortgage(
        balance=float(mo.get("balance") or 0),
        rate=float(mo.get("rate") or 0),
        term_years=int(mo.get("remaining_years") or 30),
        value=mo.get("property_value"),
        pmi_monthly=mo.get("pmi_monthly"),
        extra_monthly=float(mo.get("extra_monthly") or 0),
    )
    pmi = mo.get("pmi_monthly")
    if r.ltv is not None and pmi and r.ltv < _housing.PMI_REMOVAL_LTV:
        yearly = float(pmi) * 12
        return act(
            skill,
            f"Loan-to-value is {r.ltv:.0%}, below the "
            f"{_housing.PMI_REMOVAL_LTV:.0%} threshold, and mortgage "
            f"insurance is still being paid ({_money(yearly)}/yr)",
            TIER_DRAG, impact_annual=yearly,
            detail="Removal is usually not automatic; ask, and an appraisal "
                   "may be needed.")
    return ok(skill, "No PMI waste; refinancing is a break-even calculation")


# rent-vs-buy: mirrors run.py lines 18-31 calling housing.compare; tier
# because a verdict for renting over the planned horizon is an ongoing priced
# excess cost of owning, annualised over the horizon (drag); a verdict for
# buying leaves nothing to do.
def _rent_vs_buy(data: dict) -> "Outcome":
    skill = "rent-vs-buy"
    p = F._dig(data, "housing.purchase") or {}
    rent = float(F._dig(data, "housing.monthly_rent"))
    years = int(p.get("expected_years") or 7)
    ret = F._dig(data, "assumptions.nominal_investment_return")
    if ret is None:
        ret = _housing.DEFAULT_INVESTMENT_RETURN
    appr = F._dig(data, "assumptions.home_appreciation")
    if appr is None:
        appr = _housing.DEFAULT_APPRECIATION
    growth = F._dig(data, "assumptions.rent_growth")
    if growth is None:
        growth = _housing.DEFAULT_RENT_GROWTH
    c = _housing.compare(
        p, monthly_rent=rent, years=years,
        investment_return=float(ret), appreciation=float(appr),
        rent_growth=float(growth))
    gap = abs(c.difference)
    if gap <= 0:
        return ok(skill, f"Renting and buying cost about the same over "
                         f"{years} years")
    if c.owning_cheaper:
        return ok(skill, f"Buying is cheaper over {years} years, by "
                         f"{_money(gap)}")
    yearly = gap / years if years else gap
    breakeven = (f"break-even about {c.breakeven_years} years"
                 if c.breakeven_years else "no break-even within 40 years")
    return act(
        skill,
        f"Renting is cheaper over {years} years, by {_money(gap)} "
        f"(about {_money(yearly)}/yr); {breakeven}",
        TIER_DRAG, impact_annual=yearly,
        detail="Principal repaid is excluded from owning cost; both sides "
               "are carried forward to the horizon at the investment return.")


# housing-affordability: mirrors the runner's reconciled scenario and
# constraint calculation. A target above the stress ceiling is an actionable
# planning conflict; a reconciliation failure is a blocker, never an estimate.
def _housing_affordability(data: dict) -> Outcome:
    skill = "housing-affordability"
    try:
        r = _afford.assess(
            scenarios=F._dig(data, "cash_flow.scenarios") or [],
            purchase=F._dig(data, "housing.purchase") or {},
            monthly_rent=float(F._dig(data, "housing.monthly_rent")),
            balance_sheet=F._dig(data, "household.balance_sheet") or [],
            reserve_assets=F.reserve_assets(data),
            retirement_annual_savings=F._dig(
                data, "retirement.annual_savings"),
            household_income=F.household_income(data),
            household_income_components=F.household_income_components(data),
            affordability=F._dig(data, "housing.affordability") or {},
            transition=F._dig(data, "housing.transition") or {},
            rental_deals=F._dig(data, "real_estate.deals") or [],
            portfolio_wash_sale=F._dig(data, "portfolio.wash_sale"),
        )
    except _afford.ReconciliationError as exc:
        return act(skill, f"Affordability blocked: {exc}", TIER_OPTIMISE)
    try:
        transition = _afford.transition_from_facts(data)
    except _afford.ReconciliationError as exc:
        return act(skill, f"Housing transition blocked: {exc}", TIER_OPTIMISE)
    if transition.blockers:
        return act(
            skill, "Housing transition financing/occupancy is inconsistent",
            TIER_OPTIMISE, detail="; ".join(transition.blockers))
    phase_failures = [
        check for check in _afford.phase_cash_checks(r.scenarios, transition)
        if not check.passes
    ]
    if phase_failures:
        return act(
            skill,
            f"Target transition misses the savings floor in "
            f"{len(phase_failures)} phase/scenario row(s)",
            TIER_OPTIMISE,
            detail="Run the phase table; current rent, tenant carry, and "
                   "owner costs are applied exactly once.")
    if r.target_price > r.stress_tested_ceiling:
        return act(
            skill,
            f"Target {_money(r.target_price)} exceeds the stress-tested "
            f"ceiling {_money(r.stress_tested_ceiling)}",
            TIER_OPTIMISE,
            detail=f"Binding constraint: {r.binding_constraint}. Current "
                   f"income capacity is {_money(r.current_income_ceiling)}; "
                   f"liquidity limit is {_money(r.liquidity_maximum)}.")
    return ok(
        skill,
        f"Target {_money(r.target_price)} is within the stress-tested ceiling "
        f"of {_money(r.stress_tested_ceiling)}")


# ca-sfh-disclosure-review: mirrors run.py lines 65, 78 and 88 calling
# disclosure.required_disclosures / year_gated_but_unknown / missing_reports;
# tier because run.py lines 52-57 force the choice: this is the checklist, not
# the analysis, with no pass/fail verdict, so it is act() at optimise even
# when the package is complete on paper.
def _ca_sfh_disclosure_review(data: dict) -> "Outcome":
    skill = "ca-sfh-disclosure-review"
    state = (F._dig(data, "property_review.state")
             or F._dig(data, "meta.jurisdiction.state"))
    ptype = F._dig(data, "property_review.property_type")
    year = F._dig(data, "property_review.year_built")
    provided = F._dig(data, "property_review.documents_provided")
    if state != "CA":
        return ok(skill, "This skill encodes California law only, and the "
                         f"recorded jurisdiction is {state}")
    req = _disclosure.required_disclosures(property_type=ptype,
                                           year_built=year)
    have = {str(x).strip().lower() for x in (provided or [])}
    missing_d = sorted(d.name for d in req if d.key not in have)
    missing_r = sorted(
        label for _k, label in _disclosure.missing_reports(
            provided, property_type=_disclosure.SINGLE_FAMILY))
    unknown_year = _disclosure.year_gated_but_unknown(year_built=year)
    if not missing_d and not missing_r and not unknown_year:
        return act(
            skill,
            "Package complete on paper; every conclusion still requires "
            "reading the documents",
            TIER_OPTIMISE,
            detail="This is the checklist, not the analysis: no part of it "
                   "is a finding until a document has been read.")
    bits = []
    if missing_d:
        bits.append(f"{len(missing_d)} required disclosure(s) not seen: "
                    + "; ".join(missing_d))
    if missing_r:
        bits.append(f"{len(missing_r)} standard report(s) missing: "
                    + "; ".join(missing_r))
    if unknown_year:
        bits.append("year_built unrecorded, so "
                    + ", ".join(sorted(d.name for d in unknown_year))
                    + " stays on the list")
    if _disclosure.is_cid(ptype):
        bits.append("property sits in a common interest development: use "
                    "ca-condo-hoa-disclosure-review for the association half")
    return act(
        skill,
        f"Disclosure package gaps: {'; '.join(bits)}",
        TIER_OPTIMISE,
        detail="Label every claim from the documents as stated, inferred "
               "or absent.")


# ca-condo-hoa-disclosure-review: mirrors run.py lines 61, 85, 107-108, 185
# and 199 calling disclosure.missing_packet_items / review_hoa / sb326 /
# required_disclosures / missing_reports; tier because run.py lines 50-58
# force the choice: checklist, not analysis, and the module refuses to score
# a property or produce a verdict, so act() at optimise with the severest
# checklist item as the headline.
def _ca_condo_hoa_disclosure_review(data: dict) -> "Outcome":
    skill = "ca-condo-hoa-disclosure-review"
    state = (F._dig(data, "property_review.state")
             or F._dig(data, "meta.jurisdiction.state"))
    ptype = F._dig(data, "property_review.property_type")
    year = F._dig(data, "property_review.year_built")
    units = F._dig(data, "property_review.unit_count")
    elevated = F._dig(data, "property_review.elevated_elements")
    provided = F._dig(data, "property_review.documents_provided")
    hoa = F._dig(data, "property_review.hoa") or {}
    if state != "CA":
        return ok(skill, "This skill encodes California law only, and the "
                         f"recorded jurisdiction is {state}")
    if not _disclosure.is_cid(ptype):
        return ok(skill, "No association on this property type; use "
                         "ca-sfh-disclosure-review")
    packet_missing = _disclosure.missing_packet_items(hoa.get("packet_provided"))
    r = _disclosure.review_hoa(hoa)
    sb = _disclosure.sb326(property_type=ptype, unit_count=units,
                           elevated_elements=elevated,
                           report=hoa.get("sb326_report"))
    req = _disclosure.required_disclosures(property_type=ptype,
                                           year_built=year)
    have = {str(x).strip().lower() for x in (provided or [])}
    absent = sorted(d.name for d in req if d.key not in have)
    missing_r = sorted(
        label for _k, label in _disclosure.missing_reports(
            provided, property_type=ptype))
    high = sorted(f.topic for f in r.flags if f.severity == "high")
    bits = []
    if high:
        bits.append(f"{len(high)} high-severity association flag(s): "
                    + "; ".join(high))
    if packet_missing:
        bits.append(f"{len(packet_missing)} of "
                    f"{len(_disclosure.HOA_PACKET_ITEMS)} §4525 packet items "
                    "not recorded as provided")
    if sb.applies:
        bits.append(f"SB 326 applies; report status `{sb.status}`")
    elif sb.applies is None:
        bits.append("SB 326 applicability cannot be determined")
    if absent:
        bits.append(f"{len(absent)} other disclosure(s) not seen: "
                    + "; ".join(absent))
    if missing_r:
        bits.append(f"{len(missing_r)} standard report(s) missing: "
                    + "; ".join(missing_r))
    if not r.determinable:
        bits.append("some association inputs unrecorded, each reported as "
                    "a note rather than a pass")
    if not bits:
        return act(
            skill,
            "Association checklist complete on paper; every conclusion "
            "still requires reading the documents",
            TIER_OPTIMISE,
            detail="On a condo the building and the association are usually "
                   "the larger risk.")
    return act(
        skill,
        f"Condo disclosure gaps: {'; '.join(bits)}",
        TIER_OPTIMISE,
        detail="A missing §4525 item is a finding rather than a gap in the "
               "analysis; request missing items in writing, by name.")


# windfall-management: mirrors run.py lines 24-39 calling
# transitions.assess_windfall (with the run.py lines 21-27 naked-beneficiary
# derivation and as_of=F.as_of(data)); tier because the live 90-day pause is
# a dated finding expiring (closing, days_to_expiry from the runner's own
# pause_days_remaining), the federal tax on receipt is priced (drag), and
# character/beneficiary gaps are real but neither (optimise).
def _windfall_management(data: dict) -> "Outcome":
    skill = "windfall-management"
    events = F._dig(data, "transitions.windfall") or []
    bs = F._dig(data, "household.balance_sheet") or []
    naked = sorted(r.get("name", "?") for r in bs
                   if r.get("new_from_windfall")
                   and r.get("beneficiary_applicable") is not False
                   and r.get("beneficiaries") is None)
    if not events:
        return ok(skill, "No windfall events recorded")
    plan = _trans.assess_windfall(
        events,
        as_of=F.as_of(data),
        marginal_rate=F._dig(data, "assumptions.marginal_tax_rate"),
        withheld=F._dig(data, "transitions.tax_withheld_ytd"),
        prior_year_tax=F._dig(data, "transitions.prior_year_tax"),
        prior_year_agi=F._dig(data, "transitions.prior_year_agi"),
        aca_marketplace_coverage=F._dig(
            data, "transitions.aca_marketplace_coverage"),
        medicare_within_lookback=F._dig(
            data, "transitions.medicare_within_lookback"),
        new_accounts_without_beneficiaries=naked,
    )
    out = Outcome(skill=skill, status="ok", headline="")
    live = [e for e in plan.events if e.pause_elapsed is False]
    if live:
        soonest = min(e.pause_days_remaining or 0 for e in live)
        out.actions.append(Action(
            skill=skill, tier=TIER_CLOSING,
            headline=f"Do nothing irreversible for another {soonest} "
                     f"day(s): {len(live)} of {len(plan.events)} windfall "
                     "event(s) inside the 90-day pause",
            days_to_expiry=soonest,
            irreversible=True,
            detail="Park it somewhere safe and liquid; cover the tax; name "
                   "beneficiaries."))
    if plan.estimated_tax is not None and plan.estimated_tax > 0:
        detail = (f"Taxable on receipt {_money(plan.taxable_amount)}; "
                  f"estimated federal tax {_money(plan.estimated_tax)}.")
        if plan.shortfall:
            detail += f" Gap against withheld: {_money(plan.shortfall)}."
        if plan.safe_harbor is not None:
            detail += (f" Prior-year safe harbour {_money(plan.safe_harbor)}.")
        out.actions.append(Action(
            skill=skill, tier=TIER_DRAG,
            headline=f"About {_money(plan.estimated_tax)} of federal tax on "
                     "the windfall receipt",
            impact_annual=plan.estimated_tax,
            detail=detail + " Federal only, nominal, and a floor."))
    unknown = sorted(e.label for e in plan.events
                     if not e.character.known)
    if unknown:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"{len(unknown)} windfall event(s) with unknown tax "
                     f"character: {'; '.join(unknown)}",
            detail="The kind determines the tax; do not fill the gap by "
                   "analogy."))
    undated = [e for e in plan.events if e.pause_days_remaining is None]
    if undated and not live:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="No receipt date recorded, so the 90-day pause cannot "
                     "be checked",
            detail="Add `received`. If the money arrived this month, the "
                   "answer is no."))
    if F._dig(data, "assumptions.marginal_tax_rate") is None:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="No marginal rate supplied, so the tax owed cannot "
                     "be sized",
            detail="Unknown is not zero: the failure mode is spending the "
                   "gross and meeting the bill in April."))
    if naked:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"{len(naked)} new account(s) with no beneficiary "
                     f"recorded: {'; '.join(naked)}",
            detail="A designation overrides the will; run "
                   "`beneficiary-audit`."))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    elif plan.estimated_tax == 0:
        out.headline = ("No federal income tax on receipt; pause elapsed "
                        "and character known")
    else:
        out.headline = "Windfall reviewed; pause elapsed, nothing priced"
    return out


# contribution-space-audit: mirrors run.py build lines 18-21 calling contributions.audit_space; tier because unused room is neither dated (the runner carries no deadline objects) nor priced $/yr by the module (total_unused is dollars of room, not an annual cost)
def _contribution_space_audit(data: dict) -> "Outcome":
    skill = "contribution-space-audit"
    year = F._dig(data, "contributions.year")
    a = _contrib.audit_space(F._dig(data, "contributions") or {},
                             members=F._dig(data, "household.members") or [],
                             year=year)
    if not a.limits_known:
        return act(skill, "; ".join(a.findings) or "contribution space inconclusive: limits unknown",
                   TIER_OPTIMISE)
    if a.total_unused > 0:
        return act(skill, f"{_money(a.total_unused)} of tax-advantaged space is unused this year",
                   TIER_OPTIMISE,
                   detail="; ".join(a.findings[:2]))
    return ok(skill, "All recorded tax-advantaged space is used")

# hsa-review: mirrors run.py build lines 18-22 and 53-60 calling limits.for_year and limits.hsa_space; tier because unused HSA room is neither dated (no deadline objects in the runner) nor priced $/yr by the module
def _hsa_review(data: dict) -> "Outcome":
    skill = "hsa-review"
    year = F._dig(data, "contributions.year")
    lim = _lim.for_year(year)
    hsa = F._dig(data, "contributions.hsa")
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    age = primary.get("age")
    if not lim.known:
        return act(skill, f"Statutory limits for {year} unknown; HSA space cannot be checked",
                   TIER_OPTIMISE)
    if hsa is None:
        return act(skill, "HSA not recorded; if HDHP-eligible this is the highest-value unused space",
                   TIER_OPTIMISE)
    if hsa.get("eligible") is False or hsa.get("coverage") in (None, "none"):
        return ok(skill, "Not HSA-eligible; worth re-evaluating at open enrolment")
    used = float(hsa.get("contribution") or 0)
    space = _lim.hsa_space(hsa.get("coverage"), age, lim)
    if space and used < space:
        return act(skill, f"{_money(space - used)} of HSA space unused; fill before taxable saving",
                   TIER_OPTIMISE)
    return ok(skill, "HSA space fully used")

# equity-comp-review: mirrors run.py build lines 18-20 calling concentration.vesting_outlook; tier because the module prices the step-down in dollars per year (run rate vs steady state delta)
def _equity_comp_review(data: dict) -> "Outcome":
    skill = "equity-comp-review"
    eq = F._dig(data, "equity_comp") or {}
    today = F.as_of(data)
    if today is None:
        return act(skill, "meta.as_of is missing, so vesting dates cannot be "
                          "placed in time",
                   TIER_OPTIMISE)
    o = _conc.vesting_outlook(eq.get("grants") or [], today=today)
    if o.delta > 0:
        first = o.next_cliff.isoformat() if o.next_cliff else "date unknown"
        return act(skill,
                   f"Equity income steps down {_money(o.delta)}/yr without refresh; first step {first}",
                   TIER_DRAG, impact_annual=o.delta,
                   detail="Test affordability against the steady state, not the run rate.")
    return ok(skill, "No near-term vesting cliff")

# employer-concentration-risk: mirrors run.py build lines 18-37 calling concentration.assess_exposure and concentration.joint_scenario; tier because the joint layoff-plus-decline loss cannot be self-insured after the fact, while the standing sell-at-vest rule is real but neither expiring nor priced
def _employer_concentration_risk(data: dict) -> "Outcome":
    skill = "employer-concentration-risk"
    eq = F._dig(data, "equity_comp") or {}
    members = F._dig(data, "household.members") or []
    employer = eq.get("employer") or "the employer"
    linked = [x for x in members if x.get("employer")]
    income_linked = sum(float(x.get("income_annual") or 0) for x in linked)
    investable = (F.tier_total(data, F.LIQUID) + F.tier_total(data, F.AGE_RESTRICTED)
                  + F.tier_total(data, F.ILLIQUID))
    e = _conc.assess_exposure(
        employer=employer,
        income_from_employer=income_linked,
        total_income=F.household_income(data),
        held_value=float(eq.get("held_value") or 0),
        unvested_value=float(eq.get("unvested_value") or 0),
        investable=investable, liquid=F.liquid(data),
        monthly_spending=float(F._dig(data, "household.annual_spending")) / 12.0,
        sell_at_vest=eq.get("sell_at_vest"),
    )
    s = _conc.joint_scenario(e)
    out = Outcome(skill=skill, status="ok", headline="")
    if e.severity != "within_guideline":
        out.actions.append(Action(
            skill=skill, tier=TIER_UNCOVERED,
            headline=f"{e.income_share:.0%} of income and {e.asset_share:.0%} of assets depend on "
                     f"{employer}; severity {e.severity.replace('_', ' ')}",
            detail=f"Joint scenario loses {_money(s.total_loss)} with {s.runway_months:.0f} months "
                   "runway; the layoff and the decline are one event, not two."))
    if eq.get("sell_at_vest") is not True:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="Adopt sell-at-vest as a standing policy",
            detail="Vested shares held are cash used to buy employer stock; decide once."))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Employer concentration within guideline with sell-at-vest in force"
    return out

# solo-retirement-plan-choice: mirrors run.py build lines 18-44 calling entity.solo_plan_options with TaxParams(marginal_rate, ss_wage_base); tier because the plan choice is real but neither dated (no deadline objects in the runner) nor priced $/yr by the module
def _solo_retirement_plan_choice(data: dict) -> "Outcome":
    skill = "solo-retirement-plan-choice"
    biz = F._dig(data, "business") or {}
    members = F._dig(data, "household.members") or []
    owners = set(biz.get("owners") or [])
    owner = next((x for x in members if x.get("id") in owners), None)
    if owner is None:
        owner = next((x for x in members if x.get("role") == "primary"), {})
    age = owner.get("age")
    as_of = F.as_of(data)
    year = as_of.year if as_of else None
    net_profit = float(biz.get("gross_revenue") or 0) - float(biz.get("expenses") or 0)
    structure = biz.get("structure")
    salary = biz.get("owner_w2_salary")
    on_payroll = structure in (_ent.S_CORP, _ent.C_CORP)
    p = _ent.TaxParams(
        marginal_rate=F._dig(data, "assumptions.marginal_tax_rate"),
        ss_wage_base=F._dig(data, "assumptions.ss_wage_base"),
    )
    choice = _ent.solo_plan_options(
        net_profit=None if on_payroll else net_profit,
        w2_salary=salary if on_payroll else None,
        age=age, year=year, p=p)
    if not choice.limits_known:
        return act(skill, "; ".join(choice.findings) or "solo plan choice inconclusive: limits unknown",
                   TIER_OPTIMISE)
    best = choice.best
    if best is not None and best.total is not None:
        if on_payroll and salary is None:
            return act(skill,
                       f"{best.name} shelters the most at {_money(best.total)}, but W-2 salary is "
                       "unrecorded so plan space cannot be sized",
                       TIER_OPTIMISE)
        return act(skill, f"{best.name} shelters the most: {_money(best.total)} this year",
                   TIER_OPTIMISE, detail="; ".join(choice.findings[:1]))
    return ok(skill, "No solo plan figure computable on these inputs")

# entity-structure-comparison: mirrors run.py _params lines 19-47 and build lines 51-62 calling entity.compare; tier because the take-home gap between structures is an ongoing priced annual cost of staying put
def _entity_structure_comparison(data: dict) -> "Outcome":
    skill = "entity-structure-comparison"
    members = F._dig(data, "household.members") or []
    adults = [x for x in members if x.get("role") in ("primary", "spouse")]
    status = F._dig(data, "household.filing_status") or (
        "married_joint" if len(adults) > 1 else "single")
    owners = set(F._dig(data, "business.owners") or [])
    other_wages = float(F._dig(data, "business.owner_outside_wages") or 0.0)
    other_income = float(sum(x.get("income_annual") or 0 for x in adults
                             if x.get("id") not in owners))
    p = _ent.TaxParams(
        marginal_rate=F._dig(data, "assumptions.marginal_tax_rate"),
        state_rate=F._dig(data, "assumptions.state_tax_rate"),
        ss_wage_base=F._dig(data, "assumptions.ss_wage_base"),
        qbi_threshold=F._dig(data, "assumptions.qbi_threshold"),
        qbi_phase_in=F._dig(data, "assumptions.qbi_phase_in_range"),
        qualified_dividend_rate=F._dig(data, "assumptions.qualified_dividend_rate"),
        niit_rate=F._dig(data, "assumptions.niit_rate"),
        filing_status=status,
        other_wages=other_wages,
        other_taxable_income=other_income,
        deductions_total=F._dig(data, "assumptions.deductions_total"),
    )
    biz = F._dig(data, "business") or {}
    b = _ent.Business(
        gross_revenue=float(biz.get("gross_revenue") or 0),
        expenses=float(biz.get("expenses") or 0),
        sstb=bool(biz.get("sstb")),
        field=biz.get("field"),
        ubia=biz.get("ubia"),
        reasonable_salary_floor=biz.get("reasonable_salary_floor"),
        s_corp_annual_cost=biz.get("s_corp_annual_cost"),
    )
    c = _ent.compare(b, p)
    if not c.params_known:
        return act(skill, "; ".join(c.findings) or "entity comparison inconclusive: indexed figures missing",
                   TIER_OPTIMISE)
    best = c.best
    if best is None:
        return act(skill, "No entity figure computable on these inputs", TIER_OPTIMISE)
    label = {_ent.SCHEDULE_C: "Schedule C", _ent.S_CORP: "S-Corp", _ent.C_CORP: "C-Corp"}
    runner_up = max([o.take_home for o in c.outcomes
                     if o.unavailable is None and o.structure != best.structure], default=None)
    gap = best.take_home - runner_up if runner_up is not None else 0.0
    if gap > 0:
        return act(skill,
                   f"{label.get(best.structure, best.structure)} ahead by {_money(gap)}/yr take-home",
                   TIER_DRAG, impact_annual=gap,
                   detail="Gaps between rows are reliable; levels are approximations.")
    return ok(skill, "No structure ahead on these figures")

# depreciation-election: mirrors run.py _figures lines 17-29 and build lines 33-60 calling depreciation.evaluate and depreciation.method_lock; tier because year-one elections are real choices but carry no deadline objects in the runner and no $/yr pricing in the module
def _depreciation_election(data: dict) -> "Outcome":
    skill = "depreciation-election"
    rows = F._dig(data, "business.assets") or []
    as_of = F.as_of(data)
    figures = _depr.YearFigures(
        year=as_of.year if as_of else None,
        section_179_limit=F._dig(data, "assumptions.section_179_limit"),
        section_179_phaseout=F._dig(data, "assumptions.section_179_phaseout"),
        suv_179_cap=F._dig(data, "assumptions.suv_179_cap"),
        bonus_pct=F._dig(data, "assumptions.bonus_depreciation_pct"),
        luxury_auto_year1_cap=F._dig(data, "assumptions.luxury_auto_year1_cap"),
        luxury_auto_year1_cap_no_bonus=F._dig(data, "assumptions.luxury_auto_year1_cap_no_bonus"),
        standard_mileage_rate=F._dig(data, "assumptions.standard_mileage_rate"),
    )
    income = F._dig(data, "business.taxable_income")
    total_placed = sum(float(r.get("cost") or 0) for r in rows)
    out = Outcome(skill=skill, status="ok", headline="")
    for row in sorted(rows, key=lambda r: (r.get("description") or r.get("name") or "asset")):
        a = _depr.Asset(
            description=row.get("description") or row.get("name") or "asset",
            cost=float(row.get("cost") or 0),
            business_use=row.get("business_use"),
            gvwr_lbs=row.get("gvwr_lbs"),
            annual_business_miles=row.get("annual_business_miles"),
            actual_operating_cost=row.get("actual_operating_cost"),
            placed_in_service=row.get("placed_in_service"),
        )
        e = _depr.evaluate(a, figures, taxable_business_income=income,
                           total_placed_in_service=total_placed)
        if a.business_use is None:
            out.actions.append(Action(
                skill=skill, tier=TIER_OPTIMISE,
                headline=f"{a.description}: business-use percentage not recorded, so no election can be sized",
                detail="Unknown is not 100%."))
            continue
        near_line = (_depr.BUSINESS_USE_FLOOR <= (a.business_use or 0.0)
                     < _depr.BUSINESS_USE_FLOOR + _depr.USE_WARNING_MARGIN)
        carried = [o for o in e.options if o.carryforward]
        lock_open = a.is_vehicle and row.get("first_year_method") is None
        if carried or lock_open or near_line:
            largest = e.largest
            bits = []
            if carried:
                bits.append(f"{_money(carried[0].carryforward)} carried forward")
            if lock_open:
                bits.append("year-one method unrecorded; actuals now close off mileage for life")
            if near_line:
                bits.append("use barely over 50%; recapture risk")
            out.actions.append(Action(
                skill=skill, tier=TIER_OPTIMISE,
                headline=f"{a.description}: "
                         f"{largest.label + ' ' + _money(largest.year_one_deduction) if largest else 'no clean election'} "
                         f"({'; '.join(bits)})",
                detail="; ".join(e.findings[:2])))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Depreciation elections carry no carryforward, lock-in, or recapture flags"
    return out


# asset-allocation-review: mirrors run.py build lines 18-27 calling portfolio.review_allocation, portfolio.years_to_retirement, portfolio.glide_path and portfolio.review_location; tier because drift, glide position and location swaps are real but neither expiring nor protection gaps nor priced in $/yr, so optimise.
def _asset_allocation_review(data: dict) -> Outcome:
    skill = "asset-allocation-review"
    rows = F._dig(data, "household.balance_sheet") or []
    a = _port.review_allocation(rows, F._dig(data, "portfolio.target_allocation"))
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), None)
    years = _port.years_to_retirement(
        F._dig(data, "retirement.planned_retirement_age"),
        (primary or {}).get("age"))
    g = _port.glide_path(years=years, actual_equity=a.inv.equity_share)
    loc = _port.review_location(a.inv)
    if not a.total:
        return act(skill, "No classified holdings, so there is no allocation to review",
                   TIER_OPTIMISE,
                   detail="Every balance-sheet row is earmarked, pending, or missing "
                          "asset_class. Name the class before drift can be read.")
    out = Outcome(skill=skill, status="ok", headline="")
    if a.breached:
        over = sorted((s for s in a.breached if s.drift > 0),
                      key=lambda s: s.asset_class)
        under = sorted((s for s in a.breached if s.drift < 0),
                       key=lambda s: s.asset_class)
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"{len(a.breached)} of {len(a.sleeves)} classes are outside "
                     "their band",
            detail="Overweight: "
                   + (", ".join(f"{s.asset_class} {s.drift:+.1%}" for s in over)
                      or "none")
                   + ". Underweight: "
                   + (", ".join(f"{s.asset_class} {s.drift:+.1%}" for s in under)
                      or "none")
                   + ". Whether the drift is worth correcting yet is "
                     "rebalancing-rules, a separate decision from whether the "
                     "target itself is right."))
    if g.known and g.within is False:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"Held equity {g.actual:.0%} sits outside the "
                     f"{g.low:.0%}-{g.high:.0%} reference band",
            detail=f"Horizon {g.years:.0f} years. The band is a convention, not "
                   "a calculation; anywhere inside it is a defensible policy."))
    taxable_income_assets = sum(
        h.value for h in loc.inv.holdings
        if h.asset_class in _port.INCOME_CLASSES and h.account_type == _port.TAXABLE)
    sheltered_equity = sum(
        h.value for h in loc.inv.holdings
        if h.asset_class in _port.EQUITY_CLASSES
        and h.account_type == _port.TAX_DEFERRED)
    if taxable_income_assets and sheltered_equity:
        swap = min(taxable_income_assets, sheltered_equity)
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"Up to {_money(swap)} of location swap available with no "
                     "allocation change",
            detail=f"{_money(taxable_income_assets)} of income-producing assets "
                   f"sit in taxable while {_money(sheltered_equity)} of equity "
                   "sits in tax-deferred; swapping changes no risk and nothing "
                   "on any statement changes size."))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Allocation in band, glide path agrees, location correct"
    return out


# rebalancing-rules: mirrors run.py build lines 18-26 calling portfolio.review_allocation and portfolio.rebalance_plan; tier because a fired rule is real but neither expiring nor priced in $/yr (trade sizes are correction sizes, not costs), so optimise, while the runner's own next-review deadline passes through as closing with days_to_expiry.
def _rebalancing_rules(data: dict) -> Outcome:
    skill = "rebalancing-rules"
    rows = F._dig(data, "household.balance_sheet") or []
    a = _port.review_allocation(rows, F._dig(data, "portfolio.target_allocation"))
    plan = _port.rebalance_plan(
        a,
        policy=F._dig(data, "portfolio.rebalancing.policy"),
        last_reviewed=F._dig(data, "portfolio.rebalancing.last_reviewed"),
        as_of=F.as_of(data),
        annual_contributions=F._dig(data, "portfolio.annual_contributions"),
    )
    if not a.total:
        return act(skill, "No classified holdings, so no drift can be computed",
                   TIER_OPTIMISE,
                   detail="Add asset_class to the balance sheet before this rule "
                          "can be applied.")
    out = Outcome(skill=skill, status="ok", headline="")
    if plan.triggered:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"The rule fires: {_money(plan.buys)} of buying restores "
                     f"the target, {_money(plan.taxable_sale_needed)} of it via "
                     "taxable sale",
            detail=f"{len(a.breached)} class(es) breached their band. Exhaust "
                   "new contributions and sheltered accounts first; the taxable "
                   "sale is the part with a tax cost and goes last."))
    nr = plan.next_review
    if (nr is not None and nr.on is not None
            and (nr.passed or (nr.days_remaining is not None
                               and nr.days_remaining <= CLOSING_WINDOW_DAYS))):
        if nr.passed:
            headline = (f"Rebalancing review overdue by "
                        f"{abs(nr.days_remaining)} days")
        else:
            headline = (f"Rebalancing review due in "
                        f"{nr.days_remaining} days")
        out.actions.append(Action(
            skill=skill, tier=TIER_CLOSING,
            headline=headline,
            days_to_expiry=nr.days_remaining,
            detail="A rule nobody runs is indistinguishable from no rule."))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "The rule says do nothing; every class is inside its band"
    return out


# wash-sale-policy: mirrors run.py build lines 18-27 calling portfolio.wash_sale_policy; tier because a replacement purchase inside a retirement account destroys the loss permanently with no basis adjustment (uncovered, irreversible) while other coverage gaps merely defer the loss or leave the rule unconfirmed (optimise); no Deadline objects pass through, so no closing tier here.
def _wash_sale_policy(data: dict) -> Outcome:
    skill = "wash-sale-policy"
    ws = F._dig(data, "portfolio.wash_sale") or {}
    p = _port.wash_sale_policy(
        ws.get("excluded_securities"),
        F._dig(data, "household.balance_sheet") or [],
        as_of=F.as_of(data),
        provider=ws.get("direct_index_provider"),
        continuous=ws.get("harvesting_continuous"),
        spouse_accounts_covered=ws.get("spouse_accounts_covered"),
    )
    out = Outcome(skill=skill, status="ok", headline="")
    if not p.accounts:
        return act(skill, "No account coverage recorded, so the policy cannot "
                          "be shown to reach beyond the harvesting account",
                   TIER_OPTIMISE,
                   detail="Add account_type and wash_sale_policy_applied to "
                          "every balance-sheet row. Unknown here is the exact "
                          "state in which the expensive version of this "
                          "mistake occurs.")
    for ac in sorted(p.retirement_gaps, key=lambda a: a.name):
        out.actions.append(Action(
            skill=skill, tier=TIER_UNCOVERED,
            headline=f"`{ac.name}` is outside the exclusion list; a purchase "
                     "there kills the loss permanently",
            irreversible=True,
            detail="Under Rev. Rul. 2008-5 no basis adjustment is available in "
                   "an IRA. An ordinary wash sale defers the loss; this one "
                   "deletes it, and automatic contributions nobody was "
                   "watching are the usual cause."))
    for ac in sorted((a for a in p.gaps if not a.is_retirement),
                     key=lambda a: a.name):
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"`{ac.name}` is not covered by the exclusion list",
            detail="Coverage recorded as unknown counts as no coverage: nobody "
                   "has checked. No retirement account is among these, which "
                   "removes the worst case but not the rule."))
    if ws.get("spouse_accounts_covered") is False:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="A spouse's accounts are recorded as not covered",
            detail="A purchase by a spouse triggers the wash sale just as one "
                   "by the taxpayer does, and cross-broker it is invisible on "
                   "both 1099-Bs."))
    elif ws.get("spouse_accounts_covered") is None:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="Whether a spouse's accounts are covered is not recorded",
            detail="Purchases by a spouse count; this needs an answer rather "
                   "than an assumption."))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Every recorded account is covered by the exclusion list"
    return out


# charitable-giving-strategy: mirrors run.py build lines 18-34 (charity.review_gifts), 72-94 (charity.best_bunch), 108-119 (charity.check_limits) and 121-126 (charity.qcd); tier because avoided gains, bunching benefit and QCD availability are real and priced but one-time or window-sized rather than expiring or annual drags, so optimise with the priced figure in impact_annual and its basis in detail.
def _charitable_giving_strategy(data: dict) -> Outcome:
    skill = "charitable-giving-strategy"
    members = F._dig(data, "household.members") or []
    adults = [x for x in members if x.get("role") in ("primary", "spouse")]
    ages = [x.get("age") for x in adults if x.get("age") is not None]
    marginal = float(F._dig(data, "assumptions.marginal_tax_rate"))
    investable = (F.tier_total(data, F.LIQUID)
                  + F.tier_total(data, F.AGE_RESTRICTED)
                  + F.tier_total(data, F.ILLIQUID))
    agi = F._dig(data, "household.agi")
    if agi is None:
        agi = F.household_income(data)
    holdings = F._dig(data, "charity.candidate_holdings") or []
    r = _charity.review_gifts(holdings,
                       ltcg_rate=F._dig(data, "assumptions.ltcg_rate"),
                       niit_rate=F._dig(data, "assumptions.niit_rate"),
                       investable=investable or None)
    out = Outcome(skill=skill, status="ok", headline="")
    if r.total_avoided > 0:
        best = r.best
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"{_money(r.total_avoided)} of gains tax avoided by "
                     "giving in kind rather than selling first",
            detail=(f"Best gift: {best.name}. " if best is not None else "")
                   + "One-time saving per gift, not an annual figure. "
                     "Transfer the shares; a sale the day before realises the "
                     "gain and there is no way back from it."))
    losses = sorted(l.name for l in r.lines if l.at_a_loss)
    if losses:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"Sell first, donate cash: {', '.join(losses)}",
            detail="Donating a loss position deducts the value and forfeits "
                   "the loss permanently. Sell, book the loss against other "
                   "gains, donate the proceeds: the charity receives the same "
                   "amount and the loss survives."))
    standard = F._dig(data, "assumptions.standard_deduction")
    annual_gift = F._dig(data, "charity.annual_gift")
    other = F._dig(data, "assumptions.other_itemized_deductions")
    if standard is not None and annual_gift is not None and other is not None:
        p = _charity.best_bunch(standard_deduction=float(standard),
                         other_itemized=float(other),
                         annual_gift=float(annual_gift),
                         marginal_rate=marginal)
        if p.worth_it:
            out.actions.append(Action(
                skill=skill, tier=TIER_OPTIMISE,
                impact_annual=(p.benefit / p.years) if p.years else p.benefit,
                headline=f"Bunching {p.years} years of giving into one is "
                         f"worth {_money(p.benefit)}",
                detail=f"{_money(p.extra_deduction)} of additional deduction "
                       f"over the {p.years}-year window at a {marginal:.0%} "
                       "marginal rate; impact shown annualised. A "
                       "donor-advised fund separates the deduction from the "
                       "grant so the charity's cash flow need not absorb the "
                       "bunching."))
        appreciated = min(float(annual_gift) * p.years,
                          sum(l.value for l in r.lines if not l.at_a_loss)) \
            if r.lines else 0.0
        c = _charity.check_limits(agi=float(agi),
                           cash_gift=max(0.0, float(annual_gift) * p.years
                                         - appreciated),
                           appreciated_gift=appreciated)
        if c.appreciated_excess > 0 or c.cash_excess > 0:
            out.actions.append(Action(
                skill=skill, tier=TIER_OPTIMISE,
                headline=f"{_money(c.appreciated_excess + c.cash_excess)} of "
                         "the bunched gift exceeds its AGI limit",
                detail=f"Cash and appreciated property carry different limits; "
                       f"the excess carries forward {_charity.CARRYFORWARD_YEARS} "
                       "years and then expires unused. Splitting the gift "
                       "across two tax years is usually better than relying "
                       "on it."))
    q = _charity.qcd(age=max(ages) if ages else None,
              annual_limit=F._dig(data, "assumptions.qcd_annual_limit"),
              rmd_applies=F._dig(data, "household.rmd_applies"))
    if q.eligible:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="Qualified charitable distributions are available; give "
                     "from the IRA",
            detail="A QCD never enters AGI, which beats a deduction, and it "
                   "counts toward the required minimum distribution. Make the "
                   "QCD before taking any other distribution for the year."))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "No charitable lever pays: nothing to give in kind, " \
                       "bunching gains nothing, no QCD available"
    return out


# 1031-exchange-modeling: mirrors run.py build lines 18-26 calling realestate.model_exchange; tier because recognised boot tax is real and priced but one-time (optimise with the tax in impact_annual and its one-time basis in detail), while the runner's own 45/180-day clocks pass through as closing with days_to_expiry, and a passed identification window is irreversible.
def _x1031_exchange_modeling(data: dict) -> Outcome:
    skill = "1031-exchange-modeling"
    r = _re.model_exchange(
        F._dig(data, "real_estate.exchange") or {},
        as_of=F.as_of(data),
        recapture_rate=F._dig(data, "assumptions.depreciation_recapture_rate"),
        ltcg_rate=F._dig(data, "assumptions.ltcg_rate"),
        niit_rate=F._dig(data, "assumptions.niit_rate"),
        state_rate=F._dig(data, "assumptions.state_tax_rate"),
        discount_rate=F._dig(data, "assumptions.expected_return_apr"),
    )
    out = Outcome(skill=skill, status="ok", headline="")
    if r.identify_by is not None and r.close_by is not None:
        if (r.days_to_identify is not None
                and (r.days_to_identify < 0
                     or r.days_to_identify <= CLOSING_WINDOW_DAYS)):
            if r.days_to_identify < 0:
                headline = (f"Identification window passed on "
                            f"{r.identify_by.isoformat()}; model as a taxable "
                            "sale")
            else:
                headline = (f"Identify in writing to the QI by "
                            f"{r.identify_by.isoformat()} "
                            f"({r.days_to_identify} days left)")
            out.actions.append(Action(
                skill=skill, tier=TIER_CLOSING,
                headline=headline,
                days_to_expiry=r.days_to_identify,
                irreversible=(r.days_to_identify < 0),
                detail="Both clocks run from the relinquished closing in "
                       "calendar days and neither is extendable. Engage the "
                       "qualified intermediary before closing; it cannot be "
                       "fixed afterwards."))
        if (r.days_to_close is not None
                and (r.days_to_close < 0
                     or r.days_to_close <= CLOSING_WINDOW_DAYS)):
            if r.days_to_close < 0:
                headline = (f"Closing window passed on "
                            f"{r.close_by.isoformat()}")
            else:
                headline = (f"Close by {r.close_by.isoformat()} "
                            f"({r.days_to_close} days left)")
            out.actions.append(Action(
                skill=skill, tier=TIER_CLOSING,
                headline=headline,
                days_to_expiry=r.days_to_close,
                irreversible=(r.days_to_close < 0),
                detail="The 180 days shorten to the return due date for the "
                       "year of sale if earlier; extend the return if a Q4 "
                       "sale would otherwise truncate this."))
    if r.recognized_gain > 0:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"{_money(r.recognized_gain)} of gain is recognised now "
                     f"on {_money(r.cash_boot + r.debt_boot)} of boot",
            detail=f"{_money(r.deferred_gain)} defers. One-time tax on the "
                   "recognised gain, not an annual figure; injecting cash or "
                   "taking on replacement debt offsets debt boot dollar for "
                   "dollar."))
    elif not r.fully_deferred and r.total_gain > 0:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline="Full deferral fails the rule of thumb",
            detail=f"Buy replacement property of equal or greater value "
                   f"({_money(r.amount_realized)}) and reinvest all net "
                   f"equity ({_money(r.net_equity)})."))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    elif r.fully_deferred:
        out.headline = (f"Full deferral: {_money(r.total_gain)} of gain "
                        "defers into the replacement property")
    else:
        out.headline = "No gain is recognised and the deferral rule is satisfied"
    return out


# rental-deal-underwriting: mirrors run.py build line 22 calling realestate.underwrite once per deal; tier because a sub-floor DSCR is a financing verdict that is real but neither expiring nor an annual cost on money already held, so optimise with one action per failing deal.
def _rental_deal_underwriting(data: dict) -> Outcome:
    skill = "rental-deal-underwriting"
    deals = [_re.underwrite(d) for d in (F._dig(data, "real_estate.deals") or [])]
    if not deals:
        return act(skill, "No deals recorded under real_estate.deals",
                   TIER_OPTIMISE)
    fails = sorted((u for u in deals if u.financeable is False),
                   key=lambda u: u.label)
    if not fails:
        return ok(skill, f"All {len(deals)} deals clear the "
                         f"{_re.DSCR_LENDER_FLOOR:.2f} DSCR floor")
    out = Outcome(skill=skill, status="action",
                  headline=f"{len(fails)} of {len(deals)} deals fail the "
                           f"{_re.DSCR_LENDER_FLOOR:.2f} DSCR floor")
    for u in fails:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"{u.label}: DSCR {u.dscr:.2f} is below the floor; a "
                     "larger down payment, a lower price, or walk away",
            detail="At that leverage the property does not service its own "
                   "debt and the borrower's salary is the reserve. Every "
                   "figure is pre-investor-tax and nominal; no after-tax "
                   "return is available until passive-loss-eligibility says a "
                   "section 469 door is open."))
    return out


# passive-loss-eligibility: mirrors run.py build lines 18-29 calling realestate.assess_gate; tier because suspended losses defer to passive income or disposition rather than vanishing, so they are real and priced but neither expiring nor unrecoverable, hence optimise with this year's suspended loss in impact_annual and one action per shut activity.
def _passive_loss_eligibility(data: dict) -> Outcome:
    skill = "passive-loss-eligibility"
    part = F._dig(data, "real_estate.participation") or {}
    g = _re.assess_gate(
        F._dig(data, "real_estate.activities") or [],
        magi=float(part.get("magi")),
        active_participation=part.get("active_participation"),
        hours_real_property=part.get("hours_real_property"),
        hours_all_work=part.get("hours_all_work"),
        grouping_election=bool(part.get("grouping_election")),
        allowance=F._dig(data, "assumptions.passive_loss_allowance"),
        phaseout_start=F._dig(data, "assumptions.passive_loss_phaseout_start"),
        phaseout_end=F._dig(data, "assumptions.passive_loss_phaseout_end"),
    )
    if not g.activities:
        return ok(skill, "No rental activities recorded, so there is no loss "
                         "to gate")
    shut = sorted((a for a in g.activities if not a.open),
                  key=lambda a: a.label)
    if not shut:
        return ok(skill, f"A door is open on {len(g.activities)} of "
                         f"{len(g.activities)} activities")
    out = Outcome(skill=skill, status="action",
                  headline=f"No door is open on {len(shut)} of "
                           f"{len(g.activities)} activities")
    for a in shut:
        out.actions.append(Action(
            skill=skill, tier=TIER_OPTIMISE,
            headline=f"{a.label}: {_money(a.suspended_this_year)} of loss "
                     "suspends instead of offsetting wage income this year",
            detail="Suspended losses carry forward indefinitely. They offset "
                   "future passive income, and the whole accumulated balance "
                   "is released in full on a fully taxable disposition of the "
                   "activity to an unrelated party."))
    return out


# feie-vs-ftc: mirrors run.py lines 22-44 calling X.parse_brackets/X.compare; tier drag because the module prices the annual tax gap between the two elections.
def _feie_vs_ftc(data: dict) -> "Outcome":
    skill = "feie-vs-ftc"
    e = F._dig(data, "expat") or {}
    members = F._dig(data, "household.members") or []
    status = e.get("filing_status") or (
        "married_joint" if any(x.get("role") == "spouse" for x in members)
        else "single")
    kids = [x for x in members
            if x.get("role") == "dependent"
            and (x.get("age") is not None and x["age"] < _expat.CTC_QUALIFYING_AGE)]
    assumptions = F._dig(data, "assumptions") or {}
    try:
        brackets = _expat.parse_brackets(assumptions, status)
    except _expat.BracketError:
        brackets = None
    c = _expat.compare(
        e,
        brackets=brackets,
        exclusion_cap=assumptions.get("feie_exclusion_cap"),
        children_under_17=len(kids),
        refundable_ctc_per_child=assumptions.get("additional_ctc_per_child"),
    )
    if not c.determinable:
        return act(skill, "FEIE vs FTC comparison cannot be run from the facts recorded",
                   TIER_OPTIMISE, detail="; ".join(c.findings))
    if c.recommendation == "too_close":
        return ok(skill, "No recommendation between the exclusion and the credit on the arithmetic")
    leader = "credit (Form 1116)" if c.recommendation == "ftc" else "exclusion (Form 2555)"
    gap = abs(c.adjusted_delta)
    return act(skill, f"The {leader} is cheaper by {_money(gap)}/yr once valued adjustments apply",
               TIER_DRAG, impact_annual=gap,
               detail="; ".join(c.findings))


# foreign-presence-tests: mirrors run.py lines 17-22, 41, 80-83, 104 calling P.build_ledger/P.physical_presence/P.bona_fide/P.destination_test; tier optimise because a day-count shortfall or failed check is neither dated-expiring nor priced.
def _foreign_presence_tests(data: dict) -> "Outcome":
    skill = "foreign-presence-tests"
    spec = F._dig(data, "presence") or {}
    led = _presence.build_ledger(spec.get("days"))
    as_of = F.as_of(data)
    tax_year = spec.get("tax_year") or (as_of.year if as_of else None)
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    r = _presence.physical_presence(led, tax_year=tax_year)
    b = _presence.bona_fide(spec.get("bona_fide"),
                             us_status=primary.get("us_status"),
                             citizenship=primary.get("citizenship"),
                             tax_year=tax_year)
    t = _presence.destination_test(led, spec.get("destination"))
    out = Outcome(skill=skill, status="ok", headline="")
    if not r.determinable:
        out.actions.append(Action(skill=skill, tier=TIER_OPTIMISE,
                                  headline="Physical Presence Test cannot be evaluated from the ledger",
                                  detail="; ".join(r.findings + led.findings)))
    elif not r.passes:
        out.actions.append(Action(skill=skill, tier=TIER_OPTIMISE,
                                  headline=f"Physical Presence Test not met — short by {r.shortfall} day(s) on the best 12-month window",
                                  detail="; ".join(r.findings)))
    for chk in sorted(b.checks, key=lambda x: x.label):
        if chk.state == "fail":
            out.actions.append(Action(skill=skill, tier=TIER_OPTIMISE,
                                      headline=f"Bona fide residence check failed: {chk.label}",
                                      detail=chk.detail))
    if t.crosses:
        out.actions.append(Action(skill=skill, tier=TIER_OPTIMISE,
                                  headline=f"Destination residency threshold crossed in {t.country}",
                                  detail="; ".join(t.findings)))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Presence ledger supports the 330-day test with no failed residence checks"
    return out


# foreign-reporting-audit: mirrors run.py lines 20-28 calling R.audit; tier uncovered for blocker-severity required filings because a missed required filing is penalty exposure that cannot be self-insured after the fact, optimise for gap-severity unknowns.
def _foreign_reporting_audit(data: dict) -> "Outcome":
    skill = "foreign-reporting-audit"
    members = F._dig(data, "household.members") or []
    adults = [x for x in members if x.get("role") in ("primary", "spouse")]
    status = "married_joint" if len(adults) > 1 else "single"
    accounts = F._dig(data, "foreign_accounts")
    a = _reporting.audit(accounts, filing_status=status,
                         tax_home_abroad=bool(F._dig(data, "household.tax_home_abroad")),
                         foreign_gifts_received=F._dig(data, "foreign_gifts_received"))
    out = Outcome(skill=skill, status="ok", headline="")
    for f in sorted(a.findings, key=lambda x: (x.form, x.detail)):
        if f.severity == "blocker":
            out.actions.append(Action(skill=skill, tier=TIER_UNCOVERED,
                                      headline=f"{f.form}: required filing on what is recorded",
                                      detail=f.detail, irreversible=True))
        elif f.severity == "gap":
            out.actions.append(Action(skill=skill, tier=TIER_OPTIMISE,
                                      headline=f"{f.form}: cannot be determined — record what is missing",
                                      detail=f.detail))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "No foreign reporting obligation on what is recorded"
    return out


# foreign-pension-classification: mirrors run.py line 25 calling N.audit; tier uncovered for problematic buckets because 3520/3520-A penalty exposure cannot be self-insured after the fact, optimise for unknown-bucket schemes.
def _foreign_pension_classification(data: dict) -> "Outcome":
    skill = "foreign-pension-classification"
    a = _pension.audit(F._dig(data, "foreign_pensions"))
    if not a.classifications:
        return act(skill, "No foreign pension schemes recorded — confirm absence rather than assuming it",
                   TIER_OPTIMISE, detail="; ".join(a.findings))
    out = Outcome(skill=skill, status="ok", headline="")
    for c in sorted(a.classifications, key=lambda x: x.label):
        if c.bucket == _pension.UNKNOWN_BUCKET:
            out.actions.append(Action(skill=skill, tier=TIER_OPTIMISE,
                                      headline=f"{c.label}: scheme not in the table — a preparer has to place it",
                                      detail="; ".join(c.findings)))
        elif c.problematic:
            out.actions.append(Action(skill=skill, tier=TIER_UNCOVERED,
                                      headline=f"{c.label}: {c.bucket} — {', '.join(c.forms)}",
                                      detail="; ".join(c.drivers + c.findings)))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "Every recorded scheme is treaty-protected"
    return out


# cfc-gilti-screen: mirrors run.py line 27 calling X.cfc_screen; tier drag for CFC/other-form entities because the module prices the per-form per-year non-filing penalty, optimise for undetermined or shareholder-only positions.
def _cfc_gilti_screen(data: dict) -> "Outcome":
    skill = "cfc-gilti-screen"
    s = _expat.cfc_screen(F._dig(data, "expat.foreign_entities"))
    out = Outcome(skill=skill, status="ok", headline="")
    for e in sorted(s.entities, key=lambda x: x.name):
        if e.is_cfc:
            out.actions.append(Action(
                skill=skill, tier=TIER_DRAG,
                headline=f"{e.name} is a CFC — {', '.join(e.forms)}",
                impact_annual=_expat.FORM_5471_PENALTY * max(1, len(e.forms)),
                detail="; ".join(e.findings)))
        elif e.kind in _expat.OTHER_FORMS and e.forms:
            out.actions.append(Action(
                skill=skill, tier=TIER_DRAG,
                headline=f"{e.name}: {e.forms[0]} applies outside the CFC rules",
                impact_annual=_expat.FORM_5471_PENALTY * max(1, len(e.forms)),
                detail="; ".join(e.findings)))
        elif e.is_cfc is None:
            out.actions.append(Action(
                skill=skill, tier=TIER_OPTIMISE,
                headline=f"{e.name}: ownership not recorded — CFC status cannot be determined",
                detail="; ".join(e.findings)))
        elif e.is_us_shareholder:
            out.actions.append(Action(
                skill=skill, tier=TIER_OPTIMISE,
                headline=f"{e.name}: US-shareholder position but not a CFC — confirm filing categories",
                detail="; ".join(e.findings)))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = "No CFC on the entities recorded"
    return out


# pfic-divest-or-comply: mirrors run.py lines 28-48 calling P.RateSeries.from_facts/P.divest_or_comply with the pfic_holdings-or-foreign_accounts fallback; tier drag because the module prices the per-fund per-year compliance cost, optimise where unpriced or regime-unknown.
def _pfic_divest_or_comply(data: dict) -> "Outcome":
    skill = "pfic-divest-or-comply"
    as_of = F.as_of(data)
    if as_of is None:
        return act(skill, "PFIC holding period cannot be measured — meta.as_of is missing",
                   TIER_OPTIMISE)
    holdings = F._dig(data, "pfic_holdings")
    if holdings is None:
        holdings = [a for a in (F._dig(data, "foreign_accounts") or [])
                    if a.get("kind") in ("foreign_mutual_fund", "foreign_etf",
                                         "unit_trust", "investment_linked_policy")]
    d = _pfic.divest_or_comply(
        holdings,
        rates=_pfic.RateSeries.from_facts(F._dig(data, "assumptions.pfic_rates")),
        as_of=as_of,
        annual_cost_per_form=F._dig(data, "assumptions.pfic_form_cost_annual"),
        ltcg_rate=F._dig(data, "assumptions.ltcg_rate"),
    )
    if not d.funds:
        return act(skill, "No PFIC holdings recorded — confirm absence rather than assuming it",
                   TIER_OPTIMISE, detail="; ".join(d.findings))
    out = Outcome(skill=skill, status="ok", headline="")
    if d.annual_compliance is not None:
        detail = "; ".join(d.findings)
        if d.charge is not None and d.charge.computable:
            detail = f"Exit charge {_money(d.charge.total)}; breakeven {d.breakeven_years:.1f} years. " + detail if d.breakeven_years is not None else detail
        out.actions.append(Action(skill=skill, tier=TIER_DRAG,
                                  headline=f"{d.forms_per_year} Form 8621(s) a year cost {_money(d.annual_compliance)}/yr — divest or comply",
                                  impact_annual=d.annual_compliance, detail=detail))
    elif d.charge is not None and d.charge.computable:
        out.actions.append(Action(skill=skill, tier=TIER_OPTIMISE,
                                  headline=f"PFIC exit charge {_money(d.charge.total)} — get a per-form quote to complete the comparison",
                                  detail="; ".join(d.findings)))
    else:
        out.actions.append(Action(skill=skill, tier=TIER_OPTIMISE,
                                  headline="PFIC holdings recorded but neither priced nor comparable — record values, bases and dates",
                                  detail="; ".join(d.findings)))
    for f in sorted(d.funds, key=lambda x: x.name):
        if not f.availability.determinable:
            out.actions.append(Action(skill=skill, tier=TIER_OPTIMISE,
                                      headline=f"{f.name}: regime availability unknown — ask the administrator in writing",
                                      detail="; ".join(f.availability.reasons)))
    out.status = "action"
    out.headline = out.actions[0].headline
    return out


# state-domicile-exit: mirrors run.py lines 16-31 calling P.build_ledger/P.count_present_days/X.domicile_exit; tier optimise throughout because run.py lines 77-102 render a severance checklist with no verdict threshold, priced figure or deadline object, so each outstanding step is its own action.
def _state_domicile_exit(data: dict) -> "Outcome":
    skill = "state-domicile-exit"
    spec = F._dig(data, "state_exit") or {}
    as_of = F.as_of(data)
    year = spec.get("count_year") or (as_of.year if as_of else None)
    days = None
    led = _presence.build_ledger(F._dig(data, "presence.days"))
    if year and led.stays:
        days = _presence.count_present_days(
            led, start=_dt.date(year, 1, 1), end=_dt.date(year, 12, 31),
            state=spec.get("from_state"))
    x = _expat.domicile_exit(
        spec, days_in_state=days,
        new_domicile_established=spec.get("new_domicile_established"))
    out = Outcome(skill=skill, status="ok", headline="")
    if spec.get("new_domicile_established") is False:
        out.actions.append(Action(skill=skill, tier=TIER_OPTIMISE,
                                  headline="No new domicile established — the exit claim fails on that alone",
                                  detail="; ".join(x.findings)))
    for k, detail in x.outstanding:
        out.actions.append(Action(skill=skill, tier=TIER_OPTIMISE,
                                  headline=f"Severance step outstanding: {k}",
                                  detail=detail))
    if x.unrecorded:
        out.actions.append(Action(skill=skill, tier=TIER_OPTIMISE,
                                  headline=f"{len(x.unrecorded)} severance fact(s) unrecorded — unrecorded is not done",
                                  detail="; ".join(d for _, d in x.unrecorded)))
    if out.actions:
        out.status = "action"
        out.headline = out.actions[0].headline
    else:
        out.headline = f"Severance checklist complete {x.score}"
    return out


# cost-segregation-screen: mirrors run.py build() lines 53-71 calling _re.assess_gate
# (via _gates, lines 17-49) and _re.screen_cost_segregation; tier optimise because
# the benefit is a one-time timing PV, not an ongoing annual drag, and runner
# lines 144-146 state a prior-year method change removes any hurry (not closing);
# it is not a protection gap (not uncovered). No deadline objects in the runner.
def _cost_segregation_screen(data: dict) -> "Outcome":
    skill = "cost-segregation-screen"
    acts_in = F._dig(data, "real_estate.activities")
    part = F._dig(data, "real_estate.participation") or {}
    gates: dict = {}
    if acts_in and part.get("magi") is not None:
        g = _re.assess_gate(
            acts_in,
            magi=float(part["magi"]),
            active_participation=part.get("active_participation"),
            hours_real_property=part.get("hours_real_property"),
            hours_all_work=part.get("hours_all_work"),
            grouping_election=bool(part.get("grouping_election")),
            allowance=F._dig(data, "assumptions.passive_loss_allowance"),
            phaseout_start=F._dig(data, "assumptions.passive_loss_phaseout_start"),
            phaseout_end=F._dig(data, "assumptions.passive_loss_phaseout_end"),
        )
        gates = {a.label: a.open for a in g.activities}
    rows = F._dig(data, "real_estate.cost_segregation") or []
    if isinstance(rows, dict):
        rows = [rows]
    screens = [
        _re.screen_cost_segregation(
            row,
            gate_open=gates.get(row.get("label")),
            marginal_rate=F._dig(data, "assumptions.marginal_tax_rate"),
            bonus_rate=F._dig(data, "assumptions.bonus_depreciation_rate"),
            discount_rate=F._dig(data, "assumptions.expected_return_apr"),
            state_rate=F._dig(data, "assumptions.state_tax_rate"),
        )
        for row in rows
    ]
    if not screens:
        return ok(skill, "No properties recorded for cost segregation screening")
    out = Outcome(skill=skill, status="ok", headline="")
    for s in sorted(screens, key=lambda s: s.label):
        if s.worth_commissioning:
            out.actions.append(Action(
                skill=skill, tier=TIER_OPTIMISE,
                headline=(f"{s.label} clears the "
                          f"{_re.MIN_BENEFIT_TO_COST:.0f}x benefit-to-fee bar — "
                          "commission a study"),
                detail=(f"Present-value timing benefit against a study fee of "
                        f"{s.benefit_to_cost:.1f}x at the conservative end of "
                        "the reclassification range.")))
    if out.actions:
        out.status = "action"
        out.headline = (f"{len(out.actions)} of {len(screens)} properties clear "
                        "the benefit-to-fee bar for a study")
    else:
        out.headline = ("No property clears the benefit-to-fee bar for a study "
                        "at the conservative end of the range")
    return out


# cross-border-healthcare: mirrors run.py build() lines 25-31 calling
# _xb.part_b_decision; tier drag for keep (ongoing premiums priced per year),
# optimise for drop (a one-time enrolment decision, not an annual cost) and for
# cannot_determine (the deciding intention is unrecorded — unknown is not zero).
# The runner yields no deadline objects, so no days_to_expiry.
def _cross_border_healthcare(data: dict) -> "Outcome":
    skill = "cross-border-healthcare"
    med = F._dig(data, "crossborder.medicare") or {}
    d = _xb.part_b_decision(
        months_abroad=float(med.get("months_abroad_planned")),
        standard_premium_monthly=float(med.get("standard_premium_monthly")),
        will_return=med.get("will_return_to_us"),
        years_after_return=med.get("years_after_return"),
    )
    if d.months_abroad <= 0:
        return ok(skill, "No months abroad planned — no Part B decision to make")
    if d.recommendation == "keep":
        return act(
            skill,
            f"Keep Part B while abroad ({d.months_abroad:.0f} months)",
            TIER_DRAG, impact_annual=d.standard_premium_monthly * 12,
            detail=(f"Premiums for cover that cannot be used abroad, weighed "
                    f"against a permanent penalty over the years back in the "
                    f"US. See the skill report for the keep-vs-penalty totals."))
    if d.recommendation == "drop":
        return act(
            skill, "Dropping Part B is cheaper on these numbers", TIER_OPTIMISE,
            detail=(f"Penalty over the years back in the US is priced below "
                    f"the keep cost in the skill report; re-enrolment is only "
                    f"in the General Enrolment Period and Medigap guaranteed "
                    f"issue may be lost."))
    return act(
        skill,
        "Part B keep-or-drop cannot be decided — record whether you will return to the US",
        TIER_OPTIMISE,
        detail=("The keep cost is linear in time abroad while the penalty cost "
                "is time abroad multiplied by years lived afterwards, so the "
                "intention decides the comparison."))


# geo-arbitrage-model: mirrors run.py build() calling F.retirement_assets and
# _xb.model; tier drag because the verdict is priced dollars per year
# (baseline burn minus blended burn, cutting the portfolio target); ok when the
# split saves nothing. The runner yields no deadline objects, no days_to_expiry.
def _geo_arbitrage_model(data: dict) -> "Outcome":
    skill = "geo-arbitrage-model"
    assets = F.retirement_assets(data).included
    savings = float(F._dig(data, "retirement.annual_savings"))
    p = _xb.model(
        F._dig(data, "crossborder.locations") or [],
        assets=assets,
        annual_savings=savings,
        fixed_annual=float(F._dig(data, "crossborder.fixed_annual_costs") or 0),
        duplicate_housing=F._dig(data, "crossborder.duplicate_housing"),
        savings_by_year=_retirement_savings_path(data, savings),
    )
    if not p.legs:
        return ok(skill, "No locations recorded, so there is nothing to blend")
    if p.annual_saving > 0:
        return act(
            skill,
            "Split-living plan saves against a full year at the dearest location",
            TIER_DRAG, impact_annual=p.annual_saving,
            detail=(f"Blended burn against a full year at the dearest leg; "
                    f"the saving cuts the portfolio target. Plan on the "
                    f"FX-stressed row — the saving is denominated in a "
                    f"currency the household neither earns nor holds."))
    return ok(skill, "Split arrangement costs no less than a full year at the dearest location")


# roth-portability-check: mirrors run.py build() lines 25-31 calling
# _xb.portability; tier uncovered when any destination inverts because converting
# buys an irreversible US tax bill for an exemption the destination will not
# grant (runner lines 33-36); impact_annual is the yearly US tax on the planned
# annual conversion where priced. Unknown destinations (not in the table) are an
# optimise action — unknown is not zero.
def _roth_portability_check(data: dict) -> "Outcome":
    skill = "roth-portability-check"
    p = _xb.portability(
        F._dig(data, "crossborder.destinations") or [],
        roth_balance=F._dig(data, "crossborder.roth_balance"),
        traditional_balance=F._dig(data, "crossborder.traditional_balance"),
        planned_conversion=F._dig(data, "crossborder.planned_conversion_annual"),
        conversion_tax_rate=F._dig(data, "assumptions.marginal_tax_rate"),
    )
    if p.any_inverts:
        bad = sorted(d.label for d in p.destinations if d.inverts)
        return act(
            skill,
            ("At least one destination does not honour the Roth wrapper "
             f"({', '.join(bad)}) — halt conversions"),
            TIER_UNCOVERED, impact_annual=p.conversion_tax_now,
            irreversible=True,
            detail=("Converting now pays US tax today for an exemption the "
                    "destination may not grant, and the two tax events land in "
                    "different years so no relief mechanism bridges them."))
    if p.any_unknown:
        return act(
            skill,
            "At least one destination is not in the country table — verify treatment before converting",
            TIER_OPTIMISE,
            detail=("Absence from the table means nobody checked, not that the "
                    "treatment is benign. Take the question to a cross-border "
                    "tax professional; do not convert in the meantime."))
    return ok(skill, "No destination recorded here is known to tax Roth distributions")


def _financial_history_review(data: dict) -> Outcome:
    paths = [Path(path) for path in F._dig(data, "history.snapshot_files") or []]
    history = T.load_history(paths)
    return ok(
        "financial-history-review",
        f"{len(history.snapshots)} immutable history snapshot(s) available; "
        "run explicitly for trend decisions",
    )


def _tax_planning(data: dict) -> Outcome:
    skill = "tax-planning"
    plan = _taxplan.plan_from_facts(data)
    return ok(
        skill,
        f"{len(plan.opportunities)} tax-planning candidate(s) summarized; "
        "excluded from the action worklist to avoid duplicating the "
        "specialist skills",
    )


def _financial_scenario_planner(data: dict) -> Outcome:
    from . import scenario as _scenario  # noqa: PLC0415
    specs = _scenario.scenarios_from_facts(data)
    return ok(
        "financial-scenario-planner",
        f"{len(specs)} hypothetical scenario(s) recorded; excluded from the "
        "current-action worklist",
    )


def _job_loss_stress_test(data: dict) -> Outcome:
    from . import scenario as _scenario  # noqa: PLC0415
    count = sum(
        any(event.type == "employment_loss" for event in spec.events)
        for spec in _scenario.scenarios_from_facts(data)
    )
    return ok(
        "job-loss-stress-test",
        f"{count} job-loss stress case(s) recorded; hypothetical results are "
        "not current findings",
    )


def _windfall_deployment_planner(data: dict) -> Outcome:
    from . import scenario as _scenario  # noqa: PLC0415
    count = sum(
        any(event.type in ("cash_receipt", "asset_receipt")
            for event in spec.events)
        for spec in _scenario.scenarios_from_facts(data)
    )
    return ok(
        "windfall-deployment-planner",
        f"{count} windfall deployment case(s) recorded; hypothetical results "
        "are not current findings",
    )


ADAPTERS: dict[str, Callable[[dict], Outcome]] = {
    "cash-yield-review": _cash_yield,
    "conflict-check": _conflict_check,
    "disability-insurance-review": _disability,
    "1031-exchange-modeling": _x1031_exchange_modeling,
    "aca-subsidy-optimization": _aca_subsidy_optimization,
    "asset-allocation-review": _asset_allocation_review,
    "auto-insurance-review": _auto_insurance_review,
    "beneficiary-audit": _beneficiary_audit,
    "ca-condo-hoa-disclosure-review": _ca_condo_hoa_disclosure_review,
    "ca-sfh-disclosure-review": _ca_sfh_disclosure_review,
    "cfc-gilti-screen": _cfc_gilti_screen,
    "charitable-giving-strategy": _charitable_giving_strategy,
    "citizenship-status-review": _citizenship_status_review,
    "contribution-space-audit": _contribution_space_audit,
    "continuity-plan": _continuity_plan,
    "cost-segregation-screen": _cost_segregation_screen,
    "cross-border-healthcare": _cross_border_healthcare,
    "debt-payoff-priority": _debt_payoff_priority,
    "depreciation-election": _depreciation_election,
    "digital-estate": _digital_estate,
    "divorce-asset-split": _divorce_asset_split,
    "education-funding": _education_funding,
    "emergency-fund-sizing": _emergency_fund_sizing,
    "employer-concentration-risk": _employer_concentration_risk,
    "employer-match-audit": _employer_match_audit,
    "entity-structure-comparison": _entity_structure_comparison,
    "equity-comp-review": _equity_comp_review,
    "estate-document-review": _estate_document_review,
    "feie-vs-ftc": _feie_vs_ftc,
    "foreign-pension-classification": _foreign_pension_classification,
    "foreign-presence-tests": _foreign_presence_tests,
    "foreign-reporting-audit": _foreign_reporting_audit,
    "financial-history-review": _financial_history_review,
    "financial-scenario-planner": _financial_scenario_planner,
    "geo-arbitrage-model": _geo_arbitrage_model,
    "housing-affordability": _housing_affordability,
    "hsa-review": _hsa_review,
    "life-insurance-review": _life_insurance_review,
    "long-term-care-funding": _long_term_care_funding,
    "marriage-finance-merger": _marriage_finance_merger,
    "medicare-enrollment-timing": _medicare_enrollment_timing,
    "mortgage-review": _mortgage_review,
    "passive-loss-eligibility": _passive_loss_eligibility,
    "pfic-divest-or-comply": _pfic_divest_or_comply,
    "probate-exposure": _probate_exposure,
    "rebalancing-rules": _rebalancing_rules,
    "rent-vs-buy": _rent_vs_buy,
    "rental-deal-underwriting": _rental_deal_underwriting,
    "renters-homeowners-review": _renters_homeowners_review,
    "retirement-readiness": _retirement_readiness,
    "roth-conversion-window": _roth_conversion_window,
    "roth-portability-check": _roth_portability_check,
    "social-security-timing": _social_security_timing,
    "solo-retirement-plan-choice": _solo_retirement_plan_choice,
    "state-domicile-exit": _state_domicile_exit,
    "survivor-needs": _survivor_needs,
    "tax-planning": _tax_planning,
    "umbrella-liability": _umbrella_liability,
    "wash-sale-policy": _wash_sale_policy,
    "windfall-management": _windfall_management,
    "windfall-deployment-planner": _windfall_deployment_planner,
    "job-loss-stress-test": _job_loss_stress_test,
    "withdrawal-sequencing": _withdrawal_sequencing,
}
