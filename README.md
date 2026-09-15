# pf-skills

Agent skills for evaluating and optimizing personal finance — insurance, liability, and risk —
that run entirely on your own machine against your own data.

> **Status:** seventeen clusters shipped, plus a cross-cutting status audit — property & casualty, income protection,
> estate, tax-advantaged space, cash & debt, concentration, retirement, housing, education, cross-border retirement,
> expat tax filing, offshore assets & pensions, owner-operator business, portfolio policy, charitable giving,
> healthcare & aging, life transitions, and real estate investing.
>
> Clusters 10 onward ship **without a real-data validation case** — the validation set does not exercise foreign
> earned income, business ownership or investment property. `ROADMAP.md` predicted this; it is a property of those
> skills, not a discovery to be made later.

| Skill | Covers |
|---|---|
| `auto-insurance-review` | Liability adequacy, UM/UIM, the comp/collision drop test, UMPD and MedPay interactions |
| `renters-homeowners-review` | Personal liability and the umbrella attachment gate, contents, loss of use, settlement basis, sub-limits, endorsed exclusions |
| `umbrella-liability` | Sizing against attachable assets and future earnings, the attachment gate, exclusions and pass-throughs |
| `survivor-needs` | Capital-needs analysis: what the household needs if an income stops |
| `life-insurance-review` | Coverage gap, term expiry, and the real return on a cash-value policy |
| `disability-insurance-review` | After-tax cover against spending, occupation definition, and expiring rider windows |

Run them in that order. Each of the first two checks whether the underlying
limits qualify for an umbrella to attach above them; `umbrella-liability`
depends on both being fixed first.

What comes next, and what this project deliberately won't do: [ROADMAP.md](ROADMAP.md).

### A test here is designed to fail eventually

`test_the_current_year_is_present_in_the_limits_table` goes red when the
calendar rolls into a year `lib/pf/limits.py` doesn't cover. That is the
mechanism, not a bug — statutory limits change annually, and a stale one gets
quoted confidently and believed. The skills themselves degrade safely, so it is
a maintenance signal rather than a functional break. Run
`reference-data-refresh`.

---

## Your data never leaves your machine

The first question anyone should ask of a personal-finance tool, answered plainly:

- **There is no server.** No account, no sign-up, no upload.
- **Your figures live in `inputs/facts.yml`**, gitignored, on your disk.
- **Skills are text.** They tell an AI agent already running on your machine how to reason about
  the numbers you give it. Nothing in this repo transmits anything.
- **Reports are written to `outputs/`**, also gitignored.
- **Statements you drop in `documents/` stay there.** Nothing reads them but you and whichever
  agent you hand them to; nothing in that directory is committed.

If you install via `npx skills add`, that CLI reports an anonymous install count and nothing
else — it never sees your data, because it isn't involved once the files are on disk.

The one thing to be aware of: **your AI agent is a third party.** If you run these skills in
Claude Code, Cursor, or similar, your facts are sent to that provider like any other file you
open. That's their privacy policy, not ours. For maximum privacy, run against a local model.

---

## How it works

```
1. Check the setup       uv run scripts/doctor.py
2. Start a facts file    uv run scripts/init_facts.py
3. Add your documents    cp ~/Downloads/*.pdf documents/
4. Get a worklist        uv run skills/document-intake/run.py
5. Ask your agent        "review my auto insurance"
6. Read the report       outputs/
```

Full walkthrough: **[QUICKSTART.md](QUICKSTART.md)**.

**Step 2 writes a skeleton of nulls rather than copying the example
household.** Copying is one command and it is the wrong first move: every field
you never get to still holds an invented figure, and no skill can tell the
difference between a number you entered and one the example came with. A null
stops the skill and names the field; an invented number produces a confident
report.

**Step 4 is the one that saves the hour.** Fifty-three skills read a facts file
and nothing writes one, so the real onboarding cost is transcription.
`document-intake` makes it ordered and finite: it ranks the unset fields by how
many skills each one unblocks, and `household.members` alone is about thirty of
them.

Skills contain **procedures and thresholds**. Your facts file contains **values**. That split is
why the skills can be public while your data stays private — and why a skill is reviewable by
anyone without exposing anyone.

---

## Layout

```
skills/     the skills themselves
lib/        tested arithmetic — ratios, IRR, unit conversion
scripts/    setup and safety — doctor, init_facts, privacy_audit
inputs/     facts.example.yml ships; facts.yml is yours and gitignored
documents/  your statements; the README ships, nothing else does
outputs/    generated reports; gitignored
tests/      synthetic fixtures only
SCHEMA.md   the facts contract
```

**Arithmetic lives in `lib/`, not in prose.** A derived number restated in a document is a
number that will eventually disagree with its source. Ratios, real-vs-nominal conversion, and
expected-value calculations are code with tests so they cannot drift.

---

## Design principles

**State the jurisdiction.** Insurance and tax rules are state-specific. A skill that needs a
state rule and doesn't recognize yours says so instead of applying the one it knows.

**Label the basis of every figure.** An instant cash offer is not Actual Cash Value. A skill
that runs a premium-to-value test against the wrong basis gives a confidently wrong answer, so
the schema requires you to declare which you have.

**Insure what you cannot absorb.** The recurring question is not "is this coverage worth it on
expected value" — insurance is never EV-positive. It is "would this loss be survivable." Those
give opposite answers on cheap assets and catastrophic liability.

**Show the math.** Tables and derivations, not conclusions. Every figure should be checkable.

**Name the uncertainty.** Estimates are labeled as estimates. Unverified inputs are labeled
unverified. A skill that needs a number you don't have stops and asks.

---

## Not advice

This is analysis tooling, not licensed financial, tax, or legal advice. It shows reasoning so
you can check it and names what would change the answer. Rules vary by state and change over
time. Verify anything that matters against your actual policy documents and a qualified
professional.

---

## License

MIT
