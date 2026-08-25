"""Tests for Boss Counter Party Recommender."""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from palengine.analytics.boss_recommender import BossPartyRecommender, BOSS_REGISTRY
from palengine.cli.main import cli


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    # Mock static pals
    engine.query_pals.return_value = [
        {"internal_name": "Jormuntide_Fire", "name": "Jormuntide Ignis", "display_name": "Jormuntide Ignis", "element_1": "Dragon", "element_2": "Fire", "hp": 130, "attack_melee": 130, "defense": 100},
        {"internal_name": "Chillet", "name": "Chillet", "display_name": "Chillet", "element_1": "Ice", "element_2": "Dragon", "hp": 90, "attack_melee": 85, "defense": 75},
        {"internal_name": "Gobfin", "name": "Gobfin", "display_name": "Gobfin", "element_1": "Water", "element_2": None, "hp": 85, "attack_melee": 85, "defense": 70},
        {"internal_name": "Anubis", "name": "Anubis", "display_name": "Anubis", "element_1": "Ground", "element_2": None, "hp": 120, "attack_melee": 130, "defense": 100},
    ]
    # Mock active skills
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"name": "Dragon Cannon", "element": "Dragon", "power": 30, "cool_time": 2},
        {"name": "Draconic Breath", "element": "Dragon", "power": 70, "cool_time": 15},
        {"name": "Dragon Meteor", "element": "Dragon", "power": 150, "cool_time": 55},
    ]
    engine.conn.cursor.return_value = cursor
    engine.find_breeding_path.return_value = [{"parent1": "Relaxaurus", "parent2": "Sparkit", "child": "Relaxaurus Lux"}]
    return engine


@pytest.fixture
def mock_instances():
    return [
        {
            "instance_id": "inst-1",
            "species": "Jormuntide Ignis",
            "display_name": "Jormuntide Ignis",
            "level": 55,
            "gender": "Male",
            "rank": 0,
            "iv_hp": 80,
            "iv_melee": 85,
            "iv_defense": 75,
            "location": "palbox",
            "passives": [{"name": "Ferocious"}, {"name": "Musclehead"}],
        },
        {
            "instance_id": "inst-2",
            "species": "Chillet",
            "display_name": "Chillet",
            "level": 40,
            "gender": "Female",
            "rank": 0,
            "iv_hp": 70,
            "iv_melee": 65,
            "iv_defense": 60,
            "location": "party",
            "passives": [{"name": "Vanguard"}],
        },
        {
            "instance_id": "inst-3",
            "species": "Gobfin",
            "display_name": "Gobfin",
            "level": 45,
            "gender": "Male",
            "rank": 0,
            "iv_hp": 50,
            "iv_melee": 80,
            "iv_defense": 50,
            "location": "palbox",
            "passives": [{"name": "Vanguard"}],
        },
        {
            "instance_id": "inst-4",
            "species": "Anubis",
            "display_name": "Anubis",
            "level": 60,
            "gender": "Female",
            "rank": 2,
            "iv_hp": 90,
            "iv_melee": 95,
            "iv_defense": 90,
            "location": "base",
            "location_details_base_camp_name": "Mining Camp",
            "passives": [{"name": "Legend"}, {"name": "Burly Body"}],
        },
    ]


def test_resolve_boss_tower(mock_engine):
    recommender = BossPartyRecommender(mock_engine)
    boss = recommender.resolve_boss("Victor & Shadowbeak")
    assert boss is not None
    assert boss["canonical_name"] == "Victor & Shadowbeak"
    assert "Dark" in boss["elements"]
    assert "Dragon" in boss["weaknesses"]


def test_resolve_boss_alpha(mock_engine):
    recommender = BossPartyRecommender(mock_engine)
    boss = recommender.resolve_boss("Jetragon")
    assert boss is not None
    assert "Jetragon" in boss["canonical_name"]
    assert "Ice" in boss["weaknesses"]


def test_recommend_party_for_boss(mock_engine, mock_instances):
    mock_engine.query_instances.return_value = mock_instances
    recommender = BossPartyRecommender(mock_engine)
    
    result = recommender.recommend_party_for_boss("Victor & Shadowbeak")
    
    assert "boss_profile" in result
    assert "team_a_pal_dps" in result
    assert "team_b_mounted_player_dps" in result
    assert "team_c_balanced_hybrid" in result
    
    # Check human-readable representation and no raw GUIDs
    team_a = result["team_a_pal_dps"]
    assert len(team_a) > 0
    first_member = team_a[0]
    assert "species" in first_member
    assert "gender" in first_member
    assert "rank" in first_member
    assert "location" in first_member
    assert "passives" in first_member


def test_cli_boss_party_command():
    runner = CliRunner()
    mock_output = {
        "boss_profile": {
            "canonical_name": "Victor & Shadowbeak",
            "location": "Astral Mountains",
            "level": 50,
            "hp": 200750,
            "elements": ["Dark"],
            "weaknesses": ["Dragon"],
            "dangerous_moves": ["Divine Disaster"],
            "tactics": "Use arena pillars.",
        },
        "team_a_pal_dps": [{
            "species": "Jormuntide Ignis",
            "gender": "Male",
            "level": 55,
            "rank": "0 Star",
            "element": "Dragon/Fire",
            "location": "Palbox",
            "passives": ["Ferocious"],
            "ivs": "80/85/75",
        }],

        "team_b_mounted_player_dps": [],
        "team_c_balanced_hybrid": [],
        "recommended_waza": [{"name": "Dragon Cannon", "element": "Dragon", "power": 30, "ct": "2s"}],
        "breeding_projects": [],
    }
    
    with patch("palengine.db.sqlite_engine.SQLiteEngine.__init__", return_value=None), \
         patch("palengine.analytics.boss_recommender.BossPartyRecommender.recommend_party_for_boss", return_value=mock_output), \
         patch("palengine.cli.main.get_resolved_save_path", return_value="dummy_path"):
        result = runner.invoke(cli, ["boss-party", "Victor & Shadowbeak"])
        assert result.exit_code == 0
        assert "Victor & Shadowbeak" in result.output
        assert "Jormuntide Ignis" in result.output
        assert "Dragon Cannon" in result.output

