"""Debt payoff ordering, and the honest version of avalanche vs snowball.

Most treatments of this pick a side. Avalanche (highest rate first) minimises
interest and is mathematically correct. Snowball (smallest balance first) closes
accounts sooner and is what people actually finish.

**Both are shown, with the cost of the difference stated in dollars.** That
number is usually small, and it is the only honest way to present the choice:
if snowball costs a few hundred dollars and is the plan that gets completed, it
is the better plan. Telling someone their preference is irrational, and then
watching them abandon the optimal schedule, helps nobody.

The third option — don't accelerate, invest instead — is compared on an
**after-tax** basis, because deductible interest and taxable returns are not
directly comparable rates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

AVALANCHE = "avalanche"
SNOWBALL = "snowball"

#: Guard against a schedule that never terminates because minimum payments do
#: not cover interest.
MAX_MONTHS = 1200

#: Below this after-tax rate, accelerating payoff is competing with investing
#: rather than obviously beating it. Not a hard line — a rate this low is
#: usually a mortgage or a subsidised loan, where the answer turns on risk
#: tolerance rather than arithmetic.
INVEST_INSTEAD_THRESHOLD = 0.05


@dataclass
class Debt:
    name: str
    balance: float
    apr: float
    minimum_payment: float
    kind: str = "other"
    deductible: bool = False

    def after_tax_apr(self, marginal_rate: float) -> float:
        return self.apr * (1 - marginal_rate) if self.deductible else self.apr


@dataclass
class Schedule:
    method: str
    months: int
    total_interest: float
    order: list[str] = field(default_factory=list)
    terminated: bool = True


@dataclass
class DebtPlan:
    debts: list[Debt]
    avalanche: Schedule | None = None
    snowball: Schedule | None = None
    cost_of_snowball: float | None = None
    findings: list[str] = field(default_factory=list)

    @property
    def total_balance(self) -> float:
        return sum(d.balance for d in self.debts)

    @property
    def total_minimum(self) -> float:
        return sum(d.minimum_payment for d in self.debts)


def parse(rows: list[dict]) -> list[Debt]:
    out = []
    for r in rows or []:
        out.append(Debt(
            name=r.get("name") or "debt",
            balance=float(r.get("balance") or 0),
            apr=float(r.get("apr") or 0),
            minimum_payment=float(r.get("minimum_payment") or 0),
            kind=r.get("kind") or "other",
            deductible=bool(r.get("deductible_interest")),
        ))
    return [d for d in out if d.balance > 0]


def order_for(debts: list[Debt], method: str, marginal_rate: float = 0.0) -> list[Debt]:
    if method == AVALANCHE:
        return sorted(debts, key=lambda d: (-d.after_tax_apr(marginal_rate), d.balance))
    if method == SNOWBALL:
        return sorted(debts, key=lambda d: (d.balance, -d.apr))
    raise ValueError(f"unknown method {method!r}")


def simulate(
    debts: list[Debt],
    *,
    method: str,
    monthly_extra: float = 0.0,
    marginal_rate: float = 0.0,
) -> Schedule:
    """Month-by-month payoff. Minimums on everything, extra to the target."""
    working = [Debt(d.name, d.balance, d.apr, d.minimum_payment, d.kind, d.deductible)
               for d in debts]
    sequence = [d.name for d in order_for(working, method, marginal_rate)]
    by_name = {d.name: d for d in working}

    total_interest = 0.0
    months = 0
    while any(d.balance > 0 for d in working) and months < MAX_MONTHS:
        months += 1
        # Interest accrues first, on the balance carried into the month.
        for d in working:
            if d.balance > 0:
                interest = d.balance * d.apr / 12.0
                d.balance += interest
                total_interest += interest

        pool = monthly_extra
        for d in working:
            if d.balance <= 0:
                # A cleared debt frees its minimum for the next target. This
                # is the snowball effect, and it applies to both methods.
                pool += d.minimum_payment
                continue
            pay = min(d.minimum_payment, d.balance)
            d.balance -= pay
            pool += d.minimum_payment - pay

        for name in sequence:
            if pool <= 0:
                break
            d = by_name[name]
            if d.balance <= 0:
                continue
            pay = min(pool, d.balance)
            d.balance -= pay
            pool -= pay

    return Schedule(
        method=method,
        months=months,
        total_interest=total_interest,
        order=sequence,
        terminated=months < MAX_MONTHS,
    )


def plan(
    rows: list[dict],
    *,
    monthly_extra: float = 0.0,
    marginal_rate: float = 0.0,
    expected_return_apr: float | None = None,
) -> DebtPlan:
    debts = parse(rows)
    p = DebtPlan(debts=debts)
    if not debts:
        p.findings.append("No debts recorded with a balance. Nothing to order.")
        return p

    p.avalanche = simulate(debts, method=AVALANCHE, monthly_extra=monthly_extra,
                           marginal_rate=marginal_rate)
    p.snowball = simulate(debts, method=SNOWBALL, monthly_extra=monthly_extra,
                          marginal_rate=marginal_rate)

    if not p.avalanche.terminated:
        p.findings.append(
            "**The schedule does not terminate.** Minimum payments are not "
            "covering interest, so balances grow indefinitely. This is a "
            "restructuring problem, not an ordering one — the question is not "
            "which debt to target but how to increase total payment or "
            "renegotiate the terms."
        )
        return p

    p.cost_of_snowball = p.snowball.total_interest - p.avalanche.total_interest

    if p.cost_of_snowball <= 0:
        p.findings.append(
            "Both orderings cost the same here — the highest-rate debt is also "
            "the smallest, so there is no trade-off to make."
        )
    else:
        months_diff = p.snowball.months - p.avalanche.months
        p.findings.append(
            f"**Snowball costs {_money(p.cost_of_snowball)} more** than "
            f"avalanche"
            + (f" and finishes {months_diff} month(s) later" if months_diff else "")
            + ". That is the entire price of the psychologically easier "
            "schedule. If closing the first account quickly is what makes the "
            "plan get finished, it is worth paying — the optimal schedule that "
            "gets abandoned in month four is not optimal."
        )

    # ── invest instead ──────────────────────────────────────────────────
    if expected_return_apr is not None:
        low_rate = [d for d in debts
                    if d.after_tax_apr(marginal_rate) < expected_return_apr]
        if low_rate:
            names = ", ".join(f"`{d.name}` ({d.after_tax_apr(marginal_rate):.2%} "
                              f"after tax)" for d in low_rate)
            p.findings.append(
                f"**Paying these down early competes with investing rather "
                f"than beating it:** {names}, against an assumed "
                f"{expected_return_apr:.2%} expected return. The arithmetic "
                "favours investing — but the arithmetic is comparing a "
                "**certain** return against an **uncertain** one, which is not "
                "a like-for-like comparison. Paying down debt is risk-free and "
                "irreversible; investing is neither. Reasonable people choose "
                "the guaranteed return, and that is a preference, not an error."
            )
    else:
        p.findings.append(
            "No `assumptions.expected_return_apr` supplied, so the "
            "pay-down-versus-invest comparison is skipped rather than "
            "assumed."
        )

    high = [d for d in debts if d.apr >= 0.15]
    if high:
        p.findings.append(
            f"{len(high)} debt(s) at 15% or above. At those rates paying down "
            "beats essentially any investment on a risk-adjusted basis, and "
            "the ordering debate is academic — target them first under either "
            "method."
        )
    return p


def _money(x) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
