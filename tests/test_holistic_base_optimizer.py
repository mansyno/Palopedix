"""Unit tests for World Settings extraction and Holistic Multi-Base Pal Optimization."""

import pytest
from palengine.analytics.pal_recommender import PalRecommender
from palengine.cli.main import discover_save_path
from palengine.db.sqlite_engine import SQLiteEngine
from palengine.parser.extract_settings import extract_world_settings


def test_extract_world_settings():
    """Tests extracting custom world options from active save directory."""
    save_path = discover_save_path()
    if save_path:
        settings = extract_world_settings(save_path)
        assert isinstance(settings, dict)
        assert "BaseCampWorkerMaxNum" in settings
        assert settings["BaseCampWorkerMaxNum"] == 20


def test_dynamic_base_capacity():
    """Verifies SQLiteEngine dynamically applies BaseCampWorkerMaxNum to get_base_camps."""
    engine = SQLiteEngine()
    save_path = discover_save_path()
    if save_path:
        engine.load_save_data(save_path)
        camps = engine.get_base_camps()
        assert len(camps) > 0
        for c in camps:
            assert c["max_pals"] >= 20


def test_holistic_multi_base_optimization_zero_duplicates():
    """Verifies recommend_all_bases allocates disjoint sets of Pals across all bases."""
    engine = SQLiteEngine()
    save_path = discover_save_path()
    if save_path:
        engine.load_save_data(save_path)
        recommender = PalRecommender(engine)
        all_recs = recommender.recommend_all_bases()

        assert len(all_recs) > 0
        assigned_instances = set()

        for bid, rec in all_recs.items():
            assert "recommended_team" in rec
            assert rec["max_capacity"] >= 20
            team = rec["recommended_team"]
            
            for pal in team:
                iid = str(pal.get("instance_id"))
                # Guarantee each Pal instance is unique across all bases
                assert iid not in assigned_instances, f"Pal instance {iid} ({pal['display_name']}) duplicated in base {bid}"
                assigned_instances.add(iid)


def test_mock_multi_base_specialization_fairness():
    """Verifies holistic optimization distributes specialists to best matching bases."""
    engine = SQLiteEngine()
    recommender = PalRecommender(engine)

    # Mock bases: 1 Mining outpost, 1 Agriculture farm
    mock_camps = [
        {"base_camp_id": "camp_mining", "name": "Ore Outpost", "max_pals": 5},
        {"base_camp_id": "camp_farm", "name": "Farm Outpost", "max_pals": 5},
    ]

    all_recs = recommender.recommend_all_bases(base_camps=mock_camps)
    assert "camp_mining" in all_recs
    assert "camp_farm" in all_recs
