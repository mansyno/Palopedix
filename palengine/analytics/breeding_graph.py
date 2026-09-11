# Palopedix Breeding Graph Optimizer & Pathfinding Engine
import math
from typing import Optional, Any
from palengine.db.utils import clean_species_name, normalize_passives, transform_icon_path, is_playable_pal

def is_valid_standard_candidate(pal_dict: dict[str, Any], restricted_set: Optional[set[str]] = None) -> bool:
    """Helper to verify if Pal is eligible for mathematical breeding formula."""
    if restricted_set is None:
        restricted_set = set()
    d_name = pal_dict.get("display_name", "")
    i_name = pal_dict.get("internal_name", "")
    if d_name.lower() in restricted_set or i_name.lower() in restricted_set:
        return False
    if pal_dict.get("is_variant") == 1 or "boss_" in i_name.lower():
        return False
    return True

class BreedingGraphOptimizer:
    """Encapsulates breeding combination logic, graph traversal, and multi-generation pathfinding."""

    PAL_GENDER_RATIOS: dict[str, tuple[int, int]] = {
        "beegarde": (20, 80), "elizabee": (20, 80), "petallia": (20, 80),
        "lovander": (20, 80), "dazzi": (20, 80), "ribbuny": (20, 80),
        "flopie": (20, 80), "vixy": (20, 80), "cremis": (20, 80), "cinnamoth": (20, 80),
        "relaxaurus": (80, 20), "relaxaurus lux": (80, 20), "mozzarina": (80, 20),
        "eikthyrdeer": (80, 20), "eikthyrdeer terra": (80, 20), "grizzbolt": (80, 20),
        "warsect": (80, 20), "rayhound": (80, 20), "wumpo": (80, 20), "wumpo botan": (80, 20),
        "kingpaca": (90, 10), "kingpaca cryst": (90, 10), "lyleen noct": (0, 100),
    }

    def __init__(self, engine: Any):
        self.engine = engine

    def get_hatch_odds(self, child_species: str, required_gender: str) -> dict[str, str]:
        sp_l = child_species.strip().lower()
        m_pct, f_pct = self.PAL_GENDER_RATIOS.get(sp_l, (50, 50))
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

    def calculate_passive_score(
        self,
        pal_instance: dict[str, Any],
        target_skills: Optional[list[str]] = None,
        scoring_weights: Optional[dict[str, float]] = None
    ) -> tuple[int, list[str]]:
        """Calculate score based on passives matching target skills and generic tier values."""
        if not pal_instance:
            return 0, []
            
        passives_raw = pal_instance.get("passives", [])
        p_names = []
        for p in passives_raw:
            if isinstance(p, dict):
                p_names.append(p.get("name", ""))
            elif isinstance(p, str):
                p_names.append(p)

        matched_skills = []
        score = 0
        
        # Target skill match bonus (+50 points per match)
        if target_skills:
            for skill in target_skills:
                skill_clean = skill.strip().lower()
                for p in p_names:
                    if p.lower() == skill_clean:
                        score += 50
                        matched_skills.append(p)

        # Baseline tier score
        negatives = {"slacker", "downtrodden", "pacifist", "bottomless stomach", "brittle", "glutton", "destructive", "sadist", "coward", "clumsy", "distracted", "unstable", "dehydrated", "sloppy"}
        legends = {"legend", "celestial emperor", "lord of lightning", "divine dragon", "siren of the void", "eternal flame", "ice emperor", "flame emperor", "earth emperor", "spirit emperor", "emperor", "holy beast"}
        gold = {"artisan", "ferocious", "musclehead", "swift", "lucky", "work slave", "vanguard", "stronghold strategist", "burly body", "remarkable", "runner", "workaholic", "mine foreman", "logging foreman", "motivational leader", "serious"}

        for p in p_names:
            p_l = p.lower()
            if p_l in negatives:
                score -= 10
            elif p_l in legends:
                score += 15
            elif p_l in gold:
                score += 10
            else:
                score += 2

        # IV bonus (+0.1 per IV point)
        iv_hp = pal_instance.get("iv_hp") or 0
        iv_atk = pal_instance.get("iv_melee") or 0
        iv_def = pal_instance.get("iv_defense") or 0
        score += int((iv_hp + iv_atk + iv_def) * 0.1)

        # Condenser rank bonus (+5 per star)
        rank = pal_instance.get("rank") or 0
        score += rank * 5

        return score, matched_skills

    def score_pal_instance(
        self,
        pal_instance: dict[str, Any],
        target_skills: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Enrich a Pal instance with score and matched passives."""
        score, matched = self.calculate_passive_score(pal_instance, target_skills)
        instance_copy = dict(pal_instance)
        instance_copy["score"] = score
        instance_copy["matched_passives"] = matched
        return instance_copy

    def get_best_parent_instances(
        self,
        species: str,
        gender: Optional[str] = None,
        target_skills: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        """Find the single highest scoring instances of a species with optional gender filter."""
        filters = {"species": species}
        if gender:
            filters["gender"] = gender
        instances = self.engine.query_instances(filters)
        scored_instances = []
        for inst in instances:
            scored = self.score_pal_instance(inst, target_skills)
            scored_instances.append(scored)

        scored_instances.sort(key=lambda x: x.get("score", 0), reverse=True)
        return scored_instances

    def get_breeding_result(self, parent1: str, parent2: str) -> Optional[dict[str, Any]]:
        """Calculates breeding result child for two parent species."""
        p1_in = parent1.strip().lower()
        p2_in = parent2.strip().lower()

        p1_row = self.engine.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
            (p1_in, p1_in),
        ).fetchone() or self.engine.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) LIKE ? OR LOWER(internal_name) LIKE ?",
            (f"%{p1_in}%", f"%{p1_in}%"),
        ).fetchone()

        p2_row = self.engine.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
            (p2_in, p2_in),
        ).fetchone() or self.engine.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) LIKE ? OR LOWER(internal_name) LIKE ?",
            (f"%{p2_in}%", f"%{p2_in}%"),
        ).fetchone()

        if not p1_row or not p2_row:
            return None

        p1_names = {p1_in, p1_row["display_name"].lower(), p1_row["internal_name"].lower()}
        p2_names = {p2_in, p2_row["display_name"].lower(), p2_row["internal_name"].lower()}

        if p1_row["display_name"].lower() == p2_row["display_name"].lower():
            row = self.engine.conn.execute(
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
                row = self.engine.conn.execute(
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
            child_row = self.engine.conn.execute(
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

        restricted_set = self.engine.get_restricted_breeding_species()
        all_pals_rows = self.engine.conn.execute("SELECT * FROM pals WHERE is_variant = 0 ORDER BY index_order ASC").fetchall()
        candidate_pals = [dict(r) for r in all_pals_rows if is_valid_standard_candidate(dict(r), restricted_set)]
        if candidate_pals:
            best_pal = min(candidate_pals, key=lambda p: abs(p["breeding_power"] - target_power))
            res = dict(best_pal)
            res["icon_path"] = transform_icon_path(res.get("icon_path"))
            return res

        return None

    def get_offspring_for_parent(self, parent: str, pool: Optional[list[str]] = None) -> list[dict[str, Any]]:
        """Find all possible offspring a parent can produce when paired with pals in the pool."""
        all_pals = self.engine.query_pals({})
        parent_clean = clean_species_name(parent)

        if pool:
            partner_pals = [p for p in all_pals if p.get("display_name") in pool]
        else:
            partner_pals = all_pals

        offspring_map: dict[str, dict[str, Any]] = {}
        for partner in partner_pals:
            partner_name = partner.get("display_name")
            res = self.get_breeding_result(parent_clean, partner_name)
            if not res:
                continue
            child_name = res.get("display_name")
            if child_name not in offspring_map:
                offspring_map[child_name] = {
                    "display_name": child_name,
                    "paldex_number": res.get("paldex_number"),
                    "icon_path": res.get("icon_path"),
                    "breeding_power": res.get("breeding_power"),
                    "element_1": res.get("element_1"),
                    "element_2": res.get("element_2"),
                    "other_parents": [partner_name]
                }
            else:
                if partner_name not in offspring_map[child_name]["other_parents"]:
                    offspring_map[child_name]["other_parents"].append(partner_name)

        return sorted(list(offspring_map.values()), key=lambda x: x.get("paldex_number") or 999)

    def find_parents_for_child(self, child: str, pool: Optional[list[str]] = None) -> list[tuple[str, str]]:
        """Returns all breeding combinations (Parent 1, Parent 2) that yield target child, optionally filtered by available pool."""
        c = child.strip().lower()

        child_row = self.engine.conn.execute(
            "SELECT display_name FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
            (c, c),
        ).fetchone()
        if not child_row:
            child_row = self.engine.conn.execute(
                "SELECT display_name FROM pals WHERE LOWER(display_name) LIKE ? OR LOWER(internal_name) LIKE ?",
                (f"%{c}%", f"%{c}%"),
            ).fetchone()
            if not child_row:
                return []

        child_name = child_row["display_name"]
        target_child_lower = child_name.lower()

        pals_rows = self.engine.conn.execute(
            "SELECT display_name, internal_name, breeding_power, is_variant, index_order FROM pals"
        ).fetchall()
        all_pals = [dict(r) for r in pals_rows if is_playable_pal(dict(r))]

        name_map = {p["internal_name"].lower(): p["display_name"] for p in all_pals}
        name_map.update({p["display_name"].lower(): p["display_name"] for p in all_pals})

        combos_rows = self.engine.conn.execute("SELECT parent1, parent2, child FROM breeding_combos").fetchall()
        special_combos: dict[tuple[str, str], str] = {}
        for r in combos_rows:
            p1_l = name_map.get(r["parent1"].lower(), r["parent1"]).lower()
            p2_l = name_map.get(r["parent2"].lower(), r["parent2"]).lower()
            ch_name = name_map.get(r["child"].lower(), r["child"])
            special_combos[(p1_l, p2_l)] = ch_name
            special_combos[(p2_l, p1_l)] = ch_name

        restricted_set = self.engine.get_restricted_breeding_species()
        candidate_pals = [p for p in all_pals if is_valid_standard_candidate(p, restricted_set)]
        candidate_pals.sort(key=lambda x: x["index_order"])

        max_bp = max((p["breeding_power"] for p in all_pals if p.get("breeding_power") is not None), default=1500)
        max_pow = max_bp + 100
        power_to_child: list[str] = [""] * max_pow
        for tp in range(max_pow):
            best = min(candidate_pals, key=lambda p: abs(p["breeding_power"] - tp))
            power_to_child[tp] = best["display_name"]

        def calc_standard_child(power1: int, power2: int) -> str:
            target_power = (power1 + power2 + 1) // 2
            if target_power < max_pow:
                return power_to_child[target_power]
            return candidate_pals[0]["display_name"]

        pool_set = {p.strip().lower() for p in pool} if pool else None

        results = set()

        if not pool_set or child_name.lower() in pool_set:
            results.add((child_name, child_name))

        for i in range(len(all_pals)):
            for j in range(i, len(all_pals)):
                p1_name = all_pals[i]["display_name"]
                p2_name = all_pals[j]["display_name"]
                p1_l, p2_l = p1_name.lower(), p2_name.lower()

                if pool_set and (p1_l not in pool_set or p2_l not in pool_set):
                    continue

                if p1_l == p2_l:
                    result_child = p1_name
                elif (p1_l, p2_l) in special_combos:
                    result_child = special_combos[(p1_l, p2_l)]
                elif all_pals[i]["breeding_power"] is not None and all_pals[j]["breeding_power"] is not None:
                    pow1 = all_pals[i]["breeding_power"]
                    pow2 = all_pals[j]["breeding_power"]
                    result_child = calc_standard_child(pow1, pow2)
                else:
                    result_child = ""

                if result_child.lower() == target_child_lower:
                    p1_n, p2_n = p1_name, p2_name
                    if p1_n.lower() > p2_n.lower():
                        p1_n, p2_n = p2_n, p1_n
                    results.add((p1_n, p2_n))

        return sorted(list(results), key=lambda x: (x[0].lower(), x[1].lower()))

    def get_uncaught_breeding_opportunities(self, source: str = "caught") -> list[dict[str, Any]]:
        """Find breedable species not yet in the player's caught roster."""
        owned = set(self.engine.get_owned_pal_species())
        all_pals = self.engine.query_pals({})

        if source == "caught":
            breeding_pool = list(owned)
        else:
            breeding_pool = [p.get("display_name") for p in all_pals]

        uncaught_pals = [p for p in all_pals if p.get("display_name") not in owned]
        opportunities = []

        for pal in uncaught_pals:
            target_name = pal.get("display_name")
            pairs = self.find_parents_for_child(target_name, breeding_pool)
            if pairs:
                opportunities.append({
                    "species": target_name,
                    "paldex_number": pal.get("paldex_number"),
                    "icon_path": pal.get("icon_path"),
                    "element_1": pal.get("element_1"),
                    "element_2": pal.get("element_2"),
                    "possible_pairs_count": len(pairs),
                    "pairs": [{"parent1": pair[0], "parent2": pair[1]} for pair in pairs]
                })

        return sorted(opportunities, key=lambda x: x.get("paldex_number") or 999)

    def find_all_breeding_paths(
        self,
        owned_input: Any,
        target_species: str,
        target_skills: Optional[Any] = None,
    ) -> list[dict[str, Any]]:
        """Breadth-First Search (BFS) pathfinder that returns multiple distinct alternative breeding paths with instance skill scores & gender hatch odds."""
        target_skills_list: list[str] = []
        if isinstance(target_skills, str):
            target_skills_list = [s.strip() for s in target_skills.split(",") if s.strip()]
        elif isinstance(target_skills, list):
            target_skills_list = [str(s).strip() for s in target_skills if str(s).strip()]

        pals_rows = self.engine.conn.execute(
            "SELECT display_name, internal_name, breeding_power, is_variant, index_order FROM pals"
        ).fetchall()
        all_pals = [dict(r) for r in pals_rows]
        cased_names = {r["display_name"].lower(): r["display_name"] for r in all_pals}
        power_map = {r["display_name"].lower(): r["breeding_power"] for r in all_pals}

        name_map = {p["internal_name"].lower(): p["display_name"] for p in all_pals}
        name_map.update({p["display_name"].lower(): p["display_name"] for p in all_pals})

        combos_rows = self.engine.conn.execute("SELECT parent1, parent2, child FROM breeding_combos").fetchall()
        special_combos: dict[tuple[str, str], str] = {}
        for r in combos_rows:
            p1_l = name_map.get(r["parent1"].lower(), r["parent1"]).lower()
            p2_l = name_map.get(r["parent2"].lower(), r["parent2"]).lower()
            ch_name = name_map.get(r["child"].lower(), r["child"])
            special_combos[(p1_l, p2_l)] = ch_name
            special_combos[(p2_l, p1_l)] = ch_name

        restricted_set = self.engine.get_restricted_breeding_species()
        candidate_pals = [p for p in all_pals if is_valid_standard_candidate(p, restricted_set)]
        candidate_pals.sort(key=lambda x: x["index_order"])

        max_bp = max((p["breeding_power"] for p in all_pals if p.get("breeding_power") is not None), default=1500)
        max_pow = max_bp + 100
        power_to_child: list[str] = [""] * max_pow
        for tp in range(max_pow):
            best = min(candidate_pals, key=lambda p: abs(p["breeding_power"] - tp))
            power_to_child[tp] = best["display_name"]

        def calc_child_fast(p1_l: str, p2_l: str) -> str:
            if p1_l == p2_l:
                return cased_names.get(p1_l, p1_l)
            if (p1_l, p2_l) in special_combos:
                return special_combos[(p1_l, p2_l)]
            if p1_l in power_map and p2_l in power_map and power_map[p1_l] is not None and power_map[p2_l] is not None:
                pow1 = power_map[p1_l]
                pow2 = power_map[p2_l]
                target_pow = (pow1 + pow2 + 1) // 2
                if target_pow < max_pow:
                    return power_to_child[target_pow]
                return candidate_pals[0]["display_name"]
            return ""

        target_input = target_species.strip().lower()
        target = target_input
        if target not in cased_names:
            matched = next((k for k in cased_names if target_input in k), None)
            if matched:
                target = matched
            else:
                return []

        is_all_mode = False
        if isinstance(owned_input, str) and owned_input.strip().lower() in ("all", "global", "*"):
            is_all_mode = True
        elif isinstance(owned_input, list) and any(str(i).strip().lower() in ("all", "global", "*") for i in owned_input):
            is_all_mode = True

        if is_all_mode:
            all_pairs = self.find_parents_for_child(target)
            if not all_pairs:
                return []
            
            diff_pairs = [p for p in all_pairs if p[0].lower() != target.lower() or p[1].lower() != target.lower()]
            same_pairs = [p for p in all_pairs if p[0].lower() == target.lower() and p[1].lower() == target.lower()]
            selected_pairs = diff_pairs[:8] if diff_pairs else same_pairs[:1]
            
            paths = []
            for idx, (p1, p2) in enumerate(selected_pairs):
                is_same = (p1.lower() == target.lower() and p2.lower() == target.lower())
                hatch_info = self.get_hatch_odds(target, "Any")
                step_obj = {
                    "step": 1,
                    "parent1": p1,
                    "parent1_gender": "Male",
                    "parent2": p2,
                    "parent2_gender": "Female",
                    "child": cased_names.get(target, target),
                    "gender_note": hatch_info.get("gender_note", ""),
                    "hatch_chance_pct": hatch_info.get("hatch_chance_pct", "100%"),
                    "avg_eggs": hatch_info.get("avg_eggs", "~1 egg"),
                }
                title = f"Same-Species: {p1} + {p2}" if is_same else f"Direct Pair: {p1} + {p2}"
                paths.append({
                    "path_id": idx + 1,
                    "title": title,
                    "difficulty": "1 Generation (Direct Combination)",
                    "steps": [step_obj],
                    "total_quality_score": 0,
                })
            return paths

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
                            if child not in starting_owned or child == target:
                                new_breeds.append((child, parent1, g1_req, parent2, g2_req))

            for child, p1, g1_req, p2, g2_req in new_breeds:
                if p1 == p2 and child == p1 and child != target:
                    continue

                if child not in recipes_for_child:
                    recipes_for_child[child] = []
                    if child != target:
                        next_queue.append(child)

                pair_key = tuple(sorted([(p1, g1_req), (p2, g2_req)], key=lambda x: x[0]))
                existing_pairs = [tuple(sorted([(rp1, rg1), (rp2, rg2)], key=lambda x: x[0])) for rp1, rg1, rp2, rg2 in recipes_for_child[child]]
                if pair_key not in existing_pairs and len(recipes_for_child[child]) < 5:
                    recipes_for_child[child].append((p1, g1_req, p2, g2_req))

                if child not in reachable:
                    reachable.add(child)
                    reachable_genders[child] = {"male", "female"}

            queue = next_queue
            if target in recipes_for_child or not queue:
                break

        if target not in recipes_for_child:
            return []

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

                hatch_info = {}
                if species != target:
                    hatch_info = self.get_hatch_odds(child_cased, g1_req)

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
                        if len(all_sub_paths) >= 15:
                            break
                    if len(all_sub_paths) >= 15:
                        break
                if len(all_sub_paths) >= 15:
                    break

            return all_sub_paths

        raw_paths = build_paths(target, set())

        def get_step_sig(s: dict[str, Any]) -> str:
            pair = sorted([f"{s['parent1']}:{s['parent1_gender']}", f"{s['parent2']}:{s['parent2_gender']}"])
            return f"{pair[0]}+{pair[1]}->{s['child']}"

        unique_paths = []
        path_signatures = set()

        for p in raw_paths:
            if len(p) > 3:
                continue

            for s_step in p:
                p1_sp = s_step["parent1"]
                p1_g = s_step["parent1_gender"]
                p2_sp = s_step["parent2"]
                p2_g = s_step["parent2_gender"]

                best_p1_list = self.get_best_parent_instances(p1_sp, p1_g, target_skills_list)
                if best_p1_list:
                    b1 = best_p1_list[0]
                    s_step["parent1_instance_id"] = b1.get("instance_id")
                    s_step["parent1_level"] = b1.get("level")
                    s_step["parent1_rank"] = b1.get("rank", 0)
                    s_step["parent1_nickname"] = b1.get("nickname")
                    s_step["parent1_ivs"] = {
                        "hp": b1.get("iv_hp") if b1.get("iv_hp") is not None else b1.get("ivs", {}).get("hp"),
                        "melee": b1.get("iv_melee") if b1.get("iv_melee") is not None else b1.get("ivs", {}).get("melee"),
                        "shot": b1.get("iv_shot") if b1.get("iv_shot") is not None else b1.get("ivs", {}).get("shot"),
                        "defense": b1.get("iv_defense") if b1.get("iv_defense") is not None else b1.get("ivs", {}).get("defense"),
                    }
                    s_step["parent1_score"] = b1.get("score", 0)
                    s_step["parent1_passives"] = [
                        p_item.get("name") if isinstance(p_item, dict) else str(p_item)
                        for p_item in b1.get("passives", [])
                    ]
                    s_step["parent1_matched_passives"] = b1.get("matched_passives", [])
                    s_step["parent1_location"] = b1.get("location")
                    s_step["parent1_location_details"] = b1.get("location_details")
                    s_step["parent1_icon_path"] = b1.get("icon_path")

                best_p2_list = self.get_best_parent_instances(p2_sp, p2_g, target_skills_list)
                if best_p2_list:
                    b2 = best_p2_list[0]
                    s_step["parent2_instance_id"] = b2.get("instance_id")
                    s_step["parent2_level"] = b2.get("level")
                    s_step["parent2_rank"] = b2.get("rank", 0)
                    s_step["parent2_nickname"] = b2.get("nickname")
                    s_step["parent2_ivs"] = {
                        "hp": b2.get("iv_hp") if b2.get("iv_hp") is not None else b2.get("ivs", {}).get("hp"),
                        "melee": b2.get("iv_melee") if b2.get("iv_melee") is not None else b2.get("ivs", {}).get("melee"),
                        "shot": b2.get("iv_shot") if b2.get("iv_shot") is not None else b2.get("ivs", {}).get("shot"),
                        "defense": b2.get("iv_defense") if b2.get("iv_defense") is not None else b2.get("ivs", {}).get("defense"),
                    }
                    s_step["parent2_score"] = b2.get("score", 0)
                    s_step["parent2_passives"] = [
                        p_item.get("name") if isinstance(p_item, dict) else str(p_item)
                        for p_item in b2.get("passives", [])
                    ]
                    s_step["parent2_matched_passives"] = b2.get("matched_passives", [])
                    s_step["parent2_location"] = b2.get("location")
                    s_step["parent2_location_details"] = b2.get("location_details")
                    s_step["parent2_icon_path"] = b2.get("icon_path")

            sig = "||".join(get_step_sig(s) for s in p)
            if sig in path_signatures:
                continue

            path_signatures.add(sig)
            unique_paths.append(p)

        path_candidates = []
        for p in unique_paths:
            total_matched = sum(
                len(s.get("parent1_matched_passives", [])) + len(s.get("parent2_matched_passives", []))
                for s in p
            )
            total_score = sum(
                s.get("parent1_score", 0) + s.get("parent2_score", 0)
                for s in p
            )
            path_candidates.append({
                "path": p,
                "total_matched": total_matched,
                "total_score": total_score,
                "step_count": len(p),
            })

        path_candidates.sort(
            key=lambda x: (x["total_matched"], -x["step_count"], x["total_score"]),
            reverse=True,
        )

        formatted_paths = []
        for idx, item in enumerate(path_candidates[:5]):
            p = item["path"]
            total_steps = len(p)
            has_hard_gender = any(s.get("hatch_chance_pct") in ["10%", "20%"] for s in p)
            difficulty_label = "Challenging (Low Gender Hatch Rate)" if has_hard_gender else "Easy (High Gender Hatch Rate)"
            
            title = f"Path {idx + 1} ({total_steps} Step{'s' if total_steps > 1 else ''}{' - Recommended' if idx == 0 else ' - Alternative'})"
            formatted_paths.append({
                "path_id": idx + 1,
                "title": title,
                "difficulty": difficulty_label,
                "total_quality_score": round(item["total_score"], 1),
                "matched_skills_count": item["total_matched"],
                "steps": p
            })

        return formatted_paths

    def find_breeding_path(
        self,
        owned_input: Any,
        target_species: str,
        target_skills: Optional[Any] = None,
    ) -> list[dict[str, Any]]:
        """Breadth-First Search (BFS) pathfinder returning steps of the top recommended path."""
        all_paths = self.find_all_breeding_paths(owned_input, target_species, target_skills)
        if all_paths:
            return all_paths[0]["steps"]
        return []

    def find_passive_lineage_paths(
        self,
        target_species: str,
        target_passives: Any,
        max_depth: int = 5,
        max_results: int = 3,
    ) -> list[dict[str, Any]]:
        """Calculates multi-generation lineage breeding paths to produce target Pal carrying specified passives.

        Supports (1 + 1) trait convergence, (2 + 0) clean trait convergence, and single-trait propagation.
        Prioritizes shortest path (minimum generations) capped at max_depth, returns at most max_results distinct options.
        """
        # 1. Normalize target passives input
        passives_list: list[str] = []
        if isinstance(target_passives, str):
            passives_list = [p.strip() for p in target_passives.split(",") if p.strip()]
        elif isinstance(target_passives, (list, tuple, set)):
            passives_list = [str(p).strip() for p in target_passives if str(p).strip()]

        # Deduplicate preserving order
        dedup_passives: list[str] = []
        for p in passives_list:
            if p.lower() not in [x.lower() for x in dedup_passives]:
                dedup_passives.append(p)

        if not dedup_passives:
            return []

        # Focus on up to 2 target passives
        wanted_passives = dedup_passives[:2]
        cased_passives = {p.lower(): p for p in wanted_passives}
        wanted_lower = [p.lower() for p in wanted_passives]
        p1_wanted = wanted_lower[0]
        p2_wanted = wanted_lower[1] if len(wanted_lower) > 1 else None
        p1_display = cased_passives.get(p1_wanted, p1_wanted)
        p2_display = cased_passives.get(p2_wanted, p2_wanted) if p2_wanted else ""

        # 2. Setup breeding database cache
        pals_rows = self.engine.conn.execute(
            "SELECT display_name, internal_name, breeding_power, is_variant, index_order, icon_path FROM pals"
        ).fetchall()
        all_pals = [dict(r) for r in pals_rows]
        all_pals_by_name = {p["display_name"].lower(): p for p in all_pals}
        cased_names = {r["display_name"].lower(): r["display_name"] for r in all_pals}
        name_map = {p["internal_name"].lower(): p["display_name"] for p in all_pals}
        name_map.update({p["display_name"].lower(): p["display_name"] for p in all_pals})
        icon_map = {p["display_name"].lower(): transform_icon_path(p.get("icon_path")) for p in all_pals}
        power_map = {r["display_name"].lower(): r["breeding_power"] for r in all_pals}

        combos_rows = self.engine.conn.execute("SELECT parent1, parent2, child FROM breeding_combos").fetchall()
        special_combos: dict[tuple[str, str], str] = {}
        for r in combos_rows:
            p1_l = name_map.get(r["parent1"].lower(), r["parent1"]).lower()
            p2_l = name_map.get(r["parent2"].lower(), r["parent2"]).lower()
            ch_name = name_map.get(r["child"].lower(), r["child"])
            special_combos[(p1_l, p2_l)] = ch_name
            special_combos[(p2_l, p1_l)] = ch_name

        restricted_set = self.engine.get_restricted_breeding_species()
        candidate_pals = [p for p in all_pals if is_valid_standard_candidate(p, restricted_set)]
        candidate_pals.sort(key=lambda x: x["index_order"])

        max_bp = max((p["breeding_power"] for p in all_pals if p.get("breeding_power") is not None), default=1500)
        max_pow = max_bp + 100
        power_to_child: list[str] = [""] * max_pow
        for tp in range(max_pow):
            best = min(candidate_pals, key=lambda p: abs(p["breeding_power"] - tp))
            power_to_child[tp] = best["display_name"]

        def calc_child_fast(p1_l: str, p2_l: str) -> str:
            if p1_l == p2_l:
                return cased_names.get(p1_l, p1_l)
            if (p1_l, p2_l) in special_combos:
                return special_combos[(p1_l, p2_l)]
            if p1_l in power_map and p2_l in power_map and power_map[p1_l] is not None and power_map[p2_l] is not None:
                pow1 = power_map[p1_l]
                pow2 = power_map[p2_l]
                target_pow = (pow1 + pow2 + 1) // 2
                if target_pow < max_pow:
                    return power_to_child[target_pow]
                return candidate_pals[0]["display_name"]
            return ""

        # 3. Validate target species
        target_input = clean_species_name(target_species).strip().lower()
        target = target_input
        if target not in cased_names:
            matched = next((k for k in cased_names if target_input in k), None)
            if matched:
                target = matched
            else:
                return []
        target_display = cased_names[target]

        # 4. Scan player instances
        raw_instances = self.engine.query_instances({})
        active_instances = [i for i in raw_instances if i.get("location") in ("palbox", "party", "base")]

        p1_donors: list[dict[str, Any]] = []
        p2_donors: list[dict[str, Any]] = []
        both_donors: list[dict[str, Any]] = []
        owned_by_sp_gender: dict[tuple[str, str], list[dict[str, Any]]] = {}

        for inst in active_instances:
            sp_raw = inst.get("display_name") or inst.get("name") or ""
            if sp_raw.lower() not in cased_names:
                sp_raw = name_map.get(str(inst.get("species", "")).lower(), sp_raw)
            sp_l = sp_raw.lower()
            pal_rec = all_pals_by_name.get(sp_l, {"display_name": sp_raw})
            if sp_l not in cased_names or not is_playable_pal(pal_rec):
                continue


            gender = inst.get("gender")
            if not gender or gender not in ("Male", "Female"):
                continue

            raw_passives = inst.get("passives", [])
            p_names = []
            for p in raw_passives:
                if isinstance(p, dict):
                    p_name = p.get("name")
                    if p_name:
                        p_names.append(str(p_name).strip())
                elif isinstance(p, str) and p.strip():
                    p_names.append(p.strip())

            p_set = {p.lower() for p in p_names}
            has_p1 = p1_wanted in p_set
            has_p2 = (p2_wanted in p_set) if p2_wanted else False
            junk_passives = [p for p in p_names if p.lower() not in wanted_lower]

            item = {
                "instance_id": inst.get("instance_id"),
                "species": cased_names[sp_l],
                "species_lower": sp_l,
                "gender": gender,
                "level": inst.get("level", 1),
                "nickname": inst.get("nickname"),
                "location": inst.get("location"),
                "location_details": inst.get("location_details"),
                "icon_path": inst.get("icon_path") or icon_map.get(sp_l, ""),
                "passives": p_names,
                "target_passives": [p for p in p_names if p.lower() in wanted_lower],
                "junk_passives": junk_passives,
                "junk_count": len(junk_passives),
                "score": (inst.get("iv_hp") or 0) + (inst.get("iv_melee") or 0) + (inst.get("iv_defense") or 0) + (inst.get("level") or 1),
                "is_from_palbox": True,
                "is_donor": (has_p1 or has_p2),
            }

            key = (sp_l, gender)
            if key not in owned_by_sp_gender:
                owned_by_sp_gender[key] = []
            owned_by_sp_gender[key].append(item)

            if p2_wanted:
                if has_p1 and has_p2:
                    both_donors.append(item)
                elif has_p1:
                    p1_donors.append(item)
                elif has_p2:
                    p2_donors.append(item)
            else:
                if has_p1:
                    both_donors.append(item)
                    p1_donors.append(item)

        # Sort owned lists so cleanest instances come first
        for k in owned_by_sp_gender:
            owned_by_sp_gender[k].sort(key=lambda x: (x["junk_count"], -x["score"]))

        # Sort donors by fewest junk passives
        p1_donors.sort(key=lambda x: (x["junk_count"], -x["score"]))
        p2_donors.sort(key=lambda x: (x["junk_count"], -x["score"]))
        both_donors.sort(key=lambda x: (x["junk_count"], -x["score"]))

        if not p1_donors and not both_donors:
            return []
        if p2_wanted and not p2_donors and not both_donors:
            return []

        # Distinct partner species in Palbox
        owned_partner_species = sorted(list({k[0] for k in owned_by_sp_gender.keys()}))

        def get_best_partner(sp_l: str, required_gender: Optional[str] = None) -> Optional[dict[str, Any]]:
            if required_gender:
                candidates = owned_by_sp_gender.get((sp_l, required_gender), [])
                return candidates[0] if candidates else None
            m_candidates = owned_by_sp_gender.get((sp_l, "Male"), [])
            f_candidates = owned_by_sp_gender.get((sp_l, "Female"), [])
            all_c = m_candidates + f_candidates
            if not all_c:
                return None
            all_c.sort(key=lambda x: (x["junk_count"], -x["score"]))
            return all_c[0]

        # 5. BFS Trait Propagation Branch Builder
        # Build reachable intermediate species carrying a specific trait set
        def build_trait_branches(
            seed_donors: list[dict[str, Any]],
            carried_traits: list[str],
            max_branch_depth: int = 4,
        ) -> dict[str, list[dict[str, Any]]]:
            """Returns mapping of species_lower -> list of best branch routes reaching that species."""
            branches: dict[str, list[dict[str, Any]]] = {}

            # Depth 0: Donors directly
            # Deduplicate by species: keep top 2 cleanest donors per species
            donors_by_sp: dict[str, list[dict[str, Any]]] = {}
            for d in seed_donors:
                sp = d["species_lower"]
                if sp not in donors_by_sp:
                    donors_by_sp[sp] = []
                if len(donors_by_sp[sp]) < 2:
                    donors_by_sp[sp].append(d)

            current_level: list[dict[str, Any]] = []
            for sp, d_list in donors_by_sp.items():
                for d in d_list:
                    route = {
                        "species_lower": sp,
                        "species": d["species"],
                        "donor": d,
                        "steps": [],
                        "total_junk": d["junk_count"],
                        "depth": 0,
                    }
                    if sp not in branches:
                        branches[sp] = []
                    branches[sp].append(route)
                    current_level.append(route)

            for d_idx in range(max_branch_depth):
                next_level: list[dict[str, Any]] = []
                for route in current_level:
                    curr_sp = route["species_lower"]
                    is_gen0 = (route["depth"] == 0)
                    donor_inst = route["donor"]

                    for partner_sp in owned_partner_species:
                        if is_gen0:
                            # Must match opposite gender of donor
                            donor_gender = donor_inst["gender"]
                            req_partner_gender = "Female" if donor_gender == "Male" else "Male"
                            partner_inst = get_best_partner(partner_sp, req_partner_gender)
                            if not partner_inst:
                                continue
                            if partner_inst["instance_id"] == donor_inst["instance_id"]:
                                continue
                        else:
                            # Hatched intermediate: can choose whichever gender is needed
                            partner_inst = get_best_partner(partner_sp)
                            if not partner_inst:
                                continue

                        child_sp = calc_child_fast(curr_sp, partner_sp)
                        child_l = child_sp.lower() if child_sp else ""
                        child_rec = all_pals_by_name.get(child_l, {"display_name": child_sp})
                        if not child_sp or not is_playable_pal(child_rec):
                            continue
                        if child_l == curr_sp:
                            continue  # Ignore self-loop intermediate

                        # Calculate hatch odds for intermediate
                        req_gender_for_child = "Female" if partner_inst["gender"] == "Male" else "Male"
                        hatch_info = self.get_hatch_odds(child_sp, req_gender_for_child)

                        if is_gen0:
                            p1_dict = dict(donor_inst)
                        else:
                            prev_child = route["steps"][-1]["child"]
                            p1_dict = {
                                "species": prev_child["species"],
                                "species_lower": curr_sp,
                                "gender": "Female" if partner_inst["gender"] == "Male" else "Male",
                                "target_passives": carried_traits,
                                "is_from_palbox": False,
                                "is_donor": False,
                                "icon_path": icon_map.get(curr_sp, ""),
                            }

                        p2_dict = dict(partner_inst)

                        cased_carried = [cased_passives.get(t.lower(), t) for t in carried_traits]
                        carried_str = ", ".join(cased_carried)
                        step = {
                            "step_number": len(route["steps"]) + 1,
                            "description": f"Breed {p1_dict['species']} ({carried_str}) with {p2_dict['species']} to obtain intermediate {child_sp} ({carried_str})",
                            "parent1": p1_dict,
                            "parent2": p2_dict,
                            "child": {
                                "species": child_sp,
                                "species_lower": child_l,
                                "target_passives": cased_carried,
                                "required_gender": req_gender_for_child,
                                "hatch_odds": hatch_info,
                                "icon_path": icon_map.get(child_l, ""),
                                "is_target": False,
                            },
                        }

                        new_junk = route["total_junk"] + partner_inst["junk_count"]
                        new_route = {
                            "species_lower": child_l,
                            "species": child_sp,
                            "donor": donor_inst,
                            "steps": route["steps"] + [step],
                            "total_junk": new_junk,
                            "depth": route["depth"] + 1,
                        }

                        # Prune branches per species: keep at most 2 shortest / cleanest
                        if child_l not in branches:
                            branches[child_l] = []
                            branches[child_l].append(new_route)
                            next_level.append(new_route)
                        else:
                            existing = branches[child_l]
                            min_existing_depth = min(r["depth"] for r in existing)
                            if new_route["depth"] <= min_existing_depth and len(existing) < 2:
                                existing.append(new_route)
                                next_level.append(new_route)

                current_level = next_level
                if not current_level:
                    break

            return branches

        branches_p1 = build_trait_branches(p1_donors, [p1_wanted], max_branch_depth=max_depth - 1)
        branches_p2 = build_trait_branches(p2_donors, [p2_wanted], max_branch_depth=max_depth - 1) if p2_wanted else {}
        branches_both = build_trait_branches(both_donors, wanted_passives, max_branch_depth=max_depth - 1) if both_donors else {}

        def propagate_branch_genders(
            branch_steps: list[dict[str, Any]],
            final_required_gender: str,
        ) -> list[dict[str, Any]]:
            """Propagates required genders backwards from the final output through all intermediate branch steps."""
            if not branch_steps:
                return []

            aligned_steps = [dict(s) for s in branch_steps]
            needed_child_gender = final_required_gender

            for i in range(len(aligned_steps) - 1, -1, -1):
                curr_step = dict(aligned_steps[i])
                child = dict(curr_step["child"])
                child["required_gender"] = needed_child_gender
                child["hatch_odds"] = self.get_hatch_odds(child["species"], needed_child_gender)
                curr_step["child"] = child

                p2 = dict(curr_step["parent2"])
                p2_gender = p2.get("gender", "Female")

                p1_needed_gender = "Female" if p2_gender == "Male" else "Male"
                p1 = dict(curr_step["parent1"])
                p1["gender"] = p1_needed_gender
                curr_step["parent1"] = p1

                needed_child_gender = p1_needed_gender
                aligned_steps[i] = curr_step

            return aligned_steps

        candidate_roadmaps: list[dict[str, Any]] = []

        # ── Strategy 1: 1 + 1 Trait Convergence ──────────────────────────────
        if p2_wanted:
            for s1_l, routes1 in branches_p1.items():
                for s2_l, routes2 in branches_p2.items():
                    child_sp = calc_child_fast(s1_l, s2_l)
                    if child_sp.lower() != target:
                        continue

                    for r1 in routes1:
                        for r2 in routes2:
                            d1 = len(r1["steps"])
                            d2 = len(r2["steps"])
                            total_steps = d1 + d2 + 1
                            if total_steps > max_depth:
                                continue

                            # Check gender compatibility for direct Palbox donors
                            p1_donor = r1["donor"]
                            p2_donor = r2["donor"]
                            if d1 == 0 and d2 == 0:
                                if p1_donor["instance_id"] == p2_donor["instance_id"]:
                                    continue
                                if p1_donor["gender"] == p2_donor["gender"]:
                                    continue

                            # Determine final parent genders with strict opposite gender compatibility
                            if d1 == 0 and d2 == 0:
                                fin_p1 = dict(p1_donor)
                                fin_p2 = dict(p2_donor)
                            elif d1 == 0 and d2 > 0:
                                fin_p1 = dict(p1_donor)
                                fin_p2_gender = "Female" if fin_p1["gender"] == "Male" else "Male"
                                prev2 = r2["steps"][-1]["child"]
                                fin_p2 = {
                                    "species": prev2["species"],
                                    "species_lower": s2_l,
                                    "gender": fin_p2_gender,
                                    "target_passives": [p2_display],
                                    "is_from_palbox": False,
                                    "is_donor": False,
                                    "icon_path": icon_map.get(s2_l, ""),
                                }
                            elif d1 > 0 and d2 == 0:
                                fin_p2 = dict(p2_donor)
                                fin_p1_gender = "Female" if fin_p2["gender"] == "Male" else "Male"
                                prev1 = r1["steps"][-1]["child"]
                                fin_p1 = {
                                    "species": prev1["species"],
                                    "species_lower": s1_l,
                                    "gender": fin_p1_gender,
                                    "target_passives": [p1_display],
                                    "is_from_palbox": False,
                                    "is_donor": False,
                                    "icon_path": icon_map.get(s1_l, ""),
                                }
                            else:
                                prev1 = r1["steps"][-1]["child"]
                                prev2 = r2["steps"][-1]["child"]
                                fin_p1 = {
                                    "species": prev1["species"],
                                    "species_lower": s1_l,
                                    "gender": "Male",
                                    "target_passives": [p1_display],
                                    "is_from_palbox": False,
                                    "is_donor": False,
                                    "icon_path": icon_map.get(s1_l, ""),
                                }
                                fin_p2 = {
                                    "species": prev2["species"],
                                    "species_lower": s2_l,
                                    "gender": "Female",
                                    "target_passives": [p2_display],
                                    "is_from_palbox": False,
                                    "is_donor": False,
                                    "icon_path": icon_map.get(s2_l, ""),
                                }

                            # Propagate required genders backward through branches so hatched child requirements match 100%
                            aligned_r1_steps = propagate_branch_genders(r1["steps"], fin_p1["gender"]) if d1 > 0 else []
                            aligned_r2_steps = propagate_branch_genders(r2["steps"], fin_p2["gender"]) if d2 > 0 else []

                            combined_steps: list[dict[str, Any]] = []
                            step_counter = 1

                            # Branch 1 steps
                            for s in aligned_r1_steps:
                                s_copy = dict(s)
                                s_copy["step_number"] = step_counter
                                step_counter += 1
                                combined_steps.append(s_copy)

                            # Branch 2 steps
                            for s in aligned_r2_steps:
                                s_copy = dict(s)
                                s_copy["step_number"] = step_counter
                                step_counter += 1
                                combined_steps.append(s_copy)

                            final_step = {
                                "step_number": step_counter,
                                "description": f"Breed {fin_p1['species']} ({p1_display}) with {fin_p2['species']} ({p2_display}) to obtain target {target_display} ({', '.join(wanted_passives)})",
                                "parent1": fin_p1,
                                "parent2": fin_p2,
                                "child": {
                                    "species": target_display,
                                    "species_lower": target,
                                    "target_passives": wanted_passives,
                                    "required_gender": "Any",
                                    "hatch_odds": {"hatch_chance_pct": "100%", "avg_eggs": "~1 egg", "gender_note": "Either gender completes the goal"},
                                    "icon_path": icon_map.get(target, ""),
                                    "is_target": True,
                                },
                            }
                            combined_steps.append(final_step)

                            total_junk = r1["total_junk"] + r2["total_junk"]
                            purity = max(0, 100 - (total_junk * 10))

                            candidate_roadmaps.append({
                                "strategy": "1 + 1 Trait Convergence",
                                "total_steps": total_steps,
                                "total_junk": total_junk,
                                "purity_score": purity,
                                "steps": combined_steps,
                            })

        # ── Strategy 2: 2 + 0 Clean Convergence ──────────────────────────────
        if branches_both:
            for s_l, routes in branches_both.items():
                for partner_sp in owned_partner_species:
                    child_sp = calc_child_fast(s_l, partner_sp)
                    if child_sp.lower() != target:
                        continue

                    for r in routes:
                        d = len(r["steps"])
                        total_steps = d + 1
                        if total_steps > max_depth:
                            continue

                        # Clean partner from Palbox
                        if d == 0:
                            donor = r["donor"]
                            req_g = "Female" if donor["gender"] == "Male" else "Male"
                            partner_inst = get_best_partner(partner_sp, req_g)
                            if not partner_inst or partner_inst["instance_id"] == donor["instance_id"]:
                                continue
                            p1_fin = dict(donor)
                            aligned_steps = []
                        else:
                            partner_inst = get_best_partner(partner_sp)
                            if not partner_inst:
                                continue
                            p2_gender = partner_inst.get("gender", "Female")
                            req_p1_gender = "Female" if p2_gender == "Male" else "Male"
                            prev = r["steps"][-1]["child"]
                            p1_fin = {
                                "species": prev["species"],
                                "species_lower": s_l,
                                "gender": req_p1_gender,
                                "target_passives": wanted_passives,
                                "is_from_palbox": False,
                                "is_donor": False,
                                "icon_path": icon_map.get(s_l, ""),
                            }
                            aligned_steps = propagate_branch_genders(r["steps"], req_p1_gender)

                        p2_fin = dict(partner_inst)

                        combined_steps = [dict(s) for s in aligned_steps]
                        final_step = {
                            "step_number": len(combined_steps) + 1,
                            "description": f"Breed {p1_fin['species']} ({', '.join(wanted_passives)}) with clean {p2_fin['species']} to obtain target {target_display} ({', '.join(wanted_passives)})",
                            "parent1": p1_fin,
                            "parent2": p2_fin,
                            "child": {
                                "species": target_display,
                                "species_lower": target,
                                "target_passives": wanted_passives,
                                "required_gender": "Any",
                                "hatch_odds": {"hatch_chance_pct": "100%", "avg_eggs": "~1 egg", "gender_note": "Either gender completes the goal"},
                                "icon_path": icon_map.get(target, ""),
                                "is_target": True,
                            },
                        }
                        combined_steps.append(final_step)

                        total_junk = r["total_junk"] + partner_inst["junk_count"]
                        purity = max(0, 100 - (total_junk * 10))

                        candidate_roadmaps.append({
                            "strategy": "2 + 0 Clean Convergence",
                            "total_steps": total_steps,
                            "total_junk": total_junk,
                            "purity_score": purity,
                            "steps": combined_steps,
                        })

        # ── Strategy 3: Single Passive Convergence (if only 1 wanted) ─────────
        if not p2_wanted:
            for s_l, routes in branches_p1.items():
                for partner_sp in owned_partner_species:
                    child_sp = calc_child_fast(s_l, partner_sp)
                    if child_sp.lower() != target:
                        continue

                    for r in routes:
                        d = len(r["steps"])
                        total_steps = d + 1
                        if total_steps > max_depth:
                            continue

                        if d == 0:
                            donor = r["donor"]
                            req_g = "Female" if donor["gender"] == "Male" else "Male"
                            partner_inst = get_best_partner(partner_sp, req_g)
                            if not partner_inst or partner_inst["instance_id"] == donor["instance_id"]:
                                continue
                            p1_fin = dict(donor)
                            aligned_steps = []
                        else:
                            partner_inst = get_best_partner(partner_sp)
                            if not partner_inst:
                                continue
                            p2_gender = partner_inst.get("gender", "Female")
                            req_p1_gender = "Female" if p2_gender == "Male" else "Male"
                            prev = r["steps"][-1]["child"]
                            p1_fin = {
                                "species": prev["species"],
                                "species_lower": s_l,
                                "gender": req_p1_gender,
                                "target_passives": [p1_display],
                                "is_from_palbox": False,
                                "is_donor": False,
                                "icon_path": icon_map.get(s_l, ""),
                            }
                            aligned_steps = propagate_branch_genders(r["steps"], req_p1_gender)

                        p2_fin = dict(partner_inst)
                        combined_steps = [dict(s) for s in aligned_steps]
                        final_step = {
                            "step_number": len(combined_steps) + 1,
                            "description": f"Breed {p1_fin['species']} ({p1_display}) with clean {p2_fin['species']} to obtain target {target_display} ({p1_display})",
                            "parent1": p1_fin,
                            "parent2": p2_fin,
                            "child": {
                                "species": target_display,
                                "species_lower": target,
                                "target_passives": [p1_wanted],
                                "required_gender": "Any",
                                "hatch_odds": {"hatch_chance_pct": "100%", "avg_eggs": "~1 egg", "gender_note": "Either gender completes the goal"},
                                "icon_path": icon_map.get(target, ""),
                                "is_target": True,
                            },
                        }
                        combined_steps.append(final_step)

                        total_junk = r["total_junk"] + partner_inst["junk_count"]
                        purity = max(0, 100 - (total_junk * 10))

                        candidate_roadmaps.append({
                            "strategy": "Direct Trait Convergence",
                            "total_steps": total_steps,
                            "total_junk": total_junk,
                            "purity_score": purity,
                            "steps": combined_steps,
                        })

        # 6. Sort and Deduplicate
        # Minimum steps is first priority, then fewest junk passives
        candidate_roadmaps.sort(key=lambda x: (x["total_steps"], x["total_junk"], -x["purity_score"]))

        unique_roadmaps: list[dict[str, Any]] = []
        seen_signatures: set[str] = set()

        for rm in candidate_roadmaps:
            # Create a signature of parent species and child species across steps
            sig_parts = []
            for s in rm["steps"]:
                p1_sp = s["parent1"]["species"]
                p2_sp = s["parent2"]["species"]
                pair = tuple(sorted([p1_sp, p2_sp]))
                ch = s["child"]["species"]
                sig_parts.append(f"{pair[0]}+{pair[1]}->{ch}")
            sig = " | ".join(sig_parts)

            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)
            unique_roadmaps.append(rm)
            if len(unique_roadmaps) >= max_results:
                break

        # 7. Format Final Output Objects
        formatted_results: list[dict[str, Any]] = []
        for idx, rm in enumerate(unique_roadmaps):
            steps_cnt = rm["total_steps"]
            title = f"Option {idx + 1}: {steps_cnt} Generation{'s' if steps_cnt > 1 else ''}{' (Shortest Path)' if idx == 0 else ''}"

            formatted_results.append({
                "path_id": idx + 1,
                "title": title,
                "strategy": rm["strategy"],
                "total_steps": steps_cnt,
                "purity_score": rm["purity_score"],
                "total_junk_passives": rm["total_junk"],
                "target_species": target_display,
                "target_passives": wanted_passives,
                "steps": rm["steps"],
            })

        return formatted_results

