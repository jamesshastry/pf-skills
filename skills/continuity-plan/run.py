#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Render a printable death and incapacity continuity plan."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, continuity as C, skill_metrics as M  # noqa: E402

REQUIRED = ["meta.as_of", "meta.currency", "household.members"]

READINESS = {
    C.READY: "✅ READY",
    C.INCOMPLETE: "⚠️ INCOMPLETE",
    C.BLOCKED: "🚫 BLOCKED",
}
PHASE = {
    C.IMMEDIATE: "Immediate",
    C.NEAR_TERM: "Near term",
    C.DEFER: "Defer",
}


def _status(value: bool | None) -> str:
    if value is True:
        return "confirmed"
    if value is False:
        return "recorded no"
    return "NEEDS COMPLETION"


def _audit_status(value: str) -> str:
    return {
        "blocker": "🚫 blocker",
        "gap": "⚠️ gap",
        "note": "note",
        "ok": "recorded",
    }.get(value, value)


def build(data: dict, w: cli.Writer) -> None:
    plan = C.build_plan(data)
    w.add_metrics(M.emit("continuity-plan", data))
    currency = str(data["meta"]["currency"])

    w(f"**Operational readiness: {READINESS[plan.readiness]}**")
    w()
    w(
        f"Intended reader: **{plan.intended_reader}**. This answers one "
        "question: could that reader execute the first steps without the plan "
        "author? It does not certify legal authority or estate outcomes."
    )

    for path, title in (
        (C.DEATH, "If the plan author dies"),
        (C.INCAPACITY, "If the plan author is incapacitated"),
    ):
        w()
        w(f"## {title}")
        w()
        actions = [action for action in plan.actions if action.path == path]
        w.table(
            ["When", "Priority", "Action", "How"],
            [
                [
                    PHASE[action.phase],
                    action.category.replace("_", " "),
                    action.action,
                    action.detail,
                ]
                for action in actions
            ],
        )

    w()
    w("## During stabilization: do not")
    w()
    w(
        "- Do not sell, retitle, roll over, surrender, gift, or consolidate "
        "assets before authority, beneficiary, tax, and liquidity effects are "
        "reviewed."
    )
    w(
        "- Do not cancel insurance, autopay, housing, utilities, or essential "
        "services until each obligation and claim path is verified."
    )
    w(
        "- Do not share passwords or recovery codes. Follow the sealed recovery "
        "process instead."
    )
    w(
        "- Do not sign an investment, insurance, property, or advisory agreement "
        "under pressure. Irreversible optimization can wait until the facts and "
        "authority are clear."
    )

    w()
    w("## People and institutions")
    w()
    if plan.contacts:
        w.table(
            ["Role", "Display-safe contact", "How to reach", "Status"],
            [
                [
                    contact.role.replace("_", " "),
                    contact.label,
                    contact.contact_via,
                    _status(contact.confirmed),
                ]
                for contact in plan.contacts
            ],
        )
    else:
        w("**NEEDS COMPLETION:** no contact references are recorded.")
    w()
    w(
        "Contact references point to the private contact card. Credentials and "
        "full identifiers never belong in this printable plan."
    )

    w()
    w("## Income, insurance, resources, debts, and bills")
    w()
    w(f"Amounts below are nominal {currency} from the current facts file.")
    w()
    w.table(
        ["Area", "Recorded amount", "Status", "What it means"],
        [
            [
                line.subject,
                (
                    f"{line.amount:,.0f} {currency}"
                    if line.amount is not None
                    else "not summed"
                    if line.subject == "Essential recurring obligations"
                    else "unknown"
                ),
                line.status,
                line.detail,
            ]
            for line in plan.inventory
        ],
    )
    if plan.obligations:
        w()
        w("### Essential recurring obligations")
        w()
        w.table(
            ["Obligation", "Category", "Cadence", "Autopay", "Continue"],
            [
                [
                    item.label,
                    item.category.replace("_", " "),
                    item.cadence,
                    _status(item.autopay_status),
                    item.instruction,
                ]
                for item in plan.obligations
            ],
        )

    w()
    w("## Recorded transfer facts — not legal conclusions")
    w()
    if plan.transfers:
        w.table(
            ["Asset or policy", "What is recorded", "Audit status"],
            [
                [item.subject, item.recorded_route, item.review_status]
                for item in plan.transfers
            ],
        )
    else:
        w("**NEEDS COMPLETION:** no asset or policy inventory is recorded.")
    w()
    w(
        "A title or beneficiary field records what the household last observed. "
        "The institution and appropriate professional must confirm the actual "
        "transfer route before anything is moved or elected."
    )

    w()
    w("## Documents and recovery")
    w()
    w.table(["Item", "Display-safe location reference"], plan.locations)
    w()
    open_documents = [
        item for item in plan.document_audit.sorted if item.severity != "ok"
    ]
    open_digital = [item for item in plan.digital_audit.sorted if item.severity != "ok"]
    w(
        f"Shared estate-document audit: **{len(open_documents)} open "
        "finding(s)**. Shared digital-access audit: "
        f"**{len(open_digital)} open finding(s)**."
    )
    if open_documents:
        w()
        w.table(
            ["Estate check", "Status", "Finding"],
            [
                [
                    item.subject.replace("_", " "),
                    _audit_status(item.severity),
                    item.detail,
                ]
                for item in open_documents
            ],
        )
    if open_digital:
        w()
        w.table(
            ["Access check", "Status", "Finding"],
            [
                [
                    item.subject.replace("_", " "),
                    _audit_status(item.severity),
                    item.detail,
                ]
                for item in open_digital
            ],
        )

    w()
    w("## NEEDS COMPLETION")
    w()
    if plan.findings:
        for finding in plan.findings:
            severity = "BLOCKS EXECUTION" if finding.critical else "incomplete"
            w(f"- **{severity}:** {finding.detail}")
    else:
        w("No operational completion items are open.")

    w()
    w("## Review and refresh")
    w()
    if plan.reviewed_on is None:
        w("Last reviewed: **NEEDS COMPLETION**.")
    else:
        w(
            f"Last reviewed: **{plan.reviewed_on.isoformat()}** "
            f"({plan.review_age_days} days before this facts date)."
        )
    w()
    if plan.review_triggers:
        w("Refresh immediately after:")
        for trigger in plan.review_triggers:
            w(f"- {trigger}")
    else:
        w("**NEEDS COMPLETION:** no refresh events are recorded.")

    w()
    w(
        "Before an irreversible action, have the relevant professional confirm "
        "state-law authority, tax treatment, retirement-account elections, and "
        "institution-specific requirements."
    )
    cli.disclaimer(
        w,
        "lib/pf/continuity.py",
        "This runbook records an operational path; it does not establish "
        "authority, eligibility, transfer treatment, or processing time.",
    )


if __name__ == "__main__":
    raise SystemExit(
        cli.run(
            title="Continuity plan",
            required=REQUIRED,
            build=build,
            skill_id="continuity-plan",
        )
    )
