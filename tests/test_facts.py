import datetime as dt
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from pf import facts as F  # noqa: E402

SAMPLE = {
    "meta": {"schema_version": 1, "as_of": "2026-08-30",
             "jurisdiction": {"country": "US", "state": "TX"}},
    "household": {
        "members": [
            {"id": "a1", "role": "primary", "age": 41, "income_annual": 180000},
            {"id": "a2", "role": "spouse", "age": 39, "income_annual": 0},
            {"id": "c1", "role": "dependent", "age": 8},
        ],
        "balance_sheet": [
            {"name": "cash", "value": 40000, "tier": "liquid"},
            {"name": "brokerage", "value": 45000, "tier": "liquid"},
            {"name": "retirement_401k", "value": 310000, "tier": "age_restricted"},
            {"name": "college_529", "value": 28000, "tier": "illiquid"},
        ],
        "annual_spending": 96000,
    },
}


def test_pending_positions_are_recorded_but_not_counted():
    """An unsettled order is either additional to a balance or came out of
    it. Counting it before that is confirmed may double-count."""
    with_pending = dict(SAMPLE)
    with_pending["household"] = dict(SAMPLE["household"])
    with_pending["household"]["balance_sheet"] = (
        SAMPLE["household"]["balance_sheet"]
        + [{"name": "unsettled", "value": 20_000, "tier": "liquid",
            "pending": True}])
    assert F.liquid(with_pending) == F.liquid(SAMPLE)
    assert F.attachable(with_pending) == F.attachable(SAMPLE)


def test_a_settled_position_is_counted():
    settled = dict(SAMPLE)
    settled["household"] = dict(SAMPLE["household"])
    settled["household"]["balance_sheet"] = (
        SAMPLE["household"]["balance_sheet"]
        + [{"name": "settled", "value": 20_000, "tier": "liquid"}])
    assert F.liquid(settled) == F.liquid(SAMPLE) + 20_000


def test_liquid_excludes_retirement():
    assert F.liquid(SAMPLE) == 85_000


def test_attachable_excludes_retirement_but_includes_illiquid():
    assert F.attachable(SAMPLE) == 113_000


def test_a_401k_rich_cash_poor_household_cannot_absorb():
    """The case SCHEMA.md calls out: $2M in a 401(k), $3,000 in cash."""
    poor = {
        "household": {
            "balance_sheet": [
                {"name": "cash", "value": 3_000, "tier": "liquid"},
                {"name": "401k", "value": 2_000_000, "tier": "age_restricted"},
            ],
            "annual_spending": 96_000,
        }
    }
    assert F.liquid(poor) == 3_000
    assert F.months_of_spending(poor) < 1


def test_household_income_sums_members():
    assert F.household_income(SAMPLE) == 180_000


def test_dependents():
    assert len(F.dependents(SAMPLE)) == 1


def test_require_reports_every_missing_path():
    pre = F.require(SAMPLE, ["meta.jurisdiction.state", "auto.vehicles", "umbrella.coverage"])
    assert not pre.ok
    assert pre.missing == ["auto.vehicles", "umbrella.coverage"]


def test_require_checks_fields_on_list_items():
    data = dict(SAMPLE, auto={"vehicles": [
        {"id": "v1", "label": "Car A", "value": 1000, "value_basis": "acv"},
        {"id": "v2", "label": "Car B", "value": 2000},
    ]})
    pre = F.require(data, ["auto.vehicles[].value_basis"])
    assert pre.missing == ["auto.vehicles[Car B].value_basis"]


def test_version_mismatch_is_fatal():
    with pytest.raises(F.FactsError):
        F.check_version({"meta": {"schema_version": 2}})


def test_missing_version_is_fatal():
    with pytest.raises(F.FactsError):
        F.check_version({"meta": {}})


def test_staleness_undated_counts_as_stale():
    s = F.staleness("x", None, dt.date(2026, 8, 30))
    assert s.is_stale and s.days is None


def test_staleness_recent_is_fresh():
    s = F.staleness("x", "2026-08-01", dt.date(2026, 8, 30))
    assert not s.is_stale and s.days == 29


def test_staleness_old_is_stale():
    s = F.staleness("x", "2024-01-01", dt.date(2026, 8, 30))
    assert s.is_stale


def test_example_facts_file_parses_and_satisfies_the_skill():
    """The shipped example must actually run the skill it advertises."""
    yaml = pytest.importorskip("yaml")  # noqa: F841
    data = F.load(ROOT / "inputs" / "facts.example.yml")
    pre = F.require(data, [
        "meta.jurisdiction.state",
        "household.balance_sheet",
        "auto.vehicles",
        "auto.coverage",
        "auto.vehicles[].value",
        "auto.vehicles[].value_basis",
    ])
    assert pre.ok, pre.missing


# ── duplicate keys ──────────────────────────────────────────────────────────
#
# `yaml.safe_load` resolves a duplicate mapping key silently: the second wins,
# the first is discarded, and nothing downstream can tell. A facts file with
# two `housing:` blocks parses cleanly and every skill then produces a
# confident, correctly formatted report about whichever half survived.
#
# This is not hypothetical. It happened to a real file, `rent-vs-buy` reported
# on the wrong property at the wrong price, and the file's own validator passed
# throughout.


def _write(tmp_path, body, name="facts.yml"):
    p = tmp_path / name
    p.write_text(body)
    return p


def test_a_duplicate_top_level_key_is_refused(tmp_path):
    p = _write(tmp_path, """\
meta: {schema_version: 1}
housing:
  monthly_rent: 2400
other: 1
housing:
  monthly_rent: 9999
""")
    with pytest.raises(F.FactsError) as e:
        F.load(p)
    assert "housing" in str(e.value)


def test_the_message_names_the_key_and_both_lines(tmp_path):
    """An error saying only "duplicate key found" sends someone hunting
    through a six-hundred-line file."""
    p = _write(tmp_path, """\
meta: {schema_version: 1}
housing:
  monthly_rent: 2400
other: 1
housing:
  monthly_rent: 9999
""")
    with pytest.raises(F.FactsError) as e:
        F.load(p)
    msg = str(e.value)
    assert "`housing`" in msg
    assert "line 2" in msg          # first definition
    assert "line 5" in msg          # the one that silently won


def test_a_duplicate_nested_key_is_refused(tmp_path):
    p = _write(tmp_path, """\
meta: {schema_version: 1}
housing:
  purchase:
    price: 100
    price: 200
""")
    with pytest.raises(F.FactsError) as e:
        F.load(p)
    assert "`price`" in str(e.value)
    assert "line 4" in str(e.value) and "line 5" in str(e.value)


def test_a_duplicate_inside_a_list_item_is_refused(tmp_path):
    """Mappings inside sequences are mappings too, and this is where a
    hand-edited balance sheet actually goes wrong."""
    p = _write(tmp_path, """\
meta: {schema_version: 1}
household:
  members:
    - id: a1
      age: 41
      age: 52
""")
    with pytest.raises(F.FactsError) as e:
        F.load(p)
    assert "`age`" in str(e.value)


def test_the_same_key_in_two_different_mappings_is_fine(tmp_path):
    """The guard must not fire on the ordinary case: every list item having
    an `id`, every block having a `value`. That would make it useless."""
    p = _write(tmp_path, """\
meta: {schema_version: 1}
household:
  members:
    - { id: a1, age: 41 }
    - { id: a2, age: 39 }
  balance_sheet:
    - { name: cash, value: 100 }
    - { name: brokerage, value: 200 }
""")
    assert F.load(p)["household"]["members"][1]["id"] == "a2"


def test_a_clean_file_still_loads(tmp_path):
    p = _write(tmp_path, """\
meta:
  schema_version: 1
  as_of: 2026-09-15
housing:
  monthly_rent: 2400
""")
    assert F.load(p)["housing"]["monthly_rent"] == 2400


def test_the_shipped_example_fixture_has_no_duplicate_keys():
    """The guard, pointed at the thing everybody copies."""
    assert F.load(ROOT / "inputs" / "facts.example.yml")


def test_a_duplicate_in_json_is_refused_too(tmp_path):
    """Same defect, different syntax. `json.loads` also keeps the last."""
    p = _write(tmp_path,
               '{"meta": {"schema_version": 1}, "housing": {"a": 1}, '
               '"housing": {"a": 2}}',
               name="facts.json")
    with pytest.raises(F.FactsError) as e:
        F.load(p)
    assert "housing" in str(e.value)


def test_malformed_yaml_is_still_a_factserror_not_a_yaml_error(tmp_path):
    """Callers catch FactsError. A raw YAMLError escaping `load` would reach
    the user as a traceback, which the behaviour tests forbid."""
    p = _write(tmp_path, "meta: {schema_version: 1}\n  bad indent: [\n")
    with pytest.raises(F.FactsError):
        F.load(p)
