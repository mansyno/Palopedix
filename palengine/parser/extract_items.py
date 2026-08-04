"""Module to extract item inventories from Level.sav.

Extracts player-owned item containers (personal inventory, equipped gear,
and chests placed at player base camps). Skips NPC/enemy containers.
"""

import struct
from typing import Any, cast

from palengine.parser.extract_pals import load_gvas_from_sav, clean_value

from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.palsav import decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS
from pathlib import Path
import contextlib
import os


# ── Container type labels ──────────────────────────────────────────────────
INVENTORY_CONTAINER_KEYS = {
    "CommonContainerId": "Inventory",
    "DropSlotContainerId": "Drop Slot",
    "EssentialContainerId": "Key Items",
    "WeaponLoadOutContainerId": "Weapon Loadout",
    "PlayerEquipArmorContainerId": "Equipped Armor",
    "FoodEquipContainerId": "Food Equip",
}


def _read_player_container_ids(sav_path: str) -> dict[str, str]:
    """Reads Players/*.sav to extract player item container IDs.

    Returns:
        dict mapping container_id_str -> container_type_label
    """
    players_dir = Path(sav_path).parent / "Players"
    containers: dict[str, str] = {}

    if not players_dir.exists():
        return containers

    for player_sav_path in players_dir.glob("*.sav"):
        try:
            with open(player_sav_path, "rb") as f:
                raw = f.read()

            uncompressed_len = int.from_bytes(raw[0:4], byteorder="little")
            magic = raw[8:11]

            if magic == b"PlM":
                import ooz
                gvas_data = ooz.decompress(raw[12:], uncompressed_len)
            else:
                gvas_data, _ = decompress_sav_to_gvas(raw)

            with open(os.devnull, "w") as devnull, \
                 contextlib.redirect_stdout(devnull), \
                 contextlib.redirect_stderr(devnull):
                gvas = GvasFile.read(
                    gvas_data,
                    type_hints=PALWORLD_TYPE_HINTS,
                    custom_properties={},
                )

            save_data = gvas.properties.get("SaveData", {}).get("value", {})
            if not isinstance(save_data, dict):
                continue

            # Extract InventoryInfo container IDs
            inv_info = save_data.get("InventoryInfo", {}).get("value", {})
            if isinstance(inv_info, dict):
                for key, label in INVENTORY_CONTAINER_KEYS.items():
                    cid_raw = inv_info.get(key, {})
                    cid = clean_value(cid_raw)
                    if isinstance(cid, dict):
                        cid = clean_value(cid.get("ID", {}))
                    if cid and str(cid) != "00000000-0000-0000-0000-000000000000":
                        containers[str(cid)] = label

        except Exception:
            pass  # skip unreadable player saves

    return containers


def _read_base_camp_container_ids(
    world_save_data: dict[str, Any],
) -> dict[str, str]:
    """Identifies item containers that belong to player base camps.

    Reads MapObjectSaveData to find placed objects (like chests) that
    belong to a base camp, then maps their container IDs.

    Returns:
        dict mapping container_id_str -> "Base Chest"
    """
    # This is complex because chests are MapObjects with their own
    # item container references. For now, we use a heuristic:
    # containers with BelongInfo matching a non-zero GroupId are
    # guild/player-owned. But since GroupId is all-zeros in practice,
    # we instead identify base containers by their slot count.
    #
    # Player chests typically have 10-60+ slots, while NPC drop
    # containers have only 1-5 slots. However, this isn't a reliable
    # filter on its own.
    #
    # The most reliable approach: any container that is NOT a player
    # inventory container AND has a substantial slot count (>=10) is
    # likely a player-placed chest or a base storage facility.
    return {}  # Will be populated by extract_items logic


def _decode_slot_bytes(raw_bytes: tuple | bytes) -> dict[str, Any] | None:
    """Decodes a single item slot from raw byte data.

    Format:
        4 bytes: slot_index (int32 LE)
        4 bytes: stack_count (int32 LE)
        4 bytes: string_length (int32 LE, includes null terminator)
        N bytes: item_static_id (utf-8 string)

    Returns:
        dict with 'slot_index', 'item_id', 'count', or None if empty/invalid.
    """
    if not raw_bytes or len(raw_bytes) < 12:
        return None

    b = bytes(raw_bytes)
    try:
        slot_idx = struct.unpack_from("<i", b, 0)[0]
        count = struct.unpack_from("<i", b, 4)[0]
        str_len = struct.unpack_from("<i", b, 8)[0]

        if count <= 0 or str_len <= 0 or str_len > 200:
            return None

        item_id = b[12 : 12 + str_len - 1].decode("utf-8", errors="replace")

        if not item_id or item_id.startswith("\x00"):
            return None

        return {
            "slot_index": slot_idx,
            "item_id": item_id,
            "count": count,
        }
    except Exception:
        return None


def extract_items(sav_path: str) -> list[dict[str, Any]]:
    """Reads Level.sav and extracts player-owned item inventories.

    Identifies player containers from Players/*.sav InventoryInfo,
    and also captures large-slot containers that likely belong to
    player-placed chests at bases.

    Returns:
        list of dicts, each with:
            - container_id: str
            - container_type: str (e.g. "Inventory", "Key Items", "Base Chest")
            - items: list of {item_id, count, slot_index}
    """
    # 1. Get known player container IDs from Players/*.sav
    player_containers = _read_player_container_ids(sav_path)

    # 2. Load the main Level.sav (no custom properties needed for items)
    gvas_file = load_gvas_from_sav(sav_path, [])
    properties = cast(dict[str, Any], gvas_file.properties)
    world_save_data = cast(
        dict[str, Any], properties["worldSaveData"]["value"]
    )

    item_container_data = world_save_data.get(
        "ItemContainerSaveData", {}
    ).get("value", [])

    results: list[dict[str, Any]] = []

    for container in item_container_data:
        cid = str(clean_value(container.get("key", {}).get("ID", {})))
        val = container.get("value", {})
        slot_num = clean_value(val.get("SlotNum", {}).get("value", 0))

        # Determine if this is a player-owned container
        container_type = player_containers.get(cid)

        if not container_type:
            # Heuristic: containers with 10+ slots that have items
            # are likely player-placed chests
            if slot_num and slot_num >= 10:
                container_type = "Base Chest"
            else:
                continue  # Skip NPC/small containers

        # 3. Decode item slots
        slots_raw = val.get("Slots", {}).get("value", {})
        slots_values = (
            slots_raw.get("values", [])
            if isinstance(slots_raw, dict)
            else []
        )

        items: list[dict[str, Any]] = []
        for slot in slots_values:
            raw_data = slot.get("RawData", {}).get("value", {})
            raw_bytes = raw_data.get("values", ())

            decoded = _decode_slot_bytes(raw_bytes)
            if decoded:
                items.append(decoded)

        if items:
            results.append(
                {
                    "container_id": cid,
                    "container_type": container_type,
                    "slot_count": slot_num,
                    "items": items,
                }
            )

    return results
