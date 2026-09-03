# Palopedix Database Utilities & Text Normalizers
import re
from typing import Optional, Any

def clean_species_name(species: str) -> str:
    """Normalize species name by stripping prefixes like 'boss_'."""
    if not species:
        return ""
    sp = str(species).strip()
    if sp.lower().startswith("boss_"):
        return sp[5:]
    return sp

def transform_icon_path(path: Optional[str]) -> Optional[str]:
    """Transform internal Unreal Engine asset path to local web asset path."""
    if not path:
        return None
    # If already a web path, return as is
    if path.startswith("/assets/") or path.startswith("http"):
        return path
    
    # Extract asset name from UE path: /Game/Pal/Texture/PalIcon/T_Anubis_icon.T_Anubis_icon -> /assets/pals/T_Anubis_icon.png
    parts = path.split(".")
    base_name = parts[-1] if len(parts) > 1 else path.split("/")[-1]
    if base_name.startswith("T_"):
        base_name = base_name[2:]
    if base_name.endswith("_icon"):
        base_name = base_name[:-5]
        
    return f"/assets/pals/{base_name}.png"

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

def categorize_passive_source(name: str, p_id: str, category: Optional[str]) -> str:
    """Categorize the origin source of a passive skill."""
    name_l = name.lower()
    if 'legend' in name_l or 'emperor' in name_l or 'divine dragon' in name_l:
        return 'Legendary'
    if 'mutation' in name_l or (p_id and 'mutation' in p_id.lower()):
        return 'Mutation'
    if 'world tree' in name_l or (p_id and 'worldtree' in p_id.lower()):
        return 'World Tree'
    if 'equipment' in name_l or (p_id and 'equip' in p_id.lower()):
        return 'Equipment'
    return 'Pals'

def enrich_passive_skill(skill_dict: dict[str, Any]) -> dict[str, Any]:
    """Enrich a skill record with aptitude and source metadata."""
    if not skill_dict:
        return skill_dict
    s_name = skill_dict.get('name', '')
    s_id = skill_dict.get('id', '')
    s_cat = skill_dict.get('category', '')
    
    skill_dict['aptitude'] = calculate_aptitude(s_name, s_id, s_cat)
    if skill_dict.get('type') == 'Passive':
        skill_dict['source'] = categorize_passive_source(s_name, s_id, s_cat)
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
