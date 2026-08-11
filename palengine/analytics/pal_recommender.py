"""Pal Recommendation Pathfinder for Base Camp Deployment in PalEngine.

Scores candidate owned Pals against active base camp work suitabilities, passive traits,
nocturnal uptime bonuses, and food/SAN drain balance.
"""

from typing import Any, Dict, List, Optional
from palengine.analytics.base_optimizer import BaseOptimizer
from palengine.db.sqlite_engine import SQLiteEngine


SUITABILITY_ALIAS_MAP = {
    "emitflame": "kindling",
    "kindling": "kindling",
    "watering": "watering",
    "seeding": "planting",
    "planting": "planting",
    "generateelectricity": "generating_electricity",
    "electricity": "generating_electricity",
    "generating_electricity": "generating_electricity",
    "generatingelectricity": "generating_electricity",
    "handcraft": "handiwork",
    "handiwork": "handiwork",
    "collection": "gathering",
    "gathering": "gathering",
    "deforest": "lumbering",
    "lumbering": "lumbering",
    "mining": "mining",
    "productmedicine": "medicine_production",
    "medicine": "medicine_production",
    "medicine_production": "medicine_production",
    "cool": "cooling",
    "cooling": "cooling",
    "transport": "transporting",
    "transporting": "transporting",
    "monsterfarm": "farming",
    "farming": "farming",
}


def normalize_suitability(name: str) -> str:
    if not name:
        return name
    clean = name.strip().lower().replace(" ", "").replace("_", "")
    return SUITABILITY_ALIAS_MAP.get(clean, name)


class PalRecommender:
    """Recommends optimal Pal team assignments for base camps."""

    def __init__(self, db_engine: SQLiteEngine):
        self.db_engine = db_engine
        self.optimizer = BaseOptimizer(db_engine)

    def calculate_pal_base_score(
        self,
        pal: Dict[str, Any],
        active_suitabilities: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Computes base suitability and deployment score for a single Pal instance."""
        pal_suitabilities = pal.get("suitabilities", {})
        norm_pal_suitabilities = {
            normalize_suitability(k): v for k, v in pal_suitabilities.items()
        }
        passives_display = [p.lower() for p in pal.get("passives", [])]
        raw_passives = [p.lower() for p in pal.get("raw_passives", [])]
        all_passives = set(passives_display + raw_passives)
        is_nocturnal = bool(pal.get("nocturnal"))

        # Base Work Speed Multiplier from Passives (checking display names & internal IDs)
        work_speed_mult = 1.0
        if any(p in all_passives for p in ["artisan", "craftspeed_up2"]):
            work_speed_mult += 0.50
        if any(p in all_passives for p in ["work slave", "pal_corporateslave"]):
            work_speed_mult += 0.30
        if any(p in all_passives for p in ["serious", "craftspeed_up1"]):
            work_speed_mult += 0.20
        if any(p in all_passives for p in ["conceited", "craftspeed_up0"]):
            work_speed_mult += 0.10
        if any(p in all_passives for p in ["slacker", "craftspeed_down2"]):
            work_speed_mult -= 0.30

        # Foreman & Player Buff Passives
        if any(p in all_passives for p in ["mine foreman", "trainermining_up1"]):
            work_speed_mult += 0.15
        if any(p in all_passives for p in ["logging foreman", "trainerlogging_up1"]):
            work_speed_mult += 0.15
        if any(p in all_passives for p in ["motivational leader", "trainerworkspeed_up_1"]):
            work_speed_mult += 0.15

        total_suitability_score = 0.0
        matching_roles: List[Dict[str, Any]] = []

        for req_ws, req_info in active_suitabilities.items():
            norm_req = normalize_suitability(req_ws)
            level = norm_pal_suitabilities.get(norm_req, 0)
            if level > 0:
                is_auto = req_info.get("is_automated", False)
                # Level squared scoring for high tier work suitability
                role_score = (level ** 2) * 20.0 * max(0.2, work_speed_mult)

                # Nocturnal bonus for continuous 24/7 automated work
                if is_auto and is_nocturnal:
                    role_score *= 1.35

                total_suitability_score += role_score
                matching_roles.append({
                    "work_type": req_ws,
                    "level": level,
                    "is_automated": is_auto,
                    "role_score": round(role_score, 1),
                })

        # Food & SAN penalties/bonuses
        food_req = pal.get("food_requirement") or 3
        food_penalty = food_req * 3.0
        
        bonus_points = 0.0
        if any(p in all_passives for p in ["diet lover", "pal_fullstomach_down_2"]):
            bonus_points += 15.0
        if any(p in all_passives for p in ["workaholic", "pal_san_down_2"]):
            bonus_points += 15.0
        if any(p in all_passives for p in ["positive thinker", "pal_san_down_1"]):
            bonus_points += 10.0

        level_bonus = (pal.get("level") or 1) * 0.5

        final_score = max(0.0, total_suitability_score + level_bonus + bonus_points - food_penalty)

        return {
            "instance_id": pal.get("instance_id"),
            "species": pal.get("species"),
            "display_name": pal.get("display_name") or pal.get("species"),
            "level": pal.get("level"),
            "nocturnal": is_nocturnal,
            "food_requirement": food_req,
            "passives": pal.get("passives", []),
            "work_speed_mult": round(work_speed_mult, 2),
            "matching_roles": matching_roles,
            "total_score": round(final_score, 1),
            "icon_path": pal.get("icon_path"),
        }

    def recommend_pals_for_base(
        self,
        base_camp_id: str,
        max_team_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generates optimal recommended Pal team for a given base camp.
        
        Args:
            base_camp_id: Target base camp identifier.
            max_team_size: Optional max capacity override; defaults to base camp Palbox capacity.
        """
        audit_res = self.optimizer.audit_base_work_demand(base_camp_id)
        demand_map = audit_res["demand_by_suitability"]

        # Determine base capacity
        if max_team_size is None:
            camps = self.db_engine.get_base_camps()
            target_camp = next((c for c in camps if c["base_camp_id"] == base_camp_id), None)
            max_team_size = target_camp["max_pals"] if target_camp else 15

        owned_pals = self.db_engine.get_owned_pals_with_suitabilities()
        if not owned_pals:
            return {
                "base_camp_id": base_camp_id,
                "base_category": audit_res["base_category"],
                "recommended_team": [],
                "uncovered_suitabilities": list(demand_map.keys()),
                "food_and_san_summary": self.optimizer.calculate_team_food_and_san([]),
                "message": "No owned Pals found in save file Palbox.",
            }

        # Score all owned Pals
        scored_pals = [
            self.calculate_pal_base_score(pal, demand_map)
            for pal in owned_pals
        ]
        if demand_map:
            scored_pals = [p for p in scored_pals if p["matching_roles"]]

        scored_pals.sort(key=lambda x: x["total_score"], reverse=True)

        selected_team: List[Dict[str, Any]] = []
        covered_suitabilities = set()
        role_counts: Dict[str, int] = {k: 0 for k in demand_map.keys()}

        # Calculate target worker quota per suitability based on facility counts
        target_quotas: Dict[str, int] = {}
        for req_ws, info in demand_map.items():
            f_count = info.get("facility_count", 1)
            if req_ws in ["GeneratingElectricity", "Medicine"]:
                target_quotas[req_ws] = 1
            elif req_ws in ["Planting", "Watering", "Gathering", "Transporting", "Mining"]:
                target_quotas[req_ws] = max(2, min(4, f_count * 2))
            else:
                target_quotas[req_ws] = max(1, min(3, f_count))

        def add_pal(pal: Dict[str, Any]) -> None:
            selected_team.append(pal)
            for r in pal["matching_roles"]:
                wt = r["work_type"]
                covered_suitabilities.add(wt)
                role_counts[wt] = role_counts.get(wt, 0) + 1

        # Pass 1: Ensure primary coverage for each required suitability
        for req_ws in demand_map.keys():
            if len(selected_team) >= max_team_size:
                break
            if role_counts.get(req_ws, 0) == 0:
                candidate = next(
                    (p for p in scored_pals if p not in selected_team and any(r["work_type"] == req_ws for r in p["matching_roles"])),
                    None
                )
                if candidate:
                    add_pal(candidate)

        # Pass 2: Fill target quotas for understaffed suitabilities
        for req_ws, quota in target_quotas.items():
            while role_counts.get(req_ws, 0) < quota and len(selected_team) < max_team_size:
                candidate = next(
                    (p for p in scored_pals if p not in selected_team and any(r["work_type"] == req_ws for r in p["matching_roles"])),
                    None
                )
                if candidate:
                    add_pal(candidate)
                else:
                    break

        # Pass 3: Fill remaining team capacity prioritizing understaffed roles or highest efficiency Pals
        while len(selected_team) < max_team_size:
            best_cand = None
            best_cand_score = -1.0

            for p in scored_pals:
                if p in selected_team:
                    continue
                
                dynamic_mult = 1.0
                unique_roles = len(p["matching_roles"])
                if unique_roles >= 3:
                    dynamic_mult += 0.25

                # Diminish score if all roles for this Pal are already at or above target quota
                if all(role_counts.get(r["work_type"], 0) >= target_quotas.get(r["work_type"], 2) for r in p["matching_roles"]):
                    dynamic_mult *= 0.40

                dyn_score = p["total_score"] * dynamic_mult
                if dyn_score > best_cand_score:
                    best_cand_score = dyn_score
                    best_cand = p

            if best_cand:
                add_pal(best_cand)
            else:
                break

        uncovered = [req_ws for req_ws in demand_map.keys() if req_ws not in covered_suitabilities]
        food_san_summary = self.optimizer.calculate_team_food_and_san(selected_team)

        return {
            "base_camp_id": base_camp_id,
            "base_category": audit_res["base_category"],
            "max_capacity": max_team_size,
            "team_size": len(selected_team),
            "recommended_team": selected_team,
            "demand_summary": audit_res["demand_by_suitability"],
            "uncovered_suitabilities": uncovered,
            "food_and_san_summary": food_san_summary,
        }
