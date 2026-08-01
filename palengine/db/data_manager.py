"""Data manager module for handling Pal, Skill, and Structure metadata CRUD operations.

Supports dynamic additions, edits, and deletions to accommodate game patches and custom Pal definitions.
"""

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

from palengine.config import (
    get_palworld_db_path,
    get_static_data_source,
)
from palengine.db.sqlite_engine import transform_icon_path


class PaldexDataManager:
    """Manages reading, inserting, updating, and deleting Palworld data entries."""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data")
            )
        self.data_dir = data_dir
        self.pals_path = os.path.join(self.data_dir, "pals.json")
        self.partner_skills_path = os.path.join(
            self.data_dir, "partner_skills.json"
        )
        self.passive_skills_path = os.path.join(
            self.data_dir, "passive_skills.json"
        )
        self.active_skills_path = os.path.join(
            self.data_dir, "active_skills.json"
        )
        self.work_suitabilities_path = os.path.join(
            self.data_dir, "work_suitabilities.json"
        )
        self.base_structures_path = os.path.join(
            self.data_dir, "base_structures.json"
        )
        self.breeding_combos_path = os.path.join(
            self.data_dir, "breeding_combos.json"
        )

    def _read_json(self, path: str) -> Any:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, path: str, data: Any) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # ---------- Pal CRUD Operations ----------

    def get_all_pals(self) -> List[Dict[str, Any]]:
        """Returns list of all Pals based on active static data source."""
        source = get_static_data_source()
        db_path = get_palworld_db_path()

        if source == "palworld_db" and os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM pals ORDER BY paldex_number ASC").fetchall()
            pals = []
            for r in rows:
                d = dict(r)
                d["internal_name"] = d.get("code") or d.get("id")
                d["display_name"] = d.get("name")
                d["element_types"] = [e for e in [d.get("element1"), d.get("element2")] if e]
                d["base_stats"] = {
                    "hp": d.get("hp"),
                    "attack_melee": d.get("attack"),
                    "attack_ranged": d.get("attack"),
                    "defense": d.get("defense"),
                    "work_speed": d.get("run_speed"),
                }
                d["breeding_power"] = d.get("breeding_rank")
                d["food_requirement"] = d.get("food")
                d["icon_path"] = transform_icon_path(d.get("icon_path"))
                pals.append(d)
            conn.close()
            return pals

        return self._read_json(self.pals_path)

    def get_pal(self, internal_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single Pal by internal name or display name (case-insensitive)."""
        pals = self.get_all_pals()
        target = internal_name.lower()
        for p in pals:
            if (
                p.get("internal_name", "").lower() == target
                or p.get("display_name", "").lower() == target
                or p.get("code", "").lower() == target
                or p.get("id", "").lower() == target
            ):
                return p
        return None

    def add_pal(self, pal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Adds a new Pal to the dataset.
        
        Raises ValueError if internal_name already exists.
        """
        internal_name = pal_data.get("internal_name")
        if not internal_name:
            raise ValueError("pal_data must contain 'internal_name'")

        pals = self.get_all_pals()
        if any(
            p.get("internal_name", "").lower() == internal_name.lower()
            for p in pals
        ):
            raise ValueError(f"Pal with internal_name '{internal_name}' already exists.")

        # Always update local JSON dataset to preserve master DB read-only reference
        if os.path.exists(self.pals_path):
            json_pals = self._read_json(self.pals_path)
            json_pals.append(pal_data)
            self._write_json(self.pals_path, json_pals)

        return pal_data

    def update_pal(self, internal_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates fields of an existing Pal by internal_name."""
        pals = self.get_all_pals()
        target = internal_name.lower()
        found_pal = None
        for p in pals:
            if (
                p.get("internal_name", "").lower() == target
                or p.get("display_name", "").lower() == target
            ):
                found_pal = p
                break

        if found_pal is None:
            raise KeyError(f"Pal '{internal_name}' not found.")

        found_pal.update(updates)

        if os.path.exists(self.pals_path):
            json_pals = self._read_json(self.pals_path)
            for idx, p in enumerate(json_pals):
                if p.get("internal_name", "").lower() == target or p.get("display_name", "").lower() == target:
                    json_pals[idx].update(updates)
                    self._write_json(self.pals_path, json_pals)
                    break

        return found_pal

    def delete_pal(self, internal_name: str) -> bool:
        """Deletes a Pal by internal_name. Returns True if deleted."""
        target = internal_name.lower()
        deleted = False

        if os.path.exists(self.pals_path):
            json_pals = self._read_json(self.pals_path)
            initial_len = len(json_pals)
            json_pals = [p for p in json_pals if p.get("internal_name", "").lower() != target and p.get("display_name", "").lower() != target]
            if len(json_pals) < initial_len:
                self._write_json(self.pals_path, json_pals)
                deleted = True

        return deleted
