"""Boss Counter Party Recommender for PalEngine.

Deterministic recommendation engine for 5-Pal party boss encounters
(Tower Bosses, Alpha Field Bosses / Legendaries, and Dungeon Bosses).
Evaluates player save data, element advantages, IVs, passives, ranks,
mount damage conversion, and support buffers without internal GUIDs.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from palengine.db.sqlite_engine import SQLiteEngine


# ==============================================================================
# Palworld Elemental Advantages & Resistances Matrix
# ==============================================================================

ELEMENT_ADVANTAGES: dict[str, list[str]] = {
    "Fire": ["Grass", "Ice"],
    "Grass": ["Ground"],
    "Ground": ["Electric"],
    "Electric": ["Water"],
    "Water": ["Fire"],
    "Ice": ["Dragon"],
    "Dragon": ["Dark"],
    "Dark": ["Neutral"],
    "Neutral": [],
}

ELEMENT_WEAKNESSES: dict[str, list[str]] = {
    "Fire": ["Water"],
    "Grass": ["Fire"],
    "Ground": ["Grass"],
    "Electric": ["Ground"],
    "Water": ["Electric"],
    "Ice": ["Fire"],
    "Dragon": ["Ice"],
    "Dark": ["Dragon"],
    "Neutral": ["Dark"],
}

# Mounts that change player attack to an element and/or boost that element
MOUNT_CONVERTERS: dict[str, dict[str, Any]] = {
    # Dragon
    "Chillet": {"element": "Dragon", "bonus": "Converts player attack to Dragon + Dragon Atk boost while riding"},
    "Quivern": {"element": "Dragon", "bonus": "Boosts Dragon attacks while riding"},
    # Water
    "Azurobe": {"element": "Water", "bonus": "Converts player attack to Water + Water Atk boost while riding"},
    "Suzaku Aqua": {"element": "Water", "bonus": "Boosts Water attacks while riding"},
    "Jormuntide": {"element": "Water", "bonus": "Can be ridden on water + prevents stamina drain"},
    # Fire
    "Ragnahawk": {"element": "Fire", "bonus": "Converts player attack to Fire + Fire Atk boost while riding"},
    "Pyrin": {"element": "Fire", "bonus": "Converts player attack to Fire while riding"},
    "Blazamut": {"element": "Fire", "bonus": "Boosts Fire attacks while riding"},
    "Faleris": {"element": "Fire", "bonus": "Increases drops from Ice Pals while riding"},
    # Ice
    "Frostallion": {"element": "Ice", "bonus": "Converts player attack to Ice + Ice Atk boost while riding"},
    "Vanwyrm Cryst": {"element": "Ice", "bonus": "Increases damage to weak points while riding"},
    # Electric
    "Beakon": {"element": "Electric", "bonus": "Converts player attack to Electric + Electric Atk boost while riding"},
    "Helzephyr Lux": {"element": "Electric", "bonus": "Converts player attack to Electric while riding"},
    # Dark
    "Frostallion Noct": {"element": "Dark", "bonus": "Converts player attack to Dark + Dark Atk boost while riding"},
    "Helzephyr": {"element": "Dark", "bonus": "Converts player attack to Dark while riding"},
    "Shadowbeak": {"element": "Dark", "bonus": "Boosts Dark attacks while riding"},
    "Maraith": {"element": "Dark", "bonus": "Converts player attack to Dark while riding"},
    # Grass
    "Verdash": {"element": "Grass", "bonus": "Increases player movement speed & applies Grass to player attacks while fighting together"},
}


# ==============================================================================
# Boss Registry (Tower Bosses, Legendaries, and Alpha Bosses)
# ==============================================================================

BOSS_REGISTRY: dict[str, dict[str, Any]] = {
    # 1. Tower Bosses (10-minute arena time limit = 600s)
    "zoe & grizzbolt": {
        "canonical_name": "Zoe & Grizzbolt",
        "location": "Rayne Syndicate Tower (Isolated Island: 112, -434)",
        "level": 10,
        "hp": 30550,
        "time_limit_sec": 600,
        "elements": ["Electric"],
        "weaknesses": ["Ground"],
        "dangerous_moves": ["Lightning Claw", "Lock-on Laser", "Shockwave"],
        "tactics": "Use arena pillars to block Grizzbolt's Minigun barrage. Ground attacks interrupt his charges.",
    },
    "lily & lyleen": {
        "canonical_name": "Lily & Lyleen",
        "location": "Free Pal Alliance Tower (Verdant Brook: 181, 28)",
        "level": 25,
        "hp": 69375,
        "time_limit_sec": 600,
        "elements": ["Grass"],
        "weaknesses": ["Fire"],
        "dangerous_moves": ["Seed Mine", "Hurricane Slice", "Healing Bloom"],
        "tactics": "Bring high-burst Fire Pals to out-damage Lyleen's healing and stagger her wind tornadoes.",
    },
    "axel & orserk": {
        "canonical_name": "Axel & Orserk",
        "location": "Brothers of the Eternal Pyre Tower (Mount Obsidian: -587, -517)",
        "level": 40,
        "hp": 130700,
        "time_limit_sec": 600,
        "elements": ["Dragon", "Electric"],
        "weaknesses": ["Ice", "Ground"],
        "dangerous_moves": ["Kerauno", "Lightning Strike", "Dragon Meteor"],
        "tactics": "Dual weaknesses: Use Ice for Dragon typing and Ground for Electric typing. Keep distance during Kerauno.",
    },
    "marcus & faleris": {
        "canonical_name": "Marcus & Faleris",
        "location": "PIDF Tower (Dessicated Dunes: 561, 334)",
        "level": 45,
        "hp": 146975,
        "time_limit_sec": 600,
        "elements": ["Fire"],
        "weaknesses": ["Water"],
        "dangerous_moves": ["Ignis Rage", "Fire Ball", "Phoenix Flare"],
        "tactics": "Continuous airborne mobility. Use high-speed Water moves (Aqua Gun, Hydro Laser) and keep moving.",
    },
    "victor & shadowbeak": {
        "canonical_name": "Victor & Shadowbeak",
        "location": "PAL Genetic Research Unit Tower (Astral Mountains: -148, 447)",
        "level": 50,
        "hp": 200750,
        "time_limit_sec": 600,
        "elements": ["Dark"],
        "weaknesses": ["Dragon"],
        "dangerous_moves": ["Divine Disaster", "Nightmare Ball", "Dark Laser"],
        "tactics": "Divine Disaster is lethal. Hug arena pillars to break projectile line of sight. Dragon deals 2.0x STAB.",
    },
    "saya & selyne": {
        "canonical_name": "Saya & Selyne",
        "location": "Moonflower Tower (Sakurajima: -600, 180)",
        "level": 55,
        "hp": 258000,
        "time_limit_sec": 600,
        "elements": ["Dark", "Neutral"],
        "weaknesses": ["Dragon", "Dark"],
        "dangerous_moves": ["Star Fall", "Lunar Beam", "Dark Blast"],
        "tactics": "Selyne has rapid laser sweeps. Bring Dragon/Dark tanks and stagger her with heavy artillery.",
    },

    # 2. Alpha Legendaries & Major Field Alphas (Open world - no hard arena timer)
    "jetragon": {
        "canonical_name": "Jetragon (Alpha Legendary)",
        "location": "Mount Obsidian (-845, -450)",
        "level": 50,
        "hp": 11500,
        "time_limit_sec": None,
        "elements": ["Dragon"],
        "weaknesses": ["Ice"],
        "dangerous_moves": ["Beam Slicer", "Dragon Meteor", "Fire Ball"],
        "tactics": "Extreme flight speed. Deploy Frostallion or Ice converters with rapid-fire firearms.",
    },
    "frostallion": {
        "canonical_name": "Frostallion (Alpha Legendary)",
        "location": "Astral Mountains (-357, 508)",
        "level": 50,
        "hp": 14500,
        "time_limit_sec": None,
        "elements": ["Ice"],
        "weaknesses": ["Fire"],
        "dangerous_moves": ["Crystal Wing", "Blizzard Spike", "Iceberg"],
        "tactics": "Bring mounted Fire DPS (Ragnahawk/Blazamut) to deal double damage and melt her ice barriers.",
    },
    "necromus": {
        "canonical_name": "Necromus (Alpha Legendary)",
        "location": "Dessicated Dunes (285, 655)",
        "level": 50,
        "hp": 13000,
        "time_limit_sec": None,
        "elements": ["Dark"],
        "weaknesses": ["Dragon"],
        "dangerous_moves": ["Twin Spears", "Shadow Burst", "Dark Ball"],
        "tactics": "Often fought alongside Paladius. Separate them and focus Necromus down with Dragon firepower.",
    },
    "paladius": {
        "canonical_name": "Paladius (Alpha Legendary)",
        "location": "Dessicated Dunes (285, 655)",
        "level": 50,
        "hp": 13000,
        "time_limit_sec": None,
        "elements": ["Neutral"],
        "weaknesses": ["Dark"],
        "dangerous_moves": ["Spear Thrust", "Holy Beam", "Iceberg"],
        "tactics": "High defensive shields. Bring Dark Pals (Frostallion Noct, Shadowbeak, Astegon) to shred armor.",
    },
    "blazamut": {
        "canonical_name": "Blazamut (Alpha Boss)",
        "location": "Mount Obsidian Mineshaft (-434, -531)",
        "level": 49,
        "hp": 10500,
        "time_limit_sec": None,
        "elements": ["Fire"],
        "weaknesses": ["Water"],
        "dangerous_moves": ["Magma Burst", "Fire Ball", "Rock Burst"],
        "tactics": "Enclosed cave arena. Jormuntide or Azurobe water barrage keeps him staggered continuously.",
    },
    "astegon": {
        "canonical_name": "Astegon (Alpha Boss)",
        "location": "Destroyed Mineshaft (-615, -429)",
        "level": 48,
        "hp": 9800,
        "time_limit_sec": None,
        "elements": ["Dragon", "Dark"],
        "weaknesses": ["Ice", "Dragon"],
        "dangerous_moves": ["Dragon Breath", "Dragon Meteor", "Dark Laser"],
        "tactics": "Dual weaknesses to Ice and Dragon. High melee defense, use ranged projectile active skills.",
    },
}


class BossPartyRecommender:
    """Generates optimal 5-Pal counter-parties for any boss encounter from local save data."""

    def __init__(self, engine: SQLiteEngine):
        self.engine = engine

    def resolve_boss(self, query: str) -> Optional[dict[str, Any]]:
        """Resolves user query string into a structured Boss Profile."""
        cleaned = query.strip().lower()
        
        # Direct match from registry
        for key, profile in BOSS_REGISTRY.items():
            if key in cleaned or cleaned in key:
                profile_copy = dict(profile)
                if profile_copy.get("time_limit_sec"):
                    profile_copy["required_dps"] = round(profile_copy["hp"] / profile_copy["time_limit_sec"], 1)
                else:
                    profile_copy["required_dps"] = None
                return profile_copy
                
        # Keyword checks (e.g. "victor", "faleris", "grizzbolt")
        for key, profile in BOSS_REGISTRY.items():
            words = re.findall(r"\w+", key)
            if any(w in cleaned for w in words if len(w) > 3):
                profile_copy = dict(profile)
                if profile_copy.get("time_limit_sec"):
                    profile_copy["required_dps"] = round(profile_copy["hp"] / profile_copy["time_limit_sec"], 1)
                else:
                    profile_copy["required_dps"] = None
                return profile_copy

        # Fallback: Query static SQLite Paldex for any Alpha/Pal species
        cursor = self.engine.conn.cursor()
        cursor.execute(
            """
            SELECT name, display_name, element_1, element_2, hp, attack_melee, defense
            FROM pals
            WHERE lower(name) LIKE ? OR lower(display_name) LIKE ?
            LIMIT 1
            """,
            (f"%{cleaned}%", f"%{cleaned}%"),
        )
        row = cursor.fetchone()
        if row:
            e1 = row["element_1"] or "Neutral"
            e2 = row["element_2"]
            elems = [e1] if not e2 else [e1, e2]
            weaknesses = []
            for el in elems:
                weaknesses.extend(ELEMENT_WEAKNESSES.get(el, []))
            weaknesses = list(dict.fromkeys(weaknesses))
            est_hp = row["hp"] * 100 if row["hp"] else 10000

            return {
                "canonical_name": f"Alpha {row['display_name'] or row['name']}",
                "location": "Palpagos Islands (Wild / Dungeon Encounter)",
                "level": 50,
                "hp": est_hp,
                "time_limit_sec": None,
                "required_dps": None,
                "elements": elems,
                "weaknesses": weaknesses,
                "dangerous_moves": ["Elemental Signature Skill", "Charge Attack"],
                "tactics": f"Target weakness ({', '.join(weaknesses)}) to gain 2.0x super-effective STAB multiplier.",
            }

        return None

    def get_human_pal_representation(self, pal_instance: dict[str, Any]) -> str:
        """Builds a human-readable identifier without raw IDs."""
        species = pal_instance.get("display_name") or pal_instance.get("species")
        level = pal_instance.get("level", 1)
        gender = pal_instance.get("gender") or "None"
        gender_str = f"({gender})" if gender in ["Male", "Female"] else ""
        rank = pal_instance.get("rank", 0)
        rank_str = f"{rank} Star" if rank > 0 else "0 Star"
        passives = pal_instance.get("passives", [])
        pass_names = [p["name"] if isinstance(p, dict) else str(p) for p in passives]
        pass_str = f"[{', '.join(pass_names)}]" if pass_names else "[No Passives]"
        loc_str = self._format_location(pal_instance)

        return f"{species} {gender_str} (Lv.{level}, {rank_str}) {pass_str} | {loc_str}".replace("  ", " ")

    def _format_location(self, pal_instance: dict[str, Any]) -> str:
        loc = (pal_instance.get("location") or "palbox").lower()
        if loc == "party":
            return "In Party"
        elif loc == "base":
            base_name = (
                pal_instance.get("location_details_base_camp_name")
                or pal_instance.get("location_details", {}).get("base_camp_name")
                if isinstance(pal_instance.get("location_details"), dict)
                else None
            )
            return f"Base: {base_name}" if base_name and base_name != "None" else "Base Camp"
        return "Palbox"

    def evaluate_encounter_readiness(
        self,
        boss: dict[str, Any],
        party: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Evaluates player party readiness, level gap, and time limit viability against the boss."""
        boss_level = boss.get("level", 50)
        party_levels = [p.get("level", 1) for p in party]
        highest_lvl = max(party_levels) if party_levels else 1
        avg_lvl = round(sum(party_levels) / len(party_levels), 1) if party_levels else 1
        level_gap = highest_lvl - boss_level

        # Elemental counter count
        weaknesses = set(boss.get("weaknesses", []))
        counter_count = 0
        for p in party:
            e1 = p.get("element_1") or ""
            e2 = p.get("element_2") or ""
            if e1 in weaknesses or e2 in weaknesses:
                counter_count += 1

        time_limit_sec = boss.get("time_limit_sec")
        req_dps = boss.get("required_dps")

        if level_gap >= 0 and counter_count >= 1:
            status = "FAVORED"
            verdict = f"Encounter is favored. Lead Pal (Lv.{highest_lvl}) matches or exceeds Boss level (Lv.{boss_level}) with {counter_count} super-effective counter(s)."
        elif level_gap >= -5 and counter_count >= 1:
            status = "CHALLENGING"
            verdict = f"Viable but challenging (Level gap: {level_gap}). Stagger rotation and careful dodging required."
        elif level_gap >= -9:
            status = "HIGH DIFFICULTY"
            verdict = f"High difficulty (Level gap: {level_gap}). Boss inflicts severe level-scaling damage penalties against your party."
        else:
            status = "UNLIKELY / NOT RECOMMENDED"
            verdict = f"Encounter unlikely to succeed with current roster (Level gap: {level_gap}). Leveling to at least Lv.{max(1, boss_level - 5)} is strongly advised."

        # Time constraint notes
        if time_limit_sec:
            time_mins = time_limit_sec // 60
            if status in ("HIGH DIFFICULTY", "UNLIKELY / NOT RECOMMENDED"):
                timer_note = f"[HIGH TIMEOUT RISK] Must output {req_dps:,} DPS to burn {boss['hp']:,} HP within the strict {time_mins}-minute arena limit. Underleveled damage penalties make this timeout very likely."
            else:
                timer_note = f"Arena Time Limit: {time_mins} minutes ({time_limit_sec}s). Minimum sustained DPS threshold: {req_dps:,} DPS."
        else:
            timer_note = "Open Field / Dungeon Encounter: No hard arena timer. Prioritize kiting and Pal recall dodging."

        return {
            "status": status,
            "highest_pal_level": highest_lvl,
            "average_party_level": avg_lvl,
            "boss_level": boss_level,
            "level_gap": level_gap,
            "counter_elements_in_party": counter_count,
            "time_limit": f"{time_limit_sec // 60} min ({time_limit_sec}s)" if time_limit_sec else "No Timer (Open Field)",
            "required_dps": req_dps,
            "verdict": verdict,
            "timer_note": timer_note,
        }

    def recommend_party_for_boss(
        self,
        boss_query: str,
        save_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """Calculates the single best 5-Pal party for the specified boss encounter."""
        boss = self.resolve_boss(boss_query)
        if not boss:
            raise ValueError(
                f"Could not find or resolve boss '{boss_query}'. Please check the name or element."
            )

        all_instances = self.engine.query_instances({})
        if not all_instances:
            if save_path:
                self.engine.load_save_data(save_path)
            else:
                from palengine.cli.main import get_resolved_save_path
                try:
                    resolved = get_resolved_save_path(None)
                    self.engine.load_save_data(resolved)
                except Exception:
                    pass
            all_instances = self.engine.query_instances({})

        # Static definitions lookup
        static_pals: dict[str, Any] = {}
        for p in self.engine.query_pals({}):
            for k in ["name", "display_name", "internal_name", "id", "code"]:
                val = p.get(k)
                if val:
                    static_pals[str(val).lower()] = p

        # Enrich instances with static metadata & passives
        enriched: list[dict[str, Any]] = []
        for inst in all_instances:
            spec = (inst.get("species") or "").lower()
            disp = (inst.get("display_name") or "").lower()
            st = static_pals.get(disp) or static_pals.get(spec) or {}
            inst_copy = dict(inst)
            inst_copy["element_1"] = st.get("element_1") or "Neutral"
            inst_copy["element_2"] = st.get("element_2")
            inst_copy["base_hp"] = st.get("hp", 100)
            inst_copy["base_atk"] = st.get("attack_melee", 100)
            inst_copy["base_def"] = st.get("defense", 100)
            enriched.append(inst_copy)

        weaknesses = boss["weaknesses"]

        # Score combat potential of each Pal instance against this boss
        scored_pals = []
        for p in enriched:
            e1 = p.get("element_1")
            e2 = p.get("element_2")
            is_counter = e1 in weaknesses or e2 in weaknesses
            
            lvl = p.get("level", 1)
            rank = p.get("rank", 0)
            atk_iv = p.get("iv_melee", 0)
            hp_iv = p.get("iv_hp", 0)
            def_iv = p.get("iv_defense", 0)
            
            passives = [p_obj.get("name") if isinstance(p_obj, dict) else str(p_obj) for p_obj in p.get("passives", [])]
            pass_score = 0
            if "Legend" in passives: pass_score += 30
            if "Ferocious" in passives: pass_score += 20
            if "Musclehead" in passives: pass_score += 25
            if "Serenity" in passives: pass_score += 25
            if "Burly Body" in passives: pass_score += 15
            if "Aggressive" in passives: pass_score += 10
            if "Brave" in passives: pass_score += 10
            if "Vanguard" in passives: pass_score += 20
            if "Stronghold Strategist" in passives: pass_score += 20
            if any("cheery" in p_name.lower() for p_name in passives) and "Dark" in boss["elements"]: pass_score += 15
            if any("heatproof" in p_name.lower() or "suntan" in p_name.lower() for p_name in passives) and "Fire" in boss["elements"]: pass_score += 15

            # Penalty for pacifist/slacker
            if "Pacifist" in passives: pass_score -= 30
            if "Slacker" in passives: pass_score -= 20
            if "Coward" in passives: pass_score -= 20

            base_score = (lvl * 15) + (rank * 20) + ((atk_iv + hp_iv + def_iv) * 0.2) + pass_score
            if is_counter:
                base_score *= 2.0  # 2x super effective STAB weight

            p["combat_score"] = round(base_score, 1)
            p["is_counter"] = is_counter
            scored_pals.append(p)

        scored_pals.sort(key=lambda x: x["combat_score"], reverse=True)

        # ----------------------------------------------------------------------
        # Synthesize Single Best 5-Pal Counter Team
        # ----------------------------------------------------------------------
        best_party_instances: list[dict[str, Any]] = []
        party_roles: list[str] = []

        # 1. Lead DPS: Check for Weakness Infusion Mount first, or top counter
        best_mount = None
        for p in scored_pals:
            disp_name = p.get("display_name") or p.get("species")
            if disp_name in MOUNT_CONVERTERS:
                mount_elem = MOUNT_CONVERTERS[disp_name]["element"]
                if mount_elem in weaknesses:
                    best_mount = p
                    break

        lead_pal = best_mount if (best_mount and best_mount.get("combat_score", 0) >= 200) else (scored_pals[0] if scored_pals else None)
        if lead_pal:
            best_party_instances.append(lead_pal)
            disp_name = lead_pal.get("display_name") or lead_pal.get("species")
            if disp_name in MOUNT_CONVERTERS and MOUNT_CONVERTERS[disp_name]["element"] in weaknesses:
                party_roles.append("Lead DPS & Elemental Infusion Mount")
            else:
                party_roles.append("Lead Elemental DPS")

        # 2. Secondary Attacker / Tough Combatant
        for p in scored_pals:
            if p not in best_party_instances:
                best_party_instances.append(p)
                party_roles.append("Secondary Elemental DPS / Aggro Switch")
                break

        # 3. Synergy Buffers (Gobfins for player attack or Vanguard/Stronghold Pals)
        gobbfin_pals = [
            p for p in enriched
            if "gobfin" in (p.get("display_name") or "").lower()
            and p not in best_party_instances
        ]
        gobbfin_pals.sort(key=lambda x: (x.get("rank", 0), x.get("level", 0)), reverse=True)

        vanguard_pals = [
            p for p in enriched
            if any("vanguard" in (p_obj.get("name") if isinstance(p_obj, dict) else str(p_obj)).lower() for p_obj in p.get("passives", []))
            and p not in best_party_instances
            and p not in gobbfin_pals
        ]
        vanguard_pals.sort(key=lambda x: x.get("level", 0), reverse=True)

        # Add up to 2 Gobfins if player has them and is using mounted/player combat
        for g in gobbfin_pals:
            if len(best_party_instances) < 5:
                best_party_instances.append(g)
                party_roles.append("Player Attack Buffer (Gobfin Synergy)")
            if len(best_party_instances) == 4:
                break

        # Add Vanguard/Stronghold buffers
        for v in vanguard_pals:
            if len(best_party_instances) < 5 and v not in best_party_instances:
                best_party_instances.append(v)
                party_roles.append("Player & Party Combat Buffer (Vanguard)")

        # Fill remaining slots with next top combat score counters/tanks
        for p in scored_pals:
            if p not in best_party_instances:
                best_party_instances.append(p)
                party_roles.append("Elemental Attacker / Tank Support")
            if len(best_party_instances) == 5:
                break

        # Format party with tailored movesets and role-specific passive priorities
        formatted_team = []
        for p, role in zip(best_party_instances, party_roles):
            formatted_team.append(self._format_team_member_with_waza(p, role, weaknesses))

        # Evaluate encounter readiness
        readiness = self.evaluate_encounter_readiness(boss, best_party_instances)

        return {
            "boss_profile": boss,
            "encounter_readiness": readiness,
            "recommended_party": formatted_team,
            "tactics": boss.get("tactics", ""),
        }

    def _format_team_member_with_waza(
        self,
        pal: dict[str, Any],
        role_hint: str,
        weaknesses: list[str],
    ) -> dict[str, Any]:
        passives = [p["name"] if isinstance(p, dict) else str(p) for p in pal.get("passives", [])]
        elem = f"{pal.get('element_1') or '?'}/{pal.get('element_2') or ''}".rstrip('/')
        gender = pal.get("gender") or "None"
        rank = pal.get("rank", 0)
        
        # Determine tailored active waza (moveset)
        pal_elements = [pal.get("element_1"), pal.get("element_2")]
        pal_elements = [e for e in pal_elements if e]
        # Prefer moves matching boss weakness first, then Pal's STAB element
        target_elements = [e for e in weaknesses if e in pal_elements]
        if not target_elements:
            target_elements = weaknesses + pal_elements
        
        assigned_waza = self._get_tailored_waza_for_pal(target_elements)

        # Determine optimal target passives based on role
        if "Buffer" in role_hint or "Gobfin" in role_hint:
            optimal_passives = ["Vanguard", "Stronghold Strategist", "Noble", "Fine Coat"]
        elif "Tank" in role_hint:
            optimal_passives = ["Burly Body", "Hard Skin", "Legend", "Masochist"]
        else:
            optimal_passives = ["Ferocious", "Musclehead", "Legend", "Serenity"]

        return {
            "species": pal.get("display_name") or pal.get("species"),
            "gender": gender,
            "level": pal.get("level", 1),
            "rank": f"{rank} Star" if rank > 0 else "0 Star",
            "element": elem,
            "location": self._format_location(pal),
            "passives": passives if passives else ["None"],
            "ivs": f"{pal.get('iv_hp', 0)}/{pal.get('iv_melee', 0)}/{pal.get('iv_defense', 0)}",
            "human_label": self.get_human_pal_representation(pal),
            "role": role_hint,
            "recommended_waza": assigned_waza,
            "optimal_passives": optimal_passives,
        }

    def _get_tailored_waza_for_pal(self, elements: list[str]) -> list[dict[str, Any]]:
        """Finds 3 tailored active skills (1 low CT, 1 mid CT, 1 high CT) for a Pal."""
        cursor = self.engine.conn.cursor()
        candidate_skills = []

        norm_elements = []
        for e in elements:
            if not e:
                continue
            e_str = str(e).strip()
            norm_elements.append(e_str)
            if e_str.lower() in ("ground", "earth"):
                norm_elements.extend(["Ground", "Earth"])
            elif e_str.lower() in ("grass", "leaf"):
                norm_elements.extend(["Grass", "Leaf"])
            elif e_str.lower() in ("electricity", "electric"):
                norm_elements.extend(["Electric", "Electricity"])
        norm_elements = list(dict.fromkeys(norm_elements))

        for elem in norm_elements:
            try:
                cursor.execute(
                    """
                    SELECT name, element, power, coalesce(cooldown_sec, 10) as ct
                    FROM active_skills
                    WHERE LOWER(element) = LOWER(?)
                    ORDER BY power ASC
                    """,
                    (elem,),
                )
                skills = cursor.fetchall()
                if skills:
                    candidate_skills.extend(skills)
            except Exception:
                try:
                    cursor.execute(
                        """
                        SELECT name, element, power, coalesce(cooldown, 10) as ct
                        FROM palworld_master.skills
                        WHERE LOWER(type) = 'active' AND LOWER(element) = LOWER(?)
                        ORDER BY power ASC
                        """,
                        (elem,),
                    )
                    skills = cursor.fetchall()
                    if skills:
                        candidate_skills.extend(skills)
                except Exception:
                    pass

        if not candidate_skills:
            return [
                {"name": "Power Shot", "element": "Neutral", "power": 35, "ct": "4s"},
                {"name": "Power Bomb", "element": "Neutral", "power": 70, "ct": "15s"},
                {"name": "Pal Blast", "element": "Neutral", "power": 150, "ct": "55s"},
            ]

        def _get_ct(item: Any) -> int:
            if isinstance(item, dict):
                return int(item.get("ct") or item.get("cooldown_sec") or item.get("cooldown") or item.get("cool_time") or 10)
            try:
                return int(item["ct"])
            except Exception:
                try:
                    return int(item["cooldown_sec"])
                except Exception:
                    return 10

        low_ct = next((s for s in candidate_skills if _get_ct(s) <= 7), candidate_skills[0])
        mid_ct = next((s for s in candidate_skills if 8 <= _get_ct(s) <= 25), candidate_skills[len(candidate_skills)//2])
        nuke_ct = next((s for s in reversed(candidate_skills) if _get_ct(s) >= 26), candidate_skills[-1])

        results = []
        seen = set()
        for s in [low_ct, mid_ct, nuke_ct]:
            s_name = s.get("name") if isinstance(s, dict) else s["name"]
            s_elem = s.get("element") if isinstance(s, dict) else s["element"]
            s_pwr = s.get("power") if isinstance(s, dict) else s["power"]
            if s_name not in seen:
                seen.add(s_name)
                results.append({
                    "name": s_name,
                    "element": s_elem,
                    "power": s_pwr,
                    "ct": f"{_get_ct(s)}s",
                })
        return results



