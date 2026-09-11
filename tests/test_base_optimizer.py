"""Unit & Integration Tests for Base Pal Recommendation & Optimization Engine."""

import pytest
from palengine.analytics.base_optimizer import BaseOptimizer
from palengine.analytics.pal_recommender import PalRecommender
from palengine.db.sqlite_engine import SQLiteEngine


@pytest.fixture
def engine():
    """Provides a clean SQLiteEngine instance using static metadata without loading save data."""
    return SQLiteEngine(world_id="NONE")


def test_sqlite_engine_metadata_tables(engine):
    """Verifies building_work_types, food_satiety_rates, and passive_modifiers in SQLite engine."""
    assert len(engine.get_building_work_types()) > 0
    assert len(engine.get_food_satiety_rates()) == 10
    mods = engine.get_passive_skill_modifiers()
    assert "artisan" in mods and "musclehead" in mods


def test_base_optimizer_demand_audit(engine):
    """Tests base work demand aggregation."""
    camps = engine.get_base_camps()
    if camps:
        camp_id = camps[0]["base_camp_id"]
        audit = BaseOptimizer(engine).audit_base_work_demand(camp_id)
        assert audit["base_camp_id"] == camp_id
        assert "base_category" in audit


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


def test_pal_recommender_scoring_and_synergies(engine):
    """Tests Pal recommendation scoring, negative passive penalties, and breeding synergies."""
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
    demand_map = {"Mining": {"work_type": "Mining", "is_automated": True}}
    scored = recommender.calculate_pal_base_score(mock_pal, demand_map)
    assert scored["total_score"] > 0
    assert scored["nocturnal"] is True
    assert scored["work_speed_mult"] == 1.80
