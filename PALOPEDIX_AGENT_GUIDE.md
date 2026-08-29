# PALOPEDIX AGENT OPERATING GUIDE & SYSTEM SPECIFICATION

> **CRITICAL MANDATORY INSTRUCTION FOR ALL AI AGENTS (ANTIGRAVITY / LLMs):**
> 1. You MUST read this document before formulating any plan, generating answers, or executing any task in this repository.
> 2. You MUST NOT create ad-hoc scratch scripts, duplicate parsers, custom data scrapers, or temporary query runners during a task.
> 3. You MUST ALWAYS use the existing built-in CLI commands, REST APIs, or `palengine` engine methods described below.
> 4. **Missing Functionality / Data Protocol**: Never write new speculative code, ad-hoc fallback catalogs, or workaround logic when encountering missing data or features. Always strive to solve tasks using only existing tools and schemas. If something is missing or incomplete, STOP, describe what is missing to the user, and ask for approval before adding new code.

---

## 1. Core Operating Principles

1. **Use Existing Tools First**: The `palengine` application already contains a complete, robust suite of save parsing, database querying, breeding calculations, base camp optimizations, boss counter algorithms, and condensing evaluations.
2. **Never Write Redundant One-Off Scripts**: If you need data from a save file, Paldex, skill database, or base camp, run the CLI with `--format json` or use `SQLiteEngine`. Do NOT write temporary `.py` files in the root or scratch folders.
3. **No In-Code Workarounds**: If data is missing or incomplete in a database table, do not create hardcoded Python fallback ladders. Surface the missing schema/data to the user.
4. **No Proactive / Unrequested Logic Shifts**: Do not alter parsing formulas, database schemas, or generator scoring algorithms unless explicitly asked by the user.
5. **Surgical Precision**: Touch only the exact files required for the task. Keep diffs minimal and clean.

---

## 2. PalEngine CLI Commands Reference (Agent-First Tooling)

The CLI tool is located at `palengine/cli/main.py` and supports `--format json` for direct programmatic consumption by AI agents.

### A. Paldex & Static Game Data
* **Query Static Pals**:
  ```bash
  python -m palengine.cli.main --format json pals [-e Element] [-n] [-s Suitability:Level] [--size XS|S|M|L|XL] [-c Category]
  ```
* **Breeding Outcome (2 Parents)**:
  ```bash
  python -m palengine.cli.main --format json breed "Parent1" "Parent2"
  ```
* **Multi-Generation Breeding Path**:
  ```bash
  python -m palengine.cli.main --format json breed_path -o "Lamball,Cattiva,Penking" "Shadowbeak"
  ```

### B. Save Game Dynamic Data (Auto-discovers `Level.sav` or uses `-p <path>`)
* **Query Caught Pal Instances**:
  ```bash
  python -m palengine.cli.main --format json instances [-l party|palbox|base] [-s Species] [-g Male|Female] [--min-level N] [--min-iv stat:val] [--passive PASSIVE_ID]
  ```
* **Query Condensing Candidates**:
  ```bash
  python -m palengine.cli.main --format json condense
  ```
* **Query Base Camps & Structures**:
  ```bash
  python -m palengine.cli.main --format json bases
  ```
* **Optimize Work Crew for a Base Camp**:
  ```bash
  python -m palengine.cli.main --format json base --id <BASE_CAMP_ID> --recommend [--max-team N]
  ```
* **Boss Counter-Party Recommender**:
  ```bash
  python -m palengine.cli.main --format json boss-party "Victor & Shadowbeak"
  ```
* **Active NPC Sub-Missions & Quest Fulfillment**:
  ```bash
  python -m palengine.cli.main --format json missions
  ```
* **Full Pal Export**:
  ```bash
  python -m palengine.cli.main export_pals -o caught_pals_full.json
  ```
* **Comprehensive Investment Report**:
  ```bash
  python -m palengine.cli.main recommend -o analysis_results.md --top 7
  ```

---

## 3. Backend Python Engine (`SQLiteEngine`)

When interacting with Python code directly, import and use `SQLiteEngine`:

```python
from palengine.db.sqlite_engine import SQLiteEngine
from palengine.cli.main import discover_save_path

engine = SQLiteEngine()
# Auto-discover or load specific save:
save_path = discover_save_path()
if save_path:
    engine.load_save_data(save_path)

# Built-in query methods:
pals = engine.query_pals(filters)  # Supports element, size, nocturnal, work_suitability, partner_category
categories = engine.get_partner_skill_categories()  # Returns all 18 Partner Skill categories with counts
instances = engine.query_instances(filters)
condense_candidates = engine.get_condense_candidates()
active_missions = engine.get_active_missions()
base_camps = engine.get_base_camps()
base_summary = engine.get_base_camp_summary(base_id)
skills = engine.query_skills(filters)
items = engine.query_items(filters)
tech_tree = engine.query_tech_tree(filters)
breeding_paths = engine.find_all_breeding_paths(owned_list, target_species, target_skills)
```

---

## 4. REST API Endpoints Reference

FastAPI runs at `http://localhost:8000`:
* `GET /api/worlds`: Discovered save game worlds.
* `POST /api/worlds/select`: Switch active world database.
* `GET /api/pals`: Query static Paldex with query params (`element`, `size`, `nocturnal`, `suitability`, `partner_category`).
* `GET /api/pals/partner-skill-categories`: List all Partner Skill categories with metadata and Pal counts.
* `GET /api/save/instances`: Query loaded save instances.
* `GET /api/save/condense`: Get condensing candidates with keeper & fodder breakdown.
* `GET /api/save/missions`: Active uncompleted NPC sub-missions with inventory & Palbox fulfillment status.
* `GET /api/bases` & `GET /api/bases/{id}`: Base camps & structures.
* `GET /api/base_camps/{id}/recommendations`: Base camp optimal work crew.
* `GET /api/breeding/path?target={target}&owned={auto|comma_separated}&target_skills={skills}`: Multi-gen breeding paths with gender odds and instance scores.
* `GET /api/skills`: Active, Passive, and Partner skills catalog.
* `GET /api/items` & `GET /api/items/{id}/recipe`: Items and crafting recipes.
* `GET /api/tech_tree`: Unlockable technology nodes.


---

## 5. Directory Structure & Hygiene Rules

* **`palengine/`**: Production Python backend package (API, CLI, DB, Analytics, Parser).
* **`ui/`**: React Vite web frontend.
* **`tests/`**: Pytest test suite (`python -m pytest tests -v`).
* **`data/`**: Master SQLite databases and static game datasets.
* **Root Directory**: Keep clean. Do NOT place loose `.py` scripts or JSON dumps in the project root.
* **Temporary Files**: If any scratch analysis is strictly required, remove the scratch files immediately after validation.
