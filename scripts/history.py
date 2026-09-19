#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Explicit local commands for immutable financial-history snapshots."""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from pf import facts as F, timeseries as T  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use YYYY-MM-DD") from exc


def money(value: float | None, currency: str | None) -> str:
    if value is None:
        return "unknown"
    return f"{currency + ' ' if currency else ''}{value:,.2f}"


def capture(args: argparse.Namespace) -> int:
    facts = F.load(args.facts)
    snapshot = T.capture_snapshot(
        facts,
        snapshot_id=args.snapshot_id,
        effective_date=args.effective_date,
        observed_at=args.observed_at,
        completeness=args.completeness,
    )
    T.save_snapshot(snapshot, args.output)
    print(f"saved immutable snapshot {snapshot.snapshot_id} to {args.output}")
    for note in snapshot.notes:
        print(f"gap: {note}")
    return 0


def analyze(args: argparse.Namespace) -> int:
    source = T.load_snapshot(args.snapshot)
    result = T.analyze_snapshot(
        source,
        calculated_at=args.calculated_at,
        skills_dir=args.skills_dir,
        analysis_snapshot_id=args.snapshot_id,
    )
    T.save_snapshot(result, args.output)
    print(f"saved analysis snapshot {result.snapshot_id} to {args.output}")
    return 0


def compare(args: argparse.Namespace) -> int:
    if len(args.snapshots) < 2:
        raise T.HistoryError("compare requires at least two snapshot files")
    history = T.load_history(args.snapshots)
    wanted = set(args.metric) if args.metric else None
    summary = T.summarize_history(history, metric_ids=wanted)
    print("# Financial history comparison\n")
    print("| Metric | Clock / scenario | Beginning | Ending | Change | Change % | Driver | Unexplained |")
    print("|---|---|---:|---:|---:|---:|---|---:|")
    for change in summary.changes:
        start, end = change.start, change.end
        pct = "—" if change.percentage_change is None else f"{change.percentage_change:.1%}"
        print(
            f"| `{start.metric_id}` | {start.clock} / {start.scenario} | "
            f"{money(start.value, start.currency)} | "
            f"{money(end.value, end.currency)} | "
            f"{money(change.absolute_change, end.currency)} | {pct} | "
            f"{change.change_driver} | "
            f"{money(change.unexplained, end.currency)} |"
        )
    if summary.non_comparable:
        print("\n## Kept separate\n")
        for item in summary.non_comparable:
            print(f"- {item}")
    if summary.gaps:
        print("\n## Gaps\n")
        for item in summary.gaps:
            print(f"- {item}")
    return 0


def metric(args: argparse.Namespace) -> int:
    history = T.load_history(args.snapshots)
    series = history.series(
        args.metric_id, clock=args.clock, scenario=args.scenario,
        entity_id=args.entity_id)
    print(f"# {args.metric_id}\n")
    print("| Date | Value | Source | Model |")
    print("|---|---:|---|---|")
    for point in series.observations:
        print(
            f"| {point.effective_date} | "
            f"{money(point.value, point.currency) if point.value is not None else 'unknown'} | "
            f"{point.source} | {point.model_version or 'observed'} |"
        )
    return 0


def restate(args: argparse.Namespace) -> int:
    source = T.load_snapshot(args.snapshot)
    candidates = [m for m in source.observations
                  if m.metric_id == args.metric_id
                  and m.entity_id == args.entity_id]
    if len(candidates) != 1:
        raise T.HistoryError(
            f"expected one observed point, found {len(candidates)}; specify --entity-id"
        )
    corrected = None if args.unknown_reason else args.value
    if corrected is None and not args.unknown_reason:
        raise T.HistoryError("supply --value or --unknown-reason")
    result = T.create_restatement(
        snapshot_id=args.snapshot_id,
        original_snapshot_id=source.snapshot_id,
        original=candidates[0],
        corrected_value=corrected,
        unknown_reason=args.unknown_reason,
        reason=args.reason,
        corrected_at=args.corrected_at,
    )
    T.save_snapshot(result, args.output)
    print(f"saved restatement {result.snapshot_id} to {args.output}")
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    cap = sub.add_parser("capture", help="capture facts explicitly")
    cap.add_argument("--facts", required=True)
    cap.add_argument("--output", required=True)
    cap.add_argument("--snapshot-id", required=True)
    cap.add_argument("--effective-date", required=True, type=date)
    cap.add_argument("--observed-at", required=True, type=date)
    cap.add_argument("--completeness", choices=("complete", "partial"),
                     default="complete")
    cap.set_defaults(function=capture)

    calc = sub.add_parser("calculate", aliases=["rerun"],
                          help="save current-model results for a retained snapshot")
    calc.add_argument("--snapshot", required=True)
    calc.add_argument("--output", required=True)
    calc.add_argument("--snapshot-id", required=True)
    calc.add_argument("--calculated-at", required=True, type=date)
    calc.add_argument("--skills-dir", type=Path, default=ROOT / "skills")
    calc.set_defaults(function=analyze)

    comp = sub.add_parser("compare", help="compare two or more snapshot files")
    comp.add_argument("snapshots", nargs="+")
    comp.add_argument("--metric", action="append")
    comp.set_defaults(function=compare)

    one = sub.add_parser("metric", help="show one compatible series")
    one.add_argument("metric_id")
    one.add_argument("snapshots", nargs="+")
    one.add_argument("--clock", choices=T.CLOCKS, required=True)
    one.add_argument("--scenario", required=True)
    one.add_argument("--entity-id")
    one.set_defaults(function=metric)

    fix = sub.add_parser("restate", help="write a separate correction document")
    fix.add_argument("--snapshot", required=True)
    fix.add_argument("--output", required=True)
    fix.add_argument("--snapshot-id", required=True)
    fix.add_argument("--metric-id", required=True)
    fix.add_argument("--entity-id")
    fix.add_argument("--value", type=float)
    fix.add_argument("--unknown-reason")
    fix.add_argument("--reason", required=True)
    fix.add_argument("--corrected-at", required=True, type=date)
    fix.set_defaults(function=restate)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.function(args)
    except (F.FactsError, T.HistoryError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
