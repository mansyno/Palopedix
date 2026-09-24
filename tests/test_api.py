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





