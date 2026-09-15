"""Foreign account and asset reporting: FBAR, FATCA, PFIC, and the rest.

## Why this is a compliance skill, not a planning one

Everything else in this repository helps a household decide something. This
one establishes whether an obligation **already exists** — and if it does, it
existed last year too.

That changes the tone. There is no recommendation to weigh; there is a
threshold, and you are either over it or you do not know. "You do not know" is
the most common state and is treated as a finding rather than as missing data.

## The three distinctions people get wrong

**FBAR is aggregate, and it is the maximum.** Not per account, and not the
year-end balance. Five accounts of $3,000 each cross the threshold. An account
that peaked at $12,000 in March and ended the year at $400 crosses it. People
check December statements and conclude they are fine.

**FBAR and FATCA are different filings with different thresholds.** One goes to
FinCEN separately from the tax return; the other is a form attached to it.
Filing one does not satisfy the other, and the same account is frequently
reportable on both.

**Signature authority counts.** Being able to direct an account is reportable
even with no beneficial interest — a parent's account in another country, a
business account, an elderly relative's account you help manage.

## Thresholds are statutory and not indexed

Unlike contribution limits, these have been stable for years — but they are
still reference data, and they are registered with `provenance.py` on the same
terms as everything else. Stable is not the same as verified.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── thresholds ──────────────────────────────────────────────────────────────

#: FinCEN 114. Aggregate maximum value across ALL foreign financial accounts
#: at ANY point in the calendar year. Not indexed.
FBAR_THRESHOLD = 10_000

#: Form 8938, for taxpayers living in the US. (year-end, any-time-during-year)
FATCA_US_RESIDENT = {
    "single": (50_000, 75_000),
    "married_joint": (100_000, 150_000),
}
#: Substantially higher for taxpayers whose tax home is abroad.
FATCA_ABROAD = {
    "single": (200_000, 300_000),
    "married_joint": (400_000, 600_000),
}

#: Form 8621 de minimis: filing waived below this aggregate PFIC value at
#: year end, provided no excess distribution was received and no election is
#: in effect. Both conditions matter.
PFIC_DE_MINIMIS = {"single": 25_000, "married_joint": 50_000}

#: Form 3520 — gifts or bequests from a nonresident alien individual or a
#: foreign estate above this aggregate in a year. A reporting obligation with
#: no tax attached, and penalties that are a percentage of the gift.
FOREIGN_GIFT_THRESHOLD = 100_000

REPORTING_SOURCE = (
    "31 CFR 1010.350 (FBAR); IRC §6038D and Form 8938 instructions (FATCA); "
    "Form 8621 instructions (PFIC de minimis); IRC §6039F (Form 3520)"
)
REPORTING_VERIFIED = "unverified — check against irs.gov and fincen.gov"

#: Asset kinds that are PFICs by default for a US person. A non-US pooled
#: fund is the paradigm case and the one people hold without realising.
PFIC_KINDS = ("foreign_mutual_fund", "foreign_etf", "unit_trust",
              "investment_linked_policy")


@dataclass
class Finding:
    form: str
    severity: str  # blocker | gap | note | ok
    detail: str


@dataclass
class ReportingAudit:
    filing_status: str
    abroad: bool
    account_count: int
    known_max: float
    unknown_accounts: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "blocker"]

    @property
    def determinable(self) -> bool:
        return self.unknown_accounts == 0


def audit(
    accounts: list[dict],
    *,
    filing_status: str = "married_joint",
    tax_home_abroad: bool = False,
    foreign_gifts_received: float | None = None,
) -> ReportingAudit:
    accounts = accounts or []
    known = [a for a in accounts if a.get("max_value_during_year") is not None]
    unknown = [a for a in accounts if a.get("max_value_during_year") is None]
    known_max = sum(float(a["max_value_during_year"]) for a in known)

    a = ReportingAudit(
        filing_status=filing_status,
        abroad=tax_home_abroad,
        account_count=len(accounts),
        known_max=known_max,
        unknown_accounts=len(unknown),
    )

    if not accounts:
        a.findings.append(Finding(
            "—", "gap",
            "**No foreign accounts recorded.** If that is because there are "
            "none, record `foreign_accounts: []` so the answer is checked "
            "rather than absent. Bank accounts held in a country of "
            "citizenship, accounts kept open after moving, and accounts over "
            "which you merely have signature authority all count."))
        return a

    # ── FBAR ────────────────────────────────────────────────────────────
    if unknown:
        a.findings.append(Finding(
            "FinCEN 114 (FBAR)", "blocker",
            f"**{len(unknown)} of {len(accounts)} accounts have no maximum "
            f"value recorded, so this cannot be determined.** FBAR turns on "
            f"the **aggregate maximum across all accounts at any point in the "
            f"calendar year** — not the year-end balance, and not per "
            f"account. Recorded maxima so far total "
            f"{_money(known_max)} against a {_money(FBAR_THRESHOLD)} "
            f"threshold. Pull the highest balance each account reached in "
            f"each year concerned."))
    elif known_max > FBAR_THRESHOLD:
        a.findings.append(Finding(
            "FinCEN 114 (FBAR)", "blocker",
            f"**Required.** Aggregate maximum {_money(known_max)} exceeds "
            f"{_money(FBAR_THRESHOLD)}. Filed to FinCEN separately from the "
            "tax return — filing a 1040 does not satisfy it. **If this was "
            "true in prior years it was required then too**, and the "
            "remediation path for unfiled years differs sharply depending on "
            "whether the failure was non-wilful. That is a conversation to "
            "have with a cross-border CPA before filing anything, not after."))
    else:
        a.findings.append(Finding(
            "FinCEN 114 (FBAR)", "ok",
            f"Aggregate maximum {_money(known_max)} is below the "
            f"{_money(FBAR_THRESHOLD)} threshold. Re-check annually — the "
            "test is the peak, so a single large transfer through an account "
            "can trigger it in a year when nothing else changed."))

    # ── FATCA ───────────────────────────────────────────────────────────
    table = FATCA_ABROAD if tax_home_abroad else FATCA_US_RESIDENT
    year_end, any_time = table.get(filing_status, table["married_joint"])
    where = "abroad" if tax_home_abroad else "in the US"
    if unknown:
        a.findings.append(Finding(
            "Form 8938 (FATCA)", "gap",
            f"Cannot be determined either. Thresholds for {filing_status} "
            f"living {where} are {_money(year_end)} at year end **or** "
            f"{_money(any_time)} at any time. Higher than FBAR, so FBAR "
            "usually binds first — but they are separate filings and both "
            "can apply to the same account."))
    elif known_max > any_time:
        a.findings.append(Finding(
            "Form 8938 (FATCA)", "blocker",
            f"**Likely required.** {_money(known_max)} exceeds the "
            f"{_money(any_time)} any-time threshold. Attached to the tax "
            "return, unlike FBAR. Note that Form 8938 covers foreign "
            "*assets*, which is broader than accounts — pensions, and "
            "interests in foreign entities, can count."))
    else:
        a.findings.append(Finding(
            "Form 8938 (FATCA)", "ok",
            f"Below the {_money(year_end)}/{_money(any_time)} thresholds for "
            f"{filing_status} living {where}."))

    # ── PFIC ────────────────────────────────────────────────────────────
    pfics = [x for x in accounts if x.get("kind") in PFIC_KINDS]
    if pfics:
        limit = PFIC_DE_MINIMIS.get(filing_status, PFIC_DE_MINIMIS["married_joint"])
        names = ", ".join(x.get("name", "?") for x in pfics)
        a.findings.append(Finding(
            "Form 8621 (PFIC)", "blocker",
            f"**{len(pfics)} holding(s) are PFICs by default: {names}.** A "
            f"non-US pooled fund is the paradigm case. Form 8621 is required "
            f"**per fund**, and the de minimis waiver — under "
            f"{_money(limit)} aggregate at year end — applies only if no "
            "excess distribution was received and no election is in effect. "
            "The default §1291 regime taxes gains at the highest marginal "
            "rate for each prior year plus a compound interest charge. See "
            "`pfic-divest-or-comply`; the usual answer is to sell."))

    # ── foreign gifts ───────────────────────────────────────────────────
    if foreign_gifts_received and foreign_gifts_received > FOREIGN_GIFT_THRESHOLD:
        a.findings.append(Finding(
            "Form 3520", "blocker",
            f"**Required.** Gifts or bequests of {_money(foreign_gifts_received)} "
            f"from a foreign person exceed {_money(FOREIGN_GIFT_THRESHOLD)}. "
            "**No tax is due on the gift** — this is purely a reporting "
            "obligation — but the penalty for not filing is a percentage of "
            "the amount received, which makes it one of the most expensive "
            "forms to overlook. Inheritances from family abroad are the "
            "common trigger."))
    elif foreign_gifts_received is None:
        a.findings.append(Finding(
            "Form 3520", "note",
            f"Foreign gifts and inheritances are not recorded. Above "
            f"{_money(FOREIGN_GIFT_THRESHOLD)} from a foreign person in a "
            "year, Form 3520 is required — no tax, reporting only, and a "
            "percentage-of-amount penalty for missing it."))

    a.findings.append(Finding(
        "—", "note",
        "**Signature authority counts even without ownership.** An account "
        "you can direct but do not own — a parent's, a relative's, a business "
        "account — is reportable on FBAR. This is the most commonly missed "
        "category, because it does not feel like *your* money."))
    return a


def _money(x) -> str:
    return f"${x:,.0f}"
