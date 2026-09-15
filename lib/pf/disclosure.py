"""California property disclosure: what must be provided, and what to measure.

## The one idea

An agent reading a disclosure package improvises its own checklist, and the
checklist is the part that must not be improvised. Whether a pre-1978 home needs
a lead-based paint disclosure is not a judgement call; whether the §4525 packet
is complete is a list; whether an association's reserves are weak is a
threshold with a reason.

So this module generates **what to look for**, and the agent does the looking.
Same division as `intake.py`: the repository decides what is worth reading for,
the reader reads.

## What it refuses

It does not read documents, score a property, or produce a verdict. A checklist
item is `required`, `provided` or `missing` — never `probably fine`.

It does not encode any state but California. The statutory content here is
Californian in a way that does not transfer: Davis-Stirling has no analogue in
most states, and a prompt or module that quietly applied it elsewhere would be
worse than one that refused.

## On the citations

Every entry carries a source and `verified_on: unverified`, on the same terms as
the rest of the repository. Where the pinpoint section is not certain the
authority is named without one — an approximate section number reads as settled
law and is harder to check than an honest description.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SINGLE_FAMILY, CONDO, TOWNHOME = "single_family", "condo", "townhome"
#: Property types that sit inside a common interest development, and therefore
#: carry an association, a master policy and an assessment risk.
CID_TYPES = (CONDO, TOWNHOME)

# ── thresholds ──────────────────────────────────────────────────────────────

#: Federal lead-based paint disclosure applies to housing built before this
#: year. The most commonly omitted disclosure in the package, and the omission
#: carries a federal penalty rather than merely a contractual one.
LEAD_PAINT_YEAR = 1978

#: Reserve funding bands, as a share of the fully funded balance. A convention
#: rather than a statutory test — which is exactly why the number alone decides
#: nothing. An association at 65% facing a roof next year is worse placed than
#: one at 40% that has just finished replacing everything, so these bands are
#: reported alongside the component list and never instead of it.
RESERVE_STRONG = 0.70
RESERVE_WEAK = 0.30

#: Owner delinquency above this level threatens conventional financing
#: eligibility for the whole project, not just the association's cash flow —
#: which makes it a resale problem for a buyer who is otherwise paying cash.
DELINQUENCY_FINANCING_RISK = 0.15

#: Annual reserve contribution as a share of the operating budget, below which
#: secondary-market project standards generally treat the project as
#: ineligible.
RESERVE_CONTRIBUTION_MIN = 0.10

#: Civ. Code §5605(b): a board may generally raise regular assessments by more
#: than this in a year, or levy a special assessment above 5% of the budget,
#: only with member approval. An association needing more than this has a
#: governance problem as well as a funding one.
REGULAR_ASSESSMENT_INCREASE_CAP = 0.20
SPECIAL_ASSESSMENT_BUDGET_CAP = 0.05

#: Civ. Code §4741 limits an association's ability to cap rentals below this
#: share of units. Recorded restrictions written before it are frequently
#: unenforceable as written, which matters to a buyer who intends to let.
RENTAL_CAP_FLOOR = 0.25

#: Civ. Code §5551 (SB 326) — exterior elevated elements. Applies to buildings
#: with this many or more multifamily dwelling units, for walking surfaces more
#: than this many feet above ground and supported substantially by wood.
SB326_MIN_UNITS = 3
SB326_MIN_HEIGHT_FEET = 6
SB326_CYCLE_YEARS = 9

#: Civ. Code §5550 — reserve study at least this often, with annual review.
RESERVE_STUDY_MAX_AGE_YEARS = 3

#: A finding is High severity at or above this share of purchase price. Set at
#: the point where an issue stops being a negotiation line and starts being a
#: reason to re-underwrite the purchase.
HIGH_SEVERITY_PRICE_SHARE = 0.02

DISCLOSURE_SOURCE = (
    "California Civil Code §§1102 et seq. (TDS), 1103 (NHD), 1102.6b "
    "(Mello-Roos / 1915 Act), 1101.4 (water-conserving fixtures), 2079.10a "
    "(Megan's Law notice), 4525 and 5550 and 5551 and 5605 and 4741 and 4745 "
    "and 4746 (Davis-Stirling); Health & Safety Code §§13113.7 and 17926 "
    "(smoke and CO alarms); 42 U.S.C. §4852d (lead-based paint)"
)
DISCLOSURE_VERIFIED = "unverified — check against leginfo.legislature.ca.gov"


# ── the disclosure table ────────────────────────────────────────────────────


@dataclass(frozen=True)
class Disclosure:
    key: str
    name: str
    #: Named rather than pinpointed where the section is not certain. An
    #: approximate citation reads as settled and is harder to check than a
    #: description.
    authority: str
    why: str
    #: Property types this applies to. Empty means all.
    types: tuple[str, ...] = ()
    #: Applies only to housing built before this year.
    before_year: int | None = None
    #: Applies only inside a common interest development.
    cid_only: bool = False


DISCLOSURES: tuple[Disclosure, ...] = (
    Disclosure(
        "tds", "Real Estate Transfer Disclosure Statement",
        "Civ. Code §1102 et seq.",
        "The seller's own account of the property's condition. Exempt "
        "transfers — trustee sales, probate, some REO — are excused under "
        "§1102.2, and silence from an exempt seller carries much less "
        "information than silence from an ordinary one."),
    Disclosure(
        "nhd", "Natural Hazard Disclosure statement",
        "Civ. Code §1103",
        "Fire, flood, seismic and dam inundation zones. Generally required "
        "even where the TDS is exempt, and increasingly the document that "
        "decides whether the property is insurable at all."),
    Disclosure(
        "spq", "Seller Property Questionnaire",
        "C.A.R. standard form, not statute",
        "Not required by law and near-universal in practice. Its absence is "
        "itself worth asking about, and its 'Yes' boxes are usually more "
        "informative than the TDS."),
    Disclosure(
        "lead_paint", "Lead-based paint disclosure and pamphlet",
        "42 U.S.C. §4852d (federal)",
        "Required for housing built before 1978. The most commonly missing "
        "item in a package, and the penalty is federal rather than "
        "contractual.",
        before_year=LEAD_PAINT_YEAR),
    Disclosure(
        "mello_roos", "Mello-Roos / 1915 Act special assessment notice",
        "Civ. Code §1102.6b",
        "A special district lien is an ongoing cost that does not appear in "
        "the asking price and is easy to miss in the tax bill."),
    Disclosure(
        "megans_law", "Megan's Law database notice",
        "Civ. Code §2079.10a",
        "Statutory notice language; its absence signals a package assembled "
        "without the standard addenda rather than a substantive problem."),
    Disclosure(
        "water_fixtures", "Water-conserving plumbing fixture compliance",
        "Civ. Code §1101.4",
        "Non-compliance is cheap to fix and a reliable indicator of how much "
        "else was deferred."),
    Disclosure(
        "smoke_co", "Smoke and carbon monoxide alarm compliance",
        "Health & Safety Code §§13113.7, 17926",
        "Cheap, mandatory, and a common point-of-sale condition."),
    Disclosure(
        "earthquake_guide", "Homeowner's Guide to Earthquake Safety",
        "California Civil Code, seller disclosure provisions for older "
        "light-frame dwellings",
        "Delivery is required for older conventional light-frame homes. The "
        "pinpoint section is not recorded here on purpose — confirm the "
        "current requirement rather than relying on a number in a checklist.",
        before_year=1960),
    Disclosure(
        "hoa_packet", "HOA transfer disclosure packet",
        "Civ. Code §4525",
        "Defines exactly what the seller must hand over: governing documents, "
        "pro-forma budget, assessment and reserve funding disclosure summary, "
        "reserve study, insurance summary, delinquency and litigation "
        "statements, and 12 months of open board meeting minutes. Because the "
        "list is statutory, a missing item is a finding rather than a gap in "
        "the analysis.",
        cid_only=True),
    Disclosure(
        "reserve_study", "Current reserve study",
        "Civ. Code §5550",
        "Required at least every three years with an annual review. A study "
        "older than that is a finding in its own right.",
        cid_only=True),
    Disclosure(
        "sb326", "SB 326 exterior elevated element inspection",
        "Civ. Code §5551",
        "Balconies, decks and walkways more than six feet up and supported "
        "substantially by wood, in buildings of three or more multifamily "
        "dwelling units, inspected by a licensed structural engineer or "
        "architect on a nine-year cycle. The single most common source of "
        "large, sudden California condo assessments — and where no report "
        "exists at all, the obligation exists anyway and the cost still lands "
        "on owners.",
        cid_only=True),
)

#: Items in the §4525 packet, listed so a review can name which are absent.
HOA_PACKET_ITEMS = (
    ("governing_documents", "CC&Rs, bylaws, and operating rules"),
    ("budget", "Pro-forma operating budget for the current fiscal year"),
    ("assessment_summary", "Assessment and reserve funding disclosure summary"),
    ("reserve_study", "Most recent reserve study"),
    ("insurance_summary", "Summary of the association's insurance policies"),
    ("delinquency_statement", "Statement of delinquent assessments"),
    ("litigation_statement", "Statement of pending litigation"),
    ("minutes", "Minutes of open board meetings for the last 12 months"),
    ("assessment_notice", "Notice of any approved special assessment"),
)

#: Reports a complete package normally contains, by property type. Absence is
#: a finding; a package is not complete merely because nothing in it is alarming.
STANDARD_REPORTS: dict[str, tuple[tuple[str, str], ...]] = {
    SINGLE_FAMILY: (
        ("general_inspection", "General home inspection"),
        ("pest", "Pest / wood-destroying organism (WDO) report"),
        ("roof", "Roof inspection"),
        ("sewer", "Sewer lateral camera scope"),
        ("title", "Preliminary title report"),
        ("permits", "Permit history or city records report"),
    ),
    CONDO: (
        ("general_inspection", "General inspection of the unit"),
        ("pest", "Pest / WDO report"),
        ("title", "Preliminary title report"),
        ("master_policy", "Master insurance policy declarations, not a summary"),
        ("hoa_financials", "HOA financial statements"),
        ("minutes", "Board meeting minutes — 24 months, not the statutory 12"),
    ),
}
STANDARD_REPORTS[TOWNHOME] = STANDARD_REPORTS[CONDO]


def is_cid(property_type: str | None) -> bool:
    return property_type in CID_TYPES


def required_disclosures(*, property_type: str | None,
                         year_built: int | None) -> list[Disclosure]:
    """Which statutory disclosures this property attracts.

    `year_built` of None does not silently skip the year-gated items — they are
    returned, because "we do not know whether this is pre-1978" is a question
    to ask rather than a reason to drop lead paint off the list.
    """
    out = []
    for d in DISCLOSURES:
        if d.cid_only and not is_cid(property_type):
            continue
        if d.types and property_type not in d.types:
            continue
        if d.before_year is not None and year_built is not None:
            if year_built >= d.before_year:
                continue
        out.append(d)
    return out


def year_gated_but_unknown(*, year_built: int | None) -> list[Disclosure]:
    """Disclosures kept on the list only because the build year is unrecorded."""
    if year_built is not None:
        return []
    return [d for d in DISCLOSURES if d.before_year is not None]


def missing_reports(provided: list[str] | None, *,
                    property_type: str | None) -> list[tuple[str, str]]:
    have = {str(p).strip().lower() for p in (provided or [])}
    return [(k, label)
            for k, label in STANDARD_REPORTS.get(property_type or "", ())
            if k not in have]


def missing_packet_items(provided: list[str] | None) -> list[tuple[str, str]]:
    have = {str(p).strip().lower() for p in (provided or [])}
    return [(k, label) for k, label in HOA_PACKET_ITEMS if k not in have]


# ── SB 326 ──────────────────────────────────────────────────────────────────


@dataclass
class SB326:
    applies: bool | None          # None = cannot be determined
    reason: str
    status: str                   # clean | findings | none | unrecorded
    detail: str


def sb326(*, property_type: str | None, unit_count: int | None,
          elevated_elements: bool | None, report: str | None) -> SB326:
    """Whether the balcony inspection duty applies, and whether it was done."""
    if not is_cid(property_type):
        return SB326(False, "Not a common interest development.",
                     "n/a", "Civ. Code §5551 addresses associations.")
    if unit_count is None or elevated_elements is None:
        return SB326(
            None,
            "Unit count or the presence of wood-supported elevated elements "
            "is not recorded.",
            report or "unrecorded",
            "**Cannot be determined.** The duty turns on a building of "
            f"{SB326_MIN_UNITS} or more multifamily dwelling units with "
            f"walking surfaces more than {SB326_MIN_HEIGHT_FEET} feet above "
            "ground supported substantially by wood. Both facts are cheap to "
            "establish and neither should be assumed.")
    if unit_count < SB326_MIN_UNITS or not elevated_elements:
        return SB326(
            False,
            f"{unit_count} unit(s); elevated elements: {elevated_elements}.",
            "n/a",
            "Outside the statute as recorded. Confirm the element description "
            "rather than the unit count alone — a shared wood walkway counts.")

    status = (report or "unrecorded").strip().lower()
    detail = {
        "clean": "Inspection reported with no elements requiring immediate "
                 "repair. Confirm the date and the next due date — the cycle "
                 f"is {SB326_CYCLE_YEARS} years.",
        "findings": "**Inspection identified elements needing repair.** "
                    "Establish whether the work is funded, assessed, or "
                    "neither. Unfunded structural findings are the shape of "
                    "problem that becomes a special assessment.",
        "none": "**No inspection has been performed.** The obligation exists "
                "whether or not the board has acted, so the cost is ahead of "
                "the buyer rather than behind them. This is a finding, not a "
                "gap in the package.",
    }.get(status,
          "**Not recorded.** Ask for the report and its date. Absence in the "
          "packet is not evidence that the inspection was done.")
    return SB326(True, f"{unit_count} units with wood-supported elevated "
                       "elements.", status, detail)


# ── association health ──────────────────────────────────────────────────────


@dataclass
class Flag:
    severity: str          # high | medium | note
    topic: str
    detail: str


@dataclass
class HOAReview:
    flags: list[Flag] = field(default_factory=list)
    reserve_band: str | None = None
    determinable: bool = True

    @property
    def high(self) -> list[Flag]:
        return [f for f in self.flags if f.severity == "high"]


def reserve_band(pct: float | None) -> str | None:
    if pct is None:
        return None
    if pct >= RESERVE_STRONG:
        return "strong"
    if pct >= RESERVE_WEAK:
        return "fair"
    return "weak"


def review_hoa(hoa: dict | None) -> HOAReview:
    """Threshold checks on the association. Never a score.

    Every unrecorded input produces a note rather than a pass. An association
    whose delinquency rate nobody has asked for is not an association with a
    low delinquency rate.
    """
    r = HOAReview()
    h = hoa or {}
    if not h:
        r.determinable = False
        r.flags.append(Flag(
            "high", "No association data",
            "Nothing about the association is recorded. For a common interest "
            "development that is most of the risk, and none of it has been "
            "looked at."))
        return r

    pct = h.get("reserve_percent_funded")
    r.reserve_band = reserve_band(pct)
    if pct is None:
        r.determinable = False
        r.flags.append(Flag(
            "medium", "Reserves",
            "Percent funded is not recorded. It is in the reserve study and "
            "in the annual assessment and reserve funding disclosure summary."))
    elif pct < RESERVE_WEAK:
        r.flags.append(Flag(
            "high", "Reserves",
            f"**{pct:.0%} funded**, below the {RESERVE_WEAK:.0%} band where "
            "assessment or deferral risk becomes material. Read this against "
            "the component list: what is due, and when."))
    elif pct < RESERVE_STRONG:
        r.flags.append(Flag(
            "medium", "Reserves",
            f"{pct:.0%} funded — the middle band, where the answer depends "
            "entirely on what is coming due. The percentage on its own "
            "decides nothing."))
    else:
        r.flags.append(Flag(
            "note", "Reserves",
            f"{pct:.0%} funded, above the {RESERVE_STRONG:.0%} convention for "
            "a well-funded association. Still check the component list for a "
            "large item due soon."))

    d = h.get("delinquency_rate")
    if d is None:
        r.determinable = False
        r.flags.append(Flag("medium", "Delinquencies",
                            "Not recorded. Ask the management company."))
    elif d > DELINQUENCY_FINANCING_RISK:
        r.flags.append(Flag(
            "high", "Delinquencies",
            f"**{d:.0%} of owners delinquent**, above the "
            f"{DELINQUENCY_FINANCING_RISK:.0%} level at which conventional "
            "project eligibility is generally threatened. That is a resale "
            "problem even for a cash buyer, because it shrinks the pool of "
            "buyers who can finance."))

    c = h.get("reserve_contribution_share")
    if c is not None and c < RESERVE_CONTRIBUTION_MIN:
        r.flags.append(Flag(
            "high", "Reserve contribution",
            f"Annual reserve contribution is {c:.0%} of the operating budget, "
            f"below the {RESERVE_CONTRIBUTION_MIN:.0%} that secondary-market "
            "project standards generally expect. Low dues bought this."))

    lit = h.get("litigation")
    if lit is None:
        r.determinable = False
        r.flags.append(Flag("medium", "Litigation",
                            "Not recorded. It is a required item in the "
                            "§4525 packet."))
    elif lit == "construction_defect":
        r.flags.append(Flag(
            "high", "Litigation",
            "**Construction defect litigation.** Frequently makes a project "
            "non-warrantable for its duration, which narrows the resale "
            "buyer pool to cash and portfolio lenders. It may also be the "
            "only route to funding the defect."))
    elif lit and lit != "none":
        r.flags.append(Flag("medium", "Litigation",
                            f"Litigation recorded as `{lit}`. Establish the "
                            "subject, the exposure and the insurer's position."))

    if h.get("special_assessment_pending"):
        r.flags.append(Flag(
            "high", "Special assessment",
            "**A special assessment is pending or approved.** Who pays an "
            "approved-but-unbilled assessment is a contract term rather than "
            "a custom, and the default is often not what a buyer assumes."))

    if h.get("master_policy_non_renewed"):
        r.flags.append(Flag(
            "high", "Insurance",
            "**The master policy has been non-renewed or moved carrier.** In "
            "current California conditions this is frequently the fastest "
            "moving risk in the package: it affects the assessment outlook, "
            "every owner's HO-6, and the ability to sell."))
    return r


def rental_restriction_note(cap: float | None) -> str | None:
    """Civ. Code §4741 against a recorded cap."""
    if cap is None:
        return None
    if cap < RENTAL_CAP_FLOOR:
        return (f"The recorded rental cap is {cap:.0%}. Civ. Code §4741 limits "
                f"an association's ability to cap rentals below "
                f"{RENTAL_CAP_FLOOR:.0%}, and restrictions recorded before it "
                "are frequently unenforceable as written. If letting the unit "
                "matters, this is a question for counsel rather than a "
                "settled fact — in either direction.")
    return (f"Rental cap recorded at {cap:.0%}, at or above the "
            f"{RENTAL_CAP_FLOOR:.0%} floor in Civ. Code §4741. Confirm the "
            "current count of rented units, not just the cap.")
