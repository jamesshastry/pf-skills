"""Emergency fund sizing and idle-cash yield.

`MIN_BUFFER_MONTHS` lives here now, not in `auto`. It has two consumers — the
property and casualty skills refuse to recommend dropping coverage from a
household without a buffer, and `emergency-fund-sizing` is that rule promoted
to a skill. Per ROADMAP, a shared threshold gets extracted rather than copied.

The yield side takes its benchmark from the facts file rather than fetching a
rate. Live market data is deliberately out of scope, and a stale hard-coded
rate would be worse than asking.

## Yields are compared after tax, because gross comparison gets it backwards

Two cash vehicles with the same gross yield are not the same holding. Interest
from a bank account or a prime money market is fully taxable; interest from
direct Treasuries is **exempt from state income tax**. In a high-tax state that
exemption is frequently worth more than the headline yield difference it is
hiding behind, so a gross comparison can rank the wrong vehicle first.

## The yield edge floats; the exemption is structural

This distinction is the one worth carrying. A 0.25pp gross advantage is a
function of where short rates happen to sit and can vanish next quarter. The
state-tax exemption is worth the state rate multiplied by *whatever the yield
is*, so it survives convergence. Reporting a single combined number invites a
household to act on a figure that is mostly temporary, so the module separates
the two and reports the durable part as a floor.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Never recommend self-insuring anything from a household below this. The
#: buffer is the thing doing the self-insuring.
MIN_BUFFER_MONTHS = 3.0

#: Starting point for a dual-income household with stable pay and no
#: dependents. Everything else adds to it.
BASE_MONTHS = 3.0

#: One earner supporting others. The single largest adjustment, because the
#: household has no second income to fall back on and no partial-loss case.
SINGLE_EARNER_MONTHS = 3.0

#: Dependents lengthen a job search and remove the option of drastically
#: cutting living costs.
DEPENDENTS_MONTHS = 2.0

#: A large variable-compensation share means income can fall sharply without
#: any job loss at all.
VARIABLE_COMP_MONTHS = 2.0
VARIABLE_COMP_THRESHOLD = 0.25

#: Past this there are better homes for the money than cash.
MAX_MONTHS = 12.0

#: Share of spending that is genuinely non-discretionary in a crisis. Used to
#: show the longer runway available if spending is trimmed — not to size the
#: target, which uses full spending.
ESSENTIAL_SPENDING_FACTOR = 0.75

#: Hold more than this multiple of target in cash and the excess is being
#: eroded by inflation for no benefit.
EXCESS_MULTIPLE = 1.5


@dataclass
class Buffer:
    target_months: float
    monthly_spending: float
    target: float
    liquid: float
    months_held: float
    drivers: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    @property
    def shortfall(self) -> float:
        return max(0.0, self.target - self.liquid)

    @property
    def excess(self) -> float:
        return max(0.0, self.liquid - self.target * EXCESS_MULTIPLE)

    @property
    def adequate(self) -> bool:
        return self.liquid >= self.target


def target_months(
    *,
    earners: int,
    has_dependents: bool,
    variable_comp_share: float | None,
) -> tuple[float, list[str]]:
    months = BASE_MONTHS
    drivers = [f"Base {BASE_MONTHS:.0f} months"]

    if earners <= 1:
        months += SINGLE_EARNER_MONTHS
        drivers.append(
            f"+{SINGLE_EARNER_MONTHS:.0f} single earner — no second income to "
            "fall back on, and no partial-loss case"
        )
    if has_dependents:
        months += DEPENDENTS_MONTHS
        drivers.append(
            f"+{DEPENDENTS_MONTHS:.0f} dependents — longer job search, less "
            "room to cut living costs"
        )
    if variable_comp_share is not None and variable_comp_share >= VARIABLE_COMP_THRESHOLD:
        months += VARIABLE_COMP_MONTHS
        drivers.append(
            f"+{VARIABLE_COMP_MONTHS:.0f} {variable_comp_share:.0%} of income "
            "is variable — pay can fall sharply with no job loss at all"
        )
    return min(months, MAX_MONTHS), drivers


def size_buffer(
    *,
    liquid: float,
    annual_spending: float,
    earners: int,
    has_dependents: bool,
    variable_comp_share: float | None = None,
) -> Buffer:
    months, drivers = target_months(
        earners=earners, has_dependents=has_dependents,
        variable_comp_share=variable_comp_share)
    monthly = annual_spending / 12.0
    b = Buffer(
        target_months=months,
        monthly_spending=monthly,
        target=months * monthly,
        liquid=liquid,
        months_held=(liquid / monthly) if monthly else float("inf"),
        drivers=drivers,
    )

    if b.shortfall:
        b.findings.append(
            f"**{_money(b.shortfall)} short.** Until this is filled, treat "
            "every other recommendation as blocked — self-insuring a risk "
            "requires something to self-insure from, and an under-buffered "
            "household meets an ordinary setback with debt."
        )
    elif b.excess:
        b.findings.append(
            f"**{_money(b.excess)} beyond {EXCESS_MULTIPLE:.1f}× target is "
            "sitting in cash.** An emergency fund is insurance, and past the "
            "point where it covers the emergency, more of it buys nothing "
            "while inflation erodes it. Two questions follow, in order: is it "
            "earning a competitive yield (`cash-yield-review`), and should "
            "some of it be invested instead."
        )
    else:
        b.findings.append("Adequate. No action.")

    trimmed = annual_spending * ESSENTIAL_SPENDING_FACTOR / 12.0
    if trimmed:
        b.findings.append(
            f"For context: cutting to essential spending only (about "
            f"{_money(trimmed)}/month) stretches the same {_money(liquid)} to "
            f"**{liquid / trimmed:.0f} months**. The target above deliberately "
            "uses full spending — a crisis is a bad time to be discovering "
            "which costs are actually fixed."
        )
    return b


# ── idle cash ───────────────────────────────────────────────────────────────


#: Net investment income tax, applied to investment income above a threshold.
#: Supplied rather than assumed — it does not apply to every household.
DEFAULT_NIIT_RATE = 0.038


@dataclass(frozen=True)
class TaxProfile:
    """Rates applied to interest income. All optional; absent means unknown."""

    federal: float | None = None
    niit: float | None = None
    state: float | None = None
    state_code: str | None = None

    @property
    def known(self) -> bool:
        """After-tax comparison needs at least a federal and a state rate.

        Without the state rate the exemption — the entire point — cannot be
        valued, so a partial profile is treated as no profile rather than
        producing a comparison that silently omits the thing being measured.
        """
        return self.federal is not None and self.state is not None

    def keep_rate(self, *, state_exempt: bool) -> float:
        """Share of gross interest the household keeps."""
        burden = (self.federal or 0) + (self.niit or 0)
        if not state_exempt:
            burden += self.state or 0
        return 1 - burden


def after_tax_yield(gross: float, *, state_exempt: bool, tax: TaxProfile) -> float:
    return gross * tax.keep_rate(state_exempt=state_exempt)


@dataclass
class YieldLine:
    name: str
    balance: float
    gross: float | None
    state_exempt: bool
    after_tax: float | None
    #: Annual income given up against the benchmark, on an after-tax basis
    #: where the tax profile allows, gross otherwise.
    foregone: float | None
    #: The part of `foregone` that survives the two yields converging.
    durable: float | None = None


@dataclass
class YieldReview:
    benchmark: float
    benchmark_as_of: str | None
    benchmark_label: str | None = None
    benchmark_state_exempt: bool = False
    tax: TaxProfile = field(default_factory=TaxProfile)
    lines: list[YieldLine] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    @property
    def after_tax(self) -> bool:
        return self.tax.known

    @property
    def total_foregone(self) -> float:
        return sum(l.foregone or 0 for l in self.lines)

    @property
    def total_durable(self) -> float:
        return sum(l.durable or 0 for l in self.lines)

    @property
    def unknown_yields(self) -> int:
        return sum(1 for l in self.lines if l.gross is None)


def review_yield(
    rows: list[dict],
    *,
    benchmark_apr: float | None,
    benchmark_as_of: str | None = None,
    benchmark_label: str | None = None,
    benchmark_state_exempt: bool = False,
    tax: TaxProfile | None = None,
    state: str | None = None,
) -> YieldReview:
    tax = tax or TaxProfile(state_code=state)
    r = YieldReview(benchmark=benchmark_apr or 0.0,
                    benchmark_as_of=benchmark_as_of,
                    benchmark_label=benchmark_label,
                    benchmark_state_exempt=benchmark_state_exempt,
                    tax=tax)

    if benchmark_apr is None:
        r.findings.append(
            "**No benchmark rate supplied**, so nothing can be compared. Set "
            "`assumptions.cash_benchmark_apr` to the current yield on a "
            "short-duration Treasury fund or a competitive money market. This "
            "is asked for rather than fetched: a rate hard-coded into a skill "
            "goes stale silently, and a stale benchmark produces confident "
            "nonsense in both directions."
        )
        return r

    bench_net = (after_tax_yield(benchmark_apr, state_exempt=benchmark_state_exempt,
                                 tax=tax) if tax.known else benchmark_apr)

    unclassified = 0
    for row in rows:
        if row.get("tier") != "liquid":
            continue
        # `tier: liquid` means spendable within days, which correctly
        # includes equities. They are not cash-yield candidates, so asking
        # for their yield is the wrong question — an early version demanded
        # one for a stock position.
        cls = row.get("asset_class")
        if cls is not None and cls != "cash":
            continue
        if cls is None:
            unclassified += 1
        bal = float(row.get("value") or 0)
        # `yield_apr` is the original field name, kept working. `yield_gross`
        # is preferred because it names the basis, which is the whole point.
        gross = row.get("yield_gross")
        if gross is None:
            gross = row.get("yield_apr")
        exempt = bool(row.get("state_tax_exempt"))

        if gross is None:
            r.lines.append(YieldLine(row.get("name") or "account", bal,
                                     None, exempt, None, None))
            continue

        net = after_tax_yield(gross, state_exempt=exempt, tax=tax) if tax.known else gross
        foregone = max(0.0, (bench_net - net) * bal)

        # The part that survives the two gross yields converging: the state
        # exemption, valued at the LOWER of the two yields so it is a floor
        # rather than a forecast.
        durable = 0.0
        if tax.known and benchmark_state_exempt and not exempt:
            durable = min(gross, benchmark_apr) * (tax.state or 0) * bal
        durable = min(durable, foregone)

        r.lines.append(YieldLine(row.get("name") or "account", bal, gross,
                                 exempt, net, foregone, durable))

    if unclassified:
        r.findings.append(
            f"{unclassified} liquid holding(s) have no `asset_class`, so they "
            "are reviewed as if they were cash. Mark equities and bond funds "
            "as such — `tier: liquid` means spendable within days, which is "
            "true of a stock position and does not make it a cash-yield "
            "candidate."
        )

    if r.unknown_yields:
        r.findings.append(
            f"{r.unknown_yields} cash holding(s) have no yield recorded. "
            "Look them up — the number is on the statement, and a cash "
            "account paying near zero is the most common unforced error in a "
            "household balance sheet."
        )

    if not tax.known:
        r.findings.append(
            "**Compared on gross yield only.** Supply "
            "`assumptions.marginal_tax_rate` and `assumptions.state_tax_rate` "
            "to compare after tax, which is the comparison that decides the "
            "answer: Treasury interest is exempt from state income tax and "
            "bank interest is not, so two vehicles with the same gross yield "
            "are not the same holding."
        )
    elif r.total_foregone > 0:
        r.findings.append(
            f"**{_money(r.total_foregone)}/yr foregone after tax** against "
            f"{benchmark_label or 'the benchmark'} at {benchmark_apr:.2%} "
            f"gross ({bench_net:.2%} after tax). Same risk, same liquidity, "
            "more yield — this is the rare case where the action is "
            "unambiguous."
        )
        if r.total_durable > 0:
            floating = r.total_foregone - r.total_durable
            r.findings.append(
                f"**Only {_money(r.total_durable)} of that is durable.** The "
                f"remaining {_money(floating)} comes from a gross yield edge "
                "that floats with short rates and could disappear next "
                "quarter. The state-tax exemption does not: it is worth the "
                f"state rate on whatever the yield happens to be, so "
                f"{_money(r.total_durable)}/yr is the floor on this move, not "
                "the headline figure. Decide on the floor."
            )

    if tax.known and benchmark_state_exempt:
        gross_gap = benchmark_apr - max(
            (l.gross for l in r.lines if l.gross is not None and not l.state_exempt),
            default=benchmark_apr)
        net_gap = bench_net - max(
            (l.after_tax for l in r.lines if l.after_tax is not None
             and not l.state_exempt), default=bench_net)
        if net_gap > gross_gap > 0:
            r.findings.append(
                f"**The gap widens after tax**, from {gross_gap:.2%} gross to "
                f"{net_gap:.2%} net. The exemption is worth more than the "
                "headline yield difference it is hiding behind — which is why "
                "ranking these on gross yield can pick the wrong vehicle."
            )

    if tax.known and tax.state == 0 and benchmark_state_exempt:
        r.findings.append(
            f"**{tax.state_code or 'This state'} levies no income tax, so the "
            "Treasury exemption is worth nothing here.** Compare these purely "
            "on gross yield and convenience. The exemption is the durable "
            "part of the argument in a high-tax state and simply absent in a "
            "no-tax one — which is why the state belongs in the facts file "
            "rather than being assumed."
        )

    if tax.state_code and not tax.known:
        r.findings.append(
            f"**Interest on US Treasuries is exempt from {tax.state_code} "
            "income tax**; interest from a bank account or a prime money "
            "market is not."
        )

    r.findings.append(
        "Keep the emergency fund liquid and boring. Chasing yield with money "
        "that has to be available on a bad day defeats the purpose of holding "
        "it — this is about not leaving free yield on the table, not about "
        "taking risk with the buffer."
    )
    return r


def _money(x) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
