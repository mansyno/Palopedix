"""Configuration module for PalEngine."""

import os
from typing import Literal

_STATIC_DATA_SOURCE = os.getenv("STATIC_DATA_SOURCE", "palworld_db")
_PALWORLD_DB_PATH = os.getenv("PALWORLD_DB_PATH", r"c:\AI\palDBxtrct\palworld.db")
_ASSETS_DIR = os.getenv("ASSETS_DIR", r"C:\palworld_assets")


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


def get_data_dir() -> str:
    """Returns path to PalEngine data directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
