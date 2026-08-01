# Database Schema & Visual Assets Integration Specification

This document provides a complete, structured reference for integrating the extracted Palworld SQLite database (`palworld.db`) and its companion PNG visual assets into downstream applications (e.g. `palengine` / `palopedix`).

---

## 1. Environment & File Locations

- **SQLite Database**: `c:\AI\palDBxtrct\palworld.db`
- **Schema DDL Script**: [schema.sql](file:///c:/AI/palDBxtrct/schema.sql)
- **Visual Assets Storage Directory**: `C:/palworld_assets/`
  - **Pal Headshots**: `C:/palworld_assets/pals/{pal_id}.png` (289 PNGs)
  - **Elemental Type Icons**: `C:/palworld_assets/elements/{element_name}.png` (12 PNGs)
  - **Items & Equipment Icons**: `C:/palworld_assets/items/{item_id}.png` (1,199 PNGs)
  - **Work Suitability HUD Symbols**: `C:/palworld_assets/work/{work_type_id}.png` (12 PNGs)
  - **Base Building Icons**: `C:/palworld_assets/buildings/{building_id}.png` (494 PNGs)

---

## 2. Table Changes & New Relational Tables Summary

### Modified Pre-existing Tables
- **`skills` Table**: Extended with 5 new metadata columns:
  - `category TEXT`: Skill classification (`'Standard'`, `'Exclusive'`, `'BossExclusive'`, `'Passive'`, `'Partner'`).
  - `min_range REAL`: Minimum effective targeting range.
  - `max_range REAL`: Maximum effective targeting range.
  - `stat_modifier TEXT`: Stat bonus descriptor for passives (e.g. `'+20% Attack'`).
  - `unlock_item TEXT`: Partner skill unlock requirement item name.

### New Relational Tables
1. **`items`**: Stores 1,891 items with rarity, max stack, weight, price, combat stats, restore values & icon paths.
2. **`recipes`**: Stores 872 crafting recipes, work effort required, and crafting facility IDs.
3. **`recipe_ingredients`**: Relational junction table linking recipes to required materials and item counts.
4. **`work_types`**: Stores 12 canonical Palworld work suitability types with descriptions and colored HUD symbol paths.
5. **`work_suitability`**: Relational junction table linking Pals to work types and level scaling (1 to 5).
6. **`drops`**: Stores 1,734 item drop records (min/max quantity and drop rate percentage).
7. **`breeding_combos`**: Stores 256 unique breeding parent combinations (`parent1_id`, `parent2_id` -> `child_id`).
8. **`buildings`**: Stores 552 base facilities, crafting stations, defenses, tech level unlocks & building icon paths.
9. **`technology_tree`**: Stores 839 technology nodes, tech point costs, level requirements, and unlocks.

---

## 3. Complete DDL Schema Reference

```sql
-- 1. Pals Table
CREATE TABLE IF NOT EXISTS pals (
    id TEXT PRIMARY KEY,
    code TEXT,
    name TEXT NOT NULL,
    paldex_number INTEGER,
    element1 TEXT,
    element2 TEXT,
    hp INTEGER,
    attack INTEGER,
    defense INTEGER,
    run_speed INTEGER,
    stamina INTEGER,
    food INTEGER,
    rarity INTEGER,
    breeding_rank INTEGER,
    nocturnal INTEGER, -- 0 or 1
    icon_path TEXT,
    description TEXT
);

-- 2. Extended Skills & Linkage Tables
CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    element TEXT,
    type TEXT, -- 'Active', 'Passive', 'Partner'
    category TEXT, -- 'Standard', 'Exclusive', 'BossExclusive', 'Passive', 'Partner'
    power INTEGER,
    cooldown INTEGER,
    min_range REAL,
    max_range REAL,
    stat_modifier TEXT,
    unlock_item TEXT,
    description TEXT,
    icon_path TEXT
);

CREATE TABLE IF NOT EXISTS pal_skills (
    pal_id TEXT,
    skill_id TEXT,
    level_learned INTEGER DEFAULT 1,
    PRIMARY KEY (pal_id, skill_id),
    FOREIGN KEY (pal_id) REFERENCES pals(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
);

-- 3. Items & Crafting Recipe Tables
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT, -- 'Weapon', 'Armor', 'Sphere', 'Accessory', 'Material', etc.
    subcategory TEXT,
    rarity INTEGER,
    max_stack INTEGER,
    weight REAL,
    price INTEGER,
    defense INTEGER,
    shield INTEGER,
    durability INTEGER,
    hp_restore INTEGER,
    hunger_restore INTEGER,
    description TEXT,
    icon_path TEXT
);

CREATE TABLE IF NOT EXISTS recipes (
    id TEXT PRIMARY KEY,
    item_id TEXT,
    work_amount INTEGER,
    facility_id TEXT,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id TEXT,
    material_item_id TEXT,
    material_name TEXT,
    count INTEGER,
    PRIMARY KEY (recipe_id, material_item_id),
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- 4. Work Suitability & Types Tables
CREATE TABLE IF NOT EXISTS work_types (
    id TEXT PRIMARY KEY, -- 'Kindling', 'Watering', 'Handcraft', etc.
    name TEXT NOT NULL,
    description TEXT,
    icon_path TEXT
);

CREATE TABLE IF NOT EXISTS work_suitability (
    pal_id TEXT,
    work_type TEXT,
    level INTEGER, -- 1 to 5
    PRIMARY KEY (pal_id, work_type),
    FOREIGN KEY (pal_id) REFERENCES pals(id) ON DELETE CASCADE,
    FOREIGN KEY (work_type) REFERENCES work_types(id) ON DELETE CASCADE
);

-- 5. Item Drops Table
CREATE TABLE IF NOT EXISTS drops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pal_id TEXT,
    item_id TEXT,
    item_name TEXT,
    min_quantity INTEGER,
    max_quantity INTEGER,
    drop_rate REAL,
    FOREIGN KEY (pal_id) REFERENCES pals(id) ON DELETE CASCADE
);

-- 6. Breeding Combinations Table
CREATE TABLE IF NOT EXISTS breeding_combos (
    parent1_id TEXT,
    parent2_id TEXT,
    child_id TEXT,
    is_unique INTEGER DEFAULT 0,
    PRIMARY KEY (parent1_id, parent2_id),
    FOREIGN KEY (parent1_id) REFERENCES pals(id),
    FOREIGN KEY (parent2_id) REFERENCES pals(id),
    FOREIGN KEY (child_id) REFERENCES pals(id)
);

-- 7. Base Buildings & Technology Tree Tables
CREATE TABLE IF NOT EXISTS buildings (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    build_work_amount INTEGER,
    tech_level INTEGER,
    description TEXT,
    icon_path TEXT
);

CREATE TABLE IF NOT EXISTS technology_tree (
    id TEXT PRIMARY KEY,
    level INTEGER,
    name TEXT NOT NULL,
    tech_point_cost INTEGER,
    is_ancient INTEGER DEFAULT 0,
    unlocked_item_id TEXT,
    unlocked_building_id TEXT
);
```

---

## 4. Sample Integration Queries

### A. Full Pal Payload Query (Paldex Entry)
```sql
-- 1. Base Pal Info
SELECT id, name, paldex_number, element1, element2, hp, attack, defense, run_speed, stamina, food, rarity, breeding_rank, nocturnal, icon_path, description
FROM pals WHERE id = 'Anubis';

-- 2. Work Suitabilities
SELECT wt.id, wt.name, ws.level, wt.icon_path
FROM work_suitability ws
JOIN work_types wt ON ws.work_type = wt.id
WHERE ws.pal_id = 'Anubis';

-- 3. Skills (Active, Passive & Partner)
SELECT s.id, s.name, s.element, s.type, s.category, s.power, s.cooldown, s.stat_modifier, s.icon_path, ps.level_learned
FROM skills s
JOIN pal_skills ps ON s.id = ps.skill_id
WHERE ps.pal_id = 'Anubis';

-- 4. Item Drops
SELECT item_id, item_name, min_quantity, max_quantity, drop_rate
FROM drops WHERE pal_id = 'Anubis';
```

### B. Crafting Recipe & Material Costs Query
```sql
SELECT 
    i.id AS item_id,
    i.name AS item_name,
    i.category,
    r.work_amount,
    r.facility_id,
    ri.material_name,
    ri.count AS material_count
FROM items i
JOIN recipes r ON i.id = r.item_id
JOIN recipe_ingredients ri ON r.id = ri.recipe_id
WHERE i.category = 'Weapon';
```

### C. Unique Breeding Combo Lookup Query
```sql
SELECT 
    p1.name AS parent1_name,
    p2.name AS parent2_name,
    child.name AS child_name,
    child.icon_path AS child_icon
FROM breeding_combos bc
JOIN pals p1 ON bc.parent1_id = p1.id
JOIN pals p2 ON bc.parent2_id = p2.id
JOIN pals child ON bc.child_id = child.id
WHERE bc.parent1_id = 'LazyDragon' AND bc.parent2_id = 'ElecCat';
```
