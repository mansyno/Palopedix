"""Base Work Demand & Food Analytics Engine for PalEngine.

Aggregates work suitabilities, facility work modes (automated vs player-initiated),
structure urgency tiers, electric supply-demand balance, and estimates team food satiety & SAN decay rates.
"""

from typing import Any, Dict, List, Optional
from palengine.db.sqlite_engine import SQLiteEngine


STRUCTURE_URGENCY_MAP: Dict[str, str] = {
    # ── CONTINUOUS (24/7 automated work, vital uptime) ──
    "monsterfarm": "continuous",
    "breedfarm": "continuous",
    "ranch": "continuous",
    "berrygarden": "continuous",
    "tomatogarden": "continuous",
    "lettucegarden": "continuous",
    "wheatgarden": "continuous",
    "ancientfarmblock": "continuous",
    "coalpit": "continuous",
    "stonepit": "continuous",
    "copperpit": "continuous",
    "quartzpit": "continuous",
    "sulfurpit": "continuous",
    "skyislandorepit": "continuous",
    "stationdeforest": "continuous",
    "stationdeforest2": "continuous",
    "stationdeforest3": "continuous",
    "electricgenerator": "continuous",
    "electricgenerator2": "continuous",
    "electricgenerator3": "continuous",
    "electricgenerator_large": "continuous",
    "ancientelectricgenerator": "continuous",
    "oilpump": "continuous",

    # ── FREQUENT (Consumables: smelting, cooking, flour, crushing) ──
    "blastfurnace": "frequent",
    "blastfurnace2": "frequent",
    "blastfurnace3": "frequent",
    "blastfurnace4": "frequent",
    "blastfurnace5": "frequent",
    "blastfurnace4_old": "frequent",
    "furnace_electric": "frequent",
    "furnace_primitive": "frequent",
    "cookingstove": "frequent",
    "electrickitchen": "frequent",
    "cookingpot": "frequent",
    "cookingpot_electric": "frequent",
    "flourmill": "frequent",
    "medicinefactory_primitive": "frequent",
    "medicinefactory_electric": "frequent",
    "crusher": "frequent",
    "icecrusher": "frequent",
    "woodcrusher": "frequent",

    # ── BURST (Batch sphere crafting) ──
    "spherefactory_black_01": "burst",
    "spherefactory_black_02": "burst",
    "spherefactory_black_03": "burst",
    "spherefactory_black_04": "burst",
    "spherefactory_white_01": "burst",
    "spherefactory_white_02": "burst",
    "spherefactory_white_03": "burst",

    # ── OCCASIONAL (One-off weapons, tools, gear) ──
    "weaponfactory_dirty_01": "occasional",
    "weaponfactory_dirty_02": "occasional",
    "weaponfactory_dirty_03": "occasional",
    "weaponfactory_dirty_04": "occasional",
    "weaponfactory_clean_01": "occasional",
    "weaponfactory_clean_02": "occasional",
    "weaponfactory_clean_03": "occasional",
    "workbench": "occasional",
    "workbench_primitive": "occasional",
    "workbench_quality": "occasional",
    "workbench_skillcard": "occasional",
    "workbench_skillunlock": "occasional",
    "ancientworkbench": "occasional",
}

URGENCY_WEIGHTS: Dict[str, float] = {
    "continuous": 3.0,
    "frequent": 2.0,
    "burst": 1.0,
    "occasional": 0.5,
}

ELECTRIC_SUPPLIERS = {
    "electricgenerator",
    "electricgenerator2",
    "electricgenerator3",
    "electricgenerator_large",
    "ancientelectricgenerator",
}

ELECTRIC_CONSUMERS = {
    "oilpump",
    "furnace_electric",
    "electrickitchen",
    "medicinefactory_electric",
    "electriccooler",
    "refrigerator",
}


def get_structure_urgency(struct_name: str) -> str:
    clean = struct_name.lower().replace(" ", "").replace("_", "")
    for k, v in STRUCTURE_URGENCY_MAP.items():
        if k.replace("_", "") in clean or clean in k.replace("_", ""):
            return v
    return "occasional"


class BaseOptimizer:
    """Calculates work demand and food/SAN metrics for base camps."""

    def __init__(self, db_engine: SQLiteEngine):
        self.db_engine = db_engine

    def audit_base_work_demand(self, base_camp_id: str) -> Dict[str, Any]:
        """Audits structures in a base camp and aggregates work suitability demands.
        
        Returns:
            Dict containing total_structures, demand_by_suitability, automated_demand,
            player_initiated_demand, base_category, electric_deficit, and breeding_farm_count.
        """
        structures = self.db_engine.get_base_camp_structures(base_camp_id)
        
        demand_by_suitability: Dict[str, Dict[str, Any]] = {}
        automated_demand: Dict[str, int] = {}
        player_initiated_demand: Dict[str, int] = {}
        total_structures = 0

        # Role counts for classification
        breeding_count = 0
        ranching_count = 0
        agriculture_count = 0
        cooking_count = 0
        smelting_count = 0
        crafting_count = 0
        extraction_count = 0
        electric_supplier_count = 0
        electric_consumer_count = 0

        for struct in structures:
            struct_name = struct["structure_name"]
            count = struct["count"]
            s_lower = struct_name.lower().replace(" ", "").replace("_", "")

            # Ignore raw natural terrain resource nodes, environmental clutter, and drop items
            if s_lower.startswith("natural") or "damagable" in s_lower or "dropitem" in s_lower or s_lower in ("tree", "treenode", "rock"):
                continue

            total_structures += count

            # Classify specific structure types
            if "breed" in s_lower:
                breeding_count += count
            elif "ranch" in s_lower or "monsterfarm" in s_lower or "pasture" in s_lower:
                ranching_count += count

            if any(crop in s_lower for crop in ["garden", "farmblock", "berry", "tomato", "lettuce", "wheat", "onion"]):
                agriculture_count += count

            if any(cook in s_lower for cook in ["kitchen", "cooking", "stove", "pot", "flourmill"]):
                cooking_count += count

            if any(smelt in s_lower for smelt in ["furnace", "blastfurnace"]):
                smelting_count += count

            if any(craft in s_lower for craft in ["factory", "workbench", "assembly"]):
                crafting_count += count

            # Dedicated player-built mining / extraction facilities (e.g. Stonepit, OrePit, CopperPit, CoalPit, DeforestStation, Crusher)
            if any(ext in s_lower for ext in ["stonepit", "orepit", "copperpit", "coalpit", "sulfurpit", "quartzpit", "deforest", "crusher", "oilpump", "miningpit"]):
                extraction_count += count

            # Electric power check
            if any(sup.replace("_", "") in s_lower for sup in ELECTRIC_SUPPLIERS):
                electric_supplier_count += count

            if any(con.replace("_", "") in s_lower for con in ELECTRIC_CONSUMERS):
                electric_consumer_count += count

            urgency_class = get_structure_urgency(struct_name)
            urgency_wt = URGENCY_WEIGHTS.get(urgency_class, 1.0)

            for wt_info in struct.get("work_types", []):
                wt_name = wt_info["work_type"]
                # GeneratingElectricity can only be worked at power generators
                if wt_name in ["GeneratingElectricity", "Electricity"] and electric_supplier_count == 0:
                    continue
                is_auto = bool(wt_info["is_automated"])
                mod = wt_info.get("work_amount_modifier", 1.0) or 1.0

                if wt_name not in demand_by_suitability:
                    demand_by_suitability[wt_name] = {
                        "work_type": wt_name,
                        "facility_count": 0,
                        "workload_units": 0.0,
                        "is_automated": is_auto,
                        "urgency_weight": urgency_wt,
                    }

                demand_by_suitability[wt_name]["facility_count"] += count
                demand_by_suitability[wt_name]["workload_units"] += count * mod * urgency_wt
                demand_by_suitability[wt_name]["urgency_weight"] = max(
                    demand_by_suitability[wt_name]["urgency_weight"], urgency_wt
                )

                if is_auto:
                    automated_demand[wt_name] = automated_demand.get(wt_name, 0) + count
                else:
                    player_initiated_demand[wt_name] = player_initiated_demand.get(wt_name, 0) + count

        # Natural Node Extraction Outpost:
        # If extraction structures (e.g. Stonepit, OrePit) are NOT placed in the base,
        # but natural resource nodes exist in the base camp perimeter,
        # generate Mining and Transporting demand so workers are assigned to harvest the nodes!
        if extraction_count == 0:
            natural_mining_count = 0
            for s in structures:
                s_name_lower = s["structure_name"].lower().replace(" ", "").replace("_", "")
                if s_name_lower.startswith("natural") or "damagable" in s_name_lower:
                    if any(m in s_name_lower for m in ["ore", "coal", "quartz", "sulfur", "copper", "stone"]):
                        natural_mining_count += s.get("count", 1)

            if natural_mining_count > 0:
                demand_by_suitability["Mining"] = {
                    "work_type": "Mining",
                    "facility_count": natural_mining_count,
                    "workload_units": float(natural_mining_count * 2.0),
                    "is_automated": True,
                    "urgency_weight": 2.5,
                }
                automated_demand["Mining"] = automated_demand.get("Mining", 0) + natural_mining_count
                extraction_count += natural_mining_count

        # General Outpost Fallback:
        # If a base has zero demand (no production buildings placed yet, but has an active Palbox),
        # provide a baseline generalist demand (Mining, Lumbering, Handcraft, Transporting)
        # so the base is staffed with useful all-rounders instead of returning 0 recommendations.
        if not demand_by_suitability:
            for def_suit, def_urgency in [("Mining", 2.0), ("Handcraft", 1.8), ("Transporting", 1.5), ("Lumbering", 1.2)]:
                demand_by_suitability[def_suit] = {
                    "work_type": def_suit,
                    "facility_count": 1,
                    "workload_units": 2.0,
                    "is_automated": True,
                    "urgency_weight": def_urgency,
                }
                automated_demand[def_suit] = automated_demand.get(def_suit, 0) + 1

        # Logistics Transport Demand:
        # If the base has production, farming, mining, or ranching facilities, ensure Transporting is demanded
        has_production = any(wt in demand_by_suitability for wt in ["Planting", "Mining", "Lumbering", "Watering", "Farming", "MonsterFarm", "Kindling", "Handcraft", "OilExtraction"])
        if has_production and "Transporting" not in demand_by_suitability:
            demand_by_suitability["Transporting"] = {
                "work_type": "Transporting",
                "facility_count": 1,
                "workload_units": 1.5,
                "is_automated": True,
                "urgency_weight": 1.2,
            }
            automated_demand["Transporting"] = automated_demand.get("Transporting", 0) + 1

        # Electric Supply-Demand Balance:
        # Only demand GeneratingElectricity if electric power generators are built in the base camp
        electric_deficit = max(0, electric_consumer_count - electric_supplier_count) if electric_supplier_count > 0 else 0
        if electric_supplier_count > 0 and "GeneratingElectricity" not in demand_by_suitability:
            demand_by_suitability["GeneratingElectricity"] = {
                "work_type": "GeneratingElectricity",
                "facility_count": electric_supplier_count,
                "workload_units": 3.0 * max(1, electric_supplier_count),
                "is_automated": True,
                "urgency_weight": 3.0,
            }
            automated_demand["GeneratingElectricity"] = automated_demand.get("GeneratingElectricity", 0) + electric_supplier_count

        # Determine nuanced 7-category base specialization using priority hierarchy
        base_category = "Balanced"
        if breeding_count > 0 and (agriculture_count >= 2 or cooking_count >= 1 or ranching_count >= 1):
            base_category = "Breeding & Food"
        elif ranching_count >= 1 and breeding_count == 0 and agriculture_count <= 2:
            base_category = "Ranching"
        elif electric_supplier_count >= 2 or (electric_consumer_count >= 2 and electric_supplier_count >= 1):
            base_category = "Energy & Tech"
        elif agriculture_count >= 3:
            base_category = "Agriculture"
        elif extraction_count >= 2:
            base_category = "Extraction"
        elif (smelting_count + crafting_count) >= 2:
            base_category = "Production"
        else:
            # Fallback to workload points
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
                    base_category = "Energy & Tech"

        return {
            "base_camp_id": base_camp_id,
            "total_structures": total_structures,
            "demand_by_suitability": demand_by_suitability,
            "automated_demand": automated_demand,
            "player_initiated_demand": player_initiated_demand,
            "base_category": base_category,
            "electric_deficit": electric_deficit,
            "electric_supplier_count": electric_supplier_count,
            "electric_consumer_count": electric_consumer_count,
            "breeding_farm_count": breeding_count,
            "ranch_count": ranching_count,
            "ranching_count": ranching_count,
            "agriculture_count": agriculture_count,
            "extraction_count": extraction_count,
            "smelting_count": smelting_count,
            "crafting_count": crafting_count,
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
            passives = [
                str(p.get("name") or p.get("id") or "").lower() if isinstance(p, dict) else str(p).lower()
                for p in pal.get("passives", [])
            ]
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
