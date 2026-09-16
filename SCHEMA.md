# Facts Schema v1

The contract between **your data** and **these skills**.

Skills never contain figures. They declare which fields they need, and read them from a facts
file you own. This document defines those fields.

**Your facts file stays on your machine.** Nothing here transmits, uploads, or phones home.

---

## Where your data lives

```
inputs/facts.yml          ← yours. gitignored. never committed.
inputs/facts.example.yml  ← synthetic sample. committed.
outputs/                  ← generated reports. gitignored.
```

Copy the example, replace the values, keep the shape:

```bash
cp inputs/facts.example.yml inputs/facts.yml
```

---

## Conventions

**Money** is a plain number in `meta.currency` units. No symbols, no separators: `14500`, not
`$14,500`.

**Dates** are ISO 8601: `2026-08-30`.

**`*_as_of`** marks when a value was last verified. Skills use it to flag staleness. A figure
without a date is treated as unknown age, not as current.

**Nulls are honest.** Omit a field you don't know rather than guessing. A skill that needs it
will say so and stop. A guessed number that flows into a recommendation is worse than a gap.

---

## `meta` — required

```yaml
meta:
  schema_version: 1
  as_of: 2026-08-30
  currency: USD
  jurisdiction:
    country: US
    state: TX          # two-letter code
```

**`jurisdiction` is required and has no default.** Insurance and tax rules are state-specific —
UM/UIM caps, minimum liability, community property, homestead protection all vary. A skill
that needs a state rule and doesn't recognize the jurisdiction must say so rather than silently
applying the rule it knows.

---

## `household` — required

```yaml
household:
  members:
    - { id: a1, role: primary,   age: 41, income_annual: 180000 }
    - { id: a2, role: spouse,    age: 39, income_annual: 0 }
    - { id: c1, role: dependent, age: 8 }
    - { id: c2, role: dependent, age: 5 }

  balance_sheet:
    - { name: cash,           value: 40000,  tier: liquid }
    - { name: brokerage,      value: 45000,  tier: liquid }
    - { name: retirement_401k, value: 310000, tier: age_restricted }
    - { name: home_equity,    value: 0,      tier: illiquid }

  annual_spending: 96000
  education_obligation: 180000      # optional
```

**`education_obligation` must be net of dedicated education savings.** If a 529 sits on the
balance sheet, the obligation here is the part it does **not** cover — otherwise the same money
is counted on both sides and the survivor gap is overstated.

`role`: `primary` · `spouse` · `dependent` · `other`

**`tier`** — the single most load-bearing field in the schema:

| Tier | Meaning |
|---|---|
| `liquid` | Spendable within days without penalty |
| `age_restricted` | Retirement accounts; penalty or age gate |
| `illiquid` | Property, private investments, lockups |

Skills that ask *"can this household absorb an $8,000 loss?"* use **`liquid`**, never total net
worth. A household with $2M in a 401(k) and $3,000 in cash cannot absorb an $8,000 loss.

### Titling and designation — required by `probate-exposure`

```yaml
- name: brokerage
  value: 45000
  tier: liquid
  titled_to: individual        # trust | joint | individual. null = unknown
  beneficiary_primary: a2      # trust | <member id> | descendants | estate | null
  beneficiary_contingent: c1   # trust | <member id> | descendants | null
  distribution_type: per_stirpes   # optional: per_stirpes | per_capita
```

**`titled_to` decides whether an asset goes through probate**, and it is the
only field in the schema that does. `joint` means joint tenancy **with right of
survivorship** — tenants in common does not avoid probate and looks identical on
a statement, so record it as `individual` unless the deed or registration says
survivorship.

**`null` is not "exposed" and not "covered."** An absent `titled_to` reports as
*cannot be determined*, and the estimated probate cost becomes a range. That is
the honest answer: the most common real state is that nobody has looked, and a
skill that defaults it either way produces a confident wrong number. The width
of the range is what not having looked is worth.

**`beneficiary_primary` is a shorthand, not a second source of truth.** Where
the fuller [`beneficiaries`](#the-beneficiaries-shape--required-by-beneficiary-audit)
list is present, `probate-exposure` derives the primary from it. Record one or
the other — recording both invites them to disagree.

The related field `estate.will_pours_to_trust` (boolean, optional) says whether
the will pours into a trust rather than passing to the spouse directly. It
decides whether a simplified spousal transfer may still be available, which is
flagged as a question for counsel rather than answered.

### `pending` — recorded but not counted

```yaml
- { name: treasury_mmf, value: 20000, tier: liquid, pending: true, ... }
```

An unsettled order is **either additional to an existing balance or came out of it**, and until
someone confirms which, counting it may double-count. `pending: true` keeps the position visible
and comparable while excluding it from every tier total — so no recommendation is measured
against money that may not be there.

Remove the flag once settlement is confirmed.

---

## `auto` — required by `auto-insurance-review`

```yaml
auto:
  vehicles:
    - id: v1
      label: 2019 Subaru Outback
      value: 14500
      value_basis: acv
      value_as_of: 2026-08-01
      lienholder: false
      comprehensive_premium_annual: 340
      collision_premium_annual: 760
      deductible_comprehensive: 500
      deductible_collision: 500
      primary_driver: a1

  coverage:
    bodily_injury:  { per_person: 100000, per_accident: 300000 }
    property_damage: { per_accident: 50000 }
    um_uim_bodily_injury: { per_person: 30000, per_accident: 60000 }
    um_property_damage: null
    medical_payments: null

  premium_annual_total: 2680
  term_months: 6
```

### `value_basis` — required

| Value | Meaning |
|---|---|
| `acv` | Actual Cash Value — what a carrier would pay on a total loss |
| `instant_offer` | Carvana/CarMax-style buy-now quote |
| `private_party` | Private-sale estimate |
| `estimate` | Anything else |

**Why this is required.** An instant cash offer runs materially below ACV — often 15–25% below.
A drop test run against an instant offer overstates the premium-to-value ratio and can
recommend dropping coverage that should be kept.

Skills must not treat a non-`acv` basis as ACV. They should either widen the result into a range
or state that the test is inconclusive pending a real valuation.

### Premiums are split

`comprehensive_premium_annual` and `collision_premium_annual` are **separate fields** because
they are separate decisions. Comprehensive covers theft, fire, hail, and glass — non-fault
events, typically 25–35% of the pair. Collision is the expensive half and the usual drop
candidate.

Many carriers quote them combined. If yours does, ask for the split. Until you have it, omit
both and set `comp_collision_premium_annual` instead — skills will report on collision only and
tell you the comprehensive question is unresolved.

---

## `property` — required by `renters-homeowners-review`

```yaml
property:
  form: renters              # renters | homeowners | condo
  monthly_rent: 2400
  coverage:
    personal_property: 10000
    loss_of_use: 3000
    personal_liability: 100000
    medical_payments_to_others: 1000
    deductible: 250
  settlement_basis: replacement_cost   # replacement_cost | actual_cash_value
  scheduled_items: []
  exclusions: [canine, trampoline]
  premium_annual: 180
```

---

## `umbrella` — required by `umbrella-liability`

```yaml
umbrella:
  coverage: null            # null means none in force
  premium_annual: null
```

---

## `insurance` — required by `life-insurance-review` and `disability-insurance-review`

```yaml
insurance:
  life:
    - id: l1
      label: Level Term 20
      type: term                    # term | whole | universal | variable_universal
                                    # | indexed_universal | group
      insured: a1                   # household member id
      death_benefit: 500000
      premium_annual: 420
      issued: 2021-06-06
      term_expires: 2041-06-06      # null for permanent cover
      employer_provided: false
      # permanent policies only — omit entirely on term
      cash_value: null
      cash_value_as_of: null
      premiums_paid_to_date: null
      beneficiaries:
        - { name: Ana Rivera, member_id: a2, relationship: spouse,
            share: 100, type: primary }

  disability:
    - id: d1
      label: Individual DI
      insured: a1
      monthly_benefit: 4200
      premium_annual: 1150
      elimination_days: 90
      benefit_period_years: 10      # or the string "to_65" / "to_67"
      definition: own_occupation    # own_occupation | modified_own_occupation
                                    # | any_occupation
      riders: [future_increase, cola, partial]
      future_increase_deadline: null   # ISO date, or an integer age
      employer_provided: false
      premium_paid_with: after_tax  # after_tax | pre_tax
```

### `premium_paid_with` decides whether benefits are taxed

An individual policy paid with **after-tax** dollars pays a **tax-free** benefit. An
employer-paid group policy pays a **taxable** one. The same stated monthly benefit is worth
materially different amounts, so a skill comparing cover against need must convert to a common
basis. This field is how it knows which.

### `premiums_paid_to_date` on permanent policies

Required to compute the actual return on a cash-value policy. Without it, a skill can report
the cash value but not whether it has been a good investment — which is the only question worth
asking about one.

### Life insurance is where beneficiaries usually rot

`beneficiaries` uses the same shape everywhere it appears — see below.

---

## The `beneficiaries` shape — required by `beneficiary-audit`

Not a top-level section: it is a reusable block attached to two different parents.

Attach to any `insurance.life[]` policy and any `household.balance_sheet[]` account that
supports a designation.

```yaml
beneficiaries:
  - { name: Ana Rivera, member_id: a2, relationship: spouse,
      share: 100, type: primary, per_stirpes: false }
  - { name: Rivera Family Trust, relationship: trust,
      share: 100, type: contingent }
```

`type`: `primary` · `contingent`
`relationship`: `spouse` · `child` · `trust` · `estate` · `charity` · `other`
`member_id`: links to `household.members[]` so a skill can detect a **minor named directly**

**Three states, three meanings — the distinction is load-bearing:**

| State | Meaning |
|---|---|
| Field omitted | **Unknown.** Not checked. A skill will tell you to go and look. |
| `beneficiaries: []` | **Checked, and none are named.** A defect on a retirement account or policy. |
| `beneficiary_applicable: false` | Not that kind of asset. A car does not have a beneficiary. |

Omitting is not the same as empty. Most audits fail because nobody looked, not because someone
looked and found nothing.

---

## `estate` — required by `estate-document-review` and `digital-estate`

```yaml
estate:
  documents:
    - { type: will,               exists: true,  last_reviewed: 2019-04-02 }
    - { type: revocable_trust,    exists: true,  last_reviewed: 2019-04-02, funded: false }
    - { type: financial_poa,      exists: false }
    - { type: healthcare_poa,     exists: true,  last_reviewed: 2019-04-02 }
    - { type: advance_directive,  exists: false }
  digital:
    password_manager: true
    emergency_access_configured: false
    account_inventory: false
    two_factor_recovery_documented: false
```

### `funded` on a trust

A trust that owns nothing does nothing. Creating one is the part people pay for; retitling
assets into it is the part they skip. This field is separate from `exists` for that reason.

---

## `contributions` — required by `contribution-space-audit` and `employer-match-audit`

```yaml
contributions:
  year: 2026                        # which statutory year these apply to
  employer_plan:
    plan_type: 401k
    compensation: 180000            # plan-eligible compensation
    pay_periods: 24
    deferral_rate_pct: 12           # elective deferral as % of each cheque
    employee_pre_tax: 21600
    employee_roth: 0
    employee_after_tax: 0
    employer_match: 7200
    employer_other: 0
    in_plan_roth_conversion: null   # true | false | null (unknown)
    true_up: null                   # true | false | null (unknown)
    match_formula:
      type: percent_of_pay_per_period   # or dollar_for_dollar_annual_cap
      rate: 0.5                     # matched at 50 cents on the dollar…
      cap_pct: 0.06                 # …on the first 6% of each period's pay
      # for dollar_for_dollar_annual_cap use `cap_annual` instead of cap_pct

  ira:
    - { member: a1, type: roth_backdoor, amount: 7000 }

  hsa:
    coverage: family                # self_only | family | none
    eligible: true                  # enrolled in a qualifying HDHP?
    contribution: 0
```

### `match_formula.type` is the load-bearing field

**Two formula shapes give opposite answers to the same question.** With
`percent_of_pay_per_period`, match accrues only in periods you actually contribute — so hitting
the §402(g) limit in month three forfeits the rest of the year's match unless the plan trues up.
With `dollar_for_dollar_annual_cap`, front-loading reaches the cap *sooner* and forfeits nothing.

A skill that guesses is wrong about half the time in a confident tone, so it does not guess. If
this field is absent, `employer-match-audit` reports the question as unanswerable and tells you
what to ask HR.

### `true_up`

Whether the plan makes up under-matched contributions after year end. `null` means unknown, and
unknown is treated as *at risk* — the exposure is real until someone confirms otherwise.

---

## `debts` and `assumptions` — required by `debt-payoff-priority` and `cash-yield-review`

```yaml
debts:
  - { name: card, kind: credit_card, balance: 6200, apr: 0.2249,
      minimum_payment: 155, deductible_interest: false }
  - { name: auto_loan, kind: auto, balance: 14800, apr: 0.0629,
      minimum_payment: 410, deductible_interest: false }

assumptions:
  #: Yield on a competitive money market or short-duration Treasury fund.
  #: Asked for, never fetched — a rate hard-coded in a skill goes stale
  #: silently and produces confident nonsense in both directions.
  cash_benchmark_apr: 0.042              # GROSS yield, net of fund expenses
  cash_benchmark_as_of: 2026-08-30
  cash_benchmark_label: Treasury money market
  cash_benchmark_state_tax_exempt: true

  #: Supply all three to get an after-tax comparison. Without the state rate
  #: the exemption cannot be valued, so the skill falls back to gross and
  #: says so rather than quietly omitting the thing being measured.
  marginal_tax_rate: 0.24                # federal
  niit_rate: 0.038                       # net investment income tax, if it applies
  state_tax_rate: 0.093
  expected_return_apr: 0.07        # for the pay-down-vs-invest comparison
  marginal_tax_rate: 0.24          # to put deductible interest on an after-tax basis
```

`apr` is a decimal, not a percentage: `0.0629`, not `6.29`.

**`deductible_interest`** matters because a deductible rate is not comparable to a
non-deductible one. Mortgage interest at 6% with a 24% marginal rate costs 4.56% after tax, which
can reorder the whole payoff sequence.

### Yield on liquid holdings

```yaml
- { name: checking, value: 40000, tier: liquid,
    yield_gross: 0.0001, state_tax_exempt: false }
- { name: treasury_mmf, value: 45000, tier: liquid,
    yield_gross: 0.0375, state_tax_exempt: true }
```

Omitted means unknown, and `cash-yield-review` will tell you to go and read the statement rather
than assuming a rate. *(`yield_apr` is the original name for `yield_gross` and still works.)*

**`asset_class`** (`cash` · `equity` · `bond` · `other`) keeps `cash-yield-review` off holdings
it has no business reviewing. `tier: liquid` means *spendable within days*, which is true of a
stock position — that makes it liquid, not cash. Rows without an `asset_class` are reviewed as
cash and the report says so.

**`state_tax_exempt` is the field that decides the answer.** Interest from direct Treasuries is
exempt from state income tax; bank and prime money-market interest is not. In a high-tax state
that exemption is frequently worth more than the headline yield difference it hides behind, so a
gross comparison can rank the wrong vehicle first.

**Enter yields net of expenses.** A fund's SEC 7-day yield already is. Subtracting an expense
ratio from a quoted yield double-counts it — the same basis error as comparing an instant offer
to ACV.

---

## `equity_comp` — required by `employer-concentration-risk` and `equity-comp-review`

```yaml
equity_comp:
  employer: Northwind            # label only; nothing looks it up
  held_value: 22000              # vested shares still held
  unvested_value: 41000          # pipeline that evaporates on separation
  sell_at_vest: false            # is there a standing policy?
  grants:
    - { id: g2023, granted: 2023-03-20, annual_value: 9000,  completes: 2027-02-28 }
    - { id: g2024, granted: 2024-03-20, annual_value: 11000, completes: 2028-02-28 }
```

Also add `income_components` to the earning member so the income side of the exposure can be
separated from any income that is not employer-linked:

```yaml
- { id: a1, role: primary, age: 41, income_annual: 180000,
    employer: Northwind,
    income_components: { base: 130000, bonus: 25000, equity: 25000 } }
```

**`unvested_value` is not a balance-sheet asset and must not appear there.** It is contingent on
continued employment, which is the exact thing at risk in the scenario that matters. It is
recorded here so the concentration skills can count it as *exposure* without it inflating net
worth.

**`grants[].completes`** is what makes a vesting cliff visible. An annual equity figure hides the
moment a multi-year grant finishes and the run rate steps down.

---

## `retirement` — required by cluster 7

```yaml
retirement:
  planned_retirement_age: 60
  annual_savings: 42000            # total across all accounts
  ss_claim_age: null               # null means undecided
```

Add `birth_year` to any member whose statutory ages matter:

```yaml
- { id: a1, role: primary, age: 41, birth_year: 1985, ... }
```

**`birth_year`, not just `age`.** RMD age and full retirement age are set by birth year and have
moved recently; deriving them from a current age and today's date is off by one for anyone whose
birthday has not yet fallen this year, and that is enough to give the wrong RMD age at a band
boundary.

**`annual_savings` is required and is not derived.** Gross income minus spending is not savings —
taxes are missing, and the error is large. A skill that guessed would produce a confident,
badly wrong retirement date.

---

## `housing` — required by cluster 8

```yaml
housing:
  status: renting                  # renting | owning
  monthly_rent: 2400
  purchase:                        # the property being considered
    price: 520000
    down_payment: 104000
    mortgage_rate: 0.0645
    term_years: 30
    property_tax_rate: 0.0185      # annual, of assessed value
    insurance_annual: 1800
    hoa_monthly: 0
    maintenance_rate: 0.01         # annual, of value
    expected_years: 7              # how long before selling
```

---

## `education` — required by `education-funding`

```yaml
education:
  cost_inflation: 0.05             # optional; education outruns general inflation
  real_return: 0.03                # optional; below the retirement assumption on purpose
  children:
    - member: c1                   # links to household.members
      start_age: 18
      years_of_study: 4
      annual_cost_today: 45000     # all-in: tuition, fees, housing, books
  accounts:
    - { name: college_529, value: 60000, beneficiary: c1,
        owner: a1, glide_path: age_based }
```

### `beneficiary` on an education account is not optional bookkeeping

**A 529 names exactly one beneficiary at a time.** Households think of "the college fund"; the
form does not. An account with no `beneficiary` is reported as **unallocated** rather than split
between children — splitting it would invent an allocation nobody made.

Changing the beneficiary to another qualifying family member is permitted, and is a decision
rather than an assumption.

### `annual_cost_today` is all-in and in today's money

Tuition, fees, housing, books. The skill inflates it. Entering a future figure double-counts.

---

## Status fields: `citizenship`, `us_status`, `domicile`

Required by `citizenship-status-review`. Not a top-level section — these sit inside `household`.

```yaml
household:
  members:
    - { id: a1, role: primary, citizenship: [IN], us_status: nonimmigrant_visa, ... }
    - { id: a2, role: spouse,  citizenship: [IN], us_status: nonimmigrant_visa, ... }

  domicile:
    country: US
    state: CA
    determined: false        # has anyone actually made this determination?
```

`us_status`: `citizen` · `permanent_resident` · `nonimmigrant_visa` · `nonresident`

### Three statuses, three taxes, and they do not move together

| Question | Governed by |
|---|---|
| Is worldwide income taxed by the US? | **Residence** — citizen, LPR, or substantial presence |
| Is the estate taxed, and on what? | **Domicile** — residence *plus* intent to remain |
| Does a transfer to a spouse get the marital deduction? | **The spouse's citizenship** |

A household can be fully US tax resident on income, fully US domiciled for estate purposes, and
still lose the **unlimited marital deduction** because the surviving spouse holds a foreign
passport. That combination is common, and it is why these are three fields rather than one.

### `domicile.determined` is not decoration

Estate tax turns on domicile, which is decided on facts and circumstances rather than by a form.
A US domiciliary gets the full exemption; a non-domiciliary gets **$60,000** against US-situs
assets. `determined: false` means the answer has been assumed — which is usually right and is
still worth knowing, because the downside case differs by two orders of magnitude.

### Why this was added late

The first twenty-five skills never asked. The schema refused to run without knowing which US
*state* a household lived in, and never asked whether they were a US *citizen*. See `REVIEW.md`
A1.

---

## `foreign_accounts` — required by `foreign-reporting-audit`

```yaml
foreign_accounts:
  - { name: sbi_nre, kind: bank, country: IN, max_value_during_year: 14200 }
  - { name: hdfc_nro, kind: bank, country: IN, max_value_during_year: null }
  - { name: icici_equity_fund, kind: foreign_mutual_fund, country: IN,
      max_value_during_year: 31000 }

foreign_gifts_received: null    # aggregate from foreign persons, this year
```

`foreign_gifts_received` is a top-level key alongside `foreign_accounts`.

`kind`: `bank` · `brokerage` · `foreign_mutual_fund` · `foreign_etf` · `unit_trust` ·
`investment_linked_policy` · `pension` · `other`

### `max_value_during_year`, not the balance

**FBAR turns on the aggregate maximum across all accounts at any point in the calendar year** —
not the year-end balance, and not per account. An account that peaked at $12,000 in March and
closed the year at $400 still counts at $12,000. Recording a year-end figure here produces a
confidently wrong answer, which is why the field is named the way it is.

`null` means *not looked up*, and the skill reports the question as unresolved rather than
assuming zero.

### Include accounts you do not own

Signature authority over an account — a relative's, a business's — is reportable even with no
beneficial interest. Record it.

### The PFIC kinds are not a judgement

`foreign_mutual_fund`, `foreign_etf`, `unit_trust` and `investment_linked_policy` are PFICs by
default for a US person. Recording the kind is what lets the skill say so.

---

---

## `crossborder` — required by cluster 10

```yaml
crossborder:
  # Where the household might go. "Stay put" belongs here as a row.
  destinations:
    - { country: IN, label: Bengaluru, years_until_move: 12,
        ordinary_income_rate: 0.30 }
    - { country: US, label: stay in Austin, years_until_move: null,
        ordinary_income_rate: null }

  roth_balance: 42000
  traditional_balance: 310000
  planned_conversion_annual: 40000    # null if none planned

  # A split-living arrangement. Months across all legs should total 12.
  locations:
    - { name: Austin, country: US, months_per_year: 7, monthly_spending: 7000,
        home_currency: true }
    - { name: Bengaluru, country: IN, months_per_year: 5, monthly_spending: 2600,
        home_currency: false }
  fixed_annual_costs: 18000           # costs that do not move with location
  duplicate_housing: null             # null means nobody looked

  medicare:
    enrolled_part_b: true
    standard_premium_monthly: 185     # this year's standard Part B premium
    months_abroad_planned: 60
    will_return_to_us: null           # null means undecided — it decides the answer
    years_after_return: 20
    has_medigap: false
    expat_policy_premium_annual: null
```

### `country` codes, and why so few work

`lib/pf/crossborder.py` holds **only `US` and `IN`**. Any other code returns unknown and the
skills say so rather than reasoning by analogy from a country they do know — destinations
differ on exactly the point that matters. An unrecognised code is not an error; it produces a
"nobody has checked this" finding, which is the honest answer.

### `ordinary_income_rate` is asked for, never inferred

The rate a destination would apply to a retirement distribution. A rate guessed for a country
is precisely the fabrication this module exists to avoid, so `null` produces "cannot be
quantified" rather than a placeholder.

### `roth_balance` — `null` is not zero

A missing balance means nobody looked, and the exposure arithmetic is the whole argument of
`roth-portability-check`. It is reported as undeterminable.

### `months_per_year` should total 12

Eleven months of legs is a year with a month of living costs unaccounted for. The model
reports the gap as a range between the cheapest and dearest leg and **will not spread it** —
which leg it belongs to changes the answer.

### `home_currency` drives the FX stress

`false` marks a leg whose costs are incurred in a currency the household neither earns nor
holds. Those legs get a 20% adverse stress, and the stressed row is the planning figure. Mark
every foreign-currency leg: leaving it out makes the plan look more certain than it is.

### `duplicate_housing`

Whether housing is paid for in both locations year-round. A split arrangement frequently
carries both for all twelve months while occupying one, which can erase most of the saving.
`null` means the question has not been asked, and is reported that way.

### `will_return_to_us` decides the Medicare answer

Never returning makes dropping Part B free; returning makes it expensive and permanent. `null`
prices both arms rather than assuming one — an unknown intention is not an intention to stay
away. It is the weakest input in that report and is labelled as such.

### `standard_premium_monthly` is supplied, not hard-coded

Same reasoning as `cash_benchmark_apr`. The Part B standard premium changes annually, and a
figure baked into a skill goes stale silently.

---

## `presence` — required by `foreign-presence-tests`, read by `state-domicile-exit`

One travel ledger, read by every test that counts days. Two skills read it and
neither keeps its own copy, because two implementations of "a day" eventually
disagree about the same Tuesday.

```yaml
presence:
  tax_year: 2025            # defaults to the year of meta.as_of
  days:
    - country: PT           # ISO country code. `US` is special-cased
      state: null           # US state, on US stays only — see below
      start: 2025-02-20     # inclusive
      end:   2025-07-03     # inclusive
      transit: false        # true for a day in transit / over international waters
      label: Lisbon         # free text, used when a row cannot be read
```

**A day means different things to different tests, and that is deliberate:**

| Test | Basis |
|---|---|
| §911 Physical Presence | a **full day** — a complete 24-hour period in a foreign country |
| A destination's residency threshold | **any part of a day** present |
| A US state's day count | **any part of a day** present |

So the same trip produces different numbers in different rows of the same
report, and all of them are correct.

**`transit: true`** marks a day that is not a full day in a foreign country
even when both endpoints are foreign — a day over international waters is the
paradigm case, and it is the most-missed exclusion in the 330-day count.

**`state:` on US stays** is what makes `state-domicile-exit` able to count days
in a state. Without it, that count is reported as **unknown** rather than zero.
An uncounted day is not a day you were absent.

**Gaps count against you.** A date inside the ledger's span with no stay
covering it is *not* a full foreign day, and nor is a day whose neighbour is
unknown — so the first and last day of the ledger never count. Under
examination the ledger is the evidence, and a day nobody recorded is a day
nobody can prove. Record a few days either side of each trip and they come
back honestly.

### `presence.bona_fide` — four booleans, and `null` is a real answer

```yaml
  bona_fide:
    entire_tax_year_covered: false            # an uninterrupted period covering a whole tax year
    us_abode_retained: true                   # a home kept available in the US
    claimed_nonresident_on_foreign_return: false
    indefinite_assignment: null               # nobody has answered
```

Each is reported as ok, fail, or **unknown** — and unknown is not the same as
satisfied. Each of these has ended a claim on its own.

### `presence.destination` — the threshold is yours, not ours

```yaml
  destination:
    country: PT
    threshold_days: 183       # asked for, never fetched
    tax_year_start: 2025-01-01
    tax_year_end: 2025-12-31  # not always the calendar year
```

**No country's residency rule is encoded in this repository.** A 183-day rule
written from memory would be wrong for the country where it mattered — some
jurisdictions use rolling windows, weight prior years, or have split-year rules
that change the answer entirely. Omit `threshold_days` and the skill reports
the day count and refuses the conclusion.

---

## `expat` — required by `feie-vs-ftc` and `cfc-gilti-screen`

```yaml
expat:
  tax_year: 2025
  filing_status: married_joint   # or single; derived from the household if absent
  foreign_earned_income: 150000  # required
  foreign_tax_on_earned_income: 38000   # required — the general basket only
  us_source_income: 30000
  foreign_unearned_income: 0
  planned_ira_contribution: 7000
  feie_elected_prior_year: false # decides whether switching is a 5-year commitment
  foreign_entities:
    - name: Rivera Consultoria Lda
      country: PT
      kind: foreign_corporation  # or foreign_partnership | disregarded_entity | foreign_trust
      ownership_pct: 60          # your direct holding, vote or value
      us_shareholder_pct: 60     # all US 10%-plus holders together
```

**`foreign_tax_on_earned_income` is the general basket only.** Foreign tax on
investment income sits in a separate credit basket and cannot be netted against
it; recording it here would overstate the credit. It is excluded from the
model and named in the report.

**`ownership_pct` unrecorded is reported as "cannot be determined", never as
below the threshold.** And every percentage is read as a floor: attribution
rules treat shares held by a spouse, children, parents, partnerships and trusts
as yours.

Record `foreign_entities: []` explicitly if there are none, so the answer is
checked rather than absent.

---

## `state_exit` — required by `state-domicile-exit`

```yaml
state_exit:
  from_state: CA                 # required — the state you are trying to leave
  to_state: TX
  move_date: 2024-06-30
  new_domicile_established: true # the load-bearing question, not a detail
  count_year: 2025               # which year to count state days over
  severance:                     # true = done, false = not done, absent = nobody checked
    home: true
    family: true
    business: null
    days: null
    drivers_license: true
    voter_registration: false
    vehicle_registration: true
    professional_advisors: null
    banking: false
    memberships: null
    mailing_address: null
    estate_documents: false
```

**Absent is not false.** "Nobody has checked" and "recorded as not done" are
reported as separate lists, because they call for different actions.

Only **CA** and **TX** are in the cited state table. Every other state returns
nothing and the report says so rather than reasoning by analogy.

---

## `pfic_holdings` — required by `pfic-divest-or-comply`

```yaml
pfic_holdings:
  - name: icici_india_equity
    kind: foreign_mutual_fund
    country: IN
    value: 61000
    basis: 22000
    acquired: 2016-06-15          # the original purchase, not the last top-up
    qef_statement_available: false
    marketable_on_qualified_exchange: false
```

If `pfic_holdings` is absent, the skill falls back to the PFIC-kinded rows in `foreign_accounts`
— which carry no basis or acquisition date, so it can report the regime but not the charge.

### `acquired` drives most of the charge

The §1291 charge is allocated pro-rata across every day held, and each prior year's slice
compounds. **The holding period moves the answer more than any rate does.** Where several funds
are held the charge is computed off the *earliest* acquisition, because averaging flatters it.

### `qef_statement_available` and `marketable_on_qualified_exchange`: `null` is not `false`

`null` means nobody has asked the fund administrator. The skill reports the unknown as a finding
rather than assuming a default, because the answer decides which half of the report applies.

- `qef_statement_available` — does the fund issue a **PFIC Annual Information Statement**? Most
  non-US retail funds do not. Without one there is nothing to elect under §1295.
- `marketable_on_qualified_exchange` — is this *marketable stock* regularly traded on a qualified
  exchange? An open-ended fund transacting at NAV generally is not, whatever its liquidity feels
  like.

---

## `foreign_pensions` — required by `foreign-pension-classification`

```yaml
foreign_pensions:
  - name: uk_employer_scheme
    scheme: uk_workplace_pension
    balance: 48000
  - name: epf_india
    scheme: in_epf
    balance: 31000
    employee_contributions_to_date: 26000
    employer_contributions_to_date: 18000
    holder_directs_investments: false
```

`scheme`: `uk_workplace_pension` · `uk_sipp` · `ca_rrsp` · `au_superannuation` · `sg_cpf` ·
`in_epf`. Anything else returns `UNKNOWN` and the skill says so.

### The scheme key is looked up, never inferred

The table in `lib/pf/pension.py` carries a `source` and a `verified_on` per entry. A scheme that
is not in it is reported as unknown — **never resolved by analogy to one that is.** The UK and
Australia both have employer-established workplace pensions and opposite US treatment.

### `employee_contributions_to_date` vs `employer_contributions_to_date`

One of the three facts the classification turns on. Employee contributions exceeding employer
contributions pushes a non-treaty scheme from the §402(b) employees'-trust reading toward the
foreign grantor trust reading under §§671–679 — which is what brings Forms 3520 and 3520-A into
scope, with penalties starting at $10,000.

**Absent, the report falls back to the table's default, which is the more favourable reading.**
The skill names this as its weakest input wherever it happens. The split is on the annual
statement.

### `holder_directs_investments`

The other tipping fact. Defaults to the table's `holder_directed_by_design` where not recorded.
It cannot move a scheme *into* the treaty bucket — treaty coverage is a property of the scheme and
the treaty, not of how the holder uses it.

---

## `charity` — required by `charitable-giving-strategy`

```yaml
charity:
  annual_gift: 9000              # what the household gives in an ordinary year
  candidate_holdings:
    - { name: Northwind, value: 22000, basis: 4000, held_days: 1200 }
```

`candidate_holdings` are the **lots** that would be considered for an in-kind gift, not the whole
balance sheet. `held_days` decides the long-term test (366 days); below it the deduction is
limited to **basis**, not value.

### `basis` is the field that decides the recommendation

Without it an appreciated gift and a forfeited loss are indistinguishable — and those are opposite
recommendations, not adjacent ones. Donating a position below basis deducts the value and
forfeits the loss permanently; the right move is to sell, book the loss, and donate the cash.

The AGI percentage limits (60% cash, 30% appreciated property, 5-year carryforward) and the QCD
age of 70½ **are** encoded in `lib/pf/charity.py` — statutory and stable, on the same terms as
the FBAR threshold in `reporting.py`. The standard deduction, the QCD limit and the capital gains
rate are not: two are indexed and the third is household-specific.

`household.agi` (optional) falls back to the sum of member `income_annual`;
`household.rmd_applies` (optional) unlocks the QCD-before-any-other-distribution warning.

---

## `business` — required by `entity-structure-comparison`, `solo-retirement-plan-choice` and `depreciation-election`

Scope is **one or two owner-operators with no third-party employees.** A business with
staff is business administration, not household finance, and these skills do not model it.

```yaml
business:
  owners: [a2]                      # member ids. Used to separate business income
                                    # from the rest of the household's income.
  structure: schedule_c             # schedule_c | s_corp | c_corp
  gross_revenue: 265000
  expenses: 61000                   # EXCLUDING owner salary and the employer
                                    # payroll tax on it — both are modelled per structure
  field: graphic_design
  sstb: false                       # specified service trade or business: consulting,
                                    # law, health, accounting, financial services,
                                    # performing arts, athletics. Above the §199A
                                    # threshold an SSTB's deduction phases out entirely.
  ubia: 18000                       # unadjusted basis of qualified property. Only
                                    # matters above the threshold; absent is REPORTED,
                                    # not treated as zero.
  reasonable_salary_floor: 72000    # the lowest salary defensible as reasonable
                                    # compensation. ASSERTED, never derived — see below.
  owner_w2_salary: null             # required only when structure is s_corp/c_corp:
                                    # plan space is a percentage of THIS, not of profit
  owner_outside_wages: 0            # the OWNER's own W-2 wages from other employment.
                                    # The Social Security wage base is per person — a
                                    # spouse's salary does not consume it.
  s_corp_annual_cost: 2400          # payroll processing + 1120-S + state franchise or
                                    # minimum tax + registered agent. Without it the
                                    # report gives a number instead of a verdict.
  taxable_income: 204000            # taxable income from the trade or business, for the
                                    # §179 limitation

  alternate_scenarios:              # OPTIONAL. Re-runs the comparison at a different
                                    # profit level and reports only the verdict. The
                                    # S-Corp election's verdict flips with profit, and
                                    # a single profit level shows one side of it.
    - label: A slow year
      gross_revenue: 118000
      expenses: 61000               # omitted ⇒ the main block's expenses

  assets:
    - description: Work SUV
      cost: 82000
      business_use: 0.55            # REQUIRED. Unknown is not 100%.
      gvwr_lbs: 7200
      annual_business_miles: 14000
      actual_operating_cost: null   # fuel, insurance, repairs, registration
      placed_in_service: 2026-03-02
      first_year_method: null       # standard_mileage | section_179 | bonus
```

**`reasonable_salary_floor` is an assertion, not a computation.** It depends on what the
work is, what comparable people are paid for it, and how much of the profit is labour
rather than capital. No skill here will invent it. Leave it out and the salary sweep
starts at zero, which is the left-hand end of a curve, not a recommendation.

---

## `portfolio` — required by `asset-allocation-review`, `rebalancing-rules` and `wash-sale-policy`

```yaml
portfolio:
  #: The policy. Read, never inferred from current holdings — inferring it
  #: makes drift definitionally zero. Must sum to 1.0; a target that does not
  #: is reported as a recording error and is NOT renormalised.
  target_allocation:
    us_equity: 0.50
    intl_equity: 0.20
    bond: 0.25
    cash: 0.05

  #: Annual new money available to rebalance with. The cheapest rebalancing
  #: tool there is: buying the underweight class with new money realises no
  #: gain. Omitted means unknown, and the plan says so rather than assuming 0.
  annual_contributions: 34000

  rebalancing:
    policy: bands              # bands | calendar | bands_and_calendar
    last_reviewed: 2026-02-01

  wash_sale:
    direct_index_provider: Meridian Direct
    #: A provider harvesting continuously restarts the 30-day window every
    #: time it sells, so the exclusion list has no reliable expiry date and is
    #: treated as a standing prohibition.
    harvesting_continuous: true
    #: A purchase by a spouse triggers the wash sale. null means nobody has
    #: recorded whether their accounts follow the list — reported as a gap.
    spouse_accounts_covered: null
    excluded_securities:
      - { ticker: XOM, reason: harvested_loss, sold_on: 2026-08-18, source: direct_index }
      - { ticker: KO,  reason: harvested_loss, source: direct_index }
```

### New fields on `household.balance_sheet[]`

**`account_type`** (`taxable` · `tax_deferred` · `roth` · `hsa` · `education`) is
the tax wrapper, and it is orthogonal to `tier`. `tier` answers *can this be
spent*; `account_type` answers *what happens when it is*. Both are needed:
asset location, the cost of a rebalancing trade, and the severity of a wash
sale all turn on the wrapper, not on liquidity.

`education` accounts are **excluded** from the household allocation. Money
committed to a dated obligation has its own glide path; counting a 529 as
household equity overstates the risk the household can carry.

**`holdings[]`** splits one account across asset classes, which is what a real
retirement account looks like:

```yaml
- name: retirement_401k
  value: 310000
  tier: age_restricted
  account_type: tax_deferred
  holdings:
    - { asset_class: us_equity,   value: 200000 }
    - { asset_class: intl_equity, value: 50000 }
    - { asset_class: bond,        value: 60000 }
```

The sub-holdings are used and the row `value` is ignored for allocation; a
mismatch between them is reported rather than silently reconciled.

`asset_class` extends the existing set (`cash` · `equity` · `bond` · `other`)
with `us_equity`, `intl_equity` and `reit`. `equity` still works as a single
undifferentiated class. **A row with no `asset_class` is excluded from every
allocation figure including the denominator, and named in the report** —
unknown is not "other".

**`wash_sale_policy_applied`** (`true` · `false` · `null`) records whether this
account honours the exclusion list. `null` is reported as a gap, not as
probably fine: unrecorded coverage is the exact state in which the expensive
version of the mistake happens.

---

## `healthcare` — required by cluster 16

```yaml
healthcare:
  working_past_65: true            # decides IEP vs Special Enrolment Period
  employer_employees: 250          # 20+ = group plan primary; under 20 = Medicare primary
  coverage_is_current_employment: true   # COBRA and retiree cover are NOT
  part_a_quarters: 40              # 40 needed for premium-free Part A
  ltc:
    annual_cost_today: 110000      # regional; asked for, never assumed
    cost_as_of: 2026-06-30
    survivor_annual_spending: 72000
    policies:
      - { id: ltc1, type: hybrid, insured: a1, daily_benefit: 200,
          benefit_period_years: 3, elimination_days: 90,
          inflation_protection: false, premium_annual: 4800 }
```

**`employer_employees` is the load-bearing field in the whole section.** At 20 or
more the group plan pays primary and Part B can be delayed safely. Below 20,
**Medicare is primary** — the group plan can pay as though Medicare had already
paid its share, so someone who has not enrolled is uninsured for that share and
finds out at a claim. Omitted means unknown, and `medicare-enrollment-timing`
refuses rather than assuming the safe case.

**`coverage_is_current_employment: false` is the COBRA trap.** COBRA, retiree
coverage and marketplace plans are not coverage from current employment. None
creates a Part B Special Enrolment Period and none is creditable for Part B. A
household bridging past 65 on eighteen months of COBRA accrues the permanent
late-enrolment penalty for the whole of it.

**`ltc.annual_cost_today` is regional and is not held in the repository.** A
national average applied to a high-cost metro understates the exposure badly,
and the error runs toward doing nothing. Omitted means `long-term-care-funding`
sizes nothing and says so.

**`ltc.survivor_annual_spending` is what the skill actually decides on** — not
the couple's spending. The test is whether the spouse who did not need care can
still retire after a five-year episode, and a household can pass the
percentage-of-assets screen and fail this.

**The dollar basis differs from cluster 7.** `retirement.py` is real
(today's money) throughout; `healthcare.py` is **nominal current-year** for the
ACA and Medicare figures, because those are annual parameters re-set each year
rather than indexed quantities that can be projected. The long-term-care section
is the exception and is real, stated inline.

---

## `transitions` — required by `windfall-management`, `marriage-finance-merger` and `divorce-asset-split`

Three unrelated life events sharing one section because they share one idea:
an event changes the **tax character** of a dollar, not just its location.

```yaml
transitions:
  windfall:
    - label: Inheritance from Ana's aunt
      kind: inheritance          # see the table below — this is the load-bearing field
      amount: 260000
      received: 2026-07-15       # the 90-day pause is measured from here
      source_foreign: true       # was the DONOR a foreign person?
  tax_withheld_ytd: 20900
  prior_year_tax: 38000          # one line on last year's return
  prior_year_agi: 172000         # decides the 100% / 110% safe harbour
  aca_marketplace_coverage: false
  medicare_within_lookback: false
```

### `windfall[].kind` is the load-bearing field

Everything the skill says is downstream of it, and the kinds are taxed
differently enough that guessing is worse than leaving it out. A kind not in
this list returns **unknown** and the skill refuses rather than reasoning by
analogy.

| `kind` | Income on receipt | Basis |
|---|---|---|
| `inheritance` | no | stepped up to date-of-death value |
| `retirement_account_inherited` | no | **no step-up** — ordinary income as drawn |
| `gift` | no | carries over from the donor |
| `equity_vest` | yes, as wages | equal to the amount included |
| `equity_sale` | yes, as gain | unchanged |
| `settlement` | **depends on what it compensates** | varies |
| `life_insurance` | no | n/a |
| `lottery` | yes | zero |

### `source_foreign` asks about the donor, not the wire

The Form 3520 test is whether the **donor** was a nonresident alien or a
foreign estate — not which country the money was sent from, and not whether it
ever entered a US account. `null` means nobody checked, and the skill reports
it as a gap rather than assuming domestic. Threshold lives in
`lib/pf/reporting.py`.

### `transitions.marriage`

```yaml
  marriage:
    tax_if_joint: 41200                # from your tax software, both ways
    tax_if_separate_combined: 46800    # the SUM of the two separate returns
    idr_annual_payment_joint: 14400    # income-driven student-loan payment
    idr_annual_payment_separate: 3120
    medical_expenses: 0                # itemised, for the 7.5% AGI floor test
    lower_earner_agi: null             # needed for that test
    household_agi: null
    stale_beneficiary_accounts: [retirement_401k]
    independent_access: { a1: true, a2: false }
```

**Both tax totals are asked for, never computed.** There is no bracket table in
this repository. Running the return twice in whatever software prepares it
takes ten minutes and is exact; an estimate here would be approximate and would
go stale silently. Without both figures the skill refuses to recommend a filing
status.

`independent_access` maps member id → does that person have an account in their
own name. It is a resilience check (frozen joint accounts), not a trust one.

### `transitions.divorce`

```yaml
  divorce:
    parties: [a1, a2]
    assets:
      - { name: roth_ira, kind: roth_ira, value: 200000, to: a1 }
      - { name: brokerage, kind: taxable, value: 45000, basis: 30000, to: a2 }
```

`kind` is one of `traditional_401k`, `roth_401k`, `pension`,
`traditional_ira`, `roth_ira`, `hsa`, `taxable`, `real_estate`. Anything else
is refused rather than guessed at.

**`basis` is required on `taxable` and `real_estate` and has no default.** A
missing basis is not a zero gain — it means nobody looked, and assuming basis
equals value assumes the embedded tax away in exactly the direction that makes
an unequal split look equal. Those assets are excluded from the after-tax
totals and the report says the comparison is incomplete.

The rates used are `assumptions.marginal_tax_rate` and
`assumptions.capital_gains_rate`, and the ones that matter are the
**post-divorce** rates — single or head of household, on one income.

`divorce-asset-split` covers the tax character of what is being divided and
nothing else. Valuation, support, custody and strategy are out of scope.

---

## `real_estate` — required by cluster 18

```yaml
real_estate:
  participation:                   # household-level, applies to every activity
    magi: 212000                   # modified AGI for the §469 phase-out
    active_participation: true     # approving tenants, setting rents, authorising repairs
    hours_real_property: 260       # hours in real property trades or businesses
    hours_all_work: 2340           # ALL personal services, including the day job
    grouping_election: false       # Reg. §1.469-9(g)

  activities:                      # one per rental activity
    - label: Cedar Park duplex     # the join key — see below
      avg_stay_days: 365           # total rental days / number of bookings
      material_participation_hours: 120
      most_hours_of_anyone: true   # more than ANY other individual, cleaner included
      expected_loss: 22000         # this year's tax loss, positive number
      suspended_losses: 14000      # prior-year §469 carryforward

  deals:                           # underwriting inputs, one per property
    - label: Cedar Park duplex
      price: 420000
      closing_costs: 9000
      down_payment: 147000
      loan_rate: 0.0685
      loan_term_years: 30
      gross_rent_monthly: 4000
      other_income_monthly: 0      # optional: parking, laundry, pet rent
      vacancy_rate: 0.06           # optional; defaults NON-ZERO and says so
      credit_loss_rate: 0.01       # optional
      capex_reserve_rate: 0.05     # optional; share of gross rent
      operating_expenses:          # any keys you like — they are summed
        property_tax: 7800
        insurance: 2400
        management: 3100
        maintenance: 2600
      hold_years: 7
      rent_growth: 0.03
      expense_growth: 0.035        # optional; defaults to rent_growth
      appreciation: 0.03
      selling_cost_rate: 0.07      # optional

  exchange:                        # a 1031 under consideration
    sale_price: 640000
    selling_costs: 44800
    purchase_price: 385000         # original cost of the relinquished property
    improvements: 22000
    accumulated_depreciation: 96000
    relinquished_debt: 210000      # payoff at closing
    replacement_value: 720000
    replacement_debt: 300000
    sale_date: 2026-08-03          # the 45/180 clocks run from here
    tax_return_due: 2027-04-15     # optional; truncates the 180 days if earlier
    deferral_years: 12             # how long you expect to hold the replacement

  cost_segregation:
    - label: Cedar Park duplex     # must match an activities[] label
      depreciable_basis: 340000    # BUILDING ONLY — land excluded
      property_type: residential   # residential | commercial
      study_cost: 6500
      hold_years: 10
```

### `label` is a join key, not a caption

`activities[].label`, `deals[].label` and `cost_segregation[].label` are matched
on. `cost-segregation-screen` resolves each property's §469 gate by looking up
its label in `activities`, and a property with no match is reported as
**unresolved** rather than assumed deductible. A household can have one
short-stay property whose gate is open and a long-term rental whose gate is
shut; accelerating depreciation on the second is worth nothing, and a
household-level gate would hide that.

### `avg_stay_days` is an average over bookings, not the typical stay

Total rental days divided by number of bookings, across the year. Seven or less
makes the activity **not a rental activity** under
Reg. §1.469-1T(e)(3)(ii)(A) — the only §469 door a full-time employee can
realistically walk through. One month-long winter booking can drag a four-day
average over the line, which is why the field is the average and not the
nightly minimum.

### `hours_all_work` includes the day job

It is *all* personal services in any trade or business, not just the real
estate ones. That is what makes the REPS majority test — rather than the 750
hours — the binding constraint for a W-2 earner, and recording only the real
estate hours would silently turn a failing test into a passing one.

### `most_hours_of_anyone` counts the cleaner

The 100-hour material participation test requires more than 100 hours **and**
more than any other individual — including a paid manager or cleaner, whose
hours on a short-stay property routinely exceed the owner's. Leave it `null` if
nobody has counted: the skill reports it as unknown and does **not** open the
door.

### `expected_loss` and `suspended_losses` are positive numbers

Both are losses; the sign is implied. `suspended_losses` is the prior-year §469
carryforward, and it is reported separately because the $25,000 allowance does
**not** release it — only passive income or a fully taxable disposition does.

### `depreciable_basis` excludes land

Land is never depreciable. Entering the purchase price overstates every
cost-segregation figure, typically by 15–30%, and nothing downstream can detect
it. Use the closing statement allocation or the assessor's land/improvement
split.

### Nothing here is fetched

Rents, expenses, appreciation, hours and stay lengths are all yours. There is no
market data, no rent comps, and no valuation. The statutory figures live under
`assumptions` and are refused when absent rather than defaulted.

---

## Year-specific figures under `assumptions`

Clusters 11 through 18 all need published, year-specific figures. **Every one of
them is asked for, never fetched and never held in this repository** — the same
principle as `cash_benchmark_apr`, and for the reason recorded in `REVIEW.md`
A3: `limits.py` is an unverified tax-code mirror that must not grow before what
is already in it has been verified. Absent any of them, the skill reports the
structure and refuses the figure.

```yaml
assumptions:
  # ── cluster 11: expat filing ──
  federal_brackets_as_of: "PLACEHOLDER — round numbers, not a real year's table"
  feie_exclusion_cap: 130000
  additional_ctc_per_child: null
  standard_deduction: 30000        # see the note below on its two shapes
  federal_brackets:
    married_joint:
      - { rate: 0.10, up_to: 25000 }
      # ... ascending, with the last band open-ended
      - { rate: 0.37, up_to: null }

  # ── clusters 12 & 15: PFIC and charitable giving ──
  ltcg_rate: 0.15                  # 0%, 15% or 20% — household-specific
  other_itemized_deductions: 12000 # SALT, mortgage interest, etc., excluding gifts
  qcd_annual_limit: 108000         # indexed; per person
  pfic_form_cost_annual: 400       # CPA fee, per Form 8621, per fund, per year
  pfic_rates:
    top_marginal_rate: { 2016: 0.396 }   # by tax year, acquisition to disposal
    underpayment_rate: { 2017Q2: 0.07 }  # IRS §6621, by quarter

  # ── cluster 13: owner-operator business ──
  ss_wage_base: 184500
  qbi_threshold: 394600
  qbi_phase_in_range: 100000
  qualified_dividend_rate: 0.15
  deductions_total: 31500          # standard or itemised. Optional, but absent
                                   # OVERSTATES taxable income
  section_179_limit: 1250000
  section_179_phaseout: 3130000
  suv_179_cap: 31300               # 6,000–14,000 lb GVWR
  bonus_depreciation_pct: 1.0      # equipment, read by lib/pf/depreciation.py
  luxury_auto_year1_cap: 20400     # §280F, bonus claimed
  luxury_auto_year1_cap_no_bonus: 12400   # §280F, no bonus. A SEPARATE, lower figure
  standard_mileage_rate: 0.70

  # ── cluster 16: healthcare & aging ──
  fpl_base: 15650                  # one-person federal poverty level
  fpl_per_additional_person: 5500
  fpl_as_of: 2026-01-15
  aca_benchmark_premium_annual: 21600   # second-lowest-cost silver, this household
  aca_cliff_applies: true          # whether the 400% FPL ceiling is in force
  aca_applicable_pct_schedule:     # [% of FPL, expected contribution share]
    - [1.50, 0.000]
    - [4.00, 0.085]
  medicaid_expansion_state: false  # decides what happens BELOW 100% of FPL
  expected_magi_in_gap_years: 118000
  irmaa_tiers:                     # optional; omit and the step is not sized
    - { magi_threshold: 218000, part_b_monthly: 74.00, part_d_monthly: 13.70 }

  # ── cluster 17: life transitions ──
  capital_gains_rate: 0.15

  # ── cluster 18: investment property ──
  passive_loss_allowance: 25000    # §469(i): unindexed since 1986
  passive_loss_phaseout_start: 100000
  passive_loss_phaseout_end: 150000
  depreciation_recapture_rate: 0.25     # unrecaptured §1250
  bonus_depreciation_rate: 0.40    # property, read by lib/pf/realestate.py
```

⚠️ **Every figure above is invented for the example household.** Replace them with the
published figures for the year in question before relying on any output.

### `standard_deduction` accepts two shapes

`charitable-giving-strategy` reads it as a single figure; `feie-vs-ftc` reads it
keyed by filing status (`married_joint` · `single`), because it also needs the
bracket table for that status. Both shapes are accepted, and a scalar is used as
written whatever the status is. Supply the mapping if you file more than one way.

A scalar is not wrong, but it is less specific than the question: if
`federal_brackets` is keyed by more than one status, the one deduction figure
is applied to all of them and a status whose real deduction differs gets a
plausible liability built on the wrong number. `conflict-check` warns when the
shapes are mismatched in that way.

### Federal brackets are validated structurally on load

Rates must ascend, bounds must ascend, and the last band must be open-ended
(`up_to: null`). A bracket table has no internal redundancy, so a transposed
digit produces a plausible liability rather than an error — structural checks
are the only defence available.

**`federal_brackets_as_of` is a string, not a date**, so a placeholder warning
prints inside the report itself. Replace the string with a real ISO date when
the table is replaced with real figures.

### `bonus_depreciation_pct` and `bonus_depreciation_rate` are two different keys

The first is equipment bonus depreciation for an owner-operator's business
assets; the second is the rate `cost-segregation-screen` applies to reclassified
property basis. They are read by different modules and **nothing in either
module keeps them in step** — set both, from the published figure for the year
each asset was placed in service.

One statutory percentage applied to two kinds of asset is still one percentage,
so two names for it is a defect rather than a design. Until it is one key,
`conflict-check` compares them and reports a divergence; on the example
household it fires, because `1.0` and `0.40` cannot both be right.

### `capital_gains_rate` and `ltcg_rate`

Both are the long-term federal rate. `divorce-asset-split` reads
`capital_gains_rate`; the charitable and real-estate skills read `ltcg_rate`.
They are separate keys for historical reasons and should carry the same value.

`conflict-check` reports it if they disagree — and also if only one is set,
which is the quieter failure: the skills reading the other key refuse the
figure, and that refusal reads as missing data even though the household has
already supplied it under the other name.

## `property_review` — required by the disclosure-review skills

The property currently under offer, as the **disclosure package** describes it.
Distinct from `housing.purchase`, which holds the rent-versus-buy arithmetic for
the same candidate: one is the deal, the other is the paperwork.

```yaml
property_review:
  state: CA                    # optional; the PROPERTY's state, which
                               # overrides meta.jurisdiction.state
  property_type: townhome      # single_family | condo | townhome
  year_built: 1974
  unit_count: 36               # building units; omit for detached
  elevated_elements: true      # wood-supported balconies/decks over 6ft
  documents_provided: [tds, spq, nhd, general_inspection, pest, title]
  hoa:                         # omit entirely for a detached home
    monthly_dues: 420
    reserve_percent_funded: 0.24
    delinquency_rate: 0.18
    reserve_contribution_share: 0.07
    litigation: construction_defect   # none | construction_defect | other
    special_assessment_pending: true
    master_policy_non_renewed: false
    rental_cap: 0.15
    packet_provided: [governing_documents, budget, minutes]
    sb326_report: none         # clean | findings | none
```

**`state` follows the property, not the buyer.** Disclosure law is a property
of where the house is; a household in one state reviewing a listing in another
is ordinary. Absent, `meta.jurisdiction.state` is used. The review skills encode
California only and refuse outright for anything else rather than reaching for
the nearest regime they know.

**`year_built` absent does not drop the year-gated disclosures.** Lead-based
paint stays on the checklist, flagged as "kept because the build year is
unrecorded". "We do not know whether this is pre-1978" is a question to ask, not
a reason to stop asking it.

**`documents_provided` and `packet_provided` are what you actually received**,
not what was promised. The review names what is absent, and for the §4525 packet
that absence is a statutory finding rather than a gap in the analysis.

**Every unrecorded association field produces a note, never a pass.** An
association whose delinquency rate nobody has requested is not an association
with a low delinquency rate.

## `social_security` — read by `survivor-needs`, `social-security-timing` and `disability-insurance-review`

Mirrors the structure of an SSA statement, because that is where every figure
comes from. **No skill computes a PIA**; a computed benefit would be a guess
wearing a statement's clothes.

```yaml
social_security:
  statement_date: 2026-09-15
  full_retirement_age: 67
  retirement_monthly: { 62: 2240, 67: 3200, 70: 3968 }
  disability_monthly: 3100
  survivors_monthly:
    spouse_at_fra: 3200          # the full widow(er)'s benefit
    minor_child: 2380            # also serves as the caregiver benefit
    family_maximum: 5600
  payable_abroad: null           # null = nobody has checked
  totalization_agreement: false
  spouse_own_projected_monthly: null   # the spouse's own statement figure, if any
```

**`minor_child` does double duty.** A child's benefit and the caregiver
("mother's or father's") benefit are both 75% of the worker's PIA, so the
statement's child figure serves for both. Without it the survivor sequence
cannot be built at all.

**`family_maximum` is not decoration.** Combined family benefits are capped, so
summing the individual lines overstates what a household receives. Absent, the
report says the total may be overstated rather than silently over-crediting.

**`payable_abroad` stays nullable and null by default.** It records an answer
obtained from SSA and nothing else. `social-security-timing` refuses to compute
it — the alien non-payment exceptions are specific — and this field must not
become a back door around that refusal.

**`spouse_own_projected_monthly` is the spouse's own statement figure**, read
only from their own SSA statement, and optional. `social-security-timing`
compares it against half the worker's PIA: below that, further credits do not
raise the household total, because the spousal top-up already covers the whole
amount. With only the worker's PIA on file the report names the dollar
threshold instead of the verdict. `disability-insurance-review` reads
`disability_monthly` the same way — as an overlay many group LTD policies
offset against, never as cover it nets out.

### `ss_credits` on a household member

```yaml
- { id: a2, role: spouse, ss_credits: 4 }
```

Forty credits makes a worker fully insured on their own record. A spouse with
fewer is **not** thereby entitled to less: spousal and survivor benefits do not
require their own credits. What changes is that they have no floor of their own,
and that their benefit cannot begin until the worker files — so a delay-to-70
decision defers their income too. `ss_insured: true | false` may be given
instead where the credit count is unknown.

## Extending

Skills declare their inputs in frontmatter:

```yaml
requires:
  - meta.jurisdiction
  - household.balance_sheet
  - auto.vehicles[].value
  - auto.vehicles[].value_basis
```

A skill that needs a field this schema lacks should propose an addition rather than reading
around it. Fields are additive within a `schema_version`; removals or meaning changes bump the
version.

---

## What this schema deliberately omits

Retirement accounts as *accounts* (contribution rates, plan rules, statutory limits), tax, and
equity compensation are **not** modeled yet. They will be added when skills that need them
exist. Speculating a schema ahead of its consumers produces fields nobody fills in correctly.

Homeowners `dwelling` fields are also absent — `renters-homeowners-review` names them rather
than inferring them.

---

**Not financial, tax, or legal advice.** These skills show derivations so you can check them,
and name what would change the answer. Decisions are yours.
