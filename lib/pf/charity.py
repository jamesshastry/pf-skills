"""Charitable giving: the same dollars, arranged so they cost less.

## Donating appreciated securities fixes two problems in one transaction

This is the idea the module exists to encode, and it leads every report.

Giving an appreciated long-term holding **in kind** to a public charity does
two things at once. The donor deducts the full fair market value, and **the
embedded capital gain is never realised by anyone** — the charity is exempt, so
the gain evaporates rather than transferring. Selling the same position and
donating the proceeds gives up the second half: the gain is realised, the tax
is paid, and less money reaches the charity for the same cost to the donor.

And because the security leaving the portfolio is usually the most appreciated
one, which in a concentrated household is usually the employer position, the
same transaction **reduces the concentration**. Two problems improved by one
action is rare enough in personal finance to be worth naming when it appears.
See `employer-concentration-risk` for the exposure itself; this module does not
re-derive it.

## Donating a loss position is strictly worse, always

The mirror image, and the error the excitement above produces. Donating a
holding worth less than its basis deducts the *value* and **forfeits the loss**
— nobody ever claims it. Sell it, claim the capital loss, donate the cash: same
amount to the charity, same deduction, plus a loss that offsets other gains.
There is no household for whom the in-kind version of this is better.

## The limits that decide whether a deduction is worth anything

Two of them, and they work in opposite directions:

**AGI percentage limits differ by what is given.** Cash to a public charity is
deductible to a higher share of AGI than appreciated capital-gain property is.
A large in-kind gift can exceed its limit in the year it is made — the excess
carries forward, but a carryforward is worth less than a deduction now and is
lost entirely if it expires unused.

**The standard deduction is a floor, not a subtraction.** A household whose
itemizable total sits below it gets *no* benefit from ordinary annual giving.
Bunching several years of giving into one — typically through a donor-advised
fund, which separates the deductible gift from the grant to the charity —
clears the floor in one year and takes the standard deduction in the others.
That is pure arithmetic and the module does it.

## Basis, stated

Nominal dollars, federal tax only, marginal-rate valuation of deductions.
State charitable treatment varies and is out of scope. The standard deduction,
the QCD limit and the marginal rate are **read from the facts file**: all three
are indexed or personal, and a figure encoded here would go stale silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .concentration import MAX_SINGLE_NAME_SHARE

# ── statutory limits ────────────────────────────────────────────────────────

#: §170(b)(1)(A) — cash contributions to a public charity, as a share of AGI.
CASH_AGI_LIMIT = 0.60

#: §170(b)(1)(C) — long-term capital gain property to a public charity, at
#: fair market value. The lower limit is the price of the FMV deduction.
APPRECIATED_AGI_LIMIT = 0.30

#: §170(b)(1)(C)(iii) — electing to deduct basis instead of FMV raises the
#: limit. Almost never worth it, and in the table so the trade-off is visible.
APPRECIATED_BASIS_ELECTION_LIMIT = 0.50

#: §170(d) — unused deduction carries forward this many years, then expires.
CARRYFORWARD_YEARS = 5

#: §1222 — the long-term holding period. Below it, a gift of appreciated
#: property is deductible at **basis**, not fair market value, which removes
#: most of the point.
LONG_TERM_DAYS = 366

#: §408(d)(8) — the age at which a qualified charitable distribution becomes
#: available. Note this is *not* the RMD age and has not moved with it.
QCD_AGE = 70.5

CHARITY_SOURCE = (
    "IRC §170(b) (AGI percentage limits); §170(d) (carryforward); "
    "§170(e) (reduction for short-term and ordinary-income property); "
    "§408(d)(8) (qualified charitable distributions); §1222 (holding period)"
)
CHARITY_VERIFIED = "unverified — check against irs.gov Publication 526"


# ── gifts of securities ─────────────────────────────────────────────────────


@dataclass
class GiftLine:
    name: str
    value: float
    basis: float | None
    long_term: bool | None
    #: Share of investable assets this position represents, where known.
    portfolio_share: float | None = None
    #: Tax avoided by giving in kind rather than selling first.
    gain_tax_avoided: float | None = None
    #: What the donor may deduct.
    deductible: float | None = None
    recommendation: str = ""
    detail: str = ""

    @property
    def gain(self) -> float | None:
        if self.basis is None:
            return None
        return self.value - self.basis

    @property
    def at_a_loss(self) -> bool:
        return self.gain is not None and self.gain < 0


@dataclass
class GiftReview:
    lines: list[GiftLine] = field(default_factory=list)
    gain_rate: float | None = None
    findings: list[str] = field(default_factory=list)

    @property
    def total_avoided(self) -> float:
        return sum(l.gain_tax_avoided or 0.0 for l in self.lines)

    @property
    def best(self) -> GiftLine | None:
        scored = [l for l in self.lines if l.gain_tax_avoided is not None]
        if not scored:
            return None
        return max(scored, key=lambda l: l.gain_tax_avoided or 0.0)


def review_gifts(
    holdings: list[dict],
    *,
    ltcg_rate: float | None,
    niit_rate: float | None = None,
    investable: float | None = None,
) -> GiftReview:
    """Rank candidate securities for an in-kind gift, and reject the wrong ones.

    `ltcg_rate` is required to value the avoided gain and is not defaulted —
    the rate is 0%, 15% or 20% plus NIIT depending on the household, and
    picking the middle one produces a figure that is wrong for two-thirds of
    readers with no indication which.
    """
    rate = None if ltcg_rate is None else ltcg_rate + (niit_rate or 0.0)
    r = GiftReview(gain_rate=rate)

    for h in holdings or []:
        value = float(h.get("value") or 0)
        basis = h.get("basis")
        basis = None if basis is None else float(basis)
        days = h.get("held_days")
        long_term = None if days is None else int(days) >= LONG_TERM_DAYS
        share = (value / investable) if investable else None
        line = GiftLine(name=h.get("name") or "holding", value=value,
                        basis=basis, long_term=long_term, portfolio_share=share)

        if basis is None:
            line.recommendation = "cannot assess"
            line.detail = (
                "No cost basis recorded, so whether this is an appreciated "
                "gift or a forfeited loss cannot be told apart — and those are "
                "opposite recommendations. The broker has it.")
        elif line.at_a_loss:
            line.deductible = value
            line.recommendation = "**sell first, donate cash**"
            line.detail = (
                f"Worth {_money(value)} against {_money(basis)} of basis. "
                f"Donating it in kind deducts {_money(value)} and **forfeits "
                f"the {_money(-(line.gain or 0))} loss permanently** — no one "
                f"ever claims it. Sell, book the loss against other gains, "
                f"donate the proceeds: the charity receives the same amount, "
                f"the deduction is the same, and the loss survives.")
        elif long_term is False:
            line.deductible = basis
            line.recommendation = "wait, or give something else"
            line.detail = (
                f"Held under a year, so the deduction is limited to **basis** "
                f"({_money(basis)}), not the {_money(value)} it is worth. That "
                f"removes most of the reason to give it in kind. Holding to "
                f"{LONG_TERM_DAYS} days converts the deduction to full value; "
                f"a long-term lot of the same security is the better gift "
                f"today.")
        else:
            line.deductible = value
            if rate is not None:
                line.gain_tax_avoided = max(0.0, (line.gain or 0.0)) * rate
            unknown_term = "" if long_term else (
                " Holding period is not recorded — confirm the lot is over a "
                "year old, because a short-term lot is deductible at basis "
                "only.")
            line.detail = (
                f"{_money(line.gain)} of unrealised gain on {_money(value)}. "
                f"Given in kind, the full {_money(value)} is deductible and "
                f"the gain is never realised by anyone." + unknown_term)
            line.recommendation = "**give in kind**"
        r.lines.append(line)

    if rate is None:
        r.findings.append(
            "**No capital gains rate supplied, so the avoided tax is not "
            "valued.** Set `assumptions.ltcg_rate` and, where it applies, "
            "`assumptions.niit_rate`. The rate is 0%, 15% or 20% depending on "
            "the household, so assuming one would be wrong for most readers "
            "with nothing in the output to say which.")
    elif r.total_avoided > 0:
        r.findings.append(
            f"**{_money(r.total_avoided)} of capital gains tax avoided** if "
            f"the appreciated positions above are given in kind rather than "
            f"sold first. This is money that reaches the charity instead of "
            f"the IRS at no additional cost to the donor — the deduction is "
            f"the same either way, so the avoided gain is pure gain.")

    concentrated = [l for l in r.lines
                    if l.portfolio_share is not None
                    and l.portfolio_share > MAX_SINGLE_NAME_SHARE
                    and not l.at_a_loss and l.gain and l.gain > 0]
    if concentrated:
        names = ", ".join(l.name for l in concentrated)
        r.findings.append(
            f"**{names} is both the best gift and the concentration problem.** "
            f"Giving it away trims the position without a taxable sale, which "
            f"is the rare move that improves two things at once: the "
            f"concentration falls and the gain never gets realised. Size the "
            f"gift against `employer-concentration-risk`, not against this "
            f"report — charitable intent sets the ceiling here, and a gift "
            f"large enough to fix a concentration problem is a gift larger "
            f"than most households mean to make.")

    r.findings.append(
        "**Transfer the shares, do not sell and wire the cash.** The whole "
        "benefit sits in the security arriving at the charity intact. A sale "
        "the day before, however briefly, realises the gain and there is no "
        "way back from it. Most donor-advised funds accept in-kind transfers; "
        "many small charities cannot, which is one of the reasons a DAF exists.")
    return r


# ── bunching ────────────────────────────────────────────────────────────────


@dataclass
class BunchPlan:
    standard_deduction: float
    other_itemized: float
    annual_gift: float
    marginal_rate: float
    years: int
    #: Total deductions taken over `years`, giving annually.
    annual_total: float = 0.0
    #: Total taken bunching `years` of giving into one.
    bunched_total: float = 0.0
    findings: list[str] = field(default_factory=list)

    @property
    def extra_deduction(self) -> float:
        return self.bunched_total - self.annual_total

    @property
    def benefit(self) -> float:
        return self.extra_deduction * self.marginal_rate

    @property
    def worth_it(self) -> bool:
        return self.benefit > 0


def bunch(
    *,
    standard_deduction: float,
    other_itemized: float,
    annual_gift: float,
    marginal_rate: float,
    years: int = 2,
) -> BunchPlan:
    """Compare giving annually against bunching `years` of giving into one.

    The comparison is on **total deductions taken**, not on the itemized total
    in the bunch year. A household that already itemizes comfortably gets
    nothing from bunching, and reporting the bunch-year itemized figure would
    make it look like it did.
    """
    p = BunchPlan(standard_deduction=standard_deduction,
                  other_itemized=other_itemized, annual_gift=annual_gift,
                  marginal_rate=marginal_rate, years=years)

    # In a year with no gift the household still takes the better of the
    # standard deduction and its other itemizable deductions. Using the
    # standard deduction there made bunching look actively harmful for a
    # household that itemizes comfortably — it is merely useless.
    off_year = max(standard_deduction, other_itemized)
    p.annual_total = years * max(standard_deduction, other_itemized + annual_gift)
    p.bunched_total = (max(standard_deduction, other_itemized + annual_gift * years)
                       + (years - 1) * off_year)

    if p.worth_it:
        p.findings.append(
            f"**Bunching {years} years of giving into one is worth "
            f"{_money(p.benefit)}** at a {marginal_rate:.0%} marginal rate — "
            f"{_money(p.extra_deduction)} of additional deduction over the "
            f"{years}-year window. Giving {_money(annual_gift)} a year against "
            f"a {_money(standard_deduction)} standard deduction wastes most of "
            f"it: the gift has to clear the floor before it is worth anything, "
            f"and annually it does not.")
        p.findings.append(
            "**A donor-advised fund separates the deduction from the grant.** "
            "Fund it in the bunch year, take the deduction that year, and "
            "grant to the charities on the same schedule as before. The "
            "charity's cash flow does not have to absorb the bunching — which "
            "is the objection that stops most households doing it.")
    else:
        p.findings.append(
            f"**Bunching gains nothing here.** Itemizable deductions of "
            f"{_money(other_itemized)} plus {_money(annual_gift)} of giving "
            f"already clear the {_money(standard_deduction)} standard "
            f"deduction every year, so every dollar given is already "
            f"deductible. Bunching only helps a household sitting below the "
            f"floor.")
    return p


def best_bunch(
    *,
    standard_deduction: float,
    other_itemized: float,
    annual_gift: float,
    marginal_rate: float,
    max_years: int = 5,
) -> BunchPlan:
    """The bunching window with the largest benefit, up to `max_years`.

    Capped at `CARRYFORWARD_YEARS` in effect: bunching more years than the
    carryforward window risks a deduction that expires before it is used.
    """
    plans = [bunch(standard_deduction=standard_deduction,
                   other_itemized=other_itemized, annual_gift=annual_gift,
                   marginal_rate=marginal_rate, years=n)
             for n in range(2, min(max_years, CARRYFORWARD_YEARS) + 1)]
    return max(plans, key=lambda p: p.benefit)


# ── AGI limits ──────────────────────────────────────────────────────────────


@dataclass
class LimitCheck:
    agi: float
    cash_gift: float
    appreciated_gift: float
    findings: list[str] = field(default_factory=list)

    @property
    def cash_room(self) -> float:
        return self.agi * CASH_AGI_LIMIT

    @property
    def appreciated_room(self) -> float:
        return self.agi * APPRECIATED_AGI_LIMIT

    @property
    def appreciated_excess(self) -> float:
        return max(0.0, self.appreciated_gift - self.appreciated_room)

    @property
    def cash_excess(self) -> float:
        return max(0.0, self.cash_gift - self.cash_room)


def check_limits(*, agi: float, cash_gift: float = 0.0,
                 appreciated_gift: float = 0.0) -> LimitCheck:
    """Whether the planned gifts fit inside their AGI percentage limits.

    The two limits differ, which is the part that surprises people mid-plan:
    a bunched in-kind gift sized against the cash limit overshoots the
    appreciated-property limit by half.
    """
    c = LimitCheck(agi=agi, cash_gift=cash_gift, appreciated_gift=appreciated_gift)

    c.findings.append(
        f"Against {_money(agi)} of AGI: up to {_money(c.cash_room)} of cash "
        f"({CASH_AGI_LIMIT:.0%}) and {_money(c.appreciated_room)} of "
        f"appreciated property at fair market value "
        f"({APPRECIATED_AGI_LIMIT:.0%}) are deductible this year. **The two "
        f"limits are different**, and a bunched in-kind gift sized against the "
        f"cash limit overshoots by half.")

    if c.appreciated_excess:
        c.findings.append(
            f"**{_money(c.appreciated_excess)} of the appreciated gift exceeds "
            f"the {APPRECIATED_AGI_LIMIT:.0%} limit.** It carries forward "
            f"{CARRYFORWARD_YEARS} years and then expires unused. A "
            f"carryforward is worth less than a deduction now and is worth "
            f"nothing at all if income falls in the years it has to be "
            f"absorbed — splitting the gift across two tax years is usually "
            f"better than relying on it.")
        c.findings.append(
            f"Electing to deduct **basis** instead of fair market value raises "
            f"the limit to {APPRECIATED_BASIS_ELECTION_LIMIT:.0%}. It is "
            f"almost never worth it: giving up the appreciation in the "
            f"deduction costs more than the extra room is worth unless the "
            f"position is barely appreciated, in which case there was little "
            f"reason to give it in kind.")
    if c.cash_excess:
        c.findings.append(
            f"**{_money(c.cash_excess)} of the cash gift exceeds the "
            f"{CASH_AGI_LIMIT:.0%} limit** and carries forward "
            f"{CARRYFORWARD_YEARS} years.")
    return c


# ── qualified charitable distributions ──────────────────────────────────────


@dataclass
class QCDCheck:
    age: float | None
    eligible: bool
    limit: float | None
    findings: list[str] = field(default_factory=list)


def qcd(*, age: float | None, annual_limit: float | None = None,
        rmd_applies: bool | None = None) -> QCDCheck:
    """Whether a qualified charitable distribution is available yet.

    `annual_limit` is indexed and comes from the facts file. The age is not
    indexed and is encoded — and it is **not** the RMD age, which has moved
    twice while this one has not.
    """
    c = QCDCheck(age=age, eligible=bool(age is not None and age >= QCD_AGE),
                 limit=annual_limit)

    if age is None:
        c.findings.append(
            "**No age recorded, so QCD eligibility cannot be established.** "
            "It turns on a single number.")
        return c

    if not c.eligible:
        c.findings.append(
            f"**Not yet eligible** — a QCD requires age {QCD_AGE}, and the "
            f"oldest recorded adult is {age:.0f}. Worth knowing about early: "
            f"it becomes the most efficient way to give for a household that "
            f"takes the standard deduction, because the distribution never "
            f"enters AGI at all.")
        return c

    c.findings.append(
        f"**Eligible.** A qualified charitable distribution goes directly from "
        f"an IRA to the charity and **never enters AGI** — which beats a "
        f"deduction, because AGI drives Medicare IRMAA surcharges, the "
        f"taxability of Social Security, and every phase-out in the code. A "
        f"household taking the standard deduction gets no benefit from "
        f"ordinary giving at all, and full benefit from this.")
    if annual_limit is not None:
        c.findings.append(
            f"Up to {_money(annual_limit)} per person per year, indexed. The "
            f"limit is per person, so a married couple with separate IRAs has "
            f"two of them.")
    else:
        c.findings.append(
            "**The annual limit is not recorded.** It is indexed and moves "
            "most years, so it is asked for rather than encoded here — set "
            "`assumptions.qcd_annual_limit` from the current IRS figure.")
    if rmd_applies:
        c.findings.append(
            "**A QCD counts toward the required minimum distribution**, which "
            "is the combination worth planning around: the RMD is satisfied, "
            "the charity is funded, and none of it shows up in income. Make "
            "the QCD **before** taking any other distribution for the year — "
            "the first dollars out of the IRA are the ones that count toward "
            "the RMD, and a distribution already taken cannot be undone.")
    c.findings.append(
        f"The QCD age is {QCD_AGE} and has not moved with the RMD age. They "
        f"are different numbers and the gap between them is usable — several "
        f"years in which giving from the IRA is available before it is "
        f"required.")
    return c


def _money(x) -> str:
    if x is None:
        return "not recorded"
    return f"${x:,.0f}"
