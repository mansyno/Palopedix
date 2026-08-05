"""SQLite database engine module for PalEngine.

Integrates static game metadata and dynamic save game instance data.
Supports both Palworld 1.0+ SQLite master database ('palworld_db') and legacy JSON datasets ('legacy').
"""

import json
import os
import sqlite3
from typing import Any, Optional

from palengine.world_manager import discover_worlds, get_world_by_id
from palengine.config import (
    get_assets_dir,
    get_palworld_db_path,
    get_static_data_source,
)
from palengine.parser.extract_bases import extract_bases
from palengine.parser.extract_pals import extract_pals
from palengine.parser.extract_items import extract_items


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
        world_id: Optional[str] = None,
    ):
        if data_dir is None:
            data_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data")
            )
        self.data_dir = data_dir
        self.source = source or get_static_data_source()
        self.palworld_db_path = db_path or get_palworld_db_path()
        self.conn = None
        self.current_world_id = None
        self.current_save_path = None

        # Auto-select newest world if world_id not specified
        worlds = discover_worlds()
        target_world = None
        if world_id:
            target_world = get_world_by_id(world_id)
        elif worlds:
            target_world = worlds[0]

        if target_world:
            db_file = target_world["db_path"]
            self.current_world_id = target_world["world_id"]
            self.current_save_path = target_world["sav_path"]
        else:
            db_file = os.path.join(self.data_dir, "userdata.db")

        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._load_static_metadata()
        
        # Auto-load save file into DB if empty
        if self.current_save_path and self.get_instance_count() == 0:
            try:
                self.load_save_data(self.current_save_path)
            except Exception as e:
                print(f"Auto-load save warning: {e}")

    def _create_tables(self) -> None:
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS item_containers (
                container_id TEXT PRIMARY KEY,
                container_type TEXT,
                slot_count INTEGER
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS item_container_slots (
                container_id TEXT,
                slot_index INTEGER,
                item_id TEXT,
                count INTEGER,
                PRIMARY KEY (container_id, slot_index),
                FOREIGN KEY (container_id) REFERENCES item_containers (container_id)
            )
        """
        )

        # ---------- Dynamic Save Game Tables ----------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pal_instances (
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
            CREATE TABLE IF NOT EXISTS pal_instance_passives (
                instance_id TEXT,
                passive_id TEXT,
                PRIMARY KEY (instance_id, passive_id),
                FOREIGN KEY (instance_id) REFERENCES pal_instances (instance_id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS base_camps (
                base_camp_id TEXT PRIMARY KEY,
                name TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS item_containers (
                container_id TEXT PRIMARY KEY,
                container_type TEXT,
                slot_count INTEGER
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS item_container_slots (
                container_id TEXT,
                slot_index INTEGER,
                item_id TEXT,
                count INTEGER,
                PRIMARY KEY (container_id, slot_index),
                FOREIGN KEY (container_id) REFERENCES item_containers (container_id)
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS base_structures_instances (
                base_camp_id TEXT,
                structure_name TEXT,
                count INTEGER,
                PRIMARY KEY (base_camp_id, structure_name),
                FOREIGN KEY (base_camp_id) REFERENCES base_camps (base_camp_id)
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
            cursor.execute("DROP TABLE IF EXISTS main.pals")
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

            cursor.execute("DROP TABLE IF EXISTS main.pal_work_suitabilities")
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

            cursor.execute("DROP TABLE IF EXISTS main.active_skills")
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
                WHERE type = 'Active' OR type = 'active' OR category = 'Active'
            """
            )

            cursor.execute("DROP TABLE IF EXISTS main.passive_skills")
            cursor.execute(
                """
                CREATE TABLE passive_skills AS
                SELECT id, name, CAST(power AS INTEGER) as rank, description
                FROM palworld_master.skills
                WHERE type = 'Passive' OR category = 'Passive' OR category LIKE 'Passive%'
                """
            )

            cursor.execute("DROP TABLE IF EXISTS main.partner_skills")
            cursor.execute(
                """
                CREATE TABLE partner_skills AS
                SELECT s.id, s.name, ps.pal_id as pal_internal_name, s.description
                FROM palworld_master.skills s
                JOIN palworld_master.pal_skills ps ON s.id = ps.skill_id
                WHERE s.type = 'Partner' OR s.category = 'Partner' OR s.category LIKE 'Partner%'
                """
            )

            cursor.execute("DROP TABLE IF EXISTS main.base_structures")
            cursor.execute(
                """
                CREATE TABLE base_structures AS
                SELECT id, name, category, tech_level as technology_level
                FROM palworld_master.buildings
                """
            )

            cursor.execute("DROP TABLE IF EXISTS main.breeding_combos")
            cursor.execute(
                """
                CREATE TABLE breeding_combos AS
                SELECT parent1_id as parent1, parent2_id as parent2, child_id as child
                FROM palworld_master.breeding_combos
                """
            )

            cursor.execute("DROP TABLE IF EXISTS main.work_suitabilities")
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
                CREATE TABLE IF NOT EXISTS passive_skills (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    rank INTEGER,
                    description TEXT
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS base_structures (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    category TEXT,
                    technology_level INTEGER
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS breeding_combos (
                    parent1 TEXT,
                    parent2 TEXT,
                    child TEXT,
                    PRIMARY KEY (parent1, parent2, child)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS partner_skills (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    pal_internal_name TEXT,
                    description TEXT
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pals (
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
                CREATE TABLE IF NOT EXISTS pal_work_suitabilities (
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
                CREATE TABLE IF NOT EXISTS active_skills (
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
                CREATE TABLE IF NOT EXISTS work_suitabilities (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT
                )
            """
            )

        self.conn.commit()

    def _load_static_metadata(self) -> None:
        cursor = self.conn.cursor()

        if self.source == "legacy" or not os.path.exists(self.palworld_db_path):
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

    def get_instance_count(self) -> int:
        """Returns total Pal instances stored in current DB."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) as c FROM pal_instances")
            return cursor.fetchone()["c"]
        except Exception:
            return 0

    def switch_world(self, world_id: str) -> dict[str, Any]:
        """Switches current database connection to target world database.

        Auto-parses and loads the world Level.sav if DB is empty.
        """
        world = get_world_by_id(world_id)
        if not world:
            raise ValueError(f"World not found: {world_id}")

        if self.conn:
            self.conn.close()

        self.current_world_id = world["world_id"]
        self.current_save_path = world["sav_path"]
        
        db_path = world["db_path"]
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._load_static_metadata()

        # Load save data if DB is new/empty
        if self.get_instance_count() == 0:
            self.load_save_data(self.current_save_path)

        return {
            "status": "success",
            "world_id": self.current_world_id,
            "display_name": world["display_name"],
            "sav_path": self.current_save_path,
            "instances_count": self.get_instance_count(),
        }

    def clear_instance_data(self) -> None:
        """Clears all dynamic save-game related tables."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM pal_instances")
        cursor.execute("DELETE FROM pal_instance_passives")
        cursor.execute("DELETE FROM base_camps")
        cursor.execute("DELETE FROM base_structures_instances")
        cursor.execute("DELETE FROM item_container_slots")
        cursor.execute("DELETE FROM item_containers")
        self.conn.commit()

    def load_save_data(self, sav_path: str) -> None:
        """Parses Level.sav and loads instances into the SQLite DB."""
        self.clear_instance_data()
        self.current_save_path = sav_path

        pals = extract_pals(sav_path)
        bases = extract_bases(sav_path)
        items_data = extract_items(sav_path)

        cursor = self.conn.cursor()
        for container in items_data:
            cursor.execute("""
                INSERT OR REPLACE INTO item_containers (container_id, container_type, slot_count)
                VALUES (?, ?, ?)
            """, (container['container_id'], container['container_type'], container['slot_count']))
            for item in container['items']:
                cursor.execute("""
                    INSERT OR REPLACE INTO item_container_slots (container_id, slot_index, item_id, count)
                    VALUES (?, ?, ?, ?)
                """, (container['container_id'], item['slot_index'], item['item_id'], item['count']))




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

    def get_owned_pal_inventory(self) -> dict[str, set[str]]:
        """Returns map of owned Pal display names to their available genders in save data.
        Example: {'Lamball': {'Male', 'Female'}, 'Leezpunk': {'Female'}}
        """
        rows = self.conn.execute(
            """
            SELECT DISTINCT coalesce(p.display_name, pi.species) as display_name, pi.gender
            FROM pal_instances pi
            LEFT JOIN pals p ON LOWER(pi.species) = LOWER(p.internal_name)
                             OR LOWER(pi.species) = LOWER(p.display_name)
            WHERE pi.gender IS NOT NULL AND pi.gender != ''
            """
        ).fetchall()
        inv: dict[str, set[str]] = {}
        for r in rows:
            name = r["display_name"]
            gender = r["gender"].capitalize()
            if name not in inv:
                inv[name] = set()
            inv[name].add(gender)
        return inv

    def get_owned_pal_species(self) -> list[str]:
        """Returns sorted list of distinct Pal display names currently owned in save data."""
        rows = self.conn.execute(
            """
            SELECT DISTINCT coalesce(p.display_name, pi.species) as display_name
            FROM pal_instances pi
            LEFT JOIN pals p ON LOWER(pi.species) = LOWER(p.internal_name)
                             OR LOWER(pi.species) = LOWER(p.display_name)
            ORDER BY display_name ASC
            """
        ).fetchall()
        return [r["display_name"] for r in rows if r["display_name"]]

    def get_breeding_result(self, parent1: str, parent2: str) -> Optional[dict[str, Any]]:
        """Calculates breeding result child for two parent species."""
        p1_in = parent1.strip().lower()
        p2_in = parent2.strip().lower()

        p1_row = self.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
            (p1_in, p1_in),
        ).fetchone() or self.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) LIKE ? OR LOWER(internal_name) LIKE ?",
            (f"%{p1_in}%", f"%{p1_in}%"),
        ).fetchone()

        p2_row = self.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
            (p2_in, p2_in),
        ).fetchone() or self.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) LIKE ? OR LOWER(internal_name) LIKE ?",
            (f"%{p2_in}%", f"%{p2_in}%"),
        ).fetchone()

        if not p1_row or not p2_row:
            return None

        p1_names = {p1_in, p1_row["display_name"].lower(), p1_row["internal_name"].lower()}
        p2_names = {p2_in, p2_row["display_name"].lower(), p2_row["internal_name"].lower()}

        if p1_row["display_name"].lower() == p2_row["display_name"].lower():
            row = self.conn.execute(
                "SELECT * FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
                (p1_row["display_name"].lower(), p1_row["display_name"].lower()),
            ).fetchone()
            if row:
                res = dict(row)
                res["icon_path"] = transform_icon_path(res.get("icon_path"))
                return res

        combo_row = None
        for n1 in p1_names:
            for n2 in p2_names:
                row = self.conn.execute(
                    """
                    SELECT child FROM breeding_combos
                    WHERE (LOWER(parent1) = ? AND LOWER(parent2) = ?)
                       OR (LOWER(parent1) = ? AND LOWER(parent2) = ?)
                """,
                    (n1, n2, n2, n1),
                ).fetchone()
                if row:
                    combo_row = row
                    break
            if combo_row:
                break

        if combo_row:
            child_name = combo_row["child"]
            child_row = self.conn.execute(
                "SELECT * FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
                (child_name.lower(), child_name.lower()),
            ).fetchone()
            if child_row:
                res = dict(child_row)
                res["icon_path"] = transform_icon_path(res.get("icon_path"))
                return res

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
            child_row = self.conn.execute(
                "SELECT display_name FROM pals WHERE LOWER(display_name) LIKE ? OR LOWER(internal_name) LIKE ?",
                (f"%{c}%", f"%{c}%"),
            ).fetchone()
            if not child_row:
                return []

        child_name = child_row["display_name"]
        target_child_lower = child_name.lower()

        pals_rows = self.conn.execute(
            "SELECT display_name, breeding_power, is_variant, index_order FROM pals"
        ).fetchall()
        all_pals = [dict(r) for r in pals_rows]

        combos_rows = self.conn.execute("SELECT parent1, parent2, child FROM breeding_combos").fetchall()
        special_combos: dict[tuple[str, str], str] = {}
        for r in combos_rows:
            p1_l = r["parent1"].lower()
            p2_l = r["parent2"].lower()
            ch_name = r["child"]
            special_combos[(p1_l, p2_l)] = ch_name
            special_combos[(p2_l, p1_l)] = ch_name

        restricted = {
            "jetragon", "frostallion", "paladius", "necromus",
            "bellanoir", "chikipi", "xenovader", "xenogard", "xenolord"
        }
        candidate_pals = [
            p for p in all_pals
            if p["is_variant"] == 0 and p["display_name"].lower() not in restricted
        ]
        candidate_pals.sort(key=lambda x: x["index_order"])

        def calc_standard_child(power1: int, power2: int) -> str:
            target_power = (power1 + power2 + 1) // 2
            best_pal = min(
                candidate_pals,
                key=lambda p: abs(p["breeding_power"] - target_power)
            )
            return best_pal["display_name"]

        results = set()

        # Same-species breeding gives same species
        results.add((child_name, child_name))

        for i in range(len(all_pals)):
            for j in range(i, len(all_pals)):
                p1_name = all_pals[i]["display_name"]
                p2_name = all_pals[j]["display_name"]
                p1_l, p2_l = p1_name.lower(), p2_name.lower()

                if p1_l == p2_l:
                    result_child = p1_name
                elif (p1_l, p2_l) in special_combos:
                    result_child = special_combos[(p1_l, p2_l)]
                else:
                    pow1 = all_pals[i]["breeding_power"]
                    pow2 = all_pals[j]["breeding_power"]
                    result_child = calc_standard_child(pow1, pow2)

                if result_child.lower() == target_child_lower:
                    p1_n, p2_n = p1_name, p2_name
                    if p1_n.lower() > p2_n.lower():
                        p1_n, p2_n = p2_n, p1_n
                    results.add((p1_n, p2_n))

        return sorted(list(results), key=lambda x: (x[0].lower(), x[1].lower()))

    def find_all_breeding_paths(
        self, owned_input: Any, target_species: str
    ) -> list[dict[str, Any]]:
        """Breadth-First Search (BFS) pathfinder that returns multiple distinct alternative breeding paths with gender hatch odds."""
        PAL_GENDER_RATIOS: dict[str, tuple[int, int]] = {
            "beegarde": (20, 80), "elizabee": (20, 80), "petallia": (20, 80),
            "lovander": (20, 80), "dazzi": (20, 80), "ribbuny": (20, 80),
            "flopie": (20, 80), "vixy": (20, 80), "cremis": (20, 80), "cinnamoth": (20, 80),
            "relaxaurus": (80, 20), "relaxaurus lux": (80, 20), "mozzarina": (80, 20),
            "eikthyrdeer": (80, 20), "eikthyrdeer terra": (80, 20), "grizzbolt": (80, 20),
            "warsect": (80, 20), "rayhound": (80, 20), "wumpo": (80, 20), "wumpo botan": (80, 20),
            "kingpaca": (90, 10), "kingpaca cryst": (90, 10), "lyleen noct": (0, 100),
        }

        def get_hatch_odds(child_species: str, required_gender: str) -> dict[str, str]:
            sp_l = child_species.strip().lower()
            m_pct, f_pct = PAL_GENDER_RATIOS.get(sp_l, (50, 50))
            if required_gender == "Male":
                pct = m_pct
            elif required_gender == "Female":
                pct = f_pct
            else:
                pct = 100

            if pct == 0:
                return {"hatch_chance_pct": "0%", "avg_eggs": "Impossible", "gender_note": f"Impossible to hatch {required_gender}"}
            avg = round(100.0 / pct, 1)
            avg_str = "~1 egg" if avg == 1.0 else f"~{avg} eggs"
            return {
                "hatch_chance_pct": f"{pct}%",
                "avg_eggs": avg_str,
                "gender_note": f"{pct}% {required_gender} hatch chance ({avg_str} avg)",
            }

        pals_rows = self.conn.execute(
            "SELECT display_name, internal_name, breeding_power, is_variant, index_order FROM pals"
        ).fetchall()
        all_pals = [dict(r) for r in pals_rows]
        cased_names = {r["display_name"].lower(): r["display_name"] for r in all_pals}
        power_map = {r["display_name"].lower(): r["breeding_power"] for r in all_pals}

        combos_rows = self.conn.execute("SELECT parent1, parent2, child FROM breeding_combos").fetchall()
        special_combos: dict[tuple[str, str], str] = {}
        for r in combos_rows:
            p1_l = r["parent1"].lower()
            p2_l = r["parent2"].lower()
            ch_name = r["child"]
            special_combos[(p1_l, p2_l)] = ch_name
            special_combos[(p2_l, p1_l)] = ch_name

        restricted = {
            "jetragon", "frostallion", "paladius", "necromus",
            "bellanoir", "chikipi", "xenovader", "xenogard", "xenolord"
        }
        candidate_pals = [
            p for p in all_pals
            if p["is_variant"] == 0 and p["display_name"].lower() not in restricted
        ]
        candidate_pals.sort(key=lambda x: x["index_order"])

        def calc_child_fast(p1_l: str, p2_l: str) -> str:
            if p1_l == p2_l:
                return cased_names.get(p1_l, p1_l)
            if (p1_l, p2_l) in special_combos:
                return special_combos[(p1_l, p2_l)]
            if p1_l in power_map and p2_l in power_map:
                pow1 = power_map[p1_l]
                pow2 = power_map[p2_l]
                target_pow = (pow1 + pow2 + 1) // 2
                best = min(candidate_pals, key=lambda p: abs(p["breeding_power"] - target_pow))
                return best["display_name"]
            return ""

        target_input = target_species.strip().lower()
        target = target_input
        if target not in cased_names:
            matched = next((k for k in cased_names if target_input in k), None)
            if matched:
                target = matched
            else:
                return []

        reachable_genders: dict[str, set[str]] = {}

        if isinstance(owned_input, dict):
            for sp_name, genders in owned_input.items():
                sp_l = sp_name.strip().lower()
                c_sp = cased_names.get(sp_l, sp_l).lower()
                if c_sp not in reachable_genders:
                    reachable_genders[c_sp] = set()
                for g in genders:
                    reachable_genders[c_sp].add(g.lower())
        elif isinstance(owned_input, list):
            for item in owned_input:
                item_str = str(item).strip()
                g_spec = None
                if "(" in item_str and ")" in item_str:
                    parts = item_str.split("(", 1)
                    sp_raw = parts[0].strip()
                    g_raw = parts[1].replace(")", "").strip().lower()
                    if "female" in g_raw or "♀" in g_raw:
                        g_spec = "female"
                    elif "male" in g_raw or "♂" in g_raw:
                        g_spec = "male"
                else:
                    sp_raw = item_str

                sp_l = sp_raw.lower()
                matched_sp = next((k for k in cased_names if sp_l in k), sp_l)
                if matched_sp not in reachable_genders:
                    reachable_genders[matched_sp] = set()
                if g_spec:
                    reachable_genders[matched_sp].add(g_spec)
                else:
                    reachable_genders[matched_sp].update({"male", "female"})

        starting_owned = set(reachable_genders.keys())

        def check_breeding_compatibility(p1_l: str, p2_l: str) -> tuple[bool, str, str]:
            g1 = reachable_genders.get(p1_l, set())
            g2 = reachable_genders.get(p2_l, set())
            if p1_l == p2_l:
                if "male" in g1 and "female" in g1:
                    return True, "Male", "Female"
                return False, "", ""
            if "male" in g1 and "female" in g2:
                return True, "Male", "Female"
            if "female" in g1 and "male" in g2:
                return True, "Female", "Male"
            return False, "", ""

        # Store multiple candidate parent recipes per child to allow alternative paths
        # recipes_for_child[child_lower] = list of (p1_lower, g1_req, p2_lower, g2_req)
        recipes_for_child: dict[str, list[tuple[str, str, str, str]]] = {}
        reachable = set(starting_owned)
        queue = list(reachable)

        for _generation in range(5):
            next_queue = []
            new_breeds = []
            for parent1 in queue:
                for parent2 in reachable:
                    ok, g1_req, g2_req = check_breeding_compatibility(parent1, parent2)
                    if ok:
                        child_name = calc_child_fast(parent1, parent2)
                        if child_name:
                            child = child_name.lower()
                            if child not in starting_owned:
                                new_breeds.append((child, parent1, g1_req, parent2, g2_req))

            for child, p1, g1_req, p2, g2_req in new_breeds:
                # Ignore self-breeding loops (e.g. Splatterina + Splatterina -> Splatterina)
                if p1 == p2 and child == p1:
                    continue

                if child not in recipes_for_child:
                    recipes_for_child[child] = []
                    next_queue.append(child)

                # Canonicalize parent pair to prevent order swapping duplicates (e.g. A+B vs B+A)
                pair_key = tuple(sorted([(p1, g1_req), (p2, g2_req)], key=lambda x: x[0]))
                existing_pairs = [tuple(sorted([(rp1, rg1), (rp2, rg2)], key=lambda x: x[0])) for rp1, rg1, rp2, rg2 in recipes_for_child[child]]
                if pair_key not in existing_pairs and len(recipes_for_child[child]) < 2:
                    recipes_for_child[child].append((p1, g1_req, p2, g2_req))

                if child not in reachable:
                    reachable.add(child)
                    reachable_genders[child] = {"male", "female"}

            queue = next_queue
            if target in recipes_for_child or not queue:
                break

        if target not in recipes_for_child:
            return []

        # Recursively construct all paths to target
        def build_paths(species: str, current_memo: set[str]) -> list[list[dict[str, Any]]]:
            if species not in recipes_for_child:
                return [[]]

            all_sub_paths = []
            for p1, g1_req, p2, g2_req in recipes_for_child[species]:
                pair_key_str = ":".join(sorted([f"{p1}:{g1_req}", f"{p2}:{g2_req}"]))
                recipe_key = f"{pair_key_str}->{species}"
                if recipe_key in current_memo:
                    continue
                new_memo = set(current_memo)
                new_memo.add(recipe_key)

                left_paths = build_paths(p1, new_memo)
                right_paths = build_paths(p2, new_memo)

                p1_cased = cased_names.get(p1, p1)
                p2_cased = cased_names.get(p2, p2)
                child_cased = cased_names.get(species, species)

                # Determine gender hatch odds for intermediate step
                hatch_info = {}
                if species != target:
                    hatch_info = get_hatch_odds(child_cased, g1_req)

                step = {
                    "parent1": p1_cased,
                    "parent1_gender": g1_req,
                    "parent2": p2_cased,
                    "parent2_gender": g2_req,
                    "child": child_cased,
                    **hatch_info
                }

                for lp in left_paths:
                    for rp in right_paths:
                        combined = lp + rp + [step]
                        all_sub_paths.append(combined)
                        if len(all_sub_paths) >= 10:
                            break
                    if len(all_sub_paths) >= 10:
                        break
                if len(all_sub_paths) >= 10:
                    break

            return all_sub_paths

        raw_paths = build_paths(target, set())

        # Canonicalize step signature helper
        def get_step_sig(s: dict[str, Any]) -> str:
            pair = sorted([f"{s['parent1']}:{s['parent1_gender']}", f"{s['parent2']}:{s['parent2_gender']}"])
            return f"{pair[0]}+{pair[1]}->{s['child']}"

        # Deduplicate paths and ensure alternative paths use distinct starting parent pairs
        unique_paths = []
        path_signatures = set()
        starting_pairs_seen = set()

        for p in raw_paths:
            # Filter out paths longer than 3 steps as requested by user
            if len(p) > 3:
                continue

            sig = "||".join(get_step_sig(s) for s in p)
            if sig in path_signatures:
                continue

            # Check starting parent pair signature (the initial breed step)
            first_step = p[0]
            start_pair_sig = f"{get_step_sig(first_step)}"
            if start_pair_sig in starting_pairs_seen and len(unique_paths) > 0:
                continue

            path_signatures.add(sig)
            starting_pairs_seen.add(start_pair_sig)
            unique_paths.append(p)

        # Format and rank paths
        formatted_paths = []
        for idx, p in enumerate(unique_paths[:5]):
            total_steps = len(p)
            has_hard_gender = any(s.get("hatch_chance_pct") in ["10%", "20%"] for s in p)
            difficulty_label = "Challenging (Low Gender Hatch Rate)" if has_hard_gender else "Easy (High Gender Hatch Rate)"
            
            title = f"Path {idx + 1} ({total_steps} Step{'s' if total_steps > 1 else ''}{' - Recommended' if idx == 0 else ' - Alternative'})"
            formatted_paths.append({
                "path_id": idx + 1,
                "title": title,
                "difficulty": difficulty_label,
                "steps": p
            })

        return formatted_paths

    def find_breeding_path(
        self, owned_input: Any, target_species: str
    ) -> list[dict[str, Any]]:
        """Breadth-First Search (BFS) pathfinder returning steps of the top recommended path."""
        all_paths = self.find_all_breeding_paths(owned_input, target_species)
        if all_paths:
            return all_paths[0]["steps"]
        return []

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

    def query_skills(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Queries skills (Active, Passive, Partner) catalog from master DB or legacy tables."""
        use_palworld_db = (
            self.source == "palworld_db" and os.path.exists(self.palworld_db_path)
        )

        results = []
        if use_palworld_db:
            query = "SELECT * FROM palworld_master.skills WHERE 1=1"
            params: list[Any] = []

            if "type" in filters and filters["type"]:
                query += " AND LOWER(type) = LOWER(?)"
                params.append(filters["type"])

            if "element" in filters and filters["element"]:
                el = filters["element"].lower()
                query += " AND LOWER(element) = LOWER(?)"
                params.append(el)

            if "category" in filters and filters["category"]:
                query += " AND LOWER(category) = LOWER(?)"
                params.append(filters["category"])

            if "search" in filters and filters["search"]:
                s = f"%{filters['search']}%"
                query += " AND (LOWER(name) LIKE LOWER(?) OR LOWER(id) LIKE LOWER(?) OR LOWER(description) LIKE LOWER(?))"
                params.extend([s, s, s])

            query += " ORDER BY type ASC, name ASC"

            rows = self.conn.execute(query, params).fetchall()
            for r in rows:
                d = dict(r)
                d["cooldown_sec"] = d.get("cooldown")
                d["icon_path"] = transform_icon_path(d.get("icon_path"))
                results.append(d)
        else:
            query_type = str(filters.get("type", "")).capitalize() if filters.get("type") else ""
            search_str = str(filters.get("search", "")).lower() if filters.get("search") else ""

            if not query_type or query_type == "Active":
                act_rows = self.conn.execute("SELECT *, 'Active' as type FROM active_skills").fetchall()
                for r in act_rows:
                    d = dict(r)
                    if search_str and search_str not in d.get("name", "").lower() and search_str not in d.get("id", "").lower() and search_str not in str(d.get("description", "")).lower():
                        continue
                    d["icon_path"] = transform_icon_path(d.get("icon_path"))
                    results.append(d)

            if not query_type or query_type == "Passive":
                pas_rows = self.conn.execute("SELECT *, 'Passive' as type FROM passive_skills").fetchall()
                for r in pas_rows:
                    d = dict(r)
                    if search_str and search_str not in d.get("name", "").lower() and search_str not in d.get("id", "").lower() and search_str not in str(d.get("description", "")).lower():
                        continue
                    results.append(d)

            if not query_type or query_type == "Partner":
                prt_rows = self.conn.execute("SELECT *, 'Partner' as type FROM partner_skills").fetchall()
                for r in prt_rows:
                    d = dict(r)
                    if search_str and search_str not in d.get("name", "").lower() and search_str not in d.get("id", "").lower() and search_str not in str(d.get("description", "")).lower():
                        continue
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
        use_palworld_db = (
            self.source == "palworld_db" and os.path.exists(self.palworld_db_path)
        )

        for r in rows:
            d = dict(r)
            d["icon_path"] = transform_icon_path(d.get("icon_path"))
            if use_palworld_db:
                p_rows = self.conn.execute(
                    """
                    SELECT COALESCE(s.name, pip.passive_id) as name,
                           pip.passive_id as id,
                           s.power as rank,
                           s.description,
                           s.stat_modifier,
                           s.category,
                           'Passive' as type,
                           s.icon_path
                    FROM pal_instance_passives pip
                    LEFT JOIN palworld_master.skills s ON LOWER(pip.passive_id) = LOWER(s.id) OR LOWER(pip.passive_id) = LOWER(s.name)
                    WHERE pip.instance_id = ?
                """,
                    (d["instance_id"],),
                ).fetchall()
            else:
                p_rows = self.conn.execute(
                    """
                    SELECT COALESCE(ps.name, pip.passive_id) as name, pip.passive_id as id, ps.rank, ps.description, 'Passive' as type
                    FROM pal_instance_passives pip
                    LEFT JOIN passive_skills ps ON LOWER(pip.passive_id) = LOWER(ps.id)
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


    def query_inventory(self, container_type: Optional[str] = None) -> list[dict[str, Any]]:
        """Queries item inventory from dynamic save data joined with static master items table."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) as c FROM item_containers")
            if cursor.fetchone()["c"] == 0:
                return []
        except Exception:
            return []

        query = """
            SELECT 
                c.container_id,
                c.container_type,
                c.slot_count,
                s.slot_index,
                s.item_id,
                s.count,
                m.name as display_name,
                m.category,
                m.subcategory,
                m.rarity,
                m.weight,
                m.price,
                m.icon_path,
                m.description
            FROM item_containers c
            JOIN item_container_slots s ON c.container_id = s.container_id
            LEFT JOIN palworld_master.items m ON LOWER(s.item_id) = LOWER(m.id)
        """
        params = []
        if container_type:
            query += " WHERE c.container_type = ?"
            params.append(container_type)
            
        query += " ORDER BY c.container_type, s.slot_index"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            d = dict(r)
            if not d["display_name"]:
                d["display_name"] = d["item_id"]
            if d["icon_path"]:
                parts = d["icon_path"].split("/")
                d["icon_path"] = "/assets/" + parts[-2] + "/" + parts[-1]
            results.append(d)
            
        return results

    def get_condense_candidates(self) -> list[dict]:
        from collections import defaultdict
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as c FROM pal_instances")
        count = cursor.fetchone()["c"]
        if count < 1:
            return []

        pal_metadata = {}
        for row in self.conn.execute("SELECT id, code, name, hp, attack, defense FROM palworld_master.pals"):
            data = {
                "name": row["name"],
                "hp": row["hp"],
                "attack": row["attack"],
                "defense": row["defense"]
            }
            pal_metadata[row["id"].lower()] = data
            if row["code"]:
                pal_metadata[row["code"].lower()] = data

        skill_metadata = {}
        for row in self.conn.execute("SELECT id, name, category FROM palworld_master.skills WHERE type='Passive'"):
            skill_metadata[row["id"].lower()] = {
                "name": row["name"],
                "category": row["category"] or "PassiveTier1"
            }

        cursor.execute("""
            SELECT i.species, i.level, i.iv_hp, i.iv_melee, i.iv_defense,
                   GROUP_CONCAT(p.passive_id, ',') as passives
            FROM pal_instances i
            LEFT JOIN pal_instance_passives p ON i.instance_id = p.instance_id
            GROUP BY i.instance_id
        """)
        instances = [dict(r) for r in cursor.fetchall()]

        species_groups = defaultdict(list)
        for inst in instances:
            raw_species = inst.get('species')
            if raw_species:
                meta = pal_metadata.get(raw_species.lower())
                display_species = meta['name'] if meta else raw_species
                inst['display_species'] = display_species
                inst['base_stats'] = meta if meta else {"hp": 100, "attack": 100, "defense": 100}
                
                raw_passives = (inst.get('passives') or '').split(',')
                display_passives = []
                passive_score = 0
                for p in raw_passives:
                    p = p.strip()
                    if p and p != 'None':
                        s_meta = skill_metadata.get(p.lower())
                        if s_meta:
                            display_passives.append(s_meta["name"])
                            cat = s_meta["category"]
                            try:
                                tier_str = cat.replace("PassiveTier", "")
                                passive_score += int(tier_str) * 50
                            except:
                                pass
                        else:
                            display_passives.append(p)
                            
                inst['display_passives'] = display_passives
                inst['passive_score'] = passive_score
                species_groups[display_species].append(inst)

        candidates = []
        for display_species, pals in species_groups.items():
            if len(pals) < 2:
                continue
                
            def get_score(p):
                iv_hp = p.get('iv_hp') or 0
                iv_atk = p.get('iv_melee') or 0
                iv_def = p.get('iv_defense') or 0
                iv_sum = iv_hp + iv_atk + iv_def
                p_score = p.get('passive_score', 0)
                return (p_score * 1000) + p.get('level', 0) * 100 + iv_sum

            pals.sort(key=get_score, reverse=True)
            best_pal = pals[0]
            
            candidates.append({
                'species': display_species,
                'count': len(pals),
                'best_pal': best_pal,
                'score': len(pals) * 100000 + get_score(best_pal)
            })
            
        candidates.sort(key=lambda x: (x['count'], x['score']), reverse=True)

        results = []
        for c in candidates[:10]:
            species = c['species']
            total_owned = c['count']
            sacrifices = total_owned - 1
            best = c['best_pal']
            
            lvl = best.get('level')
            iv_hp = best.get('iv_hp') or 0
            iv_atk = best.get('iv_melee') or 0
            iv_def = best.get('iv_defense') or 0
            passives_list = best.get('display_passives', [])
            
            attainable_stars = 0
            if total_owned >= 49: attainable_stars = 4
            elif total_owned >= 25: attainable_stars = 3
            elif total_owned >= 13: attainable_stars = 2
            elif total_owned >= 5: attainable_stars = 1

            sp_base = best['base_stats']
            
            def calc_hp(base, l, iv):
                return int(500 + 5 * l + (base * 0.5 * l) * (1 + (iv * 0.3) / 100))
                
            def calc_atk(base, l, iv, passives):
                val = 100 + (base * 0.075 * l) * (1 + (iv * 0.3) / 100)
                mult = 1.0
                passives_lower = [p.strip().lower() for p in passives]
                if 'musclehead' in passives_lower: mult += 0.30
                if 'ferocious' in passives_lower: mult += 0.20
                if 'coward' in passives_lower: mult -= 0.10
                if 'pacifist' in passives_lower: mult -= 0.20
                if 'hooligan' in passives_lower: mult += 0.15
                if 'sadist' in passives_lower: mult += 0.15
                return int(val * mult)
                
            def calc_def(base, l, iv, passives):
                val = 50 + (base * 0.075 * l) * (1 + (iv * 0.3) / 100)
                mult = 1.0
                passives_lower = [p.strip().lower() for p in passives]
                if 'burly body' in passives_lower: mult += 0.20
                if 'masochist' in passives_lower: mult += 0.15
                if 'downtrodden' in passives_lower: mult -= 0.10
                if 'hooligan' in passives_lower: mult -= 0.10
                return int(val * mult)

            est_hp = calc_hp(sp_base["hp"], lvl, iv_hp)
            est_atk = calc_atk(sp_base["attack"], lvl, iv_atk, passives_list)
            est_def = calc_def(sp_base["defense"], lvl, iv_def, passives_list)
            
            icon_path = None
            try:
                row = self.conn.execute("SELECT icon_path FROM palworld_master.pals WHERE name=?", (species,)).fetchone()
                if row and row["icon_path"]:
                    parts = row["icon_path"].split("/")
                    icon_path = "/assets/" + parts[-2] + "/" + parts[-1]
            except: pass

            results.append({
                'species': species,
                'total_owned': total_owned,
                'sacrifices_available': sacrifices,
                'attainable_stars': attainable_stars,
                'base_level': lvl,
                'hp': est_hp,
                'attack': est_atk,
                'defense': est_def,
                'iv_hp': iv_hp,
                'iv_attack': iv_atk,
                'iv_defense': iv_def,
                'passives': passives_list,
                'icon_path': icon_path
            })
            
        return results
