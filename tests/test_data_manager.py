"""Tests for PaldexDataManager CRUD operations (Add/Edit/Delete Pals)."""

import os
import shutil
import tempfile
import pytest

from palengine.db.data_manager import PaldexDataManager

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


@pytest.fixture
def temp_manager():
    """Creates a temporary working directory populated with real data files for isolated CRUD testing."""
    from palengine.config import get_static_data_source, set_static_data_source
    orig = get_static_data_source()
    set_static_data_source("legacy")
    temp_dir = tempfile.mkdtemp()
    for filename in [
        "pals.json",
        "partner_skills.json",
        "passive_skills.json",
        "active_skills.json",
        "work_suitabilities.json",
        "base_structures.json",
        "breeding_combos.json",
    ]:
        src = os.path.join(DATA_DIR, filename)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(temp_dir, filename))

    manager = PaldexDataManager(data_dir=temp_dir)
    yield manager
    set_static_data_source(orig)
    shutil.rmtree(temp_dir)


def test_get_all_pals(temp_manager):
    pals = temp_manager.get_all_pals()
    assert len(pals) == 288


def test_get_pal_by_name(temp_manager):
    pal = temp_manager.get_pal("SheepBall")
    assert pal is not None
    assert pal["display_name"] == "Lamball"


def test_add_pal(temp_manager):
    new_pal = {
        "internal_name": "CustomPal01",
        "display_name": "Custom Pal 1",
        "paldex_number": 999,
        "element_types": ["Neutral"],
        "partner_skill_id": None,
        "base_stats": {
            "hp": 100,
            "attack_melee": 100,
            "attack_ranged": 100,
            "defense": 100,
            "work_speed": 70,
        },
        "work_suitabilities": {"handiwork": 1},
        "breeding_power": 1000,
        "food_requirement": 3,
        "ride_type": None,
        "nocturnal": False,
        "size": "M",
        "is_variant": False,
        "base_pal": None,
    }
    temp_manager.add_pal(new_pal)

    assert len(temp_manager.get_all_pals()) == 289
    fetched = temp_manager.get_pal("CustomPal01")
    assert fetched is not None
    assert fetched["display_name"] == "Custom Pal 1"


def test_update_pal(temp_manager):
    updated = temp_manager.update_pal("SheepBall", {"breeding_power": 1234})
    assert updated["breeding_power"] == 1234

    refetched = temp_manager.get_pal("SheepBall")
    assert refetched["breeding_power"] == 1234


def test_delete_pal(temp_manager):
    success = temp_manager.delete_pal("SheepBall")
    assert success is True

    assert len(temp_manager.get_all_pals()) == 287
    assert temp_manager.get_pal("SheepBall") is None
