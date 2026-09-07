"""Configuration module for PalEngine."""

import os
from typing import Literal


def get_data_dir() -> str:
    """Returns path to PalEngine data directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


def get_default_palworld_db_path() -> str:
    """Returns default path to palworld.db in data directory with legacy fallback."""
    local_db = os.path.join(get_data_dir(), "palworld.db")
    if os.path.exists(local_db):
        return local_db
    legacy_db = r"c:\AI\palDBxtrct\palworld.db"
    if os.path.exists(legacy_db):
        return legacy_db
    return local_db


def get_default_assets_dir() -> str:
    """Returns default path to assets directory with local and legacy fallbacks."""
    # Check if unzipped folder 'palworld_assets' exists inside repo assets/
    repo_extracted_assets = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "palworld_assets"))
    if os.path.exists(repo_extracted_assets):
        return repo_extracted_assets
    # Check if files reside directly inside repo assets/
    repo_assets = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
    if os.path.exists(os.path.join(repo_assets, "pals")):
        return repo_assets
    # Legacy external assets directory fallback
    legacy_assets = r"C:\palworld_assets"
    if os.path.exists(legacy_assets):
        return legacy_assets
    return repo_assets


_STATIC_DATA_SOURCE = os.getenv("STATIC_DATA_SOURCE", "palworld_db")
_PALWORLD_DB_PATH = os.getenv("PALWORLD_DB_PATH", get_default_palworld_db_path())
_ASSETS_DIR = os.getenv("ASSETS_DIR", get_default_assets_dir())


def get_static_data_source() -> str:
    """Returns current static data source ('palworld_db' or 'legacy')."""
    return _STATIC_DATA_SOURCE


def set_static_data_source(source: str) -> None:
    """Sets current static data source ('palworld_db' or 'legacy')."""
    global _STATIC_DATA_SOURCE
    if source not in ("palworld_db", "legacy"):
        raise ValueError(f"Invalid static data source: {source}. Must be 'palworld_db' or 'legacy'.")
    _STATIC_DATA_SOURCE = source


def get_palworld_db_path() -> str:
    """Returns path to Palworld SQLite master database."""
    return _PALWORLD_DB_PATH


def set_palworld_db_path(path: str) -> None:
    """Sets path to Palworld SQLite master database."""
    global _PALWORLD_DB_PATH
    _PALWORLD_DB_PATH = path


def get_assets_dir() -> str:
    """Returns path to Palworld asset directory."""
    return _ASSETS_DIR


def set_assets_dir(path: str) -> None:
    """Sets path to Palworld asset directory."""
    global _ASSETS_DIR
    _ASSETS_DIR = path
