"""Expat filing: the §911 election, state domicile, and the CFC screen.

## The one idea

**Choosing between Form 2555 and Form 1116 on this year's tax bill alone is
how the households for whom it matters get it wrong.** The election also moves
IRA eligibility, the refundable child credit, a carryforward that is worth
money in later years, and — once revoked — five years of optionality. A
comparison that prints two numbers and picks the smaller one is not a wrong
calculation; it is the right calculation answering a smaller question than the
one asked.

So this module computes the two liabilities properly, and then reports every
consequence it can identify that the two liabilities do not capture — valued
where the facts allow it, named and left unvalued where they do not. Where an
unvalued consequence points the other way from the arithmetic, **no
recommendation is made.**

## Rates come from the facts file, never from this repository

`limits.py` already holds a hand-maintained slice of the tax code that nobody
has verified — `REVIEW.md` A3. Adding marginal brackets, the standard
deduction and the inflation-adjusted §911 cap to it would multiply the
blast radius of a single wrong entry across every skill that reads it.

So brackets, the standard deduction, the exclusion cap and the refundable
child-credit amount are **inputs**, on the same terms as
`assumptions.cash_benchmark_apr`: asked for, never fetched. Absent, this module
reports the *structure* of the decision — what moves it and in which direction
— and refuses the figure. That is a real answer, and it is the one that does
not silently go stale.

## Basis

Federal income tax only, on a cash basis, for one tax year, married-filing
status as recorded. **Not modelled:** self-employment tax (§911 does not
exclude it — a self-employed expat owes it on the excluded income too), NIIT,
the foreign housing exclusion, itemised deductions, AMT and state tax. The
§904 limitation is computed on **one general basket**, with the standard
deduction apportioned ratably between foreign- and US-source income; the
passive basket and itemised-deduction apportionment are not modelled. Each of
those is named in the report rather than left to be assumed away.

## What is refused outright

**GILTI is screened, never computed.** See `cfc_screen`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── §911 and §901 structure ─────────────────────────────────────────────────

#: §911(e)(2). Revoking the exclusion locks the taxpayer out for the five
#: following tax years absent IRS consent (a private letter ruling, with a fee
#: and a wait). This is the reason the election is not an annual coin-flip.
FEIE_REVOCATION_LOCK_YEARS = 5

#: §904(c). Unused foreign tax credits carry back one year and forward ten,
#: and only against foreign-source income in the same basket. A carryforward
#: is an option on future foreign income, not a receivable.
FTC_CARRYBACK_YEARS = 1
FTC_CARRYFORWARD_YEARS = 10

#: A child must be under this age at year end to be a qualifying child for the
#: child tax credit.
CTC_QUALIFYING_AGE = 17

#: §4973. Excise on an excess IRA contribution, charged **every year** it
#: remains in the account, not once.
IRA_EXCESS_EXCISE_RATE = 0.06

#: Below this fraction of the smaller liability, the two elections are treated
#: as too close to separate on the arithmetic alone. The modelling exclusions
#: listed in the module docstring are individually larger than this.
DECISION_MARGIN_FRACTION = 0.10


class BracketError(Exception):
    """The supplied bracket table cannot be used."""


@dataclass(frozen=True)
class Brackets:
    status: str
    #: (marginal rate, upper bound of the band). The last bound is None.
    rows: tuple[tuple[float, float | None], ...]
    standard_deduction: float
    as_of: str | None = None

    @property
    def top_rate(self) -> float:
        return self.rows[-1][0]


def parse_brackets(assumptions: dict | None, status: str) -> Brackets | None:
    """Read `assumptions.federal_brackets` and validate it hard.

    Validation is deliberately unforgiving. A bracket table is a list of
    numbers with no internal redundancy — a transposed digit produces a
    plausible liability rather than an error — so the only defences available
    are structural, and they are applied here rather than trusted.
    """
    a = assumptions or {}
    table = (a.get("federal_brackets") or {}).get(status)
    # `standard_deduction` is keyed by filing status here, but
    # `charitable-giving-strategy` reads the same key as a single figure. Both
    # shapes are accepted so one facts file can serve both.
    sd = a.get("standard_deduction")
    std = sd.get(status) if isinstance(sd, dict) else sd
    if not table or std is None:
        return None

    rows: list[tuple[float, float | None]] = []
    for i, row in enumerate(table):
        rate, up_to = row.get("rate"), row.get("up_to")
        if rate is None:
            raise BracketError(f"bracket {i} has no rate")
        if up_to is None and i != len(table) - 1:
            raise BracketError(
                f"bracket {i} has no upper bound but is not the last band")
        if up_to is not None and i == len(table) - 1:
            raise BracketError(
                "the last band must be open-ended (`up_to: null`); as supplied "
                "there is no rate for income above the final bound")
        rows.append((float(rate), None if up_to is None else float(up_to)))

    for i in range(1, len(rows)):
        if rows[i][0] <= rows[i - 1][0]:
            raise BracketError(
                f"rates are not ascending at band {i} "
                f"({rows[i - 1][0]:.0%} then {rows[i][0]:.0%})")
        prev, cur = rows[i - 1][1], rows[i][1]
        if cur is not None and prev is not None and cur <= prev:
            raise BracketError(f"band bounds are not ascending at band {i}")

    return Brackets(status=status, rows=tuple(rows),
                    standard_deduction=float(std),
                    as_of=a.get("federal_brackets_as_of"))


def tax_on(taxable: float, b: Brackets) -> float:
    """Ordinary federal income tax on a taxable amount."""
    taxable = max(0.0, float(taxable))
    tax, floor = 0.0, 0.0
    for rate, cap in b.rows:
        top = taxable if cap is None else min(taxable, cap)
        if top > floor:
            tax += (top - floor) * rate
        floor = cap if cap is not None else floor
        if cap is not None and taxable <= cap:
            break
    return tax


# ── the two elections ───────────────────────────────────────────────────────


@dataclass
class Election:
    """One way of filing, priced."""

    name: str
    excluded: float = 0.0
    taxable_income: float = 0.0
    precredit_tax: float = 0.0
    creditable_foreign_tax: float = 0.0
    credit_limitation: float = 0.0
    credit_used: float = 0.0
    carryforward: float = 0.0
    net_tax: float = 0.0
    #: Earned income able to support an IRA contribution under this election.
    ira_compensation: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class Adjustment:
    """A consequence the two liabilities do not capture."""

    label: str
    favours: str  # feie | ftc
    #: None where the facts do not allow it to be valued. Not zero.
    value: float | None
    detail: str


@dataclass
class Comparison:
    determinable: bool
    feie: Election | None = None
    ftc: Election | None = None
    adjustments: list[Adjustment] = field(default_factory=list)
    #: feie | ftc | too_close | undetermined
    recommendation: str = "undetermined"
    #: Positive means FTC costs less this year.
    current_year_delta: float = 0.0
    adjusted_delta: float = 0.0
    findings: list[str] = field(default_factory=list)
    weakest_input: str = ""

    @property
    def unvalued(self) -> list[Adjustment]:
        return [a for a in self.adjustments if a.value is None]


def _limitation(precredit: float, foreign_gross: float, total_gross: float) -> float:
    """§904: the credit cannot exceed the US tax on foreign-source income.

    The fraction is foreign-source *taxable* income over total taxable income.
    Deductions have to be apportioned to get the numerator, and the standard
    deduction is apportioned ratably — which makes the fraction equal to the
    ratio of the gross amounts. Taking the ratio on taxable income instead
    would put the whole standard deduction against US-source income and
    overstate the credit, in the direction of a refund that is not coming.
    """
    if total_gross <= 0:
        return 0.0
    return precredit * min(1.0, max(0.0, foreign_gross) / total_gross)


def compare(
    e: dict | None,
    *,
    brackets: Brackets | None,
    exclusion_cap: float | None,
    children_under_17: int = 0,
    refundable_ctc_per_child: float | None = None,
) -> Comparison:
    """Run the year both ways, then say what the two numbers leave out."""
    e = e or {}
    c = Comparison(determinable=False)

    foreign_earned = e.get("foreign_earned_income")
    foreign_tax_earned = e.get("foreign_tax_on_earned_income")
    if foreign_tax_earned is None:
        foreign_tax_earned = e.get("foreign_tax_paid")

    missing = []
    if foreign_earned is None:
        missing.append("`expat.foreign_earned_income`")
    if foreign_tax_earned is None:
        missing.append("`expat.foreign_tax_on_earned_income`")
    if brackets is None:
        missing.append("`assumptions.federal_brackets` and "
                       "`assumptions.standard_deduction`")
    if exclusion_cap is None:
        missing.append("`assumptions.feie_exclusion_cap`")

    if missing:
        c.findings.append(
            "**The comparison cannot be run, and no figure is offered.** "
            "Missing: " + ", ".join(missing) + ". The brackets, the standard "
            "deduction and the §911 cap are inputs to this repository rather "
            "than data held in it — they are year-specific, and a stale "
            "bracket table produces a confident dollar figure that is wrong "
            "by an amount nobody can see. Take them from the IRS revenue "
            "procedure for the year concerned. The structure of the decision "
            "below holds regardless.")
        return c

    c.determinable = True
    foreign_earned = float(foreign_earned)
    foreign_tax_earned = float(foreign_tax_earned)
    foreign_unearned = float(e.get("foreign_unearned_income") or 0.0)
    us_source = float(e.get("us_source_income") or 0.0)
    total_income = foreign_earned + foreign_unearned + us_source
    std = brackets.standard_deduction

    # ── Form 1116 route: no exclusion, credit the foreign tax ───────────
    ftc = Election("Form 1116 — foreign tax credit")
    ftc.taxable_income = max(0.0, total_income - std)
    ftc.precredit_tax = tax_on(ftc.taxable_income, brackets)
    ftc.creditable_foreign_tax = foreign_tax_earned
    ftc.credit_limitation = _limitation(
        ftc.precredit_tax, foreign_earned, total_income)
    ftc.credit_used = min(ftc.creditable_foreign_tax, ftc.credit_limitation)
    ftc.carryforward = max(0.0, ftc.creditable_foreign_tax - ftc.credit_limitation)
    ftc.net_tax = max(0.0, ftc.precredit_tax - ftc.credit_used)
    ftc.ira_compensation = foreign_earned

    # ── Form 2555 route: exclude, then credit only what is left ─────────
    feie = Election("Form 2555 — foreign earned income exclusion")
    feie.excluded = min(foreign_earned, float(exclusion_cap))
    feie.taxable_income = max(0.0, total_income - feie.excluded - std)
    # §911(f) stacking: the remaining income is taxed at the rates that would
    # have applied had nothing been excluded. People expect the leftover to be
    # taxed from the bottom bracket up; it is not, and that expectation is why
    # the exclusion disappoints at higher incomes.
    feie.precredit_tax = max(0.0, tax_on(feie.taxable_income + feie.excluded,
                                         brackets)
                             - tax_on(feie.excluded, brackets))
    # §911(d)(6): foreign tax allocable to excluded income is not creditable.
    unexcluded_share = (0.0 if foreign_earned <= 0
                        else max(0.0, foreign_earned - feie.excluded) / foreign_earned)
    feie.creditable_foreign_tax = foreign_tax_earned * unexcluded_share
    feie.credit_limitation = _limitation(
        feie.precredit_tax, foreign_earned - feie.excluded,
        total_income - feie.excluded)
    feie.credit_used = min(feie.creditable_foreign_tax, feie.credit_limitation)
    feie.carryforward = max(0.0, feie.creditable_foreign_tax - feie.credit_limitation)
    feie.net_tax = max(0.0, feie.precredit_tax - feie.credit_used)
    feie.ira_compensation = max(0.0, foreign_earned - feie.excluded)

    if feie.excluded >= foreign_earned:
        feie.notes.append(
            "All foreign earned income is excluded, so **none of the foreign "
            "tax on it is creditable** — the disallowance under §911(d)(6) is "
            "total, not partial. Foreign tax paid on that income is simply "
            "gone.")
    ftc.notes.append(
        "The §904 limitation apportions the standard deduction ratably "
        "between foreign- and US-source income. Foreign tax above the "
        "limitation is not refunded — it carries.")
    feie.notes.append(
        "Remaining income is taxed at the rates that would have applied "
        "without the exclusion (the §911 stacking rule), not from the bottom "
        "bracket up.")
    if brackets.as_of:
        ftc.notes.append(f"Brackets as supplied, dated {brackets.as_of}.")

    c.feie, c.ftc = feie, ftc
    c.current_year_delta = feie.net_tax - ftc.net_tax

    # ── what the two numbers leave out ──────────────────────────────────
    planned_ira = e.get("planned_ira_contribution")
    if planned_ira:
        planned_ira = float(planned_ira)
        if feie.ira_compensation < planned_ira:
            shortfall = planned_ira - feie.ira_compensation
            c.adjustments.append(Adjustment(
                "IRA contribution room", "ftc",
                round(shortfall * IRA_EXCESS_EXCISE_RATE, 2),
                f"**Excluded income cannot support an IRA contribution.** "
                f"Under the exclusion, compensation available is "
                f"{_money(feie.ira_compensation)} against a planned "
                f"{_money(planned_ira)} — a **{_money(shortfall)} excess "
                f"contribution**, carrying a {IRA_EXCESS_EXCISE_RATE:.0%} "
                "excise **for every year it stays in the account**, not once. "
                "The valued figure here is only the first year's excise; the "
                "real loss is the contribution itself and every year of "
                "sheltered growth behind it, which is not modelled. Under the "
                "credit, the full amount is supported."))
        else:
            c.adjustments.append(Adjustment(
                "IRA contribution room", "ftc", 0.0,
                f"The planned {_money(planned_ira)} contribution is supported "
                f"under either election — {_money(feie.ira_compensation)} of "
                "compensation survives the exclusion. Worth re-checking in "
                "any year income falls, because the exclusion is a fixed "
                "amount and compensation is not."))

    if children_under_17 > 0:
        c.adjustments.append(Adjustment(
            "Refundable child tax credit", "ftc",
            (None if refundable_ctc_per_child is None
             else round(children_under_17 * float(refundable_ctc_per_child), 2)),
            f"**Filing Form 2555 disqualifies the household from the "
            f"refundable additional child tax credit entirely** — Schedule "
            f"8812 asks the question directly. With {children_under_17} "
            "qualifying child(ren) and little or no US tax left to offset, "
            "the refundable portion is frequently the *only* part of the "
            "credit worth anything to an expat, so this is not a rounding "
            "item. "
            + ("It is left unvalued because "
               "`assumptions.additional_ctc_per_child` is not recorded; the "
               "amount is year-specific and this repository does not hold it."
               if refundable_ctc_per_child is None else
               "Valued at the per-child amount supplied in the facts file.")))

    if ftc.carryforward > 0:
        c.adjustments.append(Adjustment(
            "Foreign tax credit carryforward", "ftc", None,
            f"The credit route generates **{_money(ftc.carryforward)} of "
            f"unused credit**, carrying back {FTC_CARRYBACK_YEARS} year and "
            f"forward {FTC_CARRYFORWARD_YEARS}. The exclusion generates "
            f"{_money(feie.carryforward)}. It is deliberately left unvalued: "
            "it is usable only against future US tax on foreign-source income "
            "in the same basket, so a household returning to the US next year "
            "will never use it, and one staying abroad probably will. Value it "
            "yourself against your own plan — it is an option, not a "
            "receivable."))

    prior = e.get("feie_elected_prior_year")
    if prior and c.current_year_delta > 0:
        c.adjustments.append(Adjustment(
            "Five-year revocation lock", "feie", None,
            f"The exclusion was elected in a prior year. Switching to the "
            f"credit **revokes it, and revocation locks the household out for "
            f"the {FEIE_REVOCATION_LOCK_YEARS} following tax years** without "
            "IRS consent — which means a private letter ruling, a fee and a "
            "wait. So this is not a one-year decision being made once; it is "
            "a decision about the next six years, and it should be run "
            "against the expected path of the local tax rate rather than this "
            "year's. Moving to a lower-tax country inside that window is the "
            "case that hurts."))
    elif prior is None:
        c.findings.append(
            "`expat.feie_elected_prior_year` is not recorded. Whether the "
            "exclusion has ever been claimed decides whether choosing the "
            f"credit is a free choice or a {FEIE_REVOCATION_LOCK_YEARS}-year "
            "commitment. It is the cheapest fact here to establish — look at "
            "the prior return for a Form 2555.")

    # ── the recommendation, and when to withhold it ─────────────────────
    valued = sum(a.value * (1 if a.favours == "ftc" else -1)
                 for a in c.adjustments if a.value is not None)
    c.adjusted_delta = c.current_year_delta + valued

    smaller = min(feie.net_tax, ftc.net_tax)
    margin = max(1.0, smaller * DECISION_MARGIN_FRACTION)
    leader = "ftc" if c.adjusted_delta > 0 else "feie"
    against = [a for a in c.unvalued if a.favours != leader]

    if abs(c.adjusted_delta) < margin:
        c.recommendation = "too_close"
        c.findings.append(
            f"**Too close to call on the arithmetic.** The gap of "
            f"{_money(abs(c.adjusted_delta))} is inside "
            f"{DECISION_MARGIN_FRACTION:.0%} of the smaller liability, and "
            "several things this module does not model — self-employment tax, "
            "the housing exclusion, state conformity, the passive basket — "
            "are each capable of being larger than it.")
    elif against:
        c.recommendation = "too_close"
        c.findings.append(
            f"**The arithmetic favours the "
            f"{'credit' if leader == 'ftc' else 'exclusion'} by "
            f"{_money(abs(c.adjusted_delta))}, and no recommendation is made "
            f"anyway**, because "
            + "; ".join(f"*{a.label}*" for a in against)
            + " points the other way and cannot be valued from the facts "
              "recorded. Supply what is missing, or decide it deliberately. "
              "This is exactly the case the rule of thumb gets wrong: the "
              "current-year bill is the visible number and the smaller "
              "question.")
    else:
        c.recommendation = leader
        c.findings.append(
            f"**The {'credit' if leader == 'ftc' else 'exclusion'} wins by "
            f"{_money(abs(c.adjusted_delta))}** once the valued adjustments "
            "are applied, and nothing unvalued points the other way.")

    c.weakest_input = (
        "the bracket table and standard deduction supplied in the facts file. "
        "Everything above is arithmetic on top of them, and nothing in this "
        "repository can tell whether they are the right year's")
    return c


# ── state domicile: a cited table, and a short one ──────────────────────────


@dataclass(frozen=True)
class DomicileRules:
    """Whether and how a state lets go of a former resident.

    Same discipline as `jurisdiction.py`: a state is here only if the rule was
    checked, with a source and a verification date. Everything else is
    `UNKNOWN`, and the skill says so rather than applying the rule it happens
    to know. State residency rules diverge more than they converge, and the
    ones that hurt are the ones that differ from the one you have read about.
    """

    state: str
    known: bool
    #: Does the state levy a personal income tax at all?
    has_income_tax: bool | None = None
    #: True where residency turns on facts and circumstances with no day-count
    #: bright line, so leaving cannot be proven by a calendar alone.
    no_bright_line: bool | None = None
    #: Consecutive days of employment-related absence qualifying for a
    #: statutory safe harbour, where one exists.
    safe_harbor_days: int | None = None
    #: Whether the state conforms to the federal §911 exclusion. `None` means
    #: nobody has checked — never assume the federal exclusion carries.
    conforms_to_feie: bool | None = None
    guidance: str = ""
    notes: tuple[str, ...] = ()
    source: str = ""
    verified_on: str = ""


UNKNOWN_STATE = DomicileRules(state="??", known=False)

#: States with a reputation for pursuing departed residents. This is a
#: practice observation, **not an encoded rule** — nothing about how these
#: states actually test residency is asserted anywhere in this module, and for
#: NY, VA and SC nothing is in the table at all. It exists so a household
#: leaving one is told to expect scrutiny, not so a conclusion can be drawn.
HIGH_SCRUTINY_STATES = ("CA", "NY", "VA", "SC")

# ── California ──────────────────────────────────────────────────────────────
# R&TC §17014; FTB Publication 1031. Residency turns on "closest connections"
# — a facts-and-circumstances test with no day-count bright line. §17014(d)
# provides a safe harbour for an uninterrupted employment-related absence of
# at least 546 consecutive days.
CA = DomicileRules(
    state="CA",
    known=True,
    has_income_tax=True,
    no_bright_line=True,
    safe_harbor_days=546,
    conforms_to_feie=None,
    guidance="FTB Publication 1031 (Guidelines for Determining Resident Status)",
    notes=(
        "There is no number of days that proves you left. The test weighs "
        "where your closest connections are, and a day count is one factor "
        "among many — which is why a severance checklist, not a calendar, is "
        "the evidence that matters.",
        "The §17014(d) safe harbour requires the absence to be "
        "employment-related and uninterrupted, and it is lost by more than a "
        "limited number of days back in the state. It is a safe harbour, not "
        "a definition of non-residence.",
        "Whether California conforms to the federal §911 exclusion is NOT "
        "recorded here and must not be assumed. State conformity to federal "
        "exclusions is piecemeal, and a household that keeps California "
        "residency can find the exclusion applies federally and not at state "
        "level.",
    ),
    source="CA R&TC §17014; FTB Pub. 1031",
    verified_on="unverified — check against the CA Franchise Tax Board",
)

# ── Texas ───────────────────────────────────────────────────────────────────
# No personal income tax, so there is no residency determination to win or
# lose for income-tax purposes. Domicile still governs community property and
# probate.
TX = DomicileRules(
    state="TX",
    known=True,
    has_income_tax=False,
    no_bright_line=None,
    safe_harbor_days=None,
    conforms_to_feie=None,
    guidance="No personal income tax; no state residency filing determination",
    notes=(
        "With no personal income tax there is no state return to be resident "
        "for, so leaving Texas raises no state income-tax exit question.",
        "Domicile still matters here for **community property** and for "
        "probate. Moving between a community-property state and a "
        "common-law one changes the character of assets acquired on each side "
        "of the move, and that survives the move in both directions.",
    ),
    source="Texas levies no personal income tax (Tex. Const. art. VIII)",
    verified_on="unverified — check against the Texas Comptroller",
)

_DOMICILE: dict[str, DomicileRules] = {"CA": CA, "TX": TX}

DOMICILE_SOURCE = "each state's revenue authority"
DOMICILE_VERIFIED = "unverified"


def domicile_states_available() -> list[str]:
    return sorted(_DOMICILE)


def domicile_rules(state: str | None) -> DomicileRules:
    if not state:
        return UNKNOWN_STATE
    return _DOMICILE.get(state.strip().upper(),
                         DomicileRules(state=state.upper(), known=False))


#: The severance factors states actually weigh. Ordered roughly by the weight
#: they carry in published guidance: where you sleep, where your family is and
#: where your business is beat where your mail goes.
SEVERANCE_STEPS: tuple[tuple[str, str], ...] = (
    ("home", "Sell or genuinely let the former home. A property kept "
             "available for your own use is the single heaviest factor "
             "against you, and 'we kept it as an investment' is tested "
             "against whether anyone else actually lives in it."),
    ("family", "Move the spouse and school-age children. A household split "
               "across the state line is read as one household that never "
               "left."),
    ("business", "Wind down or relocate active business ties. Passive "
                 "holdings matter far less than a business you show up to."),
    ("days", "Reduce days in the state, and keep contemporaneous evidence of "
             "them. A count reconstructed later is worth much less than a "
             "calendar kept at the time."),
    ("drivers_license", "Surrender the licence and obtain one where you now "
                        "live."),
    ("voter_registration", "Register to vote in the new place and cancel the "
                           "old registration. Voting in the former state "
                           "after claiming to have left is close to "
                           "dispositive against you."),
    ("vehicle_registration", "Re-register and re-insure vehicles."),
    ("professional_advisors", "Move doctors, dentists, accountant and "
                              "lawyer. These are 'near and dear' indicators "
                              "and are routinely asked about."),
    ("banking", "Move primary banking and safe deposit boxes."),
    ("memberships", "Resign or convert resident memberships — clubs, gyms, "
                    "religious congregations — to non-resident status."),
    ("mailing_address", "Change the address on every account, not just the "
                        "post office forwarding order."),
    ("estate_documents", "Re-execute the will and powers of attorney under "
                         "the new jurisdiction's law. These are read as a "
                         "statement of where you consider yourself domiciled "
                         "— and they are the step households forget."),
)


@dataclass
class DomicileExit:
    from_state: str | None
    to_state: str | None
    rules: DomicileRules
    destination_rules: DomicileRules
    completed: list[str] = field(default_factory=list)
    outstanding: list[tuple[str, str]] = field(default_factory=list)
    unrecorded: list[tuple[str, str]] = field(default_factory=list)
    days_in_state: int | None = None
    findings: list[str] = field(default_factory=list)

    @property
    def score(self) -> str:
        done = len(self.completed)
        total = len(SEVERANCE_STEPS)
        return f"{done}/{total}"


def domicile_exit(
    spec: dict | None,
    *,
    days_in_state: int | None = None,
    new_domicile_established: bool | None = None,
) -> DomicileExit:
    """Score the severance, and lead with the rule people get backwards."""
    spec = spec or {}
    frm = (spec.get("from_state") or "").strip().upper() or None
    to = (spec.get("to_state") or "").strip().upper() or None
    ties = spec.get("severance") or {}

    x = DomicileExit(from_state=frm, to_state=to,
                     rules=domicile_rules(frm),
                     destination_rules=domicile_rules(to),
                     days_in_state=days_in_state)

    for key, detail in SEVERANCE_STEPS:
        v = ties.get(key)
        if v is True:
            x.completed.append(key)
        elif v is False:
            x.outstanding.append((key, detail))
        else:
            x.unrecorded.append((key, detail))

    # The finding that reframes everything else.
    x.findings.append(
        "**You do not lose a domicile by leaving. You lose it by acquiring "
        "another one.** Domicile is singular and sticky: the old one persists "
        "until a new one is established with the intent to remain "
        "indefinitely. A household that leaves for a posting abroad, keeps a "
        "home, and intends to come back has not changed domicile, however "
        "many days it is away — and moving somewhere you are yourself "
        "uncertain about is precisely the case where the former state's claim "
        "survives.")

    if new_domicile_established is False:
        x.findings.append(
            "**No new domicile has been established.** On the rule above, "
            "that alone is close to fatal to the exit claim regardless of how "
            "many severance steps are complete.")
    elif new_domicile_established is None:
        x.findings.append(
            "Whether a new domicile has actually been established is not "
            "recorded. It is the load-bearing question, not a detail.")

    x.findings.append(
        "**Statutory residence is a second, independent hook.** Many states "
        "tax someone as a resident on a day count plus a permanent place of "
        "abode, whether or not they are domiciled there. Winning the domicile "
        "argument and still being a statutory resident is a common and "
        "expensive outcome. Whether the state concerned has such a rule, and "
        "what it counts, is not encoded here.")

    x.findings.append(
        "**Source income is taxed either way.** Wages for work physically "
        "performed in the state, rent from property there, and income from a "
        "business operating there remain state-taxable to a non-resident. "
        "Leaving changes the residency question, not the sourcing one.")

    if not x.rules.known and frm:
        x.findings.append(
            f"**{frm} is not in the cited table, so no rule about it is "
            f"asserted here.** Only "
            f"{', '.join(domicile_states_available())} have been checked. "
            + (f"{frm} has a reputation for pursuing departed residents — "
               "that is a practice observation and not a rule, and it means "
               "you should read that state's own published residency guidance "
               "rather than infer anything from the states that are in the "
               "table."
               if frm in HIGH_SCRUTINY_STATES else
               "Read that state's own published residency guidance; the rules "
               "diverge more than they converge, and reasoning by analogy "
               "from a state that is in the table is how the wrong answer "
               "gets produced confidently."))
    elif x.rules.known and x.rules.has_income_tax is False:
        x.findings.append(
            f"**{frm} levies no personal income tax**, so there is no state "
            "residency determination to lose and no exit audit to fear on "
            "income. The steps below still matter for the destination's "
            "claim, and domicile still governs probate and community "
            "property.")
    elif x.rules.known and x.rules.no_bright_line:
        x.findings.append(
            f"**{frm} has no day-count bright line** — {x.rules.guidance}. "
            "There is no number of days that proves you left, which is why "
            "the checklist below is the evidence and the calendar is only one "
            "item on it."
            + (f" A statutory safe harbour exists for an uninterrupted "
               f"employment-related absence of {x.rules.safe_harbor_days} "
               "consecutive days or more; it is narrow, and it is lost by "
               "spending too long back in the state."
               if x.rules.safe_harbor_days else ""))

    if x.rules.known and x.rules.conforms_to_feie is None and x.rules.has_income_tax:
        x.findings.append(
            f"**Whether {frm} conforms to the federal §911 exclusion is not "
            "recorded, and must not be assumed.** If the state still treats "
            "you as a resident, foreign earned income excluded federally may "
            "be fully taxable at state level — which can make the state "
            "question worth more than the federal election in "
            "`feie-vs-ftc`.")

    if days_in_state is None:
        x.findings.append(
            "Days spent in the state could not be counted: the travel ledger "
            "has no US state detail. Add `state:` to US stays in "
            "`presence.days` and the same ledger that answers the 330-day "
            "test answers this one. An uncounted day is not a day you were "
            "absent.")

    return x


# ── CFC: a screen, and it stops on purpose ──────────────────────────────────

#: §951(b). A US person owning this share of vote **or** value is a US
#: shareholder. Value is frequently overlooked; owning non-voting shares does
#: not keep you out.
US_SHAREHOLDER_PCT = 10

#: §957(a). A foreign corporation is a CFC when US shareholders own more than
#: this share of vote or value on any day of the year. More than 50%, not 50%.
CFC_CONTROL_PCT = 50

#: §6038(b). Per form, per year, for a late or incomplete Form 5471 — before
#: the continuation penalty, which adds the same again per 30 days after
#: notice up to the cap. There is no tax due for this to apply to.
FORM_5471_PENALTY = 10_000
FORM_5471_CONTINUATION_CAP = 50_000

#: §6501(c)(8). The statute of limitations on the **entire return** does not
#: start until the required information return is filed. This is usually the
#: larger consequence and is the one nobody has heard of.
STATUTE_STAYS_OPEN = True

#: §957(a) control also exists where the threshold is met for an uninterrupted
#: period of this many days during the year — relevant to a mid-year sale.
CONTROL_PERIOD_DAYS = 30

#: Entity kinds that produce a filing obligation under a *different* form,
#: and are missed because people screen for "foreign corporation".
OTHER_FORMS = {
    "foreign_partnership": ("Form 8865", "a US person with a controlling or "
                            "10%-plus interest in a foreign partnership"),
    "disregarded_entity": ("Form 8858", "a foreign disregarded entity or "
                           "foreign branch — including a single-member "
                           "foreign LLC and an unincorporated consulting "
                           "business run abroad"),
    "foreign_trust": ("Forms 3520 and 3520-A", "a US owner or beneficiary of "
                      "a foreign trust"),
}


@dataclass
class EntityScreen:
    name: str
    country: str | None
    kind: str
    ownership_pct: float | None
    us_shareholder_pct: float | None
    #: None where ownership is not recorded — never assumed to be below.
    is_us_shareholder: bool | None = None
    is_cfc: bool | None = None
    forms: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)


@dataclass
class CfcScreen:
    entities: list[EntityScreen] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    @property
    def any_cfc(self) -> bool:
        return any(e.is_cfc for e in self.entities)

    @property
    def any_undetermined(self) -> bool:
        return any(e.is_cfc is None for e in self.entities)


def cfc_screen(entities: list[dict] | None) -> CfcScreen:
    """Establish whether a CFC exists and name the filings. Then stop.

    **This deliberately does not compute GILTI and does not model a §962
    election.** The election interacts with the §250 deduction, indirect
    foreign tax credits, the later distribution being taxed again, state
    treatment that frequently does not follow the federal result, and QBI.
    A number produced here would carry none of that and would look exactly as
    authoritative as one that did. The screen's job is to establish that the
    household is in a regime where those questions arise, quantify the
    *penalty* exposure — which is knowable — and hand over.
    """
    s = CfcScreen()
    rows = entities or []

    if not rows:
        s.findings.append(
            "**No foreign entities recorded.** If there are none, record "
            "`expat.foreign_entities: []` so the answer is checked rather "
            "than absent. The category is wider than it sounds: a foreign "
            "company you consult through, a family business holding you never "
            "think of as yours, an unincorporated business abroad, and a "
            "single-member foreign LLC all land somewhere in this section.")
        return s

    for i, row in enumerate(rows):
        name = row.get("name") or f"entity #{i}"
        kind = (row.get("kind") or "foreign_corporation").strip().lower()
        own = row.get("ownership_pct")
        total = row.get("us_shareholder_pct")
        if total is None:
            total = own

        e = EntityScreen(name=name, country=row.get("country"), kind=kind,
                         ownership_pct=own, us_shareholder_pct=total)

        if kind in OTHER_FORMS:
            form, who = OTHER_FORMS[kind]
            e.forms.append(form)
            e.findings.append(
                f"Recorded as **{kind.replace('_', ' ')}**, which is outside "
                f"the CFC rules but not outside the filing rules: {form} "
                f"applies to {who}. Screening only for foreign *corporations* "
                "is how these get missed.")
            s.entities.append(e)
            continue

        if own is None:
            e.findings.append(
                "**Ownership percentage is not recorded, so nothing can be "
                "determined.** Not recorded is not the same as below the "
                "threshold — and the thresholds are met on vote *or* value, "
                "so non-voting shares do not keep you out.")
            s.entities.append(e)
            continue

        own = float(own)
        total = float(total)
        e.is_us_shareholder = own >= US_SHAREHOLDER_PCT
        e.is_cfc = total > CFC_CONTROL_PCT and e.is_us_shareholder

        if e.is_cfc:
            e.forms.append("Form 5471 (category 5 — US shareholder of a CFC)")
            if own > CFC_CONTROL_PCT:
                e.forms.append("Form 5471 (category 4 — control)")
            e.forms.append("Form 8992 (GILTI inclusion)")
            e.findings.append(
                f"**A CFC.** US shareholders hold {total:g}% — over the "
                f"{CFC_CONTROL_PCT}% control threshold — and this holding of "
                f"{own:g}% is at or above the {US_SHAREHOLDER_PCT}% US "
                "shareholder threshold. Both conditions are required and both "
                "are met.")
            e.findings.append(
                "Consequences that follow automatically, with no distribution "
                "and no cash received: a **GILTI inclusion** in current "
                "income, **Subpart F** income picked up currently, and the "
                "information returns above. Being taxed on profits you have "
                "not been paid is the part that surprises people.")
        elif e.is_us_shareholder:
            e.findings.append(
                f"A {own:g}% holding makes this a **US shareholder** position "
                f"(the threshold is {US_SHAREHOLDER_PCT}%) but US "
                f"shareholders hold only {total:g}% in total, so it is not a "
                f"CFC on the figures recorded. Form 5471 can still apply — "
                "category 3 on an acquisition that crosses 10%, and other "
                "categories on officer or director status. Being under the "
                "control threshold is not the same as having no filing.")
        else:
            e.findings.append(
                f"A {own:g}% holding is below the {US_SHAREHOLDER_PCT}% US "
                "shareholder threshold, so no CFC inclusion arises from it on "
                "the figures recorded.")
        s.entities.append(e)

    if any(e.is_cfc or e.is_us_shareholder for e in s.entities):
        s.findings.append(
            f"**The penalties are the quantifiable part, and they do not "
            f"depend on any tax being due.** Form 5471 carries "
            f"{_money(FORM_5471_PENALTY)} **per form, per year**, with a "
            f"continuation penalty of the same again per 30 days after IRS "
            f"notice, capped at {_money(FORM_5471_CONTINUATION_CAP)} — plus a "
            "10% reduction in foreign tax credits. Three entities and three "
            "unfiled years is a six-figure exposure on a company that made "
            "nothing.")
        s.findings.append(
            "**A missing Form 5471 keeps the statute of limitations open on "
            "the entire return**, not just the part about the entity "
            "(§6501(c)(8)). Years that felt closed are not closed. This is "
            "usually the larger consequence and is the one nobody has heard "
            "of.")

    s.findings.append(
        "**Direct ownership understates the position.** Attribution rules "
        "treat shares held by a spouse, children, parents, partnerships and "
        "trusts as yours, so a family company where no individual holds a "
        "majority can still be a CFC. Two minority holders who are related "
        "is the ordinary case, not an edge case.")

    s.findings.append(
        "**This screen stops here, deliberately.** It does not compute a "
        "GILTI inclusion and it does not model a §962 election. That election "
        "interacts with the §250 deduction, indirect foreign tax credits, the "
        "later distribution being taxed a second time, state treatment that "
        "often does not follow the federal result, and QBI — and a number "
        "produced without those would look exactly as confident as one "
        "produced with them. What this establishes is that you are in a "
        "regime where the question arises, and what it costs to ignore the "
        "forms while deciding. Take it to a cross-border CPA or EA.")
    return s


def _money(x) -> str:
    return f"${x:,.0f}"
