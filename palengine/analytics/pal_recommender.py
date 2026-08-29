"""Pal Recommendation Pathfinder for Base Camp Deployment in PalEngine.

Scores candidate owned Pals against active base camp work suitabilities, passive traits,
nocturnal uptime bonuses, category specialization focus, cake production pipelines,
electric supply-demand balance, and food/SAN drain balance.
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

CATEGORY_FOCUS_MAP: Dict[str, Dict[str, Any]] = {
    "Breeding & Food": {
        "primary": ["MonsterFarm", "Farming", "Planting", "Watering", "Gathering", "Kindling"],
        "primary_mult": 1.8,
        "secondary": ["Transporting", "Cooling"],
        "secondary_mult": 1.3,
    },
    "Ranching": {
        "primary": ["MonsterFarm", "Farming"],
        "primary_mult": 1.8,
        "secondary": ["Transporting", "Gathering"],
        "secondary_mult": 1.3,
    },
    "Agriculture": {
        "primary": ["Planting", "Watering", "Gathering"],
        "primary_mult": 1.8,
        "secondary": ["Transporting", "Kindling"],
        "secondary_mult": 1.3,
    },
    "Extraction": {
        "primary": ["Mining", "Lumbering"],
        "primary_mult": 1.8,
        "secondary": ["Transporting"],
        "secondary_mult": 1.5,
    },
    "Production": {
        "primary": ["Handcraft", "Kindling"],
        "primary_mult": 1.6,
        "secondary": ["Transporting", "Mining"],
        "secondary_mult": 1.3,
    },
    "Energy & Tech": {
        "primary": ["GeneratingElectricity", "Kindling"],
        "primary_mult": 1.8,
        "secondary": ["Mining", "Transporting"],
        "secondary_mult": 1.3,
    },
    "Balanced": {
        "primary": [],
        "primary_mult": 1.0,
        "secondary": ["Transporting"],
        "secondary_mult": 1.2,
    },
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
        self._load_database_categories()

    def _load_database_categories(self) -> None:
        """Dynamically loads partner categories and ranch producers directly from SQLite."""
        self.ranch_producers: set[str] = set()
        try:
            rows = self.db_engine.conn.execute(
                "SELECT LOWER(pal_internal_name) as p_name FROM pal_partner_skill_categories WHERE category_id = 'ranch_producer'"
            ).fetchall()
            self.ranch_producers = {r["p_name"] for r in rows if r["p_name"]}
        except Exception:
            pass

    def calculate_pal_base_score(
        self,
        pal: Dict[str, Any],
        base_demand: Dict[str, Any],
        base_category: str = "Balanced",
        base_audit: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Calculates nuanced suitability, role, passive, speed, nocturnal, and food utility score for a Pal."""
        norm_pal_suitabilities = {
            normalize_suitability(k): v
            for k, v in pal.get("suitabilities", {}).items()
        }

        # Calculate Work Speed Multiplier
        work_speed_mult = 1.0
        all_passives = [
            str(p.get("name") or p.get("id") or "").lower() if isinstance(p, dict) else str(p).lower()
            for p in pal.get("passives", [])
        ]

        if any(p in all_passives for p in ["artisan", "pal_passive_workspeed_up_3"]):
            work_speed_mult += 0.50
        if any(p in all_passives for p in ["work slave", "pal_passive_workspeed_up_2"]):
            work_speed_mult += 0.30
        if any(p in all_passives for p in ["lucky", "pal_passive_rare"]):
            work_speed_mult += 0.15
        if any(p in all_passives for p in ["serious", "pal_passive_workspeed_up_1"]):
            work_speed_mult += 0.20
        if any(p in all_passives for p in ["slacker", "pal_passive_workspeed_down_2"]):
            work_speed_mult -= 0.30
        if any(p in all_passives for p in ["clumsy", "pal_passive_workspeed_down_1"]):
            work_speed_mult -= 0.10

        work_speed_mult = max(0.2, work_speed_mult)

        # Base role focus configuration
        focus_config = CATEGORY_FOCUS_MAP.get(base_category, CATEGORY_FOCUS_MAP["Balanced"])
        primary_roles = focus_config.get("primary", [])
        primary_mult = focus_config.get("primary_mult", 1.0)
        secondary_roles = focus_config.get("secondary", [])
        secondary_mult = focus_config.get("secondary_mult", 1.0)

        total_suitability_score = 0.0
        matching_roles = []
        is_nocturnal = bool(pal.get("nocturnal"))

        for req_ws, demand_info in base_demand.items():
            norm_req = normalize_suitability(req_ws)
            level = norm_pal_suitabilities.get(norm_req, 0)

            if level > 0:
                is_auto = demand_info.get("is_automated", False)
                urgency_wt = demand_info.get("urgency_weight", 1.0)

                # Exponential tier scaling: Tier 4 is drastically better than Tier 1
                base_tier_score = (level ** 2.2) * 12.0
                role_score = base_tier_score * work_speed_mult

                # Specialization priority bonus
                clean_ws = norm_req.lower().replace(" ", "").replace("_", "")
                if any(pr.lower().replace(" ", "").replace("_", "") == clean_ws for pr in primary_roles):
                    role_score *= primary_mult
                elif any(sr.lower().replace(" ", "").replace("_", "") == clean_ws for sr in secondary_roles):
                    role_score *= secondary_mult

                # Urgency multiplier from structure demand
                if urgency_wt > 1.0:
                    role_score *= (1.0 + (urgency_wt - 1.0) * 0.2)

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

        # Electric Supply-Demand Deficit Urgency Bonus
        if base_audit:
            elec_deficit = base_audit.get("electric_deficit", 0)
            if elec_deficit > 0:
                elec_lvl = norm_pal_suitabilities.get("generating_electricity", 0)
                if elec_lvl > 0:
                    total_suitability_score += (elec_lvl ** 2) * 25.0 * elec_deficit

        # Database-Driven Ranch Specialist Bonus
        disp_clean = (pal.get("display_name") or "").lower().strip()
        species_clean = (pal.get("species") or "").lower().strip()
        if species_clean.startswith("boss_"):
            species_clean = species_clean[5:]
        
        pipeline_bonus = 0.0
        if base_category in ("Breeding & Food", "Ranching"):
            is_ranch_producer = (
                species_clean in self.ranch_producers
                or disp_clean in self.ranch_producers
                or norm_pal_suitabilities.get("farming", 0) > 0
                or norm_pal_suitabilities.get("monsterfarm", 0) > 0
            )
            if is_ranch_producer:
                farm_lvl = max(norm_pal_suitabilities.get("farming", 0), norm_pal_suitabilities.get("monsterfarm", 0), 1)
                pipeline_bonus += 80.0 + (farm_lvl * 20.0)
                # Extra synergy bonus if pal has Work Slave or Artisan
                if any(p in all_passives for p in ["artisan", "work slave"]):
                    pipeline_bonus += 25.0

        # Food & SAN penalties/bonuses
        food_req = pal.get("food_requirement") or 3
        food_penalty = food_req * 3.0
        
        bonus_points = pipeline_bonus
        if any(p in all_passives for p in ["diet lover", "pal_fullstomach_down_2"]):
            bonus_points += 15.0
        if any(p in all_passives for p in ["workaholic", "pal_san_down_2"]):
            bonus_points += 15.0
        if any(p in all_passives for p in ["positive thinker", "pal_san_down_1"]):
            bonus_points += 10.0

        level_bonus = (pal.get("level") or 1) * 0.5

        # If the Pal cannot perform any demanded work at this base, score is 0
        if not matching_roles:
            final_score = 0.0
        else:
            final_score = max(0.0, total_suitability_score + level_bonus + bonus_points - food_penalty)

        return {
            "instance_id": pal.get("instance_id"),
            "species": pal.get("species"),
            "display_name": pal.get("display_name") or pal.get("species"),
            "level": pal.get("level"),
            "gender": pal.get("gender"),
            "rank": pal.get("rank"),
            "ivs": pal.get("ivs", {}),
            "iv_hp": pal.get("iv_hp"),
            "iv_melee": pal.get("iv_melee"),
            "iv_shot": pal.get("iv_shot"),
            "iv_defense": pal.get("iv_defense"),
            "location": pal.get("location", "palbox"),
            "location_details": pal.get("location_details") or {"base_camp_name": pal.get("location_details_base_camp_name")},
            "location_details_base_camp_name": pal.get("location_details_base_camp_name"),
            "nocturnal": is_nocturnal,
            "food_requirement": food_req,
            "passives": pal.get("passives", []),
            "work_speed_mult": round(work_speed_mult, 2),
            "matching_roles": matching_roles,
            "total_score": round(final_score, 1),
            "icon_path": pal.get("icon_path"),
        }

    def _calculate_target_quotas(
        self,
        demand_map: Dict[str, Any],
        base_category: str = "Balanced",
        electric_deficit: int = 0,
        reserved_breeding: int = 0,
    ) -> Dict[str, int]:
        """Calculates target worker quota per suitability based on facility counts and category focus."""
        target_quotas: Dict[str, int] = {}
        focus_config = CATEGORY_FOCUS_MAP.get(base_category, CATEGORY_FOCUS_MAP["Balanced"])
        primary_roles = [r.lower().replace(" ", "").replace("_", "") for r in focus_config.get("primary", [])]

        for req_ws, info in demand_map.items():
            f_count = info.get("facility_count", 1)
            urgency_wt = info.get("urgency_weight", 1.0)
            clean_ws = req_ws.lower().replace(" ", "").replace("_", "")

            if req_ws in ["GeneratingElectricity", "Electricity"]:
                base_q = max(1, electric_deficit + 1 if electric_deficit > 0 else 1)
            elif req_ws in ["Planting", "Watering", "Gathering"]:
                base_q = max(2, min(5, f_count))
            elif req_ws in ["Mining", "Lumbering"]:
                base_q = max(2, min(5, f_count * 2))
            elif req_ws in ["Transporting", "Transport"]:
                base_q = max(2, min(4, f_count + 1))
            elif req_ws in ["MonsterFarm", "Farming"]:
                # Guaranteed ranch slots only if non-zero breeder selected or ranching active
                if reserved_breeding > 0 or base_category in ["Breeding & Food", "Ranching"]:
                    base_q = max(2, min(4, f_count * 2))
                else:
                    base_q = max(1, min(2, f_count))
            elif req_ws in ["Kindling", "EmitFlame"]:
                base_q = max(1, min(4, f_count))
            elif req_ws in ["Medicine", "MedicineProduction"]:
                base_q = max(1, min(2, f_count))
            elif req_ws in ["Handcraft"]:
                base_q = max(1, min(4, f_count))
            else:
                base_q = max(1, min(3, f_count))

            # Boost primary focus quota
            if clean_ws in primary_roles:
                base_q = max(base_q, int(base_q * 1.3))

            target_quotas[req_ws] = base_q
        return target_quotas

    def _evaluate_team_utility(
        self,
        base_id: str,
        team: List[Dict[str, Any]],
        base_demands: Dict[str, Dict[str, Any]],
        base_quotas: Dict[str, Dict[str, int]],
    ) -> float:
        """Evaluates total work efficiency and quota fulfillment utility for a base team."""
        demand_map = base_demands.get(base_id, {})
        quotas = base_quotas.get(base_id, {})
        role_counts: Dict[str, int] = {}
        total_utility = 0.0

        for pal in team:
            total_utility += pal.get("total_score", 0.0)
            for r in pal.get("matching_roles", []):
                wt = r["work_type"]
                curr_count = role_counts.get(wt, 0)
                target = quotas.get(wt, 2)
                if curr_count < target:
                    # High utility for filling understaffed required suitability
                    total_utility += r["role_score"] * 1.5
                else:
                    # Diminishing utility for excess workers on already satiated role
                    total_utility -= r["role_score"] * 0.35
                role_counts[wt] = curr_count + 1

        san_summary = self.optimizer.calculate_team_food_and_san(team)
        if san_summary.get("san_stability_status") == "Warning":
            total_utility -= 50.0

        return total_utility

    def recommend_all_bases(
        self,
        base_camps: Optional[List[Dict[str, Any]]] = None,
        max_team_sizes: Optional[Dict[str, int]] = None,
        reserved_breeding_slots: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Performs holistic global multi-base optimization across all active base camps.
        
        Uses maximum marginal utility allocation and inter-base pairwise swap optimization
        to distribute Pal instances where their global productivity is maximized.
        Guarantees zero duplicate Pal assignments across bases.
        """
        # Return cached recommendations if available and no custom size overrides
        if max_team_sizes is None and reserved_breeding_slots is None and base_camps is None and getattr(self.db_engine, "_cached_base_recommendations", None) is not None:
            return self.db_engine._cached_base_recommendations

        if base_camps is None:
            base_camps = self.db_engine.get_base_camps()

        if not base_camps:
            return {}

        owned_pals = self.db_engine.query_instances({})
        if not owned_pals:
            results = {}
            for bc in base_camps:
                bid = bc["base_camp_id"]
                audit = self.optimizer.audit_base_work_demand(bid)
                target_cap = max_team_sizes[bid] if (max_team_sizes and bid in max_team_sizes) else bc.get("max_pals", 20)
                if reserved_breeding_slots and bid in reserved_breeding_slots:
                    breeding_reserved = reserved_breeding_slots[bid]
                else:
                    breeding_reserved = 2 * audit.get("breeding_farm_count", 0) if audit.get("breeding_farm_count", 0) > 0 else 0
                effective_cap = max(1, target_cap - breeding_reserved)
                results[bid] = {
                    "base_camp_id": bid,
                    "base_name": bc.get("custom_name") or bc.get("name") or f"Base {bid[:8]}",
                    "base_category": audit["base_category"],
                    "max_capacity": target_cap,
                    "effective_capacity": effective_cap,
                    "reserved_breeding_slots": breeding_reserved,
                    "assigned_workers_count": bc.get("assigned_pals_count", 0),
                    "team_size": 0,
                    "recommended_team": [],
                    "demand_summary": audit["demand_by_suitability"],
                    "uncovered_suitabilities": list(audit["demand_by_suitability"].keys()),
                    "food_and_san_summary": self.optimizer.calculate_team_food_and_san([]),
                    "message": "No owned Pals found in save file Palbox.",
                }
            return results

        # 1. Audit demands, capacities, and breeding reservations for each base
        base_audits: Dict[str, Dict[str, Any]] = {}
        base_demands: Dict[str, Dict[str, Any]] = {}
        base_quotas: Dict[str, Dict[str, int]] = {}
        base_target_caps: Dict[str, int] = {}
        base_effective_caps: Dict[str, int] = {}
        base_breeding_reserved: Dict[str, int] = {}

        for bc in base_camps:
            bid = bc["base_camp_id"]
            audit = self.optimizer.audit_base_work_demand(bid)
            base_audits[bid] = audit
            base_demands[bid] = audit["demand_by_suitability"]
            
            if reserved_breeding_slots and bid in reserved_breeding_slots:
                breeding_reserved = reserved_breeding_slots[bid]
            else:
                # Default to 2 slots (1 breeding pair) when breeding infrastructure exists
                breeding_reserved = 2 if audit.get("breeding_farm_count", 0) > 0 else 0

            base_quotas[bid] = self._calculate_target_quotas(
                audit["demand_by_suitability"],
                base_category=audit["base_category"],
                electric_deficit=audit.get("electric_deficit", 0),
                reserved_breeding=breeding_reserved,
            )
            
            target_cap = max_team_sizes[bid] if (max_team_sizes and bid in max_team_sizes) else bc.get("max_pals", 20)
            effective_cap = max(1, target_cap - breeding_reserved)

            base_target_caps[bid] = target_cap
            base_breeding_reserved[bid] = breeding_reserved
            base_effective_caps[bid] = effective_cap

        # 2. Precalculate Pal scores for each base camp
        scored_matrix: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for pal in owned_pals:
            iid = str(pal.get("instance_id") or id(pal))
            scored_matrix[iid] = {}
            for bid in base_audits.keys():
                scored_matrix[iid][bid] = self.calculate_pal_base_score(
                    pal,
                    base_demands[bid],
                    base_category=base_audits[bid]["base_category"],
                    base_audit=base_audits[bid],
                )

        assigned_teams: Dict[str, List[Dict[str, Any]]] = {bid: [] for bid in base_audits.keys()}
        role_counts: Dict[str, Dict[str, int]] = {
            bid: {k: 0 for k in base_demands[bid].keys()} for bid in base_audits.keys()
        }
        assigned_instance_ids: set[str] = set()

        # 3. Phase 1: Critical Ranch Producers & Specialist Allocation
        # 3a. In Breeding & Food or Ranching bases, allocate distinct Ranch Producers from the database
        for bid, audit in base_audits.items():
            if audit["base_category"] in ("Breeding & Food", "Ranching"):
                ranch_cands = [
                    p for p in owned_pals
                    if str(p.get("instance_id") or id(p)) not in assigned_instance_ids
                    and (
                        (p.get("species") or "").lower().replace("boss_", "") in self.ranch_producers
                        or (p.get("display_name") or "").lower() in self.ranch_producers
                        or p.get("suitabilities", {}).get("farming", 0) > 0
                        or p.get("suitabilities", {}).get("monsterfarm", 0) > 0
                    )
                ]
                assigned_ranch_species: set[str] = set()
                ranch_cands.sort(
                    key=lambda p: scored_matrix[str(p.get("instance_id") or id(p))][bid]["total_score"],
                    reverse=True,
                )
                for cand in ranch_cands:
                    if len(assigned_teams[bid]) >= base_effective_caps[bid]:
                        break
                    cand_sp = (cand.get("species") or "").lower().replace("boss_", "")
                    if cand_sp not in assigned_ranch_species:
                        cand_iid = str(cand.get("instance_id") or id(cand))
                        cand_scored = scored_matrix[cand_iid][bid]
                        assigned_teams[bid].append(cand_scored)
                        for r in cand_scored.get("matching_roles", []):
                            role_counts[bid][r["work_type"]] = role_counts[bid].get(r["work_type"], 0) + 1
                        assigned_instance_ids.add(cand_iid)
                        assigned_ranch_species.add(cand_sp)

        # 3b. Critical Scarcity & Specialist Allocation
        for bid, demand_map in base_demands.items():
            for req_ws in demand_map.keys():
                norm_req = normalize_suitability(req_ws)
                qualified_candidates = [
                    p for p in owned_pals
                    if str(p.get("instance_id") or id(p)) not in assigned_instance_ids
                    and normalize_suitability(req_ws) in [normalize_suitability(k) for k in p.get("suitabilities", {}).keys()]
                ]
                if 0 < len(qualified_candidates) <= 2 and len(assigned_teams[bid]) < base_effective_caps[bid]:
                    best_cand = max(
                        qualified_candidates,
                        key=lambda p: scored_matrix[str(p.get("instance_id") or id(p))][bid]["total_score"]
                    )
                    cand_iid = str(best_cand.get("instance_id") or id(best_cand))
                    cand_scored = scored_matrix[cand_iid][bid]
                    assigned_teams[bid].append(cand_scored)
                    for r in cand_scored.get("matching_roles", []):
                        role_counts[bid][r["work_type"]] = role_counts[bid].get(r["work_type"], 0) + 1
                    assigned_instance_ids.add(cand_iid)

        # 4. Phase 2: Fast Analytical Global Maximum Marginal Gain Allocation
        unassigned_pals = [
            p for p in owned_pals if str(p.get("instance_id") or id(p)) not in assigned_instance_ids
        ]

        while unassigned_pals:
            open_bases = [bid for bid, cap in base_effective_caps.items() if len(assigned_teams[bid]) < cap]
            if not open_bases:
                break

            best_pair = None
            best_gain = -1e9

            for pal in unassigned_pals:
                iid = str(pal.get("instance_id") or id(pal))
                for bid in open_bases:
                    sp = scored_matrix[iid][bid]
                    gain = sp["total_score"]
                    for r in sp.get("matching_roles", []):
                        wt = r["work_type"]
                        c_cnt = role_counts[bid].get(wt, 0)
                        tgt = base_quotas[bid].get(wt, 2)
                        if c_cnt < tgt:
                            gain += r["role_score"] * 1.5
                        else:
                            gain -= r["role_score"] * 0.35

                    if gain > best_gain:
                        best_gain = gain
                        best_pair = (pal, bid, sp)

            if best_pair and best_gain > 0:
                pal_to_add, target_bid, scored_rep = best_pair
                assigned_teams[target_bid].append(scored_rep)
                for r in scored_rep.get("matching_roles", []):
                    role_counts[target_bid][r["work_type"]] = role_counts[target_bid].get(r["work_type"], 0) + 1
                iid_added = str(pal_to_add.get("instance_id") or id(pal_to_add))
                assigned_instance_ids.add(iid_added)
                unassigned_pals = [p for p in unassigned_pals if str(p.get("instance_id") or id(p)) != iid_added]
            else:
                # Fill remaining slots with highest base scorers that can perform at least 1 job
                for bid in open_bases:
                    while len(assigned_teams[bid]) < base_effective_caps[bid] and unassigned_pals:
                        valid_unassigned = [
                            p for p in unassigned_pals
                            if scored_matrix[str(p.get("instance_id") or id(p))][bid]["matching_roles"]
                            and scored_matrix[str(p.get("instance_id") or id(p))][bid]["total_score"] > 0
                        ]
                        if not valid_unassigned:
                            break
                        best_scorer = max(
                            valid_unassigned,
                            key=lambda p: scored_matrix[str(p.get("instance_id") or id(p))][bid]["total_score"]
                        )
                        s_iid = str(best_scorer.get("instance_id") or id(best_scorer))
                        s_rep = scored_matrix[s_iid][bid]
                        assigned_teams[bid].append(s_rep)
                        for r in s_rep.get("matching_roles", []):
                            role_counts[bid][r["work_type"]] = role_counts[bid].get(r["work_type"], 0) + 1
                        assigned_instance_ids.add(s_iid)
                        unassigned_pals = [p for p in unassigned_pals if str(p.get("instance_id") or id(p)) != s_iid]
                break

        # 5. Phase 3: Inter-Base Pairwise Swap Optimization (Local Search)
        base_id_list = list(base_audits.keys())
        for _ in range(25):
            improved = False
            for i in range(len(base_id_list)):
                for j in range(i + 1, len(base_id_list)):
                    bu, bv = base_id_list[i], base_id_list[j]
                    team_u = assigned_teams[bu]
                    team_v = assigned_teams[bv]

                    for idx_u, pal_u in enumerate(team_u):
                        iid_u = str(pal_u.get("instance_id"))
                        for idx_v, pal_v in enumerate(team_v):
                            iid_v = str(pal_v.get("instance_id"))

                            curr_score = (
                                self._evaluate_team_utility(bu, team_u, base_demands, base_quotas) +
                                self._evaluate_team_utility(bv, team_v, base_demands, base_quotas)
                            )

                            new_pal_u_for_v = scored_matrix[iid_u][bv]
                            new_pal_v_for_u = scored_matrix[iid_v][bu]

                            swapped_u = team_u[:idx_u] + team_u[idx_u + 1:] + [new_pal_v_for_u]
                            swapped_v = team_v[:idx_v] + team_v[idx_v + 1:] + [new_pal_u_for_v]

                            new_score = (
                                self._evaluate_team_utility(bu, swapped_u, base_demands, base_quotas) +
                                self._evaluate_team_utility(bv, swapped_v, base_demands, base_quotas)
                            )

                            if new_score - curr_score > 1.0:
                                assigned_teams[bu] = swapped_u
                                assigned_teams[bv] = swapped_v
                                team_u = swapped_u
                                team_v = swapped_v
                                improved = True
                                break
                        if improved:
                            break
                    if improved:
                        break
            if not improved:
                break

        # 6. Build final structured results per base camp
        final_results: Dict[str, Dict[str, Any]] = {}
        for bid, team in assigned_teams.items():
            audit = base_demands[bid]
            covered = set()
            for p in team:
                for r in p.get("matching_roles", []):
                    covered.add(r["work_type"])

            uncovered = [req_ws for req_ws in audit.keys() if req_ws not in covered]
            team.sort(key=lambda x: x.get("total_score", 0.0), reverse=True)
            food_san = self.optimizer.calculate_team_food_and_san(team)

            matching_bc = next((c for c in base_camps if c["base_camp_id"] == bid), {})
            b_name = matching_bc.get("custom_name") or matching_bc.get("name") or f"Base {bid[:8]}"

            final_results[bid] = {
                "base_camp_id": bid,
                "base_name": b_name,
                "base_category": base_audits[bid]["base_category"],
                "max_capacity": base_target_caps[bid],
                "effective_capacity": base_effective_caps[bid],
                "reserved_breeding_slots": base_breeding_reserved[bid],
                "assigned_workers_count": matching_bc.get("assigned_pals_count", 0),
                "team_size": len(team),
                "recommended_team": team,
                "demand_summary": audit,
                "uncovered_suitabilities": uncovered,
                "food_and_san_summary": food_san,
            }

        # Cache in db_engine if standard run
        if max_team_sizes is None:
            self.db_engine._cached_base_recommendations = final_results

        return final_results

    def recommend_pals_for_base(
        self,
        base_camp_id: str,
        max_team_size: Optional[int] = None,
        reserved_breeding: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generates optimal recommended Pal team for a given base camp using holistic multi-base optimization.
        
        Args:
            base_camp_id: Target base camp identifier.
            max_team_size: Optional max capacity override; defaults to base camp Palbox capacity.
            reserved_breeding: Optional custom reserved breeding slots override.
        """
        # If cached, return immediately
        if max_team_size is None and reserved_breeding is None and getattr(self.db_engine, "_cached_base_recommendations", None) is not None:
            cached = self.db_engine._cached_base_recommendations.get(base_camp_id)
            if cached:
                return cached

        camps = self.db_engine.get_base_camps()
        max_team_sizes = {base_camp_id: max_team_size} if max_team_size is not None else None
        reserved_breeding_slots = {base_camp_id: reserved_breeding} if reserved_breeding is not None else None
        all_recs = self.recommend_all_bases(
            camps,
            max_team_sizes=max_team_sizes,
            reserved_breeding_slots=reserved_breeding_slots,
        )
        
        if base_camp_id in all_recs:
            return all_recs[base_camp_id]

        # Fallback for single unknown base
        audit_res = self.optimizer.audit_base_work_demand(base_camp_id)
        target_cap = max_team_size or 20
        breeding_reserved = reserved_breeding if reserved_breeding is not None else (2 * audit_res.get("breeding_farm_count", 0))
        return {
            "base_camp_id": base_camp_id,
            "base_name": f"Base {base_camp_id[:8]}",
            "base_category": audit_res["base_category"],
            "max_capacity": target_cap,
            "effective_capacity": max(1, target_cap - breeding_reserved),
            "reserved_breeding_slots": breeding_reserved,
            "assigned_workers_count": 0,
            "team_size": 0,
            "recommended_team": [],
            "demand_summary": audit_res["demand_by_suitability"],
            "uncovered_suitabilities": list(audit_res["demand_by_suitability"].keys()),
            "food_and_san_summary": self.optimizer.calculate_team_food_and_san([]),
            "message": "Base camp not found.",
        }
