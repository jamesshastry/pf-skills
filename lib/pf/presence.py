"""One travel ledger, read by every test that counts days.

## The one idea

**A "day" means different things to different tests, and the only safe way to
hold that is one ledger with the definitions attached to it.**

- §911's Physical Presence Test counts **full days** — a complete 24-hour
  period present in a foreign country. A travel day between the US and abroad
  is not one. Neither is a day over international waters.
- A destination's residency threshold — the 183-day family of rules — almost
  always counts **any part of a day** of physical presence.
- A US state counting days toward statutory residence generally counts **any
  part of a day** too, often with its own exceptions.

The same trip therefore produces three different numbers, all correct. Two
implementations of "a day" eventually disagree about the same Tuesday, and the
disagreement surfaces as a number nobody can reconcile. So there is one
ledger, one set of derived day sets, and the differences are named here rather
than discovered.

## What this module refuses

**It does not know any country's residency threshold.** Not one. The threshold
is supplied per-destination from the facts file, the same way
`assumptions.cash_benchmark_apr` is — asked for, never fetched. A 183-day rule
encoded here from memory would be wrong for the country where it mattered,
and confidently so; several jurisdictions count differently (rolling windows,
weighted prior years, split-year rules) and the number alone would not capture
it.

**It does not decide bona fide residence.** That is a facts-and-circumstances
determination the IRS makes, not a day count. What is checkable — whether an
uninterrupted period covering an entire tax year even exists, whether the
taxpayer is eligible for the test at all — is checked; the conclusion is not
offered.

**Unknown days are not foreign days.** A gap in the ledger counts against the
Physical Presence Test rather than for it. That is the conservative direction:
the failure mode of the opposite convention is a household claiming an
exclusion it cannot substantiate under audit, where the ledger *is* the
evidence.

## Dates come from the caller

Never the clock. `meta.as_of` decides what "this year" means.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

US = "US"

#: §911(d)(1)(B). Full days present in a foreign country required within any
#: period of 12 consecutive months. Not 330 days abroad — 330 *full* days.
FULL_DAYS_REQUIRED = 330

#: The window is any 12 consecutive months, not the calendar year. Held as 365
#: days so the arithmetic is a sliding window rather than a calendar walk;
#: the difference across a leap year is one day and is reported, not hidden.
WINDOW_DAYS = 365

#: A day counted for the Physical Presence Test must be complete. Recorded
#: here as a constant so the two counting bases cannot drift apart in prose.
FULL_DAY_BASIS = (
    "a complete 24-hour period present in a foreign country — travel days to "
    "or from the US, and days over international waters, do not count"
)

#: Destination residency thresholds and US state statutory-residence counts
#: almost always use this basis instead.
PART_DAY_BASIS = "any part of a day physically present counts as a day"

PRESENCE_SOURCE = (
    "IRC §911(d)(1)(B) and Treas. Reg. §1.911-2(d) — the physical presence "
    "test: 330 full days in a foreign country within any period of 12 "
    "consecutive months, and what makes a day a full day"
)
PRESENCE_VERIFIED = (
    "unverified — check against irs.gov Publication 54 and the text of §911")


class LedgerError(Exception):
    """The ledger cannot be read at all."""


@dataclass(frozen=True)
class Stay:
    """A continuous period in one place, inclusive of both end dates."""

    country: str
    start: _dt.date
    end: _dt.date
    #: US state, where the stay is in the US. Absent means the ledger cannot
    #: answer state-level questions — which is a finding, not a zero.
    state: str | None = None
    #: True for a day or days spent in transit, including over international
    #: waters. Not a full day in a foreign country even when both endpoints
    #: are foreign.
    transit: bool = False
    label: str = ""

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


@dataclass
class Ledger:
    stays: list[Stay] = field(default_factory=list)
    #: date -> the stays covering it. A date with more than one is an overlap.
    by_date: dict[_dt.date, list[Stay]] = field(default_factory=dict)
    gaps: list[tuple[_dt.date, _dt.date]] = field(default_factory=list)
    overlaps: list[_dt.date] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    @property
    def first(self) -> _dt.date | None:
        return min((s.start for s in self.stays), default=None)

    @property
    def last(self) -> _dt.date | None:
        return max((s.end for s in self.stays), default=None)

    @property
    def span_days(self) -> int:
        if self.first is None or self.last is None:
            return 0
        return (self.last - self.first).days + 1

    @property
    def has_state_detail(self) -> bool:
        return any(s.state for s in self.stays if s.country == US)


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


def build_ledger(rows: list[dict] | None) -> Ledger:
    """Turn facts-file rows into a ledger, reporting what cannot be read.

    Malformed rows are dropped *and named*. Silently skipping one would
    shorten a window by exactly the days nobody noticed were missing.
    """
    led = Ledger()
    for i, row in enumerate(rows or []):
        label = row.get("label") or row.get("country") or f"#{i}"
        start, end = _as_date(row.get("start")), _as_date(row.get("end"))
        country = (row.get("country") or "").strip().upper()
        if not country:
            led.findings.append(f"Stay `{label}` has no country and was ignored.")
            continue
        if start is None or end is None:
            led.findings.append(
                f"Stay `{label}` has an unreadable start or end date and was "
                "ignored. Dates must be ISO `YYYY-MM-DD`.")
            continue
        if end < start:
            led.findings.append(
                f"Stay `{label}` ends before it starts and was ignored.")
            continue
        state = row.get("state")
        led.stays.append(Stay(
            country=country, start=start, end=end,
            state=(state or "").strip().upper() or None,
            transit=bool(row.get("transit")), label=str(label)))

    led.stays.sort(key=lambda s: (s.start, s.end))
    for s in led.stays:
        d = s.start
        while d <= s.end:
            led.by_date.setdefault(d, []).append(s)
            d += _dt.timedelta(days=1)

    led.overlaps = sorted(d for d, v in led.by_date.items() if len(v) > 1)

    if led.first is not None:
        gap_start = None
        d = led.first
        while d <= led.last:
            if d not in led.by_date:
                gap_start = gap_start or d
            elif gap_start is not None:
                led.gaps.append((gap_start, d - _dt.timedelta(days=1)))
                gap_start = None
            d += _dt.timedelta(days=1)
        if gap_start is not None:  # pragma: no cover - last date is covered
            led.gaps.append((gap_start, led.last))

    if led.gaps:
        total = sum((b - a).days + 1 for a, b in led.gaps)
        led.findings.append(
            f"**{total} day(s) inside the ledger's span are unaccounted for**, "
            f"in {len(led.gaps)} gap(s). They are counted as *not* full "
            "foreign days. That is deliberate — under audit the ledger is the "
            "evidence, and a day nobody recorded is a day nobody can prove.")
    if led.overlaps:
        led.findings.append(
            f"**{len(led.overlaps)} date(s) are covered by more than one "
            "stay.** For a part-day count that can be legitimate — arriving "
            "somewhere the day you left somewhere else — but check they are "
            "not duplicate entries, which would inflate every count here.")
    return led


# ── the two day sets ────────────────────────────────────────────────────────


def full_foreign_days(led: Ledger) -> set[_dt.date]:
    """Dates that are full days present in a foreign country.

    A date qualifies only if all four hold:

    1. it is covered by the ledger;
    2. no stay covering it is in the US;
    3. no stay covering it is marked `transit` — a day over international
       waters is not a day in a foreign country even between two foreign
       points, which is the single most-missed exclusion here;
    4. **both neighbouring dates are covered.** A day at the edge of what the
       ledger knows cannot be shown to have been complete.
    """
    out: set[_dt.date] = set()
    for d, stays in led.by_date.items():
        if any(s.country == US for s in stays):
            continue
        if any(s.transit for s in stays):
            continue
        if (d - _dt.timedelta(days=1)) not in led.by_date:
            continue
        if (d + _dt.timedelta(days=1)) not in led.by_date:
            continue
        out.add(d)
    return out


def count_present_days(
    led: Ledger,
    *,
    start: _dt.date,
    end: _dt.date,
    country: str | None = None,
    state: str | None = None,
) -> int | None:
    """Days present in a jurisdiction on the **part-day** basis.

    Returns `None` — not zero — when the question cannot be answered from
    this ledger: a state count against a ledger with no state detail is
    unknown, and reporting it as zero would read as "you were never there".
    """
    if state and not led.has_state_detail:
        return None
    if country is None and state is None:
        raise ValueError("count_present_days needs a country or a state")

    n = 0
    d = start
    while d <= end:
        for s in led.by_date.get(d, ()):
            if country and s.country != country.strip().upper():
                continue
            if state and s.state != state.strip().upper():
                continue
            n += 1
            break
        d += _dt.timedelta(days=1)
    return n


# ── the Physical Presence Test ──────────────────────────────────────────────


@dataclass
class PhysicalPresence:
    determinable: bool
    #: Best rolling 12-month window found, and its full-day count.
    window_start: _dt.date | None = None
    window_end: _dt.date | None = None
    best_days: int = 0
    #: The same count over the calendar tax year, for comparison.
    tax_year: int | None = None
    calendar_days: int | None = None
    passes: bool = False
    calendar_passes: bool = False
    shortfall: int = 0
    findings: list[str] = field(default_factory=list)

    @property
    def window_placement_matters(self) -> bool:
        """The optimisation is real when the rolling window wins."""
        return bool(self.passes and not self.calendar_passes)


def physical_presence(led: Ledger, *, tax_year: int | None = None) -> PhysicalPresence:
    """Find the best 12-month window, not just the calendar year.

    The window placement is a genuine optimisation, not a formality. A
    household that left in March and counts January to December fails; the
    same travel counted from March to the following February passes. Because
    the exclusion is then prorated by the days of the qualifying window that
    fall in the tax year, moving the window changes both *whether* it is
    available and *how much* of it is.
    """
    r = PhysicalPresence(determinable=False, tax_year=tax_year)
    days = full_foreign_days(led)

    if led.first is None:
        r.findings.append(
            "**No travel ledger recorded.** The Physical Presence Test is a "
            "count of days, and there is nothing to count. A ledger "
            "reconstructed from passport stamps and boarding passes after the "
            "fact is the normal starting point; build it before the return, "
            "not during an examination.")
        return r

    if led.span_days < WINDOW_DAYS:
        r.findings.append(
            f"**The ledger spans {led.span_days} days — under the "
            f"{WINDOW_DAYS} a 12-month window needs.** No window can be "
            "evaluated. Extend the ledger backwards or forwards; days outside "
            "it are unknown, and unknown days do not count toward 330.")
        if tax_year:
            r.calendar_days = sum(1 for d in days if d.year == tax_year)
        return r

    r.determinable = True

    # Sliding window over the span. Small n (a few thousand days at most), so
    # the straightforward walk is clearer than a prefix-sum and fast enough.
    best, best_start = -1, led.first
    d = led.first
    while d + _dt.timedelta(days=WINDOW_DAYS - 1) <= led.last:
        end = d + _dt.timedelta(days=WINDOW_DAYS - 1)
        n = sum(1 for x in days if d <= x <= end)
        if n > best:
            best, best_start = n, d
        d += _dt.timedelta(days=1)

    r.best_days = max(best, 0)
    r.window_start = best_start
    r.window_end = best_start + _dt.timedelta(days=WINDOW_DAYS - 1)
    r.passes = r.best_days >= FULL_DAYS_REQUIRED
    r.shortfall = max(0, FULL_DAYS_REQUIRED - r.best_days)

    if tax_year:
        r.calendar_days = sum(1 for x in days if x.year == tax_year)
        r.calendar_passes = r.calendar_days >= FULL_DAYS_REQUIRED

    if r.passes and not r.calendar_passes and tax_year:
        r.findings.append(
            f"**The calendar year fails and a rolling window passes.** "
            f"{r.calendar_days} full days in {tax_year} against "
            f"{r.best_days} in the 12 months from "
            f"{r.window_start.isoformat()}. The test is *any* period of 12 "
            "consecutive months, and choosing it well is the difference "
            "between the exclusion being available and not. The exclusion is "
            "then prorated by the qualifying days falling inside the tax "
            "year, so the placement moves the amount as well as the "
            "eligibility.")
    elif not r.passes:
        r.findings.append(
            f"**No 12-month window reaches {FULL_DAYS_REQUIRED} full days.** "
            f"The best available is {r.best_days}, from "
            f"{r.window_start.isoformat()} — short by {r.shortfall}. "
            "Bona fide residence is the other route and is not a day count; "
            "it is also unavailable to most non-citizens, so check "
            "eligibility before planning around it.")
    return r


# ── bona fide residence ─────────────────────────────────────────────────────


@dataclass
class Check:
    label: str
    state: str  # ok | fail | unknown
    detail: str


@dataclass
class BonaFide:
    #: None where eligibility for the test itself could not be established.
    eligible: bool | None = None
    checks: list[Check] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    @property
    def any_fail(self) -> bool:
        return any(c.state == "fail" for c in self.checks)

    @property
    def any_unknown(self) -> bool:
        return any(c.state == "unknown" for c in self.checks)


def bona_fide(
    facts: dict | None,
    *,
    us_status: str | None,
    citizenship: list[str] | None,
    tax_year: int | None,
) -> BonaFide:
    """Check what is checkable about bona fide residence, and stop there.

    The test is not arithmetic. It asks whether someone has established a
    residence in a foreign country for an uninterrupted period including an
    entire tax year, and it turns on intent, the nature of the stay, and what
    was told to the host country. Necessary conditions can be checked;
    sufficiency cannot, and a skill asserting it would be inventing an IRS
    determination.
    """
    f = facts or {}
    b = BonaFide()

    # Eligibility gate. Worth checking first, because a household that fails
    # it has one route and not two, and the day ledger is then the whole
    # answer.
    if us_status == "citizen":
        b.eligible = True
    elif us_status in ("permanent_resident", "nonimmigrant_visa"):
        b.eligible = None
        b.findings.append(
            "**Bona fide residence may not be available at all.** The test is "
            "open to US citizens, and to US resident aliens who are citizens "
            "or nationals of a country with which the US has an income tax "
            "treaty containing a non-discrimination article. Whether that "
            f"applies to {', '.join(citizenship or []) or 'this household'} "
            "is a treaty question and is **not** encoded here — check it "
            "before relying on this route. The Physical Presence Test has no "
            "such gate.")
    else:
        b.eligible = None

    covered = f.get("entire_tax_year_covered")
    b.checks.append(Check(
        f"Uninterrupted period covering all of {tax_year or 'the tax year'}",
        "ok" if covered is True else ("fail" if covered is False else "unknown"),
        "The period must include one **entire** tax year. A move in June "
        "qualifies for the following full year, not the year of the move — "
        "though once qualified, the earlier and later partial years can be "
        "claimed too."))

    abode = f.get("us_abode_retained")
    b.checks.append(Check(
        "No abode retained in the US",
        "fail" if abode is True else ("ok" if abode is False else "unknown"),
        "**A tax home abroad is defeated by an abode in the US**, and this "
        "sinks more claims than the day count does. It is about where "
        "personal and family ties sit, not where a house is owned — a rented "
        "family home kept available, with a spouse and children living in it, "
        "is an abode."))

    claimed = f.get("claimed_nonresident_on_foreign_return")
    b.checks.append(Check(
        "Did not claim non-residence to the host country",
        "fail" if claimed is True else ("ok" if claimed is False else "unknown"),
        "Telling the host country you are a non-resident, to avoid its tax, "
        "and telling the IRS you are a bona fide resident of it, is an "
        "inconsistency Form 2555 asks about directly. It generally ends the "
        "claim."))

    indefinite = f.get("indefinite_assignment")
    b.checks.append(Check(
        "Assignment is indefinite rather than for a stated short term",
        "ok" if indefinite is True else ("fail" if indefinite is False
                                         else "unknown"),
        "A posting with a defined end date, with the family and the home left "
        "behind, reads as a temporary absence from a US residence rather than "
        "residence abroad."))

    if b.any_unknown:
        b.findings.append(
            "**Some of these have not been answered.** Unanswered is not the "
            "same as satisfied; each one has ended a claim on its own.")
    return b


# ── a destination's own threshold ───────────────────────────────────────────


@dataclass
class DestinationTest:
    country: str | None
    days: int | None
    threshold: int | None
    start: _dt.date | None = None
    end: _dt.date | None = None
    crosses: bool | None = None
    findings: list[str] = field(default_factory=list)


def destination_test(led: Ledger, spec: dict | None) -> DestinationTest:
    """Count days in the destination and compare to a supplied threshold.

    The threshold comes from the facts file. **No country's rule is encoded
    here** — see the module docstring. The count is on the part-day basis,
    which is the common convention and is stated in the report so a country
    that counts differently is visibly a mismatch rather than a silent one.
    """
    spec = spec or {}
    country = (spec.get("country") or "").strip().upper() or None
    threshold = spec.get("threshold_days")
    start = _as_date(spec.get("tax_year_start"))
    end = _as_date(spec.get("tax_year_end"))

    t = DestinationTest(country=country, days=None, threshold=threshold,
                        start=start, end=end)
    if not country:
        t.findings.append(
            "No destination country recorded, so no local residency test was "
            "run. A US citizen owes US tax either way — but becoming tax "
            "resident somewhere else is what creates the foreign tax that "
            "makes the credit worth having, and the local filing obligation "
            "that comes with it.")
        return t
    if start is None or end is None:
        t.findings.append(
            f"**{country}'s tax year is not recorded**, so there is no period "
            "to count over. It is not always the calendar year — assuming it "
            "is will produce a count for the wrong twelve months.")
        return t

    t.days = count_present_days(led, start=start, end=end, country=country)

    if threshold is None:
        t.findings.append(
            f"**{country}'s residency threshold is not recorded, so no "
            f"conclusion is offered.** Days present in {country} over the "
            f"recorded tax year: **{t.days}**. This repository does not hold "
            "any country's residency rule — encoding one from memory is how a "
            "confident wrong answer gets produced for the one country that "
            "mattered. Supply the threshold, and check how that country "
            "counts: some use a rolling window, some weight prior years, some "
            "have a split-year rule that changes the answer entirely.")
        return t

    t.crosses = t.days is not None and t.days >= int(threshold)
    if t.crosses:
        t.findings.append(
            f"**{t.days} days in {country} against a recorded threshold of "
            f"{threshold} — crossed.** Expect a local filing obligation and "
            "local tax on some or all income. That is not necessarily bad: "
            "foreign tax paid is what feeds the Foreign Tax Credit. It does "
            "mean a second return, and it is the point at which a treaty "
            "tie-breaker becomes relevant.")
    else:
        t.findings.append(
            f"{t.days} days in {country} against a recorded threshold of "
            f"{threshold} — not crossed on a day count alone. **Day counts "
            "are usually the backstop test, not the only one.** A permanent "
            "home, a centre of vital interests, or habitual abode can make "
            "someone resident well under the day threshold.")
    return t


#: The framing that has to appear in any report built on this module.
PERPETUAL_TRAVELER_NOTE = (
    "**Being tax resident nowhere does not make a US citizen tax resident "
    "nowhere.** US taxation follows citizenship, not sleep. Someone moving "
    "between countries fast enough to trip no local threshold still files a "
    "US return on worldwide income — and has made their position *worse*, not "
    "better: with no foreign tax paid there is nothing to credit, and with no "
    "foreign tax home the §911 exclusion is unavailable even if the 330 days "
    "are there. The strategy that actually reduces the bill is the opposite "
    "one — becoming properly resident somewhere, and using the tax that "
    "creates."
)
