"""Unit tests for Partner Skill Scaling and Tag Resolution in PalEngine."""

import pytest
from palengine.analytics.partner_skill_scaling import (
    get_scaled_partner_skill,
    sanitize_markup_elements,
)
from palengine.db.sqlite_engine import SQLiteEngine


def test_sanitize_markup_elements():
    # Test Ground element resolution
    raw_ground = (
        "Can be ridden. While mounted, changes the player's attack type to "
        "<img id=|ElemIcon_Ground|/><uiCommon id=|COMMON_ELEMENT_NAME_Earth| style=|Elem_Ground|/> "
        "and increases Attack by <Status_Up>{Passive2_EffectValue1}%</>."
    )
    sanitized = sanitize_markup_elements(raw_ground, "Gildane")
    assert "changes the player's attack type to Ground and increases Attack by" in sanitized
    assert "<" not in sanitized
    assert ">" not in sanitized

    # Test Fire element resolution
    raw_fire = (
        "While fighting together, player attack type becomes "
        "<uiCommon id=|COMMON_ELEMENT_NAME_Fire| style=|Elem_Fire|/>."
    )
    sanitized_fire = sanitize_markup_elements(raw_fire, "Chillet")
    assert "player attack type becomes Fire." in sanitized_fire


def test_gildane_rank_scaling():
    base_desc = (
        "Can be ridden. While mounted, changes the player's attack type to "
        "<img id=|ElemIcon_Ground|/><uiCommon id=|COMMON_ELEMENT_NAME_Earth| style=|Elem_Ground|/> "
        "and increases Attack by 50%."
    )

    # 0 Stars -> Lv 1 (5%)
    res_0 = get_scaled_partner_skill("Gildane", 0, base_desc, "Sandstorm's Blessing", "Gildane Saddle")
    assert res_0["level"] == 1
    assert res_0["stars"] == 0
    assert "increases Attack by 5%" in res_0["description"]
    assert res_0["scaling_range"] == "5% -> 20%"

    # 1 Star -> Lv 2 (7.5%)
    res_1 = get_scaled_partner_skill("Gildane", 1, base_desc, "Sandstorm's Blessing", "Gildane Saddle")
    assert res_1["level"] == 2
    assert "increases Attack by 7.5%" in res_1["description"]

    # 2 Stars -> Lv 3 (10%) - matches user screenshot
    res_2 = get_scaled_partner_skill("Gildane", 2, base_desc, "Sandstorm's Blessing", "Gildane Saddle")
    assert res_2["level"] == 3
    assert "increases Attack by 10%" in res_2["description"]

    # 4 Stars -> Lv 5 (20%)
    res_4 = get_scaled_partner_skill("Gildane", 4, base_desc, "Sandstorm's Blessing", "Gildane Saddle")
    assert res_4["level"] == 5
    assert "increases Attack by 20%" in res_4["description"]


def test_gobfin_rank_scaling():
    base_desc = "While in team, increases player's attack power by 50%."

    # 0 Stars -> Lv 1 (10%)
    res_0 = get_scaled_partner_skill("Gobfin", 0, base_desc, "Angry Shark")
    assert res_0["level"] == 1
    assert "increases player's attack power by 10%" in res_0["description"]
    assert res_0["scaling_range"] == "10% -> 20%"

    # 4 Stars -> Lv 5 (20%)
    res_4 = get_scaled_partner_skill("Gobfin", 4, base_desc, "Angry Shark")
    assert res_4["level"] == 5
    assert "increases player's attack power by 20%" in res_4["description"]


def test_capacity_booster_scaling():
    base_desc = "While in team, helps carry supplies, increasing max carrying capacity by +50."

    res_0 = get_scaled_partner_skill("Cattiva", 0, base_desc, "Cat Helper")
    assert res_0["level"] == 1
    assert "+50" in res_0["description"]

    res_4 = get_scaled_partner_skill("Cattiva", 4, base_desc, "Cat Helper")
    assert res_4["level"] == 5
    assert "+100" in res_4["description"]


def test_query_pals_partner_skill_enrichment():
    engine = SQLiteEngine(world_id="test_static_pals")
    pals = engine.query_pals({})
    assert len(pals) > 0
    # Check that partner_skill is properly structured
    for p in pals:
        if p.get("partner_skill"):
            ps = p["partner_skill"]
            assert "name" in ps
            assert "description" in ps
            if ps.get("description"):
                assert "<" not in ps["description"]
                assert ">" not in ps["description"]
                assert "ReferenceMsgId" not in ps["description"]
                assert "EffectValue" not in ps["description"]
                assert "{" not in ps["description"]
                assert "}" not in ps["description"]


def test_relaxaurus_tag_stripping():
    raw_desc = (
        "Can be ridden.\r\n"
        "Can rapidly fire a missile launcher while mounted.\r\n"
        "[ReferenceMsgId_DamageUp]"
    )
    sanitized = sanitize_markup_elements(raw_desc, "Relaxaurus Lux")
    assert "ReferenceMsgId" not in sanitized
    assert sanitized == "Can be ridden. Can rapidly fire a missile launcher while mounted."


def test_knocklem_ignis_scaling():
    base_desc = (
        "When activated, a steel resolve increases Knocklem Ignis's Attack by 50% "
        "and Defense by 50% for a limited time."
    )
    # Lv 1 (0 Stars)
    res_0 = get_scaled_partner_skill("Knocklem Ignis", 0, base_desc, "Iron Guardian Mode")
    assert res_0["level"] == 1
    assert "increases Knocklem Ignis's Attack by 60% and Defense by 60%" in res_0["description"]
    assert res_0["scaling_range"] == "60% -> 100%"

    # Lv 5 (4 Stars)
    res_4 = get_scaled_partner_skill("WingGolem_Fire", 4, base_desc, "Iron Guardian Mode")
    assert res_4["level"] == 5
    assert "increases Knocklem Ignis's Attack by 100% and Defense by 100%" in res_4["description"]


def test_anubis_scaling():
    base_desc = (
        "When activated, Anubis changes the player's attack type to Ground "
        "and increases Attack by 50%. Occasionally evades attacks with a flash sidestep during battle."
    )
    # Lv 1 (0 Stars)
    res_0 = get_scaled_partner_skill("Anubis", 0, base_desc, "Guardian of the Desert")
    assert res_0["level"] == 1
    assert "increases Attack by 30%" in res_0["description"]
    assert res_0["scaling_range"] == "30% -> 50%"

    # Lv 5 (4 Stars)
    res_4 = get_scaled_partner_skill("Anubis", 4, base_desc, "Guardian of the Desert")
    assert res_4["level"] == 5
    assert "increases Attack by 50%" in res_4["description"]

