# California Tax Return

## No California resident return

`tax_return.state` is **TX** for 2026, so this household does not file a California resident return (Form 540) for that year, and nothing is computed.

What would change that:

- **Moving to California, or out of it, during the year.** That is a part-year return (Form 540NR). It is not modelled here; take it to a preparer.
- **California-source income while living elsewhere** — a California rental, a California business, or wages for work done in California — can require a nonresident return (Form 540NR). Also not modelled.
- **An LLC organized, registered or doing business in California** owes the $800 annual tax and files Form 568 regardless of where its owner lives.

If the household has left California, the residency facts are reviewed by `state-domicile-exit`.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/ca_return.py` with their reasons; every figure above is derived, not restated. A workpaper for review, not a filed return.*
