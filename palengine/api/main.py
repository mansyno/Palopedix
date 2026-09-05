"""FastAPI application for PalEngine.

Exposes endpoints for querying static Paldex, breeding calculations, asset serving, and save file dynamic instances.
"""

import os
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from palengine.cli.main import get_resolved_save_path
from palengine.config import (
    get_assets_dir,
    get_static_data_source,
    set_static_data_source,
)
from palengine.db.sqlite_engine import SQLiteEngine

app = FastAPI(title="PalEngine API", version="1.0.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount local asset directory if available
assets_dir = get_assets_dir()
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# Global database connection instance
db_engine = SQLiteEngine()


class LoadSaveRequest(BaseModel):
    save_path: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    static_data_source: str


from palengine.world_manager import discover_worlds, get_world_by_id


class SelectWorldRequest(BaseModel):
    world_id: str


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    """Returns current API configuration."""
    return {
        "static_data_source": get_static_data_source(),
        "assets_dir": get_assets_dir(),
    }


@app.get("/api/worlds")
def get_worlds() -> dict[str, Any]:
    """Returns list of active discovered save worlds and current selected world."""
    worlds = discover_worlds()
    return {
        "worlds": worlds,
        "current_world_id": db_engine.current_world_id,
        "current_save_path": db_engine.current_save_path,
    }


@app.post("/api/worlds/select")
def select_world(payload: SelectWorldRequest) -> dict[str, Any]:
    """Switches active world database connection."""
    try:
        res = db_engine.switch_world(payload.world_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/config")
def update_config(payload: ConfigUpdateRequest) -> dict[str, Any]:
    """Updates API static data source ('palworld_db' or 'legacy')."""
    global db_engine
    set_static_data_source(payload.static_data_source)
    db_engine = SQLiteEngine()
    return {
        "status": "success",
        "static_data_source": get_static_data_source(),
    }


@app.post("/api/save/load")
def load_save(payload: LoadSaveRequest) -> dict[str, Any]:
    """Loads the save game database from the provided path or auto-discovers it."""
    try:
        resolved_path = get_resolved_save_path(payload.save_path)
        db_engine.load_save_data(resolved_path)
        return {
            "status": "success",
            "message": "Save game loaded successfully.",
            "path": resolved_path,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/save/status")
def get_save_status() -> dict[str, Any]:
    """Returns whether a save game is currently loaded in memory."""
    try:
        cursor = db_engine.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM pal_instances")
        count = cursor.fetchone()["count"]
        return {
            "loaded": count > 0,
            "path": db_engine.current_save_path if count > 0 else None,
        }
    except Exception:
        return {"loaded": False, "path": None}


@app.get("/api/pals")
def get_pals(
    element: Optional[str] = None,
    nocturnal: Optional[bool] = None,
    size: Optional[str] = None,
    suitability: Optional[str] = None,
    partner_category: Optional[str] = None,
    category: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Queries the static Paldex database."""
    filters: dict[str, Any] = {}
    if element:
        filters["element"] = element.capitalize()
    if nocturnal is not None:
        filters["nocturnal"] = nocturnal
    if size:
        filters["size"] = size
    if partner_category or category:
        filters["partner_category"] = partner_category or category

    if suitability:
        if ":" in suitability:
            name, min_lvl = suitability.split(":", 1)
            filters["work_suitability"] = {"name": name.lower(), "min_level": int(min_lvl)}
        else:
            filters["work_suitability"] = {"name": suitability.lower(), "min_level": 1}

    return db_engine.query_pals(filters)


@app.get("/api/pals/partner-skill-categories")
def get_partner_skill_categories() -> list[dict[str, Any]]:
    """Returns all available Partner Skill categories with metadata and current Pal counts."""
    return db_engine.get_partner_skill_categories()


@app.get("/api/save/instances")
def get_instances(
    location: Optional[str] = None,
    species: Optional[str] = None,
    gender: Optional[str] = None,
    min_level: Optional[int] = None,
    passive: Optional[str] = None,
    partner_category: Optional[str] = None,
    category: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Queries dynamic Pal instances (requires loading save game first)."""
    filters: dict[str, Any] = {}
    if location:
        filters["location"] = location
    if species:
        filters["species"] = species
    if gender:
        filters["gender"] = gender
    if min_level:
        filters["min_level"] = min_level
    if passive:
        filters["passive_id"] = passive
    if partner_category or category:
        filters["partner_category"] = partner_category or category

    return db_engine.query_instances(filters)


@app.get("/api/save/condense")
def get_condense_candidates() -> list[dict[str, Any]]:
    """Returns top condensing candidates from the dynamic save instances."""
    return db_engine.get_condense_candidates()


@app.get("/api/save/missions")
def get_active_missions() -> list[dict[str, Any]]:
    """Returns active uncompleted sub-missions evaluated against targeted inventory items and caught Pals."""
    return db_engine.get_active_missions()


@app.get("/api/save/inventory")
def get_inventory(container_type: Optional[str] = None) -> list[dict[str, Any]]:
    """Queries item inventory from dynamic save data."""
    return db_engine.query_inventory(container_type)


@app.get("/api/save/owned-species")
def get_owned_species() -> list[str]:
    """Returns list of distinct Pal species owned in the loaded save data."""
    return db_engine.get_owned_pal_species()


class RenameBaseRequest(BaseModel):
    custom_name: str


@app.get("/api/bases")
def get_bases() -> list[dict[str, Any]]:
    """Lists all base camps, structure summaries, and focus categories."""
    from palengine.analytics.base_optimizer import BaseOptimizer
    optimizer = BaseOptimizer(db_engine)

    cursor = db_engine.conn.cursor()
    cursor.execute("SELECT base_camp_id, name FROM base_camps")
    base_rows = cursor.fetchall()

    results = []
    for b in base_rows:
        bid = b["base_camp_id"]
        summary = db_engine.get_base_camp_summary(bid)
        if summary:
            audit = optimizer.audit_base_work_demand(bid)
            summary["base_category"] = audit.get("base_category", "Balanced")
            summary["electric_deficit"] = audit.get("electric_deficit", 0)
            summary["breeding_farm_count"] = audit.get("breeding_farm_count", 0)
            results.append(summary)
    return results


@app.get("/api/bases/{base_camp_id}")
def get_base_detail(base_camp_id: str) -> dict[str, Any]:
    """Returns detailed summary for a specific base camp."""
    from palengine.analytics.base_optimizer import BaseOptimizer
    summary = db_engine.get_base_camp_summary(base_camp_id)
    if not summary:
        raise HTTPException(
            status_code=404, detail=f"Base camp not found: {base_camp_id}"
        )
    audit = BaseOptimizer(db_engine).audit_base_work_demand(base_camp_id)
    summary["base_category"] = audit.get("base_category", "Balanced")
    summary["electric_deficit"] = audit.get("electric_deficit", 0)
    summary["breeding_farm_count"] = audit.get("breeding_farm_count", 0)
    return summary


@app.put("/api/base_camps/{base_camp_id}/name")
@app.put("/api/bases/{base_camp_id}/name")
def rename_base_camp(base_camp_id: str, request: RenameBaseRequest) -> dict[str, Any]:
    """Sets a custom app-level name for a base camp."""
    db_engine.set_base_camp_custom_name(base_camp_id, request.custom_name)
    return {
        "success": True,
        "base_camp_id": base_camp_id,
        "custom_name": request.custom_name.strip(),
    }


@app.get("/api/breeding/result")
@app.get("/api/breeding/calculate")
def get_breed_result(parent1: str, parent2: str) -> dict[str, Any]:
    """Calculates breeding result of two parent species."""
    res = db_engine.get_breeding_result(parent1, parent2)
    if not res:
        raise HTTPException(
            status_code=400,
            detail=f"Could not calculate breeding result for parents: '{parent1}', '{parent2}'",
        )
    return res


@app.get("/api/breeding/parents")
@app.get("/api/breeding/parents/{child}")
def get_breed_parents(
    child: Optional[str] = None,
    owned: Optional[str] = None,
    source: Optional[str] = None,
) -> list[tuple[str, str]]:
    """Lists all breeding combinations that yield the target child, optionally filtered by owned inventory."""
    if not child:
        raise HTTPException(status_code=400, detail="Target child Pal is required.")
    pool_param = owned or source
    if pool_param and pool_param.strip().lower() in ("all", "global", "*"):
        return db_engine.find_parents_for_child(child)
    elif pool_param and pool_param.strip().lower() in ("auto", "caught"):
        owned_inv = list(db_engine.get_owned_pal_inventory().keys())
        return db_engine.find_parents_for_child(child, pool=owned_inv)
    elif pool_param:
        owned_list = [s.strip() for s in pool_param.split(",") if s.strip()]
        return db_engine.find_parents_for_child(child, pool=owned_list)
    return db_engine.find_parents_for_child(child)


@app.get("/api/breeding/offspring")
@app.get("/api/breeding/offspring/{parent}")
def get_breed_offspring(
    parent: Optional[str] = None,
    owned: Optional[str] = None,
    source: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Lists all unique offspring possible from a single parent, optionally filtered by owned inventory."""
    if not parent:
        raise HTTPException(status_code=400, detail="Parent Pal is required.")
    pool_param = owned or source
    if pool_param and pool_param.strip().lower() in ("all", "global", "*"):
        return db_engine.get_offspring_for_parent(parent)
    elif pool_param and pool_param.strip().lower() in ("auto", "caught"):
        owned_inv = list(db_engine.get_owned_pal_inventory().keys())
        return db_engine.get_offspring_for_parent(parent, pool=owned_inv)
    elif pool_param:
        owned_list = [s.strip() for s in pool_param.split(",") if s.strip()]
        return db_engine.get_offspring_for_parent(parent, pool=owned_list)
    return db_engine.get_offspring_for_parent(parent)


@app.get("/api/breeding/uncaught")
@app.get("/api/breeding/uncaught-opportunities")
def get_uncaught_breeding_opportunities(
    owned: Optional[str] = None,
    source: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Finds all Pal species not yet caught that can be bred from currently owned Pals or all game pals."""
    pool_param = owned or source
    if pool_param and pool_param.strip().lower() in ("all", "global", "*"):
        return db_engine.get_uncaught_breeding_opportunities(parent_pool="all")
    elif pool_param and pool_param.strip().lower() not in ("auto", "caught"):
        owned_list = [s.strip() for s in pool_param.split(",") if s.strip()]
        return db_engine.get_uncaught_breeding_opportunities(owned_input=owned_list, parent_pool=owned_list)
    return db_engine.get_uncaught_breeding_opportunities(parent_pool="auto")


@app.get("/api/breeding/path")
def get_breeding_path(
    target: str,
    owned: Optional[str] = None,
    owned_pals: Optional[str] = None,
    source: Optional[str] = None,
    target_skills: Optional[str] = None,
) -> dict[str, Any]:
    """Finds shortest multi-generation breeding paths to target Pal with skill-aware parent instance quality & gender odds."""
    pool_param = owned_pals or owned or source
    if pool_param and pool_param.strip().lower() in ("all", "global", "*"):
        paths = db_engine.find_all_breeding_paths("all", target, target_skills)
    elif not pool_param or pool_param.strip().lower() in ("auto", "caught"):
        owned_inv = db_engine.get_owned_pal_inventory()
        paths = db_engine.find_all_breeding_paths(owned_inv, target, target_skills)
    else:
        owned_list = [s.strip() for s in pool_param.split(",") if s.strip()]
        paths = db_engine.find_all_breeding_paths(owned_list, target, target_skills)

    return {"target": target, "target_skills": target_skills, "paths": paths}


@app.get("/api/items")
def get_items(
    category: Optional[str] = None,
    rarity: Optional[int] = None,
    search: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Queries items and equipment catalog."""
    filters: dict[str, Any] = {}
    if category:
        filters["category"] = category
    if rarity is not None:
        filters["rarity"] = rarity
    if search:
        filters["search"] = search
    return db_engine.query_items(filters)


@app.get("/api/items/{item_id}/recipe")
def get_recipe(item_id: str) -> dict[str, Any]:
    """Retrieves crafting recipe and material ingredients for an item."""
    recipe = db_engine.get_item_recipe(item_id)
    if not recipe:
        raise HTTPException(
            status_code=404, detail=f"No crafting recipe found for item: '{item_id}'"
        )
    return recipe


@app.get("/api/buildings")
def get_buildings(
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Queries base camp buildings & infrastructure."""
    filters: dict[str, Any] = {}
    if category:
        filters["category"] = category
    if search:
        filters["search"] = search
    return db_engine.query_buildings(filters)


@app.get("/api/tech_tree")
def get_tech_tree(
    level: Optional[int] = None,
    is_ancient: Optional[bool] = None,
) -> list[dict[str, Any]]:
    """Queries technology tree unlock nodes."""
    filters: dict[str, Any] = {}
    if level is not None:
        filters["level"] = level
    if is_ancient is not None:
        filters["is_ancient"] = is_ancient
    return db_engine.query_tech_tree(filters)


@app.get("/api/work_types")
def get_work_types() -> list[dict[str, Any]]:
    """Lists all 12 official Palworld work suitability types with HUD icon paths."""
    return db_engine.query_work_types()


@app.get("/api/skills")
def get_skills(
    type: Optional[str] = None,
    element: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Queries skills catalog (Active, Passive, Partner)."""
    filters: dict[str, Any] = {}
    if type:
        filters["type"] = type
    if element:
        filters["element"] = element
    if category:
        filters["category"] = category
    if source:
        filters["source"] = source
    if search:
        filters["search"] = search
    return db_engine.query_skills(filters)


@app.get("/api/base_camps")
def get_base_camps() -> list[dict[str, Any]]:
    """Returns list of active base camps in user save data."""
    return db_engine.get_base_camps()


@app.get("/api/base_camps/{base_camp_id}/structures")
def get_base_camp_structures(base_camp_id: str) -> list[dict[str, Any]]:
    """Returns structures built in a base camp with work suitability requirements."""
    return db_engine.get_base_camp_structures(base_camp_id)


@app.get("/api/base_camps/{base_camp_id}/recommendations")
def get_base_camp_recommendations(
    base_camp_id: str,
    max_team_size: Optional[int] = Query(None, description="Optional max team size capacity override"),
    reserved_breeding: Optional[int] = Query(None, description="Optional reserved breeding slots override"),
) -> dict[str, Any]:
    """Generates optimal recommended Pal team for a given base camp using holistic multi-base optimization."""
    from palengine.analytics.pal_recommender import PalRecommender
    recommender = PalRecommender(db_engine)
    return recommender.recommend_pals_for_base(
        base_camp_id,
        max_team_size=max_team_size,
        reserved_breeding=reserved_breeding,
    )


@app.get("/api/save/settings")
def get_world_settings() -> dict[str, Any]:
    """Returns active world multiplier settings (e.g. BaseCampWorkerMaxNum, EggHatchTime)."""
    return db_engine.get_world_settings()


# ── Base-to-Base Container Migration & Logistics ──────────────────────────────
class MigrationManifestRequest(BaseModel):
    source_base_id: str
    target_base_id: str
    included_types: Optional[list[str]] = None


class MigrationExecuteRequest(BaseModel):
    source_base_id: str
    target_base_id: str
    included_types: Optional[list[str]] = None
    force: bool = False


def _get_active_save_path() -> Optional[str]:
    from palengine.cli.main import discover_save_path
    return getattr(db_engine, "current_save_path", None) or discover_save_path()


@app.get("/api/migration/bases")
def get_migration_bases() -> list[dict[str, Any]]:
    """Returns all base camps with container type breakdown and item counts."""
    from palengine.logistics.base_migration import CONTAINER_TYPE_INFO, inspect_base_containers

    save_path = _get_active_save_path()
    if not save_path or not os.path.exists(save_path):
        raise HTTPException(status_code=404, detail="Save file Level.sav not found.")

    all_containers = inspect_base_containers(save_path)
    custom_names = db_engine.get_base_camp_custom_names()
    base_camps_db = {b["base_camp_id"]: b for b in db_engine.get_base_camps()}

    result = []
    for b_id, c_list in all_containers.items():
        db_base = base_camps_db.get(b_id, {})
        display_name = (
            custom_names.get(b_id)
            or db_base.get("name")
            or f"Base {b_id[:8]}"
        )

        type_counts: dict[str, dict[str, Any]] = {}
        total_items = 0
        named_containers = []

        for c in c_list:
            oid = c["map_object_id"]
            type_name = CONTAINER_TYPE_INFO.get(oid, {}).get("name", oid)
            if oid not in type_counts:
                type_counts[oid] = {
                    "type_id": oid,
                    "name": type_name,
                    "count": 0,
                    "slots": CONTAINER_TYPE_INFO.get(oid, {}).get("slots", 32),
                }
            type_counts[oid]["count"] += 1
            total_items += sum(i["count"] for i in c["items"])
            if c.get("custom_name"):
                named_containers.append({
                    "custom_name": c["custom_name"],
                    "map_object_id": oid,
                    "type_name": type_name,
                    "items_count": len(c["items"]),
                })

        result.append({
            "base_camp_id": b_id,
            "name": display_name,
            "total_containers": len(c_list),
            "total_items": total_items,
            "container_types": list(type_counts.values()),
            "named_containers": named_containers,
        })

    return result


@app.post("/api/migration/manifest")
def create_migration_manifest(req: MigrationManifestRequest) -> dict[str, Any]:
    """Generates the Construction Manifest and Base 2 container readiness status."""
    from palengine.logistics.base_migration import generate_construction_manifest

    save_path = _get_active_save_path()
    if not save_path or not os.path.exists(save_path):
        raise HTTPException(status_code=404, detail="Save file Level.sav not found.")

    try:
        manifest = generate_construction_manifest(
            save_path,
            req.source_base_id,
            req.target_base_id,
            included_types=req.included_types,
        )
        return manifest
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/migration/execute")
def execute_migration(req: MigrationExecuteRequest) -> dict[str, Any]:
    """Executes the container item relocation into Base 2 and empties source containers."""
    import psutil
    from palengine.logistics.base_migration import execute_base_migration

    # Safety check: ensure Palworld is not running
    if not req.force:
        for proc in psutil.process_iter(["name"]):
            try:
                if "palworld" in (proc.info["name"] or "").lower():
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Palworld is currently running. Please save and exit the game completely "
                            "before transferring items to prevent file locks, corruption, or overwrite conflicts."
                        ),
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    save_path = _get_active_save_path()
    if not save_path or not os.path.exists(save_path):
        raise HTTPException(status_code=404, detail="Save file Level.sav not found.")

    try:
        result = execute_base_migration(
            save_path,
            req.source_base_id,
            req.target_base_id,
            included_types=req.included_types,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))





