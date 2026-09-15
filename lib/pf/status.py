"""Citizenship, immigration status, and domicile — and what they change.

## Why this module exists

Review finding A1: not one of the first twenty-five skills mentioned citizenship, visa status or
domicile. Every conclusion carried a silent assumption that the household was a US citizen or
permanent resident. The schema refused to run without knowing which US *state* someone lived in
and never asked whether they were a US *citizen*.

## The distinction the rest of the repository was missing

Three different statuses govern three different taxes, and they do not move together:

| Question | Governed by |
|---|---|
| Is worldwide income taxed by the US? | **Residence** — citizen, LPR, or substantial presence |
| Is the estate taxed by the US, and on what? | **Domicile** — residence *plus* intent to remain |
| Does a transfer to a spouse get the marital deduction? | **The spouse's citizenship** |

A household can be fully US tax resident on income, fully US domiciled for estate purposes, and
still lose the unlimited marital deduction because the surviving spouse holds a foreign passport.
That combination is common and is the finding this module exists to surface.

## What is encoded and what is refused

Encoded: the rules above, which are stable and statutory. **Refused:** anything country-specific
that is not in the cited table — payment of benefits abroad, treaty relief, local recognition of
US accounts. Those are `UNKNOWN` and the skills say so.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CITIZEN = "citizen"
PERMANENT_RESIDENT = "permanent_resident"
NONIMMIGRANT = "nonimmigrant_visa"
NONRESIDENT = "nonresident"

US_STATUSES = (CITIZEN, PERMANENT_RESIDENT, NONIMMIGRANT, NONRESIDENT)

#: Statuses that make someone a US person for income tax on worldwide income.
#: A nonimmigrant visa holder meeting the substantial presence test is also a
#: US tax resident — the visa category does not exempt them.
WORLDWIDE_INCOME_STATUSES = (CITIZEN, PERMANENT_RESIDENT, NONIMMIGRANT)

#: Estate-tax exemption available to a non-domiciliary, against US-situs
#: assets only. Orders of magnitude below the domiciliary exemption, which is
#: why the domicile determination is worth making deliberately.
NON_DOMICILIARY_ESTATE_EXEMPTION = 60_000

#: §877A expatriation tax reaches citizens who relinquish and long-term
#: residents who cease to be permanent residents, where long-term means LPR in
#: this many of the last fifteen taxable years.
LONG_TERM_RESIDENT_YEARS = 8
LONG_TERM_RESIDENT_WINDOW = 15


@dataclass(frozen=True)
class Totalization:
    """Whether a US social-security totalization agreement exists.

    Cited table, same discipline as `jurisdiction.py`. An agreement prevents
    double social-security contributions and lets coverage periods be
    combined; its absence is a real cost that nothing else compensates for.
    """

    country: str
    known: bool
    agreement: bool | None = None
    note: str = ""
    source: str = ""
    verified_on: str = ""


_TOTALIZATION: dict[str, Totalization] = {
    "IN": Totalization(
        "IN", True, agreement=False,
        note="There is no US–India totalization agreement. An Indian national "
             "working in the US pays US Social Security and Medicare with no "
             "coordination and no certificate of coverage, and Indian "
             "provident-fund periods cannot be combined with US credits. This "
             "is a straightforward cost with no offset, and it is frequently "
             "assumed away by analyses written for European destinations.",
        source="SSA list of totalization agreements — India absent",
        verified_on="unverified — check ssa.gov/international",
    ),
    "GB": Totalization(
        "GB", True, agreement=True,
        note="A US–UK totalization agreement exists; coverage periods can be "
             "combined and dual contributions avoided via a certificate of "
             "coverage.",
        source="SSA list of totalization agreements",
        verified_on="unverified — check ssa.gov/international",
    ),
}

TOTALIZATION_SOURCE = "SSA totalization agreement list"
TOTALIZATION_VERIFIED = "unverified — check ssa.gov/international"


def totalization(country: str | None) -> Totalization:
    if not country:
        return Totalization("??", False)
    return _TOTALIZATION.get(country.strip().upper(),
                             Totalization(country.upper(), False))


def countries_available() -> list[str]:
    return sorted(_TOTALIZATION)


# ── the audit ───────────────────────────────────────────────────────────────


@dataclass
class Finding:
    area: str
    severity: str  # blocker | gap | note | ok
    detail: str
    affects: tuple[str, ...] = ()


@dataclass
class StatusAudit:
    us_person: bool | None
    domicile_country: str | None
    domicile_determined: bool
    findings: list[Finding] = field(default_factory=list)

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "blocker"]

    @property
    def affected_skills(self) -> list[str]:
        out: set[str] = set()
        for f in self.findings:
            out |= set(f.affects)
        return sorted(out)


def _status(member: dict) -> str | None:
    return member.get("us_status")


def audit(
    members: list[dict],
    *,
    domicile: dict | None,
    estate_exemption: float | None = None,
) -> StatusAudit:
    domicile = domicile or {}
    adults = [m for m in members if m.get("role") in ("primary", "spouse")]
    statuses = {m.get("id"): _status(m) for m in adults}

    unknown = [i for i, s in statuses.items() if s is None]
    us_person = (None if unknown else
                 any(s in WORLDWIDE_INCOME_STATUSES for s in statuses.values()))

    a = StatusAudit(
        us_person=us_person,
        domicile_country=domicile.get("country"),
        domicile_determined=bool(domicile.get("determined")),
    )

    if unknown:
        a.findings.append(Finding(
            "status", "blocker",
            f"**US status not recorded for {', '.join(unknown)}.** Everything "
            "below, and several already-shipped skills, assume a status that "
            "nobody has stated. Record `us_status` for every adult.",
            ("all",)))
        return a

    # ── income tax ──────────────────────────────────────────────────────
    if us_person:
        nonimm = [i for i, s in statuses.items() if s == NONIMMIGRANT]
        if nonimm:
            a.findings.append(Finding(
                "income tax", "note",
                f"{', '.join(nonimm)} hold a nonimmigrant visa but, on the "
                "substantial presence test, are **US tax residents on "
                "worldwide income** exactly as a citizen would be. The visa "
                "category changes immigration rights, not income-tax reach — "
                "including the obligation to report foreign accounts.",
                ("foreign-reporting-audit",)))

    # ── the marital deduction ───────────────────────────────────────────
    non_citizen_spouses = [
        m.get("id") for m in adults
        if m.get("role") == "spouse" and _status(m) != CITIZEN
    ]
    if non_citizen_spouses:
        a.findings.append(Finding(
            "estate", "blocker",
            f"**The unlimited marital deduction does not apply to a "
            f"non-US-citizen spouse** ({', '.join(non_citizen_spouses)}). "
            "Property passing to them at death does not qualify unless it "
            "passes through a **qualifying domestic trust (QDOT)**, which has "
            "to exist and be drafted for the purpose before it is needed. "
            "The deduction can also be preserved if the spouse naturalises "
            "before the estate-tax return is filed — which is a reason to "
            "know where the naturalisation timeline sits.",
            ("estate-document-review", "beneficiary-audit", "survivor-needs",
             "life-insurance-review")))
        a.findings.append(Finding(
            "estate", "note",
            "Lifetime gifts to a non-citizen spouse are also capped at an "
            "annual exclusion rather than being unlimited. Relevant to any "
            "plan that equalises assets between spouses.",
            ("estate-document-review",)))

    # ── domicile ────────────────────────────────────────────────────────
    if not a.domicile_country:
        a.findings.append(Finding(
            "estate", "blocker",
            "**Domicile is not recorded.** Estate and gift tax turn on "
            "domicile — residence plus intent to remain indefinitely — which "
            "is a different test from income-tax residency and is decided on "
            "facts and circumstances. A US domiciliary gets the full "
            "exemption; a non-domiciliary gets "
            f"**{_money(NON_DOMICILIARY_ESTATE_EXEMPTION)}** against US-situs "
            "assets, taxed up to 40% above it. That is a difference of two "
            "orders of magnitude on the same balance sheet.",
            ("estate-document-review",)))
    elif a.domicile_country == "US" and not a.domicile_determined:
        a.findings.append(Finding(
            "estate", "gap",
            "US domicile is **assumed rather than determined**. Long "
            "residence, family, a home and a pending immigration petition all "
            "point to intent to remain, and that is usually enough — but it "
            "is a determination someone should make deliberately, because the "
            "downside case is an exemption of "
            f"{_money(NON_DOMICILIARY_ESTATE_EXEMPTION)} rather than millions.",
            ("estate-document-review",)))
    elif a.domicile_country != "US":
        a.findings.append(Finding(
            "estate", "blocker",
            f"Domicile recorded as **{a.domicile_country}**, not the US. US "
            f"estate tax then reaches only US-situs assets — US real property "
            f"and stock in US corporations — against an exemption of "
            f"{_money(NON_DOMICILIARY_ESTATE_EXEMPTION)}. US bank deposits "
            "and life-insurance proceeds on a non-resident's life are "
            "generally **not** US-situs, which cuts both ways and needs "
            "counsel rather than a skill.",
            ("estate-document-review", "life-insurance-review")))

    # ── expatriation ────────────────────────────────────────────────────
    exposed = [i for i, s in statuses.items()
               if s in (CITIZEN, PERMANENT_RESIDENT)]
    if exposed:
        a.findings.append(Finding(
            "expatriation", "note",
            "The §877A expatriation tax can reach a citizen who relinquishes "
            f"and a permanent resident who held that status in "
            f"{LONG_TERM_RESIDENT_YEARS} of the last "
            f"{LONG_TERM_RESIDENT_WINDOW} years and then ceases to be one. "
            "Anyone planning to leave permanently should understand it "
            "**before** taking the status, not after.",
            ("cross-border planning",)))
    else:
        a.findings.append(Finding(
            "expatriation", "ok",
            "No §877A expatriation exposure: it reaches citizens and "
            "long-term permanent residents, and nobody here holds either "
            "status. **This is an argument worth costing before accepting a "
            "green card**, because taking one starts the eight-year clock.",
            ("cross-border planning",)))

    return a


def social_security_notes(*, statuses: dict, home_country: str | None) -> list[str]:
    """Status-dependent caveats on the Social Security analysis."""
    out: list[str] = []
    t = totalization(home_country)

    if t.known and t.agreement is False:
        out.append(f"**{t.country}:** {t.note}")
    elif t.known:
        out.append(f"**{t.country}:** {t.note}")
    elif home_country:
        out.append(
            f"Whether a US–{home_country} totalization agreement exists is "
            "not in the table. It determines whether contributions are "
            "duplicated and whether coverage periods combine — check "
            "ssa.gov/international rather than assuming."
        )

    non_citizens = [i for i, s in statuses.items() if s and s != CITIZEN]
    if non_citizens:
        out.append(
            "**Payment of benefits outside the US is restricted for "
            "non-citizens.** Entitlement and payability are different "
            "questions: credits can be fully earned and payment still stop "
            "after an extended absence, depending on citizenship and country "
            "of residence. The exceptions are specific and this table does "
            "not encode them — confirm with SSA before a plan depends on "
            "benefits arriving abroad."
        )
    return out


def _money(x) -> str:
    return f"${x:,.0f}"
