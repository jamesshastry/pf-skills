"""U.S. federal individual income tax return (Form 1040) workpaper.

The one idea: **a return is a chain of dependent lines, and a single unknown
link makes every line after it a guess.** This module computes Form 1040 line
by line from the source documents a household actually holds (W-2, 1099-INT,
1099-DIV, 1099-B, Schedule C records, HSA and IRA statements, Schedule A
receipts, estimated-payment confirmations), says which schedules each figure
triggers, and stops — listing what is missing — rather than filling a gap.
It prepares and checks; it never e-files and never substitutes for the
filed return.

Basis: nominal dollars of ``tax_year``. Arithmetic is exact (the IRS tax
tables round taxable income below $100,000 to $50 bands, so a filed figure
can differ by a few dollars). Annual parameters come from a cited table keyed
by tax year; a year not in the table uses the nearest one and is flagged as a
projection.

Accepts partnership (1065) and S-corporation (1120S) K-1s for a materially
participating owner: ordinary income and guaranteed payments (Schedule E
part II), interest and dividends, partnership SE earnings, and the §199A
items. Refuses (stops with a pointer, never estimates): passive K-1s, K-1
rental income, §179 and other codes, trust K-1s, rental and other
passive activities (``passive-loss-eligibility``), depreciation schedules
(``depreciation-election``), PFICs (``pfic-divest-or-comply``), nonresident
and dual-status returns, ISO exercises and other AMT preferences beyond the
standard and SALT add-backs, collectibles and §1250 gain, the excess business
loss limitation, foreign income outside the passive category
(``feie-vs-ftc``), and a §199A deduction above the threshold without the
per-business SSTB flag, W-2 wages and UBIA. Detects and reports without
computing: the kiddie tax on a dependent's own return (Form 8615) and
FBAR/Form 8938 exposure (``foreign-reporting-audit``).

Itemized deductions reuse :class:`pf.cashflow.ItemizedDeductionRules`;
bracket arithmetic reuses :func:`pf.cashflow.progressive_tax`; HSA, IRA and
elective-deferral limits come from :mod:`pf.limits`; the Social Security wage
base comes from :mod:`pf.aid`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from math import isfinite

from . import aid as _aid
from . import cashflow as _cf
from . import limits as _lim

# ── Statutory constants (not inflation-indexed) ─────────────────────────

#: Filing statuses accepted. ``qss`` (qualifying surviving spouse) uses the
#: joint brackets and standard deduction (§1(j)(2)(A), §63(c)(2)).
FILING_STATUSES = ("single", "mfj", "mfs", "hoh", "qss")

#: §1211(b): net capital loss deductible against ordinary income;
#: half for married filing separately.
CAPITAL_LOSS_LIMIT = {"mfs": 1_500.0}
CAPITAL_LOSS_LIMIT_DEFAULT = 3_000.0

#: Schedule B is required when taxable interest or ordinary dividends exceed
#: this amount (Schedule B instructions).
SCHEDULE_B_THRESHOLD = 1_500.0

#: §1402(a)(12): net earnings from self-employment are 92.35% of net profit
#: (100% less half the 15.3% rate).
SE_EARNINGS_FACTOR = 0.9235
#: §1402(b)(2): no SE tax when net earnings are under $400.
SE_MINIMUM_EARNINGS = 400.0
#: §1401(a) OASDI and §1401(b)(1) hospital insurance rates on SE income.
SE_OASDI_RATE = 0.124
SE_MEDICARE_RATE = 0.029
#: §164(f): half of SE tax is an above-the-line deduction.
SE_DEDUCTION_SHARE = 0.5
#: §3101(a) employee OASDI rate, used for the excess-withholding credit
#: (§31(b)) when two employers each withheld up to the wage base.
EMPLOYEE_OASDI_RATE = _aid.OASDI_RATE
#: §3101(b)(1) employee Medicare rate; withholding above it on a W-2 is
#: Additional Medicare Tax withheld (Form 8959 Part V).
EMPLOYEE_MEDICARE_RATE = _aid.MEDICARE_RATE

#: §3101(b)(2) / §1401(b)(2): Additional Medicare Tax rate and thresholds
#: (not indexed). Qualifying surviving spouse uses $200,000 (Form 8959 instr.).
ADDITIONAL_MEDICARE_RATE = _aid.ADDITIONAL_MEDICARE_RATE
ADDITIONAL_MEDICARE_THRESHOLD = {"mfj": 250_000.0, "mfs": 125_000.0,
                                 "single": 200_000.0, "hoh": 200_000.0,
                                 "qss": 200_000.0}
#: §3102(f)(1): employers withhold the 0.9% only on wages above $200,000
#: paid to an employee, regardless of filing status.
EMPLOYER_ADDITIONAL_MEDICARE_WITHHOLDING_THRESHOLD = 200_000.0

#: §1411(a)(1), (b): Net Investment Income Tax rate and MAGI thresholds
#: (not indexed).
NIIT_RATE = 0.038
NIIT_THRESHOLD = {"mfj": 250_000.0, "qss": 250_000.0, "mfs": 125_000.0,
                  "single": 200_000.0, "hoh": 200_000.0}

#: §223(f)(4): additional tax on HSA distributions not used for qualified
#: medical expenses, waived from age 65.
HSA_ADDITIONAL_TAX_RATE = 0.20
HSA_PENALTY_FREE_AGE = 65

#: §24(b)(1)-(2): CTC/ODC phase-out — $50 per $1,000 (or fraction) of MAGI
#: above $400,000 joint, $200,000 otherwise (P.L. 119-21 made permanent).
CTC_PHASEOUT_THRESHOLD = {"mfj": 400_000.0}
CTC_PHASEOUT_THRESHOLD_DEFAULT = 200_000.0
CTC_PHASEOUT_STEP = 1_000.0
CTC_PHASEOUT_PER_STEP = 50.0
#: §24(c)(1): a qualifying child for the CTC has not attained age 17.
CTC_AGE_LIMIT = 17
#: §24(h)(4): $500 credit for other dependents (not indexed).
ODC_AMOUNT = 500.0
#: §24(d)(1)(B)(i): refundable portion is 15% of earned income above $2,500.
ACTC_EARNED_INCOME_FLOOR = 2_500.0
ACTC_RATE = 0.15
#: §152(c)(1)(B): a qualifying child lives with the taxpayer more than half
#: the year; whole months are recorded, so seven or more.
MIN_MONTHS_LIVED = 7

#: §904(j): foreign tax credit without Form 1116 when all foreign income is
#: passive, reported on a payee statement, and creditable tax is at most
#: $300 ($600 joint).
SIMPLIFIED_FTC_LIMIT = {"mfj": 600.0}
SIMPLIFIED_FTC_LIMIT_DEFAULT = 300.0
#: §904(c): excess foreign tax carries back one year and forward ten.
FTC_CARRYBACK_YEARS, FTC_CARRYFORWARD_YEARS = 1, 10

#: §55(b)(1)(A): AMT rates below and above the 28% breakpoint.
AMT_RATE_LOW, AMT_RATE_HIGH = 0.26, 0.28

#: §1(h): preferential rates on qualified dividends and net capital gain.
CG_RATE_MID, CG_RATE_HIGH = 0.15, 0.20

#: §199A(a): 20% of qualified business income, limited to 20% of taxable
#: income less net capital gain; §199A(b)(2)(B) wage/UBIA limits.
QBI_RATE = 0.20
QBI_WAGE_RATE = 0.50
QBI_WAGE_RATE_WITH_UBIA = 0.25
QBI_UBIA_RATE = 0.025

#: §6654(d)(1)(B)-(C), (e)(1): estimated-tax safe harbors — 90% of current
#: tax, or 100% of prior-year tax (110% when prior-year AGI exceeds $150,000,
#: $75,000 married filing separately); no penalty under $1,000 owed.
SAFE_HARBOR_CURRENT = 0.90
SAFE_HARBOR_PRIOR = 1.00
SAFE_HARBOR_PRIOR_HIGH = 1.10
SAFE_HARBOR_HIGH_AGI = {"mfs": 75_000.0}
SAFE_HARBOR_HIGH_AGI_DEFAULT = 150_000.0
PENALTY_DE_MINIMIS = 1_000.0
#: §6654(c)-(d): four equal required installments; withholding is treated
#: as paid evenly through the year (§6654(g)).
INSTALLMENT_DUE = ("Apr 15", "Jun 15", "Sep 15", "Jan 15 (following year)")

#: Treas. Reg. §31.3402(g)-1(a)(7): optional flat rate on supplemental wages
#: (bonus, RSU vesting) up to $1,000,000; mandatory 37% above it.
SUPPLEMENTAL_WITHHOLDING_RATE = 0.22
SUPPLEMENTAL_MANDATORY_THRESHOLD = 1_000_000.0

#: §213(a) medical floor, §163(h)(3)(F) acquisition-debt limit (halved MFS),
#: §164(b)(7) SALT phase-out rate and floor (halved MFS), §170(b)(1)(I)
#: 0.5% charitable floor and §68 2/37 limitation (from 2026), §170(p)
#: non-itemizer cash charitable deduction (from 2026).
MEDICAL_AGI_FLOOR = 0.075
MORTGAGE_DEBT_LIMIT = 750_000.0
SALT_PHASEOUT_RATE = 0.30
SALT_FLOOR = 10_000.0
ITEMIZED_LIMITATION_RATE = 2 / 37
#: §170(b)(1)(G): cash gifts to public charities are limited to 60% of AGI.
CHARITABLE_CASH_LIMIT = 0.60
#: §170(b)(1)(C): capital-gain property at fair value is limited to 30% of AGI,
#: and (§170(b)(1)(B)/(C)) non-cash gifts together with cash may not exceed
#: 50% of AGI. Non-cash gifts are treated as capital-gain property — the
#: stricter class, so the deduction is never overstated.
CHARITABLE_PROPERTY_LIMIT = 0.30
CHARITABLE_NONCASH_OVERALL = 0.50
#: §170(d)(1): excess contributions carry forward five years.
CHARITABLE_CARRYFORWARD_YEARS = 5
#: §170(f)(8): a contemporaneous written acknowledgment for a gift of $250
#: or more; §170(f)(11)(B): Form 8283 for non-cash gifts over $500.
CHARITY_ACK_THRESHOLD = 250.0
FORM_8283_THRESHOLD = 500.0

#: §151(d)(5)(C) (P.L. 119-21 §70103): $6,000 deduction per taxpayer aged 65
#: or older, tax years 2025-2028, reduced by 6% of MAGI above $75,000
#: ($150,000 joint); married filing separately is ineligible.
SENIOR_DEDUCTION_YEARS = range(2025, 2029)
SENIOR_DEDUCTION_AMOUNT = 6_000.0
SENIOR_DEDUCTION_PHASEOUT_RATE = 0.06
SENIOR_DEDUCTION_THRESHOLD = {"mfj": 150_000.0}
SENIOR_DEDUCTION_THRESHOLD_DEFAULT = 75_000.0
SENIOR_AGE = 65

#: §86(c), (b): Social Security benefits worksheet base and adjusted base
#: amounts (not indexed). Married filing separately and living with the
#: spouse at any time in the year: both are zero, so up to 85% is taxable.
SS_BASE_AMOUNT = {"mfj": 32_000.0, "mfs_together": 0.0}
SS_BASE_AMOUNT_DEFAULT = 25_000.0
SS_ADJUSTED_BASE_EXTRA = {"mfj": 12_000.0, "mfs_together": 0.0}
SS_ADJUSTED_BASE_EXTRA_DEFAULT = 9_000.0
#: §86(a)(1)-(2): 50% of benefits in the first tier, 85% above it.
SS_TIER1_RATE = 0.50
SS_TIER2_RATE = 0.85

#: K-1 forms accepted: partnership (Form 1065) and S corporation (1120S).
K1_FORMS = ("1065", "1120S")
#: Fields a K-1 entry may carry. Anything else (rental income, §179, other
#: box codes) is refused rather than silently dropped.
K1_FIELDS = frozenset({
    "entity", "form", "owner", "ordinary_business_income", "guaranteed_payments",
    "se_earnings", "interest", "dividends", "distributions", "qbi_income",
    "qbi_w2_wages", "qbi_ubia", "sstb", "material_participation"})
#: Label for a K-1 whose owner is not recorded on a joint return. It matches
#: no W-2, so its SE tax is computed without wage-base netting (an upper bound).
UNATTRIBUTED = "unattributed owner"

#: §219(g)(2)(A)(ii)-(C): the deductible IRA limit phases down over the
#: range, rounded up to the next $10, with a $200 minimum while any remains.
IRA_DEDUCTION_ROUNDING = 10.0
IRA_DEDUCTION_MINIMUM = 200.0

#: Fields ``tax_return.foreign`` may carry. Anything else non-zero is refused.
FOREIGN_FIELDS = frozenset({
    "country", "accounts", "interest", "dividends", "qualified_dividends",
    "capital_transactions", "rent", "foreign_tax_paid", "reported_on_1099",
    "category", "income"})
#: 1099-DIV boxes this module does not tax: §199A REIT dividends (box 5),
#: unrecaptured §1250 gain (2b), collectibles gain (2d), §1202 gain (2c).
UNSUPPORTED_DIVIDEND_FIELDS = ("section_199a_dividends", "unrecaptured_1250",
                               "collectibles_gain", "section_1202_gain")
#: Most federal estimated-tax installments in a year (§6654(c)).
MAX_INSTALLMENTS = 4

#: Top-level keys that put a return outside this module, and where to go.
OUT_OF_SCOPE = {
    "schedule_k1": "enter partnership and S-corporation K-1s under tax_return.k1 "
                   "(see SCHEMA.md); trust K-1s and passive activities are not "
                   "modelled — see passive-loss-eligibility",
    "rental_properties": "rental income is a passive activity (Schedule E, Form 8582); "
                         "use passive-loss-eligibility and depreciation-election",
    "schedule_e": "Schedule E part I income (rents, royalties) is not modelled; use "
                  "passive-loss-eligibility (K-1s go under tax_return.k1)",
    "depreciation": "depreciation schedules (Form 4562) are not computed; use "
                    "depreciation-election and enter the resulting expense in schedule_c",
    "pfic": "PFIC income (Form 8621) is not modelled; use pfic-divest-or-comply",
    "iso_exercises": "ISO exercises are an AMT preference this module does not "
                     "compute; model the AMT with a full Form 6251",
    "amt_preferences": "AMT preferences beyond the standard and SALT add-backs are "
                       "not computed",
}

#: Transcribed from the cited sources (Rev. Proc. text read 2026-11-22 for
#: the inflation-adjusted items); marked unverified until a human checks them,
#: per the repository's provenance policy.
FEDERAL_VERIFIED = "unverified"

Bracket = _cf.Bracket


class FederalReturnError(ValueError):
    """The inputs cannot support a return without guessing."""

    def __init__(self, message: str, missing: list[str] | None = None):
        super().__init__(message)
        self.missing = list(missing or [])


@dataclass(frozen=True)
class FederalYear:
    """Inflation-adjusted and year-specific parameters for one tax year.

    Dict keys are bracket groups: ``mfj`` (also qualifying surviving spouse),
    ``single``, ``hoh``, ``mfs``.
    """
    tax_year: int
    source: str
    verified_on: str
    #: §1(j)(2): (rate, upper bound of taxable income or None).
    brackets: dict[str, tuple[Bracket, ...]]
    #: §63(c)(2) basic standard deduction.
    standard_deduction: dict[str, float]
    #: §63(f): additional amount per box (65+ or blind), married / unmarried.
    additional_standard_married: float
    additional_standard_unmarried: float
    #: §1(j)(5)(B): top of the 0% and 15% capital-gain bands.
    cg_zero_max: dict[str, float]
    cg_fifteen_max: dict[str, float]
    #: §55(d): AMT exemption (``single`` covers head of household).
    amt_exemption: dict[str, float]
    amt_phaseout_start: dict[str, float]
    amt_phaseout_rate: float
    #: §55(b)(1): AMT taxable income where 28% starts (``mfs`` / ``other``).
    amt_28_threshold: dict[str, float]
    #: §24(a), §24(h)(5): CTC per child and the refundable maximum per child.
    ctc_per_child: float
    actc_refundable_max: float
    #: §199A(e)(2) threshold and §199A(b)(3)(B) phase-in range
    #: (``mfj``, ``mfs``, ``other``).
    qbi_threshold: dict[str, float]
    qbi_phase_in_range: dict[str, float]
    #: §199A(i): minimum deduction and the QBI needed for it (None before 2026).
    qbi_minimum_deduction: float | None
    qbi_minimum_income: float | None
    #: §164(b)(7): SALT cap and MAGI phase-out threshold (MFS is half).
    salt_cap: float
    salt_phaseout_threshold: float
    #: §170(b)(1)(I) floor; §170(p) non-itemizer limit (``mfj`` / ``other``);
    #: §68 limitation rate. Zero before 2026.
    charitable_agi_floor: float
    nonitemizer_charitable_limit: dict[str, float]
    itemized_limitation_rate: float
    #: §461(l)(3)(A)(ii)(II) excess business loss threshold (``mfj``/``other``).
    excess_business_loss: dict[str, float]
    #: §219(g)(3)(B), (g)(7): traditional IRA deduction phase-out ranges by
    #: MAGI — ``covered_single`` (single/HoH, or MFS apart all year),
    #: ``covered_joint`` (MFJ/QSS, contributor covered), ``spouse_covered``
    #: (MFJ, contributor not covered, spouse covered), ``mfs`` (MFS living together).
    ira_deduction_phaseout: dict[str, tuple[float, float]]


def _b(*pairs) -> tuple[Bracket, ...]:
    rates = (0.10, 0.12, 0.22, 0.24, 0.32, 0.35, 0.37)
    return tuple(zip(rates, list(pairs) + [None]))


FEDERAL_TABLES: dict[int, FederalYear] = {
    2025: FederalYear(
        tax_year=2025,
        source="Rev. Proc. 2024-40 (brackets, capital-gain bands, AMT, §199A, "
               "excess business loss, additional standard deduction, ACTC); "
               "P.L. 119-21 §§70102, 70104, 70120 as amended for 2025 "
               "(standard deduction $31,500/$15,750/$23,625, CTC $2,200, "
               "SALT cap $40,000 phasing down above $500,000 MAGI); IRS "
               "Notice 2024-80 (IRA deduction phase-outs)",
        verified_on=FEDERAL_VERIFIED,
        brackets={
            "mfj": _b(23_850, 96_950, 206_700, 394_600, 501_050, 751_600),
            "hoh": _b(17_000, 64_850, 103_350, 197_300, 250_500, 626_350),
            "single": _b(11_925, 48_475, 103_350, 197_300, 250_525, 626_350),
            "mfs": _b(11_925, 48_475, 103_350, 197_300, 250_525, 375_800),
        },
        standard_deduction={"mfj": 31_500, "hoh": 23_625, "single": 15_750,
                            "mfs": 15_750},
        additional_standard_married=1_600, additional_standard_unmarried=2_000,
        cg_zero_max={"mfj": 96_700, "mfs": 48_350, "hoh": 64_750, "single": 48_350},
        cg_fifteen_max={"mfj": 600_050, "mfs": 300_000, "hoh": 566_700,
                        "single": 533_400},
        amt_exemption={"mfj": 137_000, "single": 88_100, "mfs": 68_500},
        amt_phaseout_start={"mfj": 1_252_700, "single": 626_350, "mfs": 626_350},
        amt_phaseout_rate=0.25,
        amt_28_threshold={"mfs": 119_550, "other": 239_100},
        ctc_per_child=2_200, actc_refundable_max=1_700,
        qbi_threshold={"mfj": 394_600, "mfs": 197_300, "other": 197_300},
        qbi_phase_in_range={"mfj": 100_000, "mfs": 50_000, "other": 50_000},
        qbi_minimum_deduction=None, qbi_minimum_income=None,
        salt_cap=40_000, salt_phaseout_threshold=500_000,
        charitable_agi_floor=0.0,
        nonitemizer_charitable_limit={"mfj": 0.0, "other": 0.0},
        itemized_limitation_rate=0.0,
        excess_business_loss={"mfj": 626_000, "other": 313_000},
        ira_deduction_phaseout={"covered_single": (79_000, 89_000),
                                "covered_joint": (126_000, 146_000),
                                "spouse_covered": (236_000, 246_000),
                                "mfs": (0, 10_000)},
    ),
    2026: FederalYear(
        tax_year=2026,
        source="Rev. Proc. 2025-32 §§4.01, 4.03, 4.05, 4.10, 4.14, 4.26, 4.31 "
               "and §2.12 (§199A(i) minimum); P.L. 119-21: §164(b)(7) SALT "
               "cap $40,400 phasing down above $505,000 MAGI, §170(b)(1)(I) "
               "0.5% floor, §170(p) $1,000/$2,000, §68 2/37 limitation, "
               "AMT exemption phase-out at 50%; IRS 2026 COLA release "
               "(IRA deduction phase-outs $81,000/$129,000/$242,000)",
        verified_on=FEDERAL_VERIFIED,
        brackets={
            "mfj": _b(24_800, 100_800, 211_400, 403_550, 512_450, 768_700),
            "hoh": _b(17_700, 67_450, 105_700, 201_750, 256_200, 640_600),
            "single": _b(12_400, 50_400, 105_700, 201_775, 256_225, 640_600),
            "mfs": _b(12_400, 50_400, 105_700, 201_775, 256_225, 384_350),
        },
        standard_deduction={"mfj": 32_200, "hoh": 24_150, "single": 16_100,
                            "mfs": 16_100},
        additional_standard_married=1_650, additional_standard_unmarried=2_050,
        cg_zero_max={"mfj": 98_900, "mfs": 49_450, "hoh": 66_200, "single": 49_450},
        cg_fifteen_max={"mfj": 613_700, "mfs": 306_850, "hoh": 579_600,
                        "single": 545_500},
        amt_exemption={"mfj": 140_200, "single": 90_100, "mfs": 70_100},
        amt_phaseout_start={"mfj": 1_000_000, "single": 500_000, "mfs": 500_000},
        amt_phaseout_rate=0.50,
        amt_28_threshold={"mfs": 122_250, "other": 244_500},
        ctc_per_child=2_200, actc_refundable_max=1_700,
        qbi_threshold={"mfj": 403_500, "mfs": 201_775, "other": 201_750},
        qbi_phase_in_range={"mfj": 150_000, "mfs": 75_000, "other": 75_000},
        qbi_minimum_deduction=400, qbi_minimum_income=1_000,
        salt_cap=40_400, salt_phaseout_threshold=505_000,
        charitable_agi_floor=0.005,
        nonitemizer_charitable_limit={"mfj": 2_000.0, "other": 1_000.0},
        itemized_limitation_rate=ITEMIZED_LIMITATION_RATE,
        excess_business_loss={"mfj": 512_000, "other": 256_000},
        ira_deduction_phaseout={"covered_single": (81_000, 91_000),
                                "covered_joint": (129_000, 149_000),
                                "spouse_covered": (242_000, 252_000),
                                "mfs": (0, 10_000)},
    ),
}


def table_for(tax_year: int) -> tuple[FederalYear, bool]:
    """The table for the year, or the nearest shipped one and True when the
    requested year is not in this module (a projection or a back-cast)."""
    if tax_year in FEDERAL_TABLES:
        return FEDERAL_TABLES[tax_year], False
    years = sorted(FEDERAL_TABLES)
    nearest = years[0] if tax_year < years[0] else years[-1]
    return FEDERAL_TABLES[nearest], True


def _group(status: str) -> str:
    return {"qss": "mfj"}.get(status, status)


def _amt_group(status: str) -> str:
    return {"qss": "mfj", "hoh": "single"}.get(status, status)


def _qbi_group(status: str) -> str:
    return {"mfj": "mfj", "qss": "mfj", "mfs": "mfs"}.get(status, "other")


def _joint(status: str) -> str:
    return "mfj" if status == "mfj" else "other"


def itemized_rules(status: str, table: FederalYear) -> _cf.ItemizedDeductionRules:
    """The cashflow itemized-deduction rules for one filing status and year."""
    half = 0.5 if status == "mfs" else 1.0
    brackets = table.brackets[_group(status)]
    top_start = brackets[-2][1]
    return _cf.ItemizedDeductionRules(
        salt_cap=table.salt_cap * half,
        medical_agi_floor=MEDICAL_AGI_FLOOR,
        mortgage_interest_debt_limit=MORTGAGE_DEBT_LIMIT * half,
        salt_phaseout_threshold=table.salt_phaseout_threshold * half,
        salt_phaseout_rate=SALT_PHASEOUT_RATE,
        salt_cap_floor=SALT_FLOOR * half,
        charitable_agi_floor=table.charitable_agi_floor,
        nonitemizer_charitable_limit=table.nonitemizer_charitable_limit[_joint(status)],
        limitation_rate=table.itemized_limitation_rate,
        limitation_threshold=top_start if table.itemized_limitation_rate else None,
    )


# ── result ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FederalReturn:
    tax_year: int
    filing_status: str
    projection: bool
    table_source: str
    wages: float
    taxable_interest: float
    tax_exempt_interest: float
    us_treasury_interest: float
    ordinary_dividends: float
    qualified_dividends: float
    capital_gain_distributions: float
    short_term_net: float
    long_term_net: float
    #: Schedule D line 21: net gain, or the loss after the §1211 limit.
    net_capital_gain_or_loss: float
    capital_loss_carryover_to_next_year: dict
    schedule_c_net: float
    schedule_c_detail: list
    ira_taxable: float
    hsa_taxable_distributions: float
    foreign_income: float
    #: Form 1040 line 6b: taxable part of SSA-1099 benefits (§86 worksheet).
    taxable_social_security: float
    #: Schedule 1 line 1: state/local income tax refund taxable under the
    #: tax-benefit rule (§111; Pub. 525 worksheet).
    state_refund_taxable: float
    total_income: float
    self_employment_tax: float
    adjustments: dict
    agi: float
    itemized: dict
    itemized_total: float
    standard_deduction: float
    itemizes: bool
    nonitemizer_charitable: float
    deduction_used: float
    senior_deduction: float
    qbi_deduction: float
    taxable_income: float
    preferential_income: float
    regular_tax: float
    marginal_rate: float
    amt: float
    credits: dict
    niit: float
    additional_medicare_tax: float
    other_taxes: dict
    total_tax: float
    withholding: dict
    estimated_payments: float | None
    refundable_credits: float
    total_payments: float | None
    #: Positive is a refund, negative a balance due; None when payments are
    #: unknown.
    refund_or_due: float | None
    penalty_safe_harbor: dict
    next_year_estimates: dict
    carryforwards: dict
    forms: list
    documents: list
    bounds: list
    findings: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    #: Schedule E part II: K-1 ordinary business income plus guaranteed payments.
    k1_income: float = 0.0
    k1_detail: list = field(default_factory=list)


# ── input handling ───────────────────────────────────────────────────────


class _Ctx:
    def __init__(self) -> None:
        self.stop: list[str] = []
        self.missing: list[str] = []
        self.findings: list[str] = []
        self.bounds: list[str] = []
        self.forms: set[str] = set()
        self.documents: list[str] = []

    def num(self, value, path: str, *, stop: bool = True,
            allow_negative: bool = False) -> float | None:
        """A required figure. ``None`` is unknown: listed, and either queued
        to stop the computation or returned as None for the caller to bound."""
        if value is None:
            self.missing.append(path)
            if stop:
                self.stop.append(path)
            return None
        if isinstance(value, bool):
            raise FederalReturnError(f"{path} must be a number, not {value!r}")
        try:
            x = float(value)
        except (TypeError, ValueError) as e:
            raise FederalReturnError(f"{path} must be a number, not {value!r}") from e
        if not isfinite(x):
            raise FederalReturnError(f"{path} must be finite")
        if x < 0 and not allow_negative:
            raise FederalReturnError(f"{path} cannot be negative ({x:,.0f})")
        return x

    def opt(self, d: dict, key: str, path: str, *, stop: bool = True) -> float | None:
        """A secondary field: absent means none on the document, ``null``
        means nobody looked."""
        if key not in d:
            return 0.0
        return self.num(d[key], path, stop=stop)


def _list(ctx: _Ctx, tr: dict, key: str, doc: str, *, stop: bool = True) -> list | None:
    """A list section. Absent is empty; ``null`` is unknown — listed, and
    either queued to stop (``stop``) or returned as None for the caller to
    bound."""
    if key not in tr:
        return []
    v = tr[key]
    if v is None:
        ctx.missing.append(f"{key} ({doc} — not recorded)")
        if stop:
            ctx.stop.append(key)
            return []
        return None
    if not isinstance(v, list):
        raise FederalReturnError(f"{key} must be a list")
    for i, x in enumerate(v):
        if not isinstance(x, dict):
            raise FederalReturnError(f"{key}[{i}] must be a mapping")
    return v


def _section(ctx: _Ctx, d: dict, key: str, doc: str, *, stop: bool,
             path: str | None = None) -> dict | None:
    """A mapping section. Absent is empty; ``null`` is unknown — listed, and
    either queued to stop or returned as None for the caller to bound."""
    path = path or key
    if key not in d:
        return {}
    v = d[key]
    if v is None:
        ctx.missing.append(f"{path} ({doc} — not recorded)")
        if stop:
            ctx.stop.append(path)
        return None
    if not isinstance(v, dict):
        raise FederalReturnError(f"{path} must be a mapping")
    return v


def _check_scope(tr: dict) -> None:
    for key, why in OUT_OF_SCOPE.items():
        if tr.get(key):
            raise FederalReturnError(f"out of scope — {why}")
    residency = tr.get("residency", "resident")
    if residency not in (None, "resident", "citizen"):
        raise FederalReturnError(
            f"out of scope — a {residency} return (Form 1040-NR or dual-status) "
            "is not modelled")


# ── components ───────────────────────────────────────────────────────────


def _taxpayers(ctx: _Ctx, tr: dict, status: str) -> list[dict]:
    tps = tr.get("taxpayers")
    if not tps or not isinstance(tps, list):
        raise FederalReturnError("taxpayers is required (one entry per filer)")
    want = 2 if status == "mfj" else 1
    if len(tps) != want:
        raise FederalReturnError(
            f"filing status {status} takes {want} taxpayer(s); {len(tps)} listed")
    for i, t in enumerate(tps):
        if t.get("age") is None:
            ctx.missing.append(f"taxpayers[{i}].age")
            ctx.stop.append(f"taxpayers[{i}].age")
    return tps


def _owner_of(item: dict, tps: list[dict]) -> str | None:
    if item.get("owner"):
        return item["owner"]
    if len(tps) == 1:
        return tps[0].get("member") or "taxpayer"
    return None


def _age_of(member: str | None, tps: list[dict]) -> int | None:
    if len(tps) == 1 and member in (None, "taxpayer", tps[0].get("member")):
        return tps[0].get("age")
    for t in tps:
        if t.get("member") == member:
            return t.get("age")
    return None


def _transactions(ctx: _Ctx, rows: list, prefix: str) -> tuple[float, float]:
    """Net short- and long-term gain of Form 8949 rows."""
    st = lt = 0.0
    for i, t in enumerate(rows):
        p = f"{prefix}[{i}]"
        if not isinstance(t, dict):
            raise FederalReturnError(f"{p} must be a mapping")
        if t.get("collectible") or t.get("section_1250"):
            raise FederalReturnError(
                f"out of scope — {p} is a collectible or §1250 gain (28%/25% rates)")
        if t.get("pfic"):
            raise FederalReturnError(
                f"out of scope — {p} is a PFIC (e.g. a foreign mutual fund); use "
                "pfic-divest-or-comply")
        proceeds = ctx.num(t.get("proceeds"), f"{p}.proceeds")
        basis = ctx.num(t.get("basis"), f"{p}.basis")
        wash = ctx.opt(t, "wash_sale_disallowed", f"{p}.wash_sale_disallowed")
        term = t.get("term")
        if term not in ("short", "long"):
            raise FederalReturnError(f"{p}.term must be short or long")
        if t.get("basis_reported") is False:
            ctx.findings.append(
                f"{t.get('description', p)}: basis was not reported to the IRS "
                "(Form 8949 box B/E) — keep the purchase records that support "
                "the basis entered.")
        if None in (proceeds, basis, wash):
            continue
        gain = proceeds - basis + wash
        if wash:
            ctx.findings.append(
                f"{t.get('description', p)}: ${wash:,.0f} of loss disallowed as a "
                "wash sale (Form 8949 code W); it moves into the replacement "
                "shares' basis, not lost.")
        if term == "short":
            st += gain
        else:
            lt += gain
    return st, lt


def _capital(ctx: _Ctx, tr: dict, cgd: float, foreign_rows: list) -> dict:
    st, lt = _transactions(ctx, _list(ctx, tr, "capital_transactions", "Form 1099-B"),
                           "capital_transactions")
    fst, flt = _transactions(ctx, foreign_rows, "foreign.capital_transactions")
    carry = _section(ctx, tr, "capital_loss_carryover",
                     "last year's capital loss carryover worksheet", stop=True) or {}
    st_carry = ctx.opt(carry, "short", "capital_loss_carryover.short") or 0.0
    lt_carry = ctx.opt(carry, "long", "capital_loss_carryover.long") or 0.0
    return {"st": st + fst - st_carry, "lt": lt + flt + cgd - lt_carry,
            "foreign_st": fst, "foreign_lt": flt,
            "st_carry_in": st_carry, "lt_carry_in": lt_carry}


def _carryover(st: float, lt: float, loss_deducted: float,
               taxable_income_before: float) -> dict:
    """Schedule D Capital Loss Carryover Worksheet (lines 1-13)."""
    line3 = max(0.0, taxable_income_before + loss_deducted)
    line4 = min(loss_deducted, line3)
    st_loss = max(0.0, -st)
    lt_gain = max(0.0, lt)
    st_carry = max(0.0, st_loss - (line4 + lt_gain))
    lt_loss = max(0.0, -lt)
    st_gain = max(0.0, st)
    lt_carry = max(0.0, lt_loss - (st_gain + max(0.0, line4 - st_loss)))
    return {"short": st_carry, "long": lt_carry}


def _schedule_c(ctx: _Ctx, tr: dict, tps: list[dict]) -> list[dict]:
    out = []
    for i, b in enumerate(_list(ctx, tr, "schedule_c", "Schedule C records")):
        p = f"schedule_c[{i}]"
        owner = _owner_of(b, tps)
        if owner is None:
            ctx.missing.append(f"{p}.owner")
            ctx.stop.append(f"{p}.owner")
        gross = ctx.num(b.get("gross_receipts"), f"{p}.gross_receipts")
        expenses = b.get("expenses") or {}
        if b.get("expenses") is None and "expenses" in b:
            ctx.missing.append(f"{p}.expenses")
            ctx.stop.append(f"{p}.expenses")
        exp_total = 0.0
        for k, v in expenses.items():
            x = ctx.num(v, f"{p}.expenses.{k}")
            exp_total += x or 0.0
        vehicle = ctx.opt(b, "vehicle", f"{p}.vehicle") or 0.0
        home = ctx.opt(b, "home_office", f"{p}.home_office") or 0.0
        if gross is None:
            continue
        tentative = gross - exp_total - vehicle
        allowed_home = max(0.0, min(home, tentative))
        disallowed = home - allowed_home
        simplified = b.get("home_office_method") == "simplified"
        net = tentative - allowed_home
        name = b.get("business", p)
        if disallowed > 0:
            if simplified:
                ctx.findings.append(
                    f"{name}: ${disallowed:,.0f} of home-office deduction exceeds "
                    "the business's income and is lost — the simplified method "
                    "has no carryforward (Form 8829 would carry it).")
            else:
                ctx.findings.append(
                    f"{name}: ${disallowed:,.0f} of home-office deduction cannot "
                    "create or increase a loss (§280A(c)(5)); it carries forward "
                    "on Form 8829.")
        if net < 0:
            ctx.findings.append(
                f"{name}: Schedule C loss of ${-net:,.0f} offsets other income on "
                "the assumption of material participation, an at-risk investment "
                "and a profit motive (§183) — each is a question an examiner asks.")
        out.append({"business": name, "owner": owner, "gross_receipts": gross,
                    "expenses": exp_total + vehicle, "home_office_allowed": allowed_home,
                    "home_office_carryforward": 0.0 if simplified else disallowed,
                    "net": net, "sstb": b.get("sstb"), "w2_wages": b.get("w2_wages"),
                    "ubia": b.get("ubia")})
    return out


def _k1s(ctx: _Ctx, tr: dict, tps: list[dict], status: str) -> list[dict]:
    """Partnership and S-corporation K-1s for materially participating owners."""
    out = []
    for i, k in enumerate(_list(ctx, tr, "k1", "Schedule K-1")):
        p = f"k1[{i}]"
        name = k.get("entity") or p
        form = str(k.get("form"))
        if form not in K1_FORMS:
            raise FederalReturnError(
                f"out of scope — {p} form {k.get('form')!r}: only 1065 and 1120S "
                "K-1s are accepted (a trust K-1 is not modelled)")
        extra = sorted(key for key, v in k.items()
                       if key not in K1_FIELDS and v not in (None, 0, False, [], {}))
        if extra:
            raise FederalReturnError(
                f"out of scope — {name} K-1 carries {', '.join(extra)}: rental "
                "income, §179 and other codes are not modelled (see "
                "passive-loss-eligibility and depreciation-election)")
        mp = k.get("material_participation")
        if mp is False:
            raise FederalReturnError(
                f"out of scope — {name} K-1 is passive (no material participation); "
                "use passive-loss-eligibility (Form 8582)")
        if mp is None:
            ctx.missing.append(f"{p}.material_participation")
            ctx.stop.append(f"{p}.material_participation (passive or not decides "
                            "the treatment)")
        owner = _owner_of(k, tps)
        ordinary_inc = ctx.num(k.get("ordinary_business_income"),
                               f"{p}.ordinary_business_income", allow_negative=True)
        gp = ctx.num(k.get("guaranteed_payments", 0), f"{p}.guaranteed_payments")
        interest = ctx.num(k.get("interest", 0), f"{p}.interest")
        dividends = ctx.num(k.get("dividends", 0), f"{p}.dividends")
        qbi_income = ctx.num(k.get("qbi_income"), f"{p}.qbi_income", allow_negative=True)
        dist = ctx.num(k.get("distributions", 0), f"{p}.distributions", stop=False)
        if form == "1120S":
            if gp:
                raise FederalReturnError(
                    f"{p}: an S corporation does not report guaranteed payments — "
                    "shareholder pay is W-2 wages")
            se_earn = 0.0
            if k.get("se_earnings"):
                ctx.findings.append(
                    f"{name}: se_earnings on an 1120S K-1 ignored — S-corporation "
                    "income is not self-employment income.")
        else:
            se_earn = ctx.num(k.get("se_earnings"), f"{p}.se_earnings",
                              allow_negative=True)
        if owner is None:
            if se_earn:
                ctx.missing.append(f"{p}.owner")
                ctx.bounds.append(
                    f"{p} has no owner on a joint return, so its SE earnings were "
                    "not netted against a W-2 wage base — SE tax is an upper bound.")
            owner = UNATTRIBUTED
        wages, ubia, sstb = k.get("qbi_w2_wages"), k.get("qbi_ubia"), k.get("sstb")
        for key, v in (("qbi_w2_wages", wages), ("qbi_ubia", ubia)):
            if key in k and v is None:
                ctx.missing.append(f"{p}.{key}")
            elif v is not None:
                ctx.num(v, f"{p}.{key}")
        if None in (ordinary_inc, gp, interest, dividends, qbi_income, se_earn):
            continue
        out.append({"business": name, "entity": name, "form": form, "owner": owner,
                    "ordinary_business_income": ordinary_inc,
                    "guaranteed_payments": gp, "interest": interest,
                    "dividends": dividends, "distributions": dist,
                    "se_earnings": se_earn, "net": qbi_income,
                    "se_base": min(se_earn, max(0.0, ordinary_inc)),
                    "sstb": sstb, "w2_wages": wages, "ubia": ubia})
        ctx.documents.append(f"Schedule K-1 ({form}) — {name}")
        if dividends:
            ctx.findings.append(
                f"{name}: ${dividends:,.0f} of K-1 dividends taxed as ordinary — the "
                "k1 entry does not split out qualified dividends, so tax is an "
                "upper bound if some are qualified.")
        if dist:
            ctx.findings.append(
                f"{name}: ${dist:,.0f} of distributions are informational here — "
                "they are tax-free only up to basis, which the entity skill "
                "(llc-tax-return) tracks.")
        if ordinary_inc < 0:
            ctx.findings.append(
                f"{name}: K-1 loss of ${-ordinary_inc:,.0f} allowed on the "
                "assumption that basis and at-risk amounts cover it (Form 7203 / "
                "Form 6198) — the entity skill must confirm.")
    return out


def _se_tax(ctx: _Ctx, businesses: list[dict], w2: list[dict], tps: list[dict],
            wage_base: float) -> dict:
    """Schedule SE per owner, coordinating the OASDI base with W-2 SS wages."""
    by_owner: dict[str, float] = {}
    for b in businesses:
        by_owner[b["owner"]] = by_owner.get(b["owner"], 0.0) + b["net"]
    result = {}
    for owner, net in by_owner.items():
        earnings = max(0.0, net) * SE_EARNINGS_FACTOR
        if earnings < SE_MINIMUM_EARNINGS:
            if net > 0:
                ctx.findings.append(
                    f"{owner}: net self-employment earnings ${earnings:,.0f} are "
                    f"under ${SE_MINIMUM_EARNINGS:,.0f} — no SE tax.")
            result[owner] = {"earnings": earnings, "oasdi": 0.0, "medicare": 0.0,
                             "tax": 0.0}
            continue
        ss_wages = 0.0
        for i, w in enumerate(w2):
            wo = _owner_of(w, tps)
            if wo is None:
                ctx.missing.append(f"w2[{i}].owner")
                ctx.bounds.append(
                    f"w2[{i}] has no owner, so its Social Security wages were not "
                    f"netted against {owner}'s SE wage base — SE tax is an upper bound.")
                continue
            if wo != owner:
                continue
            ss = ctx.num(w.get("ss_wages"), f"w2[{i}].ss_wages", stop=False)
            if ss is None:
                ctx.bounds.append(
                    f"w2[{i}].ss_wages unknown — SE tax for {owner} is an upper bound.")
                continue
            ss_wages += ss
        oasdi_base = max(0.0, min(earnings, wage_base - ss_wages))
        oasdi = oasdi_base * SE_OASDI_RATE
        medicare = earnings * SE_MEDICARE_RATE
        if ss_wages and oasdi_base < earnings:
            ctx.findings.append(
                f"{owner}: W-2 Social Security wages of ${ss_wages:,.0f} count "
                f"first against the ${wage_base:,.0f} wage base — SE tax charges "
                f"the 12.4% OASDI on only ${oasdi_base:,.0f} of ${earnings:,.0f} "
                "SE earnings.")
        elif oasdi_base < earnings:
            ctx.findings.append(
                f"{owner}: SE earnings of ${earnings:,.0f} exceed the "
                f"${wage_base:,.0f} wage base — OASDI stops there; the 2.9% "
                "Medicare share applies to all of it.")
        result[owner] = {"earnings": earnings, "oasdi": oasdi, "medicare": medicare,
                         "tax": oasdi + medicare}
    return result


def _hsa(ctx: _Ctx, tr: dict, tps: list[dict], box12_w: float, lim) -> dict:
    """Form 8889 for one HSA account holder (``hsa.owner``)."""
    zero = {"deduction": 0.0, "excess": 0.0, "taxable": 0.0, "additional_tax": 0.0,
            "limit": None}
    h = _section(ctx, tr, "hsa", "Form 8889: coverage, contributions, distributions",
                 stop=True)
    if h is None:
        return zero
    if not h:
        if box12_w:
            ctx.findings.append(
                f"W-2 box 12 code W shows ${box12_w:,.0f} of HSA contributions but "
                "no hsa block is recorded — Form 8889 is required.")
            ctx.missing.append("hsa (Form 8889: coverage, contributions, distributions)")
            ctx.bounds.append("HSA not recorded although W-2 box 12 code W shows "
                              "contributions — no deduction or excess computed.")
        return zero
    ctx.forms.add("Form 8889")
    ctx.documents.append("Form 5498-SA and 1099-SA (HSA contributions and distributions)")
    owner = _owner_of(h, tps)
    owner_age = _age_of(owner, tps) if owner else None
    if owner is None:
        ctx.missing.append("hsa.owner")
    personal = ctx.opt(h, "contributions_personal", "hsa.contributions_personal",
                       stop=False)
    employer = h.get("employer_contributions")
    if employer is None:
        employer = box12_w
        if box12_w:
            ctx.findings.append(
                f"HSA employer contributions taken from W-2 box 12 code W "
                f"(${box12_w:,.0f}).")
    else:
        employer = ctx.num(employer, "hsa.employer_contributions")
        if employer is not None and box12_w and abs(employer - box12_w) > 1:
            ctx.findings.append(
                f"HSA employer contributions ${employer:,.0f} disagree with W-2 "
                f"box 12 code W ${box12_w:,.0f} — box W includes pre-tax payroll "
                "contributions you made through a cafeteria plan.")
    months = 12.0
    if "eligible_months" in h:
        months = ctx.num(h["eligible_months"], "hsa.eligible_months", stop=False)
        if months is not None and not 0 <= months <= 12:
            raise FederalReturnError("hsa.eligible_months must be between 0 and 12")
    coverage = h.get("coverage")
    out = dict(zero)
    ages = [t.get("age") or 0 for t in tps]
    if (personal or employer) and coverage not in ("self", "family"):
        ctx.missing.append("hsa.coverage")
        ctx.bounds.append("HSA coverage unknown — no HSA deduction taken; tax is "
                          "an upper bound.")
    elif (personal or employer) and months is None:
        ctx.bounds.append("HSA eligible months unknown — no HSA deduction taken; "
                          "tax is an upper bound.")
    elif coverage in ("self", "family") and lim.known:
        catch = lim.hsa_catch_up_55 or 0
        if coverage == "family":
            # §223(b)(3), (b)(5): each spouse 55+ may add a catch-up to his or
            # her own HSA under family coverage.
            n_catch = sum(1 for a in ages if a >= _lim.HSA_CATCH_UP_AGE)
        elif owner_age is not None:
            n_catch = 1 if owner_age >= _lim.HSA_CATCH_UP_AGE else 0
        elif all(a >= _lim.HSA_CATCH_UP_AGE for a in ages):
            n_catch = 1
        else:
            n_catch = 0
            if any(a >= _lim.HSA_CATCH_UP_AGE for a in ages):
                ctx.bounds.append("hsa.owner unknown on self-only coverage — no "
                                  "age-55 catch-up allowed; tax is an upper bound.")
        base = _lim.hsa_space(coverage, None, lim) or 0
        # §223(b)(2): the limit accrues monthly (the last-month rule and its
        # testing period are not modelled).
        limit = (base + n_catch * catch) * months / 12
        out["limit"] = limit
        if personal is None:
            ctx.bounds.append("HSA personal contributions unknown — no deduction "
                              "taken; tax is an upper bound.")
        else:
            out["deduction"] = max(0.0, min(personal, limit - (employer or 0.0)))
            excess = personal + (employer or 0.0) - limit
            if excess > 0:
                out["excess"] = excess
                ctx.findings.append(
                    f"HSA contributions exceed the ${limit:,.0f} {coverage} limit "
                    f"by ${excess:,.0f} — withdraw the excess and its earnings "
                    "before the filing deadline or owe the 6% excise (Form 5329) "
                    "every year it stays.")
        if coverage == "family" and n_catch:
            ctx.findings.append(
                "The age-55 HSA catch-up is per person and must go into each "
                "older spouse's own HSA.")
        if months < 12:
            ctx.findings.append(f"HSA limit prorated to {months:g} eligible months.")
    elif coverage in ("self", "family"):
        ctx.bounds.append(f"No HSA limit on file for {lim.year} — no deduction taken.")
    dist = ctx.opt(h, "distributions", "hsa.distributions", stop=True) or 0.0
    qualified = ctx.opt(h, "qualified_expenses", "hsa.qualified_expenses") or 0.0
    taxable = max(0.0, dist - qualified)
    if taxable:
        out["taxable"] = taxable
        # §223(f)(4)(C): the additional tax turns on the account beneficiary's age.
        if owner_age is not None:
            young = owner_age < HSA_PENALTY_FREE_AGE
        else:
            young = any(a < HSA_PENALTY_FREE_AGE for a in ages)
            if young and not all(a < HSA_PENALTY_FREE_AGE for a in ages):
                ctx.bounds.append("hsa.owner unknown — the 20% additional tax is "
                                  "charged; tax is an upper bound.")
        if young:
            out["additional_tax"] = taxable * HSA_ADDITIONAL_TAX_RATE
        ctx.findings.append(
            f"HSA distributions exceed qualified expenses by ${taxable:,.0f}: "
            "taxable" + (", plus the 20% additional tax" if young else "") + ".")
    return out


def _iras(ctx: _Ctx, tr: dict, tps: list[dict], lim) -> dict:
    """IRA entries aggregated per owner — Form 8606 works per person, not per
    account. Returns per-owner totals; the deduction and the pro-rata rule are
    applied by :func:`_ira_deduction` and :func:`_form_8606`."""
    owners: dict[str, dict] = {}
    for i, a in enumerate(_list(ctx, tr, "ira", "Forms 5498 / 1099-R / prior 8606")):
        p = f"ira[{i}]"
        if a.get("distributions"):
            raise FederalReturnError(
                f"out of scope — {p}.distributions: IRA distributions other than "
                "Roth conversions (Form 1099-R) are not modelled")
        owner = _owner_of(a, tps)
        if owner is None:
            ctx.missing.append(f"{p}.owner")
            ctx.stop.append(f"{p}.owner")
            continue
        o = owners.setdefault(owner, {"deductible": 0.0, "nondeductible": 0.0,
                                      "prior": 0.0, "prior_entries": 0, "conv": 0.0,
                                      "balance": 0.0, "balance_paths": []})
        contrib = ctx.opt(a, "traditional_contributions",
                          f"{p}.traditional_contributions") or 0.0
        o["deductible" if a.get("deductible") else "nondeductible"] += contrib
        prior = ctx.opt(a, "nondeductible_basis_prior", f"{p}.nondeductible_basis_prior")
        if prior:
            o["prior_entries"] += 1
        o["prior"] += prior or 0.0
        o["conv"] += ctx.opt(a, "conversions_to_roth", f"{p}.conversions_to_roth") or 0.0
        o["balance_paths"].append((p, a.get("year_end_traditional_balance"),
                                   "year_end_traditional_balance" in a))
    for owner, o in owners.items():
        if o["prior_entries"] > 1:
            raise FederalReturnError(
                f"{owner}: nondeductible_basis_prior appears on more than one ira "
                "entry — basis is per person (last year's Form 8606 line 14); give "
                "it once")
        space = _lim.ira_space(_age_of(owner, tps), lim)
        total = o["deductible"] + o["nondeductible"]
        if space is not None and total > space:
            ctx.findings.append(
                f"{owner}: IRA contributions ${total:,.0f} exceed the "
                f"${space:,.0f} limit — the excess draws a 6% excise each year "
                "until removed.")
        o["space"] = space
        if o["conv"]:
            for p, v, present in o["balance_paths"]:
                b = ctx.num(v if present else None, f"{p}.year_end_traditional_balance")
                o["balance"] += b or 0.0
    return owners


def _covered(owner: str | None, tps: list[dict], deferrals: dict) -> bool | None:
    """Active participant in a workplace plan (§219(g)(5)): recorded on the
    taxpayer, else evidenced by W-2 elective deferrals; otherwise unknown."""
    for t in tps:
        if t.get("member") == owner or (len(tps) == 1 and owner in (None, "taxpayer")):
            v = t.get("covered_by_workplace_plan")
            if v is not None:
                return bool(v)
    if deferrals.get(owner):
        return True
    return None


def _ira_deduction(ctx: _Ctx, owners: dict, tps: list[dict], status: str,
                   magi: float, table: FederalYear, deferrals: dict,
                   apart: bool | None) -> float:
    """§219(g): the deductible part of contributions marked ``deductible``.
    The rest becomes Form 8606 basis. ``magi`` excludes Roth conversions."""
    total = 0.0
    for owner, o in owners.items():
        want = o["deductible"]
        if not want:
            continue
        cap = min(want, o["space"]) if o["space"] is not None else want
        me = _covered(owner, tps, deferrals)
        spouse = None
        if status == "mfj":
            other = next((t.get("member") for t in tps if t.get("member") != owner), None)
            spouse = _covered(other, tps, deferrals)
        unknown = me is None or (status == "mfj" and not me and spouse is None)
        if unknown:
            ctx.missing.append(f"taxpayers[].covered_by_workplace_plan ({owner})")
            ctx.bounds.append(
                f"{owner}: workplace-plan coverage unknown — no IRA deduction "
                "taken; the contribution is treated as nondeductible basis and "
                "tax is an upper bound.")
            allowed = 0.0
        else:
            rng = None
            if me:
                if status in ("mfj", "qss"):
                    rng = table.ira_deduction_phaseout["covered_joint"]
                elif status == "mfs" and not apart:
                    rng = table.ira_deduction_phaseout["mfs"]
                else:
                    rng = table.ira_deduction_phaseout["covered_single"]
            elif spouse:
                rng = table.ira_deduction_phaseout["spouse_covered"]
            if rng is None:
                allowed = cap
            else:
                lo, hi = rng
                if magi <= lo:
                    allowed = cap
                elif magi >= hi:
                    allowed = 0.0
                else:
                    limit = (o["space"] or cap) * (hi - magi) / (hi - lo)
                    limit = math.ceil(limit / IRA_DEDUCTION_ROUNDING) * IRA_DEDUCTION_ROUNDING
                    limit = max(limit, IRA_DEDUCTION_MINIMUM)
                    allowed = min(cap, limit)
                if allowed < cap:
                    ctx.findings.append(
                        f"{owner}: IRA deduction limited to ${allowed:,.0f} of "
                        f"${cap:,.0f} — MAGI ${magi:,.0f} against the "
                        f"${lo:,.0f}–${hi:,.0f} phase-out for a workplace-plan "
                        "participant" + ("'s spouse" if not me else "")
                        + "; the rest is nondeductible basis (Form 8606).")
        o["nondeductible"] += want - allowed
        o["deductible_allowed"] = allowed
        total += allowed
    return total


def _form_8606(ctx: _Ctx, owners: dict) -> dict:
    """Pro-rata rule per owner (Form 8606 lines 1-14)."""
    taxable = 0.0
    basis_out: dict[str, float] = {}
    for owner, o in owners.items():
        nd, prior, conv, balance = o["nondeductible"], o["prior"], o["conv"], o["balance"]
        if not (nd or conv or prior):
            continue
        ctx.forms.add("Form 8606")
        ctx.documents.append(f"{owner}: prior-year Form 8606 (basis), Form 5498 "
                             "(Dec 31 value), Form 1099-R (conversion)")
        basis = prior + nd
        if conv:
            denom = balance + conv
            fraction = min(1.0, basis / denom) if denom else 1.0
            nontaxable = conv * fraction
            conv_taxable = conv - nontaxable
            taxable += conv_taxable
            basis -= nontaxable
            if balance > 0:
                ctx.findings.append(
                    f"{owner}: ${balance:,.0f} remained in traditional/SEP/SIMPLE "
                    f"IRAs on Dec 31, so the pro-rata rule made ${conv_taxable:,.0f} "
                    f"of the ${conv:,.0f} conversion taxable and left "
                    f"${basis:,.0f} of basis behind. Rolling pre-tax IRA money "
                    "into a workplace plan before Dec 31 avoids this.")
            elif conv_taxable > 0:
                ctx.findings.append(
                    f"{owner}: ${conv_taxable:,.0f} of the conversion is taxable "
                    "(earnings above basis).")
        basis_out[owner] = basis
    return {"taxable": taxable, "basis": basis_out}


def _qbi(ctx: _Ctx, businesses: list[dict], se: dict, ti_before: float,
         net_cg: float, status: str, table: FederalYear, prior_loss: float) -> tuple[float, float]:
    """§199A deduction and the qualified business loss carried forward."""
    if not businesses:
        return 0.0, 0.0
    rows = []
    for b in businesses:
        s = se.get(b["owner"], {})
        # Share of the owner's SE earnings that this business's QBI produced:
        # Schedule C net, or a partnership's ordinary income (guaranteed
        # payments are SE income but not QBI).
        base = b.get("se_base", b["net"])
        owner_se = s.get("earnings", 0.0) / SE_EARNINGS_FACTOR
        share = min(1.0, base / owner_se) if owner_se > 0 and base > 0 else 0.0
        half = s.get("tax", 0.0) * SE_DEDUCTION_SHARE * share
        rows.append({**b, "qbi": b["net"] - half})
    total = sum(r["qbi"] for r in rows) - prior_loss
    if total <= 0:
        ctx.findings.append(
            f"Net qualified business income is ${total:,.0f}: no §199A deduction, "
            "and the loss carries forward to reduce next year's QBI.")
        return 0.0, -total
    ctx.forms.add("Form 8995" if ti_before <= table.qbi_threshold[_qbi_group(status)]
                  else "Form 8995-A")
    threshold = table.qbi_threshold[_qbi_group(status)]
    rng = table.qbi_phase_in_range[_qbi_group(status)]
    # Spread losses (and any prior-year loss) pro rata over profitable businesses.
    pos = sum(r["qbi"] for r in rows if r["qbi"] > 0)
    for r in rows:
        r["qbi_net"] = r["qbi"] / pos * total if r["qbi"] > 0 else 0.0
    # QBI from businesses that remain "qualified" (§199A(d)(2)-(3)): an SSTB
    # above the phase-in range is not, so it cannot reach the §199A(i) minimum.
    qualified_qbi = total
    if ti_before <= threshold:
        component = QBI_RATE * total
    else:
        frac = min(1.0, (ti_before - threshold) / rng)
        component = 0.0
        for r in rows:
            if r["qbi_net"] <= 0:
                continue
            if r["sstb"] is None or r["w2_wages"] is None or r["ubia"] is None:
                raise FederalReturnError(
                    f"taxable income ${ti_before:,.0f} is above the §199A threshold "
                    f"${threshold:,.0f}: {r['business']} needs sstb, w2_wages and "
                    "ubia (qbi_w2_wages and qbi_ubia on a K-1) to apply the wage "
                    "limit — refusing to guess them")
            qbi, wages, ubia = r["qbi_net"], float(r["w2_wages"]), float(r["ubia"])
            if r["sstb"]:
                if frac >= 1.0:
                    qualified_qbi -= r["qbi_net"]
                    ctx.findings.append(
                        f"{r['business']} is a specified service business and "
                        "taxable income is above the phase-in range — no §199A "
                        "deduction for it.")
                    continue
                applicable = 1.0 - frac
                qbi, wages, ubia = qbi * applicable, wages * applicable, ubia * applicable
            tentative = QBI_RATE * qbi
            limit = max(QBI_WAGE_RATE * wages,
                        QBI_WAGE_RATE_WITH_UBIA * wages + QBI_UBIA_RATE * ubia)
            if frac >= 1.0:
                component += min(tentative, limit)
            elif tentative > limit:
                component += tentative - (tentative - limit) * frac
            else:
                component += tentative
    income_cap = QBI_RATE * max(0.0, ti_before - net_cg)
    deduction = min(component, income_cap)
    if (table.qbi_minimum_deduction is not None
            and qualified_qbi >= (table.qbi_minimum_income or 0)
            and deduction < table.qbi_minimum_deduction):
        deduction = min(table.qbi_minimum_deduction, max(0.0, ti_before))
        ctx.findings.append(
            f"§199A minimum deduction of ${table.qbi_minimum_deduction:,.0f} applied "
            "(requires material participation in the business).")
    return deduction, 0.0


def _brackets_tax(ti: float, brackets) -> float:
    return _cf.progressive_tax(ti, brackets)


def _marginal(ordinary: float, brackets) -> float:
    for rate, upper in brackets:
        if upper is None or ordinary < upper:
            return rate
    return brackets[-1][0]


def _cg_split(pref: float, base: float, zero_max: float, fifteen_max: float):
    """Preferential income stacked on ``base`` ordinary income → (0%, 15%, 20%)."""
    at0 = min(pref, max(0.0, zero_max - base))
    at15 = min(pref - at0, max(0.0, fifteen_max - max(base, zero_max)))
    return at0, at15, pref - at0 - at15


def regular_tax(ti: float, pref: float, status: str, table: FederalYear) -> float:
    """Qualified Dividends and Capital Gain Tax Worksheet."""
    g = _group(status)
    pref = min(max(0.0, pref), ti)
    ordinary = ti - pref
    _, at15, at20 = _cg_split(pref, ordinary, table.cg_zero_max[g], table.cg_fifteen_max[g])
    tax = _brackets_tax(ordinary, table.brackets[g]) + CG_RATE_MID * at15 + CG_RATE_HIGH * at20
    return min(tax, _brackets_tax(ti, table.brackets[g]))


def amt(amti: float, pref: float, regular_ordinary: float, regular: float,
        status: str, table: FederalYear) -> dict:
    """Form 6251: exemption phase-out, 26/28% rates, Part III capital rates."""
    ag = _amt_group(status)
    exemption = max(0.0, table.amt_exemption[ag]
                    - table.amt_phaseout_rate * max(0.0, amti - table.amt_phaseout_start[ag]))
    base = max(0.0, amti - exemption)
    brk = table.amt_28_threshold["mfs" if status == "mfs" else "other"]

    def flat(x: float) -> float:
        return AMT_RATE_LOW * min(x, brk) + AMT_RATE_HIGH * max(0.0, x - brk)

    p = min(max(0.0, pref), base)
    g = _group(status)
    _, at15, at20 = _cg_split(p, regular_ordinary, table.cg_zero_max[g],
                              table.cg_fifteen_max[g])
    tmt = min(flat(base - p) + CG_RATE_MID * at15 + CG_RATE_HIGH * at20, flat(base))
    return {"amti": amti, "exemption": exemption, "taxable": base,
            "tentative_minimum_tax": tmt, "amt": max(0.0, tmt - regular)}


def _ctc_reduction(magi: float, status: str) -> float:
    threshold = CTC_PHASEOUT_THRESHOLD.get(status, CTC_PHASEOUT_THRESHOLD_DEFAULT)
    if magi <= threshold:
        return 0.0
    return CTC_PHASEOUT_PER_STEP * math.ceil((magi - threshold) / CTC_PHASEOUT_STEP)


def taxable_social_security(benefits: float, other_income: float,
                            tax_exempt_interest: float, adjustments: float,
                            group: str) -> float:
    """Form 1040 Social Security Benefits Worksheet, lines 1-18.

    ``group`` is ``mfj``, ``mfs_together`` or anything else (single, head of
    household, qualifying surviving spouse, MFS lived apart all year)."""
    if benefits <= 0:
        return 0.0
    half = SS_TIER1_RATE * benefits                                   # line 2
    provisional = half + other_income + tax_exempt_interest          # line 5
    if adjustments >= provisional:                                    # line 7
        return 0.0
    line7 = provisional - adjustments
    base = SS_BASE_AMOUNT.get(group, SS_BASE_AMOUNT_DEFAULT)
    if base >= line7 and group != "mfs_together":                     # line 9
        return 0.0
    line9 = max(0.0, line7 - base)
    extra = SS_ADJUSTED_BASE_EXTRA.get(group, SS_ADJUSTED_BASE_EXTRA_DEFAULT)
    line11 = max(0.0, line9 - extra)
    line14 = min(half, SS_TIER1_RATE * min(line9, extra))
    return min(line14 + SS_TIER2_RATE * line11, SS_TIER2_RATE * benefits)


def state_refund_taxable(refund: float, *, itemized_prior: bool,
                         itemized_deduction_prior: float = 0.0,
                         standard_deduction_prior: float = 0.0,
                         salt_paid_prior: float = 0.0,
                         salt_deducted_prior: float = 0.0) -> float:
    """Tax-benefit rule for a state or local income tax refund (Pub. 525
    State and Local Income Tax Refund Worksheet, simplified).

    Taxable only to the extent the deduction reduced last year's tax: not
    more than the refund, not more than last year's itemized deductions in
    excess of the standard deduction, and — when the SALT cap bound — not
    more than the SALT deduction in excess of the taxes that would have been
    paid net of the refund."""
    if refund <= 0 or not itemized_prior:
        return 0.0
    excess = max(0.0, itemized_deduction_prior - standard_deduction_prior)
    cap_recovery = max(0.0, salt_deducted_prior - (salt_paid_prior - refund))
    return min(refund, excess, cap_recovery)


# ── the return ───────────────────────────────────────────────────────────


def _foreign(ctx: _Ctx, tr: dict) -> dict:
    """``tax_return.foreign`` routed to its real lines: interest (2b), dividends
    (3a/3b), gains (Schedule D). Rent and unrouteable totals are refused."""
    f = _section(ctx, tr, "foreign", "foreign income and tax", stop=True)
    f = f or {}
    extra = sorted(k for k, v in f.items()
                   if k not in FOREIGN_FIELDS and v not in (None, 0, False, [], {}, ""))
    if extra:
        raise FederalReturnError(
            f"out of scope — foreign {', '.join(extra)}: only foreign interest, "
            "dividends and capital transactions are modelled")
    if "income" in f and f["income"] not in (0, None):
        raise FederalReturnError(
            "foreign.income is not accepted: one total mixes interest, dividends, "
            "gains and rent, which are taxed on different lines and at different "
            "rates. Split it into foreign.interest, foreign.dividends "
            "(+ qualified_dividends), foreign.capital_transactions and foreign.rent")
    if "income" in f and f["income"] is None:
        ctx.missing.append("foreign.income (split into routed fields)")
        ctx.stop.append("foreign.income")
    rent = ctx.opt(f, "rent", "foreign.rent")
    if rent:
        raise FederalReturnError(
            "out of scope — foreign rent is Schedule E part I income with U.S. "
            "depreciation and passive-activity rules; use passive-loss-eligibility "
            "and depreciation-election")
    interest = ctx.opt(f, "interest", "foreign.interest") or 0.0
    dividends = ctx.opt(f, "dividends", "foreign.dividends") or 0.0
    qd = ctx.opt(f, "qualified_dividends", "foreign.qualified_dividends", stop=False)
    if qd is None:
        if dividends:
            ctx.bounds.append("foreign.qualified_dividends unknown — all foreign "
                              "dividends taxed as ordinary; tax is an upper bound.")
        qd = 0.0
    if qd > dividends:
        raise FederalReturnError("foreign.qualified_dividends exceed foreign.dividends")
    rows = f.get("capital_transactions", [])
    if rows is None:
        ctx.missing.append("foreign.capital_transactions")
        ctx.stop.append("foreign.capital_transactions")
        rows = []
    if not isinstance(rows, list):
        raise FederalReturnError("foreign.capital_transactions must be a list")
    ftp = f.get("foreign_tax_paid", 0)
    passive_tax: float = 0.0
    if ftp is None:
        ctx.missing.append("foreign.foreign_tax_paid")
        ctx.bounds.append("foreign.foreign_tax_paid unknown — no foreign tax credit "
                          "taken for it; tax is an upper bound.")
    elif isinstance(ftp, dict):
        pt = ctx.opt(ftp, "passive", "foreign.foreign_tax_paid.passive", stop=False)
        if pt is None:
            ctx.bounds.append("foreign.foreign_tax_paid.passive unknown — no foreign "
                              "tax credit taken for it; tax is an upper bound.")
        passive_tax = pt or 0.0
        gt = ctx.opt(ftp, "general", "foreign.foreign_tax_paid.general")
        if gt:
            raise FederalReturnError(
                "out of scope — general-category foreign tax (foreign earned or "
                "business income); use feie-vs-ftc")
    else:
        passive_tax = ctx.num(ftp, "foreign.foreign_tax_paid", stop=False) or 0.0
    category = f.get("category", "passive")
    if "category" in f and category is None:
        ctx.missing.append("foreign.category")
        ctx.stop.append("foreign.category")
    elif category != "passive" and (interest or dividends or rows or passive_tax):
        raise FederalReturnError(
            f"out of scope — foreign income in the {category!r} category; use "
            "feie-vs-ftc for foreign earned income")
    has_income = bool(interest or dividends or rows)
    present = bool(f.get("country") or f.get("accounts") or has_income or passive_tax)
    return {"interest": interest, "dividends": dividends, "qualified": qd,
            "rows": rows, "tax": passive_tax, "has_income": has_income,
            "present": present, "reported_on_1099": bool(f.get("reported_on_1099")),
            "country": f.get("country")}


def compute(tr: dict) -> FederalReturn:
    """Compute Form 1040 from a ``tax_return`` block. Raises
    :class:`FederalReturnError` (with ``.missing``) when a figure that
    determines tax is unknown, the input is malformed, or the return is out
    of scope."""
    try:
        return _compute(tr)
    except FederalReturnError:
        raise
    except (TypeError, ValueError, AttributeError, KeyError) as e:
        raise FederalReturnError(f"malformed tax_return input: {e}") from e


def _compute(tr: dict) -> FederalReturn:
    if not isinstance(tr, dict):
        raise FederalReturnError("tax_return block is missing")
    _check_scope(tr)
    ctx = _Ctx()
    try:
        year = int(tr.get("tax_year"))
    except (TypeError, ValueError) as e:
        raise FederalReturnError("tax_year is required, e.g. 2026") from e
    status = tr.get("filing_status")
    if status not in FILING_STATUSES:
        raise FederalReturnError(
            f"filing_status must be one of {', '.join(FILING_STATUSES)}")
    table, projection = table_for(year)
    g = _group(status)
    if projection:
        ctx.findings.append(
            f"No {year} parameter table ships with this module — {table.tax_year} "
            "brackets, deductions and thresholds are used. Treat every figure as "
            "a projection until the year's revenue procedure is added.")
    wage_base, wb_proj = _aid.wage_base_for(year)
    lim = _lim.for_year(year)
    if not lim.known:
        lim = _lim.for_year(table.tax_year)
    tps = _taxpayers(ctx, tr, status)
    ctx.forms.add("Form 1040")
    apart = tr.get("mfs_lived_apart_all_year")

    # Wages (line 1a)
    w2 = _list(ctx, tr, "w2", "Form W-2")
    wages = fed_wh = medicare_wages = medicare_wh = 0.0
    wh_known = True
    box12 = {"D": 0.0, "W": 0.0, "AA": 0.0}
    supplemental = 0.0
    sdi = 0.0
    deferrals: dict[str, float] = {}
    ss_by_owner: dict[str, dict[str, float]] = {}
    for i, w in enumerate(w2):
        p = f"w2[{i}]"
        emp = w.get("employer", p)
        ctx.documents.append(f"Form W-2 — {emp}")
        x = ctx.num(w.get("wages"), f"{p}.wages")
        wages += x or 0.0
        fw = ctx.num(w.get("federal_withheld"), f"{p}.federal_withheld", stop=False)
        if fw is None:
            wh_known = False
        fed_wh += fw or 0.0
        mw = ctx.num(w.get("medicare_wages"), f"{p}.medicare_wages", stop=False)
        if mw is None:
            mw = x or 0.0
            ctx.bounds.append(f"{p}.medicare_wages unknown — box 1 wages used for "
                              "Form 8959.")
        medicare_wages += mw
        mwh = ctx.num(w.get("medicare_withheld"), f"{p}.medicare_withheld", stop=False)
        if mwh is None:
            mwh = mw * EMPLOYEE_MEDICARE_RATE
            ctx.bounds.append(f"{p}.medicare_withheld unknown — no Additional "
                              "Medicare withholding credited; refund is a lower bound.")
        medicare_wh += mwh
        sd = ctx.opt(w, "sdi_withheld", f"{p}.sdi_withheld", stop=False)
        if sd is None:
            ctx.bounds.append(f"{p}.sdi_withheld unknown — left out of state and "
                              "local taxes; itemized deductions are a lower bound.")
        sdi += sd or 0.0
        b12 = _section(ctx, w, "box12", "W-2 box 12", stop=False, path=f"{p}.box12")
        owner = _owner_of(w, tps)
        if b12 is None:
            b12 = {}
            ctx.bounds.append(f"{p}.box12 unknown — HSA employer contributions and "
                              "deferral limits not checked.")
        for code in box12:
            v = ctx.num(b12.get(code, 0), f"{p}.box12.{code}", stop=False)
            box12[code] += v or 0.0
            if code in ("D", "AA"):
                deferrals[owner] = deferrals.get(owner, 0.0) + (v or 0.0)
        sup = w.get("supplemental_wages", w.get("rsu_income"))
        if sup is not None:
            supplemental += ctx.num(sup, f"{p}.supplemental_wages", stop=False) or 0.0
        if w.get("ss_withheld") is not None:
            ssw = ctx.num(w.get("ss_withheld"), f"{p}.ss_withheld", stop=False) or 0.0
            emps = ss_by_owner.setdefault(owner, {})
            emps[str(emp)] = emps.get(str(emp), 0.0) + ssw
    for owner, d in deferrals.items():
        if owner is None or not lim.known or not d:
            continue
        cap = (lim.elective_deferral or 0) + _lim.catch_up_for_age(_age_of(owner, tps), lim)
        if d > cap:
            ctx.findings.append(
                f"{owner}: elective deferrals (box 12 D + AA) of ${d:,.0f} exceed "
                f"the ${cap:,.0f} limit — the excess must be distributed by Apr 15 "
                "or it is taxed twice.")
    # Excess Social Security withholding (two or more *different* employers)
    excess_ss = 0.0
    ss_cap = wage_base * EMPLOYEE_OASDI_RATE
    for owner, emps in ss_by_owner.items():
        total_ss = sum(emps.values())
        if owner is not None and len(emps) > 1 and total_ss > ss_cap:
            excess_ss += total_ss - ss_cap
            ctx.findings.append(
                f"{owner}: {len(emps)} employers withheld ${total_ss:,.0f} of Social "
                f"Security tax against a ${ss_cap:,.0f} maximum — the "
                f"${total_ss - ss_cap:,.0f} excess is refundable (Schedule 3).")
        elif owner is not None and total_ss > ss_cap + 1:
            ctx.findings.append(
                f"{owner}: one employer withheld ${total_ss:,.0f} of Social Security "
                "tax, above the maximum — the employer must refund it; it is not a "
                "credit on the return.")

    # Interest and dividends (lines 2a/2b, 3a/3b)
    interest = treasury = exempt = 0.0
    for i, it in enumerate(_list(ctx, tr, "interest", "Form 1099-INT")):
        p = f"interest[{i}]"
        ctx.documents.append(f"Form 1099-INT — {it.get('payer', p)}")
        interest += ctx.num(it.get("amount"), f"{p}.amount") or 0.0
        treasury += ctx.opt(it, "us_treasury", f"{p}.us_treasury") or 0.0
        exempt += ctx.opt(it, "tax_exempt", f"{p}.tax_exempt") or 0.0
    taxable_interest = interest + treasury
    ordinary = qualified = cgd = div_ftax = div_foreign_src = 0.0
    div_src_unknown = False
    for i, d in enumerate(_list(ctx, tr, "dividends", "Form 1099-DIV")):
        p = f"dividends[{i}]"
        for bad in UNSUPPORTED_DIVIDEND_FIELDS:
            if d.get(bad):
                raise FederalReturnError(
                    f"out of scope — {p}.{bad}: §199A REIT dividends and "
                    "§1250/collectibles/§1202 gain are not modelled")
        ctx.documents.append(f"Form 1099-DIV — {d.get('payer', p)}")
        o = ctx.num(d.get("ordinary"), f"{p}.ordinary") or 0.0
        q = ctx.opt(d, "qualified", f"{p}.qualified") or 0.0
        if q > o:
            raise FederalReturnError(f"{p}: qualified dividends exceed ordinary dividends")
        ordinary += o
        qualified += q
        cgd += ctx.opt(d, "capital_gain_distributions", f"{p}.capital_gain_distributions") or 0.0
        ft = ctx.opt(d, "foreign_tax_paid", f"{p}.foreign_tax_paid", stop=False) or 0.0
        div_ftax += ft
        src = ctx.opt(d, "foreign_source_income", f"{p}.foreign_source_income", stop=False)
        if ft and ("foreign_source_income" not in d or src is None):
            div_src_unknown = True
        div_foreign_src += src or 0.0
    # K-1s (Schedule E part II); their interest and dividends join lines 2b/3b
    k1s = _k1s(ctx, tr, tps, status)
    k1_income = sum(k["ordinary_business_income"] + k["guaranteed_payments"] for k in k1s)
    taxable_interest += sum(k["interest"] for k in k1s)
    ordinary += sum(k["dividends"] for k in k1s)
    if k1s:
        ctx.forms.update({"Schedule E", "Schedule 1"})
    # Foreign income, routed to its lines
    fx = _foreign(ctx, tr)
    taxable_interest += fx["interest"]
    ordinary += fx["dividends"]
    qualified += fx["qualified"]
    if taxable_interest > SCHEDULE_B_THRESHOLD or ordinary > SCHEDULE_B_THRESHOLD:
        ctx.forms.add("Schedule B")
    if fx["present"]:
        ctx.forms.add("Schedule B")
        ctx.findings.append(
            "Foreign income or accounts are present: Schedule B Part III (foreign "
            "accounts and trusts) must be completed whatever the amounts; check "
            "FBAR (FinCEN 114) and Form 8938 with foreign-reporting-audit — "
            "neither is computed here, and the penalties are independent of tax owed.")
    if fx["has_income"]:
        ctx.documents.append("Foreign bank and broker statements for the U.S. calendar "
                             "year, converted to USD")
    if treasury:
        ctx.findings.append(
            f"${treasury:,.0f} of U.S. Treasury interest is federally taxable but "
            "exempt from state income tax — carried for the state return.")
    if exempt:
        ctx.findings.append(
            f"${exempt:,.0f} of tax-exempt interest is reported (line 2a) but not "
            "taxed; private-activity bond interest would be an AMT preference.")

    # Capital gains (line 7)
    cap = _capital(ctx, tr, cgd, fx["rows"])
    st, lt = cap["st"], cap["lt"]
    net_cap = st + lt
    loss_limit = CAPITAL_LOSS_LIMIT.get(status, CAPITAL_LOSS_LIMIT_DEFAULT)
    cap_in_income = net_cap if net_cap >= 0 else -min(loss_limit, -net_cap)
    if (tr.get("capital_transactions") or fx["rows"] or cgd or cap["st_carry_in"]
            or cap["lt_carry_in"]):
        ctx.forms.add("Schedule D")
        if tr.get("capital_transactions") or fx["rows"]:
            ctx.forms.add("Form 8949")
        if tr.get("capital_transactions"):
            ctx.documents.append("Form 1099-B (each broker)")
    net_capital_gain = max(0.0, min(lt, net_cap))

    # Schedule C, SE tax
    businesses = _schedule_c(ctx, tr, tps)
    sc_net = sum(b["net"] for b in businesses)
    if businesses:
        ctx.forms.update({"Schedule C", "Schedule 1"})
    business_net = sc_net + sum(k["ordinary_business_income"] for k in k1s)
    ebl = table.excess_business_loss[_joint(status)]
    if -business_net > ebl:
        raise FederalReturnError(
            f"out of scope — a business loss of ${-business_net:,.0f} exceeds the "
            f"${ebl:,.0f} excess business loss threshold (§461(l), Form 461)")
    se_rows = businesses + [{"owner": k["owner"], "net": k["se_earnings"]}
                            for k in k1s if k["form"] == "1065"]
    se = _se_tax(ctx, se_rows, w2, tps, wage_base) if se_rows else {}
    se_tax = sum(v["tax"] for v in se.values())
    se_earnings = sum(v["earnings"] for v in se.values() if v["tax"])
    if se_tax:
        ctx.forms.update({"Schedule SE", "Schedule 2"})
    half_se = se_tax * SE_DEDUCTION_SHARE

    # HSA, IRA
    hsa = _hsa(ctx, tr, tps, box12["W"], lim)
    ira_owners = _iras(ctx, tr, tps, lim)
    wants_ira_deduction = any(o["deductible"] for o in ira_owners.values())

    # Dependents and kiddie-tax detection
    deps = _list(ctx, tr, "dependents", "dependents", stop=False)
    if deps is None:
        ctx.bounds.append("dependents not recorded — no child or dependent credit "
                          "taken; tax is an upper bound.")
        deps = []
    for i, d in enumerate(deps):
        if d.get("unearned_income"):
            ctx.findings.append(
                f"{d.get('member', f'dependents[{i}]')} has unearned income: the "
                "child may need a return with Form 8615 (kiddie tax) or a Form 8814 "
                "election — not computed here.")

    # Social Security benefits (SSA-1099 box 5); withholding is box 6
    ss_benefits = 0.0
    ss_withheld: float | None = 0.0
    for i, b in enumerate(_list(ctx, tr, "social_security_benefits", "Form SSA-1099")):
        p = f"social_security_benefits[{i}]"
        ctx.documents.append(f"Form SSA-1099 — {b.get('recipient', p)}")
        ss_benefits += ctx.num(b.get("net_benefits"), f"{p}.net_benefits",
                               allow_negative=True) or 0.0
        sw = ctx.num(b.get("federal_withheld", 0), f"{p}.federal_withheld", stop=False)
        if sw is None:
            ctx.bounds.append(f"{p}.federal_withheld unknown — refund or balance "
                              "due cannot be determined.")
            ss_withheld = None
        elif ss_withheld is not None:
            ss_withheld += sw
    ss_group = "other"
    if ss_benefits > 0:
        if status == "mfj":
            ss_group = "mfj"
        elif status == "mfs":
            if apart is None:
                ctx.missing.append("mfs_lived_apart_all_year")
                ctx.stop.append("mfs_lived_apart_all_year (decides the Social "
                                "Security base amount on an MFS return)")
            ss_group = "other" if apart else "mfs_together"
        if wants_ira_deduction:
            raise FederalReturnError(
                "out of scope — a deductible IRA contribution alongside Social "
                "Security benefits needs the Pub. 590-A circular worksheet")
    elif ss_benefits < 0:
        ctx.findings.append(
            "Net Social Security benefits are negative (repayment exceeded "
            "benefits): the repayment may be deductible or a §1341 credit — "
            "not computed.")
        ss_benefits = 0.0

    # Prior year: state/local refund (tax-benefit rule) and safe-harbor inputs
    py = _section(ctx, tr, "prior_year", "last year's return", stop=False)
    if py is None:
        py = {}
    refund_in = 0.0
    refund_args: dict | None = None
    if "state_refund_received" in py:
        refund_in = ctx.num(py["state_refund_received"],
                            "prior_year.state_refund_received")
        if refund_in:
            item_prior = py.get("itemized_prior")
            if item_prior is None:
                ctx.missing.append("prior_year.itemized_prior")
                ctx.stop.append("prior_year.itemized_prior (decides whether the "
                                "state refund is taxable)")
            elif item_prior:
                refund_args = {"itemized_prior": True}
                for k in ("itemized_deduction_prior", "standard_deduction_prior",
                          "salt_paid_prior", "salt_deducted_prior"):
                    refund_args[k] = ctx.num(py.get(k), f"prior_year.{k}")
            else:
                refund_args = {"itemized_prior": False}
        refund_in = refund_in or 0.0
    prior_qbi_loss = ctx.num(tr.get("qbi_loss_carryforward", 0), "qbi_loss_carryforward")

    if ctx.stop:
        raise FederalReturnError(
            "cannot compute the return without: " + ", ".join(sorted(set(ctx.stop))),
            missing=sorted(set(ctx.missing)))
    prior_qbi_loss = prior_qbi_loss or 0.0

    refund_taxable = state_refund_taxable(refund_in, **refund_args) if refund_args else 0.0
    if refund_in:
        ctx.documents.append("Form 1099-G (state or local income tax refund)")
        ctx.findings.append(
            f"State/local refund of ${refund_in:,.0f}: ${refund_taxable:,.0f} is "
            "taxable under the tax-benefit rule"
            + (" (last year's standard deduction means none of it is)."
               if refund_args and not refund_args["itemized_prior"] else
               " (limited to what the deduction actually saved last year)."))
    if refund_taxable:
        ctx.forms.add("Schedule 1")
    income_before_ira = (wages + taxable_interest + ordinary + cap_in_income + sc_net
                         + k1_income + hsa["taxable"] + refund_taxable)
    # §219(g)(3)(A) / Pub. 590-A: MAGI for the IRA deduction excludes Roth
    # conversion income, so the deduction is settled before Form 8606.
    ira_magi = income_before_ira - hsa["deduction"] - half_se
    ira_deduction = _ira_deduction(ctx, ira_owners, tps, status, ira_magi, table,
                                   deferrals, apart)
    ira = _form_8606(ctx, ira_owners)
    other_income = income_before_ira + ira["taxable"]
    adjustments = {"hsa_deduction": hsa["deduction"], "half_se_tax": half_se,
                   "ira_deduction": ira_deduction}
    if any(adjustments.values()):
        ctx.forms.add("Schedule 1")
    taxable_ss = taxable_social_security(ss_benefits, other_income, exempt,
                                         sum(adjustments.values()), ss_group)
    if ss_benefits > 0:
        ctx.findings.append(
            f"${taxable_ss:,.0f} of ${ss_benefits:,.0f} Social Security benefits "
            f"is taxable ({taxable_ss / ss_benefits:.0%}; the ceiling is 85%).")
    total_income = other_income + taxable_ss
    agi = total_income - sum(adjustments.values())
    magi = agi  # no excluded foreign earned income is modelled

    # Senior deduction (2025-2028)
    seniors = sum(1 for t in tps if (t.get("age") or 0) >= SENIOR_AGE)
    senior = 0.0
    if seniors and year in SENIOR_DEDUCTION_YEARS:
        if status == "mfs":
            ctx.findings.append("The 65+ senior deduction is not available on a "
                                "married-filing-separately return.")
        else:
            thr = SENIOR_DEDUCTION_THRESHOLD.get(status, SENIOR_DEDUCTION_THRESHOLD_DEFAULT)
            per = max(0.0, SENIOR_DEDUCTION_AMOUNT
                      - SENIOR_DEDUCTION_PHASEOUT_RATE * max(0.0, magi - thr))
            senior = per * seniors
            if senior:
                ctx.forms.add("Schedule 1-A")

    # Standard deduction
    boxes = sum((1 if (t.get("age") or 0) >= SENIOR_AGE else 0) + (1 if t.get("blind") else 0)
                for t in tps)
    add = (table.additional_standard_unmarried if status in ("single", "hoh")
           else table.additional_standard_married)
    standard = table.standard_deduction[g] + boxes * add
    must_itemize = False
    if status == "mfs":
        spouse_itemizes = tr.get("spouse_itemizes")
        if spouse_itemizes is None:
            ctx.missing.append("spouse_itemizes")
            ctx.bounds.append("Married filing separately and spouse_itemizes not "
                              "recorded — if the spouse itemizes, the standard "
                              "deduction is zero (§63(c)(6)(A)) and tax is understated.")
        elif spouse_itemizes:
            must_itemize = True
            standard = 0.0
            ctx.findings.append("The spouse itemizes on a separate return, so this "
                                "return must itemize too (§63(c)(6)(A)).")

    # Itemized deductions (reuse cashflow rules)
    rules = itemized_rules(status, table)
    it = _section(ctx, tr, "itemized", "Schedule A amounts", stop=False)
    it_unknown = []
    if it is None:
        it_unknown.append("itemized (whole section)")
        it = {}

    def item(key: str) -> float:
        v = ctx.opt(it, key, f"itemized.{key}", stop=False)
        if v is None:
            it_unknown.append(key)
            return 0.0
        return v

    medical = item("medical")
    prop = item("property_tax")
    other_salt = item("other_state_local_taxes")
    mort = item("mortgage_interest")
    cash_gifts = item("charitable_cash")
    noncash = item("charitable_noncash")
    mort_bal = it.get("mortgage_balance")
    if mort and mort_bal is None:
        raise FederalReturnError(
            "itemized.mortgage_interest needs itemized.mortgage_balance (Form 1098 "
            "box 2) for the acquisition-debt limit",
            missing=sorted(set(ctx.missing + ["itemized.mortgage_balance"])))
    mort_bal = ctx.num(mort_bal, "itemized.mortgage_balance") if mort_bal is not None else None
    state_paid = tr.get("state_income_tax_paid")
    if state_paid is None:
        state_wh = 0.0
        for i, w in enumerate(w2):
            v = ctx.num(w.get("state_withheld", 0), f"w2[{i}].state_withheld", stop=False)
            if v is None:
                it_unknown.append(f"w2[{i}].state_withheld")
            state_wh += v or 0.0
        est_s = _section(ctx, tr, "estimated_payments", "estimated payments",
                         stop=False) or {}
        est_state = est_s.get("state", [])
        if est_state is None:
            it_unknown.append("estimated_payments.state")
            est_state = []
        if not isinstance(est_state, list):
            raise FederalReturnError("estimated_payments.state must be a list")
        state_est = 0.0
        for q, v in enumerate(est_state):
            x = ctx.num(v, f"estimated_payments.state[{q}]", stop=False)
            if x is None:
                it_unknown.append(f"estimated_payments.state[{q}]")
            state_est += x or 0.0
        state_tax = state_wh + state_est
        if state_tax:
            ctx.findings.append(
                f"State income tax deducted = W-2 state withholding plus state "
                f"estimates paid (${state_tax:,.0f}). Add any prior-year state "
                "balance paid this year via state_income_tax_paid.")
    else:
        state_tax = ctx.num(state_paid, "state_income_tax_paid")
    # §170(b): 60% of AGI for cash, 30% for (capital-gain) property, 50% overall
    cash_allowed = min(cash_gifts, CHARITABLE_CASH_LIMIT * max(0.0, agi))
    noncash_allowed = min(noncash, CHARITABLE_PROPERTY_LIMIT * max(0.0, agi),
                          max(0.0, CHARITABLE_NONCASH_OVERALL * agi - cash_allowed))
    charity_carry = (cash_gifts - cash_allowed) + (noncash - noncash_allowed)
    salt_raw = state_tax + sdi + prop + other_salt
    inputs = _cf.ItemizedDeductionInputs(
        medical_expenses=medical, property_tax=prop, other_state_local_taxes=other_salt,
        mortgage_interest=mort, mortgage_balance=mort_bal,
        charitable=cash_allowed + noncash_allowed)
    gross_itemized = _cf.itemized_deduction(
        adjusted_gross_income=agi, state_income_tax=state_tax, state_payroll_tax=sdi,
        rules=rules, inputs=inputs)
    salt_cap = rules.effective_salt_cap(agi)
    comp = {
        "state_income_tax": state_tax + sdi,
        "property_tax": prop,
        "other_state_local_taxes": other_salt,
        "salt_before_cap": salt_raw,
        "salt_cap": salt_cap,
        "salt_allowed": min(salt_cap, salt_raw),
        "medical": max(0.0, medical - rules.medical_agi_floor * agi),
        "mortgage_interest": _cf._prorate_interest(mort, inputs.mortgage_balance,
                                                   rules.mortgage_interest_debt_limit),
        "charitable": max(0.0, cash_allowed + noncash_allowed
                          - rules.charitable_agi_floor * agi),
    }
    reduction = rules.limitation(gross_itemized, agi - senior)
    comp["limitation_2_37"] = -reduction
    itemized_total = gross_itemized - reduction
    if salt_raw > salt_cap:
        ctx.findings.append(
            f"SALT of ${salt_raw:,.0f} is capped at ${salt_cap:,.0f}"
            + (" (the cap phases down above the MAGI threshold)"
               if salt_cap < rules.salt_cap else "") + ".")
    if reduction:
        ctx.findings.append(
            f"The 2/37 limitation on itemized deductions in the 37% bracket "
            f"reduces them by ${reduction:,.0f} (measured on AGI, a close "
            "approximation of the statute's taxable-income measure).")
    if cash_gifts >= CHARITY_ACK_THRESHOLD:
        ctx.documents.append("Written acknowledgment for each gift of $250 or more")
    if noncash > FORM_8283_THRESHOLD:
        ctx.forms.add("Form 8283")
    if mort:
        ctx.documents.append("Form 1098 (mortgage interest and principal balance)")
    if prop:
        ctx.documents.append("Property tax bills (amounts paid in the year)")

    nonitemizer_possible = min(cash_gifts, rules.nonitemizer_charitable_limit)
    itemizes = must_itemize or itemized_total > standard + nonitemizer_possible
    nonitemizer = 0.0 if itemizes else nonitemizer_possible
    if itemizes:
        ctx.forms.add("Schedule A")
        if charity_carry > 0:
            ctx.findings.append(
                f"Charitable gifts above the AGI limits (60% cash, 30% property, 50% "
                f"overall): ${charity_carry:,.0f} carries forward up to "
                f"{CHARITABLE_CARRYFORWARD_YEARS} years. Non-cash gifts are treated as "
                "capital-gain property (30%); ordinary-income property would allow 50%.")
    if it_unknown:
        ctx.bounds.append(
            "Itemized amounts unknown (" + ", ".join(it_unknown) + ") were left out: "
            "itemized deductions are a lower bound and tax an upper bound"
            + ("; itemizing may still beat the standard deduction." if not itemizes else "."))
    deduction_used = itemized_total if itemizes else standard + nonitemizer
    if nonitemizer:
        ctx.findings.append(
            f"Taking the standard deduction still allows ${nonitemizer:,.0f} of "
            "cash charitable gifts (non-itemizer deduction, §170(p)).")

    # QBI and taxable income
    ti_before_qbi = max(0.0, agi - deduction_used - senior)
    pref_income = qualified + net_capital_gain
    qbi, qbi_carry = _qbi(ctx, businesses + k1s, se, ti_before_qbi, pref_income,
                          status, table, prior_qbi_loss)
    ti = max(0.0, ti_before_qbi - qbi)

    # Capital loss carryover
    carry = {"short": 0.0, "long": 0.0}
    if net_cap < 0:
        loss_deducted = -cap_in_income
        carry = _carryover(st, lt, loss_deducted, agi - deduction_used - senior - qbi)
        if carry["short"] or carry["long"]:
            ctx.findings.append(
                f"Net capital loss of ${-net_cap:,.0f}: ${loss_deducted:,.0f} "
                f"deducted this year; ${carry['short']:,.0f} short-term and "
                f"${carry['long']:,.0f} long-term carry to next year.")

    # Regular tax
    pref = min(pref_income, ti)
    reg = regular_tax(ti, pref, status, table)
    ordinary_ti = ti - pref
    marginal = _marginal(ordinary_ti, table.brackets[g])
    at0 = at15 = at20 = 0.0
    if pref:
        at0, at15, at20 = _cg_split(pref, ordinary_ti, table.cg_zero_max[g],
                                    table.cg_fifteen_max[g])
        ctx.findings.append(
            f"Qualified dividends and net long-term gain of ${pref:,.0f}: "
            f"${at0:,.0f} at 0%, ${at15:,.0f} at 15%, ${at20:,.0f} at 20%.")

    # AMT — the senior deduction is a personal exemption for AMT and is added
    # back (§56(b)(1)(E); Form 6251 line 1a instructions).
    addback = (standard if not itemizes else
               comp["salt_allowed"] * (itemized_total / gross_itemized if gross_itemized else 1.0))
    amt_r = amt(ti + addback + senior, pref, ordinary_ti, reg, status, table)
    amt_tax = amt_r["amt"]
    if amt_tax:
        ctx.forms.update({"Form 6251", "Schedule 2"})
        ctx.findings.append(
            f"AMT of ${amt_tax:,.0f}: tentative minimum tax "
            f"${amt_r['tentative_minimum_tax']:,.0f} exceeds regular tax "
            f"${reg:,.0f}. A deduction that is added back for AMT is worth "
            "nothing at the margin while AMT applies.")

    # Foreign tax credit
    foreign_tax = fx["tax"]
    total_ftax = foreign_tax + div_ftax
    foreign_gain = max(0.0, cap["foreign_st"] + cap["foreign_lt"])
    foreign_gross = fx["interest"] + fx["dividends"] + foreign_gain + div_foreign_src
    credits: dict[str, float] = {}
    ftc = ftc_carry = 0.0
    if total_ftax:
        simple_limit = SIMPLIFIED_FTC_LIMIT.get(status, SIMPLIFIED_FTC_LIMIT_DEFAULT)
        on_1099 = (not fx["has_income"] and not foreign_tax) or fx["reported_on_1099"]
        if total_ftax <= simple_limit and on_1099:
            ftc = min(total_ftax, reg)
            ctx.findings.append(
                f"Foreign tax of ${total_ftax:,.0f} is within the "
                f"${simple_limit:,.0f} simplified election — claimed without "
                "Form 1116.")
        else:
            ctx.forms.add("Form 1116")
            if div_src_unknown:
                ctx.missing.append("dividends[].foreign_source_income (for Form 1116)")
                ctx.bounds.append(
                    "Foreign-source income on a 1099-DIV with foreign tax is not "
                    "recorded — counted as zero in the Form 1116 limit, so the "
                    "credit is a lower bound.")
            # Capital-gain rate adjustment (Form 1116 instructions): preferential
            # income enters numerator and denominator scaled by its rate / the
            # top rate, at the household's effective preferential rate.
            top = table.brackets[g][-1][0]
            eff = (CG_RATE_MID * at15 + CG_RATE_HIGH * at20) / pref if pref else 0.0
            factor = eff / top
            foreign_pref = min(pref, fx["qualified"]
                               + min(max(0.0, cap["foreign_lt"]), net_capital_gain))
            share = foreign_gross / total_income if total_income > 0 else 0.0
            foreign_taxable = max(0.0, foreign_gross - foreign_pref * (1 - factor)
                                  - (deduction_used + senior) * share)
            denom = ti - pref * (1 - factor)
            limit = reg * min(1.0, foreign_taxable / denom) if denom > 0 else 0.0
            ftc = min(total_ftax, limit)
            ftc_carry = total_ftax - ftc
            ctx.findings.append(
                f"Form 1116 limit: ${foreign_taxable:,.0f} foreign-source taxable "
                f"income / ${denom:,.0f} taxable income × ${reg:,.0f} US tax = "
                f"${limit:,.0f}; credit ${ftc:,.0f} of ${total_ftax:,.0f} paid."
                + (f" ${ftc_carry:,.0f} carries back {FTC_CARRYBACK_YEARS} year and "
                   f"forward {FTC_CARRYFORWARD_YEARS}." if ftc_carry > 0 else "")
                + (f" Preferential income scaled by {factor:.3f} (capital-gain "
                   "rate adjustment)." if pref else "")
                + " Passive category only.")
            if amt_tax:
                ctx.findings.append("AMT and a foreign tax credit together need the "
                                    "separate AMT foreign tax credit — not computed.")
        credits["foreign_tax_credit"] = ftc
        ctx.forms.add("Schedule 3")
        if "Form 1116" in ctx.forms:
            ctx.documents.append("Foreign tax statements (amounts paid and income source)")

    # Child tax credit / credit for other dependents (Schedule 8812)
    n_ctc = n_odc = 0
    for i, d in enumerate(deps):
        name = d.get("member", f"dependents[{i}]")
        age = d.get("age")
        months = d.get("months_lived")
        if age is None or months is None:
            ctx.missing.append(f"dependents[{i}].age/months_lived")
            ctx.bounds.append(f"dependents[{i}]: age or months lived unknown — no "
                              "credit taken; tax is an upper bound.")
            continue
        # Pub. 501: a child born or who died in the year meets the residency
        # test if your home was its home for more than half the time it was alive.
        if d.get("born_or_died_in_year"):
            alive = d.get("months_alive")
            if alive is None:
                ctx.missing.append(f"dependents[{i}].months_alive")
                ctx.bounds.append(f"{name}: born or died in the year but months_alive "
                                  "unknown — no credit taken; tax is an upper bound.")
                continue
            lived = months > alive / 2
        else:
            lived = months >= MIN_MONTHS_LIVED
        if "ssn" in d and d["ssn"] is None:
            ctx.missing.append(f"dependents[{i}].ssn")
            ctx.bounds.append(f"{name}: SSN status unknown — credit for other "
                              "dependents taken instead of the CTC; tax is an upper bound.")
        has_ssn = d.get("ssn", True)
        if not lived and age < CTC_AGE_LIMIT:
            ctx.findings.append(
                f"{name} lived with you {months} months — under the residency "
                "test, so no child tax credit; credit for other dependents taken "
                "if they qualify as a dependent.")
            n_odc += 1
        elif age < CTC_AGE_LIMIT and has_ssn:
            n_ctc += 1
        else:
            n_odc += 1
            if age >= 24 or (age >= 19 and not d.get("student")):
                ctx.findings.append(
                    f"{name} (age {age}) is past the qualifying-child age test — the "
                    "$500 credit assumes the qualifying-relative tests (gross income, "
                    "support) are met; confirm them.")
    tentative_ctc = n_ctc * table.ctc_per_child + n_odc * ODC_AMOUNT
    ctc_reduction = min(tentative_ctc, _ctc_reduction(magi, status))
    ctc_after = tentative_ctc - ctc_reduction
    liability = reg + amt_tax - ftc
    ctc_nonref = min(ctc_after, max(0.0, liability))
    earned = max(0.0, wages + sc_net + sum(k["se_earnings"] for k in k1s) - half_se)
    actc = 0.0
    if n_ctc:
        unused = ctc_after - ctc_nonref
        actc = min(unused, n_ctc * table.actc_refundable_max,
                   ACTC_RATE * max(0.0, earned - ACTC_EARNED_INCOME_FLOOR))
    if tentative_ctc:
        ctx.forms.add("Schedule 8812")
        credits["child_and_other_dependent_credit"] = ctc_nonref
        if ctc_reduction:
            ctx.findings.append(
                f"Child/other-dependent credit of ${tentative_ctc:,.0f} reduced by "
                f"${ctc_reduction:,.0f} for MAGI above "
                f"${CTC_PHASEOUT_THRESHOLD.get(status, CTC_PHASEOUT_THRESHOLD_DEFAULT):,.0f}.")
        if n_odc:
            ctx.findings.append(
                f"{n_odc} dependent(s) aged {CTC_AGE_LIMIT}+ (or not meeting the "
                f"child tests) get the ${ODC_AMOUNT:,.0f} credit for other dependents.")
    if actc:
        credits["additional_child_tax_credit"] = actc
    if excess_ss:
        credits["excess_social_security"] = excess_ss

    # Other taxes
    am_threshold = ADDITIONAL_MEDICARE_THRESHOLD[status]
    am_wages = max(0.0, medicare_wages - am_threshold)
    am_se = max(0.0, se_earnings - max(0.0, am_threshold - medicare_wages))
    addl_medicare = ADDITIONAL_MEDICARE_RATE * (am_wages + am_se)
    am_withheld = max(0.0, medicare_wh - EMPLOYEE_MEDICARE_RATE * medicare_wages)
    if addl_medicare or am_withheld:
        ctx.forms.update({"Form 8959", "Schedule 2"})
        ctx.findings.append(
            f"Additional Medicare Tax ${addl_medicare:,.0f} on wages/SE income above "
            f"${am_threshold:,.0f}; employers withheld ${am_withheld:,.0f} under the "
            f"${EMPLOYER_ADDITIONAL_MEDICARE_WITHHOLDING_THRESHOLD:,.0f}-per-employer "
            "rule, credited as withholding"
            + (" — under-withheld because the rule ignores the spouse's wages and "
               "filing status." if addl_medicare > am_withheld + 1 else
               " — over-withheld; the excess comes back." if am_withheld > addl_medicare + 1
               else "."))
    nii = max(0.0, taxable_interest + ordinary + cap_in_income)
    niit_base = min(nii, max(0.0, magi - NIIT_THRESHOLD[status]))
    niit = NIIT_RATE * niit_base
    if niit:
        ctx.forms.update({"Form 8960", "Schedule 2"})
        ctx.findings.append(
            f"NIIT ${niit:,.0f}: 3.8% of the lesser of net investment income "
            f"${nii:,.0f} and MAGI above ${NIIT_THRESHOLD[status]:,.0f}.")
    other_taxes = {"self_employment_tax": se_tax, "additional_medicare_tax": addl_medicare,
                   "niit": niit, "hsa_additional_tax": hsa["additional_tax"]}
    nonref = sum(v for k, v in credits.items()
                 if k in ("foreign_tax_credit", "child_and_other_dependent_credit"))
    total_tax = max(0.0, reg + amt_tax - nonref) + sum(other_taxes.values())
    refundable = actc + excess_ss

    # Payments
    est = _section(ctx, tr, "estimated_payments", "estimated payments", stop=False)
    est_quarters: list[float | None] = []
    est_known = est is not None
    applied: float | None = 0.0
    if est is None:
        ctx.bounds.append("estimated_payments not recorded — refund or balance due "
                          "cannot be determined.")
    else:
        fed_est = est.get("federal", [])
        if fed_est is None:
            est_known = False
            ctx.missing.append("estimated_payments.federal")
            fed_est = []
        if not isinstance(fed_est, list):
            raise FederalReturnError("estimated_payments.federal must be a list of "
                                     "up to four installments")
        if len(fed_est) > MAX_INSTALLMENTS:
            raise FederalReturnError(
                f"estimated_payments.federal has {len(fed_est)} entries; at most "
                f"{MAX_INSTALLMENTS} installments (Apr, Jun, Sep, Jan)")
        for q, v in enumerate(fed_est):
            x = ctx.num(v, f"estimated_payments.federal[{q}]", stop=False)
            if x is None:
                est_known = False
            est_quarters.append(x)
        applied = ctx.opt(est, "applied_from_prior_year",
                          "estimated_payments.applied_from_prior_year", stop=False)
        if applied is None:
            est_known = False
    est_total = (sum(x or 0.0 for x in est_quarters) + (applied or 0.0)) if est_known else None
    if ss_withheld is None:
        wh_known = False
        ss_withheld = 0.0
    withholding = {"w2_federal": fed_wh, "additional_medicare_withheld": am_withheld,
                   "ssa_1099_federal": ss_withheld,
                   "total": fed_wh + am_withheld + ss_withheld}
    if not wh_known:
        ctx.bounds.append("Federal withholding is unknown — refund or balance due "
                          "cannot be determined.")
    payments = (withholding["total"] + est_total + refundable
                if (wh_known and est_total is not None) else None)
    refund = None if payments is None else payments - total_tax
    if est_total is not None and est_quarters:
        ctx.documents.append("Federal estimated-payment confirmations (Form 1040-ES)")

    if refund is not None and refund < 0 and supplemental and marginal > SUPPLEMENTAL_WITHHOLDING_RATE:
        short = supplemental * (marginal - SUPPLEMENTAL_WITHHOLDING_RATE)
        ctx.findings.append(
            f"${supplemental:,.0f} of supplemental wages (RSU vesting, bonus) was "
            f"withheld at the {SUPPLEMENTAL_WITHHOLDING_RATE:.0%} flat rate against a "
            f"{marginal:.0%} marginal rate — about ${short:,.0f} of the balance "
            "due. Raise W-4 withholding or make estimates on vest dates.")

    # Underpayment penalty safe harbor (Form 2210)
    py_tax = py.get("federal_total_tax")
    py_agi = py.get("agi")
    tax_2210 = max(0.0, total_tax - refundable)
    current_req = SAFE_HARBOR_CURRENT * tax_2210
    high = SAFE_HARBOR_HIGH_AGI.get(status, SAFE_HARBOR_HIGH_AGI_DEFAULT)
    if py_tax is None:
        ctx.missing.append("prior_year.federal_total_tax")
        prior_req = None
        prior_pct = None
    else:
        py_tax = ctx.num(py_tax, "prior_year.federal_total_tax")
        if py_agi is None:
            ctx.missing.append("prior_year.agi")
            prior_pct = SAFE_HARBOR_PRIOR_HIGH
            ctx.bounds.append("Prior-year AGI unknown — the 110% prior-year safe "
                              "harbor is assumed (the stricter of the two).")
        else:
            py_agi = ctx.num(py_agi, "prior_year.agi", allow_negative=True)
            prior_pct = SAFE_HARBOR_PRIOR_HIGH if py_agi > high else SAFE_HARBOR_PRIOR
        prior_req = prior_pct * py_tax
    required = current_req if prior_req is None else min(current_req, prior_req)
    harbor: dict = {"tax_for_penalty": tax_2210, "current_year_90": current_req,
                    "prior_year_pct": prior_pct, "prior_year_required": prior_req,
                    "required_annual": required, "paid": None, "met": None,
                    "quarters": [], "owed_after_withholding": None}
    if wh_known and est_total is not None:
        paid = withholding["total"] + est_total
        harbor["paid"] = paid
        owed = tax_2210 - withholding["total"]
        harbor["owed_after_withholding"] = owed
        quarters = []
        cum_req = cum_paid = 0.0
        q_est = [x or 0.0 for x in est_quarters] + [0.0] * (4 - len(est_quarters))
        q_est[0] += applied or 0.0
        for q in range(4):
            cum_req += required / 4
            cum_paid += withholding["total"] / 4 + q_est[q]
            quarters.append({"due": INSTALLMENT_DUE[q], "required_cumulative": cum_req,
                             "paid_cumulative": cum_paid,
                             "shortfall": max(0.0, cum_req - cum_paid)})
        harbor["quarters"] = quarters
        # §6654(e)(1): the $1,000 test is tax less withholding only.
        if owed < PENALTY_DE_MINIMIS:
            harbor["met"] = True
            harbor["reason"] = (f"under ${PENALTY_DE_MINIMIS:,.0f} owed after "
                                "withholding")
        elif all(x["shortfall"] < 0.5 for x in quarters):
            harbor["met"] = True
            harbor["reason"] = "every installment met the safe harbor"
        else:
            harbor["met"] = False
            late = [x["due"] for x in quarters if x["shortfall"] >= 0.5]
            harbor["reason"] = "installments short at " + ", ".join(late)
            ctx.forms.add("Form 2210")
            ctx.findings.append(
                f"Underpayment penalty likely: ${paid:,.0f} paid against a "
                f"${required:,.0f} safe harbor"
                + ("" if prior_req is not None else " (prior-year tax unknown, so "
                   "only the 90% test was available)")
                + f"; short at {', '.join(late)}. The annualized-income method "
                "(Form 2210 Schedule AI) can reduce it when income arrived late "
                "in the year — not computed.")
    # Next-year estimated payments (110%/100% of this year's tax)
    ny_pct = SAFE_HARBOR_PRIOR_HIGH if agi > high else SAFE_HARBOR_PRIOR
    ny_target = ny_pct * tax_2210
    ny_quarterly = max(0.0, ny_target - withholding["total"]) / 4
    next_year = {"tax_year": year + 1, "basis_pct": ny_pct, "target": ny_target,
                 "assumed_withholding": withholding["total"],
                 "quarterly": ny_quarterly,
                 "due": [f"{d}" for d in INSTALLMENT_DUE]}

    if ctx.stop:   # a late stop must never be silently passed
        raise FederalReturnError(
            "cannot compute the return without: " + ", ".join(sorted(set(ctx.stop))),
            missing=sorted(set(ctx.missing)))

    carryforwards = {
        "capital_loss": carry,
        "home_office": {b["business"]: b["home_office_carryforward"]
                        for b in businesses if b["home_office_carryforward"]},
        "qbi_loss": qbi_carry,
        "foreign_tax_credit": ftc_carry,
        "ira_basis": ira["basis"],
        "charitable": charity_carry if itemizes else 0.0,
    }
    documents = ["Prior-year Form 1040 (AGI, total tax, carryovers)"] + ctx.documents
    return FederalReturn(
        tax_year=year, filing_status=status, projection=projection or wb_proj,
        table_source=table.source,
        wages=wages, taxable_interest=taxable_interest, tax_exempt_interest=exempt,
        us_treasury_interest=treasury, ordinary_dividends=ordinary,
        qualified_dividends=qualified, capital_gain_distributions=cgd,
        short_term_net=st, long_term_net=lt, net_capital_gain_or_loss=cap_in_income,
        capital_loss_carryover_to_next_year=carry,
        schedule_c_net=sc_net, schedule_c_detail=businesses,
        ira_taxable=ira["taxable"], hsa_taxable_distributions=hsa["taxable"],
        foreign_income=foreign_gross, taxable_social_security=taxable_ss,
        state_refund_taxable=refund_taxable, total_income=total_income,
        self_employment_tax=se_tax, adjustments=adjustments, agi=agi,
        itemized=comp, itemized_total=itemized_total, standard_deduction=standard,
        itemizes=itemizes, nonitemizer_charitable=nonitemizer,
        deduction_used=deduction_used, senior_deduction=senior, qbi_deduction=qbi,
        taxable_income=ti, preferential_income=pref, regular_tax=reg,
        marginal_rate=marginal, amt=amt_tax, credits=credits, niit=niit,
        additional_medicare_tax=addl_medicare, other_taxes=other_taxes,
        total_tax=total_tax, withholding=withholding, estimated_payments=est_total,
        refundable_credits=refundable, total_payments=payments, refund_or_due=refund,
        penalty_safe_harbor=harbor, next_year_estimates=next_year,
        carryforwards=carryforwards, forms=sorted(ctx.forms),
        documents=list(dict.fromkeys(documents)), bounds=ctx.bounds,
        findings=ctx.findings, missing=sorted(set(ctx.missing)),
        k1_income=k1_income, k1_detail=k1s,
    )
