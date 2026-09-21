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
private files staged from `inputs/`, `outputs/`, `history/`, or `prompts/`.
Both exist because `git add -f` is one keystroke away and a mistyped ignore
rule fails silently.

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
four lines of YAML and it unblocks roughly thirty of the sixty-five skills that
read a facts file.

## 4. Add your documents

```bash
cp ~/Downloads/checking.pdf inputs/banking/
cp ~/Downloads/brokerage.pdf inputs/investments/
cp ~/Downloads/auto-policy.pdf inputs/insurance/
uv run skills/document-intake/run.py
```

Anything, any format, any filename. The committed category scaffolds cover
banking, investments, retirement, insurance, income, debts, tax, property,
estate, education, healthcare, business, cross-border records, and life events.
Their contents are ignored and nothing is uploaded. The legacy flat
`documents/` directory is still scanned.

The report tells you which fields are still unset, **which of them block the
most skills**, and which document probably answers each. Work that list from
the top — it is ordered by what the next hour buys you.

Nothing in there is parsed. Filenames are matched against schema areas as a
hint for whoever reads them.

## 5. Rank the live issues

Once the confirmed facts support useful analysis, run the whole-household
review before choosing a specialist report:

```bash
uv run skills/household-review/run.py --facts inputs/facts.yml
```

It ranks expiring findings, uncovered losses, priced drags, and then
optimizations. It also lists blocked skills and the facts that would unlock
them. The report chooses the live starting point; it does not replace the
specialist reports that calculate each conclusion.

## 6. Follow the relevant skill chain

```bash
uv run skills/emergency-fund-sizing/run.py --facts inputs/facts.yml
```

`emergency-fund-sizing` is a good first one: it needs three fields and its
answer is easy to sanity-check against what you already believe.

A skill missing a field **stops and names it**. That is the designed behaviour,
not an error to work around.

Do not run the catalog from top to bottom. Follow the domain chain around the
issue selected by `household-review`. Common examples include:

- property reviews before `umbrella-liability`;
- survivor needs before life-insurance review, with disability reviewed as a
  related but independently sized income-replacement risk;
- allocation before rebalancing, then wash-sale and tax review before a taxable
  trade;
- retirement readiness before Social Security, withdrawal, Roth, healthcare,
  and tax decisions; and
- affordability and disclosures before `home-offer-strategy`, which evaluates
  supplied closed sales without fetching or inventing comparable data; and
- beneficiary, estate-document, probate, and digital-estate reviews before the
  operational `continuity-plan`.

The complete routing table is in [README.md](README.md#skill-chains).

```bash
# Save a report
uv run skills/auto-insurance-review/run.py --facts inputs/facts.yml \
  > outputs/reports/auto-2026.md
```

The first history-enabled skills can also write their metrics to a separate,
machine-readable file without changing the Markdown report:

```bash
uv run skills/emergency-fund-sizing/run.py --facts inputs/facts.yml \
  --structured-output outputs/structured/emergency-fund-2026.json
```

That file is written only when requested and is not a history snapshot. The
runner refuses to overwrite it.

## 7. Check the edges

```bash
uv run skills/conflict-check/run.py --facts inputs/facts.yml
```

Every skill is individually correct. Some of them give the same household
**opposite instructions** — filling low tax brackets with Roth conversions
raises the MAGI that premium subsidies taper against, and both pieces of advice
are right. Nothing in a single report would tell you.

Run this after the relevant specialist reports and again when a scenario would
activate a previously dormant conflict. Resolve the tradeoff before acting;
the conflict report deliberately does not choose for you.

## 8. Model a scenario before a material change *(when applicable)*

Record a reconciled baseline under `cash_flow.scenarios` and deterministic,
typed events under `scenario_planning.scenarios`; use the synthetic example for
shape, never for amounts. Then run the general or focused report:

```bash
uv run skills/financial-scenario-planner/run.py --facts inputs/facts.yml
uv run skills/job-loss-stress-test/run.py --facts inputs/facts.yml
uv run skills/windfall-deployment-planner/run.py --facts inputs/facts.yml
```

Use a scenario when a recommendation materially changes cash flow, liquidity,
debt, retirement timing, or the balance sheet. These reports do not assign
probabilities, fetch market data, execute an action, or write results back into
the facts file. See
[SCHEMA.md](SCHEMA.md#scenario_planning--deterministic-what-if-paths) for event
types, reconciliation rules, and same-month ordering.

## 9. Start a history only when you have a truthful observation *(optional)*

Do not reconstruct old balances from memory. Start with the first date you can
support, and distinguish when the facts were true from when you recorded them:

```bash
uv run scripts/history.py capture --facts inputs/facts.yml \
  --snapshot-id s2026-08-30 --effective-date 2026-08-30 \
  --observed-at 2026-08-31 --output history/2026-08-30.yml
uv run scripts/history.py calculate --snapshot history/2026-08-30.yml \
  --snapshot-id a2026-08-31 --calculated-at 2026-08-31 \
  --output history/2026-08-30.analysis.yml
```

Capture refuses to overwrite a file. Corrections are separate restatement
documents; the original remains intact. After a second capture, compare them:

```bash
uv run scripts/history.py compare \
  history/2026-08-30.yml history/2026-11-30.yml
```

Add the files you want reviewed to `history.snapshot_files` in your facts file,
then run `financial-history-review`. The three clocks—observed facts, analyses,
and projections—remain separate, and missing values are never carried forward.
After recording a later truthful observation, use the history review to explain
what changed and run `household-review` again to reprioritize the worklist.
See [SCHEMA.md](SCHEMA.md#history--immutable-local-snapshots) for the document
contract and restatement command.

---

## Using this with an agent

The skills are written to be read by an agent as much as by you. The intended
loop:

1. You put documents in the matching `inputs/<category>/` directories
2. The agent runs `document-intake` and reads the files
3. The agent **proposes** values; **you** confirm them into `inputs/facts.yml`
4. The agent runs `household-review`, follows the relevant specialist chain,
   and explains the reports
5. The agent checks cross-skill conflicts and models material changes before
   you decide whether to act

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

Files under `history/` contain retained copies of private facts. They are
gitignored, and the commit hook blocks a forced add. Do not bypass either
guard.

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
| `inputs/README.md` | Private facts, source-document categories, and history paths |
| `outputs/README.md` | Private output categories and save examples |
| `documents/README.md` | Compatibility notes for the legacy flat document directory |
| `CONTRIBUTING.md` | House style, if you want to add a skill |
| `ROADMAP.md` | What is built, what is not, and what was rejected |
| `REVIEW.md` | The standing list of what is wrong with this |

*Not financial, tax, or legal advice.*
