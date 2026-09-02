"""Unit & Integration Tests for Base Pal Recommendation & Optimization Engine."""

import pytest
from palengine.analytics.base_optimizer import BaseOptimizer
from palengine.analytics.pal_recommender import PalRecommender
from palengine.db.sqlite_engine import SQLiteEngine


@pytest.fixture
def engine():
    """Provides a clean SQLiteEngine instance using static metadata."""
    eng = SQLiteEngine(world_id="NONE")
    return eng


def test_sqlite_engine_metadata_tables(engine):
    """Verifies building_work_types, food_satiety_rates, and passive_modifiers in SQLite engine."""
    bwt = engine.get_building_work_types()
    assert isinstance(bwt, list)
    assert len(bwt) > 0

    rates = engine.get_food_satiety_rates()
    assert isinstance(rates, list)
    assert len(rates) == 10
    assert rates[0]["food_rating"] == 1

    mods = engine.get_passive_skill_modifiers()
    assert isinstance(mods, dict)
    assert len(mods) > 0
    assert "artisan" in mods
    assert "musclehead" in mods
    assert "swift" in mods
    assert "destructive" in mods


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


def test_pal_recommender_negative_passives_and_movement_speed(engine):
    """Tests that negative passives penalize score and movement speed enhances Transporting."""
    recommender = PalRecommender(engine)

    pal_clean = {
        "instance_id": "clean_anubis",
        "species": "Anubis",
        "display_name": "Anubis",
        "level": 30,
        "food_requirement": 6,
        "passives": ["Serious"],
        "suitabilities": {"Mining": 3, "Handcraft": 4, "Transporting": 2},
    }
    pal_bad = {
        "instance_id": "bad_anubis",
        "species": "Anubis",
        "display_name": "Anubis",
        "level": 30,
        "food_requirement": 6,
        "passives": ["Musclehead", "Destructive"],
        "suitabilities": {"Mining": 3, "Handcraft": 4, "Transporting": 2},
    }
    pal_fast = {
        "instance_id": "fast_anubis",
        "species": "Anubis",
        "display_name": "Anubis",
        "level": 30,
        "food_requirement": 6,
        "passives": ["Swift", "Runner"],
        "suitabilities": {"Mining": 3, "Handcraft": 4, "Transporting": 2},
    }

    demand_craft = {"Handcraft": {"work_type": "Handcraft", "is_automated": False}}
    demand_transport = {"Transporting": {"work_type": "Transporting", "is_automated": True}}

    score_clean_craft = recommender.calculate_pal_base_score(pal_clean, demand_craft)
    score_bad_craft = recommender.calculate_pal_base_score(pal_bad, demand_craft)
    score_clean_trans = recommender.calculate_pal_base_score(pal_clean, demand_transport)
    score_fast_trans = recommender.calculate_pal_base_score(pal_fast, demand_transport)

    assert score_clean_craft["total_score"] > score_bad_craft["total_score"]
    assert score_bad_craft["work_speed_mult"] == 0.50  # 1.0 - 0.5 (Musclehead)
    assert score_bad_craft["san_bonus"] == -25.0  # Destructive penalty
    assert score_fast_trans["total_score"] > score_clean_trans["total_score"]
    assert score_fast_trans["move_speed_mult"] == 1.50  # 1.0 + 0.3 (Swift) + 0.2 (Runner)


def test_pal_recommender_partner_skill_category_synergies(engine):
    """Tests dynamic database partner skill synergies for Ranching and Breeding."""
    recommender = PalRecommender(engine)

    pal_breeder = {
        "instance_id": "breeder_pal",
        "species": "SakuraSaurus",
        "display_name": "SakuraSaurus",
        "level": 25,
        "food_requirement": 6,
        "passives": [],
        "suitabilities": {"Planting": 2},
    }
    audit_with_breeding = {"breeding_farm_count": 2, "ranch_count": 0}
    audit_without_breeding = {"breeding_farm_count": 0, "ranch_count": 0}
    demand_plant = {"Planting": {"work_type": "Planting", "is_automated": True}}

    score_with = recommender.calculate_pal_base_score(pal_breeder, demand_plant, base_audit=audit_with_breeding)
    score_without = recommender.calculate_pal_base_score(pal_breeder, demand_plant, base_audit=audit_without_breeding)

    assert score_with["total_score"] > score_without["total_score"]
