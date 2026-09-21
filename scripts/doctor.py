#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Is this checkout set up correctly, and is the facts file usable?

    uv run scripts/doctor.py

Every check either passes, warns, or fails, and every failure says what to run
next. Written because the alternative first-run experience is a traceback from
whichever skill the newcomer happened to try first.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OK, WARN, FAIL = "  ok  ", " warn ", " FAIL "
_results: list[tuple[str, str, str]] = []


def check(status: str, name: str, detail: str = "") -> None:
    _results.append((status, name, detail))


def _run(*cmd: str) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 127, ""


def environment() -> None:
    v = sys.version_info
    if v >= (3, 10):
        check(OK, "python", f"{v.major}.{v.minor}.{v.micro}")
    else:
        check(FAIL, "python", f"{v.major}.{v.minor} — skills need 3.10+")

    rc, out = _run("uv", "--version")
    if rc == 0:
        check(OK, "uv", out.split()[1] if len(out.split()) > 1 else out)
    else:
        check(WARN, "uv", "not found — install from astral.sh/uv. Skills carry "
                          "PEP 723 metadata so `uv run` needs nothing "
                          "preinstalled; without it you must manage deps.")


def privacy_guards() -> None:
    gi = (ROOT / ".gitignore")
    txt = gi.read_text() if gi.exists() else ""
    for rule, what in (("inputs/*", "facts and source documents"),
                       ("documents/*", "legacy statement drop zone"),
                       ("outputs/*", "generated reports"),
                       ("history/*", "historical facts and analyses"),
                       ("prompts/*", "private task prompts and briefs")):
        if rule in txt:
            check(OK, f"gitignore {rule}", what)
        else:
            check(FAIL, f"gitignore {rule}", f"{what} are NOT ignored")

    rc, _ = _run("git", "-C", str(ROOT), "rev-parse", "--git-dir")
    if rc != 0:
        check(WARN, "git", "not a git repo — the commit guards do not apply")
        return

    hook = ROOT / ".git" / "hooks" / "pre-commit"
    if hook.exists():
        check(OK, "pre-commit hook", "installed")
    else:
        check(WARN, "pre-commit hook", "not installed — run `pre-commit "
                                       "install`. .gitignore still applies; "
                                       "this is the second guard, for `git "
                                       "add -f` and typo'd ignore rules.")

    # The check that matters most: has anything private already been staged?
    rc, out = _run(
        "git", "-C", str(ROOT), "ls-files", "inputs/", "documents/",
        "outputs/", "history/", "prompts/"
    )
    allowed = {
        "inputs/README.md", "documents/README.md", "outputs/README.md",
        "outputs/.gitkeep", "history/.gitkeep", "prompts/README.md",
    }

    def public_scaffold(path: str) -> bool:
        parts = Path(path).parts
        return (
            path in allowed
            or (len(parts) == 2 and parts[0] == "inputs"
                and parts[1].endswith(".example.yml"))
            or (len(parts) == 3 and parts[0] in ("inputs", "outputs")
                and parts[2] == ".gitignore")
        )

    tracked = [f for f in out.splitlines() if f and not public_scaffold(f)]
    _, all_tracked = _run("git", "-C", str(ROOT), "ls-files")
    tracked.extend(
        f for f in all_tracked.splitlines()
        if "/" not in f and f.endswith(("-prompt.md", "-brief.md"))
    )
    if tracked:
        check(FAIL, "tracked private files",
              "IN GIT: " + ", ".join(tracked[:5]))
    else:
        check(OK, "tracked private files", "none")


def facts() -> None:
    path = ROOT / "inputs" / "facts.yml"
    if not path.exists():
        check(WARN, "facts file", "none yet — run `uv run scripts/init_facts.py`")
        return
    try:
        import yaml
        data = yaml.safe_load(path.read_text()) or {}
    except Exception as e:                       # noqa: BLE001
        check(FAIL, "facts file", f"does not parse: {type(e).__name__}: {e}")
        return
    check(OK, "facts file", "parses")

    meta = data.get("meta") or {}
    if meta.get("schema_version") == 1:
        check(OK, "schema_version", "1")
    else:
        check(WARN, "schema_version", f"{meta.get('schema_version')!r} — expected 1")

    if (meta.get("jurisdiction") or {}).get("state"):
        check(OK, "jurisdiction.state", str(meta["jurisdiction"]["state"]))
    else:
        check(FAIL, "jurisdiction.state", "unset — required, and has no "
                                          "default. State rules change "
                                          "conclusions.")

    as_of = meta.get("as_of")
    if as_of:
        import datetime as dt
        try:
            d = (as_of if isinstance(as_of, dt.date)
                 else dt.date.fromisoformat(str(as_of)))
            age = (dt.date.today() - d).days
            check(OK if age <= 400 else WARN, "meta.as_of",
                  f"{d} ({age} days old)"
                  + ("" if age <= 400 else " — over a year; figures may be stale"))
        except ValueError:
            check(WARN, "meta.as_of", f"{as_of!r} is not an ISO date")
    else:
        check(WARN, "meta.as_of", "unset — staleness cannot be reported")


def coverage() -> None:
    """How many skills can run. The number a newcomer actually wants."""
    sys.path.insert(0, str(ROOT / "lib"))
    try:
        from pf import intake as I
        sys.path.insert(0, str(ROOT / "skills" / "document-intake"))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_intake_runner", ROOT / "skills" / "document-intake" / "run.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)          # type: ignore[union-attr]
        data, _ = mod.load_facts(None)
        rep = I.assess(data, mod.requirements(), [])
        n, total = len(rep.runnable), rep.total_skills
        check(OK if n else WARN, "skills runnable", f"{n} of {total}")
    except Exception as e:                       # noqa: BLE001
        check(WARN, "skills runnable", f"could not determine: {e}")


def main() -> int:
    environment()
    privacy_guards()
    facts()
    coverage()

    print("\npf-skills doctor\n" + "─" * 60)
    for status, name, detail in _results:
        print(f"[{status}] {name:<24} {detail}")
    fails = sum(1 for s, _, _ in _results if s == FAIL)
    warns = sum(1 for s, _, _ in _results if s == WARN)
    print("─" * 60)
    if fails:
        print(f"{fails} failure(s), {warns} warning(s). Fix the failures first.")
    elif warns:
        print(f"No failures, {warns} warning(s). Usable.")
    else:
        print("All checks passed.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
