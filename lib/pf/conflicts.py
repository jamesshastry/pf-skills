"""Where two skills give the same household opposite instructions.

## The gap this closes

Review finding A6. Every skill here is individually correct and each is tested
in isolation. Nothing tests the *edges between them* — and some of those edges
are contradictions.

The worked example: `roth-conversion-window` tells a household to deliberately
**raise** taxable income in early retirement, to fill low brackets before RMDs
begin. `aca-subsidy-optimization` tells the same household to **suppress**
modified AGI in exactly those years, because the premium tax credit tapers.
Both are right. For a household retiring before 65, they are talking about the
same years.

A household running one skill sees confident advice and no hint that the other
exists. That is a worse failure than either skill being wrong, because there is
nothing on the page to be suspicious of.

## Why a registry rather than cross-imports

`education-funding` reaches into `retirement.assess_readiness` to apply the
retirement-first rule, and that coupling is earned. Doing it for every pair
would produce a dependency graph nobody can reason about, and the roadmap's own
filter — small schema slice, one decision — would stop meaning anything.

So conflicts are declared **data**, in one place, with the condition that makes
each live. Adding a skill means asking whether it contradicts an existing one;
the answer lives here rather than in either skill.

## What a conflict is, and is not

A conflict is two pieces of **correct** advice that cannot both be followed.
Not a bug, not a duplication, and not a disagreement about facts. The
resolution is almost never "one of them is wrong" — it is a trade-off the
household has to price, and the registry's job is to make sure they know it
exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class Conflict:
    key: str
    skills: tuple[str, ...]
    #: What each side tells the household to do — stated as the opposition.
    tension: str
    #: When it actually bites, rather than when it theoretically could.
    trigger: str
    #: How to resolve it. Never "pick one".
    resolution: str
    #: Returns True when this household's facts make it live.
    applies: Callable[[dict], bool] = lambda facts: True
    #: Module that computes the size of this conflict, where one exists. The
    #: registry answers "does this apply", cheaply and for every pair; a
    #: quantifier answers "and how much does it cost", for a few. Naming it
    #: here stops the two being mistaken for duplicates of each other.
    quantified_by: str = ""


def _dig(facts: dict, dotted: str):
    from . import facts as F
    return F._dig(facts, dotted)


def _retires_before_medicare(facts: dict) -> bool:
    age = _dig(facts, "retirement.planned_retirement_age")
    return age is not None and age < 65


def _has_business(facts: dict) -> bool:
    return bool(_dig(facts, "business"))


def _buying_property(facts: dict) -> bool:
    return bool(_dig(facts, "housing.purchase"))


def _housing_affordability_plan(facts: dict) -> bool:
    return bool(_dig(facts, "housing.affordability"))


def _housing_liquidation_with_wash_policy(facts: dict) -> bool:
    return bool(
        _dig(facts, "housing.affordability.funding.taxable_liquidation")
        and _dig(facts, "portfolio.wash_sale"))


def _rental_first_home(facts: dict) -> bool:
    return _dig(facts, "housing.transition.kind") == "rental_then_owner"


def _employer_income_stress(facts: dict) -> bool:
    members = _dig(facts, "household.members") or []
    scenarios = _dig(facts, "cash_flow.scenarios") or []
    return (
        any(m.get("employer") and float(m.get("income_annual") or 0) > 0
            for m in members)
        and any(s.get("kind") == "conservative" for s in scenarios)
    )


def _harvesting_and_rebalancing(facts: dict) -> bool:
    """Driven by the facts that establish the condition, not inferred.

    An earlier version required a balance-sheet row that was simultaneously
    `tier: liquid` and `asset_class: equity`. No such row existed on the
    shipped fixture — the equity sits nested under a retirement row, and the
    vocabulary is `us_equity`/`intl_equity` rather than `equity` — so the
    household whose direct-index provider harvests continuously was told this
    conflict was *dormant*. A false negative from a safety net is worse than
    no safety net: it asserts the edge was checked and is clear.
    """
    ws = _dig(facts, "portfolio.wash_sale") or {}
    harvesting = bool(ws.get("harvesting_continuous")
                      or ws.get("excluded_securities")
                      or ws.get("direct_index_provider"))
    return harvesting and bool(_dig(facts, "portfolio.target_allocation"))


def _has_pretax_balance(facts: dict) -> bool:
    from . import facts as F
    return F.tier_total(facts, F.AGE_RESTRICTED) > 0


def _conversions_planned(facts: dict) -> bool:
    """Any signal that conversions are contemplated."""
    return bool(_dig(facts, "crossborder.planned_conversion_annual")
                or _dig(facts, "retirement.planned_conversion_annual")
                or _dig(facts, "retirement.planned_retirement_age"))


def _roth_destination_contested(facts: dict) -> bool:
    """A destination whose Roth treatment is not settled, plus a conversion."""
    if not _conversions_planned(facts):
        return False
    from . import crossborder as X
    for code in (_dig(facts, "crossborder.destinations") or []):
        c = code.get("country") if isinstance(code, dict) else code
        rec = X.country_for(c)
        if not rec.known:
            return True
        if getattr(rec, "inverts_conversion_advice", False):
            return True
    return False


def _depreciating_business_assets(facts: dict) -> bool:
    return bool(_dig(facts, "business.assets"))


def _rental_losses_in_play(facts: dict) -> bool:
    return bool(_dig(facts, "real_estate"))


def _holds_pfics(facts: dict) -> bool:
    return bool(_dig(facts, "pfic_holdings"))


def _charitable_intent(facts: dict) -> bool:
    return bool(_dig(facts, "charity"))


def _feie_and_ira(facts: dict) -> bool:
    return bool(_dig(facts, "expat.planned_ira_contribution"))


def _non_citizen_spouse_with_assets(facts: dict) -> bool:
    """A spouse who is not a US citizen, and a balance sheet to retitle.

    Driven by the facts that establish the condition rather than by a
    downstream conclusion: `citizenship-status-review` already records the
    status, and `probate-exposure` will recommend retitling whenever anything
    is exposed or unchecked.
    """
    members = _dig(facts, "household.members") or []
    spouse = next((m for m in members if m.get("role") == "spouse"), None)
    if not spouse:
        return False
    status = spouse.get("us_status")
    cits = spouse.get("citizenship") or []
    non_citizen = (status is not None and status != "citizen") or (
        bool(cits) and "US" not in cits)
    return non_citizen and bool(_dig(facts, "household.balance_sheet"))


REGISTRY: tuple[Conflict, ...] = (
    Conflict(
        key="probate-titling-vs-non-citizen-spouse",
        skills=("probate-exposure", "citizenship-status-review"),
        tension="One says retitle assets jointly or into the trust, because "
                "that is the cheapest way out of probate. The other records "
                "that the spouse is **not a US citizen**, and the transfer "
                "rules that make retitling cheap for a citizen spouse do not "
                "apply: there is no unlimited marital deduction, and adding a "
                "non-citizen spouse to a title can be a reportable gift "
                "rather than a free administrative step.",
        trigger="A spouse recorded as anything other than a US citizen, and "
                "any account that probate-exposure would recommend retitling.",
        resolution="Do not let the probate answer drive the titling decision "
                   "on its own. Probate cost is a known, bounded, one-off "
                   "administrative fee; a mishandled transfer to a "
                   "non-citizen spouse is a tax question with a much wider "
                   "range and a QDOT may be the instrument that actually "
                   "belongs here. Establish the status question first — it is "
                   "cheap — then decide titling. This registry entry does not "
                   "decide it, and neither skill should.",
        applies=_non_citizen_spouse_with_assets,
    ),
    Conflict(
        key="conversions-vs-aca",
        skills=("roth-conversion-window", "aca-subsidy-optimization"),
        tension="One says **raise** taxable income in early retirement to fill "
                "low brackets before RMDs. The other says **suppress** "
                "modified AGI in those same years, because the premium tax "
                "credit tapers as MAGI rises.",
        trigger="Retiring before 65, so there are years funded on the "
                "individual market before Medicare begins. The conversion "
                "window and the subsidy years are then the same years.",
        resolution="Price it rather than choosing a side. Each converted "
                   "dollar costs tax now *and* some subsidy now, and saves "
                   "tax later. The subsidy loss is immediate and certain; the "
                   "conversion benefit is deferred and depends on future "
                   "rates. A common shape is to convert lightly or not at all "
                   "until Medicare starts, then convert hard between 65 and "
                   "RMDs — but that window may be short, which is exactly the "
                   "trade-off.",
        applies=_retires_before_medicare,
        quantified_by="lib/pf/healthcare.py — magi_conflicts()",
    ),
    Conflict(
        key="conversions-vs-irmaa",
        skills=("roth-conversion-window", "medicare-enrollment-timing"),
        tension="Conversions raise MAGI. IRMAA surcharges look back **two "
                "years**, so income at 63 sets Medicare premiums at 65.",
        trigger="Any conversion in the two years before Medicare enrolment, "
                "or in any year once enrolled.",
        resolution="IRMAA tiers are **cliffs, not slopes** — a dollar over a "
                   "threshold costs the whole step. Size each conversion to "
                   "the headroom under the next tier rather than to a round "
                   "number, and remember the lookback means this year's "
                   "conversion shows up on a premium bill two years from now.",
        # A registry that always fires trains the reader to skip it. No
        # pre-tax balance means nothing to convert.
        applies=_has_pretax_balance,
        quantified_by="lib/pf/healthcare.py — magi_conflicts()",
    ),
    Conflict(
        key="salary-vs-solo401k",
        skills=("entity-structure-comparison", "solo-retirement-plan-choice"),
        tension="Lowering W-2 salary in an S-Corp saves payroll tax and "
                "preserves qualified business income. Raising it increases "
                "the compensation base that the Solo 401(k) employer "
                "contribution is calculated on.",
        trigger="An S-Corp owner-operator funding a Solo 401(k).",
        resolution="The salary that minimises this year's tax is usually not "
                   "the salary that maximises the shelter. Model both "
                   "together — optimising either alone gives the wrong "
                   "number, and the reasonable-salary figure has to survive "
                   "scrutiny regardless.",
        applies=_has_business,
    ),
    Conflict(
        key="downpayment-vs-retirement",
        skills=("housing-affordability", "retirement-readiness"),
        tension="A down payment moves a large sum out of invested assets. "
                "`housing-affordability` uses it at closing while "
                "`retirement-readiness` otherwise projects from a balance "
                "sheet that still includes the pre-close assets.",
        trigger="A purchase under consideration while a retirement projection "
                "is being relied on.",
        resolution="Re-run the retirement projection with the down payment "
                   "and closing costs removed from investable assets, and "
                   "with ownership costs rather than rent in spending. The "
                   "retirement date usually moves, and that movement is part "
                   "of the price of the house.",
        applies=_buying_property,
    ),
    Conflict(
        key="downpayment-vs-emergency-reserve",
        skills=("housing-affordability", "emergency-fund-sizing"),
        tension="Closing funds and the emergency reserve compete for the same "
                "cash, while marketable stock is not cash at par for either "
                "purpose.",
        trigger="A purchase target with a post-close reserve rule.",
        resolution="Treat the reserve as a use at closing, not as money left "
                   "over after the down payment. Count only cash equivalents "
                   "at face value; convert planned securities through the "
                   "taxable sources-and-uses ledger first. A price that needs "
                   "the emergency reserve to close fails the liquidity test.",
        applies=_housing_affordability_plan,
    ),
    Conflict(
        key="housing-cashflow-vs-savings-floor",
        skills=("housing-affordability", "retirement-readiness"),
        tension="A lender may approve debt service that consumes the annual "
                "saving needed for the retirement plan.",
        trigger="An affordability scenario with an explicit savings floor.",
        resolution="Apply the greater of the dollar and gross-income-rate "
                   "savings floors before calling a price feasible. The "
                   "lender maximum remains a separate outer limit, never the "
                   "household target.",
        applies=lambda f: any(
            bool(s.get("minimum_savings"))
            for s in (_dig(f, "cash_flow.scenarios") or [])),
    ),
    Conflict(
        key="housing-liquidation-vs-wash-sale",
        skills=("housing-affordability", "wash-sale-policy",
                "rebalancing-rules"),
        tension="Selling taxable lots for closing can realise gains or losses "
                "while automated purchases or rebalancing can disallow the "
                "loss during the wash-sale window.",
        trigger="A taxable portfolio sale alongside a household wash-sale policy.",
        resolution="Name the lots sold, reserve tax from basis and holding "
                   "period, and clear every purchase channel against the "
                   "exclusion list before relying on a loss. Use new money or "
                   "tax-advantaged trades to rebalance without recreating the "
                   "sold position.",
        applies=_housing_liquidation_with_wash_policy,
    ),
    Conflict(
        key="rental-first-vs-passive-loss",
        skills=("housing-affordability", "passive-loss-eligibility"),
        tension="The rental-first plan may show a tax loss, but §469 can "
                "suspend it instead of reducing the cash cost of the tenant phase.",
        trigger="A home is rented to a tenant before owner occupancy.",
        resolution="Join the proposed property to its §469 activity by label. "
                   "Keep the phase pre-investor-tax and use zero current tax "
                   "benefit unless the gate affirmatively opens; a suspended "
                   "loss is deferred value, not closing-period cash.",
        applies=_rental_first_home,
    ),
    Conflict(
        key="employer-income-vs-housing-stress",
        skills=("housing-affordability", "employer-concentration-risk",
                "equity-comp-review"),
        tension="The same employer can supply salary, bonus, and equity while "
                "also driving the asset decline that accompanies a job loss.",
        trigger="Employer-linked income and a conservative affordability scenario.",
        resolution="Build the conservative case from named compensation "
                   "components, reducing variable and employer-correlated "
                   "income without counting any component twice. Use that "
                   "case for the stress ceiling and keep the current case as "
                   "capacity, not as the sole answer.",
        applies=_employer_income_stress,
    ),
    Conflict(
        key="harvesting-vs-allocation",
        skills=("wash-sale-policy", "rebalancing-rules"),
        tension="Rebalancing buys the asset class that has fallen. Harvesting "
                "sells losses in that same class. A purchase within the "
                "61-day window disallows the loss.",
        trigger="Any taxable account where losses are being harvested — "
                "including automatically by a direct-indexing provider.",
        resolution="Rebalance with **new contributions and tax-advantaged "
                   "accounts first**. Where a taxable purchase is "
                   "unavoidable, check it against the exclusion list. A "
                   "purchase in an IRA disallows the loss **permanently, with "
                   "no basis adjustment**, because the IRA cannot inherit the "
                   "basis — which is why the policy must span every account.",
        applies=_harvesting_and_rebalancing,
    ),
    Conflict(
        key="concentration-vs-charity",
        skills=("employer-concentration-risk", "charitable-giving-strategy"),
        tension="Not opposed, but competing for the same shares: selling at "
                "vest realises gain and diversifies; donating appreciated "
                "shares avoids the gain entirely but gives the asset away.",
        trigger="Concentrated appreciated employer stock plus any charitable "
                "intent.",
        resolution="Donate the **most appreciated** lots and sell the rest. "
                   "Donating avoids the largest embedded gains at no tax cost "
                   "and reduces concentration at the same time; selling "
                   "low-basis shares to fund a cash donation wastes the "
                   "opportunity. Sequence matters more than the totals here.",
        applies=lambda f: bool(_dig(f, "equity_comp")),
    ),
    Conflict(
        key="conversions-vs-roth-portability",
        skills=("roth-conversion-window", "roth-portability-check"),
        tension="One says convert to fill low brackets before RMDs. The other "
                "says a conversion is a **bet that a jurisdiction you may move "
                "to honours the Roth wrapper** — and several do not, taxing "
                "distributions as ordinary income anyway.",
        trigger="Conversions contemplated alongside a destination whose Roth "
                "treatment is contested or simply not in the table.",
        resolution="A conversion is **irreversible** and recharacterisation is "
                   "no longer available, so this is not symmetric: converting "
                   "into a wrapper the destination ignores means paying US tax "
                   "now for nothing. Resolve the destination question, or at "
                   "least its probability, before converting — not after. "
                   "Where the destination is unknown, that uncertainty is "
                   "itself an argument for converting less.",
        applies=_roth_destination_contested,
    ),
    Conflict(
        key="depreciation-vs-qbi",
        skills=("depreciation-election", "entity-structure-comparison"),
        tension="Accelerating cost recovery with §179 or bonus reduces "
                "qualified business income — so it also cuts the §199A "
                "deduction by twenty cents on every accelerated dollar.",
        trigger="An owner-operator business claiming QBI and electing "
                "accelerated depreciation in the same year.",
        resolution="Model them together. The deduction that minimises this "
                   "year's taxable income is not automatically the one that "
                   "maximises after-tax income, because part of it is clawed "
                   "back through a smaller QBI deduction. Bonus can also "
                   "create a loss where §179 cannot, which changes which "
                   "years the benefit lands in.",
        applies=_depreciating_business_assets,
    ),
    Conflict(
        key="losses-vs-magi",
        skills=("passive-loss-eligibility", "aca-subsidy-optimization"),
        tension="Unlocked rental losses and accelerated depreciation **reduce** "
                "AGI — which raises the premium credit and can drop an IRMAA "
                "tier. The MAGI discussion elsewhere treats conversions as the "
                "only lever.",
        trigger="Rental activity with deductible losses in a year where the "
                "premium credit or an IRMAA tier is in play.",
        resolution="This one runs in the household's favour and is routinely "
                   "missed for that reason. Count the losses when computing "
                   "subsidy-relevant MAGI rather than treating the two "
                   "questions separately — and note it cuts the other way on "
                   "disposition, when suspended losses release and recapture "
                   "lands in a single year.",
        applies=_rental_losses_in_play,
    ),
    Conflict(
        key="allocation-vs-pfic",
        skills=("asset-allocation-review", "pfic-divest-or-comply"),
        tension="An allocation target with an international sleeve says buy "
                "more foreign exposure. PFIC says exit foreign pooled funds. "
                "Rebalancing into international through the locally cheapest "
                "vehicle is precisely how a PFIC gets bought.",
        trigger="A target allocation with international exposure alongside any "
                "foreign pooled holding.",
        resolution="Hold the international allocation through **US-domiciled** "
                   "funds. The exposure is the goal; the domicile of the "
                   "wrapper is what creates the problem, and the two are "
                   "separable. This is the same conclusion the India portfolio "
                   "guide reached for a different reason.",
        applies=_holds_pfics,
    ),
    Conflict(
        key="feie-vs-ira",
        skills=("feie-vs-ftc", "contribution-space-audit"),
        tension="Income excluded under the FEIE is **not compensation** for IRA "
                "purposes. Take the exclusion and then fund an IRA and you "
                "have made an excess contribution, which carries an annual "
                "excise charge until corrected.",
        trigger="A FEIE election alongside any planned IRA contribution.",
        resolution="Either leave enough income unexcluded to support the "
                   "contribution, or take the foreign tax credit instead — "
                   "which preserves IRA eligibility and generates carryforward "
                   "credits. `feie-vs-ftc` handles this internally; it is "
                   "registered here so it is visible from the contribution "
                   "side too, where somebody may be looking at space without "
                   "knowing an election was made.",
        applies=_feie_and_ira,
    ),
    Conflict(
        key="charity-vs-magi",
        skills=("charitable-giving-strategy", "aca-subsidy-optimization"),
        tension="Charitable deductions are **below the line**. They reduce "
                "taxable income and do **not** reduce AGI — so they do nothing "
                "for the premium credit, which is computed on MAGI.",
        trigger="Charitable intent in a year where the premium credit matters.",
        resolution="Do not expect bunching to help the subsidy; it will not. A "
                   "qualified charitable distribution from an IRA **does** "
                   "reduce AGI — but only from the qualifying age, which is "
                   "after Medicare begins, so it arrives too late to help the "
                   "credit and helps IRMAA instead. Sequence accordingly.",
        applies=_charitable_intent,
    ),
    Conflict(
        key="hsa-vs-medicare",
        skills=("hsa-review", "medicare-enrollment-timing"),
        tension="One says maximise the HSA. The other says HSA contributions "
                "must stop before Part A begins — and Part A can be backdated, "
                "so contributions in the months before enrolment can become "
                "excess retrospectively.",
        trigger="Approaching Medicare age while still contributing to an HSA.",
        resolution="Stop HSA contributions well before enrolling, and remember "
                   "the backdating: the stop date is set by when Part A "
                   "becomes effective, not by when you filed. Claiming Social "
                   "Security triggers automatic Part A enrolment, which "
                   "catches people who intended to delay both.",
        applies=lambda f: any(
            (m.get("age") or 0) >= 60
            for m in (_dig(f, "household.members") or [])),
    ),
    Conflict(
        key="education-vs-retirement",
        skills=("education-funding", "retirement-readiness"),
        tension="Education funding competes directly with retirement funding "
                "for the same annual savings.",
        trigger="Dependants with an education obligation and a retirement "
                "target not yet reached.",
        resolution="**Already handled inside `education-funding`**, which "
                   "runs the readiness check and applies the "
                   "retirement-first rule rather than stating it. Registered "
                   "here so the resolution is discoverable from either side, "
                   "and so the next person adding a skill sees the precedent "
                   "for reaching across.",
        applies=lambda f: bool(_dig(f, "education.children")),
    ),
)


@dataclass
class ConflictReport:
    live: list[Conflict] = field(default_factory=list)
    dormant: list[Conflict] = field(default_factory=list)

    @property
    def skills_involved(self) -> list[str]:
        return sorted({s for c in self.live for s in c.skills})


def check(facts: dict, *, only_for: str | None = None) -> ConflictReport:
    """Which registered conflicts this household's facts make live.

    `only_for` filters to conflicts involving one skill, so a skill can
    surface its own contradictions in its own report.
    """
    r = ConflictReport()
    for c in REGISTRY:
        if only_for and only_for not in c.skills:
            continue
        try:
            live = bool(c.applies(facts))
        except Exception:
            # A predicate that cannot evaluate is reported as live rather than
            # silently dropped: an unknown is not an absence.
            live = True
        (r.live if live else r.dormant).append(c)
    return r


def for_skill(facts: dict, skill: str) -> list[Conflict]:
    return check(facts, only_for=skill).live


# ── aliased facts ───────────────────────────────────────────────────────────
#
# A different defect from the one above, kept separate because conflating them
# would blunt both. A conflict is two pieces of correct advice. An alias is one
# real-world quantity recorded under two key names, read by two modules that
# cannot see each other.
#
# It is the failure `CONTRIBUTING.md` names — "a figure computed in two places
# eventually disagrees with itself" — arriving through the facts file rather
# than through code. It is worse than the code version in one specific way:
# both skills stay internally consistent and each report looks right, so there
# is nothing on either page to be suspicious of.
#
# These exist for historical reasons (independently written modules reaching
# for the same published figure) and the honest fix is one key. Until then the
# divergence is at least detected rather than merely documented.


@dataclass(frozen=True)
class Alias:
    #: The single real-world quantity all the keys below record.
    concept: str
    #: Dotted paths that mean the same thing, and who reads each.
    keys: tuple[tuple[str, str], ...]
    #: Why there is more than one. Never a justification.
    why: str


ALIASES: tuple[Alias, ...] = (
    Alias(
        concept="Long-term federal capital gains rate",
        keys=(("assumptions.ltcg_rate",
               "`pfic-divest-or-comply`, `charitable-giving-strategy`, "
               "`1031-exchange-modeling`"),
              ("assumptions.capital_gains_rate", "`divorce-asset-split`")),
        why="Two clusters were written independently and each named the rate "
            "for itself. There is one rate.",
    ),
    Alias(
        concept="§168(k) bonus depreciation percentage",
        keys=(("assumptions.bonus_depreciation_pct",
               "`depreciation-election` — business equipment"),
              ("assumptions.bonus_depreciation_rate",
               "`cost-segregation-screen` — reclassified property basis")),
        why="One statutory percentage, phasing down on one schedule, applied "
            "to two kinds of asset. Splitting the key does not split the "
            "statute — it only hides that these two must move together.",
    ),
)


@dataclass
class AliasFinding:
    concept: str
    status: str  # diverged | partial | agreed | absent
    values: dict
    detail: str

    @property
    def serious(self) -> bool:
        return self.status in ("diverged", "partial")


def aliased(facts: dict) -> list[AliasFinding]:
    """Keys that record one quantity under two names, and whether they agree.

    `diverged` is the loud case. `partial` is quieter and more common: one key
    is set, the other is not, so one skill computes a figure and its twin
    refuses — which reads as the second skill lacking data rather than as the
    household having answered the question already.
    """
    out: list[AliasFinding] = []
    for a in ALIASES:
        vals = {k: _dig(facts, k) for k, _ in a.keys}
        present = {k: v for k, v in vals.items() if v is not None}
        readers = dict(a.keys)

        if not present:
            out.append(AliasFinding(a.concept, "absent", vals,
                                    "Neither key is set; every skill reading "
                                    "this refuses the figure."))
        elif len(present) < len(vals):
            missing = [k for k in vals if k not in present]
            out.append(AliasFinding(
                a.concept, "partial", vals,
                "Set as " + ", ".join(f"`{k}` = {v}" for k, v in present.items())
                + "; not set as " + ", ".join(f"`{k}`" for k in missing)
                + ". " + " ".join(f"{readers[k]} therefore refuses the figure."
                                  for k in missing)
                + " That refusal reads as missing data, but the value is "
                  "already recorded under the other name."))
        elif len({float(v) for v in present.values()}) > 1:
            out.append(AliasFinding(
                a.concept, "diverged", vals,
                "Recorded twice with different values: "
                + ", ".join(f"`{k}` = {v} ({readers[k]})"
                            for k, v in present.items())
                + ". These are the same quantity, so at least one is wrong, "
                  "and each skill will report a confident figure built on its "
                  "own copy."))
        else:
            out.append(AliasFinding(a.concept, "agreed", vals,
                                    "Both keys are set and agree."))
    return out


def shape_warnings(facts: dict) -> list[str]:
    """Facts whose *shape* silently narrows an answer.

    Distinct from a missing value, which refuses loudly. A shape that is
    accepted but less specific than the question produces an answer — just not
    the one asked for.
    """
    out: list[str] = []
    a = _dig(facts, "assumptions") or {}
    sd = a.get("standard_deduction")
    brackets = a.get("federal_brackets") or {}
    if sd is not None and not isinstance(sd, dict) and len(brackets) > 1:
        out.append(
            f"`assumptions.standard_deduction` is a single figure ({sd}) while "
            f"`assumptions.federal_brackets` is keyed by "
            f"{len(brackets)} filing statuses ({', '.join(sorted(brackets))}). "
            "The one figure is used for **every** status, so a status whose "
            "real deduction differs gets a plausible liability computed from "
            "the wrong deduction. Supply the mapping shape instead.")
    return out
