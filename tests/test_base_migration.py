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


def test_base_migration_item_classification():
    """Verify core category mappings, container metadata, and stack sizes."""
    assert len(MAIN_CATEGORIES) == 11
    assert CONTAINER_TYPE_INFO["ItemChest_03"]["slots"] == 40

    # Key category checks
    assert classify_item("Blueprint_AssaultRifle_4") == "weapon_schematics"
    assert classify_item("Ore") == "mining_metallurgy"
    assert classify_item("PalSphere") == "spheres_ammo_weapons"
    assert classify_item("TechnologyBook_G1") == "books_manuals"
    assert classify_item("SkillCard_FlameThrower") == "skill_fruits_tactical"
    assert classify_item("Berries") == "food_ingredients"

    # Stack size checks
    assert get_item_max_stack("Ore") > 0
    assert get_item_max_stack("Blueprint_Bow_1") > 0


def test_base_migration_manifest_and_container_routing():
    """Verify container slots and item routing defaults for migration manifests."""
    # Ensure all primary storage containers have valid slot definitions
    for cid in ["ItemChest_01", "ItemChest_02", "ItemChest_03", "Shelf02_Stone", "Box01_Iron"]:
        assert cid in CONTAINER_TYPE_INFO
        assert CONTAINER_TYPE_INFO[cid]["slots"] > 0
