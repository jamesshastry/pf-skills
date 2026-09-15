"""Beneficiary and estate audits.

A different shape from every other module here. There is almost no
arithmetic — these are **completeness and consistency checks**, and the
findings are categorical rather than numeric.

Worth being honest about that in the output. A checklist that dresses itself
up as a model is worse than one that says what it is, because the reader
calibrates on the wrong thing.

The reason this cluster earns its place despite the thin maths: **beneficiary
designations override the will.** An otherwise perfect estate plan is defeated
by one unrevised form, and nobody ever looks.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

#: Age below which a person named directly as a beneficiary triggers a
#: court-supervised guardianship rather than simply receiving the money.
AGE_OF_MAJORITY = 18

#: Estate documents go stale. Not because they expire — they don't — but
#: because the life they describe does: births, deaths, marriages, divorces,
#: moves between states.
DOCUMENT_REVIEW_YEARS = 5

#: The documents a household is expected to have. A type absent from the
#: facts file is reported as *not recorded*, which is distinct from absent.
#: A non-US-citizen spouse cannot receive an unlimited marital deduction, so
#: the document set is different. Added after review finding A1 — the first
#: version of this module assumed citizenship without asking.
QDOT_DOCUMENT = "qdot"

EXPECTED_DOCUMENTS = {
    "will": "Directs everything **not** governed by a beneficiary designation "
            "or joint title. Without one the state's intestacy rules decide, "
            "and they rarely match anyone's intent.",
    "financial_poa": "Lets someone manage money if you are alive but "
                     "incapacitated. A will does nothing here — it only "
                     "operates on death. This is the most commonly missing "
                     "document and the one whose absence bites soonest.",
    "healthcare_poa": "Lets someone make medical decisions for you.",
    "advance_directive": "States your own wishes so the decision is not left "
                         "to someone else to guess under pressure.",
    "revocable_trust": "Avoids probate and controls timing of distribution. "
                       "Optional — but if one exists it must be funded.",
}

DIGITAL_CHECKS = {
    "password_manager": "A password manager, so credentials exist in one "
                        "recoverable place.",
    "emergency_access_configured": "Emergency or legacy access configured in "
                                   "that manager. Having the vault and no way "
                                   "in is the same as not having it.",
    "account_inventory": "A written inventory of accounts and institutions. "
                         "A survivor cannot close or claim what they do not "
                         "know exists.",
    "two_factor_recovery_documented": "Two-factor recovery codes recorded "
                                      "somewhere reachable. 2FA locks out "
                                      "heirs exactly as well as it locks out "
                                      "attackers.",
}


@dataclass
class Finding:
    subject: str
    severity: str  # blocker | gap | note | ok
    detail: str


SEVERITY_ORDER = {"blocker": 0, "gap": 1, "note": 2, "ok": 3}


@dataclass
class Audit:
    findings: list[Finding] = field(default_factory=list)
    checked: int = 0
    unknown: int = 0

    def add(self, subject: str, severity: str, detail: str) -> None:
        self.findings.append(Finding(subject, severity, detail))

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "blocker"]

    @property
    def sorted(self) -> list[Finding]:
        return sorted(self.findings, key=lambda f: SEVERITY_ORDER[f.severity])


# ── beneficiaries ───────────────────────────────────────────────────────────


def _minor_ids(members: list[dict]) -> set[str]:
    return {
        m["id"] for m in members
        if m.get("id") and (m.get("age") is not None) and m["age"] < AGE_OF_MAJORITY
    }


def audit_beneficiaries(
    items: list[tuple[str, dict]],
    *,
    members: list[dict],
    trust_funded: bool | None,
) -> Audit:
    """`items` is a list of (label, record) where record may carry
    `beneficiaries` and `beneficiary_applicable`."""
    a = Audit()
    minors = _minor_ids(members)

    for label, rec in items:
        if rec.get("beneficiary_applicable") is False:
            continue
        a.checked += 1
        bens = rec.get("beneficiaries")

        if bens is None:
            a.unknown += 1
            a.add(label, "gap",
                  "**Not recorded.** Nobody has looked. Most audits fail here "
                  "rather than on a wrong designation — pull the form and "
                  "record what it actually says.")
            continue

        if not bens:
            a.add(label, "blocker",
                  "**No beneficiary named.** The asset falls into the estate "
                  "and goes through probate — slower, public, and governed by "
                  "the will rather than by choice. On a retirement account it "
                  "can also collapse the distribution period for the heirs.")
            continue

        primary = [b for b in bens if b.get("type") == "primary"]
        contingent = [b for b in bens if b.get("type") == "contingent"]

        if not primary:
            a.add(label, "blocker",
                  "Beneficiaries listed but **none is primary**.")
        else:
            share = sum(b.get("share") or 0 for b in primary)
            if abs(share - 100) > 0.01:
                a.add(label, "blocker",
                      f"**Primary shares total {share}%, not 100%.** The "
                      "remainder is unallocated and will be resolved by the "
                      "custodian's default rules, not yours.")

        if contingent:
            cshare = sum(b.get("share") or 0 for b in contingent)
            if abs(cshare - 100) > 0.01:
                a.add(label, "gap",
                      f"Contingent shares total {cshare}%, not 100%.")
        else:
            a.add(label, "gap",
                  "**No contingent beneficiary.** If the primary dies first, "
                  "or with you, the asset lands in the estate — the exact "
                  "outcome the designation exists to avoid. This is the most "
                  "common real defect, because people name a spouse and stop.")

        named_minors = [b for b in bens if b.get("member_id") in minors]
        if named_minors:
            who = ", ".join(b.get("name") or b["member_id"] for b in named_minors)
            a.add(label, "blocker",
                  f"**Minor named directly: {who}.** A minor cannot receive "
                  "the proceeds, so a court appoints a guardian of the estate "
                  "— expensive, slow, supervised, and it hands the money over "
                  "outright at majority. Name a trust for their benefit "
                  "instead, which is usually why the trust exists.")

        for b in bens:
            if b.get("relationship") == "trust":
                if trust_funded is False:
                    a.add(label, "gap",
                          "Names a trust, and the trust is recorded as "
                          "**unfunded**. Naming a trust as beneficiary does "
                          "work even when it holds nothing during life — but "
                          "confirm the trust language actually contemplates "
                          "receiving it.")
                elif trust_funded is None:
                    a.add(label, "note",
                          "Names a trust whose funding status is unknown. "
                          "Confirm it exists, is signed, and its terms match "
                          "the intent here.")
            if b.get("relationship") == "estate":
                a.add(label, "gap",
                      "Names **the estate** as beneficiary. This is almost "
                      "always a mistake — it forces probate and, on a "
                      "retirement account, usually shortens the payout period "
                      "available to heirs.")

        if len(bens) > 1 and any(b.get("relationship") == "child" for b in bens):
            if not any(b.get("per_stirpes") is not None for b in bens):
                a.add(label, "note",
                      "Multiple beneficiaries including children, and "
                      "`per_stirpes` is not set either way. It decides whether "
                      "a predeceased child's share passes to their children or "
                      "is split among the survivors. Choose it deliberately.")

        if not any(f.subject == label for f in a.findings):
            a.add(label, "ok", "Primary and contingent named, shares total 100%.")
    return a


# ── documents ───────────────────────────────────────────────────────────────


def audit_documents(
    documents: list[dict],
    *,
    today: _dt.date | None = None,
    non_citizen_spouse: bool = False,
    domicile_determined: bool | None = None,
) -> Audit:
    today = today or _dt.date.today()
    a = Audit()

    if non_citizen_spouse:
        has_qdot = any(d.get("type") == QDOT_DOCUMENT and d.get("exists")
                       for d in documents or [])
        a.add("qdot", "ok" if has_qdot else "blocker",
              "A QDOT is recorded." if has_qdot else
              "**The surviving spouse is not a US citizen, and no QDOT is "
              "recorded.** The unlimited marital deduction does not apply to "
              "a non-citizen spouse; property has to pass through a "
              "qualifying domestic trust to defer the tax, and that trust has "
              "to exist and be drafted for the purpose before it is needed. "
              "Ask the attorney who drew the existing trust whether it "
              "qualifies — a standard revocable trust generally does not.")

    if domicile_determined is False:
        a.add("domicile", "gap",
              "Estate tax turns on **domicile**, not on income-tax residency, "
              "and domicile here is assumed rather than determined. A US "
              "domiciliary gets the full exemption; a non-domiciliary gets "
              "$60,000 against US-situs assets. Worth a deliberate "
              "determination — see `citizenship-status-review`.")
    by_type = {d.get("type"): d for d in documents or []}

    for dtype, why in EXPECTED_DOCUMENTS.items():
        doc = by_type.get(dtype)
        optional = dtype == "revocable_trust"

        if doc is None:
            a.unknown += 1
            a.add(dtype, "gap",
                  f"**Not recorded.** {why} Record whether one exists — "
                  "unknown is not the same as absent, and only one of them is "
                  "fixable by drafting.")
            continue

        a.checked += 1
        exists = doc.get("exists")
        if exists is False:
            a.add(dtype, "note" if optional else "blocker",
                  f"**Does not exist.** {why}")
            continue
        if exists is None:
            a.add(dtype, "gap", f"Existence not stated. {why}")
            continue

        reviewed = doc.get("last_reviewed")
        if isinstance(reviewed, _dt.datetime):
            reviewed = reviewed.date()
        elif isinstance(reviewed, str):
            try:
                reviewed = _dt.date.fromisoformat(reviewed)
            except ValueError:
                reviewed = None

        if reviewed is None:
            a.add(dtype, "gap",
                  "Exists, but **no review date recorded**. A document that "
                  "predates a birth, a death, a marriage, a divorce, or a move "
                  "between states may no longer say what you think.")
        else:
            years = (today - reviewed).days / 365.25
            if years > DOCUMENT_REVIEW_YEARS:
                a.add(dtype, "gap",
                      f"Last reviewed {reviewed.isoformat()} — **{years:.0f} "
                      f"years ago**, past the {DOCUMENT_REVIEW_YEARS}-year "
                      "mark. Re-read it against the household as it is now.")
            else:
                a.add(dtype, "ok",
                      f"Exists, reviewed {reviewed.isoformat()} "
                      f"({years:.1f} years ago).")

        if dtype == "revocable_trust":
            funded = doc.get("funded")
            if funded is False:
                a.add("revocable_trust_funding", "blocker",
                      "**The trust is not funded.** A trust that owns nothing "
                      "does nothing. Creating it is the part people pay for; "
                      "retitling assets into it is the part they skip, and "
                      "skipping it means the probate the trust was bought to "
                      "avoid happens anyway.")
            elif funded is None:
                a.add("revocable_trust_funding", "gap",
                      "Trust exists; **funding status unknown**. Check which "
                      "assets are actually titled in its name. This is the "
                      "single most common estate-planning failure.")
            else:
                a.add("revocable_trust_funding", "ok", "Trust is funded.")
    return a


# ── digital ─────────────────────────────────────────────────────────────────


def audit_digital(digital: dict | None) -> Audit:
    a = Audit()
    digital = digital or {}
    for key, why in DIGITAL_CHECKS.items():
        val = digital.get(key)
        if val is None:
            a.unknown += 1
            a.add(key, "gap", f"Not recorded. {why}")
        elif val:
            a.checked += 1
            a.add(key, "ok", why)
        else:
            a.checked += 1
            a.add(key, "gap", f"**Missing.** {why}")

    if digital.get("password_manager") and not digital.get("emergency_access_configured"):
        a.add("combination", "blocker",
              "**A password manager with no emergency access is a single "
              "point of failure, not a plan.** Every credential is in one "
              "place and nobody else can reach it. This is worse than no "
              "manager, because it creates the belief that the problem is "
              "solved.")
    return a
