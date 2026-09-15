"""Employer concentration and equity compensation.

Both skills in this cluster are about one relationship: the household's
dependence on a single employer for income *and* assets *and* future income.

**The seam with a portfolio tool matters here more than anywhere else.** This
module answers "how exposed is this household, and what standing policy should
it adopt". It does not compute factor exposures, select tax lots, or decide
when to trade. Those need positions and market data and belong elsewhere. What
comes out of here is a *policy* — a rule the household adopts once — not a
transaction.

The load-bearing insight is that the exposures are **not independent**. Salary,
bonus, vesting equity, held employer stock and the unvested pipeline are all
one bet on one company. Stress-testing a layoff and a share-price decline
separately understates the risk badly, because the scenario that produces one
tends to produce the other.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

#: Conventional ceiling for a single position as a share of investable assets.
#: Widely cited, and it addresses only half the problem here — it says nothing
#: about income from the same source.
MAX_SINGLE_NAME_SHARE = 0.10

#: The share above which the position dominates the portfolio's outcome
#: regardless of anything else in it.
SEVERE_SINGLE_NAME_SHARE = 0.20

#: Income-side bands. A diversified portfolio does not help a household whose
#: entire income depends on one employer, so income concentration is scored
#: on its own and the worse of the two scores wins.
SEVERE_INCOME_SHARE = 0.90
ELEVATED_INCOME_SHARE = 0.60

#: Share decline assumed in the joint scenario. Not a forecast — a single
#: large-cap falling by half while its employer sheds staff is an ordinary
#: event, not a tail one, and it has happened to most well-known employers.
JOINT_SCENARIO_DECLINE = 0.50

#: Months of income loss assumed alongside it.
JOINT_SCENARIO_MONTHS = 12

#: A grant completing within this horizon is a near-term cliff worth planning
#: around rather than a distant one.
CLIFF_HORIZON_MONTHS = 24


@dataclass
class Exposure:
    employer: str
    income_from_employer: float
    total_income: float
    held_value: float
    unvested_value: float
    investable: float
    liquid: float
    monthly_spending: float
    findings: list[str] = field(default_factory=list)

    @property
    def income_share(self) -> float:
        return self.income_from_employer / self.total_income if self.total_income else 0.0

    @property
    def asset_share(self) -> float:
        return self.held_value / self.investable if self.investable else 0.0

    @property
    def total_at_risk(self) -> float:
        """Assets plus one year of employer income plus the unvested pipeline."""
        return self.held_value + self.unvested_value + self.income_from_employer

    @property
    def asset_severity(self) -> str:
        if self.asset_share >= SEVERE_SINGLE_NAME_SHARE:
            return "severe"
        if self.asset_share > MAX_SINGLE_NAME_SHARE:
            return "elevated"
        return "within_guideline"

    @property
    def income_severity(self) -> str:
        if self.income_share >= SEVERE_INCOME_SHARE:
            return "severe"
        if self.income_share >= ELEVATED_INCOME_SHARE:
            return "elevated"
        return "within_guideline"

    @property
    def severity(self) -> str:
        """The worse of the two, not the asset score alone.

        An earlier version reported only asset concentration, which labelled a
        household with a diversified portfolio and 100% of its income from one
        employer as "within guideline" — reassuring, and wrong. A diversified
        portfolio does not pay the mortgage when the salary stops.
        """
        order = ("within_guideline", "elevated", "severe")
        return max(self.asset_severity, self.income_severity, key=order.index)


@dataclass
class JointScenario:
    decline: float
    months: int
    stock_loss: float
    income_loss: float
    unvested_loss: float
    liquid_after: float
    runway_months: float
    total_loss: float


def joint_scenario(e: Exposure) -> JointScenario:
    """Share price falls and the job ends, together — because they do.

    Modelled jointly and never as two separate tests. Two independent stress
    tests, each survivable, can describe a combined event that is not.
    """
    stock_loss = e.held_value * JOINT_SCENARIO_DECLINE
    income_loss = e.income_from_employer * (JOINT_SCENARIO_MONTHS / 12.0)
    unvested_loss = e.unvested_value
    liquid_after = max(0.0, e.liquid - stock_loss)
    return JointScenario(
        decline=JOINT_SCENARIO_DECLINE,
        months=JOINT_SCENARIO_MONTHS,
        stock_loss=stock_loss,
        income_loss=income_loss,
        unvested_loss=unvested_loss,
        liquid_after=liquid_after,
        runway_months=(liquid_after / e.monthly_spending) if e.monthly_spending else float("inf"),
        total_loss=stock_loss + income_loss + unvested_loss,
    )


def assess_exposure(
    *,
    employer: str,
    income_from_employer: float,
    total_income: float,
    held_value: float,
    unvested_value: float,
    investable: float,
    liquid: float,
    monthly_spending: float,
    sell_at_vest: bool | None,
) -> Exposure:
    e = Exposure(
        employer=employer,
        income_from_employer=income_from_employer,
        total_income=total_income,
        held_value=held_value,
        unvested_value=unvested_value,
        investable=investable,
        liquid=liquid,
        monthly_spending=monthly_spending,
    )

    # Fires on income concentration alone. Gating it on the asset share as
    # well suppressed it for exactly the household that needs it most: one
    # with a sensibly diversified portfolio and a single source of income.
    if e.income_share >= SEVERE_INCOME_SHARE and (e.held_value or e.unvested_value):
        e.findings.append(
            f"**{e.income_share:.0%} of household income and {e.asset_share:.0%} "
            f"of investable assets depend on {employer}, and "
            f"{_money(e.total_at_risk)} in total.** These are not two "
            "exposures, they are one. The event that ends the income is the "
            "same class of event that reprices the stock, so any analysis that "
            "stress-tests them separately understates the risk."
        )

    if e.income_severity == "severe":
        e.findings.append(
            f"**Income concentration is the binding constraint here, not the "
            f"portfolio.** {e.income_share:.0%} of household income comes from "
            f"one employer. No amount of diversification on the asset side "
            "changes that, and it is not fixable by selling anything — the "
            "levers are a second income, a larger buffer, and not adding "
            "employer stock on top of it."
        )
    elif e.income_severity == "elevated":
        e.findings.append(
            f"{e.income_share:.0%} of household income comes from one "
            "employer. Worth naming alongside the asset side rather than "
            "treating the portfolio as the whole picture."
        )

    if e.asset_severity == "severe":
        e.findings.append(
            f"A single position at {e.asset_share:.0%} of investable assets is "
            f"past the point where it dominates the portfolio's outcome. "
            f"Whatever else is held, the result is mostly a bet on {employer}."
        )
    elif e.asset_severity == "elevated":
        e.findings.append(
            f"{e.asset_share:.0%} in a single name, against a conventional "
            f"{MAX_SINGLE_NAME_SHARE:.0%} guideline. The guideline addresses "
            "only half of this — it says nothing about income from the same "
            "source, which is the larger exposure here."
        )
    else:
        e.findings.append(
            f"Holdings are {e.asset_share:.0%} of investable assets, within the "
            f"{MAX_SINGLE_NAME_SHARE:.0%} guideline. The income concentration "
            "is the remaining question."
        )

    if sell_at_vest is False:
        e.findings.append(
            "**No sell-at-vest policy is in force.** Vested shares are a "
            "decision made afresh every quarter, which in practice means they "
            "accumulate. Holding vested shares is mathematically identical to "
            "receiving the cash and immediately buying the employer's stock "
            "with it — an act nobody would perform deliberately at this "
            "concentration. Adopt the policy once so it stops being a "
            "recurring judgement call made under a disposition effect."
        )
    elif sell_at_vest is None:
        e.findings.append(
            "Whether a sell-at-vest policy exists is not recorded. It is the "
            "single highest-leverage decision in this whole area, precisely "
            "because it is made once rather than repeatedly."
        )
    else:
        e.findings.append(
            "**Sell-at-vest is in force.** This is the right structure: it "
            "stops the concentration growing without requiring a market view, "
            "and removes a recurring decision."
        )

    e.findings.append(
        "Diversifying is not a market call. Selling does not predict the "
        "shares will fall — it declines to keep making a large undiversified "
        "bet whose downside is correlated with unemployment. If the holding "
        "would not be bought today at today's price with cash, holding it is "
        "the same decision."
    )
    return e


# ── equity compensation and the cliff ───────────────────────────────────────


@dataclass
class Grant:
    id: str
    annual_value: float
    completes: _dt.date | None

    def months_remaining(self, today: _dt.date) -> float | None:
        if self.completes is None:
            return None
        return (self.completes - today).days / 30.44


@dataclass
class VestingOutlook:
    run_rate: float
    steady_state: float
    delta: float
    next_cliff: _dt.date | None
    grants: list[Grant] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    @property
    def drop_share(self) -> float:
        return self.delta / self.run_rate if self.run_rate else 0.0


def vesting_outlook(
    grants_raw: list[dict],
    *,
    today: _dt.date,
    horizon_months: int = CLIFF_HORIZON_MONTHS,
) -> VestingOutlook:
    grants = []
    for g in grants_raw or []:
        c = g.get("completes")
        if isinstance(c, _dt.datetime):
            c = c.date()
        elif isinstance(c, str):
            try:
                c = _dt.date.fromisoformat(c)
            except ValueError:
                c = None
        grants.append(Grant(g.get("id") or "grant",
                            float(g.get("annual_value") or 0), c))

    run_rate = sum(g.annual_value for g in grants)
    expiring = [g for g in grants
                if g.months_remaining(today) is not None
                and 0 <= g.months_remaining(today) <= horizon_months]
    delta = sum(g.annual_value for g in expiring)
    next_cliff = min((g.completes for g in expiring), default=None)

    o = VestingOutlook(
        run_rate=run_rate,
        steady_state=run_rate - delta,
        delta=delta,
        next_cliff=next_cliff,
        grants=grants,
    )

    if delta > 0 and next_cliff:
        first = [g for g in expiring if g.completes == next_cliff]
        first_delta = sum(g.annual_value for g in first)
        steps = (f"in {len(expiring)} steps, the first on "
                 f"{next_cliff.isoformat()} ({_money(first_delta)}/yr)"
                 if len(expiring) > 1
                 else f"on {next_cliff.isoformat()}")
        o.findings.append(
            f"**The current run rate is not the steady state.** "
            f"{_money(delta)}/yr ({o.drop_share:.0%} of equity income) comes "
            f"from grant(s) completing within {horizon_months} months — "
            f"{steps}. Without refresh grants of similar size, equity income "
            f"falls to {_money(o.steady_state)}."
        )
        o.findings.append(
            "**Plan against the lower figure.** Sustaining the current rate "
            "assumes refresh grants continue at their present size, which is a "
            "discretionary decision by someone else, made annually, and "
            "correlated with exactly the conditions in which it is least "
            "likely — a weak share price or a cost-reduction cycle."
        )
    elif not grants:
        o.findings.append(
            "No grants recorded. If equity is part of compensation, record the "
            "vest schedule — the cliff when a multi-year grant completes is "
            "invisible in an annual income figure."
        )
    else:
        o.findings.append(
            f"No grant completes within {horizon_months} months. The current "
            f"run rate of {_money(run_rate)} is durable over that horizon."
        )
    return o


def _money(x) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
