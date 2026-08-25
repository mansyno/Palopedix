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
    # 1. Tower Bosses
    "zoe & grizzbolt": {
        "canonical_name": "Zoe & Grizzbolt",
        "location": "Rayne Syndicate Tower (Isolated Island: 112, -434)",
        "level": 10,
        "hp": 30550,
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
        "elements": ["Dark", "Neutral"],
        "weaknesses": ["Dragon", "Dark"],
        "dangerous_moves": ["Star Fall", "Lunar Beam", "Dark Blast"],
        "tactics": "Selyne has rapid laser sweeps. Bring Dragon/Dark tanks and stagger her with heavy artillery.",
    },

    # 2. Alpha Legendaries & Major Field Alphas
    "jetragon": {
        "canonical_name": "Jetragon (Alpha Legendary)",
        "location": "Mount Obsidian (-845, -450)",
        "level": 50,
        "hp": 11500,
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
                return profile
                
        # Keyword checks (e.g. "victor", "faleris", "grizzbolt")
        for key, profile in BOSS_REGISTRY.items():
            words = re.findall(r"\w+", key)
            if any(w in cleaned for w in words if len(w) > 3):
                return profile

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

            return {
                "canonical_name": f"Alpha {row['display_name'] or row['name']}",
                "location": "Palpagos Islands (Wild / Dungeon Encounter)",
                "level": 50,
                "hp": row["hp"] * 100 if row["hp"] else 10000,
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

    def recommend_party_for_boss(
        self,
        boss_query: str,
        save_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """Calculates 3 optimal 5-Pal party archetypes for the specified boss."""
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

        # ----------------------------------------------------------------------
        # Archetype 1: Pure Pal Elemental DPS (Direct Counters)
        # ----------------------------------------------------------------------
        counter_pals = []
        for p in enriched:
            e1 = p.get("element_1")
            e2 = p.get("element_2")
            is_counter = e1 in weaknesses or e2 in weaknesses
            
            # Compute score
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
            if "Vanguard" in passives: pass_score += 15
            if "Stronghold Strategist" in passives: pass_score += 15
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
            counter_pals.append(p)

        counter_pals.sort(key=lambda x: x["combat_score"], reverse=True)

        # Build 5-Pal Option A (Top Counter Combat Team)
        team_a = counter_pals[:5]

        # ----------------------------------------------------------------------
        # Archetype 2: Mounted Player-DPS Build (Infusion Mount + Gobfin Stack)
        # ----------------------------------------------------------------------
        # Find best mount converter matching boss weakness
        best_mount = None
        for p in counter_pals:
            disp_name = p.get("display_name") or p.get("species")
            if disp_name in MOUNT_CONVERTERS:
                mount_elem = MOUNT_CONVERTERS[disp_name]["element"]
                if mount_elem in weaknesses:
                    best_mount = p
                    break
        
        # If no weakness mount found, pick highest level mount
        if not best_mount:
            for p in counter_pals:
                disp_name = p.get("display_name") or p.get("species")
                if disp_name in MOUNT_CONVERTERS:
                    best_mount = p
                    break

        # If still none, fallback to top Pal
        if not best_mount and counter_pals:
            best_mount = counter_pals[0]

        # Find Gobfins & Gobfin Ignis
        gobbfin_pals = [
            p for p in enriched
            if "gobfin" in (p.get("display_name") or "").lower()
            and p.get("instance_id") != (best_mount.get("instance_id") if best_mount else None)
        ]
        gobbfin_pals.sort(key=lambda x: (x.get("rank", 0), x.get("level", 0)), reverse=True)

        # Find Vanguard / Stronghold pals if not enough Gobfins
        vanguard_pals = [
            p for p in enriched
            if any("vanguard" in (p_obj.get("name") if isinstance(p_obj, dict) else str(p_obj)).lower() for p_obj in p.get("passives", []))
            and p.get("instance_id") != (best_mount.get("instance_id") if best_mount else None)
            and p not in gobbfin_pals
        ]
        vanguard_pals.sort(key=lambda x: x.get("level", 0), reverse=True)

        team_b: list[dict[str, Any]] = [best_mount] if best_mount else []
        needed = 5 - len(team_b)
        team_b.extend(gobbfin_pals[:needed])
        if len(team_b) < 5:
            team_b.extend(vanguard_pals[: 5 - len(team_b)])
        if len(team_b) < 5:
            for p in counter_pals:
                if p not in team_b:
                    team_b.append(p)
                if len(team_b) == 5:
                    break

        # ----------------------------------------------------------------------
        # Archetype 3: Balanced Hybrid & Survival Team
        # ----------------------------------------------------------------------
        # Slot 1: Highest Level Boss Counter DPS
        # Slot 2: Highest Defense/HP Tank (for swapping aggro)
        # Slot 3: Vanguard / Player Attack Buffer
        # Slot 4: Stronghold / Defense Buffer or High Level Pal
        # Slot 5: Fast Stagger / Secondary Attacker
        team_c: list[dict[str, Any]] = []
        if team_a:
            team_c.append(team_a[0])  # Main DPS

        # High HP/Def Tank
        tanks = sorted(enriched, key=lambda x: (x.get("base_hp", 0) + x.get("base_def", 0), x.get("level", 0)), reverse=True)
        for t in tanks:
            if t not in team_c:
                team_c.append(t)
                break

        # Vanguard Buffer
        for v in vanguard_pals:
            if v not in team_c:
                team_c.append(v)
                break

        # Secondary DPS / Gobfin
        for g in gobbfin_pals:
            if g not in team_c:
                team_c.append(g)
                break

        # Fill remaining slots with next best combat pals
        for p in counter_pals:
            if p not in team_c:
                team_c.append(p)
            if len(team_c) == 5:
                break

        # ----------------------------------------------------------------------
        # Breeding Fallbacks (Tier 3)
        # ----------------------------------------------------------------------
        breeding_suggestions = []
        owned_species = list(set([p.get("display_name") or p.get("species") for p in enriched if p.get("display_name") or p.get("species")]))
        
        # Best counter target species for this boss weakness
        target_counter_candidates = []
        for name, sp in static_pals.items():
            if sp.get("element_1") in weaknesses or sp.get("element_2") in weaknesses:
                if (sp.get("attack_melee") or 0) >= 100:
                    target_counter_candidates.append(sp.get("display_name") or sp.get("name"))
        target_counter_candidates = list(dict.fromkeys(target_counter_candidates))[:5]

        for target in target_counter_candidates:
            # Check if player already has high level one
            has_high_lvl = any(p.get("level", 0) >= 40 and (p.get("display_name") == target or p.get("species") == target) for p in enriched)
            if not has_high_lvl:
                path = self.engine.find_breeding_path(owned_species, target)
                if path:
                    breeding_suggestions.append({
                        "target_pal": target,
                        "element": f"{static_pals.get(target.lower(), {}).get('element_1')}/{static_pals.get(target.lower(), {}).get('element_2') or ''}".rstrip('/'),
                        "path": path,
                        "warning": "[Level 1 Warning] Hatches at Level 1 (Requires EXP training / manuals before boss battle)",
                    })

                    if len(breeding_suggestions) >= 2:
                        break

        # Format output payload
        return {
            "boss_profile": boss,
            "team_a_pal_dps": [self._format_team_member(p, "Primary Elemental DPS / Tank") for p in team_a],
            "team_b_mounted_player_dps": [self._format_team_member(p, "Mounted Infusion / Player Buff") for p in team_b],
            "team_c_balanced_hybrid": [self._format_team_member(p, "Balanced DPS / Utility") for p in team_c],
            "recommended_waza": self._recommend_active_skills(weaknesses),
            "breeding_projects": breeding_suggestions,
            "tactics": boss.get("tactics", ""),
        }

    def _format_team_member(self, pal: dict[str, Any], role_hint: str) -> dict[str, Any]:
        passives = [p["name"] if isinstance(p, dict) else str(p) for p in pal.get("passives", [])]
        elem = f"{pal.get('element_1') or '?'}/{pal.get('element_2') or ''}".rstrip('/')
        gender = pal.get("gender") or "None"
        rank = pal.get("rank", 0)
        
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
        }


    def _recommend_active_skills(self, weaknesses: list[str]) -> list[dict[str, Any]]:
        """Finds recommended active skill movesets matching weakness elements."""
        cursor = self.engine.conn.cursor()
        results = []
        for elem in weaknesses:
            try:
                cursor.execute(
                    """
                    SELECT name, element, power, coalesce(cooldown_sec, cool_time, 10) as ct
                    FROM active_skills
                    WHERE element = ?
                    ORDER BY power ASC
                    """,
                    (elem,),
                )
                skills = cursor.fetchall()
            except Exception:
                try:
                    cursor.execute(
                        """
                        SELECT name, element, power, 10 as ct
                        FROM active_skills
                        WHERE element = ?
                        ORDER BY power ASC
                        """,
                        (elem,),
                    )
                    skills = cursor.fetchall()
                except Exception:
                    skills = []

            if skills:
                def _get_ct(item: Any) -> int:
                    if isinstance(item, dict):
                        return int(item.get("ct") or item.get("cooldown_sec") or item.get("cool_time") or 10)
                    try:
                        return int(item["ct"])
                    except Exception:
                        return 10

                # Pick 1 low cooldown (CT <= 7), 1 mid burst (CT 8-25), 1 nuke (CT >= 26)
                low_ct = next((s for s in skills if _get_ct(s) <= 7), skills[0])
                mid_ct = next((s for s in skills if 8 <= _get_ct(s) <= 25), skills[len(skills)//2])
                nuke_ct = next((s for s in reversed(skills) if _get_ct(s) >= 26), skills[-1])
                
                seen_names = set()
                for s in [low_ct, mid_ct, nuke_ct]:
                    s_name = s.get("name") if isinstance(s, dict) else s["name"]
                    s_elem = s.get("element") if isinstance(s, dict) else s["element"]
                    s_pwr = s.get("power") if isinstance(s, dict) else s["power"]
                    if s_name not in seen_names:
                        seen_names.add(s_name)
                        results.append({
                            "name": s_name,
                            "element": s_elem,
                            "power": s_pwr,
                            "ct": f"{_get_ct(s)}s",
                        })
        return results[:6]


