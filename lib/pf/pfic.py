"""Passive foreign investment companies: divest, or comply and pay.

## The decision is divest-or-comply, not which election

The natural framing is §1291 versus QEF versus mark-to-market. That is the
right *analysis* and the wrong *decision*, because for a retail holder the
answer is usually neither election:

- **QEF (§1295) requires a PFIC Annual Information Statement** from the fund.
  Most non-US retail funds do not produce one, because their US investors are
  a rounding error and the statement exists solely for US tax purposes.
- **Mark-to-market (§1296) requires marketable stock** — regularly traded on a
  qualified exchange. A non-listed open-ended fund is not that.

Both are frequently unavailable, which leaves **§1291 by default** — and §1291
by default is the case for selling. So the regime comparison is an *input*
here. The output is a comparison of the ongoing annual compliance cost (Form
8621 per fund, per year, plus the CPA fee and the punitive rate differential)
against the one-off cost of getting out.

`quant-platform/docs/INDIA_PORTFOLIO_GUIDE.md` reaches the same conclusion for
Indian mutual funds, with a compliance-cost table. This module quantifies what
that guide argues qualitatively; it is not restated here.

## The §1291 interest charge, and why it is computed rather than described

An excess distribution — or the entire gain on disposition — is allocated
pro-rata **across every day of the holding period**. The slice landing in each
prior year is taxed at **that year's highest marginal rate**, whatever the
holder's actual bracket was, and then carries a compound interest charge at the
IRS underpayment rate from that year's return due date to this one's. On a long
hold the interest can exceed the tax, which is precisely the part nobody
intuits, and the reason it is worth computing instead of warning about.

## The rate series is supplied, never encoded

The calculation needs **the top marginal rate for every year of the holding
period and the underpayment rate for every quarter of it.** A fund bought in
2005 needs eighty-odd quarterly rates. Encoding that series from memory would
be a long list of numbers in which each wrong entry silently corrupts a dollar
figure someone may act on — so the series comes from the facts file, on exactly
the same terms as `assumptions.cash_benchmark_apr`. Asked for, never fetched.

If the series is incomplete the module reports the **shape** of the exposure —
holding period, regime available, what drives the charge — and refuses the
figure. It never partially computes across the years it happens to have.

## Basis, stated

Every figure is **nominal US dollars, federal tax only**. State tax, NIIT and
foreign tax credits are out of scope. Interest is compounded quarterly from the
supplied quarterly rates; §6622 compounds daily, so the result is an estimate
that runs slightly low, and it is an estimate of the *size of a problem*, not a
number to enter on a form.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

#: Form 8621 is required **per fund, per year** — not per household and not per
#: account. Five funds in one brokerage account is five forms.
FORMS_PER_FUND_PER_YEAR = 1

#: §6622 compounds the underpayment interest daily. Quarterly compounding off
#: the quarterly rate is the most that supplied quarterly data supports, and it
#: understates slightly — stated rather than silently absorbed.
COMPOUNDING_PERIODS_PER_YEAR = 4

#: Interest runs from the unextended due date of each prior year's return to
#: the unextended due date of the disposition year's return. April 15 is used
#: for every year; weekend and holiday shifts move it by days, not months.
RETURN_DUE_MONTH = 4
RETURN_DUE_DAY = 15

#: Past this holding period the interest component routinely exceeds the tax
#: component, which inverts the intuition that a long hold is the safe one.
#: Used to decide when to say so, not to change any arithmetic.
LONG_HOLD_YEARS = 10

PFIC_SOURCE = (
    "IRC §1291 (excess distribution and interest charge); §1295 (QEF); "
    "§1296 (mark-to-market); §6621/§6622 (underpayment rate, compounding); "
    "Form 8621 instructions"
)
PFIC_VERIFIED = "unverified — check against irs.gov"

#: Regimes, in the order a holder would prefer them.
QEF = "QEF (§1295)"
MTM = "mark-to-market (§1296)"
DEFAULT_1291 = "§1291 default"


# ── which regime is actually available ──────────────────────────────────────


@dataclass(frozen=True)
class RegimeAvailability:
    """What the fund's own facts permit. Not what the holder would prefer."""

    qef: bool | None
    mtm: bool | None
    reasons: tuple[str, ...] = ()

    @property
    def regime(self) -> str:
        if self.qef:
            return QEF
        if self.mtm:
            return MTM
        return DEFAULT_1291

    @property
    def determinable(self) -> bool:
        """Both inputs answered. `None` on either means nobody asked the fund."""
        return self.qef is not None and self.mtm is not None


def regimes_for(fund: dict) -> RegimeAvailability:
    """Read regime availability off one holding.

    `null` is not `false`. A fund whose PFIC Annual Information Statement
    nobody has asked about is recorded as unknown, and the unknown is the
    finding — asking the fund administrator is a one-email task with a large
    payoff, and assuming the answer in either direction is the error.
    """
    qef = fund.get("qef_statement_available")
    mtm = fund.get("marketable_on_qualified_exchange")
    reasons: list[str] = []

    if qef is None:
        reasons.append(
            "**QEF availability unknown.** A QEF election needs a PFIC Annual "
            "Information Statement from the fund; most non-US retail funds do "
            "not issue one, because their US investors are a rounding error. "
            "Ask the administrator in writing — the answer is usually no, and "
            "a documented no is what supports the decision to sell.")
    elif not qef:
        reasons.append(
            "**No PFIC Annual Information Statement, so QEF is unavailable.** "
            "This is the common case and it is the fund's decision, not the "
            "holder's — there is nothing to elect.")
    else:
        reasons.append(
            "**QEF is available.** Income is picked up annually as it is "
            "earned, at ordinary and capital rates, with no interest charge. "
            "This materially changes the comparison below and the election "
            "must be made for the first year of the holding period to be fully "
            "effective; a late election leaves the §1291 taint in place until "
            "purged.")

    if mtm is None:
        reasons.append(
            "**Mark-to-market availability unknown.** §1296 needs *marketable "
            "stock* — regularly traded on a qualified exchange. An open-ended "
            "fund that transacts at NAV is generally not that, whatever its "
            "liquidity feels like.")
    elif not mtm:
        reasons.append(
            "**Not marketable stock on a qualified exchange, so §1296 is "
            "unavailable.**")
    else:
        reasons.append(
            "**Mark-to-market is available.** Gains are ordinary income each "
            "year with no interest charge, losses are deductible only to the "
            "extent of prior mark-to-market gains, and the election does not "
            "retroactively clear a §1291 holding period.")

    return RegimeAvailability(qef=qef, mtm=mtm, reasons=tuple(reasons))


# ── the §1291 allocation ────────────────────────────────────────────────────


@dataclass
class YearSlice:
    year: int
    days: int
    amount: float
    #: That year's highest marginal rate — not the holder's bracket.
    top_rate: float | None = None
    tax: float | None = None
    interest: float | None = None
    #: The disposition year (and any pre-PFIC years) are taxed as ordinary
    #: income in the current year with no interest charge.
    current_year: bool = False

    @property
    def total(self) -> float | None:
        if self.tax is None:
            return None
        return self.tax + (self.interest or 0.0)


def allocate(amount: float, *, acquired: _dt.date, disposed: _dt.date) -> list[YearSlice]:
    """Spread `amount` pro-rata across every day held, grouped by tax year.

    Pro-rata by days, which is what §1291(a)(1)(A) requires. The disposition
    year gets its own slice and is flagged: it is taxed in the current year at
    current rates with no interest, and treating it like a prior year would
    invent an interest charge that does not exist.
    """
    if disposed < acquired:
        raise ValueError("disposed before acquired")
    total_days = (disposed - acquired).days + 1
    slices: list[YearSlice] = []
    for year in range(acquired.year, disposed.year + 1):
        start = max(acquired, _dt.date(year, 1, 1))
        end = min(disposed, _dt.date(year, 12, 31))
        days = (end - start).days + 1
        slices.append(YearSlice(
            year=year,
            days=days,
            amount=amount * days / total_days,
            current_year=(year == disposed.year),
        ))
    return slices


@dataclass
class RateSeries:
    """Top marginal rate by year and underpayment rate by quarter.

    Both come from the facts file. Neither is defaulted, and a gap is reported
    rather than interpolated: interpolating a tax rate produces a plausible
    number with no authority behind it, which is the worst kind.
    """

    top_marginal: dict[int, float] = field(default_factory=dict)
    #: Keyed "2005Q2". Annual-equivalent rate, as the IRS quotes it.
    underpayment: dict[str, float] = field(default_factory=dict)

    @staticmethod
    def from_facts(block: dict | None) -> "RateSeries":
        block = block or {}
        top = {int(k): float(v)
               for k, v in (block.get("top_marginal_rate") or {}).items()}
        under = {str(k).upper(): float(v)
                 for k, v in (block.get("underpayment_rate") or {}).items()}
        return RateSeries(top_marginal=top, underpayment=under)

    def missing_for(self, slices: list[YearSlice], *, disposed: _dt.date) -> list[str]:
        """Every rate the charge needs and does not have, named exactly."""
        need: list[str] = []
        for s in slices:
            if s.year not in self.top_marginal:
                need.append(f"top_marginal_rate.{s.year}")
        for q in _quarters_needed(slices, disposed=disposed):
            if q not in self.underpayment:
                need.append(f"underpayment_rate.{q}")
        return need


def _quarter_key(d: _dt.date) -> str:
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def _quarters_between(start: _dt.date, end: _dt.date) -> list[str]:
    keys: list[str] = []
    y, q = start.year, (start.month - 1) // 3 + 1
    ey, eq = end.year, (end.month - 1) // 3 + 1
    while (y, q) < (ey, eq):
        keys.append(f"{y}Q{q}")
        q += 1
        if q > 4:
            y, q = y + 1, 1
    return keys


def _due(year: int) -> _dt.date:
    return _dt.date(year + 1, RETURN_DUE_MONTH, RETURN_DUE_DAY)


def _quarters_needed(slices: list[YearSlice], *, disposed: _dt.date) -> list[str]:
    end = _due(disposed.year)
    need: list[str] = []
    for s in slices:
        if s.current_year:
            continue
        for k in _quarters_between(_due(s.year), end):
            if k not in need:
                need.append(k)
    return need


@dataclass
class Charge:
    """A §1291 excess-distribution computation, or an explanation of why not."""

    amount: float
    acquired: _dt.date
    disposed: _dt.date
    slices: list[YearSlice] = field(default_factory=list)
    missing_rates: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    @property
    def holding_years(self) -> float:
        return ((self.disposed - self.acquired).days + 1) / 365.25

    @property
    def computable(self) -> bool:
        return not self.missing_rates

    @property
    def tax(self) -> float | None:
        if not self.computable:
            return None
        return sum(s.tax or 0.0 for s in self.slices)

    @property
    def interest(self) -> float | None:
        if not self.computable:
            return None
        return sum(s.interest or 0.0 for s in self.slices)

    @property
    def total(self) -> float | None:
        if not self.computable:
            return None
        return (self.tax or 0.0) + (self.interest or 0.0)

    @property
    def effective_rate(self) -> float | None:
        if not self.computable or not self.amount:
            return None
        return (self.total or 0.0) / self.amount

    @property
    def interest_exceeds_tax(self) -> bool:
        return bool(self.computable and (self.interest or 0) > (self.tax or 0))


def compute_charge(
    amount: float,
    *,
    acquired: _dt.date,
    disposed: _dt.date,
    rates: RateSeries,
) -> Charge:
    """The §1291 charge on an excess distribution or a disposition gain.

    Refuses wholesale on any missing rate. A charge computed across the years
    the series happens to cover is not a smaller charge — it is the same charge
    reported too low, and nothing in the output would say so.
    """
    c = Charge(amount=amount, acquired=acquired, disposed=disposed,
               slices=allocate(amount, acquired=acquired, disposed=disposed))
    c.missing_rates = rates.missing_for(c.slices, disposed=disposed)

    if c.missing_rates:
        c.findings.append(
            f"**The charge cannot be computed: {len(c.missing_rates)} rate(s) "
            f"are missing from `assumptions.pfic_rates`.** The allocation "
            f"itself is shown below, so the *shape* of the exposure is visible "
            f"— but no dollar figure is produced, because a charge computed "
            f"across only the years the series happens to cover reads as a "
            f"smaller charge rather than an incomplete one. These rates are "
            f"asked for rather than encoded: eighty-odd quarterly figures "
            f"transcribed from memory is eighty-odd chances to corrupt a "
            f"number someone acts on. Source: IRS Rev. Ruls. on the §6621 "
            f"underpayment rate, and the annual rate schedules.")
        return c

    end = _due(disposed.year)
    for s in c.slices:
        s.top_rate = rates.top_marginal[s.year]
        s.tax = s.amount * s.top_rate
        if s.current_year:
            s.interest = 0.0
            continue
        factor = 1.0
        for q in _quarters_between(_due(s.year), end):
            factor *= 1 + rates.underpayment[q] / COMPOUNDING_PERIODS_PER_YEAR
        s.interest = s.tax * (factor - 1)

    c.findings.append(
        f"**{_money(c.total)} on {_money(amount)}** — an effective "
        f"{c.effective_rate:.1%}, of which {_money(c.tax)} is tax and "
        f"{_money(c.interest)} is interest. The gain was allocated across "
        f"{len(c.slices)} tax year(s) and each prior year's slice taxed at "
        f"**that year's highest marginal rate**, not the holder's bracket, "
        f"then compounded forward at the underpayment rate.")

    if c.interest_exceeds_tax:
        c.findings.append(
            f"**The interest exceeds the tax** ({_money(c.interest)} against "
            f"{_money(c.tax)}). This is the part that is never intuited, and "
            f"it is why a long-held PFIC is the expensive case rather than the "
            f"safe one: the charge grows with the holding period whether or "
            f"not the fund does.")
    elif c.holding_years >= LONG_HOLD_YEARS:
        c.findings.append(
            f"Held {c.holding_years:.0f} years. Past roughly "
            f"{LONG_HOLD_YEARS} the interest component usually overtakes the "
            f"tax; it has not here, which is worth confirming against the "
            f"underpayment series you supplied before relying on it.")

    c.findings.append(
        "Interest is compounded quarterly from the quarterly rates supplied. "
        "§6622 compounds daily, so this runs slightly low. It is an estimate "
        "of the size of a problem, not a figure to enter on a Form 8621.")
    return c


# ── divest or comply ────────────────────────────────────────────────────────


@dataclass
class FundLine:
    name: str
    value: float | None
    basis: float | None
    acquired: _dt.date | None
    availability: RegimeAvailability

    @property
    def gain(self) -> float | None:
        if self.value is None or self.basis is None:
            return None
        return self.value - self.basis


@dataclass
class Decision:
    funds: list[FundLine] = field(default_factory=list)
    charge: Charge | None = None
    #: Annual cost of staying compliant, from the facts file.
    annual_compliance: float | None = None
    #: Years of compliance that cost the same as getting out today.
    breakeven_years: float | None = None
    findings: list[str] = field(default_factory=list)

    @property
    def forms_per_year(self) -> int:
        return len(self.funds) * FORMS_PER_FUND_PER_YEAR

    @property
    def any_election_available(self) -> bool:
        return any(f.availability.regime != DEFAULT_1291 for f in self.funds)


def divest_or_comply(
    funds: list[dict],
    *,
    rates: RateSeries,
    as_of: _dt.date,
    annual_cost_per_form: float | None = None,
    ltcg_rate: float | None = None,
) -> Decision:
    """Compare ongoing compliance against the one-off cost of getting out.

    `annual_cost_per_form` is the CPA fee for one Form 8621 for one fund for
    one year. It is a market price, not a statute, so it comes from the facts
    file — and when it is absent the comparison is inverted and the *breakeven
    fee* is reported instead, which needs no assumption at all.
    """
    d = Decision()
    for f in funds or []:
        acq = _as_date(f.get("acquired"))
        d.funds.append(FundLine(
            name=f.get("name") or "fund",
            value=_num(f.get("value")),
            basis=_num(f.get("basis")),
            acquired=acq,
            availability=regimes_for(f),
        ))

    if not d.funds:
        d.findings.append(
            "**No PFIC holdings recorded.** If there are none, record "
            "`pfic_holdings: []` so the answer is checked rather than absent. "
            "A non-US mutual fund, ETF, unit trust or investment-linked "
            "insurance policy is a PFIC by default — including one held inside "
            "a foreign brokerage you think of as a savings account.")
        return d

    # The charge is computed on the aggregate gain of the funds that have
    # enough recorded to place them, using the earliest acquisition. Earliest
    # rather than an average, because the longest holding period is the one
    # that drives the interest, and an average would flatter the answer.
    priced = [f for f in d.funds if f.gain is not None and f.acquired is not None]
    if priced:
        total_gain = sum(f.gain or 0.0 for f in priced)
        earliest = min(f.acquired for f in priced if f.acquired)
        if total_gain > 0:
            d.charge = compute_charge(total_gain, acquired=earliest,
                                      disposed=as_of, rates=rates)
        else:
            d.findings.append(
                f"**Aggregate position is at or below basis "
                f"({_money(total_gain)} gain).** With no gain there is no "
                f"excess distribution on disposition, so the §1291 exit charge "
                f"is near zero and the case for selling is at its strongest it "
                f"will ever be. A PFIC underwater is the cheapest one to leave, "
                f"and the cost of staying is unchanged.")

    if len(priced) < len(d.funds):
        d.findings.append(
            f"{len(d.funds) - len(priced)} of {len(d.funds)} holding(s) lack a "
            f"value, a basis or an acquisition date, so they are excluded from "
            f"the charge. They are not excluded from the compliance cost — a "
            f"fund still needs its Form 8621 whether or not anyone has looked "
            f"up what it cost.")

    if annual_cost_per_form is not None:
        d.annual_compliance = annual_cost_per_form * d.forms_per_year
        d.findings.append(
            f"**{_money(d.annual_compliance)}/yr to stay compliant** — "
            f"{d.forms_per_year} Form 8621(s) at "
            f"{_money(annual_cost_per_form)} each. Form 8621 is per fund, per "
            f"year, and it does not stop while the fund is held.")
        if d.charge and d.charge.computable and d.annual_compliance > 0:
            d.breakeven_years = (d.charge.total or 0.0) / d.annual_compliance
            d.findings.append(
                f"**Breakeven: {d.breakeven_years:.1f} years.** Exiting today "
                f"costs {_money(d.charge.total)}; staying costs "
                f"{_money(d.annual_compliance)}/yr. Holding longer than "
                f"{d.breakeven_years:.1f} years costs more than leaving now — "
                f"and this understates the case for leaving, because **the "
                f"exit charge itself grows every year you wait.** The "
                f"allocation lengthens and each new slice compounds. There is "
                f"no year in which selling gets cheaper.")
    elif d.charge and d.charge.computable:
        d.findings.append(
            f"**No per-form compliance cost supplied**, so the comparison is "
            f"inverted: at {d.forms_per_year} form(s) a year, holding for ten "
            f"more years costs the same as exiting today only if preparation "
            f"comes in under "
            f"{_money((d.charge.total or 0) / (d.forms_per_year * 10))} per "
            f"form per year. Set `assumptions.pfic_form_cost_annual` to a "
            f"quote from your own preparer rather than a typical figure — this "
            f"is a market price, and quotes for cross-border work vary by more "
            f"than the decision's margin.")
    else:
        d.findings.append(
            "**No per-form compliance cost supplied.** Set "
            "`assumptions.pfic_form_cost_annual` to a quote from the preparer "
            "who would actually file these.")

    if ltcg_rate is not None and d.charge and d.charge.computable:
        plain = (d.charge.amount or 0.0) * ltcg_rate
        d.findings.append(
            f"**The rate differential is the whole penalty.** The same gain in "
            f"a US-domiciled fund would have been long-term capital gain: "
            f"{_money(plain)} at {ltcg_rate:.0%}, against "
            f"{_money(d.charge.total)} under §1291 — "
            f"{_money((d.charge.total or 0) - plain)} more for holding the "
            f"same exposure through the wrong wrapper.")

    if not d.any_election_available:
        d.findings.append(
            "**No election is available on any holding, so §1291 applies by "
            "default** — and §1291 by default is the case for selling. There "
            "is no version of holding these that gets cheaper with time. See "
            "`quant-platform/docs/INDIA_PORTFOLIO_GUIDE.md` for the same "
            "conclusion reached on Indian mutual funds, with an equivalent US-"
            "domiciled wrapper for the same exposure.")
    else:
        d.findings.append(
            "**At least one election is available**, which changes the "
            "arithmetic above rather than settling it — an election stops the "
            "charge accruing from here, it does not clear what has already "
            "accrued. A late QEF leaves the §1291 taint in place until it is "
            "purged by a deemed sale, which triggers the charge computed here.")

    if any(not f.availability.determinable for f in d.funds):
        d.findings.append(
            "**Regime availability is unknown on at least one holding.** "
            "`null` is not `false`. Ask the fund administrator whether a PFIC "
            "Annual Information Statement is issued — one email, and the "
            "answer decides which half of this report applies.")

    d.findings.append(
        "This is a decision, not a filing position. Everything above ends at a "
        "cross-border CPA or EA — including, especially, the exit itself: "
        "selling a PFIC is the event that triggers the charge, and the order "
        "of operations within a tax year is theirs to set.")
    return d


def _num(x) -> float | None:
    return None if x is None else float(x)


def _as_date(value) -> _dt.date | None:
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str):
        try:
            return _dt.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _money(x) -> str:
    if x is None:
        return "not computed"
    return f"${x:,.0f}"
