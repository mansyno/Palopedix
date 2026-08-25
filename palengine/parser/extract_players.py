import os
from pathlib import Path
from typing import Any, cast
from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.palsav import decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS
from palengine.parser.extract_pals import load_gvas_from_sav, clean_value

def _extract_status_points(prop: Any) -> dict[str, int]:
    pts_dict: dict[str, int] = {}
    pts_prop = prop.get("value", {}).get("values", [])
    for pt_entry in pts_prop:
        stat_name = clean_value(pt_entry.get("StatusName", {}).get("value"))
        stat_val = clean_value(pt_entry.get("StatusPoint", {}).get("value", 0))
        if stat_name and isinstance(stat_val, int):
            pts_dict[str(stat_name)] = stat_val
    return pts_dict

def extract_players(level_sav_path: str) -> list[dict[str, Any]]:
    """Extracts player character data from Level.sav and Players/*.sav files."""
    if not level_sav_path or not os.path.exists(level_sav_path):
        return []

    # 1. Parse Level.sav for Player character states
    gvas = load_gvas_from_sav(level_sav_path, [".worldSaveData.CharacterSaveParameterMap.Value.RawData"])
    world_save_data = gvas.properties.get("worldSaveData", {}).get("value", {})
    char_map = world_save_data.get("CharacterSaveParameterMap", {}).get("value", [])

    players_by_uid: dict[str, dict[str, Any]] = {}

    for char_entry in char_map:
        val = cast(dict[str, Any], char_entry.get("value", {}))
        raw_data = cast(dict[str, Any], val.get("RawData", {}).get("value") or {})
        char_obj = cast(dict[str, Any], raw_data.get("object") or {})
        save_param = cast(dict[str, Any], char_obj.get("SaveParameter", {}).get("value") or {})
        
        is_player = bool(clean_value(save_param.get("IsPlayer", {}).get("value", False)))
        if not is_player:
            continue

        key_struct = cast(dict[str, Any], char_entry.get("key") or {})
        player_uid = str(key_struct.get("PlayerUId", {}).get("value") or "")
        if not player_uid or player_uid == "00000000-0000-0000-0000-000000000000":
            continue

        level = clean_value(save_param.get("Level", {}).get("value", 1))
        exp = clean_value(save_param.get("Exp", {}).get("value", 0))
        nickname = clean_value(save_param.get("NickName", {}).get("value", ""))
        
        hp_dict = save_param.get("Hp", {}).get("value", {})
        hp_current = clean_value(hp_dict.get("Value", {}).get("value", 0))
        hp_max = clean_value(hp_dict.get("Max", {}).get("value", 0))
        
        shield_dict = save_param.get("ShieldHP", {}).get("value", {})
        shield_current = clean_value(shield_dict.get("Value", {}).get("value", 0))
        shield_max = clean_value(shield_dict.get("Max", {}).get("value", 0))
        
        status_points = _extract_status_points(save_param.get("GotStatusPointList", {}))

        players_by_uid[player_uid] = {
            "player_uid": player_uid,
            "nickname": nickname,
            "level": level,
            "exp": exp,
            "hp_current": hp_current,
            "hp_max": hp_max,
            "shield_current": shield_current,
            "shield_max": shield_max,
            "status_points": status_points,
            "tech_points": 0,
            "boss_tech_points": 0,
            "unlocked_techs": [],
            "paldeck_captures": {},
            "inventory_container_id": None,
        }

    # 2. Parse Players/*.sav for progression data
    players_dir = Path(level_sav_path).parent / "Players"
    if players_dir.exists():
        for p_file in players_dir.glob("*.sav"):
            try:
                with open(p_file, "rb") as f:
                    raw = f.read()

                uncompressed_len = int.from_bytes(raw[0:4], byteorder="little")
                magic = raw[8:11]
                if magic == b"PlM":
                    import ooz
                    gvas_data = ooz.decompress(raw[12:], uncompressed_len)
                else:
                    gvas_data, _ = decompress_sav_to_gvas(raw)

                import contextlib
                with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
                    p_gvas = GvasFile.read(gvas_data, type_hints=PALWORLD_TYPE_HINTS, custom_properties={})
                
                p_save_data = p_gvas.properties.get("SaveData", {}).get("value", {})
                
                uid = clean_value(p_save_data.get("PlayerUId", {}).get("value"))
                if not uid:
                    continue
                uid_str = str(uid)
                if uid_str not in players_by_uid:
                    continue
                
                p_dict = players_by_uid[uid_str]
                
                p_dict["tech_points"] = clean_value(p_save_data.get("TechnologyPoint", {}).get("value", 0))
                p_dict["boss_tech_points"] = clean_value(p_save_data.get("bossTechnologyPoint", {}).get("value", 0))
                
                techs = p_save_data.get("UnlockedRecipeTechnologyNames", {}).get("value", {}).get("values", [])
                p_dict["unlocked_techs"] = [clean_value(t) for t in techs if clean_value(t)]
                
                inv_info = p_save_data.get("InventoryInfo", {}).get("value", {})
                if inv_info:
                    common_container = inv_info.get("CommonContainerId", {}).get("value", {})
                    cid = clean_value(common_container.get("ID", {}).get("value"))
                    if cid:
                        p_dict["inventory_container_id"] = str(cid)
                        
                record_data = p_save_data.get("RecordData", {}).get("value", {})
                if record_data:
                    paldeck = record_data.get("PalCaptureCount", {}).get("value", [])
                    captures = {}
                    for cap_entry in paldeck:
                        species = clean_value(cap_entry.get("key"))
                        count = clean_value(cap_entry.get("value"))
                        if species and isinstance(count, int):
                            captures[str(species)] = count
                    p_dict["paldeck_captures"] = captures
                    
            except Exception as e:
                print(f"Warning: Failed to parse player file {p_file.name}: {e}")

    return list(players_by_uid.values())
