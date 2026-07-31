"""Module to extract Pal instances from Level.sav."""

from typing import Any, cast

# ──────────────────────────────────────────────────────────────────────────────
# Compatibility patches for Palworld v0.6+ / v1.0 save format.
#
# palworld-save-tools raises "Warning: EOF not reached" for any rawdata struct
# that gained new fields in newer game versions. We silence those exceptions
# so partial data is still usable, and override character.decode_bytes to do
# a graceful partial read that handles trailing unknown bytes.
# ──────────────────────────────────────────────────────────────────────────────

import importlib, pkgutil
import palworld_save_tools.rawdata as _rawdata_pkg
from palworld_save_tools.rawdata import (
    character, group, map_object, map_model,
)


def _tolerant_wrap(fn):
    """Wrap decode_bytes to swallow 'Warning: EOF not reached' exceptions."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            if "Warning: EOF not reached" in str(exc):
                return None  # caller must handle None gracefully
            raise
    wrapper.__wrapped__ = fn
    return wrapper


# Bulk-patch all rawdata submodules
for _info in pkgutil.iter_modules(_rawdata_pkg.__path__):
    try:
        _mod = importlib.import_module(f"palworld_save_tools.rawdata.{_info.name}")
        if hasattr(_mod, "decode_bytes") and not getattr(_mod.decode_bytes, "__wrapped__", False):
            _mod.decode_bytes = _tolerant_wrap(_mod.decode_bytes)
    except Exception:
        pass


# ── character: custom graceful partial-read (avoids losing already-parsed data) ──
def _tolerant_char_decode_bytes(parent_reader, char_bytes):
    """Reimplemented character.decode_bytes that tolerates trailing bytes."""
    reader = parent_reader.internal_copy(bytes(char_bytes), debug=False)
    char_data: dict[str, Any] = {
        "object": reader.properties_until_end(),
        "unknown_bytes": reader.byte_list(4) if reader.size - reader.data.tell() >= 4 else [0, 0, 0, 0],
        "group_id": reader.guid() if reader.size - reader.data.tell() >= 16 else "00000000-0000-0000-0000-000000000000",
    }
    # Ignore any remaining trailing bytes (new fields added in v0.6+)
    return char_data

character.decode_bytes = _tolerant_char_decode_bytes


def _tolerant_char_decode(reader, type_name, size, path):
    if type_name != "ArrayProperty":
        raise Exception(f"Expected ArrayProperty, got {type_name}")
    value = reader.property(type_name, size, path, nested_caller_path=path)
    char_bytes = value["value"]["values"]
    value["value"] = _tolerant_char_decode_bytes(reader, char_bytes)
    return value

character.decode = _tolerant_char_decode


# ── group: fallback to raw bytes when group type layout is unknown ──
def _fallback_decode_group(reader, type_name, size, path):
    if type_name != "MapProperty":
        raise Exception(f"Expected MapProperty, got {type_name}")
    value = reader.property(type_name, size, path, nested_caller_path=path)
    for g in value["value"]:
        group_type = g["value"]["GroupType"]["value"]["value"]
        group_bytes = g["value"]["RawData"]["value"]["values"]
        try:
            decoded = group.decode_bytes(reader, group_bytes, group_type)
            if decoded is not None:
                g["value"]["RawData"]["value"] = decoded
        except Exception:
            pass  # keep raw values
    return value

group.decode = _fallback_decode_group


# ── MapObjectSaveData: only decode Model (needed for base_camp_id_belong_to) ──
def _tolerant_map_model_decode_bytes(parent_reader, m_bytes):
    reader = parent_reader.internal_copy(bytes(m_bytes), debug=False)
    data = {}
    try:
        data["instance_id"] = reader.guid()
        data["concrete_model_instance_id"] = reader.guid()
        data["base_camp_id_belong_to"] = reader.guid()
    except Exception:
        pass
    return data

def _selective_decode_map_object(reader, type_name, size, path):
    if type_name != "ArrayProperty":
        raise Exception(f"Expected ArrayProperty, got {type_name}")
    value = reader.property(type_name, size, path, nested_caller_path=path)
    for obj in value["value"]["values"]:
        try:
            raw_data = obj["Model"]["value"]["RawData"]["value"]
            if "values" in raw_data:
                decoded = _tolerant_map_model_decode_bytes(reader, raw_data["values"])
                obj["Model"]["value"]["RawData"]["value"] = decoded
        except Exception:
            pass  # keep raw values for sub-models we can't decode
    return value

map_object.decode = _selective_decode_map_object


# ── BaseCampSaveData: tolerant partial read ──
def _tolerant_base_camp_decode_bytes(parent_reader, b_bytes):
    reader = parent_reader.internal_copy(bytes(b_bytes), debug=False)
    data = {}
    try:
        data["id"] = reader.guid()
        data["name"] = reader.fstring()
    except Exception:
        pass
    return data

def _tolerant_base_camp_decode(reader, type_name, size, path):
    if type_name != "ArrayProperty":
        raise Exception(f"Expected ArrayProperty, got {type_name}")
    value = reader.property(type_name, size, path, nested_caller_path=path)
    value["value"] = _tolerant_base_camp_decode_bytes(reader, value["value"]["values"])
    return value


# ── WorkerDirector: tolerant partial read ──
def _tolerant_worker_director_decode_bytes(parent_reader, b_bytes):
    reader = parent_reader.internal_copy(bytes(b_bytes), debug=False)
    data = {}
    try:
        data["id"] = reader.guid()
        data["spawn_transform"] = reader.ftransform()
        data["current_order_type"] = reader.byte()
        data["current_battle_type"] = reader.byte()
        data["container_id"] = reader.guid()
    except Exception:
        pass
    return data

def _tolerant_worker_director_decode(reader, type_name, size, path):
    if type_name != "ArrayProperty":
        raise Exception(f"Expected ArrayProperty, got {type_name}")
    value = reader.property(type_name, size, path, nested_caller_path=path)
    value["value"] = _tolerant_worker_director_decode_bytes(reader, value["value"]["values"])
    return value

# ── Register all overrides into PALWORLD_CUSTOM_PROPERTIES ──
from palworld_save_tools.paltypes import PALWORLD_CUSTOM_PROPERTIES

def _register(key, decode_fn):
    if key in PALWORLD_CUSTOM_PROPERTIES:
        _, orig_enc = PALWORLD_CUSTOM_PROPERTIES[key]
        PALWORLD_CUSTOM_PROPERTIES[key] = (decode_fn, orig_enc)

_register(".worldSaveData.CharacterSaveParameterMap.Value.RawData", _tolerant_char_decode)
_register(".worldSaveData.GroupSaveDataMap", _fallback_decode_group)
_register(".worldSaveData.MapObjectSaveData", _selective_decode_map_object)
_register(".worldSaveData.BaseCampSaveData.Value.RawData", _tolerant_base_camp_decode)
_register(".worldSaveData.BaseCampSaveData.Value.WorkerDirector.RawData", _tolerant_worker_director_decode)


# ──────────────────────────────────────────────────────────────────────────────


def clean_value(val: Any) -> Any:
    """Unwrap nested GVAS property dicts into primitive Python types."""
    while isinstance(val, dict) and "value" in val:
        val = val["value"]
    return val


from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.palsav import decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS


def load_gvas_from_sav(sav_path: str, custom_properties_keys: list[str]) -> GvasFile:
    """Loads Level.sav and returns parsed GvasFile with selective custom properties decoding.

    Supports both PlZ (zlib) and PlM (Oodle) compression formats.
    """
    with open(sav_path, "rb") as f:
        data = f.read()

    uncompressed_len = int.from_bytes(data[0:4], byteorder="little")
    magic_bytes = data[8:11]

    if magic_bytes == b"PlM":
        try:
            import ooz
            gvas_data = ooz.decompress(data[12:], uncompressed_len)
        except ImportError:
            raise Exception(
                "Oodle compression (PlM) detected, but the 'ooz' library is not installed. "
                "Please run: pip install git+https://github.com/oMaN-Rod/pyooz.git"
            )
    else:
        gvas_data, _ = decompress_sav_to_gvas(data)

    custom_properties = {}
    for prop in PALWORLD_CUSTOM_PROPERTIES:
        if prop in custom_properties_keys:
            custom_properties[prop] = PALWORLD_CUSTOM_PROPERTIES[prop]

    import sys, os, contextlib
    with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
        gvas_file = GvasFile.read(
            gvas_data,
            type_hints=PALWORLD_TYPE_HINTS,
            custom_properties=custom_properties,
        )
    return gvas_file


def load_player_containers(level_sav_path: str) -> dict[str, tuple[str, str]]:
    """Reads Players/*.sav files adjacent to Level.sav to get container IDs.

    Returns a dict mapping container_id_str -> (player_uid_str, location_type)
    where location_type is 'party' or 'palbox'.
    """
    import os
    from pathlib import Path

    players_dir = Path(level_sav_path).parent / "Players"
    containers: dict[str, tuple[str, str]] = {}

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

            import sys, os, contextlib
            with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
                gvas = GvasFile.read(
                    gvas_data,
                    type_hints=PALWORLD_TYPE_HINTS,
                    custom_properties={},  # no custom decoders needed for player sav
                )

            save_data = gvas.properties.get("SaveData", {}).get("value", {})
            if not isinstance(save_data, dict):
                continue

            individual_id = save_data.get("IndividualId", {}).get("value", {})
            player_uid = individual_id.get("PlayerUId", {}).get("value")
            player_uid_str = str(player_uid) if player_uid is not None else player_sav_path.stem

            otomo_raw = save_data.get("OtomoCharacterContainerId", {}).get("value", {})
            otomo_id = clean_value(otomo_raw.get("ID", {}).get("value"))
            if otomo_id is not None:
                containers[str(otomo_id)] = (player_uid_str, "party")

            storage_raw = save_data.get("PalStorageContainerId", {}).get("value", {})
            storage_id = clean_value(storage_raw.get("ID", {}).get("value"))
            if storage_id is not None:
                containers[str(storage_id)] = (player_uid_str, "palbox")

        except Exception:
            pass  # skip unreadable player saves

    return containers





def extract_pals(sav_path: str) -> list[dict[str, Any]]:
    """Reads Level.sav and extracts all Pal instances.

    Differentiates between party, Palbox, and base camp locations.
    """
    custom_props: list[str] = [
        ".worldSaveData.CharacterSaveParameterMap.Value.RawData",
        ".worldSaveData.GroupSaveDataMap",
        ".worldSaveData.BaseCampSaveData.Value.RawData",
        ".worldSaveData.BaseCampSaveData.Value.WorkerDirector.RawData",
    ]
    gvas_file = load_gvas_from_sav(sav_path, custom_props)

    properties = cast(dict[str, Any], gvas_file.properties)
    world_save_data = cast(dict[str, Any], properties["worldSaveData"]["value"])

    # 1. Parse base camps to identify base camp worker containers
    base_camp_containers: dict[str, dict[str, str]] = {}
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

        worker_director = cast(dict[str, Any], val.get("WorkerDirector", {}).get("value", {}))
        wd_raw_data = cast(
            dict[str, Any], worker_director.get("RawData", {}).get("value") or {}
        )
        worker_container_id = wd_raw_data.get("container_id")

        if worker_container_id is not None and base_id is not None:
            base_camp_containers[str(worker_container_id)] = {
                "base_camp_id": str(base_id),
                "base_camp_name": base_name,
            }


    # 2. Load player container IDs from Players/*.sav (where Palworld actually stores them)
    player_containers: dict[str, tuple[str, str]] = load_player_containers(sav_path)

    char_save_parameter_map = cast(
        list[dict[str, Any]],
        world_save_data.get("CharacterSaveParameterMap", {}).get("value", []),
    )



    # 3. Extract Pal instances
    pals: list[dict[str, Any]] = []
    for char_entry in char_save_parameter_map:
        val = cast(dict[str, Any], char_entry.get("value", {}))
        raw_data = cast(dict[str, Any], val.get("RawData", {}).get("value") or {})
        char_obj = cast(dict[str, Any], raw_data.get("object") or {})
        save_param = cast(dict[str, Any], char_obj.get("SaveParameter", {}).get("value") or {})

        is_player = bool(clean_value(save_param.get("IsPlayer", {}).get("value", False)))
        if is_player:
            continue

        character_id = clean_value(save_param.get("CharacterID", {}).get("value"))
        if not character_id:
            continue

        key_struct = cast(dict[str, Any], char_entry.get("key") or {})
        instance_id = key_struct.get("InstanceId", {}).get("value")
        owner_player_uid = key_struct.get("PlayerUId", {}).get("value")


        level = clean_value(save_param.get("Level", {}).get("value", 1))
        gender_raw = save_param.get("Gender", {}).get("value", "EPalGenderType::None")
        gender = clean_value(gender_raw)
        if isinstance(gender, str):
            if gender.startswith("EPalGenderType::"):
                gender = gender.replace("EPalGenderType::", "")
        else:
            gender = "None"

        iv_hp = clean_value(save_param.get("Talent_HP", {}).get("value", 0))
        iv_melee = clean_value(save_param.get("Talent_Melee", {}).get("value", 0))
        iv_shot = clean_value(save_param.get("Talent_Shot", {}).get("value", 0))
        iv_defense = clean_value(save_param.get("Talent_Defense", {}).get("value", 0))

        passive_list_prop = cast(dict[str, Any], save_param.get("PassiveSkillList", {}).get("value", {}))
        passives = cast(list[str], passive_list_prop.get("values", []))

        rank = clean_value(save_param.get("Rank", {}).get("value", 0))

        slot_id = cast(dict[str, Any], save_param.get("SlotId", {}).get("value") or {})
        # PalContainerId struct: ContainerId.value.ID.value = UUID
        container_id = clean_value(
            slot_id.get("ContainerId", {}).get("value", {}).get("ID", {}).get("value")
        )


        location_type = "unknown"
        location_details = None

        container_id_str = str(container_id) if container_id is not None else None
        if container_id_str:
            if container_id_str in player_containers:
                player_uid_str, loc_type = player_containers[container_id_str]
                location_type = loc_type
                location_details = {"player_uid": player_uid_str}
            elif container_id_str in base_camp_containers:
                location_type = "base"
                location_details = base_camp_containers[container_id_str]

        pal_info = {
            "instance_id": str(instance_id) if instance_id is not None else None,
            "owner_uid": str(owner_player_uid) if owner_player_uid is not None else None,
            "species": character_id,
            "level": level,
            "gender": gender,
            "ivs": {
                "hp": iv_hp,
                "melee": iv_melee,
                "shot": iv_shot,
                "defense": iv_defense,
            },
            "passives": passives,
            "rank": rank,
            "location": location_type,
            "location_details": location_details,
        }
        pals.append(pal_info)

    return pals
