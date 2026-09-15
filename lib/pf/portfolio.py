"""Portfolio *policy*: the target, the rule that restores it, and what may not be bought.

Three decisions a household makes once and then stops re-litigating:

1. **What mix should we hold, and where should each piece live** — allocation
   and *location*, which are different questions with different answers.
2. **What triggers a correction** — a band, a calendar, or (the common case) an
   undocumented mood.
3. **What may never be bought, in which accounts, and until when** — the
   wash-sale exclusion list.

## The seam with a portfolio tool

This module answers *"should I, and what is my rule"*. It refuses *"which lots,
and when"*. It does not read prices, does not select tax lots, does not compute
a gain, and does not emit an order. Everything here is derived from balances the
household already wrote down, so the output is a policy document, not a trade
list. The drift figures below are sized in dollars only to make the policy
decidable — they are not a rebalancing instruction, and the ordering of lots
inside a taxable sale is deliberately out of scope.

## Balances, not market values

Every figure comes from `household.balance_sheet` as of `meta.as_of`. A drift
computed from month-old balances is still the right *policy* input: bands exist
precisely because the exact number does not matter, only which side of the band
it falls on. Where that distinction is close, the report says so rather than
implying a precision the input cannot carry.

## Unknown is not zero

A holding with no `asset_class` is not cash and is not equity — it is
unclassified, excluded from the denominators, and reported. Folding it into
"other" would produce a tidy allocation table that is quietly wrong.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from . import facts as _facts

# ── asset classes and account types ─────────────────────────────────────────

ASSET_CLASSES = ("us_equity", "intl_equity", "equity", "bond", "reit", "cash", "other")

#: Growth assets. Their return arrives mostly as unrealised appreciation, which
#: is why *where* they are held changes the after-tax outcome.
EQUITY_CLASSES = frozenset({"us_equity", "intl_equity", "equity"})

#: Assets that throw off ordinary income taxed every year whether or not
#: anything is sold. The whole asset-location argument rests on this property.
INCOME_CLASSES = frozenset({"bond", "reit"})

TAXABLE = "taxable"
TAX_DEFERRED = "tax_deferred"
ROTH = "roth"
HSA = "hsa"
EDUCATION = "education"
ACCOUNT_TYPES = (TAXABLE, TAX_DEFERRED, ROTH, HSA, EDUCATION)

#: Growth in these is never taxed, so the highest-expected-return assets belong
#: here — a dollar of return earned in a Roth is worth more than the same dollar
#: earned anywhere else, and that is true regardless of any market view.
NEVER_TAXED = frozenset({ROTH, HSA})

#: Sheltered from annual taxation of income, but taxed as ordinary income on
#: the way out. This is where income-producing assets belong.
SHELTERED = frozenset({TAX_DEFERRED, ROTH, HSA})

#: Earmarked against a specific named obligation with its own glide path, so it
#: does not belong in the household's allocation denominators. Counting a 529
#: as household equity overstates the household's risk capacity by money that
#: is already spoken for.
EARMARKED_ACCOUNTS = frozenset({EDUCATION})

# ── glide path ──────────────────────────────────────────────────────────────

#: Equity share at a zero-year horizon, before any credit for time. Not zero:
#: a retirement is a thirty-year liability, and a portfolio with no growth
#: assets fails to inflation rather than to volatility.
GLIDE_BASE_EQUITY = 0.40

#: Additional equity share per year of horizon. Two points a year reaches the
#: ceiling at roughly a twenty-five-year horizon, which is where the ability to
#: wait out a drawdown stops being the binding constraint.
GLIDE_EQUITY_PER_YEAR = 0.02

MIN_EQUITY_SHARE = 0.30
MAX_EQUITY_SHARE = 0.90

#: The glide path is reported as a band, never a point. A ±10pp spread is
#: roughly the width of the honest disagreement between reasonable published
#: glide paths at the same age, and quoting a single number invites a household
#: to treat a convention as a calculation.
GLIDE_BAND = 0.10

#: Inside this horizon, sequence-of-returns risk rather than long-run expected
#: return is the thing the allocation has to survive.
NEAR_RETIREMENT_YEARS = 10

# ── rebalancing bands ───────────────────────────────────────────────────────

#: Absolute drift, in percentage points of the whole portfolio, that makes a
#: correction worth its costs. Below this the tracking error against the target
#: is smaller than the spread, the taxes, and the chance of being wrong about
#: the target in the first place.
ABSOLUTE_BAND = 0.05

#: Relative drift, as a share of the class's own target. A 5pp absolute band can
#: never trigger on a class targeted at 5% — it would have to vanish entirely
#: and still not breach. The relative band is what governs small sleeves.
RELATIVE_BAND = 0.25

#: Bands are a rule about *when to look*, not a promise to look continuously.
#: Quarterly is frequent enough that a breach is caught while it is still small
#: and infrequent enough that it does not become a market-watching habit.
BAND_CHECK_MONTHS = 3

#: Binary floating point makes 0.55 - 0.50 slightly larger than 0.05, which
#: would report a portfolio sitting exactly on its band as having breached it.
#: The band is a judgement to one decimal place; this tolerance is far below
#: anything the input can resolve.
BAND_EPSILON = 1e-9

#: Cadence for a calendar policy. Annual is the standard choice, and its virtue
#: is that it is unambiguous: the date decides, not the portfolio.
CALENDAR_MONTHS = 12

# ── wash sales ──────────────────────────────────────────────────────────────

#: §1091 runs 30 days *before* and 30 days *after* the sale. The "before" half
#: is the one households miss, because a purchase that already happened cannot
#: be undone once the loss is taken.
WASH_SALE_WINDOW_DAYS = 30

#: 30 before + the day of sale + 30 after. Quoting "30 days" as the rule
#: understates the exposure by half.
WASH_SALE_TOTAL_DAYS = 61

WASH_SALE_SOURCE = (
    "IRC §1091 and IRS Publication 550 (wash sales); Rev. Rul. 2008-5 "
    "(purchase in an IRA disallows the loss with no basis adjustment)"
)

#: Nobody in this repository has re-checked this against the source. It is
#: long-settled federal law rather than an annually adjusted figure, but saying
#: "verified" without having verified it is how a table goes quietly stale.
WASH_SALE_VERIFIED_ON = "unverified — check against irs.gov Publication 550"

WASH_SALE_VALUES = {
    "window_days_each_side": WASH_SALE_WINDOW_DAYS,
    "total_window_days": WASH_SALE_TOTAL_DAYS,
    "applies_across_all_accounts": True,
    "ira_purchase_disallows_permanently": True,
    "ira_basis_adjustment_available": False,
    "test_is_substantially_identical": True,
}

#: Account types where a replacement purchase destroys the loss outright rather
#: than deferring it. Rev. Rul. 2008-5 addresses IRAs specifically; a 401(k) is
#: not named in it, and the policy covers one anyway — see `RETIREMENT_ACCOUNTS`.
IRA_ACCOUNTS = frozenset({ROTH, TAX_DEFERRED})


# ── holdings ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Holding:
    """One asset class inside one account. A row may expand into several."""

    account: str
    account_type: str | None
    asset_class: str
    value: float

    @property
    def sheltered(self) -> bool:
        return self.account_type in SHELTERED

    @property
    def never_taxed(self) -> bool:
        return self.account_type in NEVER_TAXED


@dataclass
class Inventory:
    holdings: list[Holding] = field(default_factory=list)
    #: Rows carrying value but no asset class. Excluded from every denominator.
    unclassified: list[tuple[str, float]] = field(default_factory=list)
    #: Rows excluded on purpose because they are earmarked.
    earmarked: list[tuple[str, float]] = field(default_factory=list)
    #: Rows whose `holdings[]` do not sum to the row's own `value`.
    mismatched: list[tuple[str, float, float]] = field(default_factory=list)
    #: Rows with an asset class but no account type — location cannot be judged.
    untyped: list[tuple[str, float]] = field(default_factory=list)

    @property
    def total(self) -> float:
        return sum(h.value for h in self.holdings)

    @property
    def unclassified_value(self) -> float:
        return sum(v for _, v in self.unclassified)

    def by_class(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for h in self.holdings:
            out[h.asset_class] = out.get(h.asset_class, 0.0) + h.value
        return out

    def value_in(self, asset_class: str, account_types: frozenset[str]) -> float:
        return sum(h.value for h in self.holdings
                   if h.asset_class == asset_class and h.account_type in account_types)

    @property
    def equity_share(self) -> float | None:
        if not self.total:
            return None
        return sum(h.value for h in self.holdings
                   if h.asset_class in EQUITY_CLASSES) / self.total


def inventory(rows: list[dict]) -> Inventory:
    """Expand balance-sheet rows into per-class holdings.

    A row is one account. `holdings: [{asset_class, value}]` splits it; a bare
    `asset_class` treats the whole account as one class. `pending` rows are
    excluded for the same reason `facts.tier_total` excludes them — an
    unsettled order may already be counted in the balance it came from.
    """
    inv = Inventory()
    for row in rows or []:
        if row.get("pending"):
            continue
        name = row.get("name") or "account"
        value = float(row.get("value") or 0)
        acct = row.get("account_type")
        if acct in EARMARKED_ACCOUNTS:
            inv.earmarked.append((name, value))
            continue

        parts = row.get("holdings")
        if parts:
            total = 0.0
            for p in parts:
                cls = p.get("asset_class")
                pv = float(p.get("value") or 0)
                total += pv
                if cls is None:
                    inv.unclassified.append((f"{name} (sub-holding)", pv))
                    continue
                inv.holdings.append(Holding(name, acct, cls, pv))
                if acct is None:
                    inv.untyped.append((name, pv))
            if abs(total - value) > 1.0:
                inv.mismatched.append((name, value, total))
            continue

        cls = row.get("asset_class")
        if cls is None:
            inv.unclassified.append((name, value))
            continue
        inv.holdings.append(Holding(name, acct, cls, value))
        if acct is None:
            inv.untyped.append((name, value))
    return inv


# ── allocation against the recorded target ──────────────────────────────────


@dataclass
class Sleeve:
    asset_class: str
    target: float
    value: float
    share: float

    @property
    def drift(self) -> float:
        """Signed, in points of the whole portfolio. Positive means overweight."""
        return self.share - self.target

    @property
    def relative_drift(self) -> float | None:
        if not self.target:
            return None
        return self.drift / self.target

    @property
    def band(self) -> float:
        """The tighter of the absolute and relative bands — the 5/25 rule."""
        return band_for(self.target)

    @property
    def breached(self) -> bool:
        return abs(self.drift) > self.band + BAND_EPSILON

    @property
    def which_band(self) -> str:
        return ("relative" if self.target * RELATIVE_BAND < ABSOLUTE_BAND
                else "absolute")


def band_for(target: float) -> float:
    """5 points absolute or 25% relative, whichever binds first.

    A class targeted at 5% cannot breach a 5pp absolute band even if it goes to
    zero, so the absolute band alone leaves small sleeves permanently
    unmanaged. A class targeted at 50% would need a 12.5pp move under the
    relative band alone, which is a larger deviation than the target is worth
    defending to.
    """
    if not target:
        return ABSOLUTE_BAND
    return min(ABSOLUTE_BAND, target * RELATIVE_BAND)


@dataclass
class Allocation:
    total: float
    sleeves: list[Sleeve] = field(default_factory=list)
    inv: Inventory = field(default_factory=Inventory)
    target_sum: float = 0.0
    findings: list[str] = field(default_factory=list)

    @property
    def breached(self) -> list[Sleeve]:
        return [s for s in self.sleeves if s.breached]

    @property
    def in_band(self) -> list[Sleeve]:
        return [s for s in self.sleeves if not s.breached]

    @property
    def target_equity(self) -> float:
        return sum(s.target for s in self.sleeves if s.asset_class in EQUITY_CLASSES)

    @property
    def actual_equity(self) -> float:
        return sum(s.share for s in self.sleeves if s.asset_class in EQUITY_CLASSES)


def review_allocation(rows: list[dict], target: dict[str, float] | None) -> Allocation:
    """Compare the recorded target against what is actually held."""
    inv = inventory(rows)
    actual = inv.by_class()
    target = {k: float(v) for k, v in (target or {}).items()}
    a = Allocation(total=inv.total, inv=inv, target_sum=sum(target.values()))

    for cls in sorted(set(target) | set(actual)):
        value = actual.get(cls, 0.0)
        a.sleeves.append(Sleeve(
            asset_class=cls,
            target=target.get(cls, 0.0),
            value=value,
            share=(value / inv.total) if inv.total else 0.0,
        ))

    if abs(a.target_sum - 1.0) > 0.005:
        a.findings.append(
            f"**The recorded target sums to {a.target_sum:.1%}, not 100%.** "
            "Nothing here renormalises it — a target that does not add up is a "
            "recording error, and scaling it silently would invent a policy "
            "nobody chose. Fix `portfolio.target_allocation` before reading the "
            "drift column."
        )

    if inv.unclassified:
        a.findings.append(
            f"**{_money(inv.unclassified_value)} across "
            f"{len(inv.unclassified)} holding(s) has no `asset_class`** and is "
            "excluded from every figure above, including the denominator. "
            "Unknown is not 'other': an allocation table that quietly absorbs "
            "unclassified money is wrong in a direction nobody can see. Name "
            f"the class on: {', '.join(n for n, _ in inv.unclassified)}."
        )

    for name, stated, summed in inv.mismatched:
        a.findings.append(
            f"`{name}` records {_money(stated)} but its `holdings` sum to "
            f"{_money(summed)}. The sub-holdings are used and the row total is "
            "ignored; reconcile them."
        )

    if inv.earmarked:
        ear = sum(v for _, v in inv.earmarked)
        a.findings.append(
            f"{_money(ear)} in earmarked account(s) "
            f"({', '.join(n for n, _ in inv.earmarked)}) is excluded. Money "
            "committed to a dated obligation has its own glide path and its own "
            "deadline; counting it as household equity overstates how much risk "
            "this household can actually carry."
        )

    over = [s for s in a.breached if s.drift > 0]
    under = [s for s in a.breached if s.drift < 0]
    if a.breached:
        a.findings.append(
            f"**{len(a.breached)} of {len(a.sleeves)} classes are outside "
            "their band.** Overweight: "
            + (", ".join(f"{s.asset_class} {s.drift:+.1%}" for s in over) or "none")
            + ". Underweight: "
            + (", ".join(f"{s.asset_class} {s.drift:+.1%}" for s in under) or "none")
            + ". What to do about it is `rebalancing-rules`, which is a "
            "separate decision from whether the target itself is right."
        )
    elif a.sleeves:
        a.findings.append(
            "**Every class is inside its band.** No action — and specifically, "
            "no action is the correct action, not a deferral of one. The bands "
            "exist so that small drift does not become a recurring judgement."
        )
    return a


# ── glide path ──────────────────────────────────────────────────────────────


@dataclass
class Glide:
    years: float | None
    reference: float | None
    low: float | None
    high: float | None
    actual: float | None
    findings: list[str] = field(default_factory=list)

    @property
    def known(self) -> bool:
        return self.reference is not None

    @property
    def within(self) -> bool | None:
        if self.actual is None or self.low is None:
            return None
        return self.low <= self.actual <= self.high


def years_to_retirement(planned_age: float | None, current_age: float | None) -> float | None:
    if planned_age is None or current_age is None:
        return None
    return max(0.0, float(planned_age) - float(current_age))


def glide_path(*, years: float | None, actual_equity: float | None) -> Glide:
    """A reference equity band for the horizon, and where the household sits.

    Horizon, not age. Age is a proxy for horizon and a poor one — two
    forty-year-olds retiring at 55 and at 70 have very different capacities to
    wait out a drawdown, and the second one is the one the age-based rules of
    thumb get wrong.
    """
    if years is None:
        g = Glide(None, None, None, None, actual_equity)
        g.findings.append(
            "**Horizon cannot be determined**, so no glide-path reference is "
            "offered. Record `retirement.planned_retirement_age` and the "
            "primary member's `age`. A guessed horizon produces a confident "
            "equity target, and the horizon is the single input it is most "
            "sensitive to."
        )
        return g

    ref = min(MAX_EQUITY_SHARE,
              max(MIN_EQUITY_SHARE, GLIDE_BASE_EQUITY + GLIDE_EQUITY_PER_YEAR * years))
    g = Glide(years, ref, max(0.0, ref - GLIDE_BAND), min(1.0, ref + GLIDE_BAND),
              actual_equity)

    g.findings.append(
        f"At a **{years:.0f}-year horizon** the reference equity share is "
        f"{g.low:.0%}–{g.high:.0%}. This is a convention, not a calculation: "
        "published glide paths disagree with each other by about this much at "
        "any given age, which is why it is reported as a band. Anywhere inside "
        "it is a defensible policy; the width is the honest part."
    )

    if actual_equity is None:
        g.findings.append(
            "The current equity share could not be computed, so there is "
            "nothing to compare the band against."
        )
    elif actual_equity > g.high:
        g.findings.append(
            f"Held equity is **{actual_equity:.0%}**, above the band. That is a "
            "choice a household can make deliberately — it is not a choice to "
            "make by not having looked."
        )
    elif actual_equity < g.low:
        g.findings.append(
            f"Held equity is **{actual_equity:.0%}**, below the band. Over a "
            f"{years:.0f}-year horizon the dominant risk is not a drawdown, it "
            "is inflation quietly removing the purchasing power of the "
            "non-equity half while it waits."
        )
    else:
        g.findings.append(
            f"Held equity is **{actual_equity:.0%}**, inside the band. The "
            "allocation and the horizon agree."
        )

    if years <= NEAR_RETIREMENT_YEARS:
        g.findings.append(
            f"**Inside {NEAR_RETIREMENT_YEARS} years of the target date, "
            "sequence-of-returns risk displaces expected return as the thing "
            "the allocation has to survive.** The relevant question stops being "
            "'what compounds best' and becomes 'how many years of spending can "
            "be funded without selling equity into a fall'. A single-point "
            "equity share does not answer that; how the non-equity part is "
            "laddered against the first few years of withdrawals does."
        )
    return g


# ── asset location ──────────────────────────────────────────────────────────


@dataclass
class Location:
    inv: Inventory
    findings: list[str] = field(default_factory=list)

    def total_in(self, account_types: frozenset[str]) -> float:
        return sum(h.value for h in self.inv.holdings
                   if h.account_type in account_types)


def review_location(inv: Inventory) -> Location:
    """Which account type holds which asset class — the unexamined half.

    Location is not allocation. Moving a bond fund from a taxable account to a
    401(k) changes nothing about the household's risk and everything about its
    after-tax return, which is exactly why it goes unexamined: no number on any
    statement moves.

    The ordering this encodes: income-producing assets into tax-deferred, where
    their annual ordinary-income tax drag disappears; the highest-expected-return
    assets into Roth or HSA, where the growth is never taxed at all.
    """
    loc = Location(inv)

    if inv.untyped:
        v = sum(x for _, x in inv.untyped)
        loc.findings.append(
            f"**{_money(v)} has an asset class but no `account_type`**, so its "
            "location cannot be judged at all "
            f"({', '.join(sorted({n for n, _ in inv.untyped}))}). This is the "
            "weakest input in this report: without it, half the analysis is "
            "unavailable and the half that runs is computed over a subset."
        )

    taxable_income_assets = sum(
        h.value for h in inv.holdings
        if h.asset_class in INCOME_CLASSES and h.account_type == TAXABLE)
    sheltered_equity = sum(
        h.value for h in inv.holdings
        if h.asset_class in EQUITY_CLASSES and h.account_type == TAX_DEFERRED)

    if taxable_income_assets and sheltered_equity:
        swap = min(taxable_income_assets, sheltered_equity)
        loc.findings.append(
            f"**{_money(taxable_income_assets)} of income-producing assets sit "
            f"in taxable accounts while {_money(sheltered_equity)} of equity "
            "sits in tax-deferred ones.** Up to "
            f"{_money(swap)} of that is a straight swap: the same total "
            "allocation, the same risk, the interest no longer taxed annually "
            "at ordinary rates, and the equity's return converted back into "
            "deferred capital gain. Nothing on any statement changes size."
        )
    elif taxable_income_assets and not sheltered_equity:
        loc.findings.append(
            f"{_money(taxable_income_assets)} of income-producing assets is in "
            "taxable accounts with no equity in tax-deferred to swap against. "
            "The fix is a future one: direct new tax-deferred contributions to "
            "bonds before selling anything, because a swap costs nothing and a "
            "sale can cost tax."
        )
    elif sum(h.value for h in inv.holdings if h.asset_class in INCOME_CLASSES):
        loc.findings.append(
            "**Income-producing assets are already held in sheltered "
            "accounts.** This is the correct placement and worth recording as "
            "policy so that the next contribution does not quietly undo it."
        )

    never_taxed = sum(h.value for h in inv.holdings if h.never_taxed)
    if not never_taxed:
        loc.findings.append(
            "**No Roth or HSA assets are recorded.** The account whose growth "
            "is never taxed is the one that should hold the highest-expected-"
            "return assets, and this household has nowhere to put them. That "
            "is a contribution-space question before it is a location "
            "question — see `contribution-space-audit`."
        )
    else:
        nt_equity = sum(h.value for h in inv.holdings
                        if h.never_taxed and h.asset_class in EQUITY_CLASSES)
        share = nt_equity / never_taxed if never_taxed else 0.0
        overall = inv.equity_share or 0.0
        if share < overall:
            loc.findings.append(
                f"Roth/HSA holdings are {share:.0%} equity against "
                f"{overall:.0%} for the portfolio as a whole. The account whose "
                "growth is never taxed is holding the assets least likely to "
                "grow. Reversing that changes no risk and no allocation."
            )
        else:
            loc.findings.append(
                f"Roth/HSA holdings are {share:.0%} equity against "
                f"{overall:.0%} overall — the highest-growth assets are in the "
                "account where growth is never taxed. Correct as it stands."
            )

    loc.findings.append(
        "Location is worth doing **only while the allocation stays fixed.** "
        "Using it as a reason to change the mix — 'more equity because it is in "
        "the Roth' — converts a free improvement into a risk decision made for "
        "a tax reason."
    )
    return loc


# ── rebalancing ─────────────────────────────────────────────────────────────

POLICY_BANDS = "bands"
POLICY_CALENDAR = "calendar"
POLICY_BOTH = "bands_and_calendar"
POLICIES = (POLICY_BANDS, POLICY_CALENDAR, POLICY_BOTH)


@dataclass
class Trade:
    asset_class: str
    #: Positive is a purchase, negative is a sale.
    amount: float
    breached: bool
    #: Value of this class held in accounts where a sale realises nothing.
    free_to_sell: float = 0.0


@dataclass
class Plan:
    policy: str | None
    alloc: Allocation
    trades: list[Trade] = field(default_factory=list)
    contributions: float | None = None
    next_review: _facts.Deadline | None = None
    findings: list[str] = field(default_factory=list)

    @property
    def buys(self) -> float:
        return sum(t.amount for t in self.trades if t.amount > 0)

    @property
    def sells(self) -> float:
        return -sum(t.amount for t in self.trades if t.amount < 0)

    @property
    def funded_by_contributions(self) -> float:
        return min(self.buys, self.contributions or 0.0)

    @property
    def free_capacity(self) -> float:
        """Sales that realise no taxable gain — sheltered accounts, and cash."""
        return sum(min(-t.amount, t.free_to_sell) for t in self.trades if t.amount < 0)

    @property
    def taxable_sale_needed(self) -> float:
        return max(0.0, self.buys - self.funded_by_contributions - self.free_capacity)

    @property
    def triggered(self) -> bool:
        return bool(self.alloc.breached)


def rebalance_plan(
    alloc: Allocation,
    *,
    policy: str | None,
    last_reviewed=None,
    as_of: _dt.date | None = None,
    annual_contributions: float | None = None,
) -> Plan:
    """What the recorded rule says to do now, and what it would cost.

    The finding this exists to produce: a correction made in a taxable account
    realises gains, so the rule should exhaust new contributions and sheltered
    accounts *first* and treat a taxable sale as the last resort rather than the
    default. Most households discover this ordering after the tax bill.
    """
    p = Plan(policy=policy, alloc=alloc, contributions=annual_contributions)

    for s in alloc.sleeves:
        amount = (s.target - s.share) * alloc.total
        free = 0.0
        if amount < 0:
            # Sheltered sales realise nothing. Neither does spending down cash,
            # in any account — its basis is its value.
            free = alloc.inv.value_in(s.asset_class, SHELTERED)
            if s.asset_class == "cash":
                free = s.value
        p.trades.append(Trade(s.asset_class, amount, s.breached, free))

    if policy not in POLICIES:
        p.findings.append(
            "**No rebalancing policy is recorded.** That is not neutral — it "
            "means the decision gets made afresh each time someone looks at the "
            "portfolio, which is exactly when it is hardest to make well. The "
            "choice is between a band rule and a calendar rule, and either one "
            "beats deciding in the moment. Set `portfolio.rebalancing.policy`."
        )
    elif policy == POLICY_CALENDAR:
        p.findings.append(
            f"**Calendar policy, every {CALENDAR_MONTHS} months.** Its virtue "
            "is that the date decides rather than the portfolio, so it cannot "
            "become market timing. Its cost is that it trades when nothing has "
            "moved and does nothing when something has."
        )
    else:
        p.findings.append(
            f"**Band policy: {ABSOLUTE_BAND:.0%} absolute or "
            f"{RELATIVE_BAND:.0%} relative, whichever binds first.** Checked "
            f"every {BAND_CHECK_MONTHS} months. The absolute band alone never "
            "fires on a small sleeve — a class targeted at 5% would have to "
            "disappear entirely — and the relative band alone tolerates a "
            "12.5pp move in a 50% class. Each covers the other's blind spot."
        )

    if last_reviewed is not None:
        months = CALENDAR_MONTHS if policy in (POLICY_CALENDAR, POLICY_BOTH) else BAND_CHECK_MONTHS
        due = _add_months(_facts._as_date(last_reviewed), months)
        p.next_review = _facts.deadline("next rebalancing review", due, as_of)
        if p.next_review.passed:
            p.findings.append(
                f"**The review is overdue** — due {due.isoformat()}, "
                f"{abs(p.next_review.days_remaining)} days ago. A rule nobody "
                "runs is indistinguishable from no rule."
            )
    else:
        p.findings.append(
            "`portfolio.rebalancing.last_reviewed` is not recorded, so whether "
            "the cadence is being kept cannot be determined. A policy without a "
            "date is an intention."
        )

    if not p.triggered:
        p.findings.append(
            "**Nothing is outside its band, so the rule says do nothing.** "
            "Rebalancing into a portfolio that is already where it should be "
            "pays spreads and possibly tax to change nothing."
        )
        return p

    p.findings.append(
        f"**{_money(p.buys)} of buying and {_money(p.sells)} of selling would "
        "restore the target** — about "
        f"{(p.buys / alloc.total if alloc.total else 0):.1%} of the portfolio. "
        "That is the size of the correction, not an instruction: which holdings "
        "and which lots is a portfolio-tool question and deliberately not "
        "answered here."
    )

    if annual_contributions:
        p.findings.append(
            f"**Direct the next {_money(min(p.buys, annual_contributions))} of "
            f"contributions to the underweight classes first.** Buying with new "
            "money corrects the drift without selling anything, which means "
            "without realising a single dollar of gain. At "
            f"{_money(annual_contributions)}/yr of contributions this "
            + ("covers the entire correction."
               if annual_contributions >= p.buys
               else f"covers {annual_contributions / p.buys:.0%} of it.")
        )
    else:
        p.findings.append(
            "Annual contributions are not recorded. They are the cheapest "
            "rebalancing tool available — new money buys the underweight class "
            "without selling anything — and leaving them out of the plan "
            "understates how much of the correction is free."
        )

    if p.taxable_sale_needed <= 0:
        p.findings.append(
            "**The whole correction can be made without realising a taxable "
            "gain**, using contributions, sheltered accounts, and cash. Selling "
            "inside a tax-deferred or Roth account is not a taxable event, so "
            "the correction is free there; doing the identical trade in the "
            "taxable account is not."
        )
    else:
        p.findings.append(
            f"**{_money(p.taxable_sale_needed)} would still have to come from a "
            "taxable sale** after contributions, sheltered accounts and cash "
            "are exhausted. That is the part with a tax cost attached, and it "
            "is the part to do last, slowly, and with the holding period "
            "checked. Whether that specific sale is worth its tax is a "
            "lot-level question this skill does not answer — but note that "
            "tolerating a little drift is a legitimate answer to it, which is "
            "why the band is a band and not a target."
        )

    p.findings.append(
        "**Order of operations, in cost order:** new contributions → "
        "dividends and interest redirected rather than reinvested → sales "
        "inside sheltered accounts → cash → taxable sales last. Most "
        "households run this list backwards because the taxable account is the "
        "one they look at."
    )
    return p


def _add_months(d: _dt.date | None, months: int) -> _dt.date | None:
    if d is None:
        return None
    y, m = divmod(d.month - 1 + months, 12)
    return _dt.date(d.year + y, m + 1, min(d.day, 28))


# ── wash-sale policy ────────────────────────────────────────────────────────


@dataclass
class Exclusion:
    ticker: str
    reason: str | None
    sold_on: _dt.date | None
    source: str | None

    def clear_on(self, *, continuous: bool) -> _dt.date | None:
        """The first day a purchase is safe, or None if it cannot be known."""
        if continuous:
            return None
        if self.sold_on is None:
            return None
        return self.sold_on + _dt.timedelta(days=WASH_SALE_WINDOW_DAYS + 1)


@dataclass
class AccountCoverage:
    name: str
    account_type: str | None
    #: True, False, or None for "nobody has recorded whether it is".
    covered: bool | None

    @property
    def is_retirement(self) -> bool:
        return self.account_type in IRA_ACCOUNTS

    @property
    def gap(self) -> bool:
        """Unknown counts as a gap. Unknown is not covered."""
        return self.covered is not True


@dataclass
class WashSalePolicy:
    exclusions: list[Exclusion] = field(default_factory=list)
    accounts: list[AccountCoverage] = field(default_factory=list)
    provider: str | None = None
    continuous: bool | None = None
    spouse_accounts_covered: bool | None = None
    as_of: _dt.date | None = None
    findings: list[str] = field(default_factory=list)

    @property
    def gaps(self) -> list[AccountCoverage]:
        return [a for a in self.accounts if a.gap]

    @property
    def retirement_gaps(self) -> list[AccountCoverage]:
        return [a for a in self.gaps if a.is_retirement]

    @property
    def covered_count(self) -> int:
        return sum(1 for a in self.accounts if a.covered is True)


def wash_sale_policy(
    excluded: list[dict] | None,
    rows: list[dict] | None,
    *,
    as_of: _dt.date | None,
    provider: str | None = None,
    continuous: bool | None = None,
    spouse_accounts_covered: bool | None = None,
) -> WashSalePolicy:
    """The standing rule: what may not be bought, where, and until when.

    This is a policy, not a harvest. It never proposes selling anything, never
    values a loss, and never picks a replacement security — those need lots and
    prices. What it produces is a list the household hands to every account it
    controls, and a statement of which accounts are actually honouring it.
    """
    p = WashSalePolicy(provider=provider, continuous=continuous,
                       spouse_accounts_covered=spouse_accounts_covered,
                       as_of=as_of)

    for e in excluded or []:
        p.exclusions.append(Exclusion(
            ticker=str(e.get("ticker") or "?"),
            reason=e.get("reason"),
            sold_on=_facts._as_date(e.get("sold_on")),
            source=e.get("source"),
        ))

    for row in rows or []:
        if row.get("account_type") is None and row.get("wash_sale_policy_applied") is None:
            continue
        p.accounts.append(AccountCoverage(
            name=row.get("name") or "account",
            account_type=row.get("account_type"),
            covered=row.get("wash_sale_policy_applied"),
        ))

    p.findings.append(
        f"**The window is {WASH_SALE_WINDOW_DAYS} days before the sale and "
        f"{WASH_SALE_WINDOW_DAYS} days after it — {WASH_SALE_TOTAL_DAYS} days "
        "in total.** The half that gets missed is the one before, because a "
        "purchase that has already happened cannot be undone once the loss is "
        "taken. A dividend reinvestment, an automatic monthly contribution, or "
        "a rebalancing buy inside that window is a purchase like any other."
    )

    p.findings.append(
        "**The test is *substantially identical*, not identical.** A different "
        "fund tracking the same index is the case everyone argues about; the "
        "same fund in a different account, or the fund's own ETF share class, "
        "is not arguable at all. A policy written against tickers is a policy "
        "against the easy half of the rule — write it against the exposure."
    )

    p.findings.append(
        "**The rule spans every account the household controls, not just the "
        "one holding the loss.** Both spouses, every broker, every retirement "
        "account. Nothing reconciles these for you: each broker reports wash "
        "sales only within its own accounts, so a cross-broker wash sale is "
        "invisible on both 1099-Bs and the taxpayer is still the one who owes "
        "it."
    )

    p.findings.append(
        "**A replacement purchase inside an IRA destroys the loss outright.** "
        "Under Rev. Rul. 2008-5 the loss is disallowed and — unlike an ordinary "
        "wash sale — **no basis adjustment is available**, because the IRA is "
        "not a taxpayer that can inherit it. An ordinary wash sale defers the "
        "loss; this one deletes it. It is the single most expensive wash-sale "
        "mistake available, and it is made by an automatic contribution "
        "nobody was watching."
    )

    if p.retirement_gaps:
        names = ", ".join(f"`{a.name}`" for a in p.retirement_gaps)
        unknown = [a for a in p.retirement_gaps if a.covered is None]
        p.findings.append(
            f"**{len(p.retirement_gaps)} retirement account(s) are not covered "
            f"by the exclusion list: {names}.** This is the finding. Every "
            "automatic contribution and every reinvested dividend in those "
            "accounts is a purchase, and if it lands on an excluded security "
            "within the window, the corresponding loss in the taxable account "
            "is gone permanently."
            + (" Coverage is recorded as unknown rather than false for "
               f"{len(unknown)} of them, which is the same exposure: nobody "
               "has checked." if unknown else "")
        )
    elif p.accounts:
        p.findings.append(
            f"All {p.covered_count} recorded account(s) are covered by the "
            "exclusion list, including the retirement accounts. That is the "
            "structure that makes continuous harvesting safe."
        )
    else:
        p.findings.append(
            "**No account coverage is recorded at all**, so whether the policy "
            "reaches beyond the harvesting account cannot be determined. Add "
            "`account_type` and `wash_sale_policy_applied` to every row of the "
            "balance sheet. Unknown here is not 'probably fine' — it is the "
            "exact state in which the expensive version of this mistake occurs."
        )

    if spouse_accounts_covered is False:
        p.findings.append(
            "**A spouse's accounts are recorded as not covered.** A purchase by "
            "a spouse triggers the wash sale just as one by the taxpayer does. "
            "If the accounts are at a different broker the trade is invisible "
            "to both 1099-Bs, which makes it more dangerous rather than less."
        )
    elif spouse_accounts_covered is None:
        p.findings.append(
            "Whether a spouse's accounts are covered is not recorded. Purchases "
            "by a spouse count; this needs an answer rather than an assumption."
        )

    if continuous:
        p.findings.append(
            f"**{provider or 'The direct-indexing provider'} harvests "
            "continuously, so the exclusion list is not a list with an expiry "
            "date — it is a standing prohibition.** A security sold at a loss "
            "this month may be sold again next month, restarting the window "
            "each time. Treat every name on the list as permanently unbuyable "
            "everywhere else until the provider removes it, and re-pull the "
            "list on a schedule rather than at the moment of a trade."
        )
    elif p.exclusions:
        dated = [e for e in p.exclusions if e.sold_on]
        undated = [e for e in p.exclusions if not e.sold_on]
        if dated and as_of:
            live = [e for e in dated if e.clear_on(continuous=False) > as_of]
            p.findings.append(
                f"{len(live)} of {len(dated)} dated exclusion(s) are still "
                f"inside the {WASH_SALE_WINDOW_DAYS}-day window as of "
                f"{as_of.isoformat()}. The rest have cleared and can be removed "
                "from the list — a list that only grows stops being read."
            )
        if undated:
            p.findings.append(
                f"{len(undated)} exclusion(s) carry no `sold_on` date, so when "
                "they clear cannot be determined. They stay on the list: an "
                "exclusion of unknown age is an exclusion."
            )

    if not p.exclusions:
        p.findings.append(
            "No excluded securities are recorded. If nothing has been harvested "
            "there is nothing to exclude and this policy is a precaution; if "
            "something has, the list is the missing input and the policy cannot "
            "be enforced without it."
        )

    p.findings.append(
        "**What this does not do:** it does not identify losses, value them, "
        "choose replacement securities, or decide when to harvest. Those need "
        "lot-level positions and live prices and belong to a portfolio tool. "
        "This is the standing rule that tool has to obey."
    )
    return p


def _money(x) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
