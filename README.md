# Palopedix

Palopedix is an all-in-one save parser, base camp optimizer, breeding strategist, and interactive database viewer for **Palworld**. Designed for both players looking to maximize their gameplay and AI coding agents running automated analyses, Palopedix decodes your raw game saves and static game data into actionable insights through three powerful interfaces: a modern Web UI, a robust REST API, and a programmatic CLI.

---

## Three Ways to Experience Palopedix

Palopedix provides three distinct interfaces to fit your workflow:

| Interface | Access | Best For |
| :--- | :--- | :--- |
| 🖥️ **Modern Web UI** | `http://localhost:5173` | Interactive visual exploration, party building, filtering, base camp crews, and breeding trees. |
| ⚡ **FastAPI REST Server** | `http://localhost:8000` | Automated data pipelines, external webhooks, and interactive API documentation at `/docs`. |
| 🤖 **Agent-First CLI** | `python -m palengine.cli.main` | Terminal power users and LLM/AI agents using structured `--format json` output. |

---

## Core Application Capabilities

### 1. 🌐 World Pals & Save Game Explorer
- **Global vs Caught Toggle**: Switch seamlessly between exploring all **291 genuine in-game Pal species** (with base stats, elemental affinities, partner abilities, and mount speeds) and viewing your **personal caught Pal instances**.
- **Accurate Pal Filtering**: The global database filters out dummy, unreleased, and non-playable entities (crossover slimes, Terraria event monsters, boss trainer pairs, and cut NPCs).
- **Comprehensive Instance Details**: Inspect exact IVs (HP, Attack, Defense), souls invested, condensation ranks, active movesets, and passive skills.
- **Scope-Aware Advanced Filter Modal**: A 7-column modal with searchable floating dropdowns (`CustomSelect`), 4-slot passive combinations, element filters, and full undo/redo history. When in "Caught Pals" mode, the passive dropdown dynamically filters to show only skills present on your captured Pals.

### 2. 🏰 Base Camp Work Crew Optimizer
- **Infrastructure Demand Analysis**: Automatically inspects every building, furnace, farm, assembly line, and workstation across all your base camps.
- **24/7 Productivity Balancing**: Calculates work suitability requirements, workload distribution, food consumption, and SAN decay.
- **Smart Crew Recommendations**: Recommends the optimal team of Pals from your Palbox to keep all facilities running without burnout.

### 3. 🧬 Multi-Generation Breeding Path Finder
- **BFS Pathfinding**: Calculates the shortest breeding chain from Pals you currently own to any target Pal in the game.
- **Passive Skill Inheritance**: Prioritizes parent pairs carrying your desired target passives (e.g., Legend, Musclehead, Ferocious, Swift).
- **Gender Probability & Quality Scoring**: Evaluates gender ratios and individual parent quality to maximize the probability of successful breeding outcomes.

### 4. ⚔️ Boss Counter-Party Recommender
- **Optimal 5-Pal Teams**: Automatically constructs top counter-parties against Tower Bosses, Alpha Field Bosses, and Legendaries.
- **Three Combat Archetypes**:
  - *Pure Elemental DPS*: Capitalizes on severe elemental weaknesses.
  - *Mounted Player Infusion*: Uses element-converting mounts (e.g., Chillet, Frostallion) and player attack buffers (Gobfin Vanguard stacks) for maximum player damage.
  - *Balanced Hybrid Survival*: Prioritizes defensive durability, life steal, and active elemental counters for prolonged fights.

### 5. ⭐ Pal Condenser Planner
- **Keeper vs Fodder Identification**: Pinpoints your highest-IV and best-passive "Keeper" base Pals.
- **Duplicate Optimization**: Calculates exact duplicate counts needed for Rank 1 through Rank 5 condensation upgrades without accidentally sacrificing valuable breeding stock.

### 6. 🎒 Pal Gear, Saddles & Inventory Tracking
- **Automatic Key Item Detection**: Reads your player inventory and Key Items (`EssentialContainerId`) in real time.
- **Crafted Status Badges**: Displays `✅ Crafted & Ready` or `🔒 Not Crafted` across all Pal tooltips, modals, and filters for saddles, harnesses, gloves, and weapons.

### 7. 📖 Paldex, Skills & Tech Tree Catalog
- **18 Partner Skill Categories**: Deterministically classifies all partner abilities (Flying Mounts, Ground Mounts, Ranch Producers, Player Infusions, Artillery, Combat Buffs, Healers, Item Droppers, etc.).
- **Authentic Scaling (Lv 1–5)**: Shows exact partner skill stat and damage increases for every condensation rank.
- **Skills & Crafting Recipes**: Browse equipment, spheres, ammunition, structures, exact ingredient recipes, and ancient technology unlocks.

---

## Getting Started & Installation (Players & Users)

Palopedix is designed for zero-friction setup. **You do NOT need external extractors or game asset dumpers**—the master static game database (`data/palworld.db`) is already included.

### Prerequisites
Before running Palopedix, ensure you have:
1. **Python 3.10+**: [Download Python](https://www.python.org/downloads/) *(make sure to check "Add Python to PATH" during installation)*.
2. **Node.js 18+**: [Download Node.js](https://nodejs.org/).

---

### Windows One-Click Quick Start

1. **Clone or Download** the repository:
   ```bash
   git clone https://github.com/mansyno/Palopedix.git
   cd Palopedix
   ```
2. **Double-click `run.bat`**:
   `run.bat` is completely self-installing:
   - Verifies your Python / Conda environment.
   - Automatically installs required Python packages from `requirements.txt`.
   - Automatically installs UI dependencies (`npm install`).
   - Checks for visual assets and auto-extracts them if available.
   - Concurrently launches the backend server and opens the frontend UI at `http://localhost:5173`.

---

### Loading Your Save Game

To inspect your own world, Pals, bases, and inventory:
1. **Default Palworld Save Location (Steam)**:
   ```
   %LOCALAPPDATA%\Pal\Saved\SaveGames\<SteamID>\<WorldID>\Level.sav
   ```
2. **Loading**:
   - Palopedix will auto-discover existing saves in your Steam save folder on startup.
   - Alternatively, open the **Settings** tab in the web UI to browse for your `Level.sav` file or upload it directly.

---

### Visual Assets Setup (Pal Portraits & Icons)

The application functions 100% without images. To view high-resolution Pal portraits, element badges, skill icons, and structure graphics:
1. Download **`palworld_assets.zip`** from [Release v1.0.0](https://github.com/mansyno/Palopedix/releases/tag/v1.0.0).
2. Place `palworld_assets.zip` into the `assets/` folder in the project directory.
3. Launch `run.bat`—it will automatically detect and extract the images into `assets/` on first run!

---

## Developer, CLI & AI Agent Reference

### 1. Running the Stack Manually

#### Backend (FastAPI)
```bash
pip install -r requirements.txt
python -m uvicorn palengine.api.main:app --reload --port 8000
```
Interactive Swagger API documentation is available at `http://localhost:8000/docs`.

#### Frontend (React + Vite)
```bash
cd ui
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

### 2. Command-Line Interface (CLI)

The CLI tool resides at `palengine/cli/main.py` and supports `--format json` for direct AI agent consumption:

```bash
# General CLI help
python -m palengine.cli.main --help

# Query static Pals by element, work suitability, and size
python -m palengine.cli.main pals -e Dragon -s mining:3

# Query caught Pal instances from save game
python -m palengine.cli.main --format json instances -l party

# Recommend optimal counter party for any boss
python -m palengine.cli.main --format json boss-party "Victor & Shadowbeak"

# Optimize base camp work crew
python -m palengine.cli.main --format json base --id <BASE_CAMP_ID> --recommend

# Find multi-generation breeding paths
python -m palengine.cli.main --format json breed_path -o "Lamball,Cattiva" "Shadowbeak"

# Inspect active uncompleted NPC sub-missions
python -m palengine.cli.main --format json missions
```

---

### 3. Running Automated Tests

Run the complete test suite with:
```bash
python -m pytest tests -v
```

---

## Project Structure

```
palopedix/
├── palengine/                 # Python backend package
│   ├── analytics/             # Base optimizer, Boss Recommender & Breeding graphs
│   ├── api/                   # FastAPI server & REST endpoints
│   ├── cli/                   # Click CLI entry point (palengine/cli/main.py)
│   ├── db/                    # SQLite engine, Paldex querying & save loaders
│   ├── parser/                # Level.sav GVAS binary decoding & entity extraction
│   └── world_manager.py       # Multi-world save discovery & switching
├── ui/                        # Modern React + Vite frontend web application
│   ├── src/components/        # Explorer, Breeding, Base Camps, Condenser & Modals
│   └── src/services/          # Frontend API integration layer
├── data/                      # Bundled master database (palworld.db) & structure aliases
├── assets/                    # Visual assets directory (PNGs & icons)
├── tests/                     # Automated pytest suite
├── run.bat                    # One-click Windows startup & self-install script
├── PALOPEDIX_AGENT_GUIDE.md   # Operating guide for AI coding agents
└── AGENTS.md                  # Workspace agent configuration & rules
```
