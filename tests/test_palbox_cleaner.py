"""Tests for Palbox Cleaner & Audit System."""

import pytest
from unittest.mock import MagicMock
from click.testing import CliRunner

from palengine.analytics.palbox_cleaner import PalboxCleaner
from palengine.cli.main import cli


@pytest.fixture
def mock_cleaner_engine():
    engine = MagicMock()
    # Mock pals table with breeding power
    engine.conn.execute.return_value.fetchall.return_value = [
        {"display_name": "Jormuntide Ignis", "internal_name": "Jormuntide_Fire", "breeding_power": 310},
        {"display_name": "Anubis", "internal_name": "Anubis", "breeding_power": 570},
        {"display_name": "Lamball", "internal_name": "Lamball", "breeding_power": 1470},
        {"display_name": "Cattiva", "internal_name": "Cattiva", "breeding_power": 1460},
    ]
    return engine


def test_investment_protection(mock_cleaner_engine):
    cleaner = PalboxCleaner(mock_cleaner_engine)
    instances = [
        {
            "instance_id": "inst-rank4",
            "species": "Lamball",
            "display_name": "Lamball",
            "location": "palbox",
            "rank": 4,
            "level": 30,
            "passives": [{"name": "Slacker"}],  # Detrimental, but rank 4!
        },
        {
            "instance_id": "inst-souls",
            "species": "Cattiva",
            "display_name": "Cattiva",
            "location": "palbox",
            "rank": 0,
            "level": 25,
            "soul_points": {"attack": 10},
            "passives": [],
        },
    ]

    res = cleaner.analyze_palbox(instances)
    assert res["total_evaluated"] == 2
    assert res["keep_core_count"] == 2
    assert res["freeable_slots"] == 0
    for p in res["roster"]:
        assert p["audit_action"] == "keep_core"


def test_clean_2_synergy_and_junk_singletons(mock_cleaner_engine):
    cleaner = PalboxCleaner(mock_cleaner_engine)
    instances = [
        # Species keeper for Lamball
        {
            "instance_id": "inst-lamball-keeper",
            "species": "Lamball",
            "display_name": "Lamball",
            "location": "palbox",
            "rank": 0,
            "level": 50,
            "passives": [{"name": "Artisan"}, {"name": "Work Slave"}],
        },
        # Clean 2+2 synergy Lamball (different gender/traits)
        {
            "instance_id": "inst-lamball-synergy",
            "species": "Lamball",
            "display_name": "Lamball",
            "location": "palbox",
            "gender": "Female",
            "rank": 0,
            "level": 20,
            "passives": [{"name": "Serious"}, {"name": "Nocturnal"}],
        },
        # Junk singleton Lamball (Coward)
        {
            "instance_id": "inst-lamball-junk",
            "species": "Lamball",
            "display_name": "Lamball",
            "location": "palbox",
            "rank": 0,
            "level": 5,
            "passives": [{"name": "Coward"}],
        },
    ]

    res = cleaner.analyze_palbox(instances)
    assert res["total_evaluated"] == 3
    roster_by_id = {p["instance_id"]: p for p in res["roster"]}

    # Best Lamball is designated species keeper
    assert roster_by_id["inst-lamball-keeper"]["audit_action"] == "keep_core"
    assert roster_by_id["inst-lamball-keeper"]["is_species_keeper"] is True

    # 2nd Lamball is recognized as clean 2+2 breeding synergy
    assert roster_by_id["inst-lamball-synergy"]["audit_action"] == "keep_breeding"
    assert roster_by_id["inst-lamball-synergy"]["is_clean_2_synergy"] is True

    # 3rd Lamball is marked for condensation fodder (since Lamball keeper has rank 0)
    assert roster_by_id["inst-lamball-junk"]["audit_action"] == "condense"


def test_species_baseline_floor(mock_cleaner_engine):
    cleaner = PalboxCleaner(mock_cleaner_engine)
    # Even if instances have terrible stats, 1 of each species MUST be kept
    instances = [
        {
            "instance_id": "inst-anubis",
            "species": "Anubis",
            "display_name": "Anubis",
            "location": "palbox",
            "rank": 0,
            "level": 1,
            "passives": [{"name": "Slacker"}],
        },
        {
            "instance_id": "inst-cattiva",
            "species": "Cattiva",
            "display_name": "Cattiva",
            "location": "palbox",
            "rank": 0,
            "level": 1,
            "passives": [{"name": "Coward"}],
        },
    ]

    res = cleaner.analyze_palbox(instances)
    assert res["species_count"] == 2
    assert res["keep_core_count"] == 2
    for p in res["roster"]:
        assert p["audit_action"] == "keep_core"
        assert p["is_species_keeper"] is True


def test_cli_cleanup_palbox():
    runner = CliRunner()
    result = runner.invoke(cli, ["cleanup-palbox", "-n", "5"])
    assert result.exit_code == 0
    assert "PALBOX CLEANUP AUDIT SUMMARY" in result.output
    assert "Total Freeable Slots:" in result.output


def test_cli_cleanup_palbox_json():
    runner = CliRunner()
    result = runner.invoke(cli, ["--format", "json", "cleanup-palbox"])
    assert result.exit_code == 0
    assert '"total_evaluated":' in result.output
    assert '"freeable_slots":' in result.output


def test_multi_passive_and_legendary_priority(mock_cleaner_engine):
    cleaner = PalboxCleaner(mock_cleaner_engine)
    instances = [
        # 2-passive Pal (Serenity + Vanguard)
        {
            "instance_id": "inst-2pass",
            "species": "Helzephyr",
            "display_name": "Helzephyr",
            "location": "palbox",
            "gender": "Female",
            "rank": 0,
            "level": 1,
            "ivs": {"hp": 60, "melee": 97, "defense": 90},
            "passives": [{"name": "Serenity"}, {"name": "Vanguard"}],
        },
        # 3-passive Pal with Legend (Serenity + Legend + Vanguard)
        {
            "instance_id": "inst-3pass-legend",
            "species": "Helzephyr",
            "display_name": "Helzephyr",
            "location": "palbox",
            "gender": "Male",
            "rank": 0,
            "level": 1,
            "ivs": {"hp": 79, "melee": 68, "defense": 92},
            "passives": [{"name": "Serenity"}, {"name": "Legend"}, {"name": "Vanguard"}],
        },
    ]

    res = cleaner.analyze_palbox(instances)
    assert res["total_evaluated"] == 2
    roster_by_id = {p["instance_id"]: p for p in res["roster"]}

    # 3-passive Pal with Legend MUST have higher score and be designated Core Keeper
    keeper = roster_by_id["inst-3pass-legend"]
    assert keeper["audit_action"] == "keep_core"
    assert keeper["is_species_keeper"] is True

    # 2-passive Pal is preserved as breeding stock (opposite gender, clean 2+2 synergy)
    breeder = roster_by_id["inst-2pass"]
    assert breeder["audit_action"] == "keep_breeding"
    assert breeder["is_synergy_keeper"] is True


def test_duplicate_high_tier_and_synergy_condenses(mock_cleaner_engine):
    cleaner = PalboxCleaner(mock_cleaner_engine)
    instances = [
        # Core keeper: Best male with 3 passives
        {
            "instance_id": "inst-male-core",
            "species": "Helzephyr",
            "display_name": "Helzephyr",
            "location": "palbox",
            "gender": "Male",
            "rank": 0,
            "level": 1,
            "ivs": {"hp": 90, "melee": 90, "defense": 90},
            "passives": [{"name": "Serenity"}, {"name": "Legend"}, {"name": "Vanguard"}],
        },
        # Duplicate male with same 3 passives (lower IVs) -> should be condensed!
        {
            "instance_id": "inst-male-dup",
            "species": "Helzephyr",
            "display_name": "Helzephyr",
            "location": "palbox",
            "gender": "Male",
            "rank": 0,
            "level": 1,
            "ivs": {"hp": 30, "melee": 30, "defense": 30},
            "passives": [{"name": "Serenity"}, {"name": "Legend"}, {"name": "Vanguard"}],
        },
        # Best female with 2 passives (Serenity + Vanguard) -> keep breeding
        {
            "instance_id": "inst-female-best",
            "species": "Helzephyr",
            "display_name": "Helzephyr",
            "location": "palbox",
            "gender": "Female",
            "rank": 0,
            "level": 1,
            "ivs": {"hp": 80, "melee": 80, "defense": 80},
            "passives": [{"name": "Serenity"}, {"name": "Vanguard"}],
        },
        # Duplicate female with same 2 passives (lower IVs) -> should be condensed!
        {
            "instance_id": "inst-female-dup",
            "species": "Helzephyr",
            "display_name": "Helzephyr",
            "location": "palbox",
            "gender": "Female",
            "rank": 0,
            "level": 1,
            "ivs": {"hp": 20, "melee": 20, "defense": 20},
            "passives": [{"name": "Serenity"}, {"name": "Vanguard"}],
        },
    ]

    res = cleaner.analyze_palbox(instances)
    assert res["total_evaluated"] == 4
    roster_by_id = {p["instance_id"]: p for p in res["roster"]}

    # Core keeper
    assert roster_by_id["inst-male-core"]["audit_action"] == "keep_core"
    assert roster_by_id["inst-male-core"]["is_species_keeper"] is True

    # Duplicate male of same traits -> condensed
    assert roster_by_id["inst-male-dup"]["audit_action"] == "condense"

    # Best female 2-passive -> keep breeding
    assert roster_by_id["inst-female-best"]["audit_action"] == "keep_breeding"
    assert roster_by_id["inst-female-best"]["is_synergy_keeper"] is True

    # Duplicate female of same traits -> condensed
    assert roster_by_id["inst-female-dup"]["audit_action"] == "condense"

