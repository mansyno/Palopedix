"""Module for discovering active Palworld save worlds and managing per-world database paths."""

import os
import time
from typing import Any, Optional

from palengine.config import get_data_dir


def extract_world_name_from_meta(level_meta_path: str) -> Optional[str]:
    """Extracts actual world name string (e.g. 'Palpagos Islands 1') from LevelMeta.sav."""
    if not os.path.exists(level_meta_path):
        return None
    try:
        data = open(level_meta_path, "rb").read()
        idx = data.find(b"WorldName\x00")
        if idx != -1:
            str_idx = data.find(b"StrProperty\x00", idx)
            if str_idx != -1:
                val_start = str_idx + len(b"StrProperty\x00") + 2
                end_idx = data.find(b"\x00", val_start)
                if end_idx != -1:
                    parsed_name = data[val_start:end_idx].decode("utf-8", "ignore").strip()
                    if parsed_name and len(parsed_name) < 100:
                        return parsed_name
    except Exception:
        pass
    return None


def discover_worlds() -> list[dict[str, Any]]:
    """Scans Steam save directories for active Palworld save folders.

    Only folders containing a valid Level.sav are included.

    Returns:
        list of dicts containing world metadata:
            - world_id: str (World GUID string)
            - steam_id: str (Player's SteamID folder name)
            - sav_path: str (Absolute path to Level.sav)
            - db_path: str (Absolute path to corresponding per-world .db file)
            - display_name: str (Human readable label, e.g. "Palpagos Islands 1 [6ED60B4B]")
            - size_bytes: int (File size of Level.sav)
            - last_modified: str (ISO timestamp string)
    """
    save_root = os.path.expanduser(r"~\AppData\Local\Pal\Saved\SaveGames")
    if not os.path.exists(save_root):
        return []

    data_dir = get_data_dir()
    os.makedirs(data_dir, exist_ok=True)

    worlds: list[dict[str, Any]] = []

    try:
        steam_entries = os.listdir(save_root)
    except Exception:
        return []

    for steam_id in steam_entries:
        steam_dir = os.path.join(save_root, steam_id)
        if not os.path.isdir(steam_dir):
            continue

        try:
            world_entries = os.listdir(steam_dir)
        except Exception:
            continue

        for world_id in world_entries:
            world_dir = os.path.join(steam_dir, world_id)
            level_sav = os.path.join(world_dir, "Level.sav")

            # Active-only rule: Only register if Level.sav actually exists
            if os.path.isfile(level_sav):
                try:
                    stat = os.stat(level_sav)
                    size_bytes = stat.st_size
                    mtime = stat.st_mtime
                    mtime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
                except Exception:
                    size_bytes = 0
                    mtime_str = "Unknown"

                size_kb = round(size_bytes / 1024, 1)
                short_id = world_id[:8].upper()

                level_meta = os.path.join(world_dir, "LevelMeta.sav")
                custom_name = extract_world_name_from_meta(level_meta)
                if custom_name:
                    display_name = f"{custom_name} [{short_id}]"
                else:
                    display_name = f"World {short_id} ({size_kb} KB)"

                # Per-world DB path inside data/
                db_filename = f"world_{world_id}.db"
                db_path = os.path.join(data_dir, db_filename)

                worlds.append(
                    {
                        "world_id": world_id,
                        "steam_id": steam_id,
                        "sav_path": level_sav,
                        "db_path": db_path,
                        "display_name": display_name,
                        "size_bytes": size_bytes,
                        "last_modified": mtime_str,
                    }
                )

    # Sort worlds by last modified date (newest first)
    worlds.sort(key=lambda x: x.get("last_modified", ""), reverse=True)
    return worlds


def get_world_by_id(world_id: str) -> Optional[dict[str, Any]]:
    """Returns world metadata dict for a specific world_id, or None if not found."""
    worlds = discover_worlds()
    for w in worlds:
        if w["world_id"] == world_id:
            return w
    return None
