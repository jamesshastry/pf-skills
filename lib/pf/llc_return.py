"""U.S. LLC tax workpaper for one tax year, by federal classification.

The one idea: **an LLC has no tax identity of its own — its classification
decides which return exists, which lines the ledger lands on, and what flows to
each owner.** The same bookkeeping ledger becomes a Schedule C on the owner's
1040 (disregarded), a Form 1065 with a K-1 per member (partnership), or a Form
1120-S with officer wages and a K-1 per shareholder (S corporation). The
mistakes are classification mistakes: self-employment tax charged on S-corp
K-1 income, guaranteed payments left out of a partner's SE earnings, an S
corporation paying its owner nothing but distributions, a California LLC fee
estimate never sent, a $2,000 contractor with no W-9.

This module maps the ledger to the right return lines, applies the limits that
live at the entity (50% meals, the home-office income limit, §195/§248/§709
start-up and organizational costs), builds each owner's hand-off in exactly
the shape the ``federal-tax-return`` skill reads (``tax_return.schedule_c[]``
or ``tax_return.k1[]``), checks 1099-NEC obligations, and — for California —
the Form 568 annual tax and LLC fee or the Form 100S franchise tax. It
prepares and checks; it does not e-file.

Basis: nominal dollars of ``tax_year``; calendar tax year assumed (a fiscal
year LLC shifts every due date and is not modelled). Due dates move off a
Saturday or Sunday; legal holidays are not modelled.

Unknown is not zero. A ``null`` figure that determines the entity's income
(gross receipts, COGS, an expense, guaranteed payments, officer wages, the
employer payroll tax) stops the computation and is listed. A ``null`` that
only affects a check (owner basis, distributions, a contractor's W-9 or
entity type, a state payment) is listed and the check is reported as bounded
or undetermined.

Refuses (``LLCReturnError``, with a pointer): C-corporation classification;
rental or real-estate LLCs (``passive-loss-eligibility``); asset-level
depreciation and §179 detail (``depreciation-election`` — supply the resulting
amount); inventory accounting beyond a supplied COGS figure; multi-state
apportionment; foreign owners and §1446 withholding; partnership special
allocations, §754 and §704(c); payroll filing mechanics (941/940/DE 9) beyond
annual totals; an S election that takes effect partway through the year.

Reuses: California LLC annual tax, fee tiers, first-year exemption window and
due-month rules from :mod:`pf.ca_return`; the SE earnings factor and $400
floor from :mod:`pf.federal_return`; the Social Security wage base and
employer FICA rates from :mod:`pf.aid`.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from math import isfinite

from . import aid as _aid
from . import ca_return as _ca
from . import federal_return as _fed

# ── classifications and scope ───────────────────────────────────────────

DISREGARDED = "disregarded"
PARTNERSHIP = "partnership"
S_CORP = "s_corp"
#: Treas. Reg. §301.7701-3: an LLC is disregarded (one owner) or a
#: partnership (two or more) by default, or elects corporate status (Form
#: 8832) and then S status (Form 2553). C-corporation status is refused.
CLASSIFICATIONS = (DISREGARDED, PARTNERSHIP, S_CORP)

FORM = {DISREGARDED: "Schedule C (Form 1040)", PARTNERSHIP: "Form 1065",
        S_CORP: "Form 1120-S"}
K1_FORM = {PARTNERSHIP: "1065", S_CORP: "1120S"}

#: Keys that put an LLC outside this module, and where to go instead.
OUT_OF_SCOPE = {
    "rental_properties": "rental real estate is a passive activity (Form 8825, "
                         "§469); use passive-loss-eligibility",
    "real_estate": "real-estate activity is a passive activity; use "
                   "passive-loss-eligibility",
    "rental": "rental activity is a passive activity; use passive-loss-eligibility",
    "inventory": "inventory accounting (§471, Form 1125-A detail) is not "
                 "modelled; supply cost_of_goods_sold as a single figure",
    "apportionment": "multi-state apportionment (Schedule R, state sourcing) is "
                     "not modelled",
    "other_states": "multi-state filing and apportionment is not modelled",
    "special_allocations": "partnership special allocations (§704(b)) are not "
                           "modelled; this module allocates strictly by share",
    "section_754": "a §754 election and §743(b)/§734(b) adjustments are not modelled",
    "section_704c": "§704(c) built-in gain allocations are not modelled",
    "section_179": "asset-level §179 detail belongs in depreciation-election; "
                   "enter the resulting amount as depreciation",
    "assets": "asset-level depreciation belongs in depreciation-election; enter "
              "the resulting amount as depreciation",
    "payroll_filings": "payroll filing mechanics (Forms 941/940, CA DE 9) are not "
                       "modelled beyond annual totals",
    "withholding_1446": "§1446 withholding on foreign partners is not modelled",
}

#: Treas. Reg. §1.6041-1(a)(1)(iv): payments by card or through a
#: third-party settlement organization are reported on Form 1099-K by the
#: processor, not on 1099-NEC by the payer.
CARD_PAYMENT_METHODS = ("card", "third_party_network")
#: Categories that on Schedule C / Form 1065 cover employees only; the owner's
#: own retirement contributions and health insurance go elsewhere.
OWNER_SENSITIVE_CATEGORIES = ("retirement_plans", "employee_benefit_programs")
#: Which payee entity types are exempt from 1099-NEC (Instructions for Forms
#: 1099-MISC and 1099-NEC, "Payments to corporations"), except attorney fees.
EXEMPT_PAYEE_TYPES = ("corporation", "s_corp", "c_corp")
PAYEE_TYPES = ("individual", "sole_proprietor", "partnership", "llc") + EXEMPT_PAYEE_TYPES

#: Rev. Proc. 2002-69: spouses who own an entity as community property may
#: treat it as disregarded or as a partnership. These are the community
#: property states (IRS Pub. 555); elective-community-property states are not
#: included.
COMMUNITY_PROPERTY_STATES = ("AZ", "CA", "ID", "LA", "NV", "NM", "TX", "WA", "WI")

# ── statutory rules that do not change annually ─────────────────────────

#: §274(n)(1): business meals are 50% deductible (the 2021-2022 restaurant
#: exception expired). Schedule C instructions, line 24b.
MEALS_DEDUCTIBLE_SHARE = 0.50
#: Rev. Proc. 2013-13 (Schedule C instructions, Simplified Method Worksheet):
#: $5 per square foot, at most 300 square feet, no carryforward.
SIMPLIFIED_HOME_OFFICE_RATE = 5.0
SIMPLIFIED_HOME_OFFICE_MAX_SQFT = 300.0
#: §195(b)(1) start-up costs, §248(a) corporate and §709(b) partnership
#: organizational costs: deduct up to $5,000 in the year business begins,
#: reduced dollar for dollar by costs above $50,000; amortize the rest
#: ratably over 180 months starting with the month business begins.
STARTUP_IMMEDIATE = 5_000.0
STARTUP_PHASEOUT_START = 50_000.0
STARTUP_AMORTIZATION_MONTHS = 180
#: §3406(a)(1): backup withholding at the fourth-lowest rate in §1(c),
#: 24% since 2018 (made permanent by P.L. 119-21).
BACKUP_WITHHOLDING_RATE = 0.24
#: §6698(b)(1) / §6699(b)(1): the per-owner monthly penalty runs for at most
#: 12 months.
LATE_PENALTY_MAX_MONTHS = 12
#: §183(d): an activity is presumed to be for profit if it shows a profit in
#: 3 or more of 5 consecutive years.
HOBBY_PROFIT_YEARS = 3
HOBBY_WINDOW_YEARS = 5
#: §6072(b) (Forms 1065 and 1120-S): the 15th day of the 3rd month after the
#: year ends; §6072(a): the owner's 1040, with Schedule C, the 15th day of the
#: 4th month.
ENTITY_RETURN_MONTH = 3
INDIVIDUAL_RETURN_MONTH = 4
#: Rev. Proc. 84-35: a partnership of 10 or fewer partners, all individuals
#: (or estates) reporting their shares, with each partner's share of every
#: item the same, may show reasonable cause for a late Form 1065. Relief is
#: requested, not automatic.
SMALL_PARTNERSHIP_MAX_PARTNERS = 10
#: §6071(c): Form 1099-NEC is due to the IRS and the payee by January 31.
NEC_DUE = (1, 31)
#: §1402(a)(12), §1402(b)(2) — reused from the federal module so the two
#: never disagree.
SE_EARNINGS_FACTOR = _fed.SE_EARNINGS_FACTOR
SE_MINIMUM_EARNINGS = _fed.SE_MINIMUM_EARNINGS
#: §3111(a)-(b): employer OASDI and Medicare rates equal the employee rates.
EMPLOYER_OASDI_RATE = _aid.OASDI_RATE
EMPLOYER_MEDICARE_RATE = _aid.MEDICARE_RATE

# ── California (Form 568 rules reused from ca_return) ───────────────────

CA_LLC_ANNUAL_TAX = _ca.LLC_ANNUAL_TAX
CA_LLC_FIRST_YEAR_EXEMPT_YEARS = _ca.LLC_FIRST_YEAR_EXEMPT_YEARS
CA_LLC_FEE_ESTIMATE_MONTH = _ca.LLC_FEE_ESTIMATE_MONTH
CA_SMLLC_RETURN_MONTH = _ca.LLC_RETURN_MONTH
#: 2025 Form 568 booklet, "When and Where to File": an LLC classified as a
#: partnership files by the 15th day of the 3rd month (R&TC §18633.5).
CA_PARTNERSHIP_RETURN_MONTH = 3
#: 2025 Form 568 booklet, "Estimated Fee for LLCs": the penalty is 10% of the
#: fee owed over the timely estimated payment (R&TC §17942(d)(2)).
CA_FEE_UNDERPAYMENT_PENALTY = 0.10
#: 2025 Form 100S booklet, General Information B: S corporations pay the
#: greater of 1.5% of net income or the $800 minimum franchise tax
#: (R&TC §23802(b), §23153). Financial S corporations (3.5%) are not modelled.
CA_S_CORP_RATE = 0.015
CA_MIN_FRANCHISE_TAX = 800.0
#: 2025 Form 100S booklet, General Information K: Form 100-ES installments of
#: 30/40/0/30% on the 15th day of the 4th, 6th, 9th and 12th months; the first
#: is never less than the minimum franchise tax.
CA_CORP_ES_SHARES = (0.30, 0.40, 0.0, 0.30)
#: 2026 Form 100-ES instructions, Worksheet I line 11: cumulative required
#: 30/70/70/100%. When the tax is no more than the minimum, all of it is due
#: with the first installment; otherwise the first is at least the minimum.
CA_CORP_ES_CUMULATIVE = (0.30, 0.70, 0.70, 1.00)
CA_CORP_ES_MONTHS = (4, 6, 9, 12)
#: 2025 Form 568 booklet, General Information D: an LLC whose taxable year
#: is 15 days or less and that did no business in California during it files
#: no return and owes no annual tax or fee (R&TC §17946).
CA_SHORT_YEAR_DAYS = 15
#: 2025 Form 568 booklet, General Information G: no fee-estimate penalty if
#: the timely estimate is at least the preceding year's total fee.
#: Same booklet: late Form 568 costs $18 per member per month, 12 months max.
CA_568_LATE_PER_MEMBER_MONTH = 18.0
#: EDD Form DE 542: report an independent contractor (individual or sole
#: proprietor) paid $600 or more within 20 days (Unemployment Insurance Code
#: §1088.8). California did not adopt the federal $2,000 change.
CA_DE542_THRESHOLD = 600.0

#: Transcribed from the cited sources (read 2026-11-22); marked unverified
#: until a human checks them, per the repository's provenance policy.
LLC_VERIFIED = "unverified"
STATUTORY_SOURCE = (
    "IRC §§195, 248, 709, 274(n), 183(d), 1402, 3406, 6071, 6072, 6698, 6699; "
    "Rev. Proc. 2013-13; Rev. Proc. 2002-69; 2025 Instructions for Form 1065, "
    "Form 1120-S and Schedule C; 2025 FTB Form 568 and Form 100S booklets; "
    "EDD DE 542")


@dataclass(frozen=True)
class LLCYear:
    """Year-specific figures. ``mileage_rates`` holds one rate, or two when
    the IRS changed the rate mid-year (first half, second half)."""
    nec_threshold: float
    mileage_rates: tuple[float, ...]
    #: §6698(b)(1)/§6699(b)(1) amount for returns required to be filed in
    #: the year after ``tax_year``.
    late_penalty_per_owner_month: float
    source: str
    verified_on: str = LLC_VERIFIED


LLC_TABLES: dict[int, LLCYear] = {
    2025: LLCYear(
        nec_threshold=600.0, mileage_rates=(0.70,),
        late_penalty_per_owner_month=255.0,
        source="§6041(a) $600 for payments before 2026; IR-2024-312 (70¢); "
               "2025 Instructions for Form 1065 and Form 1120-S, Penalties "
               "($255 for returns required to be filed in 2026)"),
    2026: LLCYear(
        nec_threshold=2_000.0, mileage_rates=(0.725, 0.76),
        late_penalty_per_owner_month=260.0,
        source="P.L. 119-21 §70433 and Rev. Proc. 2025-32 §2.15 ($2,000 for "
               "payments after 2025, indexed from 2027); IR-2025-128 (72.5¢ "
               "Jan-Jun) and IR-2026-29 (76¢ Jul-Dec); Rev. Proc. 2025-32 "
               "§3.55-3.56 ($260 for returns required to be filed in 2027)"),
}

#: Expense categories → (Schedule C line, Form 1065 line, Form 1120-S line).
#: Line numbers from the 2025 forms and instructions. Any other key is
#: accepted and lands on "other expenses / other deductions".
CATEGORY_LINES: dict[str, tuple[str, str, str]] = {
    "advertising": ("8", "21", "16"),
    "commissions_and_fees": ("10", "21", "20"),
    "contract_labor": ("11", "21", "20"),
    "employee_benefit_programs": ("14", "19", "18"),
    "insurance": ("15", "21", "20"),
    "mortgage_interest": ("16a", "15", "13"),
    "interest": ("16b", "15", "13"),
    "legal_and_professional": ("17", "21", "20"),
    "office_expense": ("18", "21", "20"),
    "retirement_plans": ("19", "18", "17"),
    "rent_vehicles_equipment": ("20a", "13", "11"),
    "rent": ("20b", "13", "11"),
    "repairs": ("21", "11", "9"),
    "supplies": ("22", "21", "20"),
    "taxes_and_licenses": ("23", "14", "12"),
    "travel": ("24a", "21", "20"),
    "utilities": ("25", "21", "20"),
    "wages": ("26", "9", "8"),
    "bad_debts": ("27b", "12", "10"),
}
OTHER_LINE = ("27b", "21", "20")
#: Fixed line assignments for items the module computes.
LINES = {
    "gross_receipts": ("1", "1a", "1a"),
    "returns": ("2", "1b", "1b"),
    "cogs": ("4", "2", "2"),
    "other_income": ("6", "7", "5"),
    "gross_income": ("7", "8", "6"),
    "vehicle": ("9", "21", "20"),
    "depreciation": ("13", "16c", "14"),
    "meals": ("24b", "21", "20"),
    "startup": ("27b", "21", "20"),
    "guaranteed_payments": (None, "10", None),
    "officer_wages": (None, None, "7"),
    "payroll_taxes": (None, None, "12"),
    "total_deductions": ("28", "22", "21"),
    "home_office": ("30", None, None),
    "net": ("31", "23", "22"),
}
COLUMN = {DISREGARDED: 0, PARTNERSHIP: 1, S_CORP: 2}


class LLCReturnError(ValueError):
    """The inputs cannot support the workpaper without guessing, or the LLC
    is outside what this module prepares."""

    def __init__(self, message: str, missing: list[str] | None = None):
        super().__init__(message)
        self.missing = list(missing or [])


def table_for(tax_year: int) -> tuple[LLCYear, bool]:
    """The year's table, or the nearest one and ``True`` (a projection)."""
    if tax_year in LLC_TABLES:
        return LLC_TABLES[tax_year], False
    nearest = min(LLC_TABLES, key=lambda y: (abs(y - tax_year), -y))
    return LLC_TABLES[nearest], True


# ── results ─────────────────────────────────────────────────────────────


@dataclass
class LLCReturn:
    name: str
    tax_year: int
    classification: str
    form: str
    state: str | None
    table_source: str
    projection: bool
    #: Return lines in order: (line, label, amount).
    lines: list
    gross_income: float
    total_deductions: float
    #: Schedule C line 31 net profit, or ordinary business income.
    net: float
    home_office: dict | None
    startup: dict | None
    #: Paste into tax_return.schedule_c[] (disregarded only).
    schedule_c: dict | None
    #: Paste into tax_return.k1[] (partnership / S corp).
    k1: list
    #: Per owner: [(box, label, amount-or-None)].
    k1_boxes: dict
    #: Officer W-2s for tax_return.w2[] (S corp).
    w2: list
    basis: list
    nec: dict
    deadlines: list
    late_penalty: dict | None
    reasonable_comp: dict | None
    ca: dict | None
    #: Paste into tax_return.ca.llc[] (disregarded CA LLC owned by an individual).
    ca_llc: dict | None
    se_note: list
    findings: list = field(default_factory=list)
    bounds: list = field(default_factory=list)
    missing: list = field(default_factory=list)


# ── helpers ─────────────────────────────────────────────────────────────


class _Ctx:
    def __init__(self, name: str) -> None:
        self.name = name
        self.stop: list[str] = []
        self.missing: list[str] = []
        self.findings: list[str] = []
        self.bounds: list[str] = []

    def num(self, value, path: str, *, stop: bool = True,
            allow_negative: bool = False) -> float | None:
        if value is None:
            self.missing.append(path)
            if stop:
                self.stop.append(path)
            return None
        if isinstance(value, bool):
            raise LLCReturnError(f"{path} must be a number, not {value!r}")
        try:
            x = float(value)
        except (TypeError, ValueError) as e:
            raise LLCReturnError(f"{path} must be a number, not {value!r}") from e
        if not isfinite(x):
            raise LLCReturnError(f"{path} must be finite")
        if x < 0 and not allow_negative:
            raise LLCReturnError(f"{path} cannot be negative ({x:,.0f})")
        return x

    def field(self, d: dict, key: str, path: str, *, stop: bool = True,
              allow_negative: bool = False) -> float | None:
        """Absent means none on the books; ``null`` means nobody looked."""
        if key not in d:
            return 0.0
        return self.num(d[key], path, stop=stop, allow_negative=allow_negative)

    def lst(self, d: dict, key: str, path: str, *, stop: bool) -> list | None:
        if key not in d:
            return []
        v = d[key]
        if v is None:
            self.missing.append(f"{path} (list not recorded)")
            if stop:
                self.stop.append(path)
            return None
        if not isinstance(v, list):
            raise LLCReturnError(f"{path} must be a list")
        return v


def _date(value, path: str) -> _dt.date | None:
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    try:
        return _dt.date.fromisoformat(str(value))
    except ValueError as e:
        raise LLCReturnError(f"{path} must be a date (YYYY-MM-DD), not {value!r}") from e


def _line_key(line: str | None) -> tuple[int, str]:
    """Sort return lines numerically: 9 before 16a before 27b."""
    digits = "".join(ch for ch in (line or "") if ch.isdigit())
    return (int(digits) if digits else 999, line or "")


def due(year: int, month: int, day: int = 15) -> _dt.date:
    """A due date, moved off a weekend (§7503; holidays not modelled)."""
    d = _dt.date(year, month, day)
    while d.weekday() >= 5:
        d += _dt.timedelta(days=1)
    return d


def amortize(incurred: float, began: _dt.date, tax_year: int) -> dict:
    """§195 / §248 / §709: the immediate deduction and this year's
    amortization for costs ``incurred`` by a business that began on
    ``began`` (calendar tax year)."""
    immediate_cap = max(0.0, STARTUP_IMMEDIATE - max(0.0, incurred - STARTUP_PHASEOUT_START))
    immediate_amount = min(incurred, immediate_cap)
    base = incurred - immediate_amount
    monthly = base / STARTUP_AMORTIZATION_MONTHS
    if began.year > tax_year:
        return {"incurred": incurred, "immediate": 0.0, "amortization": 0.0,
                "months": 0, "monthly": monthly, "remaining": incurred,
                "not_begun": True}
    if began.year == tax_year:
        immediate, before, months = immediate_amount, 0, 13 - began.month
    else:
        immediate = 0.0
        before = (tax_year - began.year) * 12 - (began.month - 1)
        months = 12
    months = max(0, min(months, STARTUP_AMORTIZATION_MONTHS - before))
    amort = monthly * months
    remaining = max(0.0, base - monthly * (before + months))
    return {"incurred": incurred, "immediate": immediate, "amortization": amort,
            "months": months, "monthly": monthly, "remaining": remaining,
            "not_begun": False}


def _check_scope(llc: dict) -> None:
    for key, why in OUT_OF_SCOPE.items():
        if llc.get(key):
            raise LLCReturnError(f"out of scope — {why}")
    if llc.get("activity") in ("rental", "real_estate"):
        raise LLCReturnError(f"out of scope — {OUT_OF_SCOPE['rental']}")
    dep = llc.get("depreciation")
    if isinstance(dep, (dict, list)):
        raise LLCReturnError(
            "out of scope — asset-level depreciation detail belongs in "
            "depreciation-election; enter the resulting deduction as a single "
            "depreciation amount")
    if llc.get("classification") == "c_corp":
        raise LLCReturnError(
            "out of scope — an LLC taxed as a C corporation files Form 1120 and "
            "pays entity-level tax; this module prepares disregarded, "
            "partnership and S-corporation LLCs only")
    for o in llc.get("owners") or []:
        if isinstance(o, dict) and o.get("foreign"):
            raise LLCReturnError(
                "out of scope — a foreign owner brings §1446 withholding (Forms "
                "8804/8805) and, for an S corporation, ineligibility (§1361(b)); "
                "not modelled")


# ── the computation ─────────────────────────────────────────────────────


def compute(llc: dict, *, tax_year: int, state: str | None = None,
            spouses: tuple[str, str] | None = None,
            household_state: str | None = None) -> LLCReturn:
    """Prepare the workpaper for one LLC.

    ``state`` overrides ``llc["state"]``. ``spouses`` (two member ids) and
    ``household_state`` decide whether the Rev. Proc. 2002-69 note applies.
    """
    if not isinstance(llc, dict):
        raise LLCReturnError("each llc_returns entry must be a mapping")
    name = str(llc.get("name") or "LLC")
    ctx = _Ctx(name)
    _check_scope(llc)
    try:
        tax_year = int(tax_year)
    except (TypeError, ValueError) as e:
        raise LLCReturnError("tax_year is required", ["tax_return.tax_year"]) from e
    state = (state if state is not None else llc.get("state"))
    state = str(state).upper() if state else None
    table, projection = table_for(tax_year)

    cls = llc.get("classification")
    if cls is None:
        raise LLCReturnError(f"{name}: classification is required",
                             ["classification"])
    if cls not in CLASSIFICATIONS:
        raise LLCReturnError(
            f"{name}: classification must be one of {', '.join(CLASSIFICATIONS)}, "
            f"not {cls!r}")
    col = COLUMN[cls]

    method = llc.get("accounting_method", "cash")
    if method not in ("cash", "accrual"):
        raise LLCReturnError(f"{name}: accounting_method must be cash or accrual")

    formed = _date(llc.get("formed_on"), "formed_on")
    if formed is None:
        ctx.missing.append("formed_on")
    elif formed.year > tax_year:
        raise LLCReturnError(f"{name}: formed {formed.isoformat()}, after tax year "
                             f"{tax_year} — no return for that year")
    first_year = formed is not None and formed.year == tax_year

    owners = _owners(ctx, llc, cls, spouses, household_state, state)
    members = [o["member"] for o in owners]

    if cls == S_CORP:
        _s_election(ctx, llc, tax_year, formed)

    # ── income ──
    gross = ctx.num(llc.get("gross_receipts"), "gross_receipts")
    returns = ctx.field(llc, "returns_and_allowances", "returns_and_allowances")
    cogs = ctx.field(llc, "cost_of_goods_sold", "cost_of_goods_sold")
    other = ctx.field(llc, "other_income", "other_income", allow_negative=True)
    interest = ctx.field(llc, "interest_income", "interest_income")
    dividends = ctx.field(llc, "dividend_income", "dividend_income")

    # ── deductions ──
    expenses = llc.get("expenses")
    if expenses is None and "expenses" in llc:
        ctx.missing.append("expenses")
        ctx.stop.append("expenses")
    expenses = expenses or {}
    if not isinstance(expenses, dict):
        raise LLCReturnError(f"{name}: expenses must be a mapping of category: amount")
    exp_rows = []
    unmapped = []
    for k, v in expenses.items():
        x = ctx.num(v, f"expenses.{k}")
        line = CATEGORY_LINES.get(k)
        if line is None:
            if k != "other":
                unmapped.append(k)
            line = OTHER_LINE
        exp_rows.append((k, line[col], x))
    if unmapped:
        ctx.findings.append(
            f"Categories {', '.join(sorted(unmapped))} have no dedicated line and are "
            f"reported as other {'expenses (Part V)' if cls == DISREGARDED else 'deductions'}"
            " — itemize them on the attached statement.")
    sensitive = [k for k in OWNER_SENSITIVE_CATEGORIES if expenses.get(k)]
    if sensitive and cls == DISREGARDED:
        ctx.findings.append(
            f"{', '.join(sensitive)} on Schedule C lines 14/19 are for employees only. "
            "The owner's own SEP/solo 401(k) contributions and self-employed health "
            "insurance go on Schedule 1, not Schedule C — on these lines they "
            "understate SE tax and QBI. Move any owner amounts out.")
    elif sensitive and cls == PARTNERSHIP:
        ctx.findings.append(
            f"{', '.join(sensitive)} on Form 1065 lines 18/19 are for employees only. "
            "Contributions for a partner are reported on K-1 box 13 (code R), and "
            "a partner's health insurance is a guaranteed payment — not an entity "
            "deduction on these lines.")
    elif sensitive and cls == S_CORP:
        ctx.findings.append(
            "Health insurance for a more-than-2% shareholder is deductible by the S "
            "corporation only if included in that officer's W-2 box 1 wages (Notice "
            "2008-1); check the officer W-2.")
    if cls == PARTNERSHIP and (expenses.get("wages") or 0) and members:
        ctx.findings.append(
            "Wages on a partnership return are for employees only; a member "
            "cannot be a W-2 employee of the partnership (Rev. Rul. 69-184) — "
            "payments to members belong in guaranteed_payments.")

    meals_raw = ctx.field(llc, "meals", "meals")
    meals = None if meals_raw is None else meals_raw * MEALS_DEDUCTIBLE_SHARE
    depreciation = 0.0
    if "depreciation" in llc:
        depreciation = ctx.num(llc["depreciation"], "depreciation", stop=False)
        if depreciation is None:
            ctx.bounds.append(
                "depreciation is not recorded — net income is an upper bound "
                "(run depreciation-election and enter the amount).")
            depreciation = 0.0
    vehicle = _vehicle(ctx, llc, table)
    startup = _startup(ctx, llc, cls, tax_year)

    gp_rows, officer_rows, payroll_tax = [], [], 0.0
    gp_total = officer_total = 0.0
    if cls == PARTNERSHIP:
        gp_rows = _member_amounts(ctx, llc, "guaranteed_payments", members, stop=True)
        gp_total = sum(r["amount"] for r in gp_rows if r["amount"] is not None)
    elif llc.get("guaranteed_payments"):
        raise LLCReturnError(
            f"{name}: guaranteed payments exist only in a partnership; a "
            f"{cls.replace('_', ' ')} pays its owner "
            + ("wages (officer_wages)" if cls == S_CORP else "nothing — the owner "
               "draws, and the draw is not a deduction"))
    if cls == S_CORP:
        officer_rows = _officers(ctx, llc)
        officer_total = sum(r["amount"] for r in officer_rows if r["amount"] is not None)
        payroll_tax = ctx.num(llc.get("payroll_taxes_employer", 0.0),
                              "payroll_taxes_employer") or 0.0
    elif llc.get("officer_wages"):
        raise LLCReturnError(
            f"{name}: officer wages exist only in an S corporation; "
            + ("a partnership pays members guaranteed payments"
               if cls == PARTNERSHIP else "a disregarded LLC's owner is not "
               "its employee"))

    if ctx.stop:
        raise LLCReturnError(
            f"{name}: figures that determine the entity's income are not "
            "recorded — refusing to guess", sorted(set(ctx.stop)))

    lines: list = []

    def line(key: str, label: str, amount: float) -> None:
        ln = LINES[key][col]
        lines.append((ln, label, amount))

    if returns > gross:
        raise LLCReturnError(f"{name}: returns_and_allowances exceed gross_receipts")
    gross_income = gross - returns - cogs + other
    line("gross_receipts", "Gross receipts or sales", gross)
    if returns:
        line("returns", "Returns and allowances", -returns)
    if cogs:
        line("cogs", "Cost of goods sold (supplied figure)", -cogs)
    if other:
        line("other_income", "Other income", other)
    line("gross_income", "Gross income", gross_income)

    deductions: list[tuple[str, str, float]] = []
    if cls == S_CORP:
        deductions.append((LINES["officer_wages"][col], "Compensation of officers",
                           officer_total))
    if cls == PARTNERSHIP:
        deductions.append((LINES["guaranteed_payments"][col],
                           "Guaranteed payments to partners", gp_total))
    for k, ln, x in exp_rows:
        if k == "taxes_and_licenses" and cls == S_CORP:
            continue
        deductions.append((ln, k.replace("_", " ").capitalize(), x))
    if cls == S_CORP and (payroll_tax or "taxes_and_licenses" in expenses):
        deductions.append((LINES["payroll_taxes"][col],
                           "Taxes and licenses (incl. employer payroll tax)",
                           payroll_tax + float(expenses.get("taxes_and_licenses") or 0)))
    if vehicle["amount"]:
        deductions.append((LINES["vehicle"][col], vehicle["label"], vehicle["amount"]))
    if depreciation:
        deductions.append((LINES["depreciation"][col],
                           "Depreciation (from depreciation-election)", depreciation))
    if meals:
        deductions.append((LINES["meals"][col],
                           f"Meals ({MEALS_DEDUCTIBLE_SHARE:.0%} of ${meals_raw:,.0f})",
                           meals))
    if startup and startup["deduction"]:
        deductions.append((LINES["startup"][col],
                           "Start-up / organizational costs (Form 4562 Part VI)",
                           startup["deduction"]))
    deductions.sort(key=lambda d: _line_key(d[0]))
    for ln, label, x in deductions:
        lines.append((ln, label, -x))
    total_ded = sum(x for _, _, x in deductions)
    line("total_deductions", "Total deductions" if cls != DISREGARDED
         else "Total expenses", -total_ded)

    tentative = gross_income - total_ded
    home = _home_office(ctx, llc, cls, tentative)
    if home and home["allowed"]:
        line("home_office", f"Business use of home ({home['method']})", -home["allowed"])
    net = tentative - (home["allowed"] if home else 0.0)
    line("net", "Net profit or (loss)" if cls == DISREGARDED
         else "Ordinary business income (loss)", net)

    sstb = llc.get("sstb")
    ubia = llc.get("ubia")
    if ubia is not None:
        ubia = ctx.num(ubia, "ubia")
    if sstb is None:
        ctx.missing.append("sstb (needed by the owner's §199A computation above "
                           "the threshold)")
    if ubia is None:
        ctx.missing.append("ubia (needed by the owner's §199A computation above "
                           "the threshold)")
    w2_wages_paid = float(expenses.get("wages") or 0) + officer_total
    nondeductible = (meals_raw or 0.0) - (meals or 0.0)

    dist_rows = _member_amounts(ctx, llc, "distributions", members, stop=False)
    dists = None
    if dist_rows is not None:
        dists = {}
        for m in members:
            mine = [r["amount"] for r in dist_rows if r["member"] == m]
            dists[m] = None if None in mine else sum(mine)

    schedule_c = None
    se_note: list = []
    k1, k1_boxes, w2, basis = [], {}, [], []
    reasonable = None
    if cls == DISREGARDED:
        split = _se_split(ctx, llc, owners)
        schedule_c = [
            _schedule_c_handoff(name, member, frac, gross - returns, cogs, other,
                                exp_rows, meals, depreciation, startup, vehicle, home,
                                sstb, w2_wages_paid, ubia, len(split) > 1)
            for member, frac in split]
        for member, frac in split:
            earnings = max(0.0, net * frac) * SE_EARNINGS_FACTOR
            who = "" if len(split) == 1 else f"{member}: "
            if earnings >= SE_MINIMUM_EARNINGS:
                se_note.append(
                    f"{who}Net earnings from self-employment are ${earnings:,.0f} "
                    f"({SE_EARNINGS_FACTOR:.2%} of ${net * frac:,.0f}), at or above "
                    f"${SE_MINIMUM_EARNINGS:,.0f}: SE tax applies. federal-tax-return "
                    "computes it (with the owner's W-2 Social Security wages).")
            else:
                se_note.append(
                    f"{who}Net earnings from self-employment are ${earnings:,.0f}, "
                    f"under ${SE_MINIMUM_EARNINGS:,.0f}: no SE tax.")
        if interest or dividends:
            ctx.findings.append(
                "Interest and dividends of a disregarded LLC go on the owner's "
                "Schedule B (1099-INT/DIV), not Schedule C.")
    else:
        k1, k1_boxes = _k1s(ctx, name, cls, owners, net, gp_rows, interest, dividends,
                            dists, w2_wages_paid, ubia, sstb, nondeductible)
        basis = _basis(ctx, cls, owners, net, interest, dividends, dists, llc,
                       nondeductible, members)
        if cls == PARTNERSHIP:
            for row in k1:
                e = row["se_earnings"]
                if e is not None and e * SE_EARNINGS_FACTOR >= SE_MINIMUM_EARNINGS:
                    se_note.append(
                        f"{row['owner']}: box 14A ${e:,.0f} → SE tax on the "
                        "member's own Schedule SE (computed by federal-tax-return).")
            if any(o["active"] is None for o in owners):
                ctx.missing.append("owners[].active (decides box 14A self-employment "
                                   "earnings)")
        else:
            base_wb, _p = _aid.wage_base_for(tax_year)
            w2 = [{"employer": name, "owner": r["member"], "wages": r["amount"],
                   "federal_withheld": r["federal_withheld"],
                   "ss_wages": min(r["amount"], base_wb), "ss_withheld": r["ss_withheld"],
                   "medicare_wages": r["amount"],
                   "medicare_withheld": r["medicare_withheld"]} for r in officer_rows]
            ctx.findings.append(
                "Officer W-2 hand-off: box 1 wages equal the payroll amount; pre-tax "
                "401(k) or cafeteria deferrals (which lower box 1 but not boxes 3/5) "
                "are not modelled — copy box 1 from the actual W-2.")
            reasonable = _reasonable_comp(ctx, llc, owners, officer_rows, dists, net,
                                          payroll_tax, tax_year)
            se_note.append("S-corporation K-1 income carries no self-employment tax; "
                           "payroll tax is paid on officer wages instead.")

    _hobby(ctx, llc, net, tax_year)
    nec = _nec(ctx, llc, table, tax_year, state, expenses)
    deadlines, late = _deadlines(cls, tax_year, len(owners), table, nec)
    ca, ca_llc = None, None
    if state == "CA":
        ca, ca_llc = _california(ctx, llc, cls, tax_year, formed, first_year, gross,
                                 returns, other, interest, dividends, net, deadlines,
                                 name, owners)
    elif state:
        ctx.findings.append(
            f"State obligations for {state} are not modelled — check that state's "
            "LLC registration fee, franchise or gross-receipts tax and annual report.")
    else:
        ctx.missing.append("state (state of organization or registration)")

    if projection:
        ctx.findings.append(
            f"No {tax_year} table ships with the module; the 1099-NEC threshold, "
            "mileage rate and late-filing penalty are the nearest year's — a "
            "projection.")
    deadlines.sort(key=lambda d: d[0])

    return LLCReturn(
        name=name, tax_year=tax_year, classification=cls, form=FORM[cls],
        state=state, table_source=table.source, projection=projection,
        lines=lines, gross_income=gross_income, total_deductions=total_ded, net=net,
        home_office=home, startup=startup, schedule_c=schedule_c, k1=k1,
        k1_boxes=k1_boxes, w2=w2, basis=basis, nec=nec, deadlines=deadlines,
        late_penalty=late, reasonable_comp=reasonable, ca=ca, ca_llc=ca_llc,
        se_note=se_note, findings=ctx.findings, bounds=ctx.bounds,
        missing=list(dict.fromkeys(ctx.missing)))


# ── components ──────────────────────────────────────────────────────────


def _owners(ctx: _Ctx, llc: dict, cls: str, spouses, household_state,
            state) -> list[dict]:
    rows = llc.get("owners")
    if not rows or not isinstance(rows, list):
        raise LLCReturnError(f"{ctx.name}: owners is required (member, share)",
                             ["owners"])
    out = []
    for i, o in enumerate(rows):
        if not isinstance(o, dict) or not o.get("member"):
            raise LLCReturnError(f"{ctx.name}: owners[{i}].member is required",
                                 [f"owners[{i}].member"])
        share = o.get("share")
        if share is None:
            raise LLCReturnError(f"{ctx.name}: owners[{i}].share is required",
                                 [f"owners[{i}].share"])
        share = ctx.num(share, f"owners[{i}].share")
        if not 0 < share <= 1:
            raise LLCReturnError(f"{ctx.name}: owners[{i}].share must be in (0, 1]")
        out.append({"member": str(o["member"]), "share": share,
                    "active": o.get("active"),
                    "material_participation": o.get("material_participation")})
    if len({o["member"] for o in out}) != len(out):
        raise LLCReturnError(f"{ctx.name}: an owner is listed twice")
    total = sum(o["share"] for o in out)
    if abs(total - 1.0) > 1e-6:
        raise LLCReturnError(f"{ctx.name}: owner shares sum to {total:.4f}, not 1")

    ids = {o["member"] for o in out}
    spouse_pair = bool(spouses) and len(out) == 2 and ids == set(spouses)
    cp = (household_state or "").upper() in COMMUNITY_PROPERTY_STATES
    if cls == DISREGARDED and len(out) > 1:
        if spouse_pair and cp:
            ctx.findings.append(
                "Two spouses owning the LLC as community property in "
                f"{household_state.upper()} may treat it as disregarded (Rev. Proc. "
                "2002-69). Report it consistently; switching later is a change "
                "in classification.")
        else:
            raise LLCReturnError(
                f"{ctx.name}: a disregarded LLC has one owner; {len(out)} are "
                "listed. Only spouses holding it as community property may treat "
                "a two-member LLC as disregarded (Rev. Proc. 2002-69) — otherwise "
                "it is a partnership")
    if cls == PARTNERSHIP:
        if len(out) < 2:
            raise LLCReturnError(
                f"{ctx.name}: a single-member LLC cannot be a partnership — it is "
                "disregarded unless it elects corporate status")
        if spouse_pair and cp:
            ctx.findings.append(
                "The two owners are spouses in a community property state: Rev. "
                "Proc. 2002-69 lets them report as a disregarded entity on one "
                "Schedule C instead of filing Form 1065. The qualified joint "
                "venture election (§761(f)) is not available to an LLC.")
    if cls == S_CORP and any(o.get("entity") for o in rows if isinstance(o, dict)):
        raise LLCReturnError(
            f"{ctx.name}: an S corporation's shareholders must be individuals, "
            "estates or certain trusts (§1361(b)(1)(B)); an entity owner is not "
            "modelled")
    return out


def _s_election(ctx: _Ctx, llc: dict, tax_year: int, formed) -> None:
    eff = _date(llc.get("s_election_effective"), "s_election_effective")
    if eff is None:
        raise LLCReturnError(
            f"{ctx.name}: s_election_effective is required for an S corporation "
            "(Form 2553 effective date)", ["s_election_effective"])
    if eff.year > tax_year:
        raise LLCReturnError(
            f"{ctx.name}: the S election takes effect {eff.isoformat()}, after "
            f"{tax_year} — for {tax_year} the LLC is not an S corporation")
    start = max(_dt.date(tax_year, 1, 1), formed) if formed else _dt.date(tax_year, 1, 1)
    if eff.year == tax_year and eff > start:
        raise LLCReturnError(
            f"out of scope — the S election takes effect {eff.isoformat()}, partway "
            f"through {tax_year}: the year splits into a short pre-election period "
            "(Schedule C or Form 1065) and a short Form 1120-S, which this module "
            "does not prepare")
    ctx.findings.append(
        "S election in force for the whole year. A late election needs Rev. Proc. "
        "2013-30 relief; confirm the IRS acceptance letter (CP261) is on file.")


def _member_amounts(ctx: _Ctx, llc: dict, key: str, members: list[str], *,
                    stop: bool) -> list | None:
    rows = ctx.lst(llc, key, key, stop=stop)
    if rows is None:
        return None
    out = []
    for i, r in enumerate(rows):
        m = r.get("member") if isinstance(r, dict) else None
        if m is None:
            raise LLCReturnError(f"{ctx.name}: {key}[{i}].member is required")
        if m not in members:
            raise LLCReturnError(f"{ctx.name}: {key}[{i}].member {m!r} is not an owner")
        out.append({"member": m,
                    "amount": ctx.num(r.get("amount"), f"{key}[{i}].amount", stop=stop)})
    return out


def _officers(ctx: _Ctx, llc: dict) -> list:
    rows = ctx.lst(llc, "officer_wages", "officer_wages", stop=True) or []
    out = []
    for i, r in enumerate(rows):
        p = f"officer_wages[{i}]"
        if not isinstance(r, dict) or not r.get("member"):
            raise LLCReturnError(f"{ctx.name}: {p}.member is required")
        out.append({
            "member": r["member"], "amount": ctx.num(r.get("amount"), f"{p}.amount"),
            "federal_withheld": _opt_known(ctx, r, "federal_withheld", p),
            "ss_withheld": _opt_known(ctx, r, "ss_withheld", p),
            "medicare_withheld": _opt_known(ctx, r, "medicare_withheld", p)})
    return out


def _opt_known(ctx: _Ctx, r: dict, key: str, p: str) -> float | None:
    """A W-2 withholding figure: absent or null is unknown, never zero."""
    v = r.get(key)
    if v is None:
        ctx.missing.append(f"{p}.{key}")
        return None
    return ctx.num(v, f"{p}.{key}")


def _se_split(ctx: _Ctx, llc: dict, owners: list) -> list[tuple[str, float]]:
    """Who carries the Schedule C. One owner: all of it. Spouses under Rev.
    Proc. 2002-69: §1402(a)(5)(A) attributes SE income to the spouse(s)
    carrying on the business — by ``se_share`` if recorded, else by share."""
    if len(owners) == 1:
        return [(owners[0]["member"], 1.0)]
    raw = {o["member"]: o for o in llc.get("owners") or []}
    split = []
    for o in owners:
        x = raw.get(o["member"], {}).get("se_share")
        split.append((o["member"], o["share"] if x is None
                      else ctx.num(x, f"owners[{o['member']}].se_share")))
    total = sum(f for _, f in split)
    if abs(total - 1.0) > 1e-6:
        raise LLCReturnError(f"{ctx.name}: owners[].se_share sums to {total:.4f}, not 1")
    ctx.findings.append(
        "SE income is split between the spouses by "
        + ("se_share" if any(raw.get(m, {}).get("se_share") is not None for m, _ in split)
           else "ownership share (record owners[].se_share if one spouse runs the "
           "business)")
        + " (§1402(a)(5)(A)); each spouse gets a Schedule C row and Social Security "
        "credit for their part.")
    return [(m, f) for m, f in split if f > 0]


def _vehicle(ctx: _Ctx, llc: dict, table: LLCYear) -> dict:
    v = llc.get("vehicle")
    none = {"amount": 0.0, "label": "", "method": None}
    if not v:
        return none
    method = v.get("method")
    if method == "actual":
        amt = ctx.num(v.get("amount"), "vehicle.amount")
        return {"amount": amt or 0.0, "method": "actual",
                "label": "Car and truck expenses (actual, business share)"}
    if method != "standard":
        raise LLCReturnError(f"{ctx.name}: vehicle.method must be standard or actual")
    miles = v.get("business_miles")
    rates = table.mileage_rates
    if miles is None:
        ctx.num(None, "vehicle.business_miles")
        return none
    if isinstance(miles, list):
        if len(miles) != len(rates):
            raise LLCReturnError(
                f"{ctx.name}: vehicle.business_miles has {len(miles)} periods; the "
                f"year has {len(rates)} mileage rate(s)")
        ms = [ctx.num(m, "vehicle.business_miles") or 0.0 for m in miles]
        amt = sum(m * r for m, r in zip(ms, rates))
        label = " + ".join(f"{m:,.0f} mi × {r * 100:g}¢" for m, r in zip(ms, rates))
    else:
        m = ctx.num(miles, "vehicle.business_miles") or 0.0
        if len(rates) > 1:
            r = min(rates)
            ctx.bounds.append(
                f"The mileage rate changed mid-year ({', '.join(f'{x * 100:g}¢' for x in rates)}) "
                "and business_miles is one total — the lower rate was used, so "
                "the vehicle deduction is a lower bound. Record miles as "
                "[first half, second half].")
        else:
            r = rates[0]
        amt = m * r
        label = f"{m:,.0f} mi × {r * 100:g}¢"
    return {"amount": amt, "method": "standard",
            "label": f"Car and truck expenses (standard mileage: {label})"}


def _startup(ctx: _Ctx, llc: dict, cls: str, tax_year: int) -> dict | None:
    sc = llc.get("startup_costs") or {}
    incurred = ctx.field(sc, "incurred", "startup_costs.incurred", stop=True) if sc else 0.0
    org = ctx.field(llc, "organizational_costs", "organizational_costs")
    if not incurred and not org:
        return None
    began = _date(sc.get("business_began"), "startup_costs.business_began")
    if began is None:
        ctx.num(None, "startup_costs.business_began")
        return None
    if incurred is None or org is None:
        return None
    parts = []
    if cls == DISREGARDED:
        # A disregarded entity is neither a corporation (§248) nor a
        # partnership (§709): its formation costs are start-up costs.
        combined = incurred + org
        parts.append(("§195 start-up (incl. formation costs)", amortize(combined, began,
                                                                       tax_year)))
        if org:
            ctx.findings.append(
                "A disregarded LLC is neither a corporation (§248) nor a partnership "
                "(§709), so its formation costs were added to §195 start-up costs — "
                "one $5,000 allowance, not two.")
    else:
        if incurred:
            parts.append(("§195 start-up", amortize(incurred, began, tax_year)))
        if org:
            parts.append((("§709 organizational" if cls == PARTNERSHIP
                           else "§248 organizational"), amortize(org, began, tax_year)))
    for label, a in parts:
        if a["not_begun"]:
            ctx.findings.append(
                f"{label}: business began {began.isoformat()}, after {tax_year} — "
                "nothing is deductible until the month business begins.")
        elif a["incurred"] > STARTUP_PHASEOUT_START + STARTUP_IMMEDIATE:
            ctx.findings.append(
                f"{label}: costs of ${a['incurred']:,.0f} exceed "
                f"${STARTUP_PHASEOUT_START + STARTUP_IMMEDIATE:,.0f}, so the "
                f"${STARTUP_IMMEDIATE:,.0f} immediate deduction is fully phased out; "
                f"all of it amortizes over {STARTUP_AMORTIZATION_MONTHS} months.")
    deduction = sum(a["immediate"] + a["amortization"] for _, a in parts)
    return {"parts": parts, "deduction": deduction, "began": began}


def _home_office(ctx: _Ctx, llc: dict, cls: str, tentative: float) -> dict | None:
    h = llc.get("home_office")
    if not h:
        return None
    method = h.get("method")
    if method == "simplified":
        sq = ctx.num(h.get("sq_ft"), "home_office.sq_ft", stop=False)
        if sq is None:
            ctx.bounds.append("home_office.sq_ft unknown — no home-office deduction "
                              "taken; net income is an upper bound.")
            return None
        amount = min(sq, SIMPLIFIED_HOME_OFFICE_MAX_SQFT) * SIMPLIFIED_HOME_OFFICE_RATE
    elif method == "actual":
        amount = ctx.num(h.get("amount"), "home_office.amount", stop=False)
        if amount is None:
            ctx.bounds.append("home_office.amount unknown — no home-office deduction "
                              "taken; net income is an upper bound.")
            return None
    else:
        raise LLCReturnError(f"{ctx.name}: home_office.method must be simplified or actual")
    if not amount:
        return None
    if cls != DISREGARDED:
        ctx.findings.append(
            f"Home office of ${amount:,.0f} is not deductible on {FORM[cls]}. "
            + ("A member deducts it as unreimbursed partnership expenses on Schedule "
               "E only if the operating agreement requires the member to bear it."
               if cls == PARTNERSHIP else
               "The S corporation should reimburse the shareholder-employee under "
               "an accountable plan; the reimbursement is then deductible here."))
        return {"method": method, "amount": amount, "allowed": 0.0,
                "carryforward": 0.0, "lost": 0.0}
    allowed = max(0.0, min(amount, tentative))
    excess = amount - allowed
    carry = 0.0 if method == "simplified" else excess
    if excess > 0:
        ctx.findings.append(
            f"Home office: ${excess:,.0f} exceeds the business's income and "
            + ("is lost — the simplified method has no carryforward."
               if method == "simplified" else
               "carries forward on Form 8829 (§280A(c)(5))."))
    return {"method": method, "amount": amount, "allowed": allowed,
            "carryforward": carry, "lost": excess - carry}


def _schedule_c_handoff(name, owner, frac, receipts, cogs, other, exp_rows, meals,
                        depreciation, startup, vehicle, home, sstb, w2_wages, ubia,
                        split) -> dict:
    """Exactly the keys federal_return._schedule_c reads. ``gross_receipts``
    is receipts after returns plus positive other income — never negative;
    COGS and a negative other income travel as expenses, so the net agrees."""
    exp = {k: x * frac for k, _, x in exp_rows}
    if cogs:
        exp["cost_of_goods_sold"] = cogs * frac
    if other < 0:
        exp["other_income_loss"] = -other * frac
    if meals:
        exp["meals_deductible"] = meals * frac
    if depreciation:
        exp["depreciation"] = depreciation * frac
    if startup and startup["deduction"]:
        exp["startup_amortization"] = startup["deduction"] * frac
    return {"owner": owner, "business": name + (f" ({frac:.0%} share)" if split else ""),
            "gross_receipts": (receipts + max(0.0, other)) * frac,
            "expenses": exp, "vehicle": vehicle["amount"] * frac,
            "home_office": (home["amount"] if home else 0.0) * frac,
            "home_office_method": ("simplified" if home and home["method"] == "simplified"
                                   else "regular"),
            "sstb": sstb, "w2_wages": w2_wages * frac,
            "ubia": None if ubia is None else ubia * frac}


def _k1s(ctx, name, cls, owners, net, gp_rows, interest, dividends, dists,
         w2_wages, ubia, sstb, nondeductible):
    out, boxes = [], {}
    form = K1_FORM[cls]
    for o in owners:
        m, s = o["member"], o["share"]
        obi = net * s
        gp = sum(r["amount"] for r in gp_rows if r["member"] == m) if gp_rows else 0.0
        d = None if dists is None else dists.get(m)
        if cls == PARTNERSHIP:
            se = None if o["active"] is None else (obi + gp if o["active"] else gp)
        else:
            se = 0.0
        row = {"owner": m, "entity": name, "form": form,
               "ordinary_business_income": obi, "guaranteed_payments": gp,
               "se_earnings": se, "interest": interest * s, "dividends": dividends * s,
               "distributions": d, "qbi_income": obi, "qbi_w2_wages": w2_wages * s,
               "qbi_ubia": None if ubia is None else ubia * s, "sstb": sstb,
               "material_participation": o["material_participation"]}
        out.append(row)
        if cls == PARTNERSHIP:
            code19 = "19F" if o["active"] else "19A"
            boxes[m] = [
                ("1", "Ordinary business income (loss)", obi),
                ("4a", "Guaranteed payments for services", gp),
                ("4c", "Total guaranteed payments", gp),
                ("5", "Interest income", interest * s),
                ("6a", "Ordinary dividends", dividends * s),
                ("14A", "Net earnings (loss) from self-employment", se),
                ("18C", "Nondeductible expenses", nondeductible * s),
                (code19, "Distributions of cash" + (" — partner providing services"
                                                     if o["active"] else ""), d),
                ("20Z", "§199A: QBI", obi),
                ("20Z", "§199A: W-2 wages", w2_wages * s),
                ("20Z", "§199A: UBIA", row["qbi_ubia"]),
            ]
        else:
            boxes[m] = [
                ("1", "Ordinary business income (loss)", obi),
                ("4", "Interest income", interest * s),
                ("5a", "Ordinary dividends", dividends * s),
                ("16C", "Nondeductible expenses", nondeductible * s),
                ("16D", "Distributions", d),
                ("17V", "§199A: QBI", obi),
                ("17V", "§199A: W-2 wages", w2_wages * s),
                ("17V", "§199A: UBIA", row["qbi_ubia"]),
            ]
    if any(o["material_participation"] is None for o in owners):
        ctx.missing.append("owners[].material_participation (§469; federal-tax-return "
                           "stops without it)")
    if cls == PARTNERSHIP:
        ctx.findings.append(
            "Box 14A treats members marked active as general partners (share of "
            "ordinary income plus guaranteed payments) and others as limited "
            "partners (guaranteed payments only, §1402(a)(13)). For an LLC member "
            "the limited-partner exception is contested (Soroban Capital Partners, "
            "T.C. 2023) — a passive label is not a safe harbor.")
        ctx.findings.append(
            "Box 19: the 2025 Form 1065 instructions split cash distributions into "
            "code A (partners not providing services) and code F (partners providing "
            "services); members marked active are reported under F. Check the code "
            "list on the year's form.")
        if gp_rows:
            ctx.findings.append(
                "Guaranteed payments are deducted at the entity, excluded from QBI "
                "(§199A(c)(4)) and fully subject to SE tax for the recipient; no "
                "tax is withheld, so the member pays estimates.")
    return out, boxes


def _basis(ctx, cls, owners, net, interest, dividends, dists, llc, nondeductible,
           members) -> list:
    """Outside basis (partnership, §705/§704(d)) or stock + debt basis (S corp,
    §1367/§1366(d)): contributions and income, then distributions, then
    nondeductible expenses, then losses (Reg. §1.1367-1(f); §1.704-1(d)(2))."""
    rows = ctx.lst(llc, "owner_basis_start", "owner_basis_start", stop=False)
    known: dict[str, float | None] = {}
    if rows is not None:
        for i, r in enumerate(rows):
            mm = r.get("member") if isinstance(r, dict) else None
            if mm not in members:
                raise LLCReturnError(
                    f"{ctx.name}: owner_basis_start[{i}].member {mm!r} is not an owner")
            known[mm] = ctx.num(r.get("amount"), f"owner_basis_start[{i}].amount",
                                stop=False)
    contrib_rows = _member_amounts(ctx, llc, "contributions", members, stop=False)
    contrib = {m: None if contrib_rows is None else
               (None if any(r["amount"] is None for r in contrib_rows if r["member"] == m)
                else sum(r["amount"] for r in contrib_rows if r["member"] == m))
               for m in members}
    out = []
    for o in owners:
        m, s = o["member"], o["share"]
        obi = net * s
        c = contrib[m]
        income = max(0.0, obi) + (interest + dividends) * s
        nd = nondeductible * s
        loss = max(0.0, -obi)
        d = None if dists is None else dists.get(m)
        start = known.get(m) if m in known else None
        if start is None or c is None:
            row = {"member": m, "start": start, "contributions": c, "income": income,
                   "distributions": d, "nondeductible": nd, "loss": loss,
                   "allowed_loss": None, "suspended": None,
                   "excess_distribution": None, "end": None}
            if loss:
                ctx.bounds.append(
                    f"{m}: loss of ${loss:,.0f} is deductible only up to basis "
                    f"({'§704(d)' if cls == PARTNERSHIP else '§1366(d)'}); basis is "
                    f"not recorded, so between 0 and ${loss:,.0f} is suspended.")
            if d:
                ctx.bounds.append(
                    f"{m}: distributions of ${d:,.0f} with unknown basis — any excess "
                    "over basis is taxable gain "
                    f"({'§731(a)' if cls == PARTNERSHIP else '§1368(b)(2)'}).")
            if (loss or d) and m not in known:
                ctx.missing.append(f"owner_basis_start for {m}")
            out.append(row)
            continue
        after_inc = start + c + income
        dd = d or 0.0
        excess = max(0.0, dd - after_inc)
        after_dist = max(0.0, after_inc - dd)
        after_nd = max(0.0, after_dist - nd)
        allowed = min(loss, after_nd)
        suspended = loss - allowed
        end = after_nd - allowed
        if d is None:
            ctx.bounds.append(f"{m}: distributions unknown — basis check assumes none.")
        if excess:
            ctx.findings.append(
                f"{m}: distributions exceed basis by ${excess:,.0f} — taxable as gain "
                f"({'§731(a)' if cls == PARTNERSHIP else '§1368(b)(2)'}).")
        if suspended:
            ctx.findings.append(
                f"{m}: ${suspended:,.0f} of the ${loss:,.0f} loss exceeds basis and is "
                "suspended until basis is restored; at-risk (§465) and passive "
                "(§469) limits apply after this and are not modelled.")
        out.append({"member": m, "start": start, "contributions": c, "income": income,
                    "distributions": d, "nondeductible": nd, "loss": loss,
                    "allowed_loss": allowed, "suspended": suspended,
                    "excess_distribution": excess, "end": end})
    if cls == S_CORP and any(r["start"] is not None for r in out):
        ctx.findings.append(
            "S-corporation basis here combines stock and debt basis; distributions "
            "reduce only stock basis, so a shareholder with loan basis should split "
            "them (Form 7203). A shareholder may elect to take losses before "
            "nondeductible expenses (Reg. §1.1367-1(g)); not modelled.")
    return out


def _reasonable_comp(ctx, llc, owners, officer_rows, dists, net, payroll_tax,
                     tax_year) -> dict:
    """The IRS position, not a bright line: services by a shareholder-officer
    must be paid as wages before non-wage distributions (Rev. Rul. 74-44;
    Watson v. U.S., 668 F.3d 1008 (8th Cir. 2012); 2025 Form 1120-S
    instructions, line 7)."""
    floor = llc.get("reasonable_salary_floor")
    if floor is not None:
        floor = ctx.num(floor, "reasonable_salary_floor")
    rows = []
    wages_by = {}
    for r in officer_rows:
        wages_by[r["member"]] = wages_by.get(r["member"], 0.0) + (r["amount"] or 0.0)
    status = "no flag"
    for o in owners:
        m = o["member"]
        w = wages_by.get(m, 0.0)
        d = None if dists is None else dists.get(m)
        profit = max(0.0, net * o["share"])
        if o["active"] is False:
            rows.append({"member": m, "wages": w, "distributions": d, "verdict":
                         "not an officer providing services"})
            continue
        if w == 0 and ((d or 0) > 0 or profit > 0):
            verdict, status = "flag", "flag"
            ctx.findings.append(
                f"{m}: no officer wages against ${(d or 0):,.0f} of distributions and "
                f"${profit:,.0f} of profit. The IRS treats payments to a "
                "shareholder-officer who performs services as wages to the extent "
                "of reasonable compensation (Rev. Rul. 74-44; Watson, 8th Cir. "
                "2012) — this is the pattern examined most.")
        elif floor is not None and w < floor:
            verdict, status = "flag", "flag"
            ctx.findings.append(
                f"{m}: officer wages of ${w:,.0f} are below the recorded "
                f"reasonable_salary_floor of ${floor:,.0f}.")
        elif d is not None and w < d:
            verdict = "review"
            if status == "no flag":
                status = "review"
            ctx.findings.append(
                f"{m}: wages of ${w:,.0f} are less than distributions of ${d:,.0f}. "
                "There is no ratio test — the question is what the services would "
                "cost to hire — but this is the shape an examiner looks at. Record "
                "the comparable-pay evidence in reasonable_salary_floor.")
        else:
            verdict = "no flag"
        rows.append({"member": m, "wages": w, "distributions": d, "verdict": verdict})
    if floor is None and status != "no flag":
        ctx.missing.append("reasonable_salary_floor (comparable-pay evidence; asserted, "
                           "never derived)")

    base, _proj = _aid.wage_base_for(tax_year)
    expected = sum(min(r["amount"] or 0.0, base) * EMPLOYER_OASDI_RATE
                   + (r["amount"] or 0.0) * EMPLOYER_MEDICARE_RATE for r in officer_rows)
    if payroll_tax + 0.5 < expected:
        ctx.findings.append(
            f"Employer payroll tax of ${payroll_tax:,.0f} is below the employer FICA "
            f"alone (${expected:,.0f} on the officer wages); FUTA and state "
            "unemployment come on top. Check the payroll reports.")

    # One class of stock (Reg. §1.1361-1(l)(2)): distributions follow shares.
    if dists is not None and len(owners) > 1 and all(v is not None for v in dists.values()):
        total = sum(dists.values())
        if total > 0:
            off = [o["member"] for o in owners
                   if abs(dists[o["member"]] - total * o["share"]) > 1.0]
            if off:
                ctx.findings.append(
                    "Distributions are not in proportion to ownership "
                    f"({', '.join(off)}). Disproportionate distributions can be "
                    "argued to create a second class of stock and end the S "
                    "election (Reg. §1.1361-1(l)(2)); true them up.")
    return {"status": status, "floor": floor, "rows": rows,
            "employer_fica_expected": expected}


def _hobby(ctx: _Ctx, llc: dict, net: float, tax_year: int) -> None:
    if net >= 0:
        return
    hist = llc.get("prior_year_results")
    if not hist:
        ctx.findings.append(
            f"A ${-net:,.0f} loss. If losses recur, §183 can disallow them; the "
            f"profit presumption needs a profit in {HOBBY_PROFIT_YEARS} of "
            f"{HOBBY_WINDOW_YEARS} years. Record prior_year_results to test it.")
        return
    years = {}
    for i, r in enumerate(hist):
        y = r.get("year")
        v = ctx.num(r.get("net"), f"prior_year_results[{i}].net", stop=False,
                    allow_negative=True)
        if y is not None and v is not None and tax_year - HOBBY_WINDOW_YEARS < int(y) < tax_year:
            years[int(y)] = v
    years[tax_year] = net
    profits = sum(1 for v in years.values() if v > 0)
    losses = sum(1 for v in years.values() if v < 0)
    if len(years) >= HOBBY_WINDOW_YEARS and profits < HOBBY_PROFIT_YEARS:
        ctx.findings.append(
            f"Hobby-loss risk: profit in {profits} of the last {HOBBY_WINDOW_YEARS} "
            f"years, so the §183(d) presumption is not available. The losses stand "
            "only on the nine factors of Reg. §1.183-2(b) — keep a business plan "
            "and books that show a profit motive.")
    elif losses >= 2:
        ctx.findings.append(
            f"Losses in {losses} of {len(years)} recorded years. §183(d) presumes a "
            f"profit motive with profits in {HOBBY_PROFIT_YEARS} of "
            f"{HOBBY_WINDOW_YEARS}; on this record that is not yet established.")


def _nec(ctx: _Ctx, llc: dict, table: LLCYear, tax_year: int, state, expenses) -> dict:
    rows = ctx.lst(llc, "contractors", "contractors", stop=False)
    threshold = table.nec_threshold
    out = {"threshold": threshold, "due": due(tax_year + 1, *NEC_DUE), "payees": [],
           "required": 0, "backup_withholding": 0.0, "undetermined": rows is None,
           "de542": []}
    if rows is None:
        ctx.bounds.append("contractors is null — 1099-NEC obligations cannot be "
                          "determined.")
        return out
    labour = sum(float(expenses.get(k) or 0) for k in
                 ("contract_labor", "commissions_and_fees", "legal_and_professional"))
    if not rows and labour >= threshold:
        ctx.findings.append(
            f"${labour:,.0f} of contract labor, commissions or professional fees but "
            "no contractors listed — 1099-NEC obligations cannot be checked.")
    for i, r in enumerate(rows):
        p = f"contractors[{i}]"
        amt = ctx.num(r.get("amount"), f"{p}.amount", stop=False)
        kind = r.get("entity_type")
        attorney = bool(r.get("attorney"))
        w9 = r.get("w9_on_file")
        via = r.get("paid_via")
        if kind is not None and kind not in PAYEE_TYPES:
            raise LLCReturnError(f"{ctx.name}: {p}.entity_type must be one of "
                                 f"{', '.join(PAYEE_TYPES)}")
        row = {"name": r.get("name") or p, "amount": amt, "entity_type": kind,
               "w9_on_file": w9, "attorney": attorney, "required": None,
               "backup": None}
        if via in CARD_PAYMENT_METHODS:
            row["required"] = False
            ctx.findings.append(
                f"{row['name']}: paid by {via.replace('_', ' ')} — reported on Form "
                "1099-K by the processor, not on 1099-NEC (Reg. §1.6041-1(a)(1)(iv)).")
        elif amt is None:
            ctx.bounds.append(f"{row['name']}: amount unknown — 1099-NEC requirement "
                              "undetermined.")
        elif amt >= threshold:
            if kind in EXEMPT_PAYEE_TYPES and not attorney:
                row["required"] = False
            elif kind is None:
                row["required"] = None
                ctx.missing.append(f"{p}.entity_type")
                ctx.findings.append(
                    f"{row['name']}: ${amt:,.0f} paid; a 1099-NEC is required unless "
                    "the payee is a corporation — the W-9 says which.")
            else:
                row["required"] = True
                out["required"] += 1
            if row["required"] is not False and w9 is None:
                ctx.missing.append(f"{p}.w9_on_file")
                ctx.bounds.append(
                    f"{row['name']}: whether a W-9 is on file is not recorded — "
                    f"backup withholding exposure of up to "
                    f"${amt * BACKUP_WITHHOLDING_RATE:,.0f} cannot be ruled out.")
            elif row["required"] is not False and w9 is False:
                bw = amt * BACKUP_WITHHOLDING_RATE
                row["backup"] = bw
                out["backup_withholding"] += bw
                ctx.findings.append(
                    f"{row['name']}: no W-9 on file for ${amt:,.0f} paid — backup "
                    f"withholding of {BACKUP_WITHHOLDING_RATE:.0%} (${bw:,.0f}) "
                    "should have been withheld (§3406). The payer owes it if not; "
                    "get the W-9 now.")
        else:
            row["required"] = False
        if (state == "CA" and amt is not None and amt >= CA_DE542_THRESHOLD
                and via not in CARD_PAYMENT_METHODS):
            if kind in ("individual", "sole_proprietor"):
                out["de542"].append(row["name"])
            elif kind is None:
                out["de542"].append(f"{row['name']} (if an individual — type unknown)")
        out["payees"].append(row)
    return out


def _deadlines(cls, tax_year, n_owners, table, nec):
    y = tax_year + 1
    out = []
    late = None
    if cls == DISREGARDED:
        out.append((due(y, INDIVIDUAL_RETURN_MONTH), "Schedule C with the owner's "
                    "Form 1040 (no federal entity return)"))
    else:
        d = due(y, ENTITY_RETURN_MONTH)
        out.append((d, f"{FORM[cls]} and Schedules K-1 (extension: Form 7004, six "
                       "months)"))
        per = table.late_penalty_per_owner_month
        late = {"small_partnership": cls == PARTNERSHIP
                and n_owners <= SMALL_PARTNERSHIP_MAX_PARTNERS,
                "per_owner_month": per, "owners": n_owners,
                "per_month": per * n_owners,
                "maximum": per * n_owners * LATE_PENALTY_MAX_MONTHS,
                "section": "§6698" if cls == PARTNERSHIP else "§6699"}
    if any(p["required"] is not False for p in nec["payees"]):
        out.append((nec["due"], "Forms 1099-NEC to payees and the IRS"))
    return out, late


def corp_es_installments(tax: float) -> list[float]:
    """Form 100-ES required installments (2026 instructions): the whole tax
    with installment 1 when it is no more than the minimum; otherwise
    cumulative 30/70/70/100% targets, the first at least the minimum."""
    if tax <= CA_MIN_FRANCHISE_TAX:
        return [tax, 0.0, 0.0, 0.0]
    out, prev = [], 0.0
    for i, cum in enumerate(CA_CORP_ES_CUMULATIVE):
        target = min(tax, max(cum * tax, CA_MIN_FRANCHISE_TAX if i == 0 else 0.0))
        target = max(target, prev)
        out.append(target - prev)
        prev = target
    return out


def _california(ctx, llc, cls, tax_year, formed, first_year, gross, returns, other,
                interest, dividends, net, deadlines, name, owners):
    pays = llc.get("estimated_payments", [])
    paid: list | None
    if pays is None:
        paid = None
        ctx.missing.append("estimated_payments (California entity payments)")
    else:
        if not isinstance(pays, list):
            raise LLCReturnError(f"{name}: estimated_payments must be a list")
        paid = [ctx.num(x, f"estimated_payments[{i}]", stop=False) for i, x in enumerate(pays)]
        paid += [0.0] * (4 - len(paid))
        if any(x is None for x in paid):
            ctx.missing.append("estimated_payments (an installment is null)")
            paid = None
    y = tax_year
    if cls == S_CORP:
        ca_income = net + interest + dividends
        on_income = max(0.0, ca_income) * CA_S_CORP_RATE
        tax = max(on_income, CA_MIN_FRANCHISE_TAX)
        note = ("Form 100S. An LLC taxed as a corporation is subject to the "
                "Corporation Tax Law and files Form 100S — not Form 568 — so it "
                "owes no LLC annual tax or LLC fee (2025 Form 568 booklet, \"LLC "
                "Taxed as a Corporation\").")
        if first_year:
            ctx.findings.append(
                "First taxable year: corporations that incorporate or qualify through "
                "the Secretary of State are exempt from the $800 minimum in year one "
                "(R&TC §23153(f)). Whether an LLC electing corporate status qualifies "
                "is not settled here — the $800 minimum is kept, which is the "
                "conservative figure. Confirm with the FTB.")
        ctx.findings.append(
            f"California net income is approximated as ordinary income plus "
            f"interest and dividends (${ca_income:,.0f}); the Form 100S computation "
            "starts from federal income with C-corporation-style California "
            "adjustments (depreciation, state tax) not modelled here.")
        installments = [{"due": due(y, mo), "required": req,
                         "paid": None if paid is None else paid[i]}
                        for i, (req, mo) in enumerate(zip(corp_es_installments(tax),
                                                          CA_CORP_ES_MONTHS))]
        cum_req = cum_paid = 0.0
        short = []
        for inst in installments:
            cum_req += inst["required"]
            if paid is not None:
                cum_paid += inst["paid"]
                if cum_paid + 0.5 < cum_req:
                    short.append(inst["due"].isoformat())
        if short:
            ctx.findings.append(
                "Form 100-ES installments fell short by " + ", ".join(short)
                + " — an underpayment penalty may apply (FTB 5806, not computed; "
                "the prior-year-tax exception is not tested).")
        balance = None if paid is None else tax - sum(paid)
        deadlines.append((due(y + 1, 3), "California Form 100S (franchise tax "
                                         "balance due)"))
        for inst in installments:
            if inst["required"]:
                deadlines.append((inst["due"], f"California Form 100-ES installment "
                                               f"(${inst['required']:,.0f})"))
        return ({"form": "100S", "tax": tax, "on_income": on_income,
                 "minimum": CA_MIN_FRANCHISE_TAX, "ca_income": ca_income,
                 "installments": installments, "paid": None if paid is None else sum(paid),
                 "balance": balance, "note": note, "annual_tax": None, "fee": None,
                 "fee_penalty": None, "total_income": None, "late_per_month": None,
                 "short_year": None}, None)

    # Form 568 (disregarded or partnership)
    n_members = len(owners)
    late_568 = CA_568_LATE_PER_MEMBER_MONTH * n_members
    if cls == PARTNERSHIP:
        ret_due = due(y + 1, CA_PARTNERSHIP_RETURN_MONTH)
        form_note = ("Form 568 with Schedule K-1 (568) per member, due the 15th day "
                     "of the 3rd month. Nonresident members need Form 3832 consents "
                     "or withholding (not modelled).")
    else:
        ret_due = due(y + 1, CA_SMLLC_RETURN_MONTH)
        form_note = ("Form 568 filed with the owner's return, due the 15th day of the "
                     "4th month after the owner's year ends.")
    form_note += (f" Filing it late costs ${CA_568_LATE_PER_MEMBER_MONTH:,.0f} × "
                  f"{n_members} member(s) = ${late_568:,.0f} per month, up to 12 months "
                  "(Form 568 booklet, General Information G).")

    # R&TC §17946: a taxable year of 15 days or less with no California business.
    short_year = None
    if first_year and formed is not None:
        days = (_dt.date(y, 12, 31) - formed).days + 1
        if days <= CA_SHORT_YEAR_DAYS:
            did = llc.get("did_business_in_short_year")
            if did is False:
                ctx.findings.append(
                    f"First taxable year is {days} days and no business was done in "
                    "California: no Form 568, annual tax or fee for it (R&TC §17946). "
                    f"The first $800 is the {y + 1} tax.")
                deadlines.append((due(y + 1, 4),
                                  f"California $800 annual tax (FTB 3522) for {y + 1}"))
                return ({"form": "568", "annual_tax": 0.0, "annual_due": None,
                         "total_income": 0.0, "fee": 0.0, "fee_due": None,
                         "fee_paid": None, "fee_penalty": None, "return_due": None,
                         "paid": None if paid is None else sum(paid),
                         "balance": None if paid is None else -sum(paid),
                         "note": "No Form 568 for this short year (R&TC §17946).",
                         "tax": None, "late_per_month": None, "short_year": days},
                        None)
            short_year = days
            if did is None:
                ctx.missing.append("did_business_in_short_year (decides the R&TC "
                                   "§17946 15-day exemption)")
                ctx.bounds.append(
                    f"The first taxable year is {days} days: if no business was done "
                    "in California in it, no return, $800 or fee is owed for it (R&TC "
                    "§17946). The $800 is shown as owed — an upper bound.")

    total_income = (gross - returns) + other + interest + dividends
    fee = _ca.llc_fee(total_income)
    annual = CA_LLC_ANNUAL_TAX
    annual_due = due(y, 4)
    if first_year and formed is not None:
        if formed.year in CA_LLC_FIRST_YEAR_EXEMPT_YEARS:
            annual, annual_due = 0.0, None
        else:
            d = _ca._add_months(formed, 4)
            annual_due = due(d.year, d.month)
            ctx.findings.append(
                f"First year: the 2021–2023 first-year exemption has expired, so the "
                f"$800 is owed for {tax_year}, due {annual_due.isoformat()} (15th day "
                "of the 4th month after formation).")
    elif formed is None:
        ctx.findings.append("formed_on is not recorded — the first-year annual-tax "
                            "due date cannot be dated.")

    # FTB 3536: the 15th day of the 6th month of the LLC's taxable year, counting
    # the formation month; none if the year ends first (Form 568 booklet).
    if first_year and formed is not None:
        d6 = _ca._add_months(formed, CA_LLC_FEE_ESTIMATE_MONTH)
        fee_due = None if d6.year > y else due(d6.year, d6.month)
    else:
        fee_due = due(y, CA_LLC_FEE_ESTIMATE_MONTH)
    fee_paid = None if paid is None else paid[1]
    prior_fee = llc.get("prior_year_fee")
    if prior_fee is not None:
        prior_fee = ctx.num(prior_fee, "prior_year_fee")
    fee_penalty = None
    if fee_due is None:
        fee_penalty = 0.0
        if fee:
            ctx.findings.append(
                "The first taxable year ends before the 15th day of its 6th month: no "
                "estimated fee is due; the whole fee is paid with Form 568.")
    elif fee_paid is not None:
        fee_penalty = max(0.0, fee - fee_paid) * CA_FEE_UNDERPAYMENT_PENALTY
        if fee_penalty and prior_fee is not None and fee_paid >= prior_fee:
            fee_penalty = 0.0
            ctx.findings.append(
                f"The ${fee_paid:,.0f} estimate covers last year's ${prior_fee:,.0f} "
                "fee, so the 10% underpayment penalty does not apply (Form 568 "
                "booklet, General Information G).")
        elif fee_penalty:
            safe = ("there is no preceding year, so the prior-year safe harbor is "
                    "unavailable" if first_year else
                    "last year's fee is not recorded (prior_year_fee); if the "
                    "estimate covered it there is no penalty, so this is an upper "
                    "bound" if prior_fee is None else
                    f"the estimate is under last year's ${prior_fee:,.0f} fee too")
            ctx.findings.append(
                f"LLC fee of ${fee:,.0f} against a timely estimate of ${fee_paid:,.0f}: "
                f"the 10% penalty on the shortfall is ${fee_penalty:,.0f} (FTB 3536 was "
                f"due {fee_due.isoformat()}) — {safe}.")
            if prior_fee is None and not first_year:
                ctx.missing.append("prior_year_fee (the 10% penalty safe harbor)")
    if annual_due:
        deadlines.append((annual_due, f"California $800 annual tax (FTB 3522) for {y}"))
    if fee and fee_due:
        deadlines.append((fee_due, f"California LLC fee estimate (FTB 3536), ${fee:,.0f}"))
    deadlines.append((ret_due, "California Form 568 (LLC fee balance with FTB 3536)"))
    deadlines.append((due(y + 1, 4), f"California $800 annual tax (FTB 3522) for {y + 1}"))
    owed = annual + fee
    balance = None if paid is None else owed - sum(paid)
    ca_llc = None
    if cls == DISREGARDED:
        ca_llc = {"name": name, "gross_receipts_total_income": total_income,
                  "formed_year": formed.year if formed else None,
                  "formed_on": formed.isoformat() if formed else None}
    return ({"form": "568", "annual_tax": annual, "annual_due": annual_due,
             "total_income": total_income, "fee": fee, "fee_due": fee_due,
             "fee_paid": fee_paid, "fee_penalty": fee_penalty, "return_due": ret_due,
             "paid": None if paid is None else sum(paid), "balance": balance,
             "note": form_note, "tax": None, "late_per_month": late_568,
             "short_year": short_year, "prior_year_fee": prior_fee}, ca_llc)
