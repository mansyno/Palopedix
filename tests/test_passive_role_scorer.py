"""Unit tests for the 4-Aspect Passive Role Scorer."""

import pytest
from palengine.analytics.passive_role_scorer import (
    calculate_passive_role_scores,
    WORK_PASSIVES,
    ATTACK_PASSIVES,
    DEFENSE_PASSIVES,
    MOVEMENT_PASSIVES,
)
from palengine.db.sqlite_engine import SQLiteEngine


def test_calculate_passive_role_scores_work():
    """Verifies Work points calculation and negative trade-off penalty."""
    passives = ["Remarkable Craftsmanship", "Artisan", "Serious", "Musclehead"]
    res = calculate_passive_role_scores(passives)

    # Work: +75 + 50 + 20 - 50 = 95
    assert res["score_work"] == 95
    # Attack: Musclehead gives +30
    assert res["score_attack"] == 30
    assert res["score_defense"] == 0
    assert res["score_movement"] == 0

    assert res["score_best"] == 95
    assert res["best_role"] == "work"
    assert len(res["breakdown"]["work"]) == 4


def test_calculate_passive_role_scores_attack():
    """Verifies Attack points calculation, trade-offs, and top offensive passives."""
    passives = ["Twin-Edged Holy Blade", "God of Destruction", "Demon God", "Musclehead"]
    res = calculate_passive_role_scores(passives)

    # Attack: +50 + 40 + 30 + 30 = 150
    assert res["score_attack"] == 150
    # Work penalty: Musclehead gives -50
    assert res["score_work"] == -50
    # Defense: Twin-Edged Holy Blade gives -30, God of Destruction gives +20 = -10
    assert res["score_defense"] == -10
    assert res["score_best"] == 150
    assert res["best_role"] == "attack"


def test_calculate_passive_role_scores_defense():
    """Verifies Defense points calculation including defensive passives and Coward penalty."""
    passives = ["Sanctified Meat Shield", "Diamond Body", "Burly Body", "Coward"]
    res = calculate_passive_role_scores(passives)

    # Defense: +50 (Sanctified Meat Shield) + 35 (Diamond Body) + 20 (Burly Body) = 105
    assert res["score_defense"] == 105
    # Attack: Coward gives -10
    assert res["score_attack"] == -10
    assert res["score_work"] == 0
    assert res["score_movement"] == 0
    assert res["score_best"] == 105
    assert res["best_role"] == "defense"


def test_calculate_passive_role_scores_movement():
    """Verifies Movement speed points calculation and cross-role bonus from Legend."""
    passives = ["Swift", "Runner", "Nimble", "Legend"]
    res = calculate_passive_role_scores(passives)

    # Movement: +30 (Swift) + 20 (Runner) + 10 (Nimble) + 20 (Legend) = 80
    assert res["score_movement"] == 80
    # Legend also grants +20 Attack and +20 Defense
    assert res["score_attack"] == 20
    assert res["score_defense"] == 20
    assert res["score_best"] == 80
    assert res["best_role"] == "movement"


def test_alias_and_misspelling_handling():
    """Verifies aliases for Nocturnal/Night Owl and World Tree Seedbed/World Tree's Bounty."""
    res1 = calculate_passive_role_scores(["Nocturnal", "Night Owl"])
    assert res1["score_work"] == 35  # 20 + 15

    res2 = calculate_passive_role_scores(["World Tree's Bounty"])
    assert res2["score_work"] == 25

    res3 = calculate_passive_role_scores(["World Tree Seedbed"])
    assert res3["score_work"] == 25


def test_unlisted_passives_zero_score():
    """Verifies that unlisted passives contribute 0 points."""
    res = calculate_passive_role_scores(["NonExistentPassive", "RandomPlaceholder"])
    assert res["score_work"] == 0
    assert res["score_attack"] == 0
    assert res["score_defense"] == 0
    assert res["score_movement"] == 0
    assert res["score_best"] == 0
    assert len(res["breakdown"]["work"]) == 0
    assert len(res["breakdown"]["attack"]) == 0


def test_passives_dict_and_string_formats():
    """Verifies that input passives can be strings or dicts with 'name' or 'id'."""
    passives = [
        {"name": "Artisan"},
        "Serious",
        {"id": "Passive_Musclehead", "name": "Musclehead"},
    ]
    res = calculate_passive_role_scores(passives)
    # Work: +50 (Artisan) + 20 (Serious) - 50 (Musclehead) = 20
    assert res["score_work"] == 20
    assert res["score_attack"] == 30


def test_sqlite_engine_enrichment_and_sorting():
    """Verifies that SQLiteEngine queries enrich instances with role scores and support sort_by."""
    engine = SQLiteEngine()
    instances = engine.query_instances({})
    if not instances:
        pytest.skip("No save instances found in database for instance query test.")

    first = instances[0]
    assert "score_work" in first
    assert "score_attack" in first
    assert "score_defense" in first
    assert "score_movement" in first
    assert "score_best" in first
    assert "best_role" in first
    assert "role_scores" in first
    assert "role_breakdown" in first

    # Test sorting by work score
    sorted_work = engine.query_instances({}, sort_by="work")
    for i in range(len(sorted_work) - 1):
        assert sorted_work[i]["score_work"] >= sorted_work[i + 1]["score_work"]

    # Test sorting by attack score
    sorted_attack = engine.query_instances({}, sort_by="attack")
    for i in range(len(sorted_attack) - 1):
        assert sorted_attack[i]["score_attack"] >= sorted_attack[i + 1]["score_attack"]
