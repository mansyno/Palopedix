"""Integration and unit tests for Palworld 1.0+ master DB integration and asset serving."""

import os
import pytest
from fastapi.testclient import TestClient

from palengine.api.main import app
from palengine.config import (
    get_assets_dir,
    get_palworld_db_path,
    get_static_data_source,
    set_static_data_source,
)
from palengine.db.data_manager import PaldexDataManager
from palengine.db.sqlite_engine import SQLiteEngine, transform_icon_path

client = TestClient(app)


def test_transform_icon_path():
    assert transform_icon_path(None) is None
    assert transform_icon_path("C:/palworld_assets/pals/Anubis.png") == "/assets/pals/Anubis.png"
    assert transform_icon_path(r"C:\palworld_assets\skills\SheepBall_Skill1.png") == "/assets/skills/SheepBall_Skill1.png"
    assert transform_icon_path("/some/other/path.png") == "/some/other/path.png"


def test_config_get_and_set():
    original_source = get_static_data_source()
    try:
        set_static_data_source("legacy")
        assert get_static_data_source() == "legacy"
        set_static_data_source("palworld_db")
        assert get_static_data_source() == "palworld_db"
        with pytest.raises(ValueError):
            set_static_data_source("invalid_source")
    finally:
        set_static_data_source(original_source)


def test_sqlite_engine_palworld_db_mode():
    db_path = get_palworld_db_path()
    if not os.path.exists(db_path):
        pytest.skip(f"Master database not found at {db_path}")

    engine = SQLiteEngine(source="palworld_db")
    assert engine.source == "palworld_db"

    pals = engine.query_pals({})
    assert len(pals) > 0

    # Test Anubis or Lamball presence
    lamball = [p for p in pals if p["display_name"] == "Lamball"]
    assert len(lamball) > 0
    assert lamball[0]["element_1"] in ("Normal", "Neutral")
    assert lamball[0]["icon_path"] is not None and "SheepBall" in lamball[0]["icon_path"]
    assert "skills" in lamball[0]
    assert "work_suitabilities" in lamball[0]
    assert "drops" in lamball[0]


def test_sqlite_engine_legacy_mode():
    engine = SQLiteEngine(source="legacy")
    assert engine.source == "legacy"

    pals = engine.query_pals({})
    assert len(pals) > 0
    lamball = [p for p in pals if p["display_name"] == "Lamball"]
    assert len(lamball) > 0
    assert lamball[0]["element_1"] in ("Normal", "Neutral")


def test_data_manager_sources():
    dm_db = PaldexDataManager()
    original_source = get_static_data_source()
    try:
        set_static_data_source("palworld_db")
        pals_db = dm_db.get_all_pals()
        assert len(pals_db) > 0

        set_static_data_source("legacy")
        pals_legacy = dm_db.get_all_pals()
        assert isinstance(pals_legacy, list)
    finally:
        set_static_data_source(original_source)


def test_api_config_endpoint():
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert "static_data_source" in data

    post_res = client.post("/api/config", json={"static_data_source": "palworld_db"})
    assert post_res.status_code == 200
    assert post_res.json()["static_data_source"] == "palworld_db"


def test_api_pals_and_asset_urls():
    client.post("/api/config", json={"static_data_source": "palworld_db"})
    res = client.get("/api/pals")
    assert res.status_code == 200
    pals = res.json()
    assert len(pals) > 0

    lamball = [p for p in pals if p["display_name"] == "Lamball"][0]
    assert lamball["icon_path"] == "/assets/pals/SheepBall.png"

    # Test fetching static asset via mounted FastAPI static route
    assets_dir = get_assets_dir()
    if os.path.exists(assets_dir):
        asset_res = client.get("/assets/pals/SheepBall.png")
        assert asset_res.status_code == 200
        assert asset_res.headers["content-type"] in ("image/png", "application/octet-stream")


def test_breeding_calculations_palworld_db():
    client.post("/api/config", json={"static_data_source": "palworld_db"})
    res = client.get("/api/breeding/result?parent1=Relaxaurus&parent2=Sparkit")
    assert res.status_code == 200
    child = res.json()
    assert "display_name" in child
    assert child["icon_path"] is not None


def test_new_schema_api_endpoints():
    client.post("/api/config", json={"static_data_source": "palworld_db"})

    # 1. Items API
    items_res = client.get("/api/items")
    assert items_res.status_code == 200
    items = items_res.json()
    assert len(items) > 0

    # 2. Buildings API
    b_res = client.get("/api/buildings")
    assert b_res.status_code == 200
    buildings = b_res.json()
    assert len(buildings) > 0

    # 3. Tech Tree API
    t_res = client.get("/api/tech_tree")
    assert t_res.status_code == 200
    tech = t_res.json()
    assert len(tech) > 0

    # 4. Work Types API
    w_res = client.get("/api/work_types")
    assert w_res.status_code == 200
    work_types = w_res.json()
    assert len(work_types) == 12
    assert work_types[0]["icon_path"].startswith("/assets/work/")

