import pytest
from fastapi.testclient import TestClient
from palengine.api.main import app
from palengine.db.sqlite_engine import SQLiteEngine
from palengine.analytics.breeding_graph import BreedingGraphOptimizer


def test_passive_lineage_api_validation():
    """Verify endpoint rejects missing parameters."""
    client = TestClient(app)
    # Missing passives
    res = client.get("/api/breeding/lineage-path?target=Eidrolon")
    assert res.status_code == 422 or res.status_code == 400

    # Missing target
    res = client.get("/api/breeding/lineage-path?passives=Demon%20God")
    assert res.status_code == 422 or res.status_code == 400


def test_passive_lineage_nonexistent_passive():
    """Verify empty result when requesting passive traits player does not own."""
    client = TestClient(app)
    res = client.get("/api/breeding/lineage-path?target=Eidrolon&passives=NonExistentSkillXYZ123")
    assert res.status_code == 200
    data = res.json()
    assert data["target_species"] == "Eidrolon"
    assert data["paths"] == []


def test_passive_lineage_nonexistent_target():
    """Verify empty result when requesting an invalid Pal species."""
    client = TestClient(app)
    res = client.get("/api/breeding/lineage-path?target=PikachuNotReal&passives=Demon%20God")
    assert res.status_code == 200
    data = res.json()
    assert data["paths"] == []


def test_passive_lineage_live_convergence():
    """Verify multi-generation 1+1 convergence for Eidrolon with Immortality + Demon God."""
    client = TestClient(app)
    res = client.get("/api/breeding/lineage-path?target=Eidrolon&passives=Immortality,Demon%20God&max_depth=5&max_results=3")
    assert res.status_code == 200
    data = res.json()
    assert data["target_species"] == "Eidrolon"
    assert len(data["target_passives"]) == 2

    paths = data.get("paths", [])
    assert len(paths) >= 1
    assert len(paths) <= 3

    # Option 1 should be the shortest path (2 generations)
    top_path = paths[0]
    assert top_path["total_steps"] == 2
    assert "2 Generations" in top_path["title"]
    assert top_path["strategy"] == "1 + 1 Trait Convergence"
    assert len(top_path["steps"]) == 2

    # Verify step 1 produces intermediate Beakon Cryst
    step1 = top_path["steps"][0]
    assert step1["step_number"] == 1
    assert step1["child"]["species"] == "Beakon Cryst"
    assert "Demon God" in step1["child"]["target_passives"]

    # Verify step 2 yields Eidrolon
    step2 = top_path["steps"][1]
    assert step2["step_number"] == 2
    assert step2["child"]["species"] == "Eidrolon"
    assert "Immortality" in step2["child"]["target_passives"]
    assert "Demon God" in step2["child"]["target_passives"]


def test_passive_lineage_single_passive():
    """Verify single-passive lineage calculation."""
    client = TestClient(app)
    res = client.get("/api/breeding/lineage-path?target=Eidrolon&passives=Immortality&max_depth=3")
    assert res.status_code == 200
    data = res.json()
    paths = data.get("paths", [])
    assert len(paths) >= 1
    for p in paths:
        assert p["strategy"] == "Direct Trait Convergence" or p["strategy"] == "2 + 0 Clean Convergence"
        assert p["total_steps"] <= 3


def test_passive_lineage_three_passives():
    """Verify 3-passive lineage calculation converges all 3 traits into the target Pal."""
    client = TestClient(app)
    res = client.get("/api/breeding/lineage-path?target=Eidrolon&passives=Legend,Artisan,Ferocious&max_depth=5&max_results=3")
    assert res.status_code == 200
    data = res.json()
    assert data["target_species"] == "Eidrolon"
    assert len(data["target_passives"]) == 3

    paths = data.get("paths", [])
    # It's valid for the engine to find no paths if the player's inventory doesn't have donors for all 3 traits.
    # But if paths exist, they must satisfy the structural constraints.
    for p in paths:
        assert p["strategy"] in (
            "3 + 0 Triple Carrier Convergence",
            "2 + 1 Trait Convergence",
            "1 + 1 + 1 Hierarchical Convergence",
        )
        assert p["total_steps"] <= 5
        # Final step must produce the target species
        final_step = p["steps"][-1]
        assert final_step["child"]["species"] == "Eidrolon"
        assert final_step["child"]["is_target"] is True
        # All 3 passives present in the final child target_passives
        final_passives = [tp.lower() for tp in final_step["child"]["target_passives"]]
        assert "legend" in final_passives
        assert "artisan" in final_passives
        assert "ferocious" in final_passives


def test_passive_lineage_four_passives():
    """Verify 4-passive lineage calculation converges all 4 traits into the target Pal."""
    client = TestClient(app)
    res = client.get("/api/breeding/lineage-path?target=Eidrolon&passives=Legend,Artisan,Ferocious,Swift&max_depth=5&max_results=3")
    assert res.status_code == 200
    data = res.json()
    assert data["target_species"] == "Eidrolon"
    assert len(data["target_passives"]) == 4

    paths = data.get("paths", [])
    for p in paths:
        assert p["strategy"] in (
            "4 + 0 Quad Carrier Convergence",
            "3 + 1 Trait Convergence",
            "2 + 2 Dual Carrier Convergence",
            "1 + 1 + 1 + 1 Two-Line Intermediate Tree",
        )
        assert p["total_steps"] <= 5
        final_step = p["steps"][-1]
        assert final_step["child"]["species"] == "Eidrolon"
        assert final_step["child"]["is_target"] is True
        final_passives = [tp.lower() for tp in final_step["child"]["target_passives"]]
        assert "legend" in final_passives
        assert "artisan" in final_passives
        assert "ferocious" in final_passives
        assert "swift" in final_passives


def test_passive_lineage_api_rejects_five_passives():
    """Verify endpoint rejects more than 4 passives."""
    client = TestClient(app)
    res = client.get("/api/breeding/lineage-path?target=Eidrolon&passives=Legend,Artisan,Ferocious,Swift,Runner")
    assert res.status_code == 400
    assert "Maximum 4" in res.json()["detail"]

