"""Loading, validating, and summarising a facts file.

The contract is SCHEMA.md. This module enforces the parts of it that skills
depend on, and — importantly — *refuses to guess*. A missing field produces a
`MissingFields` result the skill reports back to the user, never a default.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

#: A figure older than this is reported as stale. Vehicle values move fast
#: enough that a two-year-old number will not survive a carrier conversation.
STALE_AFTER_DAYS = 365

LIQUID = "liquid"
AGE_RESTRICTED = "age_restricted"
ILLIQUID = "illiquid"
TIERS = (LIQUID, AGE_RESTRICTED, ILLIQUID)

#: Additive classifications used where ``tier`` is too broad.  In particular,
#: ``liquid`` correctly includes stock that can settle in days, but stock is
#: not cash for a closing reserve and not every asset funds retirement.
CASH_EQUIVALENT = "cash_equivalent"
MARKETABLE = "marketable"
RESTRICTED = "restricted"
RESERVE_ILLIQUID = "illiquid"
LIQUIDITY_CLASSES = (CASH_EQUIVALENT, MARKETABLE, RESTRICTED,
                     RESERVE_ILLIQUID)


class FactsError(Exception):
    """The facts file cannot be used at all (unparseable, wrong version)."""


@dataclass(frozen=True)
class Staleness:
    label: str
    as_of: _dt.date | None
    days: int | None

    @property
    def is_stale(self) -> bool:
        return self.days is None or self.days > STALE_AFTER_DAYS


@dataclass
class Preflight:
    """Result of checking a facts mapping against one skill's requirements."""

    missing: list[str] = field(default_factory=list)
    stale: list[Staleness] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing


def _duplicate_key_error(key: Any, first_line: int, second_line: int) -> FactsError:
    """The message this defect deserves.

    "duplicate key found" sends someone hunting through a 600-line file, so
    both locations are named. The explanation is here rather than in a comment
    because the person reading it is mid-incident and will not go looking.
    """
    return FactsError(
        f"duplicate key `{key}` in the facts file.\n"
        f"  first defined at line {first_line}\n"
        f"  defined again at line {second_line}\n"
        "\n"
        "YAML resolves this silently: the second block wins and the first is "
        "discarded. Nothing downstream can tell, so every skill produces a "
        "confident, correctly formatted report about whichever half survived. "
        "This is refused rather than resolved because there is no safe guess "
        "about which one you meant.\n"
        "\n"
        "Merge the two blocks into one. Do not simply delete the later block — "
        "it is the one that has been in effect."
    )


def _strict_yaml_loader():
    """A SafeLoader that refuses duplicate mapping keys.

    Built here rather than at import time because PyYAML is an optional
    dependency — a `.json` facts file must work without it.

    `construct_mapping` is called once per mapping node, so overriding it
    catches duplicates at the top level, nested, and inside list items,
    without the caller needing to know which.
    """
    import yaml  # noqa: PLC0415

    class StrictLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            seen: dict[Any, int] = {}
            for key_node, _value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                try:
                    hash(key)
                except TypeError:          # an unhashable key is its own bug
                    continue
                line = key_node.start_mark.line + 1   # marks are 0-based
                if key in seen:
                    raise _duplicate_key_error(key, seen[key], line)
                seen[key] = line
            return super().construct_mapping(node, deep=deep)

    return StrictLoader


def _json_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """The same guard for JSON, which also keeps the last of a duplicate pair.

    JSON carries no line numbers through `object_pairs_hook`, so the message
    is necessarily weaker — but silently discarding half a file is the same
    defect whichever syntax it arrives in.
    """
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise FactsError(
                f"duplicate key `{key}` in the facts file.\n"
                "JSON resolves this silently — the later value wins and the "
                "earlier one is discarded, so a skill reports confidently on "
                "half the data. Merge the two rather than deleting one."
            )
        out[key] = value
    return out


def load(path: str | Path) -> dict[str, Any]:
    """Read a facts file. YAML if PyYAML is installed; JSON always.

    Duplicate keys are an error, not a resolution. See `_duplicate_key_error`.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        data = json.loads(text, object_pairs_hook=_json_no_duplicates)
    else:
        try:
            import yaml  # noqa: PLC0415
        except ModuleNotFoundError as exc:  # pragma: no cover - env dependent
            raise FactsError(
                "Reading a .yml facts file needs PyYAML.\n"
                "  pip install pyyaml     (or run the skill with: uv run)\n"
                "A .json facts file works with no dependencies."
            ) from exc
        try:
            data = yaml.load(text, Loader=_strict_yaml_loader())  # noqa: S506
        except yaml.YAMLError as exc:
            if isinstance(exc, FactsError):   # pragma: no cover - defensive
                raise
            raise FactsError(f"{p} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise FactsError(f"{p} did not parse to a mapping.")
    check_version(data)
    return data


def check_version(facts: dict[str, Any]) -> None:
    v = _dig(facts, "meta.schema_version")
    if v is None:
        raise FactsError("meta.schema_version is missing. See SCHEMA.md.")
    if v != SCHEMA_VERSION:
        raise FactsError(
            f"facts file is schema_version {v}; this library speaks {SCHEMA_VERSION}."
        )


def _dig(facts: Any, dotted: str) -> Any:
    """Fetch a dotted path. `a.b[].c` means 'c must exist on every item of b'."""
    cur = facts
    for part in dotted.split("."):
        if part.endswith("[]"):
            key = part[:-2]
            if not isinstance(cur, dict) or not cur.get(key):
                return None
            return cur[key]  # caller handles the list
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def require(facts: dict[str, Any], paths: list[str]) -> Preflight:
    """Check required dotted paths, including `list[].field` forms.

    Missing paths are de-duplicated. Several `things[].field` requirements all
    report the same missing `things` head, and listing it three times reads
    like three separate problems.
    """
    pre = Preflight()
    for dotted in paths:
        if "[]." in dotted:
            head, tail = dotted.split("[].", 1)
            items = _dig(facts, head + "[]")
            if not items:
                pre.missing.append(head)
                continue
            for i, item in enumerate(items):
                label = item.get("label") or item.get("id") or f"#{i}"
                if _dig(item, tail) is None:
                    pre.missing.append(f"{head}[{label}].{tail}")
        elif _dig(facts, dotted) is None:
            pre.missing.append(dotted)

    seen: set[str] = set()
    pre.missing = [m for m in pre.missing
                   if not (m in seen or seen.add(m))]
    return pre


# ── balance sheet ───────────────────────────────────────────────────────────


def tier_total(facts: dict[str, Any], tier: str) -> float:
    """Sum a tier, excluding anything marked `pending`.

    A pending position is recorded but not counted: an unsettled order is
    either additional to an existing balance or came out of it, and until
    someone confirms which, counting it may double-count. Recording it is
    still worth doing — it makes the position visible and comparable — but it
    must not inflate a total that a recommendation is measured against.
    """
    if tier not in TIERS:
        raise ValueError(f"unknown tier {tier!r}")
    rows = _dig(facts, "household.balance_sheet") or []
    return float(sum(r.get("value", 0) for r in rows
                     if r.get("tier") == tier and not r.get("pending")))


def liquid(facts: dict[str, Any]) -> float:
    """What the household can spend within days without penalty."""
    return tier_total(facts, LIQUID)


def attachable(facts: dict[str, Any]) -> float:
    """Assets a judgment creditor can plausibly reach.

    Liquid + illiquid. `age_restricted` is excluded: ERISA plans are broadly
    protected from creditors, and IRAs are protected to a state-set amount.
    That state variation is why the skill states the assumption rather than
    burying it.
    """
    return tier_total(facts, LIQUID) + tier_total(facts, ILLIQUID)


def household_income(facts: dict[str, Any]) -> float:
    members = _dig(facts, "household.members") or []
    return float(sum(m.get("income_annual", 0) or 0 for m in members))


def household_income_components(facts: dict[str, Any]) -> dict[str, float]:
    """Aggregate named compensation components across household members."""
    out: dict[str, float] = {}
    for member in _dig(facts, "household.members") or []:
        for name, value in (member.get("income_components") or {}).items():
            out[str(name)] = out.get(str(name), 0.0) + float(value or 0.0)
    return out


def dependents(facts: dict[str, Any]) -> list[dict[str, Any]]:
    members = _dig(facts, "household.members") or []
    return [m for m in members if m.get("role") == "dependent"]


def months_of_spending(facts: dict[str, Any]) -> float | None:
    spend = _dig(facts, "household.annual_spending")
    if not spend:
        return None
    return liquid(facts) / (float(spend) / 12.0)


@dataclass
class ClassifiedAssets:
    """An auditable balance-sheet slice, with unknown rows kept visible."""

    included: float = 0.0
    excluded: float = 0.0
    unknown: list[str] = field(default_factory=list)
    rows: list[tuple[str, float]] = field(default_factory=list)
    by_class: dict[str, float] = field(default_factory=dict)


def retirement_assets(facts: dict[str, Any]) -> ClassifiedAssets:
    """Assets explicitly available to fund retirement.

    ``retirement_eligible`` is authoritative.  For older facts files, an
    account whose wrapper is unambiguously retirement-directed is included;
    every other unclassified row is excluded and named.  This is deliberately
    asymmetric: understating a projection with an explicit uncertainty is
    safer than silently calling a home, 529, or personal property a retirement
    portfolio.
    """
    out = ClassifiedAssets()
    for row in _dig(facts, "household.balance_sheet") or []:
        if row.get("pending"):
            continue
        name = str(row.get("name") or "unnamed asset")
        value = max(
            0.0,
            float(row.get("value") or 0.0)
            - float(row.get("margin_debt") or 0.0),
        )
        eligible = row.get("retirement_eligible")
        if eligible is None:
            account_type = row.get("account_type")
            if account_type in ("tax_deferred", "roth", "hsa"):
                eligible = True
            else:
                out.unknown.append(name)
                out.excluded += value
                continue
        if eligible:
            out.included += value
            out.rows.append((name, value))
        else:
            out.excluded += value
    return out


def reserve_assets(facts: dict[str, Any]) -> ClassifiedAssets:
    """Cash-equivalent reserves, without treating marketable stock as cash.

    Rows classified ``marketable`` are returned in ``rows`` for disclosure,
    but only ``cash_equivalent`` balances enter ``included``.  Unclassified
    rows are never promoted from the legacy ``liquid`` tier at par.
    """
    out = ClassifiedAssets()
    for row in _dig(facts, "household.balance_sheet") or []:
        if row.get("pending"):
            continue
        name = str(row.get("name") or "unnamed asset")
        value = float(row.get("value") or 0.0)
        classification = row.get("liquidity_class")
        if classification not in LIQUIDITY_CLASSES:
            out.unknown.append(name)
            out.excluded += value
            continue
        out.by_class[classification] = out.by_class.get(classification, 0.0) + value
        if classification == CASH_EQUIVALENT:
            out.included += value
        else:
            out.excluded += value
            if classification == MARKETABLE:
                out.rows.append((name, value))
    return out


# ── dates ───────────────────────────────────────────────────────────────────


def as_of(facts: dict[str, Any]) -> _dt.date | None:
    return _as_date(_dig(facts, "meta.as_of"))


def _as_date(value: Any) -> _dt.date | None:
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


@dataclass(frozen=True)
class Deadline:
    """A finding that stops being actionable on a date.

    ROADMAP open question 4. Insurability windows, rider-exercise options and
    open-enrolment periods all expire, and a recommendation that quietly went
    stale is worse than no recommendation — the household believes it is still
    available.
    """

    label: str
    on: _dt.date | None
    days_remaining: int | None

    @property
    def passed(self) -> bool:
        return self.days_remaining is not None and self.days_remaining < 0

    @property
    def urgency(self) -> str:
        if self.days_remaining is None:
            return "unknown"
        if self.days_remaining < 0:
            return "passed"
        if self.days_remaining <= 180:
            return "urgent"
        if self.days_remaining <= 730:
            return "approaching"
        return "distant"


def deadline(label: str, on: Any, reference: _dt.date | None = None) -> Deadline:
    d = _as_date(on)
    ref = reference or _dt.date.today()
    if d is None:
        return Deadline(label, None, None)
    return Deadline(label, d, (d - ref).days)


def staleness(label: str, value_as_of: Any, reference: _dt.date | None) -> Staleness:
    d = _as_date(value_as_of)
    ref = reference or _dt.date.today()
    if d is None:
        return Staleness(label, None, None)
    return Staleness(label, d, (ref - d).days)
