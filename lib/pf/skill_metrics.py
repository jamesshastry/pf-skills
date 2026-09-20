"""First-release structured metric adapters for existing domain skills.

Each adapter calls the same pure domain function as the corresponding runner.
The time-series layer owns storage and comparison; these adapters only expose
stable IDs and bases.  Adding history support to a skill is therefore a small
registration here, not a second report or persistence system.
"""

from __future__ import annotations

from collections.abc import Callable

from . import cash as C
from . import concentration as CN
from . import disability as D
from . import education as E
from . import facts as F
from . import housing_affordability as H
from . import life as L
from . import retirement as R
from . import survivor as S
from . import tax_planning as TP
from . import timeseries as T


def _currency(data: dict) -> str:
    return str(F._dig(data, "meta.currency") or "")


def _metric(data: dict, metric_id: str, value: float | None, *, unit: str,
            basis: str, source: str, scenario: str = "current",
            entity_id: str | None = None, label: str | None = None,
            unknown_reason: str | None = None, assumptions=None):
    return T.analysis_metric(
        data, metric_id, value, unit=unit, basis=basis, scenario=scenario,
        source=source, currency=_currency(data) if unit == "currency" else None,
        entity_id=entity_id, display_label=label,
        unknown_reason=unknown_reason, assumptions=assumptions,
    )


def emergency_fund(data: dict) -> list[T.MetricObservation]:
    members = F._dig(data, "household.members") or []
    earners = [x for x in members if float(x.get("income_annual") or 0) > 0]
    variable = next((x.get("income_variable_share") for x in earners
                     if x.get("income_variable_share") is not None), None)
    reserve = F.reserve_assets(data)
    result = C.size_buffer(
        liquid=reserve.included,
        annual_spending=float(F._dig(data, "household.annual_spending")),
        earners=len(earners), has_dependents=bool(F.dependents(data)),
        variable_comp_share=variable,
    )
    assumptions = {
        "earners": len(earners), "dependents": bool(F.dependents(data)),
        "variable_comp_share": variable,
    }
    return [
        _metric(data, "emergency_fund.months_held", result.months_held,
                unit="months", basis=T.BASIS_NONMONETARY,
                source="emergency-fund-sizing", assumptions=assumptions),
        _metric(data, "emergency_fund.target", result.target,
                unit="currency", basis=T.BASIS_NOMINAL,
                source="emergency-fund-sizing", assumptions=assumptions),
        _metric(data, "emergency_fund.shortfall", result.shortfall,
                unit="currency", basis=T.BASIS_NOMINAL,
                source="emergency-fund-sizing", assumptions=assumptions),
    ]


def employer_concentration(data: dict) -> list[T.MetricObservation]:
    eq = F._dig(data, "equity_comp") or {}
    members = F._dig(data, "household.members") or []
    linked = [x for x in members if x.get("employer")]
    exposure = CN.assess_exposure(
        employer=eq.get("employer") or "the employer",
        income_from_employer=sum(float(x.get("income_annual") or 0)
                                 for x in linked),
        total_income=F.household_income(data),
        held_value=float(eq.get("held_value") or 0),
        unvested_value=float(eq.get("unvested_value") or 0),
        investable=(F.tier_total(data, F.LIQUID)
                    + F.tier_total(data, F.AGE_RESTRICTED)
                    + F.tier_total(data, F.ILLIQUID)),
        liquid=F.liquid(data),
        monthly_spending=float(F._dig(data, "household.annual_spending")) / 12,
        sell_at_vest=eq.get("sell_at_vest"),
    )
    joint = CN.joint_scenario(exposure)
    assumptions = {
        "decline": CN.JOINT_SCENARIO_DECLINE,
        "months": CN.JOINT_SCENARIO_MONTHS,
    }
    return [
        _metric(data, "employer_concentration.income_share",
                exposure.income_share, unit="ratio",
                basis=T.BASIS_NONMONETARY,
                source="employer-concentration-risk", assumptions=assumptions),
        _metric(data, "employer_concentration.asset_share",
                exposure.asset_share, unit="ratio",
                basis=T.BASIS_NONMONETARY,
                source="employer-concentration-risk", assumptions=assumptions),
        _metric(data, "employer_concentration.joint_loss", joint.total_loss,
                unit="currency", basis=T.BASIS_NOMINAL,
                source="employer-concentration-risk", assumptions=assumptions),
        _metric(data, "employer_concentration.runway_months",
                joint.runway_months, unit="months",
                basis=T.BASIS_NONMONETARY,
                source="employer-concentration-risk", assumptions=assumptions),
    ]


def _retirement_savings_path(data: dict, annual: float) -> list[float]:
    current = next((s for s in F._dig(data, "cash_flow.scenarios") or []
                    if s.get("kind") == "current"), {})
    return R.savings_path_from_obligations(
        annual, current.get("obligations") or [])


def retirement(data: dict) -> list[T.MetricObservation]:
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    spending = float(F._dig(data, "household.annual_spending"))
    savings = float(F._dig(data, "retirement.annual_savings"))
    classified = F.retirement_assets(data)
    if classified.unknown:
        reason = "retirement eligibility missing for: " + ", ".join(classified.unknown)
        return [
            _metric(data, "retirement.target_reached_age", None,
                    unit="years", basis=T.BASIS_NONMONETARY,
                    source="retirement-readiness", unknown_reason=reason),
        ]
    result = R.assess_readiness(
        annual_spending=spending, assets=classified.included,
        annual_savings=savings, current_age=primary.get("age"),
        savings_by_year=_retirement_savings_path(data, savings),
    )
    assumptions = {
        "real_return": result.real_return,
        "withdrawal_rate": result.withdrawal_rate,
    }
    return [
        _metric(data, "retirement.target", result.target,
                unit="currency", basis=T.BASIS_REAL,
                source="retirement-readiness", assumptions=assumptions),
        _metric(data, "retirement.target_reached_age", result.age_at_target,
                unit="years", basis=T.BASIS_NONMONETARY,
                source="retirement-readiness",
                unknown_reason=("target not reached within model horizon"
                                if result.age_at_target is None else None),
                assumptions=assumptions),
    ]


def housing_affordability(data: dict) -> list[T.MetricObservation]:
    try:
        result = H.assess(
            scenarios=F._dig(data, "cash_flow.scenarios") or [],
            purchase=F._dig(data, "housing.purchase") or {},
            monthly_rent=float(F._dig(data, "housing.monthly_rent")),
            balance_sheet=F._dig(data, "household.balance_sheet") or [],
            reserve_assets=F.reserve_assets(data),
            retirement_annual_savings=F._dig(data, "retirement.annual_savings"),
            household_income=F.household_income(data),
            household_income_components=F.household_income_components(data),
            affordability=F._dig(data, "housing.affordability") or {},
            transition=F._dig(data, "housing.transition") or {},
            rental_deals=F._dig(data, "real_estate.deals") or [],
            portfolio_wash_sale=F._dig(data, "portfolio.wash_sale"),
        )
    except H.ReconciliationError as exc:
        return [_metric(
            data, "housing.stress_price_ceiling", None, unit="currency",
            basis=T.BASIS_NOMINAL, source="housing-affordability",
            scenario="stress", unknown_reason=str(exc))]
    metrics = [
        _metric(data, "housing.current_price_ceiling",
                result.current_income_ceiling, unit="currency",
                basis=T.BASIS_NOMINAL, source="housing-affordability",
                scenario="current"),
        _metric(data, "housing.stress_price_ceiling",
                result.stress_tested_ceiling, unit="currency",
                basis=T.BASIS_NOMINAL, source="housing-affordability",
                scenario="stress"),
        _metric(data, "housing.liquidity_price_ceiling",
                result.liquidity_maximum, unit="currency",
                basis=T.BASIS_NOMINAL, source="housing-affordability",
                scenario="current"),
    ]
    scenario_ids = {
        str(row.get("label")): row.get("id")
        for row in F._dig(data, "cash_flow.scenarios") or []
    }
    for label, kind, ceiling in result.scenario_cash_flow_limits:
        stable_id = scenario_ids.get(str(label))
        if not stable_id:
            continue
        metrics.append(_metric(
            data, "housing.cash_flow_price_ceiling", ceiling,
            unit="currency", basis=T.BASIS_NOMINAL,
            source="housing-affordability", scenario=kind,
            entity_id=str(stable_id),
            label=label,
        ))
    return metrics


def education(data: dict) -> list[T.MetricObservation]:
    edu = F._dig(data, "education") or {}
    plan = E.plan_for(
        edu.get("children"), members=F._dig(data, "household.members") or [],
        accounts=edu.get("accounts") or [],
        cost_inflation=float(edu.get("cost_inflation") or E.DEFAULT_COST_INFLATION),
        real_return=float(edu.get("real_return") or E.DEFAULT_REAL_RETURN),
        state=F._dig(data, "meta.jurisdiction.state"),
    )
    assumptions = {
        "cost_inflation": float(
            edu.get("cost_inflation") or E.DEFAULT_COST_INFLATION),
        "real_return": float(edu.get("real_return") or E.DEFAULT_REAL_RETURN),
    }
    metrics = [_metric(
        data, "education.total_funding_gap", plan.total_gap,
        unit="currency", basis=T.BASIS_NOMINAL,
        source="education-funding", assumptions=assumptions)]
    for child in plan.children:
        metrics.append(_metric(
            data, "education.funding_gap", max(0.0, child.gap),
            unit="currency", basis=T.BASIS_NOMINAL,
            source="education-funding", entity_id=str(child.member_id),
            label=str(child.member_id), assumptions=assumptions))
    return metrics


def _survivor_need(data: dict, insured_id: str) -> S.SurvivorNeed:
    members = F._dig(data, "household.members") or []
    available = (F.tier_total(data, F.LIQUID)
                 + F.tier_total(data, F.AGE_RESTRICTED)
                 + F.tier_total(data, F.ILLIQUID))
    return S.compute(
        insured_id=insured_id, members=members,
        annual_spending=float(F._dig(data, "household.annual_spending")),
        assets_available=available,
        education_obligation=F._dig(data, "household.education_obligation"),
        non_citizen_survivor=any(
            x.get("role") == "spouse" and x.get("us_status")
            and x.get("us_status") != "citizen" for x in members),
        social_security=F._dig(data, "social_security"),
    )


def survivor_needs(data: dict) -> list[T.MetricObservation]:
    earners = [x for x in F._dig(data, "household.members") or []
               if x.get("role") in ("primary", "spouse")
               and float(x.get("income_annual") or 0) > 0]
    return [_metric(
        data, "insurance.survivor_capital_gap", _survivor_need(data, e["id"]).net_need,
        unit="currency", basis=T.BASIS_REAL, source="survivor-needs",
        entity_id=str(e["id"]), label=str(e.get("role") or e["id"]))
        for e in earners]


def life_insurance(data: dict) -> list[T.MetricObservation]:
    policies = F._dig(data, "insurance.life") or []
    dependents = F.dependents(data)
    metrics = []
    for insured_id in sorted({p.get("insured") for p in policies if p.get("insured")}):
        need = _survivor_need(data, str(insured_id))
        result = L.assess(
            policies, need=need.net_need, insured_id=str(insured_id),
            dependents=dependents, today=F.as_of(data))
        metrics.append(_metric(
            data, "insurance.life_coverage_gap", result.gap,
            unit="currency", basis=T.BASIS_REAL,
            source="life-insurance-review", entity_id=str(insured_id),
            label=str(insured_id)))
    return metrics


def disability_insurance(data: dict) -> list[T.MetricObservation]:
    policies = F._dig(data, "insurance.disability") or []
    members = F._dig(data, "household.members") or []
    metrics = []
    for insured_id in sorted({p.get("insured") for p in policies if p.get("insured")}):
        member = next((x for x in members if x.get("id") == insured_id), {})
        result = D.assess(
            policies, insured_id=str(insured_id), insured_age=member.get("age"),
            annual_spending=float(F._dig(data, "household.annual_spending")),
            gross_income=float(member.get("income_annual") or 0),
            liquid_assets=F.liquid(data), reference_date=F.as_of(data),
        )
        metrics.append(_metric(
            data, "insurance.disability_coverage_gap_monthly",
            result.monthly_gap, unit="currency", basis=T.BASIS_NOMINAL,
            source="disability-insurance-review", entity_id=str(insured_id),
            label=str(insured_id),
            assumptions={"tax_rate": D.ASSUMED_MARGINAL_RATE}))
    return metrics


def tax_planning(data: dict) -> list[T.MetricObservation]:
    plan = TP.plan_from_facts(data)
    assumptions = {
        "history_years": [row.tax_year for row in plan.history.years],
    }
    metrics = [
        _metric(
            data,
            "tax.projected_combined_tax",
            plan.current.combined_tax,
            unit="currency",
            basis=T.BASIS_NOMINAL,
            source="tax-planning",
            assumptions=assumptions,
        ),
        _metric(
            data,
            "tax.projected_effective_rate",
            plan.current.effective_rate,
            unit="ratio",
            basis=T.BASIS_NONMONETARY,
            source="tax-planning",
            assumptions=assumptions,
        ),
        _metric(
            data,
            "tax.historical_weighted_effective_rate",
            plan.history.weighted_effective_rate,
            unit="ratio",
            basis=T.BASIS_NONMONETARY,
            source="tax-planning",
            scenario="historical_baseline",
            assumptions=assumptions,
        ),
    ]
    if plan.current.payment_gap is not None:
        metrics.append(_metric(
            data,
            "tax.projected_payment_gap",
            plan.current.payment_gap,
            unit="currency",
            basis=T.BASIS_NOMINAL,
            source="tax-planning",
            assumptions=assumptions,
        ))
    return metrics


ADAPTERS: dict[str, Callable[[dict], list[T.MetricObservation]]] = {
    "disability-insurance-review": disability_insurance,
    "education-funding": education,
    "emergency-fund-sizing": emergency_fund,
    "employer-concentration-risk": employer_concentration,
    "housing-affordability": housing_affordability,
    "life-insurance-review": life_insurance,
    "retirement-readiness": retirement,
    "survivor-needs": survivor_needs,
    "tax-planning": tax_planning,
}


def emit(skill: str, data: dict) -> list[T.MetricObservation]:
    adapter = ADAPTERS.get(skill)
    return adapter(data) if adapter else []
