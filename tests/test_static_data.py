"""Schema validation tests for all static data JSON files."""

import json
import os
import pytest

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_json(filename: str) -> list | dict:
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        pytest.skip(f"Static JSON file '{filename}' not present in data directory")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- pals.json ----------


class TestPals:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.pals = load_json("pals.json")

    def test_is_list(self):
        assert isinstance(self.pals, list)

    def test_not_empty(self):
        assert len(self.pals) > 0, "pals.json must contain at least one Pal"

    def test_required_fields(self):
        required = {
            "internal_name", "display_name", "paldex_number",
            "element_types", "base_stats", "work_suitabilities",
            "breeding_power", "food_requirement", "is_variant",
        }
        for pal in self.pals:
            missing = required - set(pal.keys())
            assert not missing, (
                f"Pal '{pal.get('display_name', '?')}' missing fields: {missing}"
            )

    def test_internal_names_unique(self):
        names = [p["internal_name"] for p in self.pals]
        dupes = [n for n in names if names.count(n) > 1]
        assert not dupes, f"Duplicate internal_names: {set(dupes)}"

    def test_element_types_valid(self):
        valid_elements = {
            "Neutral", "Fire", "Water", "Electric", "Ice",
            "Ground", "Grass", "Dark", "Dragon",
        }
        for pal in self.pals:
            for elem in pal["element_types"]:
                assert elem in valid_elements, (
                    f"Pal '{pal['display_name']}' has invalid element: {elem}"
                )

    def test_base_stats_structure(self):
        stat_keys = {"hp", "attack_melee", "attack_ranged", "defense", "work_speed"}
        for pal in self.pals:
            missing = stat_keys - set(pal["base_stats"].keys())
            assert not missing, (
                f"Pal '{pal['display_name']}' base_stats missing: {missing}"
            )
            for key in stat_keys:
                val = pal["base_stats"][key]
                assert isinstance(val, int) and val > 0, (
                    f"Pal '{pal['display_name']}' stat '{key}' must be positive int, got {val}"
                )

    def test_breeding_power_positive(self):
        for pal in self.pals:
            assert pal["breeding_power"] > 0, (
                f"Pal '{pal['display_name']}' breeding_power must be positive"
            )

    def test_work_suitabilities_valid_types(self):
        valid_types = {
            "kindling", "watering", "planting", "generating_electricity",
            "handiwork", "gathering", "lumbering", "mining",
            "medicine_production", "cooling", "transporting", "farming",
        }
        for pal in self.pals:
            for work_type in pal["work_suitabilities"]:
                assert work_type in valid_types, (
                    f"Pal '{pal['display_name']}' has invalid work type: {work_type}"
                )

    def test_work_suitability_levels(self):
        for pal in self.pals:
            for work_type, level in pal["work_suitabilities"].items():
                assert isinstance(level, int) and 1 <= level <= 10, (
                    f"Pal '{pal['display_name']}' work '{work_type}' level must be 1-5, got {level}"
                )


# ---------- passive_skills.json ----------


class TestPassiveSkills:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.skills = load_json("passive_skills.json")

    def test_is_list(self):
        assert isinstance(self.skills, list)

    def test_not_empty(self):
        assert len(self.skills) > 0

    def test_required_fields(self):
        required = {"id", "name", "rank", "effects", "description"}
        for skill in self.skills:
            missing = required - set(skill.keys())
            assert not missing, (
                f"Passive skill '{skill.get('name', '?')}' missing: {missing}"
            )

    def test_ids_unique(self):
        ids = [s["id"] for s in self.skills]
        dupes = [i for i in ids if ids.count(i) > 1]
        assert not dupes, f"Duplicate passive skill ids: {set(dupes)}"

    def test_rank_range(self):
        for skill in self.skills:
            assert -3 <= skill["rank"] <= 4, (
                f"Skill '{skill['name']}' rank {skill['rank']} out of range [-3, 4]"
            )

    def test_effects_structure(self):
        for skill in self.skills:
            assert isinstance(skill["effects"], list), (
                f"Skill '{skill['name']}' effects must be a list"
            )
            for effect in skill["effects"]:
                assert "stat" in effect and "modifier_pct" in effect, (
                    f"Skill '{skill['name']}' effect missing stat/modifier_pct"
                )


# ---------- active_skills.json ----------


class TestActiveSkills:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.skills = load_json("active_skills.json")

    def test_is_list(self):
        assert isinstance(self.skills, list)

    def test_required_fields(self):
        required = {"id", "name", "element", "power", "cooldown_sec"}
        for skill in self.skills:
            missing = required - set(skill.keys())
            assert not missing, (
                f"Active skill '{skill.get('name', '?')}' missing: {missing}"
            )

    def test_ids_unique(self):
        ids = [s["id"] for s in self.skills]
        dupes = [i for i in ids if ids.count(i) > 1]
        assert not dupes, f"Duplicate active skill ids: {set(dupes)}"


# ---------- partner_skills.json ----------


class TestPartnerSkills:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.skills = load_json("partner_skills.json")
        self.pals = load_json("pals.json")

    def test_is_list(self):
        assert isinstance(self.skills, list)

    def test_required_fields(self):
        required = {"id", "name", "pal_internal_name", "description"}
        for skill in self.skills:
            missing = required - set(skill.keys())
            assert not missing, (
                f"Partner skill '{skill.get('name', '?')}' missing: {missing}"
            )

    def test_ids_unique(self):
        ids = [s["id"] for s in self.skills]
        dupes = [i for i in ids if ids.count(i) > 1]
        assert not dupes, f"Duplicate partner skill ids: {set(dupes)}"


# ---------- work_suitabilities.json ----------


class TestWorkSuitabilities:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.types = load_json("work_suitabilities.json")

    def test_is_list(self):
        assert isinstance(self.types, list)

    def test_count(self):
        assert len(self.types) == 12, f"Expected 12 work types, got {len(self.types)}"

    def test_required_fields(self):
        for wt in self.types:
            assert "id" in wt and "name" in wt, (
                f"Work type entry missing id or name: {wt}"
            )


# ---------- base_structures.json ----------


class TestBaseStructures:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.structures = load_json("base_structures.json")

    def test_is_list(self):
        assert isinstance(self.structures, list)

    def test_required_fields(self):
        required = {"id", "name", "category", "technology_level"}
        for s in self.structures:
            missing = required - set(s.keys())
            assert not missing, (
                f"Structure '{s.get('name', '?')}' missing: {missing}"
            )

    def test_ids_unique(self):
        ids = [s["id"] for s in self.structures]
        dupes = [i for i in ids if ids.count(i) > 1]
        assert not dupes, f"Duplicate structure ids: {set(dupes)}"


# ---------- breeding_combos.json ----------


class TestBreedingCombos:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_json("breeding_combos.json")

    def test_has_unique_combos(self):
        assert "unique_combos" in self.data
        assert isinstance(self.data["unique_combos"], list)

    def test_combo_structure(self):
        required = {"parent1", "parent2", "child"}
        for combo in self.data["unique_combos"]:
            missing = required - set(combo.keys())
            assert not missing, f"Breeding combo missing fields: {missing} in {combo}"

    def test_no_duplicate_combos(self):
        pairs = []
        for combo in self.data["unique_combos"]:
            pair = tuple(sorted([combo["parent1"], combo["parent2"]]))
            assert pair not in pairs, (
                f"Duplicate breeding pair: {combo['parent1']} + {combo['parent2']}"
            )
            pairs.append(pair)


# ---------- Cross-file integrity ----------


class TestCrossFileIntegrity:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.pals = load_json("pals.json")
        self.partner_skills = load_json("partner_skills.json")
        self.work_types = load_json("work_suitabilities.json")

    def test_pal_work_types_match_definitions(self):
        valid_ids = {wt["id"] for wt in self.work_types}
        for pal in self.pals:
            for wt in pal["work_suitabilities"]:
                assert wt in valid_ids, (
                    f"Pal '{pal['display_name']}' references unknown work type: {wt}"
                )

    def test_partner_skill_pal_references_exist(self):
        pal_names = {p["internal_name"] for p in self.pals}
        for ps in self.partner_skills:
            assert ps["pal_internal_name"] in pal_names, (
                f"Partner skill '{ps['name']}' references unknown Pal: "
                f"{ps['pal_internal_name']}"
            )

    def test_pal_partner_skill_references_exist(self):
        ps_ids = {ps["id"] for ps in self.partner_skills}
        for pal in self.pals:
            ps_id = pal.get("partner_skill_id")
            if ps_id:
                assert ps_id in ps_ids, (
                    f"Pal '{pal['display_name']}' references unknown partner skill: "
                    f"{ps_id}"
                )
