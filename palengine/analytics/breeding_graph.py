# Palopedix Breeding Graph Optimizer & Pathfinding Engine
import math
from typing import Optional, Any
from palengine.db.utils import clean_species_name, normalize_passives, transform_icon_path

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
        all_pals = [dict(r) for r in pals_rows]

        combos_rows = self.engine.conn.execute("SELECT parent1, parent2, child FROM breeding_combos").fetchall()
        special_combos: dict[tuple[str, str], str] = {}
        for r in combos_rows:
            p1_l = r["parent1"].lower()
            p2_l = r["parent2"].lower()
            ch_name = r["child"]
            special_combos[(p1_l, p2_l)] = ch_name
            special_combos[(p2_l, p1_l)] = ch_name

        restricted_set = self.engine.get_restricted_breeding_species()
        candidate_pals = [p for p in all_pals if is_valid_standard_candidate(p, restricted_set)]
        candidate_pals.sort(key=lambda x: x["index_order"])

        def calc_standard_child(power1: int, power2: int) -> str:
            target_power = (power1 + power2 + 1) // 2
            best_pal = min(
                candidate_pals,
                key=lambda p: abs(p["breeding_power"] - target_power)
            )
            return best_pal["display_name"]

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
                elif p1_name.lower() not in restricted_set and p2_name.lower() not in restricted_set:
                    pow1 = all_pals[i]["breeding_power"]
                    pow2 = all_pals[j]["breeding_power"]
                    if pow1 is not None and pow2 is not None:
                        result_child = calc_standard_child(pow1, pow2)
                    else:
                        result_child = ""
                else:
                    result_child = ""

                if result_child.lower() == target_child_lower:
                    results.add((p1_name, p2_name))

        return sorted(list(results), key=lambda x: (x[0], x[1]))

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

        combos_rows = self.engine.conn.execute("SELECT parent1, parent2, child FROM breeding_combos").fetchall()
        special_combos: dict[tuple[str, str], str] = {}
        for r in combos_rows:
            p1_l = r["parent1"].lower()
            p2_l = r["parent2"].lower()
            ch_name = r["child"]
            special_combos[(p1_l, p2_l)] = ch_name
            special_combos[(p2_l, p1_l)] = ch_name

        restricted_set = self.engine.get_restricted_breeding_species()
        candidate_pals = [p for p in all_pals if is_valid_standard_candidate(p, restricted_set)]
        candidate_pals.sort(key=lambda x: x["index_order"])

        def calc_child_fast(p1_l: str, p2_l: str) -> str:
            if p1_l == p2_l:
                return cased_names.get(p1_l, p1_l)
            if (p1_l, p2_l) in special_combos:
                return special_combos[(p1_l, p2_l)]
            if p1_l not in restricted_set and p2_l not in restricted_set and p1_l in power_map and p2_l in power_map:
                pow1 = power_map[p1_l]
                pow2 = power_map[p2_l]
                target_pow = (pow1 + pow2 + 1) // 2
                best = min(candidate_pals, key=lambda p: abs(p["breeding_power"] - target_pow))
                return best["display_name"]
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
