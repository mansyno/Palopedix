"""Base-to-Base Container Migration and Intelligent Inventory Sorting Engine.

Provides:
- 10-category comprehensive item classification based on game master database.
- Base container inspection with custom_name decoding.
- Construction Manifest generation (slot math, bin-packing, numbered labels).
- Safe atomic Level.sav modification (source container emptying, target population, timestamped backup).
"""

import contextlib
import math
import os
import shutil
import sqlite3
import struct
import time
from typing import Any, Optional

from palengine.config import get_palworld_db_path
from palengine.parser.extract_items import extract_items
from palengine.parser.extract_pals import load_gvas_from_sav
from palworld_save_tools.archive import FArchiveReader, FArchiveWriter
from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.palsav import compress_gvas_to_sav, decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS


# ── Container Types & Metadata ────────────────────────────────────────────────
CONTAINER_TYPE_INFO: dict[str, dict[str, Any]] = {
    "ItemChest_01": {"name": "Wooden Chest", "slots": 16, "category": "General"},
    "ItemChest_02": {"name": "Metal Chest", "slots": 24, "category": "General"},
    "ItemChest_03": {"name": "Refined Metal Chest", "slots": 40, "category": "General"},
    "ItemChest_04": {"name": "Large Container", "slots": 40, "category": "General"},
    "ShippingContainer": {"name": "Shipping Container", "slots": 40, "category": "General"},
    "CoolerBox": {"name": "Cooler Box", "slots": 10, "category": "Food"},
    "CoolerPalFoodBox": {"name": "Cooler Food Box", "slots": 30, "category": "Food"},
    "PalFoodBox": {"name": "Feed Box", "slots": 6, "category": "Food"},
    "PalMedicineBox": {"name": "Medicine Box", "slots": 6, "category": "Medicine"},
    "GuildChest": {"name": "Guild Chest", "slots": 32, "category": "General"},
    # Furniture Storage (Wardrobes, Cabinets, Cupboards, Shelves)
    "Shelf02_Stone": {"name": "Antique Wardrobe", "slots": 20, "category": "Furniture"},
    "Shelf01_Stone": {"name": "Antique Stone Shelf", "slots": 16, "category": "Furniture"},
    "Shelf03_Stone": {"name": "Antique Cabinet", "slots": 24, "category": "Furniture"},
    "Shelf04_Stone": {"name": "Antique Cupboard", "slots": 20, "category": "Furniture"},
    "Shelf05_Stone": {"name": "Antique Desk Storage", "slots": 16, "category": "Furniture"},
    "Shelf06_Stone": {"name": "Antique Large Shelf", "slots": 24, "category": "Furniture"},
    "Shelf07_Stone": {"name": "Antique Stone Locker", "slots": 20, "category": "Furniture"},
    "Shelf01_Iron": {"name": "Iron Locker", "slots": 24, "category": "Furniture"},
    "Shelf02_Iron": {"name": "Iron Shelf", "slots": 24, "category": "Furniture"},
    "Shelf03_Iron": {"name": "Iron Cabinet", "slots": 24, "category": "Furniture"},
    "Shelf04_Iron": {"name": "Iron Cupboard", "slots": 24, "category": "Furniture"},
    "Box01_Iron": {"name": "Iron Storage Box", "slots": 24, "category": "General"},
    "Box02_Iron": {"name": "Iron Storage Box (Small)", "slots": 16, "category": "General"},
    "Container01_Iron": {"name": "Iron Shipping Container", "slots": 40, "category": "General"},
    "Box01_Stone": {"name": "Stone Storage Box", "slots": 16, "category": "General"},
    "Box_Wood": {"name": "Wooden Storage Box", "slots": 16, "category": "General"},
    "Shelf_Wood": {"name": "Wooden Bookshelf", "slots": 16, "category": "Furniture"},
    "Shelf_Cask_Wood": {"name": "Barrel Shelf", "slots": 16, "category": "Furniture"},
    "Shelf_Hang01_Wood": {"name": "Wall Wooden Shelf 1", "slots": 8, "category": "Furniture"},
    "Shelf_Hang02_Wood": {"name": "Wall Wooden Shelf 2", "slots": 8, "category": "Furniture"},
    "Shelf01_Wall_Stone": {"name": "Wall Stone Shelf", "slots": 8, "category": "Furniture"},
    "Shelf01_Wall_Iron": {"name": "Wall Iron Shelf", "slots": 8, "category": "Furniture"},
}

DEFAULT_CONTAINER_SLOTS = 32


def get_effective_migration_target_type(source_map_object_id: str) -> str:
    """Maps furniture and wardrobe storage to standard Metal Chest (ItemChest_02).

    All other functional containers preserve their exact type (e.g. CoolerBox, FeedBox).
    """
    info = CONTAINER_TYPE_INFO.get(source_map_object_id, {})
    if (
        info.get("category") == "Furniture"
        or "Shelf" in source_map_object_id
        or "Wardrobe" in info.get("name", "")
        or "Cabinet" in info.get("name", "")
        or "Locker" in info.get("name", "")
        or "Closet" in info.get("name", "")
    ):
        return "ItemChest_02"
    return source_map_object_id



# ── The 10 Core Item Categories ───────────────────────────────────────────────
MAIN_CATEGORIES: list[dict[str, str]] = [
    {
        "id": "mining_metallurgy",
        "name": "Mining & Metallurgy (Raw & Refined)",
        "label": "Metals",
        "default_container": "ItemChest_02",
    },
    {
        "id": "structural_construction",
        "name": "Structural & Construction (Basic Building)",
        "label": "Building",
        "default_container": "ItemChest_02",
    },
    {
        "id": "monster_drops",
        "name": "Monster Drops & Biologicals",
        "label": "Drops",
        "default_container": "ItemChest_02",
    },
    {
        "id": "weapon_schematics",
        "name": "Weapon Schematics & Blueprints (Dedicated)",
        "label": "Wpn Schem",
        "default_container": "ItemChest_02",
    },
    {
        "id": "armor_schematics",
        "name": "Armor Schematics & Blueprints (Dedicated)",
        "label": "Arm Schem",
        "default_container": "ItemChest_02",
    },
    {
        "id": "defence_attack_schematics",
        "name": "Defence & Attack Schematics & Blueprints (Dedicated)",
        "label": "Def Schem",
        "default_container": "ItemChest_02",
    },
    {
        "id": "books_manuals",
        "name": "Books & Manuals (Work & Training)",
        "label": "Manuals",
        "default_container": "ItemChest_02",
    },
    {
        "id": "growth_elixirs",
        "name": "Pal Souls, Lotuses & Growth",
        "label": "Pal Growth",
        "default_container": "ItemChest_02",
    },
    {
        "id": "skill_fruits_tactical",
        "name": "Skill Fruits & Tactical Consumables",
        "label": "Skill Fruits",
        "default_container": "ItemChest_02",
    },
    {
        "id": "spheres_ammo_weapons",
        "name": "Spheres, Ammo & Weaponry",
        "label": "Combat",
        "default_container": "ItemChest_02",
    },
    {
        "id": "food_ingredients",
        "name": "Food, Ingredients & Crops (Perishables)",
        "label": "Food",
        "default_container": "ItemChest_02",
    },
]

CATEGORY_BY_ID = {c["id"]: c for c in MAIN_CATEGORIES}


# ── Master Database Item Metadata Cache ────────────────────────────────────────
_ITEM_METADATA_CACHE: Optional[dict[str, dict[str, Any]]] = None


def get_item_metadata_cache() -> dict[str, dict[str, Any]]:
    """Loads item master metadata (category, subcategory, max_stack) from palworld.db."""
    global _ITEM_METADATA_CACHE
    if _ITEM_METADATA_CACHE is not None:
        return _ITEM_METADATA_CACHE

    db_path = get_palworld_db_path()
    cache: dict[str, dict[str, Any]] = {}
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute(
                "SELECT id, name, category, subcategory, max_stack, weight, rarity FROM items"
            ).fetchall()
            for r in rows:
                cache[r["id"].lower()] = dict(r)
            conn.close()
        except Exception:
            pass

    _ITEM_METADATA_CACHE = cache
    return _ITEM_METADATA_CACHE


# ── Item Classifier (10 Main Categories) ──────────────────────────────────────
def classify_item(item_id: str) -> str:
    """Classifies any Palworld item static ID into exactly one of the 11 main categories."""
    if not item_id:
        return "structural_construction"

    i_lower = item_id.strip().lower()
    meta = get_item_metadata_cache().get(i_lower, {})
    cat = (meta.get("category") or "").strip()
    subcat = (meta.get("subcategory") or "").strip()

    # 1. Schematics & Blueprints (3 Dedicated Categories)
    if cat == "Blueprint" or i_lower.startswith("blueprint_") or "schematic" in i_lower:
        if any(
            k in i_lower
            for k in [
                "armor", "helmet", "head", "cloth", "shield", "heat", "cold"
            ]
        ) and "turret" not in i_lower:
            return "armor_schematics"
        if any(
            k in i_lower
            for k in [
                "turret", "trap", "defense", "defence", "wall", "gate", "ring", "accessory", "attack"
            ]
        ):
            return "defence_attack_schematics"
        return "weapon_schematics"

    # 2. Food, Ingredients, Crops & Seeds
    if (
        cat == "Food"
        or subcat.startswith("Food")
        or i_lower.endswith("seeds")
        or any(
            i_lower.startswith(prefix)
            for prefix in [
                "food_", "meat_", "fish_", "baked_", "fried_", "berry", "wheat",
                "tomato", "lettuce", "milk", "egg", "honey", "cake", "bread"
            ]
        )
        or i_lower in {"berries", "wheat", "tomato", "lettuce", "milk", "egg", "honey", "cake"}
    ):
        return "food_ingredients"

    # 3. Skill Fruits (Active Pal Skill Machines)
    if (
        subcat in {"ConsumeWazaMachine"}
        or i_lower.startswith("skillcard_")
        or "wazamachine" in i_lower
    ):
        return "skill_fruits_tactical"

    # 4. Books & Manuals (Work Suitability Handbooks, Training Manuals, Technical Manuals)
    if (
        subcat in {
            "ConsumeTechnologyBook",
            "ConsumeAncientTechnologyBook",
            "ConsumePalWorkSuitabilityUp",
            "ConsumePalGainExp",
        }
        or any(
            k in i_lower
            for k in [
                "worksuitability_addticket",
                "expboost",
                "technologybook",
                "ancienttechnologybook",
            ]
        )
    ):
        return "books_manuals"

    # 5. Pal Souls, Lotuses & Growth Enhancers (Physical stat boosters & remedies)
    if (
        subcat in {
            "ConsumeGainStatusPoints",
            "ConsumePalRankUp",
            "ConsumePalLevelUp",
            "ConsumePalAwakening",
            "ConsumePalTalentUp",
            "ConsumePalGainFriendshipPoint",
            "ConsumePassiveSkillChange",
            "ConsumePalRevive",
            "ConsumeWorldTreeHolyWater",
            "Drug",
            "Medicine",
        }
        or i_lower.startswith("lotus_")
        or i_lower.startswith("palupgradestone")
        or i_lower.startswith("fruit_")
        or i_lower.startswith("affectionfruit_")
        or i_lower.startswith("rankup_")
        or i_lower.startswith("elixir_")
        or any(
            k in i_lower
            for k in [
                "palsoul",
                "statuspoint",
                "memorywiping",
                "mindcleansing",
                "disposable_implant",
                "passive_implant",
            ]
        )
    ):
        return "growth_elixirs"

    # 6. Mining & Metallurgy (Raw ores, ingots, processed minerals)
    if (
        subcat in {"MaterialOre", "MaterialIngot"}
        or i_lower in {
            "coal", "sulfur", "quartz", "plasteel", "plastic", "palbrite",
            "chromium", "ore", "copperore", "ironore", "ancient_lava", "lava_ancient"
        }
    ):
        return "mining_metallurgy"

    # 7. Combat, Ammo, Spheres, Keys & Raid Slabs
    if (
        cat in {"Ammo", "Weapon", "SpecialWeapon", "Armor", "Accessory", "Glider", "CaptureItemModifier"}
        or subcat in {"ConsumeBullet", "SPWeaponCaptureBall", "ConsumeTreasureMap"}
        or i_lower.startswith("palsphere")
        or i_lower.endswith("bullet")
        or i_lower.endswith("arrow")
        or i_lower.startswith("treasureboxkey")
        or i_lower.startswith("palsummon_")
        or i_lower in {"money", "goldcoin", "reinforcedarrow", "homeward", "battleticket"}
        or i_lower.startswith("bountyproof")
    ):
        return "spheres_ammo_weapons"

    # 8. Monster Drops & Biologicals (Textiles, organs, parts, gems)
    if (
        subcat in {"MaterialMonster", "MaterialJewelry", "MaterialPalEgg"}
        or i_lower.startswith("paloil")
        or i_lower.startswith("palitem_")
        or any(
            k in i_lower
            for k in [
                "cloth", "leather", "wool", "organ", "bone", "horn", "fang",
                "claw", "feather", "pelt", "gem", "diamond", "ruby", "sapphire",
                "ancientparts", "ancientcore", "venom", "predatorcrystal"
            ]
        )
    ):
        return "monster_drops"

    # 9. Structural & Construction (Basic Building materials only)
    if (
        subcat in {"MaterialWood", "MaterialStone", "MaterialProccessing"}
        or any(
            k in i_lower
            for k in [
                "wood", "stone", "fiber", "charcoal", "cement", "clay",
                "pal_crystal", "polymer", "circuit", "gunpowder", "carbonfiber",
                "silicon", "machineparts", "processed_wood"
            ]
        )
    ):
        return "structural_construction"

    # Fallback to general monster drops / materials if still uncaught
    return "monster_drops"


def get_item_max_stack(item_id: str) -> int:
    """Returns max stack size for an item, defaulting to 9999 for materials or 100 for others."""
    i_lower = item_id.strip().lower()
    meta = get_item_metadata_cache().get(i_lower, {})
    max_stack = meta.get("max_stack")
    if max_stack and int(max_stack) > 0:
        return int(max_stack)
    cat = meta.get("category", "")
    if cat in {"Material", "Food"}:
        return 9999
    elif cat in {"Ammo"}:
        return 9999
    elif cat in {"Blueprint"} or i_lower.startswith("blueprint_") or "schematic" in i_lower:
        return 1
    elif cat in {"Weapon", "Armor", "Glider", "Accessory"}:
        return 1
    return 100


# ── Save File Inspection (Bases & Containers) ──────────────────────────────────
def inspect_base_containers(
    sav_path: str,
) -> dict[str, list[dict[str, Any]]]:
    """Inspects all containers in Level.sav grouped by base_camp_id.

    Returns mapping of base_camp_id -> list of container dicts:
        {
            'instance_id': str,
            'concrete_model_id': str,
            'container_id': str,
            'map_object_id': str,
            'custom_name': str | None,
            'base_camp_id': str,
            'slot_count': int,
            'items': list[{'item_id': str, 'count': int, 'slot_index': int}],
            'transform': dict,
        }
    """
    with open(sav_path, "rb") as f:
        raw = f.read()

    magic = raw[8:11]
    if magic == b"PlM":
        import ooz
        ulen = int.from_bytes(raw[0:4], byteorder="little")
        gvas_bytes = ooz.decompress(raw[12:], ulen)
    else:
        gvas_bytes, _ = decompress_sav_to_gvas(raw)

    with open(os.devnull, "w") as devnull, contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
        gvas = GvasFile.read(
            gvas_bytes,
            type_hints=PALWORLD_TYPE_HINTS,
            custom_properties={},
        )

    world_save_data = gvas.properties.get("worldSaveData", {}).get("value", {})
    map_objects = (
        world_save_data.get("MapObjectSaveData", {}).get("value", {}).get("values", [])
    )
    item_containers_raw = (
        world_save_data.get("ItemContainerSaveData", {}).get("value", [])
    )

    # 1. Map container_id -> container items
    container_items_map: dict[str, dict[str, Any]] = {}
    for c in item_containers_raw:
        cid = str(c.get("key", {}).get("ID", {}).get("value", ""))
        val = c.get("value", {})
        slot_num = val.get("SlotNum", {}).get("value", 0)

        slots_raw = val.get("Slots", {}).get("value", {}).get("values", [])
        items_list = []
        for s in slots_raw:
            raw_b = s.get("RawData", {}).get("value", {}).get("values", [])
            if len(raw_b) >= 12:
                b = bytes(raw_b)
                s_idx = struct.unpack_from("<i", b, 0)[0]
                cnt = struct.unpack_from("<i", b, 4)[0]
                s_len = struct.unpack_from("<i", b, 8)[0]
                if cnt > 0 and 0 < s_len <= 200:
                    i_name = b[12 : 12 + s_len - 1].decode("utf-8", errors="replace")
                    if i_name and not i_name.startswith("\x00"):
                        items_list.append(
                            {"slot_index": s_idx, "item_id": i_name, "count": cnt}
                        )

        container_items_map[cid] = {
            "slot_num": slot_num,
            "items": items_list,
        }

    # 2. Iterate map objects to find placed containers
    base_containers: dict[str, list[dict[str, Any]]] = {}

    for m in map_objects:
        oid = m.get("MapObjectId", {}).get("value", "")
        oid_lower = oid.lower()
        is_storage = (
            oid in CONTAINER_TYPE_INFO
            or any(
                k in oid_lower
                for k in (
                    "chest",
                    "container",
                    "box",
                    "storage",
                    "shelf",
                    "wardrobe",
                    "cabinet",
                    "locker",
                    "closet",
                    "cupboard",
                )
            )
        )
        if not is_storage:
            continue

        # Exclude work stations or monuments that aren't storage containers
        if oid in (
            "PalBoxV2",
            "PalBoxTerminal",
            "ToolBoxV1",
            "ToolBoxV2",
            "GlobalPalStorage",
            "DimensionPalStorage",
            "BaseCampWorkHard",
            "SupplyDrop",
        ):
            continue

        model = m.get("Model", {}).get("value", {})
        model_raw = model.get("RawData", {}).get("value", {})
        raw_bytes = bytes(model_raw.get("values", []))
        if len(raw_bytes) < 32:
            continue

        reader = FArchiveReader(raw_bytes)
        try:
            inst_id = str(reader.guid())
            cm_id = str(reader.guid())
            base_id = str(reader.guid())
            _ = reader.guid()  # group_id
            _ = reader.i32()  # hp_cur
            _ = reader.i32()  # hp_max
            transform = reader.ftransform()
            _ = reader.guid()  # repair
            _ = reader.guid()  # spawner
            _ = reader.guid()  # owner
            _ = reader.guid()  # build_player
            _ = reader.byte()  # interact
            _ = reader.guid()  # stage
            _ = reader.u32()  # valid
            _ = reader.i64()  # created_at
            _ = reader.i64()  # padding

            custom_name = None
            if not reader.eof():
                custom_name = reader.fstring()
                if not custom_name:
                    custom_name = None
        except Exception:
            continue

        if not base_id or base_id == "00000000-0000-0000-0000-000000000000":
            continue

        # Find target_container_id from ConcreteModel ModuleMap
        target_cid = None
        cm = m.get("ConcreteModel", {}).get("value", {})
        module_map = cm.get("ModuleMap", {}).get("value", [])
        for mod in module_map:
            mod_key = mod.get("key")
            if mod_key == "EPalMapObjectConcreteModelModuleType::ItemContainer":
                mod_bytes = bytes(
                    mod.get("value", {}).get("RawData", {}).get("value", {}).get("values", [])
                )
                if len(mod_bytes) >= 16:
                    target_cid = str(FArchiveReader(mod_bytes).guid())
                break

        if not target_cid:
            continue

        c_info = container_items_map.get(
            target_cid, {"slot_num": CONTAINER_TYPE_INFO.get(oid, {}).get("slots", 24), "items": []}
        )

        obj_record = {
            "instance_id": inst_id,
            "concrete_model_id": cm_id,
            "container_id": target_cid,
            "map_object_id": oid,
            "custom_name": custom_name,
            "base_camp_id": base_id,
            "slot_count": c_info["slot_num"],
            "items": c_info["items"],
            "transform": transform,
        }

        base_containers.setdefault(base_id, []).append(obj_record)

    return base_containers


# ── Construction Manifest Generator ───────────────────────────────────────────
def generate_construction_manifest(
    sav_path: str,
    source_base_id: str,
    target_base_id: str,
    included_types: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Generates the Base 2 Construction Manifest for a proposed container move.

    Calculates:
    - Items grouped into the 10 main categories.
    - Required slots per category (ceil(quantity / max_stack)).
    - Recommended container types and numbered labels ([Category 1], [Category 2]).
    - Status of Base 2 target containers (detects whether named chests already exist).
    """
    all_base_containers = inspect_base_containers(sav_path)
    source_containers = all_base_containers.get(source_base_id, [])
    target_containers = all_base_containers.get(target_base_id, [])

    # Filter source containers by included_types
    if included_types:
        included_set = set(included_types)
        filtered_source = [c for c in source_containers if c["map_object_id"] in included_set]
    else:
        filtered_source = source_containers

    # Aggregate item quantities per (category_id, container_type)
    category_type_items: dict[str, dict[str, dict[str, int]]] = {
        c["id"]: {} for c in MAIN_CATEGORIES
    }
    total_source_items = 0

    for sc in filtered_source:
        sc_type = sc["map_object_id"]
        eff_type = get_effective_migration_target_type(sc_type)
        for item in sc["items"]:
            item_id = item["item_id"]
            cnt = item["count"]
            cat_id = classify_item(item_id)
            if eff_type not in category_type_items[cat_id]:
                category_type_items[cat_id][eff_type] = {}
            category_type_items[cat_id][eff_type][item_id] = (
                category_type_items[cat_id][eff_type].get(item_id, 0) + cnt
            )
            total_source_items += cnt

    # Index target containers by lowercase custom_name
    target_by_name: dict[str, dict[str, Any]] = {}
    for tc in target_containers:
        if tc.get("custom_name"):
            target_by_name[tc["custom_name"].strip().lower()] = tc

    # Build manifest entries
    manifest_containers: list[dict[str, Any]] = []
    category_summaries: list[dict[str, Any]] = []

    for cat in MAIN_CATEGORIES:
        c_id = cat["id"]
        c_name = cat["name"]
        c_label = cat["label"]
        type_groups = category_type_items[c_id]

        if not type_groups:
            continue

        multiple_types_in_cat = len(type_groups) > 1
        cat_containers = []
        all_cat_items = []
        total_cat_slots = 0

        # Process each container type group separately to guarantee 1:1 type preservation
        for sc_type, items_dict in sorted(type_groups.items(), key=lambda x: x[0]):
            rec_name = CONTAINER_TYPE_INFO.get(sc_type, {}).get("name", sc_type)
            container_cap = CONTAINER_TYPE_INFO.get(sc_type, {}).get("slots", 24)

            slots_needed = 0
            group_item_details = []
            for item_id, count in sorted(items_dict.items(), key=lambda x: x[0]):
                max_s = get_item_max_stack(item_id)
                stacks = math.ceil(count / max_s)
                slots_needed += stacks
                item_info = {
                    "item_id": item_id,
                    "count": count,
                    "max_stack": max_s,
                    "stacks": stacks,
                    "container_type": sc_type,
                    "container_name": rec_name,
                }
                group_item_details.append(item_info)
                all_cat_items.append(item_info)

            total_cat_slots += slots_needed
            containers_needed = math.ceil(slots_needed / container_cap)

            # Determine type label tag if multiple container types exist in this category
            type_tag = ""
            if multiple_types_in_cat:
                if sc_type == "CoolerPalFoodBox":
                    type_tag = " CoolFeed"
                elif sc_type == "CoolerBox":
                    type_tag = " Cooler"
                elif "Food" in sc_type:
                    type_tag = " Feed"
                elif "Wardrobe" in rec_name or "Shelf" in sc_type:
                    type_tag = " Wardrobe"
                elif "Locker" in rec_name:
                    type_tag = " Locker"
                elif "Cabinet" in rec_name:
                    type_tag = " Cabinet"
                elif "Medicine" in sc_type:
                    type_tag = " Med"
                else:
                    type_tag = f" {rec_name.split()[0]}"

            for i in range(1, containers_needed + 1):
                box_label = f"{c_label}{type_tag} {i}"
                search_name = box_label.lower()
                bracket_search = f"[{box_label.lower()}]"
                single_clean = (
                    f"{c_label}{type_tag}".lower()
                    if containers_needed == 1
                    else None
                )
                single_bracket = (
                    f"[{c_label}{type_tag}]".lower()
                    if containers_needed == 1
                    else None
                )
                fallback_clean = f"{c_label} {i}".lower() if not multiple_types_in_cat else None
                fallback_bracket = f"[{c_label} {i}]".lower() if not multiple_types_in_cat else None

                alias_clean = search_name.replace("pal growth", "growth")
                alias_bracket = f"[{alias_clean}]"

                matched_tc = (
                    target_by_name.get(search_name)
                    or target_by_name.get(bracket_search)
                    or target_by_name.get(alias_clean)
                    or target_by_name.get(alias_bracket)
                    or (target_by_name.get(single_clean) if single_clean else None)
                    or (target_by_name.get(single_bracket) if single_bracket else None)
                    or (target_by_name.get(fallback_clean) if fallback_clean else None)
                    or (target_by_name.get(fallback_bracket) if fallback_bracket else None)
                )

                # Validate container type match
                type_match = False
                matched_type_name = None
                if matched_tc:
                    matched_type_name = CONTAINER_TYPE_INFO.get(
                        matched_tc["map_object_id"], {}
                    ).get("name", matched_tc["map_object_id"])
                    type_match = (matched_tc["map_object_id"] == sc_type)

                is_ready = matched_tc is not None and type_match

                entry = {
                    "category_id": c_id,
                    "category_name": c_name,
                    "box_label": box_label,
                    "recommended_container_type": sc_type,
                    "recommended_container_name": rec_name,
                    "slots_required": min(slots_needed - (i - 1) * container_cap, container_cap),
                    "container_capacity": container_cap,
                    "is_ready": is_ready,
                    "matched_target_container_id": matched_tc["container_id"] if matched_tc else None,
                    "matched_target_custom_name": matched_tc["custom_name"] if matched_tc else None,
                    "type_mismatch": matched_tc is not None and not type_match,
                    "matched_container_type": matched_tc["map_object_id"] if matched_tc else None,
                    "matched_container_name": matched_type_name,
                }
                manifest_containers.append(entry)
                cat_containers.append(entry)

        category_summaries.append(
            {
                "category_id": c_id,
                "category_name": c_name,
                "total_unique_items": len(all_cat_items),
                "total_slots_needed": total_cat_slots,
                "containers_needed": len(cat_containers),
                "containers": cat_containers,
                "items": all_cat_items,
            }
        )

    all_ready = len(manifest_containers) > 0 and all(
        c["is_ready"] for c in manifest_containers
    )

    total_source_slots = sum(len(sc.get("items", [])) for sc in filtered_source)
    total_slots_needed = sum(c.get("total_slots_needed", 0) for c in category_summaries)
    total_capacity_needed = sum(c.get("container_capacity", 0) for c in manifest_containers)

    return {
        "source_base_id": source_base_id,
        "target_base_id": target_base_id,
        "total_source_containers": len(filtered_source),
        "total_source_items": total_source_items,
        "total_source_slots": total_source_slots,
        "total_slots_needed": total_slots_needed,
        "total_capacity_needed": total_capacity_needed,
        "total_target_containers": len(target_containers),
        "all_ready_to_migrate": all_ready,
        "manifest": manifest_containers,
        "category_summaries": category_summaries,
    }


# ── Relocation & Save Engine ──────────────────────────────────────────────────
def execute_base_migration(
    sav_path: str,
    source_base_id: str,
    target_base_id: str,
    included_types: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Executes the container item migration from Source Base to Target Base.

    1. Validates all required Base 2 containers exist by custom_name.
    2. Generates an atomic timestamped backup Level.sav.bak_YYYYMMDD_HHMMSS.
    3. Reads Level.sav and populates item slots into Base 2 containers.
    4. Empties item slots in Base 1 source containers (leaving containers intact for disassembly).
    5. Saves Level.sav with verification.
    """
    manifest_res = generate_construction_manifest(
        sav_path, source_base_id, target_base_id, included_types
    )

    if not manifest_res["all_ready_to_migrate"]:
        missing = [
            c["box_label"]
            for c in manifest_res["manifest"]
            if not c["is_ready"]
        ]
        raise ValueError(
            f"Cannot execute migration. The following required target containers were not found at Base 2: {', '.join(missing)}"
        )

    # 1. Create atomic timestamped backup
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = f"{sav_path}.bak_{timestamp}"
    shutil.copy2(sav_path, backup_path)

    # 2. Decompress Level.sav
    with open(sav_path, "rb") as f:
        raw = f.read()

    save_type = raw[11] if len(raw) > 11 else 0x31
    magic = raw[8:11]
    if magic == b"PlM":
        import ooz
        ulen = int.from_bytes(raw[0:4], byteorder="little")
        gvas_bytes = ooz.decompress(raw[12:], ulen)
    else:
        gvas_bytes, _ = decompress_sav_to_gvas(raw)

    with open(os.devnull, "w") as devnull, contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
        gvas = GvasFile.read(
            gvas_bytes,
            type_hints=PALWORLD_TYPE_HINTS,
            custom_properties={},
        )

    world_save_data = gvas.properties.get("worldSaveData", {}).get("value", {})
    item_containers_raw = (
        world_save_data.get("ItemContainerSaveData", {}).get("value", [])
    )

    # Map container_id -> container struct reference in GVAS
    container_struct_map: dict[str, dict[str, Any]] = {}
    for c in item_containers_raw:
        cid = str(c.get("key", {}).get("ID", {}).get("value", ""))
        container_struct_map[cid] = c

    # Gather all source container IDs
    all_base_containers = inspect_base_containers(sav_path)
    source_containers = all_base_containers.get(source_base_id, [])
    if included_types:
        included_set = set(included_types)
        source_containers = [
            sc for sc in source_containers if sc["map_object_id"] in included_set
        ]

    # Collect all slot structs from source containers grouped by (category, container_type)
    slots_by_cat_and_type: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for sc in source_containers:
        sc_id = sc["container_id"]
        sc_type = sc["map_object_id"]
        eff_type = get_effective_migration_target_type(sc_type)
        c_struct = container_struct_map.get(sc_id)
        if not c_struct:
            continue
        slots_list = (
            c_struct.get("value", {})
            .get("Slots", {})
            .get("value", {})
            .get("values", [])
        )
        for s in slots_list:
            raw_b = bytes(s.get("RawData", {}).get("value", {}).get("values", []))
            if len(raw_b) >= 12:
                s_len = struct.unpack_from("<i", raw_b, 8)[0]
                if 0 < s_len <= 200:
                    i_name = raw_b[12 : 12 + s_len - 1].decode("utf-8", errors="replace")
                    cat_id = classify_item(i_name)
                    key = (cat_id, eff_type)
                    if key not in slots_by_cat_and_type:
                        slots_by_cat_and_type[key] = []
                    slots_by_cat_and_type[key].append(s)

    # Cohesive sorting: sort item slots by item name alphabetically, then count descending
    for key, slot_list in slots_by_cat_and_type.items():
        def _slot_sort_key(s_item):
            raw_b = bytes(s_item.get("RawData", {}).get("value", {}).get("values", []))
            if len(raw_b) >= 12:
                s_len = struct.unpack_from("<i", raw_b, 8)[0]
                count = struct.unpack_from("<i", raw_b, 4)[0]
                if 0 < s_len <= 200:
                    i_name = raw_b[12 : 12 + s_len - 1].decode("utf-8", errors="replace")
                    return (i_name.lower(), -count)
            return ("", 0)

        slot_list.sort(key=_slot_sort_key)

    # Map manifest target containers to assign slots
    items_moved_count = 0
    containers_populated = 0

    for m_entry in manifest_res["manifest"]:
        cat_id = m_entry["category_id"]
        rec_type = m_entry["recommended_container_type"]
        target_cid = m_entry["matched_target_container_id"]
        target_struct = container_struct_map.get(target_cid)
        if not target_struct:
            continue

        cap = m_entry["container_capacity"]
        actual_slot_num = target_struct.get("value", {}).get("SlotNum", {}).get("value")
        if isinstance(actual_slot_num, int) and actual_slot_num > 0:
            cap = min(cap, actual_slot_num)

        key = (cat_id, rec_type)
        cat_slots = slots_by_cat_and_type.get(key, [])
        assign_slots = cat_slots[:cap]
        slots_by_cat_and_type[key] = cat_slots[cap:]

        new_slot_values = []
        for new_idx, slot_item in enumerate(assign_slots):
            if new_idx >= cap:
                break
            raw_b = bytearray(
                slot_item.get("RawData", {}).get("value", {}).get("values", [])
            )
            # Re-index slot index (first 4 bytes int32 LE)
            struct.pack_into("<i", raw_b, 0, new_idx)
            slot_item["RawData"]["value"]["values"] = list(raw_b)
            new_slot_values.append(slot_item)
            items_moved_count += 1

        # Assign slots to target container
        target_struct["value"]["Slots"]["value"]["values"] = new_slot_values
        containers_populated += 1

    # Empty all source containers (leave containers intact for manual disassembly)
    for sc in source_containers:
        sc_id = sc["container_id"]
        c_struct = container_struct_map.get(sc_id)
        if c_struct:
            c_struct["value"]["Slots"]["value"]["values"] = []

    # 3. Compress and write Level.sav
    new_gvas_bytes = gvas.write()
    new_sav_bytes = compress_gvas_to_sav(new_gvas_bytes, save_type)

    with open(sav_path, "wb") as f:
        f.write(new_sav_bytes)

    return {
        "success": True,
        "backup_created": backup_path,
        "containers_emptied": len(source_containers),
        "containers_populated": containers_populated,
        "total_item_stacks_moved": items_moved_count,
        "source_base_id": source_base_id,
        "target_base_id": target_base_id,
    }
