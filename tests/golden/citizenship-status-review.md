# Citizenship, status and domicile

Three different statuses govern three different taxes, and they do not move together:

| Question | Governed by |
|---|---|
| Is worldwide income taxed by the US? | **Residence** — citizen, permanent resident, or substantial presence |
| Is the estate taxed, and on what? | **Domicile** — residence *plus* intent to remain |
| Does a transfer to a spouse get the marital deduction? | **The spouse's citizenship** |

A household can be fully US tax resident on income, fully US domiciled for estate purposes, and still lose the unlimited marital deduction because the surviving spouse holds a foreign passport.

## Recorded status

| Member | Role | Citizenship | US status |
|---|---|---|---|
| a1 | primary | US | citizen |
| a2 | spouse | CA | permanent_resident |

Domicile: **US / TX** · determined deliberately

## Findings

- 🚫 **BLOCKER** **estate** — **The unlimited marital deduction does not apply to a non-US-citizen spouse** (a2). Property passing to them at death does not qualify unless it passes through a **qualifying domestic trust (QDOT)**, which has to exist and be drafted for the purpose before it is needed. The deduction can also be preserved if the spouse naturalises before the estate-tax return is filed — which is a reason to know where the naturalisation timeline sits.
  *Affects: `estate-document-review`, `beneficiary-audit`, `survivor-needs`, `life-insurance-review`*

- · Note **estate** — Lifetime gifts to a non-citizen spouse are also capped at an annual exclusion rather than being unlimited. Relevant to any plan that equalises assets between spouses.
  *Affects: `estate-document-review`*

- · Note **expatriation** — The §877A expatriation tax can reach a citizen who relinquishes and a permanent resident who held that status in 8 of the last 15 years and then ceases to be one. Anyone planning to leave permanently should understand it **before** taking the status, not after.
  *Affects: `cross-border planning`*

## Shipped conclusions to re-check

These skills were written before status was in the schema, so any conclusion they have already produced was reached without it:

- `beneficiary-audit`
- `cross-border planning`
- `estate-document-review`
- `life-insurance-review`
- `survivor-needs`

Re-run them once status is recorded. Where a finding above is a blocker, treat the earlier conclusion as unverified rather than wrong — it may well survive, but nothing checked.

## What this skill will not tell you

Whether you *are* US domiciled, whether a QDOT is needed in your case, whether benefits will be payable where you intend to live, and anything turning on a treaty. Those are determinations, not lookups. This skill establishes **which questions apply to you** and which shipped conclusions were reached without asking them.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/status.py` with their reasons; every figure above is derived, not restated. Immigration and estate-domicile questions need a lawyer, not a skill.*
