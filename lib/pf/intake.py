"""What is in `documents/`, what the schema still needs, and the gap between.

## The one idea

Fifty-four skills read `inputs/facts.yml`. **Nothing writes it.** A new
household's first hour is spent hand-transcribing figures out of PDFs into a
39KB example file — which is precisely the task most likely to introduce the
transcription and figure-drift defects this repository exists to prevent.

This module does not parse documents. It builds the **worklist**: which schema
fields are still unset, which document would answer each one, and which of
those documents appear to be present. An agent with the documents open does the
reading; this decides what is worth reading *for*, and in what order.

## Why coverage is measured against skills, not against the schema

The schema has several hundred fields and nobody fills all of them. Measuring
"percent complete" against the whole schema produces a number that is
discouraging, meaningless, and never reaches 100.

So completeness is measured the only way that pays: **how many skills can
actually run**. Ten fields that unlock four skills beat forty that unlock none,
and the ordering falls out of the data rather than from an opinion about what
matters.

## What it refuses

It does not read financial documents, guess at a value from a filename, or
infer one field from another. A field is set or it is not. The output is a
list of questions, and a question with an invented answer is worse than an
open one — which is the same rule the rest of the repository runs on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Filename fragments that suggest a document answers a given area. Matched
#: case-insensitively against the file *name* only. Deliberately generous:
#: a false positive costs one glance, a false negative costs a missed field.
DOC_HINTS: dict[str, tuple[str, ...]] = {
    "auto": ("auto", "vehicle", "car", "geico", "progressive", "statefarm",
             "state-farm", "allstate", "policy-auto"),
    "property": ("renter", "homeowner", "home-policy", "condo", "hazard",
                 "dwelling", "ho3", "ho-3", "ho6"),
    "umbrella": ("umbrella", "excess-liability"),
    "insurance.life": ("life", "term", "whole-life", "universal", "vul",
                       "annual-statement"),
    "insurance.disability": ("disability", "ltd", "di-policy", "income-protection"),
    "household.balance_sheet": ("statement", "brokerage", "401k", "401-k",
                                "ira", "hsa", "529", "vanguard", "fidelity",
                                "schwab", "bank", "checking", "savings"),
    "equity_comp": ("equity", "rsu", "grant", "vest", "stock-plan", "etrade",
                    "shareworks", "carta"),
    "debts": ("loan", "mortgage", "student", "card-statement", "heloc"),
    "tax": ("1040", "1099", "w-2", "w2", "tax-return", "schedule-", "8938",
            "fbar", "114"),
    "foreign_accounts": ("nre", "nro", "foreign", "overseas", "fbar", "8938"),
    "property_real_estate": ("rental", "closing", "settlement", "hud-1",
                             "depreciation-schedule"),
}

#: Documents worth having that no filename will announce, because they are
#: usually not files at all. Listed so the report can ask rather than assume.
OFF_PAPER = (
    ("household.annual_spending",
     "Twelve months of spending. A budgeting export, or last year's total "
     "outflow minus savings — not a guess at the monthly figure times twelve."),
    ("meta.jurisdiction.state",
     "Which US state, and since when. Required, with no default: liability "
     "minimums, community property and homestead rules all turn on it."),
    ("household.members[].citizenship",
     "Citizenship and immigration status for each adult. Three separate "
     "taxes turn on three different answers here — see `status.py`."),
    ("foreign_accounts[].max_value_during_year",
     "The PEAK balance of each foreign account in each year, not the "
     "year-end figure. Only a full year of statements shows it."),
)


@dataclass
class Document:
    name: str
    size_bytes: int
    #: Schema areas this filename suggests it might answer.
    suggests: tuple[str, ...] = ()

    @property
    def unrecognised(self) -> bool:
        return not self.suggests


@dataclass
class Gap:
    """One skill that cannot run yet, and what it is waiting on."""
    skill: str
    missing: tuple[str, ...]

    @property
    def distance(self) -> int:
        return len(self.missing)


@dataclass
class IntakeReport:
    documents: list[Document] = field(default_factory=list)
    runnable: list[str] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    #: Missing field -> the skills it blocks. Sorted by blast radius.
    blocking: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)

    @property
    def total_skills(self) -> int:
        return len(self.runnable) + len(self.gaps)

    @property
    def nearly_there(self) -> list[Gap]:
        """Skills blocked on one or two fields — where the next hour pays."""
        return [g for g in sorted(self.gaps, key=lambda g: g.distance)
                if g.distance <= 2]


def classify(name: str, size_bytes: int = 0) -> Document:
    low = name.lower()
    hits = tuple(sorted(area for area, frags in DOC_HINTS.items()
                        if any(f in low for f in frags)))
    return Document(name=name, size_bytes=size_bytes, suggests=hits)


def _present(facts: dict, dotted: str) -> bool:
    """Whether a required path resolves to something other than None.

    Uses the same resolver the skills use, so "present" here means exactly
    what it means at the point a skill refuses to run. An empty list counts as
    absent: `foreign_accounts: []` is an answer, but an empty `vehicles` list
    means the section was stubbed and never filled.
    """
    from . import facts as F
    v = F._dig(facts, dotted)
    if v is None:
        return False
    if isinstance(v, (list, dict)) and len(v) == 0:
        return False
    return True


def assess(facts: dict, requirements: dict[str, list[str]],
           documents: list[Document] | None = None) -> IntakeReport:
    """Which skills run, which do not, and what each is waiting on.

    `requirements` maps skill name to its declared `REQUIRED` paths, read from
    the skills themselves rather than restated here — a second copy of that
    list would drift from the runners within a release.
    """
    r = IntakeReport(documents=list(documents or []))
    blocks: dict[str, list[str]] = {}

    for skill in sorted(requirements):
        missing = tuple(p for p in requirements[skill] if not _present(facts, p))
        if missing:
            r.gaps.append(Gap(skill=skill, missing=missing))
            for p in missing:
                blocks.setdefault(p, []).append(skill)
        else:
            r.runnable.append(skill)

    r.blocking = sorted(((p, tuple(sorted(s))) for p, s in blocks.items()),
                        key=lambda kv: (-len(kv[1]), kv[0]))
    return r


def suggested_documents(report: IntakeReport) -> list[tuple[str, tuple[str, ...]]]:
    """For each blocking field, which document areas would plausibly answer it.

    Returns the field and the matching areas from `DOC_HINTS`. A field with no
    matching area is still returned, with an empty tuple — "we do not know
    which document has this" is information, not a reason to omit the row.
    """
    out = []
    for path, _skills in report.blocking:
        root = path.split("[")[0]
        areas = tuple(a for a in DOC_HINTS
                      if root.startswith(a) or a.startswith(root.split(".")[0]))
        out.append((path, areas))
    return out


#: Skills that take no `--facts`, so they declare no requirements to run
#: against. `reference-data-refresh` reports on the repository's own tables
#: rather than a household; `document-intake` runs before a facts file
#: exists. Every consumer of the skill directory skips the same set — it
#: lives here rather than in each runner so the set cannot drift.
FACTS_FREE = frozenset({"reference-data-refresh", "document-intake"})


def skill_requirements(skills_dir, *, skip=FACTS_FREE) -> dict[str, list[str]]:
    """Each skill's declared inputs, read from its own SKILL.md.

    Read rather than restated: a second copy of this mapping would drift
    from the runners within a release, and the contract tests already
    guarantee that `requires` matches each runner's REQUIRED.
    """
    from pathlib import Path
    out: dict[str, list[str]] = {}
    for d in sorted(Path(skills_dir).iterdir()):
        if not d.is_dir() or d.name in skip:
            continue
        md = d / "SKILL.md"
        if not md.exists():
            continue
        paths, inside = [], False
        for line in md.read_text(encoding="utf-8").splitlines():
            if line.strip() == "requires:":
                inside = True
                continue
            if inside:
                s = line.strip()
                if s.startswith("- "):
                    paths.append(s[2:].split("#")[0].strip())
                elif s and not s.startswith("#"):
                    break
        out[d.name] = paths
    return out


def consumed_paths(skills_dir, lib_dir) -> set[str]:
    """Every facts path any skill can read, required or optional.

    Union of two sources, both read rather than restated: each skill's
    declared `requires` (which the contract tests already pin to its
    runner's REQUIRED), and every string literal passed to a `*_dig`
    call in the runners plus the lib modules that read whole facts
    (`conflicts` predicates, `facts` helpers). A skill that reads a
    subtree covers everything beneath it; optionals count, because an
    unread *optional* is still read when present.
    """
    import ast
    from pathlib import Path
    out: set[str] = set()
    for paths in skill_requirements(skills_dir).values():
        out.update(paths)
    sources = sorted(Path(skills_dir).glob("*/run.py"))
    for name in ("conflicts.py", "facts.py"):
        p = Path(lib_dir) / name
        if p.exists():
            sources.append(p)
    for src in sources:
        try:
            tree = ast.parse(src.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            # F._dig in runners, bare _dig in the scanned lib modules.
            is_dig = (isinstance(fn, ast.Attribute) and fn.attr == "_dig"
                      or isinstance(fn, ast.Name) and fn.id == "_dig")
            if not is_dig:
                continue
            # _dig takes (facts, dotted): the path is the second argument.
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                arg = node.args[1].value
                if isinstance(arg, str) and arg:
                    out.add(arg)
    return out


def _leaves(node, prefix: str = ""):
    """(Scalar leaf path, value) pairs of a facts file, list indices dropped."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _leaves(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(node, list):
        for v in node:
            yield from _leaves(v, prefix)
    else:
        yield prefix, node


def drift(facts: dict, consumed: set[str]) -> list[str]:
    """Facts-file leaves no skill reads, sorted.

    `None` leaves are skipped: null means nobody looked, and flagging every
    untouched skeleton field would bury the real signal — recorded data the
    library ignores. A leaf counts as read when a consumed path equals it or
    sits above it (whole-subtree reads cover their children).
    """
    out = []
    for leaf, value in _leaves(facts):
        if value is None:
            continue
        if not any(c == leaf or leaf.startswith(c + ".") or c.startswith(leaf + ".")
                   for c in consumed):
            out.append(leaf)
    return sorted(set(out))


_SAFE_NAME = re.compile(r"^[\w\-. ]+$")


def looks_renamed_for_privacy(name: str) -> bool:
    """Whether a filename itself carries personal data.

    A statement saved as `Jane-Q-Smith-acct-4417-Nov.pdf` puts a name and a
    partial account number into a directory listing, a shell history and any
    screenshot of either. `documents/` is gitignored, so this never reaches
    git — but gitignore does not protect a terminal recording or a support
    ticket, and the fix costs one `mv`.
    """
    if not _SAFE_NAME.match(name):
        return False
    stem = name.rsplit(".", 1)[0]
    # Two or more capitalised words reads as a person's name.
    if len(re.findall(r"\b[A-Z][a-z]{2,}\b", stem)) >= 2:
        return True
    # A long digit run reads as an account or policy number. Five digits, not
    # four: at four this fires on every year (`-2026`) and on every tax form
    # (`1040`, `1099`, `8938`, `5471`), which is most of what belongs in a
    # well-named statement. A warning that fires on good filenames trains the
    # reader to ignore it, and then it is worse than absent.
    #
    # The cost is a masked "last four" of an account, which this will miss.
    # That is the right trade: the four digits are already the redacted form.
    return bool(re.search(r"(?<!\d)\d{5,}(?!\d)", stem))
