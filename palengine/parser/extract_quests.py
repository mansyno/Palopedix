import os
from pathlib import Path
from typing import Any
from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.palsav import decompress_sav_to_gvas
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS
from palengine.parser.extract_pals import clean_value


def extract_active_quests(level_sav_path: str) -> list[dict[str, Any]]:
    """Extracts active, uncompleted quests from player save files adjacent to Level.sav.
    
    Reads Players/*.sav to inspect OrderedQuestArray_FullRelease, CompletedQuestArray_FullRelease,
    and legacy QuestSaveData records. Filters out completed quests and non-sub missions.
    """
    if not level_sav_path or not os.path.exists(level_sav_path):
        return []

    active_quest_ids: set[str] = set()
    completed_quest_ids: set[str] = set()

    # 1. Parse Players/*.sav for player quest states
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
                with open(os.devnull, "w") as devnull, contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                    p_gvas = GvasFile.read(gvas_data, type_hints=PALWORLD_TYPE_HINTS, custom_properties={})

                p_save_data = p_gvas.properties.get("SaveData", {}).get("value", {})
                
                # Palworld 1.0 Full Release quest arrays
                for order_key in ("OrderedQuestArray_FullRelease", "OrderedQuestArray"):
                    ordered_arr = p_save_data.get(order_key, {}).get("value", {}).get("values", [])
                    for q in ordered_arr:
                        if isinstance(q, dict):
                            q_name_prop = q.get("QuestName", {})
                            q_name = q_name_prop.get("value") if isinstance(q_name_prop, dict) else q.get("QuestName")
                            if q_name:
                                active_quest_ids.add(str(q_name))
                        elif isinstance(q, str):
                            active_quest_ids.add(q)

                for comp_key in ("CompletedQuestArray_FullRelease", "CompletedQuestArray"):
                    comp_arr = p_save_data.get(comp_key, {}).get("value", {}).get("values", [])
                    for c in comp_arr:
                        if isinstance(c, str):
                            completed_quest_ids.add(c)
                        elif isinstance(c, dict):
                            c_name = c.get("value") or c.get("QuestName", {}).get("value") or c.get("QuestName")
                            if c_name:
                                completed_quest_ids.add(str(c_name))

                # Legacy QuestSaveData / NormalQuest / MissionSaveData
                quest_save = p_save_data.get("QuestSaveData", {}).get("value", {}) or {}
                if isinstance(quest_save, dict):
                    active_list = quest_save.get("ActiveQuestList", {}).get("value", {}).get("values", [])
                    for q in active_list:
                        qid = clean_value(q)
                        if qid:
                            active_quest_ids.add(str(qid))
                    
                    completed_list = quest_save.get("CompletedQuestList", {}).get("value", {}).get("values", [])
                    for q in completed_list:
                        qid = clean_value(q)
                        if qid:
                            completed_quest_ids.add(str(qid))

                normal_quest = p_save_data.get("NormalQuestData", {}).get("value", {}) or {}
                if isinstance(normal_quest, dict):
                    for k, v in normal_quest.items():
                        q_name = clean_value(k)
                        q_val = clean_value(v)
                        if q_name:
                            if q_val and str(q_val).lower() not in ("completed", "done"):
                                active_quest_ids.add(str(q_name))
                            elif q_val and str(q_val).lower() in ("completed", "done"):
                                completed_quest_ids.add(str(q_name))

            except Exception:
                # Silently skip corrupted or unreadable individual player file
                pass

    # Exclude completed quests and non-sub missions (filter out Main_* and Hidden_*)
    final_active_ids = {qid for qid in (active_quest_ids - completed_quest_ids) if qid.startswith("Sub_")}

    return [{"quest_id": qid} for qid in sorted(final_active_ids)]
