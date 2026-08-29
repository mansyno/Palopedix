"""Module to extract World Option settings from WorldOption.sav or PalWorldSettings.ini."""

import os
import re
from typing import Any, Dict, Optional
from palengine.parser.extract_pals import load_gvas_from_sav


def extract_world_settings(sav_path: str) -> Dict[str, Any]:
    """Reads WorldOption.sav (or PalWorldSettings.ini) and extracts game multiplier options.

    Args:
        sav_path: Path to Level.sav or the world save directory.

    Returns:
        Dict mapping setting key names (e.g. 'BaseCampWorkerMaxNum') to parsed values.
    """
    save_dir = os.path.dirname(sav_path) if os.path.isfile(sav_path) else sav_path

    # Defaults
    settings: Dict[str, Any] = {
        "BaseCampWorkerMaxNum": 15,
        "BaseCampMaxNumInGuild": 4,
        "PalEggDefaultHatchingTime": 0.0,
        "ExpRate": 1.0,
        "PalCaptureRate": 1.0,
        "DayTimeSpeedRate": 1.0,
        "NightTimeSpeedRate": 1.0,
    }

    # 1. Check WorldOption.sav in the save folder
    opt_sav_path = os.path.join(save_dir, "WorldOption.sav")
    if os.path.exists(opt_sav_path):
        try:
            gvas = load_gvas_from_sav(opt_sav_path, [])
            raw_props = gvas.properties.get("OptionWorldData", {}).get("value", {})
            if isinstance(raw_props, dict):
                settings_dict = raw_props.get("Settings", {}).get("value", {})
                if isinstance(settings_dict, dict):
                    for k, v in settings_dict.items():
                        val = v.get("value") if isinstance(v, dict) else v
                        if isinstance(val, dict) and "value" in val:
                            val = val["value"]
                        settings[k] = val
            return settings
        except Exception:
            pass

    # 2. Check PalWorldSettings.ini if present (e.g. Dedicated Server configuration)
    ini_path = os.path.join(save_dir, "PalWorldSettings.ini")
    if not os.path.exists(ini_path):
        parent_dir = os.path.dirname(save_dir)
        candidate = os.path.join(parent_dir, "PalWorldSettings.ini")
        if os.path.exists(candidate):
            ini_path = candidate

    if os.path.exists(ini_path):
        try:
            with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            match = re.search(r"OptionSettings=\((.*?)\)", content, re.DOTALL)
            if match:
                inner = match.group(1)
                pairs = re.findall(r"([A-Za-z0-9_]+)=([^\s,\)\"]+|\"[^\"]*\")", inner)
                for k, v in pairs:
                    v_clean = v.strip('"')
                    if v_clean.lower() == "true":
                        settings[k] = True
                    elif v_clean.lower() == "false":
                        settings[k] = False
                    else:
                        try:
                            if "." in v_clean:
                                settings[k] = float(v_clean)
                            else:
                                settings[k] = int(v_clean)
                        except ValueError:
                            settings[k] = v_clean
        except Exception:
            pass

    return settings
