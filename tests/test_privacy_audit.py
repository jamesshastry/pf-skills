"""Privacy audit coverage of the complete public worktree."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "privacy_audit.py"
SPEC = importlib.util.spec_from_file_location("privacy_audit", SCRIPT)
privacy_audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(privacy_audit)


def test_repository_files_include_nonignored_untracked_files(monkeypatch):
    calls = []

    def fake_git(*args):
        calls.append(args)
        return "tracked.py\nnew-skill/SKILL.md\n"

    monkeypatch.setattr(privacy_audit, "git", fake_git)
    assert privacy_audit.repository_files() == [
        "tracked.py", "new-skill/SKILL.md"]
    assert calls == [
        ("ls-files", "--cached", "--others", "--exclude-standard")]
