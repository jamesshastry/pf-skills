---
name: digital-estate
description: Audit whether anyone could actually access the household's accounts — password manager emergency access, a written account inventory, and two-factor recovery. Use when asked about digital estate planning, what happens to online accounts on death or incapacity, or as the practical complement to a will. Reads figures from a local facts file.
requires:
  - household.members
---

# Digital estate

## The problem in one sentence

Every other estate document assumes someone can **reach** the accounts.

Good security practice and good estate practice pull in opposite directions:
two-factor authentication and a strong password manager lock out heirs exactly
as effectively as they lock out attackers. A household can have a perfect will,
current powers of attorney, and clean beneficiary designations, and still leave
a survivor unable to log in to anything.

## The blocker worth naming loudly

**A password manager with no emergency access configured is a single point of
failure, not a plan.**

Every credential is in one place and nobody else can reach it. This is *worse*
than having no manager at all, because it creates the belief that the problem
is solved. The report treats this combination as a blocker rather than a gap
for that reason.

Configuring legacy or emergency access is usually a few minutes of work and it
converts the vault from a lockbox into a plan. It is the highest-value single
setting in this whole review.

## The test

Not *does a plan exist*, but:

> **Could the person you have in mind actually log in tomorrow, without you,
> using only what they can find?**

Most households fail this while believing they pass. Walk the path end to end
once — actually attempt the recovery — rather than assuming it works.

## What it checks

| Check | Why |
|---|---|
| Password manager | Credentials exist in one recoverable place |
| **Emergency access configured** | Someone can actually get in |
| Written account inventory | A survivor cannot claim what they don't know exists |
| 2FA recovery codes recorded | The second factor doesn't become the barrier |

## Things worth raising that aren't in the checks

**Platform-level inheritance tools exist and are off by default.** Legacy
contacts and inactive-account handlers are per-platform, independent of
anything in the will, and take minutes to set.

**Terms of service frequently make accounts non-transferable.** An executor may
have a clear legal right to the *value* of an asset and no right at all to the
account holding it. This bites hardest on anything purely digital.

**The recovery path must not require the credentials being recovered.** A
printed sheet stored with the will beats anything clever. Circular dependencies
here are common and fatal.

## Closing

1. **The blocker, if present** — vault without emergency access.
2. **The one-sentence test**, put to the user directly.
3. **Suggest actually walking the path**, not just recording that a plan exists.
4. **Store the result with the will**, since that is where someone will look.

---

*Not financial, tax, or legal advice. Platform access rules vary and change.*
