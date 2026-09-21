#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Provenance report — what this repo knows about the world, and when it checked.

Facts-free by default: this is about the repository's own tables, not any
household. With --facts it additionally audits annual-parameter metadata and
reports schema drift without displaying the underlying private values.

    uv run skills/reference-data-refresh/run.py
"""
from __future__ import annotations
import argparse
import datetime as dt
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import annual_parameters as A  # noqa: E402
from pf import intake as I, provenance as P  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

SEV = {"blocker": "🚫 **BLOCKER**", "stale": "⚠️ Stale", "unverified": "· Unverified"}


def fmt(v) -> str:
    if isinstance(v, bool) or v is None:
        return f"`{v}`"
    if isinstance(v, dict):
        return "  ·  ".join(f"{k}: {fmt(x)}" for k, x in v.items())
    if isinstance(v, (tuple, list)):
        return " / ".join(fmt(x) for x in v)
    if isinstance(v, int) and abs(v) >= 1000:
        return f"**${v:,}**"
    return f"**{v}**"


def _tables(annual_only: bool) -> list[P.Table]:
    return [table for table in P.registry()
            if not annual_only or table.cadence == P.ANNUAL]


def _entry_is_selected(
    table: P.Table,
    entry: P.Entry,
    *,
    annual_only: bool,
    target_year: int,
) -> bool:
    return not (
        annual_only
        and table.requires_current_year
        and entry.key != str(target_year)
    )


def _selected_issues(
    *,
    today: dt.date,
    target_year: int,
    annual_only: bool,
) -> list[P.Issue]:
    issues = P.check(today, required_year=target_year)
    if not annual_only:
        return issues
    annual = {table.name: table for table in _tables(True)}
    return [
        issue for issue in issues
        if issue.table in annual and (
            not annual[issue.table].requires_current_year
            or issue.key == str(target_year)
        )
    ]


def checklist(*, annual_only: bool, target_year: int) -> int:
    """Every asserted value, generated from the tables themselves.

    Generated rather than hand-written on purpose: a hand-written checklist
    silently omits whatever was added to a table after it.
    """
    today = dt.date.today()
    out: list[str] = []
    w = out.append

    tables = _tables(annual_only)
    entries = [
        (table, entry)
        for table in tables
        for entry in table.entries
        if _entry_is_selected(
            table, entry, annual_only=annual_only,
            target_year=target_year)
    ]
    total = sum(len(entry.values) for _, entry in entries)
    w("# Reference data verification checklist")
    w("")
    w(f"Generated {today.isoformat()} from the tables themselves — **"
      f"{total} asserted values** across {len(tables)} table(s).")
    if annual_only:
        w(f"Annual-only view for tax year **{target_year}**.")
    w("")
    w("Check each value against the authority's own page—not a summary article "
      "or search result. An existing verification date records the last review; "
      "it does not make the value permanently current.")
    w("")
    w("**When a whole entry checks out**, set `verified_on: <today>` on it in "
      "the module and re-run `reference-data-refresh` to confirm the report "
      "changes. **If any value is wrong**, fix it and note what it was — a "
      "wrong entry that has been quoted in a report is a defect, not a typo.")

    for tb in tables:
        w("")
        w(f"## {tb.name}")
        w("")
        w(f"`{tb.module}` · changes **{tb.cadence}**")
        w("")
        for u in (tb.url or tb.authority).split(" · "):
            w(f"- {u}")
        for e in tb.entries:
            if not _entry_is_selected(
                    tb, e, annual_only=annual_only,
                    target_year=target_year):
                continue
            w("")
            w(f"### `{e.key}`")
            w("")
            if not e.values:
                w("- [ ] *(no individual values recorded)*")
                continue
            for k, v in e.values.items():
                w(f"- [ ] `{k}` = {fmt(v)}")
            w("")
            w(f"  → then set `verified_on` on `{e.key}` in `{tb.module}`")

    w("")
    w("---")
    w("")
    w("## Why this matters more than it looks")
    w("")
    w("These are the only values in the repository that can be **wrong rather "
      "than merely debatable**. Every threshold elsewhere is a judgement you "
      "can argue with; these are facts, and a wrong one propagates silently "
      "into a confident dollar figure.")
    w("")
    w("The proposed clusters would add federal brackets, the standard "
      "deduction, QBI thresholds, §179 limits, ACA subsidy tables and IRMAA "
      "tiers to the same file. **Verifying what is already here is the "
      "precondition for that, not a follow-up to it** — see `REVIEW.md` A3.")
    print("\n".join(out))
    return 0


def drift_section(facts_path: str, facts: dict) -> list[str]:
    """Fields in a household file no skill reads. Advisory, never a blocker:
    a household legitimately records figures before any skill consumes them,
    and failing their run for being ahead of the schema would punish exactly
    the diligence this check is meant to notice."""
    out: list[str] = []
    w = out.append
    consumed = I.consumed_paths(ROOT / "skills", ROOT / "lib" / "pf")
    uncovered = I.drift(facts, consumed)
    w("")
    w("## Schema drift")
    w("")
    w(f"Read from `{facts_path}`.")
    w("")
    if not uncovered:
        w("No drift: every recorded field is read by at least one skill.")
    else:
        w(f"**{len(uncovered)} recorded field(s) no skill consumes.** Either "
          "private analysis has outrun the public schema — the case this "
          "check exists for — or the field is misspelled, or it belongs to "
          "a skill not yet built:")
        w("")
        for leaf in uncovered:
            w(f"- `{leaf}`")
    return out


def annual_facts_section(
    facts: dict,
    *,
    target_year: int,
    today: dt.date,
) -> tuple[list[str], int]:
    """Report annual provenance without echoing any private parameter value."""
    out: list[str] = []
    w = out.append
    audits = A.audit(facts, target_year=target_year, today=today)
    active = [audit for audit in audits if audit.active]
    issues = [
        (audit.group.label, issue)
        for audit in active
        for issue in audit.issues
    ]

    w("")
    w("## Private annual-parameter metadata")
    w("")
    w(f"Target tax year: **{target_year}**. Values remain local and are not "
      "printed by this audit.")
    w("")
    w("| Group | Scope | Fields present | Tax year | Verified | Sources | Status |")
    w("|---|---|---:|---:|---|---:|---|")
    for audit in audits:
        status = ("not used" if not audit.active else
                  "attested" if audit.ready else "needs review")
        verified = audit.verified_on.isoformat() if audit.verified_on else "—"
        year = str(audit.tax_year) if audit.tax_year is not None else "—"
        w(f"| {audit.group.label} | {audit.group.scope} | "
          f"{len(audit.present_paths)} | {year} | {verified} | "
          f"{audit.source_count} | {status} |")

    if issues:
        w("")
        w("### Annual-parameter issues")
        w("")
        for label, issue in issues:
            w(f"- ⚠️ **{label}** — {issue}.")
    return out, len(issues)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checklist", action="store_true",
                    help="emit a verification checklist of every asserted value")
    ap.add_argument("--annual-only", action="store_true",
                    help="limit repository checks to annual tables")
    year = ap.add_mutually_exclusive_group()
    year.add_argument("--target-year", type=int, default=None, metavar="YEAR",
                      help="year that must be ready; defaults to facts or today")
    year.add_argument("--scheduled", action="store_true",
                      help="select next year in November and December")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero for stale or unverified data too")
    ap.add_argument("--facts", default=None, metavar="FILE",
                    help="also audit private annual metadata and schema drift")
    args = ap.parse_args()

    today = dt.date.today()
    facts = None
    if args.facts:
        import yaml
        with open(args.facts, encoding="utf-8") as fh:
            facts = yaml.safe_load(fh) or {}
        if not isinstance(facts, dict):
            ap.error("--facts must contain a YAML mapping")

    target_year = A.scheduled_target_year(today) if args.scheduled else args.target_year
    if target_year is None and facts is not None:
        target_year = A.infer_tax_year(facts)
    target_year = target_year or today.year
    if target_year < 1900 or target_year > 9999:
        ap.error("--target-year must be a four-digit year")

    if args.checklist:
        return checklist(
            annual_only=args.annual_only,
            target_year=target_year,
        )

    out: list[str] = []
    w = out.append

    w("# Reference data provenance")
    w("")
    w(f"As of **{today.isoformat()}**.")
    w(f"Annual readiness target: **{target_year}**.")
    w("")
    w("Every other module in this repository encodes reasoning, which does "
      "not expire. These tables encode **facts about the outside world**, "
      "which do.")
    w("")

    tables = _tables(args.annual_only)
    issues = _selected_issues(
        today=today,
        target_year=target_year,
        annual_only=args.annual_only,
    )
    blockers = [i for i in issues if i.severity == "blocker"]
    w(f"**{len(blockers)} blocker(s)** · {len(issues)} issue(s) total.")

    for t in tables:
        w("")
        w(f"## {t.name}")
        w("")
        w(f"`{t.module}` · {t.holds}")
        w("")
        w(f"**Authority:** {t.authority} · **changes:** {t.cadence} · "
          f"**tolerance:** {P.MAX_AGE_DAYS[t.cadence] // 365} year(s)")
        w("")
        w("| Entry | Verified | Source |")
        w("|---|---|---|")
        for e in t.entries:
            if not _entry_is_selected(
                    t, e, annual_only=args.annual_only,
                    target_year=target_year):
                continue
            when = ("**never**" if e.self_declared_unverified
                    else e.verified_on.isoformat() if e.verified_on else "**unknown**")
            w(f"| `{e.key}` | {when} | {e.source or '—'} |")

    if issues:
        w("")
        w("## Issues")
        w("")
        for i in sorted(issues, key=lambda x: x.severity != "blocker"):
            w(f"- {SEV[i.severity]} **{i.table} / {i.key}** — {i.detail}")

    facts_issue_count = 0
    if facts is not None:
        section, facts_issue_count = annual_facts_section(
            facts, target_year=target_year, today=today)
        out.extend(section)
        out.extend(drift_section(args.facts, facts))

    w("")
    w("---")
    w("")
    w("Run the `reference-data-refresh` skill to act on this. Do not edit the "
      "tables from memory.")
    print("\n".join(out))
    strict_issues = args.strict and bool(issues or facts_issue_count)
    return 1 if blockers or strict_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
