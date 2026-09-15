# Depreciation election

3 asset(s) placed in service, $149,000 total cost · taxable business income $204,000

**A deduction and a deduction are not the same deduction.** §179 cannot create or increase a loss and carries the excess forward; bonus depreciation can. On a vehicle, the year-one method choice also decides what is available for every year after it.

## Work SUV

$82,000 cost · 55% business use · 7,200 lb GVWR · 14,000 business miles · placed in service <DATE>

| Election | Year-one deduction | Carried forward | Limited by | Closes off mileage |
|---|---|---|---|---|
| §179 expensing | **$31,300** | — | SUV §179 cap (6,000–14,000 lb GVWR) | yes |
| Bonus depreciation | **$45,100** | — | — | yes |
| Standard mileage | **$9,800** | — | — | no |

- **Bonus depreciation can create or increase a net operating loss**, which §179 cannot. In a year where business income is thin that is the whole difference between the two elections, and it runs the other way from the usual advice: a loss is only worth creating if it can be used.

- The standard rate **already includes depreciation**, so no separate depreciation, §179 or bonus may be claimed on the same vehicle in the same year. It also reduces basis, which matters on sale.

- **Year one decides the method for the life of this vehicle — in one direction only.** Claim actual expenses with depreciation now and standard mileage is closed off for this vehicle permanently. Start with standard mileage and you may switch to actual expenses later, but only on straight line. If the two are close, the reversible choice is worth something the arithmetic does not show.

- At 7,200 lb GVWR this is above the 6,000 lb line, so the §280F passenger-auto caps do not apply and the first-year deduction can be large. **This is the most aggressively marketed deduction in small-business tax, and the marketing omits the conditions.** The vehicle must be placed in service and actually used in the business this year, above 50%, and the proof is a contemporaneous mileage log — not a reconstruction.

- **Business use is 55% — barely over the line.** One changed contract or one relocation and it drops below 50%, at which point the accelerated deduction already claimed is recaptured as ordinary income: about $36,080 on the largest election above. That arrives in a year the cash is spent and the vehicle is worth less than the tax on it. A thin margin over the test is a reason to take the smaller deduction, not the larger one.

- `actual_operating_cost` is not recorded, so actual expenses cannot be compared against the mileage figure on a like-for-like basis. The comparison above is depreciation only — fuel, insurance, repairs and registration are deductible under the actual method and are already inside the standard rate.

- No first-year method is recorded for this vehicle, so the options still open cannot be determined. It is on the return for the year it was placed in service.

## Sedan

$41,000 cost · 70% business use · 4,100 lb GVWR · 9,000 business miles · placed in service <DATE>

| Election | Year-one deduction | Carried forward | Limited by | Closes off mileage |
|---|---|---|---|---|
| §179 expensing | **$12,400** | — | §280F luxury auto first-year cap | yes |
| Bonus depreciation | **$20,400** | — | §280F luxury auto first-year cap | yes |
| Standard mileage | **$6,300** | — | — | no |

- **Bonus depreciation can create or increase a net operating loss**, which §179 cannot. In a year where business income is thin that is the whole difference between the two elections, and it runs the other way from the usual advice: a loss is only worth creating if it can be used.

- The standard rate **already includes depreciation**, so no separate depreciation, §179 or bonus may be claimed on the same vehicle in the same year. It also reduces basis, which matters on sale.

- **Year one decides the method for the life of this vehicle — in one direction only.** Claim actual expenses with depreciation now and standard mileage is closed off for this vehicle permanently. Start with standard mileage and you may switch to actual expenses later, but only on straight line. If the two are close, the reversible choice is worth something the arithmetic does not show.

- Standard mileage was taken in year one, so **both methods remain available.** Switching to actual expenses is allowed, but depreciation from then on must be straight line over the remaining recovery period, on a basis already reduced by the depreciation component of the mileage rate.

- That flexibility has a value the year-one arithmetic never shows, and it is the reason the smaller deduction is sometimes the better election.

## Large-format printer

$26,000 cost · 100% business use · placed in service <DATE>

| Election | Year-one deduction | Carried forward | Limited by | Closes off mileage |
|---|---|---|---|---|
| §179 expensing | **$26,000** | — | — | no |
| Bonus depreciation | **$26,000** | — | — | no |

- **Bonus depreciation can create or increase a net operating loss**, which §179 cannot. In a year where business income is thin that is the whole difference between the two elections, and it runs the other way from the usual advice: a loss is only worth creating if it can be used.

## Before electing anything

- **The bigger deduction is not automatically the better one.** A deduction is worth your marginal rate this year; deferring it to a year with a higher rate, or to a year where it is not wasted against a loss, can be worth more. Front-loading everything into a low-income year is the common mistake, and §179's income limit is the tax code making the same point.
- **A purchase is not a saving.** Buying an asset to reduce tax costs the full price to save the marginal rate on it. It is only worth doing if the business needed the asset anyway.
- **The records are the deduction.** A contemporaneous mileage log is what substantiates business use; a reconstruction after a notice arrives is not the same thing and is treated as such.
- **States frequently decouple** from bonus depreciation and sometimes from §179. A state deduction cannot be inferred from the federal one, and is not computed here.

## The weakest input

**Business-use percentage.** It scales every figure above, decides whether §179 and bonus are available at all, and is the first thing an examiner asks about. It is also the one input a household estimates rather than measures. Unknown is not 100%, and a percentage that is barely over 50% is a reason to take the smaller deduction — the recapture on a later drop below the line arrives in a year the cash is already spent.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/depreciation.py` with their reasons; every figure above is derived, not restated. Every year-specific figure here comes from your facts file, not from a table in this repository — the §179 limit, the bonus percentage, the auto caps and the mileage rate all change. Confirm them against irs.gov for the year the asset was placed in service.*
