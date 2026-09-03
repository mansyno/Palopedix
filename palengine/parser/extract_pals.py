# basedpyright: basic
# pyright: basic
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

import functools
import importlib
import pkgutil
import palworld_save_tools.rawdata as _rawdata_pkg
from palworld_save_tools.rawdata import (
    character, group, map_object,
)


def _tolerant_wrap(fn):
    """Wrap decode_bytes to swallow 'Warning: EOF not reached' exceptions."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            if "Warning: EOF not reached" in str(exc):
                return None  # caller must handle None gracefully
            raise
    return wrapper


# Bulk-patch all rawdata submodules
for _info in pkgutil.iter_modules(_rawdata_pkg.__path__):
    try:
        _mod = importlib.import_module(f"palworld_save_tools.rawdata.{_info.name}")
        if hasattr(_mod, "decode_bytes") and not getattr(_mod.decode_bytes, "__wrapped__", False):
            setattr(_mod, "decode_bytes", _tolerant_wrap(_mod.decode_bytes))
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
        if len(m_bytes) >= 257:
            reader.data.seek(245)
            _ = reader.i64()
            custom_name = reader.fstring()
            if custom_name:
                data["custom_name"] = custom_name
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

# ── FArchiveReader: support SetProperty (Palworld v0.3+ / v0.4+ Locker & Dimensional Palbox) ──
import palworld_save_tools.archive as _archive_mod

if not getattr(_archive_mod.FArchiveReader.property, "_set_property_patched", False):
    _orig_archive_property = _archive_mod.FArchiveReader.property

    def _tolerant_archive_property(self, type_name: str, size: int, path: str, nested_caller_path: str = ""):
        if type_name == "SetProperty":
            set_type = self.fstring()
            _id = self.optional_guid()
            self.data.seek(self.data.tell() + size)
            return {
                "set_type": set_type,
                "id": _id,
                "value": [],
                "type": type_name,
            }
        return _orig_archive_property(self, type_name, size, path, nested_caller_path=nested_caller_path)

    _tolerant_archive_property._set_property_patched = True  # type: ignore[attr-defined]
    _archive_mod.FArchiveReader.property = _tolerant_archive_property


# ──────────────────────────────────────────────────────────────────────────────


def clean_value(val: Any) -> Any:
    """Unwrap nested GVAS property dicts into primitive Python types."""
    while isinstance(val, dict) and "value" in val:
        val = val["value"]
    return val


from palworld_save_tools.gvas import GvasFile, GvasHeader
from palworld_save_tools.palsav import decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS
from palworld_save_tools.archive import FArchiveReader

NEEDED_WORLD_SAVE_DATA_PROPERTIES = {
    "CharacterSaveParameterMap",
    "BaseCampSaveData",
    "MapObjectSaveData",
    "ItemContainerSaveData",
    "GroupSaveDataMap",
    "GameTimeSaveData",
    "GuildExtraSaveDataMap",
    "QuestSaveData",
}


def load_gvas_from_sav(sav_path: str, custom_properties_keys: list[str]) -> GvasFile:
    """Loads Level.sav and returns parsed GvasFile with selective custom properties decoding.

    Supports both PlZ (zlib) and PlM (Oodle) compression formats, and selectively parses
    essential worldSaveData sub-properties while cleanly skipping heavy/unsupported world dump structs.
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

    import contextlib
    import os

    with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
        gvas_file = GvasFile.read(
            gvas_data,
            type_hints=PALWORLD_TYPE_HINTS,
            custom_properties=custom_properties,
            allow_nan=True,
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

            import contextlib
            import os
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


    # 2. Load player container IDs from Players/*.sav and CharacterSaveParameterMap
    player_containers: dict[str, tuple[str, str]] = load_player_containers(sav_path)

    char_save_parameter_map = cast(
        list[dict[str, Any]],
        world_save_data.get("CharacterSaveParameterMap", {}).get("value", []),
    )

    for char_entry in char_save_parameter_map:
        val = cast(dict[str, Any], char_entry.get("value", {}))
        raw_data = cast(dict[str, Any], val.get("RawData", {}).get("value") or {})
        char_obj = cast(dict[str, Any], raw_data.get("object") or {})
        save_param = cast(dict[str, Any], char_obj.get("SaveParameter", {}).get("value") or {})
        is_player = bool(clean_value(save_param.get("IsPlayer", {}).get("value", False)))
        if is_player:
            key_struct = clean_value(char_entry.get("key")) or {}
            player_uid = clean_value(key_struct.get("PlayerUId"))
            if player_uid is not None:
                p_uid_str = str(player_uid)
                otomo_id = clean_value(save_param.get("OtomoCharacterContainerId"))
                if otomo_id:
                    player_containers[str(otomo_id)] = (p_uid_str, "party")

                storage_id = clean_value(save_param.get("PalStorageContainerId"))
                if storage_id:
                    player_containers[str(storage_id)] = (p_uid_str, "palbox")

def _parse_pal_data(
    save_param: dict[str, Any],
    instance_id: Any,
    owner_player_uid: Any,
    location_type: str,
    location_details: Any,
) -> dict[str, Any]:
    character_id = clean_value(save_param.get("CharacterID", {}).get("value"))
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

    # Newer Palworld saves renamed Talent_Melee to Talent_Shot.
    actual_melee_iv = int(iv_melee) if (str(iv_melee).isdigit() and int(iv_melee) > 0) else (int(iv_shot) if str(iv_shot).isdigit() else 0)

    passive_list_prop = cast(dict[str, Any], save_param.get("PassiveSkillList", {}).get("value", {}))
    passives = cast(list[str], passive_list_prop.get("values", []))

    raw_rank = clean_value(save_param.get("Rank", {}).get("value", 0))
    try:
        raw_rank_val = int(raw_rank) if raw_rank is not None else 0
        rank = max(0, raw_rank_val - 1) if raw_rank_val > 0 else 0
    except (ValueError, TypeError):
        rank = 0
    exp = clean_value(save_param.get("Exp", {}).get("value", 0))

    equip_waza = cast(list[str], save_param.get("EquipWaza", {}).get("value", {}).get("values", []))
    mastered_waza = cast(list[str], save_param.get("MasteredWaza", {}).get("value", {}).get("values", []))

    # Clean waza names
    equip_waza = [w for w in (clean_value(w) for w in equip_waza) if w]
    mastered_waza = [w for w in (clean_value(w) for w in mastered_waza) if w]

    def _extract_status_points(prop_name: str) -> dict[str, int]:
        pts_dict: dict[str, int] = {}
        pts_prop = save_param.get(prop_name, {}).get("value", {}).get("values", [])
        for pt_entry in pts_prop:
            stat_name = clean_value(pt_entry.get("StatusName", {}).get("value"))
            stat_val = clean_value(pt_entry.get("StatusPoint", {}).get("value", 0))
            if stat_name and isinstance(stat_val, int):
                pts_dict[str(stat_name)] = stat_val
        return pts_dict

    soul_points = _extract_status_points("GotStatusPointList")
    elixir_points = _extract_status_points("GotExStatusPointList")

    return {
        "instance_id": str(instance_id) if instance_id is not None else None,
        "owner_uid": str(owner_player_uid) if owner_player_uid is not None else None,
        "species": character_id,
        "level": level,
        "gender": gender,
        "ivs": {
            "hp": iv_hp,
            "melee": actual_melee_iv,
            "shot": iv_shot,
            "defense": iv_defense,
        },
        "passives": passives,
        "rank": rank,
        "exp": exp,
        "equip_waza": equip_waza,
        "mastered_waza": mastered_waza,
        "soul_points": soul_points,
        "elixir_points": elixir_points,
        "location": location_type,
        "location_details": location_details,
    }


def extract_pals(sav_path: str) -> list[dict[str, Any]]:
    """Reads Level.sav and Players/*_dps.sav to extract all Pal instances.

    Differentiates between party, Palbox, base camp, viewing cage, and Dimensional Pal Storage.
    """
    import os
    import contextlib
    from pathlib import Path

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

    # 2. Load player container IDs from Players/*.sav and CharacterSaveParameterMap
    player_containers: dict[str, tuple[str, str]] = load_player_containers(sav_path)

    char_save_parameter_map = cast(
        list[dict[str, Any]],
        world_save_data.get("CharacterSaveParameterMap", {}).get("value", []),
    )

    for char_entry in char_save_parameter_map:
        val = cast(dict[str, Any], char_entry.get("value", {}))
        raw_data = cast(dict[str, Any], val.get("RawData", {}).get("value") or {})
        char_obj = cast(dict[str, Any], raw_data.get("object") or {})
        save_param = cast(dict[str, Any], char_obj.get("SaveParameter", {}).get("value") or {})
        is_player = bool(clean_value(save_param.get("IsPlayer", {}).get("value", False)))
        if is_player:
            key_struct = clean_value(char_entry.get("key")) or {}
            player_uid = clean_value(key_struct.get("PlayerUId"))
            if player_uid is not None:
                p_uid_str = str(player_uid)
                otomo_id = clean_value(save_param.get("OtomoCharacterContainerId"))
                if otomo_id:
                    player_containers[str(otomo_id)] = (p_uid_str, "party")

                storage_id = clean_value(save_param.get("PalStorageContainerId"))
                if storage_id:
                    player_containers[str(storage_id)] = (p_uid_str, "palbox")

    # 3. Extract Pal instances from Level.sav CharacterSaveParameterMap
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

        slot_id = cast(dict[str, Any], save_param.get("SlotID", {}).get("value") or save_param.get("SlotId", {}).get("value") or {})
        raw_cid = slot_id.get("ContainerId")
        container_id = clean_value(raw_cid)
        if isinstance(container_id, dict) and "ID" in container_id:
            container_id = clean_value(container_id["ID"])

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
            else:
                location_type = "cage"
                location_details = {"container_id": container_id_str}

        pal_info = _parse_pal_data(
            save_param=save_param,
            instance_id=instance_id,
            owner_player_uid=owner_player_uid,
            location_type=location_type,
            location_details=location_details,
        )
        pals.append(pal_info)

    # 4. Extract Pals from Dimensional Pal Storage (Players/*_dps.sav)
    players_dir = Path(sav_path).parent / "Players"
    if players_dir.exists():
        for dps_path in players_dir.glob("*_dps.sav"):
            try:
                with open(dps_path, "rb") as f:
                    raw = f.read()

                uncompressed_len = int.from_bytes(raw[0:4], byteorder="little")
                magic = raw[8:11]

                if magic == b"PlM":
                    import ooz
                    gvas_data = ooz.decompress(raw[12:], uncompressed_len)
                else:
                    gvas_data, _ = decompress_sav_to_gvas(raw)

                with open(os.devnull, "w") as f_null, contextlib.redirect_stdout(f_null), contextlib.redirect_stderr(f_null):
                    gvas_dps = GvasFile.read(
                        gvas_data,
                        type_hints=PALWORLD_TYPE_HINTS,
                        custom_properties={},
                    )

                player_uid_stem = dps_path.stem.replace("_dps", "")
                spa = gvas_dps.properties.get("SaveParameterArray", {}).get("value", {}).get("values", [])
                for idx, slot_entry in enumerate(spa):
                    save_param_obj = slot_entry.get("SaveParameter", {})
                    if not save_param_obj or not save_param_obj.get("value"):
                        continue
                    save_param = cast(dict[str, Any], save_param_obj.get("value"))
                    char_id_val = save_param.get("CharacterID", {})
                    if not char_id_val or not char_id_val.get("value"):
                        continue
                    character_id = clean_value(char_id_val.get("value"))
                    if not character_id or str(character_id).lower() in ("none", ""):
                        continue

                    raw_inst_id = clean_value(slot_entry.get("InstanceId", {}).get("value")) or clean_value(save_param.get("InstanceId", {}).get("value"))
                    if isinstance(raw_inst_id, dict):
                        inst_id = str(raw_inst_id.get("ID") or raw_inst_id.get("InstanceId") or f"dps_{player_uid_stem}_{idx}")
                    elif raw_inst_id:
                        inst_id = str(raw_inst_id)
                    else:
                        inst_id = f"dps_{player_uid_stem}_{idx}"

                    owner_uid = clean_value(save_param.get("OwnerPlayerUId", {}).get("value")) or player_uid_stem
                    slot_number = idx + 1
                    box_num = (idx // 30) + 1
                    box_slot = (idx % 30) + 1
                    storage_label = f"Slot {slot_number} (Box {box_num}-{box_slot})"

                    pal_info = _parse_pal_data(
                        save_param=save_param,
                        instance_id=inst_id,
                        owner_player_uid=str(owner_uid),
                        location_type="dps",
                        location_details={
                            "slot_index": slot_number,
                            "box": box_num,
                            "box_slot": box_slot,
                            "base_camp_name": storage_label,
                            "player_uid": player_uid_stem,
                        },
                    )
                    pals.append(pal_info)
            except Exception:
                pass

    return pals
