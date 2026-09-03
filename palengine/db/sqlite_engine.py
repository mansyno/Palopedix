"""SQLite database engine module for PalEngine.

Integrates static game metadata and dynamic save game instance data.
Supports both Palworld 1.0+ SQLite master database ('palworld_db') and legacy JSON datasets ('legacy').
"""

import json
import os
import re
import sqlite3
from collections import defaultdict
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
from palengine.parser.extract_quests import extract_active_quests
from palengine.parser.extract_settings import extract_world_settings
from palengine.analytics.breeding_graph import BreedingGraphOptimizer


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


def clean_skill_text(text: Optional[str], pal_name: str = "Pal") -> Optional[str]:
    """Removes Unreal Engine markup tags and resolves canonical element and entity names."""
    if not text:
        return None
    from palengine.analytics.partner_skill_scaling import sanitize_markup_elements
    cleaned = sanitize_markup_elements(text, pal_name)
    # Remove Unreal placeholder variables like {ReferenceMsgId_DamageUp} or [ReferenceMsgId_DamageUp]
    cleaned = re.sub(r"\[ReferenceMsgId_[^\]]+\]", "", cleaned)
    cleaned = re.sub(r"\{ReferenceMsgId_[^}]+\}", "", cleaned)
    cleaned = re.sub(r"\[ReferencePassive[^\]]+\]", "", cleaned)
    cleaned = re.sub(r"\{ReferencePassive[^}]+\}", "", cleaned)
    cleaned = re.sub(r"\[Passive[^\]]+\]", "", cleaned)
    cleaned = re.sub(r"\{Passive[^}]+\}", "", cleaned)
    # Normalize whitespace and punctuation spacing
    cleaned = " ".join(cleaned.split())
    cleaned = re.sub(r"\s+([.,!?:;%])", r"\1", cleaned)
    return cleaned if cleaned else None


def calculate_aptitude(name: str, p_id: str, category: Optional[str]) -> dict[str, Any]:
    """Computes aptitude tier (▲/▼) and badge color for passive skills."""
    n_lower = name.lower()
    pid_lower = p_id.lower()
    cat_lower = str(category or "").lower()

    if "legend" in n_lower or "legend" in pid_lower:
        return {"label": "LEGEND", "color": "legend", "rank": 4}
    if "lucky" in n_lower or "lucky" in pid_lower:
        return {"label": "LUCKY", "color": "gold", "rank": 4}
    if any(k in n_lower or k in pid_lower for k in ["emperor", "siren", "divine", "demon", "eternal", "invader"]):
        return {"label": "▲▲▲", "color": "gold", "rank": 3}
    if "rank3" in cat_lower or "rank3" in pid_lower or "3" in pid_lower:
        return {"label": "▲▲▲", "color": "gold", "rank": 3}
    if "rank2" in cat_lower or "rank2" in pid_lower or "2" in pid_lower:
        return {"label": "▲▲", "color": "white", "rank": 2}
    if "down" in pid_lower or "deffence_down" in pid_lower or "attack_down" in pid_lower or any(k in n_lower for k in ["clumsy", "slacker", "coward", "pacifist", "downtrodden", "brittle", "glutton", "bottomless stomach", "destructive", "destabilized", "sloppy", "shabby", "sickly", "unstable"]):
        return {"label": "▼", "color": "red", "rank": -1}
    return {"label": "▲", "color": "white", "rank": 1}


RESTRICTED_BREEDING_SPECIES = {
    # Strict Legendaries / Raid Bosses / Uniques (cannot be standard formula children)
    "jetragon", "frostallion", "paladius", "necromus", "neptilius", "astralym", "panthalus", "hartalis",
    "bellanoir", "bellanoir libero", "blazamut ryu", "selyne", "bastigor", "shaolong", "silvance", "dandilord",
    "aegidron", "solenne", "renjishi", "xenovader", "xenogard", "xenolord", "chikipi", "chickenpal",
    # Special-Recipe / Self-Only Pals (cannot be generic power children)
    "shadowbeak", "faleris", "grizzbolt", "orserk", "lyleen", "jormuntide ignis", "mimog",
    # Unreleased / Cut Content
    "boltmane", "eleclion", "dragostrophe", "blackfurdragon", "pidf rider", "police_palride",
    # Tower Boss Entities
    "zoe & grizzbolt", "lily & lyleen", "marcus & faleris", "axel & orserk",
    "victor & shadowbeak", "saya & selyne", "auri & shaolong", "bjorn & bastigor", "zenara & astralym",
    # Crossover / Yakushima / Event Entities
    "green slime", "blue slime", "red slime", "purple slime", "illuminant slime", "rainbow slime",
    "enchanted sword", "cave bat", "illuminant bat", "eye of cthulhu", "demon eye", "true eye of cthulhu", "moon lord",
    "tetroise primo", "tetroise",
}


def is_valid_standard_candidate(pal_dict: dict[str, Any], restricted_set: Optional[set[str]] = None) -> bool:
    if pal_dict.get("is_variant", 0) != 0:
        return False
    d_name = str(pal_dict.get("display_name", "")).strip().lower()
    i_name = str(pal_dict.get("internal_name", "")).strip().lower()
    if "&" in d_name or "boss" in i_name or i_name.startswith("yakushima") or i_name.startswith("raid_"):
        return False
    active_restricted = restricted_set if restricted_set is not None else RESTRICTED_BREEDING_SPECIES
    if d_name in active_restricted or i_name in active_restricted:
        return False
    return True


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
    """Enriches passive skill dictionary with clean descriptions, aptitudes, and sources."""
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

    if not mod and desc:
        mod = desc
    if not desc and mod:
        desc = mod

    skill_dict["description"] = desc
    skill_dict["stat_modifier"] = mod
    return skill_dict


PARTNER_SKILL_CATEGORY_DEFS: list[dict[str, Any]] = [
    {
        "category_id": "flying_mount",
        "name": "Flying Mounts",
        "description": "Can be ridden as an airborne flying mount with vertical altitude control.",
        "icon": "🦅",
        "sort_order": 1,
    },
    {
        "category_id": "ground_mount",
        "name": "Ground Mounts",
        "description": "Can be ridden for rapid terrestrial travel and exploration.",
        "icon": "🐎",
        "sort_order": 2,
    },
    {
        "category_id": "swimming_mount",
        "name": "Swimming Mounts",
        "description": "Can be ridden across water surfaces without stamina drain.",
        "icon": "🌊",
        "sort_order": 3,
    },
    {
        "category_id": "glider",
        "name": "Gliders",
        "description": "Replaces or enhances the equipped glider (speed glide, vertical lift, no fall damage).",
        "icon": "🪂",
        "sort_order": 4,
    },
    {
        "category_id": "ranch_producer",
        "name": "Ranch Producers",
        "description": "Produces items, ingredients, or spheres when assigned to a Ranch.",
        "icon": "🚜",
        "sort_order": 5,
    },
    {
        "category_id": "player_element_infusion",
        "name": "Player Element Infusion",
        "description": "Changes the player's weapon/attack element and boosts player attack while active or mounted.",
        "icon": "⚡",
        "sort_order": 6,
    },
    {
        "category_id": "player_combat_buffer",
        "name": "Player Combat Buffers",
        "description": "Boosts player Attack %, Defense %, Dodge I-Frames, or Weak Point damage.",
        "icon": "⚔️",
        "sort_order": 7,
    },
    {
        "category_id": "party_pal_buffer",
        "name": "Pal / Party Combat Buffers",
        "description": "Passively boosts attack, defense, or speed for party Pals or elemental allies.",
        "icon": "🛡️",
        "sort_order": 8,
    },
    {
        "category_id": "heavy_artillery",
        "name": "Heavy Artillery & Direct Weapons",
        "description": "Pal operates as or equips heavy weaponry (Minigun, Missile Launcher, Grenade Launcher, Assault Rifle, Flamethrower).",
        "icon": "💥",
        "sort_order": 9,
    },
    {
        "category_id": "coop_attacker",
        "name": "Autonomous Co-Op Attackers",
        "description": "Pal hovers beside player to fire independent magic bullets/lightning, syncs tandem attacks, or follows up player hits.",
        "icon": "👥",
        "sort_order": 10,
    },
    {
        "category_id": "healer_lifesteal",
        "name": "Healers & Life-Steal",
        "description": "Actively heals player and party HP, grants life-steal on attacks, or revives on incapacitation.",
        "icon": "💖",
        "sort_order": 11,
    },
    {
        "category_id": "carrying_capacity",
        "name": "Carrying Capacity Boosters",
        "description": "Increases maximum player inventory carrying weight or reduces encumbrance.",
        "icon": "🎒",
        "sort_order": 12,
    },
    {
        "category_id": "drop_loot_booster",
        "name": "Drop Rate & Loot Boosters",
        "description": "Increases item drops or Pal Souls dropped when defeating enemies.",
        "icon": "🎁",
        "sort_order": 13,
    },
    {
        "category_id": "resource_gathering",
        "name": "Resource Gathering Boosters",
        "description": "Enhances ore mining, tree logging efficiency, or preserves equipment durability.",
        "icon": "⛏️",
        "sort_order": 14,
    },
    {
        "category_id": "breeding_egg_booster",
        "name": "Breeding & Egg Boosters",
        "description": "Accelerates egg incubation speed at base, breeding farm production, or boosts Alpha egg chance.",
        "icon": "🥚",
        "sort_order": 15,
    },
    {
        "category_id": "fishing_helper",
        "name": "Fishing & Mini-Game Helpers",
        "description": "Enhances fishing minigame catch rate, reduces meter drain, or attracts talented Pals.",
        "icon": "🎣",
        "sort_order": 16,
    },
    {
        "category_id": "exploration_survival",
        "name": "Exploration & Environmental Protection",
        "description": "Scans for nearby dungeons/chests/ores, provides thermal/lava/toxic gas immunity, or grants invisibility.",
        "icon": "🧭",
        "sort_order": 17,
    },
    {
        "category_id": "no_active_skill",
        "name": "No Functional Partner Skill",
        "description": "Pals currently without an active partner skill (WIP abilities).",
        "icon": "❓",
        "sort_order": 18,
    },
]

PASSIVE_SKILL_MODIFIER_DEFS: list[dict[str, Any]] = [
    # ── Work Speed Modifiers ──
    {"passive_id": "WorldTree_CraftSpeed", "name": "Demon's Hand", "work_speed_mod": 0.90, "san_decay_pts": -15.0},
    {"passive_id": "CraftSpeed_up3", "name": "Remarkable Craftsmanship", "work_speed_mod": 0.75},
    {"passive_id": "CraftSpeed_up2", "name": "Artisan", "work_speed_mod": 0.50},
    {"passive_id": "PAL_CorporateSlave", "name": "Work Slave", "work_speed_mod": 0.30},
    {"passive_id": "WorkSpeed_ACC_up4", "name": "Speedy Worker Lv. 4", "work_speed_mod": 0.25},
    {"passive_id": "CraftSpeed_up1", "name": "Serious", "work_speed_mod": 0.20},
    {"passive_id": "Rare", "name": "Lucky", "work_speed_mod": 0.20},
    {"passive_id": "WorkSpeed_ACC_up3", "name": "Speedy Worker Lv. 3", "work_speed_mod": 0.20},
    {"passive_id": "WorkSpeed_ACC_up2", "name": "Speedy Worker Lv. 2", "work_speed_mod": 0.15},
    {"passive_id": "PAL_conceited", "name": "Conceited", "work_speed_mod": 0.10},
    {"passive_id": "WorkSpeed_ACC_up1", "name": "Speedy Worker Lv. 1", "work_speed_mod": 0.10},
    {"passive_id": "CraftSpeed_down1", "name": "Clumsy", "work_speed_mod": -0.10},
    {"passive_id": "PAL_rude", "name": "Hooligan", "work_speed_mod": -0.10},
    {"passive_id": "PAL_SpiritualInst", "name": "Mentally unstable", "work_speed_mod": -0.10},
    {"passive_id": "WorldTree_Sanity", "name": "Hermit Sage", "work_speed_mod": -0.20, "san_decay_pts": 25.0},
    {"passive_id": "CraftSpeed_down2", "name": "Slacker", "work_speed_mod": -0.30},
    {"passive_id": "Noukin", "name": "Musclehead", "work_speed_mod": -0.50},

    # ── Movement Speed Modifiers (Logistics / Transporters & Gatherers) ──
    {"passive_id": "WorldTree_MoveSpeed", "name": "Dimensional Leap", "move_speed_mod": 0.50, "hunger_rate_pts": -15.0},
    {"passive_id": "MoveSpeed_up_3", "name": "Swift", "move_speed_mod": 0.30},
    {"passive_id": "MoveSpeed_up_2", "name": "Runner", "move_speed_mod": 0.20},
    {"passive_id": "Legend", "name": "Legend", "move_speed_mod": 0.20},
    {"passive_id": "MoveSpeed_up_1", "name": "Nimble", "move_speed_mod": 0.10},
    {"passive_id": "GYM_NAME_Meadow", "name": "Rayne Syndicate Boss", "move_speed_mod": 0.10},

    # ── Hunger / Satiety Modifiers (Eating Breaks vs Active Uptime) ──
    {"passive_id": "WorldTree_FullStomach", "name": "World Tree Seedbed", "hunger_rate_pts": 30.0},
    {"passive_id": "PAL_FullStomach_Down_3", "name": "Mastery of Fasting", "hunger_rate_pts": 20.0},
    {"passive_id": "PAL_FullStomach_Down_2", "name": "Diet Lover", "hunger_rate_pts": 15.0},
    {"passive_id": "PAL_FullStomach_Down_1", "name": "Dainty Eater", "hunger_rate_pts": 10.0},
    {"passive_id": "FullStomach_Down_1_BossDefeat", "name": "FullStomach_Down_1_BossDefeat", "hunger_rate_pts": 10.0},
    {"passive_id": "PAL_FullStomach_Up_1", "name": "Glutton", "hunger_rate_pts": -15.0},
    {"passive_id": "PAL_FullStomach_Up_2", "name": "Bottomless Stomach", "hunger_rate_pts": -25.0},

    # ── SAN Degradation vs Preservation (Slacking, Injuries, Refusal) ──
    {"passive_id": "PAL_Sanity_Down_3", "name": "Heart of the Immovable King", "san_decay_pts": 20.0},
    {"passive_id": "PAL_Sanity_Down_2", "name": "Workaholic", "san_decay_pts": 15.0},
    {"passive_id": "PAL_Sanity_Down_1", "name": "Positive Thinker", "san_decay_pts": 10.0},
    {"passive_id": "PAL_Sanity_Up_1", "name": "Unstable", "san_decay_pts": -15.0},
    {"passive_id": "PAL_Sanity_Up_2", "name": "Destructive", "san_decay_pts": -25.0},
]


def classify_pal_partner_categories(
    pal_name: str, partner_skill_name: Optional[str], partner_skill_desc: Optional[str]
) -> list[str]:
    """Deterministically classifies a Pal into one or more Partner Skill categories."""
    ps_name = str(partner_skill_name or "").strip()
    desc = str(partner_skill_desc or "").strip()
    text = f"{ps_name} {desc}".lower()

    if not ps_name or ps_name == "-" or "still being investigated" in desc.lower() or "under investigation" in desc.lower():
        return ["no_active_skill"]

    cats: list[str] = []
    if "flying mount" in text or ("fly" in text and "ridden" in text):
        cats.append("flying_mount")
    elif "travel on water" in text or "water mount" in text:
        cats.append("swimming_mount")
    elif "ridden" in text or "ride" in text or "mounted" in text:
        cats.append("ground_mount")

    if "glider" in text or "gliding" in text or "glide" in text:
        cats.append("glider")

    if any(k in text for k in ["ranch", "when assigned to", "assigned to", "digs up", "drops when assigned", "sometimes drops", "milk maker"]):
        cats.append("ranch_producer")

    if "attack type" in text or "changes the player" in text:
        cats.append("player_element_infusion")

    if any(
        k in text
        for k in [
            "player's attack",
            "player attack",
            "player's defense",
            "player defense",
            "player takes reduced damage",
            "reduced damage",
            "elemental resistance",
            "player and party pals take",
            "barrier",
            "weak point",
            "weak points",
            "dodge roll",
            "dodge step",
            "inflict 50",
            "melee weapon",
            "weapon damage",
            "bow damage",
            "bow charge",
            "enchant",
            "critical strike",
            "damage to enemies afflicted",
            "climbing speed",
            "capture rate",
            "homeward prayer",
        ]
    ):
        cats.append("player_combat_buffer")

    if any(
        k in text
        for k in [
            "increases attack of",
            "increases defense of",
            "increases its attack and defense",
            "increases knocklem",
            "steel resolve increases",
            "enhances",
            "party pal",
            "fighting alongside you",
            "in party, increases",
            "each other pal in your party",
            "work suitability level for all other",
            "depletion rate of",
        ]
    ):
        cats.append("party_pal_buffer")

    if any(
        k in text
        for k in [
            "minigun",
            "missile",
            "rocket",
            "grenade",
            "flamethrower",
            "machine gun",
            "shotgun",
            "weapon-wielding",
            "egg launcher",
            "launcher",
            "assault rifle",
            "gunfire",
            "bomb",
            "thrown at an enemy",
            "katana",
            "player equips",
        ]
    ):
        cats.append("heavy_artillery")

    if any(
        k in text
        for k in [
            "attacks alongside",
            "follows up",
            "in tandem",
            "attacks targeted enemy",
            "appears near the player",
            "attacks hostile enemies",
            "nightmare iris",
            "nightmare stare",
            "sentinel of the great sea",
            "magic bullets",
            "body surf",
            "fire surf",
            "mad eye lunge",
            "phantasmal gaze",
            "summons shadow",
            "bat backup",
            "assist during combat",
        ]
    ):
        cats.append("coop_attacker")

    if any(
        k in text
        for k in [
            "restore",
            "health",
            "heal",
            "life steal",
            "absorbs damage and restores",
            "revives",
        ]
    ):
        cats.append("healer_lifesteal")

    if any(k in text for k in ["carrying capacity", "weight", "luggage"]):
        cats.append("carrying_capacity")

    if any(
        k in text
        for k in [
            "drop 50% more",
            "drops +50%",
            "more items when defeated",
            "more pal souls",
            "drop rate",
        ]
    ):
        cats.append("drop_loot_booster")

    if any(
        k in text
        for k in [
            "incubate",
            "breeding farm",
            "pal egg",
            "alpha pal egg",
            "egg production",
        ]
    ):
        cats.append("breeding_egg_booster")

    if any(k in text for k in ["ore", "mining", "wood", "trees", "logging", "durability", "crops", "harvest", "work speed", "salvaging"]):
        cats.append("resource_gathering")

    if any(k in text for k in ["fishing", "talented pals", "capture gauge"]):
        cats.append("fishing_helper")

    if any(
        k in text
        for k in [
            "detect",
            "radar",
            "invisible",
            "temperature",
            "cold resistance",
            "heat resistance",
            "lava damage",
            "toxic gas",
            "spores",
            "night vision",
            "teleports to the nearest base",
            "open treasure chests",
        ]
    ):
        cats.append("exploration_survival")

    return cats if cats else ["no_active_skill"]


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
        self._cached_active_missions: Optional[list[dict[str, Any]]] = None
        self._cached_base_recommendations: Optional[dict[str, Any]] = None

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
        self.conn = sqlite3.connect(db_file, check_same_thread=False, timeout=30.0)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=30000")
        self._create_tables()
        self._load_static_metadata()
        self.breeding_optimizer = BreedingGraphOptimizer(self)
        
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

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pal_instances_species ON pal_instances(species)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pal_instances_loc ON pal_instances(location)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pal_instance_passives_iid ON pal_instance_passives(instance_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pal_instance_waza_iid ON pal_instance_waza(instance_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pal_instance_status_iid ON pal_instance_status_points(instance_id)")

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
            CREATE TABLE IF NOT EXISTS base_camp_custom_names (
                base_camp_id TEXT PRIMARY KEY,
                custom_name TEXT NOT NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS structure_aliases (
                alias TEXT PRIMARY KEY,
                canonical_name TEXT,
                display_name TEXT,
                work_type TEXT,
                is_automated INTEGER
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

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS player_active_missions (
                quest_id TEXT PRIMARY KEY
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS world_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT
            )
        """
        )

        # ---------- Static Metadata Source Setup ----------
        use_palworld_db = (
            self.source == "palworld_db" and os.path.exists(self.palworld_db_path)
        )

        if use_palworld_db:
            # Attach external master SQLite database if not already attached
            db_path_clean = self.palworld_db_path.replace("\\", "/")
            try:
                cursor.execute(f"ATTACH DATABASE '{db_path_clean}' AS palworld_master")
            except Exception:
                pass

            cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pals'")
            tables_exist = cursor.fetchone() is not None

            if not tables_exist:
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

                # Special Crossover Unique Combos (Eye of Cthulhu)
                eye_combos = [
                    ("Eye of Cthulhu", "Eye of Cthulhu", "Eye of Cthulhu"),
                    ("Blue Slime", "Eye of Cthulhu", "Eye of Cthulhu"),
                    ("Cave Bat", "Eye of Cthulhu", "Eye of Cthulhu"),
                    ("Demon Eye", "Eye of Cthulhu", "Eye of Cthulhu"),
                    ("Enchanted Sword", "Eye of Cthulhu", "Eye of Cthulhu"),
                    ("Green Slime", "Eye of Cthulhu", "Eye of Cthulhu"),
                    ("Illuminant Bat", "Eye of Cthulhu", "Eye of Cthulhu"),
                    ("Illuminant Slime", "Eye of Cthulhu", "Eye of Cthulhu"),
                    ("Purple Slime", "Eye of Cthulhu", "Eye of Cthulhu"),
                    ("Rainbow Slime", "Eye of Cthulhu", "Eye of Cthulhu"),
                    ("Red Slime", "Eye of Cthulhu", "Eye of Cthulhu"),
                ]
                for p1, p2, ch in eye_combos:
                    cursor.execute(
                        "INSERT OR IGNORE INTO breeding_combos (parent1, parent2, child) VALUES (?, ?, ?)",
                        (p1, p2, ch),
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
                INSERT OR IGNORE INTO work_suitabilities (id, name, description)
                SELECT DISTINCT work_type, work_type, '' FROM palworld_master.work_suitability
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
                INSERT OR IGNORE INTO building_work_types (building_id, work_type, is_automated, work_amount_modifier)
                SELECT building_id, work_type, is_automated, work_amount_modifier FROM palworld_master.building_work_types
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
            cursor.execute(
                """
                INSERT OR IGNORE INTO food_satiety_rates (food_rating, satiety_amount, san_decay_multiplier)
                SELECT food_tier, AVG(satiety_drain_per_min), AVG(base_san_drain_per_min) 
                FROM palworld_master.food_satiety_rates 
                GROUP BY food_tier
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sub_missions (
                    id TEXT PRIMARY KEY,
                    category TEXT,
                    title TEXT,
                    npc_name TEXT,
                    objective TEXT,
                    start_dialogue TEXT,
                    in_progress_dialogue TEXT,
                    completed_dialogue TEXT,
                    target_type TEXT,
                    target_id TEXT,
                    target_count INTEGER
                )
            """
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO sub_missions
                SELECT * FROM palworld_master.sub_missions
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sub_mission_rewards (
                    sub_mission_id TEXT,
                    item_id TEXT,
                    item_count INTEGER
                )
            """
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO sub_mission_rewards
                SELECT * FROM palworld_master.sub_mission_rewards
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

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sub_missions (
                    id TEXT PRIMARY KEY,
                    category TEXT,
                    title TEXT,
                    npc_name TEXT,
                    objective TEXT,
                    start_dialogue TEXT,
                    in_progress_dialogue TEXT,
                    completed_dialogue TEXT,
                    target_type TEXT,
                    target_id TEXT,
                    target_count INTEGER
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sub_mission_rewards (
                    id INTEGER PRIMARY KEY,
                    mission_id TEXT,
                    reward_type TEXT,
                    item_id TEXT,
                    item_name TEXT,
                    quantity INTEGER
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

            # Special Crossover Unique Combos (Eye of Cthulhu)
            eye_combos = [
                ("Eye of Cthulhu", "Eye of Cthulhu", "Eye of Cthulhu"),
                ("Blue Slime", "Eye of Cthulhu", "Eye of Cthulhu"),
                ("Cave Bat", "Eye of Cthulhu", "Eye of Cthulhu"),
                ("Demon Eye", "Eye of Cthulhu", "Eye of Cthulhu"),
                ("Enchanted Sword", "Eye of Cthulhu", "Eye of Cthulhu"),
                ("Green Slime", "Eye of Cthulhu", "Eye of Cthulhu"),
                ("Illuminant Bat", "Eye of Cthulhu", "Eye of Cthulhu"),
                ("Illuminant Slime", "Eye of Cthulhu", "Eye of Cthulhu"),
                ("Purple Slime", "Eye of Cthulhu", "Eye of Cthulhu"),
                ("Rainbow Slime", "Eye of Cthulhu", "Eye of Cthulhu"),
                ("Red Slime", "Eye of Cthulhu", "Eye of Cthulhu"),
            ]
            for p1, p2, ch in eye_combos:
                cursor.execute(
                    "INSERT OR IGNORE INTO breeding_combos (parent1, parent2, child) VALUES (?, ?, ?)",
                    (p1, p2, ch),
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

        # ---------- Partner Skill Categories Table Setup & Population ----------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS partner_skill_categories (
                category_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                icon TEXT,
                sort_order INTEGER
            )
            """
        )
        cat_count_row = cursor.execute("SELECT COUNT(*) FROM partner_skill_categories").fetchone()
        if not cat_count_row or cat_count_row[0] == 0:
            for cat in PARTNER_SKILL_CATEGORY_DEFS:
                cursor.execute(
                    "INSERT OR REPLACE INTO partner_skill_categories (category_id, name, description, icon, sort_order) VALUES (?, ?, ?, ?, ?)",
                    (cat["category_id"], cat["name"], cat["description"], cat["icon"], cat["sort_order"]),
                )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pal_partner_skill_categories (
                pal_internal_name TEXT,
                category_id TEXT,
                PRIMARY KEY (pal_internal_name, category_id)
            )
            """
        )

        # Populate categories for all pals if not populated
        pal_cat_count = cursor.execute("SELECT COUNT(*) FROM pal_partner_skill_categories").fetchone()
        if not pal_cat_count or pal_cat_count[0] == 0:
            use_palworld_db = (
                self.source == "palworld_db" and os.path.exists(self.palworld_db_path)
            )
            try:
                pal_rows = cursor.execute(
                    """
                    SELECT p.internal_name, p.display_name, p.id, p.code,
                           ps.name as partner_name, ps.description as partner_desc
                    FROM pals p
                    LEFT JOIN partner_skills ps ON LOWER(p.internal_name) = LOWER(ps.pal_internal_name)
                                                OR LOWER(p.id) = LOWER(ps.pal_internal_name)
                                                OR LOWER(p.code) = LOWER(ps.pal_internal_name)
                    """
                ).fetchall()

                for pr in pal_rows:
                    pal_key = pr["internal_name"] or pr["id"] or pr["code"]
                    p_display = pr["display_name"]
                    ps_name = pr["partner_name"]
                    ps_desc = pr["partner_desc"]

                    # If partner_skills row didn't match via pal_internal_name, try checking palworld_master
                    if use_palworld_db and (not ps_name or not ps_desc):
                        try:
                            s_row = cursor.execute(
                                """
                                SELECT s.name, s.description
                                FROM palworld_master.pal_skills ps
                                JOIN palworld_master.skills s ON ps.skill_id = s.id
                                WHERE (LOWER(ps.pal_id) = LOWER(?) OR ps.pal_id = ?)
                                  AND (s.type = 'Partner' OR s.category = 'Partner' OR s.category LIKE 'Partner%')
                                LIMIT 1
                                """,
                                (pal_key, pal_key),
                            ).fetchone()
                            if s_row:
                                ps_name = s_row["name"]
                                ps_desc = clean_skill_text(s_row["description"])
                        except Exception:
                            pass

                    cats = classify_pal_partner_categories(p_display, ps_name, ps_desc)
                    for c in cats:
                        cursor.execute(
                            "INSERT OR IGNORE INTO pal_partner_skill_categories (pal_internal_name, category_id) VALUES (?, ?)",
                            (pal_key, c),
                        )
            except Exception as e:
                print(f"Warning populating partner skill categories: {e}")

        # ---------- Passive Skill Modifiers Table Setup & Population ----------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS passive_skill_modifiers (
                passive_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                work_speed_mod REAL DEFAULT 0.0,
                move_speed_mod REAL DEFAULT 0.0,
                san_decay_pts REAL DEFAULT 0.0,
                hunger_rate_pts REAL DEFAULT 0.0
            )
            """
        )
        mod_count = cursor.execute("SELECT COUNT(*) FROM passive_skill_modifiers").fetchone()
        if not mod_count or mod_count[0] == 0:
            for pmod in PASSIVE_SKILL_MODIFIER_DEFS:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO passive_skill_modifiers 
                    (passive_id, name, work_speed_mod, move_speed_mod, san_decay_pts, hunger_rate_pts)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pmod["passive_id"],
                        pmod["name"],
                        pmod.get("work_speed_mod", 0.0),
                        pmod.get("move_speed_mod", 0.0),
                        pmod.get("san_decay_pts", 0.0),
                        pmod.get("hunger_rate_pts", 0.0),
                    ),
                )

        # Seed structure aliases and friendly display names into SQLite structure_aliases table
        sa_count = cursor.execute("SELECT COUNT(*) FROM structure_aliases").fetchone()
        if not sa_count or sa_count[0] == 0:
            aliases_path = os.path.join(self.data_dir, "structure_aliases.json")
            if os.path.exists(aliases_path):
                try:
                    with open(aliases_path, "r", encoding="utf-8") as f:
                        aliases_data = json.load(f)
                    for sa in aliases_data:
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO structure_aliases (alias, canonical_name, display_name, work_type, is_automated)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (
                                sa.get("alias"),
                                sa.get("canonical_name"),
                                sa.get("display_name"),
                                sa.get("work_type"),
                                sa.get("is_automated", 0),
                            ),
                        )
                except Exception as e:
                    print(f"Warning populating structure aliases: {e}")

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
        cursor.execute("DELETE FROM player_active_missions")
        cursor.execute("DELETE FROM world_settings")
        self._cached_base_recommendations = None
        self._cached_active_missions = None
        self.conn.commit()

    def load_save_data(self, sav_path: str) -> None:
        """Parses Level.sav and loads instances into the SQLite DB."""
        self.clear_instance_data()
        self.current_save_path = sav_path

        pals = extract_pals(sav_path)
        bases = extract_bases(sav_path)
        items_data = extract_items(sav_path)
        players = extract_players(sav_path)
        active_quests = extract_active_quests(sav_path)
        world_settings = extract_world_settings(sav_path)

        cursor = self.conn.cursor()

        for k, v in world_settings.items():
            cursor.execute(
                "INSERT OR REPLACE INTO world_settings (setting_key, setting_value) VALUES (?, ?)",
                (str(k), str(v))
            )

        for q in active_quests:
            if q.get("quest_id"):
                cursor.execute(
                    "INSERT OR REPLACE INTO player_active_missions (quest_id) VALUES (?)",
                    (q["quest_id"],)
                )
        
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

    def get_restricted_breeding_species(self) -> set[str]:
        """Returns a lowercased set of all Pal internal and display names that cannot be standard average-formula offspring."""
        if hasattr(self, "_restricted_breeding_set") and self._restricted_breeding_set:
            return self._restricted_breeding_set

        restricted = set(RESTRICTED_BREEDING_SPECIES)
        try:
            rows = self.conn.execute(
                "SELECT DISTINCT LOWER(child) FROM breeding_combos WHERE LOWER(parent1) = LOWER(parent2) AND LOWER(parent2) = LOWER(child)"
            ).fetchall()
            for r in rows:
                if r[0]:
                    restricted.add(r[0].strip().lower())

            p_rows = self.conn.execute("SELECT LOWER(display_name), LOWER(internal_name) FROM pals").fetchall()
            for dn, iname in p_rows:
                dn_l = (dn or "").strip().lower()
                in_l = (iname or "").strip().lower()
                if dn_l in restricted or in_l in restricted:
                    restricted.add(dn_l)
                    restricted.add(in_l)
        except Exception:
            pass

        self._restricted_breeding_set = restricted
        return restricted

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

        restricted_set = self.get_restricted_breeding_species()
        all_pals_rows = self.conn.execute("SELECT * FROM pals WHERE is_variant = 0 ORDER BY index_order ASC").fetchall()
        candidate_pals = [dict(r) for r in all_pals_rows if is_valid_standard_candidate(dict(r), restricted_set)]
        if candidate_pals:
            best_pal = min(candidate_pals, key=lambda p: abs(p["breeding_power"] - target_power))
            res = dict(best_pal)
            res["icon_path"] = transform_icon_path(res.get("icon_path"))
            return res
        return None

    def get_offspring_for_parent(self, parent: str, pool: Optional[list[str]] = None) -> list[dict[str, Any]]:
        """Finds all unique offspring possible from the given parent with partner parents list and pool filtering."""
        p_row = self.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) = ? OR LOWER(internal_name) = ?",
            (parent.lower(), parent.lower()),
        ).fetchone() or self.conn.execute(
            "SELECT display_name, internal_name, breeding_power FROM pals WHERE LOWER(display_name) LIKE ? OR LOWER(internal_name) LIKE ?",
            (f"%{parent.lower()}%", f"%{parent.lower()}%"),
        ).fetchone()

        if not p_row:
            return []

        all_pals = self.conn.execute("SELECT display_name, internal_name, breeding_power, index_order FROM pals").fetchall()

        pool_set = {p.strip().lower() for p in pool} if pool else None
        if pool_set:
            candidate_others = [dict(r) for r in all_pals if r["display_name"].lower() in pool_set or r["internal_name"].lower() in pool_set]
        else:
            candidate_others = [dict(r) for r in all_pals]

        offspring_map: dict[str, dict[str, Any]] = {}

        for other in candidate_others:
            res = self.get_breeding_result(p_row["display_name"], other["display_name"])
            if res:
                c_name = res["display_name"]
                if c_name not in offspring_map:
                    entry = dict(res)
                    entry["other_parents"] = [other["display_name"]]
                    offspring_map[c_name] = entry
                else:
                    if other["display_name"] not in offspring_map[c_name]["other_parents"]:
                        offspring_map[c_name]["other_parents"].append(other["display_name"])

        for entry in offspring_map.values():
            entry["other_parents"].sort()

        return sorted(list(offspring_map.values()), key=lambda x: (x.get("index_order", 9999), x.get("display_name", "")))

    def find_parents_for_child(self, child: str, pool: Optional[list[str]] = None) -> list[tuple[str, str]]:
        """Returns all breeding combinations (Parent 1, Parent 2) that yield target child, optionally filtered by available pool."""
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
            "SELECT display_name, internal_name, breeding_power, is_variant, index_order FROM pals"
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

        restricted_set = self.get_restricted_breeding_species()
        candidate_pals = [p for p in all_pals if is_valid_standard_candidate(p, restricted_set)]
        candidate_pals.sort(key=lambda x: x["index_order"])

        def calc_standard_child(power1: int, power2: int) -> str:
            target_power = (power1 + power2 + 1) // 2
            best_pal = min(
                candidate_pals,
                key=lambda p: abs(p["breeding_power"] - target_power)
            )
            return best_pal["display_name"]

        pool_set = {p.strip().lower() for p in pool} if pool else None

        results = set()

        # Same-species breeding gives same species (only if child is in pool when pool filtering active)
        if not pool_set or child_name.lower() in pool_set:
            results.add((child_name, child_name))

        for i in range(len(all_pals)):
            for j in range(i, len(all_pals)):
                p1_name = all_pals[i]["display_name"]
                p2_name = all_pals[j]["display_name"]
                p1_l, p2_l = p1_name.lower(), p2_name.lower()

                if pool_set and (p1_l not in pool_set or p2_l not in pool_set):
                    continue

                if p1_l == p2_l:
                    result_child = p1_name
                elif (p1_l, p2_l) in special_combos:
                    result_child = special_combos[(p1_l, p2_l)]
                elif p1_name.lower() not in restricted_set and p2_name.lower() not in restricted_set:
                    pow1 = all_pals[i]["breeding_power"]
                    pow2 = all_pals[j]["breeding_power"]
                    result_child = calc_standard_child(pow1, pow2)
                else:
                    continue

                if result_child.lower() == target_child_lower:
                    p1_n, p2_n = p1_name, p2_name
                    if p1_n.lower() > p2_n.lower():
                        p1_n, p2_n = p2_n, p1_n
                    results.add((p1_n, p2_n))

        return sorted(list(results), key=lambda x: (x[0].lower(), x[1].lower()))

    def get_uncaught_breeding_opportunities(
        self,
        owned_input: Optional[Any] = None,
        parent_pool: Optional[Any] = None
    ) -> list[dict[str, Any]]:
        """Finds all Pal species NOT yet caught in the save file that can be bred using available Pals."""
        if owned_input is not None:
            if isinstance(owned_input, str):
                owned_species = [s.strip() for s in owned_input.split(",") if s.strip()]
            else:
                owned_species = list(owned_input)
        else:
            owned_inv = self.get_owned_pal_inventory()
            owned_species = list(owned_inv.keys()) if owned_inv else []

        owned_set = {s.strip().lower() for s in owned_species}

        pals_rows = self.conn.execute(
            "SELECT display_name, paldex_number, icon_path, element_1, element_2, rarity, breeding_power, is_variant, index_order FROM pals ORDER BY paldex_number ASC, index_order ASC"
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

        restricted_set = self.get_restricted_breeding_species()
        candidate_pals = [p for p in all_pals if is_valid_standard_candidate(p, restricted_set)]
        candidate_pals.sort(key=lambda x: x["index_order"])

        # Pre-compute power to child table for O(1) lookup
        max_pow = max(p["breeding_power"] for p in all_pals) * 2 + 100
        power_to_child = [None] * max_pow
        for p_val in range(max_pow):
            best_pal = min(candidate_pals, key=lambda cp: abs(cp["breeding_power"] - p_val))
            power_to_child[p_val] = best_pal["display_name"]

        # Determine which pool of parents can be used
        is_all_game = False
        if parent_pool is not None:
            if isinstance(parent_pool, str):
                if parent_pool.lower() in ("all", "global", "*"):
                    is_all_game = True
                    pool_pals = all_pals
                elif parent_pool.lower() in ("auto", "caught"):
                    pool_pals = [p for p in all_pals if p["display_name"].lower() in owned_set]
                else:
                    custom_set = {s.strip().lower() for s in parent_pool.split(",") if s.strip()}
                    pool_pals = [p for p in all_pals if p["display_name"].lower() in custom_set]
            elif isinstance(parent_pool, (list, set)):
                custom_set = {s.strip().lower() for s in parent_pool if s.strip()}
                pool_pals = [p for p in all_pals if p["display_name"].lower() in custom_set]
            else:
                pool_pals = [p for p in all_pals if p["display_name"].lower() in owned_set]
        else:
            pool_pals = [p for p in all_pals if p["display_name"].lower() in owned_set]

        # Fast single pass over pool pairs to group uncaught offspring
        uncaught_pairs_map: dict[str, list[tuple[str, str]]] = {}
        uncaught_set = {
            p["display_name"].lower() for p in all_pals
            if p["display_name"].lower() not in owned_set
            and "&" not in p["display_name"]
            and p["display_name"].lower() not in {"boltmane", "dragostrophe", "pidf rider"}
            and not str(p.get("internal_name") or "").startswith("POLICE_")
            and "Boss" not in str(p.get("internal_name") or "")
        }

        for i in range(len(pool_pals)):
            p1 = pool_pals[i]
            p1_name = p1["display_name"]
            p1_l = p1_name.lower()
            for j in range(i, len(pool_pals)):
                p2 = pool_pals[j]
                p2_name = p2["display_name"]
                p2_l = p2_name.lower()

                if p1_l == p2_l:
                    result_child = p1_name
                elif (p1_l, p2_l) in special_combos:
                    result_child = special_combos[(p1_l, p2_l)]
                elif p1_l not in restricted_set and p2_l not in restricted_set:
                    tp = (p1["breeding_power"] + p2["breeding_power"] + 1) // 2
                    result_child = power_to_child[tp] if tp < max_pow else candidate_pals[0]["display_name"]
                else:
                    continue

                ch_l = result_child.lower()
                if ch_l in uncaught_set:
                    # Disallow self-breeding (Child + Child) as an acquisition path for an uncaught species
                    if p1_l == ch_l and p2_l == ch_l:
                        continue
                    if ch_l not in uncaught_pairs_map:
                        uncaught_pairs_map[ch_l] = []
                    p1_n, p2_n = p1_name, p2_name
                    if p1_n.lower() > p2_n.lower():
                        p1_n, p2_n = p2_n, p1_n
                    uncaught_pairs_map[ch_l].append((p1_n, p2_n))

        results = []
        for r in all_pals:
            d_name = r["display_name"]
            d_lower = d_name.lower()
            if (
                d_lower in owned_set
                or "&" in d_name
                or d_lower in {"boltmane", "dragostrophe", "pidf rider"}
                or str(r.get("internal_name") or "").startswith("POLICE_")
                or "Boss" in str(r.get("internal_name") or "")
            ):
                continue

            pairs = uncaught_pairs_map.get(d_lower, [])
            if pairs:
                results.append({
                    "species": d_name,
                    "paldex_number": r["paldex_number"],
                    "icon_path": transform_icon_path(r["icon_path"]),
                    "element_1": r["element_1"],
                    "element_2": r["element_2"],
                    "rarity": r["rarity"],
                    "possible_pairs_count": len(pairs),
                    "pairs": [{"parent1": p1, "parent2": p2} for p1, p2 in pairs]
                })

        return results

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

        restricted_set = self.get_restricted_breeding_species()
        candidate_pals = [p for p in all_pals if is_valid_standard_candidate(p, restricted_set)]
        candidate_pals.sort(key=lambda x: x["index_order"])

        def calc_child_fast(p1_l: str, p2_l: str) -> str:
            if p1_l == p2_l:
                return cased_names.get(p1_l, p1_l)
            if (p1_l, p2_l) in special_combos:
                return special_combos[(p1_l, p2_l)]
            if p1_l not in restricted_set and p2_l not in restricted_set and p1_l in power_map and p2_l in power_map:
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

        is_all_mode = False
        if isinstance(owned_input, str) and owned_input.strip().lower() in ("all", "global", "*"):
            is_all_mode = True
        elif isinstance(owned_input, list) and any(str(i).strip().lower() in ("all", "global", "*") for i in owned_input):
            is_all_mode = True

        if is_all_mode:
            all_pairs = self.find_parents_for_child(target)
            if not all_pairs:
                return []
            
            diff_pairs = [p for p in all_pairs if p[0].lower() != target.lower() or p[1].lower() != target.lower()]
            same_pairs = [p for p in all_pairs if p[0].lower() == target.lower() and p[1].lower() == target.lower()]
            selected_pairs = diff_pairs[:8] if diff_pairs else same_pairs[:1]
            
            paths = []
            for idx, (p1, p2) in enumerate(selected_pairs):
                is_same = (p1.lower() == target.lower() and p2.lower() == target.lower())
                hatch_info = get_hatch_odds(target, "Any")
                step_obj = {
                    "step": 1,
                    "parent1": p1,
                    "parent1_gender": "Male",
                    "parent2": p2,
                    "parent2_gender": "Female",
                    "child": cased_names.get(target, target),
                    "gender_note": hatch_info.get("gender_note", ""),
                    "hatch_chance_pct": hatch_info.get("hatch_chance_pct", "100%"),
                    "avg_eggs": hatch_info.get("avg_eggs", "~1 egg"),
                }
                title = f"Same-Species: {p1} + {p2}" if is_same else f"Direct Pair: {p1} + {p2}"
                paths.append({
                    "path_id": idx + 1,
                    "title": title,
                    "difficulty": "1 Generation (Direct Combination)",
                    "steps": [step_obj],
                    "total_quality_score": 0,
                })
            return paths

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
                            if child not in starting_owned or child == target:
                                new_breeds.append((child, parent1, g1_req, parent2, g2_req))

            for child, p1, g1_req, p2, g2_req in new_breeds:
                # Ignore self-breeding loops for intermediate steps, but allow for target if compatible
                if p1 == p2 and child == p1 and child != target:
                    continue

                if child not in recipes_for_child:
                    recipes_for_child[child] = []
                    if child != target:
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
                    s_step["parent1_level"] = b1.get("level")
                    s_step["parent1_rank"] = b1.get("rank", 0)
                    s_step["parent1_nickname"] = b1.get("nickname")
                    s_step["parent1_ivs"] = {
                        "hp": b1.get("iv_hp") if b1.get("iv_hp") is not None else b1.get("ivs", {}).get("hp"),
                        "melee": b1.get("iv_melee") if b1.get("iv_melee") is not None else b1.get("ivs", {}).get("melee"),
                        "shot": b1.get("iv_shot") if b1.get("iv_shot") is not None else b1.get("ivs", {}).get("shot"),
                        "defense": b1.get("iv_defense") if b1.get("iv_defense") is not None else b1.get("ivs", {}).get("defense"),
                    }
                    s_step["parent1_score"] = b1.get("skill_score", 0)
                    s_step["parent1_passives"] = [
                        p_item.get("name") if isinstance(p_item, dict) else str(p_item)
                        for p_item in b1.get("passives", [])
                    ]
                    s_step["parent1_matched_passives"] = b1.get("matched_passives", [])
                    s_step["parent1_location"] = b1.get("location")
                    s_step["parent1_location_details"] = b1.get("location_details")
                    s_step["parent1_icon_path"] = b1.get("icon_path")

                best_p2_list = self.get_best_parent_instances(p2_sp, p2_g, target_skills_list)
                if best_p2_list:
                    b2 = best_p2_list[0]
                    s_step["parent2_instance_id"] = b2.get("instance_id")
                    s_step["parent2_level"] = b2.get("level")
                    s_step["parent2_rank"] = b2.get("rank", 0)
                    s_step["parent2_nickname"] = b2.get("nickname")
                    s_step["parent2_ivs"] = {
                        "hp": b2.get("iv_hp") if b2.get("iv_hp") is not None else b2.get("ivs", {}).get("hp"),
                        "melee": b2.get("iv_melee") if b2.get("iv_melee") is not None else b2.get("ivs", {}).get("melee"),
                        "shot": b2.get("iv_shot") if b2.get("iv_shot") is not None else b2.get("ivs", {}).get("shot"),
                        "defense": b2.get("iv_defense") if b2.get("iv_defense") is not None else b2.get("ivs", {}).get("defense"),
                    }
                    s_step["parent2_score"] = b2.get("skill_score", 0)
                    s_step["parent2_passives"] = [
                        p_item.get("name") if isinstance(p_item, dict) else str(p_item)
                        for p_item in b2.get("passives", [])
                    ]
                    s_step["parent2_matched_passives"] = b2.get("matched_passives", [])
                    s_step["parent2_location"] = b2.get("location")
                    s_step["parent2_location_details"] = b2.get("location_details")
                    s_step["parent2_icon_path"] = b2.get("icon_path")

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

        if "partner_category" in filters and filters["partner_category"]:
            raw_cat = str(filters["partner_category"]).strip().lower()
            query += """ AND (
                internal_name IN (
                    SELECT pal_internal_name FROM pal_partner_skill_categories
                    WHERE LOWER(category_id) = LOWER(?) OR LOWER(category_id) = LOWER(REPLACE(?, ' ', '_'))
                       OR category_id IN (SELECT category_id FROM partner_skill_categories WHERE LOWER(name) = LOWER(?))
                )
                OR id IN (
                    SELECT pal_internal_name FROM pal_partner_skill_categories
                    WHERE LOWER(category_id) = LOWER(?) OR LOWER(category_id) = LOWER(REPLACE(?, ' ', '_'))
                       OR category_id IN (SELECT category_id FROM partner_skill_categories WHERE LOWER(name) = LOWER(?))
                )
            )"""
            params.extend([raw_cat, raw_cat, raw_cat, raw_cat, raw_cat, raw_cat])

        query += " ORDER BY paldex_number ASC"

        rows = self.conn.execute(query, params).fetchall()
        results = []

        use_palworld_db = (
            self.source == "palworld_db" and os.path.exists(self.palworld_db_path)
        )

        pal_skills_map = defaultdict(list)
        pal_ws_map = defaultdict(list)
        if use_palworld_db:
            try:
                s_all = self.conn.execute("""
                    SELECT ps.pal_id, s.id, s.name, s.element, s.type, s.category, s.power, s.cooldown,
                           s.min_range, s.max_range, s.stat_modifier, s.unlock_item,
                           s.description, s.icon_path, ps.level_learned, ps.is_guaranteed
                    FROM palworld_master.pal_skills ps
                    JOIN palworld_master.skills s ON ps.skill_id = s.id
                    ORDER BY ps.level_learned ASC, s.name ASC
                """).fetchall()
                for sr in s_all:
                    s_dict = dict(sr)
                    pal_skills_map[str(s_dict.get("pal_id") or "").lower()].append(s_dict)
            except Exception:
                pass

            try:
                ws_all = self.conn.execute("SELECT pal_id, work_type, level FROM palworld_master.work_suitability ORDER BY level DESC").fetchall()
                for wsr in ws_all:
                    pal_ws_map[str(wsr.get("pal_id") or "").lower()].append(dict(wsr))
            except Exception:
                pass

        for r in rows:
            pal_dict = dict(r)
            pal_dict["icon_path"] = transform_icon_path(pal_dict.get("icon_path"))
            pal_dict["base_speed"] = pal_dict.get("run_speed") or pal_dict.get("speed") or 0
            pal_dict["run_speed"] = pal_dict.get("run_speed") or pal_dict.get("speed") or 0

            if use_palworld_db:
                pal_id = pal_dict.get("internal_name") or pal_dict.get("id")
                pal_key = str(pal_dict.get("internal_name") or pal_dict.get("id") or "").lower().strip()
                # Attach skills from preloaded map
                try:
                    s_rows = pal_skills_map.get(pal_key, []) or pal_skills_map.get(str(pal_id).lower(), [])
                    pal_skills_list = []
                    for s_dict in s_rows:
                        s_name = s_dict.get("name")
                        s_type = s_dict.get("type")
                        s_cat = s_dict.get("category")
                        s_desc = clean_skill_text(s_dict.get("description"), pal_dict.get("display_name") or "Pal")
                        s_item = s_dict.get("unlock_item")

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
                    if partner_skills:
                        from palengine.analytics.partner_skill_scaling import get_scaled_partner_skill
                        ps_raw = partner_skills[0]
                        scaled_ps = get_scaled_partner_skill(
                            species_id_or_name=pal_dict.get("internal_name") or pal_dict.get("id") or pal_dict.get("display_name"),
                            stars=0,
                            base_description=ps_raw.get("description"),
                            skill_name=ps_raw.get("name"),
                            unlock_item=ps_raw.get("unlock_item"),
                        )
                        pal_dict["partner_skill"] = {
                            **ps_raw,
                            **scaled_ps,
                        }
                    else:
                        pal_dict["partner_skill"] = None
                except Exception as e:
                    pal_dict["skills"] = []
                    pal_dict["partner_skill"] = None

                # Attach work suitabilities from preloaded map or fallback
                try:
                    ws_rows = pal_ws_map.get(pal_key, []) or pal_ws_map.get(str(pal_id).lower(), [])
                    if not ws_rows:
                        ws_rows = self.conn.execute(
                            "SELECT suitability_name as work_type, level FROM pal_work_suitabilities WHERE pal_internal_name = ? ORDER BY level DESC",
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

            # Attach Partner Skill Categories
            try:
                pal_key = pal_dict.get("internal_name") or pal_dict.get("id") or ""
                cat_rows = self.conn.execute(
                    """
                    SELECT DISTINCT c.category_id as id, c.name, c.icon, c.description
                    FROM pal_partner_skill_categories pc
                    JOIN partner_skill_categories c ON pc.category_id = c.category_id
                    WHERE LOWER(pc.pal_internal_name) = LOWER(?)
                    ORDER BY c.sort_order ASC
                    """,
                    (pal_key,),
                ).fetchall()
                pal_dict["partner_skill_categories"] = [dict(cr) for cr in cat_rows]
            except Exception:
                pal_dict["partner_skill_categories"] = []

            results.append(pal_dict)

        return results

    def get_partner_skill_categories(self) -> list[dict[str, Any]]:
        """Returns all partner skill categories with icons, descriptions, and current pal counts."""
        try:
            rows = self.conn.execute(
                """
                SELECT c.category_id, c.name, c.description, c.icon, c.sort_order,
                       COUNT(DISTINCT pc.pal_internal_name) as pal_count
                FROM partner_skill_categories c
                LEFT JOIN pal_partner_skill_categories pc ON c.category_id = pc.category_id
                GROUP BY c.category_id
                ORDER BY c.sort_order ASC
                """
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"Error querying partner skill categories: {e}")
            return []

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
        # 1. Preload master pals dictionary in memory for O(1) attribute lookup
        pal_rows = self.conn.execute("SELECT * FROM pals").fetchall()
        pals_map = {}
        for p in pal_rows:
            pd = dict(p)
            for k in ("internal_name", "display_name", "id", "code"):
                val = pd.get(k)
                if val:
                    pals_map[str(val).lower()] = pd

        query = "SELECT * FROM pal_instances WHERE 1=1"
        params: list[Any] = []

        if "location" in filters and filters["location"]:
            query += " AND location = ?"
            params.append(filters["location"])

        if "gender" in filters and filters["gender"]:
            query += " AND gender = ?"
            params.append(filters["gender"])

        if "min_level" in filters and filters["min_level"]:
            query += " AND level >= ?"
            params.append(filters["min_level"])

        if "min_rank" in filters and filters["min_rank"]:
            query += " AND rank >= ?"
            params.append(filters["min_rank"])

        if "min_iv_hp" in filters and filters["min_iv_hp"]:
            query += " AND iv_hp >= ?"
            params.append(filters["min_iv_hp"])

        if "min_iv_melee" in filters and filters["min_iv_melee"]:
            query += " AND iv_melee >= ?"
            params.append(filters["min_iv_melee"])

        if "min_iv_shot" in filters and filters["min_iv_shot"]:
            query += " AND iv_shot >= ?"
            params.append(filters["min_iv_shot"])

        if "min_iv_defense" in filters and filters["min_iv_defense"]:
            query += " AND iv_defense >= ?"
            params.append(filters["min_iv_defense"])

        if "instance_id" in filters and filters["instance_id"]:
            query += " AND instance_id = ?"
            params.append(filters["instance_id"])

        if "passive_id" in filters and filters["passive_id"]:
            query += """ AND instance_id IN (
                SELECT instance_id FROM pal_instance_passives
                WHERE LOWER(passive_id) = ?
            )"""
            params.append(filters["passive_id"].lower())

        query += " ORDER BY level DESC, species ASC"

        rows = self.conn.execute(query, params).fetchall()
        if not rows:
            return []

        # Filter by species in Python if requested
        if "species" in filters and filters["species"]:
            s_target = str(filters["species"]).strip().lower()
            filtered_rows = []
            for r in rows:
                sp = (r["species"] or "").lower()
                clean_sp = sp[5:] if sp.startswith("boss_") else sp
                p_meta = pals_map.get(clean_sp) or pals_map.get(sp) or {}
                d_name = (p_meta.get("display_name") or sp).lower()
                if s_target in d_name or s_target in sp:
                    filtered_rows.append(r)
            rows = filtered_rows
            if not rows:
                return []

        # Filter by partner_category in Python if requested
        if "partner_category" in filters or "category" in filters:
            cat_val = (filters.get("partner_category") or filters.get("category") or "").strip().lower()
            matching_pal_rows = self.conn.execute(
                """
                SELECT LOWER(pal_internal_name) as p_name
                FROM pal_partner_skill_categories pc
                JOIN partner_skill_categories c ON pc.category_id = c.category_id
                WHERE LOWER(c.category_id) = ? OR LOWER(c.name) = ?
                """,
                (cat_val, cat_val),
            ).fetchall()
            matching_pal_names = {r["p_name"] for r in matching_pal_rows if r["p_name"]}
            filtered_rows = []
            for r in rows:
                sp = (r["species"] or "").lower()
                clean_sp = sp[5:] if sp.startswith("boss_") else sp
                p_meta = pals_map.get(clean_sp) or pals_map.get(sp) or {}
                p_keys = {
                    sp, clean_sp,
                    (p_meta.get("internal_name") or "").lower(),
                    (p_meta.get("id") or "").lower(),
                    (p_meta.get("code") or "").lower(),
                    (p_meta.get("display_name") or "").lower(),
                }
                if p_keys & matching_pal_names:
                    filtered_rows.append(r)
            rows = filtered_rows
            if not rows:
                return []

        use_palworld_db = (
            self.source == "palworld_db" and os.path.exists(self.palworld_db_path)
        )

        inst_ids = [r["instance_id"] for r in rows if r["instance_id"]]

        # 1. Batch load Partner Skill Categories mapping
        pal_cats_map = defaultdict(list)
        try:
            pal_cats_rows = self.conn.execute(
                """
                SELECT pc.pal_internal_name, c.category_id as id, c.name, c.icon, c.description
                FROM pal_partner_skill_categories pc
                JOIN partner_skill_categories c ON pc.category_id = c.category_id
                ORDER BY c.sort_order ASC
                """
            ).fetchall()
            for cr in pal_cats_rows:
                pal_cats_map[cr["pal_internal_name"].lower()].append({
                    "id": cr["id"],
                    "name": cr["name"],
                    "icon": cr["icon"],
                    "description": cr["description"]
                })
        except Exception:
            pass

        # 1b. Batch load Work Suitabilities mapping
        pal_ws_map = defaultdict(dict)
        try:
            ws_rows = self.conn.execute("SELECT pal_internal_name, suitability_name, level FROM pal_work_suitabilities").fetchall()
            for wsr in ws_rows:
                pal_ws_map[wsr["pal_internal_name"].lower()][wsr["suitability_name"]] = wsr["level"]
        except Exception:
            pass

        # Preload master skills dictionary once in-memory for instant O(1) enrichment
        skills_map = {}
        if use_palworld_db:
            try:
                s_rows = self.conn.execute("SELECT * FROM palworld_master.skills").fetchall()
                for sr in s_rows:
                    sd = dict(sr)
                    s_id = str(sd.get("id") or "").lower()
                    s_name = str(sd.get("name") or "").lower()
                    skills_map[s_id] = sd
                    skills_map[s_name] = sd
                    skills_map[s_id.replace("epalwazaid::", "")] = sd
            except Exception:
                pass

        # 2. Batch load Passives
        passives_map = defaultdict(list)
        if inst_ids:
            try:
                id_placeholders = ",".join("?" for _ in inst_ids)
                p_rows = self.conn.execute(
                    f"SELECT instance_id, passive_id FROM pal_instance_passives WHERE instance_id IN ({id_placeholders})",
                    inst_ids,
                ).fetchall()

                for pr in p_rows:
                    iid = pr["instance_id"]
                    pid = pr["passive_id"]
                    s_meta = skills_map.get(pid.lower()) if use_palworld_db else {}
                    pd = {
                        "instance_id": iid,
                        "id": pid,
                        "name": s_meta.get("name") or pid,
                        "rank": s_meta.get("power", 1) if use_palworld_db else 1,
                        "description": s_meta.get("description"),
                        "stat_modifier": s_meta.get("stat_modifier"),
                        "category": s_meta.get("category"),
                        "type": "Passive",
                        "icon_path": transform_icon_path(s_meta.get("icon_path")),
                    }
                    pd = enrich_passive_skill(pd)
                    passives_map[iid].append(pd)
            except Exception:
                pass

        # 3. Batch load Waza (Attacks)
        waza_map = defaultdict(lambda: {"equip": [], "mastered": []})
        if inst_ids:
            try:
                id_placeholders = ",".join("?" for _ in inst_ids)
                w_rows = self.conn.execute(
                    f"SELECT instance_id, waza_id, is_equipped FROM pal_instance_waza WHERE instance_id IN ({id_placeholders}) ORDER BY is_equipped DESC",
                    inst_ids,
                ).fetchall()

                for wr in w_rows:
                    iid = wr["instance_id"]
                    wid = wr["waza_id"]
                    is_eq = wr["is_equipped"]
                    s_meta = (
                        skills_map.get(wid.lower())
                        or skills_map.get(wid.lower().replace("epalwazaid::", ""))
                        or {}
                    ) if use_palworld_db else {}

                    wd = {
                        "instance_id": iid,
                        "id": wid,
                        "name": s_meta.get("name") or wid.replace("EPalWazaID::", ""),
                        "element": s_meta.get("element"),
                        "power": s_meta.get("power"),
                        "cooldown": s_meta.get("cooldown"),
                        "cooldown_sec": s_meta.get("cooldown"),
                        "icon_path": transform_icon_path(s_meta.get("icon_path")),
                        "description": clean_skill_text(s_meta.get("description")),
                        "type": "Active",
                        "is_equipped": is_eq,
                    }
                    if is_eq == 1:
                        waza_map[iid]["equip"].append(wd)
                    else:
                        waza_map[iid]["mastered"].append(wd)
            except Exception:
                pass

        # 4. Batch load Status Points
        soul_map = defaultdict(dict)
        elixir_map = defaultdict(dict)
        if inst_ids:
            try:
                id_placeholders = ",".join("?" for _ in inst_ids)
                sp_rows = self.conn.execute(
                    f"SELECT instance_id, stat_name, points, type FROM pal_instance_status_points WHERE instance_id IN ({id_placeholders})",
                    inst_ids,
                ).fetchall()
                for spr in sp_rows:
                    if spr["type"] == "soul":
                        soul_map[spr["instance_id"]][spr["stat_name"]] = spr["points"]
                    elif spr["type"] == "elixir":
                        elixir_map[spr["instance_id"]][spr["stat_name"]] = spr["points"]
            except Exception:
                pass

        # 5. Batch load custom base names
        custom_names_map = self.get_base_camp_custom_names()

        results = []
        for r in rows:
            d = dict(r)
            base_id = d.get("location_details_base_camp_id")
            if base_id and base_id in custom_names_map:
                d["location_details_base_camp_name"] = custom_names_map[base_id]

            sp = (d.get("species") or "").lower()
            clean_sp = sp[5:] if sp.startswith("boss_") else sp
            p_meta = pals_map.get(clean_sp) or pals_map.get(sp) or {}
            d["display_name"] = p_meta.get("display_name") or d.get("species")
            d["element_1"] = p_meta.get("element_1")
            d["element_2"] = p_meta.get("element_2")
            d["hp"] = p_meta.get("hp")
            d["attack_melee"] = p_meta.get("attack_melee")
            d["defense"] = p_meta.get("defense")
            d["icon_path"] = transform_icon_path(p_meta.get("icon_path"))
            pal_key = (p_meta.get("internal_name") or p_meta.get("id") or d.get("character_id") or d.get("species") or "").lower()
            d["partner_skill_categories"] = pal_cats_map.get(pal_key, [])
            inst_id = d.get("instance_id")
            inst_passives = passives_map.get(inst_id, [])
            d["passives"] = inst_passives
            d["equip_waza"] = waza_map[inst_id]["equip"]
            d["mastered_waza"] = waza_map[inst_id]["mastered"]
            d["soul_points"] = soul_map.get(inst_id, {})
            d["elixir_points"] = elixir_map.get(inst_id, {})
            d["ivs"] = {
                "hp": d.get("iv_hp"),
                "melee": d.get("iv_melee"),
                "shot": d.get("iv_shot"),
                "defense": d.get("iv_defense"),
            }

            # Calculate movement speed & passive buffs
            base_speed = int(p_meta.get("run_speed") or p_meta.get("speed") or 0)
            speed_mod = 0
            speed_buffs = []
            for pas in inst_passives:
                p_name = str(pas.get("name") or pas.get("id") or "").lower()
                if "swift" in p_name:
                    speed_mod += 30
                    speed_buffs.append("Swift (+30%)")
                elif "runner" in p_name:
                    speed_mod += 20
                    speed_buffs.append("Runner (+20%)")
                elif "nimble" in p_name:
                    speed_mod += 10
                    speed_buffs.append("Nimble (+10%)")
                elif "legend" in p_name:
                    speed_mod += 15
                    speed_buffs.append("Legend (+15%)")
                elif "ace swimmer" in p_name:
                    speed_mod += 15
                    speed_buffs.append("Ace Swimmer (+15%)")
                elif "king of the waves" in p_name:
                    speed_mod += 30
                    speed_buffs.append("King of the Waves (+30%)")

            d["base_speed"] = base_speed
            d["speed_modifier_pct"] = speed_mod
            d["speed_buffs"] = speed_buffs
            d["current_speed"] = round(base_speed * (1.0 + speed_mod / 100.0)) if base_speed else 0
            
            # Attach work suitabilities
            inst_ws = pal_ws_map.get(clean_sp, {}) or pal_ws_map.get(sp, {}) or pal_ws_map.get(pal_key, {})
            d["suitabilities"] = inst_ws
            d["work_suitabilities"] = inst_ws

            # Attach rank-scaled partner skill
            ps_meta = skills_map.get(f"partnerskill_{pal_key}") or skills_map.get(f"partnerskill_{clean_sp}")
            if not ps_meta and use_palworld_db:
                for sk_k, sk_v in skills_map.items():
                    if sk_v.get("type") == "Partner" and (str(sk_v.get("pal_internal_name", "")).lower() in (pal_key, clean_sp, sp)):
                        ps_meta = sk_v
                        break

            from palengine.analytics.partner_skill_scaling import get_scaled_partner_skill
            pal_rank = int(d.get("rank") or 0)
            scaled_ps = get_scaled_partner_skill(
                species_id_or_name=p_meta.get("internal_name") or d.get("species") or d.get("display_name"),
                stars=pal_rank,
                base_description=ps_meta.get("description") if ps_meta else None,
                skill_name=ps_meta.get("name") if ps_meta else None,
                unlock_item=ps_meta.get("unlock_item") if ps_meta else None,
            )
            if ps_meta or scaled_ps.get("description"):
                d["partner_skill"] = {
                    **(ps_meta or {}),
                    **scaled_ps,
                }
            else:
                d["partner_skill"] = None
            
            results.append(d)

        return results

    def get_base_camp_summary(self, base_camp_id: str) -> Optional[dict[str, Any]]:
        """Returns details, workers, and structure counts for a given Base Camp."""
        base_row = self.conn.execute(
            """
            SELECT bc.*, cn.custom_name
            FROM base_camps bc
            LEFT JOIN base_camp_custom_names cn ON bc.base_camp_id = cn.base_camp_id
            WHERE bc.base_camp_id = ?
            """,
            (base_camp_id,),
        ).fetchone()

        if not base_row:
            return None

        summary = dict(base_row)
        if summary.get("custom_name"):
            summary["display_name"] = summary["custom_name"]
        else:
            summary["display_name"] = summary.get("name") or f"Base {base_camp_id[:8]}"

        struct_rows = self.conn.execute(
            """
            SELECT bsi.structure_name, bsi.count,
                   COALESCE(sa.display_name, bs.name, bsi.structure_name) as display_name,
                   COALESCE(bs.category, 'Infrastructure') as category
            FROM base_structures_instances bsi
            LEFT JOIN structure_aliases sa ON LOWER(bsi.structure_name) = LOWER(sa.alias)
            LEFT JOIN base_structures bs ON LOWER(bsi.structure_name) = LOWER(bs.id)
                                         OR LOWER(bsi.structure_name) = LOWER(bs.name)
                                         OR LOWER(sa.canonical_name) = LOWER(bs.id)
                                         OR LOWER(sa.canonical_name) = LOWER(bs.name)
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
            SELECT i.instance_id, i.species, i.level, i.rank, i.iv_hp, i.iv_melee, i.iv_defense, i.location, i.location_details_base_camp_name,
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
                'pals': pals,
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

            loc_counts = defaultdict(int)
            for p in c['pals']:
                loc = (p.get('location') or 'storage').lower()
                if loc == 'dps': loc_counts['Dimensional Storage'] += 1
                elif loc == 'palbox': loc_counts['Palbox'] += 1
                elif loc == 'party': loc_counts['Party'] += 1
                elif loc == 'base': loc_counts['Base Camp'] += 1
                else: loc_counts['Storage'] += 1
            
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

            best_loc_str = (best.get('location') or 'storage').lower()
            if best_loc_str == 'dps': best_loc_display = 'Dimensional Storage'
            elif best_loc_str == 'palbox': best_loc_display = 'Palbox'
            elif best_loc_str == 'party': best_loc_display = 'Party'
            # Attach partner skill categories
            c_cats = []
            try:
                cat_rows = self.conn.execute(
                    """
                    SELECT DISTINCT c.category_id as id, c.name, c.icon, c.description
                    FROM pal_partner_skill_categories pc
                    JOIN partner_skill_categories c ON pc.category_id = c.category_id
                    WHERE LOWER(pc.pal_internal_name) = LOWER(?) OR LOWER(pc.pal_internal_name) = LOWER(?)
                    ORDER BY c.sort_order ASC
                    """,
                    (species, best.get("species", "")),
                ).fetchall()
                c_cats = [dict(cr) for cr in cat_rows]
            except Exception:
                c_cats = []

            results.append({
                'species': species,
                'total_owned': total_owned,
                'sacrifices_available': sacrifices,
                'attainable_stars': attainable_stars,
                'base_level': lvl,
                'best_location': best_loc_display,
                'locations_breakdown': dict(loc_counts),
                'hp': est_hp,
                'attack': est_atk,
                'defense': est_def,
                'iv_hp': iv_hp,
                'iv_attack': iv_atk,
                'iv_defense': iv_def,
                'passives': passives_list,
                'partner_skill_categories': c_cats,
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
        rows = cursor.execute(
            """
            SELECT food_rating, 
                   AVG(satiety_amount) as satiety_amount, 
                   AVG(san_decay_multiplier) as san_decay_multiplier
            FROM food_satiety_rates 
            GROUP BY food_rating 
            ORDER BY food_rating ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def get_world_settings(self) -> dict[str, Any]:
        """Returns extracted world multiplier settings from WorldOption.sav or PalWorldSettings.ini."""
        cursor = self.conn.cursor()
        try:
            rows = cursor.execute("SELECT setting_key, setting_value FROM world_settings").fetchall()
            res: dict[str, Any] = {}
            for r in rows:
                val_str = r["setting_value"]
                if val_str.lower() == "true":
                    res[r["setting_key"]] = True
                elif val_str.lower() == "false":
                    res[r["setting_key"]] = False
                else:
                    try:
                        if "." in val_str:
                            res[r["setting_key"]] = float(val_str)
                        else:
                            res[r["setting_key"]] = int(val_str)
                    except ValueError:
                        res[r["setting_key"]] = val_str
            return res
        except Exception:
            return {}

    def set_base_camp_custom_name(self, base_camp_id: str, custom_name: str) -> None:
        """Sets a custom user-defined display name for a base camp."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO base_camp_custom_names (base_camp_id, custom_name)
            VALUES (?, ?)
            """,
            (base_camp_id, custom_name.strip()),
        )
        self.conn.commit()
        self._cached_base_recommendations = None

    def get_base_camp_custom_names(self) -> dict[str, str]:
        """Returns mapping of base_camp_id to custom_name."""
        cursor = self.conn.cursor()
        try:
            rows = cursor.execute("SELECT base_camp_id, custom_name FROM base_camp_custom_names").fetchall()
            return {r["base_camp_id"]: r["custom_name"] for r in rows}
        except Exception:
            return {}

    def get_base_camps(self) -> list[dict[str, Any]]:
        """Returns all base camps with structure counts, assigned Pals, and dynamic max capacity."""
        cursor = self.conn.cursor()
        camps = cursor.execute(
            """
            SELECT bc.base_camp_id, bc.name, cn.custom_name
            FROM base_camps bc
            LEFT JOIN base_camp_custom_names cn ON bc.base_camp_id = cn.base_camp_id
            """
        ).fetchall()
        settings = self.get_world_settings()
        default_max = int(settings.get("BaseCampWorkerMaxNum", 15))

        results = []
        for c in camps:
            c_dict = dict(c)
            camp_id = c_dict["base_camp_id"]
            if c_dict.get("custom_name"):
                c_dict["display_name"] = c_dict["custom_name"]
            else:
                c_dict["display_name"] = c_dict.get("name") or f"Base {camp_id[:8]}"
            
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
            c_dict["max_pals"] = max(assigned_count, default_max)
            results.append(c_dict)
        return results

    def get_base_camp_structures(self, base_camp_id: str) -> list[dict[str, Any]]:
        """Returns structures present in a base camp with their work suitabilities."""
        cursor = self.conn.cursor()
        rows = cursor.execute(
            """
            SELECT bsi.structure_name, bsi.count,
                   COALESCE(bwt.work_type, sa.work_type) as work_type,
                   COALESCE(bwt.is_automated, sa.is_automated, 0) as is_automated,
                   COALESCE(bwt.work_amount_modifier, 1.0) as work_amount_modifier,
                   COALESCE(sa.display_name, bs.name, bsi.structure_name) as display_name
            FROM base_structures_instances bsi
            LEFT JOIN structure_aliases sa ON LOWER(bsi.structure_name) = LOWER(sa.alias)
                                           OR LOWER(REPLACE(bsi.structure_name, '_', ' ')) = LOWER(sa.alias)
                                           OR LOWER(REPLACE(bsi.structure_name, ' ', '')) = LOWER(REPLACE(sa.alias, ' ', ''))
            LEFT JOIN building_work_types bwt ON LOWER(bsi.structure_name) = LOWER(bwt.building_id)
                                              OR LOWER(sa.canonical_name) = LOWER(bwt.building_id)
                                              OR LOWER(REPLACE(bsi.structure_name, '_', '')) = LOWER(REPLACE(bwt.building_id, '_', ''))
            LEFT JOIN base_structures bs ON LOWER(bsi.structure_name) = LOWER(bs.id)
            WHERE bsi.base_camp_id = ?
            """,
            (base_camp_id,),
        ).fetchall()
        
        # Group by structure_name (ignoring natural clutter, terrain nodes, and drop items)
        structures_map: dict[str, dict[str, Any]] = {}
        for r in rows:
            s_name = r["structure_name"]
            count = r["count"]
            disp_name = r["display_name"]
            s_lower = s_name.lower().replace(" ", "").replace("_", "")
            if s_lower.startswith("natural") or "damagable" in s_lower or "dropitem" in s_lower or s_lower in ("tree", "treenode", "rock"):
                continue

            if s_name not in structures_map:
                structures_map[s_name] = {
                    "structure_name": s_name,
                    "display_name": disp_name,
                    "count": count,
                    "work_types": [],
                }
            if r["work_type"]:
                structures_map[s_name]["work_types"].append({
                    "work_type": r["work_type"],
                    "is_automated": r["is_automated"],
                    "work_amount_modifier": r["work_amount_modifier"],
                })

        result_list = list(structures_map.values())

        # If base has automated production structures (farms/pits/ranches), ensure Transporting is included in work demand
        has_logistics_demand = any(
            any(wt["work_type"] in ["Planting", "Mining", "Lumbering", "Watering", "Farming", "MonsterFarm", "Kindling", "Handcraft"] for wt in item.get("work_types", []))
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
        """Returns all owned Pal instances in the Palbox with work suitabilities and passives (batch-optimized)."""
        cursor = self.conn.cursor()
        instances = cursor.execute(
            """
            SELECT pi.*, p.display_name, p.paldex_number, p.food_requirement, p.nocturnal, p.icon_path
            FROM pal_instances pi
            LEFT JOIN pals p ON LOWER(REPLACE(pi.species, 'BOSS_', '')) = LOWER(p.internal_name)
                             OR LOWER(pi.species) = LOWER(p.internal_name)
                             OR LOWER(pi.species) = LOWER(p.display_name)
            WHERE pi.location IN ('palbox', 'base', 'party', 'dps')
            """
        ).fetchall()

        if not instances:
            return []

        # Batch load suitabilities into lookup dict
        ws_lookup: dict[str, dict[str, int]] = {}
        for r in cursor.execute("SELECT LOWER(pal_internal_name) as k, suitability_name, level FROM pal_work_suitabilities").fetchall():
            k = r["k"]
            if k not in ws_lookup:
                ws_lookup[k] = {}
            ws_lookup[k][r["suitability_name"]] = r["level"]

        # Batch load passives into lookup dict
        pass_lookup: dict[str, list[dict[str, str]]] = {}
        for r in cursor.execute(
            """
            SELECT pip.instance_id, COALESCE(ps.name, pip.passive_id) as name, pip.passive_id as id
            FROM pal_instance_passives pip
            LEFT JOIN passive_skills ps ON LOWER(pip.passive_id) = LOWER(ps.id)
            """
        ).fetchall():
            iid = r["instance_id"]
            if iid not in pass_lookup:
                pass_lookup[iid] = []
            pass_lookup[iid].append({"name": r["name"], "id": r["id"]})

        custom_names_map = self.get_base_camp_custom_names()

        results = []
        for inst in instances:
            d = dict(inst)
            inst_id = d["instance_id"]
            base_id = d.get("location_details_base_camp_id")
            if base_id and base_id in custom_names_map:
                d["location_details_base_camp_name"] = custom_names_map[base_id]

            species_clean = (d.get("species") or "").lower().replace("boss_", "")
            species_raw = (d.get("species") or "").lower()

            d["suitabilities"] = ws_lookup.get(species_clean) or ws_lookup.get(species_raw, {})
            pass_list = pass_lookup.get(inst_id, [])
            d["passives"] = [p["name"] for p in pass_list]
            d["raw_passives"] = [p["id"] for p in pass_list]
            d["icon_path"] = transform_icon_path(d.get("icon_path"))
            results.append(d)
        return results

    def get_passive_skill_modifiers(self) -> dict[str, dict[str, float]]:
        """Returns mapping of passive skill modifiers from SQLite keyed by lowercase id and name."""
        try:
            cursor = self.conn.cursor()
            rows = cursor.execute(
                "SELECT passive_id, name, work_speed_mod, move_speed_mod, san_decay_pts, hunger_rate_pts FROM passive_skill_modifiers"
            ).fetchall()
            mod_map: dict[str, dict[str, float]] = {}
            for r in rows:
                entry = {
                    "work_speed_mod": float(r["work_speed_mod"] or 0.0),
                    "move_speed_mod": float(r["move_speed_mod"] or 0.0),
                    "san_decay_pts": float(r["san_decay_pts"] or 0.0),
                    "hunger_rate_pts": float(r["hunger_rate_pts"] or 0.0),
                }
                if r["passive_id"]:
                    mod_map[r["passive_id"].lower().strip()] = entry
                if r["name"]:
                    mod_map[r["name"].lower().strip()] = entry
            return mod_map
        except Exception:
            return {}

    def get_partner_skill_categories_map(self) -> dict[str, set[str]]:
        """Returns mapping of category_id -> set of lowercase pal internal names from SQLite."""
        try:
            cursor = self.conn.cursor()
            rows = cursor.execute(
                "SELECT category_id, LOWER(pal_internal_name) as p_name FROM pal_partner_skill_categories"
            ).fetchall()
            cat_map: dict[str, set[str]] = defaultdict(set)
            for r in rows:
                if r["category_id"] and r["p_name"]:
                    cat_map[r["category_id"]].add(r["p_name"])
            return cat_map
        except Exception:
            return defaultdict(set)

    def get_active_missions(self, save_path: Optional[str] = None) -> list[dict[str, Any]]:
        """Evaluates active uncompleted NPC sub-missions against targeted inventory items and caught Pals."""
        if save_path is None and getattr(self, "_cached_active_missions", None) is not None:
            return self._cached_active_missions

        cursor = self.conn.cursor()

        # 1. Read cached active quest IDs from database
        cursor.execute("CREATE TABLE IF NOT EXISTS player_active_missions (quest_id TEXT PRIMARY KEY)")
        rows = cursor.execute("SELECT quest_id FROM player_active_missions").fetchall()
        active_ids = [r["quest_id"] for r in rows if r["quest_id"]]

        if not active_ids:
            effective_path = save_path or self.current_save_path
            if effective_path:
                extracted = extract_active_quests(effective_path)
                for q in extracted:
                    if q.get("quest_id"):
                        cursor.execute("INSERT OR REPLACE INTO player_active_missions (quest_id) VALUES (?)", (q["quest_id"],))
                self.conn.commit()
                active_ids = [q["quest_id"] for q in extracted if q.get("quest_id")]

        if not active_ids:
            # Fallback: if no active missions, check sub_missions table
            all_m_rows = cursor.execute("SELECT id FROM sub_missions LIMIT 25").fetchall()
            active_ids = [r["id"] for r in all_m_rows]

        if not active_ids:
            return []

        # 2. Query master missions from SQLite
        sub_m_cols = [c[1] for c in cursor.execute("PRAGMA table_info(sub_missions)").fetchall()]
        has_alias = "alias_id" in sub_m_cols
        placeholders = ",".join("?" for _ in active_ids)

        missions_by_key = {}
        if has_alias:
            m_rows = cursor.execute(
                f"""
                SELECT id, alias_id, category, title, npc_name, location, objective, mission_type, requires_giving_pal
                FROM sub_missions
                WHERE id IN ({placeholders}) OR alias_id IN ({placeholders})
                """,
                active_ids + active_ids
            ).fetchall()
            for mr in m_rows:
                m_dict = dict(mr)
                missions_by_key[mr["id"].lower()] = m_dict
                if mr["alias_id"]:
                    missions_by_key[mr["alias_id"].lower()] = m_dict
        else:
            m_rows = cursor.execute(
                f"""
                SELECT id, category, title, npc_name, objective, target_type, target_id, target_count
                FROM sub_missions
                WHERE id IN ({placeholders})
                """,
                active_ids
            ).fetchall()
            for mr in m_rows:
                m_dict = dict(mr)
                m_dict["alias_id"] = None
                m_dict["location"] = "Palpagos Islands"
                m_dict["mission_type"] = "item_delivery" if m_dict.get("target_type") == "Item" else "pal_give" if m_dict.get("target_type") in ("Pal", "PassiveSkill") else "hunt"
                m_dict["requires_giving_pal"] = 1 if m_dict.get("target_type") in ("Pal", "PassiveSkill") else 0
                missions_by_key[mr["id"].lower()] = m_dict

        found_db_ids = list({m["id"] for m in missions_by_key.values()})
        targets_by_mid: dict[str, list[dict[str, Any]]] = defaultdict(list)
        rewards_by_mid: dict[str, list[dict[str, Any]]] = defaultdict(list)
        needed_item_ids: set[str] = set()

        if found_db_ids:
            db_placeholders = ",".join("?" for _ in found_db_ids)
            try:
                t_rows = cursor.execute(
                    f"""
                    SELECT mission_id, target_type, target_id, target_name, target_count, target_passive, target_suitability
                    FROM sub_mission_targets
                    WHERE mission_id IN ({db_placeholders})
                    """,
                    found_db_ids
                ).fetchall()
                for tr in t_rows:
                    td = dict(tr)
                    targets_by_mid[tr["mission_id"]].append(td)
                    if tr["target_type"] == "item" and tr["target_id"]:
                        needed_item_ids.add(tr["target_id"].lower())
            except Exception:
                pass

            try:
                r_rows = cursor.execute(
                    f"""
                    SELECT mission_id, reward_type, item_id, item_name, quantity
                    FROM sub_mission_rewards
                    WHERE mission_id IN ({db_placeholders})
                    """,
                    found_db_ids
                ).fetchall()
                for rr in r_rows:
                    rewards_by_mid[rr["mission_id"]].append(dict(rr))
            except Exception:
                pass

        # 3. Targeted inventory query (personal + base chests)
        item_counts: dict[str, int] = {}
        if needed_item_ids:
            item_placeholders = ",".join("?" for _ in needed_item_ids)
            inv_rows = cursor.execute(
                f"SELECT LOWER(item_id) as item_id, SUM(count) as total_count FROM item_container_slots WHERE LOWER(item_id) IN ({item_placeholders}) GROUP BY LOWER(item_id)",
                list(needed_item_ids),
            ).fetchall()
            for ir in inv_rows:
                item_counts[ir["item_id"]] = ir["total_count"] or 0

        # Build evaluated missions
        evaluated_missions = []
        for raw_qid in active_ids:
            clean_key = raw_qid.lower()
            m_def = missions_by_key.get(clean_key) or missions_by_key.get(clean_key.replace("sub_", ""))

            if not m_def:
                m_def = {
                    "id": raw_qid,
                    "title": raw_qid.replace("Sub_", "").replace("_", " "),
                    "npc_name": "World NPC",
                    "location": "Palpagos Islands",
                    "objective": raw_qid,
                    "mission_type": "custom",
                    "requires_giving_pal": 0,
                }

            mid = m_def["id"]
            m_targets = targets_by_mid.get(mid, [])
            m_rewards = rewards_by_mid.get(mid, [])

            # Format reward string
            reward_parts = []
            for r in m_rewards:
                r_type = r.get("reward_type")
                qty = r.get("quantity", 1)
                i_name = r.get("item_name")
                if r_type == "Exp":
                    reward_parts.append(f"+{qty:,} EXP")
                elif r_type == "Gold":
                    reward_parts.append(f"{qty:,} Gold")
                elif i_name:
                    reward_parts.append(f"{qty} {i_name}" if qty > 1 else f"1 {i_name}")
            reward_str = ", ".join(reward_parts)

            req_items_eval = []
            req_pals_eval = []
            all_items_met = True
            all_pals_met = True
            has_some_items = False
            has_some_pals = False

            for tgt in m_targets:
                tt = tgt.get("target_type")
                need = tgt.get("target_count", 1)

                if tt == "item":
                    iid = str(tgt.get("target_id") or "").lower()
                    have = item_counts.get(iid, 0)
                    is_met = have >= need
                    if not is_met:
                        all_items_met = False
                    if have > 0:
                        has_some_items = True
                    req_items_eval.append({
                        "item_id": tgt.get("target_id"),
                        "name": tgt.get("target_name"),
                        "count_required": need,
                        "count_have": have,
                        "is_met": is_met,
                    })

                elif tt in ("pal", "passive", "suitability"):
                    spec = str(tgt.get("target_id") or "").strip()
                    req_passive = tgt.get("target_passive")
                    req_suit = tgt.get("target_suitability")

                    try:
                        if req_passive and spec:
                            p_rows = cursor.execute("""
                                SELECT p.instance_id, p.species, p.location, p.location_details_base_camp_name
                                FROM pal_instances p
                                LEFT JOIN pals ON LOWER(p.species) = LOWER(pals.internal_name) OR LOWER(p.species) = LOWER(pals.id)
                                JOIN pal_instance_passives pip ON p.instance_id = pip.instance_id
                                WHERE (LOWER(p.species) = LOWER(?) OR LOWER(COALESCE(pals.display_name, '')) = LOWER(?) OR LOWER(COALESCE(pals.internal_name, '')) = LOWER(?))
                                  AND (LOWER(pip.passive_id) LIKE LOWER(?) OR LOWER(pip.passive_id) = LOWER(?))
                            """, (spec, spec, spec, f"%{req_passive}%", req_passive)).fetchall()
                        elif req_passive:
                            p_rows = cursor.execute("""
                                SELECT p.instance_id, p.species, p.location, p.location_details_base_camp_name
                                FROM pal_instances p
                                JOIN pal_instance_passives pip ON p.instance_id = pip.instance_id
                                WHERE (LOWER(pip.passive_id) LIKE LOWER(?) OR LOWER(pip.passive_id) = LOWER(?))
                            """, (f"%{req_passive}%", req_passive)).fetchall()
                        elif spec:
                            p_rows = cursor.execute("""
                                SELECT p.instance_id, p.species, p.location, p.location_details_base_camp_name
                                FROM pal_instances p
                                LEFT JOIN pals ON LOWER(p.species) = LOWER(pals.internal_name) OR LOWER(p.species) = LOWER(pals.id)
                                WHERE LOWER(p.species) = LOWER(?) OR LOWER(COALESCE(pals.display_name, '')) = LOWER(?) OR LOWER(COALESCE(pals.internal_name, '')) = LOWER(?)
                            """, (spec, spec, spec)).fetchall()
                        else:
                            p_rows = []
                    except Exception:
                        p_rows = []

                    have = len(p_rows)
                    is_met = have >= need
                    if not is_met:
                        all_pals_met = False
                    if have > 0:
                        has_some_pals = True

                    locations_found = set()
                    for prow in p_rows:
                        loc = (prow["location"] or "storage").lower()
                        if loc == "palbox":
                            locations_found.add("Palbox")
                        elif loc == "party":
                            locations_found.add("Party")
                        elif loc == "base":
                            bname = prow["location_details_base_camp_name"]
                            locations_found.add(f"Base: {bname}" if bname else "Base")
                        elif loc == "cage":
                            bname = prow["location_details_base_camp_name"]
                            locations_found.add(f"Cage: {bname}" if bname else "Cage")
                        elif loc == "dps":
                            locations_found.add("Dimensional Storage")
                        else:
                            locations_found.add("Storage")

                    req_pals_eval.append({
                        "species": tgt.get("target_id"),
                        "name": tgt.get("target_name"),
                        "passive": req_passive,
                        "count_required": need,
                        "count_have": have,
                        "is_met": is_met,
                        "locations": sorted(list(locations_found)),
                    })

            is_ready = (all_items_met and all_pals_met) if (req_items_eval or req_pals_eval) else False
            if is_ready:
                status = "ready"
            elif has_some_items or has_some_pals:
                status = "in_progress"
            else:
                status = "missing"

            evaluated_missions.append({
                "quest_id": raw_qid,
                "name": m_def["title"],
                "npc_name": m_def["npc_name"],
                "location": m_def["location"],
                "objective": m_def["objective"],
                "type": m_def["mission_type"],
                "requires_giving_pal": bool(m_def.get("requires_giving_pal")),
                "required_items": req_items_eval,
                "required_pals": req_pals_eval,
                "rewards": reward_str,
                "status": status,
                "is_ready": is_ready,
            })

        # Group missions by settlement / location
        locations_map: dict[str, list[dict[str, Any]]] = {}
        for m in evaluated_missions:
            loc = m.get("location", "Palpagos Islands")
            if loc not in locations_map:
                locations_map[loc] = []
            locations_map[loc].append(m)

        grouped_locations = []
        for loc_name, m_list in locations_map.items():
            ready_count = sum(1 for m in m_list if m["is_ready"])
            grouped_locations.append({
                "location": loc_name,
                "total_missions": len(m_list),
                "ready_missions": ready_count,
                "has_batch_turnin": ready_count >= 2,
                "missions": m_list,
            })

        if save_path is None:
            self._cached_active_missions = grouped_locations

        return grouped_locations

