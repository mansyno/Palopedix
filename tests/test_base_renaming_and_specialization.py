"""Unit tests for Base Camp Renaming and Nuanced 7-Category Optimization Engine."""

import pytest
from palengine.analytics.base_optimizer import BaseOptimizer
from palengine.analytics.pal_recommender import PalRecommender
from palengine.db.sqlite_engine import SQLiteEngine


@pytest.fixture
def engine():
    eng = SQLiteEngine(world_id="NONE")
    # Insert mock base camp
    eng.conn.execute("INSERT OR REPLACE INTO base_camps (base_camp_id, name) VALUES ('test_base_1', 'Unnamed Base')")
    eng.conn.execute("INSERT OR REPLACE INTO base_camps (base_camp_id, name) VALUES ('test_base_2', 'Unnamed Base')")
    eng.conn.commit()
    return eng


def test_base_camp_renaming_persistence(engine):
    """Tests setting and getting custom base camp names."""
    engine.conn.execute("INSERT OR REPLACE INTO base_camps (base_camp_id, name) VALUES ('test_base_1', 'Unnamed Base')")
    engine.conn.commit()

    engine.set_base_camp_custom_name("test_base_1", "Breeding & Cake HQ")
    
    names = engine.get_base_camp_custom_names()
    assert names.get("test_base_1") == "Breeding & Cake HQ"

    camps = engine.get_base_camps()
    base1 = next(c for c in camps if c["base_camp_id"] == "test_base_1")
    assert base1["display_name"] == "Breeding & Cake HQ"
    assert base1["custom_name"] == "Breeding & Cake HQ"

    summary = engine.get_base_camp_summary("test_base_1")
    assert summary is not None
    assert summary["display_name"] == "Breeding & Cake HQ"


def test_breeding_and_food_categorization(engine):
    """Tests 7-category detection for Breeding & Food base."""
    # Add Breeding Farm (BreedFarm) + Berry Garden + Electric Kitchen
    engine.conn.execute("DELETE FROM base_structures_instances WHERE base_camp_id = 'test_base_1'")
    engine.conn.execute("INSERT INTO base_structures_instances (base_camp_id, structure_name, count) VALUES ('test_base_1', 'BreedFarm', 2)")
    engine.conn.execute("INSERT INTO base_structures_instances (base_camp_id, structure_name, count) VALUES ('test_base_1', 'BerryGarden', 4)")
    engine.conn.execute("INSERT INTO base_structures_instances (base_camp_id, structure_name, count) VALUES ('test_base_1', 'ElectricKitchen', 1)")
    engine.conn.commit()

    optimizer = BaseOptimizer(engine)
    audit = optimizer.audit_base_work_demand("test_base_1")

    assert audit["base_category"] == "Breeding & Food"
    assert audit["breeding_farm_count"] == 2


def test_breeding_farm_slot_reservation(engine):
    """Tests that effective capacity reserves 2 slots per breeding farm."""
    engine.conn.execute("DELETE FROM base_structures_instances WHERE base_camp_id = 'test_base_1'")
    engine.conn.execute("INSERT INTO base_structures_instances (base_camp_id, structure_name, count) VALUES ('test_base_1', 'BreedFarm', 2)")
    engine.conn.commit()

    recommender = PalRecommender(engine)
    res = recommender.recommend_pals_for_base("test_base_1", max_team_size=20)

    assert res["max_capacity"] == 20
    assert res["reserved_breeding_slots"] == 4  # 2 * 2 breeding farms
    assert res["effective_capacity"] == 16      # 20 - 4


def test_cake_pipeline_ranch_pal_bonus(engine):
    """Tests that Mozzarina, Beegarde, Chikipi receive cake ingredient pipeline bonus in Breeding & Food base."""
    recommender = PalRecommender(engine)

    mozzarina = {
        "instance_id": "cow_1",
        "species": "Mozzarina",
        "display_name": "Mozzarina",
        "level": 20,
        "food_requirement": 3,
        "nocturnal": 0,
        "passives": ["Artisan"],
        "suitabilities": {"Farming": 1},
    }

    demand_map = {
        "Farming": {"work_type": "Farming", "is_automated": True, "facility_count": 2, "urgency_weight": 3.0}
    }

    # Score in Breeding & Food base vs Balanced base
    score_breeding = recommender.calculate_pal_base_score(
        mozzarina, demand_map, base_category="Breeding & Food"
    )
    score_balanced = recommender.calculate_pal_base_score(
        mozzarina, demand_map, base_category="Balanced"
    )

    # In Breeding & Food base, Mozzarina should score significantly higher due to cake pipeline bonus
    assert score_breeding["total_score"] > score_balanced["total_score"]


def test_electric_supply_demand_deficit(engine):
    """Tests electric balance deficit detection and power prioritization."""
    # Base with 2 oil pumps and only 1 small generator (deficit = 1)
    engine.conn.execute("DELETE FROM base_structures_instances WHERE base_camp_id = 'test_base_1'")
    engine.conn.execute("INSERT INTO base_structures_instances (base_camp_id, structure_name, count) VALUES ('test_base_1', 'OilPump', 2)")
    engine.conn.execute("INSERT INTO base_structures_instances (base_camp_id, structure_name, count) VALUES ('test_base_1', 'ElectricGenerator', 1)")
    engine.conn.commit()

    optimizer = BaseOptimizer(engine)
    audit = optimizer.audit_base_work_demand("test_base_1")

    assert audit["electric_deficit"] == 1
    assert audit["electric_consumer_count"] == 2
    assert audit["electric_supplier_count"] == 1


def test_rename_base_camp(engine):
    """Tests updating base camp custom name in SQLite."""
    engine.conn.execute("INSERT OR REPLACE INTO base_camp_custom_names (base_camp_id, custom_name) VALUES ('test_base_1', 'New Alpha Outpost')")
    engine.conn.commit()

    summary = engine.get_base_camp_summary("test_base_1")
    assert summary["display_name"] == "New Alpha Outpost"


def test_structure_aliases_database_resolution(engine):
    """Tests that structure names are resolved via the SQLite structure_aliases table."""
    engine.conn.execute("DELETE FROM base_structures_instances WHERE base_camp_id = 'test_base_1'")
    engine.conn.execute("INSERT INTO base_structures_instances (base_camp_id, structure_name, count) VALUES ('test_base_1', 'FarmBlockV2 wheet', 2)")
    engine.conn.execute("INSERT INTO base_structures_instances (base_camp_id, structure_name, count) VALUES ('test_base_1', 'Clinic', 1)")
    engine.conn.execute("INSERT INTO base_structures_instances (base_camp_id, structure_name, count) VALUES ('test_base_1', 'CharacterRankUp', 1)")
    engine.conn.commit()

    summary = engine.get_base_camp_summary("test_base_1")
    structs = {s["structure_name"]: s["display_name"] for s in summary["structures"]}
    assert structs.get("FarmBlockV2 wheet") == "Wheat Plantation"
    assert structs.get("Clinic") == "Pal Medical Center"
    assert structs.get("CharacterRankUp") == "Pal Essence Condenser"

    # Verify work types mapping from DB
    camp_structs = engine.get_base_camp_structures("test_base_1")
    clinic_entry = next(s for s in camp_structs if s["structure_name"] == "Clinic")
    assert any(wt["work_type"] == "Medicine" for wt in clinic_entry["work_types"])


def test_recommendation_instance_tooltip_fields(engine):
    """Tests that calculate_pal_base_score returns all fields required by PalInstanceTooltip."""
    recommender = PalRecommender(engine)
    pal = {
        "instance_id": "test_pal_1",
        "species": "Braloha",
        "display_name": "Braloha",
        "level": 20,
        "gender": "Female",
        "rank": 3,
        "ivs": {"hp": 59, "melee": 43, "defense": 36},
        "iv_hp": 59,
        "iv_melee": 43,
        "iv_defense": 36,
        "location": "base",
        "location_details_base_camp_name": "Dragon Sanctuary",
        "passives": ["Artisan", "Power of Gaia", "Ferocious", "Farmhand"],
        "suitabilities": {"Planting": 5, "Gathering": 5},
    }
    scored = recommender.calculate_pal_base_score(pal, {"Planting": {"facility_count": 2, "urgency_weight": 2.0}})
    assert scored["gender"] == "Female"
    assert scored["rank"] == 3
    assert scored["ivs"] == {"hp": 59, "melee": 43, "defense": 36}
    assert scored["iv_hp"] == 59
    assert scored["location"] == "base"
    assert scored["location_details"]["base_camp_name"] == "Dragon Sanctuary"


def test_custom_reserved_breeding_slots_override(engine):
    """Tests overriding reserved breeding slots via query param / parameter."""
    engine.conn.execute("DELETE FROM base_structures_instances WHERE base_camp_id = 'test_base_1'")
    engine.conn.execute("INSERT INTO base_structures_instances (base_camp_id, structure_name, count) VALUES ('test_base_1', 'BreedFarm', 2)")
    engine.conn.commit()

    recommender = PalRecommender(engine)
    # Default without override: 4 reserved slots (2 * 2 farms)
    res_default = recommender.recommend_pals_for_base("test_base_1", max_team_size=20)
    assert res_default["reserved_breeding_slots"] == 4
    assert res_default["effective_capacity"] == 16

    # Override to 2 reserved slots
    res_custom = recommender.recommend_pals_for_base("test_base_1", max_team_size=20, reserved_breeding=2)
    assert res_custom["reserved_breeding_slots"] == 2
    assert res_custom["effective_capacity"] == 18

    # Override to 0 reserved slots
    res_zero = recommender.recommend_pals_for_base("test_base_1", max_team_size=20, reserved_breeding=0)
    assert res_zero["reserved_breeding_slots"] == 0
    assert res_zero["effective_capacity"] == 20


def test_no_generators_no_electric_demand(engine):
    """Tests that a base with 0 electric generators does NOT demand GeneratingElectricity."""
    engine.conn.execute("DELETE FROM base_structures_instances WHERE base_camp_id = 'test_base_1'")
    engine.conn.execute("INSERT INTO base_structures_instances (base_camp_id, structure_name, count) VALUES ('test_base_1', 'ElectricKitchen', 1)")
    engine.conn.commit()

    optimizer = BaseOptimizer(engine)
    audit = optimizer.audit_base_work_demand("test_base_1")
    assert "GeneratingElectricity" not in audit["demand_by_suitability"]
    assert audit["electric_deficit"] == 0

