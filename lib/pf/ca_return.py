"""California resident income tax return (Form 540 + Schedule CA) workpaper.

The one idea: **California starts from federal AGI and then disagrees with it
in a short, enumerable list of places.** A CA return is wrong in practice not
because the rate schedule was misread but because one of those disagreements
was missed — HSA contributions California never recognised, Treasury interest
it may not tax, a mortgage cap it never lowered, a SALT cap it never adopted,
SDI that is not a payment, a Behavioral Health Services Tax that does not
double for joint filers. This module takes federal figures as given, applies
each disagreement as a named Schedule CA line, and carries the result through
Form 540 to a refund or balance due, the next year's 30/40/0/30 estimated
payments, and any single-member LLC's $800 tax and fee.

It prepares and checks; it does not e-file, and it never treats an unknown as
zero. A ``null`` figure goes to ``missing`` and the finding says which way the
result is biased.

Basis: nominal dollars of ``tax_year``, whole dollars as on the form.

Refuses (``CAReturnError``): part-year and nonresident returns (Form 540NR);
the other-state tax credit (Schedule S); kiddie tax (FTB 3800 / FTB 3803);
rental, passive, and K-1 income (FTB 3801); a taxpayer who can be claimed as
someone else's dependent; registered domestic partners filing differently from
federal; and tax years before the earliest shipped table. CA alternative
minimum tax (Schedule P) is flagged, not computed.
"""
from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass, field
from typing import Any

from .cashflow import (
    CashFlowError,
    ItemizedDeductionInputs,
    StateItemizedDeductionRules,
    progressive_tax,
    state_itemized_deduction,
)


class CAReturnError(ValueError):
    """The inputs cannot support a California return without guessing, or the
    return is outside what this module prepares."""


FILING_STATUSES = ("single", "mfj", "mfs", "hoh", "qss")

#: Transcribed from the cited FTB publications; marked unverified until a
#: human checks them against the source, per the repository's provenance policy.
CA_VERIFIED = "unverified"

# ── Statutory rules that do not change annually ─────────────────────────

#: R&TC §17043 (Prop. 63, renamed by Prop. 1 of 2024): 1% on taxable income
#: over $1,000,000. Form 540 line 62 instructions — the threshold is the same
#: for every filing status; there is no joint-return doubling.
BHST_THRESHOLD = 1_000_000.0
BHST_RATE = 0.01
#: Schedule CA (540) Part II line 1-4: CA follows the federal 7.5%-of-AGI
#: medical floor, measured against federal AGI (Form 540 line 13).
MEDICAL_AGI_FLOOR = 0.075
#: Schedule CA (540) Part II line 8: CA never adopted the TCJA $750,000 cap;
#: acquisition debt limit stays $1,000,000 ($500,000 MFS).
MORTGAGE_DEBT_LIMIT = {"mfs": 500_000.0}
MORTGAGE_DEBT_LIMIT_DEFAULT = 1_000_000.0
#: Schedule CA (540) Part II line 11-12: CA limits charitable contributions
#: to 50% of federal AGI.
CHARITABLE_AGI_LIMIT = 0.50
#: Schedule CA (540) Part II line 19-21: CA did not suspend miscellaneous
#: itemized deductions; they are allowed above 2% of federal AGI.
MISC_ITEMIZED_AGI_FLOOR = 0.02
#: Schedule CA (540) line 29 Itemized Deductions Worksheet: reduction is 6%
#: of federal AGI over the threshold, capped at 80% of itemized deductions
#: other than medical, investment interest, casualty and gambling losses.
ITEMIZED_PHASEOUT_RATE = 0.06
ITEMIZED_PHASEOUT_MAX_SHARE = 0.80
#: Form 540 line 32 AGI Limitation Worksheet: each exemption credit falls by
#: $6 for each $2,500 ($1,250 MFS), or part of it, of federal AGI over the
#: threshold.
EXEMPTION_PHASEOUT_STEP = 2_500.0
EXEMPTION_PHASEOUT_STEP_MFS = 1_250.0
EXEMPTION_PHASEOUT_PER_STEP = 6.0
#: Form 540 line 9: senior exemption if 65 or older by December 31.
SENIOR_AGE = 65
#: IRC §1211(b) as adopted by R&TC §18151: net capital loss deduction limit.
CAPITAL_LOSS_LIMIT = 3_000.0
CAPITAL_LOSS_LIMIT_MFS = 1_500.0

# ── Estimated tax (R&TC §19136, §19136.3; Form 540-ES instructions) ──────

#: R&TC §19136.1: installments are 30%, 40%, 0%, 30% of the required annual
#: payment (2026 Form 540-ES instructions, General Information).
ES_INSTALLMENT_SHARES = (0.30, 0.40, 0.0, 0.30)
#: Form 540-ES Section B / FTB 5805: current-year safe harbor is 90%.
ES_CURRENT_YEAR_SHARE = 0.90
#: Form 540-ES Section C: prior-year safe harbor is 100%, or 110% when prior
#: California AGI exceeded $150,000 ($75,000 MFS).
ES_PRIOR_YEAR_SHARE = 1.00
ES_PRIOR_YEAR_SHARE_HIGH = 1.10
ES_HIGH_INCOME_AGI = 150_000.0
ES_HIGH_INCOME_AGI_MFS = 75_000.0
#: R&TC §19136.3, Form 540-ES Section C: California AGI of $1,000,000 or
#: more ($500,000 MFS) removes the prior-year safe harbor entirely.
ES_NO_PRIOR_YEAR_AGI = 1_000_000.0
ES_NO_PRIOR_YEAR_AGI_MFS = 500_000.0
#: Form 540-ES Section B / FTB 5805 Part II line 4: no estimates are required
#: if tax after withholding and credits is under $500 ($250 MFS).
ES_MIN_BALANCE = 500.0
ES_MIN_BALANCE_MFS = 250.0
#: Form 540-ES Section D due dates as (month offset from the tax year, month,
#: day): April 15, June 15, September 15, and January 15 of the next year.
#: The next business day applies when a date falls on a weekend or holiday;
#: that adjustment is not computed.
ES_DUE_DATES = ((0, 4, 15), (0, 6, 15), (0, 9, 15), (1, 1, 15))

# ── LLC tax and fee (R&TC §17941, §17942; 2025 Form 568 booklet) ─────────

#: R&TC §17941: $800 annual tax on every LLC doing business in or organised
#: or registered in California, due the 15th day of the 4th month of its
#: taxable year (form FTB 3522).
LLC_ANNUAL_TAX = 800.0
#: R&TC §17941(g) (AB 85, 2020): no first-year annual tax for LLCs that
#: organised or registered in taxable years beginning on or after
#: 2021-01-01 and before 2024-01-01 (ftb.ca.gov LLC page, "Exceptions to the
#: first year annual tax"). Expired: formations from 2024 owe the first year.
LLC_FIRST_YEAR_EXEMPT_YEARS = range(2021, 2024)
#: R&TC §17942 / 2025 Form 568 booklet, General Information F: fee by total
#: California income, as (at least, fee). Below $250,000 there is no fee.
LLC_FEE_TIERS = ((5_000_000.0, 11_790.0), (1_000_000.0, 6_000.0),
                 (500_000.0, 2_500.0), (250_000.0, 900.0))
#: Form 568 booklet: the estimated fee (FTB 3536) is due the 15th day of the
#: 6th month; Form 568 for a disregarded SMLLC owned by an individual is due
#: the 15th day of the 4th month after the owner's year ends.
LLC_FEE_ESTIMATE_MONTH = 6
LLC_RETURN_MONTH = 4


#: Label of the renter's credit in ``CAReturn.credits``.
RENTERS_CREDIT_NAME = "Nonrefundable renter's credit"


@dataclass(frozen=True)
class CAYear:
    """Annually indexed California tables for one tax year."""
    tax_year: int
    source: str
    verified_on: str
    #: (rate, upper bound or None), per R&TC §17041 as indexed by §17041(h).
    brackets: dict[str, tuple[tuple[float, float | None], ...]]
    standard_deduction: dict[str, float]
    personal_exemption: float
    blind_exemption: float
    senior_exemption: float
    dependent_exemption: float
    #: Federal AGI above which exemption credits and itemized deductions are
    #: limited (R&TC §17054.1, §17077).
    agi_limit: dict[str, float]
    #: Renter's credit: (California AGI ceiling, credit) — R&TC §17053.5.
    renters: dict[str, tuple[float, float]]
    #: Form 540 line 61: total income above which AMT may apply (screen only).
    amt_screen: dict[str, float]


_SINGLE = ((0.01, 11_079.0), (0.02, 26_264.0), (0.04, 41_452.0),
           (0.06, 57_542.0), (0.08, 72_724.0), (0.093, 371_479.0),
           (0.103, 445_771.0), (0.113, 742_953.0), (0.123, None))
_JOINT = ((0.01, 22_158.0), (0.02, 52_528.0), (0.04, 82_904.0),
          (0.06, 115_084.0), (0.08, 145_448.0), (0.093, 742_958.0),
          (0.103, 891_542.0), (0.113, 1_485_906.0), (0.123, None))
_HOH = ((0.01, 22_173.0), (0.02, 52_530.0), (0.04, 67_716.0),
        (0.06, 83_805.0), (0.08, 98_990.0), (0.093, 505_208.0),
        (0.103, 606_251.0), (0.113, 1_010_417.0), (0.123, None))

CA_TABLES: dict[int, CAYear] = {
    2025: CAYear(
        tax_year=2025,
        source="FTB 2025 California Tax Rate Schedules; 2025 Form 540 and "
               "540 Booklet (lines 18, 32, 46, 61, 62); 2025 Schedule CA "
               "(540) instructions (line 29); ftb.ca.gov Nonrefundable "
               "renter's credit page (updated 2026-02-20)",
        verified_on=CA_VERIFIED,
        brackets={"single": _SINGLE, "mfs": _SINGLE, "mfj": _JOINT,
                  "qss": _JOINT, "hoh": _HOH},
        standard_deduction={"single": 5_706.0, "mfs": 5_706.0,
                            "mfj": 11_412.0, "qss": 11_412.0, "hoh": 11_412.0},
        personal_exemption=153.0,
        blind_exemption=153.0,
        senior_exemption=153.0,
        dependent_exemption=475.0,
        agi_limit={"single": 252_203.0, "mfs": 252_203.0, "mfj": 504_411.0,
                   "qss": 504_411.0, "hoh": 378_310.0},
        renters={"single": (53_994.0, 60.0), "mfs": (53_994.0, 60.0),
                 "mfj": (107_987.0, 120.0), "qss": (107_987.0, 120.0),
                 "hoh": (107_987.0, 120.0)},
        amt_screen={"single": 92_749.0, "hoh": 92_749.0, "mfs": 61_830.0,
                    "mfj": 123_667.0, "qss": 123_667.0},
    ),
}


def table_for(tax_year: int) -> tuple[CAYear, bool]:
    """The table for ``tax_year``, or the latest shipped table and True when
    the year's indexed amounts are not yet published (a projection).

    Earlier years are refused: before 2024 an SDI wage cap made excess SDI a
    creditable payment, which this module does not model."""
    if tax_year in CA_TABLES:
        return CA_TABLES[tax_year], False
    if tax_year < min(CA_TABLES):
        raise CAReturnError(
            f"no California tables for {tax_year}; the earliest shipped year "
            f"is {min(CA_TABLES)}")
    return CA_TABLES[max(CA_TABLES)], True


# ── Inputs from the federal return ──────────────────────────────────────

@dataclass(frozen=True)
class FederalInputs:
    """The subset of the federal return California starts from.

    ``None`` means the federal figure is unknown, which is different from 0.
    """
    tax_year: int
    filing_status: str
    agi: float | None
    us_treasury_interest: float | None
    tax_exempt_interest: float | None
    net_capital_gain_or_loss: float | None
    hsa_deduction: float = 0.0
    half_se_tax: float = 0.0
    taxable_social_security: float = 0.0
    state_refund_taxable: float = 0.0
    federal_amt: float | None = None


def from_federal(fr: Any) -> FederalInputs:
    """Adapter from ``pf.federal_return.FederalReturn`` by attribute name, so
    this module does not import the federal one."""
    adj = getattr(fr, "adjustments", None) or {}
    return FederalInputs(
        tax_year=int(getattr(fr, "tax_year")),
        filing_status=str(getattr(fr, "filing_status")),
        agi=getattr(fr, "agi", None),
        us_treasury_interest=getattr(fr, "us_treasury_interest", None),
        tax_exempt_interest=getattr(fr, "tax_exempt_interest", None),
        net_capital_gain_or_loss=getattr(fr, "net_capital_gain_or_loss", None),
        hsa_deduction=float(adj.get("hsa_deduction", adj.get("hsa")) or 0.0),
        half_se_tax=float(adj.get("half_se_tax") or 0.0),
        taxable_social_security=float(
            getattr(fr, "taxable_social_security", 0.0) or 0.0),
        state_refund_taxable=float(getattr(fr, "state_refund_taxable", 0.0) or 0.0),
        federal_amt=getattr(fr, "amt", None),
    )


# ── Results ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Adjustment:
    """One Schedule CA (540) Part I line: a subtraction (column B) or an
    addition (column C) to federal income."""
    line: str
    description: str
    subtraction: float = 0.0
    addition: float = 0.0


@dataclass(frozen=True)
class Installment:
    number: int
    due: _dt.date
    share: float
    amount: float


@dataclass(frozen=True)
class LLCObligation:
    name: str
    total_income: float | None
    annual_tax: float
    annual_tax_due: _dt.date | None
    fee: float | None
    fee_estimate_due: _dt.date
    return_due: _dt.date
    note: str


@dataclass
class CAReturn:
    tax_year: int
    filing_status: str
    projection: bool
    table_year: int
    # Form 540
    federal_agi: float                       # line 13
    adjustments: list[Adjustment]
    subtractions: float                      # line 14
    additions: float                         # line 16
    ca_agi: float                            # line 17
    standard_deduction: float
    itemized_deduction: float | None         # Schedule CA Part II line 29
    itemized_before_limit: float | None
    deduction: float                         # line 18
    deduction_kind: str                      # "standard" | "itemized"
    taxable_income: float                    # line 19
    tax: float                               # line 31
    exemption_counts: dict[str, int]
    exemption_before_limit: float
    exemption_credits: float                 # line 32
    tax_after_exemptions: float              # line 35
    credits: list[tuple[str, float]]         # lines 40-46, allowed amounts
    total_credits: float                     # line 47
    tax_after_credits: float                 # line 48
    bhst: float                              # line 62
    other_taxes: float                       # line 63
    total_tax: float                         # line 64
    withholding: float                       # line 71
    estimated_payments: float                # line 72
    other_withholding: float                 # line 73
    total_payments: float                    # line 78
    use_tax: float | None                    # line 91
    refund: float                            # line 97 (0 if a balance is due)
    balance_due: float                       # line 100
    # Estimated tax
    underpayment_required_annual: float | None
    underpayment_shortfalls: list[float]
    next_year_required_annual: float | None
    next_year_installments: list[Installment]
    llcs: list[LLCObligation]
    findings: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.missing


# ── Helpers ─────────────────────────────────────────────────────────────

def _whole(x: float) -> float:
    """Round to whole dollars, half up, as the form instructs."""
    return float(math.floor(x + 0.5)) if x >= 0 else -float(math.floor(-x + 0.5))


def _num(value: Any, label: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as e:
        raise CAReturnError(f"{label} must be numeric, got {value!r}") from e


def _date(year: int, month: int, day: int) -> _dt.date:
    return _dt.date(year, month, day)


def _add_months(d: _dt.date, months: int) -> _dt.date:
    """The 15th day of the month ``months`` after ``d``'s month, counting
    ``d``'s month as the first (the FTB "15th day of the 4th month")."""
    m = d.month - 1 + months - 1
    return _dt.date(d.year + m // 12, m % 12 + 1, 15)


def _state(w: dict) -> str | None:
    """A W-2's state code, upper-cased; ``None`` when not recorded."""
    st = w.get("state")
    return None if st is None else str(st).strip().upper()


def _refuse_out_of_scope(tr: dict, ca: dict) -> None:
    state = tr.get("state")
    if state is not None and str(state).upper() != "CA":
        raise CAReturnError(
            f"tax_return.state is {state!r}; this module prepares only a "
            "California resident return")
    residency = ca.get("residency")
    if residency not in (None, "resident", "full_year"):
        raise CAReturnError(
            f"residency {residency!r}: part-year and nonresident returns use "
            "Form 540NR, which this module does not prepare")
    if (ca.get("other_state_tax_paid") or 0) > 0 or any(
            _state(w) not in (None, "CA") and (w.get("state_withheld") or 0) > 0
            for w in tr.get("w2") or []):
        raise CAReturnError(
            "tax paid to another state: the other-state tax credit "
            "(Schedule S) is not modelled")
    if ca.get("ftb3800") or ca.get("ftb3803"):
        raise CAReturnError(
            "kiddie tax (FTB 3800 / FTB 3803) is not modelled; prepare the "
            "child's tax separately")
    foreign = tr.get("foreign")
    if isinstance(foreign, dict) and (foreign.get("rent") or 0):
        raise CAReturnError(
            "tax_return.foreign.rent is present: rental income (Schedule CA "
            "Section A line 5, CA depreciation) is not modelled")
    for key in ("rental", "schedule_e", "k1", "passive"):
        if tr.get(key):
            raise CAReturnError(
                f"tax_return.{key} is present: rental, passive and K-1 income "
                "(Schedule CA Section A line 5; FTB 3801 for passive "
                "activities) are not modelled")
    for t in tr.get("taxpayers") or []:
        if t.get("can_be_claimed_as_dependent"):
            raise CAReturnError(
                "a taxpayer can be claimed as someone else's dependent; the "
                "dependent standard deduction worksheet is not modelled")
    if ca.get("rdp"):
        raise CAReturnError(
            "registered domestic partners recompute federal AGI on a pro forma "
            "return (FTB Pub. 737); not modelled")


def _status_threshold(status: str, normal: float, mfs: float) -> float:
    return mfs if status == "mfs" else normal


# ── Schedule CA Part I ──────────────────────────────────────────────────

def schedule_ca_adjustments(tr: dict, fed: FederalInputs, missing: list[str],
                            findings: list[str]) -> list[Adjustment]:
    """Schedule CA (540) Part I lines, from federal AGI to California AGI."""
    ca = tr.get("ca") or {}
    adj: list[Adjustment] = []
    status = fed.filing_status

    # Line 2: U.S. Treasury interest is exempt from state tax (31 U.S.C. §3124).
    treasury = fed.us_treasury_interest
    if treasury is None:
        missing.append("federal us_treasury_interest — California AGI may be "
                       "overstated by any Treasury interest")
    elif treasury:
        adj.append(Adjustment("2", "U.S. Treasury interest (exempt from state tax)",
                              subtraction=float(treasury)))

    # Line 2: tax-exempt interest from another state's bonds is taxable in CA.
    # ``tax_exempt`` is the dollar amount of 1099-INT box 8 (shared schema);
    # ``amount`` (box 1) is already in federal AGI and is not touched here.
    non_ca_muni = 0.0
    for i, it in enumerate(tr.get("interest") or []):
        raw = it.get("tax_exempt")
        if isinstance(raw, bool):
            raise CAReturnError(
                f"tax_return.interest[{i}].tax_exempt is {raw!r}; it is the "
                "dollar amount of federally tax-exempt interest (1099-INT box 8)")
        amount = _num(raw, f"tax_return.interest[{i}].tax_exempt")
        if amount is None:
            if "tax_exempt" in it:
                missing.append(f"tax_return.interest[{i}].tax_exempt")
            continue
        if amount <= 0:
            continue
        flag = it.get("ca_exempt")
        if flag is None:
            missing.append(
                f"tax_return.interest[{i}].ca_exempt — whether federally "
                "tax-exempt interest is California (or qualifying fund) "
                "interest; if not, California taxes it")
        elif not flag:
            non_ca_muni += amount
    if non_ca_muni:
        adj.append(Adjustment("2", "Non-California municipal interest "
                              "(federally exempt, CA taxable)",
                              addition=non_ca_muni))

    # Line 3: dividends from funds holding U.S. obligations are exempt in CA
    # to the extent the fund reports them (R&TC §17145; Schedule CA line 3).
    usd = _num(ca.get("us_obligation_dividends"), "tax_return.ca.us_obligation_dividends")
    if usd:
        adj.append(Adjustment("3", "Dividends from U.S.-obligation funds "
                              "(exempt in CA)", subtraction=usd))

    # Line 1h / 13 / 8f: California does not recognise HSAs.
    # Employer (and payroll cafeteria-plan) contributions: W-2 box 12 W when
    # any W-2 records it, else ``hsa.employer_contributions``.
    hsa = tr.get("hsa") or {}
    box_w: float | None = None
    box_w_unknown = False
    for i, w in enumerate(tr.get("w2") or []):
        b12 = w.get("box12") or {}
        if "W" not in b12:
            continue
        v = _num(b12.get("W"), f"tax_return.w2[{i}].box12.W")
        if v is None:
            box_w_unknown = True
            missing.append(f"tax_return.w2[{i}].box12.W")
            continue
        box_w = (box_w or 0.0) + v
    hsa_employer = _num(hsa.get("employer_contributions"),
                        "tax_return.hsa.employer_contributions")
    if box_w is not None:
        employer, source = box_w, "W-2 box 12 W"
        if hsa_employer is not None and abs(hsa_employer - box_w) > 1:
            findings.append(
                f"HSA employer contributions disagree: W-2 box 12 W "
                f"{box_w:,.0f} vs hsa.employer_contributions "
                f"{hsa_employer:,.0f}. Box 12 W is used; check which is right.")
    elif hsa_employer is not None:
        employer, source = hsa_employer, "hsa.employer_contributions"
    else:
        employer, source = 0.0, ""
        if hsa and not box_w_unknown:
            missing.append(
                "tax_return.hsa.employer_contributions (or W-2 box 12 W) — "
                "employer HSA contributions are CA income; California AGI is "
                "a lower bound without them")
    if employer:
        adj.append(Adjustment("1h", f"Employer and payroll HSA contributions "
                              f"({source}) — CA does not recognise HSAs",
                              addition=employer))
    if fed.hsa_deduction:
        adj.append(Adjustment("13", "HSA deduction (federal Schedule 1) — no "
                              "CA conformity", addition=fed.hsa_deduction))
    hsa_open = bool(hsa) or employer > 0 or fed.hsa_deduction > 0
    if hsa_open:
        earnings = _num(ca.get("hsa_earnings"), "tax_return.ca.hsa_earnings")
        if earnings is None:
            missing.append("tax_return.ca.hsa_earnings — HSA interest, "
                           "dividends and gains are taxable in CA each year; "
                           "California AGI is a lower bound without them")
        elif earnings:
            adj.append(Adjustment("2/3/7", "HSA interest, dividends and gains "
                                  "taxable in CA in the year earned",
                                  addition=earnings))
        dist = _num(hsa.get("distributions"), "tax_return.hsa.distributions")
        qual = _num(hsa.get("qualified_expenses"), "tax_return.hsa.qualified_expenses")
        if dist and qual is None:
            missing.append("tax_return.hsa.qualified_expenses")
        elif dist:
            nonqualified = max(0.0, dist - qual)
            if nonqualified:
                adj.append(Adjustment(
                    "8f", "HSA distribution not used for medical expenses "
                    "(federally taxable; CA already taxed the contributions)",
                    subtraction=nonqualified))

    # Line 1 (Form 1040 line 1): a taxable state income tax refund.
    if fed.state_refund_taxable:
        adj.append(Adjustment("B1", "State income tax refund — not taxable in CA",
                              subtraction=fed.state_refund_taxable))

    # Line 6: Social Security benefits are not taxed by California.
    if fed.taxable_social_security:
        adj.append(Adjustment("6", "Taxable Social Security benefits — not "
                              "taxed by CA", subtraction=fed.taxable_social_security))

    # Line 7: capital loss carryover can differ from federal.
    cap = _capital_adjustment(tr, fed, ca, missing, findings)
    if cap:
        adj.append(cap)

    # Line 3 / 12: depreciation (CA does not conform to bonus depreciation
    # and has its own §179 limit — FTB 3885A).
    dep_override = ca.get("depreciation_adjustment")
    has_dep = any(
        ((sc.get("expenses") or {}).get(k) or 0) > 0
        for sc in tr.get("schedule_c") or []
        for k in ("depreciation", "section_179", "bonus_depreciation"))
    if dep_override is not None:
        v = float(dep_override)
        if v:
            adj.append(Adjustment(
                "3", "Depreciation difference (FTB 3885A: no CA bonus "
                "depreciation, lower §179 limit)",
                addition=max(v, 0.0), subtraction=max(-v, 0.0)))
    elif has_dep:
        missing.append(
            "tax_return.ca.depreciation_adjustment — Schedule C claims "
            "depreciation; CA disallows bonus depreciation and limits §179 "
            "(FTB 3885A). California AGI is a lower bound until it is supplied")

    other = ca.get("other_adjustments") or []
    for i, o in enumerate(other):
        amt = _num(o.get("amount"), f"tax_return.ca.other_adjustments[{i}].amount")
        if amt is None:
            missing.append(f"tax_return.ca.other_adjustments[{i}].amount")
            continue
        adj.append(Adjustment(str(o.get("line", "")), str(o.get("description", "other")),
                              addition=max(amt, 0.0), subtraction=max(-amt, 0.0)))
    return adj


def _capital_adjustment(tr: dict, fed: FederalInputs, ca: dict,
                        missing: list[str], findings: list[str]) -> Adjustment | None:
    carry = ca.get("ca_capital_loss_carryover")
    if carry is None:
        if (tr.get("capital_loss_carryover") or {}):
            findings.append(
                "California capital-loss carryover not recorded: assumed equal "
                "to the federal carryover. It differs where an earlier year had "
                "a CA basis difference — check the prior-year Schedule D (540).")
        return None
    if isinstance(carry, dict):
        parts = [carry.get("short"), carry.get("long")]
        if any(p is None for p in parts):
            missing.append("tax_return.ca.ca_capital_loss_carryover.short/long")
            return None
        carry_total = abs(float(parts[0])) + abs(float(parts[1]))
    else:
        carry_total = abs(float(carry))
    if fed.net_capital_gain_or_loss is None:
        missing.append("federal net_capital_gain_or_loss")
        return None
    net = 0.0
    # Foreign sales are in federal net capital gain too (federal_return routes
    # foreign.capital_transactions there), so they belong in the CA recompute.
    foreign = (tr.get("foreign") or {}) if isinstance(tr.get("foreign"), dict) else {}
    rows = [("capital_transactions", i, t)
            for i, t in enumerate(tr.get("capital_transactions") or [])]
    rows += [("foreign.capital_transactions", i, t)
             for i, t in enumerate(foreign.get("capital_transactions") or [])]
    for where, i, t in rows:
        p = _num(t.get("proceeds"), f"tax_return.{where}[{i}].proceeds")
        b = _num(t.get("basis"), f"tax_return.{where}[{i}].basis")
        if p is None or b is None:
            missing.append(f"tax_return.{where}[{i}].proceeds/basis")
            return None
        net += p - b + float(t.get("wash_sale_disallowed") or 0.0)
    for d in tr.get("dividends") or []:
        net += float(d.get("capital_gain_distributions") or 0.0)
    net -= carry_total
    limit = CAPITAL_LOSS_LIMIT_MFS if fed.filing_status == "mfs" else CAPITAL_LOSS_LIMIT
    ca_amount = max(net, -limit)
    diff = _whole(ca_amount - fed.net_capital_gain_or_loss)
    if not diff:
        return None
    findings.append(
        f"CA capital gain/loss is {ca_amount:,.0f} against federal "
        f"{fed.net_capital_gain_or_loss:,.0f} because the CA carryover "
        f"({carry_total:,.0f}) differs; CA carries forward "
        f"{max(0.0, -net - limit):,.0f} on Schedule D (540).")
    return Adjustment("7", "Capital gain/loss with the California carryover",
                      addition=max(diff, 0.0), subtraction=max(-diff, 0.0))


# ── Deduction ───────────────────────────────────────────────────────────

def ca_itemized(tr: dict, federal_agi: float, table: CAYear, status: str,
                missing: list[str], findings: list[str]) -> tuple[float | None, float | None]:
    """(allowed, before limitation). ``None`` when any recorded item is null.

    Reuses ``cashflow.state_itemized_deduction``: no CA income tax or SDI, no
    SALT cap, $1M mortgage limit, 7.5% medical floor, and the 6%/80%
    limitation above the federal-AGI threshold."""
    it = tr.get("itemized")
    if not it:
        return None, None
    hsa = tr.get("hsa") or {}
    vals: dict[str, float] = {}
    unknown = False
    for key in ("medical", "property_tax", "other_state_local_taxes",
                "mortgage_interest", "charitable_cash", "charitable_noncash"):
        if key in it and it[key] is None:
            missing.append(f"tax_return.itemized.{key}")
            unknown = True
        vals[key] = float(it.get(key) or 0.0)
    if unknown:
        return None, None
    # Schedule CA Part II line 4 col C: medical paid by tax-free HSA
    # distributions is deductible in CA.
    hsa_medical = 0.0
    if hsa.get("distributions") and hsa.get("qualified_expenses") is not None:
        hsa_medical = min(float(hsa["distributions"]), float(hsa["qualified_expenses"]))
    charitable = vals["charitable_cash"] + vals["charitable_noncash"]
    cap = CHARITABLE_AGI_LIMIT * max(federal_agi, 0.0)
    if charitable > cap:
        findings.append(
            f"Charitable gifts of {charitable:,.0f} exceed CA's 50%-of-AGI "
            f"limit; {cap:,.0f} is deducted and the excess carries forward. "
            "Lower federal limits on appreciated property (30%) are not modelled.")
        charitable = cap
    ca = tr.get("ca") or {}
    misc = float(ca.get("miscellaneous_itemized") or 0.0)
    misc_allowed = max(0.0, misc - MISC_ITEMIZED_AGI_FLOOR * max(federal_agi, 0.0))
    # Schedule CA Part II line 8 col C (home-equity interest on up to $100,000
    # of debt, which CA still allows) and line 6 col C (foreign real property
    # tax, which CA still allows). Supplied as the allowable amounts.
    misc_allowed += float(ca.get("home_equity_interest") or 0.0)
    misc_allowed += float(ca.get("foreign_real_property_tax") or 0.0)
    rules = StateItemizedDeductionRules(
        standard_deduction=table.standard_deduction[status],
        medical_agi_floor=MEDICAL_AGI_FLOOR,
        mortgage_interest_debt_limit=MORTGAGE_DEBT_LIMIT.get(
            status, MORTGAGE_DEBT_LIMIT_DEFAULT),
        salt_cap=None,
        phaseout_threshold=table.agi_limit[status],
        phaseout_rate=ITEMIZED_PHASEOUT_RATE,
        phaseout_max_share=ITEMIZED_PHASEOUT_MAX_SHARE,
    )
    balance = it.get("mortgage_balance")
    try:
        inputs = ItemizedDeductionInputs(
            medical_expenses=vals["medical"] + hsa_medical,
            property_tax=vals["property_tax"],
            other_state_local_taxes=vals["other_state_local_taxes"],
            mortgage_interest=vals["mortgage_interest"],
            mortgage_balance=None if balance is None else float(balance),
            charitable=charitable,
            other_itemized=misc_allowed,
        )
        unlimited_rules = StateItemizedDeductionRules(
            standard_deduction=rules.standard_deduction,
            medical_agi_floor=rules.medical_agi_floor,
            mortgage_interest_debt_limit=rules.mortgage_interest_debt_limit)
        before = state_itemized_deduction(adjusted_gross_income=federal_agi,
                                          rules=unlimited_rules, inputs=inputs)
        allowed = state_itemized_deduction(adjusted_gross_income=federal_agi,
                                           rules=rules, inputs=inputs)
    except CashFlowError as e:
        label = ("tax_return.itemized.mortgage_balance" if "mortgage" in str(e)
                 else "tax_return.itemized")
        missing.append(f"{label} — {e}")
        return None, None
    return _whole(allowed), _whole(before)


# ── Exemption credits ───────────────────────────────────────────────────

def exemption_credits(tr: dict, federal_agi: float, table: CAYear, status: str,
                      missing: list[str]) -> tuple[dict[str, int], float, float]:
    """(counts, before limitation, allowed) — Form 540 lines 7-10 and 32."""
    taxpayers = tr.get("taxpayers") or []
    personal = 2 if status in ("mfj", "qss") else 1
    blind = sum(1 for t in taxpayers if t.get("blind"))
    senior = 0
    for i, t in enumerate(taxpayers):
        if t.get("age") is None:
            missing.append(f"tax_return.taxpayers[{i}].age — senior exemption "
                           "cannot be determined; tax may be overstated")
        elif int(t["age"]) >= SENIOR_AGE:
            senior += 1
    deps = len(tr.get("dependents") or [])
    counts = {"personal": personal, "blind": blind, "senior": senior, "dependent": deps}
    pbs_n = personal + blind + senior
    pbs = (personal * table.personal_exemption + blind * table.blind_exemption
           + senior * table.senior_exemption)
    dep_total = deps * table.dependent_exemption
    before = pbs + dep_total
    excess = federal_agi - table.agi_limit[status]
    if excess <= 0:
        return counts, before, before
    step = EXEMPTION_PHASEOUT_STEP_MFS if status == "mfs" else EXEMPTION_PHASEOUT_STEP
    steps = math.ceil(excess / step)
    per = steps * EXEMPTION_PHASEOUT_PER_STEP
    allowed = max(0.0, pbs - per * pbs_n) + max(0.0, dep_total - per * deps)
    return counts, before, allowed


# ── Main computation ────────────────────────────────────────────────────

def compute(tr: dict, fed: FederalInputs) -> CAReturn:
    """Form 540 workpaper for ``tr`` (the facts ``tax_return`` block)."""
    if not isinstance(tr, dict):
        raise CAReturnError("tax_return block is missing")
    ca = tr.get("ca") or {}
    _refuse_out_of_scope(tr, ca)

    try:
        year = int(tr.get("tax_year"))
    except (TypeError, ValueError) as e:
        raise CAReturnError("tax_return.tax_year is required") from e
    status = tr.get("filing_status")
    if status not in FILING_STATUSES:
        raise CAReturnError(f"filing_status {status!r} is not one of {FILING_STATUSES}")
    if fed.tax_year != year:
        raise CAReturnError(f"federal return is for {fed.tax_year}, not {year}")
    if fed.filing_status != status:
        raise CAReturnError(
            f"federal filing status {fed.filing_status!r} differs from "
            f"{status!r}; CA generally requires the federal status")
    if fed.agi is None:
        raise CAReturnError("federal AGI is unknown; California starts from it")

    table, projection = table_for(year)
    missing: list[str] = []
    findings: list[str] = []
    if projection:
        findings.append(
            f"FTB has not published {year} indexed amounts in this module; the "
            f"{table.tax_year} brackets, deduction, credits and thresholds are "
            "used as a projection. Indexing raises them each year, so tax is "
            "slightly overstated — recheck when the FTB publishes them.")

    federal_agi = _whole(float(fed.agi))
    adjustments = schedule_ca_adjustments(tr, fed, missing, findings)
    subtractions = _whole(sum(a.subtraction for a in adjustments))
    additions = _whole(sum(a.addition for a in adjustments))
    ca_agi = federal_agi - subtractions + additions

    findings.append(
        "Capital gains and qualified dividends are taxed as ordinary income in "
        "CA — there is no preferential rate.")
    findings.append(
        "Nothing below federal AGI carries over: the QBI deduction (§199A) has "
        "no CA equivalent, and CA builds its own deduction from Schedule A.")
    if fed.half_se_tax:
        findings.append("The deduction for half of self-employment tax conforms; "
                        "no Schedule CA adjustment is needed for it.")

    # Deduction (line 18)
    std = table.standard_deduction[status]
    itemized, itemized_before = ca_itemized(tr, federal_agi, table, status,
                                            missing, findings)
    if itemized is None and tr.get("itemized"):
        findings.append("Itemized deductions are incomplete, so the standard "
                        "deduction is used — tax is an upper bound.")
    # The shared block's spouse_itemizes (read by federal) applies unless the
    # CA block overrides it; CA follows the same both-or-neither rule.
    spouse_itemizes = ca.get("spouse_itemizes", tr.get("spouse_itemizes"))
    mfs_must_itemize = status == "mfs" and bool(spouse_itemizes)
    if mfs_must_itemize and itemized is None and not tr.get("itemized"):
        # Form 540 line 18: if the spouse itemizes, this return must too,
        # even when its itemized total is below the standard deduction.
        itemized = itemized_before = 0.0
        findings.append("Married filing separately and the spouse itemizes: "
                        "this return must itemize too. No itemized block is "
                        "recorded, so the deduction is 0.")
    if itemized is not None and (itemized > std or mfs_must_itemize):
        deduction, kind = itemized, "itemized"
    elif mfs_must_itemize:
        deduction, kind = std, "standard"
        findings.append("Married filing separately and the spouse itemizes, "
                        "but itemized deductions are incomplete: the standard "
                        "deduction shown is not allowed on the filed return.")
    else:
        deduction, kind = std, "standard"
    if status == "mfs" and spouse_itemizes is None:
        findings.append("Married filing separately: both spouses must itemize "
                        "or both take the standard deduction "
                        "(tax_return.spouse_itemizes not recorded).")
    if itemized_before is not None and itemized is not None and itemized < itemized_before:
        findings.append(
            f"CA itemized deductions are limited above federal AGI "
            f"{table.agi_limit[status]:,.0f}: {itemized_before:,.0f} falls to "
            f"{itemized:,.0f}.")

    taxable = max(0.0, ca_agi - deduction)
    tax = _whole(progressive_tax(taxable, table.brackets[status]))
    if taxable <= 100_000:
        findings.append("Taxable income is $100,000 or less, where the form "
                        "uses the tax table; the rate schedule used here can "
                        "differ from it by a few dollars.")

    counts, ex_before, ex_allowed = exemption_credits(tr, federal_agi, table,
                                                      status, missing)
    ex_allowed = _whole(ex_allowed)
    if ex_allowed < ex_before:
        findings.append(
            f"Exemption credits phase out above federal AGI "
            f"{table.agi_limit[status]:,.0f}: {ex_before:,.0f} falls to "
            f"{ex_allowed:,.0f}.")
    line33 = max(0.0, tax - ex_allowed)
    line35 = line33

    # Nonrefundable credits (lines 40-46). R&TC §17039 order: credits with no
    # carryover (the renter's credit, and any input marked carryover: false)
    # before credits that carry over, so a carryover never crowds out a
    # credit that would be lost.
    no_carry: list[tuple[str, float]] = []
    carry: list[tuple[str, float]] = []
    for i, c in enumerate(ca.get("nonrefundable_credits") or []):
        amt = _num(c.get("amount"), f"tax_return.ca.nonrefundable_credits[{i}].amount")
        if amt is None:
            missing.append(f"tax_return.ca.nonrefundable_credits[{i}].amount")
            continue
        name = str(c.get("name", "credit"))
        (no_carry if c.get("carryover") is False else carry).append((name, amt))
    limit, renter_credit = table.renters[status]
    renter = ca.get("renter")
    if ca_agi <= limit:
        if renter is None:
            findings.append(
                f"California AGI is within the renter's credit limit "
                f"({limit:,.0f}) but renter status is not recorded "
                "(tax_return.ca.renter) — credit not claimed.")
        elif renter:
            no_carry.append((RENTERS_CREDIT_NAME, renter_credit))
    elif renter:
        findings.append(
            f"Renter's credit not available: California AGI {ca_agi:,.0f} "
            f"exceeds {limit:,.0f}.")
    credits: list[tuple[str, float]] = []
    remaining = line35
    for group, carries in ((no_carry, False), (carry, True)):
        for name, amt in group:
            used = min(amt, remaining)
            remaining -= used
            credits.append((name, used))
            if used < amt:
                findings.append(
                    f"{name}: {amt - used:,.0f} exceeds the remaining tax; "
                    + ("the excess carries forward." if carries
                       else "it has no carryover and is lost."))
    total_credits = float(sum(a for _, a in credits))
    line48 = max(0.0, line35 - total_credits)

    # Other taxes
    amt_flag = (fed.federal_amt or 0) > 0 or ca.get("amt_preferences")
    if amt_flag:
        findings.append(
            "Alternative minimum tax may apply (federal AMT or a recorded "
            "preference item such as an ISO exercise). CA AMT (Schedule P, "
            "7% rate) is not computed — line 61 is left at zero, so tax is a "
            "lower bound.")
    elif ca_agi > table.amt_screen[status] and ca.get("amt_preferences") is None:
        findings.append(
            "California AMT: no preference items are recorded "
            "(tax_return.ca.amt_preferences). Confirm there were none (ISO "
            "exercises, accelerated depreciation) before filing.")
    bhst = _whole(BHST_RATE * max(0.0, taxable - BHST_THRESHOLD))
    if bhst:
        findings.append(
            f"Behavioral Health Services Tax (formerly Mental Health Services "
            f"Tax): 1% of taxable income over $1,000,000 = {bhst:,.0f}. The "
            "threshold does not double on a joint return.")
    other_taxes = float(ca.get("other_taxes") or 0.0)
    total_tax = line48 + bhst + other_taxes

    # Payments
    withholding = 0.0
    sdi_employers = 0
    for i, w in enumerate(tr.get("w2") or []):
        st = _state(w)
        if st is None and w.get("state_withheld"):
            missing.append(f"tax_return.w2[{i}].state — withholding not "
                           "counted until the state is known")
            continue
        if st == "CA":
            v = _num(w.get("state_withheld"), f"tax_return.w2[{i}].state_withheld")
            if v is None:
                missing.append(f"tax_return.w2[{i}].state_withheld — payments "
                               "are a lower bound")
            else:
                withholding += v
        if (w.get("sdi_withheld") or 0) > 0:
            sdi_employers += 1
    withholding += float(ca.get("other_ca_withholding") or 0.0)
    est_list = (tr.get("estimated_payments") or {}).get("state") or []
    if not isinstance(est_list, (list, tuple)) or len(est_list) > 4:
        raise CAReturnError(
            "tax_return.estimated_payments.state must be a list of up to four "
            f"quarterly amounts, got {est_list!r}")
    if any(p is None for p in est_list):
        missing.append("tax_return.estimated_payments.state — a null quarter; "
                       "payments are a lower bound")
    est_paid = [_num(p, "tax_return.estimated_payments.state") or 0.0
                for p in est_list] + [0.0] * (4 - len(est_list))
    overpayment = _num(ca.get("prior_year_overpayment_applied"),
                       "tax_return.ca.prior_year_overpayment_applied") or 0.0
    estimated = (sum(est_paid) + overpayment
                 + float(ca.get("extension_payment") or 0.0))
    other_wh = float(ca.get("withholding_592b_593") or 0.0)
    total_payments = withholding + estimated + other_wh
    findings.append(
        "SDI withheld (W-2 box 14) is not a payment toward income tax. Since "
        "2024 SDI has no wage ceiling, so excess SDI from multiple employers "
        "cannot arise and Form 540 no longer has a line for it."
        + (" Two or more employers withheld SDI; any over-withholding is "
           "recovered from the employer, not the FTB." if sdi_employers > 1 else ""))

    use_tax = _num(ca.get("use_tax"), "tax_return.ca.use_tax")
    if use_tax is None:
        missing.append("tax_return.ca.use_tax — line 91 must not be left blank; "
                       "enter 0 if no use tax is owed")
    if ca.get("full_year_health_coverage") is False:
        findings.append("Not every household member had full-year coverage: the "
                        "Individual Shared Responsibility penalty (line 92, FTB "
                        "3853) applies and is not computed.")
    elif ca.get("full_year_health_coverage") is None:
        missing.append("tax_return.ca.full_year_health_coverage — line 92 "
                       "Individual Shared Responsibility penalty")
    owed = total_tax + (use_tax or 0.0)
    refund = max(0.0, total_payments - owed)
    balance = max(0.0, owed - total_payments)

    # Underpayment of estimated tax for this year (FTB 5805 regular method).
    # The prior-year overpayment applied is credited on the first due date;
    # an extension payment comes after the last installment and is left out.
    timely = [est_paid[0] + overpayment] + est_paid[1:]
    req_annual, shortfalls = _underpayment(tr, ca, status, line48 + bhst,
                                           ca_agi, withholding + other_wh,
                                           timely, missing, findings)
    # Next year's schedule (Form 540-ES).
    next_agi = _num(ca.get("next_year_agi_estimate"),
                    "tax_return.ca.next_year_agi_estimate")
    next_req, installments = _next_year(year, status, line48 + bhst, ca_agi,
                                        withholding + other_wh, findings,
                                        next_agi=next_agi)
    llcs = _llcs(ca.get("llc") or [], year, missing, findings)

    return CAReturn(
        tax_year=year, filing_status=status, projection=projection,
        table_year=table.tax_year, federal_agi=federal_agi,
        adjustments=adjustments, subtractions=subtractions, additions=additions,
        ca_agi=ca_agi, standard_deduction=std, itemized_deduction=itemized,
        itemized_before_limit=itemized_before, deduction=deduction,
        deduction_kind=kind, taxable_income=taxable, tax=tax,
        exemption_counts=counts, exemption_before_limit=ex_before,
        exemption_credits=ex_allowed, tax_after_exemptions=line35,
        credits=credits, total_credits=total_credits, tax_after_credits=line48,
        bhst=bhst, other_taxes=other_taxes, total_tax=total_tax,
        withholding=withholding, estimated_payments=estimated,
        other_withholding=other_wh, total_payments=total_payments,
        use_tax=use_tax, refund=refund, balance_due=balance,
        underpayment_required_annual=req_annual,
        underpayment_shortfalls=shortfalls,
        next_year_required_annual=next_req,
        next_year_installments=installments, llcs=llcs,
        findings=findings, missing=missing,
    )


def _underpayment(tr: dict, ca: dict, status: str, current_tax: float,
                  ca_agi: float, withholding: float, est_paid: list[float],
                  missing: list[str], findings: list[str]
                  ) -> tuple[float | None, list[float]]:
    """FTB 5805 Part II required annual payment and per-installment shortfall.

    Withholding is treated as paid in four equal parts (FTB 5805 Part I
    question 3 default). ``current_tax`` is line 48 + line 62 (AMT, line 61,
    is not computed)."""
    min_bal = ES_MIN_BALANCE_MFS if status == "mfs" else ES_MIN_BALANCE
    if current_tax - withholding < min_bal:
        findings.append("No underpayment penalty: tax after withholding is "
                        f"under ${min_bal:,.0f} (FTB 5805 Part II line 4).")
        return None, []
    current_share = ES_CURRENT_YEAR_SHARE * current_tax
    no_prior = ca_agi >= _status_threshold(status, ES_NO_PRIOR_YEAR_AGI,
                                           ES_NO_PRIOR_YEAR_AGI_MFS)
    prior = tr.get("prior_year") or {}
    prior_tax = _num(prior.get("state_total_tax"), "tax_return.prior_year.state_total_tax")
    if no_prior:
        required = current_share
        findings.append("California AGI is $1,000,000 or more ($500,000 MFS): "
                        "the prior-year safe harbor is unavailable; the "
                        "required annual payment is 90% of this year's tax.")
    elif prior_tax is None:
        missing.append("tax_return.prior_year.state_total_tax — prior-year "
                       "safe harbor cannot be tested; 90% of current tax used")
        required = current_share
    else:
        prior_agi = _num(ca.get("prior_year_ca_agi"), "tax_return.ca.prior_year_ca_agi")
        if prior_agi is None:
            prior_agi = _num(prior.get("agi"), "tax_return.prior_year.agi")
            if prior_agi is not None:
                findings.append("Prior-year California AGI not recorded; prior "
                                "federal AGI is used to choose 100% or 110%.")
        if prior_agi is None:
            missing.append("tax_return.ca.prior_year_ca_agi — 110% assumed")
            high = True
        else:
            high = prior_agi > _status_threshold(status, ES_HIGH_INCOME_AGI,
                                                 ES_HIGH_INCOME_AGI_MFS)
        share = ES_PRIOR_YEAR_SHARE_HIGH if high else ES_PRIOR_YEAR_SHARE
        required = min(current_share, share * prior_tax)
    required = _whole(required)
    shortfalls: list[float] = []
    cum_req = cum_paid = 0.0
    for i, s in enumerate(ES_INSTALLMENT_SHARES):
        cum_req += s * required
        cum_paid += withholding / 4 + est_paid[i]
        shortfalls.append(_whole(max(0.0, cum_req - cum_paid)))
    if any(shortfalls):
        findings.append(
            f"Estimated tax was underpaid against a required annual payment of "
            f"{required:,.0f} (cumulative shortfall by installment: "
            + ", ".join(f"{x:,.0f}" for x in shortfalls)
            + "). Expect an FTB 5805 penalty; the annualized method may reduce "
            "it if income arrived late in the year.")
    return required, shortfalls


def _next_year(year: int, status: str, current_tax: float, ca_agi: float,
               withholding: float, findings: list[str], *,
               next_agi: float | None = None,
               ) -> tuple[float | None, list[Installment]]:
    """Form 540-ES schedule for ``year + 1`` on the prior-year safe harbor,
    assuming withholding repeats. The current-year (90%) path needs a
    projection of next year's tax, which this module does not make.

    R&TC §19136.3 bars the prior-year safe harbor when the AGI of the year
    being estimated (``year + 1``) is $1M or more ($500K MFS). That AGI is
    unknown here unless ``next_agi`` is supplied, so the schedule is printed
    on the condition that it stays below the line."""
    nxt = year + 1
    bar = _status_threshold(status, ES_NO_PRIOR_YEAR_AGI, ES_NO_PRIOR_YEAR_AGI_MFS)
    if next_agi is not None and next_agi >= bar:
        findings.append(
            f"Estimated {nxt} California AGI ({next_agi:,.0f}) is "
            f"${bar:,.0f} or more, which removes the prior-year safe harbor: "
            f"{nxt} estimates must be 90% of projected {nxt} tax, which needs "
            "a projection this workpaper does not make.")
        return None, []
    condition = ("" if next_agi is not None else
                 f" This holds only if {nxt} California AGI stays under "
                 f"${bar:,.0f}; at or above it, estimates must be 90% of "
                 f"{nxt} tax (record tax_return.ca.next_year_agi_estimate).")
    high = ca_agi > _status_threshold(status, ES_HIGH_INCOME_AGI, ES_HIGH_INCOME_AGI_MFS)
    share = ES_PRIOR_YEAR_SHARE_HIGH if high else ES_PRIOR_YEAR_SHARE
    required = _whole(share * current_tax)
    balance = max(0.0, required - withholding)
    min_bal = ES_MIN_BALANCE_MFS if status == "mfs" else ES_MIN_BALANCE
    if balance < min_bal:
        findings.append(
            f"No {nxt} estimated payments needed if withholding repeats: "
            f"{share:.0%} of this year's tax ({required:,.0f}) is covered "
            f"within ${min_bal:,.0f}." + condition)
        return required, []
    installments = [
        Installment(i + 1, _date(nxt + off, mo, day), s, _whole(s * balance))
        for i, (s, (off, mo, day)) in enumerate(zip(ES_INSTALLMENT_SHARES, ES_DUE_DATES))
    ]
    findings.append(
        f"{nxt} estimates on the prior-year safe harbor: {share:.0%} of "
        f"{current_tax:,.0f} = {required:,.0f}, less withholding of "
        f"{withholding:,.0f}, paid 30/40/0/30. A later bonus or equity vest "
        "withheld at the flat supplemental rate changes this." + condition)
    return required, installments


def llc_fee(total_income: float) -> float:
    for floor, fee in LLC_FEE_TIERS:
        if total_income >= floor:
            return fee
    return 0.0


def _formed_on(value: Any, i: int) -> _dt.date | None:
    if value is None or isinstance(value, _dt.date):
        return value
    try:
        return _dt.date.fromisoformat(str(value))
    except ValueError as e:
        raise CAReturnError(
            f"tax_return.ca.llc[{i}].formed_on {value!r} is not an ISO date") from e


def _llcs(rows: list, year: int, missing: list[str],
          findings: list[str]) -> list[LLCObligation]:
    out = []
    for i, r in enumerate(rows):
        name = str(r.get("name") or f"LLC {i + 1}")
        formed = r.get("formed_year")
        if formed is None:
            missing.append(f"tax_return.ca.llc[{i}].formed_year — first-year "
                           "annual tax cannot be determined")
            formed = year - 1
        formed = int(formed)
        if formed > year:
            continue
        income = _num(r.get("gross_receipts_total_income"),
                      f"tax_return.ca.llc[{i}].gross_receipts_total_income")
        if income is None:
            missing.append(f"tax_return.ca.llc[{i}].gross_receipts_total_income "
                           "— LLC fee cannot be determined")
        fee = None if income is None else llc_fee(income)
        annual_due: _dt.date | None = _date(year, 4, 15)
        fee_due = _date(year, LLC_FEE_ESTIMATE_MONTH, 15)
        if formed == year and formed in LLC_FIRST_YEAR_EXEMPT_YEARS:
            d0 = _formed_on(r.get("formed_on"), i)
            if d0 is not None:
                fee_due = _add_months(d0, LLC_FEE_ESTIMATE_MONTH)
        annual = LLC_ANNUAL_TAX
        note = "Disregarded SMLLC: Form 568 with the owner's return; $800 by FTB 3522."
        if formed == year:
            if formed in LLC_FIRST_YEAR_EXEMPT_YEARS:
                annual, annual_due = 0.0, None
                note = "First-year annual tax exempt (formed 2021–2023)."
            else:
                d = _formed_on(r.get("formed_on"), i)
                if d is None:
                    missing.append(f"tax_return.ca.llc[{i}].formed_on — first-year "
                                   "$800 is due the 15th day of the 4th month "
                                   "after the Secretary of State filing")
                    annual_due = None
                else:
                    annual_due = _add_months(d, 4)
                    fee_due = _add_months(d, LLC_FEE_ESTIMATE_MONTH)
                note = ("First year: the 2021–2023 exemption has expired, so the "
                        "$800 is owed for the formation year.")
        out.append(LLCObligation(
            name=name, total_income=income, annual_tax=annual,
            annual_tax_due=annual_due, fee=fee,
            fee_estimate_due=fee_due,
            return_due=_date(year + 1, LLC_RETURN_MONTH, 15), note=note))
        if fee:
            findings.append(
                f"{name}: total California income {income:,.0f} incurs an LLC "
                f"fee of {fee:,.0f} on top of the $800 tax; the estimate "
                f"(FTB 3536) was due {fee_due.isoformat()} — a short estimate costs a "
                "10% penalty on the shortfall.")
        findings.append(
            f"{name}: the {year + 1} $800 annual tax is due {year + 1}-04-15 "
            "(FTB 3522), the same day as this year's Form 568.")
    return out
