# Palopedix

Palopedix is an advanced save parser, analytics engine, and interactive database viewer for **Palworld**. It features a modern React web interface, a robust FastAPI backend, and an agent-first CLI for players and AI coding agents to inspect, optimize, and plan gameplay.

---

## Key Features

- **Paldex & Skills Catalog**: Explore stats, elements, partner skills, active skills, passives, work suitabilities, authentic condensation rank scaling (Lv 1–5), and **18 deterministic Partner Skill categories** (Flying Mounts, Ranch Producers, Player Infusions, Artillery, Healers, Combat Buffs, etc.).
- **Global vs Caught Modes**: Seamlessly toggle between viewing all **291 genuine in-game Pals** or focusing exclusively on your **caught Pal instances**.
- **Pal Gear & Saddle Tracking**: Auto-detects crafted Key Items (`EssentialContainerId`) from save games, providing real-time crafted status badges (`✅ Crafted & Ready` vs `🔒 Not Crafted`) in Pal Tooltips, Detail Modals, and Explorer filters.
- **Advanced Pal Explorer & Filter Modal**: Centralized 7-column filter modal with searchable dropdowns (`CustomSelect`), 4-slot passive combinations, element filters, removable filter chips, and full **Undo / Redo / Clear History** navigation.
- **Save Game Parser & World Manager**: Auto-discovers Palworld save games (`Level.sav`), supports multi-world save switching, and decodes caught Pals, IVs, souls, ranks, and inventory.
- **Base Camp Work Crew Optimizer**: Analyzes placed infrastructure in active base camps, calculates work suitability demand, balances food consumption and SAN decay, and recommends optimal 24/7 Pal crews.
- **Multi-Generation Breeding Path Finder**: BFS pathfinding from owned Pals to any target Pal, complete with parent instance quality scoring, target passive skill preservation, and gender probability calculations.
- **Boss Counter-Party Recommender**: Builds optimal 5-Pal counter teams for Tower Bosses, Alpha Field Bosses, and Legendaries across three combat archetypes (Pure Elemental DPS, Mounted Player Infusion, and Balanced Hybrid Survival).
- **Pal Condenser Planner**: Evaluates duplicate Pal counts to pinpoint the highest-value condensing candidates and identifies optimal "Keeper" base Pals based on IVs and passives.
- **Items, Crafting & Tech Tree**: Browse equipment, spheres, materials, exact crafting recipes, and ancient technology unlocks.
- **Agent-First CLI**: Complete programmatic command-line interface with `--format json` output designed for AI agent integration.

---

## Self-Installation & Quick Start

Palopedix is designed to work immediately after cloning. **You do NOT need to extract or dump game files yourself.**

### 1. Bundled Master Game Data
The repository includes the full static master database (`data/palworld.db`). This pre-extracted database contains all 291 playable Pal species, 139 authentic passive skills, level-up active skills, partner abilities, breeding combinations, items, recipes, and technology trees.

### 2. Save Game Setup
To inspect your own world and Pals, you only need to provide your Palworld `Level.sav` save file:
- **Default Steam Save Location**:
  ```
  %LOCALAPPDATA%\Pal\Saved\SaveGames\<SteamID>\<WorldID>\Level.sav
  ```
- The application will either auto-detect existing local saves, or you can select/upload your `Level.sav` directly in the web UI **Settings** tab.

### 3. Visual Assets Setup (Optional)
The application runs with full functionality without images. To view Pal portraits, skill icons, and structure graphics:
1. Download `palworld_assets.zip` from the [Palopedix GitHub Releases](https://github.com/mansyno/Palopedix/releases).
2. Place `palworld_assets.zip` into the `assets/` folder.
3. When you run `run.bat`, the app will automatically detect and extract the images into `assets/` on first launch.

---

## Running the Application

### Prerequisites
- **Python 3.10+** (with `pip`)
- **Node.js 18+** (with `npm`)

### Easy One-Click Launch (Windows)
Double-click **`run.bat`** in the project root:
- Automatically detects Python / Conda environment.
- Automatically installs missing Python packages (`requirements.txt`).
- Automatically installs frontend packages (`npm install`).
- Auto-extracts `assets/palworld_assets.zip` if present.
- Launches both the FastAPI backend and Vite frontend dev servers.

### Manual Launch

#### 1. Install Backend Dependencies & Start Server
```bash
pip install -r requirements.txt
python -m uvicorn palengine.api.main:app --reload --port 8000
```

#### 2. Install Frontend Dependencies & Start UI
```bash
cd ui
npm install
npm run dev
```
Open your browser to `http://localhost:5173`.

---

## CLI Reference (AI Agent & Command Line Tooling)

The backend provides a comprehensive CLI at `palengine/cli/main.py`:

```bash
# General CLI help
python -m palengine.cli.main --help

# Query static Pals (supports filtering by element, suitability, size)
python -m palengine.cli.main pals -e Dragon -s mining:3

# Query caught Pal instances from save
python -m palengine.cli.main --format json instances -l party

# Recommend boss counter party
python -m palengine.cli.main --format json boss-party "Victor & Shadowbeak"

# Optimize base camp work crew
python -m palengine.cli.main --format json base --id <BASE_CAMP_ID> --recommend

# Find multi-generation breeding paths
python -m palengine.cli.main --format json breed_path -o "Lamball,Cattiva" "Shadowbeak"
```

---

## Project Structure

```
palopedix/
├── palengine/                 # Python backend package
│   ├── analytics/             # Optimizer, Boss Recommender & Breeding algorithms
│   ├── api/                   # FastAPI REST server & endpoints
│   ├── cli/                   # Click CLI entry point (palengine/cli/main.py)
│   ├── db/                    # SQLite engine & database query layer
│   ├── parser/                # Level.sav GVAS decoding & entity extraction
│   └── world_manager.py       # Multi-world save discovery & switching
├── ui/                        # Modern React + Vite frontend web app
├── data/                      # Bundled master database (palworld.db) & structure aliases
├── assets/                    # Visual assets directory (PNGs / icons)
├── tests/                     # Automated pytest test suite
├── PALOPEDIX_AGENT_GUIDE.md   # Mandatory operating guide for AI coding agents
└── AGENTS.md                  # Workspace agent guidelines & rules
```

---

## Running Tests

Execute the automated test suite:
```bash
python -m pytest tests -v
```
