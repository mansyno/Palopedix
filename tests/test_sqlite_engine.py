"""Unit tests for the SQLiteEngine module."""

import pytest
from unittest.mock import patch
from uuid import UUID

from palengine.db.sqlite_engine import SQLiteEngine


def test_sqlite_engine_initialization():
    engine = SQLiteEngine()

    # Verify tables exist
    cursor = engine.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row["name"] for row in cursor.fetchall()]

    assert "pals" in tables
    assert "pal_work_suitabilities" in tables
    assert "partner_skills" in tables
    assert "passive_skills" in tables
    assert "active_skills" in tables
    assert "breeding_combos" in tables

    # Verify static data is loaded
    cursor.execute("SELECT count(*) as cnt FROM pals")
    pals_count = cursor.fetchone()["cnt"]
    assert pals_count >= 288  # Cleaned static pals count

    cursor.execute("SELECT count(*) as cnt FROM passive_skills")
    passives_count = cursor.fetchone()["cnt"]
    assert passives_count > 0


def test_save_refresh_capability():
    engine = SQLiteEngine()

    # Verify dynamic tables are empty initially
    cursor = engine.conn.cursor()
    cursor.execute("SELECT count(*) as cnt FROM pal_instances")
    assert cursor.fetchone()["cnt"] == 0

    # Mock parsed save data
    mock_pals = [
        {
            "instance_id": "00000000-0000-0000-0000-000000000001",
            "owner_uid": "11111111-1111-1111-1111-111111111111",
            "species": "SheepBall",
            "level": 10,
            "gender": "Male",
            "ivs": {"hp": 50, "melee": 50, "shot": 50, "defense": 50},
            "passives": ["Serious"],
            "rank": 1,
            "location": "party",
            "location_details": {"player_uid": "11111111-1111-1111-1111-111111111111"}
        }
    ]
    mock_bases = {
        "77777777-7777-7777-7777-777777777777": {
            "name": "Base Camp One",
            "structures": {"straw_pal_bed": 2}
        }
    }

    with patch("palengine.db.sqlite_engine.extract_pals", return_value=mock_pals), \
         patch("palengine.db.sqlite_engine.extract_bases", return_value=mock_bases):
        
        engine.load_save_data("dummy.sav")

        # Verify populated tables
        cursor.execute("SELECT count(*) as cnt FROM pal_instances")
        assert cursor.fetchone()["cnt"] == 1
        cursor.execute("SELECT count(*) as cnt FROM base_camps")
        assert cursor.fetchone()["cnt"] == 1

        # Clear/Refresh
        engine.clear_instance_data()

        # Verify dynamic tables are cleared
        cursor.execute("SELECT count(*) as cnt FROM pal_instances")
        assert cursor.fetchone()["cnt"] == 0
        cursor.execute("SELECT count(*) as cnt FROM base_camps")
        assert cursor.fetchone()["cnt"] == 0

        # Verify static data remains intact
        cursor.execute("SELECT count(*) as cnt FROM pals")
        assert cursor.fetchone()["cnt"] >= 288


def test_breeding_logic_and_tie_breaker():
    engine = SQLiteEngine()

    # 1. Same-species breeding
    res = engine.get_breeding_result("Anubis", "Anubis")
    assert res is not None
    assert res["display_name"] == "Anubis"

    # 2. Unique combo override
    res = engine.get_breeding_result("Relaxaurus", "Sparkit")
    assert res is not None
    assert res["display_name"] == "Relaxaurus Lux"

    # 3. Standard breeding formula
    # Let's test standard breeding math:
    # Nyafia (breeding_power = 1250) + Prunelia (breeding_power = 1390)
    # Target = (1250 + 1390 + 1) // 2 = 1320
    # Let's check which Pal has breeding power closest to 1320.
    res = engine.get_breeding_result("Nyafia", "Prunelia")
    assert res is not None
    # Let's check if the result is not a variant
    assert res["is_variant"] == 0

    # 4. Tie-breaker check using custom values
    # Insert custom Pals to ensure a tie-breaker behaves exactly as expected
    cursor = engine.conn.cursor()
    cursor.execute("DELETE FROM pals")  # Temp clear pals to control tie-breaker

    # Insert Pal A (power = 100, index_order = 0)
    cursor.execute("""
        INSERT INTO pals (internal_name, display_name, breeding_power, is_variant, index_order)
        VALUES ('PalA', 'Pal A', 100, 0, 0)
    """)
    # Insert Pal B (power = 120, index_order = 1)
    cursor.execute("""
        INSERT INTO pals (internal_name, display_name, breeding_power, is_variant, index_order)
        VALUES ('PalB', 'Pal B', 120, 0, 1)
    """)
    # Target power will be exactly 110 (which is equidistant to 100 and 120)
    # The tie-breaker should pick Pal A because it has index_order = 0
    res = engine.get_breeding_result("Pal A", "Pal B")
    assert res is not None
    assert res["display_name"] == "Pal A"


def test_breeding_path_finder():
    engine = SQLiteEngine()

    # Clear pals and combos to create a simplified deterministic breeding graph
    cursor = engine.conn.cursor()
    cursor.execute("DELETE FROM pals")
    cursor.execute("DELETE FROM breeding_combos")

    pals_data = [
        ("Lamball", 1500, 0),
        ("Cattiva", 1480, 1),
        ("Chikipi", 1500, 2),  # Chikipi is restricted in breeding_result
        ("Anubis", 100, 3),
        ("Penking", 520, 4),
        ("Bushy", 1490, 5),
    ]
    for name, power, idx in pals_data:
        cursor.execute("""
            INSERT INTO pals (internal_name, display_name, breeding_power, is_variant, index_order)
            VALUES (?, ?, ?, 0, ?)
        """, (name, name, power, idx))

    # Add custom unique combos
    cursor.execute("""
        INSERT INTO breeding_combos (parent1, parent2, child)
        VALUES ('Lamball', 'Cattiva', 'Bushy')
    """)
    cursor.execute("""
        INSERT INTO breeding_combos (parent1, parent2, child)
        VALUES ('Bushy', 'Penking', 'Anubis')
    """)

    # Find path from ['Lamball', 'Cattiva', 'Penking'] to 'Anubis'
    # Step 1: Lamball + Cattiva -> Bushy
    # Step 2: Bushy + Penking -> Anubis
    path = engine.find_breeding_path(["Lamball", "Cattiva", "Penking"], "Anubis")
    assert len(path) == 2
    assert path[0]["parent1"] in ["Lamball", "Cattiva"]
    assert path[0]["child"] == "Bushy"
    assert "parent1_gender" in path[0] and "parent2_gender" in path[0]
    assert path[1]["child"] == "Anubis"


def test_query_apis():
    engine = SQLiteEngine()

    # Test query pals by elements
    elements_pals = engine.query_pals({"element": "Neutral"})
    assert len(elements_pals) > 0
    for p in elements_pals:
        assert p["element_1"] == "Neutral" or p["element_2"] == "Neutral"

    # Test query pals by work suitability
    handiwork_pals = engine.query_pals({"work_suitability": {"name": "handiwork", "min_level": 3}})
    assert len(handiwork_pals) > 0
    for p in handiwork_pals:
        # Check that they indeed support Handiwork level >= 3
        cursor = engine.conn.cursor()
        cursor.execute(
            "SELECT level FROM pal_work_suitabilities WHERE pal_internal_name = ? AND suitability_name = 'handiwork'",
            (p["internal_name"],)
        )
        lvl = cursor.fetchone()["level"]
        assert lvl >= 3


def test_query_skills():
    engine = SQLiteEngine()

    # Query all skills
    all_skills = engine.query_skills({})
    assert len(all_skills) >= 1152

    # Query by type
    active_skills = engine.query_skills({"type": "Active"})
    assert len(active_skills) == 324

    passive_skills = engine.query_skills({"type": "Passive"})
    assert len(passive_skills) == 420

    partner_skills = engine.query_skills({"type": "Partner"})
    assert len(partner_skills) == 408

    # Query search
    runner_skills = engine.query_skills({"search": "Runner"})
    assert len(runner_skills) > 0
    assert any(s["name"] == "Runner" for s in runner_skills)


def test_gender_aware_breeding_path():
    engine = SQLiteEngine()
    # Two same-gender species (both Male) cannot breed
    two_males = {"Daedream": {"Male"}, "Foxparks": {"Male"}}
    assert engine.find_breeding_path(two_males, "Celaray") == []

    # Opposite gender species (Male + Female) can breed
    male_female = {"Daedream": {"Male"}, "Leezpunk": {"Female"}}
    path = engine.find_breeding_path(male_female, "Celaray")
    assert len(path) > 0
    assert path[0]["parent1_gender"] != path[0]["parent2_gender"]

