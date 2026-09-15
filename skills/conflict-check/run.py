#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Where two skills would give this household opposite instructions."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, conflicts as C  # noqa: E402

REQUIRED = ["household.members"]


def build(data: dict, w: cli.Writer) -> None:
    r = C.check(data)

    w("Every skill here is individually correct and each is tested in "
      "isolation. **Nothing tests the edges between them**, and some of those "
      "edges are contradictions — two pieces of correct advice that cannot "
      "both be followed.")
    w()
    w("A household running one skill sees confident advice and no hint the "
      "other exists. That is worse than either skill being wrong, because "
      "there is nothing on the page to be suspicious of.")
    w()
    if r.live:
        w(f"**{len(r.live)} conflict(s) live for this household**, involving "
          f"{len(r.skills_involved)} skills.")
    else:
        w("**No registered conflicts are live** on the facts recorded.")

    for c in r.live:
        w()
        w(f"## {' ⇄ '.join('`' + s + '`' for s in c.skills)}")
        w()
        w(f"**The tension.** {c.tension}")
        w()
        w(f"**When it bites.** {c.trigger}")
        w()
        w(f"**How to resolve it.** {c.resolution}")
        if c.quantified_by:
            w()
            w(f"> **Sized elsewhere.** `{c.quantified_by}` computes the "
              "overlap and, where the inputs allow, the cost. This entry says "
              "the conflict exists; that one says how much it is worth.")

    if r.dormant:
        w()
        w("## Registered but not live")
        w()
        w("These are real conflicts that this household's facts do not "
          "currently trigger. They are listed because facts change:")
        w()
        for c in r.dormant:
            w(f"- {' ⇄ '.join('`' + s + '`' for s in c.skills)} — {c.trigger}")

    aliases = [a for a in C.aliased(data) if a.serious]
    shapes = C.shape_warnings(data)
    if aliases or shapes:
        w()
        w("## One quantity, two keys")
        w()
        w("A different defect from the conflicts above, and a quieter one. "
          "These are not two pieces of advice in tension — they are **one "
          "real-world figure recorded under two names**, read by two modules "
          "that cannot see each other. Each report stays internally "
          "consistent, so there is nothing on either page to be suspicious "
          "of.")
        for a in aliases:
            w()
            w(f"**{a.concept}** — {a.status}. {a.detail}")
        for s in shapes:
            w()
            w(f"**Shape.** {s}")

    w()
    w("## What this is not")
    w()
    w("Not a list of bugs. A conflict here is **two correct answers that "
      "cannot both be acted on**, and the resolution is almost never \"one of "
      "them is wrong\" — it is a trade-off someone has to price. The "
      "registry's job is to make sure nobody prices it without knowing it is "
      "there.")
    w()
    w("It is also not complete. It holds the conflicts somebody has noticed "
      "and written down; the ones nobody has noticed are, by definition, not "
      "here. Adding a skill should include asking what it contradicts.")
    cli.disclaimer(w, "lib/pf/conflicts.py")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Cross-skill conflict check",
                             required=REQUIRED, build=build))
