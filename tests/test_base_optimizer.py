"""Unit & Integration Tests for Base Pal Recommendation & Optimization Engine."""

import pytest
from palengine.analytics.base_optimizer import BaseOptimizer
from palengine.analytics.pal_recommender import PalRecommender
from palengine.db.sqlite_engine import SQLiteEngine


@pytest.fixture
def engine():
    """Provides a clean SQLiteEngine instance."""
    eng = SQLiteEngine()
    return eng


def test_sqlite_engine_metadata_tables(engine):
    """Verifies building_work_types and food_satiety_rates are present in SQLite engine."""
    bwt = engine.get_building_work_types()
    assert isinstance(bwt, list)
    assert len(bwt) > 0

    rates = engine.get_food_satiety_rates()
    assert isinstance(rates, list)
    assert len(rates) == 10
    assert rates[0]["food_rating"] == 1


def test_base_optimizer_demand_audit(engine):
    """Tests base work demand aggregation."""
    camps = engine.get_base_camps()
    assert isinstance(camps, list)
    if camps:
        camp_id = camps[0]["base_camp_id"]
        optimizer = BaseOptimizer(engine)
        audit = optimizer.audit_base_work_demand(camp_id)
        assert audit["base_camp_id"] == camp_id
        assert "base_category" in audit
        assert "demand_by_suitability" in audit


def test_base_optimizer_food_san_calculation(engine):
    """Tests team food satiety drain and SAN stability calculation."""
    optimizer = BaseOptimizer(engine)
    mock_team = [
        {"species": "Lamball", "food_requirement": 2, "passives": ["Diet Lover"], "nocturnal": 0},
        {"species": "Tombat", "food_requirement": 4, "passives": ["Workaholic"], "nocturnal": 1},
    ]
    summary = optimizer.calculate_team_food_and_san(mock_team)
    assert summary["team_size"] == 2
    assert summary["nocturnal_pals_count"] == 1
    assert summary["total_hourly_satiety_drain"] > 0
    assert summary["san_stability_status"] in ["Excellent", "Good", "Warning"]


def test_pal_recommender_scoring(engine):
    """Tests Pal recommendation scoring with nocturnal bonuses and passives."""
    recommender = PalRecommender(engine)
    mock_pal = {
        "instance_id": "inst_1",
        "species": "Tombat",
        "display_name": "Tombat",
        "level": 25,
        "food_requirement": 4,
        "nocturnal": 1,
        "passives": ["Artisan", "Work Slave"],
        "suitabilities": {"Mining": 2, "Gathering": 2},
    }
    demand_map = {
        "Mining": {"work_type": "Mining", "is_automated": True},
    }
    scored = recommender.calculate_pal_base_score(mock_pal, demand_map)
    assert scored["total_score"] > 0
    assert scored["nocturnal"] is True
    assert scored["work_speed_mult"] == 1.80  # 1.0 + 0.5 (Artisan) + 0.3 (Work Slave)


def test_pal_recommender_full_recommendation(engine):
    """Tests full recommendation pathfinder for base camp."""
    camps = engine.get_base_camps()
    if camps:
        camp_id = camps[0]["base_camp_id"]
        recommender = PalRecommender(engine)
        res = recommender.recommend_pals_for_base(camp_id, max_team_size=5)
        assert res["base_camp_id"] == camp_id
        assert "recommended_team" in res
        assert "food_and_san_summary" in res
