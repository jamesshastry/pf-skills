#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Which assets go through court, what it costs, and the cheapest way out."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, probate as P  # noqa: E402

REQUIRED = [
    "meta.jurisdiction.state",
    "household.members",
    "household.balance_sheet",
]
m = cli.money

VERDICT = {P.AVOIDS: "✅ avoids", P.PROBATE: "🚫 **probate**",
           P.UNDETERMINED: "· cannot be determined"}


def build(data: dict, w: cli.Writer) -> None:
    state = F._dig(data, "meta.jurisdiction.state")
    members = F._dig(data, "household.members") or []
    rows = F._dig(data, "household.balance_sheet") or []
    docs = F._dig(data, "estate.documents") or []
    by_type = {d.get("type"): d for d in docs}
    trust = by_type.get("revocable_trust") or {}
    trust_exists = bool(trust.get("exists"))
    trust_funded = trust.get("funded")

    e = P.assess(rows, state=state)

    w("**A pour-over will does not avoid probate.** It directs whatever is "
      "left into the trust on death — it fixes the *destination*, not the "
      "*route*. Anything still titled in an individual name goes through "
      "court first and lands in the trust afterwards, having paid for the "
      "trip. Households with a drafted trust routinely assume they are "
      "covered here and are not.")
    w()
    w(f"Jurisdiction: **{state}**"
      + ("" if e.rules.known else " — not in the cited table"))

    # ── per account ─────────────────────────────────────────────────────
    w()
    w("## Every account, and where it goes")
    w()
    def shown(r) -> str:
        """Three different blanks, kept apart deliberately.

        "not applicable" is an answer, "checked — none named" is a defect, and
        "not recorded" means nobody looked. Rendering all three as an empty
        cell is how a reader concludes the wrong thing from a correct table.
        """
        if r.designation_state == P.NOT_APPLICABLE:
            return "*not applicable*"
        if r.designation_state == P.NONE_NAMED:
            return "**checked — none named**"
        if r.designation:
            return f"`{r.designation}`"
        return "*not recorded*"

    w.table(
        ["Account", "Titling", "Primary designation", "Value", "Verdict"],
        [[r.label,
          f"`{r.titling}`" if r.titling else "*not recorded*",
          shown(r), m(r.value), VERDICT[r.verdict]] for r in e.routes])
    w()
    for r in e.routes:
        if r.verdict != P.AVOIDS:
            w(f"- **{r.label}** — {r.why}")

    # ── the totals ──────────────────────────────────────────────────────
    w()
    w("## What is exposed")
    w()
    if e.exposed:
        w(f"**{m(e.exposed_total)} across {len(e.exposed)} account(s)** will "
          "pass under the will and through probate on the recorded facts.")
    else:
        w("**No account is positively exposed** on the recorded facts.")
    if e.undetermined:
        w()
        w(f"A further **{m(e.undetermined_total)} across "
          f"{len(e.undetermined)} account(s) cannot be determined** — the "
          "titling, the designation, or both have never been recorded. That "
          "is not a small residual: it is the width of the answer. The real "
          f"figure is somewhere between {m(e.exposed_total)} and "
          f"{m(e.upper_total)}, and closing that gap costs phone calls "
          "rather than money.")

    # ── the cost ────────────────────────────────────────────────────────
    w()
    w("## What that costs")
    w()
    for finding in e.findings:
        w(finding)
        w()
    lo = P.cost(e.exposed_total, e.rules)
    if lo.computable and lo.small_estate:
        w(f"**Effectively nothing.** {lo.detail}")
    elif lo.computable:
        w(f"**{m(lo.total)}** on the exposed total.")
        w()
        w(lo.detail)
    elif e.rules.known:
        w(lo.detail)

    if e.undetermined and e.rules.known:
        hi = P.cost(e.upper_total, e.rules)
        if hi.computable and not hi.small_estate:
            w()
            w(f"If everything unchecked turns out to be exposed, "
              f"**{m(hi.total)}** — {m((hi.total or 0) - (lo.total or 0))} "
              "more than the figure above. That difference is what not "
              "having looked is worth.")

    if e.rules.known and e.rules.basis == P.STATUTORY_PERCENTAGE:
        w()
        w("| Band | Rate |")
        w("|---|---|")
        prev = 0
        for bound, rate in e.rules.fee_schedule or ():
            if rate is None:
                w(f"| above {m(prev)} | set by the court |")
                break
            w(f"| {m(prev)} – {m(bound)} | {rate:.1%} |")
            prev = bound
        w()
        w("Shown so it can be checked rather than believed.")

    # ── spousal shortcut ────────────────────────────────────────────────
    w()
    w("## The spousal shortcut")
    w()
    w(P.spousal_note(e.rules,
                     will_pours_to_trust=F._dig(data, "estate.will_pours_to_trust")))

    # ── the fixes ───────────────────────────────────────────────────────
    fixes = P.recommend(e.routes, members=members, trust_exists=trust_exists)
    if fixes:
        w()
        w("## The cheapest fix, per account")
        w()
        w("**Not a blanket recommendation.** The right instrument depends on "
          "the tax wrapper, and the two rules point in opposite directions: a "
          "taxable account belongs in the trust, while a **retirement** "
          "account names the spouse directly, because a trust as primary "
          "generally forfeits the spousal rollover and forces a roughly "
          "ten-year payout. Optimising only for probate would recommend the "
          "trust for both and cost a surviving spouse decades of deferral.")
        w()
        for f in fixes:
            w(f"**{f.label}** — {f.instrument}")
            w()
            w(f"> {f.rationale}")
            if f.withheld:
                w(">")
                w(f"> ⚠️ **Withheld on suitability.** {f.withheld}")
            w()

    # ── caveats ─────────────────────────────────────────────────────────
    w("## What this does not do")
    w()
    if trust_exists and trust_funded is False:
        w("- **A trust exists and is recorded as unfunded.** Every account "
          "above that is not titled to it is the funding that was never "
          "done. See `estate-document-review`.")
    w("- It does not check whether a designation is *coherent* — missing "
      "contingents, shares that do not total 100%, a minor named directly. "
      "That is `beneficiary-audit`, and it is the other half of this.")
    w("- It does not decide whether joint titling is appropriate. Adding a "
      "joint owner is a completed gift in many cases, exposes the asset to "
      "that person's creditors and divorce, and can forfeit a step-up in "
      "basis. It avoids probate; that is not the same as being a good idea.")
    w("- Probate cost here is ordinary fees only. Extraordinary fees, filing "
      "costs, appraisal, bond and the value of the delay are all real and "
      "none are in the figure.")
    w()
    w(f"**Weakest input:** the `titled_to` field. It is the one thing that "
      f"decides every verdict above, it is not on any statement, and "
      f"{len(e.undetermined)} of {len(e.routes)} account(s) do not have it "
      "recorded. A deed or registration says what it says regardless of what "
      "anyone remembers signing.")
    cli.disclaimer(w, "lib/pf/probate.py")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Probate exposure",
                             required=REQUIRED, build=build))
