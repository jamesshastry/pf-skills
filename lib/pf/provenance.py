"""Where the repository's reference data came from, and when it was checked.

Every other module here encodes *reasoning*, which does not expire. These
tables encode **facts about the outside world**, which do — statutory
contribution limits change every year, state insurance rules change on
legislative timescales.

Nothing in the design prevented them going stale, which is the gap this closes.
D16 in the private validation set was precisely this failure: an IRA
contribution left at the prior year's limit, never wrong when written.

The registry is deliberately hand-maintained. Auto-discovering provenance would
mean inferring it, and a table's real weakness is usually that nobody has
looked at it — which no amount of introspection reveals.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from . import charity as _cha
from . import crossborder as _xb
from . import depreciation as _dep
from . import disclosure as _dis
from . import education as _edu
from . import entity as _ent
from . import expat as _exp
from . import healthcare as _hc
from . import jurisdiction as _jur
from . import pension as _pen
from . import pfic as _pfi
from . import portfolio as _pf
from . import probate as _prb
from . import presence as _pre
from . import realestate as _re
from . import reporting as _rep
from . import ssa as _ssa
from . import status as _sta
from . import transitions as _tra
from . import limits as _lim

ANNUAL = "annual"
LEGISLATIVE = "legislative"

#: How long an entry may go unverified before it is reported stale.
MAX_AGE_DAYS = {ANNUAL: 365, LEGISLATIVE: 730}

UNVERIFIED_MARKERS = ("unverified", "", None)


@dataclass
class Entry:
    key: str
    source: str
    verified_on: _dt.date | None
    #: True when the field is present but says "nobody has checked this".
    self_declared_unverified: bool = False
    #: Every value this entry asserts, so the verification checklist can be
    #: generated from the tables rather than hand-written. A hand-written
    #: checklist silently omits whatever was added after it.
    values: dict = field(default_factory=dict)


@dataclass
class Table:
    name: str
    module: str
    holds: str
    authority: str
    cadence: str
    #: Where a human goes to check it.
    url: str = ""
    entries: list[Entry] = field(default_factory=list)
    #: For annual tables: the years that must be present.
    requires_current_year: bool = False


@dataclass
class Issue:
    table: str
    key: str | None
    severity: str  # blocker | stale | unverified
    detail: str


def _parse(value) -> tuple[_dt.date | None, bool]:
    if value in UNVERIFIED_MARKERS:
        return None, True
    if isinstance(value, _dt.date):
        return value, False
    if isinstance(value, str):
        try:
            return _dt.date.fromisoformat(value[:10]), False
        except ValueError:
            return None, True
    return None, True


def registry() -> list[Table]:
    """Every table in the repo whose contents can go out of date."""
    limits_entries = []
    for year in _lim.years_available():
        lim = _lim.for_year(year)
        on, unver = _parse(lim.verified_on)
        limits_entries.append(Entry(
            str(year), lim.source, on, unver,
            values={k: getattr(lim, k) for k in (
                "elective_deferral", "catch_up_50", "catch_up_60_63",
                "total_additions", "compensation_limit", "ira_contribution",
                "ira_catch_up", "hsa_self_only", "hsa_family",
                "hsa_catch_up_55")}))

    jur_entries = []
    for code in _jur.states_available():
        rules = _jur.rules_for(code)
        on, unver = _parse(getattr(rules, "verified_on", None))
        jur_entries.append(Entry(
            code, getattr(rules, "source", "") or "", on, unver,
            values={k: getattr(rules, k) for k in (
                "min_liability", "um_uim_capped_at_bi", "umpd_available",
                "umpd_max", "umpd_excluded_by_collision", "umpd_deductible")}))

    prb_entries = []
    for code in _prb.states_available():
        pr = _prb.rules_for(code)
        on, unver = _parse(pr.verified_on)
        prb_entries.append(Entry(
            code, pr.source, on, unver,
            values={k: getattr(pr, k) for k in (
                "basis", "fee_schedule", "fee_claimable_twice",
                "small_estate_threshold", "spousal_simplified")}))

    dis_on, dis_unver = _parse(_dis.DISCLOSURE_VERIFIED)
    dis_entries = [
        Entry("California disclosure and Davis-Stirling thresholds",
              _dis.DISCLOSURE_SOURCE, dis_on, dis_unver,
              values={k: getattr(_dis, k) for k in (
                  "LEAD_PAINT_YEAR", "RESERVE_STRONG", "RESERVE_WEAK",
                  "DELINQUENCY_FINANCING_RISK", "RESERVE_CONTRIBUTION_MIN",
                  "REGULAR_ASSESSMENT_INCREASE_CAP",
                  "SPECIAL_ASSESSMENT_BUDGET_CAP", "RENTAL_CAP_FLOOR",
                  "SB326_MIN_UNITS", "SB326_MIN_HEIGHT_FEET",
                  "SB326_CYCLE_YEARS", "RESERVE_STUDY_MAX_AGE_YEARS")}),
        Entry("required disclosures by property type and year",
              _dis.DISCLOSURE_SOURCE, dis_on, dis_unver,
              values={d.key: d.authority for d in _dis.DISCLOSURES}),
    ]

    ssa_on, ssa_unver = _parse(_ssa.SSA_VERIFIED)
    ssa_entries = [Entry(
        "survivor benefit eligibility ages and factors", _ssa.SSA_SOURCE,
        ssa_on, ssa_unver,
        values={k: getattr(_ssa, k) for k in (
            "CHILD_BENEFIT_END_AGE", "CHILD_BENEFIT_END_AGE_IN_SCHOOL",
            "CAREGIVER_CHILD_AGE_LIMIT", "WIDOW_EARLIEST_AGE",
            "WIDOW_FACTOR_AT_EARLIEST", "CHILD_AND_CAREGIVER_PIA_SHARE",
            "FULLY_INSURED_CREDITS")})]

    ages_on, ages_unver = _parse(_lim.RETIREMENT_AGES_VERIFIED)
    rep_on, rep_unver = _parse(_rep.REPORTING_VERIFIED)

    tot_entries = []
    for code in _sta.countries_available():
        tt = _sta.totalization(code)
        on, unver = _parse(tt.verified_on)
        tot_entries.append(Entry(code, tt.source, on, unver,
                                 values={"agreement": tt.agreement}))

    edu_entries = []
    for code in _edu.states_available():
        sb = _edu.state_benefit(code)
        on, unver = _parse(sb.verified_on)
        edu_entries.append(Entry(
            code, sb.source, on, unver,
            values={"has_income_tax": sb.has_income_tax,
                    "deduction_available": sb.deduction_available}))

    xb_entries = []
    for code in _xb.countries_available():
        c = _xb.country_for(code)
        on, unver = _parse(c.verified_on)
        xb_entries.append(Entry(code, c.source, on, unver,
                                values=c.asserted_values()))

    dom_entries = []
    for code in _exp.domicile_states_available():
        dr = _exp.domicile_rules(code)
        on, unver = _parse(dr.verified_on)
        dom_entries.append(Entry(
            code, dr.source, on, unver,
            values={"has_income_tax": dr.has_income_tax,
                    "no_bright_line": dr.no_bright_line,
                    "safe_harbor_days": dr.safe_harbor_days,
                    "conforms_to_feie": dr.conforms_to_feie}))

    pen_entries = []
    for key in _pen.schemes_available():
        s = _pen.scheme_for(key)
        on, unver = _parse(s.verified_on)
        pen_entries.append(Entry(
            key, s.source, on, unver,
            values={k: getattr(s, k) for k in (
                "bucket", "treaty", "treaty_article", "rev_proc_relief",
                "holder_directed_by_design")}))

    pfic_on, pfic_unver = _parse(_pfi.PFIC_VERIFIED)
    cha_on, cha_unver = _parse(_cha.CHARITY_VERIFIED)
    ws_on, ws_unver = _parse(_pf.WASH_SALE_VERIFIED_ON)
    ent_on, ent_unver = _parse(_ent.ENTITY_VERIFIED)
    med_on, med_unver = _parse(_hc.MEDICARE_VERIFIED)
    aca_on, aca_unver = _parse(_hc.ACA_VERIFIED)
    pre_on, pre_unver = _parse(_pre.PRESENCE_VERIFIED)
    dep_on, dep_unver = _parse(_dep.DEPRECIATION_VERIFIED)

    return [
        Table(
            name="statutory contribution limits",
            module="lib/pf/limits.py",
            holds="§402(g), §415(c), catch-up, IRA and HSA limits by year",
            authority="irs.gov — annual cost-of-living adjustments",
            url="https://www.irs.gov/retirement-plans/plan-participant-employee/"
                "retirement-topics-401k-and-profit-sharing-plan-contribution-limits · "
                "https://www.irs.gov/publications/p969",
            cadence=ANNUAL,
            entries=limits_entries,
            requires_current_year=True,
        ),
        Table(
            name="statutory retirement ages",
            module="lib/pf/limits.py",
            holds="RMD age, Social Security claiming ages, §72(t) and Rule of 55",
            authority="irs.gov and ssa.gov",
            cadence=LEGISLATIVE,
            url="https://www.irs.gov/retirement-plans/retirement-plan-and-ira-"
                "required-minimum-distributions-faqs · https://www.ssa.gov/benefits/retirement/planner/ageincrease.html",
            entries=[Entry(
                "all birth years", _lim.RETIREMENT_AGES_SOURCE,
                ages_on, ages_unver,
                values={"rmd_age (born 1960+)": 75, "rmd_age (born 1951-1959)": 73,
                        "ss_full (born 1960+)": 67, "ss_earliest": 62,
                        "ss_latest": 70, "ira_penalty_free_age": 59.5,
                        "rule_of_55_age": 55})],
        ),
        Table(
            name="state 529 income-tax treatment",
            module="lib/pf/education.py",
            holds="whether a state deducts 529 contributions, and whether it "
                  "taxes income at all",
            authority="each state's revenue authority",
            url="https://www.ftb.ca.gov · https://comptroller.texas.gov",
            cadence=LEGISLATIVE,
            entries=edu_entries,
        ),
        Table(
            name="foreign reporting thresholds",
            module="lib/pf/reporting.py",
            holds="FBAR, FATCA, PFIC de minimis and Form 3520 thresholds",
            authority="irs.gov and fincen.gov",
            cadence=LEGISLATIVE,
            url="https://bsaefiling.fincen.treas.gov · "
                "https://www.irs.gov/businesses/comparison-of-form-8938-and-fbar-requirements",
            entries=[Entry(
                "all", _rep.REPORTING_SOURCE, rep_on, rep_unver,
                values={"FBAR_THRESHOLD": _rep.FBAR_THRESHOLD,
                        "FATCA_US_RESIDENT": _rep.FATCA_US_RESIDENT,
                        "FATCA_ABROAD": _rep.FATCA_ABROAD,
                        "PFIC_DE_MINIMIS": _rep.PFIC_DE_MINIMIS,
                        "FOREIGN_GIFT_THRESHOLD": _rep.FOREIGN_GIFT_THRESHOLD})],
        ),
        Table(
            name="social security survivor benefit rules",
            module="lib/pf/ssa.py",
            holds="when a child, caregiver and widow(er)'s benefit start and "
                  "stop, the early-claiming factor, and insured-status credits",
            authority="Social Security Act §202; 20 CFR 404.350-404.390",
            url="https://www.ssa.gov/benefits/survivors/",
            cadence=LEGISLATIVE,
            entries=ssa_entries,
        ),
        Table(
            name="social security totalization agreements",
            module="lib/pf/status.py",
            holds="whether a US totalization agreement exists with a country",
            authority="ssa.gov",
            url="https://www.ssa.gov/international/agreements_overview.html",
            cadence=LEGISLATIVE,
            entries=tot_entries,
        ),
        Table(
            name="California property disclosure requirements",
            module="lib/pf/disclosure.py",
            holds="which disclosures a property attracts, the §4525 packet, "
                  "SB 326 applicability, and association health thresholds",
            authority="California Civil Code and Health & Safety Code; "
                      "42 U.S.C. §4852d",
            url="https://leginfo.legislature.ca.gov",
            cadence=LEGISLATIVE,
            entries=dis_entries,
        ),
        Table(
            name="state probate cost and small-estate rules",
            module="lib/pf/probate.py",
            holds="fee basis and schedule, whether the fee is claimable twice, "
                  "small-estate thresholds, simplified spousal transfers",
            authority="each state's probate code",
            url="https://leginfo.legislature.ca.gov · "
                "https://statutes.capitol.texas.gov",
            cadence=LEGISLATIVE,
            entries=prb_entries,
        ),
        Table(
            name="state auto insurance rules",
            module="lib/pf/jurisdiction.py",
            holds="UM/UIM caps, UMPD availability and limits, statutory minimums",
            authority="each state's insurance code or department guidance",
            url="https://www.insurance.ca.gov · https://www.tdi.texas.gov",
            cadence=LEGISLATIVE,
            entries=jur_entries,
        ),
        Table(
            name="foreign treatment of US retirement accounts",
            module="lib/pf/crossborder.py",
            holds="whether a country recognises the Roth wrapper, its "
                  "residency day tests, and any transitional status for "
                  "returning residents",
            authority="each country's revenue authority, and a cross-border "
                      "tax professional — this table is the least "
                      "self-sufficient in the repository",
            url="https://www.irs.gov/individuals/international-taxpayers · "
                "https://www.incometaxindia.gov.in",
            cadence=LEGISLATIVE,
            entries=xb_entries,
        ),
        Table(
            name="state domicile and residency rules",
            module="lib/pf/expat.py",
            holds="whether a state taxes income, whether residency has a "
                  "day-count bright line, statutory safe harbours, and "
                  "whether the state conforms to the §911 exclusion",
            authority="each state's revenue authority",
            url="https://www.ftb.ca.gov/forms/2024/2024-1031-publication.pdf · "
                "https://comptroller.texas.gov",
            cadence=LEGISLATIVE,
            entries=dom_entries,
        ),
        Table(
            name="foreign pension scheme classification",
            module="lib/pf/pension.py",
            holds="treaty status and default trust classification, per scheme",
            authority="the relevant bilateral income tax treaty, and irs.gov "
                      "for the revenue procedures",
            url="https://www.irs.gov/businesses/international-businesses/"
                "united-states-income-tax-treaties-a-to-z",
            cadence=LEGISLATIVE,
            entries=pen_entries,
        ),
        Table(
            name="PFIC regime mechanics",
            module="lib/pf/pfic.py",
            holds="§1291 allocation and interest mechanics, and the "
                  "availability conditions for the §1295 and §1296 elections",
            authority="irs.gov — Form 8621 instructions",
            url="https://www.irs.gov/forms-pubs/about-form-8621",
            cadence=LEGISLATIVE,
            entries=[Entry(
                "all", _pfi.PFIC_SOURCE, pfic_on, pfic_unver,
                values={"COMPOUNDING_PERIODS_PER_YEAR":
                        _pfi.COMPOUNDING_PERIODS_PER_YEAR,
                        "RETURN_DUE_MONTH": _pfi.RETURN_DUE_MONTH,
                        "RETURN_DUE_DAY": _pfi.RETURN_DUE_DAY,
                        "FORMS_PER_FUND_PER_YEAR":
                        _pfi.FORMS_PER_FUND_PER_YEAR})],
        ),
        Table(
            name="charitable deduction limits",
            module="lib/pf/charity.py",
            holds="§170(b) AGI percentage limits, the §170(d) carryforward "
                  "period, the long-term holding period, and the QCD age",
            authority="irs.gov — Publication 526",
            url="https://www.irs.gov/publications/p526",
            cadence=LEGISLATIVE,
            entries=[Entry(
                "all", _cha.CHARITY_SOURCE, cha_on, cha_unver,
                values={"CASH_AGI_LIMIT": _cha.CASH_AGI_LIMIT,
                        "APPRECIATED_AGI_LIMIT": _cha.APPRECIATED_AGI_LIMIT,
                        "APPRECIATED_BASIS_ELECTION_LIMIT":
                        _cha.APPRECIATED_BASIS_ELECTION_LIMIT,
                        "CARRYFORWARD_YEARS": _cha.CARRYFORWARD_YEARS,
                        "LONG_TERM_DAYS": _cha.LONG_TERM_DAYS,
                        "QCD_AGE": _cha.QCD_AGE})],
        ),
        Table(
            name="wash sale rule",
            module="lib/pf/portfolio.py",
            holds="the 61-day window, its application across all accounts, "
                  "and the permanent disallowance of a loss when the "
                  "replacement is bought in an IRA",
            authority="irs.gov — IRC §1091, Publication 550, Rev. Rul. 2008-5",
            url="https://www.irs.gov/publications/p550 · "
                "https://www.irs.gov/pub/irs-drop/rr-08-05.pdf",
            cadence=LEGISLATIVE,
            entries=[Entry("all", _pf.WASH_SALE_SOURCE, ws_on, ws_unver,
                           values=dict(_pf.WASH_SALE_VALUES))],
        ),
        Table(
            name="windfall tax character",
            module="lib/pf/transitions.py",
            holds="whether each kind of windfall is income on receipt, and "
                  "what basis it carries",
            authority="irs.gov",
            url="https://www.irs.gov/publications/p559 · "
                "https://www.irs.gov/publications/p4345",
            cadence=LEGISLATIVE,
            entries=[
                Entry(k, _tra.tax_character(k).source,
                      *_parse(_tra.tax_character(k).verified_on),
                      values={"income_on_receipt":
                              _tra.tax_character(k).income_on_receipt,
                              "basis_rule": _tra.tax_character(k).basis_rule})
                for k in _tra.windfall_kinds_available()],
        ),
        Table(
            name="windfall tax administration",
            module="lib/pf/transitions.py",
            holds="estimated-tax safe harbours, supplemental withholding "
                  "rates, FDIC and SIPC limits. The IRMAA lookback this "
                  "module reports on is defined in and ticked under "
                  "`lib/pf/healthcare.py`",
            authority="irs.gov, ssa.gov, fdic.gov, sipc.org",
            url="https://www.irs.gov/publications/p505",
            cadence=LEGISLATIVE,
            entries=[
                Entry("estimated tax", _tra.TAX_ADMIN_SOURCE,
                      *_parse(_tra.TAX_ADMIN_VERIFIED),
                      values={
                          "SUPPLEMENTAL_WITHHOLDING_RATE":
                              _tra.SUPPLEMENTAL_WITHHOLDING_RATE,
                          "SUPPLEMENTAL_WITHHOLDING_RATE_ABOVE":
                              _tra.SUPPLEMENTAL_WITHHOLDING_RATE_ABOVE,
                          "SUPPLEMENTAL_WITHHOLDING_THRESHOLD":
                              _tra.SUPPLEMENTAL_WITHHOLDING_THRESHOLD,
                          "SAFE_HARBOR_CURRENT_YEAR":
                              _tra.SAFE_HARBOR_CURRENT_YEAR,
                          "SAFE_HARBOR_PRIOR_YEAR": _tra.SAFE_HARBOR_PRIOR_YEAR,
                          "SAFE_HARBOR_PRIOR_YEAR_HIGH_AGI":
                              _tra.SAFE_HARBOR_PRIOR_YEAR_HIGH_AGI,
                          "SAFE_HARBOR_HIGH_AGI": _tra.SAFE_HARBOR_HIGH_AGI}),
                Entry("deposit insurance", _tra.INSURANCE_SOURCE,
                      *_parse(_tra.INSURANCE_VERIFIED),
                      values={
                          "FDIC_LIMIT_PER_DEPOSITOR":
                              _tra.FDIC_LIMIT_PER_DEPOSITOR,
                          "SIPC_LIMIT": _tra.SIPC_LIMIT,
                          "SIPC_CASH_SUBLIMIT": _tra.SIPC_CASH_SUBLIMIT}),
            ],
        ),
        Table(
            name="marriage and divorce transfer rules",
            module="lib/pf/transitions.py",
            holds="which instrument divides each account type, the medical "
                  "AGI floor, and the MFS Roth phase-out ceiling",
            authority="irs.gov; ERISA case law",
            url="https://www.irs.gov/publications/p504",
            cadence=LEGISLATIVE,
            entries=[
                Entry("marriage", _tra.MARRIAGE_SOURCE,
                      *_parse(_tra.MARRIAGE_VERIFIED),
                      values={"MEDICAL_DEDUCTION_AGI_FLOOR":
                              _tra.MEDICAL_DEDUCTION_AGI_FLOOR,
                              "MFS_ROTH_PHASEOUT_CEILING":
                              _tra.MFS_ROTH_PHASEOUT_CEILING}),
                Entry("divorce", _tra.DIVORCE_SOURCE,
                      *_parse(_tra.DIVORCE_VERIFIED),
                      values={
                          "EARLY_DISTRIBUTION_PENALTY":
                              _tra.EARLY_DISTRIBUTION_PENALTY,
                          **{k: _tra.transfer_mechanism(k).instrument
                             for k in _tra.mechanism_kinds_available()}}),
            ],
        ),
        Table(
            name="payroll, §199A and corporate tax rates",
            module="lib/pf/entity.py",
            holds="the SECA/FICA rates and the fixed Additional Medicare "
                  "thresholds, the 92.35% net-earnings factor, the §199A "
                  "deduction rate and its wage limits, the SSTB list, the "
                  "corporate rate, and the owner-only plan employer rates",
            authority="irs.gov — Publications 15, 334 and 535, and the "
                      "statutory text of §§1401, 199A and 11(b)",
            url="https://www.irs.gov/publications/p334 · "
                "https://www.irs.gov/publications/p15 · "
                "https://www.irs.gov/newsroom/qualified-business-income-deduction",
            cadence=LEGISLATIVE,
            entries=[Entry(
                "all", _ent.ENTITY_SOURCE, ent_on, ent_unver,
                values={"SS_RATE": _ent.SS_RATE,
                        "MEDICARE_RATE": _ent.MEDICARE_RATE,
                        "ADDL_MEDICARE_RATE": _ent.ADDL_MEDICARE_RATE,
                        "ADDL_MEDICARE_THRESHOLD":
                        _ent.ADDL_MEDICARE_THRESHOLD,
                        "SE_BASE_FACTOR": _ent.SE_BASE_FACTOR,
                        "QBI_RATE": _ent.QBI_RATE,
                        "QBI_WAGE_ONLY": _ent.QBI_WAGE_ONLY,
                        "QBI_WAGE_PLUS_WAGE": _ent.QBI_WAGE_PLUS_WAGE,
                        "QBI_WAGE_PLUS_UBIA": _ent.QBI_WAGE_PLUS_UBIA,
                        "C_CORP_RATE": _ent.C_CORP_RATE,
                        "SSTB_FIELDS": _ent.SSTB_FIELDS,
                        "EMPLOYER_RATE_W2": _ent.EMPLOYER_RATE_W2,
                        "EMPLOYER_RATE_SELF_EMPLOYED":
                        _ent.EMPLOYER_RATE_SELF_EMPLOYED})],
        ),
        Table(
            name="Medicare enrolment structure and penalties",
            module="lib/pf/healthcare.py",
            holds="the entitlement age, the enrolment period lengths, the "
                  "late-enrolment penalty rates, the quarters required for "
                  "premium-free Part A, the employer-size test that decides "
                  "which payer is primary, the IRMAA lookback, and the "
                  "retroactive Part A window that ends HSA eligibility",
            authority="medicare.gov and cms.gov; irs.gov Publication 969 for "
                      "the HSA interaction",
            url="https://www.medicare.gov/basics/get-started-with-medicare/"
                "sign-up/when-does-medicare-coverage-start · "
                "https://www.irs.gov/publications/p969",
            cadence=LEGISLATIVE,
            entries=[Entry(
                "all", _hc.MEDICARE_SOURCE, med_on, med_unver,
                values={"MEDICARE_AGE": _hc.MEDICARE_AGE,
                        "IRMAA_LOOKBACK_YEARS": _hc.IRMAA_LOOKBACK_YEARS,
                        "IEP_MONTHS": _hc.IEP_MONTHS,
                        "IEP_MONTHS_BEFORE": _hc.IEP_MONTHS_BEFORE,
                        "IEP_MONTHS_AFTER": _hc.IEP_MONTHS_AFTER,
                        "SEP_PART_B_MONTHS": _hc.SEP_PART_B_MONTHS,
                        "CREDITABLE_COVERAGE_GAP_DAYS":
                        _hc.CREDITABLE_COVERAGE_GAP_DAYS,
                        "PART_B_PENALTY_PER_12M": _hc.PART_B_PENALTY_PER_12M,
                        "PART_D_PENALTY_PER_MONTH":
                        _hc.PART_D_PENALTY_PER_MONTH,
                        "PART_A_QUARTERS_REQUIRED":
                        _hc.PART_A_QUARTERS_REQUIRED,
                        "SEP_EMPLOYER_MIN_EMPLOYEES":
                        _hc.SEP_EMPLOYER_MIN_EMPLOYEES,
                        "HSA_STOP_MONTHS_BEFORE_PART_A":
                        _hc.HSA_STOP_MONTHS_BEFORE_PART_A})],
        ),
        Table(
            name="ACA premium tax credit and Medicaid boundaries",
            module="lib/pf/healthcare.py",
            holds="the federal-poverty-level multiples that bound premium tax "
                  "credit eligibility, and the Medicaid expansion level. The "
                  "FPL dollar figures, the applicable-percentage schedule and "
                  "whether the cliff is in force are inputs, not held here",
            authority="healthcare.gov and irs.gov — Form 8962 instructions",
            url="https://www.irs.gov/instructions/i8962 · "
                "https://www.healthcare.gov/lower-costs/",
            cadence=LEGISLATIVE,
            entries=[Entry(
                "all", _hc.ACA_SOURCE, aca_on, aca_unver,
                values={"CLIFF_FPL_PCT": _hc.CLIFF_FPL_PCT,
                        "PTC_FLOOR_FPL_PCT": _hc.PTC_FLOOR_FPL_PCT,
                        "MEDICAID_EXPANSION_FPL_PCT":
                        _hc.MEDICAID_EXPANSION_FPL_PCT})],
        ),
        Table(
            name="§469 passive activity tests, §1031 clocks and §168 recovery",
            module="lib/pf/realestate.py",
            holds="the seven-day short-stay rule, the Real Estate "
                  "Professional hour and majority tests, the material "
                  "participation hour tests, the special allowance phase-out "
                  "rate, the two 1031 deadlines, and the straight-line "
                  "recovery periods for real property",
            authority="irs.gov — Publications 925 and 527, and the Form 8824 "
                      "instructions",
            url="https://www.irs.gov/publications/p925 · "
                "https://www.irs.gov/publications/p527 · "
                "https://www.irs.gov/instructions/i8824",
            cadence=LEGISLATIVE,
            entries=[
                Entry("§469 participation tests", _re.PASSIVE_LOSS_SOURCE,
                      *_parse(_re.PASSIVE_LOSS_VERIFIED),
                      values={"SHORT_STAY_DAYS": _re.SHORT_STAY_DAYS,
                              "REPS_MIN_HOURS": _re.REPS_MIN_HOURS,
                              "REPS_MAJORITY_SHARE": _re.REPS_MAJORITY_SHARE,
                              "MATERIAL_PARTICIPATION_HOURS":
                              _re.MATERIAL_PARTICIPATION_HOURS,
                              "MATERIAL_PARTICIPATION_SAFE_HARBOUR_HOURS":
                              _re.MATERIAL_PARTICIPATION_SAFE_HARBOUR_HOURS,
                              "ALLOWANCE_PHASEOUT_RATE":
                              _re.ALLOWANCE_PHASEOUT_RATE}),
                Entry("§1031 exchange clocks", _re.EXCHANGE_SOURCE,
                      *_parse(_re.EXCHANGE_VERIFIED),
                      values={"EXCHANGE_IDENTIFY_DAYS":
                              _re.EXCHANGE_IDENTIFY_DAYS,
                              "EXCHANGE_CLOSE_DAYS": _re.EXCHANGE_CLOSE_DAYS}),
                Entry("§168 recovery periods", _re.RECOVERY_SOURCE,
                      *_parse(_re.RECOVERY_VERIFIED),
                      values={"RESIDENTIAL_RECOVERY_YEARS":
                              _re.RESIDENTIAL_RECOVERY_YEARS,
                              "COMMERCIAL_RECOVERY_YEARS":
                              _re.COMMERCIAL_RECOVERY_YEARS}),
            ],
        ),
        Table(
            name="§280F vehicle tests and MACRS class life",
            module="lib/pf/depreciation.py",
            holds="the qualified-business-use floor that gates §179 and bonus, "
                  "the two GVWR lines, and the recovery period a vehicle's "
                  "recapture is measured against. The year-specific dollar "
                  "figures are read from the facts file, never held here",
            authority="irs.gov — Publications 463 and 946",
            url="https://www.irs.gov/publications/p946 · "
                "https://www.irs.gov/publications/p463",
            cadence=LEGISLATIVE,
            entries=[Entry(
                "all", _dep.DEPRECIATION_SOURCE, dep_on, dep_unver,
                values={"BUSINESS_USE_FLOOR": _dep.BUSINESS_USE_FLOOR,
                        "HEAVY_GVWR_LBS": _dep.HEAVY_GVWR_LBS,
                        "WORK_VEHICLE_GVWR_LBS": _dep.WORK_VEHICLE_GVWR_LBS,
                        "VEHICLE_RECOVERY_YEARS":
                        _dep.VEHICLE_RECOVERY_YEARS})],
        ),
        Table(
            name="§911 physical presence test",
            module="lib/pf/presence.py",
            holds="the full-day count and the window it is counted in, and "
                  "what makes a day a full day",
            authority="irs.gov — Publication 54",
            url="https://www.irs.gov/publications/p54",
            cadence=LEGISLATIVE,
            entries=[Entry(
                "all", _pre.PRESENCE_SOURCE, pre_on, pre_unver,
                values={"FULL_DAYS_REQUIRED": _pre.FULL_DAYS_REQUIRED,
                        "WINDOW_DAYS": _pre.WINDOW_DAYS,
                        "FULL_DAY_BASIS": _pre.FULL_DAY_BASIS})],
        ),
    ]


def check(today: _dt.date | None = None) -> list[Issue]:
    today = today or _dt.date.today()
    issues: list[Issue] = []

    for table in registry():
        if table.requires_current_year:
            years = {e.key for e in table.entries}
            if str(today.year) not in years:
                issues.append(Issue(
                    table.name, str(today.year), "blocker",
                    f"**{today.year} is missing from `{table.module}`.** Every "
                    f"skill reading it will refuse to answer for the current "
                    f"year — which is the designed behaviour, but it means "
                    f"those skills are inert until the table is updated. "
                    f"Source: {table.authority}."))

        for e in table.entries:
            if e.self_declared_unverified:
                issues.append(Issue(
                    table.name, e.key, "unverified",
                    f"`{e.key}` has never been checked by a human against "
                    f"{table.authority}. It was transcribed and marked as "
                    f"unverified — treat every figure in it as provisional."))
                continue
            if e.verified_on is None:
                issues.append(Issue(
                    table.name, e.key, "unverified",
                    f"`{e.key}` has no parseable verification date."))
                continue
            age = (today - e.verified_on).days
            if age > MAX_AGE_DAYS[table.cadence]:
                issues.append(Issue(
                    table.name, e.key, "stale",
                    f"`{e.key}` last verified {e.verified_on.isoformat()} — "
                    f"{age // 365} year(s) ago, past the "
                    f"{MAX_AGE_DAYS[table.cadence] // 365}-year mark for "
                    f"{table.cadence} data."))
    return issues


def blockers(today: _dt.date | None = None) -> list[Issue]:
    return [i for i in check(today) if i.severity == "blocker"]
