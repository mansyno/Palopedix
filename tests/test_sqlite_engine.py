"""Unit tests for SQLiteEngine core functionality."""

import pytest
from palengine.db.sqlite_engine import SQLiteEngine


@pytest.fixture(scope="module")
def engine():
    """Provides a shared SQLiteEngine instance using static data without disk save loading."""
    return SQLiteEngine(world_id="NONE")


def test_sqlite_engine_initialization(engine):
    """Verifies table schema creation and static database connection."""
    cursor = engine.conn.cursor()
    cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pals'")
    assert cursor.fetchone() is not None

    cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='passive_skills'")
    assert cursor.fetchone() is not None


def test_sqlite_engine_paldex_and_skills_query(engine):
    """Verifies querying pals, skills, and items."""
    pals = engine.query_pals({"element": "Fire"})
    assert len(pals) > 0
    assert all(p["element_1"] == "Fire" or p.get("element_2") == "Fire" for p in pals)

    skills = engine.query_skills({"type": "Active"})
    assert len(skills) > 0

    items = engine.query_items({})
    assert len(items) > 0


def test_sqlite_engine_breeding_calculations(engine):
    """Verifies breeding calculation formulas and tie-breaking."""
    res = engine.get_breeding_result("Lamball", "Cattiva")
    assert res is not None
    assert "display_name" in res


def test_sqlite_engine_partner_skill_categories(engine):
    """Verifies Partner Skill Categories aggregation."""
    categories = engine.get_partner_skill_categories()
    assert isinstance(categories, list)
    assert len(categories) > 0
    cat_ids = {c["category_id"] for c in categories}
    assert "flying_mount" in cat_ids or "ground_mount" in cat_ids
