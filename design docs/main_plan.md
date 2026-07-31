# Role & Project Overview

You are an expert systems architect and developer building **PalEngine**: a high-performance local tool designed to parse Palworld 1.0 save files (`Level.sav`), combine them with static Paldex game metadata, and expose the data through both an interactive Web UI and a machine-readable CLI.

---

# Architecture Overview

1. **Static Data Core:** Clean JSON datasets covering all Palworld 1.0 Pals, Partner Skills, Passive Skills, Active Skills, Work Suitabilities, and Base Structures.
2. **Save File Parser:** A wrapper using `palworld-save-tools` (or native bindings) to parse `%LOCALAPPDATA%\Pal\Saved\SaveGames\<SteamID>\<SaveID>\Level.sav`. Extracts:
   - Palbox & Party Pals (Level, IVs, Passives, Gender, Condensation rank, Location).
   - Base Infrastructure (Counts of placed structures per Base Camp ID).
3. **In-Memory SQLite Unified DB:** Loads static JSON + parsed save data into an indexed SQLite DB to support complex multi-condition relational queries (e.g., cross-referencing breeding pairs, skill overlaps, base production audits).
4. **Dual Interface Layer:**
   - **CLI Tool (`palengine`):** Returns formatted markdown tables or raw JSON streams for AI/CLI automation.
   - **Web UI (Vite + React):** Fast, clean dashboard with multi-select filtering, Pal details, base inventory view, and a breeding path finder.
5. **Assumptions** if during the planing and exectution you are faced with an ambiguity of a kind that can have an impact on exisitng and new tasks/code stop and elevate this to me before conuntineng
   -

---

# Self-Supervision & Project Control Rules

Before writing any code, you MUST set up a tracking system:

1. **Initialize `PROGRESS.md`:** Create a `PROGRESS.md` file in the project root listing all phases, sub-tasks, and their current status (`[ ]` Pending, `[/]` In Progress, `[X]` Complete).
2. **Sequential Execution:** Work through phases strictly in order. Do NOT begin UI code until the SQLite core and CLI endpoints are functional.
3. **Status Updates:** Update `PROGRESS.md` after completing every sub-task.
4. **Data Safety:** Ensure the save parser only performs **read operations** on `Level.sav` and gracefully handles large binary files without memory exhaustion.

---

# Implementation Milestones

## Phase 1: Workspace & Static Paldex Data Engine

- Establish project directory structure (`/data`, `/parser`, `/db`, `/cli`, `/ui`).
- Create seed JSON files for Pals, Passives, Work Suitabilities, and Base Structures for Palworld 1.0.
- Verify static data schema integrity.

## Phase 2: Save Parser Integration (`Level.sav`)

- Integrate `palworld-save-tools` or GVAS parser.
- Write `parser/extract_pals.py` to target `CharacterSaveParameterMap`.
- Write `parser/extract_bases.py` to scan base structure inventory per Palbox ID.

## Phase 3: In-Memory SQLite Engine

- Design SQLite schema joining static tables and user instance tables.
- Write DB initialization logic to load static JSON + parse output on launch.
- Expose query functions for advanced filtering and breeding logic.

## Phase 4: CLI & Web UI Interfaces

- Build `palengine` CLI wrapper for machine/AI query execution.
- Build React/Vite web application for human interaction and search.

---

# First Action

Begin by creating `PROGRESS.md` and setting up the Phase 1 project directory structure and static data schemas.
