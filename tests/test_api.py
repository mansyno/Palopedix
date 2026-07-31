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
