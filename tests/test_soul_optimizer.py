"""Unit tests for the Pal Soul Crusher Optimizer."""

import pytest
from palengine.analytics.soul_optimizer import (
    optimize_pal_souls,
    calculate_direct_maxable_stats,
    solve_crusher_plan,
)
from palengine.db.sqlite_engine import SQLiteEngine


def test_calculate_direct_maxable_stats():
    """Verifies direct maxable stat calculation without any conversion."""
    inv = {
        "small": 100,  # 10 stats
        "medium": 60,  # 10 stats
        "large": 60,   # 10 stats
        "giant": 300,  # 10 stats
    }
    assert calculate_direct_maxable_stats(inv) == 10

    # Bottlenecked by Giant
    inv_bottleneck = {
        "small": 500,  # 50 stats
        "medium": 300, # 50 stats
        "large": 300,  # 50 stats
        "giant": 30,   # 1 stat
    }
    assert calculate_direct_maxable_stats(inv_bottleneck) == 1


def test_soul_optimizer_user_inventory_upward():
    """Verifies optimization with user inventory where small/medium surplus upgrades to giant."""
    inv = {
        "small": 680,
        "medium": 473,
        "large": 350,
        "giant": 380,
    }
    res = optimize_pal_souls(inv)

    assert res["direct_maxable_stats"] == 12
    assert res["optimal_maxable_stats"] == 21
    assert res["stats_gained_via_crusher"] == 9
    assert len(res["crusher_steps"]) == 3

    # Check that projected inventory satisfies all 21 stats requirements
    final_inv = res["projected_inventory"]
    req = res["required_for_optimal"]
    for tier in ("small", "medium", "large", "giant"):
        assert final_inv[tier] >= req[tier]


def test_soul_optimizer_downward_shattering():
    """Verifies optimization where giant surplus shatters downwards into lower tiers."""
    inv = {
        "small": 0,
        "medium": 0,
        "large": 0,
        "giant": 100,
    }
    res = optimize_pal_souls(inv)

    assert res["direct_maxable_stats"] == 0
    # 100 Giant = 800 Small equivalents -> 800 // 286 = 2 stats
    assert res["optimal_maxable_stats"] == 2
    assert len(res["crusher_steps"]) == 3

    # Steps should be shatters
    for step in res["crusher_steps"]:
        assert step["action"] == "shatter"

    final_inv = res["projected_inventory"]
    assert final_inv["small"] >= 20
    assert final_inv["medium"] >= 12
    assert final_inv["large"] >= 12
    assert final_inv["giant"] >= 60


def test_soul_optimizer_zero_or_insufficient():
    """Verifies edge case where inventory is zero or insufficient for even 1 stat."""
    res_zero = optimize_pal_souls({"small": 0, "medium": 0, "large": 0, "giant": 0})
    assert res_zero["direct_maxable_stats"] == 0
    assert res_zero["optimal_maxable_stats"] == 0
    assert len(res_zero["crusher_steps"]) == 0

    res_low = optimize_pal_souls({"small": 5, "medium": 2, "large": 1, "giant": 0})
    assert res_low["direct_maxable_stats"] == 0
    assert res_low["optimal_maxable_stats"] == 0
    assert len(res_low["crusher_steps"]) == 0


def test_soul_optimizer_already_optimal():
    """Verifies inventory that already has optimal distribution requires 0 steps."""
    inv = {
        "small": 20,
        "medium": 12,
        "large": 12,
        "giant": 60,
    }
    res = optimize_pal_souls(inv)
    assert res["direct_maxable_stats"] == 2
    assert res["optimal_maxable_stats"] == 2
    assert res["stats_gained_via_crusher"] == 0
    assert len(res["crusher_steps"]) == 0


def test_sqlite_engine_soul_summary_integration():
    """Verifies SQLiteEngine.get_soul_optimizer_summary() query method."""
    engine = SQLiteEngine()
    summary = engine.get_soul_optimizer_summary()

    assert "current_inventory" in summary
    assert "direct_maxable_stats" in summary
    assert "optimal_maxable_stats" in summary
    assert "crusher_steps" in summary
    assert "projected_inventory" in summary
    assert "remainder_after_optimal" in summary

    inv = summary["current_inventory"]
    assert all(k in inv for k in ("small", "medium", "large", "giant"))
