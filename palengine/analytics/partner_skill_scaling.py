"""Partner Skill Scaling and Dynamic Text Interpolation Module for PalEngine.

Handles resolution of rich-text game markup tags (element names, icons, character names),
and computes rank-appropriate skill levels (Lv 1 to Lv 5) and effect percentages
based on Pal condensation rank (0 to 4 stars).
"""

from __future__ import annotations

import re
from typing import Any, Optional

# Canonical Element Mapping from Unreal Engine Localization Tags
ELEMENT_TAG_MAP: dict[str, str] = {
    "COMMON_ELEMENT_NAME_EARTH": "Ground",
    "COMMON_ELEMENT_NAME_GROUND": "Ground",
    "COMMON_ELEMENT_NAME_FIRE": "Fire",
    "COMMON_ELEMENT_NAME_WATER": "Water",
    "COMMON_ELEMENT_NAME_LEAF": "Grass",
    "COMMON_ELEMENT_NAME_GRASS": "Grass",
    "COMMON_ELEMENT_NAME_ELECTRICITY": "Electric",
    "COMMON_ELEMENT_NAME_ELECTRIC": "Electric",
    "COMMON_ELEMENT_NAME_ICE": "Ice",
    "COMMON_ELEMENT_NAME_DARK": "Dark",
    "COMMON_ELEMENT_NAME_DARKNESS": "Dark",
    "COMMON_ELEMENT_NAME_DRAGON": "Dragon",
    "COMMON_ELEMENT_NAME_NORMAL": "Neutral",
    "COMMON_ELEMENT_NAME_NEUTRAL": "Neutral",
}

# 5-Tier Scaling Values [Lv1, Lv2, Lv3, Lv4, Lv5]
# Corresponds to Condensation Stars [0★, 1★, 2★, 3★, 4★]
PARTNER_SKILL_SCALING_TABLE: dict[str, dict[str, Any]] = {
    # --- 1. Mount Element Converters & Infusion ---
    "GoldenHorse": {
        "levels": ["5%", "7.5%", "10%", "15%", "20%"],
        "element": "Ground",
        "type": "infusion",
    },
    "IceDeer": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Dragon",
        "type": "infusion",
    },
    "IceDeer_Fire": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Fire",
        "type": "infusion",
    },
    "FireKirin": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Fire",
        "type": "infusion",
    },
    "FireKirin_Dark": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Dark",
        "type": "infusion",
    },
    "ThunderBird": {
        "params": {
            "Passive3_EffectValue1": ["50%", "55%", "60%", "75%", "100%"],
            "Passive1_EffectValue1": ["5%", "6%", "7%", "8%", "10%"],
        },
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Electric",
        "type": "infusion",
    },
    "ThunderBird_Ice": {
        "params": {
            "Passive3_EffectValue1": ["50%", "55%", "60%", "75%", "100%"],
            "Passive1_EffectValue1": ["5%", "6%", "7%", "8%", "10%"],
        },
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Ice",
        "type": "infusion",
    },
    "HadesBird": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Dark",
        "type": "infusion",
    },
    "HadesBird_Electric": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Electric",
        "type": "infusion",
    },
    "BlueDragon": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Water",
        "type": "infusion",
    },
    "BlueDragon_Ice": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Ice",
        "type": "infusion",
    },
    "WaterDragon": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Water",
        "type": "infusion",
    },
    "IceHorse": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Ice",
        "type": "infusion",
    },
    "IceHorse_Dark": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Dark",
        "type": "infusion",
    },
    "RedArmorBird": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Fire",
        "type": "infusion",
    },
    "DarkArmorBird": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Dark",
        "type": "infusion",
    },
    "GrassPanda": {
        "levels": ["10%", "15%", "20%", "25%", "30%"],
        "element": "Grass",
        "type": "infusion",
    },
    "GrassPanda_Electric": {
        "levels": ["10%", "15%", "20%", "25%", "30%"],
        "element": "Electric",
        "type": "infusion",
    },
    "Anubis": {
        "levels": ["30%", "35%", "40%", "45%", "50%"],
        "element": "Ground",
        "type": "infusion",
    },

    # --- 1b. Self Stat Multipliers (Knocklem & Variants) ---
    "WingGolem": {
        "levels": ["60%", "70%", "80%", "90%", "100%"],
        "type": "self_buff",
    },
    "WingGolem_Fire": {
        "levels": ["60%", "70%", "80%", "90%", "100%"],
        "type": "self_buff",
    },

    # --- 2. Combat Buffers (Party Stat Amplification) ---
    "SharkMan": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_atk",
        "target": "Player",
    },
    "SharkMan_Fire": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_atk",
        "target": "Player",
    },
    "FlameTiger": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_elem_atk",
        "element": "Fire",
    },
    "WaterKelp": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_elem_atk",
        "element": "Water",
    },
    "WaterKelp_Fire": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_elem_atk",
        "element": "Fire",
    },
    "ElecCat": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_elem_atk",
        "element": "Electric",
    },
    "ThornHedgehog": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_elem_atk",
        "element": "Grass",
    },
    "IceFox": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_elem_atk",
        "element": "Ice",
    },
    "MudMan": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_elem_atk",
        "element": "Ground",
    },
    "DarkOwl": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_elem_atk",
        "element": "Dark",
    },
    "FluffySheep": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_elem_atk",
        "element": "Neutral",
    },
    "CuteRabbit": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_work",
    },
    "MoonQueen": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_elem_atk",
    },
    "HerculesBeetle": {
        "params": {
            "Passive1_EffectValue1": ["10%", "11%", "13%", "16%", "20%"],
            "Passive2_EffectValue1": ["10%", "11%", "13%", "16%", "20%"],
        },
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "combat_def",
    },
    "HerculesBeetle_Ground": {
        "params": {
            "Passive1_EffectValue1": ["10%", "11%", "13%", "16%", "20%"],
            "Passive2_EffectValue1": ["10%", "11%", "13%", "16%", "20%"],
        },
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "combat_def",
    },
    "DarkScorpion": {
        "params": {
            "Passive2_EffectValue1": ["10%", "11%", "13%", "16%", "20%"],
            "Passive1_EffectValue1": ["40%", "48%", "56%", "68%", "80%"],
        },
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "combat_def_drop",
    },
    "DarkScorpion_Ground": {
        "params": {
            "Passive2_EffectValue1": ["10%", "11%", "13%", "16%", "20%"],
            "Passive1_EffectValue1": ["40%", "48%", "56%", "68%", "80%"],
        },
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "combat_def_drop",
    },
    "ScorpionMan": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "combat_def",
    },
    "ScorpionMan_Ground": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "combat_def",
    },
    "Umihebi": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_elem_atk",
        "element": "Water",
    },
    "Umihebi_Fire": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "party_elem_atk",
        "element": "Fire",
    },

    # --- 3. Carrying Capacity Helpers ---
    "PinkCat": {
        "levels": ["+50", "+60", "+70", "+80", "+100"],
        "type": "capacity",
    },
    "PlantSloth": {
        "levels": ["+100", "+110", "+120", "+130", "+150"],
        "type": "capacity",
    },
    "PlantSloth_Flower": {
        "levels": ["+100", "+110", "+120", "+130", "+150"],
        "type": "capacity",
    },
    "KingAlpaca": {
        "levels": ["+100", "+110", "+120", "+130", "+150"],
        "type": "capacity",
    },
    "KingAlpaca_Ice": {
        "levels": ["+100", "+110", "+120", "+130", "+150"],
        "type": "capacity",
    },
    "Yeti": {
        "levels": ["+120", "+130", "+140", "+150", "+170"],
        "type": "capacity",
    },
    "Yeti_Grass": {
        "levels": ["+120", "+130", "+140", "+150", "+170"],
        "type": "capacity",
    },
    "MoonBeetle": {
        "levels": ["+80", "+90", "+100", "+110", "+130"],
        "type": "capacity",
    },

    # --- 3b. Weight Reducers on Specific Materials ---
    "TentacleTurtle": {
        "levels": ["10%", "15%", "20%", "25%", "30%"],
        "type": "weight_reduce",
    },
    "TentacleTurtle_Ground": {
        "levels": ["10%", "15%", "20%", "25%", "30%"],
        "type": "weight_reduce",
    },

    # --- 4. Drop Rate Boosters ---
    "Vaelet": {
        "levels": ["40%", "48%", "56%", "68%", "80%"],
        "type": "drop",
        "element": "Ground",
    },
    "Cryolinx": {
        "levels": ["40%", "48%", "56%", "68%", "80%"],
        "type": "drop",
        "element": "Dragon",
    },
    "Elphidran": {
        "levels": ["40%", "48%", "56%", "68%", "80%"],
        "type": "drop",
        "element": "Dark",
    },
    "Elphidran_Aqua": {
        "levels": ["40%", "48%", "56%", "68%", "80%"],
        "type": "drop",
        "element": "Fire",
    },
    "Faleris": {
        "levels": ["40%", "48%", "56%", "68%", "80%"],
        "type": "drop",
        "element": "Ice",
    },
    "Penking": {
        "levels": ["40%", "48%", "56%", "68%", "80%"],
        "type": "drop",
        "element": "Fire",
    },
    "Katress": {
        "levels": ["40%", "48%", "56%", "68%", "80%"],
        "type": "drop",
        "element": "Neutral",
    },
    "Katress_Dark": {
        "levels": ["40%", "48%", "56%", "68%", "80%"],
        "type": "drop",
        "element": "Normal",
    },
    "Blazehowl": {
        "levels": ["40%", "48%", "56%", "68%", "80%"],
        "type": "drop",
        "element": "Grass",
    },
    "Blazehowl_Dark": {
        "levels": ["40%", "48%", "56%", "68%", "80%"],
        "type": "drop",
        "element": "Neutral",
    },

    # --- 5. Active Healers & Life Steal ---
    "FlowerPrincess": {
        "levels": ["1000 HP", "1300 HP", "1600 HP", "2000 HP", "2500 HP"],
        "type": "heal",
    },
    "FlowerPrincess_Dark": {
        "levels": ["1000 HP", "1300 HP", "1600 HP", "2000 HP", "2500 HP"],
        "type": "heal",
    },
    "FlowerGirl": {
        "levels": ["400 HP", "500 HP", "600 HP", "700 HP", "800 HP"],
        "type": "heal",
    },
    "Elephant": {
        "levels": ["200 HP", "260 HP", "320 HP", "400 HP", "500 HP"],
        "type": "heal",
    },
    "PinkLizard": {
        "levels": ["6%", "8%", "10%", "13%", "16%"],
        "type": "life_steal",
    },
}

# Aliases matching internal names or display names
SPECIES_ALIASES: dict[str, str] = {
    "gildane": "GoldenHorse",
    "goldenhorse": "GoldenHorse",
    "gobfin": "SharkMan",
    "gobfin ignis": "SharkMan_Fire",
    "gobfin_fire": "SharkMan_Fire",
    "chillet": "IceDeer",
    "chillet ignis": "IceDeer_Fire",
    "chillet_fire": "IceDeer_Fire",
    "ragnahawk": "FireKirin",
    "firekirin": "FireKirin",
    "pyrin": "RedArmorBird",
    "redarmorbird": "RedArmorBird",
    "pyrin noct": "DarkArmorBird",
    "pyrin_noct": "DarkArmorBird",
    "darkarmorbird": "DarkArmorBird",
    "beakon": "ThunderBird",
    "beakon cryst": "ThunderBird_Ice",
    "beakon_cryst": "ThunderBird_Ice",
    "thunderbird": "ThunderBird",
    "thunderbird_ice": "ThunderBird_Ice",
    "helzephyr": "HadesBird",
    "helzephyr lux": "HadesBird_Electric",
    "helzephyr_lux": "HadesBird_Electric",
    "hadesbird": "HadesBird",
    "hadesbird_electric": "HadesBird_Electric",
    "azurobe": "BlueDragon",
    "azurobe cryst": "BlueDragon_Ice",
    "azurobe_cryst": "BlueDragon_Ice",
    "bluedragon": "BlueDragon",
    "bluedragon_ice": "BlueDragon_Ice",
    "frostallion": "IceHorse",
    "frostallion noct": "IceHorse_Dark",
    "frostallion_noct": "IceHorse_Dark",
    "icehorse": "IceHorse",
    "icehorse_dark": "IceHorse_Dark",
    "mossanda": "GrassPanda",
    "mossanda lux": "GrassPanda_Electric",
    "mossanda_lux": "GrassPanda_Electric",
    "grasspanda": "GrassPanda",
    "grasspanda_electric": "GrassPanda_Electric",
    "verdash": "GrassRabbitMan",
    "grassrabbitman": "GrassRabbitMan",
    "anubis": "Anubis",
    "knocklem": "WingGolem",
    "knocklem ignis": "WingGolem_Fire",
    "knocklem_ignis": "WingGolem_Fire",
    "winggolem": "WingGolem",
    "winggolem_fire": "WingGolem_Fire",
    "relaxaurus": "LazyDragon",
    "relaxaurus lux": "LazyDragon_Electric",
    "relaxaurus_lux": "LazyDragon_Electric",
    "lazydragon": "LazyDragon",
    "lazydragon_electric": "LazyDragon_Electric",
    "digtoise": "TentacleTurtle",
    "tentacleturtle": "TentacleTurtle",
    "selyne": "MoonQueen",
    "moonqueen": "MoonQueen",
    "warsect": "HerculesBeetle",
    "warsect terra": "HerculesBeetle_Ground",
    "warsect_terra": "HerculesBeetle_Ground",
    "herculesbeetle": "HerculesBeetle",
    "herculesbeetle_ground": "HerculesBeetle_Ground",
    "menasting": "DarkScorpion",
    "menasting terra": "DarkScorpion_Ground",
    "menasting_terra": "DarkScorpion_Ground",
    "darkscorpion": "DarkScorpion",
    "darkscorpion_ground": "DarkScorpion_Ground",
    "prixter": "ScorpionMan",
    "prixter lux": "ScorpionMan_Electric",
    "prixter_lux": "ScorpionMan_Electric",
    "scorpionman": "ScorpionMan",
    "scorpionman_ground": "ScorpionMan_Ground",
    "scorpionman_electric": "ScorpionMan_Electric",
    "jormuntide": "Umihebi",
    "jormuntide ignis": "Umihebi_Fire",
    "jormuntide_ignis": "Umihebi_Fire",
    "umihebi": "Umihebi",
    "umihebi_fire": "Umihebi_Fire",
    "cattiva": "PinkCat",
    "pinkcat": "PinkCat",
    "broncherry": "PlantSloth",
    "broncherry aqua": "PlantSloth_Flower",
    "broncherry_aqua": "PlantSloth_Flower",
    "plantsloth": "PlantSloth",
    "plantsloth_flower": "PlantSloth_Flower",
    "kingpaca": "KingAlpaca",
    "ice kingpaca": "KingAlpaca_Ice",
    "ice_kingpaca": "KingAlpaca_Ice",
    "kingalpaca": "KingAlpaca",
    "kingalpaca_ice": "KingAlpaca_Ice",
    "wumpo": "Yeti",
    "wumpo botan": "Yeti_Grass",
    "wumpo_botan": "Yeti_Grass",
    "yeti": "Yeti",
    "yeti_grass": "Yeti_Grass",
    "lunasect": "MoonBeetle",
    "moonbeetle": "MoonBeetle",
    "vaelet": "Vaelet",
    "cryolinx": "Cryolinx",
    "elphidran": "Elphidran",
    "elphidran aqua": "Elphidran_Aqua",
    "elphidran_aqua": "Elphidran_Aqua",
    "faleris": "Faleris",
    "penking": "Penking",
    "katress": "Katress",
    "katress ignis": "Katress_Dark",
    "katress_ignis": "Katress_Dark",
    "blazehowl": "Blazehowl",
    "blazehowl noct": "Blazehowl_Dark",
    "blazehowl_noct": "Blazehowl_Dark",
    "lyleen": "FlowerPrincess",
    "lyleen noct": "FlowerPrincess_Dark",
    "lyleen_noct": "FlowerPrincess_Dark",
    "flowerprincess": "FlowerPrincess",
    "flowerprincess_dark": "FlowerPrincess_Dark",
    "petallia": "FlowerGirl",
    "flowergirl": "FlowerGirl",
    "teafant": "Elephant",
    "elephant": "Elephant",
    "lovander": "PinkLizard",
    "pinklizard": "PinkLizard",
    "rooby": "FlameTiger",
    "flametiger": "FlameTiger",
    "kelpsea": "WaterKelp",
    "kelpsea ignis": "WaterKelp_Fire",
    "kelpsea_ignis": "WaterKelp_Fire",
    "waterkelp": "WaterKelp",
    "waterkelp_fire": "WaterKelp_Fire",
    "sparkit": "ElecCat",
    "eleccat": "ElecCat",
    "bristla": "ThornHedgehog",
    "thornhedgehog": "ThornHedgehog",
    "foxcicle": "IceFox",
    "icefox": "IceFox",
    "dumud": "MudMan",
    "mudman": "MudMan",
    "hoocrates": "DarkOwl",
    "darkowl": "DarkOwl",
    "cremis": "FluffySheep",
    "fluffysheep": "FluffySheep",
    "ribbuny": "CuteRabbit",
    "cuterabbit": "CuteRabbit",
}


def sanitize_markup_elements(text: Optional[str], pal_name: str = "Pal") -> str:
    """Replaces rich text XML tags with canonical elements and entity names.

    E.g.: <uiCommon id=|COMMON_ELEMENT_NAME_Earth| style=|Elem_Ground|/> -> Ground
    """
    if not text:
        return ""

    t = str(text)

    # 1. Resolve localized element names
    for tag_key, elem_name in ELEMENT_TAG_MAP.items():
        pattern = re.compile(rf"<uiCommon id=\|{tag_key}\|[^>]*/>", re.IGNORECASE)
        t = pattern.sub(f" {elem_name} ", t)
        # Also catch icon tags with element in name
        elem_suffix = tag_key.replace("COMMON_ELEMENT_NAME_", "")
        icon_pattern = re.compile(rf"<img id=\|ElemIcon_{elem_suffix}\|[^>]*/>", re.IGNORECASE)
        t = icon_pattern.sub("", t)

    # 2. General element tag fallback (e.g. id=|ElemIcon_Ground| or id=|COMMON_ELEMENT_NAME_...|)
    def _elem_match_sub(m: re.Match) -> str:
        tag_id = m.group(1).upper()
        if tag_id in ELEMENT_TAG_MAP:
            return f" {ELEMENT_TAG_MAP[tag_id]} "
        for k, v in ELEMENT_TAG_MAP.items():
            if k in tag_id:
                return f" {v} "
        return " "

    t = re.sub(r"<uiCommon id=\|([^|]+)\|[^>]*/>", _elem_match_sub, t)

    # 3. Resolve Pal & Item placeholders
    t = re.sub(r"<characterName id=\|.*?\|/>", pal_name, t)
    t = re.sub(r"<itemName id=\|([^|]+)\|[^>]*/>", r"\1", t)

    # 4. Clean formatting/status tags
    t = re.sub(r"</?[^>]+>", "", t)

    # 5. Strip ReferenceMsgId dev tags (both [] and {})
    t = re.sub(r"\[ReferenceMsgId_[^\]]+\]", "", t)
    t = re.sub(r"\{ReferenceMsgId_[^}]+\}", "", t)

    # 6. Fix common corrupted UTF-8 punctuation (e.g. â€™ -> ')
    t = t.replace("â€™", "'").replace("’", "'").replace("‘", "'")
    t = t.replace("â€œ", '"').replace("â€", '"').replace("“", '"').replace("”", '"')
    t = t.replace("\ufffd", "'")

    # 7. Normalize whitespace and punctuation spacing
    cleaned = " ".join(t.replace("\r", " ").replace("\n", " ").split())
    cleaned = re.sub(r"\s+([.,!?:;%])", r"\1", cleaned)
    return cleaned


# Default context-aware scaling tiers [Lv1, Lv2, Lv3, Lv4, Lv5] (stars 0 to 4)
DEFAULT_COMBAT_BUFF_SCALING = ["10%", "11%", "13%", "16%", "20%"]
DEFAULT_DROP_SCALING = ["40%", "48%", "56%", "68%", "80%"]
DEFAULT_DEFENSE_SCALING = ["10%", "11%", "13%", "16%", "20%"]
DEFAULT_SPEED_SCALING = ["5%", "6%", "7%", "8%", "10%"]
DEFAULT_MOUNT_INFUSION_SCALING = ["50%", "55%", "60%", "75%", "100%"]
DEFAULT_CAPACITY_SCALING = ["+50", "+60", "+70", "+80", "+100"]
DEFAULT_ACTIVE_MULT_SCALING = ["1.0", "1.1", "1.2", "1.3", "1.5"]


def get_scaled_partner_skill(
    species_id_or_name: str,
    stars: int = 0,
    base_description: Optional[str] = None,
    skill_name: Optional[str] = None,
    unlock_item: Optional[str] = None,
) -> dict[str, Any]:
    """Computes rank-scaled partner skill metadata and description.

    Args:
        species_id_or_name: Pal internal ID (e.g. 'GoldenHorse') or display name ('Gildane').
        stars: Pal condensation rank (0 to 4 stars).
        base_description: Optional raw description string from database.
        skill_name: Optional localized skill name.
        unlock_item: Optional unlock harness/saddle item name.

    Returns:
        Dictionary containing level (1-5), stars (0-4), description, scaling_range, and meta.
    """
    clean_stars = max(0, min(4, int(stars) if str(stars).isdigit() else 0))
    skill_level = clean_stars + 1  # 0★ -> Lv 1, 1★ -> Lv 2, 2★ -> Lv 3, 3★ -> Lv 4, 4★ -> Lv 5

    # Identify scaling entry
    canon_key = species_id_or_name
    if canon_key not in PARTNER_SKILL_SCALING_TABLE:
        lookup = str(canon_key).lower().strip()
        canon_key = SPECIES_ALIASES.get(lookup, canon_key)
        if canon_key not in PARTNER_SKILL_SCALING_TABLE:
            canon_key = SPECIES_ALIASES.get(lookup.replace(" ", "_"), canon_key)
            if canon_key not in PARTNER_SKILL_SCALING_TABLE:
                canon_key = SPECIES_ALIASES.get(lookup.replace("_", " "), canon_key)

    scaling_info = PARTNER_SKILL_SCALING_TABLE.get(canon_key)

    # Clean the raw/base description first
    desc = sanitize_markup_elements(base_description or "", str(species_id_or_name))

    # If description is missing the element name after "attack type to and", fix it using scaling_info
    if scaling_info and "element" in scaling_info:
        elem = scaling_info["element"]
        if "attack type to and" in desc:
            desc = desc.replace("attack type to and", f"attack type to {elem} and")
        elif "attack type to  and" in desc:
            desc = desc.replace("attack type to  and", f"attack type to {elem} and")

    # Multi-parameter scaling replacement from params map
    has_params = bool(scaling_info and "params" in scaling_info)
    if has_params:
        for p_name, p_levels in scaling_info["params"].items():
            val = p_levels[clean_stars]
            desc = re.sub(rf"\{{{p_name}\}}%?", val, desc)
            desc = re.sub(rf"\[{p_name}\]%?", val, desc)

    scaling_range = None
    curr_value = None

    if scaling_info and "levels" in scaling_info:
        levels = scaling_info["levels"]
        curr_value = levels[clean_stars]
        scaling_range = f"{levels[0]} -> {levels[-1]}"

        # Replace dynamic percentage in description only if specific params were not used
        if not has_params:
            if "%" in curr_value:
                desc = re.sub(
                    r"(increases [^.]+? by\s+)\d+(?:\.\d+)?%",
                    rf"\g<1>{curr_value}",
                    desc,
                    flags=re.IGNORECASE,
                )
                desc = re.sub(
                    r"(\bby\s+)\d+(?:\.\d+)?%",
                    rf"\g<1>{curr_value}",
                    desc,
                    flags=re.IGNORECASE,
                )
                desc = re.sub(
                    r"(efficiency by\s+)\d+(?:\.\d+)?%",
                    rf"\g<1>{curr_value}",
                    desc,
                    flags=re.IGNORECASE,
                )
                desc = re.sub(
                    r"(\+?)\d+(?:\.\d+)?%\s*(increase|boost|more|damage)",
                    rf"{curr_value} \2",
                    desc,
                    flags=re.IGNORECASE,
                )
            elif "HP" in curr_value:
                desc = re.sub(r"\d+\s*HP", curr_value, desc)
                desc = re.sub(r"\{.*?EffectValue.*?\}", curr_value, desc)
                desc = re.sub(r"\[.*?EffectValue.*?\]", curr_value, desc)
            elif "+" in curr_value:
                desc = re.sub(r"\+\d+", curr_value, desc)
                desc = re.sub(r"\{.*?EffectValue.*?\}", curr_value, desc)
                desc = re.sub(r"\[.*?EffectValue.*?\]", curr_value, desc)

    # Dynamic Contextual Fallback for remaining unresolved tokens and broken placeholders
    # 1. Active skill rank multiplier (e.g. x{ActiveSkillMainValueByRank} -> 1.0 to 1.5)
    mult_val = DEFAULT_ACTIVE_MULT_SCALING[clean_stars]
    desc = re.sub(r"\{ActiveSkillMainValueByRank\}%?", mult_val, desc)
    desc = re.sub(r"\[ActiveSkillMainValueByRank\]%?", mult_val, desc)

    # 2. Drop rate boosts
    drop_val = DEFAULT_DROP_SCALING[clean_stars]
    desc = re.sub(r"drop\s*(\{[^}]+\}|\[[^\]]+\])\s*%?", f"drop {drop_val}", desc, flags=re.IGNORECASE)
    desc = re.sub(r"\bdrop%", f"drop {drop_val}", desc, flags=re.IGNORECASE)
    desc = re.sub(r"\bdrop\s+%", f"drop {drop_val}", desc, flags=re.IGNORECASE)

    # 3. Speed boosts
    speed_val = DEFAULT_SPEED_SCALING[clean_stars]
    desc = re.sub(r"(Speed\s+increases\s+by)\s*(\{[^}]+\}|\[[^\]]+\])\s*%?", rf"\g<1> {speed_val}", desc, flags=re.IGNORECASE)
    desc = re.sub(r"(Speed\s+increases\s+by)\s*%", rf"\g<1> {speed_val}", desc, flags=re.IGNORECASE)

    # 4. Defense boosts
    def_val = DEFAULT_DEFENSE_SCALING[clean_stars]
    desc = re.sub(r"(Defense\s+increases\s+by)\s*(\{[^}]+\}|\[[^\]]+\])\s*%?", rf"\g<1> {def_val}", desc, flags=re.IGNORECASE)
    desc = re.sub(r"(Defense\s+increases\s+by)\s*%", rf"\g<1> {def_val}", desc, flags=re.IGNORECASE)

    # 5. Damage taken reduction
    desc = re.sub(r"take\s*(\{[^}]+\}|\[[^\]]+\])\s*%?\s*less", f"take {def_val} less", desc, flags=re.IGNORECASE)
    desc = re.sub(r"take%\s*less", f"take {def_val} less", desc, flags=re.IGNORECASE)
    desc = re.sub(r"take\s+%\s*less", f"take {def_val} less", desc, flags=re.IGNORECASE)

    # 6. Carrying capacity
    cap_val = DEFAULT_CAPACITY_SCALING[clean_stars]
    desc = re.sub(r"(capacity\s+by)\s*\+?(\{[^}]+\}|\[[^\]]+\])%?", rf"\g<1> {cap_val}", desc, flags=re.IGNORECASE)
    desc = re.sub(r"(capacity\s+by)\s*%", rf"\g<1> {cap_val}", desc, flags=re.IGNORECASE)

    # 7. Attack boost on Mounts vs General Party Buffs
    if "mount" in desc.lower() and "attack" in desc.lower():
        atk_val = curr_value if (curr_value and "%" in curr_value) else DEFAULT_MOUNT_INFUSION_SCALING[clean_stars]
    else:
        atk_val = curr_value if (curr_value and "%" in curr_value) else DEFAULT_COMBAT_BUFF_SCALING[clean_stars]

    desc = re.sub(r"(Attack\s+increases\s+by)\s*(\{[^}]+\}|\[[^\]]+\])\s*%?", rf"\g<1> {atk_val}", desc, flags=re.IGNORECASE)
    desc = re.sub(r"(increases\s+Attack\s+by)\s*(\{[^}]+\}|\[[^\]]+\])\s*%?", rf"\g<1> {atk_val}", desc, flags=re.IGNORECASE)
    desc = re.sub(r"(Attack\s+by)\s*(\{[^}]+\}|\[[^\]]+\])\s*%?", rf"\g<1> {atk_val}", desc, flags=re.IGNORECASE)

    desc = re.sub(r"(Attack\s+increases\s+by)\s*%", rf"\g<1> {atk_val}", desc, flags=re.IGNORECASE)
    desc = re.sub(r"(increases\s+Attack\s+by)\s*%", rf"\g<1> {atk_val}", desc, flags=re.IGNORECASE)
    desc = re.sub(r"(Attack\s+by)\s*%", rf"\g<1> {atk_val}", desc, flags=re.IGNORECASE)

    # 8. Work speed / harvest / other base buffs
    work_val = DEFAULT_COMBAT_BUFF_SCALING[clean_stars]
    desc = re.sub(r"(work\s+speed\s+by)\s*(\{[^}]+\}|\[[^\]]+\])\s*%?", rf"\g<1> {work_val}", desc, flags=re.IGNORECASE)
    desc = re.sub(r"(work\s+speed\s+by)\s*%", rf"\g<1> {work_val}", desc, flags=re.IGNORECASE)
    desc = re.sub(r"(harvest\s+by)\s*(\{[^}]+\}|\[[^\]]+\])\s*%?", rf"\g<1> {work_val}", desc, flags=re.IGNORECASE)
    desc = re.sub(r"(harvest\s+by)\s*%", rf"\g<1> {work_val}", desc, flags=re.IGNORECASE)

    # 9. Generic remaining {Passive...} or [Passive...] or {EffectValue...}
    generic_val = curr_value if (curr_value and "%" in curr_value) else DEFAULT_COMBAT_BUFF_SCALING[clean_stars]
    desc = re.sub(r"\{.*?Passive.*?\}%?", generic_val, desc)
    desc = re.sub(r"\[.*?Passive.*?\]%?", generic_val, desc)
    desc = re.sub(r"\{.*?EffectValue.*?\}%?", generic_val, desc)
    desc = re.sub(r"\[.*?EffectValue.*?\]%?", generic_val, desc)

    # 10. Fix any remaining bare 'by%' or 'by %'
    desc = re.sub(r"\bby\s*%", f"by {generic_val}", desc)
    desc = re.sub(r"\bby%", f"by {generic_val}", desc)
    desc = re.sub(r"\bby(?=\d)", "by ", desc)

    # 11. Dev / Reference tags cleanup
    desc = re.sub(r"\[ReferenceMsgId_[^\]]+\]", "", desc)
    desc = re.sub(r"\{ReferenceMsgId_[^}]+\}", "", desc)
    desc = re.sub(r"\[Reference[^\]]+\]", "", desc)
    desc = re.sub(r"\{Reference[^}]+\}", "", desc)

    # 12. If any remaining {tag}% exists, replace with generic_val
    desc = re.sub(r"\{[^}]+\}%", generic_val, desc)
    # If any remaining {tag} without % exists, strip it
    desc = re.sub(r"\{[^}]+\}", "", desc)
    desc = re.sub(r"\[[^\]]+\]", "", desc)

    # 13. Final safety check: no bare '% preceded by a word character
    desc = re.sub(r"([a-zA-Z])%", rf"\1 {generic_val}", desc)
    desc = " ".join(desc.split())
    desc = re.sub(r"\s+([.,!?:;%])", r"\1", desc)

    if not curr_value:
        curr_value = DEFAULT_COMBAT_BUFF_SCALING[clean_stars]
    if not scaling_range:
        scaling_range = f"{DEFAULT_COMBAT_BUFF_SCALING[0]} -> {DEFAULT_COMBAT_BUFF_SCALING[-1]}"

    return {
        "name": skill_name,
        "level": skill_level,
        "stars": clean_stars,
        "description": desc,
        "scaling_range": scaling_range,
        "current_value": curr_value,
        "unlock_item": unlock_item,
    }
