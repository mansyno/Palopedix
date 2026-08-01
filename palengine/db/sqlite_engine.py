"""SQLite database engine module for PalEngine.

Integrates static game metadata and dynamic save game instance data.
Supports both Palworld 1.0+ SQLite master database ('palworld_db') and legacy JSON datasets ('legacy').
"""

import json
import os
import sqlite3
from typing import Any, Optional

from palengine.config import (
    get_assets_dir,
    get_palworld_db_path,
    get_static_data_source,
)
from palengine.parser.extract_bases import extract_bases
from palengine.parser.extract_pals import extract_pals


def transform_icon_path(path: Optional[str]) -> Optional[str]:
    """Converts absolute local asset file paths into web-accessible URL paths (/assets/...)."""
    if not path:
        return None
    normalized = path.replace("\\", "/")
    assets_dir = get_assets_dir().replace("\\", "/").rstrip("/")
    if normalized.lower().startswith(assets_dir.lower()):
        rel_path = normalized[len(assets_dir):]
        if not rel_path.startswith("/"):
            rel_path = "/" + rel_path
        return f"/assets{rel_path}"
    elif "palworld_assets" in normalized.lower():
        idx = normalized.lower().find("palworld_assets")
        rel_path = normalized[idx + len("palworld_assets"):]
        if not rel_path.startswith("/"):
            rel_path = "/" + rel_path
        return f"/assets{rel_path}"
    return path


class SQLiteEngine:
    """Manages the SQLite database engine for PalEngine."""

    def __init__(
        self,
        data_dir: Optional[str] = None,
        source: Optional[str] = None,
        db_path: Optional[str] = None,
    ):
        if data_dir is None:
            data_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data")
            )
        self.data_dir = data_dir
        self.source = source or get_static_data_source()
        self.palworld_db_path = db_path or get_palworld_db_path()

        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.current_save_path = None

        # Create schemas and load static data
        self._create_tables()
        self._load_static_metadata()

    def _create_tables(self) -> None:
        cursor = self.conn.cursor()

        # ---------- Dynamic Save Game Tables ----------
        cursor.execute(
            """
            CREATE TABLE pal_instances (
                instance_id TEXT PRIMARY KEY,
                owner_uid TEXT,
                species TEXT,
                level INTEGER,
                gender TEXT,
                iv_hp INTEGER,
                iv_melee INTEGER,
                iv_shot INTEGER,
                iv_defense INTEGER,
                rank INTEGER,
                location TEXT,
                location_details_player_uid TEXT,
                location_details_base_camp_id TEXT,
                location_details_base_camp_name TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE pal_instance_passives (
                instance_id TEXT,
                passive_id TEXT,
                PRIMARY KEY (instance_id, passive_id),
                FOREIGN KEY (instance_id) REFERENCES pal_instances (instance_id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE base_camps (
                base_camp_id TEXT PRIMARY KEY,
                name TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE base_structures_instances (
                base_camp_id TEXT,
                structure_name TEXT,
                count INTEGER,
                PRIMARY KEY (base_camp_id, structure_name),
                FOREIGN KEY (base_camp_id) REFERENCES base_camps (base_camp_id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE passive_skills (
                id TEXT PRIMARY KEY,
                name TEXT,
                rank INTEGER,
                description TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE base_structures (
                id TEXT PRIMARY KEY,
                name TEXT,
                category TEXT,
                technology_level INTEGER
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE breeding_combos (
                parent1 TEXT,
                parent2 TEXT,
                child TEXT,
                PRIMARY KEY (parent1, parent2, child)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE partner_skills (
                id TEXT PRIMARY KEY,
                name TEXT,
                pal_internal_name TEXT,
                description TEXT
            )
        """
        )

        # ---------- Static Metadata Source Setup ----------
        use_palworld_db = (
            self.source == "palworld_db" and os.path.exists(self.palworld_db_path)
        )

        if use_palworld_db:
            # Attach external master SQLite database
            db_path_clean = self.palworld_db_path.replace("\\", "/")
            cursor.execute(f"ATTACH DATABASE '{db_path_clean}' AS palworld_master")

            # Create in-memory tables populated from attached master database
            cursor.execute(
                r"""
                CREATE TABLE pals AS
                SELECT
                    coalesce(code, id) AS internal_name,
                    name AS display_name,
                    paldex_number,
                    CASE
                        WHEN LOWER(element1) IN ('normal', 'neutral') THEN 'Neutral'
                        WHEN LOWER(element1) IN ('leaf', 'grass') THEN 'Grass'
                        WHEN LOWER(element1) IN ('electricity', 'electric') THEN 'Electric'
                        ELSE element1
                    END AS element_1,
                    CASE
                        WHEN LOWER(element2) IN ('normal', 'neutral') THEN 'Neutral'
                        WHEN LOWER(element2) IN ('leaf', 'grass') THEN 'Grass'
                        WHEN LOWER(element2) IN ('electricity', 'electric') THEN 'Electric'
                        ELSE element2
                    END AS element_2,
                    hp,
                    attack AS attack_melee,
                    attack AS attack_ranged,
                    defense,
                    run_speed AS work_speed,
                    breeding_rank AS breeding_power,
                    food AS food_requirement,
                    NULL AS ride_type,
                    nocturnal,
                    'M' AS size,
                    CASE WHEN id LIKE '%\_%' ESCAPE '\' THEN 1 ELSE 0 END AS is_variant,
                    NULL AS base_pal,
                    paldex_number AS index_order,
                    icon_path,
                    description,
                    id,
                    code,
                    run_speed,
                    stamina,
                    rarity
                FROM palworld_master.pals
            """
            )

            cursor.execute(
                """
                CREATE TABLE pal_work_suitabilities AS
                SELECT
                    pal_id AS pal_internal_name,
                    CASE LOWER(work_type)
                        WHEN 'handcraft' THEN 'handiwork'
                        WHEN 'electricity' THEN 'generating_electricity'
                        WHEN 'medicine' THEN 'medicine_production'
                        WHEN 'transport' THEN 'transporting'
                        WHEN 'monsterfarm' THEN 'farming'
                        ELSE LOWER(work_type)
                    END AS suitability_name,
                    level
                FROM palworld_master.work_suitability
            """
            )

            cursor.execute(
                """
                CREATE TABLE active_skills AS
                SELECT
                    id,
                    name,
                    element,
                    power,
                    cooldown AS cooldown_sec,
                    description,
                    icon_path
                FROM palworld_master.skills
            """
            )

            cursor.execute(
                """
                CREATE TABLE work_suitabilities AS
                SELECT DISTINCT
                    work_type AS id,
                    work_type AS name,
                    '' AS description
                FROM palworld_master.work_suitability
            """
            )
        else:
            # Legacy In-Memory SQLite Tables
            cursor.execute(
                """
                CREATE TABLE pals (
                    internal_name TEXT PRIMARY KEY,
                    display_name TEXT,
                    paldex_number INTEGER,
                    element_1 TEXT,
                    element_2 TEXT,
                    hp INTEGER,
                    attack_melee INTEGER,
                    attack_ranged INTEGER,
                    defense INTEGER,
                    work_speed INTEGER,
                    breeding_power INTEGER,
                    food_requirement INTEGER,
                    ride_type TEXT,
                    nocturnal INTEGER,
                    size TEXT,
                    is_variant INTEGER,
                    base_pal TEXT,
                    index_order INTEGER,
                    icon_path TEXT,
                    description TEXT
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE pal_work_suitabilities (
                    pal_internal_name TEXT,
                    suitability_name TEXT,
                    level INTEGER,
                    PRIMARY KEY (pal_internal_name, suitability_name),
                    FOREIGN KEY (pal_internal_name) REFERENCES pals (internal_name)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE active_skills (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    element TEXT,
                    power INTEGER,
                    cooldown_sec INTEGER,
                    description TEXT,
                    icon_path TEXT
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE work_suitabilities (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT
                )
            """
            )

        self.conn.commit()

    def _load_static_metadata(self) -> None:
        cursor = self.conn.cursor()

        # Always load passive skills, base structures, and breeding combos if present
        passives_path = os.path.join(self.data_dir, "passive_skills.json")
        if os.path.exists(passives_path):
            with open(passives_path, "r", encoding="utf-8") as f:
                passives_data = json.load(f)
            for ps in passives_data:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO passive_skills (id, name, rank, description)
                    VALUES (?, ?, ?, ?)
                """,
                    (ps.get("id"), ps.get("name"), ps.get("rank"), ps.get("description")),
                )

        bs_path = os.path.join(self.data_dir, "base_structures.json")
        if os.path.exists(bs_path):
            with open(bs_path, "r", encoding="utf-8") as f:
                bs_data = json.load(f)
            for bs in bs_data:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO base_structures (id, name, category, technology_level)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        bs.get("id"),
                        bs.get("name"),
                        bs.get("category"),
                        bs.get("technology_level"),
                    ),
                )

        bc_path = os.path.join(self.data_dir, "breeding_combos.json")
        if os.path.exists(bc_path):
            with open(bc_path, "r", encoding="utf-8") as f:
                bc_data = json.load(f)
            for bc in bc_data.get("unique_combos", []):
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO breeding_combos (parent1, parent2, child)
                    VALUES (?, ?, ?)
                """,
                    (bc.get("parent1"), bc.get("parent2"), bc.get("child")),
                )

        ps_path = os.path.join(self.data_dir, "partner_skills.json")
        if os.path.exists(ps_path):
            with open(ps_path, "r", encoding="utf-8") as f:
                ps_data = json.load(f)
            for ps in ps_data:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO partner_skills (id, name, pal_internal_name, description)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        ps.get("id"),
                        ps.get("name"),
                        ps.get("pal_internal_name"),
                        ps.get("description"),
                    ),
                )

        # Load legacy static tables if NOT using palworld_db
        if self.source == "legacy" or not os.path.exists(self.palworld_db_path):
            pals_path = os.path.join(self.data_dir, "pals.json")
            if os.path.exists(pals_path):
                with open(pals_path, "r", encoding="utf-8") as f:
                    pals_data = json.load(f)
                for idx, p in enumerate(pals_data):
                    elements = p.get("element_types", [])
                    element_1 = elements[0] if len(elements) > 0 else None
                    element_2 = elements[1] if len(elements) > 1 else None

                    stats = p.get("base_stats", {})
                    cursor.execute(
                        """
                        INSERT INTO pals (
                            internal_name, display_name, paldex_number, element_1, element_2,
                            hp, attack_melee, attack_ranged, defense, work_speed,
                            breeding_power, food_requirement, ride_type, nocturnal,
                            size, is_variant, base_pal, index_order
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            p.get("internal_name"),
                            p.get("display_name"),
                            p.get("paldex_number"),
                            element_1,
                            element_2,
                            stats.get("hp"),
                            stats.get("attack_melee"),
                            stats.get("attack_ranged"),
                            stats.get("defense"),
                            stats.get("work_speed"),
                            p.get("breeding_power"),
                            p.get("food_requirement"),
                            p.get("ride_type"),
                            1 if p.get("nocturnal") else 0,
                            p.get("size"),
                            1 if p.get("is_variant") else 0,
                            p.get("base_pal"),
                            idx,
                        ),
                    )

                    # Work Suitabilities for this Pal
                    suitabilities = p.get("work_suitabilities", {})
                    for s_name, s_level in suitabilities.items():
                        cursor.execute(
                            """
                            INSERT INTO pal_work_suitabilities (pal_internal_name, suitability_name, level)
                            VALUES (?, ?, ?)
                        """,
                            (p.get("internal_name"), s_name, s_level),
                        )

            # Load Active Skills
            actives_path = os.path.join(self.data_dir, "active_skills.json")
            if os.path.exists(actives_path):
                with open(actives_path, "r", encoding="utf-8") as f:
                    actives_data = json.load(f)
                for act in actives_data:
                    cursor.execute(
                        """
                        INSERT INTO active_skills (id, name, element, power, cooldown_sec, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            act.get("id"),
                            act.get("name"),
                            act.get("element"),
                            act.get("power"),
                            act.get("cooldown_sec"),
                            act.get("description"),
                        ),
                    )

            # Load Work Suitabilities Definitions
            ws_path = os.path.join(self.data_dir, "work_suitabilities.json")
            if os.path.exists(ws_path):
                with open(ws_path, "r", encoding="utf-8") as f:
                    ws_data = json.load(f)
                for ws in ws_data:
                    cursor.execute(
                        """
                        INSERT INTO work_suitabilities (id, name, description)
                        VALUES (?, ?, ?)
                    """,
                        (ws.get("id"), ws.get("name"), ws.get("description")),
                    )

        self.conn.commit()

    # ---------- Save Data Reload capability ----------

    def clear_instance_data(self) -> None:
        """Clears all dynamic save-game related tables."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM pal_instances")
        cursor.execute("DELETE FROM pal_instance_passives")
        cursor.execute("DELETE FROM base_camps")
        cursor.execute("DELETE FROM base_structures_instances")
        self.conn.commit()

    def load_save_data(self, sav_path: str) -> None:
        """Parses Level.sav and loads instances into the SQLite DB."""
        self.clear_instance_data()
        self.current_save_path = sav_path

        pals = extract_pals(sav_path)
        bases = extract_bases(sav_path)

        cursor = self.conn.cursor()

        for base_id, base_info in bases.items():
            cursor.execute(
                """
                INSERT OR REPLACE INTO base_camps (base_camp_id, name)
                VALUES (?, ?)
            """,
                (base_id, base_info["name"]),
            )

            for struct_name, count in base_info["structures"].items():
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO base_structures_instances (base_camp_id, structure_name, count)
                    VALUES (?, ?, ?)
                """,
                    (base_id, struct_name, count),
                )

        for pal in pals:
            loc_details = pal.get("location_details") or {}
            loc_player_uid = loc_details.get("player_uid")
            loc_base_camp_id = loc_details.get("base_camp_id")
            loc_base_camp_name = loc_details.get("base_camp_name")

            cursor.execute(
                """
                INSERT OR REPLACE INTO pal_instances (
                    instance_id, owner_uid, species, level, gender,
                    iv_hp, iv_melee, iv_shot, iv_defense, rank, location,
                    location_details_player_uid, location_details_base_camp_id,
                    location_details_base_camp_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    pal.get("instance_id"),
                    pal.get("owner_uid"),
                    pal.get("species"),
                    pal.get("level"),
                    pal.get("gender"),
                    pal.get("ivs", {}).get("hp"),
                    pal.get("ivs", {}).get("melee"),
                    pal.get("ivs", {}).get("shot"),
                    pal.get("ivs", {}).get("defense"),
                    pal.get("rank"),
                    pal.get("location"),
                    loc_player_uid,
                    loc_base_camp_id,
                    loc_base_camp_name,
                ),
            )

            for p_id in pal.get("passives", []):
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO pal_instance_passives (instance_id, passive_id)
                    VALUES (?, ?)
                """,
                    (pal.get("instance_id"), p_id),
                )

        self.conn.commit()

    # ---------- Advanced Breeding Logic APIs ----------

    def get_breeding_result(self, parent1: str, parent2: str) -> Optional[dict[str, Any]]:
        """Calculates breeding result child for two parent species."""
        p1 = parent1.strip().lower()
        p2 = parent2.strip().lower()

        if p1 == p2:
            row = self.conn.execute(
                "SELECT * FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
                (p1, p1),
            ).fetchone()
            if row:
                res = dict(row)
                res["icon_path"] = transform_icon_path(res.get("icon_path"))
                return res
            return None

        row = self.conn.execute(
            """
            SELECT child FROM breeding_combos
            WHERE (LOWER(parent1) = ? AND LOWER(parent2) = ?)
               OR (LOWER(parent1) = ? AND LOWER(parent2) = ?)
        """,
            (p1, p2, p2, p1),
        ).fetchone()

        if row:
            child_name = row["child"]
            child_row = self.conn.execute(
                "SELECT * FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
                (child_name.lower(), child_name.lower()),
            ).fetchone()
            if child_row:
                res = dict(child_row)
                res["icon_path"] = transform_icon_path(res.get("icon_path"))
                return res
            return None

        p1_row = self.conn.execute(
            "SELECT breeding_power FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
            (p1, p1),
        ).fetchone()
        p2_row = self.conn.execute(
            "SELECT breeding_power FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
            (p2, p2),
        ).fetchone()

        if not p1_row or not p2_row:
            return None

        p1_power = p1_row["breeding_power"]
        p2_power = p2_row["breeding_power"]

        target_power = (p1_power + p2_power + 1) // 2

        restricted = (
            "jetragon",
            "frostallion",
            "paladius",
            "necromus",
            "bellanoir",
            "chikipi",
            "xenovader",
            "xenogard",
            "xenolord",
        )

        query = f"""
            SELECT * FROM pals
            WHERE is_variant = 0
              AND LOWER(display_name) NOT IN ({','.join('?' for _ in restricted)})
            ORDER BY abs(breeding_power - ?) ASC, index_order ASC
            LIMIT 1
        """
        child_row = self.conn.execute(query, restricted + (target_power,)).fetchone()
        if child_row:
            res = dict(child_row)
            res["icon_path"] = transform_icon_path(res.get("icon_path"))
            return res
        return None

    def find_parents_for_child(self, child: str) -> list[tuple[str, str]]:
        """Returns all breeding combinations (Parent 1, Parent 2) that yield target child."""
        c = child.strip().lower()

        child_row = self.conn.execute(
            "SELECT display_name FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
            (c, c),
        ).fetchone()
        if not child_row:
            return []
        child_name = child_row["display_name"]

        pals_rows = self.conn.execute(
            "SELECT display_name, breeding_power FROM pals"
        ).fetchall()
        pals = [dict(r) for r in pals_rows]

        results = set()
        results.add((child_name, child_name))

        rows = self.conn.execute(
            "SELECT parent1, parent2 FROM breeding_combos WHERE LOWER(child) = ?", (c,)
        ).fetchall()
        for r in rows:
            p1, p2 = r["parent1"], r["parent2"]
            if p1.lower() > p2.lower():
                p1, p2 = p2, p1
            results.add((p1, p2))

        for i in range(len(pals)):
            for j in range(i + 1, len(pals)):
                p1_name = pals[i]["display_name"]
                p2_name = pals[j]["display_name"]

                res = self.get_breeding_result(p1_name, p2_name)
                if res and res.get("display_name", "").lower() == c:
                    p1_n, p2_n = p1_name, p2_name
                    if p1_n.lower() > p2_n.lower():
                        p1_n, p2_n = p2_n, p1_n
                    results.add((p1_n, p2_n))

        return sorted(list(results), key=lambda x: (x[0].lower(), x[1].lower()))

    def find_breeding_path(
        self, owned_species: list[str], target_species: str
    ) -> list[dict[str, str]]:
        """Breadth-First Search (BFS) pathfinder to breed the target Pal from owned species."""
        owned_set = {s.strip().lower() for s in owned_species}
        target = target_species.strip().lower()

        pals_rows = self.conn.execute("SELECT display_name FROM pals").fetchall()
        cased_names = {r["display_name"].lower(): r["display_name"] for r in pals_rows}

        if target not in cased_names:
            return []

        if target in owned_set:
            return []

        parent_recipes: dict[str, tuple[str, str]] = {}
        reachable = set(owned_set)
        queue = list(owned_set)

        found = False
        for _generation in range(5):
            if found:
                break

            next_queue = []
            new_breeds = []
            for parent1 in queue:
                for parent2 in reachable:
                    child_pal = self.get_breeding_result(
                        cased_names.get(parent1, parent1),
                        cased_names.get(parent2, parent2),
                    )
                    if child_pal:
                        child = child_pal.get("display_name", "").lower()
                        if child and child not in reachable:
                            new_breeds.append((child, parent1, parent2))

            for child, p1, p2 in new_breeds:
                if child not in reachable:
                    reachable.add(child)
                    next_queue.append(child)
                    parent_recipes[child] = (p1, p2)
                    if child == target:
                        found = True
                        break

            queue = next_queue
            if not queue:
                break

        if target not in parent_recipes:
            return []

        memo: set[str] = set()

        def collect_steps(species: str) -> list[dict[str, str]]:
            if species not in parent_recipes:
                return []
            p1, p2 = parent_recipes[species]
            steps = []
            steps.extend(collect_steps(p1))
            steps.extend(collect_steps(p2))

            p1_cased = cased_names.get(p1, p1)
            p2_cased = cased_names.get(p2, p2)
            child_cased = cased_names.get(species, species)

            if p1_cased.lower() > p2_cased.lower():
                p1_cased, p2_cased = p2_cased, p1_cased

            recipe_key = f"{p1_cased.lower()}+{p2_cased.lower()}->{child_cased.lower()}"
            if recipe_key not in memo:
                memo.add(recipe_key)
                steps.append(
                    {"parent1": p1_cased, "parent2": p2_cased, "child": child_cased}
                )
            return steps

        return collect_steps(target)

    # ---------- Querying APIs ----------

    def query_pals(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Queries static Pals metadata table with multiple filter conditions."""
        query = "SELECT * FROM pals WHERE 1=1"
        params: list[Any] = []

        if "element" in filters:
            el = filters["element"].lower()
            el_matches = [el]
            if el in ("normal", "neutral"):
                el_matches = ["normal", "neutral"]
            elif el in ("leaf", "grass"):
                el_matches = ["leaf", "grass"]
            elif el in ("electricity", "electric"):
                el_matches = ["electricity", "electric"]

            query += f" AND (LOWER(element_1) IN ({','.join('?' for _ in el_matches)}) OR LOWER(element_2) IN ({','.join('?' for _ in el_matches)}))"
            params.extend(el_matches + el_matches)

        if "nocturnal" in filters:
            query += " AND nocturnal = ?"
            params.append(1 if filters["nocturnal"] else 0)

        if "size" in filters:
            query += " AND size = ?"
            params.append(filters["size"])

        if "is_variant" in filters:
            query += " AND is_variant = ?"
            params.append(1 if filters["is_variant"] else 0)

        if "work_suitability" in filters:
            s_filter = filters["work_suitability"]
            raw_s_name = str(s_filter.get("name", "")).lower()
            ws_map = {
                "handiwork": ["handiwork", "handcraft"],
                "handcraft": ["handiwork", "handcraft"],
                "generating_electricity": ["generating_electricity", "electricity"],
                "electricity": ["generating_electricity", "electricity"],
                "medicine_production": ["medicine_production", "medicine"],
                "medicine": ["medicine_production", "medicine"],
                "transporting": ["transporting", "transport"],
                "transport": ["transporting", "transport"],
                "farming": ["farming", "monsterfarm"],
                "monsterfarm": ["farming", "monsterfarm"],
            }
            s_names = ws_map.get(raw_s_name, [raw_s_name])
            query += f""" AND internal_name IN (
                SELECT pal_internal_name FROM pal_work_suitabilities
                WHERE LOWER(suitability_name) IN ({','.join('?' for _ in s_names)})
            """
            params.extend(s_names)
            if "min_level" in s_filter:
                query += " AND level >= ?"
                params.append(s_filter["min_level"])
            query += ")"

        query += " ORDER BY paldex_number ASC"

        rows = self.conn.execute(query, params).fetchall()
        results = []

        use_palworld_db = (
            self.source == "palworld_db" and os.path.exists(self.palworld_db_path)
        )

        for r in rows:
            pal_dict = dict(r)
            pal_dict["icon_path"] = transform_icon_path(pal_dict.get("icon_path"))

            if use_palworld_db:
                pal_id = pal_dict.get("internal_name") or pal_dict.get("id")
                # Attach skills from palworld_master
                try:
                    s_rows = self.conn.execute(
                        """
                        SELECT s.id, s.name, s.element, s.type, s.category, s.power, s.cooldown,
                               s.min_range, s.max_range, s.stat_modifier, s.unlock_item,
                               s.description, s.icon_path, ps.level_learned, ps.is_guaranteed
                        FROM palworld_master.pal_skills ps
                        JOIN palworld_master.skills s ON ps.skill_id = s.id
                        WHERE LOWER(ps.pal_id) = LOWER(?) OR ps.pal_id = ?
                        ORDER BY ps.level_learned ASC, s.name ASC
                    """,
                        (pal_id, pal_id),
                    ).fetchall()
                    pal_dict["skills"] = [
                        {
                            "id": dict(sr).get("id"),
                            "name": dict(sr).get("name"),
                            "element": dict(sr).get("element"),
                            "type": dict(sr).get("type"),
                            "category": dict(sr).get("category"),
                            "power": dict(sr).get("power"),
                            "cooldown": dict(sr).get("cooldown"),
                            "min_range": dict(sr).get("min_range"),
                            "max_range": dict(sr).get("max_range"),
                            "stat_modifier": dict(sr).get("stat_modifier"),
                            "unlock_item": dict(sr).get("unlock_item"),
                            "description": dict(sr).get("description"),
                            "icon_path": transform_icon_path(dict(sr).get("icon_path")),
                            "level_learned": dict(sr).get("level_learned"),
                            "is_guaranteed": dict(sr).get("is_guaranteed", 0),
                        }
                        for sr in s_rows
                    ]
                    partner_skills = [sk for sk in pal_dict["skills"] if (sk.get("type") == "Partner" or sk.get("category") == "Partner")]
                    pal_dict["partner_skill"] = partner_skills[0] if partner_skills else None
                except Exception as e:
                    pal_dict["skills"] = []
                    pal_dict["partner_skill"] = None

                # Attach work suitabilities from palworld_master
                try:
                    ws_rows = self.conn.execute(
                        "SELECT work_type, level FROM palworld_master.work_suitability WHERE pal_id = ? ORDER BY level DESC",
                        (pal_id,),
                    ).fetchall()
                    
                    work_type_map = {
                        "EmitFlame": ("Kindling", "Kindling.png"),
                        "Kindling": ("Kindling", "Kindling.png"),
                        "Watering": ("Watering", "Watering.png"),
                        "Seeding": ("Planting", "Planting.png"),
                        "Planting": ("Planting", "Planting.png"),
                        "GenerateElectricity": ("Generating Electricity", "GeneratingElectricity.png"),
                        "Electricity": ("Generating Electricity", "GeneratingElectricity.png"),
                        "GeneratingElectricity": ("Generating Electricity", "GeneratingElectricity.png"),
                        "Handcraft": ("Handiwork", "Handcraft.png"),
                        "Collection": ("Gathering", "Gathering.png"),
                        "Gathering": ("Gathering", "Gathering.png"),
                        "Deforest": ("Lumbering", "Lumbering.png"),
                        "Wood": ("Lumbering", "Lumbering.png"),
                        "Lumbering": ("Lumbering", "Lumbering.png"),
                        "Mining": ("Mining", "Mining.png"),
                        "Mine": ("Mining", "Mining.png"),
                        "ProductMedicine": ("Medicine Production", "Medicine.png"),
                        "Medicine": ("Medicine Production", "Medicine.png"),
                        "Cool": ("Cooling", "Cooling.png"),
                        "Cooling": ("Cooling", "Cooling.png"),
                        "Transport": ("Transporting", "Transport.png"),
                        "Transporting": ("Transporting", "Transport.png"),
                        "MonsterFarm": ("Farming", "MonsterFarm.png"),
                        "Farming": ("Farming", "MonsterFarm.png"),
                        "OilExtraction": ("Oil Extraction", "OilExtraction.png"),
                    }
                    
                    ws_suitabilities = {}
                    ws_details = []
                    for wsr in ws_rows:
                        raw_type = wsr["work_type"]
                        name, icon_name = work_type_map.get(raw_type, (raw_type, f"{raw_type}.png"))
                        level = wsr["level"]
                        ws_suitabilities[name] = level
                        ws_details.append({
                            "id": raw_type,
                            "name": name,
                            "level": level,
                            "icon_path": f"/assets/work/{icon_name}"
                        })

                    pal_dict["work_suitabilities"] = ws_suitabilities
                    pal_dict["work_suitability_details"] = ws_details
                except Exception:
                    pal_dict["work_suitabilities"] = {}
                    pal_dict["work_suitability_details"] = []

                # Attach drops from palworld_master
                try:
                    drop_rows = self.conn.execute(
                        """
                        SELECT d.item_id, d.item_name, d.min_quantity, d.max_quantity, d.drop_rate, i.icon_path
                        FROM palworld_master.drops d
                        LEFT JOIN palworld_master.items i ON d.item_id = i.id
                        WHERE d.pal_id = ?
                        """,
                        (pal_id,),
                    ).fetchall()
                    pal_dict["drops"] = [
                        {
                            "item_id": dr["item_id"],
                            "item_name": dr["item_name"],
                            "min_quantity": dr["min_quantity"],
                            "max_quantity": dr["max_quantity"],
                            "drop_rate": dr["drop_rate"],
                            "icon_path": transform_icon_path(dr["icon_path"]) if dr.get("icon_path") else transform_icon_path(f"C:/palworld_assets/items/{dr['item_id']}.png")
                        }
                        for dr in drop_rows
                    ]
                except Exception:
                    pal_dict["drops"] = []

            results.append(pal_dict)

        return results

    def query_items(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Queries items catalog with optional category, subcategory, and rarity filters."""
        if not (self.source == "palworld_db" and os.path.exists(self.palworld_db_path)):
            return []

        query = "SELECT * FROM palworld_master.items WHERE 1=1"
        params: list[Any] = []

        if "category" in filters and filters["category"]:
            query += " AND LOWER(category) = LOWER(?)"
            params.append(filters["category"])

        if "rarity" in filters and filters["rarity"] is not None:
            query += " AND rarity = ?"
            params.append(filters["rarity"])

        if "search" in filters and filters["search"]:
            query += " AND (LOWER(name) LIKE LOWER(?) OR LOWER(id) LIKE LOWER(?))"
            s = f"%{filters['search']}%"
            params.extend([s, s])

        query += " ORDER BY rarity DESC, name ASC"

        rows = self.conn.execute(query, params).fetchall()
        results = []
        assets_dir = get_assets_dir()
        for r in rows:
            d = dict(r)
            raw_path = d.get("icon_path")
            if raw_path and assets_dir:
                filename = os.path.basename(raw_path.replace("\\", "/"))
                local_file = os.path.join(assets_dir, "items", filename)
                if not os.path.exists(local_file):
                    continue
            d["icon_path"] = transform_icon_path(raw_path)
            results.append(d)
        return results

    def get_item_recipe(self, item_id: str) -> Optional[dict[str, Any]]:
        """Retrieves crafting recipe and material costs for a specific item_id."""
        if not (self.source == "palworld_db" and os.path.exists(self.palworld_db_path)):
            return None

        r_row = self.conn.execute(
            """
            SELECT r.*, i.name as item_name, b.name as facility_name, b.icon_path as facility_icon
            FROM palworld_master.recipes r
            JOIN palworld_master.items i ON r.item_id = i.id
            LEFT JOIN palworld_master.buildings b ON r.facility_id = b.id
            WHERE r.item_id = ? OR r.id = ?
            """,
            (item_id, item_id),
        ).fetchone()

        if not r_row:
            return None

        recipe_dict = dict(r_row)
        recipe_dict["facility_icon"] = transform_icon_path(recipe_dict.get("facility_icon"))

        ing_rows = self.conn.execute(
            """
            SELECT ri.*, i.icon_path
            FROM palworld_master.recipe_ingredients ri
            LEFT JOIN palworld_master.items i ON ri.material_item_id = i.id
            WHERE ri.recipe_id = ?
            """,
            (recipe_dict["id"],),
        ).fetchall()

        ingredients = []
        for ing in ing_rows:
            d = dict(ing)
            d["icon_path"] = transform_icon_path(d.get("icon_path"))
            ingredients.append(d)

        recipe_dict["ingredients"] = ingredients
        return recipe_dict

    def query_buildings(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Queries base camp buildings & infrastructure."""
        if not (self.source == "palworld_db" and os.path.exists(self.palworld_db_path)):
            return []

        query = "SELECT * FROM palworld_master.buildings WHERE 1=1"
        params: list[Any] = []

        if "category" in filters and filters["category"]:
            query += " AND LOWER(category) = LOWER(?)"
            params.append(filters["category"])

        if "search" in filters and filters["search"]:
            query += " AND (LOWER(name) LIKE LOWER(?) OR LOWER(id) LIKE LOWER(?))"
            s = f"%{filters['search']}%"
            params.extend([s, s])

        query += " ORDER BY tech_level ASC, name ASC"

        rows = self.conn.execute(query, params).fetchall()
        results = []
        assets_dir = get_assets_dir()
        for r in rows:
            d = dict(r)
            raw_path = d.get("icon_path")
            if raw_path and assets_dir:
                filename = os.path.basename(raw_path.replace("\\", "/"))
                local_file = os.path.join(assets_dir, "buildings", filename)
                if not os.path.exists(local_file):
                    continue
            d["icon_path"] = transform_icon_path(raw_path)
            results.append(d)
        return results

    def query_tech_tree(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Queries technology tree unlock nodes."""
        if not (self.source == "palworld_db" and os.path.exists(self.palworld_db_path)):
            return []

        query = "SELECT * FROM palworld_master.technology_tree WHERE 1=1"
        params: list[Any] = []

        if "level" in filters and filters["level"] is not None:
            query += " AND level = ?"
            params.append(filters["level"])

        if "is_ancient" in filters and filters["is_ancient"] is not None:
            query += " AND is_ancient = ?"
            params.append(1 if filters["is_ancient"] else 0)

        query += " ORDER BY level ASC, name ASC"

        rows = self.conn.execute(query, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            results.append(d)
        return results

    def query_work_types(self) -> list[dict[str, Any]]:
        """Queries all 12 official Palworld work suitability types with HUD icon paths."""
        if not (self.source == "palworld_db" and os.path.exists(self.palworld_db_path)):
            return []

        rows = self.conn.execute("SELECT * FROM palworld_master.work_types ORDER BY name ASC").fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["icon_path"] = transform_icon_path(d.get("icon_path"))
            results.append(d)
        return results

    def query_instances(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Queries dynamic Pal instances table with multiple filter conditions."""
        query = """
            SELECT pi.*,
                   coalesce(p.display_name, pi.species) as display_name,
                   p.element_1, p.element_2, p.hp, p.attack_melee, p.defense, p.icon_path
            FROM pal_instances pi
            LEFT JOIN pals p ON LOWER(pi.species) = LOWER(p.internal_name)
                             OR LOWER(pi.species) = LOWER(p.display_name)
            WHERE 1=1
        """
        params: list[Any] = []

        if "species" in filters:
            query += " AND (LOWER(coalesce(p.display_name, pi.species)) = ? OR LOWER(pi.species) = ?)"
            params.extend([filters["species"].lower(), filters["species"].lower()])

        if "location" in filters:
            query += " AND pi.location = ?"
            params.append(filters["location"])

        if "gender" in filters:
            query += " AND pi.gender = ?"
            params.append(filters["gender"])

        if "min_level" in filters:
            query += " AND pi.level >= ?"
            params.append(filters["min_level"])

        if "min_rank" in filters:
            query += " AND pi.rank >= ?"
            params.append(filters["min_rank"])

        if "min_iv_hp" in filters:
            query += " AND pi.iv_hp >= ?"
            params.append(filters["min_iv_hp"])

        if "min_iv_melee" in filters:
            query += " AND pi.iv_melee >= ?"
            params.append(filters["min_iv_melee"])

        if "min_iv_shot" in filters:
            query += " AND pi.iv_shot >= ?"
            params.append(filters["min_iv_shot"])

        if "min_iv_defense" in filters:
            query += " AND pi.iv_defense >= ?"
            params.append(filters["min_iv_defense"])

        if "passive_id" in filters:
            query += """ AND pi.instance_id IN (
                SELECT instance_id FROM pal_instance_passives
                WHERE LOWER(passive_id) = ?
            )"""
            params.append(filters["passive_id"].lower())

        query += " ORDER BY pi.level DESC, pi.species ASC"

        rows = self.conn.execute(query, params).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            d["icon_path"] = transform_icon_path(d.get("icon_path"))
            p_rows = self.conn.execute(
                """
                SELECT ps.name, ps.id, ps.rank, ps.description
                FROM pal_instance_passives pip
                JOIN passive_skills ps ON LOWER(pip.passive_id) = LOWER(ps.id)
                WHERE pip.instance_id = ?
            """,
                (d["instance_id"],),
            ).fetchall()
            d["passives"] = [dict(pr) for pr in p_rows]
            results.append(d)

        return results

    def get_base_camp_summary(self, base_camp_id: str) -> Optional[dict[str, Any]]:
        """Returns details, workers, and structure counts for a given Base Camp."""
        base_row = self.conn.execute(
            "SELECT * FROM base_camps WHERE base_camp_id = ?", (base_camp_id,)
        ).fetchone()

        if not base_row:
            return None

        summary = dict(base_row)

        struct_rows = self.conn.execute(
            """
            SELECT bsi.structure_name, bsi.count, bs.name as display_name, bs.category
            FROM base_structures_instances bsi
            LEFT JOIN base_structures bs ON LOWER(bsi.structure_name) = LOWER(bs.id)
                                         OR LOWER(bsi.structure_name) = LOWER(bs.name)
            WHERE bsi.base_camp_id = ?
            ORDER BY bsi.structure_name ASC
        """,
            (base_camp_id,),
        ).fetchall()
        summary["structures"] = [dict(r) for r in struct_rows]

        summary["workers"] = self.query_instances(
            {"location": "base", "min_level": 1}
        )
        summary["workers"] = [
            w
            for w in summary["workers"]
            if w.get("location_details_base_camp_id") == base_camp_id
        ]

        return summary
