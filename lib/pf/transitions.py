"""Life transitions: what the event does to the tax character of a dollar.

## The one idea

A transition does not move money so much as **re-label it**. The same $400,000
is a different asset depending on how it arrived and where it lands, and every
expensive mistake in this cluster comes from treating labelled dollars as
interchangeable:

* an inherited security generally arrives with a **stepped-up basis**; an IPO
  share does not, and a settlement depends entirely on what it compensates;
* a dollar of Roth, a dollar of pre-tax 401(k) and a dollar of taxable stock
  with an embedded gain are three different amounts of spendable money, so a
  nominal 50/50 split is not an equal one;
* marriage and divorce change the *mechanism* by which an account can move —
  QDRO, transfer incident to divorce, §1041 — and the mechanisms are not
  interchangeable either.

## The basis, stated once

Every figure here is **nominal and pre-state-tax**, in the facts file's
currency. Federal ordinary and capital-gains rates are supplied by the caller;
nothing is inferred from a bracket table, because this module does not contain
one. Where a state rule would change the answer — community property being the
large one — the module says so and refuses rather than guessing.

## What it refuses

* **Any tax computation that needs a bracket table.** The marriage comparison
  works on two numbers the household's tax software produced, not on a
  reimplementation of the code.
* **Valuation of anything.** A business, a pension's present value, a house
  net of selling costs. Those are appraisals.
* **Support, custody, and anything adversarial.** Out of scope, permanently.
* **Beneficiary completeness and Form 3520 arithmetic**, which already live in
  `estate.py` and `reporting.py` and are imported rather than restated.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from . import cash as _cash
from . import reporting as _rep
from . import status as _sta

#: The IRMAA two-year lookback is defined once, in `healthcare.py`. This module
#: reports its consequence for a windfall year; it does not own the period.
from .healthcare import IRMAA_LOOKBACK_YEARS  # noqa: F401

# ── the pause ───────────────────────────────────────────────────────────────

#: Days a windfall should sit somewhere safe and liquid before any
#: irreversible commitment. Not a market view — a decision-quality one. The
#: regretted purchases, the loans to relatives, the annuity sold by the person
#: who read the probate filing, and the resignation all happen inside the
#: first month, while the recipient is still being told the money is an
#: emergency requiring immediate action. It is not.
DECISION_PAUSE_DAYS = 90

#: FDIC deposit insurance, per depositor, per insured bank, per ownership
#: category. A windfall parked in one bank account is frequently the first
#: time a household has ever been over it.
FDIC_LIMIT_PER_DEPOSITOR = 250_000

#: SIPC, per customer, per brokerage — of which this much may be cash. SIPC
#: covers the *custodian failing*, not the investments losing value. The two
#: get conflated precisely when the balance is large enough to matter.
SIPC_LIMIT = 500_000
SIPC_CASH_SUBLIMIT = 250_000

INSURANCE_SOURCE = "12 U.S.C. §1821(a) (FDIC); 15 U.S.C. §78fff-3 (SIPC)"
INSURANCE_VERIFIED = "unverified — check fdic.gov and sipc.org"

# ── withholding and estimated tax ───────────────────────────────────────────

#: Flat federal withholding on supplemental wages — an RSU vest, a bonus, a
#: signing payment — below the annual supplemental threshold. This is the
#: single most common withholding gap: it is a *withholding* rate, not a tax
#: rate, and a household whose marginal rate is 35% is under-withheld by the
#: difference on every dollar of it.
SUPPLEMENTAL_WITHHOLDING_RATE = 0.22
#: Mandatory rate on supplemental wages above the threshold, in aggregate for
#: the year.
SUPPLEMENTAL_WITHHOLDING_RATE_ABOVE = 0.37
SUPPLEMENTAL_WITHHOLDING_THRESHOLD = 1_000_000

#: Safe harbours against the §6654 underpayment penalty: pay this share of the
#: *current* year's tax, or the prior-year multiple below, and the penalty
#: does not apply however large the final bill is. The prior-year harbour is
#: the one that matters in a windfall year, because the current year's tax is
#: exactly the number nobody can yet compute.
SAFE_HARBOR_CURRENT_YEAR = 0.90
SAFE_HARBOR_PRIOR_YEAR = 1.00
SAFE_HARBOR_PRIOR_YEAR_HIGH_AGI = 1.10
#: Prior-year AGI above which the higher prior-year multiple applies.
SAFE_HARBOR_HIGH_AGI = 150_000

#: IRMAA and ACA both look back. Medicare premiums for a year are set from the
#: modified AGI of the return filed two years earlier, so a one-off income year
#: raises premiums for one year, two years later, after the money is spent.
#: `IRMAA_LOOKBACK_YEARS` itself is defined in `healthcare.py`, which owns the
#: Medicare structure and whose skills are the load-bearing consumers. It is
#: imported at the top of this module, not restated here: two copies of a
#: statutory period eventually disagree, and the checklist can only tick one.

TAX_ADMIN_SOURCE = (
    "IRC §6654 and Pub. 505 (estimated tax safe harbours); Treas. Reg. "
    "§31.3402(g)-1 (supplemental wage withholding); 42 U.S.C. §1395r(i) "
    "(IRMAA two-year lookback)"
)
TAX_ADMIN_VERIFIED = "unverified — check against irs.gov and ssa.gov"

# ── tax character of a windfall ─────────────────────────────────────────────


@dataclass(frozen=True)
class TaxCharacter:
    """How a kind of windfall is taxed, and what basis it carries.

    `known=False` is the honest answer for anything not in the table, and the
    skills print it as a refusal. Reasoning by analogy from a kind that *is*
    here is how a settlement gets treated like an inheritance.
    """

    kind: str
    known: bool
    #: Is the receipt itself income to the recipient?
    income_on_receipt: bool | None = None
    #: "stepped_up" | "carryover" | "unchanged" | "zero" | "varies"
    basis_rule: str = "unknown"
    note: str = ""
    source: str = ""
    verified_on: str = ""


_TAX_CHARACTER: dict[str, TaxCharacter] = {
    "inheritance": TaxCharacter(
        "inheritance", True, income_on_receipt=False, basis_rule="stepped_up",
        note="An inheritance is **not income** to the recipient. Assets "
             "acquired from a decedent generally take a basis equal to fair "
             "market value at the date of death, so the decedent's unrealised "
             "gain is erased and only appreciation *after* that date is "
             "taxable on sale. Two consequences people miss: selling "
             "immediately is usually close to tax-free, and holding a "
             "concentrated inherited position for sentimental reasons is a "
             "concentration decision being made by default. Note that an "
             "inherited *retirement account* is the opposite case — no step-up "
             "on pre-tax balances, and distributions are ordinary income under "
             "the 10-year rule.",
        source="IRC §102 (receipt not income); IRC §1014 (basis of property "
               "acquired from a decedent); IRC §401(a)(9)(H) (10-year rule)",
        verified_on="unverified — check against irs.gov",
    ),
    "gift": TaxCharacter(
        "gift", True, income_on_receipt=False, basis_rule="carryover",
        note="A gift is not income to the recipient, and any gift tax is the "
             "donor's problem, not yours. But basis **carries over** from the "
             "donor — there is no step-up — so a gifted asset can arrive with "
             "a large embedded gain that becomes yours on sale. This is the "
             "sharpest difference between receiving something now and "
             "inheriting the same thing later.",
        source="IRC §102; IRC §1015 (basis of property acquired by gift)",
        verified_on="unverified — check against irs.gov",
    ),
    "equity_vest": TaxCharacter(
        "equity_vest", True, income_on_receipt=True, basis_rule="unchanged",
        note="RSUs vesting at or after an IPO are **ordinary wage income** at "
             "vest, reported on the W-2, with basis equal to the amount "
             "included. There is no step-up and no preferential rate. Shares "
             "held afterwards start a fresh holding period from the vest date, "
             "so selling within a year of vest produces a short-term gain on "
             "top of income already taxed.",
        source="IRC §83; Treas. Reg. §1.83-1",
        verified_on="unverified — check against irs.gov",
    ),
    "equity_sale": TaxCharacter(
        "equity_sale", True, income_on_receipt=True, basis_rule="unchanged",
        note="A sale of shares you already held is a capital transaction "
             "against your existing basis — long or short term by holding "
             "period. A liquidity event does not reset basis. Whether §1202 "
             "qualified small business stock applies is a separate question "
             "with specific requirements, and it is not encoded here.",
        source="IRC §1001 (gain on disposition); IRC §1222 (holding period)",
        verified_on="unverified — check against irs.gov",
    ),
    "settlement": TaxCharacter(
        "settlement", True, income_on_receipt=None, basis_rule="varies",
        note="**It depends entirely on what the settlement compensates, and "
             "the allocation in the settlement agreement largely controls it.** "
             "Damages for personal *physical* injury or sickness are excluded "
             "from income; emotional distress not arising from physical injury "
             "is not. Lost wages are ordinary income, punitive damages are "
             "income in essentially all cases, and interest on the award is "
             "interest income. A single number described as 'the settlement' "
             "cannot be characterised — get the allocation before agreeing to "
             "it, because it is far harder to argue afterwards.",
        source="IRC §104(a)(2); IRC §61; Commissioner v. Schleier",
        verified_on="unverified — check against irs.gov",
    ),
    "life_insurance": TaxCharacter(
        "life_insurance", True, income_on_receipt=False, basis_rule="stepped_up",
        note="Death benefit proceeds paid by reason of the insured's death are "
             "generally **not income** to the beneficiary. Interest paid on "
             "proceeds held by the insurer before payout is. Separately, the "
             "proceeds may still be in the insured's taxable *estate* if the "
             "insured owned the policy — a different tax from a different "
             "payer.",
        source="IRC §101(a)",
        verified_on="unverified — check against irs.gov",
    ),
    "lottery": TaxCharacter(
        "lottery", True, income_on_receipt=True, basis_rule="zero",
        note="Fully **ordinary income** in the year received, at the top of "
             "the stack. Mandatory withholding at the statutory rate is well "
             "below the top marginal rate, so a large prize is materially "
             "under-withheld at source.",
        source="IRC §61; IRC §3402(q)",
        verified_on="unverified — check against irs.gov",
    ),
    "retirement_account_inherited": TaxCharacter(
        "retirement_account_inherited", True, income_on_receipt=False,
        basis_rule="unchanged",
        note="**No step-up.** An inherited traditional IRA or 401(k) carries "
             "the decedent's tax character: distributions are ordinary income "
             "to you. Most non-spouse beneficiaries must empty the account "
             "within ten years, and where the decedent had already begun RMDs, "
             "annual distributions are required during that window too. The "
             "planning question is how to spread it across ten tax years, and "
             "it is the single most consequential decision in an inheritance "
             "with a retirement account in it.",
        source="IRC §401(a)(9)(H); IRC §691 (income in respect of a decedent)",
        verified_on="unverified — check against irs.gov",
    ),
}

WINDFALL_TAX_SOURCE = "IRC §§61, 83, 101, 102, 104, 1014, 1015, 401(a)(9)(H)"
WINDFALL_TAX_VERIFIED = "unverified — check against irs.gov"


def tax_character(kind: str | None) -> TaxCharacter:
    if not kind:
        return TaxCharacter("??", False)
    return _TAX_CHARACTER.get(str(kind).strip().lower(),
                              TaxCharacter(str(kind), False))


def windfall_kinds_available() -> list[str]:
    return sorted(_TAX_CHARACTER)


# ── findings ────────────────────────────────────────────────────────────────


@dataclass
class Finding:
    area: str
    severity: str  # blocker | gap | note | ok
    detail: str


SEVERITY_ORDER = {"blocker": 0, "gap": 1, "note": 2, "ok": 3}


def _sorted(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: SEVERITY_ORDER.get(f.severity, 9))


# ── windfall ────────────────────────────────────────────────────────────────


@dataclass
class WindfallEvent:
    id: str | None
    label: str
    kind: str
    amount: float
    character: TaxCharacter
    received: _dt.date | None
    days_held: int | None
    pause_until: _dt.date | None
    pause_days_remaining: int | None
    source_foreign: bool | None

    @property
    def pause_elapsed(self) -> bool | None:
        if self.pause_days_remaining is None:
            return None
        return self.pause_days_remaining <= 0


@dataclass
class WindfallPlan:
    events: list[WindfallEvent] = field(default_factory=list)
    total: float = 0.0
    #: Sum of amounts whose tax character is known *and* income on receipt.
    taxable_amount: float | None = None
    estimated_tax: float | None = None
    withheld: float | None = None
    shortfall: float | None = None
    safe_harbor: float | None = None
    findings: list[Finding] = field(default_factory=list)

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "blocker"]

    @property
    def any_pause_live(self) -> bool:
        return any(e.pause_elapsed is False for e in self.events)


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


def safe_harbor_payment(prior_year_tax: float | None,
                        prior_year_agi: float | None) -> float | None:
    """The prior-year safe harbour, which is the one computable in advance.

    Returns None rather than zero when the prior year is unknown: a household
    told "$0" will pay nothing and discover the penalty at filing.
    """
    if prior_year_tax is None:
        return None
    multiple = (SAFE_HARBOR_PRIOR_YEAR_HIGH_AGI
                if (prior_year_agi or 0) > SAFE_HARBOR_HIGH_AGI
                else SAFE_HARBOR_PRIOR_YEAR)
    return float(prior_year_tax) * multiple


def assess_windfall(
    events: list[dict],
    *,
    as_of: _dt.date | None,
    marginal_rate: float | None = None,
    withheld: float | None = None,
    prior_year_tax: float | None = None,
    prior_year_agi: float | None = None,
    aca_marketplace_coverage: bool | None = None,
    medicare_within_lookback: bool | None = None,
    new_accounts_without_beneficiaries: list[str] | None = None,
) -> WindfallPlan:
    """Characterise each windfall, then size the tax and reporting exposure.

    `marginal_rate` is the caller's federal ordinary rate. State tax is *not*
    applied — see the module docstring — so every tax figure below is a floor.
    """
    plan = WindfallPlan()
    events = events or []

    if not events:
        plan.findings.append(Finding(
            "windfall", "gap",
            "**No windfall recorded.** Nothing to assess. Record the event "
            "with its `kind` and `amount` — the kind is what determines the "
            "tax, and it is the field people leave out."))
        return plan

    # ── the pause, first and plainly ────────────────────────────────────
    for i, e in enumerate(events):
        kind = e.get("kind")
        char = tax_character(kind)
        received = _as_date(e.get("received"))
        pause_until = (received + _dt.timedelta(days=DECISION_PAUSE_DAYS)
                       if received else None)
        days_held = (as_of - received).days if (received and as_of) else None
        remaining = ((pause_until - as_of).days
                     if (pause_until and as_of) else None)
        plan.events.append(WindfallEvent(
            id=e.get("id"),
            label=e.get("label") or kind or f"#{i}",
            kind=kind or "unknown",
            amount=float(e.get("amount") or 0),
            character=char,
            received=received,
            days_held=days_held,
            pause_until=pause_until,
            pause_days_remaining=remaining,
            source_foreign=e.get("source_foreign"),
        ))

    plan.total = sum(e.amount for e in plan.events)

    live = [e for e in plan.events if e.pause_elapsed is False]
    undated = [e for e in plan.events if e.pause_days_remaining is None]
    if live:
        soonest = min(e.pause_days_remaining or 0 for e in live)
        plan.findings.append(Finding(
            "pause", "blocker",
            f"**Do nothing irreversible for another {soonest} day(s).** "
            f"{len(live)} of {len(plan.events)} events are inside the "
            f"{DECISION_PAUSE_DAYS}-day window. Park the money somewhere safe "
            "and liquid, decline every opportunity, and let the urgency pass. "
            "Nothing on this list — not a house, not a business, not a loan to "
            "a relative, not an annuity — gets worse by waiting three months, "
            "and the decisions people regret are made in the first one. The "
            "only things worth doing now are the reversible ones: park it, "
            "cover the tax, name beneficiaries."))
    elif undated:
        plan.findings.append(Finding(
            "pause", "gap",
            "**No receipt date recorded**, so whether the "
            f"{DECISION_PAUSE_DAYS}-day pause has elapsed cannot be "
            "determined. Add `received`. If the money arrived this month, the "
            "answer is no."))
    else:
        plan.findings.append(Finding(
            "pause", "ok",
            f"The {DECISION_PAUSE_DAYS}-day pause has elapsed on every "
            "recorded event. Decisions made from here are being made by the "
            "household rather than by the shock, which is the whole point of "
            "the delay."))

    # ── where it is parked ──────────────────────────────────────────────
    if plan.total > FDIC_LIMIT_PER_DEPOSITOR:
        plan.findings.append(Finding(
            "parking", "note",
            f"{_money(plan.total)} exceeds the "
            f"{_money(FDIC_LIMIT_PER_DEPOSITOR)} FDIC limit — per depositor, "
            "per insured bank, per ownership category. 'Safe and liquid' means "
            "insured or Treasury-backed, which in practice means splitting "
            "across banks, or a Treasury money market fund, or direct bills. "
            f"Brokerage SIPC coverage ({_money(SIPC_LIMIT)}, of which "
            f"{_money(SIPC_CASH_SUBLIMIT)} cash) is **not the same thing** — it "
            "covers the custodian failing, not the investments falling. See "
            "`cash-yield-review` for where the parked money should actually "
            "sit; parking it is not the same as leaving it at 0.01%."))

    # ── character, per event ────────────────────────────────────────────
    unknown_kinds = [e for e in plan.events if not e.character.known]
    for e in unknown_kinds:
        plan.findings.append(Finding(
            "character", "blocker",
            f"**`{e.label}`: kind `{e.kind}` is not in the table, so its tax "
            f"character cannot be determined.** Known kinds: "
            f"{', '.join(windfall_kinds_available())}. This is not a gap worth "
            "filling by analogy — the whole point of the table is that these "
            "kinds are taxed differently from one another."))

    for e in plan.events:
        if e.character.known:
            plan.findings.append(Finding(
                "character", "note", f"**{e.label}** — {e.character.note}"))

    settlements = [e for e in plan.events if e.kind == "settlement"]
    if settlements:
        plan.findings.append(Finding(
            "character", "blocker",
            "**A settlement's taxable portion cannot be computed from an "
            "amount alone**, so it is excluded from the tax estimate below "
            "rather than guessed at. Take the allocation from the settlement "
            "agreement — physical injury, emotional distress, lost wages, "
            "punitive, interest — and characterise each piece. Note also that "
            "where attorney fees come out of a taxable award, the gross amount "
            "can be income to you even though you never see the fee portion."))

    # ── the tax estimate ────────────────────────────────────────────────
    computable = [e for e in plan.events
                  if e.character.known and e.character.income_on_receipt is True]
    indeterminate = [e for e in plan.events
                     if not e.character.known
                     or e.character.income_on_receipt is None]

    if marginal_rate is None:
        plan.findings.append(Finding(
            "estimated tax", "blocker",
            "**No marginal rate supplied, so the tax owed cannot be sized.** "
            "`assumptions.marginal_tax_rate`. Unknown is not zero here: the "
            "failure mode is spending the gross and meeting the bill in "
            "April."))
    else:
        plan.taxable_amount = sum(e.amount for e in computable)
        plan.estimated_tax = plan.taxable_amount * float(marginal_rate)
        plan.withheld = withheld
        if withheld is not None:
            plan.shortfall = max(0.0, plan.estimated_tax - float(withheld))

        if plan.taxable_amount == 0 and not indeterminate:
            plan.findings.append(Finding(
                "estimated tax", "ok",
                "None of the recorded events is income on receipt, so no "
                "federal income tax arises from the windfall itself. Tax "
                "arrives later, on what the money earns and on what you sell."))
        elif plan.taxable_amount:
            line = (f"**About {_money(plan.estimated_tax)} of federal tax on "
                    f"{_money(plan.taxable_amount)} of taxable receipt** at "
                    f"{float(marginal_rate):.0%}. Federal only, nominal, and a "
                    "floor: state tax, NIIT on investment income, and the "
                    "bracket this pushes you into are all on top.")
            if plan.shortfall:
                line += (f" Against {_money(float(withheld))} withheld, the "
                         f"gap is **{_money(plan.shortfall)}**.")
            elif withheld is None:
                line += " Nothing recorded as withheld — record it."
            plan.findings.append(Finding("estimated tax", "blocker", line))

        if indeterminate:
            plan.findings.append(Finding(
                "estimated tax", "gap",
                f"{len(indeterminate)} event(s) could not be characterised and "
                "are **excluded** from that figure, so it understates the bill "
                "by an unknown amount. Do not treat it as the answer."))

    if any(e.kind == "equity_vest" for e in plan.events):
        vest_total = sum(e.amount for e in plan.events if e.kind == "equity_vest")
        rate = (SUPPLEMENTAL_WITHHOLDING_RATE_ABOVE
                if vest_total > SUPPLEMENTAL_WITHHOLDING_THRESHOLD
                else SUPPLEMENTAL_WITHHOLDING_RATE)
        detail = (
            f"**Supplemental withholding is {rate:.0%}, which is a withholding "
            f"rate and not your tax rate.** On {_money(vest_total)} of vesting "
            f"equity that withholds about {_money(vest_total * rate)}.")
        if marginal_rate is not None and float(marginal_rate) > rate:
            gap = vest_total * (float(marginal_rate) - rate)
            detail += (f" At a {float(marginal_rate):.0%} marginal rate the "
                       f"shortfall is roughly **{_money(gap)}** before state "
                       "tax — invisible on the pay stub, and payable in "
                       "April.")
        if vest_total > SUPPLEMENTAL_WITHHOLDING_THRESHOLD:
            detail += (f" Above {_money(SUPPLEMENTAL_WITHHOLDING_THRESHOLD)} "
                       "of supplemental wages in a year the higher mandatory "
                       "rate applies to the excess.")
        plan.findings.append(Finding("withholding", "blocker", detail))

    harbor = safe_harbor_payment(prior_year_tax, prior_year_agi)
    plan.safe_harbor = harbor
    if harbor is not None:
        multiple = (SAFE_HARBOR_PRIOR_YEAR_HIGH_AGI
                    if (prior_year_agi or 0) > SAFE_HARBOR_HIGH_AGI
                    else SAFE_HARBOR_PRIOR_YEAR)
        plan.findings.append(Finding(
            "estimated tax", "note",
            f"**The prior-year safe harbour is {_money(harbor)}** "
            f"({multiple:.0%} of last year's {_money(float(prior_year_tax))} "
            "tax, via withholding plus estimated payments across the year). "
            "Meet it and the §6654 underpayment penalty does not apply however "
            "large the final bill turns out to be — which matters because in a "
            "windfall year nobody can yet compute the current-year figure. The "
            f"alternative harbour is {SAFE_HARBOR_CURRENT_YEAR:.0%} of the "
            "current year's tax. Estimated payments are quarterly and the "
            "penalty is assessed per quarter, so a single catch-up payment in "
            "January does not cure an underpaid Q3."))
    else:
        plan.findings.append(Finding(
            "estimated tax", "gap",
            "Prior-year tax is not recorded, so the safe harbour cannot be "
            "computed. It is a single number on last year's return and it is "
            "the cheapest insurance available against an underpayment "
            "penalty."))

    # ── foreign source: Form 3520, imported ─────────────────────────────
    foreign_total = sum(e.amount for e in plan.events if e.source_foreign)
    unstated = [e for e in plan.events if e.source_foreign is None]
    if foreign_total > _rep.FOREIGN_GIFT_THRESHOLD:
        plan.findings.append(Finding(
            "reporting", "blocker",
            f"**Form 3520 is required.** {_money(foreign_total)} of gifts or "
            f"bequests from a foreign person exceeds the "
            f"{_money(_rep.FOREIGN_GIFT_THRESHOLD)} aggregate threshold. **No "
            "tax is due** — this is reporting only — but the penalty for not "
            "filing is a percentage of the amount received, which makes it one "
            "of the most expensive forms to overlook. It is due with the "
            "return, and an inheritance from family abroad is the ordinary "
            "trigger. See `foreign-reporting-audit`, which also covers the "
            "FBAR and FATCA consequences of the account the money landed in."))
    elif unstated:
        plan.findings.append(Finding(
            "reporting", "gap",
            "**`source_foreign` is not recorded** on "
            f"{len(unstated)} event(s). Above "
            f"{_money(_rep.FOREIGN_GIFT_THRESHOLD)} from a nonresident alien "
            "or foreign estate, Form 3520 is required — reporting only, no "
            "tax, percentage-of-amount penalty for missing it. Whether the "
            "*donor* was foreign is the test, not where the money was wired "
            "from."))
    elif foreign_total:
        plan.findings.append(Finding(
            "reporting", "ok",
            f"{_money(foreign_total)} from a foreign source is below the "
            f"{_money(_rep.FOREIGN_GIFT_THRESHOLD)} Form 3520 threshold. The "
            "threshold is aggregate across the year and across related "
            "donors — a second gift from the same family later in the year "
            "can cross it retroactively."))

    # ── beneficiaries on the new accounts ───────────────────────────────
    naked = new_accounts_without_beneficiaries or []
    if naked:
        plan.findings.append(Finding(
            "beneficiaries", "blocker",
            f"**{len(naked)} new or newly-large account(s) have no "
            f"beneficiary recorded:** {', '.join(naked)}. A designation "
            "overrides the will, so an account opened this month to hold the "
            "windfall is currently outside the estate plan entirely. Run "
            "`beneficiary-audit` — it is the check, this is only the "
            "reminder."))
    else:
        plan.findings.append(Finding(
            "beneficiaries", "note",
            "**Name a beneficiary on every account the money touches, "
            "including the one it is merely parked in.** New accounts are the "
            "commonest source of an unrevised estate plan, because nobody "
            "thinks of a holding account as part of one. `beneficiary-audit` "
            "does the checking."))

    # ── the two-year echo ───────────────────────────────────────────────
    if medicare_within_lookback:
        plan.findings.append(Finding(
            "irmaa", "note",
            f"**A large income year raises Medicare premiums {IRMAA_LOOKBACK_YEARS} "
            "years later.** IRMAA is set from the modified AGI on the return "
            f"filed {IRMAA_LOOKBACK_YEARS} years earlier, so the surcharge "
            "lands long after the money is spent and feels unrelated to it. It "
            "is a cliff, not a taper — a dollar over a bracket costs the whole "
            "step — and it applies for one year only, then falls away as "
            "income normalises. **A windfall is not a life-changing event for "
            "SSA-44 purposes**; that form's list is specific (work stoppage, "
            "divorce, death of a spouse, and so on) and receiving money is not "
            "on it. Budget for the surcharge rather than planning to appeal "
            "it. See `medicare-enrollment-timing` when it ships."))
    if aca_marketplace_coverage:
        plan.findings.append(Finding(
            "aca", "blocker",
            "**Marketplace coverage plus a windfall is a repayment risk this "
            "year, not in two.** The premium tax credit is advanced on "
            "estimated income and reconciled on the return; income above the "
            "eligibility ceiling means repaying the advance, and for a "
            "household over the limit the repayment is not capped. Update the "
            "marketplace estimate now — mid-year is far cheaper than "
            "reconciliation."))

    return plan


# ── marriage ────────────────────────────────────────────────────────────────

#: AGI floor for the itemised medical deduction. The reason separate filing can
#: win: one spouse's large medical bills measured against one spouse's AGI
#: clear a much lower floor than the same bills against a joint AGI.
MEDICAL_DEDUCTION_AGI_FLOOR = 0.075

#: Roth IRA contributions phase out from zero to this MAGI for someone married
#: filing separately who lived with their spouse at any point in the year.
#: Effectively a bar on direct Roth contributions, and one of the real costs of
#: choosing separate.
MFS_ROTH_PHASEOUT_CEILING = 10_000

MARRIAGE_SOURCE = (
    "IRC §6013 (joint returns and joint liability); IRC §213(a) (medical "
    "floor); IRC §408A(c)(3) (MFS Roth phase-out); IRC §2010(c)(5)(A) "
    "(portability election requires a filed Form 706)"
)
MARRIAGE_VERIFIED = "unverified — check against irs.gov"


@dataclass
class FilingComparison:
    joint_tax: float | None
    separate_tax: float | None
    tax_delta: float | None
    idr_delta: float | None
    net_advantage: float | None
    recommendation: str
    findings: list[Finding] = field(default_factory=list)


def compare_filing_status(
    *,
    joint_tax: float | None,
    separate_tax_combined: float | None,
    idr_payment_joint: float | None = None,
    idr_payment_separate: float | None = None,
) -> FilingComparison:
    """Compare joint against separate on figures the caller supplies.

    Deliberately not a tax engine. Both totals come from running the return
    both ways in whatever software prepares it — which takes ten minutes and
    is exact, where a bracket table here would be approximate and would go
    stale. The arithmetic worth having is the *netting*: what separate filing
    costs in tax against what it saves on an income-driven loan payment.
    """
    c = FilingComparison(joint_tax, separate_tax_combined, None, None, None,
                         "cannot be determined")

    if joint_tax is None or separate_tax_combined is None:
        c.findings.append(Finding(
            "filing status", "blocker",
            "**Both totals are needed and at least one is missing.** Run the "
            "return both ways in your tax software and record "
            "`tax_if_joint` and `tax_if_separate_combined` (the sum of the two "
            "separate returns). This is ten minutes of work and it is exact; "
            "no rule of thumb substitutes for it, because whether a couple "
            "faces a marriage penalty or a marriage bonus depends on how "
            "evenly the two incomes are split and on nothing else that "
            "generalises."))
        return c

    c.tax_delta = float(separate_tax_combined) - float(joint_tax)

    if idr_payment_joint is not None and idr_payment_separate is not None:
        c.idr_delta = float(idr_payment_joint) - float(idr_payment_separate)
    c.net_advantage = (c.idr_delta or 0.0) - c.tax_delta

    if c.tax_delta <= 0:
        c.recommendation = "separate"
        c.findings.append(Finding(
            "filing status", "note",
            f"Separate filing costs **no more** in tax "
            f"({_money(-c.tax_delta)} less). Unusual but real — it happens "
            "where both incomes are similar and one spouse has large "
            "AGI-floored deductions. Confirm the figures before acting on a "
            "counter-intuitive result."))
    elif c.net_advantage > 0:
        c.recommendation = "separate"
        c.findings.append(Finding(
            "filing status", "note",
            f"**Separate wins by {_money(c.net_advantage)}/yr.** It costs "
            f"{_money(c.tax_delta)} more in tax but saves "
            f"{_money(c.idr_delta or 0)} in income-driven student-loan "
            "payments, because most IDR plans measure the payment on the "
            "borrower's income alone when the borrower files separately. "
            "Two caveats that can reverse this: **in a community property "
            "state, income is split between spouses regardless of how you "
            "file**, which can erase the saving entirely; and the plan rules "
            "here change with litigation and regulation, so confirm the "
            "current treatment for the specific plan before filing. Neither "
            "is encoded in this module."))
    else:
        c.recommendation = "joint"
        c.findings.append(Finding(
            "filing status", "note",
            f"**Joint wins by {_money(-c.net_advantage)}/yr.** Separate filing "
            f"costs {_money(c.tax_delta)} more in tax"
            + (f" against {_money(c.idr_delta or 0)} of loan-payment saving."
               if c.idr_delta else
               ", with no offsetting loan-payment saving recorded.")))

    if c.recommendation == "separate":
        c.findings.append(Finding(
            "filing status", "gap",
            "**What separate filing also costs, none of which is in the "
            "figures above:** no student-loan interest deduction, no education "
            "credits, a Roth IRA phase-out running from zero to "
            f"{_money(MFS_ROTH_PHASEOUT_CEILING)} of MAGI for spouses who "
            "lived together at any point in the year, a halved capital-loss "
            "allowance, and a requirement that **both** spouses itemise or "
            "**both** take the standard deduction. Net those against the "
            "advantage before deciding."))

    c.findings.append(Finding(
        "liability", "note",
        "**A joint return creates joint and several liability.** Each spouse "
        "is liable for the whole tax, including on income they did not earn "
        "and understatements they did not know about, and that survives "
        "divorce. Innocent-spouse relief exists and is neither quick nor "
        "certain. Where one spouse has opaque finances — a business, foreign "
        "accounts, unfiled years — separate filing buys liability separation "
        "that is worth real money even when it costs tax. That is a legal "
        "judgement, not an arithmetic one."))
    return c


@dataclass
class MarriagePlan:
    filing: FilingComparison
    findings: list[Finding] = field(default_factory=list)

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "blocker"]


def assess_marriage(
    *,
    members: list[dict],
    domicile: dict | None,
    joint_tax: float | None,
    separate_tax_combined: float | None,
    idr_payment_joint: float | None = None,
    idr_payment_separate: float | None = None,
    medical_expenses: float | None = None,
    lower_earner_agi: float | None = None,
    household_agi: float | None = None,
    accounts_with_stale_beneficiaries: list[str] | None = None,
    monthly_spending: float | None = None,
    independent_access: dict | None = None,
) -> MarriagePlan:
    """The decisions a marriage forces, in the order they bite.

    The estate half is delegated to `status.audit` — the non-citizen-spouse
    marital-deduction rule is encoded there and restating it here would create
    the second copy that eventually disagrees with the first.
    """
    filing = compare_filing_status(
        joint_tax=joint_tax,
        separate_tax_combined=separate_tax_combined,
        idr_payment_joint=idr_payment_joint,
        idr_payment_separate=idr_payment_separate,
    )
    plan = MarriagePlan(filing=filing, findings=list(filing.findings))

    # ── the medical-deduction case for separate ─────────────────────────
    if medical_expenses:
        if lower_earner_agi is None or household_agi is None:
            plan.findings.append(Finding(
                "filing status", "gap",
                f"{_money(float(medical_expenses))} of medical expenses are "
                "recorded but the AGI figures are not, so the separate-filing "
                "case cannot be tested. The deduction is only the excess over "
                f"{MEDICAL_DEDUCTION_AGI_FLOOR:.1%} of AGI, and which AGI it is "
                "measured against is the entire question."))
        else:
            joint_floor = float(household_agi) * MEDICAL_DEDUCTION_AGI_FLOOR
            sep_floor = float(lower_earner_agi) * MEDICAL_DEDUCTION_AGI_FLOOR
            joint_ded = max(0.0, float(medical_expenses) - joint_floor)
            sep_ded = max(0.0, float(medical_expenses) - sep_floor)
            if sep_ded > joint_ded:
                plan.findings.append(Finding(
                    "filing status", "note",
                    f"**The medical deduction argues for separate.** "
                    f"{_money(float(medical_expenses))} of expenses clears a "
                    f"{_money(sep_floor)} floor "
                    f"({MEDICAL_DEDUCTION_AGI_FLOOR:.1%} of the lower earner's "
                    f"AGI) giving {_money(sep_ded)} deductible, against "
                    f"{_money(joint_ded)} on the joint floor of "
                    f"{_money(joint_floor)} — a difference of "
                    f"{_money(sep_ded - joint_ded)} of deduction. Worth the "
                    "marginal rate applied to it, and only if the spouse with "
                    "the expenses also itemises. It is already inside "
                    "`tax_if_separate_combined` if that figure was produced "
                    "properly; check that it was rather than adding it twice."))
            else:
                plan.findings.append(Finding(
                    "filing status", "ok",
                    f"Medical expenses of {_money(float(medical_expenses))} do "
                    f"not beat the joint floor by enough to argue for separate "
                    f"filing ({_money(joint_ded)} joint vs {_money(sep_ded)} "
                    "separate)."))

    # ── beneficiaries: the most-forgotten item ──────────────────────────
    stale = accounts_with_stale_beneficiaries or []
    plan.findings.append(Finding(
        "beneficiaries", "blocker" if stale else "note",
        (f"**{len(stale)} account(s) still carry a pre-marriage designation:** "
         f"{', '.join(stale)}. " if stale else
         "**Beneficiary designations are the single most-forgotten item in a "
         "marriage, and they override the will.** ")
        + "Two rules that differ and surprise people: an **ERISA plan — a "
        "401(k), a pension — makes the spouse the beneficiary automatically "
        "on marriage, and naming anyone else requires the spouse's notarised "
        "written consent**; an **IRA has no such protection**, so a parent or "
        "an ex named years ago stays named until someone files a new form. "
        "Marrying does not revoke anything on an IRA. `beneficiary-audit` "
        "does the account-by-account check."))

    # ── estate, delegated ───────────────────────────────────────────────
    st = _sta.audit(members, domicile=domicile)
    for f in st.findings:
        if f.area == "estate":
            plan.findings.append(Finding(
                "estate", f.severity,
                f.detail + " *(from `citizenship-status-review`.)*"))

    plan.findings.append(Finding(
        "estate", "note",
        "**Marriage changes estate treatment substantially, and mostly "
        "favourably.** Transfers between US-citizen spouses are unlimited, in "
        "life and at death, and the unused portion of a deceased spouse's "
        "federal exemption can pass to the survivor — but **portability is an "
        "election that requires a Form 706 to be filed, even when no estate "
        "tax is owed and no return would otherwise be required.** Missing that "
        "filing forfeits the exemption permanently, and it is missed routinely "
        "because the family is told there is no tax to pay. See "
        "`estate-document-review`; wills, powers of attorney and titling all "
        "need revisiting on the same occasion."))

    # ── combining accounts, as a policy ─────────────────────────────────
    detail = (
        "**Decide combining as a policy rather than arriving at one by "
        "default.** All three shapes work — fully joint, fully separate with "
        "an agreed split of shared costs, or joint for shared spending with "
        "personal accounts alongside — and the failure mode is not picking "
        "any of them, so accounts merge by accident and nobody can say who "
        "owns what. Two constraints worth applying to whichever is chosen: "
        "each spouse keeps **independent access to money in their own name**, "
        "which is a resilience point rather than a trust one (a frozen joint "
        "account after a death, an incapacity, or a bank's fraud hold leaves "
        "the other spouse with nothing); and each keeps an **individual credit "
        "history**, which an authorised-user card does not reliably build.")
    if monthly_spending:
        floor = float(monthly_spending) * _cash.MIN_BUFFER_MONTHS
        detail += (f" Sizing the first one: {_cash.MIN_BUFFER_MONTHS:.0f} "
                   f"months of household spending is {_money(floor)}, and "
                   f"that is the floor `cash.py` refuses to self-insure below "
                   "— a reasonable minimum for the individually-titled "
                   "account, not a target for it.")
    plan.findings.append(Finding("accounts", "note", detail))

    if independent_access is not None:
        without = [k for k, v in independent_access.items() if not v]
        if without:
            plan.findings.append(Finding(
                "accounts", "gap",
                f"**No individually-titled account recorded for "
                f"{', '.join(without)}.** See above: this is about what "
                "happens when an account is frozen, not about trust."))

    return plan


# ── divorce ─────────────────────────────────────────────────────────────────

#: §72(t) additional tax on an early distribution. Named here because the QDRO
#: exception to it is the one piece of divorce arithmetic that is both large
#: and irreversible if sequenced wrongly.
EARLY_DISTRIBUTION_PENALTY = 0.10

DIVORCE_SOURCE = (
    "IRC §1041 (transfers incident to divorce; carryover basis); IRC §414(p) "
    "(QDRO); IRC §408(d)(6) (IRA transfer incident to divorce); IRC "
    "§72(t)(2)(C) (QDRO exception to the early-distribution tax); ERISA §514 "
    "and Egelhoff v. Egelhoff (state revocation-on-divorce statutes preempted "
    "for ERISA plans); TCJA §11051 (alimony, agreements after 2018)"
)
DIVORCE_VERIFIED = "unverified — check against irs.gov and with counsel"


@dataclass(frozen=True)
class Mechanism:
    kind: str
    known: bool
    instrument: str = "unknown"
    detail: str = ""


_MECHANISM: dict[str, Mechanism] = {
    "traditional_401k": Mechanism(
        "traditional_401k", True, "QDRO",
        "A qualified plan can only be divided by a **qualified domestic "
        "relations order** — a separate court order, drafted to the plan's "
        "specification and accepted by the plan administrator. A divorce "
        "decree that says the account is split is not a QDRO and the plan will "
        "not act on it. Without one, a participant who withdraws and hands "
        "over the money has taken a taxable distribution, personally, with the "
        "early-distribution tax on top."),
    "roth_401k": Mechanism(
        "roth_401k", True, "QDRO",
        "Same QDRO requirement as a pre-tax 401(k); the Roth character and the "
        "existing holding period carry to the alternate payee."),
    "pension": Mechanism(
        "pension", True, "QDRO",
        "A defined-benefit pension also divides by QDRO, and the order must "
        "specify the form of the split — shared-payment or separate-interest, "
        "and what happens to survivor benefits. Those choices are worth more "
        "than the headline percentage and are difficult to revisit once the "
        "order is entered."),
    "traditional_ira": Mechanism(
        "traditional_ira", True, "transfer incident to divorce",
        "An IRA is **not** a qualified plan and does not use a QDRO. It moves "
        "by a transfer incident to divorce under §408(d)(6), authorised by the "
        "decree or separation agreement and executed as a direct "
        "trustee-to-trustee transfer. Taking a distribution and re-depositing "
        "it instead is a taxable event for the original owner."),
    "roth_ira": Mechanism(
        "roth_ira", True, "transfer incident to divorce",
        "A Roth IRA is not a qualified plan either, so no QDRO: a direct "
        "trustee-to-trustee transfer authorised by the decree. The five-year "
        "clocks follow the account."),
    "hsa": Mechanism(
        "hsa", True, "transfer incident to divorce",
        "An HSA transfers to a spouse or former spouse under a decree without "
        "tax, and remains an HSA in their hands."),
    "taxable": Mechanism(
        "taxable", True, "§1041 transfer",
        "A transfer between spouses, or former spouses incident to divorce, is "
        "**not a taxable event** — and **basis carries over unchanged**. The "
        "recipient inherits the embedded gain along with the shares, which is "
        "the whole reason the after-tax column differs from the statement "
        "one."),
    "real_estate": Mechanism(
        "real_estate", True, "§1041 transfer",
        "Transfers under §1041 with carryover basis, but the residence has its "
        "own layer — the capital-gain exclusion on a primary home depends on "
        "ownership and use tests that a move-out starts eroding, and the "
        "mortgage is a separate contract the decree cannot rewrite. Refinance "
        "or sale terms belong in the agreement. This module does not value "
        "property."),
}


def transfer_mechanism(kind: str | None) -> Mechanism:
    if not kind:
        return Mechanism("??", False)
    return _MECHANISM.get(str(kind).strip().lower(), Mechanism(str(kind), False))


def mechanism_kinds_available() -> list[str]:
    return sorted(_MECHANISM)


#: Account kinds whose whole balance is ordinary income when withdrawn.
PRE_TAX_KINDS = ("traditional_401k", "traditional_ira", "pension")
#: Account kinds where a qualified withdrawal is tax-free.
TAX_FREE_KINDS = ("roth_401k", "roth_ira", "hsa")
#: Account kinds taxed on the embedded gain only, and therefore needing basis.
BASIS_KINDS = ("taxable", "real_estate")


@dataclass
class SplitLine:
    name: str
    kind: str
    to: str | None
    nominal: float
    after_tax: float | None
    embedded_gain: float | None
    mechanism: Mechanism
    note: str = ""

    @property
    def determinable(self) -> bool:
        return self.after_tax is not None


@dataclass
class Split:
    lines: list[SplitLine] = field(default_factory=list)
    nominal_by_party: dict = field(default_factory=dict)
    after_tax_by_party: dict = field(default_factory=dict)
    undetermined: float = 0.0
    findings: list[Finding] = field(default_factory=list)

    @property
    def nominal_total(self) -> float:
        return sum(self.nominal_by_party.values())

    @property
    def after_tax_total(self) -> float:
        return sum(self.after_tax_by_party.values())

    @property
    def nominal_gap(self) -> float:
        v = list(self.nominal_by_party.values())
        return abs(v[0] - v[1]) if len(v) == 2 else 0.0

    @property
    def after_tax_gap(self) -> float:
        v = list(self.after_tax_by_party.values())
        return abs(v[0] - v[1]) if len(v) == 2 else 0.0

    @property
    def complete(self) -> bool:
        return self.undetermined == 0 and all(l.determinable for l in self.lines)


def after_tax_value(
    asset: dict,
    *,
    ordinary_rate: float,
    capital_gains_rate: float,
) -> tuple[float | None, float | None, str]:
    """Spendable value of one asset, and its embedded gain.

    Returns `(after_tax, embedded_gain, note)`. `None` means **cannot be
    determined** — never zero, and never the nominal value standing in for it.
    A missing basis on a taxable account is the common case and it is a
    finding, because assuming basis equals value is assuming the gain away in
    exactly the direction that makes an unequal split look equal.
    """
    kind = str(asset.get("kind") or "").strip().lower()
    value = float(asset.get("value") or 0)

    if kind in PRE_TAX_KINDS:
        return value * (1 - ordinary_rate), None, (
            f"Ordinary income on the whole balance at {ordinary_rate:.0%}.")
    if kind in TAX_FREE_KINDS:
        return value, None, (
            "Tax-free if the qualification conditions hold — the Roth "
            "five-year and age tests, or a qualified medical expense for an "
            "HSA. Treated at face value here; if a party will need the money "
            "before those conditions are met, it is worth less than this.")
    if kind in BASIS_KINDS:
        basis = asset.get("basis")
        if basis is None:
            return None, None, (
                "**Basis not recorded, so the after-tax value cannot be "
                "determined.** Not the same as a zero gain. The custodian has "
                "it; get the lot-level detail rather than a total, because "
                "which lots move changes the answer.")
        gain = max(0.0, value - float(basis))
        return value - gain * capital_gains_rate, gain, (
            f"{_money(gain)} embedded gain, taxed at {capital_gains_rate:.0%} "
            "on sale. Basis carries over on the transfer, so the tax follows "
            "whoever receives it.")
    return None, None, (
        f"Kind `{kind or '(none)'}` is not in the table, so it cannot be "
        "valued after tax. Known kinds: "
        f"{', '.join(mechanism_kinds_available())}.")


def split_assets(
    assets: list[dict],
    *,
    ordinary_rate: float | None,
    capital_gains_rate: float | None,
    party_labels: tuple[str, str] = ("a", "b"),
) -> Split:
    """After-tax value of a proposed split, party by party.

    Each asset carries `to`, naming the party who receives it. The output is
    the gap between what the two sides receive **after tax**, which is the
    number the negotiation should be conducted in and almost never is.
    """
    s = Split()
    assets = assets or []

    if not assets:
        s.findings.append(Finding(
            "split", "gap", "**No assets recorded.** Nothing to compare."))
        return s
    if ordinary_rate is None or capital_gains_rate is None:
        s.findings.append(Finding(
            "split", "blocker",
            "**Both an ordinary rate and a capital-gains rate are needed and "
            "at least one is missing.** `assumptions.marginal_tax_rate` and "
            "`assumptions.capital_gains_rate`. Without them every account "
            "looks like its statement balance, which is the error this whole "
            "skill exists to correct. Note that the relevant rates are the "
            "*post-divorce* ones — single or head of household, on one "
            "income — not the joint rates on last year's return."))
        return s

    for p in party_labels:
        s.nominal_by_party[p] = 0.0
        s.after_tax_by_party[p] = 0.0

    for i, a in enumerate(assets):
        kind = str(a.get("kind") or "").strip().lower()
        at, gain, note = after_tax_value(
            a, ordinary_rate=float(ordinary_rate),
            capital_gains_rate=float(capital_gains_rate))
        line = SplitLine(
            name=a.get("name") or kind or f"#{i}",
            kind=kind,
            to=a.get("to"),
            nominal=float(a.get("value") or 0),
            after_tax=at,
            embedded_gain=gain,
            mechanism=transfer_mechanism(kind),
            note=note,
        )
        s.lines.append(line)

        if line.to in s.nominal_by_party:
            s.nominal_by_party[line.to] += line.nominal
            if at is None:
                s.undetermined += line.nominal
            else:
                s.after_tax_by_party[line.to] += at
        elif line.to is None:
            s.findings.append(Finding(
                "split", "gap",
                f"`{line.name}` is not assigned to a party, so it is outside "
                "both totals."))
        else:
            s.findings.append(Finding(
                "split", "gap",
                f"`{line.name}` is assigned to `{line.to}`, which is not one "
                f"of {party_labels}."))

    # ── the finding this module exists for ──────────────────────────────
    if s.undetermined:
        s.findings.append(Finding(
            "split", "blocker",
            f"**{_money(s.undetermined)} of assets could not be valued after "
            "tax**, so the comparison below is incomplete and understates the "
            "true gap by an unknown amount. Fix the missing inputs before "
            "treating any of it as a negotiating position."))

    if s.complete and len(party_labels) == 2:
        p, q = party_labels
        drift = s.after_tax_gap - s.nominal_gap
        if drift > 0:
            favoured = (p if s.after_tax_by_party[p] > s.after_tax_by_party[q]
                        else q)
            s.findings.append(Finding(
                "split", "blocker",
                f"**This split is {_money(s.nominal_gap)} apart on paper and "
                f"{_money(s.after_tax_gap)} apart after tax** — "
                f"{_money(drift)} of the difference is embedded tax that the "
                f"nominal figures hide, and it runs in favour of `{favoured}`. "
                "A dollar of Roth, a dollar of pre-tax retirement and a dollar "
                "of appreciated stock are three different amounts of spendable "
                "money. Equalising the paper totals therefore produces an "
                "unequal settlement, and it is the most common and most "
                "expensive error in an otherwise amicable division. "
                f"Equalising after tax instead means moving about "
                f"{_money(s.after_tax_gap / 2)} of after-tax value the other "
                "way — in whichever account type makes that arithmetic work."))
        else:
            s.findings.append(Finding(
                "split", "ok",
                f"After-tax gap {_money(s.after_tax_gap)} against a nominal "
                f"gap of {_money(s.nominal_gap)} — the tax character is not "
                "distorting this split. Worth having checked; it usually "
                "does."))

    # ── mechanisms ──────────────────────────────────────────────────────
    seen: set[str] = set()
    for line in s.lines:
        if line.kind in seen:
            continue
        seen.add(line.kind)
        if not line.mechanism.known:
            s.findings.append(Finding(
                "mechanism", "blocker",
                f"**`{line.kind or '(none)'}` is not in the mechanism table**, "
                "so how it may be divided without tax is not stated here. Do "
                "not infer it from a kind that is."))
        else:
            s.findings.append(Finding(
                "mechanism", "note",
                f"**{line.kind} → {line.mechanism.instrument}.** "
                f"{line.mechanism.detail}"))

    if any(l.kind in ("traditional_401k", "roth_401k", "pension")
           for l in s.lines):
        s.findings.append(Finding(
            "mechanism", "blocker",
            "**Sequencing note on the QDRO, because it is irreversible.** An "
            "alternate payee who wants cash rather than a rolled-over account "
            "can take it **directly from the plan under the QDRO free of the "
            f"{EARLY_DISTRIBUTION_PENALTY:.0%} early-distribution tax** — "
            "ordinary income tax still applies. That exception is lost the "
            "moment the money is rolled into an IRA, where the ordinary "
            "early-withdrawal rules resume. Anyone who will need part of the "
            "money before the §72(t) age in `limits.py` should take it at that "
            "single point or not at all. Draft the order before the decree is "
            "final and have the plan administrator pre-approve it; a rejected "
            "QDRO after a finalised divorce means going back to court."))

    s.findings.append(Finding(
        "beneficiaries", "blocker",
        "**Beneficiary designations survive divorce unless somebody files a "
        "new form.** An ex-spouse named in 2014 is still the named beneficiary "
        "the day after the decree. Many states have a statute purporting to "
        "revoke a spousal designation automatically on divorce, and for "
        "**ERISA plans — 401(k)s, pensions, employer life insurance — those "
        "statutes are preempted and do not apply**; the plan pays whoever is "
        "on the form. Settled by the Supreme Court, and litigated repeatedly "
        "because families assume the opposite. Change the form on every "
        "account the moment the decree permits it, and re-check the retirement "
        "plan after any QDRO is executed. `beneficiary-audit` enumerates the "
        "accounts."))

    s.findings.append(Finding(
        "scope", "note",
        "**Alimony, for agreements executed after 2018, is neither deductible "
        "to the payer nor income to the recipient** — the reverse of the "
        "long-standing rule, and pre-2019 agreements keep the old treatment "
        "unless modified to adopt the new one. That is a factual statement "
        "about tax character. **How much support is appropriate, and every "
        "question involving children, is outside this module entirely.**"))

    return s


def _money(x) -> str:
    if x is None:
        return "unknown"
    return f"${x:,.0f}"
