"""Which assets go through court, what that costs, and the cheapest way out.

## The one idea

`beneficiary-audit` asks whether a designation is *coherent*. This asks a
different question with a different answer: **which assets will pass through
probate, what will that cost, and what is the cheapest instrument that avoids
it for each one.** Titling decides that, and nothing else in this repository
reads titling.

## A pour-over will does not avoid probate

The single most common misconception here, and it is held by exactly the
households who believe they are covered. A pour-over will directs whatever is
left into the trust on death — it fixes the **destination**, not the **route**.
Anything still titled in an individual name at death goes through court first
and lands in the trust afterwards, having paid for the trip.

The trust avoids probate only for assets actually retitled into it. Drafting is
the part people pay for; retitling is the part they skip.

## Avoiding probate is not the same as a good outcome

The second test, and it constrains what this module is allowed to recommend
rather than what it diagnoses. A transfer-on-death registration naming a minor
avoids probate *and* triggers a court-appointed guardianship of the estate,
which hands the whole balance over outright at the age of majority. That is
frequently worse than the probate it avoided.

So this module will not recommend an instrument that produces that outcome.
Diagnosing an existing designation that already names a minor belongs to
`beneficiary-audit`, which does it, and this module does not restate it.

## The correct designation depends on the tax wrapper

The subtle part, and the reason `recommend()` refuses to answer for "accounts"
generically:

| Wrapper | Primary should be | Why |
|---|---|---|
| Taxable | The trust | Keeps the dispositive scheme in one instrument; contingent protections apply automatically |
| Retirement | **The spouse, directly** | A trust as primary generally forfeits the spousal rollover and forces a roughly ten-year payout |

A module that optimised only for probate avoidance would recommend
trust-as-primary everywhere and quietly cost a surviving spouse decades of
deferral. Both rules are encoded, keyed off the account's tier.

## Unknown is neither exposed nor covered

`titled_to: null` means nobody looked. It is the most common real state and the
one most likely to be hiding a problem. Reporting it as exposed produces a
false alarm and a recommendation to buy paperwork; reporting it as covered
produces a silent failure. It reports as **cannot be determined**, and the
estimated cost becomes a range whose width is the cost of not having looked.

## Cost is jurisdiction-specific and never inferred

A state is in `STATES` only if its rule was checked, with a source and a
`verified_on`. Everything else is `UNKNOWN`, and the report says the cost
cannot be estimated rather than reaching for a state it happens to know.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .estate import AGE_OF_MAJORITY, _minor_ids

# ── how a state prices probate ──────────────────────────────────────────────

#: Fees set by statute as a percentage of the estate. The percentage is applied
#: to the **gross** value — before mortgages and other debts — so a heavily
#: mortgaged house is priced on the whole house.
STATUTORY_PERCENTAGE = "statutory_percentage"
#: Fees are whatever is reasonable, usually billed hourly and approved by the
#: court. Cheaper in the ordinary case and much harder to predict.
REASONABLE_HOURLY = "reasonable_hourly"


@dataclass(frozen=True)
class ProbateRules:
    state: str
    known: bool
    basis: str | None = None
    #: Cumulative upper bounds and the marginal rate below each, applied to
    #: gross value. A final `(None, None)` band means the statute stops giving
    #: a formula and the court sets the figure.
    fee_schedule: tuple[tuple[int | None, float | None], ...] | None = None
    #: True where the attorney and the personal representative may EACH claim
    #: the full statutory fee, so the real cost is double a single reading of
    #: the schedule. This is the detail that makes a percentage state
    #: expensive, and it is not obvious from the statute's face.
    fee_claimable_twice: bool | None = None
    #: Below this gross probate value an affidavit procedure replaces probate.
    #: Often indexed, so it moves.
    small_estate_threshold: int | None = None
    #: An abbreviated procedure for property passing to a surviving spouse.
    #: `None` means not checked for this state, which is not the same as False.
    spousal_simplified: bool | None = None
    source: str = ""
    verified_on: str = ""


UNKNOWN = ProbateRules(state="??", known=False)

#: Two states, deliberately. Adding one means adding the citation, not the
#: guess. See `CONTRIBUTING.md` — an unsourced entry is worse than an absent
#: one, because absence is visible.
STATES: dict[str, ProbateRules] = {
    "CA": ProbateRules(
        state="CA",
        known=True,
        basis=STATUTORY_PERCENTAGE,
        # Ordinary compensation, on the gross value of the estate accounted for.
        fee_schedule=((100_000, 0.04), (200_000, 0.03), (1_000_000, 0.02),
                      (10_000_000, 0.01), (25_000_000, 0.005), (None, None)),
        # §10800 gives the personal representative the same schedule §10810
        # gives the attorney. Both may be claimed on the same estate.
        fee_claimable_twice=True,
        small_estate_threshold=184_500,
        spousal_simplified=True,      # spousal property petition
        source="Cal. Prob. Code §§10800, 10810 (ordinary compensation); "
               "§§13100-13101 (small estate affidavit, indexed); "
               "§13650 (spousal property petition)",
        verified_on="unverified — check against leginfo.legislature.ca.gov",
    ),
    "TX": ProbateRules(
        state="TX",
        known=True,
        basis=REASONABLE_HOURLY,
        fee_schedule=None,
        fee_claimable_twice=False,
        small_estate_threshold=75_000,
        # Not checked. `None` is the honest value and is not False: Texas has
        # procedures in this area and nobody has confirmed which apply.
        spousal_simplified=None,
        source="Tex. Est. Code §205.001 (small estate affidavit, excluding "
               "homestead and exempt property); independent administration "
               "under Ch. 401 — compensation is reasonable, not scheduled",
        verified_on="unverified — check against statutes.capitol.texas.gov",
    ),
}


def rules_for(state: str | None) -> ProbateRules:
    if not state:
        return UNKNOWN
    return STATES.get(state.strip().upper(), UNKNOWN)


def states_available() -> list[str]:
    return sorted(STATES)


def statutory_fee(gross: float, rules: ProbateRules) -> float | None:
    """One statutory fee on a gross value, or None where no formula applies.

    Returns the fee for a single claimant. `fee_claimable_twice` doubles it,
    and that doubling is applied by the caller so the report can show both
    halves rather than one unexplained number.
    """
    if not rules.known or rules.basis != STATUTORY_PERCENTAGE or not rules.fee_schedule:
        return None
    total, prev = 0.0, 0.0
    for bound, rate in rules.fee_schedule:
        if rate is None:              # the statute stops giving a formula
            if gross > prev:
                return None
            break
        top = float(bound) if bound is not None else gross
        if gross <= prev:
            break
        total += (min(gross, top) - prev) * rate
        prev = top
    return round(total, 2)


# ── routing a single account ────────────────────────────────────────────────

AVOIDS = "avoids"
PROBATE = "probate"
UNDETERMINED = "undetermined"

#: Titling values the schema understands.
TITLE_TRUST, TITLE_JOINT, TITLE_INDIVIDUAL = "trust", "joint", "individual"


@dataclass
class Route:
    label: str
    value: float
    verdict: str            # avoids | probate | undetermined
    titling: str | None
    designation: str | None
    why: str
    #: True when the account is a retirement wrapper, which changes the fix.
    retirement: bool = False
    #: Which of the four designation states this account is in. Carried so the
    #: report can distinguish "nobody looked" from "this asset cannot have
    #: one" — collapsing those is the error the whole module is written
    #: against.
    designation_state: str = ""

    @property
    def exposed(self) -> bool:
        return self.verdict == PROBATE


#: The three states a designation can be in, plus "this asset cannot have
#: one". They are `beneficiary-audit`'s vocabulary, reused rather than
#: reinvented — two spellings of one distinction would drift.
NAMED, NONE_NAMED, UNRECORDED, NOT_APPLICABLE = "named", "none", "unknown", "n/a"


def designation(row: dict) -> tuple[str, str | None]:
    """The effective primary designation, from either shape the schema allows.

    `beneficiary_primary` is the shorthand this module adds. `beneficiaries`
    is the full list `beneficiary-audit` already reads. **Deriving from the
    list rather than requiring a duplicate field** is deliberate: a household
    that recorded the list and then also recorded a shorthand would eventually
    disagree with itself, and nothing would notice.
    """
    if row.get("beneficiary_applicable") is False:
        return NOT_APPLICABLE, None

    shorthand = row.get("beneficiary_primary")
    if shorthand is not None:
        return (PROBATE if shorthand == "estate" else NAMED), shorthand

    bens = row.get("beneficiaries")
    if bens is None:
        return UNRECORDED, None
    primaries = [b for b in bens if b.get("type") == "primary"]
    if not primaries:
        # Either the list is empty (checked, none named) or it holds only
        # contingents, which do not take without a primary.
        return NONE_NAMED, None
    if any((b.get("relationship") == "estate"
            or str(b.get("name", "")).strip().lower() == "estate")
           for b in primaries):
        return PROBATE, "estate"
    first = primaries[0]
    return NAMED, (first.get("member_id") or first.get("relationship")
                   or first.get("name"))


def route(row: dict) -> Route:
    """Does this account pass through probate?

    Order matters. Titling is checked first because it is dispositive: an
    account owned by the trust is outside the estate whatever any form says.
    A designation is checked second because it carries the asset outside
    probate regardless of how the account is titled.
    """
    label = row.get("label") or row.get("name") or "?"
    value = float(row.get("value") or 0)
    titling = row.get("titled_to")
    state, primary = designation(row)
    retirement = row.get("tier") == "age_restricted"
    def r(v, why):
        return Route(label, value, v, titling, primary, why, retirement, state)

    if titling == TITLE_TRUST:
        return r(AVOIDS, "Titled to the trust, so it is outside the probate "
                         "estate. This is the retitling that a pour-over will "
                         "does **not** do for you.")
    if titling == TITLE_JOINT:
        return r(AVOIDS, "Held jointly with right of survivorship, so it "
                         "passes to the survivor by operation of law. Confirm "
                         "the deed or registration actually says survivorship "
                         "— tenants in common does not, and looks identical on "
                         "a statement.")

    if state == PROBATE:
        return r(PROBATE, "The estate is named as beneficiary, which routes "
                          "the asset into probate deliberately. "
                          "`beneficiary-audit` covers why that is almost "
                          "always a mistake; this prices it.")
    if state == NAMED:
        return r(AVOIDS, "A beneficiary is named, so it passes by designation "
                         "outside the will.")

    if state == NOT_APPLICABLE:
        # A car, a boat, tangible property. No designation is possible, so
        # titling is the whole answer.
        if titling == TITLE_INDIVIDUAL:
            return r(PROBATE, "Individually titled and takes no beneficiary "
                              "designation, so it passes under the will.")
        return r(UNDETERMINED, "Takes no beneficiary designation, and the "
                               "titling is not recorded. Cannot be determined.")

    if state == NONE_NAMED:
        if titling == TITLE_INDIVIDUAL:
            return r(PROBATE, "Individually titled, and the designation was "
                              "checked with nobody named. Nothing carries it "
                              "out of the estate, so it passes under the "
                              "will.")
        return r(UNDETERMINED, "The designation was checked and nobody is "
                               "named, but the titling is not recorded — "
                               "joint or trust titling would still carry it "
                               "out. Cannot be determined until the title is "
                               "read.")

    # state == UNRECORDED
    if titling is None:
        return r(UNDETERMINED, "Neither the titling nor the designation has "
                               "been recorded. **Cannot be determined** — not "
                               "exposed and not covered. This is the most "
                               "common state and the one most likely to be "
                               "hiding a problem.")
    return r(UNDETERMINED, "Individually titled, but the beneficiary "
                           "designation has not been checked. A designation "
                           "would carry it out of probate; nobody has looked.")


# ── the estate as a whole ───────────────────────────────────────────────────


@dataclass
class Exposure:
    state: str | None
    rules: ProbateRules
    routes: list[Route] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    @property
    def exposed(self) -> list[Route]:
        return [r for r in self.routes if r.verdict == PROBATE]

    @property
    def undetermined(self) -> list[Route]:
        return [r for r in self.routes if r.verdict == UNDETERMINED]

    @property
    def exposed_total(self) -> float:
        return sum(r.value for r in self.exposed)

    @property
    def undetermined_total(self) -> float:
        return sum(r.value for r in self.undetermined)

    @property
    def upper_total(self) -> float:
        """Worst case: everything unchecked turns out to be exposed."""
        return self.exposed_total + self.undetermined_total

    @property
    def determinable(self) -> bool:
        return not self.undetermined


def assess(balance_sheet: list[dict], *, state: str | None) -> Exposure:
    rules = rules_for(state)
    e = Exposure(state=state, rules=rules,
                 routes=[route(r) for r in (balance_sheet or [])])

    if not rules.known:
        e.findings.append(
            f"**Probate cost cannot be estimated for "
            f"{state or 'an unrecorded state'}.** Only "
            f"{', '.join(states_available())} are in the cited table, and the "
            "rules differ enough between states — percentage of gross value "
            "in some, reasonable hourly fees in others — that applying a "
            "known state's schedule here would produce a confident wrong "
            "number. The routing below still holds; only the pricing does not.")
    return e


@dataclass
class Cost:
    computable: bool
    gross: float
    single_fee: float | None = None
    doubled: bool = False
    total: float | None = None
    small_estate: bool = False
    detail: str = ""


def cost(gross: float, rules: ProbateRules) -> Cost:
    """What probate on this gross value costs, with the schedule shown."""
    if not rules.known:
        return Cost(False, gross, detail="State not in the cited table.")

    if (rules.small_estate_threshold is not None
            and gross <= rules.small_estate_threshold):
        return Cost(
            True, gross, total=0.0, small_estate=True,
            detail=(
                f"{_money(gross)} is at or below the "
                f"{_money(rules.small_estate_threshold)} small-estate "
                f"threshold, so an affidavit procedure replaces probate. "
                "**The exposure here is close to zero even with no "
                "designations at all** — do not buy paperwork that changes "
                "nothing. The threshold is often indexed, so re-check it "
                "rather than assuming this stays true."))

    if rules.basis == REASONABLE_HOURLY:
        return Cost(
            False, gross,
            detail=("Fees here are whatever is reasonable, usually billed "
                    "hourly and approved by the court, so no schedule can be "
                    "applied. That is generally cheaper than a percentage "
                    "state in the ordinary case and much harder to predict. "
                    "The number to ask an attorney for is a range, not a "
                    "rate."))

    fee = statutory_fee(gross, rules)
    if fee is None:
        return Cost(False, gross,
                    detail="The statutory schedule does not reach this value; "
                           "the court sets the figure.")
    doubled = bool(rules.fee_claimable_twice)
    total = fee * 2 if doubled else fee
    detail = (f"Statutory schedule on the **gross** value {_money(gross)} — "
              f"before mortgages and other debts — gives {_money(fee)}.")
    if doubled:
        detail += (" The attorney and the personal representative may **each** "
                   f"claim that, so the ordinary total is {_money(total)}. "
                   "Reading the schedule once understates this by half.")
    detail += (" Extraordinary fees, filing costs, appraisal and bond are on "
               "top, and none of them are in this figure.")
    return Cost(True, gross, single_fee=fee, doubled=doubled, total=total,
                detail=detail)


# ── what to actually do ─────────────────────────────────────────────────────


@dataclass
class Fix:
    label: str
    instrument: str
    rationale: str
    #: Set where the obvious instrument is withheld on suitability grounds.
    withheld: str = ""


def recommend(routes: list[Route], *, members: list[dict],
              trust_exists: bool) -> list[Fix]:
    """The cheapest instrument per account, refusing a single blanket answer.

    Two rules do the work, and they point in opposite directions:

    * a taxable account belongs in the trust, because that keeps one
      dispositive scheme and the contingent protections come with it;
    * a **retirement** account names the spouse directly, because a trust as
      primary generally forfeits the spousal rollover and forces a roughly
      ten-year payout.

    Optimising only for probate would recommend the trust for both and cost a
    surviving spouse decades of deferral. There is therefore no answer for
    "the accounts" as a group.
    """
    minors = _minor_ids(members)
    spouse = next((m["id"] for m in members if m.get("role") == "spouse"), None)
    fixes: list[Fix] = []

    for r in routes:
        if r.verdict == AVOIDS:
            continue
        if r.verdict == UNDETERMINED:
            fixes.append(Fix(
                r.label, "Find out first",
                "No instrument is recommended for an account whose current "
                "state is unknown. Pull the registration and the title, then "
                "re-run. Buying a fix for a problem that may not exist is how "
                "households end up with two conflicting instruments."))
            continue

        if r.retirement:
            if spouse:
                fixes.append(Fix(
                    r.label, f"Name the spouse (`{spouse}`) as primary, directly",
                    "Retirement accounts are the exception. Naming the trust "
                    "as primary generally forfeits the spousal rollover and "
                    "forces a roughly ten-year payout, which costs far more "
                    "than the probate it avoids. Spouse as primary, and a "
                    "trust for minor children as contingent if that is the "
                    "intent."))
            else:
                fixes.append(Fix(
                    r.label, "Name a beneficiary — but not the trust by default",
                    "A designation of any kind takes this out of probate. "
                    "Whether a trust should be primary is a question for "
                    "counsel: it protects the disposition and usually "
                    "shortens the payout period. With no spouse recorded "
                    "there is no rollover to preserve, which changes the "
                    "balance."))
            continue

        # Taxable.
        if trust_exists:
            fixes.append(Fix(
                r.label, "Retitle into the trust",
                "Cheapest instrument for a taxable account where a trust "
                "already exists: no new document, one retitling, and the "
                "contingent protections already drafted apply automatically. "
                "This is the step a pour-over will does not perform."))
        else:
            minor_only = bool(minors) and not spouse
            if minor_only:
                fixes.append(Fix(
                    r.label, "Not a transfer-on-death registration",
                    "A TOD avoids probate here, and it is withheld anyway.",
                    withheld=(
                        "The only beneficiaries recorded are minors. A TOD "
                        "naming a minor avoids probate **and** triggers a "
                        "court-appointed guardianship of the estate, with the "
                        "whole balance handed over outright at the age of "
                        f"majority ({AGE_OF_MAJORITY}). That is frequently "
                        "worse than the probate it avoided. A trust for their "
                        "benefit is the instrument that does both jobs.")))
            else:
                fixes.append(Fix(
                    r.label, "Transfer-on-death registration",
                    "No trust is recorded, so a TOD is the cheapest "
                    "instrument that takes this account out of probate — a "
                    "form with the custodian rather than a document with an "
                    "attorney. It carries no contingent logic, so it is a "
                    "floor, not a plan."))
    return fixes


def spousal_note(rules: ProbateRules, *, will_pours_to_trust: bool | None) -> str:
    """The simplified-spousal-transfer interaction, flagged rather than decided."""
    if not rules.known or rules.spousal_simplified is None:
        return ("Whether this state offers an abbreviated procedure for "
                "property passing to a surviving spouse has **not been "
                "checked**. That is not the same as it having none — ask.")
    if not rules.spousal_simplified:
        return "No simplified spousal procedure is recorded for this state."
    note = ("This state offers an abbreviated procedure for property passing "
            "to a surviving spouse, which can make full probate unnecessary "
            "for the spousal share.")
    if will_pours_to_trust:
        note += (" **The will pours into a trust rather than to the spouse "
                 "directly, which may take that shortcut off the table** — "
                 "property passing to a trust is not property passing to a "
                 "spouse. Whether it still qualifies is a question for "
                 "counsel, and this module does not decide it.")
    return note


def _money(x) -> str:
    return f"${x:,.0f}"
