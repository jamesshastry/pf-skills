"""Cross-skill conflict registry — review finding A6."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import conflicts as C  # noqa: E402

BASE = {"household": {"members": [{"id": "a1", "role": "primary", "age": 52}],
                      "balance_sheet": []}}


def keys(report):
    return {c.key for c in report.live}


def test_the_registry_is_not_empty():
    assert len(C.REGISTRY) >= 5


def test_every_conflict_is_fully_specified():
    for c in C.REGISTRY:
        assert len(c.skills) >= 2, c.key
        assert c.tension and c.trigger and c.resolution, c.key


def test_conflict_keys_are_unique():
    ks = [c.key for c in C.REGISTRY]
    assert len(ks) == len(set(ks))


def test_no_resolution_just_says_pick_one():
    """A conflict is two correct answers. 'Choose one' is not a resolution."""
    for c in C.REGISTRY:
        assert "pick one" not in c.resolution.lower()
        assert len(c.resolution) > 80, c.key


# ── the worked example ──────────────────────────────────────────────────────


def test_retiring_before_medicare_makes_the_aca_conflict_live():
    facts = {**BASE, "retirement": {"planned_retirement_age": 60}}
    assert "conversions-vs-aca" in keys(C.check(facts))


def test_retiring_at_medicare_age_does_not():
    facts = {**BASE, "retirement": {"planned_retirement_age": 67}}
    r = C.check(facts)
    assert "conversions-vs-aca" not in keys(r)
    assert "conversions-vs-aca" in {c.key for c in r.dormant}


def test_a_dormant_conflict_is_still_reported():
    """Facts change. A household planning early retirement should see this
    before it becomes live, not after."""
    facts = {**BASE, "retirement": {"planned_retirement_age": 67}}
    assert C.check(facts).dormant


# ── triggers ────────────────────────────────────────────────────────────────


def test_the_irmaa_conflict_needs_something_to_convert():
    """It previously fired for every household forever. A registry that
    always fires trains the reader to skip it — review F4."""
    assert "conversions-vs-irmaa" not in keys(C.check(BASE))
    with_pretax = {"household": {"members": BASE["household"]["members"],
                                 "balance_sheet": [
                                     {"name": "401k", "value": 500_000,
                                      "tier": "age_restricted"}]}}
    assert "conversions-vs-irmaa" in keys(C.check(with_pretax))


def test_the_business_conflict_needs_a_business():
    assert "salary-vs-solo401k" not in keys(C.check(BASE))
    assert "salary-vs-solo401k" in keys(C.check({**BASE, "business": {"kind": "llc"}}))


def test_the_housing_conflict_needs_a_purchase():
    assert "downpayment-vs-retirement" not in keys(C.check(BASE))
    facts = {**BASE, "housing": {"purchase": {"price": 900_000}}}
    assert "downpayment-vs-retirement" in keys(C.check(facts))


def test_the_harvesting_conflict_is_driven_by_the_policy_not_the_holdings():
    """Review F1. An earlier predicate required a balance-sheet row that was
    simultaneously tier: liquid and asset_class: equity. No such row existed
    on the shipped fixture, so the household whose direct-index provider
    harvests continuously was told the conflict was dormant — a false negative
    from the safety net built to catch exactly that case."""
    harvesting = {**BASE, "portfolio": {
        "wash_sale": {"direct_index_provider": "SomeProvider",
                      "harvesting_continuous": True},
        "target_allocation": {"us_equity": 0.6, "intl_equity": 0.2}}}
    assert "harvesting-vs-allocation" in keys(C.check(harvesting))

    # Harvesting with no allocation policy: nothing to rebalance into.
    no_policy = {**BASE, "portfolio": {
        "wash_sale": {"harvesting_continuous": True}}}
    assert "harvesting-vs-allocation" not in keys(C.check(no_policy))
    assert "harvesting-vs-allocation" not in keys(C.check(BASE))


def test_every_registry_predicate_fires_on_the_shipped_fixture():
    """The guard review F1 asked for. `check()` swallows predicate
    exceptions, and the other tests only assert self-consistency, so a typo in
    a lambda would otherwise be invisible forever. The fixture is deliberately
    maximal; a conflict that cannot fire on it is almost certainly broken.

    Anything intentionally dormant is listed here with its reason."""
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "lib"))
    import pytest as _pytest
    _pytest.importorskip("yaml")
    from pf import facts as F

    INTENTIONALLY_DORMANT = {
        # The Rivera adults are 41 and 39; this one turns on approaching 65.
        "hsa-vs-medicare",
    }
    live = keys(C.check(F.load(root / "inputs" / "facts.example.yml")))
    never = {c.key for c in C.REGISTRY} - live - INTENTIONALLY_DORMANT
    assert not never, (
        f"registered conflicts that cannot fire on the maximal fixture: "
        f"{sorted(never)} — either the predicate is wrong or the fixture "
        f"needs the facts that trigger it")


def test_the_charity_conflict_needs_equity_comp():
    facts = {**BASE, "equity_comp": {"held_value": 130_000}}
    assert "concentration-vs-charity" in keys(C.check(facts))
    # An empty block is treated as absent, not as present-but-zero.
    assert "concentration-vs-charity" not in keys(C.check({**BASE, "equity_comp": {}}))


# ── filtering and failure modes ─────────────────────────────────────────────


def test_a_skill_can_ask_for_only_its_own_conflicts():
    facts = {**BASE, "retirement": {"planned_retirement_age": 60}}
    out = C.for_skill(facts, "roth-conversion-window")
    assert out
    assert all("roth-conversion-window" in c.skills for c in out)


def test_an_unknown_skill_has_no_conflicts():
    assert C.for_skill(BASE, "not-a-skill") == []


def test_a_predicate_that_raises_reports_the_conflict_as_live():
    """An unknown is not an absence. A predicate that cannot evaluate must
    not silently drop the conflict."""
    boom = C.Conflict(key="boom", skills=("a", "b"), tension="t",
                      trigger="x", resolution="y" * 100,
                      applies=lambda f: (_ for _ in ()).throw(ValueError()))
    original = C.REGISTRY
    try:
        C.REGISTRY = original + (boom,)
        assert "boom" in keys(C.check(BASE))
    finally:
        C.REGISTRY = original


def test_the_education_conflict_records_that_it_is_already_handled():
    c = next(x for x in C.REGISTRY if x.key == "education-vs-retirement")
    assert "Already handled inside" in c.resolution


# ── the registry and its quantifiers must not drift apart (review F2) ───────


def test_healthcare_quantifiers_point_at_real_registry_keys():
    """healthcare.py computes the SIZE of two registered conflicts. If its
    keys stop matching, the repo has two independently authored descriptions
    of one problem and no way to tell."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
    from pf import healthcare as H
    keys = {c.key for c in C.REGISTRY}
    assert H.REGISTRY_KEY_SUBSIDY in keys
    assert H.REGISTRY_KEY_IRMAA in keys


def test_quantified_conflicts_name_their_quantifier():
    quantified = [c for c in C.REGISTRY if c.quantified_by]
    assert len(quantified) >= 2
    for c in quantified:
        assert c.quantified_by.startswith("lib/pf/")


def test_the_registry_covers_the_new_clusters():
    """26 skills were added in one batch. Each cluster that can contradict
    another should appear."""
    covered = {s for c in C.REGISTRY for s in c.skills}
    for skill in ("roth-portability-check", "pfic-divest-or-comply",
                  "depreciation-election", "passive-loss-eligibility",
                  "feie-vs-ftc", "charitable-giving-strategy",
                  "asset-allocation-review", "hsa-review"):
        assert skill in covered, f"{skill} has no registered conflict"


# ── aliased keys ────────────────────────────────────────────────────────────
#
# One quantity under two names. Tested separately from the conflict registry
# because it is a different defect: not two correct answers in tension, but
# two copies of one figure that nothing keeps in step.


def _facts(**assumptions):
    return {"assumptions": assumptions}


def test_divergent_copies_of_one_figure_are_reported():
    f = _facts(bonus_depreciation_pct=1.0, bonus_depreciation_rate=0.40)
    d = [a for a in C.aliased(f) if a.status == "diverged"]
    assert [a.concept for a in d] == ["§168(k) bonus depreciation percentage"]
    assert d[0].serious


def test_agreeing_copies_are_not_reported_as_serious():
    f = _facts(ltcg_rate=0.15, capital_gains_rate=0.15)
    a = next(x for x in C.aliased(f)
             if x.concept.startswith("Long-term"))
    assert a.status == "agreed"
    assert not a.serious


def test_one_key_set_and_its_twin_absent_is_serious():
    """The quiet case. The second skill refuses, which reads as missing data
    even though the household has already supplied the figure."""
    f = _facts(ltcg_rate=0.15)
    a = next(x for x in C.aliased(f)
             if x.concept.startswith("Long-term"))
    assert a.status == "partial"
    assert a.serious
    assert "capital_gains_rate" in a.detail


def test_both_absent_is_not_serious():
    """Nobody has answered, and every reader refuses loudly. That is the
    designed behaviour, not a defect to escalate."""
    a = C.aliased(_facts())
    assert {x.status for x in a} == {"absent"}
    assert not any(x.serious for x in a)


def test_every_alias_names_at_least_two_keys_and_a_reader_for_each():
    for a in C.ALIASES:
        assert len(a.keys) >= 2, a.concept
        assert all(k.startswith("assumptions.") and reader
                   for k, reader in a.keys), a.concept


def test_scalar_deduction_against_multi_status_brackets_warns():
    f = _facts(standard_deduction=30000,
               federal_brackets={"married_joint": [], "single": []})
    assert any("standard_deduction" in w for w in C.shape_warnings(f))


def test_mapping_deduction_does_not_warn():
    f = _facts(standard_deduction={"married_joint": 30000, "single": 15000},
               federal_brackets={"married_joint": [], "single": []})
    assert C.shape_warnings(f) == []


def test_scalar_deduction_with_one_status_does_not_warn():
    """A household that files one way loses nothing by the scalar shape."""
    f = _facts(standard_deduction=30000, federal_brackets={"married_joint": []})
    assert C.shape_warnings(f) == []
