"""Operational continuity: can another person execute the first steps?

This module assembles a calm death/incapacity runbook from recorded facts.  It
reuses the estate, beneficiary, digital-access, life-insurance, debt, and
liquidity engines; it does not decide legal authority, transfer treatment,
benefit eligibility, or tax consequences.

The output is nominal current-state inventory.  It deliberately emits only
display-safe labels and references.  Credentials, recovery material, full
account numbers, and document contents belong in a sealed package, not here.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import debt as D
from . import estate as E
from . import facts as F
from . import life as L

READY = "ready"
INCOMPLETE = "incomplete"
BLOCKED = "blocked"

IMMEDIATE = "immediate"
NEAR_TERM = "near_term"
DEFER = "defer"

DEATH = "death"
INCAPACITY = "incapacity"
BOTH = "both"

#: Operational contact/location facts change more often than estate documents.
#: An annual check is a maintenance cadence, not a legal deadline.
REVIEW_INTERVAL_DAYS = 366

PHASE_ORDER = {IMMEDIATE: 0, NEAR_TERM: 1, DEFER: 2}
CATEGORY_ORDER = {
    "life_safety": 0,
    "dependent_care": 1,
    "pet_care": 2,
    "property": 3,
    "business": 4,
    "plan_access": 10,
    "authorized_help": 11,
    "cash_flow": 20,
    "coverage": 21,
    "legal": 30,
    "benefits": 31,
    "institution": 32,
    "optimization": 40,
    "other": 50,
}

CONTACT_ROLES = {
    "trusted_helper",
    "estate_attorney",
    "tax_professional",
    "employer_benefits",
    "insurance_claims",
    "financial_institution",
    "government_benefits",
    "healthcare_agent",
    "dependent_care",
    "property",
    "business",
    "other",
}
DUTY_CATEGORIES = {
    "life_safety",
    "dependent_care",
    "pet_care",
    "property",
    "business",
    "other",
}
OBLIGATION_CATEGORIES = {
    "housing",
    "utilities",
    "insurance",
    "debt",
    "dependent_care",
    "pet_care",
    "property",
    "business",
    "other",
}
EVENTS = {DEATH, INCAPACITY, BOTH}

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(?:password|passcode|pin|recovery\s+code|seed\s+phrase|"
    r"private\s+key|social\s+security\s+number|ssn)\s*[:=]\s*\S+"
)
_LONG_DIGIT_SEQUENCE = re.compile(r"(?<!\d)(?:\d[\s-]?){8,}(?!\d)")


class ContinuityError(ValueError):
    """Continuity facts have an invalid shape or contradictory value."""


@dataclass(frozen=True)
class ReadinessFinding:
    key: str
    critical: bool
    detail: str


@dataclass(frozen=True)
class Contact:
    contact_id: str
    role: str
    label: str
    contact_via: str
    confirmed: bool | None
    authority_scope_recorded: bool | None


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    label: str
    category: str
    cadence: str
    autopay_status: bool | None
    instruction: str


@dataclass(frozen=True)
class Duty:
    duty_id: str
    label: str
    category: str
    applies_to: str
    instruction: str
    confirmed: bool | None


@dataclass(frozen=True)
class PlanAction:
    action_id: str
    path: str
    phase: str
    category: str
    action: str
    detail: str


@dataclass(frozen=True)
class InventoryLine:
    subject: str
    amount: float | None
    status: str
    detail: str


@dataclass(frozen=True)
class TransferRecord:
    subject: str
    recorded_route: str
    review_status: str


@dataclass
class ContinuityPlan:
    readiness: str
    intended_reader: str
    reviewed_on: dt.date | None
    review_age_days: int | None
    findings: list[ReadinessFinding] = field(default_factory=list)
    actions: list[PlanAction] = field(default_factory=list)
    contacts: list[Contact] = field(default_factory=list)
    obligations: list[Obligation] = field(default_factory=list)
    inventory: list[InventoryLine] = field(default_factory=list)
    transfers: list[TransferRecord] = field(default_factory=list)
    locations: list[tuple[str, str]] = field(default_factory=list)
    document_audit: E.Audit = field(default_factory=E.Audit)
    digital_audit: E.Audit = field(default_factory=E.Audit)
    review_triggers: tuple[str, ...] = ()

    @property
    def critical_gaps(self) -> list[ReadinessFinding]:
        return [finding for finding in self.findings if finding.critical]

    @property
    def noncritical_gaps(self) -> list[ReadinessFinding]:
        return [finding for finding in self.findings if not finding.critical]


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ContinuityError(f"{label} must be a mapping")
    return value


def _rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ContinuityError(f"{label} must be a list")
    rows = list(value)
    if any(not isinstance(row, Mapping) for row in rows):
        raise ContinuityError(f"every {label} item must be a mapping")
    return rows


def _optional_bool(value: Any, label: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ContinuityError(f"{label} must be true, false, or null")
    return value


def _identifier(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContinuityError(f"{label} must be a non-empty string")
    return value.strip()


def display_safe(value: Any, fallback: str) -> tuple[str, bool]:
    """Return printable text and whether it passed the obvious-secret guard.

    This is defense in depth, not secret detection.  The schema still forbids
    raw credentials.  Long numeric strings are suppressed because a printable
    plan needs a pointer to the private contact/account card, not an account,
    policy, phone, or recovery identifier copied into another artifact.
    """
    if not isinstance(value, str) or not value.strip():
        return fallback, False
    text = " ".join(value.split()).replace("|", "\\|")
    if _SECRET_ASSIGNMENT.search(text) or _LONG_DIGIT_SEQUENCE.search(text):
        return fallback, False
    return text, True


def _add_gap(
    findings: list[ReadinessFinding],
    key: str,
    detail: str,
    *,
    critical: bool,
) -> None:
    if not any(item.key == key for item in findings):
        findings.append(ReadinessFinding(key, critical, detail))


def _parse_contacts(
    section: Mapping[str, Any],
    findings: list[ReadinessFinding],
) -> list[Contact]:
    rows = _rows(section.get("contacts"), "continuity.contacts")
    contacts: list[Contact] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        contact_id = _identifier(row.get("id"), f"contact #{index + 1} id")
        if contact_id is None:
            _add_gap(
                findings,
                f"contact-{index + 1}-id",
                f"Contact #{index + 1} has no stable ID.",
                critical=False,
            )
            contact_id = f"contact-{index + 1}"
        if contact_id in seen:
            raise ContinuityError(f"duplicate continuity contact id: {contact_id}")
        seen.add(contact_id)

        role = _identifier(row.get("role"), f"contact {contact_id} role")
        if role is None:
            role = "other"
            _add_gap(
                findings,
                f"contact-{contact_id}-role",
                f"Contact `{contact_id}` has no recorded role.",
                critical=False,
            )
        elif role not in CONTACT_ROLES:
            raise ContinuityError(f"contact {contact_id} has unsupported role {role!r}")

        label, label_safe = display_safe(
            row.get("label"), f"{role.replace('_', ' ').title()} contact"
        )
        contact_via, via_safe = display_safe(
            row.get("contact_via"), "NEEDS COMPLETION — contact reference"
        )
        safe_id, _safe = display_safe(contact_id, "recorded contact")
        if not label_safe or not via_safe:
            _add_gap(
                findings,
                f"contact-{contact_id}-display",
                f"Contact `{safe_id}` needs a display-safe label and "
                "contact reference; raw secrets and long identifiers are "
                "suppressed.",
                critical=role == "trusted_helper",
            )
        confirmed = _optional_bool(
            row.get("confirmed"), f"contact {contact_id} confirmed"
        )
        if confirmed is not True:
            _add_gap(
                findings,
                f"contact-{contact_id}-confirmation",
                f"Contact `{safe_id}` has not been confirmed reachable.",
                critical=False,
            )
        contacts.append(
            Contact(
                contact_id=contact_id,
                role=role,
                label=label,
                contact_via=contact_via,
                confirmed=confirmed,
                authority_scope_recorded=_optional_bool(
                    row.get("authority_scope_recorded"),
                    f"contact {contact_id} authority scope",
                ),
            )
        )
    return contacts


def _parse_obligations(
    section: Mapping[str, Any],
    findings: list[ReadinessFinding],
) -> list[Obligation]:
    rows = _rows(
        section.get("essential_obligations"), "continuity.essential_obligations"
    )
    obligations: list[Obligation] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        oid = _identifier(row.get("id"), f"obligation #{index + 1} id")
        if oid is None:
            oid = f"obligation-{index + 1}"
            _add_gap(
                findings,
                f"{oid}-id",
                f"Essential obligation #{index + 1} needs a stable ID.",
                critical=False,
            )
        if oid in seen:
            raise ContinuityError(f"duplicate continuity obligation id: {oid}")
        seen.add(oid)
        category = (
            _identifier(row.get("category"), f"obligation {oid} category") or "other"
        )
        if category not in OBLIGATION_CATEGORIES:
            raise ContinuityError(
                f"obligation {oid} has unsupported category {category!r}"
            )
        label, label_safe = display_safe(
            row.get("label"), "NEEDS COMPLETION — obligation label"
        )
        cadence, cadence_safe = display_safe(
            row.get("cadence"), "NEEDS COMPLETION — payment cadence"
        )
        instruction, instruction_safe = display_safe(
            row.get("continuation_instruction"),
            "NEEDS COMPLETION — continuation instruction",
        )
        autopay = _optional_bool(
            row.get("autopay_status"), f"obligation {oid} autopay status"
        )
        if not all((label_safe, cadence_safe, instruction_safe)) or autopay is None:
            safe_id, _safe = display_safe(oid, "recorded obligation")
            _add_gap(
                findings,
                f"obligation-{oid}-operation",
                f"Essential obligation `{safe_id}` lacks a safe label, cadence, "
                "continuation instruction, or confirmed autopay status.",
                critical=True,
            )
        obligations.append(
            Obligation(
                obligation_id=oid,
                label=label,
                category=category,
                cadence=cadence,
                autopay_status=autopay,
                instruction=instruction,
            )
        )
    return obligations


def _parse_duties(
    section: Mapping[str, Any],
    findings: list[ReadinessFinding],
) -> list[Duty]:
    rows = _rows(section.get("immediate_duties"), "continuity.immediate_duties")
    duties: list[Duty] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        did = _identifier(row.get("id"), f"duty #{index + 1} id")
        if did is None:
            did = f"duty-{index + 1}"
            _add_gap(
                findings,
                f"{did}-id",
                f"Immediate duty #{index + 1} needs a stable ID.",
                critical=False,
            )
        if did in seen:
            raise ContinuityError(f"duplicate continuity duty id: {did}")
        seen.add(did)
        category = _identifier(row.get("category"), f"duty {did} category")
        category = category or "other"
        if category not in DUTY_CATEGORIES:
            raise ContinuityError(f"duty {did} has unsupported category {category!r}")
        applies_to = (
            _identifier(row.get("applies_to"), f"duty {did} applies_to") or BOTH
        )
        if applies_to not in EVENTS:
            raise ContinuityError(
                f"duty {did} has unsupported applies_to {applies_to!r}"
            )
        label, label_safe = display_safe(
            row.get("label"), "NEEDS COMPLETION — immediate duty"
        )
        instruction, instruction_safe = display_safe(
            row.get("instruction"),
            "NEEDS COMPLETION — duty instruction",
        )
        confirmed = _optional_bool(row.get("confirmed"), f"duty {did} confirmed")
        if not label_safe or not instruction_safe or confirmed is not True:
            safe_id, _safe = display_safe(did, "recorded duty")
            _add_gap(
                findings,
                f"duty-{did}-operation",
                f"Immediate duty `{safe_id}` lacks a safe instruction or has not "
                "been confirmed.",
                critical=category != "other",
            )
        duties.append(
            Duty(
                duty_id=did,
                label=label,
                category=category,
                applies_to=applies_to,
                instruction=instruction,
                confirmed=confirmed,
            )
        )
    return duties


def _inventory(
    data: Mapping[str, Any],
    obligations: list[Obligation],
    findings: list[ReadinessFinding],
    as_of: dt.date,
) -> list[InventoryLine]:
    household = _mapping(data.get("household"), "household")
    members = _rows(household.get("members"), "household.members")
    adults = [row for row in members if row.get("role") in ("primary", "spouse")]
    income_unknown = [row for row in adults if row.get("income_annual") is None]
    income = F.household_income(dict(data))
    if income_unknown:
        findings.append(
            ReadinessFinding(
                "income-inventory",
                False,
                f"Income is not recorded for {len(income_unknown)} adult member(s).",
            )
        )
    income_line = InventoryLine(
        "Annual household income",
        None if income_unknown else income,
        "partial" if income_unknown else "recorded",
        "Gross annual income from household members; eligibility and duration "
        "are not inferred.",
    )

    balance_sheet_raw = household.get("balance_sheet")
    reserve = F.reserve_assets(dict(data))
    if balance_sheet_raw is None:
        _add_gap(
            findings,
            "asset-inventory",
            "The household balance sheet is not recorded, so available "
            "resources and institution notifications cannot be established.",
            critical=True,
        )
        reserve_amount = None
        reserve_status = "unknown"
    else:
        reserve_amount = reserve.included
        reserve_status = "partial" if reserve.unknown else "recorded"
        if reserve.unknown:
            _add_gap(
                findings,
                "reserve-classification",
                f"{len(reserve.unknown)} asset(s) lack a liquidity class; "
                "they are not treated as cash-equivalent resources.",
                critical=False,
            )
    reserve_line = InventoryLine(
        "Cash-equivalent resources",
        reserve_amount,
        reserve_status,
        "Uses the shared reserve-asset classification; marketable investments "
        "are not presented as cash.",
    )

    insurance = _mapping(data.get("insurance"), "insurance")
    policies_raw = insurance.get("life") if "insurance" in data else None
    if policies_raw is None:
        _add_gap(
            findings,
            "life-insurance-inventory",
            "Life-insurance policies are not recorded; unknown is not an "
            "explicit statement that no claim exists.",
            critical=True,
        )
        insurance_line = InventoryLine(
            "Life-insurance death benefit",
            None,
            "unknown",
            "Run `life-insurance-review` after recording the policy inventory.",
        )
    else:
        policies = _rows(policies_raw, "insurance.life")
        assessment = L.assess([dict(row) for row in policies], need=0, today=as_of)
        insurance_line = InventoryLine(
            "Life-insurance death benefit",
            assessment.in_force_portable + assessment.in_force_group,
            "recorded",
            f"{assessment.in_force_portable:,.0f} portable and "
            f"{assessment.in_force_group:,.0f} employer-provided; this is an "
            "inventory, not a claim or tax promise.",
        )

    debts_raw = data.get("debts")
    if debts_raw is None:
        _add_gap(
            findings,
            "debt-inventory",
            "Debts are not recorded; use an explicit empty list when none exist.",
            critical=False,
        )
        debt_line = InventoryLine(
            "Recorded debt balances",
            None,
            "unknown",
            "No debt inventory is available.",
        )
    else:
        debt_rows = _rows(debts_raw, "debts")
        missing_balances = sum(row.get("balance") is None for row in debt_rows)
        parsed = D.parse([dict(row) for row in debt_rows])
        debt_line = InventoryLine(
            "Recorded debt balances",
            None if missing_balances else sum(row.balance for row in parsed),
            "partial" if missing_balances else "recorded",
            (
                f"{missing_balances} debt balance(s) are unknown."
                if missing_balances
                else "Balances only; payoff, acceleration, and estate treatment are "
                "outside this runbook."
            ),
        )
        if missing_balances:
            _add_gap(
                findings,
                "debt-balances",
                f"{missing_balances} debt balance(s) are not recorded.",
                critical=False,
            )

    obligations_line = InventoryLine(
        "Essential recurring obligations",
        None,
        "recorded" if obligations else "unknown",
        f"{len(obligations)} obligation(s) have continuity instructions."
        if obligations
        else "No operational obligations are listed.",
    )
    return [income_line, insurance_line, reserve_line, debt_line, obligations_line]


def _beneficiary_audit(
    data: Mapping[str, Any],
) -> tuple[E.Audit, list[tuple[str, str, Mapping[str, Any]]]]:
    household = _mapping(data.get("household"), "household")
    assets = _rows(household.get("balance_sheet"), "household.balance_sheet")
    insurance = _mapping(data.get("insurance"), "insurance")
    policies = _rows(insurance.get("life"), "insurance.life")
    members = _rows(household.get("members"), "household.members")
    member_roles = {
        str(row.get("id")): row.get("role")
        for row in members
        if row.get("id") is not None
    }

    def normalized(row: Mapping[str, Any]) -> Mapping[str, Any]:
        """Translate the schema's beneficiary shorthand for the shared audit."""
        if "beneficiaries" in row or row.get("beneficiary_applicable") is False:
            return row
        if "beneficiary_primary" not in row:
            return row

        result = dict(row)
        beneficiaries: list[dict[str, Any]] = []
        for kind, key in (
            ("primary", "beneficiary_primary"),
            ("contingent", "beneficiary_contingent"),
        ):
            target = row.get(key)
            if target is None:
                continue
            entry: dict[str, Any] = {"type": kind, "share": 100}
            target_text = str(target)
            if target_text in member_roles:
                entry["member_id"] = target_text
                entry["relationship"] = member_roles[target_text]
            elif target_text in {"trust", "estate", "charity"}:
                entry["relationship"] = target_text
            else:
                entry["name"] = target_text
                entry["relationship"] = "other"
            beneficiaries.append(entry)
        result["beneficiaries"] = beneficiaries
        return result

    items: list[tuple[str, str, Mapping[str, Any]]] = []
    for index, row in enumerate(assets):
        items.append(
            (f"asset-{index + 1}", f"Asset {index + 1}", normalized(row))
        )
    for index, row in enumerate(policies):
        items.append(
            (f"policy-{index + 1}", f"Policy {index + 1}", normalized(row))
        )

    estate = _mapping(data.get("estate"), "estate")
    docs = _rows(estate.get("documents"), "estate.documents")
    trust = next((row for row in docs if row.get("type") == "revocable_trust"), None)
    audit = E.audit_beneficiaries(
        [(internal, dict(row)) for internal, _fallback, row in items],
        members=[dict(row) for row in members],
        trust_funded=trust.get("funded") if trust else None,
    )
    return audit, items


def _recorded_route(row: Mapping[str, Any], *, policy: bool) -> str:
    facts: list[str] = []
    title = row.get("titled_to")
    if title is not None and not policy:
        title_text, safe = display_safe(title, "title withheld")
        facts.append(f"title recorded as {title_text}" if safe else "title withheld")

    if row.get("beneficiary_applicable") is False:
        facts.append("beneficiary designation recorded as not applicable")
    elif "beneficiaries" not in row:
        facts.append("beneficiary designation not recorded")
    else:
        beneficiaries = row.get("beneficiaries")
        if not beneficiaries:
            facts.append("beneficiary list checked; none recorded")
        elif isinstance(beneficiaries, Sequence) and not isinstance(
            beneficiaries, (str, bytes)
        ):
            destinations: list[str] = []
            for beneficiary in beneficiaries:
                if not isinstance(beneficiary, Mapping):
                    continue
                designation = str(beneficiary.get("type") or "unspecified")
                member_id = beneficiary.get("member_id")
                relationship = beneficiary.get("relationship")
                if member_id:
                    target, _safe = display_safe(member_id, "member")
                    target = f"member {target}"
                elif relationship:
                    target, _safe = display_safe(relationship, "recorded party")
                else:
                    target = "recorded party"
                destinations.append(f"{designation} → {target}")
            facts.append(
                "; ".join(destinations)
                if destinations
                else "beneficiary entries cannot be summarized"
            )
        else:
            facts.append("beneficiary entries have an invalid shape")
    return "; ".join(facts) or "transfer facts not recorded"


def _transfers(
    audit: E.Audit,
    items: list[tuple[str, str, Mapping[str, Any]]],
) -> list[TransferRecord]:
    severity_order = {"blocker": 0, "gap": 1, "note": 2, "ok": 3}
    records: list[TransferRecord] = []
    for index, (internal, fallback, row) in enumerate(items):
        label, _safe = display_safe(
            row.get("label") or row.get("name") or row.get("id"), fallback
        )
        findings = [
            finding for finding in audit.findings if finding.subject == internal
        ]
        severity = min(
            (finding.severity for finding in findings),
            key=lambda value: severity_order[value],
            default="not reviewed",
        )
        if row.get("beneficiary_applicable") is False and not findings:
            review_status = "designation recorded as not applicable"
        elif severity == "ok":
            review_status = "No issue found by the designation audit"
        else:
            review_status = f"{severity}; review with `beneficiary-audit`"
        records.append(
            TransferRecord(
                subject=label,
                recorded_route=_recorded_route(
                    row, policy=internal.startswith("policy-")
                ),
                review_status=review_status,
            )
        )
    return records


def _actions(
    contacts: list[Contact],
    duties: list[Duty],
    obligations: list[Obligation],
    locations: dict[str, str],
    helper: Contact | None,
) -> list[PlanAction]:
    actions: list[PlanAction] = []

    def add(
        action_id: str,
        path: str,
        phase: str,
        category: str,
        action: str,
        detail: str,
    ) -> None:
        actions.append(PlanAction(action_id, path, phase, category, action, detail))

    for path in (DEATH, INCAPACITY):
        add(
            f"{path}-safety",
            path,
            IMMEDIATE,
            "life_safety",
            "Stabilize people and urgent care first",
            "Handle immediate medical, physical-safety, dependent, and pet "
            "needs before administrative work.",
        )
        plan_location = locations.get("offline_plan_copy")
        add(
            f"{path}-open-plan",
            path,
            IMMEDIATE,
            "plan_access",
            "Open the offline continuity plan",
            plan_location or "NEEDS COMPLETION — offline copy location",
        )
        add(
            f"{path}-helper",
            path,
            IMMEDIATE,
            "authorized_help",
            "Contact the recorded trusted helper",
            (
                f"{helper.label} — {helper.contact_via}"
                if helper
                else "NEEDS COMPLETION — authorized helper"
            ),
        )

    healthcare_agent = next(
        (
            contact
            for contact in contacts
            if contact.role == "healthcare_agent" and contact.confirmed is True
        ),
        None,
    )
    add(
        "incapacity-healthcare-agent",
        INCAPACITY,
        IMMEDIATE,
        "authorized_help",
        "Contact the recorded healthcare agent",
        (
            f"{healthcare_agent.label} — {healthcare_agent.contact_via}"
            if healthcare_agent
            else "NEEDS COMPLETION — confirmed healthcare-agent contact"
        ),
    )

    for duty in duties:
        paths = (DEATH, INCAPACITY) if duty.applies_to == BOTH else (duty.applies_to,)
        for path in paths:
            add(
                f"{path}-duty-{duty.duty_id}",
                path,
                IMMEDIATE,
                duty.category,
                duty.label,
                duty.instruction,
            )

    obligation_detail = (
        f"Use the recorded instructions for {len(obligations)} essential "
        "obligation(s); verify before changing payment methods."
        if obligations
        else "NEEDS COMPLETION — no essential-obligation instructions are recorded."
    )
    for path in (DEATH, INCAPACITY):
        add(
            f"{path}-cash-flow",
            path,
            IMMEDIATE,
            "cash_flow",
            "Keep essential obligations and coverage in force",
            obligation_detail,
        )

    event_roles = {
        DEATH: (
            "insurance_claims",
            "employer_benefits",
            "financial_institution",
            "government_benefits",
            "estate_attorney",
            "tax_professional",
        ),
        INCAPACITY: (
            "employer_benefits",
            "financial_institution",
            "estate_attorney",
            "tax_professional",
        ),
    }
    for path, roles in event_roles.items():
        for role in roles:
            for contact in contacts:
                if contact.role != role or contact.confirmed is not True:
                    continue
                category = (
                    "coverage"
                    if role == "insurance_claims"
                    else "benefits"
                    if role in ("employer_benefits", "government_benefits")
                    else "legal"
                    if role in ("estate_attorney", "tax_professional")
                    else "institution"
                )
                add(
                    f"{path}-contact-{contact.contact_id}",
                    path,
                    NEAR_TERM,
                    category,
                    f"Contact {contact.label}",
                    f"{contact.contact_via}. Ask what proof and authority the "
                    "institution requires; do not assume a timeline or result.",
                )

    for path in (DEATH, INCAPACITY):
        add(
            f"{path}-defer-changes",
            path,
            DEFER,
            "optimization",
            "Defer irreversible financial changes",
            "Do not sell, retitle, roll over, surrender, gift, or sign a new "
            "financial arrangement until authority, tax, beneficiary, and "
            "liquidity consequences have been reviewed.",
        )
    return sorted(
        actions,
        key=lambda item: (
            PHASE_ORDER[item.phase],
            CATEGORY_ORDER[item.category],
            item.path,
            item.action_id,
        ),
    )


def build_plan(data: Mapping[str, Any]) -> ContinuityPlan:
    """Build an operational plan without mutating or enriching the facts."""
    as_of = F.as_of(dict(data))
    if as_of is None:
        raise ContinuityError("meta.as_of must be a valid ISO date")
    section = _mapping(data.get("continuity"), "continuity")
    household = _mapping(data.get("household"), "household")
    members = _rows(household.get("members"), "household.members")
    member_ids = {str(row.get("id")) for row in members if row.get("id") is not None}
    findings: list[ReadinessFinding] = []

    reader_id = _identifier(
        section.get("intended_reader_id"), "continuity intended reader"
    )
    if reader_id is None or reader_id not in member_ids:
        _add_gap(
            findings,
            "intended-reader",
            "The intended reader is missing or does not match a stable "
            "household member ID.",
            critical=True,
        )
        intended_reader = "NEEDS COMPLETION"
    else:
        member = next(row for row in members if str(row.get("id")) == reader_id)
        role, _safe = display_safe(member.get("role"), "household member")
        safe_id, _safe = display_safe(reader_id, "recorded member")
        intended_reader = f"{role} ({safe_id})"

    knows_location = _optional_bool(
        section.get("intended_reader_knows_location"),
        "continuity intended_reader_knows_location",
    )
    if knows_location is not True:
        _add_gap(
            findings,
            "reader-knows-location",
            "The intended reader has not confirmed where the offline plan is.",
            critical=True,
        )

    location_fields = (
        ("offline_plan_copy", "Offline plan copy", True),
        ("document_package", "Estate/document package", True),
        ("tax_records", "Tax records", False),
        ("account_inventory", "Account inventory", True),
        ("recovery_package", "Sealed recovery package", True),
    )
    locations: dict[str, str] = {}
    location_rows: list[tuple[str, str]] = []
    for key, label, critical in location_fields:
        value, safe = display_safe(section.get(f"{key}_location"), "NEEDS COMPLETION")
        if not safe:
            _add_gap(
                findings,
                f"{key}-location",
                f"{label} needs a display-safe location reference.",
                critical=critical,
            )
        else:
            locations[key] = value
        location_rows.append((label, value))

    contacts = _parse_contacts(section, findings)
    by_contact_id = {contact.contact_id: contact for contact in contacts}
    helper_id = _identifier(
        section.get("authorized_helper_contact_id"),
        "continuity authorized helper contact id",
    )
    helper = by_contact_id.get(helper_id) if helper_id else None
    helper_ready = (
        helper is not None
        and helper.role == "trusted_helper"
        and helper.confirmed is True
        and helper.authority_scope_recorded is True
    )
    if helper is None or helper.role != "trusted_helper":
        _add_gap(
            findings,
            "authorized-helper",
            "No trusted-helper contact is linked as the authorized helper.",
            critical=True,
        )
    elif helper.confirmed is not True or helper.authority_scope_recorded is not True:
        _add_gap(
            findings,
            "authorized-helper-confirmation",
            "The trusted helper or the recorded scope of authority is not "
            "confirmed; the plan does not infer legal authority.",
            critical=True,
        )

    obligations = _parse_obligations(section, findings)
    obligations_reviewed = _optional_bool(
        section.get("essential_obligations_reviewed"),
        "continuity essential_obligations_reviewed",
    )
    if obligations_reviewed is not True:
        _add_gap(
            findings,
            "essential-obligations-reviewed",
            "Essential recurring obligations have not been explicitly reviewed.",
            critical=True,
        )

    duties = _parse_duties(section, findings)
    dependents = [row for row in members if row.get("role") == "dependent"]
    if dependents and not any(
        duty.category == "dependent_care" and duty.confirmed is True for duty in duties
    ):
        _add_gap(
            findings,
            "dependent-care-duty",
            "Dependents are recorded but no confirmed immediate-care duty is.",
            critical=True,
        )
    if data.get("business") and not any(
        duty.category == "business" and duty.confirmed is True for duty in duties
    ):
        _add_gap(
            findings,
            "business-duty",
            "A business is recorded but no confirmed immediate continuity "
            "duty is available.",
            critical=True,
        )

    estate = _mapping(data.get("estate"), "estate")
    docs = _rows(estate.get("documents"), "estate.documents")
    dom = _mapping(household.get("domicile"), "household.domicile")
    meta = _mapping(data.get("meta"), "meta")
    jurisdiction = _mapping(meta.get("jurisdiction"), "meta.jurisdiction")
    country = str(jurisdiction.get("country") or "").upper()
    non_citizen_spouse = country == "US" and any(
        row.get("role") == "spouse"
        and row.get("us_status")
        and row.get("us_status") != "citizen"
        for row in members
    )
    document_audit = E.audit_documents(
        [dict(row) for row in docs],
        today=as_of,
        non_citizen_spouse=non_citizen_spouse,
        domicile_determined=dom.get("determined") if dom else None,
    )
    by_doc = {row.get("type"): row for row in docs}
    for doc_type, label in (
        ("financial_poa", "financial power of attorney"),
        ("healthcare_poa", "healthcare power of attorney"),
    ):
        if (by_doc.get(doc_type) or {}).get("exists") is not True:
            _add_gap(
                findings,
                f"document-{doc_type}",
                f"A usable {label} is not confirmed for the incapacity path.",
                critical=True,
            )
        elif any(
            item.subject == doc_type and item.severity != "ok"
            for item in document_audit.findings
        ):
            _add_gap(
                findings,
                f"document-{doc_type}-review",
                f"The shared estate audit has an open review item for the {label}.",
                critical=False,
            )
    if (by_doc.get("will") or {}).get("exists") is not True:
        _add_gap(
            findings,
            "document-will",
            "A will is not confirmed; the report cannot establish the death "
            "transfer path.",
            critical=False,
        )
    other_document_gaps = [
        item
        for item in document_audit.findings
        if item.severity != "ok"
        and item.subject not in {"financial_poa", "healthcare_poa", "will"}
    ]
    if other_document_gaps:
        _add_gap(
            findings,
            "estate-audit",
            f"The shared estate-document audit has {len(other_document_gaps)} "
            "additional open finding(s).",
            critical=False,
        )

    digital_raw = estate.get("digital")
    digital = _mapping(digital_raw, "estate.digital")
    digital_audit = E.audit_digital(dict(digital) if digital_raw is not None else None)
    recovery_tested = _optional_bool(
        section.get("recovery_process_tested"),
        "continuity recovery_process_tested",
    )
    if recovery_tested is not True:
        _add_gap(
            findings,
            "recovery-test",
            "The intended reader has not completed an end-to-end recovery test.",
            critical=True,
        )
    if digital.get("account_inventory") is not True:
        _add_gap(
            findings,
            "digital-account-inventory",
            "A reachable account inventory is not confirmed.",
            critical=True,
        )
    if digital.get("two_factor_recovery_documented") is not True:
        _add_gap(
            findings,
            "digital-two-factor",
            "Two-factor recovery is not confirmed in the sealed recovery path.",
            critical=True,
        )
    if (
        digital.get("password_manager") is True
        and digital.get("emergency_access_configured") is not True
    ):
        _add_gap(
            findings,
            "digital-emergency-access",
            "The password manager is recorded without confirmed emergency access.",
            critical=True,
        )
    other_digital_gaps = [
        item
        for item in digital_audit.findings
        if item.severity != "ok"
        and item.subject
        not in {
            "account_inventory",
            "two_factor_recovery_documented",
            "emergency_access_configured",
            "combination",
        }
    ]
    if other_digital_gaps:
        _add_gap(
            findings,
            "digital-audit",
            f"The shared digital-access audit has {len(other_digital_gaps)} "
            "additional open finding(s).",
            critical=False,
        )

    balance_sheet = household.get("balance_sheet")
    insurance = _mapping(data.get("insurance"), "insurance")
    policies = insurance.get("life") if "insurance" in data else None
    required_roles = {"trusted_helper", "healthcare_agent"}
    if any(row.get("employer") for row in members):
        required_roles.add("employer_benefits")
    if policies:
        required_roles.add("insurance_claims")
    if balance_sheet:
        required_roles.add("financial_institution")
    if data.get("social_security"):
        required_roles.add("government_benefits")
    notification_reviewed = _optional_bool(
        section.get("notification_contacts_reviewed"),
        "continuity notification_contacts_reviewed",
    )
    if notification_reviewed is not True:
        _add_gap(
            findings,
            "notification-review",
            "Institution and professional notification contacts have not "
            "been explicitly reviewed.",
            critical=True,
        )
    present_roles = {contact.role for contact in contacts if contact.confirmed is True}
    missing_roles = sorted(required_roles - present_roles)
    if missing_roles:
        _add_gap(
            findings,
            "notification-contacts",
            "Confirmed contact references are missing for: "
            + ", ".join(role.replace("_", " ") for role in missing_roles)
            + ".",
            critical=True,
        )
    healthcare_agent = next(
        (contact for contact in contacts if contact.role == "healthcare_agent"),
        None,
    )
    if (
        healthcare_agent is not None
        and healthcare_agent.authority_scope_recorded is not True
    ):
        _add_gap(
            findings,
            "healthcare-agent-authority",
            "The healthcare agent's authority scope is not recorded; the "
            "plan does not infer authority from the contact role.",
            critical=True,
        )

    inventory = _inventory(data, obligations, findings, as_of)
    beneficiary_audit, transfer_items = _beneficiary_audit(data)
    transfers = _transfers(beneficiary_audit, transfer_items)
    beneficiary_gaps = [
        item for item in beneficiary_audit.findings if item.severity != "ok"
    ]
    if beneficiary_gaps:
        _add_gap(
            findings,
            "beneficiary-audit",
            f"The shared beneficiary audit has {len(beneficiary_gaps)} open "
            "finding(s); transfer rows remain recorded facts, not legal "
            "conclusions.",
            critical=False,
        )

    reviewed_on = F._as_date(section.get("plan_last_reviewed"))
    if section.get("plan_last_reviewed") is not None and reviewed_on is None:
        raise ContinuityError("continuity.plan_last_reviewed must be an ISO date")
    if reviewed_on is not None and reviewed_on > as_of:
        raise ContinuityError("continuity.plan_last_reviewed cannot be in the future")
    review_age_days = (as_of - reviewed_on).days if reviewed_on else None
    if review_age_days is None:
        _add_gap(
            findings,
            "plan-review-date",
            "The continuity plan has no recorded review date.",
            critical=False,
        )
    elif review_age_days > REVIEW_INTERVAL_DAYS:
        _add_gap(
            findings,
            "plan-review-stale",
            f"The continuity plan was reviewed {review_age_days} days ago, "
            f"past the {REVIEW_INTERVAL_DAYS}-day maintenance cadence.",
            critical=False,
        )

    raw_triggers = section.get("review_triggers")
    if raw_triggers is None:
        triggers: tuple[str, ...] = ()
    elif isinstance(raw_triggers, Sequence) and not isinstance(
        raw_triggers, (str, bytes)
    ):
        trigger_values: list[str] = []
        for index, value in enumerate(raw_triggers):
            text, safe = display_safe(value, "NEEDS COMPLETION")
            if not safe:
                _add_gap(
                    findings,
                    f"review-trigger-{index + 1}",
                    f"Review trigger #{index + 1} is missing or not display-safe.",
                    critical=False,
                )
            else:
                trigger_values.append(text)
        triggers = tuple(trigger_values)
    else:
        raise ContinuityError("continuity.review_triggers must be a list")
    if not triggers:
        _add_gap(
            findings,
            "review-triggers",
            "No events are recorded that trigger an immediate plan refresh.",
            critical=False,
        )

    actions = _actions(
        contacts,
        duties,
        obligations,
        locations,
        helper if helper_ready else None,
    )
    findings.sort(key=lambda item: (not item.critical, item.key))
    readiness = (
        BLOCKED
        if any(item.critical for item in findings)
        else INCOMPLETE
        if findings
        else READY
    )
    return ContinuityPlan(
        readiness=readiness,
        intended_reader=intended_reader,
        reviewed_on=reviewed_on,
        review_age_days=review_age_days,
        findings=findings,
        actions=actions,
        contacts=contacts,
        obligations=obligations,
        inventory=inventory,
        transfers=transfers,
        locations=location_rows,
        document_audit=document_audit,
        digital_audit=digital_audit,
        review_triggers=triggers,
    )
