"""Cross-border retirement: what travels with you, and what does not.

## The one idea

**A US retirement account is a creature of US law, and the destination decides
for itself what the wrapper is.** Nothing obliges a foreign revenue authority
to agree that a Roth is tax-free. Where it does not, the account becomes an
ordinary pot of money that gets taxed on the way out — after the household
already paid US tax on the way in.

That single fact **inverts the conversion advice** the rest of this repository
gives. `roth-conversion-window` is right for a household that stays: pay tax
now at a low rate to buy tax-free growth. For a household that leaves for a
destination that does not honour the wrapper, the same conversion pays a real,
irreversible US tax bill to buy an exemption the destination will not grant —
and the two tax events land in different years, so neither country's relief
mechanism can offset the other.

## What is encoded and what is refused

This is the area where this repository is **least able to be authoritative**.
Foreign treatment of US retirement accounts is contested, treaty-dependent, and
expensive to get wrong. So the country table follows the `jurisdiction.py`
pattern with the dial turned further toward refusal:

- A country is here **only if checked**, with `source` and `verified_on`.
- Everything else is `UNKNOWN`. **Never reason by analogy from a country you do
  know** — the whole point is that destinations differ.
- Treaty article numbers and foreign tax rates are **not encoded at all**.
  Where the answer turns on one, the skill names the question and stops.
- Every entry carries `needs_professional_verification`: the specific items the
  report must flag rather than assert.

The arithmetic — blended burn rates, location-adjusted targets, the Part B
penalty — is fully rigorous and carries the weight the tax content cannot.

## Basis

Burn rates and targets here are **real** — today's money throughout — because
they are consumed by `retirement.py`, which is real throughout. Medicare
premiums and penalties are **nominal current-year figures supplied by the
caller**, not projected, and are labelled as such in the report.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import retirement as _ret
from . import status as _status

#: The Medicare late-enrolment penalty rates are defined in `healthcare.py` and
#: imported, not restated. They were written independently in both modules —
#: under two different names for the Part B one — which is exactly how two
#: copies of a statutory rate drift apart. One definition, one provenance entry.
from .healthcare import (  # noqa: F401
    PART_B_PENALTY_PER_12M,
    PART_D_PENALTY_PER_MONTH,
)

# ── how a destination treats the Roth wrapper ───────────────────────────────

#: The destination treats a Roth distribution as tax-free, as the US does.
RECOGNISED = "recognised"
#: Practitioners disagree, or relief exists but addresses timing rather than
#: character. Treated as *not recognised* for planning purposes, because the
#: decision it feeds — a conversion — is irreversible.
CONTESTED = "contested"
#: The destination taxes distributions as ordinary local income.
NOT_RECOGNISED = "not_recognised"
#: Nobody has checked. Not the same as "no".
UNKNOWN_STATUS = "unknown"

#: Statuses under which conversion advice inverts. `CONTESTED` is in here on
#: purpose: an irreversible act should not be taken on a contested reading.
INVERTING_STATUSES = (CONTESTED, NOT_RECOGNISED)


@dataclass(frozen=True)
class ResidencyTest:
    """One day test a destination uses to make someone tax resident."""

    label: str
    days: int
    #: Years the day count is measured over. 1 means the tax year alone.
    window_years: int = 1
    #: True where crossing this threshold alone establishes residence. A
    #: precondition to another test is not standalone, and flagging one as
    #: though it were produces noise that trains the reader to skip warnings.
    standalone: bool = True
    note: str = ""


@dataclass(frozen=True)
class Country:
    code: str
    known: bool
    name: str = ""
    #: One of RECOGNISED / CONTESTED / NOT_RECOGNISED / UNKNOWN_STATUS.
    roth_status: str = UNKNOWN_STATUS
    roth_note: str = ""
    #: Does the country tax the worldwide income of its tax residents?
    taxes_worldwide_income: bool | None = None
    residency_tests: tuple[ResidencyTest, ...] = ()
    #: A transitional regime for returning residents, if one exists.
    transitional_status: str = ""
    transitional_note: str = ""
    transitional_max_years: int | None = None
    notes: tuple[str, ...] = ()
    #: Items a report must flag as requiring a cross-border professional rather
    #: than assert. Every entry has some; that is the honest state of this data.
    needs_professional_verification: tuple[str, ...] = ()
    #: Provenance. Surfaced by `provenance.py` so a stale entry is visible
    #: rather than merely wrong.
    source: str = ""
    verified_on: str = ""

    @property
    def roth_recognised(self) -> bool | None:
        """Tri-state. `None` means contested or unchecked — not "no"."""
        if self.roth_status == RECOGNISED:
            return True
        if self.roth_status == NOT_RECOGNISED:
            return False
        return None

    @property
    def inverts_conversion_advice(self) -> bool:
        return self.roth_status in INVERTING_STATUSES

    def asserted_values(self) -> dict:
        """Every value this entry asserts, for the provenance checklist.

        Generated rather than hand-listed: a hand-written checklist silently
        omits whatever was added to the entry after it was written.
        """
        return {
            "roth_status": self.roth_status,
            "taxes_worldwide_income": self.taxes_worldwide_income,
            "residency_tests": tuple(
                (t.label, t.days, t.window_years, t.standalone)
                for t in self.residency_tests),
            "transitional_status": self.transitional_status or None,
            "transitional_max_years": self.transitional_max_years,
        }


UNKNOWN = Country(code="??", known=False)

# ── United States ───────────────────────────────────────────────────────────
# The origin of the wrapper, and the baseline every relocation is measured
# against. Included so "stay put" is a row in the table rather than an
# unstated assumption.
US = Country(
    code="US",
    known=True,
    name="United States",
    roth_status=RECOGNISED,
    roth_note="Qualified Roth distributions are tax-free under IRC §408A. "
              "This is the treatment every Roth conversion argument assumes, "
              "and it is the only jurisdiction guaranteed to apply it.",
    taxes_worldwide_income=True,
    residency_tests=(
        ResidencyTest(
            "substantial presence", 183, 3,
            note="Days in the current year count fully, the prior year at "
                 "one-third, the year before at one-sixth. A pattern of long "
                 "visits can therefore reach 183 without any single year "
                 "coming close."),
        ResidencyTest(
            "minimum current-year presence", 31, 1, standalone=False,
            note="Substantial presence also requires at least 31 days in the "
                 "current year, whatever the weighted total. A precondition, "
                 "not a test on its own — 31 days alone makes nobody "
                 "resident."),
    ),
    notes=(
        "US citizens and lawful permanent residents are taxed on worldwide "
        "income wherever they live. Leaving does not end the obligation; only "
        "relinquishing the status does, and that has its own tax — see "
        "`citizenship-status-review` on §877A.",
        "Someone on a nonimmigrant visa who meets substantial presence is a US "
        "tax resident on worldwide income exactly as a citizen would be.",
    ),
    needs_professional_verification=(
        "Whether a closer-connection exception or a treaty tie-breaker applies "
        "in a year when two countries both claim residence.",
    ),
    source="IRC §408A (Roth); IRC §7701(b)(3) (substantial presence test)",
    verified_on="unverified — check against irs.gov",
)

# ── India ───────────────────────────────────────────────────────────────────
# Encoded narrowly and deliberately. Roth recognition is CONTESTED rather than
# decided; Section 89A relief is described by what it addresses, not by a rate
# or an article number; no totalization agreement is imported from status.py
# rather than restated here.
IN = Country(
    code="IN",
    known=True,
    name="India",
    roth_status=CONTESTED,
    roth_note="Contested is the finding, not a placeholder for one. India's "
              "Section 89A relief (Finance Act 2021) addresses the *timing* "
              "mismatch on foreign retirement accounts — income accruing in "
              "the account "
              "before withdrawal — for residents of notified countries. It is "
              "relief on when income is taxed, not a statement that a Roth "
              "distribution is tax-free in India. Practitioners do not agree "
              "that the US tax-free character survives the border, and this "
              "table will not pretend they do. Plan as though distributions "
              "are taxable locally as ordinary income until a professional "
              "says otherwise in writing.",
    taxes_worldwide_income=True,
    residency_tests=(
        ResidencyTest(
            "resident — 182 days", 182, 1,
            note="182 days or more in India during the tax year (1 April to "
                 "31 March, which is not the US calendar year — a split-year "
                 "arrangement can be under the threshold on one country's "
                 "calendar and over it on the other's)."),
        ResidencyTest(
            "resident — 60 days plus 365 over four years", 60, 1,
            note="60 days or more in the year *and* 365 days or more across "
                 "the four preceding years. This is the test that catches a "
                 "split-living arrangement nobody thought was close to "
                 "residency."),
    ),
    transitional_status="RNOR",
    transitional_note="**Resident but Not Ordinarily Resident** is a "
                      "transitional status for someone returning to India "
                      "after a long absence. Broadly, foreign-source income "
                      "is outside the Indian net while it lasts, which makes "
                      "the RNOR years the natural window for realising US "
                      "gains or taking US distributions. The qualifying "
                      "conditions turn on non-residence in nine of the ten "
                      "preceding years, or on days present across the seven "
                      "preceding years — counted precisely, from a travel log "
                      "nobody keeps retrospectively.",
    transitional_max_years=3,
    notes=(
        "India's tax year runs 1 April to 31 March. Every day count, every "
        "deadline and every 'this year' in Indian advice is on that calendar, "
        "and mixing it with the US calendar year is a documented way to get a "
        "residency answer wrong by months.",
        "PFIC treatment of Indian mutual funds held by a US person is a "
        "separate and expensive problem. It is owned by "
        "`foreign-reporting-audit`, not restated here.",
    ),
    needs_professional_verification=(
        "Whether a Roth distribution is taxable in India, and on what basis — "
        "the single most consequential open question in this report.",
        "Whether Section 89A relief is available on these specific accounts, "
        "what election it requires, and by when.",
        "The exact RNOR qualifying conditions and how many years they would "
        "last for this household, computed from an actual travel log.",
        "Whether the 60-day test is shortened for a person of Indian origin "
        "with Indian-source income above a threshold — a variant exists and "
        "this table does not encode its terms.",
        "Treaty treatment of pensions and retirement distributions. No article "
        "number is encoded here on purpose.",
    ),
    source="India Income-tax Act residency tests; Section 89A (Finance Act "
           "2021) foreign retirement account relief. Roth character "
           "deliberately recorded as contested rather than resolved.",
    verified_on="unverified — check against incometaxindia.gov.in and a "
                "cross-border tax professional",
)

_TABLE: dict[str, Country] = {"US": US, "IN": IN}

CROSSBORDER_SOURCE = "foreign treatment of US retirement accounts"
CROSSBORDER_VERIFIED = (
    "unverified — every entry needs a cross-border tax professional")


def country_for(code: str | None) -> Country:
    if not code:
        return UNKNOWN
    return _TABLE.get(code.strip().upper(), Country(code=code.upper(), known=False))


def countries_available() -> list[str]:
    return sorted(_TABLE)


# ── the Roth portability check ──────────────────────────────────────────────

#: Above this exposed balance, a few hundred dollars of cross-border tax
#: opinion is trivial against the amount at risk. Below it, the same opinion
#: can cost more than the mistake.
PROFESSIONAL_ADVICE_THRESHOLD = 50_000

#: A conversion cannot be undone — recharacterisation of a conversion was
#: repealed. Beyond this horizon, treaty positions and domestic law have had
#: long enough to change that today's treatment should not drive an
#: irreversible act taken today.
TREATY_HORIZON_YEARS = 10


@dataclass
class Destination:
    label: str
    country: Country
    years_until_move: float | None = None
    #: Destination ordinary-income rate, supplied by the caller. Never
    #: inferred: a rate guessed for a country is exactly the fabrication this
    #: module exists to avoid.
    ordinary_rate: float | None = None
    exposed_balance: float | None = None
    double_tax_estimate: float | None = None
    findings: list[str] = field(default_factory=list)

    @property
    def inverts(self) -> bool:
        return self.country.inverts_conversion_advice


@dataclass
class Portability:
    roth_balance: float | None
    traditional_balance: float | None
    planned_conversion: float | None
    conversion_tax_rate: float | None
    conversion_tax_now: float | None
    destinations: list[Destination] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    @property
    def any_inverts(self) -> bool:
        return any(d.inverts for d in self.destinations)

    @property
    def any_unknown(self) -> bool:
        return any(not d.country.known for d in self.destinations)


def portability(
    destinations_raw: list[dict],
    *,
    roth_balance: float | None = None,
    traditional_balance: float | None = None,
    planned_conversion: float | None = None,
    conversion_tax_rate: float | None = None,
) -> Portability:
    """Does the destination recognise the Roth wrapper, and what follows.

    `roth_balance` of `None` means nobody looked — reported as undeterminable
    rather than treated as zero.
    """
    conv_tax = (planned_conversion * conversion_tax_rate
                if planned_conversion is not None and conversion_tax_rate is not None
                else None)
    p = Portability(
        roth_balance=roth_balance,
        traditional_balance=traditional_balance,
        planned_conversion=planned_conversion,
        conversion_tax_rate=conversion_tax_rate,
        conversion_tax_now=conv_tax,
    )

    for row in destinations_raw or []:
        code = row.get("country")
        c = country_for(code)
        d = Destination(
            label=row.get("label") or c.name or (code or "unnamed"),
            country=c,
            years_until_move=row.get("years_until_move"),
            ordinary_rate=row.get("ordinary_income_rate"),
        )

        if roth_balance is not None:
            d.exposed_balance = roth_balance + (planned_conversion or 0.0)

        if not c.known:
            d.findings.append(
                f"**{code or 'This destination'} is not in the table, so "
                "nothing can be said about it.** This module will not reason "
                "by analogy from a country it does know — that is precisely "
                "the error it exists to prevent, because destinations differ "
                "on exactly the point that matters. Establish, in writing and "
                "from a professional in that jurisdiction: whether a Roth "
                "distribution is taxed locally, whether a treaty addresses it, "
                "and how the local residency day test is counted."
            )
            p.destinations.append(d)
            continue

        if c.roth_status == RECOGNISED:
            d.findings.append(f"**Roth recognised.** {c.roth_note}")
        elif c.roth_status == CONTESTED:
            d.findings.append(
                f"🚫 **The Roth trap — contested, which means plan as if "
                f"not recognised.** {c.roth_note}"
            )
        else:
            d.findings.append(
                f"🚫 **The Roth trap — not recognised.** {c.roth_note}")

        if d.inverts:
            if d.exposed_balance is None:
                d.findings.append(
                    "The size of the exposure **cannot be determined**: no "
                    "Roth balance is recorded. A missing balance is not a zero "
                    "balance, and the arithmetic below is the whole argument."
                )
            elif d.ordinary_rate is None:
                d.findings.append(
                    f"{_money(d.exposed_balance)} of Roth balance would be "
                    "exposed, but **no destination ordinary-income rate is "
                    "recorded, so the cost cannot be quantified.** This module "
                    "will not guess a foreign tax rate. Get the rate that "
                    "would apply to a retirement distribution for a resident "
                    "at that income level and record it."
                )
            else:
                d.double_tax_estimate = d.exposed_balance * d.ordinary_rate
                d.findings.append(
                    f"At {d.ordinary_rate:.0%}, roughly "
                    f"**{_money(d.double_tax_estimate)}** of local tax would "
                    f"fall on {_money(d.exposed_balance)} of Roth balance that "
                    "US tax has already been paid on. A rough figure on a "
                    "supplied rate, not a computation of a foreign tax "
                    "liability — it is here to establish the order of "
                    "magnitude, which is the part that changes decisions."
                )

            if c.transitional_status:
                d.findings.append(
                    f"**A transitional window may help — {c.transitional_status}, "
                    f"up to about {c.transitional_max_years} years.** "
                    f"{c.transitional_note}"
                )

        if (d.years_until_move is not None
                and d.years_until_move > TREATY_HORIZON_YEARS):
            d.findings.append(
                f"The move is **{d.years_until_move:.0f} years out**, past the "
                f"{TREATY_HORIZON_YEARS}-year mark where today's treatment "
                "should not drive an irreversible act. Treaties are "
                "renegotiated and domestic law changes. What survives that "
                "horizon is the *shape* of the risk — that the wrapper may not "
                "travel — not this year's reading of it."
            )

        t = _status.totalization(c.code)
        if t.known and t.agreement is False:
            d.findings.append(f"**Social security, {c.code}:** {t.note}")
        elif not t.known and c.code != "US":
            d.findings.append(
                f"Whether a US–{c.code} totalization agreement exists is not "
                "in the table — see `lib/pf/status.py`. It decides whether "
                "contributions are duplicated and whether coverage periods "
                "combine."
            )

        for item in c.needs_professional_verification:
            d.findings.append(f"⚠️ **Verify with a professional:** {item}")

        p.destinations.append(d)

    # ── the inversion, stated once, at the top ──────────────────────────
    if p.any_inverts:
        p.findings.append(
            "**The conversion advice inverts.** `roth-conversion-window` is "
            "right for a household that stays: pay tax now at a low rate to "
            "buy tax-free growth. For a household moving to a destination that "
            "does not honour the wrapper, the same conversion pays a real, "
            "irreversible US tax bill to buy an exemption the destination will "
            "not grant. Read that skill's output as conditional on not moving."
        )
        p.findings.append(
            "**The mechanism is the timing, and it is what makes this worse "
            "than ordinary double taxation.** A traditional account is taxed "
            "by both countries in the *same* year the distribution is taken, "
            "so a foreign tax credit or treaty relief has something to offset. "
            "A conversion moves the US tax event years earlier, into a year "
            "with no foreign tax to credit against — and the destination's tax "
            "then lands in a year with no US tax to credit against. Neither "
            "relief mechanism can reach across the gap."
        )
        if p.conversion_tax_now is not None:
            p.findings.append(
                f"**{_money(p.conversion_tax_now)} of US tax per year** at "
                f"{p.conversion_tax_rate:.0%} on a "
                f"{_money(p.planned_conversion)} conversion. That payment "
                "cannot be undone — recharacterising a conversion was "
                "repealed — so it is the clearest thing in this report: a "
                "certain cost today against a benefit that depends on a "
                "contested foreign reading."
            )
        elif planned_conversion:
            p.findings.append(
                "A conversion is planned but the tax cost **cannot be "
                "determined** — no marginal rate is recorded. Set "
                "`assumptions.marginal_tax_rate`."
            )

    if p.any_unknown:
        p.findings.append(
            "**At least one destination is not in the table.** Absence here "
            "means nobody checked, not that the treatment is benign. The "
            f"countries that are encoded: {', '.join(countries_available())}."
        )

    p.findings.append(
        "**Take this to a cross-border tax professional.** That is a weaker "
        "output than the rest of this repository produces, and saying so is "
        "part of the deliverable: foreign treatment of US retirement accounts "
        "is contested, treaty-dependent, and changes. What this skill is for "
        "is making sure you arrive at that conversation knowing which question "
        "to ask — and knowing not to convert in the meantime."
    )
    return p


# ── geo arbitrage ───────────────────────────────────────────────────────────

#: Months in a plan year. A split-living arrangement whose legs do not add up
#: to twelve is missing a leg, and the blended burn understates the year.
MONTHS_IN_YEAR = 12.0
MONTH_TOLERANCE = 0.01

#: Turning a month split into a day count for residency tests. Approximate on
#: purpose — the output is a warning to go and count real days, never a
#: substitute for counting them.
DAYS_PER_MONTH = 30.44

#: Flag a residency day test as at risk within this margin. Travel plans slip
#: by more than three weeks routinely, and the tests have no tolerance.
DAY_TEST_MARGIN_DAYS = 21

#: Stress applied to the foreign-currency legs. The saving from a cheaper
#: country is denominated in a currency the household neither earns nor holds,
#: and a fifth is an ordinary decade for a major-to-emerging pair.
FX_STRESS = 0.20


@dataclass
class Leg:
    name: str
    country: str
    months: float
    monthly_spending: float
    #: True where costs are incurred in the household's home currency. False
    #: legs are the ones FX stress applies to.
    home_currency: bool = False

    @property
    def annual_cost(self) -> float:
        return self.months * self.monthly_spending

    @property
    def estimated_days(self) -> float:
        return self.months * DAYS_PER_MONTH


@dataclass
class GeoPlan:
    legs: list[Leg]
    fixed_annual: float
    blended_annual: float
    #: The most expensive leg extrapolated to a full year, plus fixed costs.
    #: What the household would spend not doing this.
    baseline_annual: float
    stressed_annual: float
    withdrawal_rate: float
    target: float
    baseline_target: float
    stressed_target: float
    years_to_target: float | None
    years_to_baseline: float | None
    findings: list[str] = field(default_factory=list)

    @property
    def annual_saving(self) -> float:
        return self.baseline_annual - self.blended_annual

    @property
    def target_reduction(self) -> float:
        return self.baseline_target - self.target

    @property
    def months_accounted(self) -> float:
        return sum(l.months for l in self.legs)

    @property
    def years_saved(self) -> float | None:
        if self.years_to_target is None or self.years_to_baseline is None:
            return None
        return self.years_to_baseline - self.years_to_target


def blend(legs: list[Leg], fixed_annual: float = 0.0) -> float:
    """Blended annual burn. Legs plus costs that do not move with location."""
    return sum(l.annual_cost for l in legs) + fixed_annual


def stressed(legs: list[Leg], fixed_annual: float = 0.0,
             fx_stress: float = FX_STRESS) -> float:
    """Blended burn with the non-home-currency legs uprated by the stress."""
    total = fixed_annual
    for l in legs:
        total += l.annual_cost * (1 + (0.0 if l.home_currency else fx_stress))
    return total


def _legs_from(rows: list[dict]) -> list[Leg]:
    out = []
    for row in rows or []:
        out.append(Leg(
            name=row.get("name") or row.get("country") or "leg",
            country=(row.get("country") or "").upper(),
            months=float(row.get("months_per_year") or 0),
            monthly_spending=float(row.get("monthly_spending") or 0),
            home_currency=bool(row.get("home_currency")),
        ))
    return out


def model(
    locations_raw: list[dict],
    *,
    assets: float,
    annual_savings: float,
    fixed_annual: float = 0.0,
    duplicate_housing: bool | None = None,
    withdrawal_rate: float = _ret.DEFAULT_WITHDRAWAL_RATE,
    real_return: float = _ret.DEFAULT_REAL_RETURN,
    fx_stress: float = FX_STRESS,
    savings_by_year: list[float] | None = None,
) -> GeoPlan:
    """Blended burn across a split-living arrangement, and the target it implies.

    The projection machinery is `retirement.py` — `target_for`, `years_to` —
    imported rather than reimplemented, so a location-adjusted target and an
    ordinary one cannot drift apart.
    """
    legs = _legs_from(locations_raw)
    blended = blend(legs, fixed_annual)
    stress = stressed(legs, fixed_annual, fx_stress)

    dearest = max(legs, key=lambda l: l.monthly_spending, default=None)
    baseline = ((dearest.monthly_spending * MONTHS_IN_YEAR + fixed_annual)
                if dearest else fixed_annual)

    target = _ret.target_for(blended, withdrawal_rate)
    baseline_target = _ret.target_for(baseline, withdrawal_rate)
    stress_target = _ret.target_for(stress, withdrawal_rate)

    p = GeoPlan(
        legs=legs, fixed_annual=fixed_annual,
        blended_annual=blended, baseline_annual=baseline,
        stressed_annual=stress, withdrawal_rate=withdrawal_rate,
        target=target, baseline_target=baseline_target,
        stressed_target=stress_target,
        years_to_target=_ret.years_to(
            target, assets, annual_savings, real_return,
            savings_by_year=savings_by_year),
        years_to_baseline=_ret.years_to(baseline_target, assets, annual_savings,
                                        real_return,
                                        savings_by_year=savings_by_year),
    )

    if not legs:
        p.findings.append(
            "**No locations recorded**, so there is nothing to blend.")
        return p

    gap = MONTHS_IN_YEAR - p.months_accounted
    if abs(gap) > MONTH_TOLERANCE:
        if gap > 0:
            cheap = min(l.monthly_spending for l in legs)
            dear = max(l.monthly_spending for l in legs)
            p.findings.append(
                f"⚠️ **The legs account for {p.months_accounted:.1f} months, "
                f"not twelve.** {gap:.1f} month(s) of living costs are "
                f"unaccounted for, so the blended burn below is understated by "
                f"somewhere between {_money(gap * cheap)} and "
                f"{_money(gap * dear)} a year. The model will not spread the "
                "gap across the legs for you — which leg it belongs to changes "
                "the answer, and only you know."
            )
        else:
            p.findings.append(
                f"⚠️ **The legs account for {p.months_accounted:.1f} months, "
                "more than a year.** Either a leg is double-counted or the "
                "plan is not a single year. The blend below overstates."
            )

    p.findings.append(
        f"**Every dollar off the annual burn takes "
        f"{1 / withdrawal_rate:.0f} dollars off the target.** The blended "
        f"{_money(blended)} against a full year at the dearest leg "
        f"({_money(baseline)}) saves {_money(p.annual_saving)} a year, which "
        f"cuts the portfolio target by **{_money(p.target_reduction)}**. That "
        "multiplier is why spending is the strongest lever in retirement "
        "planning and why location is the strongest lever on spending."
    )

    if p.years_saved is not None and p.years_saved > 0:
        p.findings.append(
            f"On the same assets and savings, that is **"
            f"{p.years_saved:.0f} year(s) earlier** — "
            f"{p.years_to_target:.0f} years to the blended target against "
            f"{p.years_to_baseline:.0f} to the full-cost one."
        )
    elif p.years_to_target is None:
        p.findings.append(
            "The blended target is **not reached** within the projection "
            "horizon at these assumptions. Location is not the binding "
            "constraint here; the plan does not close."
        )

    foreign = [l for l in legs if not l.home_currency]
    if foreign:
        p.findings.append(
            f"**The saving is denominated in a currency you neither earn nor "
            f"hold.** At a {fx_stress:.0%} adverse move on the "
            f"{', '.join(l.name for l in foreign)} leg(s), the blended burn "
            f"rises to {_money(stress)} and the target to "
            f"{_money(stress_target)} — giving back "
            f"{_money(stress_target - target)} of the "
            f"{_money(p.target_reduction)} the move bought. This is the "
            "weakest input in the model: everything else here is arithmetic "
            "on figures you supplied, and this is a guess about exchange rates "
            "over decades. Treat the stressed row as the planning figure."
        )
    else:
        p.findings.append(
            "No leg is marked as foreign-currency, so no FX stress has been "
            "applied. If any of these costs are actually incurred in another "
            "currency, set `home_currency: false` — the exchange rate is the "
            "largest uncertainty in an arrangement like this and leaving it "
            "out makes the plan look more certain than it is."
        )

    if duplicate_housing is None:
        p.findings.append(
            "**Whether housing is paid for in both places year-round is not "
            "recorded**, so it cannot be determined whether these monthly "
            "figures overlap. A split-living arrangement frequently pays rent "
            "or carrying costs in both locations for all twelve months while "
            "only occupying one, which can erase most of the saving above. "
            "Record `duplicate_housing` rather than letting the model assume "
            "the favourable case."
        )
    elif duplicate_housing:
        p.findings.append(
            "**Housing is paid in both locations year-round.** Confirm the "
            "monthly figures above each include the full-year carrying cost "
            "rather than only the months occupied — if they do not, the "
            "blended burn is understated by the whole of the vacant-period "
            "housing cost."
        )

    # ── the residency side-effect ───────────────────────────────────────
    for l in legs:
        c = country_for(l.country)
        if not c.known:
            if l.country and l.country != "US":
                p.findings.append(
                    f"**{l.name}: {l.country} is not in the country table**, "
                    "so its residency day test is unknown. Roughly "
                    f"{l.estimated_days:.0f} days a year is enough to matter "
                    "in many jurisdictions; find the threshold before "
                    "committing to the split."
                )
            continue
        for t in c.residency_tests:
            # Multi-year tests need a real travel history rather than one
            # year's split, and a precondition is not a test. Flagging either
            # produces noise that trains the reader to skip warnings.
            if t.window_years != 1 or not t.standalone:
                continue
            if l.estimated_days >= t.days:
                p.findings.append(
                    f"🚫 **{l.name}: roughly {l.estimated_days:.0f} days a "
                    f"year crosses {c.code}'s '{t.label}' test at {t.days} "
                    f"days.** {t.note} This arrangement makes you tax resident "
                    f"there, which brings worldwide income into scope and "
                    "changes every other answer in this repository. Count real "
                    "days from a travel log — this figure is months × "
                    f"{DAYS_PER_MONTH}, which is an estimate, not a count."
                )
            elif l.estimated_days >= t.days - DAY_TEST_MARGIN_DAYS:
                p.findings.append(
                    f"⚠️ **{l.name}: roughly {l.estimated_days:.0f} days a "
                    f"year is within {DAY_TEST_MARGIN_DAYS} days of {c.code}'s "
                    f"'{t.label}' threshold ({t.days}).** {t.note} A delayed "
                    "flight or an extended visit crosses it, and the tests "
                    "have no tolerance. Keep a contemporaneous travel log."
                )

    p.findings.append(
        "Every figure here is **real** — today's money — because it feeds "
        "`retirement.py`, which is real throughout. Local inflation in the "
        "cheaper location is the thing most likely to erode this over decades, "
        "and it is not modelled: a constant real cost differential is an "
        "assumption, not a finding."
    )
    p.findings.append(
        "**Healthcare is not in these numbers and is usually the largest "
        "single line.** Medicare does not travel — see "
        "`cross-border-healthcare` before treating the saving above as "
        "spendable."
    )
    return p


# ── Medicare abroad ─────────────────────────────────────────────────────────

#: Medicare does not pay for care received outside the United States. The
#: exceptions are narrow and situational, not a travel benefit.
MEDICARE_COVERS_ABROAD = False

#: `PART_B_PENALTY_PER_12M` and `PART_D_PENALTY_PER_MONTH` are imported at the
#: top of this module from `healthcare.py`, which owns them. They are not
#: redefined here.

#: Medigap foreign travel emergency benefit, on the plans that include it.
#: A lifetime cap — not an annual one — which is what makes it a holiday
#: benefit rather than expatriate cover.
MEDIGAP_FOREIGN_COINSURANCE = 0.80
MEDIGAP_FOREIGN_DEDUCTIBLE = 250
MEDIGAP_FOREIGN_LIFETIME_MAX = 50_000
MEDIGAP_FOREIGN_TRIP_DAYS = 60

#: Guaranteed-issue window for Medigap: months from Part B starting. Outside
#: it, a carrier can medically underwrite or decline — which is the trap
#: hiding behind the enrolment penalty.
MEDIGAP_OPEN_ENROLMENT_MONTHS = 6

#: When someone who dropped Part B can get it back.
GENERAL_ENROLMENT_WINDOW = "1 January – 31 March"


@dataclass
class PartBDecision:
    months_abroad: float
    standard_premium_monthly: float
    years_after_return: float | None
    will_return: bool | None
    #: Premiums paid for cover that cannot be used abroad.
    keep_cost: float
    #: Full 12-month periods without Part B.
    penalty_years: int
    penalty_rate: float
    penalty_monthly: float
    penalty_lifetime: float | None
    #: keep | drop | cannot_determine
    recommendation: str
    findings: list[str] = field(default_factory=list)


def part_b_penalty_rate(months_without: float) -> float:
    """10% for each *full* 12-month period. Partial periods do not count."""
    return PART_B_PENALTY_PER_12M * int(max(0.0, months_without) // 12)


def part_b_decision(
    *,
    months_abroad: float,
    standard_premium_monthly: float,
    will_return: bool | None,
    years_after_return: float | None = None,
) -> PartBDecision:
    """Keep paying Part B for cover you cannot use, or drop it and take the
    permanent penalty on the way back in.

    A real arithmetic decision with a real boundary: the keep cost is linear in
    time abroad, the penalty cost is the product of time abroad *and* years
    lived after returning. Long absences followed by long lives favour keeping;
    the reverse favours dropping.
    """
    keep = months_abroad * standard_premium_monthly
    rate = part_b_penalty_rate(months_abroad)
    penalty_monthly = standard_premium_monthly * rate
    lifetime = (penalty_monthly * 12 * years_after_return
                if years_after_return is not None else None)

    if will_return is False:
        rec = "drop"
    elif will_return is None or lifetime is None:
        rec = "cannot_determine"
    else:
        rec = "keep" if lifetime > keep else "drop"

    d = PartBDecision(
        months_abroad=months_abroad,
        standard_premium_monthly=standard_premium_monthly,
        years_after_return=years_after_return,
        will_return=will_return,
        keep_cost=keep,
        penalty_years=int(max(0.0, months_abroad) // 12),
        penalty_rate=rate,
        penalty_monthly=penalty_monthly,
        penalty_lifetime=lifetime,
        recommendation=rec,
    )

    d.findings.append(
        "**Medicare does not pay for care outside the United States.** The "
        "exceptions are narrow and situational — a foreign hospital nearer "
        "than a US one in an emergency, and transit between Alaska and the "
        "lower 48 — not a travel benefit. Keeping Part B while living abroad "
        "buys nothing usable; it buys the *right to come back without a "
        "penalty*, which is a different product and worth pricing as one."
    )

    if rate == 0 and months_abroad > 0:
        d.findings.append(
            f"At {months_abroad:.0f} months there is no full 12-month period "
            "without Part B, so no penalty would apply. The penalty counts "
            "full years only — an absence of eleven months is free and "
            "thirteen is not."
        )
    else:
        d.findings.append(
            f"**Dropping Part B for {months_abroad:.0f} months means "
            f"{d.penalty_years} full year(s) uncovered — a permanent "
            f"{rate:.0%} surcharge**, about "
            f"{_money(penalty_monthly)}/month at today's standard premium, "
            "for as long as you hold Part B thereafter. It does not expire "
            "and it is not forgiven on appeal for having been abroad."
        )

    if rec == "cannot_determine":
        d.findings.append(
            "**Whether you will return to the US is not recorded, and it "
            "decides this.** Never returning makes dropping free; returning "
            "makes it expensive. Both arms are priced below rather than one of "
            "them being assumed — an unknown intention is not the same as an "
            "intention to stay away."
        )
        if lifetime is not None:
            cheaper = "keeping" if lifetime > keep else "dropping"
            d.findings.append(
                f"**If you do return**, {cheaper} is cheaper on these "
                f"numbers: {_money(keep)} of premiums for unusable cover "
                f"against {_money(lifetime)} of permanent penalty over "
                f"{years_after_return:.0f} years back in the US. **If you do "
                "not**, dropping costs nothing. Record the intention and the "
                "report will pick one."
            )
    elif rec == "keep":
        d.findings.append(
            f"**Keeping it is cheaper on these numbers**: "
            f"{_money(keep)} of premiums for unusable cover against "
            f"{_money(lifetime)} of permanent penalty over "
            f"{years_after_return:.0f} years back in the US. The penalty "
            "compounds with longevity, which is the case you are insuring "
            "against anyway."
        )
    elif rec == "drop" and will_return is False:
        d.findings.append(
            "**On a stated intention never to return, dropping is right** — "
            "the penalty only bites on re-enrolment. But that intention is the "
            "weakest input in this report and the most consequential: people "
            "return for family, for care, and because a plan made at 65 is not "
            "the plan at 80. The penalty is permanent and the Medigap problem "
            "below is worse than the penalty."
        )
    elif rec == "drop":
        d.findings.append(
            f"**Dropping is cheaper on these numbers**: {_money(lifetime)} of "
            f"lifetime penalty against {_money(keep)} of premiums for cover "
            "that cannot be used. The margin is not large enough to ignore the "
            "non-price consequences below."
        )

    d.findings.append(
        f"**Re-enrolment is not on demand.** Someone who dropped Part B gets "
        f"back in during the General Enrolment Period ({GENERAL_ENROLMENT_WINDOW}), "
        "so a return in April can mean months uninsured. Living abroad is "
        "generally **not** creditable coverage and does not create a special "
        "enrolment period — the SEP exists for coverage from current "
        "employment, which a foreign retirement is not."
    )
    d.findings.append(
        f"**The Medigap consequence is worse than the penalty and gets less "
        f"attention.** Guaranteed issue runs for "
        f"{MEDIGAP_OPEN_ENROLMENT_MONTHS} months from Part B starting. Come "
        "back years later in poorer health and a carrier can medically "
        "underwrite or decline. The penalty is a known surcharge; being "
        "uninsurable for the supplement is not priceable at all."
    )
    d.findings.append(
        "**Premiums are income-related.** A Roth conversion raises modified "
        "AGI and raises the Part B premium two years later (IRMAA) — and the "
        "penalty is a percentage, so a higher base makes the surcharge larger "
        "too. See `roth-conversion-window` and `roth-portability-check`."
    )
    d.findings.append(
        "Premiums and penalties here are **nominal current-year figures you "
        "supplied**, not projected. The standard premium is asked for rather "
        "than hard-coded because it changes annually and a stale figure would "
        "go wrong silently."
    )
    return d


def medigap_notes(*, has_medigap: bool | None) -> list[str]:
    """The foreign-travel emergency benefit, and why it is not a plan."""
    out: list[str] = []
    if has_medigap is None:
        out.append(
            "**Whether a Medigap policy is held is not recorded.** It is the "
            "only part of traditional Medicare that pays anything abroad, so "
            "the question cannot be skipped."
        )
    elif not has_medigap:
        out.append(
            "**No Medigap policy**, so there is no foreign travel emergency "
            "benefit at all. Traditional Medicare alone pays nothing outside "
            "the US."
        )
    out.append(
        f"Where a Medigap plan includes the foreign travel emergency benefit, "
        f"it pays {MEDIGAP_FOREIGN_COINSURANCE:.0%} of emergency care after a "
        f"{_money(MEDIGAP_FOREIGN_DEDUCTIBLE)} deductible, only during the "
        f"first {MEDIGAP_FOREIGN_TRIP_DAYS} days of a trip, up to "
        f"**{_money(MEDIGAP_FOREIGN_LIFETIME_MAX)} — a lifetime maximum, not "
        "an annual one.** Not every plan letter includes it. Read together, "
        "those four limits describe a holiday benefit: one serious admission "
        "abroad exhausts the lifetime cap, and month five of a five-month stay "
        "is outside the trip window entirely. It is not expatriate cover and "
        "should never be planned around as though it were."
    )
    return out


def expat_cover_notes(*, premium_annual: float | None) -> list[str]:
    """What an expat private policy has to be checked for."""
    out: list[str] = []
    if premium_annual is None:
        out.append(
            "**No expatriate policy premium is recorded**, so the alternative "
            "cannot be priced against the Part B arithmetic above. Get a real "
            "quote at your actual age — this is the one input where a "
            "placeholder is badly misleading, because expat premiums rise "
            "steeply with age rather than smoothly."
        )
    else:
        out.append(
            f"Expatriate cover is recorded at {_money(premium_annual)}/year. "
            "Price it against the Part B keep cost above, but do not treat "
            "them as the same product — one covers you where you live, the "
            "other preserves your route back."
        )
    out.append(
        "**Check these four before relying on a private expat policy**: "
        "whether it is guaranteed renewable or can be declined at the next "
        "anniversary; whether it terminates or reprices sharply at an age cap; "
        "how pre-existing conditions are treated, which is where most claims "
        "fail; and whether it covers repatriation, which is the expensive "
        "event nobody budgets for."
    )
    out.append(
        "**A destination's public system may or may not admit you**, and on "
        "what terms is not in this repository's tables — residency status, "
        "contribution history and age limits all bear on it. Find out from the "
        "system itself rather than from an expatriate forum."
    )
    return out


def _money(x) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
