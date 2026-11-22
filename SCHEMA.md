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
inputs/<category>/        ← private source documents. contents gitignored.
outputs/<purpose>/        ← generated reports/results. contents gitignored.
history/                  ← private snapshots and analyses. gitignored.
```

Create a short skeleton of nulls, then add only fields you have verified:

```bash
uv run scripts/init_facts.py
```

`inputs/facts.example.yml` demonstrates the complete shape with an entirely
synthetic household. Do not copy its values into a real facts file: an example
number left behind is indistinguishable from a number you entered.

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

`tier` keeps that existing meaning. Two additive fields answer narrower
questions without changing it:

```yaml
- name: brokerage
  value: 45000
  tier: liquid
  liquidity_class: marketable       # cash_equivalent | marketable | restricted | illiquid
  retirement_eligible: true         # explicitly available to fund the retirement goal
```

**`liquidity_class`** distinguishes closing cash from assets merely spendable
within days. `cash_equivalent` is usable at face value. `marketable` requires a
sale and its market, tax, and debt effects before it becomes closing cash.
`restricted` and `illiquid` do not fund the reserve. An unclassified legacy row
is excluded from cash reserves and named as uncertain.

**`retirement_eligible`** is the auditable retirement-goal boundary. Primary
residences, land not planned for sale, education accounts, and personal-use
property should be `false`. Old tax-deferred, Roth, and HSA wrappers are safely
inferred as eligible when the flag is absent; other unclassified legacy rows
are excluded and named rather than silently counted as portfolio assets.

A marketable taxable account may add `margin_debt` and `tax_lots[]` with
`ticker`, current `value`, `cost_basis`, and `holding_period`. Housing funding
selects lots by ticker so sale proceeds and basis have one source of truth.
Each selected lot must be wholly `short_term` or `long_term`; mixed-period
sales are modeled separately.

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

## `continuity` — operational death and incapacity runbook

This section contains only facts needed for another person to execute the
first steps without the plan author. It points to private contact and recovery
material; it does not duplicate credentials, full identifiers, document
contents, beneficiary data, balances, or insurance terms already recorded
elsewhere.

```yaml
continuity:
  intended_reader_id: a2
  intended_reader_knows_location: true
  authorized_helper_contact_id: helper-primary
  plan_last_reviewed: 2026-08-15

  # Display-safe descriptions only. Never put a combination, password,
  # recovery code, full account number, or secret itself in these fields.
  offline_plan_copy_location: Printed continuity binder
  document_package_location: Sealed estate-document packet
  tax_records_location: Tax-record index in the document packet
  account_inventory_location: Printed account inventory in the packet
  recovery_package_location: Sealed recovery packet named in the inventory
  recovery_process_tested: true

  essential_obligations_reviewed: true
  notification_contacts_reviewed: true

  contacts:
    - id: helper-primary
      role: trusted_helper
      label: Trusted family helper
      contact_via: Contact card in the sealed document packet
      confirmed: true
      authority_scope_recorded: true
    - id: benefits-primary
      role: employer_benefits
      label: Primary employer benefits desk
      contact_via: Employer contact card in the packet
      confirmed: true
    - id: healthcare-agent
      role: healthcare_agent
      label: Healthcare agent
      contact_via: Healthcare contact card in the packet
      confirmed: true
      authority_scope_recorded: true

  essential_obligations:
    - id: housing-payment
      label: Housing payment
      category: housing
      cadence: monthly
      autopay_status: true
      continuation_instruction: Keep the current payment method active and verify it against the bill inventory

  immediate_duties:
    - id: dependent-care
      label: Confirm immediate dependent care
      category: dependent_care
      applies_to: both
      instruction: Follow the dependent-care page in the document packet
      confirmed: true

  review_triggers:
    - A birth, adoption, death, marriage, or divorce
    - A move or a change in a named helper, account, policy, debt, or employer
    - Any failed recovery-path test
```

`intended_reader_id` links to `household.members[].id`.
`authorized_helper_contact_id` links to `continuity.contacts[].id`.
`authority_scope_recorded: true` means the plan records what authority is
claimed; it does **not** establish that the authority is legally effective.

Contact roles are `trusted_helper`, `estate_attorney`, `tax_professional`,
`employer_benefits`, `insurance_claims`, `financial_institution`,
`government_benefits`, `healthcare_agent`, `dependent_care`, `property`,
`business`, and `other`.
`contact_via` should point to a private contact card, directory, or sealed
packet. The printable report suppresses obvious secrets and long numeric
identifiers, but that is defense in depth rather than a secret detector.

Obligation categories are `housing`, `utilities`, `insurance`, `debt`,
`dependent_care`, `pet_care`, `property`, `business`, and `other`.
`autopay_status` is tri-state: `true` means confirmed on autopay, `false` means
confirmed manual, and `null` or omission means nobody knows. An explicit
`essential_obligations_reviewed: true` permits an empty list; omission does not
silently mean there are no obligations.

Immediate-duty categories are `life_safety`, `dependent_care`, `pet_care`,
`property`, `business`, and `other`; `applies_to` is `death`, `incapacity`, or
`both`. A household with dependents or a business needs a confirmed matching
duty before the plan can be operationally ready.

The readiness labels are operational, not legal opinions. `blocked` means the
reader cannot locate the plan or documents, reach a confirmed helper, maintain
essential obligations, execute required care/business duties, use the recovery
path, or identify required institutions. `incomplete` means those immediate
paths work but review, inventory, or transfer facts remain open. `ready` means
no recorded completion item remains. The report reuses `estate.documents`,
`estate.digital`, beneficiary lists, household resources, insurance, and debts;
do not copy those facts into this section.

Only display-safe references belong in the public example. Real contact and
location details remain in gitignored `inputs/facts.yml` and the referenced
offline package. Structured output contains only critical-gap count and plan
review age, never contacts, locations, identifiers, or free-form instructions.

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
  held_value_in_balance_sheet: false # scenario net-worth reconciliation
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

`held_value_in_balance_sheet` says whether vested employer shares are already
inside a balance-sheet account. Scenario planning requires it when
`held_value` is nonzero so a price decline neither disappears nor reduces net
worth twice. It does not change the concentration score.

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

## `cash_flow` — required by `housing-affordability`

Named scenarios are the canonical nominal household cash-flow ledger:

```yaml
cash_flow:
  scenarios:
    - id: cash-current              # stable history/scenario join key
      label: Current compensation
      kind: current                 # exactly one current; one or more conservative
      income_components: { salary: 132700, bonus: 21350, equity: 25950 }
      gross_income_annual: 180000   # optional check; components are authoritative
      taxes_annual: 40173
      after_tax_cash_income_annual: 139827
      retirement_contributions_annual: 42000
      employer_retirement_contributions_annual: 0 # counted in savings, not take-home uses
      ira_contributions_annual: 0
      other_payroll_deductions_annual: 2357
      non_housing_spending_annual: 48321
      other_committed_annual: 1775
      minimum_savings: { annual_amount: 8500, gross_income_rate: 0.05 }
      obligations:
        - { label: education contributions, annual_amount: 7333,
            start_month: 1, end_month: 48, basis: real,
            redirect_to_retirement: true }
```

`after_tax_cash_income_annual` means compensation after income/payroll taxes
but before every separately listed deduction and use. Supply it, or supply
`taxes_annual` so it can be derived. If both exist they must reconcile to gross
income. No tax rate is inferred. The current scenario also reconciles against
the member income total and `retirement.annual_savings`; a material mismatch is
a blocker. Employee and IRA contributions reduce after-tax cash in this ledger;
employer retirement contributions reconcile to total annual savings but are
not subtracted from household cash.

`non_housing_spending_annual` explicitly excludes rent and ownership. This is
why the affordability API cannot subtract an incremental owner cost from a
surplus that still contains rent. `household.annual_spending` remains the
legacy all-purpose input for existing skills and is not read here.

Time-varying `obligations` use one-based inclusive months. Omit `end_month` for
an ongoing use. Education belongs here when it is a current cash outflow; the
separate `education` section models the long-horizon funding goal.
`redirect_to_retirement: true` tells `retirement-readiness` to add the freed
cash to its real contribution path after the obligation ends. Without that
explicit instruction the projection does not assume the money will be saved.
Because retirement is real throughout, a redirected obligation must also say
`basis: real`; the current-year cash ledger can use that same amount, while a
nominal future amount is refused rather than mixed into today's dollars.

When both minimum-savings forms are present, the **greater** dollar requirement
controls. Zero is a valid recorded amount; omission is not.

`id` is optional for legacy cash-flow calculations and required before a named
case is emitted into history. Labels are for display and may change; the stable
ID is the join key.

---

## `housing` — required by cluster 8

```yaml
housing:
  status: renting                  # renting | owning
  monthly_rent: 2400
  purchase:                        # the property being considered
    price: 520000
    down_payment: 104000
    down_payment_rate: 0.20         # used to solve candidate-price ceilings
    closing_cost_rate: 0.02
    mortgage_rate: 0.0645
    term_years: 30
    property_tax_rate: 0.0185      # annual, of assessed value
    insurance_annual: 1800
    hoa_monthly: 0
    pmi_rate: 0                     # explicit zero when not applicable
    maintenance_rate: 0.01         # annual, of value
    expected_years: 7              # how long before selling

  offer:                           # home-offer-strategy; same candidate
    list_price: 525000
    subject:
      label: Maple Ridge home      # must match purchase.label
      property_type: townhome      # must match purchase/property_review
      square_feet: 1800
    selection:                     # supplied local-market criteria
      minimum_comparables: 3
      maximum_age_days: 180
      maximum_distance_miles: 2.0
      maximum_gross_adjustment_rate: 0.25
    market:
      competing_offers: unknown    # none | possible | multiple | unknown
      subject_days_on_market: 8
      market_median_days_on_market: 21 # null when not established
      price_reductions: 0
    strategy:
      financing: mortgage          # mortgage | cash
      maximum_premium_rate: 0.02   # buyer-approved premium above core range
      # Cash reserved for a low appraisal after down payment, closing costs,
      # and the required emergency reserve; required for mortgage financing.
      appraisal_gap_cash_limit: 15000 # explicit zero is valid
      offer_increment: 1000
    comparables:                   # verified, closed sales only
      - id: comp-a                 # stable local label; an address is unnecessary
        source: MLS record A       # publisher plus URL or local file reference
        verified: true
        arms_length: true
        adjustments_supported: true # material differences and basis reviewed
        sale_price: 510000
        seller_concessions: 5000   # explicit zero when confirmed absent
        sale_date: 2026-07-15
        distance_miles: 0.4
        property_type: townhome
        square_feet: 1700
        adjustments:               # signed comp-to-subject dollars
          living_area: 15000       # positive means subject is worth more
          condition: -5000         # negative means comp is worth more

  affordability:
    target_price: 520000
    candidate_prices: [87500, 287500, 363750, 520000]
    post_close_reserve_months: 6
    lender:                         # optional; omitted means not modeled
      maximum_housing_dti: 0.28
      other_debt_annual: 3600
    funding:
      taxable_liquidation:
        account_name: brokerage     # balance-sheet row; must be marketable
        loss_carryforward: 1111
        federal_tax_rate: 0.15
        state_tax_rate: 0
        securities_sold: [XOM, PFE]
        wash_sale_reviewed: false

  transition:
    kind: rental_then_owner         # see the four supported values below
    analysis_months: 36
    tenant_months: 15
    occupancy_conversion_date: 2027-11-30
    financing_occupancy: investment # investment | owner_occupied
    investment_lender_test: dscr     # dscr | personal_dti
    loan_occupancy_requirement_months: null
    refinance_at_occupancy: true
    refinance_cost: 6500
    owner_operating_cost_growth_rate: 0.03
    rental_deal_label: Maple Ridge home
```

At `purchase.price`, `down_payment` and `down_payment_rate` must agree within
rounding tolerance. The fixed amount preserves existing `rent-vs-buy`
compatibility; the rate lets `housing-affordability` solve other candidate
prices without inventing how leverage changes.

The four transition kinds are `continue_renting`,
`buy_immediately_occupy`, `rental_then_owner`, and
`buy_land_continue_renting`. The last adds `land_costs` with annual debt
service, property tax, insurance, maintenance, and HOA. A rental-first plan
joins `rental_deal_label` to both `real_estate.deals[].label` and
`real_estate.activities[].label`, reusing property underwriting and the §469
gate. It is pre-investor-tax unless the gate is open and an explicit marginal
rate exists.

If `financing_occupancy` is `owner_occupied`, record the actual lender's
`loan_occupancy_requirement_months`. The library has no legal deadline baked
in; an absent or violated requirement blocks the plan. At conversion, current
rent and tenant income stop, and owner cash costs start exactly once.
`refinance_at_occupancy` determines whether the owner phase uses the proposed
owner loan or continues the investment loan; a planned refinance also requires
`refinance_cost`. `owner_operating_cost_growth_rate` is nominal and applies to
tax, insurance, maintenance, HOA, PMI, and other owner costs, not fixed debt
service. A refinance is modeled as no-cash-out: its principal is the amortized
investment-loan balance at conversion, not a new loan recreated from the
owner-occupancy down-payment percentage.
`investment_lender_test` records how the initial loan is actually underwritten.
When it is `dscr`, the existing rental underwriting floor is enforced and a
sub-floor deal is a blocker; `personal_dti` leaves the supplied household DTI
limit as the lender constraint.

The optional `affordability.tax_benefit` is accepted only as a complete model:
`filing_status`, `itemizes_owner`, `standard_deduction_annual`,
`renter_itemized_deductions_annual`, `owner_deductible_housing_annual`,
`deduction_cap_annual`, `marginal_tax_rate`, and `modeled_price`. A partial
model is refused.
When absent, the report shows gross owner cash cost and explicitly excludes the
tax benefit. The complete model also records `modeled_price`; the benefit is
credited only at that price, never extrapolated across the affordability
ceiling as though mortgage interest and deduction caps were fixed.

### Comparable sales and offer strategy

`housing.offer` identifies the same candidate as `housing.purchase` and, when a
disclosure review is present, `property_review`. Labels and property types must
agree so a comp set cannot silently price a different home. Store private MLS,
appraisal, and disclosure PDFs under `inputs/property/evaluations/`; the entire
property input tree is gitignored. Use non-identifying stable labels in the
facts file instead of street addresses.

When comparable rows are missing, the `home-offer-strategy` agent workflow may
search public recorder, assessor, and listing-history sources. Record the
publisher and exact URL in `source`, keep the access date in the accompanying
research notes, and refresh `meta.as_of` when confirmed facts are accepted.
The deterministic runner itself makes no network calls. Do not copy a private
address into the committed example or any tracked file.

Comparables are verified, arm's-length **closed sales**. Active and pending
listings may inform `market.competing_offers`, but an asking price is not sale
evidence. `seller_concessions` is required even when zero because unknown is not
zero. The calculation first nets concessions, then adds the signed adjustment
ledger. Each adjustment converts the comp to the subject: positive when the
subject is worth more, negative when the comp is worth more.

The report places the subject and every supplied comp in a data-point
comparison table before showing the adjustment ledger. The subject row uses
its list price; comp rows use unadjusted closed-sale prices, so the two are
explicitly labeled rather than presented as equivalent evidence.

`verified` confirms the recorded sale facts; `adjustments_supported` separately
confirms that material differences—such as living area, property type,
condition, location, lot, parking, view, and HOA—were reviewed and that the
adjustment ledger has a local evidentiary basis. Both must be true. An explicit
zero adjustment means the factor was considered and no adjustment was
supported; an omitted review does not mean the properties are equivalent.

The library never supplies generic adjustment rates. A living-area or property-
type difference without the corresponding explicit adjustment excludes the
comp, as do unverified or non-arm's-length sales and sales outside the recorded
age, distance, or gross-adjustment limits. Those limits are supplied for the
local market; they are not universal appraisal rules. Excluded comps remain in
the report with reasons.

The median adjusted sale is the central estimate. The middle half is the core
range, while the full range stays visible; neither is an appraisal or a
confidence interval. The walk-away price is the lowest of the upper core value
plus `maximum_premium_rate`, the existing stress-tested affordability ceiling,
and—when financed—the central estimate plus `appraisal_gap_cash_limit`. It is
rounded down to `offer_increment`. The skill never recommends waiving a
contingency or increasing a ceiling merely because competition is recorded.

The liquidation's gross proceeds, basis, holding period, and margin payoff are
derived from the selected balance-sheet `tax_lots` and the account's
`margin_debt`; recording duplicate totals is optional and any mismatch is
refused. Mixed holding periods must be modeled as separate sales. A taxable
account `value` is its gross market value; `margin_debt` is a separate
liability, not already netted from that value. Retirement eligibility totals
use the account net of that debt.

### Migration and backward compatibility

Schema version 1 is unchanged. Existing skills continue to read the legacy
`tier`, `household.annual_spending`, `retirement.annual_savings`, and
`housing.purchase` keys. The new affordability skill additionally requires
`cash_flow`, `housing.affordability`, the new purchase rates, and
`housing.transition`; older facts therefore stop cleanly only when this new
skill is invoked. `retirement-readiness` safely infers known retirement account
wrappers, excludes other unclassified assets with a warning, and never again
uses total net worth as the portfolio. Add `retirement_eligible` and
`liquidity_class` row by row; do not change `tier` during migration.

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

### `financial_aid` — required by `student-aid-index`

```yaml
education:
  accounts:
    # vehicle decides FAFSA treatment for an account the student owns:
    # 529 / coverdell -> parent asset; utma_custodial or anything else ->
    # student asset. balance_sheet_row says the sheet already includes it.
    - { name: college_529, value: 28000, owner: a1, beneficiary: c1,
        vehicle: "529", balance_sheet_row: education-529 }
  financial_aid:
    award_year: 2036-37              # aid year; tables are looked up by this
    income_year: 2034                # must be award year start minus 2
    parent_total_income: 157000      # AGI plus untaxed income the FAFSA asks for
    parent_federal_income_tax: 15300 # income tax paid, after credits
    parent_earned_income: 180000     # wages and SE earnings of both parents
    family_size: 4
    older_parent_age: 51
    two_parents: true
    include_foreign_assets: true     # default true; false is a household choice
    cost_of_attendance: { in_state_public: 28000, private: 60000 }
    students:                        # student income, by member id
      c1: { income: 0, federal_income_tax: 0, earned_income: 0 }
```

Income and tax are **supplied, not estimated** — take them from the return for
`income_year` or a tax projection.

**Assets** come from `household.balance_sheet` plus `education.accounts` the
sheet does not already include:

| Item | FAFSA treatment |
|---|---|
| Retirement (`tier: age_restricted`), insurance cash value, pension | not reported |
| Row with `primary_residence: true`, a personal vehicle (`vehicle: car`), a pending item | not reported |
| Negative row (a liability) | not netted against assets |
| Row with `margin_debt` | counted net of the margin debt |
| Business or farm row (`vehicle: business_equity` / `farm`) | counted at recorded value, flagged |
| 529 or Coverdell, **whoever owns it** | parent asset |
| Student-owned custodial or ordinary account | student asset (20%) |
| Account owned outside the household | not reported |

An education account is "already on the sheet" when its `balance_sheet_row`
names a row (by `id` or `name`) or a row has its exact name; several accounts
may point at one aggregate row.

**Stops rather than guesses** when: `income_year` is not the prior-prior
year; an unlinked education account sits beside an unclaimed
`earmark: education` row (it may be the same money); a student-owned account
has no `vehicle`; an account has no `owner`. A `null` balance-sheet value or
cost of attendance, or a missing `students` entry, is listed and flagged as
making the result a lower bound — never read as zero.

On `household.members`, a dependent may carry `fafsa_eligible: false` (not a
U.S. citizen or eligible noncitizen) — listed, not computed.

---

## `tax_return`

Required by `federal-tax-return` (and read by `ca-tax-return`). One tax year's
return inputs, transcribed from the source documents. Figures are nominal
dollars of `tax_year`.

```yaml
tax_return:
  tax_year: 2026
  filing_status: mfj            # single | mfj | mfs | hoh | qss
  state: TX                     # state of residence for the year
  residency: resident           # optional; nonresident / dual_status stop the skill
  taxpayers:                    # one entry (two for mfj); age on Dec 31
    - { member: a1, age: 41, blind: false, covered_by_workplace_plan: true }
    - { member: a2, age: 39, blind: false }
  dependents:                   # age on Dec 31; months lived with you
    - { member: c1, age: 8, months_lived: 12, student: false }
    # optional per dependent: ssn: false (no CTC), unearned_income (flags Form 8615),
    # born_or_died_in_year: true with months_alive (residency test)
  spouse_itemizes: null         # MFS only: true forces itemizing (§63(c)(6)(A))
  w2:
    - { employer: Northwind, owner: a1, wages: 155500, federal_withheld: 21500,
        ss_wages: 180000, ss_withheld: 11160, medicare_wages: 180000,
        medicare_withheld: 2610, state: TX, state_wages: 0, state_withheld: 0,
        sdi_withheld: 0, supplemental_wages: 47300,
        box12: { D: 24500, W: 1500, DD: 18000, AA: 0 } }
  interest:                     # amount = 1099-INT box 1 (excludes box 3)
    - { payer: Bank, amount: 1200, us_treasury: 0, tax_exempt: 0 }
  dividends:
    - { payer: Brokerage, ordinary: 1900, qualified: 1500,
        capital_gain_distributions: 300, foreign_tax_paid: 45 }
    # optional: foreign_source_income (needed for Form 1116 when it applies)
  capital_transactions:
    - { description: lot, proceeds: 6000, basis: 9000, term: long,
        wash_sale_disallowed: 0, basis_reported: true }
  capital_loss_carryover: { short: 1500, long: 0 }    # from last year's worksheet
  schedule_c:
    - { owner: a2, business: Design, gross_receipts: 265000,
        expenses: { supplies: 14000, other: 9200 },  # any category names
        vehicle: 3800, home_office: 2400, home_office_method: regular,
        sstb: false, w2_wages: 0, ubia: 18000 }
  qbi_loss_carryforward: 0      # optional; prior-year qualified business loss
  k1:                           # optional; partnership / S-corp K-1s (llc-tax-return)
    - { entity: Example LLC, form: "1065", owner: a2,   # form: "1065" | "1120S"
        ordinary_business_income: 40000, guaranteed_payments: 12000,
        se_earnings: 52000, interest: 300, dividends: 0, distributions: 25000,
        qbi_income: 40000, qbi_w2_wages: 0, qbi_ubia: 6000, sstb: false,
        material_participation: true }
  hsa: { owner: a1, contributions_personal: 8000, employer_contributions: 1500,
         coverage: family, eligible_months: 12, distributions: 1200,
         qualified_expenses: 1200 }
  ira:
    - { owner: a1, traditional_contributions: 7500, deductible: false,
        nondeductible_basis_prior: 0, conversions_to_roth: 7500,
        year_end_traditional_balance: 0 }
  itemized: { medical: 2500, property_tax: 0, other_state_local_taxes: 0,
              mortgage_interest: 0, mortgage_balance: null,
              charitable_cash: 9000, charitable_noncash: 0 }
  state_income_tax_paid: 0      # null = W-2 state withholding + state estimates
  foreign:                      # foreign-source passive income NOT on a U.S. 1099, USD
    country: IN
    accounts: true              # foreign financial accounts held -> Schedule B Part III
    interest: 5179              # incl. NRE/FCNR (exempt in India, U.S.-taxable) -> line 2b
    dividends: 0                # -> line 3b
    qualified_dividends: 0      # part of dividends -> line 3a
    capital_transactions:       # same shape as capital_transactions -> Schedule D
      - { description: plot, proceeds: 104046, basis: 58960, term: long }
    rent: 0                     # non-zero is refused (Schedule E)
    foreign_tax_paid: { passive: 3645, general: 0 }   # general non-zero is refused
    reported_on_1099: false
    category: passive
  estimated_payments: { federal: [9000, 9000, 9000, 9000], state: [0, 0, 0, 0],
                        applied_from_prior_year: 0 }
  prior_year: { agi: 172000, federal_total_tax: 26000, state_total_tax: 0 }
    # optional, for a state/local refund received this year (1099-G):
    # state_refund_received, itemized_prior, itemized_deduction_prior,
    # standard_deduction_prior, salt_paid_prior, salt_deducted_prior
  social_security_benefits:     # optional; one SSA-1099 per recipient
    - { recipient: a1, net_benefits: 0, federal_withheld: 0 }   # boxes 5 and 6
  mfs_lived_apart_all_year: null   # required only for MFS with benefits
```

### Absent, zero and `null` mean three different things

| Written | Read as |
|---|---|
| A list or field left out | none on file (no 1099-INT, no Schedule C) |
| `0` | checked, and zero |
| `null` | **nobody looked** — listed in the report's *Not recorded* section |

A `null` that determines tax — W-2 `wages`, a transaction's `proceeds` or
`basis`, any Schedule C amount, `nondeductible_basis_prior`,
`year_end_traditional_balance` when converting, `qbi_loss_carryforward`, or a
whole `capital_loss_carryover`, `hsa` or `foreign` section — **stops** the
report. A `null` deduction (an `itemized` amount or the whole `itemized`
section, `hsa.coverage`, a W-2 or K-1 `owner` needed for SE tax,
`covered_by_workplace_plan`, `dependents`) is left out and the result is
labelled an upper bound on tax. A `null` withholding, estimate or
`estimated_payments` section leaves the refund undetermined. A list or section
set to `null` (`interest: null`) is unknown, not empty. Wrong-shaped input
(text where a number belongs, a scalar where a list belongs) stops with a
message, never a traceback.

### Fields that carry a rule

- **`owner`** on W-2s is needed on a joint return with Schedule C income: the
  Social Security wage base is per person, so the owner's W-2 SS wages reduce
  the SE-tax base. It also attributes excess SS withholding across two
  employers. With one taxpayer it defaults to that person.
- **`supplemental_wages`** (or `rsu_income`) is the part of box 1 withheld at
  the 22% flat rate — bonus and RSU vesting. Used only to explain a balance due.
- **`box12`**: `D`/`AA` are checked against the elective-deferral limit; `W`
  is used for HSA employer contributions when `hsa.employer_contributions` is
  `null`.
- **`wash_sale_disallowed`** is the 1099-B code-W amount; it is added back to
  the gain.
- **`home_office_method: simplified`** loses any excess over the business's
  income; `regular` (Form 8829) carries it forward.
- **`sstb`, `w2_wages`, `ubia`** are needed only when taxable income is above
  the §199A threshold; above it without them the skill refuses.
- **`k1`** takes partnership (`form: "1065"`) and S-corporation (`"1120S"`)
  K-1s for an owner who **materially participates**:
  - `ordinary_business_income` (box 1, may be negative) plus
    `guaranteed_payments` (1065 box 4) go to Schedule E part II and Schedule 1.
    A loss is allowed on the assumption that basis and at-risk amounts cover
    it — the entity skill must confirm that.
  - `interest` and `dividends` join Form 1040 lines 2b and 3b. K-1 dividends
    are taxed as ordinary, because the entry does not split out qualified
    dividends.
  - `se_earnings` (1065 box 14 code A) feeds Schedule SE with the same per-owner
    wage-base netting as Schedule C, so `owner` matters on a joint return. A
    missing owner leaves SE tax as an upper bound. S-corporation income gets no
    SE tax, and guaranteed payments on an 1120S stop the report (shareholder pay
    is W-2 wages).
  - `qbi_income`, `qbi_w2_wages`, `qbi_ubia` and `sstb` (box 20 code Z / box
    17 code V) feed the §199A computation. The wage/UBIA limit applies above
    the threshold, where a missing one stops the report. QBI is reduced by the
    half SE tax attributable to the ordinary income, but not to guaranteed
    payments.
  - `distributions` are informational only. Whether a distribution exceeds
    basis is the entity skill's question, not this return's.
  - `material_participation: false` (passive) stops the report and points to
    `passive-loss-eligibility`; `null` stops as unknown. Any other key —
    rental income, §179, other box codes — stops it. So does a form other than
    1065/1120S (a trust K-1).
  - A `null` amount that determines tax stops the report.
  - K-1 ordinary losses count with Schedule C toward the excess business loss
    threshold, and exceeding it stops the report.
- **`deductible: true`** on an IRA contribution is tested against the §219(g)
  phase-out using `taxpayers[].covered_by_workplace_plan` for the owner and,
  on a joint return, the spouse. W-2 box 12 `D`/`AA` deferrals count as
  coverage. Unknown coverage is listed, no deduction is taken (an upper bound
  on tax) and the contribution becomes Form 8606 basis. MAGI for the test
  excludes the Roth conversion (Pub. 590-A).
- **`ira`** entries are **aggregated per owner**, because Form 8606 works per
  person, not per account. List one entry per account. Give
  `nondeductible_basis_prior` (last year's 8606 line 14) on **one** entry only;
  more than one stops the report. When an owner converts,
  `year_end_traditional_balance` is required on every entry for that owner,
  and they are summed (8606 line 6). Non-conversion `distributions` are
  refused.
- **`hsa.owner`** is the account holder. Self-only coverage gets the age-55
  catch-up only for the owner. Family coverage gets one for each spouse aged
  55+, and each must go into that spouse's own HSA. The 20% additional tax
  depends on the owner's age (§223(f)(4)(C)). `eligible_months` prorates the
  limit; the last-month rule is not modelled.
- **`born_or_died_in_year: true`** with `months_alive` applies the residency
  test against the months the child was alive.
- **Charitable gifts** are limited to 60% of AGI (cash) and 30% (non-cash,
  treated as capital-gain property), with 50% overall. The excess carries
  forward five years (`carryforwards.charitable`). Itemizing is chosen only
  when it beats the standard deduction **plus** the §170(p) amount.
- **1099-DIV** keys `section_199a_dividends`, `unrecaptured_1250`,
  `collectibles_gain`, `section_1202_gain` stop the report if non-zero.
- **`state_income_tax_paid`** is the state income tax deductible on Schedule A
  for the calendar year (withholding, estimates, and a prior-year balance paid
  this year). `sdi_withheld` is added as a state income tax.
- **`foreign`** is foreign-source passive income *not* already on a 1099, in
  USD for the U.S. calendar year on U.S. rules (the `india-tax-return` U.S.
  hand-off emits these names). Each part is routed to its real line:
  - `interest` goes to line 2b and includes NRE/FCNR interest.
  - `dividends` and `qualified_dividends` go to lines 3b and 3a.
  - `capital_transactions` go through Schedule D at 0/15/20%; a row marked
    `pfic: true` is refused.
  Schedule B Part III is triggered whenever a `country`, `accounts` or any
  foreign income is present. A non-zero `rent` is refused (Schedule E,
  depreciation, Form 8582 — `passive-loss-eligibility`), as is general-category
  tax (`feie-vs-ftc`), any other non-zero key, and the old single `income`
  total (it cannot be routed). The Form 1116 limit uses the routed
  foreign-source income less a ratable share of the deductions, with the
  capital-gain rate adjustment at the household's effective preferential
  rate. `reported_on_1099: true` allows the simplified (no Form 1116) election.
- **`social_security_benefits`** feed the Form 1040 Social Security Benefits
  Worksheet (§86): up to 50% taxable above the base amount ($25,000; $32,000
  joint) and up to 85% above the adjusted base ($34,000; $44,000 joint). On a
  married-filing-separately return `mfs_lived_apart_all_year` decides the base
  (living together at any time makes both zero) and a `null` stops the report.
  Box 6 withholding counts as a payment. A deductible IRA contribution alongside
  benefits stops the report (the Pub. 590-A worksheet is circular). Negative net
  benefits (a repayment) are flagged, not computed. The result is
  `taxable_social_security`.
- **`prior_year.state_refund_received`** is a state or local income tax refund
  received this year. It is taxable only to the extent last year's deduction
  saved tax (tax-benefit rule, Pub. 525). The taxable amount is the least of:
  the refund; `itemized_deduction_prior` minus `standard_deduction_prior`; and
  `salt_deducted_prior` minus (`salt_paid_prior` minus the refund), which is
  where the SALT cap usually makes it zero. `itemized_prior: false` makes it
  zero. A missing `state_refund_received` means none was received. A `null`
  refund stops the report, and so does a refund received with
  `itemized_prior` or, when itemized, any of the four amounts unknown. The
  result is `state_refund_taxable` (Schedule 1 line 1).
- **`prior_year`** drives the penalty safe harbor. `agi` above $150,000
  ($75,000 MFS) makes it 110% of `federal_total_tax`.

### Out of scope — the skill stops with a pointer

`rental_properties`, `schedule_e` (Schedule E part I) (→ `passive-loss-eligibility`);
`schedule_k1` (→ use `k1`; passive and trust K-1s are not modelled),
a `k1` entry that is passive, carries rental, §179 or other codes, or is not
a 1065/1120S;
`depreciation` (→ `depreciation-election`), `pfic` (→ `pfic-divest-or-comply`),
`iso_exercises`, `amt_preferences`, `residency: nonresident | dual_status`, a
capital transaction marked `collectible` or `section_1250`.

---

### `tax_return.ca` — optional, read by `ca-tax-return`

`ca-tax-return` reads the shared `tax_return` block (see above) through the
federal return, then these California-only fields. Every field is optional.
**Absent** means "none" for amounts the household would know they had, such as
LLCs, credits and other withholding. **`null`** means "nobody looked". It is
listed under *Missing documents* along with which way it biases the result.

```yaml
tax_return:
  interest:
    - { payer: State muni fund, amount: 0, us_treasury: 0, tax_exempt: 400,
        ca_exempt: false }          # required when tax_exempt > 0
  ca:
    residency: resident              # part_year / nonresident are refused (540NR)
    renter: true                     # paid rent on a CA principal residence ≥ 6 months
    hsa_earnings: 85                 # HSA interest, dividends, gains for the year
    prior_year_ca_agi: 171000        # prior Form 540 line 17
    next_year_agi_estimate: null     # next year's CA AGI, if known ($1M rule)
    us_obligation_dividends: 0       # fund dividends from U.S. obligations (CA-exempt)
    home_equity_interest: 0          # allowable CA home-equity interest ($100K debt)
    foreign_real_property_tax: 0     # deductible in CA, not federally
    use_tax: 0                       # Form 540 line 91
    full_year_health_coverage: true  # Form 540 line 92
    spouse_itemizes: null            # MFS only; overrides tax_return.spouse_itemizes
    amt_preferences: false           # ISO exercise or other Schedule P items
    depreciation_adjustment: null    # FTB 3885A difference; + adds, − subtracts
    ca_capital_loss_carryover: null  # {short, long}; null = same as federal
    miscellaneous_itemized: 0        # 2%-floor miscellaneous, before the floor
    nonrefundable_credits: []        # [{name, amount, carryover}] computed elsewhere
    other_ca_withholding: 0          # 1099 CA withholding
    withholding_592b_593: 0
    prior_year_overpayment_applied: 0
    extension_payment: 0
    other_taxes: 0                   # Form 540 line 63
    other_adjustments: []            # [{line, description, amount}]
    llc:
      - { name: Example LLC, gross_receipts_total_income: 310000,
          formed_year: 2019, formed_on: null }
```

| Field | Effect |
|---|---|
| `interest[].ca_exempt` | `tax_exempt` is the box 8 dollar amount, as in the shared block. With `ca_exempt: false` that amount is added as CA income; `null` on a row with `tax_exempt > 0` is missing |
| `hsa.employer_contributions` | Added back (Schedule CA line 1h) when no W-2 records box 12 W. If both are absent while an `hsa` block exists, it is missing |
| `prior_year.state_total_tax` | Prior Form 540 lines 48 + 61 + 62 (tax after credits, AMT, BHST), the 540-ES safe-harbor base |
| `next_year_agi_estimate` | At $1M or more ($500K MFS), no prior-year safe harbor next year, so no schedule is printed. When absent, the schedule is printed on that condition |
| `nonrefundable_credits[].carryover` | `false` orders the credit with the renter's credit, before credits that carry over (R&TC §17039). Default: carries over |
| `hsa_earnings` | Schedule CA addition. Required once any HSA activity exists, because CA taxes HSA earnings every year |
| `prior_year_ca_agi` | Picks 100% or 110% for the prior-year safe harbor. Falls back to `prior_year.agi`, with a flag |
| `depreciation_adjustment` | Required when a `schedule_c` claims `depreciation`, `section_179` or `bonus_depreciation`. CA allows no bonus depreciation |
| `ca_capital_loss_carryover` | When set, CA capital gain or loss is recomputed from `capital_transactions` with this carryover. The difference from federal becomes a Schedule CA line 7 entry |
| `llc[]` | Disregarded single-member LLCs only. `gross_receipts_total_income` is Form 568 line 1 and sets the fee. Tax-year formation needs `formed_on` to date the first $800 |
| `renter` | `null` with AGI under the limit means the credit is not claimed, and the report says so |

`itemized` is read as for the federal return, with two CA rules. A key that is
absent counts as zero. A key that is `null` makes itemized unknown, so the
standard deduction is used and the tax becomes an upper bound. `medical` should
exclude anything paid from an HSA; the skill adds back qualified HSA
distributions itself. `other_state_local_taxes` must exclude state income tax,
SDI and sales tax, none of which CA allows.

**Refused** (the skill stops and names the form that applies):

- `state` other than CA
- `ca.residency` part-year or nonresident
- `ca.other_state_tax_paid > 0`, or a non-CA W-2 with state withholding
- `ca.ftb3800` / `ca.ftb3803`
- `rental`, `schedule_e`, `k1` or `passive` present
- a taxpayer with `can_be_claimed_as_dependent: true`
- `ca.rdp: true`

---

## `india_tax_return` — required by `india-tax-return`

One Indian financial year (1 April – 31 March), all amounts in **INR**
regardless of `meta.currency`. The rate is used only for the U.S. hand-off.

```yaml
india_tax_return:
  financial_year: 2025-26            # tables keyed by this; unpublished -> nearest, flagged
  taxpayer:
    member: a1                       # household.members id; citizenship read from there
    person_of_indian_origin: true    # decides the 182/120-day visitor rule
    indian_citizen: null             # optional override; else "IN" in member citizenship
    birth_date: null                 # optional; else member birth_year (age band)
    days_in_india_this_fy: 40        # required
    days_in_india_prior_4_fy: 300    # needed when this year is 60-181 days
    days_in_india_prior_7_fy: 520    # needed if resident (RNOR test)
    nri_years_in_prior_10: 10        # needed if resident (RNOR test)
    liable_to_tax_elsewhere: true    # needed for an Indian citizen with Indian income > ₹15 lakh
    visiting_india: true             # default true
    left_india_for_employment_this_fy: false
    fema_resident_outside_india: true  # decides NRE exemption (s.10(4)(ii)); required if resident and NRE interest exists
  regime: null                       # null = compare and recommend; new | old to force
  usd_inr_rate: 86.5                 # INR per USD — supplied, never fetched (required)
  usd_inr_rate_basis: "IRS yearly average"   # stated in the report
  expected_filing_date: 2026-07-20   # optional; drives s.234A/B, s.234F and the regime (after the due date: new only). Default: due date
  interest:
    - { account: NRO savings, kind: nro_savings, amount_inr: 18000, tds_inr: 5616 }
    # kind: nro_savings | nro_fd | nre_savings | nre_fd | fcnr | other
  house_property:
    - { name: Pune flat, status: let_out, gross_rent_inr: 360000,
        municipal_tax_paid_inr: 12000, home_loan_interest_inr: 0, tds_inr: 0,
        co_owner_share: 1.0 }
    # status: let_out (gross_rent_inr) | deemed_let_out (expected_rent_inr) | self_occupied
    # amounts are for the whole property; co_owner_share scales them; tds_inr is yours
  capital_gains:
    - { name: listed shares, asset: listed_equity, acquired: 2019-05-10,
        sold: 2025-09-15, sale_inr: 1200000, cost_inr: 800000,
        transfer_expenses_inr: 0, stt_paid: true, tds_inr: 34375 }
    # asset: listed_equity | equity_mf | debt_mf | property | unlisted | gold
    # stt_paid is required for listed_equity / equity_mf (null stops; never assumed true)
    # sold must fall inside the financial year
    # property only: residential (needed for s.54), exemption_54_inr, exemption_54ec_inr
    # (s.54EC: ₹50 lakh per year across all sales)
    # optional, for the U.S. hand-off only: us_proceeds_usd, us_basis_usd
    # (U.S. basis uses the purchase-date rate; without it basis is emitted as null)
  insurance_maturities:
    - { policy: growth ULIP, kind: ulip, issued: 2021-03-01, matured: 2026-03-01,
        equity_oriented: true, annual_premium_inr: 300000, sum_assured_inr: 3000000,
        maturity_inr: 1750000, total_premiums_inr: 1500000, tds_inr: 0 }
    # kind: ulip | endowment | money_back; on_death: true -> always exempt
    # a ULIP is a capital gain (s.45(1B)) only when it fails the ₹2.5 lakh test;
    # failing the premium-to-sum-assured test makes it other income, floored at nil
  dividends:
    - { payer: XYZ Ltd, amount_inr: 0, tds_inr: 0 }
  deductions_old_regime: { 80c_inr: 150000, 80d_inr: 25000, other_inr: 0 }
  advance_tax_paid_inr: 0            # null -> balance "cannot be determined"
  advance_tax_instalments: null      # [{number: 1-4, amount_inr}] — needed for s.234C if advance tax > 0
  self_assessment_tax_paid_inr: 0    # null -> balance "cannot be determined"
  brought_forward_losses: { house_property_inr: 0, stcl_inr: 0, ltcl_inr: 0 }  # absent -> tax is an upper bound
```

**Status is computed, never entered.** Indian income for the ₹15 lakh tests is
the return's own total income with NRE/FCNR interest exempt.

**s.80TTA/80TTB are computed**, not entered: s.80TTA from `nro_savings`
interest; s.80TTB (resident seniors) from all taxable deposit interest.

**Loss set-off is chosen to minimise tax** within ss.70/71/74 (intra-head
first, then house property across heads, then brought-forward losses). The
freedom to choose the order rests on tribunal rulings and the report says so.

**Filing after the due date** (`expected_filing_date`) locks the return into
the new regime (s.115BAC(6)), adds s.234A interest and the s.234F fee, and stops
this year's capital losses carrying forward (s.80).

**Unknown is not zero.** A `null` amount, sale, cost, date, premium or sum
assured stops the report and lists every such field. A `null` `tds_inr`,
`advance_tax_paid_inr` or `self_assessment_tax_paid_inr` does not stop it: the
tax is computed and the refund or balance is reported as "cannot be
determined". Unknown Indian citizenship stops it when citizenship decides the
status (deemed residence, the employment-leaver rule). A required prior-year day count that is `null` stops the report
only when it decides the status.

**Stops rather than guesses** when: more than two homes are `self_occupied`;
s.54 is claimed on a sale not marked `residential: true`; a ULIP outside
s.10(10D) lacks `matured` or `equity_oriented`; a `kind`/`asset`/`status` is not
in the lists above; `usd_inr_rate` is not positive; a sale or maturity date
falls outside the financial year; a day count is out of range; an advance-tax
instalment is malformed; the financial year predates the shipped tables.

**Refused** (top-level keys under `india_tax_return`): `business_income`,
`salary`, `vda`, `crypto`, `clubbing`, `foreign_income`; s.54F/54B claims on a
capital-gains row. `agricultural_income_inr` is flagged, not computed.

**U.S. hand-off.** The report emits a `tax_return.foreign` block in the
shape `federal-tax-return` reads: `interest` (NRE/FCNR included — India-exempt
is still U.S.-taxable), `dividends`, `qualified_dividends` (`null` when there
are dividends — holding period not recorded), `capital_transactions` (listed
shares, property, unlisted shares, gold; U.S. term by >1-year holding;
`basis: null` unless `us_basis_usd` is recorded), `rent` (gross — the federal
skill refuses it and points to `passive-loss-eligibility`) and
`foreign_tax_paid: {passive, general: 0}` (Indian tax finally borne). Indian
fund units (PFICs) and insurance maturities are left out and listed. Amounts
use the one supplied rate and cover the Indian financial year; re-split to the
U.S. calendar year before using them.

---

## `llc_returns` — required by `llc-tax-return`

One entry per LLC, for the year in `tax_return.tax_year`. Figures are the
LLC's own books for that year, in nominal dollars; a calendar tax year is
assumed.

```yaml
llc_returns:
  - name: Example Studio LLC
    state: CA                       # state of organization / registration
    classification: partnership     # disregarded | partnership | s_corp
    s_election_effective: null      # required for s_corp (Form 2553 date)
    formed_on: 2026-02-10
    owners:                         # shares sum to 1; member = household id or a label
      - { member: a1, share: 0.4, active: false, material_participation: false }
      - { member: m3, share: 0.6, active: true, material_participation: true }
      # spouses' disregarded LLC only: se_share splits the Schedule C (default share)
    accounting_method: cash         # cash | accrual
    gross_receipts: 310000
    returns_and_allowances: 4000
    cost_of_goods_sold: 0           # one figure; inventory detail is refused
    other_income: 0
    interest_income: 0              # optional; separately stated on the K-1
    dividend_income: 0              # optional
    expenses: { rent: 36000, supplies: 12000, software: 18000 }   # category: amount
    meals: 3000                     # before the 50% limit
    home_office: { method: actual, amount: 2400 }   # or { method: simplified, sq_ft: 200 }
    vehicle: { method: standard, business_miles: [4000, 5000] }   # or { method: actual, amount: 3800 }
    startup_costs: { incurred: 54000, business_began: 2026-03-01 }
    organizational_costs: 4000
    depreciation: 22000             # the amount from depreciation-election
    sstb: false                     # §199A items passed to the owners
    ubia: 40000
    contractors:
      - { name: Dana Wu, amount: 24000, w9_on_file: false, entity_type: individual }
      # entity_type: individual | sole_proprietor | partnership | llc |
      #              corporation | s_corp | c_corp; attorney: true always reports
      # paid_via: card | third_party_network → Form 1099-K, not 1099-NEC
    guaranteed_payments: [ { member: m3, amount: 180000 } ]   # partnership only
    officer_wages:                                            # s_corp only
      - { member: a2, amount: 30000, federal_withheld: 3000, ss_withheld: 1860,
          medicare_withheld: 435 }
    payroll_taxes_employer: 2337    # s_corp only: employer FICA + FUTA + state
    reasonable_salary_floor: null   # s_corp, optional: ASSERTED comparable pay
    distributions: [ { member: m3, amount: 10000 } ]
    owner_basis_start: [ { member: a1, amount: 8000 } ]   # optional; outside / stock+debt basis
    contributions: [ { member: a1, amount: 0 } ]          # optional; capital put in this year
    prior_year_results: [ { year: 2025, net: -4000 } ]    # optional; §183 test
    estimated_payments: [800, 0, 0, 0]   # California entity payments, by slot
    prior_year_fee: null            # CA: last year's LLC fee (penalty safe harbor)
    did_business_in_short_year: null   # CA: first year of 15 days or less only
```

| Field | Effect |
|---|---|
| `classification` | Decides the return: Schedule C figures (no entity return), Form 1065, or Form 1120-S. A two-owner `disregarded` LLC is accepted only for spouses in a community property state (Rev. Proc. 2002-69, read from `household.members` roles and `meta.jurisdiction.state`); a one-owner partnership is an error. `c_corp` is refused |
| `owners[].active` | General vs limited partner for SE (§1402(a)(13)). Partnership: decides box 14A (share of income plus guaranteed payments when `true`, guaranteed payments only when `false`) and box 19 code F (partner providing services, 2025 instructions) or A; `null` is listed. S corp: `false` exempts the owner from the reasonable-compensation check |
| `owners[].material_participation` | §469 material participation, passed to `tax_return.k1[]`. Separate from `active`: a limited member can still materially participate. `null` is listed, and `federal-tax-return` stops on it; `false` sends the K-1 to `passive-loss-eligibility` |
| `owners[].se_share` | Spouses' disregarded LLC (Rev. Proc. 2002-69) only: splits the Schedule C between them (§1402(a)(5)(A)); defaults to `share`. Must sum to 1 |
| `expenses` | Any category names. Known names map to their line (advertising, commissions_and_fees, contract_labor, employee_benefit_programs, insurance, mortgage_interest, interest, legal_and_professional, office_expense, retirement_plans, rent_vehicles_equipment, rent, repairs, supplies, taxes_and_licenses, travel, utilities, wages, bad_debts); others are other expenses / other deductions |
| `vehicle.business_miles` | A number, or a list with one entry per rate period when the IRS changed the rate mid-year (2026: Jan–Jun, Jul–Dec). One total in a split year uses the lower rate and says the deduction is a lower bound |
| `startup_costs.business_began` | The month amortization starts, and the month organizational costs start too. Before the tax year ends nothing is deductible |
| `depreciation` | A number. Asset detail (a list or mapping) is refused with a pointer to `depreciation-election`. `null` is listed and net income becomes an upper bound |
| `contractors` | 1099-NEC at or above the year's threshold ($600 for 2025 payments, $2,000 from 2026), except corporations unless `attorney: true`, and except `paid_via: card` / `third_party_network` (Form 1099-K). `w9_on_file: false` → 24% backup withholding flag; absent or `null` → listed and bounded. `null` list = cannot be determined |
| `officer_wages[]` | `ss_withheld` and `medicare_withheld` feed the W-2 hand-off in `federal-tax-return`'s field names (`ss_wages` = wages up to the wage base, `medicare_wages` = wages). Absent withholding is unknown, not zero |
| `contributions` | Increase basis before distributions; with nondeductible expenses (the disallowed half of meals, K-1 18C / 16C) decreasing it before losses (Reg. §1.1367-1(f)) |
| `prior_year_fee` | No 10% fee-estimate penalty if the timely estimate is at least last year's fee (Form 568 booklet, General Information G). Absent after the first year: the penalty is an upper bound |
| `did_business_in_short_year` | A first taxable year of 15 days or less with no California business owes no return, $800 or fee (R&TC §17946). `null` keeps the $800 as an upper bound |
| `owner_basis_start` | Partnership outside basis (including share of liabilities) or S-corp stock plus debt basis at the start of the year. Missing or `null` makes the loss and distribution checks bounded |
| `estimated_payments` | California payments by slot. Form 568: slot 1 is the $800 (FTB 3522), slot 2 the timely LLC fee estimate (FTB 3536, due the 15th day of the 6th month of the LLC's taxable year — counted from formation in the first year, and not due at all if that year ends first); the 10% penalty is tested against slot 2. Form 100S: the four 100-ES installments (required cumulatively 30/70/70/100%, the first at least $800; a tax of $800 or less is all due with the first). `null` leaves the balance undetermined |

**Absent, zero and `null`.** As for `tax_return`: absent is none, `0` is
checked and zero, `null` is nobody looked. A `null` that determines income
(receipts, COGS, an expense, `meals`, guaranteed payments, officer wages,
`payroll_taxes_employer`) stops that LLC; other `null`s are listed and bound
the affected check.

**Refused** (that LLC stops with a pointer): `rental`, `rental_properties`,
`real_estate` or `activity: rental`; `assets`, `section_179` or asset-level
`depreciation`; `inventory`; `apportionment`, `other_states`;
`special_allocations`, `section_754`, `section_704c`; `payroll_filings`;
`withholding_1446` or an owner with `foreign: true`; an entity owner of an S
corporation; an S election effective after the first day of the year.

**Hand-off.** The report prints rows to paste: `tax_return.schedule_c[]`
(disregarded), `tax_return.k1[]` with `{owner, entity, form, ordinary_business_income,
guaranteed_payments, se_earnings, interest, dividends, distributions,
qbi_income, qbi_w2_wages, qbi_ubia, sstb, material_participation}`
(partnership, S corp), officer W-2s for `tax_return.w2[]`, and
`tax_return.ca.llc[]` for a disregarded California LLC.

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
    - id: windfall-inheritance  # stable scenario/deployment join key
      label: Inheritance from Ana's aunt
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
  # Provenance only; values remain in their existing fields below.
  annual_parameter_metadata:
    federal_tax:
      tax_year: 2026
      verified_on: null             # ISO date after checking every active field
      sources: []                    # exact primary-authority URLs
    business_tax: { tax_year: 2026, verified_on: null, sources: [] }
    healthcare: { tax_year: 2026, verified_on: null, sources: [] }
    pfic_rates: { tax_year: 2026, verified_on: null, sources: [] }
    household_tax: { tax_year: 2026, verified_on: null, sources: [] }

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

`annual_parameter_metadata` attests to the tax year, verification date, and
sources without duplicating any value. The `reference-data-refresh --facts`
audit activates a group only when at least one of its governed fields is
present, prints no private values, and requires official groups to cite exact
URLs. `verified_on` means every active value in that group was checked; do not
date a partial review. Household-specific rates may cite a return, tax-software
projection, marketplace quote, or professional rather than a public URL.

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

## `tax_planning` — filed-return history and the current projection

This section records actual filed-return totals separately from the current
year's projection. `tax-planning` uses the history as a baseline, then tests
current contribution, taxable-lot, charitable, and retirement facts for
specific planning opportunities.

```yaml
tax_planning:
  returns:
    - tax_year: 2024
      filing_status: married_joint
      state: TX
      adjusted_gross_income: 163000
      taxable_income: 132000
      federal_total_tax: 23800
      state_income_tax: 0
      payments: 22500                 # optional; federal + state payments
    - tax_year: 2025
      filing_status: married_joint
      state: TX
      adjusted_gross_income: 172000
      taxable_income: 141000
      federal_total_tax: 26000
      state_income_tax: 0
      payments: 24000

  current_year:
    tax_year: 2026
    filing_status: married_joint
    state: TX
    projected_adjusted_gross_income: 155500
    projected_taxable_income: 125500
    projected_federal_total_tax: 24000
    projected_state_income_tax: 0
    projected_payments: 22000

    # Optional strategy inputs. Supply them from current tax software or a
    # professional; the skill will not reconstruct return-level netting.
    retirement_contribution_state_deductible: false
    remaining_roth_deferrals: 0       # future payrolls only; past Roth is fixed
    hsa_state_deductible: false
    loss_harvest_usable_amount: 3000
    loss_harvest_marginal_rate: 0.188
    target_ordinary_bracket_top: 200000
    expected_future_combined_marginal_rate: 0.30
    roth_conversion_state_taxable: false
```

`federal_total_tax` and `state_income_tax` are liabilities, not withholding.
`payments` and `projected_payments` are kept separate because refund size is a
payment-timing result, not a measure of tax efficiency. Historical rows must
be unique tax years; gaps remain gaps and are never interpolated.

`filing_status` and `state` are repeated on every row deliberately. A move or
status change can explain a rate change; hiding those dimensions makes unlike
years look comparable. The report keeps the figures visible but warns against
interpreting the rate movement as planning performance.

`loss_harvest_usable_amount` is the portion of a newly harvested loss that tax
software says can affect the current return after carryforwards and gain/loss
netting. `loss_harvest_marginal_rate` is the rate applicable to that next loss.
Supplying these two values avoids embedding an incomplete capital-gain netting
engine or assuming a statutory ordinary-loss limit.

The two state-deduction flags are explicit because retirement and HSA treatment
varies by state. Omitted means the estimate reports a federal-only floor. The
`remaining_roth_deferrals` figure excludes contributions already made, which
cannot be changed retroactively. The Roth fields create a scenario, not a
recommendation: the skill considers it
only after retirement, in a projected low-income year, and reports the current
tax cost separately from the undiscounted possible future benefit.

Return history is highly sensitive. Keep it only in gitignored
`inputs/facts.yml`; the public example contains fictional values.

## `history` — immutable local snapshots

History has its own `history_schema_version`; it is not a new meaning for any
facts-schema field. The facts file stores only the local files selected for a
review:

```yaml
history:
  snapshot_files:
    - history/2026-03-31.yml
    - history/2026-06-30.yml
  selected_metrics:                 # optional; omission means all metrics
    - household.net_worth
    - emergency_fund.months_held
```

Paths are local. Nothing uploads, fetches, or treats git history as financial
data. Run `scripts/history.py` from the repository root so relative paths have
one unambiguous base.

### Snapshot document

One immutable file represents one complete, partial, analysis, or restatement
snapshot:

```yaml
history_schema_version: 1
snapshot_id: s2026-06-30
kind: complete                     # complete | partial | analysis | restatement
effective_date: 2026-06-30         # when the facts were true
observed_at: 2026-07-02            # when the household obtained/entered them
completeness: complete             # complete | partial
facts:                             # retained for a current-model rerun
  meta: {schema_version: 1, as_of: 2026-06-30, currency: USD, ...}
  household: {...}
observations: [...]
analyses: [...]
restatements: []
notes: []
```

A complete or partial facts snapshot retains an independent copy of the facts;
an analysis snapshot can instead name `source_snapshot_id`. A partial snapshot
may carry account observations, but a household total such as net worth must be
an explicit unknown. Missing values are never zero and are never carried to the
next date.

The kinds are exclusive: complete/partial documents contain observed metrics,
analysis documents contain structured results, and restatement documents
contain corrections. Keeping them in separate files prevents a report rerun
from being mistaken for a newly observed household fact.

Capture is explicit and refuses to overwrite an existing file. To correct an
old value, `scripts/history.py restate` writes a separate document containing
the original observation, corrected observation, reason, and `corrected_at`.
The original file and originally reported value remain intact.

### Metric protocol

Every structured metric uses:

```yaml
- metric_id: household.asset_balance       # stable, machine-readable
  effective_date: 2026-06-30
  value: 90000                              # or null plus unknown_reason
  unit: currency                            # currency | ratio | months | years ...
  currency: USD                             # required only for currency
  basis: nominal                            # nominal | real | nonmonetary
  scenario: observed                        # observed/current/conservative/stress/...
  source: household.balance_sheet
  clock: observed                           # observed | analysis | projection
  status: measured                          # measured | derived | projected | unknown
  entity_id: acct-brokerage                 # stable join key
  display_label: Meridian Investments       # may change without breaking history
  observed_at: 2026-07-02
  data_quality: complete                    # complete | partial | estimated | unknown
  dimensions: {}
```

Analysis and projection metrics replace `observed_at` with `calculated_at` and
require `model_version`. They may also record `inputs_fingerprint`,
`assumptions_fingerprint`, `reference_version`, and flow-based `attribution`.
A projection's future date never becomes an observation. Re-running old facts
under current code creates analysis history, not the report that existed then.

Comparability requires the same metric ID, clock, unit, currency, basis,
scenario, stable entity ID, and dimensions. Current and conservative cases on
one date remain distinct. Nominal and real dollars, different currencies, and
different FX conversion-date dimensions are rejected unless a separate,
recorded normalization creates a common series.

Finding records use stable `finding_id`, `source_skill`, `state`, severity,
original text, `calculated_at`, `model_version`, optional transition reason,
and one of `household`, `facts`, `assumptions`, `reference_data`, `model`, or
`unknown` as `change_driver`. Supported states are `unobserved`, `open`,
`improved`, `closed`, `worsened`, and `superseded`. A changed result on the same
input fingerprint with a different model version is methodology, not progress.

Existing users start with the first truthful snapshot; they do not fabricate
prior dates. A dated Markdown report can be transcribed into a structured
analysis snapshot with its uncertainty labeled, but it is not parsed
automatically because that import is necessarily lossy.

The first numeric skill adapters are maintained in `lib/pf/skill_metrics.py`:
emergency fund, employer concentration, retirement readiness, housing
affordability, education funding, survivor need, life insurance, and disability
insurance. Capture itself supplies net worth, account balance, cash reserve,
income, spending, and retirement saving. Other review outcomes still have
stable qualitative finding IDs and can add metrics without owning storage or
charting.

## `scenario_planning` — deterministic what-if paths

A scenario is never a fact. It selects a recorded named cash-flow baseline,
applies typed events by month, and produces a projection under explicit
assumptions:

```yaml
scenario_planning:
  objective: preserve_liquidity       # optional; compare_only declares no rank
  scenarios:
    - id: job-loss-12m
      label: Primary earner unemployed for twelve months
      baseline: current
      kind: stress                     # scenario | stress | sensitivity
      as_of: 2027-01-01
      horizon_months: 60
      currency: USD
      basis: nominal                   # nominal | real
      essential_spending_annual: 71100 # explicit; never inferred from current
      liquidation_order: [cash-main, taxable-brokerage]
      market_return_annual: 0          # optional, deterministic
      retirement_return_annual: 0      # optional, deterministic
      preliminary: false               # windfall planning before pause expires
      events:
        - id: primary-separation
          type: employment_loss
          person_id: p1
          start_month: 1
          duration_months: 12
          after_tax_income_loss_monthly: 8500
          employee_contribution_loss_monthly: 1800
          employer_match_loss_monthly: 450
          severance_after_tax: 24000
          severance_month: 1
          unemployment_after_tax_monthly: 1700
          benefit_start_month: 2
          benefit_duration_months: 6
          replacement_health_cost_monthly: 1200
          unvested_forfeiture: 38000
          employer_stock_change: -0.50
```

`as_of` is the calculation date and month offsets are one-based. Duration is in
months; omission means ongoing except where a focused skill explicitly reports
it unknown. Money is in `currency` and `basis`. Every event must match both;
convert explicitly before combining currencies or nominal/real amounts.
`essential_spending_annual` is optional and remains unknown when omitted; the
job-loss wrapper never assumes a percentage cut. `liquidation_order` records
intent but does not itself sell anything—each sale still needs an explicit
withdrawal event and its tax treatment.

The monthly cash reconciliation is:

```text
opening cash
+ after-tax income and explicit inflows
- current spending
- employee retirement contributions
- other explicit outflows
= closing cash
```

`debts` must be present, using `[]` when there are none, and every recorded debt
needs a balance. Missing liabilities cannot be treated as zero in a net-worth
path.

Employer contributions increase retirement assets but never reduce household
cash. Market changes create no cash. Portfolio transfers change liquidity, not
net worth. A down payment exchanges cash for home equity; the mortgage creates
equal property and debt, while closing cost reduces net worth. No automatic
asset sale, spending cut, refinancing, family help, or retirement withdrawal is
assumed.

### Event fields

The serialized schema uses typed fields rather than executable or generic
expression maps. YAML is loaded safely and the engine never calls `eval`.

- `employment_loss`: requires `person_id`, `start_month`, and
  `after_tax_income_loss_monthly`; supports the duration, employee contribution,
  employer match, severance month/amount, benefit start/duration/amount,
  replacement health cost, unvested forfeiture, and employer-stock percentage
  shown above. Missing optional job-loss facts are reported as unknown, not zero.
- `compensation_change`: `start_month`, optional `duration_months`,
  `after_tax_income_change_monthly`, and
  `retirement_contribution_change_monthly`. Use a negative amount for a step
  down; it does not infer a tax rate from gross compensation.
- `cash_receipt`: `source_event_id` plus either `after_tax_amount`, or both
  `gross_amount` and `tax_reserve`. Reserve may be an explicit zero.
  Withholding is not liability.
- `asset_receipt`: `source_event_id`, `market_value`, `asset_type`, `cost_basis`, `holding_period`,
  `restriction_status`, `tax_rate`, `transaction_cost`, and `liquidate`.
  Liquidation requires basis and tax rate; retaining an asset permits unknown
  sale inputs but names every gap and never calls its value cash.
- `asset_price_change`: `target` (`marketable` or `employer_stock`) and signed
  `price_change`. A decline changes value and produces no cash.
- `one_time_expense`: positive `amount` in its `start_month`.
- `recurring_expense_change`: signed `amount_monthly`, `start_month`, and
  optional duration.
- `debt_payoff`: positive `amount` and optional `payoff_penalty`; principal
  reduces cash and debt equally, while the penalty reduces net worth.
- `portfolio_contribution`: positive `amount`, optional `transaction_cost`, and
  optional stable `account_id`; cash becomes marketable assets.
- `portfolio_withdrawal`: positive `amount`, optional explicit `tax_reserve`,
  `transaction_cost`, and account ID; no tax is inferred.
- `home_purchase`: either explicit `purchase_price`, `down_payment`,
  `closing_cost`, and `monthly_housing_cost_change`, or
  `housing_adapter: true`. The adapter reuses the recorded
  `housing.purchase` cash ledger and replaces rent exactly once.

The deterministic same-month order is receipts, employment/compensation,
asset repricing, expenses, withdrawals, debt payoff, home purchase, then
portfolio contributions. YAML list order cannot change the answer. Multiple
home purchases in one month, a contribution and withdrawal for the same
account/month, or two employer-stock repricings are rejected as ambiguous.
Windfall receipt events also require `source_event_id` matching exactly one
`transitions.windfall[].id`, and their gross value must reconcile. Labels are
display text and never join keys. Legacy windfall reports still work without an
ID; deployment scenarios do not.

Supported objectives are `preserve_liquidity`, `preserve_savings`,
`minimize_debt`, `minimize_retirement_delay`, `preserve_goal`, and
`compare_only`. An absent or mixed objective produces no winner. Results expose
baseline and scenario monthly paths, minimum cash and month, reserve-floor
breaches, saving during and after the event, retirement target age, terminal
liquidity/net-worth changes, an isolated-event bridge plus residual, the
binding constraint, unknowns, and recovery conditions. They also emit
projection-clock observations using the history metric protocol.

The first release is deterministic. It deliberately excludes Monte Carlo,
probabilities, market/FX fetching, a tax-return engine, individual-security
recommendations, execution, and automatic fact/result mutation.

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
