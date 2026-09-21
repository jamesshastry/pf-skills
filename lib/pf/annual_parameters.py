"""Audit metadata for year-sensitive assumptions kept in private facts.

Repository-owned reference tables are registered in :mod:`pf.provenance`.
This module covers the other side of the boundary: annual or periodic values
that deliberately remain in a household's ignored facts file.  It never
validates a tax result and never prints a private value.  It only answers
whether each active group identifies its tax year, verification date, and
sources.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from . import facts as F


@dataclass(frozen=True)
class ParameterGroup:
    key: str
    label: str
    scope: str
    cadence: str
    authority: str
    paths: tuple[str, ...]


@dataclass(frozen=True)
class GroupAudit:
    group: ParameterGroup
    present_paths: tuple[str, ...]
    tax_year: int | None
    verified_on: dt.date | None
    source_count: int
    issues: tuple[str, ...]

    @property
    def active(self) -> bool:
        return bool(self.present_paths)

    @property
    def ready(self) -> bool:
        return self.active and not self.issues


GROUPS = (
    ParameterGroup(
        key="federal_tax",
        label="Federal income-tax schedule",
        scope="official",
        cadence="annual",
        authority="IRS annual inflation-adjustment revenue procedure",
        paths=(
            "assumptions.federal_brackets",
            "assumptions.standard_deduction",
            "assumptions.feie_exclusion_cap",
            "assumptions.additional_ctc_per_child",
            "assumptions.qcd_annual_limit",
        ),
    ),
    ParameterGroup(
        key="business_tax",
        label="Payroll and business-tax limits",
        scope="official",
        cadence="annual",
        authority="IRS and SSA annual notices, publications, and procedures",
        paths=(
            "assumptions.ss_wage_base",
            "assumptions.qbi_threshold",
            "assumptions.qbi_phase_in_range",
            "assumptions.section_179_limit",
            "assumptions.section_179_phaseout",
            "assumptions.suv_179_cap",
            "assumptions.bonus_depreciation_pct",
            "assumptions.bonus_depreciation_rate",
            "assumptions.luxury_auto_year1_cap",
            "assumptions.luxury_auto_year1_cap_no_bonus",
            "assumptions.standard_mileage_rate",
        ),
    ),
    ParameterGroup(
        key="healthcare",
        label="FPL, ACA, and IRMAA parameters",
        scope="official-and-local",
        cadence="annual",
        authority="HHS, CMS, IRS, and the household's marketplace quote",
        paths=(
            "assumptions.fpl_base",
            "assumptions.fpl_per_additional_person",
            "assumptions.aca_cliff_applies",
            "assumptions.aca_applicable_pct_schedule",
            "assumptions.irmaa_tiers",
            "assumptions.aca_benchmark_premium_annual",
        ),
    ),
    ParameterGroup(
        key="pfic_rates",
        label="PFIC historical rate series",
        scope="official",
        cadence="annual-and-quarterly",
        authority="IRS annual highest rates and quarterly §6621 revenue rulings",
        paths=(
            "assumptions.pfic_rates.top_marginal_rate",
            "assumptions.pfic_rates.underpayment_rate",
        ),
    ),
    ParameterGroup(
        key="household_tax",
        label="Household tax estimates",
        scope="household",
        cadence="annual-or-change",
        authority="Filed return, tax software, or tax professional",
        paths=(
            "assumptions.marginal_tax_rate",
            "assumptions.state_tax_rate",
            "assumptions.niit_rate",
            "assumptions.qualified_dividend_rate",
            "assumptions.ltcg_rate",
            "assumptions.capital_gains_rate",
            "assumptions.depreciation_recapture_rate",
            "assumptions.deductions_total",
            "assumptions.other_itemized_deductions",
        ),
    ),
)


def scheduled_target_year(today: dt.date | None = None) -> int:
    """Check next year once the main annual IRS release season has begun."""
    today = today or dt.date.today()
    return today.year + 1 if today.month >= 11 else today.year


def _parse_date(value: object) -> dt.date | None:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _sources(value: object) -> tuple[str, ...]:
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    if isinstance(value, list):
        return tuple(v.strip() for v in value
                     if isinstance(v, str) and v.strip())
    return ()


def infer_tax_year(data: dict) -> int | None:
    """Prefer the explicit planning year, then contributions, then meta.as_of."""
    for path in (
        "tax_planning.current_year.tax_year",
        "contributions.year",
    ):
        value = F._dig(data, path)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    as_of = F.as_of(data)
    return as_of.year if as_of else None


def audit(
    data: dict,
    *,
    target_year: int,
    today: dt.date | None = None,
) -> tuple[GroupAudit, ...]:
    """Check provenance metadata without exposing the underlying values."""
    today = today or dt.date.today()
    metadata = F._dig(data, "assumptions.annual_parameter_metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    audits: list[GroupAudit] = []
    for group in GROUPS:
        present = tuple(path for path in group.paths if F._dig(data, path) is not None)
        raw = metadata.get(group.key)
        issues: list[str] = []
        tax_year = None
        verified_on = None
        sources: tuple[str, ...] = ()

        if present:
            if not isinstance(raw, dict):
                issues.append("metadata is missing")
            else:
                raw_year = raw.get("tax_year")
                if isinstance(raw_year, int) and not isinstance(raw_year, bool):
                    tax_year = raw_year
                if tax_year != target_year:
                    issues.append(
                        f"tax_year is {tax_year if tax_year is not None else 'missing'}; "
                        f"expected {target_year}")

                verified_on = _parse_date(raw.get("verified_on"))
                if verified_on is None:
                    issues.append("verified_on is missing or not an ISO date")
                elif verified_on > today:
                    issues.append("verified_on is in the future")
                elif verified_on.year < target_year - 1:
                    issues.append(
                        "verified_on predates the normal publication window for "
                        f"tax year {target_year}")

                sources = _sources(raw.get("sources"))
                if not sources:
                    issues.append("no source is recorded")
                elif group.scope == "official" and any(
                        not source.startswith(("https://", "http://"))
                        for source in sources):
                    issues.append("official sources must be recorded as exact URLs")
                elif group.scope == "official-and-local" and not any(
                        source.startswith(("https://", "http://"))
                        for source in sources):
                    issues.append(
                        "at least one official source must be an exact URL")

        audits.append(GroupAudit(
            group=group,
            present_paths=present,
            tax_year=tax_year,
            verified_on=verified_on,
            source_count=len(sources),
            issues=tuple(issues),
        ))
    return tuple(audits)
