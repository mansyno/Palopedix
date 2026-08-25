"""SQLite database engine module for PalEngine.

Integrates static game metadata and dynamic save game instance data.
Supports both Palworld 1.0+ SQLite master database ('palworld_db') and legacy JSON datasets ('legacy').
"""

import json
import os
import re
import sqlite3
from typing import Any, Optional

from palengine.world_manager import discover_worlds, get_world_by_id
from palengine.config import (
    get_assets_dir,
    get_palworld_db_path,
    get_static_data_source,
)
from palengine.parser.extract_bases import extract_bases
from palengine.parser.extract_pals import extract_pals
from palengine.parser.extract_items import extract_items
from palengine.parser.extract_players import extract_players


STRUCTURE_ALIAS_MAP = {
    # Farm / Plantation Blocks
    "farmblockv2_berries": "BerryGarden",
    "farmblock_berries": "BerryGarden",
    "farmblockv2_lettuce": "LettuceGarden",
    "farmblock_lettuce": "LettuceGarden",
    "farmblockv2_tomato": "TomatoGarden",
    "farmblock_tomato": "TomatoGarden",
    "farmblockv2_wheet": "WheatGarden",
    "farmblock_wheat": "WheatGarden",
    "ancientfarmblock": "AncientFarmBlock",
    # Medicine Facilities
    "medicinefacility_01": "MedicineFactory_Primitive",
    "medicinefacility_02": "MedicineFactory_Electric",
    "medicinefacility": "MedicineFactory_Primitive",
    # Cooking / Kitchen
    "cookingstove": "BlastFurnace",
    "electrickitchen": "BlastFurnace2",
    "campfire": "BlastFurnace",
    # Factories & Benches
    "factory_hard_01": "WeaponFactory_Clean_01",
    "factory_hard_02": "WeaponFactory_Clean_02",
    "factory_hard_03": "WeaponFactory_Clean_03",
    "workbench": "WorkBench",
    "workbench_primitive": "WorkBench_Primitive",
    "workbench_quality": "WorkBench_Quality",
    "workbench_skillunlock": "WorkBench_SkillUnlock",
    # Natural Terrain Resource Nodes
    "natural_copperore": "StonePit",
    "natural_stone": "StonePit",
    "natural_coal": "StonePit",
    "natural_sulfur": "StonePit",
    "natural_quartz": "StonePit",
    "natural_wood": "StationDeforest",
    "natural_wood_fine": "StationDeforest",
}


def transform_icon_path(path: Optional[str]) -> Optional[str]:
    """Converts absolute local asset file paths into web-accessible URL paths (/assets/...)."""
    if not path:
        return None
    normalized = path.replace("\\", "/")
    assets_dir = get_assets_dir().replace("\\", "/").rstrip("/")
    if normalized.lower().startswith(assets_dir.lower()):
        rel_path = normalized[len(assets_dir):]
        if not rel_path.startswith("/"):
            rel_path = "/" + rel_path
        return f"/assets{rel_path}"
    elif "palworld_assets" in normalized.lower():
        idx = normalized.lower().find("palworld_assets")
        rel_path = normalized[idx + len("palworld_assets"):]
        if not rel_path.startswith("/"):
            rel_path = "/" + rel_path
        return f"/assets{rel_path}"
    return normalized if (normalized.startswith("/") or normalized.startswith("http")) else None
PASSIVE_DESCRIPTIONS_MAP: dict[str, str] = {
    "artisan": "Work Speed +50%",
    "serious": "Work Speed +20%",
    "work slave": "Work Speed +30%, Attack -30%",
    "clumsy": "Work Speed -10%",
    "slacker": "Work Speed -30%",
    "ferocious": "Attack +20%",
    "musclehead": "Attack +30%, Work Speed -50%",
    "aggressive": "Attack +10%, Defense -20%",
    "coward": "Attack -10%",
    "pacifist": "Attack -20%",
    "sadist": "Attack +15%, Defense -15%",
    "burly body": "Defense +20%",
    "hard skin": "Defense +10%",
    "brave": "Attack +10%",
    "downtrodden": "Defense -10%",
    "brittle": "Defense -20%",
    "swift": "Movement Speed +30%",
    "runner": "Movement Speed +20%",
    "nimble": "Movement Speed +10%",
    "ace swimmer": "Swimming Speed +15%",
    "king of the waves": "Swimming Speed +30%",
    "vanguard": "Player Attack +10%",
    "stronghold strategist": "Player Defense +10%",
    "motivational leader": "Player Work Speed +25%",
    "mine foreman": "Player Mining Speed +25%",
    "logging foreman": "Player Logging Speed +25%",
    "workaholic": "SAN drops 15% slower",
    "positive thinker": "SAN drops 10% slower",
    "diet lover": "Hunger decreases 15% slower",
    "efficient worker": "Hunger decreases 20% slower",
    "legend": "Attack +20%, Defense +20%, Movement Speed +15%",
    "lucky": "Work Speed +15%, Attack +15%",
    "conceited": "Work Speed +10%, Defense -10%",
    "masochist": "Defense +15%, Attack -15%",
    "glutton": "Hunger drops +10% faster",
    "bottomless stomach": "Hunger drops +15% faster",
    "destructive": "SAN drops +15% faster",
    "destabilized": "SAN drops +10% faster",
    "zen mindset": "SAN drops +15% slower",
    "serenity": "Active Skill Cooldown -30%, Attack +10%",
    "impatient": "Active Skill Cooldown -15%",
    "noble": "Trading price sell +5%, buy -5%",
    "fine coat": "Trading price sell +10%, buy -10%",
    "philanthropist": "Egg incubation time -100%",
    "healing coach": "Player HP recovery speed +25%",
    "wellness watcher": "Player Stamina recovery +25%",
    "reload master": "Player Reload speed +25%",
    "whopper": "Pal Size +15%",
    "easygoing": "Defense -10%, Work Speed +10%",
    "sloppy": "SAN drops +10% faster",
    "shabby": "Max HP -10%",
    "sickly": "SAN drops +15% faster",
    "unstable": "SAN drops +20% faster",
    "hooligan": "Attack +15%, Work Speed -10%",
    "pal_rude": "Attack +15%, Work Speed -10%",
    "blood is fuel": "Absorbs 10% of damage dealt as HP",
    "savior": "Revives fallen player with 50% HP once per battle",
    "abnormal": "10.0% decrease in incoming Neutral damage.",
    "cheery": "10.0% decrease in incoming Dark damage.",
    "dragonkiller": "10.0% increase in Dragon damage.",
    "pyromaniac": "10.0% increase in Fire damage.",
    "hydromaniac": "10.0% increase in Water damage.",
    "botanist": "10.0% increase in Grass damage.",
    "capacitor": "10.0% increase in Electric damage.",
    "earth organ": "10.0% increase in Ground damage.",
    "coldproof": "10.0% decrease in incoming Ice damage.",
    "heatproof": "10.0% decrease in incoming Fire damage.",
    "sunbath lover": "10.0% decrease in incoming Fire damage.",
    "suntan lover": "10.0% decrease in incoming Fire damage.",
    "celestial emperor": "20.0% increase in Neutral damage.",
    "flame emperor": "20.0% increase in Fire damage.",
    "lord of waves": "20.0% increase in Water damage.",
    "lord of the sea": "20.0% increase in Water damage.",
    "spirit emperor": "20.0% increase in Grass damage.",
    "lord of lightning": "20.0% increase in Electric damage.",
    "lord of the underworld": "20.0% increase in Dark damage.",
    "ice emperor": "20.0% increase in Ice damage.",
    "earth emperor": "20.0% increase in Ground damage.",
    "siren of the void": "20.0% increase in Dark damage.",
    "divine dragon": "20.0% increase in Dragon damage.",
    "eternal flame": "20.0% increase in Fire & Dark damage.",
    "invader": "20.0% increase in Dragon & Dark damage.",
    "demon god": "20.0% increase in Dark & Normal damage.",
    "remarkable craftsmanship": "Work Speed +50%",
}



PARTNER_SKILL_OVERRIDES = {
    "sheepball": {
        "name": "Fluffy Shield",
        "description": "When activated, equips to the player and becomes a shield. Sometimes drops Wool when assigned to a Ranch.",
        "unlock_item": "Lamball's Harness",
    },
    "chickenpal": {
        "name": "Egg Layer",
        "description": "Sometimes lays an Egg when assigned to a Ranch.",
        "unlock_item": None,
    },
    "cutefox": {
        "name": "Dig Here!",
        "description": "Sometimes digs up Pal Spheres and items from the ground when assigned to a Ranch.",
        "unlock_item": None,
    },
    "woolfox": {
        "name": "Fluffy Wool",
        "description": "While in party, increases Attack of Neutral Pals. Sometimes drops Wool when assigned to a Ranch.",
        "unlock_item": None,
    },
    "alpaca": {
        "name": "Pacapaca Wool",
        "description": "Can be ridden. While in party, increases Melpaca's Defense and Movement Speed. Sometimes drops Wool when assigned to a Ranch.",
        "unlock_item": "Melpaca Saddle",
    },
    "lavagirl": {
        "name": "Magma Tears",
        "description": "While in party, recovers Health of the player and Party Pals. Sometimes produces Flame Organs when assigned to a Ranch.",
        "unlock_item": None,
    },
    "bastet": {
        "name": "Gold Digger",
        "description": "Sometimes digs up Gold Coins when assigned to a Ranch.",
        "unlock_item": None,
    },
    "bastet_ice": {
        "name": "Icy Whispers",
        "description": "Sometimes produces Sapphires when assigned to a Ranch.",
        "unlock_item": None,
    },
    "berrygoat": {
        "name": "Berry Picker",
        "description": "While in party, restores hunger to hungry Pals. Sometimes drops Red Berries when assigned to a Ranch.",
        "unlock_item": None,
    },
    "berrygoat_dark": {
        "name": "Venom Picker",
        "description": "While in party, restores hunger to hungry Pals. Sometimes drops Venom Glands when assigned to a Ranch.",
        "unlock_item": None,
    },
    "sweetssheep": {
        "name": "Candy Pop",
        "description": "While at a base, reduces SAN depletion rate. Sometimes produces Cotton Candy when assigned to a Ranch.",
        "unlock_item": None,
    },
    "sweetssheep_ground": {
        "name": "Bitter Pop",
        "description": "While at a base, reduces SAN depletion rate. Sometimes produces High Quality Pal Oil when assigned to a Ranch.",
        "unlock_item": None,
    },
    "cowpal": {
        "name": "Milk Maker",
        "description": "Sometimes produces Milk when assigned to a Ranch.",
        "unlock_item": None,
    },
    "soldierbee": {
        "name": "Worker Bee",
        "description": "While in party, increases Beegarde's Attack. Sometimes produces Honey when assigned to a Ranch.",
        "unlock_item": None,
    },
    "whitemoth": {
        "name": "Silk Shroud",
        "description": "When activated, attacks targeted enemy with Blizzard Spike. Sometimes produces High Quality Cloth when assigned to a Ranch.",
        "unlock_item": None,
    },
    "whitemoth_neutral": {
        "name": "Gilded Shroud",
        "description": "While in party, increases Defense of Neutral Pals. Sometimes produces High Quality Cloth when assigned to a Ranch.",
        "unlock_item": None,
    },
    "plantslime": {
        "name": "Logging Assistance",
        "description": "While in party, improves efficiency of cutting trees.",
        "unlock_item": None,
    },
    "plantslime_flower": {
        "name": "Logging Assistance",
        "description": "While in party, improves efficiency of cutting trees.",
        "unlock_item": None,
    },
    "windchimes": {
        "name": "Flying Trapeze",
        "description": "While in party, can be summoned and used in place of a glider. Can carry the player high into the air while gliding.",
        "unlock_item": "Hangyu's Gloves",
    },
    "windchimes_ice": {
        "name": "Winter Trapeze",
        "description": "While in party, can be summoned and used in place of a glider. Can carry the player high into the air while gliding.",
        "unlock_item": "Hangyu Cryst's Gloves",
    },
}


def clean_skill_text(text: Optional[str]) -> Optional[str]:
    """Cleans up internal Unreal Engine string tokens and placeholders from skill text."""
    if not text:
        return None
    cleaned = str(text)
    
    # 1. Remove HTML/XML markup tags like <NumBlue_13>...</> or <color>...</color>
    cleaned = re.sub(r'<[^>]+>', '', cleaned)

    # 2. Remove Unreal reference tokens like {ReferenceMsgId_...} or {ActiveSkillMainValueByRank}
    cleaned = re.sub(r'\{ReferenceMsgId_[^}]+\}', '', cleaned)
    cleaned = re.sub(r'\{[A-Za-z0-9_]+\}', '', cleaned)
    
    # 3. Resolve missing token extractions in game sentences
    cleaned = cleaned.replace("Sometimes lays an when assigned to .", "Sometimes lays an Egg when assigned to a Ranch.")
    cleaned = cleaned.replace("lays an when assigned to .", "lays an Egg when assigned to a Ranch.")
    cleaned = cleaned.replace("Sometimes makes when assigned to .", "Sometimes produces High Quality Cloth when assigned to a Ranch.")
    cleaned = cleaned.replace("Sometimes digs up when assigned to .", "Sometimes digs up Gold Coins when assigned to a Ranch.")
    cleaned = cleaned.replace("Sometimes drops from its back when assigned to .", "Sometimes drops Red Berries when assigned to a Ranch.")
    cleaned = cleaned.replace("Sometimes drops or when assigned to .", "Sometimes drops Mushrooms when assigned to a Ranch.")
    cleaned = cleaned.replace("Sometimes drops when assigned to .", "Sometimes produces items when assigned to a Ranch.")
    cleaned = cleaned.replace("drops when assigned to .", "drops items when assigned to a Ranch.")
    cleaned = cleaned.replace("assigned to by 50%", "assigned to a Breeding Farm by 50%")
    cleaned = cleaned.replace("afflicted with .", "afflicted with status conditions.")
    cleaned = cleaned.replace("immune to .", "immune to temperature effects.")
    cleaned = cleaned.replace("attacks targeted enemy with .", "attacks targeted enemy.")
    cleaned = cleaned.replace("forged from .", "forged from ice.")
    cleaned = cleaned.replace("player's attack type to and", "player's attack type to Electric and")
    cleaned = cleaned.replace("When this Pal uses , it has a", "When this Pal uses its skill, it has a")
    cleaned = cleaned.replace("when assigned to .", "when assigned to a Ranch.")
    cleaned = cleaned.replace("(: )", "").replace("(:)", "")

    # 4. Fix broken sentence fragments from ranch/assignment extractions
    cleaned = re.sub(r'^\s*when assigned to a Ranch\.\s*$', 'Sometimes produces items when assigned to a Ranch.', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^\s*when assigned to a Ranch\s*', 'Sometimes produces items when assigned to a Ranch. ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\.\s*when assigned to a Ranch\.', '. Sometimes produces items when assigned to a Ranch.', cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned and cleaned.lower() != "none" else None



def calculate_aptitude(name: str, p_id: str, category: Optional[str]) -> Optional[dict[str, str]]:
    """Determines Palworld in-game passive skill aptitude degree and color."""
    name_l = name.lower()
    id_l = p_id.lower()
    cat_l = (category or "").lower()

    # Tier 4 / Legend
    if "tier4" in cat_l or "legend" in name_l or "siren of the void" in name_l or "eternal flame" in name_l:
        return {"label": "LEGEND", "color": "legend", "rank": 4}

    # Negative / Red tiers (-1, -2, -3)
    if "tier-3" in cat_l or any(k in name_l for k in ["slacker", "bottomless stomach", "destructive", "pacifist", "brittle"]):
        return {"label": "▼▼▼", "color": "red", "rank": -3}
    if "tier-2" in cat_l or any(k in name_l for k in ["clumsy", "work slave", "sadist", "downtrodden", "glutton", "destabilized"]):
        return {"label": "▼▼", "color": "red", "rank": -2}
    if "tier-1" in cat_l or any(k in name_l for k in ["coward", "masochist"]):
        return {"label": "▼", "color": "red", "rank": -1}

    # Positive / Gold tiers (+1, +2, +3)
    if "tier3" in cat_l or any(k in name_l for k in ["artisan", "ferocious", "burly body", "swift", "runner", "vanguard", "stronghold strategist", "lucky"]):
        return {"label": "▲▲▲", "color": "gold", "rank": 3}
    if "tier2" in cat_l or any(k in name_l for k in ["serious", "musclehead", "hard skin", "brave", "nimble", "workaholic", "positive thinker", "diet lover", "efficient worker", "zen mindset", "serenity"]):
        return {"label": "▲▲", "color": "gold", "rank": 2}
    if "tier1" in cat_l or any(k in name_l for k in ["aggressive", "conceited", "abnormal", "cheery", "dragonkiller", "pyromaniac", "hydromaniac", "botanist", "capacitor", "earth organ", "coldproof", "heatproof", "sunbath lover", "suntan lover"]):
        return {"label": "▲", "color": "white", "rank": 1}

    return {"label": "▲", "color": "white", "rank": 1}


def categorize_passive_source(name: str, p_id: str, category: Optional[str]) -> str:
    """Categorizes passive skills into Pal, Player, or Base effects."""
    n_l = name.lower()
    id_l = p_id.lower()
    if any(k in n_l for k in ["vanguard", "stronghold strategist", "motivational leader", "mine foreman", "logging foreman", "healing coach", "wellness watcher", "reload master"]):
        return "Player Boost"
    if any(k in n_l for k in ["artisan", "serious", "work slave", "clumsy", "slacker", "conceited", "diet lover", "efficient worker", "workaholic"]):
        return "Work / Base"
    return "Pal Combat"


def enrich_passive_skill(skill_dict: dict[str, Any]) -> dict[str, Any]:
    name = str(skill_dict.get("name") or "").strip()
    p_id = str(skill_dict.get("id") or "").strip()
    raw_cat = skill_dict.get("category")

    # Aptitude degree & color indicator
    skill_dict["aptitude"] = calculate_aptitude(name, p_id, raw_cat)
    # Source categorization
    skill_dict["source"] = categorize_passive_source(name, p_id, raw_cat)
    # Clear raw category string so TIER badge is removed
    skill_dict["category"] = None

    desc = clean_skill_text(skill_dict.get("description"))
    mod = clean_skill_text(skill_dict.get("stat_modifier"))

    if not mod or not desc:
        n_lower = name.lower()
        pid_lower = p_id.lower()
        if n_lower in PASSIVE_DESCRIPTIONS_MAP:
            mod = PASSIVE_DESCRIPTIONS_MAP[n_lower]
        elif pid_lower in PASSIVE_DESCRIPTIONS_MAP:
            mod = PASSIVE_DESCRIPTIONS_MAP[pid_lower]
        else:
            m_res = re.search(r"elementresist_([a-z]+)_?(\d+)?", pid_lower)
            if m_res:
                elem = m_res.group(1).capitalize()
                lvl = m_res.group(2) or "1"
                mod = f"Decreases incoming {elem} damage (Lv. {lvl})."

            m_bst = re.search(r"elementboost_([a-z]+)_?(\d+)?", pid_lower)
            if not mod and m_bst:
                elem = m_bst.group(1).capitalize()
                lvl = m_bst.group(2) or "1"
                mod = f"Increases {elem} attack damage (Lv. {lvl})."

            m_hp = re.search(r"hp_acc_up(\d+)", pid_lower)
            if not mod and m_hp:
                mod = f"Max HP +{int(m_hp.group(1))*5}%"

            m_atk = re.search(r"attack_acc_up(\d+)", pid_lower)
            if not mod and m_atk:
                mod = f"Attack +{int(m_atk.group(1))*5}%"

            m_def = re.search(r"def(e|n)ce_acc_up(\d+)", pid_lower)
            if not mod and m_def:
                mod = f"Defense +{int(m_def.group(2))*5}%"

            m_wrk = re.search(r"workspeed_acc_up(\d+)", pid_lower)
            if not mod and m_wrk:
                mod = f"Work Speed +{int(m_wrk.group(1))*10}%"

            m_exp = re.search(r"palexp_increase_(\d+)", pid_lower)
            if not mod and m_exp:
                mod = f"Pal EXP +{int(m_exp.group(1))*10}%"

            m_temp = re.search(r"temperatureresist_([a-z0-9]+)", pid_lower)
            if not mod and m_temp:
                mod = f"Grants temperature protection ({m_temp.group(1)})"

    if not mod and desc:
        mod = desc
    if not desc and mod:
        desc = mod

    skill_dict["description"] = desc
    skill_dict["stat_modifier"] = mod
    return skill_dict


class SQLiteEngine:
    """Manages the SQLite database engine for PalEngine."""

    def __init__(
        self,
        data_dir: Optional[str] = None,
        source: Optional[str] = None,
        db_path: Optional[str] = None,
        world_id: Optional[str] = None,
    ):
        if data_dir is None:
            data_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data")
            )
        self.data_dir = data_dir
        self.source = source or get_static_data_source()
        self.palworld_db_path = db_path or get_palworld_db_path()
        self.conn = None
        self.current_world_id = None
        self.current_save_path = None

        # Auto-select newest world if world_id not specified
        worlds = discover_worlds()
        target_world = None
        if world_id:
            target_world = get_world_by_id(world_id)
        elif worlds:
            target_world = worlds[0]

        if target_world:
            db_file = target_world["db_path"]
            self.current_world_id = target_world["world_id"]
            self.current_save_path = target_world["sav_path"]
        else:
            db_file = os.path.join(self.data_dir, "userdata.db")

        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._load_static_metadata()
        
        # Auto-load save file into DB on launch ONLY if DB is empty or Level.sav file mtime updated
        if self.current_save_path and os.path.exists(self.current_save_path):
            try:
                current_mtime = str(os.path.getmtime(self.current_save_path))
                cursor = self.conn.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS save_metadata (key TEXT PRIMARY KEY, value TEXT)")
                cursor.execute("SELECT value FROM save_metadata WHERE key = 'last_mtime'")
                row = cursor.fetchone()
                last_mtime = row["value"] if row else None
                
                if not last_mtime or last_mtime != current_mtime or self.get_instance_count() == 0:
                    self.load_save_data(self.current_save_path)
            except Exception as e:
                print(f"Auto-load save check warning: {e}")

    def _create_tables(self) -> None:
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS item_containers (
                container_id TEXT PRIMARY KEY,
                container_type TEXT,
                slot_count INTEGER
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS item_container_slots (
                container_id TEXT,
                slot_index INTEGER,
                item_id TEXT,
                count INTEGER,
                PRIMARY KEY (container_id, slot_index),
                FOREIGN KEY (container_id) REFERENCES item_containers (container_id)
            )
        """
        )

        # ---------- Dynamic Save Game Tables ----------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pal_instances (
                instance_id TEXT PRIMARY KEY,
                owner_uid TEXT,
                species TEXT,
                level INTEGER,
                exp INTEGER,
                gender TEXT,
                iv_hp INTEGER,
                iv_melee INTEGER,
                iv_shot INTEGER,
                iv_defense INTEGER,
                rank INTEGER,
                location TEXT,
                location_details_player_uid TEXT,
                location_details_base_camp_id TEXT,
                location_details_base_camp_name TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pal_instance_passives (
                instance_id TEXT,
                passive_id TEXT,
                PRIMARY KEY (instance_id, passive_id),
                FOREIGN KEY (instance_id) REFERENCES pal_instances (instance_id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pal_instance_waza (
                instance_id TEXT,
                waza_id TEXT,
                is_equipped INTEGER,
                PRIMARY KEY (instance_id, waza_id),
                FOREIGN KEY (instance_id) REFERENCES pal_instances (instance_id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pal_instance_status_points (
                instance_id TEXT,
                stat_name TEXT,
                points INTEGER,
                type TEXT,
                PRIMARY KEY (instance_id, stat_name, type),
                FOREIGN KEY (instance_id) REFERENCES pal_instances (instance_id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                player_uid TEXT PRIMARY KEY,
                nickname TEXT,
                level INTEGER,
                exp INTEGER,
                hp_current INTEGER,
                hp_max INTEGER,
                shield_current INTEGER,
                shield_max INTEGER,
                tech_points INTEGER,
                boss_tech_points INTEGER,
                inventory_container_id TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS player_unlocked_techs (
                player_uid TEXT,
                tech_name TEXT,
                PRIMARY KEY (player_uid, tech_name),
                FOREIGN KEY (player_uid) REFERENCES players (player_uid)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS player_paldeck_captures (
                player_uid TEXT,
                species TEXT,
                capture_count INTEGER,
                PRIMARY KEY (player_uid, species),
                FOREIGN KEY (player_uid) REFERENCES players (player_uid)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS player_status_points (
                player_uid TEXT,
                stat_name TEXT,
                points INTEGER,
                PRIMARY KEY (player_uid, stat_name),
                FOREIGN KEY (player_uid) REFERENCES players (player_uid)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS base_camps (
                base_camp_id TEXT PRIMARY KEY,
                name TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS item_containers (
                container_id TEXT PRIMARY KEY,
                container_type TEXT,
                slot_count INTEGER
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS item_container_slots (
                container_id TEXT,
                slot_index INTEGER,
                item_id TEXT,
                count INTEGER,
                PRIMARY KEY (container_id, slot_index),
                FOREIGN KEY (container_id) REFERENCES item_containers (container_id)
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS base_structures_instances (
                base_camp_id TEXT,
                structure_name TEXT,
                count INTEGER,
                PRIMARY KEY (base_camp_id, structure_name),
                FOREIGN KEY (base_camp_id) REFERENCES base_camps (base_camp_id)
            )
        """
        )

        # ---------- Static Metadata Source Setup ----------
        use_palworld_db = (
            self.source == "palworld_db" and os.path.exists(self.palworld_db_path)
        )

        if use_palworld_db:
            # Attach external master SQLite database
            db_path_clean = self.palworld_db_path.replace("\\", "/")
            cursor.execute(f"ATTACH DATABASE '{db_path_clean}' AS palworld_master")

            # Create in-memory tables populated from attached master database
            cursor.execute("DROP TABLE IF EXISTS main.pals")
            cursor.execute(
                r"""
                CREATE TABLE pals AS
                SELECT
                    coalesce(code, id) AS internal_name,
                    name AS display_name,
                    paldex_number,
                    CASE
                        WHEN LOWER(element1) IN ('normal', 'neutral') THEN 'Neutral'
                        WHEN LOWER(element1) IN ('leaf', 'grass') THEN 'Grass'
                        WHEN LOWER(element1) IN ('electricity', 'electric') THEN 'Electric'
                        ELSE element1
                    END AS element_1,
                    CASE
                        WHEN LOWER(element2) IN ('normal', 'neutral') THEN 'Neutral'
                        WHEN LOWER(element2) IN ('leaf', 'grass') THEN 'Grass'
                        WHEN LOWER(element2) IN ('electricity', 'electric') THEN 'Electric'
                        ELSE element2
                    END AS element_2,
                    hp,
                    attack AS attack_melee,
                    attack AS attack_ranged,
                    defense,
                    run_speed AS work_speed,
                    breeding_rank AS breeding_power,
                    food AS food_requirement,
                    NULL AS ride_type,
                    nocturnal,
                    'M' AS size,
                    CASE WHEN id LIKE '%\_%' ESCAPE '\' THEN 1 ELSE 0 END AS is_variant,
                    NULL AS base_pal,
                    paldex_number AS index_order,
                    icon_path,
                    description,
                    id,
                    code,
                    run_speed,
                    stamina,
                    rarity
                FROM palworld_master.pals
            """
            )

            cursor.execute("DROP TABLE IF EXISTS main.pal_work_suitabilities")
            cursor.execute(
                """
                CREATE TABLE pal_work_suitabilities AS
                SELECT
                    pal_id AS pal_internal_name,
                    CASE LOWER(work_type)
                        WHEN 'handcraft' THEN 'handiwork'
                        WHEN 'electricity' THEN 'generating_electricity'
                        WHEN 'generateelectricity' THEN 'generating_electricity'
                        WHEN 'productmedicine' THEN 'medicine_production'
                        WHEN 'medicine' THEN 'medicine_production'
                        WHEN 'transport' THEN 'transporting'
                        WHEN 'monsterfarm' THEN 'farming'
                        WHEN 'emitflame' THEN 'kindling'
                        WHEN 'seeding' THEN 'planting'
                        WHEN 'collection' THEN 'gathering'
                        WHEN 'deforest' THEN 'lumbering'
                        WHEN 'cool' THEN 'cooling'
                        ELSE LOWER(work_type)
                    END AS suitability_name,
                    level
                FROM palworld_master.work_suitability
            """
            )

            cursor.execute("DROP TABLE IF EXISTS main.active_skills")
            cursor.execute(
                """
                CREATE TABLE active_skills AS
                SELECT
                    id,
                    name,
                    element,
                    power,
                    cooldown AS cooldown_sec,
                    description,
                    icon_path
                FROM palworld_master.skills
                WHERE type = 'Active' OR type = 'active' OR category = 'Active'
            """
            )

            cursor.execute("DROP TABLE IF EXISTS main.passive_skills")
            cursor.execute(
                """
                CREATE TABLE passive_skills AS
                SELECT id, name, CAST(power AS INTEGER) as rank, description
                FROM palworld_master.skills
                WHERE type = 'Passive' OR category = 'Passive' OR category LIKE 'Passive%'
                """
            )

            cursor.execute("DROP TABLE IF EXISTS main.partner_skills")
            cursor.execute(
                """
                CREATE TABLE partner_skills AS
                SELECT s.id, s.name, ps.pal_id as pal_internal_name, s.description
                FROM palworld_master.skills s
                JOIN palworld_master.pal_skills ps ON s.id = ps.skill_id
                WHERE s.type = 'Partner' OR s.category = 'Partner' OR s.category LIKE 'Partner%'
                """
            )

            cursor.execute("DROP TABLE IF EXISTS main.base_structures")
            cursor.execute(
                """
                CREATE TABLE base_structures AS
                SELECT id, name, category, tech_level as technology_level
                FROM palworld_master.buildings
                """
            )

            cursor.execute("DROP TABLE IF EXISTS main.breeding_combos")
            cursor.execute(
                """
                CREATE TABLE breeding_combos AS
                SELECT parent1_id as parent1, parent2_id as parent2, child_id as child
                FROM palworld_master.breeding_combos
                """
            )

            cursor.execute("DROP TABLE IF EXISTS main.work_suitabilities")
            cursor.execute(
                """
                CREATE TABLE work_suitabilities AS
                SELECT DISTINCT
                    work_type AS id,
                    work_type AS name,
                    '' AS description
                FROM palworld_master.work_suitability
            """
            )

            cursor.execute("DROP TABLE IF EXISTS main.building_work_types")
            cursor.execute(
                """
                CREATE TABLE building_work_types AS
                SELECT building_id, work_type, is_automated, work_amount_modifier
                FROM palworld_master.building_work_types
            """
            )

            cursor.execute("DROP TABLE IF EXISTS main.food_satiety_rates")
            cursor.execute(
                """
                CREATE TABLE food_satiety_rates AS
                SELECT
                    food_tier AS food_rating,
                    satiety_drain_per_min AS satiety_amount,
                    base_san_drain_per_min AS san_decay_multiplier
                FROM palworld_master.food_satiety_rates
            """
            )
        else:
            # Legacy In-Memory SQLite Tables
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS passive_skills (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    rank INTEGER,
                    description TEXT
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS base_structures (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    category TEXT,
                    technology_level INTEGER
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS breeding_combos (
                    parent1 TEXT,
                    parent2 TEXT,
                    child TEXT,
                    PRIMARY KEY (parent1, parent2, child)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS partner_skills (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    pal_internal_name TEXT,
                    description TEXT
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pals (
                    internal_name TEXT PRIMARY KEY,
                    display_name TEXT,
                    paldex_number INTEGER,
                    element_1 TEXT,
                    element_2 TEXT,
                    hp INTEGER,
                    attack_melee INTEGER,
                    attack_ranged INTEGER,
                    defense INTEGER,
                    work_speed INTEGER,
                    breeding_power INTEGER,
                    food_requirement INTEGER,
                    ride_type TEXT,
                    nocturnal INTEGER,
                    size TEXT,
                    is_variant INTEGER,
                    base_pal TEXT,
                    index_order INTEGER,
                    icon_path TEXT,
                    description TEXT
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pal_work_suitabilities (
                    pal_internal_name TEXT,
                    suitability_name TEXT,
                    level INTEGER,
                    PRIMARY KEY (pal_internal_name, suitability_name),
                    FOREIGN KEY (pal_internal_name) REFERENCES pals (internal_name)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS active_skills (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    element TEXT,
                    power INTEGER,
                    cooldown_sec INTEGER,
                    description TEXT,
                    icon_path TEXT
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS work_suitabilities (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS building_work_types (
                    building_id TEXT,
                    work_type TEXT,
                    is_automated INTEGER,
                    work_amount_modifier REAL
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS food_satiety_rates (
                    food_rating INTEGER PRIMARY KEY,
                    satiety_amount REAL,
                    san_recovery REAL,
                    san_decay_multiplier REAL
                )
            """
            )

        self.conn.commit()

    def _load_static_metadata(self) -> None:
        cursor = self.conn.cursor()

        if self.source == "legacy" or not os.path.exists(self.palworld_db_path):
            passives_path = os.path.join(self.data_dir, "passive_skills.json")
            if os.path.exists(passives_path):
                with open(passives_path, "r", encoding="utf-8") as f:
                    passives_data = json.load(f)
                for ps in passives_data:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO passive_skills (id, name, rank, description)
                        VALUES (?, ?, ?, ?)
                    """,
                        (ps.get("id"), ps.get("name"), ps.get("rank"), ps.get("description")),
                    )

            bs_path = os.path.join(self.data_dir, "base_structures.json")
            if os.path.exists(bs_path):
                with open(bs_path, "r", encoding="utf-8") as f:
                    bs_data = json.load(f)
                for bs in bs_data:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO base_structures (id, name, category, technology_level)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            bs.get("id"),
                            bs.get("name"),
                            bs.get("category"),
                            bs.get("technology_level"),
                        ),
                    )

            bc_path = os.path.join(self.data_dir, "breeding_combos.json")
            if os.path.exists(bc_path):
                with open(bc_path, "r", encoding="utf-8") as f:
                    bc_data = json.load(f)
                for bc in bc_data.get("unique_combos", []):
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO breeding_combos (parent1, parent2, child)
                        VALUES (?, ?, ?)
                    """,
                        (bc.get("parent1"), bc.get("parent2"), bc.get("child")),
                    )

            ps_path = os.path.join(self.data_dir, "partner_skills.json")
            if os.path.exists(ps_path):
                with open(ps_path, "r", encoding="utf-8") as f:
                    ps_data = json.load(f)
                for ps in ps_data:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO partner_skills (id, name, pal_internal_name, description)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            ps.get("id"),
                            ps.get("name"),
                            ps.get("pal_internal_name"),
                            ps.get("description"),
                        ),
                    )


            pals_path = os.path.join(self.data_dir, "pals.json")
            if os.path.exists(pals_path):
                with open(pals_path, "r", encoding="utf-8") as f:
                    pals_data = json.load(f)
                for idx, p in enumerate(pals_data):
                    elements = p.get("element_types", [])
                    element_1 = elements[0] if len(elements) > 0 else None
                    element_2 = elements[1] if len(elements) > 1 else None

                    stats = p.get("base_stats", {})
                    cursor.execute(
                        """
                        INSERT INTO pals (
                            internal_name, display_name, paldex_number, element_1, element_2,
                            hp, attack_melee, attack_ranged, defense, work_speed,
                            breeding_power, food_requirement, ride_type, nocturnal,
                            size, is_variant, base_pal, index_order
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            p.get("internal_name"),
                            p.get("display_name"),
                            p.get("paldex_number"),
                            element_1,
                            element_2,
                            stats.get("hp"),
                            stats.get("attack_melee"),
                            stats.get("attack_ranged"),
                            stats.get("defense"),
                            stats.get("work_speed"),
                            p.get("breeding_power"),
                            p.get("food_requirement"),
                            p.get("ride_type"),
                            1 if p.get("nocturnal") else 0,
                            p.get("size"),
                            1 if p.get("is_variant") else 0,
                            p.get("base_pal"),
                            idx,
                        ),
                    )

                    # Work Suitabilities for this Pal
                    suitabilities = p.get("work_suitabilities", {})
                    for s_name, s_level in suitabilities.items():
                        cursor.execute(
                            """
                            INSERT INTO pal_work_suitabilities (pal_internal_name, suitability_name, level)
                            VALUES (?, ?, ?)
                        """,
                            (p.get("internal_name"), s_name, s_level),
                        )

            # Load Active Skills
            actives_path = os.path.join(self.data_dir, "active_skills.json")
            if os.path.exists(actives_path):
                with open(actives_path, "r", encoding="utf-8") as f:
                    actives_data = json.load(f)
                for act in actives_data:
                    cursor.execute(
                        """
                        INSERT INTO active_skills (id, name, element, power, cooldown_sec, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            act.get("id"),
                            act.get("name"),
                            act.get("element"),
                            act.get("power"),
                            act.get("cooldown_sec"),
                            act.get("description"),
                        ),
                    )

            # Load Work Suitabilities Definitions
            ws_path = os.path.join(self.data_dir, "work_suitabilities.json")
            if os.path.exists(ws_path):
                with open(ws_path, "r", encoding="utf-8") as f:
                    ws_data = json.load(f)
                for ws in ws_data:
                    cursor.execute(
                        """
                        INSERT INTO work_suitabilities (id, name, description)
                        VALUES (?, ?, ?)
                    """,
                        (ws.get("id"), ws.get("name"), ws.get("description")),
                    )

        self.conn.commit()

    # ---------- Save Data Reload capability ----------

    def get_instance_count(self) -> int:
        """Returns total Pal instances stored in current DB."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) as c FROM pal_instances")
            return cursor.fetchone()["c"]
        except Exception:
            return 0

    def switch_world(self, world_id: str) -> dict[str, Any]:
        """Switches current database connection to target world database.

        Auto-parses and loads the world Level.sav if DB is empty.
        """
        world = get_world_by_id(world_id)
        if not world:
            raise ValueError(f"World not found: {world_id}")

        if self.conn:
            self.conn.close()

        self.current_world_id = world["world_id"]
        self.current_save_path = world["sav_path"]
        
        db_path = world["db_path"]
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._load_static_metadata()

        # Load save data if DB is new/empty
        if self.get_instance_count() == 0:
            self.load_save_data(self.current_save_path)

        return {
            "status": "success",
            "world_id": self.current_world_id,
            "display_name": world["display_name"],
            "sav_path": self.current_save_path,
            "instances_count": self.get_instance_count(),
        }

    def clear_instance_data(self) -> None:
        """Clears all dynamic save-game related tables."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM pal_instances")
        cursor.execute("DELETE FROM pal_instance_passives")
        cursor.execute("DELETE FROM pal_instance_waza")
        cursor.execute("DELETE FROM pal_instance_status_points")
        cursor.execute("DELETE FROM players")
        cursor.execute("DELETE FROM player_unlocked_techs")
        cursor.execute("DELETE FROM player_paldeck_captures")
        cursor.execute("DELETE FROM player_status_points")
        cursor.execute("DELETE FROM base_camps")
        cursor.execute("DELETE FROM base_structures_instances")
        cursor.execute("DELETE FROM item_container_slots")
        cursor.execute("DELETE FROM item_containers")
        self.conn.commit()

    def load_save_data(self, sav_path: str) -> None:
        """Parses Level.sav and loads instances into the SQLite DB."""
        self.clear_instance_data()
        self.current_save_path = sav_path

        pals = extract_pals(sav_path)
        bases = extract_bases(sav_path)
        items_data = extract_items(sav_path)
        players = extract_players(sav_path)

        cursor = self.conn.cursor()
        
        for p in players:
            cursor.execute(
                """
                INSERT OR REPLACE INTO players (
                    player_uid, nickname, level, exp, hp_current, hp_max,
                    shield_current, shield_max, tech_points, boss_tech_points,
                    inventory_container_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    p["player_uid"], p["nickname"], p["level"], p["exp"],
                    p["hp_current"], p["hp_max"], p["shield_current"], p["shield_max"],
                    p["tech_points"], p["boss_tech_points"], p["inventory_container_id"]
                )
            )
            
            for tech in p.get("unlocked_techs", []):
                cursor.execute(
                    "INSERT OR REPLACE INTO player_unlocked_techs (player_uid, tech_name) VALUES (?, ?)",
                    (p["player_uid"], tech)
                )
                
            for sp_name, count in p.get("paldeck_captures", {}).items():
                cursor.execute(
                    "INSERT OR REPLACE INTO player_paldeck_captures (player_uid, species, capture_count) VALUES (?, ?, ?)",
                    (p["player_uid"], sp_name, count)
                )
                
            for stat_name, pts in p.get("status_points", {}).items():
                cursor.execute(
                    "INSERT OR REPLACE INTO player_status_points (player_uid, stat_name, points) VALUES (?, ?, ?)",
                    (p["player_uid"], stat_name, pts)
                )

        for container in items_data:
            cursor.execute("""
                INSERT OR REPLACE INTO item_containers (container_id, container_type, slot_count)
                VALUES (?, ?, ?)
            """, (container['container_id'], container['container_type'], container['slot_count']))
            for item in container['items']:
                cursor.execute("""
                    INSERT OR REPLACE INTO item_container_slots (container_id, slot_index, item_id, count)
                    VALUES (?, ?, ?, ?)
                """, (container['container_id'], item['slot_index'], item['item_id'], item['count']))




        cursor = self.conn.cursor()

        for base_id, base_info in bases.items():
            cursor.execute(
                """
                INSERT OR REPLACE INTO base_camps (base_camp_id, name)
                VALUES (?, ?)
            """,
                (base_id, base_info["name"]),
            )

            for struct_name, count in base_info["structures"].items():
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO base_structures_instances (base_camp_id, structure_name, count)
                    VALUES (?, ?, ?)
                """,
                    (base_id, struct_name, count),
                )

        for pal in pals:
            loc_details = pal.get("location_details") or {}
            loc_player_uid = loc_details.get("player_uid")
            loc_base_camp_id = loc_details.get("base_camp_id")
            loc_base_camp_name = loc_details.get("base_camp_name")

            cursor.execute(
                """
                INSERT OR REPLACE INTO pal_instances (
                    instance_id, owner_uid, species, level, exp, gender,
                    iv_hp, iv_melee, iv_shot, iv_defense, rank, location,
                    location_details_player_uid, location_details_base_camp_id,
                    location_details_base_camp_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    pal.get("instance_id"),
                    pal.get("owner_uid"),
                    pal.get("species"),
                    pal.get("level"),
                    pal.get("exp"),
                    pal.get("gender"),
                    pal.get("ivs", {}).get("hp"),
                    pal.get("ivs", {}).get("melee"),
                    pal.get("ivs", {}).get("shot"),
                    pal.get("ivs", {}).get("defense"),
                    pal.get("rank"),
                    pal.get("location"),
                    loc_player_uid,
                    loc_base_camp_id,
                    loc_base_camp_name,
                ),
            )

            for p_id in pal.get("passives", []):
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO pal_instance_passives (instance_id, passive_id)
                    VALUES (?, ?)
                """,
                    (pal.get("instance_id"), p_id),
                )

            for waza in pal.get("equip_waza", []):
                if waza:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO pal_instance_waza (instance_id, waza_id, is_equipped)
                        VALUES (?, ?, 1)
                    """,
                        (pal.get("instance_id"), waza),
                    )

            for waza in pal.get("mastered_waza", []):
                if waza:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO pal_instance_waza (instance_id, waza_id, is_equipped)
                        VALUES (?, ?, 0)
                    """,
                        (pal.get("instance_id"), waza),
                    )

            soul_points = pal.get("soul_points", {})
            for stat_name, pts in soul_points.items():
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO pal_instance_status_points (instance_id, stat_name, points, type)
                    VALUES (?, ?, ?, 'soul')
                """,
                    (pal.get("instance_id"), stat_name, pts),
                )

            elixir_points = pal.get("elixir_points", {})
            for stat_name, pts in elixir_points.items():
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO pal_instance_status_points (instance_id, stat_name, points, type)
                    VALUES (?, ?, ?, 'elixir')
                """,
                    (pal.get("instance_id"), stat_name, pts),
                )

        if sav_path and os.path.exists(sav_path):
            mtime = str(os.path.getmtime(sav_path))
            cursor.execute("CREATE TABLE IF NOT EXISTS save_metadata (key TEXT PRIMARY KEY, value TEXT)")
            cursor.execute("INSERT OR REPLACE INTO save_metadata (key, value) VALUES ('last_mtime', ?)", (mtime,))

        self.conn.commit()

    # ---------- Instance Skill Quality Scorer & Passives Utilities ----------

    def calculate_passive_score(
        self, passive: Any, target_skills: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Calculates quality score contribution for an individual passive skill/trait.
        
        Handles passive dicts or string names/IDs. Applies bonus score for matched target skills.
        """
        PASSIVE_WEIGHTS: dict[str, float] = {
            # Tier 4 / Legend / Unique Element Passives (+20)
            "legend": 20.0, "celestial emperor": 20.0, "lord of lightning": 20.0, "divine dragon": 20.0,
            "siren of the void": 20.0, "eternal flame": 20.0, "ice emperor": 20.0, "flame emperor": 20.0,
            "earth emperor": 20.0, "spirit emperor": 20.0, "emperor": 15.0,
            
            # Tier 3 Gold Passives (+12 to +15)
            "artisan": 15.0, "ferocious": 15.0, "musclehead": 15.0, "swift": 15.0, "lucky": 15.0,
            "work slave": 12.0, "vanguard": 12.0, "stronghold strategist": 12.0, "burly body": 12.0, "remarkable": 12.0,
            
            # Tier 2 Positive Passives (+6 to +8)
            "runner": 8.0, "workaholic": 8.0, "mine foreman": 8.0, "logging foreman": 8.0, "motivational leader": 8.0,
            "serious": 8.0, "cheery": 6.0, "positive thinker": 6.0, "hard skin": 6.0, "brave": 6.0,
            
            # Tier 1 Positive Passives (+2 to +4)
            "nimble": 4.0, "abnormal": 3.0, "zen mind": 3.0, "hydromaniac": 3.0, "pyromaniac": 3.0,
            "botanist": 3.0, "capacitor": 3.0, "earth organ": 3.0, "dragonkiller": 3.0,
            
            # Red / Harmful Passives (Negative)
            "slacker": -15.0, "downtrodden": -12.0, "pacifist": -12.0, "bottomless stomach": -10.0,
            "brittle": -10.0, "glutton": -8.0, "destructive": -8.0, "sadist": -8.0,
            "coward": -5.0, "clumsy": -5.0, "distracted": -5.0, "unstable": -5.0, "dehydrated": -5.0, "sloppy": -5.0,
        }

        if isinstance(passive, dict):
            p_name = str(passive.get("name") or passive.get("id") or "").strip()
            p_id = str(passive.get("id") or "").strip()
            rank = passive.get("rank")
            desc = str(passive.get("description") or "").lower()
        else:
            p_name = str(passive).strip()
            p_id = p_name
            rank = None
            desc = ""

        p_name_lower = p_name.lower()
        p_id_lower = p_id.lower()

        # Determine base weight
        if p_name_lower in PASSIVE_WEIGHTS:
            base_score = PASSIVE_WEIGHTS[p_name_lower]
        elif p_id_lower in PASSIVE_WEIGHTS:
            base_score = PASSIVE_WEIGHTS[p_id_lower]
        elif any(neg_kw in p_name_lower or neg_kw in desc for neg_kw in ["coward", "clumsy", "glutton", "slacker", "downtrodden", "pacifist", "brittle"]):
            base_score = -8.0
        elif rank is not None and isinstance(rank, (int, float)):
            if rank >= 4:
                base_score = 15.0
            elif rank == 3:
                base_score = 10.0
            elif rank == 2:
                base_score = 5.0
            elif rank == 1:
                base_score = 2.0
            elif rank < 0:
                base_score = -5.0
            else:
                base_score = 0.0
        else:
            base_score = 1.0

        # Check target skill match
        is_target_match = False
        if target_skills:
            for t in target_skills:
                t_clean = str(t).strip().lower()
                if t_clean and (t_clean in p_name_lower or t_clean in p_id_lower or t_clean in desc):
                    is_target_match = True
                    break

        target_bonus = 20.0 if is_target_match else 0.0
        total_score = base_score + target_bonus

        return {
            "id": p_id,
            "name": p_name or p_id,
            "base_score": base_score,
            "score": total_score,
            "is_target_match": is_target_match,
            "is_negative": base_score < 0,
        }

    def score_pal_instance(
        self, instance: dict[str, Any], target_skills: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Calculates overall skill & passive trait quality score for a Pal instance.
        
        Returns score summary, matched passives, passive details, and quality rating.
        """
        passives = instance.get("passives")
        if passives is None and "instance_id" in instance:
            inst_list = self.query_instances({"instance_id": instance["instance_id"]})
            if inst_list:
                passives = inst_list[0].get("passives", [])
        if passives is None:
            passives = []

        passive_scores = []
        total_score = 0.0
        matched_passives = []
        has_red_passive = False

        for p in passives:
            res = self.calculate_passive_score(p, target_skills)
            passive_scores.append(res)
            total_score += res["score"]
            if res["is_target_match"]:
                matched_passives.append(res["name"])
            if res["is_negative"]:
                has_red_passive = True

        score_result = dict(instance)
        score_result["skill_score"] = round(total_score, 1)
        score_result["matched_passives"] = matched_passives
        score_result["passive_details"] = passive_scores
        score_result["has_red_passive"] = has_red_passive
        return score_result

    def get_best_parent_instances(
        self, species: str, gender: str, target_skills: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        """Returns owned Pal instances of target species & gender from save DB sorted by skill quality score."""
        instances = self.query_instances({"species": species, "gender": gender})
        if not instances:
            return []

        scored = [self.score_pal_instance(inst, target_skills) for inst in instances]
        scored.sort(
            key=lambda x: (
                len(x.get("matched_passives", [])),
                x.get("skill_score", 0),
                x.get("level", 0),
                x.get("rank", 0),
            ),
            reverse=True,
        )
        return scored

    # ---------- Advanced Breeding Logic APIs ----------


    def get_owned_pal_inventory(self) -> dict[str, set[str]]:
        """Returns map of owned Pal display names to their available genders in save data.
        Example: {'Lamball': {'Male', 'Female'}, 'Leezpunk': {'Female'}}
        """
        rows = self.conn.execute(
            """
            SELECT DISTINCT coalesce(p.display_name, pi.species) as display_name, pi.gender
            FROM pal_instances pi
            LEFT JOIN pals p ON LOWER(pi.species) = LOWER(p.internal_name)
                             OR LOWER(pi.species) = LOWER(p.display_name)
                             OR LOWER(pi.species) = LOWER(p.id)
                             OR LOWER(pi.species) = LOWER(p.code)
                             OR REPLACE(LOWER(pi.species), 'boss_', '') = LOWER(p.internal_name)
                             OR REPLACE(LOWER(pi.species), 'boss_', '') = LOWER(p.display_name)
                             OR REPLACE(LOWER(pi.species), 'boss_', '') = LOWER(p.id)
                             OR REPLACE(LOWER(pi.species), 'boss_', '') = LOWER(p.code)
            WHERE pi.gender IS NOT NULL AND pi.gender != ''
              AND coalesce(p.display_name, pi.species) NOT LIKE 'Hunter_%'
              AND coalesce(p.display_name, pi.species) NOT LIKE 'Believer_%'
              AND coalesce(p.display_name, pi.species) NOT LIKE 'BOSS_Female_%'
            """
        ).fetchall()
        inv: dict[str, set[str]] = {}
        for r in rows:
            name = r["display_name"]
            gender = r["gender"].capitalize()
            if name not in inv:
                inv[name] = set()
            inv[name].add(gender)
        return inv

    def get_owned_pal_species(self) -> list[str]:
        """Returns sorted list of distinct Pal display names currently owned in save data."""
        rows = self.conn.execute(
            """
            SELECT DISTINCT coalesce(p.display_name, pi.species) as display_name
            FROM pal_instances pi
            LEFT JOIN pals p ON LOWER(pi.species) = LOWER(p.internal_name)
                             OR LOWER(pi.species) = LOWER(p.display_name)
                             OR LOWER(pi.species) = LOWER(p.id)
                             OR LOWER(pi.species) = LOWER(p.code)
                             OR REPLACE(LOWER(pi.species), 'boss_', '') = LOWER(p.internal_name)
                             OR REPLACE(LOWER(pi.species), 'boss_', '') = LOWER(p.display_name)
                             OR REPLACE(LOWER(pi.species), 'boss_', '') = LOWER(p.id)
                             OR REPLACE(LOWER(pi.species), 'boss_', '') = LOWER(p.code)
            WHERE coalesce(p.display_name, pi.species) NOT LIKE 'Hunter_%'
              AND coalesce(p.display_name, pi.species) NOT LIKE 'Believer_%'
              AND coalesce(p.display_name, pi.species) NOT LIKE 'BOSS_Female_%'
            ORDER BY display_name ASC
            """
        ).fetchall()
        return [r["display_name"] for r in rows if r["display_name"]]

    def get_breeding_result(self, parent1: str, parent2: str) -> Optional[dict[str, Any]]:
        """Calculates breeding result child for two parent species."""
        p1_in = parent1.strip().lower()
        p2_in = parent2.strip().lower()

        p1_row = self.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
            (p1_in, p1_in),
        ).fetchone() or self.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) LIKE ? OR LOWER(internal_name) LIKE ?",
            (f"%{p1_in}%", f"%{p1_in}%"),
        ).fetchone()

        p2_row = self.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
            (p2_in, p2_in),
        ).fetchone() or self.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) LIKE ? OR LOWER(internal_name) LIKE ?",
            (f"%{p2_in}%", f"%{p2_in}%"),
        ).fetchone()

        if not p1_row or not p2_row:
            return None

        p1_names = {p1_in, p1_row["display_name"].lower(), p1_row["internal_name"].lower()}
        p2_names = {p2_in, p2_row["display_name"].lower(), p2_row["internal_name"].lower()}

        if p1_row["display_name"].lower() == p2_row["display_name"].lower():
            row = self.conn.execute(
                "SELECT * FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
                (p1_row["display_name"].lower(), p1_row["display_name"].lower()),
            ).fetchone()
            if row:
                res = dict(row)
                res["icon_path"] = transform_icon_path(res.get("icon_path"))
                return res

        combo_row = None
        for n1 in p1_names:
            for n2 in p2_names:
                row = self.conn.execute(
                    """
                    SELECT child FROM breeding_combos
                    WHERE (LOWER(parent1) = ? AND LOWER(parent2) = ?)
                       OR (LOWER(parent1) = ? AND LOWER(parent2) = ?)
                """,
                    (n1, n2, n2, n1),
                ).fetchone()
                if row:
                    combo_row = row
                    break
            if combo_row:
                break

        if combo_row:
            child_name = combo_row["child"]
            child_row = self.conn.execute(
                "SELECT * FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
                (child_name.lower(), child_name.lower()),
            ).fetchone()
            if child_row:
                res = dict(child_row)
                res["icon_path"] = transform_icon_path(res.get("icon_path"))
                return res

        p1_power = p1_row["breeding_power"]
        p2_power = p2_row["breeding_power"]

        target_power = (p1_power + p2_power + 1) // 2

        restricted = (
            "jetragon",
            "frostallion",
            "paladius",
            "necromus",
            "bellanoir",
            "chikipi",
            "xenovader",
            "xenogard",
            "xenolord",
        )

        query = f"""
            SELECT * FROM pals
            WHERE is_variant = 0
              AND LOWER(display_name) NOT IN ({','.join('?' for _ in restricted)})
            ORDER BY abs(breeding_power - ?) ASC, index_order ASC
            LIMIT 1
        """
        child_row = self.conn.execute(query, restricted + (target_power,)).fetchone()
        if child_row:
            res = dict(child_row)
            res["icon_path"] = transform_icon_path(res.get("icon_path"))
            return res
        return None

    def get_offspring_for_parent(self, parent: str) -> list[dict[str, Any]]:
        """Finds all unique offspring possible from the given parent."""
        p_row = self.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
            (parent.lower(), parent.lower()),
        ).fetchone() or self.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) LIKE ? OR LOWER(internal_name) LIKE ?",
            (f"%{parent.lower()}%", f"%{parent.lower()}%"),
        ).fetchone()

        if not p_row:
            return []
            
        all_pals = self.conn.execute("SELECT display_name, internal_name, breeding_power FROM pals").fetchall()
        
        offspring_set = set()
        offspring_results = []
        
        for other in all_pals:
            res = self.get_breeding_result(p_row["display_name"], other["display_name"])
            if res:
                c_name = res["display_name"]
                if c_name not in offspring_set:
                    offspring_set.add(c_name)
                    offspring_results.append(res)
                    
        return offspring_results

    def find_parents_for_child(self, child: str) -> list[tuple[str, str]]:
        """Returns all breeding combinations (Parent 1, Parent 2) that yield target child."""
        c = child.strip().lower()

        child_row = self.conn.execute(
            "SELECT display_name FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
            (c, c),
        ).fetchone()
        if not child_row:
            child_row = self.conn.execute(
                "SELECT display_name FROM pals WHERE LOWER(display_name) LIKE ? OR LOWER(internal_name) LIKE ?",
                (f"%{c}%", f"%{c}%"),
            ).fetchone()
            if not child_row:
                return []

        child_name = child_row["display_name"]
        target_child_lower = child_name.lower()

        pals_rows = self.conn.execute(
            "SELECT display_name, breeding_power, is_variant, index_order FROM pals"
        ).fetchall()
        all_pals = [dict(r) for r in pals_rows]

        combos_rows = self.conn.execute("SELECT parent1, parent2, child FROM breeding_combos").fetchall()
        special_combos: dict[tuple[str, str], str] = {}
        for r in combos_rows:
            p1_l = r["parent1"].lower()
            p2_l = r["parent2"].lower()
            ch_name = r["child"]
            special_combos[(p1_l, p2_l)] = ch_name
            special_combos[(p2_l, p1_l)] = ch_name

        restricted = {
            "jetragon", "frostallion", "paladius", "necromus",
            "bellanoir", "chikipi", "xenovader", "xenogard", "xenolord"
        }
        candidate_pals = [
            p for p in all_pals
            if p["is_variant"] == 0 and p["display_name"].lower() not in restricted
        ]
        candidate_pals.sort(key=lambda x: x["index_order"])

        def calc_standard_child(power1: int, power2: int) -> str:
            target_power = (power1 + power2 + 1) // 2
            best_pal = min(
                candidate_pals,
                key=lambda p: abs(p["breeding_power"] - target_power)
            )
            return best_pal["display_name"]

        results = set()

        # Same-species breeding gives same species
        results.add((child_name, child_name))

        for i in range(len(all_pals)):
            for j in range(i, len(all_pals)):
                p1_name = all_pals[i]["display_name"]
                p2_name = all_pals[j]["display_name"]
                p1_l, p2_l = p1_name.lower(), p2_name.lower()

                if p1_l == p2_l:
                    result_child = p1_name
                elif (p1_l, p2_l) in special_combos:
                    result_child = special_combos[(p1_l, p2_l)]
                else:
                    pow1 = all_pals[i]["breeding_power"]
                    pow2 = all_pals[j]["breeding_power"]
                    result_child = calc_standard_child(pow1, pow2)

                if result_child.lower() == target_child_lower:
                    p1_n, p2_n = p1_name, p2_name
                    if p1_n.lower() > p2_n.lower():
                        p1_n, p2_n = p2_n, p1_n
                    results.add((p1_n, p2_n))

        return sorted(list(results), key=lambda x: (x[0].lower(), x[1].lower()))

    def find_all_breeding_paths(
        self,
        owned_input: Any,
        target_species: str,
        target_skills: Optional[Any] = None,
    ) -> list[dict[str, Any]]:
        """Breadth-First Search (BFS) pathfinder that returns multiple distinct alternative breeding paths with instance skill scores & gender hatch odds."""
        target_skills_list: list[str] = []
        if isinstance(target_skills, str):
            target_skills_list = [s.strip() for s in target_skills.split(",") if s.strip()]
        elif isinstance(target_skills, list):
            target_skills_list = [str(s).strip() for s in target_skills if str(s).strip()]

        PAL_GENDER_RATIOS: dict[str, tuple[int, int]] = {
            "beegarde": (20, 80), "elizabee": (20, 80), "petallia": (20, 80),
            "lovander": (20, 80), "dazzi": (20, 80), "ribbuny": (20, 80),
            "flopie": (20, 80), "vixy": (20, 80), "cremis": (20, 80), "cinnamoth": (20, 80),
            "relaxaurus": (80, 20), "relaxaurus lux": (80, 20), "mozzarina": (80, 20),
            "eikthyrdeer": (80, 20), "eikthyrdeer terra": (80, 20), "grizzbolt": (80, 20),
            "warsect": (80, 20), "rayhound": (80, 20), "wumpo": (80, 20), "wumpo botan": (80, 20),
            "kingpaca": (90, 10), "kingpaca cryst": (90, 10), "lyleen noct": (0, 100),
        }

        def get_hatch_odds(child_species: str, required_gender: str) -> dict[str, str]:
            sp_l = child_species.strip().lower()
            m_pct, f_pct = PAL_GENDER_RATIOS.get(sp_l, (50, 50))
            if required_gender == "Male":
                pct = m_pct
            elif required_gender == "Female":
                pct = f_pct
            else:
                pct = 100

            if pct == 0:
                return {"hatch_chance_pct": "0%", "avg_eggs": "Impossible", "gender_note": f"Impossible to hatch {required_gender}"}
            avg = round(100.0 / pct, 1)
            avg_str = "~1 egg" if avg == 1.0 else f"~{avg} eggs"
            return {
                "hatch_chance_pct": f"{pct}%",
                "avg_eggs": avg_str,
                "gender_note": f"{pct}% {required_gender} hatch chance ({avg_str} avg)",
            }

        pals_rows = self.conn.execute(
            "SELECT display_name, internal_name, breeding_power, is_variant, index_order FROM pals"
        ).fetchall()
        all_pals = [dict(r) for r in pals_rows]
        cased_names = {r["display_name"].lower(): r["display_name"] for r in all_pals}
        power_map = {r["display_name"].lower(): r["breeding_power"] for r in all_pals}

        combos_rows = self.conn.execute("SELECT parent1, parent2, child FROM breeding_combos").fetchall()
        special_combos: dict[tuple[str, str], str] = {}
        for r in combos_rows:
            p1_l = r["parent1"].lower()
            p2_l = r["parent2"].lower()
            ch_name = r["child"]
            special_combos[(p1_l, p2_l)] = ch_name
            special_combos[(p2_l, p1_l)] = ch_name

        restricted = {
            "jetragon", "frostallion", "paladius", "necromus",
            "bellanoir", "chikipi", "xenovader", "xenogard", "xenolord"
        }
        candidate_pals = [
            p for p in all_pals
            if p["is_variant"] == 0 and p["display_name"].lower() not in restricted
        ]
        candidate_pals.sort(key=lambda x: x["index_order"])

        def calc_child_fast(p1_l: str, p2_l: str) -> str:
            if p1_l == p2_l:
                return cased_names.get(p1_l, p1_l)
            if (p1_l, p2_l) in special_combos:
                return special_combos[(p1_l, p2_l)]
            if p1_l in power_map and p2_l in power_map:
                pow1 = power_map[p1_l]
                pow2 = power_map[p2_l]
                target_pow = (pow1 + pow2 + 1) // 2
                best = min(candidate_pals, key=lambda p: abs(p["breeding_power"] - target_pow))
                return best["display_name"]
            return ""

        target_input = target_species.strip().lower()
        target = target_input
        if target not in cased_names:
            matched = next((k for k in cased_names if target_input in k), None)
            if matched:
                target = matched
            else:
                return []

        reachable_genders: dict[str, set[str]] = {}

        if isinstance(owned_input, dict):
            for sp_name, genders in owned_input.items():
                sp_l = sp_name.strip().lower()
                c_sp = cased_names.get(sp_l, sp_l).lower()
                if c_sp not in reachable_genders:
                    reachable_genders[c_sp] = set()
                for g in genders:
                    reachable_genders[c_sp].add(g.lower())
        elif isinstance(owned_input, list):
            for item in owned_input:
                item_str = str(item).strip()
                g_spec = None
                if "(" in item_str and ")" in item_str:
                    parts = item_str.split("(", 1)
                    sp_raw = parts[0].strip()
                    g_raw = parts[1].replace(")", "").strip().lower()
                    if "female" in g_raw or "♀" in g_raw:
                        g_spec = "female"
                    elif "male" in g_raw or "♂" in g_raw:
                        g_spec = "male"
                else:
                    sp_raw = item_str

                sp_l = sp_raw.lower()
                matched_sp = next((k for k in cased_names if sp_l in k), sp_l)
                if matched_sp not in reachable_genders:
                    reachable_genders[matched_sp] = set()
                if g_spec:
                    reachable_genders[matched_sp].add(g_spec)
                else:
                    reachable_genders[matched_sp].update({"male", "female"})

        starting_owned = set(reachable_genders.keys())

        def check_breeding_compatibility(p1_l: str, p2_l: str) -> tuple[bool, str, str]:
            g1 = reachable_genders.get(p1_l, set())
            g2 = reachable_genders.get(p2_l, set())
            if p1_l == p2_l:
                if "male" in g1 and "female" in g1:
                    return True, "Male", "Female"
                return False, "", ""
            if "male" in g1 and "female" in g2:
                return True, "Male", "Female"
            if "female" in g1 and "male" in g2:
                return True, "Female", "Male"
            return False, "", ""

        # Store multiple candidate parent recipes per child to allow alternative paths
        recipes_for_child: dict[str, list[tuple[str, str, str, str]]] = {}
        reachable = set(starting_owned)
        queue = list(reachable)

        for _generation in range(5):
            next_queue = []
            new_breeds = []
            for parent1 in queue:
                for parent2 in reachable:
                    ok, g1_req, g2_req = check_breeding_compatibility(parent1, parent2)
                    if ok:
                        child_name = calc_child_fast(parent1, parent2)
                        if child_name:
                            child = child_name.lower()
                            if child not in starting_owned:
                                new_breeds.append((child, parent1, g1_req, parent2, g2_req))

            for child, p1, g1_req, p2, g2_req in new_breeds:
                # Ignore self-breeding loops
                if p1 == p2 and child == p1:
                    continue

                if child not in recipes_for_child:
                    recipes_for_child[child] = []
                    next_queue.append(child)

                # Canonicalize parent pair to prevent order swapping duplicates
                pair_key = tuple(sorted([(p1, g1_req), (p2, g2_req)], key=lambda x: x[0]))
                existing_pairs = [tuple(sorted([(rp1, rg1), (rp2, rg2)], key=lambda x: x[0])) for rp1, rg1, rp2, rg2 in recipes_for_child[child]]
                if pair_key not in existing_pairs and len(recipes_for_child[child]) < 5:
                    recipes_for_child[child].append((p1, g1_req, p2, g2_req))

                if child not in reachable:
                    reachable.add(child)
                    reachable_genders[child] = {"male", "female"}

            queue = next_queue
            if target in recipes_for_child or not queue:
                break

        if target not in recipes_for_child:
            return []

        # Recursively construct all paths to target
        def build_paths(species: str, current_memo: set[str]) -> list[list[dict[str, Any]]]:
            if species not in recipes_for_child:
                return [[]]

            all_sub_paths = []
            for p1, g1_req, p2, g2_req in recipes_for_child[species]:
                pair_key_str = ":".join(sorted([f"{p1}:{g1_req}", f"{p2}:{g2_req}"]))
                recipe_key = f"{pair_key_str}->{species}"
                if recipe_key in current_memo:
                    continue
                new_memo = set(current_memo)
                new_memo.add(recipe_key)

                left_paths = build_paths(p1, new_memo)
                right_paths = build_paths(p2, new_memo)

                p1_cased = cased_names.get(p1, p1)
                p2_cased = cased_names.get(p2, p2)
                child_cased = cased_names.get(species, species)

                # Determine gender hatch odds for intermediate step
                hatch_info = {}
                if species != target:
                    hatch_info = get_hatch_odds(child_cased, g1_req)

                step = {
                    "parent1": p1_cased,
                    "parent1_gender": g1_req,
                    "parent2": p2_cased,
                    "parent2_gender": g2_req,
                    "child": child_cased,
                    **hatch_info
                }

                for lp in left_paths:
                    for rp in right_paths:
                        combined = lp + rp + [step]
                        all_sub_paths.append(combined)
                        if len(all_sub_paths) >= 15:
                            break
                    if len(all_sub_paths) >= 15:
                        break
                if len(all_sub_paths) >= 15:
                    break

            return all_sub_paths

        raw_paths = build_paths(target, set())

        # Canonicalize step signature helper
        def get_step_sig(s: dict[str, Any]) -> str:
            pair = sorted([f"{s['parent1']}:{s['parent1_gender']}", f"{s['parent2']}:{s['parent2_gender']}"])
            return f"{pair[0]}+{pair[1]}->{s['child']}"

        # Deduplicate paths
        unique_paths = []
        path_signatures = set()

        for p in raw_paths:
            if len(p) > 3:
                continue

            # Attach best instance scores & passives details to each step
            for s_step in p:
                p1_sp = s_step["parent1"]
                p1_g = s_step["parent1_gender"]
                p2_sp = s_step["parent2"]
                p2_g = s_step["parent2_gender"]

                best_p1_list = self.get_best_parent_instances(p1_sp, p1_g, target_skills_list)
                if best_p1_list:
                    b1 = best_p1_list[0]
                    s_step["parent1_instance_id"] = b1.get("instance_id")
                    s_step["parent1_score"] = b1.get("skill_score", 0)
                    s_step["parent1_passives"] = [
                        p_item.get("name") if isinstance(p_item, dict) else str(p_item)
                        for p_item in b1.get("passives", [])
                    ]
                    s_step["parent1_matched_passives"] = b1.get("matched_passives", [])
                    s_step["parent1_location"] = b1.get("location")

                best_p2_list = self.get_best_parent_instances(p2_sp, p2_g, target_skills_list)
                if best_p2_list:
                    b2 = best_p2_list[0]
                    s_step["parent2_instance_id"] = b2.get("instance_id")
                    s_step["parent2_score"] = b2.get("skill_score", 0)
                    s_step["parent2_passives"] = [
                        p_item.get("name") if isinstance(p_item, dict) else str(p_item)
                        for p_item in b2.get("passives", [])
                    ]
                    s_step["parent2_matched_passives"] = b2.get("matched_passives", [])
                    s_step["parent2_location"] = b2.get("location")

            sig = "||".join(get_step_sig(s) for s in p)
            if sig in path_signatures:
                continue

            path_signatures.add(sig)
            unique_paths.append(p)

        # Rank paths based on matched target skills count, combined parent skill score, and step count
        path_candidates = []
        for p in unique_paths:
            total_matched = sum(
                len(s.get("parent1_matched_passives", [])) + len(s.get("parent2_matched_passives", []))
                for s in p
            )
            total_score = sum(
                s.get("parent1_score", 0) + s.get("parent2_score", 0)
                for s in p
            )
            path_candidates.append({
                "path": p,
                "total_matched": total_matched,
                "total_score": total_score,
                "step_count": len(p),
            })

        path_candidates.sort(
            key=lambda x: (x["total_matched"], -x["step_count"], x["total_score"]),
            reverse=True,
        )

        formatted_paths = []
        for idx, item in enumerate(path_candidates[:5]):
            p = item["path"]
            total_steps = len(p)
            has_hard_gender = any(s.get("hatch_chance_pct") in ["10%", "20%"] for s in p)
            difficulty_label = "Challenging (Low Gender Hatch Rate)" if has_hard_gender else "Easy (High Gender Hatch Rate)"
            
            title = f"Path {idx + 1} ({total_steps} Step{'s' if total_steps > 1 else ''}{' - Recommended' if idx == 0 else ' - Alternative'})"
            formatted_paths.append({
                "path_id": idx + 1,
                "title": title,
                "difficulty": difficulty_label,
                "total_quality_score": round(item["total_score"], 1),
                "matched_skills_count": item["total_matched"],
                "steps": p
            })

        return formatted_paths

    def find_breeding_path(
        self,
        owned_input: Any,
        target_species: str,
        target_skills: Optional[Any] = None,
    ) -> list[dict[str, Any]]:
        """Breadth-First Search (BFS) pathfinder returning steps of the top recommended path."""
        all_paths = self.find_all_breeding_paths(owned_input, target_species, target_skills)
        if all_paths:
            return all_paths[0]["steps"]
        return []

    # ---------- Querying APIs ----------

    def query_pals(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Queries static Pals metadata table with multiple filter conditions."""
        query = "SELECT * FROM pals WHERE 1=1"
        params: list[Any] = []

        if "element" in filters:
            el = filters["element"].lower()
            el_matches = [el]
            if el in ("normal", "neutral"):
                el_matches = ["normal", "neutral"]
            elif el in ("leaf", "grass"):
                el_matches = ["leaf", "grass"]
            elif el in ("electricity", "electric"):
                el_matches = ["electricity", "electric"]

            query += f" AND (LOWER(element_1) IN ({','.join('?' for _ in el_matches)}) OR LOWER(element_2) IN ({','.join('?' for _ in el_matches)}))"
            params.extend(el_matches + el_matches)

        if "nocturnal" in filters:
            query += " AND nocturnal = ?"
            params.append(1 if filters["nocturnal"] else 0)

        if "size" in filters:
            query += " AND size = ?"
            params.append(filters["size"])

        if "is_variant" in filters:
            query += " AND is_variant = ?"
            params.append(1 if filters["is_variant"] else 0)

        if "work_suitability" in filters:
            s_filter = filters["work_suitability"]
            raw_s_name = str(s_filter.get("name", "")).lower()
            ws_map = {
                "handiwork": ["handiwork", "handcraft"],
                "handcraft": ["handiwork", "handcraft"],
                "generating_electricity": ["generating_electricity", "electricity"],
                "electricity": ["generating_electricity", "electricity"],
                "medicine_production": ["medicine_production", "medicine"],
                "medicine": ["medicine_production", "medicine"],
                "transporting": ["transporting", "transport"],
                "transport": ["transporting", "transport"],
                "farming": ["farming", "monsterfarm"],
                "monsterfarm": ["farming", "monsterfarm"],
            }
            s_names = ws_map.get(raw_s_name, [raw_s_name])
            query += f""" AND internal_name IN (
                SELECT pal_internal_name FROM pal_work_suitabilities
                WHERE LOWER(suitability_name) IN ({','.join('?' for _ in s_names)})
            """
            params.extend(s_names)
            if "min_level" in s_filter:
                query += " AND level >= ?"
                params.append(s_filter["min_level"])
            query += ")"

        query += " ORDER BY paldex_number ASC"

        rows = self.conn.execute(query, params).fetchall()
        results = []

        use_palworld_db = (
            self.source == "palworld_db" and os.path.exists(self.palworld_db_path)
        )

        for r in rows:
            pal_dict = dict(r)
            pal_dict["icon_path"] = transform_icon_path(pal_dict.get("icon_path"))

            if use_palworld_db:
                pal_id = pal_dict.get("internal_name") or pal_dict.get("id")
                pal_key = str(pal_dict.get("internal_name") or pal_dict.get("id") or "").lower().strip()
                # Attach skills from palworld_master
                try:
                    s_rows = self.conn.execute(
                        """
                        SELECT s.id, s.name, s.element, s.type, s.category, s.power, s.cooldown,
                               s.min_range, s.max_range, s.stat_modifier, s.unlock_item,
                               s.description, s.icon_path, ps.level_learned, ps.is_guaranteed
                        FROM palworld_master.pal_skills ps
                        JOIN palworld_master.skills s ON ps.skill_id = s.id
                        WHERE LOWER(ps.pal_id) = LOWER(?) OR ps.pal_id = ?
                        ORDER BY ps.level_learned ASC, s.name ASC
                    """,
                        (pal_id, pal_id),
                    ).fetchall()
                    pal_skills_list = []
                    for sr in s_rows:
                        s_dict = dict(sr)
                        s_name = s_dict.get("name")
                        s_type = s_dict.get("type")
                        s_cat = s_dict.get("category")
                        s_desc = clean_skill_text(s_dict.get("description"))
                        s_item = s_dict.get("unlock_item")

                        # Apply official partner skill overrides if applicable
                        if (s_type == "Partner" or s_cat == "Partner") and pal_key in PARTNER_SKILL_OVERRIDES:
                            ov = PARTNER_SKILL_OVERRIDES[pal_key]
                            if "name" in ov:
                                s_name = ov["name"]
                            if "description" in ov:
                                s_desc = ov["description"]
                            if "unlock_item" in ov:
                                s_item = ov["unlock_item"]

                        pal_skills_list.append({
                            "id": s_dict.get("id"),
                            "name": s_name,
                            "element": s_dict.get("element"),
                            "type": s_type,
                            "category": s_cat,
                            "power": s_dict.get("power"),
                            "cooldown": s_dict.get("cooldown"),
                            "min_range": s_dict.get("min_range"),
                            "max_range": s_dict.get("max_range"),
                            "stat_modifier": clean_skill_text(s_dict.get("stat_modifier")),
                            "unlock_item": s_item,
                            "description": s_desc,
                            "icon_path": transform_icon_path(s_dict.get("icon_path")),
                            "level_learned": s_dict.get("level_learned"),
                            "is_guaranteed": s_dict.get("is_guaranteed", 0),
                        })

                    pal_dict["skills"] = pal_skills_list
                    partner_skills = [sk for sk in pal_dict["skills"] if (sk.get("type") == "Partner" or sk.get("category") == "Partner")]
                    pal_dict["partner_skill"] = partner_skills[0] if partner_skills else None
                except Exception as e:
                    pal_dict["skills"] = []
                    pal_dict["partner_skill"] = None

                # Attach work suitabilities from palworld_master
                try:
                    ws_rows = self.conn.execute(
                        "SELECT work_type, level FROM palworld_master.work_suitability WHERE pal_id = ? ORDER BY level DESC",
                        (pal_id,),
                    ).fetchall()
                    
                    work_type_map = {
                        "EmitFlame": ("Kindling", "Kindling.png"),
                        "Kindling": ("Kindling", "Kindling.png"),
                        "Watering": ("Watering", "Watering.png"),
                        "Seeding": ("Planting", "Planting.png"),
                        "Planting": ("Planting", "Planting.png"),
                        "GenerateElectricity": ("Generating Electricity", "GeneratingElectricity.png"),
                        "Electricity": ("Generating Electricity", "GeneratingElectricity.png"),
                        "GeneratingElectricity": ("Generating Electricity", "GeneratingElectricity.png"),
                        "Handcraft": ("Handiwork", "Handcraft.png"),
                        "Collection": ("Gathering", "Gathering.png"),
                        "Gathering": ("Gathering", "Gathering.png"),
                        "Deforest": ("Lumbering", "Lumbering.png"),
                        "Wood": ("Lumbering", "Lumbering.png"),
                        "Lumbering": ("Lumbering", "Lumbering.png"),
                        "Mining": ("Mining", "Mining.png"),
                        "Mine": ("Mining", "Mining.png"),
                        "ProductMedicine": ("Medicine Production", "Medicine.png"),
                        "Medicine": ("Medicine Production", "Medicine.png"),
                        "Cool": ("Cooling", "Cooling.png"),
                        "Cooling": ("Cooling", "Cooling.png"),
                        "Transport": ("Transporting", "Transport.png"),
                        "Transporting": ("Transporting", "Transport.png"),
                        "MonsterFarm": ("Farming", "MonsterFarm.png"),
                        "Farming": ("Farming", "MonsterFarm.png"),
                        "OilExtraction": ("Oil Extraction", "OilExtraction.png"),
                    }
                    
                    ws_suitabilities = {}
                    ws_details = []
                    for wsr in ws_rows:
                        raw_type = wsr["work_type"]
                        name, icon_name = work_type_map.get(raw_type, (raw_type, f"{raw_type}.png"))
                        level = wsr["level"]
                        ws_suitabilities[name] = level
                        ws_details.append({
                            "id": raw_type,
                            "name": name,
                            "level": level,
                            "icon_path": f"/assets/work/{icon_name}"
                        })

                    pal_dict["work_suitabilities"] = ws_suitabilities
                    pal_dict["work_suitability_details"] = ws_details
                except Exception:
                    pal_dict["work_suitabilities"] = {}
                    pal_dict["work_suitability_details"] = []

                # Attach drops from palworld_master
                try:
                    drop_rows = self.conn.execute(
                        """
                        SELECT d.item_id, d.item_name, d.min_quantity, d.max_quantity, d.drop_rate, i.icon_path
                        FROM palworld_master.drops d
                        LEFT JOIN palworld_master.items i ON d.item_id = i.id
                        WHERE d.pal_id = ?
                        """,
                        (pal_id,),
                    ).fetchall()
                    pal_dict["drops"] = [
                        {
                            "item_id": dr["item_id"],
                            "item_name": dr["item_name"],
                            "min_quantity": dr["min_quantity"],
                            "max_quantity": dr["max_quantity"],
                            "drop_rate": dr["drop_rate"],
                            "icon_path": transform_icon_path(dr["icon_path"]) if dr.get("icon_path") else transform_icon_path(f"C:/palworld_assets/items/{dr['item_id']}.png")
                        }
                        for dr in drop_rows
                    ]
                except Exception:
                    pal_dict["drops"] = []

            results.append(pal_dict)

        return results

    def query_items(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Queries items catalog with optional category, subcategory, and rarity filters."""
        if not (self.source == "palworld_db" and os.path.exists(self.palworld_db_path)):
            return []

        query = "SELECT * FROM palworld_master.items WHERE 1=1"
        params: list[Any] = []

        if "category" in filters and filters["category"]:
            query += " AND LOWER(category) = LOWER(?)"
            params.append(filters["category"])

        if "rarity" in filters and filters["rarity"] is not None:
            query += " AND rarity = ?"
            params.append(filters["rarity"])

        if "search" in filters and filters["search"]:
            query += " AND (LOWER(name) LIKE LOWER(?) OR LOWER(id) LIKE LOWER(?))"
            s = f"%{filters['search']}%"
            params.extend([s, s])

        query += " ORDER BY rarity DESC, name ASC"

        rows = self.conn.execute(query, params).fetchall()
        results = []
        assets_dir = get_assets_dir()
        for r in rows:
            d = dict(r)
            raw_path = d.get("icon_path")
            if raw_path and assets_dir:
                filename = os.path.basename(raw_path.replace("\\", "/"))
                local_file = os.path.join(assets_dir, "items", filename)
                if not os.path.exists(local_file):
                    continue
            d["icon_path"] = transform_icon_path(raw_path)
            results.append(d)
        return results

    def get_item_recipe(self, item_id: str) -> Optional[dict[str, Any]]:
        """Retrieves crafting recipe and material costs for a specific item_id."""
        if not (self.source == "palworld_db" and os.path.exists(self.palworld_db_path)):
            return None

        r_row = self.conn.execute(
            """
            SELECT r.*, i.name as item_name, b.name as facility_name, b.icon_path as facility_icon
            FROM palworld_master.recipes r
            JOIN palworld_master.items i ON r.item_id = i.id
            LEFT JOIN palworld_master.buildings b ON r.facility_id = b.id
            WHERE r.item_id = ? OR r.id = ?
            """,
            (item_id, item_id),
        ).fetchone()

        if not r_row:
            return None

        recipe_dict = dict(r_row)
        recipe_dict["facility_icon"] = transform_icon_path(recipe_dict.get("facility_icon"))

        ing_rows = self.conn.execute(
            """
            SELECT ri.*, i.icon_path
            FROM palworld_master.recipe_ingredients ri
            LEFT JOIN palworld_master.items i ON ri.material_item_id = i.id
            WHERE ri.recipe_id = ?
            """,
            (recipe_dict["id"],),
        ).fetchall()

        ingredients = []
        for ing in ing_rows:
            d = dict(ing)
            d["icon_path"] = transform_icon_path(d.get("icon_path"))
            ingredients.append(d)

        recipe_dict["ingredients"] = ingredients
        return recipe_dict

    def query_buildings(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Queries base camp buildings & infrastructure."""
        if not (self.source == "palworld_db" and os.path.exists(self.palworld_db_path)):
            return []

        query = "SELECT * FROM palworld_master.buildings WHERE 1=1"
        params: list[Any] = []

        if "category" in filters and filters["category"]:
            query += " AND LOWER(category) = LOWER(?)"
            params.append(filters["category"])

        if "search" in filters and filters["search"]:
            query += " AND (LOWER(name) LIKE LOWER(?) OR LOWER(id) LIKE LOWER(?))"
            s = f"%{filters['search']}%"
            params.extend([s, s])

        query += " ORDER BY tech_level ASC, name ASC"

        rows = self.conn.execute(query, params).fetchall()
        results = []
        assets_dir = get_assets_dir()
        for r in rows:
            d = dict(r)
            raw_path = d.get("icon_path")
            if raw_path and assets_dir:
                filename = os.path.basename(raw_path.replace("\\", "/"))
                local_file = os.path.join(assets_dir, "buildings", filename)
                if not os.path.exists(local_file):
                    continue
            d["icon_path"] = transform_icon_path(raw_path)
            results.append(d)
        return results

    def query_tech_tree(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Queries technology tree unlock nodes."""
        if not (self.source == "palworld_db" and os.path.exists(self.palworld_db_path)):
            return []

        query = "SELECT * FROM palworld_master.technology_tree WHERE 1=1"
        params: list[Any] = []

        if "level" in filters and filters["level"] is not None:
            query += " AND level = ?"
            params.append(filters["level"])

        if "is_ancient" in filters and filters["is_ancient"] is not None:
            query += " AND is_ancient = ?"
            params.append(1 if filters["is_ancient"] else 0)

        query += " ORDER BY level ASC, name ASC"

        rows = self.conn.execute(query, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            results.append(d)
        return results

    def query_work_types(self) -> list[dict[str, Any]]:
        """Queries all 12 official Palworld work suitability types with HUD icon paths."""
        if not (self.source == "palworld_db" and os.path.exists(self.palworld_db_path)):
            return []

        rows = self.conn.execute("SELECT * FROM palworld_master.work_types ORDER BY name ASC").fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["icon_path"] = transform_icon_path(d.get("icon_path"))
            results.append(d)
        return results

    def query_skills(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Queries skills (Active, Passive, Partner) catalog from master DB or legacy tables."""
        use_palworld_db = (
            self.source == "palworld_db" and os.path.exists(self.palworld_db_path)
        )

        SYNONYMS_MAP = {
            "farm": ["farm", "farming", "ranch", "ranching", "crop", "crops", "breeding farm"],
            "farming": ["farm", "farming", "ranch", "ranching", "crop", "crops", "breeding farm"],
            "ranch": ["ranch", "ranching", "farm", "farming"],
            "ranching": ["ranch", "ranching", "farm", "farming"],
            "egg": ["egg", "eggs", "incubat", "hatch", "breeding"],
            "eggs": ["egg", "eggs", "incubat", "hatch", "breeding"],
            "breed": ["breed", "breeding", "egg", "eggs", "offspring"],
            "breeding": ["breed", "breeding", "egg", "eggs", "offspring"],
        }

        def skill_matches_search(skill: dict, search_str: str) -> bool:
            if not search_str:
                return True
            s_clean = search_str.lower().strip()
            terms = SYNONYMS_MAP.get(s_clean, [s_clean])
            haystack = " ".join([
                str(skill.get("name") or ""),
                str(skill.get("pal_name") or ""),
                str(skill.get("description") or ""),
                str(skill.get("stat_modifier") or ""),
                str(skill.get("unlock_item") or ""),
                str(skill.get("category") or ""),
                str(skill.get("element") or ""),
                str(skill.get("type") or ""),
                " ".join(skill.get("learned_by_pals") or [])
            ]).lower()
            return any(t in haystack for t in terms)

        results = []
        if use_palworld_db:
            q_type = str(filters.get("type", "")).strip().capitalize() if filters.get("type") else ""
            el_filter = str(filters.get("element", "")).strip().lower() if filters.get("element") else ""
            cat_filter = str(filters.get("category", "")).strip().lower() if filters.get("category") else ""
            search_str = str(filters.get("search", "")).strip().lower() if filters.get("search") else ""

            # 1. Partner Skills (Playable Pals only)
            if not q_type or q_type == "Partner":
                prt_query = """
                    SELECT 
                        s.id, s.name, s.element, s.type, s.power, s.cooldown, s.description,
                        s.category, s.stat_modifier, s.unlock_item,
                        p.id as pal_id,
                        p.name as pal_name,
                        p.paldex_number,
                        p.icon_path as pal_icon,
                        coalesce(s.icon_path, p.icon_path) as icon_path
                    FROM palworld_master.skills s
                    JOIN palworld_master.pal_skills ps ON s.id = ps.skill_id
                    JOIN palworld_master.pals p ON ps.pal_id = p.id
                    WHERE s.type = 'Partner'
                      AND p.paldex_number > 0
                      AND s.name != '-' AND s.name != ''
                      AND s.id NOT LIKE 'CollectItem_%'
                """
                prt_params: list[Any] = []
                if el_filter:
                    prt_query += " AND (LOWER(s.element) = ? OR LOWER(p.element1) = ? OR LOWER(coalesce(p.element2, '')) = ?)"
                    prt_params.extend([el_filter, el_filter, el_filter])
                if cat_filter:
                    prt_query += " AND LOWER(s.category) = ?"
                    prt_params.append(cat_filter)
                prt_query += " ORDER BY p.paldex_number ASC, p.name ASC"

                for r in self.conn.execute(prt_query, prt_params).fetchall():
                    d = dict(r)
                    pal_key = str(d.get("pal_id") or "").lower().strip()
                    if pal_key in PARTNER_SKILL_OVERRIDES:
                        ov = PARTNER_SKILL_OVERRIDES[pal_key]
                        if "name" in ov:
                            d["name"] = ov["name"]
                        if "description" in ov:
                            d["description"] = ov["description"]
                        if "unlock_item" in ov:
                            d["unlock_item"] = ov["unlock_item"]
                    d["icon_path"] = transform_icon_path(d.get("icon_path"))
                    d["pal_icon"] = transform_icon_path(d.get("pal_icon"))
                    d["description"] = clean_skill_text(d.get("description"))
                    d["stat_modifier"] = clean_skill_text(d.get("stat_modifier"))
                    if skill_matches_search(d, search_str):
                        results.append(d)

            # 2. Active Combat Skills (Playable Pals only)
            if not q_type or q_type == "Active":
                act_query = """
                    SELECT 
                        s.id, s.name, s.element, s.type, s.power, s.cooldown, s.description,
                        s.category, s.stat_modifier, s.unlock_item, s.icon_path,
                        GROUP_CONCAT(DISTINCT p.name) as learned_by_pals
                    FROM palworld_master.skills s
                    JOIN palworld_master.pal_skills ps ON s.id = ps.skill_id
                    JOIN palworld_master.pals p ON ps.pal_id = p.id
                    WHERE s.type = 'Active'
                      AND p.paldex_number > 0
                      AND s.name != '-' AND s.name != ''
                      AND s.id NOT LIKE 'CollectItem_%'
                """
                act_params: list[Any] = []
                if el_filter:
                    act_query += " AND LOWER(s.element) = ?"
                    act_params.append(el_filter)
                if cat_filter:
                    act_query += " AND LOWER(s.category) = ?"
                    act_params.append(cat_filter)
                act_query += " GROUP BY s.id ORDER BY s.name ASC"

                for r in self.conn.execute(act_query, act_params).fetchall():
                    d = dict(r)
                    d["cooldown_sec"] = d.get("cooldown")
                    d["icon_path"] = transform_icon_path(d.get("icon_path"))
                    d["description"] = clean_skill_text(d.get("description"))
                    d["stat_modifier"] = clean_skill_text(d.get("stat_modifier"))
                    if d.get("learned_by_pals"):
                        d["learned_by_pals"] = [p.strip() for p in d["learned_by_pals"].split(",") if p.strip()]
                    if skill_matches_search(d, search_str):
                        results.append(d)

            # 3. Passive Skills (Filter dummy entries)
            if not q_type or q_type == "Passive":
                pas_query = """
                    SELECT 
                        s.id, s.name, s.element, s.type, s.power, s.cooldown, s.description,
                        s.category, s.stat_modifier, s.unlock_item, s.icon_path
                    FROM palworld_master.skills s
                    WHERE s.type = 'Passive'
                      AND s.name != '-' AND s.name != ''
                      AND s.id NOT LIKE 'CollectItem_%'
                """
                pas_params: list[Any] = []
                if el_filter:
                    pas_query += " AND LOWER(s.element) = ?"
                    pas_params.append(el_filter)
                if cat_filter:
                    pas_query += " AND LOWER(s.category) = ?"
                    pas_params.append(cat_filter)
                pas_query += " ORDER BY s.name ASC"

                for r in self.conn.execute(pas_query, pas_params).fetchall():
                    d = dict(r)
                    d["icon_path"] = transform_icon_path(d.get("icon_path"))
                    d = enrich_passive_skill(d)
                    if skill_matches_search(d, search_str):
                        results.append(d)

        else:
            query_type = str(filters.get("type", "")).capitalize() if filters.get("type") else ""
            search_str = str(filters.get("search", "")).lower() if filters.get("search") else ""

            if not query_type or query_type == "Active":
                act_rows = self.conn.execute("SELECT *, 'Active' as type FROM active_skills WHERE name != '-' AND name != ''").fetchall()
                for r in act_rows:
                    d = dict(r)
                    if search_str and search_str not in d.get("name", "").lower() and search_str not in d.get("id", "").lower() and search_str not in str(d.get("description", "")).lower():
                        continue
                    d["icon_path"] = transform_icon_path(d.get("icon_path"))
                    results.append(d)

            if not query_type or query_type == "Passive":
                pas_rows = self.conn.execute("SELECT *, 'Passive' as type FROM passive_skills WHERE name != '-' AND name != ''").fetchall()
                for r in pas_rows:
                    d = dict(r)
                    if search_str and search_str not in d.get("name", "").lower() and search_str not in d.get("id", "").lower() and search_str not in str(d.get("description", "")).lower():
                        continue
                    results.append(d)

            if not query_type or query_type == "Partner":
                prt_rows = self.conn.execute("SELECT *, 'Partner' as type FROM partner_skills WHERE name != '-' AND name != ''").fetchall()
                for r in prt_rows:
                    d = dict(r)
                    if search_str and search_str not in d.get("name", "").lower() and search_str not in d.get("id", "").lower() and search_str not in str(d.get("description", "")).lower():
                        continue
                    results.append(d)

        if "source" in filters and filters["source"]:
            src_val = str(filters["source"]).strip().lower()
            results = [s for s in results if str(s.get("source", "")).strip().lower() == src_val]

        return results

    def query_instances(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Queries dynamic Pal instances table with multiple filter conditions."""
        query = """
            SELECT pi.*,
                   coalesce(p.display_name, pi.species) as display_name,
                   p.element_1, p.element_2, p.hp, p.attack_melee, p.defense, p.icon_path
            FROM pal_instances pi
            LEFT JOIN pals p ON LOWER(pi.species) = LOWER(p.internal_name)
                             OR LOWER(pi.species) = LOWER(p.display_name)
                             OR LOWER(pi.species) = LOWER(p.id)
                             OR LOWER(pi.species) = LOWER(p.code)
                             OR REPLACE(LOWER(pi.species), 'boss_', '') = LOWER(p.internal_name)
                             OR REPLACE(LOWER(pi.species), 'boss_', '') = LOWER(p.display_name)
                             OR REPLACE(LOWER(pi.species), 'boss_', '') = LOWER(p.id)
                             OR REPLACE(LOWER(pi.species), 'boss_', '') = LOWER(p.code)
            WHERE 1=1
        """
        params: list[Any] = []

        if "species" in filters:
            query += " AND (LOWER(coalesce(p.display_name, pi.species)) = ? OR LOWER(pi.species) = ?)"
            params.extend([filters["species"].lower(), filters["species"].lower()])

        if "location" in filters:
            query += " AND pi.location = ?"
            params.append(filters["location"])

        if "gender" in filters:
            query += " AND pi.gender = ?"
            params.append(filters["gender"])

        if "min_level" in filters:
            query += " AND pi.level >= ?"
            params.append(filters["min_level"])

        if "min_rank" in filters:
            query += " AND pi.rank >= ?"
            params.append(filters["min_rank"])

        if "min_iv_hp" in filters:
            query += " AND pi.iv_hp >= ?"
            params.append(filters["min_iv_hp"])

        if "min_iv_melee" in filters:
            query += " AND pi.iv_melee >= ?"
            params.append(filters["min_iv_melee"])

        if "min_iv_shot" in filters:
            query += " AND pi.iv_shot >= ?"
            params.append(filters["min_iv_shot"])

        if "min_iv_defense" in filters:
            query += " AND pi.iv_defense >= ?"
            params.append(filters["min_iv_defense"])

        if "instance_id" in filters:
            query += " AND pi.instance_id = ?"
            params.append(filters["instance_id"])

        if "passive_id" in filters:
            query += """ AND pi.instance_id IN (
                SELECT instance_id FROM pal_instance_passives
                WHERE LOWER(passive_id) = ?
            )"""
            params.append(filters["passive_id"].lower())

        query += " ORDER BY pi.level DESC, pi.species ASC"

        rows = self.conn.execute(query, params).fetchall()

        results = []
        use_palworld_db = (
            self.source == "palworld_db" and os.path.exists(self.palworld_db_path)
        )

        for r in rows:
            d = dict(r)
            d["icon_path"] = transform_icon_path(d.get("icon_path"))
            if use_palworld_db:
                p_rows = self.conn.execute(
                    """
                    SELECT COALESCE(s.name, pip.passive_id) as name,
                           pip.passive_id as id,
                           s.power as rank,
                           s.description,
                           s.stat_modifier,
                           s.category,
                           'Passive' as type,
                           s.icon_path
                    FROM pal_instance_passives pip
                    LEFT JOIN palworld_master.skills s ON LOWER(pip.passive_id) = LOWER(s.id) OR LOWER(pip.passive_id) = LOWER(s.name)
                    WHERE pip.instance_id = ?
                """,
                    (d["instance_id"],),
                ).fetchall()
            else:
                p_rows = self.conn.execute(
                    """
                    SELECT COALESCE(ps.name, pip.passive_id) as name, pip.passive_id as id, ps.rank, ps.description, 'Passive' as type
                    FROM pal_instance_passives pip
                    LEFT JOIN passive_skills ps ON LOWER(pip.passive_id) = LOWER(ps.id)
                    WHERE pip.instance_id = ?
                """,
                    (d["instance_id"],),
                ).fetchall()
            
            passives_list = []
            for pr in p_rows:
                pd = dict(pr)
                pd["icon_path"] = transform_icon_path(pd.get("icon_path"))
                pd = enrich_passive_skill(pd)
                passives_list.append(pd)
            d["passives"] = passives_list
            
            # Fetch Waza (Attacks) with full metadata
            if use_palworld_db:
                w_rows = self.conn.execute(
                    """
                    SELECT piw.waza_id as id,
                           piw.is_equipped,
                           COALESCE(s.name, REPLACE(piw.waza_id, 'EPalWazaID::', '')) as name,
                           s.element,
                           s.power,
                           s.cooldown,
                           s.icon_path,
                           s.description,
                           'Active' as type
                    FROM pal_instance_waza piw
                    LEFT JOIN palworld_master.skills s 
                           ON LOWER(piw.waza_id) = LOWER(s.id) 
                           OR LOWER(piw.waza_id) = LOWER(REPLACE(s.id, 'EPalWazaID::', ''))
                           OR LOWER(piw.waza_id) = LOWER(s.name)
                    WHERE piw.instance_id = ?
                    ORDER BY piw.is_equipped DESC, s.power DESC
                    """,
                    (d["instance_id"],)
                ).fetchall()
            else:
                w_rows = self.conn.execute(
                    "SELECT waza_id as id, is_equipped, waza_id as name, 'Active' as type FROM pal_instance_waza WHERE instance_id = ?",
                    (d["instance_id"],)
                ).fetchall()

            equipped_waza = []
            mastered_waza = []
            for wr in w_rows:
                wd = dict(wr)
                wd["cooldown_sec"] = wd.get("cooldown")
                wd["icon_path"] = transform_icon_path(wd.get("icon_path"))
                wd["description"] = clean_skill_text(wd.get("description"))
                if wd.get("is_equipped") == 1:
                    equipped_waza.append(wd)
                else:
                    mastered_waza.append(wd)

            d["equip_waza"] = equipped_waza
            d["mastered_waza"] = mastered_waza
            
            # Fetch Status Points
            sp_rows = self.conn.execute(
                "SELECT stat_name, points, type FROM pal_instance_status_points WHERE instance_id = ?",
                (d["instance_id"],)
            ).fetchall()
            d["soul_points"] = {r["stat_name"]: r["points"] for r in sp_rows if r["type"] == "soul"}
            d["elixir_points"] = {r["stat_name"]: r["points"] for r in sp_rows if r["type"] == "elixir"}
            
            results.append(d)

        return results

    def get_base_camp_summary(self, base_camp_id: str) -> Optional[dict[str, Any]]:
        """Returns details, workers, and structure counts for a given Base Camp."""
        base_row = self.conn.execute(
            "SELECT * FROM base_camps WHERE base_camp_id = ?", (base_camp_id,)
        ).fetchone()

        if not base_row:
            return None

        summary = dict(base_row)

        struct_rows = self.conn.execute(
            """
            SELECT bsi.structure_name, bsi.count, bs.name as display_name, bs.category
            FROM base_structures_instances bsi
            LEFT JOIN base_structures bs ON LOWER(bsi.structure_name) = LOWER(bs.id)
                                         OR LOWER(bsi.structure_name) = LOWER(bs.name)
            WHERE bsi.base_camp_id = ?
            ORDER BY bsi.structure_name ASC
        """,
            (base_camp_id,),
        ).fetchall()
        summary["structures"] = [dict(r) for r in struct_rows]

        summary["workers"] = self.query_instances(
            {"location": "base", "min_level": 1}
        )
        summary["workers"] = [
            w
            for w in summary["workers"]
            if w.get("location_details_base_camp_id") == base_camp_id
        ]

        return summary


    def query_inventory(self, container_type: Optional[str] = None) -> list[dict[str, Any]]:
        """Queries item inventory from dynamic save data joined with static master items table."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) as c FROM item_containers")
            if cursor.fetchone()["c"] == 0:
                return []
        except Exception:
            return []

        query = """
            SELECT 
                c.container_id,
                c.container_type,
                c.slot_count,
                s.slot_index,
                s.item_id,
                s.count,
                m.name as display_name,
                m.category,
                m.subcategory,
                m.rarity,
                m.weight,
                m.price,
                m.icon_path,
                m.description
            FROM item_containers c
            JOIN item_container_slots s ON c.container_id = s.container_id
            LEFT JOIN palworld_master.items m ON LOWER(s.item_id) = LOWER(m.id)
        """
        params = []
        if container_type:
            query += " WHERE c.container_type = ?"
            params.append(container_type)
            
        query += " ORDER BY c.container_type, s.slot_index"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            d = dict(r)
            if not d["display_name"]:
                d["display_name"] = d["item_id"]
            if d["icon_path"]:
                parts = d["icon_path"].split("/")
                d["icon_path"] = "/assets/" + parts[-2] + "/" + parts[-1]
            results.append(d)
            
        return results

    def get_condense_candidates(self) -> list[dict]:
        from collections import defaultdict
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as c FROM pal_instances")
        count = cursor.fetchone()["c"]
        if count < 1:
            return []

        pal_metadata = {}
        for row in self.conn.execute("SELECT id, code, name, hp, attack, defense, icon_path FROM palworld_master.pals"):
            data = {
                "name": row["name"],
                "hp": row["hp"],
                "attack": row["attack"],
                "defense": row["defense"],
                "icon_path": row["icon_path"],
            }
            if row["id"]:
                pal_metadata[row["id"].lower()] = data
            if row["code"]:
                pal_metadata[row["code"].lower()] = data

        for row in self.conn.execute("SELECT id, code, internal_name, display_name, hp, attack_melee, defense, icon_path FROM pals"):
            data = {
                "name": row["display_name"] or row["internal_name"] or row["id"],
                "hp": row["hp"],
                "attack": row["attack_melee"],
                "defense": row["defense"],
                "icon_path": row["icon_path"],
            }
            if row["id"]:
                pal_metadata[row["id"].lower()] = data
            if row["code"]:
                pal_metadata[row["code"].lower()] = data
            if row["internal_name"]:
                pal_metadata[row["internal_name"].lower()] = data

        skill_metadata = {}
        for row in self.conn.execute("SELECT id, name, CAST(rank AS TEXT) as category FROM passive_skills"):
            skill_metadata[row["id"].lower()] = {
                "name": row["name"],
                "category": row["category"] or "PassiveTier1"
            }

        cursor.execute("""
            SELECT i.instance_id, i.species, i.level, i.rank, i.iv_hp, i.iv_melee, i.iv_defense,
                   GROUP_CONCAT(p.passive_id, ',') as passives
            FROM pal_instances i
            LEFT JOIN pal_instance_passives p ON i.instance_id = p.instance_id
            GROUP BY i.instance_id
        """)
        instances = [dict(r) for r in cursor.fetchall()]

        species_groups = defaultdict(list)
        for inst in instances:
            raw_species = inst.get('species')
            if not raw_species:
                continue

            clean_species = raw_species.lower()
            if clean_species.startswith("boss_"):
                clean_species = clean_species[5:]

            meta = pal_metadata.get(clean_species) or pal_metadata.get(raw_species.lower())
            if not meta:
                # Skip unmapped non-Pals (human NPCs / enemies)
                continue

            display_species = meta['name']
            inst['display_species'] = display_species
            inst['base_stats'] = meta
            
            raw_passives = (inst.get('passives') or '').split(',')
            display_passives = []
            passive_score = 0
            for p in raw_passives:
                p = p.strip()
                if p and p != 'None':
                    s_meta = skill_metadata.get(p.lower())
                    if s_meta:
                        display_passives.append(s_meta["name"])
                        passive_score += 50
                    else:
                        display_passives.append(p)
                        
            inst['display_passives'] = display_passives
            inst['passive_score'] = passive_score
            species_groups[display_species].append(inst)

        candidates = []
        for display_species, pals in species_groups.items():
            if len(pals) < 2:
                continue
                
            def get_score(p):
                iv_hp = p.get('iv_hp') or 0
                iv_atk = p.get('iv_melee') or 0
                iv_def = p.get('iv_defense') or 0
                iv_sum = iv_hp + iv_atk + iv_def
                p_score = p.get('passive_score', 0)
                curr_rank = p.get('rank', 0) or 0
                return (curr_rank * 5000) + (p_score * 1000) + (p.get('level', 0) or 0) * 100 + iv_sum

            pals.sort(key=get_score, reverse=True)
            best_pal = pals[0]
            
            candidates.append({
                'species': display_species,
                'count': len(pals),
                'best_pal': best_pal,
                'score': len(pals) * 100000 + get_score(best_pal)
            })
            
        candidates.sort(key=lambda x: (x['count'], x['score']), reverse=True)

        results = []
        for c in candidates[:10]:
            species = c['species']
            total_owned = c['count']
            sacrifices = total_owned - 1
            best = c['best_pal']
            
            lvl = best.get('level') or 1
            curr_rank = best.get('rank', 0) or 0
            iv_hp = best.get('iv_hp') or 0
            iv_atk = best.get('iv_melee') or 0
            iv_def = best.get('iv_defense') or 0
            passives_list = best.get('display_passives', [])
            
            needed_per_rank = {0: 4, 1: 16, 2: 32, 3: 64}
            rem_sacrifices = sacrifices
            attainable_stars = curr_rank
            while attainable_stars < 4 and rem_sacrifices >= needed_per_rank.get(attainable_stars, 9999):
                rem_sacrifices -= needed_per_rank[attainable_stars]
                attainable_stars += 1

            sp_base = best['base_stats']
            
            def calc_hp(base, l, iv):
                return int(500 + 5 * l + (base * 0.5 * l) * (1 + (iv * 0.3) / 100))
                
            def calc_atk(base, l, iv, passives):
                val = 100 + (base * 0.075 * l) * (1 + (iv * 0.3) / 100)
                mult = 1.0
                passives_lower = [p.strip().lower() for p in passives]
                if 'musclehead' in passives_lower: mult += 0.30
                if 'ferocious' in passives_lower: mult += 0.20
                if 'coward' in passives_lower: mult -= 0.10
                if 'pacifist' in passives_lower: mult -= 0.20
                if 'hooligan' in passives_lower: mult += 0.15
                if 'sadist' in passives_lower: mult += 0.15
                return int(val * mult)
                
            def calc_def(base, l, iv, passives):
                val = 50 + (base * 0.075 * l) * (1 + (iv * 0.3) / 100)
                mult = 1.0
                passives_lower = [p.strip().lower() for p in passives]
                if 'burly body' in passives_lower: mult += 0.20
                if 'masochist' in passives_lower: mult += 0.15
                if 'downtrodden' in passives_lower: mult -= 0.10
                if 'hooligan' in passives_lower: mult -= 0.10
                return int(val * mult)

            est_hp = calc_hp(sp_base.get("hp", 100), lvl, iv_hp)
            est_atk = calc_atk(sp_base.get("attack", 100), lvl, iv_atk, passives_list)
            est_def = calc_def(sp_base.get("defense", 100), lvl, iv_def, passives_list)
            
            icon_path = None
            raw_icon = sp_base.get('icon_path')
            if raw_icon:
                parts = raw_icon.replace('\\', '/').split('/')
                icon_path = "/assets/" + parts[-2] + "/" + parts[-1]

            results.append({
                'species': species,
                'total_owned': total_owned,
                'sacrifices_available': sacrifices,
                'attainable_stars': attainable_stars,
                'base_level': lvl,
                'hp': est_hp,
                'attack': est_atk,
                'defense': est_def,
                'iv_hp': iv_hp,
                'iv_attack': iv_atk,
                'iv_defense': iv_def,
                'passives': passives_list,
                'icon_path': icon_path
            })
            
        return results

    def get_building_work_types(self, building_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Returns work suitability requirements for buildings."""
        cursor = self.conn.cursor()
        if building_id:
            rows = cursor.execute(
                "SELECT * FROM building_work_types WHERE building_id=?", (building_id,)
            ).fetchall()
        else:
            rows = cursor.execute("SELECT * FROM building_work_types").fetchall()
        return [dict(r) for r in rows]

    def get_food_satiety_rates(self) -> list[dict[str, Any]]:
        """Returns satiety and SAN decay rates across food ratings 1-10."""
        cursor = self.conn.cursor()
        rows = cursor.execute("SELECT * FROM food_satiety_rates ORDER BY food_rating ASC").fetchall()
        return [dict(r) for r in rows]

    def get_base_camps(self) -> list[dict[str, Any]]:
        """Returns all base camps with structure counts, assigned Pals, and max capacity."""
        cursor = self.conn.cursor()
        camps = cursor.execute("SELECT * FROM base_camps").fetchall()
        results = []
        for c in camps:
            c_dict = dict(c)
            camp_id = c_dict["base_camp_id"]
            
            # Count structure instances
            struct_count = cursor.execute(
                "SELECT SUM(count) as c FROM base_structures_instances WHERE base_camp_id=?", (camp_id,)
            ).fetchone()["c"] or 0
            
            # Count assigned Pals
            assigned_count = cursor.execute(
                "SELECT COUNT(*) as c FROM pal_instances WHERE location_details_base_camp_id=?", (camp_id,)
            ).fetchone()["c"] or 0

            c_dict["structure_count"] = struct_count
            c_dict["assigned_pals_count"] = assigned_count
            c_dict["max_pals"] = 15  # Baseline Palbox base capacity
            results.append(c_dict)
        return results

    def get_base_camp_structures(self, base_camp_id: str) -> list[dict[str, Any]]:
        """Returns structures present in a base camp with their work suitabilities."""
        cursor = self.conn.cursor()
        rows = cursor.execute(
            """
            SELECT bsi.structure_name, bsi.count, bwt.work_type, bwt.is_automated, bwt.work_amount_modifier
            FROM base_structures_instances bsi
            LEFT JOIN building_work_types bwt ON bsi.structure_name = bwt.building_id
            WHERE bsi.base_camp_id = ?
            """,
            (base_camp_id,),
        ).fetchall()
        
        # Group by structure_name
        structures_map: dict[str, dict[str, Any]] = {}
        for r in rows:
            s_name = r["structure_name"]
            count = r["count"]
            if s_name not in structures_map:
                structures_map[s_name] = {
                    "structure_name": s_name,
                    "count": count,
                    "work_types": [],
                }
            if r["work_type"]:
                structures_map[s_name]["work_types"].append({
                    "work_type": r["work_type"],
                    "is_automated": r["is_automated"],
                    "work_amount_modifier": r["work_amount_modifier"],
                })

        # Fallback check using STRUCTURE_ALIAS_MAP for structure names that didn't match building_work_types
        for s_name, s_data in structures_map.items():
            if not s_data["work_types"]:
                alias = STRUCTURE_ALIAS_MAP.get(s_name.lower())
                if alias:
                    alias_rows = cursor.execute(
                        "SELECT work_type, is_automated, work_amount_modifier FROM building_work_types WHERE LOWER(building_id) = LOWER(?)",
                        (alias,),
                    ).fetchall()
                    for ar in alias_rows:
                        s_data["work_types"].append({
                            "work_type": ar["work_type"],
                            "is_automated": ar["is_automated"],
                            "work_amount_modifier": ar["work_amount_modifier"],
                        })

        result_list = list(structures_map.values())

        # If base has automated production structures (farms/pits), ensure Transporting is included in work demand
        has_logistics_demand = any(
            any(wt["work_type"] in ["Planting", "Mining", "Lumbering", "Watering"] for wt in item.get("work_types", []))
            for item in result_list
        )
        if has_logistics_demand:
            has_transport = any(
                any(wt["work_type"] == "Transporting" for wt in item.get("work_types", []))
                for item in result_list
            )
            if not has_transport:
                result_list.append({
                    "structure_name": "TransportingSupport",
                    "count": 1,
                    "work_types": [{"work_type": "Transporting", "is_automated": 1, "work_amount_modifier": 1.0}]
                })

        return result_list

    def get_owned_pals_with_suitabilities(self) -> list[dict[str, Any]]:
        """Returns all owned Pal instances in the Palbox with work suitabilities and passives."""
        cursor = self.conn.cursor()
        instances = cursor.execute(
            """
            SELECT pi.*, p.display_name, p.paldex_number, p.food_requirement, p.nocturnal, p.icon_path
            FROM pal_instances pi
            LEFT JOIN pals p ON LOWER(pi.species) = LOWER(p.internal_name) OR LOWER(pi.species) = LOWER(p.display_name)
            """
        ).fetchall()

        results = []
        for inst in instances:
            d = dict(inst)
            inst_id = d["instance_id"]
            species = d["species"]

            # Get work suitabilities for species
            ws_rows = cursor.execute(
                "SELECT suitability_name, level FROM pal_work_suitabilities WHERE LOWER(pal_internal_name) = LOWER(?)",
                (species,),
            ).fetchall()
            d["suitabilities"] = {r["suitability_name"]: r["level"] for r in ws_rows}

            # Get passives for instance joining passive_skills for display name
            pass_rows = cursor.execute(
                """
                SELECT COALESCE(ps.name, pip.passive_id) as name, pip.passive_id as id
                FROM pal_instance_passives pip
                LEFT JOIN passive_skills ps ON LOWER(pip.passive_id) = LOWER(ps.id)
                WHERE pip.instance_id = ?
                """,
                (inst_id,),
            ).fetchall()
            d["passives"] = [r["name"] for r in pass_rows]
            d["raw_passives"] = [r["id"] for r in pass_rows]

            d["icon_path"] = transform_icon_path(d.get("icon_path"))
            results.append(d)
        return results
