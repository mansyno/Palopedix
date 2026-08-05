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
