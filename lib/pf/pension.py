"""Foreign pension schemes: which bucket, and what has to be filed.

## Classify, do not conclude

This module establishes **which bucket a scheme falls into** and what filing
obligation follows. It does not produce a filing position, a characterisation
to assert on a return, or a treaty claim. That line is drawn deliberately: the
classification is a decision a household can act on — get a cross-border
preparer, or do not — and the position itself is tax preparation.

One of the buckets is `CONTESTED`, and it is a real answer rather than a gap.
Where practitioners disagree and the household's facts do not separate the
readings, reporting the more favourable default would convert a refusal into a
conclusion — which is the one failure this module is built to avoid.

## Why the bucket is worth establishing at all

Classification drives Forms **3520** and **3520-A**, whose non-filing penalties
**start at $10,000** and scale with the amounts involved. A household that has
never heard of either form and holds an Australian Superannuation account is
exposed to a five-figure penalty for a filing nobody told them about. That is a
different failure mode from a suboptimal allocation, and it is why the bucket
matters more than the nuance inside it.

## The three things the classification turns on

1. **Treaty status.** A US income tax treaty with a pension article that covers
   the scheme can defer tax on inside build-up and, separately, keep the scheme
   out of the foreign-trust regime. Both matter and they are not the same
   question.
2. **Whether employee contributions exceed employer contributions.** A scheme
   funded mostly by the employee looks less like a §402(b) employees' trust and
   more like a foreign trust the employee funded — and under §§671–679 a US
   person who funds a foreign trust is treated as its owner.
3. **Who controls the investment choices.** Holder-directed investment is the
   fact that most often tips a scheme into grantor-trust territory.

## The table is cited, and silence is the honest answer

A scheme is in the table only if the treaty and revenue-procedure position has
been checked, with a `source` and a `verified_on`. Everything else returns
`UNKNOWN`, and the skill says so — **never reasoning by analogy from a
jurisdiction it does know.** UK and Australia both have workplace pensions and
opposite answers; an analogy between them would be confidently wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── buckets ─────────────────────────────────────────────────────────────────

#: A US treaty pension article covers the scheme, or a revenue procedure
#: exempts it from the foreign-trust forms. The comfortable bucket, and still
#: not a no-filing bucket — FBAR and Form 8938 are unaffected by any of this.
TREATY_PROTECTED = "treaty-protected"

#: No treaty relief, but the scheme has the shape of an employees' trust under
#: §402(b): employer-established, employer-funded, not holder-directed.
EMPLOYEES_TRUST_402B = "§402(b) employees' trust"

#: No treaty relief and the shape of a trust the holder funded and directs.
#: §§671–679 treat a US person who funds a foreign trust as its owner, which
#: is what brings 3520/3520-A into play.
FOREIGN_GRANTOR_TRUST = "foreign grantor trust (§§671–679)"

#: Practitioners disagree, and the table records the disagreement rather than
#: picking the more comfortable side of it. **Contested is the finding, not a
#: placeholder for one** — the same position `crossborder.py` takes on India's
#: treatment of the Roth wrapper. A scheme sits here when the §402(b) and
#: grantor-trust readings are both live and the household's own facts have not
#: yet separated them; recording the favourable default instead would be a
#: refusal turned silently into an answer.
CONTESTED = "contested — §402(b) or foreign grantor trust, unresolved"

#: Not in the table. Not "probably fine".
UNKNOWN_BUCKET = "unknown"

#: Form 3520 non-filing: the greater of $10,000 or a percentage of the
#: amounts involved. Form 3520-A: $10,000 for the trust's own return, which a
#: US owner is responsible for procuring. Stated as the floor, because the
#: floor is what makes the exposure non-trivial at small balances.
PENALTY_FLOOR = 10_000

PENSION_SOURCE = (
    "IRC §402(b) (employees' trusts); §§671–679 (grantor trust rules); "
    "IRC §6048 and Forms 3520/3520-A instructions; Rev. Proc. 2020-17 "
    "(exemption for applicable tax-favoured foreign retirement trusts); "
    "Rev. Proc. 2014-55 (Canadian plans); the relevant bilateral income tax "
    "treaty and its pension article"
)
PENSION_VERIFIED = "unverified — check against irs.gov and the treaty text"


@dataclass(frozen=True)
class Scheme:
    key: str
    country: str
    name: str
    known: bool
    #: The default bucket before the household's own facts are applied.
    bucket: str = UNKNOWN_BUCKET
    #: Is there a US treaty pension article that reaches this scheme?
    treaty: bool | None = None
    treaty_article: str | None = None
    #: Does a revenue procedure exempt it from Forms 3520/3520-A?
    rev_proc_relief: bool | None = None
    #: True where the holder directs the investments as a matter of the
    #: scheme's design rather than the individual's choice.
    holder_directed_by_design: bool | None = None
    notes: tuple[str, ...] = ()
    #: Provenance. Surfaced by `provenance.py` so a stale entry is visible
    #: rather than merely wrong.
    source: str = ""
    verified_on: str = ""


UNKNOWN = Scheme(key="unknown", country="??", name="unrecorded scheme",
                 known=False)

# ── United Kingdom ──────────────────────────────────────────────────────────
# US–UK treaty Art. 17/18 covers pension schemes and permits deferral of tax
# on inside build-up for a scheme established in the other state. Rev. Proc.
# 2020-17 exempts applicable tax-favoured foreign retirement trusts from
# Forms 3520/3520-A subject to its contribution and information conditions.
UK_WORKPLACE = Scheme(
    key="uk_workplace_pension",
    country="GB",
    name="UK workplace pension (occupational / auto-enrolment)",
    known=True,
    bucket=TREATY_PROTECTED,
    treaty=True,
    treaty_article="US–UK Art. 17 (pensions) and Art. 18 (pension schemes)",
    rev_proc_relief=True,
    holder_directed_by_design=False,
    notes=(
        "Treaty relief is claimed, not automatic. The deferral of inside "
        "build-up depends on the scheme qualifying under the treaty's pension "
        "definition and on the claim being made.",
        "FBAR and Form 8938 are unaffected. A treaty-protected pension is "
        "still a foreign financial asset and frequently still reportable.",
        "The 25% UK tax-free lump sum is not tax-free in the US. The treaty "
        "does not make it so, and this is the single most common surprise.",
    ),
    source="US–UK income tax treaty Arts. 17–18; Rev. Proc. 2020-17",
    verified_on="unverified — check against irs.gov and the treaty text",
)

UK_SIPP = Scheme(
    key="uk_sipp",
    country="GB",
    name="UK self-invested personal pension (SIPP)",
    known=True,
    bucket=TREATY_PROTECTED,
    treaty=True,
    treaty_article="US–UK Art. 17 (pensions) and Art. 18 (pension schemes)",
    rev_proc_relief=True,
    holder_directed_by_design=True,
    notes=(
        "Self-directed by design, which is the fact that elsewhere tips a "
        "scheme toward grantor-trust treatment. Here the treaty and Rev. "
        "Proc. 2020-17 carry the weight instead — which is exactly why the "
        "bucket is read off a cited table rather than inferred from the "
        "scheme's shape.",
        "A SIPP commonly holds non-US funds. Those holdings are PFICs in "
        "their own right; whether the pension wrapper shelters them from the "
        "PFIC regime is a treaty question and not a settled one. See "
        "`pfic-divest-or-comply`.",
    ),
    source="US–UK income tax treaty Arts. 17–18; Rev. Proc. 2020-17",
    verified_on="unverified — check against irs.gov and the treaty text",
)

# ── Canada ──────────────────────────────────────────────────────────────────
# Art. XVIII(7) permits an election to defer US tax on undistributed income.
# Rev. Proc. 2014-55 makes it automatic and eliminated the former Form 8891.
CA_RRSP = Scheme(
    key="ca_rrsp",
    country="CA",
    name="Canadian RRSP / RRIF",
    known=True,
    bucket=TREATY_PROTECTED,
    treaty=True,
    treaty_article="US–Canada Art. XVIII(7)",
    rev_proc_relief=True,
    holder_directed_by_design=True,
    notes=(
        "Deferral is automatic under Rev. Proc. 2014-55 — no election is "
        "filed and Form 8891 no longer exists. FBAR and Form 8938 still apply.",
        "A TFSA and an RESP are **not** covered by the same relief and are "
        "commonly treated as foreign trusts. Do not extend this entry to them.",
    ),
    source="US–Canada income tax treaty Art. XVIII(7); Rev. Proc. 2014-55",
    verified_on="unverified — check against irs.gov and the treaty text",
)

# ── Australia ───────────────────────────────────────────────────────────────
# The US–Australia treaty has no pension article that clearly reaches
# Superannuation inside build-up. Classification is contested between §402(b)
# and the foreign trust rules, and turns on the contribution split.
AU_SUPER = Scheme(
    key="au_superannuation",
    country="AU",
    name="Australian Superannuation",
    known=True,
    bucket=CONTESTED,
    treaty=False,
    treaty_article=None,
    rev_proc_relief=None,
    holder_directed_by_design=False,
    notes=(
        "**The best-known problem case.** The treaty does not clearly defer "
        "US tax on inside build-up, so growth may be currently taxable in the "
        "US while being tax-advantaged in Australia — the worst combination, "
        "and one that produces no Australian credit to offset it.",
        "Employer Superannuation Guarantee contributions support the §402(b) "
        "reading. Salary-sacrifice and personal contributions push toward the "
        "grantor-trust reading, and a self-managed super fund (SMSF) almost "
        "always lands there. **The table therefore records this as contested "
        "rather than defaulting to the §402(b) side**, which is the more "
        "comfortable reading and not the established one.",
        "Rev. Proc. 2020-17 relief may be available where the scheme meets "
        "its conditions, which is a question to put to a preparer rather than "
        "to assume in either direction.",
    ),
    source="US–Australia income tax treaty (no applicable pension article); "
           "IRC §402(b); §§671–679; Rev. Proc. 2020-17",
    verified_on="unverified — check against irs.gov and the treaty text",
)

# ── Singapore ───────────────────────────────────────────────────────────────
# There is no US–Singapore income tax treaty at all. Nothing to claim.
SG_CPF = Scheme(
    key="sg_cpf",
    country="SG",
    name="Singapore Central Provident Fund (CPF)",
    known=True,
    bucket=FOREIGN_GRANTOR_TRUST,
    treaty=False,
    treaty_article=None,
    rev_proc_relief=None,
    holder_directed_by_design=False,
    notes=(
        "**There is no US–Singapore income tax treaty.** Not an unfavourable "
        "article — no treaty. There is nothing to claim and no relief to "
        "argue from, which makes this the clearest of the problem cases.",
        "CPF interest is commonly treated as currently taxable in the US, "
        "with no foreign tax credit available because Singapore does not tax "
        "it. Tax-free locally and taxable in the US is the recurring shape.",
    ),
    source="No US–Singapore income tax treaty; IRC §§671–679; §6048",
    verified_on="unverified — check against irs.gov",
)

# ── India ───────────────────────────────────────────────────────────────────
# EPF and PPF are two different instruments and are held as two rows. An EPF is
# an employer scheme with a statutory employer match; a PPF is a self-funded
# individual account with no employer in it at all. Filing them under one key
# was how a structurally impossible §402(b) employees'-trust reading reached a
# self-funded account.
#
# **No treaty article number is encoded for India, on purpose** — the same
# position `crossborder.py` takes for the same country. Which article, if any,
# reaches a provident fund, and whether it reaches accrual or only payment, is
# precisely the question to put to a preparer; encoding a number here would
# assert an answer this table has not checked.
IN_EPF = Scheme(
    key="in_epf",
    country="IN",
    name="Indian Employees' Provident Fund (EPF)",
    known=True,
    bucket=CONTESTED,
    treaty=False,
    treaty_article=None,
    rev_proc_relief=None,
    holder_directed_by_design=False,
    notes=(
        "**Whether the treaty defers US tax on interest credited each year is "
        "the open question, and no article number is encoded here to answer "
        "it.** The common practitioner reading is that it does not, in which "
        "case EPF interest is currently taxable in the US while being exempt "
        "in India — and because India does not tax it, there is no foreign "
        "tax credit to offset the US liability.",
        "The employer's statutory matching contribution supports the §402(b) "
        "reading. Voluntary Provident Fund contributions are employee money "
        "and push toward the grantor-trust reading. With the split "
        "unrecorded both readings stay live, which is why the default is "
        "contested rather than the more favourable of the two.",
        "A **PPF is a different instrument** and is a separate row in this "
        "table — do not record one as `in_epf`.",
        "The EPF balance is a foreign financial account for FBAR and a "
        "foreign asset for Form 8938 regardless of which bucket it lands in.",
    ),
    source="US–India income tax treaty (no article number encoded — see the "
           "notes); IRC §402(b); §§671–679; §6048",
    verified_on="unverified — check against irs.gov and the treaty text",
)

IN_PPF = Scheme(
    key="in_ppf",
    country="IN",
    name="Indian Public Provident Fund (PPF)",
    known=True,
    bucket=FOREIGN_GRANTOR_TRUST,
    treaty=False,
    treaty_article=None,
    rev_proc_relief=None,
    holder_directed_by_design=True,
    notes=(
        "**A PPF is entirely self-funded.** There is no employer, so the "
        "§402(b) employees'-trust reading — which requires an employer to "
        "have established and funded the arrangement — has nothing to attach "
        "to. That is why the default here leans to the grantor-trust side "
        "rather than to the favourable one: the favourable reading is not "
        "merely weaker for a PPF, it is structurally unavailable.",
        "The holder chooses the deposit amount and the timing within the "
        "statutory band, which is holder direction of the kind that tips a "
        "scheme toward §§671–679 on its own.",
        "Interest is exempt in India, so the recurring shape applies with no "
        "offset: tax-favoured locally, potentially currently taxable in the "
        "US, and no foreign tax credit.",
        "A leaning default is still not a position. If a preparer can support "
        "a different characterisation on these facts, that is their call — "
        "what this row refuses to do is report the comfortable answer.",
    ),
    source="US–India income tax treaty (no article number encoded — see the "
           "notes); IRC §§671–679; §6048",
    verified_on="unverified — check against irs.gov and the treaty text",
)

_TABLE: dict[str, Scheme] = {
    s.key: s for s in (UK_WORKPLACE, UK_SIPP, CA_RRSP, AU_SUPER, SG_CPF,
                       IN_EPF, IN_PPF)
}


def schemes_available() -> list[str]:
    return sorted(_TABLE)


def scheme_for(key: str | None) -> Scheme:
    if not key:
        return UNKNOWN
    return _TABLE.get(str(key).strip().lower(), UNKNOWN)


# ── classification ──────────────────────────────────────────────────────────


@dataclass
class Classification:
    scheme: Scheme
    label: str
    bucket: str
    #: Forms the bucket points at. Never a filing position — a list of what a
    #: preparer has to rule on.
    forms: list[str] = field(default_factory=list)
    drivers: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    @property
    def determinable(self) -> bool:
        return self.bucket != UNKNOWN_BUCKET

    @property
    def problematic(self) -> bool:
        """Outside treaty protection, so the trust forms are in scope.

        `CONTESTED` belongs here: an unresolved characterisation carries the
        3520/3520-A exposure exactly as a resolved unfavourable one does. The
        penalty does not wait for the disagreement to settle.
        """
        return self.bucket in (EMPLOYEES_TRUST_402B, FOREIGN_GRANTOR_TRUST,
                               CONTESTED)

    @property
    def contested(self) -> bool:
        return self.bucket == CONTESTED


def classify(holding: dict) -> Classification:
    """Place one scheme in a bucket and name the filings that follow.

    The household's own facts can move a scheme *within* the non-treaty
    buckets. A self-funded, self-directed account is read as a grantor trust;
    a recorded employer-weighted contribution split resolves a `CONTESTED`
    scheme to the employees'-trust side. They cannot move a scheme *into* the
    treaty bucket, because treaty coverage is a property of the scheme and the
    treaty, not of how the holder uses it.

    A `CONTESTED` default is only ever narrowed by a fact the household
    supplied. Absent one it stays contested — it is not quietly resolved to
    the reading that produces the smaller problem.
    """
    scheme = scheme_for(holding.get("scheme"))
    label = holding.get("name") or scheme.name
    c = Classification(scheme=scheme, label=label, bucket=scheme.bucket)

    if not scheme.known:
        c.bucket = UNKNOWN_BUCKET
        c.findings.append(
            f"**`{holding.get('scheme') or 'no scheme recorded'}` is not in "
            f"the table, so the bucket is unknown — which is the answer, not a "
            f"gap to fill by analogy.** UK workplace pensions and Australian "
            f"Superannuation are both employer-established workplace schemes "
            f"with opposite US treatment; reasoning from one to the other "
            f"would be confidently wrong. Schemes checked so far: "
            f"{', '.join(schemes_available())}. Adding one means adding the "
            f"treaty position *and* the citation.")
        c.forms = ["unknown — a preparer has to place this before anything else"]
        c.findings.append(_ALWAYS_FBAR)
        return c

    employee = _num(holding.get("employee_contributions_to_date"))
    employer = _num(holding.get("employer_contributions_to_date"))
    directed = holding.get("holder_directs_investments")
    if directed is None:
        directed = scheme.holder_directed_by_design

    # ── treaty bucket ───────────────────────────────────────────────────
    if scheme.bucket == TREATY_PROTECTED:
        c.drivers.append(
            f"Treaty: {scheme.treaty_article}. Relief from Forms 3520/3520-A "
            f"{'is available' if scheme.rev_proc_relief else 'is not established'} "
            f"under the revenue procedures cited in the table.")
        c.forms = ["FinCEN 114 (FBAR)", "Form 8938 (FATCA)"]
        c.findings.append(
            "**Treaty-protected — the comfortable bucket, and not a no-filing "
            "bucket.** The treaty and the revenue procedures address the "
            "foreign-trust forms and the timing of tax on inside build-up. "
            "They do nothing about FBAR or Form 8938, which apply to the "
            "balance on their own terms.")
        if scheme.treaty:
            c.findings.append(
                "**Treaty relief is claimed, not automatic** — except where a "
                "revenue procedure makes it so, which the table records "
                "scheme by scheme. A position that is available and not "
                "claimed is the same as no position.")
    else:
        # ── non-treaty: which of the problem buckets ────────────────────
        c.drivers.append(
            "No US treaty pension article reaches this scheme"
            + (f" ({scheme.treaty_article})" if scheme.treaty_article else "")
            + ".")
        grantor_signals: list[str] = []
        employer_weighted = False
        if employee is not None and employer is not None:
            if employee > employer:
                grantor_signals.append(
                    f"employee contributions ({_money(employee)}) exceed "
                    f"employer contributions ({_money(employer)})")
            else:
                employer_weighted = True
                c.drivers.append(
                    f"Employer contributions ({_money(employer)}) exceed "
                    f"employee contributions ({_money(employee)}), which "
                    f"supports the employees'-trust reading.")
        else:
            c.findings.append(
                "**The contribution split is not recorded, so the bucket "
                "cannot be narrowed.** Whether employee contributions exceed "
                "employer contributions is one of the three facts the "
                "classification turns on, and it is on the annual statement. "
                "Absent it the table's recorded default stands unnarrowed — "
                "treat this as the weakest input in the report.")
        if directed:
            grantor_signals.append("the holder directs the investments")

        if grantor_signals:
            c.bucket = FOREIGN_GRANTOR_TRUST
            c.drivers.append("Grantor-trust signals: " + "; ".join(grantor_signals) + ".")
        elif scheme.bucket == CONTESTED and employer_weighted:
            # The contested default is narrowed only by a fact the household
            # supplied, and only in the direction that fact points.
            c.bucket = EMPLOYEES_TRUST_402B
        c.forms = ["Form 3520", "Form 3520-A", "FinCEN 114 (FBAR)",
                   "Form 8938 (FATCA)"]

        if c.bucket == CONTESTED:
            c.findings.append(
                f"**Contested — the §402(b) and grantor-trust readings are "
                f"both live, and this table will not pick between them.** "
                f"Practitioners disagree, the household's own facts have not "
                f"separated the two, and reporting the more comfortable "
                f"reading would turn a refusal into a conclusion. Plan on the "
                f"**conservative** footing: Form 3520 and Form 3520-A are in "
                f"scope until a preparer rules them out, and their non-filing "
                f"penalties **start at {_money(PENALTY_FLOOR)}**. Recording "
                f"the contribution split is what narrows this.")
        elif c.bucket == FOREIGN_GRANTOR_TRUST:
            c.findings.append(
                f"**Reads as a foreign grantor trust.** Under §§671–679 a US "
                f"person who funds a foreign trust is treated as its owner, "
                f"which brings **Form 3520 and Form 3520-A** into scope. "
                f"Non-filing penalties **start at {_money(PENALTY_FLOOR)}** "
                f"and scale with the amounts involved — and 3520-A is the "
                f"trust's own return, which a US owner is responsible for "
                f"procuring from an administrator who has never heard of it.")
        else:
            c.findings.append(
                f"**Reads as a §402(b) employees' trust**, the less bad of the "
                f"two non-treaty readings — but not a settled one, and the "
                f"3520/3520-A question is not closed by it. Under §402(b) a "
                f"highly-compensated employee can be currently taxable on "
                f"vested employer contributions, and the inside build-up may "
                f"be currently taxable too. Penalties on the trust forms "
                f"start at {_money(PENALTY_FLOOR)}.")

        c.findings.append(
            "**Tax-favoured locally and taxable in the US is the recurring "
            "shape**, and it is worse than it sounds: where the home country "
            "does not tax the growth, there is no foreign tax credit to offset "
            "the US liability. The two systems do not cancel out.")

    c.findings.append(_ALWAYS_FBAR)
    c.findings.append(
        "**This is a bucket, not a position.** Which form is filed, on what "
        "basis, and whether a treaty claim or a revenue procedure applies to "
        "these specific facts is a cross-border preparer's call. The purpose "
        "here is to establish whether one is needed, which is a decision the "
        "household can make today.")
    return c


_ALWAYS_FBAR = (
    "**FBAR and Form 8938 apply regardless of the bucket.** A pension balance "
    "is a foreign financial asset whatever its trust characterisation, and the "
    "aggregate FBAR test is easy to cross once a pension is counted. Run "
    "`foreign-reporting-audit` with the balance included — thresholds live "
    "there, not here."
)


@dataclass
class Audit:
    classifications: list[Classification] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    @property
    def unknown(self) -> list[Classification]:
        return [c for c in self.classifications if not c.determinable]

    @property
    def problematic(self) -> list[Classification]:
        return [c for c in self.classifications if c.problematic]

    @property
    def contested(self) -> list[Classification]:
        return [c for c in self.classifications if c.contested]


def audit(holdings: list[dict] | None) -> Audit:
    a = Audit()
    if not holdings:
        a.findings.append(
            "**No foreign pension schemes recorded.** If there are none, "
            "record `foreign_pensions: []` so the answer is checked rather "
            "than absent. A scheme left behind in a former country of "
            "employment counts, and a dormant one counts — the filing "
            "obligation attaches to the balance, not to contributions.")
        return a

    for h in holdings:
        a.classifications.append(classify(h))

    if a.problematic:
        a.findings.append(
            f"**{len(a.problematic)} of {len(a.classifications)} scheme(s) sit "
            f"outside treaty protection.** That is the finding to act on: a "
            f"preparer who handles the specific jurisdiction, before the next "
            f"filing deadline rather than after it.")
    if a.contested:
        a.findings.append(
            f"**{len(a.contested)} scheme(s) are recorded as contested rather "
            f"than classified.** That is the finding, not a gap in it: "
            f"practitioners disagree and the facts recorded here do not "
            f"separate the readings. Recording the employee/employer "
            f"contribution split is what narrows them, and until it is "
            f"recorded the conservative footing is the one to plan on.")
    if a.unknown:
        a.findings.append(
            f"**{len(a.unknown)} scheme(s) are not in the table.** Absence is "
            f"reported rather than guessed, because a wrong analogy between "
            f"jurisdictions is indistinguishable from an answer.")
    if not a.problematic and not a.unknown:
        a.findings.append(
            "**Every recorded scheme is treaty-protected.** The trust forms "
            "are likely out of scope; the reporting forms are not, and the "
            "treaty position still has to be claimed on the return.")
    return a


def _num(x) -> float | None:
    return None if x is None else float(x)


def _money(x) -> str:
    if x is None:
        return "not recorded"
    return f"${x:,.0f}"
