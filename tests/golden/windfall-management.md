# Windfall management

## Do nothing for ninety days

**Do nothing irreversible for another 44 day(s).** 1 of 2 events are inside the 90-day window. Park the money somewhere safe and liquid, decline every opportunity, and let the urgency pass. Nothing on this list — not a house, not a business, not a loan to a relative, not an annuity — gets worse by waiting three months, and the decisions people regret are made in the first one. The only things worth doing now are the reversible ones: park it, cover the tax, name beneficiaries.

**$355,000** across 2 event(s).

| Event | Amount | Kind | Income on receipt? | Basis | Pause |
|---|---|---|---|---|---|
| Inheritance from Ana's aunt | $260,000 | `inheritance` | no | stepped up | **44d left** |
| Northwind RSU vest | $95,000 | `equity_vest` | yes | unchanged | elapsed |

|  | Amount |
|---|---|
| Taxable on receipt | $95,000 |
| Estimated federal tax | $22,800 |
| Withheld | $20,900 |
| Shortfall | $1,900 |
| Prior-year safe harbour | $41,800 |

## Tax character

- **Inheritance from Ana's aunt** — An inheritance is **not income** to the recipient. Assets acquired from a decedent generally take a basis equal to fair market value at the date of death, so the decedent's unrealised gain is erased and only appreciation *after* that date is taxable on sale. Two consequences people miss: selling immediately is usually close to tax-free, and holding a concentrated inherited position for sentimental reasons is a concentration decision being made by default. Note that an inherited *retirement account* is the opposite case — no step-up on pre-tax balances, and distributions are ordinary income under the 10-year rule.

- **Northwind RSU vest** — RSUs vesting at or after an IPO are **ordinary wage income** at vest, reported on the W-2, with basis equal to the amount included. There is no step-up and no preferential rate. Shares held afterwards start a fresh holding period from the vest date, so selling within a year of vest produces a short-term gain on top of income already taxed.

## Tax and withholding

- ⚠️ **About $22,800 of federal tax on $95,000 of taxable receipt** at 24%. Federal only, nominal, and a floor: state tax, NIIT on investment income, and the bracket this pushes you into are all on top. Against $20,900 withheld, the gap is **$1,900**.

- ⚠️ **Supplemental withholding is 22%, which is a withholding rate and not your tax rate.** On $95,000 of vesting equity that withholds about $20,900. At a 24% marginal rate the shortfall is roughly **$1,900** before state tax — invisible on the pay stub, and payable in April.

- **The prior-year safe harbour is $41,800** (110% of last year's $38,000 tax, via withholding plus estimated payments across the year). Meet it and the §6654 underpayment penalty does not apply however large the final bill turns out to be — which matters because in a windfall year nobody can yet compute the current-year figure. The alternative harbour is 90% of the current year's tax. Estimated payments are quarterly and the penalty is assessed per quarter, so a single catch-up payment in January does not cure an underpaid Q3.

## Where it sits meanwhile

- $355,000 exceeds the $250,000 FDIC limit — per depositor, per insured bank, per ownership category. 'Safe and liquid' means insured or Treasury-backed, which in practice means splitting across banks, or a Treasury money market fund, or direct bills. Brokerage SIPC coverage ($500,000, of which $250,000 cash) is **not the same thing** — it covers the custodian failing, not the investments falling. See `cash-yield-review` for where the parked money should actually sit; parking it is not the same as leaving it at 0.01%.

## Reporting

- ⚠️ **Form 3520 is required.** $260,000 of gifts or bequests from a foreign person exceeds the $100,000 aggregate threshold. **No tax is due** — this is reporting only — but the penalty for not filing is a percentage of the amount received, which makes it one of the most expensive forms to overlook. It is due with the return, and an inheritance from family abroad is the ordinary trigger. See `foreign-reporting-audit`, which also covers the FBAR and FATCA consequences of the account the money landed in.

## Beneficiaries

- **Name a beneficiary on every account the money touches, including the one it is merely parked in.** New accounts are the commonest source of an unrevised estate plan, because nobody thinks of a holding account as part of one. `beneficiary-audit` does the checking.

## The weakest input

**`kind`.** Everything above is downstream of it, and it is the one field a user fills in from memory rather than from a document. An inheritance that is actually an inherited IRA, or a settlement recorded without its allocation, produces a confident answer that is wrong by the whole tax bill.

## What this will not do

- **Tell you what to buy.** That is the next conversation, after the ninety days, and it is `portfolio` work rather than transition work.
- **Compute state tax, NIIT, or the bracket this pushes you into.** Every figure here is federal, nominal, and a floor.
- **Characterise a settlement.** That needs the allocation in the agreement, and no amount of arithmetic substitutes for it.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/transitions.py` with their reasons; every figure above is derived, not restated. The tax-character table is transcribed statute, marked unverified — check it before relying on it.*
