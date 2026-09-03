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
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Electric",
        "type": "infusion",
    },
    "ThunderBird_Ice": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Ice",
        "type": "infusion",
    },
    "DarkScorpion": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Dark",
        "type": "infusion",
    },
    "DarkScorpion_Electric": {
        "levels": ["50%", "55%", "60%", "75%", "100%"],
        "element": "Electric",
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
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "combat_def",
    },
    "HerculesBeetle_Ground": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "combat_def",
    },
    "ScorpionMan": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "combat_def",
    },
    "ScorpionMan_Ground": {
        "levels": ["10%", "11%", "13%", "16%", "20%"],
        "type": "combat_def",
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
    "chillet": "IceDeer",
    "chillet ignis": "IceDeer_Fire",
    "ragnahawk": "FireKirin",
    "pyrin": "RedArmorBird",
    "pyrin noct": "DarkArmorBird",
    "beakon": "ThunderBird",
    "helzephyr": "DarkScorpion",
    "helzephyr lux": "DarkScorpion_Electric",
    "azurobe": "WaterDragon",
    "frostallion": "IceHorse",
    "frostallion noct": "IceHorse_Dark",
    "verdash": "GrassPanda",
    "anubis": "Anubis",
    "knocklem": "WingGolem",
    "knocklem ignis": "WingGolem_Fire",
    "winggolem": "WingGolem",
    "winggolem_fire": "WingGolem_Fire",
    "relaxaurus": "LazyDragon",
    "relaxaurus lux": "LazyDragon_Electric",
    "lazydragon": "LazyDragon",
    "lazydragon_electric": "LazyDragon_Electric",
    "digtoise": "TentacleTurtle",
    "tentacleturtle": "TentacleTurtle",
    "selyne": "MoonQueen",
    "moonqueen": "MoonQueen",
    "warsect": "HerculesBeetle",
    "herculesbeetle": "HerculesBeetle",
    "menasting": "ScorpionMan",
    "menasting terra": "ScorpionMan_Ground",
    "cattiva": "PinkCat",
    "broncherry": "PlantSloth",
    "broncherry aqua": "PlantSloth_Flower",
    "kingpaca": "KingAlpaca",
    "ice kingpaca": "KingAlpaca_Ice",
    "wumpo": "Yeti",
    "wumpo botan": "Yeti_Grass",
    "lunasect": "MoonBeetle",
    "vaelet": "Vaelet",
    "cryolinx": "Cryolinx",
    "elphidran": "Elphidran",
    "elphidran aqua": "Elphidran_Aqua",
    "faleris": "Faleris",
    "penking": "Penking",
    "katress": "Katress",
    "katress ignis": "Katress_Dark",
    "blazehowl": "Blazehowl",
    "blazehowl noct": "Blazehowl_Dark",
    "lyleen": "FlowerPrincess",
    "lyleen noct": "FlowerPrincess_Dark",
    "petallia": "FlowerGirl",
    "teafant": "Elephant",
    "lovander": "PinkLizard",
    "rooby": "FlameTiger",
    "kelpsea": "WaterKelp",
    "kelpsea ignis": "WaterKelp_Fire",
    "sparkit": "ElecCat",
    "bristla": "ThornHedgehog",
    "foxcicle": "IceFox",
    "dumud": "MudMan",
    "hoocrates": "DarkOwl",
    "cremis": "FluffySheep",
    "ribbuny": "CuteRabbit",
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

    # 5. Strip all ReferenceMsgId and raw Unreal dev tags (both [] and {})
    t = re.sub(r"\[ReferenceMsgId_[^\]]+\]", "", t)
    t = re.sub(r"\{ReferenceMsgId_[^}]+\}", "", t)
    t = re.sub(r"\[ReferencePassive[^\]]+\]", "", t)
    t = re.sub(r"\{ReferencePassive[^}]+\}", "", t)
    t = re.sub(r"\[Passive[^\]]+\]", "", t)
    t = re.sub(r"\{Passive[^}]+\}", "", t)

    # 6. Fix common corrupted UTF-8 punctuation (e.g. â€™ -> ')
    t = t.replace("â€™", "'").replace("’", "'").replace("‘", "'")
    t = t.replace("â€œ", '"').replace("â€", '"').replace("“", '"').replace("”", '"')
    t = t.replace("\ufffd", "'")

    # 7. Normalize whitespace and punctuation spacing
    cleaned = " ".join(t.replace("\r", " ").replace("\n", " ").split())
    cleaned = re.sub(r"\s+([.,!?:;%])", r"\1", cleaned)
    return cleaned


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
        lookup = canon_key.lower().strip()
        canon_key = SPECIES_ALIASES.get(lookup, canon_key)

    scaling_info = PARTNER_SKILL_SCALING_TABLE.get(canon_key)

    # Clean the raw/base description first
    desc = sanitize_markup_elements(base_description or "", species_id_or_name)

    # If description is missing the element name after "attack type to and", fix it using scaling_info
    if scaling_info and "element" in scaling_info:
        elem = scaling_info["element"]
        if "attack type to and" in desc:
            desc = desc.replace("attack type to and", f"attack type to {elem} and")
        elif "attack type to  and" in desc:
            desc = desc.replace("attack type to  and", f"attack type to {elem} and")

    scaling_range = None
    curr_value = None

    if scaling_info and "levels" in scaling_info:
        levels = scaling_info["levels"]
        curr_value = levels[clean_stars]
        scaling_range = f"{levels[0]} -> {levels[-1]}"

        # Replace dynamic percentage in description
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
            # Generic catch for unresolved placeholders
            desc = re.sub(r"\{.*?EffectValue.*?\}%?", curr_value, desc)
            desc = re.sub(r"\[.*?EffectValue.*?\]%?", curr_value, desc)
            desc = re.sub(r"\{.*?Passive.*?\}%?", curr_value, desc)
            desc = re.sub(r"\[.*?Passive.*?\]%?", curr_value, desc)
        elif "HP" in curr_value:
            desc = re.sub(r"\d+\s*HP", curr_value, desc)
            desc = re.sub(r"\{.*?EffectValue.*?\}", curr_value, desc)
            desc = re.sub(r"\[.*?EffectValue.*?\]", curr_value, desc)
        elif "+" in curr_value:
            desc = re.sub(r"\+\d+", curr_value, desc)
            desc = re.sub(r"\{.*?EffectValue.*?\}", curr_value, desc)
            desc = re.sub(r"\[.*?EffectValue.*?\]", curr_value, desc)
        # Generic cleanup of any remaining EffectValue tokens
        desc = re.sub(r"\{.*?EffectValue.*?\}", "50", desc)
        desc = re.sub(r"\[.*?EffectValue.*?\]", "50", desc)
        desc = re.sub(r"\{.*?Passive.*?\}", "50", desc)
        desc = re.sub(r"\[.*?Passive.*?\]", "50", desc)

    # Final pass: Strip or interpolate any remaining unresolved curly braces {Tag} or dev brackets [Tag]
    desc = re.sub(r"\{ActiveSkillMainValueByRank\}%?", "100%", desc)
    desc = re.sub(r"\[ActiveSkillMainValueByRank\]%?", "100%", desc)
    desc = re.sub(r"\{ReferenceMsgId_[^}]+\}", "", desc)
    desc = re.sub(r"\[ReferenceMsgId_[^\]]+\]", "", desc)
    desc = re.sub(r"\{[^}]+\}", "", desc)
    desc = re.sub(r"\[Reference[^\]]+\]", "", desc)
    desc = " ".join(desc.split())
    desc = re.sub(r"\s+([.,!?:;%])", r"\1", desc)

    return {
        "name": skill_name,
        "level": skill_level,
        "stars": clean_stars,
        "description": desc,
        "scaling_range": scaling_range,
        "current_value": curr_value,
        "unlock_item": unlock_item,
    }
