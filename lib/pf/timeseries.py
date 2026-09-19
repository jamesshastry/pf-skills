"""Structured financial history without confusing observations and forecasts.

The one idea is that a number is comparable only when its identity, clock,
scenario, unit, currency, basis and stable entity dimensions agree.  A balance
observed in 2026, a conclusion calculated in 2026, and a projected 2036 balance
are deliberately different series even when they share a metric ID.

This module owns the protocol, immutable snapshot documents, comparison rules,
and small observed-facts adapter.  It does not scrape Markdown, forward-fill a
gap, fetch prices or FX, infer transaction flows from endpoint balances, or
write a snapshot as a side effect of an ordinary skill run.
"""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import math
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable

from . import facts as F

HISTORY_SCHEMA_VERSION = 1
METRIC_PROTOCOL_VERSION = 1
ANALYSIS_MODEL_VERSION = "pf-skills-v1"

CLOCK_OBSERVED = "observed"
CLOCK_ANALYSIS = "analysis"
CLOCK_PROJECTION = "projection"
CLOCKS = (CLOCK_OBSERVED, CLOCK_ANALYSIS, CLOCK_PROJECTION)

SNAPSHOT_COMPLETE = "complete"
SNAPSHOT_PARTIAL = "partial"
SNAPSHOT_ANALYSIS = "analysis"
SNAPSHOT_RESTATEMENT = "restatement"
SNAPSHOT_KINDS = (
    SNAPSHOT_COMPLETE,
    SNAPSHOT_PARTIAL,
    SNAPSHOT_ANALYSIS,
    SNAPSHOT_RESTATEMENT,
)

BASIS_NOMINAL = "nominal"
BASIS_REAL = "real"
BASIS_NONMONETARY = "nonmonetary"
BASES = (BASIS_NOMINAL, BASIS_REAL, BASIS_NONMONETARY)

QUALITY_COMPLETE = "complete"
QUALITY_PARTIAL = "partial"
QUALITY_ESTIMATED = "estimated"
QUALITY_UNKNOWN = "unknown"
QUALITIES = (
    QUALITY_COMPLETE,
    QUALITY_PARTIAL,
    QUALITY_ESTIMATED,
    QUALITY_UNKNOWN,
)
METRIC_STATUSES = ("measured", "derived", "projected", "unknown")

FINDING_STATES = (
    "unobserved", "open", "improved", "closed", "worsened", "superseded"
)
CHANGE_DRIVERS = (
    "household", "facts", "assumptions", "reference_data", "model", "unknown"
)

_STABLE_ID = re.compile(r"^[a-z][a-z0-9_.-]*$")
_ENTITY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


class HistoryError(ValueError):
    """A history document or comparison would produce a misleading result."""


def _date(value: Any, field_name: str) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except ValueError as exc:
            raise HistoryError(f"{field_name} must be an ISO date") from exc
    raise HistoryError(f"{field_name} must be an ISO date")


def _optional_date(value: Any, field_name: str) -> dt.date | None:
    return None if value is None else _date(value, field_name)


def _pairs(value: Any) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    rows = value.items() if isinstance(value, dict) else value
    return tuple(sorted((str(k), str(v)) for k, v in rows))


def fingerprint(value: Any) -> str:
    """Stable local fingerprint for attribution; never a replacement for facts."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def analysis_input_fingerprint(facts: dict[str, Any]) -> str:
    """Fingerprint financial inputs while excluding the run's own timestamp."""
    copied = copy.deepcopy(facts)
    if isinstance(copied.get("meta"), dict):
        copied["meta"].pop("analysis_at", None)
    return fingerprint(copied)


@dataclass(frozen=True)
class MetricObservation:
    """One typed metric at one date on exactly one of the three clocks."""

    metric_id: str
    effective_date: dt.date
    value: float | None
    unit: str
    basis: str
    scenario: str
    source: str
    clock: str
    status: str
    currency: str | None = None
    entity_id: str | None = None
    display_label: str | None = None
    dimensions: tuple[tuple[str, str], ...] = ()
    observed_at: dt.date | None = None
    calculated_at: dt.date | None = None
    model_version: str | None = None
    data_quality: str = QUALITY_COMPLETE
    unknown_reason: str | None = None
    inputs_fingerprint: str | None = None
    assumptions_fingerprint: str | None = None
    reference_version: str | None = None
    attribution: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        if not _STABLE_ID.fullmatch(self.metric_id):
            raise HistoryError(f"invalid stable metric_id {self.metric_id!r}")
        if self.entity_id is not None and not _ENTITY_ID.fullmatch(self.entity_id):
            raise HistoryError(f"invalid stable entity_id {self.entity_id!r}")
        if self.clock not in CLOCKS:
            raise HistoryError(f"unknown clock {self.clock!r}")
        if self.basis not in BASES:
            raise HistoryError(f"unknown basis {self.basis!r}")
        if self.data_quality not in QUALITIES:
            raise HistoryError(f"unknown data_quality {self.data_quality!r}")
        if self.status not in METRIC_STATUSES:
            raise HistoryError(f"unknown metric status {self.status!r}")
        if not self.unit or not self.scenario or not self.source:
            raise HistoryError("unit, scenario and source are required")
        if self.unit == "currency" and not self.currency:
            raise HistoryError("currency metrics require a currency code")
        if self.unit != "currency" and self.currency is not None:
            raise HistoryError("non-currency metrics cannot carry currency")
        unknown = self.value is None
        if unknown != bool(self.unknown_reason):
            raise HistoryError(
                "an observation needs either a numeric value or an explicit "
                "unknown_reason, never neither or both"
            )
        if unknown and self.data_quality != QUALITY_UNKNOWN:
            raise HistoryError("an unknown value must use data_quality=unknown")
        if unknown and self.status != "unknown":
            raise HistoryError("an unknown value must use status=unknown")
        if not unknown and self.status == "unknown":
            raise HistoryError("a numeric value cannot use status=unknown")
        if self.clock == CLOCK_OBSERVED:
            if self.scenario != "observed":
                raise HistoryError("observed history must use scenario=observed")
            if self.model_version is not None or self.calculated_at is not None:
                raise HistoryError(
                    "observed facts cannot carry a model version or calculated_at"
                )
            if self.observed_at is None:
                raise HistoryError("observed history requires observed_at")
            if self.status not in ("measured", "unknown"):
                raise HistoryError("observed history status must be measured or unknown")
        else:
            if not self.model_version or self.calculated_at is None:
                raise HistoryError(
                    "analysis and projection observations require model_version "
                    "and calculated_at"
                )
            if self.observed_at is not None:
                raise HistoryError("analysis/projection metrics cannot carry observed_at")
        if self.clock == CLOCK_ANALYSIS and self.status not in ("derived", "unknown"):
            raise HistoryError("analysis status must be derived or unknown")
        if self.clock == CLOCK_PROJECTION and self.scenario == "observed":
            raise HistoryError("a projection cannot use scenario=observed")
        if (self.clock == CLOCK_PROJECTION and self.value is not None
                and self.status != "projected"):
            raise HistoryError("forward projections must use status=projected")
        if self.value is not None and not math.isfinite(self.value):
            raise HistoryError("metric value must be finite")

    @property
    def series_key(self) -> tuple[Any, ...]:
        """Everything that must match before two points can be compared."""
        return (
            self.metric_id,
            self.clock,
            self.unit,
            self.currency,
            self.basis,
            self.scenario,
            self.entity_id,
            self.dimensions,
        )

    @property
    def point_key(self) -> tuple[Any, ...]:
        if self.clock == CLOCK_OBSERVED:
            return self.series_key + (self.effective_date,)
        return self.series_key + (
            self.effective_date, self.calculated_at, self.model_version)

    @property
    def sort_date(self) -> dt.date:
        return (self.calculated_at if self.clock == CLOCK_ANALYSIS
                else self.effective_date) or self.effective_date

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "metric_id": self.metric_id,
            "effective_date": self.effective_date.isoformat(),
            "value": self.value,
            "unit": self.unit,
            "basis": self.basis,
            "scenario": self.scenario,
            "source": self.source,
            "clock": self.clock,
            "status": self.status,
            "data_quality": self.data_quality,
        }
        optional = {
            "currency": self.currency,
            "entity_id": self.entity_id,
            "display_label": self.display_label,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
            "model_version": self.model_version,
            "unknown_reason": self.unknown_reason,
            "inputs_fingerprint": self.inputs_fingerprint,
            "assumptions_fingerprint": self.assumptions_fingerprint,
            "reference_version": self.reference_version,
        }
        out.update({k: v for k, v in optional.items() if v is not None})
        if self.dimensions:
            out["dimensions"] = dict(self.dimensions)
        if self.attribution:
            out["attribution"] = dict(self.attribution)
        return out

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "MetricObservation":
        return cls(
            metric_id=str(row["metric_id"]),
            effective_date=_date(row["effective_date"], "effective_date"),
            value=None if row.get("value") is None else float(row["value"]),
            unit=str(row["unit"]),
            basis=str(row["basis"]),
            scenario=str(row["scenario"]),
            source=str(row["source"]),
            clock=str(row["clock"]),
            status=str(row["status"]),
            currency=row.get("currency"),
            entity_id=row.get("entity_id"),
            display_label=row.get("display_label"),
            dimensions=_pairs(row.get("dimensions")),
            observed_at=_optional_date(row.get("observed_at"), "observed_at"),
            calculated_at=_optional_date(row.get("calculated_at"), "calculated_at"),
            model_version=row.get("model_version"),
            data_quality=str(row.get("data_quality") or QUALITY_COMPLETE),
            unknown_reason=row.get("unknown_reason"),
            inputs_fingerprint=row.get("inputs_fingerprint"),
            assumptions_fingerprint=row.get("assumptions_fingerprint"),
            reference_version=row.get("reference_version"),
            attribution=tuple(
                sorted((str(k), float(v)) for k, v in
                       (row.get("attribution") or {}).items())
            ),
        )


@dataclass(frozen=True)
class FindingObservation:
    """A stable finding state; wording is retained but never used as its key."""

    finding_id: str
    effective_date: dt.date
    source_skill: str
    state: str
    severity: str
    text: str
    calculated_at: dt.date
    model_version: str
    transition_reason: str | None = None
    change_driver: str = "unknown"
    inputs_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if not _STABLE_ID.fullmatch(self.finding_id):
            raise HistoryError(f"invalid stable finding_id {self.finding_id!r}")
        if self.state not in FINDING_STATES:
            raise HistoryError(f"unknown finding state {self.state!r}")
        if self.change_driver not in CHANGE_DRIVERS:
            raise HistoryError(f"unknown change driver {self.change_driver!r}")
        if self.state in ("improved", "closed", "worsened", "superseded") \
                and not self.transition_reason:
            raise HistoryError("finding transitions require a reason")

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "effective_date": self.effective_date.isoformat(),
            "source_skill": self.source_skill,
            "state": self.state,
            "severity": self.severity,
            "text": self.text,
            "calculated_at": self.calculated_at.isoformat(),
            "model_version": self.model_version,
            "transition_reason": self.transition_reason,
            "change_driver": self.change_driver,
            "inputs_fingerprint": self.inputs_fingerprint,
        }

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "FindingObservation":
        return cls(
            finding_id=str(row["finding_id"]),
            effective_date=_date(row["effective_date"], "effective_date"),
            source_skill=str(row["source_skill"]),
            state=str(row["state"]),
            severity=str(row["severity"]),
            text=str(row["text"]),
            calculated_at=_date(row["calculated_at"], "calculated_at"),
            model_version=str(row["model_version"]),
            transition_reason=row.get("transition_reason"),
            change_driver=str(row.get("change_driver") or "unknown"),
            inputs_fingerprint=row.get("inputs_fingerprint"),
        )


@dataclass
class StructuredResult:
    skill_id: str
    headline: str
    calculated_at: dt.date
    model_version: str
    metrics: list[MetricObservation] = field(default_factory=list)
    findings: list[FindingObservation] = field(default_factory=list)
    dependencies: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "headline": self.headline,
            "calculated_at": self.calculated_at.isoformat(),
            "model_version": self.model_version,
            "metrics": [m.to_dict() for m in self.metrics],
            "findings": [f.to_dict() for f in self.findings],
            "dependencies": list(self.dependencies),
            "assumptions": list(self.assumptions),
        }

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "StructuredResult":
        return cls(
            skill_id=str(row["skill_id"]),
            headline=str(row.get("headline") or ""),
            calculated_at=_date(row["calculated_at"], "calculated_at"),
            model_version=str(row["model_version"]),
            metrics=[MetricObservation.from_dict(x) for x in row.get("metrics") or []],
            findings=[FindingObservation.from_dict(x)
                      for x in row.get("findings") or []],
            dependencies=tuple(str(x) for x in row.get("dependencies") or []),
            assumptions=tuple(str(x) for x in row.get("assumptions") or []),
        )


@dataclass(frozen=True)
class Restatement:
    """A correction that retains the original observation verbatim."""

    original_snapshot_id: str
    original: MetricObservation
    corrected: MetricObservation
    reason: str
    corrected_at: dt.date

    def __post_init__(self) -> None:
        if self.original.point_key != self.corrected.point_key:
            raise HistoryError("a restatement must preserve the metric point key")
        if not self.reason.strip():
            raise HistoryError("a restatement requires a reason")

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_snapshot_id": self.original_snapshot_id,
            "original": self.original.to_dict(),
            "corrected": self.corrected.to_dict(),
            "reason": self.reason,
            "corrected_at": self.corrected_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "Restatement":
        return cls(
            original_snapshot_id=str(row["original_snapshot_id"]),
            original=MetricObservation.from_dict(row["original"]),
            corrected=MetricObservation.from_dict(row["corrected"]),
            reason=str(row["reason"]),
            corrected_at=_date(row["corrected_at"], "corrected_at"),
        )


@dataclass
class Snapshot:
    snapshot_id: str
    kind: str
    effective_date: dt.date
    observed_at: dt.date
    completeness: str
    facts: dict[str, Any] | None = None
    observations: list[MetricObservation] = field(default_factory=list)
    analyses: list[StructuredResult] = field(default_factory=list)
    restatements: list[Restatement] = field(default_factory=list)
    notes: tuple[str, ...] = ()
    source_snapshot_id: str | None = None

    def __post_init__(self) -> None:
        if not _STABLE_ID.fullmatch(self.snapshot_id):
            raise HistoryError(f"invalid snapshot_id {self.snapshot_id!r}")
        if self.kind not in SNAPSHOT_KINDS:
            raise HistoryError(f"unknown snapshot kind {self.kind!r}")
        if self.completeness not in (SNAPSHOT_COMPLETE, SNAPSHOT_PARTIAL):
            raise HistoryError("completeness must be complete or partial")
        if self.kind in (SNAPSHOT_COMPLETE, SNAPSHOT_PARTIAL) and self.facts is None:
            raise HistoryError("fact snapshots must retain an independent facts copy")
        if self.kind in (SNAPSHOT_COMPLETE, SNAPSHOT_PARTIAL) \
                and (self.analyses or self.restatements):
            raise HistoryError(
                "fact snapshots cannot contain analysis results or restatements")
        if self.kind == SNAPSHOT_ANALYSIS and (
                self.facts is not None or self.observations or self.restatements):
            raise HistoryError(
                "analysis snapshots contain only structured analysis results")
        if self.kind == SNAPSHOT_RESTATEMENT and (
                self.facts is not None or self.observations or self.analyses):
            raise HistoryError(
                "restatement snapshots contain only correction records")
        for obs in self.observations:
            if obs.clock != CLOCK_OBSERVED:
                raise HistoryError("snapshot observations must use the observed clock")
        for result in self.analyses:
            if any(m.clock == CLOCK_OBSERVED for m in result.metrics):
                raise HistoryError("analysis results cannot contain observed metrics")

    @property
    def facts_fingerprint(self) -> str | None:
        return fingerprint(self.facts) if self.facts is not None else None

    def all_metrics(self) -> list[MetricObservation]:
        out = list(self.observations)
        for result in self.analyses:
            out.extend(result.metrics)
        return out

    def all_findings(self) -> list[FindingObservation]:
        return [f for result in self.analyses for f in result.findings]

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "history_schema_version": HISTORY_SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "kind": self.kind,
            "effective_date": self.effective_date.isoformat(),
            "observed_at": self.observed_at.isoformat(),
            "completeness": self.completeness,
            "observations": [m.to_dict() for m in self.observations],
            "analyses": [a.to_dict() for a in self.analyses],
            "restatements": [r.to_dict() for r in self.restatements],
            "notes": list(self.notes),
        }
        if self.source_snapshot_id is not None:
            out["source_snapshot_id"] = self.source_snapshot_id
        if self.facts is not None:
            out["facts"] = copy.deepcopy(self.facts)
            out["facts_fingerprint"] = self.facts_fingerprint
        return out

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "Snapshot":
        if row.get("history_schema_version") != HISTORY_SCHEMA_VERSION:
            raise HistoryError(
                f"history schema version {row.get('history_schema_version')!r} "
                f"is not supported; expected {HISTORY_SCHEMA_VERSION}"
            )
        snapshot = cls(
            snapshot_id=str(row["snapshot_id"]),
            kind=str(row["kind"]),
            effective_date=_date(row["effective_date"], "effective_date"),
            observed_at=_date(row["observed_at"], "observed_at"),
            completeness=str(row["completeness"]),
            facts=copy.deepcopy(row.get("facts")),
            observations=[MetricObservation.from_dict(x)
                          for x in row.get("observations") or []],
            analyses=[StructuredResult.from_dict(x)
                      for x in row.get("analyses") or []],
            restatements=[Restatement.from_dict(x)
                          for x in row.get("restatements") or []],
            notes=tuple(str(x) for x in row.get("notes") or []),
            source_snapshot_id=row.get("source_snapshot_id"),
        )
        recorded = row.get("facts_fingerprint")
        if recorded and recorded != snapshot.facts_fingerprint:
            raise HistoryError("snapshot facts do not match facts_fingerprint")
        return snapshot


def _money_observation(
    metric_id: str,
    date: dt.date,
    value: float | None,
    *,
    currency: str,
    source: str,
    observed_at: dt.date,
    entity_id: str | None = None,
    display_label: str | None = None,
    quality: str = QUALITY_COMPLETE,
    unknown_reason: str | None = None,
) -> MetricObservation:
    return MetricObservation(
        metric_id=metric_id,
        effective_date=date,
        value=value,
        unit="currency",
        currency=currency,
        basis=BASIS_NOMINAL,
        scenario="observed",
        source=source,
        clock=CLOCK_OBSERVED,
        status="unknown" if value is None else "measured",
        entity_id=entity_id,
        display_label=display_label,
        observed_at=observed_at,
        data_quality=quality,
        unknown_reason=unknown_reason,
    )


def observed_metrics(
    facts: dict[str, Any],
    *,
    effective_date: dt.date,
    observed_at: dt.date,
    completeness: str,
) -> tuple[list[MetricObservation], list[str]]:
    """Extract the small, stable first-release observed metric set."""
    if completeness not in (SNAPSHOT_COMPLETE, SNAPSHOT_PARTIAL):
        raise HistoryError("completeness must be complete or partial")
    currency = str(F._dig(facts, "meta.currency") or "")
    if not currency:
        raise HistoryError("meta.currency is required for history capture")
    rows = F._dig(facts, "household.balance_sheet") or []
    debt_rows = F._dig(facts, "debts")
    debts = debt_rows or []
    metrics: list[MetricObservation] = []
    gaps: list[str] = []

    for row in rows:
        stable_id = row.get("id")
        if not stable_id:
            gaps.append(f"balance-sheet row `{row.get('name') or '?'}` has no stable id")
            continue
        raw_value = row.get("value")
        value = (None if raw_value is None else
                 float(raw_value) - float(row.get("margin_debt") or 0))
        metrics.append(_money_observation(
            "household.asset_balance", effective_date, value,
            currency=currency, source="household.balance_sheet",
            observed_at=observed_at, entity_id=str(stable_id),
            display_label=str(row.get("name") or stable_id),
            quality=QUALITY_UNKNOWN if value is None else QUALITY_COMPLETE,
            unknown_reason=("balance not recorded" if value is None else None),
        ))

    if completeness == SNAPSHOT_COMPLETE:
        missing_total = [row.get("name") or "unnamed asset" for row in rows
                         if not row.get("pending") and row.get("value") is None]
        missing_total.extend(
            row.get("name") or "unnamed debt" for row in debts
            if row.get("balance") is None)
        if debt_rows is None:
            missing_total.append("debts section")
        if missing_total:
            metrics.append(_money_observation(
                "household.net_worth", effective_date, None,
                currency=currency, source="household.balance_sheet+debts",
                observed_at=observed_at, quality=QUALITY_UNKNOWN,
                unknown_reason="missing values: " + ", ".join(missing_total),
            ))
        else:
            assets = sum(float(row["value"])
                         - float(row.get("margin_debt") or 0) for row in rows
                         if not row.get("pending"))
            debt = sum(float(row["balance"]) for row in debts)
            metrics.append(_money_observation(
                "household.net_worth", effective_date, assets - debt,
                currency=currency, source="household.balance_sheet+debts",
                observed_at=observed_at,
            ))
    else:
        metrics.append(_money_observation(
            "household.net_worth", effective_date, None,
            currency=currency, source="household.balance_sheet+debts",
            observed_at=observed_at, quality=QUALITY_UNKNOWN,
            unknown_reason="partial snapshot cannot support a household total",
        ))

    reserve = F.reserve_assets(facts)
    missing_cash = [str(row.get("name") or "unnamed cash asset") for row in rows
                    if row.get("liquidity_class") == F.CASH_EQUIVALENT
                    and row.get("value") is None]
    metrics.append(_money_observation(
        "household.cash_reserve", effective_date,
        None if missing_cash else reserve.included,
        currency=currency, source="household.balance_sheet.liquidity_class",
        observed_at=observed_at,
        quality=(QUALITY_UNKNOWN if missing_cash else
                 QUALITY_PARTIAL if reserve.unknown else QUALITY_COMPLETE),
        unknown_reason=("missing values: " + ", ".join(missing_cash)
                        if missing_cash else None),
    ))
    if reserve.unknown:
        gaps.append("liquidity classification missing for: " +
                    ", ".join(sorted(reserve.unknown)))

    income_rows = [row for row in F._dig(facts, "household.members") or []
                   if row.get("role") in ("primary", "spouse")]
    income = (None if any(row.get("income_annual") is None for row in income_rows)
              else F.household_income(facts))
    scalar_money = (
        ("household.gross_income_annual", income,
         "household.members[].income_annual"),
        ("household.spending_annual", F._dig(facts, "household.annual_spending"),
         "household.annual_spending"),
        ("household.retirement_savings_annual",
         F._dig(facts, "retirement.annual_savings"),
         "retirement.annual_savings"),
    )
    for metric_id, raw, source in scalar_money:
        if raw is None:
            metrics.append(_money_observation(
                metric_id, effective_date, None, currency=currency,
                source=source, observed_at=observed_at,
                quality=QUALITY_UNKNOWN, unknown_reason="not recorded",
            ))
        else:
            metrics.append(_money_observation(
                metric_id, effective_date, float(raw), currency=currency,
                source=source, observed_at=observed_at,
            ))
    return metrics, gaps


def analysis_metric(
    facts: dict[str, Any],
    metric_id: str,
    value: float | None,
    *,
    unit: str,
    basis: str,
    scenario: str,
    source: str,
    model_version: str = ANALYSIS_MODEL_VERSION,
    currency: str | None = None,
    entity_id: str | None = None,
    display_label: str | None = None,
    unknown_reason: str | None = None,
    assumptions: Any = None,
    reference_version: str | None = None,
) -> MetricObservation:
    """Build a deterministic analysis-clock observation for a skill adapter."""
    effective = F.as_of(facts)
    if effective is None:
        raise HistoryError("meta.as_of is required for a structured result")
    calculated = _optional_date(
        F._dig(facts, "meta.analysis_at"), "meta.analysis_at") or effective
    return MetricObservation(
        metric_id=metric_id,
        effective_date=effective,
        value=value,
        unit=unit,
        basis=basis,
        scenario=scenario,
        source=source,
        clock=CLOCK_ANALYSIS,
        status="unknown" if value is None else "derived",
        currency=currency,
        entity_id=entity_id,
        display_label=display_label,
        calculated_at=calculated,
        model_version=model_version,
        data_quality=QUALITY_UNKNOWN if value is None else QUALITY_COMPLETE,
        unknown_reason=unknown_reason,
        inputs_fingerprint=analysis_input_fingerprint(facts),
        assumptions_fingerprint=(fingerprint(assumptions)
                                 if assumptions is not None else None),
        reference_version=reference_version,
    )


def capture_snapshot(
    facts: dict[str, Any],
    *,
    snapshot_id: str,
    effective_date: dt.date,
    observed_at: dt.date,
    completeness: str = SNAPSHOT_COMPLETE,
) -> Snapshot:
    """Create an in-memory snapshot without mutating the supplied facts."""
    facts_date = F.as_of(facts)
    if facts_date != effective_date:
        raise HistoryError(
            "capture effective_date must match meta.as_of; use a partial/event "
            "snapshot with facts actually effective on the requested date"
        )
    original = fingerprint(facts)
    copied = copy.deepcopy(facts)
    metrics, gaps = observed_metrics(
        copied, effective_date=effective_date, observed_at=observed_at,
        completeness=completeness,
    )
    if fingerprint(facts) != original:
        raise AssertionError("history capture mutated the source facts")
    return Snapshot(
        snapshot_id=snapshot_id,
        kind=completeness,
        effective_date=effective_date,
        observed_at=observed_at,
        completeness=completeness,
        facts=copied,
        observations=metrics,
        notes=tuple(gaps),
    )


def save_snapshot(snapshot: Snapshot, path: str | Path) -> None:
    """Persist explicitly; ordinary reports never call this function."""
    target = Path(path)
    if target.exists():
        raise HistoryError(
            f"refusing to overwrite immutable snapshot {target}; use the "
            "restatement workflow"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = snapshot.to_dict()
    if target.suffix.lower() == ".json":
        text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    else:
        try:
            import yaml  # noqa: PLC0415
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise HistoryError("saving YAML history requires PyYAML") from exc
        text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    target.write_text(text, encoding="utf-8")


def load_snapshot(path: str | Path) -> Snapshot:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() == ".json":
        row = json.loads(text, object_pairs_hook=F._json_no_duplicates)
    else:
        try:
            import yaml  # noqa: PLC0415
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise HistoryError("loading YAML history requires PyYAML") from exc
        row = yaml.load(text, Loader=F._strict_yaml_loader())  # noqa: S506
    if not isinstance(row, dict):
        raise HistoryError(f"{source} did not contain a history mapping")
    return Snapshot.from_dict(row)


@dataclass(frozen=True)
class MetricSeries:
    key: tuple[Any, ...]
    observations: tuple[MetricObservation, ...]

    def __post_init__(self) -> None:
        if any(o.series_key != self.key for o in self.observations):
            raise HistoryError("a series cannot mix clocks, scenarios, units or bases")
        order = [(o.sort_date, o.model_version or "") for o in self.observations]
        if order != sorted(order) or len({o.point_key for o in self.observations}) != len(order):
            raise HistoryError("a series needs unique observations in date order")


@dataclass(frozen=True)
class MetricChange:
    start: MetricObservation
    end: MetricObservation
    absolute_change: float
    percentage_change: float | None
    attribution: tuple[tuple[str, float], ...]
    unexplained: float
    change_driver: str
    warnings: tuple[str, ...] = ()


def compare_points(start: MetricObservation, end: MetricObservation) -> MetricChange:
    if start.series_key != end.series_key:
        differences = []
        labels = (
            "metric", "clock", "unit", "currency", "basis", "scenario",
            "entity", "dimensions",
        )
        for label, a, b in zip(labels, start.series_key, end.series_key):
            if a != b:
                differences.append(f"{label} {a!r} != {b!r}")
        raise HistoryError("non-comparable observations: " + "; ".join(differences))
    if start.value is None or end.value is None:
        raise HistoryError("unknown observations cannot be compared as zero")
    delta = end.value - start.value
    pct = None if start.value == 0 else delta / abs(start.value)
    pieces = dict(end.attribution)
    explained = sum(pieces.values())
    residual = delta - explained
    driver = "household"
    warnings: list[str] = []
    if (start.inputs_fingerprint and
            start.inputs_fingerprint == end.inputs_fingerprint and
            start.model_version != end.model_version):
        driver = "model"
        warnings.append("same inputs; model version changed")
    elif start.assumptions_fingerprint != end.assumptions_fingerprint:
        driver = "assumptions"
    elif start.reference_version != end.reference_version:
        driver = "reference_data"
    if not pieces and delta:
        warnings.append("no flow data; endpoint change is unattributed")
    return MetricChange(
        start=start,
        end=end,
        absolute_change=delta,
        percentage_change=pct,
        attribution=tuple(sorted(pieces.items())),
        unexplained=residual,
        change_driver=driver,
        warnings=tuple(warnings),
    )


@dataclass
class History:
    snapshots: list[Snapshot]

    def __post_init__(self) -> None:
        ids = [s.snapshot_id for s in self.snapshots]
        if len(ids) != len(set(ids)):
            raise HistoryError("snapshot IDs must be unique")
        self.snapshots.sort(key=lambda s: (s.effective_date, s.snapshot_id))

    def metrics(self, *, include_original_restatements: bool = False) -> list[MetricObservation]:
        points: dict[tuple[Any, ...], MetricObservation] = {}
        originals: list[MetricObservation] = []
        for snapshot in self.snapshots:
            for metric in snapshot.all_metrics():
                if metric.point_key in points:
                    raise HistoryError(
                        "duplicate metric point without a restatement: "
                        f"{metric.metric_id} {metric.effective_date}"
                    )
                points[metric.point_key] = metric
        restatements = sorted(
            (row for snapshot in self.snapshots for row in snapshot.restatements),
            key=lambda row: row.corrected_at,
        )
        for restatement in restatements:
            current = points.get(restatement.original.point_key)
            if current != restatement.original:
                raise HistoryError(
                    "restatement original does not match the retained history"
                )
            originals.append(restatement.original)
            points[restatement.corrected.point_key] = restatement.corrected
        out = sorted(points.values(), key=lambda m: (
            repr(m.series_key), m.effective_date, m.calculated_at or m.effective_date))
        if include_original_restatements:
            out.extend(originals)
        return out

    def series(
        self,
        metric_id: str,
        *,
        clock: str,
        scenario: str,
        entity_id: str | None = None,
    ) -> MetricSeries:
        selected = [m for m in self.metrics()
                    if m.metric_id == metric_id and m.clock == clock
                    and m.scenario == scenario and m.entity_id == entity_id]
        if not selected:
            raise HistoryError("no matching observations")
        keys = {m.series_key for m in selected}
        if len(keys) != 1:
            raise HistoryError(
                "matching observations use incompatible unit, currency, basis "
                "or dimensions; normalize explicitly before comparison"
            )
        return MetricSeries(next(iter(keys)), tuple(sorted(
            selected, key=lambda m: (m.sort_date, m.model_version or ""))))

    def findings(self) -> list[FindingObservation]:
        return sorted(
            (f for s in self.snapshots for f in s.all_findings()),
            key=lambda f: (f.finding_id, f.calculated_at),
        )


def load_history(paths: Iterable[str | Path]) -> History:
    return History([load_snapshot(path) for path in paths])


def analyze_snapshot(
    snapshot: Snapshot,
    *,
    calculated_at: dt.date,
    skills_dir: str | Path,
    analysis_snapshot_id: str,
) -> Snapshot:
    """Re-run retained facts under the current model into a new document."""
    if snapshot.facts is None:
        raise HistoryError("analysis requires a snapshot that retains facts")
    data = copy.deepcopy(snapshot.facts)
    data.setdefault("meta", {})["analysis_at"] = calculated_at.isoformat()
    from . import review as V  # noqa: PLC0415 — avoids protocol/review cycle
    household = V.collect(data, skills_dir)
    analyses = V.structured_results(household, data)
    return Snapshot(
        snapshot_id=analysis_snapshot_id,
        kind=SNAPSHOT_ANALYSIS,
        effective_date=snapshot.effective_date,
        observed_at=calculated_at,
        completeness=snapshot.completeness,
        facts=None,
        analyses=analyses,
        source_snapshot_id=snapshot.snapshot_id,
        notes=(
            "Current model rerun; this is analysis history, not an observation.",
            f"{len(household.blocked)} skill(s) lacked inputs and were not approximated.",
        ),
    )


@dataclass
class HistorySummary:
    series: list[MetricSeries] = field(default_factory=list)
    changes: list[MetricChange] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    non_comparable: list[str] = field(default_factory=list)
    finding_changes: list[tuple[FindingObservation | None,
                                FindingObservation]] = field(default_factory=list)


def summarize_history(
    history: History,
    *,
    metric_ids: set[str] | None = None,
) -> HistorySummary:
    """Build the one structured object consumed by every history table."""
    summary = HistorySummary()
    groups: dict[tuple[Any, ...], list[MetricObservation]] = {}
    identities: dict[str, set[tuple[Any, ...]]] = {}
    for metric in history.metrics():
        if metric_ids is not None and metric.metric_id not in metric_ids:
            continue
        groups.setdefault(metric.series_key, []).append(metric)
        identities.setdefault(metric.metric_id, set()).add(metric.series_key)
    for metric_id, keys in identities.items():
        if len(keys) > 1:
            variants = sorted({
                f"{key[1]}/{key[5]}/{key[3] or '-'}-{key[4]}"
                + (f"/{dict(key[7])}" if key[7] else "") for key in keys
            })
            summary.non_comparable.append(
                f"{metric_id} has separate series: " + ", ".join(variants))
    for key, points in sorted(groups.items(), key=lambda item: str(item[0])):
        points.sort(key=lambda point: (point.sort_date, point.model_version or ""))
        # More than one result can re-run the same effective snapshot.  They
        # remain distinct on the analysis clock and are ordered by calculated_at.
        series = MetricSeries(key, tuple(points))
        summary.series.append(series)
        unknown = [point for point in points if point.value is None]
        for point in unknown:
            summary.gaps.append(
                f"{point.metric_id} at {point.effective_date}: "
                f"{point.unknown_reason}")
        known = [point for point in points if point.value is not None]
        if len(known) >= 2:
            summary.changes.append(compare_points(known[0], known[-1]))
    summary.changes.sort(
        key=lambda change: (
            0 if change.start.unit == "currency" else 1,
            -abs(change.absolute_change),
            change.start.metric_id,
        ))
    summary.gaps.sort()
    summary.non_comparable.sort()
    summary.finding_changes = finding_transitions(history.findings())
    return summary


def create_restatement(
    *,
    snapshot_id: str,
    original_snapshot_id: str,
    original: MetricObservation,
    corrected_value: float | None,
    reason: str,
    corrected_at: dt.date,
    unknown_reason: str | None = None,
) -> Snapshot:
    quality = QUALITY_UNKNOWN if corrected_value is None else original.data_quality
    corrected = replace(
        original,
        value=corrected_value,
        unknown_reason=unknown_reason,
        data_quality=quality,
        status="unknown" if corrected_value is None else original.status,
    )
    restatement = Restatement(
        original_snapshot_id=original_snapshot_id,
        original=original,
        corrected=corrected,
        reason=reason,
        corrected_at=corrected_at,
    )
    return Snapshot(
        snapshot_id=snapshot_id,
        kind=SNAPSHOT_RESTATEMENT,
        effective_date=original.effective_date,
        observed_at=corrected_at,
        completeness=SNAPSHOT_PARTIAL,
        facts=None,
        restatements=[restatement],
        notes=(f"Restated {original.metric_id}: {reason}",),
    )


def finding_transitions(
    findings: Iterable[FindingObservation],
) -> list[tuple[FindingObservation | None, FindingObservation]]:
    """Return transitions while retaining both old and new wording."""
    by_id: dict[str, list[FindingObservation]] = {}
    for finding in findings:
        by_id.setdefault(finding.finding_id, []).append(finding)
    transitions: list[tuple[FindingObservation | None, FindingObservation]] = []
    for rows in by_id.values():
        rows.sort(key=lambda f: (f.calculated_at, f.effective_date))
        previous = None
        for row in rows:
            if previous is None or row.state != previous.state or row.text != previous.text:
                transitions.append((previous, row))
            previous = row
    return sorted(transitions, key=lambda pair: (
        pair[1].calculated_at, pair[1].finding_id))
