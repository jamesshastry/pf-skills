"""Shared entry point for skill runners.

Extracted at the third consumer, per ROADMAP.md. Every skill runner does the
same four things before it can say anything useful: parse --facts, load it,
check its required paths, and stop cleanly if they are missing. Only the
rendering differs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / "lib") not in sys.path:
    sys.path.insert(0, str(_ROOT / "lib"))

from pf import facts as F  # noqa: E402


class Writer:
    """Accumulates markdown lines. `w("text")` reads better than list.append."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, text: str = "") -> None:
        self.lines.append(text)

    def table(self, header: list[str], rows: list[list[str]]) -> None:
        self("| " + " | ".join(header) + " |")
        self("|" + "---|" * len(header))
        for r in rows:
            self("| " + " | ".join(str(c) for c in r) + " |")

    def render(self) -> str:
        return "\n".join(self.lines)


def run(
    *,
    title: str,
    required: list[str],
    build: Callable[[dict, Writer], None],
    missing_hint: str = "See SCHEMA.md. Fill these in rather than letting the skill guess.",
    argv: list[str] | None = None,
) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--facts", required=True)
    args = ap.parse_args(argv)

    try:
        data = F.load(args.facts)
    except F.FactsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    w = Writer()
    w(f"# {title}")
    w()

    pre = F.require(data, required)
    if not pre.ok:
        w("## Stopped — missing required facts")
        w()
        for m in pre.missing:
            w(f"- `{m}`")
        w()
        w(missing_hint)
        print(w.render())
        return 1

    build(data, w)
    print(w.render())
    return 0


def money(x) -> str:
    if x is None:
        return "none"
    if isinstance(x, str):
        return x
    return f"${x:,.0f}"


def disclaimer(w: Writer, module: str, extra: str = "") -> None:
    w()
    w("---")
    w()
    w(
        f"*Not financial, tax, or legal advice. Thresholds are in `{module}` "
        f"with their reasons; every figure above is derived, not restated."
        + (f" {extra}" if extra else "")
        + "*"
    )
