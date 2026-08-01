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


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    """Returns current API configuration."""
    return {
        "static_data_source": get_static_data_source(),
        "assets_dir": get_assets_dir(),
    }


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
) -> list[dict[str, Any]]:
    """Queries the static Paldex database."""
    filters: dict[str, Any] = {}
    if element:
        filters["element"] = element.capitalize()
    if nocturnal is not None:
        filters["nocturnal"] = nocturnal
    if size:
        filters["size"] = size

    if suitability:
        if ":" in suitability:
            name, min_lvl = suitability.split(":", 1)
            filters["work_suitability"] = {"name": name.lower(), "min_level": int(min_lvl)}
        else:
            filters["work_suitability"] = {"name": suitability.lower(), "min_level": 1}

    return db_engine.query_pals(filters)


@app.get("/api/save/instances")
def get_instances(
    location: Optional[str] = None,
    species: Optional[str] = None,
    gender: Optional[str] = None,
    min_level: Optional[int] = None,
    passive: Optional[str] = None,
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

    return db_engine.query_instances(filters)


@app.get("/api/bases")
def get_bases() -> list[dict[str, Any]]:
    """Lists all base camps and structure Summaries."""
    cursor = db_engine.conn.cursor()
    cursor.execute("SELECT base_camp_id, name FROM base_camps")
    base_rows = cursor.fetchall()

    results = []
    for b in base_rows:
        summary = db_engine.get_base_camp_summary(b["base_camp_id"])
        if summary:
            results.append(summary)
    return results


@app.get("/api/bases/{base_camp_id}")
def get_base_detail(base_camp_id: str) -> dict[str, Any]:
    """Returns detailed summary for a specific base camp."""
    summary = db_engine.get_base_camp_summary(base_camp_id)
    if not summary:
        raise HTTPException(
            status_code=404, detail=f"Base camp not found: {base_camp_id}"
        )
    return summary


@app.get("/api/breeding/result")
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
def get_breed_parents(child: str) -> list[tuple[str, str]]:
    """Lists all breeding combinations that yield the target child."""
    return db_engine.find_parents_for_child(child)


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

