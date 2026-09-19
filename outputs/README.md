# outputs/

Generated files are grouped by purpose rather than mirroring the source-input
categories. The directories are committed as scaffolding; every generated file
inside them is gitignored because reports contain derived private financial
information.

```text
outputs/
├── reports/      current-state skill and household reports
├── history/      rendered comparisons of retained snapshots
├── scenarios/    deterministic what-if and stress-test reports
└── structured/   machine-readable JSON metrics and findings
```

`outputs/history/` contains rendered comparisons. The root `history/`
directory contains the immutable source snapshots themselves; keep that
distinction intact.

Save ordinary Markdown with shell redirection:

```bash
uv run skills/auto-insurance-review/run.py --facts inputs/facts.yml \
  > outputs/reports/auto-2026.md
```

History-enabled skills can additionally write machine-readable JSON:

```bash
uv run skills/emergency-fund-sizing/run.py --facts inputs/facts.yml \
  --structured-output outputs/structured/emergency-fund-2026.json \
  > outputs/reports/emergency-fund-2026.md
```

Runners refuse to overwrite structured output. Shell redirection does not, so
check the destination before reusing a Markdown filename.
