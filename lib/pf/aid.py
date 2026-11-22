"""Federal Student Aid Index (SAI) for a dependent student, and what it decides.

The one idea: **need-based aid is cost of attendance minus SAI.** When the
parents' *income alone* produces an SAI above the cost of attendance, no asset
decision — buying a home, spending down cash, moving a child's money — can
create need. Asset repositioning "for aid" is then a cost with no benefit.
The module computes the SAI (FAFSA Simplification formula, 20 U.S.C. §1087oo)
and says which side of that line a household is on.

Basis: nominal dollars of the income ("base") year — two years before the
award year starts (prior-prior year).

Refuses: the CSS Profile and other institutional methodologies (they count
home equity and use their own tables); state aid programs; independent
students; Pell Grant scheduling. Business and farm rows are counted at their
recorded value and flagged — the net-worth treatment the form applies to them
is not modelled. Unknown values, unlinked education accounts that could
duplicate a balance-sheet row, and an income year that is not the
prior-prior year stop the calculation (``AidError``) rather than being
guessed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ── Statutory constants (20 U.S.C. §1087oo) ──────────────────────────────

#: §1087oo(d)(1): parents' net assets above the protection allowance are
#: converted to income at 12% before the assessment schedule applies.
ASSET_CONVERSION_RATE = 0.12
#: §1087oo(g)(1): student available income is assessed at 50%, floored at
#: zero from award year 2025-26 onward.
STUDENT_INCOME_RATE = 0.50
#: §1087oo(h): student assets are assessed at 20%.
STUDENT_ASSET_RATE = 0.20
#: §1087oo(a)(2): the SAI cannot be lower than -$1,500.
MIN_SAI = -1500.0
#: §1087oo(c)(2) applies "the rate of tax under section 3101(b)" of the
#: Internal Revenue Code: 1.45% on all earnings (§3101(b)(1)) plus the
#: additional 0.9% above $250,000 on a joint return, $200,000 otherwise
#: (§3101(b)(2)).
MEDICARE_RATE = 0.0145
ADDITIONAL_MEDICARE_RATE = 0.009
ADDITIONAL_MEDICARE_THRESHOLD = {True: 250_000.0, False: 200_000.0}
#: 26 U.S.C. §3101(a) OASDI rate.
OASDI_RATE = 0.062

#: Education accounts the FAFSA reports as a **parent** asset even when the
#: dependent student owns them (20 U.S.C. §1087vv(f)). Custodial (UTMA/UGMA)
#: and ordinary accounts in the student's name stay student assets.
EDUCATION_VEHICLES = frozenset({
    "529", "529_plan", "529_savings", "prepaid_tuition",
    "coverdell", "coverdell_esa",
})
#: Personal vehicles are not reported on the FAFSA.
PERSONAL_VEHICLES = frozenset({"car", "auto", "automobile", "personal_vehicle"})
#: Rows treated as business or farm equity.
BUSINESS_VEHICLES = frozenset({"business", "business_equity", "farm", "llc_interest"})


class AidError(ValueError):
    """The inputs cannot support an SAI without guessing."""

#: Balance-sheet vehicles that are life-insurance cash values or pensions,
#: which the FAFSA excludes from assets.
INSURANCE_OR_PENSION_VEHICLES = frozenset({
    "ulip_fund", "endowment_fund", "money_back_value", "pension_value",
    "whole_life_surrender", "whole_life", "universal_life",
    "variable_universal_life", "cash_value_life", "annuity", "pension",
})

#: Transcribed from the cited sources; marked unverified until a human checks
#: them against the source, per the repository's provenance policy.
AID_VERIFIED = "unverified"


@dataclass(frozen=True)
class AidYear:
    """Annually updated need-analysis tables for one award year."""
    award_year: str
    source: str
    verified_on: str
    parent_ipa: dict[int, float]
    parent_ipa_additional: float
    student_ipa: float
    eea_cap: float
    eea_rate: float
    #: (older-parent age upper bound, two parents, one parent); None = and up.
    apa: tuple[tuple[int | None, float, float], ...]
    #: AAI below this floor contributes ``negative_floor_contribution``.
    negative_aai_floor: float
    negative_floor_contribution: float
    #: (upper bound or None, base, rate, lower bound of the band).
    schedule: tuple[tuple[float | None, float, float, float], ...]


AID_TABLES: dict[str, AidYear] = {
    "2026-27": AidYear(
        award_year="2026-27",
        source="Federal Register, Federal Need Analysis Methodology for the "
               "2026-27 Award Year (FR Doc. 2025-10243, published 2025-06-05)",
        verified_on=AID_VERIFIED,
        parent_ipa={2: 29190, 3: 36330, 4: 44880, 5: 52950, 6: 61930},
        parent_ipa_additional=6990,
        student_ipa=11770,
        eea_cap=5000,
        eea_rate=0.35,
        apa=((None, 0.0, 0.0),),      # zero at every age for 2026-27
        negative_aai_floor=-8500,
        negative_floor_contribution=-1870,
        schedule=(
            (21800, 0, 0.22, -8500),
            (27300, 4796, 0.25, 21800),
            (32800, 6171, 0.29, 27300),
            (38400, 7766, 0.34, 32800),
            (43900, 9670, 0.40, 38400),
            (None, 11870, 0.47, 43900),
        ),
    ),
}

#: Social Security contribution and benefit base by earnings year (ssa.gov).
SS_WAGE_BASE: dict[int, float] = {2024: 168600, 2025: 176100, 2026: 184500}
SS_WAGE_BASE_SOURCE = "ssa.gov — Contribution and Benefit Base"
SS_WAGE_BASE_VERIFIED = AID_VERIFIED


def table_for(award_year: str) -> tuple[AidYear, bool]:
    """Return the table for the award year, or the nearest shipped one and
    True when the requested year is not in this module (a projection for a
    later year, a back-cast for an earlier one)."""
    if award_year in AID_TABLES:
        return AID_TABLES[award_year], False
    years = sorted(AID_TABLES)
    nearest = years[0] if award_year < years[0] else years[-1]
    return AID_TABLES[nearest], True


def award_start(award_year: str) -> int:
    """First calendar year of an award year such as ``"2031-32"``."""
    try:
        return int(str(award_year).split("-")[0])
    except ValueError as e:
        raise AidError(f"award year {award_year!r} is not of the form 2031-32") from e


def wage_base_for(year: int) -> tuple[float, bool]:
    if year in SS_WAGE_BASE:
        return SS_WAGE_BASE[year], False
    nearest = min(SS_WAGE_BASE) if year < min(SS_WAGE_BASE) else max(SS_WAGE_BASE)
    return SS_WAGE_BASE[nearest], True


def parent_ipa(table: AidYear, family_size: int) -> float:
    if family_size < 2:
        raise ValueError("family size for a dependent student is at least 2")
    top = max(table.parent_ipa)
    if family_size <= top:
        return table.parent_ipa[family_size]
    return table.parent_ipa[top] + (family_size - top) * table.parent_ipa_additional


def asset_protection(table: AidYear, older_parent_age: int, two_parents: bool) -> float:
    for upper, two, one in table.apa:
        if upper is None or older_parent_age <= upper:
            return two if two_parents else one
    return 0.0


def assess(aai: float, table: AidYear) -> float:
    """Parents' contribution from adjusted available income."""
    if aai < table.negative_aai_floor:
        return table.negative_floor_contribution
    for upper, base, rate, lower in table.schedule:
        if upper is None or aai <= upper:
            start = 0.0 if lower < 0 else lower
            if lower < 0:                       # first band: rate x AAI
                return aai * rate
            return base + (aai - start) * rate
    raise AssertionError("schedule needs an open-ended final band")


def payroll_allowance(earned: float, wage_base: float, joint: bool) -> float:
    """§1087oo(c)(2): OASDI on earnings up to the contribution and benefit
    base — "or twice such contribution and benefit base, in the case of a
    joint return" — plus Medicare. The statute doubles the base for the
    parents together, not per earner, so for a one-earner couple above the
    base the allowance exceeds the Social Security tax actually withheld.
    That is the formula, not an error here."""
    cap = wage_base * (2 if joint else 1)
    medicare = (earned * MEDICARE_RATE
                + max(0.0, earned - ADDITIONAL_MEDICARE_THRESHOLD[joint])
                * ADDITIONAL_MEDICARE_RATE)
    return medicare + min(earned, cap) * OASDI_RATE


@dataclass(frozen=True)
class ParentInputs:
    #: FAFSA total income: AGI plus untaxed income the form asks for.
    total_income: float
    federal_income_tax: float
    earned_income: float
    family_size: int
    older_parent_age: int
    two_parents: bool
    assets: float
    income_year: int


@dataclass
class SAIResult:
    award_year: str
    projected_table: bool
    projected_wage_base: bool
    allowances: dict[str, float]
    available_income: float
    reportable_assets: float
    asset_contribution_income: float
    adjusted_available_income: float
    parent_contribution: float
    parent_contribution_income_only: float
    findings: list[str] = field(default_factory=list)


def parent_contribution(p: ParentInputs, award_year: str) -> SAIResult:
    if p.federal_income_tax < 0 or p.earned_income < 0 or p.assets < 0:
        raise AidError("federal income tax, earned income and assets cannot be negative")
    expected = award_start(award_year) - 2
    if p.income_year != expected:
        raise AidError(f"award year {award_year} uses {expected} income "
                       f"(prior-prior year), not {p.income_year}")
    table, projected = table_for(award_year)
    base, base_projected = wage_base_for(p.income_year)
    allowances = {
        "federal income tax": p.federal_income_tax,
        "payroll tax allowance": payroll_allowance(p.earned_income, base,
                                                   p.two_parents),
        "income protection allowance": parent_ipa(table, p.family_size),
        "employment expense allowance": min(table.eea_cap,
                                            table.eea_rate * p.earned_income),
    }
    available = p.total_income - sum(allowances.values())
    net_assets = max(0.0, p.assets - asset_protection(
        table, p.older_parent_age, p.two_parents))
    from_assets = net_assets * ASSET_CONVERSION_RATE
    aai = available + from_assets
    return SAIResult(
        award_year=award_year,
        projected_table=projected,
        projected_wage_base=base_projected,
        allowances=allowances,
        available_income=available,
        reportable_assets=p.assets,
        asset_contribution_income=from_assets,
        adjusted_available_income=aai,
        parent_contribution=assess(aai, table),
        parent_contribution_income_only=assess(available, table),
    )


def student_contribution(*, income: float, federal_income_tax: float,
                         earned_income: float, assets: float, income_year: int,
                         award_year: str, parents_aai: float = 0.0) -> float:
    """§1087oo(g)-(h). ``parents_aai`` feeds the allowance for parents'
    negative available income (§1087oo(g)(4)): when the parents' adjusted
    available income is negative, that shortfall shelters student income."""
    table, _ = table_for(award_year)
    base, _ = wage_base_for(income_year)
    adjustment = (federal_income_tax
                  + payroll_allowance(earned_income, base, joint=False)
                  + table.student_ipa
                  + max(0.0, -parents_aai))
    from_income = max(0.0, (income - adjustment) * STUDENT_INCOME_RATE)
    return from_income + max(0.0, assets * STUDENT_ASSET_RATE)


def sai(parent: SAIResult, student: float) -> float:
    return max(MIN_SAI, parent.parent_contribution + student)


@dataclass(frozen=True)
class AssetLine:
    name: str
    value: float
    counted: bool
    reason: str


def classify_assets(balance_sheet: list[dict], *,
                    include_foreign: bool) -> list[AssetLine]:
    """FAFSA treatment of each balance-sheet row. Retirement (tier
    ``age_restricted``), insurance cash values and pensions, a primary
    residence, personal vehicles and pending items are excluded. Negative
    rows are liabilities the form does not net against assets; margin debt
    is netted from its own account. A row with no value is listed and not
    counted — the total is then a lower bound, and the findings say so.
    Foreign rows are excluded only when the caller says so; the FAFSA itself
    asks for investments wherever they are held."""
    out: list[AssetLine] = []
    for row in balance_sheet or []:
        name = str(row.get("name"))
        raw = row.get("value")
        if raw is None:
            out.append(AssetLine(name, 0.0, False, "value not recorded — not counted"))
            continue
        value = float(raw)
        vehicle = row.get("vehicle")
        if row.get("pending"):
            out.append(AssetLine(name, value, False, "pending — not counted"))
        elif row.get("tier") == "age_restricted":
            out.append(AssetLine(name, value, False, "retirement account"))
        elif row.get("vehicle") in INSURANCE_OR_PENSION_VEHICLES:
            out.append(AssetLine(name, value, False, "insurance cash value or pension"))
        elif row.get("primary_residence"):
            out.append(AssetLine(name, value, False, "primary residence"))
        elif vehicle in PERSONAL_VEHICLES or row.get("asset_class") == "vehicle":
            out.append(AssetLine(name, value, False, "personal vehicle"))
        elif value < 0:
            out.append(AssetLine(name, value, False,
                                 "liability — the FAFSA does not net it against assets"))
        elif row.get("country") not in (None, "US") and not include_foreign:
            out.append(AssetLine(name, value, False, "foreign — excluded by household choice"))
        elif vehicle in BUSINESS_VEHICLES or row.get("asset_class") == "business":
            out.append(AssetLine(name, value, True,
                                 "business or farm — counted at recorded value"))
        elif row.get("margin_debt"):
            net = max(0.0, value - float(row["margin_debt"]))
            out.append(AssetLine(name, net, True,
                                 f"counted net of ${float(row['margin_debt']):,.0f} margin debt"))
        else:
            out.append(AssetLine(name, value, True, "counted"))
    return out


def need(cost_of_attendance: float, sai_value: float) -> float:
    return max(0.0, cost_of_attendance - max(0.0, sai_value))


def assessment_findings(parent: SAIResult, costs: dict[str, float]) -> list[str]:
    """The decision: is any need-based aid plausible, and can assets move it?"""
    out: list[str] = []
    if not costs:
        return ["No cost of attendance recorded, so need cannot be determined."]
    top = max(costs.values())
    rate = ASSET_CONVERSION_RATE * AID_TABLES[sorted(AID_TABLES)[-1]].schedule[-1][2]
    if parent.parent_contribution_income_only >= top:
        claim = (f"Income alone produces a parent contribution of "
                 f"${parent.parent_contribution_income_only:,.0f}, above the "
                 f"highest cost of attendance listed (${top:,.0f}).")
        if parent.projected_table:
            # Unindexed allowances overstate the SAI, so a projected verdict
            # is shown with its margin rather than as a bold conclusion.
            out.append(
                f"{claim} On these tables no asset decision creates need-based "
                f"aid, but the margin is ${parent.parent_contribution_income_only - top:,.0f} "
                "and the allowances have not been indexed to the award year — "
                "recheck when its tables are published before acting on it.")
        else:
            out.append(
                f"**{claim}** No asset decision can create need-based aid. Do "
                "not time a home purchase, spend down savings or move a "
                "child's money for aid purposes.")
    elif parent.parent_contribution >= top:
        out.append(
            "Income alone leaves room for need, but reportable assets push the "
            f"SAI above cost. Each $10,000 of reportable parent assets moves the "
            f"SAI by up to ${10000 * rate:,.0f}; a primary residence and "
            "retirement accounts are not counted.")
    else:
        out.append(
            "Need-based aid is plausible at the listed costs. Asset placement "
            f"matters at the margin: up to ${10000 * rate:,.0f} of SAI per $10,000 "
            "of reportable parent assets (529s included, whoever owns them), and "
            "$2,000 per $10,000 in the student's own non-529 accounts.")
    if parent.projected_table:
        shipped = sorted(AID_TABLES)
        if parent.award_year < shipped[0]:
            out.append(
                f"The {parent.award_year} tables are not in this module; the "
                f"earliest shipped year ({shipped[0]}) was used. Treat dollar "
                "figures as approximate.")
        else:
            out.append(
                f"The {parent.award_year} tables are not yet published; the latest "
                "published year was used. Treat dollar figures as a projection.")
    if parent.projected_wage_base:
        if award_start(parent.award_year) - 2 < min(SS_WAGE_BASE):
            out.append("The Social Security wage base for the income year is not "
                       "in this module; the earliest known base was used.")
        else:
            out.append("The Social Security wage base for the income year is not "
                       "yet published; the latest known base was used.")
    return out


# ── Facts → result, shared by the skill runner and the household review ──

@dataclass
class StudentRow:
    member_id: str
    name: str
    eligible: bool | None
    student_assets: float
    sai: float | None
    need: dict[str, float]
    income_recorded: bool = True


@dataclass
class HouseholdAid:
    award_year: str
    income_year: int
    include_foreign: bool
    assets: list[AssetLine]
    parent: SAIResult
    costs: dict[str, float]
    students: list[StudentRow]
    findings: list[str]


def _education_lines(accounts: list[dict], balance_sheet: list[dict],
                     parents: set, dependents: set
                     ) -> tuple[list[AssetLine], dict[str, float]]:
    """Education accounts not already on the balance sheet, as parent asset
    lines, plus student-held totals by member id.

    An account is already on the sheet when its ``balance_sheet_row`` names a
    row (by id or name) or a row has the account's exact name. Several
    accounts may point at one aggregate row. An unlinked account while an
    ``earmark: education`` row is unclaimed is ambiguous — the row may or may
    not be that account — and stops the calculation."""
    rows = balance_sheet or []
    keys = {r.get("id") for r in rows if r.get("id")} | {r.get("name") for r in rows}
    claimed: set = set()
    loose: list[dict] = []
    for acct in accounts or []:
        link = acct.get("balance_sheet_row")
        if link is not None:
            if link not in keys:
                raise AidError(f"education account {acct.get('name')!r} links to "
                               f"balance-sheet row {link!r}, which does not exist")
            claimed.add(link)
        elif acct.get("name") in keys:
            claimed.add(acct.get("name"))
        else:
            loose.append(acct)
    unclaimed = [r.get("name") for r in rows if r.get("earmark") == "education"
                 and r.get("id") not in claimed and r.get("name") not in claimed]
    if loose and unclaimed:
        raise AidError(
            "cannot tell whether education accounts "
            f"{[a.get('name') for a in loose]} are the balance-sheet row(s) "
            f"{unclaimed}; set balance_sheet_row on each account that the row "
            "already includes")

    lines: list[AssetLine] = []
    held: dict[str, float] = {}
    for acct in loose:
        name = str(acct.get("name"))
        if acct.get("value") is None:
            lines.append(AssetLine(name, 0.0, False, "value not recorded — not counted"))
            continue
        value = float(acct["value"])
        owner, vehicle = acct.get("owner"), acct.get("vehicle")
        if owner in parents:
            lines.append(AssetLine(name, value, True, "parent-owned education account"))
        elif owner in dependents:
            if vehicle in EDUCATION_VEHICLES:
                lines.append(AssetLine(name, value, True,
                                       "529 owned by the student — reported as a parent asset"))
            elif vehicle is None:
                raise AidError(f"student-owned account {name!r} has no vehicle; a 529 "
                               "is a parent asset, a custodial account a student asset")
            else:
                held[owner] = held.get(owner, 0.0) + value
        elif owner is None:
            raise AidError(f"education account {name!r} has no owner")
        else:
            lines.append(AssetLine(name, value, False,
                                   "owned outside the household — not reported"))
    return lines, held


def household(fa: dict, *, balance_sheet: list[dict], members: list[dict],
              accounts: list[dict]) -> HouseholdAid:
    """Assemble inputs from an ``education.financial_aid`` block and the
    household's balance sheet, members and education accounts."""
    include_foreign = fa.get("include_foreign_assets", True)
    lines = classify_assets(balance_sheet, include_foreign=include_foreign)
    parents = {x.get("id") for x in members if x.get("role") in ("primary", "spouse")}
    dependents = {x.get("id") for x in members if x.get("role") == "dependent"}
    extra, held = _education_lines(accounts, balance_sheet, parents, dependents)
    lines += extra

    award_year, income_year = str(fa["award_year"]), int(fa["income_year"])
    p = parent_contribution(ParentInputs(
        total_income=float(fa["parent_total_income"]),
        federal_income_tax=float(fa["parent_federal_income_tax"]),
        earned_income=float(fa["parent_earned_income"]),
        family_size=int(fa["family_size"]),
        older_parent_age=int(fa["older_parent_age"]),
        two_parents=bool(fa["two_parents"]),
        assets=sum(x.value for x in lines if x.counted),
        income_year=income_year,
    ), award_year)
    raw_costs = fa.get("cost_of_attendance") or {}
    costs = {str(k): float(v) for k, v in raw_costs.items() if v is not None}
    missing_costs = [str(k) for k, v in raw_costs.items() if v is None]

    students: list[StudentRow] = []
    student_cfg = fa.get("students") or {}
    for mem in members:
        if mem.get("role") != "dependent":
            continue
        mid = str(mem.get("id"))
        name = str(mem.get("name", mid))
        eligible = mem.get("fafsa_eligible")
        if eligible is False:
            students.append(StudentRow(mid, name, False, held.get(mid, 0.0), None, {}))
            continue
        s = student_cfg.get(mid)
        recorded = s is not None and all(
            s.get(k) is not None for k in ("income", "federal_income_tax", "earned_income"))
        s = s or {}
        sc = student_contribution(
            income=float(s.get("income") or 0),
            federal_income_tax=float(s.get("federal_income_tax") or 0),
            earned_income=float(s.get("earned_income") or 0),
            assets=held.get(mid, 0.0), income_year=income_year, award_year=award_year,
            parents_aai=p.adjusted_available_income)
        value = sai(p, sc)
        students.append(StudentRow(mid, name, eligible, held.get(mid, 0.0), value,
                                   {k: need(c, value) for k, c in costs.items()},
                                   recorded))

    findings = assessment_findings(p, costs)
    if missing_costs:
        findings.append(f"Cost of attendance not recorded for {', '.join(missing_costs)}; "
                        "those schools are left out of the decision.")
    unknown = [x.name for x in lines if x.reason.startswith("value not recorded")]
    if unknown:
        findings.append(f"No value recorded for {', '.join(unknown)}; reportable assets "
                        "and the parent contribution are lower bounds.")
    if any(x.reason.startswith("business or farm") for x in lines):
        findings.append("Business or farm equity is counted at its recorded value; the "
                        "form's own net-worth questions are not modelled.")
    if any(not s.income_recorded for s in students if s.sai is not None):
        findings.append("Student income is not recorded for every eligible student; it "
                        "is left out, so those SAIs are lower bounds.")
    return HouseholdAid(award_year, income_year, include_foreign, lines, p, costs,
                        students, findings)
