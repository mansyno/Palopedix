import pytest
import sqlite3
from palengine.db.sqlite_engine import SQLiteEngine


def test_get_active_missions_evaluation(tmp_path):
    """Tests targeted inventory & pal checks for active missions with SQLite tables."""
    db_file = tmp_path / "test_missions.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE item_containers (
            container_id TEXT PRIMARY KEY,
            container_type TEXT,
            slot_count INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE item_container_slots (
            container_id TEXT,
            slot_index INTEGER,
            item_id TEXT,
            count INTEGER,
            PRIMARY KEY (container_id, slot_index)
        )
    """)
    cursor.execute("""
        CREATE TABLE pal_instances (
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
            location_details_base_camp_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE pal_instance_passives (
            instance_id TEXT,
            passive_id TEXT,
            PRIMARY KEY (instance_id, passive_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE player_active_missions (
            quest_id TEXT PRIMARY KEY
        )
    """)

    cursor.execute("""
        CREATE TABLE sub_missions (
            id TEXT PRIMARY KEY,
            alias_id TEXT,
            category TEXT,
            title TEXT,
            npc_name TEXT,
            location TEXT,
            objective TEXT,
            mission_type TEXT,
            requires_giving_pal INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE sub_mission_targets (
            id INTEGER PRIMARY KEY,
            mission_id TEXT,
            target_type TEXT,
            target_id TEXT,
            target_name TEXT,
            target_count INTEGER,
            target_passive TEXT,
            target_suitability TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE sub_mission_rewards (
            id INTEGER PRIMARY KEY,
            mission_id TEXT,
            reward_type TEXT,
            item_id TEXT,
            item_name TEXT,
            quantity INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE items (
            id TEXT PRIMARY KEY,
            name TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE pals (
            id TEXT PRIMARY KEY,
            internal_name TEXT,
            display_name TEXT
        )
    """)

    # Insert items: 10 Berries, 2 Wool, 1 Gyoza
    cursor.execute("INSERT INTO item_containers VALUES ('c1', 'player', 10)")
    cursor.execute("INSERT INTO item_container_slots VALUES ('c1', 0, 'Berries', 10)")
    cursor.execute("INSERT INTO item_container_slots VALUES ('c1', 1, 'Wool', 2)")
    cursor.execute("INSERT INTO item_container_slots VALUES ('c1', 2, 'Gyoza', 1)")

    # Insert Pal: 1 Lamball
    # Insert Pal: 1 Lamball in Palbox (species stored as SheepBall)
    cursor.execute("INSERT INTO pals (id, internal_name, display_name) VALUES ('SheepBall', 'SheepBall', 'Lamball')")
    cursor.execute("INSERT INTO pal_instances (instance_id, species, level, rank, location) VALUES ('p1', 'SheepBall', 5, 0, 'palbox')")

    # Insert Active Missions: Sub_PalDisplay_A and Sub_FoodReward
    cursor.execute("INSERT INTO player_active_missions (quest_id) VALUES ('Sub_PalDisplay_A')")
    cursor.execute("INSERT INTO player_active_missions (quest_id) VALUES ('Sub_FoodReward')")

    # Insert Sub Missions
    cursor.execute("INSERT INTO sub_missions VALUES ('Sub_PalDisplay_A', 'PalDisplay_A', 'SubQuest', 'Request from Pal Critic (Lamball)', 'Pal Critic', 'Small Settlement', 'Show a Lamball to the Pal Critic', 'pal_show', 0)")
    cursor.execute("INSERT INTO sub_missions VALUES ('Sub_FoodReward', 'Food', 'SubQuest', 'Request from an Arrogant Foodie', 'Arrogant Gourmet', 'Windswept Hills', 'Deliver 1 Dumplings to the Gourmet', 'item_delivery', 0)")

    # Insert Targets
    cursor.execute("INSERT INTO sub_mission_targets VALUES (1, 'Sub_PalDisplay_A', 'pal', 'SheepBall', 'Lamball', 1, NULL, NULL)")
    cursor.execute("INSERT INTO sub_mission_targets VALUES (2, 'Sub_FoodReward', 'item', 'Gyoza', 'Dumplings', 1, NULL, NULL)")

    # Insert Rewards
    cursor.execute("INSERT INTO sub_mission_rewards VALUES (1, 'Sub_FoodReward', 'Item', 'TechnicalBook_G3', 'High Grade Technical Manual', 3)")
    cursor.execute("INSERT INTO sub_mission_rewards VALUES (2, 'Sub_PalDisplay_A', 'Gold', NULL, 'Gold', 500)")

    conn.commit()
    conn.close()

    # Instantiate isolated SQLiteEngine
    engine = SQLiteEngine.__new__(SQLiteEngine)
    engine.conn = sqlite3.connect(str(db_file))
    engine.conn.row_factory = sqlite3.Row
    engine.current_save_path = None

    # Evaluate active missions
    grouped = engine.get_active_missions(save_path=None)
    assert isinstance(grouped, list)
    assert len(grouped) > 0

    # Check Small Settlement missions
    small_settlement = next((g for g in grouped if g["location"] == "Small Settlement"), None)
    assert small_settlement is not None
    missions = small_settlement["missions"]

    # Request from Pal Critic (Sub_PalDisplay_A): Needs 1 Lamball. We have 1 in Palbox -> Ready!
    critic_m = next((m for m in missions if m["quest_id"] == "Sub_PalDisplay_A"), None)
    assert critic_m is not None
    assert critic_m["is_ready"] is True
    assert critic_m["status"] == "ready"
    assert critic_m["required_pals"][0]["count_have"] == 1
    assert critic_m["required_pals"][0]["is_met"] is True
    assert "Palbox" in critic_m["required_pals"][0]["locations"]

    # Check Windswept Hills missions: Request from an Arrogant Foodie (Sub_FoodReward): Needs 1 Gyoza. We have 1 -> Ready!
    windswept = next((g for g in grouped if g["location"] == "Windswept Hills"), None)
    assert windswept is not None
    foodie_m = next((m for m in windswept["missions"] if m["quest_id"] == "Sub_FoodReward"), None)
    assert foodie_m is not None
    assert foodie_m["is_ready"] is True
    assert foodie_m["required_items"][0]["count_have"] == 1
    assert foodie_m["required_items"][0]["is_met"] is True
    assert "High Grade Technical Manual" in foodie_m["rewards"] or "TechnicalBook_G3" in foodie_m["rewards"]
