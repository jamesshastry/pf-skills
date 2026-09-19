"""Deterministic household scenarios on one reconciled monthly cash spine.

The engine applies explicit, typed events to a named cash-flow baseline.  It
keeps cash, marketable assets, retirement assets, illiquid assets and debt
separate so a transfer cannot masquerade as wealth creation and a terminally
solvent path cannot hide an intra-year cash failure.

It does not infer taxes, basis, benefits, severance, spending cuts or future
pay.  It never mutates facts, fetches data, executes a transaction, or treats a
hypothesis as an observed fact.  Results are deterministic projections, not
probabilities.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, replace
from typing import Any

from . import cash as C
from . import facts as F
from . import retirement as R
from . import timeseries as T

SCENARIO_MODEL_VERSION = "scenario-v1"

EVENT_TYPES = (
    "employment_loss",
    "compensation_change",
    "cash_receipt",
    "asset_receipt",
    "asset_price_change",
    "one_time_expense",
    "recurring_expense_change",
    "debt_payoff",
    "portfolio_withdrawal",
    "home_purchase",
    "portfolio_contribution",
)

#: Same-month precedence.  Receipts and income changes land before expenses;
#: withdrawals and debt payoff precede purchases; voluntary investing is last.
#: Event order is data, not YAML order, so two equivalent files reconcile alike.
EVENT_ORDER = {
    "cash_receipt": 10,
    "asset_receipt": 10,
    "employment_loss": 20,
    "compensation_change": 20,
    "asset_price_change": 30,
    "one_time_expense": 40,
    "recurring_expense_change": 40,
    "portfolio_withdrawal": 50,
    "debt_payoff": 60,
    "home_purchase": 70,
    "portfolio_contribution": 80,
}

OBJECTIVES = (
    "preserve_liquidity",
    "preserve_savings",
    "minimize_debt",
    "minimize_retirement_delay",
    "preserve_goal",
    "compare_only",
)


class ScenarioError(ValueError):
    """A scenario is incomplete, ambiguous or arithmetically impossible."""


def _amount(row: dict[str, Any], key: str, *, required: bool = False) -> float:
    value = row.get(key)
    if value is None:
        if required:
            raise ScenarioError(f"{row.get('id', 'event')}: {key} is required")
        return 0.0
    result = float(value)
    if not math.isfinite(result):
        raise ScenarioError(f"{row.get('id', 'event')}: {key} must be finite")
    return result


def _month(row: dict[str, Any], key: str, *, default: int | None = None) -> int | None:
    raw = row.get(key, default)
    if raw is None:
        return None
    value = int(raw)
    if value < 1:
        raise ScenarioError(f"{row.get('id', 'event')}: {key} must be >= 1")
    return value


@dataclass(frozen=True)
class ScenarioEvent:
    id: str
    type: str
    start_month: int
    duration_months: int | None = None
    person_id: str | None = None
    account_id: str | None = None
    source_event_id: str | None = None
    currency: str = "USD"
    basis: str = T.BASIS_NOMINAL
    # Cash and asset receipt fields.
    gross_amount: float | None = None
    after_tax_amount: float | None = None
    tax_reserve: float | None = None
    market_value: float | None = None
    cost_basis: float | None = None
    tax_rate: float | None = None
    transaction_cost: float = 0.0
    liquidate: bool = False
    asset_type: str | None = None
    holding_period: str | None = None
    restriction_status: str | None = None
    # Employment and compensation fields; all amounts are monthly unless named.
    after_tax_income_loss_monthly: float = 0.0
    after_tax_income_change_monthly: float = 0.0
    employee_contribution_loss_monthly: float = 0.0
    employer_match_loss_monthly: float = 0.0
    retirement_contribution_change_monthly: float = 0.0
    replacement_health_cost_monthly: float = 0.0
    severance_after_tax: float = 0.0
    severance_month: int | None = None
    unemployment_after_tax_monthly: float = 0.0
    benefit_start_month: int | None = None
    benefit_duration_months: int | None = None
    unvested_forfeiture: float = 0.0
    employer_stock_change: float | None = None
    # Generic expense/value/transfer fields.
    amount: float = 0.0
    amount_monthly: float = 0.0
    price_change: float | None = None
    target: str | None = None
    payoff_penalty: float = 0.0
    # Home purchase fields.
    purchase_price: float = 0.0
    down_payment: float = 0.0
    closing_cost: float = 0.0
    monthly_housing_cost_change: float = 0.0
    housing_adapter: bool = False
    label: str | None = None
    unknown_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not T._STABLE_ID.fullmatch(self.id):
            raise ScenarioError(f"invalid stable event id {self.id!r}")
        for name in ("person_id", "account_id", "source_event_id"):
            value = getattr(self, name)
            if value is not None and not T._ENTITY_ID.fullmatch(value):
                raise ScenarioError(f"{self.id}: invalid stable {name} {value!r}")
        if self.type not in EVENT_TYPES:
            raise ScenarioError(f"unknown event type {self.type!r}")
        if self.start_month < 1:
            raise ScenarioError("event start_month must be >= 1")
        if self.duration_months is not None and self.duration_months < 1:
            raise ScenarioError("event duration_months must be >= 1")
        if self.basis not in (T.BASIS_NOMINAL, T.BASIS_REAL):
            raise ScenarioError("event basis must be nominal or real")
        for name in (
            "transaction_cost", "after_tax_income_loss_monthly",
            "employee_contribution_loss_monthly", "employer_match_loss_monthly",
            "replacement_health_cost_monthly", "severance_after_tax",
            "unemployment_after_tax_monthly", "unvested_forfeiture", "amount",
            "payoff_penalty", "purchase_price", "down_payment", "closing_cost",
        ):
            if getattr(self, name) < 0:
                raise ScenarioError(f"{self.id}: {name} cannot be negative")
        for name in ("gross_amount", "after_tax_amount", "tax_reserve",
                     "market_value", "cost_basis"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ScenarioError(f"{self.id}: {name} cannot be negative")
        if self.tax_rate is not None and not 0 <= self.tax_rate <= 1:
            raise ScenarioError(f"{self.id}: tax_rate must be between zero and one")
        if (self.severance_month is not None
                and self.severance_month < self.start_month):
            raise ScenarioError(f"{self.id}: severance cannot precede job loss")
        if (self.benefit_start_month is not None
                and self.benefit_start_month < self.start_month):
            raise ScenarioError(f"{self.id}: benefits cannot precede job loss")
        if self.type == "employment_loss":
            if not self.person_id:
                raise ScenarioError(f"{self.id}: employment_loss needs person_id")
            if self.after_tax_income_loss_monthly <= 0:
                raise ScenarioError(
                    f"{self.id}: record after_tax_income_loss_monthly; taxes "
                    "will not be inferred from gross pay"
                )
        if self.type == "cash_receipt":
            if self.after_tax_amount is None:
                if self.gross_amount is None or self.tax_reserve is None:
                    raise ScenarioError(
                        f"{self.id}: cash receipt needs after_tax_amount or "
                        "gross_amount plus tax_reserve"
                    )
                if self.tax_reserve > self.gross_amount:
                    raise ScenarioError(f"{self.id}: tax reserve exceeds receipt")
            elif self.gross_amount is not None or self.tax_reserve is not None:
                if self.gross_amount is None or self.tax_reserve is None:
                    raise ScenarioError(
                        f"{self.id}: duplicate receipt totals need both gross "
                        "amount and tax reserve")
                if not math.isclose(
                        self.after_tax_amount, self.gross_amount - self.tax_reserve,
                        abs_tol=0.01):
                    raise ScenarioError(
                        f"{self.id}: after-tax receipt does not reconcile to "
                        "gross less tax reserve")
        if self.type == "asset_receipt":
            if self.market_value is None:
                raise ScenarioError(f"{self.id}: asset receipt needs market_value")
            if self.transaction_cost > self.market_value:
                raise ScenarioError(f"{self.id}: transaction cost exceeds asset value")
            if self.liquidate and (self.cost_basis is None or self.tax_rate is None):
                raise ScenarioError(
                    f"{self.id}: liquidation needs known cost_basis and tax_rate; "
                    "unknown basis is not zero"
                )
        if self.type == "asset_price_change":
            if self.price_change is None or self.price_change < -1:
                raise ScenarioError(f"{self.id}: price_change cannot exceed a total loss")
            if self.target not in ("marketable", "employer_stock"):
                raise ScenarioError(
                    f"{self.id}: asset price target must be marketable or employer_stock"
                )
        if self.employer_stock_change is not None and self.employer_stock_change < -1:
            raise ScenarioError(f"{self.id}: employer stock change cannot exceed a total loss")
        if self.type in ("portfolio_contribution", "portfolio_withdrawal",
                         "one_time_expense", "debt_payoff") and self.amount <= 0:
            raise ScenarioError(f"{self.id}: amount must be positive")
        if self.type == "home_purchase" and not self.housing_adapter:
            if self.purchase_price <= 0 or self.down_payment < 0:
                raise ScenarioError(f"{self.id}: invalid purchase price/down payment")
            if self.down_payment > self.purchase_price:
                raise ScenarioError(f"{self.id}: down payment exceeds purchase price")

    @property
    def end_month(self) -> int | None:
        if self.duration_months is None:
            return None
        return self.start_month + self.duration_months - 1

    def active(self, month: int) -> bool:
        return month >= self.start_month and (
            self.end_month is None or month <= self.end_month)

    @classmethod
    def from_dict(cls, row: dict[str, Any], *, currency: str) -> "ScenarioEvent":
        event_type = str(row.get("type") or "")
        unknown_fields: tuple[str, ...] = ()
        if event_type == "employment_loss":
            inspect = (
                "duration_months", "severance_after_tax",
                "unemployment_after_tax_monthly",
                "replacement_health_cost_monthly",
                "employee_contribution_loss_monthly",
                "employer_match_loss_monthly", "unvested_forfeiture",
                "employer_stock_change",
            )
            unknown_fields = tuple(key for key in inspect if key not in row)
        elif event_type == "asset_receipt":
            inspect = (
                "asset_type", "cost_basis", "holding_period",
                "restriction_status", "tax_rate", "transaction_cost",
            )
            unknown_fields = tuple(key for key in inspect if key not in row)
        return cls(
            id=str(row.get("id") or ""),
            type=event_type,
            start_month=_month(row, "start_month", default=1) or 1,
            duration_months=_month(row, "duration_months"),
            person_id=row.get("person_id"),
            account_id=row.get("account_id"),
            source_event_id=row.get("source_event_id"),
            currency=str(row.get("currency") or currency),
            basis=str(row.get("basis") or T.BASIS_NOMINAL),
            gross_amount=(None if row.get("gross_amount") is None
                          else _amount(row, "gross_amount")),
            after_tax_amount=(None if row.get("after_tax_amount") is None
                              else _amount(row, "after_tax_amount")),
            tax_reserve=(None if row.get("tax_reserve") is None
                         else _amount(row, "tax_reserve")),
            market_value=(None if row.get("market_value") is None
                          else _amount(row, "market_value")),
            cost_basis=(None if row.get("cost_basis") is None
                        else _amount(row, "cost_basis")),
            tax_rate=(None if row.get("tax_rate") is None
                      else _amount(row, "tax_rate")),
            transaction_cost=_amount(row, "transaction_cost"),
            liquidate=bool(row.get("liquidate", False)),
            asset_type=row.get("asset_type"),
            holding_period=row.get("holding_period"),
            restriction_status=row.get("restriction_status"),
            after_tax_income_loss_monthly=_amount(
                row, "after_tax_income_loss_monthly"),
            after_tax_income_change_monthly=_amount(
                row, "after_tax_income_change_monthly"),
            employee_contribution_loss_monthly=_amount(
                row, "employee_contribution_loss_monthly"),
            employer_match_loss_monthly=_amount(
                row, "employer_match_loss_monthly"),
            retirement_contribution_change_monthly=_amount(
                row, "retirement_contribution_change_monthly"),
            replacement_health_cost_monthly=_amount(
                row, "replacement_health_cost_monthly"),
            severance_after_tax=_amount(row, "severance_after_tax"),
            severance_month=_month(row, "severance_month"),
            unemployment_after_tax_monthly=_amount(
                row, "unemployment_after_tax_monthly"),
            benefit_start_month=_month(row, "benefit_start_month"),
            benefit_duration_months=_month(row, "benefit_duration_months"),
            unvested_forfeiture=_amount(row, "unvested_forfeiture"),
            employer_stock_change=(None if row.get("employer_stock_change") is None
                                   else _amount(row, "employer_stock_change")),
            amount=_amount(row, "amount"),
            amount_monthly=_amount(row, "amount_monthly"),
            price_change=(None if row.get("price_change") is None
                          else _amount(row, "price_change")),
            target=row.get("target"),
            payoff_penalty=_amount(row, "payoff_penalty"),
            purchase_price=_amount(row, "purchase_price"),
            down_payment=_amount(row, "down_payment"),
            closing_cost=_amount(row, "closing_cost"),
            monthly_housing_cost_change=_amount(
                row, "monthly_housing_cost_change"),
            housing_adapter=bool(row.get("housing_adapter", False)),
            label=row.get("label"),
            unknown_fields=unknown_fields,
        )


@dataclass(frozen=True)
class ScenarioSpec:
    id: str
    label: str
    as_of: dt.date
    baseline: str
    kind: str
    horizon_months: int
    objective: str | None
    currency: str
    basis: str
    events: tuple[ScenarioEvent, ...]
    essential_spending_annual: float | None = None
    liquidation_order: tuple[str, ...] = ()
    market_return_annual: float = 0.0
    retirement_return_annual: float = 0.0
    preliminary: bool = False

    def __post_init__(self) -> None:
        if not T._STABLE_ID.fullmatch(self.id):
            raise ScenarioError(f"invalid stable scenario id {self.id!r}")
        if self.kind not in ("scenario", "stress", "sensitivity"):
            raise ScenarioError(f"unknown scenario kind {self.kind!r}")
        if self.horizon_months < 1:
            raise ScenarioError("horizon_months must be positive")
        if self.objective is not None and self.objective not in OBJECTIVES:
            raise ScenarioError(f"unknown objective {self.objective!r}")
        if self.basis not in (T.BASIS_NOMINAL, T.BASIS_REAL):
            raise ScenarioError("scenario basis must be nominal or real")
        if self.essential_spending_annual is not None \
                and self.essential_spending_annual < 0:
            raise ScenarioError("essential_spending_annual cannot be negative")
        if self.market_return_annual < -1 or self.retirement_return_annual < -1:
            raise ScenarioError("annual return cannot be below a total loss")
        ids = [event.id for event in self.events]
        if len(ids) != len(set(ids)):
            raise ScenarioError("scenario event IDs must be unique")
        for event in self.events:
            if event.currency != self.currency or event.basis != self.basis:
                raise ScenarioError(
                    f"{event.id}: event currency/basis differs from scenario; "
                    "record an explicit conversion before combining them"
                )
            if event.start_month > self.horizon_months:
                raise ScenarioError(f"{event.id}: starts after scenario horizon")
            if event.severance_month is not None and event.severance_month > self.horizon_months:
                raise ScenarioError(f"{event.id}: severance is after scenario horizon")
        if len(self.liquidation_order) != len(set(self.liquidation_order)):
            raise ScenarioError("liquidation_order cannot repeat an account")
        self._validate_conflicts()

    def _validate_conflicts(self) -> None:
        homes: dict[int, list[str]] = {}
        flows: dict[tuple[int, str | None], set[str]] = {}
        employer_price: dict[int, list[str]] = {}
        for event in self.events:
            if event.type == "home_purchase":
                homes.setdefault(event.start_month, []).append(event.id)
            if event.type in ("portfolio_contribution", "portfolio_withdrawal"):
                flows.setdefault((event.start_month, event.account_id), set()).add(
                    event.type)
            if (event.type == "employment_loss" and
                    event.employer_stock_change is not None):
                employer_price.setdefault(event.start_month, []).append(event.id)
        employment = [event for event in self.events
                      if event.type == "employment_loss"]
        for index, first in enumerate(employment):
            for second in employment[index + 1:]:
                first_end = first.end_month or self.horizon_months
                second_end = second.end_month or self.horizon_months
                if (first.person_id == second.person_id
                        and first.start_month <= second_end
                        and second.start_month <= first_end):
                    raise ScenarioError(
                        "overlapping employment-loss bundles for one person "
                        "would double count the same shock")
            if event.type == "asset_price_change" and event.target == "employer_stock":
                employer_price.setdefault(event.start_month, []).append(event.id)
        duplicate_homes = [ids for ids in homes.values() if len(ids) > 1]
        if duplicate_homes:
            raise ScenarioError("multiple home purchases in one month are ambiguous")
        if any(len(types) > 1 for types in flows.values()):
            raise ScenarioError(
                "same-month contribution and withdrawal for one account are ambiguous"
            )
        if any(len(ids) > 1 for ids in employer_price.values()):
            raise ScenarioError(
                "employer stock is repriced more than once in the same month"
            )

    @classmethod
    def from_dict(cls, row: dict[str, Any], *, default_currency: str) -> "ScenarioSpec":
        currency = str(row.get("currency") or default_currency)
        basis = str(row.get("basis") or T.BASIS_NOMINAL)
        events = tuple(ScenarioEvent.from_dict(
            {**event, "basis": event.get("basis", basis)}, currency=currency)
            for event in row.get("events") or [])
        return cls(
            id=str(row.get("id") or ""),
            label=str(row.get("label") or row.get("id") or ""),
            as_of=T._date(row.get("as_of"), "scenario as_of"),
            baseline=str(row.get("baseline") or "current"),
            kind=str(row.get("kind") or "scenario"),
            horizon_months=int(row.get("horizon_months") or 0),
            objective=row.get("objective"),
            currency=currency,
            basis=basis,
            events=events,
            essential_spending_annual=(
                None if row.get("essential_spending_annual") is None
                else float(row["essential_spending_annual"])
            ),
            liquidation_order=tuple(
                str(x) for x in row.get("liquidation_order") or []),
            market_return_annual=float(row.get("market_return_annual") or 0),
            retirement_return_annual=float(
                row.get("retirement_return_annual") or 0),
            preliminary=bool(row.get("preliminary", False)),
        )


@dataclass(frozen=True)
class Baseline:
    as_of: dt.date
    currency: str
    basis: str
    name: str
    monthly_after_tax_income: float
    monthly_current_spending: float
    monthly_essential_spending: float | None
    monthly_employee_retirement_contribution: float
    monthly_employer_retirement_contribution: float
    monthly_other_outflows: float
    cash: float
    marketable: float
    retirement: float
    illiquid: float
    debt: float
    employer_stock: float
    employer_stock_in_marketable: bool
    unvested_equity: float
    emergency_floor: float
    annual_savings_floor: float
    current_age: int | None
    retirement_spending_annual: float
    source_fingerprint: str

    @property
    def net_worth(self) -> float:
        separate_employer_stock = (0.0 if self.employer_stock_in_marketable
                                   else self.employer_stock)
        return (self.cash + self.marketable + separate_employer_stock
                + self.retirement + self.illiquid - self.debt)


def baseline_from_facts(facts: dict[str, Any], name: str = "current") -> Baseline:
    """Reuse reconciled facts and the emergency/retirement domain boundaries."""
    scenario_rows = F._dig(facts, "cash_flow.scenarios") or []
    selected = next((row for row in scenario_rows
                     if row.get("kind") == name or row.get("label") == name
                     or row.get("id") == name), None)
    if selected is None:
        raise ScenarioError(f"cash-flow baseline {name!r} was not found")
    after_tax = selected.get("after_tax_cash_income_annual")
    if after_tax is None:
        gross = selected.get("gross_income_annual")
        taxes = selected.get("taxes_annual")
        if gross is None or taxes is None:
            raise ScenarioError(
                "baseline needs after_tax_cash_income_annual or gross income "
                "and taxes; no tax rate will be inferred"
            )
        after_tax = float(gross) - float(taxes)

    retirement_employee = (
        float(selected.get("retirement_contributions_annual") or 0)
        + float(selected.get("ira_contributions_annual") or 0)
    )
    retirement_employer = float(
        selected.get("employer_retirement_contributions_annual") or 0)
    current_spending = (
        float(selected.get("non_housing_spending_annual") or 0)
        + float(selected.get("other_committed_annual") or 0)
    )
    housing_status = F._dig(facts, "housing.status")
    if housing_status == "renting":
        current_spending += float(F._dig(facts, "housing.monthly_rent") or 0) * 12
    elif housing_status == "owning":
        purchase = F._dig(facts, "housing.purchase") or {}
        try:
            from . import housing_affordability as H  # noqa: PLC0415
            current_spending += H.owner_cash_cost(
                purchase, price=float(purchase.get("price") or 0)).gross_annual
        except Exception as exc:  # noqa: BLE001
            raise ScenarioError(f"owner housing baseline cannot reconcile: {exc}") from exc
    other_outflows = float(selected.get("other_payroll_deductions_annual") or 0)

    cash = 0.0
    marketable = 0.0
    illiquid = 0.0
    employer_stock = float(F._dig(facts, "equity_comp.held_value") or 0)
    in_balance_sheet = F._dig(
        facts, "equity_comp.held_value_in_balance_sheet")
    if employer_stock and in_balance_sheet is None:
        raise ScenarioError(
            "equity_comp.held_value_in_balance_sheet is required so employer "
            "stock is neither omitted nor counted twice")
    for row in F._dig(facts, "household.balance_sheet") or []:
        if row.get("pending"):
            continue
        if row.get("value") is None:
            raise ScenarioError(
                f"balance-sheet value is unknown for {row.get('id') or row.get('name') or '?'}")
        value = max(0.0, float(row.get("value") or 0)
                    - float(row.get("margin_debt") or 0))
        cls = row.get("liquidity_class")
        if cls == F.CASH_EQUIVALENT:
            cash += value
        elif cls == F.MARKETABLE:
            marketable += value
        elif row.get("retirement_eligible") is not True:
            illiquid += value
    retirement_assets = F.retirement_assets(facts)
    retirement = retirement_assets.included
    # Avoid counting a marketable taxable account in both buckets when it is
    # explicitly retirement-eligible: scenario liquidity and retirement goal
    # are separate views of the same dollars, but net worth needs one owner.
    retirement_marketable = sum(
        max(0.0, float(row.get("value") or 0) - float(row.get("margin_debt") or 0))
        for row in F._dig(facts, "household.balance_sheet") or []
        if not row.get("pending") and row.get("liquidity_class") == F.MARKETABLE
        and row.get("retirement_eligible") is True
    )
    retirement_for_net_worth = max(0.0, retirement - retirement_marketable)
    retirement = retirement_for_net_worth
    debt_rows = F._dig(facts, "debts")
    if debt_rows is None:
        raise ScenarioError("debts must be recorded as a list, including []")
    missing_debt = [row.get("name") or "unnamed debt" for row in debt_rows
                    if row.get("balance") is None]
    if missing_debt:
        raise ScenarioError("debt balance is unknown for " + ", ".join(missing_debt))
    debt = sum(float(row["balance"]) for row in debt_rows)

    members = F._dig(facts, "household.members") or []
    earners = [m for m in members if float(m.get("income_annual") or 0) > 0]
    variable = next((m.get("income_variable_share") for m in earners
                     if m.get("income_variable_share") is not None), None)
    buffer = C.size_buffer(
        liquid=F.reserve_assets(facts).included,
        annual_spending=float(F._dig(facts, "household.annual_spending") or 0),
        earners=len(earners), has_dependents=bool(F.dependents(facts)),
        variable_comp_share=variable,
    )
    primary = next((m for m in members if m.get("role") == "primary"), {})
    minimum = selected.get("minimum_savings") or {}
    gross = float(selected.get("gross_income_annual") or 0)
    cash_floor = max(
        float(minimum.get("annual_amount") or 0),
        gross * float(minimum.get("gross_income_rate") or 0),
    )
    return Baseline(
        as_of=F.as_of(facts) or T._date(F._dig(facts, "meta.as_of"), "meta.as_of"),
        currency=str(F._dig(facts, "meta.currency") or ""),
        basis=T.BASIS_NOMINAL,
        name=name,
        monthly_after_tax_income=float(after_tax) / 12,
        monthly_current_spending=current_spending / 12,
        monthly_essential_spending=None,
        monthly_employee_retirement_contribution=retirement_employee / 12,
        monthly_employer_retirement_contribution=retirement_employer / 12,
        monthly_other_outflows=other_outflows / 12,
        cash=cash,
        marketable=marketable,
        retirement=retirement,
        illiquid=illiquid,
        debt=debt,
        employer_stock=employer_stock,
        employer_stock_in_marketable=bool(in_balance_sheet),
        unvested_equity=float(F._dig(facts, "equity_comp.unvested_value") or 0),
        emergency_floor=buffer.target,
        annual_savings_floor=retirement_employee + retirement_employer + cash_floor,
        current_age=primary.get("age"),
        retirement_spending_annual=float(
            F._dig(facts, "household.annual_spending") or 0),
        source_fingerprint=T.fingerprint(facts),
    )


@dataclass(frozen=True)
class MonthState:
    month: int
    date: dt.date
    opening_cash: float
    after_tax_income: float
    explicit_inflows: float
    spending: float
    employee_retirement_contributions: float
    employer_retirement_contributions: float
    other_outflows: float
    explicit_outflows: float
    closing_cash: float
    marketable: float
    retirement: float
    illiquid: float
    debt: float
    net_worth: float
    employer_stock: float
    unvested_equity: float
    event_ids: tuple[str, ...]

    @property
    def cash_reconciles(self) -> bool:
        expected = (self.opening_cash + self.after_tax_income
                    + self.explicit_inflows - self.spending
                    - self.employee_retirement_contributions
                    - self.other_outflows)
        return math.isclose(expected, self.closing_cash, abs_tol=0.01)

    @property
    def retirement_contributions(self) -> float:
        return (self.employee_retirement_contributions
                + self.employer_retirement_contributions)


@dataclass(frozen=True)
class BridgeItem:
    event_id: str
    cash_change: float
    net_worth_change: float
    note: str


@dataclass
class ScenarioResult:
    spec: ScenarioSpec
    baseline: Baseline
    baseline_path: tuple[MonthState, ...]
    monthly_path: tuple[MonthState, ...]
    bridge: tuple[BridgeItem, ...]
    minimum_cash: float
    minimum_cash_month: int
    months_below_floor: int
    terminal_liquidity_change: float
    terminal_net_worth_change: float
    annual_savings_during_shock: float
    annual_savings_after_recovery: float
    retirement_age_at_target: float | None
    binding_constraint: str
    recovery_conditions: tuple[str, ...]
    unknowns: tuple[str, ...]
    metrics: tuple[T.MetricObservation, ...]

    @property
    def liquidity_passes(self) -> bool:
        return self.months_below_floor == 0 and self.minimum_cash >= 0


def _add_months(value: dt.date, months: int) -> dt.date:
    index = value.year * 12 + value.month - 1 + months
    year, month0 = divmod(index, 12)
    day = min(value.day, (dt.date(year + (month0 == 11), (month0 + 1) % 12 + 1, 1)
                          - dt.timedelta(days=1)).day)
    return dt.date(year, month0 + 1, day)


@dataclass
class _MutableState:
    cash: float
    marketable: float
    retirement: float
    illiquid: float
    debt: float
    employer_stock: float
    employer_stock_in_marketable: bool
    unvested: float
    spending_delta: float = 0.0

    @property
    def net_worth(self) -> float:
        separate_employer_stock = (0.0 if self.employer_stock_in_marketable
                                   else self.employer_stock)
        return (self.cash + self.marketable + separate_employer_stock
                + self.retirement + self.illiquid - self.debt)


def _receipt_net(event: ScenarioEvent) -> float:
    if event.after_tax_amount is not None:
        return event.after_tax_amount
    assert event.gross_amount is not None and event.tax_reserve is not None
    return event.gross_amount - event.tax_reserve


def _active_benefit(event: ScenarioEvent, month: int) -> bool:
    if not event.unemployment_after_tax_monthly:
        return False
    start = event.benefit_start_month or event.start_month
    duration = event.benefit_duration_months or event.duration_months
    end = None if duration is None else start + duration - 1
    return month >= start and (end is None or month <= end)


def _run_path(baseline: Baseline, spec: ScenarioSpec,
              events: tuple[ScenarioEvent, ...]) -> tuple[tuple[MonthState, ...], tuple[BridgeItem, ...]]:
    state = _MutableState(
        cash=baseline.cash,
        marketable=baseline.marketable,
        retirement=baseline.retirement,
        illiquid=baseline.illiquid,
        debt=baseline.debt,
        employer_stock=baseline.employer_stock,
        employer_stock_in_marketable=baseline.employer_stock_in_marketable,
        unvested=baseline.unvested_equity,
    )
    path: list[MonthState] = []
    bridge_totals: dict[str, list[Any]] = {}
    market_growth = (1 + spec.market_return_annual) ** (1 / 12) - 1
    retirement_growth = (1 + spec.retirement_return_annual) ** (1 / 12) - 1

    ordered = sorted(events, key=lambda e: (e.start_month, EVENT_ORDER[e.type], e.id))
    for month in range(1, spec.horizon_months + 1):
        opening = state.cash
        opening_net_worth = state.net_worth
        income = baseline.monthly_after_tax_income
        spending = baseline.monthly_current_spending + state.spending_delta
        employee_contribution = baseline.monthly_employee_retirement_contribution
        employer_contribution = baseline.monthly_employer_retirement_contribution
        other_outflows = baseline.monthly_other_outflows
        explicit_inflows = 0.0
        explicit_outflows = 0.0
        event_ids: list[str] = []

        active = [event for event in ordered
                  if event.start_month == month or event.active(month)]
        for event in active:
            applied = False
            if event.type == "employment_loss" and event.active(month):
                income -= event.after_tax_income_loss_monthly
                employee_contribution -= event.employee_contribution_loss_monthly
                employer_contribution -= event.employer_match_loss_monthly
                spending += event.replacement_health_cost_monthly
                if _active_benefit(event, month):
                    income += event.unemployment_after_tax_monthly
                if month == (event.severance_month or event.start_month):
                    explicit_inflows += event.severance_after_tax
                if month == event.start_month:
                    state.unvested = max(0.0, state.unvested - event.unvested_forfeiture)
                    if event.employer_stock_change is not None:
                        loss = state.employer_stock * event.employer_stock_change
                        state.employer_stock += loss
                        if state.employer_stock_in_marketable:
                            state.marketable += loss
                applied = True
            elif event.type == "compensation_change" and event.active(month):
                income += event.after_tax_income_change_monthly
                employee_contribution += event.retirement_contribution_change_monthly
                applied = True
            elif event.type == "recurring_expense_change" and event.active(month):
                spending += event.amount_monthly
                applied = True
            elif month == event.start_month:
                applied = True
                if event.type == "cash_receipt":
                    explicit_inflows += _receipt_net(event)
                elif event.type == "asset_receipt":
                    assert event.market_value is not None
                    if event.liquidate:
                        assert event.cost_basis is not None and event.tax_rate is not None
                        gain = max(0.0, event.market_value - event.cost_basis)
                        explicit_inflows += max(
                            0.0, event.market_value - gain * event.tax_rate
                            - event.transaction_cost)
                    else:
                        state.marketable += event.market_value - event.transaction_cost
                elif event.type == "asset_price_change":
                    assert event.price_change is not None
                    if event.target == "marketable":
                        state.marketable *= 1 + event.price_change
                        if state.employer_stock_in_marketable:
                            state.employer_stock *= 1 + event.price_change
                    else:
                        change = state.employer_stock * event.price_change
                        state.employer_stock += change
                        if state.employer_stock_in_marketable:
                            state.marketable += change
                elif event.type == "one_time_expense":
                    other_outflows += event.amount
                    explicit_outflows += event.amount
                elif event.type == "portfolio_withdrawal":
                    if event.amount > state.marketable:
                        raise ScenarioError(
                            f"{event.id}: withdrawal exceeds marketable assets in month {month}"
                        )
                    state.marketable -= event.amount
                    tax = event.tax_reserve or 0.0
                    if tax > event.amount:
                        raise ScenarioError(f"{event.id}: tax reserve exceeds withdrawal")
                    explicit_inflows += event.amount - tax - event.transaction_cost
                elif event.type == "debt_payoff":
                    if event.amount > state.debt:
                        raise ScenarioError(
                            f"{event.id}: payoff exceeds recorded debt in month {month}"
                        )
                    other_outflows += event.amount + event.payoff_penalty
                    explicit_outflows += event.amount + event.payoff_penalty
                    state.debt -= event.amount
                elif event.type == "home_purchase":
                    mortgage = event.purchase_price - event.down_payment
                    other_outflows += event.down_payment + event.closing_cost
                    explicit_outflows += event.down_payment + event.closing_cost
                    state.illiquid += event.purchase_price
                    state.debt += mortgage
                    state.spending_delta += event.monthly_housing_cost_change
                elif event.type == "portfolio_contribution":
                    other_outflows += event.amount + event.transaction_cost
                    explicit_outflows += event.amount + event.transaction_cost
                    state.marketable += event.amount
            if applied:
                event_ids.append(event.id)

        if income < 0:
            raise ScenarioError(
                f"month {month}: event income reductions exceed the baseline")
        if employee_contribution < 0 or employer_contribution < 0:
            raise ScenarioError(
                f"month {month}: contribution reductions exceed the baseline")
        if spending < 0:
            raise ScenarioError(
                f"month {month}: expense reductions exceed baseline spending")
        state.cash = (opening + income + explicit_inflows - spending
                      - employee_contribution - other_outflows)
        state.marketable *= 1 + market_growth
        state.employer_stock *= 1 + market_growth
        state.retirement = (state.retirement + employee_contribution
                            + employer_contribution) \
            * (1 + retirement_growth)
        date = _add_months(spec.as_of, month)
        row = MonthState(
            month=month,
            date=date,
            opening_cash=opening,
            after_tax_income=income,
            explicit_inflows=explicit_inflows,
            spending=spending,
            employee_retirement_contributions=employee_contribution,
            employer_retirement_contributions=employer_contribution,
            other_outflows=other_outflows,
            explicit_outflows=explicit_outflows,
            closing_cash=state.cash,
            marketable=state.marketable,
            retirement=state.retirement,
            illiquid=state.illiquid,
            debt=state.debt,
            net_worth=state.net_worth,
            employer_stock=state.employer_stock,
            unvested_equity=state.unvested,
            event_ids=tuple(event_ids),
        )
        if not row.cash_reconciles:
            raise AssertionError(f"month {month} cash does not reconcile")
        path.append(row)
        month_cash_delta = state.cash - opening
        month_nw_delta = state.net_worth - opening_net_worth
        for event_id in event_ids:
            # A multi-event month cannot honestly allocate shared baseline
            # cash flow between events.  The bridge retains the event and puts
            # unallocated movement in the residual at comparison time.
            slot = bridge_totals.setdefault(event_id, [0.0, 0.0])
            if len(event_ids) == 1:
                slot[0] += month_cash_delta
                slot[1] += month_nw_delta

    bridge = tuple(
        BridgeItem(event_id=event.id,
                   cash_change=float(bridge_totals.get(event.id, [0, 0])[0]),
                   net_worth_change=float(bridge_totals.get(event.id, [0, 0])[1]),
                   note=("isolated month effect" if bridge_totals.get(event.id) != [0, 0]
                         else "shares a month or has no cash/net-worth effect; residual retained"))
        for event in ordered
    )
    return tuple(path), bridge


def _annual_savings(path: tuple[MonthState, ...], months: range) -> float:
    rows = [row for row in path if row.month in months]
    if not rows:
        return 0.0
    total = sum(row.retirement_contributions + max(
        0.0,
        row.after_tax_income - row.spending
        - row.employee_retirement_contributions
        - (row.other_outflows - row.explicit_outflows),
    ) for row in rows)
    return total * 12 / len(rows)


def _scenario_metrics(
    spec: ScenarioSpec,
    baseline: Baseline,
    path: tuple[MonthState, ...],
) -> tuple[T.MetricObservation, ...]:
    out: list[T.MetricObservation] = []
    for row in path:
        common = dict(
            effective_date=row.date,
            unit="currency",
            currency=spec.currency,
            basis=spec.basis,
            scenario=spec.id,
            source="scenario.monthly_path",
            clock=T.CLOCK_PROJECTION,
            status="projected",
            calculated_at=spec.as_of,
            model_version=SCENARIO_MODEL_VERSION,
            inputs_fingerprint=baseline.source_fingerprint,
        )
        out.append(T.MetricObservation(
            metric_id="scenario.cash_balance", value=row.closing_cash, **common))
        out.append(T.MetricObservation(
            metric_id="scenario.net_worth", value=row.net_worth, **common))
        out.append(T.MetricObservation(
            metric_id="scenario.retirement_assets", value=row.retirement, **common))
        out.append(T.MetricObservation(
            metric_id="scenario.employer_stock", value=row.employer_stock, **common))
    return tuple(out)


def run_scenario(baseline: Baseline, spec: ScenarioSpec) -> ScenarioResult:
    if baseline.currency != spec.currency or baseline.basis != spec.basis:
        raise ScenarioError(
            "baseline and scenario currency/basis differ; record an explicit "
            "conversion before combining them"
        )
    if baseline.as_of != spec.as_of:
        raise ScenarioError(
            "scenario as_of must equal the recorded baseline date; applying "
            "events to an unstated gap would invent intervening facts")
    baseline_path, _ = _run_path(baseline, spec, ())
    path, _ = _run_path(baseline, spec, spec.events)
    bridge_rows: list[BridgeItem] = []
    for event in spec.events:
        isolated, _ = _run_path(baseline, spec, (event,))
        bridge_rows.append(BridgeItem(
            event_id=event.id,
            cash_change=(isolated[-1].closing_cash
                         - baseline_path[-1].closing_cash),
            net_worth_change=(isolated[-1].net_worth
                              - baseline_path[-1].net_worth),
            note="isolated event effect; any composition residual remains explicit",
        ))
    bridge = tuple(bridge_rows)
    minimum = min(path, key=lambda row: (row.closing_cash, row.month))
    terminal = path[-1]
    terminal_base = baseline_path[-1]
    months_below = sum(row.closing_cash < baseline.emergency_floor for row in path)

    shock_windows = []
    for event in spec.events:
        if event.type == "employment_loss":
            shock_windows.append(event.end_month or spec.horizon_months)
        elif (event.type in ("compensation_change", "recurring_expense_change")
              and event.end_month is not None):
            shock_windows.append(event.end_month)
    shock_end = max(shock_windows, default=0)
    during_end = min(spec.horizon_months, max(12, shock_end))
    annual_during = _annual_savings(path, range(1, during_end + 1))
    # A run-rate excludes one-time receipts and purchases.  Use the final
    # twelve months (or the explicit post-shock interval when later) rather
    # than annualising the whole horizon and calling a windfall "saving".
    recovery_start = max(shock_end + 1, spec.horizon_months - 11, 1)
    annual_after = _annual_savings(
        path, range(recovery_start, spec.horizon_months + 1))

    last_contribution = path[-1].retirement_contributions * 12
    retirement = R.assess_readiness(
        annual_spending=baseline.retirement_spending_annual,
        assets=max(0.0, terminal.retirement + terminal.marketable
                   + (0.0 if baseline.employer_stock_in_marketable
                      else terminal.employer_stock)),
        annual_savings=last_contribution,
        current_age=(None if baseline.current_age is None else
                     baseline.current_age + spec.horizon_months / 12),
    )
    constraints = {
        "cash balance": minimum.closing_cash,
        "emergency-fund floor": min(
            row.closing_cash - baseline.emergency_floor for row in path),
        "annual-savings floor": min(annual_during, annual_after)
        - baseline.annual_savings_floor,
    }
    binding = min(constraints, key=constraints.get)
    recovery: list[str] = []
    if minimum.closing_cash < 0:
        recovery.append(
            f"Add at least ${-minimum.closing_cash:,.0f} before month "
            f"{minimum.month}, or explicitly reduce an outflow before then."
        )
    if months_below:
        first = next(row.month for row in path
                     if row.closing_cash < baseline.emergency_floor)
        recovery.append(
            f"Restore cash above the ${baseline.emergency_floor:,.0f} reserve "
            f"floor after the first breach in month {first}."
        )
    if annual_after < baseline.annual_savings_floor:
        recovery.append(
            f"Post-recovery annual saving must rise by "
            f"${baseline.annual_savings_floor - annual_after:,.0f}."
        )
    if not recovery:
        recovery.append("No modeled recovery condition is breached.")

    return ScenarioResult(
        spec=spec,
        baseline=baseline,
        baseline_path=baseline_path,
        monthly_path=path,
        bridge=bridge,
        minimum_cash=minimum.closing_cash,
        minimum_cash_month=minimum.month,
        months_below_floor=months_below,
        terminal_liquidity_change=terminal.closing_cash - terminal_base.closing_cash,
        terminal_net_worth_change=terminal.net_worth - terminal_base.net_worth,
        annual_savings_during_shock=annual_during,
        annual_savings_after_recovery=annual_after,
        retirement_age_at_target=retirement.age_at_target,
        binding_constraint=binding,
        recovery_conditions=tuple(recovery),
        unknowns=tuple(
            f"{event.id}.{field_name}"
            for event in spec.events for field_name in event.unknown_fields),
        metrics=_scenario_metrics(spec, baseline, path),
    )


def scenarios_from_facts(facts: dict[str, Any]) -> list[ScenarioSpec]:
    currency = str(F._dig(facts, "meta.currency") or "")
    rows = F._dig(facts, "scenario_planning.scenarios") or []
    shared_objective = F._dig(facts, "scenario_planning.objective")
    ids: set[str] = set()
    out = []
    for row in rows:
        prepared = dict(row)
        if "objective" not in prepared and shared_objective is not None:
            prepared["objective"] = shared_objective
        spec = ScenarioSpec.from_dict(prepared, default_currency=currency)
        if spec.id in ids:
            raise ScenarioError(f"duplicate scenario id {spec.id!r}")
        ids.add(spec.id)
        out.append(spec)
    return out


def adapt_housing_events(facts: dict[str, Any], spec: ScenarioSpec) -> ScenarioSpec:
    """Resolve a home event through the existing affordability cash ledger."""
    from . import housing_affordability as H  # noqa: PLC0415
    purchase = F._dig(facts, "housing.purchase") or {}
    rent = float(F._dig(facts, "housing.monthly_rent") or 0)
    events = []
    for event in spec.events:
        if event.type != "home_purchase" or not event.housing_adapter:
            events.append(event)
            continue
        try:
            owner = H.owner_cash_cost(purchase)
        except H.ReconciliationError as exc:
            raise ScenarioError(f"{event.id}: housing adapter failed: {exc}") from exc
        events.append(replace(
            event,
            purchase_price=owner.price,
            down_payment=owner.down_payment,
            closing_cost=owner.closing_costs,
            monthly_housing_cost_change=owner.gross_annual / 12 - rent,
        ))
    return replace(spec, events=tuple(events))


def run_from_facts(facts: dict[str, Any]) -> list[ScenarioResult]:
    """Run all specifications and prove that the caller's facts stayed intact."""
    before = T.fingerprint(facts)
    results = []
    for spec in scenarios_from_facts(facts):
        spec = adapt_housing_events(facts, spec)
        baseline = baseline_from_facts(facts, spec.baseline)
        if spec.essential_spending_annual is not None:
            baseline = replace(
                baseline,
                monthly_essential_spending=spec.essential_spending_annual / 12,
            )
        results.append(run_scenario(baseline, spec))
    if T.fingerprint(facts) != before:
        raise AssertionError("scenario execution mutated baseline facts")
    return results


def rank_results(results: list[ScenarioResult], objective: str | None) -> list[ScenarioResult]:
    """Rank only when a recorded objective supplies the value judgement."""
    if objective in (None, "compare_only"):
        return list(results)
    if objective == "preserve_liquidity":
        return sorted(results, key=lambda r: (-r.minimum_cash, r.spec.id))
    if objective == "preserve_savings":
        return sorted(results, key=lambda r: (-r.annual_savings_after_recovery,
                                              r.spec.id))
    if objective == "minimize_debt":
        return sorted(results, key=lambda r: (r.monthly_path[-1].debt, r.spec.id))
    if objective == "minimize_retirement_delay":
        return sorted(results, key=lambda r: (
            r.retirement_age_at_target if r.retirement_age_at_target is not None
            else float("inf"), r.spec.id))
    if objective == "preserve_goal":
        return sorted(results, key=lambda r: (-r.monthly_path[-1].cash, r.spec.id))
    raise ScenarioError(f"unknown objective {objective!r}")


def current_and_essential_runway(
    result: ScenarioResult,
) -> tuple[float, float | None]:
    """Two explicit runways; never assumes the household achieved the cut."""
    cash = result.baseline.cash
    current = (cash / result.baseline.monthly_current_spending
               if result.baseline.monthly_current_spending else float("inf"))
    essential = (cash / result.baseline.monthly_essential_spending
                 if result.baseline.monthly_essential_spending else None)
    return current, essential


def windfall_net_amount(event: ScenarioEvent) -> tuple[float | None, str | None]:
    """Return spendable cash only when tax character and basis support it."""
    if event.type == "cash_receipt":
        return _receipt_net(event), None
    if event.type != "asset_receipt":
        return None, "not a receipt event"
    if not event.liquidate:
        return None, "asset is retained, so gross market value is not cash"
    if event.cost_basis is None or event.tax_rate is None:
        return None, "basis or tax rate is unknown"
    assert event.market_value is not None
    gain = max(0.0, event.market_value - event.cost_basis)
    return max(0.0, event.market_value - gain * event.tax_rate
               - event.transaction_cost), None


def windfall_link_errors(
    spec: ScenarioSpec,
    recorded_events: list[Any],
) -> tuple[str, ...]:
    """Prove scenario receipts are the windfalls already characterized."""
    errors: list[str] = []
    for event in spec.events:
        if event.type not in ("cash_receipt", "asset_receipt"):
            continue
        if not event.source_event_id:
            errors.append(f"{event.id}: receipt needs source_event_id")
            continue
        matches = [row for row in recorded_events if row.id == event.source_event_id]
        if len(matches) != 1:
            errors.append(
                f"{event.id}: source_event_id {event.source_event_id!r} "
                f"matched {len(matches)} "
                "recorded windfalls")
            continue
        gross = (event.gross_amount if event.type == "cash_receipt"
                 else event.market_value)
        if gross is None:
            errors.append(f"{event.id}: gross receipt is required for reconciliation")
        elif not math.isclose(float(gross), matches[0].amount, abs_tol=0.01):
            errors.append(
                f"{event.id}: scenario gross {gross:,.2f} disagrees with "
                f"recorded windfall {matches[0].amount:,.2f}")
    return tuple(errors)
