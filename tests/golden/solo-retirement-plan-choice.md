# Solo retirement plan choice

Owner-only business · $204,000 net profit · schedule_c · age 39

**Solo 401(k) shelters the most: $62,466** this year.

| Plan | Elective deferral | Catch-up | Employer | Total | Capped by |
|---|---|---|---|---|---|
| Solo 401(k) | $24,500 | — | $37,966 | **$62,466** | — |
| SEP IRA | none | — | $37,966 | **$37,966** | — |
| Defined benefit | none | — | — | **no figure** | actuarial |

*§415(c) and the catch-up rules are read from `lib/pf/limits.py` for 2026; nothing here recomputes them. For what is already used across every account, see `contribution-space-audit`.*

- **The Solo 401(k) shelters $24,500 more than the SEP** on the same net self-employment earnings. The gap is the elective deferral, which a SEP has no equivalent of.

- For a Schedule C the employer contribution is itself deductible against QBI, so the after-tax value of a dollar contributed is less than the marginal rate suggests — the §199A deduction shrinks by 20 cents of that dollar too.

## Solo 401(k)

- Elective deferral of up to $24,500 **on top of** the 25%/20% employer piece, plus catch-up which sits outside §415(c). Both come from the same person; the plan just counts them separately.

## SEP IRA

- A SEP has **no elective deferral and no catch-up.** Everything must come from the employer percentage, so below the income where that percentage alone reaches §415(c), a SEP simply shelters less.

- A SEP also requires **proportional contributions for every eligible employee** at the same percentage of pay. That is costless while the business is owner-only and expensive the year it is not — which is the failure mode: the plan was chosen for its simplicity and becomes the reason a first hire is unaffordable.

## Defined benefit

- **No figure, deliberately.** A defined benefit plan is limited by §415(b) — a *benefit* limit — and the deductible contribution is whatever an enrolled actuary certifies is needed to fund it, given age, compensation history and assumed returns. It is routinely $100k–$300k+ for an older high-income owner, which is the reason to look at it, and it cannot be estimated responsibly without the actuary.

- It is also a **funding commitment**, not an annual election: the contribution is largely mandatory in bad years too, and terminating early has consequences. Right for cash-rich, stable, high-income owner-operators over roughly 45; wrong for volatile income.

## The year the business hires

- A **Solo 401(k) stops being solo** the moment a non-spouse employee becomes eligible. It does not break; it becomes an ordinary 401(k), with nondiscrimination testing, a real Form 5500 and administration costs to match.
- A spouse working in the business is **not** a disqualifying employee, and can have their own deferral and employer contribution. That frequently doubles what an owner-operator couple can shelter.

## The weakest input

**Net profit**, which is an estimate until the year closes. The employer contribution is a percentage of it, and the deadline for funding an employer contribution runs to the return due date — so this figure can be finalised after the year ends, unlike the elective deferral election.

Deadlines differ by plan and are the thing most often missed: a Solo 401(k) generally must **exist** before the year ends even though it can be funded later, while a SEP can be both established and funded up to the return due date. Check the current rule before relying on either.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/entity.py` with their reasons; every figure above is derived, not restated. Statutory limits are in `lib/pf/limits.py` and are marked unverified — check them against irs.gov before relying on a figure.*
