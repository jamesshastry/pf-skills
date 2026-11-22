"""Indian income-tax return workpaper (ITR-2 shape) for one financial year.

The one idea: **residential status decides what India may tax, and the regime
decides how much.** A non-resident is taxed only on India-source income, gets
no s.87A rebate, cannot use the basic exemption limit against special-rate
capital gains, and loses NRE/FCNR interest exemption only by becoming
ordinarily resident. Determine status from the day counts first; everything
downstream is wrong if that is wrong. Then compute the tax under both
regimes (where the choice is open) and say which is lower, what has already
been withheld, and what the U.S. return needs from it.

Basis: nominal Indian rupees of the financial year (1 April - 31 March). USD
appears only in the U.S. hand-off, converted at a rate the facts supply; no
rate is ever fetched.

Statute: FY 2025-26 (AY 2026-27) is governed by the Income-tax Act, 1961 as
amended by the Finance Act 2025. The Income-tax Act, 2025 applies from
1 April 2026, so FY 2026-27 is "tax year 2026-27" under the new Act with
renumbered sections (``IndiaYear.sections``). Section citations in prose use
the 1961 numbering unless the year's table says otherwise.

Refuses (``IndiaReturnError``): business or professional income (ITR-3),
virtual digital assets, clubbing of another person's income, a resident's
foreign income, salary from India, and s.54F/54B claims. Flags without
computing: agricultural income, Schedule FA for residents, DTAA treaty-rate
claims (Form 10F / TRC). Unknown figures are never read as zero: a missing
amount stops the return; a missing TDS figure leaves the refund undetermined.

Not tax advice. It prepares and checks; it does not e-file.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

# ── Statutory constants that do not vary by year in the shipped tables ────

#: s.6(1)(a): 182 days or more in India in the year makes an individual resident.
RESIDENT_DAYS = 182
#: s.6(1)(c): 60 days in the year plus 365 days in the four preceding years.
SHORT_STAY_DAYS = 60
PRIOR_4_YEARS_DAYS = 365
#: s.6(1) Explanation 1(b) (Finance Act 2020): for an Indian citizen or person
#: of Indian origin visiting India whose Indian income exceeds ₹15 lakh, the
#: 60 days becomes 120 days; otherwise 182 days.
VISITOR_HIGH_INCOME_DAYS = 120
INDIAN_INCOME_THRESHOLD = 1_500_000
#: s.6(6)(a): not ordinarily resident if non-resident in 9 of the 10 preceding
#: years, or (b) in India 729 days or less in the 7 preceding years.
RNOR_NR_YEARS_OF_10 = 9
RNOR_MAX_DAYS_PRIOR_7 = 729
#: Plausibility bounds on day counts: a year has at most 366 days, so four
#: and seven years at most 1,461 and 2,557; ten years hold at most ten.
DAY_RANGES = {"days_in_india_this_fy": 366, "days_in_india_prior_4_fy": 1461,
              "days_in_india_prior_7_fy": 2557, "nri_years_in_prior_10": 10}

#: s.2(42A) as amended by Finance (No.2) Act 2024 for transfers on or after
#: 23 July 2024: listed securities and equity-oriented fund units are long
#: term after 12 months; every other capital asset after 24 months.
LISTED_HOLDING_MONTHS = 12
OTHER_HOLDING_MONTHS = 24
#: s.50AA: units of a specified (debt) mutual fund acquired on or after
#: 1 April 2023 are short term whatever the holding period, taxed at slab.
DEBT_MF_CUTOFF = _dt.date(2023, 4, 1)
#: Proviso to s.112(1)(a) (Finance (No.2) Act 2024): the 20%-with-indexation
#: option survives only for RESIDENT individuals/HUFs on land or buildings
#: acquired before this date (tax is the lower of 12.5% without and 20% with
#: indexation). Non-residents get 12.5% without indexation. Confirmed against
#: commentary, not the Act text.
INDEXATION_GRANDFATHER_DATE = _dt.date(2024, 7, 23)
#: s.54 (Finance Act 2023, from AY 2024-25): cost of the new house counted up
#: to ₹10 crore.
S54_CAP = 100_000_000
#: s.54EC: bonds up to ₹50 lakh in a financial year, land or building only
#: (restated in the CBDT FAQs on the Finance (No.2) Bill 2024).
S54EC_CAP = 5_000_000

#: s.10(10D) fourth proviso (Finance Act 2021): ULIPs issued on/after
#: 1 Feb 2021 with aggregate annual premium above ₹2.5 lakh are not exempt;
#: the gain is a capital gain (s.45(1B)).
ULIP_CUTOFF = _dt.date(2021, 2, 1)
ULIP_PREMIUM_LIMIT = 250_000
#: s.10(10D) sixth proviso (Finance Act 2023): non-ULIP policies issued
#: on/after 1 Apr 2023 with aggregate premium above ₹5 lakh are not exempt;
#: the receipt less premiums is other income (s.56(2)(xiii)).
NON_ULIP_CUTOFF = _dt.date(2023, 4, 1)
NON_ULIP_PREMIUM_LIMIT = 500_000
#: s.10(10D)(c)/(d): premium in any year above 20% of sum assured (policies
#: issued 1 Apr 2003 - 31 Mar 2012) or 10% (issued on/after 1 Apr 2012)
#: breaks the exemption. Policies before 1 Apr 2003 have no such test.
PREMIUM_TEST_START = _dt.date(2003, 4, 1)
PREMIUM_TEST_TIGHTEN = _dt.date(2012, 4, 1)
PREMIUM_RATIO_PRE_2012 = 0.20
PREMIUM_RATIO_POST_2012 = 0.10

#: s.80C aggregate cap; s.80TTA cap on savings interest (old regime only;
#: available to non-residents). s.80TTB is for resident senior citizens.
CAP_80C = 150_000
CAP_80TTA = 10_000
CAP_80TTB = 50_000
#: s.80D: ₹25,000 for self/family (₹50,000 if a senior); the absolute
#: maximum with senior parents' cover too is ₹1,00,000. Claims above the
#: self limit are flagged because the split is not recorded.
CAP_80D_SELF = 25_000
CAP_80D_MAX = 100_000
#: s.208: advance tax is due when the year's tax after TDS is ₹10,000 or more.
ADVANCE_TAX_THRESHOLD = 10_000
#: s.234B: interest applies when advance tax paid is below 90% of assessed tax.
ADVANCE_TAX_SHORTFALL_PCT = 0.90
#: s.234A/B/C: simple interest at 1% per month or part of a month.
INTEREST_PER_MONTH = 0.01
#: s.211: cumulative advance-tax instalments (15 Jun, 15 Sep, 15 Dec, 15 Mar).
#: s.234C charges 3 months on the first three shortfalls and 1 on the last.
INSTALMENTS = ((0.15, 3), (0.45, 3), (0.75, 3), (1.00, 1))
#: s.234F late fee; ₹1,000 if total income does not exceed ₹5 lakh.
LATE_FEE = 5_000
LATE_FEE_SMALL = 1_000
LATE_FEE_SMALL_INCOME = 500_000
#: s.139(1) seventh proviso / Rule 12AB: TDS+TCS of ₹25,000 or more
#: (₹50,000 for a resident senior) makes filing mandatory.
TDS_TRIGGER = 25_000
TDS_TRIGGER_SENIOR = 50_000
#: s.288A / s.288B: total income and tax are rounded to the nearest ₹10.
ROUND_TO = 10

#: Transcribed and cross-checked against secondary sources; marked unverified
#: until a human checks the primary text, per the repository's provenance
#: policy.
INDIA_VERIFIED = "unverified"


class IndiaReturnError(ValueError):
    """The inputs cannot support an Indian return without guessing, or ask
    for something this module refuses to compute."""


@dataclass(frozen=True)
class IndiaYear:
    """Rates and limits for one financial year."""
    financial_year: str
    act: str
    source: str
    verified_on: str
    #: (upper bound or None, rate) bands.
    new_slabs: tuple[tuple[float | None, float], ...]
    old_slabs: dict[str, tuple[tuple[float | None, float], ...]]
    #: regime -> (total-income ceiling, maximum rebate); residents only.
    rebate_87a: dict[str, tuple[float, float]]
    #: (threshold, rate) — rate applies when total income exceeds threshold.
    surcharge: tuple[tuple[float, float], ...]
    new_regime_surcharge_max: float
    special_surcharge_cap: float
    cess: float
    stcg_111a: float
    ltcg_112a: float
    ltcg_112a_exemption: float
    ltcg_112: float
    dividend_115a: float
    hp_standard_deduction: float
    self_occupied_interest_cap: float
    hp_loss_setoff_cap: float
    max_self_occupied: int
    due_date: str
    belated_deadline: str
    revised_deadline: str
    #: name -> section citation under the governing Act.
    sections: dict[str, str]


_SECTIONS_1961 = {
    "residence": "s.6", "nre_interest": "s.10(4)(ii)", "fcnr_interest": "s.10(15)(iv)(fa)",
    "insurance": "s.10(10D)", "house_property": "ss.22-24", "hp_setoff": "s.71(3A)",
    "hp_carry": "s.71B", "cg_carry": "s.74", "stcg_equity": "s.111A", "ltcg": "s.112",
    "ltcg_equity": "s.112A", "debt_mf": "s.50AA", "s54": "s.54", "s54ec": "s.54EC",
    "80c": "s.80C", "80d": "s.80D", "80tta": "s.80TTA", "rebate": "s.87A",
    "new_regime": "s.115BAC", "dividend_nr": "s.115A", "return": "s.139(1)",
    "belated": "s.139(4)", "revised": "s.139(5)", "tds_nr": "s.195",
    "int_late": "s.234A", "int_advance": "s.234B", "int_deferral": "s.234C",
    "late_fee": "s.234F", "insurance_other": "s.56(2)(xiii)",
}
#: Income-tax Act 2025 numbering, from published old-to-new concordances
#: (secondary). Keys absent here could not be confirmed and fall back to the
#: 1961 number marked "(1961 numbering)".
_SECTIONS_2025 = {
    "residence": "s.6", "stcg_equity": "s.196", "ltcg": "s.197",
    "ltcg_equity": "s.198", "s54": "s.82", "s54ec": "s.85", "80c": "s.123",
    "80d": "s.126", "rebate": "s.156", "new_regime": "s.202",
    "return": "s.263(1)", "belated": "s.263(4)", "revised": "s.263(5)",
    "tds_nr": "s.393(2)", "int_late": "s.423", "int_advance": "s.424",
    "int_deferral": "s.425", "late_fee": "s.428",
}

_NEW_SLABS_2025 = ((400_000, 0.0), (800_000, 0.05), (1_200_000, 0.10),
                   (1_600_000, 0.15), (2_000_000, 0.20), (2_400_000, 0.25),
                   (None, 0.30))
_OLD_SLABS = {
    "below_60": ((250_000, 0.0), (500_000, 0.05), (1_000_000, 0.20), (None, 0.30)),
    #: First Schedule Part I Para A(II)/(III): the higher exemptions are for
    #: an individual "being a resident in India" aged 60+/80+.
    "senior": ((300_000, 0.0), (500_000, 0.05), (1_000_000, 0.20), (None, 0.30)),
    "super_senior": ((500_000, 0.0), (1_000_000, 0.20), (None, 0.30)),
}
_SURCHARGE = ((5_000_000, 0.10), (10_000_000, 0.15), (20_000_000, 0.25),
              (50_000_000, 0.37))

INDIA_TABLES: dict[str, IndiaYear] = {
    "2025-26": IndiaYear(
        financial_year="2025-26",
        act="Income-tax Act, 1961 (AY 2026-27)",
        source="Finance Act 2025, First Schedule; incometax.gov.in 'Tax rates' "
               "help page for AY 2026-27 (slabs, surcharge, 87A, cess); "
               "capital gains per CBDT FAQs on the Finance (No.2) Bill 2024 "
               "(20% s.111A, 12.5% s.112/112A, ₹1.25 lakh s.112A exemption, "
               "12/24-month holding, ₹50 lakh s.54EC — via taxscan.in, as "
               "incometaxindia.gov.in returned 403); resident-only indexation "
               "proviso to s.112(1)(a) and Finance Act 2023 ₹10 crore s.54 cap "
               "per taxguru.in commentary; due dates per Finance Act "
               "2026 commentary (revised return to 31 Mar 2027 — confirm on the "
               "e-filing portal)",
        verified_on=INDIA_VERIFIED,
        new_slabs=_NEW_SLABS_2025,
        old_slabs=_OLD_SLABS,
        rebate_87a={"new": (1_200_000, 60_000), "old": (500_000, 12_500)},
        surcharge=_SURCHARGE,
        new_regime_surcharge_max=0.25,
        special_surcharge_cap=0.15,
        cess=0.04,
        stcg_111a=0.20, ltcg_112a=0.125, ltcg_112a_exemption=125_000,
        ltcg_112=0.125, dividend_115a=0.20,
        hp_standard_deduction=0.30, self_occupied_interest_cap=200_000,
        hp_loss_setoff_cap=200_000, max_self_occupied=2,
        due_date="2026-07-31", belated_deadline="2026-12-31",
        revised_deadline="2027-03-31",
        sections=dict(_SECTIONS_1961),
    ),
    "2026-27": IndiaYear(
        financial_year="2026-27",
        act="Income-tax Act, 2025 (tax year 2026-27)",
        source="Income-tax Act, 2025 (in force 1 Apr 2026); Union Budget / "
               "Finance Act 2026 reported no change to slabs, rebate or "
               "capital-gains rates (secondary sources); section numbers from "
               "published 1961-to-2025 concordances — verify against the Act",
        verified_on=INDIA_VERIFIED,
        new_slabs=_NEW_SLABS_2025,
        old_slabs=_OLD_SLABS,
        rebate_87a={"new": (1_200_000, 60_000), "old": (500_000, 12_500)},
        surcharge=_SURCHARGE,
        new_regime_surcharge_max=0.25,
        special_surcharge_cap=0.15,
        cess=0.04,
        stcg_111a=0.20, ltcg_112a=0.125, ltcg_112a_exemption=125_000,
        ltcg_112=0.125, dividend_115a=0.20,
        hp_standard_deduction=0.30, self_occupied_interest_cap=200_000,
        hp_loss_setoff_cap=200_000, max_self_occupied=2,
        due_date="2027-07-31", belated_deadline="2027-12-31",
        revised_deadline="2028-03-31",
        sections={k: _SECTIONS_2025.get(k, f"{v} (1961 numbering)")
                  for k, v in _SECTIONS_1961.items()},
    ),
}


def table_for(fy: str) -> tuple[IndiaYear, bool]:
    """The year's table, or the nearest shipped one and True (a projection
    for a later year, a back-cast for an earlier one)."""
    if fy in INDIA_TABLES:
        return INDIA_TABLES[fy], False
    years = sorted(INDIA_TABLES)
    nearest = years[0] if fy < years[0] else years[-1]
    return INDIA_TABLES[nearest], True


def fy_start(fy: str) -> int:
    try:
        start, end = str(fy).split("-")
        s = int(start)
        if int(end) != (s + 1) % 100:
            raise ValueError
        return s
    except ValueError as e:
        raise IndiaReturnError(f"financial year {fy!r} is not of the form 2025-26") from e


# ── small helpers ──────────────────────────────────────────────────────────

def _date(v) -> _dt.date | None:
    if v is None:
        return None
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    try:
        return _dt.date.fromisoformat(str(v))
    except ValueError as e:
        raise IndiaReturnError(f"{v!r} is not an ISO date") from e


def _months_held(acquired: _dt.date, sold: _dt.date) -> int:
    """Whole months held; a partial month does not count toward 'more than'."""
    m = (sold.year - acquired.year) * 12 + sold.month - acquired.month
    if sold.day < acquired.day:
        m -= 1
    return m


def _long_term(acquired: _dt.date, sold: _dt.date, months: int) -> bool:
    """'More than' N months: held at least N whole months and a day."""
    held = _months_held(acquired, sold)
    return held > months or (held == months and sold.day != acquired.day)


def round10(x: float) -> float:
    """s.288A/288B: nearest ₹10, five rounding up."""
    return float(int((x + 5) // ROUND_TO) * ROUND_TO) if x >= 0 else -round10(-x)


def slab_tax(income: float, slabs) -> float:
    tax, lower = 0.0, 0.0
    for upper, rate in slabs:
        if income <= lower:
            break
        top = income if upper is None else min(income, upper)
        tax += (top - lower) * rate
        if upper is None:
            break
        lower = upper
    return tax


def basic_exemption(slabs) -> float:
    return float(slabs[0][0])


# ── residential status ─────────────────────────────────────────────────────

NR, RNOR, ROR = "non_resident", "resident_not_ordinarily_resident", "resident_ordinarily_resident"
STATUS_LABEL = {NR: "Non-resident (NR)", RNOR: "Resident but not ordinarily resident (RNOR)",
                ROR: "Resident and ordinarily resident (ROR)"}


@dataclass
class Residence:
    status: str
    basis: str
    indian_income: float
    findings: list[str] = field(default_factory=list)

    @property
    def resident(self) -> bool:
        return self.status != NR


def residence(tp: dict, *, indian_citizen: bool | None, indian_income: float,
              sec: str = "s.6") -> Residence:
    """s.6 as amended by Finance Act 2020. ``indian_income`` is total income
    other than income from foreign sources."""
    days = tp.get("days_in_india_this_fy")
    if days is None:
        raise IndiaReturnError("taxpayer.days_in_india_this_fy is not recorded; "
                               "residential status cannot be determined")
    days = int(days)
    for key, top in DAY_RANGES.items():
        v = tp.get(key)
        if v is not None and not 0 <= int(v) <= top:
            raise IndiaReturnError(f"taxpayer.{key} = {v} is outside 0-{top}")
    prior4 = tp.get("days_in_india_prior_4_fy")
    pio = tp.get("person_of_indian_origin")
    visiting = tp.get("visiting_india", True)
    leaving = bool(tp.get("left_india_for_employment_this_fy", False))
    high = indian_income > INDIAN_INCOME_THRESHOLD
    out: list[str] = []
    resident, via, rnor_forced = False, "", False

    if days >= RESIDENT_DAYS:
        resident, via = True, f"{days} days in India (≥ {RESIDENT_DAYS}) — {sec}(1)(a)"
    elif days >= SHORT_STAY_DAYS:
        if prior4 is None:
            raise IndiaReturnError(
                f"{days} days in India is within the 60-181 day band, so "
                "taxpayer.days_in_india_prior_4_fy decides residence and is not recorded")
        if int(prior4) >= PRIOR_4_YEARS_DAYS:
            indian_link = indian_citizen or pio
            if indian_link is None:
                raise IndiaReturnError(
                    "whether the taxpayer is an Indian citizen or person of Indian "
                    "origin decides the 60/120/182-day test; record "
                    "person_of_indian_origin")
            if leaving and indian_citizen is None:
                raise IndiaReturnError(
                    "the 182-day rule for a citizen leaving India for employment "
                    "turns on Indian citizenship, which is not recorded on the "
                    "member or as taxpayer.indian_citizen")
            if leaving and indian_citizen:
                threshold, why = RESIDENT_DAYS, "citizen leaving India for employment"
            elif indian_link and visiting:
                threshold = VISITOR_HIGH_INCOME_DAYS if high else RESIDENT_DAYS
                why = ("citizen/PIO visiting, Indian income above ₹15 lakh" if high
                       else "citizen/PIO visiting, Indian income ₹15 lakh or less")
            else:
                threshold, why = SHORT_STAY_DAYS, "no visitor relaxation"
            if days >= threshold:
                resident = True
                via = (f"{days} days in the year and {int(prior4)} in the four "
                       f"preceding years; the day test is {threshold} ({why}) — "
                       f"{sec}(1)(c)")
                if threshold == VISITOR_HIGH_INCOME_DAYS:
                    rnor_forced = True
            else:
                via = (f"{days} days is below the {threshold}-day test that applies "
                       f"({why})")
        else:
            via = (f"{days} days in the year but only {int(prior4)} in the four "
                   f"preceding years (< {PRIOR_4_YEARS_DAYS})")
    else:
        via = f"{days} days in India (< {SHORT_STAY_DAYS})"

    if not resident and high and indian_citizen is None:
        raise IndiaReturnError(
            f"Indian income above ₹15 lakh makes Indian citizenship decide deemed "
            f"residence ({sec}(1A)); record citizenship on the member or "
            "taxpayer.indian_citizen")
    if not resident and indian_citizen and high:
        liable = tp.get("liable_to_tax_elsewhere")
        if liable is None:
            raise IndiaReturnError(
                "an Indian citizen with Indian income above ₹15 lakh is deemed "
                f"resident ({sec}(1A)) unless liable to tax in another country; "
                "record liable_to_tax_elsewhere")
        if not liable:
            resident, rnor_forced = True, True
            via = (f"deemed resident {sec}(1A): Indian citizen, Indian income above "
                   "₹15 lakh, not liable to tax elsewhere by residence or domicile")

    if not resident:
        return Residence(NR, via, indian_income, out)
    if rnor_forced:
        return Residence(RNOR, via + "; RNOR by statute (s.6(6)(c)/(d))",
                         indian_income, out)
    nr_years = tp.get("nri_years_in_prior_10")
    prior7 = tp.get("days_in_india_prior_7_fy")
    if nr_years is not None and int(nr_years) >= RNOR_NR_YEARS_OF_10:
        return Residence(RNOR, via + f"; non-resident in {int(nr_years)} of the 10 "
                         "preceding years", indian_income, out)
    if prior7 is not None and int(prior7) <= RNOR_MAX_DAYS_PRIOR_7:
        return Residence(RNOR, via + f"; {int(prior7)} days in the 7 preceding years "
                         f"(≤ {RNOR_MAX_DAYS_PRIOR_7})", indian_income, out)
    if nr_years is None or prior7 is None:
        raise IndiaReturnError(
            "resident this year; whether ordinarily resident turns on "
            "nri_years_in_prior_10 and days_in_india_prior_7_fy, which are not "
            "both recorded")
    return Residence(ROR, via, indian_income, out)


# ── income lines ───────────────────────────────────────────────────────────

PASSIVE, GENERAL = "passive", "general"

INTEREST_KINDS = {"nro_savings", "nro_fd", "nre_savings", "nre_fd", "fcnr", "other"}
EXEMPT_FOR_NONORDINARY = {"nre_savings", "nre_fd", "fcnr"}
CG_ASSETS = {"listed_equity", "equity_mf", "debt_mf", "property", "unlisted", "gold"}
INSURANCE_KINDS = {"ulip", "endowment", "money_back"}

#: Input keys this module refuses, with where to go instead.
REFUSED = {
    "business_income": "business or professional income needs ITR-3; not modelled",
    "salary": "Indian salary is not modelled by this workpaper",
    "vda": "virtual digital assets (s.115BBH) are not modelled",
    "crypto": "virtual digital assets (s.115BBH) are not modelled",
    "clubbing": "clubbing of another person's income is not modelled",
    "foreign_income": "a resident's foreign income is not modelled; this "
                      "workpaper covers India-source income only",
}


@dataclass
class Line:
    """One income item after classification."""
    head: str          # interest | house_property | capital_gains | insurance | dividends
    name: str
    pool: str          # slab | hp | stcg_slab | stcg_111a | ltcg_112 | ltcg_112a | div_115a | exempt
    amount: float      # Indian-basis income (may be negative for losses)
    tds: float | None
    gross_inr: float   # gross receipt, for the U.S. hand-off
    us_category: str = PASSIVE
    note: str = ""
    #: interest account kind (for s.80TTA); s.54/54EC exemption on a gain.
    kind: str = ""
    exempt_54: float = 0.0


def _amount(row: dict, key: str, label: str, missing: list[str]) -> float:
    v = row.get(key)
    if v is None:
        missing.append(f"{label}.{key}")
        return 0.0
    return float(v)


def _nre_exempt(status: str, fema_outside: bool | None) -> tuple[bool, str]:
    """s.10(4)(ii) turns on FEMA status ("person resident outside India"),
    not income-tax residence. A non-resident with FEMA status unrecorded is
    treated as outside India (the usual case) and the note says so; for a
    resident (RNOR/ROR) the two diverge often enough that it must be recorded."""
    if fema_outside is True:
        return True, "exempt — s.10(4)(ii), person resident outside India (FEMA)"
    if fema_outside is False:
        return False, "taxable — FEMA status is resident in India, so s.10(4)(ii) does not apply"
    if status == NR:
        return True, ("exempt — s.10(4)(ii), assuming FEMA status resident outside "
                      "India (not recorded)")
    raise IndiaReturnError(
        "NRE interest exemption (s.10(4)(ii)) turns on FEMA status, which is not "
        "recorded and is not implied for a resident; record "
        "taxpayer.fema_resident_outside_india")


def interest_lines(rows: list[dict], status: str, missing: list[str],
                   fema_outside: bool | None = None) -> list[Line]:
    out = []
    for r in rows or []:
        name = str(r.get("account", "interest"))
        kind = r.get("kind")
        if kind not in INTEREST_KINDS:
            raise IndiaReturnError(f"interest {name!r}: kind {kind!r} is not one of "
                                   f"{sorted(INTEREST_KINDS)}")
        amt = _amount(r, "amount_inr", f"interest[{name}]", missing)
        tds = r.get("tds_inr")
        if kind == "fcnr":
            exempt = status != ROR
            note = ("exempt — s.10(15)(iv)(fa), non-resident/RNOR" if exempt
                    else "taxable — FCNR exemption lost once ordinarily resident")
        elif kind in EXEMPT_FOR_NONORDINARY:
            exempt, note = _nre_exempt(status, fema_outside)
        else:
            exempt, note = False, "taxable at slab"
        if exempt:
            out.append(Line("interest", name, "exempt", amt,
                            None if tds is None else float(tds), amt, note=note,
                            kind=kind))
        else:
            out.append(Line("interest", name, "slab", amt,
                            None if tds is None else float(tds), amt, note=note,
                            kind=kind))
    return out


@dataclass
class Property:
    name: str
    status: str
    share: float
    annual_value: float
    municipal_tax: float
    interest: float
    tds: float | None
    gross_rent: float


def properties(rows: list[dict], cap: int, missing: list[str]) -> list[Property]:
    out = []
    for r in rows or []:
        name = str(r.get("name", "property"))
        st = r.get("status")
        share = float(r.get("co_owner_share", 1.0) if r.get("co_owner_share") is not None else 1.0)
        if not 0 < share <= 1:
            raise IndiaReturnError(f"house_property {name!r}: co_owner_share must be in (0, 1]")
        lbl = f"house_property[{name}]"
        interest = _amount(r, "home_loan_interest_inr", lbl, missing)
        if st == "let_out":
            rent = _amount(r, "gross_rent_inr", lbl, missing)
            av = rent
        elif st == "deemed_let_out":
            av = _amount(r, "expected_rent_inr", lbl, missing)
            rent = 0.0
        elif st == "self_occupied":
            av, rent = 0.0, 0.0
        else:
            raise IndiaReturnError(f"house_property {name!r}: status {st!r} is not "
                                   "let_out | self_occupied | deemed_let_out")
        mtax = 0.0 if st == "self_occupied" else _amount(r, "municipal_tax_paid_inr", lbl, missing)
        tds = r.get("tds_inr")
        out.append(Property(name, st, share, av * share, mtax * share,
                            interest * share, None if tds is None else float(tds),
                            rent * share))
    n_so = sum(1 for p in out if p.status == "self_occupied")
    if n_so > cap:
        raise IndiaReturnError(
            f"{n_so} properties are marked self_occupied; s.23(4) allows {cap}. "
            "Choose which, and mark the rest deemed_let_out with expected_rent_inr")
    return out


def _in_year(d: _dt.date, bounds, what: str) -> None:
    """A sale or maturity outside the financial year belongs to another
    return — and before 23 July 2024 to different rates."""
    if bounds and not bounds[0] <= d <= bounds[1]:
        raise IndiaReturnError(f"{what} {d.isoformat()} is outside the financial year "
                               f"{bounds[0].isoformat()} to {bounds[1].isoformat()}")


def cg_lines(rows: list[dict], status: str, missing: list[str],
             findings: list[str], bounds=None) -> list[Line]:
    out = []
    ec_used = 0.0     # s.54EC limit is per financial year, across all sales
    for i, r in enumerate(rows or []):
        asset = r.get("asset")
        name = str(r.get("name") or f"{asset} #{i + 1}")
        lbl = f"capital_gains[{name}]"
        if asset not in CG_ASSETS:
            raise IndiaReturnError(f"capital gain {name!r}: asset {asset!r} is not one "
                                   f"of {sorted(CG_ASSETS)}")
        if r.get("exemption_54f_inr") or r.get("exemption_54b_inr"):
            raise IndiaReturnError(f"{name!r}: s.54F/54B claims are not modelled")
        acq, sold = _date(r.get("acquired")), _date(r.get("sold"))
        if acq is None:
            missing.append(f"{lbl}.acquired")
        if sold is None:
            missing.append(f"{lbl}.sold")
        sale = _amount(r, "sale_inr", lbl, missing)
        cost = _amount(r, "cost_inr", lbl, missing)
        exp = float(r.get("transfer_expenses_inr") or 0)
        tds = r.get("tds_inr")
        tds = None if tds is None else float(tds)
        if acq is None or sold is None:
            continue
        _in_year(sold, bounds, f"capital gain {name!r}: sold")
        gain = sale - cost - exp
        stt = r.get("stt_paid")
        note = ""
        if asset in ("listed_equity", "equity_mf") and stt is None:
            # Unknown STT is not the favourable s.111A/112A treatment.
            missing.append(f"{lbl}.stt_paid")
            continue
        if asset in ("listed_equity", "equity_mf"):
            lt = _long_term(acq, sold, LISTED_HOLDING_MONTHS)
            if stt:
                pool = "ltcg_112a" if lt else "stcg_111a"
            else:
                pool = "ltcg_112" if lt else "stcg_slab"
                note = "no STT — s.111A/112A unavailable"
        elif asset == "debt_mf":
            if acq >= DEBT_MF_CUTOFF:
                pool, note = "stcg_slab", "s.50AA — deemed short term, slab"
            else:
                pool = ("ltcg_112" if _long_term(acq, sold, OTHER_HOLDING_MONTHS)
                        else "stcg_slab")
        else:
            lt = _long_term(acq, sold, OTHER_HOLDING_MONTHS)
            pool = "ltcg_112" if lt else "stcg_slab"
            if asset == "property" and lt and acq < INDEXATION_GRANDFATHER_DATE:
                if status == NR:
                    note = ("12.5% without indexation — the 20%-with-indexation "
                            "option is for residents only")
                else:
                    note = ("resident: compare 20% with indexation (cost inflation "
                            "index not encoded) — not computed")
                    findings.append(
                        f"{name}: as a resident you may elect 20% with indexation "
                        "instead of 12.5% without; the cost inflation index is not "
                        "in this module, so only the 12.5% figure is computed — an "
                        "upper bound if indexation would be cheaper.")
            if asset == "unlisted" and status == NR:
                note = ("non-resident: first proviso to s.48 computes the gain in "
                        "the currency of purchase (Rule 115A) — not modelled")
        exempt = 0.0
        if gain > 0 and asset == "property":
            e54 = float(r.get("exemption_54_inr") or 0)
            e54ec = float(r.get("exemption_54ec_inr") or 0)
            if e54 and pool == "ltcg_112":
                if not r.get("residential"):
                    raise IndiaReturnError(f"{name!r}: s.54 needs a residential house sold "
                                           "(set residential: true)")
                exempt += min(gain, min(e54, S54_CAP))
            if e54ec and pool == "ltcg_112":
                room = max(0.0, S54EC_CAP - ec_used)
                use = min(gain - exempt, e54ec, room)
                exempt += use
                ec_used += use
                if e54ec > room:
                    findings.append(f"{name}: s.54EC limited to ₹50 lakh per financial "
                                    f"year across all sales; ₹{room:,.0f} of room was left.")
            if (e54 or e54ec) and pool != "ltcg_112":
                findings.append(f"{name}: s.54/54EC apply only to long-term gains; "
                                "the claimed reinvestment was ignored.")
            if exempt:
                note = (note + "; " if note else "") + f"₹{exempt:,.0f} exempt s.54/54EC"
        elif r.get("exemption_54_inr") or r.get("exemption_54ec_inr"):
            findings.append(f"{name}: s.54/54EC apply only to gains on land or "
                            "buildings; the claimed reinvestment was ignored.")
        if gain < 0:
            note = (note + "; " if note else "") + (
                "short-term loss — set off against any gain" if pool in ("stcg_slab", "stcg_111a")
                else "long-term loss — set off against long-term gains only")
        out.append(Line("capital_gains", name, pool, gain - exempt, tds, sale,
                        note=note, exempt_54=exempt))
    return out


def insurance_lines(rows: list[dict], missing: list[str],
                    findings: list[str], bounds=None) -> list[Line]:
    out = []
    pol = []
    for r in rows or []:
        name = str(r.get("policy", "policy"))
        kind = r.get("kind")
        if kind not in INSURANCE_KINDS:
            raise IndiaReturnError(f"insurance {name!r}: kind {kind!r} is not one of "
                                   f"{sorted(INSURANCE_KINDS)}")
        issued = _date(r.get("issued"))
        if issued is None:
            missing.append(f"insurance_maturities[{name}].issued")
        pol.append((r, name, kind, issued))
    ulip_agg = sum(float(r.get("annual_premium_inr") or 0) for r, _, k, d in pol
                   if k == "ulip" and d and d >= ULIP_CUTOFF)
    other_agg = sum(float(r.get("annual_premium_inr") or 0) for r, _, k, d in pol
                    if k != "ulip" and d and d >= NON_ULIP_CUTOFF)
    for r, name, kind, issued in pol:
        lbl = f"insurance_maturities[{name}]"
        maturity = _amount(r, "maturity_inr", lbl, missing)
        premiums = _amount(r, "total_premiums_inr", lbl, missing)
        tds = r.get("tds_inr")
        tds = None if tds is None else float(tds)
        if issued is None:
            continue
        if r.get("on_death"):
            out.append(Line("insurance", name, "exempt", maturity - premiums, tds,
                            maturity, note="death benefit — always exempt s.10(10D)"))
            continue
        annual = _amount(r, "annual_premium_inr", lbl, missing)
        sa = _amount(r, "sum_assured_inr", lbl, missing)
        gain = maturity - premiums
        matured = _date(r.get("matured"))
        if matured is not None:
            _in_year(matured, bounds, f"insurance {name!r}: matured")
        ratio_reason = agg_reason = ""
        if issued >= PREMIUM_TEST_START and sa > 0:
            ratio = PREMIUM_RATIO_POST_2012 if issued >= PREMIUM_TEST_TIGHTEN else PREMIUM_RATIO_PRE_2012
            if annual > ratio * sa:
                ratio_reason = f"premium above {ratio:.0%} of sum assured"
        elif issued >= PREMIUM_TEST_START and sa <= 0:
            missing.append(f"{lbl}.sum_assured_inr")
        if kind == "ulip" and issued >= ULIP_CUTOFF and ulip_agg > ULIP_PREMIUM_LIMIT:
            agg_reason = (f"ULIP issued on/after 1 Feb 2021, aggregate premium "
                          f"₹{ulip_agg:,.0f} > ₹2.5 lakh")
        if kind != "ulip" and issued >= NON_ULIP_CUTOFF and other_agg > NON_ULIP_PREMIUM_LIMIT:
            agg_reason = (f"issued on/after 1 Apr 2023, aggregate premium "
                          f"₹{other_agg:,.0f} > ₹5 lakh")
        reason = ratio_reason or agg_reason
        if not reason:
            out.append(Line("insurance", name, "exempt", gain, tds, maturity,
                            note="exempt s.10(10D)"))
            continue
        # s.45(1B) makes a ULIP a capital asset only where the exemption
        # fails under the ₹2.5 lakh provisos. A ULIP failing the
        # premium-to-sum-assured test is other income, like any policy.
        if kind == "ulip" and agg_reason and not ratio_reason:
            eq = r.get("equity_oriented")
            if matured is None or eq is None:
                if matured is None:
                    missing.append(f"{lbl}.matured")
                if eq is None:
                    missing.append(f"{lbl}.equity_oriented")
                continue
            if eq:
                lt = _long_term(issued, matured, LISTED_HOLDING_MONTHS)
                pool = "ltcg_112a" if lt else "stcg_111a"
            else:
                lt = _long_term(issued, matured, OTHER_HOLDING_MONTHS)
                pool = "ltcg_112" if lt else "stcg_slab"
                findings.append(f"{name}: a non-equity ULIP outside s.10(10D) is "
                                "treated here as an ordinary capital asset — verify.")
            out.append(Line("insurance", name, pool, gain, tds, maturity,
                            note=f"not exempt ({reason}) — capital gain s.45(1B)"))
        else:
            if kind == "ulip" and agg_reason:
                findings.append(f"{name}: fails both the premium-ratio test and the "
                                "₹2.5 lakh ULIP test; taxed as other income on the "
                                "ratio failure — verify whether s.45(1B) applies instead.")
            amt = max(0.0, gain)
            note = f"not exempt ({reason}) — other income, receipt less premiums"
            if gain < 0:
                note += "; negative result floored at nil (not a loss)"
            out.append(Line("insurance", name, "slab", amt, tds, maturity, note=note))
    if pol:
        findings.append("The s.10(10D) aggregate-premium tests count every policy you "
                        "hold, not only those maturing this year; the aggregate here "
                        "uses only the policies listed.")
    return out


def dividend_lines(rows: list[dict], status: str, missing: list[str]) -> list[Line]:
    out = []
    for r in rows or []:
        name = str(r.get("payer", "dividends"))
        amt = _amount(r, "amount_inr", f"dividends[{name}]", missing)
        tds = r.get("tds_inr")
        pool = "div_115a" if status == NR else "div_slab"
        note = ("non-resident — 20% under s.115A, no deductions" if status == NR
                else "slab; surcharge capped at 15%")
        out.append(Line("dividends", name, pool, amt, None if tds is None else float(tds),
                        amt, note=note))
    return out


# ── regime computation ─────────────────────────────────────────────────────

#: Pools taxed at slab rates. ``div_slab`` is a resident's dividends: slab
#: rate, but its surcharge is capped like special-rate income.
SLAB_POOLS = ("slab", "div_slab", "stcg_slab", "hp")
SPECIAL_POOLS = ("stcg_111a", "ltcg_112", "ltcg_112a", "div_115a")
ALL_POOLS = SLAB_POOLS + SPECIAL_POOLS
#: s.70(2): a short-term capital loss may be set off against any capital gain.
CG_POOLS = ("stcg_slab", "stcg_111a", "ltcg_112", "ltcg_112a")
#: s.70(3): a long-term capital loss only against long-term gains.
LT_POOLS = ("ltcg_112", "ltcg_112a")
#: s.71: a house-property loss against any other head (capital gains included).
OTHER_HEAD_POOLS = ("slab", "div_slab", "stcg_slab", "stcg_111a", "div_115a",
                    "ltcg_112", "ltcg_112a")
#: The finding that goes with any loss set-off: the order is chosen to
#: minimise tax, which the statute permits but does not prescribe.
SETOFF_BASIS = ("Losses are set off in the order that minimises tax, within what "
                "ss.70, 71 and 74 permit (s.70 intra-head first, then s.71 across "
                "heads, then brought-forward losses). The taxpayer's freedom to "
                "choose that order rests on tribunal rulings (e.g. ITAT, Montgomery "
                "Emerging Markets Fund), not on express statutory text.")


@dataclass
class RegimeResult:
    regime: str
    hp_income: float
    pools: dict[str, float]
    gross_total_income: float
    deductions: dict[str, float]
    total_income: float
    slab_income: float
    exemption_used_against_special: float
    slab_tax: float
    special_tax: dict[str, float]
    rebate: float
    surcharge: float
    marginal_relief: float
    cess: float
    tax: float
    carry_forward: dict[str, float]
    notes: list[str] = field(default_factory=list)
    losses_set_off: bool = False


def _slabs(t: IndiaYear, regime: str, resident: bool, age_band: str) -> tuple:
    if regime == "new":
        return t.new_slabs
    return t.old_slabs[age_band if resident else "below_60"]


def _surcharge_rate(t: IndiaYear, income: float, regime: str) -> float:
    rate = 0.0
    for threshold, r in t.surcharge:
        if income > threshold:
            rate = r
    if regime == "new":
        rate = min(rate, t.new_regime_surcharge_max)
    return rate


def _deductions(regime: str, resident: bool, age_band: str, lines: list[Line],
                deductions_in: dict, ordinary: float, notes: list[str],
                missing: list[str]) -> dict[str, float]:
    """Chapter VI-A (old regime only), limited to ordinary income."""
    if regime != "old":
        return {}
    out: dict[str, float] = {}
    d = deductions_in or {}
    for key, cap in (("80c_inr", CAP_80C), ("80d_inr", CAP_80D_MAX), ("other_inr", None)):
        v = d.get(key)
        if v is None:
            if key in d:
                missing.append(f"deductions_old_regime.{key}")
            continue
        v = float(v)
        if key == "80d_inr" and v > CAP_80D_SELF:
            notes.append(f"s.80D claim of ₹{v:,.0f} exceeds ₹{CAP_80D_SELF:,.0f}; it is "
                         "allowed only with senior or parents' cover — verify the split.")
        if cap is not None and v > cap:
            notes.append(f"{key[:-4].upper()} claim capped at ₹{cap:,.0f}.")
            v = cap
        if v:
            out[key.replace("_inr", "").upper()] = v
    taxable_interest = [ln for ln in lines if ln.head == "interest" and ln.pool == "slab"]
    if resident and age_band != "below_60":
        deposits = sum(ln.amount for ln in taxable_interest if ln.kind != "other")
        if deposits:
            out["80TTB"] = min(CAP_80TTB, deposits)
    else:
        savings = sum(ln.amount for ln in taxable_interest if ln.kind == "nro_savings")
        if savings:
            out["80TTA"] = min(CAP_80TTA, savings)
    total = sum(out.values())
    if total > ordinary:
        notes.append("Chapter VI-A deductions limited to income other than "
                     "special-rate capital gains and s.115A dividends.")
        scale = ordinary / total if total else 0
        out = {k: v * scale for k, v in out.items()}
    return out


@dataclass
class _Assessed:
    gti: float
    deductions: dict[str, float]
    ti: float
    slab_income: float
    exemption_used: float
    s_tax: float
    sp_tax: dict[str, float]
    rebate: float
    surcharge: float
    relief: float
    cess: float
    tax: float


def _assess(t: IndiaYear, regime: str, *, resident: bool, age_band: str,
            pools: dict[str, float], lines: list[Line], deductions_in: dict,
            notes: list[str], missing: list[str], exact: bool = True) -> _Assessed:
    """Tax on pools already net of every set-off. ``exact=False`` skips the
    ₹10 rounding so the set-off search sees smooth differences."""
    rnd = round10 if exact else (lambda x: x)
    pos = {k: max(0.0, pools.get(k, 0.0)) for k in ALL_POOLS}
    gti = sum(pos.values())
    special_total = sum(pos[k] for k in SPECIAL_POOLS)
    ordinary = gti - special_total
    deductions = _deductions(regime, resident, age_band, lines, deductions_in,
                             ordinary, notes, missing)
    ti = rnd(gti - sum(deductions.values()))
    slab_income = max(0.0, ti - special_total)

    slabs = _slabs(t, regime, resident, age_band)
    exemption_used = 0.0
    special = {k: pos[k] for k in SPECIAL_POOLS}
    if resident:
        shortfall = max(0.0, basic_exemption(slabs) - slab_income)
        for k in ("stcg_111a", "ltcg_112", "ltcg_112a"):
            use = min(shortfall, special[k])
            special[k] -= use
            shortfall -= use
            exemption_used += use
    elif special_total and slab_income < basic_exemption(slabs):
        notes.append("Non-resident: the unused basic exemption cannot reduce "
                     "special-rate gains (provisos to ss.111A/112/112A).")
    s_tax = slab_tax(slab_income, slabs)
    sp_tax = {
        "stcg_111a": special["stcg_111a"] * t.stcg_111a,
        "ltcg_112": special["ltcg_112"] * t.ltcg_112,
        "ltcg_112a": max(0.0, special["ltcg_112a"] - t.ltcg_112a_exemption) * t.ltcg_112a,
        "div_115a": special["div_115a"] * t.dividend_115a,
    }

    # Rebate s.87A — residents only.
    rebate = 0.0
    if resident:
        limit, cap = t.rebate_87a[regime]
        if regime == "new":
            if ti <= limit:
                rebate = min(cap, s_tax)
            elif s_tax > ti - limit:
                # Marginal relief: tax on slab income may not exceed the income
                # above the limit (runs out near ₹12,70,588 on FY 2025-26 slabs).
                rebate = s_tax - (ti - limit)
        elif ti <= limit:
            rebate = min(cap, s_tax + sp_tax["stcg_111a"] + sp_tax["ltcg_112"])
    tax_after_rebate = s_tax + sum(sp_tax.values()) - rebate

    # Surcharge: full rate on slab tax; capped at 15% on s.111A/112/112A tax
    # and on dividends (First Schedule since Finance Act 2022), including the
    # dividend share of a resident's slab tax, apportioned pro rata.
    rate = _surcharge_rate(t, ti, regime)
    capped = min(rate, t.special_surcharge_cap)
    slab_base = sum(pos[k] for k in SLAB_POOLS)
    div_share = pos["div_slab"] / slab_base if slab_base else 0.0
    net_slab = max(0.0, s_tax - rebate)
    ordinary_tax = net_slab * (1 - div_share)
    capped_tax = net_slab * div_share + sum(sp_tax.values())
    surcharge = ordinary_tax * rate + capped_tax * capped
    relief = 0.0
    if rate:
        threshold = max(th for th, _ in t.surcharge if ti > th)
        lower_rate = _surcharge_rate(t, threshold, regime)
        # Tax on income of exactly the threshold: the excess comes off slab
        # income first, then off special-rate income pro rata.
        over = ti - threshold
        slab_at = max(0.0, slab_income - over)
        rest = over - (slab_income - slab_at)
        special_base = sum(special.values()) or 1.0
        sp_scale = max(0.0, 1 - rest / special_base) if rest > 0 else 1.0
        slab_tax_at = slab_tax(slab_at, slabs)
        ord_at = slab_tax_at * (1 - div_share)
        cap_at = slab_tax_at * div_share + sum(sp_tax.values()) * sp_scale
        at_threshold = (ord_at + cap_at + ord_at * lower_rate
                        + cap_at * min(lower_rate, t.special_surcharge_cap))
        excess = (tax_after_rebate + surcharge) - at_threshold
        if excess > over:
            relief = min(surcharge, excess - over)
            notes.append(f"Marginal relief of ₹{relief:,.0f} on surcharge at the "
                         f"₹{threshold:,.0f} threshold.")
    surcharge_net = surcharge - relief
    cess = (tax_after_rebate + surcharge_net) * t.cess
    tax = rnd(tax_after_rebate + surcharge_net + cess)
    return _Assessed(gti, deductions, ti, slab_income, exemption_used, s_tax, sp_tax,
                     rebate, surcharge_net, relief, cess, tax)


def compute_regime(t: IndiaYear, regime: str, *, resident: bool, age_band: str,
                   lines: list[Line], props: list[Property], bf: dict,
                   deductions_in: dict, missing: list[str],
                   late: bool = False) -> RegimeResult:
    notes: list[str] = []
    pools = {k: 0.0 for k in ALL_POOLS}
    stcl = ltcl = 0.0
    for ln in lines:
        if ln.pool == "exempt":
            continue
        if ln.amount < 0:
            if ln.pool in ("stcg_slab", "stcg_111a"):
                stcl += -ln.amount
            elif ln.pool in LT_POOLS:
                ltcl += -ln.amount
            # Other-sources items floor at nil; they never become losses.
            continue
        pools[ln.pool] += ln.amount

    # House property (s.70(1): properties net against each other first).
    so_cap = t.self_occupied_interest_cap
    so_interest = sum(p.interest for p in props if p.status == "self_occupied")
    hp = 0.0
    for p in props:
        if p.status == "self_occupied":
            continue
        nav = p.annual_value - p.municipal_tax
        hp += nav - t.hp_standard_deduction * max(0.0, nav) - p.interest
    if so_interest:
        if regime == "old":
            allowed = min(so_interest, so_cap)
            hp -= allowed
            if so_interest > so_cap:
                notes.append(f"Self-occupied interest capped at ₹{so_cap:,.0f} "
                             f"(₹{so_interest:,.0f} paid).")
        else:
            notes.append("New regime: no deduction for interest on a self-occupied "
                         f"home (₹{so_interest:,.0f} disallowed).")
    hp_income = hp
    hp_loss = max(0.0, -hp)
    pools["hp"] = max(0.0, hp)

    def tax_of(trial: dict[str, float]) -> _Assessed:
        return _assess(t, regime, resident=resident, age_band=age_band, pools=trial,
                       lines=lines, deductions_in=deductions_in, notes=[],
                       missing=[], exact=False)

    slabs = _slabs(t, regime, resident, age_band)
    set_off = [False]

    def allocate(loss: float, eligible: tuple[str, ...]) -> float:
        """Set ``loss`` off against ``eligible`` pools, choosing at each
        breakpoint the pool whose reduction saves the most tax. Set-off is
        compulsory, so a zero-saving pool is still used; ties go to the
        order in ``eligible``."""
        while loss > 0.005:
            avail = [k for k in eligible if pools[k] > 0.005]
            if not avail:
                break
            base = tax_of(pools)
            best = None
            for rank, k in enumerate(avail):
                v = pools[k]
                steps = {v}
                points = []
                if k in SLAB_POOLS:
                    points += [base.slab_income - (u or 0) for u, _ in slabs if u]
                    points.append(base.slab_income)
                if k == "ltcg_112a":
                    points.append(v - t.ltcg_112a_exemption)
                if resident and k in SPECIAL_POOLS:
                    points.append(v - max(0.0, basic_exemption(slabs) - base.slab_income))
                points += [base.ti - th for th, _ in t.surcharge]
                if resident:
                    points.append(base.ti - t.rebate_87a[regime][0])
                steps |= {x for x in points if 0.005 < x < v}
                for d in sorted(steps):
                    d = min(d, loss)
                    trial = dict(pools)
                    trial[k] -= d
                    saving = (base.tax - tax_of(trial).tax) / d
                    key = (round(saving, 9), -rank, d)
                    if best is None or key > best[0]:
                        best = (key, k, d)
            _, k, d = best
            pools[k] -= d
            loss -= d
            set_off[0] = True
        return max(0.0, loss)

    carry: dict[str, float] = {}
    # s.70: intra-head — long-term loss first (fewer places to go), then short-term.
    ltcl = allocate(ltcl, LT_POOLS)
    stcl = allocate(stcl, CG_POOLS)
    # s.71: house-property loss across heads — old regime, capped.
    if hp_loss:
        if regime == "old":
            setoff = min(hp_loss, t.hp_loss_setoff_cap)
            left = allocate(setoff, OTHER_HEAD_POOLS)
            carry["house_property"] = hp_loss - (setoff - left)
            if hp_loss > t.hp_loss_setoff_cap:
                notes.append(f"House-property loss set off against other heads capped "
                             f"at ₹{t.hp_loss_setoff_cap:,.0f}; the rest carries forward "
                             "8 years against house property only.")
        else:
            carry["house_property"] = hp_loss
            notes.append("New regime: a house-property loss cannot be set off against "
                         "other heads; it is shown as carried forward (practitioner "
                         "view — verify).")
    # Brought forward: s.71B house property against house property; s.74
    # capital losses (short-term against any gain, long-term against long-term).
    bf_hp = float(bf.get("house_property_inr") or 0)
    if bf_hp and pools["hp"] > 0:
        used = min(bf_hp, pools["hp"])
        pools["hp"] -= used
        bf_hp -= used
        set_off[0] = True
        if regime == "new":
            notes.append("Brought-forward house-property loss set off against "
                         "house-property income; under the new regime a loss "
                         "attributable to self-occupied interest is not allowed — "
                         "confirm its origin.")
    carry["house_property"] = carry.get("house_property", 0.0) + bf_hp
    bf_lt = allocate(float(bf.get("ltcl_inr") or 0), LT_POOLS)
    bf_st = allocate(float(bf.get("stcl_inr") or 0), CG_POOLS)
    if late and (stcl or ltcl):
        notes.append("Return after the due date: this year's capital losses "
                     f"(₹{stcl + ltcl:,.0f} unabsorbed) cannot be carried forward "
                     "(s.80); house-property loss is unaffected.")
        stcl = ltcl = 0.0
    carry["short_term_capital_loss"] = stcl + bf_st
    carry["long_term_capital_loss"] = ltcl + bf_lt

    a = _assess(t, regime, resident=resident, age_band=age_band, pools=pools,
                lines=lines, deductions_in=deductions_in, notes=notes, missing=missing)
    return RegimeResult(regime, hp_income, pools, a.gti, a.deductions, a.ti,
                        a.slab_income, a.exemption_used, a.s_tax, a.sp_tax, a.rebate,
                        a.surcharge, a.relief, a.cess, a.tax, carry, notes,
                        set_off[0])


# ── credits, interest, filing ──────────────────────────────────────────────

@dataclass
class Credits:
    tds: float | None
    tds_unknown: list[str]
    advance_tax: float | None
    self_assessment_tax: float | None
    interest_234a: float | None
    interest_234b: float | None
    interest_234c: float | None
    late_fee: float
    balance: float | None       # positive = payable, negative = refund
    notes: list[str] = field(default_factory=list)


def _months_between(start: _dt.date, end: _dt.date) -> int:
    """Months or part months from ``start`` to ``end`` inclusive."""
    if end < start:
        return 0
    return (end.year - start.year) * 12 + end.month - start.month + 1


def _instalments(rows) -> dict[int, float]:
    """Validate advance-tax instalments: numbers 1-4, amounts numeric."""
    paid: dict[int, float] = {}
    if rows is None:
        return paid
    if not isinstance(rows, list):
        raise IndiaReturnError("advance_tax_instalments must be a list of "
                               "{number: 1-4, amount_inr}")
    for inst in rows:
        try:
            n = int(inst.get("number"))
            amt = float(inst.get("amount_inr"))
        except (TypeError, ValueError, AttributeError) as e:
            raise IndiaReturnError(f"advance_tax_instalments entry {inst!r} needs a "
                                   "numeric number (1-4) and amount_inr") from e
        if n not in (1, 2, 3, 4):
            raise IndiaReturnError(f"advance-tax instalment number {n} is not 1-4")
        paid[n] = paid.get(n, 0.0) + amt
    return paid


def credits(t: IndiaYear, fy: str, res: Residence, rr: RegimeResult,
            lines: list[Line], props: list[Property], itr: dict,
            age_band: str) -> Credits:
    notes: list[str] = []
    tds_items = [(ln.name, ln.tds) for ln in lines] + [(p.name, p.tds) for p in props]
    unknown = [n for n, v in tds_items if v is None]
    tds = None if unknown else sum(v for _, v in tds_items)
    adv_raw = itr.get("advance_tax_paid_inr")
    sat_raw = itr.get("self_assessment_tax_paid_inr")
    adv = None if adv_raw is None else float(adv_raw)
    sat = None if sat_raw is None else float(sat_raw)
    for key, v in (("advance_tax_paid_inr", adv), ("self_assessment_tax_paid_inr", sat)):
        if v is None:
            unknown.append(key)
            notes.append(f"{key} not recorded — the balance and advance-tax interest "
                         "cannot be determined (unknown is not zero; check Form 26AS).")
    paid = _instalments(itr.get("advance_tax_instalments"))
    due = _date(t.due_date)
    filing = _date(itr.get("expected_filing_date")) or due
    if itr.get("expected_filing_date") is None:
        notes.append(f"Interest estimated as if filed and paid on the due date ({t.due_date}).")
    ay_start = _dt.date(fy_start(fy) + 1, 4, 1)

    i234a = i234b = i234c = None
    if tds is not None and adv is not None:
        assessed = max(0.0, rr.tax - tds)
        senior_exempt = res.resident and age_band != "below_60"
        if assessed >= ADVANCE_TAX_THRESHOLD and not senior_exempt:
            if adv < ADVANCE_TAX_SHORTFALL_PCT * assessed:
                i234b = round(max(0.0, assessed - adv) * INTEREST_PER_MONTH
                              * _months_between(ay_start, filing))
            else:
                i234b = 0.0
            if itr.get("advance_tax_instalments") is None and adv > 0:
                notes.append("s.234C cannot be computed without instalment dates; "
                             "record advance_tax_instalments.")
            else:
                cg_tax_share = (sum(rr.special_tax[k] for k in ("stcg_111a", "ltcg_112",
                                                                "ltcg_112a"))
                                / max(1.0, rr.slab_tax + sum(rr.special_tax.values())))
                base = assessed * (1 - cg_tax_share)
                cum, total = 0.0, 0.0
                for n, (pct, months) in enumerate(INSTALMENTS, start=1):
                    cum += paid.get(n, 0.0)
                    total += max(0.0, pct * base - cum) * INTEREST_PER_MONTH * months
                i234c = round(total)
                notes.append("s.234C is approximate: capital-gains tax is excluded "
                             "(gains arising after an instalment date are relieved "
                             "if paid in later instalments); non-gain income is "
                             "assumed to accrue evenly.")
        else:
            i234b = i234c = 0.0
            if senior_exempt and assessed >= ADVANCE_TAX_THRESHOLD:
                notes.append("Resident senior citizen without business income: no "
                             "advance tax (s.207(1)), so no s.234B/C.")
        if filing > due:
            i234a = round(max(0.0, rr.tax - tds - adv) * INTEREST_PER_MONTH
                          * _months_between(due + _dt.timedelta(days=1), filing))
        else:
            i234a = 0.0
    late_fee = 0.0
    if filing > due and rr.gross_total_income > basic_exemption(
            _slabs(t, rr.regime, res.resident, age_band)):
        late_fee = LATE_FEE_SMALL if rr.total_income <= LATE_FEE_SMALL_INCOME else LATE_FEE
    balance = None
    if tds is not None and adv is not None and sat is not None:
        balance = (rr.tax + (i234a or 0) + (i234b or 0) + (i234c or 0) + late_fee
                   - tds - adv - sat)
        balance = round10(balance)
    return Credits(tds, unknown, adv, sat, i234a, i234b, i234c, late_fee, balance, notes)


@dataclass
class Filing:
    mandatory: bool
    reasons: list[str]
    due_date: str
    belated_deadline: str
    revised_deadline: str
    notes: list[str] = field(default_factory=list)


def filing(t: IndiaYear, res: Residence, rr: RegimeResult, cr: Credits,
           lines: list[Line], age_band: str) -> Filing:
    s = t.sections
    reasons, notes = [], []
    pre_exemption = rr.gross_total_income + sum(ln.exempt_54
                                                for ln in lines)
    limit = basic_exemption(_slabs(t, rr.regime, res.resident, age_band))
    if pre_exemption > limit:
        reasons.append(f"income before Chapter VI-A and s.54/54EC exemptions "
                       f"(₹{pre_exemption:,.0f}) exceeds the basic exemption "
                       f"(₹{limit:,.0f}) — {s['return']}")
    tds_limit = (TDS_TRIGGER_SENIOR if res.resident and age_band != "below_60"
                 else TDS_TRIGGER)
    if cr.tds is not None and cr.tds >= tds_limit:
        reasons.append(f"TDS of ₹{cr.tds:,.0f} is ₹{tds_limit:,.0f} or more — seventh "
                       f"proviso to {s['return']} (Rule 12AB)")
    if cr.balance is not None and cr.balance < 0:
        notes.append(f"A refund of ₹{-cr.balance:,.0f} can only be claimed by filing "
                     "(optional, but the money is otherwise lost).")
    if any(v > 0 for v in rr.carry_forward.values()):
        notes.append("Losses carry forward only if the return is filed by the due "
                     "date (s.80; house-property loss excepted) — file on time.")
    notes.append("Other seventh-proviso triggers (large deposits, foreign travel, "
                 "electricity, turnover) are not checked here.")
    if res.status == NR:
        notes.append("s.115G relief from filing (NRI with only investment income/LTCG "
                     "on foreign-exchange assets, fully taxed at source) is not "
                     "evaluated.")
    return Filing(bool(reasons), reasons, t.due_date, t.belated_deadline,
                  t.revised_deadline, notes)


# ── U.S. hand-off ──────────────────────────────────────────────────────────

@dataclass
class USHandoff:
    rate: float | None
    rate_basis: str
    income_inr: dict[str, float]
    income_usd: dict[str, float] | None
    tax_inr: float
    tax_usd: float | None
    india_exempt_inr: float
    india_exempt_usd: float | None
    #: what makes up india_exempt_inr: NRE/FCNR interest, s.10(10D) maturity
    #: gains, s.54/54EC-sheltered gains.
    india_exempt_detail: dict[str, float] = field(default_factory=dict)
    #: Indian taxable income split the way the federal return asks for it
    #: (interest, dividends, capital transactions, rent, other), INR and USD.
    by_type_inr: dict[str, float] = field(default_factory=dict)
    by_type_usd: dict[str, float] | None = None
    #: The ``tax_return.foreign`` block in the shape ``federal-tax-return``
    #: reads (USD, U.S. rules), or None without a rate.
    federal_foreign: dict | None = None
    #: Items deliberately left out of that block, with where they go instead.
    federal_excluded: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


#: Indian fund units are PFICs for a U.S. person; the federal skill refuses
#: them in capital_transactions, so they are routed to pfic-divest-or-comply.
PFIC_ASSETS = frozenset({"equity_mf", "debt_mf"})
#: U.S. long-term holding period: more than one year (IRC §1222).
US_LONG_TERM_MONTHS = 12


def _usd(x: float | None, rate: float) -> float | None:
    return None if x is None else round(x / rate)


def federal_foreign(itr: dict, lines: list[Line], props: list[Property],
                    tax_inr: float, rate: float) -> tuple[dict, list[str]]:
    """``tax_return.foreign`` for the federal skill. Amounts are converted at
    the single supplied rate. Interest includes India-exempt NRE/FCNR.
    Capital transactions use ``us_proceeds_usd``/``us_basis_usd`` when the
    facts give them; otherwise proceeds are converted at the supplied rate
    and basis is ``None`` (U.S. basis uses the purchase-date rate, which
    this module does not have — unknown, not the year's rate)."""
    excluded: list[str] = []
    interest = sum(ln.amount for ln in lines if ln.head == "interest")
    dividends = sum(ln.amount for ln in lines if ln.head == "dividends")
    txns = []
    for i, r in enumerate(itr.get("capital_gains") or []):
        asset = r.get("asset")
        name = str(r.get("name") or f"{asset} #{i + 1}")
        if asset in PFIC_ASSETS:
            excluded.append(f"Left out — {name}: Indian fund units are a PFIC — see "
                            "`pfic-divest-or-comply`, not capital_transactions")
            continue
        acq, sold = _date(r.get("acquired")), _date(r.get("sold"))
        proceeds = r.get("us_proceeds_usd")
        # Gross proceeds; transfer expenses belong in U.S. basis (Form 8949).
        proceeds = (round(float(proceeds)) if proceeds is not None
                    else _usd(float(r["sale_inr"]), rate))
        basis = r.get("us_basis_usd")
        basis = None if basis is None else round(float(basis))
        term = "long" if _long_term(acq, sold, US_LONG_TERM_MONTHS) else "short"
        desc = f"{name} (India, {asset}, sold {sold.isoformat()})"
        if basis is None and r.get("transfer_expenses_inr"):
            desc += (f"; add ₹{float(r['transfer_expenses_inr']):,.0f} transfer "
                     "expenses to U.S. basis")
        if asset == "gold":
            desc += " — collectible, 28% U.S. rate"
        txns.append({"description": desc, "proceeds": proceeds, "basis": basis,
                     "term": term, "wash_sale_disallowed": 0, "basis_reported": False})
    for ln in lines:
        if ln.head == "insurance" and ln.amount:
            excluded.append(f"Left out — {ln.name}: insurance maturity, out of scope for the "
                            "federal skill (IRC §7702 / PFIC questions)")
    rent = sum(p.gross_rent for p in props)
    if rent:
        excluded.append(f"Left out — rent of ₹{rent:,.0f} gross (${rent / rate:,.0f}): "
                        "U.S.-taxable, but the federal skill refuses non-zero rent "
                        "(Schedule E, depreciation, §469) — see "
                        "`passive-loss-eligibility`; `rent: 0` in the block means not "
                        "carried here, not none received")
    block = {
        "country": "IN",
        "accounts": bool(itr.get("interest")),
        "interest": _usd(interest, rate),
        "dividends": _usd(dividends, rate),
        # Treaty-country corporation, but the U.S. holding period is not
        # recorded: unknown, not zero.
        "qualified_dividends": None if dividends else 0,
        "capital_transactions": txns,
        "rent": 0,
        "foreign_tax_paid": {"passive": _usd(tax_inr, rate), "general": 0},
        "reported_on_1099": False,
        "category": PASSIVE,
    }
    return block, excluded


def us_handoff(itr: dict, lines: list[Line], props: list[Property],
               rr: RegimeResult) -> USHandoff:
    rate = itr.get("usd_inr_rate")
    rate = float(rate) if rate is not None else None
    if rate is not None and rate <= 0:
        raise IndiaReturnError("usd_inr_rate must be positive (INR per USD)")
    basis = str(itr.get("usd_inr_rate_basis") or "as supplied in the facts file; basis not stated")
    taxable = [ln for ln in lines if ln.pool != "exempt"]
    passive = sum(ln.amount for ln in taxable) + rr.hp_income
    income = {PASSIVE: passive, GENERAL: 0.0}
    by_type = {
        "interest": sum(ln.amount for ln in taxable if ln.head == "interest"),
        "dividends": sum(ln.amount for ln in taxable if ln.head == "dividends"),
        "capital_transactions": sum(ln.amount for ln in taxable
                                    if ln.pool not in ("slab", "div_slab")
                                    and ln.head in ("capital_gains", "insurance")),
        "rent": rr.hp_income,
        "other": sum(ln.amount for ln in taxable
                     if ln.head == "insurance" and ln.pool == "slab"),
    }
    detail = {
        "NRE/FCNR interest": sum(ln.amount for ln in lines
                                 if ln.pool == "exempt" and ln.head == "interest"),
        "s.10(10D) maturity gains": sum(max(0.0, ln.amount) for ln in lines
                                        if ln.pool == "exempt" and ln.head == "insurance"
                                        and "death" not in ln.note),
        "s.54/54EC-sheltered gains": sum(ln.exempt_54 for ln in lines),
    }
    detail = {k: v for k, v in detail.items() if v}
    exempt = sum(detail.values())
    conv = (lambda x: x / rate) if rate else None
    notes = [
        "All income here is passive category (interest, rent, gains, insurance, "
        "dividends); general would hold Indian salary or business income, which is "
        "out of scope. Passive income taxed in India above the top U.S. rate may be "
        "re-categorised as general under the high-taxed income rule — the U.S. return decides.",
        "The INR tables are on the Indian basis (30% standard deduction on rent, "
        "Indian cost). The `tax_return.foreign` block is converted at one supplied "
        "rate and covers the Indian financial year (April-March); the U.S. return is "
        "calendar-year, so interest and tax must be re-split across two U.S. years, "
        "and each sale belongs to the U.S. year of its date. U.S. basis uses the "
        "purchase-date rate: it is left null unless `us_basis_usd` is recorded.",
        "Creditable tax is the Indian liability finally borne (TDS + advance + "
        "self-assessment − refund), never the TDS alone; s.234 interest and fees "
        "are not tax. India-U.S. DTAA relief-from-double-taxation article "
        "(Article 25 in the treaty text — verify) and its resourcing rule decide the "
        "credit; not encoded here.",
        "Income exempt in India — NRE/FCNR interest, s.10(10D) maturity gains (an "
        "Indian policy often fails IRC §7702, so the inside build-up is taxable), "
        "and gains sheltered by s.54/54EC — is still U.S.-taxable with no Indian tax "
        "to credit.",
        "Indian mutual funds (and ULIPs that hold them) are PFICs for a U.S. person — "
        "see `pfic-divest-or-comply`. FBAR and Form 8938 are separate — see "
        "`foreign-reporting-audit`.",
    ]
    return USHandoff(rate, basis, income,
                     {k: conv(v) for k, v in income.items()} if conv else None,
                     rr.tax, conv(rr.tax) if conv else None, exempt,
                     conv(exempt) if conv else None, detail, by_type,
                     {k: conv(v) for k, v in by_type.items()} if conv else None,
                     *(federal_foreign(itr, lines, props, rr.tax, rate) if rate
                       else (None, [])),
                     notes)


# ── checklist ──────────────────────────────────────────────────────────────

def checklist(lines: list[Line], props: list[Property], itr: dict,
              res: Residence) -> list[str]:
    out = ["Form 26AS, Annual Information Statement (AIS) and Taxpayer Information "
           "Summary (TIS) for the year — reconcile every TDS figure below against them",
           "Passport entry/exit stamps or travel log for the day counts behind "
           "residential status"]
    if any(ln.head == "interest" for ln in lines):
        out.append("Bank interest certificates for each NRO/NRE/FCNR account, and "
                   "Form 16A for TDS on NRO interest")
    if any(p.status in ("let_out", "deemed_let_out") for p in props):
        out.append("Rent agreement and rent receipts; municipal-tax receipts showing "
                   "payment during the year; Form 16A if the tenant deducted TDS"
                   + (" (tenants of a non-resident must deduct under s.195)"
                      if res.status == NR else ""))
    if any(p.interest for p in props):
        out.append("Home-loan interest certificate from the lender (interest and "
                   "principal split; pre-construction interest if any)")
    if any(ln.head == "capital_gains" for ln in lines):
        out.append("Capital-gains statements from the broker and RTA (CAMS/KFintech) "
                   "with acquisition dates and cost; contract notes showing STT")
    if any(ln.head == "capital_gains" and ln.note and "s.54" in ln.note for ln in lines) \
            or any(r.get("asset") == "property" for r in itr.get("capital_gains") or []):
        out.append("Purchase and sale deeds, stamp-duty valuation, transfer-expense "
                   "invoices; Form 16A for s.195 TDS by the buyer; s.54 new-house "
                   "deed or s.54EC bond certificates if claimed")
    if any(ln.head == "insurance" for ln in lines):
        out.append("Insurer's maturity statement and full premium history (needed "
                   "for the s.10(10D) premium tests)")
    if any(ln.head == "dividends" for ln in lines):
        out.append("Dividend statements and Form 16A")
    if res.status == NR:
        out.append("Tax Residency Certificate and Form 10F if any treaty rate is "
                   "claimed (treaty claims themselves are not computed here)")
    missing_tds = [ln.name for ln in lines if ln.tds is None] + \
                  [p.name for p in props if p.tds is None]
    if missing_tds:
        out.append("TDS not recorded for: " + ", ".join(missing_tds))
    return out


# ── top level ──────────────────────────────────────────────────────────────

@dataclass
class IndiaReturn:
    financial_year: str
    table: IndiaYear
    projected_table: bool
    residence: Residence
    lines: list[Line]
    properties: list[Property]
    regimes: dict[str, RegimeResult]
    recommended: str
    chosen: str
    credits: Credits
    filing: Filing
    us: USHandoff
    checklist: list[str]
    findings: list[str]
    weakest_input: str


def _indian_citizen(itr: dict, members: list[dict] | None) -> bool | None:
    tp = itr.get("taxpayer") or {}
    if tp.get("indian_citizen") is not None:
        return bool(tp["indian_citizen"])
    mid = tp.get("member")
    for m in members or []:
        if m.get("id") == mid and m.get("citizenship") is not None:
            return "IN" in (m.get("citizenship") or [])
    return None


def _age_band(itr: dict, members: list[dict] | None, start: int) -> tuple[str, str]:
    """Senior (60+) or super senior (80+) at any time in the year. Returns
    (band, note); an ambiguous birth year is resolved to below_60 with a note."""
    tp = itr.get("taxpayer") or {}
    bd = _date(tp.get("birth_date"))
    if bd:
        end = _dt.date(start + 1, 3, 31)
        age = end.year - bd.year - ((end.month, end.day) < (bd.month, bd.day))
        return ("super_senior" if age >= 80 else "senior" if age >= 60 else "below_60"), ""
    by = None
    for m in members or []:
        if m.get("id") == tp.get("member"):
            by = m.get("birth_year")
    if by is None:
        return "below_60", "birth date not recorded; treated as under 60"
    by = int(by)
    for band, age in (("super_senior", 80), ("senior", 60)):
        if by + age <= start:
            return band, ""
        if by + age == start + 1:
            return "below_60", (f"turns {age} in {start + 1}; whether before 31 March "
                                "decides the age band — record birth_date")
    return "below_60", ""


def compute(itr: dict, *, members: list[dict] | None = None) -> IndiaReturn:
    """Prepare the workpaper from an ``india_tax_return`` block."""
    if not itr:
        raise IndiaReturnError("no india_tax_return block")
    for key, why in REFUSED.items():
        if itr.get(key):
            raise IndiaReturnError(f"{key}: {why}")
    fy = str(itr.get("financial_year") or "")
    start = fy_start(fy)
    if fy < min(INDIA_TABLES):
        raise IndiaReturnError(
            f"FY {fy} predates the shipped tables (earliest {min(INDIA_TABLES)}); "
            "earlier years had different slabs, s.87A limits and pre-23-July-2024 "
            "capital-gains rates, so it is refused rather than back-cast")
    t, projected = table_for(fy)
    s = t.sections
    findings: list[str] = []
    missing: list[str] = []
    tp = itr.get("taxpayer") or {}
    bounds = (_dt.date(start, 4, 1), _dt.date(start + 1, 3, 31))
    fema = tp.get("fema_resident_outside_india")
    due = _date(t.due_date)
    filing_on = _date(itr.get("expected_filing_date")) or due
    late = filing_on > due

    # Status needs Indian income; NRE/FCNR are exempt for NR and RNOR alike,
    # and the ₹15 lakh tests only ever produce RNOR, so compute it as NR.
    prov_lines = (interest_lines(itr.get("interest"), NR, missing, fema)
                  + cg_lines(itr.get("capital_gains"), NR, [], [], bounds)
                  + insurance_lines(itr.get("insurance_maturities"), [], [], bounds)
                  + dividend_lines(itr.get("dividends"), NR, []))
    props = properties(itr.get("house_property"), t.max_self_occupied, missing)
    if missing:
        raise IndiaReturnError("required figures not recorded (unknown is not zero): "
                               + ", ".join(dict.fromkeys(missing)))
    age_band, age_note = _age_band(itr, members, start)
    provisional = compute_regime(t, "new", resident=False, age_band="below_60",
                                 lines=prov_lines, props=props, bf={},
                                 deductions_in={}, missing=[])
    citizen = _indian_citizen(itr, members)
    res = residence(tp, indian_citizen=citizen,
                    indian_income=provisional.gross_total_income, sec=s["residence"])

    lines = (interest_lines(itr.get("interest"), res.status, missing, fema)
             + cg_lines(itr.get("capital_gains"), res.status, missing, findings, bounds)
             + insurance_lines(itr.get("insurance_maturities"), missing, findings, bounds)
             + dividend_lines(itr.get("dividends"), res.status, missing))
    if missing:
        raise IndiaReturnError("required figures not recorded (unknown is not zero): "
                               + ", ".join(dict.fromkeys(missing)))
    if age_note and res.resident:
        findings.append(f"Age band: {age_note}.")

    bf_raw = itr.get("brought_forward_losses")
    bf = bf_raw or {}
    bf_unknown = bf_raw is None or any(
        bf.get(k) is None for k in ("house_property_inr", "stcl_inr", "ltcl_inr"))
    ded = itr.get("deductions_old_regime") or {}
    forced = itr.get("regime")
    if forced not in (None, "new", "old"):
        raise IndiaReturnError(f"regime {forced!r} is not new | old | null")
    regimes = {}
    for reg in ("new", "old"):
        regimes[reg] = compute_regime(t, reg, resident=res.resident, age_band=age_band,
                                      lines=lines, props=props, bf=bf,
                                      deductions_in=ded, missing=missing,
                                      late=late)
    if missing:
        raise IndiaReturnError("required figures not recorded (unknown is not zero): "
                               + ", ".join(dict.fromkeys(missing)))
    recommended = "old" if regimes["old"].tax < regimes["new"].tax else "new"
    old_barred = late
    if old_barred:
        # s.115BAC(6): without business income the old regime is open only in
        # a return under s.139(1), i.e. by the due date.
        recommended = "new"
    chosen = "new" if old_barred else (forced or recommended)
    rr = regimes[chosen]
    cr = credits(t, fy, res, rr, lines, props, itr, age_band)
    fl = filing(t, res, rr, cr, lines, age_band)
    us = us_handoff(itr, lines, props, rr)

    # Findings — the decision first.
    findings.insert(0, f"**Residential status: {STATUS_LABEL[res.status]}.** {res.basis}.")
    if res.status == NR:
        findings.insert(1, "Only India-source income is taxed; NRE/FCNR interest is "
                        f"exempt; no {s['rebate']} rebate; the basic exemption cannot "
                        "absorb special-rate capital gains.")
    elif res.status == RNOR:
        findings.insert(1, "RNOR: India-source income plus foreign income from a "
                        "business controlled in India or a profession set up in India "
                        "(not modelled); NRE/FCNR interest stays exempt while FEMA "
                        "status is resident outside India.")
    else:
        findings.insert(1, "**Ordinarily resident: India taxes worldwide income.** This "
                        "workpaper covers India-source income only, so the tax is a "
                        "LOWER BOUND; foreign income and Schedule FA (foreign assets) "
                        "must be added by a professional. NRE/FCNR interest is taxable.")
    diff = abs(regimes["new"].tax - regimes["old"].tax)
    if old_barred:
        cheaper = regimes["old"].tax < regimes["new"].tax
        findings.append(
            f"**Filed after the due date ({t.due_date}), so only the new regime is "
            f"available** ({s['new_regime']}(6)): ₹{regimes['new'].tax:,.0f}."
            + (" The old regime was requested and is not applied." if forced == "old" else "")
            + (f" Filing on time under the old regime would have saved ₹{diff:,.0f}."
               if cheaper else ""))
    elif forced and forced != recommended:
        findings.append(f"Regime forced to **{forced}**, which costs ₹{diff:,.0f} more "
                        f"than the {recommended} regime.")
    else:
        findings.append(f"**{recommended.title()} regime is lower by ₹{diff:,.0f}** "
                        f"(₹{regimes[recommended].tax:,.0f} vs "
                        f"₹{regimes['old' if recommended == 'new' else 'new'].tax:,.0f}). "
                        "Without business income the choice is made each year in the "
                        f"return; the old regime is available only in a return filed "
                        f"by the due date ({t.due_date}) — a belated return is taxed "
                        f"under the new regime ({s['new_regime']}).")
    if any(r.losses_set_off for r in regimes.values()):
        findings.append(SETOFF_BASIS)
    if bf_unknown:
        findings.append("Brought-forward losses are not fully recorded; they can only "
                        "reduce tax, so the liability shown is an **upper bound**.")
    if cr.balance is None:
        findings.append("Refund or balance payable **cannot be determined**: not "
                        "recorded — " + ", ".join(cr.tds_unknown) + ".")
    elif cr.balance < 0:
        findings.append(f"**Refund due: ₹{-cr.balance:,.0f}.**")
    elif cr.balance > 0:
        findings.append(f"**Balance payable: ₹{cr.balance:,.0f}** (self-assessment tax "
                        "before filing).")
    else:
        findings.append("Tax fully covered by credits; nothing payable or refundable.")
    findings.append(("Filing is **mandatory**: " + "; ".join(fl.reasons) + ".")
                    if fl.mandatory else "Filing is not mandatory on the income test.")
    if res.status == NR and any(p.status == "let_out" and p.tds == 0 for p in props):
        findings.append("Rent from a non-resident's let-out property carried no TDS. "
                        "Tenants paying a non-resident must deduct under s.195; the "
                        "tax falls due as advance/self-assessment tax instead.")
    if itr.get("agricultural_income_inr"):
        findings.append("Agricultural income recorded: exempt under s.10(1) but it can "
                        "raise the rate on other income (partial integration) — not "
                        "computed.")
    if projected:
        findings.append(f"No table for FY {fy}; the latest (FY {t.financial_year}) table "
                        "is used. Treat every figure as a projection.")
    if start >= 2026:
        findings.append(f"FY {fy} falls under the {t.act}. Section numbers shown are the "
                        "new Act's where a concordance confirmed them; verify against "
                        "the Act before relying on any citation.")
    weakest = ("the day counts behind residential status — a few days in India "
               "moves the whole return between NR, RNOR and ROR, and they come from a "
               "travel log, not a statement")
    return IndiaReturn(fy, t, projected, res, lines, props, regimes, recommended, chosen,
                       cr, fl, us, checklist(lines, props, itr, res), findings, weakest)
