"""Base Work Demand & Food Analytics Engine for PalEngine.

Aggregates work suitabilities, facility work modes (automated vs player-initiated),
and estimates team food satiety & SAN decay rates.
"""

from typing import Any, Dict, List, Optional
from palengine.db.sqlite_engine import SQLiteEngine


class BaseOptimizer:
    """Calculates work demand and food/SAN metrics for base camps."""

    def __init__(self, db_engine: SQLiteEngine):
        self.db_engine = db_engine

    def audit_base_work_demand(self, base_camp_id: str) -> Dict[str, Any]:
        """Audits structures in a base camp and aggregates work suitability demands.
        
        Returns:
            Dict containing total_structures, demand_by_suitability, automated_demand,
            player_initiated_demand, and base_category.
        """
        structures = self.db_engine.get_base_camp_structures(base_camp_id)
        
        demand_by_suitability: Dict[str, Dict[str, Any]] = {}
        automated_demand: Dict[str, int] = {}
        player_initiated_demand: Dict[str, int] = {}
        total_structures = 0

        for struct in structures:
            struct_name = struct["structure_name"]
            count = struct["count"]
            total_structures += count

            for wt_info in struct.get("work_types", []):
                wt_name = wt_info["work_type"]
                is_auto = bool(wt_info["is_automated"])
                mod = wt_info.get("work_amount_modifier", 1.0) or 1.0

                if wt_name not in demand_by_suitability:
                    demand_by_suitability[wt_name] = {
                        "work_type": wt_name,
                        "facility_count": 0,
                        "workload_units": 0.0,
                        "is_automated": is_auto,
                    }

                demand_by_suitability[wt_name]["facility_count"] += count
                demand_by_suitability[wt_name]["workload_units"] += count * mod

                if is_auto:
                    automated_demand[wt_name] = automated_demand.get(wt_name, 0) + count
                else:
                    player_initiated_demand[wt_name] = player_initiated_demand.get(wt_name, 0) + count

        # Natural Terrain Resources Baseline:
        # Every base camp area contains natural map terrain resources (natural ore nodes, coal, stone, trees).
        # Ensure Mining, Lumbering, and Transporting demands exist so natural terrain resources are harvested.
        for natural_role in ["Mining", "Lumbering", "Transporting"]:
            if natural_role not in demand_by_suitability:
                demand_by_suitability[natural_role] = {
                    "work_type": natural_role,
                    "facility_count": 1,
                    "workload_units": 1.0,
                    "is_automated": True,
                }
                automated_demand[natural_role] = automated_demand.get(natural_role, 0) + 1



        # Determine Primary Base Category based on workload distribution
        base_category = "Balanced"
        agr_points = sum(automated_demand.get(k, 0) for k in ["Planting", "Watering", "Gathering", "Farming"])
        ext_points = sum(automated_demand.get(k, 0) for k in ["Mining", "Lumbering"])
        prod_points = sum(player_initiated_demand.get(k, 0) for k in ["Handcraft", "Kindling", "Medicine"])
        nrg_points = automated_demand.get("GeneratingElectricity", 0) + player_initiated_demand.get("GeneratingElectricity", 0)

        max_pts = max(agr_points, ext_points, prod_points, nrg_points, 0)
        if max_pts > 0:
            if max_pts == agr_points:
                base_category = "Agriculture"
            elif max_pts == ext_points:
                base_category = "Extraction"
            elif max_pts == prod_points:
                base_category = "Production"
            elif max_pts == nrg_points:
                base_category = "Energy"

        return {
            "base_camp_id": base_camp_id,
            "total_structures": total_structures,
            "demand_by_suitability": demand_by_suitability,
            "automated_demand": automated_demand,
            "player_initiated_demand": player_initiated_demand,
            "base_category": base_category,
        }

    def calculate_team_food_and_san(self, team_pals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates total hourly food satiety drain and SAN decay index for a team of Pals."""
        rates_data = self.db_engine.get_food_satiety_rates()
        satiety_map = {r["food_rating"]: r for r in rates_data}

        total_base_hunger = 0.0
        total_adjusted_hunger = 0.0
        total_san_decay_mult = 0.0
        nocturnal_count = 0

        for pal in team_pals:
            food_rating = pal.get("food_requirement") or 3
            food_rating = max(1, min(10, int(food_rating)))
            
            rate_info = satiety_map.get(food_rating, {
                "satiety_amount": food_rating * 15.0,
                "san_decay_multiplier": 1.0
            })

            base_satiety = rate_info["satiety_amount"]
            san_mult = rate_info["san_decay_multiplier"]

            # Passive modifiers
            passives = [p.lower() for p in pal.get("passives", [])]
            hunger_mod = 1.0
            san_mod = 1.0

            if "diet lover" in passives:
                hunger_mod -= 0.15
            if "glutton" in passives:
                hunger_mod += 0.15
            if "workaholic" in passives:
                san_mod -= 0.15
            if "positive thinker" in passives:
                san_mod -= 0.10
            if "destructive" in passives:
                san_mod += 0.15

            if pal.get("nocturnal"):
                nocturnal_count += 1

            total_base_hunger += base_satiety
            total_adjusted_hunger += base_satiety * max(0.2, hunger_mod)
            total_san_decay_mult += san_mult * max(0.2, san_mod)

        pal_count = len(team_pals)
        avg_san_mult = (total_san_decay_mult / pal_count) if pal_count > 0 else 1.0

        return {
            "team_size": pal_count,
            "nocturnal_pals_count": nocturnal_count,
            "total_hourly_satiety_drain": round(total_adjusted_hunger, 2),
            "base_satiety_drain": round(total_base_hunger, 2),
            "average_san_decay_multiplier": round(avg_san_mult, 3),
            "san_stability_status": "Excellent" if avg_san_mult <= 0.9 else ("Good" if avg_san_mult <= 1.1 else "Warning"),
        }
