"""Unit tests for Base-to-Base Container Migration and Logistics Engine."""

import os
import tempfile
import pytest

from palengine.logistics.base_migration import (
    CONTAINER_TYPE_INFO,
    MAIN_CATEGORIES,
    classify_item,
    get_item_max_stack,
    generate_construction_manifest,
)


def test_main_categories_definition():
    """Verify that all 10 core categories are properly configured."""
    assert len(MAIN_CATEGORIES) == 10
    cat_ids = {c["id"] for c in MAIN_CATEGORIES}
    expected_ids = {
        "mining_metallurgy",
        "structural_construction",
        "monster_drops",
        "weapon_schematics",
        "armor_schematics",
        "defence_attack_schematics",
        "books_growth_tech",
        "skill_fruits_tactical",
        "spheres_ammo_weapons",
        "food_ingredients",
    }
    assert cat_ids == expected_ids


def test_item_classification_weapons_and_schematics():
    """Verify blueprints and weapons are correctly partitioned."""
    assert classify_item("Blueprint_Handgun_3") == "weapon_schematics"
    assert classify_item("Blueprint_AssaultRifle_4") == "weapon_schematics"
    assert classify_item("Blueprint_Bow_2") == "weapon_schematics"

    # Armor Blueprints
    assert classify_item("Blueprint_ClothArmor_2") == "armor_schematics"
    assert classify_item("Blueprint_Head001_1") == "armor_schematics"
    assert classify_item("Blueprint_Shield_2") == "armor_schematics"

    # Defence & Attack Blueprints
    assert classify_item("Blueprint_Turret_1") == "defence_attack_schematics"
    assert classify_item("Blueprint_Trap_1") == "defence_attack_schematics"
    assert classify_item("Blueprint_DefenseWall_Metal") == "defence_attack_schematics"
    assert classify_item("Blueprint_Ring_Attack_2") == "defence_attack_schematics"


def test_item_classification_resources():
    """Verify raw materials and processed goods map correctly."""
    # Mining & Metallurgy
    assert classify_item("Ore") == "mining_metallurgy"
    assert classify_item("CopperOre") == "mining_metallurgy"
    assert classify_item("Coal") == "mining_metallurgy"
    assert classify_item("Sulfur") == "mining_metallurgy"
    assert classify_item("IronIngot") == "mining_metallurgy"
    assert classify_item("StealIngot") == "mining_metallurgy"
    assert classify_item("Plasteel") == "mining_metallurgy"

    # Structural & Construction
    assert classify_item("Wood") == "structural_construction"
    assert classify_item("Stone") == "structural_construction"
    assert classify_item("Fiber") == "structural_construction"
    assert classify_item("Cement") == "structural_construction"
    assert classify_item("Polymer") == "structural_construction"
    assert classify_item("Circuit") == "structural_construction"

    # Monster Drops & Biologicals
    assert classify_item("Horn") == "monster_drops"
    assert classify_item("Bone") == "monster_drops"
    assert classify_item("Leather") == "monster_drops"
    assert classify_item("Wool") == "monster_drops"
    assert classify_item("FireOrgan") == "monster_drops"
    assert classify_item("ElectricOrgan") == "monster_drops"
    assert classify_item("Diamond") == "monster_drops"


def test_item_classification_consumables_and_combat():
    """Verify combat, books, skill fruits, and food categories."""
    # Combat & Weapons
    assert classify_item("PalSphere") == "spheres_ammo_weapons"
    assert classify_item("PalSphere_Tera") == "spheres_ammo_weapons"
    assert classify_item("Arrow") == "spheres_ammo_weapons"
    assert classify_item("HandgunBullet") == "spheres_ammo_weapons"
    assert classify_item("ReinforcedArrow") == "spheres_ammo_weapons"
    assert classify_item("Money") == "spheres_ammo_weapons"

    # Books & Tech
    assert classify_item("TechnologyBook_G1") == "books_growth_tech"
    assert classify_item("AncientTechnologyBook_G1") == "books_growth_tech"
    assert classify_item("PalUpgradeStone") == "books_growth_tech"
    assert classify_item("PalSoul") == "books_growth_tech"

    # Skill Fruits & Tactical
    assert classify_item("SkillCard_FlameThrower") == "skill_fruits_tactical"
    assert classify_item("Medicines") == "skill_fruits_tactical"
    assert classify_item("Potion") == "skill_fruits_tactical"

    # Food & Crops
    assert classify_item("Berries") == "food_ingredients"
    assert classify_item("Wheat") == "food_ingredients"
    assert classify_item("Milk") == "food_ingredients"
    assert classify_item("Egg") == "food_ingredients"
    assert classify_item("Cake") == "food_ingredients"


def test_container_metadata():
    """Verify standard container capacities."""
    assert CONTAINER_TYPE_INFO["ItemChest_01"]["slots"] == 16  # Wooden
    assert CONTAINER_TYPE_INFO["ItemChest_02"]["slots"] == 32  # Metal
    assert CONTAINER_TYPE_INFO["ItemChest_03"]["slots"] == 40  # Refined
    assert CONTAINER_TYPE_INFO["CoolerBox"]["slots"] == 10     # Cooler
    assert CONTAINER_TYPE_INFO["Shelf02_Stone"]["name"] == "Antique Wardrobe"
    assert CONTAINER_TYPE_INFO["Shelf02_Stone"]["slots"] == 20


def test_item_max_stack_defaults():
    """Verify stack size lookups."""
    assert get_item_max_stack("Arrow") == 9999
    assert get_item_max_stack("Wood") == 9999
    assert get_item_max_stack("Blueprint_Handgun_3") == 1


def test_manifest_source_container_type_preservation(monkeypatch):
    """Verify items in Metal Chests are never routed into Cooler Boxes in manifest."""
    from palengine.logistics.base_migration import generate_construction_manifest

    # Mock inspect_base_containers to return food items inside a Metal Chest (ItemChest_02)
    fake_containers = {
        "base_src": [
            {
                "instance_id": "inst-1",
                "container_id": "cid-1",
                "map_object_id": "ItemChest_02",  # Metal Chest
                "custom_name": "source_metal",
                "slot_count": 32,
                "items": [
                    {"item_id": "BerrySeeds", "count": 1056, "slot_index": 0},
                    {"item_id": "Honey", "count": 9437, "slot_index": 1},
                    {"item_id": "Sweet", "count": 8, "slot_index": 2},
                ],
            }
        ],
        "base_dst": [],
    }

    monkeypatch.setattr(
        "palengine.logistics.base_migration.inspect_base_containers",
        lambda _: fake_containers,
    )

    manifest_res = generate_construction_manifest(
        sav_path="dummy_path.sav",
        source_base_id="base_src",
        target_base_id="base_dst",
    )

    # Check that Food category recommended container is strictly Metal Chest (ItemChest_02), NOT CoolerBox
    manifest = manifest_res["manifest"]
    assert len(manifest) == 1
    entry = manifest[0]
    assert entry["category_id"] == "food_ingredients"
    assert entry["recommended_container_type"] == "ItemChest_02"
    assert entry["recommended_container_name"] == "Metal Chest"
    assert entry["container_capacity"] == 32
    assert entry["box_label"] == "Food 1"
    assert len(entry["box_label"]) <= 24


def test_wardrobe_items_route_to_metal_chest(monkeypatch):
    """Verify Antique Wardrobe items route to standard Metal Chests (ItemChest_02), not new wardrobes."""
    from palengine.logistics.base_migration import generate_construction_manifest

    fake_containers = {
        "base_src": [
            {
                "instance_id": "inst-wardrobe",
                "container_id": "cid-w",
                "map_object_id": "Shelf02_Stone",  # Antique Wardrobe
                "custom_name": "old_wardrobe",
                "slot_count": 20,
                "items": [
                    {"item_id": "Blueprint_Handgun_3", "count": 1, "slot_index": 0},
                    {"item_id": "Blueprint_AssaultRifle_4", "count": 1, "slot_index": 1},
                ],
            }
        ],
        "base_dst": [],
    }

    monkeypatch.setattr(
        "palengine.logistics.base_migration.inspect_base_containers",
        lambda _: fake_containers,
    )

    manifest_res = generate_construction_manifest(
        sav_path="dummy_path.sav",
        source_base_id="base_src",
        target_base_id="base_dst",
    )

    manifest = manifest_res["manifest"]
    assert len(manifest) == 1
    entry = manifest[0]
    assert entry["category_id"] == "weapon_schematics"
    assert entry["recommended_container_type"] == "ItemChest_02"
    assert entry["recommended_container_name"] == "Metal Chest"
    assert entry["box_label"] == "Wpn Schem 1"

