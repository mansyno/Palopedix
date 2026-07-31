"""Data manager module for handling Pal, Skill, and Structure metadata CRUD operations.

Supports dynamic additions, edits, and deletions to accommodate game patches and custom Pal definitions.
"""

import json
import os
from typing import Any, Dict, List, Optional


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
        """Returns list of all Pals."""
        return self._read_json(self.pals_path)

    def get_pal(self, internal_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single Pal by internal name (case-insensitive)."""
        pals = self.get_all_pals()
        target = internal_name.lower()
        for p in pals:
            if p.get("internal_name", "").lower() == target:
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
        if any(p.get("internal_name", "").lower() == internal_name.lower() for p in pals):
            raise ValueError(f"Pal with internal_name '{internal_name}' already exists.")

        pals.append(pal_data)
        self._write_json(self.pals_path, pals)
        return pal_data

    def update_pal(self, internal_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates fields of an existing Pal by internal_name."""
        pals = self.get_all_pals()
        target = internal_name.lower()
        found_idx = None
        for idx, p in enumerate(pals):
            if p.get("internal_name", "").lower() == target:
                found_idx = idx
                break

        if found_idx is None:
            raise KeyError(f"Pal '{internal_name}' not found.")

        pals[found_idx].update(updates)
        self._write_json(self.pals_path, pals)
        return pals[found_idx]

    def delete_pal(self, internal_name: str) -> bool:
        """Deletes a Pal by internal_name. Returns True if deleted."""
        pals = self.get_all_pals()
        target = internal_name.lower()
        initial_len = len(pals)
        pals = [p for p in pals if p.get("internal_name", "").lower() != target]

        if len(pals) < initial_len:
            self._write_json(self.pals_path, pals)
            return True
        return False
