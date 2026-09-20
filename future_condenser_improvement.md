# Future Condenser Improvement Specification & Architecture Plan

## 1. Executive Summary & Root Cause Analysis

The current Pal Condenser optimizer in `palengine` (`get_condense_candidates` in `palengine/db/sqlite_engine.py`) determines the "Best Pal" (the keeper to receive upgrades) and "Sacrifices" (the fodder to be consumed) using a primitive scoring formula:

```python
score = (curr_rank * 5000) + (len(passives) * 50 * 1000) + (level * 100) + (iv_hp + iv_melee + iv_defense)
```

### Identified Root Causes (Problems vs. Symptoms)

1. **Quantity Over Quality in Passives**:
   * *The Flaw*: Passives are weighted solely by count (`len(passives) * 50`).
   * *The Problem*: A Pal with 4 detrimental red traits (*Slacker*, *Pacifist*, *Coward*, *Glutton*) receives `+200,000` score points, beating a Pal with 2 god-tier gold traits (*Musclehead*, *Ferocious*) which only gets `+100,000`.
   * *Root Cause*: The scoring function ignores the master database `skills` table, which already stores passive tiers and stat modifiers.

2. **Flat IV Sum Sacrifices Prized Breeding Parents**:
   * *The Flaw*: IVs are evaluated strictly as a flat scalar sum (`iv_hp + iv_melee + iv_defense`).
   * *The Problem*: A Pal with **100 Attack / 10 HP / 10 Def** (Sum: 120) is recommended to be **ground up as fodder** to upgrade a mediocre **45 HP / 45 Atk / 45 Def** Pal (Sum: 135).
   * *Root Cause*: The algorithm lacks a "Specialist Threshold". A Pal with a 90–100 in even a single stat has immense breeding inheritance value and must not be consumed blindly.

3. **Role Blindness (Base Crafters vs. Combat DPS)**:
   * *The Flaw*: Every species is evaluated identically.
   * *The Problem*: Anubis (tier 4 Handiwork crafter) is evaluated on IVs, when IVs have zero effect on crafting or mining speeds. Conversely, combat mounts are evaluated without considering whether they have survival IVs (HP/Def) or combat passives.
   * *Root Cause*: The condenser does not leverage the existing `work_suitability` or `pals` tables to dynamically contextualize what makes a specific Pal valuable.

---

## 2. Core Operating Principles (Strict AGENTS.md Compliance)

1. **Database-First (Zero Hardcoding)**:
   * No hardcoded passive lists or arbitrary dictionary multipliers in application code.
   * All passive quality rankings must be read directly from the master database `data/palworld.db` (`skills` table: `category` contains `PassiveTier-3` through `PassiveTier5`).
2. **Use Existing Tools Exclusively**:
   * Utilize `SQLiteEngine.query_pals()`, `SQLiteEngine.query_instances()`, and master metadata tables (`skills`, `work_suitability`, `pals`).
   * Do not introduce speculative schemas or destructive table migrations.
3. **Surgical Scope Hygiene**:
   * Confine calculation changes to scoring methods, ensuring all downstream consumer contracts (`attainable_stars`, `sacrifices_available`, `best_pal`, UI card renderings) remain intact.

---

## 3. Detailed Technical Architecture Plan

### Component A: Database-Driven Passive Scoring
* **Existing Master Data**:
  * In `data/palworld.db` (`palworld_master.skills`):
    * `category` values:
      * Negative Traits: `PassiveTier-1`, `PassiveTier-2`, `PassiveTier-3`
      * Positive Traits: `PassiveTier1`, `PassiveTier2`, `PassiveTier3`, `PassiveTier4`, `PassiveTier5`
    * `description`: Explicit percentages (e.g. `Work Speed +50%`, `Attack +20%`).
* **Scoring Mechanics**:
  * Parse the numeric tier directly from the database `category`:
    * Tier 4 & 5 (*Legend, Emperor, Flame Emperor*): High positive value (+250)
    * Tier 3 (*Artisan, Musclehead, Ferocious, Swift, Lucky*): Very high positive value (+200)
    * Tier 2 (*Serious, Workaholic, Runner, Burly Body*): Moderate positive value (+100)
    * Tier 1 (*Brave, Hard Skin, Nimble*): Small positive value (+40)
    * Tier -1 (*Glutton, Clumsy, Coward*): Moderate penalty (-100)
    * Tier -2 (*Downtrodden, Brittle, Destructive*): Heavy penalty (-200)
    * Tier -3 (*Slacker, Pacifist*): Severe penalty (-350)
  * Net passive score = Sum of database-derived tier weights. A Pal with negative traits is naturally pushed down to fodder status.

### Component B: The "Breeding Specialist" Protection Shield
* **The Rule**: Any Pal with **at least one IV >= 90** is designated as an **Elite Breeding Asset**.
* **Condenser Behavior**:
  * If a Pal qualifies as an Elite Breeding Asset, it is **excluded from being recommended as a sacrifice** unless the user explicitly unlocks it.
  * When choosing the "Keeper", if a Pal has balanced stats (e.g. 85/85/85), it may be the combat keeper, while single-stat 100s are protected in the Palbox.

### Component C: Dynamic Role-Aware Weighting
* **Worker Bias**:
  * If a Pal's highest work suitability is Level 3 or higher (queried from `work_suitability` in master DB), and its partner skill is non-combat, prioritize *Work Speed* and *Sanity* passives (*Artisan*, *Work Slave*, *Serious*). IV weights are scaled down to near-zero.
* **Combat Bias**:
  * For combat species, prioritize *Attack IV*, *HP IV*, *Defense IV*, and combat passives (*Musclehead*, *Ferocious*, *Legend*, *Serenity*).

---

## 4. Proposed Schema & Method Touchpoints

1. **`palengine/db/sqlite_engine.py`**:
   * Refactor `get_score(p)` inside `get_condense_candidates()`:
     * Replace `len(passives) * 50 * 1000` with the database-driven passive evaluation.
     * Incorporate `is_breeding_specialist` flag (`max(iv_hp, iv_melee, iv_defense) >= 90`).
     * Separate `sacrifices` into:
       * `safe_sacrifices`: True fodder (low IVs, no elite passives).
       * `protected_assets`: Highlighted or excluded Pals (high IVs or high-tier passives).
2. **API Endpoint (`/api/save/condense`)**:
   * Enrich response payload with:
     * `keeper_reasons`: Human-readable summary (e.g. *"Rank 1 + Musclehead, Ferocious + 94 Atk IV"*).
     * `protected_count`: Number of Pals of this species saved from the sacrifice pool due to breeding value.
3. **Frontend Condenser UI (`ui/src/components/CondenserView.jsx`)**:
   * Display visual badge on recommended keepers showing their primary strength (*"Combat Ace"*, *"Breeding Stock"*, *"Master Worker"*).
   * Show warning icon if any sacrifice has an IV >= 85.

---

## 5. Open Questions for Final Review

1. **Strict Exclusion vs. Warning Tag**:
   * Should Pals with an IV >= 90 or Tier 3+ gold passives be **strictly excluded** from the sacrifice pool, or should they remain in the pool but flagged with a red warning in the UI?
2. **Hybrid Pals**:
   * Some Pals (like Anubis or Astegon) are both top-tier combat fighters and top-tier base workers. Should the user be able to toggle a Pal's intended role (*Combat* vs. *Work*), or should the algorithm evaluate the Pal's individual passives (e.g. if it rolled *Artisan*, treat as worker; if it rolled *Musclehead*, treat as fighter)?
