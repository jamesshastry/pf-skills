#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""What is in documents/, what the schema still needs, and what to do next.

Takes no --facts by default: this runs *before* a facts file exists, and
reports usefully when there is nothing to read yet.

    uv run skills/document-intake/run.py
    uv run skills/document-intake/run.py --facts inputs/facts.yml
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, intake as I  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "documents"
SKILLS = ROOT / "skills"


def requirements() -> dict[str, list[str]]:
    """Each skill's declared inputs, read from its own SKILL.md.

    Kept as a thin wrapper: `scripts/doctor.py` calls `mod.requirements()`.
    The implementation lives in `lib/pf/intake.py`, shared with
    `household-review` — one copy for every consumer of the skill directory.
    """
    return I.skill_requirements(SKILLS, skip=I.FACTS_FREE)


def scan() -> list[I.Document]:
    if not DOCS.exists():
        return []
    return [I.classify(p.name, p.stat().st_size)
            for p in sorted(DOCS.rglob("*"))
            if p.is_file() and p.name not in (".gitkeep", "README.md")]


def load_facts(path: Path | None) -> tuple[dict, str]:
    if path is None:
        for c in (ROOT / "inputs" / "facts.yml",):
            if c.exists():
                path = c
                break
    if path is None or not path.exists():
        return {}, ""
    import yaml
    full = path.resolve()
    try:
        shown = str(full.relative_to(ROOT))
    except ValueError:          # a facts file kept outside the repo
        shown = str(full)
    return yaml.safe_load(full.read_text()) or {}, shown


def build(facts: dict, facts_path: str, docs: list[I.Document], w: cli.Writer) -> None:
    rep = I.assess(facts, requirements(), docs)

    # ── documents ───────────────────────────────────────────────────────
    w("## Documents")
    w()
    if not docs:
        w("**`documents/` is empty.** Drop statements, policies and prior "
          "returns in there — anything, any name, any format. Nothing in that "
          "directory is committed, and nothing leaves this machine.")
    else:
        named = [d for d in docs if I.looks_renamed_for_privacy(d.name)]
        w(f"**{len(docs)} file(s).** Filenames are matched against the schema "
          "areas they plausibly answer. A match is a hint for whoever reads "
          "them, never a value — nothing here is parsed.")
        w()
        w.table(["File", "Might answer"],
                [[f"`{d.name}`",
                  ", ".join(f"`{a}`" for a in d.suggests) or "— unrecognised"]
                 for d in docs])
        if named:
            w()
            w(f"> **{len(named)} filename(s) carry personal data**: "
              + ", ".join(f"`{d.name}`" for d in named[:5])
              + ". `documents/` is gitignored, so this never reaches git — but "
                "gitignore does not protect a screen share, a terminal "
                "recording or a support ticket. Renaming costs one `mv`.")

    # ── where the household stands ──────────────────────────────────────
    w()
    w("## What runs today")
    w()
    if not facts_path:
        w("**No facts file yet**, so every skill below is blocked on "
          "everything. Start with `scripts/init_facts.py`, which writes a "
          "skeleton of nulls rather than copying the example household — a "
          "copied fixture leaves invented figures in place, and an invented "
          "figure that survives into a report is the defect this repository "
          "is organised against.")
    else:
        w(f"Read from `{facts_path}`.")
    w()
    w(f"**{len(rep.runnable)} of {rep.total_skills} skills can run.**")

    if rep.runnable:
        w()
        w("<details><summary>Runnable now</summary>")
        w()
        for s in rep.runnable:
            w(f"- `{s}`")
        w()
        w("</details>")

    # ── the worklist ────────────────────────────────────────────────────
    near = rep.nearly_there
    if near:
        w()
        w("## Next hour")
        w()
        w("Skills blocked on one or two fields. This is where effort pays "
          "first — not because these skills matter most, but because the "
          "distance is shortest and finishing one tells you the shape is "
          "right before you transcribe forty more fields.")
        w()
        w.table(["Skill", "Waiting on"],
                [[f"`{g.skill}`", ", ".join(f"`{m}`" for m in g.missing)]
                 for g in near[:12]])

    if rep.blocking:
        w()
        w("## Fields by blast radius")
        w()
        w("One missing field usually blocks several skills. Ordered by how "
          "many, so the first rows buy the most.")
        w()
        rows = [[f"`{p}`", str(len(sk)), ", ".join(f"`{s}`" for s in sk[:4])
                 + (" …" if len(sk) > 4 else "")]
                for p, sk in rep.blocking[:20]]
        w.table(["Field", "Blocks", "Which skills"], rows)
        if len(rep.blocking) > 20:
            w()
            w(f"*…and {len(rep.blocking) - 20} more fields.*")

    # ── things no filename announces ────────────────────────────────────
    w()
    w("## Not on any statement")
    w()
    w("These are needed, and no document announces them. They are the usual "
      "reason an intake stalls at ninety percent.")
    w()
    for pathname, why in I.OFF_PAPER:
        w(f"- **`{pathname}`** — {why}")

    w()
    w("## How to use this with an agent")
    w()
    w("Put the documents in `documents/`, run this, and hand an agent the "
      "report together with the files. The report says which fields are "
      "open and which document probably answers each; the agent reads and "
      "proposes values; **you** confirm them into `inputs/facts.yml`.")
    w()
    w("Keep the confirmation step. Every skill downstream treats a recorded "
      "figure as established fact and will build a confident recommendation "
      "on it, so a misread statement does not stay a misread statement — it "
      "becomes a conclusion. `null` is always the safe answer: a skill that "
      "is missing a field stops and says so, which is the designed behaviour "
      "and not a failure.")
    cli.disclaimer(w, "lib/pf/intake.py")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--facts", type=Path, default=None,
                    help="facts file (default: inputs/facts.yml if it exists)")
    a = ap.parse_args()
    facts, path = load_facts(a.facts)
    w = cli.Writer()
    w("# Document intake")
    w()
    build(facts, path, scan(), w)
    print(w.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
