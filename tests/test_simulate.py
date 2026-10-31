import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import simulate


def test_portfolio_has_all_tiers():
    port = simulate.draw_portfolio(n=100)
    assert set(port["tier"]) == {"low", "medium", "high"}
    assert (port["base_incident"] > 0).all()


def test_empty_bundle_changes_nothing():
    port = simulate.draw_portfolio(n=50)
    p, delay, review = simulate.apply_bundle(port, [])
    assert (p == port["base_incident"].values).all()
    assert delay.sum() == 0 and review.sum() == 0


def test_human_in_loop_only_touches_high_tier():
    port = simulate.draw_portfolio(n=100)
    p, delay, review = simulate.apply_bundle(port, ["human in the loop"])
    low = (port["tier"] == "low").values
    assert (p[low] == port["base_incident"].values[low]).all()
    high = (port["tier"] == "high").values
    assert (p[high] < port["base_incident"].values[high]).all()


def test_more_interventions_prevent_more_harm_but_cost_more():
    port = simulate.draw_portfolio(n=100)
    one = simulate.evaluate(port, ["bias testing gate"], runs=50)
    all_on = simulate.evaluate(port, list(simulate.INTERVENTIONS), runs=50)
    assert all_on["harm_prevented"] >= one["harm_prevented"]
    assert all_on["value_forgone"] > one["value_forgone"]


def test_bundle_count():
    assert len(simulate.all_bundles()) == 2 ** len(simulate.INTERVENTIONS)
