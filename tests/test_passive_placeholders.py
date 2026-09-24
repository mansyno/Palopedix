"""Unit tests for passive skill placeholder resolution and enrichment."""

import sqlite3
import pytest
from palengine.db.sqlite_engine import SQLiteEngine
from palengine.db.utils import enrich_passive_skill, resolve_passive_placeholders


def test_resolve_passive_placeholders_known_skills():
    """Verify specific known passive skills resolve correctly."""
    # Stronghold Strategist
    raw_def = "{EffectValue1}% increase in Player Defense."
    resolved_def = resolve_passive_placeholders(raw_def, "TrainerDEF_UP_1", "Stronghold Strategist")
    assert resolved_def == "10.0% increase in Player Defense."

    # Easygoing
    raw_easy = "Active skill cooldown extension {EffectValue1}%"
    resolved_easy = resolve_passive_placeholders(raw_easy, "CoolTimeReduction_Down_1", "Easygoing")
    assert resolved_easy == "Active skill cooldown extension -15.0%"

    # Vanguard
    raw_atk = "{EffectValue1}% increase in Player Attack."
    resolved_atk = resolve_passive_placeholders(raw_atk, "TrainerATK_UP_1", "Vanguard")
    assert resolved_atk == "10.0% increase in Player Attack."


def test_enrich_passive_skill_dict():
    """Verify enrich_passive_skill applies resolution directly to dictionary."""
    pd = {
        "id": "TrainerDEF_UP_1",
        "name": "Stronghold Strategist",
        "type": "Passive",
        "description": "{EffectValue1}% increase in Player Defense.",
        "stat_modifier": "{EffectValue1}% increase in Player Defense.",
    }
    enriched = enrich_passive_skill(pd)
    assert enriched["description"] == "10.0% increase in Player Defense."
    assert enriched["stat_modifier"] == "10.0% increase in Player Defense."
    assert "{" not in enriched["description"]


def test_all_master_db_passives_resolve_cleanly():
    """Verify that all passive skills in the master database resolve with 0 placeholder tokens."""
    conn = sqlite3.connect("data/palworld.db")
    cur = conn.cursor()
    rows = cur.execute("SELECT id, name, description, stat_modifier FROM skills WHERE type = 'Passive'").fetchall()
    conn.close()

    for r in rows:
        skill_dict = {
            "id": r[0],
            "name": r[1],
            "type": "Passive",
            "description": r[2],
            "stat_modifier": r[3],
        }
        enriched = enrich_passive_skill(skill_dict)
        desc = enriched.get("description") or ""
        mod = enriched.get("stat_modifier") or ""
        assert "{EffectValue" not in desc, f"Found unresolved token in {r[0]} ({r[1]}): {desc}"
        assert "{EffectValue" not in mod, f"Found unresolved token in {r[0]} ({r[1]}): {mod}"


def test_unmapped_placeholder_sanitization():
    """Verify that an unknown passive skill with EffectValue placeholder is sanitized gracefully."""
    raw = "Unknown effect +{EffectValue1}% to all stats."
    sanitized = resolve_passive_placeholders(raw, "Unknown_Skill_999", "Unknown")
    assert "{EffectValue" not in sanitized
    assert "{" not in sanitized
