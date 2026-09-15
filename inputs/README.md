# inputs/

**`facts.example.yml`** — a synthetic household. Committed. Every figure is invented.

**`facts.yml`** — yours. Gitignored. Never committed, never transmitted.

```bash
cp inputs/facts.example.yml inputs/facts.yml
```

Then replace the values, keeping the field names. See [`../SCHEMA.md`](../SCHEMA.md).

---

Two guards keep real data out of git: the `inputs/*` rule in `.gitignore`, and a pre-commit
hook that blocks any non-example file staged from this directory. Both exist because
`git add -f` is one keystroke away and a mistyped ignore rule fails silently.

If you keep several scenarios, name them anything except `*.example.yml`:

```
facts.yml
facts.2027-projection.yml
facts.spouse-returns-to-work.yml
```

All are ignored.
