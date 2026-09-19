"""Report-level check for the rent-vs-buy implied-real consistency display.

The arithmetic lives in `pf.housing` and is pinned in `test_housing.py`.
These cover the runner procedure added alongside it: when the caller
overrides `rent_growth` or `home_appreciation`, the report shows the implied
real spread next to the inputs, and warns when the override moves the spread
off the defaults.
"""

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import cli  # noqa: E402

_RUN = Path(__file__).resolve().parents[1] / "skills" / "rent-vs-buy" / "run.py"
_spec = importlib.util.spec_from_file_location("rent_vs_buy_run", _RUN)
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)

PURCHASE = {"price": 520_000, "down_payment": 104_000, "mortgage_rate": 0.0645,
            "term_years": 30, "property_tax_rate": 0.0185,
            "insurance_annual": 1_800, "hoa_monthly": 0,
            "maintenance_rate": 0.01, "expected_years": 7}


def render(**assumptions):
    data = {"housing": {"monthly_rent": 2_400, "purchase": dict(PURCHASE)},
            "assumptions": dict(assumptions)}
    w = cli.Writer()
    run.build(data, w)
    return w.render()


def test_no_override_shows_no_implied_real_line():
    text = render()
    assert "implied" not in text.lower()
    assert "Check the real view" not in text


def test_matched_override_at_defaults_shows_spread_without_a_warning():
    text = render(rent_growth=0.03, home_appreciation=0.03)
    assert "+0.0% real" in text
    assert "Check the real view" not in text


def test_lowering_rent_growth_alone_warns_that_the_real_view_rose():
    text = render(rent_growth=0.01, home_appreciation=0.03)
    assert "+2.0% real" in text
    assert "Check the real view" in text


def test_raising_appreciation_alone_warns():
    text = render(rent_growth=0.03, home_appreciation=0.05)
    assert "+2.0% real" in text
    assert "Check the real view" in text


def test_matched_override_off_defaults_shows_spread_without_a_warning():
    text = render(rent_growth=0.05, home_appreciation=0.05)
    assert "+0.0% real" in text
    assert "Check the real view" not in text


def test_an_explicit_zero_rent_growth_is_honoured_not_replaced_by_default():
    """`or`-based defaulting would silently turn an explicit 0.0 into the
    3% default, which is exactly the silent spread change this check exists
    to catch."""
    text = render(rent_growth=0.0, home_appreciation=0.03)
    assert "+3.0% real" in text
    assert "Check the real view" in text
