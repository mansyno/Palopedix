"""Pal Investment & Combat/Transport Recommender for PalEngine.

Deterministic recommendation engine based on Palworld v1.0+ community meta.
Evaluates owned Pal instances against combat/mount tier lists, passive skill values,
IVs, condensation ranks, and player inventory upgrade materials (manuals, souls,
stat fruits, skill fruits, kinship peaches).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from palengine.db.sqlite_engine import SQLiteEngine


# ==============================================================================
# v1.0+ Meta Constants
# ==============================================================================

COMBAT_SPECIES_TIER: dict[str, float] = {
    # S-Tier
    "Jetragon": 1.5, "Xenolord": 1.5, "Hartalis": 1.5,
    "Bellanoir Libero": 1.5, "Frostallion": 1.5, "Jormuntide Ignis": 1.5,
    "Frostallion Noct": 1.5, "Shadowbeak": 1.5,
    # A-Tier
    "Shaolong": 1.3, "Knocklem Ignis": 1.3, "Neptilius": 1.3,
    "Anubis": 1.3, "Blazamut": 1.3, "Suzaku": 1.3, "Suzaku Aqua": 1.3,
    "Necromus": 1.3, "Paladius": 1.3, "Orserk": 1.3,
    "Astegon": 1.3, "Ragnahawk": 1.3, "Selyne": 1.3,
    "Blazamut Ryu": 1.3, "Bellanoir": 1.3, "Prixter": 1.3,
    "Eidrolon": 1.3, "Eidrolon Ignis": 1.3, "Panthalus": 1.3,
    "Xenogard": 1.3,
    # B-Tier
    "Relaxaurus": 1.1, "Relaxaurus Lux": 1.1, "Quivern": 1.1, "Quivern Botan": 1.1,
    "Lyleen": 1.1, "Lyleen Noct": 1.1, "Cryolinx": 1.1,
    "Menasting": 1.1, "Jormuntide": 1.1, "Warsect": 1.1,
    "Helzephyr": 1.1, "Helzephyr Lux": 1.1, "Beakon": 1.1, "Beakon Cryst": 1.1,
    "Faleris": 1.1, "Faleris Aqua": 1.1, "Vanwyrm": 1.1, "Vanwyrm Cryst": 1.1,
    "Grizzbolt": 1.1, "Elizabee": 1.1, "Univolt": 1.1, "Univolt Cryst": 1.1,
    "Pyrin": 1.1, "Pyrin Noct": 1.1, "Mammorest": 1.1,
    "Reptyro": 1.1, "Reptyro Cryst": 1.1, "Wumpo": 1.1, "Wumpo Botan": 1.1,
}

COMBAT_PASSIVE_VALUES: dict[str, int] = {
    # S-Tier Combat
    "Legend": 30,
    "Demon God": 30,
    "Serenity": 28,
    "Immortality": 25,
    # A-Tier Combat
    "Musclehead": 25,
    "Ferocious": 20,
    "Lucky": 18,
    "Diamond Body": 15,
    # B-Tier Combat
    "Brave": 12,
    "Aggressive": 10,
    "Vanguard": 10,
    "Stronghold Strategist": 10,
    "Burly Body": 10,
    "Hard Skin": 8,
    "Blood of the Dragon": 8,
    "Cheery": 5,
    "Suntan Lover": 5,
    "Otherworldly Cells": 5,
    # Negative Passives
    "Coward": -25,
    "Pacifist": -30,
    "Slacker": -15,
    "Downtrodden": -10,
    "Clumsy": -10,
}

TRANSPORT_PASSIVE_VALUES: dict[str, int] = {
    "Legend": 30,
    "Swift": 35,
    "Runner": 25,
    "Nimble": 15,
    "Lucky": 10,
    "Coward": -15,
    "Slacker": -10,
    "Downtrodden": -10,
    "Clumsy": -5,
}

FLYING_SPECIES_BONUS: dict[str, float] = {
    "Jetragon": 1.5,
    "Panthalus": 1.4,
    "Shaolong": 1.3,
    "Eidrolon": 1.25, "Eidrolon Ignis": 1.25,
    "Xenolord": 1.2,
    "Faleris": 1.15, "Faleris Aqua": 1.15,
    "Shadowbeak": 1.15,
    "Frostallion": 1.15, "Frostallion Noct": 1.15,
    "Suzaku": 1.1, "Suzaku Aqua": 1.1,
}

GROUND_SPECIES_BONUS: dict[str, float] = {
    "Paladius": 1.5,
    "Hartalis": 1.45,
    "Necromus": 1.4,
    "Xenogard": 1.3,
    "Yakumo": 1.2,
    "Pyrin": 1.15, "Pyrin Noct": 1.15,
    "Univolt": 1.1, "Univolt Cryst": 1.1,
    "Direhowl": 1.05,
}

SWIMMING_SPECIES_BONUS: dict[str, float] = {
    "Neptilius": 1.5,
    "Jormuntide": 1.4, "Jormuntide Ignis": 1.3,
    "Surfent": 1.1,
    "Azurobe": 1.05, "Azurobe Cryst": 1.05,
}


class InvestmentRecommender:
    """Evaluates Pal instances and deterministically allocates upgrade resources."""

    def __init__(self, db_engine: SQLiteEngine):
        self.engine = db_engine

    def _extract_roster_and_inventory(self) -> Tuple[List[dict], dict, dict, dict, dict]:
        """Loads instances, inventory, partner skills, species data, and dupe counts."""
        instances = self.engine.query_instances({})
        cursor = self.engine.conn.cursor()

        # Mount type mapping from partner skills
        mount_types: dict[str, str] = {}
        rows = cursor.execute("""
            SELECT ps.pal_internal_name, ps.description, p.display_name
            FROM partner_skills ps
            LEFT JOIN pals p ON LOWER(ps.pal_internal_name) = LOWER(p.internal_name)
            WHERE LOWER(ps.description) LIKE '%can be ridden%'
        """).fetchall()
        for r in rows:
            desc = (r["description"] or "").lower()
            name = r["display_name"] or r["pal_internal_name"]
            if "flying mount" in desc:
                mount_types[name] = "flying"
            elif "travel on water" in desc or "swimming" in desc:
                mount_types[name] = "swimming"
            else:
                mount_types[name] = "ground"
            if name == "Neptilius":
                mount_types[name] = "swimming"

        # Species base stats
        species_meta: dict[str, dict] = {}
        rows = cursor.execute("""
            SELECT display_name, element_1, element_2, run_speed, attack_melee, hp, defense
            FROM pals
        """).fetchall()
        for r in rows:
            species_meta[r["display_name"]] = {
                "element_1": r["element_1"],
                "element_2": r["element_2"],
                "run_speed": r["run_speed"] or 0,
                "attack": r["attack_melee"] or 0,
                "hp": r["hp"] or 0,
                "defense": r["defense"] or 0,
            }

        # Dupe counts per species
        dupe_counts: dict[str, int] = {}
        rows = cursor.execute("""
            SELECT COALESCE(p.display_name, pi.species) as name, COUNT(*) as count
            FROM pal_instances pi
            LEFT JOIN pals p ON LOWER(pi.species) = LOWER(p.internal_name)
            GROUP BY COALESCE(p.display_name, pi.species)
        """).fetchall()
        for r in rows:
            dupe_counts[r["name"]] = r["count"]

        # Inventory categorization
        raw_items = self.engine.query_inventory()
        inventory: dict[str, Any] = {
            "training_manuals": {"S": 0, "M": 0, "L": 0, "XL": 0},
            "pal_souls": {"Small": 0, "Medium": 0, "Large": 0, "Giant": 0},
            "stat_fruits": {},
            "skill_fruits": [],
            "kinship_items": {},
            "other_consumables": {},
        }

        for item in raw_items:
            iid = (item.get("item_id") or "").lower()
            name = item.get("display_name") or item.get("item_id") or ""
            count = item.get("count", 0)

            if "expboost_01" in iid:
                inventory["training_manuals"]["S"] += count
            elif "expboost_02" in iid:
                inventory["training_manuals"]["M"] += count
            elif "expboost_03" in iid:
                inventory["training_manuals"]["L"] += count
            elif "expboost_04" in iid:
                inventory["training_manuals"]["XL"] += count
            elif iid == "palupgradestone":
                inventory["pal_souls"]["Small"] += count
            elif "palupgradestone2" in iid:
                inventory["pal_souls"]["Medium"] += count
            elif "palupgradestone3" in iid:
                inventory["pal_souls"]["Large"] += count
            elif "palupgradestone4" in iid:
                inventory["pal_souls"]["Giant"] += count
            elif "skill fruit" in name.lower() or "skillfruit" in iid:
                elem_match = re.search(r"(Grass|Fire|Water|Electric|Ice|Ground|Dark|Dragon)", name, re.IGNORECASE)
                element = elem_match.group(1).capitalize() if elem_match else "Neutral"
                inventory["skill_fruits"].append({
                    "name": name,
                    "element": element,
                    "item_id": item.get("item_id"),
                    "count": count,
                })
            elif "fruit" in name.lower() or "peach" in name.lower():
                if "peach" in name.lower():
                    inventory["kinship_items"][name] = inventory["kinship_items"].get(name, 0) + count
                else:
                    inventory["stat_fruits"][name] = inventory["stat_fruits"].get(name, 0) + count
            elif "manual" in name.lower() or "technical" in name.lower():
                inventory["other_consumables"][name] = inventory["other_consumables"].get(name, 0) + count

        return instances, mount_types, species_meta, dupe_counts, inventory

    def _score_combat(
        self,
        pal: dict,
        species_meta: dict,
        dupe_counts: dict,
        inventory: dict
    ) -> dict[str, Any]:
        """Calculates combat potential, immediate viability, and investment priority."""
        species = pal.get("display_name") or pal.get("species", "Unknown")
        level = pal.get("level", 1) or 1
        rank = pal.get("rank", 0) or 0
        passives = [p.get("name", "") for p in pal.get("passives", [])]
        iv_hp = pal.get("iv_hp", 0) or 0
        iv_melee = pal.get("iv_melee", 0) or 0
        iv_defense = pal.get("iv_defense", 0) or 0
        iv_avg = (iv_hp + iv_melee + iv_defense) / 3.0

        species_mult = COMBAT_SPECIES_TIER.get(species, 1.0)
        passive_score = sum(COMBAT_PASSIVE_VALUES.get(p, 0) for p in passives)
        passive_factor = max(0.3, 1.0 + (passive_score / 100.0))
        iv_factor = 0.5 + (iv_avg / 100.0) * 0.5

        raw_potential = species_mult * passive_factor * iv_factor * 100.0

        # Level viability factor
        total_manual_points = (
            inventory["training_manuals"]["S"] * 1
            + inventory["training_manuals"]["M"] * 3
            + inventory["training_manuals"]["L"] * 10
            + inventory["training_manuals"]["XL"] * 30
        )
        if level >= 45:
            level_viability = 1.0
        elif level >= 30:
            level_viability = 0.85
        elif level >= 15:
            level_viability = 0.65
        else:
            level_viability = 0.7 if total_manual_points > 1000 else (0.5 if total_manual_points > 300 else 0.3)

        dupe_count = dupe_counts.get(species, 1)
        condense_bonus = 1.0
        if dupe_count >= 16 and rank < 4:
            condense_bonus = 1.3
        elif dupe_count >= 4 and rank < 4:
            condense_bonus = 1.15

        total_souls = (
            inventory["pal_souls"]["Small"]
            + inventory["pal_souls"]["Medium"] * 3
            + inventory["pal_souls"]["Large"] * 9
            + inventory["pal_souls"]["Giant"] * 27
        )
        soul_bonus = 1.1 if total_souls > 100 or rank > 0 else 1.0

        immediate_viability = raw_potential * level_viability
        investment_priority = raw_potential * condense_bonus * soul_bonus

        meta = species_meta.get(species, {})
        return {
            "instance_id": pal.get("instance_id"),
            "species": species,
            "element_1": meta.get("element_1", pal.get("element_1")),
            "element_2": meta.get("element_2", pal.get("element_2")),
            "level": level,
            "rank": rank,
            "iv_hp": iv_hp,
            "iv_melee": iv_melee,
            "iv_defense": iv_defense,
            "iv_avg": round(iv_avg, 1),
            "passives": passives,
            "passive_score": passive_score,
            "raw_potential": round(raw_potential, 1),
            "immediate_viability": round(immediate_viability, 1),
            "investment_priority": round(investment_priority, 1),
            "dupe_count": dupe_count,
        }

    def _score_transport(
        self,
        pal: dict,
        mount_types: dict,
        species_meta: dict,
        dupe_counts: dict,
        inventory: dict,
        target_type: str
    ) -> Optional[dict[str, Any]]:
        """Calculates transport and mount viability score."""
        species = pal.get("display_name") or pal.get("species", "Unknown")
        if mount_types.get(species) != target_type:
            return None

        level = pal.get("level", 1) or 1
        rank = pal.get("rank", 0) or 0
        passives = [p.get("name", "") for p in pal.get("passives", [])]
        iv_hp = pal.get("iv_hp", 0) or 0
        iv_melee = pal.get("iv_melee", 0) or 0
        iv_defense = pal.get("iv_defense", 0) or 0
        iv_avg = (iv_hp + iv_melee + iv_defense) / 3.0

        meta = species_meta.get(species, {})
        base_speed = meta.get("run_speed", 0)

        if target_type == "flying":
            species_bonus = FLYING_SPECIES_BONUS.get(species, 1.0)
        elif target_type == "ground":
            species_bonus = GROUND_SPECIES_BONUS.get(species, 1.0)
        else:
            species_bonus = SWIMMING_SPECIES_BONUS.get(species, 1.0)

        passive_score = sum(TRANSPORT_PASSIVE_VALUES.get(p, 0) for p in passives)
        passive_factor = max(0.5, 1.0 + (passive_score / 100.0))
        iv_factor = 0.8 + (iv_avg / 100.0) * 0.2

        raw_potential = base_speed * species_bonus * passive_factor * iv_factor

        total_manual_points = (
            inventory["training_manuals"]["S"] * 1
            + inventory["training_manuals"]["M"] * 3
            + inventory["training_manuals"]["L"] * 10
            + inventory["training_manuals"]["XL"] * 30
        )
        if level >= 30:
            level_viability = 1.0
        elif level >= 15:
            level_viability = 0.8
        else:
            level_viability = 0.6 if total_manual_points > 300 else 0.35

        immediate_viability = raw_potential * level_viability

        return {
            "instance_id": pal.get("instance_id"),
            "species": species,
            "element_1": meta.get("element_1", pal.get("element_1")),
            "element_2": meta.get("element_2", pal.get("element_2")),
            "mount_type": target_type,
            "level": level,
            "rank": rank,
            "iv_avg": round(iv_avg, 1),
            "passives": passives,
            "passive_score": passive_score,
            "base_speed": base_speed,
            "raw_potential": round(raw_potential, 1),
            "immediate_viability": round(immediate_viability, 1),
            "dupe_count": dupe_counts.get(species, 1),
        }

    def _allocate_resources_all_in(
        self,
        top_combat: List[dict],
        top_flying: List[dict],
        inventory: dict
    ) -> List[dict[str, Any]]:
        """Option 1: All-In Strategy focusing resources on #1 Primary Carry and #1 Mount."""
        actions: List[dict[str, Any]] = []

        manuals = dict(inventory["training_manuals"])
        souls = dict(inventory["pal_souls"])
        stat_fruits = dict(inventory["stat_fruits"])
        skill_fruits = [dict(sf) for sf in inventory["skill_fruits"]]

        # Primary Carry
        if top_combat:
            primary = top_combat[0]
            action: dict[str, Any] = {
                "target_pal": f"{primary['species']} (Lv{primary['level']}, {primary['rank']}★)",
                "role": "Primary Combat Carry",
                "manuals_allocated": {},
                "souls_allocated": {},
                "stat_fruits_allocated": {},
                "skill_fruits_allocated": [],
                "condensation_step": f"Condense up to {min(primary['dupe_count'], 116)} available duplicate {primary['species']} Pals.",
            }

            # Allocate up to 150 L manuals or available
            l_used = min(manuals.get("L", 0), 120)
            manuals["L"] -= l_used
            xl_used = min(manuals.get("XL", 0), 10)
            manuals["XL"] -= xl_used
            action["manuals_allocated"] = {"Training Manual (L)": l_used, "Training Manual (XL)": xl_used}

            # Allocate souls
            s_used = min(souls.get("Small", 0), 120)
            souls["Small"] -= s_used
            m_used = min(souls.get("Medium", 0), 60)
            souls["Medium"] -= m_used
            lg_used = min(souls.get("Large", 0), 30)
            souls["Large"] -= lg_used
            gt_used = min(souls.get("Giant", 0), 10)
            souls["Giant"] -= gt_used
            action["souls_allocated"] = {
                "Small Pal Soul": s_used,
                "Medium Pal Soul": m_used,
                "Large Pal Soul": lg_used,
                "Giant Pal Soul": gt_used,
            }

            # Stat fruits to carry
            for sf_name, count in list(stat_fruits.items()):
                action["stat_fruits_allocated"][sf_name] = count
                stat_fruits[sf_name] = 0

            # Match skill fruits
            p_elem1 = (primary.get("element_1") or "").capitalize()
            p_elem2 = (primary.get("element_2") or "").capitalize()
            for sf in skill_fruits:
                if sf["count"] > 0 and sf["element"] in [p_elem1, p_elem2, "Dark", "Dragon", "Ground"]:
                    action["skill_fruits_allocated"].append(f"{sf['name']} (x{sf['count']})")
                    sf["count"] = 0

            actions.append(action)

        # Secondary / Mount
        if top_flying:
            mount = top_flying[0]
            action = {
                "target_pal": f"{mount['species']} (Lv{mount['level']}, {mount['rank']}★)",
                "role": "Primary Aerial Mount & Combat Support",
                "manuals_allocated": {
                    "Training Manual (L)": manuals.get("L", 0),
                    "Training Manual (M)": manuals.get("M", 0),
                    "Training Manual (S)": manuals.get("S", 0),
                },
                "souls_allocated": {
                    "Small Pal Soul": souls.get("Small", 0),
                    "Medium Pal Soul": souls.get("Medium", 0),
                    "Large Pal Soul": souls.get("Large", 0),
                    "Giant Pal Soul": souls.get("Giant", 0),
                },
                "stat_fruits_allocated": {},
                "skill_fruits_allocated": [
                    f"{sf['name']} (x{sf['count']})" for sf in skill_fruits if sf["count"] > 0
                ],
                "condensation_step": f"Condense up to {min(mount['dupe_count'], 116)} available duplicate {mount['species']} Pals into 4★ rank.",
            }
            actions.append(action)

        return actions

    def _allocate_resources_party_spread(
        self,
        top_combat: List[dict],
        top_flying: List[dict],
        top_ground: List[dict],
        top_swimming: List[dict],
        inventory: dict
    ) -> List[dict[str, Any]]:
        """Option 2: Party Spread Strategy balancing resources across a full 5-Pal team."""
        party: List[Tuple[dict, str]] = []

        if top_combat:
            party.append((top_combat[0], "Combat Lead"))
        if top_flying:
            party.append((top_flying[0], "Flying Mount"))
        if top_ground:
            party.append((top_ground[0], "Ground Mount"))
        if top_swimming:
            party.append((top_swimming[0], "Aquatic Mount"))

        # 5th slot: next highest combat or growth candidate not already in party
        used_ids = {p[0].get("instance_id") for p in party}
        for c in top_combat[1:]:
            if c.get("instance_id") not in used_ids:
                party.append((c, "Secondary Fighter / Boss Counter"))
                break

        party_size = len(party)
        if party_size == 0:
            return []

        manuals = dict(inventory["training_manuals"])
        souls = dict(inventory["pal_souls"])
        stat_fruits = dict(inventory["stat_fruits"])
        skill_fruits = [dict(sf) for sf in inventory["skill_fruits"]]

        allocations: List[dict[str, Any]] = []

        l_per_pal = manuals.get("L", 0) // party_size
        m_per_pal = manuals.get("M", 0) // party_size
        s_per_pal = manuals.get("S", 0) // party_size
        xl_per_pal = manuals.get("XL", 0) // party_size

        small_soul_per_pal = souls.get("Small", 0) // party_size
        med_soul_per_pal = souls.get("Medium", 0) // party_size
        large_soul_per_pal = souls.get("Large", 0) // party_size
        giant_soul_per_pal = souls.get("Giant", 0) // party_size

        for idx, (pal, role) in enumerate(party):
            entry: dict[str, Any] = {
                "slot": idx + 1,
                "target_pal": f"{pal['species']} (Lv{pal['level']}, {pal['rank']}★)",
                "role": role,
                "manuals_allocated": {
                    "Training Manual (L)": l_per_pal,
                    "Training Manual (M)": m_per_pal,
                    "Training Manual (S)": s_per_pal,
                    "Training Manual (XL)": xl_per_pal,
                },
                "souls_allocated": {
                    "Small Pal Soul": small_soul_per_pal,
                    "Medium Pal Soul": med_soul_per_pal,
                    "Large Pal Soul": large_soul_per_pal,
                    "Giant Pal Soul": giant_soul_per_pal,
                },
                "stat_fruits_allocated": {},
                "skill_fruits_allocated": [],
                "condensation_step": f"Condense {min(pal['dupe_count'], 116)}x duplicate {pal['species']}.",
            }

            # Distribute stat fruits (lead gets Life/Stout)
            if idx == 0:
                for sf_name, count in stat_fruits.items():
                    entry["stat_fruits_allocated"][sf_name] = count

            # Assign skill fruits matching element
            elem1 = (pal.get("element_1") or "").capitalize()
            elem2 = (pal.get("element_2") or "").capitalize()
            for sf in skill_fruits:
                if sf["count"] > 0 and sf["element"] in [elem1, elem2]:
                    entry["skill_fruits_allocated"].append(f"{sf['name']} (x{sf['count']})")
                    sf["count"] = 0

            allocations.append(entry)

        # Distribute remaining unmatched skill fruits to mount fighters
        unmatched = [sf for sf in skill_fruits if sf["count"] > 0]
        for sf in unmatched:
            allocations[0]["skill_fruits_allocated"].append(f"{sf['name']} (x{sf['count']})")

        return allocations

    def generate_recommendations(self, top_n: int = 7) -> dict[str, Any]:
        """Runs the entire recommendation and resource allocation pipeline."""
        instances, mount_types, species_meta, dupe_counts, inventory = self._extract_roster_and_inventory()

        combat_scored: List[dict] = []
        flying_scored: List[dict] = []
        ground_scored: List[dict] = []
        swimming_scored: List[dict] = []

        for pal in instances:
            c = self._score_combat(pal, species_meta, dupe_counts, inventory)
            combat_scored.append(c)

            species = pal.get("display_name") or pal.get("species", "Unknown")
            if species in mount_types:
                for mt in ["flying", "ground", "swimming"]:
                    res = self._score_transport(pal, mount_types, species_meta, dupe_counts, inventory, mt)
                    if res:
                        if mt == "flying":
                            flying_scored.append(res)
                        elif mt == "ground":
                            ground_scored.append(res)
                        else:
                            swimming_scored.append(res)

        combat_scored.sort(key=lambda x: x["investment_priority"], reverse=True)
        flying_scored.sort(key=lambda x: x["raw_potential"], reverse=True)
        ground_scored.sort(key=lambda x: x["raw_potential"], reverse=True)
        swimming_scored.sort(key=lambda x: x["raw_potential"], reverse=True)

        all_transport = flying_scored + ground_scored + swimming_scored
        all_transport.sort(key=lambda x: x["raw_potential"], reverse=True)

        leveling = [c for c in combat_scored if c["level"] < 25 and c["raw_potential"] > 80]
        leveling.sort(key=lambda x: x["raw_potential"], reverse=True)

        all_in_alloc = self._allocate_resources_all_in(combat_scored, flying_scored, inventory)
        party_alloc = self._allocate_resources_party_spread(
            combat_scored, flying_scored, ground_scored, swimming_scored, inventory
        )

        return {
            "inventory": inventory,
            "total_pals": len(instances),
            "combat_top": combat_scored[:top_n],
            "flying_top": flying_scored[:top_n],
            "ground_top": ground_scored[:top_n],
            "swimming_top": swimming_scored[:top_n],
            "best_of_all_top": all_transport[:2],
            "leveling_top": leveling[:top_n],
            "allocation_all_in": all_in_alloc,
            "allocation_party_spread": party_alloc,
        }

    def generate_report_markdown(self, top_n: int = 7) -> str:
        """Generates a deterministic markdown report from the recommendation data."""
        data = self.generate_recommendations(top_n=top_n)
        inv = data["inventory"]

        lines: List[str] = [
            "# Pal Investment Recommendation Report",
            "",
            f"> Analysis executed deterministically across **{data['total_pals']} Pals** extracted from save data.",
            "",
            "---",
            "",
            "## 1. Available Upgrade Resource Budget",
            "",
            "### Training Manuals & EXP",
            "| Item | Quantity | Estimated Impact |",
            "|:---|---:|:---|",
            f"| Training Manual (S) | {inv['training_manuals']['S']} | Tiny EXP booster |",
            f"| Training Manual (M) | {inv['training_manuals']['M']} | Small EXP booster |",
            f"| Training Manual (L) | {inv['training_manuals']['L']} | **High Impact** (Primary Leveling Engine) |",
            f"| Training Manual (XL) | {inv['training_manuals']['XL']} | **Massive EXP boost** |",
            "",
            "### Pal Souls (Stat Enhancements)",
            "| Item | Quantity | Tier |",
            "|:---|---:|:---|",
            f"| Small Pal Soul | {inv['pal_souls']['Small']} | Tier 1-3 Enhancements |",
            f"| Medium Pal Soul | {inv['pal_souls']['Medium']} | Tier 4-6 Enhancements |",
            f"| Large Pal Soul | {inv['pal_souls']['Large']} | Tier 7-9 Enhancements |",
            f"| Giant Pal Soul | {inv['pal_souls']['Giant']} | Max Tier Enhancements |",
            "",
            "### Stat Fruits, Kinship & Skill Consumables",
            "| Category | Item | Quantity |",
            "|:---|:---|---:|",
        ]

        for sf_name, count in inv["stat_fruits"].items():
            lines.append(f"| Stat Fruit | {sf_name} | {count} |")
        for kp_name, count in inv["kinship_items"].items():
            lines.append(f"| Kinship Item | {kp_name} | {count} |")
        for sf in inv["skill_fruits"]:
            lines.append(f"| Skill Fruit ({sf['element']}) | {sf['name']} | {sf['count']} |")

        lines.extend([
            "",
            "---",
            "",
            f"## 2. Top {top_n} Combat Candidates",
            "",
            "| # | Species | Element | Lv | Rank | IV (HP/ATK/DEF) | IV Avg | Key Passives | Potential | Priority | Dupe Stock |",
            "|:--|:--------|:--------|---:|:-----|:----------------|-------:|:-------------|----------:|---------:|-----------:|",
        ])

        for i, c in enumerate(data["combat_top"], 1):
            elem = "/".join(filter(None, [c.get("element_1"), c.get("element_2")])) or "Neutral"
            passives_str = ", ".join(c["passives"]) if c["passives"] else "None"
            lines.append(
                f"| {i} | **{c['species']}** | {elem} | {c['level']} | {c['rank']}★ | "
                f"{c['iv_hp']}/{c['iv_melee']}/{c['iv_defense']} | {c['iv_avg']} | "
                f"{passives_str} | {c['raw_potential']} | {c['investment_priority']} | {c['dupe_count']} |"
            )

        lines.extend([
            "",
            "---",
            "",
            f"## 3. Top {top_n} Flying Mount Candidates",
            "",
            "| # | Species | Element | Lv | Base Speed | Passives | Potential | Dupe Stock |",
            "|:--|:--------|:--------|---:|-----------:|:---------|----------:|-----------:|",
        ])

        for i, f in enumerate(data["flying_top"], 1):
            elem = "/".join(filter(None, [f.get("element_1"), f.get("element_2")])) or "Neutral"
            passives_str = ", ".join(f["passives"]) if f["passives"] else "None"
            lines.append(
                f"| {i} | **{f['species']}** | {elem} | {f['level']} | {f['base_speed']} | "
                f"{passives_str} | {f['raw_potential']} | {f['dupe_count']} |"
            )

        lines.extend([
            "",
            "---",
            "",
            f"## 4. Top {top_n} Ground Riding Mount Candidates",
            "",
            "| # | Species | Element | Lv | Base Speed | Passives | Potential | Dupe Stock |",
            "|:--|:--------|:--------|---:|-----------:|:---------|----------:|-----------:|",
        ])

        for i, g in enumerate(data["ground_top"], 1):
            elem = "/".join(filter(None, [g.get("element_1"), g.get("element_2")])) or "Neutral"
            passives_str = ", ".join(g["passives"]) if g["passives"] else "None"
            lines.append(
                f"| {i} | **{g['species']}** | {elem} | {g['level']} | {g['base_speed']} | "
                f"{passives_str} | {g['raw_potential']} | {g['dupe_count']} |"
            )

        lines.extend([
            "",
            "---",
            "",
            f"## 5. Top {top_n} Swimming Mount Candidates",
            "",
            "| # | Species | Element | Lv | Base Speed | Passives | Potential | Dupe Stock |",
            "|:--|:--------|:--------|---:|-----------:|:---------|----------:|-----------:|",
        ])

        for i, s in enumerate(data["swimming_top"], 1):
            elem = "/".join(filter(None, [s.get("element_1"), s.get("element_2")])) or "Neutral"
            passives_str = ", ".join(s["passives"]) if s["passives"] else "None"
            lines.append(
                f"| {i} | **{s['species']}** | {elem} | {s['level']} | {s['base_speed']} | "
                f"{passives_str} | {s['raw_potential']} | {s['dupe_count']} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 6. Top 2 Best-Of-All Transport Candidates",
            "",
            "| # | Species | Mount Type | Lv | Base Speed | Passives | Potential |",
            "|:--|:--------|:-----------|---:|-----------:|:---------|----------:|",
        ])

        for i, b in enumerate(data["best_of_all_top"], 1):
            passives_str = ", ".join(b["passives"]) if b["passives"] else "None"
            lines.append(
                f"| {i} | **{b['species']}** | {b['mount_type'].capitalize()} | {b['level']} | "
                f"{b['base_speed']} | {passives_str} | {b['raw_potential']} |"
            )

        lines.extend([
            "",
            "---",
            "",
            f"## 7. Top {top_n} Leveling Priority Candidates",
            "",
            "| # | Species | Element | Lv | IV (HP/ATK/DEF) | Key Passives | Potential |",
            "|:--|:--------|:--------|---:|:----------------|:-------------|----------:|",
        ])

        for i, l in enumerate(data["leveling_top"], 1):
            elem = "/".join(filter(None, [l.get("element_1"), l.get("element_2")])) or "Neutral"
            passives_str = ", ".join(l["passives"]) if l["passives"] else "None"
            lines.append(
                f"| {i} | **{l['species']}** | {elem} | {l['level']} | "
                f"{l['iv_hp']}/{l['iv_melee']}/{l['iv_defense']} | {passives_str} | {l['raw_potential']} |"
            )

        # Strategy 1
        lines.extend([
            "",
            "---",
            "",
            "## 8. Resource Allocation — Strategy 1: All-In Carry Focus",
            "",
            "> Directs all highest-impact materials into the single highest-ceiling combat Pal and primary mount.",
            "",
        ])

        for act in data["allocation_all_in"]:
            lines.append(f"### Target: {act['target_pal']} — Role: `{act['role']}`")
            lines.append("- **Training Manuals Assigned**:")
            for m_name, count in act["manuals_allocated"].items():
                if count > 0:
                    lines.append(f"  - {m_name}: `{count}` units")
            lines.append("- **Pal Souls Assigned**:")
            for s_name, count in act["souls_allocated"].items():
                if count > 0:
                    lines.append(f"  - {s_name}: `{count}` units")
            if act["stat_fruits_allocated"]:
                lines.append("- **Stat Fruits Assigned**:")
                for sf_name, count in act["stat_fruits_allocated"].items():
                    lines.append(f"  - {sf_name}: `{count}` units")
            if act["skill_fruits_allocated"]:
                lines.append("- **Skill Fruits Assigned**:")
                for skf in act["skill_fruits_allocated"]:
                    lines.append(f"  - {skf}")
            lines.append(f"- **Condensation Step**: {act['condensation_step']}")
            lines.append("")

        # Strategy 2
        lines.extend([
            "---",
            "",
            "## 9. Resource Allocation — Strategy 2: 5-Pal Active Party Spread",
            "",
            "> Balances available Training Manuals, Pal Souls, and Skill Fruits evenly across a complete 5-Pal squad.",
            "",
        ])

        for act in data["allocation_party_spread"]:
            lines.append(f"### Slot {act['slot']}: {act['target_pal']} — `{act['role']}`")
            lines.append("- **Training Manuals Assigned**:")
            for m_name, count in act["manuals_allocated"].items():
                if count > 0:
                    lines.append(f"  - {m_name}: `{count}` units")
            lines.append("- **Pal Souls Assigned**:")
            for s_name, count in act["souls_allocated"].items():
                if count > 0:
                    lines.append(f"  - {s_name}: `{count}` units")
            if act["stat_fruits_allocated"]:
                lines.append("- **Stat Fruits Assigned**:")
                for sf_name, count in act["stat_fruits_allocated"].items():
                    lines.append(f"  - {sf_name}: `{count}` units")
            if act["skill_fruits_allocated"]:
                lines.append("- **Skill Fruits Assigned**:")
                for skf in act["skill_fruits_allocated"]:
                    lines.append(f"  - {skf}")
            lines.append(f"- **Condensation Step**: {act['condensation_step']}")
            lines.append("")

        return "\n".join(lines)
