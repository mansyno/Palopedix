"""Palbox Cleaner & Roster Auditor Engine for Palopedix.

Deterministic evaluation and multi-factor ranking system designed to triage full Palboxes.
Safeguards investments (ranks, souls, IVs), preserves a living Paldex floor (at least 1 of each species),
prioritizes the clean 2+2 breeding synergy meta and clean singletons, deduplicates high-supply traits across
power brackets and genders, and categorizes every Pal into actionable recommendations:
- KEEP_CORE (Investment, Species Keeper, Max Combat/Worker)
- KEEP_BREEDING (Clean 2+2 Synergy, Clean Singletons, Blank Slates)
- CONDENSE (Sacrifice fodder for a designated keeper)
- BUTCHER_OR_SELL (Redundant, contaminated, or low-utility surplus)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from palengine.analytics.passive_role_scorer import (
    ATTACK_PASSIVES,
    DEFENSE_PASSIVES,
    MOVEMENT_PASSIVES,
    WORK_PASSIVES,
    _extract_passive_name,
)


# ==============================================================================
# Meta & Trait Tier Dictionaries
# ==============================================================================

# Exclusive / Legendary / Raid / Bounty passives (cannot roll on standard wild Pals)
EXCLUSIVE_LEGENDARY_PASSIVES: Set[str] = {
    "legend",
    "divine dragon",
    "lord of the underworld",
    "celestial emperor",
    "spirit emperor",
    "lord of lightning",
    "lord of the sea",
    "earth emperor",
    "flame emperor",
    "ice emperor",
    "siren of the void",
    "philanthropist",
    "demonic",
    "demon god",
    "immortality",
    "twin-edged holy blade",
    "sanctified meat shield",
    "god of destruction",
    "hermit sage",
    "dimensional leap",
    "world tree's bounty",
    "world tree seedbed",
    "babysitter",
    "lunker",
}

# Core Meta Passives (high-demand rollable staples for endgame builds)
CORE_META_PASSIVES: Set[str] = {
    "artisan",
    "work slave",
    "serious",
    "nocturnal",
    "musclehead",
    "ferocious",
    "burly body",
    "diamond body",
    "swift",
    "runner",
    "nimble",
    "serenity",
    "impatient",
    "lucky",
    "vanguard",
    "stronghold strategist",
    "infinite stamina",
    "fit as a fiddle",
    "eternal engine",
}

# Detrimental / Negative Passives that pollute breeding pools
DETRIMENTAL_PASSIVES: Set[str] = {
    "slacker",
    "downtrodden",
    "pacifist",
    "bottomless stomach",
    "brittle",
    "glutton",
    "destructive",
    "sadist",
    "coward",
    "clumsy",
    "distracted",
    "unstable",
    "dehydrated",
    "sloppy",
}

ALL_DESIRABLE_PASSIVES: Set[str] = (
    set(WORK_PASSIVES.keys())
    | set(ATTACK_PASSIVES.keys())
    | set(DEFENSE_PASSIVES.keys())
    | set(MOVEMENT_PASSIVES.keys())
    | EXCLUSIVE_LEGENDARY_PASSIVES
    | CORE_META_PASSIVES
) - DETRIMENTAL_PASSIVES


def get_passive_role_category(name: str) -> str:
    """Classifies a desirable passive into its primary role."""
    nl = name.lower()
    if nl in EXCLUSIVE_LEGENDARY_PASSIVES:
        if nl in {"philanthropist", "babysitter", "hermit sage", "world tree's bounty", "world tree seedbed"}:
            return "work"
        if nl in {"dimensional leap"}:
            return "movement"
        return "exclusive_combat"
    if nl in WORK_PASSIVES and WORK_PASSIVES[nl] > 10:
        return "work"
    if nl in ATTACK_PASSIVES and ATTACK_PASSIVES[nl] > 10:
        return "attack"
    if nl in DEFENSE_PASSIVES and DEFENSE_PASSIVES[nl] > 10:
        return "defense"
    if nl in MOVEMENT_PASSIVES and MOVEMENT_PASSIVES[nl] > 10:
        return "movement"
    if nl in {"vanguard", "stronghold strategist"}:
        return "player_buff"
    return "general"


def evaluate_synergy(p1: str, p2: str) -> Tuple[bool, str]:
    """Evaluates if two passives have clean synergistic role compatibility."""
    r1 = get_passive_role_category(p1)
    r2 = get_passive_role_category(p2)

    if r1 == "work" and r2 == "work":
        return True, "Work Speed Synergy (2+2 Base Worker)"
    if r1 in {"attack", "defense", "exclusive_combat"} and r2 in {"attack", "defense", "exclusive_combat"}:
        return True, "Combat Synergy (2+2 Battle)"
    if r1 == "movement" and r2 == "movement":
        return True, "Mount Speed Synergy (2+2 Runner)"
    if r1 == "player_buff" and r2 == "player_buff":
        return True, "Player Buffer Synergy (2+2 Stat Aura)"
    if (r1 in {"attack", "exclusive_combat"} and r2 == "movement") or (r2 in {"attack", "exclusive_combat"} and r1 == "movement"):
        return True, "Combat Mount Synergy (2+2 Fighter)"
    return False, "Dual Positive Traits"


# ==============================================================================
# Palbox Cleaner Engine
# ==============================================================================

class PalboxCleaner:
    """Evaluates and ranks Palbox instances to optimize space and guide cleanup."""

    def __init__(self, db_engine: Any):
        self.engine = db_engine
        self._power_map: Dict[str, int] = {}
        self._init_breeding_powers()

    def _init_breeding_powers(self) -> None:
        """Loads breeding power from pals master table for power-tier grouping."""
        try:
            rows = self.engine.conn.execute(
                "SELECT display_name, internal_name, breeding_power FROM pals"
            ).fetchall()
            for r in rows:
                bp = r["breeding_power"] if r["breeding_power"] is not None else 1500
                dn = (r["display_name"] or "").strip().lower()
                in_name = (r["internal_name"] or "").strip().lower()
                if dn:
                    self._power_map[dn] = bp
                if in_name:
                    self._power_map[in_name] = bp
        except Exception:
            pass

    def get_breeding_power_tier(self, species_name: str) -> str:
        """Categorizes breeding power into Low (<500), Mid (500-1000), or High (>1000)."""
        bp = self._power_map.get(species_name.strip().lower(), 1000)
        if bp < 500:
            return "low"
        elif bp <= 1000:
            return "mid"
        return "high"

    def analyze_palbox(self, instances: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Performs complete analysis and scoring on all Palbox instances."""
        if instances is None:
            all_instances = self.engine.query_instances({})
            # Filter strictly to palbox location
            palbox_instances = [i for i in all_instances if (i.get("location") or "palbox").lower() == "palbox"]
        else:
            palbox_instances = [i for i in instances if (i.get("location") or "palbox").lower() == "palbox"]

        if not palbox_instances:
            return {
                "total_evaluated": 0,
                "keep_core_count": 0,
                "keep_breeding_count": 0,
                "condense_fodder_count": 0,
                "butcher_sell_count": 0,
                "freeable_slots": 0,
                "species_count": 0,
                "condense_targets": [],
                "roster": [],
            }

        # 1. Group by species for living Paldex floor & condensation tracking
        species_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for inst in palbox_instances:
            sp = inst.get("display_name") or inst.get("species") or "Unknown"
            species_map[sp].append(inst)

        # 2. Extract and pre-score individual Pal instances
        scored_instances = []
        for inst in palbox_instances:
            scored = self._calculate_instance_raw_score(inst)
            scored_instances.append(scored)

        # 3. Determine primary species keepers (guarantees at least 1 of each caught species is kept)
        species_best_pal: Dict[str, Dict[str, Any]] = {}
        for sp, pals in species_map.items():
            # Sort instances of this species by raw score descending
            sp_scored = [s for s in scored_instances if (s["instance"].get("display_name") or s["instance"].get("species")) == sp]
            sp_scored.sort(key=lambda x: x["raw_score"], reverse=True)
            if sp_scored:
                best = sp_scored[0]
                best["is_species_keeper"] = True
                species_best_pal[sp] = best

        # 4. Trait Deduplication & Power Tier Allocation
        # Map trait carriers: passive -> power_tier -> gender -> list of instances
        trait_carriers: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        blank_slates: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

        # Synergy & High-Tier Breeding Stock Deduplication:
        # Group by: species -> trait_combo_key -> gender -> list of instances
        synergy_stock: Dict[str, Dict[Tuple[str, ...], Dict[str, List[Dict[str, Any]]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )

        for s in scored_instances:
            inst = s["instance"]
            sp = inst.get("display_name") or inst.get("species") or ""
            power_tier = self.get_breeding_power_tier(sp)
            gender = inst.get("gender") or "Unknown"
            passives = s["passive_names"]
            desirable = s["desirable_traits"]

            if len(passives) == 0:
                blank_slates[power_tier][gender].append(s)
            elif not s["has_negative"]:
                # Trait carriers (single or 2-passive clean bridges)
                if len(passives) <= 2:
                    for p in desirable:
                        trait_carriers[p][power_tier][gender].append(s)

                # Breeding synergy candidates (clean 2-passive synergy OR 3+ desirable traits without negatives)
                if s["is_clean_2_synergy"] or (len(desirable) >= 3 and len(passives) == len(desirable)):
                    trait_key = tuple(sorted(desirable))
                    synergy_stock[sp][trait_key][gender].append(s)

        # Sort carrier buckets by score and mark the top 1 per gender/tier as essential keepers
        for p, tiers in trait_carriers.items():
            for tier, genders in tiers.items():
                for gender, pals in genders.items():
                    pals.sort(key=lambda x: x["raw_score"], reverse=True)
                    if pals:
                        # Top carrier in this gender/tier bucket is marked
                        pals[0]["is_trait_keeper"] = True
                        pals[0]["retained_traits"].append(p)

        # Allocate top blank slates (1 Male, 1 Female per power tier)
        for tier, genders in blank_slates.items():
            for gender, pals in genders.items():
                pals.sort(key=lambda x: x["raw_score"], reverse=True)
                if pals:
                    pals[0]["is_blank_slate_keeper"] = True

        # Allocate synergy breeding stock (top 1 per gender & trait combo, deduplicated against core keeper)
        for sp, trait_combos in synergy_stock.items():
            for trait_key, genders in trait_combos.items():
                for gender, pals in genders.items():
                    pals.sort(key=lambda x: x["raw_score"], reverse=True)
                    # Check if one of these instances is already designated as species core keeper
                    has_species_keeper = any(p["is_species_keeper"] for p in pals)
                    if has_species_keeper:
                        # Core keeper already satisfies this gender & trait combo; any extras are duplicates!
                        continue
                    else:
                        # Top instance of this gender & trait combo is preserved for breeding
                        pals[0]["is_synergy_keeper"] = True

        # 5. Final Action Classification & Reason Assignment
        condense_targets_map: Dict[str, Dict[str, Any]] = {}
        for sp, keeper_scored in species_best_pal.items():
            k_inst = keeper_scored["instance"]
            curr_rank = k_inst.get("rank", 0) or 0
            if curr_rank < 4:
                condense_targets_map[sp] = {
                    "keeper_id": k_inst.get("instance_id"),
                    "species": sp,
                    "current_rank": curr_rank,
                    "target_rank": curr_rank + 1,
                    "fodder_available": 0,
                    "fodder_ids": [],
                }

        final_roster = []
        keep_core_count = 0
        keep_breeding_count = 0
        condense_fodder_count = 0
        butcher_sell_count = 0

        for s in scored_instances:
            inst = s["instance"]
            sp = inst.get("display_name") or inst.get("species") or "Unknown"
            rank = inst.get("rank", 0) or 0
            is_species_keeper = s["is_species_keeper"]
            is_synergy_keeper = s.get("is_synergy_keeper", False)
            is_trait_keeper = s["is_trait_keeper"]
            is_blank_keeper = s["is_blank_slate_keeper"]
            is_clean_2 = s["is_clean_2_synergy"]
            has_negative = s["has_negative"]
            souls_spent = s["souls_spent"]
            level = inst.get("level", 1) or 1
            iv_sum = s["iv_sum"]

            action = "butcher_sell"
            action_label = "Butcher / Sell"
            action_reason = "Redundant surplus with low breeding or combat utility"

            # Rule 1: High Investment or Primary Species Keeper -> KEEP_CORE
            if rank > 0:
                action = "keep_core"
                action_label = "Keep (Core)"
                action_reason = f"Investment Protected: Condensation Rank {rank} Star"
                keep_core_count += 1
            elif souls_spent > 0:
                action = "keep_core"
                action_label = "Keep (Core)"
                action_reason = f"Investment Protected: {souls_spent} Stat Souls Invested"
                keep_core_count += 1
            elif is_species_keeper:
                action = "keep_core"
                action_label = "Keep (Core)"
                action_reason = f"Designated Living Paldex Keeper for {sp}"
                keep_core_count += 1
            elif level >= 45 and not has_negative and iv_sum >= 240:
                action = "keep_core"
                action_label = "Keep (Core)"
                action_reason = f"High Level ({level}) & Strong IVs ({iv_sum}/300)"
                keep_core_count += 1

            # Rule 2: Clean Synergy / High-Tier Breeding Stock or Essential Trait Bridge -> KEEP_BREEDING
            elif is_synergy_keeper:
                t_count = len(s["desirable_traits"])
                if t_count >= 3:
                    action_reason = f"Elite Multi-Trait Breeding Stock ({t_count} Desirable Traits, {s['gender']})"
                else:
                    action_reason = f"Elite 2+2 Breeding Synergy: {s['synergy_label']} ({s['gender']})"
                action = "keep_breeding"
                action_label = "Keep (Breeding)"
                keep_breeding_count += 1
            elif is_trait_keeper:
                t_names = ", ".join(s["retained_traits"][:2])
                action = "keep_breeding"
                action_label = "Keep (Breeding)"
                action_reason = f"Designated {s['power_tier'].capitalize()}-Tier Trait Bridge ({t_names})"
                keep_breeding_count += 1
            elif is_blank_keeper:
                action = "keep_breeding"
                action_label = "Keep (Breeding)"
                action_reason = f"Clean Blank Slate (0 Passives, {s['gender']}, {s['power_tier'].capitalize()} Power)"
                keep_breeding_count += 1

            # Rule 3: Species has an eligible Condensation Keeper -> CONDENSE
            elif sp in condense_targets_map and not (rank > 0):
                target_info = condense_targets_map[sp]
                action = "condense"
                action_label = "Condense Fodder"
                if len(s["desirable_traits"]) >= 3 and not has_negative:
                    action_reason = f"Duplicate High-Tier Surplus - Condense Fodder for {sp} (Target: Rank {target_info['current_rank']} Star -> {target_info['target_rank']} Star)"
                elif is_clean_2:
                    action_reason = f"Duplicate Breeding Stock - Condense Fodder for {sp} (Target: Rank {target_info['current_rank']} Star -> {target_info['target_rank']} Star)"
                else:
                    action_reason = f"Condense Fodder for {sp} (Target: Rank {target_info['current_rank']} Star -> {target_info['target_rank']} Star)"
                target_info["fodder_available"] += 1
                target_info["fodder_ids"].append(inst.get("instance_id"))
                condense_fodder_count += 1

            # Rule 4: Otherwise -> BUTCHER / SELL
            else:
                if has_negative:
                    action_reason = f"Polluted by negative trait ({', '.join(s['negative_traits'])})"
                elif len(s["desirable_traits"]) >= 3:
                    action_reason = "Duplicate high-tier surplus beyond breeding and condensation needs"
                elif is_clean_2:
                    action_reason = "Duplicate breeding stock beyond breeding and condensation needs"
                elif len(s["passive_names"]) == 1 and not s["has_desirable"]:
                    action_reason = "Low-impact non-meta single passive"
                elif len(s["passive_names"]) >= 3:
                    action_reason = "Cluttered passive pool without high investment"
                else:
                    action_reason = "Surplus duplicate beyond breeding and condensation needs"
                butcher_sell_count += 1

            # Enrich instance for UI consumption
            enriched = dict(inst)
            enriched["audit_score"] = s["total_score"]
            enriched["audit_action"] = action
            enriched["audit_action_label"] = action_label
            enriched["audit_reason"] = action_reason
            enriched["is_species_keeper"] = is_species_keeper
            enriched["is_trait_keeper"] = is_trait_keeper
            enriched["is_clean_2_synergy"] = is_clean_2
            enriched["is_synergy_keeper"] = is_synergy_keeper
            enriched["power_tier"] = s["power_tier"]
            enriched["score_breakdown"] = s["breakdown"]

            final_roster.append(enriched)

        # Sort roster by action priority, then audit score descending
        action_order = {"keep_core": 0, "keep_breeding": 1, "condense": 2, "butcher_sell": 3}
        final_roster.sort(key=lambda x: (action_order.get(x["audit_action"], 4), -x["audit_score"]))

        # Filter condense targets to those with at least 1 fodder available
        active_condense_targets = [
            t for t in condense_targets_map.values() if t["fodder_available"] > 0
        ]
        active_condense_targets.sort(key=lambda x: x["fodder_available"], reverse=True)

        return {
            "total_evaluated": len(palbox_instances),
            "keep_core_count": keep_core_count,
            "keep_breeding_count": keep_breeding_count,
            "condense_fodder_count": condense_fodder_count,
            "butcher_sell_count": butcher_sell_count,
            "freeable_slots": condense_fodder_count + butcher_sell_count,
            "species_count": len(species_map),
            "condense_targets": active_condense_targets,
            "roster": final_roster,
        }

    def _calculate_instance_raw_score(self, inst: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates multi-factor score breakdown for a single Palbox Pal."""
        sp = inst.get("display_name") or inst.get("species") or ""
        power_tier = self.get_breeding_power_tier(sp)
        level = inst.get("level", 1) or 1
        rank = inst.get("rank", 0) or 0
        gender = inst.get("gender") or "Unknown"

        # 1. Investment Points
        rank_points = {0: 0, 1: 30000, 2: 60000, 3: 120000, 4: 300000}.get(rank, 0)

        # Souls spent
        soul_points = inst.get("soul_points") or {}
        souls_spent = 0
        if isinstance(soul_points, dict):
            souls_spent = sum(v for v in soul_points.values() if isinstance(v, (int, float)))
        soul_score = souls_spent * 1500

        # Level points
        level_score = level * 100

        # IVs
        ivs = inst.get("ivs") or {}
        iv_hp = ivs.get("hp", 0) or inst.get("iv_hp", 0) or 0
        iv_atk = ivs.get("melee", 0) or inst.get("iv_melee", 0) or 0
        iv_def = ivs.get("defense", 0) or inst.get("iv_defense", 0) or 0
        iv_sum = iv_hp + iv_atk + iv_def

        iv_score = iv_sum * 10
        if any(v == 100 for v in [iv_hp, iv_atk, iv_def]):
            iv_score += 5000
        if iv_sum >= 270:
            iv_score += 8000

        # 2. Passives Analysis
        passives_raw = inst.get("passives") or []
        passive_names = [_extract_passive_name(p) for p in passives_raw if p]
        negative_traits = [p for p in passive_names if p in DETRIMENTAL_PASSIVES]
        has_negative = len(negative_traits) > 0

        desirable_traits = [p for p in passive_names if p in ALL_DESIRABLE_PASSIVES]
        exclusive_traits = [p for p in passive_names if p in EXCLUSIVE_LEGENDARY_PASSIVES]
        has_desirable = len(desirable_traits) > 0

        passive_score = 0
        is_clean_2 = False
        synergy_label = ""

        # 1. Base value per passive (stacks across all passives)
        for p in passive_names:
            if p in EXCLUSIVE_LEGENDARY_PASSIVES:
                passive_score += 20000
            elif p in CORE_META_PASSIVES:
                passive_score += 10000
            elif p in ALL_DESIRABLE_PASSIVES:
                passive_score += 4000
            elif p in DETRIMENTAL_PASSIVES:
                passive_score -= 12000

        # 2. Build completion & Clean Synergy Bonuses
        if len(passive_names) == 0:
            passive_score += 4000  # Clean blank slate bonus
        elif not has_negative:
            if len(desirable_traits) == 4 and len(passive_names) == 4:
                passive_score += 30000  # God-roll 4-passive build completion bonus
            elif len(desirable_traits) == 3 and len(passive_names) == 3:
                passive_score += 18000  # Near god-roll 3-passive build completion bonus
            elif len(desirable_traits) == 2 and len(passive_names) == 2:
                is_synergistic, syn_desc = evaluate_synergy(desirable_traits[0], desirable_traits[1])
                is_clean_2 = True
                synergy_label = syn_desc
                passive_score += 10000 if is_synergistic else 6000

        total_score = rank_points + soul_score + level_score + iv_score + passive_score

        return {
            "instance": inst,
            "raw_score": total_score,
            "total_score": total_score,
            "power_tier": power_tier,
            "gender": gender,
            "passive_names": passive_names,
            "negative_traits": negative_traits,
            "has_negative": has_negative,
            "has_desirable": has_desirable,
            "desirable_traits": desirable_traits,
            "exclusive_traits": exclusive_traits,
            "is_clean_2_synergy": is_clean_2,
            "synergy_label": synergy_label,
            "is_species_keeper": False,
            "is_synergy_keeper": False,
            "is_trait_keeper": False,
            "is_blank_slate_keeper": False,
            "retained_traits": [],
            "souls_spent": souls_spent,
            "iv_sum": iv_sum,
            "breakdown": {
                "rank_points": rank_points,
                "soul_points": soul_score,
                "level_points": level_score,
                "iv_points": iv_score,
                "passive_points": passive_score,
            },
        }
