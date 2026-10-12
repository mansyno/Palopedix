"""Tests for the FastAPI application."""

from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch

from palengine.api.main import app

client = TestClient(app)


def test_api_get_pals():
    mock_pals = [
        {
            "internal_name": "Anubis",
            "display_name": "Anubis",
            "paldex_number": 100,
            "element_1": "Ground",
            "element_2": None,
        }
    ]
    with patch("palengine.api.main.db_engine.query_pals", return_value=mock_pals):
        response = client.get("/api/pals?element=Ground")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["display_name"] == "Anubis"


def test_api_breeding_result():
    mock_child = {
        "display_name": "Relaxaurus Lux",
        "paldex_number": 80,
    }
    with patch("palengine.api.main.db_engine.get_breeding_result", return_value=mock_child):
        response = client.get("/api/breeding/result?parent1=Relaxaurus&parent2=Sparkit")
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Relaxaurus Lux"


def test_api_owned_species():
    with patch("palengine.api.main.db_engine.get_owned_pal_species", return_value=["Lamball", "Cattiva"]):
        response = client.get("/api/save/owned-species")
        assert response.status_code == 200
        assert response.json() == ["Lamball", "Cattiva"]


def test_api_breeding_path():
    mock_paths = [{"path_id": 1, "title": "Path 1", "difficulty": "Easy", "steps": [{"parent1": "Lamball", "parent2": "Penking", "child": "Bushi"}]}]
    with patch("palengine.api.main.db_engine.find_all_breeding_paths", return_value=mock_paths):
        response = client.get("/api/breeding/path?target=Bushi&owned=auto")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert len(data["paths"]) == 1
        assert data["paths"][0]["steps"][0]["child"] == "Bushi"


def test_api_breeding_path_with_target_skills():
    mock_paths = [{
        "path_id": 1,
        "title": "Path 1",
        "difficulty": "Easy",
        "total_quality_score": 55.0,
        "matched_skills_count": 2,
        "steps": [{
            "parent1": "Lamball",
            "parent1_score": 35.0,
            "parent1_passives": ["Artisan", "Swift"],
            "parent1_matched_passives": ["Artisan"],
            "parent2": "Penking",
            "child": "Bushi"
        }]
    }]
    with patch("palengine.api.main.db_engine.find_all_breeding_paths", return_value=mock_paths) as mock_fn:
        response = client.get("/api/breeding/path?target=Bushi&owned=auto&target_skills=Artisan,Swift")
        assert response.status_code == 200
        data = response.json()
        assert data["target_skills"] == "Artisan,Swift"
        assert len(data["paths"]) == 1
        mock_fn.assert_called_once_with(mock_fn.call_args[0][0], "Bushi", "Artisan,Swift")


def test_api_partner_skill_categories():
    mock_cats = [
        {"category_id": "flying_mount", "name": "Flying Mounts", "icon": "🦅", "pal_count": 29}
    ]
    with patch("palengine.api.main.db_engine.get_partner_skill_categories", return_value=mock_cats):
        response = client.get("/api/pals/partner-skill-categories")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["category_id"] == "flying_mount"


def test_api_get_pals_with_partner_category():
    mock_pals = [
        {
            "display_name": "Jetragon",
            "partner_skill_categories": [{"id": "flying_mount", "name": "Flying Mounts"}],
        }
    ]
    with patch("palengine.api.main.db_engine.query_pals", return_value=mock_pals) as mock_fn:
        response = client.get("/api/pals?partner_category=flying_mount")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["display_name"] == "Jetragon"
        mock_fn.assert_called_once_with({"partner_category": "flying_mount"})


def test_api_get_pals_with_partner_subcategory():
    mock_pals = [
        {
            "display_name": "Mozzarina",
            "partner_skill_categories": [{"id": "ranch_producer", "name": "Ranch Item Producers"}],
            "partner_skill_subcategories": [{"id": "milk", "name": "Milk", "parent_category_id": "ranch_producer"}],
        }
    ]
    with patch("palengine.api.main.db_engine.query_pals", return_value=mock_pals) as mock_fn:
        response = client.get("/api/pals?partner_category=ranch_producer&partner_subcategory=milk")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["display_name"] == "Mozzarina"
        mock_fn.assert_called_once_with({
            "partner_category": "ranch_producer",
            "partner_subcategory": "milk",
        })


def test_api_get_instances_with_partner_subcategory():
    mock_instances = [
        {
            "instance_id": "inst-1",
            "species": "Mozzarina",
            "partner_skill_categories": [{"id": "ranch_producer", "name": "Ranch Item Producers"}],
            "partner_skill_subcategories": [{"id": "milk", "name": "Milk", "parent_category_id": "ranch_producer"}],
        }
    ]
    with patch("palengine.api.main.db_engine.query_instances", return_value=mock_instances) as mock_fn:
        response = client.get("/api/save/instances?partner_category=ranch_producer&partner_subcategory=milk")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        mock_fn.assert_called_once_with({
            "partner_category": "ranch_producer",
            "partner_subcategory": "milk",
        })


def test_api_get_bosses():
    response = client.get("/api/bosses")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 12
    first = data[0]
    assert "canonical_name" in first
    assert "category" in first
    assert "elements" in first
    assert "icon_path" in first


def test_api_get_boss_party():
    mock_result = {
        "boss_profile": {"canonical_name": "Victor & Shadowbeak", "level": 50},
        "encounter_readiness": {"status": "FAVORED", "verdict": "Encounter is favored."},
        "recommended_party": [],
        "tactics": "Use arena pillars.",
    }
    with patch(
        "palengine.analytics.boss_recommender.BossPartyRecommender.recommend_party_for_boss",
        return_value=mock_result,
    ):
        response = client.get("/api/bosses/victor/party")
        assert response.status_code == 200
        data = response.json()
        assert data["boss_profile"]["canonical_name"] == "Victor & Shadowbeak"
        assert data["encounter_readiness"]["status"] == "FAVORED"


def test_api_get_palbox_cleanup():
    mock_result = {
        "total_evaluated": 10,
        "keep_core_count": 3,
        "keep_breeding_count": 2,
        "condense_fodder_count": 4,
        "butcher_sell_count": 1,
        "freeable_slots": 5,
        "species_count": 3,
        "condense_targets": [],
        "roster": [],
    }
    with patch(
        "palengine.api.main.db_engine.get_palbox_cleanup_recommendations",
        return_value=mock_result,
    ):
        response = client.get("/api/save/palbox-cleanup")
        assert response.status_code == 200
        data = response.json()
        assert data["total_evaluated"] == 10
        assert data["freeable_slots"] == 5
        assert data["keep_core_count"] == 3


def test_api_tech_tree():
    response = client.get("/api/tech_tree")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 500

    first = data[0]
    for key in ("id", "name", "level", "tech_point_cost", "is_ancient", "is_unlocked", "tier", "unlocks", "built_count", "is_built", "has_buildings"):
        assert key in first

    # Test filtering by is_ancient
    res_ancient = client.get("/api/tech_tree?is_ancient=true")
    assert res_ancient.status_code == 200
    ancient_data = res_ancient.json()
    assert len(ancient_data) > 0
    assert all(item["is_ancient"] == 1 for item in ancient_data)

    # Test filtering by is_unlocked
    res_unlocked = client.get("/api/tech_tree?is_unlocked=true")
    assert res_unlocked.status_code == 200
    unlocked_data = res_unlocked.json()
    assert len(unlocked_data) > 0
    assert all(item["is_unlocked"] is True for item in unlocked_data)

    # Test filtering by is_built
    res_built = client.get("/api/tech_tree?is_built=true")
    assert res_built.status_code == 200
    built_data = res_built.json()
    assert all(item["is_built"] is True for item in built_data)

    # Test alias /api/technology
    res_alias = client.get("/api/technology")
    assert res_alias.status_code == 200
    assert len(res_alias.json()) == len(data)


def test_api_buildings():
    response = client.get("/api/buildings")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 450

    first = data[0]
    for key in ("id", "name", "category", "built_count", "is_built", "unlock_method", "is_unlocked"):
        assert key in first

    # Test filtering by is_built
    res_built = client.get("/api/buildings?is_built=true")
    assert res_built.status_code == 200
    built_data = res_built.json()
    assert all(item["is_built"] is True for item in built_data)

    # Test filtering by unlock_method
    res_tech = client.get("/api/buildings?unlock_method=Standard Tech")
    assert res_tech.status_code == 200
    tech_data = res_tech.json()
    assert len(tech_data) > 0
    assert all(item["unlock_method"] == "Standard Tech" for item in tech_data)








