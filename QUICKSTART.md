# Quickstart

From nothing to your first report. About ten minutes, most of it typing your
own numbers.

**Everything runs on your machine.** No account, no key, no network call. The
skills read a file you own and print markdown to your terminal.

---

## 1. Get it

```bash
git clone <this-repo> pf-skills && cd pf-skills
```

You need [`uv`](https://docs.astral.sh/uv/) and Python 3.10+. Every skill
carries [PEP 723](https://peps.python.org/pep-0723/) inline metadata, so
`uv run` fetches what a skill needs by itself — there is no install step and no
virtualenv to activate.

```bash
uv run scripts/doctor.py
```

That checks your environment and the privacy guards, and tells you what is
missing. Run it again any time something behaves oddly.

## 2. Turn on the commit guards

Only if you plan to commit anything back. Skip otherwise — `.gitignore`
already protects you.

```bash
uv run --with pre-commit pre-commit install
```

Two guards keep real data out of git: the ignore rules, and a hook that blocks
any non-example file staged from `inputs/`. Both exist because `git add -f` is
one keystroke away and a mistyped ignore rule fails silently.

## 3. Make a facts file

```bash
uv run scripts/init_facts.py
```

This writes `inputs/facts.yml` as a **skeleton of nulls**.

Do not copy the example household instead. `cp inputs/facts.example.yml
inputs/facts.yml` is one command and it is the wrong first move: every field
you never get to still holds an invented figure, and a skill cannot tell the
difference between a number you entered and one the Riveras came with. A null
fails loudly; an invented number produces a confident report.

Fill in `household.members` and `meta.jurisdiction.state` first. That is about
four lines of YAML and it unblocks roughly thirty of the fifty-three skills.

## 4. Add your documents

```bash
cp ~/Downloads/*.pdf documents/
uv run skills/document-intake/run.py
```

Anything, any format, any filename. Nothing in `documents/` is committed and
nothing is uploaded.

The report tells you which fields are still unset, **which of them block the
most skills**, and which document probably answers each. Work that list from
the top — it is ordered by what the next hour buys you.

Nothing in there is parsed. Filenames are matched against schema areas as a
hint for whoever reads them.

## 5. Run a skill

```bash
uv run skills/emergency-fund-sizing/run.py --facts inputs/facts.yml
```

`emergency-fund-sizing` is a good first one: it needs three fields and its
answer is easy to sanity-check against what you already believe.

A skill missing a field **stops and names it**. That is the designed behaviour,
not an error to work around.

```bash
# Save a report
uv run skills/auto-insurance-review/run.py --facts inputs/facts.yml \
  > outputs/auto-2026.md
```

## 6. Check the edges

```bash
uv run skills/conflict-check/run.py --facts inputs/facts.yml
```

Every skill is individually correct. Some of them give the same household
**opposite instructions** — filling low tax brackets with Roth conversions
raises the MAGI that premium subsidies taper against, and both pieces of advice
are right. Nothing in a single report would tell you.

---

## Using this with an agent

The skills are written to be read by an agent as much as by you. The intended
loop:

1. You put documents in `documents/`
2. The agent runs `document-intake` and reads the files
3. The agent **proposes** values; **you** confirm them into `inputs/facts.yml`
4. The agent runs the relevant skills and explains the reports

**Keep step 3.** Every skill treats a recorded figure as established fact and
builds a confident recommendation on it. A misread statement does not stay a
misread statement — it becomes a conclusion several reports away from the page
it came from, with nothing marking it as uncertain.

To install them as agent skills:

```bash
ln -s "$PWD/skills" ~/.claude/skills/pf-skills
```

---

## Before you push anything

If you fork this and commit your own work:

```bash
uv run scripts/privacy_audit.py --from inputs/facts.yml
```

Two automated passes — things private by *shape* (emails, addresses, account
numbers) and your *actual values*, searched across the working tree **and the
full git history**. A value deleted in a later commit is still published the
moment the repository is.

The third pass is not automated and is usually the one that matters. Read your
own prose asking: **could a stranger identify a household from this?**
Nationality, immigration status, metro area, employer type and approximate net
worth identify a person as surely as a name, and no scanner will ever flag
them. This repository has had exactly that defect, found by reading rather than
by grepping.

---

## Where to look next

| File | What it is |
|---|---|
| `README.md` | Every skill, one line each |
| `SCHEMA.md` | The facts contract — every field, and why it exists |
| `documents/README.md` | What documents are worth having |
| `CONTRIBUTING.md` | House style, if you want to add a skill |
| `ROADMAP.md` | What is built, what is not, and what was rejected |
| `REVIEW.md` | The standing list of what is wrong with this |

*Not financial, tax, or legal advice.*
