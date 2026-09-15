"""Harness for testing the skills themselves, rather than the arithmetic.

`lib/` is well covered by unit tests. The skills were not covered at all: a
`SKILL.md` could declare inputs its runner never checks, a runner could crash
instead of stopping cleanly, and a report could silently change shape. All of
those are invisible to a test suite that only exercises `pf.*`.

This module provides the discovery and execution plumbing; the assertions live
in `test_skill_*.py`.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
EXAMPLE_FACTS = ROOT / "inputs" / "facts.example.yml"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

#: Skills that take no `--facts`, for two different reasons.
#:
#: `reference-data-refresh` inspects the repository's own reference tables
#: rather than a household, so its output legitimately depends on today's date.
#:
#: `document-intake` runs *before* a facts file exists — it is the one skill
#: that produces facts rather than consuming them. Its input is whatever the
#: household dropped in `documents/`, which is gitignored and different for
#: everyone, so it can have no golden fixture either.
#:
#: Both are excluded from the contract checks that assume a household skill:
#: declared `requires`, resolvable paths, and a golden.
FACTS_FREE = {"reference-data-refresh", "document-intake"}

#: A date anywhere in output is normalised before golden comparison so a
#: report that legitimately prints "as of" does not churn the fixtures.
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass
class Skill:
    name: str
    dir: Path

    @property
    def skill_md(self) -> Path:
        return self.dir / "SKILL.md"

    @property
    def runner(self) -> Path:
        return self.dir / "run.py"

    @property
    def facts_free(self) -> bool:
        return self.name in FACTS_FREE

    # ── frontmatter ─────────────────────────────────────────────────────

    def frontmatter(self) -> dict:
        """Parse the YAML frontmatter without requiring PyYAML.

        Deliberately a small hand parser: the frontmatter here is a flat
        mapping plus one list, and depending on PyYAML would mean the contract
        test cannot run in a bare environment.
        """
        text = self.skill_md.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise AssertionError(f"{self.name}: SKILL.md has no frontmatter")
        end = text.index("\n---\n", 3)
        block = text[4:end]

        out: dict = {}
        key = None
        for raw in block.splitlines():
            if not raw.strip():
                continue
            if raw.startswith("  - "):
                if key is None:
                    raise AssertionError(f"{self.name}: list item before any key")
                out.setdefault(key, []).append(raw[4:].strip())
                continue
            if ":" not in raw:
                # A wrapped continuation of the previous scalar.
                if key and isinstance(out.get(key), str):
                    out[key] = out[key] + " " + raw.strip()
                continue
            key, _, value = raw.partition(":")
            key = key.strip()
            value = value.strip()
            out[key] = value if value else []
        return out

    def body(self) -> str:
        text = self.skill_md.read_text(encoding="utf-8")
        end = text.index("\n---\n", 3)
        return text[end + 5:]

    # ── the runner's own declared requirements ──────────────────────────

    def runner_required(self) -> list[str] | None:
        """Extract the REQUIRED list from run.py by reading the source.

        Reading rather than importing: importing would execute module-level
        `sys.path` surgery and pull in optional dependencies, and this test
        needs to work on a runner that is broken.
        """
        src = self.runner.read_text(encoding="utf-8")
        m = re.search(r"^REQUIRED\s*=\s*(\[[^\]]*\])", src, re.M | re.S)
        if not m:
            return None
        items = re.findall(r'"([^"]+)"', m.group(1))
        return items

    def has_pep723_header(self) -> bool:
        src = self.runner.read_text(encoding="utf-8")
        return "# /// script" in src and "# ///" in src


def discover() -> list[Skill]:
    out = [Skill(p.name, p) for p in sorted(SKILLS_DIR.iterdir())
           if p.is_dir() and not p.name.startswith(".")]
    if not out:
        raise AssertionError("no skills discovered — harness is misconfigured")
    return out


# ── execution ───────────────────────────────────────────────────────────────


@dataclass
class Run:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_skill(skill: Skill, facts: Path | None = None, timeout: int = 120) -> Run:
    cmd = [sys.executable, str(skill.runner)]
    if not skill.facts_free:
        cmd += ["--facts", str(facts or EXAMPLE_FACTS)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       cwd=str(ROOT))
    return Run(p.returncode, p.stdout, p.stderr)


def normalise(text: str) -> str:
    """Strip anything that legitimately varies between runs."""
    return _ISO_DATE.sub("<DATE>", text)


# ── fixtures for the stop-cleanly path ──────────────────────────────────────

MINIMAL_FACTS = {"meta": {"schema_version": 1, "as_of": "2026-08-30",
                          "currency": "USD",
                          "jurisdiction": {"country": "US", "state": "TX"}}}


def write_minimal(tmp_path: Path) -> Path:
    """A valid but nearly empty facts file.

    Every household skill must respond to this by listing what it needs and
    exiting 1 — never by crashing, and never by inventing a default.
    """
    p = tmp_path / "minimal.json"
    p.write_text(json.dumps(MINIMAL_FACTS), encoding="utf-8")
    return p


def write_bad_version(tmp_path: Path) -> Path:
    p = tmp_path / "badversion.json"
    p.write_text(json.dumps({"meta": {"schema_version": 99}}), encoding="utf-8")
    return p
