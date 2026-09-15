"""Rent versus buy, and mortgage review.

The rent-versus-buy comparison is almost always presented wrongly: monthly
mortgage payment against monthly rent. That comparison is meaningless, because
the payment is not the cost of owning. Most of the real cost is in the items
that never appear on the mortgage statement — property tax, insurance,
maintenance, and the transaction costs of getting in and out.

So this module compares **total cost of occupancy over a holding period**,
counts the principal portion as savings rather than cost, and reports a
break-even holding period. The break-even is the actual output: buying is
rarely wrong or right in general, it is wrong or right *for how long you stay*.

Nothing here forecasts house prices. Appreciation is an input the household
supplies, and the default is **zero real** appreciation so the conclusion does
not rest on a forecast.

## Everything here is NOMINAL, and that is a deliberate choice

Unlike `retirement.py`, which is real throughout, this module works in nominal
terms — because the mortgage rate is inherently nominal and rewriting it into
real terms would obscure the one number the household actually knows.

That means every other input must be nominal too, and the defaults enforce it:
the investment return is a nominal return, rent growth is nominal, and **zero
real appreciation is expressed as appreciation equal to rent growth**, not as
zero.

Getting this wrong is easy and expensive. An earlier version of this module
took its investment return from `assumptions.expected_return_apr` — a nominal
figure, since it exists to be compared against nominal debt rates — and applied
it as a real return alongside zero *nominal* appreciation. That combination
made buying look catastrophic and never break even. Same defect class as mixing
real and nominal in a retirement projection; it just hides better here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Cost of buying, as a share of price — legal, inspection, lender fees.
BUY_COSTS = 0.02

#: Cost of selling, as a share of price. Agent commission dominates, and it is
#: the single largest reason short holding periods lose.
SELL_COSTS = 0.06

#: Annual maintenance as a share of value when not supplied. A benchmark, and
#: the most under-budgeted line in home ownership.
DEFAULT_MAINTENANCE_RATE = 0.01

#: NOMINAL return assumed on the down payment had it stayed invested. The
#: opportunity cost that rent-versus-buy comparisons almost always omit, and
#: usually the second-largest line in the table.
DEFAULT_INVESTMENT_RETURN = 0.07

#: NOMINAL rent growth when not supplied — roughly general inflation.
DEFAULT_RENT_GROWTH = 0.03

#: NOMINAL house price appreciation when not supplied. Set equal to rent
#: growth, which is **zero real appreciation** expressed in nominal terms.
#: Setting this to 0 would silently assume houses fall in real terms every
#: year and would decide the answer on its own.
DEFAULT_APPRECIATION = DEFAULT_RENT_GROWTH

#: A refinance has to recover its cost inside this many months to be obviously
#: worth doing.
REFI_BREAKEVEN_MONTHS = 36

#: Loan-to-value at which mortgage insurance can usually be removed.
PMI_REMOVAL_LTV = 0.80

#: HOA dues stop being a line in the outflows table and become a finding once
#: their **price-equivalent** reaches this share of the purchase price.
#:
#: The test is on price-equivalence rather than on dues as a share of annual
#: running cost, and that choice matters. A share-of-running-cost test is
#: dominated by principal and interest, so on an expensive property it stays
#: comfortably small — well under any threshold worth setting — while the same
#: dues are displacing six figures of purchase price. It would have missed the
#: case this finding was written for. This test measures what the finding is
#: actually about: whether the listing price is misleading as a comparator
#: against properties that carry no dues.
#:
#: 5% is set where the distortion exceeds ordinary negotiating range. Below it
#: the dues change the arithmetic; above it they change *which houses this one
#: should be compared against at all*, which is a different kind of error and
#: not one more decimal places will fix.
HOA_MATERIAL_PRICE_SHARE = 0.05

#: Assumed growth in dues when not supplied. Dues track labour, insurance and
#: deferred reserves rather than general prices and have historically run at or
#: above inflation, so this is a floor rather than a forecast — the point
#: survives any plausible value.
DEFAULT_HOA_GROWTH = DEFAULT_RENT_GROWTH

#: Horizon for the "what will dues be by then" figure. Chosen to land inside a
#: typical mortgage term while being far enough out that compounding is
#: visible, and because it is roughly when a mid-career buyer's income stops.
HOA_PROJECTION_YEARS = 20


def monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    """Standard amortising payment."""
    if principal <= 0:
        return 0.0
    r = annual_rate / 12.0
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r / (1 - (1 + r) ** -n)


def amortise(principal: float, annual_rate: float, years: int, months: int):
    """Return (interest_paid, principal_paid, balance) over `months`."""
    r = annual_rate / 12.0
    pmt = monthly_payment(principal, annual_rate, years)
    balance = principal
    interest_total = principal_total = 0.0
    for _ in range(min(months, years * 12)):
        interest = balance * r
        principal_part = min(pmt - interest, balance)
        balance -= principal_part
        interest_total += interest
        principal_total += principal_part
        if balance <= 0:
            break
    return interest_total, principal_total, max(0.0, balance)


@dataclass
class Comparison:
    years: int
    price: float
    down_payment: float
    loan: float
    monthly_payment: float
    interest_paid: float
    principal_paid: float
    tax_paid: float
    insurance_paid: float
    maintenance_paid: float
    hoa_paid: float
    transaction_costs: float
    opportunity_cost: float
    appreciation: float
    total_cost_of_owning: float
    total_cost_of_renting: float
    breakeven_years: int | None
    findings: list[str] = field(default_factory=list)

    @property
    def owning_cheaper(self) -> bool:
        return self.total_cost_of_owning < self.total_cost_of_renting

    @property
    def difference(self) -> float:
        return self.total_cost_of_owning - self.total_cost_of_renting


def _fv(amount: float, rate: float, years_to_horizon: float) -> float:
    return amount * (1 + rate) ** years_to_horizon


def cost_of_owning(p: dict, years: int, *, investment_return: float,
                   appreciation: float) -> dict:
    """Cost of owning, expressed as **wealth given up by the horizon**.

    Every outflow is carried forward to the horizon at `investment_return`,
    because a dollar spent on housing in year 3 is a dollar that could have
    been invested for the remaining term. Summing undiscounted cash flows
    across thirty years — as an earlier version did — treats a dollar in year
    30 as equal to a dollar today and systematically flatters whichever side
    spends later. Owning front-loads cost and back-loads benefit, so that
    error favoured buying.

    Terminal equity is credited at the horizon: sale price, less selling
    costs, less the outstanding balance.
    """
    price = float(p.get("price") or 0)
    down = float(p.get("down_payment") or 0)
    loan = max(0.0, price - down)
    rate = float(p.get("mortgage_rate") or 0)
    term = int(p.get("term_years") or 30)
    months = years * 12

    pmt = monthly_payment(loan, rate, term)
    interest, principal, balance = amortise(loan, rate, term, months)

    annual_pi = pmt * 12
    annual_tax = price * float(p.get("property_tax_rate") or 0)
    annual_ins = float(p.get("insurance_annual") or 0)
    annual_maint = price * float(p.get("maintenance_rate") or DEFAULT_MAINTENANCE_RATE)
    annual_hoa = float(p.get("hoa_monthly") or 0) * 12

    # Year-0 outflows compound for the whole term.
    upfront = down + price * BUY_COSTS
    outflows_fv = _fv(upfront, investment_return, years)

    running = annual_pi + annual_tax + annual_ins + annual_maint + annual_hoa
    for y in range(1, years + 1):
        paid = running if y * 12 <= term * 12 else (
            annual_tax + annual_ins + annual_maint + annual_hoa)
        outflows_fv += _fv(paid, investment_return, years - y)

    future_price = price * (1 + appreciation) ** years
    terminal_equity = future_price - future_price * SELL_COSTS - balance

    return {
        "price": price, "down": down, "loan": loan, "payment": pmt,
        "interest": interest, "principal": principal,
        "tax": annual_tax * years, "insurance": annual_ins * years,
        "maintenance": annual_maint * years, "hoa": annual_hoa * years,
        "transaction": price * BUY_COSTS + future_price * SELL_COSTS,
        "outflows_fv": outflows_fv,
        "terminal_equity": terminal_equity,
        "future_price": future_price,
        "balance": balance,
        "gain": future_price - price,
        "total": outflows_fv - terminal_equity,
    }


@dataclass
class HOAEquivalence:
    """Dues expressed as the mortgage and the price they are equivalent to.

    An HOA is **not a substitute for maintenance. It is a substitute for
    mortgage.** Maintenance is lumpy, deferrable and partly discretionary;
    dues are fixed, unavoidable and perpetual. That makes them debt service in
    everything but name, and converting them to price-equivalence is the only
    way to compare a property that carries them against one that does not.
    """
    monthly_dues: float
    annual_dues: float
    rate: float
    term: int
    ltv: float
    #: Dues divided by the annual payment on one dollar of loan.
    loan_equivalent: float
    #: The loan-equivalent grossed up by the LTV actually being used.
    price_equivalent: float
    share_of_price: float
    comparable_price: float
    projected_monthly: float
    projection_years: int

    @property
    def material(self) -> bool:
        return self.share_of_price >= HOA_MATERIAL_PRICE_SHARE


def hoa_equivalence(p: dict, *,
                    hoa_growth: float = DEFAULT_HOA_GROWTH,
                    projection_years: int = HOA_PROJECTION_YEARS
                    ) -> HOAEquivalence | None:
    """What the dues are worth in loan and in price. None if not computable.

    Both the rate and the loan-to-value come from the facts. Hardcoding a rate
    would put a market assumption inside a conversion that should only reflect
    the deal in front of the household.
    """
    monthly = float(p.get("hoa_monthly") or 0)
    price = float(p.get("price") or 0)
    rate = float(p.get("mortgage_rate") or 0)
    term = int(p.get("term_years") or 30)
    down = float(p.get("down_payment") or 0)
    if monthly <= 0 or price <= 0 or rate <= 0:
        return None
    ltv = max(0.0, price - down) / price
    if ltv <= 0:
        # An all-cash purchase has no mortgage to be equivalent to. The dues
        # are still real; there is simply no conversion to make.
        return None

    annual_pi_per_dollar = monthly_payment(1.0, rate, term) * 12
    if annual_pi_per_dollar <= 0:                # pragma: no cover - defensive
        return None
    annual = monthly * 12
    loan_equiv = annual / annual_pi_per_dollar
    price_equiv = loan_equiv / ltv
    return HOAEquivalence(
        monthly_dues=monthly, annual_dues=annual, rate=rate, term=term,
        ltv=ltv, loan_equivalent=loan_equiv, price_equivalent=price_equiv,
        share_of_price=price_equiv / price,
        comparable_price=price + price_equiv,
        projected_monthly=monthly * (1 + hoa_growth) ** projection_years,
        projection_years=projection_years,
    )


def cost_of_renting(monthly_rent: float, years: int, *,
                    rent_growth: float,
                    investment_return: float = DEFAULT_INVESTMENT_RETURN) -> float:
    """Rent carried forward to the same horizon at the same rate."""
    total = 0.0
    rent = monthly_rent * 12
    for y in range(1, years + 1):
        total += _fv(rent, investment_return, years - y)
        rent *= (1 + rent_growth)
    return total


def compare(
    purchase: dict,
    *,
    monthly_rent: float,
    years: int,
    investment_return: float = DEFAULT_INVESTMENT_RETURN,
    appreciation: float = DEFAULT_APPRECIATION,
    rent_growth: float = DEFAULT_RENT_GROWTH,
) -> Comparison:
    own = cost_of_owning(purchase, years, investment_return=investment_return,
                         appreciation=appreciation)
    rent_total = cost_of_renting(monthly_rent, years, rent_growth=rent_growth,
                                 investment_return=investment_return)

    breakeven = None
    for y in range(1, 41):
        o = cost_of_owning(purchase, y, investment_return=investment_return,
                           appreciation=appreciation)
        r = cost_of_renting(monthly_rent, y, rent_growth=rent_growth,
                            investment_return=investment_return)
        if o["total"] <= r:
            breakeven = y
            break

    c = Comparison(
        years=years, price=own["price"], down_payment=own["down"],
        loan=own["loan"], monthly_payment=own["payment"],
        interest_paid=own["interest"], principal_paid=own["principal"],
        tax_paid=own["tax"], insurance_paid=own["insurance"],
        maintenance_paid=own["maintenance"], hoa_paid=own["hoa"],
        transaction_costs=own["transaction"],
        opportunity_cost=own["outflows_fv"],
        appreciation=own["terminal_equity"], total_cost_of_owning=own["total"],
        total_cost_of_renting=rent_total, breakeven_years=breakeven,
    )

    c.findings.append(
        "**Do not compare the mortgage payment to the rent.** The payment is "
        "not the cost of owning. Property tax, insurance, maintenance and the "
        "cost of getting in and out are most of it, and none of them appears "
        "on a mortgage statement."
    )
    c.findings.append(
        f"Principal repayment ({_money(own['principal'])} over {years} years) "
        "is **excluded from the cost of owning** — it converts cash into "
        "equity rather than spending it. Counting it as a cost is the most "
        "common error in the other direction."
    )
    c.findings.append(
        f"**Both sides are carried forward to the horizon at "
        f"{investment_return:.0%}**, not summed undiscounted. A dollar spent "
        "on housing in year 3 is a dollar that could have been invested for "
        "the rest of the term. Owning front-loads cost and back-loads "
        "benefit, so ignoring timing flatters buying — which is the error "
        "most published comparisons make, on top of omitting the down "
        "payment's opportunity cost entirely."
    )
    if breakeven is None:
        c.findings.append(
            "**Buying does not break even within 40 years** at these "
            "assumptions. That normally means the price-to-rent ratio is very "
            "high, or the assumed appreciation is very low — check both before "
            "treating it as settled."
        )
    else:
        c.findings.append(
            f"**Break-even at about {breakeven} year(s).** Below that, renting "
            "wins; above it, buying does. This is the real output — buying is "
            "rarely right or wrong in general, it is right or wrong *for how "
            "long you stay*."
        )
    real_appreciation = appreciation - rent_growth
    c.findings.append(
        f"**Everything here is nominal**, because the mortgage rate is. "
        f"Appreciation {appreciation:.1%} against rent growth "
        f"{rent_growth:.1%} is **{real_appreciation:+.1%} real** — "
        + ("the deliberate default, so no forecast is baked in."
           if abs(real_appreciation) < 1e-9 else
           "a supplied assumption. Check how much of the conclusion rests on "
           "it before relying on the answer.")
    )
    c.findings.append(
        f"Selling costs alone are about {SELL_COSTS:.0%} of price. That single "
        "line is why short holding periods lose, and it does not shrink if the "
        "market moves against you."
    )

    eq = hoa_equivalence(purchase, hoa_growth=rent_growth)
    if eq is not None and eq.material:
        c.findings.append(
            f"**The HOA is not a substitute for maintenance — it is a "
            f"substitute for mortgage.** {_money(eq.monthly_dues)}/month is "
            f"fixed, unavoidable and perpetual, which makes it debt service "
            f"in everything but name. At {eq.rate:.2%} over {eq.term} years "
            f"and the {eq.ltv:.0%} loan-to-value actually being used, "
            f"{_money(eq.annual_dues)} a year carries "
            f"**{_money(eq.loan_equivalent)} of loan**, which at that "
            f"loan-to-value is **{_money(eq.price_equivalent)} of price** — "
            f"{eq.share_of_price:.0%} of the asking price. A "
            f"{_money(own['price'])} property with these dues costs what a "
            f"**{_money(eq.comparable_price)}** property without them costs. "
            "That is the comparison to make against listings that carry no "
            "dues, and no amount of reading the outflows table surfaces it."
        )
        c.findings.append(
            f"**And it is worse debt than a mortgage.** Principal and interest "
            f"are fixed and gone at the end of the term; dues inflate and "
            f"never end. At {rent_growth:.0%} growth, "
            f"{_money(eq.monthly_dues)}/month is about "
            f"**{_money(eq.projected_monthly)}/month in "
            f"{eq.projection_years} years** — typically arriving around the "
            "time earned income stops. The association also sets the number, "
            "and a special assessment is not optional."
        )
        c.findings.append(
            f"Over {years} years the dues total {_money(c.hoa_paid)}"
            + (", the largest avoidable line here after interest."
               if c.hoa_paid > c.transaction_costs else ".")
            + " Unlike maintenance, none of it is deferrable, and unlike "
              "principal, none of it comes back on sale."
        )
    return c


# ── mortgage review ─────────────────────────────────────────────────────────


@dataclass
class MortgageReview:
    balance: float
    rate: float
    payment: float
    ltv: float | None
    findings: list[str] = field(default_factory=list)


def review_mortgage(
    *, balance: float, rate: float, term_years: int, value: float | None,
    pmi_monthly: float | None = None, extra_monthly: float = 0.0,
) -> MortgageReview:
    pmt = monthly_payment(balance, rate, term_years)
    ltv = (balance / value) if value else None
    m = MortgageReview(balance=balance, rate=rate, payment=pmt, ltv=ltv)

    if ltv is not None and pmi_monthly and ltv < PMI_REMOVAL_LTV:
        m.findings.append(
            f"**Loan-to-value is {ltv:.0%}, below the {PMI_REMOVAL_LTV:.0%} "
            f"threshold, and mortgage insurance is still being paid — "
            f"{_money(pmi_monthly * 12)}/yr.** Removal is usually not "
            "automatic on request-based schemes; you have to ask, and may need "
            "an appraisal. This is free money and it is routinely left "
            "unclaimed for years."
        )
    elif ltv is not None:
        m.findings.append(f"Loan-to-value {ltv:.0%}.")

    if extra_monthly > 0:
        base_i, _, _ = amortise(balance, rate, term_years, term_years * 12)
        r = rate / 12.0
        bal, saved_i, months = balance, 0.0, 0
        while bal > 0 and months < term_years * 12:
            interest = bal * r
            bal -= min(pmt + extra_monthly - interest, bal)
            saved_i += interest
            months += 1
        m.findings.append(
            f"Paying {_money(extra_monthly)}/month extra clears the loan in "
            f"**{months // 12}y {months % 12}m** instead of {term_years}y, "
            f"saving about {_money(base_i - saved_i)} of interest."
        )
        m.findings.append(
            "**Compare that against investing the same amount.** Prepaying a "
            f"mortgage is a guaranteed {rate:.2%} return, tax-adjusted if the "
            "interest is deductible. That is a *certain* return against an "
            "*uncertain* one, so preferring it is a preference, not an error — "
            "see `debt-payoff-priority`, which makes the same argument."
        )
    m.findings.append(
        "**Refinancing is a break-even calculation, not a rate comparison.** "
        f"Divide the closing costs by the monthly saving; under about "
        f"{REFI_BREAKEVEN_MONTHS} months it is usually clear, beyond it "
        "depends how long you will stay. Resetting a 20-years-remaining loan "
        "to a fresh 30-year term lowers the payment while increasing total "
        "interest — that is a cash-flow decision being presented as a saving."
    )
    return m


def _money(x) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
