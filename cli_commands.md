# PalEngine CLI Commands Reference

This document provides a comprehensive reference for the available CLI commands in the PalEngine application.

The CLI tool is executed via `python -m palengine.cli.main` or `python palengine/cli/main.py`.

It supports global `--format` options (`table` for human readability, or `json` for programmatic consumption by AI agents).

```bash
python -m palengine.cli.main --format json <command> [options]
```

---

## Command Reference

### 1. `pals` (Static Paldex Database)
Queries the static Paldex database without requiring a save file.
* **Options**:
  * `--element`, `-e`: Filter by element type (e.g. `Fire`, `Dragon`, `Electric`).
  * `--nocturnal`, `-n`: Filter by nocturnal habits.
  * `--suitability`, `-s`: Filter by work suitability in `name:level` or `name` format (e.g. `handiwork:3`, `kindling:2`).
  * `--size`: Filter by Pal size (`XS`, `S`, `M`, `L`, `XL`).
* **Example**:
  ```bash
  python -m palengine.cli.main --format json pals -e Dragon -s mining:3
  ```

### 2. `instances` (Save Game Pal Instances)
Queries dynamic caught Pal instances from player save data.
* **Options**:
  * `--save-path`, `-p`: Path to `Level.sav` (auto-discovers if omitted).
  * `--location`, `-l`: Filter by location (`party`, `palbox`, `base`).
  * `--species`, `-s`: Filter by species display name (e.g. `Anubis`).
  * `--gender`, `-g`: Filter by gender (`Male`, `Female`).
  * `--min-level`: Filter by minimum Pal level.
  * `--min-iv`: Filter by minimum IV in `stat:val` format (e.g. `attack:80`, `defense:70`).
  * `--passive`: Filter by passive skill ID.
* **Example**:
  ```bash
  python -m palengine.cli.main --format json instances -s Anubis --location palbox
  ```

### 3. `condense` (Condenser Optimization)
Calculates the best candidates for condensing duplicate Pals into high-tier star rank keepers based on IVs and passive skills.
* **Options**:
  * `--save-path`, `-p`: Path to `Level.sav` (auto-discovers if omitted).
* **Example**:
  ```bash
  python -m palengine.cli.main --format json condense
  ```

### 4. `bases` (Base Camp Summary)
Summarizes all player base camps, active worker count, and placed infrastructure structures.
* **Options**:
  * `--save-path`, `-p`: Path to `Level.sav` (auto-discovers if omitted).
* **Example**:
  ```bash
  python -m palengine.cli.main --format json bases
  ```

### 5. `base` (Base Camp Optimization & Role Recommendations)
Inspects a specific base camp or generates optimal 24/7 worker team recommendations.
* **Options**:
  * `--id`: Target Base Camp ID. If omitted, lists all base camp IDs.
  * `--recommend`: Generates optimal Pal crew recommendations tailored to built structures, SAN stability, and nocturnal coverage.
  * `--max-team`: Override maximum team capacity.
* **Example**:
  ```bash
  python -m palengine.cli.main --format json base --id <BASE_CAMP_ID> --recommend
  ```

### 6. `breed` (Two-Parent Breeding Calculator)
Calculates the exact resulting child species from two parent species.
* **Arguments**: `parent1` `parent2`
* **Example**:
  ```bash
  python -m palengine.cli.main --format json breed "Grizzbolt" "Relaxaurus"
  ```

### 7. `breed_path` (Multi-Generation Breeding Path Finder)
Finds the shortest multi-generation BFS breeding path from owned species to a target Pal.
* **Options**:
  * `--owned`, `-o`: Comma-separated list of currently owned Pal species.
* **Arguments**: `target`
* **Example**:
  ```bash
  python -m palengine.cli.main --format json breed_path -o "Lamball,Cattiva,Penking" "Shadowbeak"
  ```

### 8. `boss-party` (Boss Counter-Team Recommender)
Generates 5-Pal counter-party builds, active skill (waza) selections, and breeding fallback paths for any Tower Boss, Alpha Field Boss, or Legendary.
* **Arguments**: `boss_name` (e.g. `Victor & Shadowbeak`, `Jetragon`, `Frostallion`, `Bellanoir`)
* **Options**:
  * `--save-path`, `-p`: Path to `Level.sav` (auto-discovers if omitted).
* **Example**:
  ```bash
  python -m palengine.cli.main --format json boss-party "Victor & Shadowbeak"
  ```

### 9. `recommend` (Investment & Combat Report Generator)
Generates deterministic Pal investment recommendations across Combat, Mounts, and Resource Allocations into a markdown report.
* **Options**:
  * `--save-path`, `-p`: Path to `Level.sav` (auto-discovers if omitted).
  * `--output`, `-o`: Output markdown path (default: `analysis_results.md`).
  * `--top`, `-t`: Number of top candidates per category (default: `7`).
* **Example**:
  ```bash
  python -m palengine.cli.main recommend -o analysis_results.md --top 5
  ```

### 10. `export_pals` (Export Caught Pals)
Exports all caught Pals in the save game with full stats, IVs, passives, and locations into a JSON file.
* **Options**:
  * `--save-path`, `-p`: Path to `Level.sav` (auto-discovers if omitted).
  * `--output`, `-o`: Output file path (default: `caught_pals_full.json`).
