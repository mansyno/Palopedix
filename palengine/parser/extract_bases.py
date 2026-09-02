"""Module to extract Base Camp structures from Level.sav."""

import re
from typing import Any, cast

from palengine.parser.extract_pals import load_gvas_from_sav


def extract_bases(sav_path: str) -> dict[str, dict[str, Any]]:
    """Reads Level.sav and counts placed structures per Base Camp ID.

    Returns:
        dict mapping base_camp_id (str) to a dict with:
            - 'name': str (base camp name)
            - 'structures': dict[str, int] (counts of each structure type)
    """
    custom_props: list[str] = [
        ".worldSaveData.MapObjectSaveData",
        ".worldSaveData.BaseCampSaveData.Value.RawData",
    ]
    gvas_file = load_gvas_from_sav(sav_path, custom_props)

    # Cast properties to dict to avoid unknown member access warnings
    properties = cast(dict[str, Any], gvas_file.properties)
    world_save_data = cast(dict[str, Any], properties["worldSaveData"]["value"])

    # 1. Parse base camps to map base camp IDs to names
    base_camps: dict[str, dict[str, Any]] = {}
    base_camp_save_data = cast(
        list[dict[str, Any]],
        world_save_data.get("BaseCampSaveData", {}).get("value", []),
    )
    for entry in base_camp_save_data:
        val = cast(dict[str, Any], entry.get("value", {}))
        raw_data = cast(dict[str, Any], val.get("RawData", {}).get("value") or {})
        base_id = raw_data.get("id")
        base_name = cast(str, raw_data.get("name", "Unnamed Base"))
        if not base_name or "新規生成拠点" in base_name:
            base_name = "Unnamed Base"
        if base_id is not None:
            base_camps[str(base_id)] = {
                "name": base_name,
                "structures": {},
            }

    # 2. Parse map objects to count structures & natural resource nodes per base camp
    map_object_save_data = cast(
        dict[str, Any],
        world_save_data.get("MapObjectSaveData", {}).get("value", {}),
    )
    map_objects = cast(list[dict[str, Any]], map_object_save_data.get("values", []))

    for obj in map_objects:
        # ObjectId indicates structure type
        object_id = cast(str, obj.get("ObjectId", {}).get("value"))
        if not object_id:
            object_id = cast(str, obj.get("MapObjectId", {}).get("value"))
        if not object_id:
            continue

        model = cast(dict[str, Any], obj.get("Model", {}).get("value", {}))
        model_raw = cast(dict[str, Any], model.get("RawData", {}).get("value") or {})
        belong_base_id = model_raw.get("base_camp_id_belong_to")

        if belong_base_id is not None:
            belong_base_id_str = str(belong_base_id)
            # If the belong_base_id is all zeros, it doesn't belong to any base camp
            if belong_base_id_str == "00000000-0000-0000-0000-000000000000":
                continue

            # Check if this object is a natural resource node (only for Damagable terrain rocks or Trees)
            node_key = object_id
            if object_id.startswith("Damagable") or object_id.startswith("Tree"):
                cm = cast(dict[str, Any], obj.get("ConcreteModel", {}).get("value", {}))
                cm_raw = cm.get("RawData", {}).get("value")
                if isinstance(cm_raw, dict):
                    vals = cm_raw.get("values", ())
                    b = bytes(vals)
                    matches = re.findall(b"CopperOre|Coal|Sulfur|Quartz|Stone|Wood_Fine|Wood", b)
                    if matches:
                        raw_sub = matches[0].decode("ascii")
                        node_key = f"Natural_{raw_sub}"

            # Ensure the base camp entry exists
            if belong_base_id_str not in base_camps:
                base_camps[belong_base_id_str] = {
                    "name": f"Unknown Base ({belong_base_id_str[:8]})",
                    "structures": {},
                }

            base_structures = cast(
                dict[str, int], base_camps[belong_base_id_str]["structures"]
            )
            base_structures[node_key] = base_structures.get(node_key, 0) + 1

    return base_camps
