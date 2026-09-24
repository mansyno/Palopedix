# Palopedix Database Utilities & Text Normalizers
import re
from typing import Optional, Any

from palengine.config import get_assets_dir

def clean_species_name(species: str) -> str:
    """Normalize species name by stripping prefixes like 'boss_'."""
    if not species:
        return ""
    sp = str(species).strip()
    if sp.lower().startswith("boss_"):
        return sp[5:]
    return sp

def transform_icon_path(path: Optional[str]) -> Optional[str]:
    """Converts internal Unreal Engine asset paths or absolute local asset paths into web-accessible URL paths (/assets/...)."""
    if not path:
        return None
    normalized = path.replace("\\", "/")
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        normalized = re.sub(r"/+", "/", normalized)
    if normalized.startswith("/assets/") or normalized.startswith("http://") or normalized.startswith("https://"):
        return normalized

    # Handle local filesystem asset directory
    try:
        assets_dir = get_assets_dir().replace("\\", "/").rstrip("/")
        if normalized.lower().startswith(assets_dir.lower()):
            rel_path = normalized[len(assets_dir):]
            if not rel_path.startswith("/"):
                rel_path = "/" + rel_path
            return f"/assets{rel_path}"
    except Exception:
        pass

    if "palworld_assets" in normalized.lower():
        idx = normalized.lower().find("palworld_assets")
        rel_path = normalized[idx + len("palworld_assets"):]
        if not rel_path.startswith("/"):
            rel_path = "/" + rel_path
        return f"/assets{rel_path}"

    # Extract asset name from UE path: /Game/Pal/Texture/PalIcon/T_Anubis_icon.T_Anubis_icon -> /assets/pals/Anubis.png
    if "/game/" in normalized.lower():
        parts = normalized.split(".")
        base_name = parts[-1] if len(parts) > 1 else normalized.split("/")[-1]
        if base_name.startswith("T_"):
            base_name = base_name[2:]
        if base_name.endswith("_icon"):
            base_name = base_name[:-5]
        return f"/assets/pals/{base_name}.png"

    return normalized if normalized.startswith("/") else None

def clean_skill_text(text: Optional[str]) -> Optional[str]:
    """Clean rich text formatting tags and resolve elements properly from skill descriptions."""
    if not text:
        return None
    from palengine.analytics.partner_skill_scaling import sanitize_markup_elements
    cleaned = sanitize_markup_elements(text)
    return cleaned if cleaned else None

def calculate_aptitude(name: str, p_id: str, category: Optional[str]) -> dict[str, Any]:
    """Calculate passive aptitude tier and visual badge colors."""
    name_lower = name.lower()
    
    # Negative Passives (Red)
    negatives = {
        'slacker', 'downtrodden', 'pacifist', 'bottomless stomach', 'brittle',
        'glutton', 'destructive', 'sadist', 'coward', 'clumsy', 'distracted',
        'unstable', 'dehydrated', 'sloppy'
    }
    if name_lower in negatives or (category and category.lower() == 'negative'):
        return {'tier': -1, 'color': 'red', 'label': 'Negative'}
    
    # Legendary Passives (Legendary Gradient)
    legends = {
        'legend', 'celestial emperor', 'lord of lightning', 'divine dragon',
        'siren of the void', 'eternal flame', 'ice emperor', 'flame emperor',
        'earth emperor', 'spirit emperor', 'emperor', 'holy beast'
    }
    if name_lower in legends or (category and category.lower() == 'legendary'):
        return {'tier': 4, 'color': 'legend', 'label': 'Legendary'}
    
    # Tier 3 / Gold Passives
    gold = {
        'artisan', 'ferocious', 'musclehead', 'swift', 'lucky',
        'work slave', 'vanguard', 'stronghold strategist', 'burly body', 'remarkable',
        'runner', 'workaholic', 'mine foreman', 'logging foreman', 'motivational leader', 'serious'
    }
    if name_lower in gold or (category and category.lower() in ('gold', 'tier3')):
        return {'tier': 3, 'color': 'gold', 'label': 'Tier 3 (Gold)'}
    
    return {'tier': 1, 'color': 'white', 'label': 'Standard'}

def is_pal_passive(p_id: str, name: str) -> bool:
    """Returns True if the passive skill is an authentic Pal passive (not equipment, boss defeat perk, or effigy)."""
    if not p_id or not name or name == "-" or name == "":
        return False
    # Boss defeat rewards (permanent player perks)
    if "BossDefeat" in p_id:
        return False
    # Accessories, rings, and armor equipment
    if "ACC" in p_id or "Equip" in p_id or "Armor" in p_id:
        return False
    # Rings of elemental resistance (item rings: ElementResist_Aqua_1, vs Pal passives: ElementResist_Aqua_1_PAL)
    if p_id.startswith("ElementResist_") and not p_id.endswith("_PAL"):
        return False
    # Lifmunk effigy player capture power
    if p_id.startswith("CaptureLevel_"):
        return False
    # Glider / boots / jump count player perks
    if p_id.startswith("AirDash_") or p_id.startswith("JumpCount_") or p_id.startswith("RideJumpCount_"):
        return False
    # Thermal undershirt / armor temperature resist
    if p_id.startswith("TemperatureResist_"):
        return False
    # Carrying capacity / drop rate accessories
    if p_id.startswith("MaxInventoryWeight_") or p_id.startswith("StonDrop_") or p_id.startswith("WoodDrop_") or p_id.startswith("StonWoodDrop_"):
        return False
    # Sphere launcher modules
    if p_id.startswith("SphereModule_"):
        return False
    # Gym leader / boss specific internal skills
    if p_id.startswith("GYM_"):
        return False
    # Collect items dummy entries
    if p_id.startswith("CollectItem_"):
        return False
    return True


def categorize_passive_source(name: str, p_id: str, category: Optional[str] = None) -> str:
    """Categorize the origin source of a passive skill."""
    if not is_pal_passive(p_id, name):
        p_lower = p_id.lower()
        if "bossdefeat" in p_lower:
            return "Boss Defeat"
        if any(p_lower.startswith(k) for k in ["capturelevel_", "airdash_", "jumpcount_", "ridejumpcount_", "spheremodule_"]):
            return "Player"
        return "Equipment"

    name_l = name.lower()
    id_l = p_id.lower()
    if "worldtree" in id_l or "world tree" in name_l:
        return "World Tree"
    if "mutation" in id_l or "mutation" in name_l:
        return "Mutation"
    if (
        "legend" in name_l
        or "emperor" in name_l
        or "divine dragon" in name_l
        or "lord of " in name_l
        or p_id in ["Legend", "Witch", "EternalFlame", "Invader"]
    ):
        return "Legendary"
    return "Pals"

PASSIVE_SKILL_RESOLVED_TEXT: dict[str, str] = {
    "traineratk_up_1": "10.0% increase in Player Attack.",
    "vanguard": "10.0% increase in Player Attack.",
    "trainerdef_up_1": "10.0% increase in Player Defense.",
    "stronghold strategist": "10.0% increase in Player Defense.",
    "trainerworkspeed_up_1": "25.0% increase in Player Work Speed.",
    "motivational leader": "25.0% increase in Player Work Speed.",
    "trainermining_up1": "25.0% increase in Player Mining Efficiency.",
    "mine foreman": "25.0% increase in Player Mining Efficiency.",
    "trainerlogging_up1": "25.0% increase in Player Logging Efficiency.",
    "logging foreman": "25.0% increase in Player Logging Efficiency.",
    "elementresist_normal_1_pal": "10.0% decrease in incoming Neutral damage.",
    "abnormal": "10.0% decrease in incoming Neutral damage.",
    "elementresist_fire_1_pal": "10.0% decrease in incoming Fire damage.",
    "suntan lover": "10.0% decrease in incoming Fire damage.",
    "elementresist_aqua_1_pal": "10.0% decrease in incoming Water damage.",
    "waterproof": "10.0% decrease in incoming Water damage.",
    "elementresist_thunder_1_pal": "10.0% decrease in incoming Lightning damage.",
    "insulated body": "10.0% decrease in incoming Lightning damage.",
    "elementresist_leaf_1_pal": "10.0% decrease in incoming Grass damage.",
    "botanical barrier": "10.0% decrease in incoming Grass damage.",
    "elementresist_ice_1_pal": "10.0% decrease in incoming Ice damage.",
    "heated body": "10.0% decrease in incoming Ice damage.",
    "elementresist_earth_1_pal": "10.0% decrease in incoming Earth damage.",
    "earthquake resistant": "10.0% decrease in incoming Earth damage.",
    "elementresist_dark_1_pal": "10.0% decrease in incoming Dark damage.",
    "cheery": "10.0% decrease in incoming Dark damage.",
    "elementresist_dragon_1_pal": "10.0% decrease in incoming Dragon damage.",
    "dragonkiller": "10.0% decrease in incoming Dragon damage.",
    "elementboost_normal_1_pal": "10.0% increase in Neutral attack damage.",
    "spirit of zen": "10.0% increase in Neutral attack damage.",
    "elementboost_fire_1_pal": "10.0% increase in Fire attack damage.",
    "pyromaniac": "10.0% increase in Fire attack damage.",
    "elementboost_aqua_1_pal": "10.0% increase in Water attack damage.",
    "hydromaniac": "10.0% increase in Water attack damage.",
    "elementboost_thunder_1_pal": "10.0% increase in Lightning attack damage.",
    "capacitor": "10.0% increase in Lightning attack damage.",
    "elementboost_leaf_1_pal": "10.0% increase in Grass attack damage.",
    "fragrant foliage": "10.0% increase in Grass attack damage.",
    "elementboost_ice_1_pal": "10.0% increase in Ice attack damage.",
    "coldblooded": "10.0% increase in Ice attack damage.",
    "elementboost_earth_1_pal": "10.0% increase in Earth attack damage.",
    "power of gaia": "10.0% increase in Earth attack damage.",
    "elementboost_dark_1_pal": "10.0% increase in Dark attack damage.",
    "veil of darkness": "10.0% increase in Dark attack damage.",
    "elementboost_dragon_1_pal": "10.0% increase in Dragon attack damage.",
    "blood of the dragon": "10.0% increase in Dragon attack damage.",
    "cooltimereduction_up_1": "Active skill cooldown reduction 30.0% Attack +10.0%",
    "serenity": "Active skill cooldown reduction 30.0% Attack +10.0%",
    "cooltimereduction_up_2": "Active skill cooldown reduction 15.0%",
    "impatient": "Active skill cooldown reduction 15.0%",
    "cooltimereduction_up_3": "Active skill cooldown reduction 30.0% Attack +10.0%",
    "tempest fury": "Active skill cooldown reduction 30.0% Attack +10.0%",
    "cooltimereduction_down_1": "Active skill cooldown extension -15.0%",
    "easygoing": "Active skill cooldown extension -15.0%",
    "stamina_up_1": "Max Stamina +50.0% *This effect is only valid for rideable pals.",
    "infinite stamina": "Max Stamina +50.0% *This effect is only valid for rideable pals.",
    "stamina_up_2": "Max Stamina +25.0% *This effect is only valid for rideable pals.",
    "fit as a fiddle": "Max Stamina +25.0% *This effect is only valid for rideable pals.",
    "stamina_up_3": "Max Stamina +75.0% *This effect is only valid for rideable pals.",
    "eternal engine": "Max Stamina +75.0% *This effect is only valid for rideable pals.",
    "stamina_down_1": "Max Stamina -25.0% *This effect is only valid for rideable pals.",
    "sickly": "Max Stamina -25.0% *This effect is only valid for rideable pals.",
    "saleprice_up_1": "Increases the value of items when sold by +5.0%",
    "noble": "Increases the value of items when sold by +5.0%",
    "saleprice_up_2": "Increases the value of items when sold by +3.0%",
    "fine furs": "Increases the value of items when sold by +3.0%",
    "saleprice_down_1": "Decreases the value of items when sold by -10.0%",
    "shabby": "Decreases the value of items when sold by -10.0%",
    "alien": "Attack +10.0% Fire damage reduction 15.0% Lightning damage reduction 15.0%",
    "otherworldly cells": "Attack +10.0% Fire damage reduction 15.0% Lightning damage reduction 15.0%",
    "test_palegg_hatchingspeed_up": "When assigned to a Breeding Farm, breeding speed is increased by 100.0%.",
    "philanthropist": "When assigned to a Breeding Farm, breeding speed is increased by 100.0%.",
    "vampire": "Absorbs a portion of the damage dealt to restore Health. Does not sleep at night and continues to work.",
    "vampiric": "Absorbs a portion of the damage dealt to restore Health. Does not sleep at night and continues to work.",
    "nushi": "20.0% increase to Water attack damage 20.0% increase to Ice attack damage 20.0% increase to Defense.",
    "lunker": "20.0% increase to Water attack damage 20.0% increase to Ice attack damage 20.0% increase to Defense.",
    "gym_name_meadow": "Attack +20.0% Movement Speed increases 10.0%",
    "rayne syndicate boss": "Attack +20.0% Movement Speed increases 10.0%",
    "worldtree_atk": "Attack +50.0% Defense -30.0% World Tree resources will not vanish when approached.",
    "twin-edged holy blade": "Attack +50.0% Defense -30.0% World Tree resources will not vanish when approached.",
    "worldtree_def": "Defense +50.0% Attack -30.0% World Tree resources will not vanish when approached.",
    "sanctified meat shield": "Defense +50.0% Attack -30.0% World Tree resources will not vanish when approached.",
    "worldtree_craftspeed": "Work Speed +90.0% SAN decreases +15.0% faster. World Tree resources will not vanish when approached.",
    "demon's hand": "Work Speed +90.0% SAN decreases +15.0% faster. World Tree resources will not vanish when approached.",
    "demons hand": "Work Speed +90.0% SAN decreases +15.0% faster. World Tree resources will not vanish when approached.",
    "worldtree_fullstomach": "Decrease Hunger depletion rate by +50.0% Max Health -20.0% World Tree resources will not vanish when approached.",
    "world tree's bounty": "Decrease Hunger depletion rate by +50.0% Max Health -20.0% World Tree resources will not vanish when approached.",
    "world tree seedbed": "Decrease Hunger depletion rate by +50.0% Max Health -20.0% World Tree resources will not vanish when approached.",
    "worldtree_sanity": "SAN drops +50.0% slower. Work Speed -20.0% World Tree resources will not vanish when approached.",
    "hermit sage": "SAN drops +50.0% slower. Work Speed -20.0% World Tree resources will not vanish when approached.",
    "worldtree_movespeed": "Movement Speed +50.0% Increases Hunger depletion rate by +15.0% World Tree resources will not vanish when approached.",
    "dimensional leap": "Movement Speed +50.0% Increases Hunger depletion rate by +15.0% World Tree resources will not vanish when approached.",
    "worldtree_atk_def": "Attack +40.0% Defense +20.0% Max Health -50.0% World Tree resources will not vanish when approached.",
    "god of destruction": "Attack +40.0% Defense +20.0% Max Health -50.0% World Tree resources will not vanish when approached.",
    "mutationpal_babysitter": "While at a base, increases egg production speed by +30.0% and incubation speed by +30.0% for Pals assigned to a Breeding Farm.",
    "babysitter": "While at a base, increases egg production speed by +30.0% and incubation speed by +30.0% for Pals assigned to a Breeding Farm.",
    "mutationpal_mutant": "Pal and Player Auto Health Regeneration Rate +50.0% Defense +25.0% Immune to Poison Damage Immune to Burn Damage",
    "idiosyncratic": "Pal and Player Auto Health Regeneration Rate +50.0% Defense +25.0% Immune to Poison Damage Immune to Burn Damage",
    "mutationpal_immortal": "Absorbs 5.0% of damage dealt and restores Health. Pal Auto Health Regeneration Rate +100.0% Attack +15.0%",
    "immortality": "Absorbs 5.0% of damage dealt and restores Health. Pal Auto Health Regeneration Rate +100.0% Attack +15.0%",
    "deffence_up2": "Defense +20.0% Immune to Flinch",
    "burly body": "Defense +20.0% Immune to Flinch",
    "deffence_up2_2": "Defense +20.0% Immune to Knockback",
    "heavyweight": "Defense +20.0% Immune to Knockback",
    "deffence_up3": "Defense +30.0% Immune to Flinch Immune to Knockback",
    "diamond body": "Defense +30.0% Immune to Flinch Immune to Knockback",
    "legend": "Attack +20.0% Defense +20.0% Movement Speed increases 20.0%",
}

def resolve_passive_placeholders(text: Optional[str], p_id: str = "", name: str = "") -> Optional[str]:
    """Resolves {EffectValue} placeholders in passive skill texts using canonical game parameter values."""
    if not text and not p_id and not name:
        return text
    has_placeholder = bool(text and ("{" in text or "EffectValue" in text))
    pid_key = str(p_id or "").strip().lower()
    name_key = str(name or "").strip().lower()

    resolved = PASSIVE_SKILL_RESOLVED_TEXT.get(pid_key) or PASSIVE_SKILL_RESOLVED_TEXT.get(name_key)
    if resolved:
        if not text or has_placeholder:
            return resolved

    if text and has_placeholder:
        cleaned = re.sub(r"\{.*?EffectValue.*?\}%?", "", text)
        cleaned = re.sub(r"\[.*?EffectValue.*?\]%?", "", cleaned)
        cleaned = " ".join(cleaned.split())
        return cleaned

    return text

def enrich_passive_skill(skill_dict: dict[str, Any]) -> dict[str, Any]:
    """Enrich a skill record with aptitude, source metadata, and resolved parameter values."""
    if not skill_dict:
        return skill_dict
    s_name = skill_dict.get('name', '')
    s_id = skill_dict.get('id', '')
    s_cat = skill_dict.get('category', '')
    
    skill_dict['aptitude'] = calculate_aptitude(s_name, s_id, s_cat)
    if skill_dict.get('type') == 'Passive':
        skill_dict['source'] = categorize_passive_source(s_name, s_id, s_cat)

    desc = skill_dict.get('description')
    mod = skill_dict.get('stat_modifier')
    if desc or mod or s_id or s_name:
        desc = resolve_passive_placeholders(desc, s_id, s_name)
        mod = resolve_passive_placeholders(mod, s_id, s_name)
        if not mod and desc:
            mod = desc
        if not desc and mod:
            desc = mod
        skill_dict['description'] = desc
        skill_dict['stat_modifier'] = mod

    return skill_dict

def normalize_passives(passives_raw: list) -> list[dict[str, Any]]:
    """Normalize a list of passive identifiers/dictionaries into a standardized list of dicts."""
    if not passives_raw:
        return []
    normalized = []
    for p in passives_raw:
        if isinstance(p, dict):
            normalized.append({
                'id': p.get('id') or p.get('name', ''),
                'name': p.get('name') or p.get('id', ''),
                'rank': p.get('rank', 1),
                'stat_modifier': p.get('stat_modifier', ''),
                'description': p.get('description', ''),
                'aptitude': p.get('aptitude') or calculate_aptitude(p.get('name', ''), p.get('id', ''), '')
            })
        elif isinstance(p, str):
            normalized.append({
                'id': p,
                'name': p,
                'rank': 1,
                'stat_modifier': '',
                'description': '',
                'aptitude': calculate_aptitude(p, p, '')
            })
    return normalized


NON_PLAYABLE_SPECIES = {
    # 9 Tower Boss Entities
    "zoe & grizzbolt", "lily & lyleen", "marcus & faleris", "axel & orserk",
    "victor & shadowbeak", "saya & selyne", "auri & shaolong", "bjorn & bastigor", "zenara & astralym",
    # 6 Crossover Slimes
    "green slime", "blue slime", "red slime", "purple slime", "illuminant slime", "rainbow slime",
    # 7 Terraria Event Monsters
    "enchanted sword", "cave bat", "illuminant bat", "eye of cthulhu", "demon eye", "true eye of cthulhu", "moon lord",
    # 3 Cut / Unreleased NPCs
    "boltmane", "dragostrophe", "pidf rider", "eleclion", "blackfurdragon", "police_palride",
}


def is_playable_pal(pal_dict: dict[str, Any]) -> bool:
    """Returns True if the Pal is one of the 291 genuine playable in-game Pals."""
    dn = str(pal_dict.get("display_name", "")).strip().lower()
    in_name = str(pal_dict.get("internal_name", "")).strip().lower()
    if "&" in dn or "boss" in in_name or in_name.startswith("police_") or in_name.startswith("yakushima") or in_name.startswith("raid_"):
        return False
    return dn not in NON_PLAYABLE_SPECIES and in_name not in NON_PLAYABLE_SPECIES

