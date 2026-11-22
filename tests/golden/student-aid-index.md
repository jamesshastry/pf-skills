# Student Aid Index

**Award year 2036-37**, based on 2034 income (prior-prior year) and assets on the filing date.

## The decision

- Need-based aid is plausible at the listed costs. Asset placement matters at the margin: up to $564 of SAI per $10,000 of reportable parent assets (529s included, whoever owns them), and $2,000 per $10,000 in the student's own non-529 accounts.

- The 2036-37 tables are not yet published; the latest published year was used. Treat dollar figures as a projection.

- The Social Security wage base for the income year is not yet published; the latest known base was used.

- Student income is not recorded for every eligible student; it is left out, so those SAIs are lower bounds.

## Parents' contribution

|  | Amount |
|---|---|
| Total income (AGI + untaxed income) | $157,000 |
| Less federal income tax | −$15,300 |
| Less payroll tax allowance | −$13,770 |
| Less income protection allowance | −$44,880 |
| Less employment expense allowance | −$5,000 |
| **Available income** | **$78,050** |
| Reportable parent assets | $108,679 |
| × 12% conversion | $13,041 |
| Adjusted available income | $91,091 |
| **Parents' contribution** | **$34,050** |
| — from income alone | $27,920 |

There is **no state tax allowance** and no reduction for two children in college at once — both were removed by the FAFSA Simplification Act.

## Assets: what counts

| Item | Value | FAFSA treatment |
|---|---|---|
| cash | $40,000 | counted |
| brokerage | $40,679 | counted net of $4,321 margin debt |
| retirement_401k | $310,000 | retirement account |
| college_529 | $28,000 | counted |

## Per student

| Student | SAI | Need by school | Student-held assets |
|---|---|---|---|
| c1 *(eligibility not recorded — computed as if eligible)* | $34,050 | in_state_public: $0, private: $25,950 | $0 |
| c2 *(eligibility not recorded — computed as if eligible)* *(student income not recorded)* | $34,050 | in_state_public: $0, private: $25,950 | $0 |

**Weakest input:** the income year. The FAFSA uses income from two years before the award year, so a one-off gain or a job loss in that year moves the result more than any asset decision.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/aid.py` with their reasons; every figure above is derived, not restated. The CSS Profile and other institutional methodologies are not modelled.*
