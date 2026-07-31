"""SQLite database engine module for PalEngine.

Integrates static game metadata and dynamic save game instance data.
"""

import json
import os
import sqlite3
from typing import Any, Optional

from palengine.parser.extract_bases import extract_bases
from palengine.parser.extract_pals import extract_pals


class SQLiteEngine:
    """Manages the in-memory SQLite database for PalEngine."""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data")
            )
        self.data_dir = data_dir
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.current_save_path = None

        # Create schemas and load static data
        self._create_tables()
        self._load_static_metadata()

    def _create_tables(self) -> None:
        cursor = self.conn.cursor()

        # ---------- Static Metadata Tables ----------
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
                index_order INTEGER
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
            CREATE TABLE partner_skills (
                id TEXT PRIMARY KEY,
                name TEXT,
                pal_internal_name TEXT,
                description TEXT,
                FOREIGN KEY (pal_internal_name) REFERENCES pals (internal_name)
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
            CREATE TABLE active_skills (
                id TEXT PRIMARY KEY,
                name TEXT,
                element TEXT,
                power INTEGER,
                cooldown_sec INTEGER,
                description TEXT
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

        self.conn.commit()

    def _load_static_metadata(self) -> None:
        cursor = self.conn.cursor()

        # Load Pals
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

        # Load Partner Skills
        ps_path = os.path.join(self.data_dir, "partner_skills.json")
        if os.path.exists(ps_path):
            with open(ps_path, "r", encoding="utf-8") as f:
                ps_data = json.load(f)
            for ps in ps_data:
                cursor.execute(
                    """
                    INSERT INTO partner_skills (id, name, pal_internal_name, description)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        ps.get("id"),
                        ps.get("name"),
                        ps.get("pal_internal_name"),
                        ps.get("description"),
                    ),
                )

        # Load Passive Skills
        passives_path = os.path.join(self.data_dir, "passive_skills.json")
        if os.path.exists(passives_path):
            with open(passives_path, "r", encoding="utf-8") as f:
                passives_data = json.load(f)
            for ps in passives_data:
                cursor.execute(
                    """
                    INSERT INTO passive_skills (id, name, rank, description)
                    VALUES (?, ?, ?, ?)
                """,
                    (ps.get("id"), ps.get("name"), ps.get("rank"), ps.get("description")),
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

        # Load Base Structures Definitions
        bs_path = os.path.join(self.data_dir, "base_structures.json")
        if os.path.exists(bs_path):
            with open(bs_path, "r", encoding="utf-8") as f:
                bs_data = json.load(f)
            for bs in bs_data:
                cursor.execute(
                    """
                    INSERT INTO base_structures (id, name, category, technology_level)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        bs.get("id"),
                        bs.get("name"),
                        bs.get("category"),
                        bs.get("technology_level"),
                    ),
                )

        # Load Breeding Combos
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

        # Parse save data
        pals = extract_pals(sav_path)
        bases = extract_bases(sav_path)

        cursor = self.conn.cursor()

        # Insert base camps
        for base_id, base_info in bases.items():
            cursor.execute(
                """
                INSERT OR REPLACE INTO base_camps (base_camp_id, name)
                VALUES (?, ?)
            """,
                (base_id, base_info["name"]),
            )

            # Insert base structures instances
            for struct_name, count in base_info["structures"].items():
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO base_structures_instances (base_camp_id, structure_name, count)
                    VALUES (?, ?, ?)
                """,
                    (base_id, struct_name, count),
                )

        # Insert Pal instances
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

            # Passives for this instance
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
        """Calculates breeding result child for two parent species.

        Implements special overrides, same-species breeding, and standard average math.
        """
        p1 = parent1.strip().lower()
        p2 = parent2.strip().lower()

        # Same species always yields same species
        if p1 == p2:
            row = self.conn.execute(
                "SELECT * FROM pals WHERE LOWER(display_name) = ?", (p1,)
            ).fetchone()
            return dict(row) if row else None

        # Check unique combos (order-independent)
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
                "SELECT * FROM pals WHERE LOWER(display_name) = ?", (child_name.lower(),)
            ).fetchone()
            return dict(child_row) if child_row else None

        # Standard breeding power calculation
        p1_row = self.conn.execute(
            "SELECT breeding_power FROM pals WHERE LOWER(display_name) = ?", (p1,)
        ).fetchone()
        p2_row = self.conn.execute(
            "SELECT breeding_power FROM pals WHERE LOWER(display_name) = ?", (p2,)
        ).fetchone()

        if not p1_row or not p2_row:
            return None

        p1_power = p1_row["breeding_power"]
        p2_power = p2_row["breeding_power"]

        target_power = (p1_power + p2_power + 1) // 2

        # Filter out variants and special/legendary Pals that cannot be standard child results
        # Legendaries/Raid bosses/Special: Jetragon, Frostallion, Paladius, Necromus, Bellanoir, Chikipi, Xenovader, Xenogard, Xenolord
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

        # Select closest breeding power, breaking ties strictly by internal index_order
        query = f"""
            SELECT * FROM pals
            WHERE is_variant = 0
              AND LOWER(display_name) NOT IN ({','.join('?' for _ in restricted)})
            ORDER BY abs(breeding_power - ?) ASC, index_order ASC
            LIMIT 1
        """
        child_row = self.conn.execute(query, restricted + (target_power,)).fetchone()
        return dict(child_row) if child_row else None

    def find_parents_for_child(self, child: str) -> list[tuple[str, str]]:
        """Returns all breeding combinations (Parent 1, Parent 2) that yield target child."""
        c = child.strip().lower()

        # Find child row to verify existence
        child_row = self.conn.execute(
            "SELECT display_name FROM pals WHERE LOWER(display_name) = ?", (c,)
        ).fetchone()
        if not child_row:
            return []
        child_name = child_row["display_name"]

        # Fetch all Pals in DB to run combinations
        pals_rows = self.conn.execute(
            "SELECT display_name, breeding_power FROM pals"
        ).fetchall()
        pals = [dict(r) for r in pals_rows]

        results = set()

        # 1. Same-species combo yields itself
        results.add((child_name, child_name))

        # 2. Check unique combos in DB
        rows = self.conn.execute(
            "SELECT parent1, parent2 FROM breeding_combos WHERE LOWER(child) = ?", (c,)
        ).fetchall()
        for r in rows:
            p1, p2 = r["parent1"], r["parent2"]
            if p1.lower() > p2.lower():
                p1, p2 = p2, p1
            results.add((p1, p2))

        # 3. Check formulaic breeding combinations
        # We can iterate through all pairs of Pals
        for i in range(len(pals)):
            for j in range(i + 1, len(pals)):
                p1_name = pals[i]["display_name"]
                p2_name = pals[j]["display_name"]

                # Skip same-species (handled in step 1) or unique combos (handled in step 2)
                # Just calculate the result
                res = self.get_breeding_result(p1_name, p2_name)
                if res and res["display_name"].lower() == c:
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

        # Find display names map to return correct casing
        pals_rows = self.conn.execute("SELECT display_name FROM pals").fetchall()
        cased_names = {r["display_name"].lower(): r["display_name"] for r in pals_rows}

        if target not in cased_names:
            return []

        if target in owned_set:
            return []

        # Queue for BFS containing (species_name)
        # parent_recipes maps: child_species -> (parent1, parent2)
        parent_recipes: dict[str, tuple[str, str]] = {}
        reachable = set(owned_set)
        queue = list(owned_set)

        found = False
        # Limit depth to prevent infinite loops (max 5 generations)
        for generation in range(5):
            if found:
                break

            next_queue = []
            # Calculate all combinations of currently reachable species
            # We want to check combinations of A in queue and B in reachable
            new_breeds = []
            for parent1 in queue:
                for parent2 in reachable:
                    child_pal = self.get_breeding_result(
                        cased_names.get(parent1, parent1),
                        cased_names.get(parent2, parent2),
                    )
                    if child_pal:
                        child = child_pal["display_name"].lower()
                        if child not in reachable:
                            new_breeds.append((child, parent1, parent2))

            # Add newly discovered breeds to reachable
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

        # Trace back recipe tree
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

            # Ensure parents are in consistent sorted order for display
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
            query += " AND (element_1 = ? OR element_2 = ?)"
            params.extend([filters["element"], filters["element"]])

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
            # Need to join with work suitabilities table
            s_filter = filters["work_suitability"]
            query += """ AND internal_name IN (
                SELECT pal_internal_name FROM pal_work_suitabilities
                WHERE suitability_name = ?
            """
            params.append(s_filter.get("name"))
            if "min_level" in s_filter:
                query += " AND level >= ?"
                params.append(s_filter["min_level"])
            query += ")"

        # Order by Paldex number
        query += " ORDER BY paldex_number ASC"

        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def query_instances(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Queries dynamic Pal instances table with multiple filter conditions."""
        query = """
            SELECT pi.*, p.display_name, p.element_1, p.element_2
            FROM pal_instances pi
            JOIN pals p ON LOWER(pi.species) = LOWER(p.internal_name)
                        OR LOWER(pi.species) = LOWER(p.display_name)
            WHERE 1=1
        """
        params: list[Any] = []

        if "species" in filters:
            query += " AND (LOWER(p.display_name) = ? OR LOWER(p.internal_name) = ?)"
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

        # Attach passives list to each instance dictionary
        results = []
        for r in rows:
            d = dict(r)
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

        # Placed structures
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

        # Deployed workers
        summary["workers"] = self.query_instances(
            {"location": "base", "min_level": 1}  # Filter logic
        )
        # Filter workers to only those belonging to this base
        summary["workers"] = [
            w
            for w in summary["workers"]
            if w.get("location_details_base_camp_id") == base_camp_id
        ]

        return summary
