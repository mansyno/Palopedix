# Endgame Base Master Plan (Authoritative Game State)

---

## 1. Multi-Base Synergy & Universal Storage

All 3 bases share storage in real-time via **Guild Chests (`GuildChest`)**. Items placed in a Guild Chest in any base are immediately available in construction menus and crafting queues everywhere without manual hauling.

```
┌────────────────────────────────┐        ┌────────────────────────────────┐
│    BASE 1: PRODUCTION & FOOD   │        │     BASE 2: MINING OUTPOST     │
├────────────────────────────────┤        ├────────────────────────────────┤
│ • Salad & Food Farming         │        │ • Ore & Coal Extraction        │
│ • Production Assembly Lines    │        │ • Raw Material Feeders         │
│ • Breeding & Pal Storage       │        │                                │
└───────────────┬────────────────┘        └────────────────┬───────────────┘
                │                                          │
                └──────────────► ┌─────────────┐ ◄─────────┘
                                 │ GUILD CHEST │
                                 └──────┬──────┘
                                        │
                                        ▼
                        ┌────────────────────────────────┐
                        │   BASE 3: CRUDE OIL & TECH     │
                        ├────────────────────────────────┤
                        │ • 146 Foundations & Palbox (✓) │
                        │ • Guild Chest & Feed Box (✓)   │
                        │ • 2x Crude Oil Extractors      │
                        │ • Large Power Generator        │
                        │ • Quartz Mining Site           │
                        └────────────────────────────────┘
```

---

## 2. Technology & Schematic Status (300 Normal / 38 Boss Tech Points)

### A. All High-Tier Tech Already Unlocked in Your Save:
* **Crude Oil Extractor (`OilPump`)** & **Large Power Generator (`ElectricGenerator_Large`)** — unlocked and ready to build.
* **Pal Metal Ingot recipe**, **Plasteel (`Plastic`)**, **Circuit Boards (`Infra_ElectronicCircuit`)**, **Polymer**, **Carbon Fiber**, **Cement**.
* **Sphere Assembly Lines**, **Production Assembly Lines**, **Weapon Assembly Lines**, **Electric Generator**, **Electric Kitchen**, **Spa / Spa 2**.
* **Assault Rifle Ammo (`AssaultRifleBullet`)**.

### B. High-End Schematics in Your Inventory (No Tech Points Needed):
* **Assault Rifle Schematic 3 (`Blueprint_AssaultRifle_Default3`)** — Epic Tier Assault Rifle (plus you already have an `AssaultRifle_Default3` crafted in storage with 1,363 bullets).
* **Cold Pal Metal Armor Schematic 5 (`Blueprint_StealArmorCold_5`)** — Legendary Tier 5 armor.
* **Heat Pal Metal Armor Schematic 4 (`Blueprint_StealArmorHeat_4`)** — Epic Tier 4 armor.
* **Semi-Auto Shotgun Schematic 3 (`Blueprint_SemiAutoShotgun_3`)**.
* **Makeshift Assault Rifle Schematic 4 (`Blueprint_MakeshiftAssaultRifle_4`)**.

### C. The Only Thing Left to Unlock:
* **Quartz Mining Site (`QuartzPit`)** — Spend Tech Points to unlock this structure so `Blazamut` and `Menasting` can mine infinite Pure Quartz locally at your base.

---

## 3. Completing Base 3 Construction

You have already built the **146 Foundations**, **Palbox**, **Guild Chest**, **Food Box**, **Electric Generator**, and **Furnace** at Base 3. To finish the base:

1. **Place 2× Crude Oil Extractors (`OilPump`):**
   * Snap them directly onto the 2 natural oil seeps.
   * Materials pull automatically from your Guild Chest.
2. **Place 1× Large Power Generator (`ElectricGenerator_Large`):**
   * Supplies continuous 24/7 power for the extractors.
3. **Place 1× Quartz Mining Site (`QuartzPit`):**
   * Drop it on your foundation floor for infinite passive Quartz.
4. **Pal Comfort & Wellbeing:**
   * Place Pal Beds (`MedicalPalBed_02`/`03`) on your foundations under a roof.
   * Place 1 **High Quality Hot Spring (`Spa2`)**.
   * Stock your Feed Box with **Salad** from Base 1 (+30% Work Speed).

---

## 4. Base 3 Assigned Pal Roster

| Role | Pal Name | Level | Suitability | Assigned Task |
| :--- | :--- | :--- | :--- | :--- |
| **Power (Lead)** | **Dynamoff** | 33 | **Electricity Lv 6** | Keeps Large Generator at 100% |
| **Power (Backup)** | **Beakon** | 44 | **Electricity Lv 4** | Backup generation & transport |
| **Smelting** | **Jormuntide Ignis** | 43 | **Kindling Lv 7** | Rapid smelting of Plasteel & Ingots |
| **Mining (Lead)** | **Blazamut** | 34 | **Mining Lv 7 / Kindling Lv 7** | Mines Quartz site + secondary smelting |
| **Mining #2** | **Menasting** | 43 | **Mining Lv 5** | Continuous Quartz extraction |
| **Crafting #1** | **Anubis** | 36 | **Handiwork Lv 6 / Mining Lv 5** | Instant crafting of Spheres & Ammo |
| **Crafting #2** | **Splatterina** | 39 | **Handiwork Lv 5** | Assembly line crafting |
| **Watering / Crusher** | **Whalaska** | 44 | **Watering Lv 5 / Cooling Lv 6** | Operates Crusher for Paldium Fragments |
| **Transport #1** | **Eidrolon** | 30 | **Transporting Lv 6** | Hauls Crude Oil & Quartz to chests |
| **Transport #2** | **Eidrolon** | 30 | **Transporting Lv 6** | Secondary heavy hauler |
| **Transport #3** | **Ragnahawk** | 42 | **Transporting Lv 5** | High-speed aerial hauler |