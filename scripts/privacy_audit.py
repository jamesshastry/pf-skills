#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Has anything private reached the public part of this repository?

    uv run scripts/privacy_audit.py
    uv run scripts/privacy_audit.py --from ../my-private-repo/data/facts.yml

## Two passes, because two different things go wrong

**Pattern pass** — searches tracked files for things that are private by shape:
emails, SSNs, street addresses, long digit runs. Finds what you did not mean to
type.

**Token pass** — takes your *actual* values (from a private facts file, or from
a local `.privacy-tokens.local`) and searches for each one. Finds what you did
mean to type, somewhere you did not mean to type it. This is the pass that
matters, and it is the one gitleaks cannot do: gitleaks knows what a secret
looks like, not what your kids are called.

## It searches history, not just the working tree

A value removed in a later commit is still published the moment the repository
is. `git log -S` is the check, and it is the reason to run this **before** the
first push rather than after.

## The strongest finding is usually not a figure

A profile — nationality, immigration status, metro area, approximate net worth,
employer type — identifies a household as surely as a name, and reads as
harmless prose. Patterns will not catch it and neither will tokens. Read your
own documentation asking "could a stranger recognise someone from this?"
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL_TOKENS = ROOT / ".privacy-tokens.local"

#: Private by shape. Deliberately narrow — a noisy audit gets ignored, which is
#: worse than no audit because it feels like diligence.
PATTERNS: dict[str, re.Pattern] = {
    "email":          re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"),
    "ssn":            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "street address": re.compile(r"\b\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+"
                                 r"(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|"
                                 r"Boulevard|Blvd|Way|Court|Ct|Circle|Cir)\b"),
    "long digit run": re.compile(r"(?<![\d.])\d{9,}(?![\d.])"),
    "phone":          re.compile(r"\b\(\d{3}\)\s*\d{3}-\d{4}\b|\b\d{3}-\d{3}-\d{4}\b"),
}

#: Paths whose matches are expected. Test fixtures and the schema are meant to
#: contain example-shaped values.
ALLOW = ("tests/", "inputs/facts.example.yml", ".gitleaks.toml",
         "scripts/privacy_audit.py")

#: Words that are private-looking but are ordinary vocabulary here. Without
#: this the token pass returns 200 hits on "cash" and nobody reads any of them.
STOPWORDS = {
    "cash", "spouse", "primary", "dependent", "estimate", "liquid", "trust",
    "equity", "bank", "term", "partial", "meta", "education", "property",
    "renters", "illiquid", "pool", "contingent", "estate", "other", "single",
    "married_joint", "none", "true", "false", "null", "usd", "self", "annual",
}


def git(*args: str) -> str:
    p = subprocess.run(("git", "-C", str(ROOT), *args),
                       capture_output=True, text=True)
    return p.stdout


def repository_files() -> list[str]:
    """Tracked and non-ignored untracked files in the public worktree.

    A privacy audit run before staging is the valuable one. Scanning only
    ``git ls-files`` gave every newly created report, fixture, and skill a
    blind window until it entered the index.
    """
    return [
        f for f in git(
            "ls-files", "--cached", "--others", "--exclude-standard"
        ).split("\n") if f
    ]


def pattern_pass() -> list[tuple[str, str, str, str]]:
    hits = []
    for f in repository_files():
        if any(f.startswith(a) or f == a for a in ALLOW):
            continue
        try:
            text = (ROOT / f).read_text()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, pat in PATTERNS.items():
                m = pat.search(line)
                if m:
                    hits.append((label, f, str(lineno), m.group(0)))
    return hits


def collect_tokens(facts_path: Path | None) -> set[str]:
    toks: set[str] = set()
    if LOCAL_TOKENS.exists():
        toks |= {t.strip() for t in LOCAL_TOKENS.read_text().splitlines()
                 if t.strip() and not t.startswith("#")}
    if facts_path and facts_path.exists():
        import yaml

        def walk(o):
            if isinstance(o, dict):
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
            elif isinstance(o, str):
                s = o.strip()
                # Multi-word strings and identifiers; skip bare enum values.
                if len(s) >= 5 and not re.fullmatch(r"[\d\-.:/ ]+", s):
                    toks.add(s)
            elif isinstance(o, bool):
                pass
            elif isinstance(o, (int, float)) and abs(o) >= 10_000:
                # Round numbers collide with schema examples constantly.
                if int(o) % 1000 != 0:
                    toks.add(str(int(o)))
        walk(yaml.safe_load(facts_path.read_text()))
    return {t for t in toks if t.lower() not in STOPWORDS and len(t) >= 5}


_IDENTITY = (
    re.compile(r"\b[A-Z][a-z]{2,}\b.*\b[A-Z][a-z]{2,}\b"),   # two proper nouns
    re.compile(r"(?<![\d.])\d{5,}(?![\d.])"),                # account/policy no.
    re.compile(r"@"),
)


def _vocabulary(token: str, public: str) -> bool:
    """Whether a token is schema vocabulary rather than someone's identity.

    `after_tax`, `revocable_trust` and `nonimmigrant_visa` appear in a real
    facts file *and* in SCHEMA.md, because the schema defines them. Reporting
    them is not a false positive in the sense of a bug — the token really is in
    both places — but it is useless, and eighteen useless rows is how an audit
    stops being read.

    The exception is anything identity-shaped. A name or an account number that
    somehow reached the schema or the example fixture is a finding *because* it
    is there, so those are never suppressed.
    """
    if any(p.search(token) for p in _IDENTITY):
        return False
    return token in public


def token_pass(tokens: set[str], quiet: bool = True) -> list[tuple[str, list[str], int]]:
    """Each token, where it appears now, and in how many past commits."""
    hits = []
    public = ""
    for f in ("SCHEMA.md", "inputs/facts.example.yml"):
        p = ROOT / f
        if p.exists():
            public += p.read_text()
    blobs = {}
    for f in repository_files():
        try:
            blobs[f] = (ROOT / f).read_text()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    suppressed = 0
    for t in sorted(tokens):
        where = [f for f, b in blobs.items() if t in b]
        history = len([c for c in git("log", "--all", "-S", t, "--oneline").split("\n") if c])
        if not (where or history):
            continue
        if quiet and _vocabulary(t, public):
            suppressed += 1
            continue
        hits.append((t, where, history))
    token_pass.suppressed = suppressed          # type: ignore[attr-defined]
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="include tokens that are schema vocabulary "
                         "(after_tax, revocable_trust, ...) rather than identity")
    ap.add_argument("--from", dest="facts", type=Path, default=None,
                    help="a PRIVATE facts file to draw real values from. "
                         "Read only; never copied into this repo.")
    a = ap.parse_args()

    print("privacy audit\n" + "=" * 62)

    pat = pattern_pass()
    print(f"\n1. Pattern pass — {len(pat)} hit(s) in public worktree files "
          f"(fixtures and SCHEMA excluded)")
    for label, f, line, text in pat[:40]:
        print(f"   {label:<15} {f}:{line}  {text[:48]}")
    if not pat:
        print("   clean")

    tokens = collect_tokens(a.facts)
    if not tokens:
        print("\n2. Token pass — SKIPPED. No private values supplied.")
        print(f"   Pass --from <private facts file>, or write one token per "
              f"line into\n   {LOCAL_TOKENS.name} (gitignored).")
        print("\n   This is the pass that finds real leaks. A pattern scan "
              "alone\n   cannot tell that a street name is yours.")
    else:
        tok = token_pass(tokens, quiet=not a.all)
        skipped = getattr(token_pass, "suppressed", 0)
        print(f"\n2. Token pass — {len(tokens)} private value(s) checked, "
              f"{len(tok)} found in this repo"
              + (f" ({skipped} schema-vocabulary hit(s) suppressed; --all to "
                 f"show)" if skipped else ""))
        for t, where, history in tok[:40]:
            loc = ", ".join(where[:3]) or "—"
            print(f"   {t[:34]!r:<38} tree: {loc}"
                  + (f"   history: {history} commit(s)" if history else ""))
        if not tok:
            print("   clean — no private value appears in the tree or history")

    print("\n3. Prose pass — NOT AUTOMATED")
    print("   Read README.md, ROADMAP.md and any review document asking:")
    print("   could a stranger identify a household from this? Nationality,")
    print("   immigration status, metro area, employer type and approximate")
    print("   net worth identify a person as surely as a name, and no")
    print("   pattern or token scan will ever flag them.")

    print("\n" + "=" * 62)
    bad = len(pat) + (len(tok) if tokens else 0)
    if bad:
        print(f"{bad} item(s) to review. A hit is not automatically a leak — "
              f"read each one.")
        return 1
    print("Automated passes clean. The prose pass is still yours to do.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
