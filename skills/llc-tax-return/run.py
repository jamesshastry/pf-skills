#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""LLC tax workpaper — return lines by classification, owner hand-off, 1099-NEC, California."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, llc_return as L  # noqa: E402

REQUIRED = [
    "tax_return.tax_year",
    "llc_returns",
]
m = cli.money

CLASS_LABEL = {L.DISREGARDED: "disregarded (single-member)",
               L.PARTNERSHIP: "partnership (multi-member)",
               L.S_CORP: "S corporation (Form 2553 election)"}


def s(x) -> str:
    """Signed money; unknown stays unknown."""
    if x is None:
        return "unknown"
    return f"−{m(-x)}" if x < -0.5 else m(abs(x) if abs(x) < 0.5 else x)


def flow(v) -> str:
    """A YAML flow value, whole dollars, for pasting into the facts file."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return str(round(v))
    if isinstance(v, int):
        return str(v)
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k}: {flow(x)}" for k, x in v.items()) + " }"
    text = str(v)
    return text if text.replace(" ", "").replace("_", "").isalnum() else f'"{text}"'


def _spouses(data: dict):
    members = F._dig(data, "household.members") or []
    p = [x.get("id") for x in members if x.get("role") == "primary"]
    sp = [x.get("id") for x in members if x.get("role") == "spouse"]
    return (p[0], sp[0]) if p and sp else None


def _stopped(w: cli.Writer, name: str, e: L.LLCReturnError) -> None:
    w(f"## Stopped — {name}: the inputs cannot support this workpaper")
    w()
    w(f"- {e}")
    for item in e.missing:
        w(f"- missing: `llc_returns[{name}].{item}`")
    w()
    w("See SCHEMA.md `llc_returns`. Fill this in rather than letting the skill guess.")
    w()


def render(w: cli.Writer, r: L.LLCReturn) -> None:
    w(f"## {r.name} — {r.form}")
    w()
    w(f"**Tax year {r.tax_year}**, classified as {CLASS_LABEL[r.classification]}; "
      f"state of registration: {r.state or 'not recorded'}.")
    if r.projection:
        w()
        w(f"> **Projection.** No {r.tax_year} table ships with the module; the "
          "nearest year's figures were used.")
    w()
    w("### The answer")
    w()
    if r.classification == L.DISREGARDED:
        who = " and ".join(f"{x['owner']}'s" for x in r.schedule_c)
        w(f"**No federal entity return.** Net {'profit' if r.net >= 0 else 'loss'} "
          f"of **{s(r.net)}** goes on {who} Schedule C.")
    else:
        w(f"**{r.form}** with ordinary business income of **{s(r.net)}**, passed "
          f"through to {len(r.k1)} owner(s) on Schedule K-1.")
    for line in r.se_note:
        w()
        w(line)
    w()
    for b in r.bounds:
        w(f"> {b}")
        w()

    w(f"### {r.form} lines")
    w()
    w.table(["Line", "Item", "Amount"],
            [[ln or "—", label, s(x)] for ln, label, x in r.lines])
    w()
    if r.home_office and r.classification == L.DISREGARDED:
        h = r.home_office
        w(f"Home office ({h['method']}): {m(h['amount'])} claimed, {m(h['allowed'])} "
          f"allowed against the business's income"
          + (f"; {m(h['carryforward'])} carries forward on Form 8829" if h["carryforward"]
             else "") + (f"; {m(h['lost'])} lost" if h["lost"] else "") + ".")
        w()
    if r.startup:
        rows = []
        for label, a in r.startup["parts"]:
            rows.append([label, m(a["incurred"]), m(a["immediate"]),
                         f"{m(a['amortization'])} ({a['months']} mo × {m(a['monthly'])})",
                         m(a["remaining"])])
        w(f"Start-up and organizational costs (business began "
          f"{r.startup['began'].isoformat()}):")
        w()
        w.table(["Cost", "Incurred", "Expensed now", "Amortized this year",
                 "Left to amortize"], rows)
        w()

    w("### Owner hand-off")
    w()
    if r.schedule_c:
        w("Paste into `tax_return.schedule_c` — `federal-tax-return` applies the "
          "home-office limit, SE tax and §199A from it:")
        w()
        w("```yaml")
        for row in r.schedule_c:
            w(f"- {flow(row)}")
        w("```")
        w()
        if r.ca_llc:
            w("And into `tax_return.ca.llc` for `ca-tax-return`:")
            w()
            w("```yaml")
            w(f"- {flow(r.ca_llc)}")
            w("```")
            w()
    else:
        owners = list(r.k1_boxes)
        header = ["Box", "Item"] + owners
        boxes = r.k1_boxes[owners[0]]
        rows = []
        for i, (box, label, _) in enumerate(boxes):
            codes = list(dict.fromkeys(r.k1_boxes[o][i][0] for o in owners))
            row = [" / ".join(codes), label]
            for o in owners:
                b = r.k1_boxes[o][i]
                row.append(s(b[2]))
            rows.append(row)
        w.table(header, rows)
        w()
        w("Paste each row into `tax_return.k1` for `federal-tax-return`:")
        w()
        w("```yaml")
        for row in r.k1:
            w(f"- {flow(row)}")
        w("```")
        w()
        if r.w2:
            w("Officer wages arrive on the owner's W-2 — paste into `tax_return.w2`:")
            w()
            w("```yaml")
            for x in r.w2:
                w(f"- {flow(x)}")
            w("```")
            w()

    if r.basis:
        w("### Basis and loss limit")
        w()
        w.table(["Owner", "Start", "+ Contributions", "+ Income", "− Distributions",
                 "− Nondeductible", "Loss", "Allowed", "Suspended",
                 "Gain (excess distribution)", "End"],
                [[b["member"], s(b["start"]), s(b["contributions"]), m(b["income"]),
                  s(b["distributions"]), m(b["nondeductible"]), m(b["loss"]),
                  s(b["allowed_loss"]), s(b["suspended"]),
                  s(b["excess_distribution"]), s(b["end"])] for b in r.basis])
        w()
        w("Order: contributions and income increase basis first, then distributions, "
          "then nondeductible expenses, then losses (Reg. §1.1367-1(f); "
          "§1.704-1(d)(2)).")
        w()

    if r.reasonable_comp:
        rc = r.reasonable_comp
        w("### Reasonable compensation")
        w()
        verdict = {"flag": "**Flag**", "review": "**Review**",
                   "no flag": "**No flag**"}[rc["status"]]
        w(f"{verdict} — the IRS position is that a shareholder-officer who performs "
          "services is paid wages before non-wage distributions (Rev. Rul. 74-44; "
          "Form 1120-S instructions, line 7). There is no ratio or percentage test.")
        w()
        w.table(["Owner", "Officer wages", "Distributions", "Verdict"],
                [[x["member"], m(x["wages"]), s(x["distributions"]), x["verdict"]]
                 for x in rc["rows"]])
        w()

    n = r.nec
    w("### Form 1099-NEC")
    w()
    if n["undetermined"]:
        w("**Cannot be determined** — `contractors` is not recorded.")
    elif not n["payees"]:
        w("No contractors recorded.")
        w()
    else:
        w(f"Threshold for {r.tax_year}: **{m(n['threshold'])}** per payee; due "
          f"{n['due'].isoformat()}.")
        w()
        req = {True: "required", False: "not required", None: "undetermined"}
        w.table(["Payee", "Paid", "Type", "W-9", "1099-NEC", "Backup withholding"],
                [[p["name"], s(p["amount"]), p["entity_type"] or "unknown",
                  {True: "yes", False: "no"}.get(p["w9_on_file"], "unknown"),
                  req[p["required"]], m(p["backup"]) if p["backup"] else "—"]
                 for p in n["payees"]])
        w()
        if n["de542"]:
            w(f"California also requires EDD Form DE 542 within 20 days for "
              f"individual contractors paid {m(L.CA_DE542_THRESHOLD)} or more: "
              f"{', '.join(n['de542'])}.")
            w()

    if r.ca:
        c = r.ca
        w("### California")
        w()
        if c["form"] == "568":
            if c["return_due"] is None:
                w(c["note"])
                w()
                c = None
        if c and c["form"] == "568":
            rows = [["Annual LLC tax (FTB 3522)", m(c["annual_tax"])],
                    ["Total California income (fee base)", m(c["total_income"])],
                    ["LLC fee (FTB 3536)", m(c["fee"])],
                    ["Paid (3522 + 3536 + other)", s(c["paid"])],
                    ["Balance due with Form 568", s(c["balance"])]]
            if c["fee"]:
                rows.insert(3, ["10% estimate-shortfall penalty", s(c["fee_penalty"])])
            w.table(["Form 568", "Amount"], rows)
        elif c:
            w.table(["Form 100S", "Amount"],
                    [["California net income (approximation)", s(c["ca_income"])],
                     [f"Tax at {L.CA_S_CORP_RATE:.1%}", m(c["on_income"])],
                     ["Minimum franchise tax", m(c["minimum"])],
                     ["**Tax (greater of)**", f"**{m(c['tax'])}**"],
                     ["Paid (Form 100-ES)", s(c["paid"])],
                     ["Balance due with Form 100S", s(c["balance"])]])
        if c:
            w()
            w(c["note"])
            w()

    if r.late_penalty:
        lp = r.late_penalty
        w(f"**Filing late** costs {m(lp['per_owner_month'])} × {lp['owners']} owner(s) "
          f"= {m(lp['per_month'])} per month ({lp['section']}), up to "
          f"{m(lp['maximum'])} at {L.LATE_PENALTY_MAX_MONTHS} months — even with no "
          "tax due. Each Schedule K-1 furnished late is a separate §6722 penalty.")
        if lp["small_partnership"]:
            w(" A partnership of ten or fewer individual partners sharing every item "
              "pro rata can ask for relief under Rev. Proc. 84-35 — on request, "
              "not automatically.")
        w()

    w("### Deadlines")
    w()
    w.table(["Due", "What"], [[d.isoformat(), what] for d, what in r.deadlines])
    w()
    w("Weekend due dates move to Monday; legal holidays are not modelled.")
    w()
    if r.findings:
        w("### Findings")
        w()
        for f in r.findings:
            w(f"- {f}")
        w()
    if r.missing:
        w("**Not recorded** (listed, never read as zero):")
        w()
        for item in r.missing:
            w(f"- `llc_returns[{r.name}].{item}`")
        w()


def build(data: dict, w: cli.Writer) -> None:
    year = F._dig(data, "tax_return.tax_year")
    llcs = F._dig(data, "llc_returns")
    if not isinstance(llcs, list):
        llcs = []
    spouses = _spouses(data)
    hh_state = F._dig(data, "meta.jurisdiction.state")
    w(f"Tax year {year}; {len(llcs)} LLC(s). Parameters: "
      f"{L.table_for(int(year))[0].source}.")
    w()
    for i, llc in enumerate(llcs):
        name = (llc.get("name") if isinstance(llc, dict) else None) or f"#{i}"
        try:
            r = L.compute(llc, tax_year=year, spouses=spouses, household_state=hh_state)
        except L.LLCReturnError as e:
            _stopped(w, name, e)
            continue
        render(w, r)
    w("**Weakest input:** owner basis — it decides whether a loss is deductible "
      "and whether a distribution is taxable, and it lives in records outside the "
      "year's ledger (contributions, prior K-1s, share of liabilities).")
    cli.disclaimer(w, "lib/pf/llc_return.py",
                   "This is a workpaper for checking an LLC's returns, not a filed "
                   "return; it does not e-file.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="LLC Tax Return Workpaper", required=REQUIRED,
                             build=build))
