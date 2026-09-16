"""Social Security benefit amounts, and the survivor sequence in particular.

## Why this is a module and not three copies

`survivor-needs` must net survivor benefits out of the capital requirement.
`social-security-timing` should show dollars beside its percentage table.
`disability-insurance-review` needs SSDI, which many policies offset against.
Three consumers, one set of figures — so the figures live here and are imported.

## The sequence is the finding, not the amount

A survivor's benefit is not a flat annual figure, and averaging it across the
horizon erases the only feature that makes the analysis worth running:

| Phase | What is payable |
|---|---|
| Youngest child under 16 | Caregiver benefit **plus** a child benefit per qualifying child |
| Children qualify, none under 16 | Child benefits only — the caregiver benefit has already stopped |
| No qualifying child, survivor under 60 | **Nothing.** This is the gap |
| Survivor 60 to their FRA | Reduced widow(er)'s benefit |
| Survivor's FRA onward | Full widow(er)'s benefit |

The caregiver benefit stopping at the youngest child's sixteenth birthday —
not their eighteenth — is the part households get wrong, and it opens the gap
years earlier than expected.

## Amounts come from the statement, never from this module

Every figure is read from `social_security` in the facts file, which mirrors the
structure of an SSA statement. This module holds the **rules** — who is eligible
when, and how the family maximum binds — and no dollar amounts at all. A PIA
this module computed would be a guess wearing a statement's clothes.

## What it refuses

It does not compute a PIA, apply the WEP or GPO, model earnings tests, or decide
whether benefits are payable abroad. `social-security-timing` already refuses the
last of those and that refusal stands: the alien non-payment exceptions are
specific, and a household needs SSA's answer rather than a table's.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: A child's benefit ends at 18, or 19 while still in secondary school.
CHILD_BENEFIT_END_AGE = 18
CHILD_BENEFIT_END_AGE_IN_SCHOOL = 19

#: The caregiver ("mother's or father's") benefit is payable only while a child
#: in care is under 16 — not until the child's benefit ends. Households
#: routinely assume the two run together, which places the gap two years later
#: than it really starts.
CAREGIVER_CHILD_AGE_LIMIT = 16

#: Earliest age for a widow(er)'s benefit on a deceased worker's record.
WIDOW_EARLIEST_AGE = 60

#: Widow(er)'s benefit at 60 as a share of the full benefit, reduced for early
#: claiming and rising to 100% at the survivor's own full retirement age.
WIDOW_FACTOR_AT_EARLIEST = 0.715

#: Both the child's benefit and the caregiver benefit are 75% of the worker's
#: PIA, so a statement's child figure serves for both. Recorded as a ratio
#: rather than used to derive a dollar amount — the amounts stay on the
#: statement.
CHILD_AND_CAREGIVER_PIA_SHARE = 0.75

SSA_SOURCE = (
    "Social Security Act §202 (child's, mother's/father's and widow(er)'s "
    "insurance benefits); 20 CFR 404.350-404.390; SSA family maximum "
    "provisions at §203(a)"
)
SSA_VERIFIED = "unverified — check against ssa.gov"


@dataclass
class Benefits:
    """The amounts, as the statement gives them. Monthly."""
    spouse_at_fra: float | None = None
    minor_child: float | None = None
    family_maximum: float | None = None
    survivor_fra: int | None = None

    @property
    def computable(self) -> bool:
        return self.spouse_at_fra is not None and self.minor_child is not None


@dataclass
class Year:
    survivor_age: int
    annual: float
    label: str
    capped: bool = False


@dataclass
class Phase:
    start_age: int
    end_age: int
    annual: float
    label: str
    capped: bool = False

    @property
    def years(self) -> int:
        return self.end_age - self.start_age + 1


@dataclass
class SurvivorBenefit:
    computable: bool
    years: list[Year] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def phases(self) -> list[Phase]:
        """Consecutive years of equal benefit, collapsed for reporting."""
        out: list[Phase] = []
        for y in self.years:
            if out and out[-1].label == y.label and out[-1].annual == y.annual:
                out[-1].end_age = y.survivor_age
            else:
                out.append(Phase(y.survivor_age, y.survivor_age, y.annual,
                                 y.label, y.capped))
        return out

    def annual_at(self, survivor_age: int) -> float:
        for y in self.years:
            if y.survivor_age == survivor_age:
                return y.annual
        return 0.0

    @property
    def gap(self) -> Phase | None:
        """The stretch with nothing payable, if there is one."""
        return next((p for p in self.phases if p.annual == 0), None)


def read_benefits(ss: dict | None) -> Benefits:
    s = ss or {}
    surv = s.get("survivors_monthly") or {}
    return Benefits(
        spouse_at_fra=surv.get("spouse_at_fra"),
        minor_child=surv.get("minor_child"),
        family_maximum=surv.get("family_maximum"),
        survivor_fra=s.get("full_retirement_age"),
    )


def survivor_schedule(
    *,
    benefits: Benefits,
    survivor_age: int | None,
    dependent_ages: list[int],
    horizon_years: int,
    child_in_school: bool = False,
) -> SurvivorBenefit:
    """Year-by-year survivor benefit over the horizon.

    Real terms throughout, matching `survivor.py`: benefits carry a
    cost-of-living adjustment, so a constant figure in today's money is the
    right assumption rather than a conservative one.
    """
    out = SurvivorBenefit(computable=False)

    if not benefits.computable:
        out.notes.append(
            "**No Social Security survivor amounts are recorded**, so none is "
            "netted and the capital need below is the figure *before* any "
            "benefit. Add `social_security.survivors_monthly` from the SSA "
            "statement — `spouse_at_fra` and `minor_child` at minimum. For "
            "most households this is the largest single omission in the "
            "calculation.")
        return out
    if survivor_age is None:
        out.notes.append(
            "No surviving adult age is recorded, so the benefit sequence "
            "cannot be placed in time and nothing is netted. The sequence is "
            "the point — a flat average would hide the gap.")
        return out

    fra = benefits.survivor_fra
    if fra is None:
        fra = 67
        out.notes.append(
            "`social_security.full_retirement_age` is not recorded, so 67 is "
            "assumed for the step from the reduced to the full widow(er)'s "
            "benefit. It is on the statement; record it.")

    child_end = (CHILD_BENEFIT_END_AGE_IN_SCHOOL if child_in_school
                 else CHILD_BENEFIT_END_AGE)
    cap = benefits.family_maximum
    out.computable = True

    for i in range(horizon_years):
        age = survivor_age + i
        kids = [a + i for a in dependent_ages]
        qualifying = [a for a in kids if a < child_end]
        caregiving = any(a < CAREGIVER_CHILD_AGE_LIMIT for a in kids)

        monthly, parts = 0.0, []
        if qualifying:
            monthly += len(qualifying) * benefits.minor_child
            parts.append(f"{len(qualifying)} child benefit(s)")
        if caregiving:
            monthly += benefits.minor_child        # same 75% of PIA
            parts.append("caregiver benefit")
        if not qualifying and not caregiving:
            if age >= fra:
                monthly = benefits.spouse_at_fra
                parts.append("full widow(er)'s benefit")
            elif age >= WIDOW_EARLIEST_AGE:
                monthly = benefits.spouse_at_fra * WIDOW_FACTOR_AT_EARLIEST
                parts.append("reduced widow(er)'s benefit")

        capped = False
        if cap is not None and monthly > cap:
            monthly, capped = cap, True

        out.years.append(Year(
            survivor_age=age,
            annual=round(monthly * 12, 2),
            label=" + ".join(parts) or "nothing payable",
            capped=capped))

    if cap is None:
        out.notes.append(
            "**No `family_maximum` is recorded.** Combined family benefits are "
            "capped, so where several are payable at once the total below may "
            "overstate what actually arrives. The figure is on the statement.")
    elif any(y.capped for y in out.years):
        out.notes.append(
            "The family maximum binds in at least one year, so the total is "
            "less than the individual benefits added together. That is the "
            "point of recording it.")

    gap = out.gap
    if gap is not None:
        out.notes.append(
            f"**The gap: ages {gap.start_age} to {gap.end_age}, "
            f"{gap.years} year(s) with nothing payable.** The caregiver "
            f"benefit stops when the youngest child turns "
            f"{CAREGIVER_CHILD_AGE_LIMIT} — not {child_end} — and a "
            f"widow(er)'s benefit cannot start before {WIDOW_EARLIEST_AGE}. "
            "Those years are funded entirely from capital, and netting a flat "
            "average across the horizon would hide them completely.")
    return out


# ── insured status ──────────────────────────────────────────────────────────

#: Credits required for a worker to be fully insured on their own record.
FULLY_INSURED_CREDITS = 40


def insured_status(member: dict) -> bool | None:
    """Whether this person is insured on their own record. None = unrecorded."""
    if member.get("ss_insured") is not None:
        return bool(member["ss_insured"])
    credits = member.get("ss_credits")
    if credits is None:
        return None
    return int(credits) >= FULLY_INSURED_CREDITS


def uninsured_spouse_notes(*, insured: bool | None,
                           payable_abroad: bool | None) -> list[str]:
    """What a short work history does and does not change.

    The common intuition — that few credits reduce a spouse's entitlement — is
    wrong, and saying so plainly is worth more than the caveats that follow it.
    """
    if insured is None:
        return ["Whether the spouse is fully insured on their own record is "
                f"not recorded. Add `ss_credits` or `ss_insured` to the "
                f"member; {FULLY_INSURED_CREDITS} credits is the threshold."]
    if insured:
        return []
    out = [
        "**A short work history does not reduce spousal or survivor "
        "benefits.** Neither requires the spouse's own credits, so "
        "entitlement is unaffected — the usual intuition here is simply "
        "wrong, and acting on it wastes years.",
        "**But there is no floor.** Every dollar of this spouse's Social "
        "Security flows through the worker's record rather than their own, so "
        "anything that interrupts payment on that record interrupts all of "
        "it rather than part of it.",
        "**And their benefit is coupled to the worker's filing date.** A "
        "spousal benefit cannot begin until the worker files, so a decision "
        "to delay to 70 silently defers the spouse's income too — that cost "
        "belongs in the delay calculation and is routinely left out.",
    ]
    if payable_abroad is False:
        out.append(
            "**Payment abroad is recorded as restricted**, and with no "
            "benefit of their own the spouse carries that risk on their "
            "entire entitlement.")
    elif payable_abroad is None:
        out.append(
            "Whether benefits are payable abroad is not recorded. For a "
            "spouse with no record of their own this is the difference "
            "between some exposure and total exposure — worth an answer from "
            "SSA rather than an assumption.")
    return out


def credit_building_is_futile(*, own_projected_monthly: float | None,
                              worker_pia_monthly: float | None) -> bool | None:
    """Whether more credits would raise household benefits at all.

    A spousal benefit tops the lower earner up to 50% of the worker's PIA, so
    an own-record benefit below that adds nothing to the household. For a
    late, short career against a 35-year average this is usually the case —
    and it is worth knowing before spending years on the wrong basis.
    """
    if own_projected_monthly is None or worker_pia_monthly is None:
        return None
    return own_projected_monthly < 0.5 * worker_pia_monthly


def worker_pia_from_statement(ss: dict | None) -> float | None:
    """The worker's PIA, read — never derived — from the statement.

    By definition the full-retirement-age benefit *is* the PIA, so the
    statement's `retirement_monthly` at `full_retirement_age` serves directly.
    Keys arrive as ints from YAML and strings from JSON; both are tried.
    """
    s = ss or {}
    table = s.get("retirement_monthly") or {}
    fra = s.get("full_retirement_age")
    for key in (fra, str(fra)):
        if key in table and table[key] is not None:
            return float(table[key])
    return None


def credit_building_notes(*, own_projected_monthly: float | None,
                          worker_pia_monthly: float | None) -> list[str]:
    """What to tell a spouse deciding whether more credits are worth earning.

    The verdict needs both figures; with only the worker's PIA the 50%
    threshold can still be named in dollars, which is usually enough to stop
    someone deciding on the wrong basis.
    """
    verdict = credit_building_is_futile(
        own_projected_monthly=own_projected_monthly,
        worker_pia_monthly=worker_pia_monthly)
    if verdict is True:
        return [
            "**Earning more credits will not raise household benefits.** The "
            f"spouse's own projected benefit "
            f"(${own_projected_monthly:,.0f}/mo) stays below half the "
            f"worker's PIA (${worker_pia_monthly:,.0f}/mo), so the spousal "
            "top-up already covers it. Decide about further work on any basis "
            "other than this one."]
    if verdict is False:
        return [
            "The spouse's own projected benefit clears half the worker's PIA, "
            "so further credits **can** raise the household total — the "
            "spousal top-up does not swallow it whole. Worth pricing before "
            "deciding."]
    if worker_pia_monthly is not None:
        return [
            "Building the spouse's own record raises the household total only "
            "once their own benefit would exceed **half the worker's PIA** "
            f"(about ${0.5 * worker_pia_monthly:,.0f}/mo on this statement). "
            "A late, short career averaged over 35 years rarely clears that "
            "bar — confirm against the spouse's own statement rather than "
            "assuming either way. Add "
            "`social_security.spouse_own_projected_monthly` to test it."]
    return [
        "Whether building the spouse's own record would raise household "
        "benefits cannot be tested without figures: the worker's PIA (the "
        "`retirement_monthly` figure at full retirement age) and the spouse's "
        "own projected benefit. Record both from the statements rather than "
        "assuming more credits means more income."]


def disability_overlay_notes(*, ssdi_monthly: float | None,
                             has_group_cover: bool) -> list[str]:
    """SSDI as an overlay on private disability cover.

    SSDI is read from the statement, never estimated — and its absence from
    the file is not its absence from the household. Many group LTD policies
    offset dollar-for-dollar against it, so a stacked total that ignores the
    offset overstates what a disabled worker actually receives.
    """
    if ssdi_monthly is None:
        return [
            "Social Security Disability Insurance is an **unmodelled "
            "overlay**: it may pay on top of — or be subtracted from — these "
            "benefits, and nothing above accounts for it. Add "
            "`social_security.disability_monthly` from the SSA statement. "
            "Until then the gap above treats SSDI as zero, which is a missing "
            "input rather than a finding."]
    out = [
        f"SSDI of about ${ssdi_monthly:,.0f}/mo is recorded from the "
        "statement. It is an overlay on these policies, not part of them — "
        "the cover above stands on its own."]
    if has_group_cover:
        out.append(
            "**Many group LTD policies offset dollar-for-dollar against "
            "SSDI**, so the group benefit and SSDI do not stack. Read the "
            "offset clause in the plan documents: where it exists, the "
            "private benefit overstates what actually arrives by up to the "
            "SSDI amount.")
    return out
