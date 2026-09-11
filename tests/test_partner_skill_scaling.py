"""Unit tests for Partner Skill Scaling and Tag Resolution in PalEngine."""

import pytest
from palengine.analytics.partner_skill_scaling import (
    get_scaled_partner_skill,
    sanitize_markup_elements,
)
from palengine.db.sqlite_engine import SQLiteEngine


def test_partner_skill_scaling_mechanics():
    """Validates star rank scaling across attack buffs, carrying capacity, and defense."""
    # 1. Attack scaling (Gildane)
    gildane_desc = "While mounted, changes player's attack type to Ground and increases Attack by 50%."
    res_0 = get_scaled_partner_skill("Gildane", 0, gildane_desc, "Sandstorm's Blessing")
    res_4 = get_scaled_partner_skill("Gildane", 4, gildane_desc, "Sandstorm's Blessing")
    assert res_0["level"] == 1 and "increases Attack by 5%" in res_0["description"]
    assert res_4["level"] == 5 and "increases Attack by 20%" in res_4["description"]

    # 2. Capacity booster (Cattiva)
    cattiva_desc = "While in team, helps carry supplies, increasing max carrying capacity by +50."
    assert "+50" in get_scaled_partner_skill("Cattiva", 0, cattiva_desc, "Cat Helper")["description"]
    assert "+100" in get_scaled_partner_skill("Cattiva", 4, cattiva_desc, "Cat Helper")["description"]

    # 3. Party attack buffer (Gobfin)
    gobfin_desc = "While in team, increases player's attack power by 10%."
    res_gob = get_scaled_partner_skill("Gobfin", 4, gobfin_desc, "Angry Shark")
    assert "increases player's attack power by 20%" in res_gob["description"]

    # 4. Multi-param token scaling (Menasting Terra)
    menasting_desc = "While fighting together, player's Defense increases by {Passive2_EffectValue1} and Electric damage decreases by {Passive1_EffectValue1}."
    res_men = get_scaled_partner_skill("Menasting Terra", 4, menasting_desc, "Steel Scorpion")
    assert "Defense increases by 20%" in res_men["description"]
    assert "Electric damage decreases by 80%" in res_men["description"]


def test_partner_skill_sanitization_and_enrichment():
    """Validates markup tag stripping and verifies clean partner skill text in database query."""
    raw_markup = (
        "Can be ridden. While mounted, changes player's attack to "
        "<img id=|ElemIcon_Ground|/><uiCommon id=|COMMON_ELEMENT_NAME_Earth| style=|Elem_Ground|/> "
        "and increases Attack by <Status_Up>{Passive2_EffectValue1}%</>.[ReferenceMsgId_DamageUp]"
    )
    sanitized = sanitize_markup_elements(raw_markup, "Gildane")
    assert "Ground" in sanitized
    assert "<" not in sanitized and ">" not in sanitized and "ReferenceMsgId" not in sanitized

    # Verify live engine enrichment produces zero raw unescaped template tags
    engine = SQLiteEngine(world_id="NONE")
    pals = engine.query_pals({})
    assert len(pals) > 0
    for p in pals:
        ps = p.get("partner_skill")
        if ps and ps.get("description"):
            desc = ps["description"]
            assert "<" not in desc and ">" not in desc and "{" not in desc and "}" not in desc
