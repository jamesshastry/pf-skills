#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Render comparable local history from immutable structured snapshots."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, timeseries as T  # noqa: E402

REQUIRED = ["history.snapshot_files"]


def _value(point: T.MetricObservation, value: float | None = None) -> str:
    number = point.value if value is None else value
    if number is None:
        return "**unknown**"
    if point.unit == "currency":
        return f"{point.currency} {number:,.0f}"
    if point.unit in ("ratio", "percent"):
        return f"{number:.1%}"
    return f"{number:,.1f} {point.unit}"


def build(data: dict, w: cli.Writer) -> None:
    cfg = F._dig(data, "history") or {}
    paths = [Path(path) for path in cfg.get("snapshot_files") or []]
    history = T.load_history(paths)
    selected = set(cfg.get("selected_metrics") or []) or None
    summary = T.summarize_history(history, metric_ids=selected)

    w("**Observed facts, historical analyses, and projections remain three "
      "separate clocks.** No row below combines them.")
    w()
    w("## Material comparable changes")
    w()
    if summary.changes:
        w.table(
            ["Metric", "Clock / case", "Beginning", "Ending", "Change", "%",
             "Driver", "Unexplained"],
            [[f"`{c.start.metric_id}`",
              f"{c.start.clock} / {c.start.scenario}",
              _value(c.start), _value(c.end), _value(c.end, c.absolute_change),
              "—" if c.percentage_change is None else f"{c.percentage_change:.1%}",
              c.change_driver, _value(c.end, c.unexplained)]
             for c in summary.changes],
        )
    else:
        w("No selected series has two known comparable points.")

    w()
    w("## Period tables")
    for series in summary.series:
        first = series.observations[0]
        w()
        entity = f" · `{first.entity_id}`" if first.entity_id else ""
        w(f"### `{first.metric_id}` · {first.clock} / {first.scenario}{entity}")
        w()
        w.table(
            ["Effective", "Calculated", "Value", "Source", "Model"],
            [[point.effective_date.isoformat(),
              point.calculated_at.isoformat() if point.calculated_at else "—",
              _value(point), point.source, point.model_version or "observed"]
             for point in series.observations],
        )

    w()
    w("## Finding transitions")
    w()
    transitions = [(old, new) for old, new in summary.finding_changes if old is not None]
    if transitions:
        w.table(
            ["Finding", "From", "To", "Driver", "Reason"],
            [[f"`{new.finding_id}`", old.state, new.state,
              ("**methodology**" if old.inputs_fingerprint == new.inputs_fingerprint
               and old.model_version != new.model_version else new.change_driver),
              new.transition_reason or "not recorded"]
             for old, new in transitions],
        )
    else:
        w("No finding changed state in the selected history.")

    if summary.non_comparable:
        w()
        w("## Deliberately kept separate")
        w()
        for item in summary.non_comparable:
            w(f"- {item}")
    if summary.gaps:
        w()
        w("## Data gaps")
        w()
        for item in summary.gaps:
            w(f"- {item}")
    w()
    w("Changes without recorded flows remain unexplained residuals. No partial "
      "period was annualized and no missing date was carried forward.")
    cli.disclaimer(w, "lib/pf/timeseries.py")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Financial history review",
                             required=REQUIRED, build=build))
